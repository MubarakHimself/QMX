"""``before_ledger_append`` validating gate that never discards evidence (FR-Q32).

A well-formed evidence append from the ``dispatch_lease`` holder cannot be
denied — timeout allows with ``hook_timeout`` annotation; policy/precedence
denies are forced to allow. Schema-invalid or outside-lease refuses write to
the ledger but quarantine the entry verbatim — never discard (L39; DEC-0309).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal, cast

from qma.core.plugins.hooks import HookResult, build_hook_result
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

__all__ = [
    "DAEMON_AUTHORED_ENTRY_KINDS",
    "LEDGER_ENTRY_REQUIRED_FIELDS",
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


LEDGER_ENTRY_REQUIRED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "kind",
        "attempt_no",
        "authored_by",
        "recorded_at",
    }
)

# Closed daemon-authored kinds exempt from the lease-holder check (CT-51).
DAEMON_AUTHORED_ENTRY_KINDS: Final[frozenset[str]] = frozenset({"reassigned", "unknown_tail"})

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
                "stream": "ledger_quarantine_stream",
                "reason": self.reason,
                "denial_source": self.denial_source,
                "entry": dict(self.entry),
                "discarded": False,
            }
        )


@dataclass
class LedgerQuarantineStream:
    """Durable companion of the ledger store — refuse writes land here (AD-8)."""

    _records: list[LedgerQuarantineRecord] = field(default_factory=list[LedgerQuarantineRecord])

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
        return record

    @property
    def records(self) -> tuple[LedgerQuarantineRecord, ...]:
        return tuple(self._records)

    @property
    def discarded_count(self) -> int:
        """Always zero — quarantine never discards (FR-Q32; L39)."""
        return 0


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


def is_exempt_ledger_author(entry: Mapping[str, object]) -> bool:
    """Daemon-authored kinds and hook-returned ledger_entry with authored_by daemon."""
    kind = entry.get("kind")
    authored_by = entry.get("authored_by")
    if kind in DAEMON_AUTHORED_ENTRY_KINDS and _authored_by_is_daemon(authored_by):
        return True
    # Hook-returned ledger_entry: authored_by daemon plus returning hook registry id.
    return kind == "ledger_entry" and _authored_by_is_daemon(authored_by)


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
    dispatch_lease_holder: str | None,
    timed_out: bool = False,
    attempted_result: HookResult | None = None,
    quarantine: LedgerQuarantineStream | None = None,
    telemetry: HookTimeoutTelemetrySink | None = None,
    correlation_id: str | None = None,
) -> LedgerAppendGateResult:
    """Validate and resolve ``before_ledger_append`` under L39 evidence law.

    - Well-formed + lease holder (or exempt author) + timeout → allow + annotate.
    - Well-formed + lease holder + deny/policy → allow (cannot deny).
    - Schema-invalid or outside-lease → quarantine stream, never discard.
    """
    stream = quarantine if quarantine is not None else LedgerQuarantineStream()
    well_formed = is_well_formed_ledger_entry(entry)
    lease_ok = is_exempt_ledger_author(entry) or is_dispatch_lease_holder(
        entry, dispatch_lease_holder=dispatch_lease_holder
    )

    if not well_formed or not lease_ok:
        reason = "schema_invalid" if not well_formed else "outside_dispatch_lease"
        denial_source = "schema" if not well_formed else "lease"
        # An explicit deny from a hook still quarantines rather than discarding.
        if attempted_result is not None and attempted_result.reason:
            reason = attempted_result.reason
        record = stream.write(entry, reason=reason, denial_source=denial_source)
        return LedgerAppendGateResult(
            result=build_hook_result(HookResultDecision.DENY, reason=reason),
            disposition="quarantine",
            entry=MappingProxyType(dict(entry)),
            quarantine=record,
        )

    # Well-formed evidence from the qualified holder — cannot deny (L39).
    if timed_out:
        resolution = resolve_hook_timeout(
            BEFORE_LEDGER_APPEND_EVENT,
            correlation_id=correlation_id,
            telemetry=telemetry,
        )
        annotated = annotate_ledger_entry(entry, annotation=HOOK_TIMEOUT_REASON)
        return LedgerAppendGateResult(
            result=resolution.result,
            disposition="record",
            entry=annotated,
            timeout_key=HOOK_TIMEOUT_BEFORE_KEY,
            telemetry=resolution.telemetry,
        )

    if attempted_result is not None and attempted_result.decision is HookResultDecision.DENY:
        # Permission policy / precedence / permissive mode may not deny.
        return _force_allow_well_formed(entry, reason="evidence_deny_overridden")

    if attempted_result is not None:
        return LedgerAppendGateResult(
            result=attempted_result,
            disposition="record",
            entry=MappingProxyType(dict(entry)),
        )

    return LedgerAppendGateResult(
        result=build_hook_result(HookResultDecision.ALLOW, reason="ledger_append_ok"),
        disposition="record",
        entry=MappingProxyType(dict(entry)),
    )
