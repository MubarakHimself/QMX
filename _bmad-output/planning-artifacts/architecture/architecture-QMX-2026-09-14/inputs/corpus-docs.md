# Corpus map — strategy-experimentation architecture sitting

Architecture-only input. Evidence levels: `documented-design` unless marked `source-inspected`. Product source tip: `integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`.

## Compact map

| Area | Classification | Ratified surface | Evidence | This sitting |
|---|---|---|---|---|
| Ordinary Python always legal + graduation (L33) | reuse | Constitution L9/L33; glossary Graduation path | documented-design | Confirm ownership; do not reopen law |
| QMB library + CLI (experimentation umbrella) | reuse | COMP-QMB, ADR-0017, B-1..B-15, FEAT-0029, FR-036..046 | documented-design + source-inspected (`qmb/`) | Ownership = run tunnel; do not re-architect |
| QML two-artifact bots + conformance | reuse | COMP-QML, ADR-0018, CT-33/34, FEAT-0030, FR-047..050 | documented-design | Own strategy declaration; GAP-0085 may extend |
| Data splits / journals / rooms | reuse | CT-12, CT-13, CT-10/11, L18–L20 | documented-design | Consume; no new data layer |
| CT-32 performance results | reuse/connect | CT-32 adopted by QMB; optimistic taint until GAP-0048 | documented-design | Wire/fill taxonomy content under GAP-0048 |
| QMA ExperimentSpec + QMB door (CT-47) | connect/extend | CT-47, FEAT-0044, DEC-0316 | documented-design **vs** source-inspected conflict | **Must reconcile** wiring_status |
| Human+agent co-use of experimentation | undecided (PRD hole) | PRD users §3; QMA money-path DEC-0341 | user-intent + documented-design | Decide ownership map |
| Fidelity taxonomy / calibration / simulated world | extend (partial) | GAP-0048 seams closed DEC-0164; content open | documented-design | **Decide content or keep own sitting** |
| Search-quality / attempt gate | extend (raw material only) | GAP-0049, GAP-0016/0017 deferred DEC-0121 | documented-design | Decide if this sitting is the owed “backtesting sitting” |
| Strategy-mechanism decomposition | undecided | GAP-0085; QMA said “revisit at QML sitting” (already past) | documented-design | **In-scope candidate** |
| Analysis workflows / Graph Templates / RLM fan-out | reuse ports; content deferred | QMA AD-12/14/17; GAP-0075/0076/0080 | documented-design | Leave most deferred; pin ownership only |
| Central backtesting service / donor engines | dead — never revive | DEC-0084/0085/0086; DEC-0375/0376 | documented-design | Graveyard |

---

## 1. What the corpus already considers ratified for experimentation

### Standing laws (do not reopen)

- QMF toolbox, not application (`docs/constitution.md:30-31`, L7–L8); applications QMB/QML/QMN/QMA built ON it (`docs/AGENTS.md:15-29`).
- Ordinary Python always legal; governed evidence requires graduation through the extension shape (`docs/constitution.md:82`, L33 / DEC-0133).
- Exact money/time/fingerprints/typed refusals; worlds `live | replay | simulated` with simulated reserved-unusable until GAP-0048 (`docs/constitution.md` L-block; `docs/glossary.md` World; DEC-0110).
- Default-deny roster imports; QMB/QML/QMA never import `qmf-venue` (`docs/constitution.md:76`, L30).
- Only a human promotes into the live zone (L17); QMA’s only money-path output is a candidate (`docs/AGENTS.md:29`, DEC-0341).
- Paper-before-promotion outside the node (DEC-0261); node has no per-bot paper lane.
- Build-our-own: borrow donor **mechanisms**, never donor engines or foreign platform contracts (DEC-0013; PRD §7).
- Configurable = UI-editable (L38).

### Experimentation product stack (ratified design)

| Layer | What is ratified | Key cites |
|---|---|---|
| **Umbrella vocabulary** | Experimentation = research activity; backtest = verification stage inside it | `docs/glossary.md` Experimentation and backtesting; DEC-0159 |
| **QMB** | One pure library + `qmb` CLI; pure `run()` / impure orchestrator; one resolved run-config; CT-32 + CT-13 in `world=replay`; fill/slippage/cost/financing **seams**; optimistic taint; Optuna behind typed port `n_jobs=1`; passive hub as-of sets (DEC-0084 stays dead) | `docs/components/qmb.md:15-25`; ADR-0017; B-1..B-15; FEAT-0029 |
| **QML** | Two-artifact bot (CT-33 + plain Python); CT-34 confluence; strategy family = key not authority; conformance gates evidence citation/seats, never tunnel entry; `.qml` DSL not revived | `docs/components/qml.md` via index; ADR-0018; CT-33/34; FEAT-0030 |
| **Data** | Train/validation/sealed-test splits (CT-12); journals CT-13; rooms per world; Dukascopy personal-use closed DEC-0170 | CT-12; CT-13; L18–L20 |
| **Risk evidence** | CT-22/27 Book/BMS templates; CT-32 performance container; admission interfaces (thresholds blank-block-live) | CT-22 v2; CT-27; CT-32 |
| **QMA experiment path** | Content-addressed `ExperimentSpec`; `BacktestHandle`/`StrategyHandle`; Experiment Ledger; single `qmb` door via `analysis-backtest` plugin; one job per environment; no QMA↔qmb package import | CT-47; DEC-0316; DEC-0348; FEAT-0044 |
| **Node relationship** | Live loop reuses QMB `run_slice` unforked; bots arrive backtested/papered outside node | ADR-0019; DEC-0261; TN-5 |

### Feature inventory (FEAT-0020 onward, experimentation-relevant)

- FEAT-0020..0022 — indicators/structure (consumed by QMB run loop).
- FEAT-0027 — risk contracts implementation (QMB/QML dependency).
- **FEAT-0029** — QMB experimentation library + CLI (full B-spine).
- **FEAT-0030** — QML bot authoring.
- FEAT-0031/0032 — node + CONNECT (consume QMB/QML; not experimentation owners).
- **FEAT-0040..0046** — QMA packages; FEAT-0044 is ExperimentSpec + QMB door.

### Contracts this sitting reads as settled shape

CT-12, CT-13, CT-22, CT-27, CT-32, CT-33, CT-34, CT-47 (shape ratified; **wiring claim stale** — §4).

---

## 2. Open / deferred gaps — decide here vs leave deferred

### Decide in this sitting (or explicitly refuse and keep a named later sitting)

| ID | Question | Why here |
|---|---|---|
| **GAP-0048** (remainder) | Fidelity taxonomy values, forex fill/slippage/financing calibration, parity contracts, simulated-time typing unlocking `world=simulated` | Seams already ruled (DEC-0164). Corpus assigns content to “backtesting / fidelity sitting.” This sitting **is** the strategy-experimentation architecture sitting — either absorb GAP-0048 content or mint an explicit AD that it remains a separate irreversible sitting. |
| **GAP-0049** | SR* / search-quality threshold, evaluation population, attempt-budget effect | Raw material accrues via QMB trials (DEC-0169). Thresholds still blank; staged funnel (ticket 008) waits on them. |
| **GAP-0016 / GAP-0017** | Look-ahead **registration gate** (CT-08 checklist) and attempt-count **policy** | Prevention delivered in QMB; gate/policy still operator-deferred to “the backtesting sitting” (DEC-0121). If this sitting claims that role, close or re-defer with a new revisit condition. |
| **GAP-0085** | Typed strategy-mechanism decomposition (Entry/Exit/Filter/Session/Position/Invalidation) | QMA Deferred table said “revisit at the QML sitting”; QML already closed GAP-0047 without answering GAP-0085. Ownership already stated: QML + `qmf-registry` own semantics; QMA carries candidates. Needs an AD: ship V1 decomposition, slim it, or re-defer with a non-obsolete revisit trigger. |
| **Human+agent experimentation ownership** | Who authors, who runs, who analyzes, what graduates | Standing laws exist; end-to-end ownership map across QMB/QML/QMA is not one AD. PRD §3 sketches users; no FR set for co-workflows. |
| **CT-47 wiring reconcile** | Docs `defined-unwired` / “no code exists” vs integration source | Brief-mandated; silent pick forbidden (§4). |

### Must leave deferred (revisit conditions already stated; not this sitting’s product)

| Block | IDs | Why not here |
|---|---|---|
| QMA ops / UI / memory / browser / VPS | GAP-0070–0084, 0086–0091 (except 0085) | Not strategy-experimentation semantics; revisit when Missions/UI/providers block |
| Node | GAP-0050–0056, GAP-0058 | KSA values, MIS training, hot-apply, agent/MCP door, confinement, second VPS, fill-sim-in-replay, placement variant |
| CONNECT | GAP-0059, GAP-0060 | FTR-02, live source token |
| QMB spine deferred non-content | MCP door details, cloud-burst, UI rendering, debug/ML-RL/Rust path, locked third split, Grid/Euler, prop-firm Books | Explicitly out of V1 / other sittings (`architecture-QMB-…/ARCHITECTURE-SPINE.md:244-259`) |
| Parent QMX deferred non-experiment | Alpha-decay math, window widths, margin sizing, crypto calendar, observability design, etc. | `architecture-QMX-…/ARCHITECTURE-SPINE.md:599-632` |

### Partial closures already on record (do not re-litigate seams)

- GAP-0048 **seams** ruled; isolated-sandbox + Bot-by-Book matrix answered by QMB architecture (`_docwork/gaps.yaml` GAP-0048 answer).
- GAP-0016 look-ahead **prevention** delivered; only registration **gate** open.
- GAP-0047 answered by QML (DEC-0184).
- GAP-0057 answered — no per-bot warm-up on node (DEC-0261).

---

## 3. PRD coverage holes (prd-QMX-2026-08-21) vs recovered intent

Recovered intent axes from the brief: **human+agent, ordinary Python, data, strategy creation, experiments, analysis, workflows, extensibility**.

| Intent axis | PRD coverage | Hole |
|---|---|---|
| **Ordinary Python** | FR-046 / FR-047: plain Python first-class; no `.qml` DSL | Graduation **path** (L33 → CT-16/17 or CT-33) not an FR; only constitutional |
| **Human+agent** | §3: operator + agents as users; agents use QMB CLI / Python APIs | No FRs for shared experiment ledger, agent-placed `ExperimentSpec`, approval diffs on `money_path_relevant` candidates, or desk Graph Templates |
| **Data** | FR-010..018, FR-042 | Adequate for research splits; no FR tying ExperimentSpec `data_ref` to CT-12 manifests |
| **Strategy creation** | FR-047..050 (QML) | No FR for strategy-mechanism atoms (GAP-0085); no FR for ungoverned→governed graduation of bots beyond conformance ticket |
| **Experiments** | FR-036..045 (QMB tunnel) | Strong on run/optimize/robustness; **no** ExperimentSpec, Experiment Ledger, or “one qmb job per environment” QMA door (those post-date PRD / live in ADR-0020) |
| **Analysis** | Thin: robustness ladder FR-040; CT-32 reports FR-043 | No Analysis-desk / RLM / BacktestHandle FRs; PRD §6 still says QMA “ideation has not begun” (`prd.md:502-513`) while docs have full ADR-0020 |
| **Workflows** | Notification/unattended doctrine; promotion SCN | No Hypothesis-Test-Learn / Act-Observe-Verify Graph Template FRs; staged funnel (ticket 008) deferred without PRD row |
| **Extensibility** | QMB adapters/config fragments; QML extension shape | QMA desk `plugin` packs and CT-42 not in PRD; PRD still lists Modal/E2B as “direction only” while QMA Cut rejects them on cost (GAP-0075) |

**Stale PRD composition table** (`prd.md:78-85`): QMA = “Deliberately unplanned; Named phase boundary only.” Corpus supersedes that with COMP-QMA-*, CT-40..51, FEAT-0040..0046. Trading node row similarly understates ADR-0019. This sitting should treat PRD §5 G–H as QMB/QML authority and **not** treat §6 QMA prose as architecture authority.

---

## 4. Stale-doc vs source conflicts (known)

### CT-47 — primary brief conflict

| Claim in docs | Reality on integration |
|---|---|
| `wiring_status: defined-unwired`; comments/provenance “no code exists” (`docs/contracts/ct-47-qma-experiment-spec.yaml:6-9`, `:69`) | Source **exists** under `qmx-agents/` |

**Source-inspected evidence** (`git show integration@1b451a8:…`):

- `qmx-agents/packages/qma-core/src/qma/core/ports/experiments.py` — `ExperimentSpec`, parse/identity, GAP-0085 refuse set, CT-07 edge types.
- `qmx-agents/packages/qma-core/src/qma/core/ports/qmb.py` — QMB door types / admit helpers.
- `qmx-agents/packages/qma-daemon/src/qma/daemon/backtest/service.py` — `BacktestingService` (analysis-backtest half; one job per env; no `import qmb`).
- `qmx-agents/packages/qma-daemon/src/qma/daemon/experiments/service.py` + `ledgers/experiment.py`.
- Tests/examples: `test_experiment_spec.py`, `test_qmb_backtesting_door.py`, `experiment_spec_usage.py`, etc.

**Reconcile rule for this sitting:** do not silently prefer docs or code. Produce an AD that either (a) updates CT-47/`wiring_status` + consumers to match factory-built surface and classifies remaining gaps as missing **wiring** vs missing **function**, or (b) marks integration paths as provisional/non-authorizing until factory re-ratification — but state the conflict explicitly.

### Adjacent stale “no code” patterns (same class, lower priority)

Many risk/QML contracts still say `defined-unwired` / “no code exists” (e.g. CT-32, CT-33) while `qmb/` and `qml/` trees exist on integration. Same discipline: class existence ≠ end-to-end proof; stale docs ≠ proof of absence.

### PRD vs docs

- PRD §6 QMA “research — ideation has not begun” vs ADR-0020 absorbed (`_docwork/stage_state.yaml` QMA increment).
- PRD delivery sequence predates node CONNECT and QMA factory features.

---

## 5. Dead decisions that must not be revived

### Experimentation / backtesting graveyard

| DEC | Rejected idea | Cite |
|---|---|---|
| **DEC-0084** | Central always-on backtesting service for all agents/Books | `docs/gap-report.md:294`; B-15 hub is dumb storage |
| **DEC-0085** | Adopt Nautilus Trader contracts as foundation | gap-report dead table |
| **DEC-0086** | Three-day spike to adopt an external trading framework | gap-report |
| **DEC-0014** | Third-party libraries that define strategy families | gap-report |
| Engine / kernel vocabulary for QMB | “Backtesting engine”, “QMX Backtesting Framework” | glossary retired names; DEC-0159; DEC-0348 |
| Git-branch-per-parameter lineage | **DEC-0376** Cut | QMA Cut table; CT-47 uses content-addressed config |
| QMA execution / paper trading tool | **DEC-0375** | Money-path barrier |
| Parallel Bot paper twin | DEC-0069 | ADR-0009 |
| Donor engines (Jesse/LEAN/Nautilus) as runtime | DEC-0013 + QMB inherited invariants | shapes only |

### QMA Cut-outright (DEC-0360..0379) — do not smuggle back via “experimentation”

Foreign agent runtimes, plugin marketplace, group-chat coordination, eleven-entry loop registry, salvage from deleted `workroom/agentic-system-planning`, etc. (`docs/gap-report.md:299-324`; QMA spine Cut table).

### Still “out of scope for QMF roster” but realized as apps

DEC-0083/0087/0088 deferred backtesting **in QMF V1** — capability lives in COMP-QMB, not roster (`docs/gap-report.md` out-of-scope section). Do not pull backtesting into `qmf-*` packages.

---

## Closing synthesis (brief-required)

### (1) What already exists

- Full ratified **design** for QMB (tunnel), QML (strategy artifacts + conformance), data splits/journals, CT-32 evidence, and QMA’s ExperimentSpec/QMB-door **contract**.
- Integration **source** for QMB and for CT-47-shaped QMA experiment/backtest ports (inspect, do not assume E2E).
- Standing laws for ordinary Python, human promotion, no QMA execution, no central backtest service, no donor engines.

### (2) Missing wiring vs missing function

| Missing **function** (need AD / content) | Missing **wiring** (shape exists; factory/docs lag) |
|---|---|
| GAP-0048 taxonomy + calibration + parity + simulated-time | CT-47 / CT-32 / CT-33 docs still `defined-unwired` while packages exist |
| GAP-0049 thresholds + attempt policy (0016/0017 gate) | QMA daemon ↔ QMB door runtime placement vs package-import ban (design says job placement; verify end-to-end) |
| GAP-0085 strategy-mechanism types | Admission-bar threshold **values** (interfaces exist; blanks block live) |
| Human+agent experiment workflows as FRs/ADs | PRD §6 QMA text vs ADR-0020 absorption |
| Staged funnel routing (ticket 008) as product behavior | Hub deployment detail (node/ops) |

### (3) Recommended architectural ownership

| Concern | Owner | Class |
|---|---|---|
| Run loop, fills, optimize, robustness, CT-32 emission | **COMP-QMB** | reuse |
| Bot/strategy declaration, confluence, conformance, mechanism atoms (if minted) | **COMP-QML** + **qmf-registry** kinds | reuse / extend |
| Splits, rooms, journals, raw evidence | **qmf-data** | reuse |
| Book/BMS/admission interfaces | **qmf-risk** | reuse |
| ExperimentSpec, Experiment Ledger, candidate lineage, single qmb door | **COMP-QMA-CORE** definitions + **COMP-QMA-DAEMON** runtime | connect (reconcile wiring) |
| Live/paper money path, soak, promotion click | **COMP-QMN** | out of scope for content here |
| Simulator UI / charts UI | Deferred consumers | leave deferred |

### (4) Open questions — need AD vs can stay Deferred

**Need AD (this sitting):**

1. Is this sitting the owed GAP-0048/0049/0016/0017 “backtesting sitting,” or does it only pin ownership and spawn a child sitting?
2. GAP-0085: mint V1 mechanism vocabulary under QML/registry, slim subset, or re-defer with a new trigger (QML sitting already consumed)?
3. CT-47 (and sibling contracts): update `wiring_status` from source-inspected integration, or quarantine source as non-authorizing — **explicit reconcile**.
4. Human+agent experimentation ownership map (author / run / analyze / graduate / promote) as one AD spanning QMB/QML/QMA.
5. Whether staged funnel triage is V1 library procedure (manual stages) or stays Deferred until GAP-0049.

**Can stay Deferred:**

- GAP-0070–0084, 0086–0091; node GAP-0050–0056/0058; CONNECT 0059/0060.
- MCP door details, cloud-burst, UI/Simulator, RLM performance envelope (GAP-0076), memory backend (GAP-0072), alpha-decay math, window numeric widths.

---

## Spine Deferred pointers (for cross-check)

- QMX: `architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md:599+`
- QMB: `architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md:244+`
- QML: `architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md:198+` (thresholds stay 0048/0049)
- NODE: `architecture-NODE-2026-08-28/ARCHITECTURE-SPINE.md:963+`
- QMA: `architecture-QMA-2026-08-28/ARCHITECTURE-SPINE.md:525+` (Deferred) and `:552+` (Cut)
- CONNECT: `architecture-CONNECT-2026-09-11/ARCHITECTURE-SPINE.md:176+`
