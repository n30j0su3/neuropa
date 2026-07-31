from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Entity:
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    deleted_at: str | None = None
    entity_type: ClassVar[str] = "entity"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["entity_type"] = self.entity_type
        return data


@dataclass
class InboxItem(Entity):
    raw_text: str = ""
    source: str = "text"
    status: str = "new"
    context: dict[str, Any] = field(default_factory=dict)
    entity_type: ClassVar[str] = "inbox"


@dataclass
class Task(Entity):
    title: str = ""
    next_action: str = ""
    steps: list[str] = field(default_factory=list)
    estimate_range: str = ""
    energy: str = "medium"
    project_id: str | None = None
    status: str = "open"
    created_from: str | None = None
    entity_type: ClassVar[str] = "task"


@dataclass
class Reminder(Entity):
    task_id: str | None = None
    what: str = ""
    where: str = ""
    duration: str = ""
    first_step: str = ""
    trigger_at: str | None = None
    recurrence: str | None = None
    snooze_state: str = "none"
    channel: str = "local"
    escalation: str = "notice"
    entity_type: ClassVar[str] = "reminder"


@dataclass
class Project(Entity):
    name: str = ""
    why: str = ""
    status: str = "active"
    milestones: list[str] = field(default_factory=list)
    next_action: str = ""
    last_touched: str | None = None
    entity_type: ClassVar[str] = "project"


@dataclass
class FocusSession(Entity):
    task_id: str | None = None
    planned_min: int = 25
    actual_min: int = 0
    pauses: list[dict[str, Any]] = field(default_factory=list)
    outcome: str = "planned"
    reflection_1q: str = ""
    entity_type: ClassVar[str] = "focus_session"


@dataclass
class CalendarEvent(Entity):
    title: str = ""
    start: str | None = None
    end: str | None = None
    source: str = "local"
    reminder_ids: list[str] = field(default_factory=list)
    entity_type: ClassVar[str] = "calendar_event"


@dataclass
class MemoryClaim(Entity):
    claim_text: str = ""
    source_type: str = "note"
    source_ref: str = ""
    confidence: float = 0.0
    superseded_by: str | None = None
    entity_type: ClassVar[str] = "memory_claim"


@dataclass
class Artifact(Entity):
    type: str = "file"
    path: str = ""
    blob_ref: str | None = None
    title: str = ""
    tags: list[str] = field(default_factory=list)
    version: int = 1
    links: dict[str, Any] = field(default_factory=dict)
    entity_type: ClassVar[str] = "artifact"


@dataclass
class Skill(Entity):
    name: str = ""
    version: str = "1.0.0"
    enabled: bool = False
    permissions: dict[str, Any] = field(default_factory=dict)
    source: str = "local"
    entity_type: ClassVar[str] = "skill"


@dataclass
class Provider(Entity):
    kind: str = "local"
    model: str = ""
    health: str = "unknown"
    cost_label: str = "free"
    privacy_label: str = "local"
    entity_type: ClassVar[str] = "provider"


@dataclass
class Preset(Entity):
    name: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    entity_type: ClassVar[str] = "preset"

ENTITY_TYPES = {c.entity_type: c for c in [InboxItem, Task, Reminder, Project, FocusSession, CalendarEvent, MemoryClaim, Artifact, Skill, Provider, Preset]}
