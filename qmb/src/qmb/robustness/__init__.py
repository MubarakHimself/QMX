"""Validation-ladder procedures as pure library functions (B-14).

The B-14 robustness ladder — Monte Carlo trade-shuffle, Monte Carlo
candle-perturbation, the rule-significance gate, and walk-forward — ships as pure
QMB library functions (22.2-22.5) built on ONE identity-bearing foundation:

* a **versioned statistical-procedure contract** (:mod:`qmb.robustness.contract`)
  stamping each rung's AD-5 format version and pinning the shared B-4 purity and
  claim-class guarantees, plus the required-configurable resolver (AR-13);
* the bounded **return-space float carve-out** (:mod:`qmb.robustness.carveout`) —
  P&L and equity stay exact scaled integers, floats live only inside a statistic
  under a fixed rounding contract, and float-valued measures take AD-41
  label-derived identity;
* the shared **distribution-summary primitive** (:mod:`qmb.robustness.summary`) —
  percentile ranks, confidence bands, and an empirical one-tailed p-value as pure
  data, with no pass/fail verdict.

Every procedure claims robustness or infra-stress, never edge (L20, DEC-0169), and
no output gates live money while GAP-0048 is open; thresholds and pass batteries
stay deferred (SC-06, SC-07).
"""

from __future__ import annotations

from typing import Final

from qmb.robustness.carveout import (
    IDENTITY_IS_LABEL_DERIVED,
    IDENTITY_USES_FLOAT_BITS,
    MONEY_PATH_STAYS_EXACT_INTEGER,
    RETURN_SPACE_MEASURE_CLASS,
    RETURN_SPACE_MEASURE_FORMAT_VERSION,
    RETURN_SPACE_STAT_ROUNDING,
    RETURN_SPACE_STAT_SCALE,
    ReturnSpaceMeasure,
    carve_return_statistic,
    carveout_identity,
    reenter_money_path,
)
from qmb.robustness.contract import (
    CLAIM_CLASS_EDGE,
    CLAIM_CLASS_INFRA_STRESS,
    CLAIM_CLASS_ROBUSTNESS,
    CLAIM_GATED_BEHIND,
    CONFIGURABLE_INPUT_DIMENSIONS,
    CONFIGURABLE_INPUTS_HAVE_RATIFIED_VALUE,
    MODULE_HAS_GLOBAL_MUTABLE_STATE,
    MODULE_SHIPS_INVENTED_DEFAULT,
    PROCEDURE_GATES_LIVE_MONEY,
    PROCEDURE_IS_PURE_LIBRARY_FUNCTION,
    PROCEDURE_MAKES_EDGE_CLAIM,
    PROCEDURE_MC_CANDLE_PERTURBATION,
    PROCEDURE_MC_TRADE_SHUFFLE,
    PROCEDURE_RULE_SIGNIFICANCE,
    PROCEDURE_SPENDS_SPLIT_BUDGET,
    PROCEDURE_WALK_FORWARD,
    PROCEDURE_WRITES_LEDGER_LINE,
    PROCEDURE_WRITES_LOG,
    ROBUSTNESS_CLAIM_CLASSES,
    ROBUSTNESS_CONTRACT_FORMAT_VERSION,
    ROBUSTNESS_PROCEDURES,
    THRESHOLDS_DEFERRED_TO,
    StatisticalProcedureContract,
    contract_identity,
    procedure_contract,
    refuse_edge_claim,
    refuse_live_money_gate,
    require_configurable,
    require_positive_int,
)
from qmb.robustness.summary import (
    DIRECTION_HIGHER_IS_BETTER,
    DIRECTION_LOWER_IS_BETTER,
    DISTRIBUTION_SUMMARY_CLASS,
    DISTRIBUTION_SUMMARY_FORMAT_VERSION,
    SUMMARY_DIRECTIONS,
    SUMMARY_EMITS_VERDICT,
    SUMMARY_FORBIDDEN_VERDICTS,
    SUMMARY_INVENTS_ALPHA,
    SUMMARY_VERDICT_DEFERRED_TO,
    DistributionBand,
    DistributionSummary,
    refuse_pass_fail_verdict,
    summarize_distribution,
    summary_identity,
)

__all__ = [
    "CLAIM_CLASS_EDGE",
    "CLAIM_CLASS_INFRA_STRESS",
    "CLAIM_CLASS_ROBUSTNESS",
    "CLAIM_GATED_BEHIND",
    "CONFIGURABLE_INPUTS_HAVE_RATIFIED_VALUE",
    "CONFIGURABLE_INPUT_DIMENSIONS",
    "DIRECTION_HIGHER_IS_BETTER",
    "DIRECTION_LOWER_IS_BETTER",
    "DISTRIBUTION_SUMMARY_CLASS",
    "DISTRIBUTION_SUMMARY_FORMAT_VERSION",
    "IDENTITY_IS_LABEL_DERIVED",
    "IDENTITY_USES_FLOAT_BITS",
    "MODULE_HAS_GLOBAL_MUTABLE_STATE",
    "MODULE_SHIPS_INVENTED_DEFAULT",
    "MONEY_PATH_STAYS_EXACT_INTEGER",
    "PROCEDURES",
    "PROCEDURE_GATES_LIVE_MONEY",
    "PROCEDURE_IS_PURE_LIBRARY_FUNCTION",
    "PROCEDURE_MAKES_EDGE_CLAIM",
    "PROCEDURE_MC_CANDLE_PERTURBATION",
    "PROCEDURE_MC_TRADE_SHUFFLE",
    "PROCEDURE_RULE_SIGNIFICANCE",
    "PROCEDURE_SPENDS_SPLIT_BUDGET",
    "PROCEDURE_WALK_FORWARD",
    "PROCEDURE_WRITES_LEDGER_LINE",
    "PROCEDURE_WRITES_LOG",
    "RETURN_SPACE_MEASURE_CLASS",
    "RETURN_SPACE_MEASURE_FORMAT_VERSION",
    "RETURN_SPACE_STAT_ROUNDING",
    "RETURN_SPACE_STAT_SCALE",
    "ROBUSTNESS_CLAIM_CLASSES",
    "ROBUSTNESS_CONTRACT_FORMAT_VERSION",
    "ROBUSTNESS_PROCEDURES",
    "SUMMARY_DIRECTIONS",
    "SUMMARY_EMITS_VERDICT",
    "SUMMARY_FORBIDDEN_VERDICTS",
    "SUMMARY_INVENTS_ALPHA",
    "SUMMARY_VERDICT_DEFERRED_TO",
    "THRESHOLDS_DEFERRED_TO",
    "DistributionBand",
    "DistributionSummary",
    "ReturnSpaceMeasure",
    "StatisticalProcedureContract",
    "carve_return_statistic",
    "carveout_identity",
    "contract_identity",
    "ladder_identity",
    "procedure_contract",
    "reenter_money_path",
    "refuse_edge_claim",
    "refuse_live_money_gate",
    "refuse_pass_fail_verdict",
    "require_configurable",
    "require_positive_int",
    "robustness_foundation_identity",
    "summarize_distribution",
    "summary_identity",
]

# The full validation ladder as named rungs, including the Epic 14/21 backtest and
# optimize rungs the robustness ladder builds on. The robustness-only rungs are
# pinned separately in :data:`ROBUSTNESS_PROCEDURES`.
PROCEDURES: Final[tuple[str, ...]] = (
    "backtest",
    "optimize",
    *ROBUSTNESS_PROCEDURES,
)


def ladder_identity() -> dict[str, object]:
    """Identity-bearing ladder fields. Package SemVer is omitted."""
    return {"procedures": PROCEDURES, "claim_class": "robustness-or-infra-stress"}


def robustness_foundation_identity() -> dict[str, object]:
    """The composed Story 22.1 foundation identity. Package SemVer is omitted."""
    return {
        "carveout": carveout_identity(),
        "contract": contract_identity(),
        "ladder": ladder_identity(),
        "summary": summary_identity(),
    }
