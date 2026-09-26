"""CT-10 SourceObservation try_create resolvers and fp1 identity content.

Split from :mod:`qmf.data.observation` so the public module stays under the
Skylos god-file limits. Callers keep importing
:class:`~qmf.data.observation.SourceObservation` from :mod:`qmf.data.observation`.
"""

from __future__ import annotations

from typing import NamedTuple

from qmf.core import (
    Fingerprint,
    Instant,
    MonotonicReading,
    Ok,
    Result,
    World,
    WriterId,
    is_refusal,
)
from qmf.data.observation_types import (
    CONTRACT_FORMAT_VERSION,
    ForeignMoney,
    ForeignTimestamp,
    MarketDataContext,
    as_instant,
    clean_str,
    coerce_fingerprint,
    coerce_world,
    invalid,
    writer_identity,
)


class ObservationCore(NamedTuple):
    """Required identity parts resolved by :func:`resolve_observation_core`."""

    event_time: Instant
    known_at: Instant
    source: str
    source_native_id: str
    revision: str
    receive_wall_time: Instant
    writer: WriterId
    sequence: int
    world: World


class ObservationExtras(NamedTuple):
    """Optional blocks resolved by :func:`resolve_observation_extras`."""

    foreign_timestamp: ForeignTimestamp | None
    foreign_money: ForeignMoney | None
    market_data: MarketDataContext | None
    receive_monotonic_diagnostic: MonotonicReading | None
    correction_of: Fingerprint | None


def _require_sequence(sequence: object) -> Result[int]:
    """A per-writer non-negative integer sequence, or ``invalid input``."""
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        return invalid(
            "sequence",
            "sequence is required: a per-writer non-negative strictly-increasing integer",
            given=repr(sequence),
        )
    return Ok(sequence)


def resolve_observation_required(
    event_time: object,
    known_at: object,
    source: object,
    source_native_id: object,
    revision: object,
) -> Result[tuple[Instant, Instant, str, str, str]]:
    """Resolve event-time, known-at, and provenance tokens in admission order."""
    resolved_event_time = as_instant(event_time)
    if resolved_event_time is None:
        return invalid(
            "event_time",
            "event-time is required: an Instant or int64 UTC-nanosecond count "
            "(when the fact occurred)",
            given=repr(event_time),
        )
    resolved_known_at = as_instant(known_at)
    if resolved_known_at is None:
        return invalid(
            "known_at",
            "known-at is required: an Instant or int64 UTC-nanosecond count "
            "(when the fact became knowable)",
            given=repr(known_at),
        )
    return _require_provenance_tokens(
        resolved_event_time, resolved_known_at, source, source_native_id, revision
    )


def _require_provenance_tokens(
    event_time: Instant,
    known_at: Instant,
    source: object,
    source_native_id: object,
    revision: object,
) -> Result[tuple[Instant, Instant, str, str, str]]:
    """Resolve source / native-id / revision after the bitemporal instants."""
    clean_source = clean_str(source)
    if clean_source is None:
        return invalid(
            "source",
            "source is required: a non-empty provenance id, orthogonal to VenueId",
            given=repr(source),
        )
    clean_native_id = clean_str(source_native_id)
    if clean_native_id is None:
        return invalid(
            "source_native_id",
            "source-native id is required: the provider's own id for the fact",
            given=repr(source_native_id),
        )
    clean_revision = clean_str(revision)
    if clean_revision is None:
        return invalid(
            "revision",
            "revision is required: the provider's revision of the fact",
            given=repr(revision),
        )
    return Ok((event_time, known_at, clean_source, clean_native_id, clean_revision))


def resolve_observation_writer_block(
    receive_wall_time: object,
    writer: object,
    sequence: object,
    world: object,
) -> Result[tuple[Instant, WriterId, int, World]]:
    """Resolve receive-wall-time, writer, sequence, and world in admission order."""
    resolved_receive = as_instant(receive_wall_time)
    if resolved_receive is None:
        return invalid(
            "receive_wall_time",
            "receive-wall-time is required: a local receive Instant or int64 UTC ns",
            given=repr(receive_wall_time),
        )
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "writer is required: an AD-8 WriterId with its boot/epoch id",
            given=repr(writer),
        )
    resolved_sequence = _require_sequence(sequence)
    if is_refusal(resolved_sequence):
        return resolved_sequence
    resolved_world = coerce_world(world)
    if resolved_world is None:
        return invalid(
            "world",
            "world is required and one of the closed set live | replay | simulated",
            given=repr(world),
        )
    return Ok((resolved_receive, writer, resolved_sequence.value, resolved_world))


def resolve_observation_core(
    event_time: object,
    known_at: object,
    source: object,
    source_native_id: object,
    revision: object,
    receive_wall_time: object,
    writer: object,
    sequence: object,
    world: object,
) -> Result[ObservationCore]:
    """Resolve the required identity parts, or the first ``invalid input`` refusal."""
    required = resolve_observation_required(
        event_time, known_at, source, source_native_id, revision
    )
    if is_refusal(required):
        return required
    writer_block = resolve_observation_writer_block(receive_wall_time, writer, sequence, world)
    if is_refusal(writer_block):
        return writer_block
    event_time_v, known_at_v, source_v, native_id_v, revision_v = required.value
    receive_v, writer_v, sequence_v, world_v = writer_block.value
    return Ok(
        ObservationCore(
            event_time=event_time_v,
            known_at=known_at_v,
            source=source_v,
            source_native_id=native_id_v,
            revision=revision_v,
            receive_wall_time=receive_v,
            writer=writer_v,
            sequence=sequence_v,
            world=world_v,
        )
    )


def resolve_foreign_timestamp(value: object | None) -> Result[ForeignTimestamp | None]:
    """Resolve the optional foreign-timestamp block: ``None``, a value, or a refusal."""
    if value is None:
        return Ok(None)
    if isinstance(value, ForeignTimestamp):
        return Ok(value)
    return invalid(
        "foreign_timestamp",
        "the foreign timestamp is a ForeignTimestamp value (or omitted)",
        given=repr(value),
    )


def resolve_foreign_money(value: object | None) -> Result[ForeignMoney | None]:
    """Resolve the optional foreign-money block: ``None``, a value, or a refusal."""
    if value is None:
        return Ok(None)
    if isinstance(value, ForeignMoney):
        return Ok(value)
    return invalid(
        "foreign_money",
        "foreign money is a ForeignMoney value (or omitted)",
        given=repr(value),
    )


def resolve_market_data(value: object | None) -> Result[MarketDataContext | None]:
    """Resolve the optional self-describing market-data context."""
    if value is None:
        return Ok(None)
    if isinstance(value, MarketDataContext):
        return Ok(value)
    return invalid(
        "market_data",
        "market data is a MarketDataContext value (or omitted)",
        given=repr(value),
    )


def resolve_diagnostic(value: object | None) -> Result[MonotonicReading | None]:
    """Resolve the optional boot-scoped diagnostic: ``None``, a reading, or a refusal."""
    if value is None:
        return Ok(None)
    if isinstance(value, MonotonicReading):
        return Ok(value)
    return invalid(
        "receive_monotonic_diagnostic",
        "the receive-monotonic diagnostic is a MonotonicReading value (or omitted); it "
        "is never an Instant and never rendered as a time",
        given=repr(value),
    )


def resolve_correction_of(value: object | None) -> Result[Fingerprint | None]:
    """Resolve the optional ``correction_of``: ``None``, a fingerprint, or a refusal."""
    if value is None:
        return Ok(None)
    resolved = coerce_fingerprint(value)
    if resolved is None:
        return invalid(
            "correction_of",
            "correction_of is the corrected observation's fp1:sha256:<hex> fingerprint",
            given=repr(value),
        )
    return Ok(resolved)


def resolve_observation_extras(
    foreign_timestamp: object | None,
    foreign_money: object | None,
    market_data: object | None,
    receive_monotonic_diagnostic: object | None,
    correction_of: object | None,
) -> Result[ObservationExtras]:
    """Resolve optional blocks in admission order, or the first refusal."""
    resolved_ts = resolve_foreign_timestamp(foreign_timestamp)
    if is_refusal(resolved_ts):
        return resolved_ts
    resolved_money = resolve_foreign_money(foreign_money)
    if is_refusal(resolved_money):
        return resolved_money
    return _finish_observation_extras(
        resolved_ts.value,
        resolved_money.value,
        market_data,
        receive_monotonic_diagnostic,
        correction_of,
    )


def _finish_observation_extras(
    foreign_timestamp: ForeignTimestamp | None,
    foreign_money: ForeignMoney | None,
    market_data: object | None,
    receive_monotonic_diagnostic: object | None,
    correction_of: object | None,
) -> Result[ObservationExtras]:
    """Resolve market-data, diagnostic, and correction_of after the foreign blocks."""
    resolved_market_data = resolve_market_data(market_data)
    if is_refusal(resolved_market_data):
        return resolved_market_data
    resolved_diagnostic = resolve_diagnostic(receive_monotonic_diagnostic)
    if is_refusal(resolved_diagnostic):
        return resolved_diagnostic
    resolved_correction = resolve_correction_of(correction_of)
    if is_refusal(resolved_correction):
        return resolved_correction
    return Ok(
        ObservationExtras(
            foreign_timestamp=foreign_timestamp,
            foreign_money=foreign_money,
            market_data=resolved_market_data.value,
            receive_monotonic_diagnostic=resolved_diagnostic.value,
            correction_of=resolved_correction.value,
        )
    )


def _fold_optional_identity(
    content: dict[str, object],
    *,
    foreign_timestamp: ForeignTimestamp | None,
    foreign_money: ForeignMoney | None,
    market_data: MarketDataContext | None,
    correction_of: Fingerprint | None,
) -> None:
    """Fold present optional blocks into identity; omit absent keys (never null)."""
    if foreign_timestamp is not None:
        content["foreign_timestamp"] = foreign_timestamp.fp1_identity()
    if foreign_money is not None:
        content["foreign_money"] = foreign_money.fp1_identity()
    if market_data is not None:
        content["market_data"] = market_data.fp1_identity()
    if correction_of is not None:
        content["correction_of"] = correction_of.value


def identity_content(
    *,
    event_time: Instant,
    known_at: Instant,
    source: str,
    source_native_id: str,
    revision: str,
    receive_wall_time: Instant,
    writer: WriterId,
    sequence: int,
    world: World,
    foreign_timestamp: ForeignTimestamp | None,
    foreign_money: ForeignMoney | None,
    market_data: MarketDataContext | None,
    correction_of: Fingerprint | None,
) -> dict[str, object]:
    """The observation's canonical ``fp1`` identity content — the parts that ARE its
    identity.

    Built identically by :meth:`SourceObservation.try_create` (to compute the
    fingerprint) and :meth:`SourceObservation.fp1_identity` (so a read-back
    re-fingerprints to the same value). Every field is identity by default; the
    ``receive_monotonic_diagnostic`` is the one deliberate exclusion (boot-scoped, never
    identity) and the ``fingerprint`` is the identity itself, never folded into its own
    computation. The optional foreign blocks and ``correction_of`` are present only when
    set — an absent value is an omitted key, never a null (fp1; DEC-0108).
    """
    content: dict[str, object] = {
        "class": "source-observation",
        "event_time": event_time.fp1_identity(),
        "known_at": known_at.fp1_identity(),
        "source": source,
        "source_native_id": source_native_id,
        "revision": revision,
        "receive_wall_time": receive_wall_time.fp1_identity(),
        "writer": writer_identity(writer),
        "sequence": sequence,
        "world": world.value,
        "format_version": CONTRACT_FORMAT_VERSION,
    }
    _fold_optional_identity(
        content,
        foreign_timestamp=foreign_timestamp,
        foreign_money=foreign_money,
        market_data=market_data,
        correction_of=correction_of,
    )
    return content
