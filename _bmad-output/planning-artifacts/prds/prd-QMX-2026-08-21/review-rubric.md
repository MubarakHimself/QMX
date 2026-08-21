# PRD Quality Review — QMX Platform PRD

**Reviewed:** `prd.md` (439 lines, `status: draft`) + `addendum.md`
**Rubric:** `.claude/skills/bmad-prd/assets/prd-validation-checklist.md`
**Calibration:** solo operator, load-bearing (chain-top — feeds `bmad-architecture` reconciliation → epics-and-stories → factory lanes). Deliberately lean-but-complete; depth lives in the cited `docs/` corpus.

## Overall verdict

This is a disciplined, unusually honest capability spec whose citation layer holds up under audit — every `docs/` ID I checked resolves, every enumerated count matches its contract verbatim, and every contract CT-01 through CT-34 except the deferred CT-08 has at least one FR standing over it. The document earns its leanness: it is a pointer architecture, and the pointers are real.

What is at risk is the handoff, not the thinking. The Primary success measures (§9) are adjectives rather than tests; the QMB block compresses a thirteen-spec library into eleven epic-sized FRs while `qmf-core` gets five FRs for a far smaller surface; §1's "V1 goal" names roughly nine deliverables where §5 carries FRs for about thirteen; and there is no vocabulary anchor for domain nouns the FRs lean on hardest ("tunnel entry," "charter doors," "benching," "SQS"). None of this is a rewrite — it is one pass over §1, §5's preamble, §9, and a Glossary pointer. Fix those four and this is a genuinely strong chain-top PRD.

---

## Decision-readiness — strong

The PRD states decisions as decisions and names what was given up. §5 does not hedge: `world=simulated` is "reserved-unusable in V1" (FR-005), admission is "three technical layers with **no probation and no paper-performance gate**" (FR-028), performance measurement "publishes and never acts; **no composite score** gates money" (FR-034), and FR-044 concedes outright that "all fills are `optimistic`-tainted and **no verdict-bearing backtest ships** until GAP-0048 closes." That last one is a PRD volunteering that its own headline capability cannot yet produce a trustworthy verdict. That is the opposite of smoothing to neutral.

The counter-metrics in §9 are the strongest single passage in the document because they name the specific failure the metric invites: *"a platform easy to run because it skipped the doors is a failure"* and *"if a library only works inside the QMX repo, the external-agent test fails."* These are not decorative — they close the exact loophole each Primary measure opens. Likewise §10 row 5 keeps **DEC-0049** (may auto-detectors mutate trading state) formally open with "Operator ruling needed" rather than quietly resolving it; I confirmed it is still `open` in `docs/gap-report.md:187` and `docs/knowledge/traceability.md:72`. Row 8 refuses to assume GitBook and `docs/` already agree on QML framing. Both are live tensions, honestly parked.

Where it slips: the Standing-status paragraph and §10 row 1 leave the whole document in a limbo a later reader cannot resolve — "conditional sign-off go-ahead," flipping "once an independent contradiction sweep passes," status "In progress (this session)." A reader opening this in October cannot tell whether implementation is authorized. And for a PRD carrying this much deferred material there is not a single `[NOTE FOR PM]` callout (count: 0), so the tensions that *are* named live only in a table at the very end rather than at the point of use.

### Findings

- **medium** Standing status has no resolvable state (§ Standing status; § 10 row 1) — "In progress (this session)" is unreadable outside the session that wrote it, and it gates the entire document's authority under L29. *Fix:* replace with a checkable condition and owner — e.g. "signed-off when `_docwork/stage_state.yaml` `ratification` reads `operator-signed`; until then L29 applies" — so any later reader can verify the state from the repo.
- **medium** Zero `[NOTE FOR PM]` callouts despite three live tensions (§ 10 rows 5, 8; § 2 terminal-phase assumption) — DEC-0049's unresolved auto-detector authority, the GitBook/`docs/` QML divergence, and the inferred Phase-3 terminal slot are all real forks that a downstream reader meets in §5/§6 but only learns about in §10. *Fix:* place one callout at each point of use (FR-010/§C for DEC-0049, FR-047/§H for the GitBook divergence, §6 for the terminal slot).
- **low** Struck-through "Closed" rows kept in the live table (§ 10 rows 6, 7, 9) — three of ten rows are resolved history, diluting the five that need attention. *Fix:* move them to a "resolved during drafting" line beneath the table.

---

## Substance over theater — strong

Almost nothing here is furniture. §3 names three actor classes and immediately disqualifies one of them from being a user at all — "**Bots** (in-platform actors, not users)" — which is the anti-persona-theater move. There are no personas, no differentiation section, no market framing. The Vision (§1) could not swap into another PRD in this category: "bot → Book → BMS → operator" and "the operator's in-flight powers are limited to resurrection, periodic review, and ratification" are load-bearing sentences that constrain §5's FRs directly (FR-027, FR-009).

The NFR set (§8) is the clearest tell. NFR-01 names CPython 3.14 and two tier-1 OS targets. NFR-02 names a coverage floor of 80% and 100% branch coverage on CT-01/CT-02 modules specifically — not "high coverage." NFR-04 is the anti-boilerplate NFR: rather than inventing a latency budget it declares **"measure-then-budget: no invented numbers"** and states the one constraint that is actually known (qmf-core import under ~1s) against a named reference workload (~40 bots at the 10/100/200 marks). A PRD that refuses to fabricate a threshold and says so is doing the opposite of NFR theater.

I spot-checked the claimed novelty and it is not claimed — there is no innovation section, and the one framing device ("we are building React and its documentation before we build the website") is used as a scope discipline, not as differentiation. Correct restraint.

### Findings

- **low** One boilerplate clause in an otherwise product-specific NFR set (§ 8, NFR-10) — "Monitoring and evaluation are built in, not bolted on" is the single sentence in §8 that would survive a copy-paste into any PRD. *Fix:* replace with the thing it actually means here — failures surface as CT-04 typed refusals and CT-13 journal events, so diagnosis reads evidence rather than logs (which §9 already says better).

---

## Strategic coherence — strong

The PRD has a thesis and bets on it visibly. The thesis is stated twice — §1's *"we are building React and its documentation before we build the website"* and §2's delivery-sequence quote *"why would you build something before the framework that is meant to build it comes in"* — and §2's phase table is that thesis executed: QMF/QMB/QML get full FRs, the trading node and terminal get capability outlines with no FRs, QMA gets a named boundary only. Prioritization follows the thesis rather than ease; the trading node is the *older, better-designed* piece and it is still deferred, with the PRD stating the expensive consequence out loud ("a high chance it is rewritten using QMF").

Scope kind is coherently **platform**, and §7's exclusions track it: everything cut is either a surface above the foundation (terminal, Simulator, charts front-end) or a capability the foundation deliberately does not yet type (`world=simulated`, margin-aware sizing, multi-currency). Nothing is cut because it was hard.

One inversion is worth naming. The thesis is about foundation stability, and §9 has exactly the right test for it — *"QMB and QML build against QMF's published contracts without patching the framework — the 'React before the website' test."* But that test sits under **Supporting (proposed, kept from the draft)** while the Primary lens measures operability. The document's own bet is therefore measured in the demoted tier, and the tier label ("proposed, kept from the draft") reads as lower confidence than the rest of §9. If the factory optimizes to the Primary lens, it optimizes for something adjacent to the thesis rather than the thesis.

### Findings

- **medium** The thesis's own test is demoted to Supporting (§ 9) — "Foundation stability … the 'React before the website' test" is the direct validator of §1's stated bet, yet it sits under a tier labelled "proposed, kept from the draft," beneath a Primary lens about deployability and repairability. *Fix:* either promote foundation stability to Primary alongside the DevOps lens, or state explicitly that the DevOps lens is the *gating* measure and foundation stability the *thesis* measure — both required, different jobs. Also drop "proposed, kept from the draft," which reads as unratified.

---

## Done-ness clarity — thin

This is the dimension the epics-and-stories pass will lean on hardest, and it is where the PRD's leanness stops paying for itself.

The good half is genuinely good. Most FRs carry a consequence an engineer can write a test against, because the invariant *is* the test: "binary floats are banned on the money path and treated as a taint" (FR-001), "refusals are returned, never raised" (FR-004), "cross-world reads are refused" (FR-011), "exactly five kinds under the four-outcome law: timeout is not rejection, UNKNOWN is a state not an error" (FR-023), "every virtual close mints exactly one exit record" (FR-032), "same config → same results" (FR-037), "identical run configs produce byte-identical CT-32 artifacts" (NFR-03). Roughly forty of the fifty FRs are falsifiable as written, and each cites the artifact carrying acceptance depth. That is a better hit rate than most PRDs achieve with ten times the words.

The failing half is concentrated in two places. First, §9's **Primary** measures — the ones the PRD elevates above all others — are the least measurable content in the document: "install and run **without ceremony**," "Deploying to a server must be **unremarkable**," "finding and fixing it **takes little**." Every one of these is exactly the "system handles X gracefully" shape the rubric asks me to flag, and they are load-bearing here because §9 says to *judge V1* by them. The Supporting tier, by contrast, is fully testable ("100% of V1 FRs trace to ratified docs/ IDs," "byte-identical CT-32 artifacts," "zero float taints … enforced by gate tooling, not review"). The measurability is inverted relative to the priority.

Second, FR granularity in §5 G is an order of magnitude off the rest of the document. **FR-039** carries nine distinct capabilities in one requirement (typed search space, objective plus constraints, train/test/locked-validation discipline, TPE sampler, grid sampler, resume, cost estimation, anti-overfit sensitivity report). **FR-046** carries four separate delivery surfaces (the `qmb` CLI, the Python API, notebooks, an optional MCP door). Each is an epic. Meanwhile **FR-003** is "Instrument identity is an opaque, never-parsed `(venue, symbol)` pair" — one afternoon. The eleven FRs FR-036..FR-046 stand over what the corpus carries as roughly thirteen separate QMB specs. The PRD does cite the spec name after each (`spec-optimization`, `spec-multi-routes`, …), which is the saving grace — but it never *says* that the cited spec is the unit of work, so a story generator reading FR-039 as one requirement will produce one under-specified epic where thirteen specs' worth of scope lives.

### Findings

- **high** Primary success measures are unmeasurable as written (§ 9, "the DevOps lens") — "without ceremony," "unremarkable," "takes little" cannot pass or fail, yet §9 instructs the reader to judge V1 by them, and the measurable tier sits below. *Fix:* give each Primary bullet one literal executable test. Deployability: a clean-machine script that runs `uv add qmb` on both tier-1 OSes and completes a canned backtest end-to-end, with no DB server and no Docker, in under a stated wall-clock. One-person operability: a named set of injected failures (venue UNKNOWN, corrupt store partition, missing calendar pin) where the first diagnostic step is reading a CT-04 refusal or CT-13 event, not a stack trace. External usability: an agent given only the published package docs and a fresh venv builds a bot and produces a CT-32 artifact, scripted as an acceptance run.
- **high** FR granularity in §5 G is epic-sized where §5 A is task-sized (§ 5 G, esp. FR-039, FR-046; contrast FR-003) — FR-039 bundles nine capabilities, FR-046 bundles four doors, and eleven FRs stand over roughly thirteen QMB specs, so the epics-and-stories pass will size the QMB lane far below its real scope. *Fix:* do not bloat the PRD — add one line to §5's preamble making the mapping explicit: "each FR's cited artifact is the epic boundary and the source of its acceptance criteria; where an FR cites a `spec-*` document, that document is one epic." Optionally split FR-039 into search-space/sampler, discipline, and reporting, and FR-046 into CLI and library-surface FRs.
- **medium** FR-050 states an ownership fact with no testable consequence (§ 5 H) — "QML defines the bot runtime protocol that QMB (and later the trading node) hosts" is a boundary assignment, not a requirement; nothing here can pass or fail. *Fix:* add the consequence that makes it verifiable — a bot conforming to the protocol runs unmodified under both hosts, and a host-specific behavioral difference is a defect (this is also what makes ADR-0018's "verdict is host-independent by construction" testable).
- **medium** FR-016 names no engines and no seam contract (§ 5 C) — "a dependency-free store seam over swappable local engines" leaves both the seam and the swap set undefined, while `docs/architecture/overview.md` names four concrete stores (Parquet, DuckDB, SQLite, JSONL) each behind a QMF-owned contract with stdlib-typed boundary signatures. The PRD is *less* specific than the corpus it cites, and it cites a component rather than a CT. *Fix:* name the four engines and which are V1-required, and cite the store contract rather than the component.
- **low** Two unbounded phrases in otherwise-testable FRs (§ 5 G, FR-037 "intra-bar fill fidelity," "cancel/observe while running"; FR-045 "a governed concurrency cap") — the first two have no stated bound or observable; the third is honestly deferred by NFR-04's measure-then-budget rule, which is worth stating inline so a reader does not read it as an oversight. *Fix:* bound FR-037's two clauses (what fidelity, observable how; what "cancel" guarantees mid-run), and tag FR-045's cap as NFR-04-deferred.

---

## Scope honesty — strong

§7 does more work than any other section. Omissions are not left to inference: `world=simulated` is excluded *with its unblocking condition* (GAP-0048's fidelity taxonomy); margin-aware sizing, non-USD numeraire, prop-firm Books, L2 depth, `close_partial`, and swap-Wednesday are each named individually rather than swept under "advanced features"; futures and options are marked **"permanently excluded"** — a distinct commitment from deferral, and rare to see stated. §6 is equally disciplined: three future phases each get a capability outline explicitly labelled "no V1 FRs," and QMA's status is given as "**research — ideation has not begun**" rather than dressed as a roadmap item. De-scoping is proposed out loud, never done silently.

The open-items density is healthy for the stakes: seven live rows in §10 plus two `[ASSUMPTION]` tags across a fifty-FR chain-top PRD, and the blocking one (corpus sign-off) is named as blocking. This is not a PRD hiding its unknowns.

Two gaps. There is no **Assumptions Index** — the rubric's roundtrip check fails in one direction: two `[ASSUMPTION]` tags in `prd.md` (§2 terminal placement; §6 terminal capability list) and one in `addendum.md`, none indexed. And the addendum's assumption is now *stale in a way that contradicts the PRD*: `addendum.md:48-50` tags QMA as "[ASSUMPTION — confirm before it appears anywhere binding]," while §10 row 7 records it "CONFIRMED by operator dictation 2026-08-21" — and QMA has meanwhile appeared in the §2 phase table and as a §6 heading. Two documents in the same workspace state opposite things about the same name.

### Findings

- **medium** No Assumptions Index, and the addendum contradicts the PRD on QMA (§ 2, § 6 tags; `addendum.md` § Naming notes vs. § 10 row 7) — the addendum still gates the QMA name on confirmation "before it appears anywhere binding," which it now does in two PRD sections that §10 declares confirmed. *Fix:* add a three-line Assumptions Index at the end of `prd.md` (terminal Phase-3 slot; terminal capability list; anything surviving from the addendum), and update `addendum.md` to record QMA as confirmed with its date rather than tagged.
- **low** Permanent exclusions and MVP deferrals share one list (§ 7) — "Futures and options (permanently excluded)" sits in the same bullet run as "ML extras, live/streaming charts … (all deferred by QMB rulings)," so a reader scanning for revisit candidates cannot separate "never" from "not yet." *Fix:* split §7 into "Never" and "Not in V1," or mark each bullet.

---

## Downstream usability — adequate

This PRD is chain-top and says so in its own Audience block, so this dimension carries real weight — and the mechanical half is excellent. FR-001..FR-050 are contiguous, unique, no gaps or duplicates; NFR-01..NFR-10 likewise. I resolved every category of citation against the repo and found **zero broken references**: all thirty-four `CT-*` files exist; ADR-0002 and ADR-0006..ADR-0018 exist; SCN-0002..SCN-0012 exist; every cited constitution law (L2, L7, L13, L14, L17–L20, L29, L30, L34–L39) is present in `docs/constitution.md`; DEC-0049 is genuinely still `open`; DEC-0121, DEC-0159 and DEC-0185 all resolve; GAP-0016/0017/0048/0049 carry exactly the statuses §10 claims. Sections also survive being pulled out alone — §5's groups are self-contained and there is no "see above."

Better still, I checked §5's coverage against the contract set: **every contract CT-01 through CT-34 has at least one FR standing over it, except CT-08** — and CT-08's absence is correct, matching GAP-0016's deferral, which §9's own traceability metric states as the exception. That is a real completeness proof, and it is the strongest structural property of the document.

Three things will still cost the downstream reader. First, there is **no Glossary and no pointer to one**, despite `docs/glossary.md` existing. §5 uses domain nouns exactly once, undefined, with no local anchor: "**tunnel entry**" (FR-048) appears nowhere else in the PRD and is unguessable; "charter doors" (§1, FR-027), "benching … a read-time fold" (FR-034), "SQS" (FR-035, expanded nowhere), "fidelity taint," "room-roles," and "footprint" are the same. The rubric's first check on this dimension is a Glossary, and a one-line pointer would satisfy it.

Second, §5's component groupings quietly flatten a distinction the corpus treats as load-bearing. §5 D lists `qmf-calendar-forex` alongside `qmf-indicators` and `qmf-structure` as peers, but `docs/components/qmf-calendar-forex.md:17` and `overview.md` §"Package shape" put it **outside the seven-package roster, on its own SemVer ladder rather than the roster's lockstep versioning**. §5 C's heading "(qmf-data, -store, -backup, -ingest)" presents four peers where `overview.md:94` states `COMP-QMF-DATA-INGEST/-STORE/-BACKUP` "are internal seams of `qmf-data` … they do not enlarge the public roster." A factory lane reading §5 as its package list will mis-scope packaging, versioning, and release mechanics.

Third — and this is the one that will bite epic sizing — §1's V1 goal sentence and §5's FR set disagree on how much V1 is. §1 says "**QMF's seven packages plus QMB and QML**" — nine deliverables. But §5 carries FRs for at least four more: FR-021 (`qmf-calendar-forex`, outside the seven), FR-017 (dukascopy adapter), FR-018 (calendar-feed source), FR-026 (cTrader adapter). Each is a separate component spec in `docs/components/`. Anyone scoping the build from the quotable §1 sentence undercounts by roughly a third.

Journeys are fine, and better than they look: §4's seven bullets are unnumbered, but the FRs already cite the matching SCN IDs throughout (FR-009→SCN-0007, FR-010→SCN-0002, FR-012→SCN-0003, FR-014→SCN-0004, FR-023→SCN-0005, FR-029→SCN-0006, FR-033→SCN-0008/0010, FR-034→SCN-0011, FR-036→SCN-0012, FR-041→SCN-0009). The journey↔FR link exists; it is just never declared, so a reader must notice it.

### Findings

- **high** No Glossary and no pointer to `docs/glossary.md` (§ Audience block; § 5 throughout) — "tunnel entry" (FR-048), "charter doors" (FR-027), "benching" (FR-034), "SQS" (FR-035, never expanded), "fidelity taint," "room-roles," and "footprint" each appear without definition or anchor, and the rubric's first downstream check is an exact-vocabulary source. *Fix:* one line in the Audience block binding PRD vocabulary to `docs/glossary.md` verbatim, plus a short local table for the eight-to-ten nouns §5 leans on hardest so the PRD stands alone for a first-time reader.
- **high** §1's V1 goal undercounts §5's own FR set (§ 1 "V1 goal" vs. § 5 FR-017, FR-018, FR-021, FR-026) — "QMF's seven packages plus QMB and QML" names nine deliverables where §5 carries FRs for roughly thirteen, omitting the calendar extension and the three first adapters (dukascopy, calendar-feed, cTrader), each of which has its own component spec. *Fix:* restate as "the seven roster packages, the `qmf-calendar-forex` extension, the first source and venue adapters (dukascopy, calendar-feed, cTrader), plus QMB and QML."
- **medium** §5 flattens roster membership (§ 5 C heading, § 5 D) — `qmf-calendar-forex` is presented as a peer of two roster packages though `qmf-calendar-forex.md:17` places it "outside the seven-package roster, on its own SemVer ladder," and `-store`/`-backup`/`-ingest` are presented as peers of `qmf-data` though `overview.md:94` calls them internal seams that "do not enlarge the public roster." *Fix:* mark the extension and the three seams inline in the group headings; the packaging and lockstep-versioning consequences are a factory concern.
- **medium** Success Measures carry no IDs and no FR cross-references (§ 9) — no SM-1..N numbering means nothing downstream can cite a measure, and no measure names the FRs it validates, so the traceability the PRD demands of itself in §9's own first Supporting bullet is not applied to §9. *Fix:* number them SM-1..SM-n plus SM-C1..SM-Cn for counter-metrics, and cite validated FRs on each.
- **low** The journey↔FR link exists but is never declared (§ 4) — the seven journeys are unnumbered bullets, yet ten FRs already cite the corresponding SCN IDs. *Fix:* one line under §4 — "each journey's FRs cite its SCN ID; SCN-* IDs serve as this PRD's UJ IDs" — turns an implicit convention into a usable one.

---

## Shape fit — strong

The PRD has been shaped to the product rather than to the template, and the calls are the right ones. Per the rubric's own guidance, a single-operator internal platform takes **capability-spec shape**, UJs become overhead, and SMs run operational rather than user-facing — which is precisely what this document does. §5 is capability-grouped by component with no user-story framing; §9's Primary lens is explicitly operational ("judge V1 like a senior DevOps engineer serving a one-man army"); §3 has no persona section and instead names three actor classes, disqualifying one from user status.

The UJ decision is the notable one. Rather than authoring UJs to fill a slot, §4 says outright *"The corpus's golden scenarios are the ratified journeys; the PRD lists the load-bearing ones rather than re-authoring them"* and points at SCN-0002..SCN-0012. That is the correct anti-over-formalization move for this shape, and it avoids duplicating ratified content — exactly what the PRD's own leanness contract promises. There is no under-formalization risk in the other direction either: this is not a consumer product missing its UJs.

Length is right. About 440 lines for a chain-top platform PRD with fifty FRs sits inside the "as long as its FRs and concerns require" band, and the addendum correctly absorbs the material that would have padded it — form-factor evolution, CLI positioning rationale, three generations of old-version lineage, the reason the old PRD is excluded. The addendum is being used as designed: depth that belongs downstream, not overflow dumped to look thorough.

The one shape the PRD does *not* fully claim is brownfield, and it is right not to: `addendum.md` § "Why the old-version PRD is excluded" establishes that the old codebase is not being extended, so existing-code accuracy is not a live obligation. That is stated, not assumed.

### Findings

None. The shape is fitted, the omissions are reasoned, and the two decisions a reviewer would most likely challenge (no authored UJs, no persona section) are both defended in the text.

---

## Mechanical notes

- **ID continuity — clean.** FR-001..FR-050 contiguous, unique, no gaps or duplicates. NFR-01..NFR-10 likewise. Nothing references an FR or NFR that does not exist.
- **Cross-references — all resolve.** Verified against the repo: all 34 `CT-*` contract files present in `docs/contracts/`; ADR-0002 and ADR-0006..ADR-0018 present; SCN-0002..SCN-0012 present; every cited law (L2, L7, L13, L14, L17, L18, L19, L20, L29, L30, L34, L35, L36, L37, L38, L39) present in `docs/constitution.md`; DEC-0049 confirmed still `open`; DEC-0121, DEC-0159, DEC-0185 all resolve; GAP-0016, GAP-0017, GAP-0048, GAP-0049 carry exactly the statuses §10 states. **Zero broken citations found.**
- **Factual spot-checks — all pass.** Seven typed refusal categories (CT-04 line 17); seven journal event types (CT-13 line 17); exactly five venue command kinds under four outcomes (CT-19 lines 15, 19); seven room-roles instantiated per world with cross-world reads refused (CT-11 line 19); the 12-month no-peek seal (CT-12; `qmf-data.md:91`); three-layer admission with no probation or paper-performance gate (`qmf-risk.md:87`); USD-only numeraire (`qmf-risk.md:147`); R as one relationship with three typed faces frozen at admission (`qmf-risk.md:145`). FR-048 correctly declines to restate QML's layer count, avoiding a collision with FR-028's three — the two are different gates and the PRD keeps them distinct.
- **Contract coverage — complete.** Every contract CT-01..CT-34 has at least one FR standing over it except CT-08, whose exclusion is correct (GAP-0016 deferral) and is stated as the exception in §9's traceability metric.
- **Assumptions Index roundtrip — fails one direction.** 2 `[ASSUMPTION]` tags in `prd.md`, 1 in `addendum.md`, 0 indexed anywhere. No index section exists. See Scope honesty.
- **`[NOTE FOR PM]` count: 0.** See Decision-readiness.
- **Glossary drift — none detectable, but unverifiable.** Terms are used consistently within the PRD (Book, BMS, bot, world, taint, promotion occurrence, binding epoch all hold their form), but with no Glossary and no pointer there is no source to drift *against*. Consistency here is currently an accident of single authorship, not a guarantee.
- **Workspace hygiene.** No `.memlog.md` in `prd-QMX-2026-08-21/` — a later Update or Validate re-entry will hit SKILL.md's bootstrap path (`memlog.py init` + reverse-engineer a thin log) rather than resuming from a real trail. Worth seeding before finalize. `prd.md` carries frontmatter (`status: draft`, correct pre-finalize); `addendum.md` carries none.
- **Section inventory vs. Essential Spine.** Present and doing real work: Document Purpose (as the Audience block), Vision, Target User (§3), Features/FRs (§5), Non-Goals (§7), MVP Scope (§2 + §6 + §7), Success Metrics (§9), Open Questions (§10), plus an adapted Cross-Cutting NFRs cluster (§8). Missing: **Glossary** (§3 of the spine) and **Assumptions Index** (§9 of the spine) — both flagged above. Key User Journeys are deliberately downscaled to SCN pointers, which is a defended drop, not an omission.
