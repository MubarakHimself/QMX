"""Multi-route permutation sweeps: axes, Cartesian expansion, and batch admission.

A sweep runs the full Cartesian space as a batch of isolated, fully-labeled runs.
Each combination is one isolated run of the same never-forked run loop with
different variables — the batch merges nothing (DEC-0169). This package owns the
pure axis-to-run-spec expansion and pre-flight run count (Story 20.1, B-12);
batch admission: one registry as-of resolved through the single library-owned
registry-read port and frozen for every combination (Story 20.2, B-15, SC-11);
and batch execution: each combination runs as one isolated, fully-labelled OS
process under the ``min(cpu, memory)`` governor and writes exactly one ledger
line, where a single combo's refusal is that combo's outcome and never aborts
the batch (Story 20.3, B-4, B-5, spec R10-R12). Cross-run ranking is a read-time
fold over these per-combo lines: it orders a completed sweep's combinations by a
declared objective ``measure_identity`` with optional metric-operator-value
constraints, publishes never acts, and reports refused/incomplete combos
separately — never re-running and never coercing a refusal to a zero score
(Story 20.4, B-4, B-10, B-12, B-14, spec R11-R12).
"""

from __future__ import annotations

from qmb.sweep.admit import (
    ADMISSION_FREEZES_AS_OF,
    ADMISSION_HAS_SECOND_CACHE,
    ADMISSION_SINGLE_AS_OF,
    REGISTRY_AS_OF_KEY,
    SWEEP_LABEL_CLASS,
    SWEEP_LABEL_FORMAT_VERSION,
    SWEEP_RUN_LABEL_CLASS,
    AdmittedSweep,
    SweepLabel,
    admit_sweep,
    sweep_admission_identity,
)
from qmb.sweep.axes import (
    CONVERSION_KINDS,
    PREFLIGHT_ADMITS_BATCH,
    PREFLIGHT_IS_PURE_INSPECTION,
    PREFLIGHT_SPAWNS_PROCESS,
    PREFLIGHT_WRITES_LEDGER_LINE,
    SWEEP_AXES,
    SWEEP_DECLARATION_CLASS,
    SWEEP_FORMAT_VERSION,
    SWEEP_RUN_SPEC_CLASS,
    VALUE_KIND_BOOLEAN,
    VALUE_KIND_CATEGORICAL,
    VALUE_KIND_EXACT_INTEGER,
    VALUE_KIND_MONEY,
    VALUE_KIND_RATIONAL,
    SweepDeclaration,
    SweepRunSpec,
    expand_sweep,
    preflight_run_count,
    sweep_axes_identity,
)
from qmb.sweep.batch import (
    BATCH_ABORTS_ON_COMBO_REFUSAL,
    BATCH_ONE_LINE_PER_COMBO,
    STATUS_COMPLETED,
    STATUS_REFUSED,
    SWEEP_COORDINATES_CLASS,
    SWEEP_COORDINATES_FORMAT_VERSION,
    SweepBatchReport,
    SweepComboOutcome,
    run_sweep_batch,
    sweep_batch_identity,
    sweep_coordinates_of,
)
from qmb.sweep.rank import (
    CONSTRAINT_OPERATORS,
    INCOMPLETE_CONSTRAINT_MISSING,
    INCOMPLETE_CONSTRAINT_UNDEFINED,
    INCOMPLETE_OBJECTIVE_MISSING,
    INCOMPLETE_OBJECTIVE_UNDEFINED,
    INCOMPLETE_REASONS,
    INCOMPLETE_REFUSED,
    RANK_ADDS_COMPUTATION,
    RANK_ASCENDING,
    RANK_DESCENDING,
    RANK_DIRECTIONS,
    RANK_FORBIDDEN_ACTS,
    RANK_MAKES_EDGE_CLAIM,
    RANK_MAKES_PASS_FAIL_VERDICT,
    RANK_PUBLISHES_NEVER_ACTS,
    RANKING_CLASS,
    RANKING_FORMAT_VERSION,
    ConstraintFilter,
    IncompleteCombo,
    RankedCombo,
    SweepRanking,
    rank_sweep,
    refuse_rank_act,
    sweep_rank_identity,
)

__all__ = [
    "ADMISSION_FREEZES_AS_OF",
    "ADMISSION_HAS_SECOND_CACHE",
    "ADMISSION_SINGLE_AS_OF",
    "BATCH_ABORTS_ON_COMBO_REFUSAL",
    "BATCH_ONE_LINE_PER_COMBO",
    "CONSTRAINT_OPERATORS",
    "CONVERSION_KINDS",
    "INCOMPLETE_CONSTRAINT_MISSING",
    "INCOMPLETE_CONSTRAINT_UNDEFINED",
    "INCOMPLETE_OBJECTIVE_MISSING",
    "INCOMPLETE_OBJECTIVE_UNDEFINED",
    "INCOMPLETE_REASONS",
    "INCOMPLETE_REFUSED",
    "PREFLIGHT_ADMITS_BATCH",
    "PREFLIGHT_IS_PURE_INSPECTION",
    "PREFLIGHT_SPAWNS_PROCESS",
    "PREFLIGHT_WRITES_LEDGER_LINE",
    "RANKING_CLASS",
    "RANKING_FORMAT_VERSION",
    "RANK_ADDS_COMPUTATION",
    "RANK_ASCENDING",
    "RANK_DESCENDING",
    "RANK_DIRECTIONS",
    "RANK_FORBIDDEN_ACTS",
    "RANK_MAKES_EDGE_CLAIM",
    "RANK_MAKES_PASS_FAIL_VERDICT",
    "RANK_PUBLISHES_NEVER_ACTS",
    "REGISTRY_AS_OF_KEY",
    "STATUS_COMPLETED",
    "STATUS_REFUSED",
    "SWEEP_AXES",
    "SWEEP_COORDINATES_CLASS",
    "SWEEP_COORDINATES_FORMAT_VERSION",
    "SWEEP_DECLARATION_CLASS",
    "SWEEP_FORMAT_VERSION",
    "SWEEP_LABEL_CLASS",
    "SWEEP_LABEL_FORMAT_VERSION",
    "SWEEP_RUN_LABEL_CLASS",
    "SWEEP_RUN_SPEC_CLASS",
    "VALUE_KIND_BOOLEAN",
    "VALUE_KIND_CATEGORICAL",
    "VALUE_KIND_EXACT_INTEGER",
    "VALUE_KIND_MONEY",
    "VALUE_KIND_RATIONAL",
    "AdmittedSweep",
    "ConstraintFilter",
    "IncompleteCombo",
    "RankedCombo",
    "SweepBatchReport",
    "SweepComboOutcome",
    "SweepDeclaration",
    "SweepLabel",
    "SweepRanking",
    "SweepRunSpec",
    "admit_sweep",
    "expand_sweep",
    "preflight_run_count",
    "rank_sweep",
    "refuse_rank_act",
    "run_sweep_batch",
    "sweep_admission_identity",
    "sweep_axes_identity",
    "sweep_batch_identity",
    "sweep_coordinates_of",
    "sweep_rank_identity",
]
