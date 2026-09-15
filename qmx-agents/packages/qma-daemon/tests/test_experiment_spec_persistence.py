"""Story 36.3 — ExperimentSpec, ledger, and CT-07 edges persist through sqlite."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from qma.core.content import content_address
from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.experiments import (
    COORDINATED_CONTINUITY_KIND,
    EXPERIMENT_CHANGE_RESOLVED_CONFIG,
    EXPERIMENT_LINEAGE_EDGE_TYPE,
    GIT_COMMIT_REF_PREFIX,
    ExperimentSpec,
)
from qma.daemon.experiments import (
    EXPERIMENT_LEDGER_ENTRY_TABLE,
    EXPERIMENT_LEDGER_TABLE,
    EXPERIMENT_LINEAGE_EDGE_TABLE,
    EXPERIMENT_SPEC_TABLE,
    EXPERIMENT_SQLITE_TABLES,
    ExperimentSpecService,
)
from qma.daemon.process import DaemonProcess
from qma.daemon.taskgraph.records import DispatchLease
from qmf.core import is_ok, is_refusal
from qmf.registry import EdgeType

_COMMIT = GIT_COMMIT_REF_PREFIX + ("e" * 40)


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


def _spec(*, config: str = "cfg-persist") -> ExperimentSpec:
    created = ExperimentSpec.try_create(
        data_ref="data:eurusd",
        environment_ref="env:docker",
        seed=11,
        model_and_harness_version={"model": "analyst-v1", "harness": "qmb-1"},
        cost_assumptions={"spread_usd_cents": 10},
        resolved_config_ref=_fp(config),
    )
    assert is_ok(created)
    return created.value


def _compose(tmp_path: Path, *, boot: str) -> DaemonProcess:
    result = DaemonProcess.compose(
        tmp_path,
        machine="test-host",
        boot_epoch_id=boot,
        bind_port=0,
    )
    assert is_ok(result), result
    return result.value


def test_daemon_restart_restores_spec_ledger_and_successor_edges(tmp_path: Path) -> None:
    process = _compose(tmp_path, boot="boot-36-3-a")
    try:
        assert process.experiments.product_truth == "sqlite"
        assert process.sqlite_table_names() >= EXPERIMENT_SQLITE_TABLES
        assert process.qmb_jsonl_tables_present() == frozenset()
        lease = _lease()
        registered = process.experiments.register(
            _spec(),
            dispatch_lease=lease,
            model_deployment_ref="deploy:analyst-v1",
        )
        assert is_ok(registered)
        base_fp1 = registered.value.spec.spec_fp1
        successor = process.experiments.create_successor(
            predecessor_fp1=base_fp1,
            change=EXPERIMENT_CHANGE_RESOLVED_CONFIG,
            dispatch_lease=lease,
            model_deployment_ref="deploy:analyst-v1",
            resolved_config_ref=_fp("cfg-sweep"),
        )
        assert is_ok(successor)
        succ_fp1 = successor.value.spec.spec_fp1
        assert successor.value.spec.code_ref is None
        assert successor.value.lineage_edge is not None
        assert successor.value.lineage_edge.edge_type is EdgeType.BRANCHES_FROM
        evidence = process.experiments.append_evidence(
            spec_fp1=base_fp1,
            dispatch_lease=lease,
            model_deployment_ref="deploy:analyst-v1",
            body={
                "ct32_ref": _fp("ct32-run"),
                "qmb_ledger_ref": "qmb-ledger:run-1",
                "note": "coordinated refs only",
            },
        )
        assert is_ok(evidence)
        assert evidence.value.entries[0].body["ct32_ref"] == _fp("ct32-run")
        events = process.journal.read_all()
        assert is_ok(events)
        names = [row["event"] for row in events.value]
        assert "experiment.registered" in names
        assert "experiment.branched" in names
        assert "ledger.appended" in names
    finally:
        process.close()

    restarted = _compose(tmp_path, boot="boot-36-3-b")
    try:
        assert restarted.experiments.product_truth == "sqlite"
        restored = restarted.experiments.resolve(base_fp1)
        assert is_ok(restored)
        assert restored.value.spec.spec_fp1 == base_fp1
        assert restored.value.ledger.author_agent_id == "agent-analyst-1"
        assert restored.value.ledger.entries[0].body["qmb_ledger_ref"] == "qmb-ledger:run-1"
        assert "jsonl" not in restored.value.ledger.entries[0].body
        assert "ct32" not in restored.value.ledger.entries[0].body
        succ = restarted.experiments.resolve(succ_fp1)
        assert is_ok(succ)
        assert succ.value.spec.resolved_config_ref == _fp("cfg-sweep")
        assert succ.value.lineage_edge is not None
        assert succ.value.lineage_edge.edge_type.value == EXPERIMENT_LINEAGE_EDGE_TYPE
        assert succ.value.lineage_edge.from_ref.value == succ_fp1
        assert succ.value.lineage_edge.to_ref.value == base_fp1
        edges = restarted.experiments.lineage_edges(base_fp1)
        assert len(edges) == 1
        assert edges[0].from_ref.value == succ_fp1
        snap = restarted.snapshot()
        assert snap["experiment_product_truth"] == "sqlite"
        tables = snap["experiment_sqlite_tables"]
        assert isinstance(tables, list)
        named = [str(item) for item in cast("list[object]", tables)]
        assert set(named) == set(EXPERIMENT_SQLITE_TABLES)
        assert snap["qmb_jsonl_tables"] == []
    finally:
        restarted.close()


def test_in_memory_maps_are_not_product_truth(tmp_path: Path) -> None:
    process = _compose(tmp_path, boot="boot-36-3-cache")
    try:
        registered = process.experiments.register(
            _spec(config="cache"),
            dispatch_lease=_lease(),
            model_deployment_ref="deploy:a",
        )
        assert is_ok(registered)
        spec_fp1 = registered.value.spec.spec_fp1
        process.experiments.drop_memory_cache()
        missing = process.experiments.resolve(spec_fp1)
        assert is_refusal(missing)
        reloaded = process.experiments.reload()
        assert is_ok(reloaded)
        restored = process.experiments.resolve(spec_fp1)
        assert is_ok(restored)
        assert restored.value.spec.spec_fp1 == spec_fp1
    finally:
        process.close()


def test_qma_stores_refs_only_and_qmb_does_not_write_edges(tmp_path: Path) -> None:
    process = _compose(tmp_path, boot="boot-36-3-refs")
    try:
        service = process.experiments
        lease = _lease()
        registered = service.register(
            _spec(config="refs"),
            dispatch_lease=lease,
            model_deployment_ref="deploy:a",
        )
        assert is_ok(registered)
        copied = service.append_evidence(
            spec_fp1=registered.value.spec.spec_fp1,
            dispatch_lease=lease,
            model_deployment_ref="deploy:a",
            body={"ct32": {"copied": True}},
        )
        assert is_refusal(copied)
        assert copied.context["field"] == "body"
        jsonl = service.copy_qmb_jsonl('{"event":1}\n')
        assert is_refusal(jsonl)
        merged = service.merge_ct32({"result": {}})
        assert is_refusal(merged)
        qmb_edge = service.create_successor(
            predecessor_fp1=registered.value.spec.spec_fp1,
            change=EXPERIMENT_CHANGE_RESOLVED_CONFIG,
            dispatch_lease=lease,
            model_deployment_ref="deploy:a",
            resolved_config_ref=_fp("from-qmb"),
            source="qmb",
        )
        assert is_refusal(qmb_edge)
        assert qmb_edge.context["field"] == "qmb_lineage"
        assert is_refusal(service.write_edges_from_qmb())
        assert EXPERIMENT_SPEC_TABLE in process.sqlite_table_names()
        assert EXPERIMENT_LEDGER_TABLE in process.sqlite_table_names()
        assert EXPERIMENT_LEDGER_ENTRY_TABLE in process.sqlite_table_names()
        assert EXPERIMENT_LINEAGE_EDGE_TABLE in process.sqlite_table_names()
    finally:
        process.close()


def test_project_workspace_and_git_branch_parameter_are_refused(tmp_path: Path) -> None:
    process = _compose(tmp_path, boot="boot-36-3-identity")
    try:
        service = process.experiments
        project = service.register_project()
        assert is_refusal(project)
        assert project.context["field"] == "continuity"
        workspace = service.register_workspace()
        assert is_refusal(workspace)
        admitted = service.admit_continuity(COORDINATED_CONTINUITY_KIND)
        assert is_ok(admitted)
        lease = _lease()
        registered = service.register(
            _spec(config="identity"),
            dispatch_lease=lease,
            model_deployment_ref="deploy:a",
            continuity_kind="workspace",
        )
        assert is_refusal(registered)
        ok = service.register(
            _spec(config="identity"),
            dispatch_lease=lease,
            model_deployment_ref="deploy:a",
        )
        assert is_ok(ok)
        branch = service.create_successor(
            predecessor_fp1=ok.value.spec.spec_fp1,
            change=EXPERIMENT_CHANGE_RESOLVED_CONFIG,
            dispatch_lease=lease,
            model_deployment_ref="deploy:a",
            resolved_config_ref="git:branch:params",
        )
        assert is_refusal(branch)
        memory_only = ExperimentSpecService()
        assert memory_only.product_truth == "memory"
    finally:
        process.close()
