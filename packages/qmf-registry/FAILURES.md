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
  redefined. Reserved names are honored on **every** admission path, not only the
  `KindRegistry`/`Registrar` surface: the public `RegistrationRecord.try_create` refuses
  a reserved kind outright (`reserved: true`), and `RegistryPersistence.persist_record`
  refuses a reserved-kind record that was not minted through its dedicated signing path
  (FR-9's `policy rejection`), so a promotion-occurrence card can never be forged by
  minting a reserved-kind record with a card-shaped body and persisting it (Story 2.1
  AC4; DEC-0116, DEC-0158). Only `PromotionCard.sign` mints a reserved kind, through the
  package-internal reserved-mint path that marks the record genuine.
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
- **Detection:** `EdgeLog.append`/`append_edge` holds `supersedes` **pinned linear** in the
  in-memory reference stream, and `RegistryPersistence.persist_edge` holds it **on the
  durable path too, and room-wide**: CT-07's one-resolvable-head invariant is a property of
  the whole registry room, not of any single stream, so before a genuinely new `supersedes`
  edge is appended the persisted edge set **across every edge stream in the room** (each read
  back and witness-verified) is consulted and the same law applied to all of it. A genuinely
  new `supersedes` edge is refused when its subject already has an outgoing `supersedes` edge
  **on any stream** (a record may supersede at most one record), when the record it supersedes
  already has a superseder **on any stream** (a second would fork "current"), when it points a
  record at itself, or when it would close a cycle in the version chain — so a fork can never
  hide by landing on a second edge stream. A branching Book/BMS version graph uses
  `branches-from` instead, which carries no linearity constraint, and a byte-identical
  re-append of an existing `supersedes` edge is idempotent (FR-7), decided by the store's own
  fp1, never a linearity violation. The invariant therefore holds for persisted evidence
  room-wide, not only within one stream or the in-memory `EdgeLog` — a durable registry room
  can never fork "current" (M1).
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

### FR-9: Live promotion with no human-signed promotion-occurrence card (CT-06, FM-4)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `authorize_live_promotion` is the refusal law for crossing into the live
  zone. It is refused when no human-signed promotion-occurrence card is present (`card` is
  `None`); when a card IS present but attests a different record than the one requested (its
  `context` names both the `attested` and `requested` fingerprints); and when the present
  card has been **superseded** by a later signed correction — the gate consults the
  supersedes state the caller **must supply** (`superseded` is a required argument with **no
  default**: a collection of superseded card fingerprints, or of CT-07 `supersedes`
  `LineageEdge`s to read them from) and refuses a card whose `fp1` appears there
  (`superseded_card` in `context`), because only the **current head** of the supersedes chain
  speaks for live money (FM-5). The caller's obligation is explicit: **omitting** `superseded`
  is a programmer error (a `TypeError` at call time, AR-13) and passing `None` is an `invalid
  input` wiring refusal — neither can silently skip the only-the-current-head check — while an
  **empty collection** is the legitimate answer meaning "I checked; nothing supersedes this
  card"; any other malformed value is likewise an `invalid input` wiring refusal. When the
  present card attests an **AD-32 template** (`template_definition_fp1`),
  the gate additionally **requires** the current in-force template fingerprint as its
  `in_force_template_fp1` argument and refuses on any mismatch (`policy rejection`, naming the
  `attested_template` and `in_force_template`); an **absent** argument is itself a refusal, never
  a silent skip, and a malformed one is an `invalid input` wiring refusal — so a signature can
  never authorize a crossing under a superseded template (DEC-0158; AD-32). A card that carries
  no template does not consult it. Only a human promotes an artifact into the live zone (AR-39,
  DEC-0041); an agent's passed checks or recommendation is never an authorization, and neither
  is a superseded card or a card attesting a superseded template.
- **Auto-recovery / retry:** none automatic. The gate RETURNS a `policy rejection`
  `TypedRefusal` (retryability `no`); promotion does not occur and no live capability is
  granted. A human must sign a promotion-occurrence card attesting THIS record (its exact
  `fp1` and, for a risk admission, the exact template fingerprint), after which the request
  is made again. Nothing is raised.
- **Visible degraded state:** none. The artifact stays in its pre-promotion zone; no live
  capability is granted and no state changes.
- **Notification tier:** operator-visible. The absence of a human signature on the path to
  live money is a decision surfaced to the operator, not a silent log line — but it is a
  normal governance outcome, not an alarm.
- **Product-user affordance:** nothing failed at runtime; the platform refused to move an
  artifact toward live money because no human signed off on it (or the signature was for a
  different artifact). A human must read the plain-words summary and sign the promotion
  card attesting this exact artifact; passing any number of automated checks cannot
  substitute for that signature.

### FR-10: Invalid promotion-card construction (CT-06, ADR-0015)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `PromotionCard.sign` validates every part before minting — a blank
  `signer` (the human-only reviewer identity), a blank or missing `plain_words_summary` (it
  is mandatory and an identity field), an `attested_fp1` that is not an `fp1` fingerprint, a
  `template_definition_fp1` (for an AD-32 risk admission) that is not an `fp1` fingerprint,
  or a `signed_at` that is not an `Instant`; the delegated `RegistrationRecord` factory then
  refuses a bad `writer` or `sequence`. V1 signing takes no cryptographic dependency — the
  signer is the recorded reviewer identity — and the stable id is derived from the card's
  identity content, never accepted from the caller.
- **Auto-recovery / retry:** none automatic. `sign` RETURNS an `invalid input`
  `TypedRefusal` (retryability `no`) whose `context` names the offending `field`; the caller
  corrects the part and retries. Nothing is raised, and no card is minted.
- **Visible degraded state:** none. Construction simply does not yield a card; no state
  changes.
- **Notification tier:** silent-log. A malformed card part is a programming/wiring mistake
  surfaced as a value.
- **Product-user affordance:** nothing failed for an end user; a developer or workflow
  assembling a promotion card supplied a bad part (a missing summary, a non-`fp1` attested
  reference, and so on). The refusal's `context` says which field was wrong; fix it and
  retry — the plain-words summary is mandatory because the signature attests the exact words
  a human read.

### FR-11: Promotion-summary correction that supersedes nothing (CT-06, CT-07, FM-5)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `correct_summary` mints a NEW card with the corrected summary and a CT-07
  `supersedes` edge linking it to the prior card. The corrected card is signed under a
  **fresh human approval**: the required `signer` argument is the reviewer who read the NEW
  words, and the new card is signed under it — never the prior card's signature reused over
  words that human never read (that reuse is exactly the forgery this refuses; H2, ADR-0015).
  It is refused when `prior` is not a `PromotionCard`, when `signer` is blank or absent (no
  fresh approval), when the corrected summary is itself invalid (a blank summary, a bad
  writer/sequence — propagated from `PromotionCard.sign`), when the corrected summary is
  UNCHANGED under the same signer (it would mint the identical card, with nothing to
  supersede), or when the supersedes-edge writer is not a `WriterId` (propagated from
  `LineageEdge.try_create`). The signed record is never edited in place — a correction is
  always a new card, because the signature attests the exact words read.
- **Auto-recovery / retry:** none automatic. The operation RETURNS an `invalid input`
  `TypedRefusal` (retryability `no`) whose `context` names the offending field; the caller
  supplies a genuinely different, valid summary (and valid writers) and retries. Nothing is
  raised, no card is minted, and no edge is appended.
- **Visible degraded state:** none. The prior card and its lineage are unchanged.
- **Notification tier:** silent-log. A degenerate or malformed correction is a
  programming/wiring mistake surfaced as a value.
- **Product-user affordance:** nothing failed for an end user; a developer tried to correct
  a signed summary with the same words, a malformed summary, or a bad writer. To fix a typo,
  supply the corrected words — a new signed card is minted and linked to the prior one; the
  original signed card is preserved untouched because the signature attests the exact words
  read.

### FR-12: Unpersistable promotion journal event (CT-13, block-on-unpersistable)

- **Failure class:** `storage failure` (a CT-04 refusal category), for the unpersistable
  path; `invalid input` for a wiring mistake.
- **Detection:** `emit_promotion_event` builds the CT-13 promotion event (only the card's
  `fp1` plus `correlation_id`) and appends it through the core `JournalSink` injected at the
  composition root. When the sink cannot durably persist the event it returns a
  `storage failure` refusal (recognized by `is_unpersistable`); a `card` that is not a
  signed `PromotionCard`, or a `sink` that is not a `JournalSink`, is an `invalid input`
  refusal before anything is emitted. The registry card stays canonical — the journal never
  holds a second promotion schema.
- **Auto-recovery / retry:** none automatic. On a `storage failure` the writer that holds
  the `WriterId` must **block its command stream** until the store recovers, then re-emit
  (block-on-unpersistable) — the intent is never dropped and success is never assumed. On an
  `invalid input` the caller fixes the card or the sink wiring and retries. Nothing is
  raised.
- **Visible degraded state:** the emitting writer's command stream is blocked until the
  journal append lands; the promotion card itself is already canonical in the registry, so
  no promotion fact is lost — only its journal pointer is pending. (Physical persistence
  lands in Story 2.4; this seam surfaces the refusal.)
- **Notification tier:** operator-visible for the storage failure (a blocked stream needs
  attention); silent-log for the wiring `invalid input`.
- **Product-user affordance:** nothing an end user did caused an unpersistable event; the
  journal store is unavailable, so the platform blocks rather than pretending the event
  landed. It resumes once storage recovers. A wiring `invalid input` means a developer
  passed a bad card or sink — the refusal's `context` says which; fix it and retry.

### FR-13: Cross-world read or simulated-world persistence (CT-09, FM-7)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `RegistryPersistence` is bound to exactly one world's registry room.
  `RegistryPersistence.open` for `world = simulated` is refused when the qmf-data store
  resolves the per-world bundle — `simulated` has no governed namespace in V1, so a non-live
  world never writes the live evidence namespace. Every read declares the world it reads as
  (there is no implicit same-world default): `load_record` / `read_edges` with a `for_world`
  that differs from the room's world are refused at the qmf-data boundary. World isolation is
  storage separation, so one world's room never serves another's evidence.
- **Auto-recovery / retry:** none automatic. The operation RETURNS a `policy rejection`
  `TypedRefusal` (retryability `no`); nothing is read or written. The caller opens the
  correct world's persistence (never `simulated` in V1) and declares the matching `for_world`,
  then retries. Nothing is raised across the seam.
- **Visible degraded state:** none. No cross-world data is served and no simulated evidence is
  written; stored state is unchanged.
- **Notification tier:** silent-log. A cross-world read or a simulated-world write is a
  wiring/governance mistake surfaced as a value, not an operational alarm.
- **Product-user affordance:** nothing failed at runtime for an end user; a developer read a
  record or edge as the wrong world, or tried to persist into the reserved `simulated` world.
  The refusal's `context` names the requested and room worlds; open the right world and declare
  the matching read world, then retry — `simulated` stays unusable until GAP-0048.

### FR-14: Underlying store failure or corrupt persisted artifact (CT-09, FM-8)

- **Failure class:** `storage failure` (a CT-04 refusal category).
- **Detection:** every persist/load routes through qmf-data's CT-11 store seam, which
  **translates a store-library exception to a `storage failure` typed refusal at the qmf-data
  boundary** — a disk-full, corrupt, locked, or truncated store never propagates as an
  exception across the package seam (`RegistryPersistence.persist_record` /
  `persist_edge` / `load_record` / `read_edges` simply return the store's refusal). A read
  that returns bytes the registry cannot parse back into its CT-06/CT-07 shape — corrupt
  stored evidence, since the writes here are canonical by construction — is itself surfaced as
  a `storage failure` (retryability `no`), never served as a valid or wrong artifact.
  Read-back is verified against a tamper-independent authority, so a **silently altered**
  artifact never reads back as valid either: a record is stored keyed on its **own fp1 stable
  id** (the stored bytes ARE its CT-06 fp1 identity content, no wrapping envelope; M2), so
  `load_record` recomputes that fp1 over the persisted identity and refuses (`storage failure`)
  when it does not equal the key the record was read under — one recompute both verifies
  integrity and yields the stable id, and tampered canonical bytes (the digest key unchanged)
  are caught. A lineage edge — persisted to a
  JSONL stream whose per-line index is rebuilt from the line bytes on read (AR-31), which
  carries no tamper-independent authority of its own — is additionally anchored by a
  tamper-evident **integrity witness** in the (content-addressed, SQLite) record store;
  `read_edges` refuses (`storage failure`) any reconstructed edge whose `fp1` fingerprint has
  no witness, so a canonical-preserving edit of a stored edge line (which the JSONL index
  cannot detect) reconstructs to an unwitnessed edge and is never served as a valid edge
  pointing elsewhere.
- **Auto-recovery / retry:** none automatic. A transient outage carries retryability `yes`
  (block until the store recovers, then retry — no partial registration is ever claimed
  successful); a corrupt/truncated store carries retryability `no` and needs operator
  intervention or a restore. Nothing is raised across the seam.
- **Visible degraded state:** the write did not land (no partial registration is claimed) or
  the read did not serve; the caller that holds the `WriterId` blocks on a retryable outage
  rather than assuming success.
- **Notification tier:** operator-visible — a failing or corrupt store needs attention, and a
  corrupt artifact is an evidence-integrity event.
- **Product-user affordance:** nothing an end user did caused this; the underlying store is
  full, locked, truncated, or corrupt. The platform refuses rather than pretending the write
  landed or serving corrupt bytes. A transient outage clears on retry once storage recovers; a
  corrupt store needs an operator restore from the off-machine backup.

### FR-15: Registry format migration refused (CT-09, AR-32, AR-25)

- **Failure class:** `invalid input` (for the guards and a bad transform), or the propagated
  category of an aborting stage (`stale evidence` for a preflight miss, `storage failure` for a
  store fault) — all CT-04 refusal categories.
- **Detection:** `migrate_registry_format` runs preflight → backup-first → dry-run → migrate →
  verify and refuses before or during a stage rather than mutating the only copy. A
  same-root `source`/`destination` is refused (`invalid input`, `field: destination`) so a
  migration is never in-place; a **cross-world** `source`/`destination` (e.g. a live source
  into a replay destination) is refused (`policy rejection`, `field: destination`) so a
  migration stays within one world and a live corpus is never copied into the replay namespace
  (FM-7); a non-positive `to_format_version` is `invalid input`; a preflight record that does
  not already read back from the source aborts with that read's refusal (a missing record is
  `stale evidence`); a `transform` that refuses, returns a non-record, or returns a record NOT
  stamping the target format version aborts the dry-run with **nothing written**; and a
  destination store fault during the migrate stage aborts with no partial migration claimed
  complete. The **backup-first** stage does not merely read the source's restorable export and
  drop it — it **writes a real backup artifact** (through a caller-supplied `backup_sink` or,
  by default, a file under the destination root) before any migrate write, and the report's
  `backed_up`/`backup_path` reflect that real write rather than a hard-coded constant; a
  backup-write failure (or a refusing sink) is returned and aborts the migration before any
  destination write. The procedure migrates **records only** — the report states this
  explicitly (`records_only`), so a reader never mistakes a verified record migration for a
  lineage-edge migration; CT-07 edges are append-only and format-stamped per line and are not
  transformed here (M4).
- **Auto-recovery / retry:** none automatic. The operation RETURNS the refusal; on any
  pre-migrate refusal nothing is written, and the source (append-only, only read) remains the
  intact restore path named by the report's `restore_path`. The caller fixes the offending
  input (distinct destination root, positive target version, a transform that stamps it) and
  retries. Nothing is raised.
- **Visible degraded state:** none — the source is never mutated in place, so a failed
  migration leaves the original corpus fully readable; a partially-written destination is a
  fresh, discardable store.
- **Notification tier:** silent-log for the wiring guards; operator-visible if a store fault
  aborts a migrate in progress (the destination is incomplete and must be rebuilt or discarded).
- **Product-user affordance:** nothing failed for an end user; a developer or operator ran a
  format migration with a bad shape — the same store as source and destination, a different
  world for source and destination, a bad target version, a record not present in the source,
  or a transform that did not produce a valid record stamping the new version. The refusal's
  `context` names the problem; correct it and re-run. The only copy is never mutated, so a
  refused migration is always safe to retry.

### FR-15a: Migration into a destination that already holds a pre-migration backup (CT-09, AR-32)

- **Failure class:** `invalid input` (a CT-04 refusal category), on `field: destination` —
  the same family as FR-15's same-root guard.
- **Detection:** the backup-first stage's default sink writes one artifact,
  `<destination.root>/pre-migration-backup/<world>-registry-room.backup.json`. Before
  writing, it checks whether that path is already taken by a real file. A destination root
  that has already been migrated into still holds the previous run's backup, so a second
  `migrate_registry_format` into the same root is refused **by name**: the `context` carries
  `backup_path` and a `reason` stating that a backup already exists there, that a migration
  writes its backup to a fresh destination root, and that the remedy is to remove that
  backup once it is no longer the restore path or to re-run against a fresh destination.
  Without this guard the exclusive create (`O_CREAT | O_EXCL`, FR-14's symlink-safety
  measure) still refused — but as a raw `storage failure` carrying an OS errno, which reads
  as a disk fault rather than the wiring mistake it is. A **symlink** at that path is a
  different failure and stays FR-14's `storage failure`: it is a hostile path, not an
  already-taken one. A caller-supplied `backup_sink` owns its own naming and is not subject
  to this guard.
- **Design note — why refuse rather than auto-name:** the alternative, giving each backup a
  unique name, cannot be built here. A timestamped name would read the system clock below
  the composition root, which FR-002 forbids and the ambient-nondeterminism gate fails
  closed on; an ordinal name would need a directory scan, reintroducing the
  check-then-create race the exclusive create exists to remove. Both would also quietly
  normalise repeat migrations into a destination that is not fresh, which the ratified
  never-in-place, distinct-destination semantics (AR-32) forbid.
- **Auto-recovery / retry:** none automatic. The operation RETURNS the refusal at
  backup-first, **before any migrate write**, so the second run changes nothing. The
  operator either removes the previous backup (once it is no longer the restore path) or
  re-runs against a fresh destination root, then retries. Nothing is raised.
- **Visible degraded state:** none. The previous run's backup is left byte-identical, the
  source is untouched, and the destination gains nothing from the refused run.
- **Notification tier:** silent-log. Re-pointing a migration at an already-migrated
  destination is a wiring/operator mistake surfaced as a value.
- **Product-user affordance:** nothing failed for an end user. An operator re-ran a format
  migration into a destination root that already holds a pre-migration backup. The refusal
  names that exact path and the two ways forward; pick one and re-run.

### FR-16: Per-writer registration sequence going backwards (CT-06, DEC-0106)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `Registrar` tracks each writer's high-water sequence and enforces that a
  genuinely-new (`stored`) record's `sequence` **strictly exceeds** the last sequence stored
  for the same writer — the per-writer sequence is a strictly-increasing ordering key
  (DEC-0106), so a writer's registration stream that goes backwards or repeats a sequence is
  refused (`field: sequence`, with the writer's `order_tuple`, the `last_sequence`, and the
  `given` value in `context`). A byte-identical re-write is `idempotent` — the same occurrence
  replayed — and is **exempt** from the check (and returns the already-stored record, not the
  caller's twin), so deduplication is never mistaken for a backwards sequence. The first record
  from a writer sets the high-water mark and always passes; each writer has its own counter.
- **Auto-recovery / retry:** none automatic. `register` RETURNS the `invalid input`
  `TypedRefusal` (retryability `no`); nothing is admitted and nothing is raised. The caller
  supplies the writer's next strictly-increasing sequence and retries.
- **Visible degraded state:** none. The stored records and each writer's counter are unchanged.
- **Notification tier:** silent-log. A sequence that goes backwards is a wiring/ordering
  mistake surfaced as a value, not an operational alarm.
- **Product-user affordance:** nothing failed for an end user; a developer wired a writer's
  registration stream out of order (a sequence at or below one the writer already used). The
  per-writer sequence must strictly increase — mint it from a `WriterSequencer` (or otherwise
  advance it) and retry; it is an ordering key, never an identity or dedup key.
