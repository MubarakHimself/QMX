"""Fail-closed hook timeout resolution that preserves evidence (FR-Q32; CT-41).

Timeout spans are cited only as ``registry:hook.timeout_*`` keys — never numeric
constants. Phase-specific fail rules live in ``qma.core.vocabulary.hooks``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

from qma.core.plugins.hooks import HookResult, build_hook_result
from qma.core.vocabulary.enums import HookControl, HookResultDecision
from qma.core.vocabulary.hooks import (
    BEFORE_LEDGER_APPEND_EVENT,
    HOOK_TIMEOUT_REASON,
    parse_hook_event_name,
    timeout_decision_for_event,
)
from qma.daemon.journal.variables import registry_key

__all__ = [
    "HOOK_TIMEOUT_AFTER_KEY",
    "HOOK_TIMEOUT_BEFORE_KEY",
    "HOOK_TIMEOUT_CONTROL_KEY",
    "HOOK_TIMEOUT_KEYS",
    "HookTimeoutResolution",
    "HookTimeoutTelemetry",
    "HookTimeoutTelemetrySink",
    "resolve_hook_timeout",
    "timeout_registry_key_for_event",
]


HOOK_TIMEOUT_BEFORE_KEY: Final[str] = registry_key("hook.timeout_before")
HOOK_TIMEOUT_AFTER_KEY: Final[str] = registry_key("hook.timeout_after")
HOOK_TIMEOUT_CONTROL_KEY: Final[str] = registry_key("hook.timeout_control")

HOOK_TIMEOUT_KEYS: Final[frozenset[str]] = frozenset(
    {
        HOOK_TIMEOUT_BEFORE_KEY,
        HOOK_TIMEOUT_AFTER_KEY,
        HOOK_TIMEOUT_CONTROL_KEY,
    }
)


def timeout_registry_key_for_event(event: str) -> str:
    """Cite the phase's ``registry:hook.timeout_*`` key — never a duration value."""
    name = parse_hook_event_name(event)
    if name.startswith("before_"):
        return HOOK_TIMEOUT_BEFORE_KEY
    if name.startswith("after_"):
        return HOOK_TIMEOUT_AFTER_KEY
    if name in {HookControl.AGENT_STOP.value, HookControl.REVIEW_REQUIRED.value}:
        return HOOK_TIMEOUT_CONTROL_KEY
    msg = f"no timeout registry key for event {name!r} (FR-Q32; CT-41)"
    raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class HookTimeoutTelemetry:
    """Telemetry record emitted on a fail-closed ``before_*`` / review timeout."""

    event: str
    decision: str
    reason: str
    timeout_key: str
    correlation_id: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "kind": "hook_timeout",
                "event": self.event,
                "decision": self.decision,
                "reason": self.reason,
                "timeout_key": self.timeout_key,
                "correlation_id": self.correlation_id,
            }
        )


@dataclass
class HookTimeoutTelemetrySink:
    """In-process telemetry sink for hook timeout records (AD-23 companion)."""

    _records: list[HookTimeoutTelemetry] = field(default_factory=list[HookTimeoutTelemetry])

    def emit(self, record: HookTimeoutTelemetry) -> HookTimeoutTelemetry:
        self._records.append(record)
        return record

    @property
    def records(self) -> tuple[HookTimeoutTelemetry, ...]:
        return tuple(self._records)

    def clear(self) -> None:
        self._records.clear()


@dataclass(frozen=True, slots=True)
class HookTimeoutResolution:
    """Resolved HookResult plus the registry timeout citation and optional telemetry."""

    result: HookResult
    timeout_key: str
    event: str
    telemetry: HookTimeoutTelemetry | None = None

    @property
    def decision(self) -> HookResultDecision:
        return self.result.decision

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "event": self.event,
            "decision": self.result.decision.value,
            "reason": self.result.reason,
            "timeout_key": self.timeout_key,
        }
        if self.telemetry is not None:
            payload["telemetry"] = dict(self.telemetry.to_payload())
        return MappingProxyType(payload)


def _emits_timeout_telemetry(event: str, decision: HookResultDecision) -> bool:
    """Telemetry accompanies fail-closed deny timeouts (FR-Q32)."""
    name = parse_hook_event_name(event)
    if decision is not HookResultDecision.DENY:
        return False
    # before_ledger_append never denies on timeout; after_*/agent_stop observe.
    return name != BEFORE_LEDGER_APPEND_EVENT


def resolve_hook_timeout(
    event: str,
    *,
    correlation_id: str | None = None,
    telemetry: HookTimeoutTelemetrySink | None = None,
) -> HookTimeoutResolution:
    """Resolve a timed-out hook under the phase-specific fail rule (FR-Q32).

    Timeout spans are referenced only through registry keys. A deny timeout
    emits a telemetry record carrying ``correlation_id`` when provided.
    """
    name = parse_hook_event_name(event)
    timeout_key = timeout_registry_key_for_event(name)
    decision = timeout_decision_for_event(name)
    result = build_hook_result(decision, reason=HOOK_TIMEOUT_REASON)
    record: HookTimeoutTelemetry | None = None
    if _emits_timeout_telemetry(name, decision):
        record = HookTimeoutTelemetry(
            event=name,
            decision=decision.value,
            reason=HOOK_TIMEOUT_REASON,
            timeout_key=timeout_key,
            correlation_id=correlation_id,
        )
        if telemetry is not None:
            telemetry.emit(record)
    return HookTimeoutResolution(
        result=result,
        timeout_key=timeout_key,
        event=name,
        telemetry=record,
    )
