"""Reference usage — bid/ask preservation and source-disagreement edges (Story 6.2).

Executable::

    python packages/qmf-data/examples/ticks_usage.py

Shows the three things Story 6.2 pins down:

1. Tick sources stay separately identified; bid and ask are preserved with source
   timestamps and are never merged into a mid (AC1).
2. Two sources on the same fact emit corroborates on agreement and disagrees-with
   on disagreement — never averaged away (AC2).
3. A later (source, id, revision) artifact links to the earlier one via supersedes,
   never overwriting it (AC3).
"""

from __future__ import annotations

import sys
from typing import TypeVar

from qmf.core import (
    Instrument,
    Ok,
    RefusalCategory,
    Result,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.data import (
    EDGE_CORROBORATES,
    EDGE_DISAGREES_WITH,
    EDGE_SUPERSEDES,
    ExternalSourceIngest,
    IntakeReceipt,
    ProviderRecord,
    SourceRequest,
    TickObservation,
    TickQuote,
    link_revision,
    refuse_mid_merge,
    relate_source_facts,
)

T = TypeVar("T")

_EVENT_NS = 1_700_000_000_000_000_000
_KNOWN_NS = 1_700_000_001_000_000_000
_RECEIVE_NS = 1_700_000_002_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def _require(condition: object, what: str) -> None:
    if not condition:
        raise AssertionError(f"expected {what}")


def _writer(stream: str = "ticks") -> WriterId:
    return _unwrap(WriterId.try_create("node-a", "ingest", stream, "boot-1"), "writer")


def _instrument() -> Instrument:
    venue = _unwrap(VenueId.try_create("broker-a"), "venue")
    return _unwrap(Instrument.try_create(venue, "EURUSD"), "instrument")


class _DemoPort:
    """Stand-in CT-15 provider returning no network payload — records are intake'd directly."""

    def fetch(self, request: SourceRequest, /) -> Result[tuple[ProviderRecord, ...]]:
        del request
        return Ok(())


def _quote(
    source: str,
    native_id: str,
    *,
    event_delta: int = 0,
    bid: int = 110250,
    ask: int = 110260,
    revision: str = "r1",
    known_at: int | None = None,
    bid_timestamp: dict[str, str] | None = None,
    ask_timestamp: dict[str, str] | None = None,
    correction_of: object | None = None,
) -> ProviderRecord:
    return ProviderRecord(
        source=source,
        source_native_id=native_id,
        revision=revision,
        event_time=_EVENT_NS + event_delta,
        known_at=_KNOWN_NS if known_at is None else known_at,
        instrument=_instrument(),
        bid={"verbatim": bid, "scale": 5},
        ask={"verbatim": ask, "scale": 5},
        bid_timestamp=bid_timestamp,
        ask_timestamp=ask_timestamp,
        correction_of=correction_of,
    )


def _intake_tick(
    ingest: ExternalSourceIngest,
    record: ProviderRecord,
    *,
    stream: str = "ticks",
    sequence: int,
    what: str,
) -> IntakeReceipt:
    return _unwrap(
        ingest.intake(
            record,
            writer=_writer(stream),
            sequence=sequence,
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS,
        ),
        what,
    )


def bid_ask_preserved(ingest: ExternalSourceIngest) -> str:
    receipt = _intake_tick(
        ingest,
        _quote(
            "dukascopy",
            "EURUSD#42",
            bid_timestamp={
                "verbatim": "2026-08-21T12:00:00.123",
                "zone": "UTC",
                "offset": "+00:00",
                "resolution": "ms",
            },
            ask_timestamp={
                "verbatim": "2026-08-21T12:00:00.124",
                "zone": "UTC",
                "offset": "+00:00",
                "resolution": "ms",
            },
        ),
        sequence=0,
        what="dukascopy tick",
    )
    quote = receipt.quote
    if not isinstance(quote, TickQuote):
        raise AssertionError("expected quote present")
    if receipt.tick is None:
        raise AssertionError("expected tick observation present")
    mid = refuse_mid_merge(given=(quote.bid.verbatim + quote.ask.verbatim) // 2)
    _require(is_refusal(mid) and mid.category is RefusalCategory.POLICY_REJECTION, "mid refused")
    return (
        f"bid={quote.bid.verbatim} ask={quote.ask.verbatim} "
        f"(source={receipt.intake_key.source}; mid merge refused)"
    )


def _agree_pair(ingest: ExternalSourceIngest) -> tuple[TickObservation, TickObservation]:
    dukas = _intake_tick(
        ingest,
        _quote("dukascopy", "EURUSD#same-fact", event_delta=10),
        stream="dukascopy",
        sequence=1,
        what="dukascopy fact",
    )
    agree = _intake_tick(
        ingest,
        _quote("broker-feed", "EURUSD#peer-agree", event_delta=10),
        stream="broker",
        sequence=0,
        what="broker agree",
    )
    if dukas.tick is None or agree.tick is None:
        raise AssertionError("expected agree ticks")
    return dukas.tick, agree.tick


def _disagree_pair(ingest: ExternalSourceIngest) -> tuple[TickObservation, TickObservation]:
    disagree = _intake_tick(
        ingest,
        _quote("broker-feed", "EURUSD#peer-disagree", event_delta=20, ask=110999),
        stream="broker",
        sequence=1,
        what="broker disagree peer",
    )
    dukas_b = _intake_tick(
        ingest,
        _quote("dukascopy", "EURUSD#same-fact-b", event_delta=20),
        stream="dukascopy",
        sequence=2,
        what="dukascopy disagree fact",
    )
    if dukas_b.tick is None or disagree.tick is None:
        raise AssertionError("expected disagree ticks")
    return dukas_b.tick, disagree.tick


def disagreement_edges(ingest: ExternalSourceIngest) -> str:
    left, right = _agree_pair(ingest)
    other, peer = _disagree_pair(ingest)
    corr = _unwrap(
        relate_source_facts(left, right, writer=_writer("lineage")),
        "corroborates",
    )
    disc = _unwrap(
        relate_source_facts(other, peer, writer=_writer("lineage")),
        "disagrees-with",
    )
    _require(corr.edge_type == EDGE_CORROBORATES, "corroborates edge")
    _require(disc.edge_type == EDGE_DISAGREES_WITH, "disagrees-with edge")
    return f"{corr.edge_type} on agreement; {disc.edge_type} on disagreement (never averaged)"


def revision_linked(ingest: ExternalSourceIngest) -> str:
    first = _intake_tick(
        ingest,
        _quote("dukascopy", "EURUSD#rev", event_delta=30),
        sequence=3,
        what="r1",
    )
    second = _intake_tick(
        ingest,
        _quote(
            "dukascopy",
            "EURUSD#rev",
            event_delta=30,
            revision="r2",
            known_at=_KNOWN_NS + 1,
            bid=110251,
            ask=110261,
            correction_of=first.observation.fingerprint,
        ),
        sequence=4,
        what="r2",
    )
    _require(
        first.observation.fingerprint.value != second.observation.fingerprint.value,
        "distinct fp1",
    )
    if first.tick is None or second.tick is None:
        raise AssertionError("expected revision ticks")
    edge = _unwrap(
        link_revision(second.tick, first.tick, writer=_writer("lineage")),
        "supersedes",
    )
    _require(edge.edge_type == EDGE_SUPERSEDES, "supersedes edge")
    return (
        f"r2 supersedes r1 ({edge.from_ref.value[-12:]} -> {edge.to_ref.value[-12:]}); "
        "earlier evidence kept"
    )


def main() -> None:
    ingest = ExternalSourceIngest(_DemoPort())
    sys.stdout.write(f"bid/ask preserved: {bid_ask_preserved(ingest)}\n")
    sys.stdout.write(f"source disagreement: {disagreement_edges(ingest)}\n")
    sys.stdout.write(f"revision link: {revision_linked(ingest)}\n")


if __name__ == "__main__":
    main()
