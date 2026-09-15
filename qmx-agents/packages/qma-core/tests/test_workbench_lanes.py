"""Story 36.4 — caller-declared lane flags are refused on the QMB door."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.experiments import (
    EXPERIMENT_LEDGER_WORKBENCH_LANE,
    QMB_LEDGER_WORKBENCH_LANE,
    admit_experiment_evidence_body,
    coordinated_run_labels,
    refuse_caller_declared_lane_fields,
)
from qma.core.ports.qmb import parse_qmb_backtest_request
from qmf.core import is_ok, is_refusal
from qmf.core.refusal import RefusalCategory


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    return minted.value


def _request(**fields: object):
    payload: dict[str, object] = {
        "owner": _owner(),
        "task_id": "task-bt-1",
        "environment_ref": "env:docker",
        "experiment_spec_fp1": "fp1:sha256:" + ("a" * 64),
        "evidence_ref": "evidence:recorded-bars",
    }
    payload.update(fields)
    return parse_qmb_backtest_request(**payload)


def test_coordinated_labels_are_two_objects() -> None:
    labels = coordinated_run_labels()
    assert labels["qmb_ledger_workbench_lane"] == QMB_LEDGER_WORKBENCH_LANE == "governed"
    assert labels["experiment_ledger_workbench_lane"] == EXPERIMENT_LEDGER_WORKBENCH_LANE
    assert labels["experiment_ledger_workbench_lane"] == "coordinated"
    assert labels["door"] == "coordinated"
    assert "workbench_lane" not in labels


def test_caller_declared_lane_on_payload_is_refused() -> None:
    extra = _request(extra={"workbench_lane": "coordinated"})
    assert is_refusal(extra)
    assert extra.category is RefusalCategory.POLICY_REJECTION
    assert extra.context["field"] == "workbench_lane"
    assert extra.context["spine_amendment"] is True
    flagged = _request(lane="governed")
    assert is_refusal(flagged)
    method = _request(analysis_method="rerun")
    assert is_refusal(method)
    blocked = refuse_caller_declared_lane_fields(workbench_lane="governed")
    assert blocked is not None
    assert blocked.context["qmb_ledger_workbench_lane"] == "governed"
    assert blocked.context["experiment_ledger_workbench_lane"] == "coordinated"


def test_experiment_ledger_body_stamps_coordinated_and_refuses_collapse() -> None:
    admitted = admit_experiment_evidence_body(
        {"ct32_ref": "fp1:sha256:" + ("b" * 64), "qmb_ledger_ref": "qmb-ledger:run-1"}
    )
    assert is_ok(admitted)
    assert admitted.value["workbench_lane"] == "coordinated"
    collapsed = admit_experiment_evidence_body(
        {"ct32_ref": "fp1:sha256:" + ("c" * 64), "qmb_ledger_workbench_lane": "governed"}
    )
    assert is_refusal(collapsed)
    wrong = admit_experiment_evidence_body({"workbench_lane": "governed"})
    assert is_refusal(wrong)
    ok_explicit = admit_experiment_evidence_body({"workbench_lane": "coordinated"})
    assert is_ok(ok_explicit)
