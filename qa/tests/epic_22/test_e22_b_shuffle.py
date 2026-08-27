"""Epic 22 · Story 22.2 — Monte Carlo trade-shuffle (sequence-risk mode).

Independent L3 acceptance tests T22-310..314. A shuffle re-orders the realised CT-29
trades and re-accumulates the equity path with exact-integer money math, stays
procedure-ephemeral (world=replay), is per-scenario reproducible, and writes its
summary as chart-series data with no verdict. Every test names its counter-case.
"""

from __future__ import annotations

from conftest import (
    assert_ct04_refusal,
    instant,
    interval,
    is_exact_quantity,
    is_ok,
    is_refusal,
    unwrap,
    usd,
)

from qmf.core.exact import Money
from qmf.core.fingerprint import World
from qmf.core.refusal import RefusalCategory

from qmb.robustness import (
    SEED_DERIVATION_RULE,
    run_trade_shuffle,
    scenario_seed,
)
from qmb.results.measures import ClosedTrade


def _trades():
    return [
        unwrap(ClosedTrade.try_create(usd(500), usd(10), "long", instant(30)), "t0"),
        unwrap(ClosedTrade.try_create(usd(-300), usd(10), "short", instant(90)), "t1"),
        unwrap(ClosedTrade.try_create(usd(200), usd(10), "long", instant(150)), "t2"),
        unwrap(ClosedTrade.try_create(usd(-100), usd(10), "long", instant(300)), "t3"),
        unwrap(ClosedTrade.try_create(usd(400), usd(10), "short", instant(400)), "t4"),
    ]


def _run(**overrides):
    kwargs = dict(
        trades=_trades(),
        starting_capital=usd(100_000),
        period=interval(0, 400),
        base_seed=7,
        metrics=["net_profit", "max_drawdown"],
        scenario_count=24,
    )
    kwargs.update(overrides)
    return run_trade_shuffle(**kwargs)


# --- T22-310 (R-001: re-orders CT-29 trades; exact-integer equity; no float) P1 ---


def test_t22_310_shuffle_permutes_pnls_with_exact_integer_money():
    """The shuffle is a permutation of the realised P&Ls, re-accumulated in exact Money.

    Counter-case: a resample-with-replacement would make the order-invariant net_profit
    vary across scenarios; a float equity path would leave non-exact scenario values.
    We observe net_profit is invariant (one distinct value), a path-dependent metric
    varies, and every scenario magnitude is an exact quantity (Money/ExactRational).
    """
    result = unwrap(_run(), "shuffle")
    net = result.metric_named("net_profit")
    draw = result.metric_named("max_drawdown")
    assert net is not None and draw is not None

    net_values = {v.as_fraction() for v in net.distribution.values}
    assert len(net_values) == 1, "net_profit varied — the shuffle is not an order-only permutation"
    draw_values = {v.as_fraction() for v in draw.distribution.values}
    assert len(draw_values) > 1, "max_drawdown never moved — ordering had no effect (not a shuffle)"

    for metric in (net, draw):
        for value in metric.distribution.values:
            assert is_exact_quantity(value), f"non-exact scenario value {value!r} on the equity path"


# --- T22-311 (procedure-ephemeral: no synthetic series; world=replay; seed in label) P0 ---


def test_t22_311_shuffle_stays_world_replay_and_stamps_procedure_and_seed():
    """The shuffle mints no synthetic series: the run stays world=replay, seed in the label.

    Counter-case: a world other than ``replay``, or a result label missing the procedure
    identity or base seed, would break the B-7 procedure-ephemeral provenance.
    """
    result = unwrap(_run(base_seed=42), "shuffle")
    assert result.world == World.REPLAY.value
    label = result.result_label()
    assert label["world"] == World.REPLAY.value
    assert label["procedure"] == result.procedure
    assert label["base_seed"] == 42
    assert label["provenance_kind"] == "procedure-ephemeral"


# --- T22-312 (reproducibility: seed=base+index; provenance; re-run bit-for-bit) P0 ---


def test_t22_312_seed_is_base_plus_index_and_run_reproduces_bit_for_bit():
    """Scenario seeds are ``base + index`` and a re-run reproduces the fingerprint.

    Counter-case: a non-additive derivation would make scenario_seed(10,3) != 13; a
    hidden RNG or clock would make the re-run fingerprint differ.
    """
    assert unwrap(scenario_seed(10, 3), "seed") == 13
    assert unwrap(scenario_seed(10, 0), "seed0") == 10
    assert unwrap(scenario_seed(10, 3), "seed") != 10  # discriminates a constant derivation

    first = unwrap(_run(), "first")
    second = unwrap(_run(), "second")
    assert unwrap(first.fingerprint(), "fp1").value == unwrap(second.fingerprint(), "fp2").value


def test_t22_312_provenance_records_rng_seed_rule_count_and_window_bounds():
    """The result records RNG family, base seed, the seed rule, count, and window bounds.

    Counter-case: a provenance whose data-window bounds do not equal the supplied
    period, or whose seed-derivation rule is not ``base_seed + scenario_index``.
    """
    period = interval(0, 400)
    result = unwrap(_run(period=period, base_seed=7, scenario_count=24), "shuffle")
    prov = result.provenance
    assert prov.base_seed == 7
    assert prov.scenario_count == 24
    assert prov.seed_derivation_rule == SEED_DERIVATION_RULE == "base_seed + scenario_index"
    assert prov.rng_family  # a non-empty declared family
    assert prov.data_window_start_ns == period.start.value_ns
    assert prov.data_window_end_ns == period.end.value_ns


# --- T22-313 (per-metric summary as chart-series DATA, never images; no verdict) P1 ---


def test_t22_313_metric_distributions_are_chart_series_data_not_images():
    """Each metric distribution is written as chart-series DATA, never an image, no verdict.

    Counter-case: an image/png/svg/base64 payload key, or an emitted verdict flag, would
    breach FR-043 (series data, never images) and the no-verdict rule.
    """
    result = unwrap(_run(), "shuffle")
    series = result.chart_series()
    assert series, "no chart series emitted"
    banned = ("image", "png", "svg", "base64", "figure", "bitmap")
    for chart in series:
        keys = {str(k).lower() for k in chart}
        assert "values" in keys, f"chart series carries no data array: {keys}"
        assert not any(any(b in k for b in banned) for k in keys), f"image payload leaked: {keys}"
    for metric in result.metrics:
        assert metric.summary.emits_verdict is False
        assert metric.fp1_identity()["emits_image_payload"] is False


# --- T22-314 (scenario count UI-editable configurable; MC-1000 not baked) P1 --


def test_t22_314_scenario_count_has_no_ratified_value_and_no_baked_default():
    """The scenario count is required from config/argument — MC-1000 is not baked.

    Counter-case: a run that succeeds with neither config nor an explicit count would
    prove a baked default (e.g. MC-1000).
    """
    refused = run_trade_shuffle(
        trades=_trades(),
        starting_capital=usd(100_000),
        period=interval(0, 400),
        base_seed=7,
        metrics=["net_profit"],
    )
    assert_ct04_refusal(refused, RefusalCategory.INVALID_INPUT, what="shuffle with no scenario count")

    # Supplied via the resolved run-config key resolves normally.
    from qmb.robustness import SCENARIO_COUNT_KEY

    via_config = run_trade_shuffle(
        trades=_trades(),
        starting_capital=usd(100_000),
        period=interval(0, 400),
        base_seed=7,
        metrics=["net_profit"],
        config={SCENARIO_COUNT_KEY: 12},
    )
    assert is_ok(via_config)
    assert unwrap(via_config, "cfg").provenance.scenario_count == 12
