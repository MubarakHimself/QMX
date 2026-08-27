# Verification Plan — Epic 5: qmf-data — backup, restore & verify

- **Epic:** Epic 5 — `qmf-data` backup/restore/verify primitives (Wave 3, priority L)
- **Package under test:** the backup surface **inside** `packages/qmf-data` — `src/qmf/data/backup.py` (COMP-QMF-DATA-BACKUP / CT-14) and `src/qmf/data/store/backup_input.py` (COMP-QMF-DATA-STORE / CT-26). There is no separate `qmf-data-backup` package; the two components ship as modules of `qmf.data`.
- **Tier:** **T2**. Tier scope for this lane: **L3 contract + L2 property for every AC**, **targeted L1** units for point behaviours, **L4** integration for the physical round-trip / seal-survives-restore / migration (backup-restore is an explicitly ratified tier-2 integration target), **L5** the SCN-0004 acceptance chain, and an **L6** requirements-fidelity review. `poe check` = tier 1 (fmt+lint+types+unit+coverage); `poe check-integration` = tier 2 (contract + integration in isolated per-package envs).
- **FRs covered:** FR-014 (the only FR in this epic).
- **Contracts owned:** CT-14 (off-machine backup boundary, owner COMP-QMF-DATA-BACKUP), CT-26 (store-to-backup input, owner COMP-QMF-DATA-STORE). **Consumed / preserved:** CT-04 (typed refusal), CT-05 (fp1 identity), CT-02 (int64 UTC ns instants), CT-12 (the 12-month seal — *enforced on restore*, contract owned by Epic 3), CT-11 (evidence persistence / keep-raw-forever — *preserved by restore*, owned by Epic 3), CT-10 (the records carried), CT-13 (journal — the verify/migration/final-look events).
- **Author stance:** Section 4 (Independent Test List) was authored from the requirements corpus (epics.md §Epic 5, `docs/contracts/ct-14`, `ct-26`, `ct-04`, `docs/components/qmf-data-backup.md`, `docs/components/object-storage.md`, `docs/scenarios/SCN-0004`, the ratified testing lenses, the security model) **BEFORE any `packages/qmf-data/src/qmf/data/backup.py` or `.../store/backup_input.py` source file was opened**. Source is read-only evidence; a failing planned test is a **FINDING**, never a licence to edit source or weaken the test.

> **Template-provenance caveat (load-bearing for the reader).** The two named authorities `_bmad-output/test-artifacts/test-design-qa.md` and `.../test-design/QMX-handoff.md` are **absent from this worktree** (`_bmad-output/test-artifacts/` does not exist — confirmed). The 8-section per-epic shape below, the L0–L6 test-level architecture, and the "one behaviour, one level, lower level wins" rule are reconstructed from `docs/lenses/testing/test-strategy.md` + `docs/lenses/testing/fixtures-and-scenarios.md` (both ratified), the P0/risk-gate content embedded verbatim in the lane task, and the sibling Epic 3 plan's reconstruction (which the Epic 3 L6 review confirmed still stands unreconciled). The **P0-6 / P0-7 assertions and the R-007 / R-012 gates are Epic 3's numbering, carried onto the restore/backup surface here as their restore-side projection**; if the real handoff is restored, reconcile the numbering and section shape against it — it is authoritative over this reconstruction.

---

## Section 1 — Epic Charter & Scope-Under-Test

`COMP-QMF-DATA-BACKUP` provides QMF's **backup, restore, and verify primitives only** — carrying encrypted, versioned copies off-machine from `COMP-QMF-DATA-STORE` (through CT-26) to `COMP-OBJECT-STORAGE` (through CT-14). The design is ratified — nightly, encrypted, versioned, off-machine, with automated sample-restore tests and a periodic full-restore rehearsal — while the **schedule and its execution are application/ops-owned**, the same split as all scheduling (DEC-0118, AD-20). QMF ships the primitives; the cadence that runs them nightly is application/ops territory.

**In scope (this epic, four stories):**

| Story | Title | Primary FR / CT | ACs |
|---|---|---|---|
| 5.1 | Store-to-backup input + encrypted versioned off-machine copy | FR-014 / CT-26 (+CT-14) | AC1–AC5 |
| 5.2 | Restore primitive with seal + world-isolation enforcement | FR-014 / CT-14 (preserves CT-12, CT-11) | AC1–AC4 |
| 5.3 | Verify primitives — sample-restore + full-restore rehearsal | FR-014 / CT-14 (SCN-0004) | AC1–AC4 |
| 5.4 | Application-owned nightly off-machine cycle | FR-014 / CT-14 + CT-26 (AR-34) | AC1–AC4 |

**Epic-specific priority — round-trip integrity of an irreversible boundary.** A backup exists to be the last honest copy. The failures that matter are all *silent*: a restore that returns Ok while omitting or fabricating rows; a backup that reports success while the bytes never left; a restore that becomes a back door around the seal or cross-world isolation; a migration or retention action that mutates the *only* copy. Verification weight is therefore concentrated on **byte/fingerprint round-trip identity (or an honest refusal)**, on **loud failure** (every fault a returned typed refusal, never a silent skip), and on the **preservation invariants** (seal survives restore, world isolation survives restore, raw evidence is never mutated or deleted). Symlink-safe writes are asserted as the **requirement** that defends those invariants under an adversarial filesystem, not as any particular syscall.

**Explicitly out of scope / deferred (blocked specs, verified — not gaps in this plan):** numeric RPO/RTO/retention-depth and restore-verification cadence; the crypto algorithm / encryption key custody; object-storage provider selection and object-key layout; the nightly schedule *execution* itself (application/ops-owned). See Section 8. **Epic-binding note:** the seal (CT-12) and the seven room-roles / world isolation (CT-11) are **owned by Epic 3**; this epic tests only the restore/backup **obligation to preserve** them (Story 5.2 AC2/AC3), never the seal's or the room-role contract's own semantics — those belong to Epic 3's plan.

---

## Section 2 — Authorities, Precedence & Requirement Inventory

**Precedence read (highest first):** epics.md §Epic 5 (Stories 5.1–5.4, AC1–AC5) → `docs/contracts/ct-14-backup-restore.yaml` + `ct-26-store-backup-input.yaml` + `ct-04-typed-refusal.yaml` + `docs/components/qmf-data-backup.md` + `docs/components/object-storage.md` + `docs/constitution.md` + `docs/scenarios/SCN-0004-off-machine-backup.md` → `docs/lenses/testing/*` + `docs/lenses/security/security-model.md` → (test-design-qa.md — absent, reconstructed) → (QMX-handoff.md — absent, P0/R content carried from the Epic 3 reconstruction + lane task).

**Requirement inventory (the map every planned test traces to):**

| Req | Source | Behaviour to prove | FM | SCN |
|---|---|---|---|---|
| FR-014 / CT-26 | Story 5.1 AC1 | Store presents each room-role's records per world as a consistent, restorable, **non-mutating** input; covers **every** room-role incl. the registry room under one retention/backup/migration law; int64 UTC ns passes through **verbatim**, never re-derived under a later calendar/tzdata | BK/FM-1 | SCN-0004 |
| FR-014 / CT-14 | Story 5.1 AC2 | Copy is **encrypted + versioned**; each off-machine copy a new distinct version; a backup **never mutates the only copy** | — | SCN-0004 |
| FR-014 / CT-26 | Story 5.1 AC3 | A CT-26 read crossing worlds or reading `world=simulated` → `policy rejection` (storage separation delivers world isolation) | BK/FM-1 | — |
| FR-014 / CT-14 | Story 5.1 AC4 | Bucket unreachable / rejects upload / copy corrupt → **`storage failure` returned, never raised**; no completion claimed | BK/FM-2 | — |
| FR-014 / CT-14 | Story 5.1 AC5 | Carries the **encryption-required pointer** without baking in provider or credential; **no credential in evidence** | BK/FM-7 | — |
| FR-014 / CT-14 | Story 5.2 AC1 | Restore **never rewrites the only copy in place**; each off-machine copy stays a distinct version; restored int64 ns preserved **verbatim** | BK/FM-3 | SCN-0004 |
| FR-014 / CT-14→CT-12 | Story 5.2 AC2 | A read against **restored** data touching the sealed holdout → `policy rejection`, **identical to a live read** | BK/FM-4 | — |
| FR-014 / CT-14→CT-11 | Story 5.2 AC3 | A restore read crossing worlds, or a restore writing `world=simulated` into governed evidence → `policy rejection` | BK/FM-1 | — |
| FR-014 / CT-14→CT-11 | Story 5.2 AC4 | A retention action during restore that would delete the **only local raw** evidence copy → does **not** proceed; raw + lineage kept forever | BK/FM-5 | — |
| FR-014 / CT-14 | Story 5.3 AC1 | Recoverability claimed **only** through the verify primitives (automated sample-restore + periodic full-restore rehearsal); **never from a snapshot alone** | — | SCN-0004 |
| FR-014 / CT-14 | Story 5.3 AC2 | Verify confirms restored evidence against a documented restore path; a corrupt/failed restore yields **no recoverability claim** — returns `storage failure`, never reports success | BK/FM-2 | SCN-0004 |
| FR-014 / CT-14 | Story 5.3 AC3 | Migration order **preflight → backup-first → dry-run → migrate → verify**; never an in-place mutation of the only copy | BK/FM-3 | SCN-0004 |
| FR-014 / CT-14 | Story 5.3 AC4 | Exposes sample-restore + full-restore rehearsal as first-class ops **without** filling the four `registry:*` numeric keys from a recommendation | BK/FM-6 | SCN-0004 |
| FR-014 / CT-14 | Story 5.4 AC1 | App drives the cycle: CT-14 encrypted versioned off-machine copy on `registry:backup_cadence`=nightly + sample/full-restore rehearsal, over every room-role per world | — | SCN-0004 |
| FR-014 / CT-14 | Story 5.4 AC2 | A request that QMF **own** the nightly schedule or a numeric RPO/RTO → refused as **outside the component boundary** (primitive only) | BK/FM-6 | — |
| FR-014 / CT-26 | Story 5.4 AC3 | Nightly cycle: a cross-world backup read → `policy rejection`; no `world=simulated` room carried into governed evidence | BK/FM-1 | — |
| FR-014 / CT-14 | Story 5.4 AC4 | Transfer with unresolved key custody: carries the encryption-required pointer, **no credential in evidence**, key custody stays node/ops | BK/FM-7 | — |

*(BK/FM-n = the failure-mode rows of `docs/components/qmf-data-backup.md`.)*

**P0 assertions in scope (Epic 3 numbering, restore/backup-side projection):**
- **P0-6 (restore projection)** — the 12-month seal is enforced on a read against **restored** data at **every** read boundary, identical to a live read; a sealed read → `policy rejection`, never a silent empty result. `Story 5.2 AC2 / CT-14 invariant / CT-12 / SCN-0003↔0004`.
- **P0-7 (backup/restore projection)** — cross-world reads refuse **and** `world=simulated` refuses, on **both** the CT-26 backup input and the restore write. `Story 5.1 AC3 / 5.2 AC3 / 5.4 AC3 / CT-26 + CT-14`.

**Risk gates in scope:**
- **R-007** — every storage/transport fault (unreachable bucket, rejected upload, partial/interrupted ack, corrupt copy, locked/truncated/corrupt store) **returns** a typed `storage failure` rather than raising across the boundary or claiming completion — *backup failure is loud, never silently skipped*.
- **R-012** — the seal and world refusals **hold on the restore path exactly as on a live read**, at every enumerated read path over restored data.
- **R-INTEGRITY** *(epic headline)* — the round-trip is **byte/fingerprint-identical or it refuses**; a corrupt/partial/mismatched restore yields **no recoverability claim** and **no fabricated evidence** (never a silent partial restore).
- **R-EVIDENCE** — no backup, restore, migration, or retention action mutates or deletes the only copy / the only local raw evidence; keep-raw-forever holds under an adversarial (symlinked) filesystem.

---

## Section 3 — Risk Assessment & Gates

Risk is scored on *irreversibility × likelihood-of-silent-pass*. A backup boundary's worst failures are the quiet ones — a success verdict over data that never restores — so each headline gets a **property/invariant test that enumerates the fault or path space**, not a single happy round-trip.

| Risk | Failure it guards | Gate | Where proven |
|---|---|---|---|
| **R-INTEGRITY** | A restore returns Ok but omits, reorders, or fabricates rows; a "success" verdict over a corrupt copy | Restore reproduces every record **byte/fingerprint-identical**, or refuses; **no** verify path claims recoverability without a byte/fp match to the source | L2 property (5.2-P1, 5.3-P1) + L4 real round-trip (5.2-I1) |
| **R-012 / P0-6** | A sealed row read back through a **restored** backup while a live read would refuse; a caller-declared `at` under-stating position to slip the seal | Sealed-period read over restored data → `policy rejection` at **every** read boundary; seal position **derived from the resolved evidence**, never a caller argument | L2 property path-enum (5.2-P2) + L4 restored-read (5.2-I2) |
| **R-007** | A store/transport exception escaping the boundary, or a completion claimed on a byte-transfer ack alone | Full fault matrix → **returned** `storage failure`; **no** exception type escapes CT-14/CT-26; durability never inferred from an ack | L2 fault-matrix property (5.1-P4) + L4 object-storage fault sim (5.1-I1) |
| **P0-7** | A cross-world backup read allowed on one room-role while blocked on another; a `simulated` room carried into evidence | Cross-world refuses on **every** room-role read path (backup **and** restore); `simulated` refuses both directions | L2 path-enum (5.1-P3, 5.2-P3) + L1 witnesses |
| **R-EVIDENCE** | A migration/retention/restore write mutating or deleting the only copy; a symlinked target redirecting a write onto the only-local-raw copy or outside the root | No write path removes/overwrites a raw original or its lineage; a symlinked-out target is **never** followed to touch evidence — writes within the intended root or refuses | L2 property (5.1-P2, 5.2-P4, 5.3-P2) + L4 migration (5.3-I1) |

**Prohibited-by-plan:** no planned test may (a) fabricate a numeric RPO/RTO/retention/cadence value to make an assertion pass (they have no ratified value — Section 8); (b) assert an actual scheduler/cron firing as a QMF primitive (the schedule is application/ops-owned); (c) assert cryptographic strength of the encryption (no ratified algorithm/key custody); (d) assert the seal's or room-role contract's own semantics here (Epic 3-owned — test only the restore's duty to preserve them); (e) treat a byte-transfer acknowledgement as a recoverability claim.

---

## Section 4 — Independent Test List (authored from requirements, pre-source)

Notation: `T{story}-U#` unit (L1), `-P#` property/invariant (L2), `-C#` contract (L3), `-I#` integration (L4); `G#` static gate (L0); `ACC#` acceptance scenario (L5). "Assertion" states the observable pass condition. Every public boundary **returns** value-or-refusal; a refusal assertion checks CT-04 `category` (`storage failure` | `policy rejection`) + machine-readable context, **never a parsed exception string**.

### Static / documentation gates (L0)
- **G1** — Import / provider gate: the backup surface imports only `qmf.core` + its own `qmf.data` / `qmf.data.store` seam; **no** object-storage-provider SDK and **no** crypto-provider is baked in — the target stays external and replaceable (DEC-0045, DEC-0120).
- **G2** — No-credential gate: no secret value, provider credential, or encryption key appears in the backup source, its `examples/`, or any evidence artifact; the tier-1 secret-scan gate rides `poe check` (DEC-0136). Only a reference id may appear.
- **G3** — No-schedule / no-runtime gate: the backup surface contains no scheduler, event loop, or nightly-cron runtime — the schedule is application/ops-owned (DEC-0008, DEC-0022; BK/FM-6).

### Story 5.1 — CT-26 input + CT-14 copy (FR-014)
- **5.1-U1** (L1) — The CT-26 read presents records as an **unlimited reader under one-writer-per-stream** and is **non-mutating**: the source room's record set and fingerprints are byte-identical before and after the backup read. *(AC1, DEC-0113)*
- **5.1-U2** (L1) — Every one of the seven `source_room_role` values — ingest door, immutable raw archive, processed, journal, split-governed research door, backup, **registry room** — is presentable through the CT-26 input under one retention/backup/migration law. *(AC1, DEC-0117)*
- **5.1-U3** (L1) — Two backups of the same room yield **distinct, monotonic `copy_version` ordinals**; neither rewrites the other — each off-machine copy is a new versioned artifact. *(AC2, DEC-0118)*
- **5.1-U4** (L1) — The CT-14 payload crosses the boundary as **encrypted-opaque bytes** (typed/marked encrypted); the plaintext store content is not the payload. *(Requirement asserted, not the crypto — AC2, AC5)*
- **5.1-U5** (L1) — A CT-26 backup input requested for a world **other than the room's** world → `policy rejection` refusal, never a silent read. *(AC3, BK/FM-1) — **P0-7 (backup side)**.*
- **5.1-U6** (L1) — A CT-26 read of `world = simulated` governed evidence → `policy rejection` refusal. *(AC3, DEC-0110) — **P0-7**.*
- **5.1-U7** (L1) — A CT-14 transfer to an **unreachable** bucket → `storage failure` refusal **returned**; **no** completion claimed. *(AC4, BK/FM-2, DEC-0109)*
- **5.1-U8** (L1) — A **rejected upload** and a **corrupt-copy** detection each → `storage failure` refusal returned; no completion claimed. *(AC4, BK/FM-2)*
- **5.1-U9** (L1) — The primitive carries an **encryption-required pointer** with no provider selection and no credential baked in; the object-storage target stays external/replaceable. *(AC5, AR-37, DEC-0045)*
- **5.1-U10** (L1) — No credential/secret value appears in the backup artifact, its `fp1` identity, or any refusal context — a reference id only, if anything. *(AC5, BK/FM-7, DEC-0136)*
- **5.1-P1** (L2) — Property (**timestamp fidelity**): for arbitrary int64 UTC ns record timestamps, CT-26 (and the CT-14 round-trip) pass them through **verbatim** — restored value equals stored value bit-for-bit, never re-derived under a later calendar identity or tzdata version. *(AC1, DEC-0106; spans 5.2 AC1)*
- **5.1-P2** (L2) — Property (**R-EVIDENCE / no-mutate-only-copy**): across arbitrary backup sequences over a fixed source room, **no** backup operation mutates or deletes any source record — the only copy's fingerprint set is invariant under any number of backups. *(AC2, DEC-0118)*
- **5.1-P3** (L2) — Property (**P0-7 / world isolation on backup**): for **every** `source_room_role`, a cross-world backup input refuses with `policy rejection` at every room-role read path; storage separation, not identity alone. *(AC3, BK/FM-1)*
- **5.1-P4** (L2) — Property (**R-007 / loud failure**): across the full transfer-fault matrix (unreachable, rejected, interrupted/partial-ack, corrupt copy) **and** the CT-26 store-fault matrix (locked, truncated, corrupt store), **no** exception type escapes the CT-14/CT-26 boundary; every fault surfaces as a **returned** `storage failure` and no completion/recoverability is claimed. *(AC4, BK/FM-2, DEC-0109)*
- **5.1-P5** (L2) — Property (**no-credential-in-evidence**): for arbitrary backup artifacts, no field carries a secret value; the encryption key/credential is never embedded in payload metadata, `fp1`, or refusal context. *(AC5, BK/FM-7)*
- **5.1-C1** (L3) — CT-26 round-trip: `store-room-record-set` encode/decode semantic equality over {`contract_format_version`, `world`, `source_room_role`, `records`, record timestamps}; `source_room_role` enum = the seven room-roles; format-version stamp present. *(AC1)*
- **5.1-C2** (L3) — CT-26 boundary/invalid: `world` and `source_room_role` enum membership; nullability (`contract_format_version`, `world`, `source_room_role` required; null prohibited in identity — absent = omitted key); record timestamps `int64-utc-ns` unit; `boundary_refusal_categories ⊆ {storage failure, policy rejection}`. *(AC1, AC3, AC4)*
- **5.1-C3** (L3) — CT-14 round-trip: `off-machine-backup-copy` encode/decode over {`contract_format_version`, `world`, `copy_version` (int ordinal), `payload` (encrypted-opaque-bytes), payload timestamps `int64-utc-ns`}. *(AC2)*
- **5.1-C4** (L3) — CT-14 boundary/refusal: `world` enum {live, replay, **simulated** (reserved-unusable)}; `copy_version` monotonic ordinal; format-version stamp; nullability; `boundary_refusal_categories` exactly {storage failure, policy rejection} — **not** the other five categories. *(AC2, AC3, AC4)*

### Story 5.2 — Restore with seal + world isolation (FR-014)
- **5.2-U1** (L1) — A restore into a **replacement** store never rewrites the source off-machine copy in place — the restored-from `copy_version` is unchanged after restore. *(AC1, DEC-0118)*
- **5.2-U2** (L1) — A read against restored data that touches the sealed holdout → `policy rejection` refusal, **identical to a live read**; never a silent empty result. *(AC2, BK/FM-4, DEC-0119) — **P0-6 (restore side)**.*
- **5.2-U3** (L1) — A restore read crossing worlds → `policy rejection`. *(AC3, DEC-0117) — **P0-7**.*
- **5.2-U4** (L1) — A restore that would write `world = simulated` into governed evidence → `policy rejection`. *(AC3, DEC-0110) — **P0-7**.*
- **5.2-U5** (L1) — A retention/cleanup action during restore that would delete the **only local raw** evidence copy → does **not** proceed under this component's authority; raw originals and lineage are kept. *(AC4, BK/FM-5, DEC-0118)*
- **5.2-P1** (L2) — Property (**R-INTEGRITY / byte-fingerprint identical**): for arbitrary backed-up record sets, restore reproduces every record **byte/fingerprint-identical** to what was backed up, **or** the restore refuses — never a silent partial or reordered restore. *(AC1, DEC-0106, DEC-0118)*
- **5.2-P2** (L2) — Property (**R-012 / P0-6 / seal survives restore**): for arbitrary CT-12 manifests/dates, a sealed-period read over **restored** data refuses with `policy rejection` at every enumerated read boundary (raw archive, processed, research door), **identical to the live-data behaviour**, with the seal position **derived from the resolved evidence, never a caller-declared position**. *(AC2, BK/FM-4)*
- **5.2-P3** (L2) — Property (**world isolation on restore**): for every room-role, a cross-world restore read refuses with `policy rejection` at every restored read path. *(AC3, BK/FM-1)*
- **5.2-P4** (L2) — Property (**R-EVIDENCE / keep-raw-forever + symlink-safe write**): no restore/backup/retention write path removes or overwrites a raw original or its lineage; **and** a restore write whose target path resolves (via a symlink) onto the only-local-raw-evidence copy, or outside the replacement-store root, **never** mutates or deletes that evidence — it writes within the intended root or refuses. *(AC4, BK/FM-5; requirement asserted, not the implementation)*

### Story 5.3 — Verify primitives (FR-014, SCN-0004)
- **5.3-U1** (L1) — A recoverability claim is produced **only** by the ratified verify primitives; a snapshot / upload acknowledgement **alone** yields **no** recoverability claim. *(AC1, DEC-0118)*
- **5.3-U2** (L1) — Both verify primitives are exposed as **first-class** operations: automated sample-restore and periodic full-restore rehearsal each run and return a verdict. *(AC1, AC4)*
- **5.3-U3** (L1) — A sample-restore whose read-back **byte/fp matches** the source confirms restored evidence against the documented restore path (verdict = recoverable). *(AC2)*
- **5.3-U4** (L1) — A **corrupt or failed** restore yields **no** recoverability claim — the boundary returns a `storage failure` refusal rather than reporting success. *(AC2, BK/FM-2, DEC-0109)*
- **5.3-U5** (L1) — A migration runs the ordered sequence **preflight → backup-first → dry-run → migrate → verify**; the only copy is backed up **before** any migrate step and is never mutated in place. *(AC3, AR-32, BK/FM-3, DEC-0118)*
- **5.3-U6** (L1) — The primitive exposes sample-restore + full-restore rehearsal **without** filling `registry:restore_verification_cadence`, `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, or `registry:backup_retention_period` from a recommendation (those keys stay unset / node-ops). *(AC4, DEC-0118) — see Section 8.*
- **5.3-P1** (L2) — Property (**R-INTEGRITY / restore-never-fabricates**): for arbitrary corrupt / missing / mismatched restored copies, verify **never** returns a recoverability/success claim — every such case → `storage failure` refusal; a success verdict is **impossible** without a byte/fingerprint match against the source, and a snapshot alone never suffices. *(AC1, AC2, DEC-0109)*
- **5.3-P2** (L2) — Property (**R-EVIDENCE / no-mutate under migration**): across arbitrary migration inputs, the pre-migration only-copy fingerprint set is preserved and a fresh backup version exists; no migrate step writes over the only copy, and a migration that cannot back up first **refuses** rather than proceeding. *(AC3, BK/FM-3)*

### Story 5.4 — Application-owned nightly cycle (FR-014, AR-34)
- **5.4-U1** (L1) — The cycle backs up **every** room-role including the registry room, per world (enumerate all seven × {live, replay}). *(AC1, AC3, DEC-0117)*
- **5.4-U2** (L1) — A request to COMP-QMF-DATA / COMP-QMF-DATA-BACKUP to **own** the nightly schedule or a numeric RPO/RTO → refused as **outside the component boundary** — the boundary provides the primitive only. *(AC2, BK/FM-6, DEC-0118, DEC-0051)*
- **5.4-U3** (L1) — During the nightly cycle, a cross-world backup read → `policy rejection`; no `world = simulated` room is carried into governed evidence. *(AC3, DEC-0117, DEC-0110) — cycle-level witness for P0-7.*
- **5.4-U4** (L1) — During a transfer with **unresolved key custody**, the boundary carries the encryption-required pointer, embeds no credential in evidence, and leaves key custody a node/ops item. *(AC4, BK/FM-7, AR-37)*
- **5.4-P1** (L2) — Property (**boundary integrity — primitive only**): no CT-14/CT-26 operation accepts or stores a schedule or a numeric RPO/RTO/retention value; every such input is refused / not-persisted as outside boundary. *(AC2, Story 5.3 AC4, BK/FM-6)*

### Integration (L4 — tier 2, backup/restore target)
- **5.1-I1** (L4) — Object-storage adapter fault simulation: unreachable / rejected-upload / partial-ack / corrupt-object each → `storage failure` **returned** (never raised); durability is **never** inferred from a byte-transfer acknowledgement. *(Story 5.1 AC4; COMP-OBJECT-STORAGE FM-1/FM-2/FM-6) — **R-007**.*
- **5.2-I1** (L4) — Real round-trip over a filesystem/object-storage double: back up a room → transfer → restore into a **replacement** store → read back; **every record byte/fingerprint-identical**; a copy corrupted in transit → `storage failure`, **no** partial restore. *(Story 5.1 AC2 / 5.2 AC1 / 5.3 AC2) — **R-INTEGRITY**.*
- **5.2-I2** (L4) — Seal survives a **real** restore: a read into the sealed period through a restored backup → `policy rejection`, identical to a live read. *(Story 5.2 AC2) — **R-012 / P0-6**.*
- **5.3-I1** (L4) — Migration integration: preflight → backup-first → dry-run → migrate → verify over a real store; the only copy is intact and a fresh backup version exists; a migration whose **backup-first step fails aborts before migrate**. *(Story 5.3 AC3) — **R-EVIDENCE**.*
- **5.4-I1** (L4) — Nightly-cycle wiring (app-driven, injected CT-02 clock): the app driver invokes the CT-14 copy + sample-restore + full-restore rehearsal across every room-role per world; a cross-world read in the cycle → `policy rejection`. *(Story 5.4 AC1/AC3) — the schedule is asserted as app-driven, not as a QMF-owned scheduler.*

### Acceptance scenario (L5)
- **ACC-1** — **SCN-0004**: the store holds an original observation, its correction, and their lineage. An agent creates a snapshot, transmits it off-machine, restores it into a replacement store, runs a migration, and asks to declare disaster-recovery complete. Then: recoverability is claimed **only** through the verify primitives (never from a snapshot alone); the migration runs preflight → backup-first → dry-run → migrate → verify and **never mutates the only copy**; the restored read still enforces the **seal and world isolation**; timestamps round-trip verbatim; **no credential enters evidence**. *(SCN-0004, DEC-0118, DEC-0045)*

### Requirements-fidelity review (L6)
- **L6-R1** — A senior review of the authored suite **against the requirements**, with `backup.py` / `backup_input.py` read as **read-only evidence** only. One question per test: *does it assert what CT-14 / CT-26 / the AC demand, or what the code happens to do?* Mandatory probes (each a FINDING if it fails): **(a)** seal-on-restore is asserted against sealed **rows** with position **derived from the resolved evidence**, not a caller-declared `at` (the exact defect the Epic 3 L6 review caught on the sibling seal path — guard against its recurrence on the restore path); **(b)** the fault matrix injects a **real** store-library / transport exception at the true seam, not qmf-data's already-normalized error; **(c)** round-trip integrity asserts **byte/fingerprint identity**, not a shape/length check; **(d)** the symlink-safe test asserts *evidence outside the root is untouched*, not that a particular syscall was used; **(e)** no ratified numeric (RPO/RTO/cadence/retention) is fabricated into a passing fixture and no app-owned schedule is asserted as a QMF primitive.

---

## Section 5 — Test-Level Assignment & Rationale (L0–L6)

**Level architecture (reconstructed):** L0 static/documentation gates · L1 unit (tier 1) · L2 property/invariant (tier 1) · L3 contract conformance (tier 2, isolated per-package env) · L4 integration (tier 2) · L5 QMF acceptance scenario (tier 2) · **L6 requirements-fidelity review**. This is a **T2 plan**: the **L3 contract + L2 property pair for every AC** is the primary deliverable, backed by **targeted L1** witnesses; **L4** carries the four behaviours that physically cross the boundary (round-trip, seal-survives-restore, migration order, object-storage faults) and cannot be proven in a pure unit; **L5** is the golden chain; **L6** is the fidelity gate.

**One behaviour, one level — lower level wins (applied decisions):**
- Pure refusal *shape* checks (cross-world, simulated, missing key, wrong refusal-category set) live at **L1 / L3**, not re-asserted at L4 — a pure policy decision needs no physical store.
- "Refuses at **every** read path / **every** room-role" (P0-6, P0-7, R-012) is a *quantifier over paths*, so it lives at **L2 property** (enumerate the paths); a single L1 case cannot prove universality. The restored-read path additionally earns **one L4** (5.2-I2) because it physically crosses the backup boundary.
- **Round-trip integrity** is a *universal invariant* → **L2** (5.2-P1, 5.3-P1) with a **physical witness at L4** (5.2-I1), because "byte-identical after a real transfer + restore" is exactly what a pure unit cannot exercise.
- The **fault-to-refusal translation** (R-007) is proven as an *enumerated matrix property* at **L2** (5.1-P4), with the true-seam exception injection at **L4** (5.1-I1) where a real store/transport library would actually raise.
- **CT round-trip / enum / nullability / refusal-category set** → **L3** contract only (CT-14 + CT-26, owned here, run by producer + COMP-OBJECT-STORAGE consumer at tier 2). Not duplicated as L1.
- **Migration ordering** and **cross-component wiring** (nightly cycle) → **L4** only.
- The **golden chain** (SCN-0004) → **L5** only; its component refusals are already covered lower, so L5 asserts *chain integrity + lineage + no-only-copy-mutation*, not the individual refusals.
- **Fidelity** (does the assertion match the requirement or the code?) is not a behaviour a lower level can carry — it is the **L6** review pass.

**Planned counts by level:**

| Level | Scope | Count |
|---|---|---|
| L0 | static/doc gates | 3 |
| **L1** | unit | **25** |
| **L2** | property/invariant | **12** |
| **L3** | contract conformance | **4** |
| **L4** | integration | **5** |
| L5 | acceptance scenario | 1 |
| **Executable total** | | **50** |
| L6 | requirements-fidelity review | 1 review pass (not a pytest node) |

*(L1 per story: 5.1=10, 5.2=5, 5.3=6, 5.4=4 = 25. L2 per story: 5.1=5, 5.2=4, 5.3=2, 5.4=1 = 12. L3: CT-26 round-trip + boundary, CT-14 round-trip + boundary = 4. L4: 5.1-I1, 5.2-I1, 5.2-I2, 5.3-I1, 5.4-I1 = 5.)*

---

## Section 6 — Coverage & Weak-Spot Focus

Coverage floor is **80% per package** (100% branch is required only on the CT-01/CT-02 primitive modules in qmf-core — not applicable here). **These figures come from `coverage.json` (a data artifact); no source logic was read to author Section 4.**

| File | Line | Branch | Signal |
|---|---|---|---|
| `packages/qmf-data/src/qmf/data/backup.py` | 80.0% (303/361) | ~69% (90/130) | 58 missing lines + **38 partial** branches; sits **exactly on the 80% floor** — no margin. First missing lines cluster at 353–405 (a contiguous block, plausibly a whole error/verify/migration path). |
| `packages/qmf-data/src/qmf/data/store/backup_input.py` | 95.4% (97/99) | ~88% (28/32) | 2 missing lines (193, 213) + 4 partial branches — a thin CT-26 input seam, near-covered. |

**Interpretation against requirements (filename → requirement area, no source read):** `backup.py` most plausibly holds the CT-14 backup/restore/**verify** primitives and the migration sequence (Stories 5.1/5.2/5.3); its **38 partial branches** at the 80% floor are the classic signature of **error/refusal branches never exercised** — precisely the `storage failure` translation (R-007), the seal-on-restore refusal (R-012), the no-mutate/keep-raw guards (R-EVIDENCE), and the corrupt-restore no-claim path (R-INTEGRITY) this epic must guarantee. `backup_input.py` is the CT-26 read seam (Story 5.1 AC1/AC3); its two missing lines + four partials are likely the cross-world / simulated refusal arm (5.1-U5/U6/P3).

**Weak-spot probes (planned; each is a FINDING if it fails, never a source edit):**
- **WS-1** — Drive **every** fault branch (unreachable, rejected, partial-ack, corrupt copy, locked, truncated, corrupt store) so the `storage failure` translation branches (5.1-P4, 5.1-I1) are *covered*, not partial. Target: the partial branches in the 353–405 block of `backup.py`.
- **WS-2** — Exercise **both arms** of every seal / cross-world / no-mutate / corrupt-restore decision — the "refuse" arm is the one that shows up partial. Ties to 5.2-P2, 5.2-P4, 5.3-P1, 5.3-P2.
- **WS-3** — Cover the cross-world / simulated refusal arm of `backup_input.py` (lines 193, 213 + partials) — 5.1-U5/U6/P3.
- **Coverage is not behaviour evidence:** a branch counted covered still requires its assertion to check the *returned refusal category* and the *byte/fp identity*, per DEC-0109. Because `backup.py` sits **exactly on the floor**, any test that raises a covered-line count without asserting the returned refusal is explicitly out of bounds; percentage never substitutes for a named-behaviour assertion.

---

## Section 7 — Fixtures, Data & Environment

- **Determinism:** injected CT-02 clock (int64 UTC ns) at the composition root; **no fixture below the root reads the system clock**; a monotonic reading is never an Instant. Property/randomized fixtures declare a seed; equal semantic inputs replay to equal `fp1` (single qmf-core implementation, floats refused in identity).
- **Worlds:** fixtures parametrize `world ∈ {live, replay}` for positive paths and assert `simulated` refuses; room-roles instantiated in **separate physical roots per world** (world isolation is storage separation, not identity).
- **Backup/restore doubles:** a filesystem or in-memory object-storage double for tier-1 units and tier-2 integration; the object-storage boundary is exercised through **controlled replays / fault injection** (unreachable, rejected, partial-ack, corrupt), **never a live provider** — QMF tests adapter behaviour under documented external outcomes, never provider internals.
- **Round-trip harness:** back up → (transfer) → restore into a **fresh replacement** store, then compare **`fp1` fingerprints and raw bytes** record-by-record; the "or refuses" arm asserts a returned `storage failure`. Corruption is injected as a class of the fault matrix.
- **Seal fixture:** a CT-12 fingerprinted split with `train/validation/sealed-test`, a **frozen** seal TradingDate from `registry:historical_holdout_months` (~12mo); the restored-read seal position is **computed from the resolved evidence**, never hardcoded and never taken from a caller `at`.
- **Symlink fixture:** a replacement-store root containing a symlink whose target is a **sentinel "only-copy" file/dir placed outside the root**; after a restore/backup write, assert the sentinel's bytes are **unchanged** *or* the write refused — the requirement (evidence outside the root is untouched), not the syscall.
- **Refusal harness:** boundaries **return** value-or-refusal; the harness asserts CT-04 `category` (`storage failure` | `policy rejection`) + machine-readable context + retryability, never a parsed exception message.
- **Secrets:** fixtures carry **references, never values**; no credential/encryption key enters any artifact, `fp1`, log, or refusal context; the tier-1 secret-scan gate rides `poe check` (DEC-0136).
- **Source classes:** every fixture tagged `source-evidence | controlled-replay | synthetic`; **synthetic may prove infrastructure / failure handling only and may never satisfy a trading-edge assertion** (DEC-0054) — backup is pure infrastructure, so synthetic fixtures are appropriate throughout here.
- **Engines / env (tier 2):** the ratified store stack behind QMF-owned contracts; no database server; **isolated per-package env** at tier 2 so an undeclared import (e.g. a provider SDK) fails rather than resolving through the shared venv.
- **Run:** `uv run` from the worktree root (`.venv` dev group synced); property fixtures via `uv run --with hypothesis …` if hypothesis is absent.

---

## Section 8 — Execution, Exit Criteria & Untestable / Deferred

**Execution order:** L0 gates → L1 units → L2 properties (R-007 / R-012 / R-INTEGRITY / R-EVIDENCE quantifier proofs) → L3 CT-14/CT-26 conformance → L4 integration (round-trip, seal-survives-restore, migration, object-storage faults) → L5 SCN-0004 → **L6 requirements-fidelity review**. Findings are recorded, not fixed; a red test that asserts a requirement the code violates is a **defect finding**, and the source is never edited to make it pass.

**Exit criteria (T2 sign-off for this epic):**
1. Every AC (5.1 AC1–AC5, 5.2 AC1–AC4, 5.3 AC1–AC4, 5.4 AC1–AC4) has at least one passing **L3 or L2** assertion; every P0-6 / P0-7 / R-007 / R-012 / R-INTEGRITY / R-EVIDENCE gate has at least one passing **L2 property** and, where it crosses the boundary, its **L4** witness.
2. `backup.py` raised **above** the 80% floor with its refusal/verify/migration branches (the 38 partials) covered — or each residual partial recorded as a **finding** with the missing branch named; `backup_input.py`'s cross-world arm (lines 193, 213) covered.
3. No planned test fabricates a numeric RPO/RTO/retention/cadence value, asserts a scheduler firing as a QMF primitive, or asserts the seal's / room-role contract's own semantics (Epic 3-owned).
4. The **L6** review returns no un-recorded fidelity gap — in particular the seal-on-restore assertion is verified to bind against sealed **rows** with an evidence-derived position (not a caller `at`).
5. Traceability complete: every test cites FR/CT/AC/FM/SCN/DEC (and AR where relevant) ids.

**Requirements judged untestable now (with reason — these are blocked specs, not plan gaps):**
- **U-A — Numeric RPO / RTO / retention-depth / restore-verification cadence.** `registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`, `registry:backup_retention_period`, `registry:restore_verification_cadence` are named at the **node/ops sitting** with no ratified value (DEC-0118; Story 5.1 AC5, 5.3 AC4, 5.4 AC2). The **behaviours** — primitives exposed as first-class ops, the boundary refusing to own the numbers (5.3-U6, 5.4-P1) — are testable; the **numeric targets** have no spine value to assert.
- **U-B — Encryption strength / crypto algorithm / key custody.** Encryption is *required* but the algorithm, key custody, and crypto dependency are node/ops (DEC-0118, AR-37). Testable = the payload is marked **encrypted-opaque** and **no credential enters evidence/`fp1`** (5.1-U4/U10/P5, G2); **not** that the ciphertext is cryptographically secure or correctly keyed — there is no ratified key or algorithm to verify against.
- **U-C — Object-storage provider selection + object-key layout.** Node/ops (DEC-0045, DEC-0118). Testable = **no provider baked in / target external-replaceable** (G1, 5.1-U9); the layout itself has no ratified value.
- **U-D — The nightly schedule *execution* itself.** Application/ops-owned; explicitly **not** a QMF primitive (Story 5.4 AC2, BK/FM-6, DEC-0118). Testable = QMF **refuses to own** the schedule (5.4-U2) and the primitives are invoked **when the app drives** them (5.4-I1); an actual cron/scheduler firing is **outside the QMF boundary** and asserting it here would violate the primitives-only law.
- **U-E — Full-restore rehearsal *cadence* (period).** `registry:restore_verification_cadence` is node/ops (DEC-0118). The rehearsal **as a primitive** is testable (5.3-U2/U3); **how often** it runs is not.

**Plan caveat carried forward:** `test-design-qa.md` and `QMX-handoff.md` were absent from the worktree, and the P0/R-gate ids are Epic 3's numbering projected onto the restore/backup surface; if the real handoff is restored, reconcile this plan's section shape, level names, and the P0/R-gate numbering against it (they are authoritative over this reconstruction). The Epic 3 L6 review confirmed the same absence and let the reconstruction stand.
