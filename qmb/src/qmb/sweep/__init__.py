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
the batch (Story 20.3, B-4, B-5, spec R10-R12). Cross-run ranking is a later
read-time fold over these per-combo lines.
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

__all__ = [
    "ADMISSION_FREEZES_AS_OF",
    "ADMISSION_HAS_SECOND_CACHE",
    "ADMISSION_SINGLE_AS_OF",
    "BATCH_ABORTS_ON_COMBO_REFUSAL",
    "BATCH_ONE_LINE_PER_COMBO",
    "CONVERSION_KINDS",
    "PREFLIGHT_ADMITS_BATCH",
    "PREFLIGHT_IS_PURE_INSPECTION",
    "PREFLIGHT_SPAWNS_PROCESS",
    "PREFLIGHT_WRITES_LEDGER_LINE",
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
    "SweepBatchReport",
    "SweepComboOutcome",
    "SweepDeclaration",
    "SweepLabel",
    "SweepRunSpec",
    "admit_sweep",
    "expand_sweep",
    "preflight_run_count",
    "run_sweep_batch",
    "sweep_admission_identity",
    "sweep_axes_identity",
    "sweep_batch_identity",
    "sweep_coordinates_of",
]
