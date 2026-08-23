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
from qmf.indicators.series import (
    IndicatorSeries,
    InputSeries,
    PresenceState,
    presence_code,
    presence_from_code,
)

__all__ = [
    "CANONICAL_OWNERS",
    "CONTRACT_FORMAT_VERSION",
    "DEFAULT_ANALYTIC_SCALE",
    "IDENTITY_ELEMENTS",
    "OPTIONAL_IDENTITY_ELEMENTS",
    "AlignmentMode",
    "AlignmentPolicy",
    "ArithmeticReference",
    "AsOfSample",
    "BatchKernel",
    "BatchResult",
    "ChannelKind",
    "ConfiguredIndicator",
    "DeclaredBudget",
    "EmissionPolicy",
    "EmissionTiming",
    "FormulaOwner",
    "FormulaOwnership",
    "IndicatorSeries",
    "InputSeries",
    "KernelOutput",
    "MissingValuePolicy",
    "OutputArity",
    "OutputChannel",
    "PresenceState",
    "QuoteSide",
    "ReferenceKernel",
    "SeriesInput",
    "SupportedMode",
    "SupportsFp1Identity",
    "__version__",
    "align_to_instant",
    "canonical_owner",
    "compute_batch",
    "ownership_conformance_defects",
    "presence_code",
    "presence_from_code",
    "reference_grounded_defects",
    "reference_status",
    "require_governed",
    "resolve_canonical_arithmetic",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
