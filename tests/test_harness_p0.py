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
