# qmf-registry — failure register

Failure-register entries for `qmf-registry`, per the workspace convention
(`conventions/failure-register.md`, NFR-11). One entry per designed failure mode,
written for someone who was not in the design room.

### FR-1: Unregistered, reserved, or undefined-field registration (CT-06, FM-1)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** registration resolves its kind through `KindRegistry.contract_for`
  and admits its body through the resolved `KindContract.validate_body`. A kind that
  was never registered is refused as **unknown** (its `context` names the offending
  `kind` and lists the `known` kinds); one of the two honored reserved names
  (`promotion-occurrence-card`, `treasury-boundary-event`) is refused as **reserved**
  (`reserved: true`) — its body is defined by its own dedicated contract, never the
  generic path; and a body carrying a field the kind's contract does not define (or
  missing a required one) is refused with the offending `unknown` / `missing` field
  names. Kinds — and a kind's field set — are addable in a later version, never
  redefined.
- **Auto-recovery / retry:** none automatic. The operation RETURNS the `invalid input`
  `TypedRefusal` (retryability `no`); the caller registers the kind first, corrects the
  body to the kind's field set, or routes a reserved kind through its own contract, then
  retries. Nothing is raised across the boundary, and no record is written.
- **Visible degraded state:** none. No record is admitted; no stored state changes.
- **Notification tier:** silent-log. A wrong kind name or a body field outside a kind's
  contract is a programming/wiring mistake surfaced as a value, not an operational
  alarm.
- **Product-user affordance:** nothing failed at runtime for an end user; a developer
  wiring a registration named a kind the registry does not define, tried to mint a
  reserved kind through the generic path, or supplied a body field the kind's contract
  does not carry. The refusal's `context` says exactly which kind or field was wrong (and
  what is allowed); fix the call and retry.

### FR-2: Kind redefinition attempt (CT-06)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `KindRegistry.register` refuses a contract whose name is already
  registered, or whose name is one of the reserved names, or whose name is blank or
  format version non-positive. Kinds are **addable but never redefined**: the roster
  only grows, and an existing kind's meaning never mutates in place.
- **Auto-recovery / retry:** none automatic. `register` RETURNS an `invalid input`
  `TypedRefusal` (retryability `no`) naming the offending `kind`; to change a kind's
  meaning a caller mints a NEW kind (or a new format version), never re-registers the
  old name. Nothing is raised.
- **Visible degraded state:** none. The existing kind roster is unchanged.
- **Notification tier:** silent-log. A duplicate/redefine registration is a wiring
  mistake surfaced as a value.
- **Product-user affordance:** nothing failed for an end user; a developer tried to
  register a kind that already exists (or to claim a reserved name). Add a new kind or a
  new format version instead of redefining an existing one, then retry.

### FR-3: Invalid registration-record construction (CT-06)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `RegistrationRecord.try_create` validates every header part before
  building — a blank `kind`, a non-positive `contract_format_version`, an
  `at_birth_parent_refs` that is not a sequence of `fp1` fingerprints, a non-mapping
  `body`, a body that is not `fp1`-clean identity content (a binary float, a null, or a
  non-string key — refused by qmf-core when the identity is fingerprinted), a `writer`
  that is not a `WriterId`, a negative/non-integer `sequence`, or a `created_at` that is
  not an `Instant`. The stable id is **derived** from the identity content and is never
  accepted from the caller, so a record can never claim an id its content does not
  derive.
- **Auto-recovery / retry:** none automatic. The factory RETURNS an `invalid input`
  `TypedRefusal` (retryability `no`) whose `context` names the offending `field`; the
  caller corrects the part and retries. Nothing is raised, and no part is defaulted in
  place of a missing one.
- **Visible degraded state:** none. Construction simply does not yield the record.
- **Notification tier:** silent-log. A malformed header/body part is a programming
  mistake surfaced as a value.
- **Product-user affordance:** nothing failed at runtime for an end user; a developer
  building a registration supplied a bad header or body part. The refusal's `context`
  says which field was wrong; fix the call and retry. History is never rewritten — a
  correction is a new record with new CT-07 lineage, never an in-place edit.

### FR-4: A true fp1 collision on a registration write (CT-06, FM-6)

- **Failure class:** `policy rejection` (a CT-04 refusal category). The registry-layer
  guard is pure; a `storage failure` category arises only at the qmf-data boundary
  (FM-8, Story 2.4), never here.
- **Detection:** `Registrar` keys a write on the record's `fp1` stable-id digest and
  reconciles bytes through qmf-core's `reconcile_write`. A first write of a stable id is
  `stored`; a re-write whose canonical bytes are **byte-identical** is `idempotent` and
  accepted silently (so identical work from two sandboxes deduplicates); a re-write whose
  bytes **differ** under the same stable id is a true collision — identity asserted while
  content differs.
- **Auto-recovery / retry:** none, and the stored record is **never overwritten**. The
  collision RETURNS a `policy rejection` `TypedRefusal` (retryability `no`) whose
  `context` names the offending `fingerprint`, carries `alarm: true`, and sets
  `notification_tier: alarm`. Nothing is raised across the boundary.
- **Visible degraded state:** none in this pure guard — the prior record remains and a
  byte-identical re-write stays idempotent. Durable storage (Story 2.4, qmf-data)
  surfaces the alarm operationally.
- **Notification tier:** alarm. A true collision is an identity-integrity event, not a
  routine input mistake, so it is surfaced loudly rather than silent-logged.
- **Product-user affordance:** nothing an end user did caused this; it is an
  identity-integrity event a developer or operator must investigate. The refusal's
  `context` names the stable id under which two different byte sequences collided; the
  write is refused and the original record is preserved untouched.
