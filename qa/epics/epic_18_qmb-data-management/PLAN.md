# Epic 18 — QMB data management — Verification PLAN (audit tier T2)

> Per-epic verification plan. **Eight sections, order load-bearing.** **Section 4 (the
> independent test list) was authored entirely from requirements BEFORE any
> `qmb/src/qmb/data/` source file of this epic's package was opened.** As of authoring,
> **zero files under `qmb/`** have been read — the whole plan is requirement-derived. Test
> file paths named below are planned targets under `qa/` to be created at execution time. A
> failing test is a **FINDING**; source is read-only evidence and is never edited to make a
> test pass, and a test is never weakened to pass.

> **PROCESS-GAP / PLAN-INTEGRITY CAVEAT (read first).** Two authorities named in the audit
> brief **do not exist in this worktree**:
> `_bmad-output/test-artifacts/test-design-qa.md` (the Per-Epic Test Plan Template + the
> L0–L6 test-level architecture) and `_bmad-output/test-artifacts/test-design/QMX-handoff.md`
> (the 15 P0/P1 assertions + this epic's risk-gate rows). Confirmed absent by full-tree search
> (`_bmad-output/test-artifacts/` does not exist; only `archive/recovery/*/restart-handoff.md`
> match "handoff"). **Consequence:** the 8-section structure below and the L0–L6 taxonomy in
> §5 are **reconstructed** from the sibling PLANs already in this audit
> (`qa/epics/epic_13_qmb-substrate/PLAN.md`, `epic_14_qmb-run-loop/PLAN.md`), from the
> ratified quality tiers (`docs/lenses/testing/fixtures-and-scenarios.md`, DEC-0101/0102),
> and from this project's own vocabulary (tier-2 = `poe check-integration`; "one behaviour
> one level, lower level wins"). The **risk gates R-007 and R-011, the tier scope, and the
> confirmed defect FIND-001** are taken verbatim from the task brief. **L6 is the review
> level** (each audited epic ships an `L6-REVIEW.md`), not the reconstructed "non-functional"
> guess an earlier sibling PLAN made. When the two files are restored, reconcile §1 template
> order, §3 risk-gate rows, and §5 level definitions against them before executing. This is a
> **finding**, recorded, not worked around.

---

## 1. Epic under test and authorities

- **Epic:** 18 — QMB data management. **Wave 7, priority L** (per epics.md line 400 wave
  row). **Audit tier:** T2.
- **Package under test:** `qmb/src/qmb/data/` — the thin `qmb data` command fronts over the
  ratified QMF data contracts (module `data/` in the QMB structural seed, B-11). Doors:
  `qmb/src/qmb/doors/{cli,api}` for the `data` command group. Seams consumed read-only:
  `qmf-data` (CT-10/CT-11/CT-13/CT-15 rooms + intake + journal), `qmf-core` (CT-01/CT-02/CT-04),
  `qmf-registry` (CT-07 lineage), `qmf-calendar-forex` (Epic 4 FX calendar provider for gap-check).
- **What this epic delivers (scope of verification — FR-042; B-11; AR-54; DEC-0166/0170):**
  the `qmb data` command group as **thin fronts** over QMF data contracts — **download-once**
  acquisition under the operator's own provider relationship into the immutable raw archive
  (18.1); the **ship-no-corpus licensing gate** turning each window's recorded license tag
  into a governed-evidence pass-or-typed-refusal (18.2); `qmb data list` catalog by
  `(venue, symbol, window, side)` (18.3); `qmb data verify` window integrity (18.4); and
  `qmb data gap-check` calendar-aware gap detection (18.5). QMB **mints no second data layer**
  — the `qmf.data` contracts own all persistence.
- **Two senses of "tier" (do not conflate).** *Audit tier* **T2** = this plan's scrutiny band
  (its scope is defined by the brief: **L2 + L3 for every AC, targeted L1 properties, an L6
  review**). *Test tier* **tier-2** = the project's `poe check-integration` execution band that
  the door-parity contract test and the zero-corpus release check run in. §5 maps the L0–L6
  levels onto those bands.
- **Explicitly OUT of scope (delivered by other epics — seams only here, see §7):** the raw
  archive / bitemporal store / room roles and CT-15 idempotent intake themselves (Epics 3/6 —
  QMB only fronts them); the run loop that *reads* the rooms and whose provider-fetch attempt is
  a `policy rejection` (Epic 14); the CT-32/ledger citing artifact into whose lineage a passing
  license tag rides (Epics 14/19); synthetic-fill *content* and the `world=simulated` unlock
  (Epic 23 / GAP-0048); full cross-door parity beyond the data-catalog payload (Epic 16); the
  real FX-session calendar content (Epic 4). Epic 1 owns the FR-002 ambient-clock *scanner
  mechanism* (Story 1.8) — see the epic-binding note under §3 on FIND-001.

**Authorities consulted (precedence order):**
1. `_bmad-output/planning-artifacts/epics.md` — **Epic 18** (Stories 18.1–18.5, lines
   3572–3728), plus the FR map (FR-042 → Epic 18, line 300) and FR-002 (owned by **Epic 1**,
   line 35).
2. `docs/` knowledge base: `docs/components/qmb.md` (**B-11** data commands; B-1 thin doors;
   B-7 provenance-derived world; FM-3/FM-10; DEC-0166/0170); contracts **CT-10** (source
   observation / bitemporal), **CT-15** (external-source adapter / idempotent intake),
   **CT-04** (typed refusal, seven categories), **CT-01** (exact money/price scaled-int),
   **CT-02** (time + versioned calendar), **CT-07** (lineage edge), **CT-13** (journal /
   data-quality event), **CT-11** (evidence persistence); `docs/lenses/testing/
   fixtures-and-scenarios.md` (fixture classes, determinism rules, DEC-0106 clock injection).
3. `_bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/` spine (B-1..B-15,
   inherited AD-/AR-). Architecture rules cited by the Epic-18 ACs: **AR-54** (runs read rooms,
   never providers; no vendored downloader; wheel ships no corpus), **AR-46** (bid+ask
   preserved), **AR-15** (money-path exact integers), **AR-13** (value-or-typed-refusal),
   **AR-30** (rebuildable DuckDB view over Parquet), **AR-35** (propagated `correlation_id`),
   **AR-58** (per-transport refusal rendering / verbatim door value), **AR-16** (nothing below
   the composition root reads the system clock), **SC-07** (interfaces-not-numbers), **SC-06 /
   L20** (nothing synthetic validates edge).
4. **MISSING (see caveat above):** `test-design-qa.md`; `QMX-handoff.md`. R-007, R-011, the T2
   tier scope, and FIND-001 are taken from the task brief.

---

## 2. Requirements inventory and traceability

Every acceptance criterion of Epic 18, restated as a testable requirement (RQ), keyed to the
independent test(s) in §4. **Epic-binding confirmed:** every RQ below is owned by Epic 18's
section of epics.md (FR-042). The one cross-cutting invariant — **RQ-CLOCK / FIND-001** — is
carried because the offending code is Epic 18's own deliverable (`qmb/src/qmb/data/download.py`)
and the read breaks Epic 18's own reproducible-window (18.1 AC2) and determinism (18.4 AC5 /
18.5 AC4) ACs; the FR-002 *scanner mechanism* stays Epic 1's and is **not** tested here.

| RQ | Requirement (assertion) | Story / AC | Contract / rule | Test id(s) |
|---|---|---|---|---|
| RQ1 | `data download` is a thin front over CT-10/CT-15 that adds **no second data layer**; it carries only parsing, transport, and adapter-selection; `qmf.data` owns all persistence. | 18.1 AC1 | B-11, B-1 | T18-1a, T18-0c |
| RQ2 | The request accepts `(venue, symbol[list], start, end, resolution, side∈{bid,ask,both})` from a Book/BMS fragment or flags; `end` defaults to today but honors an explicit `end` for a **reproducible window**. | 18.1 AC2 | — | T18-1b |
| RQ-CLOCK | **No `qmb/data` code below the composition root reads an ambient system clock** (`datetime.now()`, `time.time()`, `date.today()`, …); `end`-defaults-to-today and every time read are taken from an **injected clock**, so the window is reproducible. **CONFIRMED LIVE DEFECT — `download.py:127` reads `datetime.now()` (FIND-001).** | 18.1 AC2 (reproducible window) + cross-cutting | FR-002 / CT-02 / AR-16; DEC-0106 | **T18-P1**, T18-0a |
| RQ3 | Fetch flows through a **QMX-authored** provider-adapter port (`fetch`, `earliest_available`, `list_symbols`, batch `count`, `rate-limit`), Dukascopy adapter #1; **no third-party downloader code is vendored**. | 18.1 AC2 | AR-54, DEC-0013/0059 | T18-1d, T18-0d |
| RQ4 | A provider error — maintenance, geo-block (HTTP-451-class), bad window, missing entitlement — returns a **CT-04 typed refusal** (category + machine-readable context + retryability) rendered per transport; **never a silent partial ingest**. | 18.1 AC2 | CT-04, AR-58 | T18-1e **[R-007]** |
| RQ5 | Bid and ask land as **distinct streams**, never collapsed to one OHLCV. | 18.1 AC3 | AR-46 | T18-1f |
| RQ6 | Timestamps are **int64 UTC-ns** and prices are **exact scaled integers** crossing a named **AD-22** conversion boundary; a provider-native float/decimal never reaches a CT-10 write unconverted. | 18.1 AC3 | CT-01, AR-15 | **T18-P3**, T18-1h |
| RQ7 | Fetched ticks/bars are written as **CT-10 bitemporal source observations** into the world-scoped raw room (CT-11) and retained forever. | 18.1 AC3 | CT-10, CT-11 | T18-1h |
| RQ8 | Re-running download with identical inputs over an overlapping window is **idempotent** via the bitemporal `(source, source-native id, revision)` key (already-present observations skipped, not duplicated). | 18.1 AC4 | CT-15, CT-10 | T18-1i, **T18-P2** |
| RQ9 | `--overwrite` appends a **new CT-10 revision** rather than mutating the only copy. | 18.1 AC4 | CT-10 | T18-1j |
| RQ10 | A long import emits **machine-observable progress** (percent, date-reached, ETA) to a supervising channel — not only a human progress bar. | 18.1 AC5 | — | T18-1k (seam, §7) |
| RQ11 | Each ingested window records **provenance + a license tag** as CT-10 source-observation metadata (the input the 18.2 gate enforces). | 18.1 AC5 | B-11 | T18-1m **[R-011]** |
| RQ12 | Runs read **only qmf-data rooms** with no path to a provider; `data download` is the **sole** provider-fetch surface; a run that attempts a provider fetch is a `policy rejection`. | 18.1 AC6 | AR-54 | T18-1l (run half → Epic 14, §7) |
| RQ13 | The gate returns **value-or-typed-refusal**: a granting tag passes; a tag of `denied`, `unknown`, or **absent** is a typed refusal for governed-evidence use, carrying `(venue, symbol, window)` + tag state as machine-readable context. | 18.2 AC1 | CT-04, AR-13, B-11 | T18-2a **[R-011]**, T18-6a |
| RQ14 | The recognized license states are an **explicit interface** (redistribution-ok / internal-only / denied / unknown) resolved from a per-venue policy record or operator ruling, **never inferred by the adapter**; an un-ruled state is **blank**, and a blank is treated as `unknown` → blocks governed use. | 18.2 AC2 | SC-07 | **T18-P4** |
| RQ15 | A Dukascopy window with no recorded usage right **still ingests and is catalogable**; non-evidence use (infra stress, strategy-logic smoke) is allowed; governed-evidence citation is refused until a usage right is recorded. | 18.2 AC3 | DEC-0170 | T18-2c |
| RQ16 | The built/shipped wheel contains and redistributes **zero corpus bytes**. | 18.2 AC4 | AR-54 | T18-2d |
| RQ17 | On a passing window cited as governed evidence, the license tag + **granting authority ride into the citing artifact's CT-07 lineage**; the gate is a **pure read-time check that writes nothing**. | 18.2 AC5 | CT-07 | T18-2e (gate side; downstream ride → Epics 14/19, §7) |
| RQ18 | `data list` reports, per `(venue, symbol, resolution, side∈{bid,ask})`, the covered `[start,end]`, observation/bar count, provenance, license tag, and current bitemporal revision. | 18.3 AC1 | FR-042 | T18-3a |
| RQ19 | The catalog is served through qmf-data contracts as a **rebuildable DuckDB view over the Parquet rooms** — never an authoritative second store. | 18.3 AC2 | B-11, AR-30 | T18-3b |
| RQ20 | An **absent window** returns an explicit "not present" result **as a VALUE** (not a refusal). | 18.3 AC3 | — | T18-3c |
| RQ21 | When both sides are requested but only one is present, the **missing side is shown absent** for that `(venue, symbol, resolution)`. | 18.3 AC4 | — | T18-3d |
| RQ22 | The same catalog query through the **CLI and the Python API door returns an identical machine-readable payload** (tier-2 door-parity contract test); the CLI renders it, the Python door returns it verbatim. | 18.3 AC5 | B-1, AR-58 | T18-3e |
| RQ23 | `verify` checks bid+ask both present where `both` was requested, timestamps **monotonic int64 UTC-ns**, and prices **exact scaled integers with no float taint**, returning a typed result carrying the counts + any defects. | 18.4 AC1 | CT-01, AR-15 | T18-4a, **T18-P3** |
| RQ24 | The edge-integrity **tolerance is a configurable interface with no invented number**; a **blank** tolerance leaves the guard **un-armed** and verify reports the raw edge offsets rather than passing/failing against a fabricated threshold. | 18.4 AC2 | SC-07 | T18-4b |
| RQ25 | A defect (edge beyond an armed tolerance, a requested side missing, a non-integer price taint, an empty provider return) returns a **CT-04 typed refusal** with machine-readable context, **never a silent pass**. | 18.4 AC3 | CT-04 | T18-4c **[R-007]** |
| RQ26 | Interior gaps are **reported, not filled**; a synthetic fill would be a `world=simulated` derived layer, never written as observed. | 18.4 AC4 | B-7, L20 | T18-4d (seam, §7) |
| RQ27 | The verdict is a **factual data-quality result** (never edge/verdict-bearing) journaled through CT-13 with a propagated `correlation_id`; a re-run over the same immutable window **reproduces the same verdict**. | 18.4 AC5 | CT-13, AR-35, NFR-03 | T18-4e, **T18-P5** |
| RQ28 | `gap-check` resolves expected sessions from the **CT-02 versioned trading calendar** (qmf-calendar-forex for FX), computes expected-minus-present bars per session, and reports gaps as `(start, end, expected, present)`. | 18.5 AC1 | CT-02 | T18-5a |
| RQ29 | Where the calendar marks the venue **closed** and bars are absent → **real closure, not a gap**; where the venue is **open** but bars absent → **genuine gap** — the calendar is the deciding authority. | 18.5 AC2 | CT-02 | T18-5b |
| RQ30 | A **24/7** venue reading an always-open CT-02 calendar treats every non-present interior interval within an open window as a **genuine gap** (no closure exemption). | 18.5 AC3 | CT-02 | T18-5c |
| RQ31 | gap-check **records the CT-02 calendar version** used; re-running with the same window + same version yields the **identical gap set**. | 18.5 AC4 | NFR-03 | **T18-P6**, T18-5a |
| RQ32 | gap-check only reports gaps and **never writes interior fill**; a filled series is a `world=simulated` `policy rejection` for governed evidence until GAP-0048. | 18.5 AC5 | SC-06, B-7 | T18-5e (seam, §7) |
| RQ33 | A missing or **unresolvable calendar** for a `(venue, symbol)` returns a CT-04 **`unavailable dependency`** typed refusal — never a silent always-open guess. | 18.5 AC6 | CT-04 | T18-5f **[R-007]** |
| RQ34 | **Every refusal** on an Epic-18 path is a valid **CT-04 value** — category ∈ the seven, context present (non-null), retryability present — **RETURNED** across the public boundary, never raised. | cross-cutting | CT-04 | T18-6a |

FR/NFR roots: **FR-042** (data-management commands + licensing gate), **NFR-02** (determinism,
no ambient nondeterminism, no module-global mutable state), **NFR-03** (reproducibility).

---

## 3. Risk gates and priority assertions

The epic-specific focus. Data acquisition is the **root of every downstream run's evidence**:
an unlicensed window silently cited, a malformed window silently accepted, or a
non-reproducible download all corrupt the governed record before a single backtest runs. The
brief flags a **worst-likelihood cluster of 3 CRITICAL complexity findings** in this package
and one **confirmed live defect**. The gates below are the audit's centre of gravity.

### FIND-001 — CONFIRMED LIVE DEFECT: ambient clock below the composition root (RQ-CLOCK)
`qmb/src/qmb/data/download.py:127` reads `datetime.now()` below the composition root — an
**ambient-scan FAIL** and a violation of the injected-clock invariant (**FR-002 / CT-02 /
AR-16**; DEC-0106 "no fixture or code below the root reads the system clock — time is
injected"). Because `end` defaults to today, an ambient read makes the "reproducible window"
that **18.1 AC2** promises non-reproducible, and it undermines the determinism **18.4 AC5 /
18.5 AC4** demand. **The regression test T18-P1 pins the requirement and SHOULD FAIL against
current source** — inject a clock and observe that `end`/today derives from it, paired with the
L0 import scan T18-0a. **Recorded as a finding; source is NOT edited to fix it.**
*Epic-binding note:* FR-002's *scanner mechanism* is owned by Epic 1 (Story 1.8) and is not
re-tested here; T18-P1 asserts the invariant's manifestation in Epic 18's own deliverable
against Epic 18's own reproducibility ACs — squarely in scope.

### R-007 — adversarial / malformed input refuses rather than `Ok` (worst-likelihood cluster)
Every ingest, catalog, verify, and gap-check boundary that meets a hostile or malformed input
must return a **CT-04 typed refusal**, never a silent success, partial ingest, or fabricated
pass. Covered by **T18-1e** (provider error — maintenance / geo-block / bad window / missing
entitlement → refusal, no partial ingest), **T18-4c** (verify defect — edge-beyond-tolerance /
missing side / float taint / empty return → refusal, never a silent pass), **T18-5f**
(unresolvable calendar → `unavailable dependency`, never an always-open guess), reinforced by
**T18-6a** (every refusal is a valid returned CT-04 value). These are the assertions that hold
the **3 CRITICAL complexity loci** honest (see below).

### R-011 — license-tag presence gates governed evidence (DEC-0166/0170)
Download-once + per-window license tags: a window's recorded tag is the sole thing standing
between raw data and governed-evidence citation. Covered by **T18-1m** (every window records a
license tag as CT-10 metadata), **T18-2a** (gate passes a granting tag, refuses
denied/unknown/absent for governed use), **T18-P4** (the taxonomy is a total, explicit
interface; blank ⇒ unknown ⇒ block), **T18-2c** (unlicensed Dukascopy window still ingests +
non-evidence use allowed, governed citation refused — DEC-0170 personal-use posture), and
**T18-2e** (a passing tag + granting authority ride into CT-07 lineage; the gate writes
nothing). **The gate presence is the audit's second centre of gravity: an absent tag must fail
closed.**

### The 3 CRITICAL complexity findings — the worst-likelihood cluster
The brief states three CRITICAL complexity findings in `qmb/src/qmb/data/`. From the
requirement surface (metrics **to be confirmed against the module inventory at execution**,
sibling-plan discipline) the three highest-branch, highest-identity loci are:

| Locus (requirement-derived) | Why it is the risk | Densest coverage in this plan |
|---|---|---|
| **download orchestration** (`download.py` — where FIND-001 lives): parsing + transport + adapter-selection + AD-22 conversion + bitemporal idempotent keying + `--overwrite` revision + progress + provenance/license tagging. | The most branches and the most identity weight; the confirmed ambient-clock defect is here, and any silent partial ingest or dedup miss corrupts the archive. | T18-1a/1b/1d/1e/1f/1h/1i/1j/1m + properties T18-P1 (clock), T18-P2 (idempotence), T18-P3 (exact-int). |
| **verify integrity** (`verify.py`-class): side-presence + monotonic-timestamp + float-taint + edge-tolerance guard + empty-return, each a distinct defect arm. | Multi-arm refusal logic is where a silent pass hides; the edge tolerance is an un-armed-by-default SC-07 interface easy to mis-default to a fabricated number. | T18-4a/4b/4c + determinism property T18-P5 + refusal-shape T18-6a. |
| **gap-check calendar classification** (`gapcheck.py`-class): session resolution + closed-vs-gap decision + 24/7 branch + calendar-version determinism + unresolvable-calendar refusal. | The closed-vs-gap decision is the whole point; a wrong branch either hides a real hole or invents a phantom gap, and an unknown calendar must never default to always-open. | T18-5a/5b/5c/5f + determinism property T18-P6. |

### Priority ladder (derived — the 15-assertion handoff is absent, §1 caveat)
- **P0 (block the epic on any failure):** RQ-CLOCK/FIND-001, RQ4, RQ8, RQ11, RQ13, RQ14, RQ16,
  RQ25, RQ29, RQ33, RQ34.
- **P1 (high — evidence honesty & fidelity):** RQ1, RQ5, RQ6, RQ7, RQ9, RQ15, RQ17, RQ23, RQ24,
  RQ27, RQ28, RQ30, RQ31, RQ22.
- **P2 (completeness):** RQ2, RQ3, RQ10, RQ12, RQ18, RQ19, RQ20, RQ21, RQ26, RQ32.

---

## 4. Independent test list (authored from requirements before reading src)

> This section was written purely from the authorities in §1 (epics.md Epic-18 ACs, the QMB
> spine B-11/B-1/B-7, the CT-* contracts, the fixtures lens). **No `qmb/` source file was read
> before or during its authoring.** Each row asserts what the REQUIREMENT demands. A test that
> fails is a FINDING; source is read-only evidence, never edited to make a test pass, and a
> test is never weakened. Level assignment follows "one behaviour, one level; the lowest level
> that can meaningfully assert it wins" (taxonomy in §5). Properties use `hypothesis`
> (`uv run --with hypothesis ...` if not synced).

### 4.0 Static / structural gates (L0)
- **T18-0a** — static import scan: **no module under `qmb/src/qmb/data/`** imports or calls an
  ambient system-clock source (`datetime.now`, `datetime.utcnow`, `date.today`, `time.time`,
  `time.perf_counter`, …). **Pairs with T18-P1; expected FAIL — FIND-001.** *(RQ-CLOCK)*
- **T18-0b** — static: **no module-global mutable state** anywhere in `qmb/data/`. *(RQ34 / NFR-02, AR-11)*
- **T18-0c** — static/thin-front: `qmb/data/` declares **no second persistence store of its
  own** (no Parquet/DuckDB/SQLite/JSONL *writer* originating in `data/`); all persistence routes
  through the qmf-data contracts. *(RQ1 / B-11)*
- **T18-0d** — static: **no third-party downloader code is vendored** in `qmb/data/` (source/import
  scan for dukascopy-node-class vendored code); the adapter is QMX-authored. *(RQ3 / AR-54, DEC-0013)*
- **T18-2d** — packaging/release check (tier-2): the built wheel bundles **zero corpus bytes** —
  no market-data files in the distribution. *(RQ16 / AR-54)* **P0**

### 4.1 Targeted properties & units (L1)
- **T18-P1** — **[RQ-CLOCK / FIND-001]** injected-clock regression: with a clock injected into
  `data download`, `end`-defaults-to-today derives the frontier date **from the injected clock
  only**; observe via the injected clock/sink that no ambient wall-clock read occurs. **SHOULD
  FAIL against current source (`download.py:127`) — record as FIND-001, do not fix.** **P0**
- **T18-P2** — **[RQ8]** idempotence property: over arbitrary overlapping/duplicate windows, a
  second download with identical inputs writes **zero** duplicate CT-10 observations (dedup on
  `(source, source-native id, revision)`). *(hypothesis)*
- **T18-P3** — **[RQ6/RQ23]** money-path property: every price emitted to a CT-10 write / read by
  verify is an **exact scaled integer** and every timestamp is **int64 UTC-ns**; a
  provider-native float/decimal never crosses the boundary unconverted (the AD-22 conversion is
  named). *(hypothesis; the money-path-float negative)* **P0-adjacent**
- **T18-P4** — **[RQ14 / R-011]** license-gate totality: over the explicit taxonomy
  {redistribution-ok, internal-only, denied, unknown} **plus blank**, the gate is a **total
  function** to pass/refuse; blank resolves to `unknown` → refuse; no state is silently inferred
  by the adapter. *(hypothesis)* **P0**
- **T18-P5** — **[RQ27]** verify determinism: a re-run of verify over the **same immutable
  window** reproduces a **byte-identical** verdict/result. *(NFR-03)*
- **T18-P6** — **[RQ31]** gap-check determinism: re-running gap-check with the **same window +
  same CT-02 calendar version** yields the **identical gap set**, and the calendar version is
  recorded in the result. *(NFR-03)*

### 4.2 Component / integration (L2) — every AC
**Story 18.1 — download-once**
- **T18-1a** — **[RQ1]** `data download` composed over the CT-10/CT-15 seam adds no second
  persistence path: every write lands through the qmf-data CT-10 boundary (spy at the boundary),
  and `data/` holds no store of its own. **P1**
- **T18-1b** — **[RQ2]** the request is assembled from `(venue, symbol[list], start, end,
  resolution, side∈{bid,ask,both})` sourced from a Book/BMS fragment or invocation flags; an
  explicit `end` is honored verbatim (reproducible window).
- **T18-1d** — **[RQ3]** fetch flows through the QMX-authored provider-adapter port exposing
  exactly `fetch, earliest_available, list_symbols, count, rate-limit`; Dukascopy is adapter #1
  bound behind that port.
- **T18-1f** — **[RQ5]** bid and ask land as **two distinct streams**, never collapsed to one
  OHLCV. **P1**
- **T18-1i** — **[RQ8]** component idempotence: a second download with identical inputs over an
  overlapping window writes no duplicate observation (dedup observed at the CT-15 seam). **P0**
- **T18-1j** — **[RQ9]** `--overwrite` appends a **new CT-10 revision** (new revision token →
  new artifact) rather than mutating/overwriting the existing observation. **P1**
- **T18-1k** — **[RQ10]** a long import emits machine-observable progress events (percent,
  date-reached, ETA) to an **injected progress sink** — not only a human progress bar. *(seam, §7)*
- **T18-1l** — **[RQ12]** the data-read commands (list/verify/gap-check) reach **only qmf-data
  rooms** — no provider-adapter edge; `data download` is the sole module holding the provider
  port. *(run-loop policy-rejection half → Epic 14, §7)*
- **T18-1m** — **[RQ11 / R-011]** each ingested window records **provenance + a license tag** as
  CT-10 source-observation metadata (the input the 18.2 gate reads). **P0**

**Story 18.2 — licensing gate**
- **T18-2a** — **[RQ13 / R-011]** the gate returns **value-or-refusal**: a granting tag → pass
  (value); `denied`/`unknown`/absent → a CT-04 typed refusal for governed use carrying
  `(venue, symbol, window)` + tag state. **P0**
- **T18-2c** — **[RQ15]** an unlicensed Dukascopy window **still ingests and is catalogable**;
  non-evidence use (infra stress, strategy smoke) is allowed; governed-evidence citation is
  refused until a usage right is recorded. *(DEC-0170)* **P1**

**Story 18.3 — list catalog**
- **T18-3a** — **[RQ18]** `data list` reports, per `(venue, symbol, resolution, side)`, covered
  `[start,end]`, observation/bar count, provenance, license tag, current bitemporal revision.
- **T18-3b** — **[RQ19]** the catalog is a **rebuildable DuckDB view** over the Parquet rooms:
  dropping and rebuilding it loses no evidence; it is never an authoritative second store. *(AR-30)*
- **T18-3c** — **[RQ20]** an absent window returns an explicit "not present" **VALUE** (not a
  CT-04 refusal). **P2**
- **T18-3d** — **[RQ21]** both sides requested but only one present → the missing side is
  reported **absent** for that `(venue, symbol, resolution)`.

**Story 18.4 — verify**
- **T18-4a** — **[RQ23]** verify checks bid+ask both present where `both` requested, timestamps
  monotonic int64 UTC-ns, prices exact scaled integers no-float-taint, returning a typed result
  carrying counts + defects. **P1**
- **T18-4b** — **[RQ24]** the edge tolerance is a **configurable interface with no invented
  number**; a **blank** tolerance leaves the guard **un-armed** and verify reports raw edge
  offsets rather than passing/failing against a fabricated threshold. *(SC-07)* **P1**
- **T18-4d** — **[RQ26]** verify reports interior gaps and **never fills them**; a synthetic fill
  would be a `world=simulated` derived layer, never written as observed. *(seam, §7)*

**Story 18.5 — gap-check**
- **T18-5a** — **[RQ28/RQ31]** gap-check resolves expected sessions from a CT-02 versioned
  calendar, computes expected-minus-present bars per session, reports gaps as `(start, end,
  expected, present)`, and records the calendar version used. **P1**
- **T18-5b** — **[RQ29]** against a controlled calendar: an absent bar on a **closed** session →
  **real closure, not a gap**; an absent bar on an **open** session → **genuine gap**. **P0**
- **T18-5c** — **[RQ30]** a **24/7** venue on an always-open calendar → every non-present interior
  interval within an open window is a **genuine gap** (no closure exemption).
- **T18-5e** — **[RQ32]** gap-check only reports gaps and **never writes interior fill**; a
  fill request is a `world=simulated` `policy rejection` for governed evidence until GAP-0048.
  *(seam, §7)*

### 4.3 Contract conformance (L3) — every AC
- **T18-1e** — **[RQ4 / R-007]** a provider error (maintenance, geo-block HTTP-451-class, bad
  window, missing entitlement) → a **CT-04 typed refusal** (category + non-null context +
  retryability) rendered per transport; **no CT-10 observation written on the refusal path**
  (no silent partial ingest). *(AR-58)* **P0**
- **T18-1h** — **[RQ6/RQ7]** fetched ticks/bars are written as **CT-10 bitemporal source
  observations** (event_time, known_at, source, source_native_id, revision, bid/ask scaled-int,
  world) into the world-scoped raw room (CT-11), shape-conformant. **P1**
- **T18-2e** — **[RQ17]** on a passing window, the license tag + **granting authority** are
  emitted as a **CT-07 lineage-edge** payload and the gate **writes nothing** (pure read-time).
  *(downstream ride into a run's citation → Epics 14/19, §7)* **P1**
- **T18-3e** — **[RQ22]** door-parity contract test (tier-2): the same catalog query through the
  **CLI** door and the **Python API** door returns a **byte-identical machine-readable payload**;
  the CLI renders it, the Python door returns it verbatim. *(B-1, AR-58)* **P1**
- **T18-4c** — **[RQ25 / R-007]** a verify defect (edge beyond an armed tolerance, requested side
  missing, non-integer price taint, empty provider return) → a **CT-04 typed refusal** with
  machine-readable context, **never a silent pass**. **P0**
- **T18-4e** — **[RQ27]** the verify verdict is journaled as a **CT-13 data-quality event**
  (never an edge/verdict-bearing claim) with a propagated `correlation_id`. *(AR-35)* **P1**
- **T18-5f** — **[RQ33 / R-007]** a missing or unresolvable calendar for `(venue, symbol)` → a
  CT-04 **`unavailable dependency`** typed refusal — never a silent always-open guess. **P0**
- **T18-6a** — **[RQ34]** every refusal on an Epic-18 path is a valid **CT-04** value: category ∈
  the seven, context present (non-null), retryability present — **RETURNED** across the public
  boundary, never raised. (folds the refusal-shape half of RQ4/RQ13/RQ25/RQ33.) **P0**

### 4.4 Golden scenario (L4)
- **T18-6b** — **[golden]** a data-lifecycle walk over a small controlled corpus: **download**
  a window (injected clock, licensed tag) → **list** shows it with its tag + revision →
  **verify** returns a typed pass → **gap-check** against a controlled calendar classifies
  closure-vs-gap deterministically. **No `SCN-*` exists for data management** — this is a
  *proposed* scenario binding, recorded in §7.4.

### 4.5 Adversarial review (L6)
- **T18-L6** — adversarial deep review of `qmb/data/` producing `L6-REVIEW.md`, scoped to the
  **3 CRITICAL complexity loci** (download orchestration, verify integrity, gap-check
  classification), the **refusal-honesty surface** (R-007), and the **license-gate fail-closed
  surface** (R-011). Confirms each critical branch maps to an assertion in §4.1–§4.3 and hunts
  the leaks coverage cannot see (a silent partial ingest, a mis-defaulted edge tolerance, a
  closed-vs-gap inversion, an ambient nondeterminism beyond FIND-001).

---

## 5. Test-level allocation (L0–L6; one behaviour one level, lower level wins)

Reconstructed taxonomy (test-design-qa.md absent, §1). **L6 = the review level** (each audited
epic ships an `L6-REVIEW.md`). Rule enforced: **one behaviour, one level; the lowest level that
can meaningfully assert it wins** — no behaviour is re-asserted higher except where a property
adds breadth a component case cannot (flagged). **T2 tier scope = L2 + L3 for every AC, targeted
L1 properties, an L6 review.**

| Level | Definition here | Execution band | Epic-18 tests | Count |
|---|---|---|---|---|
| **L0** | Static / structural gates on source: ambient-clock import scan, no module-global mutable state, thin-front (no second store), no vendored downloader, zero-corpus packaging. | lint/type + tier-2 packaging | T18-0a, T18-0b, T18-0c, T18-0d, T18-2d | **5** |
| **L1** | Targeted unit / property — one pure function or one law, injected inputs, deterministic, no network. | tier-1 (`poe check`) / `--with hypothesis` | T18-P1, T18-P2, T18-P3, T18-P4, T18-P5, T18-P6 | **6** |
| **L2** | Component / integration in-process — `data` command wired through the CT-10/CT-15 seam, the rooms/DuckDB view, a controlled calendar, and the doors, with fakes; no OS process. | tier-1/2 | T18-1a,1b,1d,1f,1i,1j,1k,1l,1m, 2a,2c, 3a,3b,3c,3d, 4a,4b,4d, 5a,5b,5c,5e | **22** |
| **L3** | Contract conformance — CT-04 refusal shape, CT-10 observation shape, CT-07 lineage, CT-13 data-quality journal, door-parity payload identity. | **tier-2** (`poe check-integration`) | T18-1e,1h, 2e, 3e, 4c,4e, 5f, 6a | **8** |
| **L4** | Golden scenario — the download→list→verify→gap-check lifecycle walk (proposed SCN). | tier-2 | T18-6b | **1** |
| **L5** | System / orchestrated (process-per-run, ledger) — **none in Epic 18** (Epic 15). | — | — | 0 |
| **L6** | Adversarial review of the 3 critical loci + R-007/R-011 surfaces → `L6-REVIEW.md`. | review pass | T18-L6 | 1 (review) |

**Planned counts — L0: 5 · L1: 6 · L2: 22 · L3: 8 · L4: 1** (executable total **42**), plus the
**L6** review pass. Every one of the 34 RQs has at least one **L2 or L3** test (T2 scope
satisfied); the 6 L1 properties are the targeted-property allocation; the 5 L0 gates back them.

**Lower-level-wins applications:**
- Idempotence is asserted once at **L2** (T18-1i, concrete dedup at the seam) with an **L1**
  property (T18-P2) for breadth — not a duplicate concrete case.
- The exact-integer/int64-ns money-path law is an **L1** property (T18-P3) covering both download
  (RQ6) and verify (RQ23); the CT-10 *write shape* that carries it is asserted once at **L3**
  (T18-1h), not re-asserted per command.
- The **triggering** behaviour of each refusal (provider error, verify defect, unresolvable
  calendar) sits at **L2/L3** with the command; its CT-04 *shape* is folded **once** into T18-6a.
- The ambient-clock invariant is proven negatively by the **L0** import scan (T18-0a) **and** the
  **L1** behavioural regression (T18-P1) together — the static gate proves absence of the import,
  the behavioural test proves the injected clock is actually used.

---

## 6. Fixtures, data and determinism harness

- **Runner:** `uv run pytest qa/tests/epic_18 -q` from the worktree root (dev group synced);
  properties `uv run --with hypothesis ...`; the door-parity and zero-corpus checks in the
  project's tier-2 (`poe check-integration`) band. **All tests live under `qa/`**; source is
  read-only. A failing test is a **finding** recorded in this epic's findings artifact, never a
  reason to edit `qmb/data/` source or soften an assertion.
- **Controlled corpus (test evidence only — DEC-0007; never product market data):** a small,
  fully-declared multi-window tick/bar fixture with known `(venue, symbol, resolution, side)`
  coverage, a deliberate **interior gap**, a **missing-side** window, a **float-taint** row (to
  trip verify), and a **duplicate/overlapping** window (to trip idempotence). Checked into
  `qa/`, never fetched from a provider at test time (B-11 download-once).
- **Provider-adapter fake:** an in-memory adapter implementing the QMX port
  (`fetch, earliest_available, list_symbols, count, rate-limit`) with scripted **error arms** —
  maintenance, geo-block (HTTP-451-class), bad window, missing entitlement, empty return — for
  T18-1e / T18-4c. A **recorded controlled replay** (fixtures-lens "external controlled replay"
  class), never a live Dukascopy call, never a test of provider internals.
- **Injected clock (the FIND-001 harness):** a CT-02 clock (int64 UTC-ns) injected at the
  composition root; T18-P1 asserts `end`-defaults-to-today reads it, and T18-0a asserts no
  `data/` module reads the system clock. **The clock is the single most load-bearing fixture in
  this plan** — it is how the confirmed defect is observed rather than argued.
- **License-tag policy fixture:** a per-venue policy record exposing the explicit interface
  {redistribution-ok, internal-only, denied, unknown} **plus a blank/un-ruled entry**; tags are
  **resolved from this record, never invented literals** (SC-07). T18-P4 sweeps every state.
- **Controlled CT-02 calendars:** (a) a calendar with a **closed day** (weekend/holiday) and (b)
  an **always-open 24/7** calendar, each carrying a declared **version**; plus an
  **unresolvable/absent** calendar for T18-5f. Gap-check determinism (T18-P6) pins the same
  version across re-runs.
- **CT-10 / CT-04 / CT-07 / CT-13 fakes are shape-faithful** to the ratified contracts (fields,
  unit-kinds, the seven refusal categories, non-null context, retryability) — a test that passes
  against a shape-unfaithful fake is itself a finding.
- **Determinism rules (fixtures-and-scenarios.md / DEC-0106):** no network below the root; time
  is the injected CT-02 clock; property fixtures **declare their seed**; equal semantic inputs
  replay to equal CT-05 `fp1` via the single qmf-core implementation, floats refused in identity.
  Run the properties under `PYTHONHASHSEED` variation to catch dict/set-ordering leaks.
- **Refusal harness (T18-6a):** every "is refused" assertion checks a **RETURNED** CT-04 value
  (one arm of a result union) with the correct category and non-null context — **never a raised
  exception across a public boundary** — and asserts the **absence of prohibited side effects**
  (no CT-10 write on a refusal path, no journal line, no second store).
- **Values are referenced, never restated:** the license taxonomy and the edge tolerance are
  **interfaces** (policy record / registry key), never invented numbers; a blank tolerance is
  **un-armed** and a blank tag is **unknown** — the tests assert the interface and the
  fail-closed default, not a fabricated threshold (SC-07).

---

## 7. Untestable / deferred / blocked requirements

### 7.1 RQ12 run-side — DEFERRED to Epic 14 (seam only here)
"A run that attempts a provider fetch is a `policy rejection`" fires inside the run loop, which
is Epic 14. Epic 18 tests only the **data-command side**: `data download` is the sole module
holding the provider port, and list/verify/gap-check reach only rooms (T18-1l). The run-loop
refusal is recorded as an Epic-14 assertion, not an Epic-18 coverage gap.

### 7.2 RQ17 downstream half — DEFERRED to Epics 14/19 (seam only here)
The license tag + granting authority **riding into a citing artifact's CT-07 lineage** requires
a governed-evidence artifact (a run's CT-32 / ledger citation), minted downstream. Epic 18 tests
the **gate side**: it produces the tag + authority as a lineage-ready payload and **writes
nothing** (T18-2e). The ride-into-a-run's-citation is an Epic-14/19 assertion.

### 7.3 RQ26 / RQ32 synthetic-fill content — GAP-0048 / Epic 23 (refusal seam only)
Producing a **filled series** is Epic 23 synthetic territory, `world=simulated`, a `policy
rejection` for governed evidence until GAP-0048 ratifies simulated-time typing (SC-06/B-7).
Epic 18 tests only the **refuse-to-fill seams** (T18-4d, T18-5e): verify/gap-check report gaps
and never write fill. The *content* of a synthetic fill is not asserted here — asserting it
would test an unratified value.

### 7.4 No `SCN-*` for data management — proposed binding, not a ratified scenario
The golden walk T18-6b is a **proposed** scenario (download→list→verify→gap-check); no
`docs/scenarios/SCN-*` covers data acquisition (the existing SCN-0001..0012 cover core, registry,
data-store seal, venue, risk, and the QMB replay run — none the data commands). Recorded as a
scenario gap; the walk executes as an L4 integration case, not as a ratified golden scenario,
until an `SCN-*` is authored.

### 7.5 RQ10 progress channel — PARTIAL (injected sink here; real agent channel downstream)
The **machine-observable progress events** (percent, date-reached, ETA) are testable against an
**injected sink** (T18-1k). Their transport to a *real supervising-agent channel* is a
door/orchestrator concern (Epic 15/16); only event emission + shape is asserted in Epic 18.

### 7.6 Real FX-session calendar content — Epic 4 (controlled fixtures here)
gap-check consumes the **qmf-calendar-forex** provider (Epic 4) read-only. Epic 18 tests the
**closed-vs-gap decision logic** against **controlled CT-02 calendar fixtures** (closed-day,
24/7, unresolvable); the correctness of the *real* FX session data is Epic 4's, not asserted here.

### 7.7 Cross-door full parity — Epic 16 (data-catalog payload only here)
Full parity across the entire `qmb` command surface is Epic 16's tier-2 contract test. Epic 18
asserts parity only for the **data catalog payload** (T18-3e).

### 7.8 PLAN-INTEGRITY CAVEAT — named authorities absent (recorded finding)
`test-design-qa.md` and `QMX-handoff.md` are absent (§1). The 8-section template, the L0–L6
taxonomy, and the P0/P1 ladder are reconstructed; **R-007, R-011, the T2 tier scope, and
FIND-001** are taken from the task brief. When the files are restored, reconcile §1/§3/§5. This
is a finding, recorded, not worked around.

---

## 8. Exit criteria and coverage ledger

The epic's verification passes when:

1. **Every RQ in §2 maps to at least one executed test in §4**, and every §4 test has a
   recorded **PASS**, **FINDING**, or **DEFERRED** (a FINDING is a requirement the source does
   not satisfy — never resolved by editing source or weakening the test).
2. **FIND-001 is executed and recorded:** T18-P1 (+ T18-0a) run against current source, **fail
   as predicted**, and the failure is filed as FIND-001 (ambient `datetime.now()` at
   `download.py:127`; FR-002 / CT-02 / AR-16 + 18.1-AC2 reproducible-window). **Source is not
   fixed by this audit.**
3. **Risk gates satisfied (all P0 green except the knowingly-failing FIND-001 regression):**
   - **R-007** — T18-1e, T18-4c, T18-5f, T18-6a all PASS (every adversarial/malformed input
     refuses with a returned CT-04 value; no silent partial ingest, no silent pass, no
     always-open guess).
   - **R-011** — T18-1m, T18-2a, T18-P4, T18-2c, T18-2e all PASS (every window carries a license
     tag; the gate passes a granting tag and refuses denied/unknown/**absent**; blank ⇒ unknown ⇒
     block; the gate writes nothing).
4. **L0 gate green** (except T18-0a, the FIND-001 pair): no module-global mutable state
   (T18-0b), no second store in `data/` (T18-0c), no vendored downloader (T18-0d), **zero corpus
   bytes in the wheel** (T18-2d).
5. **T2 scope met:** every AC has an executed **L2 or L3** test; the 6 **L1 properties** and the
   **L6 review** (`L6-REVIEW.md`) are complete, the review confirming each of the 3 CRITICAL
   complexity loci's critical branches maps to a §4 assertion.
6. **Determinism proven:** T18-P5 (verify) and T18-P6 (gap-check) PASS under `PYTHONHASHSEED`
   variation; the gap-check result records its CT-02 calendar version.
7. **Deferred items (§7) are explicitly recorded as deferred**, each with its owning epic — none
   silently counted as passed, none silently counted as failed.

Coverage ledger to be maintained alongside execution in
`qa/epics/epic_18_qmb-data-management/` — one row per §4 test id → {level, priority,
status PASS/FINDING/DEFERRED, evidence path}, plus `findings.csv` (FIND-001 seeded) and
`RESULTS.md`.

| RQ | Test id(s) | Prio | Level(s) | Status |
|---|---|---|---|---|
| RQ-CLOCK/FIND-001 | T18-P1, T18-0a | P0 | L1,L0 | planned — **expected FINDING** |
| RQ1 | T18-1a, T18-0c | P1 | L2,L0 | planned |
| RQ2 | T18-1b | P2 | L2 | planned |
| RQ3 | T18-1d, T18-0d | P2 | L2,L0 | planned |
| RQ4 | T18-1e | P0 | L3 | planned **[R-007]** |
| RQ5 | T18-1f | P1 | L2 | planned |
| RQ6 | T18-P3, T18-1h | P1 | L1,L3 | planned |
| RQ7 | T18-1h | P1 | L3 | planned |
| RQ8 | T18-1i, T18-P2 | P0 | L2,L1 | planned |
| RQ9 | T18-1j | P1 | L2 | planned |
| RQ10 | T18-1k | P2 | L2 | planned (seam §7.5) |
| RQ11 | T18-1m | P0 | L2 | planned **[R-011]** |
| RQ12 | T18-1l | P2 | L2 | planned (run half → Epic 14 §7.1) |
| RQ13 | T18-2a, T18-6a | P0 | L2,L3 | planned **[R-011]** |
| RQ14 | T18-P4 | P0 | L1 | planned **[R-011]** |
| RQ15 | T18-2c | P1 | L2 | planned |
| RQ16 | T18-2d | P0 | L0 | planned |
| RQ17 | T18-2e | P1 | L3 | planned (downstream → Epics 14/19 §7.2) |
| RQ18 | T18-3a | P2 | L2 | planned |
| RQ19 | T18-3b | P1 | L2 | planned |
| RQ20 | T18-3c | P2 | L2 | planned |
| RQ21 | T18-3d | P2 | L2 | planned |
| RQ22 | T18-3e | P1 | L3 | planned |
| RQ23 | T18-4a, T18-P3 | P1 | L2,L1 | planned |
| RQ24 | T18-4b | P1 | L2 | planned |
| RQ25 | T18-4c | P0 | L3 | planned **[R-007]** |
| RQ26 | T18-4d | P2 | L2 | planned (seam §7.3) |
| RQ27 | T18-4e, T18-P5 | P1 | L3,L1 | planned |
| RQ28 | T18-5a | P1 | L2 | planned |
| RQ29 | T18-5b | P0 | L2 | planned |
| RQ30 | T18-5c | P1 | L2 | planned |
| RQ31 | T18-P6, T18-5a | P1 | L1,L2 | planned |
| RQ32 | T18-5e | P2 | L2 | planned (seam §7.3) |
| RQ33 | T18-5f | P0 | L3 | planned **[R-007]** |
| RQ34 | T18-6a | P0 | L3 | planned |
| golden | T18-6b | — | L4 | planned (proposed SCN §7.4) |
| review | T18-L6 | — | L6 | planned → `L6-REVIEW.md` |
