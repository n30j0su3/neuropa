from __future__ import annotations

from typing import Any
from neuropa.domain import Database, MemoryClaim


class MemoryClaimService:
    def __init__(self, db: Database):
        self.db = db

    def store_claim(self, claim_text: str, source_type: str, source_ref: str, confidence: float = 0.5) -> MemoryClaim:
        return self.db.create(MemoryClaim(claim_text=claim_text, source_type=source_type, source_ref=source_ref, confidence=max(0.0, min(1.0, confidence))))

    def search_claims(self, query: str, limit: int = 5) -> list[MemoryClaim]:
        terms = [t.lower() for t in query.split() if t]
        claims = [c for c in self.db.list("memory_claim") if not c.superseded_by and all(t in c.claim_text.lower() for t in terms)]
        claims.sort(key=lambda c: c.created_at, reverse=True)
        claims.sort(key=lambda c: c.confidence, reverse=True)
        return claims[:limit]

    def supersede(self, old_id: str, new_claim_id: str) -> MemoryClaim:
        old = self.db.get("memory_claim", old_id)
        new = self.db.get("memory_claim", new_claim_id)
        if not old or not new:
            raise KeyError(old_id if not old else new_claim_id)
        return self.db.update(old, superseded_by=new_claim_id)  # type: ignore[arg-type]

    def answer_with_evidence(self, query: str) -> dict[str, Any]:
        found = self.search_claims(query, limit=1)
        if not found:
            return {"answer": "No tengo evidencia sobre eso todavía.", "source": None, "confidence": 0, "stored_at": None}
        claim = found[0]
        return {"answer": claim.claim_text, "source": claim.source_ref, "confidence": claim.confidence, "stored_at": claim.created_at}
