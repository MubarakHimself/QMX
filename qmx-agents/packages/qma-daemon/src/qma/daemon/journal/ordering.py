"""Cross-store fold ordering by announcement ``journal_seq`` (FR-Q24; AD-6).

The announcement's ``journal_seq`` is the ordering key in every cross-store fold.
Equal instants dispose by ascending ``journal_seq``, never by a timestamp.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "AnnouncedRecord",
    "journal_seq_sort_key",
    "order_by_announcement_journal_seq",
]


@dataclass(frozen=True, slots=True)
class AnnouncedRecord:
    """A cross-store fold input carrying its announcement ``journal_seq``.

    ``recorded_at`` / ``occurred_at`` may be present for knowledge-time bounds
    (Story 42.3) but are never used as a total-order or equal-instant tie-breaker.
    """

    journal_seq: int
    store: str
    record_fp1: str
    recorded_at: int | None = None
    occurred_at: int | None = None
    payload: object | None = None


def journal_seq_sort_key(record: AnnouncedRecord) -> int:
    """Sole total-order key for announced evidence — never a timestamp."""
    return record.journal_seq


def order_by_announcement_journal_seq(
    records: Sequence[AnnouncedRecord],
) -> list[AnnouncedRecord]:
    """Order fold inputs by ascending announcement ``journal_seq`` (FR-Q24).

    Records announced at the same instant are disposed solely by ascending
    ``journal_seq``. Timestamps are ignored even when present and equal.
    """
    return sorted(records, key=journal_seq_sort_key)
