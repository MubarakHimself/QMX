# qmf-indicators — failure register

Failure-register entries for `qmf-indicators`, per the workspace convention
(`conventions/failure-register.md`, NFR-11). One entry per designed failure mode,
written for someone who was not in the design room.

### FR-1: A binary float on the parameter path (CT-16, FM-1)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `ConfiguredIndicator.try_create` validates its `parameters` before
  building. Each parameter value must be a `qmf.core.ExactRational` (a scaled integer
  or a numerator/denominator pair); a binary `float` is caught explicitly, and any
  other non-`ExactRational` value is refused too, so a float can never appear in a
  parameter or in the configuration's `fp1` identity. `ExactRational.try_create` itself
  refuses a float numerator/denominator upstream, and the workspace money-path scanner
  fails the gate on any such float in shipped source.
- **Auto-recovery / retry:** none automatic. The factory RETURNS an `invalid input`
  `TypedRefusal` (retryability `no`) whose `context` names the `parameters` field, the
  offending `parameter` name, and the given value. Nothing is raised across the boundary.
- **Visible degraded state:** none. No configuration is produced; no state changes.
- **Notification tier:** silent-log. A float on the parameter path is a programming
  mistake surfaced as a value, not an operational alarm.
- **Product-user affordance:** nothing failed at runtime for an end user; a developer
  declared a parameter as a binary float where an exact rational belongs. Build the
  parameter from `ExactRational.try_create(numerator, denominator, unit_kind)` (a scaled
  integer or a num/den pair) and retry — exact rationals keep every configured
  indicator's identity float-free by construction.

### FR-2: An identity element missing from the fingerprint (CT-16, contract defect)

- **Failure class:** contract defect (caught by the conformance test, not a runtime
  refusal).
- **Detection:** a configured indicator's identity is the **entire declared
  configuration**, and its `fp1` is the only dedup key. `IDENTITY_ELEMENTS` names every
  required identity element; `ConfiguredIndicator.fp1_identity` must place every one of
  them in the fingerprint content. The Tier-1 conformance tests assert that each
  `IDENTITY_ELEMENTS` key is present in the fingerprint content and that removing any one
  element changes the fingerprint — so an element that is stored but silently left out of
  identity fails the test. An element missing from the fingerprint is a contract defect,
  not a tolerated omission.
- **Auto-recovery / retry:** none — this is a build-time gate, not a runtime path. The
  defect is fixed by adding the element back into the fingerprint content (and, if it is a
  new element, into `IDENTITY_ELEMENTS`).
- **Visible degraded state:** none in production, because the gate blocks the defect from
  shipping. Were such a defect to escape, two configurations differing only in the dropped
  element would collide on one `fp1` and deduplicate as if identical — the exact silent
  drift the identity discipline exists to prevent.
- **Notification tier:** gate failure (the Tier-1 test suite reads red).
- **Product-user affordance:** not user-facing; it is an identity-integrity invariant the
  factory gate enforces before any configuration reaches evidence.

### FR-3: A malformed configuration part (CT-16, FM-1 family)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `ConfiguredIndicator.try_create` (and the `SeriesInput`,
  `OutputChannel`, `EmissionPolicy`, `DeclaredBudget`, and `ArithmeticReference`
  factories it composes) validate every declared part before building: a blank
  `formula_id`, a non-positive `contract_format_version`, an empty or non-sequence input
  set, a duplicate input or output-channel name, a channel kind / quote side / arity /
  alignment / missing-value / supported-mode outside its closed set, a calendar
  requirement that is not a `CalendarIdentity`, a bar-spec reference that is not
  fp1-clean identity content, a negative `warm_up`, an arithmetic reference that is not an
  `ArithmeticReference`, or a mistyped optional element. The unchecked frozen dataclass
  constructor performs no such validation and is for trusted internal callers.
- **Auto-recovery / retry:** none automatic. Each factory RETURNS an `invalid input`
  `TypedRefusal` (retryability `no`) whose `context` names the offending `field` (and,
  where relevant, the index, name, or allowed set); the caller corrects the part and
  calls again. Nothing is raised across the boundary, and a part is never defaulted in
  place of a missing one.
- **Visible degraded state:** none. Construction simply does not yield the configuration;
  no global or persistent state changes.
- **Notification tier:** silent-log. A malformed configuration part is a programming or
  wiring mistake surfaced as a value, not an operational alarm.
- **Product-user affordance:** nothing failed at runtime for an end user; a developer
  assembling a configured indicator at the composition root supplied a bad part. The
  refusal's `context` says which field (and index or name) was wrong and what is allowed;
  fix the call and retry.

### FR-4: The canonical arithmetic reference is unavailable or mismatched (CT-16, FM-2)

- **Failure class:** `unavailable dependency` (a CT-04 refusal category).
- **Detection:** importing `qmf.indicators` asserts the reference-configuration record of
  `registry:canonical_indicator_reference` (TA-Lib C 0.7.1 + Python wrapper 0.7.1). The
  `_reference` module resolves the installed reference — importing the pinned wrapper
  lazily and by name, then reading its wrapper version, C-library version, and
  process-global compatibility mode **without mutating anything** — and asserts three
  things: the reference is importable; the resolved artifacts equal the pin
  (`verify_artifact_pin`); and the reference's process-global configuration equals the
  reference-configuration record (`verify_reference_configuration`). A missing reference,
  a resolved version differing from the pin (the runtime-checkable form of "the resolved
  artifacts differ from the lockfile pin"), or a process-global configuration differing
  from the record each fails the assertion. A fingerprint must never attest arithmetic
  that was not the arithmetic used.
- **Auto-recovery / retry:** none automatic; retryability is `no` — a missing,
  mis-versioned, or mis-configured reference is a provisioning/wiring condition a retry
  cannot fix. The assertion RETURNS an `unavailable dependency` `TypedRefusal` (reachable
  through `reference_status()`), never raised — importing the package on a machine without
  the pinned artifact stays safe, and a reference-owned formula then refuses through
  `resolve_canonical_arithmetic` rather than falling back to re-implemented arithmetic.
- **Visible degraded state:** the package is not a usable canonical-arithmetic provider;
  `reference_status()` carries the refusal and `reference_ready` is `false`. No
  process-global state changes — the package never mutates the reference's configuration.
- **Notification tier:** silent-log at import; the refusal is a value a composition root
  inspects, not an operational alarm.
- **Product-user affordance:** the pinned reference must be installed and configured as
  the record declares. The refusal's `context` names the offending field and the
  pinned-versus-resolved values (or the missing/differing configuration field); provision
  `ta-lib==0.7.1` (its wheel bundles the C library on the tier-1 OSes) and retry.

### FR-5: A vendor object crosses CT-16, or a reference formula is re-implemented (CT-16, FM-5)

- **Failure class:** contract defect (caught by the conformance tests, not a runtime
  refusal).
- **Detection:** two invariants. First, **package neutrality** — no TA-Lib or other
  vendor object appears in any public signature or output; the raw reference module
  handle stays private to `_reference` and the resolved identity is projected into the
  package-neutral `ArithmeticReference`, so the public surface returns only qmf-core /
  stdlib values and CT-04 refusals. Second, **one canonical owner per formula** — where
  the reference implements a formula, wrapping it is mandatory and canonical, and
  re-implementing it is a defect. `ownership_conformance_defects` (structural) flags a
  package-owned formula that names a reference function, and `reference_grounded_defects`
  (verified against the live reference) flags a package-owned formula whose name the
  reference actually implements, or a reference-owned formula naming a function the
  reference lacks. The Tier-1 tests assert the shipped `CANONICAL_OWNERS` registry is
  conformant on both and that a synthetic re-implementation is caught.
- **Auto-recovery / retry:** none — these are build-time gates, not runtime paths. A
  neutrality breach is fixed by keeping the vendor object private; a re-implementation is
  fixed by declaring the formula reference-owned and wrapping it (or, for a formula the
  reference genuinely lacks, keeping it package-owned).
- **Visible degraded state:** none in production, because the gates block the defect from
  shipping. Were a re-implementation to escape, two governed producers could publish
  divergent arithmetic for one formula — the exact drift the wrap-not-reimplement law
  exists to prevent.
- **Notification tier:** gate failure (the Tier-1 conformance tests read red).
- **Product-user affordance:** not user-facing; it is a canonical-arithmetic-integrity
  invariant the factory gate enforces before any wrapper reaches evidence.

### FR-6: Forward-fill or interpolation across the evaluation instant (CT-16, FM-1)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `align_to_instant` aligns a bulk series to an evaluation instant. Only
  as-of alignment — the last present value whose knowable-at is at or before the instant —
  is legal for governed evidence. A `forward-fill` or `interpolate` request is refused
  before any value is read, because both would draw on data known only *after* the
  instant (look-ahead across the evaluation instant). The `AlignmentMode` enum names the
  two illegal modes precisely so the refusal is nameable and testable; they are never
  usable values.
- **Auto-recovery / retry:** none automatic; retryability is `no` — the request is a
  policy violation, not a transient condition. The operation RETURNS the `policy
  rejection` `TypedRefusal` whose `context` names the requested mode. Nothing is raised.
- **Visible degraded state:** none. No value is produced; no state changes.
- **Notification tier:** silent-log. A look-ahead alignment request is a wiring mistake
  surfaced as a value, not an operational alarm.
- **Product-user affordance:** governed evidence forbids look-ahead across the evaluation
  instant. Align as-of (the last value known at or before the instant); if a later value
  is genuinely wanted, evaluate at a later instant. The refusal's `context` says which
  mode was refused.

### FR-7: A calendar-open gap under a refuse missing-value policy (CT-16, FM-1)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** during `compute_batch`, a position the market-hours calendar marks
  closed is `absent_by_schedule` (never a gap), but a calendar-open position with no data
  follows the configuration's declared missing-value policy. Under `mark-gap` the output
  position is a `gap`; under `refuse` the whole batch is refused rather than silent-filled.
  The layout analysis detects the gap position and refuses immediately.
- **Auto-recovery / retry:** none automatic; retryability is `no`. The operation RETURNS
  the `policy rejection` `TypedRefusal` naming the `missing_value_policy` field and the
  offending position. Nothing is raised, and no value is ever fabricated for the gap.
- **Visible degraded state:** none. No output series is produced; no state changes.
- **Notification tier:** silent-log. The refusal is a value the composition root inspects.
- **Product-user affordance:** the input has a calendar-open gap and the configuration
  declared a refuse policy. Either supply the missing observation, or declare a `mark-gap`
  policy so the gap is presence-mapped rather than refused — never silently filled.

### FR-8: Warm-up below the reference lookback (CT-16, warm-up discipline)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `compute_batch` resolves the reference's lookback from the kernel output
  (the leading-undefined count) and refuses if the configuration's `warm_up` is below it.
  Warm-up is an integer count of completed input observations at least the reference's
  lookback; a marked not-ready value must cover every undefined leading position, so a
  warm-up shorter than the lookback is a contract error.
- **Auto-recovery / retry:** none automatic; retryability is `no`. The operation RETURNS
  the `invalid input` `TypedRefusal` naming the `warm_up` field, the declared warm-up, and
  the reference lookback. Nothing is raised.
- **Visible degraded state:** none. No output series is produced; no state changes.
- **Notification tier:** silent-log. A too-short warm-up is a configuration mistake
  surfaced as a value, not an operational alarm.
- **Product-user affordance:** raise the configuration's warm-up to at least the
  reference's lookback (the refusal's `context` names both) and recompute.

### FR-9: Provisional samples reaching governed evidence (CT-16, DEC-0126)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** an in-progress emission policy (or a provisional contributing input)
  marks output positions `provisional`, and the result's evidence class becomes
  `provisional`. `require_governed` refuses any result whose evidence class is provisional
  or that carries a provisional output position — provisional samples never enter governed
  evidence.
- **Auto-recovery / retry:** none automatic; retryability is `no`. The guard RETURNS the
  `policy rejection` `TypedRefusal` naming the evidence class or the offending channel.
  Nothing is raised, and no provisional value is admitted.
- **Visible degraded state:** none. The confirmed label is simply not returned for
  routing into the governed-evidence store.
- **Notification tier:** silent-log. The refusal is a value the composition root inspects
  before it routes a result into governed evidence.
- **Product-user affordance:** compute with a bar-closed emission policy (which yields a
  confirmed result) before routing into governed evidence; a provisional/in-progress
  result is for live display, never for governed evidence.

### FR-10: A snapshot restored on a different (OS, arithmetic-reference build) tuple (CT-16, FM-7)

- **Failure class:** `unavailable dependency` (a CT-04 refusal category).
- **Detection:** a `StreamingSnapshot` is a serialized contract with its own format
  version (`SNAPSHOT_FORMAT_VERSION`) scoped to a declared `(OS, arithmetic-reference
  build)` tuple (`SnapshotScope`). `StreamingIndicator.restore` takes the *current* scope
  (injected by the composition root, never read ambiently) and compares it to the
  snapshot's scope before resuming any state; a differing OS or a differing
  arithmetic-reference build fails the check. The reference's floating-point arithmetic —
  and therefore the resumed streaming state — is only attestable within one tuple, so a
  result from restored state must never attest arithmetic that was not the arithmetic used.
- **Auto-recovery / retry:** none automatic; retryability is `no` — a cross-tuple mismatch
  is a provisioning condition a retry cannot fix. `restore` RETURNS an `unavailable
  dependency` `TypedRefusal` naming the `scope` field and both the snapshot and current
  scope tuples. Nothing is raised, and no state is resumed.
- **Visible degraded state:** none. No streaming instance is produced; the snapshot is
  untouched and remains restorable on its own tuple.
- **Notification tier:** silent-log. The refusal is a value the composition root inspects
  before it resumes a stream.
- **Product-user affordance:** resume the snapshot on the same OS and pinned
  arithmetic-reference build it was produced on; a cross-tuple resume is deliberately
  refused rather than silently producing drifted numbers. A same-process/same-build
  equality is the gate — cross-OS or cross-build agreement is a separate registered
  comparison artifact, never a resume path.
