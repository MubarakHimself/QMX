# QML Architecture Spine — Rubric-Walker Review

**Artifact:** `architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md` (QL-1..QL-10)
**Lens:** Rubric walker (good-spine checklist)
**Binding law read:** QMF AD-1..AD-41 (parent), QMB B-1..B-15 (sibling), QML memlog
**Date:** 2026-08-21

## Verdict

The QML spine is structurally sound and, on substance, a faithful thin-consumer child of QMF/QMB: every QL fixes a genuine cross-unit invariant (not restated parent law), each carries Binds/Prevents/Rule, the seed is minimal and code-owned, Deferred names each punt with a landing place, both mermaid diagrams parse and convey real structure, and the close-reason mapping in QL-9 lands entirely inside the ratified AD-33 taxonomy with no invented members. The dominant defect is mechanical and load-bearing: the spine was renumbered from the memlog's QL-1..QL-9 draft to the final QL-1..QL-10, but nine internal `QL-n` cross-references were left at their old (memlog-era) targets, so a small builder agent chasing "the runtime protocol (QL-6)" or "entry-intent derivation (QL-6)" lands on the strategy-family rule instead. Beyond that, four decision-level seams are under-specified enough to let two independent builders diverge: whether an application may import the `qmf-risk` edge module (QL-1 asserts a carve-out to an absolutely-worded parent rule), who actually runs the impure conformance sandbox given QML's AD-15 purity, who executes the Book `ExitLogicRef` at entry-intent mint, and QML's own package version-ladder stance. None are fatal; all are fixable with local edits.

---

## Findings (most severe first)

### RW-1 — HIGH — Nine stale `QL-n` cross-references from the memlog→spine renumbering

The memlog numbered confluence=QL-4, family=QL-5, protocol=QL-6, gate=QL-7, exit=QL-8. The final spine inserted **Footprint** as a new QL-4, pushing everything from confluence onward up by one (confluence→QL-5, family→QL-6, protocol→QL-7, gate→QL-8, exit→QL-9). Some cross-references were updated to the new numbering (QL-5's "producer binding per QL-4", QL-6's "prediction linter (QL-8)", QL-10's "QL-7 seats"), but nine were missed and still point at the old targets. Each misdirects a reader to the wrong rule:

| # | Location | Text says | Should say | Lands the reader on |
| --- | --- | --- | --- | --- |
| 1 | QL-1 Rule (line 49) | "the bot runtime protocol hosts invoke (QL-6)" | QL-7 | QL-6 = strategy family |
| 2 | QL-1 Rule (line 49) | "the conformance gate (QL-7)" | QL-8 | QL-7 = runtime protocol |
| 3 | QL-2 Rule (line 55) | "conforming to the QL-6 runtime protocol" | QL-7 | QL-6 = strategy family |
| 4 | QL-3 Rule (line 62) | "the strategy-family id (QL-5)" | QL-6 | QL-5 = confluence kind |
| 5 | QL-3 Parameterization law (line 71) | "declares canonical-assignment evidence (QL-7)" | QL-8 | QL-7 = runtime protocol |
| 6 | Inherited table, AD-32 row (line 33) | "gains the two bot-side fields (QL-7)" | QL-8 | QL-7 = runtime protocol |
| 7 | Inherited table, AD-33 row (line 34) | "QL-8 ratifies the donor atoms as-is" | QL-9 | QL-8 = conformance gate |
| 8 | Inherited table, AD-40 row (line 35) | "entry-intent derivation (QL-6)" | QL-7 | QL-6 = strategy family |
| 9 | Inherited table, QMB Deferred row (line 39) | "QL-7's ticket honors it verbatim" | QL-8 | QL-7 = runtime protocol |

This directly defeats rubric criterion 8 (terse-convergent, buildable without drift): the spine explicitly exists so a small agent can navigate it, and half its forward-pointers to the protocol/gate/exit rules are wrong.

**Fix:** Correct all nine to the spine's final numbering (mapping: old protocol QL-6 → QL-7; old gate QL-7 → QL-8; old exit QL-8 → QL-9; old family QL-5 → QL-6). Then grep the whole spine once more for `QL-` and confirm every reference resolves to the section it names.

### RW-2 — MEDIUM — QL-1 asserts QML imports `qmf-risk`, an edge module the parent says "nothing imports"

QL-1's dependency stance: "QML imports `qmf-core` …, `qmf-registry` …, and `qmf-risk` (CT-23 intent types) — application-layer composition, legal because the default-deny edge rule governs QMF roster packages internally, never applications built on the workspace." The parent's Dependency-direction rule is worded absolutely: "`qmf-core` depends on nothing; every package may depend on `qmf-core`; **nothing imports `qmf-venue` or `qmf-risk`**" and the diagram labels both as "edge modules — nothing imports them." QML needs the CT-23/CT-29 types (defined *by* `qmf-risk` per AD-33) to mint intents, so it genuinely must import `qmf-risk` — and it resolves the tension by declaring a roster-vs-application carve-out that the parent text does not itself state. This is the child reinterpreting read-only binding law. The reading is defensible (the parent rule is plainly about the seven-package hexagon, and the sibling QMB already "consumes qmf-risk contracts") but it is asserted as settled rather than surfaced as a reconciliation dependency, and if the strict reading wins, QML's entire dependency paragraph is illegal and needs a `qmf-core`-hosted contract-type home instead.

**Fix:** Do not let the child silently settle a parent-law carve-out. Either (a) add one explicit sentence flagging this as a reconciliation item requiring the parent rule to be read/annotated as roster-scoped (operator/docs-factory confirmable), or (b) restructure so the pure CT-23/CT-29/CT-32 contract *protocols* QML consumes live in `qmf-core` (importable without the edge module) while `qmf-risk` retains only the risk logic — mirroring how QMF already keeps shared nouns in `qmf-core`. Keep the `qmf-venue` prohibition as-is (that asymmetry is principled and correct).

### RW-3 — MEDIUM — Conformance Layer-2 sandbox execution vs QML's AD-15 purity: the seam is not stated where it is used

QL-8 describes Layer 2 as impure, stateful work: "the logic artifact **loads in an isolated environment**; runs a golden evidence slice twice … respects the no-clock/no-I-O/no-network constraints (**static import scan + sandbox denial**); honors … a snapshot/restore round-trip." QL-1 separately pins QML "pure per AD-15 (no threads, no I/O); registration writes and sandbox processes ride the platform/QMB composition roots through AD-28's injected-sink pattern." Read alone, QL-8 reads as though QML spawns and polices the sandbox — which would violate AD-15 and contradict QL-1. The split (QML ships the checks/suite as pure functions plus a sandbox protocol; the host/composition root provides process isolation, syscall denial, and execution — exactly as QMB's orchestrator owns all impurity per B-4/B-5) is the intended design but is only gestured at in QL-1, not stated in the rule that describes the sandbox. A builder could reasonably implement `qml.conformance` spawning subprocesses.

**Fix:** Add one clause to QL-8 Layer 2 making the seam explicit: QML provides the conformance suite and a sandbox-execution protocol as pure functions returning verdicts; the host/composition root supplies process isolation, the syscall-denial sandbox, and execution and feeds results back (AD-15 purity preserved, AD-28 injected-sink pattern, mirroring QMB's orchestrator). Note that registration-time conformance is a QML-V1 concern (distinct from the already-Deferred seat-time footprint policing), so this seam cannot be punted.

### RW-4 — MEDIUM — QL-7 entry-intent derivation does not say who executes the Book `ExitLogicRef`

QL-7: "the declared full-loss price on a CT-23 entry intent is derived **at intent mint** by executing the Book-declared family `ExitLogicRef` (module_id + config resolved read-only from the bound Book's `exit_policy` …); the Book door deterministically recomputes and verifies at admission." It never assigns the executor. If the bot's plain-Python logic runs the `ExitLogicRef`, the bot must be handed the bound Book's `exit_policy` — coupling bot logic to Book exit config and breaking QL-1's load-bearing promise that "an unregistered bot needs zero QML imports to run in QMB or research." If the protocol harness/host runs it as the intent crosses the door, the bot stays ignorant and the clean bot→Book boundary (AD-29 authority order, AD-33 single-authored R) holds. Two builders will split on this, and one of the two readings quietly violates QL-1 and AD-29.

**Fix:** State in QL-7 that the **protocol harness (host side), not the bot logic**, executes the resolved `ExitLogicRef` when the bot's advisory proposal crosses the door, stamping the derived full-loss price onto the CT-23 intent; the bot supplies only its advisory stop proposal and cited evidence. This preserves the zero-import property and keeps R single-authored (bot proposes, host derives against Book policy, Book door verifies).

### RW-5 — LOW — QML's own package version-ladder / distribution channel is not ruled (packaging dimension)

Rubric criterion 3 lists packaging/distribution as a dimension that must be decided, deferred, or open. QL-1 and the frontmatter decide the *shape* ("one uv-installable distribution, import `qml`"), and the Stack section rules dependency pins ("rides the QMF workspace pins … adds zero runtime dependencies"). But the sibling QMB explicitly ruled its own version ladder and channel (B-13: own SemVer as display-only provenance, `uv add qmb` as the required import channel, `uvx` as CLI-only convenience). QML — which claims to be "application layer built on QMF exactly as QMB is" — leaves unstated whether the `qml` distribution rides QMF-roster lockstep or its own SemVer ladder, and whether its SemVer is display-only provenance. The dimension is partially, not fully, decided.

**Fix:** Add one line (Stack or QL-1) mirroring B-13: the `qml` distribution carries its own SemVer as display-only provenance (never identity — the logic-artifact identity and CT-33 `fp1` carry identity), consumes the QMF workspace lockstep, and is a normal pinned project dependency.

### RW-6 — LOW — QL-1 "defines no cross-component contract of its own" contradicts QL-7's QML-owned runtime-protocol contract

QL-1 Rule: "QMF's contracts are the shared layer; QML consumes them and **defines no cross-component contract of its own**." QL-7 Binds: "**QML's own format-versioned protocol contract** (AD-5's second ladder; not CT-numbered, mirroring QMB's own contracts)." The runtime protocol spans bots ↔ hosts, so it is cross-component by any plain reading. The intended distinction — QML mints no new *QMF-ladder* (CT-*) shared-contract stratum, but does own a QML-local contract exactly as QMB owns its run-config/ledger contracts — is correct, but the QL-1 wording overstates it and reads as a contradiction against QL-7.

**Fix:** Sharpen QL-1 to: "QML mints no new QMF-ladder (CT-*) shared contract; its runtime protocol (QL-7) is a QML-local contract on its own format-version ladder, exactly as QMB owns its run-config and ledger contracts."

### RW-7 — LOW — "content fingerprint of the built artifact" as a Bot identity field risks non-reproducible identity, weakening AD-16 dedup

QL-2/QL-3 make Bot identity include "the **content fingerprint of the built artifact**" of the logic distribution, alongside distribution identity + version. A built Python wheel is not generally byte-reproducible (zip mtimes, build metadata), so identical logic built in two sandboxes could hash differently, minting two Bot identities and defeating AD-16's guarantee that "identical work from two sandboxes deduplicates" (and forking AD-35 cohort keys that ride Bot identity).

**Fix:** Base logic-artifact identity on a **reproducible source/content fingerprint** (or distribution identity + version alone) rather than a possibly-non-reproducible built-wheel hash; state the canonicalization so two sandboxes building the same source produce one Bot `fp1`.

### RW-8 — LOW — "advisory stop proposal" (QL-7) is an undefined term of art

QL-7 introduces "the bot's advisory stop proposal" as the input the `ExitLogicRef` consumes, but never defines it or binds it to an existing term. AD-33's entry intent carries "an advisory `proposed_r`"; whether the "stop proposal" is `proposed_r`, a proposed stop distance/price, or a distinct field is left to the reader. Every other term of art in the spine resolves to a definition here or in the parent/sibling; this one does not.

**Fix:** Define "advisory stop proposal" at first use or bind it explicitly to AD-33's advisory `proposed_r` (or name the proposed stop distance as the field), so the QL-7 derivation has a typed input.

---

## Rubric checklist (what passed)

- **(1) Each QL fixes a real invariant, not restated parent law/seed detail** — PASS. QL-2 (two-artifact bot + no DSL), QL-3 (CT-33 identity + canonical-assignment law), QL-4 (footprint producer bindings/templates), QL-5 (confluence anatomy + minted `filter` role), QL-6 (family = key-not-authority), QL-7 (runtime protocol), QL-8 (technical conformance + admission interfaces) all decide genuine two-builders-could-diverge questions. QL-1/QL-9/QL-10 lean on positioning/ratification but each closes a live question (dependency stance, the AD-33 provenance flag, before/after-node order).
- **(2) Binds/Prevents/Rule on every QL** — PASS. All ten carry the triad.
- **(3) Structural dimensions each decided/deferred/open** — MOSTLY PASS. Identity (QL-3/QL-5), versioning (QL-3), registration/write path (QL-1/QL-8), runtime protocol (QL-7), conformance (QL-8), admission interfaces (QL-8), dependency stance (QL-1), hosting (QL-7/QL-10/seed), naming (Conventions) all present. Gaps: packaging version-ladder (RW-5) and the conformance-sandbox execution seam (RW-3).
- **(4) Seed minimal and owned-by-code** — PASS. `qml/` with declaration/footprint/families/protocol/conformance/examples/tests, plus a hosting note; no over-specification, `examples/` gives the L27 reference bot.
- **(5) Deferred names its punts with landing places** — PASS. Seven rows, each with a home (platform/agentic sittings, GAP-0048/0049, node sitting, AD-17 holding seam, memlog open question).
- **(6) Diagrams valid mermaid, real structure** — PASS. Both `graph` diagrams parse (subgraph id+title, edge-label syntax, `[( )]` cylinders, `<br/>`/`·` in labels all legal) and convey the artifact graph and the distribution/host graph.
- **(7) No placeholder or invented fact** — PASS. QL-9's close-reason mapping lands entirely inside AD-33's ratified CT-29 taxonomy; CT-33/CT-34 correctly continue the QMF ladder past CT-32; the DEC-0024 citation in QL-9 is corpus-grounded (compound decision also retiring the uniform/asymmetric SL/TP service, per `extract-old-recovered.md:552` and `qml-original-dig.md`).
- **(8) Terse-convergent, buildable without drift** — FAIL on navigation (RW-1), plus the RW-3/RW-4 execution-owner ambiguities.
- **(9) No undefined terms** — MOSTLY PASS. One nit: "advisory stop proposal" (RW-8). All other terms resolve here or in AD-*/B-*.
