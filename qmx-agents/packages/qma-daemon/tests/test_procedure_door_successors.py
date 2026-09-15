"""Story 37.3 — config-changing door steps mint ExperimentSpec successors."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.barriers import assert_no_qmb_import, scan_qmb_imports
from qma.core.content import content_address
from qma.core.control import (
    PROCEDURE_IS_EXPERIMENT_SPEC,
    PROCEDURE_SUCCESSOR_EDGE_TYPE,
    author_procedure,
    procedure_mints_ct07_edge,
    procedure_successor_edge_type,
    procedure_uses_bot_supersedes,
)
from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.plugins import analysis_procedure_graph_payload
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.experiments import (
    COORDINATED_CONTINUITY_KIND,
    EXPERIMENT_LINEAGE_EDGE_TYPE,
    ExperimentSpec,
    admit_coordinated_continuity,
)
from qma.core.ports.qmb import QMB_OCCUPANCY_QUERY, QMB_OCCUPANCY_RUN
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.daemon.backtest import BacktestingService, RecordingQmbDoorTransport
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.experiments import ExperimentSpecService
from qma.daemon.taskgraph import execute_procedure_door_step
from qma.daemon.taskgraph.records import DispatchLease
from qma.daemon.tools import ToolRegistry
from qmf.core import is_ok, is_refusal
from qmf.registry import EdgeType

AGENTS_ROOT = Path(__file__).resolve().parents[3]
DAEMON_SRC = Path(__file__).resolve().parents[1] / "src"
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "procedure_successor_usage.py"
EVIDENCE_REF = "evidence:recorded-bars"


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


def _lease(*, task_id: str = "task-37-3") -> DispatchLease:
    return DispatchLease(
        task_id=task_id,
        holder_agent_id="agent-analyst-1",
        mission_id="mission-exp",
        owner=_owner(),
    )


def _spec(*, config: str = "cfg-37-3") -> ExperimentSpec:
    created = ExperimentSpec.try_create(
        data_ref="data:eurusd",
        environment_ref="env:docker",
        seed=37,
        model_and_harness_version={"model": "analyst-v1", "harness": "qmb-1"},
        cost_assumptions={"spread_usd_cents": 10},
        resolved_config_ref=_fp(config),
    )
    assert is_ok(created)
    return created.value


def _service(
    experiments: ExperimentSpecService | None = None,
) -> tuple[BacktestingService, RecordingQmbDoorTransport]:
    transport = RecordingQmbDoorTransport()
    service = BacktestingService(
        tools=ToolRegistry(),
        jobs=JobHandleService(),
        environments=_envs(),
        transport=transport,
        experiments=experiments,
    )
    assert is_ok(service.install())
    return service, transport


def test_config_changing_door_step_mints_successor_via_create_successor() -> None:
    experiments = ExperimentSpecService()
    lease = _lease()
    registered = experiments.register(
        _spec(),
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(registered)
    predecessor = registered.value.spec
    predecessor_payload = dict(predecessor.to_payload())
    service, transport = _service(experiments)
    nxt = _fp("cfg-37-3-next")
    placed = service.place_procedure_step(
        "optimize.run",
        owner=_owner(),
        task_id="task-opt",
        environment_ref="env:docker",
        experiment_spec_fp1=predecessor.spec_fp1,
        evidence_ref=EVIDENCE_REF,
        resolved_config_ref=nxt,
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(placed), placed
    row = placed.value
    assert row.occupancy == QMB_OCCUPANCY_RUN
    assert row.mints_experiment_spec is True
    assert row.successor is not None
    assert row.successor.spec.resolved_config_ref == nxt
    assert row.successor.spec.spec_fp1 != predecessor.spec_fp1
    assert row.successor.spec.code_ref is None
    assert row.experiment_spec_fp1 == row.successor.spec.spec_fp1
    assert row.continuity == COORDINATED_CONTINUITY_KIND
    edge = row.successor.lineage_edge
    assert edge is not None
    assert edge.edge_type is EdgeType.BRANCHES_FROM
    assert edge.edge_type.value == EXPERIMENT_LINEAGE_EDGE_TYPE
    assert edge.edge_type.value == PROCEDURE_SUCCESSOR_EDGE_TYPE
    assert edge.from_ref.value == row.successor.spec.spec_fp1
    assert edge.to_ref.value == predecessor.spec_fp1
    still = experiments.resolve(predecessor.spec_fp1)
    assert is_ok(still)
    assert dict(still.value.spec.to_payload()) == predecessor_payload
    edges = experiments.lineage_edges(predecessor.spec_fp1)
    assert len(edges) == 1
    assert edges[0].edge_type is EdgeType.BRANCHES_FROM
    assert transport.invocations[0].argv == ("optimize", "run")
    source = Path(service.place_procedure_step.__code__.co_filename).read_text(encoding="utf-8")
    assert "create_successor(" in source
    assert "EXPERIMENT_CHANGE_RESOLVED_CONFIG" in source
    assert "EXPERIMENT_LINEAGE_EDGE_TYPE" in source
    assert "EdgeType.SUPERSEDES" not in source


def test_same_resolved_config_does_not_mint_successor() -> None:
    experiments = ExperimentSpecService()
    lease = _lease()
    registered = experiments.register(
        _spec(config="same"),
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(registered)
    service, _transport = _service(experiments)
    placed = service.place_procedure_step(
        "backtest.run",
        owner=_owner(),
        task_id="task-same",
        environment_ref="env:docker",
        experiment_spec_fp1=registered.value.spec.spec_fp1,
        evidence_ref=EVIDENCE_REF,
        resolved_config_ref=registered.value.spec.resolved_config_ref,
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(placed)
    assert placed.value.mints_experiment_spec is False
    assert placed.value.successor is None
    assert placed.value.experiment_spec_fp1 == registered.value.spec.spec_fp1
    assert experiments.lineage_edges(registered.value.spec.spec_fp1) == ()


def test_query_step_without_config_change_mints_no_successor() -> None:
    service, _transport = _service()
    assert service.occupying_job("env:docker") is None
    placed = service.place_procedure_step(
        "analysis.project",
        owner=_owner(),
        task_id="task-project",
        environment_ref="env:docker",
    )
    assert is_ok(placed)
    row = placed.value
    assert row.occupancy == QMB_OCCUPANCY_QUERY
    assert row.consumes_environment is False
    assert row.mints_ct32 is False
    assert row.mints_experiment_spec is False
    assert row.successor is None
    assert row.run is None
    assert service.occupying_job("env:docker") is None
    rank = service.place_procedure_step(
        "sweep.rank",
        owner=_owner(),
        task_id="task-rank",
        environment_ref="env:docker",
    )
    assert is_ok(rank)
    assert rank.value.mints_experiment_spec is False
    assert service.occupying_job("env:docker") is None
    experiments = ExperimentSpecService()
    assert is_refusal(experiments.mint_query_successor())


def test_query_step_cannot_change_resolved_config() -> None:
    experiments = ExperimentSpecService()
    lease = _lease()
    registered = experiments.register(
        _spec(config="query"),
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(registered)
    service, _transport = _service(experiments)
    refused = service.place_procedure_step(
        "compare_runs",
        owner=_owner(),
        task_id="task-compare",
        environment_ref="env:docker",
        experiment_spec_fp1=registered.value.spec.spec_fp1,
        resolved_config_ref=_fp("cfg-query-change"),
    )
    assert is_refusal(refused)
    assert refused.context["mints_experiment_spec"] is False
    assert service.occupying_job("env:docker") is None
    assert experiments.lineage_edges(registered.value.spec.spec_fp1) == ()


def test_config_changing_step_requires_experiments_and_lease() -> None:
    service, _transport = _service()
    unbound = service.place_procedure_step(
        "optimize.run",
        owner=_owner(),
        task_id="task-unbound",
        environment_ref="env:docker",
        experiment_spec_fp1=_fp("unbound"),
        evidence_ref=EVIDENCE_REF,
        resolved_config_ref=_fp("cfg-unbound"),
    )
    assert is_refusal(unbound)
    assert unbound.context["field"] == "experiments"
    experiments = ExperimentSpecService()
    lease = _lease()
    registered = experiments.register(
        _spec(config="lease"),
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(registered)
    bound, _other = _service(experiments)
    missing_lease = bound.place_procedure_step(
        "optimize.run",
        owner=_owner(),
        task_id="task-no-lease",
        environment_ref="env:docker",
        experiment_spec_fp1=registered.value.spec.spec_fp1,
        evidence_ref=EVIDENCE_REF,
        resolved_config_ref=_fp("cfg-no-lease"),
    )
    assert is_refusal(missing_lease)
    assert missing_lease.context["field"] == "dispatch_lease"


def test_bot_supersedes_and_new_edge_kinds_are_refused() -> None:
    experiments = ExperimentSpecService()
    lease = _lease()
    registered = experiments.register(
        _spec(config="edge"),
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(registered)
    service, _transport = _service(experiments)
    supersedes = service.place_procedure_step(
        "optimize.run",
        owner=_owner(),
        task_id="task-sup",
        environment_ref="env:docker",
        experiment_spec_fp1=registered.value.spec.spec_fp1,
        evidence_ref=EVIDENCE_REF,
        resolved_config_ref=_fp("cfg-sup"),
        edge_type="supersedes",
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_refusal(supersedes)
    assert supersedes.context["uses_bot_supersedes"] is False
    minted = service.place_procedure_step(
        "optimize.run",
        owner=_owner(),
        task_id="task-new-edge",
        environment_ref="env:docker",
        experiment_spec_fp1=registered.value.spec.spec_fp1,
        evidence_ref=EVIDENCE_REF,
        resolved_config_ref=_fp("cfg-new-edge"),
        edge_type="experiment-predecessor",
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_refusal(minted)
    assert minted.context["mints_ct07_edge"] is False
    assert procedure_uses_bot_supersedes() is False
    assert procedure_mints_ct07_edge() is False
    assert procedure_successor_edge_type() == "branches-from"


def test_procedure_record_is_not_the_continuity_object() -> None:
    authored = author_procedure(analysis_procedure_graph_payload())
    assert is_ok(authored)
    assert authored.value.is_experiment_spec is PROCEDURE_IS_EXPERIMENT_SPEC
    continuity = admit_coordinated_continuity(COORDINATED_CONTINUITY_KIND)
    assert is_ok(continuity)
    assert continuity.value == COORDINATED_CONTINUITY_KIND
    assert is_refusal(admit_coordinated_continuity("procedure"))
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    owner = Quant(
        actor_id=minted.value,
        desk=DeskSlug.ANALYSIS,
        quant_slug="notebook",
        role=RoleName.ANALYST,
        name="Quant notebook",
    )
    experiments = ExperimentSpecService()
    lease = _lease(task_id="task-node")
    registered = experiments.register(
        _spec(config="node"),
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(registered)
    service, _transport = _service(experiments)
    run = execute_procedure_door_step(
        authored.value,
        "backtest",
        service=service,
        owner=owner,
        environment_ref="env:docker",
        experiment_spec_fp1=registered.value.spec.spec_fp1,
        evidence_ref=EVIDENCE_REF,
        resolved_config_ref=_fp("cfg-node-next"),
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
        task_id="task-node",
    )
    assert is_ok(run)
    assert run.value.mints_experiment_spec is True
    assert run.value.successor is not None
    assert run.value.successor.lineage_edge is not None
    assert run.value.successor.lineage_edge.edge_type is EdgeType.BRANCHES_FROM
    assert run.value.continuity == COORDINATED_CONTINUITY_KIND


def test_daemon_still_never_imports_qmb() -> None:
    assert_no_qmb_import(DAEMON_SRC)
    assert scan_qmb_imports(DAEMON_SRC) == ()
    assert_no_qmb_import(AGENTS_ROOT / "plugins")
    assert scan_qmb_imports(AGENTS_ROOT / "plugins") == ()


def test_procedure_successor_usage_example() -> None:
    namespace = runpy.run_path(str(EXAMPLE), run_name="__main__")
    assert callable(namespace["main"])
    namespace["main"]()
