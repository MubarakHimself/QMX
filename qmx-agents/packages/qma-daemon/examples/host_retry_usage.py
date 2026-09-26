"""L27 reference usage: host retry none/read; no blind external-egress retry (62.1 / 62.2)."""

from __future__ import annotations

from qma.core.operations import public_operation_descriptors
from qma.core.refusals.variants import BlindRetryRefused, StaleObservation
from qma.core.vocabulary.enums import EffectClass, ReconcilePolicy
from qma.daemon.journal.variables import (
    HOST_RETRY_ATTEMPT_CEILING_KEY,
    GovernedVariableRegistry,
)
from qma.daemon.retry import (
    BLIND_EXTERNAL_EGRESS_RETRY,
    CAS_CONFLICT_IS_RETRY,
    EFFECT_CLASS_TYPES_EXISTED_AT_INSPECT_SHA,
    HOST_RETRY_INSPECT_SHA,
    HOST_RETRY_LOOP_EXISTED_AT_INSPECT_SHA,
    OPERATOR_IS_RECOVERY_LOOP,
    RECONCILE_POLICY_TYPES_EXISTED_AT_INSPECT_SHA,
    UNKNOWN_BLOCKED_AUTO_RETRY,
    HostRetryLoop,
    HostRetryStopReason,
    claim_effect_class_or_reconcile_policy_absent_at_inspect_sha,
    claim_host_retry_loop_at_inspect_sha,
)
from qma.wire import compute_input_hash
from qma.wire.invocation_envelope import InvocationEnvelope
from qmf.core import is_ok, is_refusal
from qmf.core.refusal import Ok, RefusalCategory, Result, Retryability, TypedRefusal


def _descriptor():
    for item in public_operation_descriptors():
        if item.op_id == "qmb.analysis.project" and item.version == 1:
            return item
    raise AssertionError("qmb.analysis.project v1 missing")


def _envelope() -> dict[str, object]:
    hashed = compute_input_hash({"run_fp1": "run-1"}, descriptor=_descriptor())
    assert is_ok(hashed)
    return {
        "logical_invocation_id": "inv:read-1",
        "attempt_id": 1,
        "op_id": "qmb.analysis.project",
        "op_version": 1,
        "contribution": {"package_version": "0.1.0", "qualified_id": "analysis-backtest:qmb"},
        "instance_id": "inst:1",
        "config_revision": 4,
        "grant_id": "grant:app",
        "effect_class": "read",
        "idempotency_key": "idem:1",
        "reconcile_policy": "query-then-decide",
        "input_hash": hashed.value,
        "call_depth": 0,
        "caller_kind": "user",
    }


def main() -> None:
    assert HOST_RETRY_LOOP_EXISTED_AT_INSPECT_SHA is False
    assert EFFECT_CLASS_TYPES_EXISTED_AT_INSPECT_SHA is True
    assert RECONCILE_POLICY_TYPES_EXISTED_AT_INSPECT_SHA is True
    assert HOST_RETRY_INSPECT_SHA == "34c148b"
    assert OPERATOR_IS_RECOVERY_LOOP is False
    assert is_refusal(claim_host_retry_loop_at_inspect_sha(True))
    assert is_ok(claim_host_retry_loop_at_inspect_sha(False))
    assert is_refusal(claim_effect_class_or_reconcile_policy_absent_at_inspect_sha(True))
    assert EffectClass.READ.value == "read"
    assert ReconcilePolicy.QUERY_THEN_DECIDE.value == "query-then-decide"

    row = GovernedVariableRegistry.with_builtins().rows()[HOST_RETRY_ATTEMPT_CEILING_KEY]
    assert row.default is None
    assert is_refusal(HostRetryLoop().attempt_ceiling())

    loop = HostRetryLoop(injected_ceiling=2)
    seen: list[int] = []

    def call(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        assert envelope.logical_invocation_id == "inv:read-1"
        if envelope.attempt_id == 1:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.YES,
                context={"reason": "flake"},
            )
        return Ok({"ok": True})

    result = loop.run(_envelope(), call)
    assert is_ok(result)
    assert seen == [1, 2]
    assert result.value.attempt_ids == (1, 2)
    assert result.value.stop_reason is HostRetryStopReason.SUCCESS
    assert result.value.operator_is_recovery_loop is False
    print("host retried read on the same logical_invocation_id")

    assert BLIND_EXTERNAL_EGRESS_RETRY is False
    assert CAS_CONFLICT_IS_RETRY is False
    assert UNKNOWN_BLOCKED_AUTO_RETRY is False
    egress_seen: list[int] = []

    def egress_call(envelope: InvocationEnvelope) -> Result[object]:
        egress_seen.append(envelope.attempt_id)
        return TypedRefusal(
            category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
            retryability=Retryability.YES,
            context={"reason": "no-receipt"},
        )

    lost = loop.run({**_envelope(), "effect_class": "external-egress"}, egress_call)
    assert is_ok(lost)
    assert egress_seen == [1]
    assert lost.value.stop_reason is HostRetryStopReason.UNKNOWN
    assert lost.value.effect_outcome is not None
    assert lost.value.effect_outcome.disposition == "unknown"
    blind = loop.run(
        {**_envelope(), "effect_class": "external-egress", "attempt_id": 2},
        egress_call,
    )
    assert is_refusal(blind)
    assert BlindRetryRefused.matches(blind)
    assert egress_seen == [1]

    def cas_call(envelope: InvocationEnvelope) -> Result[object]:
        return StaleObservation.of(
            field="config_revision",
            bound=envelope.config_revision,
            live=5,
            cas=True,
            reason="cas_mismatch",
        )

    conflict = loop.run({**_envelope(), "effect_class": "mutate-config"}, cas_call)
    assert is_ok(conflict)
    assert conflict.value.stop_reason is HostRetryStopReason.CAS_CONFLICT
    print("no blind external-egress retry; CAS conflict is not a retry")


if __name__ == "__main__":
    main()
