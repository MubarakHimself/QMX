"""Named one-way replay import port over sealed-archive (TN-21 / DEC-0229).

This is the single sanctioned cross-world READ. There is no write exception.
Live evidence enters replay only through this port; replay never writes live
or paper rooms. GAP-0056 stays deferred: the port carries recorded observations
and signal snapshots, never a fill model.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    Account,
    AccountRole,
    Ok,
    Result,
    TypedRefusal,
    VenueId,
    World,
    is_refusal,
)

from qmn.data.sealed_archive import SEALED_ARCHIVE_ROLE, SealedArchive
from qmn.mis.signal_snapshot import ProducerReadiness
from qmn.replay._refuse import clean_token, invalid, policy, unavailable

__all__ = [
    "FILL_SIMULATION_IN_REPLAY",
    "GAP_0056_DEFERRED",
    "RECORDED_DAY_KIND",
    "REPLAY_IMPORT_PORT",
    "REPLAY_IMPORT_SURFACE",
    "RecordedDay",
    "RecordedSignalSnapshot",
    "ReplayImportPort",
    "decode_recorded_day",
    "encode_recorded_day",
    "refuse_cross_world_write",
    "refuse_fill_simulation",
    "refuse_sqs_recompute",
]


REPLAY_IMPORT_SURFACE: Final[str] = "qmn.replay.import_port"
REPLAY_IMPORT_PORT: Final[str] = "replay-import"
RECORDED_DAY_KIND: Final[str] = "qmn-replay-recorded-day"
RECORDED_DAY_FORMAT_VERSION: Final[int] = 1
FILL_SIMULATION_IN_REPLAY: Final[bool] = False
GAP_0056_DEFERRED: Final[bool] = True

_CROSS_WORLD_WRITE_ID: Final[str] = "replay.cross_world_write"
_MISSING_INTERVAL_ID: Final[str] = "replay.missing_sealed_interval"
_FILL_ID: Final[str] = "replay.fill_simulation"
_SQS_RECOMPUTE_ID: Final[str] = "replay.sqs_recompute"


def refuse_cross_world_write(*, target_world: object = None) -> TypedRefusal:
    """No write exception to AD-19 exists (DEC-0206, DEC-0229)."""
    return policy(
        "write",
        "the replay import port is read-only; no cross-world write is possible",
        failure_id=_CROSS_WORLD_WRITE_ID,
        target_world=repr(target_world),
        port=REPLAY_IMPORT_PORT,
    )


def refuse_fill_simulation(*, reason: object = None) -> TypedRefusal:
    """GAP-0056 remains deferred — replay diffs decisions, never fills."""
    del reason
    return policy(
        "fill",
        "replay has no fill simulation in V1; GAP-0056 remains deferred (DEC-0206, DEC-0229)",
        failure_id=_FILL_ID,
        fill_simulation=FILL_SIMULATION_IN_REPLAY,
        gap="GAP-0056",
        deferred=GAP_0056_DEFERRED,
    )


def refuse_sqs_recompute(*, frontier_ns: object = None) -> TypedRefusal:
    """Replay reuses recorded signal snapshots; it never recomputes SQS."""
    return policy(
        "sqs",
        "replay reuses the recorded per-instant signal snapshot; missing "
        "snapshots read not_ready and refuse entries — SQS is never recomputed",
        failure_id=_SQS_RECOMPUTE_ID,
        frontier_ns=repr(frontier_ns),
    )


@dataclass(frozen=True, slots=True)
class RecordedSignalSnapshot:
    """Compact recorded signal snapshot — evidence, never a live recompute."""

    frontier_ns: int
    environment: str
    feed_state: str
    sqs_readiness: ProducerReadiness
    sqs_hard_block: bool
    snapshot_fp1: str
    labeler_version: str

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "frontier_ns": self.frontier_ns,
                "environment": self.environment,
                "feed_state": self.feed_state,
                "sqs_readiness": self.sqs_readiness.value,
                "sqs_hard_block": self.sqs_hard_block,
                "snapshot_fp1": self.snapshot_fp1,
                "labeler_version": self.labeler_version,
            }
        )

    def entry_refused(self) -> bool:
        """Missing/non-ok SQS is a conservative hard block (DEC-0206)."""
        return self.sqs_readiness is not ProducerReadiness.OK or self.sqs_hard_block


@dataclass(frozen=True, slots=True)
class RecordedDay:
    """One sealed-archive interval of recorded node evidence."""

    source_world: World
    venue_id: VenueId
    account: Account
    stream_id: str
    composition_fp: str
    start_ns: int
    end_ns: int
    observations: tuple[Mapping[str, object], ...]
    snapshots: tuple[RecordedSignalSnapshot, ...]
    decisions: tuple[Mapping[str, object], ...]
    controls: tuple[Mapping[str, object], ...]
    commands: tuple[Mapping[str, object], ...]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "format_version": RECORDED_DAY_FORMAT_VERSION,
                "kind": RECORDED_DAY_KIND,
                "source_world": self.source_world.value,
                "venue_id": self.venue_id.value,
                "account_id": self.account.account_id,
                "account_role": self.account.role.value,
                "stream_id": self.stream_id,
                "composition_fp": self.composition_fp,
                "interval": {"start_ns": self.start_ns, "end_ns": self.end_ns},
                "observations": [dict(item) for item in self.observations],
                "signal_snapshots": [dict(item.as_mapping()) for item in self.snapshots],
                "decisions": [dict(item) for item in self.decisions],
                "controls": [dict(item) for item in self.controls],
                "commands": [dict(item) for item in self.commands],
            }
        )

    def snapshot_at(self, frontier_ns: int) -> RecordedSignalSnapshot | None:
        """Exact-instant lookup; absence means not_ready (DEC-0206)."""
        for item in self.snapshots:
            if item.frontier_ns == frontier_ns:
                return item
        return None

    def sqs_readiness_at(self, frontier_ns: int) -> ProducerReadiness:
        snap = self.snapshot_at(frontier_ns)
        if snap is None:
            return ProducerReadiness.NOT_READY
        return snap.sqs_readiness


def encode_recorded_day(day: RecordedDay) -> bytes:
    """Canonical JSON bytes for a sealed-archive prefix payload."""
    return (json.dumps(dict(day.as_mapping()), sort_keys=True) + "\n").encode("utf-8")


def decode_recorded_day(payload: object) -> Result[RecordedDay]:
    """Parse a sealed-archive prefix into a recorded day."""
    if isinstance(payload, (bytes, bytearray)):
        try:
            body = json.loads(bytes(payload).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return invalid("payload", "recorded-day prefix is UTF-8 JSON")
    elif isinstance(payload, Mapping):
        body = dict(cast("Mapping[str, object]", payload))
    else:
        return invalid(
            "payload",
            "recorded-day payload is JSON bytes or a mapping",
            given=type(payload).__name__,
        )
    if not isinstance(body, dict):
        return invalid("payload", "recorded-day JSON is an object")
    record = cast("dict[str, object]", body)
    if record.get("kind") != RECORDED_DAY_KIND:
        return invalid(
            "kind",
            "sealed-archive replay prefix names qmn-replay-recorded-day",
            given=repr(record.get("kind")),
        )
    version = record.get("format_version")
    if version != RECORDED_DAY_FORMAT_VERSION:
        return invalid(
            "format_version",
            "recorded-day format_version is 1",
            given=repr(version),
        )
    source = _as_world(record.get("source_world"))
    if is_refusal(source):
        return source
    venue = VenueId.try_create(record.get("venue_id"))
    if is_refusal(venue):
        return venue
    role_token = clean_token(record.get("account_role")) or AccountRole.DEMO.value
    try:
        role = AccountRole(role_token)
    except ValueError:
        return invalid("account_role", "account_role is a closed AccountRole", given=role_token)
    account_id = clean_token(record.get("account_id"))
    if account_id is None:
        return invalid("account_id", "recorded day names a non-empty account id")
    account = Account.try_create(account_id, venue.value, role)
    if is_refusal(account):
        return account
    stream_id = clean_token(record.get("stream_id"))
    if stream_id is None:
        return invalid("stream_id", "recorded day names a non-empty stream id")
    composition_fp = clean_token(record.get("composition_fp"))
    if composition_fp is None:
        return invalid("composition_fp", "recorded day cites the resolved node-config fp1")
    interval = record.get("interval")
    if not isinstance(interval, Mapping):
        return invalid("interval", "recorded day carries a {start_ns, end_ns} interval")
    window = cast("Mapping[str, object]", interval)
    start_ns = _as_nonneg_int(window.get("start_ns"), field="start_ns")
    if is_refusal(start_ns):
        return start_ns
    end_ns = _as_nonneg_int(window.get("end_ns"), field="end_ns")
    if is_refusal(end_ns):
        return end_ns
    if end_ns.value <= start_ns.value:
        return invalid(
            "interval",
            "recorded-day interval is a non-empty [start_ns, end_ns)",
            start_ns=start_ns.value,
            end_ns=end_ns.value,
        )
    observations = _as_row_tuple(record.get("observations"), field="observations")
    if is_refusal(observations):
        return observations
    snapshots = _as_snapshots(record.get("signal_snapshots"))
    if is_refusal(snapshots):
        return snapshots
    decisions = _as_row_tuple(record.get("decisions"), field="decisions")
    if is_refusal(decisions):
        return decisions
    controls = _as_row_tuple(record.get("controls"), field="controls")
    if is_refusal(controls):
        return controls
    commands = _as_row_tuple(record.get("commands"), field="commands")
    if is_refusal(commands):
        return commands
    return Ok(
        RecordedDay(
            source_world=source.value,
            venue_id=venue.value,
            account=account.value,
            stream_id=stream_id,
            composition_fp=composition_fp,
            start_ns=start_ns.value,
            end_ns=end_ns.value,
            observations=observations.value,
            snapshots=snapshots.value,
            decisions=decisions.value,
            controls=controls.value,
            commands=commands.value,
        )
    )


class ReplayImportPort:
    """Read-only sealed-archive crossing. The one AD-19 exception (DEC-0229)."""

    def __init__(self, archive: SealedArchive) -> None:
        self._archive = archive

    @property
    def name(self) -> str:
        return REPLAY_IMPORT_PORT

    @property
    def room_role(self) -> str:
        return SEALED_ARCHIVE_ROLE

    @property
    def writable(self) -> bool:
        return False

    def read_interval(
        self,
        *,
        source_world: object,
        room_role: object,
        prefix_id: object,
        start_ns: object,
        end_ns: object,
    ) -> Result[RecordedDay]:
        """Read one sealed interval. Never a hot-room or live-sink read."""
        resolved = _as_world(source_world)
        if is_refusal(resolved):
            return resolved
        start = _as_nonneg_int(start_ns, field="start_ns")
        if is_refusal(start):
            return start
        end = _as_nonneg_int(end_ns, field="end_ns")
        if is_refusal(end):
            return end
        payload = self._archive.read_prefix(
            world=resolved.value,
            room_role=room_role,
            prefix_id=prefix_id,
        )
        if is_refusal(payload):
            return unavailable(
                "interval",
                "replay reads live evidence only through the named one-way "
                "replay-import port over a sealed-archive interval",
                failure_id=_MISSING_INTERVAL_ID,
                prefix_id=repr(prefix_id),
                room_role=repr(room_role),
                after_condition="sealed-archive watermarked copy of the interval",
            )
        day = decode_recorded_day(payload.value)
        if is_refusal(day):
            return day
        if day.value.start_ns != start.value or day.value.end_ns != end.value:
            return invalid(
                "interval",
                "selected interval must match the sealed recorded-day window",
                selected_start_ns=start.value,
                selected_end_ns=end.value,
                recorded_start_ns=day.value.start_ns,
                recorded_end_ns=day.value.end_ns,
            )
        if day.value.source_world is not resolved.value:
            return invalid(
                "source_world",
                "import port source world must match the sealed prefix world",
                selected=resolved.value.value,
                recorded=day.value.source_world.value,
            )
        return day

    def write(
        self,
        *,
        target_world: object,
        payload: object = None,
    ) -> Result[None]:
        """Always refuse — there is no write exception."""
        del payload
        return refuse_cross_world_write(target_world=target_world)

    def write_to_live(self, payload: object = None) -> Result[None]:
        return self.write(target_world=World.LIVE, payload=payload)

    def write_to_paper(self, payload: object = None) -> Result[None]:
        return self.write(target_world="paper", payload=payload)


def _as_world(value: object) -> Result[World]:
    if isinstance(value, World):
        resolved = value
    elif isinstance(value, str):
        try:
            resolved = World(value)
        except ValueError:
            return invalid(
                "world",
                "world is one of the closed set live | replay | simulated",
                given=value,
            )
    else:
        return invalid(
            "world",
            "world is a World or one of the closed set live | replay | simulated",
            given=repr(value),
        )
    if resolved is World.SIMULATED:
        return policy(
            "world",
            "world = simulated is reserved-unusable; replay does not import it",
            world=resolved.value,
        )
    return Ok(resolved)


def _as_nonneg_int(value: object, *, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(field, f"{field} is a non-negative int64", given=repr(value))
    return Ok(value)


def _as_row_tuple(value: object, *, field: str) -> Result[tuple[Mapping[str, object], ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(field, f"{field} is a sequence of mappings", given=type(value).__name__)
    rows: list[Mapping[str, object]] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, Mapping):
            return invalid(
                field,
                f"each {field} row is a mapping",
                index=index,
                given=type(item).__name__,
            )
        rows.append(MappingProxyType(dict(cast("Mapping[str, object]", item))))
    return Ok(tuple(rows))


def _as_snapshots(value: object) -> Result[tuple[RecordedSignalSnapshot, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "signal_snapshots",
            "signal_snapshots is a sequence of recorded snapshot mappings",
            given=type(value).__name__,
        )
    out: list[RecordedSignalSnapshot] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, Mapping):
            return invalid(
                "signal_snapshots",
                "each recorded snapshot is a mapping",
                index=index,
            )
        row = cast("Mapping[str, object]", item)
        frontier = _as_nonneg_int(row.get("frontier_ns"), field="frontier_ns")
        if is_refusal(frontier):
            return frontier
        environment = clean_token(row.get("environment"))
        if environment is None:
            return invalid("environment", "a recorded snapshot is environment-keyed")
        feed_state = clean_token(row.get("feed_state"))
        if feed_state is None:
            return invalid("feed_state", "a recorded snapshot names feed_state")
        readiness_token = clean_token(row.get("sqs_readiness"))
        if readiness_token is None:
            return invalid("sqs_readiness", "a recorded snapshot names sqs_readiness")
        try:
            readiness = ProducerReadiness(readiness_token)
        except ValueError:
            return invalid(
                "sqs_readiness",
                "sqs_readiness is ok|not_ready|unavailable|stale|refused",
                given=readiness_token,
            )
        hard_block = row.get("sqs_hard_block")
        if not isinstance(hard_block, bool):
            hard_block = readiness is not ProducerReadiness.OK
        snapshot_fp1 = clean_token(row.get("snapshot_fp1"))
        if snapshot_fp1 is None:
            return invalid("snapshot_fp1", "a recorded snapshot carries its fp1")
        labeler_version = clean_token(row.get("labeler_version")) or "recorded"
        out.append(
            RecordedSignalSnapshot(
                frontier_ns=frontier.value,
                environment=environment,
                feed_state=feed_state,
                sqs_readiness=readiness,
                sqs_hard_block=hard_block,
                snapshot_fp1=snapshot_fp1,
                labeler_version=labeler_version,
            )
        )
    return Ok(tuple(out))
