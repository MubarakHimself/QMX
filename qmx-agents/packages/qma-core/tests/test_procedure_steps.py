"""Story 37.2 — procedure run-steps occupy; query-steps do not (FR-W33)."""

from __future__ import annotations

from qma.core.control import (
    EPIC_33_QUERY_COMMANDS,
    EPIC_35_QUERY_COMMANDS,
    PROCEDURE_QUERY_STEP_COMMANDS,
    PROCEDURE_RUN_STEP_COMMANDS,
    PROCEDURE_STEP_TYPES,
    QMB_PROCEDURE_DOOR_STEPS,
    classify_procedure_step,
    is_query_step,
    is_run_step,
    procedure_step_command,
)
from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.qmb import (
    QMB_OCCUPANCY_QUERY,
    QMB_OCCUPANCY_RUN,
    QMB_RUN_COMMANDS,
    build_qmb_door_invocation,
    classify_qmb_door_occupancy,
    parse_qmb_backtest_request,
    refuse_query_ct32_or_successor,
)
from qmf.core import is_ok, is_refusal


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    return minted.value


def test_run_commands_occupy_and_query_commands_do_not() -> None:
    run_named = (
        "backtest",
        "optimize",
        "sweep",
        "robustness",
        "analysis.rerun",
        "data.download",
    )
    for command in run_named:
        classified = classify_procedure_step(command)
        assert is_ok(classified), command
        assert classified.value.occupancy == QMB_OCCUPANCY_RUN
        assert classified.value.consumes_environment is True
        assert is_run_step(command)
        assert not is_query_step(command)
    query_named = (
        "analysis.project",
        "compare_runs",
        "sweep.rank",
        "data.gap-check",
        "data.verify",
        "data.catalog",
        "data.list",
    )
    for command in query_named:
        classified = classify_procedure_step(command)
        assert is_ok(classified), command
        assert classified.value.occupancy == QMB_OCCUPANCY_QUERY
        assert classified.value.consumes_environment is False
        assert classified.value.mints_ct32 is False
        assert classified.value.mints_experiment_spec is False
        assert is_query_step(command)
        assert not is_run_step(command)
    assert PROCEDURE_RUN_STEP_COMMANDS == QMB_RUN_COMMANDS
    assert EPIC_35_QUERY_COMMANDS <= PROCEDURE_QUERY_STEP_COMMANDS
    assert EPIC_33_QUERY_COMMANDS <= PROCEDURE_QUERY_STEP_COMMANDS


def test_pack_step_types_match_door_occupancy() -> None:
    ids = {str(node["id"]) for node in PROCEDURE_STEP_TYPES}
    assert {"backtest", "optimize", "sweep", "robustness", "rerun", "download"} <= ids
    assert {"project", "compare", "rank", "gap-check", "verify", "catalog", "list"} <= ids
    for node in PROCEDURE_STEP_TYPES:
        classified = classify_procedure_step(node)
        assert is_ok(classified)
        assert classified.value.occupancy == node["placement"]
        door = classify_qmb_door_occupancy(node["command"])
        assert is_ok(door)
        assert door.value.occupancy == classified.value.occupancy
    sample_ids = {str(node["id"]) for node in QMB_PROCEDURE_DOOR_STEPS}
    assert sample_ids == {"backtest", "project", "rank", "download"}


def test_mismatched_placement_is_refused() -> None:
    refused = classify_procedure_step(
        {
            "id": "project",
            "command": "analysis.project",
            "placement": QMB_OCCUPANCY_RUN,
        }
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "placement"
    resolved = procedure_step_command({"id": "rank"})
    assert is_ok(resolved)
    assert resolved.value == "sweep.rank"


def test_run_invocation_builder_refuses_query_commands() -> None:
    created = parse_qmb_backtest_request(
        owner=_owner(),
        task_id="task-bt-1",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:sha256:" + ("a" * 64),
        evidence_ref="evidence:recorded-bars",
    )
    assert is_ok(created)
    run = build_qmb_door_invocation(
        created.value,
        job_id="qmb:docker:t1",
        command="optimize.run",
    )
    assert is_ok(run)
    assert run.value.argv == ("optimize", "run")
    assert run.value.payload["occupancy"] == QMB_OCCUPANCY_RUN
    query = build_qmb_door_invocation(
        created.value,
        job_id="qmb:docker:t1",
        command="analysis.project",
    )
    assert is_refusal(query)
    successor = refuse_query_ct32_or_successor(command="sweep.rank")
    assert is_refusal(successor)
    assert successor.context["mints_ct32"] is False
    assert successor.context["mints_experiment_spec"] is False
