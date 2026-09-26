"""CT-10 verbatim foreign evidence types and small coercers.

Split from :mod:`qmf.data.observation` so the public module stays under the
Skylos god-file limits. Callers keep importing these names from
:mod:`qmf.data.observation`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    Fingerprint,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    World,
    WriterId,
    is_ok,
    is_refusal,
)

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "ForeignMoney",
    "ForeignTimestamp",
    "MarketDataContext",
]

# CT-10 carries its own integer contract format version, stamped into every observation
# artifact; its meaning never mutates — an incompatible change mints the next version
# plus a migration note (DEC-0103; versioning-from-birth L15). This is CT-10's own, not
# CT-05's — each contract owns its format version.
CONTRACT_FORMAT_VERSION: Final[int] = 1


def invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
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


def clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``.

    Provenance tokens (source, source-native id, revision) and the verbatim foreign
    timestamp parts are opaque: the returned token is the caller's string unchanged —
    never stripped, cased, or parsed.
    """
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def as_instant(value: object) -> Instant | None:
    """Resolve ``value`` to an :class:`~qmf.core.Instant`, or ``None``.

    Accepts an :class:`~qmf.core.Instant` or an int64 UTC-nanosecond count (built through
    ``Instant.try_create`` so the range check is qmf-core's, never restated here).
    """
    if isinstance(value, Instant):
        return value
    built = Instant.try_create(value)
    return built.value if is_ok(built) else None


def coerce_world(value: object) -> World | None:
    """Resolve ``value`` to a :class:`~qmf.core.World` member, or ``None``."""
    if isinstance(value, World):
        return value
    if isinstance(value, str):
        try:
            return World(value)
        except ValueError:
            return None
    return None


def coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`~qmf.core.Fingerprint` or a valid ``fp1:sha256:<hex>`` string."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    return parsed.value if is_ok(parsed) else None


def writer_identity(writer: WriterId) -> dict[str, object]:
    """The writer's identity content — :class:`~qmf.core.WriterId` exposes no
    ``fp1_identity``, so its ``(machine, role, stream, boot_epoch_id)`` parts are folded
    in explicitly and consistently."""
    return {
        "machine": writer.machine,
        "role": writer.role,
        "stream": writer.stream,
        "boot_epoch_id": writer.boot_epoch_id,
    }


def _require_market_tokens(
    venue: object,
    symbol: object,
    resolution: object,
    license_tag: object,
) -> Result[dict[str, str]]:
    """Validate the opaque market-data coordinate tokens, or refuse the first blank."""
    tokens: dict[str, str] = {}
    for field_name, value in (
        ("venue", venue),
        ("symbol", symbol),
        ("resolution", resolution),
        ("license_tag", license_tag),
    ):
        token = clean_str(value)
        if token is None:
            return invalid(
                f"market_data.{field_name}",
                f"market-data {field_name} is a non-empty opaque token",
                given=repr(value),
            )
        tokens[field_name] = token
    return Ok(tokens)


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
        clean_verbatim = clean_str(verbatim)
        if clean_verbatim is None:
            return invalid(
                "foreign_timestamp.verbatim",
                "the source timestamp is stored verbatim as a non-empty string",
                given=repr(verbatim),
            )
        clean_zone = clean_str(zone)
        if clean_zone is None:
            return invalid(
                "foreign_timestamp.zone",
                "the foreign timestamp carries its declared zone as a non-empty string",
                given=repr(zone),
            )
        return _finish_foreign_timestamp(cls, clean_verbatim, clean_zone, offset, resolution)

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


def _finish_foreign_timestamp(
    cls: type[ForeignTimestamp],
    verbatim: str,
    zone: str,
    offset: object,
    resolution: object,
) -> Result[ForeignTimestamp]:
    """Validate offset/resolution and construct the frozen timestamp."""
    clean_offset = clean_str(offset)
    if clean_offset is None:
        return invalid(
            "foreign_timestamp.offset",
            "the foreign timestamp carries its declared UTC offset as a non-empty string",
            given=repr(offset),
        )
    clean_resolution = clean_str(resolution)
    if clean_resolution is None:
        return invalid(
            "foreign_timestamp.resolution",
            "the foreign timestamp carries the source's actual resolution as a "
            "non-empty string (e.g. milliseconds)",
            given=repr(resolution),
        )
    return Ok(
        cls(
            verbatim=verbatim,
            zone=zone,
            offset=clean_offset,
            resolution=clean_resolution,
        )
    )


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
            return invalid(
                "foreign_money.verbatim",
                "foreign money is a verbatim scaled integer, never a binary float (DEC-0105)",
                given=repr(verbatim),
            )
        if isinstance(scale, bool) or not isinstance(scale, int) or scale < 0:
            return invalid(
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


@dataclass(frozen=True, slots=True)
class MarketDataContext:
    """Identity-bearing market-data coordinates carried by a CT-10 observation.

    The context makes a persisted venue observation self-describing: catalog views can
    be rebuilt from the observation itself without treating an acquisition-request
    envelope as evidence.  The usage right and provenance ride the same immutable row.
    """

    venue: str
    symbol: str
    resolution: str
    side: str
    license_tag: str
    provenance: Mapping[str, object]

    @classmethod
    def try_create(
        cls,
        *,
        venue: object,
        symbol: object,
        resolution: object,
        side: object,
        license_tag: object,
        provenance: object,
    ) -> Result[MarketDataContext]:
        """Validate the self-describing coordinates and copy provenance read-only."""
        tokens = _require_market_tokens(venue, symbol, resolution, license_tag)
        if is_refusal(tokens):
            return tokens
        side_token = clean_str(side)
        if side_token not in ("bid", "ask"):
            return invalid(
                "market_data.side",
                "a persisted market-data observation names its actual bid or ask side",
                given=repr(side),
            )
        if not isinstance(provenance, Mapping):
            return invalid(
                "market_data.provenance",
                "market-data provenance is a mapping recorded on the observation",
                given=repr(provenance),
            )
        copied = MappingProxyType(dict(cast("Mapping[str, object]", provenance)))
        body = tokens.value
        return Ok(
            cls(
                venue=body["venue"],
                symbol=body["symbol"],
                resolution=body["resolution"],
                side=side_token,
                license_tag=body["license_tag"],
                provenance=copied,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity: coordinates, usage right, and provenance."""
        return {
            "class": "market-data-context",
            "venue": self.venue,
            "symbol": self.symbol,
            "resolution": self.resolution,
            "side": self.side,
            "license_tag": self.license_tag,
            "provenance": dict(self.provenance),
            "format_version": CONTRACT_FORMAT_VERSION,
        }

    def to_row(self) -> dict[str, object]:
        """JSON-native nested row carried by :class:`SourceObservation`."""
        return {
            "venue": self.venue,
            "symbol": self.symbol,
            "resolution": self.resolution,
            "side": self.side,
            "license_tag": self.license_tag,
            "provenance": dict(self.provenance),
            "format_version": CONTRACT_FORMAT_VERSION,
        }

    @classmethod
    def from_row(cls, row: object) -> Result[MarketDataContext]:
        """Rebuild a context from its persisted nested mapping."""
        if not isinstance(row, Mapping):
            return invalid(
                "market_data",
                "persisted market-data context is a mapping",
                given=repr(row),
            )
        body = cast("Mapping[str, object]", row)
        return cls.try_create(
            venue=body.get("venue"),
            symbol=body.get("symbol"),
            resolution=body.get("resolution"),
            side=body.get("side"),
            license_tag=body.get("license_tag"),
            provenance=body.get("provenance"),
        )
