"""Reconnect and gap-recovery orchestration (Story 24.8 / TN-10/11).

On a lost session the node refreshes and authenticates by credential
*reference*, re-verifies required capabilities, gap-replays fills and lifecycle
events (persisting them before healthy), reconciles outstanding commands, and
never resubmits a command. The receive frontier and the interpretation cursor
remain distinct objects — reconnect advances only the receive frontier;
interpretation re-fold is a separate boot step (DEC-0195, DEC-0190, DEC-0137).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    Instant,
    JournalSink,
    ObservationSink,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    SecretRef,
    SecretValue,
    TypedRefusal,
    is_refusal,
)
from qmf.venue.commands import SubmissionOutcome, UnknownTrigger
from qmf.venue.connection import AccountBinding, ConnectionManager
from qmf.venue.ctrader import InFlightResolution, SessionRecovery

from qmn.venue.port import VenueClientPort

__all__ = [
    "ReceiveFrontier",
    "ReconnectGapRecovery",
    "ReconnectPhase",
    "ReconnectReport",
    "RecoveredObservation",
]


_FILL_KINDS: Final[frozenset[str]] = frozenset({"fill", "execution-fill", "deal"})
_LIFECYCLE_KINDS: Final[frozenset[str]] = frozenset(
    {
        "lifecycle",
        "submission-acknowledgement",
        "cancel-acknowledgement",
        "expiry",
        "close-by-venue",
        "order",
    }
)
_PERSISTABLE_KINDS: Final[frozenset[str]] = _FILL_KINDS | _LIFECYCLE_KINDS


class ReconnectPhase(StrEnum):
    """Ordered reconnect phases; healthy is terminal and last (TN-10)."""

    AUTHENTICATE = "authenticate"
    VERIFY_CAPABILITIES = "verify-capabilities"
    GAP_REPLAY = "gap-replay"
    PERSIST_RECOVERED = "persist-recovered"
    RECONCILE_OUTSTANDING = "reconcile-outstanding"
    HEALTHY = "healthy"


@dataclass(frozen=True, slots=True)
class RecoveredObservation:
    """One fill or lifecycle event recovered during gap replay."""

    observation_id: str
    kind: str
    receive_wall_ns: int
    payload: Mapping[str, object]
    execution_id: str | None = None

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "observation_id": self.observation_id,
            "kind": self.kind,
            "receive_wall_ns": self.receive_wall_ns,
            "payload": dict(self.payload),
        }
        if self.execution_id is not None:
            body["execution_id"] = self.execution_id
        return MappingProxyType(body)


@dataclass
class ReceiveFrontier:
    """Receive-wall high-water mark of *recorded* observations.

    Distinct from the durable interpretation cursor: reconnect and gap-replay
    advance this frontier as evidence lands; interpretation commit stays a
    completed-slice act on the loop driver (DEC-0190, DEC-0195).
    """

    last_observation_id: str | None = None
    last_receive_wall_ns: int | None = None
    last_seen_execution_id: str | None = None
    recorded_count: int = 0

    def advance(
        self,
        *,
        observation_id: str,
        receive_wall_ns: int,
        execution_id: str | None = None,
    ) -> None:
        """Advance the receive high-water mark after a durable record."""
        self.last_observation_id = observation_id
        self.last_receive_wall_ns = receive_wall_ns
        self.recorded_count += 1
        if execution_id is not None and execution_id.strip() != "":
            self.last_seen_execution_id = execution_id.strip()

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "last_observation_id": self.last_observation_id,
                "last_receive_wall_ns": self.last_receive_wall_ns,
                "last_seen_execution_id": self.last_seen_execution_id,
                "recorded_count": self.recorded_count,
            }
        )


@dataclass(frozen=True, slots=True)
class ReconnectReport:
    """Outcome of one reconnect / gap-recovery run."""

    healthy: bool
    phases_completed: tuple[ReconnectPhase, ...]
    credential_ref_id: str
    capabilities: Mapping[str, object]
    recovered: tuple[Mapping[str, object], ...]
    outstanding_resolutions: tuple[InFlightResolution, ...]
    receive_frontier: Mapping[str, object]
    interpretation_cursor_observation_id: str | None
    commands_resubmitted: int
    correlation_evidence: Mapping[str, object]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "healthy": self.healthy,
                "phases_completed": [phase.value for phase in self.phases_completed],
                "credential_ref_id": self.credential_ref_id,
                "capabilities": dict(self.capabilities),
                "recovered": [dict(item) for item in self.recovered],
                "outstanding_resolutions": [
                    {
                        "command_id": item.command_id,
                        "outcome": item.outcome.value,
                        "trigger": item.trigger.value,
                    }
                    for item in self.outstanding_resolutions
                ],
                "receive_frontier": dict(self.receive_frontier),
                "interpretation_cursor_observation_id": (
                    self.interpretation_cursor_observation_id
                ),
                "commands_resubmitted": self.commands_resubmitted,
                "correlation_evidence": dict(self.correlation_evidence),
                "resubmits_command": SessionRecovery.resubmits_command,
            }
        )


@dataclass
class ReconnectGapRecovery:
    """Drive reconnect → verify → gap-replay → reconcile → healthy.

    Structural invariant: :attr:`commands_resubmitted` stays zero and
    :class:`~qmf.venue.ctrader.SessionRecovery` never resubmits (DEC-0137).
    """

    client: VenueClientPort
    credential_ref: SecretRef
    receive_frontier: ReceiveFrontier
    interpretation_cursor_observation_id: str | None = None
    connection_manager: ConnectionManager | None = None
    binding: AccountBinding | None = None
    observation_sink: ObservationSink[Mapping[str, object]] | None = None
    journal_sink: JournalSink[Mapping[str, object]] | None = None
    _recovery: SessionRecovery = field(default_factory=SessionRecovery)
    _commands_resubmitted: int = 0
    _healthy: bool = False
    _phases: list[ReconnectPhase] = field(default_factory=list[ReconnectPhase])

    @classmethod
    def try_create(
        cls,
        *,
        client: object,
        credential_ref: object,
        receive_frontier: object | None = None,
        interpretation_cursor_observation_id: object = None,
        connection_manager: object = None,
        binding: object = None,
        observation_sink: object = None,
        journal_sink: object = None,
    ) -> Result[ReconnectGapRecovery]:
        """Validate wiring. Credential handles are references — never values."""
        if not isinstance(client, VenueClientPort):
            return _invalid(
                "client",
                "reconnect drives a VenueClientPort",
                given=type(client).__name__,
            )
        if isinstance(credential_ref, SecretValue):
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "credential_ref",
                    "reason": "reconnect authenticates by credential reference; "
                    "a SecretValue must never cross this boundary",
                },
            )
        if not isinstance(credential_ref, SecretRef) or credential_ref.value.strip() == "":
            return _invalid(
                "credential_ref",
                "reconnect authenticates by an opaque SecretRef",
                given=repr(credential_ref),
            )
        frontier: ReceiveFrontier
        if receive_frontier is None:
            frontier = ReceiveFrontier()
        elif isinstance(receive_frontier, ReceiveFrontier):
            frontier = receive_frontier
        else:
            return _invalid(
                "receive_frontier",
                "receive frontier is a ReceiveFrontier instance",
                given=type(receive_frontier).__name__,
            )
        cursor_id: str | None
        if interpretation_cursor_observation_id is None:
            cursor_id = None
        elif (
            isinstance(interpretation_cursor_observation_id, str)
            and interpretation_cursor_observation_id.strip() != ""
        ):
            cursor_id = interpretation_cursor_observation_id.strip()
        else:
            return _invalid(
                "interpretation_cursor_observation_id",
                "interpretation cursor id is a non-empty token when supplied",
                given=repr(interpretation_cursor_observation_id),
            )
        cm: ConnectionManager | None
        if connection_manager is None:
            cm = None
        elif isinstance(connection_manager, ConnectionManager):
            cm = connection_manager
        else:
            return _invalid(
                "connection_manager",
                "when supplied, connection_manager must be a ConnectionManager",
                given=type(connection_manager).__name__,
            )
        bound: AccountBinding | None
        if binding is None:
            bound = None
        elif isinstance(binding, AccountBinding):
            if binding.secret_ref != credential_ref:
                return _invalid(
                    "binding",
                    "binding credential reference must equal the reconnect credential_ref",
                    binding_ref=binding.secret_ref.value,
                    credential_ref=credential_ref.value,
                )
            bound = binding
        else:
            return _invalid(
                "binding",
                "when supplied, binding must be an AccountBinding",
                given=type(binding).__name__,
            )
        if cm is not None and bound is None:
            return _invalid(
                "binding",
                "ConnectionManager re-auth requires an AccountBinding keyed by "
                "the same credential reference",
            )
        obs: ObservationSink[Mapping[str, object]] | None
        if observation_sink is None:
            obs = None
        elif isinstance(observation_sink, ObservationSink):
            obs = cast("ObservationSink[Mapping[str, object]]", observation_sink)
        else:
            return _invalid(
                "observation_sink",
                "when supplied, observation_sink must be an ObservationSink",
                given=type(observation_sink).__name__,
            )
        journal: JournalSink[Mapping[str, object]] | None
        if journal_sink is None:
            journal = None
        elif isinstance(journal_sink, JournalSink):
            journal = cast("JournalSink[Mapping[str, object]]", journal_sink)
        else:
            return _invalid(
                "journal_sink",
                "when supplied, journal_sink must be a JournalSink",
                given=type(journal_sink).__name__,
            )
        return Ok(
            cls(
                client=client,
                credential_ref=credential_ref,
                receive_frontier=frontier,
                interpretation_cursor_observation_id=cursor_id,
                connection_manager=cm,
                binding=bound,
                observation_sink=obs,
                journal_sink=journal,
            )
        )

    @property
    def healthy(self) -> bool:
        """Whether reconnect completed and declared the session healthy."""
        return self._healthy

    @property
    def commands_resubmitted(self) -> int:
        """Always zero — reconnect never resubmits a command (DEC-0137)."""
        return self._commands_resubmitted

    @property
    def resubmits_command(self) -> bool:
        return SessionRecovery.resubmits_command

    def run(
        self,
        *,
        recovered: object = (),
        outstanding_command_ids: object = (),
        correlation_instant: object | None = None,
    ) -> Result[ReconnectReport]:
        """Execute the full reconnect sequence; healthy only after persist + reconcile."""
        if SessionRecovery.resubmits_command:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "session_recovery",
                    "reason": "SessionRecovery.resubmits_command must remain False",
                },
            )
        self._healthy = False
        self._phases = []
        cursor_before = self.interpretation_cursor_observation_id

        auth = self._authenticate()
        if is_refusal(auth):
            return auth
        self._phases.append(ReconnectPhase.AUTHENTICATE)

        caps = self.client.verify_capabilities()
        if is_refusal(caps):
            return caps
        self._phases.append(ReconnectPhase.VERIFY_CAPABILITIES)
        capabilities = dict(caps.value)

        gap = self._gap_replay(recovered)
        if is_refusal(gap):
            return gap
        recovered_rows, gap_had_events = gap.value
        self._phases.append(ReconnectPhase.GAP_REPLAY)
        self._phases.append(ReconnectPhase.PERSIST_RECOVERED)

        resolved = self._recovery.on_disconnect(outstanding_command_ids)
        if is_refusal(resolved):
            return resolved
        # Reconcile = mark UNKNOWN / observe; never submit or resubmit.
        if self._commands_resubmitted != 0:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "commands_resubmitted",
                    "reason": "reconnect reconciled outstanding commands without "
                    "resubmission; a non-zero resubmit count is a bug",
                    "commands_resubmitted": self._commands_resubmitted,
                },
            )
        self._phases.append(ReconnectPhase.RECONCILE_OUTSTANDING)

        correlation = self._correlation_evidence(
            gap_had_events=gap_had_events,
            correlation_instant=correlation_instant,
            outstanding=resolved.value,
        )
        self._healthy = True
        self._phases.append(ReconnectPhase.HEALTHY)

        # Interpretation cursor must remain untouched by reconnect.
        if self.interpretation_cursor_observation_id != cursor_before:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "interpretation_cursor",
                    "reason": "reconnect must not advance the interpretation cursor; "
                    "receive frontier and interpretation cursor stay distinct",
                    "before": cursor_before,
                    "after": self.interpretation_cursor_observation_id,
                },
            )

        return Ok(
            ReconnectReport(
                healthy=True,
                phases_completed=tuple(self._phases),
                credential_ref_id=self.credential_ref.value,
                capabilities=MappingProxyType(capabilities),
                recovered=tuple(recovered_rows),
                outstanding_resolutions=resolved.value,
                receive_frontier=self.receive_frontier.as_mapping(),
                interpretation_cursor_observation_id=(
                    self.interpretation_cursor_observation_id
                ),
                commands_resubmitted=self._commands_resubmitted,
                correlation_evidence=correlation,
            )
        )

    def _authenticate(self) -> Result[SecretRef]:
        """Refresh/authenticate by credential reference only."""
        if self.connection_manager is not None and self.binding is not None:
            # Lost session: drop any stale held value, then re-open by reference.
            if self.connection_manager.holds_secret(self.credential_ref):
                closed = self.connection_manager.close_session(self.credential_ref)
                if is_refusal(closed):
                    return closed
            opened = self.connection_manager.open_session(self.binding)
            if is_refusal(opened):
                return opened
            if opened.value != self.credential_ref:
                return TypedRefusal(
                    category=RefusalCategory.POLICY_REJECTION,
                    retryability=Retryability.NO,
                    context={
                        "field": "credential_ref",
                        "reason": "re-auth must return the same credential reference",
                        "expected": self.credential_ref.value,
                        "got": opened.value.value,
                    },
                )
            return Ok(self.credential_ref)
        # Credential-free path: reference presence is the auth handle; no value.
        return Ok(self.credential_ref)

    def _gap_replay(
        self, recovered: object
    ) -> Result[tuple[tuple[Mapping[str, object], ...], bool]]:
        """Persist recovered fills/lifecycle since last-seen execution, then advance frontier."""
        if isinstance(recovered, (str, bytes)) or not isinstance(recovered, Sequence):
            return _invalid(
                "recovered",
                "gap replay takes a sequence of RecoveredObservation or mappings",
                given=repr(recovered),
            )
        since = self.receive_frontier.last_seen_execution_id
        persisted: list[Mapping[str, object]] = []
        for index, item in enumerate(cast("Sequence[object]", recovered)):
            obs = _coerce_recovered(item, index=index)
            if is_refusal(obs):
                return obs
            row = obs.value
            if row.kind not in _PERSISTABLE_KINDS:
                return _invalid(
                    "recovered",
                    "gap replay persists fills and lifecycle events only",
                    index=index,
                    kind=row.kind,
                    allowed=sorted(_PERSISTABLE_KINDS),
                )
            # Skip events at-or-before the last-seen execution identity.
            if (
                since is not None
                and row.execution_id is not None
                and row.execution_id == since
            ):
                continue
            recorded = self._persist(row)
            if is_refusal(recorded):
                return recorded
            self.receive_frontier.advance(
                observation_id=row.observation_id,
                receive_wall_ns=row.receive_wall_ns,
                execution_id=row.execution_id,
            )
            persisted.append(row.as_mapping())
        return Ok((tuple(persisted), len(persisted) > 0))

    def _persist(self, row: RecoveredObservation) -> Result[bool]:
        """Record recovered evidence before healthy may be declared."""
        payload = MappingProxyType(
            {
                "kind": "gap-replay",
                "observation_kind": row.kind,
                "observation_id": row.observation_id,
                "execution_id": row.execution_id,
                "receive_wall_ns": row.receive_wall_ns,
                "payload": dict(row.payload),
                "credential_ref_id": self.credential_ref.value,
            }
        )
        if self.observation_sink is not None:
            emitted = self.observation_sink.emit(payload)
            if is_refusal(emitted):
                return emitted
        if self.journal_sink is not None:
            event_type = "fill" if row.kind in _FILL_KINDS else "order"
            journal_row = MappingProxyType(
                {
                    "event_type": event_type,
                    "kind": "gap-replay",
                    "observation_id": row.observation_id,
                    "execution_id": row.execution_id,
                    "receive_wall_ns": row.receive_wall_ns,
                }
            )
            appended = self.journal_sink.append(journal_row)
            if is_refusal(appended):
                return appended
        return Ok(True)

    def _correlation_evidence(
        self,
        *,
        gap_had_events: bool,
        correlation_instant: object | None,
        outstanding: tuple[InFlightResolution, ...],
    ) -> Mapping[str, object]:
        """Even a no-gap reconnect emits correlation evidence (TN-10)."""
        instant_ns: int | None
        if isinstance(correlation_instant, Instant):
            instant_ns = correlation_instant.value_ns
        elif correlation_instant is None:
            instant_ns = None
        else:
            instant_ns = None
        return MappingProxyType(
            {
                "kind": "reconnect-correlation",
                "gap_had_events": gap_had_events,
                "no_gap": not gap_had_events,
                "credential_ref_id": self.credential_ref.value,
                "outstanding_unknown_count": len(outstanding),
                "outstanding_all_unknown": all(
                    item.outcome is SubmissionOutcome.UNKNOWN
                    and item.trigger is UnknownTrigger.DISCONNECT
                    for item in outstanding
                ),
                "receive_frontier": dict(self.receive_frontier.as_mapping()),
                "interpretation_cursor_observation_id": (
                    self.interpretation_cursor_observation_id
                ),
                "frontiers_distinct": True,
                "correlation_instant_ns": instant_ns,
                "commands_resubmitted": self._commands_resubmitted,
            }
        )


def _coerce_recovered(item: object, *, index: int) -> Result[RecoveredObservation]:
    if isinstance(item, RecoveredObservation):
        return Ok(item)
    if not isinstance(item, Mapping):
        return _invalid(
            "recovered",
            "each recovered item is a RecoveredObservation or mapping",
            index=index,
            given=type(item).__name__,
        )
    body = cast("Mapping[str, object]", item)
    oid = body.get("observation_id")
    kind = body.get("kind")
    wall = body.get("receive_wall_ns")
    payload = body.get("payload", {})
    execution_id = body.get("execution_id")
    if not isinstance(oid, str) or oid.strip() == "":
        return _invalid(
            "observation_id",
            "recovered observation names a non-empty observation id",
            index=index,
            given=repr(oid),
        )
    if not isinstance(kind, str) or kind.strip() == "":
        return _invalid(
            "kind",
            "recovered observation names a non-empty kind",
            index=index,
            given=repr(kind),
        )
    if not isinstance(wall, int) or isinstance(wall, bool) or wall < 0:
        return _invalid(
            "receive_wall_ns",
            "recovered observation carries a non-negative receive-wall ns",
            index=index,
            given=repr(wall),
        )
    if not isinstance(payload, Mapping):
        return _invalid(
            "payload",
            "recovered observation payload is a mapping",
            index=index,
            given=type(payload).__name__,
        )
    exec_id: str | None
    if execution_id is None:
        exec_id = None
    elif isinstance(execution_id, str) and execution_id.strip() != "":
        exec_id = execution_id.strip()
    else:
        return _invalid(
            "execution_id",
            "execution id is a non-empty token when supplied",
            index=index,
            given=repr(execution_id),
        )
    return Ok(
        RecoveredObservation(
            observation_id=oid.strip(),
            kind=kind.strip().lower(),
            receive_wall_ns=wall,
            payload=MappingProxyType(dict(cast("Mapping[str, object]", payload))),
            execution_id=exec_id,
        )
    )


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )
