"""Kill line, breakeven ratchet, and qualifying-loss bench (TN-8; Story 26.7).

Wires AD-36/AD-40/AD-41 and CT-29/CT-30 onto the node composition root:

* ``kill_line_capital_floor`` IS AD-40 ``loss_floor`` — evaluated per binding
  against marked virtual-ledger equity; breach flattens under ``kill_line_flat``,
  stands the binding down, and routes to the paired demo target (FTR-07: no
  invented floors).
* V1 dynamic protection is the single-sided breakeven ratchet; Book origination
  applies trigger/offset/min-improvement, the command path never re-applies them.
* The qualifying-loss bench fold (SCN-0011 fixture ``qmn/bench-fold``) benches a
  seat on ``realized_r <= -q`` while the Book stays LIVE; breakevens never count.
"""

from __future__ import annotations

from typing import Final

from qmn.capital.bench_fold import (
    BENCH_CONSECUTIVE_LOSS_THRESHOLD_REGISTRY_KEY,
    BENCH_DISPOSITIONS,
    BENCH_FOLD_FIXTURE,
    QUALIFYING_LOSS_THRESHOLD_REGISTRY_KEY,
    BenchCrossingEffect,
    BenchFoldReport,
    apply_bench_crossing,
    evaluate_qualifying_loss_bench,
    refuse_stale_exit_before_intent,
)
from qmn.capital.kill_line import (
    KILL_LINE_CAPITAL_FLOOR_REGISTRY_KEY,
    LOSS_FLOOR_REGISTRY_KEY,
    OPERATOR_KILL_LINE_RESUME,
    KillLineBreachPackage,
    KillLineCadence,
    KillLineEvaluation,
    KillLineRestore,
    apply_kill_line_breach,
    evaluate_kill_line,
    marked_virtual_equity,
    refuse_invented_kill_line_floor,
    restore_kill_line_stand_down,
)
from qmn.capital.ratchet import (
    AMEND_MIN_IMPROVEMENT_REGISTRY_KEY,
    BREAKEVEN_RATCHET_OFFSET_REGISTRY_KEY,
    BREAKEVEN_RATCHET_TRIGGER_REGISTRY_KEY,
    V1_DYNAMIC_PROTECTION_GRAMMAR,
    BreakevenRatchetOrigin,
    BreakevenRatchetProposal,
    DynamicProtectionGrammar,
    dispatch_originated_breakeven_ratchet,
    originate_breakeven_ratchet,
    refuse_non_breakeven_dynamic_grammar,
    v1_dynamic_protection_is_breakeven_ratchet_only,
)

__all__ = [
    "AMEND_MIN_IMPROVEMENT_REGISTRY_KEY",
    "BENCH_CONSECUTIVE_LOSS_THRESHOLD_REGISTRY_KEY",
    "BENCH_DISPOSITIONS",
    "BENCH_FOLD_FIXTURE",
    "BREAKEVEN_RATCHET_OFFSET_REGISTRY_KEY",
    "BREAKEVEN_RATCHET_TRIGGER_REGISTRY_KEY",
    "CAPITAL_SURFACE",
    "KILL_LINE_CAPITAL_FLOOR_REGISTRY_KEY",
    "LOSS_FLOOR_REGISTRY_KEY",
    "OPERATOR_KILL_LINE_RESUME",
    "QUALIFYING_LOSS_THRESHOLD_REGISTRY_KEY",
    "V1_DYNAMIC_PROTECTION_GRAMMAR",
    "BenchCrossingEffect",
    "BenchFoldReport",
    "BreakevenRatchetOrigin",
    "BreakevenRatchetProposal",
    "DynamicProtectionGrammar",
    "KillLineBreachPackage",
    "KillLineCadence",
    "KillLineEvaluation",
    "KillLineRestore",
    "apply_bench_crossing",
    "apply_kill_line_breach",
    "dispatch_originated_breakeven_ratchet",
    "evaluate_kill_line",
    "evaluate_qualifying_loss_bench",
    "marked_virtual_equity",
    "originate_breakeven_ratchet",
    "refuse_invented_kill_line_floor",
    "refuse_non_breakeven_dynamic_grammar",
    "refuse_stale_exit_before_intent",
    "restore_kill_line_stand_down",
    "v1_dynamic_protection_is_breakeven_ratchet_only",
]

CAPITAL_SURFACE: Final[str] = "qmn.capital"
