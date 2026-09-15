"""L27 reference usage: config-changing door steps mint ExperimentSpec successors."""

from __future__ import annotations

from qma.core.content import content_address
from qma.core.control import (
    author_procedure,
    procedure_mints_ct07_edge,
    procedure_successor_edge_type,
    procedure_uses_bot_supersedes,
)
from qma.core.ontology import ActorId, DeskSlug
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
from qma.daemon.taskgraph.records import DispatchLease
from qmf.core import is_ok, is_refusal
from qmf.registry import EdgeType


def _fp(label: str) -> str:
    addressed = content_address({"label": label})
    assert is_ok(addressed)
    return addressed.value.value


def main() -> None:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    owner = minted.value
    envs = ExecutionEnvironmentRegistry()
    assert is_ok(
        envs.register_declaration(
            ExecutionEnvironmentDeclaration.isolated(
                ExecutionEnvironmentKind.DOCKER,
                provider_ref="local-docker",
            )
        )
    )
    authored = author_procedure(analysis_procedure_graph_payload())
    assert is_ok(authored)
    assert authored.value.is_experiment_spec is False
    assert procedure_uses_bot_supersedes() is False
    assert procedure_mints_ct07_edge() is False
    assert procedure_successor_edge_type() == EXPERIMENT_LINEAGE_EDGE_TYPE
    assert is_ok(admit_coordinated_continuity(COORDINATED_CONTINUITY_KIND))

    lease = DispatchLease(
        task_id="task-37-3",
        holder_agent_id="agent-analyst-1",
        mission_id="mission-exp",
        owner=owner,
    )
    spec = ExperimentSpec.try_create(
        data_ref="data:eurusd",
        environment_ref="env:docker",
        seed=37,
        model_and_harness_version={"model": "analyst-v1", "harness": "qmb-1"},
        cost_assumptions={"spread_usd_cents": 10},
        resolved_config_ref=_fp("cfg-a"),
    )
    assert is_ok(spec)
    experiments = ExperimentSpecService()
    registered = experiments.register(
        spec.value,
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(registered)
    service = BacktestingService(
        jobs=JobHandleService(),
        environments=envs,
        transport=RecordingQmbDoorTransport(),
        experiments=experiments,
    )
    assert is_ok(service.install())

    query = service.place_procedure_step(
        "analysis.project",
        owner=owner,
        task_id="task-project",
        environment_ref="env:docker",
    )
    assert is_ok(query)
    assert query.value.occupancy == QMB_OCCUPANCY_QUERY
    assert query.value.mints_experiment_spec is False
    assert query.value.successor is None
    assert service.occupying_job("docker") is None

    changed = service.place_procedure_step(
        "optimize.run",
        owner=owner,
        task_id="task-opt",
        environment_ref="env:docker",
        experiment_spec_fp1=registered.value.spec.spec_fp1,
        evidence_ref="evidence:recorded-bars",
        resolved_config_ref=_fp("cfg-b"),
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(changed)
    assert changed.value.occupancy == QMB_OCCUPANCY_RUN
    assert changed.value.mints_experiment_spec is True
    assert changed.value.successor is not None
    assert changed.value.run is not None
    edge = changed.value.successor.lineage_edge
    assert edge is not None
    assert edge.edge_type is EdgeType.BRANCHES_FROM
    assert service.occupying_job("docker") == changed.value.run.handle.job_id
    assert is_refusal(
        service.place_procedure_step(
            "optimize.run",
            owner=owner,
            task_id="task-sup",
            environment_ref="env:docker",
            experiment_spec_fp1=registered.value.spec.spec_fp1,
            evidence_ref="evidence:recorded-bars",
            resolved_config_ref=_fp("cfg-c"),
            edge_type="supersedes",
            dispatch_lease=lease,
            model_deployment_ref="deploy:analyst-v1",
        )
    )


if __name__ == "__main__":
    main()
