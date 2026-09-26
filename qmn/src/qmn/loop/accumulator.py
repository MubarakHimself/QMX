"""Push-to-pull recording accumulator — single first writer (TN-5 / Story 24.4).

VenueClientPort observations for one ``(VenueId, account)`` stream enter here
and nowhere else. Recording through the governed intake
(:class:`~qmf.core.ObservationSink`) and journaling under the venue
:class:`~qmf.core.WriterId` precede foldability. Overflow never drops
execution or system observations; market-data coalescing emits ``data quality``
evidence and the cycle receives entry-side ``no-new-entry`` (DEC-0190).
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import ClassVar, Final, cast

from qmf.core import (
    Account,
    Instant,
    JournalSink,
    ObservationSink,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    SinkAck,
    TypedRefusal,
    VenueId,
    WriterId,
    is_refusal,
    unpersistable,
)

from qmn.loop.kinds import (
    DATA_QUALITY_EVENT_TYPE,
    CycleBand,
    InboundObservation,
    ObservationClass,
    classify_observation,
)

__all__ = [
    "RecordingAccumulator",
    "clear_first_writer_registry",
    "first_writer_for",
    "stream_key",
]


_REGISTRY: Final[MutableMapping[str, str]] = {}


def stream_key(venue_id: VenueId, account: Account) -> str:
    """Canonical ``(VenueId, account)`` command-stream token."""
    return f"{venue_id.value}:{account.account_id}"


def first_writer_for(venue_id: VenueId, account: Account) -> str | None:
    """Return the registered sole first-writer id for the stream, if any."""
    return _REGISTRY.get(stream_key(venue_id, account))


def clear_first_writer_registry() -> None:
    """Test helper — drop every sole-first-writer registration."""
    _REGISTRY.clear()


@dataclass
class RecordingAccumulator:
    """Sole first writer of inbound observations for one command stream.

    Push path: stamp receive wall → record (observation sink) → journal under
    the venue WriterId → enqueue as foldable. Pull path: drain foldable
    observations for one frontier close. No sibling feed may write the same
    stream's inbound observations (FR-054; TN-5).
    """

    venue_id: VenueId
    account: Account
    writer_id: WriterId
    observation_sink: ObservationSink[Mapping[str, object]]
    journal_sink: JournalSink[Mapping[str, object]]
    accumulator_bound: int
    writer_name: str = "recording-accumulator"
    _foldable: list[InboundObservation] = field(default_factory=list[InboundObservation])
    _receive_seq: int = 0
    _cycle_band: CycleBand = CycleBand.OK
    _coalesce_events: list[Mapping[str, object]] = field(default_factory=list[Mapping[str, object]])
    _frontier: Instant | None = None
    _registered: bool = False

    # Class-level marker for "this module is the only first-writer path".
    SOLE_FIRST_WRITER: ClassVar[bool] = True

    @classmethod
    def try_create(
        cls,
        *,
        venue_id: object,
        account: object,
        writer_id: object,
        observation_sink: object,
        journal_sink: object,
        accumulator_bound: object,
        writer_name: object = "recording-accumulator",
    ) -> Result[RecordingAccumulator]:
        """Validate wiring and claim sole first-writer for the stream."""
        if not isinstance(venue_id, VenueId) or venue_id.value.strip() == "":
            return _invalid("venue_id", "accumulator binds a VenueId", given=repr(venue_id))
        if not isinstance(account, Account):
            return _invalid("account", "accumulator binds an Account", given=repr(account))
        if account.venue != venue_id:
            return _invalid(
                "account",
                "account must belong to the bound VenueId",
                venue=venue_id.value,
                account=account.account_id,
            )
        if not isinstance(writer_id, WriterId):
            return _invalid(
                "writer_id",
                "inbound observations journal under the venue WriterId",
                given=repr(type(writer_id).__name__),
            )
        if not callable(getattr(observation_sink, "emit", None)):
            return _invalid(
                "observation_sink",
                "governed intake is an ObservationSink",
                given=repr(type(observation_sink).__name__),
            )
        if not callable(getattr(journal_sink, "append", None)):
            return _invalid(
                "journal_sink",
                "journaling uses a JournalSink under the venue WriterId",
                given=repr(type(journal_sink).__name__),
            )
        if isinstance(accumulator_bound, bool) or not isinstance(accumulator_bound, int):
            return _invalid(
                "accumulator_bound",
                "accumulator_bound is a positive integer count (registry:accumulator_bound)",
                given=repr(accumulator_bound),
            )
        if accumulator_bound < 1:
            return _invalid(
                "accumulator_bound",
                "an unbounded or non-positive accumulator is an absent mechanism",
                given=accumulator_bound,
            )
        name = str(writer_name).strip() if writer_name is not None else ""
        if not name:
            return _invalid(
                "writer_name",
                "the sole first-writer registration names a non-empty writer",
                given=repr(writer_name),
            )
        key = stream_key(venue_id, account)
        existing = _REGISTRY.get(key)
        if existing is not None and existing != name:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "first_writer",
                    "reason": "no sibling feed or module writes inbound observations; "
                    "one push-to-pull accumulator is the single first writer per "
                    "(VenueId, account) stream",
                    "stream": key,
                    "registered": existing,
                    "attempted": name,
                },
            )
        acc = cls(
            venue_id=venue_id,
            account=account,
            writer_id=writer_id,
            observation_sink=observation_sink,  # type: ignore[arg-type]
            journal_sink=journal_sink,  # type: ignore[arg-type]
            accumulator_bound=accumulator_bound,
            writer_name=name,
        )
        _REGISTRY[key] = name
        acc._registered = True
        return Ok(acc)

    @property
    def key(self) -> str:
        """Command-stream key for this accumulator."""
        return stream_key(self.venue_id, self.account)

    @property
    def depth(self) -> int:
        """Foldable queue depth (post-record, pre-pull)."""
        return len(self._foldable)

    @property
    def cycle_band(self) -> CycleBand:
        """Current cycle band; ``no-new-entry`` after overflow or latency breach."""
        return self._cycle_band

    @property
    def frontier(self) -> Instant | None:
        """Latest stamped receive-wall frontier, or None before the first push."""
        return self._frontier

    @property
    def coalesce_events(self) -> tuple[Mapping[str, object], ...]:
        """Data-quality evidence emitted by market-data coalescing."""
        return tuple(self._coalesce_events)

    def push(
        self,
        *,
        observation_id: object,
        stream_id: object,
        receive_wall: object,
        payload: object,
        kind: object = None,
        observation_class: object = None,
        venue_instant: object = None,
        coalesce_key: object = None,
        closed: object = True,
    ) -> Result[InboundObservation]:
        """Record then enqueue one inbound observation as foldable.

        Order is mandatory: observation-sink emit and WriterId journal append
        happen before the observation becomes foldable. A sibling write path
        does not exist on this object.
        """
        klass: ObservationClass
        if observation_class is None:
            klass = classify_observation(kind if kind is not None else _payload_kind(payload))
        else:
            built_class = observation_class
            if not isinstance(built_class, ObservationClass):
                try:
                    klass = ObservationClass(str(built_class).strip().lower())
                except ValueError:
                    return _invalid(
                        "observation_class",
                        "observation_class is market-data | execution | system",
                        given=repr(observation_class),
                    )
            else:
                klass = built_class

        key = coalesce_key
        if key is None and klass is ObservationClass.MARKET_DATA:
            key = str(stream_id).strip() if stream_id is not None else None

        built = InboundObservation.try_create(
            observation_id=observation_id,
            stream_id=stream_id,
            observation_class=klass,
            receive_wall=receive_wall,
            payload=payload,
            venue_instant=venue_instant,
            coalesce_key=key,
            closed=closed,
        )
        if is_refusal(built):
            return built
        obs = built.value

        if self._frontier is None or obs.receive_wall.value_ns >= self._frontier.value_ns:
            self._frontier = obs.receive_wall
        else:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "receive_wall",
                    "reason": "the live frontier is monotonically non-decreasing by "
                    "the accumulator's receive-wall stamp",
                    "frontier_ns": self._frontier.value_ns,
                    "given_ns": obs.receive_wall.value_ns,
                },
            )

        recorded = self._record_and_journal(obs)
        if is_refusal(recorded):
            return recorded

        self._receive_seq += 1
        overflow = self._enqueue(obs)
        if is_refusal(overflow):
            return overflow
        return Ok(obs)

    def pull_foldable(self) -> tuple[InboundObservation, ...]:
        """Drain every foldable observation for the pending frontier close."""
        batch = tuple(self._foldable)
        self._foldable.clear()
        return batch

    def mark_latency_breach(
        self, *, elapsed_ns: int, bound_ns: int
    ) -> Result[Mapping[str, object]]:
        """Journal slice-latency breach evidence and raise entry-side no-new-entry."""
        evidence = {
            "event_type": DATA_QUALITY_EVENT_TYPE,
            "kind": "slice-latency-breach",
            "elapsed_ns": elapsed_ns,
            "max_slice_latency_ns": bound_ns,
            "band": CycleBand.NO_NEW_ENTRY.value,
            "entry_side_only": True,
            "writer": self._writer_fields(),
        }
        appended = self.journal_sink.append(MappingProxyType(dict(evidence)))
        if is_refusal(appended):
            return appended
        self._cycle_band = CycleBand.NO_NEW_ENTRY
        self._coalesce_events.append(MappingProxyType(dict(evidence)))
        return Ok(MappingProxyType(dict(evidence)))

    def clear_cycle_band(self) -> None:
        """Reset the per-cycle band after the affected cycle has consumed it."""
        self._cycle_band = CycleBand.OK

    def release(self) -> None:
        """Drop the sole-first-writer claim for this stream (shutdown / tests)."""
        if self._registered and _REGISTRY.get(self.key) == self.writer_name:
            del _REGISTRY[self.key]
            self._registered = False

    def _enqueue(self, obs: InboundObservation) -> Result[bool]:
        if len(self._foldable) < self.accumulator_bound:
            self._foldable.append(obs)
            return Ok(True)

        if obs.observation_class is ObservationClass.MARKET_DATA:
            coalesced = self._coalesce_market_data(obs)
            if is_refusal(coalesced):
                return coalesced
            self._cycle_band = CycleBand.NO_NEW_ENTRY
            return Ok(True)

        # Execution / system must never be dropped. Prefer coalescing an existing
        # market-data slot to make room; otherwise storage failure blocks entries.
        freed = self._evict_one_market_data_for(obs)
        if is_refusal(freed):
            return freed
        if freed.value:
            self._foldable.append(obs)
            self._cycle_band = CycleBand.NO_NEW_ENTRY
            return Ok(True)
        self._cycle_band = CycleBand.NO_NEW_ENTRY
        return unpersistable(
            "accumulator_bound cannot be honoured without dropping an execution "
            "or system observation; storage failure blocks entries only",
            context={
                "accumulator_bound": self.accumulator_bound,
                "depth": len(self._foldable),
                "observation_class": obs.observation_class.value,
                "band": CycleBand.NO_NEW_ENTRY.value,
            },
        )

    def _coalesce_market_data(self, obs: InboundObservation) -> Result[SinkAck]:
        key = obs.coalesce_key or obs.stream_id
        replaced = False
        for index, existing in enumerate(self._foldable):
            if (
                existing.observation_class is ObservationClass.MARKET_DATA
                and (existing.coalesce_key or existing.stream_id) == key
            ):
                self._foldable[index] = obs
                replaced = True
                break
        if not replaced:
            # No same-key slot: drop the oldest market-data row to keep bound.
            for index, existing in enumerate(self._foldable):
                if existing.observation_class is ObservationClass.MARKET_DATA:
                    self._foldable[index] = obs
                    key = existing.coalesce_key or existing.stream_id
                    replaced = True
                    break
        if not replaced:
            return unpersistable(
                "market-data coalescing found no market-data slot under accumulator_bound",
                context={
                    "accumulator_bound": self.accumulator_bound,
                    "depth": len(self._foldable),
                },
            )
        evidence = {
            "event_type": DATA_QUALITY_EVENT_TYPE,
            "kind": "market-data-coalesce",
            "coalesce_key": key,
            "retained_observation_id": obs.observation_id,
            "band": CycleBand.NO_NEW_ENTRY.value,
            "entry_side_only": True,
            "writer": self._writer_fields(),
        }
        appended = self.journal_sink.append(MappingProxyType(dict(evidence)))
        if is_refusal(appended):
            return appended
        self._coalesce_events.append(MappingProxyType(dict(evidence)))
        return appended

    def _evict_one_market_data_for(self, _obs: InboundObservation) -> Result[bool]:
        for index, existing in enumerate(self._foldable):
            if existing.observation_class is ObservationClass.MARKET_DATA:
                evidence = {
                    "event_type": DATA_QUALITY_EVENT_TYPE,
                    "kind": "market-data-coalesce",
                    "coalesce_key": existing.coalesce_key or existing.stream_id,
                    "evicted_observation_id": existing.observation_id,
                    "reason": "make-room-for-execution-or-system",
                    "band": CycleBand.NO_NEW_ENTRY.value,
                    "entry_side_only": True,
                    "writer": self._writer_fields(),
                }
                appended = self.journal_sink.append(MappingProxyType(dict(evidence)))
                if is_refusal(appended):
                    return appended
                self._coalesce_events.append(MappingProxyType(dict(evidence)))
                del self._foldable[index]
                return Ok(True)
        return Ok(False)

    def _record_and_journal(self, obs: InboundObservation) -> Result[bool]:
        event_type = _journal_event_type(obs)
        if is_refusal(event_type):
            return event_type
        identity = _identity_fields(obs.payload)
        record = {
            "kind": "governed-intake",
            "phase": "record-before-fold",
            "stream": self.key,
            "writer": self._writer_fields(),
            "observation": dict(obs.as_mapping()),
            "foldable": False,
            **identity,
        }
        raw = obs.payload.get("raw_payload")
        if isinstance(raw, Mapping):
            record["raw_payload"] = dict(cast("Mapping[str, object]", raw))
        emitted = self.observation_sink.emit(MappingProxyType(dict(record)))
        if is_refusal(emitted):
            return emitted
        journal_row: dict[str, object] = {
            "event_type": event_type.value,
            "kind": "accumulator-journal",
            "observation_id": obs.observation_id,
            "observation_class": obs.observation_class.value,
            "receive_wall_time_ns": obs.receive_wall.value_ns,
            "writer": self._writer_fields(),
            "sequence_hint": self._receive_seq + 1,
            **identity,
        }
        if obs.venue_instant is not None:
            journal_row["venue_instant_ns"] = obs.venue_instant.value_ns
        appended = self.journal_sink.append(MappingProxyType(dict(journal_row)))
        if is_refusal(appended):
            return appended
        return Ok(True)

    def _writer_fields(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "machine": self.writer_id.machine,
                "role": self.writer_id.role,
                "stream": self.writer_id.stream,
                "boot_epoch_id": self.writer_id.boot_epoch_id,
            }
        )


_CT13_SEVEN: Final[frozenset[str]] = frozenset(
    {
        "decision",
        "order",
        "fill",
        "risk transition",
        "promotion",
        "data quality",
        "control action",
    }
)
_IDENTITY_KEYS: Final[tuple[str, ...]] = (
    "source",
    "source_native_id",
    "revision",
    "event_time_ns",
    "known_at_ns",
)


def _identity_fields(payload: Mapping[str, object]) -> dict[str, object]:
    fields: dict[str, object] = {}
    for key in _IDENTITY_KEYS:
        if key in payload:
            fields[key] = payload[key]
    return fields


def _journal_event_type(obs: InboundObservation) -> Result[str]:
    proposed = obs.payload.get("ct13_event_type") or obs.payload.get("event_type")
    if isinstance(proposed, str) and proposed.strip() != "":
        event_type = proposed.strip().lower()
        if event_type == "observation":
            return TypedRefusal(
                category=RefusalCategory.UNSUPPORTED_CAPABILITY,
                retryability=Retryability.NO,
                context={
                    "field": "event_type",
                    "reason": "data intake never infers or mints an observation "
                    "journal type; CT-13's closed seven stand (FTR-01)",
                    "ftr": "FTR-01",
                    "failure_id": "data.intake.observation_journal_type",
                    "given": event_type,
                    "allowed_ct13": sorted(_CT13_SEVEN),
                },
            )
        if event_type not in _CT13_SEVEN:
            return TypedRefusal(
                category=RefusalCategory.UNSUPPORTED_CAPABILITY,
                retryability=Retryability.NO,
                context={
                    "field": "event_type",
                    "reason": "an eighth node-private journal type is refused (FTR-01)",
                    "ftr": "FTR-01",
                    "failure_id": "data.intake.observation_journal_type",
                    "given": event_type,
                    "allowed_ct13": sorted(_CT13_SEVEN),
                },
            )
        return Ok(event_type)
    if obs.observation_class is ObservationClass.MARKET_DATA:
        return Ok(DATA_QUALITY_EVENT_TYPE)
    if obs.observation_class is ObservationClass.EXECUTION:
        return Ok("fill")
    return Ok("control action")


def _payload_kind(payload: object) -> object:
    if isinstance(payload, Mapping):
        mapping = cast("Mapping[str, object]", payload)
        for key in ("kind", "wire_kind", "observation_kind"):
            if key in mapping:
                value: object = mapping[key]
                return value
    return "system"


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )
