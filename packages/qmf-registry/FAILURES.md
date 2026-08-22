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

### FR-5: Invalid lineage-edge construction (CT-07, FM-2)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `LineageEdge.try_create` validates every part before building — an
  `edge_type` outside the ratified CT-07 set (its `context` names the offending value and
  lists the `allowed` set), a `from_ref` or `to_ref` that is not an `fp1` fingerprint
  (`fp1:sha256:<hex>` — a minted or mutable id is refused), a `writer` that is not a
  `WriterId`, or a non-positive `contract_format_version`. The edge fingerprint is
  **derived** from the identity content and is never accepted from the caller, so an edge
  can never claim an id its content does not derive.
- **Auto-recovery / retry:** none automatic. The factory RETURNS an `invalid input`
  `TypedRefusal` (retryability `no`) whose `context` names the offending `field`; the
  caller corrects the part and retries. Nothing is raised, and no edge is admitted.
- **Visible degraded state:** none. Construction simply does not yield the edge; the
  edge stream is unchanged.
- **Notification tier:** silent-log. A wrong edge kind or a non-`fp1` endpoint is a
  programming/wiring mistake surfaced as a value, not an operational alarm.
- **Product-user affordance:** nothing failed at runtime for an end user; a developer
  wiring lineage used an edge kind outside the ratified set (edge kinds are addable in a
  later version, never invented at a call site) or referenced an endpoint by something
  other than an `fp1` fingerprint. The refusal's `context` says exactly which field was
  wrong (and what is allowed); fix the call and retry.

### FR-6: supersedes linearity violation (CT-07)

- **Failure class:** `policy rejection` (a CT-04 refusal category). The registry-layer
  guard is pure; a `storage failure` category arises only at the qmf-data boundary
  (FM-8, Story 2.4), never here.
- **Detection:** `EdgeLog.append`/`append_edge` holds `supersedes` **pinned linear**. A
  genuinely new `supersedes` edge is refused when its subject already has an outgoing
  `supersedes` edge (a record may supersede at most one record), when the record it
  supersedes already has a superseder (a second would fork "current"), when it points a
  record at itself, or when it would close a cycle in the version chain. A branching
  Book/BMS version graph uses `branches-from` instead, which carries no linearity
  constraint, and a byte-identical re-append of an existing `supersedes` edge is
  idempotent (FR-7), never a linearity violation.
- **Auto-recovery / retry:** none automatic. The append RETURNS a `policy rejection`
  `TypedRefusal` (retryability `no`) whose `context` names the offending `subject` /
  `superseded` fingerprints and what already occupies that slot. Nothing is committed and
  nothing is raised; the caller records a `branches-from` edge instead, or corrects the
  endpoints, then retries.
- **Visible degraded state:** none. The existing chain is unchanged, so "current" stays
  resolvable and unambiguous.
- **Notification tier:** silent-log. An attempt to fork or loop a linear chain is a
  modeling/wiring mistake surfaced as a value, not an operational alarm.
- **Product-user affordance:** nothing failed for an end user; a developer tried to make
  a supersedes chain ambiguous (two "currents") or circular. Use a `branches-from` edge
  for a genuinely branching version graph, where several heads are legal and "current" is
  a separate dated pointer record; otherwise correct the endpoints and retry.

### FR-7: A true fp1 collision on a lineage-edge append (CT-07, FM-2)

- **Failure class:** `policy rejection` (a CT-04 refusal category). The registry-layer
  guard is pure; a `storage failure` category arises only at the qmf-data boundary
  (FM-8, Story 2.4), never here.
- **Detection:** `EdgeLog` keys an append on the edge's `fp1` fingerprint digest and
  reconciles bytes through qmf-core's `reconcile_write`. A first append of an edge
  fingerprint is `stored`; a re-append whose canonical bytes are **byte-identical** is
  `idempotent` and accepted silently (so a repeated identical assertion on a single-writer
  stream dedups); a re-append whose bytes **differ** under the same edge fingerprint is a
  true collision — identity asserted while content differs.
- **Auto-recovery / retry:** none, and the stored edge is **never overwritten**. The
  collision RETURNS a `policy rejection` `TypedRefusal` (retryability `no`) whose
  `context` names the offending `fingerprint`, carries `alarm: true`, and sets
  `notification_tier: alarm`. Nothing is raised across the boundary.
- **Visible degraded state:** none in this pure guard — the prior edge remains and a
  byte-identical re-append stays idempotent. Durable storage (Story 2.4, qmf-data)
  surfaces the alarm operationally.
- **Notification tier:** alarm. A true collision is an identity-integrity event, not a
  routine input mistake, so it is surfaced loudly rather than silent-logged.
- **Product-user affordance:** nothing an end user did caused this; it is an
  identity-integrity event a developer or operator must investigate. The refusal's
  `context` names the edge fingerprint under which two different byte sequences collided;
  the append is refused and the original edge is preserved untouched.

### FR-8: Wrong writer on a single-writer edge stream (CT-07)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** an `EdgeLog` holds exactly one `WriterId`. `append` always stamps that
  writer, and `append_edge` refuses a pre-built edge whose `writer` is not the stream's
  writer; the refusal's `context` names both the `stream_writer` and the `edge_writer`.
  An edge stream has exactly one writer and unlimited readers.
- **Auto-recovery / retry:** none automatic. The append RETURNS a `policy rejection`
  `TypedRefusal` (retryability `no`); nothing is committed and nothing is raised. The
  caller opens a separate edge stream for the other writer, then retries.
- **Visible degraded state:** none. The stream is unchanged.
- **Notification tier:** silent-log. A cross-writer append is a wiring mistake surfaced
  as a value.
- **Product-user affordance:** nothing failed for an end user; a developer appended an
  edge minted by a different writer onto a stream that already has its own single writer.
  Each edge stream has exactly one writer — open a stream per writer — then retry.
