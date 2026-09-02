"""Story 46.7 — continue verified Task Graph work within registered bounds (FR-Q63)."""

from __future__ import annotations

import runpy
from collections.abc import Mapping
from pathlib import Path

from qma.core.ontology import (
    CONTINUATION_BOUND_KEYS,
    CONTINUATION_BUDGET_KEY,
    CONTINUATION_ESCALATION_TARGET_KEY,
    CONTINUATION_MAX_CONSECUTIVE_KEY,
    CONTINUATION_UNDECLARED_VALUE,
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
    MessageKind,
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


def _quant(*, slug: str = "nova") -> Quant:
    minted = ActorId.mint(DeskSlug.RESEARCH, slug)
    assert is_ok(minted)
    return Quant(
        actor_id=minted.value,
        desk=DeskSlug.RESEARCH,
        quant_slug=slug,
        role=RoleName.RESEARCHER,
        name=f"Quant {slug}",
    )


def _clock(*, boot: str = "boot-continuation", n: int = 64) -> DataDrivenClock:
    base = 1_700_000_000_000_000_000
    walls = tuple(Instant(value_ns=base + i) for i in range(n))
    monos = tuple(i * 1_000 for i in range(n))
    return DataDrivenClock(boot_epoch_id=boot, wall_instants=walls, monotonic_ns=monos)


def _open_journal(
    tmp_path: Path, *, boot: str = "boot-continuation"
) -> tuple[PersistenceSubstrate, AuthoritativeJournal]:
    substrate_result = PersistenceSubstrate.open(tmp_path, machine="test-host", boot_epoch_id=boot)
    assert is_ok(substrate_result), substrate_result
    substrate = substrate_result.value
    journal_result = AuthoritativeJournal.bind(substrate, clock=_clock(boot=boot))
    assert is_ok(journal_result), journal_result
    return substrate, journal_result.value


class _EnvStub:
    """Structural ExecutionEnvironment stand-in."""


def _template() -> GraphTemplate:
    return GraphTemplate(
        qualified_id="research-corpus:survey",
        version="1",
        nodes=(
            {"id": "survey", "kind": "task", "intent": "survey corpus"},
            {"id": "summarize", "kind": "task", "intent": "summarize findings"},
        ),
    )


def _controller(
    tmp_path: Path,
) -> tuple[AgentContinuation, Quant, PersistenceSubstrate, AuthoritativeJournal, str]:
    owner = _quant()
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    registered = compiler.templates.register(_template())
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
    substrate, journal = _open_journal(tmp_path)
    variables = GovernedVariableRegistry.with_builtins()
    continuation = AgentContinuation(_dispatcher=dispatcher, _variables=variables)
    assert is_ok(continuation.register_quant(owner))
    return continuation, owner, substrate, journal, mission_id


def _declare_bounds(
    continuation: AgentContinuation,
    journal: AuthoritativeJournal,
    *,
    max_consecutive: int,
    budget: int,
    escalation_target: str = "quant_mailbox",
) -> None:
    for name, value in (
        (CONTINUATION_MAX_CONSECUTIVE_KEY, max_consecutive),
        (CONTINUATION_BUDGET_KEY, budget),
        (CONTINUATION_ESCALATION_TARGET_KEY, escalation_target),
    ):
        written = continuation.variables.variable_set(
            name,
            value,
            principal_class="operator",
            journal=journal,
        )
        assert is_ok(written)


def _catalog() -> tuple[DeploymentRecord, DeploymentRecord]:
    return (
        DeploymentRecord(
            deployment_id="author",
            model_class=ModelClass.WORKHORSE_GENERAL,
            model_family="family-a",
        ),
        DeploymentRecord(
            deployment_id="reviewer",
            model_class=ModelClass.REASONING_HIGH,
            model_family="family-b",
        ),
    )


def _passing_verifier() -> DeterministicVerifier:
    def run(_payload: Mapping[str, object]) -> Mapping[str, object]:
        return {"passed": True, "checks": ["schema"]}

    return DeterministicVerifier(kind=HookImplementationKind.CALLABLE, run=run)


def _failing_verifier() -> DeterministicVerifier:
    def run(_payload: Mapping[str, object]) -> Mapping[str, object]:
        return {"passed": False, "reason": "tests_failed"}

    return DeterministicVerifier(kind=HookImplementationKind.CALLABLE, run=run)


def _block_stop(_event: HookEvent) -> HookResult:
    return build_hook_result(HookResultDecision.BLOCK_STOP, reason="keep_working")


def test_completion_requires_deterministic_verifier(tmp_path: Path) -> None:
    continuation, owner, substrate, journal, mission_id = _controller(tmp_path)
    try:
        _declare_bounds(continuation, journal, max_consecutive=4, budget=4)
        graph = continuation.dispatcher.store.for_mission(mission_id)
        assert graph is not None
        task = graph.tasks[0]
        attached = continuation.attach_run(
            agent_id="agent-a",
            owner=owner,
            mission_id=task.mission_id,
            task_id=task.id,
        )
        assert is_ok(attached)
        missing = continuation.propose_completion(
            agent_id="agent-a",
            task_id=task.id,
            verifier=None,
            author_family="family-a",
            catalog=_catalog(),
        )
        assert is_ok(missing)
        assert missing.value.complete is False
        assert missing.value.verifier_passed is False

        failed = continuation.propose_completion(
            agent_id="agent-a",
            task_id=task.id,
            verifier=_failing_verifier(),
            author_family="family-a",
            catalog=_catalog(),
        )
        assert is_ok(failed)
        assert failed.value.complete is False
        assert failed.value.verifier_passed is False
        assert failed.value.reason == "verifier_failed"
        assert failed.value.model_substituted is False

        passed = continuation.propose_completion(
            agent_id="agent-a",
            task_id=task.id,
            verifier=_passing_verifier(),
            author_family="family-a",
            catalog=_catalog(),
        )
        assert is_ok(passed)
        assert passed.value.complete is True
        assert passed.value.verifier_passed is True
        assert passed.value.verifier_ref is not None
        assert passed.value.verifier_ref.startswith("fp1:sha256:")
    finally:
        journal.close()
        substrate.close()


def test_model_authored_outcome_does_not_substitute(tmp_path: Path) -> None:
    continuation, owner, substrate, journal, mission_id = _controller(tmp_path)
    try:
        _declare_bounds(continuation, journal, max_consecutive=4, budget=4)
        graph = continuation.dispatcher.store.for_mission(mission_id)
        assert graph is not None
        task = graph.tasks[0]
        assert is_ok(
            continuation.attach_run(
                agent_id="agent-a",
                owner=owner,
                mission_id=task.mission_id,
                task_id=task.id,
            )
        )
        substituted = continuation.propose_completion(
            agent_id="agent-a",
            task_id=task.id,
            verifier=_passing_verifier(),
            author_family="family-a",
            catalog=_catalog(),
            model_authored_outcome={"complete": True, "passed": True},
        )
        assert is_ok(substituted)
        assert substituted.value.complete is False
        assert substituted.value.model_substituted is True
        assert substituted.value.verifier_passed is False
    finally:
        journal.close()
        substrate.close()


def test_agent_stop_block_stop_returns_to_next_ready_task(tmp_path: Path) -> None:
    continuation, owner, substrate, journal, mission_id = _controller(tmp_path)
    try:
        _declare_bounds(continuation, journal, max_consecutive=4, budget=4)
        assert is_ok(continuation.hooks.register_handler("agent_stop", _block_stop))
        graph = continuation.dispatcher.store.for_mission(mission_id)
        assert graph is not None
        first = graph.tasks[0]
        second = graph.tasks[1]
        dispatched = continuation.dispatcher.dispatch_task(
            task_id=first.id,
            holder_agent_id="agent-a",
        )
        assert is_ok(dispatched)
        assert is_ok(
            continuation.attach_run(
                agent_id="agent-a",
                owner=owner,
                mission_id=first.mission_id,
                task_id=first.id,
            )
        )
        outcome = continuation.on_agent_stop("agent-a")
        assert is_ok(outcome)
        assert outcome.value.decision is HookResultDecision.BLOCK_STOP
        assert outcome.value.continued is True
        assert outcome.value.stopped is False
        assert outcome.value.invented_task is False
        assert outcome.value.next_task is not None
        assert outcome.value.next_task.id == second.id
        assert outcome.value.next_task.id != first.id
        run = continuation.run_state("agent-a")
        assert run is not None
        assert run.stopped is False
        assert run.current_task_id == second.id
    finally:
        journal.close()
        substrate.close()


def test_bounds_come_only_from_registry_keys(tmp_path: Path) -> None:
    continuation, _owner, substrate, journal, _mission_id = _controller(tmp_path)
    try:
        undeclared = continuation.resolve_bounds()
        assert is_refusal(undeclared)
        _declare_bounds(continuation, journal, max_consecutive=2, budget=5)
        bounds = continuation.resolve_bounds()
        assert is_ok(bounds)
        assert bounds.value.source_keys == CONTINUATION_BOUND_KEYS
        assert bounds.value.max_consecutive_key == CONTINUATION_MAX_CONSECUTIVE_KEY
        assert bounds.value.budget_key == CONTINUATION_BUDGET_KEY
        assert bounds.value.escalation_target_key == CONTINUATION_ESCALATION_TARGET_KEY
        assert continuation.bound_keys == CONTINUATION_BOUND_KEYS
        max_value = continuation.variables.get_value(CONTINUATION_MAX_CONSECUTIVE_KEY)
        budget_value = continuation.variables.get_value(CONTINUATION_BUDGET_KEY)
        target_value = continuation.variables.get_value(CONTINUATION_ESCALATION_TARGET_KEY)
        assert is_ok(max_value) and max_value.value == 2
        assert is_ok(budget_value) and budget_value.value == 5
        assert is_ok(target_value) and target_value.value == "quant_mailbox"
        assert max_value.value != CONTINUATION_UNDECLARED_VALUE
    finally:
        journal.close()
        substrate.close()


def test_budget_exhaustion_escalates_to_quant_mailbox_and_stops(tmp_path: Path) -> None:
    continuation, owner, substrate, journal, mission_id = _controller(tmp_path)
    try:
        _declare_bounds(continuation, journal, max_consecutive=8, budget=0)
        assert is_ok(continuation.hooks.register_handler("agent_stop", _block_stop))
        graph = continuation.dispatcher.store.for_mission(mission_id)
        assert graph is not None
        first = graph.tasks[0]
        assert is_ok(
            continuation.dispatcher.dispatch_task(
                task_id=first.id,
                holder_agent_id="agent-a",
            )
        )
        assert is_ok(
            continuation.attach_run(
                agent_id="agent-a",
                owner=owner,
                mission_id=first.mission_id,
                task_id=first.id,
            )
        )
        invented = continuation.invent_task(agent_id="agent-a")
        assert is_refusal(invented)
        assert invented.context["invented_task"] is False
        outcome = continuation.on_agent_stop("agent-a")
        assert is_ok(outcome)
        assert outcome.value.continued is False
        assert outcome.value.stopped is True
        assert outcome.value.escalated is True
        assert outcome.value.invented_task is False
        assert outcome.value.reason == "continuation_budget_exhausted"
        assert outcome.value.escalation is not None
        envelope = outcome.value.escalation.envelope
        assert envelope.to_actor == owner.actor_id
        assert envelope.kind is MessageKind.NOTIFY
        assert isinstance(envelope.body, Mapping)
        assert envelope.body["invented_task"] is False
        assert envelope.body["escalation_target_key"] == CONTINUATION_ESCALATION_TARGET_KEY
        assert envelope.body["source_keys"] == list(CONTINUATION_BOUND_KEYS)
        mailbox = continuation.mailboxes.mailbox_for(owner)
        assert mailbox is not None
        assert mailbox.record_for(envelope.msg_id) is not None
        run = continuation.run_state("agent-a")
        assert run is not None and run.stopped is True
        again = continuation.on_agent_stop("agent-a")
        assert is_refusal(again)
    finally:
        journal.close()
        substrate.close()


def test_no_ready_task_does_not_invent_work(tmp_path: Path) -> None:
    continuation, owner, substrate, journal, mission_id = _controller(tmp_path)
    try:
        _declare_bounds(continuation, journal, max_consecutive=8, budget=8)
        assert is_ok(continuation.hooks.register_handler("agent_stop", _block_stop))
        graph = continuation.dispatcher.store.for_mission(mission_id)
        assert graph is not None
        for task in graph.tasks:
            dispatched = continuation.dispatcher.dispatch_task(
                task_id=task.id,
                holder_agent_id="agent-a",
            )
            assert is_ok(dispatched)
            graph = continuation.dispatcher.store.for_mission(task.mission_id)
            assert graph is not None
        first = graph.tasks[0]
        assert is_ok(
            continuation.attach_run(
                agent_id="agent-a",
                owner=owner,
                mission_id=first.mission_id,
                task_id=first.id,
            )
        )
        fill = continuation.on_agent_stop("agent-a", invent_task=True)
        assert is_refusal(fill)
        outcome = continuation.on_agent_stop("agent-a")
        assert is_ok(outcome)
        assert outcome.value.continued is False
        assert outcome.value.stopped is True
        assert outcome.value.escalated is False
        assert outcome.value.invented_task is False
        assert outcome.value.reason == "no_ready_task"
        assert outcome.value.next_task is None
    finally:
        journal.close()
        substrate.close()


def test_agent_stop_observe_ends_the_run(tmp_path: Path) -> None:
    continuation, owner, substrate, journal, mission_id = _controller(tmp_path)
    try:
        _declare_bounds(continuation, journal, max_consecutive=8, budget=8)
        graph = continuation.dispatcher.store.for_mission(mission_id)
        assert graph is not None
        first = graph.tasks[0]
        assert is_ok(
            continuation.attach_run(
                agent_id="agent-a",
                owner=owner,
                mission_id=first.mission_id,
                task_id=first.id,
            )
        )
        outcome = continuation.on_agent_stop("agent-a")
        assert is_ok(outcome)
        assert outcome.value.decision is HookResultDecision.OBSERVE
        assert outcome.value.continued is False
        assert outcome.value.stopped is True
        assert outcome.value.escalated is False
    finally:
        journal.close()
        substrate.close()


def test_example_script() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "continuation_usage.py"
    namespace = runpy.run_path(str(path), run_name="__main__")
    assert namespace["main"] is not None
