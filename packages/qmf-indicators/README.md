# qmf-indicators

The two-mode CT-16 indicator protocol and wrappers around the pinned canonical arithmetic reference.

`qmf-indicators` imports as `qmf.indicators` under the PEP 420 `qmf.*` implicit namespace
(there is no `qmf/__init__.py` in any distribution). It versions in SemVer lockstep with the other six roster packages (0.x until the V1 blueprint ships).

## Status

Scaffold plus the first public contract. Story 1.1 established identity, the
dependency direction, a benchmark-harness slot, and the Tier-1 test surface;
Story 7.1 landed the CT-16 **configured-indicator declaration record and its fp1
identity** — the frozen `ConfiguredIndicator` whose `fp1` (computed by the single
`qmf-core` fingerprint function, nowhere else) spans the entire declared
configuration: the `formula_id`, the per-configured-indicator
`contract_format_version`, the exact-rational `parameters` (a binary float is
refused — exact rationals only), the ordered named `inputs` (each a `SeriesInput`
carrying instrument-or-source identity, a `BarSpec` identity reference, channel
kind, quote side, and — for a derived input — the upstream fingerprint), the
`calendar_requirements` (rule set + version + tzdata version), the
`alignment_policy` and `missing_value_policy`, the `warm_up` count, the ordered
`output_schema`, the `supported_modes`, and the identity-bearing
`ArithmeticReference` — plus the declared-when-present `EmissionPolicy`, warm-up
time bound, and light-claim `DeclaredBudget`. Two configurations differing in any
one element receive distinct fingerprints, that `fp1` is the only dedup key, and
an element missing from the fingerprint is a contract defect (`IDENTITY_ELEMENTS`).

Story 7.2 landed **TA-Lib canonical arithmetic wrapping with the
reference-configuration record asserted at import**. The pinned canonical arithmetic
reference is `registry:canonical_indicator_reference` — TA-Lib C library 0.7.1 +
Python wrapper 0.7.1 — declared as `ta-lib==0.7.1` in this package's `pyproject.toml`
and provisioned into the gate environment through the root `indicators-talib`
dependency group (the same workspace-member pattern as `store-engines` /
`calendar-tzdata` / `venue-proto`); the wheel filename + hash live in `uv.lock`.
**Importing the package asserts the reference-configuration record**: it resolves the
installed reference and, if the resolved artifacts differ from the pin or the
reference's process-global configuration differs from the record, the assertion yields
an `unavailable dependency` refusal (reachable through `reference_status()`), so a
fingerprint never attests arithmetic that was not used (FM-2). The package **never
mutates** the reference's process-global configuration — it only reads
`get_compatibility()` and never calls a setter. Ownership is law (`CANONICAL_OWNERS`,
`FormulaOwnership`): where the reference implements a formula, wrapping it is mandatory
and it is canonical (`REFERENCE`); where it does not — volume-weighted,
session-anchored, QMX-original — this package's own arithmetic is canonical
(`PACKAGE`). `resolve_canonical_arithmetic` enforces mandatory wrapping (a
reference-owned formula requires the verified reference), the conformance checks flag
re-implementing a reference-owned formula as a contract defect (FM-5), and no TA-Lib
object crosses any public boundary.

The two-mode compute protocol, the concrete wrapper set, and the full conformance
harness arrive in later stories. Build, lint, type-check, and test it through the
workspace `poe` tasks — never in isolation.
