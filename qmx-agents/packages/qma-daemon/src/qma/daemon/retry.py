"""Host retry loop for effect ``none`` / ``read`` (Story 62.1; DEC-0457).

A public call whose effect class is ``none`` or ``read`` and whose typed
retryability is not ``NO`` retries in the host until success, until
``retryability=NO``, or until the host-registered attempt ceiling. Attempts
increment ``attempt_id`` on the same ``logical_invocation_id``. The operator
is not the recovery loop.

The attempt ceiling is ``registry:host.retry_attempt_ceiling`` (GAP-0108;
cheap-veto A9). This story mints no number. Tests may inject a ceiling.
Production code does not hardcode a sitting-invented default such as ``3``.

The Story 54.3 / parent AD-24 effect-class matrix is not loosened: only
``none`` / ``read`` enter the loop. Effect-class and ``reconcile_policy``
types existed at inspect SHA ``34c148b``; the host retry **loop** did not.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qma.core.operations.effects import (
    HOST_RETRY_EFFECT_CLASSES,
    apply_effect_outcome,
    host_retry_applies,
)
from qma.core.vocabulary.enums import EffectClass, ReconcilePolicy
from qma.daemon.journal.variables import (
    HOST_RETRY_ATTEMPT_CEILING_KEY,
    HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY,
    GovernedVariableRegistry,
)
from qma.wire.invocation_envelope import InvocationEnvelope, parse_invocation_envelope
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "EFFECT_CLASS_TYPES_EXISTED_AT_INSPECT_SHA",
    "HOST_RETRY_ATTEMPT_CEILING_KEY",
    "HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY",
    "HOST_RETRY_EFFECT_CLASSES",
    "HOST_RETRY_INSPECT_SHA",
    "HOST_RETRY_LOOP_EXISTED_AT_INSPECT_SHA",
    "HOST_RETRY_LOOP_OWNER",
    "OPERATOR_IS_RECOVERY_LOOP",
    "RECONCILE_POLICY_TYPES_EXISTED_AT_INSPECT_SHA",
    "STORY_54_3_EFFECT_RETRY_MATRIX_LOOSENED",
    "HostRetryLoop",
    "HostRetryResult",
    "HostRetryStopReason",
    "claim_effect_class_or_reconcile_policy_absent_at_inspect_sha",
    "claim_host_retry_loop_at_inspect_sha",
]


HOST_RETRY_INSPECT_SHA: Final[str] = "34c148b"
HOST_RETRY_LOOP_EXISTED_AT_INSPECT_SHA: Final[bool] = False
EFFECT_CLASS_TYPES_EXISTED_AT_INSPECT_SHA: Final[bool] = True
RECONCILE_POLICY_TYPES_EXISTED_AT_INSPECT_SHA: Final[bool] = True
STORY_54_3_EFFECT_RETRY_MATRIX_LOOSENED: Final[bool] = False
OPERATOR_IS_RECOVERY_LOOP: Final[bool] = False
HOST_RETRY_LOOP_OWNER: Final[str] = "COMP-QMA-DAEMON"


class HostRetryStopReason(StrEnum):
    """Why the host retry loop stopped (FR-PG-23)."""

    SUCCESS = "success"
    RETRYABILITY_NO = "retryability_no"
    ATTEMPT_CEILING = "attempt_ceiling"


@dataclass(frozen=True, slots=True)
class HostRetryResult:
    """Outcome of one host-owned retry loop on a public call."""

    logical_invocation_id: str
    attempt_ids: tuple[int, ...]
    attempt_id: int
    envelope: InvocationEnvelope
    stop_reason: HostRetryStopReason
    operator_is_recovery_loop: bool = False
    value: object | None = None
    refusal: TypedRefusal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "operator_is_recovery_loop", False)

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "attempt_id": self.attempt_id,
            "attempt_ids": list(self.attempt_ids),
            "logical_invocation_id": self.logical_invocation_id,
            "operator_is_recovery_loop": self.operator_is_recovery_loop,
            "stop_reason": self.stop_reason.value,
        }
        if self.refusal is not None:
            payload["retryability"] = self.refusal.retryability.value
        return MappingProxyType(payload)


def claim_host_retry_loop_at_inspect_sha(existed: object) -> Result[bool]:
    """Claiming the host retry loop existed at inspect SHA ``34c148b`` fails."""
    if existed is True or existed == "true":
        return policy_rejection(
            "host_retry_loop",
            "the host retry loop was absent at inspect SHA 34c148b; effect-class "
            "and reconcile_policy types existed as CONNECT fixtures (DEC-0465; "
            "NFR-PG-04; SCN-0026 Branch D)",
            existed_at_inspect_sha=False,
            inspect_sha=HOST_RETRY_INSPECT_SHA,
            effect_class_types_existed_at_inspect_sha=True,
            reconcile_policy_types_existed_at_inspect_sha=True,
        )
    if existed is not False:
        return invalid_input(
            "existed_at_inspect_sha",
            "inspect-SHA claim is a boolean",
            given=repr(existed),
        )
    return Ok(False)


def claim_effect_class_or_reconcile_policy_absent_at_inspect_sha(
    absent: object,
) -> Result[bool]:
    """Claiming effect-class / reconcile_policy types were absent at 34c148b fails."""
    if absent is True or absent == "true":
        return policy_rejection(
            "effect_class",
            "effect-class and reconcile_policy types existed at inspect SHA "
            "34c148b as CONNECT fixtures; the host retry loop did not "
            "(DEC-0465; NFR-PG-04; SCN-0026 Branch D)",
            existed_at_inspect_sha=True,
            host_retry_loop_existed_at_inspect_sha=False,
            inspect_sha=HOST_RETRY_INSPECT_SHA,
            effect_classes=sorted(member.value for member in EffectClass),
            reconcile_policies=sorted(member.value for member in ReconcilePolicy),
        )
    if absent is not False:
        return invalid_input(
            "absent_at_inspect_sha",
            "inspect-SHA claim is a boolean",
            given=repr(absent),
        )
    return Ok(False)


def _unavailable_ceiling(given: object, *, source: str) -> TypedRefusal:
    shown: object = given if isinstance(given, (str, int, type(None))) else repr(given)
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context={
            "field": "attempt_ceiling",
            "reason": "host retry attempt ceiling is a host-registered "
            "registry row; this story mints no number and production "
            "must not invent a default such as 3 (GAP-0108; cheap-veto A9)",
            "registry_key": HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY,
            "invented_default": False,
            "source": source,
            "given": shown,
        },
    )


def _validate_ceiling(value: object, *, source: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return _unavailable_ceiling(value, source=source)
    return Ok(value)


def _with_attempt(envelope: InvocationEnvelope, attempt_id: int) -> Result[InvocationEnvelope]:
    payload = dict(envelope.to_payload())
    payload["attempt_id"] = attempt_id
    return parse_invocation_envelope(payload)


class HostRetryLoop:
    """COMP-QMA-DAEMON host retry loop on the InvocationEnvelope (FR-PG-23)."""

    def __init__(
        self,
        *,
        variables: GovernedVariableRegistry | None = None,
        injected_ceiling: int | None = None,
    ) -> None:
        self._variables = (
            variables if variables is not None else GovernedVariableRegistry.with_builtins()
        )
        self._injected_ceiling = injected_ceiling

    @property
    def ceiling_key(self) -> str:
        return HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY

    def attempt_ceiling(self) -> Result[int]:
        """Read the host-registered ceiling. Tests may inject a fixture value."""
        if self._injected_ceiling is not None:
            return _validate_ceiling(self._injected_ceiling, source="fixture")
        raw = self._variables.get_value(HOST_RETRY_ATTEMPT_CEILING_KEY)
        if is_refusal(raw):
            return raw
        return _validate_ceiling(raw.value, source="registry")

    def run(
        self,
        envelope: object,
        call: Callable[[InvocationEnvelope], Result[object]],
    ) -> Result[HostRetryResult]:
        """Retry a public ``none`` / ``read`` call on one ``logical_invocation_id``."""
        parsed = (
            Ok(envelope)
            if isinstance(envelope, InvocationEnvelope)
            else parse_invocation_envelope(envelope)
        )
        if is_refusal(parsed):
            return parsed
        current = parsed.value
        ceiling = self.attempt_ceiling()
        if is_refusal(ceiling):
            return ceiling
        cap = ceiling.value
        if current.attempt_id > cap:
            return invalid_input(
                "attempt_id",
                "attempt_id exceeds the host-registered attempt ceiling",
                attempt_id=current.attempt_id,
                ceiling=cap,
                registry_key=HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY,
            )

        attempt_ids: list[int] = []
        logical = current.logical_invocation_id
        last: Result[object] | None = None
        while current.attempt_id <= cap:
            if current.logical_invocation_id != logical:
                return invalid_input(
                    "logical_invocation_id",
                    "host retry keeps the same logical_invocation_id",
                    bound=logical,
                    given=current.logical_invocation_id,
                )
            attempt_ids.append(current.attempt_id)
            last = call(current)
            if is_ok(last):
                return Ok(
                    HostRetryResult(
                        logical_invocation_id=logical,
                        attempt_ids=tuple(attempt_ids),
                        attempt_id=current.attempt_id,
                        envelope=current,
                        stop_reason=HostRetryStopReason.SUCCESS,
                        operator_is_recovery_loop=OPERATOR_IS_RECOVERY_LOOP,
                        value=last.value,
                    )
                )
            if last.retryability is Retryability.NO:
                return Ok(
                    HostRetryResult(
                        logical_invocation_id=logical,
                        attempt_ids=tuple(attempt_ids),
                        attempt_id=current.attempt_id,
                        envelope=current,
                        stop_reason=HostRetryStopReason.RETRYABILITY_NO,
                        operator_is_recovery_loop=OPERATOR_IS_RECOVERY_LOOP,
                        refusal=last,
                    )
                )
            next_id = current.attempt_id + 1
            if next_id > cap:
                return Ok(
                    HostRetryResult(
                        logical_invocation_id=logical,
                        attempt_ids=tuple(attempt_ids),
                        attempt_id=current.attempt_id,
                        envelope=current,
                        stop_reason=HostRetryStopReason.ATTEMPT_CEILING,
                        operator_is_recovery_loop=OPERATOR_IS_RECOVERY_LOOP,
                        refusal=last,
                    )
                )
            applies = host_retry_applies(
                effect_class=current.effect_class,
                retryability=last.retryability,
            )
            if is_refusal(applies) or not applies.value:
                return Ok(
                    HostRetryResult(
                        logical_invocation_id=logical,
                        attempt_ids=tuple(attempt_ids),
                        attempt_id=current.attempt_id,
                        envelope=current,
                        stop_reason=HostRetryStopReason.RETRYABILITY_NO,
                        operator_is_recovery_loop=OPERATOR_IS_RECOVERY_LOOP,
                        refusal=last,
                    )
                )
            outcome = apply_effect_outcome(
                effect_class=current.effect_class,
                reconcile_policy=current.reconcile_policy,
                logical_invocation_id=logical,
                is_retry=True,
            )
            if is_refusal(outcome):
                return Ok(
                    HostRetryResult(
                        logical_invocation_id=logical,
                        attempt_ids=tuple(attempt_ids),
                        attempt_id=current.attempt_id,
                        envelope=current,
                        stop_reason=HostRetryStopReason.RETRYABILITY_NO,
                        operator_is_recovery_loop=OPERATOR_IS_RECOVERY_LOOP,
                        refusal=last,
                    )
                )
            nxt = _with_attempt(current, next_id)
            if is_refusal(nxt):
                return nxt
            current = nxt.value

        if last is None or is_ok(last):
            return invalid_input(
                "attempt_ceiling",
                "host retry loop produced no attempt",
                ceiling=cap,
            )
        return Ok(
            HostRetryResult(
                logical_invocation_id=logical,
                attempt_ids=tuple(attempt_ids),
                attempt_id=attempt_ids[-1],
                envelope=current,
                stop_reason=HostRetryStopReason.ATTEMPT_CEILING,
                operator_is_recovery_loop=OPERATOR_IS_RECOVERY_LOOP,
                refusal=last,
            )
        )
