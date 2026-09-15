"""Story 45.8 — single QMB door definitions (FR-Q55; CT-47)."""

from __future__ import annotations

from qma.core.barriers.capability import CapabilityRung
from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.qmb import (
    ANALYSIS_BACKTEST_PLUGIN_ID,
    QMB_BACKTEST_TOOL_ID,
    QMB_CHILD_PROCESSES_ARE_QMA_JOBS,
    QMB_CLI_ARGV,
    QMB_CLI_PROGRAM,
    QMB_OCCUPANCY_QUERY,
    QMB_OCCUPANCY_RUN,
    QMB_OPENS_DAEMON_SQLITE,
    QMB_OWNED_CONCERNS,
    QMB_PROCESS_PER_RUN_CHILD,
    QMB_ROUTE,
    QMB_WORLD_REPLAY,
    QmbDoorKind,
    admit_qmb_job,
    build_qmb_cli_argv,
    build_qmb_door_invocation,
    classify_qmb_door_occupancy,
    environment_kind_from_ref,
    occupying_qmb_job,
    parse_qmb_backtest_request,
    process_per_run_child_is_qma_job,
    qma_owns_backtest_concern,
    qmb_backtest_tool_record,
    qmb_opens_daemon_sqlite,
    refuse_qmb_import_edge,
    refuse_query_ct32_or_successor,
    refuse_second_qmb_job,
    release_qmb_job,
)
from qma.core.ports.tools import ToolKind
from qma.core.refusals import NAMED_REFUSAL_VARIANTS
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
    return parse_qmb_backtest_request(
        owner=payload["owner"],
        task_id=payload["task_id"],
        environment_ref=payload["environment_ref"],
        experiment_spec_fp1=payload["experiment_spec_fp1"],
        evidence_ref=payload["evidence_ref"],
        world=payload.get("world", QMB_WORLD_REPLAY),
        door=payload.get("door", QmbDoorKind.CLI),
        recorded=payload.get("recorded", True),
        tool_id=payload.get("tool_id", QMB_BACKTEST_TOOL_ID),
        extra=payload.get("extra"),
        account=payload.get("account"),
        venue=payload.get("venue"),
        paper=payload.get("paper"),
        live=payload.get("live"),
    )


def test_backtest_tool_is_the_one_analysis_backtest_entry() -> None:
    record = qmb_backtest_tool_record()
    assert record.tool_id == QMB_BACKTEST_TOOL_ID
    assert record.plugin_id == ANALYSIS_BACKTEST_PLUGIN_ID
    assert record.kind is ToolKind.BACKTEST
    assert record.capability_rung is CapabilityRung.CONTAINERIZED_PROGRAM
    assert "backtest" in record.acts
    assert record.schema["world"] == QMB_WORLD_REPLAY
    assert record.schema["route"] == list(QMB_ROUTE)


def test_request_is_replay_recorded_evidence_only() -> None:
    created = _request()
    assert is_ok(created)
    assert created.value.world == QMB_WORLD_REPLAY
    assert created.value.recorded is True
    assert created.value.occupancy_key == "docker"
    assert created.value.tool_id == QMB_BACKTEST_TOOL_ID
    assert created.value.to_payload()["route"] == list(QMB_ROUTE)


def test_environment_kind_from_prefixed_ref() -> None:
    parsed = environment_kind_from_ref("env:docker-analysis")
    assert is_ok(parsed)
    assert parsed.value == "docker"


def test_venue_account_and_non_replay_world_are_refused() -> None:
    venue = _request(venue="ctrader-demo")
    assert is_refusal(venue)
    assert venue.category is RefusalCategory.POLICY_REJECTION
    assert venue.context["field"] == "venue"
    paper = _request(world="paper")
    assert is_refusal(paper)
    extra = _request(extra={"account_id": "acct-1"})
    assert is_refusal(extra)
    live_evidence = _request(evidence_ref="open_position")
    assert is_refusal(live_evidence)
    unrecorded = _request(recorded=False)
    assert is_refusal(unrecorded)


def test_one_qmb_job_per_environment_occupancy() -> None:
    first = admit_qmb_job({}, occupancy_key="docker", job_id="qmb:docker:t1")
    assert is_ok(first)
    assert occupying_qmb_job(first.value, "docker") == "qmb:docker:t1"
    second = admit_qmb_job(first.value, occupancy_key="docker", job_id="qmb:docker:t2")
    assert is_refusal(second)
    assert second.context["field"] == "qmb_job"
    other = admit_qmb_job(first.value, occupancy_key="local", job_id="qmb:local:t3")
    assert is_ok(other)
    released = release_qmb_job(first.value, occupancy_key="docker", job_id="qmb:docker:t1")
    retry = admit_qmb_job(released, occupancy_key="docker", job_id="qmb:docker:t2")
    assert is_ok(retry)
    named = refuse_second_qmb_job(environment_ref="docker", occupying_job_id="qmb:docker:t1")
    assert named.category is RefusalCategory.POLICY_REJECTION


def test_door_invocation_is_runtime_not_import() -> None:
    created = _request()
    assert is_ok(created)
    invocation = build_qmb_door_invocation(created.value, job_id="qmb:docker:t1")
    assert is_ok(invocation)
    assert invocation.value.program == QMB_CLI_PROGRAM
    assert invocation.value.argv == QMB_CLI_ARGV
    assert invocation.value.import_edge is False
    assert invocation.value.payload["world"] == QMB_WORLD_REPLAY
    assert invocation.value.payload["qma_re_specifies"] is False
    mcp = _request(door=QmbDoorKind.MCP)
    assert is_ok(mcp)
    mcp_inv = build_qmb_door_invocation(mcp.value, job_id="qmb:docker:t1")
    assert is_ok(mcp_inv)
    assert mcp_inv.value.kind is QmbDoorKind.MCP
    assert mcp_inv.value.program == QMB_CLI_PROGRAM


def test_qma_does_not_own_qmb_backtest_concerns() -> None:
    for concern in QMB_OWNED_CONCERNS:
        assert qma_owns_backtest_concern(concern) is False
    refused = refuse_qmb_import_edge()
    assert is_refusal(refused)
    assert refused.context["field"] == "import"


def test_second_qmb_job_is_not_a_new_named_variant() -> None:
    names = [cls.VARIANT for cls in NAMED_REFUSAL_VARIANTS]
    assert "SecondQmbJob" not in names
    assert "QmbImportEdge" not in names


def test_occupancy_classifies_runs_versus_queries() -> None:
    run_commands = (
        "backtest.run",
        ("optimize", "run"),
        "sweep.batch",
        "robustness.walk-forward",
        "analysis.rerun",
        "data.download",
        "data.generate",
    )
    for command in run_commands:
        classified = classify_qmb_door_occupancy(command)
        assert is_ok(classified)
        assert classified.value.occupancy == QMB_OCCUPANCY_RUN
        assert classified.value.consumes_environment is True
        assert classified.value.children_are_qma_jobs is False
        assert classified.value.mints_experiment_spec is False
        assert classified.value.opens_daemon_sqlite is False
    query_commands = (
        "analysis.project",
        "compare_runs",
        "sweep.rank",
        "ledger.merge",
        "data.gap-check",
        "data.verify",
        "data.catalog",
        "data.list",
    )
    for command in query_commands:
        classified = classify_qmb_door_occupancy(command)
        assert is_ok(classified)
        assert classified.value.occupancy == QMB_OCCUPANCY_QUERY
        assert classified.value.consumes_environment is False
        assert classified.value.mints_ct32 is False
        assert classified.value.mints_experiment_spec is False
    argv = build_qmb_cli_argv("analysis.project")
    assert is_ok(argv)
    assert argv.value == ("analysis", "project")
    assert QMB_CLI_ARGV == ("backtest", "run")
    assert qmb_opens_daemon_sqlite() is False
    assert QMB_OPENS_DAEMON_SQLITE is False
    assert process_per_run_child_is_qma_job() is False
    assert QMB_CHILD_PROCESSES_ARE_QMA_JOBS is False
    refused = refuse_query_ct32_or_successor(command="analysis.project")
    assert is_refusal(refused)
    assert refused.context["mints_ct32"] is False
    assert refused.context["mints_experiment_spec"] is False


def test_queries_and_process_children_do_not_consume_occupancy() -> None:
    first = admit_qmb_job({}, occupancy_key="docker", job_id="qmb:docker:t1")
    assert is_ok(first)
    query = admit_qmb_job(
        first.value,
        occupancy_key="docker",
        job_id="qmbq:docker:q1",
        occupancy_class=QMB_OCCUPANCY_QUERY,
    )
    assert is_ok(query)
    assert occupying_qmb_job(query.value, "docker") == "qmb:docker:t1"
    child = admit_qmb_job(
        first.value,
        occupancy_key="docker",
        job_id="qmb:docker:child",
        kind=QMB_PROCESS_PER_RUN_CHILD,
    )
    assert is_ok(child)
    assert occupying_qmb_job(child.value, "docker") == "qmb:docker:t1"
    second = admit_qmb_job(first.value, occupancy_key="docker", job_id="qmb:docker:t2")
    assert is_refusal(second)
