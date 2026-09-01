"""Durable-clock law for daemon evidence (FR-Q25; AD-6 clock law).

Every durable record carries ``occurred_at`` and ``recorded_at`` as int64 UTC
nanoseconds from ``qmf-core``'s injected :class:`~qmf.core.chrono.Clock`. No
component reads host local time and no worker timestamps its own evidence.
Wall-clock policies name an explicit IANA zone; duration policies are spans from
a recorded UTC instant and carry no timezone.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from qmf.core import Clock, Duration, Instant, Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "KNOWLEDGE_TIME_BOUND",
    "DaemonClock",
    "DurableTimestamps",
    "DurationPolicy",
    "WallClockPolicy",
    "refuse_host_local_time",
    "refuse_worker_evidence_timestamp",
]

KNOWLEDGE_TIME_BOUND: Final[str] = "as_of_recorded_at"

# Closed vocabulary of operator-facing wall-clock policy kinds (AD-6 clock law).
WallClockPolicyKind = Literal[
    "quiet_hours",
    "routine_cron",
    "rollup",
    "ledger_date_index",
]


@dataclass(frozen=True, slots=True)
class DurableTimestamps:
    """``occurred_at`` / ``recorded_at`` as int64 UTC nanoseconds (FR-Q25)."""

    occurred_at: int
    recorded_at: int

    def as_mapping(self) -> MappingProxyType[str, int]:
        """Frozen timestamp fields for a durable record row."""
        return MappingProxyType(
            {
                "occurred_at": self.occurred_at,
                "recorded_at": self.recorded_at,
            }
        )


@dataclass(frozen=True, slots=True)
class WallClockPolicy:
    """Operator-facing wall-clock policy with an explicit IANA zone (FR-Q25).

    The zone is resolved at evaluation time in the daemon — never implied by the
    host local zone.
    """

    kind: WallClockPolicyKind
    iana_zone: str

    def resolve_zone(self) -> Result[ZoneInfo]:
        """Resolve the named IANA zone at evaluation time."""
        return _resolve_iana_zone(self.iana_zone)


@dataclass(frozen=True, slots=True)
class DurationPolicy:
    """Duration policy: a span from a recorded UTC instant, no timezone (FR-Q25)."""

    name: str
    span: Duration
    from_recorded_at: int

    def deadline(self) -> Result[Instant]:
        """UTC instant at ``from_recorded_at + span`` (checked arithmetic)."""
        start = Instant.try_create(self.from_recorded_at)
        if is_refusal(start):
            return start
        return start.value.add_duration(self.span)


def refuse_host_local_time(*, attempted: object = None) -> Result[object]:
    """Refuse any host-local time read (FR-Q25; AD-6).

    Components obtain time only from the daemon's injected ``qmf-core`` clock.
    """
    return policy_rejection(
        "host_local_time",
        "no component reads host local time; durable and policy time come only "
        "from qmf-core's clock via the daemon (FR-Q25; AD-6)",
        attempted=repr(attempted),
    )


def refuse_worker_evidence_timestamp(*, attempted: object = None) -> Result[object]:
    """Refuse a worker-authored evidence timestamp (FR-Q25; AD-6).

    The daemon records evidence time; workers may not stamp their own evidence.
    """
    return policy_rejection(
        "worker_evidence_timestamp",
        "no worker timestamps its own evidence; the daemon records occurred_at "
        "and recorded_at from qmf-core's clock (FR-Q25; AD-6)",
        attempted=repr(attempted),
    )


def _resolve_iana_zone(iana_zone: object) -> Result[ZoneInfo]:
    if not isinstance(iana_zone, str) or iana_zone.strip() == "":
        return invalid_input(
            "iana_zone",
            "a wall-clock policy carries an explicit non-empty IANA zone "
            "(FR-Q25; AD-6)",
            given=repr(iana_zone),
        )
    try:
        return Ok(ZoneInfo(iana_zone))
    except ZoneInfoNotFoundError:
        return invalid_input(
            "iana_zone",
            "wall-clock policy IANA zone must resolve in the tz database at "
            "evaluation time (FR-Q25; AD-6)",
            given=iana_zone,
        )
    except Exception as exc:  # ZoneInfo can raise other OS errors on bad paths
        return invalid_input(
            "iana_zone",
            f"wall-clock policy IANA zone could not be resolved: {exc}",
            given=iana_zone,
        )


def _try_wall_clock_kind(kind: object) -> Result[WallClockPolicyKind]:
    allowed: dict[str, WallClockPolicyKind] = {
        "quiet_hours": "quiet_hours",
        "routine_cron": "routine_cron",
        "rollup": "rollup",
        "ledger_date_index": "ledger_date_index",
    }
    if isinstance(kind, str) and kind in allowed:
        return Ok(allowed[kind])
    return invalid_input(
        "kind",
        "wall-clock policy kind is one of quiet_hours, routine_cron, rollup, "
        "ledger_date_index (FR-Q25; AD-6)",
        given=repr(kind),
        allowed=sorted(allowed),
    )


class DaemonClock:
    """Daemon facade over an injected ``qmf-core`` :class:`~qmf.core.chrono.Clock`.

    Stamps durable records, evaluates wall-clock and duration policies, and
    refuses host-local and worker-authored evidence timestamps.
    """

    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    @property
    def boot_epoch_id(self) -> str:
        return self._clock.boot_epoch_id

    @property
    def injected(self) -> Clock:
        """The injected qmf-core clock — never the host local clock."""
        return self._clock

    def wall_now(self) -> Result[Instant]:
        """Current UTC wall instant from the injected clock."""
        return self._clock.wall_now()

    def stamp_durable(
        self,
        *,
        occurred_at: Instant | int | None = None,
        worker_authored_timestamp: object = None,
    ) -> Result[DurableTimestamps]:
        """Supply ``occurred_at`` and ``recorded_at`` as int64 UTC nanoseconds.

        ``recorded_at`` is always the daemon's clock reading at stamp time.
        ``occurred_at`` defaults to the same instant; an external occurrence may
        be supplied as an :class:`~qmf.core.chrono.Instant` or int64 ns count.
        A worker-authored timestamp argument is always refused.
        """
        if worker_authored_timestamp is not None:
            return refuse_worker_evidence_timestamp(attempted=worker_authored_timestamp)

        recorded = self._clock.wall_now()
        if is_refusal(recorded):
            return recorded
        recorded_ns = recorded.value.value_ns

        if occurred_at is None:
            return Ok(
                DurableTimestamps(occurred_at=recorded_ns, recorded_at=recorded_ns)
            )

        if isinstance(occurred_at, Instant):
            return Ok(
                DurableTimestamps(
                    occurred_at=occurred_at.value_ns,
                    recorded_at=recorded_ns,
                )
            )
        if isinstance(occurred_at, int) and not isinstance(occurred_at, bool):
            instant = Instant.try_create(occurred_at)
            if is_refusal(instant):
                return instant
            return Ok(
                DurableTimestamps(
                    occurred_at=instant.value.value_ns,
                    recorded_at=recorded_ns,
                )
            )
        return invalid_input(
            "occurred_at",
            "occurred_at is an Instant or int64 UTC nanoseconds from qmf-core's "
            "clock vocabulary (FR-Q25; AD-6)",
            given=repr(occurred_at),
        )

    def stamp_evidence_record(
        self,
        record: dict[str, object],
        *,
        occurred_at: Instant | int | None = None,
        journal_seq: int | None = None,
        announcement_bound: bool = True,
        worker_authored_timestamp: object = None,
    ) -> Result[dict[str, object]]:
        """Stamp a durable evidence mapping and optionally its announcement seq.

        Announcement-bound stores receive ``journal_seq``; telemetry (exempt)
        omits it. Worker-authored timestamp fields on the input are refused.
        """
        if worker_authored_timestamp is not None:
            return refuse_worker_evidence_timestamp(attempted=worker_authored_timestamp)
        for banned in ("occurred_at", "recorded_at"):
            if banned in record:
                return refuse_worker_evidence_timestamp(
                    attempted={banned: record[banned]}
                )

        stamps = self.stamp_durable(occurred_at=occurred_at)
        if is_refusal(stamps):
            return stamps

        out = dict(record)
        out["occurred_at"] = stamps.value.occurred_at
        out["recorded_at"] = stamps.value.recorded_at
        if announcement_bound:
            if journal_seq is None:
                return invalid_input(
                    "journal_seq",
                    "an announcement-bound durable record includes its "
                    "announcement journal_seq (FR-Q25; AD-6)",
                )
            if not isinstance(journal_seq, int) or isinstance(journal_seq, bool) or journal_seq < 1:
                return invalid_input(
                    "journal_seq",
                    "journal_seq is a positive int allocated by the authoritative "
                    "journal (FR-Q25; AD-6)",
                    given=repr(journal_seq),
                )
            out["journal_seq"] = journal_seq
        elif "journal_seq" in out:
            return policy_rejection(
                "journal_seq",
                "a telemetry record carries occurred_at and recorded_at but no "
                "journal_seq (FR-Q25; AD-6, AD-23)",
            )
        return Ok(out)

    def wall_clock_policy(
        self, kind: object, iana_zone: object
    ) -> Result[WallClockPolicy]:
        """Build a wall-clock policy that carries an explicit IANA zone."""
        kind_result = _try_wall_clock_kind(kind)
        if is_refusal(kind_result):
            return kind_result
        zone = _resolve_iana_zone(iana_zone)
        if is_refusal(zone):
            return zone
        # _resolve_iana_zone already validated a non-empty str.
        return Ok(
            WallClockPolicy(kind=kind_result.value, iana_zone=str(iana_zone))
        )

    def evaluate_wall_clock_policy(
        self, policy: WallClockPolicy, *, at: Instant | None = None
    ) -> Result[tuple[ZoneInfo, Instant]]:
        """Resolve the policy's IANA zone at evaluation time against ``at`` or now."""
        zone = policy.resolve_zone()
        if is_refusal(zone):
            return zone
        instant = Ok(at) if at is not None else self.wall_now()
        if is_refusal(instant):
            return instant
        # Instant is always UTC; zone is for civil interpretation only.
        return Ok((zone.value, instant.value))

    def duration_policy(
        self,
        name: object,
        span_ns: object,
        *,
        from_recorded_at: object,
    ) -> Result[DurationPolicy]:
        """Build a duration policy measured from a recorded UTC instant (no zone)."""
        if not isinstance(name, str) or name.strip() == "":
            return invalid_input(
                "name",
                "a duration policy names a non-empty policy id (FR-Q25; AD-6)",
                given=repr(name),
            )
        span = Duration.try_create(span_ns)
        if is_refusal(span):
            return span
        start = Instant.try_create(from_recorded_at)
        if is_refusal(start):
            return start
        return Ok(
            DurationPolicy(
                name=name,
                span=span.value,
                from_recorded_at=start.value.value_ns,
            )
        )
