"""Deterministic Quant-owned Routine scheduler (CT-49; AD-29; FR-Q62).

Operator-principal writes persist declarative Routine records. Firing mints a
fresh ``correlation_id`` at the scheduled-trigger origin, runs
``before_routine_fire`` / ``after_routine_fire``, and instantiates a Mission
through the Mission Compiler as a ``machine`` principal with no extra authority
and no ability to answer a human gate. Missed fires while the daemon is down
are recorded, never replayed; catch-up is an explicit operator action.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal

from qma.core.ontology import Quant
from qma.core.ontology.routine import (
    MAX_CONCURRENT_REGISTRY_KEY,
    MISSED_FIRE_DISPOSITION,
    ROUTINE_CATCH_UP_COMMAND,
    ROUTINE_WRITE_COMMAND,
    Routine,
    authorize_routine_catch_up,
    authorize_routine_write,
    parse_routine,
    refuse_agent_routine_write,
    source_may_write_routine,
)
from qma.core.plugins.hooks import HookSource
from qma.core.vocabulary.enums import HookResultDecision, HookVerb, PrincipalClass
from qma.daemon.hooks.registry import HookRegistry, event_names_for_verb
from qma.daemon.journal.authoritative import AuthoritativeJournal
from qma.daemon.journal.fold_contracts import v1_fold_contract
from qma.daemon.journal.variables import registry_key
from qma.daemon.scheduler.cron import due_instants, slot_end_ns, validate_schedule_zone
from qma.daemon.scheduler.wake import routine_fire_suppressed_by_quiet_hours
from qma.daemon.taskgraph.compiler import CompileRequest, CompileResult, MissionCompiler
from qma.daemon.taskgraph.records import MissionRecord
from qma.wire.correlation import CorrelationMintOrigin, mint_correlation_id
from qma.wire.principals import AuthorizedWireCommand, authorize_wire_command
from qmf.core import Clock, DataDrivenClock, Instant, Ok, Result, is_ok, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "AUTOMATIC_BACKFILL",
    "MAX_CONCURRENT_REGISTRY_KEY",
    "MISSED_FIRE_DISPOSITION",
    "ROUTINE_CATCH_UP_COMMAND",
    "ROUTINE_FIRE_PRINCIPAL",
    "ROUTINE_RECORDS_FOLD_ID",
    "ROUTINE_RECORDS_STORE_NAME",
    "ROUTINE_WRITE_COMMAND",
    "CatchUpResult",
    "MissedFire",
    "RoutineFire",
    "RoutineScheduler",
    "RoutineTickResult",
    "machine_principal_may_answer_human_gate",
]


ROUTINE_RECORDS_STORE_NAME: Final[str] = "routine_records"
ROUTINE_RECORDS_FOLD_ID: Final[str] = "routine_records"
AUTOMATIC_BACKFILL: Final[bool] = False
ROUTINE_FIRE_PRINCIPAL: Final[PrincipalClass] = PrincipalClass.MACHINE

_ROUTINE_WRITTEN_EVENT: Final[str] = "routine.written"
_ROUTINE_FIRED_EVENT: Final[str] = "routine.fired"
_ROUTINE_MISSED_EVENT: Final[str] = "routine.missed"
_ROUTINE_CATCH_UP_EVENT: Final[str] = "routine.catch_up"
_DEFAULT_CLOCK_TICKS: Final[int] = 256
_DEFAULT_CLOCK_BASE_NS: Final[int] = 1_700_000_000_000_000_000
_BLOCKING_BEFORE: Final[frozenset[HookResultDecision]] = frozenset(
    {
        HookResultDecision.DENY,
        HookResultDecision.DEFER,
        HookResultDecision.ASK,
        HookResultDecision.BLOCK_STOP,
    }
)


def machine_principal_may_answer_human_gate() -> bool:
    """A firing Routine is a machine principal and can answer no human gate."""
    return False


def _default_clock() -> DataDrivenClock:
    walls = tuple(Instant(value_ns=_DEFAULT_CLOCK_BASE_NS + i) for i in range(_DEFAULT_CLOCK_TICKS))
    monos = tuple(i * 1_000 for i in range(_DEFAULT_CLOCK_TICKS))
    return DataDrivenClock(
        boot_epoch_id="routine-scheduler",
        wall_instants=walls,
        monotonic_ns=monos,
    )


@dataclass(frozen=True, slots=True)
class MissedFire:
    """One scheduled fire that was recorded, not replayed (CT-49; FR-Q62)."""

    routine_id: str
    scheduled_at_ns: int
    disposition: Literal["recorded"] = "recorded"
    caught_up: bool = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "routine_id": self.routine_id,
                "scheduled_at": self.scheduled_at_ns,
                "disposition": self.disposition,
                "caught_up": self.caught_up,
                "replayed": False,
                "automatic_backfill": AUTOMATIC_BACKFILL,
            }
        )


@dataclass(frozen=True, slots=True)
class RoutineFire:
    """One instantiated Routine firing (CT-49; FR-Q62)."""

    routine_id: str
    scheduled_at_ns: int
    correlation_id: str
    principal_class: PrincipalClass
    mission: MissionRecord
    compiled: CompileResult
    before_event: str
    after_event: str
    catch_up: bool = False

    @property
    def extra_authority(self) -> bool:
        return False

    @property
    def may_answer_human_gate(self) -> bool:
        return machine_principal_may_answer_human_gate()

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "routine_id": self.routine_id,
                "scheduled_at": self.scheduled_at_ns,
                "correlation_id": self.correlation_id,
                "principal_class": self.principal_class.value,
                "extra_authority": False,
                "may_answer_human_gate": False,
                "mission_id": self.mission.id,
                "graph_template_ref": self.mission.graph_template_ref,
                "goal": self.mission.goal.text,
                "before_event": self.before_event,
                "after_event": self.after_event,
                "catch_up": self.catch_up,
                "mint_origin": CorrelationMintOrigin.SCHEDULED_TRIGGER.value,
            }
        )


@dataclass(frozen=True, slots=True)
class RoutineTickResult:
    """Outcome of one scheduler evaluation over a Routine."""

    routine_id: str
    fired: tuple[RoutineFire, ...]
    missed: tuple[MissedFire, ...]
    skipped_disabled: bool
    skipped_at_cap: bool

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "routine_id": self.routine_id,
                "fired": [dict(item.to_payload()) for item in self.fired],
                "missed": [dict(item.to_payload()) for item in self.missed],
                "skipped_disabled": self.skipped_disabled,
                "skipped_at_cap": self.skipped_at_cap,
                "automatic_backfill": AUTOMATIC_BACKFILL,
            }
        )


@dataclass(frozen=True, slots=True)
class CatchUpResult:
    """Operator-gated replay of recorded missed fires — never automatic."""

    routine_id: str
    fired: tuple[RoutineFire, ...]
    remaining_missed: tuple[MissedFire, ...]

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "routine_id": self.routine_id,
                "fired": [dict(item.to_payload()) for item in self.fired],
                "remaining_missed": [dict(item.to_payload()) for item in self.remaining_missed],
                "automatic_backfill": AUTOMATIC_BACKFILL,
                "command": ROUTINE_CATCH_UP_COMMAND,
            }
        )


@dataclass
class _RoutineState:
    record: Routine
    created_at_ns: int
    last_evaluated_at_ns: int
    active_mission_ids: list[str] = field(default_factory=list[str])
    missed: list[MissedFire] = field(default_factory=list[MissedFire])
    fires: list[RoutineFire] = field(default_factory=list[RoutineFire])


@dataclass
class RoutineScheduler:
    """Daemon-owned Routine store and deterministic scheduler (CT-49; FR-Q62)."""

    _records: dict[str, _RoutineState] = field(default_factory=dict[str, _RoutineState])
    _quants: dict[str, Quant] = field(default_factory=dict[str, Quant])
    _clock: Clock = field(default_factory=_default_clock)
    _journal: AuthoritativeJournal | None = None
    _hooks: HookRegistry = field(default_factory=HookRegistry)
    _compiler: MissionCompiler = field(default_factory=MissionCompiler)
    _journal_rows: int = 0

    @property
    def store_name(self) -> str:
        return ROUTINE_RECORDS_STORE_NAME

    @property
    def fold_id(self) -> str:
        return ROUTINE_RECORDS_FOLD_ID

    @property
    def hooks(self) -> HookRegistry:
        return self._hooks

    @property
    def compiler(self) -> MissionCompiler:
        return self._compiler

    @property
    def automatic_backfill(self) -> bool:
        return AUTOMATIC_BACKFILL

    @property
    def max_concurrent_registry_key(self) -> str:
        return MAX_CONCURRENT_REGISTRY_KEY

    def journal_event_count(self) -> int:
        return self._journal_rows

    def register_quant(self, quant: Quant) -> None:
        """Remember the owning Quant so the Mission Compiler can instantiate."""
        self._quants[quant.actor_id.value] = quant
        self._compiler.remember_quant(quant.actor_id)

    def get(self, routine_id: str) -> Routine | None:
        state = self._records.get(routine_id)
        return None if state is None else state.record

    def missed_fires(self, routine_id: str) -> tuple[MissedFire, ...]:
        state = self._records.get(routine_id)
        if state is None:
            return ()
        return tuple(item for item in state.missed if not item.caught_up)

    def fires(self, routine_id: str) -> tuple[RoutineFire, ...]:
        state = self._records.get(routine_id)
        return () if state is None else tuple(state.fires)

    def active_count(self, routine_id: str) -> int:
        state = self._records.get(routine_id)
        return 0 if state is None else len(state.active_mission_ids)

    def release_mission(self, routine_id: str, mission_id: str) -> None:
        """Drop a finished Mission from the per-Routine concurrency cap."""
        state = self._records.get(routine_id)
        if state is None:
            return
        try:
            state.active_mission_ids.remove(mission_id)
        except ValueError:
            return

    def write(
        self,
        body: Mapping[str, object] | Routine,
        *,
        principal_class: object,
        source: object = "operator",
        owner: Quant | None = None,
        at: Instant | None = None,
    ) -> Result[Routine]:
        """Persist a Routine as operator-only declarative daemon state."""
        if not source_may_write_routine(source):
            return refuse_agent_routine_write(source=source)
        authorized = authorize_wire_command(ROUTINE_WRITE_COMMAND, principal_class)
        if is_refusal(authorized):
            return authorized
        principal = authorize_routine_write(authorized.value.principal_class)
        if is_refusal(principal):
            return principal
        parsed = parse_routine(body)
        if is_refusal(parsed):
            return parsed
        record = parsed.value
        zone = validate_schedule_zone(record.schedule.iana_zone)
        if is_refusal(zone):
            return zone
        if owner is not None:
            if owner.actor_id != record.owner_ref:
                return invalid_input(
                    "owner_ref",
                    "Routine owner_ref must match the supplied Quant ActorId (CT-49; AD-7; FR-Q62)",
                    given=record.owner_ref.value,
                )
            self.register_quant(owner)
        quant = self._quants.get(record.owner_ref.value)
        if quant is None:
            return invalid_input(
                "owner_ref",
                "Routine owner_ref must name a registered Quant (CT-49; FR-Q62)",
                given=record.owner_ref.value,
            )
        when = self._now(at)
        if is_refusal(when):
            return when
        existing = self._records.get(record.id)
        schedule_changed = existing is not None and existing.record.schedule != record.schedule
        if existing is None or schedule_changed:
            state = _RoutineState(
                record=record,
                created_at_ns=when.value.value_ns,
                last_evaluated_at_ns=when.value.value_ns,
            )
            if existing is not None:
                state.active_mission_ids = existing.active_mission_ids
                state.fires = existing.fires
                state.missed = existing.missed
        else:
            existing.record = record
            state = existing
        self._records[record.id] = state
        declared = self._declare_store()
        if is_refusal(declared):
            return declared
        journaled = self._journal_event(
            _ROUTINE_WRITTEN_EVENT,
            record,
            payload={"routine": dict(record.to_payload())},
            at=when.value,
        )
        if is_refusal(journaled):
            return journaled
        return Ok(record)

    def authorize_human_gate(
        self,
        command: object,
        principal_class: object,
    ) -> Result[AuthorizedWireCommand]:
        """Refuse human-gate commands from the Routine's machine principal."""
        return authorize_wire_command(command, principal_class)

    def tick(
        self,
        *,
        at: Instant | None = None,
        routine_id: str | None = None,
    ) -> Result[tuple[RoutineTickResult, ...]]:
        """Evaluate due Routines. Missed fires in the gap are recorded, not replayed."""
        when = self._now(at)
        if is_refusal(when):
            return when
        now = when.value
        targets: Sequence[str]
        if routine_id is None:
            targets = tuple(self._records)
        else:
            if routine_id not in self._records:
                return invalid_input(
                    "id",
                    "unknown Routine id (CT-49; FR-Q62)",
                    given=routine_id,
                )
            targets = (routine_id,)
        results: list[RoutineTickResult] = []
        for rid in targets:
            evaluated = self._evaluate(self._records[rid], now=now, replay_missed=False)
            if is_refusal(evaluated):
                return evaluated
            results.append(evaluated.value)
        return Ok(tuple(results))

    def recover(self, *, at: Instant | None = None) -> Result[tuple[RoutineTickResult, ...]]:
        """Record missed fires after downtime without replaying them."""
        return self.tick(at=at)

    def catch_up(
        self,
        routine_id: str,
        *,
        principal_class: object,
        at: Instant | None = None,
    ) -> Result[CatchUpResult]:
        """Replay recorded missed fires — operator principal only, never automatic."""
        authorized = authorize_wire_command(ROUTINE_CATCH_UP_COMMAND, principal_class)
        if is_refusal(authorized):
            return authorized
        principal = authorize_routine_catch_up(authorized.value.principal_class)
        if is_refusal(principal):
            return principal
        state = self._records.get(routine_id)
        if state is None:
            return invalid_input("id", "unknown Routine id (CT-49; FR-Q62)", given=routine_id)
        when = self._now(at)
        if is_refusal(when):
            return when
        outstanding = [item for item in state.missed if not item.caught_up]
        fired: list[RoutineFire] = []
        for missed in outstanding:
            if len(state.active_mission_ids) >= state.record.max_concurrent:
                continue
            ignited = self._fire(
                state,
                scheduled_at_ns=missed.scheduled_at_ns,
                now=when.value,
                catch_up=True,
            )
            if is_refusal(ignited):
                return ignited
            if ignited.value is None:
                continue
            fired.append(ignited.value)
        caught_ns = {item.scheduled_at_ns for item in fired}
        updated: list[MissedFire] = []
        for item in state.missed:
            if item.scheduled_at_ns in caught_ns and not item.caught_up:
                updated.append(
                    MissedFire(
                        routine_id=item.routine_id,
                        scheduled_at_ns=item.scheduled_at_ns,
                        disposition="recorded",
                        caught_up=True,
                    )
                )
            else:
                updated.append(item)
        state.missed = updated
        remaining = tuple(item for item in state.missed if not item.caught_up)
        journaled = self._journal_event(
            _ROUTINE_CATCH_UP_EVENT,
            state.record,
            payload={
                "routine_id": routine_id,
                "fired": [dict(item.to_payload()) for item in fired],
                "remaining": len(remaining),
                "automatic_backfill": AUTOMATIC_BACKFILL,
            },
            at=when.value,
        )
        if is_refusal(journaled):
            return journaled
        return Ok(
            CatchUpResult(
                routine_id=routine_id,
                fired=tuple(fired),
                remaining_missed=remaining,
            )
        )

    def _evaluate(
        self,
        state: _RoutineState,
        *,
        now: Instant,
        replay_missed: bool,
    ) -> Result[RoutineTickResult]:
        _ = replay_missed  # never true — automatic backfill is excluded.
        record = state.record
        first_due = None
        if record.schedule.kind == "interval" and record.schedule.every_ns is not None:
            first_due = state.created_at_ns + record.schedule.every_ns
        dues = due_instants(
            record.schedule,
            after_ns=state.last_evaluated_at_ns,
            until_ns=now.value_ns,
            first_due_ns=first_due,
        )
        if is_refusal(dues):
            return dues
        due_ns = dues.value
        state.last_evaluated_at_ns = now.value_ns
        if not due_ns:
            return Ok(
                RoutineTickResult(
                    routine_id=record.id,
                    fired=(),
                    missed=(),
                    skipped_disabled=not record.enabled,
                    skipped_at_cap=False,
                )
            )

        current: int | None = None
        missed_ns: list[int] = []
        for scheduled in due_ns:
            end = slot_end_ns(record.schedule, scheduled)
            if is_refusal(end):
                return end
            if scheduled <= now.value_ns < end.value:
                current = scheduled
            else:
                missed_ns.append(scheduled)

        skipped_disabled = False
        skipped_at_cap = False
        recorded_missed: list[MissedFire] = []
        fired: list[RoutineFire] = []

        if not record.enabled:
            skipped_disabled = True
            state.last_evaluated_at_ns = now.value_ns
            return Ok(
                RoutineTickResult(
                    routine_id=record.id,
                    fired=(),
                    missed=(),
                    skipped_disabled=True,
                    skipped_at_cap=False,
                )
            )

        for scheduled in missed_ns:
            missed = MissedFire(routine_id=record.id, scheduled_at_ns=scheduled)
            state.missed.append(missed)
            recorded_missed.append(missed)
            journaled = self._journal_event(
                _ROUTINE_MISSED_EVENT,
                record,
                payload=dict(missed.to_payload()),
                at=now,
            )
            if is_refusal(journaled):
                return journaled

        if current is not None:
            if len(state.active_mission_ids) >= record.max_concurrent:
                skipped_at_cap = True
            else:
                suppressed = routine_fire_suppressed_by_quiet_hours(None, at=now)
                if is_refusal(suppressed):
                    return suppressed
                ignited = self._fire(state, scheduled_at_ns=current, now=now, catch_up=False)
                if is_refusal(ignited):
                    return ignited
                if ignited.value is not None:
                    fired.append(ignited.value)

        return Ok(
            RoutineTickResult(
                routine_id=record.id,
                fired=tuple(fired),
                missed=tuple(recorded_missed),
                skipped_disabled=skipped_disabled,
                skipped_at_cap=skipped_at_cap,
            )
        )

    def _fire(
        self,
        state: _RoutineState,
        *,
        scheduled_at_ns: int,
        now: Instant,
        catch_up: bool,
    ) -> Result[RoutineFire | None]:
        record = state.record
        owner = self._quants.get(record.owner_ref.value)
        if owner is None:
            return invalid_input(
                "owner_ref",
                "Routine owner_ref must name a registered Quant (CT-49; FR-Q62)",
                given=record.owner_ref.value,
            )
        correlation = mint_correlation_id(
            origin=CorrelationMintOrigin.SCHEDULED_TRIGGER,
            correlation_id=f"routine:{record.id}:{scheduled_at_ns}",
        )
        if is_refusal(correlation):
            return correlation
        cid = correlation.value.correlation_id
        before, after = event_names_for_verb(HookVerb.ROUTINE_FIRE)
        payload: dict[str, object] = {
            "routine_id": record.id,
            "owner_ref": record.owner_ref.value,
            "goal": record.goal.text,
            "graph_template_ref": record.graph_template_ref,
            "correlation_id": cid,
            "principal_class": ROUTINE_FIRE_PRINCIPAL.value,
            "scheduled_at": scheduled_at_ns,
            "extra_authority": False,
            "may_answer_human_gate": False,
            "catch_up": catch_up,
        }
        before_result = self._hooks.dispatch(
            before,
            payload=payload,
            source=HookSource.MISSION,
            correlation_id=cid,
        )
        if is_refusal(before_result):
            return before_result
        if before_result.value.decision in _BLOCKING_BEFORE:
            return policy_rejection(
                before,
                f"{before} resolved to {before_result.value.decision.value}; "
                "act not executed (CT-49; AD-10; FR-Q62)",
                given=before_result.value.reason or before_result.value.decision.value,
            )

        compiled = self._compiler.compile(
            CompileRequest(
                goal=record.goal,
                owner=owner,
                graph_template_ref=record.graph_template_ref,
            )
        )
        after_payload = dict(payload)
        if is_ok(compiled):
            after_payload["mission_id"] = compiled.value.mission.id
            after_payload["effect"] = dict(compiled.value.to_payload())
        else:
            after_payload["compile_refused"] = True
        after_result = self._hooks.dispatch(
            after,
            payload=after_payload,
            source=HookSource.MISSION,
            correlation_id=cid,
        )
        if is_refusal(after_result):
            return after_result
        if is_refusal(compiled):
            return compiled

        fire = RoutineFire(
            routine_id=record.id,
            scheduled_at_ns=scheduled_at_ns,
            correlation_id=cid,
            principal_class=ROUTINE_FIRE_PRINCIPAL,
            mission=compiled.value.mission,
            compiled=compiled.value,
            before_event=before,
            after_event=after,
            catch_up=catch_up,
        )
        state.fires.append(fire)
        state.active_mission_ids.append(compiled.value.mission.id)
        journaled = self._journal_event(
            _ROUTINE_FIRED_EVENT,
            record,
            payload=dict(fire.to_payload()),
            at=now,
        )
        if is_refusal(journaled):
            return journaled
        return Ok(fire)

    def _now(self, at: Instant | None) -> Result[Instant]:
        if at is not None:
            return Ok(at)
        return self._clock.wall_now()

    def _declare_store(self) -> Result[object]:
        if self._journal is None:
            return Ok(None)
        declared = self._journal.declare_store(ROUTINE_RECORDS_STORE_NAME)
        if is_refusal(declared):
            return declared
        fold = v1_fold_contract(ROUTINE_RECORDS_FOLD_ID)
        if fold is not None:
            registered = self._journal.register_fold(ROUTINE_RECORDS_FOLD_ID)
            if is_refusal(registered):
                return registered
        return Ok(None)

    def _journal_event(
        self,
        event: str,
        record: Routine,
        *,
        payload: Mapping[str, object],
        at: Instant,
    ) -> Result[int | None]:
        if self._journal is None:
            self._journal_rows += 1
            return Ok(None)
        declared = self._declare_store()
        if is_refusal(declared):
            return declared
        quant = self._quants.get(record.owner_ref.value)
        scope: list[dict[str, str]] = []
        if quant is not None:
            scope = [
                {"kind": "desk", "id": quant.desk.value},
                {"kind": "quant", "id": quant.quant_slug},
            ]
        body: dict[str, object] = dict(payload)
        body["store"] = ROUTINE_RECORDS_STORE_NAME
        if event == _ROUTINE_WRITTEN_EVENT:
            body["principal_class"] = PrincipalClass.OPERATOR.value
        else:
            body["principal_class"] = ROUTINE_FIRE_PRINCIPAL.value
        appended = self._journal.append_event(
            event,
            scope_path=scope,
            payload=body,
            occurred_at=at,
        )
        if is_refusal(appended):
            return appended
        self._journal_rows += 1
        return Ok(appended.value.record.journal_seq)

    def to_payload(self, routine_id: str) -> Mapping[str, object] | None:
        state = self._records.get(routine_id)
        if state is None:
            return None
        fold = v1_fold_contract(ROUTINE_RECORDS_FOLD_ID)
        return MappingProxyType(
            {
                "store": ROUTINE_RECORDS_STORE_NAME,
                "fold_id": ROUTINE_RECORDS_FOLD_ID,
                "source_stream": None if fold is None else fold.source_stream,
                "routine": dict(state.record.to_payload()),
                "max_concurrent_registry_key": registry_key("routine.max_concurrent"),
                "automatic_backfill": AUTOMATIC_BACKFILL,
                "active_missions": list(state.active_mission_ids),
                "missed": [dict(item.to_payload()) for item in state.missed],
            }
        )
