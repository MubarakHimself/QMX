# qmf-structure — failure register

Failure-register entries for `qmf-structure`, per the workspace convention
(`conventions/failure-register.md`, NFR-11). One entry per designed failure mode,
written for someone who was not in the design room.

### FR-1: Emission-invariant violation (CT-17, FM-1)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `check_emission_invariant` — run in-component both standalone and inside
  `StructureObject.try_create` at mint — enforces two things. First, a **non-decreasing
  lifecycle chain** `anchor.start <= anchor.end <= observed_at <= confirmed_at <=
  invalidated_at` over whatever lifecycle instants are present (`confirmed_at` /
  `invalidated_at` are absent at mint and validated in place when a later lifecycle record
  supplies them); the refusal's `context` names the offending `earlier` and `later`
  `(label, instant_ns)` pair. Second, **causal availability**: `observed_at` must be at or
  after the maximum evidence time of every input actually consumed (`observed_at` and
  `max_input_evidence_time` in `context`) — a structure object is never derivable before
  the newest input it consumed. Equal instants are legal — equality is consumption, not
  look-ahead (DEC-0106). The anchor span is payload geometry: it is explicitly permitted to
  precede `observed_at` and is **excluded from the causal-availability test** (its instants
  are never compared against consumed-input evidence times), though its own ordering and its
  `end <= observed_at` bound are part of the chain. This is the interim look-ahead guard,
  independent of the deferred GAP-0016 causality registration gate (DEC-0129, DEC-0121).
- **Auto-recovery / retry:** none automatic. The check RETURNS an `invalid input`
  `TypedRefusal` (retryability `no`); no object is minted. The caller corrects the instants
  — a later `observed_at`, an anchor that does not run past it, or the true evidence time of
  the newest consumed input — and retries. Nothing is raised across the boundary.
- **Visible degraded state:** none. No object is admitted and no state changes; a repainted
  or look-ahead object simply never enters governed evidence.
- **Notification tier:** silent-log. An out-of-order chain or an `observed_at` behind a
  consumed input is a wiring/derivation mistake surfaced as a value, not an operational
  alarm.
- **Product-user affordance:** nothing failed at runtime for an end user; a developer or
  family author derived a structure object whose knowledge time was inconsistent with its
  anchor, its lifecycle, or the data it consumed. The refusal's `context` names the exact
  instants in conflict; fix the derivation so `observed_at` is the earliest instant the
  object was genuinely derivable, and retry.

### FR-2: A family whose confirmation rule is not precise (CT-17, FM-2)

- **Failure class:** `invalid input` at the concept level; `policy rejection` at the
  admission gate (both CT-04 refusal categories).
- **Detection:** a family ships into the governed library only when its confirmation rule
  states "confirmed the moment X happens" with X knowable at that instant. Two guards, one
  law. First, `ConfirmationRule.try_create` refuses a blank/absent `descriptor` — the
  imprecise case — as `invalid input` naming `field: descriptor`, so an imprecise concept
  never even produces a rule (it stays free in plain Python). Second, the Story 9.2
  admission gate `admit_to_governed_library(family)` returns a `policy rejection` naming
  `field: confirmation_rule` for a family whose descriptor is nonetheless blank (e.g.
  hand-built past the factory), since a well-formed-but-imprecise concept is one the
  governed library *declines* rather than one that is malformed. Clock-confirmed
  (degenerate) confirmation is legal (a non-blank descriptor with `clock_confirmed = True`),
  and a mechanically stated variant of any school's concept is admissible under the same
  bar; only an imprecise concept is turned away.
- **Auto-recovery / retry:** none automatic. `try_create` RETURNS an `invalid input`
  `TypedRefusal` (retryability `no`); no rule and no family are built. The concept stays
  **freely usable in plain Python outside governed evidence** — the escape hatch is the
  design's point — until its confirmation rule can be stated precisely, at which point the
  family is authored and admitted. Nothing is raised.
- **Visible degraded state:** none. No governed family is admitted; the concept lives in the
  ungoverned research lane and produces no governed evidence.
- **Notification tier:** silent-log. An imprecise rule is a design-stage decision surfaced
  as a value, not an operational alarm.
- **Product-user affordance:** nothing failed for an end user; a family author tried to
  govern a concept whose confirmation moment is not yet precisely stated. State the exact
  instant the object is confirmed (or use the concept freely outside governed evidence for
  now), then author the family and retry.

### FR-3: Invalid structure-object or value construction (CT-17)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** every value factory validates its parts before building and RETURNS a
  typed refusal naming the offending `field`. `FamilyIdentity.try_create` refuses a blank
  `family_id`, a non-positive `version`, or a blank `geometry` (geometry is open — an
  unknown token is a new declaration, not a refusal — but a blank one is refused).
  `AnchorSpan.try_create` refuses a non-`Instant` bound, `start > end`, a non-`Price` price
  bound, cross-instrument bounds, or `low > high`. `StructureObject.try_create` refuses a
  `family` that is not a `StructureFamily` (or whose `identity`/`confirmation_rule` are the
  wrong types), a `parameters` value that is not a name->`ExactRational` mapping (a binary
  float or any non-exact value is refused, so the money-path float ban holds by
  construction), a non-`AnchorSpan` `anchor`, a non-`Instant` `observed_at`, or an
  `evidence_class` outside the closed set — then runs the emission invariant (FR-1). The
  object's `fp1` is **derived** from its identity content, never accepted from the caller,
  so a minted object can never claim a fingerprint its content does not derive.
- **Auto-recovery / retry:** none automatic. The factory RETURNS an `invalid input`
  `TypedRefusal` (retryability `no`) whose `context` names the offending `field`; the caller
  corrects the part and retries. Nothing is raised, and no part is defaulted in place of a
  missing one.
- **Visible degraded state:** none. Construction simply does not yield the value; no state
  changes, and no minted object is ever mutated in place — a correction is a new artifact
  with a `supersedes` edge (FM-3, `refit`), never an in-place edit.
- **Notification tier:** silent-log. A malformed identity, anchor, or parameter part is a
  programming/wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a developer or
  family author supplied a bad part when minting a structure object. The refusal's `context`
  says which field was wrong (and what is allowed); fix the call and retry.

### FR-4: An overwrite, correction, or refit that would mutate an object or edge (CT-17, FM-3)

- **Failure class:** structurally prohibited (no mutation path exists); `invalid input` (a
  CT-04 refusal category) for a malformed refit.
- **Detection:** overwriting is impossible **by construction** — `StructureObject`, every
  lifecycle record (`ConfirmationRecord`, `InvalidationRecord`, `InteractionRecord`), and
  every `LifecycleEdge` are frozen dataclasses, so an in-place edit raises
  `FrozenInstanceError` (a programmer error, not a domain refusal). State evolves **only**
  by appending records; a correction or refit goes through `refit(prior, ...)`, which mints
  a **new** `StructureObject` (same family, anchors frozen at the new fit) and emits a
  `supersedes` `LifecycleEdge` from the new artifact to the prior one, keeping the lineage's
  first observed-at. `refit` RETURNS an `invalid input` refusal when the new `observed_at`
  precedes the prior object's (a refit is observed no earlier than what it supersedes), when
  `first_observed_at` would follow the fit, when the emission invariant fails (FR-1), or
  when the fit is byte-identical to the prior (an identical fit is the same fact, not a new
  artifact — `field: anchor`).
- **Auto-recovery / retry:** none automatic. The prior object and every earlier record stay
  untouched immutable evidence — earlier evidence remains. A refit that is refused yields no
  new artifact; the caller corrects the fit and retries. Nothing is raised across the
  boundary.
- **Visible degraded state:** none. History is never rewritten; a refit only appends a new
  artifact and a `supersedes` edge, and readers resolve "current" from the lineage.
- **Notification tier:** silent-log. An attempted overwrite is a design/wiring mistake
  surfaced as a value (or, for a raw attribute write, an exception the caller never should
  have attempted).
- **Product-user affordance:** nothing failed at runtime for an end user; a developer tried
  to change a minted fact in place. Append an interaction/invalidation record for evolving
  state, or `refit` for a new fit — the refusal's `context` names what to correct.

### FR-5: A read-time state fold over a foreign or pre-observation record (CT-17, FM-1)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `resolve_state(obj, records, at=T)` folds one object's own append-only
  record stream to a knowledge time T — "still valid at T" is a **read-time fold**, never a
  stored field. It RETURNS an `invalid input` refusal (`field: records`) when a record in
  the stream references a different object's `fp1` (a fold is over one object's edge stream)
  or when a record's instant precedes the object's `observed_at` (a lifecycle fact before
  the observation it accrues to is causally impossible — the interim look-ahead guard). A
  record whose instant follows T is not refused: it is simply **not yet visible** at T
  (look-ahead-safe), so a read at an earlier T can never see a later fact. Invalidation
  never cascades automatically — `resolve_state` folds only the object's own records; a
  reader who wants cascade calls `resolve_cascade` with the family's `InvalidationPredicate`
  over the parent's resolved state, an explicit opt-in derivation.
- **Auto-recovery / retry:** none automatic. The fold yields no state on refusal; the caller
  supplies the object's own stream, or corrects the offending record, and retries. Nothing
  is raised.
- **Visible degraded state:** none. No object or record is mutated; the fold is a pure read.
- **Notification tier:** silent-log. A mismatched or pre-observation record is a
  wiring/derivation mistake surfaced as a value.
- **Product-user affordance:** nothing failed for an end user; a developer folded the wrong
  records into an object's state. The refusal's `context` names the object and record
  fingerprints (or the instants in conflict); pass the object's own record stream and retry.
