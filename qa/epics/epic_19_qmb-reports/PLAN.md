# Verification PLAN — Epic 19: QMB Reports & Result Artifacts

**Audit tier:** **T3** (lighter than T2 — the deliverable is **L3 acceptance tests for the P0/P1 ACs**, one **L6** adversarial review, one **L4** golden-scenario participation with Epic 14, and one regression pin per *confirmed* advisory finding. No exhaustive L1/L2 branch or property suites are built.)
**Package under test:** `qmb/src/qmb/results/` — the CT-32 assembly and its downstream reads. Module *names* observed by directory listing only (`ct32.py`, `measures.py`, `accounting.py`, `charts.py`, `render.py`, `interpret.py`); **no source file was read before §4 was authored.**
**Delivers:** FR-043 — the canonical CT-32 result artifact, the QMX-native measure set, suppression/veto accounting, charts-as-data, and pure downstream rendering/interpretation/reproduction.
**Governing invariants:** QMB spine **B-10** (measurement publishes, never acts; CT-32/CT-13 adoption) and **B-13** (distribution/identity), **AR-59** (full result label set), **AR-14** (single canonical `fp1` function), **AR-15** (exact money/time), **AD-10** (identity-vs-display), **AD-12** (result label), **AD-40** (closed unit-kind vocabulary), and **DEC-0162** (reader-derived verdicts — never stored).

> **PROCESS GAP (read first).** Two authorities named in the audit brief **do not exist in this worktree**:
> `_bmad-output/test-artifacts/test-design-qa.md` (the Per-Epic Test Plan Template + the L0–L6 test-level architecture) and
> `_bmad-output/test-artifacts/test-design/QMX-handoff.md` (the 15 P0/P1 assertions + this epic's risk-gate rows). Confirmed absent by full-tree search; `_bmad-output/test-artifacts/` does not exist. Sibling plans (`epic_13`, `epic_14`) record the same gap.
> **Consequence:** the 8-section structure, the L0–L6 taxonomy in §5, and the P0/P1 split in §3 are **reconstructed** from the ratified corpus (epics.md Epic 19; `docs/contracts/ct-32`; `docs/components/qmb.md` B-4/B-10; spec-reports `R-RPT-*`; SCN-0012; the constitution) and the **level scheme the task brief supplies for T3** (L3 acceptance · L4 scenario with E14 · L6 review · regression pins). **Risk gate `R-016` = "L4 scenario participation with E14"** is taken from the task brief. When the two files are restored, reconcile §1 template order, §3 assertion set, and §5 level definitions against them before executing.

---

## Section 1 — Epic Context, Scope & Authorities

**What this epic is.** Every completed QMB run's pure `run()` return is assembled into **exactly one** canonical, machine-readable **CT-32 performance-result** written into the run's own output directory. The CT-32 container is **ADOPTED, not reinvented** — QMB is the designated CT-32 producer (CT-32 `intended_producers: [COMP-QMB]`, DEC-0163); there is never a second "report JSON" that could drift from the evidence. The artifact holds the full AD-12 label, an ordered unit-kinded `measure_set` (no composite score), suppression and veto accounting, chart series (data, never images), and a fidelity identity carrying the pre-GAP-0048 `optimistic` taint. Every human-facing rendering, agent interpretation, and reproduction check is a **pure downstream function of the artifact** — agents read the artifact, never renderings — and none of them sizes, promotes, benches, binds, or changes a mode.

**The verdict discipline (epic-specific centre of gravity).** A run's admission-bar **verdict is never stored** in the artifact. It is a **reader-derived, per-requirement, read-time fold** against the cited AD-32 bar (structural parity on producer-contract versions, unit-kind, and comparison rule), and its answer is **`not-yet-ruled`** while a requirement is blank or on a world/role miss (DEC-0162; qmb.md B-4 §77-81; CT-32 invariant, ct-32 L33). A **replay-world verdict can never gate live money.** Epic 19 therefore asserts the **negative** — the artifact stores no verdict, no pass/fail, no composite score — and that the artifact carries the **per-requirement inputs** the downstream fold consumes (measures + unit-kinds + `metric_contract_format_version` + world + account role + suppression/veto + fidelity taint). *The fold computation itself is not built in Epic 19 (see §7 boundary).*

**In scope (Stories 19.1–19.5):**
- 19.1 — the canonical CT-32 container + full AD-12 label + `fp1` via qmf-core only + single-account-role rule + provenance-derived world + fidelity/optimistic taint.
- 19.2 — the ordered, unit-kinded, exact, governed measure set with no composite score.
- 19.3 — suppression accounting (authority, reason) + veto accounting (door), from the run's own CT-13 journal streams only.
- 19.4 — chart series as data (`{name, unit_kind, points:[{t,v}]}`), derived from the run's own position/order/journal record.
- 19.5 — pure downstream HTML/markdown rendering, in-house interpretation skills, run reproduction, and per-run concurrency isolation.

**Out of scope (owned elsewhere; seams only here) — per the EPIC-BINDING RULE:**
- **The ledger line and its "one pass/fail end-result line" (`R-RPT-16/17/18/20`) → Epic 15** ("exactly one ledger line per run"). *Note the documented tension:* spec-reports `R-RPT-17` says the ledger stores one structural pass/fail line, but ratified **DEC-0162 / CT-32 / qmb.md B-4** say verdicts are **never stored** — the ratified corpus wins; Epic 19 tests the never-stored discipline and flags the conflict for the Epic-15 auditor.
- **The read-time verdict fold itself** (per-requirement outcomes, `not-yet-ruled`, re-verdict-on-ruling, the canonical-assignment qualifier, the replay-never-gates-live *enforcement*) → the Book-bar/admission reader (qmb.md B-4; downstream of the Epic-15 ledger). Epic 19 owns only the artifact's *inputs* and the *absence* of a stored verdict.
- **The run loop, warm-up, fills, and the pure `run()` return content** → Epic 14. Epic 19 consumes that return; it does not produce it.
- **The orchestrator, process-per-run, operational logs streamed "during" a run (`R-RPT-16` log half)** → Epic 15.
- **Fidelity *content* / GAP-0048** (whether a fill is correctly modeled; forex calibration; `world=simulated` unlock) → Epic 17 / GAP-0048. Epic 19 stamps the `optimistic` taint and the non-edge-claiming property only.

**Authorities, in precedence order:**
1. Epic 19 section of `_bmad-output/planning-artifacts/epics.md` (Stories 19.1–19.5, ACs; lines 3730–3963).
2. `docs/` knowledge base: `docs/contracts/ct-32-performance-result.yaml` (the container, its invariants, its enums, the reader-derived-verdict invariant at L33); `docs/components/qmb.md` (B-4 reader-derived verdicts §77-81; B-10; the "may never" list §25); `docs/components/qmf-risk.md` (admission-bar / not-yet-ruled discipline); `docs/scenarios/SCN-0012-qmb-replay-run.md` (steps 7–8 — the L4 golden scenario, **R-016**); `docs/constitution.md` (L6 fixtures, L17 human-promotion, L20 nothing-synthetic-validates-edge, L38 configurable=UI-editable); contracts `ct-04` (typed refusal), `ct-13` (journal), `ct-29` (exit record).
3. spec-reports `R-RPT-1..24` (`_bmad-output/planning-artifacts/architecture/.../research-backtesting/specs/spec-reports.md`) — the requirement source the epic intro cites; **research-spec precedence is below the ratified corpus** (where they conflict — R-RPT-17 stored pass/fail — the ratified decision governs).
4. *(Missing — see Process Gap)* test-design-qa.md; QMX-handoff.md.

**Two senses of "tier" (do not conflate).** *Audit tier* **T3** = this plan's scrutiny band (lighter than T2). *Test tiers* tier-1/tier-2/tier-3 = the project's `poe check` / `check-integration` / `check-release` execution bands; §5 maps the L-levels onto them.

---

## Section 2 — Requirements → Behaviours Traceability

Every row is a testable behaviour extracted from a ratified source and confirmed to belong to **Epic 19's** section of epics.md. "Ref" cites the governing AC / spine / contract / R-RPT.

| # | Behaviour (requirement, stated as an assertion) | Ref | Story | Prio |
|---|---|---|---|---|
| R1 | A completed run's pure return assembles into **exactly one CT-32 container** written into the run's output dir; its `fp1` is returned; **no second "report JSON"** is produced (CT-32 ADOPTED, not reinvented). | R-RPT-1, CT-32 inv.1, B-10, AC19.1 | 19.1 | **P0** |
| R2 | The container carries the **full AD-12 label**: producer contract identity + integer format version, input fingerprints, evidence time range (**trading interval only, never warm-up**), occurrence identity, evidence class, world, account-binding role. | AR-59, AD-12, B-10, B-4, R-RPT-2, AC19.1 | 19.1 | **P0** |
| R3 | The label additionally carries resolved-config `fp1` (run-id root), `registry_as_of`, data/split fingerprints, fidelity identity, and RNG provenance where the run is stochastic. | AR-59, B-13, AC19.1 | 19.1 | P1 |
| R4 | `fp1` is **label-derived per AD-10** and computed **only** by qmf-core's canonical `fp1:sha256` (AR-14); **no other module recomputes it**, and **no float bytes ever enter identity**. | R-RPT-6, AR-14, AD-10, AC19.1 | 19.1 | **P0** |
| R5 | A result that would span **more than one account-binding role** → a typed **policy-rejection**, and **no artifact is written**. | R-RPT-7, CT-32 inv.8, AC19.1 | 19.1 | **P0** |
| R6 | `world` is copied **verbatim from data-derived provenance, never a flag**; a replay run stamps `world=replay`; a store-tainted `world=simulated` has already refused upstream, so **no such artifact is produced in V1**. | B-7, SC-06, AC19.1 | 19.1 | **P0** |
| R7 | Fidelity identity = adapter-id + composition-version + `optimistic` taint ⇒ the artifact is **non-edge-claiming by construction**: no verdict-bearing claim, cannot claim edge, cannot spend split budget until GAP-0048. | SC-06, B-6, AC19.1 | 19.1 | P1 |
| R8 | Every measure is a member of an **ordered `measure_set`** and carries a **non-null unit-kind** from the closed AD-40 vocabulary. | R-RPT-3, AD-40, B-10, AC19.2 | 19.2 | **P0** |
| R9 | A measure whose unit-kind would be **null** → an **invalid-input typed refusal**, never silently defaulted. | R-RPT-3, CT-32 nullability, AC19.2 | 19.2 | **P0** |
| R10 | Money measures are **exact scaled integers** at the declared currency scale, never binary float; time measures are **int64 UTC-ns or a typed `duration`**. | R-RPT-4, AR-15, AC19.2 | 19.2 | P1 |
| R11 | Each metric's arithmetic is pinned by its own **`metric_contract_format_version`**; an arithmetic change is a **format-version mint** with before/after evidence, never a silent code change. | R-RPT-5, CT-32 inv.9, AC19.2 | 19.2 | P1 |
| R12 | An **uncomputable metric** (fewer than 2 daily samples; profit factor with no losing trades) → a typed **"undefined / insufficient-sample" refusal** a reader can tell apart from zero — never a magic cap of 10, never NaN coerced to 0. | R-RPT-3, AC19.2 | 19.2 | P1 |
| R13 | **No single composite score, grade, tier band, or weighted rating** appears anywhere in the artifact — the set is never collapsed into one number; producing the artifact **sizes/promotes/benches nothing and changes no mode**. **(verdict never stored)** | R-RPT-10, R-RPT-9, B-10, DEC-0162, AC19.2 | 19.2 | **P0** |
| R14 | Suppression tally keyed by **(authority, reason)** + veto tally keyed by **door**, derived **only from the run's own CT-13 journal streams** — never a parallel bespoke log. | R-RPT-8, B-10, B-4, AC19.3 | 19.3 | P1 |
| R15 | A run with **no suppression and no veto** emits **explicit zero-count keys** — keys are never omitted. | R-RPT-8, CT-32 nullability, AC19.3 | 19.3 | P1 |
| R16 | Each suppression/veto count carries the **`count`** unit-kind, and the two tallies form a **distinct field group** from the returns/trade measures (a control-heavy window is never folded into an alpha figure). | R-RPT-3, R-RPT-8, AC19.3 | 19.3 | P1 |
| R17 | A journal event whose suppression **authority or reason is unresolvable** → a **typed refusal**, never dropped or silently bucketed. | R-RPT-8, AR-13, AC19.3 | 19.3 | P1 |
| R18 | Each chart is a series **`{name, unit_kind, points:[{t,v}]}`**, `t` = int64 UTC-ns, `v` = unit-kinded exact (integer money or exact-rational ratio); **no image/base64/PNG is ever the canonical payload**. | R-RPT-11, R-RPT-12, B-10, AC19.4 | 19.4 | **P0** |
| R19 | **No color, style, or histogram bin** is embedded in the series data — those are renderer concerns. | R-RPT-12, AC19.4 | 19.4 | P1 |
| R20 | Each V1 chart series derives **solely from the run's own ordered position/order/journal record** — not a parallel log that could disagree with the ledger (incl. drawdown top-5 worst-periods `{start, bottom, recovery, max_drawdown}`). | R-RPT-13, R-RPT-14, AC19.4 | 19.4 | P1 |
| R21 | A single-instrument, unleveraged run **omits** holdings/exposure/allocation/leverage series (never empty or faked); a multi-instrument/leveraged run reconstructs them from the same ordered stream. | R-RPT-13, R-RPT-14, AC19.4 | 19.4 | P1 |
| R22 | Benchmark-relative series are **omitted with an explicit "no benchmark declared" note** when none is declared (never faked); when present, the benchmark identity is recorded in the artifact. | R-RPT-15, AC19.4 | 19.4 | P1 |
| R23 | A dense-series **display downsample** is a display-only derivative carrying its **own declared sampler identity**, **AD-10-excluded from identity**, never the canonical payload. | CT-32 QMB-extension inv., AD-10, B-10, AC19.4 | 19.4 | P1 |
| R24 | HTML/markdown rendering is a **pure function of the artifact** — field/token substitution only, adding no computation and deriving no new number. | R-RPT-21, B-10, AC19.5 | 19.5 | **P0** |
| R25 | The rendered **headline shows the world label and account-binding role verbatim and unmissably**, so a replay/paper result is never mistaken for a live one. | R-RPT-2, R-RPT-19, AC19.5 | 19.5 | **P0** |
| R26 | In-house interpretation skills **read the CT-32 artifact, never a rendering** — agents never parse HTML. | R-RPT-22, B-10, AC19.5 | 19.5 | P1 |
| R27 | Re-executing a stored run id under its resolved run-config and recomputing the CT-32 fingerprint **reproduces the stored fingerprint exactly, or the verify returns a typed refusal** — a mismatch is never silently tolerated. | CT-32 reproducibility inv., B-10, NFR-03, AC19.5 | 19.5 | **P0** |
| R28 | Artifact production is **per-run isolated**; 12–14 concurrent runs each save their own artifact with **no shared mutable render state and no cross-run contention**. | R-RPT-24, B-5, AC19.5 | 19.5 | P1 |
| R29 | Across render + interpret + reproduce, **none has sized, promoted, benched, bound, or changed a mode** — every downstream read is **publish-only**. **(verdict / publish-only)** | R-RPT-9, B-10, DEC-0162, AC19.5 | 19.5 | **P0** |

**P0 set (13):** R1, R2, R4, R5, R6, R8, R9, R13, R18, R24, R25, R27, R29.
**P1 set (16):** R3, R7, R10, R11, R12, R14, R15, R16, R17, R19, R20, R21, R22, R23, R26, R28.

---

## Section 3 — Risk Assessment, Weak Spots & Priority

**Highest-value risk theme.** The CT-32 artifact is the **single source of admission-bar evidence and the analyst's report** (CT-32 invariant 1). A defect here either (a) fabricates a second report that drifts from the evidence, (b) smuggles a stored verdict/score that lets a replay run masquerade as a ruling, (c) corrupts identity so reproduction and cross-door agreement break, or (d) reads a replay/paper result as live. Each is silent and downstream-uncorrectable.

**Three epic-specific gates (the audit's centre of gravity):**

1. **CT-32 is ADOPTED, not reinvented (R1).** Exactly one CT-32 container; no bespoke report JSON. The artifact *is* the CT-32 the contract minted — same fields, same invariants, same enums. A parallel container is the defect the whole epic exists to prevent. **P0.**
2. **Verdicts are reader-derived — never stored (R13, R29, and the negative of the B-4 fold).** No composite score/grade/tier/weighted rating anywhere; producing/rendering/interpreting/reproducing acts on nothing; the artifact carries per-requirement *inputs* only. `not-yet-ruled` and the fold live downstream (qmb.md B-4). **P0.**
3. **Identity integrity + replay-never-gates-live (R4, R6, R25, R27, R7).** `fp1` label-derived via qmf-core only, no float bytes; world stamped from provenance not a flag; headline shows world/role verbatim; re-run reproduces or refuses; the `optimistic` taint makes the artifact non-edge-claiming. Together these guarantee a replay/pre-GAP-0048 result can never be read as, or gate, live money. **P0.**

**Named weak spots (to confirm against the module inventory at execution — module *names* only known now):**

| Locus | Risk implication | Mitigation in this plan |
|---|---|---|
| `results/ct32.py` (assembly + label + `fp1`) | The single point where the container is minted; a local `fp1` recompute, a float in identity, a second report container, or a stored verdict all live here. | §4 group A (R1/R2/R4/R5/R6/R7) + static gates S1/S2. |
| `results/measures.py` (measure set) | Null unit-kind defaulting, binary-float money, a magic-cap-of-10 or NaN→0, or a composite score. | §4 group B (R8–R13) + unit gates U1/U2/U3. |
| `results/accounting.py` (suppression/veto) | Reading a parallel log instead of the CT-13 journal; omitting zero keys; silently bucketing an unresolvable event. | §4 group C (R14–R17). |
| `results/charts.py` (series) | An image/base64 canonical payload; color/bins in data; a parallel log diverging from the ledger; faked benchmark/exposure series; a downsample leaking into identity. | §4 group D (R18–R23) + unit gate U4. |
| `results/render.py`, `results/interpret.py` (downstream) | A renderer that computes a new number; an interpretation skill parsing HTML; a downstream read that sizes/promotes/benches/binds; render state shared across concurrent runs. | §4 group E (R24–R29) + static gate S3. |

**Priority ladder:** P0 blocks the epic on any failure; P1 is high (evidence honesty); the L6 review is advisory (its confirmed findings become regression pins).

---

## Section 4 — Independent Test List (authored from requirements, BEFORE any src read)

> **Discipline statement.** This section was written having read **zero source files** under `qmb/src/qmb/results/` — only the directory's file *names* are known (from a listing, not a read). Every test below asserts what a **requirement** demands, derived from epics.md Epic 19, CT-32, qmb.md B-4/B-10, spec-reports R-RPT-*, and SCN-0012 — never what the code happens to do. A failing test here is a **finding**, not a licence to edit source or weaken the assertion. Test files are planned targets under `qa/tests/epic_19/`. Level assignment follows "one behaviour, one level; lower level wins" (§5). **T3 scope:** L3 acceptance carries the epic; L0/L1/L2 are deliberately minimal; one L4 scenario; one L5 concurrency test; one L6 review; regression pins reserved (one per confirmed advisory finding).

### Group S — Static / structural gates (L0)
- **T19-S1** *(L0)* No module in `results/` recomputes identity: static scan finds **no local sha256/hashing of measures or labels** — the only `fp1` computation is a call into qmf-core's canonical function. **[R4]**
- **T19-S2** *(L0)* No composite-score surface: static scan of the artifact schema/assembly finds **no `score` / `grade` / `tier` / `rating` / `weighted` field or symbol** that collapses the measure set. **[R13]**
- **T19-S3** *(L0)* Publish-only + isolation, structural: `results/` writes **no ledger line and no log**, holds **no module-global mutable state**, and spawns no thread. **[R29, R28]**

### Group U — Minimal unit laws (L1) — only where L3 cannot reach the law
- **T19-U1** *(L1)* A money measure round-trips as an **exact scaled integer** at the declared currency scale; a value that would require binary-float representation is refused, not silently coerced. **[R10]**
- **T19-U2** *(L1)* The undefined-metric path — profit factor with **no losing trades**, Sharpe with **< 2 daily samples** — returns a typed **"undefined / insufficient-sample"** refusal distinguishable from zero; **never** a cap of 10, **never** NaN→0. **[R12]**
- **T19-U3** *(L1)* A measure assembled with a **null unit-kind** returns an **invalid-input** typed refusal — no default is applied. **[R9]**
- **T19-U4** *(L1)* A chart series point is exactly `{t: int64-UTC-ns, v: unit-kinded exact}`; **no `color`, `style`, or `bin` key** is present in the data. **[R18, R19]**

### Group C0 — CT-32 adoption & refusal shape (L2)
- **T19-C1** *(L2)* The assembled artifact **is a valid CT-32 performance-result**: all mandatory CT-32 fields present (`result_label`, `population`, `period`, `measure_set`, `suppression_accounting`, `veto_accounting`); it is the CT-32 kind, **not a bespoke report container**; exactly **one** artifact, **no** second report JSON. **[R1]** — *CT-32 ADOPTED not reinvented.*
- **T19-C2** *(L2)* Every emitted quantity across `measure_set` + suppression/veto carries a **non-null AD-40 unit-kind**; suppression/veto counts carry the **`count`** unit-kind and default to **explicit zero**. **[R8, R15, R16]**
- **T19-C3** *(L2)* Every refusal on an Epic-19 path is a valid **CT-04** typed value (category ∈ {policy rejection, invalid input, unavailable dependency} as CT-32 declares), machine-readable context present, **RETURNED not raised**. **[cross-cutting]**

### Group A — Canonical CT-32 artifact & label (Story 19.1) → R1–R7 (L3 acceptance)
- **T19-A1** *(L3)* Given a completed replay run's pure return, `results/` assembly writes **exactly one** CT-32 container into the run's output directory and returns its `fp1`; **no separate report JSON** is produced. **[R1] P0**
- **T19-A2** *(L3)* The container carries the **full AD-12 label** (producer identity + integer format version, input fingerprints, evidence time range, occurrence identity, evidence class, world, account-binding role); the **evidence time range is the trading interval only, never the warm-up interval**. **[R2] P0**
- **T19-A3** *(L3)* The label additionally carries resolved-config `fp1` (run-id root), `registry_as_of`, data/split fingerprints, fidelity identity, and RNG provenance where the run is stochastic. **[R3] P1**
- **T19-A4** *(L3)* The artifact's `fp1` is computed **only** via qmf-core's canonical `fp1:sha256`; recomputing over the same label reproduces it; identity is **label-derived (AD-10)** and **no float bytes** enter it (a float-bytes injection into identity is absent/rejected). **[R4] P0**
- **T19-A5** *(L3)* A run whose result would span **> 1 account-binding role** → a typed **policy-rejection**, and **no artifact is written**. **[R5] P0**
- **T19-A6** *(L3)* `world` is stamped from the run's **data-derived provenance** (a flag attempting to declare world is ignored/refused); a replay run stamps `world=replay`; **no `world=simulated` artifact is producible here** (store-tainted runs refuse upstream). **[R6] P0**
- **T19-A7** *(L3)* Fidelity identity = adapter-id + composition-version + **`optimistic` taint**; the artifact is **non-edge-claiming** — it carries no verdict-bearing claim, and a downstream attempt to **spend split budget or claim edge** on it is refused (pre-GAP-0048). **[R7] P1**

### Group B — The measure set (Story 19.2) → R8–R13 (L3 acceptance)
- **T19-A8** *(L3)* The `measure_set` is **ordered** and every measure carries a **non-null AD-40 unit-kind** across the V1 core set (net profit, CAGR, start/end equity, Sharpe, Sortino, Calmar, max drawdown + recovery, total/winning/losing counts, win rate + long/short split, profit factor, expectancy, avg/largest win & loss, gross profit/loss, fees, streaks). **[R8] P0**
- **T19-A9** *(L3)* Each metric carries its own **`metric_contract_format_version`** pinning its arithmetic; two artifacts computed under **different** metric format versions for the same metric differ in that metric's identity (an arithmetic change is a mint, not silent). **[R11] P1**
- **T19-A10** *(L3)* **No** composite score/grade/tier band/weighted rating appears **anywhere** in the artifact; the artifact presents the measure set and **never collapses it**; assembling it **sizes/promotes/benches nothing and changes no mode**. **[R13] P0** — *verdict never stored.*

### Group D — Suppression & veto accounting (Story 19.3) → R14–R17 (L3 acceptance)
- **T19-A11** *(L3)* Suppression tally keyed by **(authority, reason)** and veto tally keyed by **door** are derived **only from the run's own CT-13 journal streams**; a divergent parallel log does not move the tally, and a tally entry not backed by a journal event is impossible. **[R14] P1**
- **T19-A12** *(L3)* A run with **no suppression and no veto** emits **explicit zero-count keys** — keys are never omitted. **[R15] P1**
- **T19-A13** *(L3)* Suppression/veto counts carry the **`count`** unit-kind and form a **distinct field group** from the returns/trade measures. **[R16] P1**
- **T19-A14** *(L3)* A journal event whose suppression **authority/reason is unresolvable** → a **typed refusal** from the tally builder; the event is **neither dropped nor silently bucketed**. **[R17] P1**

### Group E — Charts as data (Story 19.4) → R18–R23 (L3 acceptance)
- **T19-A15** *(L3)* Each chart is emitted as a series **`{name, unit_kind, points:[{t,v}]}`**, `t` = int64 UTC-ns, `v` unit-kinded exact; **no image/base64/PNG is ever the canonical payload**. **[R18] P0**
- **T19-A16** *(L3)* Each V1 chart series (equity curve, cumulative returns, drawdown/underwater + **top-5 worst-periods** `{start, bottom, recovery, max_drawdown}`, monthly-returns grid, monthly-return & trade-P&L histogram-ready arrays) derives **solely from the run's own ordered position/order/journal record**; a divergent parallel log does not produce a divergent series. **[R20] P1**
- **T19-A17** *(L3)* A **single-instrument, unleveraged** run **omits** holdings/exposure/allocation/leverage series (no empty/faked series); a **multi-instrument/leveraged** run reconstructs them from the same ordered stream. **[R21] P1**
- **T19-A18** *(L3)* With **no benchmark declared**, benchmark-relative series are **omitted with an explicit "no benchmark declared" note** (never faked); with a benchmark present, its **identity is recorded** in the artifact. **[R22] P1**
- **T19-A19** *(L3)* A **display downsample** of a dense series is a display-only derivative carrying its **own declared sampler identity**, **AD-10-excluded** from identity (adding/removing/altering it does **not** move the artifact `fp1`), never the canonical payload. **[R23] P1**

### Group F — Pure downstream reads (Story 19.5) → R24–R29 (L3 acceptance)
- **T19-A20** *(L3)* The HTML and markdown renderers are **pure functions of the artifact** — field/token substitution only; a renderer that computes a new number is a finding; rendering the same artifact twice is **byte-stable**. **[R24] P0**
- **T19-A21** *(L3)* The rendered **headline shows the world label and account-binding role verbatim and unmissably** (a replay/paper result cannot be read as live). **[R25] P0**
- **T19-A22** *(L3)* Interpretation skills (the `interpret` path) read the **CT-32 artifact, never a rendering**; given only the HTML they have no path to a number, and given the artifact they **re-derive nothing**. **[R26] P1**
- **T19-A23** *(L3)* Re-executing a stored run id under its resolved run-config and recomputing the CT-32 fingerprint **reproduces the stored fingerprint exactly, OR the verify returns a typed refusal** on mismatch — a mismatch is **never silently tolerated**. **[R27] P0** *(co-anchored with E14 / SCN-0012)*
- **T19-A24** *(L3)* Across **render + interpret + reproduce**, none has **sized/promoted/benched/bound/changed a mode** — every downstream read is **publish-only** (assert no call into the sizing/promotion/bench/bind/mode surfaces). **[R29] P0** — *verdict / publish-only.*

### Group G — Golden scenario (L4) — R-016, co-owned with Epic 14
- **T19-SCN** *(L4)* **SCN-0012 step (7) tail.** Drive the golden replay run's pure `run()` return (from Epic 14's loop fixture) through `results/` assembly and assert: exactly one CT-32 artifact with `world=replay`, `optimistic` taint, and the full AD-12 label; that the artifact carries the raw AD-40 unit-kinded measures the Epic-15 ledger line will cite; and that **step (8)'s verdict is NOT present in the artifact** (reader-derived, downstream). **[R-016]** *The loop half (steps 5–6) is Epic 14's; this test owns only the CT-32-production tail and its boundary with the reader-derived fold.*

### Group H — Concurrency isolation (L5) — T3-light, one test
- **T19-SYS** *(L5)* **12–14 concurrent** assembly tasks each write their own artifact into their own output directory with **no shared mutable render state** and **no cross-run contention**; the artifacts are independent and each `fp1` is stable. **[R28]** *(the process-per-run half is Epic 15; here only the library's render/assembly purity under concurrency.)*

### Group R — Adversarial review (L6) + regression pins
- **T19-REV** *(L6)* Run **`bmad-code-review`** over `qmb/src/qmb/results/` (`ct32.py`, `measures.py`, `accounting.py`, `charts.py`, `render.py`, `interpret.py`) against Epic 19 ACs + CT-32 invariants + the four load-bearing laws: **no stored verdict / no composite score**, **float-identity ban**, **provenance-derived world**, **publish-only**. Advisory findings are recorded in `findings.csv`.
- **T19-PIN-\*** *(L1/L2/L3, reserved)* **One regression pin per *confirmed* advisory finding** (from T19-REV) or per failing acceptance test — a minimal test that locks the corrected behaviour against regression. **Zero at authoring; populated at execution.**

---

## Section 5 — Test-Level Architecture Mapping (L0–L6)

> Reconstructed taxonomy (test-design-qa.md absent), using the **level scheme the T3 brief supplies**: L3 acceptance carries the epic; L4 is the cross-epic golden scenario; L6 is the adversarial review. Rule enforced: **one behaviour, one level; the lowest level that meaningfully asserts it wins.**

| Level | Meaning here | Execution band | Epic-19 population | Count |
|---|---|---|---|---|
| **L0** | Static / structural gates (identity-recompute scan, composite-score scan, publish-only/no-global-state). | tier-1 lint/type | T19-S1, S2, S3 | **3** |
| **L1** | Minimal pure-unit laws not reachable at L3 (exact money, undefined-metric refusal, null unit-kind, series-point shape). | tier-1 (`poe check`) | T19-U1..U4 | **4** |
| **L2** | Contract adoption + refusal shape (the artifact IS CT-32; AD-40 unit-kinds; CT-04 refusals). | tier-2 (`poe check-integration`) | T19-C1, C2, C3 | **3** |
| **L3** | **Acceptance — the T3 core**: one test per P0/P1 AC across Stories 19.1–19.5. | tier-2 | T19-A1..A24 | **24** |
| **L4** | Golden scenario — SCN-0012 step (7) tail, **co-owned with Epic 14** (R-016). | tier-2 | T19-SCN | **1** |
| **L5** | System — concurrency isolation of assembly/render (library half; process half = Epic 15). | tier-2/system | T19-SYS | **1** |
| **L6** | Adversarial review (`bmad-code-review`) + reserved regression pins. | review | T19-REV (+ T19-PIN-\* reserved) | **1** (+N pins) |

**Planned counts — L0: 3 · L1: 4 · L2: 3 · L3: 24 · L4: 1 · L5: 1 · L6: 1 review.** Executable total **36 tests + 1 review + N regression pins** (N = confirmed advisory findings, 0 at authoring).

**Lower-level-wins applications:**
- The float-identity ban is caught **statically** (S1) *and* asserted **behaviourally once** (A4); these are two facets (no local recompute vs. label-derived reproduction), not a duplication.
- The measure-set unit-kind law sits at **L2** (C2, structural over all quantities); A8 at L3 adds the *ordering* + *V1-core-set* acceptance the contract test does not enumerate.
- No-composite-score is a **static** scan (S2) plus an **acceptance** assertion (A10) that the assembled artifact over a real run carries none — the negative is proven both structurally and behaviourally because it is the epic's centre of gravity.
- Reproduction (A23) is asserted **once** at L3 and **participates** in the L4 scenario; it is not re-run as a separate property.

---

## Section 6 — Fixtures, Data & Determinism Strategy

**Runner.** `uv run pytest qa/tests/epic_19 -q` from the worktree root (dev group synced); tier-2 acceptance via the project's `poe check-integration` band. If `hypothesis` is used for any pin, `uv run --with hypothesis ...`. **All tests live under `qa/`; source is read-only evidence.** A failing test is a **finding recorded in `qa/epics/epic_19_qmb-reports/findings.csv`**, never a reason to edit `results/` source or soften an assertion.

**Fixtures (controlled test fixtures permitted under L6/DEC-0007; no product mock data, no default strategies):**
- **A completed-run pure-return fixture** — a small, deterministic `run()` return (positions/fills, CT-13 journal streams incl. control-window suppressions + door vetoes, an embargo/warm-up boundary, a resolved-config `fp1`, a `world=replay` binding, an `optimistic`-tainted fidelity identity) sufficient to assemble a full CT-32 artifact and drive all five stories. Checked into `qa/`, never sourced from a provider (B-11). **Shared with Epic 14's golden-slice fixture** for T19-SCN so the loop return and the artifact agree by construction.
- **Variants:** a multi-account-role return (T19-A5); a store-tainted return (T19-A6 negative); a single-instrument/unleveraged vs. multi-instrument/leveraged return (T19-A17); a no-benchmark vs. benchmark-declared config (T19-A18); a no-suppression/no-veto run (T19-A12); an unresolvable-authority journal event (T19-A14); a no-losing-trades / <2-sample run (T19-U2).
- **CT-32 / CT-04 / CT-13 fakes are shape-faithful** to the ratified contracts (fields, unit-kinds, refusal categories) — a test that passes against a shape-unfaithful fake is itself a finding.

**Determinism & discipline strategy:**
1. **Identity is label-derived, computed once.** A4 + S1 prove `fp1` comes only from qmf-core's canonical function and no float byte enters identity; A19 proves a display downsample is AD-10-excluded (perturbing it does not move `fp1`); A23 proves re-run reproduces or refuses.
2. **No verdict, no score — proven twice.** S2 (static) + A10 (behavioural) prove the artifact never carries a composite/verdict; A24 proves downstream reads act on nothing. The reader-derived fold is **out of scope** (§7) — Epic 19 asserts only its inputs and the stored-verdict *absence*.
3. **Exactness.** U1 (money = scaled integer), U3 (null unit-kind refused), U2 (undefined ≠ zero, no cap-of-10, no NaN→0), U4 (series-point shape) hold the QMF exact-arithmetic and honest-blank laws.
4. **Refusals are RETURNED, not raised.** Every "is refused" assertion (A5, A6, A7, A14, U2, U3, C3) checks a **returned** CT-04 typed value with the correct category — never a raised exception across a public boundary.
5. **Values are referenced, never invented.** SCN-0012 explicitly pins "no fixture number to freeze"; the plan asserts unit-kind, exactness, identity, and refusal **structure**, not the numeric value of any metric against an invented oracle (see §7).

---

## Section 7 — Coverage, T3 Scoping & Untestable / Deferred / Boundary

**T3 posture.** Coverage is a floor and a map, not the goal. Because this is **T3**, the plan does **not** build exhaustive L1/L2 or property/branch suites; it targets **acceptance of every P0/P1 AC (L3)**, one **L4** scenario, one **L5** concurrency test, and one **L6** review, with **regression pins** added only for *confirmed* advisory findings. Coverage of `results/` is recorded and reported, but the gate is **assertion completeness over the P0/P1 ACs**, not a line-percentage.

**Exit gate for the epic (see §8), in brief:** every P0 test green; every P1 test green or a recorded finding; the three §3 gates satisfied; T19-REV run and each confirmed finding pinned.

**Untestable / deferred / out-of-Epic-19 (findings and boundaries, not omissions):**

- **7.1 — The read-time verdict fold is NOT built in Epic 19.** The per-requirement outcomes, `not-yet-ruled`, re-verdict-on-ruling, the canonical-assignment qualifier, and the replay-never-gates-live **enforcement** are owned by the Book-bar / admission reader (qmb.md B-4 §77-81), downstream of the Epic-15 ledger. Epic 19 asserts only (a) the artifact **stores no verdict** (A10, S2), (b) it carries the **per-requirement inputs** the fold consumes (A2/A3/A8/A9/A11/A7), and (c) downstream reads **act on nothing** (A24). The fold's own behaviour is tested where it is built, not here.

- **7.2 — The ledger line (`R-RPT-16/17/18/20`) is Epic 15.** "Exactly one ledger line per run" and its content are Epic 15's. **Documented tension:** spec-reports `R-RPT-17` says the ledger stores one structural pass/fail line, but ratified **DEC-0162 / CT-32 (L33) / qmb.md B-4** say a verdict is **never stored** — the ratified corpus governs. Epic 19 tests the never-stored discipline (A10) and flags this spec-vs-decision conflict for the Epic-15 auditor. Not resolved here; recorded.

- **7.3 — Metric *numeric* correctness is not asserted against an invented oracle.** Epic 19 pins each measure's **unit-kind, exactness, format-version pinning, and refusal discipline** (A8/A9/A10/U1/U2/U3), **not** the numeric value of any Sharpe/Sortino/Calmar against an external oracle. SCN-0012 states "no fixture number to freeze," and L6/DEC-0007 forbids product mock data. The *arithmetic* of each metric is its own governed producer contract (R-RPT-5) — its numeric correctness is a per-metric contract concern, tested where the metric contract is ratified, not by a fabricated golden number here.

- **7.4 — GAP-0048 fidelity content.** Whether a fill is *correctly* modeled (fidelity taxonomy values, forex calibration, `world=simulated` unlock) is decided-deferred (Epic 17 / GAP-0048). Epic 19 stamps the `optimistic` taint and the **non-edge-claiming** property (A7) only; fidelity correctness is untestable now and asserting it would test an unratified value.

- **7.5 — Benchmark-relative *math* (alpha/beta/info-ratio/tracking-error) is extended-tier and benchmark-gated.** Testable now: **omitted-with-note when no benchmark, identity-recorded when present** (A18). The math itself, when a benchmark is present, is extended tier beyond the V1 core set — partial; not gated in this T3 pass.

- **7.6 — Extended-tier metrics/charts** (rolling windows, MAE/MFE, turnover, probabilistic Sharpe, Omega/Serenity/Ulcer) appear only if config declares them (R-RPT-23) — presence is config-driven, not gated here; the V1 core set (A8) is the acceptance target.

- **7.7 — PLAN-INTEGRITY CAVEAT.** `test-design-qa.md` and `QMX-handoff.md` are absent (§Process Gap). The 8-section template, the L0–L6 mapping, and the P0/P1 split are reconstructed from the ratified corpus and the T3 brief; `R-016` is taken from the brief as "L4 scenario participation with E14." Reconcile when restored. Recorded as a finding, not worked around.

---

## Section 8 — Execution, Traceability Matrix & Exit Criteria

**Execution.** Run from the worktree root: `uv run pytest qa/tests/epic_19 -q` (L0/L1 tier-1); the `poe check-integration` band for L2/L3/L4/L5; `bmad-code-review` for L6. All tests under `qa/`; source read-only. A failing test → a row in `qa/epics/epic_19_qmb-reports/findings.csv`, never a source edit.

**Traceability (requirement → test → priority → level → status). Every R1–R29 maps to ≥1 test.**

| Req | Test IDs | Prio | Level(s) | Status |
|---|---|---|---|---|
| R1 | T19-C1, T19-A1 | P0 | L2,L3 | planned |
| R2 | T19-A2 | P0 | L3 | planned |
| R3 | T19-A3 | P1 | L3 | planned |
| R4 | T19-S1, T19-A4 | P0 | L0,L3 | planned |
| R5 | T19-A5 | P0 | L3 | planned |
| R6 | T19-A6 | P0 | L3 | planned |
| R7 | T19-A7 | P1 | L3 | planned |
| R8 | T19-C2, T19-A8 | P0 | L2,L3 | planned |
| R9 | T19-U3 | P0 | L1 | planned |
| R10 | T19-U1 | P1 | L1 | planned |
| R11 | T19-A9 | P1 | L3 | planned |
| R12 | T19-U2 | P1 | L1 | planned |
| R13 | T19-S2, T19-A10 | P0 | L0,L3 | planned |
| R14 | T19-A11 | P1 | L3 | planned |
| R15 | T19-C2, T19-A12 | P1 | L2,L3 | planned |
| R16 | T19-A13 | P1 | L3 | planned |
| R17 | T19-A14 | P1 | L3 | planned |
| R18 | T19-U4, T19-A15 | P0 | L1,L3 | planned |
| R19 | T19-U4 | P1 | L1 | planned |
| R20 | T19-A16 | P1 | L3 | planned |
| R21 | T19-A17 | P1 | L3 | planned |
| R22 | T19-A18 | P1 | L3 | planned |
| R23 | T19-A19 | P1 | L3 | planned |
| R24 | T19-A20 | P0 | L3 | planned |
| R25 | T19-A21 | P0 | L3 | planned |
| R26 | T19-A22 | P1 | L3 | planned |
| R27 | T19-A23 | P0 | L3 | planned (co-anchored E14/SCN-0012) |
| R28 | T19-S3, T19-SYS | P1 | L0,L5 | planned |
| R29 | T19-S3, T19-A24 | P0 | L0,L3 | planned |
| R-016 | T19-SCN | — | L4 | planned (co-owned with Epic 14) |
| cross | T19-C3 | — | L2 | planned |
| review | T19-REV (+ T19-PIN-\*) | — | L6 | planned |

**Exit criteria (Epic 19 passes audit when):**
1. Every **P0** test (R1, R2, R4, R5, R6, R8, R9, R13, R18, R24, R25, R27, R29) is green.
2. Every **P1** test is green **or** has a recorded finding with an owner.
3. The three §3 gates hold: **(a)** CT-32 adopted-not-reinvented (C1/A1 — one CT-32, no report JSON); **(b)** verdict never stored (S2/A10) + publish-only (S3/A24); **(c)** identity integrity + replay-never-gates-live (S1/A4/A6/A21/A7/A23).
4. **T19-SCN** (L4, R-016) passes against the Epic-14-shared golden fixture, and it confirms the verdict is **absent** from the artifact.
5. **T19-REV** (L6) has run; **each confirmed advisory finding has a regression pin** (T19-PIN-\*) locking the corrected behaviour; unconfirmed findings are recorded, not pinned.
6. Every **§7 boundary/deferred item** is explicitly recorded with its owning epic — none silently counted as passed or failed. In particular the **read-time verdict fold** (§7.1), the **ledger line + R-RPT-17 tension** (§7.2), and **metric numeric correctness** (§7.3) are logged as out-of-Epic-19, not as coverage gaps.

Coverage ledger maintained alongside execution in `qa/epics/epic_19_qmb-reports/` — one row per §4 test id → {level, status PASS/FINDING/DEFERRED, evidence path}.
