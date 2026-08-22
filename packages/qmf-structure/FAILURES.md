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

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** a family ships into the governed library only when its confirmation rule
  states "confirmed the moment X happens" with X knowable at that instant.
  `ConfirmationRule.try_create` refuses a blank/absent `descriptor` — the imprecise case —
  naming `field: descriptor`. Clock-confirmed (degenerate) confirmation is legal (a
  non-blank descriptor with `clock_confirmed = True`), and a mechanically stated variant of
  any school's concept is admissible under the same bar; only an imprecise concept is turned
  away.
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
  with a `supersedes` edge (FM-3, later stories), never an in-place edit.
- **Notification tier:** silent-log. A malformed identity, anchor, or parameter part is a
  programming/wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a developer or
  family author supplied a bad part when minting a structure object. The refusal's `context`
  says which field was wrong (and what is allowed); fix the call and retry.
