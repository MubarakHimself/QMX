"""Reference usage — news-calendar feed as a governed CT-15 source (COMP-CALENDAR-FEED).

Executable::

    python packages/qmf-data/examples/calendar_feed_usage.py

Shows the five things Story 6.4 pins down:

1. Provider-native ``(source, id, revision)`` intake; a new revision is a new
   artifact and never overwrites prior evidence (AC1).
2. Impact labels stored verbatim; the feed defines no window and holds no
   permission; QMX mints no severity scale (AC2).
3. Every import is journaled as a CT-13 ``data quality`` event (AC3).
4. Failed refresh / unknown coverage / missing currency-exposure fail closed,
   journaled and alarmed, treated-as-affected — no live skip (AC4).
5. Legal archiving posture stays an open operator item — never claimed
   authorized (AC5).
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar

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
    CalendarFeedAdapter,
    CalendarFeedImport,
    CalendarImportReceipt,
    EvidenceStore,
    ExternalSourceIngest,
    FailClosedReason,
    FailClosedSignal,
    IntakeOutcome,
    JournalWriter,
    SourceRequest,
    refuse_authorized_retention_claim,
    refuse_live_skip,
    refuse_minted_severity_scale,
)

T = TypeVar("T")

_KNOWN_NS = 1_724_143_800_000_000_000
_RECEIVE_NS = _KNOWN_NS + 1_000_000
_JOURNAL_NS = _RECEIVE_NS + 1_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def _require(condition: object, what: str) -> None:
    if not condition:
        raise AssertionError(f"expected {what}")


def _writer(stream: str = "calendar") -> WriterId:
    return _unwrap(WriterId.try_create("node-a", "recorder", stream, "boot-1"), "writer")


def _snapshot() -> bytes:
    return json.dumps(
        [
            {
                "id": "nfp-2024-08-20",
                "title": "Non-Farm Payrolls",
                "country": "USD",
                "date": "2024-08-20T14:30:00+00:00",
                "impact": "High",
            },
            {
                "id": "cpi-eur-2024-08-20",
                "title": "CPI y/y",
                "country": "EUR",
                "date": "2024-08-20T09:00:00+00:00",
                "impact": "Medium",
            },
        ]
    ).encode("utf-8")


class _DemoTransport:
    """Fixture transport — production injects the standalone recorder / HTTPS."""

    def __init__(self, body: bytes | None = None) -> None:
        self.body = body if body is not None else _snapshot()
        self.mode = "ok"

    def fail(self) -> None:
        self.mode = "unavailable"

    def fetch_snapshot(self, bounds: Mapping[str, object], /) -> Result[bytes]:
        del bounds
        if self.mode == "unavailable":
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.YES,
                context={"signal": "source-unavailable", "source": CALENDAR_FEED_SOURCE},
            )
        return Ok(self.body)


def main() -> None:
    transport = _DemoTransport()
    adapter = CalendarFeedAdapter(transport)
    ingest = ExternalSourceIngest(adapter)
    bounds = {"known_at_ns": _KNOWN_NS, "revision": "r1"}
    request = SourceRequest(source=CALENDAR_FEED_SOURCE, bounds=bounds)

    # AC1 — provider-native identity through CT-15 → CT-10; revision is a new artifact.
    receipts = _unwrap(
        ingest.fetch_and_intake(
            request,
            writer=_writer(),
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS,
        ),
        "fetch_and_intake",
    )
    _require(len(receipts) == 2, "two calendar events")
    first = receipts[0]
    _require(first.outcome is IntakeOutcome.PRODUCED, "first intake produced")
    _require(first.observation.source == CALENDAR_FEED_SOURCE, "source news-calendar")
    _require(first.observation.source_native_id == "nfp-2024-08-20", "provider-native id")
    events = adapter.last_events
    print(
        f"governed CT-10: source={first.observation.source} "
        f"events={len(receipts)} ids={[e.source_native_id for e in events]}"
    )

    # Same revision → idempotent.
    same = _unwrap(
        ingest.fetch_and_intake(
            request,
            writer=_writer(),
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS,
            sequence_start=10,
        ),
        "idempotent re-intake",
    )
    _require(same[0].outcome is IntakeOutcome.IDEMPOTENT, "duplicate key idempotent")

    # New revision → distinct fingerprint.
    rev = _unwrap(
        ingest.fetch_and_intake(
            SourceRequest(source=CALENDAR_FEED_SOURCE, bounds={**bounds, "revision": "r2"}),
            writer=_writer(),
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS,
            sequence_start=20,
        ),
        "revision r2",
    )
    _require(rev[0].outcome is IntakeOutcome.PRODUCED, "new revision produced")
    _require(
        rev[0].observation.fingerprint.value != first.observation.fingerprint.value,
        "revision mints new fp1",
    )
    print(
        f"revision append-only: r1={first.observation.fingerprint.value[-12:]} "
        f"r2={rev[0].observation.fingerprint.value[-12:]}"
    )

    # AC2 — verbatim impact; no window/permission; no minted severity.
    _require(events[0].impact_label == "High", "impact High verbatim")
    _require(events[1].impact_label == "Medium", "impact Medium verbatim")
    severity = refuse_minted_severity_scale(request="demo")
    _require(is_refusal(severity), "minted severity refused")
    print(
        f"verbatim impact labels: {[e.impact_label for e in events]} "
        f"(no QMX severity; feed defines no window)"
    )

    with tempfile.TemporaryDirectory() as tmp:
        store = EvidenceStore(Path(tmp) / "store")
        world = _unwrap(store.for_world(World.LIVE), "live world")
        jw = JournalWriter(world.journal, _writer("dq"), stream_name="dq")
        importer = CalendarFeedImport(
            adapter,
            ExternalSourceIngest(adapter),
            jw,
            currency_exposures={"USD": {"ok": True}, "EUR": {"ok": True}},
        )

        # AC3 — every import journaled as data quality.
        imported_raw = _unwrap(
            importer.run(
                request,
                writer=_writer(),
                world=World.LIVE,
                receive_wall_time=_RECEIVE_NS,
                journal_instant=_JOURNAL_NS,
            ),
            "journaled import",
        )
        if not isinstance(imported_raw, CalendarImportReceipt):
            raise AssertionError("expected import receipt")
        imported: CalendarImportReceipt = imported_raw
        _require(
            imported.journal_receipt.event.payload["signal"] == "calendar-import",
            "data-quality import signal",
        )
        print(
            f"import journaled as data quality: "
            f"events={imported.journal_receipt.event.payload['event_count']} "
            f"defines_window={imported.journal_receipt.event.payload['defines_window']}"
        )

        # AC4 — failed refresh fails closed, journaled, no live skip.
        transport.fail()
        closed_raw = _unwrap(
            importer.run(
                request,
                writer=_writer(),
                world=World.LIVE,
                receive_wall_time=_RECEIVE_NS,
                journal_instant=_JOURNAL_NS + 1,
            ),
            "fail-closed refresh",
        )
        if not isinstance(closed_raw, FailClosedSignal):
            raise AssertionError("expected fail-closed signal")
        closed: FailClosedSignal = closed_raw
        _require(closed.reason is FailClosedReason.FAILED_REFRESH, "failed-refresh")
        _require(closed.treated_as_affected and closed.alarm, "treated-as-affected+alarm")
        skip = refuse_live_skip(request="demo")
        _require(is_refusal(skip), "live skip refused")
        print(
            f"fail-closed degradation: reason={closed.reason.value} "
            f"treated_as_affected={closed.treated_as_affected} (no live skip)"
        )

        # AC5 — retention not claimed authorized.
        retention = refuse_authorized_retention_claim()
        _require(is_refusal(retention), "authorized retention refused")
        _require(
            importer.legal_archiving_posture == LEGAL_ARCHIVING_POSTURE,
            "open operator item",
        )
        print(f"legal archiving posture: {LEGAL_ARCHIVING_POSTURE} (not claimed authorized)")


if __name__ == "__main__":
    main()
