# Reviewer Gate — Operator-Voice Lens

Target: `_bmad-output/planning-artifacts/architecture/architecture-QMA-2026-08-28/ARCHITECTURE-SPINE.md`
Lens: operator-voice — does the spine still sound like Mubarak's rulings, or has inherited fashion crept back?
Read: spine (full), `.memlog.md` (every `direction` / `constraint` line), `inputs/transcript-decision-register.md` §1–§8 (§4 = his own words), `research/options-sheet.md` (D-row index, vocabulary, deferred/cut tables), parent spine `architecture-QMX-2026-08-19` (head + Conventions/Stack/Seed/Deferred), `docs/constitution.md` Laws.
Date: 2026-08-28.

---

## Verdict

**Pass with one blocking gap.** This is a disciplined spine and it holds the operator's voice better than the transcript it came from: Quant replaces Bot everywhere, no blanket `qmx.` prefix survives, hooks are the enforcement surface with "agents being too agentic" preserved as the stated harm, task-level ledgers are exactly what he ruled, Docker-per-worker is the default, the one Windows VPS is the only computer-use host, deploy-to-remote is first-class from v1, no external agent SDK is a dependency, no execution tool exists at any account role, and the Cut table kills eleven pieces of inherited fashion by name — including the ones he flagged himself. The refusal to let an LLM judge a completion is stated in three places.

The blocking gap is that his **single most-stated requirement — "the use case I wanted most is the one of them working without me" (L1896) — has no owning invariant.** Scheduling, routines and cron are referenced by five ADs and contracted by none, `block_stop` sits in a precedence table with no stated purpose, and the parent spine explicitly handed cron scheduling *down to this layer* ("News-calendar auto-sync, UI, cron scheduling — Node/app/agent territory, never framework"). Under this spine's own D21 law, anything on neither table and not in D1..D22 is out of scope for v1. So as written, v1 ships a system that cannot start work on its own.

Everything else is trim: one abstraction stack that grew a sixth layer the register already called overcooked, one confidence scalar with no named author, four tagging/vocabulary drifts, and three small placeholders.

---

## Critical

### C1 — Unattended operation has no owning AD. His #1 requirement is out of scope by the spine's own scope law.

**Where:** absent — should be a new AD-27 and a D23 row in the Capability → Architecture Map. Currently scattered across AD-5, AD-6, AD-7, AD-12, AD-20, AD-25 and the Structural Seed.

**What he said:**
- L1896: *"the use case I wanted most is the one of them working without me. Seriously that right there is something I need."*
- L1896: *"I want to be away for maybe the night and the agents continue working."*
- L4954: *"the ledger is something we can adopt with hooks, and it can be very good. Even task completed and all that, to-do lists, keeping agents working."* (register §3 item 13 — "never worked through". Still never worked through.)
- Register §5: the `/goal`-style keep-working command and the Ralph Wiggum loop are both listed as things to extract.
- Register §6: *"Example routine: 'every Sunday after market close'"* (L1819); Grok Bot's **routines** are on the extract list (register §5).

**What the spine does with it:**
- AD-7 gives every Quant a `routines` field. Nothing anywhere defines what a routine is, who fires it, or what it may do.
- AD-6's clock law says every wall-clock policy — *"quiet hours, routines and cron, rollups…"* — carries an IANA zone. It governs the timezone of a subsystem that does not exist in this spine.
- AD-5 says `correlation_id` is minted *"at the originating operator command or scheduled trigger"*. Scheduled triggers have no producer.
- AD-12 and AD-20 both delegate real authority to *"a deterministic scheduler"* / *"the deterministic scheduler"*. No AD defines it, no D-number owns it, and the Capability → Architecture Map has no row for it.
- The Structural Seed ships `scheduler/` and the container diagram lists Scheduler under CONTROL — code with no contract above it.
- AD-10's precedence order opens with `block_stop`, the strongest decision in the system, and the spine never says what it is for. It is the keep-working primitive and it reads like a typo.
- AD-25 defines overnight autonomy purely as a *hosting* question ("the workstation stays on or the mission is deployed"). That answers *where* the process lives, not *what starts it* or *what keeps it going*.
- Neither the Deferred nor the Cut table mentions scheduling, routines, cron or continuation. D21 therefore rules them out of v1 by silence.

The parent spine deferred cron scheduling **to this layer by name**, and constitution L8 pushes "scheduled lifecycles" out of QMF for the same reason. This spine is where that obligation lands, and it dropped it.

**Fix (concrete):** mint **AD-27 — Routines, scheduled triggers and continuation [ADOPTED 2026-08-28]**, add `D23 routines, scheduling, continuation | daemon scheduler | AD-27` to the Capability → Architecture Map, add `D23` to the frontmatter `binds:` list, and add `routine_fire` / `before_routine_fire` to AD-10's hook set (see H1). Rule text:

> **Binds:** D23; the scheduler, the Quant `routines` field, `agent_stop`, WakePolicy, JobHandle.
> **Prevents:** the operator's overnight requirement resting on a subsystem no invariant owns; a routine firing with no evidence; an agent stopping mid-mission because a model decided it was done.
> **Rule:** A **Routine** is a durable, Quant-owned scheduled trigger: id, owning `ActorId`, cron or interval expression with an explicit IANA zone (AD-6), the Mission Template or Graph Template it instantiates, enable flag, and a max-concurrent-runs cap. Routines are declarative daemon state, never agent-authored code, and are edited in the UI (AD-26). Firing is deterministic and never an LLM decision: the scheduler mints a fresh `correlation_id`, fires `routine_fire`, and instantiates work through the Mission Compiler exactly as an operator command would — a routine has no authority an operator command does not. Missed fires while the daemon was down are recorded and **not** replayed by default; catch-up is an explicit operator action. **Continuation:** a Task is not complete until AD-10's deterministic verifier passes, and `agent_stop` returning `block_stop` returns the Agent to the next ready Task in its Mission's Task Graph rather than ending the run — this is the mechanism behind "agents keep working while I am away", and the continuation policy (max consecutive continuations, budget ceiling, escalation target) is a per-Mission configurable variable under AD-26. An Agent that exhausts its continuation budget escalates to its Quant's mailbox and stops; it never invents more work.

Then delete `routines and cron` from AD-6's clock-law list only if it is *not* added here — it should stay, and now it will have a referent.

**Editor can apply without the operator:** yes. Every clause is assembled from rulings already in the register and the memlog, and it is tagged the same way the rest of the spine is. Flag the continuation-budget default as [ASSUMPTION] if a number is wanted at implementation.

---

## High

### H1 — "Everything gets hooks" is written as a law and then broken by its own v1 list.

**Where:** AD-10 (the event set), against AD-8 (Artifacts row), AD-9 (Experiment Ledger), AD-14 (Session), AD-21 (plugin activation), AD-24 ("hooks are the single enforcement point in the agent path").

**What he said (memlog, standing principle 2026-08-28):** *"everything created in this system gets hooks — every primitive … exposes hook events so deterministic guards can stop agents from being 'too agentic'. Hooks are the control surface, not an optional feature."*

**The drift:** AD-10 states the rule — *"Every daemon-owned primitive ships with its own before/after hook events; a primitive added without them is incomplete"* — then enumerates sixteen events that miss five daemon-owned primitives the spine itself defines:

| Primitive defined in | Write path | Hook |
| --- | --- | --- |
| AD-8 — Artifacts, "producing agent via the registry" | agent → daemon registry | **none** |
| AD-9 / AD-14 — Experiment, `EXPERIMENT_LEDGER` | agent registers an Experiment | **none** |
| AD-14 — Session (the run container, three axes) | daemon opens/closes | **none** |
| AD-21 — plugin activation and unload | operator command | **none** |
| AD-27 (proposed C1) — routine fire | scheduler | **none** |

The artifact one is the sharp end: AD-8 hands the producing agent a write path into durable daemon state, and AD-24 simultaneously claims hooks are *the single enforcement point in the agent path*. Both cannot be true. By AD-10's own sentence, the spine ships five incomplete primitives.

**Fix (concrete):** in AD-10, extend the v1 event set to read `… before_skill_write, before_artifact_register, after_artifact_register, before_experiment_register, session_start, session_end, plugin_activate, plugin_deactivate, routine_fire, mission_start, mission_complete.` Then append one sentence: *"An agent-reachable write into any daemon-owned store passes a `before_*` hook without exception; a primitive whose write path has no hook event is a defect in this registry, not an exemption."* No other AD changes.

**Editor can apply without the operator:** yes — this restores his stated rule rather than adding to it.

---

### H2 — The Mission ceremony grew a sixth layer. The register flagged five of them as overcooked and his filter is "we pick what we need, not everything."

**Where:** AD-12 (Mission, Mission Compiler, Mission Director, scheduler, dispatcher, **Mission Template**), AD-7 (lead Quant), AD-13 (Graph Template).

**What he said:**
- L3976: *"Once again, we are picking things we need, not everything."*
- L1896: *"for developer I think we overcooked … seriously like two total agents I think are enough."*
- Register §8 item 11, written before this spine existed: *"The 11-field Mission contract plus a Mission Compiler plus a Mission Director plus a Role Lead plus a Scheduler — five coordination layers above a workload that today is 'research a topic and run backtests'. Real for a 30-worker overnight run; heavy ceremony for the first version."*

**The drift:** the spine kept all five and added **Mission Template** as a sixth, tagged `[ADOPTED 2026-08-28]` on the authority of packet marker P-5. A Mission Template is a stateless, versioned, plugin-contributed skeleton that the Mission Compiler instantiates. A Graph Template (AD-13) is a stateless, versioned, plugin-contributed topology that instantiates into Tasks. They are the same shape with different nouns, and the spine's own Cut table kills "The 20-service injectable context fabric" for exactly this reason — *"architecture by enumeration; most entries have no described consumer."* Nothing in the register, the memlog or the transcript asks for a Mission Template; no desk plugin in the Structural Seed is said to contribute one.

This is the one place where the spine's discipline slipped in the direction the register warned about.

**Fix (concrete):** in AD-12, delete the sentence beginning *"A **Mission Template** is the plugin-contributed, versioned, reusable Mission skeleton (P-5)…"* and replace with: *"A Mission Compiler turns a Goal into a Mission, optionally seeded from a Graph Template (AD-13) a plugin contributed; there is no separate Mission Template registry in v1."* Delete the `Mission Template` row from the Vocabulary table. Add to the Deferred table: `| A separate Mission Template registry beside Graph Templates | after the first three authored graph packs exist and a desk demonstrably needs a mission skeleton a Graph Template cannot carry |`.

If the editor judges P-5 to be load-bearing packet law, the minimum acceptable alternative is to retag the sentence `[ASSUMPTION]` — it is not operator-settled and does not belong under `[ADOPTED 2026-08-28]`.

**Editor can apply without the operator:** yes for the retag; the deletion is also within the meta-ruling ("decide, tag, present the finished spine"), but call it out in the hand-back so he can veto it in one line.

---

### H3 — `promotion_confidence` has no author. The default reading is an LLM scoring its own memory.

**Where:** AD-18 (`MemoryCandidate … promotion_confidence` (a QMA-owned scalar)), against AD-22 (*"deterministic verification … never an LLM judging itself"*) and AD-10 (*"a deterministic verifier script rather than an LLM judging itself"*).

**What he said:** L3963: *"I think it's better we have agents write deterministic scripts most likely that we can pass through instead of having agents iterate their own work or review their own work to produce a mess."* L3968: *"I would prefer this being more deterministic than anything, the entire thing. Because I know how messy agents can go."*

**The drift:** AD-18 says the candidate "carries" `promotion_confidence` and that the scalar is "QMA-owned". "QMA-owned" answers *which system owns the field name*, not *which component computes the number*. The candidate is proposed by an agent (`proposer` is a field on it), so the plain reading of "carries" is that the proposing agent supplies its own confidence — and then the AD-22 gate promotes on a number the proposer minted about its own output. That is the exact failure the operator named, hiding inside a field definition. AD-19's careful name-split law protects `evidence_confidence` from being scalarized and then leaves the scalar it split away from unowned.

**Fix (concrete):** in AD-18, replace *"`promotion_confidence` (a QMA-owned scalar)"* with:

> *"`promotion_confidence` — a scalar the **daemon's promotion gate** computes deterministically from the candidate's provenance, supporting artifacts, corroboration count and validation history. A proposing agent may never set, suggest or influence it; a `propose` call carrying the field is refused. It is a gate output, never agent input."*

**Editor can apply without the operator:** yes.

---

## Medium

### M1 — AD-7's desk-lead flag is tagged `[ADOPTED]` when the memlog records it as an open operator question.

**Where:** AD-7, sentence *"Exactly one Quant per Desk carries the lead flag, and its mailbox is the address for desk-scoped inbound…"*, under the AD's blanket `[ADOPTED 2026-08-28]` tag.

**The drift:** the memlog carries `(question) Do desk-level lead quants exist as persistent actors (transcript's Role Lead / Mission Lead)? Operator unsure ('do we have agents at a profile level?'). To confirm with the ontology batch.` — and no later line confirms it. The follow-up line only says *"desk-level quant ledgers OK"*, which is about ledgers, not about a lead actor. Register §1 item 18 tags Role Lead `[PROPOSED]`, not `[OPERATOR]`. The spine's own tag legend says `[ADOPTED]` means *settled by the operator or by the transcript he ratified*. This one is neither, and AD-7 even lists *"an undefined 'Role Lead'"* as the harm it prevents — it prevents the ambiguity by picking an answer he did not give.

The lead flag is load-bearing: AD-9 hangs the Quant Ledger on it, AD-20 hangs dead-letter addressing on it, and the ERD encodes `lead only`. If he rules the other way, three ADs move.

**Fix (concrete):** append to that sentence in AD-7: *"**[ASSUMPTION]** the operator was unsure whether desk-level lead quants exist as persistent actors (memlog, 2026-08-28) and never ruled; the lead flag is decided here under the meta-ruling. AD-9's Quant Ledger and AD-20's dead-letter address both depend on it."* Add a matching Deferred row: `| Whether desk-level lead Quants exist as persistent actors | he was unsure and never ruled; AD-7's lead flag is an assumption AD-9 and AD-20 depend on |`.

**Editor can apply without the operator:** yes — it is a truthful tag, not a design change.

---

### M2 — "QMA" quietly re-broadened from the SDK to the whole system. That is the exact correction he made.

**Where:** frontmatter `name: 'QMX Agentic System (QMA)'`; title line; Vocabulary row *"QMA (QuantMind Agents) | the SDK; Python namespace `qma.*`. **The whole system is 'the QMX agentic system (QMA)'**"*.

**The drift:** memlog, his own direction: *"QMA (Quantum Mind Agents) is now the name of the SDK **only, not a framework**. The system under design = the QMX agentic system: daemon + QMA SDK + daemon-to-UI wire contract."* Corrected the same day to QuantMind. The spine states the narrow rule and the broad usage in the same table cell, and the broad usage wins in the title, the frontmatter, the filename, and the parenthetical abbreviation used throughout. He has now had to correct QMA's scope twice; the third correction should not be necessary.

The package names (`qma-core`, `qma-daemon`, `qma-wire`) are fine — the namespace was ratified. It is the *abbreviation for the system* that drifts.

**Fix (concrete):** change the Vocabulary row to: *"QMA (QuantMind Agents) | **the SDK only, not a framework and not the system** (operator, 2026-08-28); Python namespace `qma.*`, which the daemon and wire packages share. The system under design is **the QMX agentic system** = daemon + QMA SDK + wire contract."* Change frontmatter to `name: 'QMX Agentic System (QMA SDK, daemon, wire)'` and the H1 to `# Architecture Spine — The QMX Agentic System (QMA SDK + daemon + wire contract)`. Leave the directory name alone.

**Editor can apply without the operator:** yes.

---

### M3 — Two different things are both called `L<number>`, in adjacent clauses, in a document a non-technical operator has to ratify.

**Where:** AD-14 (*"(L17, L33)"* constitution laws and *"(operator, L4954)"* a transcript line, in the same rule), AD-17 (*"(L3011, L3871)"* transcript vs *"L35"* law), the Deferred UI row (*"L5071, L5082-5084"*), AD-16 (*"L36"*), AD-15 (*"L34"*).

**The drift:** the constitution numbers its laws L1..L39+. The transcript's citations are line numbers L7..L5083. The spine uses the bare `L` prefix for both. Inside AD-14, `L17` is a constitutional law about human promotion and `L4954` is a timestamped thing he said about Jupyter — and the reader is given no way to tell. This is a legibility failure against L5 (*"code and documentation legible to human developers and coding agents"*), which the spine itself inherits in row 13 of Inherited Invariants, and it is worst for the one reader who has to sign it off.

**Fix (concrete):** rewrite every transcript citation as `T-<line>` and add a line under the tag legend in Invariants & Rules: *"`L<n>` is a constitution law (`docs/constitution.md`). `T-<n>` is a line in the source transcript (`inputs/Design-Extensible-Agents.transcript.md`)."* Six edits: AD-14 (`T-4954`), AD-17 (`T-3011`, `T-3871`), the Deferred UI row (`T-5071`, `T-5082-5084`), and the two `L4954`-class references in the Cut table if present.

**Editor can apply without the operator:** yes.

---

### M4 — His own strategy-component-mutation idea is on neither table, so D21 cuts it by silence.

**Where:** absent from the spine, the Deferred table and the Cut table.

**What he said:** register §6, attributed to him at L1896 and worked out at L2832–2879 — normalize extracted mechanisms as typed objects (`EntryMechanism`, `ExitMechanism`, `Filter`, `SessionRule`, `PositionRule`, `InvalidationRule`) and recombine them (A+B+C, A+D+C, …) with provenance traceable to *"Paper A, section 3"* / *"Paper B, equation 7"*. This is the concrete quant workflow that motivates the Researcher → Analyst pipeline, the 800-variant RLM load in AD-14, and the whole knowledge corpus.

**The drift:** the spine's D21 law reads *"anything on neither this table nor the Deferred table, and not in D1..D22, is out of scope for v1."* His idea is on neither table. Everything else that got cut was cut *with a stated reason*; this one leaves without one. The likely correct answer is that typed strategy mechanisms are QML-owned domain modeling and AD-14 already says *"Strategy and Bot semantics are QML- and `qmf-registry`-owned; QMA holds references and candidates only"* — but the spine never connects the two, so a reader who remembers the idea cannot tell whether it was placed or lost.

**Fix (concrete):** add a Deferred row: `| Typed strategy-mechanism decomposition and recombination (EntryMechanism, ExitMechanism, Filter, SessionRule, PositionRule, InvalidationRule with paper-level provenance — operator, T-1896/T-2832) | QML and qmf-registry own strategy semantics (AD-14); QMA carries the candidates and the lineage edges. Revisit at the QML sitting — QMA's `StrategyHandle` and `ExperimentSpec` are already shaped to carry the result |`.

**Editor can apply without the operator:** yes.

---

## Low

### L1 — The browser deferral drops the one name he gave it.

**Where:** Deferred row `| Browser stack choice | a browser-heavy mission actually blocks; no study exists yet |`.

He said at L3976 that he wants to **reverse-engineer Egolite** for his use case, and separately mentioned a non-Chrome-devtools CLI approach (L1896). "No study exists yet" is true; starting the later session from a blank vendor shortlist would repeat the mistake ChatGPT conceded to at L4627 and would ignore his reference method (*"we are not going to clone blindly. No, we are going to extract."*).

**Fix:** amend the row to `| Browser stack choice | a browser-heavy mission actually blocks; no study exists yet. Starting point is the operator's own: reverse-engineer **Egolite** for this use case (T-3976), not a vendor shortlist — Cloudflare Browser Run, Modal, Daytona and E2B were rejected on cost and fit (T-3976) |`. **Autofixable:** yes.

### L2 — `ContextCompiler` is a plugin-replaceable port with no named implementer other than QMA.

**Where:** AD-1's port list and cardinality table.

Six of the seven ports have obvious outside implementers (memory backends, model deployments, environments, corpora, tool adapters, compute vendors). `ContextCompiler` does not: AD-18 says *"`reflect` is optional and off, **because cognition is QMA's**"*, and context compilation is the same claim. A singleton-per-scope port whose only implementer is the daemon is the Hermes `context-engine-plugin` shape inherited without its consumer — the pattern the Cut table kills as *"architecture by enumeration."*

**Fix:** either name who may replace it (*"a desk plugin may bind one ContextCompiler per scope; the daemon ships the only v1 implementation"*) or demote it out of the port list into a daemon-internal contract and drop its cardinality row. **Autofixable:** yes, but the editor should pick one and say which.

### L3 — Two placeholders the spine presents as settled values.

**Where:** the Structural Seed's five desk plugins (`research-corpus/`, `analysis-backtest/`, `dev-factory/`, `trading-readonly/`, `pm-coordination/`) while the Deferred table still carries *"Desk consolidation (five desks vs three vs two)"*; and AD-5's *"deprecations live **N** minors then drop"*, an unminted number in a spine whose AD-26 says every number it mints is registered.

**Fix:** annotate the seed line `plugins/` with `# one per desk; the desk count itself is deferred — five shown illustratively`, and change AD-5 to `deprecations live a configured number of minors then drop (AD-26 variable \`wire.deprecation_minors\`, default 2)`. **Autofixable:** yes.

---

## What the lens checked and found clean

Recorded so the next pass does not re-litigate it.

- **Quant, not Bot** — held everywhere, including the ERD, the Vocabulary table, and AD-7's explicit *"Bot, Seat, Book, BMS and kill switch are platform terms (L36) and never name an agentic actor or artifact."*
- **No blanket `qmx.` prefix** — AD-1 and the Conventions row both state it; every ledger and plugin is desk-scoped, which is literally what he asked for at L3968.
- **No external agent SDK** — Pi, Cordis, Prime, Hermes, bb, LangGraph appear nowhere in the spine; OpenCodex, Hindsight and MCP all sit behind QMA-owned ports, and the Cut table kills the foreign-runtime protocol outright.
- **Hooks as the control surface, not a feature** — AD-10, AD-11, AD-24, and "agents being too agentic" preserved verbatim as the harm.
- **No LLM judging itself** — stated in AD-10 and AD-22; the only LLM authorities left (Mission Director deciding *what* work, cross-model reviewer) are both his own rulings.
- **Task-level ledgers** — AD-9 matches his ruling clause for clause, including "never shared between agents" and the gate on completion.
- **Docker per worker, one Windows VPS, no agent workload on the trading node** — AD-17 and AD-25, with "no shared dirty filesystem" carrying his "40 research workers on one computer is nonsense."
- **Deploy from the UI** — AD-17 and AD-25 both make remote deployment first-class from v1 with the vendor deferred, which is exactly the order he demanded (contract before vendor).
- **Jupyter/Colab in-house, not outsourced** — AD-14.
- **MCP is part of the tool system, not the tool system** — AD-16.
- **The router only balances load** — AD-15, with the no-substitution refusal.
- **"We pick what we need, not everything"** — the Cut table names thirteen things and gives each one reason; it kills his own flagged overcooking (permanent specialist rosters) and the salvage he forbade. H2 is the single place this filter failed.
- **Not for the general public** — no trust tiers, no store, no cloud tiers, no mobile clients, no multi-tenancy, no ACLs.
- **UI deferred but the wire contract fixed now** — matches his memlog constraint exactly, and the deferred row carries his terminal-not-dashboard direction forward for that session.
