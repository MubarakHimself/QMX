"""Story 22.1 — robustness module foundation (B-14): contract, carve-out, summary.

Covers the six acceptance criteria: the versioned pure-library procedure contract
(AC1), the bounded return-space float carve-out (AC2), AD-41 label-derived measure
identity (AC3), the shared distribution-summary primitive (AC4), UI-editable
configurables with no invented default (AC5), and the robustness/infra-stress claim
class that never gates live money (AC6).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType
from typing import TypeVar

from qmb.robustness import (
    CLAIM_CLASS_EDGE,
    CLAIM_GATED_BEHIND,
    CONFIGURABLE_INPUT_DIMENSIONS,
    CONFIGURABLE_INPUTS_HAVE_RATIFIED_VALUE,
    DIRECTION_HIGHER_IS_BETTER,
    DIRECTION_LOWER_IS_BETTER,
    MODULE_HAS_GLOBAL_MUTABLE_STATE,
    MODULE_SHIPS_INVENTED_DEFAULT,
    PROCEDURE_GATES_LIVE_MONEY,
    PROCEDURE_IS_PURE_LIBRARY_FUNCTION,
    PROCEDURE_MAKES_EDGE_CLAIM,
    PROCEDURE_SPENDS_SPLIT_BUDGET,
    PROCEDURE_WRITES_LEDGER_LINE,
    PROCEDURE_WRITES_LOG,
    RETURN_SPACE_STAT_ROUNDING,
    RETURN_SPACE_STAT_SCALE,
    ROBUSTNESS_CLAIM_CLASSES,
    ROBUSTNESS_CONTRACT_FORMAT_VERSION,
    ROBUSTNESS_PROCEDURES,
    SUMMARY_EMITS_VERDICT,
    carve_return_statistic,
    carveout_identity,
    contract_identity,
    procedure_contract,
    reenter_money_path,
    refuse_edge_claim,
    refuse_live_money_gate,
    refuse_pass_fail_verdict,
    require_configurable,
    require_positive_int,
    robustness_foundation_identity,
    summarize_distribution,
    summary_identity,
)
from qmf.core.exact import Money, RoundingMode, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


# --- AC1: versioned pure-library procedure contract --------------------------


def test_each_rung_has_a_format_version_1_contract() -> None:
    assert ROBUSTNESS_PROCEDURES == (
        "monte-carlo-trade-shuffle",
        "monte-carlo-candle-perturbation",
        "rule-significance",
        "walk-forward",
    )
    for procedure in ROBUSTNESS_PROCEDURES:
        contract = _ok(procedure_contract(procedure))
        assert contract.procedure == procedure
        assert contract.contract_format_version == ROBUSTNESS_CONTRACT_FORMAT_VERSION == 1
        identity = contract.fp1_identity()
        assert identity["contract_format_version"] == 1
        assert identity["procedure"] == procedure
        assert is_ok(contract.fingerprint())


def test_off_roster_procedure_is_invalid_input() -> None:
    refused = procedure_contract("edge-hunt")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_procedures_declare_pure_no_ledger_no_log_no_global_state() -> None:
    assert PROCEDURE_IS_PURE_LIBRARY_FUNCTION is True
    assert PROCEDURE_WRITES_LEDGER_LINE is False
    assert PROCEDURE_WRITES_LOG is False
    assert MODULE_HAS_GLOBAL_MUTABLE_STATE is False
    identity = contract_identity()
    assert identity["pure_library_function"] is True
    assert identity["module_has_global_mutable_state"] is False


def test_contract_identity_excludes_semver_and_fingerprints() -> None:
    identity = contract_identity()
    assert qmb.__version__ not in [str(value) for value in identity.values()]
    assert is_ok(fingerprint(identity))


# --- AC2: bounded return-space float carve-out -------------------------------


def test_carve_out_crosses_one_float_boundary_to_exact_rational() -> None:
    measure = _ok(carve_return_statistic("sharpe_ratio", 1.5))
    assert measure.scale == RETURN_SPACE_STAT_SCALE
    assert measure.rounding == RETURN_SPACE_STAT_ROUNDING.value
    assert measure.magnitude == Fraction(3, 2)
    assert measure.unit_kind == UnitKind.DIMENSIONLESS_RATIO.value


def test_carve_out_refuses_nan_and_infinity_never_zero() -> None:
    for bad in (float("nan"), float("inf"), float("-inf")):
        refused = carve_return_statistic("calmar_ratio", bad)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.INVALID_INPUT


def test_carve_out_never_admits_raw_money_or_a_blank_label() -> None:
    money = _ok(Money.try_create(100, "USD", 2))
    assert is_refusal(carve_return_statistic("x", money))
    assert is_refusal(carve_return_statistic("   ", 1.0))


def test_money_re_entry_requires_a_declared_rounding_mode() -> None:
    reentered = _ok(
        reenter_money_path(1.25, currency="USD", scale=2, rounding=RoundingMode.HALF_EVEN)
    )
    assert reentered.as_fraction() == Fraction(5, 4)
    assert reentered.currency == "USD"
    refused = reenter_money_path(1.25, currency="USD", scale=2, rounding=None)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_carveout_identity_excludes_semver_and_declares_exact_money_path() -> None:
    identity = carveout_identity()
    assert identity["money_path_stays_exact_integer"] is True
    assert identity["identity_is_label_derived"] is True
    assert identity["identity_uses_float_bits"] is False
    assert qmb.__version__ not in [str(value) for value in identity.values()]
    assert is_ok(fingerprint(identity))


# --- AC3: AD-41 label-derived measure identity -------------------------------


def test_identical_inputs_yield_identical_measure_identity() -> None:
    first = _ok(carve_return_statistic("sharpe_ratio", 1.234567890123))
    second = _ok(carve_return_statistic("sharpe_ratio", 1.234567890123))
    assert _ok(first.fingerprint()).value == _ok(second.fingerprint()).value


def test_identity_is_label_derived_not_float_bits() -> None:
    # Two distinct binary floats that round to the same scaled rational share one
    # identity — proof identity is the label + reduced rational, never the float bits.
    near = 1.5 + 1e-15
    base = _ok(carve_return_statistic("sharpe_ratio", 1.5))
    nudged = _ok(carve_return_statistic("sharpe_ratio", near))
    assert near != 1.5
    assert base.magnitude == nudged.magnitude
    assert _ok(base.fingerprint()).value == _ok(nudged.fingerprint()).value
    # No binary float ever appears in the identity content.
    assert all(not isinstance(value, float) for value in base.fp1_identity().values())


def test_a_different_label_is_a_different_identity() -> None:
    sharpe = _ok(carve_return_statistic("sharpe_ratio", 1.5))
    calmar = _ok(carve_return_statistic("calmar_ratio", 1.5))
    assert _ok(sharpe.fingerprint()).value != _ok(calmar.fingerprint()).value


# --- AC4: shared distribution-summary primitive ------------------------------


def test_one_tailed_p_value_counts_at_or_beyond_in_the_declared_direction() -> None:
    distribution = [Fraction(value) for value in range(1, 101)]  # 1..100
    higher = _ok(summarize_distribution(distribution, 90, DIRECTION_HIGHER_IS_BETTER))
    # values >= 90 are 90..100 = 11 of 100.
    assert higher.p_value == Fraction(11, 100)
    lower = _ok(summarize_distribution(distribution, 90, DIRECTION_LOWER_IS_BETTER))
    # values <= 90 are 1..90 = 90 of 100.
    assert lower.p_value == Fraction(90, 100)
    assert higher.count == 100
    assert higher.minimum == Fraction(1)
    assert higher.maximum == Fraction(100)
    assert higher.median == Fraction(101, 2)


def test_percentile_rank_and_confidence_bands_are_exact_data() -> None:
    distribution = [Fraction(value) for value in range(1, 101)]
    summary = _ok(
        summarize_distribution(
            distribution,
            50,
            DIRECTION_HIGHER_IS_BETTER,
            band_probabilities=[Fraction(1, 40), Fraction(39, 40)],
        )
    )
    # Mid-rank of 50 in 1..100: 49 below, 1 equal -> (2*49 + 1)/200.
    assert summary.percentile_rank == Fraction(99, 200)
    probabilities = [band.probability for band in summary.bands]
    assert probabilities == [Fraction(1, 40), Fraction(39, 40)]
    # Nearest-rank quantiles: ceil(0.025*100)=3 -> 3; ceil(0.975*100)=98 -> 98.
    values = [band.value for band in summary.bands]
    assert values == [Fraction(3), Fraction(98)]


def test_summary_emits_no_verdict_and_invents_no_alpha() -> None:
    distribution = [Fraction(1), Fraction(2), Fraction(3)]
    summary = _ok(summarize_distribution(distribution, 2, DIRECTION_HIGHER_IS_BETTER))
    assert summary.emits_verdict is False
    assert SUMMARY_EMITS_VERDICT is False
    # With no caller-supplied probabilities the summary invents no band.
    assert summary.bands == ()
    refused = refuse_pass_fail_verdict("pass")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_summary_refuses_empty_distribution_float_and_bad_inputs() -> None:
    assert is_refusal(summarize_distribution([], 1, DIRECTION_HIGHER_IS_BETTER))
    # A raw binary float must cross the carve-out first; it is refused here.
    assert is_refusal(summarize_distribution([1.5, 2.5], 1, DIRECTION_HIGHER_IS_BETTER))
    assert is_refusal(summarize_distribution([Fraction(1)], 1.5, DIRECTION_HIGHER_IS_BETTER))
    assert is_refusal(summarize_distribution([Fraction(1)], 1, "sideways"))
    # A band probability outside (0, 1) is refused — no default alpha invented.
    assert is_refusal(
        summarize_distribution(
            [Fraction(1), Fraction(2)],
            1,
            DIRECTION_HIGHER_IS_BETTER,
            band_probabilities=[Fraction(3, 2)],
        )
    )


def test_summary_accepts_carved_measures_and_stays_reproducible() -> None:
    carved = [
        _ok(carve_return_statistic("mc_sharpe", 0.5)),
        _ok(carve_return_statistic("mc_sharpe", 1.0)),
        _ok(carve_return_statistic("mc_sharpe", 1.5)),
    ]
    observed = _ok(carve_return_statistic("observed_sharpe", 1.25))
    first = _ok(summarize_distribution(carved, observed, DIRECTION_HIGHER_IS_BETTER))
    second = _ok(summarize_distribution(carved, observed, DIRECTION_HIGHER_IS_BETTER))
    assert _ok(first.fingerprint()).value == _ok(second.fingerprint()).value
    assert summary_identity()["emits_verdict"] is False


# --- AC5: UI-editable configurables with no invented default -----------------


def test_unset_required_configurable_is_a_typed_invalid_input_refusal() -> None:
    refused = require_positive_int({}, "qmb_mc_iterations")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    also = require_configurable({"qmb_mc_iterations": None}, "qmb_mc_iterations")
    assert is_refusal(also)
    assert also.category is RefusalCategory.INVALID_INPUT


def test_configured_positive_int_resolves_and_bad_values_refuse() -> None:
    assert _ok(require_positive_int({"iterations": 1000}, "iterations")) == 1000
    assert is_refusal(require_positive_int({"iterations": 0}, "iterations"))
    assert is_refusal(require_positive_int({"iterations": -5}, "iterations"))
    assert is_refusal(require_positive_int({"iterations": 3.5}, "iterations"))
    assert is_refusal(require_positive_int({"iterations": True}, "iterations"))


def test_configurable_resolves_from_a_resolved_run_config_keys_mapping() -> None:
    # A resolved run-config exposes its configurables as a ``keys`` mapping (B-3).
    # The resolver reads that mapping: a configured input resolves, an unset one refuses.
    config = _RunConfigCarrier(MappingProxyType({"qmb_walk_forward_minimum_observations": 250}))
    assert _ok(require_positive_int(config, "qmb_walk_forward_minimum_observations")) == 250
    refused = require_positive_int(config, "qmb_walk_forward_block_length")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_module_ships_no_invented_default_and_no_ratified_value() -> None:
    assert MODULE_SHIPS_INVENTED_DEFAULT is False
    assert CONFIGURABLE_INPUTS_HAVE_RATIFIED_VALUE is False
    assert CONFIGURABLE_INPUT_DIMENSIONS == (
        "block_length",
        "iterations",
        "minimum_observations",
        "scenarios",
        "threshold",
    )


# --- AC6: robustness/infra-stress claim, never edge, no live-money gate -------


def test_claim_class_is_robustness_or_infra_stress_never_edge() -> None:
    assert ROBUSTNESS_CLAIM_CLASSES == ("robustness", "infra-stress")
    assert CLAIM_CLASS_EDGE not in ROBUSTNESS_CLAIM_CLASSES
    assert PROCEDURE_MAKES_EDGE_CLAIM is False
    refused = refuse_edge_claim("walk-forward")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["forbidden_claim_class"] == CLAIM_CLASS_EDGE


def test_no_output_gates_live_money_or_spends_split_budget_under_gap_0048() -> None:
    assert PROCEDURE_GATES_LIVE_MONEY is False
    assert PROCEDURE_SPENDS_SPLIT_BUDGET is False
    assert CLAIM_GATED_BEHIND == "GAP-0048"
    refused = refuse_live_money_gate("monte-carlo-trade-shuffle")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["gated_behind"] == "GAP-0048"
    assert contract_identity()["gated_behind"] == "GAP-0048"


# --- foundation identity -----------------------------------------------------


def test_foundation_identity_excludes_semver_and_fingerprints() -> None:
    identity = robustness_foundation_identity()
    flat = str(identity)
    assert qmb.__version__ not in flat
    assert is_ok(fingerprint(identity))
    # Reachable both from the library root and the API door, one object.
    assert qmb.robustness_foundation_identity() == identity


@dataclass(frozen=True)
class _RunConfigCarrier:
    """A minimal resolved-run-config stand-in exposing a read-only keys mapping."""

    keys: Mapping[str, object]
