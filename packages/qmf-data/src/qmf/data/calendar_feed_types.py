"""COMP-CALENDAR-FEED public vocabulary: fail-closed signals and event evidence.

Split from :mod:`qmf.data.calendar_feed` so the adapter module stays under the
Skylos god-file limits. Callers keep importing these names from
:mod:`qmf.data.calendar_feed`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qmf.core import Instrument, Ok, Result, TypedRefusal
from qmf.data.ingest import IntakeReceipt, ProviderRecord
from qmf.data.journal_producer import JournalAppendReceipt
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "CALENDAR_FEED_SOURCE",
    "CALENDAR_FEED_VENUE",
    "CONTRACT_FORMAT_VERSION",
    "LEGAL_ARCHIVING_POSTURE",
    "CalendarEvent",
    "CalendarImportReceipt",
    "FailClosedReason",
    "FailClosedSignal",
    "fail_closed",
    "refuse_authorized_retention_claim",
    "refuse_live_skip",
    "refuse_minted_severity_scale",
]

# Story 6.4 vocabulary format version — meaning never mutates in place (L15).
CONTRACT_FORMAT_VERSION: Final[int] = 1

# Read-only provenance noun for this provider (DEC-0117) — never a VenueId.
CALENDAR_FEED_SOURCE: Final[str] = "news-calendar"

# CT-03 venue used only to host opaque currency-code instruments for event evidence.
# Scope for blackouts is CT-31 currency-exposure records, never this symbol.
CALENDAR_FEED_VENUE: Final[str] = "news-calendar"

# DEC-0119 / FM-3: legal archiving posture is an open operator item — recorded,
# never resolved, never claimed authorized by this adapter.
LEGAL_ARCHIVING_POSTURE: Final[str] = "open-operator-item"

EMPTY: Final[Mapping[str, object]] = MappingProxyType({})


class FailClosedReason(StrEnum):
    """Visible degradation reasons that must fail closed (AC4 / SCN-0008).

    Downstream CT-31 treats the instrument as affected (blocks new entries). The
    feed itself supplies no permission and no live skip (FM-4, DEC-0152).
    """

    FAILED_REFRESH = "failed-refresh"
    UNKNOWN_COVERAGE = "unknown-coverage"
    MISSING_CURRENCY_EXPOSURE = "missing-currency-exposure"


@dataclass(frozen=True, slots=True)
class FailClosedSignal:
    """A journaled, alarmed, treated-as-affected degradation signal (AC4).

    Always ``treated_as_affected=True`` and ``alarm=True``. There is no live skip
    button — :func:`refuse_live_skip` is the only answer to a skip ask.
    """

    reason: FailClosedReason
    detail: Mapping[str, object] = field(default_factory=lambda: EMPTY)
    treated_as_affected: bool = True
    alarm: bool = True
    format_version: int = CONTRACT_FORMAT_VERSION

    def to_payload(self) -> dict[str, object]:
        """CT-13 data-quality payload for this signal."""
        payload: dict[str, object] = {
            "signal": "calendar-fail-closed",
            "reason": self.reason.value,
            "treated_as_affected": True,
            "alarm": True,
            "source": CALENDAR_FEED_SOURCE,
            "component": "COMP-CALENDAR-FEED",
            "contract": "CT-15",
            "legal_archiving_posture": LEGAL_ARCHIVING_POSTURE,
            "format_version": self.format_version,
        }
        payload.update(dict(self.detail))
        return payload


def fail_closed(
    reason: object,
    *,
    detail: Mapping[str, object] | None = None,
) -> Result[FailClosedSignal]:
    """Build a fail-closed signal, or refuse an unknown reason token."""
    if isinstance(reason, FailClosedReason):
        resolved = reason
    elif isinstance(reason, str):
        try:
            resolved = FailClosedReason(reason)
        except ValueError:
            return invalid_input(
                "reason",
                "fail-closed reason must be failed-refresh | unknown-coverage | "
                "missing-currency-exposure (AC4, SCN-0008)",
                given=repr(reason),
            )
    else:
        return invalid_input(
            "reason",
            "fail-closed reason must be a FailClosedReason or its wire token",
            given=repr(reason),
        )
    det: Mapping[str, object] = EMPTY if detail is None else MappingProxyType(dict(detail))
    return Ok(FailClosedSignal(reason=resolved, detail=det))


def refuse_live_skip(
    *,
    request: str | None = None,
) -> TypedRefusal:
    """Refuse any ask for a live skip around fail-closed calendar degradation (AC4).

    SCN-0008 / DEC-0152: there is no live skip button; operator control is upstream
    configuration between sessions.
    """
    context: dict[str, object] = {
        "signal": "refuse-live-skip",
        "component": "COMP-CALENDAR-FEED",
        "contract": "CT-15",
        "treated_as_affected": True,
    }
    if request is not None:
        context["request"] = request
    return policy_rejection(
        "skip",
        "a failed calendar refresh, unknown coverage, or missing currency-exposure "
        "fails closed with no live skip button — treated-as-affected downstream "
        "(AC4, FM-4, DEC-0152, SCN-0008)",
        **context,
    )


def refuse_minted_severity_scale(
    *,
    request: str | None = None,
) -> TypedRefusal:
    """Refuse minting a QMX severity scale over provider impact labels (AC2).

    Provider impact labels are stored verbatim; severity-to-window is a declared
    node mapping outside this feed (DEC-0152, DEC-0156).
    """
    context: dict[str, object] = {
        "signal": "refuse-minted-severity",
        "component": "COMP-CALENDAR-FEED",
    }
    if request is not None:
        context["request"] = request
    return policy_rejection(
        "severity",
        "QMX mints no severity scale of its own in V1 — provider impact labels are "
        "stored verbatim; severity-to-window is a declared node mapping, not this "
        "feed (AC2, DEC-0152, DEC-0156)",
        **context,
    )


def refuse_authorized_retention_claim(
    *,
    request: str | None = None,
) -> TypedRefusal:
    """Refuse claiming operational retention is authorized (AC5 / FM-3).

    Legal archiving/retention posture remains an open operator item (DEC-0119).
    """
    context: dict[str, object] = {
        "signal": "refuse-authorized-retention",
        "component": "COMP-CALENDAR-FEED",
        "legal_archiving_posture": LEGAL_ARCHIVING_POSTURE,
    }
    if request is not None:
        context["request"] = request
    return policy_rejection(
        "retention",
        "news-calendar legal archiving/retention is an open operator item — this "
        "adapter does not claim operational retention is authorized (AC5, FM-3, "
        "DEC-0119, DEC-0052)",
        **context,
    )


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    """One news-calendar event as governed source evidence (AC1, AC2).

    Carries event-time, known-at, source, and revision. ``impact_label`` is the
    provider's label stored verbatim — never remapped to a QMX severity. ``currency``
    is the provider's opaque currency/country token for CT-31 exposure lookup; this
    value defines no window and holds no permission.
    """

    source: str
    source_native_id: str
    revision: str
    event_time_ns: int
    known_at_ns: int
    impact_label: str
    currency: str
    title: str
    foreign_timestamp: Mapping[str, object] | None = None
    format_version: int = CONTRACT_FORMAT_VERSION

    def to_provider_record(self, instrument: Instrument) -> ProviderRecord:
        """CT-15 :class:`ProviderRecord` for idempotent intake (AC1)."""
        return ProviderRecord(
            source=self.source,
            source_native_id=self.source_native_id,
            revision=self.revision,
            event_time=self.event_time_ns,
            known_at=self.known_at_ns,
            instrument=instrument,
            foreign_timestamp=dict(self.foreign_timestamp)
            if self.foreign_timestamp is not None
            else None,
        )


@dataclass(frozen=True, slots=True)
class CalendarImportReceipt:
    """Receipt of one journaled news-calendar import (AC1–AC5).

    ``legal_archiving_posture`` is always :data:`LEGAL_ARCHIVING_POSTURE` — open,
    never claimed authorized.
    """

    events: tuple[CalendarEvent, ...]
    intake_receipts: tuple[IntakeReceipt, ...]
    journal_receipt: JournalAppendReceipt
    legal_archiving_posture: str = LEGAL_ARCHIVING_POSTURE
    format_version: int = CONTRACT_FORMAT_VERSION
