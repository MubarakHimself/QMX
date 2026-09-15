"""Story 37.2 — run-steps occupy the door; query-steps call Epic 35/33."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.barriers import assert_no_qmb_import, scan_qmb_imports
from qma.core.content import content_address
from qma.core.control import (
    EPIC_33_QUERY_COMMANDS,
    EPIC_35_QUERY_COMMANDS,
    PROCEDURE_STEP_TYPES,
    author_procedure,
)
from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.plugins import analysis_procedure_graph_payload
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.qmb import (
    QMB_OCCUPANCY_QUERY,
    QMB_OCCUPANCY_RUN,
    refuse_query_ct32_or_successor,
)
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.daemon.backtest import BacktestingService, RecordingQmbDoorTransport
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.experiments import ExperimentSpecService
from qma.daemon.taskgraph import execute_procedure_door_step
from qma.daemon.tools import ToolRegistry
from qmf.core import is_ok, is_refusal

AGENTS_ROOT = Path(__file__).resolve().parents[3]
DAEMON_SRC = Path(__file__).resolve().parents[1] / "src"
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "procedure_step_usage.py"


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


def _service() -> tuple[BacktestingService, RecordingQmbDoorTransport]:
    transport = RecordingQmbDoorTransport()
    service = BacktestingService(
        tools=ToolRegistry(),
        jobs=JobHandleService(),
        environments=_envs(),
        transport=transport,
    )
    assert is_ok(service.install())
    return service, transport


def _spec_fp1() -> str:
    return _fp("proc-spec")


EVIDENCE_REF = "evidence:recorded-bars"


def test_run_step_occupies_the_story_36_2_door() -> None:
    service, transport = _service()
    placed = service.place_procedure_step(
        "backtest.run",
        owner=_owner(),
        task_id="task-run-bt",
        environment_ref="env:docker",
        experiment_spec_fp1=_spec_fp1(),
        evidence_ref=EVIDENCE_REF,
    )
    assert is_ok(placed)
    row = placed.value
    assert row.occupancy == QMB_OCCUPANCY_RUN
    assert row.consumes_environment is True
    assert row.mints_ct32 is True
    assert row.mints_experiment_spec is False
    assert row.run is not None
    assert row.query is None
    assert service.occupying_job("env:docker") == row.run.handle.job_id
    assert len(transport.invocations) == 1
    assert transport.invocations[0].argv == ("backtest", "run")
    assert transport.invocations[0].program == "qmb"
    assert transport.invocations[0].import_edge is False


def test_named_run_steps_place_one_cli_invocation() -> None:
    _, transport = _service()
    commands = (
        ("optimize.run", ("optimize", "run"), True),
        ("sweep.batch", ("sweep", "batch"), True),
        ("robustness.walk-forward", ("robustness", "walk-forward"), True),
        ("analysis.rerun", ("analysis", "rerun"), True),
        ("data.download", ("data", "download"), False),
    )
    for index, (command, argv, mints_ct32) in enumerate(commands):
        other = BacktestingService(
            tools=ToolRegistry(),
            jobs=JobHandleService(),
            environments=_envs(),
            transport=transport,
        )
        assert is_ok(other.install())
        placed = other.place_procedure_step(
            command,
            owner=_owner(),
            task_id=f"task-run-{index}",
            environment_ref="env:docker",
            experiment_spec_fp1=_spec_fp1(),
            evidence_ref=EVIDENCE_REF,
        )
        assert is_ok(placed), command
        assert placed.value.occupancy == QMB_OCCUPANCY_RUN
        assert placed.value.mints_ct32 is mints_ct32
        assert placed.value.run is not None
        assert placed.value.run.invocation.argv == argv
        assert other.occupying_job("docker") == placed.value.run.handle.job_id


def test_query_steps_call_epic_35_and_33_door_queries() -> None:
    service, _transport = _service()
    expected = {
        "analysis.project": ("analysis", "project"),
        "analysis.compare": ("analysis", "compare"),
        "compare_runs": ("analysis", "compare"),
        "sweep.rank": ("sweep", "rank"),
        "data.gap-check": ("data", "gap-check"),
        "data.verify": ("data", "verify"),
        "data.catalog": ("data", "catalog"),
        "data.list": ("data", "list"),
    }
    assert EPIC_35_QUERY_COMMANDS | EPIC_33_QUERY_COMMANDS | {"sweep.rank"} <= set(expected)
    for command, argv in expected.items():
        placed = service.place_procedure_step(
            command,
            owner=_owner(),
            task_id=f"task-q-{command}",
            environment_ref="env:docker",
        )
        assert is_ok(placed), command
        row = placed.value
        assert row.occupancy == QMB_OCCUPANCY_QUERY
        assert row.consumes_environment is False
        assert row.mints_ct32 is False
        assert row.mints_experiment_spec is False
        assert row.query is not None
        assert row.run is None
        assert row.query.invocation.argv == argv
        assert row.query.handle.job_id.startswith("qmbq:")
    assert service.occupying_job("env:docker") is None
    assert service.qmb_opened_daemon_sqlite() is False
    source = Path(service.place_procedure_step.__code__.co_filename).read_text(encoding="utf-8")
    assert "self.place_query(" in source
    assert "def project(" not in source
    assert "def compare_runs(" not in source


def test_occupied_env_refuses_second_run_but_queries_proceed() -> None:
    service, _transport = _service()
    first = service.place_procedure_step(
        {"id": "backtest", "command": "backtest.run", "placement": "run"},
        owner=_owner(),
        task_id="task-hold",
        environment_ref="env:docker",
        experiment_spec_fp1=_spec_fp1(),
        evidence_ref=EVIDENCE_REF,
    )
    assert is_ok(first)
    occupying = service.occupying_job("env:docker")
    assert occupying is not None
    second = service.place_procedure_step(
        "optimize.run",
        owner=_owner(),
        task_id="task-second-run",
        environment_ref="env:docker",
        experiment_spec_fp1=_spec_fp1(),
        evidence_ref=EVIDENCE_REF,
    )
    assert is_refusal(second)
    assert second.context["field"] == "qmb_job"
    assert service.occupying_job("env:docker") == occupying
    query = service.place_procedure_step(
        "analysis.project",
        owner=_owner(),
        task_id="task-query-while-held",
        environment_ref="env:docker",
    )
    assert is_ok(query)
    assert query.value.occupancy == QMB_OCCUPANCY_QUERY
    assert query.value.query is not None
    assert query.value.query.handle.job_id != occupying
    assert service.occupying_job("env:docker") == occupying
    rank = service.place_procedure_step(
        "sweep.rank",
        owner=_owner(),
        task_id="task-rank-while-held",
        environment_ref="env:docker",
    )
    assert is_ok(rank)
    assert service.occupying_job("env:docker") == occupying


def test_query_step_mints_no_ct32_or_spec_successor() -> None:
    service, _transport = _service()
    ct32 = service.place_procedure_step(
        "compare_runs",
        owner=_owner(),
        task_id="task-compare",
        environment_ref="env:docker",
        mint_ct32=True,
    )
    assert is_refusal(ct32)
    assert refuse_query_ct32_or_successor(command="compare_runs").context["mints_ct32"] is False
    successor = service.place_procedure_step(
        "data.catalog",
        owner=_owner(),
        task_id="task-catalog",
        environment_ref="env:docker",
        successor=True,
    )
    assert is_refusal(successor)
    experiments = ExperimentSpecService()
    assert is_refusal(experiments.mint_query_successor())
    ok_query = service.place_procedure_step(
        "data.list",
        owner=_owner(),
        task_id="task-list",
        environment_ref="env:docker",
    )
    assert is_ok(ok_query)
    assert ok_query.value.mints_ct32 is False
    assert ok_query.value.mints_experiment_spec is False


def test_graph_template_node_executes_through_the_door() -> None:
    service, transport = _service()
    authored = author_procedure(analysis_procedure_graph_payload())
    assert is_ok(authored)
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    owner = Quant(
        actor_id=minted.value,
        desk=DeskSlug.ANALYSIS,
        quant_slug="notebook",
        role=RoleName.ANALYST,
        name="Quant notebook",
    )
    run = execute_procedure_door_step(
        authored.value,
        "backtest",
        service=service,
        owner=owner,
        environment_ref="env:docker",
        experiment_spec_fp1=_spec_fp1(),
        evidence_ref=EVIDENCE_REF,
    )
    assert is_ok(run)
    assert run.value.occupancy == QMB_OCCUPANCY_RUN
    assert transport.invocations[0].argv == ("backtest", "run")
    project = execute_procedure_door_step(
        authored.value,
        "project",
        service=service,
        owner=owner,
        environment_ref="env:docker",
        task_id="task-project-node",
    )
    assert is_ok(project)
    assert project.value.occupancy == QMB_OCCUPANCY_QUERY
    unknown = execute_procedure_door_step(
        authored.value,
        "missing",
        service=service,
        owner=owner,
        environment_ref="env:docker",
    )
    assert is_refusal(unknown)
    assert len(PROCEDURE_STEP_TYPES) >= 13


def test_daemon_still_never_imports_qmb() -> None:
    assert_no_qmb_import(DAEMON_SRC)
    assert scan_qmb_imports(DAEMON_SRC) == ()
    assert_no_qmb_import(AGENTS_ROOT / "plugins")
    assert scan_qmb_imports(AGENTS_ROOT / "plugins") == ()


def test_procedure_step_usage_example() -> None:
    namespace = runpy.run_path(str(EXAMPLE), run_name="__main__")
    assert callable(namespace["main"])
    namespace["main"]()
