from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from neuropa.domain import ChatMessage, Database, MemoryClaim


def _safe_source_type(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", (value or "unknown").strip().lower()).strip("-") or "unknown"


def _safe_source_ref(value: str) -> str:
    """Return a display-safe ref; credentials/query strings never enter the graph."""
    value = (value or "").strip()
    if not value:
        return ""
    parsed = urlsplit(value)
    if parsed.scheme and parsed.netloc:
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    return re.sub(r"(?i)(token|secret|password|api[_-]?key)=([^&\s]+)", r"\1=[redacted]", value)


def normalize_source_node(source_type: str, source_ref: str) -> dict[str, Any]:
    safe_type = _safe_source_type(source_type)
    canonical_ref = _safe_source_ref(source_ref)
    digest = hashlib.sha256(f"{safe_type}\0{canonical_ref}".encode("utf-8")).hexdigest()[:24]
    return {
        "id": f"source:{safe_type}:{digest}",
        "type": "source",
        "source_type": safe_type,
        "source_ref": canonical_ref,
        "label": canonical_ref or safe_type,
    }


def claim_status(claim: MemoryClaim) -> str:
    if claim.superseded_by:
        return "superseded"
    return "active" if claim.source_ref else "orphan"


def _claim_matches(claim: MemoryClaim, filters: dict[str, Any]) -> bool:
    query = str(filters.get("query") or "").strip().lower()
    source = str(filters.get("source") or "").strip().lower()
    status = str(filters.get("status") or "").strip().lower()
    confidence = filters.get("confidence")
    if query and query not in claim.claim_text.lower():
        return False
    if source and source not in {claim.source_type.lower(), claim.source_ref.lower()}:
        return False
    if status and claim_status(claim) != status:
        return False
    if confidence is not None and claim.confidence < float(confidence):
        return False
    return True


def _source_matches(marker: Any, claim: MemoryClaim, source_node: dict[str, Any]) -> bool:
    if isinstance(marker, dict):
        marker = marker.get("claim_id") or marker.get("id") or marker.get("source_ref")
    if not isinstance(marker, str):
        return False
    return marker in {claim.id, claim.source_ref, source_node["id"]}


def build_memory_graph(db: Database, filters: dict[str, Any] | None = None) -> dict[str, list[dict[str, Any]]]:
    filters = filters or {}
    claims = [c for c in db.list("memory_claim") if isinstance(c, MemoryClaim) and _claim_matches(c, filters)]
    claim_ids = {claim.id for claim in claims}
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    for claim in claims:
        status = claim_status(claim)
        node = {
            "id": f"claim:{claim.id}",
            "type": "claim",
            "label": claim.claim_text,
            "status": status,
            "confidence": claim.confidence,
            "claim_text": claim.claim_text,
            "source_type": claim.source_type,
            "source_ref": _safe_source_ref(claim.source_ref),
            "created_at": claim.created_at,
        }
        nodes.append(node)
        if claim.source_ref:
            source = normalize_source_node(claim.source_type, claim.source_ref)
            if source["id"] not in source_ids:
                nodes.append(source)
                source_ids.add(source["id"])
            edges.append({"source": node["id"], "target": source["id"], "type": "sourced_from"})
        if claim.superseded_by and claim.superseded_by in claim_ids:
            edges.append({"source": f"claim:{claim.superseded_by}", "target": node["id"], "type": "supersedes"})

    sessions: dict[str, list[str]] = {}
    for message in db.list("chat_message"):
        if not isinstance(message, ChatMessage) or not message.process_summary:
            continue
        markers = message.process_summary.get("sources")
        if not isinstance(markers, list):
            continue
        for claim in claims:
            source = normalize_source_node(claim.source_type, claim.source_ref) if claim.source_ref else {"id": ""}
            if any(_source_matches(marker, claim, source) for marker in markers):
                sessions.setdefault(message.session_id, []).append(claim.id)
    for session_id, used_claim_ids in sessions.items():
        if not db.get("chat_session", session_id):
            continue
        session_node = {"id": f"session:{session_id}", "type": "session", "label": session_id}
        if session_node["id"] not in {n["id"] for n in nodes}:
            nodes.append(session_node)
        for claim_id in sorted(set(used_claim_ids)):
            edges.append({"source": f"claim:{claim_id}", "target": session_node["id"], "type": "used_in_session"})
    return {"nodes": nodes, "edges": edges}
