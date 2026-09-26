"""CT-13 sequence-gap detection and decision projections.

Split from :mod:`qmf.data.journal` so the public module stays under the Skylos
god-file limits. Callers keep importing these names from :mod:`qmf.data.journal`.
"""

from __future__ import annotations

from collections.abc import Iterable

from qmf.core import Ok, Result, Retryability, is_refusal
from qmf.data.journal_event import JournalEvent
from qmf.data.journal_types import DecisionOutcome, JournalEventType
from qmf.data.store.refusals import storage_failure

__all__ = [
    "detect_sequence_gaps",
    "select_decisions",
    "veto_ledger",
]


def detect_sequence_gaps(
    events: Iterable[JournalEvent], *, expected_start: int = 0
) -> Result[None]:
    """Scan a stream's events for a per-``(writer, boot-epoch)`` sequence gap (AC2).

    A stream's sequence is strictly increasing and **gapless** per ``(writer,
    boot-epoch)``; a detected gap **signals loss and is surfaced** — a ``storage failure``
    refusal (retryability ``no``: a lost event will not reappear on a re-read), never a
    silent success. Events are grouped by ``(machine, role, stream, boot_epoch_id)`` and
    each group must run contiguously from ``expected_start`` (the ``WriterSequencer`` start,
    ``0`` by default) with no missing value and no duplicate. Returns ``Ok(None)`` when
    every group is gapless.
    """
    per_writer: dict[tuple[str, str, str, str], list[int]] = {}
    for event in events:
        key = (
            event.writer.machine,
            event.writer.role,
            event.writer.stream,
            event.writer.boot_epoch_id,
        )
        per_writer.setdefault(key, []).append(event.sequence)
    for key, sequences in per_writer.items():
        scanned = _scan_writer_sequences(key, sequences, expected_start)
        if is_refusal(scanned):
            return scanned
    return Ok(None)


def _scan_writer_sequences(
    key: tuple[str, str, str, str], sequences: list[int], expected_start: int
) -> Result[None]:
    """Refuse a duplicate or gap in one writer's sequences; ``Ok(None)`` when gapless."""
    expected = expected_start
    for found in sorted(sequences):
        if found == expected:
            expected += 1
            continue
        signal = "duplicate" if found < expected else "gap"
        return storage_failure(
            f"a {signal} in the journal sequence signals loss for writer "
            f"(machine={key[0]}, role={key[1]}, stream={key[2]}, boot_epoch={key[3]}): "
            f"expected sequence {expected}, found {found}; the stream is gapless per "
            "(writer, boot-epoch) and the loss is surfaced, never swallowed (DEC-0119)",
            retryability=Retryability.NO,
            context={
                "signal": "loss",
                "kind": signal,
                "machine": key[0],
                "role": key[1],
                "stream": key[2],
                "boot_epoch": key[3],
                "expected_sequence": expected,
                "found_sequence": found,
            },
        )
    return Ok(None)


def select_decisions(
    events: Iterable[JournalEvent], *, outcome: DecisionOutcome | None = None
) -> list[JournalEvent]:
    """Select ``decision`` events, optionally by their declared ``outcome`` (AC3).

    Selection is on the **declared** ``event_type`` and ``outcome`` fields, never on key
    presence (DEC-0158, DEC-0150): a projection filtering ``outcome=refused-by-door`` reads
    the closed field every decision event carries, so it can never silently miss a decision
    that lacks some ad-hoc key. With ``outcome=None`` every decision event is returned.
    """
    decisions = [event for event in events if event.event_type is JournalEventType.DECISION]
    if outcome is None:
        return decisions
    return [event for event in decisions if event.outcome is outcome]


def veto_ledger(events: Iterable[JournalEvent]) -> list[JournalEvent]:
    """The legacy ``veto_ledger`` projection — decisions ``refused-by-door`` (AC3).

    The legacy ``veto_ledger`` survives as a projection **name** only; it selects on the
    decision event's declared ``outcome = refused-by-door`` field, never on key presence
    (DEC-0158). The full projection surface — entity journals and the CT-25 legacy-stream
    mapping table — lands in Story 3.6; this is the decision-outcome selector Story 3.5 owns.
    """
    return select_decisions(events, outcome=DecisionOutcome.REFUSED_BY_DOOR)
