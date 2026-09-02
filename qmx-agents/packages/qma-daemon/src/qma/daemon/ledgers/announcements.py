"""``ledger.appended`` announcement rows shared by the three ledger stores (AD-9)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Final, cast

__all__ = [
    "DESK_LEDGER_INDEX_KEYS",
    "LEDGER_STORE_NAMES",
    "LedgerAppendAnnouncement",
    "agent_ref_from_authored_by",
    "utc_date_from_recorded_at",
]


LEDGER_STORE_NAMES: Final[frozenset[str]] = frozenset(
    {
        "task_ledger",
        "quant_ledger",
        "experiment_ledger",
    }
)

DESK_LEDGER_INDEX_KEYS: Final[frozenset[str]] = frozenset(
    {
        "desk",
        "quant",
        "agent",
        "mission",
        "task",
        "experiment",
        "date",
    }
)

_NS_PER_SECOND: Final[int] = 1_000_000_000


def utc_date_from_recorded_at(recorded_at: int) -> str:
    """UTC calendar date of a daemon-stamped ``recorded_at`` nanosecond instant."""
    seconds, _remainder = divmod(max(recorded_at, 0), _NS_PER_SECOND)
    return datetime.fromtimestamp(seconds, tz=UTC).date().isoformat()


def agent_ref_from_authored_by(authored_by: object) -> str | None:
    """Agent id from a ledger ``authored_by`` payload; ``daemon`` has none."""
    if authored_by == "daemon":
        return None
    if isinstance(authored_by, str) and authored_by.strip():
        return authored_by.strip()
    if isinstance(authored_by, Mapping):
        body = cast("Mapping[str, object]", authored_by)
        if body.get("kind") == "daemon" or body.get("agent") == "daemon":
            return None
        raw = body.get("agent") or body.get("agent_id")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


@dataclass(frozen=True, slots=True)
class LedgerAppendAnnouncement:
    """One ``ledger.appended`` row ready for the desk-view fold (FR-Q59)."""

    journal_seq: int
    store: str
    recorded_at: int
    entry: Mapping[str, object]
    desk: str | None = None
    quant: str | None = None
    agent: str | None = None
    mission: str | None = None
    task: str | None = None
    experiment: str | None = None
    date: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "entry", MappingProxyType(dict(self.entry)))
        if self.date is None and self.recorded_at > 0:
            object.__setattr__(self, "date", utc_date_from_recorded_at(self.recorded_at))

    def index_value(self, key: str) -> str | None:
        if key == "desk":
            return self.desk
        if key == "quant":
            return self.quant
        if key == "agent":
            return self.agent
        if key == "mission":
            return self.mission
        if key == "task":
            return self.task
        if key == "experiment":
            return self.experiment
        if key == "date":
            return self.date
        return None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "journal_seq": self.journal_seq,
            "store": self.store,
            "recorded_at": self.recorded_at,
            "entry": dict(self.entry),
        }
        for key in sorted(DESK_LEDGER_INDEX_KEYS):
            value = self.index_value(key)
            if value is not None:
                payload[key] = value
        return MappingProxyType(payload)
