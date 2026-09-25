"""Reference usage — one QuantMind/QMX Copilot; nested grants do not union (60.4)."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.copilot import (
    APP_USE_MAY_APPLY,
    COPILOT_PRODUCT_IDENTITY,
    GAP_0081_CHROME_FILLED,
    IN_APP_PANEL_IS_CONTRACT,
    IN_APP_PANEL_IS_SECOND_COPILOT,
    PANEL_DISPOSE_CANCELS_JOB_HANDLE,
    SECOND_COPILOT_PRODUCT_MINTED,
)
from qma.core.refusals import NestedGrantUnionRefused
from qma.core.vocabulary.enums import JobHandleState
from qma.daemon.sessions.copilot import CopilotHost
from qmf.core import is_ok, is_refusal

_AS_OF = "2026-09-20T00:00:00Z"
_NOW = "2026-09-20T00:00:00Z"
_EXPIRES = "2026-12-31T00:00:00Z"
_CONTRIBUTION = {"package_version": "0.1.0", "qualified_id": "analysis-backtest:qmb"}
_GRANT = {
    "op_id": "qmb.analysis.project",
    "op_version": 1,
    "effect_class": "read",
    "parameter_ceiling": {"allow_keys": ["run_fp1", "as_of"]},
    "expires_at": _EXPIRES,
}


def main() -> None:
    assert COPILOT_PRODUCT_IDENTITY == "QuantMind/QMX Copilot"
    assert SECOND_COPILOT_PRODUCT_MINTED is False
    assert IN_APP_PANEL_IS_CONTRACT is True
    assert IN_APP_PANEL_IS_SECOND_COPILOT is False
    assert GAP_0081_CHROME_FILLED is False
    assert PANEL_DISPOSE_CANCELS_JOB_HANDLE is False
    assert APP_USE_MAY_APPLY is False

    host = CopilotHost()
    home = host.open_home(product_session_id="psess:home")
    assert is_ok(home)
    app = host.open_app_use(
        product_session_id="psess:app-use-1",
        instance_id="inst:1",
        panel_id="panel:app",
        copilot_profile=None,
    )
    assert is_ok(app)
    compared = host.compare_seats("psess:home", "psess:app-use-1")
    assert is_ok(compared)
    assert compared.value["independent"] is True
    assert compared.value["second_copilot"] is False
    print("one copilot identity over independently scoped psess:")

    assert is_ok(
        host.sessions.host_grant(
            "psess:home",
            grant_id="grant:home",
            instance_id="inst:1",
            **_GRANT,
        )
    )
    assert is_ok(host.sessions.host_grant("psess:app-use-1", grant_id="grant:app", **_GRANT))
    unioned = host.nested_invoke(
        caller_product_session_id="psess:home",
        callee_product_session_id="psess:app-use-1",
        envelope={
            "logical_invocation_id": "inv:1",
            "attempt_id": 1,
            "op_id": "qmb.analysis.project",
            "op_version": 1,
            "contribution": dict(_CONTRIBUTION),
            "instance_id": "inst:1",
            "config_revision": 4,
            "grant_id": "grant:app",
            "effect_class": "read",
            "idempotency_key": "idem:union",
            "reconcile_policy": "query-then-decide",
            "input_hash": "fp1:sha256:" + ("a" * 64),
            "call_depth": 1,
            "caller_kind": "workflow",
            "parent_logical_invocation_id": "inv:parent",
            "caller_session_ref": "psess:home",
        },
        payload={"run_fp1": "run-1"},
        now=_NOW,
        union_grants=True,
    )
    assert is_refusal(unioned)
    assert isinstance(unioned, NestedGrantUnionRefused)
    print("nested invoke does not union grants")

    owner = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(owner)
    handle = host.submit_job(owner=owner.value, task_id="task-60-4")
    assert is_ok(handle)
    closed = host.dispose_panel(
        "panel:app",
        product_session_id="psess:app-use-1",
        job_id=handle.value.job_id,
    )
    assert is_ok(closed)
    live = host.jobs.handle_for(handle.value.job_id)
    assert live is not None
    assert live.state is JobHandleState.RUNNING
    print("dispose does not cancel JobHandle")

    applied = host.apply_change_request(
        change_request_id="cr:filter-1",
        from_session="psess:app-use-1",
        operator_principal="operator",
        applied_at=_AS_OF,
    )
    assert is_refusal(applied)
    print("app-use cannot apply")


if __name__ == "__main__":
    main()
