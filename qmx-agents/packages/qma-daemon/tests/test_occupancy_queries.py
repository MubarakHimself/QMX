"""Story 36.5 — occupancy versus queries; JobHandle.cancel maps to QMB abort."""

from __future__ import annotations

import json
import runpy
from pathlib import Path

from qma.core.content import content_address
from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.cancel_authority import authorize_qmb_ledger_aborted_writer
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.experiments import ANALYSIS_PUBLISHED_KIND, ExperimentSpec
from qma.core.ports.qmb import (
    QMB_BACKTEST_TOOL_ID,
    QMB_OCCUPANCY_QUERY,
)
from qma.core.refusals import UnauthorizedCancelWriter
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, JobHandleState
from qma.daemon.backtest import (
    BacktestingService,
    CliQmbDoorTransport,
    RecordingQmbDoorTransport,
    cli_qmb_test_double_argv0,
)
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.experiments import ExperimentSpecService
from qma.daemon.taskgraph.records import DispatchLease
from qma.daemon.tools import ToolRegistry
from qma.wire.vocabulary import SEED_EVENT_COUNT, WIRE_EVENTS
from qmf.core import is_ok, is_refusal


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    return minted.value


def _fp(label: str) -> str:
    addressed = content_address({"label": label})
    assert is_ok(addressed)
    return addressed.value.value


def _envs() -> ExecutionEnvironmentRegistry:
    registry = ExecutionEnvironmentRegistry()
    assert is_ok(
        registry.register_declaration(
            ExecutionEnvironmentDeclaration.isolated(
                ExecutionEnvironmentKind.DOCKER,
                provider_ref="local-docker",
            )
        )
    )
    return registry


def _lease() -> DispatchLease:
    return DispatchLease(
        task_id="task-36-5",
        holder_agent_id="agent-analyst-1",
        mission_id="mission-exp",
        owner=_owner(),
    )


def _spec() -> ExperimentSpec:
    created = ExperimentSpec.try_create(
        data_ref="data:eurusd",
        environment_ref="env:docker",
        seed=36,
        model_and_harness_version={"model": "analyst-v1", "harness": "qmb-1"},
        cost_assumptions={"spread_usd_cents": 10},
        resolved_config_ref=_fp("cfg-36-5"),
    )
    assert is_ok(created)
    return created.value


def test_query_does_not_occupy_or_block_a_run() -> None:
    service = BacktestingService(
        tools=ToolRegistry(),
        jobs=JobHandleService(),
        environments=_envs(),
        transport=RecordingQmbDoorTransport(),
    )
    assert is_ok(service.install())
    query = service.place_query(
        "analysis.project",
        owner=_owner(),
        task_id="task-query-1",
        environment_ref="env:docker",
        extra={
            "stdout": json.dumps(
                {
                    "as_of": {"kind": "registry-as-of", "value_ns": 0},
                    "method": "projection",
                    "predicate": {},
                    "source_ct29": "ct29:stream",
                    "source_ct32": _fp("src"),
                },
                separators=(",", ":"),
            )
        },
        mint_ct32=True,
    )
    assert is_refusal(query)
    query = service.place_query(
        "sweep.rank",
        owner=_owner(),
        task_id="task-query-1",
        environment_ref="env:docker",
    )
    assert is_ok(query)
    assert query.value.occupancy == QMB_OCCUPANCY_QUERY
    assert query.value.mints_ct32 is False
    assert query.value.mints_experiment_spec is False
    assert service.occupying_job("env:docker") is None
    run = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=_owner(),
        task_id="task-run-1",
        environment_ref="env:docker",
        experiment_spec_fp1=_fp("run-spec"),
        evidence_ref="evidence:recorded-bars",
    )
    assert is_ok(run)
    assert service.occupying_job("env:docker") == run.value.handle.job_id
    child = service.admit_process_per_run_child("docker", child_job_id="qmb:docker:child")
    assert is_ok(child)
    occupying = service.occupying_job("docker")
    assert occupying == run.value.handle.job_id
    assert service.qmb_opened_daemon_sqlite() is False
    second = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=_owner(),
        task_id="task-run-2",
        environment_ref="env:docker",
        experiment_spec_fp1=_fp("run-spec-2"),
        evidence_ref="evidence:recorded-bars",
    )
    assert is_refusal(second)
    still_query = service.place_query(
        "data.gap-check",
        owner=_owner(),
        task_id="task-query-2",
        environment_ref="env:docker",
    )
    assert is_ok(still_query)
    assert still_query.value.handle.job_id != occupying
    successor = service.experiments
    assert successor is None or is_refusal(successor.mint_query_successor())


def test_cli_cancel_maps_to_qmb_abort_ledger(tmp_path: Path) -> None:
    ledger = tmp_path / "qmb-ledger-aborted.json"
    transport = CliQmbDoorTransport(
        argv0=cli_qmb_test_double_argv0(tmp_path / "qmb_double.py"),
        receipt_path=str(tmp_path / "receipt.json"),
        ledger_path=str(ledger),
        hang=True,
    )
    service = BacktestingService(
        tools=ToolRegistry(),
        jobs=JobHandleService(),
        environments=_envs(),
        transport=transport,
    )
    assert is_ok(service.install())
    try:
        placed = service.invoke(
            QMB_BACKTEST_TOOL_ID,
            owner=_owner(),
            task_id="task-cancel-1",
            environment_ref="env:docker",
            experiment_spec_fp1=_fp("cancel-spec"),
            evidence_ref="evidence:recorded-bars",
        )
        assert is_ok(placed)
        started = service.jobs.start(placed.value.handle.job_id)
        assert is_ok(started)
        assert transport.maps_cancel_to_qmb_abort is True
        cancelled = service.cancel(placed.value.handle.job_id)
        assert is_ok(cancelled)
        assert cancelled.value.state is JobHandleState.CANCELLED
        assert placed.value.handle.job_id in transport.abort_invocations
        assert ledger.is_file()
        line = json.loads(ledger.read_text(encoding="utf-8"))
        assert line["state"] == "aborted"
        assert line["writer"] == "qmb"
        assert line["role"] == "aborted"
        daemon_write = service.append_run_ledger({"role": "aborted"}, writer="daemon")
        assert is_refusal(daemon_write)
        plugin_write = service.append_run_ledger({"role": "aborted"}, writer="plugin")
        assert is_refusal(plugin_write)
        assert UnauthorizedCancelWriter.matches(plugin_write)
        qmb_writer = authorize_qmb_ledger_aborted_writer("qmb")
        assert is_ok(qmb_writer)
        streamed = service.jobs.stream(placed.value.handle.job_id)
        assert is_ok(streamed)
        kinds = [event.kind for event in streamed.value]
        assert "cancel" in kinds
        assert "qmb_abort" in kinds
        assert service.occupying_job("docker") is None
    finally:
        transport.close()


def test_coordinated_projection_persists_json_and_ledger(tmp_path: Path) -> None:
    experiments = ExperimentSpecService()
    lease = _lease()
    registered = experiments.register(
        _spec(),
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(registered)
    spec_fp1 = registered.value.spec.spec_fp1
    transport = CliQmbDoorTransport(
        argv0=cli_qmb_test_double_argv0(tmp_path / "qmb_double.py"),
        receipt_path=str(tmp_path / "receipt.json"),
    )
    service = BacktestingService(
        tools=ToolRegistry(),
        jobs=JobHandleService(),
        environments=_envs(),
        transport=transport,
        experiments=experiments,
        artifact_root=tmp_path,
    )
    assert is_ok(service.install())
    try:
        occupied = service.invoke(
            QMB_BACKTEST_TOOL_ID,
            owner=_owner(),
            task_id="task-run-hold",
            environment_ref="env:docker",
            experiment_spec_fp1=spec_fp1,
            evidence_ref="evidence:recorded-bars",
            dispatch_lease=lease,
            model_deployment_ref="deploy:analyst-v1",
        )
        assert is_ok(occupied)
        query = service.place_query(
            "analysis.project",
            owner=_owner(),
            task_id="task-project-1",
            environment_ref="env:docker",
            persist_projection=True,
            experiment_spec_fp1=spec_fp1,
            dispatch_lease=lease,
            model_deployment_ref="deploy:analyst-v1",
        )
        assert is_ok(query)
        assert query.value.occupancy == QMB_OCCUPANCY_QUERY
        assert query.value.published is not None
        published = query.value.published
        assert published.kind == ANALYSIS_PUBLISHED_KIND
        assert published.mints_ct32 is False
        assert published.mints_experiment_spec is False
        assert published.qmb_opens_daemon_sqlite is False
        json_path = Path(published.json_path)
        assert json_path.is_file()
        body = json.loads(json_path.read_text(encoding="utf-8"))
        assert body["method"] == "projection"
        ledger = experiments.resolve_ledger(spec_fp1)
        assert is_ok(ledger)
        kinds = [entry.body.get("kind") for entry in ledger.value.entries]
        assert ANALYSIS_PUBLISHED_KIND in kinds
        cited = [
            entry
            for entry in ledger.value.entries
            if entry.body.get("kind") == ANALYSIS_PUBLISHED_KIND
        ]
        assert cited[-1].body["saved_view_fp1_ref"] == published.view_fp1
        assert "ct32" not in cited[-1].body
        assert experiments.mint_query_successor() is not None
        assert is_refusal(experiments.mint_query_successor())
        assert service.occupying_job("env:docker") == occupied.value.handle.job_id
        streamed = service.jobs.stream(query.value.handle.job_id)
        assert is_ok(streamed)
        assert any(event.kind == "query" for event in streamed.value)
        assert query.value.handle.state is JobHandleState.DONE
    finally:
        transport.close()


def test_progress_uses_job_handle_and_existing_wire_events() -> None:
    assert len(WIRE_EVENTS) == SEED_EVENT_COUNT
    assert "qmb.progress" not in WIRE_EVENTS
    assert "occupancy.changed" not in WIRE_EVENTS
    jobs = JobHandleService()
    submitted = jobs.submit(owner=_owner(), task_id="task-progress")
    assert is_ok(submitted)
    noted = jobs.record_progress(
        submitted.value.job_id,
        "progress",
        {"surface": "ct-13", "new_event_bus": False},
    )
    assert is_ok(noted)
    streamed = jobs.stream(submitted.value.job_id)
    assert is_ok(streamed)
    kinds = [event.kind for event in streamed.value]
    assert "submit" in kinds
    assert "progress" in kinds
    for event in streamed.value:
        if event.kind == "progress":
            assert event.body.get("new_event_bus") is not True


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "occupancy_query_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
