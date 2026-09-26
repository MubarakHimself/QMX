"""CT-15 — external-source adapter seam owned by COMP-QMF-DATA-INGEST (AC1–AC6).

The middleware door that **owns and calls** the CT-15 provider port, validates and
normalizes provider responses into CT-10 :class:`~qmf.data.observation.SourceObservation`
**producer values**, and applies idempotent intake keyed on
``(source, source-native id, revision)``. A provider revision is a **new** artifact with
its own ``fp1`` — never an fp1 collision and never an overwrite of earlier evidence
(DEC-0119, DEC-0108).

What this seam guarantees:

* **AC1** — COMP-QMF-DATA-INGEST is the QMF caller of CT-15; COMP-QMF-DATA does not
  accept CT-15 as a public inbound on the store. Normalized observations are
  **application-routed** to the Data-owned CT-10 boundary
  (:class:`~qmf.data.source_boundary.SourceObservationBoundary`); producing values
  adds no package edge beyond ``qmf-data``'s existing ``qmf-core`` dependency
  (DEC-0117, DEC-0119, DEC-0120).
* **AC2** — duplicate / out-of-order arrivals under the same intake key are idempotent;
  a new ``revision`` mints a distinct observation fingerprint.
* **AC3** — foreign timestamps and foreign money ride through verbatim (zone / offset /
  resolution and the source's scaled integer) via the CT-10 value types; this seam never
  converts or rescales them.
* **AC4 / FM-2 / FM-6** — missing event-time, known-at, source, source-native id,
  revision, or a CT-03 :class:`~qmf.core.Instrument` mapping is an ``invalid input``
  refusal; no CT-10 value is emitted.
* **AC5 / FM-1 / FM-7** — a provider that is down or rate-limits returns
  ``unavailable dependency`` or ``transient venue failure`` through the port; the seam
  fabricates no observation. A read-only ``source`` is never a tradeable
  :class:`~qmf.core.VenueId`.
* **AC6 / FM-5** — asking the seam to own a scheduler, daemon, process supervisor, or
  retry loop is a ``policy rejection``; the adapter is a called port, not a running
  downloader (DEC-0051, DEC-0119).

Stdlib + qmf-core + the CT-10 value / boundary types already in this package.

Field resolvers, intake collaborators, and public value types live in sibling modules;
this module keeps the public ingest primitive and re-exports the public types.
"""

from __future__ import annotations

from qmf.core import Instrument, Result
from qmf.data.ingest_intake import bind_external_source
from qmf.data.ingest_types import (
    CONTRACT_FORMAT_VERSION,
    ExternalSourcePort,
    IntakeKey,
    IntakeOutcome,
    IntakeReceipt,
    ProviderRecord,
    SourceRequest,
    refuse_schedule_ownership,
    refuse_source_as_venue,
)
from qmf.data.observation import SourceObservation
from qmf.data.source_boundary import ObservationReceipt, SourceObservationBoundary
from qmf.data.ticks import TickQuote

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "ExternalSourceIngest",
    "ExternalSourcePort",
    "IntakeKey",
    "IntakeOutcome",
    "IntakeReceipt",
    "ProviderRecord",
    "SourceRequest",
    "refuse_schedule_ownership",
    "refuse_source_as_venue",
]


class ExternalSourceIngest:
    """COMP-QMF-DATA-INGEST — owns CT-15 calls and CT-10 producer normalization.

    Constructed with an injected :class:`ExternalSourcePort`. Each successful
    :meth:`intake` / :meth:`fetch_and_intake` yields :class:`IntakeReceipt` values the
    application routes to :class:`SourceObservationBoundary` (or via :meth:`submit`).
    An in-process ledger keys prior intakes by :class:`IntakeKey` so a duplicate
    arrival is idempotent (AC2).
    """

    def __init__(self, port: ExternalSourcePort) -> None:
        self._collaborators = bind_external_source(port)

    @property
    def port(self) -> ExternalSourcePort:
        """The injected CT-15 provider port."""
        return self._collaborators.intake.port

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
        """Validate a provider record and mint a CT-10 :class:`SourceObservation` (AC1–AC4).

        Does not consult the idempotent ledger and does not persist — pure
        normalize. A missing bitemporal field, intake key part, or CT-03 instrument
        mapping is ``invalid input`` and emits no observation. When bid/ask are
        present they are preserved as a :class:`~qmf.data.ticks.TickQuote` (fourth
        tuple element); a presented mid is refused (Story 6.2).
        """
        return self._collaborators.intake.normalize(
            record,
            writer=writer,
            sequence=sequence,
            world=world,
            receive_wall_time=receive_wall_time,
            receive_monotonic_diagnostic=receive_monotonic_diagnostic,
        )

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
        """Normalize under the idempotent ``(source, native id, revision)`` key (AC2).

        A previously seen key returns the prior receipt with
        :attr:`IntakeOutcome.IDEMPOTENT` — earlier evidence is never erased or silently
        merged. A new revision is a new artifact with its own ``fp1``.
        """
        return self._collaborators.intake.intake(
            record,
            writer=writer,
            sequence=sequence,
            world=world,
            receive_wall_time=receive_wall_time,
            receive_monotonic_diagnostic=receive_monotonic_diagnostic,
        )

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
        """Call the CT-15 port once and intake every returned record (AC1, AC5).

        A port refusal (rate-limit / unavailable) propagates unchanged — no fabricated
        observation is minted. ``sequence_start`` is the per-writer sequence of the first
        produced record; subsequent produced (non-idempotent) records increment it.
        """
        return self._collaborators.intake.fetch_and_intake(
            request,
            writer=writer,
            world=world,
            receive_wall_time=receive_wall_time,
            sequence_start=sequence_start,
            receive_monotonic_diagnostic=receive_monotonic_diagnostic,
        )

    def submit(
        self,
        observation: object,
        boundary: SourceObservationBoundary,
    ) -> Result[ObservationReceipt]:
        """Application-routed hand-off to the Data-owned CT-10 boundary (AC1).

        Thin composition helper: ingest never reaches into the store itself for CT-15
        payloads; the application injects the boundary and routes producer values.
        """
        return self._collaborators.handoff.submit(observation, boundary)

    def known_key(self, key: IntakeKey) -> bool:
        """Whether ``key`` has already been intake'd in this process ledger."""
        return self._collaborators.intake.known_key(key)

    def start_scheduler(self, *_args: object, **_kwargs: object) -> Result[IntakeReceipt]:
        """Always refuse — scheduling is application-owned (AC6 / FM-5)."""
        return self._collaborators.schedule.start_scheduler(*_args, **_kwargs)

    def run_daemon(self, *_args: object, **_kwargs: object) -> Result[IntakeReceipt]:
        """Always refuse — process supervision is application-owned (AC6 / FM-5)."""
        return self._collaborators.schedule.run_daemon(*_args, **_kwargs)

    def run_retry_loop(self, *_args: object, **_kwargs: object) -> Result[IntakeReceipt]:
        """Always refuse — retries are application-owned (AC6 / FM-5)."""
        return self._collaborators.schedule.run_retry_loop(*_args, **_kwargs)
