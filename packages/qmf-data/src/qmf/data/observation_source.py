"""CT-10 SourceObservation value — bitemporal, source-attributed evidence.

Split from :mod:`qmf.data.observation` so the public module stays under the
Skylos god-file limits. Callers keep importing :class:`SourceObservation` from
:mod:`qmf.data.observation`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict, cast

from qmf.core import (
    Fingerprint,
    Instant,
    MonotonicReading,
    Ok,
    Result,
    World,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.data.observation_build import (
    ObservationCore,
    ObservationExtras,
    identity_content,
    resolve_observation_core,
    resolve_observation_extras,
)
from qmf.data.observation_types import (
    CONTRACT_FORMAT_VERSION,
    ForeignMoney,
    ForeignTimestamp,
    MarketDataContext,
    coerce_fingerprint,
    invalid,
    writer_identity,
)

__all__ = ["SourceObservation"]


@dataclass(frozen=True, slots=True)
class SourceObservation:
    """A bitemporal, source-attributed external fact (CT-10; DEC-0117, DEC-0108).

    Its ``fingerprint`` is its identity, computed by the single ``qmf-core``
    implementation over :meth:`fp1_identity`. ``(receive_wall_time, writer, sequence)``
    orders a replay stream and carries no causal meaning; identity is the fingerprint,
    and a timestamp is never a primary or dedup key. A correction sets ``correction_of``
    to the corrected observation's fingerprint and is a distinct artifact, never an
    in-place edit.

    The frozen constructor is the trusted-internal path; :meth:`try_create` is the
    validating factory. Reconstruct a persisted row with :meth:`from_row`, which
    re-verifies the fingerprint so a tampered or corrupt row never reads back as valid.
    """

    event_time: Instant
    known_at: Instant
    source: str
    source_native_id: str
    revision: str
    receive_wall_time: Instant
    writer: WriterId
    sequence: int
    world: World
    fingerprint: Fingerprint
    foreign_timestamp: ForeignTimestamp | None = None
    foreign_money: ForeignMoney | None = None
    market_data: MarketDataContext | None = None
    receive_monotonic_diagnostic: MonotonicReading | None = None
    correction_of: Fingerprint | None = None

    @property
    def is_correction(self) -> bool:
        """Whether this observation is a correction of an earlier one (``correction_of``
        is set)."""
        return self.correction_of is not None

    @classmethod
    def try_create(
        cls,
        *,
        event_time: object,
        known_at: object,
        source: object,
        source_native_id: object,
        revision: object,
        receive_wall_time: object,
        writer: object,
        sequence: object,
        world: object,
        foreign_timestamp: object | None = None,
        foreign_money: object | None = None,
        market_data: object | None = None,
        receive_monotonic_diagnostic: object | None = None,
        correction_of: object | None = None,
    ) -> Result[SourceObservation]:
        """Validate the parts, compute the ``fp1`` identity, and build the observation.

        A record lacking event-time, known-at, source, source-native id, revision,
        receive-wall-time, writer, sequence, world, or a *computable* ``fp1`` identity is
        an ``invalid input`` refusal and never enters governed evidence (AC4/FM-1). The
        times accept an :class:`~qmf.core.Instant` or an int64 UTC-nanosecond count; the
        writer is an :class:`~qmf.core.WriterId`; the world is a :class:`~qmf.core.World`
        (or its string); ``correction_of`` is a :class:`~qmf.core.Fingerprint` (or an
        ``fp1:sha256:<hex>`` string). The fingerprint is **not** supplied — it is computed
        by ``qmf-core`` over the identity content, so identity is minted nowhere else.
        """
        return _admit_source_observation(
            cls,
            event_time,
            known_at,
            source,
            source_native_id,
            revision,
            receive_wall_time,
            writer,
            sequence,
            world,
            foreign_timestamp,
            foreign_money,
            market_data,
            receive_monotonic_diagnostic,
            correction_of,
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content; its fingerprint equals
        :attr:`fingerprint`. The boot-scoped diagnostic is excluded; every other field is
        folded in (the fp1 identity-by-default rule)."""
        return identity_content(
            event_time=self.event_time,
            known_at=self.known_at,
            source=self.source,
            source_native_id=self.source_native_id,
            revision=self.revision,
            receive_wall_time=self.receive_wall_time,
            writer=self.writer,
            sequence=self.sequence,
            world=self.world,
            foreign_timestamp=self.foreign_timestamp,
            foreign_money=self.foreign_money,
            market_data=self.market_data,
            correction_of=self.correction_of,
        )

    def to_row(self) -> dict[str, object]:
        """A flat, JSON-native serialization for the immutable raw archive.

        Carries every durable field plus the observation's own ``fingerprint`` (so a
        governed reader has the evidence identity without recomputing) and
        ``correction_of`` when present. The boot-scoped ``receive_monotonic_diagnostic``
        is deliberately not persisted — it is meaningless across boots — so two
        submissions that differ only in that diagnostic are byte-identical evidence and
        deduplicate. All values are ``int`` / ``str`` / nested ``dict``, so the row
        canonicalizes and round-trips exactly (H5).
        """
        row: dict[str, object] = {
            "event_time_ns": self.event_time.value_ns,
            "known_at_ns": self.known_at.value_ns,
            "source": self.source,
            "source_native_id": self.source_native_id,
            "revision": self.revision,
            "receive_wall_time_ns": self.receive_wall_time.value_ns,
            "writer": writer_identity(self.writer),
            "sequence": self.sequence,
            "world": self.world.value,
            "fingerprint": self.fingerprint.value,
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        _attach_optional_row_blocks(self, row)
        return row

    @classmethod
    def from_row(cls, row: object) -> Result[SourceObservation]:
        """Reconstruct an observation from a persisted :meth:`to_row` row, verifying its
        ``fp1``.

        Rebuilds the value through :meth:`try_create` (so a malformed row is an
        ``invalid input`` refusal exactly as at admission) and then checks the recomputed
        fingerprint equals the row's stored ``fingerprint`` — a mismatch means the stored
        evidence was corrupted or tampered and is refused, never returned as valid
        (H5, DEC-0108). The boot-scoped diagnostic is not persisted, so it reads back
        absent.
        """
        parsed = _parse_observation_row(row)
        if is_refusal(parsed):
            return parsed
        stored_fp, kwargs = parsed.value
        built = cls.try_create(**kwargs)
        if is_refusal(built):
            return built
        if built.value.fingerprint.value != stored_fp.value:
            return invalid(
                "fingerprint",
                "the stored row does not re-fingerprint to its recorded fp1; the evidence "
                "is corrupt or tampered and is refused rather than read back as valid",
                stored=stored_fp.value,
                recomputed=built.value.fingerprint.value,
            )
        return built


def _admit_source_observation(
    cls: type[SourceObservation],
    event_time: object,
    known_at: object,
    source: object,
    source_native_id: object,
    revision: object,
    receive_wall_time: object,
    writer: object,
    sequence: object,
    world: object,
    foreign_timestamp: object | None,
    foreign_money: object | None,
    market_data: object | None,
    receive_monotonic_diagnostic: object | None,
    correction_of: object | None,
) -> Result[SourceObservation]:
    """Resolve required and optional parts, then mint the observation."""
    core = resolve_observation_core(
        event_time,
        known_at,
        source,
        source_native_id,
        revision,
        receive_wall_time,
        writer,
        sequence,
        world,
    )
    if is_refusal(core):
        return core
    extras = resolve_observation_extras(
        foreign_timestamp,
        foreign_money,
        market_data,
        receive_monotonic_diagnostic,
        correction_of,
    )
    if is_refusal(extras):
        return extras
    return _mint_source_observation(cls, core.value, extras.value)


class _ObservationCreateArgs(TypedDict):
    """Keyword arguments :meth:`SourceObservation.try_create` accepts from a row."""

    event_time: object
    known_at: object
    source: object
    source_native_id: object
    revision: object
    receive_wall_time: object
    writer: object
    sequence: object
    world: object
    foreign_timestamp: object | None
    foreign_money: object | None
    market_data: object | None
    correction_of: object | None


def _mint_source_observation(
    cls: type[SourceObservation],
    core: ObservationCore,
    extras: ObservationExtras,
) -> Result[SourceObservation]:
    """Fingerprint identity content and construct the frozen observation."""
    content = identity_content(
        event_time=core.event_time,
        known_at=core.known_at,
        source=core.source,
        source_native_id=core.source_native_id,
        revision=core.revision,
        receive_wall_time=core.receive_wall_time,
        writer=core.writer,
        sequence=core.sequence,
        world=core.world,
        foreign_timestamp=extras.foreign_timestamp,
        foreign_money=extras.foreign_money,
        market_data=extras.market_data,
        correction_of=extras.correction_of,
    )
    fp = fingerprint(content)
    if is_refusal(fp):  # pragma: no cover - content is canonical by construction
        return fp
    return Ok(_construct_source_observation(cls, core, extras, fp.value))


def _construct_source_observation(
    cls: type[SourceObservation],
    core: ObservationCore,
    extras: ObservationExtras,
    fingerprint_value: Fingerprint,
) -> SourceObservation:
    """Trusted-internal construct after identity has been minted."""
    return cls(
        event_time=core.event_time,
        known_at=core.known_at,
        source=core.source,
        source_native_id=core.source_native_id,
        revision=core.revision,
        receive_wall_time=core.receive_wall_time,
        writer=core.writer,
        sequence=core.sequence,
        world=core.world,
        fingerprint=fingerprint_value,
        foreign_timestamp=extras.foreign_timestamp,
        foreign_money=extras.foreign_money,
        market_data=extras.market_data,
        receive_monotonic_diagnostic=extras.receive_monotonic_diagnostic,
        correction_of=extras.correction_of,
    )


def _attach_optional_row_blocks(observation: SourceObservation, row: dict[str, object]) -> None:
    """Attach present optional blocks to a ``to_row`` mapping; omit absent keys."""
    if observation.foreign_timestamp is not None:
        row["foreign_timestamp"] = {
            "verbatim": observation.foreign_timestamp.verbatim,
            "zone": observation.foreign_timestamp.zone,
            "offset": observation.foreign_timestamp.offset,
            "resolution": observation.foreign_timestamp.resolution,
        }
    if observation.foreign_money is not None:
        row["foreign_money"] = {
            "verbatim": observation.foreign_money.verbatim,
            "scale": observation.foreign_money.scale,
        }
    if observation.market_data is not None:
        row["market_data"] = observation.market_data.to_row()
    if observation.correction_of is not None:
        row["correction_of"] = observation.correction_of.value


def _parse_observation_row(
    row: object,
) -> Result[tuple[Fingerprint, _ObservationCreateArgs]]:
    """Pull stored fingerprint and try_create kwargs from a persisted mapping."""
    stored = _row_stored_fingerprint(row)
    if is_refusal(stored):
        return stored
    mapping, stored_fp = stored.value
    optionals = _row_optional_values(mapping)
    if is_refusal(optionals):
        return optionals
    return Ok((stored_fp, _observation_create_kwargs(mapping, optionals.value)))


def _row_stored_fingerprint(
    row: object,
) -> Result[tuple[Mapping[str, object], Fingerprint]]:
    """Require a mapping row that carries a parseable ``fp1`` fingerprint."""
    if not isinstance(row, Mapping):
        return invalid("row", "a persisted observation row is a mapping", given=repr(row))
    mapping = cast("Mapping[str, object]", row)
    stored_fp = coerce_fingerprint(mapping.get("fingerprint"))
    if stored_fp is None:
        return invalid(
            "fingerprint",
            "a persisted observation row carries its fp1:sha256:<hex> fingerprint",
            given=repr(mapping.get("fingerprint")),
        )
    return Ok((mapping, stored_fp))


def _row_optional_values(
    mapping: Mapping[str, object],
) -> Result[tuple[ForeignTimestamp | None, ForeignMoney | None, MarketDataContext | None]]:
    """Rebuild optional foreign/market blocks from persisted sub-mappings."""
    foreign_timestamp = _row_foreign_timestamp(mapping.get("foreign_timestamp"))
    if is_refusal(foreign_timestamp):
        return foreign_timestamp
    foreign_money = _row_foreign_money(mapping.get("foreign_money"))
    if is_refusal(foreign_money):
        return foreign_money
    market_data = _row_market_data(mapping.get("market_data"))
    if is_refusal(market_data):
        return market_data
    return Ok((foreign_timestamp.value, foreign_money.value, market_data.value))


def _observation_create_kwargs(
    mapping: Mapping[str, object],
    optionals: tuple[ForeignTimestamp | None, ForeignMoney | None, MarketDataContext | None],
) -> _ObservationCreateArgs:
    """Keyword arguments :meth:`SourceObservation.try_create` accepts from a row."""
    foreign_timestamp, foreign_money, market_data = optionals
    return {
        "event_time": mapping.get("event_time_ns"),
        "known_at": mapping.get("known_at_ns"),
        "source": mapping.get("source"),
        "source_native_id": mapping.get("source_native_id"),
        "revision": mapping.get("revision"),
        "receive_wall_time": mapping.get("receive_wall_time_ns"),
        "writer": _row_writer(mapping.get("writer")),
        "sequence": mapping.get("sequence"),
        "world": mapping.get("world"),
        "foreign_timestamp": foreign_timestamp,
        "foreign_money": foreign_money,
        "market_data": market_data,
        "correction_of": mapping.get("correction_of"),
    }


def _row_writer(value: object) -> object:
    """Rebuild a :class:`~qmf.core.WriterId` from a persisted ``writer`` sub-mapping.

    Returns the built ``WriterId`` on success, or the offending value unchanged so
    :meth:`SourceObservation.try_create` surfaces the ``invalid input`` refusal in one
    place (this helper never invents a refusal of its own).
    """
    if not isinstance(value, Mapping):
        return value
    block = cast("Mapping[str, object]", value)
    built = WriterId.try_create(
        block.get("machine"),
        block.get("role"),
        block.get("stream"),
        block.get("boot_epoch_id"),
    )
    # On failure return the mapping unchanged so try_create surfaces the one refusal.
    return built.value if is_ok(built) else block


def _row_foreign_timestamp(value: object) -> Result[ForeignTimestamp | None]:
    """Rebuild the optional foreign-timestamp block from a persisted sub-mapping."""
    if value is None:
        return Ok(None)
    if not isinstance(value, Mapping):
        return invalid(
            "foreign_timestamp",
            "a persisted foreign timestamp is a mapping",
            given=repr(value),
        )
    block = cast("Mapping[str, object]", value)
    built = ForeignTimestamp.try_create(
        block.get("verbatim"),
        block.get("zone"),
        block.get("offset"),
        block.get("resolution"),
    )
    if is_refusal(built):
        return built
    resolved: ForeignTimestamp | None = built.value
    return Ok(resolved)


def _row_foreign_money(value: object) -> Result[ForeignMoney | None]:
    """Rebuild the optional foreign-money block from a persisted sub-mapping."""
    if value is None:
        return Ok(None)
    if not isinstance(value, Mapping):
        return invalid(
            "foreign_money",
            "a persisted foreign money block is a mapping",
            given=repr(value),
        )
    block = cast("Mapping[str, object]", value)
    built = ForeignMoney.try_create(block.get("verbatim"), block.get("scale"))
    if is_refusal(built):
        return built
    resolved: ForeignMoney | None = built.value
    return Ok(resolved)


def _row_market_data(value: object) -> Result[MarketDataContext | None]:
    """Rebuild the optional market-data context from a persisted sub-mapping."""
    if value is None:
        return Ok(None)
    built = MarketDataContext.from_row(value)
    if is_refusal(built):
        return built
    resolved: MarketDataContext | None = built.value
    return Ok(resolved)
