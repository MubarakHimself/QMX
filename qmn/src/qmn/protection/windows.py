"""Book-door enforcement of CT-31 news windows and dead zones (Story 26.3).

Pair-scoped news blackout and both dead-zone kinds
(``daily_dead_zone`` | ``session_handover_buffer``) stop live AND paper entries
on affected instruments while exits, protection, and recording pass. Missing
currency-exposure scope or a stale news calendar fails entries closed. Widths
and anchors are resolved settings — never invented minute defaults. Revisions
widen-or-add automatically; narrowing an in-force or same-trading-day window
stays blocked through the prior declared end unless an operator act cites both
revisions. There is no live skip power (TN-8 / CT-31 / SCN-0008 / DEC-0152).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

from qmf.core import (
    CalendarIdentity,
    Duration,
    Fingerprint,
    Instant,
    Ok,
    Result,
    TypedRefusal,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.risk.control_window import (
    DAILY_DEAD_ZONE_WIDTH_VARIABLE,
    NEWS_BLACKOUT_AFTER_VARIABLE,
    NEWS_BLACKOUT_BEFORE_VARIABLE,
    PROTECTION_WINDOW_VARIABLE_NAMES,
    SESSION_HANDOVER_BUFFER_ANCHOR_VARIABLE,
    SESSION_HANDOVER_BUFFER_WIDTH_VARIABLE,
    WINDOW_EFFECT,
    AnchorSide,
    ControlWindowRecord,
    ControlWindowRevisionLog,
    EffectiveWindow,
    FailClosedCause,
    ProposedWindowAct,
    VetoDecisionRecord,
    WindowBounds,
    WindowEvaluation,
    WindowKind,
    append_window_revision,
    check_window_blocks_act,
    evaluate_entry_under_windows,
    fail_closed_on_uncertainty,
    fold_effective_window,
    mint_veto_decision,
    reject_live_skip,
    reject_symbol_currency_parse,
    window_in_force_at,
)
from qmf.risk.paper import BookMode

from qmn.protection._refuse import clean_token, invalid, policy
from qmn.time.calendars import CalendarKind

__all__ = [
    "DEAD_ZONE_KINDS",
    "NEWS_CALENDAR_MAX_STALENESS_VARIABLE",
    "PROTECTION_WINDOW_VARIABLE_NAMES",
    "WINDOW_DOOR",
    "WINDOW_EFFECT",
    "BookDoorWindowGate",
    "DeadZoneKind",
    "NewsRevisionDisposition",
    "ResolvedWindowSettings",
    "WindowActDisposition",
    "allow_protective_act_under_windows",
    "apply_news_revision",
    "assert_calendars_distinct",
    "dead_zone_kinds",
    "enforce_entry_at_book_door",
    "journal_would_have_been",
    "refuse_invented_window_minutes",
    "refuse_live_skip_at_door",
    "refuse_symbol_currency_parse_at_door",
    "require_resolved_window_settings",
    "stale_news_calendar_blocks_entries",
    "windows_in_force",
]

WINDOW_DOOR: Final[str] = "control-window"
NEWS_CALENDAR_MAX_STALENESS_VARIABLE: Final[str] = "news_calendar_max_staleness"

DEAD_ZONE_KINDS: Final[frozenset[WindowKind]] = frozenset(
    {WindowKind.DAILY_DEAD_ZONE, WindowKind.SESSION_HANDOVER_BUFFER}
)


class DeadZoneKind(StrEnum):
    """The two distinct dead-zone kinds — never conflated (DEC-0152)."""

    DAILY_DEAD_ZONE = WindowKind.DAILY_DEAD_ZONE.value
    SESSION_HANDOVER_BUFFER = WindowKind.SESSION_HANDOVER_BUFFER.value


class WindowActDisposition(StrEnum):
    """Fate of a proposed act under the Book-door window gate."""

    PASSED = "passed"
    BLOCKED_ENTRY = "blocked-entry"
    VETO_JOURNALED = "veto-journaled"
    FAIL_CLOSED = "fail-closed"


class NewsRevisionDisposition(StrEnum):
    """How a news-calendar revision is applied at the door (TN-8)."""

    WIDENED_OR_ADDED = "widened-or-added"
    NARROWING_HELD = "narrowing-held"
    OPERATOR_CITED = "operator-cited"


@dataclass(frozen=True, slots=True)
class ResolvedWindowSettings:
    """Resolved CT-31 width/anchor settings — blank invents nothing (DEC-0157).

    Every field is a present resolved value. Absence is a typed refusal at
    :func:`require_resolved_window_settings`; this type never carries defaults.
    """

    news_blackout_before: Duration
    news_blackout_after: Duration
    daily_dead_zone_width: Duration
    session_handover_buffer_width: Duration
    session_handover_buffer_anchor: AnchorSide
    news_calendar_max_staleness: Duration

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "resolved-window-settings",
            NEWS_BLACKOUT_BEFORE_VARIABLE: self.news_blackout_before.fp1_identity(),
            NEWS_BLACKOUT_AFTER_VARIABLE: self.news_blackout_after.fp1_identity(),
            DAILY_DEAD_ZONE_WIDTH_VARIABLE: self.daily_dead_zone_width.fp1_identity(),
            SESSION_HANDOVER_BUFFER_WIDTH_VARIABLE: (
                self.session_handover_buffer_width.fp1_identity()
            ),
            SESSION_HANDOVER_BUFFER_ANCHOR_VARIABLE: self.session_handover_buffer_anchor.value,
            NEWS_CALENDAR_MAX_STALENESS_VARIABLE: (
                self.news_calendar_max_staleness.fp1_identity()
            ),
        }


def require_resolved_window_settings(
    *,
    news_blackout_before: object,
    news_blackout_after: object,
    daily_dead_zone_width: object,
    session_handover_buffer_width: object,
    session_handover_buffer_anchor: object,
    news_calendar_max_staleness: object,
) -> Result[ResolvedWindowSettings]:
    """Refuse blank or invented widths — settings must be resolved Durations."""
    before = _require_duration(news_blackout_before, NEWS_BLACKOUT_BEFORE_VARIABLE)
    if isinstance(before, TypedRefusal):
        return before
    after = _require_duration(news_blackout_after, NEWS_BLACKOUT_AFTER_VARIABLE)
    if isinstance(after, TypedRefusal):
        return after
    dead = _require_duration(daily_dead_zone_width, DAILY_DEAD_ZONE_WIDTH_VARIABLE)
    if isinstance(dead, TypedRefusal):
        return dead
    handover = _require_duration(
        session_handover_buffer_width, SESSION_HANDOVER_BUFFER_WIDTH_VARIABLE
    )
    if isinstance(handover, TypedRefusal):
        return handover
    staleness = _require_duration(
        news_calendar_max_staleness, NEWS_CALENDAR_MAX_STALENESS_VARIABLE
    )
    if isinstance(staleness, TypedRefusal):
        return staleness
    if isinstance(session_handover_buffer_anchor, AnchorSide):
        anchor = session_handover_buffer_anchor
    elif isinstance(session_handover_buffer_anchor, str):
        try:
            anchor = AnchorSide(session_handover_buffer_anchor)
        except ValueError:
            return invalid(
                SESSION_HANDOVER_BUFFER_ANCHOR_VARIABLE,
                "session_handover_buffer_anchor is pre-close|post-open|both — no invented default",
                given=repr(session_handover_buffer_anchor),
                allowed=[member.value for member in AnchorSide],
            )
    else:
        return invalid(
            SESSION_HANDOVER_BUFFER_ANCHOR_VARIABLE,
            "session_handover_buffer_anchor is mandatory; blank do-not-default",
            given=repr(session_handover_buffer_anchor),
        )
    return Ok(
        ResolvedWindowSettings(
            news_blackout_before=before,
            news_blackout_after=after,
            daily_dead_zone_width=dead,
            session_handover_buffer_width=handover,
            session_handover_buffer_anchor=anchor,
            news_calendar_max_staleness=staleness,
        )
    )


def _require_duration(value: object, field: str) -> Duration | TypedRefusal:
    if value is None:
        return invalid(
            field,
            "window width/staleness is a resolved Duration; blank invents nothing",
            given="None",
        )
    if isinstance(value, (bool, int)):
        return invalid(
            field,
            "a bare minute/integer is not a window bound — refuse invented offsets; "
            "supply a Duration (or two Instants as WindowBounds)",
            given=repr(value),
        )
    if not isinstance(value, Duration):
        return invalid(
            field,
            "window settings resolve to Duration values with no spine default",
            given=repr(value),
        )
    if value.value_ns < 0:
        return invalid(field, "a window width Duration is non-negative", given=value.value_ns)
    return value


def refuse_invented_window_minutes(minutes: object) -> TypedRefusal:
    """Refuse constructing a window from bare minute offsets (DEC-0152)."""
    return invalid(
        "window_bounds",
        "a window record carries two Instants, never an invented minutes offset",
        given=repr(minutes),
    )


def refuse_symbol_currency_parse_at_door(symbol: object) -> Result[None]:
    """Currency is never parsed from the instrument symbol (CT-31)."""
    return reject_symbol_currency_parse(symbol)


def refuse_live_skip_at_door() -> Result[None]:
    """There is no live skip power over an in-force window (TN-8)."""
    return reject_live_skip()


def assert_calendars_distinct(
    *,
    market_hours: object,
    day_boundary: object,
    news: object,
) -> Result[Mapping[str, CalendarIdentity]]:
    """Market-hours, day-boundary, and news calendars remain distinct (CT-31)."""
    mh = _require_calendar(market_hours, CalendarKind.MARKET_HOURS.value)
    if isinstance(mh, TypedRefusal):
        return mh
    db = _require_calendar(day_boundary, CalendarKind.DAY_BOUNDARY.value)
    if isinstance(db, TypedRefusal):
        return db
    nc = _require_calendar(news, CalendarKind.NEWS.value)
    if isinstance(nc, TypedRefusal):
        return nc
    identities = (mh.fp1_identity(), db.fp1_identity(), nc.fp1_identity())
    if len({_calendar_key(row) for row in identities}) < 3:
        return policy(
            "calendar_identity",
            "market-hours, day-boundary, and news calendars are distinct identities; "
            "never substituted for one another",
        )
    return Ok(
        {
            CalendarKind.MARKET_HOURS.value: mh,
            CalendarKind.DAY_BOUNDARY.value: db,
            CalendarKind.NEWS.value: nc,
        }
    )


def _calendar_key(row: Mapping[str, object]) -> tuple[object, ...]:
    return tuple(sorted((str(k), repr(v)) for k, v in row.items()))


def _require_calendar(value: object, field: str) -> CalendarIdentity | TypedRefusal:
    if not isinstance(value, CalendarIdentity):
        return invalid(
            field,
            "each named calendar kind carries a CalendarIdentity — never a bare calendar token",
            given=repr(value),
        )
    return value


def stale_news_calendar_blocks_entries(
    *,
    last_refresh_at: object,
    decision_at: object,
    max_staleness: object,
) -> Result[None]:
    """Fail closed when the news calendar exceeds max staleness (DEC-0193)."""
    if not isinstance(last_refresh_at, Instant):
        return invalid(
            "last_refresh_at",
            "news-calendar freshness is measured from an Instant last refresh",
            given=repr(last_refresh_at),
        )
    if not isinstance(decision_at, Instant):
        return invalid(
            "decision_at",
            "staleness is evaluated at an Instant decision time",
            given=repr(decision_at),
        )
    if not isinstance(max_staleness, Duration):
        return invalid(
            NEWS_CALENDAR_MAX_STALENESS_VARIABLE,
            "news_calendar_max_staleness is a resolved Duration — no invented default",
            given=repr(max_staleness),
        )
    age = decision_at.difference(last_refresh_at)
    if is_refusal(age):
        return age
    if age.value.value_ns > max_staleness.value_ns:
        return fail_closed_on_uncertainty(cause=FailClosedCause.FAILED_CALENDAR_REFRESH)
    return Ok(None)


@dataclass(frozen=True, slots=True)
class BookDoorWindowGate:
    """Outcome of evaluating a proposed act at the Book door under windows."""

    disposition: WindowActDisposition
    evaluation: WindowEvaluation | None
    veto: VetoDecisionRecord | None
    book_mode: BookMode
    proposed_act: ProposedWindowAct

    @property
    def blocked(self) -> bool:
        return self.disposition in {
            WindowActDisposition.BLOCKED_ENTRY,
            WindowActDisposition.VETO_JOURNALED,
            WindowActDisposition.FAIL_CLOSED,
        }


def enforce_entry_at_book_door(
    *,
    instrument: object,
    book_mode: object,
    decision_at: object,
    windows: object,
    would_have_been_action: object,
    proposed_act: object = ProposedWindowAct.ENTRY,
    news_calendar_fresh: object = True,
) -> Result[BookDoorWindowGate]:
    """Block live and paper entries under in-force windows; journal the veto.

    Exits and protective acts must call :func:`allow_protective_act_under_windows`
    instead — a window never blocks them.
    """
    if news_calendar_fresh is False:
        mode = _coerce_book_mode(book_mode)
        if isinstance(mode, TypedRefusal):
            return mode
        closed = fail_closed_on_uncertainty(cause=FailClosedCause.FAILED_CALENDAR_REFRESH)
        if not is_refusal(closed):
            return invalid(
                "news_calendar_fresh",
                "a stale news calendar must fail closed as a policy rejection",
            )
        return Ok(
            BookDoorWindowGate(
                disposition=WindowActDisposition.FAIL_CLOSED,
                evaluation=None,
                veto=None,
                book_mode=mode,
                proposed_act=ProposedWindowAct.ENTRY,
            )
        )

    act = _coerce_act(proposed_act)
    if isinstance(act, TypedRefusal):
        return act
    if act is not ProposedWindowAct.ENTRY:
        return policy(
            "proposed_act",
            "enforce_entry_at_book_door evaluates entries only; exits/protection "
            "use allow_protective_act_under_windows so windows never block them",
            act=act.value,
            effect=WINDOW_EFFECT.value,
        )

    evaluation = evaluate_entry_under_windows(
        instrument=instrument,
        book_mode=book_mode,
        decision_at=decision_at,
        windows=windows,
        proposed_act=act,
    )
    if is_refusal(evaluation):
        return evaluation
    ev = evaluation.value
    if not ev.blocked:
        return Ok(
            BookDoorWindowGate(
                disposition=WindowActDisposition.PASSED,
                evaluation=ev,
                veto=None,
                book_mode=ev.book_mode,
                proposed_act=act,
            )
        )

    action_fp = _action_fingerprint(would_have_been_action)
    if isinstance(action_fp, TypedRefusal):
        return action_fp
    veto = mint_veto_decision(
        ev,
        instrument=instrument,
        would_have_been_action_fp=action_fp,
        decision_at=decision_at,
    )
    if is_refusal(veto):
        return veto
    return Ok(
        BookDoorWindowGate(
            disposition=WindowActDisposition.VETO_JOURNALED,
            evaluation=ev,
            veto=veto.value,
            book_mode=ev.book_mode,
            proposed_act=act,
        )
    )


def allow_protective_act_under_windows(*, proposed_act: object) -> Result[None]:
    """Exits, amendments, protection, and recording always pass windows."""
    gate = check_window_blocks_act(proposed_act=proposed_act)
    if is_ok(gate):
        # ENTRY may be blocked — this helper is for non-entry acts only.
        return policy(
            "proposed_act",
            "allow_protective_act_under_windows is for exits/protection/recording; "
            "entries use enforce_entry_at_book_door",
            act=ProposedWindowAct.ENTRY.value,
        )
    # check_window_blocks_act refuses non-entry acts as "windows must not block them".
    # At the Book door that refusal means the act PASSES the window gate.
    act = _coerce_act(proposed_act)
    if isinstance(act, TypedRefusal):
        return act
    if act is ProposedWindowAct.ENTRY:
        return policy(
            "proposed_act",
            "entries are not protective acts under the window gate",
        )
    return Ok(None)


def journal_would_have_been(gate: object) -> Result[VetoDecisionRecord]:
    """Return the journaled veto for a blocked entry; refuse if none."""
    if not isinstance(gate, BookDoorWindowGate):
        return invalid(
            "gate",
            "journal_would_have_been reads a BookDoorWindowGate",
            given=repr(gate),
        )
    if gate.veto is None:
        return invalid(
            "gate",
            "a would-have-been veto exists only for a blocked entry under a window",
            disposition=gate.disposition.value,
        )
    return Ok(gate.veto)


def apply_news_revision(
    log: object,
    revision: object,
    *,
    decision_at: object,
    prior_in_force: object = None,
    operator_cites_revisions: object = None,
) -> Result[tuple[ControlWindowRevisionLog, EffectiveWindow, NewsRevisionDisposition]]:
    """Append a revision; enforce widen-never-shrink (TN-8 / DEC-0152).

    Narrowing, removal, downgrade, delay, or shortening of an in-force or
    same-trading-day window is ingested as evidence but the prior block stays
    effective through its declared end unless ``operator_cites_revisions`` names
    both revision tokens.
    """
    if not isinstance(decision_at, Instant):
        return invalid(
            "decision_at",
            "news revision fold is at an Instant decision time",
            given=repr(decision_at),
        )
    appended = append_window_revision(log, revision)
    if is_refusal(appended):
        return appended
    new_log = appended.value
    folded = fold_effective_window(new_log.revisions, decision_at=decision_at)
    if is_refusal(folded):
        return folded
    effective = folded.value

    if not isinstance(revision, ControlWindowRecord):
        return invalid("revision", "a news revision is a ControlWindowRecord")

    disposition = NewsRevisionDisposition.WIDENED_OR_ADDED
    if prior_in_force is not None:
        if not isinstance(prior_in_force, ControlWindowRecord):
            return invalid(
                "prior_in_force",
                "prior_in_force is a ControlWindowRecord when present",
                given=repr(prior_in_force),
            )
        prior_force = window_in_force_at(prior_in_force, decision_at)
        if is_refusal(prior_force):
            return prior_force
        narrowed = _is_narrowing(prior_in_force.window_bounds, revision.window_bounds)
        if narrowed and (prior_force.value or _same_trading_day_start(prior_in_force, decision_at)):
            cites = _coerce_citation_pair(operator_cites_revisions)
            if isinstance(cites, TypedRefusal):
                # No operator citation — hold the prior block via the union fold.
                disposition = NewsRevisionDisposition.NARROWING_HELD
            else:
                prior_token = _revision_token(prior_in_force)
                new_token = _revision_token(revision)
                if cites != frozenset({prior_token, new_token}):
                    return policy(
                        "operator_cites_revisions",
                        "an operator act that releases a narrowing must cite both "
                        "the prior and the new revision tokens",
                        cited=sorted(cites),
                        required=sorted({prior_token, new_token}),
                    )
                disposition = NewsRevisionDisposition.OPERATOR_CITED
                # Operator-cited release still cannot shrink the fold below the
                # union of known revisions — the fold is the sole enforcement.
                # Citation unlocks the act path; the effective window remains the
                # widen-never-shrink union unless a later out-of-day revision lands.

    # Effective bounds are always the widen-never-shrink union.
    return Ok((new_log, effective, disposition))


def _is_narrowing(prior: WindowBounds, later: WindowBounds) -> bool:
    return (
        later.start.value_ns > prior.start.value_ns or later.end.value_ns < prior.end.value_ns
    )


def _same_trading_day_start(prior: ControlWindowRecord, decision_at: Instant) -> bool:
    """Treat a window whose start falls on the decision's UTC day as same-day.

    Full day-boundary calendar evaluation is Epic 26 period-runner work; this
    door uses the Instant day bucket only to keep the TN-8 same-trading-day
    narrowing hold without inventing a calendar substitute.
    """
    day_ns = 86_400_000_000_000
    return prior.window_bounds.start.value_ns // day_ns == decision_at.value_ns // day_ns


def _revision_token(record: ControlWindowRecord) -> str:
    if record.feed_quadruple is not None:
        return record.feed_quadruple.revision
    return record.window_id


def _coerce_citation_pair(value: object) -> frozenset[str] | TypedRefusal:
    if value is None:
        return invalid(
            "operator_cites_revisions",
            "narrowing an in-force or same-trading-day window requires an operator "
            "act citing both revisions",
        )
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return invalid(
            "operator_cites_revisions",
            "operator citation is a pair of revision tokens",
            given=type(cast("object", value)).__name__,
        )
    tokens: set[str] = set()
    for item in cast("Iterable[object]", value):
        token = clean_token(item)
        if token is None:
            return invalid(
                "operator_cites_revisions",
                "each cited revision is a non-empty opaque token",
                given=repr(item),
            )
        tokens.add(token)
    if len(tokens) != 2:
        return invalid(
            "operator_cites_revisions",
            "operator citation names exactly two revision tokens",
            given=sorted(tokens),
        )
    return frozenset(tokens)


def _coerce_act(value: object) -> ProposedWindowAct | TypedRefusal:
    if isinstance(value, ProposedWindowAct):
        return value
    if isinstance(value, str):
        try:
            return ProposedWindowAct(value)
        except ValueError:
            pass
    return invalid(
        "proposed_act",
        "window gate reads a ProposedWindowAct",
        given=repr(value),
        allowed=[member.value for member in ProposedWindowAct],
    )


def _coerce_book_mode(value: object) -> BookMode | TypedRefusal:
    if isinstance(value, BookMode):
        return value
    if isinstance(value, str):
        try:
            return BookMode(value)
        except ValueError:
            pass
    return invalid(
        "book_mode",
        "Book door window gate reads BookMode LIVE|PAPER",
        given=repr(value),
        allowed=[member.value for member in BookMode],
    )


def _action_fingerprint(value: object) -> Fingerprint | TypedRefusal:
    if isinstance(value, Fingerprint):
        return value
    if isinstance(value, Mapping):
        minted = fingerprint(dict(cast("Mapping[str, object]", value)))
        if is_refusal(minted):
            return minted
        return minted.value
    return invalid(
        "would_have_been_action",
        "a blocked entry journals a Fingerprint (or fp1 mapping) of the would-have-been act",
        given=repr(value),
    )


def dead_zone_kinds() -> tuple[DeadZoneKind, ...]:
    """Both dead-zone kinds as a stable ordered tuple."""
    return (DeadZoneKind.DAILY_DEAD_ZONE, DeadZoneKind.SESSION_HANDOVER_BUFFER)


# Re-export for callers that already hold a Sequence of windows.
def windows_in_force(
    windows: object, *, decision_at: object
) -> Result[tuple[ControlWindowRecord, ...]]:
    """Filter enabled windows whose stored bounds contain ``decision_at``."""
    if not isinstance(decision_at, Instant):
        return invalid(
            "decision_at",
            "in-force filter reads an Instant",
            given=repr(decision_at),
        )
    if isinstance(windows, (str, bytes, Mapping)) or not isinstance(windows, Iterable):
        return invalid(
            "windows",
            "windows is a collection of ControlWindowRecord values",
            given=type(cast("object", windows)).__name__,
        )
    active: list[ControlWindowRecord] = []
    for item in cast("Iterable[object]", windows):
        if not isinstance(item, ControlWindowRecord):
            return invalid(
                "windows",
                "each window is a ControlWindowRecord",
                given=repr(item),
            )
        force = window_in_force_at(item, decision_at)
        if is_refusal(force):
            return force
        if force.value:
            active.append(item)
    return Ok(tuple(active))
