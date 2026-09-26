"""COMP-CALENDAR-FEED — news-calendar CT-15 provider with fail-closed degradation.

Story 6.4. Distinct from the market-hours calendar and the day-boundary calendar
(DEC-0106). This module is QMF-authored adapter surface for the external
news-calendar feed consumed by the standalone recorder: provider-native identity
and revisions through idempotent ``(source, source-native id, revision)`` intake,
verbatim impact labels (QMX mints no severity scale), every import journaled as a
CT-13 ``data quality`` event, and fail-closed degradation on failed refresh /
unknown coverage / missing per-instrument currency-exposure — treated-as-affected
downstream, no live skip button. The feed defines no blackout window and holds no
permission; CT-31 owns that. Legal archiving/retention stays an open operator
item — this adapter never claims operational retention is authorized (DEC-0119,
DEC-0052, DEC-0152).

Transport bytes are injected (:class:`CalendarFeedTransport`) so tests never hit
the live CDN. Stdlib + qmf-core + the CT-15 ingest / CT-13 journal types already
in this package.

Decode, adapter, and import helpers live in sibling modules; this module
re-exports the public names so existing import paths keep working.
"""

from __future__ import annotations

from qmf.data.calendar_feed_adapter import CalendarFeedAdapter, CalendarFeedTransport
from qmf.data.calendar_feed_decode import decode_calendar_snapshot
from qmf.data.calendar_feed_import import (
    CalendarFeedImport,
    journal_fail_closed,
    journal_import,
)
from qmf.data.calendar_feed_types import (
    CALENDAR_FEED_SOURCE,
    CALENDAR_FEED_VENUE,
    CONTRACT_FORMAT_VERSION,
    LEGAL_ARCHIVING_POSTURE,
    CalendarEvent,
    CalendarImportReceipt,
    FailClosedReason,
    FailClosedSignal,
    fail_closed,
    refuse_authorized_retention_claim,
    refuse_live_skip,
    refuse_minted_severity_scale,
)

__all__ = [
    "CALENDAR_FEED_SOURCE",
    "CALENDAR_FEED_VENUE",
    "CONTRACT_FORMAT_VERSION",
    "LEGAL_ARCHIVING_POSTURE",
    "CalendarEvent",
    "CalendarFeedAdapter",
    "CalendarFeedImport",
    "CalendarFeedTransport",
    "CalendarImportReceipt",
    "FailClosedReason",
    "FailClosedSignal",
    "decode_calendar_snapshot",
    "fail_closed",
    "journal_fail_closed",
    "journal_import",
    "refuse_authorized_retention_claim",
    "refuse_live_skip",
    "refuse_minted_severity_scale",
]
