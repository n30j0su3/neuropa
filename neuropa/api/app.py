from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from neuropa.core.providers.multi_engine import MockEngine
from neuropa.domain import Database, InboxItem, default_data_dir


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


def create_app(db: Database | None = None) -> FastAPI:
    database = db or Database()
    get_token()
    app = FastAPI(title="NeuroPA Local API", version="0.1.0")
    bearer = HTTPBearer(auto_error=False)

    async def require_auth(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
        if not credentials or credentials.scheme.lower() != "bearer" or not secrets.compare_digest(credentials.credentials, get_token()):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required", headers={"WWW-Authenticate": "Bearer"})

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
        engine = MockEngine()
        return {"overall_healthy": engine.health(), "engines": {"mock": {"healthy": True, "models": engine.list_models()}}}

    return app


app = create_app()
