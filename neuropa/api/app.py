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

from neuropa.domain import Database, InboxItem, Task, FocusSession, MemoryClaim, ENTITY_TYPES, default_data_dir, Workspace, ChatSession, ChatMessage, AgentMode, ToolDefinition, Artifact, AgentProfile, Skill, MCPServer
from neuropa.domain.today import TodayService
from neuropa.memory import MemoryClaimService
from neuropa.memory.graph import build_memory_graph
from neuropa.memory.wiki import WikiService
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


def client_allowed_for_token(host: str | None, lan_cidr: str | None, pairing_required: bool = False) -> bool:
    """Token retrieval is allowed from loopback always, and from trusted LAN when pairing is not required."""
    if host in {"127.0.0.1", "::1", "testclient"}:
        return True
    if pairing_required:
        return False
    if lan_cidr:
        try:
            return ipaddress.ip_address(host or "") in validate_lan_cidr(lan_cidr)
        except (ValueError, TypeError):
            pass
    return False


class PairingGate:
    def __init__(self, code: str | None, cidr: str | None):
        self.code = code or ""
        self.required = bool(code)
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


class MemorySupersedeRequest(BaseModel):
    claim_text: str = Field(min_length=1)
    source_type: str = "note"
    source_ref: str = ""
    confidence: float = 0.5


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


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    display_name: str | None = None
    system_prompt: str | None = None
    default_provider: str | None = None
    default_mode_id: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)


class AgentModeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    description: str = Field(default="", max_length=500)
    system_prompt: str = Field(default="", max_length=12000)
    temperature: float = Field(default=0.5, ge=0, le=2)
    enabled: bool = True
    tool_ids: list[str] = Field(default_factory=list, max_length=64)


class AgentModeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    description: str | None = Field(default=None, max_length=500)
    system_prompt: str | None = Field(default=None, max_length=12000)
    temperature: float | None = Field(default=None, ge=0, le=2)
    enabled: bool | None = None
    tool_ids: list[str] | None = Field(default=None, max_length=64)


class IdentityUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    soul_md: str = Field(min_length=1, max_length=32768)
    agents_md: str = Field(min_length=1, max_length=32768)


class ExportSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sections: list[str] = Field(default_factory=list)
    format: Literal["json"] = "json"


class WikiWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1)
    body: str = ""
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    source_claims: list[str] = Field(default_factory=list)
    related_concepts: list[str] = Field(default_factory=list)


class PairRequest(BaseModel):
    code: str = Field(min_length=1, max_length=256)


class SkillCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    version: str = Field(default="1.0.0", max_length=40)
    source: Literal["local", "builtin", "repository"] = "local"
    content_path: str = Field(default="", max_length=500)
    enabled: bool = False


class SkillUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    version: str | None = Field(default=None, max_length=40)
    source: Literal["local", "builtin", "repository"] | None = None
    content_path: str | None = Field(default=None, max_length=500)
    enabled: bool | None = None


class MCPServerCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    server_type: Literal["local", "http"] = "local"
    command: list[str] = Field(default_factory=list, max_length=32)
    url: str = Field(default="", max_length=500)
    enabled: bool = False


class MCPServerUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    server_type: Literal["local", "http"] | None = None
    command: list[str] | None = Field(default=None, max_length=32)
    url: str | None = Field(default=None, max_length=500)
    enabled: bool | None = None


def create_app(db: Database | None = None, router: ProviderRouter | None = None, harness: HarnessService | None = None) -> FastAPI:
    database = db or Database()
    get_token()
    provider_router = router or ProviderRouter()
    harness_service = harness or HarnessService(database, provider_router)
    pairing_gate = PairingGate(os.getenv("NEUROPA_PAIRING_CODE"), os.getenv("NEUROPA_LAN_CIDR"))
    today = TodayService(database)
    wiki = WikiService(database.path.parent)
    memory = MemoryClaimService(database, wiki=wiki)
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
        trusted_lan = not pairing_gate.required and client_in_cidr(host, os.getenv("NEUROPA_LAN_CIDR"))
        if not master and not device and not trusted_lan:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required", headers={"WWW-Authenticate": "Bearer"})

    def valid_token(token: str | None) -> bool:
        return bool(token and secrets.compare_digest(token, get_token()))

    @app.get("/")
    def frontend() -> FileResponse:
        return FileResponse(frontend_dir / "index.html", media_type="text/html")

    @app.get("/api/token")
    def frontend_token(request: Request, response: Response) -> dict[str, bool]:
        host = request.client.host if request.client else None
        if not client_allowed_for_token(host, os.getenv("NEUROPA_LAN_CIDR"), pairing_gate.required):
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

    @app.post("/api/agent-modes", status_code=201, dependencies=[Depends(require_auth)])
    def create_agent_mode(payload: AgentModeCreateRequest) -> dict[str, Any]:
        if any(getattr(mode, "slug", "") == payload.slug for mode in database.list("agent_mode")):
            raise HTTPException(409, "Mode slug already exists")
        return database.create(AgentMode(**payload.model_dump())).to_dict()

    @app.patch("/api/agent-modes/{mode_id}", dependencies=[Depends(require_auth)])
    def update_agent_mode(mode_id: str, payload: AgentModeUpdateRequest) -> dict[str, Any]:
        mode = database.get("agent_mode", mode_id)
        if not mode:
            raise HTTPException(404, "Agent mode not found")
        changes = payload.model_dump(exclude_none=True)
        slug = changes.get("slug")
        if slug and any(item.id != mode_id and getattr(item, "slug", "") == slug for item in database.list("agent_mode")):
            raise HTTPException(409, "Mode slug already exists")
        return database.update(mode, **changes).to_dict()

    @app.delete("/api/agent-modes/{mode_id}", dependencies=[Depends(require_auth)])
    def delete_agent_mode(mode_id: str) -> dict[str, bool]:
        if not database.soft_delete("agent_mode", mode_id):
            raise HTTPException(404, "Agent mode not found")
        return {"deleted": True}

    @app.get("/api/tools", dependencies=[Depends(require_auth)])
    def tools() -> list[dict[str, Any]]:
        return [x.to_dict() for x in database.list("tool_definition")]

    @app.get("/api/artifacts", dependencies=[Depends(require_auth)])
    def artifacts() -> list[dict[str, Any]]:
        return [x.to_dict() for x in database.list("artifact")]

    @app.get("/api/artifacts/{artifact_id}", dependencies=[Depends(require_auth)])
    def read_artifact(artifact_id: str) -> dict[str, Any]:
        try:
            return harness_service.read_artifact(artifact_id)
        except KeyError as exc:
            raise HTTPException(404, "Artifact not found") from exc
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/artifacts/{artifact_id}/raw", dependencies=[Depends(require_auth)])
    def artifact_raw(artifact_id: str, inline: int = 0) -> FileResponse:
        try:
            target, media, name = harness_service.artifact_file(artifact_id)
        except KeyError as exc:
            raise HTTPException(404, "Artifact not found") from exc
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(400, str(exc)) from exc
        headers: dict[str, str] = {}
        if inline and media == "text/html":
            # Sandboxed origin: generated HTML cannot touch app cookies/storage.
            headers["Content-Security-Policy"] = "sandbox allow-scripts allow-modals"
        else:
            headers["Content-Disposition"] = f'attachment; filename="{name.replace(chr(34), "")}"'
        return FileResponse(target, media_type=media, headers=headers)

    @app.post("/api/messages/{message_id}/artifact", dependencies=[Depends(require_auth)])
    def message_artifact(message_id: str) -> dict[str, Any]:
        try: return harness_service.create_artifact(message_id).to_dict()
        except KeyError as exc: raise HTTPException(404, "Assistant message not found") from exc

    # ── AgentProfile ──

    @app.get("/api/profile", dependencies=[Depends(require_auth)])
    def get_primary_profile() -> dict[str, Any]:
        profile = harness_service.primary_profile()
        if not profile:
            raise HTTPException(404, "No primary agent profile found")
        return profile.to_dict()

    @app.put("/api/profile", dependencies=[Depends(require_auth)])
    def update_primary_profile(payload: ProfileUpdateRequest) -> dict[str, Any]:
        profile = harness_service.primary_profile()
        if not profile:
            raise HTTPException(404, "No primary agent profile found")
        try:
            return harness_service.update_profile(profile.id, **payload.model_dump(exclude_none=True)).to_dict()
        except KeyError as exc:
            raise HTTPException(404, "Profile not found") from exc

    @app.get("/api/identity", dependencies=[Depends(require_auth)])
    def get_identity() -> dict[str, str]:
        return harness_service.identity_docs()

    @app.put("/api/identity", dependencies=[Depends(require_auth)])
    def update_identity(payload: IdentityUpdateRequest) -> dict[str, str]:
        return harness_service.update_identity(**payload.model_dump())

    # ── Skills + MCP workspace registry ──

    @app.get("/api/skills", dependencies=[Depends(require_auth)])
    def list_skills() -> list[dict[str, Any]]:
        return [x.to_dict() for x in database.list("skill")]

    @app.post("/api/skills", status_code=201, dependencies=[Depends(require_auth)])
    def create_skill(payload: SkillCreateRequest) -> dict[str, Any]:
        return database.create(Skill(**payload.model_dump())).to_dict()

    @app.patch("/api/skills/{skill_id}", dependencies=[Depends(require_auth)])
    def update_skill(skill_id: str, payload: SkillUpdateRequest) -> dict[str, Any]:
        skill = database.get("skill", skill_id)
        if not skill:
            raise HTTPException(404, "Skill not found")
        return database.update(skill, **payload.model_dump(exclude_none=True)).to_dict()

    @app.delete("/api/skills/{skill_id}", dependencies=[Depends(require_auth)])
    def delete_skill(skill_id: str) -> dict[str, bool]:
        if not database.soft_delete("skill", skill_id):
            raise HTTPException(404, "Skill not found")
        return {"deleted": True}

    @app.get("/api/mcp-servers", dependencies=[Depends(require_auth)])
    def list_mcp_servers() -> list[dict[str, Any]]:
        return [x.to_dict() for x in database.list("mcp_server")]

    @app.post("/api/mcp-servers", status_code=201, dependencies=[Depends(require_auth)])
    def create_mcp_server(payload: MCPServerCreateRequest) -> dict[str, Any]:
        return database.create(MCPServer(**payload.model_dump())).to_dict()

    @app.patch("/api/mcp-servers/{server_id}", dependencies=[Depends(require_auth)])
    def update_mcp_server(server_id: str, payload: MCPServerUpdateRequest) -> dict[str, Any]:
        server = database.get("mcp_server", server_id)
        if not server:
            raise HTTPException(404, "MCP server not found")
        return database.update(server, **payload.model_dump(exclude_none=True)).to_dict()

    @app.delete("/api/mcp-servers/{server_id}", dependencies=[Depends(require_auth)])
    def delete_mcp_server(server_id: str) -> dict[str, bool]:
        if not database.soft_delete("mcp_server", server_id):
            raise HTTPException(404, "MCP server not found")
        return {"deleted": True}

    # ── Selective export ──

    _SECRET_KEY_FRAGMENTS = frozenset([
        "token", "api_key", "apikey", "secret", "password", "passwd", "credential",
        "oauth", "bearer", "authorization", "pairing_code",
    ])

    _EXPORTABLE_SECTIONS = {
        "agent_profile", "workspace", "chat_session", "chat_message",
        "memory_claim", "artifact", "skill", "tool_definition",
        "agent_mode", "mcp_server", "preset",
    }

    def _redact_secrets_recursive(obj: Any, path: str = "", redacted: list[str] | None = None) -> Any:
        """Recursively redact any key whose name contains a secret fragment."""
        if redacted is None:
            redacted = []
        if isinstance(obj, dict):
            clean: dict[str, Any] = {}
            for key, val in obj.items():
                key_lower = str(key).lower()
                full_path = f"{path}.{key}" if path else str(key)
                if any(frag in key_lower for frag in _SECRET_KEY_FRAGMENTS):
                    redacted.append(full_path)
                    clean[key] = "[REDACTED]"
                else:
                    clean[key] = _redact_secrets_recursive(val, full_path, redacted)
            return clean
        if isinstance(obj, list):
            return [_redact_secrets_recursive(item, f"{path}[{i}]", redacted) for i, item in enumerate(obj)]
        return obj

    @app.post("/api/export/selected", dependencies=[Depends(require_auth)])
    def export_selected(payload: ExportSelectionRequest) -> dict[str, Any]:
        unknown = sorted(set(payload.sections) - _EXPORTABLE_SECTIONS)
        if unknown:
            raise HTTPException(400, f"Unknown export sections: {', '.join(unknown)}")
        sections = list(dict.fromkeys(payload.sections))
        redacted_keys: list[str] = []
        entities: dict[str, Any] = {}
        for typ in sections:
            raw_rows = [obj.to_dict() for obj in database.list(typ)]
            entities[typ] = [_redact_secrets_recursive(row, redacted=redacted_keys) for row in raw_rows]
        import hashlib as _hl
        file_hashes: dict[str, str] = {}
        for typ, rows in entities.items():
            content = json.dumps(rows, ensure_ascii=False, sort_keys=True)
            file_hashes[typ] = _hl.sha256(content.encode()).hexdigest()
        result: dict[str, Any] = {
            "schema_version": "1.0.0",
            "sections": sections,
            "entities": entities,
            "file_hashes": file_hashes,
            "redacted_keys": redacted_keys,
            "omitted_secret_declaration": "Keys matching secret patterns (token, api_key, secret, password, credential, oauth, bearer, authorization, pairing_code) are replaced with [REDACTED] before hashing.",
        }
        return result

    # ── Wiki (Turn C1) ──

    @app.get("/api/wiki/pages", dependencies=[Depends(require_auth)])
    def wiki_list_pages(wiki_type: str | None = Query(default=None)):
        try:
            return wiki.list_pages(wiki_type)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/wiki/pages/{wiki_type}/{slug}", dependencies=[Depends(require_auth)])
    def wiki_read_page(wiki_type: str, slug: str):
        try:
            return wiki.read_page(wiki_type, slug)
        except FileNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.put("/api/wiki/pages/{wiki_type}/{slug}", status_code=201, dependencies=[Depends(require_auth)])
    def wiki_write_page(wiki_type: str, slug: str, payload: WikiWriteRequest):
        try:
            return wiki.write_page(wiki_type, slug, **payload.model_dump())
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/wiki/search", dependencies=[Depends(require_auth)])
    def wiki_search(q: str = Query(min_length=1)):
        return wiki.search(q)

    @app.get("/api/wiki/lint", dependencies=[Depends(require_auth)])
    def wiki_lint():
        return {"issues": wiki.lint()}

    @app.get("/api/wiki/backlinks", dependencies=[Depends(require_auth)])
    def wiki_backlinks():
        return {"backlinks": wiki.backlinks()}

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

    @app.get("/api/memory/graph", dependencies=[Depends(require_auth)])
    def memory_graph(
        query: str | None = Query(default=None),
        source: str | None = Query(default=None),
        status_filter: str | None = Query(default=None, alias="status"),
        confidence: float | None = Query(default=None, ge=0, le=1),
    ) -> dict[str, Any]:
        return build_memory_graph(database, {"query": query, "source": source, "status": status_filter, "confidence": confidence})

    @app.post("/api/memory/claims/{claim_id}/supersede", status_code=201, dependencies=[Depends(require_auth)])
    def memory_supersede(claim_id: str, payload: MemorySupersedeRequest) -> dict[str, Any]:
        try:
            return memory.supersede_claim(claim_id, **payload.model_dump()).to_dict()
        except KeyError as exc:
            raise HTTPException(404, "Memory claim not found") from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

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
        return {"replace": True, "entities": entities, "identity": harness_service.identity_docs(), **entities}

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
        identity = payload.get("identity")
        if identity is not None:
            if not isinstance(identity, dict) or set(identity) != {"soul_md", "agents_md"}:
                raise HTTPException(400, "identity inválida")
            if any(not isinstance(identity[key], str) or not identity[key].strip() or len(identity[key]) > 32768 for key in ("soul_md", "agents_md")):
                raise HTTPException(400, "capas de identidad inválidas")
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
            previous = [obj for typ in ENTITY_TYPES for obj in database.list(typ)]
            previous_identity = harness_service.identity_docs()
            database.replace_entities(prepared)
            if identity is not None:
                try:
                    harness_service.update_identity(soul_md=identity["soul_md"], agents_md=identity["agents_md"])
                except OSError as exc:
                    database.replace_entities(previous)
                    harness_service.update_identity(**previous_identity)
                    raise RuntimeError("no fue posible guardar las capas de identidad") from exc
        except (ValueError, TypeError, KeyError, RuntimeError) as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"imported": len(prepared), "identity_imported": identity is not None}

    return app


app = create_app()
