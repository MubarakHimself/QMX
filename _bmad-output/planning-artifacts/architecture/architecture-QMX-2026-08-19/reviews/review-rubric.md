# Rubric Review — ARCHITECTURE-SPINE.md (QMF V1 Foundation)

- **Artifact:** `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md` (status: draft, 2026-08-19)
- **Reviewer role:** rubric reviewer, six-point checklist
- **Grounding consulted (read-only):** `docs/gap-report.md`, `docs/constitution.md` (L1–L29), `docs/contracts/ct-05-version-fingerprint.yaml`, `.memlog.md`, `time-audit-architect.md`, `time-audit-devops.md`, `ctrader-time-research.md`
- **Declared scope honored:** registry / data / indicator / venue / risk contract detail is a later sitting and is **not** treated as a gap here.

---

## Verdict

The spine is a genuinely strong foundation document — all thirteen in-scope gaps have a matching AD, the time model absorbs every one of the nine amendments the two-lens audit demanded, and nothing in it contradicts a live operator ruling — but it ships with one **critical** hole (AD-10 names a fingerprint recipe it never defines, so the identity substrate cannot actually be built consistently by independent agents) plus a cluster of **high** findings where an in-scope divergence point is either unnamed (tier-2/3 commands, `qmf.*` namespace mechanics, per-package layout), left explicitly open with no safe default (inter-library edges), internally inconsistent (extension versioning), or silently dropped from the memlog / constitution (deprecation window, L27 reference usage, L6 no-shipped-mock-data).

**Disposition: ratify after remediation of C-1 and the H-tier findings.** None of these require reopening a ruling with the operator except H-5 (extension versioning) and H-7 (deprecation window restoration); the rest are transcription and specificity fixes.

---

## Scorecard

| # | Rubric item | Result | Weight of findings |
|---|---|---|---|
| 1 | Fixes the real divergence points for GAP-0001..0013, misses none in scope | **Partial** | 1 critical, 4 high |
| 2 | Every AD's Rule is enforceable and prevents its stated divergence | **Partial** | 1 critical, 2 high, 4 medium |
| 3 | Nothing under Deferred lets two units diverge within scope | **Fail** | 1 high, 1 medium |
| 4 | Ratifies rather than contradicts standing rulings | **Partial** | 2 high, 1 medium, 1 low (no outright contradiction found) |
| 5 | Every dimension the altitude owns is decided, deferred, or an open question | **Partial** | 1 high, 2 medium |
| 6 | Diagrams are valid mermaid and convey real rules | **Pass with reservation** | 1 medium |

---

## Findings register

### CRITICAL

**C-1 — AD-10 states a fingerprint recipe name but never states the recipe; the rule cannot prevent the divergence it claims to prevent.**
*Rubric 1, 2.* AD-10's stated prevention is "the same object hashing differently across machines." Its rule says: *"one canonical serialization (sorted fields, fixed encoding, display-only fields excluded), hashed with SHA-256, emitted as `fp1:sha256:…`"*. "Fixed encoding" is a promise, not a specification. Unspecified and load-bearing: the wire format (JSON / CBOR / length-prefixed binary), text normalization (UTF-8? NFC?), integer encoding for the scaled-integer money of AD-7 and the int64 ns of AD-8, how absent vs null fields are distinguished, how nested/collection ordering works, and how a field is *classified* as display-only. `docs/contracts/ct-05-version-fingerprint.yaml` names this exact hole as the open item ("Canonical bytes, hash algorithm, collision behavior, result-key fields, and deprecation rules remain unresolved") — the spine closes the hash algorithm and the collision behavior but leaves canonical bytes open, and does not list it under Deferred either, so it is silent rather than postponed.
The compounding problem: the spine never says the canonicalizer is a **single implementation in `qmf-core` that no other package may reimplement**. CT-05's `owner: COMP-QMF-CORE` says so; the spine does not. Two factory agents building `qmf-core` and `qmf-registry` against this text will each write a serializer, both will call the output `fp1:sha256:…`, both will pass their own tests, and the disagreement is silent — it corrupts identity and lineage rather than crashing.
*Fix (either is sufficient, both is better):* (a) add to AD-10 "the canonical serializer is one implementation in `qmf-core`; no other package may compute a fingerprint except by calling it" — this alone removes the divergence; (b) pin the `fp1` recipe concretely, or add an explicit Deferred row naming the sitting that pins it and forbidding any `fp1:` emission before then.

### HIGH

**H-1 — AD-3/AD-4 name canonical commands for tier 1 only; tiers 2 and 3 have no commands, and GAP-0003/GAP-0004 both asked for exactly that.**
*Rubric 1, 2.* GAP-0003 asks for "canonical local commands … for format-check, lint, type-check, unit, **integration**, and all". GAP-0004 asks "which **exact commands** gate each tier". AD-3 delivers `poe fmt | lint | types | test | check`; AD-4 describes tiers 2 and 3 in prose ("+ integration & contract tests"; "+ build all packages, clean-install smoke on both tier-1 OSes") with no command names. Every factory work unit runs these gates, so seven agents will mint seven names (`poe itest` vs `poe test-integration` vs `poe check2`) and tier-2 becomes un-runnable as a single gate.
Compounding: **"contract tests" is used without definition.** For seven independently-built packages this is the single most important shared concept — does each package ship conformance tests for the `CT-*` contracts it implements, who owns them, where do they live, and does a consumer package run the producer's suite? Undefined at exactly the altitude that owns it.
*Fix:* name `poe check` (t1), `poe check-integration` (t2), `poe check-release` (t3) or equivalent, and define "contract test" in one sentence with an ownership rule.

**H-2 — AD-2 mandates a shared `qmf.*` import namespace across seven distributions but states none of the mechanics that make that work.**
*Rubric 1, 2.* Seven separately installable distributions sharing one top-level `qmf` package requires PEP 420 implicit namespace packages, which requires that **no distribution ships `qmf/__init__.py`**. If one factory agent adds it to `qmf-core`, it shadows the namespace and the other six become unimportable — the classic independently-built-package failure, and the rule as written does not prevent it. Also unstated: `src/` layout vs flat (the Structural Seed shows `packages/qmf-core/` with no interior at all), the per-package `pyproject.toml` shape under `uv_build`, and whether each package declares `qmf-core` as a workspace dependency or a version-pinned one.
*Fix:* one clause in AD-2 — "`qmf.*` is a PEP 420 implicit namespace; no distribution may contain `qmf/__init__.py`; every package uses `src/` layout" — plus one canonical package skeleton in the Structural Seed.

**H-3 — Deferred row "Inter-library dependency edges beyond core … decided when each library's contracts are ratified" is a live divergence inside this sitting's scope.**
*Rubric 3.* AD-2 declares all seven packages exist **now** and the factory builds them from this spine. Under this Deferred row, an agent building `qmf-indicators` may add a dependency on `qmf-data` while an agent building `qmf-structure` assumes it may not; both are consistent with the text, both land in the same committed `uv.lock`, and the resulting graph is whatever landed first. The Dependency-direction rule reinforces the problem by calling the edges "intentionally undecided" — i.e. default-*unknown* rather than default-*deny*.
*Fix:* one word changes the safety property — "until an edge is ratified, no package may depend on any package other than `qmf-core`; adding an edge is a spine amendment." Cost zero, removes the divergence entirely, and preserves the deferral.

**H-4 — Two standing constitution laws that bind per-package construction are absent from the Inherited Invariants table and from every AD.**
*Rubric 4, 1.*
- **L27** — "Every factory-built QMF component must ship executable tests **and reference usage that demonstrates its public contract**." AD-3 mandates pytest and coverage; nothing anywhere mandates reference usage / runnable examples. This is a per-component deliverable the factory needs stated, and it is exactly the kind of thing that either appears in all seven packages or in none.
- **L6** — "QMF libraries must not ship mock market data, fake Bots, or default strategies as product artifacts; controlled test fixtures remain permitted." Silent in the spine. An agent building `qmf-data` will ship sample ticks by default. This also collides with AD-13: the benchmark harness needs load data at 10/40/100/200 units and the spine says nothing about what data a benchmark may use or whether it ships in the distribution (see also **L20**, synthetic data may stress infrastructure but must not validate edge).
The Inherited Invariants table lists 6 rulings; the constitution carries 29 laws, of which at least L5, L6, L16, L20 and L27 bind this sitting. The table is a partial list presented as the binding set.
*Fix:* add L6/L20 and L27 rows to Inherited Invariants and give L27 an enforcement home in AD-3 (reference usage is a tier-1 artifact) and L6 a prohibition line in AD-13's benchmark rule.

**H-5 — AD-2 and AD-5 disagree about how calendar extensions are versioned, and AD-8 makes the answer load-bearing.**
*Rubric 2, 5.* AD-2: "Calendar extensions are separate **versioned** packages outside the roster." AD-5: "code packages use SemVer **in lockstep**." Is a calendar extension a code package? If yes, it is lockstepped to the framework — and since AD-8 puts "the calendar + tzdata version" into every derived artifact's fingerprint, every unrelated framework release would churn the fingerprint of every calendar-derived artifact. If no, its ladder is undefined and nothing says how a tzdata bump maps to a version bump. Neither AD resolves it, and this is the one place where a versioning ambiguity propagates directly into identity.
*Fix:* state explicitly that extensions carry their own SemVer ladder outside lockstep, and that a tzdata pin change is at minimum a minor bump of the extension.

**H-6 — AD-8 drops the DevOps audit's replay/live isolation blocker, which is a foundation invariant, not a data-sitting detail.**
*Rubric 1, 3.* `time-audit-devops.md` ("Sandbox/replay clocks (blockers)") states: *"Every persisted record carries non-nullable time_domain (live | replay | simulated) participating in identity; **replay may never write into the live evidence namespace**"* and *"Factory sandboxes forbidden from producing timestamps that enter the evidence store."* The spine carries the world/time-domain field into AD-12's result label ✓ but carries **neither prohibition**. The write-isolation rule is cheap, framework-level, and directly relevant to factory agents running in disposable sandboxes today — it is the rule that stops a sandbox run from polluting real evidence. Leaving it to the data sitting means it is unstated during the exact window when sandboxes are being built.
*Fix:* one bullet in AD-12 or AD-14 — "a non-live world may never write into the live evidence namespace; factory sandboxes never produce timestamps that enter an evidence store."

**H-7 — AD-5 silently drops the deprecation window the operator ratified in the memlog, and GAP-0005 explicitly asked for it.**
*Rubric 4, 1.* Memlog GAP-0005 ruling: *"deprecations keep working with warning for one release."* GAP-0005's question: *"What release, semantic-versioning, **deprecation**, and compatibility policy applies…"* AD-5 as written covers SemVer, format versions, and append-only history — and contains no deprecation policy at all. A ratified operator ruling was lost in transcription, and the gap is therefore not actually closed.
*Fix:* restore the clause verbatim into AD-5.

### MEDIUM

**M-1 — int64-ns overflow and checked arithmetic are unstated, though both audits flagged them.**
*Rubric 1, 2.* Architect audit #17 ("int64 ns range 1677–2262 — state once"), DevOps audit ("int64-ns overflow 2262; **checked arithmetic** on ns math"). AD-8 defines Duration as signed int64 ns and Interval arithmetic over it but never says what happens on overflow — saturate, wrap, or refuse. Independently-built packages will answer differently and silently (pure-Python ints do not overflow; a numpy-backed series does). Given AD-11 exists, the answer is nearly free: overflow is a typed refusal.
*Fix:* add to AD-8 — "representable range 1677–2262 stated once; all ns arithmetic is checked; overflow is an `invalid input` typed refusal, never a wrap."

**M-2 — AD-14's stated prevention is not achieved by its rule.**
*Rubric 2.* AD-14 prevents "multi-hour what-broke hunts" via "structured logging with correlation IDs so one event can be followed across components" and "every component exposes a cheap health self-check." Neither is specified: no correlation-ID field name, no propagation mechanism across a package boundary, no log record shape, no health-check signature. Seven independently-built packages will emit seven log schemas with seven ID field names, and correlation — the entire point — will not work. The Deferred row ("Full observability/monitoring design → data/ops sitting") covers the monitoring *design* but the minimum interoperable shape has to be fixed now or the packages are already incompatible when the data sitting arrives.
*Fix:* fix the two smallest things that make it composable — the correlation-ID field name and the health-check callable signature — and defer everything else.

**M-3 — AD-13's regression gate has no threshold, and its load units do not exist in the framework.**
*Rubric 2, 5.* (a) "thereafter **significant** regressions fail the merge gate" — "significant" is undefined, and the Deferred row only defers *numeric performance budgets*, not the regression threshold. Two agents will pick 5% and 50%. The operator's "no invented numbers" ruling constrains *budgets*, not the *method parameter*, so this can be decided now (e.g. "the threshold is stated per benchmark when its baseline is recorded"). (b) "run at multiple load sizes (10/40/100/200 **bots**)" — QMF contains no bots; L7 and L16 say QMF is not an application and `qmf-core` must not assume a deployment environment. Each package's agent must translate "40 bots" into its own load unit, and each will translate differently.
*Fix:* state where the threshold is fixed, and restate the load ladder in framework-native units per package (calls/s, series length, artifact count) with the bot ladder as the node-side reference scenario that motivated it.

**M-4 — The operational / environmental envelope is seeded but has no named owning sitting.**
*Rubric 5.* The spine does address the envelope — the Structural Seed paragraph covers workstation/VPS/sandbox topology, AD-1 covers the runtime matrix, AD-4 covers pipeline events, AD-8's last bullet delegates ~57 operational clock rules, AD-14 covers the observability obligation — so this is **not** a whole-dimension silence. But the seed defers it to "later sittings" (plural, unnamed), and the Deferred table has a row for observability/monitoring and none for deployment topology, infra strategy, or operations as a whole. An unnamed owner is how a dimension falls through. Also unratified-but-mentioned: "nightly object-storage backup **proposed but not yet ratified**" sits in a seed paragraph rather than as an open question.
*Fix:* add one Deferred row — "Deployment topology, infra strategy, operations envelope → node/ops sitting" — and move the backup line into it as an open question.

**M-5 — AD-8 binds a large body of rules by pointer to a sitting-local scratch file while declaring `companions: []`.**
*Rubric 4, 5.* AD-8's final bullet makes the DevOps operational clock rules "stated obligations … **recorded in `time-audit-devops.md`**, binding on later sittings." That file lives in `_bmad-output/planning-artifacts/…`, not in the `docs/` corpus, and the frontmatter declares `companions: []`. When `/documentation-factory` runs against `docs/`, the binding target may not travel with the spine, and a binding obligation with no durable referent is not binding.
*Fix:* promote `time-audit-devops.md` (and `time-audit-architect.md`, `ctrader-time-research.md`) to declared `companions:` so they are carried, or restate the ~12 binding operational rules inline.

**M-6 — AD-3's coverage rule is ambiguous in two ways that matter to a gate.**
*Rubric 2.* "Coverage measured on every change, floor 80%" — per package or workspace-aggregate? (Aggregate lets a thin package hide behind a thick one.) Enforced at which tier, or measured only? "money/time exact-arithmetic primitives require **full coverage**" — line or branch, and *which modules qualify*? An agent can scope "exact-arithmetic primitives" as narrowly as it likes and still pass.
*Fix:* "per package, enforced at tier 1; branch coverage 100% on the modules implementing CT-01 and CT-02 primitives."

**M-7 — Three version-ish fields are introduced across AD-5, AD-10 and AD-12 without a disambiguation.**
*Rubric 2.* AD-5: "its own integer **format version** stamped into every artifact". AD-10: fingerprint recipe prefix `fp1`. AD-12: "**producer contract version**" in the result label. The Consistency Conventions row implies format version and result label are distinct fields on the same artifact, but nothing says whether AD-5's format version and AD-12's producer contract version are the same number under two names. A factory agent will guess, and half will guess wrong.
*Fix:* one line naming the three fields and their relationship.

**M-8 — Rubric 6: the diagram is valid but low-yield, and it is the only one.**
*Rubric 6.* The single `graph TD` block parses — node/edge syntax is well-formed, the dotted-labelled link `-. implement core protocols .->` is valid, re-listing `VEN`/`RISK` inside the subgraph to place them is supported mermaid, and no reserved identifier (`end`, leading `o`/`x`) is used. But it conveys one rule (everything depends on core) that the adjacent sentence already states, and the more interesting rule — "nothing imports `qmf-venue` or `qmf-risk`" — is carried by a **subgraph title**, i.e. prose inside a box, not by anything structural. It also does not show the live risk (the undecided inter-library edges of H-3) or the seam that most needs a picture: AD-8's clock injection — protocol in core, real clock injected at the composition root, replay clock injected from the data cursor, nothing below the root touching the system clock. That is a rule a diagram would genuinely enforce in a reader's head.
*Fix:* keep the dependency graph but add the clock-injection seam diagram, and render the "nothing imports these" prohibition as a struck/absent edge rather than a caption.

### LOW

**L-1 — Provenance slip in the Inherited Invariants table.** The "Build-our-own" row cites "kernel ruling 2026-08-17, **DEC-0085**". DEC-0085 is a *dead* decision (Nautilus contract adoption, rejected) — a tombstone, not the source of the invariant. The live sources are DEC-0013 (build-own boundary) and DEC-0014 (dead: strategy-family libraries), with DEC-0085/DEC-0086 as tombstones. Cite the live decision and list the tombstones as such.

**L-2 — AD-8 states a research finding slightly harder than the memlog allows.** "17:00 America/New_York rollover (**verified** = cTrader's own boundary)". `ctrader-time-research.md` marks this "UNVERIFIED: rule not stated in Open-API-specific primary docs, only platform-general threads", and the memlog records "findings presented not auto-adopted — venue sitting ratifies." The ratified fact (the forex calendar rolls at 17:00 NY) is unaffected; only the corroboration is over-claimed. Soften to "corroborated by cTrader's documented platform boundary (venue sitting verifies)".

---

## Detailed analysis

### 1. Coverage of the declared scope (GAP-0001..0013)

Every in-scope gap has a matching AD, and the mapping is clean:

| Gap | AD | Coverage |
|---|---|---|
| GAP-0001 runtime matrix | AD-1 | Complete — CPython 3.14 pinned, Win11 + Ubuntu LTS x86-64 tier 1, pure-Python portability stated |
| GAP-0002 layout / namespace / build / lock | AD-2 | Complete at the workspace level; **incomplete at the package level — H-2** |
| GAP-0003 toolchain / coverage / commands | AD-3 | Tools complete; **commands incomplete — H-1**; **coverage scope ambiguous — M-6**; **L27 reference usage missing — H-4** |
| GAP-0004 CI tiers | AD-4 | Tier events complete and correctly de-coupled from PR mechanics; **exact commands missing — H-1** |
| GAP-0005 release / SemVer / deprecation / compatibility | AD-5 | Two ladders + append-only history complete; **deprecation window dropped — H-7**; **extension ladder undefined — H-5** |
| GAP-0006 dependency + licence tiers | AD-6 | Complete. Minor: the dependency register's location is unnamed, so seven agents will invent seven registers |
| GAP-0007 exact money | AD-7 | Complete. Rounding mode is correctly left as "must be explicitly stated at a named boundary" rather than pre-guessed |
| GAP-0008 exact time | AD-8 | **Strongest section.** All nine architect amendments present (calendar protocol + out-of-roster extension, Duration/Interval half-open, monotonic-protocol-only, sequence ordering, calendar+tzdb in fingerprints, POSIX/no-leap-second, swap-Wednesday dropped, holidays in scope, venue-parameterized rollover incl. 24/7). Gaps: **overflow/checked arithmetic — M-1**; **replay write-isolation — H-6**; **binding-by-pointer — M-5** |
| GAP-0009 instrument + account identity | AD-9 | Complete, and the Account-as-first-class-noun addition genuinely closes the ~6-broker / specialization direction from the memlog |
| GAP-0010 fingerprints | AD-10 | **Incomplete — C-1.** Hash algorithm, versioned prefix, collision policy all decided; canonical bytes and single-implementation ownership are not |
| GAP-0011 typed refusals | AD-11 | Complete — six categories, machine-readable context, retryability, addable-never-redefined |
| GAP-0012 result label | AD-12 | Complete — five parts, identity semantics, display names excluded, world label carries the parked sim-time decision without committing to backtest design |
| GAP-0013 performance budgets | AD-13 | Method complete and correctly refuses invented numbers; **regression threshold and load units — M-3** |

No in-scope gap is unaddressed. The failures are specificity failures, not omissions of subject.

### 2. Enforceability

Enforceable as written, and would stop a factory agent: AD-1, AD-2 (workspace level), AD-5 (format-version half), AD-6, AD-7, AD-9, AD-11, AD-12.

Not enforceable as written: **AD-10** (no recipe — C-1), **AD-14** (no field names — M-2), **AD-13** (no threshold, wrong units — M-3), **AD-3** (coverage scope — M-6), **AD-4** (no tier-2/3 commands, "contract test" undefined — H-1).

The pattern worth naming: the ADs that fail are the ones whose Rule names a *property* ("fixed encoding", "correlation IDs", "significant regressions", "full coverage") without naming the *artifact that carries it*. Every remediation above is of the same shape — name the field, the command, the file, or the single owning implementation.

### 3. Deferred safety

Ten of the twelve Deferred rows are safe: they defer whole subject areas that this sitting's packages cannot begin without (registry, data, indicators, venue, risk, backtesting, crypto, news auto-sync, SR*). Two are not:

- **Inter-library dependency edges (H-3)** — deferred as *undecided* rather than *default-denied*, inside a sitting that has already declared all seven packages exist.
- **Full observability design (M-2)** — the deferral is right, but AD-14's binding obligation is too thin to keep the seven packages composable until the data/ops sitting lands.

One item is neither decided nor deferred and therefore silent rather than safe: the `fp1` canonical-bytes recipe (C-1), and the regression-significance threshold (M-3).

### 4. Ratification vs contradiction

**No outright contradiction of a live ruling was found.** Checks performed:

- L7/L8/L13 (QMF is not an application; definitions-only core) — the paradigm statement ratifies both explicitly ✓
- L14 / DEC-0024 (five libraries + two modules) — AD-2's seven packages is the same roster, and the calendar-extension carve-out is stated rather than smuggled ✓
- L9 / DEC-0011 (don't box in) — AD-6/8/9 neutrality rules ✓. *Reservation:* AD-3's workspace-wide pyright-strict and 80% floor could be read as contradicting "strictness only at harness and live-money gate". The correct reading is that DEC-0011 governs *consumers of QMF*, not QMF's own source, but the spine never says so, and that boundary is exactly what an agent needs when deciding whether to enforce strict typing on reference/example code. One clarifying sentence would close it.
- DEC-0015 (no futures/options; nouns must not preclude stocks/crypto) — AD-9's opaque symbol and separate asset-class records ✓; AD-8's "every calendar supplies a rollover rule (24/7 included)" ✓
- DEC-0023 / DEC-0020 / DEC-0062 (dead terminology: kernel, minimal core, exam) — Consistency Conventions bans all of them plus "engine" and "plugins" ✓
- L15 / L28 (versioned from first release; evolve by extension not replacement) — AD-5, AD-10 prefix minting, AD-11 addable categories ✓
- L3 / L29 (studies are evidence, not contracts) — the Stack table correctly labels duckdb/TA-Lib "candidates pending" and the Deferred table keeps Parquet/DuckDB/SQLite/JSONL as candidates ✓
- Live conflicts DEC-0040 and DEC-0067 — both out of scope (registry / risk), correctly untouched ✓

**What fails is completeness of the Inherited table, not fidelity:** L6, L20 and L27 bind this sitting and appear nowhere (H-4); L16 is ratified in spirit by the paradigm but violated in letter by AD-13's bot-shaped load units (M-3); L5 (legibility to humans and agents) has no convention anywhere in the spine.

### 5. Dimensional completeness at initiative altitude

Decided: runtime matrix, repo/package topology, toolchain, pipeline gating, versioning, dependency/licence policy, money, time, identity, fingerprints, error model, result identity, performance method, observability obligation, dependency direction, naming, stack pins, structural seed.

Deferred with a named home: registry, data, indicators/structure, venue, risk, backtesting, crypto, news auto-sync, monitoring design, numeric budgets, inter-library edges.

**Thin or unowned:** the operational/environmental envelope (M-4) — present as a seed paragraph and two delegations, but with no named owning sitting and no Deferred row, and with an unratified backup proposal parked in prose. **Absent entirely:** a Python-level public-API convention (are public types frozen dataclasses, `Protocol`s, `NamedTuple`s?) — arguably below initiative altitude, but with seven packages built independently against `pyright strict`, it is the next thing after H-2 that will produce seven dialects. Worth one line, not an AD.

Security/secrets is correctly out of scope (GAP-0035, venue sitting) and is not counted as a finding.

### 6. Diagrams

One diagram. It parses (see M-8 for the syntax review) and its direction convention is right — arrows read as "depends on", pointing inward at the zero-dep hub, matching the hexagonal paradigm. The dotted protocol edge from calendar extensions is the correct way to show an out-of-roster implementor.

The reservation is informational yield, not validity: the diagram restates one sentence, encodes its second rule as a caption, omits the undecided edges that are the live hazard, and there is no diagram for the clock-injection seam — the one rule in this spine that is genuinely hard to hold in prose and easy to violate in code.

---

## What the spine gets right (so remediation does not overcorrect)

- The **time section is exemplary**: it absorbed all nine amendments from an adversarial two-lens audit without diluting any of them, correctly separated framework contract from node obligation, and parked sim-time typing to the backtesting sitting while still capturing the one thing that could not wait (the world label in AD-12).
- **AD-4's reframing of CI tiers as events rather than GitHub PR mechanics** is the right altitude and correctly survives the "no remote yet" reality.
- **AD-13's refusal to invent performance numbers**, while still binding a method and one concrete commitment (core imports well under 1s), is the correct way to close a gap whose evidence does not exist yet.
- **AD-9's promotion of Account to a first-class noun** genuinely absorbs the ~6-broker/specialization direction without adding framework machinery.
- **Scope discipline is good**: registry/data/indicator/venue/risk detail stays out, and the Deferred table names where each lands.
