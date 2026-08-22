"""CT-15 / CT-10 — bid/ask tick preservation and source-disagreement edges (Story 6.2).

Tick sources stay separately identified. Bid and ask are preserved as distinct scaled
integers with their source timestamps and are **never** merged into a mid (DEC-0119,
DEC-0105). When two sources report the same fact, agreement is a ``corroborates`` typed
lineage edge and disagreement a ``disagrees-with`` edge — both ride the existing
:class:`~qmf.data.journal.CausalEdge` CT-07-shaped value already in ``qmf-data`` (never a
``qmf-registry`` import; DEC-0120). A later revision under the same
``(source, source-native id)`` is a new artifact linked by a ``supersedes`` edge, never
an overwrite (DEC-0119, DEC-0108).

Stdlib + qmf-core + the CT-10 / CT-13 value types already in this package.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

from qmf.core import (
    Fingerprint,
    Instrument,
    Ok,
    Result,
    TypedRefusal,
    WriterId,
    fingerprint,
    is_refusal,
)
from qmf.data.journal import CausalEdge
from qmf.data.observation import ForeignMoney, ForeignTimestamp, SourceObservation
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "EDGE_CORROBORATES",
    "EDGE_DISAGREES_WITH",
    "EDGE_SUPERSEDES",
    "TickObservation",
    "TickQuote",
    "link_revision",
    "refuse_mid_merge",
    "relate_source_facts",
]

# Story 6.2 vocabulary format version — stamped into tick-quote identity. Meaning never
# mutates; an incompatible change mints the next version (DEC-0103; L15).
CONTRACT_FORMAT_VERSION: Final[int] = 1

# CT-07 / CT-15 disagreement-edge tokens (DEC-0114, DEC-0119). Hyphenated wire form.
EDGE_CORROBORATES: Final[str] = "corroborates"
EDGE_DISAGREES_WITH: Final[str] = "disagrees-with"
EDGE_SUPERSEDES: Final[str] = "supersedes"


def refuse_mid_merge(*, given: object | None = None) -> TypedRefusal:
    """Refuse collapsing bid and ask into a single mid value (AC1; DEC-0119).

    Mid is a *derived* artifact produced elsewhere under lineage — never evidence on
    this seam. Asking intake to store or emit a mid is a ``policy rejection``.
    """
    context: dict[str, object] = {
        "signal": "refuse-mid-merge",
        "component": "COMP-QMF-DATA-INGEST",
        "contract": "CT-15",
    }
    if given is not None:
        context["given"] = repr(given)
    return policy_rejection(
        "mid",
        "bid and ask are preserved separately with their source timestamps and are "
        "never merged into a single mid value (AC1, DEC-0119, DEC-0105)",
        **context,
    )


def _resolve_money(value: object, *, field: str) -> Result[ForeignMoney]:
    """Require a :class:`ForeignMoney` (or verbatim/scale mapping) for a tick side."""
    if isinstance(value, ForeignMoney):
        return Ok(value)
    if isinstance(value, Mapping):
        block = cast("Mapping[str, object]", value)
        built = ForeignMoney.try_create(block.get("verbatim"), block.get("scale"))
        if is_refusal(built):
            return built
        return Ok(built.value)
    return invalid_input(
        field,
        f"{field} is a ForeignMoney (or verbatim/scale mapping) — tick sides stay "
        "scaled integers, never a binary float (DEC-0105)",
        given=repr(value),
    )


def _resolve_optional_timestamp(
    value: object | None, *, field: str
) -> Result[ForeignTimestamp | None]:
    """Optional per-side source timestamp, stored verbatim when present."""
    if value is None:
        return Ok(None)
    if isinstance(value, ForeignTimestamp):
        return Ok(value)
    if isinstance(value, Mapping):
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
    return invalid_input(
        field,
        f"{field} is a ForeignTimestamp or a verbatim/zone/offset/resolution mapping (or omitted)",
        given=repr(value),
    )


def _money_equal(left: ForeignMoney, right: ForeignMoney) -> bool:
    return left.verbatim == right.verbatim and left.scale == right.scale


def _timestamp_equal(left: ForeignTimestamp | None, right: ForeignTimestamp | None) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return (
        left.verbatim == right.verbatim
        and left.zone == right.zone
        and left.offset == right.offset
        and left.resolution == right.resolution
    )


@dataclass(frozen=True, slots=True)
class TickQuote:
    """Bid and ask preserved separately with source timestamps (AC1; DEC-0119).

    There is no mid field and no mid factory — mid is refused at the boundary. Each
    side is a :class:`~qmf.data.observation.ForeignMoney` at the source's declared
    scale; optional per-side :class:`~qmf.data.observation.ForeignTimestamp` values
    keep the provider's own timestamps when the sides differ (or when only one side
    carries a stamp).
    """

    bid: ForeignMoney
    ask: ForeignMoney
    bid_timestamp: ForeignTimestamp | None = None
    ask_timestamp: ForeignTimestamp | None = None

    @classmethod
    def try_create(
        cls,
        *,
        bid: object,
        ask: object,
        bid_timestamp: object | None = None,
        ask_timestamp: object | None = None,
        mid: object | None = None,
    ) -> Result[TickQuote]:
        """Validate and build a :class:`TickQuote`, returning value-or-refusal.

        A presented ``mid`` is always a ``policy rejection`` — sides are never averaged
        away (AC1). Both ``bid`` and ``ask`` are required.
        """
        if mid is not None:
            return refuse_mid_merge(given=mid)
        resolved_bid = _resolve_money(bid, field="bid")
        if is_refusal(resolved_bid):
            return resolved_bid
        resolved_ask = _resolve_money(ask, field="ask")
        if is_refusal(resolved_ask):
            return resolved_ask
        resolved_bid_ts = _resolve_optional_timestamp(bid_timestamp, field="bid_timestamp")
        if is_refusal(resolved_bid_ts):
            return resolved_bid_ts
        resolved_ask_ts = _resolve_optional_timestamp(ask_timestamp, field="ask_timestamp")
        if is_refusal(resolved_ask_ts):
            return resolved_ask_ts
        return Ok(
            cls(
                bid=resolved_bid.value,
                ask=resolved_ask.value,
                bid_timestamp=resolved_bid_ts.value,
                ask_timestamp=resolved_ask_ts.value,
            )
        )

    def agrees_with(self, other: TickQuote) -> bool:
        """Whether both sides (and present source timestamps) match exactly."""
        return (
            _money_equal(self.bid, other.bid)
            and _money_equal(self.ask, other.ask)
            and _timestamp_equal(self.bid_timestamp, other.bid_timestamp)
            and _timestamp_equal(self.ask_timestamp, other.ask_timestamp)
        )

    def fp1_identity(self) -> dict[str, object]:
        """Pinned canonical ``fp1`` identity — bid and ask separately, never a mid."""
        content: dict[str, object] = {
            "class": "tick-quote",
            "bid": self.bid.fp1_identity(),
            "ask": self.ask.fp1_identity(),
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.bid_timestamp is not None:
            content["bid_timestamp"] = self.bid_timestamp.fp1_identity()
        if self.ask_timestamp is not None:
            content["ask_timestamp"] = self.ask_timestamp.fp1_identity()
        return content

    def fingerprint(self) -> Result[Fingerprint]:
        """Compute the quote's ``fp1`` through the single qmf-core implementation."""
        return fingerprint(self.fp1_identity())

    def to_row(self) -> dict[str, object]:
        """JSON-native serialization — bid and ask as distinct blocks."""
        row: dict[str, object] = {
            "bid": {"verbatim": self.bid.verbatim, "scale": self.bid.scale},
            "ask": {"verbatim": self.ask.verbatim, "scale": self.ask.scale},
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.bid_timestamp is not None:
            row["bid_timestamp"] = {
                "verbatim": self.bid_timestamp.verbatim,
                "zone": self.bid_timestamp.zone,
                "offset": self.bid_timestamp.offset,
                "resolution": self.bid_timestamp.resolution,
            }
        if self.ask_timestamp is not None:
            row["ask_timestamp"] = {
                "verbatim": self.ask_timestamp.verbatim,
                "zone": self.ask_timestamp.zone,
                "offset": self.ask_timestamp.offset,
                "resolution": self.ask_timestamp.resolution,
            }
        return row

    @classmethod
    def from_row(cls, row: object) -> Result[TickQuote]:
        """Rebuild a :class:`TickQuote` from a persisted :meth:`to_row` mapping."""
        if not isinstance(row, Mapping):
            return invalid_input("row", "a persisted tick-quote row is a mapping", given=repr(row))
        mapping = cast("Mapping[str, object]", row)
        if mapping.get("mid") is not None:
            return refuse_mid_merge(given=mapping.get("mid"))
        return cls.try_create(
            bid=mapping.get("bid"),
            ask=mapping.get("ask"),
            bid_timestamp=mapping.get("bid_timestamp"),
            ask_timestamp=mapping.get("ask_timestamp"),
        )


@dataclass(frozen=True, slots=True)
class TickObservation:
    """A CT-10 observation carrying preserved bid/ask sides for one tick source (AC1).

    ``observation`` is the bitemporal CT-10 producer value (source separately identified);
    ``quote`` holds bid and ask with source timestamps; ``instrument`` is the CT-03
    mapping used to decide when two sources report the **same fact**.
    """

    observation: SourceObservation
    quote: TickQuote
    instrument: Instrument

    @property
    def source(self) -> str:
        return self.observation.source

    @property
    def fingerprint(self) -> Fingerprint:
        """The observation's evidence identity — edges reference this ``fp1``."""
        return self.observation.fingerprint


def _same_fact(left: TickObservation, right: TickObservation) -> bool:
    """Two sources report the same fact when instrument + event-time match.

    Source identity deliberately differs — that is why disagreement edges exist. The
    provider-native id may also differ across sources for the same occurrence.
    """
    return (
        left.instrument.venue.value == right.instrument.venue.value
        and left.instrument.symbol == right.instrument.symbol
        and left.observation.event_time.value_ns == right.observation.event_time.value_ns
    )


def relate_source_facts(
    left: object,
    right: object,
    *,
    writer: object,
) -> Result[CausalEdge]:
    """Emit a ``corroborates`` or ``disagrees-with`` edge for two tick sources (AC2).

    Both arguments must be :class:`TickObservation` values for the same fact (same
    instrument and event-time) from **distinct** sources. Matching bid/ask (+ present
    timestamps) yields ``corroborates``; any difference yields ``disagrees-with``. The
    two observations are never averaged or collapsed into one number (FM-3, DEC-0119).
    The edge is a :class:`~qmf.data.journal.CausalEdge` value the application routes to
    the lineage stream — this package does not import ``qmf-registry`` (DEC-0120).
    """
    if not isinstance(left, TickObservation):
        return invalid_input(
            "left",
            "relate_source_facts compares two TickObservation values",
            given=repr(left),
        )
    if not isinstance(right, TickObservation):
        return invalid_input(
            "right",
            "relate_source_facts compares two TickObservation values",
            given=repr(right),
        )
    if not isinstance(writer, WriterId):
        return invalid_input(
            "writer",
            "a source-disagreement edge stream has exactly one holding WriterId",
            given=repr(writer),
        )
    if left.source == right.source:
        return invalid_input(
            "source",
            "corroborates / disagrees-with relate two *distinct* tick sources on the "
            "same fact — a single source does not corroborate itself (DEC-0119)",
            left=left.source,
            right=right.source,
        )
    if not _same_fact(left, right):
        return invalid_input(
            "fact",
            "corroborates / disagrees-with require the same fact (instrument + "
            "event-time) across the two sources; differing facts are not related here",
            left_event_ns=left.observation.event_time.value_ns,
            right_event_ns=right.observation.event_time.value_ns,
            left_instrument=f"{left.instrument.venue.value}/{left.instrument.symbol}",
            right_instrument=(f"{right.instrument.venue.value}/{right.instrument.symbol}"),
        )
    edge_type = EDGE_CORROBORATES if left.quote.agrees_with(right.quote) else EDGE_DISAGREES_WITH
    # from_ref = accruing/derived endpoint (first presented source); to_ref = peer.
    return CausalEdge.try_create(
        edge_type=edge_type,
        from_ref=left.fingerprint,
        to_ref=right.fingerprint,
        writer=writer,
    )


def link_revision(
    newer: object,
    earlier: object,
    *,
    writer: object,
) -> Result[CausalEdge]:
    """Link a later ``(source, id, revision)`` artifact to an earlier one (AC3).

    Both arguments are :class:`~qmf.data.observation.SourceObservation` or
    :class:`TickObservation` values. They must share ``source`` and ``source_native_id``,
    differ in ``revision``, and the newer fingerprint must differ from the earlier —
    the edge is ``supersedes`` (newer → earlier). Evidence is never overwritten
    (DEC-0119, DEC-0108). Prefer also setting ``correction_of`` on the newer
    observation at mint time; this edge is the CT-07 lineage link the application
    routes alongside.
    """
    newer_obs = _as_observation(newer, field="newer")
    if is_refusal(newer_obs):
        return newer_obs
    earlier_obs = _as_observation(earlier, field="earlier")
    if is_refusal(earlier_obs):
        return earlier_obs
    if not isinstance(writer, WriterId):
        return invalid_input(
            "writer",
            "a revision-link edge stream has exactly one holding WriterId",
            given=repr(writer),
        )
    n = newer_obs.value
    e = earlier_obs.value
    if n.source != e.source or n.source_native_id != e.source_native_id:
        return invalid_input(
            "intake_key",
            "a revision link requires the same (source, source-native id) under a new "
            "revision — different facts are not revision-linked (DEC-0119)",
            newer_source=n.source,
            earlier_source=e.source,
            newer_native_id=n.source_native_id,
            earlier_native_id=e.source_native_id,
        )
    if n.revision == e.revision:
        return invalid_input(
            "revision",
            "a revision link requires a distinct revision token; the same revision is "
            "idempotent intake, not a superseding artifact (DEC-0119)",
            revision=n.revision,
        )
    if n.fingerprint.value == e.fingerprint.value:
        return invalid_input(
            "fingerprint",
            "a later revision must mint a distinct fp1 artifact — identical "
            "fingerprints are not a superseding pair (DEC-0108)",
            fingerprint=n.fingerprint.value,
        )
    return CausalEdge.try_create(
        edge_type=EDGE_SUPERSEDES,
        from_ref=n.fingerprint,
        to_ref=e.fingerprint,
        writer=writer,
    )


def _as_observation(value: object, *, field: str) -> Result[SourceObservation]:
    if isinstance(value, TickObservation):
        return Ok(value.observation)
    if isinstance(value, SourceObservation):
        return Ok(value)
    return invalid_input(
        field,
        f"{field} is a SourceObservation or TickObservation",
        given=repr(value),
    )
