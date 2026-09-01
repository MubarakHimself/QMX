"""Journal-before-dispatch gate for money-path effects (Story 26.13 / QMX-F069).

TN-24h / DEC-0209 / DEC-0150: every command, control, protection, promotion,
activation, treasury, or settings effect persists evidence first under CT-20
``atomic`` or ``ordered-with-recovery``. A sink refusal or a partial write is a
storage failure that blocks the effect (entries only). A log line or best-effort
write is not a journal and cannot pass the gate.

The happens-before is observed: the journal sink is invoked, then the dispatcher.
Tests inject a recording journal and a recording dispatcher that share a trace.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, MutableSequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Protocol, cast

from qmf.core import (
    JournalSink,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    SinkAck,
    SinkResult,
    TypedRefusal,
    is_ok,
    is_refusal,
    is_unpersistable,
    unpersistable,
)

# Inlined from qmn.observability.logging so this module stays a leaf (no
# package-init cycle through doors/config). Values must match that module.
LOGS_ARE_NOT_JOURNALS: Final[bool] = True
LOGS_SATISFY_CT13_EVIDENCE: Final[bool] = False

__all__ = [
    "BEST_EFFORT_PATH_PERMITTED",
    "EFFECT_KINDS",
    "JOURNAL_DISPATCH_SURFACE",
    "LOG_ONLY_PATH_PERMITTED",
    "STORAGE_FAILURE_IDS",
    "CallableDispatcher",
    "EffectDispatcher",
    "HappensBeforeTrace",
    "JournalBeforeDispatchReceipt",
    "LogLineSink",
    "RecordingEffectDispatcher",
    "RecordingJournalSink",
    "WriteBoundary",
    "enact_activation",
    "enact_command",
    "enact_control",
    "enact_promotion",
    "enact_protection",
    "enact_settings",
    "enact_treasury",
    "journal_before_effect",
    "passthrough_dispatch",
]

JOURNAL_DISPATCH_SURFACE: Final[str] = "qmn.journal_dispatch"
LOG_ONLY_PATH_PERMITTED: Final[bool] = False
BEST_EFFORT_PATH_PERMITTED: Final[bool] = False

EFFECT_KINDS: Final[tuple[str, ...]] = (
    "command",
    "control",
    "protection",
    "promotion",
    "activation",
    "treasury",
    "settings",
)

STORAGE_FAILURE_IDS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "journal_before_dispatch": "storage.journal_before_dispatch",
        "partial_write": "storage.partial_write",
        "log_only": "storage.log_only_path",
        "best_effort": "storage.best_effort_path",
    }
)


class WriteBoundary(StrEnum):
    """CT-20 named transaction boundary (DEC-0138 / TN-24h)."""

    ATOMIC = "atomic"
    ORDERED_WITH_RECOVERY = "ordered-with-recovery"


@dataclass
class HappensBeforeTrace:
    """Shared call-order recorder for a fake journal and a fake dispatcher."""

    steps: MutableSequence[str] = field(default_factory=list[str])

    def record(self, step: str) -> None:
        self.steps.append(step)

    def as_tuple(self) -> tuple[str, ...]:
        return tuple(self.steps)


class EffectDispatcher(Protocol):
    """Applies one already-journaled effect. Never called on journal failure."""

    def dispatch(self, payload: Mapping[str, object], /) -> Result[object]:
        """Apply the effect. Must not run unless the journal write landed."""
        ...


@dataclass
class RecordingJournalSink:
    """Test double: records append order onto an optional happens-before trace."""

    trace: HappensBeforeTrace | None = None
    fail: bool = False
    partial: bool = False
    best_effort: bool = False
    appended: MutableSequence[object] = field(default_factory=list[object])

    def append(self, event: object, /) -> SinkResult:
        if self.trace is not None:
            self.trace.record("journal")
        if self.fail:
            return unpersistable(
                "injected journal failure",
                context={
                    "failure_id": "storage.journal_before_dispatch",
                    "blocks_entries": True,
                    "blocks_exits": False,
                },
            )
        self.appended.append(event)
        if self.partial:
            return Ok(SinkAck(detail={"partial": True, "complete": False}))
        return Ok(SinkAck(detail={"partial": False, "complete": True}))


@dataclass
class RecordingEffectDispatcher:
    """Test double: records dispatch order onto an optional happens-before trace."""

    trace: HappensBeforeTrace | None = None
    fail: bool = False
    calls: MutableSequence[Mapping[str, object]] = field(
        default_factory=list[Mapping[str, object]]
    )

    def dispatch(self, payload: Mapping[str, object], /) -> Result[object]:
        if self.trace is not None:
            self.trace.record("dispatch")
        self.calls.append(payload)
        if self.fail:
            return _policy("effect", "injected dispatcher failure")
        return Ok(MappingProxyType(dict(payload)))


@dataclass
class CallableDispatcher:
    """Wrap a callable as an :class:`EffectDispatcher`."""

    fn: Callable[[Mapping[str, object]], Result[object]]
    trace: HappensBeforeTrace | None = None
    calls: MutableSequence[Mapping[str, object]] = field(
        default_factory=list[Mapping[str, object]]
    )

    def dispatch(self, payload: Mapping[str, object], /) -> Result[object]:
        if self.trace is not None:
            self.trace.record("dispatch")
        self.calls.append(payload)
        return self.fn(payload)


@dataclass
class LogLineSink:
    """Deliberately not a :class:`~qmf.core.JournalSink` — a log-only stand-in."""

    lines: MutableSequence[str] = field(default_factory=list[str])

    def info(self, message: object, /) -> None:
        self.lines.append(str(message))


@dataclass(frozen=True, slots=True)
class JournalBeforeDispatchReceipt:
    """Evidence that a journal write preceded effect dispatch."""

    kind: str
    payload: Mapping[str, object]
    boundary: str
    dispatched: bool
    blocks_entries_on_failure: bool
    steps: tuple[str, ...]
    dispatcher_result: object | None = None

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "kind": self.kind,
            "payload": dict(self.payload),
            "boundary": self.boundary,
            "dispatched": self.dispatched,
            "blocks_entries_on_failure": self.blocks_entries_on_failure,
            "steps": self.steps,
            "log_only_permitted": LOG_ONLY_PATH_PERMITTED,
            "best_effort_permitted": BEST_EFFORT_PATH_PERMITTED,
        }
        if self.dispatcher_result is not None:
            body["dispatcher_result"] = self.dispatcher_result
        return MappingProxyType(body)


def passthrough_dispatch(payload: Mapping[str, object]) -> Result[object]:
    """Identity dispatcher used when the caller only needs the journal write."""
    return Ok(payload)


def _clean_token(value: object) -> str | None:
    if isinstance(value, str) and value.strip() != "":
        return value.strip()
    return None


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context={"field": field, "reason": reason, **extra},
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context={"field": field, "reason": reason, **extra},
    )


def journal_before_effect(
    *,
    kind: object,
    payload: object,
    journal: object,
    dispatcher: object,
    boundary: object = WriteBoundary.ORDERED_WITH_RECOVERY,
    best_effort: object = False,
) -> Result[JournalBeforeDispatchReceipt]:
    """Persist ``payload`` then dispatch. Storage failure never reaches dispatch.

    The journal sink is invoked first. A refusal, a partial write, a log-only
    stand-in, or a best-effort flag blocks the effect (entries only) and leaves
    the dispatcher uncalled.
    """
    token = _clean_token(kind)
    if token is None or token not in EFFECT_KINDS:
        return _invalid(
            "kind",
            "journal-before-dispatch covers command|control|protection|promotion|"
            "activation|treasury|settings",
            given=repr(kind),
            allowed=list(EFFECT_KINDS),
        )
    if not isinstance(payload, Mapping):
        return _invalid(
            "payload",
            "journal-before-dispatch persists a mapping payload",
            given=type(payload).__name__,
        )
    body = MappingProxyType(dict(cast("Mapping[str, object]", payload)))
    resolved_boundary = _coerce_boundary(boundary)
    if is_refusal(resolved_boundary):
        return resolved_boundary
    if best_effort is True or getattr(journal, "best_effort", False) is True:
        return _policy(
            "journal",
            "a best-effort write is not journal evidence and cannot pass "
            "journal-before-dispatch",
            failure_id="storage.best_effort_path",
            best_effort_permitted=BEST_EFFORT_PATH_PERMITTED,
            blocks_entries=True,
            blocks_exits=False,
        )
    if not isinstance(best_effort, bool):
        return _invalid(
            "best_effort",
            "best_effort is a bool and must be false",
            given=repr(best_effort),
        )
    if not isinstance(journal, JournalSink):
        return _policy(
            "journal",
            "required journal/evidence persists through a JournalSink; a log line "
            "never substitutes for the missing journal record",
            failure_id="storage.log_only_path",
            given=type(journal).__name__,
            logs_are_not_journals=LOGS_ARE_NOT_JOURNALS,
            logs_satisfy_ct13=LOGS_SATISFY_CT13_EVIDENCE,
            log_only_permitted=LOG_ONLY_PATH_PERMITTED,
            log_record_is_journal_evidence=False,
            blocks_entries=True,
            blocks_exits=False,
        )
    if not hasattr(dispatcher, "dispatch"):
        return _invalid(
            "dispatcher",
            "journal-before-dispatch requires an EffectDispatcher with dispatch()",
            given=type(dispatcher).__name__,
        )

    sink = cast("JournalSink[Mapping[str, object]]", journal)
    appended: SinkResult = sink.append(body)
    if is_refusal(appended):
        if is_unpersistable(appended):
            return _block_entries(appended, failure_id="storage.journal_before_dispatch")
        return appended
    if not is_ok(appended):
        return cast("Result[JournalBeforeDispatchReceipt]", appended)
    if _is_partial_ack(appended.value):
        return unpersistable(
            "partial write is a storage failure that blocks entries",
            context={
                "failure_id": "storage.partial_write",
                "blocks_entries": True,
                "blocks_exits": False,
                "kind": token,
                "boundary": resolved_boundary.value.value,
            },
        )

    applied = dispatcher.dispatch(body)
    if is_refusal(applied):
        return applied
    if not is_ok(applied):
        return cast("Result[JournalBeforeDispatchReceipt]", applied)
    return Ok(
        JournalBeforeDispatchReceipt(
            kind=token,
            payload=body,
            boundary=resolved_boundary.value.value,
            dispatched=True,
            blocks_entries_on_failure=True,
            steps=("journal", "dispatch"),
            dispatcher_result=applied.value,
        )
    )


def enact_command(
    payload: object,
    *,
    journal: object,
    dispatcher: object,
    boundary: object = WriteBoundary.ORDERED_WITH_RECOVERY,
) -> Result[JournalBeforeDispatchReceipt]:
    """Journal a command before venue dispatch."""
    body = _with_kind(payload, "command")
    if is_refusal(body):
        return body
    return journal_before_effect(
        kind="command",
        payload=body.value,
        journal=journal,
        dispatcher=dispatcher,
        boundary=boundary,
    )


def enact_control(
    payload: object,
    *,
    journal: object,
    dispatcher: object,
    boundary: object = WriteBoundary.ORDERED_WITH_RECOVERY,
) -> Result[JournalBeforeDispatchReceipt]:
    """Journal a CT-30 control action before dispatch."""
    body = _with_kind(payload, "control")
    if is_refusal(body):
        return body
    return journal_before_effect(
        kind="control",
        payload=body.value,
        journal=journal,
        dispatcher=dispatcher,
        boundary=boundary,
    )


def enact_protection(
    payload: object,
    *,
    journal: object,
    dispatcher: object,
    boundary: object = WriteBoundary.ORDERED_WITH_RECOVERY,
) -> Result[JournalBeforeDispatchReceipt]:
    """Journal a standing protective intent before dispatch."""
    body = _with_kind(payload, "protection")
    if is_refusal(body):
        return body
    return journal_before_effect(
        kind="protection",
        payload=body.value,
        journal=journal,
        dispatcher=dispatcher,
        boundary=boundary,
    )


def enact_promotion(
    payload: object,
    *,
    journal: object,
    dispatcher: object,
    boundary: object = WriteBoundary.ATOMIC,
) -> Result[JournalBeforeDispatchReceipt]:
    """Journal a promotion event before the landing takes effect."""
    body = _with_kind(payload, "promotion")
    if is_refusal(body):
        return body
    return journal_before_effect(
        kind="promotion",
        payload=body.value,
        journal=journal,
        dispatcher=dispatcher,
        boundary=boundary,
    )


def enact_activation(
    payload: object,
    *,
    journal: object,
    dispatcher: object,
    boundary: object = WriteBoundary.ATOMIC,
) -> Result[JournalBeforeDispatchReceipt]:
    """Journal an activation transition before enforced state changes."""
    body = _with_kind(payload, "activation")
    if is_refusal(body):
        return body
    return journal_before_effect(
        kind="activation",
        payload=body.value,
        journal=journal,
        dispatcher=dispatcher,
        boundary=boundary,
    )


def enact_treasury(
    payload: object,
    *,
    journal: object,
    dispatcher: object,
    boundary: object = WriteBoundary.ATOMIC,
) -> Result[JournalBeforeDispatchReceipt]:
    """Journal a treasury boundary act before cash is applied."""
    body = _with_kind(payload, "treasury")
    if is_refusal(body):
        return body
    return journal_before_effect(
        kind="treasury",
        payload=body.value,
        journal=journal,
        dispatcher=dispatcher,
        boundary=boundary,
    )


def enact_settings(
    payload: object,
    *,
    journal: object,
    dispatcher: object,
    boundary: object = WriteBoundary.ATOMIC,
) -> Result[JournalBeforeDispatchReceipt]:
    """Journal a settings edit before the resolved config changes."""
    body = _with_kind(payload, "settings")
    if is_refusal(body):
        return body
    return journal_before_effect(
        kind="settings",
        payload=body.value,
        journal=journal,
        dispatcher=dispatcher,
        boundary=boundary,
    )


def _with_kind(payload: object, kind: str) -> Result[Mapping[str, object]]:
    if payload is None:
        return Ok(MappingProxyType({"kind": kind}))
    if not isinstance(payload, Mapping):
        return _invalid(
            "payload",
            "effect payload is a mapping",
            given=type(payload).__name__,
            kind=kind,
        )
    body = dict(cast("Mapping[str, object]", payload))
    body.setdefault("kind", kind)
    return Ok(MappingProxyType(body))


def _coerce_boundary(value: object) -> Result[WriteBoundary]:
    if isinstance(value, WriteBoundary):
        return Ok(value)
    token = _clean_token(value)
    if token is None:
        return _invalid(
            "boundary",
            "decision-plus-evidence writes declare atomic or ordered-with-recovery",
            given=repr(value),
            allowed=[item.value for item in WriteBoundary],
        )
    try:
        return Ok(WriteBoundary(token))
    except ValueError:
        return _invalid(
            "boundary",
            "decision-plus-evidence writes declare atomic or ordered-with-recovery",
            given=token,
            allowed=[item.value for item in WriteBoundary],
        )


def _is_partial_ack(ack: SinkAck) -> bool:
    detail = dict(ack.detail)
    return detail.get("partial") is True or detail.get("complete") is False


def _block_entries(refusal: TypedRefusal, *, failure_id: str) -> TypedRefusal:
    context = dict(refusal.context)
    context.setdefault("failure_id", failure_id)
    context.setdefault("blocks_entries", True)
    context.setdefault("blocks_exits", False)
    return TypedRefusal(
        category=RefusalCategory.STORAGE_FAILURE,
        retryability=refusal.retryability,
        context=context,
        after_condition_descriptor=refusal.after_condition_descriptor,
    )
