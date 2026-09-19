# Loop / graph / agentic engineering vs STRATS and QMA

> **Research briefing. Not a spine. Not ratified. Not an AD mint. Possibilities only.**
>
> Plan only. No code, no Stats edits, no `docs/` edits, no git commits. Do not start `bmad-architecture`, documentation-factory, or epics from this file. Do not absorb Build Alpha.

| Field | Value |
|---|---|
| Status | architecture-increment **input** |
| Date | 2026-09-10 |
| Canonical path | `workroom/research/2026-09-10_loop-engineering-strats.md` |
| Parent briefing | `workroom/research/2026-09-09_strats-append-to-qmx.md` (STRATS bind; this file does not reopen it) |
| Clipping | `C:/Users/Mubarak/Documents/brain/brain/Clippings/The Loop Runs While You Sleep.md` (Build Alpha, 2026-09-02)[9] |
| Operator lean | STRATS sits more under **loop engineering**. MIS is a different sitting — noted only, not redesigned. |

**One-sentence claim.** The clipping's overnight cycle is QMA graph work plus a QMB validation door, with STRATS as the durable hypothesis / dead-end library that makes later revolutions cheaper — not a new loop runtime, not Build Alpha, and not live signals (DEC-0341).

---

## 0. Problem split

Do not solve column A with a design from column B.

| Problem | What it is here | What it is not |
|---|---|---|
| Overnight discovery cycle | Plateau notice + move the **search box** while the operator sleeps | A QMN live loop, a QMF roster loop, or Build Alpha |
| Inside-the-box search | Parameter search (RSI length, stop distance, lookback) | Changing which signals / fitness / order type exist |
| Hypothesis + dead-end library | STRATS files+SQLite: primitives, DNA, tagged failures as knowledge | QMA MemoryProvider, QMB ledger, genetic engine |
| Generate / backtest / validate | QMB library functions (B-8 optimize, B-14 ladder) | QMA importing COMP-QMB; QMA executing |
| Unattended agent | QMA Routine → Graph Template → Task Graph | An eleven-entry loop registry (Cut, DEC-0378) |
| MIS | — | Clipping's "regime filter" is a **search hyperparameter**, not a node signal snapshot. Do not redesign MIS. |

---

## 1. Vendor marketing vs portable ideas (2025–2026)

Three 2026 labels. Keep the portable mechanics; drop the product.

**Loop engineering (June 2026).** Replace the human as the person who prompts; design the system that prompts, checks, remembers, and re-runs.[1][2] Portable pieces: scheduled or event trigger; machine-checkable stop; persistent state **outside** the conversation; verifier ≠ maker; budget; escalate to a human.[1][2] Vendor pieces: Codex Automations, Claude `/loop` `/goal`, LangChain product names.[1][7] Skeptics call this renamed cron; the arXiv review found loop *config* in repos but almost no committed *state files*.[2]

**Graph engineering (July 2026).** Who decides the path — the agent or you.[4] Nodes, edges, shared state; a loop is the smallest graph (one node with an edge back).[3][4] Portable: encode valid paths and gates; keep agent freedom **inside** a node; graphs are usually cyclic, not DAGs.[3] Not knowledge-graphs / GraphRAG.[4] Vendor: LangGraph; Chase treated the new word as mostly the old framework.[3][4] TrueFoundry: graph = topology; loop = how an agentic node executes.[6]

**Agentic engineering (quant, 2025).** Man Numeric AlphaGPT: Idea Person / Implementer / Evaluator; proposes signals, writes code, backtests **before a human sees output**; same evaluation thresholds as human research; speed raises multiple-testing / p-hacking risk.[5][8] The clipping cites this warning and does not deny it.[9]

**Build Alpha (do not absorb).** C++ GA desk: 7,000+ signals, overnight box-moves, local memory store, export to TS/NT/MC/MT4/MT5/TV/Python.[9][10] Portable ideas only: generate/backtest/validate; plateau → move the box; negative results as a moat; gate must not loosen; no live signals.

QMA already named the nested stack without the 2026 slogans: **Graph Template** (topology, no runtime state) / **Task Graph** (runtime) / **Loop** (node kind with stopping_condition, budget, escalation) / **Skill ≠ Loop**. Operator last word: **graphs, not loops** (DEC-0340, DEC-0378). Named cycles — Act-Observe-Verify and **Hypothesis-Test-Learn-Mutate-Gate** — arrive as plugin `graph_template`s, none shipped in `qma-daemon` v1.

---

## 2. Twelve-row mapping (clipping → QMX)

| # | Clipping | Portable idea | QMX bind (possibility) |
|---|---|---|---|
| 1 | Generate. Backtest. Validate. | Deterministic research cycle | **QMB** (`optimize/`, `robustness/`). QMA reaches QMB only as the `analysis-backtest` door / `qmb` CLI — **no package edge** to COMP-QMB. |
| 2 | Genetic algorithm inside the box | Parameter search in a declared space | QMB B-8 Optuna over CT-33 typed space. STRATS must **not** grow genetic/evolution machinery (GROUND-STATE §8). |
| 3 | Plateau: search went flat | Machine-checkable stop; verifier ≠ searcher | QMB ledger fold (no improvement on the objective) + a Graph Template `deterministic_script` / verifier. Not an LLM noticing "2am." |
| 4 | Move the **box** (signals, fitness, order type, regime filter, filter-vs-scale) | Change search hyperparameters, not RSI length | QMA proposes a new `ExperimentSpec` (code/config/data refs, lineage DAG). Human **applies**. The box is not a STRATS executor field. |
| 5 | "If the productive region sits outside your box, no amount of compute finds it" | Inside-box GA cannot invent a missing primitive | STRATS dictionary + DNA is the **eligible primitive set**. Moving the box = citing / proposing different primitives — not rewriting QMB's sampler. |
| 6 | Memory of plateaus, moves, dead ends, tagged by pool / fitness / market / TF / direction | Persistent state outside the session; negative results as research inventory | **STRATS** as hypothesis + dead-end **knowledge**. QMA **MemoryProvider** is desk memory (admission_confidence), not the library. Never conflate (DEC-0318). |
| 7 | Revolution 400 smarter than 4 because failures survived | Retrieval before the next generation | Knowledge `search/retrieve/cite` over a pinned `CorpusSnapshot` (CT-44). Session recall is Memory `recall` — `NoMemoryProvider` until GAP-0072. |
| 8 | Validation gate must not loosen | Same thresholds, AI or human; more tests raise bogus-signal odds[5] | QMB B-14 ladder (MC, significance, walk-forward) + AD-22 "never an LLM judging itself." QMA cannot retune Book bars. DEC-0162: no stored pass/fail an agent can game. |
| 9 | Does **not** generate live trade signals; export is native code; human step remains | Discovery ≠ execution | **DEC-0341.** Candidate artifact only. No execution tool, paper included. `promote` is the human live-zone act outside QMA. |
| 10 | Overnight while you sleep; client need not exist | Unattended scheduled work | QMA **Routine** (cron/interval, machine principal) + `qma-wire` (closing a client never stops an agent). Not the QMN `run_slice` loop. |
| 11 | AI writes new signals mid-session, composed from 17 categories | Move the box by inventing primitives | **Conflict.** KnowledgeSource is read-only (DEC-0318). STRATS population is paused. AD-22: v1 apply needs an `operator` principal. Possibility: draft as candidate / `qmx_report` source kind — never write-back into Stats. |
| 12 | STRATS vs the overnight loop | Library vs runtime | STRATS = loop-engineering **state** (hypotheses, dead ends). QMA = overnight **graph**. QMB = generate/backtest/validate. Do not merge the three. |

---

## 3. Possibilities (not law)

**P1 — Bind, do not mint a loop runtime.** Overnight discovery is a plugin Graph Template (the already-named Hypothesis-Test-Learn-Mutate-Gate, or a thinner sibling) fired by a Routine. A `loop` node may iterate *inside* that template. An eleven-entry loop registry as organising centre stays Cut.

**P2 — STRATS is the dead-end / hypothesis moat.** Tag failures by signal pool, fitness, market, timeframe, direction in STRATS knowledge notes or lineage — as **knowledge**, with six `evidence_confidence` dims. Empirical status is a dimension, not a QMB ledger line. STRATS still must not hold run results, experiment ledgers, executors, or genetic machinery.

**P3 — Box move is a candidate, not a silent mutation.** Plateau → QMA drafts a new ExperimentSpec / primitive-pool proposal → QMB re-runs the ladder unchanged → human applies. `money_path_relevant` still requires a `human_gate`. A Routine is a `machine` principal and can answer no human gate.

**P4 — Two memories, two confidences.** (a) STRATS / CT-44: durable corpus, cite-copy, no write-back. (b) MemoryProvider: admitted session/desk memory of "what we tried last night." A QMA report re-enters only as a **distinct** `source_id` / kind (`qmx_report`), never into `strats`.

**P5 — QMB stays the gate.** Generate/backtest/validate, Optuna-inside-the-box, B-14 robustness. QMA never re-specifies QMB, never holds scheduling authority over QMB internals, never loosens bars to make a revolution look better.

**P6 — Reject.** New COMP for "the loop." Absorbing Build Alpha (signal library, C++ engine, broker exporters). STRATS as QML bots. QMA execution. Starting population because "the loop needs signals." MIS training / regime_classifier as this sitting.

---

## 4. Conflicts with ratified QMA

QMA never executes (DEC-0341). That part of the clipping **aligns**. The rest collides where the clipping wants an unsupervised self-rewriting desk.

| Id | Clipping pressure | Ratified constraint | Handling (possibility) |
|---|---|---|---|
| C1 | "Loop" as the product | Graphs, not loops (DEC-0340). Loop registry as centre is Cut (DEC-0378). Loop is a **node kind**. | Speak graph; keep loop as iteration inside a template. |
| C2 | Unattended box-move **and** apply | AD-22: v1 every apply needs `operator` principal; no scheduled approval path. Routine = `machine`. | Overnight **run** of a frozen template is legal. Overnight **mutation** of templates/loops/skills is not, until a later spine amendment. |
| C3 | Write new signals into the library mid-session | DEC-0318 / CT-44: read-only, no write-back, no QMX fields in Stats. Population paused. | Draft elsewhere. Human authors STRATS. Distinct `qmx_report` if QMA must retain the draft. |
| C4 | One local "memory store" of reasoning + dead ends | Memory ≠ Knowledge (DEC-0317/0318). `admission_confidence` ≠ `evidence_confidence`. v1 `NoMemoryProvider` (GAP-0072). | Split: STRATS for durable dead ends; MemoryProvider later for desk recall; Experiment Ledger for run reasoning. |
| C5 | Pipeline decides; you only see survivors | QMA has no COMP-QMB import. QMB publishes; does not bench/promote/bind. Replay verdicts cannot gate live money (DEC-0162). | QMB door + human promote. Do not let QMA filter by a stored pass/fail. |
| C6 | Faster discovery as the metric ("revolutions") | Man Group: more tests → more bogus signals.[5] QMB B-14 claims robustness, never edge (L20). | Count revolutions only as process telemetry, not as edge. Gate unchanged. |
| C7 | Export live-ready vendor code | DEC-0341 deny-list; no `qmf-venue`; candidate artifact only. | Aligns if export = draft QML / report, not orders. |
| C8 | Self-improving loop (GAP-0074 not met) | Self-improvement gates stay off until trajectory evidence exists (GAP-0074). | Do not treat the clipping as switching GAP-0074 on. |

**MIS (note only).** "Which regime filter applies" in the clipping is a **search-box hyperparameter**. It is not the node's compute-once MIS snapshot, not `regime_classifier_v1`, not Book/KSA input. Leave GAP-0051 alone.

---

## 5. Recommended bind vs new loop runtime

**Recommend: bind.** Use the QMA daemon that already exists: Routine (heartbeat) → plugin Graph Template (valid paths) → `loop` node (iteration) → QMB door (generate/backtest/validate, gate frozen) → STRATS via KnowledgeSource (hypotheses + dead ends) → human apply / promote.

**Do not mint a new loop runtime.** A second daemon, a vendor GA harness, or a revived eleven-entry loop registry fights DEC-0303 (one asyncio daemon), DEC-0340, and DEC-0378.

**STRATS under loop engineering** means: STRATS is the on-disk state the next night reads so it does not spend five million candidates relearning a dead end. It is not the overnight process. QMA is that process. QMB is the referee. Build Alpha stays a clipping.

**What this briefing does not do.** Re-sit QMA. Reopen the STRATS `root_path` bind. Start population. Touch MIS. Write `docs/`.

---

## 6. Local sources

| Id | Path | Used for |
|---|---|---|
| S1 | `C:/Users/Mubarak/Documents/brain/brain/Clippings/The Loop Runs While You Sleep.md` | Overnight loop, box vs GA, negative-result moat, no live signals |
| S2 | `C:/Users/Mubarak/Desktop/Stats/README.md` | Portable files+SQLite; pause-before-populate |
| S3 | `C:/Users/Mubarak/Desktop/Stats/STRATS-BUILD-STATE.md` | Present tree; 239; LAYOUT-DEMO |
| S4 | `C:/Users/Mubarak/Desktop/Stats/STRATS-GROUND-STATE.md` §8 | No genetic machinery, executors, run results, agent memory, MIS in STRATS |
| S5 | `C:/Users/Mubarak/Desktop/QMX/workroom/research/2026-09-09_strats-append-to-qmx.md` | Existing KnowledgeSource bind; do not reopen |
| S6 | `docs/components/qma-daemon.md` | Graph/Loop/Skill; Routine; QMB door; Memory vs Knowledge; DEC-0341 |
| S7 | `docs/glossary.md` | Graph Template; Loop; Knowledge; Memory; MIS |
| S8 | `docs/contracts/ct-44-qma-knowledge-source.yaml` | DEC-0318 read-only; cite-copy; no write-back |
| S9 | `docs/components/qmb.md` | B-8 inside-box sampler; B-14 validation ladder; no stored pass/fail |
| S10 | `docs/gap-report.md` | DEC-0378; GAP-0072/0073/0074; GAP-0086 |
| S11 | `_bmad-output/.../ARCHITECTURE-SPINE.md` AD-12/13/16/18/19/22/29 | Inherited; not re-derived |

Web citations [1]–[10] are the ledger below. Claims about QMX/STRATS are from S1–S11, not from vendor blogs.

## Sources

[1] https://addyosmani.com/blog/loop-engineering
[2] https://arxiv.org/html/2608.21884v1
[3] https://www.langchain.com/blog/3-years-of-graph-engineering-with-langgraph
[4] https://www.aibuilderclub.com/blog/graph-engineering-guide-2026
[5] https://www.man.com/insights/what-ai-can-do-for-alpha
[6] https://www.truefoundry.com/blog/graph-engineering-enterprise-guide
[7] https://www.langchain.com/blog/the-art-of-loop-engineering
[8] https://www.ai-street.co/p/inside-man-group-s-alphagpt
[9] https://x.com/buildalpha/status/2095101541002739830
[10] https://buildalpha.com
