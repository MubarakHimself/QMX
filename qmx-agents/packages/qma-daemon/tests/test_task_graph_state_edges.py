"""Story 57.1 — persist task_graph_state edges in daemon sqlite."""

from __future__ import annotations

import ast
import runpy
from pathlib import Path
from typing import cast

from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.qmb import QMB_OCCUPANCY_QUERY, QMB_OCCUPANCY_RUN, qmb_opens_daemon_sqlite
from qma.core.vocabulary.enums import EdgeMapping, ExecutionEnvironmentKind, NodeKind
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.envs.registry import EnvironmentLease
from qma.daemon.plugins import research_corpus_plugin_load_config
from qma.daemon.process import DaemonProcess
from qma.daemon.scheduler import PROCEDURE_RUNTIME, SECOND_SCHEDULER_MINTED, RoutineScheduler
from qma.daemon.taskgraph import (
    DURABLE_EDGES_EXISTED_AT_INSPECT_SHA,
    NODE_SUCCESSOR_KEYS,
    OCCUPANCY_TABLE_MINTED,
    TASK_GRAPH_STATE_EDGE_TABLE,
    TASK_GRAPH_STATE_SQLITE_TABLES,
    TASK_GRAPH_STATE_STORE,
    TASK_GRAPH_STATE_TABLE,
    CompileRequest,
    CompileResult,
    GraphTemplate,
    GraphTemplateCatalog,
    MissionCompiler,
    TaskGraphDispatcher,
    TaskGraphStateService,
    claim_durable_edges_at_inspect_sha,
    refuse_qmb_occupancy_write,
    refuse_second_scheduler,
)
from qmf.core import is_ok, is_refusal

_SRC = Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "taskgraph"
_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "task_graph_state_usage.py"


def _quant(*, slug: str = "alpha", desk: DeskSlug = DeskSlug.RESEARCH) -> Quant:
    minted = ActorId.mint(desk, slug)
    assert is_ok(minted)
    return Quant(
        actor_id=minted.value,
        desk=desk,
        quant_slug=slug,
        role=RoleName.RESEARCHER,
        name=f"Quant {slug}",
    )


def _edge(
    src: str,
    dst: str,
    *,
    mapping: str = "one",
) -> dict[str, object]:
    return {
        "from": src,
        "to": dst,
        "mapping": mapping,
        "from_port": "data",
        "to_port": "data",
    }


def _template() -> GraphTemplate:
    return GraphTemplate(
        qualified_id="research-corpus:two-step",
        version="1",
        nodes=(
            {"id": "prepare", "kind": "task", "intent": "prepare corpus"},
            {"id": "survey", "kind": "task", "intent": "survey coverage"},
        ),
        edges=(_edge("prepare", "survey", mapping="one"),),
    )


def _compile() -> tuple[Quant, CompileResult]:
    owner = _quant()
    catalog = GraphTemplateCatalog()
    registered = catalog.register(_template())
    assert is_ok(registered)
    compiler = MissionCompiler(
        templates=catalog,
        known_quant_actor_ids={owner.actor_id.value},
    )
    compiled = compiler.compile(
        CompileRequest(
            goal=Goal(text="survey after prepare"),
            owner=owner,
            graph_template_ref="research-corpus:two-step",
            intent="survey after prepare",
        )
    )
    assert is_ok(compiled)
    return owner, compiled.value


def _compose(tmp_path: Path, *, boot: str) -> DaemonProcess:
    seed = tmp_path / "seed-corpus"
    seed.mkdir(exist_ok=True)
    result = DaemonProcess.compose(
        tmp_path,
        machine="test-host",
        boot_epoch_id=boot,
        bind_port=0,
        plugin_load_configs=research_corpus_plugin_load_config(seed),
    )
    assert is_ok(result), result
    return result.value


def test_claiming_durable_edges_existed_at_270e992_fails() -> None:
    assert DURABLE_EDGES_EXISTED_AT_INSPECT_SHA is False
    refused = claim_durable_edges_at_inspect_sha(True)
    assert is_refusal(refused)
    assert refused.context["existed_at_inspect_sha"] is False
    ok = claim_durable_edges_at_inspect_sha(False)
    assert is_ok(ok)
    assert ok.value is False


def test_compile_persists_edges_on_task_graph_not_node_lists() -> None:
    _owner, compiled = _compile()
    graph = compiled.task_graph
    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.from_node == "prepare"
    assert edge.to_node == "survey"
    assert edge.mapping is EdgeMapping.ONE
    payload = dict(graph.to_payload())
    edges = cast("list[object]", payload["edges"])
    assert edges == [{"from": "prepare", "to": "survey", "mapping": "one"}]
    for node in graph.nodes:
        assert not NODE_SUCCESSOR_KEYS.intersection(node.config)
        node_payload = dict(node.to_payload())
        assert "successors" not in node_payload
    assert graph.successor_ids("prepare") == ("survey",)
    assert graph.outgoing_edges("prepare")[0].mapping is EdgeMapping.ONE


def test_durable_edges_survive_daemon_restart(tmp_path: Path) -> None:
    _owner, compiled = _compile()
    graph = compiled.task_graph
    process = _compose(tmp_path, boot="boot-57-1-a")
    try:
        assert process.task_graphs.product_truth == "sqlite"
        assert process.sqlite_table_names() >= TASK_GRAPH_STATE_SQLITE_TABLES
        persisted = process.task_graphs.persist(graph)
        assert is_ok(persisted)
        rows = process.sqlite.execute(
            "SELECT from_node, to_node, mapping FROM task_graph_state_edge "
            "WHERE graph_id = ?",
            (graph.id,),
        )
        assert rows == [("prepare", "survey", "one")]
        occupancy_tables = {
            name
            for name in process.sqlite_table_names()
            if "occupancy" in name
        }
        assert occupancy_tables == set()
        assert process.task_graphs.occupancy_table_present() is False
        snap = process.snapshot()
        assert snap["occupancy_table_minted"] is False
        assert snap["second_scheduler_minted"] is False
        tables = snap["task_graph_state_tables"]
        assert isinstance(tables, list)
        assert set(cast("list[str]", tables)) == set(TASK_GRAPH_STATE_SQLITE_TABLES)
    finally:
        process.close()

    restarted = _compose(tmp_path, boot="boot-57-1-b")
    try:
        restored = restarted.task_graphs.get(graph.id)
        assert is_ok(restored)
        walked = restored.value
        assert walked.id == graph.id
        assert [(e.from_node, e.to_node, e.mapping.value) for e in walked.edges] == [
            ("prepare", "survey", "one")
        ]
        assert walked.successor_ids("prepare") == ("survey",)
        for node in walked.nodes:
            assert "successors" not in node.to_payload()
        edge_rows = restarted.sqlite.execute(
            "SELECT from_node, to_node, mapping FROM task_graph_state_edge "
            "WHERE graph_id = ?",
            (graph.id,),
        )
        assert edge_rows == [("prepare", "survey", "one")]
        named = restarted.task_graphs.store
        assert named == TASK_GRAPH_STATE_STORE
        assert TASK_GRAPH_STATE_TABLE in restarted.sqlite_table_names()
        assert TASK_GRAPH_STATE_EDGE_TABLE in restarted.sqlite_table_names()
    finally:
        restarted.close()


def test_in_memory_cache_is_not_product_truth(tmp_path: Path) -> None:
    _owner, compiled = _compile()
    process = _compose(tmp_path, boot="boot-57-1-cache")
    try:
        persisted = process.task_graphs.persist(compiled.task_graph)
        assert is_ok(persisted)
        graph_id = compiled.task_graph.id
        process.task_graphs.drop_memory_cache()
        restored = process.task_graphs.get(graph_id)
        assert is_ok(restored)
        assert restored.value.successor_ids("prepare") == ("survey",)
    finally:
        process.close()


def test_occupancy_is_lease_plus_door_law_not_a_table(tmp_path: Path) -> None:
    _owner, compiled = _compile()
    graph = compiled.task_graph
    process = _compose(tmp_path, boot="boot-57-1-occ")
    try:
        lease = EnvironmentLease(
            task_id=graph.tasks[0].id,
            kind="docker",
            slot_id="slot-1",
            provider_id="local-docker",
        )
        occupied = process.task_graphs.occupy_run_step(graph, lease)
        assert is_ok(occupied)
        occupancy = dict(process.task_graphs.occupancy_for(graph.id))
        assert occupancy["law"] == "environment_lease+workbench_ad8"
        assert occupancy["separate_table"] is False
        assert occupancy["qmb_writes"] is False
        slots = cast("dict[str, object]", occupancy["slots"])
        slot = cast("dict[str, object]", slots[graph.tasks[0].id])
        assert slot["door"] == QMB_OCCUPANCY_RUN
        assert slot["consumes_environment"] is True
        env = cast("dict[str, object]", slot["environment_lease"])
        assert env["lease"] == "environment_lease"
        assert OCCUPANCY_TABLE_MINTED is False
        assert process.task_graphs.occupancy_table_present() is False
        qmb_write = process.task_graphs.write_qmb_occupancy(task_id=graph.tasks[0].id)
        assert is_refusal(qmb_write)
        assert qmb_write.context["qmb_writes"] is False
        assert qmb_opens_daemon_sqlite() is False
        query_lease = EnvironmentLease(
            task_id=graph.tasks[1].id,
            kind="docker",
            slot_id="slot-2",
            provider_id="local-docker",
        )
        queried = process.task_graphs.occupy_run_step(
            occupied.value,
            query_lease,
            door=QMB_OCCUPANCY_QUERY,
        )
        assert is_ok(queried)
        occupancy_after = dict(process.task_graphs.occupancy_for(graph.id))
        slots_after = cast("dict[str, object]", occupancy_after["slots"])
        query_slot = cast("dict[str, object]", slots_after[graph.tasks[1].id])
        assert query_slot["door"] == QMB_OCCUPANCY_QUERY
        assert "environment_lease" not in query_slot
    finally:
        process.close()


def test_second_scheduler_is_refused() -> None:
    assert SECOND_SCHEDULER_MINTED is False
    assert PROCEDURE_RUNTIME == ("RoutineScheduler", "MissionCompiler")
    refused = refuse_second_scheduler(given="WorkflowScheduler")
    assert is_refusal(refused)
    assert refused.context["minted"] is False
    runtime = refused.context["runtime"]
    assert isinstance(runtime, (list, tuple))
    assert list(cast("list[str] | tuple[str, ...]", runtime)) == [
        "RoutineScheduler",
        "MissionCompiler",
    ]
    service = TaskGraphStateService()
    minted = service.mint_second_scheduler("WorkflowScheduler")
    assert is_refusal(minted)
    assert RoutineScheduler.__name__ == "RoutineScheduler"
    assert MissionCompiler.__name__ == "MissionCompiler"


def test_dispatcher_materialize_writes_sqlite_when_bound(tmp_path: Path) -> None:
    owner, compiled = _compile()
    process = _compose(tmp_path, boot="boot-57-1-disp")
    try:
        envs = ExecutionEnvironmentRegistry()
        assert is_ok(
            envs.register_declaration(
                ExecutionEnvironmentDeclaration.isolated(
                    ExecutionEnvironmentKind.DOCKER,
                    provider_ref="local-docker",
                )
            )
        )
        dispatcher = TaskGraphDispatcher(environments=envs, durable=process.task_graphs)
        dispatcher.materialize(compiled.task_graph, mission=compiled.mission)
        ready = compiled.task_graph.ready_tasks()[0]
        decision = dispatcher.dispatch_task(
            task_id=ready.id,
            holder_agent_id="agent-worker-1",
            environment_kind=ExecutionEnvironmentKind.DOCKER,
        )
        assert is_ok(decision)
        assert decision.value.environment_lease is not None
        occupancy = dict(process.task_graphs.occupancy_for(compiled.task_graph.id))
        slots = cast("dict[str, object]", occupancy["slots"])
        assert ready.id in slots
        process.task_graphs.drop_memory_cache()
        restored = process.task_graphs.get(compiled.task_graph.id)
        assert is_ok(restored)
        assert restored.value.successor_ids("prepare") == ("survey",)
        _ = owner
    finally:
        process.close()


def test_refuse_qmb_occupancy_write_helper() -> None:
    refused = refuse_qmb_occupancy_write()
    assert is_refusal(refused)
    assert refused.context["qmb_opens_daemon_sqlite"] is False
    assert refused.context["separate_table"] is False


def test_nodes_refuse_successor_lists() -> None:
    catalog = GraphTemplateCatalog()
    template = GraphTemplate(
        qualified_id="research-corpus:listed",
        version="1",
        nodes=(
            {
                "id": "a",
                "kind": "task",
                "successors": ["b"],
                "intent": "a",
            },
            {"id": "b", "kind": "task", "intent": "b"},
        ),
        edges=(_edge("a", "b"),),
    )
    registered = catalog.register(template)
    assert is_ok(registered)
    owner = _quant(slug="listed")
    compiler = MissionCompiler(
        templates=catalog,
        known_quant_actor_ids={owner.actor_id.value},
    )
    compiled = compiler.compile(
        CompileRequest(
            goal=Goal(text="listed successors"),
            owner=owner,
            graph_template_ref="research-corpus:listed",
        )
    )
    assert is_refusal(compiled)


def test_example_and_source_keep_named_projection() -> None:
    tree = ast.parse((_SRC / "projection.py").read_text(encoding="utf-8"))
    assigned: dict[str, object] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        ):
            if isinstance(node.value, (ast.Constant, ast.Tuple, ast.List)):
                assigned[node.target.id] = ast.literal_eval(node.value)
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, (ast.Constant, ast.Tuple, ast.List))
        ):
            assigned[node.targets[0].id] = ast.literal_eval(node.value)
    assert assigned.get("TASK_GRAPH_STATE_STORE") == "task_graph_state"
    assert assigned.get("DURABLE_EDGES_EXISTED_AT_INSPECT_SHA") is False
    assert assigned.get("OCCUPANCY_TABLE_MINTED") is False
    assert assigned.get("SECOND_SCHEDULER_MINTED") is False
    assert assigned.get("QMB_WRITES_DAEMON_OCCUPANCY") is False
    namespace = runpy.run_path(str(_EXAMPLE))
    assert callable(namespace["main"])
    namespace["main"]()


def test_zip_mapping_is_preserved(tmp_path: Path) -> None:
    owner = _quant(slug="zip")
    catalog = GraphTemplateCatalog()
    template = GraphTemplate(
        qualified_id="research-corpus:zip",
        version="1",
        nodes=(
            {"id": "left", "kind": "task", "intent": "left"},
            {"id": "right", "kind": "task", "intent": "right"},
        ),
        edges=(_edge("left", "right", mapping="zip"),),
    )
    assert is_ok(catalog.register(template))
    compiler = MissionCompiler(
        templates=catalog,
        known_quant_actor_ids={owner.actor_id.value},
    )
    compiled = compiler.compile(
        CompileRequest(
            goal=Goal(text="zip mapping"),
            owner=owner,
            graph_template_ref="research-corpus:zip",
        )
    )
    assert is_ok(compiled)
    assert compiled.value.task_graph.edges[0].mapping is EdgeMapping.ZIP
    process = _compose(tmp_path, boot="boot-57-1-zip")
    try:
        persisted = process.task_graphs.persist(compiled.value.task_graph)
        assert is_ok(persisted)
    finally:
        process.close()
    restarted = _compose(tmp_path, boot="boot-57-1-zip-b")
    try:
        restored = restarted.task_graphs.get(compiled.value.task_graph.id)
        assert is_ok(restored)
        assert restored.value.edges[0].mapping is EdgeMapping.ZIP
        _ = NodeKind.TASK
    finally:
        restarted.close()
