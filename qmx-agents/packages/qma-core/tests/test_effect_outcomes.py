"""Story 54.3 — effect-specific retry outcomes and nested permission narrowing."""

from __future__ import annotations

from qma.core.operations import (
    EFFECT_RETRY_BY_CLASS,
    RECONCILE_POLICIES,
    apply_effect_outcome,
    cas_config_revision,
    effect_retry_kind,
    may_retry_effect,
    parse_reconcile_policy,
    place_run_identity,
    reconcile_external_egress,
)
from qma.core.ports.permissions import (
    NESTED_INVOCATION_UNIONS_PERMISSIONS,
    nested_invocation_permissions,
)
from qma.core.refusals import BlindRetryRefused, NestedPermissionUnionRefused, StaleObservation
from qma.core.vocabulary import EffectClass, EffectRetryOutcome, JobHandleState, ReconcilePolicy
from qmf.core import is_ok, is_refusal


def test_every_effect_class_has_a_closed_retry_outcome() -> None:
    assert set(EFFECT_RETRY_BY_CLASS) == set(EffectClass)
    assert EFFECT_RETRY_BY_CLASS[EffectClass.NONE] is EffectRetryOutcome.MAY_RETRY
    assert EFFECT_RETRY_BY_CLASS[EffectClass.READ] is EffectRetryOutcome.MAY_RETRY
    assert EFFECT_RETRY_BY_CLASS[EffectClass.APPEND_EVIDENCE] is EffectRetryOutcome.DEDUPE
    assert EFFECT_RETRY_BY_CLASS[EffectClass.MUTATE_CONFIG] is EffectRetryOutcome.CAS
    assert EFFECT_RETRY_BY_CLASS[EffectClass.PLACE_RUN] is EffectRetryOutcome.RUN_IDENTITY
    assert EFFECT_RETRY_BY_CLASS[EffectClass.EXTERNAL_EGRESS] is (
        EffectRetryOutcome.RECEIPT_OR_UNKNOWN
    )
    none_retry = may_retry_effect("none")
    read_retry = may_retry_effect("read")
    egress = may_retry_effect("external-egress")
    assert is_ok(none_retry) and none_retry.value is True
    assert is_ok(read_retry) and read_retry.value is True
    assert is_ok(egress) and egress.value is False
    kind = effect_retry_kind("append-evidence")
    assert is_ok(kind)
    assert kind.value is EffectRetryOutcome.DEDUPE


def test_reconcile_policy_is_the_closed_ad24_set() -> None:
    assert {
        "query-then-decide",
        "unknown-manual",
        "never-retry",
    } == RECONCILE_POLICIES
    for token in RECONCILE_POLICIES:
        parsed = parse_reconcile_policy(token)
        assert is_ok(parsed)
        assert parsed.value is ReconcilePolicy(token)
    refused = parse_reconcile_policy("blind-retry")
    assert is_refusal(refused)
    assert refused.context["field"] == "reconcile_policy"


def test_none_and_read_may_retry() -> None:
    for effect in ("none", "read"):
        first = apply_effect_outcome(
            effect_class=effect,
            reconcile_policy="query-then-decide",
            logical_invocation_id="inv:1",
        )
        retry = apply_effect_outcome(
            effect_class=effect,
            reconcile_policy="query-then-decide",
            logical_invocation_id="inv:1",
            is_retry=True,
        )
        assert is_ok(first) and is_ok(retry)
        assert first.value.disposition == "retry"
        assert retry.value.disposition == "retry"
        blocked = apply_effect_outcome(
            effect_class=effect,
            reconcile_policy="never-retry",
            logical_invocation_id="inv:1",
            is_retry=True,
        )
        assert is_refusal(blocked)


def test_append_evidence_dedupes_on_the_key() -> None:
    prior = {"entry": "already-appended"}
    first = apply_effect_outcome(
        effect_class="append-evidence",
        reconcile_policy="query-then-decide",
        logical_invocation_id="inv:ev",
    )
    replay = apply_effect_outcome(
        effect_class="append-evidence",
        reconcile_policy="query-then-decide",
        logical_invocation_id="inv:ev",
        prior_result=prior,
        is_retry=True,
    )
    assert is_ok(first) and is_ok(replay)
    assert first.value.retry_kind is EffectRetryOutcome.DEDUPE
    assert replay.value.disposition == "dedupe"
    assert replay.value.duplicated is False
    assert dict(replay.value.prior_result or {}) == prior


def test_mutate_config_is_cas_on_config_revision() -> None:
    applied = apply_effect_outcome(
        effect_class="mutate-config",
        reconcile_policy="query-then-decide",
        logical_invocation_id="inv:cfg",
        config_revision=4,
        live_config_revision=4,
    )
    assert is_ok(applied)
    assert applied.value.disposition == "cas-apply"
    assert applied.value.config_revision == 4
    conflict = cas_config_revision(bound=4, live=5)
    assert is_refusal(conflict)
    assert isinstance(conflict, StaleObservation)
    assert conflict.context["cas"] is True
    refused = apply_effect_outcome(
        effect_class="mutate-config",
        reconcile_policy="query-then-decide",
        logical_invocation_id="inv:cfg",
        config_revision=4,
        live_config_revision=5,
    )
    assert is_refusal(refused)


def test_place_run_uses_logical_invocation_id_as_run_identity() -> None:
    identity = place_run_identity("inv:run-7")
    assert is_ok(identity)
    assert identity.value == "inv:run-7"
    outcome = apply_effect_outcome(
        effect_class="place-run",
        reconcile_policy="query-then-decide",
        logical_invocation_id="inv:run-7",
        prior_result={"run": "inv:run-7"},
    )
    assert is_ok(outcome)
    assert outcome.value.disposition == "run-identity"
    assert outcome.value.run_identity == "inv:run-7"
    assert outcome.value.duplicated is False


def test_external_egress_without_receipt_is_unknown_and_must_not_blind_retry() -> None:
    first = reconcile_external_egress(
        logical_invocation_id="inv:egress",
        reconcile_policy="query-then-decide",
        receipt=None,
        is_retry=False,
    )
    assert is_ok(first)
    assert first.value.disposition == "unknown"
    assert first.value.handle_state is JobHandleState.UNKNOWN
    assert first.value.handle_state not in {
        JobHandleState.FAILED,
        JobHandleState.ABORTED,
        JobHandleState.DONE,
    }
    replay = reconcile_external_egress(
        logical_invocation_id="inv:egress",
        reconcile_policy="query-then-decide",
        prior_result={"order": "already-sent"},
        is_retry=True,
    )
    assert is_ok(replay)
    assert replay.value.disposition == "replay"
    assert replay.value.duplicated is False
    assert dict(replay.value.prior_result or {}) == {"order": "already-sent"}
    blind = reconcile_external_egress(
        logical_invocation_id="inv:egress",
        reconcile_policy="query-then-decide",
        receipt=None,
        is_retry=True,
    )
    assert is_refusal(blind)
    assert isinstance(blind, BlindRetryRefused)
    assert blind.context["reason"] == "external_egress_must_not_blind_retry"
    never = apply_effect_outcome(
        effect_class="external-egress",
        reconcile_policy="never-retry",
        logical_invocation_id="inv:egress",
        is_retry=True,
    )
    assert is_refusal(never)
    assert isinstance(never, BlindRetryRefused)
    receipted = apply_effect_outcome(
        effect_class="external-egress",
        reconcile_policy="unknown-manual",
        logical_invocation_id="inv:egress",
        receipt={"ack": "ok"},
    )
    assert is_ok(receipted)
    assert receipted.value.disposition == "receipt"
    assert receipted.value.handle_state is JobHandleState.DONE


def test_nested_invocation_does_not_union_permissions() -> None:
    assert NESTED_INVOCATION_UNIONS_PERMISSIONS is False
    narrowed = nested_invocation_permissions(
        ["library.read", "library.run"],
        ["library.read"],
    )
    assert is_ok(narrowed)
    assert narrowed.value == frozenset({"library.read"})
    unioned = nested_invocation_permissions(
        ["library.read"],
        ["library.read", "library.run"],
    )
    assert is_refusal(unioned)
    assert isinstance(unioned, NestedPermissionUnionRefused)
    extras = unioned.context["extras"]
    assert extras in (("library.run",), ["library.run"])
    forced = nested_invocation_permissions(
        ["library.read"],
        ["library.read"],
        union=True,
    )
    assert is_refusal(forced)
    assert isinstance(forced, NestedPermissionUnionRefused)
