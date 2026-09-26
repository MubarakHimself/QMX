"""Host retry loop for effect ``none`` / ``read`` (Story 62.1 / 62.2 / 62.3).

A public call whose effect class is ``none`` or ``read`` and whose typed
retryability is not ``NO`` retries in the host until success, until
``retryability=NO``, or until the host-registered attempt ceiling. Attempts
increment ``attempt_id`` on the same ``logical_invocation_id``. The operator
is not the recovery loop.

The Story 54.3 / parent AD-24 effect-class matrix is not loosened: only
``none`` / ``read`` enter the loop. ``external-egress`` without a receipt
becomes ``unknown`` and MUST NOT blind-retry (no second send). CAS
``conflict`` is not a retry. ``append-evidence`` still dedupes; ``place-run``
still uses ``logical_invocation_id`` as run identity; outbox replay is not a
second dispatch (Story 57.2). ``reconcile_policy`` ``never-retry`` and
``unknown-manual`` win over default host retry. Parent AD-25
``unknown-blocked`` is never auto-retried. A pack may set attempts to zero;
it MUST NOT exceed the host ceiling or the matrix. No per-pack retry enum.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qma.core.operations.effects import (
    CAS_CONFLICT_IS_RETRY,
    HOST_RETRY_EFFECT_CLASSES,
    OUTBOX_REPLAY_IS_SECOND_DISPATCH,
    PER_PACK_RETRY_ENUM_MINTED,
    UNKNOWN_BLOCKED_AUTO_RETRY,
    EffectOutcome,
    apply_effect_outcome,
    bind_pack_retry_attempts,
    host_may_dispatch,
    host_may_send_again,
    is_cas_conflict,
    is_unknown_blocked,
    reconcile_policy_wins_over_host_retry,
)
from qma.core.refusals.variants import BlindRetryRefused
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
    "BLIND_EXTERNAL_EGRESS_RETRY",
    "CAS_CONFLICT_IS_RETRY",
    "EFFECT_CLASS_TYPES_EXISTED_AT_INSPECT_SHA",
    "HOST_RETRY_ATTEMPT_CEILING_KEY",
    "HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY",
    "HOST_RETRY_EFFECT_CLASSES",
    "HOST_RETRY_INSPECT_SHA",
    "HOST_RETRY_LOOP_EXISTED_AT_INSPECT_SHA",
    "HOST_RETRY_LOOP_OWNER",
    "OPERATOR_IS_RECOVERY_LOOP",
    "OUTBOX_REPLAY_IS_SECOND_DISPATCH",
    "PER_PACK_RETRY_ENUM_MINTED",
    "RECONCILE_POLICY_TYPES_EXISTED_AT_INSPECT_SHA",
    "STORY_54_3_EFFECT_RETRY_MATRIX_LOOSENED",
    "UNKNOWN_BLOCKED_AUTO_RETRY",
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
BLIND_EXTERNAL_EGRESS_RETRY: Final[bool] = False


class HostRetryStopReason(StrEnum):
    """Why the host retry loop stopped (FR-PG-23 / FR-PG-24 / FR-PG-25 / FR-PG-26)."""

    SUCCESS = "success"
    RETRYABILITY_NO = "retryability_no"
    ATTEMPT_CEILING = "attempt_ceiling"
    PACK_ZERO_ATTEMPTS = "pack_zero_attempts"
    UNKNOWN = "unknown"
    CAS_CONFLICT = "cas_conflict"
    RECONCILE_POLICY = "reconcile_policy"
    UNKNOWN_BLOCKED = "unknown_blocked"
    EFFECT_CLASS = "effect_class"


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
    effect_outcome: EffectOutcome | None = None
    cas_conflict: bool = False
    unknown_blocked: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "operator_is_recovery_loop", False)
        if self.stop_reason is HostRetryStopReason.CAS_CONFLICT:
            object.__setattr__(self, "cas_conflict", True)
        if self.stop_reason is HostRetryStopReason.UNKNOWN_BLOCKED:
            object.__setattr__(self, "unknown_blocked", True)

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "attempt_id": self.attempt_id,
            "attempt_ids": list(self.attempt_ids),
            "cas_conflict": self.cas_conflict,
            "logical_invocation_id": self.logical_invocation_id,
            "operator_is_recovery_loop": self.operator_is_recovery_loop,
            "stop_reason": self.stop_reason.value,
            "unknown_blocked": self.unknown_blocked,
        }
        if self.refusal is not None:
            payload["retryability"] = self.refusal.retryability.value
        if self.effect_outcome is not None:
            payload["disposition"] = self.effect_outcome.disposition
            if self.effect_outcome.handle_state is not None:
                payload["handle_state"] = self.effect_outcome.handle_state.value
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


def _receipt_of(value: object, explicit: object | None) -> object | None:
    if explicit is not None:
        return explicit
    if not isinstance(value, Mapping):
        return None
    payload = cast(Mapping[str, object], value)
    receipt = payload.get("receipt")
    return receipt if receipt else None


def _finish(
    envelope: InvocationEnvelope,
    attempt_ids: tuple[int, ...],
    stop_reason: HostRetryStopReason,
    *,
    value: object | None = None,
    refusal: TypedRefusal | None = None,
    effect_outcome: EffectOutcome | None = None,
) -> Ok[HostRetryResult]:
    return Ok(
        HostRetryResult(
            logical_invocation_id=envelope.logical_invocation_id,
            attempt_ids=attempt_ids,
            attempt_id=attempt_ids[-1] if attempt_ids else envelope.attempt_id,
            envelope=envelope,
            stop_reason=stop_reason,
            operator_is_recovery_loop=OPERATOR_IS_RECOVERY_LOOP,
            value=value,
            refusal=refusal,
            effect_outcome=effect_outcome,
        )
    )


def _blocked_without_dispatch(
    envelope: InvocationEnvelope,
    *,
    receipt: object | None,
    prior_result: Mapping[str, object] | None,
    unknown_blocked: bool,
    cas_conflict: bool,
) -> Result[HostRetryResult]:
    """Stop without a send when the parent matrix forbids dispatch."""
    if unknown_blocked:
        return _finish(envelope, (), HostRetryStopReason.UNKNOWN_BLOCKED)
    if cas_conflict:
        return _finish(envelope, (), HostRetryStopReason.CAS_CONFLICT)
    if prior_result is not None:
        outcome = apply_effect_outcome(
            effect_class=envelope.effect_class,
            reconcile_policy=envelope.reconcile_policy,
            logical_invocation_id=envelope.logical_invocation_id,
            config_revision=envelope.config_revision,
            receipt=receipt,
            prior_result=prior_result,
            is_retry=True,
        )
        if is_refusal(outcome):
            return outcome
        reason = HostRetryStopReason.EFFECT_CLASS
        if outcome.value.disposition in {"unknown", "replay"}:
            reason = HostRetryStopReason.UNKNOWN
        elif outcome.value.disposition == "receipt":
            reason = HostRetryStopReason.SUCCESS
        return _finish(
            envelope,
            (),
            reason,
            value=dict(prior_result),
            effect_outcome=outcome.value,
        )
    wins = reconcile_policy_wins_over_host_retry(envelope.reconcile_policy)
    if is_ok(wins) and wins.value:
        return _finish(envelope, (), HostRetryStopReason.RECONCILE_POLICY)
    if envelope.effect_class is EffectClass.EXTERNAL_EGRESS:
        return BlindRetryRefused.of(
            logical_invocation_id=envelope.logical_invocation_id,
            reconcile_policy=envelope.reconcile_policy.value,
            blind_retry=BLIND_EXTERNAL_EGRESS_RETRY,
        )
    if envelope.effect_class is EffectClass.MUTATE_CONFIG:
        return _finish(envelope, (), HostRetryStopReason.CAS_CONFLICT)
    return _finish(envelope, (), HostRetryStopReason.EFFECT_CLASS)


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
        *,
        receipt: object | None = None,
        prior_result: Mapping[str, object] | None = None,
        unknown_blocked: bool = False,
        cas_conflict: bool = False,
        pack_attempts: object | None = None,
    ) -> Result[HostRetryResult]:
        """Retry a public ``none`` / ``read`` call on one ``logical_invocation_id``.

        Other effect classes consult the parent matrix and never take a second
        send. ``prior_result`` is replay/dedupe, not a dispatch. Pack attempts
        of zero means the host does not retry that op (FR-PG-26).
        """
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
        pack_zero = False
        bound_pack = pack_attempts
        if pack_attempts is not None:
            bound = bind_pack_retry_attempts(
                pack_attempts=pack_attempts,
                host_ceiling=ceiling.value,
                effect_class=current.effect_class,
            )
            if is_refusal(bound):
                return bound
            cap = bound.value.send_cap
            pack_zero = bound.value.zero_attempts
            bound_pack = bound.value.pack_attempts
        if current.attempt_id > cap:
            return invalid_input(
                "attempt_id",
                "attempt_id exceeds the host-registered attempt ceiling",
                attempt_id=current.attempt_id,
                ceiling=cap,
                registry_key=HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY,
            )

        may = host_may_dispatch(
            effect_class=current.effect_class,
            reconcile_policy=current.reconcile_policy,
            attempt_id=current.attempt_id,
            prior_result=prior_result,
            unknown_blocked=unknown_blocked,
            cas_conflict=cas_conflict,
        )
        if is_refusal(may):
            return may
        if not may.value:
            return _blocked_without_dispatch(
                current,
                receipt=receipt,
                prior_result=prior_result,
                unknown_blocked=unknown_blocked,
                cas_conflict=cas_conflict,
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
            ids = tuple(attempt_ids)
            if is_ok(last):
                if current.effect_class is EffectClass.EXTERNAL_EGRESS:
                    got = _receipt_of(last.value, receipt)
                    outcome = apply_effect_outcome(
                        effect_class=current.effect_class,
                        reconcile_policy=current.reconcile_policy,
                        logical_invocation_id=logical,
                        receipt=got,
                        is_retry=False,
                    )
                    if is_refusal(outcome):
                        return outcome
                    if got is None:
                        return _finish(
                            current,
                            ids,
                            HostRetryStopReason.UNKNOWN,
                            value=last.value,
                            effect_outcome=outcome.value,
                        )
                    return _finish(
                        current,
                        ids,
                        HostRetryStopReason.SUCCESS,
                        value=last.value,
                        effect_outcome=outcome.value,
                    )
                return _finish(
                    current,
                    ids,
                    HostRetryStopReason.SUCCESS,
                    value=last.value,
                )
            if is_unknown_blocked(last) or unknown_blocked:
                return _finish(
                    current,
                    ids,
                    HostRetryStopReason.UNKNOWN_BLOCKED,
                    refusal=last,
                )
            if is_cas_conflict(last) or cas_conflict:
                return _finish(
                    current,
                    ids,
                    HostRetryStopReason.CAS_CONFLICT,
                    refusal=last,
                )
            if current.effect_class is EffectClass.EXTERNAL_EGRESS:
                outcome = apply_effect_outcome(
                    effect_class=current.effect_class,
                    reconcile_policy=current.reconcile_policy,
                    logical_invocation_id=logical,
                    receipt=None,
                    is_retry=False,
                )
                if is_refusal(outcome):
                    return outcome
                return _finish(
                    current,
                    ids,
                    HostRetryStopReason.UNKNOWN,
                    refusal=last,
                    effect_outcome=outcome.value,
                )
            if last.retryability is Retryability.NO:
                return _finish(
                    current,
                    ids,
                    HostRetryStopReason.RETRYABILITY_NO,
                    refusal=last,
                )
            next_id = current.attempt_id + 1
            if next_id > cap:
                reason = (
                    HostRetryStopReason.PACK_ZERO_ATTEMPTS
                    if pack_zero
                    else HostRetryStopReason.ATTEMPT_CEILING
                )
                return _finish(
                    current,
                    ids,
                    reason,
                    refusal=last,
                )
            again = host_may_send_again(
                effect_class=current.effect_class,
                reconcile_policy=current.reconcile_policy,
                retryability=last.retryability,
                cas_conflict=is_cas_conflict(last),
                unknown_blocked=is_unknown_blocked(last),
                receipt=None,
                pack_attempts=bound_pack,
            )
            if is_refusal(again):
                return again
            if not again.value:
                if pack_zero:
                    return _finish(
                        current,
                        ids,
                        HostRetryStopReason.PACK_ZERO_ATTEMPTS,
                        refusal=last,
                    )
                wins = reconcile_policy_wins_over_host_retry(current.reconcile_policy)
                reason = HostRetryStopReason.EFFECT_CLASS
                if is_ok(wins) and wins.value:
                    reason = HostRetryStopReason.RECONCILE_POLICY
                return _finish(current, ids, reason, refusal=last)
            outcome = apply_effect_outcome(
                effect_class=current.effect_class,
                reconcile_policy=current.reconcile_policy,
                logical_invocation_id=logical,
                is_retry=True,
            )
            if is_refusal(outcome):
                return _finish(
                    current,
                    ids,
                    HostRetryStopReason.RECONCILE_POLICY,
                    refusal=last,
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
        return _finish(
            current,
            tuple(attempt_ids),
            HostRetryStopReason.ATTEMPT_CEILING,
            refusal=last,
        )
