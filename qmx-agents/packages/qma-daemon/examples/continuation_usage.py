"""L27 reference usage: verified continuation within registry bounds."""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from pathlib import Path

from qma.core.ontology import (
    CONTINUATION_BOUND_KEYS,
    CONTINUATION_BUDGET_KEY,
    CONTINUATION_ESCALATION_TARGET_KEY,
    CONTINUATION_MAX_CONSECUTIVE_KEY,
    ActorId,
    DeskSlug,
    Goal,
    Quant,
    RoleName,
)
from qma.core.plugins.hooks import (
    HookEvent,
    HookImplementationKind,
    HookResult,
    build_hook_result,
)
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.model import DeploymentRecord
from qma.core.vocabulary.enums import (
    ExecutionEnvironmentKind,
    HookResultDecision,
    ModelClass,
    TaskMissionState,
)
from qma.daemon import AuthoritativeJournal, PersistenceSubstrate
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.hooks.verifiers import DeterministicVerifier
from qma.daemon.journal import GovernedVariableRegistry
from qma.daemon.scheduler import AgentContinuation
from qma.daemon.taskgraph import CompileRequest, GraphTemplate, MissionCompiler, TaskGraphDispatcher
from qmf.core import DataDrivenClock, Instant, is_ok, is_refusal


class _EnvStub:
    """Structural ExecutionEnvironment stand-in."""


def _clock() -> DataDrivenClock:
    base = 1_700_000_000_000_000_000
    walls = tuple(Instant(value_ns=base + i) for i in range(32))
    monos = tuple(i * 1_000 for i in range(32))
    return DataDrivenClock(
        boot_epoch_id="continuation-example",
        wall_instants=walls,
        monotonic_ns=monos,
    )


def main() -> None:
    minted = ActorId.mint(DeskSlug.RESEARCH, "nova")
    assert is_ok(minted)
    owner = Quant(
        actor_id=minted.value,
        desk=DeskSlug.RESEARCH,
        quant_slug="nova",
        role=RoleName.RESEARCHER,
        name="Quant nova",
    )
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    registered = compiler.templates.register(
        GraphTemplate(
            qualified_id="research-corpus:survey",
            version="1",
            nodes=(
                {"id": "survey", "kind": "task", "intent": "survey corpus"},
                {"id": "summarize", "kind": "task", "intent": "summarize findings"},
            ),
        )
    )
    assert is_ok(registered)
    compiled = compiler.compile(
        CompileRequest(
            goal=Goal(text="survey corpus coverage"),
            owner=owner,
            graph_template_ref="research-corpus:survey",
        )
    )
    assert is_ok(compiled)
    envs = ExecutionEnvironmentRegistry()
    assert is_ok(
        envs.register(
            ExecutionEnvironmentKind.DOCKER,
            _EnvStub(),
            provider_id="local-docker",
            declaration=ExecutionEnvironmentDeclaration.isolated(
                ExecutionEnvironmentKind.DOCKER,
                provider_ref="local-docker",
            ),
        )
    )
    dispatcher = TaskGraphDispatcher(environments=envs)
    mission_id = compiled.value.mission.id
    dispatcher.materialize(compiled.value.task_graph, mission=compiled.value.mission)
    graph = dispatcher.store.for_mission(mission_id)
    assert graph is not None
    for task in graph.tasks:
        if task.state is TaskMissionState.PENDING:
            graph = graph.replace_task(task.with_state(TaskMissionState.READY))
    dispatcher.store.put(graph)

    root = Path(tempfile.mkdtemp(prefix="qma-continuation-"))
    substrate_result = PersistenceSubstrate.open(root, machine="example-host", boot_epoch_id="ex")
    assert is_ok(substrate_result)
    substrate = substrate_result.value
    journal_result = AuthoritativeJournal.bind(substrate, clock=_clock())
    assert is_ok(journal_result)
    journal = journal_result.value
    try:
        variables = GovernedVariableRegistry.with_builtins()
        continuation = AgentContinuation(_dispatcher=dispatcher, _variables=variables)
        assert continuation.bound_keys == CONTINUATION_BOUND_KEYS
        assert is_ok(continuation.register_quant(owner))
        for name, value in (
            (CONTINUATION_MAX_CONSECUTIVE_KEY, 2),
            (CONTINUATION_BUDGET_KEY, 0),
            (CONTINUATION_ESCALATION_TARGET_KEY, "quant_mailbox"),
        ):
            assert is_ok(
                continuation.variables.variable_set(
                    name,
                    value,
                    principal_class="operator",
                    journal=journal,
                )
            )

        first = graph.tasks[0]
        assert is_ok(
            continuation.dispatcher.dispatch_task(task_id=first.id, holder_agent_id="agent-a")
        )
        assert is_ok(
            continuation.attach_run(
                agent_id="agent-a",
                owner=owner,
                mission_id=mission_id,
                task_id=first.id,
            )
        )

        def verifier(_payload: Mapping[str, object]) -> Mapping[str, object]:
            return {"passed": False}

        catalog = (
            DeploymentRecord("author", ModelClass.WORKHORSE_GENERAL, "family-a"),
            DeploymentRecord("reviewer", ModelClass.REASONING_HIGH, "family-b"),
        )
        incomplete = continuation.propose_completion(
            agent_id="agent-a",
            task_id=first.id,
            verifier=DeterministicVerifier(kind=HookImplementationKind.CALLABLE, run=verifier),
            author_family="family-a",
            catalog=catalog,
        )
        assert is_ok(incomplete)
        assert incomplete.value.complete is False

        substituted = continuation.propose_completion(
            agent_id="agent-a",
            task_id=first.id,
            verifier=None,
            author_family="family-a",
            catalog=catalog,
            model_authored_outcome="done",
        )
        assert is_ok(substituted)
        assert substituted.value.complete is False
        assert substituted.value.model_substituted is True

        def block_stop(_event: HookEvent) -> HookResult:
            return build_hook_result(HookResultDecision.BLOCK_STOP)

        assert is_ok(continuation.hooks.register_handler("agent_stop", block_stop))
        exhausted = continuation.on_agent_stop("agent-a")
        assert is_ok(exhausted)
        assert exhausted.value.stopped is True
        assert exhausted.value.escalated is True
        assert exhausted.value.invented_task is False
        assert exhausted.value.escalation is not None
        assert exhausted.value.escalation.envelope.to_actor == owner.actor_id
        invented = continuation.invent_task(agent_id="agent-a")
        assert is_refusal(invented)
    finally:
        journal.close()
        substrate.close()


if __name__ == "__main__":
    main()
