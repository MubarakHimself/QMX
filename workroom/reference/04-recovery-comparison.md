# 04 — Recovery Comparison: old Examination Engine vs the fresh backtesting verdict

**For:** Mubarak (re-ratification required) · **Written:** 2026-08-17 · **Status:** register, not adopted
**Compares:** `.recovery/backtesting-engine-retrieval/recovered-backtesting-engine.md` (+ `restart-handoff.md`, `source-ledger.md`, `README.md`) against `reference/02-backtesting-verdict.md`, with `reference/03-wave2-supplement.md`, `research/09-experimentation-search-overfitting.md` and `research/00-qmf-synthesis-module-map.md` as supporting evidence.
**Standing rule this document obeys:** old material is evidence, never authority (`tracker/map.md` §Notes, "Authority"). Nothing here is adopted until Mubarak rules on §6.
**Ratified topology this document assumes:** *"no central backtest engine — backtesting decentralizes into callable QMF components"* (`tracker/map.md`, Session accord — QMX Foundations v2).
**Sources read:** the recovery package in full (`README.md`, `restart-handoff.md`, `recovered-backtesting-engine.md` §§1–18, `source-ledger.md`); `reference/02-backtesting-verdict.md` §§0–8 in full; `reference/03-wave2-supplement.md` (ideas #73–#115, corrections W2-1…W2-7); `research/09-experimentation-search-overfitting.md` (§§1–4, 6, 9.3, 11.2, 12, 14.2–14.6); `research/00-qmf-synthesis-module-map.md`; `tracker/map.md`; `artifacts/2026-08-17-qmf-v1-spec-DRAFT.md`. **No old implementation code was read into this document, and none was copied.**

---

## In plain words

1. The old project never built a backtester. What it left behind is a **specification** for one — a "Examination Engine" that would live on a central Backend Node, run each job in its own process, and hand out signed **certificates** saying a bot had passed.
2. That specification was **good**. It was written by someone taking honesty seriously: it says the replay must behave exactly like live trading except for two things, it says failed runs must be kept forever, and it says the engine is never allowed to promote anything to live.
3. The fresh verdict was written months later, from open-source engine studies, by someone who had not read the old spec. It arrives at **the same conclusions on the load-bearing points** — the same two-swaps rule, the same "record exactly what produced this number" rule, the same walk-forward/Monte-Carlo/PBO battery, the same "the engine measures, it never promotes."
4. Two people reaching the same answer from different directions is the strongest signal available on a design nobody can test yet. Those convergences should be treated as close to settled.
5. Where they differ, the fresh verdict is usually **finer-grained** (costs split into five columns instead of one number; identity as a content hash instead of a version string) and the old spec is usually **stricter about consequences** (a mismatch does not just warn, it invalidates).
6. The real difference is not quality, it is **shape**. The old design is a service you send work to. Your ratified ruling makes backtesting a set of parts other QMF code calls directly — and it replaces certificates with a ladder a strategy climbs: proposed → measured → validated → confirmed-on-holdout → live.
7. That change is not a downgrade of the old design; it deletes four problems the old design had to solve (a queue, a scheduler, a "who is allowed to write the results file" argument, and a second database) and it deletes them by **making the result's name be its own fingerprint**.
8. But the move also drops three things the old design was right about, and they need to be put back by hand: a **per-bot page** that shows every run a strategy ever had, passes and failures together; the rule that a simulation which **refuses fewer trades than reality** is invalid evidence; and the rule that **anything which can change how much you lose must be recorded in the result's name**, or the result is a lie.
9. The fresh verdict brings things the old design had no concept of at all: **prop-firm rules** (your stated goal), a **search budget** that stops an agent from testing a thousand ideas against the same five years of data, an **automatic warm-up** check that stops half-cooked indicators from trading, and a **fingerprint you can re-run** to catch a lying agent.
10. One old number is probably wrong and worth catching now: the old spec's Monte-Carlo test shuffles the order of completed trades and then reports the spread of profit factor and Sharpe. Those two numbers **cannot change** when you shuffle trade order. Three quarters of that test reports nothing.
11. One fresh gap is worth catching too: the fresh verdict tests its *formulas* against a reference implementation, but never tests whether the whole battery actually **fails a strategy that is known to be fake**. The old spec did require that. It is the cheapest possible proof that the honesty machinery works.
12. Nothing found here overturns the fresh verdict's recommendation (contracts first, then the engine as an assembly).
13. **Outcome in one sentence:** the old design was right about *invariants and consequences* and the fresh verdict is right about *identity, budget and shape* — so the register below folds the old invariants into the fresh contracts as ladder rules and registration preconditions, and asks you to re-ratify 17 decisions.

---

## Where they agree

Each line: the convergence, then why it matters. **These were derived independently** — the fresh verdict's evidence index (`reference/02-backtesting-verdict.md` §Evidence index) lists only open-source studies and `research/` files; it never read the recovery package. Independent derivation of the same rule is the strongest correctness evidence available for a system that cannot yet be tested.

**A1 — Two-substitution replay parity.**
Old: *"Replay/live parity permits exactly two substitutions: historical data for live ticks, and an in-house fill simulator for the Adapter"* (`recovered-backtesting-engine.md` §6 INV-02). Fresh: one kernel, three wirings, where backtest differs from live only in `ClockFactory` (SimClock vs WallClock) and venue (SimVenue vs cTrader), with a CI test asserting `qmf.runtime` has **no import edge** to `qmf.sim` (`reference/02-backtesting-verdict.md` §2.1).
*Why it matters:* two authors independently concluded that every other difference is a bug. The fresh side additionally supplies the enforcement mechanism the old side left as prose — and `research/00` Novel-2 makes SimBroker implementation #1 against the conformance suite so parity is structural.

**A2 — Reproducibility identity as a closed set of pinned inputs.**
Old: minimum identity is `bot_spec_version + data_snapshot_id + config_hash + seed`, with `config_hash` covering *"resolved registry values and attribute/policy bindings in force for the run"* (§6 INV-06/INV-07). Fresh: `run_id = sha256(canonical_json(RunSpec))` over `(confluence_id, split_id, data_fingerprint, qmf_version, venue_model_id, book_config_hash, fill_assumptions_id, fidelity, metrics_set_id, seeds, thread_pins, env_lock_hash)` (`02` §3.3, §3.4).
*Why it matters:* same rule, and the fresh set is a strict superset of the old one. The old design proves the requirement is not a fashion of the open-source studies; the fresh design proves the field list was incomplete.

**A3 — No ambient time or randomness in run identity.**
Old: *"Run identity contains no ambient time or randomness. Clock, bounds and seed are explicit inputs"* (§6 INV-05). Fresh: the canonical result document strips wall-clock and machine identity so *"two honest runs on two machines produce the same digest"*, and all random identities are normalised to class-prefixed ordinals (`02` §3.5).
*Why it matters:* the old rule states the principle; the fresh one states the *test* that proves it holds. Together they are a complete requirement.

**A4 — Walk-forward + Monte-Carlo + PBO battery.**
Old: walk-forward with aggregated OOS as primary evidence, Monte-Carlo distributions, PBO via CSCV (§10.1, §10.2). Fresh: `qmf.overfit` computing *"DSR, PSR, PBO via CSCV (+ its IS→OOS slope), MinBTL-vs-actual, effective_n_trials, Harvey–Liu haircut, plus SPA/StepM/MCS"* (`research/00` Ring 7; `research/09` §3), plus two Monte-Carlo families (`02` §5.3).
*Why it matters:* the specific triad — walk-forward, resampling, PBO — was chosen twice from different literatures. Treat the triad as settled; the *methods and numbers* are not (see B8).

**A5 — Battery honesty must itself be proven (convergent in principle; the old side is stronger).**
Old SM-6: *"multiple overfit archetypes fail; a known-good control passes; a mismatched-labeler certificate blocks live use"* — recorded as `KEEP` and *"never implemented"* (§10.3). Fresh: the same instinct appears three times but only as *formula* and *stability* tests — oracle-test QMF's implementation against `purgedcv` in CI (`research/09` §6), a determinism regression test with a pinned output hash (`research/09` §12.3 item 7), a frozen golden-backtest digest in CI (`02` §3.5), and the no-lookahead property test as a **precondition of registration** (`research/00` Novel-1).
*Why it matters:* both sides independently concluded the checker must be checked with known-answer inputs. But the fresh side verifies *arithmetic*; the old side verifies *behaviour end-to-end* — that the assembled battery actually fails a strategy built to be fake. Neither research file contains an overfit-archetype suite; this is a genuine old-side contribution and is carried into §4 (item 12).

**A6 — The engine has no authority.**
Old: *"The engine evaluates. It does not generate signal logic, mutate candidates, self-register, self-promote or decide live entry"* (§6 INV-14); *"Certificates are evidence. They are not permission to trade"* (§5). Fresh: the monitor *"writes a verdict, feeds `qmf.bms`, and updates the registry promotion state. It never re-sizes, never retrains, never deploys"*, adopting Hummingbot's rule verbatim — *"safety limits are user-only and never agent-writable"* (`02` §5.5); promotion is a manifest edit with a human gate (`research/00` §Promotion).
*Why it matters:* this is the single rule most likely to be eroded by convenience. Two independent derivations make it non-negotiable.

**A7 — Failed and invalidated evidence is kept forever, and is the denominator.**
Old: *"Failed runs and invalidated certificates remain immutable evidence; corpus presence never means current validity"* (§6 INV-12). Fresh: *"deleting is impossible — because deleting failed runs is how a trial count gets laundered, and **failed runs are the denominator**"* (`02` §3.3, citing `research/09` §11.2); *"Failed confluences are the most valuable rows in the table"* (`research/00` §Promotion).
*Why it matters:* the old side reached this from evidence-integrity; the fresh side from statistical validity. Same rule, two justifications — which is why it should be a schema property (append-only), not a policy.

**A8 — The money/protection gate runs inside the run loop, with production semantics.**
Old: *"Book policy, ordered doors, formulas, protection, costs and refusal behavior use the same in-house semantics as live"* (§6 INV-03). Fresh: *"The Book is in the loop, not in a spreadsheet afterwards"*, with three independent engines cited and Freqtrade named as the counterexample that *"looks only at closed trades and is therefore structurally unable to model any real prop-firm rule"* (`02` §4.1).
*Why it matters:* the old design derived this from parity; the fresh design from prop-firm mechanics. A Book graded outside the run it constrains is grading a different exam — both documents say so in almost the same words.

**A9 — Cost-adjusted evidence, not gross.**
Old FORM-0009/0010: `EV = p·W − (1−p)·L − c` and break-even `p > (L + c) / (W + L)` (§10.1); OOS expectancy floor stated *after modeled costs*. Fresh: five-column `TradingCost` with `edge_gross`, `edge_net` and the four deductions reported separately (`02` §2.6, §3.7).
*Why it matters:* same requirement, different resolution. The old formulas are the closed form of the fresh verdict's edge-vs-spread registration refusal — see §4 item 5.

**A10 — Immutable, manifested, explicitly-versioned data; no live-updating fallback.**
Old: *"Replay reads immutable, manifested data and explicitly selects source class/input-availability tier. No partial-version or live-updating fallback is allowed"* (§6 INV-10). Fresh: `data_fingerprint` as per-partition content hashes *"guards against silent data revision — Jesse's candle store supports `on_conflict='replace'`, overwriting historical OHLCV in place"* (`02` §3.4); `split_id` + `split_registry_version` is *"the only permitted way to name data. Raw dates do not exist in the signature"*.
*Why it matters:* the old side named the hazard; the fresh side found a shipping product that has it. Convergence plus a live example.

**A11 — Version mismatch must invalidate, not warn.**
Old: *"Labeler-version mismatch invalidates a certificate and blocks live use until recertification"* (§6 INV-09). Fresh: change any key component and *"the old baseline is **automatically not applicable**. No human has to remember"* (`02` §5.2); *"old results do not silently become claims about the new definition"* (`02` §3.4).
*Why it matters:* identical consequence, achieved two ways — the old by an explicit invalidation event, the fresh by making the key stop matching. See B2 for how to keep both.

**A12 — Exact arithmetic for money; floats only where they cannot decide anything.**
Old: *"Exact financial arithmetic uses scaled integers/Decimal; binary float is allowed only for replay-stable statistics and labeler features"* (§6 INV-08). Fresh: `Decimal` on every `TradingCost` column (`02` §2.6) and *"`Decimal` for all money/price/quantity (no floats in money paths)"* (`artifacts/2026-08-17-qmf-v1-spec-DRAFT.md` §5).
*Why it matters:* a boring convergence that closes an entire class of irreproducibility, and it is cheap only if decided before the first line of code.

**A13 — Canonical serialization + hashing; no pickle.**
Old: results *"hashed using canonical JSON and SHA-256"* with deterministic ordering (§9), and O-23 flags *"canonical manifest serialization before hashes become durable identity"* as a required ratification. Fresh: *"**No `pickle` anywhere in the result path.** rqalpha pickles its whole result dict — version-fragile, unreadable without the code, a deserialisation hazard"* (`02` §2.8 item 18); sorted keys, unordered arrays sorted, reader re-canonicalises and rejects non-canonical bytes (`02` §3.5).
*Why it matters:* the old side knew canonical serialization was load-bearing and unratified; the fresh side supplies the exact discipline.

**A14 — Research work must never sit on the trading hot path.**
Old: *"completely off the Trading Node hot path; Backend/Exam failure does not block trading"* (§4). Fresh: two deployables — installable app + one Trading VPS (`tracker/map.md`, Session accord) — and two CI-enforced lockfiles, trading vs analysis (`research/00` Novel-7).
*Why it matters:* the old design bought this with a separate node; the ratified topology buys it with a separate deployable and a dependency fence. The *guarantee* survives the topology change intact (see B1).

---

## Where they conflict

Each conflict states both positions fairly, then a recommended resolution. **Every resolution is RATIFY-PENDING** — none is adopted.

### B1 — Topology: a central Examination Engine service vs QMF callable components

**Old position.** A backend-node service: *"a backend-node Examination Engine using an in-house, deterministic, book-specific replay harness"* (§1), hosted on the always-on Backend Node, running *"process-per-run workers under the Backend Node supervisor"* (§4), with an unbuilt but required job lifecycle (§7 step 3; O-02, O-20), a worker→publication seam (INV-11, O-26), and a PostgreSQL certificate corpus plus per-bot dossier tables owned by a registered `exam-host` writer (§13).

**Fresh/ratified position.** *"No central backtest engine — backtesting decentralizes into callable QMF components"* (`tracker/map.md`, Session accord). `qmf.run.execute(RunSpec) -> RunResult` is *"the **only** producer of a result"* (`02` §3.3); results are content-addressed and append-only; there is no queue, no scheduler, no service boundary, and no database server (`tracker/map.md` §Not yet specified, storage architecture: *"no database server"*).

**What the move actually changes, and what replaces each piece:**

| Old mechanism | Why it existed | What replaces it under QMF components |
|---|---|---|
| **Job lifecycle** — accepted/refused, validated, queued/running, completed/failed/cancelled, retry, idempotency (§18 item 3; O-02) | A service must track work it accepted but has not finished | Collapses into a **function call plus three durable facts**: (a) a registration refusal, which happens *before* any data is loaded and never becomes a run (`02` §3.1); (b) a budget-ledger row written **before the call returns**, because *"a crashed run that saw the data has still spent the budget"* (`research/09` §14.4); (c) an append-only `RunResult`. **Idempotency is free** — `run_id = sha256(canonical_json(RunSpec))`, so a retry is bit-identical and an identical key is a cache hit (`02` §3.3, §4.4). **Cancellation** becomes killing a process, which is safe because nothing partial was ever published. **The gap:** the old lifecycle had first-class `failed` and `insufficient-data` states (§12.1) that the fresh design never names; a crashed run currently leaves a spent budget row and no result row. |
| **Process-per-run isolation** (§4, `KEEP`) | Crash containment on a shared always-on node; one read-only DuckDB context per runner | Demote from architecture to an **executor option** on `qmf.run`. The determinism requirement already forces the hard part: *"Parallel execution must not change results, only wall-clock"*, with a CI test asserting 1-worker vs N-worker bit-identity (`research/09` §12.3). Process-per-run then earns its place for Book Matrix / Campaign fan-out and for crash containment, not as a topology rule. The hot-path guarantee it used to provide is now provided by the two-deployable ruling (A14). |
| **Worker → publication seam** (INV-11, O-26: sole Class-3 finalizer, one registered writer per table family) | Two writers to one mutable store is a corruption risk, so ownership had to be assigned | **Dissolved by content addressing.** When an artifact's address *is* its hash, two workers producing the same run produce the same bytes at the same address; there is no write conflict to arbitrate. What still needs a single owner is the **mutable index** — `qmf.registry`'s manifest chain and `qmf.ledger`'s budget table — and wave-2 supplies the discipline for exactly that: hash-chained append with an **external `(count, head_hash)` anchor** (internal linkage alone cannot detect tail truncation), fail-loud on write errors, and chain resume from disk on restart (`reference/03-wave2-supplement.md` #110). |
| **Certificate + dossier storage** (§13: Backend PostgreSQL corpus; Trading Node Class-1 index holds *operative* validity) | A certificate is a durable object that must be issued, stored, found, and invalidated | **Certificate → (`RunResult` + a promotion-ladder rung).** The evidence is the append-only `RunResult`; the *permission* is the rung recorded on the confluence manifest — `proposed → measured → validated → confirmed → live → retired`, append-only with a `supersedes` rollback pointer (`research/00` §Promotion). This preserves the old design's sharpest distinction — INV-12's *"corpus presence never means current validity"* — because a passing `RunResult` is a fact and the rung is a separate, revocable statement. **The dossier does not survive the move** and must be rebuilt (see §4 item 1). |

**Recommended resolution (RATIFY-PENDING).** Adopt the components topology in full. Explicitly ratify the four replacements above as the *answers* to old O-02, O-20, O-26 and O-19 rather than leaving those seams open. Add back the two things the move drops: a `RunStatus` enum on `RunResult` carrying `COMPLETED | FAILED | REFUSED | INSUFFICIENT_DATA` — wave-2's three-state rule says a check that cannot be measured must never collapse into pass or fail (`03-wave2-supplement.md` #105) — and the per-bot dossier as a derived read-model (§4 item 1).

### B2 — Certification as a discrete certificate vs a rung on a promotion ladder

**Old position.** CT-EXAM-01 (per-bot) and CT-EXAM-02 (cohort) are issued documents with named fields, and an explicit **invalidation event** fires on labeler-version mismatch and (once designed) stop-policy mismatch (§12.2, §12.3, INV-09, PE-8/O-08).

**Fresh position.** There is no certificate. There is a rung on a ladder, and inapplicability is automatic: change any key component and the baseline *"is automatically not applicable"* (`02` §5.2).

**The genuine conflict.** Automatic inapplicability is silent. The old design wanted a *visible event* — "this certificate was invalidated, and here is why" — because a silently-inapplicable claim looks identical to a claim nobody has made yet, and a non-technical operator cannot tell them apart.

**Recommended resolution (RATIFY-PENDING).** Adopt the ladder, and import the old invalidation semantics as an explicit **demotion rule**: a rung is held by the tuple `(confluence_id × book_config_hash × venue_model_id × fill_assumptions_id × fidelity × metrics_set_id × split_id)`; when any element changes, the confluence **drops** to the highest rung whose evidence still keys correctly, the demotion is written as an append-only ledger row naming the field that changed, and the operator UI shows the drop. This is the fresh baseline mechanism (`02` §5.2) reused as the promotion mechanism, with the old design's visibility requirement bolted on.

### B3 — "One bot × one Book, no abstract certified bot" vs the Book Matrix

**Old position.** *"Certification is for one immutable bot specification against one specific Book contract/profile. **No abstract 'certified bot' state exists.**"* (§6 INV-01.)

**Fresh position.** The Book Matrix is *"a grid of Runs sharing one `confluence_id` with different `book_config_hash`"*, and it is cheap because identical keys are cache hits (`02` §4.4).

**The genuine conflict.** They are compatible at the schema level — a Matrix *is* a set of per-Book claims — but the Matrix's presentation invites the exact reading INV-01 forbids ("this bot is good, look at the grid"), and it carries a second hazard the fresh verdict itself flags: *"Twelve Books × 500 parameter trials is 6,000 trials against that split, not 500. Sequential per-space searching hides this in Freqtrade and must not hide it here"* (`02` §3.6, citing `research/09` §9.2).

**Recommended resolution (RATIFY-PENDING).** Ratify INV-01 verbatim into QMF as a schema property: **no table anywhere holds an aggregate "this confluence is good" row**; every claim names its Book. Keep the Matrix as a *view*, never a record. Enforce the trial arithmetic in `qmf.ledger`, not in an operator's memory — the ledger's per-row *"correlation fingerprint of the parameter set"* and the `N̂ = ρ̂ + (1 − ρ̂)·M` effective-trial spend are the mechanism (`research/09` §14.4).

### B4 — Data source class and the licensing gate

**Old position.** Every run explicitly selects a **source class** and an **input-availability tier**, and *"A run must not silently combine self-recorded, materialized-backfill, synthetic, derived or shadow evidence"* (§13). The old repo's real multi-year Dukascopy corpus was refused for canonical use by a licensing gate returning `SOURCE_LICENSE_NOT_CANONICAL_USABLE` (§14).

**Fresh position.** Data is named by `split_id` + `split_registry_version` and pinned by `data_fingerprint` (`02` §3.4). There is **no source-class concept**. D12 rules the Dukascopy question the other way: *"Accept for personal non-redistributed use, recorded as dated decision"* (`artifacts/2026-08-17-qmf-v1-spec-DRAFT.md` §2 D12).

**Why this is load-bearing now, not later.** Your own ratified synthetic-data rule — *"synthetic data can stress a strategy, never validate an edge"* (`tracker/map.md` §Not yet specified) — is **unenforceable without a source-class field**. Right now it is a sentence in a tracker; with `source_class` on the split it becomes a registration precondition. The same field is what stops a shadow-recorded partition from quietly joining a canonical backtest.

**Recommended resolution (RATIFY-PENDING).** Adopt `source_class ∈ {self_recorded, materialized_backfill, synthetic, derived, shadow}` as a first-class field on `qmf.data.splits`, carried into `data_fingerprint`. Refuse at registration any Run whose split mixes classes, and refuse any promotion above `measured` for a Run whose split contains `synthetic`. The licensing verdict itself is superseded by D12 — that is an operator risk call already made, and the old gate's refusal is evidence of prudence, not authority.

### B5 — Sessions: measured context vs a permission input

**Old position.** *"Sessions/overlap may be measured context but never restored as clock-window permission"* (§6 INV-13) — a deliberate reaction against the old WF2 world where session windows carried trading authority (§17, `DROP`).

**Fresh position.** Sessions appear in three places that all look like permission: `SESSION_CLOSED` as a BMS denial and `OUTSIDE_SESSION` as a `NoFill` reason (`02` §3.7, §4.1), and `tradeability` wired into the BMS *"so a challenge is never attempted in a hostile hour"* (`research/00` Novel-5).

**The genuine conflict.** The old rule is right about one of these and wrong about the other two. A venue that is genuinely closed is a **fact** — refusing the fill is correct and required by parity. "Do not trade thin hours" is a **policy** — and the old design's fear is exactly that such a policy becomes invisible authority nobody can see or version.

**Recommended resolution (RATIFY-PENDING).** Split them by ownership. Venue-closure facts live in `qmf.venue_model` and are not configurable per strategy. Session/tradeability *restrictions* live in the **Book manifest** and therefore inside `book_config_hash` — never in the confluence, never in the engine — and their denial counts appear on the card (`02` §3.7 already shows `SESSION_CLOSED ×3`). That satisfies INV-13's real concern (invisible clock-window authority) while keeping Novel-5.

### B6 — Fidelity taxonomy vs the two-substitution rule

**Old position.** Exactly two substitutions are permitted (INV-02), and *"Every relevant refusal is reproduced… **Easier-than-production evidence is invalid**"* (INV-04).

**Fresh position.** Three fidelity levels — `bar_close`, `bar_intrabar`, `tick` — each entering the result key, with optimistic matching modes **tainted**: refused promotion past `measured` and barred from spending split budget (`02` §2.3).

**The genuine conflict.** Under a strict reading of INV-02, `bar_close` is a *third* substitution — bar aggregation standing in for the tick stream — and under INV-04 it is inadmissible, because a bar-close fill is systematically easier than a real one. The fresh design does not forbid it; it keys it and taints it.

**Recommended resolution (RATIFY-PENDING).** Adopt the fresh keyed-and-tainted approach, and import INV-04 as a **ladder rule** rather than a prohibition: only `tick`-fidelity evidence may reach the `confirmed` rung; `bar_intrabar` caps at `validated`; anything under an optimistic matching mode caps at `measured` and spends no budget. This converts a blanket invariant into a gradient, which is what makes early screening runs usable without letting them buy a promotion. Wave-2 sharpens the same point from the fill side: *"touching a price is not filling at it"*, with `fill_at_touch_prob` defaulting to **0.0** and *"On bar data, equality is **never** a fill"* (`03-wave2-supplement.md` #95).

### B7 — In-house rebuild vs the NautilusTrader hybrid

**Old position.** Unambiguous: *"in-house rebuild. Donor engines are lenses only"* (§4).

**Fresh position.** Also recommends building — but deliberately restates the counter-case at full strength now that D1 was amended to permit LGPL for unmodified, separately-installed dependencies: a hybrid *"would hand you a battle-tested matching engine, a canonical result schema, latency models and a sandbox mode on day one"*, and *"if you weigh time-to-first-trustworthy-number above architectural coherence, this is the option to argue for, and I would not call you wrong"* (`02` §6.3.2).

**The genuine conflict.** The old spec forecloses a door the fresh verdict deliberately holds open.

**Recommended resolution (RATIFY-PENDING).** Hold the in-house line, on a reason both documents independently supply: a hybrid forces the Book to live outside the engine that grades it, which is precisely the defect the fresh verdict names as making Freqtrade's protections useless (`02` §4.1) and which old INV-03 forbids by name. Let the already-agreed 3-factory-day adoption spike be the only re-opener (`tracker/map.md` §Decisions, kernel verdict).

### B8 — Fixed registry battery constants vs derived, pre-registered budgets

**Old position.** Seven registry-bound numbers, recorded as `RECONFIRM` *"while preserving prior binding status"* (§10.1): walk-forward IS 6 months, OOS 1 month, minimum 200 OOS trades per window, OOS expectancy floor 0.15R after modeled costs, 1,000 Monte-Carlo permutations, PBO pass `< 0.25`, PBO dead `> 0.50`; plus CSCV with `S = 16` subperiods (§10.2).

**Fresh position.** Thresholds are **derived and pre-registered per experiment**, not fixed in a registry. Budget is derived: `budget(split_id) = N_max such that MinBTL(N_max, SR*) ≤ length_of_split_in_years` — at `SR* = 1.0` a five-year split allows **45** effective trials; at `SR* = 2.0`, ~1,600 (`research/09` §14.4; `02` §3.6). DSR must clear 95% (`research/09` §2).

**What the evidence actually says — this matters.** A full read of `research/09` finds that **none of the old seven numbers has fresh support**, and two are actively disfavoured:
- **No IS/OOS window length appears anywhere.** `research/09` never endorses or criticises 6-month/1-month; it rejects the framing — *"The escape valve is not 'raise the budget', it is 'the split registry has more splits'"* (§14.4) — and refuses raw dates in any API (§14.3).
- **`S = 16` is not mentioned.** The CSCV algorithm is given only as "S even" with `C(S, S/2)` combinations (§3).
- **PBO `0.25` is not mentioned; `0.50` appears only as the interpretive midpoint** — *"A PBO of 0.5 means your selection method is worth exactly nothing"* — never as a gate (§3). `research/09` requires a pre-registered maximum PBO but names no number.
- **Minimum trade count is endorsed as a concept and left unnumbered:** *"QMF should make this a hard rejection, not a soft multiplier: below a minimum trade count, the result is not a result"*, with the framing *"MinBTL is about **time**; minimum trade count is about **sample**. Both are needed"* (§9.3). Freqtrade's 50 is quoted as prior art, not adopted.
- **No expectancy floor exists** in the fresh material at all.
- **No Monte-Carlo permutation count exists** in `research/09`; the only `1000` in the file is `arch`'s library default for `SPA`/`StepM`/`MCS`.

**Recommended resolution (RATIFY-PENDING).** Keep the fresh *derivation* as authority and re-import the old numbers only where they have independent standing:
- **Re-register** PBO `< 0.25` / `> 0.50` and CSCV `S = 16` as **initial pre-registered values** with a `definition_source` pointing at the old registry, flagged `evidence_state: hypothesis` until traced to the Bailey–López de Prado CSCV paper (SSRN 2326253, cited at `research/09` §3). They are the only two of the seven with plausible literature backing, and having *a* number beats having none.
- **Re-derive** the walk-forward windows from the split registry rather than fixing them; a 6/1 month split is a `split_id`, not a constant.
- **Adopt** minimum-OOS-trades as a hard rejection per `research/09` §9.3, with 200 recorded as the old value and the actual number set from measured trade frequency per Book.
- **Carry** the 0.15R expectancy floor forward as a Book-level pre-registered threshold, not a global constant — it is meaningless without a stated cost model, and the fresh design has five cost columns where the old had one `c`.
- Add `research/09` §14.6's requirement that reporting uses **worst-fold path metrics, not the average**, since *"Prop-firm rules are evaluated on the worst day, not the mean day."*

### B9 — What the Monte Carlo is actually measuring

**Old position.** *"Monte Carlo permutations of completed OOS trades, reporting 5th/50th/95th distributions for final equity, drawdown, Sharpe and profit factor"* (§10.2), with 1,000 permutations (§10.1).

**Fresh position.** Two Monte-Carlo questions that *"QMF should copy that split exactly"*: **candle-perturbation MC** (perturb the price path, re-run the strategy) answers *"is this overfit to this exact history?"*; **trade-reorder MC** (reshuffle already-realised trades) answers *"how bad could the drawdown path have been?"* and is documented as carrying **zero** information about overfitting, *"since win rate and return are invariant to trade order"* (`02` §5.3, from `jesse.md` §MM4).

**The genuine conflict, and it is a defect.** The old procedure is trade-reorder MC. Of the four statistics it reports, **profit factor and per-trade Sharpe are exactly invariant to trade order**, and final equity is invariant under additive-R accounting. Only maximum drawdown genuinely varies. As specified, three quarters of the old Monte-Carlo output is a degenerate distribution with a zero-width 5th-to-95th band — and it was positioned as overfitting evidence, which it structurally cannot be.

**Recommended resolution (RATIFY-PENDING).** Split the old procedure in two, per the fresh verdict:
- **Trade-reorder MC** is kept, renamed honestly, and reports **only path statistics** — max drawdown, worst day, longest losing streak, time-under-water. It feeds `qmf.bms` and the prop-firm ratchet checks, which is exactly where it is valuable.
- **Overfitting evidence** comes from candle-perturbation MC plus PBO — and wave-2 adds a cheaper single-strategy option that needs no competing pool: **perturbation PBO**, jitter one confluence's parameters ±20%, backtest the variants, run PBO over the resulting matrix (`03-wave2-supplement.md` #108). That maps cleanly onto `confluence_id` being a content hash over the resolved parameter set.
- Also decide whether "permutation" in the old spec meant reorder or **resample-with-replacement**. If the latter, it is a bootstrap and must be named one, with block size reflecting the strategy's average holding period *"not `sqrt(T)`"* (`research/09` §4).

### B10 — The unit of certification: a bot, or a confluence

**Old position.** The unit is a `bot_id` + immutable `bot_spec_version`, executed through a QML compiler/runtime boundary (CT-QML-01, O-29), against a Book profile.

**Fresh position.** The unit is a `Confluence` — `{level, trigger, confirmations[], exit, sizing_policy, gates[], max_bars_between_touch_and_trigger}` — identified by `sha256(canonical_json(spec))` including every component's semver, and persisted as **typed data, never generated source** (`research/00` §Level/Trigger/Confirmation; `03-wave2-supplement.md` #113).

**The genuine conflict.** Mostly vocabulary, with one substantive edge: the old model assumes an opaque compiled artifact whose identity is a version string and whose code identity is a repo commit (§8, "Candidate" field group). The fresh model assumes an inspectable structure whose identity is its content — which is what makes deduplication, warm-up computation up the tree, and composition-time refusal possible at all (`02` §2.4, §3.1).

**Recommended resolution (RATIFY-PENDING).** Adopt the confluence-as-data model; retire `bot_spec_version` as an identity mechanism and keep "bot" only as operator vocabulary. Explicitly note that this **deletes old O-29** (the QML compiler/runtime boundary as a certification dependency): there is no compiled artifact to pin when the spec *is* the artifact. Old INV-01's real content — one immutable candidate, one Book — survives untouched.

---

## Old ideas the fresh verdict missed

Each: what it is, why it is valuable, and **keep / adapt / drop**.

**1 — The per-bot dossier. KEEP (rebuild as a derived read-model).**
Old: *"Per-bot dossier — Backend evidence assembly under its registered table-family writer; **passing and failing artifacts remain linked**"* (§13). The fresh design stores every `RunResult` under its hash, append-only — but the operator's only view is a **card per run** (`02` §3.7). There is no page answering "show me everything ever run against this confluence." That page is precisely what makes the append-only failure rows usable rather than merely stored, and it is what a non-technical operator will actually open. *Implementation:* a derived read-model over `qmf.run` + `qmf.ledger` keyed by `confluence_id`, with the ladder rung, the budget consumed, and every run pass or fail. No new writer, so it costs nothing against B1's content-addressing.

**2 — Refusal parity as an invariant. KEEP.**
Old: *"Every relevant refusal is reproduced, ordered and visible in replay evidence. **Easier-than-production evidence is invalid**"* and *"omit live refusals or inconvenient production behavior"* is listed under what the engine may **not** do (§6 INV-04, §3). The fresh verdict reports `NoFill` counts by reason on the card and notes *"a backtest that fills 100% of its orders in the hostile hours is visibly suspect"* (`02` §2.5, §3.7) — but never states the invariant, and never makes under-refusal a **failure**. *Implementation:* ratify the invariant; give it two teeth — (a) the adapter conformance suite asserts `SimVenue` and `qmf.broker.ctrader` return the **same denial code** for the same intent + state (`02` §2.2), and (b) `qmf.monitor` tracks **refusal-rate divergence** live-vs-backtest alongside the fill divergence it already tracks (`02` §5.4). This is the cheapest extension of an accepted mechanism in the whole register.

**3 — Exam pinning, generalised. KEEP (as a rule, not a field list).**
Old: labeler mismatch invalidates (INV-09), and *"Any stop policy shaping measured loss must eventually pin and invalidate the same way"* (PE-8 / O-08), with CT-EXAM-01 expected to eventually carry *"every policy version shaping loss — especially stop policy"* (§12.2). The fresh design pins a good list (`book_config_hash`, `venue_model_id`, `fill_assumptions_id`, `fidelity`, `metrics_set_id`) but never states the **general rule** that produced it. *Implementation:* ratify — **if it can change the loss distribution, it is in the result key, or it is a bug** — and turn it into a test: enumerate every input the run loop reads, assert each appears in the `RunSpec` canonical document. That converts a hand-maintained list into a checkable property, which is exactly what the old design was reaching for and could not express.

**4 — Cohort correlation, with the threshold left null. ADAPT.**
Old CT-EXAM-02 carries `cohort_id`, `book_id`, `correlation_observations`, `expected_loss_shape`, `certified_at_utc`; the method and the `F_CHORUS` threshold stay open under GAP-0012, and *"Missing measurement must remain explicit rather than producing an invented threshold"* (§12.3, O-11). The fresh side has cluster-robust intervals for the *statistical* version of this problem (`03-wave2-supplement.md` #106: *"same-day pattern hits across different tickers are one market move observed twice"*) and a portfolio risk multiplier (`02` §4.4) — but **no evidence object about how concurrently-live bots co-move on one account**. The fresh verdict independently reopens the same hole from the money side: *"Multi-Book on one broker account… drawdown caps are joint"*, listed as an unclosed open question (`02` §8 item 4). *Implementation:* keep the slot as a `CohortResult` produced by `qmf.monitor` over concurrently-live confluences on one account; keep the discipline of a **null threshold** and an explicit `unmeasurable` state rather than an invented number — which is exactly wave-2 #105's three-state rule.

**5 — FORM-0009 / FORM-0010. KEEP the formulas; RECONFIRM the numbers (see B8).**
`EV = p·W − (1−p)·L − c` and break-even `p > (L + c) / (W + L)` (§10.1). The fresh verdict has richer cost data and never writes the condition down. But `research/00` Novel-3 refuses a confluence *"whose median winner at its trading hours is smaller than the p90 spread"* — and **FORM-0010 is the closed form of that refusal's threshold**, generalised from spread to the full five-column cost. *Implementation:* adopt both formulas verbatim into `qmf.metrics`, and make FORM-0010 the arithmetic behind the registration-time edge-vs-spread gate. The fresh verdict says that gate should *"read one field"* (`02` §2.6); this is the field's comparison.

**6 — Certification-side paper separated from fail-mechanism paper. ADAPT.**
Old: *"Design certification-side paper/warm-up separately from Trading fail-mechanism paper"* (`restart-handoff.md` §Design order item 9; §7 step 10; O-16). The fresh verdict has one Paper mode (live prices, simulated fills) used as a prop-firm rehearsal (`02` §2.1, §4.3). The old distinction is not about mechanism, it is about **role**: paper as evidence toward promotion, versus paper as a degraded live state the system falls back into. *Implementation:* keep one mechanism, ratify two roles — paper-as-evidence produces a promotable `RunResult`; paper-as-fail-mechanism is a `qmf.bms` state and produces **no** promotable evidence. Without the rule, a system that degrades into paper on a bad day quietly manufactures promotion evidence out of its own failure.

**7 — The engine's one question. KEEP verbatim.**
*"Does this immutable bot specification retain a cost-adjusted edge under production-equivalent behavior when evaluated against this exact Book profile and its pinned policy versions?"* (§3.) This single sentence encodes INV-01, cost-adjustment, parity and pinning. Nothing in the fresh verdict states the mission this compactly. *Implementation:* the module docstring of `qmf.run`, with "bot specification" swapped for "confluence" per B10.

**8 — Insufficient-window handling as explicit evidence. KEEP.**
Old: *"exclusion/explicit handling of windows below the minimum trade count"* (§10.2). `research/09` §9.3 agrees a thin window must be a hard rejection but does not say what the *window* becomes. The wave-2 answer already exists: a check that cannot be measured must report `unmeasurable`, never a pass and never a silent drop, *"or agents will learn which inputs make the check unmeasurable"* (`03-wave2-supplement.md` #105). *Implementation:* below the minimum trade count, a walk-forward window is `unmeasurable`; a run with too many unmeasurable windows is `INSUFFICIENT_DATA`, not `FAILED`, and spends budget either way.

**9 — The bounded data-request contract and its refusals. ADAPT.**
Old CT-MIS-02: five request fields, explicit UTC bounds validated with `end > start`, reads only manifest-visible artifacts, *"refuses hidden, corrupt, unsafe or extra-authority inputs"*, orders results deterministically, hashes with canonical JSON + SHA-256, performs no mutation (§9). The fresh `qmf.data.splits.load(split_id=...)` is the analogue but the **refusal list is sharper on the old side**. Note also old O-25: `[start, end)` was *"the old helper's behavior"* and **was never ratified** — a one-line decision that silently shifts every boundary bar if left open. *Implementation:* fold the refusal list into `load()` as preconditions; ratify `[start, end)` explicitly (§6 item 16). Wave-2 supplies the neighbouring boundary discipline: side-inclusion as *"an explicit named parameter, not an implicit off-by-one"* (`03-wave2-supplement.md` #87).

**10 — Deterministic result ordering as a contract property. KEEP.**
Old §9 requires deterministically ordered results from the data seam. `research/09` §12.3 requires total event ordering *"(timestamp, then a documented event-type priority, then a stable instrument key, then a monotonic sequence number)"*. Same requirement, two layers — the old at the data boundary, the fresh at the event loop. Both are needed; neither implies the other.

**11 — The "do not recover" register. KEEP as a standing never-build list.**
Old §17 names mechanics that must never return: WF1 and old WF2 Stages G–I, six-clamp/multiplier stacks/equity bands/slot caps/old circuit breaker, DPR/PRS ranking and slot auctions, automatic registry writes, probation, paper redemption, self-promotion, session windows as authority, identifier recycling. The fresh material has **no negative list at all**. *Implementation:* carry §17 forward verbatim as QMF's never-build register. It costs nothing and it is exactly the class of thing a tireless agent re-derives at 3am because it looks clever in isolation.

**12 — Battery-honesty acceptance via overfit archetypes. KEEP — this is the biggest single carry.**
Old SM-6 (§10.3): *"multiple overfit archetypes fail; a known-good control passes; a mismatched-labeler certificate blocks live use"* — recorded as `KEEP` and never implemented. A full read of `research/09` confirms **no equivalent exists on the fresh side**: §6 oracle-tests the *formulas* against `purgedcv`; §12.3 pins a determinism hash; `02` §3.5 freezes a golden digest. All three prove the code did not change. **None proves the battery works.** *Implementation:* a fixture suite of deliberately fake strategies — a future-peeking labeler, a curve-fit parameter set found by exhaustive search on the same window, a strategy that trades only on the four best days, a constant-return series (which `research/09` §6 notes can otherwise *"produce an infinite Sharpe and win the in-sample selection"*) — each of which the assembled battery **must fail**, plus one known-good control it must pass, run in CI. This is the only end-to-end proof that the honesty machinery is honest, and it is a few days of work.

---

## Fresh ideas the old design lacked

**1 — Content-hashed identity everywhere.** `confluence_id = sha256(canonical_json(spec))` over resolved parameters *plus every component's semver*; likewise `venue_model_id`, `data_fingerprint`, `metrics_set_id`, `run_id` (`02` §3.4; `research/00` §Confluence identity). The old design had version *strings* and one `config_hash`. Four consequences the old design could not get: automatic deduplication of the same idea found twice by two agents; automatic staleness of old results when a definition changes; the writer-ownership problem dissolving (B1); and the budget ledger being able to tell *"whether a search actually explored anything new."*

**2 — Registration-time refusal.** *"A run that is refused cannot produce a number to lie about"* (`02` §3, §3.1). Composition rules that compute automatically — causality is the worst of its parts, `smoothed` is **not constructible** for a live-bound component; stability worst-of-parts; `evidence_state` worst-of-parts — plus the no-lookahead property test `label(bars[0:t])[-1] == label(bars[0:t+n])[t]` as a **precondition of registration** (`research/00` Novel-1). The old design's entire integrity story was post-hoc evidence; it had no pre-run gate of any kind.

**3 — Spread-cost registration refusal.** A confluence whose median winner at its trading hours is smaller than the p90 spread *"cannot be registered, is never backtested, and therefore **never spends split budget**"* (`research/00` Novel-3). The old design knew the arithmetic (FORM-0010) and ran it after the backtest, which is exactly backwards.

**4 — The split-budget ledger. The single largest addition.** An OOS window is a consumable resource. Budget is **derived**, not chosen: `budget(split_id) = N_max such that MinBTL(N_max, SR*) ≤ split_length_years` — 45 effective trials on five years at `SR* = 1.0`, ~1,600 at `SR* = 2.0`. Spend is in **effective** trials via `N̂ = ρ̂ + (1 − ρ̂)·M`. A row is written **before** the call returns. `SplitBudgetExhausted` has **no `force=True`**, and the escape valve is more splits, not more budget (`research/09` §14.4; `02` §3.6). Lineage chains: *"A 'small follow-up search' that inherits a 5,000-trial parent has 5,000 trials in its denominator, not 50"* (§14.2). The old design had **no concept of search cost at all** — its battery could be re-run against the same data without limit, which is the exact mechanism by which *"a million variations of a worthless strategy"* yields a Sharpe of 4.87 (`research/09` §1).

**5 — Deflation and the no-naked-float result type.** *"The return type of an experiment is not a float. It is a result object carrying the metric **and** `n_trials`, `n_trials_cumulative_on_split`, DSR, PBO, MinBTL-vs-actual and the verdict… Make the naked number inaccessible"* (`research/09` §14.3.4). The worked example is the whole argument: SR 2.5 passes DSR at N=46 and fails at N=100 — *"the identical strategy passes or fails purely on how many things you tried"* (§2). Ratify verbatim: *"A Sharpe ratio is not a result. A Sharpe ratio plus the number of effective trials that produced it is a result."*

**6 — `evidence_state` as a data field.** `hypothesis | measured | validated | retired`, with a citation, composing worst-of-parts, visible in the operator UI and readable by agents (`research/00` Novel-9, §ComponentDef; `02` §3.1). SMC and candlesticks ship as `hypothesis`, visibly. *"Honesty as a data field beats honesty as a doc paragraph."* The old design had labeler versions and no honesty grade.

**7 — The canonical result document, digest, and re-execution.** Versioned schema, sorted keys, unordered arrays sorted, **all random identities normalised to class-prefixed ordinals**, wall-clock and machine identity excluded, a `blake3:` digest, a reader that re-canonicalises and **rejects non-canonical bytes so a hand-edited document fails to load rather than loading as truth**, and `first_divergence()` naming the first differing field (`02` §3.5). The old design hashed query *results* with canonical JSON + SHA-256 (§9) but had no whole-result canonicalization, no identity normalisation, no divergence locator, and no re-execution verb.

**8 — The fidelity taxonomy with a taint rule.** Three levels, `fidelity` in every result key, and optimistic matching modes refused promotion and barred from spending budget (`02` §2.3). Named as the one decision that *"cannot be retrofitted."*

**9 — Automatic warm-up, enforced by dispatch.** `warmup = max(component.warmup_bars) + max_bars_between_touch_and_trigger`, computed up the composition tree, with the runtime refusing to dispatch `on_bar` until warm and a **separate `pre_warm` method** rather than an `if` — *"there is no branch an agent can forget"* (`02` §2.4). Framed as a QMX emergency precisely because *"an LLM composing a Confluence… cannot be trusted to compute the combined warm-up, and the failure is silent."* The old design has no warm-up concept anywhere.

**10 — Five-column `TradingCost` including `financing` from the first commit** (`02` §2.6; `research/00` Novel-8). The old design had a cost schedule and a scalar `c`. Five columns are what turn *"did my edge die or did my broker get worse?"* from an investigation into a subtraction (`02` §5.4).

**11 — Two clocks: `wall_ts` and `session_date`.** The prop-firm daily-loss anchor is a business-day boundary in a firm-specified timezone — FTMO at 00:00 CE(S)T, a *moving* offset; Topstep 17:00–15:10 CT — and *"Get this wrong and a challenge fails on a technicality that no backtest showed"* (`02` §2.7). The old design had UTC bounds only.

**12 — Program and Campaign.** A prop-firm lifetime as an ordered phase machine (evaluation → funded → payout → reset) run N times over start dates and seeds, reported as a **distribution**: pass rate per phase, breach rate **by binding rule**, E[net payout] with p05/p50/p95, ruin probability, days-to-funded, worst-fold path metrics (`02` §4.3). The old design had no prop-firm concept at all — and prop firms are a stated major operator goal (`tracker/map.md` §Not yet specified).

**13 — The prop-firm ruleset as a six-axis registered manifest** — anchor, measure, cadence, day-boundary/tz, ratchet-and-lock, breach action — with mandatory `source_url` + `retrieved_on` because *"All three firms' pages changed within four months of the research date"* (`02` §4.2). Plus durable gate state reconciled from the broker's own history at startup, the defect found in **every** framework surveyed (`02` §4.2; `03-wave2-supplement.md` #81).

**14 — Paper mode as a free third wiring.** Live prices, simulated fills, same kernel, same Fill Engine, real clock — *"a prop-firm challenge dry-run at zero risk, and it comes free from the design rather than as extra work"* (`02` §2.1, §4.3).

**15 — Alpha-decay monitoring on the same metrics contract,** with `baseline_id` keyed to the full tuple so a changed Book value makes the old baseline automatically inapplicable, a three-cause split (cost/fill decay, signal decay, regime), comparison **against a band not a number**, and `river.drift` only on the VPS — plus the sequencing insight that *"you do not need a detector today; you need the data that makes decay detectable later"* (`02` §5). The old design had recertification but no continuous monitor.

**16 — Typed fill failures with framework-applied guarantees.** `NoFill(reason)` — slippage may say "no fill" and the counts are reported; the limit clamp is applied **by the framework, not the model**, so a model *"cannot breach a limit price even by mistake"*; partial fills are the default case with a per-bar liquidity budget shared across competing orders; a `PessimisticFillModel` ships alongside the realistic one and *"every promotion candidate runs under both"* (`02` §2.5). The old fill sequence had partial/rejection probabilities but none of these four guarantees.

**17 — Wave-2 physics the old design never reached** (`reference/03-wave2-supplement.md`): two-clock replay of one tape, where the strategy and the venue each hold their own book so look-ahead is *unrepresentable* rather than tested-for (#73); touch ≠ fill, `fill_at_touch_prob` default 0.0 (#95); buys at the ask, sells at the bid, never mid — *"On a 0.8-pip EURUSD spread against a 10-pip target that is 16% of gross edge"* (#98); the fill parameter **fitted against live results** rather than guessed once (#97); latency as a timestamped bus with separate entry and response legs (#93) and real latency collected by placing unexecutable orders on a schedule (#94); charging the strategy for its own thinking time (#102); voiding positions when the sim loses the information its model depends on (#101); ingest-time ordering invariants with quarantine rather than repair (#76, #77); the hash-chained ledger with an external anchor (#110); perturbation PBO for a single strategy (#108); the verdict carrying a `reasons` array naming which pre-registered threshold tripped (#109); `purged_size` as **declared execution latency** with registration refusing `purged_size=0` unless same-bar fills are actually supported (#111).

**18 — A vocabulary ruling that prevents a recurring confusion.** One word, one job: `SimVenue`, Fill Engine, Fill Assumption Set, Run, Replay, Paper mode, Book Matrix, Program, Campaign — and *"the word 'Simulator' never again means the fill engine"* (`02` §1). The old package needed three paragraphs to separate "Examination Engine" from "replay harness" from "Backtest Engine" from "Replay Service" (§1), which is the same problem unresolved.

---

## Re-ratification list

Seventeen decisions. Each is one plain question with a recommendation. None is adopted.

1. **Does the old central Examination Engine dissolve entirely into QMF components — no service, no queue, no scheduler, no separate certification host?**
   *Recommend: yes.* It is your ratified ruling, and B1 shows content addressing genuinely answers the four seams the old design left open (O-02, O-19, O-20, O-26) rather than merely ignoring them.

2. **Is a certificate replaced by a `RunResult` plus a promotion-ladder rung, with no separate certificate object anywhere?**
   *Recommend: yes* — with B2's explicit demotion rule, so an invalidation is a visible event and not a silent key mismatch.

3. **Does `qmf.run.execute()` stay a synchronous library call whose retry is simply re-running the same `RunSpec`, with process-per-run kept only as a fan-out and crash-containment option?**
   *Recommend: yes.* Idempotency comes free from `run_id`; the determinism CI test (1 worker vs N workers bit-identical) is what makes it safe.

4. **Does `RunResult` carry an explicit `RunStatus` including `INSUFFICIENT_DATA` as a state distinct from `FAILED`?**
   *Recommend: yes.* Wave-2 #105: a check that cannot be measured must never collapse into pass or fail, *"or agents will learn which inputs make the check unmeasurable."*

5. **Does old INV-01 carry into QMF verbatim — no table anywhere holds an aggregate "this confluence is good" row, and the Book Matrix is a view, never a record?**
   *Recommend: yes*, with the 12-Books × 500-trials laundering trap enforced in `qmf.ledger` rather than remembered.

6. **Does refusal parity become a ratified invariant, tested by the adapter conformance suite and monitored as live-vs-backtest refusal divergence?**
   *Recommend: yes.* Cheapest extension of an already-accepted mechanism, and the fresh design has the hook but not the rule.

7. **Does the pinning rule generalise — anything that can change the loss distribution is in the result key, or it is a bug — enforced as a test rather than a hand-maintained field list?**
   *Recommend: yes.* This is the old design's PE-8 instinct expressed as a property.

8. **Does `source_class` (self-recorded / materialized-backfill / synthetic / derived / shadow) become a first-class field, with mixed-class splits refused at registration and synthetic-containing runs capped at `measured`?**
   *Recommend: yes.* Without it your ratified "synthetic can stress, never validate" rule is unenforceable.

9. **Do the seven old battery numbers get re-registered as initial pre-registered values, or discarded?**
   *Recommend: split.* Re-register PBO `<0.25` / `>0.50` and CSCV `S=16` as `evidence_state: hypothesis` with a `definition_source`; re-derive the walk-forward windows as `split_id`s; adopt minimum-OOS-trades as a hard rejection with 200 as the recorded prior; carry 0.15R as a **Book-level** threshold, not a global constant. None of the seven has independent support in `research/09`.

10. **Is the old Monte Carlo split into a path-risk test (trade-reorder, reporting drawdown statistics only) and a genuine overfitting test (candle-perturbation MC plus PBO, with perturbation PBO as the cheap single-strategy option)?**
    *Recommend: yes.* As specified, three of the old procedure's four reported statistics are invariant to what it permutes.

11. **Do FORM-0009 and FORM-0010 carry forward verbatim as QMF's cost-adjusted expectancy and break-even formulas, and become the arithmetic behind the edge-vs-spread registration refusal?**
    *Recommend: yes.* Same idea as Novel-3, and the old form is the general one.

12. **Is the per-bot dossier rebuilt as a derived read-model over the run store, keyed by `confluence_id`, linking passing and failing runs?**
    *Recommend: yes.* It is the operator-facing half of "failed runs are the denominator", and without it that rule is storage with no reader.

13. **Do we build the overfit-archetype fixture suite — several fake strategies the battery must fail, one known-good control it must pass — in CI?**
    *Recommend: yes.* Nothing on the fresh side tests the battery's behaviour; this is the strongest single carry from the recovery and it is a few days of work.

14. **Does only `tick`-fidelity evidence reach the `confirmed` rung, with `bar_intrabar` capped at `validated` and optimistic modes capped at `measured`?**
    *Recommend: yes.* It converts old INV-04 from a prohibition that would ban all fast screening into a ladder rule.

15. **Are there two paper roles on one paper mechanism — paper-as-evidence (promotable) and paper-as-fail-mechanism (never promotable)?**
    *Recommend: yes*, otherwise a system that degrades into paper on a bad day manufactures promotion evidence out of its own failure.

16. **Is `[start, end)` ratified as the interval convention for every data request, with boundary-side inclusion an explicit named parameter?**
    *Recommend: yes.* Old O-25 shows it was never actually ratified — only inherited from a helper — and it silently shifts every boundary bar.

17. **Does old §17 "do not recover" become QMF's standing never-build register, and do we hold the in-house-engine line against the NautilusTrader hybrid the fresh verdict restates at full strength?**
    *Recommend: yes to both*, with the already-agreed 3-factory-day adoption spike as the only re-opener on the hybrid.

