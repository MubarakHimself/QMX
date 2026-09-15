"""Instantiate a QMA procedure: one Graph Template compiles to one Mission.

Story 37.1 / FR-W32. Skills stay knowledge. Routines expand their named Graph
Template. The procedure itself is not an ExperimentSpec and mints no CT-07
edge. Any door step is READY so it may be the first placement.

Story 37.2 / FR-W33. Run-steps occupy the CT-47 qmb door. Query-steps call
Epic 35/33 door queries and consume no occupancy.

Story 37.3 / FR-W34. A door step that changes resolved-config mints an
ExperimentSpec successor via ``create_successor`` plus CT-07
``branches-from``. Query-steps that do not change resolved-config mint
no successor. Coordinated continuity remains the spec fp1.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from qma.core.control.procedures import (
    COMPOSITION_NON_LINEAR,
    PROCEDURE_IS_EXPERIMENT_SPEC,
    ProcedureKind,
    ReusableProcedure,
    author_procedure,
    classify_procedure_step,
    refuse_procedure_as_experiment_spec,
)
from qma.core.ontology import ActorId, Goal, Quant
from qma.core.ports.qmb import QMB_WORLD_REPLAY, QmbDoorKind
from qma.core.vocabulary.enums import PrincipalClass, TaskMissionState
from qma.daemon.taskgraph.compiler import CompileRequest, CompileResult, MissionCompiler
from qma.daemon.taskgraph.records import DispatchLease, GraphTemplate
from qmf.core import Ok, Result, is_ok
from qmf.data.store.refusals import invalid_input, policy_rejection

if TYPE_CHECKING:
    from qma.daemon.backtest.service import BacktestingService, ProcedureStepPlacement

__all__ = [
    "execute_procedure_door_step",
    "instantiate_procedure",
]


def instantiate_procedure(
    procedure: ReusableProcedure | Mapping[str, object],
    *,
    owner: Quant,
    compiler: MissionCompiler,
    goal: Goal | None = None,
    principal: PrincipalClass | str | None = None,
) -> Result[CompileResult]:
    """Compile one Graph Template instantiation to exactly one Mission."""
    if isinstance(procedure, ReusableProcedure):
        record = procedure
    else:
        authored = author_procedure(procedure, principal=principal)
        if not is_ok(authored):
            return authored
        record = authored.value
    if record.is_experiment_spec is not PROCEDURE_IS_EXPERIMENT_SPEC:
        return refuse_procedure_as_experiment_spec(given=record.qualified_id)
    if record.composition != COMPOSITION_NON_LINEAR:
        return policy_rejection(
            "composition",
            "procedure composition stays non-linear (FR-W32; FR-W34; DEC-0277)",
            given=record.composition,
        )
    if record.kind is ProcedureKind.SKILL:
        return policy_rejection(
            "kind",
            "a Skill is reusable procedure knowledge and does not compile to a "
            "Mission; instantiate the Graph Template (FR-W32; AD-13)",
            qualified_id=record.qualified_id,
        )
    if record.kind is ProcedureKind.ROUTINE:
        if record.routine is None or record.graph_template_ref is None:
            return invalid_input(
                "graph_template_ref",
                "a Routine instantiates by expanding its named Graph Template",
            )
        template_ref = record.graph_template_ref
        intent = record.routine.goal.text
        resolved_goal = record.routine.goal
    else:
        template_ref = record.qualified_id
        if compiler.templates.get(template_ref) is None:
            registered = compiler.templates.register(
                GraphTemplate(
                    qualified_id=record.qualified_id,
                    version=record.version,
                    nodes=record.nodes,
                    edges=record.edges,
                )
            )
            if not is_ok(registered):
                return registered
        resolved_goal = goal if goal is not None else Goal(text=record.qualified_id)
        intent = resolved_goal.text

    compiled = compiler.compile(
        CompileRequest(
            goal=resolved_goal,
            owner=owner,
            graph_template_ref=template_ref,
            intent=intent,
            require_decomposition_reasoning=False,
        )
    )
    if not is_ok(compiled):
        return compiled
    result = compiled.value
    graph = result.task_graph
    door_ids = frozenset(record.first_door_steps)
    if door_ids:
        for task in result.task_graph.tasks:
            if task.node_id in door_ids and task.state is not TaskMissionState.READY:
                graph = graph.replace_task(task.with_state(TaskMissionState.READY))
    if result.mission.graph_template_ref != template_ref:
        return invalid_input(
            "graph_template_ref",
            "Graph Template instantiation must cite the authored procedure",
            given=result.mission.graph_template_ref,
        )
    return Ok(CompileResult(mission=result.mission, task_graph=graph))


def execute_procedure_door_step(
    procedure: ReusableProcedure,
    node_id: str,
    *,
    service: BacktestingService,
    owner: ActorId | Quant | str,
    environment_ref: str,
    task_id: str | None = None,
    experiment_spec_fp1: str | None = None,
    evidence_ref: str | None = None,
    extra: Mapping[str, object] | None = None,
    dispatch_lease: DispatchLease | None = None,
    model_deployment_ref: object = None,
    persist_projection: bool = False,
    mint_ct32: object = None,
    successor: object = None,
    resolved_config_ref: object = None,
    change: object = None,
    edge_type: object = None,
    world: str | None = None,
    door: QmbDoorKind | str = QmbDoorKind.CLI,
) -> Result[ProcedureStepPlacement]:
    """Place one authored procedure node through the Story 36.2 QMB door."""
    node: Mapping[str, object] | None = None
    for candidate in procedure.nodes:
        if candidate.get("id") == node_id:
            node = candidate
            break
    if node is None:
        return invalid_input(
            "node_id",
            "procedure door step must name an authored Graph Template node",
            given=node_id,
            qualified_id=procedure.qualified_id,
        )
    classified = classify_procedure_step(node)
    if not is_ok(classified):
        return classified
    actor: ActorId | str = owner.actor_id if isinstance(owner, Quant) else owner
    return service.place_procedure_step(
        node,
        owner=actor,
        task_id=task_id if task_id is not None else node_id,
        environment_ref=environment_ref,
        experiment_spec_fp1=experiment_spec_fp1,
        evidence_ref=evidence_ref,
        extra=extra,
        dispatch_lease=dispatch_lease,
        model_deployment_ref=model_deployment_ref,
        persist_projection=persist_projection,
        mint_ct32=mint_ct32,
        successor=successor,
        resolved_config_ref=resolved_config_ref,
        change=change,
        edge_type=edge_type,
        world=world if world is not None else QMB_WORLD_REPLAY,
        door=door,
    )
