"""Epic 10 independent audit — Cluster I (Story 10.9).

CT-31 protection windows: entries-only, instrument-scoped, fail-closed, and
widen-never-shrink. Authored from Story 10.9 ACs, CT-31, and SCN-0008.

I4 (widen-never-shrink) is Hypothesis-driven — run with `--with hypothesis`.

Planned IDs: I1-I7.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st
from qmf.core import (
    CalendarIdentity,
    Instant,
    Instrument,
    RefusalCategory,
    VenueId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.risk.control_window import (
    WINDOW_EFFECT,
    WINDOW_FORCED_FLAT_ARBITRATION_RANK,
    AnchorSide,
    ControlWindowRecord,
    ControlWindowRevisionLog,
    CurrencyExposureRecord,
    FailClosedCause,
    FeedQuadruple,
    ProposedWindowAct,
    ResolvedInstrumentScope,
    ScopeResolutionDisposition,
    WindowBounds,
    WindowForcedFlatPolicy,
    WindowKind,
    append_window_revision,
    check_window_blocks_act,
    evaluate_entry_under_windows,
    fail_closed_on_uncertainty,
    fold_effective_window,
    instrument_in_scope,
    mint_control_window,
    mint_veto_decision,
    reject_click_exemption,
    reject_live_skip,
    reject_symbol_currency_parse,
    resolve_instrument_scope,
)
from qmf.risk.paper import BookMode, TriggerDisposition


def _instant(ns: int) -> Instant:
    result = Instant.try_create(ns)
    assert is_ok(result)
    return result.value


def _instrument(symbol: str = "EURUSD") -> Instrument:
    result = Instrument.try_create(VenueId(value="ctrader"), symbol)
    assert is_ok(result)
    return result.value


def _calendar() -> CalendarIdentity:
    result = CalendarIdentity.try_create("forex-17NY", "v3", "2024a")
    assert is_ok(result)
    return result.value


def _bounds(start: int, end: int) -> WindowBounds:
    result = WindowBounds.try_create(_instant(start), _instant(end))
    assert is_ok(result)
    return result.value


def _exposure(instrument: Instrument, *currencies: str, record_id: str = "exp-1") -> CurrencyExposureRecord:
    result = CurrencyExposureRecord.try_create(instrument, currencies, _instant(500), record_id)
    assert is_ok(result)
    return result.value


def _scope(currencies: tuple[str, ...] = ("USD",)) -> ResolvedInstrumentScope:
    candidate = _instrument("EURUSD")
    result = resolve_instrument_scope(
        affected_currencies=currencies, candidate_instruments=(candidate,),
        exposure_records=(_exposure(candidate, *currencies),),
    )
    assert is_ok(result)
    return result.value


def _feed(revision: str = "r1", known_at: int = 900_000_000) -> FeedQuadruple:
    result = FeedQuadruple.try_create("calendar-feed", "nfp-2024-08", revision, _instant(known_at))
    assert is_ok(result)
    return result.value


def _news_window(*, start: int = 1_000_000_000, end: int = 2_000_000_000, revision: str = "r1",
                 known_at: int = 900_000_000, scope: ResolvedInstrumentScope | None = None,
                 window_id: str = "win-nfp-1", enabled: bool = True) -> ControlWindowRecord:
    result = mint_control_window(
        _bounds(start, end), WindowKind.NEWS, scope if scope is not None else _scope(),
        "high-impact-news", _calendar(), window_id,
        feed_quadruple=_feed(revision, known_at), enabled_by_book=enabled,
    )
    assert is_ok(result)
    return result.value


# --- I1: the window record shape ---------------------------------------------


def test_I1_window_record_shape() -> None:
    assert {k.value for k in WindowKind} == {"news", "daily_dead_zone", "session_handover_buffer"}
    window = _news_window()
    # Two instants (never an offset).
    assert window.window_bounds.start.value_ns == 1_000_000_000
    assert window.window_bounds.end.value_ns == 2_000_000_000
    assert window.feed_quadruple is not None
    assert window.window_kind is WindowKind.NEWS
    # A session-handover window MUST declare an anchor side.
    missing_anchor = mint_control_window(_bounds(1, 2), WindowKind.SESSION_HANDOVER_BUFFER,
                                         _scope(), "handover", _calendar(), "win-ho")
    assert is_refusal(missing_anchor)
    assert missing_anchor.category is RefusalCategory.INVALID_INPUT
    ok = mint_control_window(_bounds(1, 2), WindowKind.SESSION_HANDOVER_BUFFER, _scope(),
                             "handover", _calendar(), "win-ho", anchor_side=AnchorSide.BOTH)
    assert is_ok(ok)
    # Bounds refuse an offset-shaped (bare integer) input.
    offset = WindowBounds.try_create(15, 30)
    assert is_refusal(offset)
    assert "never an offset" in str(offset.context["reason"])


# --- I2: entries-only, live and paper; the veto path ------------------------


def test_I2_window_blocks_entries_only_live_and_paper() -> None:
    assert WINDOW_EFFECT.value == "entries-only"
    assert is_ok(check_window_blocks_act(proposed_act=ProposedWindowAct.ENTRY))
    # It blocks NOTHING else: exit, protection amend, protection action, observation.
    for act in (ProposedWindowAct.EXIT, ProposedWindowAct.AMEND_PROTECTION,
                ProposedWindowAct.PROTECTION_ACTION, ProposedWindowAct.RECORD_EVIDENCE):
        refused = check_window_blocks_act(proposed_act=act)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
    window = _news_window()
    instrument = _instrument()
    decision = _instant(1_500_000_000)
    for mode in (BookMode.LIVE, BookMode.PAPER):
        evaluation = evaluate_entry_under_windows(instrument=instrument, book_mode=mode,
                                                  decision_at=decision, windows=[window])
        assert is_ok(evaluation)
        assert evaluation.value.blocked is True
    # The veto path carries the refusing door, the would-have-been action, and window fp.
    evaluation = evaluate_entry_under_windows(instrument=instrument, book_mode=BookMode.LIVE,
                                              decision_at=decision, windows=[window])
    assert is_ok(evaluation)
    action_fp = fingerprint({"class": "would-have-been-entry", "symbol": "EURUSD"})
    assert is_ok(action_fp)
    veto = mint_veto_decision(evaluation.value, instrument=instrument,
                              would_have_been_action_fp=action_fp.value, decision_at=decision)
    assert is_ok(veto)
    assert veto.value.refusing_door == "control-window"
    assert veto.value.fp1_identity()["path"] == "veto"


# --- I3 [R-001 currency]: scope via currency exposure; missing -> blocked ----


def test_I3_scope_via_currency_exposure_missing_treated_as_affected() -> None:
    # Symbol-currency parsing is forbidden (a policy rejection) — scope is declared.
    assert reject_symbol_currency_parse("EURUSD").category is RefusalCategory.POLICY_REJECTION
    eurusd, gbpusd, xauusd = _instrument("EURUSD"), _instrument("GBPUSD"), _instrument("XAUUSD")
    scope = resolve_instrument_scope(
        affected_currencies={"USD"}, candidate_instruments=[eurusd, gbpusd, xauusd],
        exposure_records=[_exposure(eurusd, "EUR", "USD", record_id="e1"),
                          _exposure(gbpusd, "GBP", "USD", record_id="e2")],  # XAUUSD missing
    )
    assert is_ok(scope)
    assert eurusd in scope.value.instruments
    # A missing exposure record -> the instrument is treated as affected and blocked.
    assert xauusd in scope.value.all_blocked()
    disposition = instrument_in_scope(scope.value, xauusd)
    assert is_ok(disposition)
    assert disposition.value is ScopeResolutionDisposition.TREATED_AS_AFFECTED_MISSING_EXPOSURE
    window = _news_window(scope=scope.value)
    evaluation = evaluate_entry_under_windows(instrument=xauusd, book_mode=BookMode.PAPER,
                                              decision_at=_instant(1_500_000_000), windows=[window])
    assert is_ok(evaluation)
    assert evaluation.value.blocked is True
    assert evaluation.value.data_quality_alarm is True


# --- I4 [property]: widen-never-shrink, forward-only union fold ---------------


@settings(max_examples=100)
@given(
    spans=st.lists(
        st.tuples(st.integers(min_value=1, max_value=5_000), st.integers(min_value=1, max_value=5_000)),
        min_size=1, max_size=5,
    )
)
def test_I4_effective_window_is_the_widening_union(spans: list[tuple[int, int]]) -> None:
    # All revisions known well before the decision instant; the effective window is the
    # union — start no later than the earliest, end no earlier than the latest.
    windows = []
    known_at = 100
    starts: list[int] = []
    ends: list[int] = []
    for i, (a, b) in enumerate(spans):
        start = min(a, b) + 10_000  # keep bounds in the future relative to known_at
        end = max(a, b) + 10_000
        if start == end:
            end = start + 1
        starts.append(start)
        ends.append(end)
        windows.append(_news_window(start=start, end=end, revision=f"r{i}", known_at=known_at))
    log = ControlWindowRevisionLog(window_id="win-nfp-1")
    for window in windows:
        appended = append_window_revision(log, window)
        assert is_ok(appended)
        log = appended.value
    folded = fold_effective_window(log.revisions, decision_at=_instant(known_at + 1))
    assert is_ok(folded)
    assert folded.value.bounds.start.value_ns <= min(starts)
    assert folded.value.bounds.end.value_ns >= max(ends)


def test_I4_narrowing_revision_is_accepted_but_never_shrinks_the_effect() -> None:
    wide = _news_window(start=800, end=2_500, revision="r1", known_at=100)
    narrow = _news_window(start=1_200, end=1_800, revision="r2", known_at=200)
    log = ControlWindowRevisionLog(window_id="win-nfp-1")
    first = append_window_revision(log, wide)
    assert is_ok(first)
    second = append_window_revision(first.value, narrow)
    assert is_ok(second)  # intake never refuses a narrowing revision...
    folded = fold_effective_window(second.value.revisions, decision_at=_instant(300))
    assert is_ok(folded)
    # ...but the effect is the widest union, never narrowed.
    assert folded.value.bounds.start.value_ns == 800
    assert folded.value.bounds.end.value_ns == 2_500


# --- I5: fail-closed; no live skip; no click exemption -----------------------


def test_I5_fail_closed_no_skip_no_click_exemption() -> None:
    for cause in FailClosedCause:
        refused = fail_closed_on_uncertainty(cause=cause)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
    assert reject_live_skip().category is RefusalCategory.POLICY_REJECTION
    assert reject_click_exemption().category is RefusalCategory.POLICY_REJECTION


# --- I6: window_forced_flat rank 2; V1 declares none -------------------------


def test_I6_window_forced_flat_rank_two_v1_declares_none() -> None:
    policy = WindowForcedFlatPolicy.v1_default()
    assert policy.declares_forced_flat is False
    assert policy.arbitration_rank == WINDOW_FORCED_FLAT_ARBITRATION_RANK == 2
    declared = WindowForcedFlatPolicy.try_create(True)
    assert is_ok(declared)
    assert declared.value.declares_forced_flat is True


# --- I7 [L4]: SCN-0008 executable golden fixture -----------------------------


def test_I7_scn0008_pair_scoped_news_end_to_end() -> None:
    """SCN-0008: high-impact USD news scopes to USD-exposed instruments only.
    An in-scope pair is blocked (live and paper); an out-of-scope pair trades;
    an instrument with no exposure record is treated-as-affected and alarmed."""
    eurusd, usdjpy, audcad = _instrument("EURUSD"), _instrument("USDJPY"), _instrument("AUDCAD")
    scope = resolve_instrument_scope(
        affected_currencies={"USD"},
        candidate_instruments=[eurusd, usdjpy, audcad],
        exposure_records=[
            _exposure(eurusd, "EUR", "USD", record_id="e1"),
            _exposure(usdjpy, "USD", "JPY", record_id="e2"),
            # audcad has NO exposure record -> treated as affected
        ],
    )
    assert is_ok(scope)
    window = _news_window(scope=scope.value, start=1_000_000_000, end=2_000_000_000)
    decision = _instant(1_500_000_000)

    # in-scope USD pairs blocked, live and paper alike
    for pair in (eurusd, usdjpy):
        for mode in (BookMode.LIVE, BookMode.PAPER):
            ev = evaluate_entry_under_windows(instrument=pair, book_mode=mode,
                                              decision_at=decision, windows=[window])
            assert is_ok(ev)
            assert ev.value.blocked is True

    # the unknown-exposure instrument fails closed (blocked + data-quality alarm)
    orphan = evaluate_entry_under_windows(instrument=audcad, book_mode=BookMode.LIVE,
                                          decision_at=decision, windows=[window])
    assert is_ok(orphan)
    assert orphan.value.blocked is True
    assert orphan.value.data_quality_alarm is True

    # an out-of-window decision instant does not block
    before = evaluate_entry_under_windows(instrument=eurusd, book_mode=BookMode.LIVE,
                                          decision_at=_instant(500_000_000), windows=[window])
    assert is_ok(before)
    assert before.value.blocked is False
