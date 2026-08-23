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

Story 7.3 landed **batch mode with as-of-only alignment and presence-mapped
outputs**. The bulk series vocabulary (`series.py`) carries a CT-16 column in the
pinned form — immutable little-endian `int64` values, an out-of-band scale, a
parallel integer-encoded presence map (`PresenceState` mirrors
`registry:presence_map_states` verbatim — `present | provisional | not_ready | gap
| absent_by_schedule`), and a parallel knowable-at run: `InputSeries` for an input
column and `IndicatorSeries` for an output channel, whose `equals` compares
presence maps first and values only at present positions. `compute_batch`
(`batch.py`) computes a configured indicator over whole input series and returns
one **full-length, index-aligned** `IndicatorSeries` per output channel plus the
AD-12 result label. Begin-index trimming is prohibited (output length equals input
length); every position carries a presence value; no NaN or sentinel is ever
written. A market-hours-closed input position is `absent_by_schedule` (never a
gap); a calendar-open position with no data follows the declared missing-value
policy — `mark-gap` marks a `gap`, `refuse` returns a `policy rejection` — never
silent filling. Warm-up is an integer count of completed observations, at least the
reference's lookback (a shorter warm-up is refused); during warm-up the output is a
marked `not_ready` value, never a number. Every output sample carries a knowable-at
(the max over its contributing inputs), and provisional samples never enter
governed evidence (`require_governed`). `align_to_instant` aligns a value to an
evaluation instant **as-of only** — the last value known at or before it; a
forward-fill or interpolation request across the instant is a `policy rejection`
(no look-ahead, FM-1). The numeric core is a `BatchKernel` seam; `ReferenceKernel`
is the bridge that wraps the pinned reference where it owns a formula — descaling to
the analytic reference and rescaling its result to a scaled integer under an
explicit half-even rounding mode, so no binary float crosses the engine or persists.

Story 7.4 landed **streaming mode, the tier-2 equality law, and restore-equivalence**
(`streaming.py`): `StreamingIndicator` is the one named stateful class (one `WriterId`
holder, unlimited readers) whose numbers are **equal to batch by construction** — each
update recomputes through the identical `BatchKernel` over the accumulated observations;
`assert_mode_equality` runs the equality law under a per-configuration integer-ULP
comparator (default 0), and a versioned `StreamingSnapshot` scoped to a declared `(OS,
arithmetic-reference build)` tuple gives restore-then-N equals cold-warm-then-N, with a
cross-tuple restore refused (FM-7). Story 7.5 landed **the conformance harness, the
light/heavy benchmark budgets, and the one named catalog surface** (`conformance.py`,
`benchmark.py`, `budget.py`, `catalog.py`).

Story 7.6 landed **the first wrapper set of TA-Lib-backed configured indicators and the
FM-4 arithmetic-upgrade comparison suite**. `WRAPPER_SET` (`wrappers.py`) is the first set
of concrete CT-16 configured indicators — the reference-owned, single-input,
period-taking formulas the batch bridge computes end to end (`sma`, `ema`, `wma`, `rsi`,
`mom`, `roc`), each a `WrapperSpec` that wraps the reference formula (re-implementing the
reference's arithmetic is a contract defect, FM-5, caught by
`wrapper_set_conformance_defects`) with a mechanically stated capability term and **no
trading-school name** in any rule or vocabulary. `configure_wrapper` assembles a full
`ConfiguredIndicator` from an injected period, input set, calendar requirements, and
arithmetic-reference configuration, declaring **both modes** (so the equality law binds)
and setting **warm-up to at least the reference's lookback** (`reference_lookback`) — the
minimum by default, never below it. `compare_reference_outputs` (`comparison.py`) is the
FM-4 comparison suite: it compares a candidate reference's output to the current one over
identical canonical inputs and, on any change, returns a `ComparisonReport` carrying a
`ContractFormatMint` — never a silent accept — that mints the **per-configured-indicator**
contract format version (`previous + 1`) with recorded before/after `fp1` evidence, while
the CT-16 protocol format version stays unchanged (never a protocol-wide bump).

Build, lint, type-check, and test it through the workspace `poe` tasks — never in
isolation.
