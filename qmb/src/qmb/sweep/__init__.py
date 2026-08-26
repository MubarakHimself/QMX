"""Multi-route permutation sweeps: axes, Cartesian expansion, and batch admission.

A sweep runs the full Cartesian space as a batch of isolated, fully-labeled runs.
Each combination is one isolated run of the same never-forked run loop with
different variables — the batch merges nothing (DEC-0169). This package owns the
pure axis-to-run-spec expansion and pre-flight run count (Story 20.1, B-12) plus
batch admission: one registry as-of resolved through the single library-owned
registry-read port and frozen for every combination (Story 20.2, B-15, SC-11).
Per-combo ledger lines and cross-run ranking land in later stories of the epic.
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

__all__ = [
    "ADMISSION_FREEZES_AS_OF",
    "ADMISSION_HAS_SECOND_CACHE",
    "ADMISSION_SINGLE_AS_OF",
    "CONVERSION_KINDS",
    "PREFLIGHT_ADMITS_BATCH",
    "PREFLIGHT_IS_PURE_INSPECTION",
    "PREFLIGHT_SPAWNS_PROCESS",
    "PREFLIGHT_WRITES_LEDGER_LINE",
    "REGISTRY_AS_OF_KEY",
    "SWEEP_AXES",
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
    "SweepDeclaration",
    "SweepLabel",
    "SweepRunSpec",
    "admit_sweep",
    "expand_sweep",
    "preflight_run_count",
    "sweep_admission_identity",
    "sweep_axes_identity",
]
