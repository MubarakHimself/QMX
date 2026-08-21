# Adversarial Review — QMB spine (B-1 … B-14)

- **Target:** `architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md` (status: draft, updated 2026-08-20)
- **Scope:** B-1 … B-14 and the diagrams/conventions they rest on, in interaction with inherited QMF AD-1 … AD-41 (read-only). Not a re-review of the parent. Not an omissions hunt. Deferred rows are in play only where they already let two units diverge *now*.
- **Prior sibling passes (not this job):** `review-currency.md`, `review-reconcile-qmf.md`, `review-rubric.md`. This pass does not re-score their omission/reconcile findings; it recasts only those that are also assembly clashes.
- **Date:** 2026-08-20
- **Grounding (read, not re-reviewed):** parent `ARCHITECTURE-SPINE.md`; `research-backtesting/challenge-mechanics.md`, `challenge-economics.md`, `challenge-override.md`; donor specs `spec-backtest-loop.md`, `spec-fill-fees.md`, `spec-optimization.md`, `spec-mc-significance.md`, `spec-concurrency.md`. Format: parent `reviews/review-adversarial-risk.md`.

---

## 1. Method

I am not hunting for things the spine forgot, and I am not re-opening GAP-0048/0049, live wiring, MCP tool lists, UI rendering, QML, or QMF law. I am building **pairs of units one level down** — the doors, adapters, compilers, ledger writers, result authors and procedure runners a factory agent would write from these B-ids — where *both* units obey every ratified B-id and inherited AD to the letter and the two still cannot be assembled. Recurring pair types (plus three the spine itself minted):

| Pair | Unit A | Unit B | Load-bearing B-ids |
| --- | --- | --- | --- |
| P-1 | CLI door (flags, sequence-diagram compiler) | Python API door (library `run(config)`) | B-1, B-3 |
| P-2 | fill adapter | slippage adapter + fee/cost adapter | B-6 |
| P-3 | `qmb data generate` writer | result-label world deriver / B-14 MC | B-7, B-11, B-14 |
| P-4 | sandbox WriterId ledger fragment | laptop / hub merge-view (Book-bar reader) | B-4, B-5, deployment diagram |
| P-5 | optimizer trial runner (and TPE parent) | Book-bar verdict consumer | B-8, B-4, B-14 |
| P-6 | run-config compiler | Book/BMS fragment author | B-3, B-13, AD-29 |
| P-7 | warm-up pre-seeder | first-slice trading / indicator state | B-2 |
| P-8 | permutation / MC / WF batch aggregator | per-run ledger | B-12, B-4, B-14 |
| P-9 | B-10 canonical-artifact author | AD-32/AD-41 bar + CT-29/CT-32 consumer | B-10, B-4, AD-29..41 |
| P-10 | replay binding / virtual-ledger minter | config-only capital field | B-3, B-4, AD-29, AD-40 |
| P-11 | process-per-run supervisor | library `run()` ledger writer | B-4, B-5, AD-15 |
| P-12 | B-12 tick / HTF stream | B-6 declared-path bar splitter | B-2, B-6, B-12 |

**Severity rule.** Divergence that fails loudly at an AD-4 / B-1 tier-2 gate is rated lower. Divergence where both units run, both pass their own gates, and they write **different identities, different numbers, or different verdicts into the ledger / result label / canonical artifact** — or where the Book-bar reader and the trial runner disagree on what a pass *is* — is critical. Fingerprints and ledger lines are forever; an identity fork under one `optimistic` taint, or a scoreboard that cannot tell a trial from a confirmation, is the class this architecture cannot repair later.

**What this pass is not.** The rubric already named the ungoverned sync hub as a missing B-id; I only keep the hub where B-4's own "merge view" sentence has two legal referents. GAP-0048's missing taxonomy values are not findings; the interim `optimistic` taint *collapsing two fill algorithms into one label* is. Ticket 008's staged funnel is an omission, not a pair, and is left to the rubric.

**Verdict:** the spine absorbed the earlier challenge dossiers on doors, taint-as-claim-class, and label axes, and those closures hold. What it did not close is **assembly**: one sentence of B-2 names both donor warm-up mechanisms; the Book-bar verdict, the B-10 metric set and the AD-32/AD-41 producers are three owners of one pass/fail; B-7 forbids the synthetic world that B-14's own MC rung is required to produce; and the adaptive optimizer cannot exist as a library port under process-per-run without a second, unlabelled state. Fourteen B-ids, eleven places two conformant units mint incompatible evidence.

**Counts: 9 critical, 8 high, 4 medium (21 total).**

Five structural roots (§5) account for seven of the nine criticals.

---

## 2. Critical — both units conform, both pass their gates, and ledger, label, or trade record forks

### C-01 — B-2's warm-up is both donor mechanisms in one sentence, and they do not produce the same first trade

- **Unit A — the pre-seeder (Jesse reading).** B-2: *"Warm-up is a **pre-seeded**, trading-locked phase."* A treats warm-up as out-of-band injection of N bars into indicator state **before** the loop starts (`spec-backtest-loop.md` §2.A: Jesse `inject_warmup_candles_to_store`; the loop never iterates those bars; the strategy is never called). "Acting during warm-up is a typed refusal" is vacuously true — there is no warm-up slice to act in. The first slice of the loop is a live trading slice with hot indicators.
- **Unit B — the trading-locked phase (LEAN reading).** The same sentence: *"a **trading-locked phase**."* B runs warm-up bars through the **same** event-slice loop, strategies are called, order intents refuse (`spec-backtest-loop.md` §1, LEAN `SetWarmUp` / `IsWarmingUp`). Indicator and structure state are the path-dependent product of those slices, including any intra-slice fill-model interaction with *resting* state that A never simulated.

**The incompatible build.** Identical bot, identical data, identical resolved config. A's first tradable instant is the run-spec start; B's is start + warm-up length. A's indicators were seeded by a bulk load that did not run the fill/slippage/fee ports (B-6) or the per-slice sub-phase order (B-2) on those bars; B's did. The trade record (B-10), the ledger verdict (B-4) and the result label's evidence range (AD-12) differ, and both runs are honestly labelled — neither unit has anywhere to record "which warm-up mechanism I am," because B-2 names one phase.

Compounding it: AD-21 already has a warm-up, as the split-manifest's purge/embargo default (*"warm-up + confirmation-delay bound"*). Unit A subtracts it once at the split and again as loop pre-seed (double-skip). Unit B treats the split embargo as the warm-up and runs no second phase. Three legal first-trade instants, one B-id.

**Severity: CRITICAL.** Permanent look-ahead / look-behind fork on every run, invisible in the label.

**Closing clause (B-2).** *"Warm-up is in-loop: the same event-slice loop, same sub-phase order, same adapters, trading locked. Acting — minting an entry intent, an exit intent, or any command — is a typed `policy rejection`. Pre-seeding indicator buffers without replaying slices is not warm-up and is not a legal substitute. Warm-up length is the split-manifest embargo already declared under AD-21 for the producers the stream set cites; the loop does not add a second window. The evidence range on the result label is the trading interval, not the warm-up interval, and the warm-up mechanism identity is a single pinned value (`in-loop-locked`) in the resolved config."*

---

### C-02 — "Per-slice sub-phase order … is fixed and documented" never pins the order, so look-ahead is a local documentation choice

- **Unit A — the run-loop author, strategy-first.** B-2: *"per-slice sub-phase order and instrument order are **fixed and documented**, making identical inputs produce identical slices."* A documents, in the runloop package, the order: ingest slice → indicators → strategy intents → B-6 fills on this slice's path. The strategy sees this bar's close (and this HTF bar's close, B-12) before fills on the same slice are decided. Identical inputs produce identical slices **inside A's build**.
- **Unit B — the run-loop author, resting-fills-first.** B documents the donor-LEAN / honest-Jesse fill-path order: ingest slice → B-6 executes resting orders against the declared intra-slice path → then indicators → then strategy intents, which cannot fill against the same slice's close. Identical inputs produce identical slices **inside B's build**.

**The incompatible build.** B-2's determinism guarantee is intra-implementation. Cross-implementation, the same resolved config yields different trade records because the spine **acknowledged** the order is load-bearing and then left it to each unit to "document." Instrument order is the same hole at a smaller grain: A sorts by `(venue, symbol)` ascending (AD-10 canonical); B uses B-12 stream-set declaration order. A cross-instrument bot that sizes the second name off the first name's fill in the same slice gets two different books.

This is not deferred GAP-0048 fidelity. It is the loop's own causality, which B-2 exists to freeze.

**Severity: CRITICAL.** Look-ahead vs not, under one fingerprint recipe.

**Closing clause (B-2).** *"The sub-phase order is spine-pinned, not package-documented: (1) advance frontier clock to the slice instant; (2) ingest the slice's events; (3) execute **resting** orders through the B-6 ports against the declared intra-slice path; (4) update indicators/structure on closed data only; (5) strategy callbacks mint intents; (6) new intents are **not** eligible to fill against this slice's path — they rest for a later slice. Instrument order inside a slice is the stream-set declaration order (B-12), which is identity content of the resolved config. A build that documents a different order is non-conformant, not an alternative."*

---

### C-03 — Three owners of "pass": B-10's metric set, B-4's Book-bar verdict, and AD-32/AD-41's governed producers

- **Unit A — the `results/` artifact author.** B-10: *"every run emits one canonical machine-readable result artifact: **unit-kinded exact-money metrics (the named metric set, versioned)** … trade record."* A mints a QMB-local set (`pnl`, `max_drawdown`, `trade_count`, …), versions it, puts it in the artifact. Chart series and the trade record live there. Agents read this, never renderings.
- **Unit B — the ledger / Book-bar consumer.** B-4: the completion line carries *"the unbiased end verdict (pass/fail against **the Book's declared bar**; `unrated` when the bar is not yet ruled)."* B compares A's metrics to the Book's `admission_bar` (AD-32: a set of `measure_identity` + comparison + threshold + `evidence_requirements`). Inherited AD-29..41: QMB consumes, never redefines.
- **Unit C — the CT-32 / AD-23 producer author (forced by the parent).** AD-41: the performance-result container is CT-32; *"a performance metric is a **governed producer under AD-23**."* AD-32: *"Parity is structural: a presented result whose producer contract format versions differ from the bar's declared requirements **does not satisfy the bar** — a refusal, never a warning."*

**The incompatible build.** A's `max_drawdown` is not the Book's `measure_identity`. B either (i) maps by English name and **passes a bar AD-32 says is unsatisfied**, writing `pass` into the ledger — the scoreboard and the evidence diverge, the thing B-4 exists to prevent — or (ii) correctly refuses parity and every QMB run is `unrated` until someone reimplements AD-23 producers inside QMB, at which point A and C are two metric vocabularies for one run and B-10's "one canonical artifact" is a lie. Both of B's readings are conformant: B-4 never says the bar is AD-32's packet (world, role, producer versions) rather than "the numbers the Book wrote down," and B-10 never says the named set *is* the AD-23 roster.

Second fork, same root: B-10's "exact-money metrics" cannot type a Sharpe (AD-40 `dimensionless-ratio`, AD-41 float-with-label-derived-identity). B-8: *"Objectives are named metrics from B-10's canonical set."* The optimizer's default industrial objective is then either undeclarable (A) or smuggled in as a local float (a third unit), and neither figure is the one the Book bar cites.

**Severity: CRITICAL.** The product face of QMB is "did this bot clear the Book." Three units, three answers.

**Closing clause (B-10 + B-4).** *"B-10's named metric set **is** the AD-23/AD-41 governed-producer roster; QMB does not mint a parallel vocabulary. The canonical artifact is a CT-32 performance result (AD-41) plus display-only chart series that are **explicitly AD-10-excluded** from identity (see H-04). The B-4 verdict is a read of that CT-32 against the Book's `admission_bar` under AD-32 parity (producer contract versions, unit-kind, comparison rule) and under the bar's `evidence_requirements`; a world/role miss is `unrated`, never a numeric pass. Optimizer objectives (B-8) are `measure_identity`s from that same roster."*

---

### C-04 — B-7 makes every synthetic consumption `world=simulated` → policy rejection; B-14's MC candle-perturbation rung is required to produce labelled ledger evidence from exactly that

- **Unit A — the store / label deriver.** B-7: *"Synthetic-origin data is tainted at the store level; **any run consuming it is world=simulated (policy rejection for governed evidence until GAP-0048)**."* World is derived, never caller-declared. A taints `qmb data generate` output (B-11) and any in-memory perturbation that lands in a store. Every consumer is `simulated` and cannot write governed evidence.
- **Unit B — the B-14 MC author.** B-14: the ladder includes *"Monte Carlo (trade-shuffle; **real-seeded candle perturbation**)"*, each rung *"producing labelled runs and ledger entries under B-3/B-4."* B-7's own second paragraph: *"real-seeded perturbation (block-bootstrap class) **may additionally claim robustness** under the MC procedures of B-14."* B therefore produces governed robustness evidence from perturbed candles.

**The incompatible build.** A's reading of paragraph 1 makes B's rung illegal: the MC candle path either (i) writes perturbed candles into a store (B-7 taint → `simulated` → policy rejection → no ledger line, contradicting B-14) or (ii) perturbs in memory to dodge the store-level taint, in which case world stays `replay` and B-7's taint is a no-op for the one consumer it exists to classify. Trade-shuffle is the same fork: A treats shuffled equity as synthetic-origin; B treats it as a statistical procedure over real trades, world remains `replay`.

This is not GAP-0048. The deferred row parks simulated-time typing that *unlocks* `world=simulated` for governed evidence. Until then, paragraph 1 says "no" and paragraph 2 / B-14 say "yes, robustness." Two conformant units, opposite claim classes, opposite worlds, opposite ledger-ability.

**Severity: CRITICAL.**

**Closing clause (B-7 + B-14).** *"Store-persisted fabricated-from-scratch data (random-walk class, `qmb data generate`) is store-tainted; any run that **reads the store** is `world=simulated` and a `policy rejection` for governed evidence until GAP-0048. **Procedure-ephemeral** perturbation — B-14 trade-shuffle and real-seeded block-bootstrap that never persist a synthetic series into a data room — does not change world: the run remains `world=replay`, the procedure identity + seed enter the label (B-13), and the claim class is robustness-only (L20), never edge. Claim class is a label field distinct from world."*

---

### C-05 — Every optimize trial, MC path and WF window ledgers `pass/fail` against the Book bar, so the scoreboard is the search

- **Unit A — the trial runner.** B-8: *"Every trial is a first-class run under B-3/B-4 — its own resolved config, log, and **ledger line**."* B-4 binds *"all run kinds (backtest, **optimize trial**, MC, significance, walk-forward)"* to one entry shape: *"the unbiased end verdict (**pass/fail against the Book's declared bar**)."* A scores every trial against the bar. Most of a TPE search will fail it; two lucky in-sample points will pass it. That is what the sentences say.
- **Unit B — the Book-bar reader.** B-4: the merge view *"is what 'the Book sets the bar' reads."* B folds ledger lines for this Book/bot. It sees 400 `fail` and 2 `pass` for the same bot on the train split (B-8's declared train/test lives on the run spec, not on the verdict).

**The incompatible build.** Does the bot pass the Book? A's ledger says twice yes. B has no legal rule that a trial's `pass` is a different noun from a confirmation backtest's `pass` — B-4 used one verdict vocabulary for every run kind. GAP-0049 parks *attempt counting* and *thresholds*; it does not park the **kind of the verdict**. The Deferred row even advertises the opposite: *"B-4/B-8 ledger completeness accrues their raw material regardless."* Raw material with the same `pass` tag as the confirmation run **is** the p-hacked scoreboard B-4's Prevents clause names (*"the scoreboard and the evidence diverging"*).

"Unbiased" does not save it. One unit reads unbiased as "written at completion, not mid-run" (the log-during / ledger-at-end rule). Another reads it as "test-split only." Both are in the Prevents clause. Neither is in the Rule.

**Severity: CRITICAL.** In-sample search results become the Book's official record.

**Closing clause (B-4).** *"The ledger line's verdict field is a **discriminated kind**, not a reuse of `pass/fail`: `bar-pass | bar-fail | unrated | aborted` are legal only on a run whose run spec declares `role = confirmation` (the test/holdout split, AD-21) and whose adapters are the Book-declared set (see H-02). Optimize trials, MC replicates, significance replicates and WF **train** windows ledger `trial | replicate` plus the objective metric, **never** `bar-pass`/`bar-fail`. The Book-bar read (B-4 merge view) selects `role = confirmation` lines only. 'Unbiased' means exactly this selection, not 'written at completion'."*

---

### C-06 — B-6 declares three ports and one function, and never says who moves the price; until GAP-0048 both answers stamp `optimistic`

- **Unit A — the fill adapter.** B-6: *"fills, slippage, and costs are **three separate ports** (order intent × market state → Fill | NoFill + itemized costs …)."* The parenthetical is one function. A implements that function as the fill port: Fill|NoFill **includes** the slipped price; itemized costs are computed inside the same call; the other two "ports" are internal helpers. Intra-slice path-crossing uses the already-slipped price, so a limit that would not cross after spread does not fill.
- **Unit B — three adapters, LEAN order.** `spec-fill-fees.md` §2A (the interface the spine studied): fill decides whether/at-what-price, **then** slippage adjusts, **then** fee charges cash. B's fill port crosses on the unspread path; slippage then moves the fill; a fill that is now outside the bar still stands. Financing/admin fee (AD-8/AD-41 vocabulary, B-6's own note) is applied by the cost port on a cadence B picks (per slice vs AD-8 17:00 NY rollover).

**The incompatible build.** Same intent, same bar, two fill prices, two cost totals, two trade records. B-6 says each adapter carries *"a declared fidelity identity that enters the result label"* **and** *"Until GAP-0048 … all fills carry an `optimistic` taint."* Two readings of the identity, both legal while the taxonomy is deferred:

1. The identity **is** `optimistic` until GAP-0048 — A's and B's results share a label axis and are compared as the same experiment.
2. The identity is an adapter-local string (`ohlc-then-spread` vs `spread-then-cross`) **plus** the taint — labels differ, but the Book-bar reader (C-05) still has to know whether they are the same test condition.

The Deferred table parks taxonomy *values* and forex *content*. It does not park **composition order**, and composition order is enough to fork every number in the artifact. The `optimistic` taint closes the claim-class hole (cannot claim edge, cannot spend split budget); it does not close the identity hole. Two optimistic algorithms are not one algorithm.

**Severity: CRITICAL.** Different money in the trade record under one taint.

**Closing clause (B-6).** *"Composition is pinned: (1) fill port decides Fill|NoFill and a **pre-slip** price by declared-path crossing inside the slice; (2) slippage port maps that price to a post-slip price and may veto the fill (`NoFill`) if the slipped price is not a legal print on the slice; (3) cost port itemizes cash charges (commission, financing/admin fee at the AD-8 accounting rollover, not per-slice) on the post-slip fill. Three ports, that order, that veto. Fidelity identity is **adapter-id + composition-version + taint**, and `optimistic` is the taint field, never the identity. GAP-0048 replaces taint values; it does not later invent the pipeline."*

---

### C-07 — The adaptive sampler cannot live in the library, cannot live in the door, and cannot live in Optuna's store, yet B-8 requires it

- **Unit A — the optimizer as a library port.** B-8: *"the optimizer is a **library port** whose default adapter is a genuinely adaptive sampler (TPE-class)."* AD-15 / inherited row: the library never spawns threads or background work; Conventions: *"No module-global mutable state anywhere in the library … explicit context objects only."* A holds the TPE model in a context object inside `optimize/`, suggests a point, runs the trial by calling `run()` in-process. Adaptive state is in-process, sequential, reproducible from (sampler identity, seed, prior trials). B-5's 12–14 concurrent **processes** are not used for trials — B-5 binds "all concurrent execution," so A is arguably non-conformant the moment it stays in-process. If A instead spawns processes, the library has spawned, which AD-15 forbids.
- **Unit B — the door/runner as the process owner.** B-5: concurrent runs are separate OS processes; the application owns concurrency. B-1: doors carry **no domain logic**. TPE's next-point function *is* domain logic. B therefore puts TPE in the CLI/process-runner, suggests 12–14 points from the same study snapshot (the only way to fill B-5's concurrency), spawns 14 trial processes, collects ledger lines, updates the study. Parallel ask-from-stale-history is a different search from A's sequential ask; the label still carries the same sampler identity + seed (B-8, B-13).
- **Unit C — Optuna's own study store.** Stack pins `optuna` 4.9.0. Optuna 4.x persists trials via SQLAlchemy (SQLite is AD-19-legal). C uses that store as the adaptive state, *in addition to* B-4's ledger. B-8 says search history is complete *"by construction"* via trial ledger lines. Now there are two histories; they diverge on crashed trials (see H-05) and on which objective value was recorded.

**The incompatible build.** A, B and C are each the only way to satisfy a different sentence, and any two of them cannot assemble: library-state vs door-state vs third-party store; sequential vs 14-wide stale-ask; one history vs two. Replaying "the same" optimize from the label (sampler + seed) does not recover the parameter sequence unless the **prior-trial fingerprint chain** is in the label, which B-8 does not require. Jesse's donor lesson (`spec-optimization.md` §2: Optuna used as a ledger while the sampler was `np.random`) is exactly this split; B-8 exists to not repeat it and then recreates it at the process boundary.

**Severity: CRITICAL.** Unreproducible search under an honest-looking label.

**Closing clause (B-8 + B-5).** *"Sampler state is a first-class, fingerprinted **study artifact** in the run's parent directory, not a library global, not a door, not Optuna RDB. The optimizer port is `ask(study) → params` and `tell(study, result) → study'`; both are pure. Process-per-run applies to **trials**; the parent campaign is one OS process that only asks, spawns, waits, tells. Parallel `ask` without an intervening `tell` is refused (`unsupported capability`) — TPE-class adapters are sequential; a non-adaptive grid/Sobol adapter may ask a declared batch. Every trial label carries `study_fp` (the study artifact before this ask) + trial index + sampler identity + seed. Optuna may implement `ask`/`tell`; its storage adapter is not a QMB ledger."*

---

### C-08 — A QMB run either mints an AD-29 replay binding (and then has R) or it doesn't (and then it cannot consume the Book it claims to test)

- **Unit A — the config-only compiler.** B-3: a run consumes one resolved run-config compiled from flags, run spec, **Book + BMS config fragments**, workspace defaults. A inlines the Book's `money_rules` numbers into the config, puts a `starting_capital` field on the run spec / flags, and sizes with a local function of those numbers. No CT-28 binding record is minted — QMB is an application, QMF ledgers/bindings are "node runtime behavior" the parent scope excluded. B-4 still writes pass/fail against the Book bar.
- **Unit B — the inherited-machinery consumer.** Inherited row: AD-29..41 *"QMB consumes, never redefines."* AD-29: *"a replay of a binding **mints a different binding identity**"* (`world` is live-constant for V1 live bindings; replay is a different identity by rule). AD-40: `r_unit_price`, `book_capital` (virtual-ledger equity at period-open), admission sizing, frozen R faces — all per **binding**, not per config field. B mints a `world=replay` binding for the run, sizes through the Book door, writes virtual positions and CT-29 exits.

**The incompatible build.** A's `starting_capital` is a free field (flags beat the Book fragment, B-3), so two runs of "the same Book" have two R denominators and two bar outcomes. B's capital is the binding's virtual ledger, whose seed is whatever B chose (paper starting balance from AD-30's `paper` section — but this is not paper, paper is `world=live`; BMS accounting; a new QMB-only seed). The parent stated the position (*"the backtesting sitting inherits a stated position, not an accident"*) and QMB's B-ids never pick it up. The trade record (B-10) under A is a QMB-local schema; under B it is CT-29. C-03's bar then evaluates different objects.

This is not re-deciding QMF. The parent already ruled that replay mints a binding. The hole is QMB B-3 talking only in fragments, so a factory agent can ship A and another can ship B.

**Severity: CRITICAL.** Two R figures, two exit schemas, one Book name on the label.

**Closing clause (B-3 + B-4).** *"Every QMB run mints exactly one AD-29 binding with `world=replay` (a different identity from any live binding of the same Book instance, as AD-29 already states). `starting_capital` is not a flag; it is the binding's virtual-ledger seed, taken from a **mandatory** run-spec field that the Book fragment may default and that flags may not silently replace — a flag override of the seed stamps `seed_overridden` on the binding and forces B-4 `unrated` (H-02). Sizing, R freeze, and exits consume `qmf-risk` contracts through the composition root; the B-10 trade record **is** the CT-29 stream of that binding (C-03). No QMB-local position schema."*

---

### C-09 — B-4's "merge view over the fragments" has two legal referents; they are the two machines in the spine's own diagram

- **Unit A — the sandbox writer.** B-4: ledger is *"physically WriterId-scoped fragment files (one per writer context, AD-15 … concurrent processes never share a file)."* B-5: *"a run's completion-ledger append (to **its own fragment**, per B-4) is its **single write-back moment**; merging happens only in read views."* A writes `ledger.{WriterId}.jsonl` beside the sandbox's uv-installed state (or in the run dir — B-4 also says logs live *"in the run's own directory"* and never relocates the fragment). Write-back has happened. A is done.
- **Unit B — the laptop Book-bar reader.** B-4: *"'the ledger' as read is a **merge view over the fragments**, and it is what 'the Book sets the bar' reads."* B merges the fragments it can see — the laptop's. The deployment diagram draws `HUB[(sync hub: registry + ledger files)]` with `CLI1 <--> HUB` and `CLI2 <--> HUB`, but no B-id names the hub, the fragment set, the as-of, or the merge authority. B is conformant: it merged every fragment in scope.

**The incompatible build.** The operator mints `scalping@3` on the laptop; sandbox fragments still score `scalping@2`; B's merge view is the bar; A's completed `pass` lines are not in it (or, after a partial copy, some of them are). Two legal bars for one Book. This is the challenge-mechanics Attack 1/2 pair recast as assembly: not "please specify sync" as an omission, but **B-4's own sentences locating the write and the read in two places with no identity for the set being merged**.

AD-12/AD-19 make a third unit: a merge that includes a `world=live` paper fragment and a `world=replay` fragment is a cross-world read (`policy rejection`). B-4 never scopes the merge by world or role. In v1 QMB is *almost* single-world, except the inherited row explicitly admits *"paper=world live"* into QMB.

**Severity: CRITICAL.** The Book-bar read is not a defined object.

**Closing clause (B-4).** *"A ledger fragment is a WriterId-scoped JSONL file whose **home** is a named, world-and-role-scoped ledger directory, not the run directory (run dirs hold logs + the B-10 artifact; the completion line is appended to the ledger directory). The merge view is over **that directory at a stated as-of**; the as-of instant enters every bar-read. Cross-machine visibility is a **copy of fragment files** into that directory (operator-gated or a designated reducer); it is not a live service (DEC-0084). A merge never crosses AD-12 worlds or AD-9 roles. A run whose Book/BMS fragment was superseded after the compiler's `registry_as_of` (B-13) ledgers `unrated` with `stale evidence` context, and does not mint `bar-pass`."*

---

## 3. High — two legal contracts; a gate or an operator can still see the wreck, but the wreck is already labelled

### H-01 — B-3 puts Book and BMS fragments in one precedence tier; AD-29 gives them an authority order that is a collision rule

- **Unit A** lets invocation flags and the run spec override both fragments equally (B-3's list: `flags > run spec > Book + BMS > defaults`). On a same-key clash between Book and BMS fragments, A last-wins by JSON merge.
- **Unit B** reads inherited AD-29: Book owns admission/sizing/doors/leash/profile; BMS owns accounting/constraints/journals/KSA/reporting. B refuses a same-key clash as `invalid input`, or lets BMS win on constraint keys.

**Divergence.** The resolved-config fingerprint (B-3 ledger key, B-13 label) differs for the same Book@version + BMS@version because the compiler's intra-tier rule is undeclared. Named condition presets (*"config fragments like any other"*) have **no** listed tier at all — A puts `stress-spread` with the run spec, B with the Book.

**Severity: HIGH.**

**Closing clause (B-3).** *"Book and BMS fragment key-spaces are disjoint by AD-29 authority; a colliding key is `invalid input`, never last-wins. Named condition presets are a **run-spec** layer (flags > run spec+presets > Book fragment > BMS fragment > defaults) and may not override BMS constraint keys. Every layer that contributed is a lineage edge on the resolved artifact."*

### H-02 — Flags legally compile a run the Book did not author, and B-4 still scores it against that Book's bar

B-3: flags beat the Book fragment. B-4: verdict is against the Book's declared bar. A run with `--fill zero-slippage` (or a replaced seed, C-08) is a legal resolved config whose fingerprint differs from the Book's, **and** a legal `bar-pass` under that Book's name.

- **Unit A (compiler)** stamps the Book name@version into the label because B-13 says Books are resolved name@version, and scores the bar because B-4 says so.
- **Unit B (Book author)** assumes the bar is evaluated under the Book's own test conditions (the operator's "CLI updates when I create a Book" — Capability map row 2).

**Severity: HIGH.** Same scoreboard, different exam.

**Closing clause (B-3 + B-4).** *"A flag or run-spec overlay that changes a Book-declared test condition (fill/slippage/cost adapter identity, stream set, seed, bar-path, split) is a **condition override**: the label carries the Book identity as lineage, the verdict is `unrated` with `condition-override`, and the bar-read ignores the line. Overrides of non-test keys (output path, log verbosity) are ordinary flags."*

### H-03 — B-14 ladder rungs are "runs" and also "procedures that contain runs"; MC / WF / significance cardinality forks the ledger

B-4 lists `MC` and `significance` as run kinds (singular). B-14 says each ladder function produces *"labelled runs and ledger entries"* (plural). B-8's "every trial is a run" is the obvious analogy.

- **Unit A:** one `qmb montecarlo` invocation = one run, one config, one ledger line; 1000 shuffles live inside the B-10 artifact as a distribution. Crash of shuffle 437 is a log line, not a ledger line.
- **Unit B:** each shuffle / bootstrap replicate / WF window is a B-5 process-per-run with its own ledger line (B-12 Cartesian isolation). Batch aggregation is a read-time view (B-12).

**Divergence.** A's Book-bar reader (after C-05's fix, the confirmation line) sees one MC verdict; B's sees 1000. Procedure identity, RNG provenance and core-count (Jesse's significance seed is `base + batch_index` per CPU batch — `spec-mc-significance.md` §2A) enter one label or a thousand, and p-values depend on `n_jobs` unless pinned. Two contracts for one rung.

**Severity: HIGH.**

**Closing clause (B-14).** *"Each ladder invocation is one **campaign run** (one resolved config, one ledger line of kind `procedure`, verdict `unrated` w.r.t. the Book bar). Inner replicates are child runs under B-5/B-12 only when the procedure's versioned contract says so; MC trade-shuffle and significance bootstrap are **in-artifact** distributions (no child ledger lines); MC candle-perturbation and WF windows **are** child runs, because each consumes a different data identity. Every procedure contract pins `n_replicates`, `n_jobs = 1` (reduction is sequential; cores do not enter identity), seed, and generator."*

### H-04 — B-10's one artifact contains lossy chart series, so "one run, one artifact" forks on downsample choice

B-10: *"every run emits **one** canonical … artifact"* including *"chart series as data … **downsampled by a declared sampler**."* Downsampling is computation that changes bytes.

- **Unit A** treats series as identity content (AD-10 default). Two report resolutions = two artifacts = two fingerprints for one run, contradicting "one."
- **Unit B** treats series as display-only. Without an **explicit versioned AD-10 exclusion** that is implementer judgment, which AD-10 forbids.

**Severity: HIGH.** Pure identity fork.

**Closing clause (B-10 + AD-10).** *"Chart series in the canonical artifact are display-only, excluded from `fp1` by a versioned declaration in the result contract. The identity-bearing body is the CT-32 measures + CT-29 trade/exit records + label. Downsample sampler is a renderer input, not a run-config field."*

### H-05 — "Exactly one ledger line" and "never silently absent" assign the aborted write to two units

B-4: *"At completion **the run** appends exactly one ledger entry"* and *"Crashed/aborted runs ledger as `aborted` … **never silently absent**."* A SIGKILL/OOM child cannot append (B-5's 12–14 near the memory ceiling makes this ordinary, not exotic).

- **Unit A (library)** writes the line in `run()`'s `finally`. Caught exceptions = one line. SIGKILL = silent absence. Letter of "the run appends."
- **Unit B (process supervisor)** sees non-zero/missing and writes `aborted` on the child's behalf, satisfying "never silently absent." On a caught exception the child already wrote, and B writes again.

**Divergence.** Two lines for one run (B-4 broken) or silent absence (B-4 broken). Both units are enforcing B-4.

**Severity: HIGH.**

**Closing clause (B-4 + B-5).** *"The library writes the completion line for every run that returns. The process supervisor is the **only** writer of `aborted` for a child that exits without a line (SIGKILL, OOM, power), and it refuses to write if the fragment already contains that run id. 'Never silently absent' is a supervisor obligation, not a library obligation. Duplicate run ids in one fragment are `storage failure`."*

### H-06 — B-11 fetch-at-runtime vs B-3 "config fingerprint is the ledger key" vs Conventions "run id = config fp + occurrence"

B-11: Dukascopy is fetched at run-time under the user's relationship. B-13: data/split fingerprints enter the **label**, separately from the resolved-config fingerprint. B-3: the resolved artifact's fingerprint *"is the **ledger key**."* Conventions: *"run id = fingerprint of the resolved run-config **+ occurrence id**."*

- **Unit A** keys the ledger by config fp (B-3). Two fetches of the same spec, provider revised a candle, data fps differ, labels differ, ledger key collides: AD-10 silent-accept if someone made the line byte-identical (it isn't) or a true collision alarm, or an overwrite of the first occurrence.
- **Unit B** keys by run id = config fp + occurrence (Conventions). Every invocation is a new line; the Book-bar reader (C-05/C-09) must further select, and "the same experiment" has no canonical line.

**Severity: HIGH.** The ledger's primary key is stated twice.

**Closing clause (B-3 + Conventions).** *"The ledger's identity key is the **run id** (resolved-config fp + occurrence id). The resolved-config fp is a **query axis**, not a unique key. Data is resolved **before** the config is sealed: fetch/verify (B-11) produces the data/split fingerprints that **enter the resolved config** (and therefore its fp), or the run refuses `stale evidence`/`unavailable dependency`. A later provider revision cannot silently share a config fp with an earlier fetch."*

### H-07 — A data-only HTF stream's current bar is visible, or it isn't; B-12 only forbids undeclared streams

B-12: *"strategies read other streams only through the declared set."* B-2 prevents look-ahead *"via time arithmetic,"* not via the current forming higher-TF bar.

- **Unit A** exposes the in-progress HTF bar on the slice (it is in the declared set; its Instant equals the LTF close that completes it).
- **Unit B** exposes only **closed** bars; the HTF value on the slice is the previous close.

**Divergence.** Classic HTF look-ahead, both legal, both deterministic, different trades, same stream-set fingerprint unless closed-vs-forming is identity.

**Severity: HIGH.**

**Closing clause (B-12 + B-2).** *"Strategies read **closed** bars only. A bar is closed at its interval's exclusive end Instant. The forming bar of any stream is not in the strategy's readable set; fill ports (C-02 step 3) may still use the current slice's intra-bar path. Closed-only is identity content of the loop, not a bot option."*

### H-08 — B-6's fill path is always bar-splitting; B-12 lets a tick stream join the set; one of those sentences is ignored

- **Unit A (fill adapter)** always splits the **trading-role** timeframe bar (`declared-path bar splitting … never end-of-bar teleporting`). A tick stream in the set is data-only (indicators), never a fill input.
- **Unit B (fill adapter)** if a tick/quote stream is present, fills on ticks; bar-splitting is the fallback. Higher fidelity, still `optimistic` (C-06), still B-12-legal.

**Divergence.** Same stream set, different fills. GAP-0048 will later *name* this difference; nothing stops B shipping now under the same taint.

**Severity: HIGH.** Deferred taxonomy does not hold this seam; C-06's adapter-id + taint split does, if closed.

**Closing clause (B-6).** *"Fill reads only the trading-role stream(s) declared in the stream set. V1 fill is declared-path bar splitting on that stream's bars, even if a tick stream is present as data-only. A tick-fill adapter is a different adapter-id and remains `optimistic`-tainted until GAP-0048; it is not an implicit upgrade when ticks happen to be declared."*

---

## 4. Medium — cheap tighteners

### M-01 — B-1 door parity vs the sequence diagram's CLI-owned compiler vs MCP-later

B-1: every capability exists once in the library; doors are adaptation only (the list is parsing, transport, refusal rendering, registry enumeration). Door parity is a tier-2 test of *"identical function surface and semantics."* The sequence diagram has the **CLI** compile the run-config (`C->>C: compile ONE resolved run-config`) then `C->>L: run(config)`. Invocation flags are CLI-native.

- CLI author puts the compiler in the door (flags live there; CLI is "the product face").
- Python-API author puts the compiler in the library (B-1). `run()` on a pre-built dict and `qmb backtest --book …` then resolve different layers (H-01/H-02) from the same English request.

MCP is Deferred-as-to-details but B-1 already asserts parity "across doors" and B-5 already forbids a daemon; a localhost-bound MCP server (B-1) is a daemon. v1 can ship without MCP; the parity test's door-set is still undeclared (CLI+Python now, or all three forever).

**Closing clause (B-1).** *"The config compiler is a library function. Doors only parse to its input DTO (flags, kwargs, MCP args) and render its output. The parity test's door-set is the shipped doors; MCP, when it ships, is stdio or an optional long-lived process **outside** the library, re-resolving the compiler per call, and is not a B-5 required daemon."*

### M-02 — WriterId mint for process-per-run: per-run, per-slot, or per-machine

AD-8: WriterId is per `(machine, role, stream)`. B-5: process-per-run, concurrent processes never share a file (B-4). A PID-derived WriterId explodes one-line fragment files and dies with the process; a stable per-machine WriterId makes concurrent runs share a file, which B-4 forbids; a 12–14 **slot** identity is a worker pool, which smells like the runtime B-5 banned.

**Closing clause (B-5).** *"The process runner mints a **slot** WriterId per concurrent worker (`(machine, qmb-ledger, slot-n)`), reused across sequential runs on that slot, never across two live processes. Slot count is the declared concurrency cap. No pool daemon: the parent campaign process (C-07) is the slot owner and exits when the campaign does."*

### M-03 — "Acting" during warm-up, and signal-only significance

B-2 refuses "acting" during warm-up. B-14 significance is *"signal-only run-loop pass with **orders disabled**."* If acting = minting intents, significance still mints signals (Jesse's `should_long/short` with `with_execution=False`). If acting = any strategy callback with a side effect, significance is illegal during warm-up and possibly always (orders disabled *is* a run-long warm-up by Unit B of C-01).

**Closing clause (B-2 + B-14).** *"Acting = minting an entry/exit intent or command. Signal-only mode records the would-have-been intent as a B-10 series and does not mint commands; it is legal during and after warm-up. Warm-up still refuses commands."*

### M-04 — Plain-Python bots vs B-13 `name@version` from the registry

Deferred: *"QMB tests plain-Python bots until QML lands; QML conformance gates **governed evidence**, not tunnel entry."* B-13: *"Books and **bots** are resolved name@version from the registry."*

- Unit A accepts a filesystem path in the run spec (tunnel entry; label carries a file hash).
- Unit B refuses unregistered bots (`unavailable dependency`).

Governed vs ungoverned is the Deferred row's own split; the label recipe doesn't have an ungoverned mode.

**Closing clause (B-13).** *"Tunnel entry may name a bot by filesystem path; the label then carries `bot_source = path` + content fp and the B-4 verdict is `unrated` (not governed). `bar-pass`/`bar-fail` require `bot = name@version` from the registry. QML conformance, when it lands, is a second gate on governed evidence, not a third entry mode."*

---

## 5. Structural roots

Seven of the nine criticals collapse to five clauses:

| Root | Closes | One-line patch |
| --- | --- | --- |
| R1. Pin the loop's causality | C-01, C-02, H-07, M-03 | In-loop locked warm-up; spine-pinned sub-phase order; closed bars only |
| R2. One measure roster, one verdict kind | C-03, C-05, H-02, H-04 | B-10 = CT-32/AD-23; `bar-pass` only on confirmation runs under Book-declared conditions |
| R3. World vs claim-class vs procedure-ephemeral | C-04, H-03, H-08 | Store-taint ≠ in-memory MC; campaign vs child run cardinality pinned per rung |
| R4. Sampler study artifact; sequential ask | C-07, M-02 | Study fp in the trial label; no parallel ask for TPE; slots not daemons |
| R5. Replay binding + a defined ledger directory | C-08, C-09, H-05, H-06 | Mint `world=replay` binding; fragment home + as-of merge; run id is the ledger key |

C-06 (fill pipeline) is its own one-clause pin and does not wait on GAP-0048.

---

## 6. What holds (so the criticals are read in proportion)

- **B-1's door shape** (thin adaptation, UI in-process over Python, MCP not stacked on HTTP) closed challenge-mechanics Attacks 3–4 and should stay. The remaining leak is *where the compiler lives* (M-01), not the three-stack donor failure.
- **B-6's claim-class taint** (`optimistic` ⇒ no edge, no split-budget spend) closed challenge-mechanics Attack 7 as a *claim* seam. It did not close identity (C-06).
- **B-7's store-level taint as a world derivation** is the right operationalization of AD-12 + L20 for `qmb data generate`. It overreaches when applied to B-14's ephemeral procedures (C-04).
- **B-5 process-per-run** is the correct AD-15 reading and matches both donors' actual isolation (`spec-concurrency.md`). It needs the study-artifact / slot-WriterId split (C-07, M-02) to coexist with adaptive search.
- **B-9's portable/unsealed split** correctly answers challenge-override Attack 5 (seal vs Jupyter anywhere). It is not an assembly clash on this spine.
- **No B-id re-decides QMF law.** The misses are QMB not *picking up* AD-29's replay-binding sentence (C-08), AD-32's parity sentence (C-03), and AD-12/19's world-scoped read (C-09) — consume-and-apply holes, not overrides.

---

## 7. Verdict

The QMB spine is the right shape — one library, one resolved config, one loop, claim-class taints, process-per-run — but as written it lets two factory agents ship a Jesse warm-up next to a LEAN warm-up, a QMB-local Sharpe next to the Book's AD-23 bar, a TPE search that cannot be replayed from its label, and a Book-bar reader that does not see the sandbox that just passed it; pin the loop order, the measure roster, the verdict kind, the fill pipeline, the study artifact, and the ledger's home, and the rest of the B-ids hold.
