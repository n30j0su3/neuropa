"""Regression: grounded-memory retrieval must answer natural-language questions.

The previous ALL-terms-substring rule failed real queries like
"que provider gratuito usa NeuroPA" because stopwords ("que") never appear
inside claims — breaking NeuroPA's anti-hallucination pillar.
"""

from neuropa.domain import Database
from neuropa.memory import MemoryClaimService


def _service(tmp_path):
    db = Database(tmp_path / "test.db")
    db.migrate()
    return MemoryClaimService(db)


def test_natural_language_query_finds_claim(tmp_path):
    svc = _service(tmp_path)
    svc.store_claim(
        claim_text="NeuroPA usa OpenCode como provider gratuito por defecto",
        source_type="note", source_ref="validacion",
        confidence=0.95,
    )
    found = svc.search_claims("que provider gratuito usa NeuroPA")
    assert found, "natural-language question must retrieve the stored claim"
    assert "OpenCode" in found[0].claim_text


def test_unrelated_query_returns_no_evidence(tmp_path):
    svc = _service(tmp_path)
    svc.store_claim(claim_text="NeuroPA usa OpenCode como provider gratuito por defecto", source_type="note", source_ref="x", confidence=0.9)
    assert svc.search_claims("precio suscripcion enterprise") == []
    answer = svc.answer_with_evidence("precio suscripcion enterprise")
    assert answer["source"] is None
    assert "No tengo evidencia" in answer["answer"]


def test_stopword_only_query_falls_back_to_recent_claims(tmp_path):
    svc = _service(tmp_path)
    svc.store_claim(claim_text="dato uno", source_type="note", source_ref="t", confidence=0.4)
    svc.store_claim(claim_text="dato dos", source_type="note", source_ref="t", confidence=0.9)
    found = svc.search_claims("que es")
    assert found and found[0].claim_text == "dato dos"


def test_superseded_claims_are_not_retrieved(tmp_path):
    svc = _service(tmp_path)
    old = svc.store_claim(claim_text="OpenRouter es el provider por defecto", source_type="note", source_ref="t", confidence=0.9)
    svc.supersede_claim(old.id, claim_text="OpenCode es el provider por defecto", source_type="note", source_ref="t", confidence=0.9)
    assert all("OpenRouter" not in c.claim_text for c in svc.search_claims("provider defecto"))
