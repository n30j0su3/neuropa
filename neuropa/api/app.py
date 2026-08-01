from __future__ import annotations

import json
import ipaddress
import os
import secrets
import time
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from neuropa.domain import Database, InboxItem, Task, FocusSession, MemoryClaim, ENTITY_TYPES, default_data_dir, Workspace, ChatSession, ChatMessage, AgentMode, ToolDefinition, Artifact
from neuropa.domain.today import TodayService
from neuropa.memory import MemoryClaimService
from neuropa.providers import NoAIProviderAvailable, ProviderRouter
from neuropa.services import HarnessService


def client_allowed_for_token(host: str | None, lan_cidr: str | None) -> bool:
    """Allow token pairing only from loopback or an explicitly enabled LAN."""
    if host in {"127.0.0.1", "::1", "testclient"}:
        return True
    if not host or not lan_cidr:
        return False
    try:
        return ipaddress.ip_address(host) in ipaddress.ip_network(lan_cidr, strict=False)
    except ValueError:
        return False


def token_path() -> Path:
    return default_data_dir() / "token"


def get_token() -> str:
    path = token_path()
    if not path.exists():
        path.write_text(secrets.token_urlsafe(32), encoding="utf-8")
        path.chmod(0o600)
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


def create_app(db: Database | None = None, router: ProviderRouter | None = None, harness: HarnessService | None = None) -> FastAPI:
    database = db or Database()
    get_token()
    provider_router = router or ProviderRouter()
    harness_service = harness or HarnessService(database, provider_router)
    today = TodayService(database)
    memory = MemoryClaimService(database)
    app = FastAPI(title="NeuroPA Local API", version="0.2.0")
    frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
    assets_dir = frontend_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    bearer = HTTPBearer(auto_error=False)

    async def require_auth(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
        if not credentials or credentials.scheme.lower() != "bearer" or not secrets.compare_digest(credentials.credentials, get_token()):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required", headers={"WWW-Authenticate": "Bearer"})

    def valid_token(token: str | None) -> bool:
        return bool(token and secrets.compare_digest(token, get_token()))

    @app.get("/")
    def frontend() -> FileResponse:
        return FileResponse(frontend_dir / "index.html", media_type="text/html")

    @app.get("/api/token")
    def frontend_token(request: Request) -> dict[str, str]:
        host = request.client.host if request.client else None
        lan_cidr = os.getenv("NEUROPA_LAN_CIDR")
        if not client_allowed_for_token(host, lan_cidr):
            raise HTTPException(status_code=403, detail="Token pairing is not enabled for this client")
        return {"token": get_token()}

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
        return harness_service.create_session(**payload.model_dump()).to_dict()

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
        if not valid_token(token):
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
        return {typ: [obj.to_dict() for obj in database.list(typ)] for typ in ENTITY_TYPES}

    @app.post("/api/import", dependencies=[Depends(require_auth)])
    def import_data(payload: dict[str, Any]) -> dict[str, Any]:
        database.conn.execute("DELETE FROM entities")
        database.conn.commit()
        count = 0
        for typ, rows in payload.items():
            cls = ENTITY_TYPES.get(typ)
            if not cls or not isinstance(rows, list):
                continue
            for row in rows:
                data = dict(row)
                data.pop("entity_type", None)
                database.create(cls(**data))
                count += 1
        return {"imported": count}

    return app


app = create_app()
