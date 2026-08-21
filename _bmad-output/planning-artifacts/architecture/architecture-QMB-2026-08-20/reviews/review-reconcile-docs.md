---
review: QMB architecture spine — reconcile vs docs/ knowledge base
lens: RECONCILE (does QMB contradict, silently omit, or fail to adopt what docs/ already ratified)
reviewer-role: gate reviewer (docs-reconcile lens)
target: _bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md
docs-root: C:/Users/Mubarak/Desktop/QMX/docs
qmf-spine: _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md
date: 2026-08-20
---

# Verdict

The QMB spine is **substantively sound and well-grounded** in the ratified corpus — its
gap citations (GAP-0047/0048/0049, GAP-0016/0017, ticket-008), its world model
(replay legal, simulated reserved until GAP-0048), its data posture (CT-10/CT-15,
download-once, Dukascopy, bid+ask, licensing gate open), its concurrency stance
(process-per-run, no Ray/Docker/daemon, no central service), and its vocabulary
("library"/"CLI", never "engine") all reconcile cleanly with docs/. **No hard
contradiction of a ratified DEC/contract/law was found.** The material problem is
one of **adoption, not conflict**: the single most-consumed contract for what QMB
produces — **CT-32 (performance-result container)** — is a fully-specified,
ratified-shape contract that QMB restates in its own words but never binds or adopts;
and the ratified journal (CT-13) that QMB's run loop directly feeds is never cited.
Plus a cluster of citation-hygiene defects (dead-decision ids, wrong law number).

Answer to the framing question (task item 4): **CT-32 is NOT a skeleton awaiting
this work.** It is `status: provisional`, `version: 1`, `wiring_status: defined-unwired`
— AD-41 ratified the container shape; the doc stays provisional pending corpus
re-ratification (DEC-0155), and it is explicitly waiting for **the software factory
to ship it**. QMB is that shipping vehicle. CT-32 already fixes the fields QMB's
"canonical result artifact" must align with.

---

# Findings (most-severe first)

## [HIGH] F1 — B-10's canonical result artifact reinvents CT-32 instead of adopting it

**docs:** `docs/contracts/ct-32-performance-result.yaml` (owner COMP-QMF-RISK; AD-41;
DEC-0155/0154/0146/0158). **QMB:** B-10, frontmatter `binds: [… CT-32 …]`, Capability map
row "Algorithm reports".

CT-32 is a complete, ratified container with mandated fields:
`result_label` (full AD-12 label + account-binding role), a **fingerprinted `population`
declaration** (Bot identity; binding-record fingerprints in/out; account roles;
instruments; AD-35 cohort key), a declared `period` (AD-8 Interval + calendar id/version
+ knowledge-time bound), an ordered `measure_set` where **every quantity carries a
unit-kind from the closed AD-40 vocabulary** (money/price-delta/quantity/value-factor/
r-multiple/rate/count/dimensionless-ratio/duration/instant — null unit-kind is a refusal),
`suppression_accounting` (counts by authority+reason), `veto_accounting` (counts by door),
a `baseline_pointer`, and a per-metric `metric_contract_format_version`.

QMB's B-10 independently re-derives several CT-32 rules almost verbatim — "unit-kinded
exact-money metrics (the named metric set, versioned — metric arithmetic changes mint a
contract version)" is exactly CT-32's "a performance metric is a governed producer under
AD-23 … an arithmetic change is a format-version mint." But B-10 names its own shape
("unit-kinded exact-money metrics, chart series as data, the trade record"), cites CT-32
**only in the frontmatter binds list and never in the body**, and omits CT-32's mandated
fields — most consequentially **`suppression_accounting` and `veto_accounting`**. A
backtest run loop refuses/suppresses through SQS (AD-39), protection windows (AD-38), and
the admission door; without those counts in the result, a month of spread-blocked or
window-blocked entries reads as collapsed decision quality with no recorded cause — the
exact misreading CT-32 exists to prevent ("so neither our arbitration nor our doors ever
read as decay").

Under **L31/DEC-0122** ("everything downstream of QMF … must be built with QMF libraries
and must not re-implement or bypass the framework's contracts"), a QMB "canonical result
artifact" that parallels CT-32 is a re-implementation of the framework's performance-result
contract. CT-32 is `defined-unwired` precisely awaiting the factory; QMB is the natural
place it gets wired.

**Fix:** rewrite B-10 so the canonical result artifact **is a CT-32 performance-result**
(produced through qmf-risk's CT-32 surface, composition-root-wired), adopting `result_label`,
`population`, `period`, the AD-40-unit-kinded `measure_set`, `suppression_accounting`,
`veto_accounting`, and per-metric contract format version. Declare QMB's genuine additions
— chart series as data, the downsampled trade/candle series — as **explicit QMB extensions**
alongside the CT-32 core (they are legitimately absent from CT-32, which is measure-set
focused). This is feasible without friction: CT-32 nullability already lets `baseline_pointer`
be absent on a non-decay backtest and lets suppression/veto default to zero counts, so a
replay-world backtest fits the container cleanly.

## [MED-HIGH] F2 — The run loop feeds CT-13's journal but the spine never cites CT-13

**docs:** `docs/contracts/ct-13-journal.yaml` (seven event types: decision, order, fill,
risk transition, promotion, data quality, control action; N append-only writer-scoped
streams; instantiated per world; DEC-0119/0109/0150/0158); AD-21. **QMB:** B-2 (run loop
emits decisions/orders/fills), B-4 ("append-only per-run logs" + one completion ledger),
B-10 ("the trade record").

QMB's event-slice loop produces exactly `decision`, `order`, and `fill` events (and, via its
doors, `control action` / `data quality`) — the ratified CT-13 taxonomy — in the **replay**
world (a legal QMB world). Yet **CT-13 is cited nowhere in the QMB spine.** B-4 speaks of
"per-run logs" and B-10 of "the trade record" as bespoke artifacts, with no mapping onto
CT-13's seven event types or its writer-scoped, per-world stream model. This risks a QMB
run bypassing the ratified journal — again an L31 concern — and it collides with CT-11's
evidence rule that **only raw-archive and journal formats are evidence-bearing** (everything
else is a rebuildable view): a bespoke "trade record" that is neither is not evidence under
CT-11.

**Fix:** state in B-4/B-10 that the run loop's decision/order/fill (plus control-action and
data-quality) events are **CT-13 journal events written to replay-world writer-scoped
streams** (CT-11 room-role `journal`, per-world), and that B-10's "trade record" is a
read-view/projection over those events (or the fill observations), not a new evidence
format. Keep the completion ledger (F5) explicitly as an index/view over CT-32 results +
CT-13 journals, not as a substitute evidence-bearing format.

## [MED] F3 — GAP-0016/0017 are re-deferred, but docs assign them to *this* sitting

**docs:** `docs/gap-report.md` L19 ("2 deferred to **the backtesting sitting** — GAP-0016
look-ahead/causality registration gate and GAP-0017 attempt counter, per DEC-0121");
QMF spine Deferred ("Look-ahead registration gate + attempt counter … Operator-deferred to
the backtesting sitting"); AD-18 ("evidence checklist … causality slot ← backtesting").
**QMB:** Deferred list ("GAP-0049 + GAP-0016/0017 … operator-deferred").

The corpus routes GAP-0016/0017 to "the backtesting sitting," and QMB **is** the backtesting
sitting (GAP-0048). QMB re-defers them to a follow-on search-campaign sitting. That is a
legitimate scope split — QMB does deliver look-ahead **prevention** mechanically (B-2 frontier
clock forbidding time-arithmetic look-ahead; B-8 split-manifest train/test enforcement;
B-12 declared stream sets forbidding ad-hoc cross-stream reads) — but the corpus expects the
backtesting sitting to close the **registration gate** and **attempt counter**, and AD-18's
promotion causality slot depends on GAP-0016 landing somewhere.

**Fix:** distinguish, in the Deferred entry, look-ahead **prevention** (delivered here by
B-2/B-8/B-12) from the GAP-0016 registration **gate** and GAP-0017 counter (operator-deferred);
cite the operator ruling that authorizes deferring them past this sitting; and note the
downstream dependency (AD-18 promotion causality slot / GAP-0016).

## [MED] F4 — Promotion-card and admission evidence feeds (AD-18 / AD-32) are not stated

**docs:** AD-18 ("evidence checklist … untouched-test proof ← data splits; causality slot ←
backtesting"); AD-32 (admission-bar evidence + three-layer packet); CT-32 ("one kind serving
both the AD-32 admission-bar evidence and the analyst's report"). **QMB:** B-4/B-10 connect
to "the Book sets the bar" (AD-32/AD-41) but never to the AD-18 promotion card.

QMB's results are the corpus's designated source for the promotion card's **causality
evidence slot** and for AD-32 admission evidence, yet the spine only says its ledger is "what
'the Book sets the bar' reads." The promotion-card / admission-evidence linkage — and its
guardrail (a replay-world result is not itself live-gating; governed-evidence use rides
GAP-0048) — is left implicit.

**Fix:** add to B-10 (and/or B-4) that CT-32 results feed the AD-18 promotion-card causality
evidence slot and AD-32 admission evidence, with the explicit caveat that replay-world
evidence does not by itself gate live money (see F5) and that governed-evidence admission of
these artifacts is gated by GAP-0048.

## [MED] F5 — Completion-ledger verdict must be per-requirement + world/parity-caveated

**docs:** AD-32 ("each requirement passes or fails on its own terms … no composite score,
rating, tier band, or weighted aggregate may express a bar"); CT-32 ("no score, rating, tier
band, or weighted composite may express a result"; "measurement publishes, never acts");
AD-29 (replay and live are "deliberately incomparable by binding"; a replay of a binding
mints a different binding identity); AD-32 parity ("a paper role may never gate live money").
**QMB:** B-4 ("the unbiased end verdict (pass/fail against the Book's declared bar; `unrated`
when the bar is not yet ruled)").

Two reconciliations needed. (a) A single "pass/fail against the bar" must be the **conjunction
of per-requirement verdicts** (each requirement on its own terms), never an aggregate
score/rating/tier — otherwise it collides with AD-32/CT-32's composite-ban. (b) A backtest is
**world=replay**; per AD-29 replay evidence is incomparable-by-binding to live, and AD-32
gates live money on world/account-role + producer-version parity. So a QMB replay-world
"verdict vs bar" is an experimentation read that **cannot itself satisfy a live-gating bar**.
QMB's "unrated" also duplicates CT-22/AD-32's `not-yet-ruled` threshold tag — align the word.

**Fix:** in B-4, state the verdict is the per-requirement conjunction (not a composite), that
a replay-world verdict does not satisfy a live-gating admission bar (AD-29/AD-32 world+parity),
and prefer `not-yet-ruled` over `unrated` to match the CT-22 threshold vocabulary.

## [LOW-MED] F6 — Inherited row cites DEC-0084..0086 (dead decisions) as live "kernel rulings"

**docs:** `docs/gap-report.md` L199-201 and `docs/knowledge/traceability.md` L107-109 mark
**DEC-0084, DEC-0085, DEC-0086 as `dead`** — they are the *rejected* options
(DEC-0084 = "one centralized always-on backtesting service"; DEC-0085 = "adopt Nautilus
contracts"; DEC-0086 = "three-day adoption spike"), killed by ADR-0011. The live authority for
QMB's principles is **DEC-0013** (build-our-own boundary) plus **ADR-0011** (the deaths). The
QMF spine's own Inherited table records "DEC-0013 (live; DEC-0085/0086 are tombstones)".
**QMB:** Inherited Invariants row "`D1 / DEC-0084..0086 | kernel rulings | No donor code ever
(shapes only); no central always-on service; build-our-own`".

The principle is correct and fully aligned; the citation is inverted — a reader chasing
DEC-0084 finds a statement proposing the *opposite* (a central service). This is exactly what
QMB's "no central always-on service" rejects.

**Fix:** re-cite as **DEC-0013 + ADR-0011** (which kills DEC-0084/0085/0086), matching the QMF
spine's tombstone note; drop the live "kernel rulings" framing of the dead ids.

## [LOW-MED] F7 — Inherited row cites "L21" for applications-outside-QMF; docs L21 is the cTrader law

**docs:** `docs/constitution.md` **L21 = "The first Venue integration must use the cTrader Open
API from Python and must not use MQL." (DEC-0060).** The "application outside QMF, built with
QMF" concept lives in **L7** (QMF is not an application), **L8** (application loops/orchestration
outside the foundation), and **L31/DEC-0122** (built with QMF). **QMB:** Inherited Invariants
row "`L21 | QMF spine | QMB is an application outside the QMF repo scope, built with QMF`".

There is a single ratified law numbering (the QMF spine's Inherited table cites constitution
L5/L6/L20/L27, and QMB's own L6/L20/L31 citations all resolve correctly against
`docs/constitution.md`). Only L21 mis-resolves — against docs it points at the cTrader/MQL law.

**Fix:** re-cite the applications-outside-and-built-with row as **L7 / L8 / L31** (L31 already
appears correctly in a separate QMB row).

## [LOW] F8 — Vocabulary not anchored to the two glossary entries that already name QMB's territory

**docs:** `docs/glossary.md` — **"Future backtesting library"** (L204-206): "*A deferred
modular, on-demand QMF consumer for testing Bot-by-Book behavior. It is outside QMF V1 and is
not a permanent central service, runtime engine, or Simulator UI.*" — and **"Simulator"**
(L670-672): "*A deferred product UI for exploring Bot-by-Book conditions … outside QMF V1.*"
Also **L198**: the experimentation-umbrella / backtesting-verification framing is "*an operator
vocabulary direction recorded 2026-08-20, **not a ratified contract** … a candidate rename for
the future backtesting library (ticket 008), to be settled at the backtesting sitting; until
that sitting rules, no contract or component renames.*" (DEC-0134 keeps the fidelity taxonomy
open.)

QMB **is** the "Future backtesting library," and its Naming convention asserts the
experimentation/backtest split as settled. Both are aligned in substance — QMB honours
"not a central service / not a runtime engine / never an engine," correctly keeps the
"Simulator" product UI deferred (Deferred: "UI rendering — platform territory; consumes B-10
artifacts"), and adopts the recorded operator vocabulary direction. But the spine never anchors
to these ratified entries.

**Fix (docs-hygiene):** (a) reference the glossary "Future backtesting library" entry as QMB's
ratified identity and name the deferred "Simulator" as a downstream consumer of B-10 artifacts,
locking the three-way vocabulary. (b) In the Naming row, acknowledge that QMB is **settling**
the candidate experimentation/backtest rename (glossary L198, ticket 008, DEC-0134) rather than
restating it as pre-existing — this sitting is the one authorized to rule it.

## [LOW] F9 — GAP-0048 partial closure should be reflected back into the gap-report

**docs:** `docs/gap-report.md` L20 treats GAP-0048 ("backtesting library") as one sitting.
**QMB:** frontmatter `binds: [GAP-0048-seams …]`; Deferred splits "GAP-0048 seams" (this spine)
from "GAP-0048 content" (fidelity taxonomy values, forex fill/slippage content, parity
contracts, simulated-time typing that unlocks world=simulated — "needs its own sitting").

This is a sound architecture-vs-content split (the spine is build-substrate; the fidelity
taxonomy is irreversible content), but it leaves GAP-0048 partially closed while the gap-report
still shows it wholly deferred, and CT-10/CT-11/AD-12 all say "the backtesting sitting defines
simulated-time typing" — a reader will expect this spine to have done so.

**Fix (docs-hygiene, on documentation-factory pass):** record GAP-0048 as **partially resolved**
(architecture/seams closed by this spine; fidelity/simulated-time content + GAP-0016/0017/0049
on a named follow-on), citing the operator's split, so the corpus and the spine agree on what
remains open.

---

# Checks that PASSED (reconcile confirmed — recorded so the gate sees the spine's strengths)

- **Worlds.** replay = QMB's legal world; simulated reserved-unusable until GAP-0048;
  paper/demo = world=live. Matches AD-12, CT-10, CT-11 verbatim. B-7 "world derived from
  provenance, never caller-declared" matches CT-10.
- **Synthetic (L6/L20).** B-7 claim classes (random-walk = infra stress only; block-bootstrap
  = robustness; nothing synthetic validates edge) match L20/DEC-0054 and AD-13; store-level
  taint matches CT-11 "simulated-world artifacts unwritable in V1."
- **Data intake (CT-10/CT-15).** B-11 download-once into the immutable raw archive,
  runs-read-only-from-rooms, Dukascopy primary, bid+ask preserved, calendars from QMF calendar
  contracts, licensing gate open — all match CT-15 (active provider COMP-DUKASCOPY; "adapter is
  a called port, not a running downloader"; "legal archiving posture … open operator item") and
  L18/AD-19.
- **Splits (CT-12).** B-8/B-12 train/test via split-manifest reads (AD-21) and B-9 sealed
  evidence never leaving controlled rooms match CT-12 and CT-11's 12-month seal.
- **Fills/costs (CT-25, DEC-0135).** B-6 three separate ports; declared fidelity in the label;
  optimistic taint until GAP-0048; calibration from recorded ticks and CT-25 fill journals;
  per-broker (DEC-0135); "financing/admin fee, 'swap' only colloquially" — all consistent with
  AD-8 (dated fee on swap-free accounts), AD-41 `cost_components`, and CT-25.
- **Concurrency / no central service.** B-5 process-per-run, WriterId streams, no Ray/Docker/
  daemon, no runtime capture — matches AD-15, CT-11 WriterId model, and the death of DEC-0084
  (central service). B-5's 12–14-run figure is correctly hedged as an AD-13 motivating reference,
  not a validated budget.
- **Config compiler (B-3).** Book/BMS fragments as generated, schema-validated, fingerprinted
  DERIVED artifacts carrying AD-16 lineage edges, "never a newly minted registry kind" — the
  correct posture under AD-16/AD-30; consistent with CT-22/CT-27 (templates are JSON-Schema-class
  config artifacts identified by fp1; bindings cite by fingerprint).
- **Vocabulary law.** "library / CLI, never an engine" matches the QMF Conventions banned list
  ("'engine' for backtesting" banned); "experimentation" umbrella / "backtest" stage matches the
  operator direction recorded at glossary L198 (candidate now being settled — see F8).
- **Gap grounding.** GAP-0047 (QML), GAP-0048 (backtesting library), GAP-0049 (SR*/search-quality),
  GAP-0016/0017, ticket-008 all exist and are correctly characterised in
  `docs/gap-report.md` (L19-20, L126-127, L139) and the QMF spine Deferred table.
- **QML/bot deferral.** B-… Deferred "QML bot schema (GAP-0047) … QMB tests plain-Python bots …
  QML conformance gates governed evidence, not tunnel entry" matches L33 (plain-Python authoring
  legal; graduation into governed evidence via the extension shape) and GAP-0047.
- **Prop-firm socket.** Deferred "Prop-firm Books — socketed upstream (DEC-0082); nothing may
  preclude them" matches AD-8/AD-29 prop-firm sockets and AD-40 baseline discipline.
