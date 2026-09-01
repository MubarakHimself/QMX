"""Story 43.7 — durable ask and defer control outcomes (FR-Q33; CT-41; CT-48)."""

from __future__ import annotations

from qma.core.ontology import ActorId
from qma.core.plugins.hooks import HookEvent, HookResult, HookSource, build_hook_result
from qma.core.vocabulary.enums import (
    AskOnTimeout,
    HookResultDecision,
    MessageKind,
    SessionAutonomy,
    TaskMissionState,
)
from qma.daemon.envs.registry import EnvironmentLease
from qma.daemon.hooks import (
    APPROVAL_REQUEST_JOURNAL_EVENT,
    ASK_ESCALATION_EXHAUSTED_REASON,
    ASK_TIMEOUT_KEY,
    NO_INTERACTIVE_AUTHORITY_REASON,
    ON_TIMEOUT_KEY,
    ApprovalTargetKind,
    ControlOutcomeController,
    HookRegistry,
    resolve_ask_route,
)
from qma.daemon.taskgraph.dispatcher import TaskGraphStore
from qma.daemon.taskgraph.records import (
    RESERVED_APPROVAL_ROUTE_OPERATOR,
    DispatchLease,
    TaskGraph,
    TaskRecord,
)
from qmf.core import is_ok


def _owner() -> ActorId:
    minted = ActorId.mint("research", "lead")
    assert is_ok(minted)
    return minted.value


def _peer() -> ActorId:
    minted = ActorId.mint("research", "peer")
    assert is_ok(minted)
    return minted.value


def _store_with_leases(task_id: str = "task-1", mission_id: str = "mission-1") -> TaskGraphStore:
    owner = _owner()
    store = TaskGraphStore()
    task = TaskRecord(
        id=task_id,
        mission_id=mission_id,
        owner=owner,
        intent="work",
        state=TaskMissionState.RUNNING,
    )
    graph = TaskGraph(id="graph-1", mission_id=mission_id, tasks=(task,))
    store.materialize(graph)
    store.record_lease(
        DispatchLease(
            task_id=task_id,
            holder_agent_id="agent-1",
            mission_id=mission_id,
            owner=owner,
        )
    )
    store.record_environment_lease(
        EnvironmentLease(
            task_id=task_id,
            kind="docker",
            slot_id="slot-1",
            provider_id="local-docker",
        )
    )
    return store


def test_registry_keys_cited_not_numeric() -> None:
    assert ASK_TIMEOUT_KEY == "registry:mission.ask_timeout"
    assert ON_TIMEOUT_KEY == "registry:mission.on_timeout"
    assert APPROVAL_REQUEST_JOURNAL_EVENT == "message.approval_request"
    assert not any(ch.isdigit() for ch in ASK_TIMEOUT_KEY)
    assert not any(ch.isdigit() for ch in ON_TIMEOUT_KEY)


def test_ask_journals_one_operator_request_and_materializes_queue() -> None:
    controller = ControlOutcomeController(task_store=_store_with_leases())
    assert controller.operator_queue.materialized is False

    outcome = controller.persist_ask(
        event="before_tool",
        mission_id="mission-1",
        owning_quant=_owner().value,
        approval_route=RESERVED_APPROVAL_ROUTE_OPERATOR,
        on_timeout=AskOnTimeout.DENY,
        correlation_id="corr-op-1",
        from_actor="daemon",
        task_id="task-1",
    )
    assert is_ok(outcome)
    ask = outcome.value
    assert ask.decision is HookResultDecision.ASK
    assert ask.journaled_request is not None
    assert ask.journaled_request.kind == MessageKind.APPROVAL_REQUEST.value
    assert ask.journaled_request.target_kind is ApprovalTargetKind.OPERATOR_QUEUE
    assert ask.journaled_request.to_actor is None
    assert ask.journaled_request.ask_timeout_key == ASK_TIMEOUT_KEY
    assert ask.journaled_request.on_timeout_key == ON_TIMEOUT_KEY
    assert ask.journaled_request.on_timeout is AskOnTimeout.DENY
    assert ask.journaled_request.journal_seq == 1
    assert ask.journaled_request.to_payload()["delivery_implemented"] is False
    assert ask.journaled_request.to_payload()["wake_implemented"] is False

    # First operator-routed request materializes the queue projection.
    assert controller.operator_queue.materialized is True
    assert len(controller.operator_queue.entries) == 1
    assert len(controller.journaled_requests) == 1

    # Unresolved ask released environment_lease, retained dispatch_lease.
    assert controller.task_store is not None
    assert controller.task_store.environment_lease_for("task-1") is None
    assert controller.task_store.lease_for("task-1") is not None
    assert ask.suspension is not None
    assert ask.suspension.environment_lease_held is False
    assert controller.unresolved_holds_environment_lease() is False


def test_ask_quant_route_carries_ct48_target_without_delivery() -> None:
    peer = _peer()
    controller = ControlOutcomeController()
    outcome = controller.persist_ask(
        event="before_task_complete",
        mission_id="mission-2",
        owning_quant=_owner().value,
        approval_route=peer.value,
        on_timeout="escalate",
        correlation_id="corr-q-1",
        from_actor="daemon",
    )
    assert is_ok(outcome)
    request = outcome.value.journaled_request
    assert request is not None
    assert request.target_kind is ApprovalTargetKind.QUANT_MAILBOX
    assert request.to_actor == peer.value
    assert request.on_timeout is AskOnTimeout.ESCALATE
    # Operator queue stays unmaterialized for Quant-routed asks.
    assert controller.operator_queue.materialized is False
    assert controller.operator_queue.entries == ()
    payload = request.to_payload()
    assert payload["to"] == peer.value
    assert payload["delivery_implemented"] is False
    assert payload["wake_implemented"] is False


def test_ask_absent_route_targets_owning_quant_mailbox() -> None:
    owner = _owner()
    kind, target = resolve_ask_route(approval_route=None, owning_quant=owner.value)
    assert kind is ApprovalTargetKind.QUANT_MAILBOX
    assert target == owner.value

    controller = ControlOutcomeController()
    outcome = controller.persist_ask(
        event="before_tool",
        mission_id="mission-3",
        owning_quant=owner.value,
        approval_route=None,
        on_timeout=AskOnTimeout.DENY,
        correlation_id="corr-own-1",
        from_actor="daemon",
    )
    assert is_ok(outcome)
    assert outcome.value.journaled_request is not None
    assert outcome.value.journaled_request.to_actor == owner.value


def test_escalation_reemits_once_then_exhausts() -> None:
    controller = ControlOutcomeController()
    first = controller.persist_ask(
        event="before_tool",
        mission_id="mission-esc",
        owning_quant=_owner().value,
        approval_route=RESERVED_APPROVAL_ROUTE_OPERATOR,
        on_timeout=AskOnTimeout.ESCALATE,
        correlation_id="corr-esc",
        from_actor="daemon",
    )
    assert is_ok(first)
    suspension_id = first.value.suspension.suspension_id  # type: ignore[union-attr]
    assert len(controller.journaled_requests) == 1
    assert len(controller.operator_queue.entries) == 1

    escalated = controller.expire_ask_timeout(suspension_id)
    assert is_ok(escalated)
    assert escalated.value.decision is HookResultDecision.ASK
    assert escalated.value.suspension is not None
    assert escalated.value.suspension.escalation_count == 1
    assert escalated.value.suspension.resolved is False
    assert len(controller.journaled_requests) == 2
    assert len(controller.operator_queue.entries) == 2
    # Same approval_request identity re-emitted.
    assert (
        escalated.value.journaled_request is not None
        and escalated.value.journaled_request.msg_id == first.value.journaled_request.msg_id  # type: ignore[union-attr]
    )

    exhausted = controller.expire_ask_timeout(suspension_id)
    assert is_ok(exhausted)
    assert exhausted.value.decision is HookResultDecision.DENY
    assert exhausted.value.result.reason == ASK_ESCALATION_EXHAUSTED_REASON
    assert exhausted.value.suspension is not None
    assert exhausted.value.suspension.resolved is True
    # No third journal emit on exhaustion.
    assert len(controller.journaled_requests) == 2


def test_on_timeout_deny_resolves_on_first_expiry() -> None:
    controller = ControlOutcomeController()
    first = controller.persist_ask(
        event="before_tool",
        mission_id="mission-deny",
        owning_quant=_owner().value,
        approval_route=RESERVED_APPROVAL_ROUTE_OPERATOR,
        on_timeout=AskOnTimeout.DENY,
        correlation_id="corr-deny",
        from_actor="daemon",
    )
    assert is_ok(first)
    suspension_id = first.value.suspension.suspension_id  # type: ignore[union-attr]
    denied = controller.expire_ask_timeout(suspension_id)
    assert is_ok(denied)
    assert denied.value.decision is HookResultDecision.DENY
    assert denied.value.result.reason == "ask_timeout_deny"
    assert len(controller.journaled_requests) == 1


def test_autonomous_ask_denies_without_operator_route() -> None:
    controller = ControlOutcomeController()
    denied = controller.persist_ask(
        event="before_tool",
        mission_id="mission-auto",
        owning_quant=_owner().value,
        approval_route=_peer().value,
        on_timeout=AskOnTimeout.ESCALATE,
        correlation_id="corr-auto-1",
        from_actor="daemon",
        session_autonomy=SessionAutonomy.AUTONOMOUS,
    )
    assert is_ok(denied)
    assert denied.value.decision is HookResultDecision.DENY
    assert denied.value.result.reason == NO_INTERACTIVE_AUTHORITY_REASON
    assert denied.value.journaled_request is None
    assert denied.value.suspension is None
    assert controller.journaled_requests == ()
    assert controller.operator_queue.materialized is False

    # Absent route also denies under autonomous.
    absent = controller.persist_ask(
        event="before_tool",
        mission_id="mission-auto-2",
        owning_quant=_owner().value,
        approval_route=None,
        on_timeout=AskOnTimeout.DENY,
        correlation_id="corr-auto-2",
        from_actor="daemon",
        session_autonomy="autonomous",
    )
    assert is_ok(absent)
    assert absent.value.result.reason == NO_INTERACTIVE_AUTHORITY_REASON


def test_autonomous_ask_allowed_when_route_is_operator() -> None:
    controller = ControlOutcomeController()
    ok = controller.persist_ask(
        event="before_tool",
        mission_id="mission-auto-op",
        owning_quant=_owner().value,
        approval_route=RESERVED_APPROVAL_ROUTE_OPERATOR,
        on_timeout=AskOnTimeout.DENY,
        correlation_id="corr-auto-op",
        from_actor="daemon",
        session_autonomy=SessionAutonomy.AUTONOMOUS,
    )
    assert is_ok(ok)
    assert ok.value.decision is HookResultDecision.ASK
    assert ok.value.journaled_request is not None
    assert controller.operator_queue.materialized is True


def test_defer_releases_env_retains_dispatch_no_reassignment() -> None:
    store = _store_with_leases()
    controller = ControlOutcomeController(task_store=store)
    assert store.environment_lease_for("task-1") is not None
    assert store.lease_for("task-1") is not None

    deferred = controller.persist_defer(
        event="before_tool",
        mission_id="mission-1",
        task_id="task-1",
        payload={"tool": "read"},
        source=HookSource.MISSION,
    )
    assert is_ok(deferred)
    outcome = deferred.value
    assert outcome.decision is HookResultDecision.DEFER
    assert outcome.environment_lease_released is True
    assert outcome.parking.dispatch_lease_retained is True
    assert outcome.parking.environment_lease_held is False
    assert outcome.parking.reassignment_recorded is False
    assert outcome.parking.attempt_no_unchanged is True
    assert store.environment_lease_for("task-1") is None
    assert store.lease_for("task-1") is not None
    assert controller.unresolved_holds_environment_lease() is False


def test_resume_defer_reruns_full_hook_chain() -> None:
    store = _store_with_leases()
    controller = ControlOutcomeController(task_store=store)
    parked = controller.persist_defer(
        event="before_tool",
        mission_id="mission-1",
        task_id="task-1",
        payload={"tool": "write"},
    )
    assert is_ok(parked)
    parking_id = parked.value.parking.parking_id

    registry = HookRegistry()
    calls: list[str] = []

    def allow_handler(event: HookEvent) -> HookResult:
        calls.append(event.event)
        return build_hook_result(HookResultDecision.ALLOW, reason="resumed_fresh")

    assert is_ok(registry.register_handler("before_tool", allow_handler))

    resumed = controller.resume_defer(parking_id, registry)
    assert is_ok(resumed)
    assert resumed.value.decision is HookResultDecision.ALLOW
    assert resumed.value.reason == "resumed_fresh"
    assert calls == ["before_tool"]
    # Prior defer decision was not reused.
    assert resumed.value.decision is not HookResultDecision.DEFER
    # Parking consumed; dispatch lease still held (no reassignment).
    assert controller.parked_defers == ()
    assert store.lease_for("task-1") is not None
    assert store.environment_lease_for("task-1") is None


def test_unresolved_controls_never_hold_environment_lease() -> None:
    owner = _owner()
    store = TaskGraphStore()
    for task_id, mission_id, graph_id, slot in (
        ("t-ask", "mission-1", "graph-ask", "slot-ask"),
        ("t-defer", "m-2", "graph-defer", "slot-defer"),
    ):
        store.materialize(
            TaskGraph(
                id=graph_id,
                mission_id=mission_id,
                tasks=(
                    TaskRecord(
                        id=task_id,
                        mission_id=mission_id,
                        owner=owner,
                        intent="work",
                        state=TaskMissionState.RUNNING,
                    ),
                ),
            )
        )
        store.record_lease(
            DispatchLease(
                task_id=task_id,
                holder_agent_id=f"agent-{task_id}",
                mission_id=mission_id,
                owner=owner,
            )
        )
        store.record_environment_lease(
            EnvironmentLease(task_id=task_id, kind="docker", slot_id=slot)
        )

    controller = ControlOutcomeController(task_store=store)
    ask = controller.persist_ask(
        event="before_tool",
        mission_id="mission-1",
        owning_quant=owner.value,
        approval_route=RESERVED_APPROVAL_ROUTE_OPERATOR,
        on_timeout=AskOnTimeout.DENY,
        correlation_id="corr-hold",
        from_actor="daemon",
        task_id="t-ask",
    )
    defer = controller.persist_defer(
        event="before_memory_write",
        mission_id="m-2",
        task_id="t-defer",
    )
    assert is_ok(ask) and is_ok(defer)
    assert store.environment_lease_for("t-ask") is None
    assert store.environment_lease_for("t-defer") is None
    assert controller.unresolved_holds_environment_lease() is False
    for suspension in controller.pending_asks:
        assert suspension.environment_lease_held is False
    for parking in controller.parked_defers:
        assert parking.environment_lease_held is False

