# Mining extract — LATER old-version planning & standards layer (`C:/Users/Mubarak/Documents/QMX`)

**Miner:** planning/standards sub-agent · **Date:** 2026-08-21
**Source scope:** root planning files (README, DECISIONS-LOG, AGENTS/CLAUDE, wiki-doc-pass-report,
mkdocs, TRADING-NODE-SHIP-GOAL), `standards/` (43 files), `_bmad-output/` (277 files — old
PRD `prd-QMX-2026-07-20`, `ARCHITECTURE-SPINE.md` 45 ADs, `epics-v2-draft.md`, UX console extract).
**Coverage judged against:** `prd-QMX-2026-08-21/prd.md` (current lean PRD, cites `docs/`).

## What this source is

The Documents/QMX tree is the **later** old build — the *deterministic trading-node section*: a full
PRD (41 FRs / 8 NFRs / 17-law constitution), a 45-AD architecture spine (topology v2, 2026-07-23), a
10-epic / 100-story breakdown, 43 ratified engineering `standards/*.json`, and a live-but-halted
trading-node implementation (Epics 1–7 partially built, Dukascopy acquisition, cTrader adapter). It is
the direct predecessor of the current QMF reframing.

**Overall disposition.** The *domain laws and contracts* of this layer are already absorbed into the
current corpus (QMF took AD-1..41 + the constitution and reframed them into a pure library). What is
**NOT** in the current corpus, and still valid post-QMF, is almost entirely **runtime and surface**
material the current PRD pushed to thin future-phase outlines (§6): the **trading-node runtime**
(Phase 2), the **terminal/console** (Phase 3), the **MIS/model layer**, **data acquisition depth**,
and a set of **cross-cutting engineering standards** for the factory lanes. The old FR list itself is
operator-deprecated and NOT mined. Everything below is mined for framing + still-valid mechanism only.

Two whole-corpus tensions to flag up front:
- **No-CLI / desktop-console-only** (old AD-33/§4.13) is **superseded** by the current DEC-0185 (`qmb`
  CLI is the single command-line surface). The *console-as-powers-bounded-surface* idea survives for
  Phase 3; "no CLI" is dead.
- **Backend-node PostgreSQL evidence home** (old AD-5/AD-13, topology v2) collides with the current
  **"no DB server anywhere in V1"** posture (FR-016, NFR-10) and "node likely rewritten on QMF." The
  *architectural shape* (always-on evidence home + one-way verify-before-purge sync + click-gated
  promotion pull) is worth carrying to Phase 2; the concrete PostgreSQL choice should be reconciled
  against the QMF data-store seam at Phase 2 design, not assumed.

---

## CARRIES — still valid post-QMF, not in current corpus/PRD

Grouped by the current PRD section each would enrich. Each item names the old ID(s) for traceback.

### A. Phase 2 trading-node runtime — enriches PRD §6 "Quant Mind trading node" (currently one paragraph)

**A1. Two-plane node architecture + evidence-home topology + verify-before-purge sync.**
(old AD-5, AD-6, AD-7, spine paradigm) — "**Sensing fans out** (MIS-Live → subscribers, computed once);
**accounting concentrates** (every state change + refusal → the single journal writer)" is a clean mental
model for the node. The runtime keeps only a bounded hot window and **never blocks** on the evidence
home; sync is **one-way** hot→evidence under **verify-before-purge** (the hot node purges a stream only
past positions the evidence home has both *durably persisted AND content-verified* — hash/row-count, never
mere receipt); a **backend-initiated re-request** control message carries watermarks back (no payload data
ever flows backward); **heartbeat watermarks** carry a cross-stream consistency position even when idle so
the joinable frontier advances instead of stalling. The **only** reverse crossing is the click-gated
promotion pull (A/F below). *Reconcile the PostgreSQL choice against QMF's no-DB-server data-store seam.*

**A2. Startup recovery discipline — fixed ordering, everything a journal projection.**
(old AD-9, AD-10, AD-11, AD-43) — per book, startup proceeds in a **fixed order**: connect → **reconnect
gap recovery** (fetch deals/positions since last-seen execution event, append recovered fills with
label-based attribution *before* reporting healthy) → **missed-rollover catch-up** (reconstruct boundary
equity from journals + broker deal history, journal the sweep as a correction-style append) →
**protection-state projection** (breaker counters, drained budget, exposure/concurrency rebuilt from
journals — a readiness gate, never a "live-state guess") → readiness gates → sequencer accepts intents.
A crash never resets safety counters. This whole cluster is absent from the current corpus (it is
node-runtime) and is directly reusable for the QMF-based node.

**A3. Reconciliation by explained-delta (the "ledger↔broker drift kill" §6 names).**
(old AD-10, FR-26, `reconciliation-reports-and-technical-kill.json`) — reconcile the **explained
relationship**, never raw equality: decompose broker-vs-virtual divergence into journaled components
(cumulative swept-but-unwithdrawn cash, re-seed remnant gaps, open-position unrealized PnL); only the
**residual after explanation** is drift, so a sweep or re-seed never false-fires the kill. Runs
per-account-binding; the paper/demo binding is excluded from the live drift check. Verdicts are exactly
`reconciled | drift | unknown`; unexplained drift halts trading and restart requires *fresh* reconciliation
review (operational restart ≠ permission to resume).

**A4. Connection-manager design + platform-rate-budget-fit.**
(old AD-30, NFR-8, `connection-manager-core.json`, `connection-pool-sizing-*.json`) — one component owns
platform sessions: **pool per account binding, multiple connections per live account** (rate cap is
*per connection*: cTrader 50 req/s general + 5 req/s historical), **per-account command affinity** for
order-lifecycle commands, **token-bucket** limiting, `label`-based per-bot fill attribution, `clientMsgId`
command↔fill correlation, arrival-stamping of unstamped events, OAuth token refresh. **Platform rate
limits are a first-class latency input**: a synchronized burst (mass invalidation-close + re-amend) can
breach the per-connection cap (protobuf-level rejection, no HTTP codes) → the order path *requires*
connection sharding or a shared token-bucket. This is the seam a future multi-account/multi-platform load
balancer attaches to. Some of this may also sharpen qmf-venue's cTrader adapter.

**A5. KSA / kill-switch transition barrier.** (old AD-23) — a protection transition must **quiesce and
drain ALL of an account's connections before enforcement counts complete**, so pool reordering can't land
a queued order after a `close_all`. A clean invariant for the node's kill path.

**A6. Fail-closed stand-down as an ALIVE state.** (old AD-36) — a crash loop (K restarts in T minutes)
**boots the process INTO fail-closed stand-down** rather than leaving it dead: sequencers refuse-and-journal
all intents, adapter connections quiesce/drain, but the **powers API keeps serving** so resurrection and
ratification stay reachable *exactly when needed*. systemd `Restart=on-failure` + start-limit counters.
This is a strong operability doctrine that directly serves the current DevOps success lens (§9) and NFR-10.

**A7. Observability tiering + external zero-authority monitoring plane.** (old AD-37) — all collection
tiered hot/warm/cold (collect what the design needs, not everything); **Prometheus + Grafana as an
*external* monitoring plane** (Loki optional for logs), outside the system, **zero authority**, consuming
synced metrics — the operator and maintenance agents watch/repair from there. **Journal durable-commit
latency** is a required hot-tier metric from day one: a GIL-contention canary, the store-swap-trigger
signal, and a capacity-model input. Aligns with "monitoring built in, not bolted on" (NFR-10).

**A8. Notification firing set.** (old AD-37) — actual push notifications fire on a **small enumerated
set only**: sweep, re_seed, refund, KSA/kill-switch events, and supervision fail-closed. **Everything else
is console evidence / UI-log only.** Concrete realization of the current "notifications never create
intraday decision loops" doctrine — a two-tier model (small push set vs passive evidence log).

**A9. Capacity model → minimum node spec.** (old AD-5 deferred, `capacity-model-micro-bench.json`) —
a named measure-then-spec deliverable: drivers are tick fan-out × pairs, labeler compute per snapshot,
durable-commit rate, sync egress, archive growth/day, read concurrency; spec values registry-owned,
**null until measured**, provisional envelope never authority. Same philosophy as current NFR-04
(measure-then-budget) but scoped to sizing the actual VPS.

**A10. Deployment + backup envelope.** (old AD-36, AD-38) — cloud/Linux design target for the node,
laptop bootstrap parity only; node colocated near the broker server for latency; systemd-creds for
node-service secrets. Backup: SQLite `db+wal+shm` as **one unit via the backup API** (never file-copy a
live db), data dir AV/indexer-excluded, WAL never on a network filesystem; because the hot node retains a
`hot_retention_days` window, an evidence-home restore replays the recent window from it, **bounding RPO by
backup-age-minus-retention-overlap**. Branch lanes carried an *evidence-class* meaning (development = local
sim evidence, staging/beta = paper evidence, main = live evidence) — superseded by the current
integration→main factory model, but the "each lane = a class of evidence" framing is a nice mental model.

### B. Phase 2 money-management / risk runtime — GitBook-authoritative; enriches §6 + confirms qmf-risk gaps

**B1. Treasury / cycle / rollover-sweep / seed / cap / kill-line model.**
(old §4.8, FR-24/25, L4/L5, `treasury-virtual-ledger-and-birth-mechanics.json`, `closed-treasury-boundary.json`)
— a **cycle** is a seed→cap event; **compounding within a cycle only, never across** (money resets between
cycles, *knowledge persists*); **rollover-only sweep** removes equity above seed (intraday cap contact does
nothing); the book↔treasury boundary is **closed** — only `sweep | refund | re_seed` cross, a fourth event
fails contract validation; **no automatic physical withdrawals** (sweeps are virtual accounting); the
**kill line** is a floor that flips the book to paper until a cycle-boundary `re_seed`, fixed within a cycle.
This treasury-cycle machinery is not visible in the current qmf-risk FR set (CT-22..32) — it is core node
money-management and belongs to the Phase-2 GitBook baseline; carry it as a Phase-2 design input.

**B2. Refund semantics (deferred, intent preserved).** (old spine Deferred) — refund = protective return
of book capital to Treasury after a blocked/killed **standstill of configurable duration T** (SQS-blocked /
kill-switch stand-down). Dormant in V1 (a refund request refuses-and-journals). Preserve the intent for the
node's money-management design.

**B3. Money-ladder sizing chain + cost-aware Kelly.** (old FR-10, FORM-0002..0006) — sizing as an explicit
chain: equity → runway → **daily loss budget (re-derived at rollover, drains intraday)** → offer per seat →
`take = min(offer, trust-bounded cost-aware Kelly)`. The **cost-aware Kelly with a trust bound** and the
"drains intraday, re-derived at rollover" budget mechanic are concrete design the current PRD's Book-owned
sizing (FR-028) leaves to GitBook/node; worth naming as node design inputs.

**B4. Position-safety cluster — open design questions worth carrying.** (old OQ-2, PE-3/PE-7/PE-8) — four
node-design questions that the old build never closed and the current corpus hasn't either: (a) **stop-out
taxonomy** (does a breakeven exit or a forced-flat count toward the breaker and toward sizing?); (b)
**position fate at boundaries** (flatten-first vs carry at rollover/sweep/re-seed/kill-line/paper; how
unrealized PnL enters the sweep); (c) **dynamic SL/TP belongs in the book grammar with BMS as config
authority**; (d) **`amend_order` as a 5th venue command** clamped to per-symbol minimum stop distance
(cTrader confirmed to support SL/TP amendment incl. server-side trailing). Carry as explicit node-phase
ratification items so they aren't re-discovered.

### C. Phase 2 MIS / model layer — enriches §6 "MIS carries ML instances with training, shadow-rollout, retraining"

**C1. Shadow rollout on the evidence node.** (old AD-20) — candidate labeler/model versions run as
**near-real-time replay over the CAPTURED canonical feed** (identical inputs by construction), off the hot
path; shadow emissions go to their **own prefix + manifest, never to live consumers**; evaluation window =
one full affected-book cycle; **promotion = ratification → live version bump → re-certification cascade,
no data copied**; the same captured substrate serves model training. This is the concrete shape of the
"shadow-rollout, retraining" the current §6 only names.

**C2. Labeler-materialization lane + disjoint source-class namespaces.** (old AD-17, `labeler-materialization-lane.json`)
— a named offline lane runs the *same versioned labeler code* over backfilled history to materialize archive
emissions; **live-recorded vs materialized-backfill emissions occupy DISJOINT partition namespaces**
(a `source_class` key above pair/date/resolution); certificates record **data-source class + input-
availability tier**. This connects directly to the current **GAP-0048 backtesting fidelity taxonomy** —
"live-recorded vs materialized-backfill, labeled at the partition + on the certificate" is a ready-made
fidelity primitive.

**C3. MIS labeler-catalog ratification discipline.** (old AR-21, `labeler-catalog-ratification.json`) —
what each labeler *is* (trained / fitted / rule-based) must be explicitly ratified; the SQS
(snapshot-quality-score) formula and inputs must be authored; **recovered/pre-trained models (Kronos, HMM,
BOCPD, MS-GARCH) carry NO current authority** until an explicit adoption decision; a genuinely new labeler
needs *fresh ratification*, not just a version bump. Good governance scaffolding for the node's model layer.

### D. Data acquisition — enriches FR-017 (Dukascopy) and FR-018 (news calendar)

**D1. Deep-history multi-source strategy.** (old AD-16, spine Stack, `deep-history-acquisition-merge.json`,
`acquisition-scope-ratification.json`) — deep history from **Dukascopy tick + TrueFX (16 majors, tick since
2009) + HistData (M1 + tick)**, with **platform continuity** for the recent window because **platform-only
backfill is rate-capped into unviability**; **≥5 years minimum depth, broadest obtainable forex set**;
pipeline is **download → clean → maintain**, each stage manifested, raw→cleaned linked by derivation;
**Databento has no spot FX**. The current FR-017 names only Dukascopy — TrueFX/HistData and the
platform-continuity-bridge strategy are additive.

**D2. News-calendar multi-source redundancy + compilation invariants.** (old AD-22, `SCN-0008` analog) —
**daily pre-trading-day refresh is a non-negotiable ritual**; **Forex Factory free weekly JSON primary**
(rate-limited 2 downloads / 5 min) + **FMP / Trading Economics / FXStreet** impact-carrying fallbacks behind
**one normalized import**, every import journaled; a failed refresh **falls through the source chain, then
degrades visibly to conservative (fail-closed) blocking**. Two hard invariants: **compilation = currency →
ALL pairs containing that currency**, and **session scoping may only WIDEN a block, never narrow it**
(e.g. EUR/JPY stays blocked through JPY news). **EODHD disqualified** (no impact field); scraping rejected.
Enriches the current pair-scoped-news-windows FR-018 with the source strategy and the widen-never-narrow rule.

### E. Modeling considerations — cross-cutting, may touch QMF / QMB / QML

**E1. Venue / platform / instrument three-axis identity.** (old AD-42, `draft-venue-encodings`) — every
instrument-scoped schema/key carries **`(venue, platform, instrument)` from day one** (FOREX-ONLY values at
V1); encodings are registry-adjacent **ratified data with one owner, minted by ratification only** — no
component invents venue/instrument spellings. **This differs from the current CT-03 opaque `(venue, symbol)`
pair**: the old model separates **venue** (market: forex) from **platform** (cTrader) from the broker-account
behind it (IC Markets / Deriv / Exness). Surface as a modeling question: does QMF need a *platform* axis
distinct from *venue* so a future MT5/dual-platform or multi-broker setup isn't a retrofit? Future venues
enter as **in-system** components behind their own adapters, each designed/coded/ratified externally — never
"agentic-manufactured."

**E2. Attribute inertness at the bot boundary — strengthens QML's two-artifact model.** (old AD-24, AD-25)
— attributes are **write-only from bot code** (declared, never read at runtime); **any attribute a bot's
logic consumes must be part of its spec/config-hash, minting a new `bot_spec_version`** — this prevents a
bot branching on its own declared attributes so its conformance evidence/certificate describes a *different*
bot. The attribute register has an **experimental (observable, unbindable) → ratified (bindable)** lifecycle;
decision logic reads attributes only through an explicit **binding allow-list of (attr_id, version)**. A
subtle, valuable governance mechanism for QML's CT-33 declaration + plain-Python-logic split and its
conformance-as-ticket doctrine.

### F. Phase 3 terminal — enriches PRD §6 "QMX terminal" (currently inferred/assumed)

**F1. Console as constitutionally-bounded control plane.** (old AD-33, §4.13, UX extract) — the console
**commands only the human powers** (resurrection, ratification, review) and **displays everything else**;
it exercises powers **directly against the node**, reads evidence from the evidence home (watermarked,
as-of visible), and **console-offline never affects trading**. Refusal is a **first-class evidence
category**, not an error state. (The old "no CLI, sole surface" clause is dead under DEC-0185; the
powers-bounded-surface shape survives.)

**F2. Click-time server-side revalidation.** (old AD-33, AD-40) — every promotion/ratification **re-executes
its precondition battery server-side against FRESH local state at click time**; **stale evidence never
authorizes anything** (evidence reads carry their as-of/watermark so staleness is visible); a
displayed-eligible state is **never a guarantee** — click-time refusal is always possible. The promotion
crossing is a **trading-node-initiated pull, idempotent by artifact-tuple key** (re-click = no-op). This
sharpens the current human-signed-promotion model (ADR-0015 / SCN-0007) with a concrete anti-stale-evidence
mechanism.

**F3. Promotion evidence panel + human dedup judgment.** (old AD-27) — the promotion click presents an
**evidence panel**: certificate/conformance summary, cohort-correlation observations, **pair/session overlap
with the live roster, and spec/footprint similarity to existing bots** — so the *human* performs the
dedup/correlation judgment V1 defers as an autonomous gate ("deduplication is very important; the forex
entry-model space is finite and hypotheses repeat"). Overlap/similarity **recompute against the fresh local
roster at click time**. A concrete, valuable surface for the terminal's promotion flow.

**F4. Three settings scopes rendered distinctly + registry-config UX invariants.** (old AD-31, FR-38) —
**system settings** (secrets, console-managed, never registry numerics) / **component settings** (registry) /
**instance values** (registry under instance ownership), rendered as three distinct scopes ("settings =
registry + secrets store — a superset, never a synonym"). Registry-config UX rules: non-configurable renders
read-only; **null shows as *unresolved*, never an editable default**; provisional/null values are visibly
distinguishable and some require operator countersign before live; a value like the kill line is not
changeable within an active cycle. Lands the current L38 UI-editability law as a concrete surface.

**F5. Per-bot dossier + automatic placement at intake.** (old AD-13, AD-45) — every artifact about a bot
(spec, backtest/exam results incl. failures, reports, build notes) **attaches to its bot id from system
entry onward, immutable and lineage-linked** — the *per-bot dossier*, with the trading journal as its
"trading view"; a first-class terminal surface. At intake, promoted artifacts **self-route by classification**
(venue/platform/instrument, book type, bot archetype) to schema partition / roster / book assignment;
**nothing enters unplaced — an unplaceable artifact is a veto-class refusal, journaled**.

### G. Cross-cutting engineering standards — enriches §8 NFRs / §9 success + the factory lanes

**G1. Behavior-anchored testing doctrine (ATDD-at-the-story-boundary).** (old NFR-7, `testing-doctrine.md`,
`golden-scenario-harness.json`) — every acceptance test must **name the evidence it protects** (a law,
contract, scenario, refusal, or required journal side-effect); **coverage % is an explicit counter-metric**,
never a substitute for behavior-anchored proof. Golden-fixture rules: **freeze time, forbid network in
unit scope, keep unresolved values visible (never substitute defaults), treat copied worked numbers as
derived checksums not authority, and assert journal side-effects wherever a law requires them**. Richer than
the current NFR-02 quality-gate list; a ready-made testing standard for the factory lanes and code-review.

**G2. No-mock-data doctrine (factory discipline).** (old DECISIONS-LOG, HARD/universal 2026-08-10) —
production-grade only: **no code/spec/enrichment/review agent may invent mock/synthetic/placeholder data**;
missing data/value/dependency/architecture → **notify + fail-closed + log to the ledger, never fabricate**.
Reconcile with the current FR-041: synthetic data is allowed **only** as an explicitly claim-class-labeled
artifact (infra-stress / robustness / logic-smoke), **never as a silent placeholder** for missing production
data. A strong guardrail for autonomous factory agents.

**G3. Money-path + nondeterminism AST scanners — concrete gate donors.** (old AD-39/AD-1/AD-3,
`enforceable-standards.json`) — a working design for the "enforced by gate tooling, not review" clause the
current FR-001/FR-002 assert: a **money-name-fragment list** (money, price, equity, sizing, size, budget,
offer, take, cost, loss, payoff, pnl, notional, margin) × **forbidden AST** (float call / float literal /
float annotation / division on money paths) + an allowed-context allowlist; plus an **ambient-nondeterminism
forbidden-call list** (datetime.now/utcnow, time.time/monotonic/perf_counter, random.\*, secrets.\*,
np.random) with a per-path allowlist. Directly reusable as the money-path / time-injection gate tool.

**G4. Atomic decision+evidence commit + single-writer-per-entity.** (old AD-8) — the decision state change
and its journal append **commit atomically in one transaction** (covers every dual write: door verdict +
veto ledger, mode row + book journal, treasury ledger + boundary event); **every governed entity has exactly
one owning module**, and foreign entities are reached *only through the owner's API*; cross-entity ops
serialize through one owner's transaction. A crisp implementation invariant for QMF's journal + registry
write paths.

**G5. Failure-register discipline + operator-as-product-user.** (old AD-44, `ad-44-failure-register.json`)
— every designed failure mode ships a **failure-register entry**: failure class, detection, auto-recovery/
retry semantics, the visible degraded state, and a **product-user affordance** — *what failed / why / can I
retry / what a retry does* — **written for a user who was not in the design room**, plus its notification
tier. Baseline **~99% autonomy**; the sole operator is treated as a *product user* for failure-surface
rendering. This complements the current typed-refusals (CT-04) with a *rendered-affordance* layer and directly
serves the one-person-operability success lens (§9) — a candidate new NFR.

**G6. Schema-evolution / migration-runner discipline.** (old AD-12, `schema-evolution-discipline.json`) —
**forward-only-by-default** migrations; **globally-unique ascending integer versions**; **never edit,
reorder, or skip an applied migration**; one owning module per table family; migration identity =
(version, owner, class, table_family). The current NFR-06 already carries the *per-contract format-version
ladder keeps old evidence readable* half; this adds the concrete migration-runner rules underneath it.

---

## DEPRECATED / superseded — confirmed dead, do not re-import

- **Six-transition paper model** (birth-in-paper, warm-up-to-live, exam-to-paper) — narrowed away even in
  the old build (AD-28 v2 relocated pre-live paper to the certification side); the current corpus reframes
  this into conformance/promotion. Dead.
- **"No CLI / config-file surface; desktop console only"** — superseded by DEC-0185 (`qmb` CLI is the single
  command-line surface). Only the powers-bounded-console *shape* survives (Phase 3).
- **Backend-node PostgreSQL as the evidence store** — collides with the current "no DB server anywhere in V1"
  (FR-016, NFR-10). Carry the *shape*, drop the engine choice pending QMF-data-store reconciliation.
- **Vocabulary tombstones** — trading-floor metaphor, KSA-under-MIS, crypto-adaptable / separate-system crypto
  framing, genesis/progenitor/DNA/genome, "quantitative" (must be "algorithmic"), "evidence node"/"middle
  node." Dead.
- **Recovered-era mechanics** — global bot pools, slot auctions, DPR/PRS merit ranking/tiers, WF1 and old
  WF-lifecycle mechanics, opinion-weighted sizing, paper-redemption loops, second journal writers, identifier
  recycling, in-place revival. Dead (mine for intent only; already mined above where anything survived).
- **The old FR-1..FR-41 list** — operator-ruled heavily deprecated; NOT carried. The *framing* (constitution,
  authority chain, unattended doctrine, refuse-and-journal, evidence grading) is already in the current corpus.
- **Agentic-side constructs** (trader-agent class, signal lane/journal, bot factory pipeline, morning brief,
  activation records, external-connector two-lens boundary) — deferred to a fresh agentic redesign in the old
  build, and the current corpus explicitly scraps old agentic ideas (QMA = own track, ideation not begun). Do
  not carry as design; note only that the *seam facts* (pull-only datasets, human promotion click, minting-at-
  spec-authoring with permanent ids + parent-linked lineage) were the durable residue.
- **MCP anticipation → no-MCP reversal** — old build reversed to no-MCP (AD-18); current corpus re-allows an
  *optional* MCP door that is never required (FR-046). The old "no MCP" absolute is superseded.

---

## Notes on sources skimmed but not separately carried

- `epics-v2-draft.md` (1726 lines) and `epics.md` — a faithful re-derivation of the same PRD+spine content
  into 10 epics / 100 stories; no new ideas beyond the ADs/FRs above. The epic→build-dependency edges (AR-25:
  MIS-Archive→Exam; QML→Bot; Exam→Book-Template; Template→Scalper; Scalper→BMS; BMS→Treasury/KSA/Data;
  KSA→Adapter) are a useful sequencing reference if/when the node phase is planned.
- `standards/*.json` (43 files) — Story-1.x..5.x ratified implementation standards; each is a concretization
  of an AD already captured (connection manager, MIS fan-out, materialization lane, reconciliation, treasury
  birth, book-type schema, etc.). Named inline above where load-bearing.
- `TRADING-NODE-SHIP-GOAL.md` — confirms the Phase-2 build framing: node runtime, Epics 1–7, **backend + DB
  only, no UI**, real cTrader demo/paper integration, ready to the human-promotion boundary but **not**
  live-money. A useful scoping precedent for how a Phase-2 node run would be bounded.
- `DECISIONS-LOG.md` — orchestration log; the durable carry is G2 (no-mock-data) and the kill-switch recall
  (hedge-fund methodology; news halt ~5–15 min with **symmetric before/after buffers**, session-relevant;
  manual black-swan switches; BMS-originated book-level switches needing correlation analysis) — a Phase-2
  KSA design input, primary source flagged as `Documents/Claude/QMX-discussion`.
- `AGENTS.md` / wiki-doc-pass-report — documentation-method discipline (Observed/Deduced/Proposed/Unresolved
  evidence grading; "never silently replace an unusual rule with a conventional design") already embodied in
  the current documentation-factory process; not separately carried.
