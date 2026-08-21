# Reviewer gate — CURRENCY / REALITY CHECK lens

Artifact: `architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md` (QL-1..QL-10)
Lens brief: verify every committed decision was reality-checked, not asserted; confirm no rule
quietly depends on an unpinned/unnamed tool or mechanism; spot-verify every cited parent/sibling/doc
fact against the actual files; flag anything stale or misquoted.
Date: 2026-08-21.

## Verdict

The spine is largely well-grounded: the load-bearing parent/sibling/doc facts it cites **do** exist
as cited. I verified each named target and all pass — AD-16 reserves the Bot kind and defers its body
to its own sitting (confirmed in the QMF spine and in `ct-06-registration.yaml`, where `Bot` is a
reserved kind name whose body comes from the QML sitting, GAP-0047); AD-17 names **exactly three**
confluence roles (levels, triggers, confirmations), so the spine's "first three verbatim from AD-17,
`filter` freshly minted here" is accurate; AD-30 declares **exactly** the two `pending(GAP-0047)`
slots the spine claims (`footprint_requirements` + the prediction linter); AD-32's
`evidence_requirements` really carries (world, account role, minimum evidence window, producer
contract format versions); AD-33 places `ExitLogicRef = {module_id, config}` in the Book's
`exit_policy` per family and flags it "open to revision by the QML sitting (GAP-0047)"; **every**
close-reason member QL-9 maps onto (`protective_stop_fill`, `target_fill`,
`protection_amendment_fill`, `operator_close`, `protection_forced_flat`, `window_forced_flat`,
`boundary_flat`, `hold_time_force_flat`, `venue_initiated_close`, `venue_liquidation`) exists in
AD-33's ratified list; B-8's parameter-space schema and B-12's stream-set shape match; QMB's Deferred
row on QML is honored verbatim; `docs/contracts/` tops out at `ct-32`, so **CT-33/CT-34 are genuinely
free**; constitution **L11** (QMF umbrella, QML the Bot library) and **L27** (tests + reference usage)
verify; the glossary's QML and Bot entries and ADR-0011 (QML Bot library deferred) support QL-1.

Four real defects remain. The most serious is a **reality-check gap**: the QL-8 Layer-2 conformance
sandbox depends on an unnamed runtime-isolation mechanism, while the Stack section claims "No new
technology is pinned." Second is a **cluster of stale draft QL-numbers** that survived the
draft→final renumber and now misdirect readers across the QL-5..QL-9 quartet. Third is a **mis-cited
law** (L21). Fourth is a pair of **present-tense glossary claims** that aren't yet true. None is fatal;
all are concretely fixable at the desk.

---

## Findings (most-severe first)

### F1 (HIGH) — QL-8's conformance sandbox rests on an unnamed, unpinned isolation mechanism, contradicting "No new technology is pinned"

**Where:** QL-8 Layer 2 (spine line 103); QL-1 (line 49); Stack section (lines 160-162); structural
seed `conformance/` (line 172); Deferred row (line 190).

**What the spine says.** QL-8 Layer 2: "the logic artifact loads in an isolated environment; runs a
golden evidence slice twice with identical intents (determinism); … respects the
no-clock/no-I/O/no-network constraints (**static import scan + sandbox denial**) …". QL-1: "registration
writes and **sandbox processes** ride the platform/QMB composition roots through AD-28's injected-sink
pattern." Stack: "**No new technology is pinned by this spine.** QML … adds **zero runtime
dependencies** beyond the `qmf-*` packages it consumes."

**Why this is a reality-check gap, not an assertion that holds.**
- The conformance gate (`conformance/` — Layer-1 linter + **Layer-2 sandbox suite**) is QML's **own**
  V1 deliverable, run at registration. It is not the deferred seat-time enforcement (Deferred row,
  line 190, defers only *live* node enforcement). So QML itself must ship the sandbox.
- "The bot never … performs I/O, network access, or undeclared randomness" is enforced by "static
  import scan + **sandbox denial**." The static/AST scan half is stdlib-doable, but it is defeated by
  dynamic imports (`importlib.import_module`, `__import__`, `ctypes`), so it cannot be the real guard.
- AD-28's injected-sink / capability-injection pattern (cited by QL-1) starves the logic of *handles*
  the host would otherwise pass, but it does **not** stop loaded Python from doing `import socket` /
  `open(...)` on its own. Denying network/I/O/clock to arbitrary in-process Python requires OS-level
  confinement — a subprocess under a restricted token / job object on Windows, and seccomp/namespaces
  (or an nsjail-class tool) on Linux. **AD-1 pins both Windows 11 and Ubuntu as tier-1 targets**, so
  the mechanism is platform-specific and non-trivial.
- The sibling that QL-1/QL-10 lean on for "sandbox processes" — QMB — provides only **process
  isolation for resource governance** (B-5: "separate OS processes (stdlib process management)… No
  Ray, no required Docker, no daemon"), explicitly *not* a security sandbox that denies
  network/I/O/clock.

So a load-bearing mechanism (the thing that makes "conformance is the ticket" mean anything) is named
only as "sandbox denial," is not pinned, is likely a genuine new dependency, and its cross-platform
feasibility was asserted rather than checked — directly against the Stack's "no new technology / zero
runtime dependencies" claim.

**Fix.** Make the Layer-2 isolation mechanism explicit and reconcile the Stack claim, one of two ways:
- **(a) Pin it.** Name the confinement approach per AD-1 tier-1 target (e.g., subprocess under a
  restricted token / job object on Windows; seccomp + namespaces / nsjail-class confinement on Linux),
  add it to the AD-6 dependency register, and change the Stack line to state the spine *does* pin a
  Layer-2 sandbox mechanism (with the cross-platform caveat), rather than "no new technology."
- **(b) Scope the V1 guarantee down honestly.** State that Layer-2 enforcement in V1 is "static
  AST/import scan + capability starvation via AD-28 injected sinks," record explicitly that in-process
  runtime denial of network/I/O and dynamic-import evasion are **not** guaranteed in V1, and defer
  hardened runtime confinement to the node/platform sitting as a **named** dependency. Then soften the
  Stack line so it no longer implies the sandbox needs nothing new.

---

### F2 (HIGH) — Stale draft QL-numbers survived the renumber; seven cross-references point to the wrong rule

**Where:** Inherited-Invariants table (lines 33, 34, 35, 39); QL-1 body (line 49); QL-3 body
(lines 63, 71).

The memlog's final-entry ID map is explicit ("spine is authoritative; earlier entries used draft
numbering"): draft QL-5→final QL-6 (strategy family), draft QL-6→final QL-7 (runtime protocol),
draft QL-7→final QL-8 (conformance/admission), draft QL-8→final QL-9 (exit reconciliation). The
structural seed (lines 168-172) and several body refs were correctly updated, **but these were not** —
each still carries the draft number and now resolves to the wrong rule:

| Line | Text (as written) | Points at | Should be |
| --- | --- | --- | --- |
| 33 | "the two bot-side fields **(QL-7)**" | QL-7 runtime protocol | **QL-8** (the two `evidence_requirements` fields live in the conformance/admission rule) |
| 34 | "**QL-8** ratifies the donor atoms as-is and closes the QML-revision flag" | QL-8 conformance | **QL-9** (exit reconciliation ratifies the donor atoms) |
| 35 | "entry-intent derivation **(QL-6)**" | QL-6 strategy family | **QL-7** (entry-intent derivation lives in the runtime protocol) |
| 39 | "**QL-7**'s ticket honors it verbatim" | QL-7 runtime protocol | **QL-8** (the ticket is in the conformance gate) |
| 49 | "the bot runtime protocol hosts invoke **(QL-6)**; (3) the conformance gate **(QL-7)**" | QL-6 / QL-7 | **QL-7** (runtime protocol) / **QL-8** (conformance gate) |
| 63 | "the strategy-family id **(QL-5)**" | QL-5 confluence kind | **QL-6** (strategy family) |
| 71 | "canonical-assignment evidence **(QL-7)**" | QL-7 runtime protocol | **QL-8** (canonical-assignment evidence is defined in the admission interface) |

That the *same* concepts are cited with the *correct* final numbers elsewhere (prediction linter
"(QL-8)" in QL-6 line 89; producer binding "(QL-4)" in QL-5 line 80; "QL-7 seats/adapter" in QL-10,
hosting seed, and both diagrams; conditions-in-logic "(QL-5)" in the Deferred table line 183) confirms
this is an incomplete renumber, not an alternate scheme. Left as-is, the Inherited-Invariants table —
the first thing a downstream reader (documentation-factory, epics-and-stories) consumes — misdirects
across the exact QL-6/7/8/9 quartet that carries the runtime/conformance/exit design.

**Fix.** Apply the memlog's final ID map to the seven rows above (per the table's right-hand column).

---

### F3 (MEDIUM) — QL-1 mis-cites law "(L21)"; the actual L21 is the cTrader-Open-API/not-MQL law

**Where:** QL-1 (line 49): "application layer built on QMF contracts exactly as QMB is **(L21)**, never
a QMF roster package (ADR-0011/L11)."

`docs/constitution.md` **L21** = DEC-0060: "The first Venue integration must use the cTrader Open API
from Python and must not use MQL." That has nothing to do with "application layer built on QMF." The
law that actually carries "QML is a library on the framework, not a roster member" is **L11**
(DEC-0017, QMF umbrella / QML the Bot library) — which QL-1 already cites correctly in the very next
clause — reinforced by **AD-2** (roster is the seven `qmf-*` packages) and **ADR-0011** (QML Bot
library deferred, outside the roster). The QMF spine does **not** define L21 as a packaging law. The
error is inherited from the QMB sibling spine, whose Inherited-Invariants row likewise mis-labels the
"own installable package, not a roster member" idea as "AD-2 / L21."

**Fix.** Replace "(L21)" with "(AD-2 / L11)" (or simply drop the tag — L11 already carries the point).
Separately, flag the QMB spine's matching "AD-2 / L21" row to the documentation-factory so the
inherited mis-citation is corrected at source rather than propagated further.

---

### F4 (LOW) — Two glossary aliases are asserted as already-recorded but are not in `docs/glossary.md`

**Where:** QL-6 (line 89): "'Archetype' **is recorded in the glossary** as the retired alias."
Consistency Conventions (line 155): "never 'BotSpec' (old word, **glossary-recorded alias**)."

`docs/glossary.md` today contains **no** `archetype`/`ArchetypeSpec` entry (grep: no matches) and **no**
`BotSpec` alias. Both statements read as present-state facts about the glossary, but the glossary has
not yet been updated — these are documentation-factory to-dos phrased as if already done. Minor (the
spine is upstream of the doc-factory increment), but the present tense is inaccurate and could let the
alias entries be assumed present and skipped.

**Fix.** Rephrase as forward directives — e.g., "'Archetype' is **to be recorded** in the glossary as
the retired alias (documentation-factory increment)" and "'BotSpec' (old word; **glossary alias to be
recorded**)" — or ensure `docs/glossary.md` gains both alias entries when this spine lands.

---

## Checks performed and passed (no finding)

- Frontmatter `binds: [GAP-0047, CT-33, CT-34, CT-06-kind-register, AD-30-pending-slots]` — all real.
- CT-33 = Bot definition, CT-34 = confluence: both above the `ct-32` ceiling; free. Filling the ct-06
  reserved `Bot` kind via a new per-kind contract is the correct AD-16 pattern.
- AD-17 confluence roles = level/trigger/confirmation only → `filter` correctly marked "freshly minted."
- AD-30 pending slots = `footprint_requirements` + prediction linter (exactly the two the spine fills).
- AD-32 `evidence_requirements` fields verified; the two bot-side additions are disclosed as additive
  (would land as a CT-22 admission_bar format-version mint under AD-5 — worth a one-line note, but the
  cited fact itself is accurate, so not raised as a defect).
- AD-33 ExitLogicRef placement + "open to revision by the QML sitting (GAP-0047)" flag — verified; QL-9
  closes it correctly.
- QL-9 close-reason mapping targets — every member exists in AD-33's ratified list (taxonomy lives in
  CT-29/AD-33, which the spine attributes correctly).
- AD-40 `bench_consecutive_loss_threshold` and AD-41 `q` — attributed to the correct AD in QL-6.
- B-8 parameter-space schema and B-12 stream-set shape — match (QL-3 adds mandatory-default +
  per-parameter unit-kind, both disclosed as QML additions grounded in AD-40 / the canonical-assignment
  law, not passed off as verbatim).
- QMB Deferred "QML bot schema (GAP-0047)" row — honored verbatim.
- Constitution L11 and L27, glossary QML + Bot entries, `ct-06` reserved kinds, ADR-0011 — all verify.
- Stack "rides QMF pins (CPython 3.14, uv, ruff, pyright, pytest, poethepoet)" — matches AD-1/AD-3.
  No unpinned tool/library/format hides in the declaration (JSON-Schema-class per AD-30), the logic
  (uv distribution per AD-2/AD-22), the protocol (AD-5 format-versioned), or snapshot/restore (versioned
  contract). The **only** unnamed mechanism is the Layer-2 sandbox — see F1.
