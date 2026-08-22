"""Time-series partitioning — the (source, instrument, time-window) key (AC5).

Time-series evidence resolves within its ``(source, instrument, time-window)``
partition inside its world's room (DEC-0118, DEC-0117). This module pins the partition
as a value type: a :class:`SeriesPartition` names the read-only provider (``source``,
orthogonal to a tradeable VenueId), the :class:`~qmf.core.Instrument` it concerns, and
the half-open :class:`~qmf.core.Interval` time window it spans. The partition is carried
inside the archived evidence and enters its fp1 identity, so the same series bytes under
two different windows are two distinct artifacts and every stored series resolves back
to exactly the partition it was placed in.

A rebuildable analytics view is never a series partition and is never treated as
evidence-bearing — series partitioning is a raw-archive (evidence) concept only (AC5).

Stdlib + qmf-core only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from qmf.core import Instant, Instrument, Interval, Ok, Result, VenueId, is_ok
from qmf.data.store import StoreReceipt
from qmf.data.store.refusals import invalid_input

__all__ = ["ResolvedSeries", "SeriesPartition", "SeriesPlacement"]


@dataclass(frozen=True, slots=True)
class SeriesPartition:
    """The ``(source, instrument, time-window)`` partition of a time-series artifact.

    ``source`` is the provenance noun for a read-only provider — orthogonal to a
    tradeable ``VenueId`` (a provider QMF only reads from is a source, one it trades at
    is a venue, DEC-0117). ``instrument`` is the ``qmf-core`` instrument identity, and
    ``window`` is the half-open ``[start, end)`` span the series covers. The three
    together locate the evidence inside its world's raw archive; two partitions are
    equal only when all three match.
    """

    source: str
    instrument: Instrument
    window: Interval

    @classmethod
    def try_create(
        cls, source: object, instrument: object, window: object
    ) -> Result[SeriesPartition]:
        """Validate and build a :class:`SeriesPartition`, returning value-or-refusal.

        ``source`` must be a non-empty token, ``instrument`` an :class:`Instrument`, and
        ``window`` an :class:`Interval`; any missing or ill-typed part is an
        ``invalid input`` refusal naming the offending field (CT-04; DEC-0109).
        """
        if not isinstance(source, str) or source.strip() == "":
            return invalid_input(
                "source",
                "a series partition names a non-empty source (a read-only provider id, "
                "orthogonal to a tradeable VenueId)",
                given=repr(source),
            )
        if not isinstance(instrument, Instrument):
            return invalid_input(
                "instrument",
                "a series partition is scoped to a qmf-core Instrument identity",
                given=repr(instrument),
            )
        if not isinstance(window, Interval):
            return invalid_input(
                "window",
                "a series partition spans a half-open qmf-core Interval time window",
                given=repr(window),
            )
        return cls._build(source.strip(), instrument, window)

    @classmethod
    def _build(
        cls, source: str, instrument: Instrument, window: Interval
    ) -> Result[SeriesPartition]:
        return Ok(cls(source=source, instrument=instrument, window=window))

    @property
    def partition_key(self) -> str:
        """A deterministic, human-legible key for the partition.

        Groups artifacts of the same source, instrument, and window under one stable
        string — ``source | venue:symbol | start_ns-end_ns`` — for logging and indexing.
        It is a convenience label, not an identity: fp1 identity comes from
        :meth:`identity`, computed only by ``qmf-core``.
        """
        return (
            f"{self.source} | {self.instrument.venue.value}:{self.instrument.symbol} | "
            f"{self.window.start.value_ns}-{self.window.end.value_ns}"
        )

    def identity(self) -> dict[str, object]:
        """The canonical partition content embedded in an archived series artifact.

        Integer-only for time (int64 UTC ns) and verbatim strings for source, venue, and
        symbol — no floats — so it canonicalizes cleanly into the artifact's fp1 identity
        (DEC-0108). :meth:`from_identity` reverses it exactly.
        """
        return {
            "source": self.source,
            "venue": self.instrument.venue.value,
            "symbol": self.instrument.symbol,
            "window_start_ns": self.window.start.value_ns,
            "window_end_ns": self.window.end.value_ns,
        }

    @classmethod
    def from_identity(cls, identity: Mapping[str, object]) -> Result[SeriesPartition]:
        """Rebuild a :class:`SeriesPartition` from a stored :meth:`identity` mapping.

        Reconstructs the ``Instrument`` and ``Interval`` through their ``qmf-core``
        factories so a corrupt or hand-edited partition (a bad venue token, a start after
        the end) is an ``invalid input`` refusal, never a silently-wrong partition.
        """
        venue = VenueId.try_create(identity.get("venue"))
        if not is_ok(venue):
            return venue
        instrument = Instrument.try_create(venue.value, identity.get("symbol"))
        if not is_ok(instrument):
            return instrument
        start = Instant.try_create(identity.get("window_start_ns"))
        if not is_ok(start):
            return start
        end = Instant.try_create(identity.get("window_end_ns"))
        if not is_ok(end):
            return end
        window = Interval.try_create(start.value, end.value)
        if not is_ok(window):
            return window
        return cls.try_create(identity.get("source"), instrument.value, window.value)

    def contains_event(self, event: object) -> Result[bool]:
        """Whether an event :class:`Instant` falls in this partition's half-open window.

        A convenience over :meth:`Interval.contains` so a caller can check whether a
        given event-time belongs in this partition (start included, end excluded).
        """
        if not isinstance(event, Instant):
            return invalid_input(
                "event",
                "partition containment tests an Instant event-time",
                given=repr(event),
            )
        return self.window.contains(event)


@dataclass(frozen=True, slots=True)
class SeriesPlacement:
    """The receipt of time-series evidence placed within its partition (AC5).

    ``partition`` is the ``(source, instrument, time-window)`` the series was placed in,
    and ``archive`` is the Story 3.1 immutable-raw-archive receipt for the artifact that
    physically holds it (its fp1 key, world, and idempotent/stored outcome). Because the
    partition rode into the artifact's identity, ``archive.fingerprint`` resolves back to
    exactly this partition.
    """

    partition: SeriesPartition
    archive: StoreReceipt


@dataclass(frozen=True, slots=True)
class ResolvedSeries:
    """Time-series evidence resolved back within its partition (AC5).

    ``partition`` is the ``(source, instrument, time-window)`` the artifact resolved
    within — proof that the evidence is located inside its declared partition — and
    ``rows`` are the series rows it holds, in stored order.
    """

    partition: SeriesPartition
    rows: tuple[dict[str, object], ...]
