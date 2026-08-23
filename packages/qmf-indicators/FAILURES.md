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
