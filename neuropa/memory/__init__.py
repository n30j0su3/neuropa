from __future__ import annotations

from typing import Any
from neuropa.domain import Database, MemoryClaim
from .graph import build_memory_graph, claim_status, normalize_source_node


_MEMORY_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al", "a", "en", "con",
    "por", "para", "que", "es", "son", "y", "o", "u", "se", "su", "sus", "mi", "mis", "tu", "tus",
    "sobre", "como", "cual", "cuales", "quien", "donde", "cuando", "tiene", "tengo",
    "the", "an", "of", "to", "in", "on", "for", "is", "are", "was", "were", "with", "and",
    "or", "my", "your", "what", "which", "who", "how", "does", "do",
}


class MemoryClaimService:
    def __init__(self, db: Database, wiki=None):
        self.db = db
        self.wiki = wiki

    def _wiki_slug(self, text: str) -> str:
        import re as _re
        slug = _re.sub(r"[^a-z0-9]+", "-", text.lower().strip())[:60].strip("-")
        return slug or "claim"

    def _sync_wiki(self, claim: MemoryClaim) -> None:
        if not self.wiki:
            return
        try:
            slug = self._wiki_slug(claim.claim_text)
            title = claim.claim_text[:80] + ("…" if len(claim.claim_text) > 80 else "")
            body = f"# {title}\n\n- **Claim:** {claim.claim_text}\n- **Fuente:** {claim.source_ref or 'no declarada'}\n- **Confianza:** {round(claim.confidence * 100)}%\n- **Fecha:** {claim.created_at}\n- **Estado:** {getattr(claim, 'status', 'active')}\n"
            self.wiki.write_page("note", slug, title=title, body=body, tags=["memory", "auto"])
        except Exception:
            pass

    def store_claim(self, claim_text: str, source_type: str, source_ref: str, confidence: float = 0.5) -> MemoryClaim:
        claim = self.db.create(MemoryClaim(claim_text=claim_text, source_type=source_type, source_ref=source_ref, confidence=max(0.0, min(1.0, confidence))))
        self._sync_wiki(claim)
        return claim

    def search_claims(self, query: str, limit: int = 5) -> list[MemoryClaim]:
        # Token-overlap retrieval: natural-language questions ("que provider
        # gratuito usa NeuroPA") must find claims even when not every word
        # appears in the claim. Stopwords and very short tokens are ignored;
        # a claim needs a meaningful share of the remaining terms to match.
        terms = [t.lower() for t in query.split() if t and t.lower() not in _MEMORY_STOPWORDS and len(t) > 2]
        claims = [c for c in self.db.list("memory_claim") if isinstance(c, MemoryClaim) and not c.superseded_by]
        if not terms:
            claims.sort(key=lambda c: (c.confidence, c.created_at), reverse=True)
            return claims[:limit]
        scored: list[tuple[float, MemoryClaim]] = []
        for claim in claims:
            text = claim.claim_text.lower()
            hits = sum(1 for t in terms if t in text)
            if hits:
                scored.append((hits / len(terms), claim))
        scored.sort(key=lambda item: (item[0], item[1].confidence, item[1].created_at), reverse=True)
        threshold = 0.34 if len(terms) > 2 else 0.0
        return [claim for score, claim in scored if score >= threshold][:limit]

    def supersede(self, old_id: str, new_claim_id: str) -> MemoryClaim:
        old = self.db.get("memory_claim", old_id)
        new = self.db.get("memory_claim", new_claim_id)
        if not old or not new:
            raise KeyError(old_id if not old else new_claim_id)
        if getattr(old, "superseded_by", None):
            raise ValueError("claim is already superseded")
        return self.db.update(old, superseded_by=new_claim_id)  # type: ignore[arg-type]

    def supersede_claim(self, old_id: str, *, claim_text: str, source_type: str = "note", source_ref: str = "", confidence: float = 0.5) -> MemoryClaim:
        old = self.db.get("memory_claim", old_id)
        if not old:
            raise KeyError(old_id)
        if getattr(old, "superseded_by", None):
            raise ValueError("claim is already superseded")
        new = MemoryClaim(claim_text=claim_text, source_type=source_type, source_ref=source_ref, confidence=max(0.0, min(1.0, confidence)))
        result = self.db.supersede(old_id, new)
        self._sync_wiki(result)
        return result

    def answer_with_evidence(self, query: str) -> dict[str, Any]:
        found = self.search_claims(query, limit=1)
        if not found:
            return {"answer": "No tengo evidencia sobre eso todavía.", "source": None, "confidence": 0, "stored_at": None}
        claim = found[0]
        return {"answer": claim.claim_text, "source": claim.source_ref, "confidence": claim.confidence, "stored_at": claim.created_at}
