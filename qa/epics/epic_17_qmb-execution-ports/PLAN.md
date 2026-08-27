# Verification PLAN — Epic 17: QMB fill/slippage/fee/financing ports

**Audit tier:** T2 (high scrutiny — evidence-honesty epic; execution modeling whose taint gates every downstream edge claim).
**Package under test:** `qmb/src/qmb/execution/` (fill / slippage / cost ports + financing scheduler + adapters + the port-set binder; the synthetic-spread model that feeds the Book's SQS door). Seams into `qmb/src/qmb/runloop/` (sub-phases 2 and 3 call-points, Epic 14), `qmb/src/qmb/config/` (resolved run-config, Epic 13), `qmb/src/qmb/results/` (CT-32 label, Epic 19).
**Delivers:** FR-044 (fidelity-labeled fill/slippage/fee/financing). Stories 17.1–17.5.
**Governing invariant:** QMB spine **B-6** (separate pinned fill→slippage→cost ports + financing scheduler; CT-23 authorized intent in, never bot-sized; partial fills first-class; fidelity = adapter-id + composition-version + taint; run fidelity is LOWEST-wins; every non-live fill `optimistic`-tainted until GAP-0048; calibration-not-invention per DEC-0135). Supporting: **B-7** (provenance-derived world), **B-2** (the sub-phase-2/3 call-points the ports execute against, owned by Epic 14), **B-10/B-13** (CT-32 label carries the fidelity + calibration fingerprints), **AR-56** (ports execute, never re-size), **AR-59** (identity/fidelity in the label).

> **PROCESS GAP (read first).** Two authorities named in the audit brief **do not exist in this worktree**:
> `_bmad-output/test-artifacts/test-design-qa.md` (the Per-Epic Test Plan Template + the L0–L6 test-level architecture) and
> `_bmad-output/test-artifacts/test-design/QMX-handoff.md` (the 15 P0/P1 assertions + this epic's risk-gate rows, including the row referenced in the brief as **R-011**).
> Confirmed absent by full-tree search (only `archive/recovery/*/restart-handoff.md` and the backtesting-spec files match). The whole `_bmad-output/test-artifacts/` directory is absent.
> **Consequence:** the 8-section structure and the L0–L6 taxonomy (§5) are **reconstructed** from the sibling Epic-14 PLAN (the nearest QMB template) and this project's own vocabulary (test-tier-2 = `poe check-integration`; "one behaviour, one level; lower level wins"). The priority ladder (§3) and the **R-011** interpretation are **derived from the ratified spine (B-6/B-7) + the Epic-17 ACs + the fill/fees source spec**, not transcribed from the missing handoff. When the two files are restored, re-reconcile §1 template order, §3 risk-gate rows (esp. R-011), §5 level definitions, and the P0/P1 set against them before executing.

---

## Section 1 — Epic Context, Scope & Authorities

**What this epic is.** Fidelity-labeled execution modeling behind SEPARATE pinned ports. Inbound is a CT-23 Book-resolved *authorized* intent (or a typed refusal) — the ports execute it, they never size it. Execution is composed from the resolved run-config in a pinned order: **(1) fill** decides `Fill | NoFill | PartialFill` and a **pre-slip** price by honest crossing of each slice's declared intra-slice path (partial quantities first-class, capped by position size and lot step); **(2) slippage** maps pre-slip → post-slip and may veto the fill if the slipped price is not a legal print; **(3) cost** itemizes commission as exact-integer money in its own currency. **Financing** is a separate scheduled position-level cash event applied at the per-broker AD-8 accounting rollover (run-loop sub-phase 2), never an order fill. A **synthetic-spread model** supplies calibrated bid/ask when the feed carries no quotes and exposes this run's modeled-spread series to the Book's SQS door. Every fill carries the `optimistic` taint and every calibration parameter comes from a versioned, fingerprinted per-broker artifact measured from QMX's own recorded evidence — **calibration, never invention (DEC-0135)** — with all fidelity ordinal values and calibration content deferred to **GAP-0048**.

**In scope (Stories 17.1–17.5):**
- **17.1** port-set binder + fidelity identity: three separate ports + financing scheduler bound from config in pinned order; CT-23 inbound guard; AD-40 full-loss precondition; fidelity identity (adapter-id + composition-version + taint); lowest-wins aggregation + mixed-fidelity comparison refusal; world derivation + GAP-0048 gating.
- **17.2** synthetic-spread model + SQS input: bid/ask keyed by instrument × hour × session from a fingerprinted calibration artifact; absent-artifact refusal; real-quote precedence; SQS-door modeled-spread series in exact `Price`; calibration fingerprint in the label.
- **17.3** fill + slippage price-forming pipeline: `Fill|NoFill|PartialFill` + pre-slip price dispatched per order type; bar-worst-case default with a labeled optimistic-exact mode; partial fills capped by size/lot-step with per-partial fee; stale-data guard, gap fills, typed NoFill reasons; deterministic intra-slice sequencing + new-intents-rest; slippage map/veto with per-run-seeded stochastic draw.
- **17.4** cost port: typed fee in own currency as exact-integer `Money`, no float on the money path; per-fill / per-partial itemization as a distinct line item; calibration-parameterized commission shapes; double-call (admission + charge) determinism; absent-calibration refusal.
- **17.5** daily-swap financing: scheduled position-level cash event at the AD-8 rollover, per instrument × direction; triple-swap + weekend/holiday from a calendar-scheduled artifact; absent-swap-table refusal; distinct CT-13 journal event + cost-drag decomposition; fidelity fingerprint in the label + GAP-0048 gating.

**Out of scope (owned elsewhere; Epic 17 tests only its ports' COMPLIANCE at the seam — see the Epic-Binding Rule below):**
- **The six-sub-phase run loop, the frontier clock, forming-bar non-actionability, and the provenance→world derivation itself** → **Epic 14 (B-2/B-7)**. Epic 17 executes against sub-phase-2 (financing) and sub-phase-3 (resting-order fill) call-points and honors the "new intents rest" rule, but the loop machinery and world-derivation logic are Epic 14's. `world=simulated` *derivation* is Epic 14; Epic 17 asserts the port-set *refuses to compose* for it.
- **The CT-23 door's own sizing / full-loss derivation / risk-monotonic exit logic (FR-032)** → **Epic 10 (qmf-risk)**. Epic 17 asserts the ports *admit only* a Book-resolved authorized intent and *require* a full-loss price before an open — the inbound guard — not how the Book resolves them.
- **Exact-integer money/price/quantity arithmetic and the AD-22 conversion boundary (FR-001, CT-01)** → **Epic 1 (qmf-core)**. Epic 17 asserts no float touches its money path and its outputs are exact `Money`/`Price`; it does not re-test core arithmetic.
- **The CT-32 assembly, the AR-59 label writer, and split-budget enforcement** → **Epic 19 / Epic 14 / qmf-data (CT-12)**. Epic 17 asserts its fidelity identity + calibration fingerprints are *present for* the label and the taint marks the run non-edge-claiming; the artifact assembly and the actual split-budget-spend refusal are downstream.
- **The fidelity taxonomy ordinal values, the calibration *content* (actual spread/slippage/fee/swap numbers), and the `world=simulated` unlock** → **GAP-0048**. Only the *seam*, the `optimistic` taint, the *relative* precedence (real > synthetic), the calibration-artifact-is-fingerprinted-and-consumed fact, and the absence-refuses behavior are testable now (see §8 untestable list).

**Two senses of "tier" (do not conflate).** *Audit tier* **T2** = this plan's scrutiny level. *Test tier* **tier-2** = the project's `poe check-integration` band that the contract-level (L3) and property (L6) tests run in. §5 maps our L0–L6 onto those bands. **T2 tier scope (from the brief):** L2 + L3 for every AC, targeted L1 properties/units for pure sub-computations, L6 review. No L4 scenario or L5 system tests are *owned* by Epic 17 (the end-to-end golden run is Epic 14/19's SCN-0012; Epic 17 contributes adapters to it — see §8).

**Authorities, in precedence order:**
1. Epic 17 section of `_bmad-output/planning-artifacts/epics.md` (Stories 17.1–17.5, ACs; FR-044).
2. `docs/` knowledge base: `docs/components/qmb.md` (§ "Execution ports, fidelity, and calibration-not-invention (B-6)", § "Provenance-derived worlds (B-7)", § result-artifact/CT-32); `docs/contracts/` — `ct-01` (exact-integer money/price/quantity, money-path taint, no float), `ct-04` (seven typed-refusal categories, returned-not-raised), `ct-13` (seven journal event types), `ct-23` (authorized intent, Book-resolved `requested_r`, full-loss-required-before-open, risk-monotonic exits, `close_partial` not-V1), `ct-29` (exit record), `ct-32` (full AD-12 label + fidelity identity + world); `docs/scenarios/SCN-0012-qmb-replay-run.md` (the golden replay run Epic 17's adapters plug into).
3. `_bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md` (B-6 verbatim rule; B-7; AR-56/AR-59; AD-8 rollover; AD-40 full-loss).
4. `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/research-backtesting/specs/spec-fill-fees.md` — the reverse-engineering source spec that DEFINES the FILL-1..8 / SLIP-1..3 / SPREAD-1..2 / FEE-1..5 / LABEL-1..3 requirement families the ACs cite; feeds GAP-0048.
5. *(Missing — see Process Gap)* test-design-qa.md; QMX-handoff.md.

**Epic-Binding Rule (confirmed).** Epic 17 owns **FR-044 only**. Every requirement below traces to an Epic-17 AC. Cross-cited FRs — FR-032 (Epic 10), FR-001 (Epic 1), FR-036/037 sub-phase order (Epic 14), FR-043 CT-32 assembly (Epic 19) — appear only as **inbound contracts the ports must honor**, tested at Epic 17's seam (does the port *comply*), never as behaviours re-owned here.

---

## Section 2 — Requirements → Behaviours Traceability

Every row is a testable behaviour extracted from a ratified source, stated as an assertion. IDs feed the independent test list (§4) and the matrix (§8). "Ref" cites the governing AC + spine/spec/contract.

| # | Behaviour (requirement, as an assertion) | Ref | Story/AC |
|---|---|---|---|
| R1 | The binder composes exactly THREE separate ports — fill, slippage, cost — plus the financing scheduler, each resolved by adapter-id, in the pinned composition order **fill → slippage → cost**. | AR-56, B-6, FILL/SLIP/FEE | 17.1/AC1 |
| R2 | Binding happens ONLY from the resolved read-only config — never by ambient discovery or a code change; changing the bound set requires a config change. | B-3, B-1, B-6 | 17.1/AC1 |
| R3 | An inbound request that is not a CT-23 Book-resolved authorized intent (e.g. a raw bot-sized order) returns a typed CT-04 refusal and **no port executes**. | CT-04, CT-23, AR-56 | 17.1/AC2 |
| R4 | A well-formed CT-23 authorized intent is admitted unchanged — the ports execute it and **never re-size** it (Book-resolved `requested_r` preserved). | AR-56, B-6, CT-23 | 17.1/AC2 |
| R5 | An intent that opens or increases a position with **no AD-40 full-loss price** → the fill port is not invoked and a typed CT-04 refusal is returned **before any open**. | AR-56, B-3, AD-40, CT-23 | 17.1/AC3 |
| R6 | A risk-reducing CT-29 exit intent is admitted **without** requiring a new full-loss price. | FR-032, CT-29 | 17.1/AC3 |
| R7 | The fidelity identity of any bound adapter is exactly **(adapter-id + composition-version + taint)**; `taint = optimistic` for every non-live fill until GAP-0048; the taint is a field, never part of the identity tuple. | B-6, SC-06, AR-59 | 17.1/AC4 |
| R8 | The **composition-version** changes whenever the bound port set OR its order changes — identity never silently drifts. | B-6, AR-59 | 17.1/AC4 |
| R9 | A run's fidelity is the **LOWEST** fidelity of any bound adapter (lowest-wins fold). | B-6 | 17.1/AC5 |
| R10 | Comparing two Book-bar results of differing fidelity **without an explicit override** returns a typed CT-04 refusal; no ordinal fidelity values are invented (the ordering taxonomy is a deferred artifact). | LABEL-3, B-6, SC-07 | 17.1/AC5 |
| R11 | Composing the port-set for `world=simulated` is refused, and a config binding a replay clock to synthetic-tainted data is `invalid input`. | B-7, SC-06 | 17.1/AC6 |
| R12 | Every optimistic-tainted run is barred from spending split budget and from any edge/verdict claim until GAP-0048 (the run's claim-class gate). | SC-06, B-6, FM-9 | 17.1/AC6 |
| R13 | With trade-only bars, the spread model supplies bid/ask keyed by **instrument × hour-of-day (UTC) × session** from its bound calibration artifact; it **never** returns an equal buy/sell price silently — an absent spread source is surfaced, not zeroed. | SPREAD-1, FILL-3 | 17.2/AC1 |
| R14 | The spread calibration artifact is versioned + fingerprinted per-broker (DEC-0135), its content measured from QMX's own recorded bid/ask ticks (deferred to GAP-0048); an unbound artifact → typed CT-04 refusal, never a silent zero; no spread constant is embedded in code. | DEC-0135, B-6, CT-04, SC-07 | 17.2/AC2 |
| R15 | When the feed carries real quotes, the real spread **takes precedence** over the synthetic model, and the run is recorded at a **higher** price-basis fidelity than a synthetic-spread run (ordinal deferred). | SPREAD-2, B-6, SC-07 | 17.2/AC3 |
| R16 | The Book's SQS door (AD-39) consumes this run's modeled-spread series as its spread input, and the series cites exact `Price` values, never binary floats. | B-2, CT-01, FR-001 | 17.2/AC4 |
| R17 | A run that bound the synthetic-spread model declares the spread calibration artifact fingerprint in the CT-32 label. | B-10, B-13, AR-59 | 17.2/AC5 |
| R18 | The fill port returns `Fill|NoFill|PartialFill` and, on a fill, a pre-slip price by crossing the declared path, **dispatched per order type** (market, limit, stop, stop-limit, trailing-stop, market-on-open, market-on-close, all-or-none group), evaluated in sub-phase 3; an all-or-none group in which any leg fails → NoFill for the whole group. | FILL-2, B-6, B-2 | 17.3/AC1 |
| R19 | The default fill price is **bar-worst-case** (buy limit=`min(high,limit)`; sell limit=`max(low,limit)`; stop=worst of stop vs current±slip); an optimistic-exact mode fills at the exact order price but stamps a **distinct fill-basis** in the fidelity label; both modes remain `optimistic`-tainted until GAP-0048. | FILL-4, SC-06, B-6 | 17.3/AC2 |
| R20 | A PartialFill emits `filled_qty < order_qty`, caps a `reduce_only` fill to the open position size, and rounds to the instrument lot step; **each partial emits its own `Fill` carrying its own pro-rated fee reference**. | FILL-8, B-6 | 17.3/AC3 |
| R21 | The stale-data guard returns a typed NoFill with a reason code from `{market_closed|stale_data|not_triggered|insufficient_liquidity|all_or_none_leg_failed}` (resting order whose bar end precedes submission, or market order beyond `stale_price_span`); an order in a between-bar gap fills at the gapped price with a `gap_fill` marker, not skipped. | FILL-1, FILL-5, FILL-7 | 17.3/AC4 |
| R22 | Several resting orders inside one slice fill in a **deterministic** order derived by splitting the declared path at each fill price, reproducible without tick data; an intent newly minted in sub-phase 5 is **not eligible** to fill against this slice's path — it rests for a later slice. | FILL-6, B-2 | 17.3/AC5 |
| R23 | Slippage maps pre-slip → post-slip (buy `+`, sell `−`) using the config-selected FX model `{zero|constant-percent|spread-crossing|gap-volatility|size-tiered}`, each parameterized by its calibration artifact (no invented numbers); it may **veto** the fill (NoFill) when the slipped price is not a legal print; it is **not** applied to passive limit fills unless configured; any stochastic term draws from a **per-run seed derived from run identity** so replay reproduces the same draw. | SLIP-1, SLIP-2, SLIP-3, SC-07, B-13 | 17.3/AC6 |
| R24 | The cost port returns a typed fee in **its own currency** mapped to exact-integer `Money`; **no float commission rate ever touches the money path**. | CT-01, FEE-1, FR-001 | 17.4/AC1 |
| R25 | Each partial carries its own **pro-rated** commission itemized separately; commission is a **distinct line item, never folded into fill P&L**. | B-6, FILL-8, FEE-5 | 17.4/AC2 |
| R26 | The commission shape is one of `{zero|percent-of-notional|per-lot/per-1k-units|notional-proportional-with-per-order-minimum}`, each parameterized by a versioned per-broker calibration artifact (DEC-0135); no rate is invented (content deferred to GAP-0048). | FEE-2, DEC-0135, SC-07 | 17.4/AC3 |
| R27 | **Double-call determinism:** the fee queried before the fill (margin/buying-power admission) and again at fill time returns the **identical** amount; a fee queried for admission whose fill does not occur charges nothing. | FEE-3 | 17.4/AC4 |
| R28 | A commission model whose calibration artifact is missing → typed CT-04 refusal, **never a silent zero** commission. | FEE-1, B-6, CT-04 | 17.4/AC5 |
| R29 | Financing applies at the per-broker **AD-8 accounting rollover** (never hardcoded), in sub-phase 2, as an exact-integer `Money` debit/credit to **each open position** — not an order fill — **per instrument and per direction** (long/short); applied at the rollover, not per slice. | AR-56, B-6, FEE-4, AD-8, B-2 | 17.5/AC1 |
| R30 | Triple-swap day and weekend/holiday handling are honored from the **bound calendar-scheduled per-broker swap-schedule artifact**; swap points, the sign convention (carry may be a **credit**), and the triple-swap weekday are read from the artifact, **never invented**. | FEE-4, DEC-0135, SC-07 | 17.5/AC2 |
| R31 | An open multi-day position whose instrument has **no bound swap table** → typed CT-04 refusal at rollover, **never a silent zero** swap. | FEE-4, CT-04 | 17.5/AC3 |
| R32 | A swap is emitted as a **distinct CT-13 journal event**, separate from fill P&L, slippage cost, and commission; the result artifact decomposes total cost drag into fill P&L, slippage, commission, and financing as **separately attributable** line items. | FEE-5, B-4, B-10 | 17.5/AC4 |
| R33 | A run that applied financing declares the financing calibration fingerprint in the CT-32 label and remains `optimistic`-tainted, barred from edge claims and split-budget spend until GAP-0048. | B-10, B-13, AR-59, SC-06, B-6 | 17.5/AC5 |

---

## Section 3 — Risk Assessment, Weak Spots & Priority

**Highest-value risk theme.** Epic 17 is where a backtest can *quietly lie*. Every failure mode here is a **silent flattering of results**: a dropped taint, a silently-zeroed spread/fee/swap, an invented constant standing in for a missing calibration, or an optimistic exact-wick fill masquerading as reality. None of these throws — they produce a *number that looks real*. The audit's entire posture is: **absence must refuse, taint must propagate, and no constant may be invented.** Four properties carry that spine:

1. **Taint propagation & lowest-wins (R7/R9/R10/R12/R33).** If a port-set can compose in a way that drops the `optimistic` taint or reports a fidelity higher than its lowest adapter, an unvalidated run can claim edge or spend split budget. **P0.**
2. **Calibration-absence refuses, never zero (R14/R28/R31, and R13's non-silent-buy=sell).** A missing spread table, fee artifact, or swap table must be a typed CT-04 refusal. A silent zero is the exact backdoor DEC-0135 ("calibration, never invention") exists to close. **P0.**
3. **CT-23 authorized-intent + AD-40 full-loss inbound guard (R3/R4/R5).** The ports must execute only a Book-resolved authorized intent and never open without a full-loss price — a bot-sized order or a stopless open reaching a port inverts the `bot → Book → BMS → operator` authority order. **P0.**
4. **Worst-case honesty + exact-integer money (R19/R24/R27).** The default fill must be bar-worst-case (not the optimistic exact-wick a naive loop grants), no float rate may touch the money path, and the admission/charge double-call must agree. **P0.**

**Named weak spots — structural risk loci (metrics to be confirmed against `coverage.json` / the module inventory at execution; the QA-harness weak-spot rows normally supplied by the missing handoff are absent):**

| Locus | Structural risk | Why it is the blind spot | Mitigation in this plan |
|---|---|---|---|
| Fill port **order-type dispatch** (`fill(...)` switch over market / limit / stop / stop-limit / trailing-stop / MOO / MOC / all-or-none) | Branch-dense switch; each arm has its own trigger + worst-case price rule. This is the **R-011 risk locus** (see below). | An untested arm is an order type that fills wrong (or fills when it should NoFill) with no error — the highest-count branch surface in the epic. | Every order-type arm gets its own L2 assertion + the worst-case price rule an L1 pure test; an L6 property bounds "never better than order price" across arbitrary OHLC (§4 Group C, T-17.3-P). |
| **Model-catalog switches** (slippage `{zero…size-tiered}`, commission `{zero…min}`, spread key lookup, swap schedule) | Each catalog is a config-selected branch that reads a calibration parameter; the *silent-zero* path lives at the "no artifact bound" edge of each. | The `zero`/absent branches are exactly where a fabricated or omitted number slips in undetected. | Absent-artifact refusal asserted per port (R14/R28/R31); an L0 static gate scans for embedded numeric constants (T-17.0-noconst). |
| **Partial-fill accumulation** (filled_qty capping, lot-step rounding, per-partial fee pro-rata) | Exact-integer accumulation across N partials of one intent; rounding + `reduce_only` cap interplay. | Off-by-a-lot-step or a fee-pro-rata rounding drift silently mis-states cost drag. | An L6 property (T-17.F-partial): `Σ filled_qty ≤ order_qty` and `Σ pro-rated fee == whole-fill fee` within the exact-integer rounding contract. |
| **Financing schedule** (AD-8 rollover instant, triple-swap weekday, weekend/holiday, long/short sign) | Calendar-scheduled, per-broker, sign-sensitive (carry can be credit); applied in sub-phase 2 not per slice. | A hardcoded rollover hour, a wrong triple-swap day, or a dropped sign silently corrupts every multi-day result. | R29/R30 at L2 against a fixture artifact; R31 absent-table refusal at L3; L0 gate that no rollover instant is hardcoded. |

**R-011 (from the missing handoff — interpreted).** The brief names "R-011 branch behaviour by requirement" as a risk-gate row. With the handoff absent, R-011 is read here as: **the branch-heavy execution-dispatch surface (fill order-type switch + slippage/commission/spread/swap model catalogs) must have every branch tied to a requirement-driven assertion, not merely covered.** A green branch with no assertion is a finding (§7). Reconcile the exact R-011 wording when the handoff is restored.

**Priority ladder (derived — see Process Gap re: the missing 15-assertion handoff):**
- **P0 (must-pass gate; block the epic on any failure):** R3, R4, R5, R7, R9, R10, R12, R13, R14, R18, R19, R20, R21, R22, R23 (veto arm), R24, R25, R27, R28, R29, R31, and the two spine properties T-17.F-taint / T-17.F-partial.
- **P1 (high — evidence honesty & attribution):** R6, R8, R11, R15, R16, R17, R26, R30, R32, R33.
- **P2 (important — completeness):** R2, R23 (map/passive/seed sub-arms not the veto).

---

## Section 4 — Independent Test List (authored from requirements, BEFORE any src read)

> **Discipline statement.** This section was written having read **zero files** under `qmb/src/qmb/execution/`. Every test asserts what a *requirement* demands — derived from the Epic-17 ACs, the B-6/B-7 spine, the fill/fees source spec (FILL/SLIP/FEE/SPREAD/LABEL), and the CT-* contracts — never what the code happens to do. A failing test is a **finding**, not a licence to edit source or weaken the assertion. Level per "one behaviour, one level; lower level wins" (taxonomy in §5). Properties use `hypothesis` (`uv run --with hypothesis ...` if unsynced). T2 scope: **L2 + L3 for every AC**, targeted **L1** for pure sub-computations, **L6** properties + review.

### Group A — Port-set composition & fidelity identity (Story 17.1) → R1–R12

- **T-17.1-a** *(L2)* The binder composes exactly three separate ports (fill, slippage, cost) plus a financing scheduler, each resolved by adapter-id from the config. **[R1]**
- **T-17.1-b** *(L2)* Composition order is pinned **fill → slippage → cost**: the fill's pre-slip price is produced before slippage runs, and cost itemizes on the post-slip fill; the order is not a runtime-supplied parameter. **[R1]**
- **T-17.1-c** *(L3)* Binding is only from the resolved read-only config — an adapter absent from the config is never bound by ambient discovery; the same config binds the same adapters deterministically. **[R2]**
- **T-17.1-d** *(L3)* An inbound request that is not a CT-23 Book-resolved authorized intent (a raw bot-sized order carrying its own size) returns a CT-04 typed refusal and **no port executes**. **[R3] P0**
- **T-17.1-e** *(L2)* A well-formed CT-23 authorized intent is admitted unchanged and executed; the ports preserve the Book-resolved `requested_r` and never re-size. **[R4] P0**
- **T-17.1-f** *(L3)* An opening/increasing intent with no AD-40 full-loss price → the fill port is never invoked and a CT-04 refusal is returned before any open. **[R5] P0**
- **T-17.1-g** *(L2)* A risk-reducing CT-29 exit intent is admitted without a new full-loss price. **[R6]**
- **T-17.1-h** *(L2)* Every bound adapter's fidelity identity is exactly `(adapter-id + composition-version + taint)`, and `taint = optimistic` for every non-live fill; the taint is a distinct field, not part of the identity tuple. **[R7] P0**
- **T-17.1-i** *(L2)* Changing the bound port set or its order changes the composition-version (two different bound sets → two different composition-versions); identity never silently drifts. **[R8]**
- **T-17.1-j** *(L1)* The run-fidelity fold returns the LOWEST fidelity among a set of bound-adapter fidelities (pure fold; a single lower-fidelity adapter downgrades the run). **[R9] P0**
- **T-17.1-k** *(L3)* Comparing two Book-bar results of differing fidelity without an explicit override returns a CT-04 typed refusal (LABEL-3); no ordinal fidelity value is asserted (taxonomy deferred). **[R10] P0**
- **T-17.1-l** *(L3)* Composing the port-set for `world=simulated` is refused, and a config binding a replay clock to synthetic-tainted data is an `invalid input` CT-04 refusal. **[R11]**
- **T-17.1-m** *(L3)* An optimistic-tainted run's label carries a claim-class gate marking it barred from edge/verdict claim and split-budget spend. **[R12] P0** *(taint-carried half; split-budget *enforcement* is downstream — see §8)*

### Group B — Synthetic-spread model & SQS input (Story 17.2) → R13–R17

- **T-17.2-a** *(L2)* With trade-only bars, the spread model supplies bid/ask keyed by instrument × hour-of-day (UTC) × session from its bound calibration artifact, and never returns an equal buy/sell price silently — an absent source is surfaced. **[R13] P0**
- **T-17.2-b** *(L3)* The bound spread calibration artifact is versioned + fingerprinted per-broker; when no artifact is bound for the instrument the model returns a CT-04 refusal, never a silent zero spread. **[R14] P0**
- **T-17.2-c** *(L2)* When the feed carries real quotes, the real spread takes precedence over the synthetic model, and the run is recorded at a higher price-basis fidelity than a synthetic-spread run (relative, not ordinal-valued). **[R15]**
- **T-17.2-d** *(L3)* The Book's SQS door (AD-39) consumes this run's modeled-spread series as its spread input, and the series cites exact `Price` values (no binary float). **[R16]**
- **T-17.2-e** *(L3)* A run that bound the synthetic-spread model declares the spread calibration artifact fingerprint in the CT-32 label. **[R17]**
- **T-17.2-P** *(L6 property)* Over arbitrary (instrument, hour, session) keys: a modeled spread is non-negative and buy ≠ sell wherever a calibration entry exists, and every key with no entry **refuses** rather than zeroes. **[R13/R14] P0**

### Group C — Fill & slippage price-forming pipeline (Story 17.3) → R18–R23  *(R-011 branch locus)*

- **T-17.3-a** *(L2)* The fill port returns `Fill|NoFill|PartialFill` and, on a fill, a pre-slip price by crossing the declared path, dispatched per order type across all eight arms (market, limit, stop, stop-limit, trailing-stop, MOO, MOC, all-or-none group). **[R18] P0**
- **T-17.3-b** *(L2)* An all-or-none group in which any leg fails returns NoFill for the whole group. **[R18]**
- **T-17.3-c** *(L1)* Worst-case pricing math is exact per order type: buy limit = `min(high,limit)`; sell limit = `max(low,limit)`; stop = worst of stop vs current±slip (pure price function). **[R19] P0**
- **T-17.3-d** *(L2)* Optimistic-exact mode fills at the exact order price but stamps a **distinct fill-basis** in the fidelity label; both worst-case and optimistic-exact remain optimistic-tainted. **[R19]**
- **T-17.3-e** *(L2)* A PartialFill emits `filled_qty < order_qty`, caps a `reduce_only` fill to the open position size, and rounds to the instrument lot step; each partial emits its own `Fill` with its own pro-rated fee reference. **[R20] P0**
- **T-17.3-f** *(L1)* Lot-step rounding is exact-integer on the quantity path (no float lot arithmetic). **[R20]**
- **T-17.3-g** *(L2)* The stale-data guard returns a typed NoFill whose reason code is drawn from the closed set `{market_closed|stale_data|not_triggered|insufficient_liquidity|all_or_none_leg_failed}`. **[R21] P0**
- **T-17.3-h** *(L2)* An order whose price sits in a between-bar gap fills at the gapped price with a `gap_fill` marker, not skipped. **[R21]**
- **T-17.3-i** *(L2)* Several resting orders inside one slice fill in a deterministic order derived by splitting the declared path at each fill price, reproducible without tick data (two runs → same sequence). **[R22] P0**
- **T-17.3-j** *(L2)* An intent newly minted by a strategy callback in sub-phase 5 is not eligible to fill against this slice's path — it is observably resting for a later slice. **[R22]** *(seam with Epic 14 B-2)*
- **T-17.3-k** *(L2)* Slippage maps pre-slip → post-slip (buy `+`, sell `−`) using the config-selected FX model across `{zero|constant-percent|spread-crossing|gap-volatility|size-tiered}`, each reading its calibration artifact. **[R23]**
- **T-17.3-l** *(L2)* The slippage port vetoes the fill (returns NoFill) when the slipped price is not a legal print on the slice. **[R23] P0**
- **T-17.3-m** *(L2)* Slippage is not applied to passive limit fills unless explicitly configured. **[R23]**
- **T-17.3-n** *(L3)* A stochastic slippage term draws from a per-run seed derived from run identity; a replay of the same run reproduces the identical draw. **[R23]**
- **T-17.3-P** *(L6 property)* Over arbitrary OHLC bars and limit/stop prices, a worst-case filled price is never *better* than the order price (≤ order price for buys, ≥ for sells) and never outside the bar range; no fill beats the exact-wick optimum. **[R19] P0**

### Group D — Cost port: exact-integer itemized commission (Story 17.4) → R24–R28

- **T-17.4-a** *(L2)* The cost port returns a typed fee amount in its own currency mapped to exact-integer `Money`; no float commission rate touches the money path. **[R24] P0**
- **T-17.4-b** *(L1)* Commission-shape math for each of `{zero|percent-of-notional|per-lot/per-1k-units|notional-proportional-with-per-order-minimum}` is exact-integer given a calibration parameter (pure function; the min-shape returns `max(minimum, rate×notional)`). **[R26]**
- **T-17.4-c** *(L2)* Each partial carries its own pro-rated commission itemized separately; commission is a distinct line item, never folded into fill P&L. **[R25] P0**
- **T-17.4-d** *(L3)* Double-call determinism: the fee queried before the fill (admission) and again at fill time returns the identical amount; a fee queried for admission whose fill does not occur charges nothing. **[R27] P0**
- **T-17.4-e** *(L3)* A commission model whose calibration artifact is missing returns a CT-04 refusal, never a silent zero commission. **[R28] P0**
- **T-17.4-f** *(L3)* Each commission shape is parameterized by a versioned per-broker calibration artifact (DEC-0135); no rate constant is embedded in source. **[R26]**

### Group E — Daily-swap financing (Story 17.5) → R29–R33

- **T-17.5-a** *(L2)* Financing applies at the per-broker AD-8 accounting rollover (resolved from the artifact, never hardcoded) in sub-phase 2, as an exact-integer `Money` debit/credit to each open position — not an order fill — per instrument and per direction (long/short); applied at the rollover, not per slice. **[R29] P0**
- **T-17.5-b** *(L2)* Triple-swap day and weekend/holiday handling are honored from the bound calendar-scheduled per-broker artifact; swap points, sign convention (carry may be a credit), and the triple-swap weekday are read from the artifact. **[R30]**
- **T-17.5-c** *(L3)* An open multi-day position whose instrument has no bound swap table returns a CT-04 refusal at rollover, never a silent zero swap. **[R31] P0**
- **T-17.5-d** *(L3)* A swap is emitted as a distinct CT-13 journal event, separate from fill P&L, slippage cost, and commission. **[R32] P1** *(event-type mapping ambiguity — see §8)*
- **T-17.5-e** *(L2)* The result artifact decomposes total cost drag into fill P&L, slippage, commission, and financing as separately attributable line items. **[R32]**
- **T-17.5-f** *(L3)* A run that applied financing declares the financing calibration fingerprint in the CT-32 label and remains optimistic-tainted (barred from edge/split-budget). **[R33]**

### Group F — Cross-cutting: taint propagation, partial composition, static gates & L6 review

- **T-17.0-protocol** *(L0)* Fill, slippage, and cost seams are declared as three distinct `typing.Protocol` types; financing is a separate scheduler seam. **[R1]**
- **T-17.0-nofloat** *(L0)* No module under `execution/` introduces a binary float onto the money/price/quantity path (static scan; calibration parameters are exact-rational / scaled-integer). **[R24/R16]**
- **T-17.0-noconst** *(L0)* No spread / slippage / commission / swap-point numeric constant and no rollover-hour constant is embedded in `execution/` source — every parameter is sourced from a bound calibration artifact (static reinforcement of DEC-0135 + R29). **[R14/R23/R26/R30/R29]**
- **T-17.F-taint** *(L6 property)* **Taint-propagation invariant:** for any bound port-set containing ≥1 optimistic (or lower-fidelity) adapter, the composed run label carries the `optimistic` taint AND the lowest fidelity; there is **no** composition that drops the taint or raises run fidelity above its lowest adapter. **[R7/R9/R12/R33] P0**
- **T-17.F-partial** *(L6 property)* **Partial-fill composition invariant:** for any sequence of partial fills of one authorized intent, `Σ filled_qty ≤ order_qty` (and ≤ open position size for `reduce_only`), each partial carries its own pro-rated commission, and `Σ pro-rated commissions == whole-fill commission` within the exact-integer rounding contract. **[R20/R25] P0**
- **T-17.F-review** *(L6 review)* Adversarial read of the execution ports against B-6 + DEC-0135, hunting: silent-zero paths, taint drops, invented constants, float leaks on the money path, composition-order violations, and hardcoded rollover/triple-swap values. Recorded in `L6-REVIEW.md`.

---

## Section 5 — Test-Level Architecture Mapping (L0–L6)

> Reconstructed taxonomy (test-design-qa.md absent). Rule enforced: **one behaviour, one level; the lowest level that can meaningfully assert it wins.** A behaviour is re-asserted higher only where a property/metamorphic test adds coverage a unit cannot (flagged). T2 scope concentrates population at **L2 + L3**, with targeted L1 and L6.

| Level | Meaning here | Execution band | Epic-17 population |
|---|---|---|---|
| **L0** | Static / structural gates on source (Protocol seams, no-float-on-money-path, no-embedded-constant). | lint/type gate | T-17.0-protocol, T-17.0-nofloat, T-17.0-noconst = **3** |
| **L1** | Pure unit — one pure function, no I/O (worst-case price math, lot-step rounding, lowest-wins fold, commission-shape math). | tier-1 (`poe check`) | T-17.1-j, T-17.3-c, T-17.3-f, T-17.4-b = **4** |
| **L2** | Component/integration in-process — a port (or the binder) wired through one intent / one slice / one rollover with stub adapters, deterministic, no OS process. | tier-1/2 | **24** |
| **L3** | Contract tests — CT-04 refusal categories, CT-23 inbound guard, CT-32 label fingerprints, double-call determinism, absent-calibration refusals, world-derivation refusal, per-run-seed reproduction, distinct CT-13 event. | **tier-2** (`poe check-integration`) | **16** |
| **L4** | Scenario / golden-path. | tier-2 | **0 owned** — Epic 17's adapters plug into SCN-0012 (Epic 14/19); the end-to-end taint-in-label appearance is asserted there. |
| **L5** | System / orchestrated (process-per-run concurrency). | system | **0 owned** — Epic 15; per-run-seed independence under concurrency verifies at Epic 15 integration. |
| **L6** | Property-based + review — taint/partial invariants, spread/worst-case properties, adversarial review. | tier-2 | T-17.2-P, T-17.3-P, T-17.F-taint, T-17.F-partial, T-17.F-review = **5** |

**Lower-level-wins applications:**
- Worst-case pricing is asserted at **L1** (T-17.3-c, exact rule) with an **L6** property (T-17.3-P) as breadth over arbitrary OHLC — not a duplicate concrete case.
- Lowest-wins fidelity is a **L1** pure fold (T-17.1-j); its *propagation through composition* is the distinct **L6** invariant (T-17.F-taint) — two behaviours (the fold vs. the guarantee it is never bypassed), not duplication.
- Calibration-absence is asserted once per port at **L3** (T-17.2-b / T-17.4-e / T-17.5-c) plus the **L6** spread property (T-17.2-P) covering the arbitrary-key space a hand case cannot enumerate.
- Partial-fill capping is at **L2** (T-17.3-e, concrete) with the **L6** accumulation invariant (T-17.F-partial) over arbitrary partial sequences.

**Level totals:** L0 = 3, L1 = 4, L2 = 24, L3 = 16, L4 = 0, L5 = 0, L6 = 5. **Total = 52.**

---

## Section 6 — Fixtures, Data & Determinism Strategy

**Fixtures (controlled test fixtures permitted; no product mock data, no default strategies, no invented calibration numbers shipped as source):**
- **Fingerprinted calibration artifacts (fixtures, not source):** a small versioned spread table (instrument × hour × session), a slippage-model parameter set, a commission-shape parameter set, and a swap-schedule (per-instrument long/short points + triple-swap weekday + weekend rule) — each a **checked-in `qa/` fixture artifact** carrying a fingerprint, so that the code reads them as bound artifacts and NO number lives in `execution/` source. The *values* are arbitrary test values, never claimed as real calibration (GAP-0048 owns real content); tests assert *mechanism and refusal*, never a specific real number.
- **A matched "no-artifact" fixture set:** for every calibration consumer, the deliberately-absent case that must produce a CT-04 refusal (R14/R28/R31).
- **Declared-path bar fixtures:** trade-only bars (to exercise the synthetic-spread path), quote-bearing bars (to exercise real-quote precedence, R15), a gap bar (R21 `gap_fill`), and a multi-order-in-one-slice bar (R22 deterministic sequencing).
- **CT-23 / CT-29 / CT-32 / CT-13 fakes** are shape-faithful to the ratified contracts (fields, unit-kinds, refusal categories, the seven journal event types). A test that passes against a shape-unfaithful fake is itself a finding.
- **Stub adapters** implementing the three port Protocols + the financing scheduler seam, plus a two-adapter mixed-fidelity pair for the lowest-wins / comparison-refusal tests (T-17.1-j/-k, T-17.F-taint).

**Determinism strategy:**
1. **Per-run seed from run identity (R23/SLIP-3).** T-17.3-n asserts a replay reproduces the identical stochastic draw; run under `PYTHONHASHSEED` variation to catch any ambient-order leak in model selection or partial-fill sequencing.
2. **Exact-integer everywhere on the money path.** L0 no-float gate (T-17.0-nofloat) + per-partial fee accumulation invariant (T-17.F-partial) prove no float drift; calibration parameters enter as exact rationals/scaled integers.
3. **No invented constants.** L0 no-const gate (T-17.0-noconst) proves the negative; the absent-artifact refusals prove the positive path also refuses rather than substitutes.
4. **Property breadth over the branch-dense loci.** Hypothesis properties drive the order-type/model-catalog space (T-17.3-P) and the spread-key space (T-17.2-P) that hand cases under-enumerate.

**Refusal discipline.** Every "is refused" assertion (T-17.1-d/-f/-k/-l, T-17.2-b, T-17.4-e, T-17.5-c, plus the NoFill reason-coded T-17.3-g/-l) checks a **returned** CT-04 typed refusal of the correct category (`invalid input` / `unsupported capability` / `policy rejection` / `unavailable dependency` as the AC dictates) — never a raised exception across a public boundary, and never a silent zero. A NoFill is a typed refusal carrying a reason code, not `None`.

---

## Section 7 — Coverage Targets & Weak-Spot Plan

**Global posture.** Coverage is a floor and a map, never the goal — a green line with no assertion is a finding. Targets are audit-pass gates; a shortfall is recorded, not waived. Metrics below are floors; the current per-file numbers are **to be confirmed against `coverage.json` at execution** (the harness weak-spot rows are absent — see Process Gap).

| Target | Floor | Rationale |
|---|---|---|
| `execution/` package line coverage | ≥ 90% | T2 evidence-honesty epic; every downstream edge claim depends on its taint. |
| `execution/` package branch coverage | ≥ 88% | Branch is where the order-type dispatch and model catalogs live. |
| **Fill order-type dispatch branch coverage** | **≥ 95%** | The **R-011** locus: every one of the eight order-type arms + the all-or-none-fail arm must be hit by a requirement-driven assertion (Group C), each branch mapped to a test ID in §8. |
| **Model-catalog & absent-artifact branches** (slippage/commission/spread/swap) | **≥ 95%** | Each `{…}` catalog arm AND each "no artifact bound" edge must be asserted (R14/R23/R26/R28/R30/R31); the silent-zero path is the highest-severity leak. |
| Mutation sensitivity (taint fold, worst-case price, absent-artifact refusal, partial-fee pro-rata) | spot-check | A mutation that flips a taint to a higher fidelity, a worst-case `min`/`max` to best-case, a refusal to a zero, or a pro-rata to a whole-fee MUST fail a test; a survivor means the test is decorative — record as a finding. |

**Weak-spot execution order (do the risk-carrying honesty work first):**
1. Calibration-absence refusals across all four ports (R14/R28/R31 + T-17.F-taint) — closes the silent-zero backdoor.
2. Taint propagation + lowest-wins (Group A T-17.1-h/-j/-k + T-17.F-taint) — the evidence-honesty spine.
3. Fill order-type dispatch + worst-case honesty (Group C + T-17.3-P) — the R-011 branch surface.
4. Partial-fill composition + per-partial fee (T-17.3-e + T-17.4-c + T-17.F-partial) — exact-integer cost-drag integrity.
5. Financing schedule (Group E) — the calendar/sign correctness tail.

---

## Section 8 — Execution, Traceability Matrix & Exit Criteria

**Execution.**
- Run from the worktree root: `uv run pytest qa/tests/epic_17 -q` for L0–L2 (tier-1) and the project's `poe check-integration` band for L3/L6 (tier-2). Properties: `uv run --with hypothesis pytest ...` if hypothesis is not in the synced dev group.
- All tests live under `qa/` per the audit write-boundary; `execution/` source is read-only evidence. A failing test is a **finding recorded in this epic's `findings.csv`**, never a reason to edit `execution/` source or soften an assertion.

**Traceability (requirement → test → priority → level → status):** every R1–R33 maps to ≥1 test.

| Req | Test IDs | Prio | Level(s) | Status |
|---|---|---|---|---|
| R1 | T-17.1-a, T-17.1-b, T-17.0-protocol | P1 | L2,L0 | planned |
| R2 | T-17.1-c | P2 | L3 | planned |
| R3 | T-17.1-d | P0 | L3 | planned |
| R4 | T-17.1-e | P0 | L2 | planned |
| R5 | T-17.1-f | P0 | L3 | planned |
| R6 | T-17.1-g | P1 | L2 | planned |
| R7 | T-17.1-h, T-17.F-taint | P0 | L2,L6 | planned |
| R8 | T-17.1-i | P1 | L2 | planned |
| R9 | T-17.1-j, T-17.F-taint | P0 | L1,L6 | planned |
| R10 | T-17.1-k | P0 | L3 | planned |
| R11 | T-17.1-l | P1 | L3 | planned (world-derivation refusal half; provenance derivation = Epic 14) |
| R12 | T-17.1-m, T-17.F-taint | P0 | L3,L6 | planned (taint-carried half; split-budget enforcement = qmf-data/Epic 14) |
| R13 | T-17.2-a, T-17.2-P | P0 | L2,L6 | planned |
| R14 | T-17.2-b, T-17.2-P, T-17.0-noconst | P0 | L3,L6,L0 | planned |
| R15 | T-17.2-c | P1 | L2 | planned (relative precedence; ordinal value = GAP-0048) |
| R16 | T-17.2-d, T-17.0-nofloat | P1 | L3,L0 | planned (read-point + exact-Price; DEC-0153 freshness reconciliation = GAP-0048) |
| R17 | T-17.2-e | P1 | L3 | planned |
| R18 | T-17.3-a, T-17.3-b | P0 | L2 | planned |
| R19 | T-17.3-c, T-17.3-d, T-17.3-P | P0 | L1,L2,L6 | planned |
| R20 | T-17.3-e, T-17.3-f, T-17.F-partial | P0 | L2,L1,L6 | planned |
| R21 | T-17.3-g, T-17.3-h | P0 | L2 | planned |
| R22 | T-17.3-i, T-17.3-j | P0 | L2 | planned (new-intents-rest shares the Epic-14 B-2 seam) |
| R23 | T-17.3-k, T-17.3-l, T-17.3-m, T-17.3-n | P0/P2 | L2,L3 | planned (veto arm P0; map/passive/seed P2) |
| R24 | T-17.4-a, T-17.0-nofloat | P0 | L2,L0 | planned |
| R25 | T-17.4-c, T-17.F-partial | P0 | L2,L6 | planned |
| R26 | T-17.4-b, T-17.4-f, T-17.0-noconst | P1 | L1,L3,L0 | planned (shapes/mechanism; rate content = GAP-0048) |
| R27 | T-17.4-d | P0 | L3 | planned |
| R28 | T-17.4-e | P0 | L3 | planned |
| R29 | T-17.5-a, T-17.0-noconst | P0 | L2,L0 | planned |
| R30 | T-17.5-b, T-17.0-noconst | P1 | L2,L0 | planned (schedule mechanism; swap-point content = GAP-0048) |
| R31 | T-17.5-c | P0 | L3 | planned |
| R32 | T-17.5-d, T-17.5-e | P1 | L3,L2 | planned (distinct-event + decomposition; exact CT-13 event_type = ambiguity, below) |
| R33 | T-17.5-f, T-17.F-taint | P1 | L3,L6 | planned |

**Exit criteria (epic passes audit when):**
1. Every **P0** test is green and mutation-sensitive on its guard (taint fold, worst-case price, absent-artifact refusal, partial-fee pro-rata).
2. The fill order-type dispatch and every model-catalog / absent-artifact branch meet their §7 floors, each covered branch tied to an assertion (the R-011 gate).
3. `T-17.F-taint` and `T-17.F-partial` are green under `PYTHONHASHSEED` variation.
4. Every "is refused" test asserts a **returned** CT-04 refusal of the correct category; every NoFill carries a reason code from the closed set.
5. Every blocked/partial requirement (R11, R12, R15, R16, R26, R30, R32) has a recorded reason and an owning epic/gap (below).
6. The L6 review (`L6-REVIEW.md`) is complete with no un-triaged silent-zero / taint-drop / invented-constant finding.

**Untestable / blocked / partial in Epic-17 isolation (findings, not omissions):**
- **Calibration *content* and the fidelity taxonomy ordinal values (GAP-0048).** Whether a specific spread/slippage/commission/swap *number* is correct, and which fidelity label ranks above which on an ordinal scale, are **untestable now** — asserting them would assert an unratified value. Testable now: the seam, the taint, *relative* precedence (real > synthetic, R15), the calibration-artifact-is-fingerprinted-and-consumed fact, and absence-refuses. (R14 content, R23 numbers, R26 rates, R30 swap points, R10/R15 ordinal.)
- **R11 provenance→world derivation** — Epic 17 asserts the port-set *refuses to compose* for `world=simulated` and treats replay-on-synthetic as `invalid input`; the derivation of `world` from data provenance is **Epic 14 (B-7)**.
- **R12/R33 split-budget spend enforcement** — the *taint carried in the label* and the *claim-class gate* are testable here; the actual refusal to *spend split budget* is enforced by qmf-data (CT-12) / the validation ladder (Epic 14+), not the ports.
- **R16 SQS-door / DEC-0153 reconciliation** — the read-point and exact-`Price` series are testable; how the modeled-spread series satisfies DEC-0153's tick/quote-sampling and `decision_freshness_bound` requirements is an explicit **GAP-0048 pending slot** (qmb.md), not settled behavior.
- **R32 exact CT-13 event_type for a swap — AMBIGUITY (candidate finding).** CT-13's seven event types are `decision | order | fill | risk transition | promotion | data quality | control action`; none is a "financing"/"swap" kind, yet the AC requires a swap to be a **distinct** CT-13 event **separate from fill**. The *shape-level* requirement (distinct event, decomposable line item) is testable; the exact event-type mapping is under-specified in the contract — flag for ruling, test the distinctness at shape level, and record the mapping gap as a finding rather than inventing a kind.
- **Partial FILL vs `close_partial` (consistency note, not a conflict).** CT-23 bars `close_partial` as a V1 *exit-intent kind*; Epic 17's first-class **partial fills** are a fill-side realism (how much of an authorized intent's quantity fills against the slice path), not an intent kind. Tests must not conflate them — a partial fill of a `close_full`/entry intent is legal; a `close_partial` *intent* remains an unsupported-capability refusal owned by CT-23/Epic 10.
- **L4/L5 owned elsewhere** — the end-to-end golden run (SCN-0012, Epic 14/19) is where Epic 17's adapters demonstrate the taint reaching the CT-32 label in a full run; per-run-seed independence under process concurrency verifies at Epic 15. Epic 17 contributes the adapters and asserts its half at L2/L3/L6.
- **Process authorities absent** — test-design-qa.md (template + L0–L6) and QMX-handoff.md (15 P0/P1 assertions + risk-gate rows incl. **R-011**) are missing; §1/§3/§5 and the R-011 interpretation are reconstructed and must be reconciled when restored. This is the single largest caveat on the plan's fidelity to the intended template.
