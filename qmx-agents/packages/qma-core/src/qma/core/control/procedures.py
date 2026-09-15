"""Reusable procedures live in QMA (FR-W32; DEC-0277; workbench AD-9).

A reusable procedure is a Graph Template, Skill, or operator Routine.
QMB does not grow a task-graph module. The procedure itself is not an
ExperimentSpec and mints no CT-07 edge kind. Composition is non-linear:
any door step may be the first placement. A compulsory
research→backtest→paper wizard or SQ Custom Projects clone is refused.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Final, Literal, cast

from qma.core.control.primitives import ControlPrimitive, Skill
from qma.core.ontology.routine import (
    ROUTINE_METADATA_KEYS,
    ROUTINE_REQUIRED_FIELDS,
    Routine,
    authorize_routine_write,
    parse_graph_template_ref,
    parse_routine,
)
from qma.core.ports.experiments import COORDINATED_CONTINUITY_KIND
from qma.core.ports.qmb import (
    ANALYSIS_BACKTEST_PLUGIN_ID,
    QMB_OCCUPANCY_QUERY,
    QMB_OCCUPANCY_RUN,
    QMB_QUERY_COMMANDS,
    QMB_RUN_COMMANDS,
    classify_qmb_door_occupancy,
)
from qma.core.vocabulary.enums import GraphArtifactKind, PrincipalClass
from qmf.core import Ok, Result, is_ok
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "ANALYSIS_PROCEDURE_ID",
    "ANALYSIS_PROCEDURE_LOCAL_ID",
    "ANALYSIS_PROCEDURE_SKILL_ID",
    "ANALYSIS_PROCEDURE_SKILL_LOCAL_ID",
    "COMPOSITION_NON_LINEAR",
    "FORBIDDEN_QMB_TASK_GRAPH_NAMES",
    "PROCEDURE_CT07_EDGE_KIND",
    "PROCEDURE_HOMES",
    "PROCEDURE_IS_EXPERIMENT_SPEC",
    "PROCEDURE_MINTS_CT07_EDGE",
    "QMB_GROWS_TASK_GRAPH",
    "QMB_PROCEDURE_DOOR_STEPS",
    "REFUSED_PROCEDURE_PRODUCTS",
    "REFUSED_WIZARD_SEQUENCE",
    "ProcedureKind",
    "ReusableProcedure",
    "author_procedure",
    "door_step_ids",
    "first_door_step_ids",
    "is_door_step",
    "parse_reusable_procedure",
    "procedure_ct07_edge_kinds",
    "procedure_mints_ct07_edge",
    "qmb_grows_task_graph",
    "refuse_linear_wizard",
    "refuse_procedure_as_experiment_spec",
    "refuse_qmb_task_graph",
    "refuse_sq_custom_projects_clone",
    "scan_qmb_task_graph_modules",
]


class ProcedureKind(StrEnum):
    """Closed procedure homes — Graph Template, Skill, or operator Routine."""

    GRAPH_TEMPLATE = ControlPrimitive.GRAPH_TEMPLATE.value
    SKILL = ControlPrimitive.SKILL.value
    ROUTINE = "routine"


PROCEDURE_HOMES: Final[frozenset[ProcedureKind]] = frozenset(ProcedureKind)
COMPOSITION_NON_LINEAR: Final[Literal["non_linear"]] = "non_linear"
PROCEDURE_IS_EXPERIMENT_SPEC: Final[Literal[False]] = False
PROCEDURE_CT07_EDGE_KIND: Final[None] = None
PROCEDURE_MINTS_CT07_EDGE: Final[Literal[False]] = False
QMB_GROWS_TASK_GRAPH: Final[Literal[False]] = False

ANALYSIS_PROCEDURE_LOCAL_ID: Final[str] = "procedure"
ANALYSIS_PROCEDURE_ID: Final[str] = f"{ANALYSIS_BACKTEST_PLUGIN_ID}:{ANALYSIS_PROCEDURE_LOCAL_ID}"
ANALYSIS_PROCEDURE_SKILL_LOCAL_ID: Final[str] = "steps"
ANALYSIS_PROCEDURE_SKILL_ID: Final[str] = (
    f"{ANALYSIS_BACKTEST_PLUGIN_ID}:{ANALYSIS_PROCEDURE_SKILL_LOCAL_ID}"
)

QMB_PROCEDURE_DOOR_STEPS: Final[tuple[Mapping[str, object], ...]] = (
    MappingProxyType(
        {
            "id": "backtest",
            "kind": "task",
            "door": "qmb",
            "placement": QMB_OCCUPANCY_RUN,
            "command": "backtest.run",
        }
    ),
    MappingProxyType(
        {
            "id": "project",
            "kind": "task",
            "door": "qmb",
            "placement": QMB_OCCUPANCY_QUERY,
            "command": "analysis.project",
        }
    ),
    MappingProxyType(
        {
            "id": "rank",
            "kind": "task",
            "door": "qmb",
            "placement": QMB_OCCUPANCY_QUERY,
            "command": "sweep.rank",
        }
    ),
    MappingProxyType(
        {
            "id": "download",
            "kind": "task",
            "door": "qmb",
            "placement": QMB_OCCUPANCY_RUN,
            "command": "data.download",
        }
    ),
)

REFUSED_PROCEDURE_PRODUCTS: Final[frozenset[str]] = frozenset(
    {
        "wizard",
        "linear_wizard",
        "compulsory_wizard",
        "research_backtest_paper",
        "research-backtest-paper",
        "custom_projects",
        "custom-projects",
        "sq_custom_projects",
        "sq-custom-projects",
        "strategyquant_custom_projects",
        "sq_custom_project",
    }
)
REFUSED_WIZARD_SEQUENCE: Final[tuple[str, ...]] = ("research", "backtest", "paper")
FORBIDDEN_QMB_TASK_GRAPH_NAMES: Final[frozenset[str]] = frozenset(
    {
        "taskgraph",
        "task_graph",
        "workflow",
        "wizard",
        "custom_projects",
        "custom-projects",
        "kanban",
    }
)
_QMB_TASK_GRAPH_HOMES: Final[frozenset[str]] = frozenset(
    {
        "qmb",
        "qmb.taskgraph",
        "qmb.task_graph",
        "qmb.workflow",
        "taskgraph",
        "task_graph",
    }
)
_PROCEDURE_KIND_ALIASES: Final[Mapping[str, ProcedureKind]] = MappingProxyType(
    {
        ProcedureKind.GRAPH_TEMPLATE.value: ProcedureKind.GRAPH_TEMPLATE,
        GraphArtifactKind.GRAPH_TEMPLATE.value: ProcedureKind.GRAPH_TEMPLATE,
        ControlPrimitive.GRAPH_TEMPLATE.value: ProcedureKind.GRAPH_TEMPLATE,
        ProcedureKind.SKILL.value: ProcedureKind.SKILL,
        ControlPrimitive.SKILL.value: ProcedureKind.SKILL,
        ProcedureKind.ROUTINE.value: ProcedureKind.ROUTINE,
        "operator_routine": ProcedureKind.ROUTINE,
    }
)
_SKIP_SCAN_DIRS: Final[frozenset[str]] = frozenset(
    {".git", "__pycache__", ".venv", "node_modules", ".ruff_cache"}
)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def _normalize_product_token(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().casefold().replace(" ", "_").replace("/", "_")


def qmb_grows_task_graph() -> bool:
    """QMB never grows a task-graph / workflow module (FR-W32; DEC-0277)."""
    return QMB_GROWS_TASK_GRAPH


def procedure_mints_ct07_edge() -> bool:
    """Procedures mint no CT-07 edge kind (FR-W32; FR-W34; DEC-0277)."""
    return PROCEDURE_MINTS_CT07_EDGE


def procedure_ct07_edge_kinds() -> frozenset[str]:
    """Empty: this story does not mint a CT-07 kind. V1 tokens stay parent-owned."""
    return frozenset()


def refuse_qmb_task_graph(*, given: object = "qmb.taskgraph") -> TypedRefusal:
    """Refuse a task-graph / workflow engine inside QMB."""
    return _policy(
        "home",
        "reusable procedures live in QMA as Graph Templates, Skills, or operator "
        "Routines; QMB does not grow a task-graph module (FR-W32; DEC-0277)",
        given=repr(given),
        qmb_grows_task_graph=False,
    )


def refuse_linear_wizard(*, given: object = "research-backtest-paper") -> TypedRefusal:
    """Refuse a compulsory research→backtest→paper wizard."""
    return _policy(
        "product",
        "a compulsory research→backtest→paper wizard is refused; composition "
        "stays non-linear and any step may be the first door placement "
        "(FR-W32; FR-W34; DEC-0277)",
        given=repr(given),
        composition=COMPOSITION_NON_LINEAR,
        sequence=list(REFUSED_WIZARD_SEQUENCE),
    )


def refuse_sq_custom_projects_clone(*, given: object = "custom_projects") -> TypedRefusal:
    """SQ Custom Projects remain a donor shape, not a clone."""
    return _policy(
        "product",
        "SQ Custom Projects remain a donor shape, not a clone; reusable "
        "procedures are QMA Graph Templates, Skills, and operator Routines "
        "(FR-W32; DEC-0277)",
        given=repr(given),
        donor="strategyquant_custom_projects",
    )


def refuse_procedure_as_experiment_spec(*, given: object = "procedure") -> TypedRefusal:
    """The procedure itself is not an ExperimentSpec."""
    return _policy(
        "experiment_spec",
        "the procedure itself is not an ExperimentSpec; one Graph Template "
        "instantiation compiles to one Mission (FR-W32; FR-W34; DEC-0277)",
        given=repr(given),
        is_experiment_spec=False,
        continuity=COORDINATED_CONTINUITY_KIND,
        ct07_edge_kind=None,
    )


def is_door_step(node: Mapping[str, object]) -> bool:
    """True when a Graph Template node places a QMB door run or query."""
    door = node.get("door")
    if isinstance(door, str) and door.strip().casefold() in {"qmb", "cli", "mcp"}:
        return True
    placement = node.get("placement")
    if placement in {QMB_OCCUPANCY_RUN, QMB_OCCUPANCY_QUERY}:
        return True
    command = node.get("command")
    if not isinstance(command, str) or command.strip() == "":
        return False
    token = command.strip().casefold()
    if token in QMB_RUN_COMMANDS or token in QMB_QUERY_COMMANDS:
        return True
    classified = classify_qmb_door_occupancy(command)
    return is_ok(classified)


def door_step_ids(nodes: Sequence[Mapping[str, object]]) -> tuple[str, ...]:
    """Node ids that place through the QMB door — any may be first."""
    found: list[str] = []
    for node in nodes:
        raw_id = node.get("id")
        if isinstance(raw_id, str) and raw_id and is_door_step(node):
            found.append(raw_id)
    return tuple(found)


def first_door_step_ids(nodes: Sequence[Mapping[str, object]]) -> tuple[str, ...]:
    """Non-linear composition: every door step is a legal first placement."""
    return door_step_ids(nodes)


def scan_qmb_task_graph_modules(root: Path) -> tuple[str, ...]:
    """Filesystem hits for a forbidden QMB task-graph / wizard module."""
    if not root.exists():
        return ()
    hits: list[str] = []
    if root.is_file():
        stem = root.stem.casefold().replace("-", "_")
        if stem in FORBIDDEN_QMB_TASK_GRAPH_NAMES:
            return (str(root),)
        return ()
    for path in root.rglob("*"):
        if any(part in _SKIP_SCAN_DIRS for part in path.parts):
            continue
        token = path.stem.casefold().replace("-", "_") if path.is_file() else path.name
        token = token.casefold().replace("-", "_")
        if token in FORBIDDEN_QMB_TASK_GRAPH_NAMES:
            hits.append(str(path))
    return tuple(dict.fromkeys(hits))


def _nodes_from(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    rows: list[Mapping[str, object]] = []
    for item in cast("Sequence[object]", value):
        if isinstance(item, Mapping):
            rows.append(MappingProxyType(dict(cast("Mapping[str, object]", item))))
    return tuple(rows)


def _edges_from(value: object) -> tuple[Mapping[str, object], ...]:
    return _nodes_from(value)


def _compulsory_order(value: object) -> tuple[str, ...]:
    if isinstance(value, str) and value.strip():
        parts = [part.strip().casefold() for part in value.replace("→", ">").split(">")]
        return tuple(part for part in parts if part)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(
            str(item).strip().casefold()
            for item in cast("Sequence[object]", value)
            if str(item).strip()
        )
    return ()


def _wizard_refusal(body: Mapping[str, object]) -> TypedRefusal | None:
    home = body.get("home", body.get("module"))
    if isinstance(home, str) and home.strip().casefold() in _QMB_TASK_GRAPH_HOMES:
        return refuse_qmb_task_graph(given=home)
    for key in ("product", "clone", "wizard", "kind"):
        token = _normalize_product_token(body.get(key))
        if token in REFUSED_PROCEDURE_PRODUCTS:
            if "custom" in token or token.startswith("sq"):
                return refuse_sq_custom_projects_clone(given=body.get(key))
            return refuse_linear_wizard(given=body.get(key))
    if body.get("linear") is True:
        return refuse_linear_wizard(given="linear=true")
    if body.get("required_first_door") not in (None, False, ""):
        return refuse_linear_wizard(given=body.get("required_first_door"))
    order = _compulsory_order(body.get("compulsory_order"))
    if order:
        return refuse_linear_wizard(given=list(order))
    continuity = _normalize_product_token(body.get("continuity"))
    if continuity in {
        COORDINATED_CONTINUITY_KIND,
        "experimentspec",
        "experiment_spec",
        "spec_fp1",
    }:
        return refuse_procedure_as_experiment_spec(given=body.get("continuity"))
    return None


def _resolve_kind(body: Mapping[str, object]) -> Result[ProcedureKind]:
    raw = body.get("kind", body.get("control_primitive", body.get("artifact_kind")))
    if raw is None:
        if "graph_template_ref" in body and "schedule" in body:
            return Ok(ProcedureKind.ROUTINE)
        if body.get("artifact_kind") == GraphArtifactKind.GRAPH_TEMPLATE.value:
            return Ok(ProcedureKind.GRAPH_TEMPLATE)
        if body.get("control_primitive") == ControlPrimitive.SKILL.value:
            return Ok(ProcedureKind.SKILL)
        if "nodes" in body or "qualified_id" in body:
            if body.get("summary") is not None and "nodes" not in body:
                return Ok(ProcedureKind.SKILL)
            return Ok(ProcedureKind.GRAPH_TEMPLATE)
        return _invalid(
            "kind",
            "a reusable procedure is a Graph Template, Skill, or operator Routine "
            "(FR-W32; DEC-0277)",
            given=repr(raw),
            allowed=sorted(kind.value for kind in ProcedureKind),
        )
    token = _normalize_product_token(raw)
    if token in REFUSED_PROCEDURE_PRODUCTS:
        if "custom" in token or token.startswith("sq"):
            return refuse_sq_custom_projects_clone(given=raw)
        return refuse_linear_wizard(given=raw)
    if token in {"experiment_spec", "experimentspec"}:
        return refuse_procedure_as_experiment_spec(given=raw)
    kind = _PROCEDURE_KIND_ALIASES.get(token)
    if kind is None:
        return _invalid(
            "kind",
            "a reusable procedure is a Graph Template, Skill, or operator Routine "
            "(FR-W32; DEC-0277)",
            given=repr(raw),
            allowed=sorted(kind.value for kind in ProcedureKind),
        )
    return Ok(kind)


@dataclass(frozen=True, slots=True)
class ReusableProcedure:
    """Authored QMA procedure. Not an ExperimentSpec. Not a QMB task graph."""

    kind: ProcedureKind
    qualified_id: str
    version: str
    nodes: tuple[Mapping[str, object], ...] = ()
    edges: tuple[Mapping[str, object], ...] = ()
    skill: Skill | None = None
    routine: Routine | None = None
    composition: Literal["non_linear"] = COMPOSITION_NON_LINEAR
    is_experiment_spec: Literal[False] = PROCEDURE_IS_EXPERIMENT_SPEC
    ct07_edge_kind: None = PROCEDURE_CT07_EDGE_KIND

    @property
    def first_door_steps(self) -> tuple[str, ...]:
        return first_door_step_ids(self.nodes)

    @property
    def graph_template_ref(self) -> str | None:
        if self.kind is ProcedureKind.GRAPH_TEMPLATE:
            return self.qualified_id
        if self.kind is ProcedureKind.ROUTINE and self.routine is not None:
            return self.routine.graph_template_ref
        return None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "kind": self.kind.value,
            "qualified_id": self.qualified_id,
            "version": self.version,
            "composition": self.composition,
            "is_experiment_spec": False,
            "ct07_edge_kind": None,
            "mints_ct07_edge": False,
            "home": "qma",
            "first_door_steps": list(self.first_door_steps),
        }
        if self.kind is ProcedureKind.GRAPH_TEMPLATE:
            payload["artifact_kind"] = GraphArtifactKind.GRAPH_TEMPLATE.value
            payload["stateless"] = True
            payload["runtime_state"] = None
            payload["nodes"] = [dict(node) for node in self.nodes]
            payload["edges"] = [dict(edge) for edge in self.edges]
            payload["control_primitive"] = ControlPrimitive.GRAPH_TEMPLATE.value
        elif self.kind is ProcedureKind.SKILL and self.skill is not None:
            payload.update(dict(self.skill.to_payload()))
            payload["kind"] = ProcedureKind.SKILL.value
        elif self.kind is ProcedureKind.ROUTINE and self.routine is not None:
            payload.update(dict(self.routine.to_payload()))
            payload["kind"] = ProcedureKind.ROUTINE.value
            payload["qualified_id"] = self.qualified_id
        return MappingProxyType(payload)


def _has_wizard_chain(
    nodes: Sequence[Mapping[str, object]],
    edges: Sequence[Mapping[str, object]],
) -> bool:
    ids = {str(node.get("id", "")).casefold().replace("-", "_") for node in nodes}
    needed = set(REFUSED_WIZARD_SEQUENCE)
    if not needed.issubset(ids):
        return False
    forward = {
        (
            str(edge.get("from", "")).casefold().replace("-", "_"),
            str(edge.get("to", "")).casefold().replace("-", "_"),
        )
        for edge in edges
    }
    return ("research", "backtest") in forward and ("backtest", "paper") in forward


def _author_graph_template(body: Mapping[str, object]) -> Result[ReusableProcedure]:
    qualified = body.get("qualified_id")
    parsed = parse_graph_template_ref(qualified)
    if not is_ok(parsed):
        return parsed
    version = body.get("version", "0.1.0")
    if not isinstance(version, str) or version.strip() == "":
        return _invalid("version", "Graph Template version is a non-empty string")
    nodes = _nodes_from(body.get("nodes", ()))
    edges = _edges_from(body.get("edges", ()))
    if _has_wizard_chain(nodes, edges):
        return refuse_linear_wizard(given="research→backtest→paper")
    return Ok(
        ReusableProcedure(
            kind=ProcedureKind.GRAPH_TEMPLATE,
            qualified_id=parsed.value,
            version=version.strip(),
            nodes=nodes,
            edges=edges,
        )
    )


def _author_skill(body: Mapping[str, object]) -> Result[ReusableProcedure]:
    qualified = body.get("qualified_id")
    if not isinstance(qualified, str) or ":" not in qualified:
        return _invalid(
            "qualified_id",
            "skill id must be fully-qualified <plugin_id>:<local_id> (AD-13; FR-W32)",
            given=repr(qualified),
        )
    version = body.get("version", "0.1.0")
    if not isinstance(version, str) or version.strip() == "":
        return _invalid("version", "Skill version is a non-empty string")
    summary = body.get("summary", "")
    if not isinstance(summary, str) or summary.strip() == "":
        return _invalid("summary", "Skill summary is required (AD-13; FR-W32)")
    raw_body = body.get("body", "")
    text = raw_body if isinstance(raw_body, str) else ""
    loop_ref = body.get("loop_ref")
    try:
        skill = Skill(
            qualified_id=qualified.strip(),
            version=version.strip(),
            summary=summary.strip(),
            body=text,
            loop_ref=loop_ref if isinstance(loop_ref, str) else None,
        )
    except ValueError as exc:
        return _invalid("skill", str(exc), given=qualified)
    return Ok(
        ReusableProcedure(
            kind=ProcedureKind.SKILL,
            qualified_id=skill.qualified_id,
            version=skill.version,
            skill=skill,
        )
    )


def _author_routine(
    body: Mapping[str, object],
    *,
    principal: PrincipalClass | str | None,
) -> Result[ReusableProcedure]:
    auth = authorize_routine_write(principal if principal is not None else "agent")
    if not is_ok(auth):
        return auth
    routine_body = {
        key: value
        for key, value in body.items()
        if key in ROUTINE_REQUIRED_FIELDS or key in ROUTINE_METADATA_KEYS
    }
    parsed = parse_routine(routine_body)
    if not is_ok(parsed):
        return parsed
    routine = parsed.value
    return Ok(
        ReusableProcedure(
            kind=ProcedureKind.ROUTINE,
            qualified_id=f"routine:{routine.id}",
            version="0.1.0",
            routine=routine,
        )
    )


def author_procedure(
    body: Mapping[str, object] | ReusableProcedure,
    *,
    principal: PrincipalClass | str | None = None,
) -> Result[ReusableProcedure]:
    """Admit a Graph Template, Skill, or operator Routine as a reusable procedure."""
    if isinstance(body, ReusableProcedure):
        return Ok(body)
    wizard = _wizard_refusal(body)
    if wizard is not None:
        return wizard
    kind = _resolve_kind(body)
    if not is_ok(kind):
        return kind
    resolved = kind.value
    if resolved is ProcedureKind.GRAPH_TEMPLATE:
        return _author_graph_template(body)
    if resolved is ProcedureKind.SKILL:
        return _author_skill(body)
    return _author_routine(body, principal=principal)


def parse_reusable_procedure(
    body: Mapping[str, object] | ReusableProcedure,
    *,
    principal: PrincipalClass | str | None = None,
) -> Result[ReusableProcedure]:
    """Result-returning constructor — alias of :func:`author_procedure`."""
    return author_procedure(body, principal=principal)
