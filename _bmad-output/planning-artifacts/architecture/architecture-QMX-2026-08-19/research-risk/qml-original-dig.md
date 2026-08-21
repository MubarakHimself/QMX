---
cluster: risk-sitting / QML-original-dig
question: "look in QML, the original version — the actual QML meant to help us have uniform bots across everything. Was it actually considered?"
sources: QMX-discussion (oldest vault, 2026-04..07) + QMX (newer wiki/GitBook)
precedence applied: current QMX rulings > old wiki (2026-07 planning delta) > GitBook baseline > QMX-discussion (oldest vault)
status: evidence dossier — read-only dig, nothing ruled here
date: 2026-08-20
safety-note: all cited paths under C:/Users/Mubarak/Documents/... are old-generation inert evidence, read-only
---

# QML — the original "uniform-bot" library: evidence dig

## Direct answer to the operator (was it actually considered?)

**Yes — extensively, and it was the single most load-bearing idea in the old
vault.** QML ("QML Shared Contract Library" / "QML Custom Library Layer", the "L"
reads as *Library*, never spelled out as a markup language) was designed as the
one layer every component imports and nothing imports below — its explicit job
was to make bots **uniform and honestly comparable**. A bot was not free-form
code; it was one canonical `BotSpec` built from the formula
`Bot = Archetype + Features + Filters + Risk + Execution + Exit Logic`, with a
**first-class `exit_logic` field**. Exit *execution* was made **system-owned and
globally uniform** (one asymmetric SL/TP authority; "bot-owned SL/TP overrides
are rejected"). So the old world already split what the current DEC-0067 brief
calls declare-vs-own-vs-execute. The uniform-bot machinery was **considered in
full and then consciously reshaped, not discarded**: in the newer generation
AD-32 *keeps* QML as "the **bot-authoring language/library, the MQL5 analog**" but
**narrows it to the bot-to-book boundary** to stop it "re-expanding into a uniform
cross-component layer." So QML the *authoring language* the operator remembers
survived; what was dropped is the *uniform cross-component contract layer* and the
concrete `BotSpec`/`exit_logic` types inside it — QML is now an in-scope shell with
zero registered interfaces (GAP-0013), `BotSpec` is a deferred stub, and the clash
report + DEC-0024 explicitly kill "any notion that the SL/TP service is globally
uniform across books" in favour of per-book (per-strategy-family) declared
stop/exit policy. Net: the mechanism (`ExitLogicRef` = module + config; template
grammar + per-instance values; system-owned executor) is a ready design donor for
today's question; only *global* uniformity was retired, and the exit mechanics
themselves are still open (PE-3/PE-7/PE-8, DEC-0067/GAP-0040).

---

## 1. What QML WAS in the original design

### 1.1 Name, position, purpose

- **Name / expansion.** Consistently "QML — Shared Contract Library"
  (`QMX-discussion/02-Components/00-QML-shared-library/00-QML-overview.md:1`,
  `:144`) and, in the GitBook certification pass, **"QML Custom Library Layer"**,
  kind `library` (`QMX-discussion/outputs/qml-spec.md:14`). The PRD glosses it as
  "QML = internal shared contract library imported by trading-node, backend-node"
  (`QMX-discussion/bmad-docs/planning-artifacts/prd.md:49`). No document expands
  QML as an acronym; the "L" is *Library*. It is **not** a markup/DSL — it is a
  typed-contract Python package (`qml.*`,
  `qml-architecture.md:265`: "Single library, namespaced package `qml.*`").
- **Position.** "the **load-bearing stratum** of the QUANTMIND architecture …
  components depend on QML; QML depends on nothing above it"
  (`00-QML-overview.md:9`). Dependency graph: `COMP-EXAM depends_on [COMP-MIS-ARCHIVE,
  COMP-QML]`; `COMP-ADAPTER depends_on [COMP-QML]`; QML depends on nothing
  (`qml-spec.md:26-27`).
- **Six/seven sub-packages** (`00-QML-overview.md:11-23`): (1) Domain types,
  (2) Bridges, (3) Feature modules, (4) FeatureBridge, (5) Runtime,
  (6) Extension Points + (7) Compiler/Validator.

### 1.2 The uniformity mechanism (this is the heart of the operator's question)

Uniformity was achieved by **four reinforcing devices**, not a config file:

1. **A single canonical import.** "A bot imports from QML and only from QML. It
   never imports from another component" (`00-QML-overview.md:101`). Operator
   vision, quoted in the architecture: "QML keeps **organisation** between
   components, agents, and bots — a single `BotSpec` import is the unifier;
   nesting prevents the flat-blob information leak"
   (`qml-architecture.md:232`).
2. **Bots are consumers, not authorities.** "A bot does not compute its own risk
   size, does not compute its own stops, does not evaluate kill-switch state"
   (`00-QML-overview.md:72`). The payoff is the uniformity rationale, verbatim:
   > "This design is what allows the system to **compare bots honestly**. Because
   > every bot's intent is evaluated by the **same deterministic risk authority
   > against the same formula**, the performance differences between bots are
   > attributable to signal quality, not to differing self-assessment of risk or
   > position sizing." (`00-QML-overview.md:74`)
3. **Typed contracts at every boundary** (~22 canonical Pydantic-v2 domain
   types, additive versioning) — "No component defines its own parallel types"
   (`00-QML-overview.md:13`; type list `qml-spec.md:57-63`). Versioning contract:
   add fields with safe defaults, never silently rename, unknown enum → most
   conservative value (`01-QML-domain-types.md:13-19`).
4. **A machine-enforceable gate.** The QML Compiler/Validator (Schema Validator +
   Sandbox Executor) "replace[s] prompt-based discipline with hard guarantees"
   (`00-QML-overview.md:23`); every `BotSpec`/`ArchetypeSpec` is CI-validated so
   "malformed specs cannot reach `main`" (`06-QML-compiler-validator.md:85`).
   Anti-sprawl gate `max_acceptable_complexity_score` (`qml-types-catalogue.md:1922`).

### 1.3 What a bot definition looked like (verbatim)

The **flat** original `BotSpec` (fields table, `01-QML-domain-types.md:73-88`):
`id, archetype, symbol, symbol_scope, timeframe(M1..D1), sessions, features
(pinned FeatureRef), confirmations, execution_profile, capability_spec, runtime,
evaluation, mutation, parent_id`. Immutable identity; a mutation = **new `id` +
`parent_id`** (`01-QML-domain-types.md:65`, `:71`).

The **locked, nested** `BotSpec` (BMAD architecture delta, ADR-007) reorganised
it into four frozen sub-models and **added `filters` + `exit_logic` as
first-class fields** (`qml-architecture.md:608-647`, verbatim):

```python
class BotSpecStatic(BaseModel):
    archetype: ArchetypeRef
    symbol: str
    symbol_scope: list[str]
    timeframe: TimeframeEnum
    sessions: list[SessionWindowRef]
    features: list[FeatureRef]
    confirmations: list[ConfirmationRef]
    filters: list[FilterRef]                # NEW: first-class per GPT bot-formula
    exit_logic: ExitLogicRef                # NEW: first-class per GPT bot-formula
    execution_profile: ExecutionProfile
    capability_spec: CapabilitySpec
# + BotSpecRuntimeView, BotSpecEvaluationSnapshot(complexity_score float 0..100),
#   BotSpecMutationAllowance(allowed_feature_mutations, locked_components, unsafe_mutation_zones)
class BotSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str; parent_id: str | None
    static: BotSpecStatic
    runtime_view: BotSpecRuntimeView
    evaluation_snapshot: BotSpecEvaluationSnapshot
    mutation_allowance: BotSpecMutationAllowance
```

Provenance of the delta: "`filters` and `exit_logic` were made first-class fields
per ADR-007 cascade from the GPT `Bot = Archetype + Features + Filters + Risk +
Execution + Exit Logic` formula" (`qml-types-catalogue.md:189`; the flat version
in `07-bot-registry-and-lifecycle` is explicitly labelled "the pre-architecture
version; the nested version here is the locked shape", `qml-types-catalogue.md:121`).
The GPT source calls this decomposition "probably the single most influential
design phrase for the framework"
(`qml-architecture-context-gpt-extract.md:39-43`, citing
`gpt-trading-algorithm-research.md:983`).

### 1.4 How bots stayed uniform across strategies

- **Archetype template governs the family.** `ArchetypeSpec` declares
  `permitted_feature_families`, `required_feature_families`,
  `permitted_timeframes`, `permitted_mutation_types`, `capability_constraints`,
  `average_rr` (`01-QML-domain-types.md:132-144`). A `BotSpec` "extends" its
  archetype; the Capability Validator blocks incompatible feature/archetype
  combos (`01-QML-domain-types.md:169-199`).
- **Agents propose; deterministic services dispose.** Domain Types and Bridges
  are **human-only**; only feature-module *variants* are agent-mutable, behind
  the Compiler (`00-QML-overview.md:82-91`; `qml-spec.md:132-142`).
- **Exit/risk mechanics are locked against mutation.** WF2 "must NOT mutate: SL
  mechanics, TP mechanics, position sizing mechanics, account/risk rules, global
  kill-switch logic, portfolio exposure logic"; it *may* mutate entry logic,
  confirmations, filters, feature selection
  (`qml-architecture-context-gpt-extract.md:56-58`, citing
  `gpt-trading-algorithm-research.md:19191-19209`). This is exactly how exits
  stayed uniform: the *declaration slot* existed, but the *mechanics* were frozen.

---

## 2. QML ↔ Books/BMS: exit methods, risk interface, stop-out semantics

### 2.1 How a bot declared its exit method — `ExitLogicRef` (verbatim)

The exit method is declared as a **module reference + a free-form config dict**
(`qml-types-catalogue.md:2319-2337`):

```python
class ExitLogicRef(BaseModel):
    """Reference to the exit logic module. First-class field in BotSpecStatic per ADR-007 cascade."""
    model_config = ConfigDict(frozen=True)
    module_id: str = Field(..., min_length=1)   # set-by: Bot author; read-by: Exit evaluator
    config:    dict[str, Any] = Field(default_factory=dict)  # per module schema
```

This is the directly reusable atom: **`module_id` picks the exit method; `config`
carries the per-strategy parameters** (a `FeatureModule.role = "exit"` "drives
exit logic … Used in BotSpecStatic.exit_logic", `qml-types-catalogue.md:3932`).
`execution_profile` separately carries "Order-type preferences, slippage
tolerance, partial-fill behaviour, **minimum RR threshold before entry**"
(`07-bot-registry-and-lifecycle.md:43`).

### 2.2 The risk interface a bot declared (it did NOT size itself)

`TradeIntent` is "the **only** mechanism through which a bot participates" and
**intentionally omits volume** — sizing belongs to the risk authority; the bot
carries only `direction` + `proposed_sl_pips` (advisory)
(`01-QML-domain-types.md:296-315`). The risk verdict returns as `RiskAuthorization`
with a full `RiskEnvelope` clamp trace (`01-QML-domain-types.md:319-359`).

### 2.3 Stop-out semantics — the OLD asymmetric SL/TP authority (system-owned)

The old vault had a dedicated component `03-execution-safety-and-asymmetric-sl-tp`
(file not present in this corpus; fully extracted in
`QMX-discussion/outputs/sltp-authority-spec.md`). Its mandate:

- **System-owned, never per-bot.** "Bots do not own, compute, or amend stops —
  they publish intent, then relinquish control. Rationale: **one consistent
  asymmetric policy; uniform kill-switch overrides with no per-bot wiring**"
  (`sltp-authority-spec.md:21-25`). Restated as FR17: "asymmetric SL/TP authority
  … **Bot-owned SL/TP overrides are rejected**"
  (`bmad-docs/planning-artifacts/epics.md:109`; `prd.md:891`).
- **The asymmetric policy** (`sltp-authority-spec.md:27-48`; summary
  `01-system-overview.md:16`): **TP trails continuously** on
  `continuation_prob > CONTINUATION_THRESHOLD` (no hard cap); **SL is one-shot to
  breakeven at +1R, never reset** for the life of the position; **losers hit
  their full original stop** so a clean 1R loss unit feeds the breaker.
- **Contracts:** bot → authority `PositionIntent`; authority → broker
  `AmendInstruction(reason ∈ {BREAKEVEN, TP_EXTENSION, KILL_SWITCH_OVERRIDE},
  source: "sltp_authority" always, priority: KS=0 / normal=10)`
  (`sltp-authority-spec.md:52-61`). In the type catalogue this shows as
  `SLTPSubscriptionRequest(initial_sl_pips, initial_tp_pips, trail_trigger_pips)`
  and `SLTPAmendment` (`qml-types-catalogue.md:2596-2628`).

### 2.4 Multiple exit methods — the exit taxonomy

There is **no single "multi-leg ladder / scale-out" bot type** in the old vault
(a corpus-wide sweep for scale-out/partial/TP1-TP2/runner returned only the
`execution_profile.partial_fill_policy` = REJECT/ACCEPT partial *fills*, not
partial *exits*, `qml-types-catalogue.md:1852`). Instead, "multiple exit methods"
lives as an **enumerated set of ways a position can close** — `CloseReason`
(`qml-types-catalogue.md:3371-3386`, verbatim):

```python
class CloseReason(StrEnum):
    SL_HIT; TP_HIT; TRAILING_SL_HIT; MANUAL_CLOSE;
    KS_FORCED_CLOSE; SESSION_CLOSE; HEDGE_CLOSE; BROKER_CLOSE
```

(the flat `TradeLog.close_reason` earlier used
`SL_HIT|TP_HIT|KILL_SWITCH_FLATTEN|MANUAL|TIMEOUT`, `01-QML-domain-types.md:427`).
So a bot ran **one declared `exit_logic` module** whose runtime behaviour (BE
move, TP trail, trailing-SL, session close, hedge close, forced flatten) produced
these different close reasons — the "multiple exit methods" are behaviours of the
single system-owned policy, parameterised per bot, not independently owned legs.

### 2.5 The Books/BMS relationship — the clash is already written up

The most decision-relevant document for this sitting is
`QMX-discussion/outputs/clash-report-sltp-vs-book.md` (Claude analysis,
2026-07-18, book-template/scalper-book/BMS/treasury read in full). Verdict up
front:

> "the new system has **NO stop-management component** — and that absence is not
> neutral. The book's money math silently assumes answers about stop behavior in
> at least three load-bearing places… they are a hole the book system is standing
> over." (`clash-report-sltp-vs-book.md:6-10`)

Key couplings between exits/stop-out and the book/BMS money system:

- **The breaker counts "stop-outs" — but stop policy DEFINES a stop-out.** Under
  the old asymmetric policy a +1R trade exits at breakeven (0R "BE-out") while
  true losers exit at full 1R. "*does a breakeven exit count toward
  `scalper_breaker_threshold`?* … Either answer changes book behavior; neither is
  written down. **This must be a ruling, not an inheritance.**"
  (`clash-report-sltp-vs-book.md:36-45`). Scalper book "**benches after
  consecutive stop-outs**" — `registry:scalper_breaker_threshold` = consecutive
  stop-outs to paper (DEC-0032) (`:19-22`).
- **Lbar (mean loss R) is measured at exam; stop policy is part of the
  measurement.** `offer_per_seat = D/(B·b·Lbar)` prices seats off characteristic
  loss; parity of stop policy between exam-replay and live is required
  (`clash-report-sltp-vs-book.md:46-54`).
- **Two authorities can now close a position** (KSA effects + the leash's
  hold-time force-flat) "but nothing defines how force-flat, KSA closures, and
  SL/TP amendments interleave … the old priority model is a good donor"
  (`clash-report-sltp-vs-book.md:55-63`).
- **BMS** "never trades, sizes, or reaches inside a book (DEC-0045)"; it owns
  journals (Records) (`clash-report-sltp-vs-book.md:23`; `qml-spec.md:155`).

---

## 3. Carried forward or dropped in later generations (dispositions)

**Disposition = the NAME/ROLE survived (QML is still "the bot-authoring
language"), but the uniform-bot MACHINERY was dropped/redistributed and the
global uniformity of exits was explicitly retired.**

The subtle, important correction for the operator: in the newer generation QML is
**not** dead and **not** merely a shell — it was *deliberately narrowed* to be the
**bot-authoring language/library, the MQL5 analog**, ending at the bot-to-book
boundary. That is exactly the "the actual QML meant to author our bots" the
operator remembers. What was dropped is the *uniform cross-component contract
layer* and the concrete `BotSpec`/`exit_logic` types inside it.

- **AD-32 — "QML narrowed to bot authoring" `[ADOPTED]`** (the ruling that did
  this): "QML is the bot-authoring language/library (the MQL5 analog)… It stops at
  the book level; explicit adapters bridge QML ↔ book internals. Everything else is
  pure Python with no QML dependency." — **Prevents:** "QML re-expanding into a
  uniform cross-component layer."
  (`QMX/_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-07-20/ARCHITECTURE-SPINE.md:261-264`;
  operator called it "the biggest change", `…/.memlog.md:78`).
- **QML the bot-authoring language is kept, in-scope.** COMP-QML "Provides the
  **bot-authoring language/library at the bot-to-book boundary**. QML stops at the
  book level… CT-QML-01 currently has zero interface entries"
  (`QMX/wiki/architecture/components.md:62`). "QML is QMX's **bot-authoring
  language/library, analogous to MQL5**… in scope as the bot-to-book authoring
  boundary, but its internal design is not complete"
  (`QMX/wiki/components/qml-library-layer.md:16-18`).
- **But it is still a shell with empty interfaces (GAP-0013).** "COMP-QML — 'QML
  Custom Library Layer', kind `library` … in-scope component shell, but its exact
  interfaces remain open. DEC-0001" (`qml-spec.md:14`); "GitBook QML = shell with
  GAP-0013 wide" (`.brain/summaries/2026-07-17-session-orientation.md:48`);
  `CT-QML-01` "current register contains zero interface entries"
  (`QMX/wiki/contracts/ct-qml-01-qml-library-interface-register.md:29-30`).
- **`BotSpec`, the old uniform bot definition, is NOT a current construct.** It
  survives only as attic/donor evidence and a *deferred* future registry: the
  current `bots` table is a 9-field stub with "Full BotSpec/lineage registry
  deferred" (`…/architecture-QMX-2026-07-20/schemas/draft-streams-and-entities.md:237`);
  "The unified gate does not ratify the full BotSpec registry, lineage, or
  career-history service" (`QMX/wiki/topics/registration-and-promotion.md:55`).
  Uniform identity is now `bot_id` + `bot_spec_version` + measured `footprint`
  ("rather than bot self-description", `QMX/wiki/glossary/index.md:53`).
- **`exit_logic` / `ExitLogicRef` are absent everywhere in the newer corpora**
  (grep across `QMX/wiki`, `.brain`, and the 2026-07 architecture spine returns
  zero hits for either token). The bot "owns entry and exit organs"
  (`QMX/wiki/system/mental-models.md:20`) but the stop *policy* is now book
  money-rules grammar governed by BMS, not a bot-spec field
  (`QMX/wiki/topics/position-safety-and-sltp-authority.md:71`). The old composition
  formula `Archetype + Features + Filters + Risk + Execution + Exit Logic` does not
  survive as a typed contract; only `archetype` survives as a no-authority naming
  token (`QMX/wiki/glossary/index.md:25`).
- **The old couplings mapped to the new world** (`qml-spec.md` Part C,
  `:147-165`) — explicit dispositions, DEC-numbered:
  - Capital slots → **Risk seats** (`max_concurrent_live_bots=3`,
    `offer_per_seat=D/(B·b·Lbar)`); slot tables dropped.
  - DPR / declared-weight multiplier stack → **DEAD (DEC-0018)**.
  - Session-window authority → **DEAD (DEC-0025)**; SessionWindow demoted to
    measured input.
  - CircuitBreakerEvent + two-strike → **Breaker door + leash chain (DEC-0037)**.
  - Registry lifecycle + house-money → **Treasury cycle** (seed→cap, kill-line→
    paper; no top-up DEC-0020) + **Exam certification**; **BMS Records owns
    journals (DEC-0046)**.
  - KillSwitchEvent TIGHTEN/REGION_SHIFT → 5 levels stay (DEC-0043) but
    **TIGHTEN dead (DEC-0019)**, REGION_SHIFT dead (DEC-0021).
  - Nine safety hooks + Intent Aggregator → **Seven doors** (footprint, viability
    veto, R_max, daily budget, breaker, exposure ledger, kill switch); every
    refusal signs the veto ledger (L11).
  - Bridges-as-authority-crossings → **Four BMS desks + 17 CT-\* contracts**;
    "if a field is not in the contract, it does not cross the boundary."
- **Exit uniformity specifically was retired.** The clash report's proposed
  resolution: "**Stop policy is part of a book's MONEY SHAPE**" — template owns
  the *grammar*, each book **instance declares its values** (DEC-0024-compliant:
  "scalper book chooses one-shot-BE + trail; a future book may choose fixed
  brackets"); one **Position Safety service** executes per-book config
  (template/instance split, ADR-0002). What **dies**: "any notion that the SL/TP
  service is **globally uniform across books** (DEC-0024)"; TIGHTEN (DEC-0019)
  (`clash-report-sltp-vs-book.md:65-92`).
- **How the newer generation now does the exit/bench job** (replacing the old
  system-owned uniform SL/TP authority):
  - **Seven doors** run on every intent (footprint, viability veto, R_max, daily
    budget, breaker, exposure ledger, kill switch); every refusal signs the veto
    ledger (`QMX/wiki/components/book-template.md:47`).
  - **Leash chain (DEC-0037)** is the graduated exit/protection funnel that
    replaced old circuit-breaker hooks: "ambient governor → day closure →
    bench-to-paper → chorus flag → kill-line stand-down → classed kill switch →
    hold-time force-flat" (`.brain/entities/qmx-new-core.md:38-40`).
  - **Bench** is now a **roster seat state** `BENCHED` driven by the breaker door,
    parameterised **per book** via the registry:
    `scalper_breaker_threshold (B=2) consecutive_stopouts`, owner
    `COMP-BOOK-SCALPER`, `configurable: true`, DEC-0029; auto-reset DEC-0032
    (`QMX/wiki/registry/variables.md:23`; `QMX/wiki/glossary/index.md:71`;
    `BENCHED`/`STOOD_DOWN` book-level semantics reserved under GAP-0015).
  - **Stop policy is book money-rules grammar governed by BMS**, not a bot field:
    "The template defines permitted rule forms, each book instance owns its
    registry/formula-backed values, BMS governs configuration, and enforcement
    crosses the adapter boundary" — and "The old globally uniform SL/TP authority
    … remain[s] excluded" (`QMX/wiki/topics/position-safety-and-sltp-authority.md:71`).
- **The exit mechanics are still OPEN pre-epic blockers in the current corpus** —
  the recovered old spec is donor-only: stop-out taxonomy (PE-3,
  `QMX/wiki/open-questions.md:18`), position fate at rollover/sweep/kill-line/paper
  (PE-7, `:20`), stop-policy pinning (PE-8), plus exit ownership DEC-0067 / GAP-0040
  (see sibling `brief-exit-ownership.md`). Whether a BE-out counts toward the
  breaker is explicitly "undefined"
  (`QMX/wiki/topics/position-safety-and-sltp-authority.md:47`) — the same hole the
  old clash report flagged, still open.

---

## 4. What is directly reusable for the current risk sitting

The operator's live need — *make bot exit-method declarations and bench/stop-out
parameters uniform and configurable per strategy family* — the old QML already
solved the "how", and the clash report already drafted the migration. Reusable
assets, ranked:

1. **`ExitLogicRef` shape as the declaration atom.** `exit_logic = { module_id,
   config: dict }` (`qml-types-catalogue.md:2326-2332`). One exit *grammar* (the
   module surface) + per-instance *config* is exactly "uniform declaration,
   configurable per family." Drop it into the Book charter's money-shape slot
   rather than onto the bot/confluence (which current AD-17 forbids from owning
   exits).
2. **Template/instance split for stop policy** (the clash report's D1, "recommend
   yes"): the **book template owns the stop-policy grammar** (initial stop from
   certified footprint, breakeven rule, trail rule, **stop-out definition —
   including whether BE-outs count toward the breaker**); each **book instance
   declares values**, operator-countersigned; a **single Position Safety service**
   executes all policies (`clash-report-sltp-vs-book.md:65-83`). This is the
   uniform-yet-per-family answer, already anchored to DEC-0024/ADR-0002.
3. **Stop-out definition must be an explicit ruling, per family.** D2: do BE-outs
   count toward `scalper_breaker_threshold`? (report recommends *no* for the
   scalper book — count full stops only; keep BE-outs as a separate measured
   metric) (`clash-report-sltp-vs-book.md:97-100`). This is the direct link
   between exit policy and the **bench/paper-demotion** parameter the sitting
   cares about.
4. **Exam/live parity law extended to stop policy.** D3: Lbar and seat pricing are
   only valid if the same stop policy runs in exam replay and live — make it a
   constitutional addition alongside L10 (`clash-report-sltp-vs-book.md:46-54,
   101`). Directly governs how per-family stop/bench params feed
   `offer_per_seat = D/(B·b·Lbar)`.
5. **Close-authority priority model as donor.** Old KS=0 / normal=10 priority
   (`sltp-authority-spec.md:57-61`) re-anchored onto leash rungs: KSA ≥
   force-flat ≥ stop amendments, adapter-enforced (D4,
   `clash-report-sltp-vs-book.md:102-104`).
6. **Survivor mechanics (candidate grammar, values TBD per book):** one-shot-BE +
   never-reset flag; full-stop losers; TP trail as `f(continuation_prob)` with
   hold-on-MI-timeout; WAL + broker-reconciliation restart; amendment idempotency
   threshold; conservative fail-safe ("when in doubt, do not widen risk" — keep
   verbatim) (`clash-report-sltp-vs-book.md:84-89`).
7. **Locked-mutation discipline.** Keep exits in `locked_components` /
   `unsafe_mutation_zones` (`qml-architecture.md:636-637`) and out of WF2's
   mutate-set (`gpt-extract.md:56`) so per-family exit config stays uniform and
   agent-tamper-proof.

**Load-bearing caveat (precedence):** everything above is the *oldest* vault
layer. It is a **design donor, not authority** — current QMX rulings (AD-17
"Exits are Book/risk/node territory"; confluence "contains no Exit") and the live
DEC-0067/GAP-0040 conflict govern. The old vault's contribution is that it proves
the uniform-declaration mechanism (`ExitLogicRef` + system-owned executor) was
built and worked, and the clash report already did the hard thinking about how to
re-seat it as per-book money-shape without re-introducing the global uniformity
that DEC-0024 retired. Reassuringly, the current generation has already ratified
exactly that donor pattern in the abstract — **template owns the uniform grammar,
each book instance owns its values** (ADR-0002 template/instance split;
`QMX/wiki/decisions/adr-0002-template-and-instance-split.md:22`), with a "dormant
socket" letting a capability exist uniformly yet be disabled per profile
(`QMX/wiki/glossary/index.md:49`). So adopting `ExitLogicRef`-style
declaration + per-family config for exits/stop-outs/bench is *continuous with*
current direction, not a reversal of it; what remains genuinely open is the
concrete stop/exit policy content (PE-3/PE-7/PE-8) and exit ownership (DEC-0067).

---

## Source index (all read-only, oldest-vault unless noted)

- `QMX-discussion/02-Components/00-QML-shared-library/00-QML-overview.md` — QML definition, uniformity rationale
- `QMX-discussion/02-Components/00-QML-shared-library/01-QML-domain-types.md` — flat BotSpec, TradeIntent, RiskAuth, CloseReason
- `QMX-discussion/outputs/qml-spec.md` — consolidated extraction (Part A binding shell / Part B old baseline / Part C re-anchor map)
- `QMX-discussion/outputs/sltp-authority-spec.md` — old system-owned asymmetric SL/TP authority (full extraction)
- `QMX-discussion/outputs/clash-report-sltp-vs-book.md` — SL/TP-vs-book clash + resolution proposal (the sitting's donor doc)
- `QMX-discussion/bmad-docs/planning-artifacts/qml-architecture.md` — nested BotSpec (ADR-007), filters/exit_logic first-class
- `QMX-discussion/bmad-docs/planning-artifacts/qml-types-catalogue.md` — ExitLogicRef, SLTP types, CloseReason, complexity gate
- `QMX-discussion/bmad-docs/planning-artifacts/qml-architecture-context-gpt-extract.md` — the `Bot = ...+ Exit Logic` formula, WF2 mutation locks
- `QMX-discussion/bmad-docs/planning-artifacts/{epics.md,prd.md}` — FR17 (bot-owned SL/TP rejected), QML gloss
- `QMX-discussion/.brain/summaries/2026-07-17-session-orientation.md` — GitBook QML = shell / GAP-0013
