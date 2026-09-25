"""Story 60.4 — one copilot identity; nested grants do not union; app-use cannot apply."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.control.primitives import Skill
from qma.core.ontology import ActorId, DeskSlug
from qma.core.operations import OperationDescriptor, public_operation_descriptors
from qma.core.ports.copilot import (
    APP_USE_MAY_APPLY,
    COPILOT_PRODUCT_IDENTITY,
    ENGINE_RUN_IS_THIRD_CHAT,
    GAP_0081_CHROME_FILLED,
    IN_APP_PANEL_IS_CONTRACT,
    IN_APP_PANEL_IS_GAP_0081_CHROME,
    IN_APP_PANEL_IS_SECOND_COPILOT,
    INSTANCE_MAY_OMIT_PANEL,
    PACK_MAY_OMIT_COPILOT_PROFILE,
    PANEL_DISPOSE_CANCELS_JOB_HANDLE,
    RECONNECT_REPLAYS_UNACKED_INTENT,
    SECOND_COPILOT_PRODUCT_MINTED,
)
from qma.core.refusals import NestedGrantUnionRefused
from qma.core.vocabulary.enums import HookResultDecision, JobHandleState
from qma.daemon.sessions import ProductSessionProfile
from qma.daemon.sessions.copilot import CopilotHost
from qma.wire import compute_input_hash, derive_child_logical_invocation_id
from qma.wire.invocation_envelope import ContributionRecord, InstanceRecord
from qmf.core import is_ok, is_refusal
from qmf.core.refusal import Result

_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "copilot_usage.py"
_AS_OF = "2026-09-20T00:00:00Z"
_NOW = "2026-09-20T00:00:00Z"
_EXPIRES = "2026-12-31T00:00:00Z"
_CONTRIBUTION = {"package_version": "0.1.0", "qualified_id": "analysis-backtest:qmb"}
_INPUT = {"run_fp1": "run-1"}
_HASH_A = "fp1:sha256:" + "aa" * 32
_SOURCE = "fp1:sha256:" + "11" * 32
_TARGET = "fp1:sha256:" + "22" * 32
_TOOL = "analysis-backtest:qmb"


def _ok[T](result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    return minted.value


def _descriptor() -> OperationDescriptor:
    for item in public_operation_descriptors():
        if item.op_id == "qmb.analysis.project" and item.version == 1:
            return item
    raise AssertionError("qmb.analysis.project v1 missing")


def _hash() -> str:
    hashed = compute_input_hash(_INPUT, descriptor=_descriptor())
    assert is_ok(hashed)
    return hashed.value


def _grant_kwargs(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "op_id": "qmb.analysis.project",
        "op_version": 1,
        "effect_class": "read",
        "parameter_ceiling": {"allow_keys": ["run_fp1", "as_of"]},
        "expires_at": _EXPIRES,
    }
    body.update(overrides)
    return body


def _envelope(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "logical_invocation_id": "inv:1",
        "attempt_id": 1,
        "op_id": "qmb.analysis.project",
        "op_version": 1,
        "contribution": dict(_CONTRIBUTION),
        "instance_id": "inst:1",
        "config_revision": 4,
        "grant_id": "grant:app",
        "effect_class": "read",
        "idempotency_key": "idem:1",
        "reconcile_policy": "query-then-decide",
        "input_hash": _hash(),
        "call_depth": 0,
        "caller_kind": "user",
        "caller_session_ref": "psess:home",
        "callee_session_ref": "psess:app-use-1",
    }
    payload.update(overrides)
    return payload


def _stores() -> tuple[
    dict[tuple[str, str], ContributionRecord],
    dict[tuple[str, int], OperationDescriptor],
    dict[tuple[str, int], InstanceRecord],
]:
    descriptor = _descriptor()
    contribution = ContributionRecord(
        qualified_id="analysis-backtest:qmb",
        package_version="0.1.0",
        availability="enabled",
    )
    instance = InstanceRecord(instance_id="inst:1", config_revision=4)
    return (
        {contribution.as_tuple(): contribution},
        {(descriptor.op_id, descriptor.version): descriptor},
        {(instance.instance_id, instance.config_revision): instance},
    )


def _nested_envelope(**overrides: object) -> dict[str, object]:
    child_id = derive_child_logical_invocation_id(
        parent_logical_invocation_id="inv:1",
        call_depth=1,
        child_op_id="qmb.analysis.project",
        child_canonical_input_hash=_hash(),
    )
    assert is_ok(child_id)
    return _envelope(
        logical_invocation_id=child_id.value,
        parent_logical_invocation_id="inv:1",
        call_depth=1,
        caller_kind="workflow",
        **overrides,
    )


def _world() -> CopilotHost:
    host = CopilotHost()
    _ok(host.open_home(product_session_id="psess:home", selected_refs=()))
    _ok(
        host.open_app_use(
            product_session_id="psess:app-use-1",
            instance_id="inst:1",
            panel_id="panel:app",
            copilot_profile=None,
        )
    )
    _ok(
        host.sessions.host_grant(
            "psess:home",
            grant_id="grant:home",
            instance_id="inst:1",
            **_grant_kwargs(),
        )
    )
    _ok(host.sessions.host_grant("psess:app-use-1", grant_id="grant:app", **_grant_kwargs()))
    return host


def test_one_copilot_identity_over_independently_scoped_seats() -> None:
    host = _world()
    payload = dict(host.identity_payload())
    assert payload["identity"] == COPILOT_PRODUCT_IDENTITY
    assert host.identity == COPILOT_PRODUCT_IDENTITY
    assert host.second_copilot_minted is False is SECOND_COPILOT_PRODUCT_MINTED
    assert host.gap_0081_chrome_filled is False is GAP_0081_CHROME_FILLED
    assert payload["in_app_panel_is_contract"] is True is IN_APP_PANEL_IS_CONTRACT
    assert payload["in_app_panel_is_gap_0081_chrome"] is False is IN_APP_PANEL_IS_GAP_0081_CHROME
    assert payload["in_app_panel_is_second_copilot"] is False is IN_APP_PANEL_IS_SECOND_COPILOT
    assert payload["pack_may_omit_copilot_profile"] is True is PACK_MAY_OMIT_COPILOT_PROFILE
    assert payload["instance_may_omit_panel"] is True is INSTANCE_MAY_OMIT_PANEL
    assert payload["engine_run_is_third_chat"] is False is ENGINE_RUN_IS_THIRD_CHAT
    assert payload["app_use_may_apply"] is False is APP_USE_MAY_APPLY
    assert _ok(host.bind_identity("QMX Copilot")) == COPILOT_PRODUCT_IDENTITY
    assert is_refusal(host.mint_second_copilot("Research Copilot"))
    assert is_refusal(host.treat_panel_as_copilot_product("panel:app"))
    assert is_refusal(host.treat_engine_run_as_chat("sess:run-1"))
    assert is_refusal(host.seat_for("sess:run-1"))

    compared = _ok(host.compare_seats("psess:home", "psess:app-use-1"))
    assert compared["identity"] == COPILOT_PRODUCT_IDENTITY
    assert compared["independent"] is True
    assert compared["second_copilot"] is False
    assert compared["seats"] == ["app-use", "authoring"]

    omitted = CopilotHost()
    _ok(
        omitted.open_app_use(
            product_session_id="psess:app-use-2",
            instance_id="inst:2",
            copilot_profile=None,
        )
    )
    assert is_ok(omitted.omit_panel("psess:app-use-2"))
    granted_profile = omitted.open_app_use(
        product_session_id="psess:app-use-3",
        instance_id="inst:3",
        copilot_profile={"grant_id": "grant:1", "prompts": []},
    )
    assert is_refusal(granted_profile)


def test_tool_availability_intersects_and_skills_do_not_grant() -> None:
    host = _world()
    host.note_published(_TOOL)
    host.note_published("research-corpus:inspect")
    host.note_host_grant(_TOOL)
    host.note_healthy(_TOOL)
    host.note_healthy("research-corpus:inspect")
    available = _ok(host.tool_availability("psess:app-use-1"))
    assert available == frozenset({_TOOL})
    allowed = _ok(host.authorize_tool("psess:app-use-1", _TOOL))
    assert allowed == _TOOL
    skill = Skill(
        qualified_id="research-corpus:inspect-skill",
        version="0.1.0",
        summary="describes inspect",
    )
    described = _ok(
        host.authorize_tool("psess:app-use-1", _TOOL, skill=skill),
    )
    assert described == _TOOL
    as_grant = host.authorize_tool(
        "psess:app-use-1",
        _TOOL,
        skill=skill,
        treat_skill_as_grant=True,
    )
    assert is_refusal(as_grant)
    hit = host.authorize_tool(
        "psess:app-use-1",
        "research-corpus:inspect",
        treat_hit_as_grant=True,
    )
    assert is_refusal(hit)
    hooked = host.authorize_tool(
        "psess:app-use-1",
        "research-corpus:inspect",
        hook_decision=HookResultDecision.ALLOW,
    )
    assert is_refusal(hooked)
    assert hooked.context["hooks_override"] is False


def test_nested_invoke_does_not_union_caller_and_callee_grants() -> None:
    host = _world()
    contributions, descriptors, instances = _stores()
    executed: list[object] = []

    def _execute(bound: object) -> None:
        executed.append(bound)

    child = _ok(
        host.nested_invoke(
            caller_product_session_id="psess:home",
            callee_product_session_id="psess:app-use-1",
            envelope=_nested_envelope(),
            payload=_INPUT,
            now=_NOW,
            contributions=contributions,
            descriptors=descriptors,
            instances=instances,
            execute=_execute,
        )
    )
    assert child.grant_ids == ("grant:app",)
    assert "grant:home" not in child.grant_ids
    assert child.grant.grant_id == "grant:app"
    assert executed != []

    leaked = host.nested_invoke(
        caller_product_session_id="psess:home",
        callee_product_session_id="psess:app-use-1",
        envelope=_nested_envelope(grant_id="grant:home", idempotency_key="idem:leak"),
        payload=_INPUT,
        now=_NOW,
        contributions=contributions,
        descriptors=descriptors,
        instances=instances,
    )
    assert is_refusal(leaked)
    assert isinstance(leaked, NestedGrantUnionRefused)
    assert leaked.context["union"] is False
    assert leaked.context["reason"] == "nested_invoke_does_not_union_grants"

    unioned = host.nested_invoke(
        caller_product_session_id="psess:home",
        callee_product_session_id="psess:app-use-1",
        envelope=_nested_envelope(idempotency_key="idem:union"),
        payload=_INPUT,
        now=_NOW,
        contributions=contributions,
        descriptors=descriptors,
        instances=instances,
        union_grants=True,
    )
    assert is_refusal(unioned)
    assert isinstance(unioned, NestedGrantUnionRefused)


def test_disposing_a_panel_does_not_cancel_running_job_handle() -> None:
    host = _world()
    handle = _ok(host.submit_job(owner=_owner(), task_id="task-60-4", job_id="job:60-4"))
    assert handle.state is JobHandleState.RUNNING
    closed = _ok(
        host.dispose_panel(
            "panel:app",
            product_session_id="psess:app-use-1",
            job_id=handle.job_id,
        )
    )
    assert closed.product_session_id == "psess:app-use-1"
    live = host.jobs.handle_for(handle.job_id)
    assert live is not None
    assert live.state is JobHandleState.RUNNING
    assert PANEL_DISPOSE_CANCELS_JOB_HANDLE is False

    snapshot = _ok(
        host.reconnect(
            "psess:app-use-1",
            resume_cursor=0,
            cursor_generation=1,
        )
    )
    assert snapshot.replays_unacked_intent is False is RECONNECT_REPLAYS_UNACKED_INTENT
    intent = host.reconnect(
        "psess:app-use-1",
        resume_cursor=0,
        cursor_generation=1,
        unacked=True,
    )
    assert is_refusal(intent)
    assert intent.context["replays_unacked_intent"] is False
    transferred = _ok(
        host.transfer_context(
            kind="selected_refs",
            from_session="psess:app-use-1",
            selected_refs=[{"kind": "run", "id": _TARGET}],
        )
    )
    assert transferred.product_session_id == "psess:app-use-1"
    transcript = host.transfer_context(
        kind="transcript",
        from_session="psess:app-use-1",
    )
    assert is_refusal(transcript)


def test_app_use_mints_change_request_and_cannot_apply() -> None:
    host = _world()
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
    minted = _ok(
        host.mint_change_request(
            from_session="psess:app-use-1",
            change_request_id="cr:filter-1",
            targets=[{"target_ref": _TARGET, "base_hash": _HASH_A}],
            patch={"kind": "filter_add", "path": "industry.known_at"},
        )
    )
    assert minted.from_session == "psess:app-use-1"
    applied = host.apply_change_request(
        change_request_id=minted.change_request_id,
        from_session="psess:app-use-1",
        operator_principal="operator",
        applied_at=_AS_OF,
    )
    assert is_refusal(applied)
    assert applied.context["applies"] is False
    assert is_refusal(host.write_package_source(from_session="psess:app-use-1"))
    assert is_refusal(host.elevate_grants(from_session="psess:app-use-1", grant_id="grant:live"))
    assert is_refusal(
        host.retarget_account(from_session="psess:app-use-1", account_scope="acct:other")
    )
    authoring = _ok(host.changes.open_authoring_handoff(minted))
    assert authoring.profile is ProductSessionProfile.AUTHORING
    _ok(
        host.changes.validate(
            change_request_id=minted.change_request_id,
            authoring_session=authoring.product_session_id,
            validated_at="2026-09-20T13:10:00Z",
        )
    )
    applied_oracle = _ok(
        host.apply_change_request(
            change_request_id=minted.change_request_id,
            from_session=authoring.product_session_id,
            operator_principal="operator",
            applied_at="2026-09-20T13:12:00Z",
        )
    )
    assert applied_oracle.outcome == "applied"
    still = _ok(host.sessions.get("psess:app-use-1"))
    assert still.granted_ops == ("grant:app",)


def test_copilot_usage_example_runs() -> None:
    namespace = runpy.run_path(str(_EXAMPLE))
    assert namespace["COPILOT_PRODUCT_IDENTITY"] == COPILOT_PRODUCT_IDENTITY
