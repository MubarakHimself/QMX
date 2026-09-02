"""``before_ledger_append`` validating gate that never discards evidence (FR-Q32, FR-Q58).

A well-formed evidence append from the ``dispatch_lease`` holder cannot be
denied — timeout allows with ``hook_timeout`` annotation; policy/precedence
denies are forced to allow. Schema-invalid or outside-lease refuses write to
the ledger but quarantine the entry verbatim — never discard (L39; DEC-0309).
The first explicit denial materializes the ``ledger_quarantine_stream``
projection.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal, cast

from qma.core.plugins.hooks import HookResult, build_hook_result
from qma.core.ports.ledgers import (
    DAEMON_AUTHORED_ENTRY_KINDS as CORE_DAEMON_AUTHORED_KINDS,
)
from qma.core.ports.ledgers import (
    HOOK_RETURNED_LEDGER_KIND,
    LEDGER_ENTRY_REQUIRED_FIELDS,
    parse_task_ledger_entry,
    stamp_hook_returned_ledger_entry,
)
from qma.core.vocabulary.enums import HookResultDecision
from qma.core.vocabulary.hooks import (
    BEFORE_LEDGER_APPEND_EVENT,
    HOOK_TIMEOUT_REASON,
)
from qma.daemon.hooks.timeouts import (
    HOOK_TIMEOUT_BEFORE_KEY,
    HookTimeoutTelemetry,
    HookTimeoutTelemetrySink,
    resolve_hook_timeout,
)
from qma.daemon.journal.stores import StoreRegistry
from qmf.core import is_ok

__all__ = [
    "DAEMON_AUTHORED_ENTRY_KINDS",
    "LEDGER_ENTRY_REQUIRED_FIELDS",
    "LEDGER_QUARANTINE_STREAM",
    "LedgerAppendDisposition",
    "LedgerAppendGateResult",
    "LedgerQuarantineRecord",
    "LedgerQuarantineStream",
    "annotate_ledger_entry",
    "evaluate_before_ledger_append",
    "is_dispatch_lease_holder",
    "is_exempt_ledger_author",
    "is_well_formed_ledger_entry",
]


# Closed daemon-authored kinds exempt from the lease-holder check (CT-51).
DAEMON_AUTHORED_ENTRY_KINDS: Final[frozenset[str]] = frozenset(
    member.value for member in CORE_DAEMON_AUTHORED_KINDS
)
LEDGER_QUARANTINE_STREAM: Final[str] = "ledger_quarantine_stream"

LedgerAppendDisposition = Literal["record", "quarantine"]


@dataclass(frozen=True, slots=True)
class LedgerQuarantineRecord:
    """One refused ledger entry written to the quarantine stream (never discarded)."""

    entry: Mapping[str, object]
    reason: str
    denial_source: str

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "stream": LEDGER_QUARANTINE_STREAM,
                "reason": self.reason,
                "denial_source": self.denial_source,
                "entry": dict(self.entry),
                "discarded": False,
            }
        )


@dataclass
class LedgerQuarantineStream:
    """Durable companion of the ledger store — refuse writes land here (AD-8).

    The ``ledger_quarantine_stream`` projection stays unmaterialized until the
    first explicit denial writes a record (FR-Q58).
    """

    _records: list[LedgerQuarantineRecord] = field(default_factory=list[LedgerQuarantineRecord])
    _stores: StoreRegistry | None = None

    def bind_projection(self, stores: StoreRegistry) -> None:
        """Attach the closed-store registry so the first deny materializes it."""
        self._stores = stores
        if self._records:
            stores.materialize_on_first_write(LEDGER_QUARANTINE_STREAM)

    def write(
        self,
        entry: Mapping[str, object],
        *,
        reason: str,
        denial_source: str,
    ) -> LedgerQuarantineRecord:
        record = LedgerQuarantineRecord(
            entry=MappingProxyType(dict(entry)),
            reason=reason,
            denial_source=denial_source,
        )
        self._records.append(record)
        if self._stores is not None:
            self._stores.materialize_on_first_write(LEDGER_QUARANTINE_STREAM)
        return record

    @property
    def records(self) -> tuple[LedgerQuarantineRecord, ...]:
        return tuple(self._records)

    @property
    def discarded_count(self) -> int:
        """Always zero — quarantine never discards (FR-Q32; L39)."""
        return 0

    @property
    def projection_materialized(self) -> bool:
        """True after the first explicit denial materializes the projection."""
        if self._stores is None:
            return False
        declared = self._stores.declared().get(LEDGER_QUARANTINE_STREAM)
        return declared is not None and declared.materialized


@dataclass(frozen=True, slots=True)
class LedgerAppendGateResult:
    """Outcome of the ``before_ledger_append`` validating gate."""

    result: HookResult
    disposition: LedgerAppendDisposition
    entry: Mapping[str, object]
    timeout_key: str | None = None
    quarantine: LedgerQuarantineRecord | None = None
    telemetry: HookTimeoutTelemetry | None = None

    @property
    def decision(self) -> HookResultDecision:
        return self.result.decision

    @property
    def recorded(self) -> bool:
        return self.disposition == "record"

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "event": BEFORE_LEDGER_APPEND_EVENT,
            "decision": self.result.decision.value,
            "reason": self.result.reason,
            "disposition": self.disposition,
            "entry": dict(self.entry),
            "discarded": False,
        }
        if self.timeout_key is not None:
            payload["timeout_key"] = self.timeout_key
        if self.quarantine is not None:
            payload["quarantine"] = dict(self.quarantine.to_payload())
        if self.telemetry is not None:
            payload["telemetry"] = dict(self.telemetry.to_payload())
        return MappingProxyType(payload)


def _authored_by_is_daemon(authored_by: object) -> bool:
    if authored_by == "daemon":
        return True
    if isinstance(authored_by, Mapping):
        body = cast(Mapping[str, object], authored_by)
        return body.get("agent") == "daemon" or body.get("kind") == "daemon"
    return False


def _hook_registry_id_of(entry: Mapping[str, object]) -> str | None:
    raw = entry.get("hook_registry_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    authored_by = entry.get("authored_by")
    if isinstance(authored_by, Mapping):
        nested = cast(Mapping[str, object], authored_by).get("hook_registry_id")
        if isinstance(nested, str) and nested.strip():
            return nested.strip()
    return None


def is_exempt_ledger_author(entry: Mapping[str, object]) -> bool:
    """Daemon-authored kinds and hook-returned ledger_entry with authored_by daemon."""
    kind = entry.get("kind")
    authored_by = entry.get("authored_by")
    if kind in DAEMON_AUTHORED_ENTRY_KINDS and _authored_by_is_daemon(authored_by):
        return True
    # Hook-returned ledger_entry: authored_by daemon plus returning hook registry id.
    return (
        kind == HOOK_RETURNED_LEDGER_KIND.value
        and _authored_by_is_daemon(authored_by)
        and _hook_registry_id_of(entry) is not None
    )


def is_dispatch_lease_holder(
    entry: Mapping[str, object],
    *,
    dispatch_lease_holder: str | None,
) -> bool:
    """True when the append author holds the Task's ``dispatch_lease``."""
    if dispatch_lease_holder is None:
        return False
    authored_by = entry.get("authored_by")
    if isinstance(authored_by, str):
        return authored_by == dispatch_lease_holder
    if isinstance(authored_by, Mapping):
        body = cast(Mapping[str, object], authored_by)
        agent_ref = body.get("agent") or body.get("agent_id")
        return agent_ref == dispatch_lease_holder
    return False


def is_well_formed_ledger_entry(entry: Mapping[str, object]) -> bool:
    """Schema-shape check for a Task Ledger entry (CT-51 required fields)."""
    if not LEDGER_ENTRY_REQUIRED_FIELDS.issubset(entry.keys()):
        return False
    for key in LEDGER_ENTRY_REQUIRED_FIELDS:
        if entry.get(key) is None:
            return False
    kind = entry.get("kind")
    if not isinstance(kind, str) or kind == "":
        return False
    attempt_no = entry.get("attempt_no")
    if not isinstance(attempt_no, int) or isinstance(attempt_no, bool) or attempt_no < 0:
        return False
    # model_deployment_ref mandatory except daemon-authored exempt kinds.
    if kind in DAEMON_AUTHORED_ENTRY_KINDS and _authored_by_is_daemon(entry.get("authored_by")):
        return True
    if kind == HOOK_RETURNED_LEDGER_KIND.value:
        return (
            _authored_by_is_daemon(entry.get("authored_by"))
            and _hook_registry_id_of(entry) is not None
        )
    return "model_deployment_ref" in entry and entry.get("model_deployment_ref") is not None


def annotate_ledger_entry(
    entry: Mapping[str, object],
    *,
    annotation: str,
) -> Mapping[str, object]:
    """Return a copy of ``entry`` carrying a non-destructive annotation."""
    annotated: dict[str, object] = dict(entry)
    existing = annotated.get("annotations")
    notes: list[str]
    if isinstance(existing, list):
        raw_notes = cast(list[object], existing)
        notes = [str(item) for item in raw_notes]
    elif existing is None:
        notes = []
    else:
        notes = [str(existing)]
    if annotation not in notes:
        notes.append(annotation)
    annotated["annotations"] = notes
    annotated["hook_timeout"] = annotation == HOOK_TIMEOUT_REASON
    return MappingProxyType(annotated)


def _force_allow_well_formed(
    entry: Mapping[str, object],
    *,
    reason: str,
) -> LedgerAppendGateResult:
    recorded: Mapping[str, object] = (
        annotate_ledger_entry(entry, annotation=reason) if reason else MappingProxyType(dict(entry))
    )
    return LedgerAppendGateResult(
        result=build_hook_result(HookResultDecision.ALLOW, reason=reason or "evidence_preserved"),
        disposition="record",
        entry=recorded,
        timeout_key=None,
    )


def evaluate_before_ledger_append(
    entry: Mapping[str, object],
    *,
    dispatch_lease_holder: str | None = None,
    timed_out: bool = False,
    attempted_result: HookResult | None = None,
    quarantine: LedgerQuarantineStream | None = None,
    telemetry: HookTimeoutTelemetrySink | None = None,
    correlation_id: str | None = None,
    hook_registry_id: str | None = None,
    ct51_schema: bool = False,
    lease_holder: str | None = None,
    schema_valid: bool | None = None,
    outside_lease_reason: str = "outside_dispatch_lease",
) -> LedgerAppendGateResult:
    """Validate and resolve ``before_ledger_append`` under L39 evidence law.

    - Well-formed + lease holder (or exempt author) + timeout → allow + annotate.
    - Well-formed + lease holder + deny/policy → allow (cannot deny).
    - Schema-invalid or outside-lease → quarantine stream, never discard.
    - First explicit denial materializes the ledger quarantine projection.
    ``lease_holder`` is the holder of the relevant named lease (Task
    ``dispatch_lease`` or Quant ``quant_ledger_lease``).
    """
    working: Mapping[str, object]
    if hook_registry_id is not None:
        working = stamp_hook_returned_ledger_entry(entry, hook_registry_id=hook_registry_id)
    else:
        working = MappingProxyType(dict(entry))

    stream = quarantine if quarantine is not None else LedgerQuarantineStream()
    if schema_valid is not None:
        well_formed = schema_valid
    elif ct51_schema:
        well_formed = is_ok(parse_task_ledger_entry(working))
    else:
        well_formed = is_well_formed_ledger_entry(working)
    holder = lease_holder if lease_holder is not None else dispatch_lease_holder
    lease_ok = is_exempt_ledger_author(working) or is_dispatch_lease_holder(
        working, dispatch_lease_holder=holder
    )

    if not well_formed or not lease_ok:
        reason = "schema_invalid" if not well_formed else outside_lease_reason
        denial_source = "schema" if not well_formed else "lease"
        # An explicit deny from a hook still quarantines rather than discarding.
        if attempted_result is not None and attempted_result.reason:
            reason = attempted_result.reason
        record = stream.write(working, reason=reason, denial_source=denial_source)
        return LedgerAppendGateResult(
            result=build_hook_result(HookResultDecision.DENY, reason=reason),
            disposition="quarantine",
            entry=MappingProxyType(dict(working)),
            quarantine=record,
        )

    # Well-formed evidence from the qualified holder — cannot deny (L39).
    if timed_out:
        resolution = resolve_hook_timeout(
            BEFORE_LEDGER_APPEND_EVENT,
            correlation_id=correlation_id,
            telemetry=telemetry,
        )
        annotated = annotate_ledger_entry(working, annotation=HOOK_TIMEOUT_REASON)
        return LedgerAppendGateResult(
            result=resolution.result,
            disposition="record",
            entry=annotated,
            timeout_key=HOOK_TIMEOUT_BEFORE_KEY,
            telemetry=resolution.telemetry,
        )

    if attempted_result is not None and attempted_result.decision is HookResultDecision.DENY:
        # Permission policy / precedence / permissive mode may not deny.
        return _force_allow_well_formed(working, reason="evidence_deny_overridden")

    if attempted_result is not None:
        return LedgerAppendGateResult(
            result=attempted_result,
            disposition="record",
            entry=MappingProxyType(dict(working)),
        )

    return LedgerAppendGateResult(
        result=build_hook_result(HookResultDecision.ALLOW, reason="ledger_append_ok"),
        disposition="record",
        entry=MappingProxyType(dict(working)),
    )
