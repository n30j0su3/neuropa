from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from neuropa.domain import AgentMode, Artifact, ChatMessage, ChatSession, Database, ToolDefinition, Workspace
from neuropa.providers import NoAIProviderAvailable, ProviderRouter

PRESETS = {
    "creativity": ("Creatividad", "Explora varias posibilidades sin abrumar; ofrece pocas ideas y una forma amable de elegir.", "creative"),
    "clarity": ("Claridad", "Reduce la ambigüedad a un siguiente paso pequeño, concreto y empezable en cinco minutos.", "clarity"),
    "detail": ("Atención al detalle", "Revisa contradicciones, supuestos y edge cases con una checklist breve y accionable.", "detail"),
    "memory": ("Memoria", "Separa hechos, inferencias y preguntas abiertas; cita sólo fuentes presentes y declara cuando no hay evidencia.", "memory"),
}


def seed_defaults(db: Database) -> None:
    existing = {m.slug for m in db.list("agent_mode")}
    for slug, (name, prompt, description) in PRESETS.items():
        if slug not in existing:
            db.create(AgentMode(name=name, slug=slug, description=description, system_prompt=f"Eres NeuroPA en modo {name}. {prompt} Proceso resumido, nunca cadena de pensamiento privada."))
    if not db.list("tool_definition"):
        db.create(ToolDefinition(name="Guardar artifact", slug="artifact-write", description="Guarda un resultado local", permissions={"fs_write": "artifacts"}))


class HarnessService:
    def __init__(self, db: Database, router: ProviderRouter | None = None, data_dir: str | Path | None = None):
        self.db = db
        self.router = router or ProviderRouter()
        self.data_dir = Path(data_dir) if data_dir else db.path.parent
        (self.data_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        seed_defaults(db)

    def default_workspace(self) -> Workspace:
        rows = self.db.list("workspace")
        return rows[0] if rows else self.db.create(Workspace())  # type: ignore[return-value]

    def create_workspace(self, name: str, description: str = "", settings: dict[str, Any] | None = None) -> Workspace:
        return self.db.create(Workspace(name=name, description=description, settings=settings or {}))

    def create_session(self, title: str = "Nueva sesión", workspace_id: str | None = None, project_id: str | None = None, mode_id: str | None = None, provider_id: str | None = None, model: str = "") -> ChatSession:
        workspace = self.db.get("workspace", workspace_id) if workspace_id else self.default_workspace()
        if mode_id is None:
            clarity = next((item for item in self.db.list("agent_mode") if item.slug == "clarity"), None)
            mode_id = clarity.id if clarity else None
        return self.db.create(ChatSession(title=title, workspace_id=workspace.id if workspace else None, project_id=project_id, mode_id=mode_id, provider_id=provider_id, model=model))

    def session_messages(self, session_id: str) -> list[ChatMessage]:
        return [x for x in self.db.list("chat_message") if x.session_id == session_id][::-1]

    def send_message(self, session_id: str, content: str, mode_id: str | None = None, provider: str | None = None, model: str = "", privacy_sensitive: bool = False) -> ChatMessage:
        session = self.db.get("chat_session", session_id)
        if not session:
            raise KeyError(session_id)
        mode = self.db.get("agent_mode", mode_id) if mode_id else (self.db.get("agent_mode", session.mode_id) if session.mode_id else None)
        mode = mode or next(iter(self.db.list("agent_mode")), None)
        user = self.db.create(ChatMessage(session_id=session_id, role="user", content=content, mode_id=mode.id if mode else None, status="sent"))
        history = self.session_messages(session_id)[-12:]
        messages = ([{"role": "system", "content": mode.system_prompt}] if mode else []) + [{"role": m.role, "content": m.content} for m in history]
        try:
            result = self.router.generate(messages, mode=provider, privacy_sensitive=privacy_sensitive, model=model or session.model, workspace=str(self.data_dir))
        except Exception as exc:
            self.db.update(user, status="failed", process_summary={"objective": content, "mode": mode.slug if mode else None, "provider": provider, "sources": [], "result": "provider_unavailable"})
            raise NoAIProviderAvailable("No fue posible obtener una respuesta; tu mensaje quedó guardado") from exc
        summary = {"objective": content, "mode": mode.slug if mode else None, "provider": result.get("provider_used"), "sources": [], "result": "completed"}
        return self.db.create(ChatMessage(session_id=session_id, role="assistant", content=result.get("text", ""), provider_used=result.get("provider_used"), model=result.get("model"), mode_id=mode.id if mode else None, process_summary=summary, usage=result.get("usage", {})))

    def create_artifact(self, message_id: str) -> Artifact:
        message = self.db.get("chat_message", message_id)
        if not message or not isinstance(message, ChatMessage) or message.role != "assistant":
            raise KeyError(message_id)
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", message.content[:40]).strip("-") or "assistant-result"
        rel = Path("artifacts") / f"{message.id}-{safe}.md"
        target = self.data_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(message.content, encoding="utf-8")
        checksum = hashlib.sha256(target.read_bytes()).hexdigest()
        return self.db.create(Artifact(type="markdown", path=str(rel), blob_ref=checksum, title=safe, version=1, links={"message_id": message.id, "checksum": checksum}))
