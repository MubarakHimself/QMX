"""Tier-1 tests for bid/ask preservation and source-disagreement edges (Story 6.2)."""

from __future__ import annotations

from qmf.core import (
    Instrument,
    Ok,
    RefusalCategory,
    Result,
    VenueId,
    World,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.data import (
    EDGE_CORROBORATES,
    EDGE_DISAGREES_WITH,
    EDGE_SUPERSEDES,
    ExternalSourceIngest,
    ForeignMoney,
    ForeignTimestamp,
    IntakeOutcome,
    ProviderRecord,
    SourceObservation,
    SourceRequest,
    TickObservation,
    TickQuote,
    link_revision,
    refuse_mid_merge,
    relate_source_facts,
)
from qmf.data.ingest import IntakeKey
from qmf.data.ticks import CONTRACT_FORMAT_VERSION

_EVENT_NS = 1_700_000_000_000_000_000
_KNOWN_NS = 1_700_000_001_000_000_000
_RECEIVE_NS = 1_700_000_002_000_000_000


def _writer(stream: str = "ticks") -> WriterId:
    built = WriterId.try_create("node-a", "ingest", stream, "boot-1")
    assert is_ok(built)
    return built.value


def _instrument() -> Instrument:
    venue = VenueId.try_create("broker-a")
    assert is_ok(venue)
    built = Instrument.try_create(venue.value, "EURUSD")
    assert is_ok(built)
    return built.value


def _money(verbatim: int = 110250, scale: int = 5) -> ForeignMoney:
    built = ForeignMoney.try_create(verbatim, scale)
    assert is_ok(built)
    return built.value


def _ts(verbatim: str = "2026-08-21T12:00:00.123") -> ForeignTimestamp:
    built = ForeignTimestamp.try_create(verbatim, "UTC", "+00:00", "ms")
    assert is_ok(built)
    return built.value


def _quote(**overrides: object) -> TickQuote:
    parts: dict[str, object] = {
        "bid": _money(110250),
        "ask": _money(110260),
        "bid_timestamp": _ts("2026-08-21T12:00:00.123"),
        "ask_timestamp": _ts("2026-08-21T12:00:00.124"),
    }
    parts.update(overrides)
    built = TickQuote.try_create(**parts)  # type: ignore[arg-type]
    assert is_ok(built), built
    return built.value


def _observation(**overrides: object) -> SourceObservation:
    parts: dict[str, object] = {
        "event_time": _EVENT_NS,
        "known_at": _KNOWN_NS,
        "source": "dukascopy",
        "source_native_id": "EURUSD#42",
        "revision": "r1",
        "receive_wall_time": _RECEIVE_NS,
        "writer": _writer(),
        "sequence": 0,
        "world": World.LIVE,
    }
    parts.update(overrides)
    built = SourceObservation.try_create(**parts)  # type: ignore[arg-type]
    assert is_ok(built), built
    return built.value


def _tick(**overrides: object) -> TickObservation:
    obs_overrides = {
        k: overrides.pop(k)
        for k in list(overrides)
        if k
        in {
            "event_time",
            "known_at",
            "source",
            "source_native_id",
            "revision",
            "receive_wall_time",
            "writer",
            "sequence",
            "world",
            "correction_of",
        }
    }
    quote = overrides.pop("quote", _quote())
    instrument = overrides.pop("instrument", _instrument())
    assert not overrides, overrides
    return TickObservation(
        observation=_observation(**obs_overrides),
        quote=quote,  # type: ignore[arg-type]
        instrument=instrument,  # type: ignore[arg-type]
    )


class _Port:
    def fetch(self, request: SourceRequest, /) -> Result[tuple[ProviderRecord, ...]]:
        del request
        return Ok(())


# --- AC1: bid/ask preserved, never mid --------------------------------------


def test_tick_quote_preserves_bid_and_ask_separately() -> None:
    quote = _quote()
    assert quote.bid.verbatim == 110250
    assert quote.ask.verbatim == 110260
    assert quote.bid_timestamp is not None
    assert quote.ask_timestamp is not None
    assert not hasattr(quote, "mid")
    identity = quote.fp1_identity()
    assert "bid" in identity
    assert "ask" in identity
    assert "mid" not in identity
    assert identity["format_version"] == CONTRACT_FORMAT_VERSION
    fp = quote.fingerprint()
    assert is_ok(fp)
    recomputed = fingerprint(quote.fp1_identity())
    assert is_ok(recomputed)
    assert recomputed.value.value == fp.value.value


def test_mid_merge_is_policy_rejection() -> None:
    refused = TickQuote.try_create(bid=_money(1), ask=_money(2), mid=110255)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "mid"
    direct = refuse_mid_merge(given=110255)
    assert is_refusal(direct)
    assert direct.category is RefusalCategory.POLICY_REJECTION


def test_tick_quote_row_round_trip() -> None:
    quote = _quote()
    rebuilt = TickQuote.from_row(quote.to_row())
    assert is_ok(rebuilt)
    assert rebuilt.value.agrees_with(quote)
    assert is_refusal(TickQuote.from_row({"bid": {"verbatim": 1, "scale": 5}, "mid": 2}))


def test_ingest_preserves_bid_ask_on_tick_record() -> None:
    ingest = ExternalSourceIngest(_Port())
    receipt = ingest.intake(
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
    )
    assert is_ok(receipt)
    assert receipt.value.outcome is IntakeOutcome.PRODUCED
    assert receipt.value.quote is not None
    assert receipt.value.quote.bid.verbatim == 110250
    assert receipt.value.quote.ask.verbatim == 110260
    assert receipt.value.tick is not None
    assert receipt.value.tick.source == "dukascopy"


def test_ingest_refuses_mid_and_partial_sides() -> None:
    ingest = ExternalSourceIngest(_Port())
    mid = ingest.intake(
        ProviderRecord(
            source="dukascopy",
            source_native_id="EURUSD#m",
            revision="r1",
            event_time=_EVENT_NS,
            known_at=_KNOWN_NS,
            instrument=_instrument(),
            mid=110255,
        ),
        writer=_writer(),
        sequence=0,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_refusal(mid)
    assert mid.category is RefusalCategory.POLICY_REJECTION

    partial = ingest.intake(
        ProviderRecord(
            source="dukascopy",
            source_native_id="EURUSD#p",
            revision="r1",
            event_time=_EVENT_NS,
            known_at=_KNOWN_NS,
            instrument=_instrument(),
            bid={"verbatim": 110250, "scale": 5},
        ),
        writer=_writer(),
        sequence=1,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_refusal(partial)
    assert partial.category is RefusalCategory.INVALID_INPUT


# --- AC2: corroborates / disagrees-with -------------------------------------


def test_agreement_emits_corroborates_edge() -> None:
    left = _tick(source="dukascopy", source_native_id="d#1", sequence=0)
    right = _tick(
        source="broker-feed",
        source_native_id="b#1",
        sequence=1,
        writer=_writer("broker"),
    )
    edge = relate_source_facts(left, right, writer=_writer("lineage"))
    assert is_ok(edge)
    assert edge.value.edge_type == EDGE_CORROBORATES
    assert edge.value.from_ref.value == left.fingerprint.value
    assert edge.value.to_ref.value == right.fingerprint.value
    row = edge.value.to_row()
    assert row["edge_type"] == "corroborates"
    assert row["from_ref"] == left.fingerprint.value
    assert row["to_ref"] == right.fingerprint.value


def test_disagreement_emits_disagrees_with_edge_never_averaged() -> None:
    left = _tick(source="dukascopy", source_native_id="d#1", sequence=0)
    right = _tick(
        source="broker-feed",
        source_native_id="b#1",
        sequence=1,
        writer=_writer("broker"),
        quote=_quote(ask=_money(110999)),
    )
    edge = relate_source_facts(left, right, writer=_writer("lineage"))
    assert is_ok(edge)
    assert edge.value.edge_type == EDGE_DISAGREES_WITH
    # Both observation fingerprints remain distinct — disagreement is visible, not merged.
    assert left.fingerprint.value != right.fingerprint.value
    assert left.quote.ask.verbatim != right.quote.ask.verbatim


def test_relate_refuses_same_source_or_different_fact() -> None:
    a = _tick(source="dukascopy", sequence=0)
    same_source = _tick(source="dukascopy", source_native_id="other", sequence=1)
    assert is_refusal(relate_source_facts(a, same_source, writer=_writer()))
    other_fact = _tick(
        source="broker-feed",
        event_time=_EVENT_NS + 1,
        sequence=1,
        writer=_writer("broker"),
    )
    assert is_refusal(relate_source_facts(a, other_fact, writer=_writer()))


# --- AC3: later revision is a new linked artifact ---------------------------


def test_revision_is_new_artifact_linked_by_supersedes() -> None:
    earlier = _observation(revision="r1", sequence=0)
    newer = _observation(revision="r2", sequence=1, correction_of=earlier.fingerprint)
    assert newer.fingerprint.value != earlier.fingerprint.value
    edge = link_revision(newer, earlier, writer=_writer("lineage"))
    assert is_ok(edge)
    assert edge.value.edge_type == EDGE_SUPERSEDES
    assert edge.value.from_ref.value == newer.fingerprint.value
    assert edge.value.to_ref.value == earlier.fingerprint.value


def test_ingest_revision_idempotent_key_and_link() -> None:
    ingest = ExternalSourceIngest(_Port())
    first = ingest.intake(
        ProviderRecord(
            source="dukascopy",
            source_native_id="EURUSD#42",
            revision="r1",
            event_time=_EVENT_NS,
            known_at=_KNOWN_NS,
            instrument=_instrument(),
            bid={"verbatim": 110250, "scale": 5},
            ask={"verbatim": 110260, "scale": 5},
        ),
        writer=_writer(),
        sequence=0,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_ok(first)
    revised = ingest.intake(
        ProviderRecord(
            source="dukascopy",
            source_native_id="EURUSD#42",
            revision="r2",
            event_time=_EVENT_NS,
            known_at=_KNOWN_NS + 1,
            instrument=_instrument(),
            bid={"verbatim": 110251, "scale": 5},
            ask={"verbatim": 110261, "scale": 5},
            correction_of=first.value.observation.fingerprint,
        ),
        writer=_writer(),
        sequence=1,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_ok(revised)
    assert revised.value.outcome is IntakeOutcome.PRODUCED
    assert revised.value.intake_key == IntakeKey("dukascopy", "EURUSD#42", "r2")
    assert revised.value.observation.fingerprint.value != first.value.observation.fingerprint.value
    # Original evidence untouched in the ledger.
    assert ingest.known_key(IntakeKey("dukascopy", "EURUSD#42", "r1"))
    edge = link_revision(revised.value.tick, first.value.tick, writer=_writer("lineage"))
    assert is_ok(edge)
    assert edge.value.edge_type == EDGE_SUPERSEDES


def test_link_revision_refuses_same_revision_or_different_key() -> None:
    a = _observation(revision="r1")
    same = _observation(revision="r1", sequence=1)
    # Same content under same revision shares fp1 when writer/sequence differ... actually
    # sequence is identity, so fingerprints differ. Still same revision token → refuse.
    refused = link_revision(same, a, writer=_writer())
    assert is_refusal(refused)
    other_source = _observation(source="broker-feed", revision="r2")
    assert is_refusal(link_revision(other_source, a, writer=_writer()))
