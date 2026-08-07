from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any

from neuropa.domain import AgentMode, AgentProfile, Artifact, ChatMessage, ChatSession, Database, MemoryClaim, ToolDefinition, Workspace
from neuropa.providers import NoAIProviderAvailable, ProviderRouter

PRESETS = {
    "creativity": ("Creatividad", "Explora varias posibilidades sin abrumar; ofrece pocas ideas y una forma amable de elegir.", "creative"),
    "clarity": ("Claridad", "Reduce la ambigüedad a un siguiente paso pequeño, concreto y empezable en cinco minutos.", "clarity"),
    "detail": ("Atención al detalle", "Revisa contradicciones, supuestos y edge cases con una checklist breve y accionable.", "detail"),
    "memory": ("Memoria", "Separa hechos, inferencias y preguntas abiertas; cita sólo fuentes presentes y declara cuando no hay evidencia.", "memory"),
}

RESPONSE_CONTRACT = (
    "Responde primero a la solicitud literal del último mensaje del usuario. "
    "El modo sólo modifica el enfoque o formato; nunca sustituye la tarea ni responde a un mensaje anterior. "
    "Sé conciso salvo que el usuario pida profundidad."
)

IDENTITY_DEFAULTS = {
    "SOUL.md": "# SOUL\nNeuroPA es un espacio local, sereno y transparente para pensar, crear y conservar contexto.\n",
    "AGENTS.md": "# AGENTS\nPrioriza la solicitud literal actual, evidencia verificable, privacidad y acciones reversibles.\n",
}


def _title_from_first_message(text: str, limit: int = 60) -> str:
    normalized = " ".join(text.split()).strip(" .,:;!_-")
    if not normalized:
        return "Nueva sesión"
    if len(normalized) <= limit:
        return normalized
    prefix = normalized[: limit + 1]
    bounded = prefix.rsplit(" ", 1)[0].strip()
    return bounded or normalized[:limit].strip()


DELIVERABLE_SUFFIXES = {".html", ".htm", ".md", ".markdown", ".txt", ".css", ".js", ".py", ".json", ".svg", ".csv"}
DELIVERABLE_MAX_BYTES = 2 * 1024 * 1024


def _snapshot_workspace(workspace_dir: Path) -> dict[str, float]:
    """Map of relative file paths -> mtime before generation runs."""
    snapshot: dict[str, float] = {}
    try:
        for path in workspace_dir.rglob("*"):
            if path.is_file() and not any(part.startswith(".") for part in path.parts):
                snapshot[str(path.relative_to(workspace_dir))] = path.stat().st_mtime
    except OSError:
        pass
    return snapshot


def seed_defaults(db: Database) -> None:
    existing = {m.slug for m in db.list("agent_mode")}
    for slug, (name, prompt, description) in PRESETS.items():
        if slug not in existing:
            db.create(AgentMode(name=name, slug=slug, description=description, system_prompt=f"Eres NeuroPA en modo {name}. {prompt} Proceso resumido, nunca cadena de pensamiento privada."))
    if not db.list("tool_definition"):
        db.create(ToolDefinition(name="Guardar artifact", slug="artifact-write", description="Guarda un resultado local", permissions={"fs_write": "artifacts"}))
    _seed_default_agent_profile(db)


def _seed_default_agent_profile(db: Database) -> None:
    existing = [p for p in db.list("agent_profile") if p.is_primary]
    if not existing:
        db.create(AgentProfile(
            name="NeuroPA",
            display_name="NeuroPA",
            system_prompt="Eres NeuroPA, un espacio local para pensar y capturar. Hablas español, eres directo y nunca fabricas datos. Si no tienes evidencia, lo dices.",
            default_provider="opencode_free",
            temperature=0.5,
            is_primary=True,
        ))


class HarnessService:
    def __init__(self, db: Database, router: ProviderRouter | None = None, data_dir: str | Path | None = None):
        self.db = db
        self.router = router or ProviderRouter()
        self.data_dir = Path(data_dir) if data_dir else db.path.parent
        (self.data_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        self.identity_dir = self.data_dir / "identity"
        self.identity_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in IDENTITY_DEFAULTS.items():
            path = self.identity_dir / filename
            if not path.exists():
                path.write_text(content, encoding="utf-8")
        seed_defaults(db)

    def default_workspace(self) -> Workspace:
        rows = self.db.list("workspace")
        return rows[0] if rows else self.db.create(Workspace())  # type: ignore[return-value]

    # ── AgentProfile ──

    def primary_profile(self) -> AgentProfile | None:
        for p in self.db.list("agent_profile"):
            if p.is_primary:
                return p
        return None

    def update_profile(self, profile_id: str, **kwargs: Any) -> AgentProfile:
        profile = self.db.get("agent_profile", profile_id)
        if not profile:
            raise KeyError(profile_id)
        allowed = {"name", "display_name", "system_prompt", "default_provider", "default_mode_id", "temperature"}
        clean = {k: v for k, v in kwargs.items() if k in allowed}
        return self.db.update(profile, **clean)

    def _profile_system_prompt(self) -> str:
        profile = self.primary_profile()
        return profile.system_prompt if profile and profile.system_prompt else ""

    def identity_docs(self) -> dict[str, str]:
        return {
            "soul_md": (self.identity_dir / "SOUL.md").read_text(encoding="utf-8"),
            "agents_md": (self.identity_dir / "AGENTS.md").read_text(encoding="utf-8"),
        }

    def update_identity(self, *, soul_md: str, agents_md: str) -> dict[str, str]:
        for filename, content in {"SOUL.md": soul_md, "AGENTS.md": agents_md}.items():
            normalized = content.rstrip() + "\n"
            target = self.identity_dir / filename
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.identity_dir, prefix=f".{filename}.", delete=False) as handle:
                handle.write(normalized)
                temp_path = Path(handle.name)
            os.chmod(temp_path, 0o600)
            temp_path.replace(target)
        return self.identity_docs()

    def _identity_system_prompt(self) -> str:
        docs = self.identity_docs()
        return (
            "CAPAS PERMANENTES DEL AGENTE (configuradas por el propietario):\n"
            f"[SOUL.md]\n{docs['soul_md'].strip()}\n\n"
            f"[AGENTS.md]\n{docs['agents_md'].strip()}\n\n"
            "La solicitud literal actual del usuario tiene prioridad sobre estas capas, el perfil y el modo."
        )

    def create_workspace(self, name: str, description: str = "", settings: dict[str, Any] | None = None) -> Workspace:
        return self.db.create(Workspace(name=name, description=description, settings=settings or {}))

    def create_session(self, title: str = "Nueva sesión", workspace_id: str | None = None, project_id: str | None = None, mode_id: str | None = None, provider_id: str | None = None, model: str = "", local_only: bool = False) -> ChatSession:
        workspace = self.db.get("workspace", workspace_id) if workspace_id else self.default_workspace()
        profile = self.primary_profile()
        if mode_id is None:
            if profile and profile.default_mode_id:
                mode_id = profile.default_mode_id
            else:
                clarity = next((item for item in self.db.list("agent_mode") if item.slug == "clarity"), None)
                mode_id = clarity.id if clarity else None
        if provider_id is None and profile and profile.default_provider:
            provider_id = profile.default_provider
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
        profile = self.primary_profile()
        resolved_provider = provider or session.provider_id or (profile.default_provider if profile else None)
        self._validate_model(resolved_provider, selected_model)
        mode = self.db.get("agent_mode", mode_id) if mode_id else (self.db.get("agent_mode", session.mode_id) if session.mode_id else None)
        if mode_id and mode is None:
            raise ValueError("mode_id no existe")
        mode = mode or next(iter(self.db.list("agent_mode")), None)
        identity_prompt = self._identity_system_prompt()
        profile_prompt = self._profile_system_prompt()
        system_prompt = (identity_prompt + "\n" + profile_prompt + "\n" + (getattr(mode, "system_prompt", "") if mode else "") + "\n" + RESPONSE_CONTRACT).strip()
        user = self.db.create(ChatMessage(session_id=session_id, role="user", content=content, mode_id=mode.id if mode else None, status="sent"))
        if session.title in ("", "Nueva sesión") and not [m for m in self.session_messages(session_id) if m.id != user.id and m.role == "user"]:
            self.db.update(session, title=_title_from_first_message(content))
        history = [
            message
            for message in self.session_messages(session_id)
            if message.id != user.id
            and message.role in {"user", "assistant"}
            and message.status != "failed"
        ][-12:]
        current = {"role": "user", "content": content}
        if scope == "none":
            messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + [current]
        elif scope == "session":
            messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + [{"role": m.role, "content": m.content} for m in history] + [current]
        else:
            messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + [{"role": m.role, "content": m.content} for m in history] + ([{"role": "system", "content": evidence_text}] if evidence_text else []) + [current]
        self.db.update(session, context_scope=scope, context_claim_ids=selected_ids)
        start_time = time.perf_counter()
        try:
            workspace_root = Path.home() / ".cache" / "neuropa" / "opencode-workspaces"
            workspace_root.mkdir(parents=True, exist_ok=True)
            workspace_dir = workspace_root / (session.id or "default")
            workspace_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            workspace_snapshot = _snapshot_workspace(workspace_dir)
            result = self.router.generate(messages, mode=resolved_provider, privacy_sensitive=privacy_sensitive or session.local_only, model=selected_model, workspace=str(workspace_dir))
        except Exception as exc:
            self.db.update(user, status="failed", process_summary={**{"objective": content, "mode": mode.slug if mode else None, "provider": resolved_provider, "sources": source_ids, "result": "provider_unavailable"}})
            raise NoAIProviderAvailable("No fue posible obtener una respuesta; tu mensaje quedó guardado") from exc
        selected_provider = result.get("provider_used") or resolved_provider
        selected_model = result.get("model") or selected_model
        usage = dict(result.get("usage") or {})
        elapsed = max(time.perf_counter() - start_time, 0.0)
        if "elapsed" not in usage:
            try:
                if "elapsed_ms" in usage:
                    usage["elapsed"] = round(float(usage["elapsed_ms"]) / 1000, 3)
                elif "duration" in usage:
                    usage["elapsed"] = round(float(usage["duration"]), 3)
                else:
                    usage["elapsed"] = round(elapsed, 3)
            except (TypeError, ValueError):
                usage["elapsed"] = round(elapsed, 3)
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        if input_tokens is None and "prompt_tokens" in usage:
            input_tokens = usage.get("prompt_tokens")
        if output_tokens is None and "completion_tokens" in usage:
            output_tokens = usage.get("completion_tokens")
        if input_tokens is not None:
            try:
                usage["input_tokens"] = int(input_tokens)
            except (TypeError, ValueError):
                usage.pop("input_tokens", None)
        if output_tokens is not None:
            try:
                usage["output_tokens"] = int(output_tokens)
            except (TypeError, ValueError):
                usage.pop("output_tokens", None)
        if usage.get("elapsed") and usage.get("output_tokens", 0):
            try:
                usage["output_tokens_per_sec"] = round(float(usage["output_tokens"]) / float(usage["elapsed"]), 2)
            except Exception:
                pass
        self.db.update(session, mode_id=mode.id if mode else session.mode_id, provider_id=selected_provider, model=selected_model)
        summary = {"objective": content, "mode": mode.slug if mode else None, "provider": selected_provider, "sources": source_ids, "result": "completed"}
        message = self.db.create(
            ChatMessage(
                session_id=session_id,
                role="assistant",
                content=result.get("text", ""),
                provider_used=result.get("provider_used"),
                model=result.get("model"),
                mode_id=mode.id if mode else None,
                process_summary=summary,
                usage=usage,
            )
        )
        deliverables = self._capture_workspace_deliverables(workspace_dir, workspace_snapshot, message)
        if deliverables:
            summary["deliverables"] = deliverables
            self.db.update(message, process_summary=summary)
        self._auto_extract_memory(content, message)
        return message

    def _auto_extract_memory(self, user_content: str, assistant_message: ChatMessage) -> None:
        """Extract memory claims from natural language 'recuerda que...' patterns.

        The user should not need to know about the /api/memory/store endpoint.
        If they say 'recuerda que X' or 'remember that X', we extract X and
        persist it as a grounded claim with the session as source.
        """
        import re as _re
        text = user_content.strip()
        patterns = [
            r"(?:recuerda\s+que|recordá\s+que|recuerde\s+que)\s+(.+)",
            r"(?:remember\s+that)\s+(.+)",
            r"(?:memoriz[ao]\s+(?:que\s+)?|guarda\s+(?:en\s+memoria\s+)?(?:que\s+)?)\s*(.+)",
        ]
        claim_text = None
        for pat in patterns:
            m = _re.search(pat, text, _re.IGNORECASE)
            if m:
                claim_text = m.group(1).strip().rstrip(".")
                break
        if not claim_text or len(claim_text) < 5:
            return
        try:
            from neuropa.memory import MemoryClaimService
            source_ref = f"sesión {assistant_message.session_id}"
            MemoryClaimService(self.db).store_claim(claim_text=claim_text, source_type="chat", source_ref=source_ref, confidence=0.85)
        except Exception:
            pass

    def _capture_workspace_deliverables(self, workspace_dir: Path, before: dict[str, float], message: ChatMessage) -> list[dict[str, str]]:
        """Register files the provider wrote into the session workspace as
        first-class Artifacts so the user can preview/download them from the chat."""
        deliverables: list[dict[str, str]] = []
        artifact_root = (self.data_dir / "artifacts").resolve()
        artifact_root.mkdir(parents=True, exist_ok=True)
        candidates: list[tuple[str, Path]] = []
        try:
            for path in sorted(workspace_dir.rglob("*")):
                if not path.is_file():
                    continue
                try:
                    rel = str(path.relative_to(workspace_dir))
                except ValueError:
                    continue
                if any(part.startswith(".") for part in Path(rel).parts):
                    continue
                if path.suffix.lower() not in DELIVERABLE_SUFFIXES:
                    continue
                try:
                    stat = path.stat()
                except OSError:
                    continue
                if stat.st_size == 0 or stat.st_size > DELIVERABLE_MAX_BYTES:
                    continue
                if rel in before and stat.st_mtime <= before[rel]:
                    continue
                candidates.append((rel, path))
        except OSError:
            return deliverables
        for rel, path in candidates[:5]:
            suffix = path.suffix.lower()
            kind = "html" if suffix in (".html", ".htm") else ("markdown" if suffix in (".md", ".markdown") else "code")
            safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", Path(rel).name).strip("-") or f"entregable{suffix}"
            generated_id = str(__import__("uuid").uuid4())
            rel_target = Path("artifacts") / f"{generated_id}-{safe}"
            target = (self.data_dir / rel_target).resolve()
            if artifact_root not in target.parents:
                continue
            temp_name = ""
            try:
                fd, temp_name = tempfile.mkstemp(prefix=".artifact-", dir=artifact_root)
                checksum_hash = hashlib.sha256()
                with os.fdopen(fd, "wb") as handle, path.open("rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        checksum_hash.update(chunk)
                        handle.write(chunk)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, target)
            except OSError:
                if temp_name and os.path.exists(temp_name):
                    os.unlink(temp_name)
                continue
            checksum = checksum_hash.hexdigest()
            artifact = self.db.create(Artifact(
                type=kind,
                path=str(rel_target),
                blob_ref=checksum,
                title=Path(rel).name,
                version=1,
                links={"message_id": message.id, "session_id": message.session_id, "checksum": checksum, "origin": "workspace", "workspace_path": rel},
            ))
            deliverables.append({"id": artifact.id, "title": artifact.title, "type": kind})
        return deliverables

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

    def read_artifact(self, artifact_id: str) -> dict[str, Any]:
        artifact = self.db.get("artifact", artifact_id)
        if not artifact or not isinstance(artifact, Artifact):
            raise KeyError(artifact_id)
        artifact_root = (self.data_dir / "artifacts").resolve()
        target = (self.data_dir / artifact.path).resolve()
        if artifact_root not in target.parents and target != artifact_root:
            raise ValueError("artifact path escapes root")
        if not target.is_file():
            raise FileNotFoundError(str(target))
        if target.suffix.lower() not in (".md", ".markdown", ".txt", ".html", ".htm", ".css", ".js", ".py", ".json", ".svg", ".csv"):
            raise ValueError("artifact type not readable")
        if target.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("artifact exceeds 2 MiB read limit")
        try:
            content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("artifact content is not valid UTF-8") from exc
        result = artifact.to_dict()
        result["content"] = content
        result["checksum"] = artifact.blob_ref or artifact.links.get("checksum")
        message_id = artifact.links.get("message_id")
        message = self.db.get("chat_message", message_id) if message_id else None
        session = self.db.get("chat_session", message.session_id) if isinstance(message, ChatMessage) else None
        result["source_session"] = session.title if isinstance(session, ChatSession) else None
        return result

    MEDIA_BY_SUFFIX = {
        ".html": "text/html", ".htm": "text/html", ".md": "text/markdown", ".markdown": "text/markdown",
        ".txt": "text/plain", ".css": "text/css", ".js": "text/javascript", ".py": "text/x-python",
        ".json": "application/json", ".svg": "image/svg+xml", ".csv": "text/csv",
    }

    def artifact_file(self, artifact_id: str) -> tuple[Path, str, str]:
        """Resolve an artifact to (safe_path, media_type, download_name) for raw serving."""
        artifact = self.db.get("artifact", artifact_id)
        if not artifact or not isinstance(artifact, Artifact):
            raise KeyError(artifact_id)
        artifact_root = (self.data_dir / "artifacts").resolve()
        target = (self.data_dir / artifact.path).resolve()
        if artifact_root not in target.parents and target != artifact_root:
            raise ValueError("artifact path escapes root")
        if not target.is_file():
            raise FileNotFoundError(str(target))
        media = self.MEDIA_BY_SUFFIX.get(target.suffix.lower(), "application/octet-stream")
        return target, media, artifact.title or target.name
