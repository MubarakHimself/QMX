# Code inventory — Trading Node (COMP-QMN / `qmn`) boundary for strategy experimentation

Read-only architecture inventory of `qmn` on `integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`.
Planning checkout stays off product branches; every code claim is `git show integration:…`.
Evidence levels: `documented-design` | `source-inspected`. Classification: `reuse | connect | extend | new | undecided`.

---

## Compact table

| # | Question | Classification | Evidence | One-line answer |
|---|---|---|---|---|
| 1 | Node paper vs research paper-validation vs QMA forbidden paper | `reuse` (node paper) / `reuse` (QMB research) / `reuse` (QMA deny) | source-inspected + documented-design | Node paper = Book-level demo routing + soak/demotion only; research paper = QMB pre-promotion; QMA has **no** execution tool at any role including paper |
| 2 | How node reuses QMB `run_slice` | `reuse` | source-inspected | `qmn.loop.CommandStreamLoop` imports and calls `qmb.runloop.run_slice` unforked behind a recording accumulator |
| 3 | Doors UI/research may read vs powers | `reuse` | source-inspected | Evidence HTTP is publish-never-act (`/status|/health|/projections|/config/explain|/metrics|/failures/*`); powers is the closed unix-socket act channel under `SO_PEERCRED` |
| 4 | What experimentation must NEVER grow on the node | `reuse` (refusals already coded) | source-inspected + documented-design | Per-bot paper/warm-up/ramp; QMB ungoverned tunnel seats; QMA execution; forked loop; in-process governed replay; sandbox→live without human hub publish + promotion |
| 5 | Candidate promotion path QMB/QMA → node | `reuse` (path coded) / `connect` (UI/research producers) | source-inspected + documented-design | Content-addressed hub inbox → human `hub_publish` → click `promotion_sign` + silent battery → ADMITTED → separate next-day `activation` |

---

## 1. Node paper mode vs research paper-validation vs QMA forbidden paper execution

### Node paper (`qmn.paper`) — Book-level, demo-routed, not a research lane

**Law (DEC-0261):** paper-before-promotion happens **OUTSIDE** the node; the node grants **no** per-bot warm-up, probation, ramp, or paper lane. Source-inspected refusals encode that vocabulary:

- `FORBIDDEN_PER_BOT_PAPER_SURFACES` = `{per-bot-warm-up, probation, ramp, paper-namespace, paper-performance-gate, bot-paper-twin, book-paper-twin, per-bot-paper-lane}` — `git show integration:qmn/src/qmn/paper/lane.py` (module docstring; `FORBIDDEN_PER_BOT_PAPER_SURFACES`; `refuse_per_bot_paper_lane`; `inspect_bot_node_journey`).
- Sole post-activation paper route: `POST_ACTIVATION_PAPER_ROUTE = "bms-book-protective-demotion"` (`lane.py`).

**What node paper *is* (two semantics only):**

1. **First-deployment / soak window** — whole system on paired **cTrader demo**, Book routing PAPER, live connection sensing-only (`git show integration:qmn/src/qmn/paper/first_deployment.py`; `docs/components/trading-node.md:172-176`; ADR-0021 / DEC-0264 honest FX paper).
2. **BMS/Book protective demotion / operator paper flip** — CT-24 Book-mode PAPER routing to exactly one paired demo target (`role=demo`, `world=live`); never a Bot/Book twin (`git show integration:qmn/src/qmn/paper/routing.py`, `transition.py`, `demotion.py`).

**Role collapse (important naming):** AD-9 roles include `paper-validation` and `paper-benched`, but **V1 node paper deliberately does not use them**. Node paper uses `NODE_PAPER_ACCOUNT_ROLE = AccountRole.DEMO` and `NODE_PAPER_WORLD = World.LIVE` only; finer roles are told apart by **routing reason**, not namespace (`routing.py` module docstring + `require_demo_paper_target`; `trading-node.md:173`; NODE spine TN-9).

CONNECT (ADR-0021 / DEC-0264) makes FX paper **honest**: same live `VenueClientPort`, vendor demo host, submit encode + position/balance read-back — not sensing-only, not a local matcher, not a twin.

Classification: **`reuse`** existing `qmn.paper` + `qmf.risk.paper` for node Book paper. Evidence: `source-inspected` + `documented-design`.

### Research paper-validation — QMB / research lanes, pre-promotion

Corpus bot journey: hypothesis → QMB backtest/iterate → **paper-traded with QMB and research lanes** → human promotion. All of that is **before** promotion and **outside** the node (`docs/changelog.md` DEC-0261 bot-journey; `docs/AGENTS.md` hard rule; `docs/components/qmb.md` pre-promotion journey; ADR-0019 Consequences).

QMB remains the experimentation host / CLI; its `run()` / `run_slice` world is replay-shaped; it **never** imports `qmf-venue` (ADR-0017; ADR-0019 option 3 rejected). QMB keeps the **ungoverned Python-bot tunnel** for research; the node **refuses** that tunnel for seats (`git show integration:qmn/src/qmn/seats/admission.py` — `UNGOVERNED_TUNNEL_NAMES`, `refuse_ungoverned_tunnel_seat`, `UNGOVERNED_EVIDENCE_KINDS` includes `qmb-ungoverned` / `research` / `tunnel`).

Node **replay** is a separate diagnostic spawn: unledgered, never gates admission/promotion (`git show integration:qmn/src/qmn/replay/session.py` — `refuse_admission_gate`, `refuse_in_node_process`; `docs/components/qmb.md` node-replay note). Governed pre-promotion evidence stays QMB CT-32 / ledger, not node replay.

Classification: **`reuse`** COMP-QMB for research paper-validation. Do **not** grow a second research paper executor on COMP-QMN. Evidence: `documented-design` + `source-inspected` (seat/replay refusals).

### QMA — paper execution is forbidden (money-path barrier)

QMA's only money-path output is a **candidate artifact a human promotes**. Rejected option: trading-desk execution tool, **"paper only" included** (ADR-0020; DEC-0341 / DEC-0375 dead). No execution tool at any account role; act-level deny-list; no `qmf-venue` import; placement/registration refuse environments that could reach the trading node (ADR-0020; `docs/components/qma-core.md` money-path / `ProhibitedMoneyPathTool`).

Classification: **`reuse`** the QMA deny-list; never `connect` QMA to node order path. Evidence: `documented-design`.

### Distinction summary

| Surface | Who | Venue money? | Authorizes live? |
|---|---|---|---|
| QMB / research paper-validation | COMP-QMB (+ research) | No `qmf-venue`; replay/research evidence | Never (replay cannot gate live) |
| QMA | COMP-QMA-* | Forbidden at any role incl. paper | Never — candidates only |
| Node Book paper | COMP-QMN | Yes — paired **demo** via live port (`world=live`, `role=demo`) | Never — machinery proof / protective route only |
| Node live | COMP-QMN | Yes — live account | Only after human promotion + next-day activation |

---

## 2. How the node reuses QMB `run_slice`

**Mechanism (source-inspected):**

- Package: `qmn/src/qmn/loop/` — docstring: unforked QMB `run_slice` behind recording accumulator (TN-5).
- `CommandStreamLoop` (`loop/driver.py`) imports `run_slice`, `SliceHandler`, `StreamSet`, `SUBPHASES`, forming-bar constants from `qmb.runloop`.
- `PINNED_SUBPHASES = SUBPHASES` — six-phase order preserved verbatim.
- On frontier close: accumulator `pull_foldable()` → build `SliceObservation`s → **`outcome = run_slice(...)`** → commit `InterpretationCursor` only after success.
- Docstring law: *"Backtest, replay, and live differ only in which clock and VenueClientPort the composition root binds; this driver always calls `run_slice` and never a second loop implementation (DEC-0190)."*

**Surround:**

- `RecordingAccumulator` is the single first writer: record via CT-15 intake + journal **before** fold (`loop/accumulator.py`; TN-5 / DEC-0190).
- One `CommandStreamLoop` per `(VenueId, account)` command stream.
- Live clock + live `VenueClientPort` bound at node composition root; QMB stays pure and venue-free.

Classification: **`reuse`** QMB B-2 loop as-is; node adds **`connect`**/`extend` only at the accumulator + venue/clock binding edge. Evidence: `source-inspected` (`git show integration:qmn/src/qmn/loop/driver.py`, `accumulator.py`, `__init__.py`); `documented-design` (`trading-node.md` TN-5; ADR-0019; NODE spine TN-5).

---

## 3. Doors the UI / research tools may read vs powers channel

**Closed three-door set; no CLI door; no agent/MCP door in V1** (`git show integration:qmn/src/qmn/doors/__init__.py`, `parity.py` — `HAS_OPERATOR_CLI_DOOR = False`, `CLI_IN_DOOR_SET = False`, `AGENT_MCP_IN_DOOR_SET = False`; DEC-0211 / TN-17).

### Evidence channel — what UI / research **may read**

- Transport: localhost HTTP, bind `127.0.0.1`, **publish-never-act**; only `GET` (`doors/http/evidence.py`).
- Routes: `/status`, `/health`, `/projections`, `/config/explain`, `/metrics`, plus `/failures/{id}` (`EVIDENCE_ROUTES` + failure path).
- Library capabilities: `read_status`, `read_health`, `read_projections`, `read_config_explanation`, `read_failure_detail`, `read_metrics` (`doors/library.py` `EVIDENCE_CAPABILITIES`).
- Desktop UI connectivity/latency panel is defined to read `/health` and `qmn_` metrics **through this channel** (DEC-0261; ADR-0019).
- Ops / research consumers of node state use the same read surface; mutations are refused at the door.

### Powers channel — human/ops **acts**, not a research playground

- Transport: unix socket `/run/qmn/powers.sock`, `SO_PEERCRED` (`doors/http/powers.py`).
- Closed list (`doors/catalog.py`):
  - **Ops-allowed:** `notify_test`, `restore_drill_run`, `config_validate`, `hub_publish`.
  - **Operator-only (refused to ops at transport):** `resurrect`, `resume`, `de_escalate`, `resolve_unknown`, `flatten`, `kill_switch_escalate`, `paper_flip`, `paper_epoch_reset`, `promotion_sign`, `activation`, `config_version_activate`, `seat_reinstate`, `state_carry`, `carries_ledger`, `continues_performance`, `value_status_countersign`, `sealed_period_final_look`, `settings_edit`, `secrets_is_set`, `attestation`, `countersign`.
- Agent/machine/service signers refused; peer credential overrides claimed signer (`authorize_powers_call`).
- `just node-…` recipes are ops toolkit over the ops principal — never trading/promotion acts (NODE spine TN-17).

### In-process Python API

Same library functions as evidence/powers adaptations; parity is derived (`doors/parity.py`). Suitable for in-process hosts; still not a research experiment runner.

Classification: **`reuse`** three doors. UI/research **read evidence**; only human/ops **enact powers**. Evidence: `source-inspected`.

---

## 4. What experimentation must NEVER grow on the node

Hard boundary (already refused in source and/or ratified law):

| Forbidden growth | Why | Where refused / ruled |
|---|---|---|
| Per-bot paper lane / warm-up / probation / ramp / paper twin / paper-performance gate | DEC-0261; bots arrive operator-approved | `qmn.paper.lane` |
| Research / QMB ungoverned tunnel occupying a seat | QL-8 / E12-F05; node needs CT-33 + QML protocol + admission layers | `qmn.seats.admission` |
| QMA execution tool (incl. "paper only") or QMA→venue edge | Money-path barrier DEC-0341 | ADR-0020; qma-core deny-list |
| Forked second loop / node-private slice engine | DEC-0190 / B-2 identity | `qmn.loop.driver` |
| In-process / ledgered node replay as admission or promotion evidence | Replay is diagnostic spawn only | `qmn.replay.session` |
| Sandbox provenance into live via silent merge | Hub refuse at publish **and** pull | `qmn.promotion.hub` / `passive_hub` |
| Same-day trade / activation override / warm-up on activation | DEC-0261 next-day activation | `FORBIDDEN_ACTIVATION_OVERRIDES`; `SAME_DAY_TRADE_PATH_EXISTS = False` in `promotion/lifecycle.py` |
| Local matching engine / Bot–Book twin for paper | AD-35 / CONNECT AD-2 | ADR-0021; `paper/transition.py` twin refusals |
| Operator CLI or agent MCP as a fourth door (V1) | R1 / DEC-0211; GAP-0053 deferred | `doors/parity.py` |
| MIS training / ML fit on the VPS decision path | GAP-0051 offline; shadow seam only on node | NODE TN-19; DEC-0261/0262 |
| Import of `qmf-venue` outside `qmn.venue` | L30 / DEC-0241 | constitution + ADR-0019 |
| Growing QMB/QMA capabilities inside `qmn` "for convenience" | Applications are peers on QMF; node is live composition root only | standing laws in `_BRIEF.md` |

Classification: **`reuse`** existing refusal surfaces; any new experiment capability is **`new`** on QMB/QMA/research — **not** on COMP-QMN. Evidence: `source-inspected` + `documented-design`.

---

## 5. Candidate promotion path from QMB/QMA artifacts to the node

End-to-end path (coded domain + ratified TN-20):

```
QMB governed runs / QMA content-addressed candidates
        │  (WriterId-scoped fragments; may carry research provenance)
        ▼
hub-inbox  (write-only; confined sandbox-push SSH identity)
        │  human ops: hub_publish power (ops-allowed)
        │  refuse provenance=sandbox at publish
        ▼
hub-published  (read-only published as-of sets)
        │  human operator: promotion_sign (operator-only)
        │  silent battery vs fresh state
        │  pull_published_as_of — refuse sandbox; verify fp1 vs card
        ▼
PromotionLanding  seat ADMITTED, no intents, no ledger, no exposure
        │  separate human activation click
        │  effective only at next account-scoped day boundary
        │  revalidate before first intent
        ▼
ACTIVE seat on live (or Book-paper-routed) binding
```

**Source anchors:**

- Passive: `accept_inbox_fragment` / `publish_inbox_fragment` / `pull_from_published`; inbound crossings only `{sandbox-push, promotion-pull}` — `git show integration:qmn/src/qmn/promotion/passive_hub.py`.
- Sandbox refuse: `refuse_sandbox_provenance` at publish and pull — `promotion/hub.py`.
- Battery checks: admission layers, fingerprints, CT-18, live baselines, admission_impact, blanks, value_status — `promotion/battery.py` (`BatteryCheckId`; demo baseline never satisfies live).
- Lifecycle: `promote_to_admitted` (human signer only; `activate=` must stay false); `request_activation`; `revalidate_before_first_intent`; agent signer prefixes include `qma:` — `promotion/lifecycle.py`.
- Seat gate: `propose_node_seat` after CT-33 / QML / prediction linter / footprint / canonical assignment / Book+BMS / AD-32 layers — `seats/admission.py`.
- Journal: CT-13 `promotion` type; activation maps CT-24 → `risk transition` — `promotion/journal.py`.

**Ownership split:**

| Stage | Owner | Classification |
|---|---|---|
| Produce backtest / paper-validation evidence | COMP-QMB | `reuse` |
| Produce agentic candidates (dev-zone only) | COMP-QMA-* | `reuse` |
| Push fragment to hub-inbox | Ops / factory / sandbox identity | `connect` |
| `hub_publish` + `promotion_sign` + `activation` | COMP-QMN powers + human | `reuse` |
| UI to drive those powers / show battery words | Desktop UI (later) | `connect` / `new` UI only — not new node semantics |

Evidence: `source-inspected` + `documented-design` (`trading-node.md` TN-20 ~376-378; ADR-0019).

---

## Closing synthesis

### (1) What already exists

- Full `qmn` tree on integration: paper, promotion, loop, seats, doors, replay, venue, capital, host, MIS shadow seam, deploy toolkit.
- Unforked `run_slice` driver + recording accumulator.
- Book-level paper routing, first-deployment window, protective demotion, explicit per-bot-lane refusals (DEC-0261).
- Three doors with closed powers catalog and evidence read routes.
- Promotion hub + silent battery + next-day activation + sandbox provenance refusals.
- Seat admission that blocks the QMB ungoverned tunnel.
- Replay as out-of-process diagnostic with admission-gate refusal.

### (2) Missing wiring vs missing function

| Item | Kind |
|---|---|
| Desktop UI over evidence + powers (SSH tunnel) | **Missing wiring** to existing doors — not missing node function |
| Research/QMA producers emitting hub-inbox fragments with correct WriterId / non-sandbox publish path | **Missing wiring / connect** at producers — hub accept/publish/pull exist |
| Honest FX paper submit/read-back on live cTrader client (CONNECT) | **Missing/incomplete function** on venue edge (ADR-0021 defects at SHA); paper **routing** law already present |
| GAP-0053 agent/MCP door | **Deferred function** — must not be mistaken for a research execution door |
| GAP-0051 MIS training models | **Missing offline function** — must not land as node experimentation |
| Per-bot paper on node | **Must remain absent** — not a gap to fill |

### (3) Recommended architectural ownership

- **COMP-QMN:** live composition root; Book paper/soak/demotion; `run_slice` host; doors; promotion/activation; governed seats; venue wiring.
- **COMP-QMB:** all strategy experimentation, backtests, research paper-validation, governed evidence for admission cards.
- **COMP-QMA-*:** candidate artifacts and lineage only; never paper/live execution.
- **COMP-QMF-RISK / registry:** Book/BMS/paper nouns, promotion card schemas, zones.
- **UI:** evidence reader + powers client; never a parallel experiment runtime.

### (4) Open questions — need AD vs Deferred

| Question | Disposition |
|---|---|
| Exact artifact schema / WriterId conventions for QMA→hub-inbox fragments in the strategy-experimentation sitting | Needs **AD** (connect contract) if not already pinned by QMA CT + hub fragment shape |
| Whether research "paper-validation" AccountRole ever becomes a node V1 role (today deliberately unused) | Stay **Deferred** / role-addition later; do not reopen DEC-0261 |
| Agent/MCP door (GAP-0053) | Stay **Deferred**; if opened, still must not grant execution or bypass human promotion |
| Fill simulation in node replay (GAP-0056) | Stay **Deferred**; must not become governed promotion evidence |
| Hot-apply settings (GAP-0052), OS seat confinement (GAP-0054) | Stay **Deferred**; orthogonal to experimentation boundary |
| UI placement of promotion battery wording | Product/UI AD later; node already returns operator words from battery |

No AD is required to reaffirm DEC-0261, the QMA money-path barrier, or unforked `run_slice` reuse — those are standing law with matching source refusals.
`)