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
The two-mode compute protocol, the canonical-arithmetic wrappers, and the
conformance harness arrive in later stories. Build, lint, type-check, and test it
through the workspace `poe` tasks — never in isolation.
