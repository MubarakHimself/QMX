"""Story 62.1 — host retries none/read on the same logical_invocation_id."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.operations import (
    EFFECT_RETRY_BY_CLASS,
    HOST_RETRY_EFFECT_CLASSES,
    public_operation_descriptors,
)
from qma.core.vocabulary.enums import EffectClass, EffectRetryOutcome, ReconcilePolicy
from qma.daemon.journal.variables import (
    HOST_RETRY_ATTEMPT_CEILING_KEY,
    HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY,
    GovernedVariableRegistry,
)
from qma.daemon.retry import (
    EFFECT_CLASS_TYPES_EXISTED_AT_INSPECT_SHA,
    HOST_RETRY_INSPECT_SHA,
    HOST_RETRY_LOOP_EXISTED_AT_INSPECT_SHA,
    HOST_RETRY_LOOP_OWNER,
    OPERATOR_IS_RECOVERY_LOOP,
    RECONCILE_POLICY_TYPES_EXISTED_AT_INSPECT_SHA,
    STORY_54_3_EFFECT_RETRY_MATRIX_LOOSENED,
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

_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "host_retry_usage.py"
_INPUT = {"run_fp1": "run-1"}


def _ok[T](result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _descriptor():
    for item in public_operation_descriptors():
        if item.op_id == "qmb.analysis.project" and item.version == 1:
            return item
    raise AssertionError("qmb.analysis.project v1 missing")


def _hash() -> str:
    hashed = compute_input_hash(_INPUT, descriptor=_descriptor())
    assert is_ok(hashed)
    return hashed.value


def _envelope(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
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
        "input_hash": _hash(),
        "call_depth": 0,
        "caller_kind": "user",
    }
    payload.update(overrides)
    return payload


def _flake(*, retryability: Retryability, reason: str = "flake") -> TypedRefusal:
    extra: dict[str, object] = {"reason": reason}
    if retryability is Retryability.AFTER_CONDITION:
        return TypedRefusal(
            category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
            retryability=retryability,
            context=extra,
            after_condition_descriptor="dependency-returns",
        )
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=retryability,
        context=extra,
    )


def test_inspect_sha_honesty_loop_absent_types_present_at_34c148b() -> None:
    assert HOST_RETRY_INSPECT_SHA == "34c148b"
    assert HOST_RETRY_LOOP_EXISTED_AT_INSPECT_SHA is False
    assert EFFECT_CLASS_TYPES_EXISTED_AT_INSPECT_SHA is True
    assert RECONCILE_POLICY_TYPES_EXISTED_AT_INSPECT_SHA is True
    assert STORY_54_3_EFFECT_RETRY_MATRIX_LOOSENED is False
    assert OPERATOR_IS_RECOVERY_LOOP is False
    assert HOST_RETRY_LOOP_OWNER == "COMP-QMA-DAEMON"
    claimed_loop = claim_host_retry_loop_at_inspect_sha(True)
    assert is_refusal(claimed_loop)
    assert claimed_loop.context["existed_at_inspect_sha"] is False
    assert claimed_loop.context["effect_class_types_existed_at_inspect_sha"] is True
    assert is_ok(claim_host_retry_loop_at_inspect_sha(False))
    assert is_refusal(claim_host_retry_loop_at_inspect_sha("maybe"))
    claimed_absent = claim_effect_class_or_reconcile_policy_absent_at_inspect_sha(True)
    assert is_refusal(claimed_absent)
    assert claimed_absent.context["existed_at_inspect_sha"] is True
    assert claimed_absent.context["host_retry_loop_existed_at_inspect_sha"] is False
    assert is_ok(claim_effect_class_or_reconcile_policy_absent_at_inspect_sha(False))
    assert is_refusal(claim_effect_class_or_reconcile_policy_absent_at_inspect_sha("maybe"))
    assert set(EffectClass) == set(EFFECT_RETRY_BY_CLASS)
    assert {
        "query-then-decide",
        "unknown-manual",
        "never-retry",
    } == {member.value for member in ReconcilePolicy}


def test_attempt_ceiling_is_registry_row_and_production_mints_no_number() -> None:
    registry = GovernedVariableRegistry.with_builtins()
    row = _ok(registry.get(HOST_RETRY_ATTEMPT_CEILING_KEY))
    assert row.name == HOST_RETRY_ATTEMPT_CEILING_KEY
    assert row.registry_key == HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY
    assert row.owning_subsystem == "COMP-QMA-DAEMON"
    assert row.default is None
    assert row.default != 3
    unfilled = HostRetryLoop().attempt_ceiling()
    assert is_refusal(unfilled)
    assert unfilled.context["registry_key"] == HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY
    assert unfilled.context["invented_default"] is False
    injected = _ok(HostRetryLoop(injected_ceiling=2).attempt_ceiling())
    assert injected == 2
    retry_src = Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "retry.py"
    variables_src = (
        Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "journal" / "variables.py"
    )
    retry_text = retry_src.read_text(encoding="utf-8")
    variables_text = variables_src.read_text(encoding="utf-8")
    assert "DEFAULT_ATTEMPT_CEILING = 3" not in retry_text
    assert "injected_ceiling: int = 3" not in retry_text
    assert "default=3" not in variables_text.split(HOST_RETRY_ATTEMPT_CEILING_KEY, 1)[1][:400]


def test_host_retries_read_flake_until_success_same_logical_invocation_id() -> None:
    loop = HostRetryLoop(injected_ceiling=4)
    seen: list[int] = []

    def call(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        assert envelope.logical_invocation_id == "inv:read-1"
        if envelope.attempt_id < 2:
            return _flake(retryability=Retryability.YES)
        return Ok({"ok": True})

    result = _ok(loop.run(_envelope(), call))
    assert seen == [1, 2]
    assert result.attempt_ids == (1, 2)
    assert result.attempt_id == 2
    assert result.logical_invocation_id == "inv:read-1"
    assert result.stop_reason is HostRetryStopReason.SUCCESS
    assert result.operator_is_recovery_loop is False
    assert result.value == {"ok": True}


def test_host_retries_none_after_condition_until_retryability_no() -> None:
    loop = HostRetryLoop(injected_ceiling=4)
    seen: list[int] = []

    def call(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        assert envelope.logical_invocation_id == "inv:none-1"
        if envelope.attempt_id == 1:
            return _flake(retryability=Retryability.AFTER_CONDITION)
        return _flake(retryability=Retryability.NO, reason="terminal")

    result = _ok(loop.run(_envelope(effect_class="none", logical_invocation_id="inv:none-1"), call))
    assert seen == [1, 2]
    assert result.attempt_ids == (1, 2)
    assert result.stop_reason is HostRetryStopReason.RETRYABILITY_NO
    assert result.refusal is not None
    assert result.refusal.retryability is Retryability.NO
    assert result.operator_is_recovery_loop is False


def test_host_stops_at_injected_attempt_ceiling() -> None:
    loop = HostRetryLoop(injected_ceiling=2)
    seen: list[int] = []

    def call(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        return _flake(retryability=Retryability.YES)

    result = _ok(loop.run(_envelope(), call))
    assert seen == [1, 2]
    assert result.attempt_ids == (1, 2)
    assert result.stop_reason is HostRetryStopReason.ATTEMPT_CEILING
    assert result.refusal is not None
    assert result.refusal.retryability is Retryability.YES
    assert result.logical_invocation_id == "inv:read-1"


def test_effect_class_matrix_is_not_loosened_for_external_egress() -> None:
    assert frozenset({EffectClass.NONE, EffectClass.READ}) == HOST_RETRY_EFFECT_CLASSES
    assert EFFECT_RETRY_BY_CLASS[EffectClass.EXTERNAL_EGRESS] is (
        EffectRetryOutcome.RECEIPT_OR_UNKNOWN
    )
    loop = HostRetryLoop(injected_ceiling=4)
    seen: list[int] = []

    def call(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        return _flake(retryability=Retryability.YES)

    result = _ok(loop.run(_envelope(effect_class="external-egress"), call))
    assert seen == [1]
    assert result.attempt_ids == (1,)
    assert result.operator_is_recovery_loop is False


def test_run_refuses_unfilled_ceiling_invalid_envelope_and_over_ceiling() -> None:
    def boom(_envelope: InvocationEnvelope) -> Result[object]:
        raise AssertionError("must not call")

    unfilled = HostRetryLoop().run(_envelope(), boom)
    assert is_refusal(unfilled)
    assert unfilled.context["invented_default"] is False
    bad = HostRetryLoop(injected_ceiling=2).run({"logical_invocation_id": "inv:x"}, boom)
    assert is_refusal(bad)
    over = HostRetryLoop(injected_ceiling=2).run(_envelope(attempt_id=4), boom)
    assert is_refusal(over)
    assert over.context["field"] == "attempt_id"


def test_never_retry_policy_does_not_take_a_second_attempt() -> None:
    loop = HostRetryLoop(injected_ceiling=4)
    seen: list[int] = []

    def call(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        return _flake(retryability=Retryability.YES)

    result = _ok(loop.run(_envelope(reconcile_policy="never-retry"), call))
    assert seen == [1]
    assert result.attempt_ids == (1,)
    assert result.to_payload()["retryability"] == "yes"


def test_copilot_host_retries_public_call() -> None:
    host = CopilotHost(retry_loop=HostRetryLoop(injected_ceiling=2))
    seen: list[int] = []

    def call(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        if envelope.attempt_id == 1:
            return _flake(retryability=Retryability.YES)
        return Ok("recovered")

    result = _ok(host.retry_public_call(_envelope(), call))
    assert seen == [1, 2]
    assert result.stop_reason is HostRetryStopReason.SUCCESS
    assert result.value == "recovered"


def test_example_host_retry_usage() -> None:
    namespace = runpy.run_path(str(_EXAMPLE))
    assert namespace["main"] is not None
