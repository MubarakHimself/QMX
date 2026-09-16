# Cut — paper (research-paper / paper-validation ownership)

Sitting: architecture-QMX-2026-09-14. Planning checkout `main`. Product inspected: `integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` via `git show` / `git ls-tree` only. No checkout, commit, or implementation.

Question: the operator wants paper testing before promotion. QMA `ExperimentSpec` forbids any account including paper. Node paper is operational soak. Where does research-paper / paper-validation live so QMA, QMB, and QMN do not each invent a paper path?

Evidence levels: `user-intent` | `documented-design` | `source-inspected`. Class/test existence is not end-to-end proof.

## Compact table

| # | Surface | Class | Evidence | Owner |
|---|---|---|---|---|
| 1 | Node paper (soak + protective demotion) | **reuse** | source-inspected + documented-design | `COMP-QMN` `qmn.paper` + `COMP-QMF-RISK` `qmf.risk.paper` |
| 2 | QMA paper execution / ExperimentSpec on an account | **reuse** (deny already coded) | source-inspected + documented-design | `COMP-QMA-CORE` barriers + CT-47 — **QMA-paper does not exist** |
| 3 | Research-paper before promotion | **connect** | user-intent + documented-design + source-inspected | Named workflow over **QMB governed replay** (`world=replay`), outside the node |
| 4 | `paper-validation` / `paper-benched` account roles | **reuse** (unused V1 namespace) | documented-design + source-inspected | CT-03 enum only; node V1 collapses paper routing to `role=demo` |
| 5 | Venue-backed candidate paper brokerage (QuantConnect-style) | **new** if demanded; **not owed** | user-intent vs L30 / DEC-0261 | Would need a fifth venue importer or a per-bot node lane — both forbidden |
| 6 | AD-32 Layer-2 demo/paper shakedown | **reuse** (different noun) | documented-design + source-inspected | `qmf.risk.admission.run_layer2_shakedown` — Book/BMS machinery proof, not strategy paper-test |
| 7 | Registry “paper zone” (QMA read-only) | **reuse** (different noun) | documented-design | Promotion-zone vocabulary, not an account |

**Topic verdict: `connect`.** Do not mint a fourth paper executor. Reuse QMB replay as research-paper, reuse QMN Book-level demo as node-paper, reuse the QMA deny-list. Connect them as three named nouns in the pre-promotion workflow. Missing work is **wiring/naming**, not a new COMP.

---

## Source-linked findings

### 1. User intent vs standing law (do not silently pick one)

**User intent** (`user-intent`): paper testing precedes promotion; a strategy variant is human-approved and assigned to an intended Book before live (`workroom/research/2026-09-14-ui-recovery-late.md:14`; `workroom/research/2026-09-14-backend-baseline.md:33`; `intent-durable.md` AD-cand-2). QuantConnect’s Research Pipeline is **Backtest → Paper → Live** with paper as live brokerage simulation (`orchestrator-verified.md:23`; CAPABILITY-EXPANSION donor table refuses “paper brokerage as QMX paper”).

**Standing law** (`documented-design`):

- Paper-before-promotion happens **OUTSIDE the node**. Bots arrive backtested, iterated, and paper-traded in QMB and the research lanes. The node grants **no** per-bot warm-up, probation, ramp, or paper lane. Sole post-activation paper route = BMS/Book protective demotion (`docs/AGENTS.md` hard rule; `docs/glossary.md` “Bot journey”; `docs/components/trading-node.md:23`; DEC-0261; GAP-0057 answered).
- QMA’s only money-path output is a candidate a human promotes. **No execution tool at any account role, paper included** (`docs/AGENTS.md` QMA money-path; `docs/contracts/ct-47-qma-experiment-spec.yaml:38`; ADR-0020; DEC-0341; DEC-0375 dead).
- Node is ONE product with modes `paper | live`. Paper is **Book-level** routing to the paired **demo** account (`role=demo`, `world=live`), never a “paper node”, never a per-bot lane (DEC-0186, DEC-0194, DEC-0261; ADR-0021 honest FX paper).
- **No paper role may gate live money.** Admission has no paper-performance gate (AD-32 / DEC-0146; CT-22; CT-32; SCN-0007). Replay-world evidence cannot gate live money (DEC-0162; `docs/components/qmb.md:209`).

Consequence: “paper testing precedes promotion” is an **operator workflow requirement**, not a machine gate that refuses promotion without paper-account fills. Two independent builders will otherwise implement incompatible paths (QMA paper tool vs QMN per-bot lane vs QMB-as-paper vs a new venue runtime). That is the AD.

### 2. Node paper — operational soak, not research-paper

`git ls-tree` on integration: the only paper *packages* are `qmn/src/qmn/paper/` and `packages/qmf-risk/src/qmf/risk/paper.py`. There is no `qmb/.../paper.py` and no QMA paper executor.

`git show integration:qmn/src/qmn/paper/__init__.py` — module identity `PAPER_SURFACE = "qmn.paper"`. Paper is “one explicit Book routing state plus protective demotion — never a per-bot warm-up, probation, ramp, or paper lane.”

`git show integration:qmn/src/qmn/paper/lane.py`:

- `FORBIDDEN_PER_BOT_PAPER_SURFACES` = `{per-bot-warm-up, probation, ramp, paper-namespace, paper-performance-gate, bot-paper-twin, book-paper-twin, per-bot-paper-lane}`.
- `POST_ACTIVATION_PAPER_ROUTE = "bms-book-protective-demotion"`.
- `refuse_per_bot_paper_lane` / `inspect_bot_node_journey` refuse every forbidden surface (`qmn/tests/test_qmn_paper.py` covers this).

`git show integration:qmn/src/qmn/paper/routing.py`:

- `NODE_PAPER_ACCOUNT_ROLE = AccountRole.DEMO`, `NODE_PAPER_WORLD = World.LIVE`.
- V1 **collapses** AD-9 roles: `paper-validation` and `paper-benched` are deliberately unused; Book-mode PAPER and benched-seat evidence share the demo role-scoped namespace and are told apart by **routing reason** (`require_demo_paper_target` policy-rejects any other role). Matches CT-24 usage note (`docs/contracts/ct-24-book-mode.yaml:31`).

`git show integration:qmn/src/qmn/paper/first_deployment.py` — soak week: full demo shape, Book routing `PAPER`, live connection sensing-only, never a live binding. CONNECT (ADR-0021 / DEC-0264) makes that demo path **honest FX paper** (same live `VenueClientPort`, vendor demo host, CT-19 encode + CT-20 read-back) — machinery proof, not a research executor (`docs/components/trading-node.md:17-23`; CAPABILITY-EXPANSION: “Research-paper does not belong here”).

SCN-0006 (Book paper transition) stays **defined-unwired until the node wires it** (`docs/scenarios/SCN-0006-book-paper-transition.md:55`). That is **missing wiring of node-paper**, not a hole that research-paper should fill.

**Do not grow research-paper on COMP-QMN.**

### 3. QMA — ExperimentSpec and the money-path barrier already refuse paper accounts

CT-47 invariant (`docs/contracts/ct-47-qma-experiment-spec.yaml:38`): an `ExperimentSpec` runs against recorded evidence and QMB replay only, **never an account of any role — paper included**. Docs still stamp `wiring_status: defined-unwired` / “no code exists” (`ct-47:6-9,69`). Integration **source exists** — treat the stamp as stale, not as absence (`code-qma.md` CT-47 reconciliation).

`git show integration:qmx-agents/packages/qma-core/src/qma/core/ports/qmb.py`:

- Route `agent → qma_backtest_tool → backtesting_service → qmb_door → qmb`.
- `QMB_WORLD_REPLAY = "replay"`.
- `VENUE_ACCOUNT_REQUEST_FIELDS` includes `paper`, `paper_account`, `demo`, `live`, `venue`, `account`, `book_mode`, …
- `_NON_REPLAY_WORLDS` includes `paper`, `live`, `demo`.
- `refuse_venue_account_backtest`: “never against any venue account”.
- `QmbBacktestRequest.try_create` refuses `account` / `venue` / `paper` / `live` kwargs and extra keys in that set.

`git show integration:qmx-agents/packages/qma-core/src/qma/core/barriers/money_path.py`: act-level deny-list; paper/live/demo prefixes stripped then matched; “Paper is an account role on a real venue, never a sandbox.” `QMA_MINTED_PROMOTION_COMMAND = None`.

`git show integration:qmx-agents/packages/qma-core/src/qma/core/ports/deployment.py:115`: `PAPER_IS_SANDBOX: Final[bool] = False`. Reachability refuses trading-node hosts and `qmf-venue` images (`barriers/reachability.py`; `docs/components/qma-daemon.md:255`).

QMA may **read** paper market data / positions / account state and may change none of it (`qma-daemon.md:255`). That read is not a paper-test path.

**Do not grow a QMA paper tool, “paper only” included.**

### 4. QMB — the only legal research-paper executor, and it is replay, not a venue

`git show integration:qmb/pyproject.toml` — depends on `qmf-core`, `qmf-registry`, `qmf-data`, `qmf-indicators`, `qmf-structure`, `qmf-risk`, `qml`. **No `qmf-venue`.** L30 / DEC-0169 / DEC-0241: QMB never imports venue; `qmn.venue` is the sole sanctioned importer.

`git show integration:qmb/src/qmb/config/replay.py` (header): every QMB run mints exactly one CT-28 binding with **`world = replay`**, a different identity from any live binding, incomparable to it.

`docs/components/qmb.md:199-209`: QMB stays barred from `qmf-venue`; a bot’s backtesting **and its paper stress-testing** are part of the pre-promotion journey, all outside the node. That sentence is the corpus’s name for research-paper. Source cannot realize it as a demo account: the loop is the same `run_slice`, the clock and port are replay. Account-role labels on QMB tests (`AccountRole.PAPER_VALIDATION` in `qmb/tests/test_downstream_reads.py`, `test_golden_slice.py`) are **labels on replay artifacts**, not venue sessions.

QMB therefore **already is** the research-paper function if research-paper is defined as governed replay + CT-32. It is **not** a paper brokerage.

### 5. `paper-validation` is an account-role noun, not a home

CT-03 (`docs/contracts/ct-03-instrument-identity.yaml:44`; `git show integration:packages/qmf-core/src/qmf/core/identity.py` `AccountRole`): `live | demo | paper-validation | paper-benched | prop-firm`.

`qmf.risk.paper.ExecutionTarget` accepts any non-live role as a paper target (`git show integration:packages/qmf-risk/src/qmf/risk/paper.py`). Risk tests default paper targets to `PAPER_VALIDATION` (`packages/qmf-risk/tests/test_paper.py`). Node V1 **refuses** that role and requires `demo` (`qmn.paper.routing.require_demo_paper_target`).

Do **not** revive `paper-validation` as:

- a QMB `world` (worlds are `live | replay | simulated`; paper/demo are `world=live` via account role, DEC-0110);
- a QMA ExperimentSpec field;
- a per-bot namespace on the node;
- a fourth runtime.

A later split of Book-mode PAPER vs benched-seat evidence is “a role addition, never a re-write” (CT-24; DEC-0194, DEC-0251). Out of this sitting.

### 6. Adjacent nouns that must not steal the name “paper”

| Noun | What it is | What it is not |
|---|---|---|
| Book mode `LIVE \| PAPER` (AD-35 / CT-24) | Dated binding-epoch routing; standing evidence state | A research experiment; a Bot twin (DEC-0069 dead) |
| AD-32 Layer 2 | Technical shakedown on a demo/paper **Book/BMS** binding — connect, register, execute; proves machinery, not edge (`qmf.risk.admission.run_layer2_shakedown`; `docs/components/qmf-risk.md:87`) | Strategy paper-test before promotion |
| Registry live-zone promotion (AD-18 / SCN-0007) | Human-signed card; node promotion then next-day activation | Paper-performance gate |
| QMA “paper zone” read-only (`qma-daemon.md:255`) | Registry zone access | An account |
| QML Layer 2 sandbox (`qmb.host.runner.run_sandbox`) | Conformance isolation | Paper trading |

---

## (1) What already exists

- **Node-paper function (source-inspected):** `qmn.paper` — soak (`first_deployment.py`), Book routing to one paired demo (`routing.py`, `transition.py`), protective demotion (`demotion.py`), per-bot-lane refusals (`lane.py`). Shapes in `qmf.risk.paper` (BookMode, ExecutionTarget, paper epochs). CONNECT honest FX paper on the live port.
- **QMA deny function (source-inspected + unit tests):** ExperimentSpec / QMB door `world=replay` only; venue/account/paper fields refused; money-path deny-list; `PAPER_IS_SANDBOX = False`; no promotion command.
- **QMB research executor (source-inspected):** pure `run()` / `run_slice`, orchestrator ledger, CT-32, CLI/API. Always `world=replay`. No venue.
- **Account-role enum (source-inspected):** `paper-validation` exists and is unused by node V1.
- **Human promotion path (documented-design + node source in `qmn.promotion`):** hub publish → `promotion_sign` + silent battery → ADMITTED → next-day `activation`. Replay and paper roles do not authorize live.

## (2) Missing wiring vs missing function

**Missing wiring (owed if this sitting names research-paper):**

- Product language: stamp **research-paper** vs **node-paper** vs **QMA-paper-does-not-exist** on UI, promotion-card copy, and ExperimentSpec/CT-32 lane so builders do not call soak “paper-testing a strategy” or call QMB replay “paper brokerage”.
- Pre-promotion workflow connect: QMB governed CT-32 (and optional ungoverned research values) → human review → hub → node. QMA may *coordinate* a replay job through CT-47; it may not attach an account.
- CT-47 docs still say `defined-unwired` / “no code exists” while daemon ports/services exist — documentation reconcile, not a new paper path (`code-qma.md`; `code-qmb.md` §10). Real QMB CLI transport vs `RecordingQmbDoorTransport` is the **CT-47 connect** cut, not this one.
- SCN-0006 / node Book-paper golden scenario still defined-unwired — node factory wiring, not research-paper.

**Missing function (not owed — do not fill as a convenience story):**

- A venue-backed **candidate** paper-trading runtime (unpromoted bot on a demo/paper account, QuantConnect paper brokerage). QMB cannot import `qmf-venue`. QMA cannot execute. QMN cannot host a per-bot paper lane. A new COMP that imports `qmf-venue` would amend L30 (second sanctioned importer). Putting unpromoted bots on node PAPER would amend DEC-0261 (“everything on the node is operator-approved”).
- Using `paper-validation` as a live V1 namespace. Node collapse to `demo` is already coded.

If the operator later wants actual demo-account paper of **unpromoted** bots, that is a **new** spine amendment, not an extend of QMB or QMA.

## (3) Recommended architectural ownership

| Job | Owner | Class |
|---|---|---|
| Research-paper / “paper-test this strategy before I promote” | **COMP-QMB** governed replay (`world=replay`, CT-32). QMA may place one `qmb` job per env through CT-47. Ungoverned `qmb.run()` remains legal and writes no evidence. | **connect** over **reuse** |
| Node-paper / soak / protective demotion / honest FX demo | **COMP-QMN** `qmn.paper` + `qmn.venue` | **reuse** |
| Book-mode PAPER shapes, epochs, dispositions | **COMP-QMF-RISK** | **reuse** |
| Forbid QMA execution including “paper only” | **COMP-QMA-CORE** deny-list (already) | **reuse** |
| Human promote + activate | Operator outside QMA, on the node powers channel | **reuse** |
| `paper-validation` role | Stay unused in V1 | **reuse** enum; do not connect |

No sixth application. No QMB venue import. No QMA paper tool. No QMN per-bot paper lane.

## (4) Open questions — AD vs Deferred

**Needs an AD (two builders would otherwise choose incompatibly):**

**Paper trinity / DEC-0261 reading.** Pin three nouns and the DEC-0261 phrase “paper-traded with QMB and the research lanes”:

1. **research-paper** = QMB governed replay (and ungoverned research values) **outside** the node, before promotion. It is **not** `world=live` paper, not a demo account, not QuantConnect paper brokerage.
2. **node-paper** = Book-level demo routing + first-deploy soak + BMS/Book protective demotion (`role=demo`, `world=live`). No per-bot paper lane.
3. **QMA-paper** does not exist.

Also pin: paper-testing-before-promotion is **workflow**, not an AD-32 paper-performance gate (replay cannot gate live; paper roles cannot gate live). Promotion evidence remains CT-32 + three-layer admission + human signature.

Draft spine AD-7 already states this; this cut is the evidence that it must stay an invariant, not a slogan.

**May stay Deferred (none-defer for extra function):**

- Splitting `paper-validation` vs `paper-benched` namespaces (CT-24: later role addition).
- GAP-0058 single-machine node placement (still COMP-QMN, still DEC-0261 — not a research-paper home).
- SCN-0006 node wiring (factory, not this sitting).
- Whether UI copy says “research-paper” vs “backtest” — product language after the AD, not a second AD.
- Venue paper of unpromoted bots — only if the operator explicitly reopens DEC-0261 and L30.

---

## Brief-required close

Already exists: three disjoint paper surfaces in source and corpus — QMN Book-demo soak/demotion, QMA account-execution forbid, QMB replay. Missing wiring: naming + pre-promotion connect so “paper-tested” cites QMB CT-32 and never soak or a QMA tool. Missing function: a candidate paper-brokerage runtime — **intentionally absent**. Ownership: research-paper on QMB; node-paper on QMN; QMA never executes. Recommended AD: paper trinity (draft AD-7).
