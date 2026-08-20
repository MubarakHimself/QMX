---
review: five-hats
target: ARCHITECTURE-SPINE.md (QMF V1 Foundation, final 2026-08-19, AD-1..AD-14)
lens: five quant-industry user roles walked against the ratified spine and the open gaps
scope: what the REMAINING sittings must not miss — registry (GAP-0014..0019), data (0020..0030), indicators/structure (0031..0034), venue (0035..0038), risk (0039..0046), backtesting (0048/0049)
stance: role-workflow. Ratified ADs are treated as settled; findings are holes the hats fall through, not objections to the ADs.
date: 2026-08-19
findings: 44 (Researcher 10 · Developer 8 · Analyst 8 · Portfolio Manager 8 · Trader 10) + 6 cross-hat conflicts
---

# Five-hats sweep — QMF V1 Foundation spine

## Verdict

The spine is sound as a **substrate** and none of the fourteen ADs fails a hat outright. But the spine was ratified along a *primitives* axis, and the hats cut across it along a *workflow* axis — so the sweep found forty-four places where a hat's ordinary week hits a seam that no remaining sitting is currently scheduled to close, and six places where two hats want opposite things from the same ruling. The dominant pattern is **cross-sitting orphans**: the highest-severity findings (cross-venue exposure identity, kill-switch contract, restart recovery, correction-aware reads, same-tick priority) each need two sittings to agree, and the current sitting order (registry → data → indicators → venue → risk) processes them in the wrong sequence at least twice. Nothing here requires reopening an AD. Everything here requires a sitting to notice it before it writes its contracts.

**How to read this.** Findings are grouped by hat. Each is one paragraph carrying a severity (**must-cover** / **should-cover** / **note**), the AD or GAP it attaches to, and the sitting that owns it. Cross-hat conflicts are collected at the end with a proposed resolution shape, because a conflict resolved implicitly by whichever sitting runs first is a conflict resolved badly.

**Scope discipline.** I declined attacks that belong to the deferred backtesting sitting except where a hat's *V1* workflow depends on them (R-1, R-4, A-2). I did not re-derive the adversarial review's seam contradictions; where a hat's finding touches the same clause (R-7 and A-3 both land near AD-10's float carve-out), the finding is about the **downstream contract the sitting must write**, not the AD itself.

---

## Severity index

| Hat | must-cover | should-cover | note | total |
|---|---:|---:|---:|---:|
| Researcher | 5 | 4 | 1 | 10 |
| Developer | 4 | 3 | 1 | 8 |
| Analyst | 4 | 3 | 1 | 8 |
| Portfolio Manager | 4 | 3 | 1 | 8 |
| Trader | 6 | 3 | 1 | 10 |
| **Total** | **23** | **16** | **5** | **44** |

Sitting load: registry **11** · data **12** · indicators/structure **7** · venue **9** · risk **14** · cross-sitting/all **6** (findings counted once per primary owner; several name a second sitting).

---

## Hat 1 — Researcher

*Workflow walked: reads a paper or a chat transcript, forms a hypothesis, runs a genetic search over indicator/confluence parameter space in a disposable sandbox, discards 99.9% of the population, registers the survivors, checks them against a sealed holdout once, hands the survivor to the developer hat.*

### R-1 — The attempt counter has no defined unit for population search — must-cover — registry sitting (GAP-0017)

A genetic algorithm evaluates thousands of genomes per generation, and GAP-0017 asks what the attempt counter counts, at which scope, and how it constrains research budget. Both naive answers break: if every genome evaluation is an attempt, the counter saturates in the first hour and the budget concept becomes decorative; if only registrations count, the entire multiple-testing surface that the counter exists to price is invisible, and GAP-0049's future SR\* threshold has no denominator to deflate against. The registry sitting must define the counting unit as a **search campaign** — charter + dataset split + declared search space + generation/evaluation budget, minted before the search runs — with population size and realized evaluation count recorded as campaign facts. This also gives AD-12's computation-identity-vs-occurrence split a clean application: one campaign computation, many evaluation occurrences.

### R-2 — AD-13's load ladder is a trading-node ladder; the research path has no rung — should-cover — registry sitting + AD-13 ladder extension (AD-13, GAP-0014)

AD-13 expresses benchmarks in framework-native units per package with the ~40-bot node scenario as the motivating reference. That reference is a *live-path latency* scenario. The researcher's load is the opposite shape: 10⁴–10⁶ canonical serializations, fingerprints, and lineage-edge appends in a burst, in a sandbox with a cold cache. If the registry and core benchmark ladders are sized only against the node scenario, the factory will legitimately optimize `fp1` and the registry append path against the wrong curve, and the GA run will be the thing that discovers it. The registry sitting should add a research rung (fingerprints/s, registrations/s, edge-appends/s at burst) when it records its first baselines.

### R-3 — Negative results need a lifecycle state and a cheap evidence form — must-cover — registry sitting (GAP-0014, GAP-0015, GAP-0017)

The registry ADR and gaps are written around artifacts that survive: registration, lineage, promotion. Research is overwhelmingly failure, and the *rejected* population is the scientifically load-bearing part — it is the multiple-testing denominator and the honest record of what was tried. If only survivors get identities and edges, the operator can never compute a deflated performance statistic and can never answer "did we already try this?". The registry sitting must decide (a) whether a `rejected` / `abandoned` lifecycle state exists on registry kinds, (b) whether rejected candidates consume attempt budget, and (c) whether a bulk-summary evidence form exists so a million discarded genomes do not become a million full records.

### R-4 — The sealed holdout cannot be consumed from a sandbox that may not write — must-cover — data sitting, colliding with AD-12 (GAP-0024, L19, AD-12 namespace rule)

L19 and the ratified 12-month seal permit one logged final look per strategy. AD-12's namespace rule says a non-live world may never write into the live evidence namespace and factory sandboxes never produce timestamps entering an evidence store. Those two are jointly unsatisfiable for the seal: an agent in a sandbox can read the split manifest and evaluate against sealed data with **nothing durable recording that the look happened**, because its writes cannot reach the store that holds the budget. The data sitting must model a seal look as a **write-gated operation against the live registry** — the look is requested, granted, and recorded as a registered occurrence before the data is readable — or the seal is honor-system only and the agentic era will burn it silently.

### R-5 — Split manifests need purge and embargo widths, not just non-overlap — should-cover — data sitting (GAP-0024, GAP-0031, GAP-0034)

GAP-0024's recommendation is time-ordered non-overlapping split manifests. That is insufficient once the consuming artifacts have look-forward horizons: an indicator with a 200-bar warm-up and a structure family that is *confirmed* N bars after it is *observed* (exactly the observed-at/confirmed-at discipline GAP-0034 requires) both leak across a bare boundary — the last training labels depend on bars sitting inside the test window. The split contract needs a declared **purge width** (drop the boundary-adjacent region) and **embargo width** (delay the test window start), derived from the maximum horizon of the artifacts consuming the split, recorded in the manifest and participating in the split fingerprint so a split reused with a longer-horizon artifact refuses rather than leaks.

### R-6 — Warm-up must be a declared, fingerprinted property so the causality gate can test it — must-cover — indicator sitting + registry sitting (GAP-0031, GAP-0016)

AD-8 ratifies that causality is compared on instants only and refuses at equal instants; GAP-0016 asks what causality/look-ahead test an artifact must pass. An indicator with warm-up emits nothing valid for its first k bars, and GAP-0031 correctly asks for explicit warm-up and missing-output markers. The unclosed piece is the join: unless the *configured* indicator exposes its warm-up length as a declared property that enters its fingerprint, the registration gate cannot assert that the artifact's evidence window actually covers warm-up, and an artifact can pass causality while its first N decisions ran on under-warmed state. The indicator protocol must publish warm-up as contract surface, and the registry gate must consume it.

### R-7 — Two sandboxes producing one label with differing float bytes is the researcher's normal case, and AD-10 currently classes it as a collision — must-cover — registry sitting (AD-10, GAP-0014, GAP-0015)

AD-10 gives float-bearing artifacts label-derived identity, explicitly does not promise cross-OS bit-identity of float content, and separately rules that same-hash-differing-bytes is a **true collision, refused and alarmed**. The researcher runs the same GA on the Windows workstation and in a Linux sandbox (both tier-1 per AD-1) and gets one identity and two payloads — a refusal and an alarm for the ordinary case. This is not an AD defect; it is a registry-side rule the AD leaves for the registry sitting to write: label-identified float artifacts with differing content checksums are **lineage siblings under one label**, recorded with their (OS, library-version) provenance, and only *identity-content* hash divergence is a collision.

### R-8 — Seed and search-state provenance have no declared home in the result label — must-cover — registry sitting (AD-12, GAP-0012, GAP-0014)

AD-12's label is producer contract format version, input fingerprints, evidence time range, computation/occurrence identity, and world. A stochastic search result is not reproducible from those alone: it needs the RNG seed, the generator identity, and — for parallel evaluation — the reduction order. Because AD-12 is closed, the registry sitting must place them without reopening it: as identity-bearing inputs (two seeds are two computations, reproducible but never deduplicated) or as occurrence provenance (one computation, many occurrences, deduplicating but not reproducible). Choosing by default rather than by ruling loses one of the two properties silently.

### R-9 — Foreign research artifacts must be registerable or don't-box-in dies at the registry door — should-cover — registry sitting (GAP-0014, DEC-0011/L9)

The don't-box-in ruling guarantees ordinary Python and any external library stays usable in research lanes — sklearn, Optuna, statsmodels, torch, whatever the method of the month is. Those produce artifacts that are not QMF nouns and have no QMF contract. Unless the registry admits an **opaque foreign artifact kind** (content checksum + declared producer + environment provenance + typed "not a QMF contract" marker), research performed the ratified way becomes unregisterable and therefore unpromotable, and the freedom is nominal. Registration should accept it; promotion may still demand more (see conflict X-1).

### R-10 — Hypothesis provenance has no kind — note — registry sitting (GAP-0014)

The research lane starts at a paper, a video, or a chat, and the operator's per-currency knowledge libraries are explicitly meant to fuel hypothesis proposals rather than control limits. Whether a *hypothesis* or *trading thesis* is itself a registry kind — carrying a source citation and accumulating lineage edges to every artifact it spawned — is worth one sentence in the registry sitting. It costs almost nothing to mint and it is the only way the operator later answers "which reading actually produced edge."

---

## Hat 2 — Developer

*Workflow walked: opens an editor, imports two or three QMF packages plus pandas and one external library, writes a bot against the future QML surface, runs it against stored evidence, then against a demo account, reads tracebacks, ships.*

### D-1 — Default-deny inter-library edges makes the natural developer import illegal, and no sitting is scheduled to request its edges — must-cover — every remaining sitting (AD-2 dependency direction)

AD-2's default-deny rule is correct discipline and the spine is right to keep it. Its consequence is procedural and currently unowned: computing an indicator over stored evidence needs `qmf-indicators` and `qmf-data` in one expression, and today that edge does not exist and each new edge is a spine amendment. If no sitting produces an edge request, every composition lands in application code with hand-marshalled types, which is precisely the tax the one-repo decision was meant to avoid. **Every remaining sitting must close with an explicit edge request or an explicit "none required"**, so the amendment set is assembled deliberately rather than discovered by the first developer.

### D-2 — Returned refusals need one blessed ergonomic surface or plain-Python users route around them — should-cover — registry sitting (earliest public-API sitting) (AD-11, L9)

AD-11 ratifies returned result unions plus `try_create` factories, and reserves exceptions for programmer error. For a thirty-line scalping bot in plain Python this means an unwrap at every boundary and no way to write a straight line of code. Nothing in the spine offers a composition idiom (chaining, collecting, early-return) or a documented, deliberately-named unwrap-or-raise for scripts and notebooks. Without one, the don't-box-in ruling is honored on paper and violated in practice — developers will reach for the unchecked constructor AD-11 provides for "trusted internal use," which is the worst available outcome. The first sitting that defines public API shape should ratify the ergonomic surface alongside it.

### D-3 — Scaled-integer money has no bulk representation, and three packages will invent three — must-cover — data sitting + indicator sitting (AD-7, GAP-0021, GAP-0031)

AD-7's frozen-dataclass `Price(instrument, scale)` is exactly right for a single value and unusable for a million of them; the Stack simultaneously admits numpy/pandas/pyarrow in outer packages. The developer computing anything over a tick series therefore needs a **bulk form** — an int64 array plus its scale carried out-of-band, with Arrow field metadata the obvious carrier — and a named conversion boundary (AD-7 already requires named boundaries with stated rounding) between bulk and value. If the data and indicator sittings each answer this independently, the developer marshals between two or three representations at every package hop, and the money-path taint rule becomes impossible to audit across them. One representation, ruled once, in the data sitting, adopted by the indicator sitting.

### D-4 — No package states what is public — should-cover — every remaining sitting (AD-3, AD-5)

AD-3 fixes *how* public things look (frozen dataclasses, Protocols) and AD-5 promises a one-release deprecation window for "anything deprecated," but nothing anywhere says **what is public**: no `__all__` convention, no underscore rule, no re-export policy. Under PEP 420 with `src/` layout, a developer importing `qmf.data._store.thing` creates an obligation the deprecation window then has to honor, and the factory has no rule telling it which symbols it may freely refactor. Each sitting should state its package's public surface rule in one line; the registry sitting should state the workspace-wide convention.

### D-5 — The venue seam's concurrency colour is the single largest un-asked developer question — must-cover — venue sitting (GAP-0038, GAP-0036, AD-6)

AD-6 prohibits dependencies that impose their own event loop and the framework-vs-node split puts the loop in the node — but `qmf-venue` wraps the cTrader Open API, which is an inherently persistent, reactive, async connection. If the venue seam is synchronous, the node's loop is forced into thread-bridging for every order and every tick; if it is async, every consumer of the seam inherits asyncio, which is arguably the platform imposition AD-6 bans. The venue sitting must rule the colour explicitly, and rule whether qmf-core's Clock protocol needs an async twin. Deciding this late means rewriting the adapter and every consumer.

### D-6 — No stateful seam declares a concurrency contract, and 40 bots is the ratified load — must-cover — indicator sitting + data sitting + venue sitting (AD-13, GAP-0031, GAP-0021, GAP-0036)

The ~40-bot scenario means ~40 concurrent consumers of shared streaming indicator state, shared evidence readers, and one venue session. Frozen dataclasses settle the value types; they settle nothing about a stateful streaming indicator (GAP-0031), a store handle (GAP-0021), or a venue session (GAP-0036). Every stateful seam must declare whether it is safe to share across threads/tasks, must be cloned per consumer, or is guarded — because the developer will otherwise discover the answer at 40 bots on a live account, which is the most expensive possible place to discover it.

### D-7 — Only one extension shape exists, and extensibility is the paramount design driver — must-cover — indicator/structure sitting + venue sitting (AD-2 extensions, GAP-0031, GAP-0034, GAP-0038)

The operator's stated paramount driver is a small core with wide seams so every later idea lands as an extension rather than a rebuild. The spine defines exactly one extension shape: calendar extensions, own SemVer ladder, outside the roster, forcing their tzdata pin. A developer writing a custom indicator, a custom structure family, or a third venue adapter has no stated discovery, declaration, or versioning path — and the word "plugins" is banned, so the shape needs its own name. The indicator/structure and venue sittings must each define their extension seam concretely (how it is declared, how it is found, how it versions, how its identity enters fingerprints), or the wide seams exist only for calendars.

### D-8 — Reference usage for the venue module collides with the no-mock-data law — note — venue sitting (AD-3/L27, L6)

L27 and AD-3 make executable tests **and** reference usage a tier-1 artifact for every component. For `qmf-venue`, reference usage that demonstrates the public contract needs a broker session, and CI has none — while L6 forbids shipping mock market data as a product artifact. The venue sitting needs a story that satisfies both: a recorded-session fixture is a *controlled test fixture* (explicitly permitted) rather than shipped mock data, but the distinction must be stated in the sitting rather than left to a factory agent's judgment.

---

## Hat 3 — Analyst

*Workflow walked: pulls performance data across Books and accounts, compares live to paper, watches a strategy's edge fade, decides whether the fade is decay or noise, writes it up, feeds the answer back to the researcher and the PM.*

### A-1 — "Comparable" needs a definition beyond `world = live` — must-cover — risk sitting (AD-12, AD-9, GAP-0045)

AD-12 deliberately assigns paper and demo runs `world = live` so they stay comparable to live for alpha-decay sensing — the right call. Comparability, though, needs more than world equality: the paper account sits at a different venue or account with different spreads, different fill quality, possibly a different calendar binding and certainly a different execution population. The risk sitting must define the **comparison cohort rule** — what makes two result streams admissible into one decay judgment — or the analyst compares a live scalper against a demo feed and reports the execution difference as alpha decay. This is the finding that decides whether the ratified paper-mode design actually delivers the thing it was ratified for.

### A-2 — Nothing in the seven-package roster owns a performance result — must-cover — risk sitting (GAP-0045, GAP-0044, AD-12)

`qmf-risk` owns Book and BMS, `qmf-data` owns evidence, `qmf-registry` owns identity, backtesting is deferred. The analyst's central object — a fingerprinted performance result over a declared population and period, produced by a versioned formula, carrying units — has no owning contract anywhere. GAP-0045 rightly defers the *mathematics* until stop-out and the units are stable, but the risk sitting must still mint the **container**: a result kind with an AD-12 label, a declared population, a declared period, and units per GAP-0044. Without it every analysis is an unregisterable one-off script and none of it accumulates.

### A-3 — Two identically-labelled reports can legitimately hold different numbers — should-cover — risk sitting + data sitting (AD-10, AD-12, AD-5)

A Sharpe, a drawdown, a decay slope is a float; AD-10 gives float-bearing artifacts label-derived identity with an integrity checksum, and AD-12 says package SemVer never enters identity. Compose them and two runs of "the same metric" under different numpy or statsmodels versions produce one identity and two values, legitimately, with no signal to the analyst. The sitting that mints the performance-result kind must therefore bind the metric's **contract format version** to its arithmetic — an arithmetic change is a format-version mint, not a package release — so identity moves when meaning moves. (Same underlying seam as R-7, reached from the reporting side; the fix is different and both are needed.)

### A-4 — Corrections make every performance number a function of when it was run — must-cover — data sitting (GAP-0023, GAP-0020, AD-5)

Evidence is append-only and corrections are annotations; no read-resolution rule exists yet, and the spine explicitly forbids any package folding corrections inline until the store contracts land. The analyst computes month-to-date P&L on Monday; a corrected fill lands on Wednesday; Monday's number is now unreproducible and nothing says so. The data sitting must make **as-of reads** — queries bounded by knowledge time — a first-class store operation, and the performance-result label must record the knowledge-time bound it was computed under. AD-5's re-derivation rule (new artifact, lineage edge to the old) covers re-deriving under a new calendar; it does not cover re-deriving under corrected inputs, and that is the analyst's daily case.

### A-5 — Multi-currency aggregation is unruled and two hats need the same ruling — must-cover — risk sitting + data sitting (AD-7, GAP-0044, GAP-0030)

Six brokers means accounts plausibly denominated in different currencies. AD-7 nails `Money(currency, scale)` and bans implicit rescale, and it is exactly right to do so — but nothing states how a portfolio-level figure is produced across currencies: which FX rate, from which source, at which knowledge time, and whether the converted figure is evidence or a derived display value with lineage. AD-7 already supplies the mechanism (a named conversion boundary with a stated rounding mode); the sitting must supply the policy. This is the identical ruling the PM needs for allocation (P-2) — rule it once, in the risk sitting, with the rate source specified in the data sitting.

### A-6 — Journal volume is both the analyst's dataset and the retention decision, and must be measured inside the data sitting — should-cover — data sitting (GAP-0025, GAP-0026, AD-13)

Every decision, refusal, suppression, and risk transition is journaled; at 40 bots making ~1s decisions that is millions of rows a day. GAP-0026 correctly refuses to set compaction before measuring volume — which makes the measurement itself a prerequisite, not a follow-up. AD-13 already makes benchmark harnesses first-class and gates peak memory; the data sitting should extend the ladder to journal write rate and resident size and produce the number as a sitting deliverable, because the retention rule, the backup RPO (GAP-0027), and the analyst's query story all hang off it.

### A-7 — Suppressed actions are the highest-value analytic dataset in the system — must-cover — risk sitting + data sitting (GAP-0046, GAP-0025)

GAP-0046's recommendation says record every suppressed action, almost in passing. For the analyst it is the counterfactual that separates "the edge died" from "our own gates blocked the trades" — without it, every news window, SQS gate, and kill-switch fire looks like decay. The risk sitting should type suppression as a first-class journal event carrying the suppressing authority, the reason (news window / SQS / kill switch / Book force-flat / stop-out / hold limit), and the would-have-been action, and the data sitting should place it in the journal event catalog (GAP-0025) rather than leaving it as generic log text.

### A-8 — Exit ownership decides P&L attribution, and the ruling should say so — note — risk sitting (GAP-0040, DEC-0067, GAP-0045)

DEC-0067 is a live conflict whose recommended resolution puts exit policy in the Book with Bots emitting exit signals through the Book contract. Whichever way it lands, attribution follows: if the Bot chose entry and the Book chose exit, per-Bot P&L is a convention, not a fact. The risk sitting should state the attribution convention in the same breath as the exit ruling, or every performance report the analyst produces carries an undeclared one.

---

## Hat 4 — Portfolio Manager

*Workflow walked: looks across ~6 brokers and their accounts, decides how much risk each Book gets, watches concentration and correlation, plans a broker migration, and later runs prop-firm-constrained Books.*

### P-1 — Cross-venue exposure is uncomputable by construction, and the fix must not be symbol parsing — must-cover — registry sitting (AD-9, GAP-0014, GAP-0015)

AD-9 makes instrument identity `(venue, venue's own symbol)` with the symbol opaque and never parsed, and declares multi-broker operation normal rather than special. Both are correct. Together they mean the PM's first question — "what is my total EURUSD exposure right now?" — has no framework answer: six brokers yield six distinct Instrument identities for one economic risk, and nothing may infer their equivalence. The registry sitting must mint an **operator-declared equivalence record**: a dated registry kind asserting "these instruments are one exposure class," minted by a human, sitting beside identity rather than deriving from it, never rewriting history, and carrying its own fingerprint so exposure figures computed under it are reproducible. This is the highest-value PM finding and it is currently in nobody's scope.

### P-2 — The Book charter needs a declared numéraire — must-cover — risk sitting (AD-7, GAP-0044)

Allocating R across six accounts requires one number in one unit, and GAP-0044 already demands every variable carry units and the three capital concepts stay distinct. The missing piece is the currency in which the allocation math runs: the Book or portfolio charter must declare its **numéraire**, its rate source, and the knowledge time at which rates are read, with the converted figure treated as a derived value with lineage across AD-7's named conversion boundary. Left unruled, the risk module and the reporting path each pick one and the PM's allocation never reconciles with the analyst's report. (Same ruling as A-5.)

### P-3 — The correlation ledger falls in the crack between framework and node — must-cover — risk sitting (GAP-0039, CT-23)

The spec places a correlation ledger inside the Risk module, while the 2026-08-19 framework-vs-node ruling puts Book runtime behavior in the node and leaves QMF holding only contracts and seams. Correlation is exactly the hybrid case: it is *computed* from evidence (data plus indicators) and *enforced* at runtime (node). Without a deliberate ruling it lands in neither. The risk sitting must state where the correlation **contract** lives — most naturally as a declared input shape on the risk-evaluation contract (CT-23), computed outside, enforced node-side — so the PM's most-requested control has a seam even though its enforcement is not framework territory.

### P-4 — Book-to-account cardinality across venues is unruled and changes three other schemas — must-cover — risk sitting (GAP-0039, GAP-0041, AD-9)

AD-9 establishes that one venue holds many accounts, each with a role, and that Books bind to accounts. It does not say whether one Book may bind accounts at *several* venues — which is the natural PM move: split one strategy Book across three brokers to diversify execution and counterparty risk. The answer changes the Book charter schema, the paper-mode transition (GAP-0041: which account does a multi-venue Book fail over to?), stop-out arithmetic (GAP-0045: whose equity?), and same-tick priority (see T-4 and conflict X-5). The risk sitting must rule it explicitly and early in its own agenda, because three later rulings depend on it.

### P-5 — Broker migration is declared normal but has no continuity edge — should-cover — registry sitting + risk sitting (AD-9, GAP-0015, GAP-0039)

AD-9 states plainly that broker migration is normal, not a special case. Operationally a migration means: exposure closes at venue A and reopens at venue B, instrument identities change, the Book's account binding changes — and the performance history must stay continuous or the analyst's decay signal resets to zero on the day of the move. The registry sitting must supply the **continuity lineage edge** (a typed "continues-as" relation between account bindings or Book epochs) alongside the equivalence record of P-1, so a migrated Book's history is one history with a documented discontinuity rather than two unrelated ones.

### P-6 — Verify the day-boundary seam is wide enough for real prop-firm rules without modeling any firm — should-cover — risk sitting (AD-8 day-boundary calendar, GAP-0039)

AD-8 ships the account-scoped day-boundary calendar precisely as a socket and models no firm, which respects the deferral. The risk sitting should nonetheless *test the socket against the shape of real constraints*, because widening it later is a format-version mint: a daily-loss rule needs a day boundary **and** a named baseline (equity at day start versus intraday high-water), a trailing max-drawdown needs a high-water mark that survives process restarts and is evaluated while positions are open, and both need evaluation on unrealized P&L. Confirm the Book charter can express "a rule evaluated against a day-boundary calendar with a named baseline over a named quantity" generically. That is seam verification, not prop-firm modeling.

### P-7 — Exposure limits need a unit that survives the asset classes the nouns must not preclude — should-cover — risk sitting (GAP-0044, AD-7, DEC-0015)

No futures or options ever, but forex CFD today, crypto perp expected, equities explicitly re-affirmed as a later target. A concentration limit expressed in lots is meaningless across those three, and AD-7 deliberately makes `Quantity(unit, scale)` opaque so it can carry all of them. The risk sitting must therefore express Book-level limits in **R** and in a **notional-in-numéraire**, both defined with units per GAP-0044, so the same charter text still reads correctly the day an equities venue is added — rather than in an instrument-native quantity that silently changes meaning per asset class.

### P-8 — Venue capabilities must be storable evidence, not a live probe — note — venue sitting (GAP-0038, CT-18)

Allocation depends on what a venue can actually do: supported order types, hedging versus netting, minimum and maximum size, leverage, whether protective stops rest server-side. CT-18 exists for capability discovery; the venue sitting should ensure its output is a **registerable, fingerprinted evidence artifact** with a knowledge time, so allocation logic and the PM's planning read declared capabilities from the store rather than requiring a live session — and so a capability change at a broker is a dated, visible event rather than a behavior change nobody recorded.

---

## Hat 5 — Trader (the operator)

*Workflow walked: ~40 live bots on a VPS making ~1s scalping decisions across six brokers; watches health, honors news blackouts, hits the kill switch when something is wrong, restarts the node after a crash, and does the human promotion job daily.*

### T-1 — The kill switch is node territory, and its contract has no named seam anywhere — must-cover — risk sitting + venue sitting (framework-vs-node ruling, GAP-0046, GAP-0036)

The 2026-08-19 ruling puts the kill switch in the node and says QMF carries "only their contracts/seams." No AD and no CT names that seam, and the tracker itself records the kill switch as "nowhere designed" and "the one component with unbounded failure cost." The risk sitting must mint the **control-action contract**: a typed control command with its authority, its scope (pair / Book / account / venue / global — the operator's news ruling is already pair-scoped, so scope is a first-class dimension), its refusal semantics, and the evidence record it writes. The venue sitting must define the corresponding **flatten path** GAP-0036 calls "explicitly authorized." Framework-vs-node correctly withholds the *behavior*; it does not excuse the absence of the *contract*.

### T-2 — A kill switch that returns a refusal has not killed anything — must-cover — venue sitting (GAP-0036, AD-11, AD-14)

The tracker flags this exact case as undesigned: what the kill switch does when it fires while the broker connection is down. AD-11 supplies `transient venue failure` and AD-14 demands loud failure with context — but for this one command, a returned refusal is not an acceptable terminal state. The venue sitting must define what a control action means when it cannot be delivered: whether it becomes a **durable intent** that the reconciliation loop replays on reconnect, whether it escalates (the operator's fallback is the broker's own web platform, manually), how long the intent stays live, and what the trader is shown in the interim. This is the highest-consequence undefined behavior in the whole surface.

### T-3 — Measure-then-budget is right, but the latency path needs a named decomposition before the first measurement — should-cover — venue sitting + indicator sitting (AD-13, GAP-0031, GAP-0036)

AD-13's refusal to invent numbers is correct and should stand. Its side effect is that nobody will know whether the design meets a ~1s scalping cadence until it is built, and by then the stage count is fixed. The venue and indicator sittings should record the **latency budget decomposition as a structure** — tick received → evidence write → indicator update → decision → risk evaluation → order submitted, each a named, separately measurable stage with its own AD-13 rung — so the first real measurements attach to something, and so a design choice that inserts a stage (an extra serialization hop, a synchronous store write on the decision path) shows up as a visible design decision rather than a benchmark surprise six months later.

### T-4 — Same-tick priority cannot be written before the venue capability set is known — must-cover — risk sitting + venue sitting, sequencing hazard (GAP-0046, GAP-0038, CT-18)

GAP-0046 asks for a deterministic priority among protective stops, Book force-flat, kill-switch actions, fast invalidation, and discretionary exits. Several of those are **venue-resident** (a broker-side stop already resting at the venue, which fires without asking anyone) and several are **node-resident**. A deterministic ordering can only be written against the actual capability set — and the current sitting order runs venue (35-38) *before* risk (39-46), which is fortunate, but only if the risk sitting explicitly consumes the venue sitting's CT-18 output rather than assuming a capability profile. Flag the dependency in both agendas so the priority rule is written against reality.

### T-5 — The blackout must evaluate the news revision known at decision time, and handle late revisions — must-cover — data sitting + risk sitting (GAP-0042, GAP-0029, GAP-0023)

The ±15-minute pair-scoped window is ratified in shape and unratified in number pending evidence — fine. The unhandled risk is that the news feed is *revised*: times move, events are added late, and GAP-0029 rightly wants provider-native identity and revisions preserved. Two rulings are missing. The data sitting must state **which revision a decision evaluates against** — the one knowable at decision time, per the same causality discipline AD-8 enforces everywhere else — so blackout behavior is reproducible in replay. The risk sitting must state what happens when a revision arrives *during* an open window, or reveals that a window should have opened ten minutes ago: does the blackout extend, retro-open, or refuse.

### T-6 — Blackout behavior for already-open positions is named in the gap and unruled — must-cover — risk sitting (GAP-0042, GAP-0046)

GAP-0042 explicitly lists "open-position behavior" among its unknowns, and the operator's ruling so far covers only halting new entries while letting bots continue in paper mode so decay data keeps flowing. The risk sitting must rule the open-position case directly — hold, flatten, tighten stops, or freeze exits — and must state its interaction with T-4: a blackout that flattens is competing with protective stops and force-flat inside the same tick, so it needs a rank in the priority order rather than a separate code path.

### T-7 — Restart is the trader's most frequent incident and no contract covers the warm state — must-cover — venue sitting + data sitting + indicator sitting (AD-8 boot id, GAP-0036, GAP-0031, GAP-0022)

AD-8 mints a boot/epoch id so restarts are visible without changing writer identity — necessary, not sufficient. Nothing states what a component must **do** on restart with 40 bots and open positions: which positions and in-flight orders exist (venue reconciliation, GAP-0036), what the last written sequence per writer was (data), how much history each streaming indicator must replay to be warm again (indicators, and it is exactly R-6's declared warm-up length), and — critically — whether trading is **blocked until reconciliation completes**. The reconciliation loop has an owner; the warm-state rebuild and the trade-blocked-until-reconciled rule cross three sittings and currently have none.

### T-8 — `health()` answers the wrong question for a solo operator — must-cover — data/ops sitting (AD-14, DEC-0049, GAP-0025)

AD-14 gives every component a no-argument `health()` returning a typed health report, which is the right primitive. The trader's actual question is not "is this component healthy" but "**may I trade right now**" — a composed judgment over clock sync (the AD-8 devops obligations), venue session state, evidence freshness, calendar availability, and data-quality detectors. The data/ops sitting must define the aggregate readiness concept and, harder, must settle whether an unhealthy component **blocks trading automatically or only notifies** — which is precisely DEC-0049, still open, and which collides with the don't-box-in principle (see conflict X-3). A solo operator running 40 bots cannot compose this judgment by hand at 3am.

### T-9 — `stale evidence` is a ratified refusal category with no threshold owner — should-cover — data sitting (AD-11, GAP-0023, GAP-0043)

AD-11 ships `stale evidence` as one of six categories. Nothing anywhere says how old is too old — and at 1s scalping cadence that number is different for a tick, a spread sample, an SQS reading, a news calendar entry, and an account balance, and different again per instrument and per session. The data sitting should attach a **declared freshness horizon to the evidence contract itself** (each observation kind declares it, overridable per instrument), so the threshold is data rather than a constant each consumer invents. Otherwise the venue module, the risk module, and the node will each pick a different number and the refusal category means three things.

### T-10 — Promotion is a daily human job and must be one signature, not a scavenger hunt — should-cover — registry sitting (GAP-0019, L17)

L17 makes promotion human-only and GAP-0019 requires a fingerprinted artifact, lineage, declared charter, causality pass, untouched-test evidence, risk binding, reviewer identity, and a signed occurrence. All of that is right, and all of it is worthless if assembling it is manual: the operator has described promotion as his daily job, and a daily job that takes an hour becomes a rubber stamp, which defeats the gate more completely than having no gate. The registry sitting should size the promotion evidence as **a single fingerprinted promotion packet** — assembled by the registry, presented whole, signed once — with the human's decision recorded as an occurrence against that packet's fingerprint.

---

## Cross-hat conflicts

Six places where two hats want opposite things from the same ruling. Each is resolvable; none should be resolved implicitly by whichever sitting happens to run first.

### X-1 — Researcher's open toolbox versus Trader's live-money strictness, colliding at the registry door

R-9 needs foreign artifacts (sklearn, Optuna, torch) registerable or the don't-box-in ruling dies where research meets the registry; T-10 and GAP-0019 need promotion evidence strong enough to trust real money to. Both cannot be satisfied by one uniform bar. **Resolution shape:** make it an explicit asymmetry — registration is permissive, cheap, and accepts opaque foreign artifacts with provenance; promotion is strict, total, and may refuse anything it cannot fully verify. That is DEC-0011's "strictness only at the harness and the live-money gate" applied to registry kinds, but the registry sitting must state it deliberately, or it will harden registration to satisfy promotion and quietly close the research lane. *Sittings: registry.*

### X-2 — Analyst and PM need cross-venue aggregation; AD-9 forbids the only cheap way to get it

A-5 and P-1 both require treating six brokers' EURUSD as one thing; AD-9 makes symbols opaque and unparseable, permanently and correctly. **Resolution shape:** the equivalence must be a **declared, dated, operator-minted record** (P-1), never an inference — and the registry sitting must say so in a way that forecloses the tempting alternative, because the moment any package is allowed to normalize symbols to bridge the gap, AD-9's guarantee is gone and nobody notices until two brokers' records mix. *Sittings: registry (record), risk (consumption).*

### X-3 — Trader wants automatic protective halting; Developer and Researcher want nothing that boxes them in — and DEC-0049 is exactly this question, still open

T-8 wants a bad health verdict to stop trading; L9's don't-box-in principle and the framework-vs-node split both push halt authority out of the framework and into the node; DEC-0049 ("may automatic detectors mutate trading state, or only notify?") is recorded as open and unratified. **Resolution shape:** QMF *emits* a typed verdict — a refusal, an unhealthy report, a stale-evidence signal — and the node *decides* what to halt. That preserves both principles, but it must be stated explicitly in the data/ops sitting, because the trader will otherwise reasonably expect the framework to protect him and discover during an incident that it only ever spoke. *Sittings: data/ops (DEC-0049), risk (control-action contract).*

### X-4 — One AD-13 benchmark ladder cannot serve a GA fan-out and a 1-second scalping path

R-2 needs throughput at burst with cold caches (vectorized, amortized, batch); T-3 needs per-tick latency with bounded jitter (streaming, allocation-conscious). These are opposing designs for the same indicator code, and GAP-0031 already gestures at "batch-and-incremental" without ruling that both are first-class. **Resolution shape:** the indicator sitting should make the two modes explicit conformance targets of one protocol, with a stated equivalence obligation between them (the same inputs must yield the same outputs across modes — that equivalence is itself a contract test per AD-4), and AD-13 should carry two separate rungs so neither optimization silently regresses the other. *Sittings: indicators, with an AD-13 ladder extension.*

### X-5 — PM wants one Book spanning several venues; Trader wants deterministic same-tick priority — and a multi-venue Book makes "same tick" undefined

P-4 asks for a Book bound to accounts at three brokers; T-4 asks for a deterministic ordering of protective and emergency actions within one tick. Two venues have two independent tick streams, two latencies, and no shared clock — under AD-8, instants alone never totally order events, and the `(instant, writer, sequence)` tie-break is explicitly a replay-determinism device with no causal meaning, so it cannot arbitrate a genuine cross-venue race. **Resolution shape:** the risk sitting must rule Book-to-venue cardinality **before** it writes the priority rule; if multi-venue Books are permitted, priority must be defined per venue-scope with an explicitly non-deterministic cross-venue boundary rather than a false total order. *Sittings: risk (both rulings, in that order).*

### X-6 — Analyst wants paper comparable to live; Trader wants paper to keep running through blackouts

AD-12 makes paper `world = live` so decay sensing works (A-1); the operator's ruling keeps bots trading in paper mode while a pair is news-blocked so performance data keeps flowing (T-6). The consequence: paper evidence generated during a blackout comes from a population the live Book was forbidden to trade — same world, same label shape, non-comparable content. **Resolution shape:** the risk sitting should tag evidence produced under an active control (news window, SQS block, kill switch) with the suppressing condition — which is the same record A-7 asks for from the reporting side — so cohort selection can include or exclude it deliberately rather than averaging two regimes together and calling the result decay. *Sittings: risk, data (journal event catalog).*

---

## Sitting handoff — what each remaining sitting must add to its agenda

| Sitting | Findings it owns |
|---|---|
| **Registry (GAP-0014..0019)** | R-1, R-2, R-3, R-7, R-8, R-9, R-10, D-2, D-4, P-1, P-5, T-10 · conflicts X-1, X-2 |
| **Data (GAP-0020..0030)** | R-4, R-5, D-3, A-4, A-6, T-5, T-8, T-9 · conflict X-3 |
| **Indicators / structure (GAP-0031..0034)** | R-5, R-6, D-3, D-6, D-7, T-3 · conflict X-4 |
| **Venue (GAP-0035..0038)** | D-5, D-6, D-7, D-8, P-8, T-1, T-2, T-3, T-4, T-7 |
| **Risk (GAP-0039..0046)** | A-1, A-2, A-3, A-5, A-7, A-8, P-2, P-3, P-4, P-6, P-7, T-1, T-4, T-6 · conflicts X-5, X-6 |
| **Backtesting (GAP-0048/0049)** | R-1 (SR\* denominator), R-5 (purge/embargo reuse), A-2 (result container reuse) — inherited, not owned |
| **All sittings** | D-1 (edge request or explicit none), D-4 (public surface rule) |

Two sequencing hazards worth carrying forward: the risk sitting must rule **Book-to-venue cardinality before same-tick priority** (X-5), and must consume the venue sitting's **CT-18 capability output before writing the priority rule** (T-4).
