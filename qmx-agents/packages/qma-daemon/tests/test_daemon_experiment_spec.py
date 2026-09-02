"""Story 45.7 — ExperimentSpec registration, ledger, and CT-07 lineage (FR-Q54)."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.content import content_address
from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.experiments import (
    EXPERIMENT_CHANGE_CODE,
    EXPERIMENT_CHANGE_RESOLVED_CONFIG,
    EXPERIMENT_LINEAGE_EDGE_TYPE,
    GIT_COMMIT_REF_PREFIX,
    ExperimentSpec,
)
from qma.daemon.experiments import ExperimentSpecService
from qma.daemon.ledgers import ExperimentLedger
from qma.daemon.taskgraph.records import DispatchLease
from qmf.core import is_ok, is_refusal
from qmf.registry import EdgeType

_COMMIT = GIT_COMMIT_REF_PREFIX + ("b" * 40)


def _fp(label: str) -> str:
    addressed = content_address({"label": label})
    assert is_ok(addressed)
    return addressed.value.value


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    return minted.value


def _lease(*, task_id: str = "task-exp-1", holder: str = "agent-analyst-1") -> DispatchLease:
    return DispatchLease(
        task_id=task_id,
        holder_agent_id=holder,
        mission_id="mission-exp",
        owner=_owner(),
    )


def _spec(*, config: str = "cfg-a", code_ref: str | None = None) -> ExperimentSpec:
    created = ExperimentSpec.try_create(
        data_ref="data:eurusd",
        environment_ref="env:docker",
        seed=11,
        model_and_harness_version={"model": "analyst-v1", "harness": "qmb-1"},
        cost_assumptions={"spread_usd_cents": 10},
        resolved_config_ref=_fp(config),
        code_ref=code_ref,
    )
    assert is_ok(created)
    return created.value


def test_register_resolves_ledger_authored_by_dispatch_lease_holder() -> None:
    service = ExperimentSpecService()
    lease = _lease()
    registered = service.register(
        _spec(),
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(registered)
    record = registered.value
    assert record.spec.experiment_ledger_ref == record.ledger.ledger_ref
    assert record.ledger.author_agent_id == "agent-analyst-1"
    assert record.ledger.registering_task_id == "task-exp-1"
    assert record.ledger.owner == lease.owner
    resolved = service.resolve_ledger(record.spec.spec_fp1)
    assert is_ok(resolved)
    assert resolved.value.ledger_ref == record.ledger.ledger_ref
    appended = service.append_evidence(
        spec_fp1=record.spec.spec_fp1,
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
        body={"note": "baseline recorded"},
    )
    assert is_ok(appended)
    assert appended.value.entries[0].authored_by == "agent-analyst-1"
    assert appended.value.entries[0].model_deployment_ref == "deploy:analyst-v1"


def test_equivalent_specs_deduplicate_and_keep_one_author() -> None:
    service = ExperimentSpecService()
    first = service.register(
        _spec(config="dup"),
        dispatch_lease=_lease(),
        model_deployment_ref="deploy:a",
    )
    assert is_ok(first)
    second = service.register(
        _spec(config="dup"),
        dispatch_lease=_lease(task_id="task-exp-2", holder="agent-other"),
        model_deployment_ref="deploy:b",
    )
    assert is_ok(second)
    assert second.value.spec.spec_fp1 == first.value.spec.spec_fp1
    assert second.value.ledger.author_agent_id == "agent-analyst-1"
    assert second.value.dispatch_lease.task_id == "task-exp-1"
    other_task = service.append_evidence(
        spec_fp1=first.value.spec.spec_fp1,
        dispatch_lease=_lease(task_id="task-exp-2", holder="agent-other"),
        model_deployment_ref="deploy:b",
        body={"note": "second author"},
    )
    assert is_refusal(other_task)
    assert other_task.context["field"] == "dispatch_lease"


def test_code_and_config_successors_write_append_only_ct07_edges() -> None:
    service = ExperimentSpecService()
    lease = _lease()
    base = service.register(
        _spec(),
        dispatch_lease=lease,
        model_deployment_ref="deploy:a",
    )
    assert is_ok(base)
    predecessor_payload = dict(base.value.spec.to_payload())
    code = service.create_successor(
        predecessor_fp1=base.value.spec.spec_fp1,
        change=EXPERIMENT_CHANGE_CODE,
        dispatch_lease=lease,
        model_deployment_ref="deploy:a",
        code_ref=_COMMIT,
    )
    assert is_ok(code)
    assert code.value.spec.code_ref == _COMMIT
    assert code.value.lineage_edge is not None
    assert code.value.lineage_edge.edge_type is EdgeType.BRANCHES_FROM
    assert code.value.lineage_edge.edge_type.value == EXPERIMENT_LINEAGE_EDGE_TYPE
    assert code.value.lineage_edge.from_ref.value == code.value.spec.spec_fp1
    assert code.value.lineage_edge.to_ref.value == base.value.spec.spec_fp1
    config = service.create_successor(
        predecessor_fp1=base.value.spec.spec_fp1,
        change=EXPERIMENT_CHANGE_RESOLVED_CONFIG,
        dispatch_lease=lease,
        model_deployment_ref="deploy:a",
        resolved_config_ref=_fp("cfg-sweep"),
    )
    assert is_ok(config)
    assert config.value.spec.code_ref is None
    assert config.value.lineage_edge is not None
    assert config.value.lineage_edge.edge_type is EdgeType.BRANCHES_FROM
    still = service.resolve(base.value.spec.spec_fp1)
    assert is_ok(still)
    assert dict(still.value.spec.to_payload()) == predecessor_payload
    edges = service.lineage_edges(base.value.spec.spec_fp1)
    assert len(edges) == 2
    assert {edge.from_ref.value for edge in edges} == {
        code.value.spec.spec_fp1,
        config.value.spec.spec_fp1,
    }


def test_in_place_mutation_and_branch_per_parameter_are_refused() -> None:
    service = ExperimentSpecService()
    registered = service.register(
        _spec(),
        dispatch_lease=_lease(),
        model_deployment_ref="deploy:a",
    )
    assert is_ok(registered)
    mutated = service.mutate_in_place(
        registered.value.spec.spec_fp1,
        seed=99,
    )
    assert is_refusal(mutated)
    branch = service.create_successor(
        predecessor_fp1=registered.value.spec.spec_fp1,
        change=EXPERIMENT_CHANGE_RESOLVED_CONFIG,
        dispatch_lease=_lease(),
        model_deployment_ref="deploy:a",
        resolved_config_ref="git:branch:params",
    )
    assert is_refusal(branch)
    missing_ledger = service.resolve_ledger("fp1:sha256:" + ("c" * 64))
    assert is_refusal(missing_ledger)


def test_gap_0085_remains_excluded_on_daemon_successor() -> None:
    service = ExperimentSpecService()
    registered = service.register(
        _spec(),
        dispatch_lease=_lease(),
        model_deployment_ref="deploy:a",
    )
    assert is_ok(registered)
    refused = service.create_successor(
        predecessor_fp1=registered.value.spec.spec_fp1,
        change=EXPERIMENT_CHANGE_RESOLVED_CONFIG,
        dispatch_lease=_lease(),
        model_deployment_ref="deploy:a",
        resolved_config_ref=_fp("cfg-gap"),
        extra={"Filter": {"name": "session"}},
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "mechanisms"


def test_experiment_ledger_type_is_exported() -> None:
    assert ExperimentLedger.__name__ == "ExperimentLedger"


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "experiment_spec_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
