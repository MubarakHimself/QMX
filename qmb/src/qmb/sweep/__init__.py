"""Multi-route permutation sweeps: axis declaration and Cartesian expansion (B-12).

A sweep runs the full Cartesian space as a batch of isolated, fully-labeled runs.
Each combination is one isolated run of the same never-forked run loop with
different variables — the batch merges nothing (DEC-0169). This package owns the
pure axis-to-run-spec expansion and the pre-flight run count the operator sees
before committing; batch admission, per-combo ledger lines, and cross-run ranking
land in later stories of the epic.
"""

from __future__ import annotations

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

__all__ = [
    "CONVERSION_KINDS",
    "PREFLIGHT_ADMITS_BATCH",
    "PREFLIGHT_IS_PURE_INSPECTION",
    "PREFLIGHT_SPAWNS_PROCESS",
    "PREFLIGHT_WRITES_LEDGER_LINE",
    "SWEEP_AXES",
    "SWEEP_DECLARATION_CLASS",
    "SWEEP_FORMAT_VERSION",
    "SWEEP_RUN_SPEC_CLASS",
    "VALUE_KIND_BOOLEAN",
    "VALUE_KIND_CATEGORICAL",
    "VALUE_KIND_EXACT_INTEGER",
    "VALUE_KIND_MONEY",
    "VALUE_KIND_RATIONAL",
    "SweepDeclaration",
    "SweepRunSpec",
    "expand_sweep",
    "preflight_run_count",
    "sweep_axes_identity",
]
