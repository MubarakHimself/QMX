# Verification PLAN — Epic 14: QMB Run Loop & Replay Backtest

**Audit tier:** T1 (highest scrutiny — determinism/identity-critical epic).
**Package under test:** `qmb/src/qmb/runloop/` (loop, frontier clock port, bar derivation, warm-up); seams into `qmb/src/qmb/execution/`, `qmb/src/qmb/config/`, `qmb/src/qmb/results/`.
**Delivers:** the loop half of FR-036 and all of FR-037.
**Governing invariant:** QMB spine **B-2** (event-slice loop, injected frontier clock, pinned identity-bearing sub-phase order, forming bars never actionable, in-loop warm-up, golden-slice determinism). Supporting: B-4 (pure `run()` returns), B-5 (cancel/limit seam), B-6 (CT-23 in / ports / CT-29 out / optimistic taint), B-7 (provenance-derived world).

> **PROCESS GAP (read first).** Two authorities named in the audit brief **do not exist in this worktree**:
> `_bmad-output/test-artifacts/test-design-qa.md` (the Per-Epic Test Plan Template + the L0–L6 test-level architecture) and
> `_bmad-output/test-artifacts/test-design/QMX-handoff.md` (the 15 P0/P1 assertions + this epic's risk-gate rows).
> Confirmed absent by full-tree search (only `archive/recovery/*/restart-handoff.md` and backtesting-spec files match). Sibling epic QA dirs (`epic_01`, `epic_03`, `epic_08`, `epic_13`) are empty, so no prior PLAN.md fixes the format either.
> **Consequence:** the 8-section structure below and the L0–L6 taxonomy in §5 are **reconstructed** from standard BMad/TEA test-architecture practice and this project's own vocabulary (tier-2 = `poe check-integration`; "one behaviour one level, lower level wins"). The P0/P1 assertion set in §3 is **derived from the ratified spine** (B-2/B-4/B-5/B-6/B-7 + Epic 14 ACs), not transcribed from the missing handoff. When the two files are restored, re-reconcile §1 template order, §3 risk-gate rows, and §5 level definitions against them before executing.

---

## Section 1 — Epic Context, Scope & Authorities

**What this epic is.** One never-forked event-slice loop. Time advances only through an injected frontier clock that **is** qmf-core's AD-8 `Clock` protocol. Every slice runs six sub-phases in a pinned, identity-bearing order. Higher-`BarSpec` bars derive only on completed boundaries; a forming bar is never visible or actionable. Warm-up runs in the same loop with trading locked. Execution consumes CT-23 Book-resolved intents through separate fill/slippage/cost ports and mints one CT-29 exit per virtual close, every fill `optimistic`-tainted until GAP-0048. The loop is cooperatively cancellable and observable. Two runs of identical inputs must produce an identical CT-32 fingerprint (tier-2 golden-slice determinism).

**In scope (Stories 14.1–14.7):** frontier clock; the six pinned sub-phases; completed-boundary bar derivation + forming-bar non-actionability; in-loop warm-up; CT-23 intake / execution-port seam / CT-29 exits; cancel-and-observe; golden-slice determinism + run-id reproduction.

**Boundary scope (Story 14.8):** QL-7 host adapter + DEC-0183 config-compiler extensions + host-owned conformance sandbox. **Blocked** on Epics 11/12 (QML/CT-33 Bot + conformance runner) and Epic 13 (compiler); epics.md itself notes 14.8 "waits for Epics 12 and 13" and is Epic 14's final story. Planned as scaffolds, executed when dependencies land (see §4 group H and §8 untestable list).

**Out of scope (owned elsewhere, seams only here):**
- Orchestrator process spawn, governor, ledger append, OS-enforced time/memory caps → **Epic 15** (B-4/B-5). The loop surfaces cooperative typed terminal states; it does not enforce OS limits.
- Fill/slippage/cost *fidelity content* (calibration values, cross-fidelity comparison rule, `world=simulated` unlock) → **GAP-0048 / Epic 17** (B-6). Only the *seam* (separate `typing.Protocol` ports), the `optimistic` taint, and the refuse-until-GAP-0048 behavior are testable now.
- SQS-door modeled-spread input (B-2 tail) → execution-adapter territory (Epic 17); the read-point exists here, the content does not.

**Two senses of "tier" (do not conflate).** *Audit tier* **T1** = this plan's scrutiny level (highest). *Test tier* **tier-2** = the project's `poe check-integration` execution band that the golden-slice determinism test and door-parity contract tests run in. §5 maps our L0–L6 levels onto those bands.

**Authorities, in precedence order:**
1. Epic 14 section of `_bmad-output/planning-artifacts/epics.md` (Stories 14.1–14.8, ACs).
2. `docs/` knowledge base: `docs/constitution.md` (L1–L39); `docs/contracts/ct-04` (typed refusal), `ct-12` (split/embargo), `ct-16` (indicator), `ct-23` (intent), `ct-29` (exit), `ct-32` (performance result); `docs/scenarios/SCN-0012-qmb-replay-run.md` (the golden replay run — Epic 14's L4 scenario, R-016).
3. `_bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md` (B-1…B-15; inherited AD-1…41).
4. *(Missing — see Process Gap)* test-design-qa.md; QMX-handoff.md.

---

## Section 2 — Requirements → Behaviours Traceability

Every row is a testable behaviour extracted from a ratified source. IDs are consumed by the independent test list (§4) and the matrix (§8). "Ref" cites the governing AC / spine / contract.

| # | Behaviour (requirement, stated as an assertion) | Ref | Story |
|---|---|---|---|
| R1 | Loop reads the current instant ONLY from the injected frontier clock; nothing below the composition root reads the system clock. | AR-16, B-2, AC14.1 | 14.1 |
| R2 | In replay the clock is a pure function of the data cursor: monotonically non-decreasing, pulled to the minimum next-emit instant across all declared streams, never rewinding. | B-2, FR-037, AC14.1 | 14.1 |
| R3 | The clock emits AD-8 wall/replay Instants, never the monotonic diagnostic kind, and does NOT choose `world`. | AD-8, B-2/B-7, AC14.1 | 14.1 |
| R4 | The frontier clock IS an implementation of qmf-core's AD-8 `Clock` protocol (substitutable, one seam for replay/backtest/live). | AD-8, B-2 | 14.1 |
| R5 | Backtest, replay, (deferred) live share identical loop code — only the injected clock/adapters change; the loop is never forked. | B-2, FR-036, AC14.1 | 14.1 |
| R6 | Asserting a simulated instant as a wall/replay Instant is a typed refusal until GAP-0048. | B-2, SC-06, AC14.1 | 14.1 |
| R7 | Per-slice sub-phase order is EXACTLY: (1) frontier advance + stream update, (2) scheduled position-level events (financing), (3) execute resting orders through the ports, (4) update indicators/structure on closed data only, (5) strategy callbacks mint intents, (6) new intents NOT eligible to fill against this slice's path. | AR-57, B-2, AC14.2 | 14.2 |
| R8 | A new intent minted in sub-phase 5 never fills against this slice's path; it rests for a later slice. | B-2, FR-037, AC14.2 | 14.2 |
| R9 | Within a phase, instruments process in stream-set declaration order (identity content of the resolved run-config). | B-2, B-12, AC14.2 | 14.2 |
| R10 | Indicators/structure update on closed data only, never on a forming bar. | B-2, CT-16, CT-17, AC14.2 | 14.2 |
| R11 | Altering the sub-phase order is identity-bearing — it yields a different fingerprint (pinned spine law). Order violations are impossible or refused. | AR-57, B-2, AC14.2 | 14.2 |
| R12 | A higher-`BarSpec` bar is built from the finest declared base stream and emitted ONLY on its completed boundary. | AR-57, B-2, AC14.3 | 14.3 |
| R13 | A forming (incomplete) bar is never visible or actionable to strategy code and carries an inspectable completeness state. | B-2, AC14.3 | 14.3 |
| R14 | A derived bar and the fills of the same slice consume the SAME (possibly gap-fixed) series — never a future or divergent series. | B-2, FR-037, AC14.3 | 14.3 |
| R15 | Completed-boundary derivation and forming-bar look-ahead prevention ship regardless of GAP-0048. | SC-06, AC14.3 | 14.3 |
| R16 | Warm-up uses the same event-slice loop, the same sub-phase order, and the same adapters, with trading locked. | SC-10, B-2, AC14.4 | 14.4 |
| R17 | During warm-up, any bot act (entry, exit, or any command) is a typed `policy rejection`. | B-2, SC-10, AC14.4 | 14.4 |
| R18 | Warm-up length is the AD-21 split-manifest embargo for the cited producers (an observation count, never a Duration); the loop adds no second window. | B-2, CT-12, AC14.4 | 14.4 |
| R19 | The result label's evidence range is the trading interval only, never the warm-up interval. | B-2, SC-10, AC14.4 | 14.4 |
| R20 | Pre-seeding indicator buffers without replaying slices is NOT warm-up. | B-2, AC14.4 | 14.4 |
| R21 | Inbound execution is a CT-23 Book-resolved (authorized) intent or a typed refusal — never a bot-sized order; an AD-40 full-loss price is required before any open. | B-6, AR-56, CT-23, AC14.5 | 14.5 |
| R22 | Fill, slippage, and cost are SEPARATE pinned `typing.Protocol` ports; fill decides `Fill \| NoFill \| PartialFill` with partial quantities first-class. | B-6, AR-56, AC14.5 | 14.5 |
| R23 | Every virtual-position close mints exactly one CT-29 exit record against the run's `world=replay` binding; bot-proposed exits are risk-monotonic (risk-reducing only). | CT-29, FR-032, AC14.5 | 14.5 |
| R24 | Pre-GAP-0048, every fill carries an `optimistic` taint; the run spends no split budget and claims no edge. | B-6, SC-06, FM-9, AC14.5 | 14.5 |
| R25 | A run whose stream set reads store-persisted synthetic data is `world=simulated` and a `policy rejection` for governed evidence until GAP-0048 (world derived from provenance, never caller-declared). | B-7, FM-2, SC-06, AC14.5 | 14.5 |
| R26 | A signalled cancel token stops the loop cooperatively at a slice boundary and returns a typed terminal state (rendered `aborted` by Epic 15). | FR-037, B-4, AC14.6 | 14.6 |
| R27 | A running loop exposes progress (data-points-processed throughput) and an `is_warming_up` flag. | FR-037, AC14.6 | 14.6 |
| R28 | A per-run time/memory limit breach detected in-loop surfaces a typed `aborted` terminal state rather than hanging. | FR-037, B-5, AC14.6 | 14.6 |
| R29 | On cancellation mid-run the pure `run()` returns a terminal refusal and writes nothing — no partial governed result. | B-4, AC14.6 | 14.6 |
| R30 | Identical inputs + resolved config run twice produce an identical CT-32 fingerprint (tier-2 golden-slice determinism test). | AR-58, B-2, NFR-03, AC14.7 | 14.7 |
| R31 | Re-running a run id under its resolved config reproduces the CT-32 fingerprint or returns a typed refusal. | AR-58, FM-11, AC14.7 | 14.7 |
| R32 | Determinism derives from the pinned sub-phase order + stream-set declaration order + pure aggregation/gap-fix/fill functions — no ambient nondeterminism. | B-2, NFR-02, AC14.7 | 14.7 |
| R33 | A run alongside N concurrent siblings is byte-identical in result and fingerprint to the run in isolation (concurrency is a scheduling decision only). | B-5, NFR-03, AC14.7 | 14.7 |
| R34 | QMB's composition root constructs a CT-33 bot via the QL-7 factory and drives it per evaluation instant with declared-footprint evidence only. | QL-7, AR-65, AC14.8 | 14.8 |
| R35 | The B-3 compiler applies DEC-0183 extensions (assignment_is_canonical stamping, producer-template resolution); a non-canonical assignment is labeled a run-spec override, never a governed-seat execution. | DEC-0183, AR-69, AC14.8 | 14.8 |
| R36 | The host-owned conformance sandbox runs the pure verdict suite in an isolated process and feeds results to the QML pure verdict function unchanged. | QL-8, AR-64, AC14.8 | 14.8 |
| R37 | A plain-Python ungoverned bot runs in the tunnel with nothing in the QL-7 path required; tunnel entry stays ungated by conformance. | QL-1, FR-047/048, AC14.8 | 14.8 |

---

## Section 3 — Risk Assessment, Weak Spots & Priority

**Highest-value risk theme (from the brief + spine):** *Every result derives from this loop.* A defect here silently corrupts every backtest, sweep, MC, and walk-forward downstream and cannot be back-filled. The three loop properties that carry platform identity:

1. **Sub-phase order is identity-bearing (R7/R11).** If order can be altered without a fingerprint change, or an out-of-order slice can execute, determinism and anti-look-ahead both collapse. **P0.**
2. **Forming bars are non-actionable (R12/R13).** A single actionable forming bar is a look-ahead leak that fabricates edge. **P0.**
3. **Determinism with no ambient time below the composition root (R1/R2/R30/R32).** Any system-clock read, unseeded RNG, dict-ordering, or set-iteration dependency below the root breaks byte-identical reproduction. **P0.**

**Named weak spots (from the QA harness metrics in the brief — to be confirmed against the module inventory at execution):**

| Locus | Metric | Risk implication | Mitigation in this plan |
|---|---|---|---|
| `qmb/src/qmb/runloop/loop.py` | cyclomatic complexity **26** | High branch density in the slice driver — the exact place order-violation, cancel-boundary, warm-up-lock, and forming-bar guards live; untested branches here are the platform's blind spot. | Branch-level targeting of the six-phase switch, the cancel/limit exits, and the warm-up gate (§4 groups B/D/F; §7 branch-coverage floor). |
| `qmb/src/qmb/runloop/bars.py` | line **68%**, branch **56%** coverage | Bar derivation + completeness state — the forming-bar/completed-boundary machinery. 44% of branches unexercised is where a forming bar could leak as actionable. | Dedicated completed-boundary + forming-bar suite incl. a hypothesis property (§4 group C; §7 raises bars.py branch floor). |

**Priority ladder (derived — see Process Gap re: the missing 15-assertion handoff):**
- **P0 (must-pass gate, block the epic on any failure):** R1, R2, R7, R8, R10, R11, R12, R13, R30, R31, R32.
- **P1 (high — evidence honesty & safety):** R3, R4, R6, R14, R16, R17, R18, R19, R21, R23, R24, R25, R26, R28, R29.
- **P2 (important — completeness):** R5, R9, R15, R20, R22, R27, R33.
- **P3 / blocked:** R34, R35, R36, R37 (Story 14.8 — cross-epic dependency).

---

## Section 4 — Independent Test List (authored from requirements, BEFORE any src read)

> **Discipline statement.** This section was written having read **zero files** under `qmb/src/qmb/runloop/`. Every test below asserts what a *requirement* demands, derived from epics.md ACs, the QMB spine, and the CT-* contracts — never what the code happens to do. A failing test here is a **finding**, not a licence to edit source or weaken the assertion. Level assignment follows "one behaviour, one level; lower level wins" (taxonomy defined in §5). Property-based tests use `hypothesis` (invoke with `uv run --with hypothesis ...` if not synced).

### Group A — Frontier clock (Story 14.1) → R1–R6

- **T-14.1-a** *(L1)* Given a fixed data cursor over ≥3 declared streams, `advance()` returns instants that are monotonically non-decreasing across the whole sequence. **[R2]**
- **T-14.1-b** *(L1)* Each advance yields the **minimum** next-emit instant across all declared streams (ties resolved by declaration order, never by wall time). **[R2, R9]**
- **T-14.1-c** *(L1)* The clock never rewinds: no output instant is strictly less than any prior output. **[R2]** *(strengthened by property T-14.1-P, group I)*
- **T-14.1-d** *(L1)* Emitted instants are AD-8 wall/replay kind; the AD-8 monotonic **diagnostic** kind is never emitted. **[R3]**
- **T-14.1-e** *(L1)* The clock exposes no `world` input or output — it does not choose `world`. **[R3]**
- **T-14.1-f** *(L3)* Substitutability contract: the frontier clock satisfies qmf-core's AD-8 `Clock` protocol and is accepted anywhere that protocol is required. **[R4]**
- **T-14.1-g** *(L2)* Inject a *poisoned* system clock (raises on read) as the process wall clock; a full replay slice sequence completes without touching it. **[R1]** *(paired with static gate T-14.0-imports, group L0)*
- **T-14.1-h** *(L3)* Attempting to assert a simulated instant as a wall/replay Instant returns a CT-04 typed refusal (category per registry) — refused until GAP-0048. **[R6]**
- **T-14.1-i** *(L4)* Metamorphic: the same loop entry point run with a replay-clock adapter vs a (stub) alternate-clock adapter executes the *same loop module path* — only the injected adapter differs; no forked code branch on run kind. **[R5]**

### Group B — Six pinned sub-phases (Story 14.2) → R7–R11

- **T-14.2-a** *(L1)* One processed slice records its sub-phase execution as exactly the ordered tuple (advance+stream, financing, execute-resting, indicators-on-closed, strategy-callbacks, intents-rest) — positions 1..6, no omission, no reorder. **[R7]** **P0**
- **T-14.2-b** *(L2)* An intent minted in phase 5 does NOT fill against the current slice's path; it is observably resting when the slice completes and can only fill on a later slice. **[R8]** **P0**
- **T-14.2-c** *(L1)* With ≥2 instruments, phase processing order equals the resolved-config stream-set declaration order (permuting declaration order permutes processing order deterministically). **[R9]**
- **T-14.2-d** *(L2)* Indicators/structure receive only closed data within a slice; a forming bar never reaches an indicator update. **[R10]** **P0**
- **T-14.2-e** *(L3)* Identity: a run whose sub-phase order is altered (via a test-only reordered driver) produces a **different** CT-32 fingerprint than the pinned order — order is identity content. **[R11]** **P0**
- **T-14.2-f** *(L1)* Order-violation is unrepresentable/refused: constructing or driving a slice with an out-of-order or truncated phase sequence yields a typed refusal (or is structurally impossible — the order is not a runtime-supplied parameter). **[R11]** **P0**

### Group C — Bars: completed-boundary & forming-bar (Story 14.3) → R12–R15 (weak spot: `bars.py`)

- **T-14.3-a** *(L1)* A higher-`BarSpec` bar is composed from the finest declared base stream and is emitted only at its completed boundary (no emission mid-interval). **[R12]** **P0**
- **T-14.3-b** *(L2)* A forming bar is never visible or actionable: a strategy callback observing an in-progress interval cannot read a completed higher bar and any act attempted against it is refused. **[R13]** **P0**
- **T-14.3-c** *(L1)* A forming bar carries an inspectable completeness state distinguishing forming from completed. **[R13]**
- **T-14.3-d** *(L2)* Within one slice, the derived bar and the fills consume the identical (possibly gap-fixed) underlying series object — never a future-shifted or divergent series. **[R14]** **P0**
- **T-14.3-e** *(L6, property)* Over arbitrary base-stream tick sequences and `BarSpec` boundaries, **no actionable event ever references a forming bar** (hypothesis, ≥200 cases). **[R13]** **P0**
- **T-14.3-f** *(L4)* Within the golden run, completed-boundary + forming-bar look-ahead prevention holds with GAP-0048 still open (no dependence on the deferred fidelity taxonomy). **[R15]**

### Group D — In-loop warm-up (Story 14.4) → R16–R20

- **T-14.4-a** *(L2)* Warm-up drives the same loop, same six-phase order, same adapters, with a trading lock engaged. **[R16]**
- **T-14.4-b** *(L2)* Any bot act during warm-up (entry, exit, or any command) returns a CT-04 `policy rejection`. **[R17]** **P1**
- **T-14.4-c** *(L1)* Warm-up length equals the AD-21 split-manifest embargo (an observation **count**, not a Duration) for the cited producers; the loop adds no second window. **[R18]**
- **T-14.4-d** *(L2)* After a warm-up→trading run, the result label's evidence range equals the trading interval only, excluding the warm-up interval. **[R19]** **P1**
- **T-14.4-e** *(L1)* Pre-seeding indicator buffers without replaying slices is rejected/typed as NOT warm-up. **[R20]**

### Group E — CT-23 intake, execution ports, CT-29 exits (Story 14.5) → R21–R25

- **T-14.5-a** *(L3)* Inbound execution accepts only a CT-23 Book-resolved (authorized) intent or returns a typed refusal; a bot-sized order (inbound `requested_r`) is refused; no open proceeds without an AD-40 full-loss price. **[R21]** **P1**
- **T-14.5-b** *(L2)* Fill, slippage, and cost are three separate `typing.Protocol` ports; the fill port returns `Fill | NoFill | PartialFill` with partial quantities first-class (capped by position size / lot step). **[R22]**
- **T-14.5-c** *(L3)* Each virtual-position close mints exactly one CT-29 exit record bound to the run's `world=replay` binding; a bot-proposed exit that widens risk / re-opens / increases size is a `policy rejection` (risk-monotonic). **[R23]** **P1**
- **T-14.5-d** *(L3)* Every fill produced pre-GAP-0048 carries an `optimistic` taint; the run's label spends no split budget and asserts no edge. **[R24]** **P1**
- **T-14.5-e** *(L3)* A run whose stream set reads store-persisted synthetic data is derived to `world=simulated` and is a `policy rejection` for governed evidence. **[R25]** **P1**
- **T-14.5-f** *(L2)* The ports never size: an intent carrying a bot-supplied size, or lacking Book resolution, is refused before reaching fill. **[R21]**

### Group F — Cancel & observe (Story 14.6) → R26–R29 (weak spot: `loop.py` exits)

- **T-14.6-a** *(L2)* A signalled cancel token stops the loop at the next slice boundary (not mid-slice) and returns a typed terminal state. **[R26]** **P1**
- **T-14.6-b** *(L2)* A running loop exposes data-points-processed throughput and an `is_warming_up` flag, both readable during the run. **[R27]**
- **T-14.6-c** *(L2)* An in-loop time/memory-limit breach surfaces a typed `aborted` terminal state; the loop does not hang. **[R28]** **P1** *(OS-enforced caps are Epic 15 — see §8)*
- **T-14.6-d** *(L2)* On mid-run cancellation the pure `run()` returns a terminal refusal and writes nothing — no partial governed result is emitted. **[R29]** **P1**

### Group G — Golden-slice determinism & run-id reproduction (Story 14.7) → R30–R33

- **T-14.7-a** *(L4)* **Flagship (tier-2 golden slice, SCN-0012):** identical inputs + resolved config run twice produce a byte-identical CT-32 fingerprint. **[R30]** **P0**
- **T-14.7-b** *(L3)* Re-running a run id under its resolved config reproduces the CT-32 fingerprint or returns a typed refusal on mismatch. **[R31]** **P0**
- **T-14.7-c** *(L4/L6 metamorphic)* Determinism is invariant under ambient perturbation: varying wall-clock, environment, process start time, and dict/set insertion incidentals leaves the CT-32 fingerprint unchanged; determinism traces only to pinned order + declaration order + pure aggregation/gap-fix/fill. **[R32]** **P0**
- **T-14.7-d** *(L5, shared with Epic 15)* A run alongside N concurrent siblings is byte-identical to the isolated run. **[R33]** *(loop-purity half testable here; process-concurrency half is Epic 15 — see §8)*

### Group H — Host conformant bots (Story 14.8) → R34–R37 **[BLOCKED — Epics 11/12/13]**

- **T-14.8-a** *(L3, blocked)* Composition root constructs a CT-33 bot via the QL-7 factory (declaration, resolved assignment, injected read surfaces); drives it per evaluation instant with declared-footprint evidence only. **[R34]**
- **T-14.8-b** *(L3, blocked)* The B-3 compiler applies DEC-0183 extensions; a non-canonical assignment is labeled a run-spec override, never a governed-seat execution. **[R35]**
- **T-14.8-c** *(L4, blocked)* The host-owned conformance sandbox runs the pure verdict suite in an isolated process and feeds results to the QML verdict function unchanged. **[R36]**
- **T-14.8-d** *(L2)* A plain-Python ungoverned bot runs in the tunnel with nothing in the QL-7 path required; tunnel entry is ungated by conformance. **[R37]** *(the one 14.8 test executable without QML — plain-Python is a day-one first-class input)*

### Group I — Properties & static gates (cross-cutting)

- **T-14.1-P** *(L6)* Property: over arbitrary multi-stream cursors the clock is monotonically non-decreasing and equals the min next-emit. **[R2]**
- **T-14.2-P** *(L6)* Property: over arbitrary phase-5 intent injections, no injected intent fills against its own slice. **[R8]**
- **T-14.0-imports** *(L0)* Static: no module in `runloop/` (below the composition root) imports a system-clock source (`time`, `datetime.now`, `perf_counter`, …). **[R1]**
- **T-14.0-state** *(L0)* Static: no module-global mutable state anywhere in `runloop/`. **[R32]**
- **T-14.0-protocol** *(L0)* Static: fill / slippage / cost seams are declared as `typing.Protocol` and are three distinct types. **[R22]**

---

## Section 5 — Test-Level Architecture Mapping (L0–L6)

> Reconstructed taxonomy (test-design-qa.md absent). Rule enforced: **one behaviour, one level; the lowest level that can meaningfully assert the behaviour wins** — no behaviour is re-asserted at a higher level except where a metamorphic/property test adds coverage a unit cannot (explicitly flagged).

| Level | Meaning here | Execution band | Epic-14 population |
|---|---|---|---|
| **L0** | Static / structural gates on source (imports, module-global state, Protocol seams, pyright-strict, ruff). | lint/type gate | T-14.0-imports, T-14.0-state, T-14.0-protocol (+ inherited AD-1/AD-3 gates) |
| **L1** | Pure unit — one pure function, no I/O, no wiring. | tier-1 (`poe check`) | 12 tests |
| **L2** | Component/integration in-process — multiple units wired through one slice / one warm-up sequence, deterministic, no OS process. | tier-1/2 | 15 tests |
| **L3** | Contract tests — CT-04/23/29/32 conformance, AD-8 protocol substitutability, fingerprint reproduction, taint/world-derivation. | **tier-2** (`poe check-integration`) | 10 tests (2 of which are 14.8-blocked) |
| **L4** | Scenario / golden-path — SCN-0012 golden-slice determinism, loop-not-forked, look-ahead-prevention narrative. | **tier-2** | 5 tests (1 of which is 14.8-blocked) |
| **L5** | System / orchestrated — process-per-run concurrency invariance. | tier-2/system | 1 test, **shared with Epic 15** (T-14.7-d) |
| **L6** | Non-functional / property-based — hypothesis invariants over arbitrary inputs; metamorphic determinism. | tier-2 | 4 properties (T-14.3-e, T-14.1-P, T-14.2-P, T-14.7-c metamorphic half) |

**Lower-level-wins applications:**
- Clock monotonicity is asserted at **L1** (T-14.1-a/c) with an **L6** property (T-14.1-P) as breadth, not a duplicate concrete case.
- Forming-bar non-actionability lives at **L2** (T-14.3-b) with the **L6** property (T-14.3-e) covering the arbitrary-boundary space `loop.py`/`bars.py` branches cannot enumerate by hand.
- Determinism is proven at **L4** (T-14.7-a) once end-to-end; **L1/L2** tests assert the *components* it derives from (pure functions, pinned order) rather than re-running the golden slice.
- Order-identity is asserted at **L1** (T-14.2-a exact order) and **L3** (T-14.2-e fingerprint change) — these are two distinct behaviours (execution order vs identity consequence), not a duplication.

---

## Section 6 — Fixtures, Data & Determinism Strategy

**Fixtures (controlled test fixtures are permitted under L6/DEC-0007; no product mock data, no default strategies shipped):**
- **Golden slice corpus:** a small, fully-declared, deterministic multi-stream tick/bar fixture with a known completed-boundary layout and a fixed embargo, sufficient to drive all six sub-phases and a warm-up→trading transition. It is the substrate for T-14.7-a/b/c. It must be checked into `qa/` fixtures, never sourced from a provider at run time (B-11).
- **Stub adapters:** in-memory fill/slippage/cost port stubs implementing the three Protocols; a replay-clock built on the fixture cursor; a poisoned system clock that raises on read (T-14.1-g); a stub strategy that mints a phase-5 intent on cue (T-14.2-b) and one that attempts a forming-bar act (T-14.3-b).
- **CT-23/CT-29/CT-32 fakes** are shape-faithful to the ratified contracts (fields, unit-kinds, refusal categories) — a test that passes against a shape-unfaithful fake is itself a finding.

**Determinism strategy (the spine of a T1 audit):**
1. **No ambient time below the composition root.** L0 import gate (T-14.0-imports) + runtime poisoned-clock (T-14.1-g) together prove the negative.
2. **No ambient nondeterminism.** T-14.7-c perturbs wall clock, env vars, process start, and hash-seed incidentals and asserts an unchanged fingerprint. Run under `PYTHONHASHSEED` variation to catch set/dict-ordering leaks.
3. **Identity is order.** Fingerprint-change tests (T-14.2-e) prove the pinned order and declaration order are *in* identity; the metamorphic test proves nothing *else* is.
4. **Property breadth over the weak spots.** Hypothesis properties (Group I) drive `bars.py` and the intent-resting logic across input spaces that hand-written cases (and the current 56% `bars.py` branch coverage) miss.

**Refusal discipline.** Every "is refused" assertion (T-14.1-h, T-14.2-f, T-14.4-b, T-14.5-a/c/e/f, T-14.6-*) checks a **returned** CT-04 typed refusal with the correct category — never a raised exception across a public boundary (CT-04 invariant; exceptions reserved for programmer error).

---

## Section 7 — Coverage Targets & Weak-Spot Plan

**Global posture.** Coverage is a *floor and a map*, never the goal — a green line with no assertion is a finding. Targets below are gates for the epic to pass audit; a shortfall is recorded, not waived.

| Target | Floor | Rationale |
|---|---|---|
| `runloop/` package line coverage | ≥ 90% | T1 epic; every result derives from it. |
| `runloop/` package branch coverage | ≥ 85% | Branch is where order/cancel/warm-up guards live. |
| **`loop.py` branch coverage** | **≥ 90%** (from current density at CC 26) | Every branch of the six-phase switch, the cancel-boundary exit, the limit-breach exit, and the warm-up gate must be hit by an assertion (Groups B/D/F). CC 26 means ≥ 26 independent paths — enumerate them and map each to a test ID in §8. |
| **`bars.py` branch coverage** | **≥ 90%** (from 56%) | The 44% unexercised branch space is exactly the forming/completed decision surface. Group C + the T-14.3-e property must close it. |
| Mutation sensitivity (loop.py, bars.py) | spot-check | For the P0 guards (order, forming-bar, cancel), a mutation that flips the guard MUST fail a test; if it survives, the test is decorative — record as a finding. |

**Weak-spot execution order (do the risky work first):**
1. `bars.py` completed-boundary + forming-bar (Group C incl. property) — closes the largest coverage gap and the highest-severity leak.
2. `loop.py` six-phase order + identity (Group B) — the P0 identity guarantee.
3. `loop.py` cancel/limit/warm-up exits (Groups D, F) — the high-CC branch tail.
4. Determinism end-to-end (Group G) — depends on 1–3 being green.

---

## Section 8 — Execution, Traceability Matrix & Exit Criteria

**Execution.**
- Run from the worktree root via `uv run pytest qmb/tests/runloop -q` (tier-1) and the project's `poe check-integration` band for L3/L4/L5 (tier-2). Properties: `uv run --with hypothesis pytest ...` if hypothesis is not in the synced dev group.
- All tests live under `qa/` per the audit's write-boundary; source is read-only evidence. A failing test is a **finding recorded in this epic's findings artifact**, never a reason to edit `runloop/` source or soften an assertion.

**Traceability (requirement → test → priority → level → status):** every R1–R37 maps to ≥1 test.

| Req | Test IDs | Prio | Level(s) | Status |
|---|---|---|---|---|
| R1 | T-14.0-imports, T-14.1-g | P0 | L0,L2 | planned |
| R2 | T-14.1-a/-b/-c, T-14.1-P | P0 | L1,L6 | planned |
| R3 | T-14.1-d/-e | P1 | L1 | planned |
| R4 | T-14.1-f | P1 | L3 | planned |
| R5 | T-14.1-i | P2 | L4 | planned |
| R6 | T-14.1-h | P1 | L3 | planned |
| R7 | T-14.2-a | P0 | L1 | planned |
| R8 | T-14.2-b, T-14.2-P | P0 | L2,L6 | planned |
| R9 | T-14.2-c | P2 | L1 | planned |
| R10 | T-14.2-d | P0 | L2 | planned |
| R11 | T-14.2-e, T-14.2-f | P0 | L3,L1 | planned |
| R12 | T-14.3-a | P0 | L1 | planned |
| R13 | T-14.3-b/-c/-e | P0 | L2,L1,L6 | planned |
| R14 | T-14.3-d | P0 | L2 | planned |
| R15 | T-14.3-f | P2 | L4 | planned |
| R16 | T-14.4-a | P1 | L2 | planned |
| R17 | T-14.4-b | P1 | L2 | planned |
| R18 | T-14.4-c | P1 | L1 | planned |
| R19 | T-14.4-d | P1 | L2 | planned |
| R20 | T-14.4-e | P2 | L1 | planned |
| R21 | T-14.5-a, T-14.5-f | P1 | L3,L2 | planned |
| R22 | T-14.5-b, T-14.0-protocol | P2 | L2,L0 | planned |
| R23 | T-14.5-c | P1 | L3 | planned |
| R24 | T-14.5-d | P1 | L3 | planned |
| R25 | T-14.5-e | P1 | L3 | planned |
| R26 | T-14.6-a | P1 | L2 | planned |
| R27 | T-14.6-b | P2 | L2 | planned |
| R28 | T-14.6-c | P1 | L2 | planned (in-loop half; OS cap = Epic 15) |
| R29 | T-14.6-d | P1 | L2 | planned |
| R30 | T-14.7-a | P0 | L4 | planned |
| R31 | T-14.7-b | P0 | L3 | planned |
| R32 | T-14.7-c, T-14.0-state | P0 | L4/L6,L0 | planned |
| R33 | T-14.7-d | P2 | L5 | planned (loop-purity half; concurrency = Epic 15) |
| R34 | T-14.8-a | P3 | L3 | **blocked (Epic 12/13)** |
| R35 | T-14.8-b | P3 | L3 | **blocked (Epic 13)** |
| R36 | T-14.8-c | P3 | L4 | **blocked (Epic 12)** |
| R37 | T-14.8-d | P2 | L2 | planned |

**Exit criteria (epic passes audit when):**
1. Every **P0** test is green and mutation-sensitive on its guard.
2. `loop.py` and `bars.py` meet their §7 branch floors, each covered branch tied to an assertion.
3. Determinism (T-14.7-a/-b/-c) is green under `PYTHONHASHSEED` variation.
4. Every "is refused" test asserts a *returned* CT-04 refusal of the correct category.
5. Every blocked/partial requirement (R28, R33, R34–R36) has a recorded reason and an owning epic (below).

**Untestable / blocked in Epic 14 isolation (findings, not omissions):**
- **R34–R36 (Story 14.8, QL-7 host / DEC-0183 compiler / conformance sandbox)** — depend on Epics 11/12 (QML CT-33 Bot + host-owned conformance runner) and Epic 13 (config compiler). epics.md marks 14.8 as waiting on Epics 12 and 13. Scaffolds planned; execution deferred until those land.
- **R33 concurrency half** — the loop's *purity/determinism* is testable here (L4); *byte-identical across N OS-process siblings* requires the Epic 15 orchestrator/governor. Owned jointly; execute at Epic 15 integration.
- **R28 OS-enforced cap** — the loop can *cooperatively surface* a typed `aborted` on an in-loop breach signal (testable), but real OS time/memory enforcement is the Epic 15 orchestrator; not testable in `runloop/` alone.
- **Fill/slippage/cost fidelity *content* (B-6 / GAP-0048)** — only the seam, the `optimistic` taint (R24), and the refuse-until-GAP-0048 behavior (R6, R25) are testable now. Whether a fill is *correctly* modeled is untestable until GAP-0048 ratifies the taxonomy — testing it would assert an unratified value.
- **SQS-door modeled-spread input (B-2 tail)** — the read-point is in the loop but the modeled-spread content is an execution-adapter/GAP-0048 concern (Epic 17); no assertion possible on content here.
- **Process authorities absent** — test-design-qa.md (template + L0–L6) and QMX-handoff.md (15 P0/P1 assertions + risk-gate rows) are missing from the worktree; §1/§3/§5 are reconstructed and must be reconciled when restored. This is the single largest caveat on the plan's fidelity to the intended template.
