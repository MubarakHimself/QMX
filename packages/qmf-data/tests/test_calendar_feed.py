"""Tier-1 tests for the news-calendar CT-15 feed with fail-closed degradation (Story 6.4)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from qmf.core import (
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
from qmf.data import (
    CALENDAR_FEED_SOURCE,
    LEGAL_ARCHIVING_POSTURE,
    CalendarEvent,
    CalendarFeedAdapter,
    CalendarFeedImport,
    CalendarImportReceipt,
    EvidenceStore,
    ExternalSourceIngest,
    FailClosedReason,
    FailClosedSignal,
    IntakeKey,
    IntakeOutcome,
    JournalEventType,
    JournalReader,
    JournalWriter,
    SourceObservationBoundary,
    SourceRequest,
    decode_calendar_snapshot,
    fail_closed,
    refuse_authorized_retention_claim,
    refuse_live_skip,
    refuse_minted_severity_scale,
)
from qmf.data.calendar_feed import CONTRACT_FORMAT_VERSION

_EVENT_NS = 1_724_140_200_000_000_000  # approx 2024-08-20T14:30:00Z
_KNOWN_NS = _EVENT_NS + 3_600 * 1_000_000_000
_RECEIVE_NS = _KNOWN_NS + 1_000_000
_JOURNAL_NS = _RECEIVE_NS + 1_000_000


def _writer(stream: str = "calendar") -> WriterId:
    built = WriterId.try_create("node-a", "recorder", stream, "boot-1")
    assert is_ok(built)
    return built.value


def _dq_writer(store: EvidenceStore) -> JournalWriter:
    world = store.for_world(World.LIVE)
    assert is_ok(world)
    return JournalWriter(world.value.journal, _writer("dq"), stream_name="dq")


def _snapshot(*events: dict[str, object]) -> bytes:
    return json.dumps(list(events)).encode("utf-8")


def _nfp(*, revision_note: str | None = None) -> dict[str, object]:
    row: dict[str, object] = {
        "title": "Non-Farm Payrolls",
        "country": "USD",
        "date": "2024-08-20T14:30:00+00:00",
        "impact": "High",
        "forecast": "180K",
        "previous": "175K",
    }
    if revision_note is not None:
        row["id"] = f"nfp-2024-08-20-{revision_note}"
    else:
        row["id"] = "nfp-2024-08-20"
    return row


def _cpi() -> dict[str, object]:
    return {
        "title": "CPI y/y",
        "country": "EUR",
        "date": "2024-08-20T09:00:00+00:00",
        "impact": "Medium",
        "id": "cpi-eur-2024-08-20",
    }


class _FixtureTransport:
    """In-memory CalendarFeedTransport — never hits the live CDN."""

    def __init__(self, body: bytes | None = None) -> None:
        self.body = body if body is not None else _snapshot(_nfp())
        self.calls: list[dict[str, object]] = []
        self.mode = "ok"

    def fail_unavailable(self) -> None:
        self.mode = "unavailable"

    def fail_rate_limit(self) -> None:
        self.mode = "rate-limit"

    def fetch_snapshot(self, bounds: Mapping[str, object], /) -> Result[bytes]:
        self.calls.append(dict(bounds))
        if self.mode == "unavailable":
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.YES,
                context={"signal": "source-unavailable", "source": CALENDAR_FEED_SOURCE},
            )
        if self.mode == "rate-limit":
            return TypedRefusal(
                category=RefusalCategory.TRANSIENT_VENUE_FAILURE,
                retryability=Retryability.YES,
                context={"signal": "rate-limited", "source": CALENDAR_FEED_SOURCE},
            )
        return Ok(self.body)


def _adapter(
    transport: _FixtureTransport | None = None,
) -> tuple[CalendarFeedAdapter, _FixtureTransport]:
    port = transport or _FixtureTransport()
    return CalendarFeedAdapter(port), port


def _bounds(**overrides: object) -> dict[str, object]:
    parts: dict[str, object] = {"known_at_ns": _KNOWN_NS, "revision": "r1"}
    parts.update(overrides)
    return parts


# --- AC1: provider-native identity + idempotent revision --------------------


def test_format_version_and_source_identity() -> None:
    assert CONTRACT_FORMAT_VERSION == 1
    assert CALENDAR_FEED_SOURCE == "news-calendar"
    assert LEGAL_ARCHIVING_POSTURE == "open-operator-item"


def test_fetch_preserves_provider_native_identity_and_impact() -> None:
    adapter, port = _adapter(_FixtureTransport(_snapshot(_nfp(), _cpi())))
    result = adapter.fetch(SourceRequest(source=CALENDAR_FEED_SOURCE, bounds=_bounds()))
    assert is_ok(result)
    assert len(port.calls) == 1
    records = result.value
    assert len(records) == 2
    assert all(r.source == CALENDAR_FEED_SOURCE for r in records)
    assert records[0].source_native_id == "nfp-2024-08-20"
    assert records[0].revision == "r1"
    events = adapter.last_events
    assert events[0].impact_label == "High"
    assert events[1].impact_label == "Medium"
    assert events[0].currency == "USD"
    assert events[1].currency == "EUR"


def test_new_revision_is_new_artifact_not_overwrite() -> None:
    adapter, _ = _adapter(_FixtureTransport(_snapshot(_nfp())))
    ingest = ExternalSourceIngest(adapter)
    first = ingest.fetch_and_intake(
        SourceRequest(source=CALENDAR_FEED_SOURCE, bounds=_bounds(revision="r1")),
        writer=_writer(),
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_ok(first)
    assert first.value[0].outcome is IntakeOutcome.PRODUCED
    fp1 = first.value[0].observation.fingerprint.value

    # Same (source, id, revision) → idempotent; prior evidence untouched.
    same = adapter.fetch(SourceRequest(source=CALENDAR_FEED_SOURCE, bounds=_bounds(revision="r1")))
    assert is_ok(same)
    idem = ingest.intake(
        same.value[0],
        writer=_writer(),
        sequence=1,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_ok(idem)
    assert idem.value.outcome is IntakeOutcome.IDEMPOTENT
    assert idem.value.observation.fingerprint.value == fp1

    # New revision under the same provider-native id → new artifact.
    revised_fetch = adapter.fetch(
        SourceRequest(source=CALENDAR_FEED_SOURCE, bounds=_bounds(revision="r2"))
    )
    assert is_ok(revised_fetch)
    produced = ingest.intake(
        revised_fetch.value[0],
        writer=_writer(),
        sequence=2,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_ok(produced)
    assert produced.value.outcome is IntakeOutcome.PRODUCED
    assert produced.value.observation.fingerprint.value != fp1
    assert ingest.known_key(IntakeKey(CALENDAR_FEED_SOURCE, "nfp-2024-08-20", "r1"))
    assert ingest.known_key(IntakeKey(CALENDAR_FEED_SOURCE, "nfp-2024-08-20", "r2"))


def test_fetch_and_intake_converts_to_ct10(tmp_path: Path) -> None:
    adapter, _ = _adapter()
    ingest = ExternalSourceIngest(adapter)
    result = ingest.fetch_and_intake(
        SourceRequest(source=CALENDAR_FEED_SOURCE, bounds=_bounds()),
        writer=_writer(),
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_ok(result)
    receipt = result.value[0]
    obs = receipt.observation
    assert obs.source == CALENDAR_FEED_SOURCE
    assert obs.source_native_id == "nfp-2024-08-20"
    assert obs.revision == "r1"
    assert obs.event_time.value_ns > 0
    assert obs.known_at.value_ns == _KNOWN_NS
    boundary = SourceObservationBoundary(EvidenceStore(tmp_path / "store"))
    admitted = ingest.submit(obs, boundary)
    assert is_ok(admitted)


# --- AC2: verbatim impact, no window/permission, no minted severity ---------


def test_impact_labels_stored_verbatim_no_severity_scale() -> None:
    decoded = decode_calendar_snapshot(
        _snapshot(
            _nfp(),
            {"title": "Speaks", "country": "GBP", "date": "2024-08-20T12:00:00Z", "impact": "Low"},
        ),
        known_at_ns=_KNOWN_NS,
    )
    assert is_ok(decoded)
    assert [e.impact_label for e in decoded.value] == ["High", "Low"]
    adapter, _ = _adapter()
    refused = adapter.mint_severity_scale()
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["signal"] == "refuse-minted-severity"
    helper = refuse_minted_severity_scale(request="map-to-window")
    assert helper.context["signal"] == "refuse-minted-severity"


def test_feed_defines_no_window_and_holds_no_permission(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "store")
    adapter, _ = _adapter()
    ingest = ExternalSourceIngest(adapter)
    importer = CalendarFeedImport(adapter, ingest, _dq_writer(store))
    result = importer.run(
        SourceRequest(source=CALENDAR_FEED_SOURCE, bounds=_bounds()),
        writer=_writer(),
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
        journal_instant=_JOURNAL_NS,
    )
    assert is_ok(result)
    assert isinstance(result.value, CalendarImportReceipt)
    payload = result.value.journal_receipt.event.payload
    assert payload["defines_window"] is False
    assert payload["holds_permission"] is False
    assert result.value.events[0].impact_label == "High"


# --- AC3: every import journaled as data quality ----------------------------


def test_import_journaled_as_ct13_data_quality(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "store")
    adapter, _ = _adapter(_FixtureTransport(_snapshot(_nfp(), _cpi())))
    ingest = ExternalSourceIngest(adapter)
    jw = _dq_writer(store)
    importer = CalendarFeedImport(adapter, ingest, jw)
    result = importer.run(
        SourceRequest(source=CALENDAR_FEED_SOURCE, bounds=_bounds()),
        writer=_writer(),
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
        journal_instant=_JOURNAL_NS,
    )
    assert is_ok(result)
    receipt = result.value
    assert isinstance(receipt, CalendarImportReceipt)
    assert receipt.journal_receipt.event.event_type is JournalEventType.DATA_QUALITY
    assert receipt.journal_receipt.event.payload["signal"] == "calendar-import"
    assert receipt.journal_receipt.event.payload["event_count"] == 2
    assert receipt.legal_archiving_posture == LEGAL_ARCHIVING_POSTURE

    world = store.for_world(World.LIVE)
    assert is_ok(world)
    read = JournalReader(world.value.journal).read("dq", for_world=World.LIVE)
    assert is_ok(read)
    assert len(read.value) == 1
    assert read.value[0].event_type is JournalEventType.DATA_QUALITY


# --- AC4: fail-closed degradation -------------------------------------------


def test_failed_refresh_fail_closed_and_journaled(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "store")
    transport = _FixtureTransport()
    transport.fail_unavailable()
    adapter, _ = _adapter(transport)
    ingest = ExternalSourceIngest(adapter)
    importer = CalendarFeedImport(adapter, ingest, _dq_writer(store))
    result = importer.run(
        SourceRequest(source=CALENDAR_FEED_SOURCE, bounds=_bounds()),
        writer=_writer(),
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
        journal_instant=_JOURNAL_NS,
    )
    assert is_ok(result)
    signal = result.value
    assert isinstance(signal, FailClosedSignal)
    assert signal.reason is FailClosedReason.FAILED_REFRESH
    assert signal.treated_as_affected is True
    assert signal.alarm is True
    assert ingest.known_key(IntakeKey(CALENDAR_FEED_SOURCE, "nfp-2024-08-20", "r1")) is False

    world = store.for_world(World.LIVE)
    assert is_ok(world)
    read = JournalReader(world.value.journal).read("dq", for_world=World.LIVE)
    assert is_ok(read)
    assert read.value[0].payload["signal"] == "calendar-fail-closed"
    assert read.value[0].payload["reason"] == "failed-refresh"
    assert read.value[0].payload["alarm"] is True


def test_unknown_coverage_fail_closed(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "store")
    adapter, _ = _adapter()
    ingest = ExternalSourceIngest(adapter)
    importer = CalendarFeedImport(adapter, ingest, _dq_writer(store))
    result = importer.run(
        SourceRequest(source=CALENDAR_FEED_SOURCE, bounds=_bounds()),
        writer=_writer(),
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
        journal_instant=_JOURNAL_NS,
        coverage_known=False,
    )
    assert is_ok(result)
    assert isinstance(result.value, FailClosedSignal)
    assert result.value.reason is FailClosedReason.UNKNOWN_COVERAGE


def test_missing_currency_exposure_fail_closed(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "store")
    adapter, _ = _adapter()
    ingest = ExternalSourceIngest(adapter)
    # Only EUR known; USD required → fail closed before fetch emits permission.
    importer = CalendarFeedImport(
        adapter, ingest, _dq_writer(store), currency_exposures={"EUR": {"pairs": ["EURUSD"]}}
    )
    result = importer.run(
        SourceRequest(source=CALENDAR_FEED_SOURCE, bounds=_bounds()),
        writer=_writer(),
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
        journal_instant=_JOURNAL_NS,
        require_exposures_for=["USD"],
    )
    assert is_ok(result)
    assert isinstance(result.value, FailClosedSignal)
    assert result.value.reason is FailClosedReason.MISSING_CURRENCY_EXPOSURE
    assert result.value.detail["currency"] == "USD"


def test_no_live_skip_button() -> None:
    adapter, _ = _adapter()
    refused = adapter.live_skip()
    assert is_refusal(refused)
    assert refused.context["signal"] == "refuse-live-skip"
    helper = refuse_live_skip(request="operator-click")
    assert helper.category is RefusalCategory.POLICY_REJECTION
    assert helper.context["treated_as_affected"] is True


def test_fail_closed_helper_builds_signal() -> None:
    built = fail_closed(FailClosedReason.FAILED_REFRESH, detail={"http": 503})
    assert is_ok(built)
    assert built.value.treated_as_affected is True
    payload = built.value.to_payload()
    assert payload["alarm"] is True
    assert payload["http"] == 503


# --- AC5: legal archiving open operator item --------------------------------


def test_retention_not_claimed_authorized() -> None:
    adapter, _ = _adapter()
    refused = adapter.claim_retention_authorized()
    assert is_refusal(refused)
    assert refused.context["signal"] == "refuse-authorized-retention"
    assert refused.context["legal_archiving_posture"] == LEGAL_ARCHIVING_POSTURE
    helper = refuse_authorized_retention_claim()
    assert helper.category is RefusalCategory.POLICY_REJECTION


def test_import_receipt_records_open_posture(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "store")
    adapter, _ = _adapter()
    ingest = ExternalSourceIngest(adapter)
    importer = CalendarFeedImport(adapter, ingest, _dq_writer(store))
    assert importer.legal_archiving_posture == LEGAL_ARCHIVING_POSTURE
    result = importer.run(
        SourceRequest(source=CALENDAR_FEED_SOURCE, bounds=_bounds()),
        writer=_writer(),
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
        journal_instant=_JOURNAL_NS,
    )
    assert is_ok(result)
    assert isinstance(result.value, CalendarImportReceipt)
    assert result.value.legal_archiving_posture == "open-operator-item"
    assert result.value.journal_receipt.event.payload["legal_archiving_posture"] == (
        LEGAL_ARCHIVING_POSTURE
    )


# --- decode / malformed -----------------------------------------------------


def test_malformed_snapshot_is_invalid_input() -> None:
    refused = decode_calendar_snapshot(b"not-json", known_at_ns=_KNOWN_NS)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_missing_impact_is_invalid_input() -> None:
    refused = decode_calendar_snapshot(
        _snapshot({"title": "X", "country": "USD", "date": "2024-08-20T12:00:00Z"}),
        known_at_ns=_KNOWN_NS,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "impact"


def test_naive_date_refused() -> None:
    refused = decode_calendar_snapshot(
        _snapshot(
            {
                "title": "X",
                "country": "USD",
                "date": "2024-08-20T12:00:00",
                "impact": "High",
            }
        ),
        known_at_ns=_KNOWN_NS,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "date"


def test_wrong_source_refused() -> None:
    adapter, _ = _adapter()
    refused = adapter.fetch(SourceRequest(source="dukascopy", bounds=_bounds()))
    assert is_refusal(refused)
    assert refused.context["field"] == "source"


def test_calendar_event_value_type() -> None:
    event = CalendarEvent(
        source=CALENDAR_FEED_SOURCE,
        source_native_id="e1",
        revision="r1",
        event_time_ns=_EVENT_NS,
        known_at_ns=_KNOWN_NS,
        impact_label="High",
        currency="USD",
        title="NFP",
    )
    assert event.format_version == 1
    assert event.impact_label == "High"
