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
    ProviderRecord,
    SourceRequest,
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


def bid_ask_preserved(ingest: ExternalSourceIngest) -> str:
    receipt = _unwrap(
        ingest.intake(
            ProviderRecord(
                source="dukascopy",
                source_native_id="EURUSD#42",
                revision="r1",
                event_time=_EVENT_NS,
                known_at=_KNOWN_NS,
                instrument=_instrument(),
                bid={"verbatim": 110250, "scale": 5},
                ask={"verbatim": 110260, "scale": 5},
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
            writer=_writer(),
            sequence=0,
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS,
        ),
        "dukascopy tick",
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


def disagreement_edges(ingest: ExternalSourceIngest) -> str:
    dukas = _unwrap(
        ingest.intake(
            ProviderRecord(
                source="dukascopy",
                source_native_id="EURUSD#same-fact",
                revision="r1",
                event_time=_EVENT_NS + 10,
                known_at=_KNOWN_NS,
                instrument=_instrument(),
                bid={"verbatim": 110250, "scale": 5},
                ask={"verbatim": 110260, "scale": 5},
            ),
            writer=_writer("dukascopy"),
            sequence=1,
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS,
        ),
        "dukascopy fact",
    )
    agree = _unwrap(
        ingest.intake(
            ProviderRecord(
                source="broker-feed",
                source_native_id="EURUSD#peer-agree",
                revision="r1",
                event_time=_EVENT_NS + 10,
                known_at=_KNOWN_NS,
                instrument=_instrument(),
                bid={"verbatim": 110250, "scale": 5},
                ask={"verbatim": 110260, "scale": 5},
            ),
            writer=_writer("broker"),
            sequence=0,
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS,
        ),
        "broker agree",
    )
    disagree = _unwrap(
        ingest.intake(
            ProviderRecord(
                source="broker-feed",
                source_native_id="EURUSD#peer-disagree",
                revision="r1",
                event_time=_EVENT_NS + 20,
                known_at=_KNOWN_NS,
                instrument=_instrument(),
                bid={"verbatim": 110250, "scale": 5},
                ask={"verbatim": 110999, "scale": 5},
            ),
            writer=_writer("broker"),
            sequence=1,
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS,
        ),
        "broker disagree peer",
    )
    dukas_b = _unwrap(
        ingest.intake(
            ProviderRecord(
                source="dukascopy",
                source_native_id="EURUSD#same-fact-b",
                revision="r1",
                event_time=_EVENT_NS + 20,
                known_at=_KNOWN_NS,
                instrument=_instrument(),
                bid={"verbatim": 110250, "scale": 5},
                ask={"verbatim": 110260, "scale": 5},
            ),
            writer=_writer("dukascopy"),
            sequence=2,
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS,
        ),
        "dukascopy disagree fact",
    )
    if dukas.tick is None or agree.tick is None:
        raise AssertionError("expected agree ticks")
    if dukas_b.tick is None or disagree.tick is None:
        raise AssertionError("expected disagree ticks")
    corr = _unwrap(
        relate_source_facts(dukas.tick, agree.tick, writer=_writer("lineage")),
        "corroborates",
    )
    disc = _unwrap(
        relate_source_facts(dukas_b.tick, disagree.tick, writer=_writer("lineage")),
        "disagrees-with",
    )
    _require(corr.edge_type == EDGE_CORROBORATES, "corroborates edge")
    _require(disc.edge_type == EDGE_DISAGREES_WITH, "disagrees-with edge")
    return f"{corr.edge_type} on agreement; {disc.edge_type} on disagreement (never averaged)"


def revision_linked(ingest: ExternalSourceIngest) -> str:
    first = _unwrap(
        ingest.intake(
            ProviderRecord(
                source="dukascopy",
                source_native_id="EURUSD#rev",
                revision="r1",
                event_time=_EVENT_NS + 30,
                known_at=_KNOWN_NS,
                instrument=_instrument(),
                bid={"verbatim": 110250, "scale": 5},
                ask={"verbatim": 110260, "scale": 5},
            ),
            writer=_writer(),
            sequence=3,
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS,
        ),
        "r1",
    )
    second = _unwrap(
        ingest.intake(
            ProviderRecord(
                source="dukascopy",
                source_native_id="EURUSD#rev",
                revision="r2",
                event_time=_EVENT_NS + 30,
                known_at=_KNOWN_NS + 1,
                instrument=_instrument(),
                bid={"verbatim": 110251, "scale": 5},
                ask={"verbatim": 110261, "scale": 5},
                correction_of=first.observation.fingerprint,
            ),
            writer=_writer(),
            sequence=4,
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS,
        ),
        "r2",
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
        f"r2 supersedes r1 ({edge.from_ref.value[-12:]} → {edge.to_ref.value[-12:]}); "
        "earlier evidence kept"
    )


def main() -> None:
    ingest = ExternalSourceIngest(_DemoPort())
    print(f"bid/ask preserved: {bid_ask_preserved(ingest)}")
    print(f"source disagreement: {disagreement_edges(ingest)}")
    print(f"revision link: {revision_linked(ingest)}")


if __name__ == "__main__":
    main()
