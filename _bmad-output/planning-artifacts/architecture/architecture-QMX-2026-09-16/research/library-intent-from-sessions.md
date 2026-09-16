# Library intent from STRATS sessions (ontology / methodology only)

Extracted from Friendly Greeting + Gold Mine recovery — **library, dictionary, primitive/role/graph/package, strategy-spec intent**. Agent crews, n8n, Gemini, model routing, and video pipeline intentionally omitted.

**Primary sources:** `recovery-5678-assistant.md` (GM recovery `msg 5678`); `goldmine-4070-assistant.md` (`msg 4070`); `goldmine-4071-user.md` (`msg 4071`); `STRATS-GROUND-STATE.md` §4.

Citation key: `FG M#` = Friendly Greeting `20260824_121737_86f88c`; `GM M#` = Gold Mine `20260825_115530_94412f`.

## 1. Why the dictionary was invented

The operator is a developer, not a trader. Agents must do domain heavy lifting. Discretionary trading talk must become a shared vocabulary — not reinvented prose per strategy.

Intent: a **canonical reusable trading language**. Strategies cite stable IDs (e.g. `bullish-engulfing`) that link to one rich definition. That vocabulary later feeds **QMX bot specs**, without making STRATS a QMX subsystem.

Quoted from recovery and `GM M4070`: the dictionary is genuine and central; agents reference a canonical term rather than inventing prose.

## 2. Primitive vs role vs graph vs package — the independence law

```text
Primitive dictionary     → “What reusable thing exists?”   (role-neutral)
Contextual role binding  → “What job does it do here?”     (strategy-specific)
Strategy logic graph     → “How do bound parts interact?”  (Boolean/temporal/stateful)
Strategy package         → human- & agent-readable candidate spec + evidence + lineage
```

A primitive is not permanently a level, trigger, or confirmation. Bullish engulfing can construct a zone, trigger entry, confirm a sweep, or exit a short.

## 3. What “specking a bot” meant

Turning discretionary source material into structured, codable **candidate specifications**. Not writing trading bots inside STRATS; not backtesting here. Front-loaded input so QMX can implement/test later.

## 4. STRATS forever vs QMX later

**STRATS:** sources, dictionary, packages, mini-KBs, catalog, lineage, source-native claims.

**QMX:** test manifests, run results, experiment ledgers, executors, adapters, book/admission/sizing, live state.

`GM M4071`: leave QMX out for now; QMX will adapt; STRATS is the library of knowledge.

## 5. Richer than four-role confluence

Pillars are human-facing lenses, not a closed schema. Recovered model: multi-role primitives, strategy-specific bindings, unbounded Boolean/temporal/stateful graph, ~14-section package, evidence, unknowns, lineage.

## 6. Do not adopt (agentic / software)

Do not pull specialist fleet, staging, curator, promotion gates, video-R&D-first, or “library as OS” into QMX. Orchestration is how Hermes protected context — not an architectural layer inside STRATS or QMA.
