"""L27 reference usage: Quant Ledger, Experiment Ledger, and desk views."""

from __future__ import annotations

from qma.core.content import content_address
from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.ports.experiments import ExperimentSpec
from qma.core.ports.ledgers import QuantLedgerLease
from qma.daemon.experiments import ExperimentSpecService
from qma.daemon.ledgers import (
    DeskLedgerViews,
    ExperimentLedgerStore,
    QuantLedgerStore,
    TaskLedgerStore,
)
from qma.daemon.taskgraph.records import DispatchLease
from qmf.core import is_ok, is_refusal


def main() -> None:
    minted = ActorId.mint(DeskSlug.RESEARCH, "lead")
    assert is_ok(minted)
    owner = minted.value
    lead = Quant(
        actor_id=owner,
        desk=DeskSlug.RESEARCH,
        quant_slug="lead",
        role=RoleName.RESEARCHER,
        name="Quant lead",
        lead=True,
    )
    next_id = ActorId.mint(DeskSlug.RESEARCH, "next")
    assert is_ok(next_id)
    follower = Quant(
        actor_id=next_id.value,
        desk=DeskSlug.RESEARCH,
        quant_slug="next",
        role=RoleName.RESEARCHER,
        name="Quant next",
        lead=False,
    )

    quants = QuantLedgerStore()
    assert is_ok(quants.open_for_quant(lead))
    assert is_refusal(quants.open_for_quant(follower))
    qlease = QuantLedgerLease(owner=owner, holder_agent_id="agent-a")
    assert is_ok(quants.grant(qlease))
    assert is_ok(
        quants.append(
            {
                "kind": "mission_opened",
                "authored_by": {"agent": "agent-a", "quant": owner.value},
                "model_deployment_ref": "deploy:workhorse",
            },
            lease=qlease,
        )
    )
    moved = quants.move_lead_flag(current=lead, successor=follower)
    assert is_ok(moved)
    assert moved.value.successor_ledger_opened is False
    assert quants.get(owner) is not None
    assert quants.get(next_id.value) is None

    tasks = TaskLedgerStore()
    dispatch = DispatchLease(
        task_id="task-1",
        holder_agent_id="agent-a",
        mission_id="mission-1",
        owner=owner,
    )
    tasks.open_for_task("task-1", owner=owner)
    assert is_ok(tasks.grant(dispatch))
    assert is_ok(
        tasks.append(
            {
                "kind": "progress",
                "authored_by": {"agent": "agent-a", "quant": owner.value},
                "model_deployment_ref": "deploy:workhorse",
            },
            lease=dispatch,
        )
    )

    experiments = ExperimentLedgerStore()
    addressed = content_address({"label": "example-cfg"})
    assert is_ok(addressed)
    spec = ExperimentSpec.try_create(
        data_ref="data:eurusd",
        environment_ref="env:docker",
        seed=1,
        model_and_harness_version={"model": "v1", "harness": "qmb-1"},
        cost_assumptions={"spread_usd_cents": 10},
        resolved_config_ref=addressed.value.value,
    )
    assert is_ok(spec)
    service = ExperimentSpecService(ledgers=experiments)
    registered = service.register(
        spec.value,
        dispatch_lease=dispatch,
        model_deployment_ref="deploy:workhorse",
    )
    assert is_ok(registered)
    assert is_ok(
        service.append_evidence(
            spec_fp1=registered.value.spec.spec_fp1,
            dispatch_lease=dispatch,
            model_deployment_ref="deploy:workhorse",
            body={"note": "notebook"},
        )
    )
    assert is_refusal(
        service.append_evidence(
            spec_fp1=registered.value.spec.spec_fp1,
            dispatch_lease=DispatchLease(
                task_id="task-other",
                holder_agent_id="agent-b",
                mission_id="mission-1",
                owner=owner,
            ),
            model_deployment_ref="deploy:other",
            body={"note": "no"},
        )
    )

    views = DeskLedgerViews(
        task_ledgers=tasks,
        quant_ledgers=quants,
        experiment_ledgers=experiments,
    )
    views.remember_quant(lead)
    folded = views.derive(DeskSlug.RESEARCH)
    assert is_ok(folded)
    assert folded.value.is_store is False
    assert {row.store for row in folded.value.rows} == {
        "task_ledger",
        "quant_ledger",
        "experiment_ledger",
    }
    assert is_refusal(views.declare_store("research_ledger"))
    assert is_refusal(views.mission_report("mission-1"))


if __name__ == "__main__":
    main()
