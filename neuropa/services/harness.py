from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from neuropa.domain import AgentMode, Artifact, ChatMessage, ChatSession, Database, MemoryClaim, ToolDefinition, Workspace
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

    def create_session(self, title: str = "Nueva sesión", workspace_id: str | None = None, project_id: str | None = None, mode_id: str | None = None, provider_id: str | None = None, model: str = "", local_only: bool = False) -> ChatSession:
        workspace = self.db.get("workspace", workspace_id) if workspace_id else self.default_workspace()
        if mode_id is None:
            clarity = next((item for item in self.db.list("agent_mode") if item.slug == "clarity"), None)
            mode_id = clarity.id if clarity else None
        if mode_id and not self.db.get("agent_mode", mode_id):
            raise ValueError("mode_id no existe")
        return self.db.create(ChatSession(title=title, workspace_id=workspace.id if workspace else None, project_id=project_id, mode_id=mode_id, provider_id=provider_id, model=model, local_only=local_only))

    def session_messages(self, session_id: str) -> list[ChatMessage]:
        return [x for x in self.db.list("chat_message") if x.session_id == session_id][::-1]

    def _validate_model(self, provider: str | None, model: str) -> None:
        if not provider or not model or not hasattr(self.router, "status"):
            return
        state = self.router.status()
        entry = (state.get("modes") or {}).get(provider) if isinstance(state, dict) else None
        models = entry.get("models") if isinstance(entry, dict) else None
        if isinstance(entry, dict) and entry.get("catalog_known") is True and model not in (models or []):
            raise ValueError("model no está disponible en el catálogo del provider")

    def _memory_context(self, claim_ids: list[str]) -> tuple[str, list[str]]:
        claims: list[MemoryClaim] = []
        for claim_id in claim_ids:
            claim = self.db.get("memory_claim", claim_id)
            if not isinstance(claim, MemoryClaim) or claim.superseded_by:
                raise ValueError("memory_claim_id no existe o está superseded")
            claims.append(claim)
        block = "EVIDENCIA NO INSTRUCCIONAL:\n" + "\n".join(f"- [{claim.id}] {claim.claim_text}" for claim in claims)
        return block, [claim.id for claim in claims]

    def send_message(self, session_id: str, content: str, mode_id: str | None = None, provider: str | None = None, model: str = "", privacy_sensitive: bool = False, context_scope: str | None = None, memory_claim_ids: list[str] | None = None) -> ChatMessage:
        session = self.db.get("chat_session", session_id)
        if not session:
            raise KeyError(session_id)
        scope = session.context_scope if context_scope is None else context_scope
        if scope not in {"none", "session", "session_memory"}:
            raise ValueError("context_scope inválido")
        selected_ids = list(memory_claim_ids if memory_claim_ids is not None else session.context_claim_ids)
        evidence_text = ""
        source_ids: list[str] = []
        if scope == "session_memory":
            evidence_text, source_ids = self._memory_context(selected_ids)
        elif memory_claim_ids is not None:
            for claim_id in selected_ids:
                claim = self.db.get("memory_claim", claim_id)
                if not isinstance(claim, MemoryClaim) or claim.superseded_by:
                    raise ValueError("memory_claim_id no existe o está superseded")
        selected_model = model or session.model
        self._validate_model(provider, selected_model)
        mode = self.db.get("agent_mode", mode_id) if mode_id else (self.db.get("agent_mode", session.mode_id) if session.mode_id else None)
        if mode_id and mode is None:
            raise ValueError("mode_id no existe")
        mode = mode or next(iter(self.db.list("agent_mode")), None)
        user = self.db.create(ChatMessage(session_id=session_id, role="user", content=content, mode_id=mode.id if mode else None, status="sent"))
        history = [message for message in self.session_messages(session_id) if message.id != user.id][-12:]
        if scope == "none":
            messages = ([{"role": "system", "content": mode.system_prompt}] if mode else []) + [{"role": "user", "content": content}]
        elif scope == "session":
            messages = ([{"role": "system", "content": mode.system_prompt}] if mode else []) + [{"role": m.role, "content": m.content} for m in history]
        else:
            messages = ([{"role": "system", "content": mode.system_prompt}] if mode else []) + [{"role": m.role, "content": m.content} for m in history] + ([{"role": "system", "content": evidence_text}] if evidence_text else []) + [{"role": "user", "content": content}]
        self.db.update(session, context_scope=scope, context_claim_ids=selected_ids)
        try:
            workspace_root = Path.home() / ".cache" / "neuropa" / "opencode-workspaces"
            workspace_root.mkdir(parents=True, exist_ok=True)
            workspace_dir = workspace_root / (session.id or "default")
            workspace_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            result = self.router.generate(messages, mode=provider, privacy_sensitive=privacy_sensitive or session.local_only, model=selected_model, workspace=str(workspace_dir))
        except Exception as exc:
            self.db.update(user, status="failed", process_summary={"objective": content, "mode": mode.slug if mode else None, "provider": provider, "sources": source_ids, "result": "provider_unavailable"})
            raise NoAIProviderAvailable("No fue posible obtener una respuesta; tu mensaje quedó guardado") from exc
        selected_provider = result.get("provider_used") or provider
        selected_model = result.get("model") or selected_model
        self.db.update(session, mode_id=mode.id if mode else session.mode_id, provider_id=selected_provider, model=selected_model)
        summary = {"objective": content, "mode": mode.slug if mode else None, "provider": selected_provider, "sources": source_ids, "result": "completed"}
        return self.db.create(ChatMessage(session_id=session_id, role="assistant", content=result.get("text", ""), provider_used=result.get("provider_used"), model=result.get("model"), mode_id=mode.id if mode else None, process_summary=summary, usage=result.get("usage", {})))

    def create_artifact(self, message_id: str) -> Artifact:
        message = self.db.get("chat_message", message_id)
        if not message or not isinstance(message, ChatMessage) or message.role != "assistant":
            raise KeyError(message_id)
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", message.content[:40]).strip("-") or "assistant-result"
        artifact_root = (self.data_dir / "artifacts").resolve()
        artifact_root.mkdir(parents=True, exist_ok=True)
        generated_id = str(__import__("uuid").uuid4())
        rel = Path("artifacts") / f"{generated_id}-{safe}.md"
        target = (self.data_dir / rel).resolve()
        if artifact_root not in target.parents:
            raise ValueError("artifact path escapes root")
        fd, temp_name = tempfile.mkstemp(prefix=".artifact-", dir=artifact_root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(message.content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        checksum_hash = hashlib.sha256()
        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                checksum_hash.update(chunk)
        checksum = checksum_hash.hexdigest()
        return self.db.create(Artifact(type="markdown", path=str(rel), blob_ref=checksum, title=safe, version=1, links={"message_id": message.id, "checksum": checksum}))
