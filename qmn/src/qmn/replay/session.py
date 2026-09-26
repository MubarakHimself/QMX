"""Replay-scoped composition, unforked run_slice drive, and decision diff.

A replay job composes ``world = replay`` from the same resolved node-config,
binds disjoint WriterIds, the replay VenueClientPort, and QMB's data-driven
frontier clock. It never resolves a secret, never opens a network/live sink,
never submits a command, and never simulates a fill (GAP-0056 deferred).
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal, cast

from qmb.runloop import DeclaredStream, SliceObservation, StreamSet
from qmf.core import (
    Account,
    DataDrivenClock,
    Instant,
    Ok,
    Result,
    SecretRef,
    SecretValue,
    SinkAck,
    SinkResult,
    TypedRefusal,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)

from qmn.config.compiler import ResolvedNodeConfig
from qmn.loop import CommandStreamLoop, RecordingAccumulator
from qmn.mis.signal_snapshot import ProducerReadiness
from qmn.replay._refuse import clean_token, invalid, policy, unavailable
from qmn.replay.port import (
    FILL_SIMULATION_IN_REPLAY,
    GAP_0056_DEFERRED,
    REPLAY_IMPORT_PORT,
    RecordedDay,
    ReplayImportPort,
    refuse_fill_simulation,
    refuse_sqs_recompute,
)
from qmn.venue import (
    ReplayAdapter,
    VenueClientKind,
    select_venue_client,
)

__all__ = [
    "NODE_PROCESS_ENV",
    "REPLAY_PROCESS_ENV",
    "REPLAY_WRITER_ROLE_PREFIX",
    "ReplayComposition",
    "ReplayDiffReport",
    "ReplayJobSpec",
    "ReplaySliceHandler",
    "ReplayWorldSink",
    "allocate_replay_writer",
    "assert_outside_node_process",
    "attach_replay_to_loop",
    "diff_recorded_day",
    "refuse_admission_gate",
    "refuse_command_submit",
    "refuse_credential_bind",
    "refuse_in_node_process",
    "refuse_live_sink",
    "refuse_live_venue_client",
    "refuse_network",
    "refuse_restore_into_live",
    "refuse_secret_resolution",
    "run_recorded_day",
    "writers_are_disjoint",
]


NODE_PROCESS_ENV: Final[str] = "QMN_NODE_PROCESS"
REPLAY_PROCESS_ENV: Final[str] = "QMN_REPLAY_PROCESS"
REPLAY_WRITER_ROLE_PREFIX: Final[str] = "replay-"
REPLAY_WORLD: Final[World] = World.REPLAY

_IN_NODE_ID: Final[str] = "replay.in_node_process"
_RESOLVE_REFUSAL_ID: Final[str] = "replay.secret_resolved"
_LIVE_SINK_ID: Final[str] = "replay.live_sink"
_NETWORK_ID: Final[str] = "replay.network"
_WRONG_WORLD_ID: Final[str] = "replay.wrong_world"
_LIVE_VENUE_ID: Final[str] = "replay.live_venue_client"
_IMPORT_REQUIRED_ID: Final[str] = "replay.import_port_required"
_COMMAND_ID: Final[str] = "replay.command_submit"
_RESTORE_ID: Final[str] = "replay.restore_into_live"
_GATE_ID: Final[str] = "replay.admission_gate"
_CLOCK_ID: Final[str] = "replay.clock_exhaustion"
_DISJOINT_ID: Final[str] = "replay.disjoint_writer"
_CREDENTIAL_ID: Final[str] = "replay.credential_bind"

_MAX_SLICE_LATENCY_NS: Final[int] = 50_000_000
_ACCUMULATOR_BOUND: Final[int] = 64


def refuse_in_node_process() -> TypedRefusal:
    """Replay never drives a second loop on the live node thread (DEC-0206)."""
    return policy(
        "process",
        "a replay run is a stdlib process-per-job spawn outside the node process",
        failure_id=_IN_NODE_ID,
        env=NODE_PROCESS_ENV,
    )


def refuse_secret_resolution(*, given: object = None) -> TypedRefusal:
    return policy(
        "secret",
        "replay resolves no credential reference and holds no venue secret",
        failure_id=_RESOLVE_REFUSAL_ID,
        given=repr(given),
        credential_resolved=False,
    )


def refuse_live_sink(*, target: object = None) -> TypedRefusal:
    return policy(
        "sink",
        "replay constructs no live sink; artifacts write only world=replay rooms",
        failure_id=_LIVE_SINK_ID,
        target=repr(target),
    )


def refuse_network(*, target: object = None) -> TypedRefusal:
    return policy(
        "network",
        "replay opens no socket and no live network path (DEC-0206)",
        failure_id=_NETWORK_ID,
        target=repr(target),
        socket_opened=False,
    )


def refuse_live_venue_client(*, kind: object = None) -> TypedRefusal:
    return policy(
        "venue_client",
        "a replay composition binds only the replay VenueClientPort",
        failure_id=_LIVE_VENUE_ID,
        kind=repr(kind),
        world=World.REPLAY.value,
    )


def refuse_command_submit(*, command: object = None) -> TypedRefusal:
    return policy(
        "submit",
        "replay neither submits nor resends any command; recorded venue answers "
        "ride as evidence only (GAP-0056 deferred)",
        failure_id=_COMMAND_ID,
        command=repr(type(command).__name__),
        fill_simulation=FILL_SIMULATION_IN_REPLAY,
    )


def refuse_restore_into_live(
    *,
    target_world: object = None,
    target_seat: object = None,
) -> TypedRefusal:
    return policy(
        "restore",
        "replay state cannot restore into live or paper seats; world is a "
        "BotStateScope identity component (DEC-0206)",
        failure_id=_RESTORE_ID,
        target_world=repr(target_world),
        target_seat=repr(target_seat),
        source_world=World.REPLAY.value,
    )


def refuse_admission_gate(*, purpose: object = None) -> TypedRefusal:
    return policy(
        "gate",
        "a replay diff is ungoverned diagnostic evidence only; it never gates "
        "admission or live money (DEC-0206, DEC-0229)",
        failure_id=_GATE_ID,
        purpose=repr(purpose),
        diagnostic_only=True,
    )


def assert_outside_node_process() -> Result[None]:
    """Refuse when the current process is marked as the trading node."""
    if os.environ.get(NODE_PROCESS_ENV) == "1":
        return refuse_in_node_process()
    return Ok(None)


def attach_replay_to_loop(loop: object) -> Result[None]:
    """Always refuse — replay is never a second loop on the node thread."""
    del loop
    return refuse_in_node_process()


def allocate_replay_writer(
    *,
    machine: object,
    role: object,
    stream: object,
    boot_epoch_id: object,
) -> Result[WriterId]:
    """Mint a WriterId in the disjoint replay namespace."""
    role_token = clean_token(role)
    if role_token is None or not role_token.startswith(REPLAY_WRITER_ROLE_PREFIX):
        return policy(
            "role",
            "replay WriterIds draw from a disjoint namespace whose role starts "
            f"with {REPLAY_WRITER_ROLE_PREFIX!r}",
            failure_id=_DISJOINT_ID,
            given=repr(role),
            prefix=REPLAY_WRITER_ROLE_PREFIX,
        )
    stream_token = clean_token(stream)
    if stream_token is None or not stream_token.startswith("replay:"):
        return policy(
            "stream",
            "replay WriterId streams are prefixed replay: so they cannot collide "
            "with live venue streams",
            failure_id=_DISJOINT_ID,
            given=repr(stream),
        )
    return WriterId.try_create(machine, role_token, stream_token, boot_epoch_id)


def writers_are_disjoint(
    replay_writers: Sequence[WriterId],
    live_writers: Sequence[WriterId],
) -> bool:
    """True when no (machine, role, stream, boot) tuple is shared."""
    live_keys = {item.order_tuple() for item in live_writers}
    for writer in replay_writers:
        if writer.order_tuple() in live_keys:
            return False
        if not writer.role.startswith(REPLAY_WRITER_ROLE_PREFIX):
            return False
    return True


@dataclass
class ReplayWorldSink:
    """In-memory sink that stamps ``world = replay`` and refuses other worlds."""

    world: World = REPLAY_WORLD
    rows: list[Mapping[str, object]] = field(default_factory=list[Mapping[str, object]])

    def emit(self, observation: object, /) -> SinkResult:
        return self._accept(observation, verb="emit")

    def append(self, event: object, /) -> SinkResult:
        return self._accept(event, verb="append")

    def _accept(self, payload: object, *, verb: str) -> SinkResult:
        del verb
        if isinstance(payload, Mapping):
            body = dict(cast("Mapping[str, object]", payload))
            declared = body.get("world")
            if declared is not None and declared != World.REPLAY.value:
                return refuse_live_sink(target=declared)
            body.setdefault("world", World.REPLAY.value)
            self.rows.append(MappingProxyType(body))
            return Ok(SinkAck())
        self.rows.append(MappingProxyType({"world": World.REPLAY.value, "payload": repr(payload)}))
        return Ok(SinkAck())


@dataclass
class ReplaySliceHandler:
    """Drive run_slice without minting venue commands or simulating fills."""

    day: RecordedDay
    produced_decisions: list[Mapping[str, object]] = field(
        default_factory=list[Mapping[str, object]]
    )
    sqs_recomputed: bool = False

    def update_stream(
        self,
        stream_id: str,
        observation: SliceObservation | None,
        frontier: Instant,
    ) -> Result[None]:
        del stream_id, observation, frontier
        return Ok(None)

    def scheduled_position_event(self, stream_id: str, frontier: Instant) -> Result[None]:
        del stream_id, frontier
        return Ok(None)

    def execute_resting(
        self,
        intent: object,
        observation: SliceObservation | None,
        frontier: Instant,
    ) -> Result[bool]:
        del intent, observation, frontier
        # Never fill — GAP-0056 stays deferred.
        return Ok(False)

    def update_closed_data(
        self,
        stream_id: str,
        observation: SliceObservation,
        frontier: Instant,
    ) -> Result[None]:
        del stream_id, observation, frontier
        return Ok(None)

    def mint_intents(self, stream_id: str, frontier: Instant) -> Result[object]:
        snap = self.day.snapshot_at(frontier.value_ns)
        if snap is None:
            readiness = ProducerReadiness.NOT_READY
            refused = True
            snapshot_fp1 = None
            hard_block = True
        else:
            readiness = snap.sqs_readiness
            refused = snap.entry_refused()
            snapshot_fp1 = snap.snapshot_fp1
            hard_block = snap.sqs_hard_block
        self.produced_decisions.append(
            MappingProxyType(
                {
                    "kind": "decision",
                    "frontier_ns": frontier.value_ns,
                    "stream_id": stream_id,
                    "sqs_readiness": readiness.value,
                    "sqs_hard_block": hard_block,
                    "entry_refused": refused,
                    "snapshot_fp1": snapshot_fp1,
                    "world": World.REPLAY.value,
                    "sqs_recomputed": False,
                }
            )
        )
        # Intents rest unfilled; nothing is submitted.
        return Ok(())

    def recompute_sqs(self, frontier_ns: object = None) -> Result[None]:
        self.sqs_recomputed = False
        return refuse_sqs_recompute(frontier_ns=frontier_ns)


@dataclass(frozen=True, slots=True)
class ReplayComposition:
    """Replay-scoped root: same config fp, disjoint writers, no secrets/network."""

    world: World
    composition_fp: str
    venue_id: VenueId
    account: Account
    writer: WriterId
    venue_client: ReplayAdapter
    clock: DataDrivenClock
    socket_opened: bool
    credential_resolved: bool
    live_sink: bool
    secrets_resolved: bool
    fill_simulation: bool = FILL_SIMULATION_IN_REPLAY

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "world": self.world.value,
                "composition_fp": self.composition_fp,
                "venue_id": self.venue_id.value,
                "account_id": self.account.account_id,
                "writer": {
                    "machine": self.writer.machine,
                    "role": self.writer.role,
                    "stream": self.writer.stream,
                    "boot_epoch_id": self.writer.boot_epoch_id,
                },
                "venue_kind": self.venue_client.kind.value,
                "socket_opened": self.socket_opened,
                "credential_resolved": self.credential_resolved,
                "live_sink": self.live_sink,
                "secrets_resolved": self.secrets_resolved,
                "fill_simulation": self.fill_simulation,
                "gap_0056_deferred": GAP_0056_DEFERRED,
            }
        )

    def bind_credential(self, credential: object) -> Result[None]:
        return refuse_credential_bind(given=credential)

    def bind_live_sink(self, sink: object) -> Result[None]:
        return refuse_live_sink(target=sink)

    def open_network(self, target: object = None) -> Result[None]:
        return refuse_network(target=target)

    def submit_or_resend(self, command: object) -> Result[None]:
        return refuse_command_submit(command=command)

    def simulate_fills(self, *args: object, **kwargs: object) -> Result[None]:
        del args, kwargs
        return refuse_fill_simulation()


@dataclass(frozen=True, slots=True)
class ReplayJobSpec:
    """Credential-free job description for one sealed interval."""

    import_port: ReplayImportPort
    source_world: World
    room_role: str
    prefix_id: str
    start_ns: int
    end_ns: int
    composition_fp: str
    machine: str
    boot_epoch_id: str

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "source_world": self.source_world.value,
                "room_role": self.room_role,
                "prefix_id": self.prefix_id,
                "start_ns": self.start_ns,
                "end_ns": self.end_ns,
                "composition_fp": self.composition_fp,
                "machine": self.machine,
                "boot_epoch_id": self.boot_epoch_id,
                "port": REPLAY_IMPORT_PORT,
                "world": World.REPLAY.value,
            }
        )

    @classmethod
    def try_create(
        cls,
        *,
        import_port: object,
        source_world: object,
        room_role: object,
        prefix_id: object,
        start_ns: object,
        end_ns: object,
        composition_fp: object,
        machine: object = "replay-host",
        boot_epoch_id: object = "replay-boot",
        config: object = None,
    ) -> Result[ReplayJobSpec]:
        if not isinstance(import_port, ReplayImportPort):
            return policy(
                "import_port",
                "live evidence enters replay only through the named one-way replay-import port",
                failure_id=_IMPORT_REQUIRED_ID,
                given=type(import_port).__name__,
            )
        if isinstance(source_world, World):
            world = source_world
        elif isinstance(source_world, str):
            try:
                world = World(source_world)
            except ValueError:
                return invalid("source_world", "source_world is live | replay", given=source_world)
        else:
            return invalid("source_world", "source_world is a World", given=repr(source_world))
        if world is World.SIMULATED:
            return policy(
                "world",
                "world = simulated is reserved-unusable",
                failure_id=_WRONG_WORLD_ID,
                world=world.value,
            )
        role = clean_token(room_role)
        if role is None:
            return invalid("room_role", "a sealed interval names a hot-room role")
        ident = clean_token(prefix_id)
        if ident is None:
            return invalid("prefix_id", "a sealed interval names a prefix id")
        start = _as_nonneg_int(start_ns, field="start_ns")
        if is_refusal(start):
            return start
        end = _as_nonneg_int(end_ns, field="end_ns")
        if is_refusal(end):
            return end
        fp = clean_token(composition_fp)
        if fp is None and isinstance(config, ResolvedNodeConfig):
            fp = config.fingerprint.value
        if fp is None:
            return invalid(
                "composition_fp",
                "replay composes from the same resolved node-config fingerprint",
            )
        if isinstance(config, ResolvedNodeConfig) and config.fingerprint.value != fp:
            return invalid(
                "composition_fp",
                "job composition_fp must match the resolved node-config artifact",
                spec=fp,
                config=config.fingerprint.value,
            )
        host = clean_token(machine)
        if host is None:
            return invalid("machine", "replay WriterIds name a machine")
        boot = clean_token(boot_epoch_id)
        if boot is None:
            return invalid("boot_epoch_id", "replay WriterIds carry a boot epoch")
        if isinstance(config, (SecretRef, SecretValue)):
            return refuse_secret_resolution(given=config)
        return Ok(
            cls(
                import_port=import_port,
                source_world=world,
                room_role=role,
                prefix_id=ident,
                start_ns=start.value,
                end_ns=end.value,
                composition_fp=fp,
                machine=host,
                boot_epoch_id=boot,
            )
        )


@dataclass(frozen=True, slots=True)
class ReplayDiffReport:
    """Ungoverned diagnostic decision/control/command diff (DEC-0206)."""

    world: World
    composition_fp: str
    interval: Mapping[str, int]
    provenance: Mapping[str, object]
    decisions: tuple[Mapping[str, object], ...]
    controls: tuple[Mapping[str, object], ...]
    commands: tuple[Mapping[str, object], ...]
    clean: bool
    diagnostic_only: bool = True
    admission_gate: bool = False
    live_gate: bool = False
    fill_simulation: bool = False
    commands_submitted: int = 0
    commands_resent: int = 0
    sqs_recomputed: bool = False
    socket_opened: bool = False
    credential_resolved: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "world": self.world.value,
                "composition_fp": self.composition_fp,
                "interval": dict(self.interval),
                "provenance": dict(self.provenance),
                "decisions": [dict(item) for item in self.decisions],
                "controls": [dict(item) for item in self.controls],
                "commands": [dict(item) for item in self.commands],
                "clean": self.clean,
                "diagnostic_only": self.diagnostic_only,
                "admission_gate": self.admission_gate,
                "live_gate": self.live_gate,
                "fill_simulation": self.fill_simulation,
                "commands_submitted": self.commands_submitted,
                "commands_resent": self.commands_resent,
                "sqs_recomputed": self.sqs_recomputed,
                "socket_opened": self.socket_opened,
                "credential_resolved": self.credential_resolved,
                "gap_0056_deferred": GAP_0056_DEFERRED,
            }
        )

    def use_as_admission_gate(self) -> Result[None]:
        return refuse_admission_gate(purpose="admission")

    def use_as_live_gate(self) -> Result[None]:
        return refuse_admission_gate(purpose="live")

    def restore_into_seat(
        self,
        *,
        target_world: object,
        target_seat: object = None,
    ) -> Result[None]:
        token = (
            clean_token(target_world) if not isinstance(target_world, World) else target_world.value
        )
        seat = clean_token(target_seat) or ""
        if token in {"live", "paper"} or seat in {"live", "paper"}:
            return refuse_restore_into_live(target_world=token, target_seat=seat)
        if token != World.REPLAY.value:
            return refuse_restore_into_live(target_world=token, target_seat=seat)
        return refuse_restore_into_live(target_world=token, target_seat=seat or "any")


def run_recorded_day(spec: ReplayJobSpec) -> Result[ReplayDiffReport]:
    """Replay one sealed interval through unforked ``run_slice`` and diff."""
    outside = assert_outside_node_process()
    if is_refusal(outside):
        return outside
    day = spec.import_port.read_interval(
        source_world=spec.source_world,
        room_role=spec.room_role,
        prefix_id=spec.prefix_id,
        start_ns=spec.start_ns,
        end_ns=spec.end_ns,
    )
    if is_refusal(day):
        return day
    recorded = day.value
    if recorded.composition_fp != spec.composition_fp:
        return invalid(
            "composition_fp",
            "replay uses the same resolved node-config fingerprint as the recorded day",
            spec=spec.composition_fp,
            recorded=recorded.composition_fp,
        )
    composed = _compose(spec, recorded)
    if is_refusal(composed):
        return composed
    composition = composed.value
    preflight = _preflight(composition)
    if is_refusal(preflight):
        return preflight
    report = _drive_and_diff(composition, recorded)
    if is_refusal(report):
        return report
    return report


def diff_recorded_day(
    recorded: RecordedDay,
    *,
    produced_decisions: Sequence[Mapping[str, object]],
    produced_controls: Sequence[Mapping[str, object]],
    commands_submitted: int,
    composition: ReplayComposition,
) -> ReplayDiffReport:
    """Structured decision/control/command diff with complete provenance."""
    decision_rows = _compare_stream("decision", recorded.decisions, produced_decisions)
    control_rows = _compare_stream("control", recorded.controls, produced_controls)
    command_rows = (
        MappingProxyType(
            {
                "kind": "command",
                "recorded_count": len(recorded.commands),
                "produced_submits": commands_submitted,
                "resent": False,
                "equal": commands_submitted == 0,
                "world": World.REPLAY.value,
            }
        ),
    )
    decisions_equal = all(bool(row.get("equal")) for row in decision_rows)
    controls_equal = all(bool(row.get("equal")) for row in control_rows)
    clean = (
        decisions_equal
        and controls_equal
        and commands_submitted == 0
        and composition.fill_simulation is False
        and composition.socket_opened is False
        and composition.credential_resolved is False
    )
    provenance = MappingProxyType(
        {
            "port": REPLAY_IMPORT_PORT,
            "source_world": recorded.source_world.value,
            "replay_world": World.REPLAY.value,
            "writer": {
                "machine": composition.writer.machine,
                "role": composition.writer.role,
                "stream": composition.writer.stream,
                "boot_epoch_id": composition.writer.boot_epoch_id,
            },
            "venue_kind": composition.venue_client.kind.value,
            "composition": dict(composition.as_mapping()),
        }
    )
    return ReplayDiffReport(
        world=World.REPLAY,
        composition_fp=composition.composition_fp,
        interval=MappingProxyType({"start_ns": recorded.start_ns, "end_ns": recorded.end_ns}),
        provenance=provenance,
        decisions=decision_rows,
        controls=control_rows,
        commands=command_rows,
        clean=clean,
        commands_submitted=commands_submitted,
        commands_resent=0,
        sqs_recomputed=False,
        socket_opened=composition.socket_opened,
        credential_resolved=composition.credential_resolved,
        fill_simulation=composition.fill_simulation,
    )


def _compose(spec: ReplayJobSpec, day: RecordedDay) -> Result[ReplayComposition]:
    selection = select_venue_client(World.REPLAY, day.venue_id)
    if is_refusal(selection):
        return selection
    if selection.value.kind is not VenueClientKind.REPLAY:
        return refuse_live_venue_client(kind=selection.value.kind)
    writer = allocate_replay_writer(
        machine=spec.machine,
        role="replay-adapter",
        stream=f"replay:{day.venue_id.value}:{day.account.account_id}",
        boot_epoch_id=spec.boot_epoch_id,
    )
    if is_refusal(writer):
        return writer
    recorded_obs = [dict(item) for item in day.observations]
    if not any(item.get("kind") == "capability-profile" for item in recorded_obs):
        recorded_obs.insert(
            0,
            {
                "kind": "capability-profile",
                "profile": {
                    "verified": True,
                    "static_declaration_present": True,
                    "measured_at_connection": True,
                    "profile_version": 1,
                    "command_sequencer_open": True,
                    "market_data_recordable": True,
                    "proto_tag": 91,
                },
            },
        )
    adapter = ReplayAdapter.try_create(World.REPLAY, day.venue_id, recorded=recorded_obs)
    if is_refusal(adapter):
        return adapter
    walls = _clock_walls(day)
    monos = tuple(7_000_000_000 + index * 1_000_000 for index in range(max(8, len(walls) * 2 + 4)))
    clock = DataDrivenClock(
        boot_epoch_id=spec.boot_epoch_id,
        wall_instants=walls,
        monotonic_ns=monos,
    )
    return Ok(
        ReplayComposition(
            world=World.REPLAY,
            composition_fp=spec.composition_fp,
            venue_id=day.venue_id,
            account=day.account,
            writer=writer.value,
            venue_client=adapter.value,
            clock=clock,
            socket_opened=adapter.value.socket_opened,
            credential_resolved=adapter.value.credential_resolved,
            live_sink=False,
            secrets_resolved=False,
        )
    )


def _preflight(composition: ReplayComposition) -> Result[None]:
    if composition.world is not World.REPLAY:
        return policy(
            "world",
            "replay composition world is replay",
            failure_id=_WRONG_WORLD_ID,
            world=composition.world.value,
        )
    if composition.venue_client.kind is not VenueClientKind.REPLAY:
        return refuse_live_venue_client(kind=composition.venue_client.kind)
    if composition.socket_opened or composition.venue_client.socket_opened:
        return refuse_network(target="socket")
    if composition.credential_resolved or composition.venue_client.credential_resolved:
        return refuse_secret_resolution()
    if composition.live_sink or composition.secrets_resolved:
        return refuse_live_sink()
    if composition.fill_simulation:
        return refuse_fill_simulation()
    if not composition.writer.role.startswith(REPLAY_WRITER_ROLE_PREFIX):
        return policy(
            "writer",
            "replay WriterIds must stay in the disjoint replay namespace",
            failure_id=_DISJOINT_ID,
            role=composition.writer.role,
        )
    opened = composition.venue_client.open_session(composition.account)
    if is_refusal(opened):
        return opened
    caps = composition.venue_client.verify_capabilities()
    if is_refusal(caps):
        return caps
    return Ok(None)


def _drive_and_diff(composition: ReplayComposition, day: RecordedDay) -> Result[ReplayDiffReport]:
    observation_sink = ReplayWorldSink()
    journal_sink = ReplayWorldSink()
    accumulator = RecordingAccumulator.try_create(
        venue_id=composition.venue_id,
        account=composition.account,
        writer_id=composition.writer,
        observation_sink=observation_sink,
        journal_sink=journal_sink,
        accumulator_bound=_ACCUMULATOR_BOUND,
        writer_name=f"replay-recording-accumulator:{composition.writer.boot_epoch_id}",
    )
    if is_refusal(accumulator):
        return accumulator
    declared = DeclaredStream.try_create(day.stream_id)
    if is_refusal(declared):
        return declared
    streams = StreamSet.try_create([declared.value])
    if is_refusal(streams):
        return streams
    handler = ReplaySliceHandler(day=day)
    loop = CommandStreamLoop.try_create(
        accumulator=accumulator.value,
        stream_set=streams.value,
        clock=composition.clock,
        max_slice_latency=_MAX_SLICE_LATENCY_NS,
        handler=handler,
    )
    if is_refusal(loop):
        return loop
    driver = loop.value
    produced_controls: list[Mapping[str, object]] = []
    for raw in day.observations:
        if raw.get("kind") == "capability-profile":
            continue
        ns = raw.get("receive_wall_time_ns")
        wall: Instant | None = None
        if isinstance(ns, int) and not isinstance(ns, bool):
            built = Instant.try_create(ns)
            if is_refusal(built):
                return built
            wall = built.value
        payload = dict(raw)
        payload.setdefault("stream_id", day.stream_id)
        payload.setdefault("world", World.REPLAY.value)
        pushed = driver.push_from_port_observation(payload, receive_wall=wall)
        if is_refusal(pushed):
            return pushed
    driven = driver.close_frontier()
    if is_refusal(driven):
        if driven.context.get("field") in {"monotonic_ns", "wall_instants"}:
            return unavailable(
                "clock",
                "replay-clock exhaustion is a typed refusal (DEC-0206)",
                failure_id=_CLOCK_ID,
                cursor=driven.context.get("cursor"),
                script_length=driven.context.get("script_length"),
            )
        return driven
    if driven.value is not None:
        produced_controls.append(
            MappingProxyType(
                {
                    "kind": "interpretation-cursor-commit",
                    "observation_id": driven.value.cursor_committed.get("observation_id"),
                    "receive_wall_time_ns": driven.value.cursor_committed.get(
                        "receive_wall_time_ns"
                    ),
                    "world": World.REPLAY.value,
                    "event_type": "control action",
                }
            )
        )
    submitted = composition.venue_client.commands_submitted
    if submitted:
        return refuse_command_submit()
    return Ok(
        diff_recorded_day(
            day,
            produced_decisions=handler.produced_decisions,
            produced_controls=produced_controls,
            commands_submitted=submitted,
            composition=composition,
        )
    )


def _clock_walls(day: RecordedDay) -> tuple[Instant, ...]:
    stamps = [day.start_ns, day.end_ns]
    for item in day.observations:
        raw = item.get("receive_wall_time_ns")
        if isinstance(raw, int) and not isinstance(raw, bool):
            stamps.append(raw)
    unique = sorted(set(stamps))
    while len(unique) < 4:
        unique.append(unique[-1] + 1_000_000 if unique else 0)
    instants: list[Instant] = []
    for ns in unique:
        built = Instant.try_create(ns)
        if is_ok(built):
            instants.append(built.value)
    return tuple(instants)


def _compare_stream(
    kind: Literal["decision", "control"],
    recorded: Sequence[Mapping[str, object]],
    produced: Sequence[Mapping[str, object]],
) -> tuple[Mapping[str, object], ...]:
    length = max(len(recorded), len(produced))
    rows: list[Mapping[str, object]] = []
    for index in range(length):
        rec = dict(recorded[index]) if index < len(recorded) else None
        prod = dict(produced[index]) if index < len(produced) else None
        rows.append(
            MappingProxyType(
                {
                    "kind": kind,
                    "index": index,
                    "recorded": rec,
                    "produced": prod,
                    "equal": _comparable(kind, rec) == _comparable(kind, prod),
                    "world": World.REPLAY.value,
                }
            )
        )
    if length == 0:
        rows.append(
            MappingProxyType(
                {
                    "kind": kind,
                    "index": 0,
                    "recorded": None,
                    "produced": None,
                    "equal": True,
                    "world": World.REPLAY.value,
                }
            )
        )
    return tuple(rows)


def _comparable(kind: str, row: Mapping[str, object] | None) -> tuple[object, ...]:
    if row is None:
        return (kind, None)
    if kind == "decision":
        return (
            kind,
            row.get("frontier_ns"),
            row.get("stream_id"),
            row.get("sqs_readiness"),
            row.get("entry_refused"),
        )
    return (kind, row.get("kind"), row.get("observation_id"), row.get("receive_wall_time_ns"))


def _as_nonneg_int(value: object, *, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(field, f"{field} is a non-negative int64", given=repr(value))
    return Ok(value)


# Credential-bind id kept referenced so the designed inventory matches emits.
def refuse_credential_bind(*, given: object = None) -> TypedRefusal:
    return policy(
        "credential",
        "replay resolves no credential reference and holds no venue secret",
        failure_id=_CREDENTIAL_ID,
        given=repr(given),
    )
