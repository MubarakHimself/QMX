# Wiki mining — extract A (first-half, sorted ascending)

**Source:** `C:/Users/Mubarak/Documents/QMX/wiki` — the later pre-QMF wiki ("took my
sweet time with it"). Files mined: the first 46 of 93 sorted paths (indices
0..45); 2 were mermaid JS assets (skipped), 44 content files read.

**Lens:** platform-level features / requirements / product framing that survive
QMF and are NOT already in the `docs/` corpus or the 2026-08-21 PRD — with a bias
to the platform ABOVE the framework (terminal/UI surfaces, platform integration,
operator workflows). Agentic depth de-scoped to boundary rulings only.

**Standing caveat.** This wiki predates QMF. Its Book/BMS/Treasury/adapter/KSA/
data-class/examination/lineage/QML component specs are almost entirely SUPERSEDED
by QMF's seven packages (qmf-core/registry/data/indicators/structure/venue/risk),
QMB, and QML as ratified in `docs/`. I did not re-mine those; the PRD already
binds them at capability level (FR-001..050). Everything below is either (a) a
platform surface ABOVE the framework that QMF deliberately does not cover, or
(b) a durable operator/integration pattern the PRD's future-phase outlines
gesture at but do not pin down.

---

## Part 1 — Carries (durable, post-QMF, not in corpus/PRD)

### C1. A three-tier deployment topology, with a distinct always-on BACKEND NODE

The wiki's ratified V1 deployment was **three deterministic nodes**, not two:

1. **Trading node** — one OS process: bots, Books, BMS write side, MIS-Live, KSA,
   adapter + connection manager, and the Powers API. The time-sensitive hot path.
2. **Backend node** — the always-on durable evidence home. Enumerated process set:
   one Python backend service, one standing PostgreSQL server, and heavy-compute
   job runners under one supervisor. It owns: sync ingestion, read-side replicas,
   Reporting/metrics aggregation, the Parquet archive + captured canonical feed,
   the **agent-facing dataset catalog**, **shadow lanes**, and the heavy analytical
   pipeline (in wiki terms, the examination pipeline host).
3. **Console** — desktop UI only.

The PRD names the trading node (Phase 2) and the terminal (Phase 3) but has **no
separate backend-node tier**. Post-QMF the backend node is not about
re-introducing a DB server (qmf-data is DB-serverless by ruling) — it is the
durable-evidence + heavy-analytics + agent-dataset + ML-shadow tier that the
node phase's own outline implicitly needs ("ML training, shadow rollouts,
retraining under MIS"). Worth carrying as an explicit deployment tier so the
node phase does not discover it late. The London-cloud-on-Linux target with
laptop/WSL2 as bootstrap parity is the wiki's stated deployment posture and lines
up with the PRD's tier-1 OS list.

> Note the wiki's own hedge: "This does not imply that each box is a separately
> deployed service." The three-tier split is a placement/authority boundary, not
> a mandate for network services. That nuance survives.

### C2. The trading hot path must never block on the backend (resilience invariant)

A hard, durable platform-integration rule the corpus/PRD does not state:

- A backend-node outage or cold-storage failure **does not block the trading hot
  path**. Only disk physics fail-closes the trading node.
- **Verify-before-purge:** the trading node retains its data until the backend has
  durably persisted AND content-verified it; trading-node purge never passes that
  frontier.
- **One-way sync** (trading → backend), watermarked, idempotent, resumable.
  "One-way binds authority, not liveness": the only reverse crossing is the
  click-gated promotion pull (see C3). Recovery after a backend restore/verify
  failure is a **backend-initiated re-request that carries only durable watermarks
  — never payload data flowing backward**.

qmf-data already gives append-only evidence + backup + verify primitives (FR-011,
FR-014), but this is the *cross-node* resilience shape layered on top. Directly
serves the PRD's now-primary DevOps success lens and NFR-10 one-person operability.

### C3. Powers API — the operator's governed action surface, with a stale-evidence guard

The console reaches the trading node through exactly **two channels**: an evidence
read channel and a **Powers API** action channel. Powers exposes exactly:

- **A1 resurrection** (the only de-escalation authority for global protection),
- **ratification / promotion**,
- **Sunday-review actions**.

The load-bearing, durable safety property: **the console never authorizes through
stale backend evidence — click-time preconditions rerun server-side on the trading
node.** Promotion specifically is a **trading-node-initiated PULL, click-gated**
(the operator's click triggers the node to pull, then places the unit in an
`ADMITTED` state with no intents/no ledger; live activation lands at a later
activation boundary). This is a concrete terminal capability + invariant the
PRD's terminal outline (§6) and promotion journey (SCN-0007/FR-009) gesture at
but never pin: promotion is not the console writing "go-live" into a database; it
is a minimal, revalidated-at-the-node pull the operator's single click gates.

### C4. Notification System as a first-class operator surface (event classes ratified, delivery deferred)

An operator-facing delivery boundary derived from journals, with a stable spine:

- **Ratified real-notification event classes:** sweep, re_seed, refund, KSA/
  kill-switch, and **supervision fail-closed**. Everything else is console
  evidence / UI log, not a push.
- **Invariant:** notifications must NEVER create an intraday human-judgment loop,
  and the channel is never a permission path back into live trading; the component
  cannot override protection and must not invent its own severity table.
- Interim tiers P1–P4 carried on the candidate; final tiering deferred.
- **Deferred delivery design (was GAP-0002):** channel selection, quiet hours,
  credential handling, retry, deduplication, and paper-book digest policy.

The PRD's unattended doctrine (§3) cites the "no intraday decision loop" constraint
but there is **no notification capability outline anywhere**. This is a real
terminal/node-phase surface with a ratified event set already in hand — cheap to
carry, and the "supervision fail-closed" trigger is a genuinely load-bearing
operability signal.

### C5. Prometheus/Grafana as an external, NON-AUTHORITATIVE monitoring plane

The wiki repeatedly names an **external Prometheus/Grafana monitoring substrate**
that is explicitly non-authoritative — a monitoring/observability plane that never
becomes a control or authority path. This is the concrete substrate behind the
PRD's "monitoring and evaluation are built in, not bolted on" (NFR-10) and the
DevOps success lens (§9), which currently name no substrate. Carrying it gives the
node/terminal phases a ratified integration target with the right guardrail baked
in ("publish evidence into the monitoring plane without acquiring authority").

### C6. Agentic boundary: pull-only curated datasets, never live-service callers (AD-18)

The wiki's governance ruling for the (out-of-scope) agentic section: agents are
**not service callers**. Their entire interface is **pull-only access to curated
datasets stored on the backend node** (the agent-facing dataset catalog); no MCP
and no live-service surfaces are exposed to the agentic section. The current PRD
frames QMA as operating through "typed machine-readable doors (qmb CLI, Python
API, optional MCP)". These are not contradictory but they ARE different postures
worth reconciling: the wiki's stance is a hard *data-egress* boundary (curated,
pull-only, backend-hosted, no live authority), which is a cleaner starting
governance stance for QMA than "MCP door optional." Carry as a boundary ruling for
the QMA track, not as agentic depth.

### C7. Read-model service family: publish-never-act analytics the terminal consumes

The recovered "proposed service boundaries" define a family of **read-only** models
that sense/explain without acquiring authority, each with explicit concurrency/
usage budgets and refusals-as-evidence:

- **Records Read API** — query journals, veto evidence, cycle events without write
  authority.
- **Replay** read model — deterministic, profile-aware replays returning evidence
  packs.
- **Performance Analytics** read model — explains journal-derived performance and
  footprint drift.
- **Decay Sensing** read model — compares live vs. certified/expected footprint.
- **Archive access** read model — typed historical snapshot/replay reads.

QMF gives the primitives (CT-32 performance "publishes and never acts", QMB's
CT-32 result artifact, journals/lineage). What's durable and NOT in the corpus is
the *platform framing*: a **Records/journal Read API** and analytics read models as
the terminal's data-plane, each budgeted and authority-free. This is the natural
back-end for the PRD's terminal "browsing evidence/journals/lineage" bullet — it
tells you the shape of what the terminal reads.

### C8. Alpha-decay / footprint-drift sensing as evidence-only review input

The strongest durable *idea* rescued from the dead DPR/PRS machinery: define decay
as **sustained, measured divergence between live behavior and the certified/
backtested footprint** (live-vs-expected mean loss, fire-rate-band violations,
regime-conditional EV drift, MAE/MFE drift, leash/veto-event frequency), plus
measured **proximity to a charter-death condition**. Strictly **read-only**:
it senses and explains, feeding operator review; it never sizes, ranks for capital,
or triggers a transition — Books/BMS/operator remain the only disposing authorities.
The corpus has performance measurement (FR-034, CT-32) but no live-vs-expected
*drift/decay monitoring* concept. Carry as a node/terminal-phase analytics
capability, agentic auto-action explicitly de-scoped.

### C9. Named operator review rituals: Sunday review and sunset review

The wiki gives the periodic-review cadence concrete names and inputs: a **Sunday
review** (weekly operator ritual, a Powers-API action) and a **sunset review**
(retirement decision), both fed by the read-model/decay evidence above. The PRD's
vision cites "periodic review" abstractly (§1, §3) and the operator-journeys list
(§4) has no review ritual. Carrying the named rituals + their evidence inputs
sharpens the operator-workflow picture for the terminal.

### C10. Console-configured, journaled account bindings (system-settings scope)

**Book-to-account assignment** is operator-configured through the console, lives in
**system-settings scope**, and is **mutable and journaled**. A future multi-account
/multi-platform load balancer attaches at the connection-manager boundary (not V1).
This is a concrete terminal configuration surface that lands the L38 UI-editability
law on a specific object (Book↔account binding), and it names the future scaling
seam. Complements FR-035/NFR-07 with an actual config object.

### C11. Node-phase operational mechanics worth pre-recording

Concrete Phase-2 mechanics the node outline (§6) will need and the wiki already
pins down:

- **Paired live+demo account bindings for paper fills:** each live account binding
  carries a paired demo binding; paper-phase fills route to the demo binding while
  the bot judges the same pinned canonical feed as live. (A venue-integration
  mechanic for the corpus's paper-as-evidence-state, FR-029.)
- **Daily pre-trading-day calendar-refresh ritual:** normalized multi-source
  import, every import journaled, degrades **visibly and conservatively** —
  unknown high-impact coverage fails to a block, never silently opens. (Operational
  ritual behind the news-window feed, FR-018/FR-033.)
- **KSA quiesce/drain on protection transitions:** on a KSA transition the
  connection manager quiesces affected Book sequencers and drains every connection
  for the account before enforcement counts as complete. (A concrete
  ordering/enforcement rule for the escalate-only global protection, FR-033.)
- **MIS candidate-labeler shadow lanes on the backend:** new sensor/labeler
  versions run in shadow over the captured canonical feed; promotion = ratification
  + recertification. (The concrete home for the node outline's "shadow-rollout,
  retraining cycles.")
- **Fire-and-reconcile order path:** confirmed fills are asynchronous; the order
  path is fire-and-reconcile on execution events, with reconnect fetching missed
  deals/positions since the last-seen execution event and reporting healthy only
  after recovery. (Aligns with and adds operational texture to qmf-venue's
  four-outcome/UNKNOWN law, FR-023/024.)

---

## Part 2 — Superseded / dead (confirmed, do NOT carry)

These appear in the mined files and are explicitly ruled out or fully absorbed;
listed so the PRD chain does not re-import them:

- **DPR/PRS merit scoring, T1/T2/T3 tiers, capital slots, slot auctions, global
  bot pools, intracycle merit reallocation, opinion-weighted sizing** — DEAD;
  conflict with Book sovereignty, formula-owned sizing, and the no-redistribution
  rule. (Only the read-only *measurement* patterns survive, → C8.)
- **WF1/WF2/WF3 lifecycle states** (`POST_WF2`, `PAPER_TRADING`, `LIVE(probation)`,
  `LIVE(full)`, `DEMOTED`, `PAUSED`, `RETIRED`, paper-to-live redemption loop) —
  DEAD; replaced by registry/registration + Book admission + Treasury cycles +
  paper state. (Superseded by qmf-registry + qmf-risk.)
- **`TIGHTEN` KSA level and "trade half-size through bad conditions"** — rejected
  designs; never revive.
- **Examination Engine as a book-admission certifier** (regime EV / cohort-
  correlation / PBO-gated certificates authorizing Book seats) — superseded:
  verification is now QMB backtesting + QML technical-never-performance conformance
  (FR-036..046, FR-048). The old exam registry constants (6mo IS / 1mo OOS / 200
  OOS trades / 0.15R floor / 1000 MC / PBO 0.25/0.50) are legacy scalper numbers,
  not corpus authority.
- **MIS as a standalone live service (MIS-Live/MIS-Archive)** — deferred per
  ADR-0011; the node phase carries only "MIS publication." Do not resurrect as a
  V1 platform component.
- **Riskfolio as any kind of authority** — was only ever dead-zone drawdown
  analysis; a donor tool reference at most.
- **EAV / sparse attribute-bag as a filter surface** — forbidden; typed core
  fields are the legal filter surface (aligns with qmf conventions).
- **`.qml` DSL revival** — not in V1 (matches ADR-0018 / FR-047).
- **The old `amend_order` / SL-TP amendment contract and its close-authority
  priority model** — was an open pre-QMF gap; superseded by qmf-venue's five
  command kinds + qmf-risk Book-owned risk-monotonic exits (FR-023, FR-032). The
  PRD already lists `close_partial` out of scope (§7).
- **Postgres/SQLite/CDC-replica/AD-12 contention-swap storage architecture** —
  superseded by qmf-data's DB-serverless store seam over swappable local engines
  (FR-016). The *cross-node evidence-durability* idea survives (→ C2); the specific
  Postgres topology does not.
- **CT-SYNC-01 field schemas, AD-41 stream register, hot_retention_days/
  sync_interval nulls** — pre-QMF open surfaces; only the one-way/verify-before-
  purge *shape* is durable (→ C2), not the unratified field work.

---

## Part 3 — Notes for the PRD chain

- The heaviest concentration of NEW value is the **platform tier above QMF**: an
  explicit backend-node deployment tier (C1) + hot-path-never-blocks-backend
  resilience (C2), the **Powers API two-channel console with the stale-evidence
  guard** (C3), the **Notification System** with a ratified event set (C4), and a
  named **monitoring plane** (C5). These sharpen PRD §2 (phase/composition table),
  §6 (node Phase 2 + terminal Phase 3 outlines), and §8–§9 (NFR-10 + DevOps lens).
- The **read-model family + Records Read API** (C7) is the concrete data-plane
  behind the terminal's "browse evidence/journals/lineage" bullet — it belongs in
  the Phase-3 terminal outline as the shape of what the terminal reads.
- **Decay/footprint-drift sensing** (C8) and the **named review rituals** (C9) are
  the two operator-workflow ideas most worth rescuing from the otherwise-dead
  analytics layer — both strictly evidence-only, both feeding the operator's
  periodic review.
- Everything in Part 2 is confirmed dead/absorbed; the value there is negative
  (stop the chain re-importing it), not additive.
