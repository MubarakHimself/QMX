"""CT-10 — the bitemporal source-observation value types (COMP-QMF-DATA).

The public value vocabulary of the CT-10 boundary: an external fact that lands as
**bitemporal, source-attributed evidence**. Every observation preserves *when it
occurred* (``event_time``) and *when it became knowable* (``known_at``), the read-only
``source`` it came from (a provenance noun ORTHOGONAL to VenueId), the provider's own
``revision``, an AD-8 :class:`~qmf.core.WriterId` with a per-writer strictly-increasing
``sequence``, its ``world``, and its ``fp1`` identity — computed by the single
``qmf-core`` implementation and **nowhere else** (AC1; DEC-0117, DEC-0108).

Three things this module pins down.

**Verbatim foreign evidence, never a silent rewrite (AC2; DEC-0106, DEC-0105).** A
foreign timestamp is kept exactly as received (:class:`ForeignTimestamp`: the verbatim
string plus its declared zone, offset, and source resolution) alongside a
:class:`~qmf.core.Instant` ``receive_wall_time`` in int64 UTC nanoseconds. Foreign money
is kept verbatim as a scaled integer at the SOURCE's declared scale
(:class:`ForeignMoney`). Neither is ever converted or rescaled here: a conversion to
framework Time or Money is a *derived* artifact carrying lineage, produced elsewhere,
never a rewrite of this evidence.

**Corrections append, they never overwrite (AC3; DEC-0117).** A correction is itself a
:class:`SourceObservation` — a distinct artifact with its own ``fp1`` — carrying
``correction_of`` set to the corrected observation's ``fp1``. It refers to the same
provider-native occurrence under a new ``revision``, so its fingerprint differs and it
can never fold inline or masquerade as the original. Read-time resolution of the
annotation is deferred in V1 (DEC-0117).

**Completeness is enforced at construction (AC4/FM-1; DEC-0109).** The frozen dataclass
constructor is the trusted-internal path; :meth:`SourceObservation.try_create` is the
validating factory that returns value-or-refusal. A record lacking event-time, known-at,
source, revision, writer, or a computable ``fp1`` identity is an ``invalid input`` typed
refusal and never enters governed evidence.

The ``receive_monotonic_diagnostic`` is an opaque, boot-scoped diagnostic: never an
Instant, never rendered as a time, **excluded from identity**, and not persisted as
durable evidence (it is meaningless across boots). Every other field is identity by
default (the fp1 recipe's rule), so :meth:`SourceObservation.fp1_identity` folds in all
of them and only them.

Stdlib + qmf-core (fp1 comes only from qmf-core). Frozen, immutable values throughout.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

from qmf.core import (
    Fingerprint,
    Instant,
    MonotonicReading,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    World,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
)

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "ForeignMoney",
    "ForeignTimestamp",
    "SourceObservation",
]

# CT-10 carries its own integer contract format version, stamped into every observation
# artifact; its meaning never mutates — an incompatible change mints the next version
# plus a migration note (DEC-0103; versioning-from-birth L15). This is CT-10's own, not
# CT-05's — each contract owns its format version.
CONTRACT_FORMAT_VERSION: Final[int] = 1


# --- refusal builder --------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a CT-10 value factory returns (FM-1).

    ``retryability`` is ``no`` — a missing bitemporal field, a malformed writer, or a
    foreign amount that is not an integer is a caller mistake, not a transient
    condition — and ``context`` always names the offending ``field`` (CT-04; DEC-0109).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``.

    Provenance tokens (source, source-native id, revision) and the verbatim foreign
    timestamp parts are opaque: the returned token is the caller's string unchanged —
    never stripped, cased, or parsed.
    """
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


# --- verbatim foreign evidence ----------------------------------------------


@dataclass(frozen=True, slots=True)
class ForeignTimestamp:
    """A source timestamp stored exactly as received (CT-10; DEC-0106).

    ``verbatim`` is the source's timestamp string, kept byte-for-byte and never
    reformatted; ``zone`` and ``offset`` are its declared zone and UTC offset as stated
    by the source; ``resolution`` is the source's actual resolution (for example
    ``milliseconds``) stored beside the nanosecond value so a coarser source is never
    presented as finer than it was received. Every part is an opaque string — never
    parsed into a framework time here; a conversion to an :class:`~qmf.core.Instant` is a
    derived value carrying lineage, produced elsewhere.
    """

    verbatim: str
    zone: str
    offset: str
    resolution: str

    @classmethod
    def try_create(
        cls, verbatim: object, zone: object, offset: object, resolution: object
    ) -> Result[ForeignTimestamp]:
        """Validate and build a :class:`ForeignTimestamp`, returning value-or-refusal.

        Each part must be a non-empty string; anything else is an ``invalid input``
        refusal naming the offending field.
        """
        clean_verbatim = _clean_str(verbatim)
        if clean_verbatim is None:
            return _invalid(
                "foreign_timestamp.verbatim",
                "the source timestamp is stored verbatim as a non-empty string",
                given=repr(verbatim),
            )
        clean_zone = _clean_str(zone)
        if clean_zone is None:
            return _invalid(
                "foreign_timestamp.zone",
                "the foreign timestamp carries its declared zone as a non-empty string",
                given=repr(zone),
            )
        clean_offset = _clean_str(offset)
        if clean_offset is None:
            return _invalid(
                "foreign_timestamp.offset",
                "the foreign timestamp carries its declared UTC offset as a non-empty string",
                given=repr(offset),
            )
        clean_resolution = _clean_str(resolution)
        if clean_resolution is None:
            return _invalid(
                "foreign_timestamp.resolution",
                "the foreign timestamp carries the source's actual resolution as a "
                "non-empty string (e.g. milliseconds)",
                given=repr(resolution),
            )
        return Ok(
            cls(
                verbatim=clean_verbatim,
                zone=clean_zone,
                offset=clean_offset,
                resolution=clean_resolution,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — the verbatim parts."""
        return {
            "class": "foreign-timestamp",
            "verbatim": self.verbatim,
            "zone": self.zone,
            "offset": self.offset,
            "resolution": self.resolution,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ForeignMoney:
    """A source money/price amount stored verbatim as a scaled integer (CT-10; DEC-0105).

    ``verbatim`` is the source's raw integer amount, kept exactly; ``scale`` is the
    source's declared number of decimal places for that amount (for example a wire price
    scale, per-symbol digits, or per-account money digits). The pair is never rescaled or
    converted to a framework :class:`~qmf.core.Money`/:class:`~qmf.core.Price` here — a
    conversion is a derived value carrying lineage, never a silent rescale. A binary
    ``float`` is refused: money is an exact integer at a declared scale.
    """

    verbatim: int
    scale: int

    @classmethod
    def try_create(cls, verbatim: object, scale: object) -> Result[ForeignMoney]:
        """Validate and build a :class:`ForeignMoney`, returning value-or-refusal.

        ``verbatim`` must be an integer (a ``bool`` and a ``float`` are refused — money
        never rides a binary float) and ``scale`` a non-negative integer.
        """
        if isinstance(verbatim, bool) or not isinstance(verbatim, int):
            return _invalid(
                "foreign_money.verbatim",
                "foreign money is a verbatim scaled integer, never a binary float (DEC-0105)",
                given=repr(verbatim),
            )
        if isinstance(scale, bool) or not isinstance(scale, int) or scale < 0:
            return _invalid(
                "foreign_money.scale",
                "the source's declared scale is a non-negative integer number of decimal places",
                given=repr(scale),
            )
        return Ok(cls(verbatim=verbatim, scale=scale))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — the raw amount and its scale."""
        return {
            "class": "foreign-money",
            "verbatim": self.verbatim,
            "scale": self.scale,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


# --- coercion helpers -------------------------------------------------------


def _as_instant(value: object) -> Instant | None:
    """Resolve ``value`` to an :class:`~qmf.core.Instant`, or ``None``.

    Accepts an :class:`~qmf.core.Instant` or an int64 UTC-nanosecond count (built through
    ``Instant.try_create`` so the range check is qmf-core's, never restated here).
    """
    if isinstance(value, Instant):
        return value
    built = Instant.try_create(value)
    return built.value if is_ok(built) else None


def _coerce_world(value: object) -> World | None:
    """Resolve ``value`` to a :class:`~qmf.core.World` member, or ``None``."""
    if isinstance(value, World):
        return value
    if isinstance(value, str):
        try:
            return World(value)
        except ValueError:
            return None
    return None


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`~qmf.core.Fingerprint` or a valid ``fp1:sha256:<hex>`` string."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    return parsed.value if is_ok(parsed) else None


def _writer_identity(writer: WriterId) -> dict[str, object]:
    """The writer's identity content — :class:`~qmf.core.WriterId` exposes no
    ``fp1_identity``, so its ``(machine, role, stream, boot_epoch_id)`` parts are folded
    in explicitly and consistently."""
    return {
        "machine": writer.machine,
        "role": writer.role,
        "stream": writer.stream,
        "boot_epoch_id": writer.boot_epoch_id,
    }


def _identity_content(
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
        "writer": _writer_identity(writer),
        "sequence": sequence,
        "world": world.value,
        "format_version": CONTRACT_FORMAT_VERSION,
    }
    if foreign_timestamp is not None:
        content["foreign_timestamp"] = foreign_timestamp.fp1_identity()
    if foreign_money is not None:
        content["foreign_money"] = foreign_money.fp1_identity()
    if correction_of is not None:
        content["correction_of"] = correction_of.value
    return content


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
        resolved_event_time = _as_instant(event_time)
        if resolved_event_time is None:
            return _invalid(
                "event_time",
                "event-time is required: an Instant or int64 UTC-nanosecond count "
                "(when the fact occurred)",
                given=repr(event_time),
            )
        resolved_known_at = _as_instant(known_at)
        if resolved_known_at is None:
            return _invalid(
                "known_at",
                "known-at is required: an Instant or int64 UTC-nanosecond count "
                "(when the fact became knowable)",
                given=repr(known_at),
            )
        clean_source = _clean_str(source)
        if clean_source is None:
            return _invalid(
                "source",
                "source is required: a non-empty provenance id, orthogonal to VenueId",
                given=repr(source),
            )
        clean_native_id = _clean_str(source_native_id)
        if clean_native_id is None:
            return _invalid(
                "source_native_id",
                "source-native id is required: the provider's own id for the fact",
                given=repr(source_native_id),
            )
        clean_revision = _clean_str(revision)
        if clean_revision is None:
            return _invalid(
                "revision",
                "revision is required: the provider's revision of the fact",
                given=repr(revision),
            )
        resolved_receive = _as_instant(receive_wall_time)
        if resolved_receive is None:
            return _invalid(
                "receive_wall_time",
                "receive-wall-time is required: a local receive Instant or int64 UTC ns",
                given=repr(receive_wall_time),
            )
        if not isinstance(writer, WriterId):
            return _invalid(
                "writer",
                "writer is required: an AD-8 WriterId with its boot/epoch id",
                given=repr(writer),
            )
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            return _invalid(
                "sequence",
                "sequence is required: a per-writer non-negative strictly-increasing integer",
                given=repr(sequence),
            )
        resolved_world = _coerce_world(world)
        if resolved_world is None:
            return _invalid(
                "world",
                "world is required and one of the closed set live | replay | simulated",
                given=repr(world),
            )
        resolved_ts = _resolve_foreign_timestamp(foreign_timestamp)
        if is_refusal(resolved_ts):
            return resolved_ts
        resolved_money = _resolve_foreign_money(foreign_money)
        if is_refusal(resolved_money):
            return resolved_money
        resolved_diagnostic = _resolve_diagnostic(receive_monotonic_diagnostic)
        if is_refusal(resolved_diagnostic):
            return resolved_diagnostic
        resolved_correction = _resolve_correction_of(correction_of)
        if is_refusal(resolved_correction):
            return resolved_correction

        content = _identity_content(
            event_time=resolved_event_time,
            known_at=resolved_known_at,
            source=clean_source,
            source_native_id=clean_native_id,
            revision=clean_revision,
            receive_wall_time=resolved_receive,
            writer=writer,
            sequence=sequence,
            world=resolved_world,
            foreign_timestamp=resolved_ts.value,
            foreign_money=resolved_money.value,
            correction_of=resolved_correction.value,
        )
        fp = fingerprint(content)
        if is_refusal(fp):  # pragma: no cover - content is canonical by construction
            return fp
        return Ok(
            cls(
                event_time=resolved_event_time,
                known_at=resolved_known_at,
                source=clean_source,
                source_native_id=clean_native_id,
                revision=clean_revision,
                receive_wall_time=resolved_receive,
                writer=writer,
                sequence=sequence,
                world=resolved_world,
                fingerprint=fp.value,
                foreign_timestamp=resolved_ts.value,
                foreign_money=resolved_money.value,
                receive_monotonic_diagnostic=resolved_diagnostic.value,
                correction_of=resolved_correction.value,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content; its fingerprint equals
        :attr:`fingerprint`. The boot-scoped diagnostic is excluded; every other field is
        folded in (the fp1 identity-by-default rule)."""
        return _identity_content(
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
            "writer": _writer_identity(self.writer),
            "sequence": self.sequence,
            "world": self.world.value,
            "fingerprint": self.fingerprint.value,
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.foreign_timestamp is not None:
            row["foreign_timestamp"] = {
                "verbatim": self.foreign_timestamp.verbatim,
                "zone": self.foreign_timestamp.zone,
                "offset": self.foreign_timestamp.offset,
                "resolution": self.foreign_timestamp.resolution,
            }
        if self.foreign_money is not None:
            row["foreign_money"] = {
                "verbatim": self.foreign_money.verbatim,
                "scale": self.foreign_money.scale,
            }
        if self.correction_of is not None:
            row["correction_of"] = self.correction_of.value
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
        if not isinstance(row, Mapping):
            return _invalid("row", "a persisted observation row is a mapping", given=repr(row))
        mapping = cast("Mapping[str, object]", row)
        stored_fp = _coerce_fingerprint(mapping.get("fingerprint"))
        if stored_fp is None:
            return _invalid(
                "fingerprint",
                "a persisted observation row carries its fp1:sha256:<hex> fingerprint",
                given=repr(mapping.get("fingerprint")),
            )
        foreign_timestamp = _row_foreign_timestamp(mapping.get("foreign_timestamp"))
        if is_refusal(foreign_timestamp):
            return foreign_timestamp
        foreign_money = _row_foreign_money(mapping.get("foreign_money"))
        if is_refusal(foreign_money):
            return foreign_money
        built = cls.try_create(
            event_time=mapping.get("event_time_ns"),
            known_at=mapping.get("known_at_ns"),
            source=mapping.get("source"),
            source_native_id=mapping.get("source_native_id"),
            revision=mapping.get("revision"),
            receive_wall_time=mapping.get("receive_wall_time_ns"),
            writer=_row_writer(mapping.get("writer")),
            sequence=mapping.get("sequence"),
            world=mapping.get("world"),
            foreign_timestamp=foreign_timestamp.value,
            foreign_money=foreign_money.value,
            correction_of=mapping.get("correction_of"),
        )
        if is_refusal(built):
            return built
        if built.value.fingerprint.value != stored_fp.value:
            return _invalid(
                "fingerprint",
                "the stored row does not re-fingerprint to its recorded fp1; the evidence "
                "is corrupt or tampered and is refused rather than read back as valid",
                stored=stored_fp.value,
                recomputed=built.value.fingerprint.value,
            )
        return built


# --- optional-part resolvers (used by try_create) ---------------------------


def _resolve_foreign_timestamp(value: object | None) -> Result[ForeignTimestamp | None]:
    """Resolve the optional foreign-timestamp block: ``None``, a value, or a refusal."""
    if value is None:
        return Ok(None)
    if isinstance(value, ForeignTimestamp):
        return Ok(value)
    return _invalid(
        "foreign_timestamp",
        "the foreign timestamp is a ForeignTimestamp value (or omitted)",
        given=repr(value),
    )


def _resolve_foreign_money(value: object | None) -> Result[ForeignMoney | None]:
    """Resolve the optional foreign-money block: ``None``, a value, or a refusal."""
    if value is None:
        return Ok(None)
    if isinstance(value, ForeignMoney):
        return Ok(value)
    return _invalid(
        "foreign_money",
        "foreign money is a ForeignMoney value (or omitted)",
        given=repr(value),
    )


def _resolve_diagnostic(value: object | None) -> Result[MonotonicReading | None]:
    """Resolve the optional boot-scoped diagnostic: ``None``, a reading, or a refusal."""
    if value is None:
        return Ok(None)
    if isinstance(value, MonotonicReading):
        return Ok(value)
    return _invalid(
        "receive_monotonic_diagnostic",
        "the receive-monotonic diagnostic is a MonotonicReading value (or omitted); it "
        "is never an Instant and never rendered as a time",
        given=repr(value),
    )


def _resolve_correction_of(value: object | None) -> Result[Fingerprint | None]:
    """Resolve the optional ``correction_of``: ``None``, a fingerprint, or a refusal."""
    if value is None:
        return Ok(None)
    resolved = _coerce_fingerprint(value)
    if resolved is None:
        return _invalid(
            "correction_of",
            "correction_of is the corrected observation's fp1:sha256:<hex> fingerprint",
            given=repr(value),
        )
    return Ok(resolved)


# --- row-reconstruction helpers (used by from_row) --------------------------


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
        return _invalid(
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
        return _invalid(
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
