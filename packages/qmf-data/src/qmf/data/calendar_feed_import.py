"""Journalled news-calendar import: fetch → intake → CT-13 data-quality event."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from qmf.core import Ok, Result, TypedRefusal, World, WriterId, is_refusal
from qmf.data.calendar_feed_adapter import CalendarFeedAdapter
from qmf.data.calendar_feed_types import (
    CALENDAR_FEED_SOURCE,
    CONTRACT_FORMAT_VERSION,
    LEGAL_ARCHIVING_POSTURE,
    CalendarEvent,
    CalendarImportReceipt,
    FailClosedReason,
    FailClosedSignal,
    fail_closed,
)
from qmf.data.ingest import ExternalSourceIngest, IntakeOutcome, IntakeReceipt, SourceRequest
from qmf.data.journal_producer import JournalAppendReceipt, JournalWriter
from qmf.data.source_boundary import ObservationReceipt, SourceObservationBoundary


def journal_import(
    writer: JournalWriter,
    *,
    instant: object,
    events: Sequence[CalendarEvent],
    intake_receipts: Sequence[IntakeReceipt] | None = None,
    extra: Mapping[str, object] | None = None,
) -> Result[JournalAppendReceipt]:
    """Journal one news-calendar import as a CT-13 ``data quality`` event (AC3)."""
    produced = 0
    idempotent = 0
    if intake_receipts is not None:
        for receipt in intake_receipts:
            if receipt.outcome is IntakeOutcome.PRODUCED:
                produced += 1
            else:
                idempotent += 1
    payload: dict[str, object] = {
        "signal": "calendar-import",
        "source": CALENDAR_FEED_SOURCE,
        "component": "COMP-CALENDAR-FEED",
        "contract": "CT-15",
        "event_type_wire": "data quality",
        "event_count": len(events),
        "produced_count": produced,
        "idempotent_count": idempotent,
        "impact_labels": [event.impact_label for event in events],
        "currencies": sorted({event.currency for event in events}),
        "legal_archiving_posture": LEGAL_ARCHIVING_POSTURE,
        "defines_window": False,
        "holds_permission": False,
        "format_version": CONTRACT_FORMAT_VERSION,
    }
    if extra is not None:
        payload.update(dict(extra))
    return writer.record_data_quality(payload, instant=instant)


def journal_fail_closed(
    writer: JournalWriter,
    signal: FailClosedSignal,
    *,
    instant: object,
) -> Result[JournalAppendReceipt]:
    """Journal a fail-closed degradation as a CT-13 ``data quality`` event (AC4)."""
    return writer.record_data_quality(signal.to_payload(), instant=instant)


class CalendarFeedImport:
    """Standalone-recorder-facing import: fetch → intake → journal (AC1–AC5).

    Scheduling stays outside this class — the application drives each call. On
    transport failure / unknown coverage / missing currency-exposure the import
    journals a fail-closed data-quality event and returns the signal; it never
    fabricates permission to trade.
    """

    def __init__(
        self,
        adapter: CalendarFeedAdapter,
        ingest: ExternalSourceIngest,
        journal: JournalWriter,
        *,
        currency_exposures: Mapping[str, object] | None = None,
    ) -> None:
        self._adapter = adapter
        self._ingest = ingest
        self._journal = journal
        # Presence of a key means exposure is known; absence → fail closed.
        self._exposures = {
            code.strip().upper(): value for code, value in (currency_exposures or {}).items()
        }

    @property
    def legal_archiving_posture(self) -> str:
        return LEGAL_ARCHIVING_POSTURE

    def run(
        self,
        request: SourceRequest,
        *,
        writer: WriterId,
        world: World,
        receive_wall_time: object,
        journal_instant: object,
        sequence_start: int = 0,
        boundary: SourceObservationBoundary | None = None,
        require_exposures_for: Sequence[str] | None = None,
        coverage_known: bool = True,
    ) -> Result[CalendarImportReceipt | FailClosedSignal]:
        """Run one import; on degradation return a journaled fail-closed signal.

        Success yields :class:`CalendarImportReceipt` (import journaled). Failure
        modes journal a ``data quality`` fail-closed event and return the
        :class:`FailClosedSignal` (still ``Ok`` wrapping the signal so the caller
        can alarm without mistaking it for permission).
        """
        closed = self._fail_closed_preflight(journal_instant, coverage_known, require_exposures_for)
        if is_refusal(closed):
            return closed
        if closed.value is not None:
            outcome: CalendarImportReceipt | FailClosedSignal = closed.value
            return Ok(outcome)
        return self._intake_and_journal(
            request,
            writer=writer,
            world=world,
            receive_wall_time=receive_wall_time,
            journal_instant=journal_instant,
            sequence_start=sequence_start,
            boundary=boundary,
        )

    def _intake_and_journal(
        self,
        request: SourceRequest,
        *,
        writer: WriterId,
        world: World,
        receive_wall_time: object,
        journal_instant: object,
        sequence_start: int,
        boundary: SourceObservationBoundary | None,
    ) -> Result[CalendarImportReceipt | FailClosedSignal]:
        fetched = self._ingest.fetch_and_intake(
            request,
            writer=writer,
            world=world,
            receive_wall_time=receive_wall_time,
            sequence_start=sequence_start,
        )
        if is_refusal(fetched):
            failed = self._journal_failed_refresh(fetched, journal_instant)
            if is_refusal(failed):
                return failed
            outcome: CalendarImportReceipt | FailClosedSignal = failed.value
            return Ok(outcome)
        events = self._adapter.last_events
        intake_receipts = fetched.value
        admitted = self._admit_produced(intake_receipts, boundary)
        if is_refusal(admitted):
            return admitted
        journaled = journal_import(
            self._journal,
            instant=journal_instant,
            events=events,
            intake_receipts=intake_receipts,
        )
        if is_refusal(journaled):
            return journaled
        return Ok(
            CalendarImportReceipt(
                events=events,
                intake_receipts=intake_receipts,
                journal_receipt=journaled.value,
            )
        )

    def _journal_signal(
        self, signal: FailClosedSignal, journal_instant: object
    ) -> Result[FailClosedSignal]:
        journaled = journal_fail_closed(self._journal, signal, instant=journal_instant)
        if is_refusal(journaled):
            return journaled
        return Ok(signal)

    def _fail_closed_preflight(
        self,
        journal_instant: object,
        coverage_known: bool,
        require_exposures_for: Sequence[str] | None,
    ) -> Result[FailClosedSignal | None]:
        if not coverage_known:
            return self._journal_unknown_coverage(journal_instant)
        if require_exposures_for is None:
            return Ok(None)
        return self._missing_exposure_signal(journal_instant, require_exposures_for)

    def _journal_unknown_coverage(self, journal_instant: object) -> Result[FailClosedSignal | None]:
        signal_result = fail_closed(
            FailClosedReason.UNKNOWN_COVERAGE,
            detail={"coverage_known": False},
        )
        if is_refusal(signal_result):
            return signal_result
        journaled = self._journal_signal(signal_result.value, journal_instant)
        if is_refusal(journaled):
            return journaled
        wrapped: FailClosedSignal | None = journaled.value
        return Ok(wrapped)

    def _missing_exposure_signal(
        self,
        journal_instant: object,
        require_exposures_for: Sequence[str],
    ) -> Result[FailClosedSignal | None]:
        for code in require_exposures_for:
            token = code.strip().upper()
            if token not in self._exposures:
                signal_result = fail_closed(
                    FailClosedReason.MISSING_CURRENCY_EXPOSURE,
                    detail={"currency": token, "instrument_scope": "unknown"},
                )
                if is_refusal(signal_result):
                    return signal_result
                journaled = self._journal_signal(signal_result.value, journal_instant)
                if is_refusal(journaled):
                    return journaled
                wrapped: FailClosedSignal | None = journaled.value
                return Ok(wrapped)
        return Ok(None)

    def _journal_failed_refresh(
        self, fetched: TypedRefusal, journal_instant: object
    ) -> Result[FailClosedSignal]:
        detail: dict[str, object] = {
            "refusal_category": fetched.category.value,
            "retryability": fetched.retryability.value,
            "provider_context": dict(fetched.context),
        }
        signal_result = fail_closed(FailClosedReason.FAILED_REFRESH, detail=detail)
        if is_refusal(signal_result):
            return signal_result
        return self._journal_signal(signal_result.value, journal_instant)

    def _admit_produced(
        self,
        intake_receipts: Sequence[IntakeReceipt],
        boundary: SourceObservationBoundary | None,
    ) -> Result[None]:
        if boundary is None:
            return Ok(None)
        for receipt in intake_receipts:
            if receipt.outcome is IntakeOutcome.PRODUCED:
                admitted: Result[ObservationReceipt] = self._ingest.submit(
                    receipt.observation, boundary
                )
                if is_refusal(admitted):
                    return admitted
        return Ok(None)
