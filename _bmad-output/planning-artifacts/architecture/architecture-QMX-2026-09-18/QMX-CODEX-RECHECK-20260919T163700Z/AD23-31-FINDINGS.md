# Findings against AD-23..AD-31 and `CONTRACTS.md`

Severity labels describe architecture risk, not implementation status. A “required repair” is a documentation/contract repair for Grok.

## Critical and high findings

### RC-01 — ATC identity is asserted in the spine but absent from the run contract

**Severity:** critical  
**Affects:** AD-23, AF-01, AF-03

AD-23 distinguishes versions by `composition_fp`, binds evidence to the PolicyPair hash, and requires every attached consumer to adopt the selected composition version (`ARCHITECTURE-SPINE.md:222-226`). `AlternativeRunConfig` carries neither `composition_fp` nor stable PolicyPair identity/version/hash; its `policy_pair` is anonymous inline content (`CONTRACTS.md:355-392`). Consequently a pin, command-owner epoch, QMB lineage row, and QML/QMN adoption cannot be proven to concern the same selected composition.

**Required repair:** make `composition_fp` and a versioned, immutable PolicyPair identity/hash normative; define its canonical preimage and bind selection, grants, simulation evidence, fencing, and CT-07 lineage to it. Inline policy bodies may be snapshots, but cannot be the sole identity.

### RC-02 — ATC command admission is self-asserted and incomplete

**Severity:** critical  
**Affects:** AD-23, AF-01, AF-03

AD-23 requires command binding to venue, account, role, instrument, adapter capability, credential ref, and owner epoch, followed by checks for policy completeness, grants, health, paper readiness, and L17 (`ARCHITECTURE-SPINE.md:226`). The contract command omits owner epoch and the admission object is a set of booleans with no grant IDs, health observations, paper evidence, promotion record, evaluating principal, time, or typed verdict (`CONTRACTS.md:355-392`). A caller can therefore claim admission without a verifiable authority chain.

**Required repair:** add owner epoch/fencing binding and an admission result produced by the authoritative host, with typed refusal, checked grant IDs, health evidence/revision, paper run/evidence refs, L17 promote ref, evaluator, and decision time. Refuse stale observations. Do not allow client booleans to authorize live.

### RC-03 — InvocationEnvelope repeats authoritative facts without a mismatch rule

**Severity:** high  
**Affects:** AD-24, AF-02, AF-05

The envelope includes `op_version`, contribution tuple, instance/config revision, grant, and `effect_class` (`ARCHITECTURE-SPINE.md:228-232`; `CONTRACTS.md:38-59`). Those values also belong to the live descriptor/instance/GrantRecord. The candidate does not say which store is authoritative at dispatch or how a mismatch is refused. A caller could label an external effect as `read`, cite a stale descriptor, or pair a valid grant with another resolved target.

**Required repair:** on every hop, resolve the contribution/descriptor and GrantRecord from authoritative stores, compare every bound field, and return a typed stale/mismatch refusal before execution. Treat the envelope as signed/bound request context, not authority by assertion.

### RC-04 — Idempotency domain and nested-call identity are under-specified

**Severity:** critical  
**Affects:** AD-24, AD-26, AF-02, AF-04, AF-05

AD-24 defines effect-specific outcomes but not who mints `idempotency_key`, its uniqueness domain/retention, canonical binding to target and input, or how nested public calls derive child identities (`ARCHITECTURE-SPINE.md:232`). This leaves collisions, replay after dedupe expiry, and recursive or delegated calls ambiguous. `request_hash` and `input_hash` likewise lack canonical preimages (`CONTRACTS.md:38-59`, `140-160`).

**Required repair:** define issuer, scope, canonical preimage, collision refusal, minimum retention, and replay result for each key/hash. Add parent invocation ID, call depth/delegation chain, and deterministic child ID rules; bind the key to operation, version, instance, config, grant, target, and canonical input.

### RC-05 — Grant immutability conflicts with `revoked_at`; expiry/revocation races are undefined

**Severity:** high  
**Affects:** AD-24, AF-10

AD-24 calls GrantRecord immutable after mint but includes optional `revoked_at` in the record (`ARCHITECTURE-SPINE.md:232`; `CONTRACTS.md:117-138`). It does not define the authorization evaluation point for queued/running/nested work or what happens when expiry/revocation races with dispatch or an external effect.

**Required repair:** keep the minted grant immutable and model revocation as a separate append-only record/event. Define evaluation moments for acceptance, dispatch, nested calls, retries, and external commit; specify whether already accepted work may finish and what evidence/refusal is emitted.

### RC-06 — Fencing has an ambiguous terminal branch and an incomplete deploy payload

**Severity:** critical  
**Affects:** AD-25, AF-03, AF-07

AD-25 lists `unknown-blocked` inside an ordered chain that continues to `predecessor-acked`, yet calls it terminal for the attempt until operator reconcile (`ARCHITECTURE-SPINE.md:234-238`). Neither the durable transition key/revision nor the reconcile command and evidence are defined. The deploy payload omits `role`, despite the fence key `(account, venue, role)`, and omits required timeout/escalation and completion-evidence fields (`CONTRACTS.md:333-353`).

**Required repair:** draw `unknown-blocked` as a terminal branch; define a new reconciled attempt or explicit operator transition with new attempt/epoch and immutable evidence. Add role, machine/attempt revision, issuer, timeout/escalation, predecessor acknowledgement, snapshot identities, and completion evidence to the contract. Define compare-and-set guards and token uniqueness.

### RC-07 — Outbox ack does not prove receiver acceptance or exactly-once logical effect

**Severity:** critical  
**Affects:** AD-26, AF-04

The transactional write in AD-26 prevents a forgotten successor, but the outbox contract lacks a uniqueness constraint/domain, full immutable envelope/target, receiver acceptance ID, or receiver-side effect ledger (`ARCHITECTURE-SPINE.md:240-244`; `CONTRACTS.md:299-313`). An ack after transport delivery is not proof that B durably accepted or deduplicated the logical invocation.

**Required repair:** define a unique key such as `(graph_run_id, successor_node_id, predecessor_revision, partition_id)`; persist the complete target/envelope hash; distinguish dispatch, durable receiver acceptance, and effect completion; require receiver dedupe keyed by logical invocation and return the prior result on replay.

### RC-08 — Join algebra lacks the identity and deterministic selection needed after restart

**Severity:** high  
**Affects:** AD-26, AF-12

`JoinState` has no graph/run/node/edge definition revision, join revision, or durable source-event identity (`CONTRACTS.md:315-331`). `first-wins` is undefined under concurrent arrival/replay, and expected cardinality, timeout origin, failed aggregation, late handling, and retry-revision behavior are not fully represented. These omissions make restart outcomes dependent on arrival timing.

**Required repair:** bind join state to immutable graph/run/node/edge revisions and a join revision; define the total ordering used by `first-wins`; persist watermark cause/time and late-event evidence; bind partial retry to the same join definition while recording reused result identities.

### RC-09 — Checkpoint is a list, not yet a consistent checkpoint protocol

**Severity:** critical  
**Affects:** AD-27, AF-13; cheap-veto A6

AD-27 lists owner/store/fence/hash and restore order (`ARCHITECTURE-SPINE.md:246-250`; `CONTRACTS.md:398-415`) but does not establish a coordinated cut, checkpoint generation, per-owner prepare/commit outcome, artifact/registry coverage, or backup object refs. There is no rule for a writer crossing the cut. The declared restore order also restores QMA projections last although the manifest is QMA-owned, leaving bootstrap authority unclear.

**Required repair:** define `checkpoint_id`/generation, manifest schema version, cut/barrier protocol, per-owner fence semantics, prepare/commit/fail outcomes, immutable backup refs and hashes, included/excluded store inventory, bootstrap copy/location, and recovery from partial checkpoint creation. Reassess restore order based on dependency direction and specify post-restore reference and external-effect reconciliation records.

### RC-10 — Stream contract conflates subscription state and events and cannot prove cutover correctness

**Severity:** critical  
**Affects:** AD-28, AF-08

AD-28 requires gap/duplicate/late events, heartbeat, loss evidence, atomic cutover, leases, and shared-feed refcount behavior (`ARCHITECTURE-SPINE.md:252-256`). The representative payload mixes subscription fields and one event, has no typed control-event union, no gap bounds, no duplicate/late references, no heartbeat/loss record, no lease set/expiry, and no cutover acknowledgement/barrier (`CONTRACTS.md:251-274`). A numeric refcount cannot identify or expire dead consumers.

**Required repair:** separate `StreamSubscription`, `StreamDataEvent`, and typed control/evidence events; define epoch reset, sequence domain, cutover barrier/ack and missing-watermark behavior, cursor durability, consumer lease identities/expiry, refcount derivation, and reconnect/backpressure outcomes.

### RC-11 — Session CAS dedupe has no namespace, retention, or compaction protocol

**Severity:** high  
**Affects:** AD-29, AF-09

AD-29's CAS result distinguishes duplicate from conflict (`ARCHITECTURE-SPINE.md:258-262`; `CONTRACTS.md:87-115`), but `command_id` uniqueness is not scoped to principal/session and the prior-result retention horizon is undefined. Reconnect cursors have no compaction/snapshot response or rule for an in-flight duplicate.

**Required repair:** define command ID issuer and namespace, durable dedupe retention, canonical payload hash and collision refusal, an `in_progress` duplicate result, cursor/generation identity, and a snapshot/resync response for compacted history.

### RC-12 — ChangeRequest mixes immutable request facts, claimed validation, and later apply evidence

**Severity:** critical  
**Affects:** AD-29, AF-14

The contract represents target refs and base hashes as parallel arrays, does not define `request_hash` canonicalization, and lets app-use populate a validation label (`CONTRACTS.md:140-160`). AD-29 also requires apply evidence “after authoring apply” in the same payload (`ARCHITECTURE-SPINE.md:262`), which either mutates a supposedly hashable request or leaves the hash scope unclear.

**Required repair:** use paired `{target_ref, base_hash}` records; define an immutable `ChangeRequest` hash preimage over requester-controlled facts and patch; record validator verdict separately under validator authority; record application as a separate append-only `ChangeApplyRecord` citing request hash, applied base/result hashes, authoring/operator principal, time, and outcome.

### RC-13 — Package manifest contradicts AD-2 contribution identity

**Severity:** high  
**Affects:** AD-30, AF-11, AF-15

AD-2 makes pack `contributes` entries structured `{point, local_id}` objects (`ARCHITECTURE-SPINE.md:93-98`). The package manifest uses opaque strings such as `"capability:qmb.analysis.project"` (`CONTRACTS.md:276-293`). That is a direct contract contradiction and cannot deterministically expand to a ContributionHit.

**Required repair:** use the AD-2 object shape and define validation/qualification to `qualified_id`, collision handling, and atomic availability revision publication.

### RC-14 — Package failure recovery, pin retention, and export proof are not decidable

**Severity:** critical  
**Affects:** AD-30, AF-11, AF-15; cheap-veto A3/A4

AD-30 requires last-usable roster restoration, constrained migrations, dependant-aware uninstall, and retention of bytes for in-flight pins (`ARCHITECTURE-SPINE.md:264-268`). The payload has no lifecycle transition record, roster generation, migration state/outcome, dependant/in-flight leases, byte-GC rule, or scan report schema. “Prove absence” of secrets/private paths/transcripts is overbroad without a threat model, canonical scanner rules, coverage, and treatment of rewritten bytes/signatures.

**Required repair:** define transition CAS and roster generations; migration prepare/commit/rollback or explicit forward-only recovery; dependant and in-flight pin leases; garbage-collection eligibility; and a versioned export scan report with threat model, detectors, coverage, typed findings, rewrite map, post-rewrite hash/signature, and fail-closed result.

### RC-15 — Recipe contract omits fields its AD makes normative

**Severity:** critical  
**Affects:** AD-31, AF-06, AF-19; cheap-veto A5

AD-31 requires input coverage, schema/roles, freshness, provenance, entitlement, licensing, and revision plus output completeness and per-input CT-07 lineage (`ARCHITECTURE-SPINE.md:270-274`). The representative definition omits several of those, has no explicit output completeness enumeration, and uses a placeholder lineage string in the release payload (`CONTRACTS.md:162-227`). Canonical hash input and the boundary between reviewable definition and runtime credentials are undefined.

**Required repair:** make the contract match the full AD-31 catalogue; define canonical normalization/hash and rename exclusions; keep credentials as typed runtime refs rather than secret definition content; bind release lineage to definition ID/version/hash, every concrete input revision, transform/environment/code pins, run ID, and completeness.

## Cross-cutting contract findings

### RC-16 — `CONTRACTS.md` falsely labels the AD-3 descriptor schema-complete

**Severity:** high  
**Affects:** AD-3, AF-16

The file says payloads are schema-complete for normative fields (`CONTRACTS.md:7-11`). The descriptor example (`CONTRACTS.md:13-36`) omits fields AD-3 explicitly requires, including separate input/output cardinality, configuration/defaults, declared operation dependencies, resource needs, documentation refs, validation class, and the complete error/refusal shape (`ARCHITECTURE-SPINE.md:100-104`).

**Required repair:** either supply the complete descriptor schema or explicitly mark the example a non-normative fragment and link to the complete schema. A fragment may not substitute one `cardinality` field for native in/out cardinality.

### RC-17 — Headless-door matrix is keyed by owner, contrary to per-operation law

**Severity:** high  
**Affects:** AF-17, AF-18

The matrix is per `Owner` (`CONTRACTS.md:433-442`), while the folded scenario correctly says supported-door sets are per `op_id` (`docs/scenarios/SCN-0022-pack-lifecycle-headless.md:27`). Owner-wide support cannot express two operations of one component with different doors and can accidentally promise unsupported entry points.

**Required repair:** key the normative matrix by `op_id` and version, enumerate supported adapters/doors, and define the typed `unsupported_door` response and event/progress/reconnect behavior per operation.

## Findings that did not reopen

- OD-01 is closed; the stale conditional ledger text is documentation drift, not a new operator question.
- The QMA AD-17 JobHandle state vocabulary is preserved in both spine and contract.
- The candidate correctly distinguishes sensing/research from an ATC and retains QMN as the only venue importer.
- The documents are honest that these machines are not implementation evidence at `270e992`; this supports AF-20 but does not close the architecture defects above.
