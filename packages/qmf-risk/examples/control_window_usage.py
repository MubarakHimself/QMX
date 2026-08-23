"""Reference usage — CT-31 protection windows (SCN-0008).

Executable::

    python packages/qmf-risk/examples/control_window_usage.py

Shows a news window as two instants with feed quadruple, declared
currency-exposure scope (never symbol-parsed), entries-only blocking live and
paper alike, widen-never-shrink fold, fail-closed, and veto-path journaling.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    Instant,
    Instrument,
    RefusalCategory,
    Result,
    VenueId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.risk.control_window import (
    AnchorSide,
    ControlWindowRevisionLog,
    CurrencyExposureRecord,
    FailClosedCause,
    FeedQuadruple,
    ProposedWindowAct,
    WindowBounds,
    WindowForcedFlatPolicy,
    WindowKind,
    append_window_revision,
    check_window_blocks_act,
    evaluate_entry_under_windows,
    fail_closed_on_uncertainty,
    fold_effective_window,
    mint_control_window,
    mint_veto_decision,
    reject_live_skip,
    reject_symbol_currency_parse,
    resolve_instrument_scope,
)
from qmf.risk.paper import BookMode

T = TypeVar("T")


def _unwrap(result: Result[T], message: str) -> T:
    if is_ok(result):
        return result.value
    raise RuntimeError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _instant(ns: int) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant mint failed")


def main() -> None:
    venue = _unwrap(VenueId.try_create("ctrader"), "venue mint failed")
    eurusd = _unwrap(Instrument.try_create(venue, "EURUSD"), "EURUSD mint failed")
    usdjpy = _unwrap(Instrument.try_create(venue, "USDJPY"), "USDJPY mint failed")
    calendar = _unwrap(
        CalendarIdentity.try_create("forex-17NY", "v3", "2024a"),
        "calendar mint failed",
    )

    # Scope is declared through currency-exposure records — never parsed.
    parse = reject_symbol_currency_parse("EURUSD")
    _require(is_refusal(parse), "symbol parse must be refused")
    print("instrument scope: symbol currency parse refused (policy rejection)")

    eurusd_exp = _unwrap(
        CurrencyExposureRecord.try_create(eurusd, ["EUR", "USD"], _instant(100), "exp-eu"),
        "EURUSD exposure failed",
    )
    usdjpy_exp = _unwrap(
        CurrencyExposureRecord.try_create(usdjpy, ["USD", "JPY"], _instant(100), "exp-uj"),
        "USDJPY exposure failed",
    )
    # High-impact USD news — both pair instruments in scope via USD exposure.
    scope = _unwrap(
        resolve_instrument_scope(
            affected_currencies=["USD"],
            candidate_instruments=[eurusd, usdjpy],
            exposure_records=[eurusd_exp, usdjpy_exp],
        ),
        "scope resolve failed",
    )
    _require(eurusd in scope.instruments and usdjpy in scope.instruments, "USD scope")
    print(f"resolved scope instruments: {sorted(i.symbol for i in scope.instruments)}")

    bounds = _unwrap(
        WindowBounds.try_create(_instant(1_000), _instant(2_000)),
        "bounds mint failed",
    )
    feed = _unwrap(
        FeedQuadruple.try_create("calendar-feed", "nfp-2024-08", "r1", _instant(500)),
        "feed quadruple failed",
    )
    window = _unwrap(
        mint_control_window(
            bounds,
            WindowKind.NEWS,
            scope,
            "high-impact-news",
            calendar,
            "win-nfp-1",
            feed_quadruple=feed,
            provider_impact_label="high",
        ),
        "news window mint failed",
    )
    _require(window.feed_quadruple is not None, "feed quadruple present")
    print(
        "news window: two instants "
        f"[{window.window_bounds.start.value_ns}, {window.window_bounds.end.value_ns}) "
        f"kind={window.window_kind.value} format={window.fp1_identity()['format_version']}"
    )

    # Entries-only: exit may not be blocked by a window.
    exit_gate = check_window_blocks_act(proposed_act=ProposedWindowAct.EXIT)
    if not is_refusal(exit_gate):
        raise RuntimeError("exit must not be window-blocked")
    _require(
        exit_gate.category is RefusalCategory.POLICY_REJECTION,
        "entries-only is a policy rejection",
    )
    print("entries-only: exit block refused (policy rejection)")

    # Live and paper entries alike are blocked on in-scope instruments.
    decision = _instant(1_500)
    for mode in (BookMode.LIVE, BookMode.PAPER):
        evaluation = _unwrap(
            evaluate_entry_under_windows(
                instrument=eurusd,
                book_mode=mode,
                decision_at=decision,
                windows=[window],
            ),
            f"evaluation under {mode.value} failed",
        )
        _require(evaluation.blocked is True, f"{mode.value} entry must block")
        print(f"blocked entry under book_mode={mode.value}")

    action_fp = _unwrap(
        fingerprint({"class": "would-have-been-entry", "symbol": "EURUSD"}),
        "action fingerprint failed",
    )
    live_eval = _unwrap(
        evaluate_entry_under_windows(
            instrument=eurusd,
            book_mode=BookMode.LIVE,
            decision_at=decision,
            windows=[window],
        ),
        "live evaluation failed",
    )
    veto = _unwrap(
        mint_veto_decision(
            live_eval,
            instrument=eurusd,
            would_have_been_action_fp=action_fp,
            decision_at=decision,
        ),
        "veto mint failed",
    )
    print(
        f"veto path: door={veto.refusing_door} path={veto.fp1_identity()['path']} "
        f"mode={veto.book_mode.value}"
    )

    # Widen-never-shrink: r2 widens, r3 narrows — fold keeps the union.
    r2_bounds = _unwrap(
        WindowBounds.try_create(_instant(800), _instant(2_500)),
        "r2 bounds failed",
    )
    r2 = _unwrap(
        mint_control_window(
            r2_bounds,
            WindowKind.NEWS,
            scope,
            "high-impact-news",
            calendar,
            "win-nfp-1",
            feed_quadruple=_unwrap(
                FeedQuadruple.try_create("calendar-feed", "nfp-2024-08", "r2", _instant(600)),
                "r2 feed failed",
            ),
        ),
        "r2 mint failed",
    )
    r3_bounds = _unwrap(
        WindowBounds.try_create(_instant(1_200), _instant(1_800)),
        "r3 bounds failed",
    )
    r3 = _unwrap(
        mint_control_window(
            r3_bounds,
            WindowKind.NEWS,
            scope,
            "high-impact-news",
            calendar,
            "win-nfp-1",
            feed_quadruple=_unwrap(
                FeedQuadruple.try_create("calendar-feed", "nfp-2024-08", "r3", _instant(700)),
                "r3 feed failed",
            ),
        ),
        "r3 mint failed",
    )
    log = ControlWindowRevisionLog(window_id="win-nfp-1")
    log = _unwrap(append_window_revision(log, window), "append r1 failed")
    log = _unwrap(append_window_revision(log, r2), "append r2 failed")
    log = _unwrap(append_window_revision(log, r3), "append r3 failed")
    effective = _unwrap(
        fold_effective_window(log.revisions, decision_at=_instant(800)),
        "effective fold failed",
    )
    _require(effective.bounds.start.value_ns == 800, "widen start")
    _require(effective.bounds.end.value_ns == 2_500, "widen end")
    print(
        "widen-never-shrink fold: "
        f"[{effective.bounds.start.value_ns}, {effective.bounds.end.value_ns}) "
        f"from {effective.revision_count} revisions"
    )

    # Fail closed — no live skip.
    closed = fail_closed_on_uncertainty(cause=FailClosedCause.UNKNOWN_COVERAGE)
    _require(is_refusal(closed), "unknown coverage must fail closed")
    _require(is_refusal(reject_live_skip()), "no live skip button")
    print("fail closed: unknown_coverage blocks; no live skip button")

    # session_handover_buffer declares anchor side; V1 window_forced_flat is none.
    handover = _unwrap(
        mint_control_window(
            bounds,
            WindowKind.SESSION_HANDOVER_BUFFER,
            scope,
            "london-ny-handover",
            calendar,
            "win-ho-1",
            anchor_side=AnchorSide.BOTH,
        ),
        "handover window mint failed",
    )
    anchor = handover.anchor_side
    if anchor is not AnchorSide.BOTH:
        raise RuntimeError("anchor side mandatory")
    policy = WindowForcedFlatPolicy.v1_default()
    _require(policy.declares_forced_flat is False, "V1 declares none")
    print(
        f"handover kind={handover.window_kind.value} anchor={anchor.value}; "
        f"window_forced_flat V1 declares_none rank={policy.arbitration_rank}"
    )


if __name__ == "__main__":
    main()
