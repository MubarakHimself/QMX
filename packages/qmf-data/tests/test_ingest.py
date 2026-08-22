"""Tier-1 tests for the CT-15 external-source ingest seam (Story 6.1)."""

from __future__ import annotations

from pathlib import Path

from qmf.core import (
    Instrument,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.data import (
    EvidenceStore,
    ExternalSourceIngest,
    ForeignMoney,
    ForeignTimestamp,
    IntakeOutcome,
    ProviderRecord,
    SourceObservationBoundary,
    SourceRequest,
    refuse_source_as_venue,
)
from qmf.data.ingest import CONTRACT_FORMAT_VERSION as CT15_FORMAT_VERSION
from qmf.data.ingest import IntakeKey, refuse_schedule_ownership
from qmf.data.observation import CONTRACT_FORMAT_VERSION as CT10_FORMAT_VERSION
from qmf.data.observation import SourceObservation

_EVENT_NS = 1_700_000_000_000_000_000
_KNOWN_NS = 1_700_000_001_000_000_000
_RECEIVE_NS = 1_700_000_002_000_000_000


def _writer() -> WriterId:
    built = WriterId.try_create("node-a", "ingest", "dukascopy", "boot-1")
    assert is_ok(built)
    return built.value


def _instrument() -> Instrument:
    venue = VenueId.try_create("broker-a")
    assert is_ok(venue)
    built = Instrument.try_create(venue.value, "EURUSD")
    assert is_ok(built)
    return built.value


def _record(**overrides: object) -> ProviderRecord:
    parts: dict[str, object] = {
        "source": "dukascopy",
        "source_native_id": "EURUSD#42",
        "revision": "r1",
        "event_time": _EVENT_NS,
        "known_at": _KNOWN_NS,
        "instrument": _instrument(),
    }
    parts.update(overrides)
    return ProviderRecord(**parts)  # type: ignore[arg-type]


class _StaticPort:
    """In-memory CT-15 provider returning a fixed response or refusal."""

    def __init__(
        self,
        response: Result[tuple[ProviderRecord, ...]] | None = None,
    ) -> None:
        self.response = response if response is not None else Ok(())
        self.calls: list[SourceRequest] = []

    def fetch(self, request: SourceRequest, /) -> Result[tuple[ProviderRecord, ...]]:
        self.calls.append(request)
        return self.response


def _ingest(
    response: Result[tuple[ProviderRecord, ...]] | None = None,
) -> tuple[ExternalSourceIngest, _StaticPort]:
    port = _StaticPort(response)
    return ExternalSourceIngest(port), port


# --- AC1: CT-15 call → CT-10 producer values, application-routed ------------


def test_ct15_format_version_is_minted() -> None:
    assert CT15_FORMAT_VERSION == 1
    assert CT10_FORMAT_VERSION == 1


def test_fetch_and_intake_calls_port_and_produces_ct10_values() -> None:
    ingest, port = _ingest(Ok((_record(),)))
    result = ingest.fetch_and_intake(
        SourceRequest(source="dukascopy", bounds={"from_ns": _EVENT_NS}),
        writer=_writer(),
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_ok(result)
    assert len(port.calls) == 1
    assert port.calls[0].source == "dukascopy"
    receipt = result.value[0]
    assert receipt.outcome is IntakeOutcome.PRODUCED
    assert isinstance(receipt.observation, SourceObservation)
    assert receipt.intake_key == IntakeKey("dukascopy", "EURUSD#42", "r1")
    assert receipt.instrument.symbol == "EURUSD"
    assert receipt.format_version == CT15_FORMAT_VERSION


def test_submit_routes_to_ct10_boundary(tmp_path: Path) -> None:
    ingest, _port = _ingest()
    intake = ingest.intake(
        _record(),
        writer=_writer(),
        sequence=0,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_ok(intake)
    boundary = SourceObservationBoundary(EvidenceStore(tmp_path / "store"))
    admitted = ingest.submit(intake.value.observation, boundary)
    assert is_ok(admitted)
    assert (
        admitted.value.observation_fingerprint.value == intake.value.observation.fingerprint.value
    )


# --- AC2: idempotent key; revision is a new fp1 artifact --------------------


def test_duplicate_intake_key_is_idempotent() -> None:
    ingest, _port = _ingest()
    first = ingest.intake(
        _record(),
        writer=_writer(),
        sequence=0,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    # Different receive time / sequence would otherwise mint a different fp1 —
    # the ledger must still return the first observation under the same key.
    second = ingest.intake(
        _record(),
        writer=_writer(),
        sequence=99,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS + 1_000_000,
    )
    assert is_ok(first)
    assert is_ok(second)
    assert second.value.outcome is IntakeOutcome.IDEMPOTENT
    assert second.value.observation.fingerprint.value == first.value.observation.fingerprint.value
    assert first.value.observation.sequence == 0


def test_new_revision_is_distinct_fp1_never_overwrite() -> None:
    ingest, _port = _ingest()
    original = ingest.intake(
        _record(revision="r1"),
        writer=_writer(),
        sequence=0,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_ok(original)
    correction = ingest.intake(
        _record(
            revision="r2",
            known_at=_KNOWN_NS + 1_000_000,
            correction_of=original.value.observation.fingerprint,
            foreign_money=ForeignMoney.try_create(110255, 5).value,  # type: ignore[union-attr]
        ),
        writer=_writer(),
        sequence=1,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS + 1_000_000,
    )
    assert is_ok(correction)
    assert correction.value.outcome is IntakeOutcome.PRODUCED
    assert (
        correction.value.observation.fingerprint.value
        != original.value.observation.fingerprint.value
    )
    assert correction.value.observation.is_correction is True
    assert original.value.observation.revision == "r1"
    assert correction.value.intake_key.revision == "r2"
    assert ingest.known_key(original.value.intake_key)
    assert ingest.known_key(correction.value.intake_key)


# --- AC3: foreign timestamp / money stored verbatim -------------------------


def test_foreign_evidence_stored_verbatim_at_declared_zone_and_scale() -> None:
    ts = ForeignTimestamp.try_create(
        "2026-08-21T12:00:00.123", "Europe/Zurich", "+02:00", "milliseconds"
    )
    money = ForeignMoney.try_create(110250, 5)
    assert is_ok(ts)
    assert is_ok(money)
    ingest, _port = _ingest()
    result = ingest.intake(
        _record(foreign_timestamp=ts.value, foreign_money=money.value),
        writer=_writer(),
        sequence=0,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_ok(result)
    obs = result.value.observation
    assert obs.foreign_timestamp is not None
    assert obs.foreign_timestamp.verbatim == "2026-08-21T12:00:00.123"
    assert obs.foreign_timestamp.zone == "Europe/Zurich"
    assert obs.foreign_timestamp.offset == "+02:00"
    assert obs.foreign_timestamp.resolution == "milliseconds"
    assert obs.foreign_money is not None
    assert obs.foreign_money.verbatim == 110250
    assert obs.foreign_money.scale == 5


def test_foreign_blocks_accepted_as_mappings() -> None:
    ingest, _port = _ingest()
    result = ingest.intake(
        _record(
            foreign_timestamp={
                "verbatim": "2026-08-21T12:00:00.123",
                "zone": "UTC",
                "offset": "+00:00",
                "resolution": "ms",
            },
            foreign_money={"verbatim": 99, "scale": 2},
        ),
        writer=_writer(),
        sequence=0,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_ok(result)
    assert result.value.observation.foreign_money is not None
    assert result.value.observation.foreign_money.verbatim == 99


# --- AC4: missing required fields / CT-03 mapping => invalid input ----------


def test_missing_known_at_is_invalid_input() -> None:
    ingest, _port = _ingest()
    refused = ingest.intake(
        _record(known_at=None),
        writer=_writer(),
        sequence=0,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "known_at"


def test_missing_event_time_is_invalid_input() -> None:
    ingest, _port = _ingest()
    refused = ingest.intake(
        _record(event_time=None),
        writer=_writer(),
        sequence=0,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "event_time"


def test_missing_source_is_invalid_input() -> None:
    ingest, _port = _ingest()
    refused = ingest.intake(
        _record(source=""),
        writer=_writer(),
        sequence=0,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "source"


def test_missing_revision_is_invalid_input() -> None:
    ingest, _port = _ingest()
    refused = ingest.intake(
        _record(revision=None),
        writer=_writer(),
        sequence=0,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "revision"


def test_missing_instrument_mapping_is_invalid_input() -> None:
    ingest, _port = _ingest()
    refused = ingest.intake(
        _record(instrument=None),
        writer=_writer(),
        sequence=0,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "instrument"


def test_instrument_mapping_from_venue_symbol_dict() -> None:
    ingest, _port = _ingest()
    result = ingest.intake(
        _record(instrument={"venue": "broker-a", "symbol": "GBPUSD"}),
        writer=_writer(),
        sequence=0,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_ok(result)
    assert result.value.instrument.symbol == "GBPUSD"
    assert result.value.instrument.venue.value == "broker-a"


# --- AC5: unavailable / rate-limit; source ≠ VenueId ------------------------


def test_rate_limit_is_transient_venue_failure_no_fabricated_observation() -> None:
    refusal = TypedRefusal(
        category=RefusalCategory.TRANSIENT_VENUE_FAILURE,
        retryability=Retryability.AFTER_CONDITION,
        context={"signal": "rate-limit", "source": "dukascopy"},
        after_condition_descriptor="retry_after_ms=200",
    )
    ingest, port = _ingest(refusal)
    result = ingest.fetch_and_intake(
        SourceRequest(source="dukascopy"),
        writer=_writer(),
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.TRANSIENT_VENUE_FAILURE
    assert len(port.calls) == 1
    assert ingest.known_key(IntakeKey("dukascopy", "EURUSD#42", "r1")) is False


def test_source_unavailable_is_unavailable_dependency() -> None:
    refusal = TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.YES,
        context={"signal": "source-unavailable", "source": "dukascopy"},
    )
    ingest, _port = _ingest(refusal)
    result = ingest.fetch_and_intake(
        SourceRequest(source="dukascopy"),
        writer=_writer(),
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_venue_id_as_source_is_refused() -> None:
    venue = VenueId.try_create("broker-a")
    assert is_ok(venue)
    ingest, _port = _ingest()
    refused = ingest.intake(
        _record(source=venue.value),
        writer=_writer(),
        sequence=0,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["signal"] == "refuse-source-as-venue"


def test_refuse_source_as_venue_helper() -> None:
    refused = refuse_source_as_venue(given="broker-a")
    assert refused.category is RefusalCategory.POLICY_REJECTION


# --- AC6: scheduler / daemon / retry loop out of authority ------------------


def test_schedule_ownership_is_policy_rejection() -> None:
    refused = refuse_schedule_ownership(request="install-cron")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["signal"] == "refuse-schedule-ownership"


def test_start_scheduler_run_daemon_retry_loop_refuse() -> None:
    ingest, _port = _ingest()
    for method in (ingest.start_scheduler, ingest.run_daemon, ingest.run_retry_loop):
        refused = method()
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert refused.context["signal"] == "refuse-schedule-ownership"


def test_malformed_request_is_invalid_input() -> None:
    ingest, _port = _ingest()
    refused = ingest.fetch_and_intake(
        {"source": "dukascopy"},
        writer=_writer(),
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "request"
