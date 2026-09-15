"""L27 reference usage: procedure run-steps occupy; query-steps do not."""

from __future__ import annotations

from qma.core.content import content_address
from qma.core.control import (
    author_procedure,
    classify_procedure_step,
    is_query_step,
    is_run_step,
)
from qma.core.ontology import ActorId, DeskSlug
from qma.core.plugins import analysis_procedure_graph_payload
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.qmb import QMB_OCCUPANCY_QUERY, QMB_OCCUPANCY_RUN
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.daemon.backtest import BacktestingService, RecordingQmbDoorTransport
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.envs.jobs import JobHandleService
from qmf.core import is_ok, is_refusal


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
    addressed = content_address({"label": "proc-37-2"})
    assert is_ok(addressed)
    service = BacktestingService(
        jobs=JobHandleService(),
        environments=envs,
        transport=RecordingQmbDoorTransport(),
    )
    assert is_ok(service.install())
    authored = author_procedure(analysis_procedure_graph_payload())
    assert is_ok(authored)
    for node in authored.value.nodes:
        classified = classify_procedure_step(node)
        assert is_ok(classified)
        if classified.value.occupancy == QMB_OCCUPANCY_RUN:
            assert is_run_step(node)
        else:
            assert is_query_step(node)

    run = service.place_procedure_step(
        "backtest.run",
        owner=owner,
        task_id="task-run",
        environment_ref="env:docker",
        experiment_spec_fp1=addressed.value.value,
        evidence_ref="evidence:recorded-bars",
    )
    assert is_ok(run)
    assert run.value.occupancy == QMB_OCCUPANCY_RUN
    assert run.value.run is not None
    occupying = run.value.run.handle.job_id
    assert service.occupying_job("docker") == occupying

    blocked = service.place_procedure_step(
        "optimize.run",
        owner=owner,
        task_id="task-blocked",
        environment_ref="env:docker",
        experiment_spec_fp1=addressed.value.value,
        evidence_ref="evidence:recorded-bars",
    )
    assert is_refusal(blocked)

    query = service.place_procedure_step(
        "analysis.project",
        owner=owner,
        task_id="task-project",
        environment_ref="env:docker",
    )
    assert is_ok(query)
    assert query.value.occupancy == QMB_OCCUPANCY_QUERY
    assert query.value.mints_ct32 is False
    assert query.value.mints_experiment_spec is False
    assert service.occupying_job("docker") == occupying


if __name__ == "__main__":
    main()
