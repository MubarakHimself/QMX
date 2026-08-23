"""qmf.indicators — the two-mode CT-16 indicator library.

Roster package of the QMF V1 uv workspace. It re-exports the public CT-16 surface as
it lands story by story.

Landed (Story 7.1): the CT-16 **configured-indicator declaration record and its fp1
identity** — the frozen :class:`ConfiguredIndicator` whose ``fp1`` (computed by the
single ``qmf-core`` fingerprint function, nowhere else) spans the **entire declared
configuration**: the ``formula_id``, the per-configured-indicator
``contract_format_version``, the exact-rational ``parameters`` (a binary float is
refused — exact rationals only), the ordered named ``inputs`` (each a
:class:`SeriesInput` carrying instrument-or-source identity, a ``BarSpec`` identity
reference, channel kind, quote side, and — for a derived input — the upstream
fingerprint), the ``calendar_requirements`` (rule set + version + tzdata version), the
``alignment_policy`` and ``missing_value_policy``, the ``warm_up`` count, the ordered
``output_schema`` of :class:`OutputChannel`\\ s, the ``supported_modes``, and the
identity-bearing :class:`ArithmeticReference` — plus the declared-when-present
:class:`EmissionPolicy`, warm-up time bound, and light-claim :class:`DeclaredBudget`.
Two configurations differing in any one element receive distinct fingerprints, that
``fp1`` is the only dedup key, and an element missing from the fingerprint is a contract
defect (:data:`IDENTITY_ELEMENTS`) (DEC-0126, DEC-0127, DEC-0128, DEC-0105, DEC-0108).

Landed (Story 7.2): **TA-Lib canonical arithmetic wrapping with the
reference-configuration record asserted at import.** The pinned canonical arithmetic
reference is ``registry:canonical_indicator_reference`` — TA-Lib C library 0.7.1 +
Python wrapper 0.7.1 — pinned as lockfile-resolved artifacts and asserted at import:
importing this package resolves the installed reference and, if the resolved artifacts
differ from the pin or its process-global configuration differs from the
reference-configuration record, the assertion yields an ``unavailable dependency``
refusal (reachable through :func:`reference_status`), so a fingerprint never attests
arithmetic that was not used (FM-2). The package never mutates the reference's
process-global configuration. Ownership is law: where the reference implements a
formula, wrapping it is mandatory and it is canonical (:data:`CANONICAL_OWNERS`,
:class:`FormulaOwnership` ``REFERENCE``); where it does not, this package's own
arithmetic is canonical (``PACKAGE``). :func:`resolve_canonical_arithmetic` enforces
mandatory wrapping — a reference-owned formula requires the verified reference — and no
TA-Lib object crosses any public boundary (FM-5) (DEC-0127, DEC-0134).

Landed (Story 7.4): **streaming mode, the tier-2 equality law, and restore-equivalence.**
:class:`StreamingIndicator` is the one named stateful class in the concurrency stance —
exactly one feeder (**one WriterId holder**) and unlimited readers — that exposes
:meth:`~StreamingIndicator.health`, tags every output with the input sequence number
that produced it (minted by a ``qmf-core`` :class:`~qmf.core.WriterSequencer`), and scales
by distinct configuration, not by consumer. Its numbers are **equal to batch by
construction**: each update recomputes through the identical
:class:`~qmf.indicators.batch.BatchKernel` over the accumulated observations, so there is
no second arithmetic that could drift. :func:`assert_mode_equality` runs the tier-2
equality law under a per-configuration integer-ULP :class:`ModeEqualityComparator`
(default 0) over canonical inputs = (series, exact parameters, cold initial state), with
the seeding rule (:data:`SEEDING_RULE`) and leading-undefined-prefix-to-not-ready mapping
(:data:`LEADING_UNDEFINED_MAPPING`) declared; cross-OS/cross-build agreement is never this
gate. A :class:`StreamingSnapshot` is a serialized contract with its own
:data:`SNAPSHOT_FORMAT_VERSION` scoped to a declared ``(OS, arithmetic-reference build)``
:class:`SnapshotScope`: restore-then-N-updates equals cold-warm-then-the-same-N-updates,
a result from restored state carries the snapshot fingerprint as an input fingerprint, and
restoring across a different tuple is an ``unavailable dependency`` refusal (FM-7)
(DEC-0126, DEC-0113, DEC-0103, DEC-0106).

Landed (Story 7.5): **the conformance harness, the light/heavy benchmark budgets, and the
one named catalog surface.** :data:`~qmf.indicators.conformance.CONCEPT_WALK_REGISTER` is the
CT-16 conformance register — the concept-walk list the contract must keep expressible — and
:func:`~qmf.indicators.conformance.run_conformance` proves at tier 2 that every register
concept (multi-instrument and multi-BarSpec input sets, derived-series chaining, non-time bar
kinds, calendar-scoped windows and calendar-anchored sampling, projected outputs under
knowable-at, batch-only statistical methods, price-valued outputs re-entering the money path,
and delta-typed price differences) is expressible as a governed configuration. The benchmark
harness records **two rungs** — :class:`~qmf.indicators.benchmark.BenchmarkRung` burst
throughput and per-tick latency per accepted input observation, with the no-op tick path
measured separately — and :func:`~qmf.indicators.benchmark.regression_gate` fails the tier-2
gate on a latency, throughput, **or** peak-memory regression alike. Light versus heavy is
per configuration: :func:`~qmf.indicators.budget.evaluate_light_claim` refuses a light claim
made without a recorded live-path rung baseline or whose benchmark misses a declared bound
(FM-6), every configuration is heavy by default, and
:func:`~qmf.indicators.budget.guard_synchronous_entry` returns ``unsupported capability`` for
a heavy configuration's synchronous entry point (FM-3). Extensions enter through the one named
:class:`~qmf.indicators.catalog.Catalog` by **explicit registration — never ambient
scanning** — carrying their distribution identity and version as mandatory fields of every
artifact (FM-8), and :func:`~qmf.indicators.catalog.graduate` is the only door from
plain-Python research into governed evidence, requiring a lineage edge back to the originating
research artifact (L33) (DEC-0126, DEC-0127, DEC-0128, DEC-0111, DEC-0133, DEC-0100).

Landed (Story 7.6): **the first wrapper set of TA-Lib-backed configured indicators and the
FM-4 arithmetic-upgrade comparison suite.** :data:`~qmf.indicators.wrappers.WRAPPER_SET` is
the first set of concrete CT-16 configured indicators — the reference-owned, single-input,
period-taking formulas the batch bridge computes end to end (``sma``, ``ema``, ``wma``,
``rsi``, ``mom``, ``roc``) — each a :class:`~qmf.indicators.wrappers.WrapperSpec` wrapping
the reference formula (re-implementing arithmetic the reference owns is a contract defect,
FM-5, which :func:`~qmf.indicators.wrappers.wrapper_set_conformance_defects` catches), with
a mechanically stated capability term and **no trading-school name** in any rule or
vocabulary (DEC-0132). :func:`~qmf.indicators.wrappers.configure_wrapper` assembles a full
:class:`ConfiguredIndicator` from an injected period, input set, calendar requirements, and
arithmetic-reference configuration, declaring **both modes** so the tier-2 equality law
binds and setting **warm-up to at least the reference's lookback**
(:func:`~qmf.indicators.wrappers.reference_lookback`) — the minimum legal value by default,
never below it. :func:`~qmf.indicators.comparison.compare_reference_outputs` is the FM-4
comparison suite: it compares a candidate reference's output to the current one over
identical canonical inputs and, on any change, returns a
:class:`~qmf.indicators.comparison.ComparisonReport` carrying a
:class:`~qmf.indicators.comparison.ContractFormatMint` — never a silent accept — that mints
the **per-configured-indicator** contract format version (``previous + 1``) with recorded
before/after ``fp1`` evidence, while the CT-16 protocol format version stays unchanged
(never a protocol-wide bump) (DEC-0127, DEC-0030, DEC-0103).

Default-deny holds: this package imports **only** ``qmf.core`` — every ``fp1``
fingerprint is computed there; the ``ta-lib`` reference is a third-party runtime
dependency kept behind the package-neutral surface — and nothing imports
``qmf-indicators``; a configuration is assembled by the application at the composition
root (DEC-0120). Public value types are frozen dataclasses and the public seam is a
:class:`typing.Protocol` (DEC-0101).
"""

from __future__ import annotations

from qmf.indicators.arithmetic import (
    CANONICAL_OWNERS,
    FormulaOwner,
    FormulaOwnership,
    canonical_owner,
    ownership_conformance_defects,
    reference_grounded_defects,
    reference_status,
    resolve_canonical_arithmetic,
)
from qmf.indicators.batch import (
    DEFAULT_ANALYTIC_SCALE,
    AlignmentMode,
    AsOfSample,
    BatchKernel,
    BatchResult,
    KernelOutput,
    ReferenceKernel,
    align_to_instant,
    compute_batch,
    require_governed,
)
from qmf.indicators.benchmark import (
    PERMILLE,
    BenchmarkBaseline,
    BenchmarkMeasurement,
    BenchmarkRung,
    NoOpTickMeasurement,
    RegressionReport,
    RegressionTolerance,
    RungMeasurement,
    compare_to_baseline,
    regression_gate,
)
from qmf.indicators.budget import (
    BudgetVerdict,
    LightHeavyVerdict,
    evaluate_light_claim,
    guard_synchronous_entry,
)
from qmf.indicators.catalog import (
    EXTENSION_DISTRIBUTION_FIELD,
    EXTENSION_VERSION_FIELD,
    Catalog,
    ExtensionIdentity,
    RegisteredExtension,
    ResearchLineage,
    graduate,
    require_extension_identity,
    stamp_extension_identity,
)
from qmf.indicators.comparison import (
    ComparisonReport,
    ContractFormatMint,
    OutputChangeVerdict,
    compare_reference_outputs,
)
from qmf.indicators.configured_indicator import (
    CONTRACT_FORMAT_VERSION,
    IDENTITY_ELEMENTS,
    OPTIONAL_IDENTITY_ELEMENTS,
    AlignmentPolicy,
    ArithmeticReference,
    ChannelKind,
    ConfiguredIndicator,
    DeclaredBudget,
    EmissionPolicy,
    EmissionTiming,
    MissingValuePolicy,
    OutputArity,
    OutputChannel,
    QuoteSide,
    SeriesInput,
    SupportedMode,
    SupportsFp1Identity,
)
from qmf.indicators.conformance import (
    CONCEPT_WALK_REGISTER,
    ConceptCheck,
    ConceptExpression,
    ConceptWalk,
    ConformanceReport,
    check_expressible,
    run_conformance,
)
from qmf.indicators.series import (
    IndicatorSeries,
    InputSeries,
    PresenceState,
    presence_code,
    presence_from_code,
)
from qmf.indicators.streaming import (
    CROSS_TUPLE_IS_A_REGISTERED_ARTIFACT,
    DEFAULT_MODE_EQUALITY_ULPS,
    LEADING_UNDEFINED_MAPPING,
    SEEDING_RULE,
    SNAPSHOT_FORMAT_VERSION,
    ChannelSample,
    ModeEqualityComparator,
    SnapshotScope,
    StreamingHealth,
    StreamingIndicator,
    StreamingObservation,
    StreamingSample,
    StreamingSnapshot,
    assert_mode_equality,
    series_equal_within_ulps,
)
from qmf.indicators.wrappers import (
    WRAPPER_FORMULAS,
    WRAPPER_SET,
    WrapperSpec,
    configure_wrapper,
    reference_lookback,
    wrapper_set_conformance_defects,
    wrapper_spec,
)

__all__ = [
    "CANONICAL_OWNERS",
    "CONCEPT_WALK_REGISTER",
    "CONTRACT_FORMAT_VERSION",
    "CROSS_TUPLE_IS_A_REGISTERED_ARTIFACT",
    "DEFAULT_ANALYTIC_SCALE",
    "DEFAULT_MODE_EQUALITY_ULPS",
    "EXTENSION_DISTRIBUTION_FIELD",
    "EXTENSION_VERSION_FIELD",
    "IDENTITY_ELEMENTS",
    "LEADING_UNDEFINED_MAPPING",
    "OPTIONAL_IDENTITY_ELEMENTS",
    "PERMILLE",
    "SEEDING_RULE",
    "SNAPSHOT_FORMAT_VERSION",
    "WRAPPER_FORMULAS",
    "WRAPPER_SET",
    "AlignmentMode",
    "AlignmentPolicy",
    "ArithmeticReference",
    "AsOfSample",
    "BatchKernel",
    "BatchResult",
    "BenchmarkBaseline",
    "BenchmarkMeasurement",
    "BenchmarkRung",
    "BudgetVerdict",
    "Catalog",
    "ChannelKind",
    "ChannelSample",
    "ComparisonReport",
    "ConceptCheck",
    "ConceptExpression",
    "ConceptWalk",
    "ConfiguredIndicator",
    "ConformanceReport",
    "ContractFormatMint",
    "DeclaredBudget",
    "EmissionPolicy",
    "EmissionTiming",
    "ExtensionIdentity",
    "FormulaOwner",
    "FormulaOwnership",
    "IndicatorSeries",
    "InputSeries",
    "KernelOutput",
    "LightHeavyVerdict",
    "MissingValuePolicy",
    "ModeEqualityComparator",
    "NoOpTickMeasurement",
    "OutputArity",
    "OutputChangeVerdict",
    "OutputChannel",
    "PresenceState",
    "QuoteSide",
    "ReferenceKernel",
    "RegisteredExtension",
    "RegressionReport",
    "RegressionTolerance",
    "ResearchLineage",
    "RungMeasurement",
    "SeriesInput",
    "SnapshotScope",
    "StreamingHealth",
    "StreamingIndicator",
    "StreamingObservation",
    "StreamingSample",
    "StreamingSnapshot",
    "SupportedMode",
    "SupportsFp1Identity",
    "WrapperSpec",
    "__version__",
    "align_to_instant",
    "assert_mode_equality",
    "canonical_owner",
    "check_expressible",
    "compare_reference_outputs",
    "compare_to_baseline",
    "compute_batch",
    "configure_wrapper",
    "evaluate_light_claim",
    "graduate",
    "guard_synchronous_entry",
    "ownership_conformance_defects",
    "presence_code",
    "presence_from_code",
    "reference_grounded_defects",
    "reference_lookback",
    "reference_status",
    "regression_gate",
    "require_extension_identity",
    "require_governed",
    "resolve_canonical_arithmetic",
    "run_conformance",
    "series_equal_within_ulps",
    "stamp_extension_identity",
    "wrapper_set_conformance_defects",
    "wrapper_spec",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
