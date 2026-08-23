"""CT-16 — the bulk series vocabulary: presence map, input series, and output series
(COMP-QMF-INDICATORS; Story 7.3).

A CT-16 series travels in the **pinned bulk form**: a read-only ``memoryview`` over
immutable little-endian ``int64`` bytes, with per-channel out-of-band scale, and a
**parallel integer-encoded presence map** in which every position carries a
``registry:presence_map_states`` value — ``present | provisional | not_ready | gap |
absent_by_schedule``. Positions are never omitted or shifted; a value's absence is a
presence-map state, **never** a missing slot, **never** a NaN, **never** a sentinel
(DEC-0126).

This module lands two value types over that form (Story 7.3):

* :class:`InputSeries` — one input channel's bulk column (values + scale + presence map
  + per-position knowable-at). It is the aggregated-bar column the application supplies
  (CT-10 source observations aggregated to a declared ``BarSpec`` by ``qmf-data``); the
  indicator receives it as data and never derives bar boundaries itself.
* :class:`IndicatorSeries` — one output channel of a batch result: full-length,
  index-aligned to the input, presence-mapped, with every position carrying a
  knowable-at instant. Its :meth:`IndicatorSeries.equals` compares presence maps first
  and values only at present positions — the CT-16 equality rule (DEC-0126).

The series vocabulary nouns ``Bar``, ``Tick``/``Quote`` and ``BarSpec`` remain
``qmf-core`` nouns referenced only by identity (Story 7.1); this module owns the CT-16
**result/input bulk form and its presence map**, part of the contract ``qmf-indicators``
owns. ``PresenceState`` mirrors ``registry:presence_map_states`` verbatim — the value is
never restated, only named (DEC-0126).

Default-deny holds: this module imports **only** ``qmf.core`` (fingerprints are computed
there, nowhere else). Public value types are frozen dataclasses; every validating factory
succeeds or RETURNS a CT-04 typed refusal (DEC-0101, DEC-0109, DEC-0120).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Final, cast

from qmf.core import (
    Fingerprint,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    fingerprint,
)

__all__ = [
    "BYTES_PER_VALUE",
    "MAX_SCALE",
    "PRESENCE_CODES",
    "IndicatorSeries",
    "InputSeries",
    "PresenceState",
    "presence_code",
    "presence_from_code",
]

# The CT-16 bulk-series contract format version stamped into every serialized series
# identity, distinct from a configuration's per-configured-indicator format version
# (DEC-0103; versioning-from-birth L15).
CONTRACT_FORMAT_VERSION: Final[int] = 1

# One value occupies exactly eight bytes: the bulk form is little-endian signed int64
# (DEC-0126). Checksums and serialization are defined over exactly this byte layout.
BYTES_PER_VALUE: Final[int] = 8

# The signed int64 range every bulk value occupies; a value outside it cannot be
# encoded and is refused rather than wrapped.
_INT64_MIN: Final[int] = -(2**63)
_INT64_MAX: Final[int] = 2**63 - 1

# The documented maximum out-of-band scale (count of decimal places) a channel
# declares, mirroring qmf-core's exact-value cap so ``10**scale`` stays a cheap integer
# and a caller-supplied scale can never force a million-digit power of ten.
MAX_SCALE: Final[int] = 72


class PresenceState(StrEnum):
    """A per-position presence state — ``registry:presence_map_states`` (DEC-0126).

    Named here verbatim from the registry, never restated: every position of a bulk
    series carries one of these in the parallel integer-encoded presence map, and NaN
    and sentinel markers are prohibited.

    * ``present`` — a value is present at this position.
    * ``provisional`` — an in-progress value that never enters governed evidence.
    * ``not_ready`` — the configuration's warm-up is not yet complete here; the output
      is a marked not-ready value, never a number.
    * ``gap`` — a calendar-open position with no data, marked under the declared
      missing-value policy (never silent filling).
    * ``absent_by_schedule`` — the market-hours calendar says closed here; never a gap.
    """

    PRESENT = "present"
    PROVISIONAL = "provisional"
    NOT_READY = "not_ready"
    GAP = "gap"
    ABSENT_BY_SCHEDULE = "absent_by_schedule"


class _PresenceCode(IntEnum):
    """The pinned integer encoding of each presence state for the parallel map.

    The presence map is integer-encoded (DEC-0126); these ordinals are the encoding,
    assigned in the registry's declared order and stable from birth (a reordering would
    mint a new format version).
    """

    PRESENT = 0
    PROVISIONAL = 1
    NOT_READY = 2
    GAP = 3
    ABSENT_BY_SCHEDULE = 4


# The presence state <-> integer-code correspondence (DEC-0126). One direction each,
# derived from the pinned ordinals so the two can never drift apart.
PRESENCE_CODES: Final[Mapping[PresenceState, int]] = {
    PresenceState.PRESENT: _PresenceCode.PRESENT.value,
    PresenceState.PROVISIONAL: _PresenceCode.PROVISIONAL.value,
    PresenceState.NOT_READY: _PresenceCode.NOT_READY.value,
    PresenceState.GAP: _PresenceCode.GAP.value,
    PresenceState.ABSENT_BY_SCHEDULE: _PresenceCode.ABSENT_BY_SCHEDULE.value,
}
_CODE_TO_PRESENCE: Final[Mapping[int, PresenceState]] = {
    code: state for state, code in PRESENCE_CODES.items()
}


def presence_code(state: PresenceState) -> int:
    """The integer code of a presence state in the parallel integer-encoded map."""
    return PRESENCE_CODES[state]


def presence_from_code(code: object) -> PresenceState | None:
    """The presence state a map code decodes to, or ``None`` for an unknown code."""
    if isinstance(code, bool) or not isinstance(code, int):
        return None
    return _CODE_TO_PRESENCE.get(code)


# --- refusal + validation helpers -------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a bulk-series factory returns (CT-04)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _coerce_scale(value: object) -> int | None:
    """Return ``value`` as an integer scale in ``[0, MAX_SCALE]``, else ``None``."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < 0 or value > MAX_SCALE:
        return None
    return value


def _coerce_values(value: object) -> bytes | None:
    """Snapshot the bulk value bytes into immutable ``bytes``, else ``None``.

    The bulk form is a read-only ``memoryview`` over immutable little-endian ``int64``
    bytes; a ``memoryview`` or ``bytearray`` is snapshotted to ``bytes`` so the frozen
    series can never be mutated through the caller's buffer, and its length must be a
    whole number of eight-byte values.
    """
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, bytearray):
        raw = bytes(value)
    elif isinstance(value, memoryview):
        raw = value.tobytes()
    else:
        return None
    if len(raw) % BYTES_PER_VALUE != 0:
        return None
    return raw


def _coerce_presence(value: object) -> tuple[PresenceState, ...] | None:
    """Resolve a sequence of presence states (members or their string values)."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return None
    resolved: list[PresenceState] = []
    for item in cast("Sequence[object]", value):
        if isinstance(item, PresenceState):
            resolved.append(item)
        elif isinstance(item, str):
            try:
                resolved.append(PresenceState(item))
            except ValueError:
                return None
        else:
            return None
    return tuple(resolved)


def _coerce_instants(value: object) -> tuple[Instant, ...] | None:
    """Resolve a sequence of knowable-at :class:`~qmf.core.Instant`\\ s."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return None
    resolved: list[Instant] = []
    for item in cast("Sequence[object]", value):
        if not isinstance(item, Instant):
            return None
        resolved.append(item)
    return tuple(resolved)


def _decode_int64(raw: bytes, index: int) -> int:
    """Decode the little-endian signed int64 at ``index`` in the bulk byte layout."""
    start = index * BYTES_PER_VALUE
    return int.from_bytes(raw[start : start + BYTES_PER_VALUE], "little", signed=True)


def encode_int64_values(scaled_ints: Sequence[object]) -> Result[bytes]:
    """Encode scaled integers into the pinned little-endian int64 bulk byte layout.

    Each item must be a genuine integer (a ``bool`` is refused); a value outside the
    signed int64 range is refused rather than wrapped, so the bulk form never silently
    truncates a magnitude (DEC-0126).
    """
    out = bytearray()
    for index, item in enumerate(scaled_ints):
        if isinstance(item, bool) or not isinstance(item, int):
            return _invalid(
                "values", "each bulk value is an integer", index=index, given=repr(item)
            )
        if item < _INT64_MIN or item > _INT64_MAX:
            return _invalid(
                "values",
                "a bulk value is outside the signed int64 range; refused, never wrapped",
                index=index,
                given=item,
            )
        out.extend(item.to_bytes(BYTES_PER_VALUE, "little", signed=True))
    return Ok(bytes(out))


def _validate_parallel(
    values: bytes,
    presence: tuple[PresenceState, ...],
    knowable_at: tuple[Instant, ...],
) -> TypedRefusal | None:
    """Refuse unless the value bytes, presence map, and knowable-at run parallel.

    Positions are never omitted or shifted, so the three parallel arrays must have one
    entry per position: ``len(values) / 8 == len(presence) == len(knowable_at)``.
    """
    count = len(values) // BYTES_PER_VALUE
    if len(presence) != count:
        return _invalid(
            "presence",
            "the presence map runs parallel to the values; one state per position",
            values=count,
            presence=len(presence),
        )
    if len(knowable_at) != count:
        return _invalid(
            "knowable_at",
            "knowable-at runs parallel to the values; one instant per position",
            values=count,
            knowable_at=len(knowable_at),
        )
    return None


def _series_identity(
    kind: str,
    values: bytes,
    scale: int,
    presence: tuple[PresenceState, ...],
    knowable_at: tuple[Instant, ...],
) -> dict[str, object]:
    """The shared canonical ``fp1`` identity content for a bulk series (DEC-0108).

    The exact byte layout is referenced by its ``sha256`` digest (the CT-16 checksum
    over that layout), alongside the out-of-band scale, the integer-encoded presence
    map, and the per-position knowable-at nanoseconds — every part identity-bearing.
    """
    return {
        "class": kind,
        "scale": scale,
        "values_digest": hashlib.sha256(values).hexdigest(),
        "value_count": len(values) // BYTES_PER_VALUE,
        "presence": [presence_code(state) for state in presence],
        "knowable_at_ns": [instant.value_ns for instant in knowable_at],
        "format_version": CONTRACT_FORMAT_VERSION,
    }


# --- input series -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InputSeries:
    """One input channel's bulk column in the pinned form (CT-16; DEC-0126).

    Immutable little-endian ``int64`` ``values`` at an out-of-band ``scale``, a parallel
    ``presence`` map, and a parallel ``knowable_at`` run — the aggregated-bar column the
    application supplies (CT-10 observations aggregated to a declared ``BarSpec`` by
    ``qmf-data``). The indicator consumes it as data and never derives bar boundaries.
    The frozen constructor is the trusted-internal path; :meth:`try_create` and
    :meth:`from_values` are the validating factories.
    """

    values: bytes
    scale: int
    presence: tuple[PresenceState, ...]
    knowable_at: tuple[Instant, ...]

    @property
    def length(self) -> int:
        """The number of positions in the series."""
        return len(self.values) // BYTES_PER_VALUE

    @property
    def buffer(self) -> memoryview:
        """A read-only ``memoryview`` over the immutable int64 byte layout."""
        return memoryview(self.values)

    def value_at(self, index: int) -> int:
        """The scaled integer at ``index`` (decoded from the little-endian layout)."""
        if index < 0 or index >= self.length:
            raise IndexError(f"position {index} is out of range for a series of {self.length}")
        return _decode_int64(self.values, index)

    def presence_at(self, index: int) -> PresenceState:
        """The presence state at ``index``."""
        return self.presence[index]

    @classmethod
    def try_create(
        cls, values: object, scale: object, presence: object, knowable_at: object
    ) -> Result[InputSeries]:
        """Validate and build an :class:`InputSeries` from the pinned bulk form.

        ``values`` is the immutable little-endian int64 bytes (a whole number of
        eight-byte values); ``scale`` an integer in ``[0, MAX_SCALE]``; ``presence`` a
        parallel run of presence states; ``knowable_at`` a parallel run of instants.
        """
        raw = _coerce_values(values)
        if raw is None:
            return _invalid(
                "values",
                "values are immutable little-endian int64 bytes, a whole number of "
                "eight-byte values",
                given=repr(type(values).__name__),
            )
        int_scale = _coerce_scale(scale)
        if int_scale is None:
            return _invalid(
                "scale",
                f"scale is an integer count of decimal places in [0, {MAX_SCALE}]",
                given=repr(scale),
            )
        states = _coerce_presence(presence)
        if states is None:
            return _invalid(
                "presence",
                "the presence map is a sequence of registry:presence_map_states values",
                given=repr(presence),
            )
        instants = _coerce_instants(knowable_at)
        if instants is None:
            return _invalid(
                "knowable_at",
                "knowable-at is a sequence of Instants, one per position",
                given=repr(knowable_at),
            )
        mismatch = _validate_parallel(raw, states, instants)
        if mismatch is not None:
            return mismatch
        return Ok(cls(values=raw, scale=int_scale, presence=states, knowable_at=instants))

    @classmethod
    def from_values(
        cls, scaled_ints: object, scale: object, presence: object, knowable_at: object
    ) -> Result[InputSeries]:
        """Build an :class:`InputSeries` from scaled integers, encoding the bulk bytes.

        A convenience over :meth:`try_create`: it encodes ``scaled_ints`` into the
        pinned little-endian int64 layout (refusing an out-of-range magnitude) and then
        validates the whole series.
        """
        if isinstance(scaled_ints, (str, bytes)) or not isinstance(scaled_ints, Sequence):
            return _invalid(
                "values", "scaled values are a sequence of integers", given=repr(scaled_ints)
            )
        encoded = encode_int64_values(cast("Sequence[object]", scaled_ints))
        if isinstance(encoded, TypedRefusal):
            return encoded
        return cls.try_create(encoded.value, scale, presence, knowable_at)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this input column."""
        return _series_identity(
            "input-series", self.values, self.scale, self.presence, self.knowable_at
        )

    def fingerprint(self) -> Result[Fingerprint]:
        """The input column's ``fp1`` fingerprint, computed by the single qmf-core seam."""
        return fingerprint(self)


# --- output series ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IndicatorSeries:
    """One output channel of a batch result in the pinned bulk form (CT-16; DEC-0126).

    Full-length and index-aligned to the input (begin-index trimming is prohibited),
    presence-mapped, with every position carrying a knowable-at instant. Immutable
    little-endian ``int64`` ``values`` at an out-of-band ``scale``, a parallel
    ``presence`` map, and a parallel ``knowable_at`` run. :meth:`equals` compares
    presence maps first and values only at present positions.
    """

    values: bytes
    scale: int
    presence: tuple[PresenceState, ...]
    knowable_at: tuple[Instant, ...]

    @property
    def length(self) -> int:
        """The number of positions in the series."""
        return len(self.values) // BYTES_PER_VALUE

    @property
    def buffer(self) -> memoryview:
        """A read-only ``memoryview`` over the immutable int64 byte layout."""
        return memoryview(self.values)

    def value_at(self, index: int) -> int:
        """The scaled integer at ``index`` (decoded from the little-endian layout)."""
        if index < 0 or index >= self.length:
            raise IndexError(f"position {index} is out of range for a series of {self.length}")
        return _decode_int64(self.values, index)

    def presence_at(self, index: int) -> PresenceState:
        """The presence state at ``index``."""
        return self.presence[index]

    @classmethod
    def try_create(
        cls, values: object, scale: object, presence: object, knowable_at: object
    ) -> Result[IndicatorSeries]:
        """Validate and build an :class:`IndicatorSeries` from the pinned bulk form."""
        raw = _coerce_values(values)
        if raw is None:
            return _invalid(
                "values",
                "values are immutable little-endian int64 bytes, a whole number of "
                "eight-byte values",
                given=repr(type(values).__name__),
            )
        int_scale = _coerce_scale(scale)
        if int_scale is None:
            return _invalid(
                "scale",
                f"scale is an integer count of decimal places in [0, {MAX_SCALE}]",
                given=repr(scale),
            )
        states = _coerce_presence(presence)
        if states is None:
            return _invalid(
                "presence",
                "the presence map is a sequence of registry:presence_map_states values",
                given=repr(presence),
            )
        instants = _coerce_instants(knowable_at)
        if instants is None:
            return _invalid(
                "knowable_at",
                "knowable-at is a sequence of Instants, one per position",
                given=repr(knowable_at),
            )
        mismatch = _validate_parallel(raw, states, instants)
        if mismatch is not None:
            return mismatch
        return Ok(cls(values=raw, scale=int_scale, presence=states, knowable_at=instants))

    def equals(self, other: object) -> Result[bool]:
        """Whether two output series are equal — presence maps first, then values.

        The CT-16 equality rule (DEC-0126): the presence maps must match position for
        position, and values are then compared **only at present positions**. Values are
        compared exactly across scales (``a * 10**b_scale == b * 10**a_scale``), so a
        value stored at two scales never forks equality. A ``not_ready`` / ``gap`` /
        ``absent_by_schedule`` position carries no number, so no value is read there.
        """
        if not isinstance(other, IndicatorSeries):
            return _invalid("other", "equality compares another IndicatorSeries", given=repr(other))
        if self.presence != other.presence:
            return Ok(False)
        left_factor = 10**other.scale
        right_factor = 10**self.scale
        for index, state in enumerate(self.presence):
            if state is not PresenceState.PRESENT:
                continue
            if self.value_at(index) * left_factor != other.value_at(index) * right_factor:
                return Ok(False)
        return Ok(True)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this output channel."""
        return _series_identity(
            "indicator-series", self.values, self.scale, self.presence, self.knowable_at
        )

    def fingerprint(self) -> Result[Fingerprint]:
        """The output channel's ``fp1`` fingerprint, computed by the single qmf-core seam."""
        return fingerprint(self)
