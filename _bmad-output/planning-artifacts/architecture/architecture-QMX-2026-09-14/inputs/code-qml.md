# Code inventory — QML (bot-authoring library)

Read-only for the QMX strategy-experimentation architecture sitting. Planning checkout is `main`. Product source inspected via `git show` / `git ls-tree` on branch `integration` at `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`. Architecture only — no implementation, commit, or branch switch.

Lead: `workroom/research/2026-09-14-qmf-qml-understanding.md`. Corpus: `docs/components/qml.md`, `docs/decisions/ADR-0018-qml-bot-authoring-library.md`, spine QL-1..QL-10 at `_bmad-output/planning-artifacts/architecture/architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md`, CT-33 / CT-34, GAP-0085.

Status vocabulary: **reuse | connect | extend | new | undecided**. Evidence: **user-intent | documented-design | source-inspected | behavior-demonstrated**.

**Doc/source reconcile:** CT-33 and CT-34 still stamp `wiring_status: defined-unwired` with the note “no code exists” (`docs/contracts/ct-33-bot-definition.yaml:9`, `docs/contracts/ct-34-confluence.yaml:9`). Integration source **does** implement author types, protocol, conformance, examples, and tests. Prefer source-inspected over the stale contract stamp; class/test existence is not end-to-end host mint proof.

---

## Compact answers (the five questions)

| # | Question | Answer | Class | Evidence |
|---|---|---|---|---|
| 1 | Two-artifact bot (CT-33 + plain Python) — implemented? | **Yes in library source.** Declaration (`BotDefinition` / CT-33 content) + logic identity (`LogicIdentity` source-manifest) + protocol factory/callback + Layer-1/2 gate exist under `qml/`. Host CT-06 envelope mint remains composition-root-owned (OR-06). | **reuse** (QML authoring surface) | source-inspected; example `conformant_bot_usage` drives both halves |
| 2 | Can unregistered ordinary Python run in QMB without `qml` imports? | **Yes by law and by host path.** QML ships `plain_research_bot.py` with zero `qml` imports; QMB `qml_compile` returns `None` for ungoverned cites and skips CT-33 extensions; `admit_ungoverned_tunnel()` keeps tunnel open. | **reuse** | source-inspected (+ documented-design) |
| 3 | Structure-generation / template-slot / mechanism recombination? | **No strategy-structure generation.** Only **declared parameter spaces** (B-8/CT-33) and **producer templates** (complete CT-16/CT-17 minus space-bound values). Condition/predicate fields are `FORBIDDEN_CONDITION_FIELDS`. GAP-0085 typed mechanism decomposition is still Deferred. | **undecided** for GAP-0085; current V1 = **reuse** parameter-space only | source-inspected; documented-design Deferred |
| 4 | Conformance gate vs performance validation | Conformance is **technical never performance** (Layer 1 declaration + Layer 2 determinism/sandbox). `max_acceptable_complexity_score` is in `DROPPED_REGISTRATION_GATES`. Performance/admission thresholds stay GAP-0048/0049 on Book CT-22. | **reuse** (gate) / **connect** (Book bar later) | source-inspected; documented-design |
| 5 | What a user who will not read QMX source can extend | (a) Tunable numbers on a declared CT-33 parameter space (ui-editable flags); (b) plain-Python logic distributions conforming to the factory/callback protocol; (c) reusable CT-34 confluences + producer bindings; (d) operator-minted strategy-family ids (key only). Not: DSL grammar, mechanism recombination kits, or Book authority fields on the family. | **extend** (user-authored bots/params) | documented-design + source-inspected APIs |

---

## Source-linked findings

### Tree (integration)

`git ls-tree -r --name-only integration qml` shows a full distribution: `declaration/`, `families/`, `footprint/`, `logic/`, `protocol/`, `conformance/`, `examples/` (incl. `conformant_bot/`), `tests/` (incl. `plain_research_bot.py`). No `.qml` DSL files; scaffold test forbids them (`qml/tests/test_scaffold.py` via `git show`).

### Q1 — Two-artifact bot implemented?

**Documented design (QL-2 / DEC-0172):** governed bot = CT-33 declaration + versioned plain-Python logic; `.qml` DSL not revived (`docs/components/qml.md:59-62`; ADR-0018).

**Source-inspected:**

- Package identity: `git show integration:qml/src/qml/__init__.py` — “Identity lives on CT-33 content and the logic source-manifest.”
- Declaration half: `qml/src/qml/declaration/bot.py` — `BotDefinition` with six body fields (`strategy_family_id`, `confluence_set`, `parameter_space`, `footprint`, `permitted_exit_intents`, `logic_reference`); `mint_bot_definition`; `FORBIDDEN_BOT_FIELDS` includes `exit_logic`, sizing, venue.
- Logic half: `qml/src/qml/logic/__init__.py` — `LogicIdentity` = distribution + version + source-manifest `fp1`; “a governed bot is exactly two artifacts.”
- Runtime glue: `qml/src/qml/protocol/factory.py` — host constructs factory with `(declaration, assignment, read_surfaces)` → `HostedBot.on_instant`.
- Reference pair: `qml/examples/conformant_bot/bot.py` (logic) + `qml/examples/conformant_bot_usage.py` (declaration + gate + golden slice). Explicit note: dated Bot-kind mint is **defined-unwired in qml**; host stamps CT-06.

**Classification:** **reuse** the two-artifact library surface. Missing piece is **wiring** (host mint / seat), not missing function inside QML.

### Q2 — Ordinary Python without `qml` imports in QMB?

**Documented design:** “an unregistered bot needs zero QML imports to run in QMB or research lanes”; conformance gates citation/seats only (`docs/components/qml.md:19`; QL-1 spine).

**Source-inspected:**

- `qml/tests/plain_research_bot.py` — docstring: “Research-lane bot with zero qml imports… This module must keep importing nothing from qml.” Class `PlainResearchBot.on_instant` only.
- `qml/src/qml/conformance/registration.py` — `admit_ungoverned_tunnel()` → `UngovernedTunnelAccess` with `ticket_required=False`, `tunnel_open=True`; `cite_ungoverned_bot` vs `cite_registered_bot`.
- QMB host: `qmb/src/qmb/config/qml_compile.py:1-7,54-80` — “Ungoverned plain-Python bot cites skip this path — tunnel entry stays ungated”; `ct33_from_record` / `apply_ct33_compiler_extensions` return `None` when no CT-33 body.

**Classification:** **reuse**. Ordinary Python remains legal; graduation is optional (`graduate_to_governed`).

### Q3 — Structure generation / template slots / mechanism recombination?

**What exists (not structure generation):**

1. **Declared parameter space only for search/tuning** — `qml/src/qml/declaration/parameters.py`: types `exact integer | exact rational | categorical | boolean`, bounds/step/default/unit-kind/ui flag; defaults = canonical assignment. QMB `qmb/src/qmb/optimize/space.py` admits a Study **over that one schema** (`study_space_from_bot` / `parameter_space_from_bot`) — varies numbers, does not invent condition graphs.
2. **Producer templates** — `qml/src/qml/footprint/template.py`: “complete CT-16/CT-17 configuration minus only the space-bound parameter values”; `resolve_template` is total/single-valued → one producer fingerprint. These are **binding templates**, not strategy-structure slots or mechanism recombination.
3. **CT-34 legs declare consumption + role**, not predicates — `FORBIDDEN_CONDITION_FIELDS` = `{condition, conditions, when, predicate, satisfied_when, grammar, expression, filter_expr}` (`qml/src/qml/declaration/confluence.py:59-70`). “Condition semantics live in Python logic in V1.”
4. **Families forbid authority/constraint powers** — `FORBIDDEN_AUTHORITY_FIELDS` includes `permitted_timeframes`, `permitted_feature_families`, `mutation_allowances` (`qml/src/qml/families/__init__.py`).

**GAP-0085 (parent QMA Deferred):** typed strategy-mechanism decomposition / recombination (`EntryMechanism`, `ExitMechanism`, `Filter`, `SessionRule`, `PositionRule`, `InvalidationRule` with paper-level provenance). Owner: QML + `qmf-registry`; QMA carries candidates/lineage only (`docs/gap-report.md:228`; QMA spine Deferred row). **No such types appear under `qml/` on integration.** Declarative condition grammar is separately Deferred (QL-5 / DEC-0175).

**Classification:** V1 capability = **reuse** declared parameter spaces + producer binding templates. GAP-0085 remains **undecided** / Deferred — needs an AD if this sitting wants mechanism recombination; otherwise stay Deferred.

### Q4 — Conformance vs performance

**Documented design (QL-8 / DEC-0178):** “conformance is technical, never performance”; ticket for governed evidence + seats; ungoverned keep tunnel (`docs/components/qml.md:94-100`).

**Source-inspected:**

- Layer 1: `lint_declaration` / `LAYER1_CHECKS` — schema, unit-kinds, refs, footprint completeness, template completeness, exit-intent vocabulary.
- Layer 2: AST/import scan (`DENIED_IMPORTS` / denial set clock|io|network|randomness), golden-slice determinism harness (`drive_golden_slice`), snapshot/restore equivalence, permitted intent kinds — pure verdict; hosts own process spawn.
- Registration: `gate_registration` requires both layers; refuses probation/partial; `DROPPED_REGISTRATION_GATES = {max_acceptable_complexity_score, complexity_score}`.
- Prediction linter: four Book-binding checks (footprint_requirements, exit subset, family→exit_policy, stream set vs CT-18) — still **technical compatibility**, not PnL/performance.

Performance / admission **threshold values** stay GAP-0048/0049 on CT-22 Book surfaces (interfaces only in QML).

**Classification:** **reuse** QML conformance as technical gate; **connect** to Book admission bar when thresholds are decided; do not fold performance into QML registration.

### Q5 — Extensibility without reading QMX source

Practical extension levels a non-source-reader can use (once docs/UI expose them):

| Level | What they change | Governed? | Authority |
|---|---|---|---|
| Parameter knobs | Values inside an existing CT-33 `parameter_space` (`ui-editable`) | Experiment overrides in QMB; live/paper seats use **canonical assignment only**; promoting tuned values mints a **new Bot version** | CT-33 / B-8 / DEC-0173 |
| New logic package | Plain Python factory+callback emitting CT-23 intents from declared footprint evidence | Ungoverned until conformance + host mint | QL-7 protocol |
| New confluence | CT-34 legs (role + producer binding and/or child cite) | Reusable registry artifact | CT-34 |
| New family id | Opaque key for Book `exit_policy` attribution | Key only — no constraint powers | QL-6 |
| Book/BMS templates | Risk, admission, footprint_requirements, exit_policy | Outside QML; Risk-owned | CT-22 / CT-27 |

They **cannot** (in V1 without new design): write a `.qml` DSL; declare leg predicates in the declaration; recombine typed Entry/Exit/Session mechanisms (GAP-0085); put sizing/`exit_logic`/venue commands on the bot; register without both conformance layers if they want governed citation.

Public author surface is the `import qml` API exported from `__init__.py` (mint helpers, protocol, conformance) plus QMB CLI/doors that already call `parameter_space_from_bot`.

---

## (1) What already exists

- Full `qml` distribution on integration: declaration (CT-33/CT-34 author types), families, footprint (+ producer templates + completeness), logic identity, runtime protocol, conformance (L1/L2/prediction/registration/graduation), examples, tests.
- Two-artifact model end-to-end in library + reference conformant bot.
- Explicit ungoverned plain-Python path (QML test module + QMB compile skip + tunnel admit).
- One authoritative parameter-space schema consumed by QMB optimization Studies.
- Technical conformance ticket; complexity/performance registration gates dropped.

## (2) Missing wiring vs missing function

| Item | Kind |
|---|---|
| Host composition-root CT-06 Bot-kind mint (`WriterId`, stamped envelope) | **Missing wiring** (OR-06 by design; QML returns fingerprintable content only) |
| Node/QMB seat runtime binding CT-28 / AD-41 active\|benched | **Missing wiring** outside QML (citation types only in QML) |
| Hardened OS-level Layer-2 confinement | **Deferred wiring** (V1 = scan + capability starvation + host process isolation) |
| Declarative condition/predicate grammar / Monaco / agent-codegen | **Deferred function** (compiles to same two artifacts when built) |
| GAP-0085 typed mechanism decomposition & recombination | **Missing function** (Deferred; not present in source) |
| Admission-bar / performance threshold **values** | **Missing Book content** (GAP-0048/0049), not QML library gaps |
| Stale CT-33/CT-34 `wiring_status: defined-unwired` / “no code exists” | **Doc drift** vs integration source |

## (3) Recommended architectural ownership

| Concern | Owner | Class |
|---|---|---|
| CT-33/CT-34 authoring, footprint/templates, protocol, conformance verdict | **COMP-QML** | reuse |
| Kind records, lineage, fp1 registry envelope | **qmf-registry** (host mints) | connect |
| Book admission / exit_policy / footprint_requirements / performance bar | **qmf-risk** (CT-22) | connect |
| Experimentation host: plain-Python bridge, CT-33 compile stamps, Study spaces, sandbox runner | **QMB** | connect / reuse |
| Seat loop hosting QL-7 | **QMN** (later) | connect |
| Strategy candidates + lineage only; no redefinition of Bot nouns | **QMA** | connect |
| GAP-0085 mechanism types if ever minted | **QML + qmf-registry** (per gap), not QMA | undecided / Deferred |

Standing law reminder: QML never imports `qmf-venue`; ordinary Python always legal; bots trade, Books control, BMS accounts, human promotes.

## (4) Open questions — AD vs Deferred

| Question | AD now? | Notes |
|---|---|---|
| Keep GAP-0085 Deferred (no Entry/Exit/Session mechanism recombination in this sitting)? | Prefer **stay Deferred** unless experimentation architecture *requires* structure search beyond parameter grids | Parent already deferred; StrategyHandle/ExperimentSpec shaped to carry later |
| Is “strategy generation” = sweep CT-33 parameter spaces only, or also mutate Python logic / confluence graphs? | **Needs AD** if QMX claims structure search | Source today supports parameter spaces only; logic/confluence edits are new Bot/confluence identities, not a recombination kit |
| Who runs Layer-2 process isolation for research graduation (QMB vs platform)? | Can stay as existing host split (DEC-0178) | Function exists; wiring is host composition |
| Refresh CT-33/CT-34 `wiring_status` after factory landing? | Doc-factory hygiene, not architecture AD | Reconcile stale “no code exists” |

---

## Citations (primary)

- `git show integration:qml/src/qml/__init__.py`
- `git show integration:qml/src/qml/declaration/bot.py`
- `git show integration:qml/src/qml/declaration/confluence.py` (`FORBIDDEN_CONDITION_FIELDS`)
- `git show integration:qml/src/qml/declaration/parameters.py`
- `git show integration:qml/src/qml/logic/__init__.py`
- `git show integration:qml/src/qml/protocol/factory.py`, `.../contract.py`
- `git show integration:qml/src/qml/footprint/template.py`, `.../manifest.py`
- `git show integration:qml/src/qml/conformance/registration.py`, `.../harness.py`
- `git show integration:qml/tests/plain_research_bot.py`
- `git show integration:qml/examples/conformant_bot/bot.py`, `.../conformant_bot_usage.py`
- `git show integration:qmb/src/qmb/config/qml_compile.py`, `.../optimize/space.py`
- `docs/components/qml.md:16-100`
- `docs/decisions/ADR-0018-qml-bot-authoring-library.md`
- `docs/contracts/ct-33-bot-definition.yaml`, `docs/contracts/ct-34-confluence.yaml`
- `_bmad-output/.../architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md` (QL-1..QL-10)
- `docs/gap-report.md:228` (GAP-0085)
- `workroom/research/2026-09-14-qmf-qml-understanding.md`
