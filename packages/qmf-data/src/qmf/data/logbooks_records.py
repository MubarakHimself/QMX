"""CT-25 legacy Records streams as projection names over the seven event types.

Split from :mod:`qmf.data.logbooks` so the public module stays under the Skylos
god-file limits. Callers keep importing these names from :mod:`qmf.data.logbooks`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qmf.core import Ok, Result
from qmf.data.journal import DecisionOutcome, JournalEvent, JournalEventType, select_decisions
from qmf.data.store.refusals import invalid_input

__all__ = [
    "RECORDS_STREAM_MAPPING",
    "RecordsStreamName",
    "RecordsStreamRule",
    "records_stream",
]


class RecordsStreamName(StrEnum):
    """The legacy five Records stream names, surviving as **projection names only** (AC4).

    Each maps onto the seven journal event types by the one versioned
    :data:`RECORDS_STREAM_MAPPING` table — no second event catalog is minted (DEC-0145).
    None of these is a stream an entity writes; they are read-time selections over the
    recorded writer-scoped streams.
    """

    VETO_LEDGER = "veto_ledger"
    TRADE_JOURNAL = "trade_journal"
    BOOK_JOURNAL = "book_journal"
    KSA_AUDIT_LOG = "ksa_audit_log"
    CORRELATION_LEDGER = "correlation_ledger"


@dataclass(frozen=True, slots=True)
class RecordsStreamRule:
    """One legacy Records projection's mapping onto the seven event types (AC4; DEC-0145).

    ``event_types`` is the subset of the seven this projection name selects; ``outcome`` is
    the decision-outcome filter a decision-selecting projection applies (only ``veto_ledger``
    sets it — to ``refused-by-door``, so the projection selects on the decision event's
    declared ``outcome`` field, never on key presence).
    """

    event_types: frozenset[JournalEventType]
    outcome: DecisionOutcome | None = None


# The ONE versioned mapping table (AC4; DEC-0145). Each legacy Records name maps onto a
# subset of AD-21's seven event types; no second event catalog exists. Rationale, from the
# recovered node/wiki material:
#   * veto_ledger      -> a refused (vetoed) decision: the decision event with declared
#                         outcome = refused-by-door (never key presence) (DEC-0158).
#   * trade_journal    -> the trade lifecycle: order + fill (venue-authored).
#   * book_journal     -> the Book lifecycle: decision (commit_decision_with_evidence),
#                         risk transition (book_mode_changed), promotion (book_definition
#                         created/registered).
#   * ksa_audit_log    -> the BMS kill-switch/safety audit stream: control action.
#   * correlation_ledger -> BMS cohort/chorus correlation observations. Historically its
#                         payload/event-type detail was OPEN; among the seven types these
#                         BMS-authored risk-domain observations map onto risk transition.
#                         The table is versioned, so the cohort-correlation-evidence sitting
#                         can re-mint this row without a second event catalog.
RECORDS_STREAM_MAPPING: Final[Mapping[RecordsStreamName, RecordsStreamRule]] = MappingProxyType(
    {
        RecordsStreamName.VETO_LEDGER: RecordsStreamRule(
            event_types=frozenset({JournalEventType.DECISION}),
            outcome=DecisionOutcome.REFUSED_BY_DOOR,
        ),
        RecordsStreamName.TRADE_JOURNAL: RecordsStreamRule(
            event_types=frozenset({JournalEventType.ORDER, JournalEventType.FILL}),
        ),
        RecordsStreamName.BOOK_JOURNAL: RecordsStreamRule(
            event_types=frozenset(
                {
                    JournalEventType.DECISION,
                    JournalEventType.RISK_TRANSITION,
                    JournalEventType.PROMOTION,
                }
            ),
        ),
        RecordsStreamName.KSA_AUDIT_LOG: RecordsStreamRule(
            event_types=frozenset({JournalEventType.CONTROL_ACTION}),
        ),
        RecordsStreamName.CORRELATION_LEDGER: RecordsStreamRule(
            event_types=frozenset({JournalEventType.RISK_TRANSITION}),
        ),
    }
)


def _coerce_records_stream_name(value: object) -> RecordsStreamName | None:
    """Resolve ``value`` to a :class:`RecordsStreamName` member, or ``None``."""
    if isinstance(value, RecordsStreamName):
        return value
    if isinstance(value, str):
        try:
            return RecordsStreamName(value)
        except ValueError:
            return None
    return None


def records_stream(events: Iterable[JournalEvent], name: object) -> Result[list[JournalEvent]]:
    """Resolve one legacy Records projection name onto the seven event types (AC4; DEC-0145).

    The legacy five Records streams survive as projection names only. This resolves a
    :class:`RecordsStreamName` (or its string) through the one versioned
    :data:`RECORDS_STREAM_MAPPING` table — no second event catalog. ``veto_ledger`` selects
    on the decision event's declared ``outcome = refused-by-door`` field (via
    :func:`~qmf.data.journal.select_decisions`), never on key presence; every other name
    selects on its declared event types. An unknown name is an ``invalid input`` refusal.
    """
    resolved = _coerce_records_stream_name(name)
    if resolved is None:
        return invalid_input(
            "name",
            "a Records projection is one of the legacy five names, mapped onto the seven "
            "event types by the one versioned CT-25 table (DEC-0145)",
            given=repr(name),
            allowed=[member.value for member in RecordsStreamName],
        )
    rule = RECORDS_STREAM_MAPPING[resolved]
    materialized = list(events)
    if rule.outcome is not None:
        return Ok(select_decisions(materialized, outcome=rule.outcome))
    return Ok([event for event in materialized if event.event_type in rule.event_types])
