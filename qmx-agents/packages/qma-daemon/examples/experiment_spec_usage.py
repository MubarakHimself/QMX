"""L27 reference usage: content-addressed ExperimentSpec and CT-07 lineage."""

from __future__ import annotations

from qma.core.content import content_address
from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.experiments import (
    EXPERIMENT_CHANGE_CODE,
    EXPERIMENT_CHANGE_RESOLVED_CONFIG,
    GIT_COMMIT_REF_PREFIX,
    ExperimentSpec,
)
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
    lease = DispatchLease(
        task_id="task-exp-1",
        holder_agent_id="agent-analyst-1",
        mission_id="mission-exp",
        owner=minted.value,
    )
    spec = ExperimentSpec.try_create(
        data_ref="data:eurusd",
        environment_ref="env:docker",
        seed=3,
        model_and_harness_version={"model": "analyst-v1", "harness": "qmb-1"},
        cost_assumptions={"spread_usd_cents": 10},
        resolved_config_ref=_fp("cfg-a"),
    )
    assert is_ok(spec)
    service = ExperimentSpecService()
    first = service.register(
        spec.value,
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(first)
    again = service.register(
        spec.value,
        dispatch_lease=DispatchLease(
            task_id="task-exp-2",
            holder_agent_id="agent-other",
            mission_id="mission-exp",
            owner=minted.value,
        ),
        model_deployment_ref="deploy:other",
    )
    assert is_ok(again)
    assert again.value.spec.spec_fp1 == first.value.spec.spec_fp1
    code = service.create_successor(
        predecessor_fp1=first.value.spec.spec_fp1,
        change=EXPERIMENT_CHANGE_CODE,
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
        code_ref=GIT_COMMIT_REF_PREFIX + ("d" * 40),
    )
    assert is_ok(code)
    assert code.value.lineage_edge is not None
    assert code.value.lineage_edge.edge_type is EdgeType.BRANCHES_FROM
    config = service.create_successor(
        predecessor_fp1=first.value.spec.spec_fp1,
        change=EXPERIMENT_CHANGE_RESOLVED_CONFIG,
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
        resolved_config_ref=_fp("cfg-b"),
    )
    assert is_ok(config)
    assert config.value.spec.code_ref is None
    assert is_refusal(service.mutate_in_place(first.value.spec.spec_fp1, seed=9))
    ledger = service.append_evidence(
        spec_fp1=first.value.spec.spec_fp1,
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
        body={"note": "recorded"},
    )
    assert is_ok(ledger)
    assert ledger.value.entries[0].authored_by == "agent-analyst-1"


if __name__ == "__main__":
    main()
