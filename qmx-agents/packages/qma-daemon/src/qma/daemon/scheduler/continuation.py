"""Verified Task Graph continuation within registered bounds (CT-49; FR-Q63).

A Task is not complete until AD-10's deterministic verifier passes — a
model-authored outcome never substitutes. ``agent_stop`` returning ``block_stop``
returns the Agent to the next ready Task in its Mission's Task Graph rather than
ending the run. Cap, budget, and escalation target are read only from
``registry:continuation.max_consecutive``, ``registry:continuation.budget``, and
``registry:continuation.escalation_target``. Exhaustion escalates to the Agent's
Quant Mailbox and stops; no Task is invented to fill remaining budget.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from qma.core.ontology import ActorId, Quant
from qma.core.ontology.continuation import (
    CONTINUATION_BOUND_KEYS,
    CONTINUATION_BUDGET_KEY,
    CONTINUATION_ESCALATION_TARGET_KEY,
    CONTINUATION_MAX_CONSECUTIVE_KEY,
    ContinuationBounds,
    parse_continuation_bounds,
    refuse_invented_continuation_task,
    refuse_model_authored_completion,
)
from qma.core.plugins.hooks import HookImplementationKind
from qma.core.ports.model import DeploymentRecord
from qma.core.vocabulary.enums import HookControl, HookResultDecision, ModelClass
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.hooks.verifiers import (
    CompletionGateOutcome,
    DeterministicVerifier,
    evaluate_required_verifier_gate,
)
from qma.daemon.journal.variables import GovernedVariableRegistry
from qma.daemon.taskgraph.dispatcher import DispatchDecision, TaskGraphDispatcher
from qma.daemon.taskgraph.records import TaskRecord
from qma.wire.correlation import CorrelationMintOrigin, mint_correlation_id
from qmf.core import Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

if TYPE_CHECKING:
    from qma.daemon.bus.mailbox import DeliveryRecord, MailboxStore

__all__ = [
    "CONTINUATION_BOUND_KEYS",
    "CONTINUATION_BUDGET_KEY",
    "CONTINUATION_ESCALATION_TARGET_KEY",
    "CONTINUATION_MAX_CONSECUTIVE_KEY",
    "AgentContinuation",
    "AgentRunState",
    "AgentStopOutcome",
    "TaskCompletionVerdict",
]


_AGENT_STOP: Final[str] = HookControl.AGENT_STOP.value
_ESCALATION_KIND: Final[str] = "notify"
_EXHAUSTED_REASON: Final[str] = "continuation_budget_exhausted"
_NO_READY_REASON: Final[str] = "no_ready_task"
_OBSERVE_REASON: Final[str] = "agent_stop_observe"


def _mailbox_store() -> MailboxStore:
    from qma.daemon.bus.mailbox import MailboxStore as _MailboxStore  # noqa: PLC0415

    return _MailboxStore()


@dataclass(frozen=True, slots=True)
class TaskCompletionVerdict:
    """Verifier-gated completion: the Task is complete only when the verifier passed."""

    complete: bool
    verifier_passed: bool
    model_substituted: bool
    reason: str
    verifier_ref: str | None = None
    gate: CompletionGateOutcome | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "complete": self.complete,
            "verifier_passed": self.verifier_passed,
            "model_substituted": self.model_substituted,
            "reason": self.reason,
            "verifier_ref": self.verifier_ref,
        }
        if self.gate is not None:
            payload["gate"] = dict(self.gate.to_payload())
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class AgentStopOutcome:
    """Result of ``agent_stop``: continue, stop, or escalate — never invent a Task."""

    decision: HookResultDecision
    continued: bool
    stopped: bool
    escalated: bool
    invented_task: bool
    consecutive: int
    budget_used: int
    reason: str
    next_task: TaskRecord | None = None
    dispatch: DispatchDecision | None = None
    escalation: DeliveryRecord | None = None
    bounds: ContinuationBounds | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "decision": self.decision.value,
            "continued": self.continued,
            "stopped": self.stopped,
            "escalated": self.escalated,
            "invented_task": self.invented_task,
            "consecutive": self.consecutive,
            "budget_used": self.budget_used,
            "reason": self.reason,
        }
        if self.next_task is not None:
            payload["next_task_id"] = self.next_task.id
        if self.dispatch is not None:
            payload["dispatch"] = dict(self.dispatch.to_payload())
        if self.escalation is not None:
            payload["escalation"] = dict(self.escalation.to_payload())
        if self.bounds is not None:
            payload["bounds"] = dict(self.bounds.to_payload())
        return MappingProxyType(payload)


@dataclass
class AgentRunState:
    """Per-Agent continuation counters for one Mission Task Graph run."""

    agent_id: str
    owner: ActorId
    mission_id: str
    current_task_id: str | None = None
    consecutive: int = 0
    budget_used: int = 0
    stopped: bool = False
    last_reason: str | None = None


@dataclass
class AgentContinuation:
    """Daemon-owned Agent-run continuation under the three registry bounds."""

    _dispatcher: TaskGraphDispatcher = field(default_factory=TaskGraphDispatcher)
    _mailboxes: MailboxStore = field(default_factory=_mailbox_store)
    _variables: GovernedVariableRegistry = field(
        default_factory=GovernedVariableRegistry.with_builtins
    )
    _hooks: HookRegistry = field(default_factory=HookRegistry)
    _runs: dict[str, AgentRunState] = field(default_factory=dict[str, AgentRunState])
    _quants: dict[str, Quant] = field(default_factory=dict[str, Quant])

    @property
    def dispatcher(self) -> TaskGraphDispatcher:
        return self._dispatcher

    @property
    def mailboxes(self) -> MailboxStore:
        return self._mailboxes

    @property
    def variables(self) -> GovernedVariableRegistry:
        return self._variables

    @property
    def hooks(self) -> HookRegistry:
        return self._hooks

    @property
    def bound_keys(self) -> tuple[str, str, str]:
        return CONTINUATION_BOUND_KEYS

    def register_quant(self, quant: Quant) -> Result[Quant]:
        """Open the Quant Mailbox used as the continuation escalation target."""
        opened = self._mailboxes.open_for_quant(quant)
        if is_refusal(opened):
            return opened
        self._quants[quant.actor_id.value] = quant
        return Ok(quant)

    def attach_run(
        self,
        *,
        agent_id: str,
        owner: Quant | ActorId,
        mission_id: str,
        task_id: str | None = None,
    ) -> Result[AgentRunState]:
        """Bind an Agent run to a Mission Task Graph. Does not mint Tasks."""
        if not agent_id:
            return invalid_input("agent_id", "continuation requires an Agent id")
        if not mission_id:
            return invalid_input("mission_id", "continuation is scoped to a Mission Task Graph")
        owner_id = owner.actor_id if isinstance(owner, Quant) else owner
        if isinstance(owner, Quant):
            registered = self.register_quant(owner)
            if is_refusal(registered):
                return registered
        run = AgentRunState(
            agent_id=agent_id,
            owner=owner_id,
            mission_id=mission_id,
            current_task_id=task_id,
        )
        self._runs[agent_id] = run
        self._mailboxes.mark_agent_running(owner_id, agent_id)
        return Ok(run)

    def run_state(self, agent_id: str) -> AgentRunState | None:
        return self._runs.get(agent_id)

    def resolve_bounds(self) -> Result[ContinuationBounds]:
        """Read continuation ceilings from the three registry keys only."""
        values: dict[str, object] = {}
        for key in CONTINUATION_BOUND_KEYS:
            got = self._variables.get_value(key)
            if is_refusal(got):
                return got
            values[key] = got.value
        return parse_continuation_bounds(values)

    def invent_task(self, *, agent_id: str | None = None) -> Result[TaskRecord]:
        """Always refuse — exhaustion never invents work to fill remaining budget."""
        extra: dict[str, object] = {}
        if agent_id is not None:
            extra["agent_id"] = agent_id
        return refuse_invented_continuation_task(**extra)

    def propose_completion(
        self,
        *,
        agent_id: str,
        task_id: str,
        verifier: DeterministicVerifier | None,
        payload: Mapping[str, object] | None = None,
        author_family: str | None,
        catalog: Sequence[DeploymentRecord] = (),
        model_class: ModelClass | str = ModelClass.WORKHORSE_GENERAL,
        model_authored_outcome: object = None,
    ) -> Result[TaskCompletionVerdict]:
        """Complete a Task only when the deterministic verifier has passed."""
        _ = (agent_id, task_id)
        if model_authored_outcome is not None:
            return Ok(
                TaskCompletionVerdict(
                    complete=False,
                    verifier_passed=False,
                    model_substituted=True,
                    reason="model_authored_outcome",
                )
            )
        if verifier is None:
            return Ok(
                TaskCompletionVerdict(
                    complete=False,
                    verifier_passed=False,
                    model_substituted=False,
                    reason="verifier_missing",
                )
            )
        if verifier.kind not in {
            HookImplementationKind.CALLABLE,
            HookImplementationKind.SUBPROCESS,
        }:
            return refuse_model_authored_completion(source=verifier.kind)
        gated = evaluate_required_verifier_gate(
            "before_task_complete",
            verifier=verifier,
            payload=payload,
            author_family=author_family,
            catalog=catalog,
            model_class=model_class,
        )
        if is_refusal(gated):
            return gated
        outcome = gated.value
        passed = (
            outcome.result.decision is HookResultDecision.ALLOW
            and outcome.result.reason == "verifier_passed"
        )
        return Ok(
            TaskCompletionVerdict(
                complete=passed,
                verifier_passed=passed,
                model_substituted=False,
                reason=outcome.result.reason,
                verifier_ref=outcome.verifier_ref,
                gate=outcome,
            )
        )

    def on_agent_stop(
        self,
        agent_id: str,
        *,
        invent_task: bool = False,
        payload: Mapping[str, object] | None = None,
    ) -> Result[AgentStopOutcome]:
        """Honor ``block_stop`` by dispatching the next ready Task, or escalate."""
        if invent_task:
            return refuse_invented_continuation_task(agent_id=agent_id, invent_task=True)
        run = self._runs.get(agent_id)
        if run is None:
            return invalid_input("agent_id", "unknown Agent run", given=agent_id)
        if run.stopped:
            return policy_rejection(
                "continuation",
                "a stopped Agent run does not continue (CT-49; FR-Q63)",
                agent_id=agent_id,
            )
        control = self._hooks.evaluate_control(_AGENT_STOP, payload=payload)
        if is_refusal(control):
            return control
        decision = control.value.decision
        if decision is not HookResultDecision.BLOCK_STOP:
            return Ok(self._stop(run, decision=decision, reason=_OBSERVE_REASON))
        bounds = self.resolve_bounds()
        if is_refusal(bounds):
            self._stop(run, decision=decision, reason="bounds_undeclared")
            return bounds
        resolved = bounds.value
        if resolved.exhausted(consecutive=run.consecutive, budget_used=run.budget_used):
            return self._escalate(run, resolved)
        nxt = self._next_ready_task(run)
        if nxt is None:
            return Ok(
                self._stop(
                    run,
                    decision=decision,
                    reason=_NO_READY_REASON,
                    bounds=resolved,
                )
            )
        dispatched = self._dispatcher.dispatch_task(
            task_id=nxt.id,
            holder_agent_id=run.agent_id,
        )
        if is_refusal(dispatched):
            return dispatched
        run.consecutive += 1
        run.budget_used += 1
        run.current_task_id = dispatched.value.task.id
        run.last_reason = "block_stop_continue"
        return Ok(
            AgentStopOutcome(
                decision=decision,
                continued=True,
                stopped=False,
                escalated=False,
                invented_task=False,
                consecutive=run.consecutive,
                budget_used=run.budget_used,
                reason="block_stop_continue",
                next_task=dispatched.value.task,
                dispatch=dispatched.value,
                bounds=resolved,
            )
        )

    def _next_ready_task(self, run: AgentRunState) -> TaskRecord | None:
        graph = self._dispatcher.store.for_mission(run.mission_id)
        if graph is None:
            return None
        for task in graph.ready_tasks():
            if task.id != run.current_task_id:
                return task
        return None

    def _stop(
        self,
        run: AgentRunState,
        *,
        decision: HookResultDecision,
        reason: str,
        bounds: ContinuationBounds | None = None,
        escalated: bool = False,
        escalation: DeliveryRecord | None = None,
    ) -> AgentStopOutcome:
        run.stopped = True
        run.last_reason = reason
        self._mailboxes.mark_agent_stopped(run.owner, run.agent_id)
        return AgentStopOutcome(
            decision=decision,
            continued=False,
            stopped=True,
            escalated=escalated,
            invented_task=False,
            consecutive=run.consecutive,
            budget_used=run.budget_used,
            reason=reason,
            escalation=escalation,
            bounds=bounds,
        )

    def _escalate(
        self,
        run: AgentRunState,
        bounds: ContinuationBounds,
    ) -> Result[AgentStopOutcome]:
        minted = mint_correlation_id(
            origin=CorrelationMintOrigin.DAEMON_LIFECYCLE,
            correlation_id=f"continuation:{run.agent_id}:{run.budget_used}",
        )
        if is_refusal(minted):
            self._stop(
                run,
                decision=HookResultDecision.BLOCK_STOP,
                reason=_EXHAUSTED_REASON,
                bounds=bounds,
            )
            return minted
        envelope: dict[str, object] = {
            "msg_id": f"continuation-escalation:{run.agent_id}",
            "from": run.owner.value,
            "to": run.owner.value,
            "kind": _ESCALATION_KIND,
            "correlation_id": minted.value.correlation_id,
            "mission_ref": run.mission_id,
            "body": {
                "reason": _EXHAUSTED_REASON,
                "invented_task": False,
                "consecutive": run.consecutive,
                "budget_used": run.budget_used,
                "escalation_target": bounds.escalation_target,
                "escalation_target_key": bounds.escalation_target_key,
                "source_keys": list(bounds.source_keys),
                "max_consecutive_key": bounds.max_consecutive_key,
                "budget_key": bounds.budget_key,
            },
        }
        if run.current_task_id is not None:
            envelope["task_ref"] = run.current_task_id
        sent = self._mailboxes.send(envelope)
        if is_refusal(sent):
            self._stop(
                run,
                decision=HookResultDecision.BLOCK_STOP,
                reason=_EXHAUSTED_REASON,
                bounds=bounds,
            )
            return sent
        return Ok(
            self._stop(
                run,
                decision=HookResultDecision.BLOCK_STOP,
                reason=_EXHAUSTED_REASON,
                bounds=bounds,
                escalated=True,
                escalation=sent.value,
            )
        )
