# Cut — generation (parameter search vs structure)

Planning checkout: `main` `430fb7d`. Product inspected: `integration` `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` via `git ls-tree` / `git show` only. No checkout, commit, or implementation. Evidence: `source-inspected` unless marked `documented-design`. Class/test existence is not end-to-end runtime proof. Stale `wiring_status: defined-unwired` on CT-33/CT-34/CT-47 is documentation drift, not absence of library source.

Leads only: `workroom/research/2026-09-14-backend-baseline.md`, `2026-09-14-qmb-understanding.md`, `2026-09-14-qmf-qml-understanding.md`; sibling inventories `inputs/code-qmb.md`, `inputs/code-qml.md`, `inputs/donor-strategyquant.md`.

**Question:** Does QMX already vary declared parameters (QMB optimize/sweep, QML parameter schema), and is typed strategy-mechanism **structure** generation (GAP-0085, StrategyQuant templates) genuinely missing?

**Answer:** Yes, and yes. Declared-parameter variation is a shipped library. Inventing condition/logic **structure** is absent. Do not sell TPE/`propose_generation` or `qmb data generate` as strategy generation.

| Capability | Class | Evidence | Owner if built |
|---|---|---|---|
| CT-33 declared parameter space (one schema) | **reuse** | source-inspected | COMP-QML authors; QMB B-8 reads |
| QMB TPE optimize over that space | **reuse** | source-inspected | COMP-QMB |
| QMB Cartesian sweep (instruments × BarSpecs × parameter values) | **reuse** (library); CLI `sweep.count` only | source-inspected | COMP-QMB |
| Producer templates (fixed vs space-bound **numbers**) | **reuse** | source-inspected | COMP-QML footprint |
| CT-17 market/causal structure (`qmf-structure`) | **reuse** (different noun) | documented-design | COMP-QMF-STRUCTURE — not bot generation |
| CLI coverage of sweep batch/rank / robustness | **connect** (missing wiring of search) | source-inspected | COMP-QMB doors |
| SQ RandomCondition / structure slots on CT-34 | **new** (missing function) | source-inspected (negative) | COMP-QML declaration |
| Typed Entry/Exit/Filter/Session/Position/Invalidation mechanisms (GAP-0085) | **new** (missing function); QMA **refuses** the nouns | source-inspected | COMP-QML + `qmf-registry`; QMA carries candidates only |
| Random/genetic/agent structure **generator** | **new** (missing function) | source-inspected (negative) | QML authors CT-33/34 + logic; QMB **runs**; QMA lineages |
| Generator algorithm (random vs genetic vs codegen) | **undecided** / can stay Deferred | documented-design | later QML increment after ownership AD |
| `.qml` DSL / predicate grammar | Deferred (not this cut) | documented-design | DEC-0172 / DEC-0175 |

**Topic verdict:** **new** for structure generation. Parameter search is **reuse** and is not generation.

---

## Compact findings

### 1. QMX already varies declared parameters

**Documented design.** QML adds the missing uniformities “declared footprint” and “declared parameter space”; B-8’s optimizer consumes **one** schema, never a QMB-local copy (`docs/components/qml.md` QL-1/QL-3; `docs/components/qmb.md` B-8; DEC-0173, DEC-0183). Types: `exact integer | exact rational | categorical | boolean`, bounds, step, mandatory default, optional hard-constraint filters, AD-40 unit-kind. Defaults = **canonical assignment**. Governed live/paper seats execute canonical assignment only; a swept non-default is a B-3 run-spec override; promoting tuned values mints a **new Bot version**.

**Source-inspected (integration).**

- Schema: `git show integration:qml/src/qml/declaration/parameters.py` — module docstring “One schema, never two (DEC-0173, DEC-0183)”; `ParameterType`, `coerce_parameter_space`, `canonical_assignment_of`.
- Study space: `git show integration:qmb/src/qmb/optimize/space.py` — `study_space_from_bot` / `StudyParameterSpace` “never redeclares the schema itself”; identity-bearing `STUDY_SPACE_KEY` in the resolved run-config.
- Thin front: `qmb/src/qmb/optimize/__init__.py:371` `parameter_space_from_bot` — “A swept non-default assignment is a B-3 run-spec override, never a silent new default.”
- Sampler: `git show integration:qmb/src/qmb/optimize/sampler.py` — `SAMPLER_FAMILY="tpe-class"`, `SAMPLER_GENERATOR="TPESampler"`, `SAMPLER_STEPPING="generation-barrier"`. `propose_generation` (`sampler.py:567`) is a pure function of `(declared space, seed, prior trial results, generation index) → ParameterBatch`. History is the ledger view (`SAMPLER_CONSULTS_OPTUNA_STORE=False`). Adaptive parallel `ask` without `tell` is refused. Word **generation** here means TPE **batch index**, not invented strategy structure.
- Sweep: `git show integration:qmb/src/qmb/sweep/axes.py` — axes `instruments | timeframes | parameters{name: values[]}`; `expand_sweep` Cartesian product; each combo is one isolated run of the **same** bot. `run_sweep_batch` / `rank_sweep` exist in library (`sweep/batch.py:230`, `sweep/rank.py`).
- CLI: `qmb/src/qmb/doors/cli/tree.py` `_COMMAND_TREE`: `optimize: (run, space, estimate)`, `sweep: (count,)`. `invoke_optimize_run` is “one optimize trial is a first-class backtest run.” API door re-exports `propose_generation`, `parameter_space_from_bot`, `run_sweep_batch`.

**What this is not.** Optimize/sweep never choose indicators, comparators, AND/OR arity, or Python logic. Changing logic or a CT-34 leg is a new Bot/confluence `fp1`, not a trial.

### 2. Producer templates are number holes, not structure holes

`git show integration:qml/src/qml/footprint/template.py` (lines 1–6): a template is a **complete** CT-16/CT-17 configuration minus only space-bound parameter values; `resolve_template` is total and single-valued → one configured-producer fingerprint.

StrategyQuant’s template is the other axis: named **RandomCondition / RandomValue / RandomAction** slots that the Builder fills with **which block** (CCI vs RSI vs Aroon), then optionally randomizes that block’s period (`inputs/donor-strategyquant.md`, official SQ templating/random-groups docs). QMX has SQ’s second axis (fixed vs space-bound numbers). QMX does **not** have the first (structure slots).

CT-34 legs declare `role + producer binding and/or child cite`, never predicates:

```59:70:qml/src/qml/declaration/confluence.py
FORBIDDEN_CONDITION_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "condition",
        "conditions",
        "when",
        "predicate",
        "satisfied_when",
        "grammar",
        "expression",
        "filter_expr",
    }
)
```

(Path on integration; cited as `git show integration:qml/src/qml/declaration/confluence.py`.) Condition WHEN lives in Python (DEC-0175). Families refuse ArchetypeSpec constraint powers (`FORBIDDEN_AUTHORITY_FIELDS` includes `permitted_feature_families`, `mutation_allowances` — `git show integration:qml/src/qml/families/__init__.py:54`).

Do **not** confuse this with **CT-17 causal/market structure** (`COMP-QMF-STRUCTURE`): swings/zones/lifecycle folds the run loop already consumes. That is not strategy-mechanism generation.

### 3. Typed strategy-mechanism structure generation is genuinely missing

**GAP-0085** (`docs/gap-report.md:228`): “What is the typed strategy-mechanism decomposition (EntryMechanism, ExitMechanism, Filter, SessionRule, PositionRule, InvalidationRule with paper-level provenance)?” Owner: QML + `qmf-registry`; QMA carries candidates and lineage. Revisit was “at the QML sitting” — that sitting closed GAP-0047 (two-artifact bot) and **did not** mint GAP-0085 nouns (`docs/AGENTS.md` QML bullet; `docs/components/qml.md` Deferred fence: predicate grammar, agent-codegen, mutation allowances).

**Negative source search** on `integration` (`git grep` over `qml/`, `qmb/`, `qmx-agents/`, `packages/`): no `EntryMechanism` types under `qml/`; no builder/structure-generator module; the only `generat*` product files are QMB **data** synthetic series (`qmb/src/qmb/data/generate.py`) and TPE `propose_generation`. QMA **refuses** the nouns:

- `git show integration:qmx-agents/packages/qma-core/src/qma/core/ports/experiments.py:6-7,78-86,147-179` — `GAP_0085_STRATEGY_MECHANISMS`; `_refuse_gap_0085` on `ExperimentSpec.try_create` / `with_change`; “QMA carries candidates and lineage edges only.”
- Tests: `qmx-agents/packages/qma-core/tests/test_experiment_spec.py` extra/`mechanisms` keys.
- `docs/contracts/ct-47-qma-experiment-spec.yaml:13` lists GAP-0085; purpose: QMA does not redefine Strategy/Bot.

SQ donor shape (fetched 2026-09-14, `inputs/donor-strategyquant.md`): random pick of building blocks into entry/exit rules; genetic crossover/mutation of **blocks**; template placeholders. Official SQ itself splits Builder (structure) from Optimizer (declared params) from Cross-checks (robustness). QMX already has the last two as QMB B-8 / B-14. The first is absent.

Agent-codegen is reserved as compiling **to the same two artifacts** (`docs/components/qml.md` QL-2) — that is a future filler of QML outputs, not a second bot language and not a QMB sampler family.

### 4. Homonym traps (must stay named)

| Phrase | Actual meaning | Not |
|---|---|---|
| QMB `propose_generation` / `SAMPLER_STEPPING=generation-barrier` | TPE trial **batch** over declared numbers | Inventing conditions |
| `qmb data generate` | Store-tainted synthetic series; `world=simulated`; L20 | Strategy generation |
| CT-17 “structure” | Market/causal producers | Strategy-mechanism atoms |
| Sweep “parameters” axis | Listed values for **named** CT-33 knobs | New knobs or new logic |
| QMA `StrategyHandle` | Content-addressed **candidate** | Mechanism vocabulary |

---

## (1) What already exists

- One authoritative CT-33 parameter-space schema in QML; QMB Studies and sweeps read it (`study_space_from_bot`, `parameter_space_from_bot`).
- Adaptive TPE search (Optuna adapter, `n_jobs=1`, ledger history, exact conversion of sampled floats, `role=trial`) plus Cartesian sweeps and anti-overfit sensitivity — **parameter search**.
- Producer templates: complete CT-16/CT-17 minus space-bound values.
- Two-artifact bots (CT-33 + plain Python); ungoverned tunnel; conformance technical-never-performance.
- QMA ExperimentSpec already splits **code** change (`git:commit:<40-hex>`) vs **resolved-config** change (parameter/config fp1) and refuses git-branch-per-parameter (DEC-0376) **and** GAP-0085 mechanism keys.
- Robustness ladder (WF, MC, significance) is a third activity, already QMB B-14 — not generation.

## (2) Missing wiring vs missing function

| Missing wiring (function present) | Missing function |
|---|---|
| CLI does not expose `run_sweep_batch` / `rank_sweep` (only `sweep.count`) | Structure/template **generator** that authors new CT-33/CT-34 and/or logic-source artifacts |
| Robustness ladder library-only (no CLI group) | GAP-0085 typed mechanism kinds (EntryMechanism, …) — absent in QML; refused in QMA |
| Host composition-root CT-06 Bot mint (OR-06; QML returns fingerprintable content) | CT-34 structure slots (RandomCondition-class holes); predicate/WHEN grammar (Deferred DEC-0175) |
| CT-33/CT-34 YAML still say `defined-unwired` / “no code exists” while `qml/` implements author types | Genetic-of-structure (SQ islands/crossover) — no module; algorithm not chosen |
| CT-47 door transport is recording-shaped in QMA (connect cut, not this one) | Allow-list of formula_ids/comparisons **for a generator** (catalog exists as CT-16 pool, not as a random-block DSL) |

Search wiring gaps must not be filed as “generation not started.” Generation has no function to wire.

## (3) Recommended architectural ownership

| Concern | Owner | Class |
|---|---|---|
| Vary declared CT-33 numbers; rank trials; robustness of a **fixed** bot | **QMB** | reuse |
| Author Bot/confluence/logic candidates; parameter schema; producer templates; conformance | **QML** | reuse now; **extend** only if structure slots are minted later |
| Kind records, fp1, lineage | **qmf-registry** | connect |
| Indicator/formula **pool** | **qmf-indicators** (CT-16) | reuse as pool, not as DSL |
| Market structure objects | **qmf-structure** (CT-17) | reuse — different noun |
| `StrategyHandle` / ExperimentSpec / lineage; never mechanism nouns | **QMA** | reuse refuse-set; connect door |
| Live seats | **QMN** | not a research generator |

If/when structure generation ships: **QML authors** new CT-33/CT-34 content and/or logic-source artifacts (ungoverned Python legal; graduation = conformance + host mint); **QMB only runs** the resulting bots (optimize/sweep remain parameter search **on that bot**); **QMA** holds candidates and CT-07 edges and never mints GAP-0085 nouns. Do not start a generator inside QMB’s tunnel. Do not revive `.qml`. Do not copy SQ’s genetic engine (DEC-0013). SQ RandomCondition is a **donor shape**, not a schema to clone.

## (4) Open questions — AD vs Deferred

**Need one AD now (this cut’s invariant):**

**Generation is not search.** Search = vary declared CT-33 parameters (same Bot `fp1`; assignment is a run-spec override; QMB optimize/sweep). Generation, if built = author **new** CT-33/CT-34 and/or logic-source artifacts via QML (new Bot `fp1`). QMB never authors bots. QMA never mints mechanism nouns. TPE `propose_generation` is not strategy generation. Ownership of GAP-0085 vocabulary is QML + `qmf-registry` (already stated DEC-0313); this sitting must **stop leaving ownership undecided** so two factory lanes cannot invent two products (a QMB structure-sampler vs a QMA mechanism palette vs a third CT-34 predicate language).

Without that invariant, two independent builders can incompatibly choose: (a) a second QMB sampler family that mutates confluence/logic, (b) ExperimentSpec `mechanisms=` as the generated object, (c) RandomCondition fields on CT-34 that silently become a second language. Those three disagree on identity (what fingerprints), evidence (trial vs new Bot), and graduation.

**Can stay Deferred (not this AD’s payload):**

- First generator algorithm (random placeholder-fill vs Python-logic synthesis vs agent-codegen compiling to the two artifacts).
- Whether to mint GAP-0085 kinds in V1, slim the set, or keep the refuse-set until a QML increment with a **non-obsolete** revisit trigger (the “revisit at the QML sitting” trigger is already consumed).
- Genetic-of-structure vs random-only (SQ documents later generations **break** template control — `inputs/donor-strategyquant.md` §5/§3).
- Declarative predicate grammar / Monaco (DEC-0172/0175).
- GAP-0049 search-quality thresholds; GAP-0048 fidelity; CLI completeness of existing search.

**PRD note (not an AD):** existing QML FRs cover two-artifact authoring; they do not yet name generation-vs-search. Update the PRD; do not treat TPE as FR coverage for F01-style generation.

---

## Citations (primary)

- `git show integration:qml/src/qml/declaration/parameters.py`
- `git show integration:qml/src/qml/declaration/confluence.py` (`FORBIDDEN_CONDITION_FIELDS`)
- `git show integration:qml/src/qml/footprint/template.py`
- `git show integration:qml/src/qml/families/__init__.py` (`FORBIDDEN_AUTHORITY_FIELDS`)
- `git show integration:qmb/src/qmb/optimize/{__init__,space,sampler}.py`
- `git show integration:qmb/src/qmb/sweep/{__init__,axes,batch,rank}.py`
- `git show integration:qmb/src/qmb/doors/cli/tree.py`
- `git show integration:qmx-agents/packages/qma-core/src/qma/core/ports/experiments.py`
- `docs/components/qmb.md` B-8 / B-12; `docs/components/qml.md` QL-3 / QL-4 / QL-5 / Deferred fence
- `docs/contracts/ct-33-bot-definition.yaml` (parameter_space one-schema; `wiring_status` stale vs source)
- `docs/contracts/ct-34-confluence.yaml` (WHEN in logic; predicate grammar Deferred)
- `docs/contracts/ct-47-qma-experiment-spec.yaml` (GAP-0085)
- `docs/gap-report.md:228` GAP-0085
- `docs/AGENTS.md` QML ratified content; QMA money-path
- `_bmad-output/.../inputs/donor-strategyquant.md` (SQ Builder ≠ Optimizer)

*Architecture only. Product cited at `integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`.*
