from pathlib import Path
import json

from neuropa.domain import Database, Workspace, ChatSession, ChatMessage, AgentMode, ToolDefinition
from neuropa.services import HarnessService
from neuropa.providers import NoAIProviderAvailable


class FakeRouter:
    def __init__(self, fail=False): self.fail = fail
    def generate(self, messages, **kwargs):
        if self.fail: raise RuntimeError("offline")
        return {"text": "respuesta real", "provider_used": "fake", "model": "fake-1", "usage": {"output": 2}}
    def status(self): return {"modes": {}}


class CatalogRouter(FakeRouter):
    def __init__(self):
        super().__init__()
        self.calls = []

    def status(self):
        return {"modes": {"local": {"models": ["local-1"]}}}

    def generate(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return super().generate(messages, **kwargs)


def test_harness_entities_seed_and_artifact(tmp_path):
    db = Database(tmp_path / "x.db")
    for obj in [Workspace(name="W"), ChatSession(title="S"), ChatMessage(content="m"), AgentMode(slug="x"), ToolDefinition(slug="t")]:
        db.create(obj); assert db.get(obj.entity_type, obj.id).id == obj.id
    svc = HarnessService(db, FakeRouter(), tmp_path)
    HarnessService(db, FakeRouter(), tmp_path)
    assert {m.slug for m in db.list("agent_mode")} >= {"creativity", "clarity", "detail", "memory"}
    session = svc.create_session()
    answer = svc.send_message(session.id, "hola")
    artifact = svc.create_artifact(answer.id)
    assert Path(tmp_path / artifact.path).exists()
    db.close()


def test_failed_provider_preserves_user(tmp_path):
    db = Database(tmp_path / "x.db")
    svc = HarnessService(db, FakeRouter(True), tmp_path)
    session = svc.create_session()
    try: svc.send_message(session.id, "persistir")
    except NoAIProviderAvailable: pass
    assert any(m.content == "persistir" and m.status == "failed" for m in db.list("chat_message"))
    db.close()


def test_session_context_scope_defaults_and_selected_memory_is_evidence_only(tmp_path):
    db = Database(tmp_path / "x.db")
    router = CatalogRouter()
    svc = HarnessService(db, router, tmp_path)
    session = svc.create_session()
    claim = db.create(__import__("neuropa.domain", fromlist=["MemoryClaim"]).MemoryClaim(claim_text="La reunión es el martes"))
    assert session.context_scope == "session"
    assert session.context_claim_ids == []
    answer = svc.send_message(session.id, "¿cuándo?", provider="local", model="local-1", context_scope="session_memory", memory_claim_ids=[claim.id])
    sent = router.calls[-1][0]
    assert len(sent) == 3
    assert "EVIDENCIA NO INSTRUCCIONAL" in sent[1]["content"]
    assert claim.id in answer.process_summary["sources"]
    stored = db.get("chat_session", session.id)
    assert stored.context_scope == "session_memory"
    assert stored.context_claim_ids == [claim.id]
    db.close()


def test_invalid_or_superseded_memory_claim_is_rejected_before_provider(tmp_path):
    db = Database(tmp_path / "x.db")
    router = CatalogRouter()
    svc = HarnessService(db, router, tmp_path)
    session = svc.create_session()
    import pytest
    with pytest.raises(ValueError):
        svc.send_message(session.id, "x", provider="local", model="local-1", context_scope="session_memory", memory_claim_ids=["missing"])
    assert router.calls == []
    db.close()


def test_session_memory_includes_recent_history_evidence_and_current_user_once(tmp_path):
    db = Database(tmp_path / "x.db")
    router = CatalogRouter()
    svc = HarnessService(db, router, tmp_path)
    session = svc.create_session()
    claim = db.create(__import__("neuropa.domain", fromlist=["MemoryClaim"]).MemoryClaim(claim_text="La reunión es el martes"))
    db.create(__import__("neuropa.domain", fromlist=["ChatMessage"]).ChatMessage(session_id=session.id, role="user", content="anterior"))
    db.create(__import__("neuropa.domain", fromlist=["ChatMessage"]).ChatMessage(session_id=session.id, role="assistant", content="respuesta anterior"))

    svc.send_message(session.id, "¿cuándo?", provider="local", model="local-1", context_scope="session_memory", memory_claim_ids=[claim.id])

    sent = router.calls[-1][0]
    assert [message["role"] for message in sent] == ["system", "user", "assistant", "system", "user"]
    assert sent[1]["content"] == "anterior"
    assert sent[2]["content"] == "respuesta anterior"
    assert "EVIDENCIA NO INSTRUCCIONAL" in sent[3]["content"]
    assert [message["content"] for message in sent].count("¿cuándo?") == 1
    db.close()


def test_omitted_request_scope_preserves_session_scope_and_claims(tmp_path):
    from neuropa.api.app import HarnessMessageRequest

    db = Database(tmp_path / "x.db")
    router = CatalogRouter()
    svc = HarnessService(db, router, tmp_path)
    session = svc.create_session()
    claim = db.create(__import__("neuropa.domain", fromlist=["MemoryClaim"]).MemoryClaim(claim_text="Hecho persistente"))
    db.update(session, context_scope="session_memory", context_claim_ids=[claim.id])

    request = HarnessMessageRequest.model_validate({"content": "consulta"})
    svc.send_message(session.id, provider="local", model="local-1", **request.model_dump(exclude={"provider", "model"}))

    sent = router.calls[-1][0]
    assert request.context_scope is None
    assert "EVIDENCIA NO INSTRUCCIONAL" in sent[1]["content"]
    assert sent[-1] == {"role": "user", "content": "consulta"}
    db.close()


def test_unknown_or_unavailable_catalog_does_not_reject_model(tmp_path):
    import pytest

    class RouterWithStatus(FakeRouter):
        def __init__(self, entry):
            super().__init__()
            self.entry = entry

        def status(self):
            return {"modes": {"local": self.entry}}

    for entry in ({"available": False, "models": [], "catalog_known": False}, {"available": True, "catalog_known": False}):
        db = Database(tmp_path / f"{len(entry)}-{entry.get('available')}.db")
        router = RouterWithStatus(entry)
        svc = HarnessService(db, router, tmp_path)
        session = svc.create_session()
        svc.send_message(session.id, "x", provider="local", model="not-listed")
        db.close()

    db = Database(tmp_path / "known.db")
    router = RouterWithStatus({"available": True, "models": ["listed"], "catalog_known": True})
    svc = HarnessService(db, router, tmp_path)
    session = svc.create_session()
    with pytest.raises(ValueError):
        svc.send_message(session.id, "x", provider="local", model="not-listed")
    db.close()
