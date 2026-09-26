"""Story 62.1 / 62.2 / 62.3 — host retry; pack may zero attempts; repair is change_request."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.operations import (
    CAS_CONFLICT_IS_RETRY,
    EFFECT_RETRY_BY_CLASS,
    HOST_RETRY_EFFECT_CLASSES,
    OUTBOX_REPLAY_IS_SECOND_DISPATCH,
    PER_PACK_RETRY_ENUM_MINTED,
    UNKNOWN_BLOCKED_AUTO_RETRY,
    public_operation_descriptors,
)
from qma.core.ports.copilot import APP_USE_MAY_APPLY
from qma.core.refusals.variants import BlindRetryRefused, StaleObservation
from qma.core.vocabulary.enums import (
    EffectClass,
    EffectRetryOutcome,
    JobHandleState,
    ReconcilePolicy,
)
from qma.daemon.journal.variables import (
    HOST_RETRY_ATTEMPT_CEILING_KEY,
    HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY,
    GovernedVariableRegistry,
)
from qma.daemon.repair import (
    ALERTS_AUTHORIZE_REPAIR,
    HMR_LIVE,
    HOT_APPLY_LIVE,
    IMPLEMENTATION_REPAIR_KINDS,
    REPAIR_IS_CHANGE_REQUEST,
    STORY_58_4_IS_APPLY_ORACLE,
)
from qma.daemon.retry import (
    BLIND_EXTERNAL_EGRESS_RETRY,
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
from qma.daemon.sessions.product_session import ProductSessionProfile
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
    assert BLIND_EXTERNAL_EGRESS_RETRY is False
    assert CAS_CONFLICT_IS_RETRY is False
    assert UNKNOWN_BLOCKED_AUTO_RETRY is False
    assert OUTBOX_REPLAY_IS_SECOND_DISPATCH is False
    assert PER_PACK_RETRY_ENUM_MINTED is False
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
    assert result.stop_reason is HostRetryStopReason.UNKNOWN
    assert result.effect_outcome is not None
    assert result.effect_outcome.disposition == "unknown"
    assert result.effect_outcome.handle_state is JobHandleState.UNKNOWN
    assert result.to_payload()["handle_state"] == "unknown"
    assert result.operator_is_recovery_loop is False
    assert BLIND_EXTERNAL_EGRESS_RETRY is False

    def boom(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        raise AssertionError("must not blind-retry external-egress")

    blind = loop.run(_envelope(effect_class="external-egress", attempt_id=2), boom)
    assert is_refusal(blind)
    assert BlindRetryRefused.matches(blind)
    assert seen == [1]


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
    assert result.stop_reason is HostRetryStopReason.RECONCILE_POLICY
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


def test_external_egress_success_without_receipt_is_unknown() -> None:
    loop = HostRetryLoop(injected_ceiling=4)
    seen: list[int] = []

    def call(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        return Ok({"order": "maybe-sent"})

    result = _ok(loop.run(_envelope(effect_class="external-egress"), call))
    assert seen == [1]
    assert result.stop_reason is HostRetryStopReason.UNKNOWN
    assert result.effect_outcome is not None
    assert result.effect_outcome.receipt is False
    receipted = _ok(
        loop.run(
            _envelope(effect_class="external-egress", logical_invocation_id="inv:ack"),
            call,
            receipt={"ack": "ok"},
        )
    )
    assert seen == [1, 1]
    assert receipted.stop_reason is HostRetryStopReason.SUCCESS
    assert receipted.effect_outcome is not None
    assert receipted.effect_outcome.disposition == "receipt"


def test_mutate_config_cas_conflict_is_not_retried() -> None:
    loop = HostRetryLoop(injected_ceiling=4)
    seen: list[int] = []

    def call(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        return StaleObservation.of(
            field="config_revision",
            bound=envelope.config_revision,
            live=5,
            cas=True,
            reason="cas_mismatch",
        )

    result = _ok(loop.run(_envelope(effect_class="mutate-config"), call))
    assert seen == [1]
    assert result.stop_reason is HostRetryStopReason.CAS_CONFLICT
    assert result.cas_conflict is True
    assert result.refusal is not None
    assert StaleObservation.matches(result.refusal)
    assert result.refusal.context["cas"] is True
    assert CAS_CONFLICT_IS_RETRY is False

    def boom(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        raise AssertionError("CAS conflict is not a retry")

    blocked = _ok(loop.run(_envelope(effect_class="mutate-config", attempt_id=2), boom))
    assert seen == [1]
    assert blocked.stop_reason is HostRetryStopReason.CAS_CONFLICT
    flagged = _ok(loop.run(_envelope(effect_class="mutate-config"), boom, cas_conflict=True))
    assert seen == [1]
    assert flagged.stop_reason is HostRetryStopReason.CAS_CONFLICT


def test_unknown_manual_wins_over_default_host_retry() -> None:
    loop = HostRetryLoop(injected_ceiling=4)
    seen: list[int] = []

    def call(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        return _flake(retryability=Retryability.YES)

    result = _ok(loop.run(_envelope(reconcile_policy="unknown-manual"), call))
    assert seen == [1]
    assert result.stop_reason is HostRetryStopReason.RECONCILE_POLICY
    assert result.attempt_ids == (1,)


def test_unknown_blocked_is_never_auto_retried() -> None:
    loop = HostRetryLoop(injected_ceiling=4)
    seen: list[int] = []

    def call(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.YES,
            context={"field": "unknown-blocked", "reason": "unknown-blocked"},
        )

    result = _ok(loop.run(_envelope(), call))
    assert seen == [1]
    assert result.stop_reason is HostRetryStopReason.UNKNOWN_BLOCKED
    assert result.unknown_blocked is True
    assert UNKNOWN_BLOCKED_AUTO_RETRY is False

    def boom(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        raise AssertionError("unknown-blocked is never auto-retried")

    gated = _ok(loop.run(_envelope(), boom, unknown_blocked=True))
    assert seen == [1]
    assert gated.stop_reason is HostRetryStopReason.UNKNOWN_BLOCKED
    assert gated.attempt_ids == ()


def test_append_evidence_dedupes_place_run_identity_outbox_replay_is_not_dispatch() -> None:
    loop = HostRetryLoop(injected_ceiling=4)
    seen: list[int] = []

    def boom(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        raise AssertionError("replay and dedupe are not a second dispatch")

    deduped = _ok(
        loop.run(
            _envelope(effect_class="append-evidence"),
            boom,
            prior_result={"entry": "already-appended"},
        )
    )
    assert seen == []
    assert deduped.effect_outcome is not None
    assert deduped.effect_outcome.disposition == "dedupe"
    assert deduped.effect_outcome.duplicated is False
    placed = _ok(
        loop.run(
            _envelope(effect_class="place-run", logical_invocation_id="inv:run-7"),
            boom,
            prior_result={"run": "inv:run-7"},
        )
    )
    assert seen == []
    assert placed.effect_outcome is not None
    assert placed.effect_outcome.disposition == "run-identity"
    assert placed.effect_outcome.run_identity == "inv:run-7"
    replayed = _ok(
        loop.run(
            _envelope(effect_class="external-egress"),
            boom,
            prior_result={"order": "already-sent"},
        )
    )
    assert seen == []
    assert OUTBOX_REPLAY_IS_SECOND_DISPATCH is False
    assert replayed.stop_reason is HostRetryStopReason.UNKNOWN
    assert replayed.effect_outcome is not None
    assert replayed.effect_outcome.disposition == "replay"
    assert replayed.effect_outcome.duplicated is False

    def flake(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        return _flake(retryability=Retryability.YES)

    append_once = _ok(loop.run(_envelope(effect_class="append-evidence"), flake))
    assert seen == [1]
    assert append_once.stop_reason is HostRetryStopReason.EFFECT_CLASS


_HASH_A = "fp1:sha256:" + "aa" * 32
_SOURCE = "fp1:sha256:" + "11" * 32
_TARGET = "fp1:sha256:" + "22" * 32
_AS_OF = "2026-09-20T13:12:00Z"


def test_pack_zero_attempts_is_not_retried() -> None:
    loop = HostRetryLoop(injected_ceiling=4)
    seen: list[int] = []

    def call(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        return _flake(retryability=Retryability.YES)

    result = _ok(loop.run(_envelope(), call, pack_attempts=0))
    assert seen == [1]
    assert result.attempt_ids == (1,)
    assert result.stop_reason is HostRetryStopReason.PACK_ZERO_ATTEMPTS
    assert result.refusal is not None
    assert result.refusal.retryability is Retryability.YES
    assert PER_PACK_RETRY_ENUM_MINTED is False

    capped = _ok(loop.run(_envelope(logical_invocation_id="inv:cap-2"), call, pack_attempts=2))
    assert seen == [1, 1, 2]
    assert capped.attempt_ids == (1, 2)
    assert capped.stop_reason is HostRetryStopReason.ATTEMPT_CEILING


def test_pack_must_not_exceed_host_ceiling_or_effect_class_matrix() -> None:
    loop = HostRetryLoop(injected_ceiling=4)

    def boom(_envelope: InvocationEnvelope) -> Result[object]:
        raise AssertionError("must not dispatch a refused pack retry bound")

    over = loop.run(_envelope(), boom, pack_attempts=5)
    assert is_refusal(over)
    assert over.context["host_ceiling"] == 4
    dialect = loop.run(_envelope(), boom, pack_attempts="aggressive")
    assert is_refusal(dialect)
    assert dialect.context["per_pack_retry_enum"] is False
    matrix = loop.run(
        _envelope(effect_class="external-egress"),
        boom,
        pack_attempts=2,
    )
    assert is_refusal(matrix)
    assert "effect-class matrix" in str(matrix.context["reason"])


def test_repair_after_failure_is_change_request_not_hot_apply() -> None:
    assert HMR_LIVE is False
    assert HOT_APPLY_LIVE is False
    assert ALERTS_AUTHORIZE_REPAIR is False
    assert APP_USE_MAY_APPLY is False
    assert REPAIR_IS_CHANGE_REQUEST is True
    assert STORY_58_4_IS_APPLY_ORACLE is True
    assert frozenset({"account_target", "code", "graph", "grants"}) == IMPLEMENTATION_REPAIR_KINDS
    host = CopilotHost(retry_loop=HostRetryLoop(injected_ceiling=4))
    _ok(
        host.open_app_use(
            product_session_id="psess:app-use-1",
            instance_id="inst:1",
            granted_ops=("grant:app",),
        )
    )
    _ok(
        host.changes.install_v1(
            instance_id="inst:1",
            package_id="sector-intel",
            version="1.0.0",
            package_source_hash=_SOURCE,
            config_revision=4,
            granted_ops=("grant:app",),
            running_jobs=("job:run-1",),
            live_hashes=[{"target_ref": _TARGET, "base_hash": _HASH_A}],
        )
    )
    seen: list[int] = []

    def call(envelope: InvocationEnvelope) -> Result[object]:
        seen.append(envelope.attempt_id)
        return _flake(retryability=Retryability.YES)

    failed = _ok(host.retry_public_call(_envelope(), call, pack_attempts=0))
    assert seen == [1]
    assert failed.stop_reason is HostRetryStopReason.PACK_ZERO_ATTEMPTS

    minted = _ok(
        host.request_implementation_repair(
            from_session="psess:app-use-1",
            change_request_id="cr:repair-code-1",
            targets=[{"target_ref": _TARGET, "base_hash": _HASH_A}],
            repair_kind="code",
        )
    )
    assert minted.patch["kind"] == "runtime_input"
    assert minted.patch["path"] == "repair.code"
    app_use_apply = host.apply_implementation_repair(
        change_request_id=minted.change_request_id,
        from_session="psess:app-use-1",
        operator_principal="operator",
        applied_at=_AS_OF,
    )
    assert is_refusal(app_use_apply)
    assert app_use_apply.context["applies"] is False
    alerted = host.request_implementation_repair(
        from_session="psess:app-use-1",
        change_request_id="cr:repair-alert-1",
        targets=[{"target_ref": _TARGET, "base_hash": _HASH_A}],
        repair_kind="graph",
        authorized_by="alert",
    )
    assert is_refusal(alerted)
    assert alerted.context["alerts_authorize"] is False
    hot = host.hot_apply_implementation_edit(kind="code")
    assert is_refusal(hot)
    assert hot.context["hot_apply"] is False
    assert hot.context["hmr"] is False
    hmr = host.request_implementation_repair(
        from_session="psess:app-use-1",
        change_request_id="cr:repair-hmr-1",
        targets=[{"target_ref": _TARGET, "base_hash": _HASH_A}],
        repair_kind="grants",
        hmr=True,
    )
    assert is_refusal(hmr)
    assert hmr.context["repair_is_change_request"] is True
    grants = _ok(
        host.request_implementation_repair(
            from_session="psess:app-use-1",
            change_request_id="cr:repair-grants-1",
            targets=[{"target_ref": _TARGET, "base_hash": _HASH_A}],
            repair_kind="grants",
        )
    )
    account = _ok(
        host.request_implementation_repair(
            from_session="psess:app-use-1",
            change_request_id="cr:repair-account-1",
            targets=[{"target_ref": _TARGET, "base_hash": _HASH_A}],
            repair_kind="account_target",
        )
    )
    assert grants.patch["path"] == "repair.grants"
    assert account.patch["path"] == "repair.account_target"
    authoring = _ok(host.changes.open_authoring_handoff(minted))
    assert authoring.profile is ProductSessionProfile.AUTHORING
    _ok(
        host.changes.validate(
            change_request_id=minted.change_request_id,
            authoring_session=authoring.product_session_id,
            validated_at="2026-09-20T13:10:00Z",
        )
    )
    applied = _ok(
        host.apply_implementation_repair(
            change_request_id=minted.change_request_id,
            from_session=authoring.product_session_id,
            operator_principal="operator",
            applied_at=_AS_OF,
        )
    )
    assert applied.outcome == "applied"
    still = _ok(host.sessions.get("psess:app-use-1"))
    assert still.granted_ops == ("grant:app",)
