from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from neuropa.domain import Database, FocusSession, Task


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class TodayService:
    def __init__(self, db: Database):
        self.db = db

    def get_today_view(self) -> dict[str, Any]:
        pending = [t for t in self.db.list("task") if t.status == "pending"]
        mit = sorted(pending, key=lambda t: (-t.priority, t.created_at))[0] if pending else None
        rest = [t for t in pending if not mit or t.id != mit.id]
        focus = next((t for t in pending if t.focus_block), None)
        now = datetime.now(timezone.utc)
        overdue = [t for t in pending if t.due_at and _dt(t.due_at) < now]
        return {"mit": mit.to_dict() if mit else None, "focus_block": focus.to_dict() if focus else None, "parking_lot": [t.to_dict() for t in rest[:5]], "inbox_count": len(self.db.list("inbox")), "overdue_review": [t.to_dict() for t in overdue]}

    def get_recovery_flow(self) -> dict[str, Any]:
        row = self.db.conn.execute("SELECT MAX(updated_at) FROM entities WHERE deleted_at IS NULL").fetchone()
        latest = _dt(row[0]) if row and row[0] else datetime.now(timezone.utc)
        days = max(0, (datetime.now(timezone.utc) - latest).days)
        overdue = sum(1 for t in self.db.list("task") if t.due_at and _dt(t.due_at) < datetime.now(timezone.utc) and t.status not in ("completed", "cancelled"))
        if days > 3:
            return {"needs_recovery": True, "days_inactive": days, "suggestion": "recomenzar desde ahora", "overdue_items": overdue}
        return {"needs_recovery": False}

    def start(self, task_id: str) -> FocusSession:
        task = self.db.get("task", task_id)
        if not task:
            raise KeyError(task_id)
        self.db.update(task, status="in_progress")
        return self.db.create(FocusSession(task_id=task_id, outcome="running"))

    def pause(self, task_id: str) -> FocusSession:
        sessions = [s for s in self.db.list("focus_session") if s.task_id == task_id and s.outcome in ("running", "paused")]
        if not sessions:
            raise KeyError(task_id)
        return self.db.update(sessions[0], outcome="paused")  # type: ignore[arg-type]
