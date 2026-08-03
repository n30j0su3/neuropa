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
