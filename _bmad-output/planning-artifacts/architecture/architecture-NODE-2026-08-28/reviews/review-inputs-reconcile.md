# Reviewer gate — INPUTS RECONCILE lens

**Artifact under review:** `ARCHITECTURE-SPINE.md` (Trading Node, 24 TN blocks) + `.memlog.md` (A1–A30).
**Lens:** for each load-bearing input, check the spine against it and return what did NOT land — a
quiet requirement (a tone, a constraint, a named item) the TN structure dropped, a divergence, a
contradiction, or an unverified claim.
**Method:** read spine + memlog in full; read the operator brief (memlog event/constraint entries),
PRD §3/§6/§8/§9/§10, `tracker/trading-node-notes.md`, `inputs/parts-bin.md` §3 seams + §5 red flags,
`inputs/corpus-verdicts-A.md` (QA1–13), `inputs/corpus-verdicts-B.md` (QB1–15). Every finding below
names the exact input sentence that did not land and where in the spine it should go.

**Coverage scorecard (what DID land — recorded so the gaps are legible as gaps, not omissions):**
The brief's required-coverage list and things-to-check list are almost fully homed. All §3 adaptation
seams have a home (via the Structural Seed ports table and their TNs). All §5 red flags R1–R15 have an
explicit answer except R13 (advisory only; see L6). The three headline reconciliations the corpus
demanded landed cleanly: four reconciliation verdicts (Corrections #1), paper = AD-35 standing state on
the paired demo not a twin (Corrections #2), Spotware SDK closed / in-house transport (Corrections #4),
soak-inside-the-warm-up-week (TN-9/A10), KSA levels adopted from GitBook with the matrix blank-blocking
live (TN-7). The findings below are the residue.

**Verdict:** PASS WITH CHANGES. No inherited-invariant contradiction and no blocker; the spine's law is
sound and its seam/red-flag coverage is complete. But two live-money-adjacent requirements named in the
inputs were dropped (H1 provisional-value countersign, H2 the venue conformance test double), and five
medium items are quiet requirements the TN structure lost. Fold H1–H2 and M1–M5 before the
documentation-factory absorption; the low items are one-line annotations.

---

## CRITICAL

None.

---

## HIGH

### H1 — The "provisional value requires countersign before live" gate was dropped; the spine ships ~30 non-blank provisional-evidence variables that reach live without a countersign

- **Where:** TN-18 (config surface), TN-20 (promotion precondition battery), the "New registry
  variables" table (spine lines 539–557).
- **Input that did not land:** PRD §6 console spine, `prd.md:483-485`: *"measured/provisional values
  never masquerade as settings; a provisional value requires an explicit operator countersign before
  live … (Note: `docs/registry/variables.yaml` carries `configurable` but no value-status field — the
  terminal cannot decide editability from data until it does.)"* Reinforced by L29 (inherited, spine
  line 81): *"provisional recommendations grant no live-money authority."*
- **What the spine did instead:** TN-18 collapses value state into two cases — **blank** (a blank that
  gates live money blocks `role = live`) and **filled** (evidence value, allowed). It then mints ~30
  new `configurable: true` variables "with evidence values only" — the clock bands 25/100/250 ms (A20),
  the seven `sqs_*` keys, `daily_dead_zone_width` ~3 h (A8), etc. — all RECONFIRM-grade, none blank.
  Under TN-20 the promotion battery re-checks "blanks, and present baselines" but has **no check that a
  filled value is ratified rather than provisional**. So the node can bind live money on drift bands,
  SQS thresholds and dead-zone widths the operator never countersigned.
- **Why it matters:** this is a live-money-authority weakening. The KSA matrix gets the correct
  treatment (blank blocks live, ratified pre-live through the settings surface — TN-7, Deferred table),
  but every *other* provisional value silently escapes that gate because it is filled with a starting
  default rather than left blank. The PRD flagged the missing `value-status` field by hand; the spine
  perpetuates the gap while adding 30 more provisional-valued rows to it.
- **Concrete fix:** in TN-18, mint the `value-status` field the PRD names (`blank | provisional-evidence
  | ratified`) on every node variable, and add the rule: a `provisional-evidence` value that gates live
  money blocks `role = live` bindings exactly as a blank does, until an operator countersign through the
  powers channel flips it to `ratified` — the same treatment the KSA matrix already gets. TN-20's
  precondition battery then checks `value-status = ratified` (not merely non-blank) for every live-gating
  variable. This also gives the terminal the field it needs to decide editability from data.

### H2 — The QA standard omits the venue conformance test double both a double and the live client must pass; the order-path proofs and CI drills have no deterministic driver

- **Where:** TN-23 (QA standard, benchmarks, soak acceptance) and TN-16 (CI matrix).
- **Input that did not land:** QA13 "New for the node", item 2 (`corpus-verdicts-A.md:1270-1272`):
  *"A venue conformance suite both a test double and the live client must pass (FEAT-0023 venue test
  double; UNKNOWN-outcome fixtures per trigger; the superseded-by-fill cancel read-back)."* Item 1 of the
  same list: *"Wire the four risk golden scenarios. SCN-0006/0008/0010/0011 stay defined-unwired until
  the node wires them … no integration or runtime proof exists until the node wires them."*
- **What the spine did instead:** TN-23's soak-acceptance gate proves the order-path behaviours
  (forced disconnect → UNKNOWN, reconnect gap recovery, four-verdict reconciliation, kill-line flatten)
  against a **real demo connection during the one-time soak** (TN-9). It provides no venue test double,
  and it does not name the four golden scenarios or FEAT-0023 as wiring targets. The permanent battery
  (TN-23) therefore has no way to drive UNKNOWN-per-trigger, superseded-by-fill, or the four risk
  scenarios deterministically in CI — the proofs exist only at soak time, once, on live infrastructure.
- **Why it matters:** the node money-path modules TN-23 extends mutmut to (command mint, equity
  derivation, drift decomposition, door-path wiring) are exactly the code the UNKNOWN/reconciliation
  fixtures exercise; without a venue double, the mutation gate and the QA-debt discharge (QMX-F062/F063/
  F067/F068/F069 — all node stories in TN-23) cannot be earned in CI, only asserted. This is the harness
  that makes the order path provable, and it is absent.
- **Concrete fix:** in TN-23, bind a venue conformance double (FEAT-0023) as a required node artifact:
  a test double and the live cTrader client both pass one conformance suite carrying UNKNOWN-outcome
  fixtures per trigger (`timeout | transport-error | disconnect`) and the superseded-by-fill cancel
  read-back; and name SCN-0006/0008/0010/0011 as the four golden scenarios the node wires and proves.
  This is separate from TN-21 replay (which diffs recorded observations, not synthetic fault fixtures).

---

## MEDIUM

### M1 — The node's read door does not carry per-read provenance (authority source / source time / receive time / watermark); a ratified console-spine constraint on the door NOW was dropped

- **Where:** TN-17 (evidence read channel), TN-15 (health read model).
- **Input that did not land:** PRD §6 console spine, `prd.md:471-472`: *"Every important read reveals
  authority source (live-authoritative vs replicated evidence), source time, receive time, and
  watermark."* QA12 (`corpus-verdicts-A.md:1159-1162`): *"these constrain the node's door now, even
  though the app is Phase 3: the node must expose a read surface that carries provenance and freshness
  per state (never one blended health value)."*
- **What the spine did:** TN-15 gets "INDEPENDENT states … never one colour" and "requested versus
  enforced shown apart" right, but neither TN-17's evidence channel nor TN-15's health model requires
  the four named provenance fields on a read. The word "provenance" in the spine refers only to
  `provenance = sandbox` and `converted_by = venue`, never to per-read authority/time/watermark.
- **Why it matters:** the terminal (Phase 3) is specified to reveal these four fields; if the node door
  built now does not carry them, the desktop backend cannot surface them later without a door change —
  the exact coupling QA12 says to avoid. Freshness/authority on a read is also what stops stale
  replicated evidence from being mistaken for live-authoritative state at a powers click.
- **Concrete fix:** in TN-17's evidence read channel, bind that every read model carries per-state
  provenance — authority source (`live-authoritative | replicated-evidence`), source time, receive
  time, and watermark — as required fields, mirroring `prd.md:471-472`.

### M2 — The five node Records streams ↔ CT-13's seven journal event types bridge is unbound; the corpus assigned this bridge to this sitting by name

- **Where:** TN-15 (logs/journals), TN-6 (veto path / suppression path).
- **Input that did not land:** `corpus-verdicts-B.md` tension 12 (line 1340): *"Two evidence taxonomies
  to bridge. The node's five Records streams (`veto_ledger, trade_journal, book_journal, ksa_audit_log,
  correlation_ledger`) and QMF's seven journal event types are two vocabularies; CT-25 already carries
  the mapping table as projection names only. The order-path study flags the bridge as 'a node-sitting
  documentation item'."* Corroborated by `tracker/trading-node-notes.md:31` (correlation ledger is one
  of the five Records streams).
- **What the spine did:** TN-15 treats journals as CT-13 seven-type evidence only; TN-6 introduces a
  "veto path" and a "suppression path" and `enacts` edges. It never names the five-stream Records model
  or maps it onto the seven journal event types. TN-17's evidence channel lists "journal projections
  (Book, BMS and per-bot logbooks)" but not the veto ledger / KSA audit log / correlation ledger as
  named streams.
- **Why it matters:** the node sitting was explicitly told it owes this bridge; leaving it unbound means
  independently-built epics may mint stream vocabularies that do not line up with CT-25's projection
  mapping, and the documentation factory has no ratified table to absorb.
- **Concrete fix:** add a TN-15 (or Parent-annotations) sub-rule binding the five Records streams to the
  seven CT-13 journal event types via CT-25's projection mapping, and cross-name the veto path as
  `veto_ledger` and the KSA level fold's audit trail as `ksa_audit_log`.

### M3 — `composition_fp` enumeration omits the registry as-of set fingerprint and the calendar identities QA4 named; two boots on different as-of sets can share a fingerprint

- **Where:** TN-2, act 3 (Fingerprint).
- **Input that did not land:** QA4 "What the node must fingerprint at boot" (`corpus-verdicts-A.md:314-
  327`): the enumerated set includes *"every calendar identity in play (market-hours, day-boundary,
  news); the registry as-of set fingerprint; every Book-definition and BMS-definition fp1 and every
  CT-28 binding-record fp; the CT-18 capability-declaration fp … the pinned error-map rows … the
  clock identity; the WriterId set; and the SecretRef ids — references only."*
- **What the spine did:** TN-2's `composition_fp` covers the resolved node-config fp1, distribution
  versions, proto tag, tzdata version, adapter capability-declaration fp1, and the OS/CPU-class tuple.
  It does **not** name the registry as-of set fingerprint or the calendar identities. (The
  venue-observation-profile fp is correctly excluded — it is measured post-seal.)
- **Why it matters:** the promotion pull (TN-20) reads a registry as-of set; if that set's fingerprint
  is not sealed into `composition_fp`, two boots that pull different as-of sets can carry the same
  `composition_fp`, breaking the spine's own claim (TN-2) that "sealing the composition into the boot
  epoch makes every evidence row traceable to the exact composition that produced it." Calendar
  identities are similarly decision-bearing and were named by the corpus.
- **Concrete fix:** extend TN-2's Fingerprint enumeration to include the registry as-of set fingerprint
  and every calendar identity in play (market-hours / day-boundary / news), per `corpus-verdicts-A.md:
  314-327` — or state explicitly that these enter transitively through the resolved node-config fp1.

### M4 — The nightly mutmut extension to the node money path will run against a code-less default branch until the squash-merge; the money-path mutation gate is silently vacuous

- **Where:** TN-23 (nightly mutmut extended to node money-path modules, A30), TN-16 (CI matrix).
- **Input that did not land:** `corpus-verdicts-A.md` tension 10 (line 1337): *"The nightly mutation
  job runs on the wrong branch, today. GitHub runs scheduled workflows on the default branch, and
  `battery.yml:167` asserts main is 'exactly where the ratified exact.py / chrono.py live.' They are
  not — `git ls-tree main` shows no `packages/`. Until the operator's squash-merge, the first nightly
  mutmut run will find nothing and fail closed on zero mutants classified. Fix by merging, or by
  pointing the schedule at integration."*
- **What the spine did:** TN-23 extends mutmut to the node's money-path modules and TN-1 handles the
  base-branch (`origin/integration@ef9bb25`, re-point onto main after the squash-merge), but neither TN
  addresses that the scheduled mutmut job targets the **default branch**, which carries no `packages/`
  (and will carry no `qmn/`) until the merge.
- **Why it matters:** the node's money-path mutation gate is the money-path safety net TN-23 leans on;
  if it runs on a code-less branch it classifies zero mutants and either fails closed (noise the
  operator learns to ignore) or passes vacuously. This is a silent gate on the money path.
- **Concrete fix:** in TN-16 (or TN-23), bind that the nightly mutmut schedule targets the branch that
  carries code — `integration` until the operator's squash-merge lands the node on `main`, then `main`
  — and that a "zero mutants classified" run fails closed and alarms rather than passing.

### M5 — "Superseded-by-terminal-subject" — the resolved node-close-vs-venue-stop race — is not carried in TN-24; QB3 named it as a thing the spine should bind

- **Where:** TN-24 (position-safety closures), TN-6 (order path).
- **Input that did not land:** QB3 "What the spine should bind" (`corpus-verdicts-B.md:381`):
  *"Superseded-by-terminal-subject as a named outcome, never a stream-blocking UNKNOWN."* Settled at
  `SCN-0010:33`/`ct-20:21,:51`: a node close that races a venue stop-out reads back as
  `rejected-by-venue (superseded-by-terminal-subject)` — *"a named outcome never UNKNOWN."*
- **What the spine did:** TN-24 enumerates the position-safety closures (a)–(i) precisely so epics have
  a checklist — partial fill, duplicate fills, disconnect-mid-order (→ UNKNOWN), position mismatch — but
  omits the close-vs-venue-stop race and its named outcome. TN-6/TN-11 inherit the order-state fold from
  qmf-venue but the spine never surfaces this outcome.
- **Why it matters:** TN-24 is the enumerated closure list; an epic writer working from it could treat a
  node close that races a venue stop as UNKNOWN (blocking the stream) instead of the ratified named
  outcome, converting a benign race into a stalled command pipe.
- **Concrete fix:** add TN-24(j): a node close superseded by a venue terminal event (stop-out / margin
  liquidation) reads back as `rejected-by-venue (superseded-by-terminal-subject)` — a named outcome,
  never a stream-blocking UNKNOWN (`SCN-0010:33`, `ct-20:21,:51`).

---

## LOW

### L1 — "Requote" is named in the brief's things-to-check but never addressed by name
- **Where:** TN-11 (error map), TN-24.
- **Input:** operator brief things-to-check (memlog) names *"partial fills/requotes/disconnect-mid-
  order/duplicate fills/position mismatch."* QB3 (`corpus-verdicts-B.md:344`): a requote *"is a venue
  rejection carried through the versioned per-adapter error map … unmapped codes failing closed to
  (transient venue failure, retryable=no, outcome=UNKNOWN)."*
- **Gap:** the spine covers partial fills / disconnect / duplicate fills / position mismatch (TN-24) but
  never states that a requote is a venue rejection routed through the TN-11 error map.
- **Fix:** one clause in TN-11 or TN-24: a requote is a mapped venue rejection through the error map,
  no separate vocabulary.

### L2 — Amend-atomicity measurement has no home; the corpus calls it a first-connection empirical check
- **Where:** TN-8 (breakeven ratchet), TN-10 (five-check verification suite), TN-11.
- **Input:** QB10/QMX-F063 (`corpus-verdicts-B.md:858`): amend atomicity *"is a first-connection
  empirical check, and it gates whether dual-sided amends are ever legal."*
- **Gap:** TN-8 says "single-sided amend_protection until amend atomicity is measured at the venue" and
  TN-23 lists F063 as a node story, but no TN states *where/how* atomicity is measured. TN-10's
  verification suite is a fixed five checks and does not include it.
- **Fix:** name the amend-atomicity measurement as a sixth first-connection empirical check (or an
  explicit venue probe), gating dual-sided amends, in TN-10 or TN-11.

### L3 — Venue-initiated close reasons (`venue_liquidation`, `venue_initiated_close`) not surfaced
- **Where:** TN-8, TN-24.
- **Input:** QB3 (`corpus-verdicts-B.md:308-310`): *"CT-29 gives them their own close reasons —
  `venue_liquidation` (reserved for venue margin liquidation; the bare phrase 'stop out' is banned) and
  `venue_initiated_close` — with `closing_authority = venue`."*
- **Gap:** the spine names `kill_line_flat` and `protection_forced_flat` (TN-8) but not the
  venue-initiated close reasons; the "stop out" banned-word rule is not carried.
- **Fix:** in TN-24, note the CT-29 venue-initiated close reasons and `closing_authority = venue`.

### L4 — Shadow-lane labelled "adopted here" but deferred in TN-19; the "no-ambient-randomness binds the live runtime" guardrail is not stated as a node invariant
- **Where:** Inherited-invariants table (spine line 91) vs TN-19; Consistency Conventions.
- **Input:** PRD §6 shadow-lane doctrine (`prd.md:423-431`): *"A recovered or pre-trained model carries
  no authority without fresh ratification … Training is an offline job — it may seed its RNG, provided
  the seed is recorded; the no-ambient-randomness invariant binds the live runtime."*
- **Gap:** the invariants table says the shadow lane is "adopted here" but TN-19 *defers* it (naming the
  seam). The specific live-runtime guardrail — no-ambient-randomness binds the live runtime, recovered
  models carry no authority without fresh ratification — is covered only implicitly by the ambient-scan
  tier-1 scanner (TN-23) and is not stated as a node invariant.
- **Fix:** correct the invariants-row wording (shadow lane = seam named, deferred) and add
  "no ambient randomness in the live runtime; a recovered/pre-trained model carries no authority without
  fresh ratification" to the Consistency Conventions or TN-19.

### L5 — Stale `qmf-venue` README (red flag R13) not flagged for the documentation factory
- **Where:** Parent annotations / TN-11.
- **Input:** parts-bin R13 (`parts-bin.md:560`): *"`packages/qmf-venue/README.md:10-13` still says
  'Scaffold (Story 1.1)…'. Trust the code … Anyone scoping node work from package READMEs will size
  this badly wrong."*
- **Gap:** every other red flag R1–R15 has an explicit spine answer; R13's answer (the spine sourced
  from code, not READMEs) is implicit, and the stale README is not flagged for correction in the doc
  factory increment.
- **Fix:** add a Parent-annotations line: the doc factory corrects the stale `qmf-venue` README.

### L6 — Venue-maintenance-window handling diverges from QB1a's recommendation without citing the divergence
- **Where:** TN-11 (venue maintenance windows), A14.
- **Input:** QB1a (`corpus-verdicts-B.md:149-156`) recommended treating a broker maintenance window as
  a daily-dead-zone window discovered by watching the broker (reusing ratified entries-only machinery).
- **Gap:** TN-11 instead rules maintenance windows are *not* a window kind at all — handled by the
  sensing-outage fail-closed rule (A14). This is a defensible cheap-veto, but it means an *announced*
  maintenance window (`maintenanceEndTimestamp`) does not proactively block entries ahead of the
  disconnect; the spine does not acknowledge it took a different path than the adjudicator recommended.
- **Fix:** note in TN-11 that A14 consciously diverges from QB1a (no proactive pre-maintenance entry
  block; the down session fails closed) so the choice is legible, not silently different.

### L7 — Position/balance first-class journaled ingestion (parts-bin B28, the CT-20 "seven journaled types" gap) is only implicit
- **Where:** TN-11 (equity derivation), TN-13 (live data), TN-10 (reconciliation).
- **Input:** parts-bin B28: *"Position / balance event ingestion as first-class journaled kinds —
  absent … Add position- and balance-event ingestion (this is the CT-20 'seven journaled types' gap)."*
- **Gap:** the node must add position- and balance-event ingestion as first-class journaled observation
  kinds; TN-11 (equity) and TN-10 (reconciliation folds) consume them but no TN explicitly homes the
  ingestion-kind build.
- **Fix:** name the position/balance ingestion kinds as a build item in TN-13 (data) or the ports/seed.

### L8 — Streaming-indicator restore-equivalence and single-feeder `WriterId` live only in the ports table, with no TN discussion
- **Where:** Structural Seed ports table (`SnapshotScope`, `StreamingIndicator.update()` feeder
  `WriterId`) vs TN-5/TN-13.
- **Input:** parts-bin §3 seams: `SnapshotScope (OS, arithmetic-reference build)` injected for
  streaming-indicator restore-equivalence; `StreamingIndicator.update()` feeder `WriterId` single-feeder
  law, one holder per streaming instance on the live path.
- **Gap:** streaming indicators run on the live path (TN-5's loop) and must restore equivalently across
  a node restart (TN-2's boot / TN-4's shutdown), but no TN discusses the single-feeder law or snapshot
  restore-equivalence for them; it is homed only in the ports table.
- **Fix:** one clause in TN-5 or TN-13 binding the single-feeder `WriterId` per streaming instance and
  snapshot restore-equivalence within the same `SnapshotScope` on the live path.

---

## Notes on inputs that reconciled cleanly (recorded so a re-review does not re-open them)

- **Restore-drill cadence** (nightly sample + monthly full, TN-13): a deliberate blend of QA8b (nightly
  + quarterly) and QB5a (weekly + monthly); the memlog records the choice explicitly. Not a gap.
- **Reconciliation cadence gates the command pipe only** (TN-10): matches `ct-20:26` /
  `trading-node-notes.md:32`. ✓
- **Four verdicts, superseded three** (Corrections #1, TN-10): matches QA9 / QB3 / QB6. ✓
- **Paper on the paired demo, not `world=simulated`, no twin** (TN-9, Corrections #2): matches QA7 /
  QB4 / red flag R9. ✓
- **KSA levels adopted from GitBook, matrix blank-blocks-live** (TN-7): matches QA6 / A tension 8. ✓
- **Two secret doors, host-key sealing not TPM2, SSH-stdin wizard** (TN-12): matches QB4 / QA5. ✓
- **In-house transport, protobuf 7.36.0, zero Spotware code; the SDK protobuf conflict is moot**
  (TN-11, Corrections #4): matches QA5 / A tension 9 / B tension 9. ✓
- **Trendbar basis measured-per-broker, tick-based interim comparison** (TN-11): matches QB11 /
  A tension 13. ✓
- **Local `integration` ref stale, Linux CI lane, tier-3 deferral stale-and-closed** (TN-1, TN-16):
  matches A tensions 11–12. ✓
- **Margin-aware sizing deferred with consequence stated; VPS/KYC/admin-fee human-only** (Deferred
  table): matches QB9 / the brief's open operator items. ✓
