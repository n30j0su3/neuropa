from __future__ import annotations

import json
import ipaddress
import os
import secrets
import time
from dataclasses import fields
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from urllib.parse import urlsplit
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from neuropa.domain import Database, InboxItem, Task, FocusSession, MemoryClaim, ENTITY_TYPES, default_data_dir, Workspace, ChatSession, ChatMessage, AgentMode, ToolDefinition, Artifact
from neuropa.domain.today import TodayService
from neuropa.memory import MemoryClaimService
from neuropa.providers import NoAIProviderAvailable, ProviderRouter
from neuropa.services import HarnessService


def validate_lan_cidr(value: str) -> ipaddress._BaseNetwork:
    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError as exc:
        raise ValueError("CIDR inválido") from exc
    if network.prefixlen < (24 if network.version == 4 else 64):
        raise ValueError("CIDR demasiado amplio")
    if network.is_unspecified or network.is_loopback or network.is_multicast or network.is_global:
        raise ValueError("CIDR debe ser privado o link-local")
    if not (network.is_private or network.is_link_local) or (network.version == 6 and not (network.network_address.exploded.startswith("fd") or network.network_address.exploded.startswith("fe80"))):
        raise ValueError("CIDR no local")
    return network


def client_in_cidr(host: str | None, lan_cidr: str | None) -> bool:
    if not host or not lan_cidr:
        return False
    try:
        return ipaddress.ip_address(host) in validate_lan_cidr(lan_cidr)
    except ValueError:
        return host == "testclient"


def client_allowed_for_token(host: str | None, lan_cidr: str | None) -> bool:
    """Master-token retrieval is loopback-only; LAN always uses pairing."""
    return host in {"127.0.0.1", "::1", "testclient"}


class PairingGate:
    def __init__(self, code: str | None, cidr: str | None):
        self.code = code or ""
        self.network = validate_lan_cidr(cidr) if cidr else None
        self.failures: dict[str, int] = {}
        self.device_tokens: dict[str, str] = {}

    def pair(self, host: str | None, code: str) -> str | None:
        ip = host or ""
        allowed = ip == "testclient" or (self.network is not None and self._contains(ip))
        if not allowed or self.failures.get(ip, 0) >= 5 or not self.code or not secrets.compare_digest(code, self.code):
            self.failures[ip] = self.failures.get(ip, 0) + 1
            return None
        self.code = ""
        return self.issue_device(ip)

    def issue_device(self, host: str) -> str:
        token = secrets.token_urlsafe(32)
        self.device_tokens[token] = host
        return token

    def _contains(self, host: str) -> bool:
        try:
            return ipaddress.ip_address(host) in self.network  # type: ignore[operator]
        except ValueError:
            return False

    def valid_device(self, token: str | None, host: str | None) -> bool:
        return bool(token and token in self.device_tokens and (host == "testclient" or self.device_tokens[token] == host))


def token_path() -> Path:
    return default_data_dir() / "token"


def get_token() -> str:
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_text(encoding="utf-8").strip()
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(secrets.token_urlsafe(32))
    return path.read_text(encoding="utf-8").strip()


class InboxCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw_text: str = Field(min_length=1)
    source: str = "text"
    context: dict[str, Any] = Field(default_factory=dict)


class InboxUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str | None = None
    status: str | None = None
    context: dict[str, Any] | None = None


class ClarifyRequest(BaseModel):
    raw_text: str | None = None
    inbox_id: str | None = None
    mode: str | None = None
    privacy_sensitive: bool = False


class MemoryStoreRequest(BaseModel):
    claim_text: str = Field(min_length=1)
    source_type: str = "note"
    source_ref: str = ""
    confidence: float = 0.5


class MemoryQueryRequest(BaseModel):
    query: str = Field(min_length=1)


class HarnessMessageRequest(BaseModel):
    content: str = Field(min_length=1)
    mode_id: str | None = None
    provider: str | None = None
    model: str = ""
    privacy_sensitive: bool = False
    context_scope: Literal["none", "session", "session_memory"] | None = None
    memory_claim_ids: list[str] | None = None


class WorkspaceRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    settings: dict[str, Any] = Field(default_factory=dict)


class SessionRequest(BaseModel):
    title: str = "Nueva sesión"
    workspace_id: str | None = None
    project_id: str | None = None
    mode_id: str | None = None
    provider_id: str | None = None
    model: str = ""
    local_only: bool = False


class PairRequest(BaseModel):
    code: str = Field(min_length=1, max_length=256)


def create_app(db: Database | None = None, router: ProviderRouter | None = None, harness: HarnessService | None = None) -> FastAPI:
    database = db or Database()
    get_token()
    provider_router = router or ProviderRouter()
    harness_service = harness or HarnessService(database, provider_router)
    pairing_gate = PairingGate(os.getenv("NEUROPA_PAIRING_CODE"), os.getenv("NEUROPA_LAN_CIDR"))
    today = TodayService(database)
    memory = MemoryClaimService(database)
    app = FastAPI(title="NeuroPA Local API", version="0.2.0")
    frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
    assets_dir = frontend_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    bearer = HTTPBearer(auto_error=False)

    async def require_auth(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
        host = request.client.host if request.client else None
        master = credentials and credentials.scheme.lower() == "bearer" and secrets.compare_digest(credentials.credentials, get_token())
        device = pairing_gate.valid_device(request.cookies.get("neuropa_session"), host)
        if not master and not device:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required", headers={"WWW-Authenticate": "Bearer"})

    def valid_token(token: str | None) -> bool:
        return bool(token and secrets.compare_digest(token, get_token()))

    @app.get("/")
    def frontend() -> FileResponse:
        return FileResponse(frontend_dir / "index.html", media_type="text/html")

    @app.get("/api/token")
    def frontend_token(request: Request, response: Response) -> dict[str, bool]:
        host = request.client.host if request.client else None
        if not client_allowed_for_token(host, os.getenv("NEUROPA_LAN_CIDR")):
            raise HTTPException(status_code=403, detail="Token pairing is loopback-only")
        device = pairing_gate.issue_device(host or "loopback")
        response.set_cookie("neuropa_session", device, max_age=8 * 60 * 60, httponly=True, samesite="strict", secure=False)
        return {"paired": True}

    @app.post("/api/pair")
    def pair(request: Request, payload: PairRequest, response: Response) -> dict[str, bool]:
        host = request.client.host if request.client else None
        device = pairing_gate.pair(host, payload.code)
        if not device:
            raise HTTPException(status_code=403, detail="Pairing failed")
        response.set_cookie("neuropa_session", device, max_age=8 * 60 * 60, httponly=True, samesite="strict", secure=False)
        return {"paired": True}

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/inbox", dependencies=[Depends(require_auth)])
    def list_inbox() -> list[dict[str, Any]]:
        return [x.to_dict() for x in database.list("inbox")]

    @app.post("/api/inbox", status_code=201, dependencies=[Depends(require_auth)])
    def create_inbox(payload: InboxCreate) -> dict[str, Any]:
        return database.create(InboxItem(raw_text=payload.raw_text, source=payload.source, context=payload.context)).to_dict()

    @app.get("/api/inbox/{item_id}", dependencies=[Depends(require_auth)])
    def get_inbox(item_id: str) -> dict[str, Any]:
        item = database.get("inbox", item_id)
        if not item:
            raise HTTPException(404, "Inbox item not found")
        return item.to_dict()

    @app.patch("/api/inbox/{item_id}", dependencies=[Depends(require_auth)])
    def update_inbox(item_id: str, payload: InboxUpdate) -> dict[str, Any]:
        item = database.get("inbox", item_id)
        if not item:
            raise HTTPException(404, "Inbox item not found")
        return database.update(item, **payload.model_dump(exclude_none=True)).to_dict()

    @app.post("/api/inbox/{item_id}/archive", dependencies=[Depends(require_auth)])
    def archive_inbox(item_id: str) -> dict[str, bool]:
        if not database.soft_delete("inbox", item_id):
            raise HTTPException(404, "Inbox item not found")
        return {"archived": True}

    @app.get("/api/providers/status", dependencies=[Depends(require_auth)])
    def providers_status() -> dict[str, Any]:
        return provider_router.status()

    @app.get("/api/workspaces", dependencies=[Depends(require_auth)])
    def list_workspaces() -> list[dict[str, Any]]:
        return [x.to_dict() for x in database.list("workspace")]

    @app.post("/api/workspaces", status_code=201, dependencies=[Depends(require_auth)])
    def create_workspace(payload: WorkspaceRequest) -> dict[str, Any]:
        return harness_service.create_workspace(**payload.model_dump()).to_dict()

    @app.get("/api/sessions", dependencies=[Depends(require_auth)])
    def list_sessions() -> list[dict[str, Any]]:
        return [x.to_dict() for x in database.list("chat_session")]

    @app.post("/api/sessions", status_code=201, dependencies=[Depends(require_auth)])
    def create_session(payload: SessionRequest) -> dict[str, Any]:
        try:
            return harness_service.create_session(**payload.model_dump()).to_dict()
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/sessions/{session_id}", dependencies=[Depends(require_auth)])
    def get_session(session_id: str) -> dict[str, Any]:
        session = database.get("chat_session", session_id)
        if not session: raise HTTPException(404, "Session not found")
        return {**session.to_dict(), "messages": [x.to_dict() for x in harness_service.session_messages(session_id)]}

    @app.post("/api/sessions/{session_id}/messages", dependencies=[Depends(require_auth)])
    def send_session_message(session_id: str, payload: HarnessMessageRequest) -> dict[str, Any]:
        try:
            return harness_service.send_message(session_id, **payload.model_dump()).to_dict()
        except KeyError as exc: raise HTTPException(404, "Session not found") from exc
        except ValueError as exc: raise HTTPException(400, str(exc)) from exc
        except NoAIProviderAvailable as exc: raise HTTPException(503, str(exc)) from exc

    @app.get("/api/agent-modes", dependencies=[Depends(require_auth)])
    def agent_modes() -> list[dict[str, Any]]:
        return [x.to_dict() for x in database.list("agent_mode")]

    @app.get("/api/tools", dependencies=[Depends(require_auth)])
    def tools() -> list[dict[str, Any]]:
        return [x.to_dict() for x in database.list("tool_definition")]

    @app.get("/api/artifacts", dependencies=[Depends(require_auth)])
    def artifacts() -> list[dict[str, Any]]:
        return [x.to_dict() for x in database.list("artifact")]

    @app.post("/api/messages/{message_id}/artifact", dependencies=[Depends(require_auth)])
    def message_artifact(message_id: str) -> dict[str, Any]:
        try: return harness_service.create_artifact(message_id).to_dict()
        except KeyError as exc: raise HTTPException(404, "Assistant message not found") from exc

    @app.post("/api/setup/detect", dependencies=[Depends(require_auth)])
    def setup_detect() -> dict[str, Any]:
        state = provider_router.status()
        recommended = "opencode_free" if state["modes"]["opencode_free"]["available"] else "local" if state["modes"]["local"]["available"] else "byok" if state["modes"]["byok"]["available"] else "managed" if state["modes"]["managed"]["available"] else None
        return {"capabilities": state["modes"], "recommended_path": recommended}

    @app.post("/api/ai/clarify", dependencies=[Depends(require_auth)])
    def clarify(payload: ClarifyRequest) -> dict[str, Any]:
        text = payload.raw_text
        if not text and payload.inbox_id:
            item = database.get("inbox", payload.inbox_id)
            text = item.raw_text if item else None  # type: ignore[union-attr]
        if not text:
            raise HTTPException(400, "raw_text or inbox_id required")
        try:
            return provider_router.clarify(text, mode=payload.mode, privacy_sensitive=payload.privacy_sensitive)  # type: ignore[call-arg]
        except NoAIProviderAvailable as exc:
            raise HTTPException(503, "No AI provider available") from exc

    @app.post("/api/memory/store", status_code=201, dependencies=[Depends(require_auth)])
    def memory_store(payload: MemoryStoreRequest) -> dict[str, Any]:
        return memory.store_claim(**payload.model_dump()).to_dict()

    @app.post("/api/memory/query", dependencies=[Depends(require_auth)])
    def memory_query(payload: MemoryQueryRequest) -> dict[str, Any]:
        return memory.answer_with_evidence(payload.query)

    @app.get("/api/today", dependencies=[Depends(require_auth)])
    def get_today() -> dict[str, Any]:
        return {"today": today.get_today_view(), "recovery": today.get_recovery_flow()}

    @app.put("/api/tasks/{task_id}/start", dependencies=[Depends(require_auth)])
    def start_task(task_id: str) -> dict[str, Any]:
        try:
            return today.start(task_id).to_dict()
        except KeyError as exc:
            raise HTTPException(404, "Task not found") from exc

    @app.put("/api/tasks/{task_id}/pause", dependencies=[Depends(require_auth)])
    def pause_task(task_id: str) -> dict[str, Any]:
        try:
            return today.pause(task_id).to_dict()
        except KeyError as exc:
            raise HTTPException(404, "Active focus session not found") from exc

    @app.websocket("/ws/focus")
    async def focus_socket(websocket: WebSocket, token: str | None = Query(default=None)) -> None:
        host = websocket.client.host if websocket.client else None
        origin = websocket.headers.get("origin")
        host_header = websocket.headers.get("host", "").split(":", 1)[0].lower()
        origin_host = (urlsplit(origin).hostname or "").lower() if origin else None
        if origin_host and host_header and origin_host != host_header:
            await websocket.close(code=1008)
            return
        is_loopback = host in {"127.0.0.1", "::1", "testclient"}
        is_lan = client_in_cidr(host, os.getenv("NEUROPA_LAN_CIDR")) and not is_loopback
        cookie_ok = pairing_gate.valid_device(websocket.cookies.get("neuropa_session"), host)
        query_ok = is_loopback and valid_token(token)
        if not cookie_ok and not query_ok:
            await websocket.close(code=1008)
            return
        if is_lan and token:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        session: FocusSession | None = None
        started = 0.0
        paused_elapsed = 0.0
        try:
            while True:
                message = json.loads(await websocket.receive_text())
                action = message.get("action")
                if action == "start":
                    task_id = message.get("task_id")
                    task = database.get("task", task_id) if task_id else None
                    if not task:
                        await websocket.send_json({"error": "Task not found"})
                        continue
                    session = database.create(FocusSession(task_id=task_id, planned_min=int(message.get("planned_min", 25)), outcome="running"))
                    database.update(task, status="in_progress")
                    started = time.monotonic()
                    paused_elapsed = 0
                    await websocket.send_json({"state": "running", "session_id": session.id})
                elif action == "tick" and session:
                    elapsed = int(paused_elapsed + (time.monotonic() - started if session.outcome == "running" else 0))
                    await websocket.send_json({"elapsed_sec": elapsed, "remaining_sec": max(0, session.planned_min * 60 - elapsed), "state": session.outcome})
                elif action == "pause" and session:
                    paused_elapsed += time.monotonic() - started
                    session = database.update(session, outcome="paused", actual_min=int(paused_elapsed / 60))
                    await websocket.send_json({"state": "paused", "session_id": session.id})
                elif action in ("complete", "abandon") and session:
                    if session.outcome == "running":
                        paused_elapsed += time.monotonic() - started
                    outcome = "completed" if action == "complete" else "abandoned"
                    session = database.update(session, outcome=outcome, actual_min=int(paused_elapsed / 60), reflection_1q=message.get("reflection", ""))
                    await websocket.send_json({"state": outcome, "session_id": session.id})
                else:
                    await websocket.send_json({"error": "Invalid focus action"})
        except WebSocketDisconnect:
            return

    @app.get("/api/export", dependencies=[Depends(require_auth)])
    def export_data() -> dict[str, Any]:
        entities = {typ: [obj.to_dict() for obj in database.list(typ)] for typ in ENTITY_TYPES}
        return {"replace": True, "entities": entities, **entities}

    @app.post("/api/import", dependencies=[Depends(require_auth)])
    async def import_data(request: Request) -> dict[str, Any]:
        body = await request.body()
        if len(body) > 5 * 1024 * 1024:
            raise HTTPException(413, "Import demasiado grande")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise HTTPException(400, "JSON inválido") from exc
        if not isinstance(payload, dict) or payload.get("replace") is not True or not isinstance(payload.get("entities"), dict):
            raise HTTPException(400, "Se requiere replace=true y entities")
        prepared = []
        seen: set[str] = set()
        try:
            for typ, rows in payload["entities"].items():
                cls = ENTITY_TYPES.get(typ)
                if cls is None or not isinstance(rows, list):
                    raise ValueError("tipo de entidad inválido")
                allowed = {field.name for field in fields(cls)}
                for row in rows:
                    if not isinstance(row, dict):
                        raise ValueError("fila inválida")
                    if set(row) - allowed - {"entity_type"}:
                        raise ValueError("campo de entidad desconocido")
                    if row.get("entity_type", typ) != typ:
                        raise ValueError("entity_type no coincide")
                    obj_id = row.get("id")
                    UUID(str(obj_id))
                    if not isinstance(obj_id, str) or "/" in obj_id or "\\" in obj_id or obj_id in seen:
                        raise ValueError("id inválido o duplicado")
                    seen.add(obj_id)
                    data = dict(row)
                    data.pop("entity_type", None)
                    prepared.append(cls(**data))
            database.replace_entities(prepared)
        except (ValueError, TypeError, KeyError) as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"imported": len(prepared)}

    return app


app = create_app()
