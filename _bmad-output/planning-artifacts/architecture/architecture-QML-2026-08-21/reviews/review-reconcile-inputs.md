---
lens: input-reconciliation
artifact: architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md
inputs-checked:
  - research-risk/qml-original-dig.md (ranked reusable assets 1-7; old BotSpec formula)
  - research-backtesting/qml-dig-verification.md (plain-Python-vs-.qml mandatory question)
  - next-session-prompts.md §8 (GAP-0047 sitting prompt named jobs)
  - operator live dictation (before/after; QML-out-of-the-way; doc-factory prompt)
  - corpus-precedence discipline
date: 2026-08-21
verdict: The spine lands the load-bearing majority of every input, but the QL structure quietly dropped or left implicit five items that a downstream reviewer / doc-factory could lose. One is a named, explicit reconciliation requirement (BotSpec formula completeness) that fails for 2 of 6 components.
---

# Input Reconciliation — QML spine vs. load-bearing inputs

## Scope of this lens

I checked the QML spine against every load-bearing input the finalize gate names,
looking specifically for **quiet requirements the QL structure dropped** — things
that are real in an input but that a reader of the spine alone cannot find a home
for. I am NOT re-checking parent-spine internal consistency (a sibling lens owns
that); where the spine cites AD-34/40/41 for a disposition I take the citation at
face value.

## What landed cleanly (confirmed, not findings)

- **Plain-Python-vs-`.qml` mandatory question (verification dossier):** RULED in
  QL-2 — the `.qml` file format + Monaco surface is not revived in V1. The `.qml`
  evidence is visibly in front of the ruling ("the Monaco-era file format returning
  as an unversioned side channel"; "what the old `.qml` file carried — entry,
  filters, gates, subscriptions"). The dossier is a named companion. Fully honored.
- **GAP-0047 prompt jobs:** Bot schema/AD-16 reserved kind (CT-33, QL-3); confluence
  per AD-17 (CT-34, QL-5); exit declarations via AD-33 ExitLogicRef (QL-9); admission
  interfaces-only with thresholds at GAP-0048/0049 (QL-8); may-run-before-backtesting
  and the QML-first build order (QL-10); plain-Python authorable (QL-1/QL-2);
  conformance-as-ticket (QL-8); configurable = UI-editable (QL-2, conventions). All
  delivered. **The one exception is CT-28 — see Finding 2.**
- **Operator before/after question:** ANSWERED in QL-10 — "QML builds BEFORE the
  trading node," matching the operator's stated lean ("I feel like it is before").
  "Get QML out of the way in terms of architecture" is honored structurally
  (thin-by-law QL-1, zero new cross-component contracts, three-thing surface).
- **Doc-factory prompt (parent-session deliverable):** nothing in the spine blocks
  it; the CT-33/CT-34 renumber-safe note actively smooths it.
- **Corpus-precedence discipline:** honored. The dig + verification dossiers are the
  only QMX-discussion vehicles; all risk/sizing content is sourced to AD-29..41
  upstream (CloseReason members are mapped *onto* CT-29, not adopted as a contract).
- **Dig assets landed:** #1 ExitLogicRef atom (QL-9, ratified as-is in the Book);
  #3 stop-out definition per family (routed to AD-41 `qualifying_loss_exit`, QL-9);
  #7 locked-mutation discipline (Deferred table → agentic sitting, seam = branches-from
  + conformance gate; and exits are structurally out of the bot, a stronger guarantee).
  #2 template/instance split is adequately dispositioned as Book territory under AD-30.

---

## Findings (most-severe first)

### F1 — HIGH — Two of the six old BotSpec formula components have no stated disposition; `execution_profile`'s min-RR-before-entry is homeless

The lens requires **every** component of `Bot = Archetype + Features + Filters +
Risk + Execution + ExitLogic` to be dispositioned. Four are explicit:

- **Archetype** → strategy family, key-not-authority (QL-6; glossary retired alias). ✓
- **Filters** → the freshly-minted `filter` leg role, provenance-marked (QL-5). ✓
- **Risk** → Book-resolved sizing, bot never sizes (QL-1, QL-7). ✓
- **ExitLogic** → no bot field; Book `exit_policy` (QL-9). ✓

Two are **not** dispositioned by name:

- **Features** — only *implicitly* covered. The old `features: list[FeatureRef]`
  (signal-producing indicators) maps to producer bindings inside confluence
  `level`/`trigger` legs (QL-4/QL-5), but the spine never states that mapping, so a
  reader reconciling old→new cannot point to where "Features" went.
- **Execution** — has **no successor at all.** The old `execution_profile` carried
  "order-type preferences, slippage tolerance, partial-fill behaviour, **minimum RR
  threshold before entry**" (qml-original-dig §2.1). Order-type/slippage/partial-fill
  are plausibly venue/node, but the spine never says so, and **min-RR-before-entry — a
  real entry-quality gate — has no home**: it is not a Book admission door, not a
  named bot-internal filter, not an explicit drop. This is exactly the "quiet
  requirement the QL structure dropped" the lens is told to hunt.

**Why it matters:** the doc-factory will absorb this spine as the QML source of truth;
an unstated disposition becomes a silently lost requirement. Min-RR-before-entry
vanishing changes what a bot is allowed to gate on.

**Fix:** Add two disposition lines (QL-5 for Features, a new sentence in QL-3 or QL-7
for Execution): (a) "the old formula's **Features** are producer bindings consumed by
`level`/`trigger` confluence legs (QL-4)"; (b) "the old **`execution_profile`** does
not survive as a bot field — order-type/slippage/partial-fill are venue/node runtime;
**min-RR-before-entry is ruled a bot-internal condition in logic (QL-5), OR a Book
admission-bar concern, OR explicitly dropped** — pick one and name it." A one-line
ruling closes the hole.

### F2 — MEDIUM — The prompt's named "Book binding via CT-28" is never cited; the bot-to-binding linkage is left implicit

GAP-0047 §8 names the job as "Book binding **via CT-28/CT-23**." CT-23 is threaded
through the whole spine; **CT-28 (the Book binding record, anchored AD-29/31/32/35 per
spine-index) appears nowhere.** Binding is instead routed through AD-41 seats, the
AD-29 bind-time check, CT-18 venue capabilities, and `footprint_requirements` /
`exit_policy` / the prediction linter. That is substantively close, but it leaves
implicit **whether the seat / CT-28 binding record needs to reference the registered
Bot definition `fp1`**, and whether "re-binding never mints a Bot" (QL-3) is fully
reconciled with CT-28's binding-epoch semantics.

**Why it matters:** a named contract from the sitting prompt is uncited; if the
binding record's bot-reference field is a quiet requirement, it drops here.

**Fix:** Add one line where QL-3/QL-8 discuss seats/binding: cite CT-28 explicitly —
either "the CT-28 binding record / AD-41 seat references the registered Bot `fp1`; the
prediction linter runs against the CT-28 binding context (venue capabilities via
CT-18)" or "binding is entirely upstream (AD-41 seat over CT-28); QML adds no binding
field." Naming CT-28 discharges the prompt job.

### F3 — MEDIUM — Dig asset #5 (close-authority priority) is neither landed nor explicitly deferred

The dig ranks **close-authority priority** as a reusable asset: the old KS=0 /
normal=10 model re-anchored so KSA ≥ force-flat ≥ stop-amendments, adapter-enforced
(qml-original-dig §4.5). QL-9 maps close *reasons* onto the CT-29 taxonomy but says
nothing about **priority / interleaving when two authorities close a position**. It is
node/Book-runtime territory (which QL-1 excludes), but the spine never states that
disposition, so a ranked asset the lens must account for silently disappears.

**Fix:** Add a QL-9 sentence or a Deferred-table row: "**close-authority priority**
(how force-flat / KSA / stop-amendments interleave) is node/Book-runtime territory,
seeded by AD-29's authority order + AD-33; the QML bot emits intents and relinquishes,
owning no closure priority — nothing foreclosed for the node sitting."

### F4 — LOW — Dig asset #4 (exam/live parity of stop policy) only half-dispositioned

QL-7 delivers the **bot-surface** half of parity cleanly ("prevents live/backtest bot
surfaces diverging"; one protocol both hosts; deterministic). The dig's asset #4 is the
*other* half — stop-policy parity between backtest-replay and live feeding
`offer_per_seat = D/(B·b·Lbar)` seat pricing (qml-original-dig §4.4). That half is
Book/BMS/backtesting territory (GAP-0048 parity contracts) and correctly outside QML,
but the spine never says so, leaving the ranked asset without a cited home.

**Fix:** One line in QL-7 or QL-10: "stop-policy / Lbar exam-live parity is Book +
backtesting (GAP-0048 parity-contract) territory; QML delivers only the bot-surface
half via QL-7's single protocol."

### F5 — LOW — Dig asset #6 (survivor mechanics) only partially cited

QL-9 lands the bot-facing survivors — one-shot BE (AD-34), full-stop losers
(AD-40/AD-41), TP-trail (later Book version). The remaining survivor mechanics the dig
lists (§4.6) — **WAL + broker-reconciliation restart, amendment idempotency threshold,
conservative fail-safe "when in doubt, do not widen risk"** — are neither cited nor
dispositioned. They are venue/node-runtime law (venue order-state machine GAP-0035..38;
AD-33 amend protection), so this is a citation-completeness gap, not a substantive hole.

**Fix:** A half-line in QL-9: "the remaining survivor mechanics (WAL/reconciliation
restart, amend idempotency, conservative-widen fail-safe) are venue/node-runtime law
(venue order-state machine + AD-33 amend protection), out of QML scope."

### F6 — LOW — The old anti-sprawl complexity gate has no successor and no stated disposition

Old QML made bots uniform partly through a **machine complexity gate**
(`max_acceptable_complexity_score`; `BotSpecEvaluationSnapshot.complexity_score` 0..100;
qml-original-dig §1.2 device 4, §1.4). The QML conformance gate (QL-8) is deliberately
technical-only (schema, determinism, no-I/O), so dropping a complexity/quality score is
plausibly *intentional* under AD-32's no-performance-gate law — but the spine never
says so, so a concrete old device silently disappears.

**Fix:** One line (Deferred table or QL-8): "the old `max_acceptable_complexity_score`
anti-sprawl gate is **not revived** — conformance is technical-never-performance
(AD-32); any complexity/quality signal is a later measure, not a registration gate."
State the drop so it is a decision, not an omission.

---

## Net

The spine is a faithful thin-consumer reconstruction and answers every operator
question the sitting was given. The gaps are all **stated-disposition** gaps, not
wrong rulings: the QL structure is correct but leaves five items (two BotSpec formula
components, three ranked dig assets, one old device) without an explicit home. Each is
closable with a single sentence; none requires reopening a QL ruling. F1's
min-RR-before-entry and F2's CT-28 are the two that could actually cause loss if the
doc-factory absorbs the spine as-is.
