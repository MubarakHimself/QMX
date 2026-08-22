"""Reference usage — CT-15 external-source ingest seam (COMP-QMF-DATA-INGEST).

Executable::

    python packages/qmf-data/examples/ingest_usage.py

Shows the six things Story 6.1 pins down:

1. Data-Ingest owns the CT-15 port call; provider responses normalize into CT-10
   producer values that the application routes to SourceObservationBoundary (AC1).
2. Intake is idempotent on (source, source-native id, revision); a new revision is
   a distinct fp1 artifact, never a collision or overwrite (AC2).
3. Foreign timestamps and foreign money ride through verbatim at their declared
   zone/scale (AC3).
4. Missing event-time / known-at / source / revision / CT-03 instrument mapping is
   an invalid-input refusal — no observation is emitted (AC4).
5. A rate-limited or unavailable provider returns a typed refusal and fabricates
   nothing; a read-only source is never a VenueId (AC5).
6. Asking the seam to own a scheduler / daemon / retry loop is a policy rejection
   (AC6).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

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
)
from qmf.data.ingest import refuse_schedule_ownership

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


def _writer() -> WriterId:
    return _unwrap(WriterId.try_create("node-a", "ingest", "dukascopy", "boot-1"), "writer")


def _instrument() -> Instrument:
    venue = _unwrap(VenueId.try_create("broker-a"), "venue")
    return _unwrap(Instrument.try_create(venue, "EURUSD"), "instrument")


class _DemoPort:
    """Stand-in CT-15 provider — real adapters ship in later stories."""

    def __init__(self) -> None:
        self._mode = "ok"

    def fail_rate_limit(self) -> None:
        self._mode = "rate-limit"

    def restore(self) -> None:
        self._mode = "ok"

    def fetch(self, request: SourceRequest, /) -> Result[tuple[ProviderRecord, ...]]:
        del request
        if self._mode == "rate-limit":
            return TypedRefusal(
                category=RefusalCategory.TRANSIENT_VENUE_FAILURE,
                retryability=Retryability.AFTER_CONDITION,
                context={"signal": "rate-limit", "source": "dukascopy"},
                after_condition_descriptor="retry_after_ms=200",
            )
        ts = _unwrap(
            ForeignTimestamp.try_create(
                "2026-08-21T12:00:00.123", "Europe/Zurich", "+02:00", "milliseconds"
            ),
            "foreign timestamp",
        )
        money = _unwrap(ForeignMoney.try_create(110250, 5), "foreign money")
        return Ok(
            (
                ProviderRecord(
                    source="dukascopy",
                    source_native_id="EURUSD#42",
                    revision="r1",
                    event_time=_EVENT_NS,
                    known_at=_KNOWN_NS,
                    instrument=_instrument(),
                    foreign_timestamp=ts,
                    foreign_money=money,
                ),
            )
        )


def fetch_normalize_and_route(
    ingest: ExternalSourceIngest, boundary: SourceObservationBoundary
) -> str:
    """AC1: call CT-15, normalize to CT-10, application-route into the boundary."""
    receipts = _unwrap(
        ingest.fetch_and_intake(
            SourceRequest(source="dukascopy", bounds={"window": "bounded"}),
            writer=_writer(),
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS,
        ),
        "fetch_and_intake",
    )
    _require(len(receipts) == 1, "one provider record")
    admitted = _unwrap(ingest.submit(receipts[0].observation, boundary), "submit")
    return admitted.observation_fingerprint.value


def idempotent_and_revision(ingest: ExternalSourceIngest) -> tuple[str, str]:
    """AC2: same key is idempotent; a new revision is a distinct fp1."""
    first = _unwrap(
        ingest.intake(
            ProviderRecord(
                source="dukascopy",
                source_native_id="EURUSD#42",
                revision="r1",
                event_time=_EVENT_NS,
                known_at=_KNOWN_NS,
                instrument=_instrument(),
            ),
            writer=_writer(),
            sequence=0,
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS,
        ),
        "first intake",
    )
    _require(first.outcome is IntakeOutcome.IDEMPOTENT, "re-fetch of r1 is idempotent")
    second = _unwrap(
        ingest.intake(
            ProviderRecord(
                source="dukascopy",
                source_native_id="EURUSD#42",
                revision="r2",
                event_time=_EVENT_NS,
                known_at=_KNOWN_NS + 1_000_000,
                instrument=_instrument(),
                correction_of=first.observation.fingerprint,
            ),
            writer=_writer(),
            sequence=1,
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS + 1_000_000,
        ),
        "revision intake",
    )
    _require(second.outcome is IntakeOutcome.PRODUCED, "r2 produced")
    _require(
        second.observation.fingerprint.value != first.observation.fingerprint.value,
        "revision has its own fp1",
    )
    return first.observation.fingerprint.value, second.observation.fingerprint.value


def verbatim_foreign(ingest: ExternalSourceIngest) -> None:
    """AC3: foreign timestamp/money survive at declared zone and scale."""
    ts = _unwrap(
        ForeignTimestamp.try_create("2026-08-21T12:00:00.123", "UTC", "+00:00", "ms"),
        "ts",
    )
    money = _unwrap(ForeignMoney.try_create(42, 3), "money")
    receipt = _unwrap(
        ingest.intake(
            ProviderRecord(
                source="dukascopy",
                source_native_id="EURUSD#99",
                revision="r1",
                event_time=_EVENT_NS,
                known_at=_KNOWN_NS,
                instrument=_instrument(),
                foreign_timestamp=ts,
                foreign_money=money,
            ),
            writer=_writer(),
            sequence=2,
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS,
        ),
        "verbatim intake",
    )
    obs = receipt.observation
    _require(obs.foreign_timestamp is not None, "foreign timestamp present")
    _require(
        obs.foreign_timestamp is not None
        and obs.foreign_timestamp.verbatim == "2026-08-21T12:00:00.123",
        "verbatim timestamp",
    )
    _require(
        obs.foreign_money is not None
        and obs.foreign_money.verbatim == 42
        and obs.foreign_money.scale == 3,
        "verbatim money at source scale",
    )


def incomplete_is_refused(ingest: ExternalSourceIngest) -> str:
    """AC4: missing known-at / instrument mapping never emits a CT-10 value."""
    refused = ingest.intake(
        ProviderRecord(
            source="dukascopy",
            source_native_id="EURUSD#7",
            revision="r1",
            event_time=_EVENT_NS,
            known_at=None,
            instrument=_instrument(),
        ),
        writer=_writer(),
        sequence=3,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    _require(is_refusal(refused), "missing known-at refused")
    no_instrument = ingest.intake(
        ProviderRecord(
            source="dukascopy",
            source_native_id="EURUSD#8",
            revision="r1",
            event_time=_EVENT_NS,
            known_at=_KNOWN_NS,
            instrument=None,
        ),
        writer=_writer(),
        sequence=3,
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    _require(is_refusal(no_instrument), "missing instrument refused")
    return refused.category.value if is_refusal(refused) else "unexpected-ok"


def provider_failure_fabricates_nothing(ingest: ExternalSourceIngest, port: _DemoPort) -> str:
    """AC5: rate-limit refusal; no fabricated observation."""
    port.fail_rate_limit()
    refused = ingest.fetch_and_intake(
        SourceRequest(source="dukascopy"),
        writer=_writer(),
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    port.restore()
    _require(is_refusal(refused), "rate-limit refused")
    _require(
        is_refusal(refused) and refused.category is RefusalCategory.TRANSIENT_VENUE_FAILURE,
        "transient venue failure",
    )
    return refused.category.value if is_refusal(refused) else "unexpected-ok"


def schedule_ask_is_refused(ingest: ExternalSourceIngest) -> str:
    """AC6: scheduler / daemon / retry loop are out of authority."""
    free = refuse_schedule_ownership(request="install-cron")
    method = ingest.start_scheduler()
    _require(is_refusal(free) and is_refusal(method), "schedule asks refused")
    return free.category.value if is_refusal(free) else "unexpected-ok"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="qmf-ct15-usage-") as tmp:
        port = _DemoPort()
        ingest = ExternalSourceIngest(port)
        boundary = SourceObservationBoundary(EvidenceStore(Path(tmp)))

        fp = fetch_normalize_and_route(ingest, boundary)
        print(f"CT-15 → CT-10 routed: {fp[:24]}...")

        original_fp, revision_fp = idempotent_and_revision(ingest)
        _require(original_fp != revision_fp, "revision distinct")
        print("idempotent key; revision is a new fp1 artifact")

        verbatim_foreign(ingest)
        print("foreign timestamp and money: stored verbatim")

        refusal = incomplete_is_refused(ingest)
        print(f"incomplete / unmapped instrument: {refusal}")

        rate = provider_failure_fabricates_nothing(ingest, port)
        print(f"rate-limit: {rate}; no fabricated observation")

        schedule = schedule_ask_is_refused(ingest)
        print(f"scheduler/daemon ask: {schedule} (called port only)")


if __name__ == "__main__":
    main()
