"""L27 reference usage: content-addressed ExperimentSpec and CT-07 lineage."""

from __future__ import annotations

import tempfile
from pathlib import Path

from qma.core.content import content_address
from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.experiments import (
    COORDINATED_CONTINUITY_KIND,
    EXPERIMENT_CHANGE_CODE,
    EXPERIMENT_CHANGE_RESOLVED_CONFIG,
    GIT_COMMIT_REF_PREFIX,
    ExperimentSpec,
)
from qma.daemon.experiments import ExperimentSpecService
from qma.daemon.process import DaemonProcess
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
    assert is_refusal(service.register_project())
    assert is_refusal(service.copy_qmb_jsonl())
    assert is_ok(service.admit_continuity(COORDINATED_CONTINUITY_KIND))
    _restart_restores_sqlite(first.value.spec.spec_fp1, lease, spec.value)


def _restart_restores_sqlite(
    spec_fp1: str,
    lease: DispatchLease,
    spec: ExperimentSpec,
) -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        first = DaemonProcess.compose(
            root,
            machine="example-host",
            boot_epoch_id="boot-example-36-3-a",
            bind_port=0,
        )
        assert is_ok(first)
        process = first.value
        try:
            registered = process.experiments.register(
                spec,
                dispatch_lease=lease,
                model_deployment_ref="deploy:analyst-v1",
            )
            assert is_ok(registered)
            evidence = process.experiments.append_evidence(
                spec_fp1=registered.value.spec.spec_fp1,
                dispatch_lease=lease,
                model_deployment_ref="deploy:analyst-v1",
                body={"ct32_ref": "fp1:sha256:" + ("a" * 64), "note": "refs only"},
            )
            assert is_ok(evidence)
        finally:
            process.close()
        restarted = DaemonProcess.compose(
            root,
            machine="example-host",
            boot_epoch_id="boot-example-36-3-b",
            bind_port=0,
        )
        assert is_ok(restarted)
        restored_process = restarted.value
        try:
            restored = restored_process.experiments.resolve(spec_fp1)
            assert is_ok(restored)
            ct32_ref = restored.value.ledger.entries[0].body["ct32_ref"]
            assert isinstance(ct32_ref, str) and ct32_ref.startswith("fp1:")
            assert restored_process.experiments.product_truth == "sqlite"
        finally:
            restored_process.close()


if __name__ == "__main__":
    main()
