---
review: input-reconciliation
target: ARCHITECTURE-SPINE.md (AD-22..AD-25 + updated Stack/Conventions/Deferred, indicators/structure sitting, 2026-08-20)
scope: everything the load-bearing inputs demanded of this increment — five-hats-sweep.md (indicators/structure-owned items + named cross-sitting obligations), gap-report.md (GAP-0031..0034 exact clauses), .memlog.md operator riders (last ~7 entries, 2026-08-20)
stance: reconciliation, not re-litigation. Checking landing, not correctness of the ruling itself.
date: 2026-08-20
---

# Input reconciliation — indicators/structure sitting (AD-22..AD-25)

## Verdict

Of the 14 discrete obligations checked, 9 are fully LANDED, 4 are PARTIAL (a real piece of the ask is missing or silently narrowed), and 1 is a genuine cross-sitting orphan whose indicator-side prerequisite landed but whose consuming mechanism (owned by an earlier, already-closed sitting) never materialized. Nothing was found flatly DROPPED with zero trace. The most consequential PARTIAL is GAP-0031's **output alignment** clause, which the gap report asks for by name and AD-22 never rules on — the spine defines what an indicator returns during warm-up but not how any output element corresponds to its input element/timestamp. The second most consequential is **T-3's latency-decomposition structure** (tick→evidence→indicator→decision→risk→order, named stages), which AD-22 answers only for the indicator's own two rungs and leaves the cross-component pipeline undecomposed and unlisted in Deferred — a quiet drop rather than an explicit one.

---

## Five-hats sweep — items owned by the indicators/structure sitting

### R-5 — Split manifests need purge and embargo widths — PARTIAL

**Ask:** a declared purge width + embargo width in the split manifest, derived from the max horizon of consuming artifacts, participating in the split fingerprint.

**What landed (indicator half):** AD-25's closing clause — *"The confirmation delay is declared contract surface entering the fingerprint; with AD-22's warm-up it feeds future split purge/embargo widths."* Combined with AD-22's warm-up-as-fingerprinted-contract-surface, the indicator/structure sitting supplied exactly the two horizon values (warm-up length, confirmation delay) that a purge/embargo calculation would consume.

**What did not land:** the consuming mechanism itself — a purge width + embargo width actually recorded in the split manifest and entering the split's `fp1` fingerprint — was never added anywhere. It is not in AD-21 (the data sitting's split-manifest rule, ratified and closed *before* this indicator sitting reopened): AD-21 says manifests are "fingerprinted, time-ordered, non-overlapping," pin one calendar identity, and use frozen TradingDate boundaries — no purge/embargo language at all. Since the data sitting already closed (memlog: "DATA AREA CLOSED") without this, and no later sitting has reopened AD-21, R-5's actual deliverable is still absent from the spine. The phrase "feeds future... widths" in AD-25 is honest about this (it says *future*), so this is not a silent flattening — but it means R-5 as a whole is not landed, only staged.

### R-6 — Warm-up as declared, fingerprinted property — LANDED (indicator half); registry half explicitly deferred, not dropped

**Ask:** warm-up as contract surface entering the fingerprint (so the registration causality gate can consume it).

**Landed:** AD-22 — *"Every configured indicator declares its warm-up length as contract surface entering its AD-10 fingerprint. During warm-up the output is a marked not-ready value, never a number."* Exact match to the ask.

**Registry consumption half:** GAP-0016 (the causality/look-ahead registration gate) was deferred to the backtesting sitting by an earlier, explicit operator ruling (memlog: "GAP-0016 + GAP-0017 DEFERRED TO BACKTESTING SITTING... artifacts registered before that sitting will lack causality evidence"), and the spine's own Deferred table repeats this. So the gate that "must consume" warm-up doesn't exist yet — but that absence is openly declared elsewhere in the spine, not a quiet drop by this sitting.

### D-3 — Bulk representation for scaled-integer money — LANDED

**Ask:** one bulk form (int64 array + out-of-band scale), ruled once, adopted everywhere.

**Landed:** AD-22 — *"Input series: the bulk form of exact values is defined in `qmf-core` — int64 arrays plus out-of-band scale/metadata (AD-7 values in bulk); one representation workspace-wide."* The five-hats text expected the data sitting to rule it first with indicators adopting; instead the indicator sitting minted it directly in `qmf-core` (memlog: "closes D-3 for this library"). Outcome matches the ask's intent (single representation, ruled once) even though the sequencing differs from what R-5-adjacent finding envisioned.

### D-6 — Stateful seam concurrency contract — LANDED (indicator slice)

**Ask:** every stateful seam declares whether it's shareable, cloned-per-consumer, or guarded.

**Landed:** AD-22 — *"Streaming instances follow AD-15: exactly one feeder, unlimited readers. Instances deduplicate by content fingerprint (formula + parameters + instrument + timeframe)... Each instance declares its state bound and supports snapshot/restore..."* Precisely answers the ask for the indicator's stateful streaming instances. (The data-store-handle and venue-session slices of D-6 remain that sitting's job, correctly out of this review's scope.)

### D-7 — Extension shape for custom indicators/structure families — PARTIAL

**Ask:** the sitting must define the extension seam concretely — how it is *declared*, how it is *found*, how it *versions*, how its identity enters *fingerprints*.

**Landed:** declared — AD-22: *"Custom indicators are authorable as CT-16-conformant extensions or as plain Python outside governed evidence; conformance is required only to enter governed evidence."* AD-25 mirrors this for structure families and states it explicitly: *"family authoring is the primary use case of the extension shape (same shape as AD-22's custom indicators)."* Identity-in-fingerprint — warm-up (AD-22) and confirmation delay (AD-25) both enter `fp1`. Versioning at the *kind* level — "Kinds are addable, never redefined" (AD-22); "Families are QMX-owned, versioned, addable never redefined" (AD-25).

**What did not land:** *discovery* ("how it is found") is never addressed — nothing states how a bot, the registry, or a factory agent locates a custom indicator or structure family authored outside the roster (contrast with AD-2's calendar extensions, which get a named package location, their own SemVer ladder, and a workspace position). Whether custom indicator/structure extensions ship as separate versioned packages (like calendar extensions) or live some other way is also unstated. The shape is named and partially specified; the discovery and packaging mechanics are not.

### T-3 — Latency budget decomposition as a named structure — PARTIAL

**Ask:** the venue and indicator sittings should record the latency budget decomposition as a structure — tick received → evidence write → indicator update → decision → risk evaluation → order submitted, each a named, separately measurable stage with its own AD-13 rung — so first measurements attach to something and stage-insertion becomes visible.

**Landed (indicator's own slice only):** AD-22 — *"The AD-13 ladder carries two rungs per indicator — burst throughput and per-tick latency — both factory-gate machinery."* This gives indicators their own measurable per-tick-latency rung, which is necessary but not sufficient for T-3's ask.

**What did not land:** the cross-component named pipeline decomposition itself (the six named stages) does not appear anywhere in the spine — not in AD-13, not in AD-22, not in the Deferred table. Since the venue sitting hasn't run yet, an incomplete decomposition is expected, but T-3 specifically asked that the *structure* (the stage list) be recorded now, independent of which sitting owns which stage's number, precisely so later measurements have something to attach to. It is absent and not flagged as deferred — this is the quieter of the two most consequential gaps in this review.

### Conflict X-4 — One AD-13 ladder cannot serve both GA burst fan-out and 1s scalping latency — LANDED

**Ask:** make batch/streaming explicit conformance targets of one protocol with a stated equivalence obligation, and give AD-13 two separate rungs.

**Landed, verbatim match:** AD-22 — *"One consumer-blind contract, two conformant modes: batch (whole series in, whole series out) and streaming (a stateful incremental instance). Identical canonical inputs MUST produce identical outputs across modes; that equivalence is an AD-4 tier-2 contract test."* Plus the two-rungs clause quoted under T-3 above. This is the cleanest full landing in the review — the resolution shape proposed by the conflict entry was adopted essentially word-for-word.

---

## Cross-sitting obligations

### D-1 — Every remaining sitting must close with an explicit edge request or "none required" — LANDED

AD-22: *"`qmf-indicators` depends on `qmf-core` only (D-1 answer: no new edges)."* AD-25: *"`qmf-structure` depends on `qmf-core` only in V1; its registry/data emissions (CT-06/07/08) go through the application/composition layer until an inter-library edge is ratified."* Both packages closed explicitly, as required.

### D-4 — Public surface rule, one line per package — LANDED (this sitting's packages)

AD-22: *"Public surface: the CT-16 protocol and core value types are public; everything else in the package is private (underscore convention)."* AD-25: *"Public surface: the CT-17 protocol and core value types; everything else private."* Both supply the exact one-liner D-4 asked for. (D-4 also asked the registry sitting to state the *workspace-wide* convention — that half is registry's own obligation, not visible in AD-16/17/18's text above, and is outside this sitting's responsibility to close.)

### T-7 — Indicator warm-state slice on restart — LANDED

AD-22: *"Each instance declares its state bound and supports snapshot/restore so restart re-warm never replays a day."* The memlog ties this explicitly to T-7. This exceeds the literal ask (replay-to-warm) by ruling snapshot/restore instead, which is a stronger answer to the same problem.

### R-2 — Burst rung on the AD-13 ladder — LANDED (indicator's slice)

AD-22's two-rungs clause (burst throughput + per-tick latency) directly implements the AD-13-ladder-extension half of R-2/X-4's resolution shape, as far as indicators are concerned. R-2's own primary content — a *registry*-side burst rung (fingerprints/s, registrations/s, edge-appends/s) — remains the registry sitting's unfinished business; no registry AD (AD-16/17/18) mentions an AD-13 rung. That gap is real but belongs to the registry sitting's reconciliation, not this one.

---

## GAP report — exact question clauses

### GAP-0031 — indicator protocol

| Clause | Status | Evidence |
|---|---|---|
| input series | LANDED | AD-22: bulk form (int64 array + out-of-band scale) defined in `qmf-core`, one representation workspace-wide |
| **output alignment** | **PARTIAL — see below** | not explicitly ruled |
| missing values | LANDED | AD-22: "marked output gap or a typed refusal per the indicator's declared missing-value policy — never silent filling" |
| warm-up | LANDED | AD-22 warm-up clause (quoted above) |
| statefulness | LANDED | AD-22: streaming instances, AD-15 one-feeder/unlimited-readers, declared state bound |
| streaming updates | LANDED | AD-22 streaming-mode + snapshot/restore clauses |
| typed failures | LANDED | AD-22: "All failures are AD-11 typed refusals" |

**Output alignment — the notable quiet gap.** The gap report asks this by name, and the review brief calls it out explicitly. AD-22 states two conformant modes must produce identical outputs for identical inputs, and that warm-up outputs are "marked not-ready" rather than numbers — which *implies* a 1:1 correspondence between input elements and output elements (every input bar gets an output slot, even a not-ready one, rather than warm-up bars being omitted from the output series). But this is inference from adjacent rules, not a ruling: nothing states output series length equals input series length, nothing states what timestamp/index an output element carries relative to its input (same instant as the triggering bar's close? a lag? indicator-declared?), and nothing addresses alignment behavior across a missing-input gap (does the output series compress, or does it carry a gap marker in the same position?). This is exactly the kind of quiet requirement an AD structure can flatten: the *shape* question ("what protocol exists") absorbed the *coordinate* question ("how do I index into the output against the input"), and the latter never got its own sentence.

### GAP-0032 — canonical arithmetic reference and dual-reference checks — LANDED

AD-23 fully answers both halves: TA-Lib pinned as a version pair (C 0.7.1 + Python wrapper 0.7.1) per release, wrap-not-reimplement for batch, streaming held equal by AD-22's equality law; dual-reference checks recorded as registered comparison artifacts (input fingerprint + parameter fingerprint + declared tolerance + verdict), upgrades gated through a comparison suite with contract-format-version minting on any output change.

### GAP-0033 — light/heavy objective rule — LANDED

AD-24: light iff a configured indicator declares AND benchmark-proves all four bounds (per-update cost within the live-path latency rung, bounded state size, bounded evidence window = its warm-up length, synchronous availability); everything else is heavy, same CT-16 contract, different placement. Classification is per-configuration, never per-name, exactly as asked.

### GAP-0034 — families ship first, causal confirmation rule, observed-at/confirmed-at — LANDED

AD-25: seed families named (swing points, horizontal levels from confirmed swings, zones, structure breaks); a family ships into governed evidence only once its confirmation rule is stated precisely ("confirmed the moment X happens," X knowable at that instant); every output carries observed-at + confirmed-at (AD-8 instants), invalidated-at appended never deleted.

---

## Operator riders (.memlog.md, 2026-08-20, last ~7 entries)

### Resource-visibility rider — PARTIAL (quiet flattening)

**Memlog ask (GAP-0031 and reaffirmed at GAP-0033):** a four-part chain — *declared budget = promise → AD-13 measurement = proof → AD-14 metrics = runtime visibility → UI display = platform territory.*

**What AD-24 actually states:** *"a configured indicator is light iff it declares AND benchmark-proves all four bounds... The declaration is contract surface; a light claim that fails its rung is refused at the merge gate."* This lands the first two links of the chain (declare, benchmark-prove) cleanly. It does **not** restate or cross-reference the third and fourth links — AD-24's text never mentions AD-14 metrics as the runtime-visibility layer for indicator resource cost, nor does it note UI display as platform territory. The two dropped links are consistent with pre-existing rules (AD-14 already commits to Prometheus-exportable metrics generally; UI is out-of-repo by construction), so nothing contradicts the rider — but the rider itself, as a connected four-part promise the operator asked to see honored, is only half-restated in the binding AD text. This is the second-most concrete instance in this review of a tone/connective requirement getting flattened by the AD format, which favors terse bounded rules over the fuller narrative chain the operator dictated.

### Extensibility / plain-Python rider — LANDED

AD-22: *"Custom indicators are authorable as CT-16-conformant extensions or as plain Python outside governed evidence; conformance is required only to enter governed evidence."* Matches the memlog rider verbatim in substance.

### Heavy-offload-to-MIS rider — LANDED

AD-24: *"Everything else is heavy: computed off the trading path (MIS/research side, node territory — computed once and fanned out) through the same CT-16 contract; different placement, not a different species."* The Deferred table separately confirms: *"MIS fan-out wiring for heavy indicators... Node territory (wiring)... AD-22/AD-24 bind both."* Matches the rider exactly, including the "wiring is node territory" scoping.

### Failure-monitoring emphasis — LANDED (by correct delegation)

AD-22 explicitly delegates rather than re-litigating: *"...both factory-gate machinery; production visibility is AD-14's job."* AD-14 (already ratified 2026-08-19) already carries loud-failure, correlation-id, and Prometheus-exportability obligations. Pointing back to an existing, adequate AD rather than restating it is the correct move, not a drop — the operator's "very important, know when something fails and how" is honored by AD-14's pre-existing text plus this sitting's explicit acknowledgment that it applies.

### No-lock-in / SMC-ICT from-scratch-families addendum — LANDED, close to verbatim

AD-25: *"No privileged families: the V1 seed candidates... are candidates only; operator-authored from-scratch families (SMC/ICT-class objects included) are first-class peers under the identical law — family authoring is the primary use case of the extension shape."* This directly mirrors the operator's own words ("I don't want to be locked in under any circumstance") and elevates from-scratch authoring to primary-use-case status rather than an afterthought, exactly as dictated.

### Adjustable / maintainable / industry-grade / whole-system-lens conditions — LANDED in substance, not in the words used

The literal phrases ("adjustable," "maintainable," "industry-grade," "whole-system lens") do not appear in AD-22/24/25's text, but the substance is present: adjustable — kinds/families "addable, never redefined"; maintainable — versioned, QMX-owned, contract-format-version-gated upgrades (AD-23); whole-system lens — composability via AD-17 ("a composite is its own artifact with lineage to its children"), and both AD-22 and AD-25 explicitly use "the same shape as" language to keep indicators and structure consistent with each other rather than diverging. This is a tone condition rather than a checkable clause, and it reads as honored rather than flattened.

---

## Summary table

| Item | Status |
|---|---|
| R-5 (purge/embargo widths) | PARTIAL — indicator prerequisite landed (AD-25); consuming mechanism absent from AD-21, unowned since data sitting closed |
| R-6 (warm-up fingerprinted) | LANDED (indicator half); registry-gate half openly deferred, not dropped |
| D-3 (bulk money representation) | LANDED — AD-22 |
| D-6 (streaming concurrency contract) | LANDED — AD-22 |
| D-7 (extension shape) | PARTIAL — declaration/versioning/identity landed; discovery/packaging mechanics unaddressed |
| T-3 (latency decomposition structure) | PARTIAL — indicator's own two rungs landed; six-stage pipeline decomposition absent and unlisted in Deferred |
| X-4 (two-mode ladder conflict) | LANDED — near-verbatim adoption of proposed resolution |
| D-1 (edge request/none) | LANDED — AD-22, AD-25 |
| D-4 (public surface one-liner) | LANDED (this sitting's packages) |
| T-7 (indicator warm-state slice) | LANDED — snapshot/restore, exceeds literal ask |
| R-2 (burst rung) | LANDED (indicator's slice); registry's own burst rung still outstanding, out of scope here |
| GAP-0031 input series | LANDED |
| GAP-0031 output alignment | **PARTIAL — most concrete gap in this review** |
| GAP-0031 missing values / warm-up / statefulness / streaming updates / typed failures | LANDED |
| GAP-0032 (TA-Lib reference + dual-reference checks) | LANDED — AD-23 |
| GAP-0033 (light/heavy rule) | LANDED — AD-24 |
| GAP-0034 (families, confirmation rule, observed/confirmed-at) | LANDED — AD-25 |
| Resource-visibility rider | PARTIAL — declare+prove landed; AD-14-metrics/UI-platform links not restated in AD-24 |
| Extensibility/plain-Python rider | LANDED — AD-22 |
| Heavy-offload-to-MIS rider | LANDED — AD-24 + Deferred table |
| Failure-monitoring emphasis | LANDED — correct delegation to AD-14 |
| No-lock-in/SMC-ICT addendum | LANDED — near-verbatim, AD-25 |
| Adjustable/maintainable/industry-grade conditions | LANDED in substance |

No items are classified DROPPED — everything checked either landed with a citable clause or landed partially with a specific, nameable gap.
