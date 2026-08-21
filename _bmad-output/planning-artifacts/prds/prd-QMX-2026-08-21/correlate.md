# Correlation verdict — five old-version mines vs the 2026-08-21 PRD

**Date:** 2026-08-21 · **Role:** correlation synthesizer
**Inputs:** `mine-discussion.md`, `mine-wiki-a.md`, `mine-wiki-b.md`, `mine-node.md`,
`mine-planning.md` (all five read in full — note the *digests* returned for
`discussion` and `wiki-b` were truncated placeholders ("test"), but both extract
files are complete and were read directly).
**Judged against:** `prd.md`, `addendum.md`, and the ratified corpus
(`docs/`, `_docwork/`, `tracker/trading-node-notes.md`).

---

## Verdict in one paragraph

Three old generations were mined. **The domain layer is done** — the laws,
contracts, authority chain, money model, venue law, and evidence discipline of
every old generation are already absorbed into QMF/QMB/QML and bound by
FR-001..FR-050. Almost nothing in `§5` needs to change. **The surviving value is
almost entirely above the framework**, in the two places the PRD deliberately
left thin: the **Phase-2 node outline** (one paragraph today; the old build is
the most complete enumeration anywhere of what the node must *do*) and the
**Phase-3 terminal outline** (one `[ASSUMPTION]` paragraph today; the old wiki
holds a full system-truth register for it). A third, smaller cluster sharpens
**NFR-10 / §9** — the DevOps lens the operator just made primary — with concrete
operability doctrine the old build had already ratified. Two old ideas are
load-bearing and **dead**: the backend-node PostgreSQL standing store, and the
"no CLI, console is the sole surface" stance.

**Counts:** 27 PRD deltas proposed · 28 themes already covered · 20 dead ideas
recorded. Zero deprecated FRs resurrected; zero agentic depth carried.

**Standing rule applied throughout:** where an old item and the current corpus
disagree, the corpus wins and the old item is recorded as superseded — never
merged. Several old "carries" turned out to be *weaker* than what the corpus
already ratified (news scoping, the sizing ladder, the fifth venue command); those
moved to §2 Covered with the delta noted.

---

## Part 1 — PRD deltas

Priority: **H** = materially improves a phase the factory will plan next ·
**M** = real gap, cheap to state · **L** = worth recording, low urgency.

### §1 Vision / §2 Composition and phases

| # | Pri | Section | Concrete change | Source |
|---|---|---|---|---|
| D1 | H | §2 table (row "Simulator UI, MIS") + §6 node | **Disambiguate MIS.** The table defers "MIS" as a consumer product (ADR-0011) while §6 has the node host "MIS publication" — these are two different things and a reader will take §7 as excluding the node's own market intelligence. Rename the §2 row to **"Simulator UI, consumer MIS product"**, and in §6 name the node's layer explicitly as **MIS-Live** — the node-runtime labeler layer that computes market-condition signals and publishes them to Book and KSA, compute-once fan-out, never a consumer surface. | mine-node §3 |
| D2 | H | §2 delivery sequence (after the Phase-1 paragraph) | Add one sentence: **the cTrader capability probe (CT-18 verify-or-refuse) must be sequenced among the earliest factory work units.** Venue feasibility cannot be designed on paper — lot rounding, min-lot, feasibility clamp, and the capability-declaration shape can invalidate upstream assumptions, so deep work must not proceed on an assumed capability set. This is a sequencing constraint for epics-and-stories, not a new FR. | mine-discussion C3 |
| D5a | M | §1 Vision, para 1 | Where the vision says the operator's in-flight powers are "resurrection, periodic review, and ratification", **name the power set concretely**: `resurrection` (the only de-escalation authority), `periodic review`, `ratification/promotion-pull`. The old node's Powers API had exactly these three as its named boundaries — the abstraction and the implementation agree, so the PRD can be specific at no cost. | mine-node §1.7, wiki-a C3 |

### §3 Users and operating model

| # | Pri | Section | Concrete change | Source |
|---|---|---|---|---|
| D3 | H | §3 "Unattended doctrine" | Make the notification constraint concrete rather than negative. Add: **notifications fire only on a closed, ratified event-class allow-list — sweep, re_seed, refund, kill-switch/KSA events, and supervision fail-closed. Everything else is console evidence / UI log, never a push.** Add the two-plane rule: authoritative system records (journals, veto ledger, lineage) and operator notification delivery are separate layers with separate policies — **losing a notification never erases the underlying evidence**, and the notification channel is never a permission path back into live trading. Delivery mechanics (channels, retries, dedup, quiet hours, credentials) stay deferred. | wiki-a C4, wiki-b G, mine-planning A8 |
| D4 | M | §3 bullet 1 ("The operator") | Add a forward-compatibility hook: **one primary operator today, possibly a small team (~3) later — so preserve named action attribution and avoid hard-baking an anonymous single-user assumption into the Powers-API identity model or the terminal.** No collaboration features now. `[ASSUMPTION — needs operator confirmation; the corpus is uniformly solo-operator and this is the one place an old source pushes back.]` | wiki-b E |

### §4 Operator journeys

| # | Pri | Section | Concrete change | Source |
|---|---|---|---|---|
| D5b | H | §4 (new bullet) | Add the missing review journey: **"Run the periodic review" — a named weekly ritual (Sunday review) and a retirement decision (sunset review), both Powers-API actions fed by read-model evidence (performance explanation, footprint/decay sensing, reconciliation status).** The PRD cites "periodic review" three times and never says what it is; these are the two rituals the old build actually named. | wiki-a C9, mine-node §1.7 |
| D6a | H | §4 "Promote a bot to live" | Extend the journey one clause: **the promotion click re-executes its full precondition battery server-side against fresh state at click time — a displayed-eligible state is never a guarantee, and stale evidence never authorizes anything.** The crossing is a **node-initiated pull, idempotent by artifact key** (re-click is a no-op), and success lands the unit in an `ADMITTED` state with no intents and no ledger — **distinct from activation**, which is a later boundary. | wiki-a C3, wiki-b C, mine-planning F2 |

### §5 Functional requirements (V1) — only two FRs touched

| # | Pri | Section | Concrete change | Source |
|---|---|---|---|---|
| D7 | H | §5 C, FR-018 | Extend FR-018: the news-calendar capability is **multi-source with a normalized single import** — a primary feed plus impact-carrying fallbacks behind one import path, every import journaled, and a **daily pre-trading-day refresh as a required ritual**; a failed refresh falls through the source chain and then degrades **visibly** to the corpus's fail-closed block, never silently opening. Add to §10 that **DEC-0119's open provider-selection item now has evidence**: the old build evaluated Forex Factory's free weekly JSON as primary (rate-limited ~2 downloads / 5 min) with FMP / Trading Economics / FXStreet as fallbacks, **disqualified EODHD for carrying no impact field**, and rejected scraping. Record as evidence for the operator's ruling, not as a ratified choice. | mine-planning D2, wiki-a C11 |
| D8 | M | §5 C, FR-017 + FR-042 | FR-017 already says Dukascopy is the *first* source; make the roster's extensibility a capability. Extend FR-042: **deep-history acquisition is multi-source (download → clean → maintain, each stage manifested, raw→cleaned linked by derivation), with a stated minimum depth and the broadest obtainable forex set.** Record two facts from the old build as inputs, not requirements: TrueFX (16 majors, tick since 2009) and HistData (M1 + tick) were the evaluated companions to Dukascopy, Databento carries no spot FX, and — the load-bearing one — **venue-only backfill is rate-capped into unviability, so the recent window needs a platform-continuity bridge rather than a broker backfill.** | mine-planning D1 |

### §6 Future-phase outlines — Quant Mind trading node (Phase 2)

The current outline is one paragraph. These six replace it with a capability-level
seam list. None is new scope; each decomposes what the paragraph already names.

| # | Pri | Section | Concrete change | Source |
|---|---|---|---|---|
| D9 | H | §6 node | **Startup, preflight, and recovery ordering.** Add: a deterministic cold-start preflight gate runs *before any state mutation* (host/disk/network-reachability/pinned-version checks, fail-closed with a typed failure id), then a fixed per-Book startup order — connect → reconnect gap recovery (fetch deals/positions since the last-seen execution event and commit recovered fills **before** reporting healthy) → missed-rollover catch-up (reconstruct boundary equity from journals, journal the sweep as a correction-style append) → protection-state projection (breaker counters, drained budget, exposure rebuilt **from journals**) → readiness gates → sequencer accepts intents. Invariant worth stating plainly: **a crash never resets safety counters, because there are no safety counters — only journal projections.** | mine-node §1.1, mine-planning A2 |
| D10 | H | §6 node | **Reconcile the explained relationship, never raw equality.** The "ledger↔broker drift kill" the outline names must decompose broker-vs-virtual divergence into journaled components (swept-but-unwithdrawn cash, re-seed remnant gaps, open-position unrealized P&L); **only the residual after explanation is drift**, so a sweep or re-seed never false-fires the kill. Verdicts are exactly `reconciled | drift | unknown`; unexplained live drift halts trading, and **operational restart is not permission to resume** — a fresh reconciliation review is required. The paper/demo binding is **excluded** from the live drift check. | mine-planning A3, mine-node §1.3 |
| D11 | M | §6 node | **Platform rate limits are a first-class design input, not an ops detail.** The connection manager owns one pool per account binding with multiple connections per live account, per-account command affinity for order-lifecycle commands, and token-bucket limiting — because **rate caps are per connection**, so a synchronized burst (mass invalidation-close plus re-amend) can breach the cap at protocol level with no HTTP status to read. The order path therefore *requires* connection sharding or a shared token bucket; this is also the seam a future multi-account / multi-platform load balancer attaches to. | mine-planning A4, mine-node §1.2, tracker (K-42) |
| D12 | H | §6 node (and cross-ref §9) | **Fail-closed stand-down is an ALIVE state.** On a crash-loop threshold (K restarts in T minutes, both unruled), the process **boots into stand-down rather than staying dead**: sequencers refuse-and-journal every intent, adapter connections quiesce and drain, and **the operator powers surface keeps serving** — so resurrection and ratification stay reachable exactly when they are needed. Add the paired enforcement rule: **a protection transition must quiesce and drain all of an account's connections before enforcement counts as complete**, so pool reordering cannot land a queued order after a `close_all`. | mine-planning A5/A6, wiki-b I, wiki-a C11 |
| D13 | H | §6 node | **Give "MIS publication" and "shadow rollout" their shape.** MIS-Live is a labeler layer publishing a snapshot to Book and KSA. A **shadow lane** runs candidate labeler/model versions as near-real-time replay over the **captured canonical feed** (identical inputs by construction), off the hot path, emitting to its **own manifest prefix, never to live consumers**, evaluated over **one full affected-book cycle**; promotion is ratification → version bump → re-certification cascade, with **no data copied**. Two governance facts to carry: **a recovered or pre-trained model carries no authority** until fresh ratification with parameter identity, training evidence, and shadow evidence; and **training is an offline job** — the no-ambient-randomness invariant binds the live runtime, so an offline trainer may seed the RNG provided it **records the seed**. | mine-node §3, mine-planning C1/C3 |
| D14 | M | §6 node | **Name the always-on evidence/heavy-compute placement tier.** The node phase implicitly needs somewhere durable for the archive, captured canonical feed, heavy analytics, and the shadow lane. State it as a **placement and authority boundary, not a deployment mandate and explicitly not a database server or a second writer**: the trading hot path **never blocks** on it (only disk physics fails the hot path closed); sync is **one-way, watermarked, idempotent, resumable, under verify-before-purge** (the hot side purges only past what the evidence side has durably persisted *and* content-verified — hash/row-count, never mere receipt); recovery is a **backend-initiated re-request carrying watermarks only, never payload flowing backward**; and the **only reverse crossing is the click-gated promotion pull** (D6a). Add the hedge the old wiki itself carried: this is a placement boundary, not a mandate that each box is a separately deployed service. | wiki-a C1/C2, wiki-b H, mine-planning A1 |

### §6 Future-phase outlines — QMX terminal (Phase 3)

The outline is currently one `[ASSUMPTION]` paragraph. The old wiki holds a full
system-truth register for exactly this; these six turn the stub into a grounded
outline without deciding layout or styling.

| # | Pri | Section | Concrete change | Source |
|---|---|---|---|---|
| D15 | H | §6 terminal | **Replace the stub with the console spine.** The terminal is **UI-only and never a second system of record** — business authority, persistence, and command validation stay server-side; it is a **desktop application that holds no trading secrets**; it is **not a manual-trading or generic market-analysis terminal** (optimize for system operation, safety, evidence, and repeated expert use); and its UX is **unattended-by-default** — it must not invent an intraday human-control loop. It reaches the platform through **exactly two channels**: an evidence *read* channel and a **Powers API** *action* channel, with **evidence review and command execution as visibly distinct steps**. Carry the anti-goals verbatim, they are the sharpest part: **no direct manual-trading surface; no generic LIVE/PAPER operator toggle; no single global health indicator that hides independent failure domains; no stale evidence authorizing an action; no editable setting without registry-backed configurability; no optimistic command success without server validation and evidence; no Prometheus/Grafana clone; no assumption that a future venue is recolored forex.** | wiki-b A |
| D16 | H | §6 terminal + §8 NFR-10 | **State independence and read provenance.** Safety, execution readiness, connection, reconciliation, data freshness, lifecycle, and sync are **independent states that must never collapse into one health color**; "trading operational" and "evidence sync degraded" are distinguishable; **requested protection state is shown separately from enforcement completion** (a KSA escalation is *requested*; it is not enforced until connections quiesce and drain — pairs with D12). Every important read reveals **authority source (live-authoritative vs replicated evidence), source time, receive time, and watermark** — read models carry provenance, not a spinner. This is a platform-legibility law for operator *and* agent, independent of the node rewrite. | wiki-b B |
| D17 | M | §6 terminal | **Name the data plane the terminal reads.** A family of **publish-never-act read models**, each budgeted, authority-free, and returning refusals as evidence: a **Records Read API** (journals, veto evidence, cycle events — no write authority), a deterministic **replay** read model, a **performance-explanation** read model, a **decay / footprint-drift sensing** read model, and an **archive access** read model. This is the concrete back end for the outline's existing "browsing evidence/journals/lineage" bullet. | wiki-a C7 |
| D18 | H | §6 terminal + §8 NFR-07 | **Editability is evidence-driven, not a boolean.** Render **three settings scopes distinctly** — system settings (secrets and bindings, console-managed, never registry numerics), component settings (registry), and instance values (registry under instance ownership); "settings = registry + secrets store, a superset, never a synonym". Then the UX invariants: a non-configurable value **renders read-only**; a **null renders as *unresolved*, never as an editable default**; **measured and provisional values are not settings** and must not masquerade as them; **a provisional value requires an explicit operator countersign in the console before live**; and a value fixed within an active cycle (the kill line) is not editable mid-cycle. Add the one concrete config object the old build named: **Book↔account bindings are console-configured, mutable, and journaled, in system-settings scope.** Consequence for the corpus: the variables registry currently carries `configurable` but **no value-status field** — the terminal cannot decide editability from data until it does. | mine-planning F4, wiki-b D, wiki-a C10 |
| D19 | M | §6 terminal | **Venue containment as a shell rule.** Future forex-adjacent, crypto, or other venue experiences reach the operator through the **same product shell via a venue selector** — valid shell architecture — **but each venue may carry a different information model**. Forex must work completely on its own, and **future venues never force false shared concepts into the forex UI or arrive as "recolored forex"**; each enters behind its own externally designed and ratified adapter. A design constraint for Phase 3, not a V1 build. | wiki-b F |
| D20 | M | §6 terminal | **Promotion evidence panel and the per-bot dossier.** The promotion click presents an evidence panel — conformance/certificate summary, **pair and session overlap with the live roster, and spec/footprint similarity to existing bots** — recomputed against the fresh roster at click time, so **the human performs the dedup and correlation judgment V1 deliberately declines to automate** ("the forex entry-model space is finite and hypotheses repeat"). Pair it with the **per-bot dossier**: every artifact about a bot (declaration, run results including failures, reports, notes) attaches to its bot id from system entry onward, immutable and lineage-linked, as a first-class terminal surface. | mine-planning F3/F5 |

### §8 NFRs and §9 Success measures

| # | Pri | Section | Concrete change | Source |
|---|---|---|---|---|
| D21 | H | §8 NFR-02 | The PRD asserts float-purity is "enforced by gate tooling, not review" (§9) but names no tool. Add to NFR-02 that **two static scanners ship as tier-1 gate artifacts**: a **money-path scanner** (a declared money-name-fragment set — money, price, equity, sizing, size, budget, offer, take, cost, loss, payoff, pnl, notional, margin — crossed with a forbidden AST set: float call, float literal, float annotation, division on a money path — with an explicit allowed-context allowlist), and an **ambient-nondeterminism scanner** (forbidden-call list: `datetime.now/utcnow`, `time.time/monotonic/perf_counter`, `random.*`, `secrets.*`, `np.random`, with a per-path allowlist). These make FR-001 and FR-002 mechanically enforceable instead of aspirational. | mine-planning G3 |
| D22 | H | §8 NFR-10 (or a new NFR-11) | **Failure-register discipline — the rendered half of typed refusals.** Every designed failure mode ships a register entry: failure class, detection, auto-recovery/retry semantics, the visible degraded state, its notification tier, and a **product-user affordance — what failed, why, can I retry, and what a retry does — written for a user who was not in the design room.** CT-04 gives the machine-legible refusal; this is the operator-legible one, and it is the direct instrument of the "one-person operability" lens: the sole operator is treated as a *product user* for failure rendering. | mine-planning G5 |
| D23 | M | §8 NFR-10 / §9 | **One observability substrate, two consumers.** State that the monitoring/evaluation substrate stood up for QMF/QMB must be **the same one that later serves QMA** — not two stacks — and that the external plane (Prometheus/Grafana class) is **zero-authority**: it consumes exported evidence and never becomes a control or authority path. The corpus already binds exportability (DEC-0112) and "an alert is evidence, not permission" (DEC-0041); what is missing is the serve-both-layers constraint, which is cheap now and expensive to retrofit. | mine-discussion C4, wiki-a C5, wiki-b G |
| D24 | M | §9 "Deployable, out of the box" | Add the old build's plain-words shipment criterion, which is the sharpest statement of this lens anywhere: **install, start, stop, back up, and recover from one canonical checkout — the operator must not hunt across folders or reconstruct Git state.** Add the crash posture: **restart-on-failure with a burst cap, so a crash loop stops instead of thrashing** (and lands in stand-down per D12). | mine-node §2 |
| D26 | M | §9 counter-metrics | Add a **fabrication counter-metric** for the factory lanes: **no code, spec, enrichment, or review agent may invent mock, synthetic, or placeholder data**; a missing value, dependency, or architectural answer must **fail closed and land in the ledger, never be fabricated**. Reconcile explicitly with FR-041: synthetic data is legal **only** as a claim-class-labeled artifact (infra-stress / robustness / logic-smoke), **never as a silent stand-in for missing production data**. This is the guardrail that keeps autonomous factory agents honest. | mine-planning G2 |

### §10 Open items

| # | Pri | Section | Concrete change | Source |
|---|---|---|---|---|
| D25a | M | §10 new row | **Alpha-decay signal catalog (future sitting, alongside GAP-0048/0049).** The corpus ratifies the *concept* and its guardrails (L26/DEC-0092, SCN-0008's cohort key, SCN-0006's paper-outage corruption) but carries **no signal list**. Record the four candidate signal classes as an input catalog — **breaker-door/leash-event fire density, MAE/MFE drift, drawdown decomposition, and regime/session-conditioned performance drift** — plus measured proximity to a charter-death condition. Guardrails ride with the carry: measured quantities and registry formula derivations with golden scenarios, **never a declared-weight composite score** (that would brush FR-034/CT-32 and DEC-0018), and decay **informs, never disposes** — it feeds the operator's sunset review (D5b), never a hot-path actor. | mine-discussion C1, wiki-a C8 |
| D25b | M | §10 new row | **Node-phase position-safety ratification cluster** — four questions the old build never closed and the current corpus has not either, recorded so they are not re-discovered: (a) **stop-out taxonomy** — does a breakeven exit or a forced flat count toward the breaker and toward sizing (the corpus rules breakeven exits out of the bench; the *sizing* half is open); (b) **position fate at money boundaries** — flatten-first vs carry at rollover/sweep/re-seed/paper flip, and how unrealized P&L enters a sweep (the corpus rules boundaries leave positions alone; the P&L accounting is unstated); (c) **dynamic SL/TP grammar** — belongs in the Book grammar with the BMS as config authority; (d) an **amendment idempotency threshold** — emit an SL/TP amend only if `|proposed − current_confirmed| > threshold`, a UI-editable configurable that suppresses tick-storm duplicate amendments and stacked broker-queue conflicts. | mine-planning B4, mine-discussion C2 |
| D25c | L | §10 new row | **Atomic decision-plus-evidence commit vs the swappable store seam.** The old build's invariant was that a decision state change and its journal append **commit atomically in one transaction** (door verdict + veto ledger; mode row + Book journal; treasury ledger + boundary event), with **exactly one owning module per governed entity**, foreign entities reached only through the owner's API. The corpus has WriterId ownership and gapless per-writer streams but no dual-write atomicity rule — and the store seam spans engines that do not all offer transactions (Parquet/JSONL). **Flag for architecture: is atomic dual-write a journal-path requirement, and does it constrain the store seam?** Corpus wins pending a ruling. | mine-planning G4, mine-node §1.5 |
| D27 | L | §6 QMA paragraph | Record — as a **track input, not a change to the current door model** — that an earlier ruling set the agentic data-egress boundary as **pull-only access to curated datasets, with no live-service surfaces exposed to agents at all**. The PRD's current posture (typed doors: `qmb` CLI, Python API, optional MCP) stands; the older stance is a cleaner *starting* governance position for the QMA track to weigh when its ideation begins. Not agentic depth — a one-line boundary note. | wiki-a C6 |

---

## Part 2 — Already covered (do not re-import)

Old-version themes the PRD or the corpus already carries. Several are covered
**more strictly** than the old source stated them — noted where so.

| Old theme | Where it already lives |
|---|---|
| Four-outcome venue law; UNKNOWN is a state; blocks its `(venue, account)` stream | FR-023/024, CT-19/20, L35, SCN-0005 — **stricter**: the corpus clears the block only on an explicit typed `resolve_unknown`, **never on a reconciliation verdict** |
| "`amend_order` as a fifth venue command" | Already minted 2026-08-20 as **`amend_protection`** — deliberately narrower; a general `amend_order` and partial close stay unminted (FR-023, CT-19) |
| Authority chain, Book as chartered gatekeeper, BMS accounts-but-never-trades | FR-027, CT-22/27, ADR-0008, L1 |
| Money-ladder sizing chain (old FORM-0002..0006) | Absorbed as the units-only ladder: `loss_runway → period_loss_budget → r_unit_price → position_risk_amount`, with the overloaded legacy `B` split into two typed variables (DEC-0154, CT-23) |
| Treasury cycle / rollover-only sweep / seed / cap / kill line | Treasury boundary events, `kill_line_flat` close reason, per-binding `state_carry` — **corpus adds a fourth boundary kind (`paper_epoch_reset`), superseding the old "a fourth event fails validation"** |
| Paper as a Book-level dated standing state | FR-029, CT-24, SCN-0006 |
| Records as a single append-only journal writer; per-entity streams | FR-013, CT-13 |
| Registry of governed numbers; blank blocks live money; `configurable` = UI-editable | FR-035, L38, `docs/registry/variables.yaml` |
| Secrets as references only, never leaving the connection manager (systemd-creds is one implementation of it) | FR-025, CT-21, L34, NFR-05 |
| Human-signed promotion as the only path to live money | FR-009, ADR-0015, SCN-0007, L17 |
| KSA escalate-only, operator-only de-escalation; kill switch and kill line named apart | §6, CT-30/31, glossary — the two are explicitly never interchanged |
| News blocking: instrument-scoped, fail-closed, live and paper alike | FR-033, CT-31, DEC-0152 — **stricter**: scope resolves through dated per-instrument currency-exposure records and **reading a currency out of a symbol is prohibited**; **widen-never-shrink** is already the ratified read-time fold |
| Exit-preservation invariant; Book-owned risk-monotonic exits; bots propose only risk-reducing exits | FR-032/033, CT-29/30, L39 |
| Measurement publishes and never acts; no composite score gates money; bench as a read-time fold | FR-034, CT-32, SCN-0011 |
| Backtest parity and reproducibility (one run loop; config fingerprint is the run id) | FR-036, SCN-0012 |
| Robustness battery (walk-forward, Monte Carlo, PBO/CSCV) | FR-040 — *separately*, the fidelity sweep found FR-039/040 over-bind the ratified QMB spine; the old sources do not settle that and should not be cited to |
| Fill/slippage/fee modeling with fidelity taint | FR-044, GAP-0048 |
| Dukascopy download-once, personal-use, ship-no-corpus licensing gate | FR-017/042 — the old pipeline encoded the same fail-closed licensing posture |
| Measure-then-budget performance; no invented numbers | NFR-04, DEC-0111/0138 — the node's 35 ms / 10–45 ms / 100 ms budgets are **evidence, not spine constants**, already recorded in `tracker/trading-node-notes.md` |
| External monitoring plane with zero authority | Exportability to Prometheus-class stacks (DEC-0112) + "an alert is evidence, not permission" (DEC-0041), `docs/lenses/observability/metrics-and-alerts.md` |
| Behavior-anchored testing doctrine; coverage as a counter-metric | `docs/lenses/testing/test-strategy.md` — "never substitutes a coverage percentage for behavior evidence", named behavior + failure-mode assertions, injected clock, declared seed, no network, synthetic fixtures never satisfy an edge assertion (DEC-0054/0096) |
| Attribute inertness at the bot boundary | **Structurally satisfied by CT-33**: everything a bot's logic consumes lives in the declared footprint plus parameter space, both inside the declaration's `fp1`, so consuming a new input mints a new bot identity by construction. The old EAV attribute bag is dead and the binding allow-list is unnecessary under this shape |
| `.qml` DSL dead; plain-Python bots first-class | FR-047, ADR-0018 |
| Append-only lineage, never-delete, two version ladders | FR-005/007, DEC-0103 |
| Recoverability claimed only through verify | FR-014, CT-14, SCN-0004 |
| Venue / platform / instrument three-axis identity question | **Ruled**: broker identity is deployment configuration, never architecture ("account IDs are enough", tracker 2026-08-20); the asset-class axis is closed by the forex-only V1 scope with futures/options permanently excluded (§7) |
| Console as a powers-bounded surface | Survives into D15; the old "no CLI, console is the sole surface" half is dead (DEC-0185) |
| A knowledge base serving humans and agents (old QuantMindWiki) | The `docs/` corpus produced by the documentation factory — versioned, append-only, ratification-gated |
| Startup reconciliation gates the command pipe only; sensing keeps flowing | FR-024, K-39, `trading-node-order-path-study.md` |

---

## Part 3 — Deprecated (recorded so nobody re-mines them)

1. **Backend-node PostgreSQL standing store + the two-node CT-SYNC-01 replica topology.** The one architecturally load-bearing old idea that is *dead* under "no DB server anywhere in V1" (FR-016, NFR-10, L30). Only the placement/authority shape survives → D14.
2. **Four-node microservices topology** (trading / backend / database / desktop UI, mutual-TLS cross-node) from the oldest vault — dead.
3. **The old FR-1..FR-41 list, the 2026-07-20 spine and PRD, the 10-epic/100-story plan, and `TRADING-NODE-SHIP-GOAL.md`'s Epic-1–7 mission** — operator-deprecated; epics regenerate from this PRD.
4. **Old contract namespaces** — `CT-BMS-*`, `CT-BOOK-*`, `CT-MIS-*`, `CT-SYNC-*`, `CT-DATA-*`, `CT-SEC-*`, `CT-PAPER-*`, `CT-ATTR-*`, `CT-KSA-*`, `CT-EXAM-*`, `CT-NOTIFY-*`, `CT-QML-*`, `CT-ADAPTER-*`, `CT-REG-*` — plus the old AD/L numbering. Re-derived into CT-01..CT-34 / DEC-0001..0185 / AD-spine / L1..L39. **The ID systems do not line up; never cite an old ID as current.**
5. **"No CLI / config-file surface; the desktop console is the sole surface"** — superseded by DEC-0185: the `qmb` CLI is the single command-line surface.
6. **The "no MCP" absolute** — superseded by the optional-never-required MCP door (FR-046).
7. **DPR / PRS merit ranking, T1/T2/T3 tiers, capital slots, slot auctions, global bot pools, intracycle merit reallocation, opinion-weighted sizing, conviction-based slot substitution** — dead (DEC-0093); only the read-only *measurement* patterns survive → D25a.
8. **WF1/WF2/WF3 lifecycle states, the paper-to-live redemption loop, the six-transition paper model, automatic live→demo demotion, in-place revival, identifier recycling** — dead; promotion is human-signed only.
9. **`TIGHTEN` kill-switch level / "trade half-size through bad conditions"** — explicitly dead (DEC-0019); never revive.
10. **Examination Engine as a book-admission certifier** and its constants (6mo IS / 1mo OOS / 200 OOS trades / 0.15R floor / 1000 MC / PBO 0.25/0.50) — superseded by QMB backtesting plus QML technical-never-performance conformance. **Those numbers are legacy scalper values, not corpus authority.**
11. **6-clamp half-Kelly, the 9-multiplier canonical sizing formula, cost-aware Kelly with a trust bound, `fee_adjusted_RR < 1.1` hard-block, realized-R:R as a Kelly input** — dead; CT-23's admission model and the units-only ladder replace them. FORM-0006 is retained only as a permanent negative test.
12. **The old "QML shared contract library"** (`BotSpec`, `MarketIntelligenceSnapshot`, `RiskAuthorization`, `TradeIntent`, `ExecutionDirective`, `KillSwitchEvent`) — **the name collision is a trap**: today's QML is bot-authoring. `BotSpec.exit_logic` and `ArchetypeSpec` constraint powers are retired; the `.qml` DSL file is dead.
13. **The entire old agentic system** — four departments, Floor Manager, Copilot, WF variant/mutation/pool-cleaning pipelines, inter-department mail, opinion nodes, video ingest, trader-agent class, signal lane/journal, bot-factory pipeline, morning brief, activation records, agent identity system — and the **RAG / semantic-search knowledge vault**. Scrapped; QMA is a fresh track whose ideation has not begun. Do not carry old agentic requirements in any form.
14. **Recovered non-authority models** — Kronos, HMM, BOCPD, MS-GARCH — and `regime_classifier_v1`, whose model family is a literal `"..._placeholder"` with `training_location: unresolved`. No architecture, hyperparameters, or label-generation method was ever ratified. Downloads, prior training, and popularity authorize nothing.
15. **EAV / sparse attribute-bag as a filter surface** — forbidden; typed core fields are the legal filter surface.
16. **Riskfolio as any kind of authority** — only ever dead-zone drawdown analysis; a donor reference at most.
17. **Vocabulary tombstones** — trading-floor metaphor, KSA-under-MIS, "evidence node" / "middle node", genesis / progenitor / DNA / genome, crypto-adaptable V1 grammar, and "quantitative" (the word is **algorithmic**).
18. **Branch lanes as evidence classes** (development = sim, staging/beta = paper, main = live) — superseded by the integration→main factory model. The "each lane is a class of evidence" framing survives only as a mental model.
19. **"Proof-shaped" module style** — pure-data validators against `standards/*.json`, no sockets and no training — an artifact of the interrupted old build. The node is expected to be rewritten on QMF.
20. **"The desktop console is load-bearing V1 scope" (old GAP-0014)** and **global SL/TP authority with the old `amend_order` close-priority model** — the first is superseded by the QMF-first / terminal-last phase order; the second by five command kinds plus Book-owned risk-monotonic exits, with `close_partial` already out of scope (§7). The 43 ratified `standards/*.json` and the `sprint-status.yaml` / `dev-auto` BMAD loop are likewise superseded — the standards are concretizations of ADs already absorbed.

---

## Part 4 — Routing and cautions

**What belongs in `tracker/trading-node-notes.md`, not the PRD.** The tracker is
already the standing cross-session ledger for node-era detail, and it carries a
standing operator instruction to collect exactly this material. Everything below
D9–D14's *capability* statements — the concrete mechanics (pool sizing numbers,
OAuth chains, migration-runner rules, capacity-driver lists, systemd unit
hardening, the labeler catalog, the SQS parameter set) — should land there rather
than swell §6. The PRD states the capability; the tracker holds the mechanism.

**Three conflicts where the corpus wins and the old source is simply wrong now.**
(1) News scoping — the old "currency → all pairs containing it" is looser than the
corpus's dated currency-exposure records; do not merge. (2) Treasury boundary
events — the old "exactly three kinds, a fourth fails validation" is superseded by
four. (3) The fifth venue command — the old general `amend_order` is superseded by
the deliberately narrower `amend_protection`.

**One PRD-internal inconsistency the mining surfaced** (D1): §2 defers MIS while
§6 has the node host it. That is a two-word fix and should not wait.

**On the two truncated digests.** The `discussion` and `wiki-b` digests arrived as
placeholders; both extract files are complete and were read in full for this
synthesis. `wiki-b` in particular turned out to hold the single richest artifact
of the whole mining run — the trading-console alignment register behind D15–D20 —
so a reader relying on digests alone would have missed the terminal material
entirely.
