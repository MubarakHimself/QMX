---
cluster: backtesting-sitting / QML-dig-verification
question: "Does the QML dig + GAP-0047 plan fully cover the operator's memory of 'the ORIGINAL QML — a quant library used to build bots under the entire QMX platform for uniformity, from before QMF'? Anything older/different, anything NEW the dig missed?"
inputs-read: research-risk/qml-original-dig.md (full); next-session-prompts.md §8 (GAP-0047 plan); QMX-discussion corpus (grep QML → 65 files, read the load-bearing hits)
verdict: dig covers the operator's memory SUBSTANTIALLY; one genuine NEW artifact the dig missed (the `.qml` bot-source file format + Monaco authoring surface). No OLDER/different QML conception exists.
status: read-only verification dossier — nothing ruled
date: 2026-08-20
safety-note: all cited paths under C:/Users/Mubarak/Documents/... are old-generation inert evidence, read-only
---

# QML dig — verification against the operator's memory

## Bottom line

1. **What old QML was per the corpus matches the dig exactly.** The QMX-discussion
   corpus is unambiguous and single-voiced: QML = "QML — Shared Contract Library"
   / GitBook "QML Custom Library Layer", kind `library`; the load-bearing stratum
   every component imports and that imports nothing above it; its explicit job to
   make bots **uniform and honestly comparable**; `Bot = Archetype + Features +
   Filters + Risk + Execution + Exit Logic`; `BotSpec` (flat → nested ADR-007);
   `ExitLogicRef`; `CloseReason` taxonomy; system-owned asymmetric SL/TP. The dig
   reproduces all of this with correct citations. Coverage of the *contract-library*
   half of the operator's memory is complete and faithful.

2. **Nothing OLDER or DIFFERENT exists.** The oldest artifact in the vault (the
   2026-04-28 clean-room brainstorming) already uses "QML" in exactly the sense the
   dig reports — a monorepo **package family** (`qml.*` / `packages/qml-*`) built in
   a 9-phase order, six sub-packages, Compiler/Validator day-one
   (`bmad-docs/brainstorming/brainstorming-session-2026-04-28-125147.md:109,146-152,
   249-251`). There is no earlier or competing conception of QML (no "Quant Markup
   Language" expansion, no pre-Shared-Contract-Library design). QML is never expanded
   as an acronym anywhere in the corpus — the dig's "L = Library, never a markup
   language" claim holds for the *package*.

3. **ONE genuine NEW artifact the dig MISSED: the `.qml` bot-source file format
   (Monaco editor).** This is load-bearing for GAP-0047 and is described below.

---

## The NEW finding — `.qml`, the bot-authoring FILE format (dig gap)

The dig treats QML as **one** thing (the typed Python contract package) and states
flatly: *"It is not a markup/DSL — it is a typed-contract Python package (`qml.*`)"*
(`qml-original-dig.md:52-54`). The corpus actually carries **TWO distinct
QML-named artifacts**, and the dig documents only the first:

- **(A) The QML package family** — `packages/qml-*`, holding the contract *types*
  (`BotSpec`, `CapabilitySpec`, `ArchetypeSpec`) and bridges
  (`13-quantmindwiki.md:314`). This is the dig's subject.
- **(B) `<name>.qml` — the bot STRATEGY SOURCE file** — a **custom `.qml` file
  extension**, authored in a **Monaco editor**, holding a bot's *"entry, filters,
  gates, subscriptions."* Produced by **WF1 codegen / WF2 mutations**; one per
  variant leaf in the shared_assets tree
  (`.../{bot_id}/variants/{variant_id}/<name>.qml`)
  (`13-quantmindwiki.md:337`, `:359`, `:113`; folder tree `:336-338`).

The corpus explicitly distinguishes the two:
> "The `.qml` extension distinguishes bot strategy files from **QML package code
> (under `packages/qml-*`)** and from vault markdown."
> (`13-quantmindwiki.md:359`)

Supporting facts on `.qml` (all `13-quantmindwiki.md` unless noted):
- **Ownership / write-gate:** Backend "owns the editable surface for `.qml` source"
  (`:387`); Development-department agents may write `<name>.qml` **only inside a
  variant folder, within the QML Compiler/Validator sandbox** (`:396`); human edits
  to `<name>.qml` go via **Copilot-triggered PR** (`:394`).
- **Not the same as the strategy narrative:** `spec.md` (research TRD narrative) is
  **NOT** bot coding truth; `<name>.qml` is the executable source (`:358-359`).
- **Earliest mention:** the 2026-04-28 brainstorm already lists "`.qml` custom file
  extension (Monaco editor)" as a top-4 foundational deliverable with a "`.qml` file
  format spec" (`brainstorming-session-2026-04-28-125147.md:222,251,286`), and the
  architecture backlog reserves a QML deep-decomposition needing "operator-led
  discussion of **bot.qml format**" (`bmad-docs/planning-artifacts/architecture.md:351`).

**Why this matters for GAP-0047.** The GAP-0047 plan (§8) says "rebuild QML as a
THIN CONSUMER… **Bots stay authorable in plain Python (don't-box-in)**; QML
conformance is the ticket into governed evidence and Book seats." The old `.qml` +
Monaco authoring surface is the **concrete embodiment of the "authoring language"
half** of AD-32's "QML is the bot-authoring language/library, the MQL5 analog." It
is the single most direct evidence of *how the operator's remembered "quant library
used to build bots" actually let a human/agent WRITE a bot* — a dedicated file
format, editor surface, codegen path, and sandboxed write-gate. The GAP-0047 sitting
will have to rule plain-Python-vs-`.qml`-DSL for bot authoring, and the dig, as
written, does not put this `.qml`-file evidence in front of that decision. It should
be added to GAP-0047's primary inputs.

---

## Everything else the dig covers well (spot-checked, confirmed)

- **Uniformity mechanism** (single canonical import; bots-as-consumers; ~22 typed
  contracts; machine-enforced Compiler gate) — verified verbatim against
  `00-QML-overview.md:9,72,74,101` and the sub-package table `:82-91`. Accurate.
- **Nested `BotSpec` + first-class `filters`/`exit_logic`** (ADR-007 cascade from
  the GPT bot-formula) — matches `qml-architecture.md` and `qml-types-catalogue.md`
  as cited. Accurate.
- **`ExitLogicRef` = `{module_id, config}`**, `CloseReason` StrEnum, system-owned
  asymmetric SL/TP (one-shot-BE, TP-trail, full-stop losers) — accurate; these are
  exactly the GAP-0047 §8 "ExitLogicRef atom" and "CloseReason taxonomy" the plan
  names.
- **Newer-generation disposition** (AD-32 narrowing; `BotSpec` deferred to a stub;
  `exit_logic`/`ExitLogicRef` absent in newer corpora; global exit-uniformity
  retired by DEC-0024; leash/seven-doors replacing the old SL/TP authority) —
  consistent with the newer-corpus citations; the dig correctly frames old QML as
  **donor-only, not authority.** The GAP-0047 plan's "old QML is evidence and shape
  ONLY, never code; its old risk/sizing content superseded by AD-29..41" is aligned
  with the dig's precedence caveat (`qml-original-dig.md:423-438`).

## Coverage verdict on the operator's memory

The operator's memory has two clauses; the dig covers 1.5 of them:
- *"a quant library used to build bots… for uniformity"* → **library half fully
  covered**; the **build/authoring half is under-covered** because the `.qml`
  source-file surface is missing.
- *"under the entire QMX platform… from before QMF"* → **fully covered.** QML as the
  cross-component load-bearing stratum, later narrowed at the bot-to-book boundary
  by AD-32 (the "before QMF" → "under QMF" transition), is exactly the dig's Part 3.

No older/different QML exists; the dig's one gap is the `.qml` bot-source file format
+ Monaco authoring surface, which should be folded into the GAP-0047 sitting inputs.

---

## Source index (read-only, QMX-discussion oldest vault)
- `02-Components/13-quantmindwiki.md` — the `.qml` file format, Monaco, folder tree, write-gates (the dig's blind spot)
- `02-Components/00-QML-shared-library/00-QML-overview.md` — QML = Shared Contract Library, uniformity rationale (confirms dig)
- `02-Components/07-bot-registry-and-lifecycle.md` — BotSpec families, indicator lineage (no `.qml` mention here — it lives in quantmindwiki)
- `bmad-docs/brainstorming/brainstorming-session-2026-04-28-125147.md` — oldest artifact; QML package family + `.qml` extension already present (no older conception)
- `bmad-docs/planning-artifacts/architecture.md:351` — reserved "bot.qml format" decomposition
