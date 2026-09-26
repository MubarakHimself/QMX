"""Story 63.2 — include-at-author versions; live merge and over-budget depth refuse."""

from __future__ import annotations

from pathlib import Path

from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.operations import public_operation_descriptors
from qma.daemon.journal.variables import (
    HOST_NESTED_MISSION_CALL_DEPTH_CEILING_KEY,
    HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY,
    HOST_RETRY_ATTEMPT_CEILING_KEY,
    HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY,
    GovernedVariableRegistry,
)
from qma.daemon.taskgraph import (
    CALL_DEPTH_REUSES_RETRY_REGISTRY_ROW,
    GAP_0108_IS_RETRY_ATTEMPT_CEILING,
    INCLUDE_AT_AUTHOR_IMPLEMENTED,
    NESTED_MISSION_CALLEE_OP_ID,
    RECURSION_CEILING_ROW_IMPLEMENTED,
    CompileRequest,
    GraphTemplate,
    NestedMissionHost,
    bind_call_depth_ceiling_key,
    include_subgraph_at_author,
)
from qma.wire import compute_input_hash
from qmf.core import RefusalCategory, is_ok, is_refusal
from qmf.core.refusal import Result

_INPUT = {"procedure_id": "research-corpus:b"}


def _ok[T](result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _quant() -> Quant:
    minted = ActorId.mint(DeskSlug.RESEARCH, "alpha")
    assert is_ok(minted)
    return Quant(
        actor_id=minted.value,
        desk=DeskSlug.RESEARCH,
        quant_slug="alpha",
        role=RoleName.RESEARCHER,
        name="Quant alpha",
    )


def _descriptor():
    for item in public_operation_descriptors():
        if item.op_id == NESTED_MISSION_CALLEE_OP_ID and item.version == 1:
            return item
    raise AssertionError("qma.procedure.start v1 missing")


def _hash() -> str:
    hashed = compute_input_hash(_INPUT, descriptor=_descriptor())
    assert is_ok(hashed)
    return hashed.value


def _template_a() -> GraphTemplate:
    return GraphTemplate(
        qualified_id="research-corpus:a",
        version="1.0.0",
        nodes=(
            {
                "id": "start-b",
                "kind": "task",
                "intent": "start nested B",
                "starts": {"qualified_id": "research-corpus:b", "version": "1.0.0"},
            },
        ),
        edges=(),
    )


def _template_b() -> GraphTemplate:
    return GraphTemplate(
        qualified_id="research-corpus:b",
        version="1.0.0",
        nodes=({"id": "work-b", "kind": "task", "intent": "do B work"},),
        edges=(),
    )


def _envelope(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "logical_invocation_id": "inv:nested-1",
        "attempt_id": 1,
        "op_id": NESTED_MISSION_CALLEE_OP_ID,
        "op_version": 1,
        "contribution": {
            "qualified_id": "research-corpus:b",
            "package_version": "1.0.0",
        },
        "instance_id": "inst:1",
        "config_revision": 4,
        "grant_id": "grant:b",
        "effect_class": "place-run",
        "idempotency_key": "idem:nested-1",
        "reconcile_policy": "query-then-decide",
        "input_hash": _hash(),
        "call_depth": 1,
        "caller_kind": "workflow",
        "parent_logical_invocation_id": "inv:parent-a",
    }
    payload.update(overrides)
    return payload


def test_include_at_author_writes_a_new_versioned_graph_template() -> None:
    assert INCLUDE_AT_AUTHOR_IMPLEMENTED is True
    host = NestedMissionHost()
    original_a = _template_a()
    original_b = _template_b()
    _ok(host.register_template(original_a))
    _ok(host.register_template(original_b))
    parent = _ok(
        host.compile_parent(
            owner=_quant(),
            template=original_a,
            goal="run A then nested B",
        )
    )
    live_nodes = {node.id for node in parent.task_graph.nodes}
    authored = _ok(host.include_at_author(original_a, original_b, new_version="1.1.0"))
    assert authored.qualified_id == "research-corpus:a"
    assert authored.version == "1.1.0"
    assert authored.version != original_a.version
    node_ids = {node["id"] for node in authored.nodes}
    assert "work-b" in node_ids
    assert "start-b" not in node_ids
    kept = host.templates.get_versioned("research-corpus:a", "1.0.0")
    assert kept is not None
    assert {node["id"] for node in kept.nodes} == {"start-b"}
    assert "work-b" not in {node["id"] for node in kept.nodes}
    assert {node.id for node in parent.task_graph.nodes} == live_nodes
    assert host.is_live(parent.task_graph.id) is True
    compiled = _ok(
        host.compiler.compile(
            CompileRequest(
                goal=parent.mission.goal,
                owner=_quant(),
                graph_template_ref="research-corpus:a",
                graph_template_version="1.1.0",
                require_decomposition_reasoning=False,
            )
        )
    )
    assert {node.id for node in compiled.task_graph.nodes} == {"work-b"}
    assert compiled.task_graph.id != parent.task_graph.id
    silent = host.compiler.compile(
        CompileRequest(
            goal=parent.mission.goal,
            owner=_quant(),
            graph_template_ref="research-corpus:a",
            require_decomposition_reasoning=False,
        )
    )
    assert is_refusal(silent)
    assert silent.context["field"] == "graph_template_version"
    assert silent.context["substituted"] is False


def test_include_at_author_is_not_a_runtime_merge_of_live_task_graphs() -> None:
    host = NestedMissionHost()
    _ok(host.register_template(_template_a()))
    _ok(host.register_template(_template_b()))
    parent = _ok(
        host.compile_parent(
            owner=_quant(),
            template=_template_a(),
            goal="run A then nested B",
        )
    )
    nested = _ok(
        host.invoke(
            "start",
            envelope=_envelope(),
            parent_graph_id=parent.task_graph.id,
            node_id="start-b",
            caller_grant_ids=("grant:a",),
            callee_grant_ids=("grant:b",),
        )
    )
    as_graphs = include_subgraph_at_author(
        parent.task_graph,
        nested.task_graph,
        new_version="1.1.0",
    )
    assert is_refusal(as_graphs)
    assert as_graphs.category is RefusalCategory.INVALID_INPUT
    assert as_graphs.context["runtime_merge"] is False
    via_host = host.include_at_author(
        parent.task_graph,
        nested.task_graph,
        new_version="1.1.0",
    )
    assert is_refusal(via_host)
    assert via_host.context["runtime_merge"] is False
    colliding = include_subgraph_at_author(
        GraphTemplate(
            qualified_id="research-corpus:a",
            version="1.0.0",
            nodes=({"id": "work-b", "kind": "task", "intent": "parent work"},),
        ),
        _template_b(),
        new_version="1.1.0",
    )
    assert is_refusal(colliding)
    assert colliding.context["substituted"] is False


def test_live_task_graph_merge_refuses_without_substituting_identity() -> None:
    host = NestedMissionHost()
    _ok(host.register_template(_template_a()))
    _ok(host.register_template(_template_b()))
    parent = _ok(
        host.compile_parent(
            owner=_quant(),
            template=_template_a(),
            goal="run A then nested B",
        )
    )
    nested = _ok(
        host.invoke(
            "start",
            envelope=_envelope(),
            parent_graph_id=parent.task_graph.id,
            node_id="start-b",
            caller_grant_ids=("grant:a",),
            callee_grant_ids=("grant:b",),
        )
    )
    merged = host.merge_live_task_graphs(
        parent.task_graph.id,
        nested.task_graph.id,
        instance_id="inst:1",
        version="1.0.0",
        account="acct:1",
        substitute_instance_id="inst:other",
        substitute_version="9.9.9",
        substitute_account="acct:other",
    )
    assert is_refusal(merged)
    assert merged.category is RefusalCategory.INVALID_INPUT
    assert merged.context["code"] == "INVALID_INPUT"
    assert merged.context["merged"] is False
    assert merged.context["substituted"] is False
    assert merged.context["substituted_instance"] is False
    assert merged.context["substituted_version"] is False
    assert merged.context["substituted_account"] is False
    missing = host.merge_live_task_graphs(
        "taskgraph:missing",
        nested.task_graph.id,
        substitute_instance_id="inst:other",
        substitute_version="9.9.9",
        substitute_account="acct:other",
    )
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.INVALID_INPUT
    assert missing.context["left_found"] is False
    assert missing.context["right_found"] is True
    assert missing.context["substituted"] is False
    others = missing.context["other_live_graph_ids"]
    assert isinstance(others, (list, tuple))
    assert nested.task_graph.id not in others
    assert host.is_live(parent.task_graph.id) is True
    assert host.is_live(nested.task_graph.id) is True
    assert {node.id for node in parent.task_graph.nodes} == {"start-b"}
    assert {node.id for node in nested.task_graph.nodes} == {"work-b"}


def test_call_depth_ceiling_is_not_gap_0108_retry_row() -> None:
    assert RECURSION_CEILING_ROW_IMPLEMENTED is True
    assert GAP_0108_IS_RETRY_ATTEMPT_CEILING is True
    assert CALL_DEPTH_REUSES_RETRY_REGISTRY_ROW is False
    assert HOST_NESTED_MISSION_CALL_DEPTH_CEILING_KEY != HOST_RETRY_ATTEMPT_CEILING_KEY
    assert (
        HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY
        != HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY
    )
    registry = GovernedVariableRegistry.with_builtins()
    row = _ok(registry.get(HOST_NESTED_MISSION_CALL_DEPTH_CEILING_KEY))
    assert row.name == HOST_NESTED_MISSION_CALL_DEPTH_CEILING_KEY
    assert row.registry_key == HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY
    assert row.owning_subsystem == "COMP-QMA-DAEMON"
    assert row.default is None
    host = NestedMissionHost()
    assert host.call_depth_ceiling_key == HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY
    assert _ok(host.call_depth_ceiling()) is None
    reused = bind_call_depth_ceiling_key(HOST_RETRY_ATTEMPT_CEILING_KEY)
    assert is_refusal(reused)
    assert reused.category is RefusalCategory.INVALID_INPUT
    assert reused.context["reused_retry_row"] is False
    assert reused.context["gap_0108"] is False
    bound = _ok(bind_call_depth_ceiling_key(HOST_NESTED_MISSION_CALL_DEPTH_CEILING_KEY))
    assert bound == HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY
    nested_src = (
        Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "taskgraph" / "nested.py"
    )
    variables_src = (
        Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "journal" / "variables.py"
    )
    nested_text = nested_src.read_text(encoding="utf-8")
    variables_text = variables_src.read_text(encoding="utf-8")
    assert "injected_call_depth_ceiling: int = 2" not in nested_text
    assert "DEFAULT_CALL_DEPTH_CEILING" not in nested_text
    snippet = variables_text.split(HOST_NESTED_MISSION_CALL_DEPTH_CEILING_KEY, 1)[1][:400]
    assert "default=2" not in snippet
    assert "default=3" not in snippet


def test_over_budget_call_depth_is_invalid_input() -> None:
    host = NestedMissionHost(injected_call_depth_ceiling=1)
    _ok(host.register_template(_template_a()))
    _ok(host.register_template(_template_b()))
    parent = _ok(
        host.compile_parent(
            owner=_quant(),
            template=_template_a(),
            goal="run A then nested B",
        )
    )
    nested = _ok(
        host.invoke(
            "start",
            envelope=_envelope(),
            parent_graph_id=parent.task_graph.id,
            node_id="start-b",
            caller_grant_ids=("grant:a",),
            callee_grant_ids=("grant:b",),
        )
    )
    assert nested.envelope.call_depth == 1
    over = host.invoke(
        "start",
        envelope=_envelope(call_depth=2, idempotency_key="idem:deep"),
        parent_graph_id=parent.task_graph.id,
        node_id="start-b",
        caller_grant_ids=("grant:a",),
        callee_grant_ids=("grant:b",),
    )
    assert is_refusal(over)
    assert over.category is RefusalCategory.INVALID_INPUT
    assert over.context["field"] == "call_depth"
    assert over.context["code"] == "INVALID_INPUT"
    assert over.context["call_depth"] == 2
    assert over.context["ceiling"] == 1
    assert over.context["registry_key"] == HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY
    assert over.context["gap_0108"] is False
    assert over.context["reused_retry_row"] is False
