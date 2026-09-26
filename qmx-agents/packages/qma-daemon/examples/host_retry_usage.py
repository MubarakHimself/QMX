"""L27 reference usage: host retry; pack may zero attempts; repair is change_request."""

from __future__ import annotations

from qma.core.operations import PER_PACK_RETRY_ENUM_MINTED, public_operation_descriptors
from qma.core.refusals.variants import BlindRetryRefused, StaleObservation
from qma.core.vocabulary.enums import EffectClass, ReconcilePolicy
from qma.daemon.journal.variables import (
    HOST_RETRY_ATTEMPT_CEILING_KEY,
    GovernedVariableRegistry,
)
from qma.daemon.repair import (
    ALERTS_AUTHORIZE_REPAIR,
    HMR_LIVE,
    HOT_APPLY_LIVE,
    REPAIR_IS_CHANGE_REQUEST,
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
from qma.daemon.sessions.copilot import CopilotHost
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

    assert PER_PACK_RETRY_ENUM_MINTED is False
    zero_seen: list[int] = []

    def zero_call(envelope: InvocationEnvelope) -> Result[object]:
        zero_seen.append(envelope.attempt_id)
        return TypedRefusal(
            category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
            retryability=Retryability.YES,
            context={"reason": "flake"},
        )

    zeroed = loop.run(_envelope(), zero_call, pack_attempts=0)
    assert is_ok(zeroed)
    assert zero_seen == [1]
    assert zeroed.value.stop_reason is HostRetryStopReason.PACK_ZERO_ATTEMPTS
    assert is_refusal(loop.run(_envelope(), zero_call, pack_attempts="always"))
    assert HMR_LIVE is False
    assert HOT_APPLY_LIVE is False
    assert ALERTS_AUTHORIZE_REPAIR is False
    assert REPAIR_IS_CHANGE_REQUEST is True
    host = CopilotHost(retry_loop=HostRetryLoop(injected_ceiling=4))
    assert is_ok(host.open_app_use(product_session_id="psess:app-use-1", instance_id="inst:1"))
    target = "fp1:sha256:" + "22" * 32
    assert is_ok(
        host.changes.install_v1(
            instance_id="inst:1",
            package_id="sector-intel",
            version="1.0.0",
            package_source_hash="fp1:sha256:" + "11" * 32,
            config_revision=4,
            granted_ops=("grant:app",),
            live_hashes=[{"target_ref": target, "base_hash": "fp1:sha256:" + "aa" * 32}],
        )
    )
    minted = host.request_implementation_repair(
        from_session="psess:app-use-1",
        change_request_id="cr:repair-code-1",
        targets=[{"target_ref": target, "base_hash": "fp1:sha256:" + "aa" * 32}],
        repair_kind="code",
    )
    assert is_ok(minted)
    assert minted.value.patch["path"] == "repair.code"
    assert is_refusal(host.hot_apply_implementation_edit())
    assert is_refusal(
        host.apply_implementation_repair(
            change_request_id="cr:repair-code-1",
            from_session="psess:app-use-1",
            operator_principal="operator",
            applied_at="2026-09-20T13:12:00Z",
            authorized_by="alert",
        )
    )
    print("pack zero attempts is not retried; repair is change_request")


if __name__ == "__main__":
    main()
