"""CT-13 — the durable journal-event vocabulary, owned by COMP-QMF-DATA (AC1-AC4).

The value vocabulary of the durable journal: a state change recorded as **evidence
encoding** — an ``int64`` UTC-nanosecond instant plus an AD-8
:class:`~qmf.core.WriterId` plus a strictly-increasing per-writer sequence — one of
exactly **seven ratified event types**. This module pins the vocabulary; the
:mod:`qmf.data.journal_producer` boundary appends it through the Story 3.1 store seam
and enforces the gapless-sequence and block-on-unpersistable discipline.

Four things this module pins down.

**Seven event types, addable but never redefined (AC1; DEC-0119, DEC-0116).**
:class:`JournalEventType` is the closed V1 set — decision, order, fill, risk
transition, promotion, data quality, control action. It is a ``StrEnum``, so a later
version may **add** a type; the seven existing meanings never change. A record whose
type is outside the set never becomes a journal event (an ``invalid input`` refusal).
QMF's own wired producers are qmf-data itself (data quality, control action).

**The decision event's mandatory closed outcome (AC3; DEC-0158, DEC-0150).** A
``decision`` event carries a mandatory :class:`DecisionOutcome` — ``authorized |
refused-by-door | suppressed`` — with the refusing-door or suppressing-authority
reference in its payload, so a projection (the legacy ``veto_ledger`` included)
selects on that **declared field**, never on key presence (:func:`select_decisions`,
:func:`veto_ledger`). A non-decision event carries no outcome; a decision event
without one does not build.

**fp1 identity, with correlation_id and display_time excluded (AC4; DEC-0112,
DEC-0108).** A journal event's identity is its ``fp1`` fingerprint, computed by the
single ``qmf-core`` implementation over :meth:`JournalEvent.fp1_identity`. Two
declared parts are **excluded from identity by this explicit versioned declaration**
(:data:`CORRELATION_ID_EXCLUDED_FROM_FP1`): ``correlation_id`` — a linking annotation
that still propagates across package boundaries — and the optional ``display_time``, a
display-only ISO-8601-with-Z rendering. Journals are evidence encoding (int64 UTC ns +
writer + sequence); operator/diagnostic logs are the ISO-8601-Z display, a distinct
thing (:meth:`JournalEvent.render_display_time`).

**Cross-stream causal linkage rides only typed edge records (AC4; DEC-0119,
DEC-0114).** ``(instant, writer, sequence)`` is a replay-determinism
:class:`~qmf.core.OrderingKey` with **no causal meaning** — causality never rides a
timestamp or the ordering key. Causal linkage across streams is a
:class:`CausalEdge`, an AD-16 typed edge record referencing two events by their ``fp1``
fingerprints (the CT-07 lineage-edge shape qmf-data emits as a value; DEC-0120).

A detected sequence gap **signals loss and is surfaced** (:func:`detect_sequence_gaps`)
— never swallowed. Stdlib + qmf-core (fp1 comes only from qmf-core); frozen, immutable
values throughout.

Event construction, causal edges, and gap detection live in sibling modules;
this module re-exports the public names so existing import paths keep working.
"""

from __future__ import annotations

from qmf.data.journal_edge import CausalEdge
from qmf.data.journal_event import JournalEvent
from qmf.data.journal_scan import detect_sequence_gaps, select_decisions, veto_ledger
from qmf.data.journal_types import (
    CONTRACT_FORMAT_VERSION,
    CORRELATION_ID_EXCLUDED_FROM_FP1,
    DISPLAY_TIME_EXCLUDED_FROM_FP1,
    DecisionOutcome,
    JournalEventType,
)

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "CORRELATION_ID_EXCLUDED_FROM_FP1",
    "DISPLAY_TIME_EXCLUDED_FROM_FP1",
    "CausalEdge",
    "DecisionOutcome",
    "JournalEvent",
    "JournalEventType",
    "detect_sequence_gaps",
    "select_decisions",
    "veto_ledger",
]
