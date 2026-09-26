"""CT-15 fetch, idempotent ledger intake, hand-off, and schedule-refusal collaborators."""

from __future__ import annotations

from dataclasses import dataclass

from qmf.core import (
    Instrument,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)
from qmf.data.ingest_resolve import (
    resolve_instrument,
    resolve_optional_foreign_money,
    resolve_optional_foreign_timestamp,
    resolve_optional_tick_quote,
)
from qmf.data.ingest_types import (
    ExternalSourcePort,
    IntakeKey,
    IntakeOutcome,
    IntakeReceipt,
    ProviderRecord,
    SourceRequest,
    clean_str,
    invalid_field,
    refuse_schedule_ownership,
)
from qmf.data.observation import SourceObservation
from qmf.data.source_boundary import ObservationReceipt, SourceObservationBoundary
from qmf.data.ticks import TickObservation, TickQuote


class ExternalSourceIntake:
    """CT-15 fetch plus idempotent ledger intake. Owns the port and in-process ledger."""

    def __init__(self, port: ExternalSourcePort) -> None:
        self._port = port
        self._ledger: dict[IntakeKey, IntakeReceipt] = {}

    @property
    def port(self) -> ExternalSourcePort:
        return self._port

    def normalize(
        self,
        record: object,
        *,
        writer: object,
        sequence: object,
        world: object,
        receive_wall_time: object,
        receive_monotonic_diagnostic: object | None = None,
    ) -> Result[tuple[SourceObservation, IntakeKey, Instrument, TickQuote | None]]:
        if not isinstance(record, ProviderRecord):
            return invalid_field(
                "record",
                "a CT-15 provider response item is a ProviderRecord",
                given=repr(record),
            )
        key = IntakeKey.try_create(record.source, record.source_native_id, record.revision)
        if is_refusal(key):
            return key
        instrument = resolve_instrument(record.instrument)
        if is_refusal(instrument):
            return instrument
        foreign_ts = resolve_optional_foreign_timestamp(record.foreign_timestamp)
        if is_refusal(foreign_ts):
            return foreign_ts
        foreign_money = resolve_optional_foreign_money(record.foreign_money)
        if is_refusal(foreign_money):
            return foreign_money
        quote = resolve_optional_tick_quote(record)
        if is_refusal(quote):
            return quote
        built = SourceObservation.try_create(
            event_time=record.event_time,
            known_at=record.known_at,
            source=key.value.source,
            source_native_id=key.value.source_native_id,
            revision=key.value.revision,
            receive_wall_time=receive_wall_time,
            writer=writer,
            sequence=sequence,
            world=world,
            foreign_timestamp=foreign_ts.value,
            foreign_money=foreign_money.value,
            receive_monotonic_diagnostic=receive_monotonic_diagnostic,
            correction_of=record.correction_of,
        )
        if is_refusal(built):
            return built
        return Ok((built.value, key.value, instrument.value, quote.value))

    def intake(
        self,
        record: object,
        *,
        writer: object,
        sequence: object,
        world: object,
        receive_wall_time: object,
        receive_monotonic_diagnostic: object | None = None,
    ) -> Result[IntakeReceipt]:
        normalized = self.normalize(
            record,
            writer=writer,
            sequence=sequence,
            world=world,
            receive_wall_time=receive_wall_time,
            receive_monotonic_diagnostic=receive_monotonic_diagnostic,
        )
        if is_refusal(normalized):
            return normalized
        observation, key, instrument, quote = normalized.value
        prior = self._ledger.get(key)
        if prior is not None:
            return Ok(
                IntakeReceipt(
                    observation=prior.observation,
                    intake_key=key,
                    instrument=prior.instrument,
                    outcome=IntakeOutcome.IDEMPOTENT,
                    quote=prior.quote,
                    tick=prior.tick,
                )
            )
        tick = (
            TickObservation(observation=observation, quote=quote, instrument=instrument)
            if quote is not None
            else None
        )
        receipt = IntakeReceipt(
            observation=observation,
            intake_key=key,
            instrument=instrument,
            outcome=IntakeOutcome.PRODUCED,
            quote=quote,
            tick=tick,
        )
        self._ledger[key] = receipt
        return Ok(receipt)

    def fetch_and_intake(
        self,
        request: object,
        *,
        writer: object,
        world: object,
        receive_wall_time: object,
        sequence_start: int = 0,
        receive_monotonic_diagnostic: object | None = None,
    ) -> Result[tuple[IntakeReceipt, ...]]:
        if not isinstance(request, SourceRequest):
            return invalid_field(
                "request",
                "a CT-15 call carries a SourceRequest naming the provider and opaque bounds",
                given=repr(request),
            )
        if clean_str(request.source) is None:
            return invalid_field(
                "source",
                "a CT-15 request names a non-empty read-only source, never a VenueId",
                given=repr(request.source),
            )
        fetched = self._fetch_port(request)
        if is_refusal(fetched):
            return fetched
        return self._intake_fetched(
            fetched.value,
            writer=writer,
            world=world,
            receive_wall_time=receive_wall_time,
            sequence_start=sequence_start,
            receive_monotonic_diagnostic=receive_monotonic_diagnostic,
        )

    def _fetch_port(self, request: SourceRequest) -> Result[tuple[ProviderRecord, ...]]:
        try:
            fetched = self._port.fetch(request)
        except Exception as exc:  # R-007: returned, never raised across the ingest boundary
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.YES,
                context={
                    "field": "port",
                    "reason": (
                        "the injected CT-15 provider port raised instead of returning; a "
                        "boundary failure is returned as a typed refusal, never raised "
                        "across the ingest boundary, and no observation is minted "
                        "(R-007, CT-04, 6.1-AC5)"
                    ),
                    "source": repr(request.source),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
        if is_refusal(fetched):
            # Provider unavailable / rate-limited — surface as-is; emit nothing (AC5).
            return fetched
        return fetched

    def _intake_fetched(
        self,
        records: tuple[ProviderRecord, ...],
        *,
        writer: object,
        world: object,
        receive_wall_time: object,
        sequence_start: int,
        receive_monotonic_diagnostic: object | None,
    ) -> Result[tuple[IntakeReceipt, ...]]:
        receipts: list[IntakeReceipt] = []
        sequence = sequence_start
        for record in records:
            result = self.intake(
                record,
                writer=writer,
                sequence=sequence,
                world=world,
                receive_wall_time=receive_wall_time,
                receive_monotonic_diagnostic=receive_monotonic_diagnostic,
            )
            if is_refusal(result):
                return result
            receipts.append(result.value)
            if result.value.outcome is IntakeOutcome.PRODUCED:
                sequence += 1
        return Ok(tuple(receipts))

    def known_key(self, key: IntakeKey) -> bool:
        return key in self._ledger


class ExternalSourceHandoff:
    """Application-routed CT-10 boundary hand-off (AC1)."""

    def submit(
        self,
        observation: object,
        boundary: SourceObservationBoundary,
    ) -> Result[ObservationReceipt]:
        return boundary.admit(observation)


class ExternalSourceScheduleBoundary:
    """Scheduler/daemon/retry asks this seam never owns (AC6 / FM-5)."""

    def __init__(self) -> None:
        self._refuse = refuse_schedule_ownership

    def start_scheduler(self, *_args: object, **_kwargs: object) -> Result[IntakeReceipt]:
        return self._refuse(request="start_scheduler")

    def run_daemon(self, *_args: object, **_kwargs: object) -> Result[IntakeReceipt]:
        return self._refuse(request="run_daemon")

    def run_retry_loop(self, *_args: object, **_kwargs: object) -> Result[IntakeReceipt]:
        return self._refuse(request="run_retry_loop")


@dataclass(frozen=True, slots=True)
class ExternalSourceCollaborators:
    """Intake port plus submit and schedule-refusal boundaries."""

    intake: ExternalSourceIntake
    handoff: ExternalSourceHandoff
    schedule: ExternalSourceScheduleBoundary


def bind_external_source(port: ExternalSourcePort) -> ExternalSourceCollaborators:
    """Wire the CT-15 intake, hand-off, and schedule-refusal collaborators."""
    return ExternalSourceCollaborators(
        intake=ExternalSourceIntake(port),
        handoff=ExternalSourceHandoff(),
        schedule=ExternalSourceScheduleBoundary(),
    )
