"""Epic 23 · Story 23.1 — ``qmb data generate``, config-selected adapters, money/time/OHLC.

Independent L3 acceptance tests T23-301..305. Each names the concrete counter-case
that would make it FAIL. Source is read-only evidence; a failing test is a FINDING,
never fixed by editing source or weakening the assertion.
"""

from __future__ import annotations

import json

from conftest import (
    BASE_NS,
    DAY_NS,
    GappedCalendar,
    assert_ct04_refusal,
    bb_resources,
    gbm_resources,
    gn_resources,
    gr_resources,
    is_ok,
    is_refusal,
    source_rows,
    unwrap,
)

import money_path_scan as mp
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory
from qmb.data import (
    GENERATOR_PROCESSES,
    SOURCE_DATASET_NONE,
    generate,
    resolve_generator_config,
)


# --- T23-301 (P1, R1/B-3/AR-14): exactly-one-process, fingerprinted artifact --


def test_t23_301_config_selects_one_process_and_is_qmf_core_fingerprinted(tmp_path) -> None:
    """A resolved config selects exactly one v1 process; its fp1 is the qmf-core canonical
    fingerprint and the artifact is recorded alongside the run.

    Counter-case that FAILS this test: the menu is not exactly four processes; the config
    fingerprint is not the qmf-core ``fp1`` of its identity content; or two distinct configs
    (different seed) collide to the same id.
    """
    assert len(GENERATOR_PROCESSES) == 4  # the v1 menu is exactly four (R2)

    resolved = resolve_generator_config(gbm_resources(seed=11))
    config = unwrap(resolved, "resolved config")
    assert config.process in GENERATOR_PROCESSES
    # exactly-one selection: the process is a single menu token, not a set/list.
    assert isinstance(config.process, str)

    # fp1 identity computed ONLY by the qmf-core canonical fingerprint (AR-14):
    canonical = fingerprint(config.fp1_identity())
    derived = config.fingerprint()
    assert is_ok(canonical) and is_ok(derived)
    assert derived.value.value == canonical.value.value
    assert isinstance(derived.value.value, str) and derived.value.value != ""

    # a different config (seed changed) is a different content-addressed id.
    other = unwrap(resolve_generator_config(gbm_resources(seed=12)), "other config")
    assert unwrap(other.fingerprint()).value != derived.value.value

    # the config is materialized as a first-class artifact recorded alongside the run.
    receipt = unwrap(generate(gbm_resources(seed=11), output_root=tmp_path), "generate")
    assert receipt.config_artifact_written is True
    written = tmp_path / receipt.config_artifact_path
    assert written.is_file()
    body = json.loads(written.read_text(encoding="utf-8"))
    assert body["process"] == config.process
    assert body["seed"] == 11
    assert receipt.config_fingerprint == derived.value.value


# --- T23-302 (P1, R2/CT-10): source-dataset citation gate --------------------


def test_t23_302_history_seeded_requires_source_dataset_gbm_records_none() -> None:
    """A history-seeded process must cite a source-dataset id; from-scratch gbm records ``none``.

    Counter-case that FAILS: a history-seeded config with no citation resolves anyway; or a
    gbm config that cites a dataset is accepted; or gbm's recorded id is not ``none``.
    """
    # history-seeded (block-bootstrap) WITHOUT a citation -> RETURNED refusal.
    no_cite = bb_resources()
    no_cite.pop("source_dataset_id", None)
    assert_ct04_refusal(
        resolve_generator_config(no_cite),
        RefusalCategory.INVALID_INPUT,
        what="history-seeded without source-dataset id",
    )

    # from-scratch gbm needs none and records SOURCE_DATASET_NONE.
    gbm = unwrap(resolve_generator_config(gbm_resources()), "gbm config")
    assert gbm.source_dataset_id == SOURCE_DATASET_NONE

    # a gbm config that DOES cite a source dataset is refused (it needs none).
    gbm_cited = gbm_resources(source_dataset_id="SIM:EURUSD:1d:mid")
    assert_ct04_refusal(
        resolve_generator_config(gbm_cited),
        RefusalCategory.INVALID_INPUT,
        what="from-scratch gbm citing a source dataset",
    )

    # discriminator: a history-seeded config WITH a citation resolves.
    ok_cite = unwrap(resolve_generator_config(bb_resources()), "cited history-seeded")
    assert ok_cite.source_dataset_id == "SIM:EURUSD:1d:mid"


# --- T23-303 (P0, R6/AR-15): money-path integrity ----------------------------


def test_t23_303_money_path_scanner_clean_over_qmb_data() -> None:
    """The NFR-02 money-path float scanner flags no binary float on the money path in
    ``qmb/src/qmb/data`` — every price is exact and any float crosses a named rounding-declared
    boundary.

    Counter-case that FAILS: any file under ``qmb/data`` carries a binary float reaching a
    money-path value without a named ``from_float`` crossing.
    """
    data_dir = mp.ROOT / "qmb" / "src" / "qmb" / "data"
    files = sorted(data_dir.glob("*.py"))
    assert files, "expected qmb/data source files to scan"
    findings: list = []
    for path in files:
        findings.extend(mp.scan_file(path, root=mp.ROOT))
    assert findings == [], f"money-path float violations in qmb/data: {findings!r}"


def test_t23_303_emitted_prices_exact_int_quantized_to_tick_and_positive() -> None:
    """Every emitted price is an exact scaled integer quantized to the instrument tick and
    strictly positive; there is no binary float on the produced money path.

    Counter-case that FAILS: a produced price is a float, is not a multiple of the tick, or is
    non-positive.
    """
    tick = 25
    receipt = unwrap(generate(bb_resources(tick_size=tick, count=6), source_series=source_rows()), "generate")
    assert receipt.bar_count == 6
    for bar in receipt.bars:
        for value in (bar.open, bar.high, bar.low, bar.close):
            assert isinstance(value, int) and not isinstance(value, bool)
            assert value > 0
            assert value % tick == 0, f"price {value} is not quantized to tick {tick}"
        # completed-bar OHLC integrity holds on integers.
        assert bar.low <= bar.open <= bar.high
        assert bar.low <= bar.close <= bar.high


def test_t23_303_timestamps_int64_utc_ns_on_market_hours_grid_weekend_gap() -> None:
    """Timestamps are int64 UTC-ns and the grid honors an injected market-hours calendar's
    weekend gap — no bar falls inside a closed span.

    Counter-case that FAILS: a produced instant is not an int, is out of ``[start, end)``, or
    lands inside the injected closed (weekend) span.
    """
    start = BASE_NS
    end = BASE_NS + 6 * DAY_NS
    gap_open = BASE_NS + 2 * DAY_NS
    gap_close = BASE_NS + 4 * DAY_NS
    calendar = GappedCalendar([(start, gap_open), (gap_close, end)])
    res = gbm_resources(count=6, start_ns=start, end_ns=end)
    receipt = unwrap(generate(res, calendar=calendar), "generate over gapped calendar")
    assert receipt.bar_count > 0
    stamps = [bar.instant_ns for bar in receipt.bars]
    for ns in stamps:
        assert isinstance(ns, int) and not isinstance(ns, bool)
        assert start <= ns < end
        assert not (gap_open <= ns < gap_close), f"instant {ns} lands inside the closed weekend gap"
    # bars fall on both open sessions and none in the gap.
    assert any(ns < gap_open for ns in stamps)
    assert any(ns >= gap_close for ns in stamps)
    assert stamps == sorted(stamps)


def test_t23_303_declared_rounding_mode_governs_the_named_conversion() -> None:
    """The single float->integer money crossing honors the config's declared rounding mode;
    FLOOR and CEILING produce different tick-quantized prices for the same seed.

    Counter-case that FAILS: the declared rounding mode has no effect on the produced prices
    (the named AD-7 boundary is not actually applied under the declared mode).
    """
    common = dict(count=6, tick_size=100, seed=3, volatility="0.05")
    floor = unwrap(generate(gbm_resources(rounding_mode="floor", **common)), "floor run")
    ceil = unwrap(generate(gbm_resources(rounding_mode="ceiling", **common)), "ceiling run")
    floor_closes = tuple(b.close for b in floor.bars)
    ceil_closes = tuple(b.close for b in ceil.bars)
    # every price is still tick-quantized under each mode ...
    for closes in (floor_closes, ceil_closes):
        assert all(c % 100 == 0 for c in closes)
    # ... and the two declared modes are not identical (the boundary is really applied).
    assert floor_closes != ceil_closes


# --- T23-304 (P0, R6/R8): OHLC integrity -> typed refusal, never corrected ----


def test_t23_304_ohlc_gate_refuses_violation_never_silently_corrects() -> None:
    """A completed bar that violates ``low <= open,close <= high`` or positivity RETURNS a typed
    ``invalid input``; a valid bar is accepted — the gate never silently corrects.

    Counter-case that FAILS: a high-below-body bar is silently repaired into an ``Ok`` bar, or
    a non-positive price is accepted.
    """
    from qmb.data import SyntheticBar

    # high below the body (high < close) -> refused, RETURNED, never corrected.
    bad_high = SyntheticBar.try_create(BASE_NS, 100, 90, 80, 95, 5)
    ref = assert_ct04_refusal(bad_high, RefusalCategory.INVALID_INPUT, what="high-below-body bar")
    assert ref.context.get("field") == "high"

    # low above the body (low > open) -> refused.
    bad_low = SyntheticBar.try_create(BASE_NS, 100, 130, 110, 120, 5)
    assert_ct04_refusal(bad_low, RefusalCategory.INVALID_INPUT, what="low-above-body bar")

    # non-positive price -> refused.
    bad_pos = SyntheticBar.try_create(BASE_NS, 0, 10, 0, 5, 5)
    assert_ct04_refusal(bad_pos, RefusalCategory.INVALID_INPUT, what="non-positive price")

    # discriminator: a valid bar is accepted unchanged (no silent mutation).
    good = SyntheticBar.try_create(BASE_NS, 100, 130, 80, 110, 5)
    bar = unwrap(good, "valid bar")
    assert (bar.open, bar.high, bar.low, bar.close) == (100, 130, 80, 110)


# --- T23-305 (P1, R2/R8/B-1): menu + mismatch refusal, config-selected --------


def test_t23_305_unknown_process_and_instrument_mismatch_refuse_never_drop() -> None:
    """An unknown process is ``unsupported capability``; a process x instrument mismatch (an
    equity-only corporate action on a forex CFD) is a category-appropriate refusal; never a
    silent drop.

    Counter-case that FAILS: a deferred/unknown process is silently substituted or accepted, or
    an equity-only event on a forex instrument is silently dropped.
    """
    # deferred open-question process -> unsupported capability.
    assert_ct04_refusal(
        resolve_generator_config(gbm_resources(process="regime-switching")),
        RefusalCategory.UNSUPPORTED_CAPABILITY,
        what="deferred regime-switching process",
    )
    # an entirely unknown process token -> unsupported capability.
    assert_ct04_refusal(
        resolve_generator_config(gbm_resources(process="banana")),
        RefusalCategory.UNSUPPORTED_CAPABILITY,
        what="unknown process token",
    )
    # a corporate-action event on a forex-CFD instrument -> category-appropriate refusal.
    assert_ct04_refusal(
        resolve_generator_config(gbm_resources(events=["corporate-action"])),
        RefusalCategory.INVALID_INPUT,
        what="corporate-action on a forex CFD",
    )


def test_t23_305_all_four_processes_are_config_selected_by_the_same_entry_point() -> None:
    """Each of the four v1 processes is produced by the SAME ``generate`` entry point selected
    purely by config (the library is never swapped, B-1).

    Counter-case that FAILS: a menu process cannot be selected by config alone through the one
    generate function.
    """
    src = source_rows()
    runs = {
        "block-bootstrap": generate(bb_resources(), source_series=src),
        "gaussian-resample": generate(gr_resources(), source_series=src),
        "gaussian-noise": generate(gn_resources(), source_series=src),
        "gbm": generate(gbm_resources()),
    }
    for process, result in runs.items():
        assert is_ok(result), f"{process}: expected Ok, got {result!r}"
        assert result.value.process == process
        # the same library surface produced every process (one entry point, config-selected).
        assert result.value.command == "generate"
