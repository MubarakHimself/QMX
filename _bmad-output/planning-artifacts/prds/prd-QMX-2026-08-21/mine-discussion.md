# Mining extract — QMX-discussion (VERY OLD vault)

Source: `C:/Users/Mubarak/Documents/Claude/QMX-discussion`
Pass: **LIGHT** (operator ruling — this predates everything; agentic material skimmed by title only).
Judged against: `prd-QMX-2026-08-21/prd.md` and the ratified `docs/` corpus.
Date: 2026-08-21.

---

## 1. What this source is

The QMX-discussion vault ("QUANTMIND — Architecture Vault", ~41 specs, ~70k words,
self-dated 2026-04..2026-07) is the **pre-QMF microservices architecture**: a
population of strategy bots competing for a few live capital slots, governed by
deterministic "authorities" and observed by a hierarchy of LLM agents, deployed
across **four node roles** (trading / backend / database / desktop UI).

Its spine is a **contract layer confusingly also named "QML"** — the *shared
contract library* (`BotSpec`, `MarketIntelligenceSnapshot`, `RiskAuthorization`,
`TradeIntent`, `ExecutionDirective`, `TradeLog`, `KillSwitchEvent`, …). This is a
different thing from today's **QML = bot-authoring library**; the name collision
is a trap.

**Overall disposition: ~90% dead or Phase-2-deferred, formally.** The current
corpus already catalogues most of this vault's load-bearing ideas in its
**dead-decisions graveyard** (glossary "Retired or prohibited names";
gap-report dead list). The two July-2026 files in `outputs/`
(`alpha-decay-spec.md`, `sltp-authority-spec.md`, plus `gaps-commentary.md` and
`deterministic-coverage-map.md`) are **already bridge/extraction artifacts** that
re-anchored the vault to the book system — they explicitly say "book rules win",
"TIGHTEN is dead (DEC-0019)", "old CB replaced by breaker-door + leash chain
(DEC-0037)". So most re-anchoring work was already done and largely absorbed.

The genuine yield of a fresh pass is **four small still-valid carries** plus a
confirmation of what is dead.

---

## 2. Carries — still valid post-QMF, NOT already fully in the corpus/PRD

### C1. Alpha-decay sensing — a candidate *signal catalog* for the deferred design
**Status in corpus:** the *concept* and its *guardrails* are ratified, but the
*mechanism* is deliberately deferred and has **no signal list** anywhere.
- L26 / DEC-0092: "Future alpha-decay and benchmark mathematics must be designed
  from current definitions and must not be reconstructed from unrecoverable
  legacy formulas."
- SCN-0008: "the active protection-window set enters the decay cohort key, so a
  news-heavy period is never compared against a quiet one and read as alpha
  decay" + "decay sensing keeps its data points" (window is a veto-path refusal).
- SCN-0006: "a silent paper outage corrupts every decay verdict computed after it."
- The alpha-decay-spec itself confirms: *"the new GitBook core does not document
  alpha decay at all; this is the only written record of the mechanism"* and *"no
  formula, weights, lookback lengths, or numeric thresholds… whoever implements
  this defines the actual math."*

**Carry:** the four candidate **decay signal classes** the old WF3 named, as an
input catalog for the future alpha-decay sitting (not the math):
1. Rolling breaker/leash-event fire density (re-anchor: old `cb_hits_in_window` →
   new **breaker-door / leash-event frequency**; GAP-0012 "certified leash-event
   frequencies" is its natural home).
2. **MAE/MFE drift** — shift over time in max-adverse / max-favorable excursion
   distributions (fragility detector: high win-rate but MAE creeping toward the
   stop → one slippage event kills it).
3. Drawdown decomposition (old vault bounded this to Riskfolio-Lib in the
   dead-zone only; sub-metrics were never specified).
4. Regime/session-conditioned performance drift.

**Re-anchor guardrails (must ride with the carry):** measured quantities +
formula-registry derivations (FORM-xxxx) with golden scenarios — **never a
declared-weight composite score**, which would brush the no-composite-score law
(FR-034 / CT-32) and DEC-0018. Decay **informs, never disposes**: it feeds the
operator's L16 sunset review and ENH proposals (L17), and flows through
books/BMS, never a hot-path actor.
**PRD target:** §6 Phase-2 trading-node outline + a future-sitting open item
(alongside GAP-0048/0049). Not a Phase-1 FR.

### C2. Amendment idempotency threshold (venue / exit order path)
**Status in corpus:** not present in CT-29 (exits) or CT-19 (venue commands).
**Carry (from sltp-authority-spec §5):** emit an SL/TP **amend only if
`|proposed − current_confirmed| > AMENDMENT_THRESHOLD_PIPS`** — a small
robustness rule that suppresses tick-storm duplicate amendments and stacked
broker-queue conflicts. Fits cleanly under the four-outcome venue law and the
Book-owned risk-monotonic exit path; the threshold is a UI-editable configurable
(L38). Related still-valid mechanic from the same spec: on restart, **reconstruct
from the write-ahead log AND reconcile against the broker's open-position feed
before resuming amendments** — this is already the spirit of the UNKNOWN /
explicit-reconciliation law (CT-19/CT-20, SCN-0005), so only the amendment-dedup
threshold is genuinely additive.
**PRD target:** §6 Phase-2 node order-path outline; candidate detail for
qmf-venue / CT-29 when the node phase is planned.

### C3. Sequence the cTrader feasibility spike as one of the FIRST factory builds
**Status in corpus:** FR-022 (capabilities via verify-or-refuse) and FR-026
(cTrader first adapter) state the *what*; nothing states the *ordering risk*.
**Carry (from gaps-commentary, GAP-0005 "LOAD-BEARING (empirical)"):** venue
feasibility *cannot be designed on paper* — it can invalidate upstream
assumptions (feasibility clamp, lot rounding/min-lot, capability discovery
shape). So the cTrader Open-API verify-or-refuse probe should be sequenced
**among the earliest factory tasks**, before deep work assumes a capability set.
This is a process/sequencing note for the epics-and-stories + factory lane, not a
new FR.
**PRD target:** informs the delivery-sequence narrative (§2) and the
epics-and-stories ordering; could be a one-line risk in §10.

### C4. One observability substrate for both the deterministic platform and (later) the agents
**Status in corpus:** NFR-10 says "monitoring and evaluation built in, not bolted
on"; the DevOps success lens (§9) is primary — but nothing says the *same*
substrate should serve the future agentic layer.
**Carry (from gaps-commentary, GAP-0009):** stand up **one** tracing/metrics/logs
substrate that serves QMF/QMB now and QMA later, rather than two stacks. Stating
this as a Phase-1 design constraint prevents rebuilding observability for the
Phase-3 agents. Partial overlap with NFR-10 — this sharpens it with the
"serve-both-layers" constraint.
**PRD target:** NFR-10 refinement / §9 DevOps lens.

*(Marginal, likely already covered — recorded for completeness, not pushed:* a
curated **broker-reference dataset** per venue — lot steps, commission schedules,
spread characteristics, connectivity notes — feeding fill/fees (FR-044) and
capability discovery (FR-022). Largely subsumed by CT-18 verify-or-refuse + the
variables registry; the only novel framing is "keep it as a durable versioned
reference," which the format-version ladders already enable.)*

---

## 3. Confirmed already-covered (not carries — do not re-import)

- **Backtest parity + reproducibility.** Old "parity principle" (every live
  authority participates in replay; only data source + execution layer
  substituted) = today's **one run loop serves backtest/replay/live, never
  forked** (FR-036). Reproducibility via `config_hash + seed + data_snapshot_id`
  = **config fingerprint is the run id and ledger key** (FR-036, SCN-0012).
- **Robustness battery.** Old walk-forward + Monte-Carlo(N=1000) + PBO/CSCV(S=16)
  = FR-040 (MC-1000, PBO, CSCV S=16) + the rule-significance gate. The corpus
  chose CSCV/PBO as the governance battery; **walk-forward windowing** (expanding
  vs rolling) is the one sub-item worth a coverage check against spec-optimization
  (FR-039 says train/test/locked-validation) — likely a conscious fold into CSCV,
  not a gap.
- **MAE/MFE.** Already in QMB `spec-reports.md` (metric set + an open note to
  confirm the fill/position record captures enough to compute them). CT-32 yaml
  doesn't yet enumerate them — a known open detail already tracked in the QMB
  spec, not a discovery.
- **Fill/slippage/fee simulator** (spread, slippage dist, commission, partial-fill
  / rejection probabilities) = FR-044, with fidelity taint until GAP-0048.
- **Fail-safe-not-fail-open + conservative-on-missing-signal** = fail-closed news
  windows (FR-033, SCN-0008) and refusals-as-data.
- **Data-quality tagging** (INCOMPLETE / ORPHANED / SENSOR_FAILED / MODE_UNRESOLVED)
  = the typed-refusal + taint model (FR-004, FR-044).
- **Append-only lineage / never-delete-deprecated** = FR-007 (typed lineage edges)
  + the two version ladders (FR-005; DEC-0103).
- **Symbol/currency-scoped news blocking** = CT-31 control windows, per-instrument
  currency-exposure records (FR-033, SCN-0008).
- **System-owned (not bot-owned) exits** = Book-owned, risk-monotonic exits;
  bots may only propose risk-reducing exits (FR-032, CT-29, L39).
- **Bots are consumers, agents propose / deterministic services dispose** = the
  authority chain bot→Book→BMS→operator and the unattended doctrine (§3; L17).
- **Knowledge base for humans + agents** (QuantMindWiki: versioned entries,
  supersedes/status, human-approval write gate, never-delete) = the `docs/`
  corpus produced by the documentation-factory (append-only, ratification gate).

---

## 4. Deprecated — notable old ideas confirmed dead / superseded

- **4-node microservices topology** (trading/backend/database nodes + DB servers,
  hot-path/cold-path split, mutual-TLS cross-node) → single-machine, **no DB
  server**, `uv add` install, qmf-data store seam (NFR-10, FR-016).
- **Composite performance score + T1/T2/T3 tiers gating money** → **no composite
  score gates money** (FR-034, CT-32); benching is a read-time fold.
- **2-strike circuit breaker with automatic live→demo demotion** → breaker-door +
  leash chain (DEC-0037); **no auto-demotion**; promotion is human-signed only
  (FR-009).
- **Paper-Trading Demotion Service** (automatic account-mode flip) → paper is a
  **Book-level standing evidence state via a dated binding-epoch change**
  (FR-029, CT-24, SCN-0006) — operator-driven, not automatic.
- **5-level kill switch GREEN/YELLOW/ORANGE/RED/BLACK with auto-flatten & TIGHTEN**
  → escalate-only KSA + kill-switch(global)/kill-line(per-Book floor) (FR-033,
  CT-30/31); platform **never auto-flattens, auto-retries, or self-clears** (L35,
  FR-023); TIGHTEN half-size **explicitly dead** (DEC-0019).
- **6-clamp half-Kelly, 9-multiplier canonical sizing formula** → CT-23 sizing (R
  is one relationship with three typed faces, frozen at admission; the **Book owns
  sizing**; GitBook is the authoritative risk/sizing baseline). The old vault had
  *already deferred* its own canonical-formula redesign.
- **Old "QML shared contract library"** name/role → filled by qmf-core + the CT
  contracts; the name QML is reused for **bot-authoring**. The **`.qml` DSL file
  is dead** — plain-Python bots stay first-class (FR-047).
- **ArchetypeSpec constraint powers + BotSpec.exit_logic** → retired (glossary
  graveyard); constraining is the Book's job; exit policy lives in the Book's
  `exit_policy` per strategy family (DEC-0176/0179/0173).
- **Whole agentic system** (four departments + Floor Manager + Copilot, WF1/WF2/WF3
  variant/mutation/pool-cleaning pipelines, inter-department mail, opinion nodes,
  video-ingest, QML Compiler/Validator agent-boundary, identity system) →
  **scrapped**; QMA is its own research track, ideation not begun (§6). Do not
  carry old agentic requirements.
- **QuantMindWiki as a RAG / semantic-search agent-grounding vault** (embeddings,
  `read_knowledge_vault`, propose-vault-entry, ingestion pipeline) → the
  grounding role is served by the `docs/` corpus; a RAG retrieval API is
  agentic-phase (deferred/scrapped with the agentic system).
- **Kronos external learned-sequence sensor + HMM / BOCPD / MS-GARCH regime
  sensors + ensemble voter + MarketIntelligenceSnapshot** → MIS is **Phase-2
  trading-node** territory (deferred); the specific model stack is not ratified.
  Old vault itself already fenced Kronos as information-only, never a risk
  multiplier — consistent with today's "measurement publishes, never acts."
- **`fee_adjusted_RR < 1.1` hard-block** and **realized-R:R (rolling 20–50) as the
  Kelly input** → these were already *deferred "V2" notes* in the old vault, tied
  to the dead Kelly formula; superseded by CT-23's admission model
  (declared full-loss price required or admission refuses).
- **Conviction-based slot substitution / 3-slot auction / equity-band slot caps**
  → slot-competition vocabulary superseded by books/seats/cycles.
