"""Durable ``ask`` and ``defer`` control outcomes (FR-Q33; CT-41; CT-48; AD-10).

``ask`` journals exactly one ``approval_request`` to the Mission ``approval_route``
or owning Quant mailbox target. Operator-routed asks materialize the operator
approval queue projection; Quant-routed records carry the CT-48 target only —
no mailbox delivery or wakes. Escalation re-emits once then denies with
``ask_escalation_exhausted``. Autonomous Sessions without an operator final hop
deny with ``no_interactive_authority``.

``defer`` parks durably, releases ``environment_lease``, retains ``dispatch_lease``
(no reassignment), and re-runs the full hook chain on resume. Unresolved
ask/defer never hold an ``environment_lease``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final
from uuid import uuid4

from qma.core.plugins.hooks import HookResult, HookSource, build_hook_result
from qma.core.vocabulary.enums import (
    AskOnTimeout,
    HookResultDecision,
    MessageKind,
    SessionAutonomy,
)
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.journal.variables import registry_key
from qma.daemon.ledgers.task import TaskLedgerStore
from qma.daemon.taskgraph.dispatcher import TaskGraphStore
from qma.daemon.taskgraph.records import RESERVED_APPROVAL_ROUTE_OPERATOR
from qmf.core import Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "APPROVAL_REQUEST_JOURNAL_EVENT",
    "ASK_ESCALATION_EXHAUSTED_REASON",
    "ASK_TIMEOUT_KEY",
    "NO_INTERACTIVE_AUTHORITY_REASON",
    "ON_TIMEOUT_KEY",
    "ApprovalRequestRecord",
    "ApprovalTargetKind",
    "AskOutcome",
    "AskSuspension",
    "ControlOutcomeController",
    "DeferOutcome",
    "DeferParking",
    "OperatorApprovalQueueProjection",
    "resolve_ask_route",
]


ASK_TIMEOUT_KEY: Final[str] = registry_key("mission.ask_timeout")
ON_TIMEOUT_KEY: Final[str] = registry_key("mission.on_timeout")
ASK_ESCALATION_EXHAUSTED_REASON: Final[str] = "ask_escalation_exhausted"
NO_INTERACTIVE_AUTHORITY_REASON: Final[str] = "no_interactive_authority"
APPROVAL_REQUEST_JOURNAL_EVENT: Final[str] = "message.approval_request"


class ApprovalTargetKind(StrEnum):
    """Where an ``approval_request`` is addressed (FR-Q33; AD-10 / AD-12)."""

    OPERATOR_QUEUE = "operator_approval_queue"
    QUANT_MAILBOX = "quant_mailbox"


@dataclass(frozen=True, slots=True)
class ApprovalRequestRecord:
    """One journaled CT-48 ``approval_request`` — target only, no delivery/wakes."""

    msg_id: str
    from_actor: str
    kind: str
    correlation_id: str
    mission_ref: str
    body: Mapping[str, object]
    ask_timeout_key: str
    on_timeout_key: str
    on_timeout: AskOnTimeout
    target_kind: ApprovalTargetKind
    journal_seq: int
    to_actor: str | None = None
    task_ref: str | None = None
    causation_id: str | None = None
    priority: int = 0
    created_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "body", MappingProxyType(dict(self.body)))
        if self.kind != MessageKind.APPROVAL_REQUEST.value:
            msg = "ApprovalRequestRecord.kind must be approval_request (CT-48; FR-Q33)"
            raise ValueError(msg)
        if self.ask_timeout_key != ASK_TIMEOUT_KEY:
            msg = f"ask_timeout must cite {ASK_TIMEOUT_KEY!r} (FR-Q33)"
            raise ValueError(msg)
        if self.on_timeout_key != ON_TIMEOUT_KEY:
            msg = f"on_timeout must cite {ON_TIMEOUT_KEY!r} (FR-Q33)"
            raise ValueError(msg)
        if self.target_kind is ApprovalTargetKind.OPERATOR_QUEUE and self.to_actor is not None:
            msg = "operator-routed approval_request carries no Quant mailbox to (FR-Q33)"
            raise ValueError(msg)
        if self.target_kind is ApprovalTargetKind.QUANT_MAILBOX and not self.to_actor:
            msg = "Quant-routed approval_request requires CT-48 to target (FR-Q33)"
            raise ValueError(msg)

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "msg_id": self.msg_id,
            "from": self.from_actor,
            "kind": self.kind,
            "correlation_id": self.correlation_id,
            "mission_ref": self.mission_ref,
            "body": dict(self.body),
            "ask_timeout": self.ask_timeout_key,
            "on_timeout_key": self.on_timeout_key,
            "on_timeout": self.on_timeout.value,
            "target_kind": self.target_kind.value,
            "journal_seq": self.journal_seq,
            "priority": self.priority,
            # Explicitly absent delivery/wake surface for this story.
            "delivery_implemented": False,
            "wake_implemented": False,
        }
        if self.to_actor is not None:
            payload["to"] = self.to_actor
        if self.task_ref is not None:
            payload["task_ref"] = self.task_ref
        if self.causation_id is not None:
            payload["causation_id"] = self.causation_id
        if self.created_at is not None:
            payload["created_at"] = self.created_at
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class AskSuspension:
    """Durable ask suspension — never holds ``environment_lease`` (FR-Q33)."""

    suspension_id: str
    event: str
    mission_id: str
    owning_quant: str
    approval_route: str | None
    request: ApprovalRequestRecord
    escalation_count: int = 0
    task_id: str | None = None
    environment_lease_held: bool = False
    resolved: bool = False
    resolution: HookResult | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "suspension_id": self.suspension_id,
            "event": self.event,
            "mission_id": self.mission_id,
            "owning_quant": self.owning_quant,
            "approval_route": self.approval_route,
            "request": dict(self.request.to_payload()),
            "escalation_count": self.escalation_count,
            "environment_lease_held": self.environment_lease_held,
            "resolved": self.resolved,
            "task_id": self.task_id,
        }
        if self.resolution is not None:
            payload["resolution"] = {
                "decision": self.resolution.decision.value,
                "reason": self.resolution.reason,
            }
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class DeferParking:
    """Durable defer parking — retains dispatch_lease, no env lease (FR-Q33)."""

    parking_id: str
    event: str
    mission_id: str
    task_id: str
    payload: Mapping[str, object]
    source: HookSource
    dispatch_lease_retained: bool = True
    environment_lease_held: bool = False
    reassignment_recorded: bool = False
    attempt_no_unchanged: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "parking_id": self.parking_id,
                "event": self.event,
                "mission_id": self.mission_id,
                "task_id": self.task_id,
                "payload": dict(self.payload),
                "source": self.source.value,
                "dispatch_lease_retained": self.dispatch_lease_retained,
                "environment_lease_held": self.environment_lease_held,
                "reassignment_recorded": self.reassignment_recorded,
                "attempt_no_unchanged": self.attempt_no_unchanged,
            }
        )


@dataclass(frozen=True, slots=True)
class AskOutcome:
    """Result of resolving a hook ``ask`` decision."""

    result: HookResult
    suspension: AskSuspension | None = None
    journaled_request: ApprovalRequestRecord | None = None

    @property
    def decision(self) -> HookResultDecision:
        return self.result.decision

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "decision": self.result.decision.value,
            "reason": self.result.reason,
        }
        if self.suspension is not None:
            payload["suspension"] = dict(self.suspension.to_payload())
        if self.journaled_request is not None:
            payload["journaled_request"] = dict(self.journaled_request.to_payload())
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class DeferOutcome:
    """Result of parking a hook ``defer`` decision."""

    result: HookResult
    parking: DeferParking
    environment_lease_released: bool

    @property
    def decision(self) -> HookResultDecision:
        return self.result.decision

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "decision": self.result.decision.value,
                "reason": self.result.reason,
                "parking": dict(self.parking.to_payload()),
                "environment_lease_released": self.environment_lease_released,
            }
        )


@dataclass
class OperatorApprovalQueueProjection:
    """Daemon-held operator approval queue — materializes on first operator ask."""

    materialized: bool = False
    _entries: list[ApprovalRequestRecord] = field(default_factory=list[ApprovalRequestRecord])

    @property
    def entries(self) -> tuple[ApprovalRequestRecord, ...]:
        return tuple(self._entries)

    def enqueue(self, request: ApprovalRequestRecord) -> ApprovalRequestRecord:
        if not self.materialized:
            self.materialized = True
        self._entries.append(request)
        return request

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "materialized": self.materialized,
                "entries": [dict(e.to_payload()) for e in self._entries],
            }
        )


def resolve_ask_route(
    *,
    approval_route: str | None,
    owning_quant: str,
) -> tuple[ApprovalTargetKind, str | None]:
    """Resolve Mission ``approval_route`` to operator queue or Quant mailbox target.

    Absent route → owning Quant mailbox. Reserved ``operator`` → operator queue.
    Any other value is treated as a Quant ``ActorId`` mailbox target (CT-48 ``to``).
    """
    if approval_route is None or approval_route == "":
        return ApprovalTargetKind.QUANT_MAILBOX, owning_quant
    if approval_route == RESERVED_APPROVAL_ROUTE_OPERATOR:
        return ApprovalTargetKind.OPERATOR_QUEUE, None
    return ApprovalTargetKind.QUANT_MAILBOX, approval_route


@dataclass
class ControlOutcomeController:
    """Daemon control surface for durable ask/defer outcomes (FR-Q33)."""

    task_store: TaskGraphStore | None = None
    ledgers: TaskLedgerStore | None = None
    _operator_queue: OperatorApprovalQueueProjection = field(
        default_factory=OperatorApprovalQueueProjection
    )
    _journal: list[ApprovalRequestRecord] = field(default_factory=list[ApprovalRequestRecord])
    _asks: dict[str, AskSuspension] = field(default_factory=dict[str, AskSuspension])
    _defers: dict[str, DeferParking] = field(default_factory=dict[str, DeferParking])
    _next_journal_seq: int = 1

    @property
    def operator_queue(self) -> OperatorApprovalQueueProjection:
        return self._operator_queue

    @property
    def journaled_requests(self) -> tuple[ApprovalRequestRecord, ...]:
        return tuple(self._journal)

    @property
    def pending_asks(self) -> tuple[AskSuspension, ...]:
        return tuple(s for s in self._asks.values() if not s.resolved)

    @property
    def parked_defers(self) -> tuple[DeferParking, ...]:
        return tuple(self._defers.values())

    def unresolved_holds_environment_lease(self) -> bool:
        """Invariant: no unresolved ask/defer holds an environment_lease."""
        return any(
            not suspension.resolved and suspension.environment_lease_held
            for suspension in self._asks.values()
        ) or any(parking.environment_lease_held for parking in self._defers.values())

    def persist_ask(
        self,
        *,
        event: str,
        mission_id: str,
        owning_quant: str,
        approval_route: str | None,
        on_timeout: AskOnTimeout | str,
        correlation_id: str,
        from_actor: str,
        session_autonomy: SessionAutonomy | str = SessionAutonomy.INTERACTIVE,
        task_id: str | None = None,
        body: Mapping[str, object] | None = None,
        reason: str = "ask",
    ) -> Result[AskOutcome]:
        """Persist an ``ask``: journal one approval_request or deny for autonomy."""
        try:
            autonomy = parse_closed(SessionAutonomy, session_autonomy)
            timeout_action = parse_closed(AskOnTimeout, on_timeout)
        except VocabularyError as exc:
            return invalid_input("ask", str(exc))

        if not correlation_id:
            return invalid_input(
                "correlation_id",
                "approval_request requires correlation_id (CT-48; FR-Q33)",
            )
        if not owning_quant:
            return invalid_input(
                "owning_quant",
                "ask requires the Mission owning Quant ActorId (FR-Q33)",
            )

        target_kind, to_actor = resolve_ask_route(
            approval_route=approval_route,
            owning_quant=owning_quant,
        )

        # Autonomous Session: ask only when final hop is reserved operator.
        if autonomy is SessionAutonomy.AUTONOMOUS:
            final_hop_operator = (
                approval_route == RESERVED_APPROVAL_ROUTE_OPERATOR
                and target_kind is ApprovalTargetKind.OPERATOR_QUEUE
            )
            if not final_hop_operator:
                denied = build_hook_result(
                    HookResultDecision.DENY,
                    reason=NO_INTERACTIVE_AUTHORITY_REASON,
                )
                return Ok(
                    AskOutcome(
                        result=denied,
                        suspension=None,
                        journaled_request=None,
                    )
                )

        # Unresolved ask never holds environment_lease.
        if task_id is not None and self.task_store is not None:
            self.task_store.release_environment_lease(task_id)

        request = self._journal_approval_request(
            from_actor=from_actor,
            to_actor=to_actor,
            target_kind=target_kind,
            mission_ref=mission_id,
            task_ref=task_id,
            correlation_id=correlation_id,
            on_timeout=timeout_action,
            body=body if body is not None else {"event": event, "reason": reason},
        )

        if target_kind is ApprovalTargetKind.OPERATOR_QUEUE:
            self._operator_queue.enqueue(request)

        suspension = AskSuspension(
            suspension_id=str(uuid4()),
            event=event,
            mission_id=mission_id,
            owning_quant=owning_quant,
            approval_route=approval_route,
            request=request,
            escalation_count=0,
            task_id=task_id,
            environment_lease_held=False,
            resolved=False,
        )
        self._asks[suspension.suspension_id] = suspension
        return Ok(
            AskOutcome(
                result=build_hook_result(HookResultDecision.ASK, reason=reason),
                suspension=suspension,
                journaled_request=request,
            )
        )

    def expire_ask_timeout(self, suspension_id: str) -> Result[AskOutcome]:
        """Apply ``registry:mission.on_timeout`` for one ask timeout expiry.

        ``escalate`` re-emits once and restarts the timeout; a second expiry
        resolves to ``deny`` with ``ask_escalation_exhausted``. ``deny`` resolves
        immediately. Never resolves to ``allow``.
        """
        suspension = self._asks.get(suspension_id)
        if suspension is None:
            return invalid_input(
                "suspension_id",
                "unknown ask suspension",
                given=suspension_id,
            )
        if suspension.resolved:
            return policy_rejection(
                "ask",
                "ask suspension is already resolved",
                suspension_id=suspension_id,
            )

        action = suspension.request.on_timeout
        if action is AskOnTimeout.DENY or suspension.escalation_count >= 1:
            denied = build_hook_result(
                HookResultDecision.DENY,
                reason=ASK_ESCALATION_EXHAUSTED_REASON
                if suspension.escalation_count >= 1
                else "ask_timeout_deny",
            )
            resolved = AskSuspension(
                suspension_id=suspension.suspension_id,
                event=suspension.event,
                mission_id=suspension.mission_id,
                owning_quant=suspension.owning_quant,
                approval_route=suspension.approval_route,
                request=suspension.request,
                escalation_count=suspension.escalation_count,
                task_id=suspension.task_id,
                environment_lease_held=False,
                resolved=True,
                resolution=denied,
            )
            self._asks[suspension_id] = resolved
            return Ok(AskOutcome(result=denied, suspension=resolved))

        # escalate: re-emit once into the same target, restart timeout once.
        reissued = self._journal_approval_request(
            from_actor=suspension.request.from_actor,
            to_actor=suspension.request.to_actor,
            target_kind=suspension.request.target_kind,
            mission_ref=suspension.request.mission_ref,
            task_ref=suspension.request.task_ref,
            correlation_id=suspension.request.correlation_id,
            on_timeout=suspension.request.on_timeout,
            body=dict(suspension.request.body),
            causation_id=suspension.request.msg_id,
            msg_id=suspension.request.msg_id,
        )
        if suspension.request.target_kind is ApprovalTargetKind.OPERATOR_QUEUE:
            self._operator_queue.enqueue(reissued)

        escalated = AskSuspension(
            suspension_id=suspension.suspension_id,
            event=suspension.event,
            mission_id=suspension.mission_id,
            owning_quant=suspension.owning_quant,
            approval_route=suspension.approval_route,
            request=reissued,
            escalation_count=1,
            task_id=suspension.task_id,
            environment_lease_held=False,
            resolved=False,
        )
        self._asks[suspension_id] = escalated
        return Ok(
            AskOutcome(
                result=build_hook_result(HookResultDecision.ASK, reason="ask_escalated"),
                suspension=escalated,
                journaled_request=reissued,
            )
        )

    def persist_defer(
        self,
        *,
        event: str,
        mission_id: str,
        task_id: str,
        payload: Mapping[str, object] | None = None,
        source: HookSource | str = HookSource.MISSION,
        reason: str = "defer",
    ) -> Result[DeferOutcome]:
        """Park work durably: release env lease, retain dispatch lease, no reassign."""
        if not task_id:
            return invalid_input("task_id", "defer requires a Task id (FR-Q33)")
        try:
            src = source if isinstance(source, HookSource) else parse_closed(HookSource, source)
        except VocabularyError as exc:
            return invalid_input("source", str(exc), given=repr(source))

        released = False
        if self.task_store is not None:
            if self.task_store.lease_for(task_id) is None:
                return policy_rejection(
                    "dispatch_lease",
                    "defer retains dispatch_lease; none held for Task (FR-Q33)",
                    task_id=task_id,
                )
            released = self.task_store.release_environment_lease(task_id)

        parking = DeferParking(
            parking_id=str(uuid4()),
            event=event,
            mission_id=mission_id,
            task_id=task_id,
            payload=dict(payload or {}),
            source=src,
            dispatch_lease_retained=True,
            environment_lease_held=False,
            reassignment_recorded=False,
            attempt_no_unchanged=True,
        )
        self._defers[parking.parking_id] = parking
        return Ok(
            DeferOutcome(
                result=build_hook_result(HookResultDecision.DEFER, reason=reason),
                parking=parking,
                environment_lease_released=released,
            )
        )

    def resume_defer(
        self,
        parking_id: str,
        registry: HookRegistry,
    ) -> Result[HookResult]:
        """Resume parked work by re-running the full hook chain (FR-Q33).

        Never reuses the prior defer decision; never writes a ``reassigned``
        ledger entry (dispatch_lease retained).
        """
        parking = self._defers.pop(parking_id, None)
        if parking is None:
            return invalid_input(
                "parking_id",
                "unknown defer parking",
                given=parking_id,
            )
        if self.task_store is not None:
            lease = self.task_store.lease_for(parking.task_id)
            if lease is None:
                return policy_rejection(
                    "dispatch_lease",
                    "resume requires retained dispatch_lease; reassignment is not resume "
                    "(FR-Q33; DEC-0308)",
                    task_id=parking.task_id,
                )
            # Resume must not invent an environment_lease; caller re-acquires.
            if self.task_store.environment_lease_for(parking.task_id) is not None:
                return policy_rejection(
                    "environment_lease",
                    "deferred work must not hold environment_lease at resume (FR-Q33)",
                    task_id=parking.task_id,
                )
            if self.ledgers is not None:
                resumed_ledger = self.ledgers.resume_from_defer(
                    task_id=parking.task_id,
                    dispatch_lease=lease,
                )
                if is_refusal(resumed_ledger):
                    return resumed_ledger

        # Full hook chain — fresh dispatch, never the parked defer decision.
        return registry.dispatch(
            parking.event,
            payload=dict(parking.payload),
            source=parking.source,
        )

    def _journal_approval_request(
        self,
        *,
        from_actor: str,
        to_actor: str | None,
        target_kind: ApprovalTargetKind,
        mission_ref: str,
        correlation_id: str,
        on_timeout: AskOnTimeout,
        body: Mapping[str, object],
        task_ref: str | None = None,
        causation_id: str | None = None,
        msg_id: str | None = None,
    ) -> ApprovalRequestRecord:
        seq = self._next_journal_seq
        self._next_journal_seq += 1
        record = ApprovalRequestRecord(
            msg_id=msg_id if msg_id is not None else str(uuid4()),
            from_actor=from_actor,
            to_actor=to_actor,
            kind=MessageKind.APPROVAL_REQUEST.value,
            correlation_id=correlation_id,
            mission_ref=mission_ref,
            task_ref=task_ref,
            causation_id=causation_id,
            body=dict(body),
            ask_timeout_key=ASK_TIMEOUT_KEY,
            on_timeout_key=ON_TIMEOUT_KEY,
            on_timeout=on_timeout,
            target_kind=target_kind,
            journal_seq=seq,
        )
        self._journal.append(record)
        return record
