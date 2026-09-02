"""TelemetryExportPort and harness-authored telemetry records (AD-23; FR-Q67).

Definitions only. Logs, traces, metrics, trajectories and session replay are
harness-authored, never agent-authored ledger entries. OpenTelemetry conformance
happens only at this swappable export port — never as an SDK imported into the
daemon core. A ledger entry may carry ``trace_ref``; telemetry never points back
into a ledger. GAP-0089 (trim window) and GAP-0090 (context compaction) stay
Deferred.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal, Protocol, cast, runtime_checkable
from uuid import uuid4

from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "GAP_0089_TRIM_WINDOW",
    "GAP_0090_CONTEXT_COMPACTION",
    "HARNESS_AUTHOR",
    "TELEMETRY_EXPORT_OPERATIONS",
    "TELEMETRY_FORBIDDEN_LEDGER_KEYS",
    "TELEMETRY_KINDS",
    "TELEMETRY_RETENTION_EXEMPT_KINDS",
    "TELEMETRY_RETENTION_KEYS",
    "TelemetryExportPort",
    "TelemetryKind",
    "TelemetryRecord",
    "parse_telemetry_kind",
    "parse_telemetry_record",
    "refuse_agent_authored_telemetry",
    "refuse_context_compaction",
    "refuse_ledger_back_reference",
    "refuse_trim_window_decision",
]


TelemetryKind = Literal[
    "log",
    "trace",
    "metric",
    "trajectory",
    "session_replay",
    "routing_decision",
    "usage",
    "compute_job",
    "tool_call",
    "hook_timeout",
]

TELEMETRY_KINDS: Final[frozenset[str]] = frozenset(
    {
        "log",
        "trace",
        "metric",
        "trajectory",
        "session_replay",
        "routing_decision",
        "usage",
        "compute_job",
        "tool_call",
        "hook_timeout",
    }
)

# Retention-exempt until GAP-0072 / GAP-0074 / GAP-0080 revisit (DEC-0322).
TELEMETRY_RETENTION_EXEMPT_KINDS: Final[frozenset[str]] = frozenset(
    {
        "trajectory",
        "session_replay",
    }
)

HARNESS_AUTHOR: Final[str] = "harness"

TELEMETRY_EXPORT_OPERATIONS: Final[frozenset[str]] = frozenset({"export", "flush"})

TELEMETRY_RETENTION_KEYS: Final[tuple[str, ...]] = (
    "registry:telemetry.retention_window",
    "registry:telemetry.trim_event_count",
    "registry:telemetry.trim_disk_bytes",
)

TELEMETRY_FORBIDDEN_LEDGER_KEYS: Final[frozenset[str]] = frozenset(
    {
        "ledger_ref",
        "task_ledger_ref",
        "quant_ledger_ref",
        "experiment_ledger_ref",
        "ledger",
        "task_ledger",
        "quant_ledger",
        "experiment_ledger",
        "ledger_entry",
    }
)

GAP_0089_TRIM_WINDOW: Final[str] = "GAP-0089"
GAP_0090_CONTEXT_COMPACTION: Final[str] = "GAP-0090"


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def refuse_agent_authored_telemetry(**extra: object) -> TypedRefusal:
    """Telemetry is harness-authored only — never an agent ledger entry (FR-Q67)."""
    return _policy(
        "authored_by",
        "telemetry records are harness-authored and never agent-authored ledger "
        "entries (AD-23; FR-Q67; DEC-0322)",
        author=HARNESS_AUTHOR,
        **extra,
    )


def refuse_ledger_back_reference(*, key: str, **extra: object) -> TypedRefusal:
    """A ledger may carry ``trace_ref``; telemetry never points into a ledger."""
    return _policy(
        key,
        "a ledger entry may carry trace_ref, but telemetry never points back "
        "into a ledger (AD-23; FR-Q67; DEC-0322)",
        allowed_direction="ledger->trace_ref",
        forbidden_direction="telemetry->ledger",
        **extra,
    )


def refuse_trim_window_decision(**extra: object) -> TypedRefusal:
    """Trim-window thresholds stay Deferred GAP-0089 (DEC-0322)."""
    return _policy(
        "trim_window",
        "the trim window for bounded non-evidence streams is Deferred GAP-0089; "
        "cite registry:telemetry.* keys only and never close the gap here "
        "(AD-23; FR-Q67; DEC-0322)",
        gap=GAP_0089_TRIM_WINDOW,
        deferred=True,
        **extra,
    )


def refuse_context_compaction(**extra: object) -> TypedRefusal:
    """Context compaction stays Deferred GAP-0090 (DEC-0313)."""
    return _policy(
        "context_compaction",
        "context compaction is Deferred GAP-0090; compaction persists nothing "
        "and no compacted transcript is evidence until the ceiling revisit "
        "(AD-14; FR-Q67; DEC-0313)",
        gap=GAP_0090_CONTEXT_COMPACTION,
        deferred=True,
        **extra,
    )


def parse_telemetry_kind(value: object) -> Result[TelemetryKind]:
    """Parse a closed telemetry kind token (AD-23)."""
    if not isinstance(value, str) or value not in TELEMETRY_KINDS:
        return _invalid(
            "kind",
            "telemetry kind is one of the closed AD-23 vocabulary tokens (FR-Q67)",
            given=repr(value),
            allowed=sorted(TELEMETRY_KINDS),
        )
    return Ok(cast("TelemetryKind", value))


def _parse_nonempty(value: object, field: str) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(
            field,
            f"{field} is a mandatory non-empty string (AD-23; FR-Q67)",
            given=repr(value),
        )
    return Ok(value.strip())


def _parse_instant(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return _invalid(
            field,
            f"{field} is int64 UTC nanoseconds (AD-23; FR-Q67; DEC-0322)",
            given=repr(value),
        )
    return Ok(value)


def _parse_payload(value: object) -> Result[Mapping[str, object]]:
    if value is None:
        return Ok(MappingProxyType({}))
    if not isinstance(value, Mapping):
        return _invalid(
            "payload",
            "telemetry payload is a mapping when present (AD-23; FR-Q67)",
            given=repr(type(value).__name__),
        )
    body = cast("Mapping[str, object]", value)
    overlap = TELEMETRY_FORBIDDEN_LEDGER_KEYS.intersection(body)
    if overlap:
        key = sorted(overlap)[0]
        return refuse_ledger_back_reference(key=key, given=body.get(key))
    return Ok(MappingProxyType(dict(body)))


@dataclass(frozen=True, slots=True)
class TelemetryRecord:
    """One harness-authored telemetry row (AD-23; FR-Q67; DEC-0322).

    Carries ``occurred_at`` and ``recorded_at`` only — no ``journal_seq``. Ordered
    by ``recorded_at`` then ``correlation_id``. Retention-exempt kinds
    (``trajectory``, ``session_replay``) are never trimmed by a daemon job.
    """

    kind: TelemetryKind
    correlation_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    wire_id: str | None = None
    authored_by: str = HARNESS_AUTHOR
    occurred_at: int = 0
    recorded_at: int = 0
    payload: Mapping[str, object] = field(default_factory=dict[str, object])

    def __post_init__(self) -> None:
        if self.authored_by != HARNESS_AUTHOR:
            msg = "telemetry authored_by must be harness (AD-23; FR-Q67)"
            raise ValueError(msg)
        if self.kind not in TELEMETRY_KINDS:
            msg = f"unknown telemetry kind {self.kind!r} (AD-23; FR-Q67)"
            raise ValueError(msg)
        if not isinstance(self.payload, MappingProxyType):
            object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        overlap = TELEMETRY_FORBIDDEN_LEDGER_KEYS.intersection(self.payload)
        if overlap:
            msg = (
                "telemetry payload may not carry ledger back-references "
                f"{sorted(overlap)} (AD-23; FR-Q67)"
            )
            raise ValueError(msg)

    @property
    def retention_exempt(self) -> bool:
        """True for trajectory / session_replay streams (DEC-0322)."""
        return self.kind in TELEMETRY_RETENTION_EXEMPT_KINDS

    @property
    def trace_ref(self) -> str:
        """Opaque trace reference a ledger entry may cite — never the reverse."""
        return f"trace:{self.id}"

    def to_payload(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "id": self.id,
            "kind": self.kind,
            "correlation_id": self.correlation_id,
            "authored_by": self.authored_by,
            "occurred_at": self.occurred_at,
            "recorded_at": self.recorded_at,
            "payload": dict(self.payload),
            "retention_exempt": self.retention_exempt,
            "trace_ref": self.trace_ref,
        }
        if self.wire_id is not None:
            body["wire_id"] = self.wire_id
        # Explicit absence: never a journal_seq on telemetry (DEC-0322).
        return MappingProxyType(body)


def parse_telemetry_record(value: object) -> Result[TelemetryRecord]:
    """Validate a harness-authored telemetry record (AD-23; FR-Q67)."""
    if isinstance(value, TelemetryRecord):
        if value.authored_by != HARNESS_AUTHOR:
            return refuse_agent_authored_telemetry(given=value.authored_by)
        return Ok(value)
    if not isinstance(value, Mapping):
        return _invalid(
            "record",
            "a TelemetryRecord is a mapping (AD-23; FR-Q67)",
            given=repr(type(value).__name__),
        )
    body = cast("Mapping[str, object]", value)

    if "journal_seq" in body:
        return _policy(
            "journal_seq",
            "a telemetry record carries occurred_at and recorded_at only — no "
            "journal_seq (AD-23; FR-Q67; DEC-0322)",
            given=body.get("journal_seq"),
        )

    authored = body.get("authored_by", HARNESS_AUTHOR)
    if authored != HARNESS_AUTHOR:
        return refuse_agent_authored_telemetry(given=authored)

    forbidden = TELEMETRY_FORBIDDEN_LEDGER_KEYS.intersection(body)
    if forbidden:
        key = sorted(forbidden)[0]
        return refuse_ledger_back_reference(key=key, given=body.get(key))

    kind = parse_telemetry_kind(body.get("kind"))
    if not isinstance(kind, Ok):
        return kind
    correlation = _parse_nonempty(body.get("correlation_id"), "correlation_id")
    if not isinstance(correlation, Ok):
        return correlation
    occurred = _parse_instant(body.get("occurred_at", 0), "occurred_at")
    if not isinstance(occurred, Ok):
        return occurred
    recorded = _parse_instant(body.get("recorded_at", occurred.value), "recorded_at")
    if not isinstance(recorded, Ok):
        return recorded
    payload = _parse_payload(body.get("payload"))
    if not isinstance(payload, Ok):
        return payload

    record_id = body.get("id")
    if record_id is None:
        resolved_id = str(uuid4())
    elif isinstance(record_id, str) and record_id.strip() != "":
        resolved_id = record_id.strip()
    else:
        return _invalid(
            "id",
            "id is a non-empty string when present (AD-23)",
            given=repr(record_id),
        )

    wire_id: str | None = None
    if "wire_id" in body or "id_wire" in body:
        raw_wire = body.get("wire_id", body.get("id_wire"))
        if raw_wire is None:
            return _invalid(
                "wire_id",
                "wire_id is omitted when unused, never null (AD-23)",
            )
        if not isinstance(raw_wire, str) or raw_wire.strip() == "":
            return _invalid(
                "wire_id",
                "wire_id is a non-empty string when present",
                given=repr(raw_wire),
            )
        wire_id = raw_wire.strip()

    return Ok(
        TelemetryRecord(
            id=resolved_id,
            kind=kind.value,
            correlation_id=correlation.value,
            wire_id=wire_id,
            authored_by=HARNESS_AUTHOR,
            occurred_at=occurred.value,
            recorded_at=recorded.value,
            payload=payload.value,
        )
    )


@runtime_checkable
class TelemetryExportPort(Protocol):
    """Swappable OpenTelemetry conformance seam — never an in-core SDK import.

    Daemon core records and trims telemetry independently of this port. An
    exporter may map QMA-owned record types onto OTel at the boundary only.
    """

    def export(self, records: Sequence[TelemetryRecord]) -> Result[int]:
        """Export harness-authored records. Returns the count accepted."""
        ...

    def flush(self) -> Result[None]:
        """Flush any buffered export state."""
        ...
