from __future__ import annotations

import json
import os
import sys
import sqlite3
import threading
from pathlib import Path
from typing import Any, TypeVar

from .models import Entity, InboxItem, MemoryClaim, now_iso

T = TypeVar("T", bound=Entity)


def default_data_dir() -> Path:
    override = os.getenv("NEUROPA_DATA_DIR") or os.getenv("NEUROPA_DATA")
    if override:
        path = Path(override).expanduser()
    elif os.name == "nt":
        path = Path(os.getenv("APPDATA", Path.home())) / "neuropa"
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "neuropa"
    else:
        path = Path.home() / ".local" / "share" / "neuropa"
    path.mkdir(parents=True, exist_ok=True)
    return path


class Database:
    CURRENT_SCHEMA = 1

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_data_dir() / "neuropa.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self._lock = threading.RLock()
        self._supersede_lock = self._lock
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.migrate()

    def migrate(self) -> int:
        self.conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)")
        current = self.conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()[0]
        if current < 1:
            self.conn.execute("""CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, payload TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT
            )""")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_deleted ON entities(deleted_at)")
            self.conn.execute("INSERT INTO schema_version(version) VALUES (1)")
            self.conn.commit()
        return 1

    def close(self) -> None:
        self.conn.close()

    def create(self, obj: T, *, commit: bool = True) -> T:
        with self._lock:
            self.conn.execute("INSERT INTO entities VALUES (?, ?, ?, ?, ?, ?)", (obj.id, obj.entity_type, json.dumps(obj.to_dict()), obj.created_at, obj.updated_at, obj.deleted_at))
            if commit:
                self.conn.commit()
        return obj

    def get(self, entity_type: str, obj_id: str, include_deleted: bool = False) -> Entity | None:
        q = "SELECT payload FROM entities WHERE entity_type=? AND id=?"
        args: list[Any] = [entity_type, obj_id]
        if not include_deleted:
            q += " AND deleted_at IS NULL"
        with self._lock:
            row = self.conn.execute(q, args).fetchone()
        if not row:
            return None
        return self._decode(row[0])

    def list(self, entity_type: str, include_deleted: bool = False) -> list[Entity]:
        q = "SELECT payload FROM entities WHERE entity_type=?"
        args: list[Any] = [entity_type]
        if not include_deleted:
            q += " AND deleted_at IS NULL"
        q += " ORDER BY created_at DESC"
        with self._lock:
            rows = self.conn.execute(q, args).fetchall()
        return [self._decode(row[0]) for row in rows]

    def update(self, obj: T, **changes: Any) -> T:
        with self._lock:
            existing = self.get(obj.entity_type, obj.id, include_deleted=True)
            if existing is None:
                raise KeyError(obj.id)
            if isinstance(existing, InboxItem):
                changes.pop("raw_text", None)
            data = existing.to_dict()
            data.update(changes)
            data["updated_at"] = now_iso()
            cls = type(existing)
            data.pop("entity_type", None)
            updated = cls(**data)
            self.conn.execute("UPDATE entities SET payload=?, updated_at=?, deleted_at=? WHERE id=?", (json.dumps(updated.to_dict()), updated.updated_at, updated.deleted_at, updated.id))
            self.conn.commit()
        return updated

    def replace_entities(self, objects: list[Entity]) -> None:
        """Atomically replace all entities after the caller validates every row."""
        with self._lock:
            try:
                self.conn.execute("BEGIN")
                self.conn.execute("DELETE FROM entities")
                for obj in objects:
                    self.create(obj, commit=False)
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def soft_delete(self, entity_type: str, obj_id: str) -> bool:
        stamp = now_iso()
        with self._lock:
            cur = self.conn.execute("UPDATE entities SET deleted_at=?, updated_at=? WHERE entity_type=? AND id=? AND deleted_at IS NULL", (stamp, stamp, entity_type, obj_id))
            self.conn.commit()
        return cur.rowcount > 0

    def supersede(self, old_id: str, new_claim: MemoryClaim) -> MemoryClaim:
        with self._supersede_lock:
            return self._supersede_locked(old_id, new_claim)

    def _supersede_locked(self, old_id: str, new_claim: MemoryClaim) -> MemoryClaim:
        try:
            # Serialize the read/insert/conditional-write sequence so a concurrent
            # supersession cannot leave an orphaned replacement claim.
            self.conn.execute("BEGIN IMMEDIATE")
            old = self.get("memory_claim", old_id)
            if old is None:
                raise KeyError(old_id)
            if not isinstance(old, MemoryClaim):
                raise KeyError(old_id)
            if old.superseded_by:
                raise ValueError("claim is already superseded")

            self.create(new_claim, commit=False)
            data = old.to_dict()
            data["superseded_by"] = new_claim.id
            data["updated_at"] = now_iso()
            data.pop("entity_type", None)
            updated = type(old)(**data)
            cur = self.conn.execute(
                """UPDATE entities
                   SET payload=?, updated_at=?, deleted_at=?
                 WHERE entity_type=? AND id=? AND deleted_at IS NULL
                   AND json_extract(payload, '$.superseded_by') IS NULL""",
                (
                    json.dumps(updated.to_dict()),
                    updated.updated_at,
                    updated.deleted_at,
                    "memory_claim",
                    old_id,
                ),
            )
            if cur.rowcount != 1:
                raise ValueError("claim is already superseded")
            self.conn.commit()
            return new_claim
        except Exception:
            self.conn.rollback()
            raise

    @staticmethod
    def _decode(payload: str) -> Entity:
        from .models import ENTITY_TYPES
        data = json.loads(payload)
        cls = ENTITY_TYPES[data.pop("entity_type")]
        return cls(**data)


Repository = Database
