"""Epic 22 · Story 22.1 — module foundation, return-space float carve-out, summary.

Independent L3 acceptance/contract tests for T22-301..309, the NFR-02 money-path
float-scanner check (T22-304), and the F-22-01 overflow regression pin (T22-PIN-01).
Each test names the concrete counter-case that would make it fail. Source is
read-only evidence; a failing test is a FINDING, never fixed by editing source.
"""

from __future__ import annotations

import math
import sys
from fractions import Fraction

from conftest import (
    WORKTREE_ROOT,
    assert_ct04_refusal,
    instr,  # noqa: F401  (re-exported session fixture)
    interval,
    is_ok,
    is_refusal,
    price,
    unwrap,
    usd,
)

from qmf.core.exact import Money, RoundingMode
from qmf.core.refusal import RefusalCategory
from qmf.core.fingerprint import World

import qmb.robustness as rob
from qmb.robustness import (
    DIRECTION_HIGHER_IS_BETTER,
    DIRECTION_LOWER_IS_BETTER,
    RETURN_SPACE_STAT_SCALE,
    carve_return_statistic,
    procedure_contract,
    reenter_money_path,
    refuse_edge_claim,
    refuse_live_money_gate,
    refuse_pass_fail_verdict,
    require_configurable,
    require_positive_int,
    run_candle_perturbation,
    run_trade_shuffle,
    summarize_distribution,
)
from qmb.results.measures import ClosedTrade


# --- small shared builders for the two ladder procedures used as purity probes ---


def _trades():
    return [
        unwrap(ClosedTrade.try_create(usd(500), usd(10), "long", _inst(30)), "t0"),
        unwrap(ClosedTrade.try_create(usd(-300), usd(10), "short", _inst(90)), "t1"),
        unwrap(ClosedTrade.try_create(usd(200), usd(10), "long", _inst(150)), "t2"),
        unwrap(ClosedTrade.try_create(usd(-100), usd(10), "long", _inst(400)), "t3"),
    ]


def _inst(day):
    from conftest import instant

    return instant(day)


def _shuffle():
    return run_trade_shuffle(
        trades=_trades(),
        starting_capital=usd(100_000),
        period=interval(0, 400),
        base_seed=7,
        metrics=["net_profit", "max_drawdown"],
        scenario_count=16,
    )


def _candles(instrument=None):
    from qmb.robustness import Candle

    return [
        unwrap(Candle.try_create(_inst(i), 100 + i, 110 + i, 90 + i, 105 + i), f"c{i}")
        for i in range(8)
    ]


# --- T22-301 (B-4 purity; no ledger/log; no module-global mutable state) P1 ---


def test_t22_301_procedure_returns_and_holds_no_global_mutable_state():
    """A ladder procedure RETURNS its result and holds no module-global mutable state.

    Counter-case: if the module accumulated per-call state in a module global, a
    second identical call — or a call interleaved with a *different* procedure —
    would produce a different fingerprint. We observe determinism across repeats and
    across an interleaved procedure, so a hidden accumulator is falsified.
    """
    first = _shuffle()
    assert is_ok(first), f"the procedure must RETURN its result, got {first!r}"
    fp1 = unwrap(unwrap(first, "first").fingerprint(), "fp1")

    # Interleave an unrelated ladder procedure that also runs stochastically.
    other = run_candle_perturbation(candles=_candles(), base_seed=3, block_length=3, scenario_count=5)
    assert is_ok(other)

    second = _shuffle()
    fp2 = unwrap(unwrap(second, "second").fingerprint(), "fp2")
    assert fp1.value == fp2.value, "repeated/interleaved calls diverged — module-global state leaked"


def test_t22_301_module_scope_has_no_bare_mutable_containers():
    """No module in the package binds a bare mutable container at module scope.

    Counter-case: a module-level ``list``/``dict``/``set`` (not a Final tuple/frozenset)
    would be shared mutable state. We scan the runtime module objects' public globals.
    """
    import qmb.robustness.carveout as m_carve
    import qmb.robustness.contract as m_contract
    import qmb.robustness.perturbation as m_pert
    import qmb.robustness.shuffle as m_shuf
    import qmb.robustness.significance as m_sig
    import qmb.robustness.summary as m_sum
    import qmb.robustness.walkforward as m_wf

    for module in (m_carve, m_contract, m_sum, m_shuf, m_pert, m_sig, m_wf):
        for name, value in vars(module).items():
            if name.startswith("_") or name.isupper():
                continue
            assert not isinstance(value, (list, dict, set, bytearray)), (
                f"{module.__name__}.{name} is a module-global mutable {type(value).__name__}"
            )


# --- T22-302 (versioned AD-5 integer contract; roster closed) P1 -------------


def test_t22_302_contract_stamps_integer_format_version_one():
    """Each procedure contract stamps an AD-5 *integer* format version (v1) in identity.

    Counter-case: a float/SemVer-shaped version, or a version absent from identity,
    would break the "old ledger entries stay readable forever" integer stamp.
    """
    contract = unwrap(procedure_contract("walk-forward"), "walk-forward contract")
    version = contract.contract_format_version
    assert isinstance(version, int) and not isinstance(version, bool)
    assert version == 1
    identity = contract.fp1_identity()
    assert identity["contract_format_version"] == 1


def test_t22_302_unknown_procedure_is_returned_invalid_refusal():
    """A procedure key outside the closed four-rung roster is a RETURNED invalid refusal.

    Counter-case: a best-effort contract for an unknown rung (an Ok) would let an
    uncontracted procedure ship.
    """
    result = procedure_contract("kitchen-sink")
    assert_ct04_refusal(result, RefusalCategory.INVALID_INPUT, what="unknown procedure")


# --- T22-303 (R-001: return-space float carve-out boundary) P0 ---------------


def test_t22_303_money_never_crosses_the_carve_as_raw_value():
    """P&L / equity Money never enters the return-space carve-out as a raw value.

    Counter-case: if ``carve_return_statistic`` accepted exact Money, the money path
    could be laundered through the statistic boundary. It must refuse raw Money.
    """
    result = carve_return_statistic("pnl", usd(12_345))
    assert_ct04_refusal(result, RefusalCategory.INVALID_INPUT, what="raw Money into carve-out")


def test_t22_303_statistic_is_stored_as_scaled_rational_not_binary_float():
    """A carved statistic is stored as an exact scaled rational under the fixed contract.

    Counter-case: a raw binary float would leave a power-of-two denominator that does
    NOT divide 10**scale. We prove the discriminator: Fraction(0.1) (den 2**55) does
    not divide 10**12, while the carved value's denominator does.
    """
    ten_scale = 10**RETURN_SPACE_STAT_SCALE
    # Discriminator sanity: a raw binary float leaks a non-dividing denominator.
    raw_float_den = Fraction(0.1).denominator
    assert ten_scale % raw_float_den != 0

    for value in (1.5, 0.1, math.log(1.1), -2.0 / 3.0):
        measure = unwrap(carve_return_statistic("sharpe", value), "carved")
        assert ten_scale % measure.magnitude.denominator == 0, (
            f"carved {value} stored with non-scaled denominator {measure.magnitude.denominator}"
        )


def test_t22_303_money_reentry_requires_declared_rounding_and_yields_exact_money():
    """The named AD-22 money re-entry needs an explicit rounding mode and yields exact Money.

    Counter-case: a null rounding mode silently applying a default, or a non-Money
    result, would let a float become money by construction.
    """
    ok = reenter_money_path(1.25, currency="USD", scale=2, rounding=RoundingMode.HALF_EVEN)
    money = unwrap(ok, "money re-entry")
    assert isinstance(money, Money)
    assert money.as_fraction() == Fraction(5, 4)

    refused = reenter_money_path(1.25, currency="USD", scale=2, rounding=None)
    assert_ct04_refusal(refused, RefusalCategory.INVALID_INPUT, what="money re-entry without rounding")


# --- T22-304 (R-001: money-path float taint caught by the NFR-02 scanner) P0 --


def test_t22_304_money_path_float_scanner_flags_a_float_and_finds_the_module_clean():
    """The tier-1 money-path float scanner flags a money-path float and finds the module clean.

    Counter-case A (scanner can fail): a ``Money(3.5, ...)`` construction must be
    flagged — a scanner that flags nothing proves nothing. Counter-case B: any binary
    float on the money path inside the shipped robustness module must be flagged; the
    module must be clean.
    """
    sys.path.insert(0, str(WORKTREE_ROOT / "tools"))
    try:
        import money_path_scan as scanner
    finally:
        pass

    injected = scanner.scan_source('Money(3.5, "USD", 2)', "<injected-taint>")
    assert injected, "the NFR-02 scanner failed to flag an obvious money-path float"

    module_dir = WORKTREE_ROOT / "qmb" / "src" / "qmb" / "robustness"
    offenders = {}
    for path in sorted(module_dir.glob("*.py")):
        findings = scanner.scan_file(path)
        if findings:
            offenders[path.name] = [f.render() for f in findings]
    assert offenders == {}, f"money-path float taint in the robustness module: {offenders}"


# --- T22-305 (AD-41 label-derived float-measure identity) P1 -----------------


def test_t22_305_measure_identity_is_label_derived_not_float_bit_identity():
    """A float-valued measure takes AD-41 label-derived identity, never float bit-identity.

    Counter-case: two distinct floats that round to the same scaled rational must share
    one identity; if identity used float bits they would diverge. And two genuinely
    different values must NOT share identity.
    """
    base = unwrap(carve_return_statistic("sharpe_ratio", 1.5), "base")
    nudged = unwrap(carve_return_statistic("sharpe_ratio", 1.5 + 1e-15), "nudged")
    assert unwrap(base.fingerprint(), "fp").value == unwrap(nudged.fingerprint(), "fp").value
    assert all(not isinstance(part, float) for part in base.fp1_identity().values())

    different = unwrap(carve_return_statistic("sharpe_ratio", 2.5), "different")
    assert unwrap(base.fingerprint(), "fp").value != unwrap(different.fingerprint(), "fp").value


# --- T22-306 (distribution-summary primitive) P1 -----------------------------


def test_t22_306_summary_one_tailed_p_value_and_direction_flip():
    """The primitive returns an exact one-tailed p-value that flips with the declared direction.

    Counter-case: a strict ``>`` (excluding the observed) instead of at-or-beyond would
    give 10/100 not 11/100; a two-tailed or direction-blind statistic would not flip.
    """
    dist = [Fraction(v) for v in range(1, 101)]
    higher = unwrap(summarize_distribution(dist, 90, DIRECTION_HIGHER_IS_BETTER), "higher")
    expected_high = Fraction(sum(1 for v in dist if v >= 90), 100)
    assert higher.p_value == expected_high == Fraction(11, 100)

    lower = unwrap(summarize_distribution(dist, 90, DIRECTION_LOWER_IS_BETTER), "lower")
    expected_low = Fraction(sum(1 for v in dist if v <= 90), 100)
    assert lower.p_value == expected_low == Fraction(90, 100)
    # Every reported measure is exact (a Fraction), never a binary float.
    for field in (higher.p_value, higher.percentile_rank, higher.median, higher.minimum):
        assert isinstance(field, Fraction)


def test_t22_306_bands_are_caller_declared_empirical_quantiles():
    """Confidence bands are the empirical quantiles at caller-declared probabilities.

    Counter-case: an invented default band level, or a wrong quantile, would break the
    nearest-rank identity. With none declared the summary returns no bands.
    """
    dist = [Fraction(v) for v in range(1, 101)]
    summary = unwrap(
        summarize_distribution(
            dist, 90, DIRECTION_HIGHER_IS_BETTER, band_probabilities=[Fraction(1, 40), Fraction(39, 40)]
        ),
        "banded",
    )
    assert [band.value for band in summary.bands] == [Fraction(3), Fraction(98)]

    no_bands = unwrap(summarize_distribution(dist, 90, DIRECTION_HIGHER_IS_BETTER), "nobands")
    assert no_bands.bands == ()


# --- T22-307 (no pass/fail verdict; no invented alpha) P0 (L20) --------------


def test_t22_307_summary_emits_no_verdict_and_invents_no_alpha():
    """The primitive emits no pass/fail verdict and invents no alpha level.

    Counter-case: any accept/reject/significant/alpha field in the output, or a default
    band level applied when none is supplied, would be a smuggled verdict/threshold.
    """
    dist = [Fraction(v) for v in range(1, 51)]
    summary = unwrap(summarize_distribution(dist, 25, DIRECTION_HIGHER_IS_BETTER), "summary")
    assert summary.emits_verdict is False
    forbidden = {"pass", "fail", "significant", "reject", "accept", "alpha", "verdict", "threshold"}
    keys = {str(k).lower() for k in summary.fp1_identity()}
    assert keys.isdisjoint(forbidden), f"verdict/alpha field leaked into the summary: {keys & forbidden}"
    # No bands invented when none declared.
    assert summary.bands == ()
    # Reading a pass/fail out of the summary is refused.
    assert_ct04_refusal(
        refuse_pass_fail_verdict("pass"), RefusalCategory.POLICY_REJECTION, what="pass/fail verdict"
    )


# --- T22-308 (unset required input -> invalid refusal; no invented default) P0 -


def test_t22_308_unset_required_configurable_is_returned_invalid_refusal():
    """An unset required count is a RETURNED ``invalid input`` refusal, never a silent default.

    Counter-case: a silently-applied number (e.g. a baked default) returned as Ok would
    mean the module ships an invented default.
    """
    unset = require_positive_int({}, "qmb_mc_iterations")
    assert_ct04_refusal(unset, RefusalCategory.INVALID_INPUT, what="unset count")
    unset2 = require_configurable({}, "qmb_threshold")
    assert_ct04_refusal(unset2, RefusalCategory.INVALID_INPUT, what="unset configurable")
    # A supplied value passes through verbatim; a fractional/float/bool/non-positive is refused.
    assert unwrap(require_positive_int({"n": 1000}, "n"), "supplied") == 1000
    assert_ct04_refusal(require_positive_int({"n": 3.5}, "n"), RefusalCategory.INVALID_INPUT, what="float count")
    assert_ct04_refusal(require_positive_int({"n": True}, "n"), RefusalCategory.INVALID_INPUT, what="bool count")
    assert_ct04_refusal(require_positive_int({"n": 0}, "n"), RefusalCategory.INVALID_INPUT, what="zero count")


def test_t22_308_procedures_refuse_when_their_required_count_is_unset():
    """Each procedure refuses (never defaults) when its required count is unset.

    Counter-case: a run that proceeds with a baked MC-1000 / block-length default.
    """
    refused = run_trade_shuffle(
        trades=_trades(),
        starting_capital=usd(100_000),
        period=interval(0, 400),
        base_seed=7,
        metrics=["net_profit"],
    )
    assert_ct04_refusal(refused, RefusalCategory.INVALID_INPUT, what="shuffle with no scenario count")

    refused_pert = run_candle_perturbation(candles=_candles(), base_seed=3, scenario_count=5)
    assert_ct04_refusal(refused_pert, RefusalCategory.INVALID_INPUT, what="perturbation with no block length")


# --- T22-309 (claim class robustness, never edge; no money gating) P0 (L20) ---


def test_t22_309_procedure_outputs_claim_robustness_never_edge():
    """A real procedure output labels its claim class robustness — never edge.

    Counter-case: a procedure result whose claim class reads ``edge`` while GAP-0048 is
    open would launder synthetic/perturbed evidence into an edge claim.
    """
    pert = unwrap(
        run_candle_perturbation(candles=_candles(), base_seed=3, block_length=3, scenario_count=5),
        "perturbation",
    )
    assert pert.claim_class == "robustness"
    assert pert.claim_class != "edge"
    assert pert.world == World.REPLAY.value


def test_t22_309_edge_claim_and_live_money_gate_are_refused():
    """Reading an edge claim or gating live money on a robustness output is refused.

    Counter-case: either returning Ok would breach L20 / SC-06.
    """
    assert_ct04_refusal(
        refuse_edge_claim("walk-forward"), RefusalCategory.POLICY_REJECTION, what="edge claim"
    )
    assert_ct04_refusal(
        refuse_live_money_gate("walk-forward"), RefusalCategory.POLICY_REJECTION, what="live-money gate"
    )


# --- T22-PIN-01 (F-22-01: OverflowError -> typed refusal) P0 — EXPECTED FAIL --


def test_t22_pin01_carveout_boundary_returns_ct04_refusal_on_overflow_FINDING_F_22_01():
    """A public carve-out boundary must RETURN a CT-04 refusal on an un-floatable value.

    F-22-01: ``carve_return_statistic`` / ``reenter_money_path`` call ``float(value)`` on
    an unchecked int; a value too large for a C double raises ``OverflowError`` across
    the public boundary instead of returning a CT-04 refusal (DEC-0109: exceptions are
    reserved for programmer error, never a refusal channel). This pin asserts the
    correct behaviour and is EXPECTED TO FAIL against current source — the failure IS
    the recorded finding, never worked around by editing source or weakening the pin.
    """
    huge = 10**400
    result = carve_return_statistic("sharpe", huge)
    assert_ct04_refusal(result, RefusalCategory.INVALID_INPUT, what="carve of an un-floatable value")


def test_t22_pin01_money_reentry_returns_ct04_refusal_on_overflow_FINDING_F_22_01():
    """The named money re-entry must RETURN a CT-04 refusal on an un-floatable value.

    Same F-22-01 defect on ``reenter_money_path``; EXPECTED TO FAIL (raises OverflowError).
    """
    huge = 10**400
    result = reenter_money_path(huge, currency="USD", scale=2, rounding=RoundingMode.HALF_EVEN)
    assert_ct04_refusal(result, RefusalCategory.INVALID_INPUT, what="money re-entry of an un-floatable value")
