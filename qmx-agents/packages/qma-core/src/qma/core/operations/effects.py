"""Effect-specific retry and reconcile outcomes (Story 54.3 / 62.2; FR-WF-22).

``none`` / ``read`` may retry. ``append-evidence`` dedupes on the key.
``mutate-config`` is compare-and-set on ``config_revision``. ``place-run``
treats ``logical_invocation_id`` as the run identity. ``external-egress`` MUST
obtain a receipt or become ``unknown`` and MUST NOT blind-retry (SCN-0021
Then 3; SCN-0026 Then 2). ``reconcile_policy`` ``never-retry`` and
``unknown-manual`` win over default host retry. CAS ``conflict`` is not a
retry. Parent AD-25 ``unknown-blocked`` is never auto-retried. Outbox replay
is not a second dispatch (Story 57.2). This module does not mint a per-pack
retry enum.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal

from qma.core.refusals.variants import BlindRetryRefused, StaleObservation
from qma.core.vocabulary.enums import (
    EffectClass,
    EffectRetryOutcome,
    JobHandleState,
    ReconcilePolicy,
)
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core.refusal import Ok, RefusalCategory, Result, Retryability, TypedRefusal

__all__ = [
    "CAS_CONFLICT_IS_RETRY",
    "EFFECT_RETRY_BY_CLASS",
    "HOST_RETRY_EFFECT_CLASSES",
    "HOST_RETRY_POLICY_OVERRIDE",
    "OUTBOX_REPLAY_IS_SECOND_DISPATCH",
    "PER_PACK_RETRY_ENUM_MINTED",
    "RECONCILE_POLICIES",
    "UNKNOWN_BLOCKED_AUTO_RETRY",
    "UNKNOWN_BLOCKED_FIELD",
    "EffectOutcome",
    "apply_effect_outcome",
    "cas_config_revision",
    "effect_retry_kind",
    "host_may_dispatch",
    "host_may_send_again",
    "host_retry_applies",
    "is_cas_conflict",
    "is_unknown_blocked",
    "may_retry_effect",
    "parse_reconcile_policy",
    "parse_retryability",
    "place_run_identity",
    "reconcile_external_egress",
    "reconcile_policy_wins_over_host_retry",
]


RECONCILE_POLICIES: Final[frozenset[str]] = frozenset(member.value for member in ReconcilePolicy)

EFFECT_RETRY_BY_CLASS: Final[Mapping[EffectClass, EffectRetryOutcome]] = MappingProxyType(
    {
        EffectClass.NONE: EffectRetryOutcome.MAY_RETRY,
        EffectClass.READ: EffectRetryOutcome.MAY_RETRY,
        EffectClass.APPEND_EVIDENCE: EffectRetryOutcome.DEDUPE,
        EffectClass.MUTATE_CONFIG: EffectRetryOutcome.CAS,
        EffectClass.PLACE_RUN: EffectRetryOutcome.RUN_IDENTITY,
        EffectClass.EXTERNAL_EGRESS: EffectRetryOutcome.RECEIPT_OR_UNKNOWN,
    }
)

# Derived from Story 54.3 — do not add classes here; that would loosen the matrix.
HOST_RETRY_EFFECT_CLASSES: Final[frozenset[EffectClass]] = frozenset(
    effect for effect, kind in EFFECT_RETRY_BY_CLASS.items() if kind is EffectRetryOutcome.MAY_RETRY
)
HOST_RETRY_POLICY_OVERRIDE: Final[frozenset[ReconcilePolicy]] = frozenset(
    {ReconcilePolicy.NEVER_RETRY, ReconcilePolicy.UNKNOWN_MANUAL}
)
CAS_CONFLICT_IS_RETRY: Final[bool] = False
UNKNOWN_BLOCKED_AUTO_RETRY: Final[bool] = False
OUTBOX_REPLAY_IS_SECOND_DISPATCH: Final[bool] = False
PER_PACK_RETRY_ENUM_MINTED: Final[bool] = False
UNKNOWN_BLOCKED_FIELD: Final[str] = "unknown-blocked"

_Disposition = Literal[
    "retry",
    "dedupe",
    "cas-apply",
    "run-identity",
    "receipt",
    "unknown",
    "replay",
]


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _parse_effect(value: object) -> Result[EffectClass]:
    try:
        return Ok(parse_closed(EffectClass, value))
    except VocabularyError as exc:
        return _invalid("effect_class", str(exc), given=repr(value))


def parse_reconcile_policy(value: object) -> Result[ReconcilePolicy]:
    """Parse the closed AD-24 reconcile policy. ``blind-retry`` is not a member."""
    try:
        return Ok(parse_closed(ReconcilePolicy, value))
    except VocabularyError as exc:
        return _invalid("reconcile_policy", str(exc), given=repr(value))


def effect_retry_kind(effect_class: object) -> Result[EffectRetryOutcome]:
    """Map a closed ``effect_class`` onto its Story 54.3 retry outcome."""
    parsed = _parse_effect(effect_class)
    if not isinstance(parsed, Ok):
        return parsed
    return Ok(EFFECT_RETRY_BY_CLASS[parsed.value])


def may_retry_effect(effect_class: object) -> Result[bool]:
    """True only for ``none`` and ``read`` (FR-WF-22)."""
    kind = effect_retry_kind(effect_class)
    if not isinstance(kind, Ok):
        return kind
    return Ok(kind.value is EffectRetryOutcome.MAY_RETRY)


def parse_retryability(value: object) -> Result[Retryability]:
    """Parse CT-04 retryability. Host retry is on when the value is not ``no``."""
    if isinstance(value, Retryability):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(Retryability(value))
        except ValueError:
            return _invalid(
                "retryability",
                "retryability is yes | no | after-condition",
                given=value,
            )
    return _invalid(
        "retryability",
        "retryability is yes | no | after-condition",
        given=repr(value),
    )


def host_retry_applies(*, effect_class: object, retryability: object) -> Result[bool]:
    """Default host retry is on only for ``none`` / ``read`` when retryability is not ``NO``.

    Does not loosen the Story 54.3 matrix: other effect classes stay off.
    """
    allowed = may_retry_effect(effect_class)
    if not isinstance(allowed, Ok):
        return allowed
    parsed = parse_retryability(retryability)
    if not isinstance(parsed, Ok):
        return parsed
    return Ok(bool(allowed.value and parsed.value is not Retryability.NO))


def reconcile_policy_wins_over_host_retry(reconcile_policy: object) -> Result[bool]:
    """``never-retry`` and ``unknown-manual`` win over default host retry (FR-PG-25)."""
    parsed = parse_reconcile_policy(reconcile_policy)
    if not isinstance(parsed, Ok):
        return parsed
    return Ok(parsed.value in HOST_RETRY_POLICY_OVERRIDE)


def is_cas_conflict(value: object) -> bool:
    """True when a mutate-config CAS result is ``conflict`` (not a retry)."""
    if value is True:
        return True
    if not isinstance(value, TypedRefusal):
        return False
    return value.context.get("cas") is True


def is_unknown_blocked(value: object) -> bool:
    """True when parent AD-25 ``unknown-blocked`` is the outcome (never auto-retried)."""
    if value is True:
        return True
    if not isinstance(value, TypedRefusal):
        return False
    return (
        value.context.get("field") == UNKNOWN_BLOCKED_FIELD
        or value.context.get("unknown_blocked") is True
    )


def host_may_dispatch(
    *,
    effect_class: object,
    reconcile_policy: object,
    attempt_id: object,
    prior_result: Mapping[str, object] | None = None,
    unknown_blocked: bool = False,
    cas_conflict: bool = False,
) -> Result[bool]:
    """Whether the host may perform a send for this envelope attempt.

    Attempt 1 may send. A later attempt is a host retry only for ``none`` /
    ``read`` when ``reconcile_policy`` does not win. ``prior_result`` is outbox
    replay / dedupe, not a second dispatch. ``unknown-blocked`` and CAS
    ``conflict`` never dispatch again.
    """
    if unknown_blocked or cas_conflict or prior_result is not None:
        return Ok(False)
    if isinstance(attempt_id, bool) or not isinstance(attempt_id, int) or attempt_id < 1:
        return _invalid(
            "attempt_id",
            "attempt_id must be a positive integer",
            given=repr(attempt_id),
        )
    if attempt_id == 1:
        return Ok(True)
    wins = reconcile_policy_wins_over_host_retry(reconcile_policy)
    if not isinstance(wins, Ok):
        return wins
    if wins.value:
        return Ok(False)
    return may_retry_effect(effect_class)


def host_may_send_again(
    *,
    effect_class: object,
    reconcile_policy: object,
    retryability: object,
    cas_conflict: bool = False,
    unknown_blocked: bool = False,
    receipt: object | None = None,
) -> Result[bool]:
    """Whether the host may take another send after a first attempt (FR-PG-24).

    External-egress without a receipt stays unknown. CAS conflict is not a
    retry. ``unknown-blocked`` is never auto-retried. Policy override wins.
    """
    if unknown_blocked:
        return Ok(UNKNOWN_BLOCKED_AUTO_RETRY)
    if cas_conflict:
        return Ok(CAS_CONFLICT_IS_RETRY)
    wins = reconcile_policy_wins_over_host_retry(reconcile_policy)
    if not isinstance(wins, Ok):
        return wins
    if wins.value:
        return Ok(False)
    parsed_effect = _parse_effect(effect_class)
    if not isinstance(parsed_effect, Ok):
        return parsed_effect
    if parsed_effect.value is EffectClass.EXTERNAL_EGRESS and receipt is None:
        return Ok(False)
    return host_retry_applies(effect_class=effect_class, retryability=retryability)


def cas_config_revision(*, bound: object, live: object) -> Result[int]:
    """Compare-and-set on ``config_revision`` (``mutate-config``)."""
    if isinstance(bound, bool) or not isinstance(bound, int):
        return _invalid("config_revision", "config_revision must be an integer", given=repr(bound))
    if isinstance(live, bool) or not isinstance(live, int):
        return _invalid(
            "config_revision",
            "live config_revision must be an integer",
            given=repr(live),
        )
    if bound != live:
        return StaleObservation.of(
            field="config_revision",
            bound=bound,
            live=live,
            cas=True,
            reason="cas_mismatch",
        )
    return Ok(bound)


def place_run_identity(logical_invocation_id: object) -> Result[str]:
    """``place-run`` uses ``logical_invocation_id`` as the run identity."""
    if not isinstance(logical_invocation_id, str) or logical_invocation_id.strip() == "":
        return _invalid(
            "logical_invocation_id",
            "place-run run identity is a non-empty logical_invocation_id",
            given=repr(logical_invocation_id),
        )
    return Ok(logical_invocation_id.strip())


def reconcile_external_egress(
    *,
    logical_invocation_id: object,
    reconcile_policy: object,
    receipt: object | None = None,
    prior_result: Mapping[str, object] | None = None,
    is_retry: bool = False,
) -> Result[EffectOutcome]:
    """Uncertain external effect stays ``unknown`` until reconcile (SCN-0021 Then 3)."""
    identity = place_run_identity(logical_invocation_id)
    if not isinstance(identity, Ok):
        return identity
    policy = parse_reconcile_policy(reconcile_policy)
    if not isinstance(policy, Ok):
        return policy
    if prior_result is not None:
        return Ok(
            EffectOutcome(
                effect_class=EffectClass.EXTERNAL_EGRESS,
                retry_kind=EffectRetryOutcome.RECEIPT_OR_UNKNOWN,
                disposition="replay",
                reconcile_policy=policy.value,
                logical_invocation_id=identity.value,
                handle_state=JobHandleState.UNKNOWN if receipt is None else JobHandleState.DONE,
                prior_result=prior_result,
                duplicated=False,
            )
        )
    if receipt is not None:
        return Ok(
            EffectOutcome(
                effect_class=EffectClass.EXTERNAL_EGRESS,
                retry_kind=EffectRetryOutcome.RECEIPT_OR_UNKNOWN,
                disposition="receipt",
                reconcile_policy=policy.value,
                logical_invocation_id=identity.value,
                handle_state=JobHandleState.DONE,
                receipt=True,
            )
        )
    if is_retry:
        return BlindRetryRefused.of(
            logical_invocation_id=identity.value,
            reconcile_policy=policy.value.value,
        )
    return Ok(
        EffectOutcome(
            effect_class=EffectClass.EXTERNAL_EGRESS,
            retry_kind=EffectRetryOutcome.RECEIPT_OR_UNKNOWN,
            disposition="unknown",
            reconcile_policy=policy.value,
            logical_invocation_id=identity.value,
            handle_state=JobHandleState.UNKNOWN,
            receipt=False,
        )
    )


@dataclass(frozen=True, slots=True)
class EffectOutcome:
    """Decided retry/reconcile outcome for one public invocation."""

    effect_class: EffectClass
    retry_kind: EffectRetryOutcome
    disposition: _Disposition
    reconcile_policy: ReconcilePolicy
    logical_invocation_id: str
    handle_state: JobHandleState | None = None
    run_identity: str | None = None
    receipt: bool | None = None
    duplicated: bool = False
    prior_result: Mapping[str, object] | None = None
    config_revision: int | None = None

    def __post_init__(self) -> None:
        if self.prior_result is not None:
            object.__setattr__(self, "prior_result", MappingProxyType(dict(self.prior_result)))

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "disposition": self.disposition,
            "duplicated": self.duplicated,
            "effect_class": self.effect_class.value,
            "logical_invocation_id": self.logical_invocation_id,
            "reconcile_policy": self.reconcile_policy.value,
            "retry_kind": self.retry_kind.value,
        }
        if self.handle_state is not None:
            payload["handle_state"] = self.handle_state.value
        if self.run_identity is not None:
            payload["run_identity"] = self.run_identity
        if self.receipt is not None:
            payload["receipt"] = self.receipt
        if self.config_revision is not None:
            payload["config_revision"] = self.config_revision
        if self.prior_result is not None:
            payload["prior_result"] = dict(self.prior_result)
        return MappingProxyType(payload)


def apply_effect_outcome(
    *,
    effect_class: object,
    reconcile_policy: object,
    logical_invocation_id: object,
    config_revision: object | None = None,
    live_config_revision: object | None = None,
    receipt: object | None = None,
    prior_result: Mapping[str, object] | None = None,
    is_retry: bool = False,
) -> Result[EffectOutcome]:
    """Apply FR-WF-22 effect-specific outcomes and the closed reconcile policy."""
    effect = _parse_effect(effect_class)
    if not isinstance(effect, Ok):
        return effect
    policy = parse_reconcile_policy(reconcile_policy)
    if not isinstance(policy, Ok):
        return policy
    identity = place_run_identity(logical_invocation_id)
    if not isinstance(identity, Ok):
        return identity
    kind = EFFECT_RETRY_BY_CLASS[effect.value]

    if effect.value is EffectClass.EXTERNAL_EGRESS:
        return reconcile_external_egress(
            logical_invocation_id=identity.value,
            reconcile_policy=policy.value,
            receipt=receipt,
            prior_result=prior_result,
            is_retry=is_retry,
        )

    if effect.value is EffectClass.APPEND_EVIDENCE:
        if prior_result is not None:
            return Ok(
                EffectOutcome(
                    effect_class=effect.value,
                    retry_kind=kind,
                    disposition="dedupe",
                    reconcile_policy=policy.value,
                    logical_invocation_id=identity.value,
                    prior_result=prior_result,
                    duplicated=False,
                )
            )
        return Ok(
            EffectOutcome(
                effect_class=effect.value,
                retry_kind=kind,
                disposition="dedupe",
                reconcile_policy=policy.value,
                logical_invocation_id=identity.value,
                duplicated=False,
            )
        )

    if effect.value is EffectClass.MUTATE_CONFIG:
        bound = 0 if config_revision is None else config_revision
        live = bound if live_config_revision is None else live_config_revision
        cas = cas_config_revision(bound=bound, live=live)
        if not isinstance(cas, Ok):
            return cas
        return Ok(
            EffectOutcome(
                effect_class=effect.value,
                retry_kind=kind,
                disposition="cas-apply",
                reconcile_policy=policy.value,
                logical_invocation_id=identity.value,
                config_revision=cas.value,
            )
        )

    if effect.value is EffectClass.PLACE_RUN:
        return Ok(
            EffectOutcome(
                effect_class=effect.value,
                retry_kind=kind,
                disposition="run-identity",
                reconcile_policy=policy.value,
                logical_invocation_id=identity.value,
                run_identity=identity.value,
                prior_result=prior_result,
                duplicated=False,
            )
        )

    if is_retry and policy.value in HOST_RETRY_POLICY_OVERRIDE:
        return _invalid(
            "reconcile_policy",
            "never-retry and unknown-manual win over default host retry",
            reconcile_policy=policy.value.value,
            effect_class=effect.value.value,
        )

    return Ok(
        EffectOutcome(
            effect_class=effect.value,
            retry_kind=kind,
            disposition="retry",
            reconcile_policy=policy.value,
            logical_invocation_id=identity.value,
            prior_result=prior_result,
        )
    )
