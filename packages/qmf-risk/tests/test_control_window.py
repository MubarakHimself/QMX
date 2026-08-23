"""Story 10.9 — CT-31 protection windows: entries-only, instrument-scoped, fail-closed.

Covers the one control-window contract for news / daily_dead_zone /
session_handover_buffer, declared currency-exposure scope, widen-never-shrink
fold, fail-closed dispositions, and veto-path journaling (CT-31; DEC-0152;
SCN-0008).
"""

from __future__ import annotations

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
    CT31_CONTRACT_FORMAT_VERSION,
    NEWS_BLACKOUT_AFTER_VARIABLE,
    NEWS_BLACKOUT_BEFORE_VARIABLE,
    PROTECTION_WINDOW_VARIABLE_NAMES,
    RATIFIED_WINDOW_KINDS,
    WINDOW_EFFECT,
    WINDOW_FORCED_FLAT_ARBITRATION_RANK,
    WINDOW_TRIGGER_DISPOSITION,
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
    window_in_force_at,
)
from qmf.risk.paper import BookMode, TriggerDisposition


def _instant(ns: int = 1_000_000_000) -> Instant:
    result = Instant.try_create(ns)
    assert is_ok(result)
    return result.value


def _venue() -> VenueId:
    result = VenueId.try_create("ctrader")
    assert is_ok(result)
    return result.value


def _instrument(symbol: str = "EURUSD") -> Instrument:
    result = Instrument.try_create(_venue(), symbol)
    assert is_ok(result)
    return result.value


def _calendar() -> CalendarIdentity:
    result = CalendarIdentity.try_create("forex-17NY", "v3", "2024a")
    assert is_ok(result)
    return result.value


def _bounds(start_ns: int = 1_000_000_000, end_ns: int = 2_000_000_000) -> WindowBounds:
    result = WindowBounds.try_create(_instant(start_ns), _instant(end_ns))
    assert is_ok(result)
    return result.value


def _exposure(
    instrument: Instrument,
    *currencies: str,
    record_id: str = "exp-1",
) -> CurrencyExposureRecord:
    result = CurrencyExposureRecord.try_create(
        instrument, currencies, _instant(500), record_id
    )
    assert is_ok(result)
    return result.value


def _scope(
    *,
    currencies: tuple[str, ...] = ("USD",),
    instruments: tuple[Instrument, ...] | None = None,
    exposures: tuple[CurrencyExposureRecord, ...] | None = None,
) -> ResolvedInstrumentScope:
    candidates = instruments if instruments is not None else (_instrument("EURUSD"),)
    records = exposures if exposures is not None else (_exposure(candidates[0], *currencies),)
    result = resolve_instrument_scope(
        affected_currencies=currencies,
        candidate_instruments=candidates,
        exposure_records=records,
    )
    assert is_ok(result)
    return result.value


def _feed(
    *,
    revision: str = "r1",
    known_at_ns: int = 900_000_000,
    event_id: str = "nfp-2024-08",
) -> FeedQuadruple:
    result = FeedQuadruple.try_create(
        "calendar-feed",
        event_id,
        revision,
        _instant(known_at_ns),
    )
    assert is_ok(result)
    return result.value


def _news_window(
    *,
    start_ns: int = 1_000_000_000,
    end_ns: int = 2_000_000_000,
    revision: str = "r1",
    known_at_ns: int = 900_000_000,
    scope: ResolvedInstrumentScope | None = None,
    window_id: str = "win-nfp-1",
    enabled: bool = True,
) -> ControlWindowRecord:
    result = mint_control_window(
        _bounds(start_ns, end_ns),
        WindowKind.NEWS,
        scope if scope is not None else _scope(),
        "high-impact-news",
        _calendar(),
        window_id,
        feed_quadruple=_feed(revision=revision, known_at_ns=known_at_ns),
        enabled_by_book=enabled,
    )
    assert is_ok(result)
    return result.value


# --- vocabulary --------------------------------------------------------------


def test_ratified_kinds_are_exactly_three() -> None:
    assert {k.value for k in WindowKind} == {
        "news",
        "daily_dead_zone",
        "session_handover_buffer",
    }
    assert frozenset(WindowKind) == RATIFIED_WINDOW_KINDS


def test_effect_is_entries_only() -> None:
    assert WINDOW_EFFECT.value == "entries-only"
    assert is_ok(check_window_blocks_act(proposed_act=ProposedWindowAct.ENTRY))
    for act in (
        ProposedWindowAct.EXIT,
        ProposedWindowAct.AMEND_PROTECTION,
        ProposedWindowAct.PROTECTION_ACTION,
        ProposedWindowAct.RECORD_EVIDENCE,
    ):
        refused = check_window_blocks_act(proposed_act=act)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION


def test_window_trigger_disposition_blocks_paper() -> None:
    assert WINDOW_TRIGGER_DISPOSITION is TriggerDisposition.BLOCKS_PAPER


def test_configurable_variables_have_names_and_no_spine_values() -> None:
    assert NEWS_BLACKOUT_BEFORE_VARIABLE == "news_blackout_before"
    assert NEWS_BLACKOUT_AFTER_VARIABLE == "news_blackout_after"
    assert "daily_dead_zone_width" in PROTECTION_WINDOW_VARIABLE_NAMES
    assert "session_handover_buffer_anchor" in PROTECTION_WINDOW_VARIABLE_NAMES
    assert "window_forced_flat" in PROTECTION_WINDOW_VARIABLE_NAMES


# --- record shape ------------------------------------------------------------


def test_news_window_carries_two_instants_and_feed_quadruple() -> None:
    window = _news_window()
    assert window.window_kind is WindowKind.NEWS
    assert window.window_bounds.start.value_ns == 1_000_000_000
    assert window.window_bounds.end.value_ns == 2_000_000_000
    assert window.feed_quadruple is not None
    assert window.feed_quadruple.source == "calendar-feed"
    assert window.feed_quadruple.revision == "r1"
    assert window.anchor_side is None
    assert window.fp1_identity()["format_version"] == CT31_CONTRACT_FORMAT_VERSION
    assert "feed_quadruple" in window.fp1_identity()
    assert is_ok(window.fingerprint())


def test_session_handover_requires_anchor_side() -> None:
    missing = mint_control_window(
        _bounds(),
        WindowKind.SESSION_HANDOVER_BUFFER,
        _scope(),
        "handover",
        _calendar(),
        "win-ho-1",
    )
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.INVALID_INPUT

    ok = mint_control_window(
        _bounds(),
        WindowKind.SESSION_HANDOVER_BUFFER,
        _scope(),
        "handover",
        _calendar(),
        "win-ho-1",
        anchor_side=AnchorSide.BOTH,
    )
    assert is_ok(ok)
    assert ok.value.anchor_side is AnchorSide.BOTH
    assert ok.value.feed_quadruple is None
    assert "feed_quadruple" not in ok.value.fp1_identity()


def test_anchor_side_forbidden_on_non_handover_kinds() -> None:
    refused = mint_control_window(
        _bounds(),
        WindowKind.DAILY_DEAD_ZONE,
        _scope(),
        "dead-zone",
        _calendar(),
        "win-dz-1",
        anchor_side=AnchorSide.PRE_CLOSE,
    )
    assert is_refusal(refused)


def test_bounds_refuse_offset_shaped_inputs() -> None:
    refused = WindowBounds.try_create(15, 30)
    assert is_refusal(refused)
    reason = refused.context["reason"]
    assert isinstance(reason, str)
    assert "never an offset" in reason


# --- instrument scope --------------------------------------------------------


def test_scope_resolves_through_currency_exposure_not_symbol() -> None:
    eurusd = _instrument("EURUSD")
    gbpusd = _instrument("GBPUSD")
    xauusd = _instrument("XAUUSD")
    scope = resolve_instrument_scope(
        affected_currencies={"USD"},
        candidate_instruments=[eurusd, gbpusd, xauusd],
        exposure_records=[
            _exposure(eurusd, "EUR", "USD", record_id="e1"),
            _exposure(gbpusd, "GBP", "USD", record_id="e2"),
            # XAUUSD missing — treated as affected
        ],
    )
    assert is_ok(scope)
    assert eurusd in scope.value.instruments
    assert gbpusd in scope.value.instruments
    assert xauusd in scope.value.treated_as_affected_missing_exposure
    assert xauusd in scope.value.all_blocked()


def test_symbol_currency_parse_is_policy_rejection() -> None:
    refused = reject_symbol_currency_parse("EURUSD")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_multi_instrument_bot_blocked_only_in_scope() -> None:
    eurusd = _instrument("EURUSD")
    usdjpy = _instrument("USDJPY")
    # News affects EUR only — USDJPY out of scope.
    scope = resolve_instrument_scope(
        affected_currencies={"EUR"},
        candidate_instruments=[eurusd, usdjpy],
        exposure_records=[
            _exposure(eurusd, "EUR", "USD", record_id="e1"),
            _exposure(usdjpy, "USD", "JPY", record_id="e2"),
        ],
    )
    assert is_ok(scope)
    window = _news_window(scope=scope.value)
    decision = _instant(1_500_000_000)

    blocked = evaluate_entry_under_windows(
        instrument=eurusd,
        book_mode=BookMode.LIVE,
        decision_at=decision,
        windows=[window],
    )
    assert is_ok(blocked)
    assert blocked.value.blocked is True

    free = evaluate_entry_under_windows(
        instrument=usdjpy,
        book_mode=BookMode.LIVE,
        decision_at=decision,
        windows=[window],
    )
    assert is_ok(free)
    assert free.value.blocked is False


def test_missing_exposure_treated_as_affected_and_alarms() -> None:
    orphan = _instrument("UNKNOWN1")
    scope = resolve_instrument_scope(
        affected_currencies={"USD"},
        candidate_instruments=[orphan],
        exposure_records=[],
    )
    assert is_ok(scope)
    disposition = instrument_in_scope(scope.value, orphan)
    assert is_ok(disposition)
    assert (
        disposition.value
        is ScopeResolutionDisposition.TREATED_AS_AFFECTED_MISSING_EXPOSURE
    )
    window = _news_window(scope=scope.value)
    evaluation = evaluate_entry_under_windows(
        instrument=orphan,
        book_mode=BookMode.PAPER,
        decision_at=_instant(1_500_000_000),
        windows=[window],
    )
    assert is_ok(evaluation)
    assert evaluation.value.blocked is True
    assert evaluation.value.data_quality_alarm is True


# --- entries-only live and paper ---------------------------------------------


def test_window_blocks_live_and_paper_entries_alike() -> None:
    window = _news_window()
    instrument = _instrument()
    decision = _instant(1_500_000_000)
    for mode in (BookMode.LIVE, BookMode.PAPER):
        evaluation = evaluate_entry_under_windows(
            instrument=instrument,
            book_mode=mode,
            decision_at=decision,
            windows=[window],
        )
        assert is_ok(evaluation)
        assert evaluation.value.blocked is True
        assert evaluation.value.book_mode is mode


def test_window_does_not_block_exit() -> None:
    window = _news_window()
    refused = evaluate_entry_under_windows(
        instrument=_instrument(),
        book_mode=BookMode.LIVE,
        decision_at=_instant(1_500_000_000),
        windows=[window],
        proposed_act=ProposedWindowAct.EXIT,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_disabled_kind_does_not_block() -> None:
    window = _news_window(enabled=False)
    evaluation = evaluate_entry_under_windows(
        instrument=_instrument(),
        book_mode=BookMode.LIVE,
        decision_at=_instant(1_500_000_000),
        windows=[window],
    )
    assert is_ok(evaluation)
    assert evaluation.value.blocked is False
    in_force = window_in_force_at(window, _instant(1_500_000_000))
    assert is_ok(in_force)
    assert in_force.value is False


# --- widen-never-shrink ------------------------------------------------------


def test_widen_never_shrink_union_fold() -> None:
    # r1: [1000, 2000); r2 widens to [800, 2500); r3 narrows to [1200, 1800).
    r1 = _news_window(start_ns=1_000, end_ns=2_000, revision="r1", known_at_ns=100)
    r2 = _news_window(start_ns=800, end_ns=2_500, revision="r2", known_at_ns=200)
    r3 = _news_window(start_ns=1_200, end_ns=1_800, revision="r3", known_at_ns=300)

    log = ControlWindowRevisionLog(window_id="win-nfp-1")
    for revision in (r1, r2, r3):
        appended = append_window_revision(log, revision)
        assert is_ok(appended)
        log = appended.value

    # After all three known: union keeps the widest [800, 2500).
    folded = fold_effective_window(log.revisions, decision_at=_instant(400))
    assert is_ok(folded)
    assert folded.value.bounds.start.value_ns == 800
    assert folded.value.bounds.end.value_ns == 2_500
    assert folded.value.revision_count == 3

    # Before r2 known: only r1.
    early = fold_effective_window(log.revisions, decision_at=_instant(150))
    assert is_ok(early)
    assert early.value.bounds.start.value_ns == 1_000
    assert early.value.bounds.end.value_ns == 2_000
    assert early.value.revision_count == 1


def test_intake_never_refuses_narrowing_revision() -> None:
    wide = _news_window(start_ns=800, end_ns=2_500, revision="r1")
    narrow = _news_window(start_ns=1_200, end_ns=1_800, revision="r2")
    log = ControlWindowRevisionLog(window_id="win-nfp-1")
    first = append_window_revision(log, wide)
    assert is_ok(first)
    result = append_window_revision(first.value, narrow)
    assert is_ok(result)
    assert len(result.value.revisions) == 2


# --- fail closed -------------------------------------------------------------


def test_fail_closed_causes_are_policy_rejections() -> None:
    for cause in FailClosedCause:
        refused = fail_closed_on_uncertainty(cause=cause)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION


def test_no_live_skip_and_no_click_exemption() -> None:
    skip = reject_live_skip()
    assert is_refusal(skip)
    assert skip.category is RefusalCategory.POLICY_REJECTION
    click = reject_click_exemption()
    assert is_refusal(click)
    assert click.category is RefusalCategory.POLICY_REJECTION


# --- veto path and window_forced_flat ----------------------------------------


def test_veto_decision_carries_door_action_and_window_fingerprints() -> None:
    window = _news_window()
    instrument = _instrument()
    evaluation = evaluate_entry_under_windows(
        instrument=instrument,
        book_mode=BookMode.LIVE,
        decision_at=_instant(1_500_000_000),
        windows=[window],
    )
    assert is_ok(evaluation)
    action_fp = fingerprint({"class": "would-have-been-entry", "symbol": "EURUSD"})
    assert is_ok(action_fp)
    veto = mint_veto_decision(
        evaluation.value,
        instrument=instrument,
        would_have_been_action_fp=action_fp.value,
        decision_at=_instant(1_500_000_000),
    )
    assert is_ok(veto)
    assert veto.value.refusing_door == "control-window"
    assert veto.value.fp1_identity()["path"] == "veto"
    window_fp = window.fingerprint()
    assert is_ok(window_fp)
    assert veto.value.controlling_window_fp.value == window_fp.value.value


def test_window_forced_flat_v1_declares_none() -> None:
    policy = WindowForcedFlatPolicy.v1_default()
    assert policy.declares_forced_flat is False
    assert policy.arbitration_rank == WINDOW_FORCED_FLAT_ARBITRATION_RANK == 2
    declared = WindowForcedFlatPolicy.try_create(True)
    assert is_ok(declared)
    assert declared.value.declares_forced_flat is True
