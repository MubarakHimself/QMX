# Epic 22 — QMB robustness ladder — Verification PLAN (audit tier T3)

> Per-epic verification plan. Eight sections, order load-bearing. **Section 4 (the
> independent test list) was authored entirely from requirements BEFORE any file
> under `qmb/src/qmb/robustness/` was opened.** As of authoring, zero source files
> of this epic's package have been read; the whole plan is requirement-derived from
> epics.md, the QMB spine, the contracts, and the constitution. Test file paths named
> below are planned targets under `qa/` to be created at execution time. A failing
> test is a FINDING; source is read-only evidence, never edited to make a test pass.

---

## 1. Epic under test and authorities

- **Epic:** 22 — QMB robustness ladder. **Wave 7, priority M** (serial after Epic 21, per epics.md wave table). **Audit tier: T3.**
- **Package under test:** `qmb/src/qmb/robustness/` — the B-14 validation-ladder module inside the single `qmb` wheel (the `robustness/` node of the Epic 13 structural seed: "MC, significance, walk-forward (B-14)"). Seams consumed (not owned here): `qmb/.../runloop/` (the B-2 event-slice loop, Epic 14), `qmb/.../orchestrator/` + `ledger/` (Epic 15), `qmb/.../results/` (CT-32 artifact, Epic 14/19), `qmb/.../registryread/` (B-15 port, Epic 13), and qmf-data split governance (Epic 3).
- **What this epic delivers (scope of verification):** the B-14 ladder as **pure QMB library functions** — Story 22.1 the module foundation (versioned statistical-procedure contract, the return-space float carve-out, the shared distribution-summary primitive); 22.2 Monte Carlo trade-shuffle; 22.3 Monte Carlo candle-perturbation; 22.4 the pre-build rule-significance gate; 22.5 walk-forward as a sequence of split-manifest runs. **Interfaces ship now; every threshold value and pass battery stays deferred** to GAP-0048/0049 (SC-07) and appears only as a UI-editable configurable with no ratified value. Every procedure runs on optimistic-tainted evidence under the GAP-0048 seam (SC-06): outputs claim robustness or infra-stress and **never edge** (L20), and none can gate live money.
- **T3 tier scope (what this pass covers, and only this):**
  1. **L3 (contract / acceptance conformance) tests for every P0 and P1 acceptance criterion** of Epic 22 (§4.3).
  2. **Regression pins per confirmed advisory finding** — the OverflowError→typed-refusal pin (F-22-01, pins P0 assertion 3) and the FAILURES.md-not-extended verification (F-22-02) (§4.4).
  3. **An L6 independent review** of the module against the B-14 spine and the L20/SC-06/SC-07 firewalls (§4.5, delivered as `L6-REVIEW.md`).
  The full L0/L1/L2/L4/L5 independent suite (pure-unit statistic math, hypothesis properties, mutation sensitivity, end-to-end governed run) is the **T1** treatment and is **out of scope for this T3 pass** — recorded as deferred-by-tier in §7, not as a requirement gap. Rationale: Epic 22 is Wave-7 weight-M, its thresholds are deferred, it is GAP-0048-gated, and no output can gate live money — a materially lower blast radius than the T1 identity/determinism epics.

**Authorities consulted (precedence order):**
1. `_bmad-output/planning-artifacts/epics.md` — Epic 22 (stories 22.1–22.5, lines 4275–4469), and the FR map (FR-040 → Epic 22, line 297).
2. `docs/` knowledge base: `docs/constitution.md` (L20 synthetic-never-edge / DEC-0054; L38 configurable = UI-editable / DEC-0157; L27 executable-contract / DEC-0096); contracts `ct-04-typed-refusal` (returned not raised, seven categories), `ct-29-exit-record` (the CT-29 trade stream), `ct-32-performance-result` (result label + chart-series data, label-derived float identity), `ct-05-version-fingerprint` (`fp1`, floats refused in identity), `ct-12-dataset-split` (split manifest); `docs/lenses/testing/test-strategy.md` (`LENS-TEST-STRATEGY`, the ratified quality-tier and test-level authority); `conventions/failure-register.md` (NFR-11 failure-register obligation).
3. `_bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md` — **B-14** (the validation ladder as library functions; the return-space float carve-out), B-4 (pure `run()` returns), B-5 (governor), B-7 (world derived from provenance), B-10 (reproduction), B-12 (read-time aggregation), B-15 (registry-read port); and the QMX spine (`architecture-QMX-2026-08-19`) for AD-5 (integer format version), AD-7 (exact money), AD-22 (the two named exact↔analytic conversion boundaries), AD-41 (label-derived identity), AD-21 (split-manifest embargo).
4. **MISSING AUTHORITIES (plan-integrity caveat, see §7.8):** the task named `_bmad-output/test-artifacts/test-design-qa.md` (Per-Epic Test Plan Template + the L0–L6 architecture) and `_bmad-output/test-artifacts/test-design/QMX-handoff.md` (the 15 P0/P1 assertions + this epic's risk-gate rows). **Neither exists in this worktree** (`_bmad-output/test-artifacts/` is absent; confirmed by full-tree search). The 8-section template and the L0–L6 scheme below are reconstructed from the ratified `LENS-TEST-STRATEGY` tier structure and the sibling QMB plan (`qa/epics/epic_13_qmb-substrate/PLAN.md`); the T3 tier scope, **risk gate R-001**, and **P0 assertion 3** are taken verbatim from the task brief. The audit convention **L6 = independent review** is inferred from every sibling epic dir shipping an `L6-REVIEW.md`.

---

## 2. Requirements inventory and traceability

Every P0/P1 acceptance criterion of Epic 22, keyed to the independent test(s) in §4. (`Ref` cites the governing AC / spine / contract / law.) Priority is derived (§1.4 caveat): **P0** = the L20 edge-firewall, the money-path float carve-out, the world/persistence refusal seams, the anti-look-ahead guarantee, and the no-verdict-while-GAP-open rules — the properties whose violation lets the ladder fabricate or launder edge. **P1** = evidence honesty, reproducibility, and configurable discipline. **P2** = Epic-15/14-owned orchestration surfaced only as a seam here (§7).

| Story | AC (abbreviated) | Ref | Prio | Test id(s) |
|---|---|---|---|---|
| 22.1 | Each ladder procedure is a pure B-4 function: consumes resolved config + data reads, RETURNS its result, writes no log and no ledger line | B-4 | P1 | T22-301 |
| 22.1 | Module declares a versioned statistical-procedure contract stamping AD-5 integer format version (v1); old ledger entries stay readable forever | AD-5, CT-05 | P1 | T22-302 |
| 22.1 | No module-global mutable state anywhere in the module | NFR-02, B-4 | P1 | T22-301 |
| 22.1 | **Return-space float carve-out:** P&L and equity paths stay exact scaled integers; floats exist only inside the statistic under a fixed declared rounding contract; any re-entry to the money path passes a named AD-22 conversion with a declared rounding mode | **B-14, AD-7, AD-22** | **P0** | **T22-303** |
| 22.1 | A binary float on the money path is a taint (FR-001), catchable by the tier-1 money-path float scanner (NFR-02) | FR-001, NFR-02 | **P0** | **T22-304** |
| 22.1 | A float-valued measure takes label-derived identity per AD-41, never float bit-identity; identical inputs → identical measure identity | AD-41, NFR-03 | P1 | T22-305 |
| 22.1 | Distribution-summary primitive: (simulated distribution, observed value, declared direction) → percentile ranks + confidence bands + empirical one-tailed p-value (fraction at/beyond observed in the declared direction) as pure data | FR-040, B-14 | P1 | T22-306 |
| 22.1 | Primitive emits NO pass/fail verdict (α levels, batteries, composition deferred to GAP-0048/0049) | **SC-07, L20** | **P0** | **T22-307** |
| 22.1 | Every threshold / iteration / scenario / block-length / min-observation input is a UI-editable configurable carrying no ratified value; no invented default; an unset required input returns a typed `invalid input` refusal (never a silently-applied number) | **NFR-07/L38, AR-13** | **P0** | **T22-308**, T22-PIN-01 |
| 22.1 | Claim class is robustness/infra-stress, never edge; no output can gate live money or spend split budget while GAP-0048 open | **L20/B-7, SC-06** | **P0** | **T22-309** |
| 22.2 | Trade-shuffle re-orders realised CT-29 trades and re-accumulates the equity path with exact-integer money math | AD-7, CT-29 | P1 | T22-310 |
| 22.2 | Procedure-ephemeral: mints/persists no synthetic market series → run stays `world=replay`; procedure identity + seed enter the label | **B-7** | **P0** | **T22-311** |
| 22.2 | Per-scenario reproducibility: seed = base_seed + scenario_index; label records RNG family, base seed, seed-derivation rule, scenario count, data-window UTC-ns bounds; re-run reproduces the CT-32 fingerprint bit-for-bit or returns a typed refusal | AR-59, B-10, NFR-03 | **P0** | **T22-312** |
| 22.2 | Per metric: percentile ranks + confidence bands + direction-aware empirical percentile rank written into the CT-32 artifact as chart-series DATA (never images); no pass/fail verdict | FR-043, B-10 | P1 | T22-313 |
| 22.2 | Scenario count is a UI-editable configurable with no ratified value; MC-1000 not baked as a default | SC-07 | P1 | T22-314 |
| 22.3 | Moving-block bootstrap of exact-integer OHLC deltas (block length configurable, no ratified value); cumulative-sum onto seed price exact-integer; always a valid strictly-positive OHLC series with high/low bounds enforced; scenario 0 = true history | AD-7, B-14 | **P0** | **T22-315** |
| 22.3 | Procedure-ephemeral: synthetic series never persisted → run stays `world=replay`; procedure identity + seed enter label; claim class robustness-only | B-7 | **P0** | **T22-316** |
| 22.3 | **Persistence refusal seam:** a config requesting persistence → `world=simulated`, typed `policy rejection` for governed evidence, cannot ledger into the bar's store until GAP-0048; a replay clock bound to synthetic-tainted persisted data → typed `invalid input` | **SC-06, B-2/B-7** | **P0** | **T22-317** |
| 22.3 | Per-scenario reproducibility: independent RNG seeded base_seed+scenario_index; label records RNG family, seed derivation, block length, scenario count, resampling scheme, data-window bounds; re-run reproduces the CT-32 fingerprint or refuses | AR-59, B-10 | P1 | T22-318 |
| 22.3 | Summary into CT-32 as data, no verdict; claim class robustness (alternate-history) never edge; cannot gate live money | L20 | P1 | T22-319 |
| 22.4 | Signal-only pass over the B-2 loop with orders disabled (trading locked as in warm-up); strategy stays permanently flat; any minted entry/exit/command during the pass → typed `policy rejection` | **B-2** | **P0** | **T22-320** |
| 22.4 | Next-bar alignment: signal at bar t scored on the NEXT bar's log return (first return not knowable at signal time); no forming-bar/future info enters the statistic; close prices are exact Price integers crossing into the float carve-out only via the named AD-22 conversion | **B-2/SC-06, AD-22** | **P0** | **T22-321** |
| 22.4 | Zero-edge null: returns detrended by in-sample mean AND rule-return series re-centred to zero before resampling (H0: E[return]=0); statistic = empirical one-tailed p-value = fraction of null resamples whose mean ≥ observed mean | B-14 | P1 | T22-322 |
| 22.4 | Insufficient data: observation count below the configured min-observation floor → typed refusal, not a fabricated p-value; unset floor → low-confidence warning label; result records seed provenance, scheme+params, iteration count, data-window bounds; re-run reproduces the null distribution bit-for-bit | **AR-13, AR-59** | **P0** | **T22-323** |
| 22.4 | Resampling scheme UI-editable configurable (`iid`\|`block`\|`stationary`) with configurable block length; iteration count + min-observation floor UI-editable configurables with no ratified value; no invented default | SC-07 | P1 | T22-324 |
| 22.4 | Advisory: result world `replay`\|`simulated` never `live`; claim class robustness never edge; never auto-merges, never gates live money; α thresholds deferred to GAP-0049 | **L20, SC-06** | **P0** | **T22-325** |
| 22.5 | WF is a sequence of split manifests (each knowledge-time/embargo-purge/calendar-in-band); each window a first-class B-3/B-4 run with its own resolved config; "train/test" a display alias for two manifests, never a substitute; reads split-governed at every boundary | AD-21, FR-012 | P1 | T22-326 |
| 22.5 | Train window ledger line `role = trial` (or `replicate`) + objective measure, never a bar verdict; an OOS window's bar outcome is a read-time fold returning `not-yet-ruled` until GAP-0048/0049 | **SC-06, B-4** | **P0** | **T22-327** |
| 22.5 | Batch admission resolves exactly one registry as-of at admission through the single B-15 read port, frozen for every window and stamped into the batch label; after admission fragments resolve by explicit fingerprint, never name@latest | SC-11, B-15 | P1 | T22-328 |
| 22.5 | Window counts / spans / OOS counts UI-editable configurables with no ratified value; no invented default, no baked WF/OOS battery | SC-07 | P1 | T22-329 |
| 22.5 | WF view is a read-time aggregation over the ledger's window runs (never a merged run), written into CT-32 as data; aggregated IS/OOS distributions are the declared feeders for the deferred PBO/CSCV battery (no ratified thresholds) | B-12, SC-07 | P1 | T22-330 |
| 22.5 | Reproducibility: a WF run id re-run under its resolved config reproduces the CT-32 fingerprint or returns a typed refusal; each window's label carries its split-manifest fingerprints, registry_as_of, world, evidence class | AR-59, B-10 | P1 | T22-331 |
| cross | Every refusal on an Epic-22 path is a valid CT-04 typed value, RETURNED not raised (no public boundary raises) | **CT-04, DEC-0109** | **P0** | **T22-PIN-01**, T22-308, T22-317, T22-323 |
| cross | Every designed failure mode above ships an NFR-11 failure-register entry in `qmb/FAILURES.md` | **NFR-11, L27** | P1 | **T22-PIN-02** |

FR/NFR roots: **FR-040** (robustness ladder — interfaces; thresholds deferred), **FR-043** (chart-series data, never images), **NFR-02** (exact money / money-path float scanner / determinism), **NFR-03** (reproducibility of identity), **NFR-07** (UI-editable configurable), **NFR-11** (failure register).

---

## 3. Risk gates and priority assertions

The epic-specific centre of gravity. The robustness ladder's entire safety rests on two firewalls that must never leak, and one confirmed defect that already breaches a third.

**R-001 — return-space float carve-out: money values stay exact integers; floats appear only in the declared return-space statistic (assert the boundary).**
This is the epic's defining risk. B-14 permits floats *only* inside a return-space statistic (mean log-return, Sharpe, Calmar, and kin) under a fixed rounding contract; P&L and equity paths must stay exact scaled integers (AD-7), and any value re-entering the money path must pass a **named AD-22 conversion** with a declared rounding mode + target scale. A float that leaks onto the money path is a taint (FR-001) the tier-1 scanner must catch (NFR-02), and a float-valued measure must take **label-derived** identity (AD-41), never the bit-identity of the float (else identical inputs diverge in identity — NFR-03 broken).
Covered by: **T22-303** (carve-out boundary: equity/P&L exact-integer; float only inside the statistic; re-entry only via AD-22), **T22-304** (money-path float taint caught by the NFR-02 scanner), **T22-305** (label-derived float-measure identity), reinforced at every procedure boundary by **T22-310** (trade-shuffle equity path exact-integer), **T22-315** (candle-perturbation OHLC cumulative-sum exact-integer), **T22-321** (significance-gate close→float only via AD-22).

**P0 assertion 3 — no public boundary raises (every failure is a RETURNED CT-04 typed refusal).**
CT-04 / DEC-0109: public operations return value-or-refusal; exceptions never carry a refusal across a boundary (they are reserved for programmer error). **Confirmed advisory finding F-22-01:** a public boundary of the robustness module raises `OverflowError` instead of returning a typed refusal.
Covered by: **T22-PIN-01** — the regression pin invokes the public boundary with an input in the range that currently triggers the overflow and asserts a **returned CT-04 refusal** (category `invalid input` or the boundary's declared category), never a raised exception. **This pin is expected to FAIL against current source and is recorded as finding F-22-01** — the plan pins the correct behaviour; the failure is the evidence, not a licence to soften the assertion. Reinforced by T22-308 / T22-317 / T22-323 (the other refusal boundaries, which must likewise return, not raise).

**F-22-02 — FAILURES.md not extended (NFR-11 / L27 incomplete-story).**
`conventions/failure-register.md` (NFR-11) makes a failure-register entry a **Tier-1 artifact obligation on every story that delivers a designed failure mode**; a designed failure with no entry is an *incomplete story, the same way a missing test is*. Epic 22 delivers many designed failure modes — the unset-required-input `invalid input` refusal (22.1), the synthetic-persistence `policy rejection` and replay-clock-on-synthetic `invalid input` (22.3), the insufficient-data refusal and low-confidence-warning path (22.4), and the OverflowError→typed-refusal path once fixed. **Verified during authoring:** `qmb/FAILURES.md` (765 lines) carries entries for stories 14.x/15.x/16.x/18.x/19.x but **zero** for Epic 22 (no `robust`/`Monte`/`shuffle`/`perturb`/`significance`/`walk-forward`/`overflow`/`carve` match anywhere in the file).
Covered by: **T22-PIN-02** — a static/doc gate asserting `qmb/FAILURES.md` contains an NFR-11 entry (all six required fields) for each Epic-22 designed failure mode. **Expected to FAIL → records finding F-22-02.**

**L20 edge-firewall (the ladder must never masquerade as edge) and SC-06/SC-07 (nothing gates money while GAP-0048/0049 are open).**
Structurally P0 across the epic, not a single row: robustness/infra-stress claim class only, never edge; no pass/fail verdict emitted; no output gates live money or spends split budget.
Covered by: **T22-307** (primitive emits no verdict), **T22-309** (claim class robustness/infra-stress, no money gating while GAP-0048 open), **T22-317** (persist-synthetic → world=simulated policy rejection), **T22-319 / T22-325** (per-procedure claim-class + advisory-only), **T22-327** (OOS `not-yet-ruled` while GAP open).

---

## 4. Independent test list (authored from requirements before reading src)

> **Discipline statement.** This section was written having read **zero files** under
> `qmb/src/qmb/robustness/`. Every test asserts what a *requirement* demands, derived from
> the Epic 22 ACs, the B-14 spine rule, the CT-* contracts, and the constitution — never
> what the code happens to do. A test that fails is a **FINDING**; source is read-only
> evidence and is never edited to make a test pass, nor is any assertion weakened to pass.
> Per the T3 tier scope, the executed band this pass is **L3 (contract/acceptance for every
> P0/P1 AC) + the regression pins + the L6 review**; the fuller L0/L1/L2/L4/L5 independent
> suite is the T1 treatment, recorded deferred-by-tier in §7. Test targets live under
> `qa/tests/epic_22/`; run via `uv run pytest qa/tests/epic_22 -q` from the worktree root.

### 4.1 (L0/L1/L2/L4/L5 — deferred-by-tier, not authored as executable tests this pass; see §7.7)

Under T3 these levels are **not** populated with an independent suite. The behaviours that would live there in a T1 pass — the pure-unit arithmetic of the distribution-summary primitive (percentile / p-value math), hypothesis properties over the bootstrap and the seed-derivation reproducibility, mutation sensitivity on the carve-out and the refusal guards, and an end-to-end governed run — are named in §7.7 with their owning level, and each P0/P1 *behaviour* they would prove is instead pinned once at L3 below.

### 4.2 (reserved — no L0/L1/L2 tests authored this pass under T3)

### 4.3 Contract / acceptance conformance (L3) — the T3 band, one test per P0/P1 AC

**Story 22.1 — module foundation, float carve-out, distribution-summary primitive**

- **T22-301** *(L3, B-4)* — a ladder procedure invoked with a resolved run-config + data reads **RETURNS** its result and writes **no log and no ledger line** (assert the injected log/ledger sinks are never touched by the library call); and no module-global mutable state exists in the module. *(22.1 AC1/AC3)* **P1**
- **T22-302** *(L3, AD-5/CT-05)* — the module declares a **versioned statistical-procedure contract** stamping its own AD-5 integer format version (v1); a format-N result stays readable after format-(N+1) ships; an unknown format version is an `unsupported capability` refusal, never a best-effort read. *(22.1 AC1)* **P1**
- **T22-303** *(L3, R-001)* — **return-space float carve-out boundary:** for a procedure computing a return-space statistic, P&L and equity paths are **exact scaled integers** (AD-7); a float appears **only inside the statistic** under a fixed declared rounding contract; any value re-entering the money path passes the **named AD-22 conversion** (declared rounding mode + target scale) — no descale/return crossing exists except through it. *(22.1 AC2)* **P0 — R-001**
- **T22-304** *(L3, R-001)* — **money-path float taint:** a binary float placed on the money path is treated as a taint (FR-001) and is flagged by the tier-1 money-path float scanner (NFR-02) when run over the robustness module. *(22.1 AC2)* **P0 — R-001**
- **T22-305** *(L3, AD-41)* — a float-valued measure labeled for identity takes **label-derived identity** (AD-41), never the bit-identity of the float; identical inputs yield identical measure identity (NFR-03). *(22.1 AC3)* **P1**
- **T22-306** *(L3)* — **distribution-summary primitive:** given (simulated distribution, observed value, declared direction ∈ {higher-is-better, lower-is-better}) it returns percentile ranks, confidence bands, and an **empirical one-tailed p-value** = the fraction of the distribution at or beyond the observed value **in the declared direction**, as pure data; the direction flips the tail correctly. *(22.1 AC4)* **P1**
- **T22-307** *(L3, SC-07/L20)* — the primitive emits **NO pass/fail verdict**: no α level, no pass battery, no accept/reject field appears in its output — only ranks/bands/p-value data. *(22.1 AC4)* **P0 — L20**
- **T22-308** *(L3, AR-13)* — an **unset required input** (a threshold, or an iteration / scenario / block-length / min-observation count) returns a typed **`invalid input`** refusal **RETURNED**, never a silently-applied number; the module ships **no invented default** for any of them. *(22.1 AC5)* **P0**
- **T22-309** *(L3, L20/SC-06)* — every robustness output is labeled **claim class robustness/infra-stress, never edge** (L20/B-7); no output can gate live money or spend split budget while GAP-0048 is open (SC-06). *(22.1 AC6)* **P0 — L20**

**Story 22.2 — Monte Carlo trade-shuffle**

- **T22-310** *(L3, R-001)* — trade-shuffle re-orders the realised **CT-29** trade stream of the run's replay binding and re-accumulates the equity path with **exact-integer** money math (AD-7); no float touches the equity path. *(22.2 AC1)* **P1**
- **T22-311** *(L3, B-7)* — **procedure-ephemeral:** trade-shuffle mints/persists **no** synthetic market series → the run stays **`world=replay`**; the procedure identity **plus seed** enter the result label. *(22.2 AC1)* **P0**
- **T22-312** *(L3, AR-59/B-10)* — **reproducibility:** each scenario's seed = `base_seed + scenario_index`; the result records RNG family, base seed, seed-derivation rule, scenario count, and data-window UTC-ns bounds; re-running the run id under its resolved config reproduces the **CT-32 fingerprint bit-for-bit or returns a typed refusal**. *(22.2 AC2)* **P0**
- **T22-313** *(L3, FR-043)* — per selected metric, percentile ranks + confidence bands + the direction-aware empirical percentile rank of the **original** result are written into the CT-32 artifact as **chart-series DATA, never images**; no pass/fail verdict. *(22.2 AC3)* **P1**
- **T22-314** *(L3, SC-07)* — the scenario count is a **UI-editable configurable with no ratified value**; the MC-1000 baseline is **not baked** as a default. *(22.2 AC4)* **P1**

**Story 22.3 — Monte Carlo candle-perturbation**

- **T22-315** *(L3, R-001)* — candle-perturbation **moving-block-bootstraps exact-integer OHLC delta tuples** (block length a UI-editable configurable, no ratified value), cumulative-sums them onto the seed price with **exact-integer** money math (AD-7), and always rebuilds a **valid strictly-positive OHLC series with high/low bounds enforced** (high ≥ max(open,close), low ≤ min(open,close), all > 0); **scenario 0 is the true history**. *(22.3 AC1)* **P0**
- **T22-316** *(L3, B-7)* — **procedure-ephemeral:** the synthetic series is never persisted → the run stays **`world=replay`**; procedure identity + seed enter the label; claim class robustness-only. *(22.3 AC2)* **P0**
- **T22-317** *(L3, SC-06)* — **persistence refusal seam:** a config that requests **persisting** the synthetic series → the run is **`world=simulated`**, a typed **`policy rejection`** for governed evidence, and cannot ledger into the bar's store until GAP-0048 closes; a config **binding a replay clock to synthetic-tainted persisted data** → a typed **`invalid input`** (B-2/B-7 wins). *(22.3 AC3)* **P0**
- **T22-318** *(L3, AR-59)* — each scenario uses an independent RNG seeded `base_seed + scenario_index`; the label records RNG family, seed derivation, block length, scenario count, resampling scheme, and data-window UTC-ns bounds; re-running the run id reproduces the CT-32 fingerprint or refuses. *(22.3 AC4)* **P1**
- **T22-319** *(L3, L20)* — percentiles / confidence bands / direction-aware ranks written into the CT-32 artifact as **data**, no verdict; claim class **robustness (alternate-history), never edge**; the result cannot gate live money. *(22.3 AC6)* **P1**

**Story 22.4 — pre-build rule-significance gate**

- **T22-320** *(L3, B-2 seam)* — **signal-only pass:** the gate drives the B-2 event-slice loop **with orders disabled** (same loop, same pinned sub-phase order, trading locked as in warm-up) so the strategy stays permanently flat; **any attempt to mint an entry, an exit, or a command during the pass is a typed `policy rejection`**. *(22.4 AC1)* **P0**
- **T22-321** *(L3, look-ahead/R-001)* — **next-bar alignment:** the signal at bar t is scored against the **NEXT** bar's log return (the first return not knowable at signal time), so **no forming-bar or future information** enters the statistic; close prices are **exact Price integers** that cross into the return-space float carve-out **only via the named AD-22 conversion** from 22.1. *(22.4 AC2)* **P0**
- **T22-322** *(L3)* — **zero-edge null:** returns are detrended by their in-sample mean **AND** the rule-return series is re-centred to zero before resampling (H0: E[return]=0); the reported statistic is the **empirical one-tailed p-value = the fraction of null resamples whose mean is ≥ the observed mean**. *(22.4 AC3)* **P1**
- **T22-323** *(L3, AR-13/AR-59)* — **insufficient data:** an observation count below the configured min-observation floor returns a **typed refusal**, never a fabricated p-value; where the floor is **unset**, the gate emits a **low-confidence warning label** instead of a hard number; the result records seed provenance (base seed + per-batch derivation), scheme + parameters, iteration count, and data-window UTC-ns bounds; re-running reproduces the null distribution bit-for-bit. *(22.4 AC5)* **P0**
- **T22-324** *(L3, SC-07)* — the resampling scheme is a UI-editable configurable (`iid` | `block` | `stationary`) with a configurable block length; the iteration count and min-observation floor are UI-editable configurables with **no ratified value**; **no invented default** for any of them. *(22.4 AC4)* **P1**
- **T22-325** *(L3, L20/SC-06)* — **advisory:** the result world is `replay` or `simulated`, **never `live`**; claim class robustness, never edge; the verdict is **advisory only** — a build pipeline may consult it but it **never auto-merges and never gates live money**; the pass/fail α thresholds stay deferred to GAP-0049. *(22.4 AC6)* **P0**

**Story 22.5 — walk-forward as a sequence of split-manifest runs**

- **T22-326** *(L3, AD-21/FR-012)* — a walk-forward is a **sequence of split manifests** (each a knowledge-time / embargo-purge / calendar-in-band manifest); each window is a **first-class run** under B-3/B-4 with its own resolved run-config; **"train/test" is a display alias for two such manifests, never a substitute**; every read goes through qmf-data split-governed at every boundary. *(22.5 AC1)* **P1**
- **T22-327** *(L3, SC-06/B-4)* — a train window's ledger line carries **`role = trial`** (or `replicate`) plus the objective measure and **never a bar verdict**; an out-of-sample window's bar outcome is a **read-time fold returning `not-yet-ruled`** until GAP-0048/0049 close. *(22.5 AC2)* **P0**
- **T22-328** *(L3, SC-11/B-15)* — batch admission resolves **exactly one registry as-of** at admission through the **single B-15 registry-read port**, frozen for every window and stamped into the batch label; after admission fragments resolve by **explicit fingerprint, never name@latest**. *(22.5 AC3)* **P1**
- **T22-329** *(L3, SC-07)* — window count, in-sample/out-of-sample spans, and step are UI-editable configurables with **no ratified value**; **no invented default and no baked WF/OOS battery**. *(22.5 AC4)* **P1**
- **T22-330** *(L3, B-12)* — the walk-forward view is a **read-time aggregation over the ledger's window runs (never a merged run)**, written into the CT-32 artifact as data; the aggregated IS/OOS metric distributions are the declared feeders for the deferred PBO/CSCV battery, which ships **no ratified thresholds**. *(22.5 AC5)* **P1**
- **T22-331** *(L3, AR-59/B-10)* — a walk-forward run id re-run under its resolved config reproduces the CT-32 fingerprint or returns a typed refusal; each window's label carries its **split-manifest fingerprints, registry_as_of, world, and evidence class**. *(22.5 AC6)* **P1**

### 4.4 Regression pins (per confirmed advisory finding)

- **T22-PIN-01** *(L3, P0 assertion 3, finding **F-22-01**)* — **OverflowError → typed refusal.** Invoke the public robustness boundary with an input in the range that currently triggers `OverflowError` (e.g. a scenario/iteration count or a return-space computation that overflows). Assert the boundary **RETURNS a valid CT-04 typed refusal** (category `invalid input` — or the boundary's declared category — with machine-readable context and retryability), and that **no exception crosses the public boundary** (DEC-0109 / CT-04: exceptions are reserved for programmer error, never a refusal channel). **This pin is expected to FAIL against current source; the failure IS the finding (F-22-01), recorded — never worked around by editing source or weakening the assertion.** Once the source is repaired (out of this audit's scope), the pin locks the behaviour against regression. **P0**
- **T22-PIN-02** *(L0, NFR-11/L27, finding **F-22-02**)* — **FAILURES.md not extended.** A static/doc gate over `qmb/FAILURES.md` asserting it contains an NFR-11 failure-register entry — with all six required fields (Failure class, Detection, Auto-recovery/retry, Visible degraded state, Notification tier, Product-user affordance) — for **each** Epic-22 designed failure mode: (a) unset-required-input `invalid input` (22.1), (b) synthetic-persistence `policy rejection` (22.3), (c) replay-clock-on-synthetic `invalid input` (22.3), (d) insufficient-data refusal + low-confidence-warning path (22.4), (e) the OverflowError→typed-refusal path (F-22-01). **Verified during authoring: none of these entries exist** (the file covers only stories 14–19). **Expected to FAIL → records finding F-22-02** (NFR-11 incomplete-story: a designed failure with no register entry is incomplete, the same as a missing test). **P1**

### 4.5 Independent review (L6)

- **T22-L6** *(L6, review — delivered as `L6-REVIEW.md`)* — an independent adversarial read of `qmb/src/qmb/robustness/` against the **B-14** spine rule, the Epic 22 ACs, and the three firewalls, confirming by reading the source (this level is *permitted* to read source — §4.3's discipline binds only the requirement-derived test list): (1) the float carve-out is genuinely bounded — no float reaches the money path outside the declared statistic, every money-path re-entry goes through the named AD-22 conversion; (2) no output field ever asserts edge or emits a pass/fail verdict (L20/SC-07); (3) every failure path RETURNS a CT-04 refusal — enumerate every `raise` on a public boundary and confirm F-22-01 is the only such defect or record any others found; (4) no invented default/threshold is shipped; (5) confirm F-22-02 (register gap) and the finding characterisations in §3 are accurate. Findings feed the epic's `findings.csv`.

---

## 5. Test-level allocation (L0–L6; one behaviour one level, lower level wins)

Reconstructed from the ratified quality tiers (`LENS-TEST-STRATEGY`, DEC-0101/0102), since `test-design-qa.md` is absent (§1.4). **L6 = independent review** per the audit convention (every sibling epic dir ships an `L6-REVIEW.md`). Under **audit tier T3** the executed band is **L3 + the pins + L6**; L0–L2/L4/L5 are not populated with an independent suite this pass — each behaviour they would prove is instead pinned once at L3 (lower-level-wins is applied *within the executed band*), and the deferred levels are listed in §7.7.

| Level | Definition | Maps to ratified tier | Epic-22 (T3) population | Count |
|---|---|---|---|---|
| **L0** | Static / build / doc gate: register completeness, no module-global mutable state, money-path float scanner | Tier 1 (`poe check`) | T22-PIN-02 (register gate); T22-304 borrows the NFR-02 scanner | **1** |
| **L1** | Pure unit: one pure function, injected inputs, deterministic | Tier 1 | *deferred-by-tier (§7.7)* — distribution-summary math, seed derivation | 0 |
| **L2** | Integration/component: qmb modules composed in-process | Tier 2 | *deferred-by-tier (§7.7)* | 0 |
| **L3** | **Contract / acceptance conformance:** CT-* round-trip/boundary/invalid-refusal, carve-out boundary, world/persistence refusal seams, reproduction, claim-class labeling — **the T3 band** | Tier 2 (`poe check-integration`) | T22-301..331 + T22-PIN-01 | **32** |
| **L4** | Property / invariant / golden-scenario: hypothesis over the bootstrap & reproducibility laws | Tier 1 (property) / Tier 2 | *deferred-by-tier (§7.7)* | 0 |
| **L5** | End-to-end governed run (procedure → CT-32 → ledger line) | Tier 2/3 | *deferred-by-tier (§7.7)* — needs Epic 14/15 | 0 |
| **L6** | **Independent adversarial review** against spine + ACs + firewalls | review artifact | T22-L6 → `L6-REVIEW.md` | **1** |

**Planned counts — L0: 1 · L3: 32 · L6: 1 review.** Total executable checks this pass: **33** + the L6 review.

Allocation notes (lower-level-wins, applied within the T3 band):
- The distribution-summary **p-value/percentile arithmetic** is inherently an L1 unit behaviour; under T3 it is asserted once as an **acceptance** conformance at L3 (**T22-306**) rather than as a pure-unit suite — the T1 L1 breadth is recorded deferred-by-tier (§7.7).
- **Reproducibility** (T22-312/318/331) is inherently an L4 property; under T3 it is pinned once at L3 as a concrete re-run-reproduces-or-refuses case per procedure; the hypothesis property over arbitrary seeds/inputs is deferred-by-tier.
- The **carve-out** and the **refusal guards** are pinned at L3 (T22-303/304/308/317/323, T22-PIN-01); **mutation sensitivity** on those guards (a mutation that flips a guard must fail a test) is the T1 treatment, deferred-by-tier.
- The **register gate** sits at L0 (T22-PIN-02) — it is a static/doc check, the lowest level that can prove it.

---

## 6. Fixtures, data and determinism harness

- **Runner:** `uv run pytest qa/tests/epic_22 -q` from the worktree root (dev group synced). Any property scaffolds authored later use `uv run --with hypothesis ...`. No test edits source; a failing test is recorded as a finding.
- **Determinism rules (from `LENS-TEST-STRATEGY` / `fixtures-and-scenarios` discipline):** unit/acceptance fixtures make **no network calls**; time is an **injected CT-02 clock (int64 UTC ns)** at the composition root — no fixture below the root reads the system clock; every randomized fixture **declares its seed** (and asserts the `base_seed + scenario_index` derivation rule directly, T22-312/318); equal semantic inputs must replay to equal CT-05 `fp1`/CT-32 fingerprints, computed by the single qmf-core implementation with **floats refused in identity content**.
- **Controlled fixtures (L6/DEC-0007 — no product mock market data, no default strategies shipped):**
  - **A small completed `world=replay` backtest fixture** with a known CT-29 trade stream and a known exact-integer equity path — the substrate for trade-shuffle (T22-310/311/312) and the reproduction pins. Checked into `qa/` fixtures, never sourced from a provider at run time.
  - **A small real-historical OHLC window** (exact-integer prices) for candle-perturbation (T22-315..319) with a known block-bootstrap output for a fixed seed, so scenario 0 = true history and the strictly-positive/high-low-bounds invariant are checkable.
  - **A bare entry-rule + data window** for the significance gate (T22-320..325): a rule whose signal series and next-bar-aligned log returns are known, so the detrended-and-recentred null and the one-tailed p-value are exactly recomputable; plus a strategy stub that attempts an entry/exit/command during the signal-only pass (must be refused).
  - **A short split-manifest sequence** for walk-forward (T22-326..331) with known per-window fingerprints and registry_as_of.
  - **An overflow-triggering input** for T22-PIN-01 (the value range that currently raises `OverflowError`).
- **CT-04 / CT-29 / CT-32 fakes** are shape-faithful to the ratified contracts (fields, unit-kinds, refusal categories, the CT-32 chart-series-data shape). A test that passes against a shape-unfaithful fake is itself a finding.
- **Refusal harness:** every "is refused" assertion (T22-308, T22-317, T22-323, T22-327 OOS fold, T22-PIN-01) checks a **RETURNED** CT-04 value carrying `{category ∈ the seven, context (present, non-null), retryability}`, and asserts the absence of prohibited side effects (no ledger line, no log write from the pure library, no persisted synthetic series). No assertion parses an exception message.
- **Values are referenced, never restated:** any governor/limit/severity value comes from registry keys, never invented literals; and because Epic 22 ships **no ratified thresholds**, the configurable tests (T22-314/324/329) assert *absence of a baked default*, not a specific number.

---

## 7. Untestable / deferred / blocked / out-of-scope requirements

### 7.1 Threshold values, α levels, and pass batteries — DEFERRED (SC-07)
Every robustness threshold, every α level, and the MC-1000 / PBO / CSCV / WF-OOS pass batteries are **deferred to the GAP-0048/0049 sittings** and ship only as UI-editable configurables with no ratified value. Testing a specific number would assert an unratified constant. Only the *discipline* is testable now — **no invented default** (T22-314/324/329), **unset required input → refusal** (T22-308), and **no pass/fail verdict emitted** (T22-307). Recorded, not a coverage gap.

### 7.2 Orchestrator governor, fan-out, and per-run ledger line — OWNED BY Epic 15
Process-per-run fan-out bounded by min(cpu, memory), enqueue-when-full, cancel tokens, and the **one-ledger-line-per-run** law (`role = replicate`/`trial`, never a bar verdict) are **Epic 15** requirements (orchestrator). AC 22.2/AC5, AC 22.3/AC5, and the per-window ledger line in 22.5 surface these only as a **seam** here. Per the EPIC-BINDING RULE they are noted, not tested in Epic 22; T22-327 asserts only the robustness-side *role/verdict shape* the orchestrator will write, not the governor.

### 7.3 The B-2 event-slice loop internals — OWNED BY Epic 14
The pinned sub-phase order, the warm-up trading-lock, and forming-bar non-actionability are **Epic 14** (run loop). Story 22.4 *uses* the loop in signal-only/orders-disabled mode; Epic 22 tests only the **robustness-side driving** of it and the policy-rejection seam (T22-320) and the next-bar alignment the gate imposes (T22-321) — never the loop's own determinism.

### 7.4 CT-32 result-artifact minting and the fingerprint engine — OWNED BY Epic 14/19
The CT-32 artifact and the golden-slice fingerprint machinery are Epic 14 (Story 14.7) / Epic 19. Epic 22's reproduction ACs *reuse* them; the robustness-side testable part is that **procedure identity + seed + seed-derivation** enter the label and that a re-run **reproduces-or-refuses** (T22-312/318/331) and that summaries are written as **chart-series data** (T22-313/319/330). The underlying fingerprint engine is not re-verified here.

### 7.5 qmf-data split governance — OWNED BY Epic 3
CT-12 split manifests, seal/embargo/purge, knowledge-time partitioning, and calendar-in-band identity are **Epic 3**. Story 22.5 *reads through* them; Epic 22 tests the WF-side **manifest-sequence construction** and the split-governed **read seam** (T22-326), not the split governance itself.

### 7.6 GAP-0048-gated content — deferred by seam (SC-06)
`world=simulated` unlock, fill/slippage/financing fidelity calibration, and split-budget spend are gated on GAP-0048 and cannot be asserted. Only the **refusal seams** are testable now: persist-synthetic → `policy rejection`, replay-clock-on-synthetic → `invalid input` (T22-317), and `not-yet-ruled` OOS folds (T22-327). The optimistic taint on all evidence is assumed, not re-proved here.

### 7.7 T3 tier scope — the L0/L1/L2/L4/L5 independent suite is DEFERRED-BY-TIER (not a requirement gap)
This is a **T3** audit. The following would be authored in a **T1** pass and are recorded here with their owning level, each P0/P1 *behaviour* they would prove already pinned once at L3 above:
- **L1 pure-unit:** the distribution-summary percentile/confidence-band/p-value arithmetic (edge cases: ties, empty/degenerate distributions, both directions); the `base_seed + scenario_index` derivation.
- **L4 property (hypothesis):** over arbitrary seeds — re-run reproduces bit-for-bit (T22-312/318/331 breadth); over arbitrary OHLC-delta sequences — the block-bootstrap always yields a strictly-positive high/low-valid series (T22-315 breadth); over arbitrary return series — the one-tailed p-value ∈ [0,1] and is monotone in the observed mean.
- **L2 integration:** the significance gate composed with the real B-2 loop stub; walk-forward composed with the registry-read port and the split-manifest sequence.
- **L5 end-to-end:** a governed procedure run producing a CT-32 artifact + one ledger line (needs Epic 14/15).
- **Mutation sensitivity (L0/L3 adjunct):** a mutation flipping the carve-out guard, a refusal guard, or the claim-class label must fail a test; a surviving mutant means the test is decorative.
Rationale for the tier: Wave-7 weight-M, thresholds deferred, GAP-0048-gated, cannot gate live money — lower blast radius than the T1 identity/determinism epics. If a P0 finding (F-22-01) proves systemic on review, escalate this epic to a T1 re-pass.

### 7.8 PLAN-INTEGRITY CAVEAT — named authorities absent
`_bmad-output/test-artifacts/test-design-qa.md` and `.../test-design/QMX-handoff.md` — named as authorities for the L0–L6 architecture, the Per-Epic template, the 15 P0/P1 assertions, and this epic's risk-gate rows — **do not exist in this worktree** (`_bmad-output/test-artifacts/` is absent). The 8-section template and L-level scheme here are reconstructed from `LENS-TEST-STRATEGY` and the sibling `epic_13` plan; **R-001** and **P0 assertion 3** are taken from the task brief; **L6 = review** is inferred from the sibling `L6-REVIEW.md` artifacts. If those files are supplied, reconcile §5's L-level mapping and §2's assertion set against them. Recorded as a finding, not worked around.

---

## 8. Exit criteria and coverage ledger

The epic's T3 verification passes when:

1. **Every P0/P1 AC in §2 maps to at least one executed L3 test in §4.3**, and every §4 test has a recorded PASS or a FINDING (a FINDING is a requirement the source does not satisfy — never resolved by editing source or weakening the test).
2. **R-001 (float carve-out) satisfied:** T22-303, T22-304, T22-305 PASS, reinforced by T22-310/315/321 — money/P&L/equity stay exact-integer; a float lives only inside the declared statistic; every money-path re-entry goes through the named AD-22 conversion; float-measures take label-derived identity.
3. **L20 / SC-06 / SC-07 firewalls green:** T22-307 (no verdict), T22-309/319/325 (claim class robustness, never edge, no money gating), T22-317 (persist-synthetic → policy rejection), T22-327 (OOS `not-yet-ruled`), and every configurable test (T22-314/324/329) proves no baked default.
4. **Refusal discipline:** T22-308, T22-317, T22-323, T22-327, and T22-PIN-01 each assert a **RETURNED** CT-04 refusal of the correct category — no public boundary raises.
5. **Confirmed findings recorded:**
   - **F-22-01 (OverflowError, P0 assertion 3)** — T22-PIN-01 is authored and **expected to FAIL** against current source; the failure is recorded as F-22-01 in `findings.csv`, characterised as *a public boundary raises `OverflowError` where CT-04 requires a returned typed refusal (DEC-0109)*. The pin locks the behaviour post-repair (repair is out of this audit's scope).
   - **F-22-02 (FAILURES.md not extended, NFR-11/L27)** — T22-PIN-02 is authored and **expected to FAIL**; recorded as F-22-02, characterised as *the robustness ladder ships designed failure modes with no `qmb/FAILURES.md` register entries (verified: zero Epic-22 entries in 765 lines)*.
6. **L6 review delivered** (`L6-REVIEW.md`) confirming the two firewalls and enumerating every public-boundary `raise` (to catch any F-22-01 siblings), with its findings folded into `findings.csv`.
7. **Deferred / out-of-scope items (§7) are explicitly recorded**, each with its owning epic or its deferral reason — none silently counted as passed, none as failed.

Coverage ledger maintained alongside execution in `qa/epics/epic_22_qmb-robustness/` — one row per §4 test id → {level, status PASS/FINDING/DEFERRED, evidence path}, plus `findings.csv` (F-22-01, F-22-02, and any L6 additions) and `RESULTS.md`.
