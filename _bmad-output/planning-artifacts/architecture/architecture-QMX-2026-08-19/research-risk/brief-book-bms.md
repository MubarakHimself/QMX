---
brief: book-bms
cluster: 'GAP-0039 (Book/BMS schemas, cardinalities, lifecycle, version compatibility, ownership) + DEC-0095 (Book↔BMS multiplicity) + five-hats P-4 / X-5 first half (multi-venue Book binding) + Book/BMS validation mechanism + "the Book sets the bar" container'
sitting: QMX risk sitting 2026-08-20
status: decision-brief — recommendations, not rulings
precedence_applied: 'current ratified corpus (docs/, tracker/, ARCHITECTURE-SPINE 2026-08-20) > old wiki (Documents/QMX/wiki) > GitBook capture 2026-07-18 > QMX-discussion legacy vault'
---

# Decision brief — Book and BMS

## Verdict in one paragraph

The current corpus holds **nothing** on Book or BMS: `CT-22` is `type: null, fields: null, enums: null, units: null, nullability: null` with every slot gapped to GAP-0039 (`docs/contracts/ct-22-book-charter.yaml:39-50`), `CT-24` is the same shape under GAP-0041 (`ct-24-book-mode.yaml:145-156`), and no `CT-BMS-*` contract exists anywhere (`docs/glossary.md:48-50`). Everything substantive lives in three older layers that agree with each other far more than the gap markers suggest. The honest reading is that **the legacy corpus answered a different question than the one now in front of us**: it described a monolithic node-side service (a Book that evaluates seven doors, a BMS with four desks that keeps ledgers and writes journals), and the 2026-08-19 framework-vs-node ruling has already redistributed most of that. Records is now `qmf-data` (AD-19/AD-21). Registration and lineage are now `qmf-registry` (AD-16). Sessions and commands are now `qmf-venue` (AD-27/AD-28). What is genuinely left for QMF is small, sharp, and currently unwritten: **three record kinds** (a Book definition, a rulebook it binds, and a dated binding to a venue-account) plus the evidence shapes that ride them. Everything that *runs* — doors, counters, ledgers, transitions — is node. This brief proposes those three kinds, resolves DEC-0095 and the multi-venue question that X-5 says must be ruled before same-tick priority, and designs the validation and "sets-the-bar" containers without inventing a single number.

**One finding is load-bearing enough to state up front:** the legacy rule that a Book's authoritative numbers live *outside* the Book definition, behind `registry://book-instance/{book_id}/…` pointers (`standards/ct-book-03-book-type-schema.json:196-217`, via the old-node-docs dossier), **cannot survive contact with AD-10 and AD-16**. AD-16 makes a record's stable id its `fp1` fingerprint; AD-10 makes every contract field identity by default. If the numbers sit outside the fingerprinted content, two Books with different money rules share one identity. That single correction cascades: it makes Book identity content-derived, which makes "changing a number mints a new Book" automatic, which delivers the never-found "scalping-book-v2 does not inherit v1's ledger" rule for free.

---

## How to read this

Eight items. Each carries: **(1) evidence with precedence applied**, **(2) bucketing** (stays QMF as a named seam vs re-buckets to the node, naming what QMF still carries), **(3) recommended ruling with the alternatives weighed**, **(4) what would change it**. Operator questions are collected at the end, recommendation first, plain words.

Two vocabulary notes used throughout:

- **Book definition** — the immutable, fingerprinted content that *is* a Book: its charter, its money-rule grammar and numbers, its admission bar, its leash grammar, its capacity rules. A noun, not a process.
- **Book binding** — a dated record joining one Book definition to one (Venue, Account, role, world). Money state, mode, counters and protective scope all hang off the *binding*, never off the definition.

---

## Item 1 — What a "Book" is in QMF: one immutable fingerprinted definition record

### 1.1 Evidence, precedence applied

**Current corpus (highest):** silent by construction. `CT-22`'s invariants say only *"Bot cardinality, Book binding, BMS multiplicity, exit ownership, fields, mutability, inheritance, and signatures remain unresolved"* (`docs/contracts/ct-22-book-charter.yaml:38`). What the current corpus *does* supply is the machinery a Book record must obey: AD-16 — *"per-kind record schemas (each its own versioned contract) share a tiny common header… A record's **stable id is derived from its `fp1` fingerprint** (never minted)… Kinds are addable, never redefined; **Bot and Book kinds are reserved names whose contents come from their own sittings**"* (`ARCHITECTURE-SPINE.md:161`). That last clause is an explicit invitation: this sitting fills the reserved Book kind.

**Old wiki (2026-07, next):** the six-section grammar, stated identically in four places. `components/book-template.md:18-26` — *"0. charter; 1. footprint; 2. money rules; 3. entrance exam; 4. leash chain; 5. capacity and sweep mechanics"*, with *"Section 6 workspace framing is not part of the ratified template"* (`:27`). Book type is *"a versioned JSON Schema contract using the ratified book-template Sections 0-5"* (`contracts/ct-book-03-book-type-schema.md:18`). Charter's own four slots: *"game played, money shape, customer plus headline metric, and death condition"* (via the local-current dossier, `primer:374`; corroborated `GITBOOK-BASE:88`).

**GitBook capture (2026-07-18):** same six sections; adds the runtime seven doors as a *separate* list — *"footprint, viability veto, R_max, daily budget, breaker, exposure ledger, and kill switch"* (`components/book-template.md:28,43`, DEC-0035). CT-BOOK-01 (the trade-intent envelope) is fully quoted: `book_id, bot_id, pair, side, requested_r, footprint_version, snapshot_version, timestamp_utc` (`contracts/ct-book-01-trade-intent-envelope.md:22-32`).

**Old node build (L-STD, ratified-by-story-5.1):** `standards/ct-book-03-book-type-schema.json` pins `template_sections minItems 6 maxItems 6`, `book_type_id ^book-type:[a-z0-9][a-z0-9-]*$`, `book_type_version ^[0-9]+[.][0-9]+[.][0-9]+$`, storage `typed_core_columns_plus_sparse_ratified_keys_json_bag`, `eav: false`, and — the clause that must die — `inline_authoritative_values_allowed: false` with numerics at `registry://book-instance/{book_id}/…/{slot_id}`, `owner_scope: "book_instance"` (`:40-118, 196-217`).

**Two corrections precedence forces on the legacy grammar:**

1. **`entrance_exam` cannot survive as a section name.** The current spine's Consistency Conventions ban the word outright: *"banned vocabulary honored (no 'kernel', 'plugins', 'engine' for backtesting, **'exam'**)"* (`ARCHITECTURE-SPINE.md:332`). The section must be renamed. `admission_bar` is the natural replacement and it is the same object the operator calls "the Book sets the bar" (Item 7).
2. **`inline_authoritative_values_allowed: false` inverts under AD-10/AD-16.** AD-10: *"every contract field is identity by default; display-only exclusion requires an explicit, versioned declaration"*, and *"all identity numerics are integers… floats are refused in identity content"* (`:118-119`). AD-16: id derived from `fp1`. Numbers behind a mutable pointer are not in the fingerprint; a Book's meaning would sit outside its identity. The legacy rule was a SQLite-storage discipline for a node with per-book registry slot tables (`standards/book-definition-minimal-existence.json:54-63`), not a framework rule. It must invert.

### 1.2 Bucketing

**Stays QMF.** The Book *definition* is a registry record kind — exactly the reserved kind AD-16 names. **Seam shape:** `CT-22` re-purposed from "Book and BMS charter placeholder" to **the Book-definition record contract**, an AD-16 per-kind schema with its own contract format version, whose content is entirely declarative.

**Re-buckets to the node:** everything the definition *describes* being executed — the seven doors evaluated against an intent, budget draining intraday, breaker counters, leash escalation, sizing arithmetic run per trade. QMF still carries: the **declaration vocabulary** those rules are written in, the **fingerprint** that makes a Book reproducible, and the **refusal categories** (AD-11) a node returns when a declared rule cannot be evaluated.

### 1.3 Recommended ruling

**A Book is one immutable, fingerprinted definition record. Its identity is its content. Its numbers are inside it, exact, and identity-bearing.**

Shape (contract format version 1):

| Slot | Ordinal | Carries |
|---|---|---|
| `charter` | 0 | game played, money shape, customer + headline metric, death condition (verbatim legacy four slots) |
| `footprint_requirements` | 1 | what behaviour envelope a bound Bot must stay inside; references measure identities, never bot self-description |
| `money_rules` | 2 | the declared money-rule set: named rules, exact-rational parameters, declared units on every term |
| `admission_bar` | 3 | the qualification requirement set — Item 7 (renamed from legacy `entrance_exam`, banned word) |
| `leash_grammar` | 4 | the declared escalation rungs this Book uses and their scope; ordering ruled by the same-tick cluster |
| `capacity_and_sweep` | 5 | roster/concurrency declarations, cycle and sweep grammar |

Plus the AD-16 common header (kind, contract format version, at-birth parent refs, writer, sequence) and four declaration blocks that make a Book *bindable*:

- `accounting_currency` — one declared currency for all of this Book's money math (Item 3.3, P-2).
- `required_venue_capabilities` — the CT-18 fields this Book's rules assume: position model (`netting | hedging`), the protection primitives it needs (`suspend-new | drain | close_all`), the command scopes it needs (`account | account-binding | instrument-within-binding`). Binding to a venue whose CT-18 declaration or venue-observation profile does not satisfy these is an `unsupported capability` refusal **at bind time, not at trade time** (AD-28, `:286`).
- `required_producer_contracts` — the contract format versions of every measure/indicator/structure producer the Book's rules reference, so a Book refuses rather than silently reading a different arithmetic (AD-5, AD-23).
- `worked_example` — Item 6.

Discipline, all inherited not invented: numbers are scaled integers or exact rationals (AD-7 `:86`); no binary float anywhere in the definition (AD-10 `:118`); every parameter carries its unit (GAP-0044's standing demand); every enumerable slot is addable-never-redefined (AD-5/AD-16); adding a seventh section is a **contract format version mint**, not a forbidden act — the legacy "Section 6 is structurally refused" rule was an anti-invention guard for a corpus with no versioning ladder, and AD-5 now supplies the ladder.

**Alternatives weighed.** (a) *Keep the legacy registry-pointer numerics.* Rejected: breaks AD-10/AD-16 identity as shown; also breaks reproducibility, since a stored result citing a Book fingerprint would not pin the numbers that produced it. (b) *Keep `entrance_exam`.* Rejected: banned vocabulary, and the rename is free. (c) *Seal the section set at six forever.* Rejected: contradicts AD-5's whole premise; sealing is what forced the legacy corpus to invent a "Section 6 is forbidden" refusal code instead of a version bump. (d) *Split Book "type" and Book "instance" into two artifacts as ADR-0002 legacy did.* Rejected as unnecessary: in QMF the contract format version **is** the type, and the record **is** the instance. Two artifacts would need a compatibility rule between them; one artifact plus a format version needs none.

### 1.4 What would change it

Evidence that the operator wants Books authored and edited through a live console with values mutating in place (the legacy console model, `references/ui-exploration/`). That workflow wants mutable slots and would force a different design — but it also forfeits reproducibility, so the right response would be a console that mints new versions on save, not mutable records.

---

## Item 2 — What a "BMS" is, and DEC-0095 (may one Book own several?)

### 2.1 Evidence, precedence applied

**Current corpus (highest):** the question is open and the *framing* is already suspicious. `qmf-risk.md` FM-8: *"One Book is assigned several BMS **policies** without a ratified multiplicity rule. The component must not select or merge them. `GAP(GAP-0039): Resolve DEC-0095.`"* (`docs/components/qmf-risk.md:112`). Note "policies", not "services". The glossary is blunter: *"BMS: Versioned risk and money-management machinery owned within the Book domain. **The documentation does not expand the initials because the authoritative sources do not fix an expansion.** Schema, ownership, and multiplicity remain `GAP(GAP-0039)`"* (`docs/glossary.md:48-50`). An acronym with no fixed expansion sitting in a contract is itself a defect.

**Old wiki:** BMS is unambiguously a single system *above* Books — *"BMS accounts for and constrains books. Its desks are Treasury, Exposure, Records, and Reporting. BMS owns the surrounding controls and records but never trades, sizes, mutates bot logic, or reaches inside a book"* (`components/book-management-system.md:15`), described as *"an accounting-and-constraint layer above books"* (`:17`). The wiki dossier's own reading: *"May one Book own several BMS? **NOT SUPPORTED** — BMS is the layer over all books, not owned by a book."*

**GitBook:** identical direction — one COMP-BMS, four desks, mode registry keyed `book_id → mode`, cross-book cap authority explicitly gapped (`components/book-management-system.md:7,43`; `contracts/ct-bms-02-mode-registry-read.md:16`).

**Old node build:** BMS state is *per `book_id`* across three tables — mode registry, treasury ledger, reconciliation (`standards/mode-registry-authoritative-book-mode-map.json:21-32`; `treasury-virtual-ledger-and-birth-mechanics.json:20-31`). The node dossier's reading: *"effectively BMS 1 : many Books… the direction is inverted."*

**All four layers agree the answer to DEC-0095 as literally asked is "no".** But they agree for a reason that no longer holds: they were describing a *running service*. Under the framework-vs-node ruling, three of the four legacy BMS desks have already been re-homed by the ratified spine:

| Legacy BMS desk | Where it lives now |
|---|---|
| Records (sole journal writer, five streams) | `qmf-data` — AD-21's N-stream journal under AD-8 `WriterId`s, seven event types (`ARCHITECTURE-SPINE.md:191`) |
| Treasury (virtual ledger, cycles, sweep) | **Node runtime.** QMF carries the boundary-event *shape* only |
| Exposure (measurement, news compilation, cross-book cap) | **Node runtime.** QMF carries the exposure-input shape and the news seam (other clusters) |
| Reporting ("zero authority") | Analytics; the measure-set result container, Item 7 |

What is left that only a Book cares about is a **policy set**: which money rules, which protection posture, which reconciliation stance, which mode-transition triggers apply to this Book. That is the thing FM-8 calls "BMS policies", and it is a *record*, not a machine.

### 2.2 Bucketing

**Stays QMF as a record kind; the machine re-buckets to the node.** **Seam shape:** a **BMS policy record** — an AD-16 kind, its own contract, fingerprinted, versioned, addable-never-redefined — plus a **dated Book↔BMS binding** carried on the Book binding record (Item 3). QMF carries the declaration and the binding history. The node carries the ledgers, the counters, the desks, and the enforcement.

**QMF still carries** (do not lose these in the re-bucketing): the Treasury boundary-event shape (the legacy `{sweep, refund, re_seed}` closed set is a good donor — `contracts/ct-bms-01-treasury-event.md:19-27`), the reconciliation verdict vocabulary (already ratified in AD-27: *"QMF defines the evidence shapes and the verdict vocabulary `reconciled | drift | unknown`"*, `:275`), and the mode-transition record shape (Item 4).

### 2.3 Recommended ruling

**"BMS" names a rulebook a Book follows, not a machine that sits above Books. A Book binds exactly one BMS policy at any instant — a dated, append-only binding, never a merge.**

Concretely:

- A BMS policy is a registry record kind with its own fingerprint and contract format version. Many may exist. One BMS policy may govern many Books.
- The Book binding (Item 3) carries `bms_policy_fingerprint` — exactly one, resolved as of a knowledge time. Re-binding is a new dated binding record with a `supersedes` edge; the old binding is never rewritten (AD-8/AD-16 append-only).
- **No selection, no merging, ever** — which is precisely what FM-8 already forbids; this ruling makes the prohibition structural rather than a warning.
- Cardinality-one here is a *deliberate ruling*, as AD-17 requires (*"no hardcoded cardinality-one without a ruling"*, `:167`), and it mirrors the precedent already set for Bots: *"one Bot is bound to exactly one Book at any time, and re-binding never mints a new Bot"* (DEC-0115, `docs/components/qmf-risk.md:59`). Multiplicity is fully preserved in the recursive sense — many policies exist, a Book may rebind over time, one policy governs many Books.

**Alternatives weighed.** (a) *Several simultaneous BMS policies with a declared precedence order.* This is what FM-8's wording hints at and it is genuinely attractive for layering (a house policy + a prop-firm overlay). Rejected **for now** because it requires a merge/resolution algorithm nobody has written, and "most-restrictive-wins" across incommensurable rule kinds is not a rule, it is a research project. Critically, choosing one-at-a-time does **not** foreclose it: under AD-5/AD-16 a future *composed* BMS policy kind — one record that declares its children and its own resolution rule, exactly the AD-17 composite idiom — is an **addable kind**, not a redefinition. Layering later arrives as a new kind, not a breaking change. (b) *Keep BMS as a system component above Books.* Rejected: three of its four desks are already re-homed by ratified ADs; keeping the component would re-create Records and Reporting inside `qmf-risk` in violation of AD-2's default-deny and `qmf-risk.md:69`. (c) *Retire the acronym entirely.* Tempting given the glossary's admission that no expansion is fixed, but the operator uses the word fluently and a rename costs continuity; better to fix its **referent** and let the expansion stay unfixed.

### 2.4 What would change it

The operator saying BMS is, in his head, a running supervisor he expects to watch on a console — in which case BMS stays a node component and QMF carries only its policy declaration, which is the same record with a different owner label. Or: a concrete near-term need for two overlapping rulebooks (a prop-firm overlay is the realistic trigger, and P-6 already flags prop-firm shapes as a seam to verify). If that need is real *today*, mint the composed-policy kind now rather than later.

---

## Item 3 — The Book binding, and may one Book bind accounts at several venues? (P-4 / X-5 first half)

**This is the item X-5 says must be ruled before same-tick priority. It is the highest-consequence item in this brief.**

### 3.1 Evidence, precedence applied

**Current corpus (highest):** *"Books bind to accounts. An account carries a role (live, demo, paper-validation, paper-benched, or prop-firm), and Venue and Account are first-class nouns defined in `COMP-QMF-CORE` with their records owned by `COMP-QMF-REGISTRY`"* (`docs/components/qmf-risk.md:61`, DEC-0107); glossary: *"One Venue may hold many Accounts… Books bind to Accounts, not directly to Venues"* (`docs/glossary.md:22`). **Neither states whether one Book may bind accounts at several distinct venues — not-found either way, in every dossier.** The spine leans permissive: *"Multi-broker (≈6 venues) and broker migration are **normal, not special cases**"* and *"**Broker identity is deployment configuration, never architecture**"* (AD-9, `:110`).

**Old wiki:** *"Book-to-account assignment is operator-configured through the desktop console, belongs to system-settings scope, and is mutable and journaled"* (`components/connection-manager.md:41`); *"The future multi-account/multi-platform load balancer attaches at this boundary. It is not a V1 implementation requirement"* (`:44`); V1 forex-only, single platform cTrader (`system/invariants.md:41`).

**Old planning:** the inverse cardinality is stated plainly — *"multiple books share ONE broker account by design… AD-30 makes account binding a free operator choice"* (`reviews/review-adversary.md:127`), with reconciliation per `account_id` and treasury ledgers per `book_id`, so an account's virtual equity is a cross-book sum.

**GitBook:** account binding lives at the adapter (`contracts/ct-adapter-01-broker-adapter-command.md:15`), not at the Book — multi-venue not addressed.

**The decisive current-corpus fact nobody in the legacy layers had:** AD-27 defines the unit of protection and uncertainty. *"the unit of `UNKNOWN` blocking, of `WriterId` ownership, and of the gapless per-writer sequence is the **(VenueId, account)** pair — coarser than an account binding… strictly finer than a connection"* (`ARCHITECTURE-SPINE.md:270`). And AD-8: *"instants alone never totally order events… the deterministic tie-break `(instant, writer, sequence)` is a **replay-determinism device with no causal meaning**"* (`:97`). Two venues have two clocks, two latencies, and no shared ordering that means anything.

### 3.2 Bucketing

**Stays QMF.** **Seam shape:** a **Book binding record** — an AD-16 kind whose identity is `(book_definition_fingerprint, VenueId, AccountId, role, world)`, deliberately mirroring AD-26's account-binding identity `(VenueId, AccountId, role, world)` (`:260`) plus the Book. Dated, append-only, outside Book identity — same idiom DEC-0115 already uses for Bot↔Book.

**Re-buckets to the node:** which bindings exist at deploy time, load balancing across them, and every runtime action within a binding.

### 3.3 Recommended ruling

**Yes — one Book may bind accounts at several venues. But each binding is its own money box and its own protection scope, and nothing in a Book's contract may require a decision that spans two bindings inside one instant.**

Four clauses:

1. **A Book has one-or-more bindings** (AD-17-conformant; no hardcoded one). Each binding is `(book, VenueId, AccountId, role, world)`.
2. **The binding is the risk domain.** Virtual ledger, cycle, budget, breaker counters, exposure, mode, and protective scope all live per binding. **The risk domain is deliberately the same unit as AD-27's command stream, `(VenueId, account)`** — so a protective action never has to arbitrate across streams, and an `UNKNOWN` block on one venue does not freeze another. This is the single design choice that makes multi-venue Books safe rather than a race condition wearing a charter.
3. **Same-tick priority is defined within a binding and explicitly undefined across bindings.** This is X-5's resolution shape, and it hands the same-tick cluster a scope it can actually write against. A Book-wide flatten is **N binding-scoped actions**, structured as AD-27's compound command: *"each child carries a derived identity (parent `fp1` + declared ordinal)… the parent's outcome is the meet of its children — any child `UNKNOWN` makes the parent `UNKNOWN`"* (`:271`). No false total order is ever asserted.
4. **Cross-binding figures are evidence, never inputs to a synchronous decision.** A Book-level exposure or equity number is a read-time fold over binding evidence at a declared knowledge time (AD-19/AD-25 idiom), carrying lineage, produced as a measure-set result (Item 7). It never gates an order.

Three consequences that must be stated rather than discovered:

- **Currency, fail-closed (P-2 / A-5).** The Book declares one `accounting_currency`. A binding whose account currency differs is **refused until a conversion policy is ratified** — cross-currency conversion is explicitly unratified everywhere in the corpus (`standards/broker-equity-computation.json:50-63`: `cross_currency_conversion_in_scope: false`, refusal `CROSS_CURRENCY_CONVERSION_UNRATIFIED`). Fail closed beats inventing an FX rate source. The seam stays open for the day it is ruled.
- **Capability, fail-closed (P-8 / T-4).** A binding is admissible only where the venue's CT-18 declaration **and** its venue-observation profile satisfy the Book's `required_venue_capabilities` — position model, protection primitives, command scopes. Checked at bind time. AD-28 already makes this refusal-backed: *"A `measured-at-connection` capability is `unavailable dependency` until its profile exists"* (`:286`). Netting-vs-hedging in particular changes the Book's money arithmetic and must be declared, not discovered.
- **Shared accounts stay legal, with the coupling named.** Several Books may bind one `(Venue, Account)`; each keeps its own virtual ledger over the shared broker balance (the legacy design, `review-adversary.md:127`). The honest cost: they share one AD-27 command stream, so one Book's `UNKNOWN` blocks the other's commands on that account. QMF permits it and documents it; whether to isolate by giving each Book its own account is a deployment choice, per AD-9's "broker identity is deployment configuration".

**Alternatives weighed.** (a) *One Book, one venue, full stop.* Simplest, and defensible for V1 where the corpus is forex-only single-platform. Rejected because AD-9 has already ratified ≈6 venues and migration as normal, and because forbidding it now would force a schema break later — exactly what AD-5 exists to avoid. It also silently kills the PM's most natural risk move (splitting a strategy across brokers for counterparty diversification). (b) *Multi-venue with a genuine cross-venue priority order.* Rejected: AD-8 says the only available tie-break has no causal meaning, so a cross-venue total order would be a fiction that looks deterministic. Better an explicit undefined boundary than a false guarantee. (c) *Multi-venue with one pooled ledger across bindings.* Rejected: requires the unratified FX conversion, and breaks the AD-27 stream isolation that makes clause 3 work.

### 3.4 What would change it

A ratified cross-currency conversion policy (source, knowledge time, rounding) would upgrade clause 4 from evidence-only toward genuine portfolio math. A venue capability set that turns out to support genuinely atomic cross-account action would reopen clause 3 — but no such capability exists on the cTrader-platform profile, and none is expected. Operator preference for one-Book-one-venue would simplify everything and cost only future flexibility.

---

## Item 4 — Lifecycle states: where they live, and the BENCHED namespace collision

### 4.1 Evidence, precedence applied

**Current corpus (highest):** `CT-24` is `wiring_status: reserved-evidence-only`, everything null, with the honest note *"State values, transition triggers, account roles, rollback, duplicate prevention, continuity, and audit fields remain unresolved"* (`docs/contracts/ct-24-book-mode.yaml:144`). And the collision is flagged explicitly: *"**BENCHED**: Do not assign BENCHED a canonical schema yet. The name is overloaded between Book mode and Bot seat state under `GAP(GAP-0045)`"* (`docs/glossary.md:518-520`).

**Old wiki (next):** the split is already made, verbatim — *"The V1 book-mode map emits only LIVE and PAPER. **BENCHED is a bot roster-seat state.** BENCHED and STOOD_DOWN remain reserved values in the wider mode vocabulary"* (`components/paper-mode-system.md:32`); *"Bot breaker benching does NOT mutate book mode"* (`ct-book-02:37`); and `ADMITTED` is *"a registration state, never a book mode"* (`glossary/index.md:19`).

**Old node build (ratified standards + code):** the split is *implemented* — `V1_BOOK_MODES = {"LIVE","PAPER"}`, `RESERVED_BOOK_MODES = {"BENCHED","STOOD_DOWN"}` (`mode_registry.py:38-40`), and `frozen-counterfactual-paper-semantics.json:43-49` carries `book_level_benched_write: false` with the invariant *"A BENCHED bot does not change the book mode."*

**GitBook (lowest here):** the *source of the collision* — one shared enum `[LIVE, PAPER, BENCHED, STOOD_DOWN]` appearing identically in CT-BOOK-02, CT-BMS-02 and CT-PAPER-01 (`contracts/ct-book-02-book-mode-state.md:7-22`).

**Precedence verdict: the split wins, decisively.** Three layers ratify or implement it; only the oldest layer conflates, and the wiki's own delta register already flagged that conflation as *"mix[ing] two namespaces… must be split"*. The current corpus is not disagreeing — it is refusing to inherit an unratified answer.

The current corpus also supplies the shape the legacy layers lacked. AD-25: lifecycle on an immutable store is *"a **read-time fold** over the object's edge stream"*, never a mutable state machine (`:241`). AD-27 applies the same to order state: *"The order-state machine… is a **read-time fold** over the observation stream… never a gate on recording"* (`:274`).

### 4.2 Bucketing

**Stays QMF as the record shape; the state machine's contents re-bucket to the node.** **Seam shape:** `CT-24` keeps its name ("Book mode and account-transition contract") and becomes the **Book-binding transition record** contract: an append-only typed event carrying `binding identity, from_state, to_state, trigger, authority, scope, evidence_refs, occurred_at, known_at`. Current state is never stored — it is the fold. The legacy `trigger_decision` pattern `DEC-[0-9]{4}` is a good donor and should survive as a required field: no transition without a ratified decision behind it.

**QMF carries** the record shape, the fold rule, and the refusal for an illegal transition. **The node carries** the state vocabulary's *triggers* and the runtime that fires them.

### 4.3 Recommended ruling

**State lives on bindings, never on definitions, and it is a fold over append-only transition records. There are two different binding kinds and they never share a state list.**

- **Book-binding state** — the Book↔(venue, account) binding. Its vocabulary is minimal and **never contains BENCHED**.
- **Bot-seat state** — the Bot↔Book binding (DEC-0115's dated record). BENCHED lives here and only here.

Two records, two vocabularies, no shared enum. This dissolves GAP-0045's overload structurally rather than by convention: the two values cannot collide because they are fields on different kinds. It also matches what the old node build already shipped, so it is a re-ratification rather than a novelty.

**Deliberately not ruled here** (belongs to the paper-mode / kill-line / stop-out clusters): the actual state values, their triggers, `STOOD_DOWN`'s fate, and whether paper is fail-mechanism-only or a standing state — the latter is on record as an open contradiction (`tracker/trading-node-notes.md:25`). This item pins the *container* so those clusters can fill it without re-litigating where state lives.

One structural rule worth carrying regardless of the values chosen: **`ADMITTED` is not a state on either binding.** It is the gap between a signed promotion occurrence (AD-18) and the first binding record existing. Modelling "registered but not yet bound" as absence-of-binding is cheaper and unfalsifiable than modelling it as a state.

**Alternatives weighed.** (a) *One shared mode enum, as GitBook had.* Rejected: it is the documented source of the collision, and every later layer split it. (b) *Store current state as a mutable field with an audit log beside it.* Rejected: contradicts AD-25/AD-27's fold pattern and AD-8's append-only law; it also re-creates the classic drift bug where the field and the log disagree after a crash. (c) *Put state on the Book definition.* Rejected outright: definitions are immutable and fingerprinted; a mutable field would change identity on every transition.

### 4.4 What would change it

A ruling that paper is a **standing state feeding alpha-decay** rather than a fail mechanism would enlarge the Book-binding vocabulary considerably (and would need A-1's comparison-cohort rule alongside it). It would not change where state lives or the two-lists split.

---

## Item 5 — Version compatibility (GAP-0039's most-neglected clause)

### 5.1 Evidence, precedence applied

**Not-found in every single corpus layer.** All nine dossiers report the same: book *types* are versioned JSON Schemas, `book_type_version` semver exists, `BOOK_DEFINITION_CONFLICT` refuses a stable `book_id` re-used with different content (`standards/book-definition-minimal-existence.json:76`) — **but no layer states a version-succession or ledger-inheritance rule**, and the specific "scalping-book-v2 is a new Book that never inherits v1's ledger" sentence appears nowhere. The nearest analogues are all *bot*-side: BotSpec immutability with `parent_id` (`bot-registry-lineage-spec.md:20-22`), *"Changing behaviorally consumed specification/configuration mints a new bot specification version"* (`object-lifecycle-bot.md:84-85`).

**The current corpus supplies the answer machinery.** AD-5: two ladders; *"a format version's meaning never changes after the fact"*; *"Re-deriving a value under a newer calendar/tzdata version produces a **new artifact with its own fingerprint and a lineage edge to the old one** — never a rewrite, never a silent equality"* (`:68`). AD-16: id = `fp1`; lineage that accrues after birth lives in typed edge records (`:161`). AD-17: the Bot precedent — identity is content, binding is separate.

### 5.2 Bucketing

**Stays QMF entirely.** This is identity and lineage, which is framework territory by construction. **Seam shape:** falls out of Item 1's fingerprint rule plus one requested edge kind.

### 5.3 Recommended ruling

**Change the content, mint a new Book. The old one is never edited. A `supersedes` edge links them, so the lineage is one line even though the identities are two.**

Because Item 1 puts the numbers *inside* the fingerprinted content, this is automatic rather than a policy anyone must remember to enforce:

- Any change to charter, money rules, admission bar, leash grammar, capacity, declared currency, or required capabilities changes `fp1` ⇒ new Book identity ⇒ `supersedes` edge to the predecessor (AD-16's existing edge kind).
- **Money does not follow automatically.** Ledger and cycle live on the *binding*; a binding names exactly one Book fingerprint. A new Book identity therefore needs a new binding, and a new binding starts a fresh cycle — which is the never-written "v2 does not inherit v1's ledger" rule, delivered structurally.
- **History does follow, if signed.** Request one new edge kind from the registry sitting: **`continues-as`** — a human-signed typed edge asserting that binding B continues binding A's performance record with a documented discontinuity. This is exactly five-hats **P-5**'s requested continuity edge, so one edge kind serves both Book versioning *and* broker migration. Without it, every rule tweak and every broker move resets the decay signal to zero (A-1's failure mode).
- **Compatibility is exact, never approximate.** A binding cites the Book definition's **fingerprint**, not a version string. A node that cannot interpret a Book definition's contract format version returns `unsupported capability` (AD-11) — never a best-effort read. There is no "compatible-ish" band, by design.

**Alternatives weighed.** (a) *Mutable Books with an internal `version` counter and an edit history.* This is closest to what a console-driven operator would expect, and it is what the legacy node build's registry-slot design implied. Rejected: any result citing a Book would cite a moving target, and AD-16 forbids minting ids independently of content. (b) *Automatic ledger continuity across versions.* Rejected: it silently mixes money earned under two different rule sets in one cycle, which is exactly what the treasury's "money resets between cycles, knowledge persists" invariant (L5, `system/invariants.md:23`) was protecting against. (c) *No continuity edge at all — every new version is a fresh history.* Rejected: kills alpha-decay sensing, which DEC-0115 explicitly preserves for Bots; it would be perverse to preserve it for Bots and destroy it for Books.

### 5.4 What would change it

An operator who wants to tune a live Book's numbers daily would find "every tweak mints a new Book" heavy. The mitigation is tooling, not architecture: minting is cheap, and the console can present a lineage as one Book with a version history. If it still chafes, the alternative is to declare a small set of slots explicitly **non-identity** (display-only per AD-10's versioned exclusion) — but any number that changes behaviour must never be in that set.

---

## Item 6 — How a new Book or BMS proves itself before carrying money (the operator's own lead)

### 6.1 Evidence, precedence applied

**Not-found across the entire corpus, in every layer.** The local-current dossier is explicit: *"No text in `docs/` describes how a **Book** or **BMS** itself proves itself before carrying money… This is a genuine gap in both layers, not just the current one."* The GitBook dossier concurs: *"there is **NO explicit 'new-book validation lead / probation' procedure** — no rule that a brand-new Book must run in PAPER for N days before carrying money."* Every layer's validation machinery is **bot-centric**: the exam battery certifies a *bot against a book*, which is the opposite direction.

**The nearest real donors:**

- **A unified registration gate** — *"Unified registration serves Book→BMS and bot→Book with schema, configuration, parity, and paired-demo checks; refusal is journaled; promotion stays human"* (`TND-DELTA:69` / K-23, `[WIKI-2026-07]`). Four autonomous checks, human promotion mandatory.
- **Multi-book structural proof (SM-5)** — V1 must prove a second book instance *"with a materially different profile… instantiates and passes door/sizing tests **without any change to global infrastructure**"* (`prd.md:554`).
- **Write-path proof gates** — every BMS store *"validates schema/trigger/foreign-key/Records-evidence at open and fails closed on drift"* (`standards/treasury-…json:27` et al.).
- **The money-carry gate** — `ledger_reconciles_gate_ready` is *"true only for fresh live-binding verdict=reconciled reports"* (`reconciliation-…json:82`).
- **The cautionary tale** — FORM-0006 (`R_max_usd <= B*b*Lbar`) shipped as a ratified formula with USD on the left and R on the right, survived three corpus generations, and was killed only by DEC-0077 as *"dimensionally invalid under the corrected meaning of R"* (`ADR-0010:25`). Nothing in any layer's validation would have caught it, because no layer ever type-checked a money rule.

**Standing constraint that rules out the obvious answer:** a Book probation/trial period is on the DO-NOT-REVIVE list (paper-redemption/probation loops), DEC-0069 killed paper twins, and the corpus never had a Book probation rule to revive anyway. So the tempting "run it in paper for a month" answer is off the table before it is considered.

### 6.2 Bucketing

**Stays QMF.** Validating a declaration against its contract is framework work — it is a contract test (AD-4) plus a promotion evidence slot (AD-18). **Seam shape:** two additions to the Book-definition contract (a `worked_example` field and a dimensional declaration on every money rule) plus a named evidence packet the promotion card cites.

**Re-buckets to the node:** the reconciliation verdict that decides whether real money is actually safe to place today, and any runtime health gating.

### 6.3 Recommended ruling

**A new Book proves itself in three layers — paperwork, arithmetic, signature. No trial period.**

**Layer 1 — Conformance (machine, cheap, at registration).** The definition validates against its contract format version: all six sections present, every parameter carrying a declared unit, every number an exact rational or scaled integer, every referenced measure/producer identity resolvable, every declared venue capability a real CT-18 field. Failures are typed refusals (AD-11), journaled as `data quality` or a Book-specific refusal class. This is the legacy unified-registration gate's "schema + configuration" checks, kept.

**Layer 2 — Dimensional proof (machine, and this is the new part).** Two requirements:

- **Every money rule declares the units of both sides**, and a contract test asserts they reconcile. `R_max_usd <= B * b * Lbar` fails this test in one second: USD on the left, a dimensionless count × a dimensionless ratio × an R-quantity on the right. This is the direct, cheap antidote to the FORM-0006 failure and to the standing note that FORM-0004/0006 are dimensionally suspect.
- **The Book definition carries a required, fingerprinted `worked_example`**: a declared set of inputs and the exact expected outputs, authored with **the Book's own declared numbers** (never invented reference numbers — AD-13). The contract test re-computes the example from the definition and refuses on mismatch. This is the legacy SCN-0001 checksum pattern (`S→U→D→offer→take`) promoted from a scenario document into a required contract field, so it can never drift away from the rules it checks.

The same two layers apply verbatim to a BMS policy record. No separate machinery.

**Layer 3 — Human signature before money (AD-18).** A Book binding to a `role = live` account requires a promotion occurrence card whose evidence packet cites: the Layer-1 conformance proof, the Layer-2 dimensional + worked-example proof, the binding identity `(venue, account, role, world)`, the capability-satisfaction proof from Item 3, and the resolved BMS policy fingerprint. Per T-10, this must be **one assembled packet signed once**, not a scavenger hunt — a daily job that takes an hour becomes a rubber stamp. The card's mandatory plain-words summary is an identity field (AD-18, `:173`).

**What this deliberately does not include, and why.** No probation window (do-not-revive). No paper-first requirement for Books (never existed; would collide with the unresolved paper-scope contradiction). No performance bar for a Book itself (a Book has no performance until bots trade in it — measuring it pre-money would require the invented numbers AD-13 forbids). No auto-blocking on health (DEC-0049 is open, and X-3's resolution shape says QMF emits a verdict, the node decides to halt).

**Alternatives weighed.** (a) *Reuse the bot exam battery on Books.* Rejected: category error. The battery measures edge; a Book declares rules. (b) *Require a Book to run in paper before live.* Rejected on the do-not-revive list and because paper's own scope is an open contradiction. (c) *Conformance only, no dimensional proof.* Rejected: that is exactly the regime under which FORM-0006 survived three generations. (d) *Dimensional proof as a lint warning rather than a refusal.* Rejected: a warning on the money path is a refusal that someone will ignore at 3am.

### 6.4 What would change it

If the operator wants QMX to *generate* Books agentically at volume (the stated default — "QMX will create new Books/BMS/bots by default"), Layer 3's one-signature-per-Book could become the bottleneck. The mitigation is batching the packet, not weakening it: promotion stays human-only under L17. If a genuine pre-money observation period is wanted despite the do-not-revive list, that needs an explicit operator ruling reopening it — it is not a delegate-quality call.

---

## Item 7 — "The Book sets the bar": the qualification container (contract only, metrics deferred)

### 7.1 Evidence, precedence applied

**The phrase is not-found verbatim in any corpus. The concept is everywhere, and it is consistent.**

- **GitBook:** *"A bot is certified against the specific book contract it intends to join, not in the abstract"* (`contracts/ct-exam-01-exam-certificate.md:14`), with the certificate carrying `bot_id, book_profile, labeler_versions, ev_by_regime, mean_loss_r, fire_rate_band, breaker_expectation, cost_ratio` (`:22-32`) and the hard rule that the certificate *"does NOT authorize live trading"* — the Book's own admission door decides.
- **Old wiki:** identical, plus the parity rule (L10) — a certificate whose producer versions differ from live is void.
- **Old planning:** *"the Examination Engine certifies a bot **against a specific book's profile** — never in the abstract"* (DEC-0055); *"validation methods vary per book type"* (AD-26 legacy).
- **Current corpus:** none of this survives. `qmf-risk.md` mentions certification nowhere. What it does supply: `GAP(GAP-0045): Define stop-out, benchmark/roster terminology, bench behavior, and **fresh alpha-decay evidence**` (`:83`) — "fresh" being the operative word, and the reason the *metrics* wait for the backtesting sitting.

**Five-hats A-2 asks this cluster for the missing container**, in almost these words: *"a fingerprinted performance result over a declared population and period, produced by a versioned formula, carrying units — has no owning contract anywhere… the risk sitting must still mint the **container**."* A-3 adds the rule the container needs: bind the metric's contract format version to its arithmetic, or two runs under different library versions share one identity and hold different numbers.

### 7.2 Bucketing

**Stays QMF — container only.** **Seam shape:** two additions.

1. **`admission_bar` (Book definition, section 3)** — the Book *declares* the bar.
2. **A measure-set result kind** — a new AD-16 registry kind that *reports* measurements. One kind serves both the qualification certificate and the analyst's performance result (A-2), because they are the same shape.

**Re-buckets away entirely:** who computes the measures (data / backtesting sitting), what the measures are, and what the thresholds are. The admission *evaluation* — comparing a presented result against a declared bar at bind time — is a node act; QMF carries the declaration, the result shape, and the refusal.

### 7.3 Recommended ruling

**The Book writes the bar. The result reports the numbers. Comparison is mechanical. Thresholds may be blank, and blank blocks live money.**

**`admission_bar`** is an ordered set of **requirement records**, each carrying:

- `measure_identity` — opaque, minted under AD-9's discipline (stable, never reused, never parsed), pointing at a measure the *data/backtesting* side defines.
- `unit` — mandatory, per GAP-0044's standing demand. No unitless numbers on this path, ever.
- `comparison` — `at-least | at-most | within-band`.
- `threshold` — an exact rational, **or the explicit literal `unratified` with a gap reference**.
- `evidence_requirements` — the world, the minimum evidence window, and the producer contract format versions the measurement must have been produced under.

**Fail-closed rule:** a Book whose `admission_bar` contains any `unratified` threshold may be registered and may bind to non-live roles, but **binding to a `role = live` account is a `policy rejection` refusal**. This is what lets the container ship complete *today* while every number stays honestly blank pending the backtesting sitting — the AD-13 "no invented numbers" discipline expressed as a structural gate rather than a promise.

**The measure-set result kind** carries an AD-12 result label plus: declared population (which bot, which binding, which cohort), declared period (event-time range **and** the knowledge-time bound it was computed under — A-4's as-of requirement), the ordered measure set with values and units, and the producer fingerprints. Two rules on it:

- **A-3's rule, adopted:** the metric's arithmetic is pinned by its **contract format version**, not by package SemVer. Changing how a measure is computed is a format-version mint (AD-5), so identity moves when meaning moves. Package SemVer never enters identity (AD-12, `:134`).
- **Parity, carried structurally from L10:** a result whose producer contract format versions differ from those declared in the Book's `evidence_requirements` does not satisfy the bar — a refusal, not a warning. This preserves the legacy "certificate void on labeler change" rule without importing any of its machinery.

**Explicitly refused here:** any composite score, any 0–100 rating, any tier band, any weighted aggregate. DPR/PRS are dead (DEC-0093, *"legacy-only; must not return as risk controls"*), and the clash report's own post-mortem — *"Six declared weights (25/20/20/10/15/10) are precisely 'opinions wearing math'"* — is the reason the container carries **an ordered set of separately-declared measures**, never one number. Each requirement passes or fails on its own terms.

**Alternatives weighed.** (a) *Wait for the backtesting sitting to design the container too.* Rejected: the container is the thing that lets the metrics be added later without a schema break; designing it after the metrics guarantees the metrics shape it. (b) *Two separate kinds for qualification certificate and performance result.* Rejected: same shape, and one kind means the analyst's decay comparison and the Book's admission bar read the same evidence — which is precisely what A-1 needs. (c) *Let a Book inherit a default bar.* Rejected: "the Book sets the bar" means each Book sets its own; a default bar is a universal recipe card by the back door, which AD-16 exists to prevent.

### 7.4 What would change it

If the backtesting sitting concludes that qualification requires a genuinely composite judgement (not a set of independent thresholds), the container needs a composite requirement record — addable under AD-16, not a redefinition, so the shape survives. If A-1's comparison-cohort rule lands somewhere other than the risk sitting, `evidence_requirements` should carry the cohort reference rather than restate the rule.

---

## Item 8 — Contract mapping, registry kinds, and the standing sitting-close obligations

### 8.1 What each CT becomes

| Contract | Today | Proposed |
|---|---|---|
| `CT-22` "Book and BMS charter contract" | `type/fields/enums/units/nullability` all null, GAP-0039 | **The Book-definition record contract.** AD-16 per-kind schema, six sections + four declaration blocks, format version 1, fingerprint = identity |
| *(new id, allocated by the sitting)* | — | **The BMS policy record contract.** Same discipline; a Book binds exactly one (Item 2) |
| *(new id, allocated by the sitting)* | — | **The Book-binding record contract.** Identity `(book fp, VenueId, AccountId, role, world)`; carries `bms_policy_fingerprint`; the risk domain (Item 3) |
| `CT-24` "Book mode and account-transition" | reserved-evidence-only, GAP-0041 | **Book-binding transition record.** Append-only; state is the fold; `trigger_decision` required (Item 4). Name already fits |
| `CT-23` "Risk evaluation and refusal" | reserved-unwired, caller unassigned | Unchanged in ownership. **This cluster pins only its request envelope**: every evaluation request carries the Book-definition fingerprint and the Book-binding identity, so every decision is reproducible and attributable. Doors, sizing and priority belong to other clusters and the node |
| `CT-25` "Risk and Book journal-evidence" | reserved-unwired | Unchanged in ownership. **This cluster pins**: every risk-journal event carries the Book-definition fingerprint and the binding identity; binding transitions are `risk transition`, one of the seven ratified journal event types (DEC-0048 / DEC-0119) |

Three new record kinds means three contracts — AD-16 is explicit that per-kind schemas each get their own versioned contract (`:161`). Id allocation is left to the sitting's synthesis lead to avoid collisions with other clusters.

### 8.2 Registry-sitting requests

- **One new edge kind: `continues-as`** — human-signed, asserting that one binding continues another's performance record across a Book version change or a broker migration. Serves Item 5 and five-hats P-5 with one kind. Additive under AD-16 ("kinds are addable, never redefined").
- **Confirmation that `supersedes` covers Book-version succession** — it should; no new kind needed.
- **P-1's cross-venue instrument equivalence record** is *not* this cluster's to mint (registry sitting owns it, per X-2), but Item 3's clause 4 consumes it: a cross-binding exposure figure is uncomputable without it. Flag the dependency in both agendas.

### 8.3 Standing sitting-close obligations (D-1, D-4)

- **D-1 — inter-library edge request: NONE REQUIRED.** `qmf-risk` imports `qmf-core` only; registration, lineage and journal evidence reach `qmf-registry` and `qmf-data` through the application composition root under default-deny. This is already the ratified position (`docs/components/qmf-risk.md:69`; AD-2 dependency direction) and nothing in this brief needs it changed. The Book-definition record is a `qmf-core`-typed value; the registry record wrapping it is minted by the root — the same pattern AD-28 pins for venue emissions (`:284`).
- **D-4 — public surface rule.** `qmf-risk`'s public surface is: the Book-definition, BMS-policy, Book-binding and transition value types (frozen dataclasses per AD-3), the `admission_bar` requirement and measure-set-result value types, and the CT-22/23/24/25 Protocols. Everything else is underscore-private.

---

## Cross-cluster handoffs

| To | What |
|---|---|
| **Same-tick priority cluster** | X-5 is answered: **the risk domain is the Book binding = AD-27's `(VenueId, account)` command stream.** Write priority *within* a domain; declare the cross-domain boundary explicitly non-deterministic. A Book-wide action is an AD-27 compound command (parent `UNKNOWN` if any child is) |
| **Flatten-authority assignment** | Whatever authority is assigned, its **scope is a Book binding**, never "the Book". Flatten across a multi-venue Book is N binding-scoped mechanical closes, each carrying AD-27's required typed scope (`account \| account-binding \| instrument-within-binding`) |
| **Paper-mode / kill-line cluster** | The state container is Item 4: transitions are append-only records on the *binding*, state is the fold, `BENCHED` is forbidden in the Book-binding vocabulary. Fill the values and triggers; do not re-litigate where state lives |
| **Stop-out / breaker cluster** | Breaker counters are **per binding**, not per Book — a Book at three venues has three counters. This matters for B's double duty: if B is also a money-ladder divisor, the divisor is binding-scoped too |
| **Money-ladder / formula cluster** | Item 6 Layer 2 is the delivery vehicle for the dimensional discipline: every replacement formula declares units on both sides and ships a worked example inside the Book definition. FORM-0004/0006 both fail that test today |
| **Backtesting sitting** | Item 7's measure-set result kind is the container for SR*/deflated statistics and for A-2's performance result. The metrics land in it without a schema break |
| **Registry sitting** | `continues-as` edge kind; P-1 equivalence record dependency (Item 8.2) |
| **News / SQS clusters** | Nothing owed from this cluster except that both are declared **per binding** in scope, and both write `risk transition` journal events carrying the binding identity |

---

## Operator questions

Six questions. Each carries the recommendation first. Answering "yes" to all six adopts this brief as written.

---

### Q1 — What is a "BMS", and can a Book follow two at once? *(resolves DEC-0095)*

**Recommendation: a BMS is a rulebook a Book follows, not a machine sitting above Books — and a Book follows exactly one rulebook at a time.**

Right now "BMS" means a service with four desks: it kept the money ledger, measured exposure, wrote every journal entry and held the protection policy. Three of those four jobs have already moved elsewhere in the new design — journals are the data layer's, records are the registry's, sessions are the venue layer's. What is genuinely left is a **rulebook**: which money rules, which protection posture, which transition triggers apply to this Book. Rulebooks are written down, versioned, and swappable. A Book names exactly one, by date. If you change it, that is a new dated entry — the old one stays on the record, nothing is overwritten, and nothing ever has to guess how to blend two rulebooks together. Later, if you genuinely need a house rulebook plus a prop-firm overlay, we add a *combined* rulebook as a new thing; it does not break anything built before it.

**Is a BMS a rulebook a Book follows (recommended), or a machine that supervises all Books?**

---

### Q2 — Can one Book run at several brokers at the same time? *(five-hats P-4 / X-5 — must be answered before same-tick priority)*

**Recommendation: yes — but each broker-account is its own money box and its own emergency scope, and nothing decides across two brokers inside the same instant.**

You have said six brokers is normal and that moving between brokers is normal. Splitting one strategy across three of them is a real risk-reduction move, so we should not forbid it. The catch is that two brokers have two clocks and two connections, and there is no honest way to say which of two things "happened first" across them. So the rule is: one Book, several bindings — one per broker-account. Each binding keeps its own balance, its own daily budget, its own breaker count, and its own emergency actions. Combined figures across brokers are a *report*, produced afterwards with a stated as-of time, never something a live order waits on. Two consequences you should see now: **(a)** if a broker account is in a currency different from the Book's declared currency, that binding is refused until we rule how to convert — we will not guess an exchange rate; **(b)** a Book refuses to bind to a broker that cannot do what its rules need (for example, hedging vs netting positions), checked when you bind it, not when a trade goes wrong.

**Can one Book bind accounts at several brokers, on those terms? Yes / no.**

---

### Q3 — If you change a Book's rules or numbers, is that a new Book?

**Recommendation: yes — a new Book, permanently linked to the old one, and its money starts fresh unless you sign a continuation.**

A Book's numbers should live inside the Book, not behind a pointer, so that a Book always means exactly one thing and any past result can be traced to the exact rules that produced it. That means changing any number changes the Book's identity. The old Book is never edited — it stays readable forever, and the new one carries a link back to it. Money follows the *binding*, so a new Book gets a fresh cycle rather than inheriting the old balance. Your track record does **not** have to reset: signing a "this continues that" link keeps the performance history as one line with a visible marker where the change happened. The same link solves broker migration, so your history does not reset when you move brokers either.

**Rules change = new Book, linked to the old, fresh money, signed continuation for history. Yes / no.**

---

### Q4 — How does a brand-new Book prove itself before it touches money?

**Recommendation: paperwork, arithmetic, and your signature — no trial period.**

Three checks. **First**, the machine checks the Book is complete and well-formed: every rule present, every number carrying its unit, every reference resolving. **Second** — and this is the new part — the machine checks the Book's *arithmetic makes sense*: every money rule must state the units on both sides and they must reconcile, and the Book must carry a small worked example (its own inputs, its own expected answers) that the machine recomputes. This is the check that would have caught the broken `R_max_usd ≤ B·b·L̄` formula the day it was written instead of three document generations later. **Third**, you sign once, on one assembled page showing all of the above plus which broker account it will trade. No probation window, no "run it in paper for a month" — you have killed probation loops before and there is no reason to bring one back for Books. The same three checks cover a new rulebook (BMS).

**Paperwork + arithmetic proof + one signature, no trial period. Yes / no.**

---

### Q5 — "The Book sets the bar" — is this the right shape?

**Recommendation: the Book writes down its own bar as a list of named requirements; the report presents the measurements; the comparison is mechanical. Any requirement left blank blocks live money.**

Each Book carries its own list: "this measurement, in these units, must be at least / at most this much, measured over this much evidence." Each requirement stands alone — no single score, no 0-to-100 rating, no tiers. Those are dead and they should stay dead; the reason they failed is that six invented weights are opinions wearing a lab coat. Crucially, **the actual measurements and thresholds do not need to exist yet.** A Book can be written today with every threshold marked "not yet ruled" — it will register and it will run against a demo account, but it will **refuse to bind to real money** until you fill them in. That way the shape ships now and the numbers arrive from the backtesting sitting later, with nothing invented in between.

**Named requirements with units, blanks allowed, blanks block live money. Yes / no.**

---

### Q6 — Book state and bot-seat state: one list or two?

**Recommendation: two separate lists that never mix — and "BENCHED" belongs only to the bot-seat list.**

Today one word, `BENCHED`, is used for two different things: a Book being stood down, and a single bot losing its seat for the day after consecutive losses. The current documentation flags this as an unresolved overload, and every later version of the old system had already split them. The clean fix is structural rather than a naming convention: a Book's state lives on the Book's binding to a broker account, a bot's state lives on the bot's binding to a Book, and each has its own separate list of possible states. They cannot collide because they are attached to different things. Also: neither list stores "current state" as an editable field — state is worked out by reading the history of transitions, so a crash can never leave the label and the history disagreeing. (What the states actually *are*, and what triggers them, is a different question that another part of this sitting is answering.)

**Two separate state lists, BENCHED only on the bot seat. Yes / no.**

---

## Confidence register

| Item | Confidence | Why |
|---|---|---|
| 1 — Book definition record | mixed | evidence-strong on the six-section grammar (four independent layers agree verbatim); **fresh design** on inline-identity numerics — a forced correction against AD-10/AD-16, found in no layer |
| 2 — BMS nature + DEC-0095 | mixed | evidence-strong that "several BMS per Book" is unsupported everywhere; **fresh design** on re-framing BMS as a policy record |
| 3 — Multi-venue binding | evidence-thin | explicitly not-found in all nine dossiers; the ruling is derived from AD-9 + AD-27 + AD-8 rather than from corpus evidence |
| 4 — State on bindings, BENCHED split | evidence-strong | wiki ratified it, node build implemented it, current corpus only refuses to inherit; fold-not-field is forced by AD-25/AD-27 |
| 5 — Version compatibility | fresh design | not-found in every layer; falls out of AD-5/AD-10/AD-16 once Item 1 lands |
| 6 — Book/BMS validation | fresh design | a genuine gap in every corpus layer; the dimensional-proof requirement is new and is the direct answer to the FORM-0006 post-mortem |
| 7 — Qualification container | mixed | evidence-strong on the concept (CT-EXAM-01 across three layers); **fresh design** on the container, deliberately metric-free |
| 8 — Contract mapping | delegate-quality | mechanical application of AD-16 to Items 1–7 |
