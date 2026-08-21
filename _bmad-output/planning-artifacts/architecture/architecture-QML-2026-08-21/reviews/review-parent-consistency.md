# QML Spine — Finalize-gate Review

**Lens: Parent / Sibling Consistency**
Artifact: `architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md` (QL-1..QL-10)
Binding law: QMF `architecture-QMX-2026-08-19` (AD-1..AD-41, Dependency direction, framework-vs-node split); QMB `architecture-QMB-2026-08-20` (B-1..B-15).
Job of this lens: verify no QL rule contradicts, weakens, or **silently** amends an inherited invariant; every parent/sibling touchpoint classified, and anything that amends a parent or requires a sibling change surfaced as such.

---

## Verdict

The QML spine is, on the whole, an unusually disciplined thin-consumer child: it re-bases the old QML's uniformity rationale onto ratified QMF law, refuses to revive a second contract layer, and correctly routes versioning through `branches-from` (QL-3 vs AD-16/AD-30), close reasons through CT-29's one taxonomy (QL-9 vs AD-33), family keying through the exact loci the parent already reaches for (QL-6 vs AD-33/AD-40/AD-41/AD-35), and derived warm-up through AD-21/B-2 with no second window (QL-4). No hard contradiction of a binding invariant survives review. However, **two touchpoints amend or lean on parent/sibling contracts without declaring the change as such** — the CT-22 `evidence_requirements` field additions (QL-8) and the R-authoring path on the entry intent (QL-7) — and **four more require sibling (QMB) changes that the spine asserts are free** (canonical-assignment check on B-4, producer-template resolution on B-3, the unit-kinded parameter schema shared with B-8, and the CT-33→CT-23 reference that must not induce a forbidden roster edge). None is fatal; each is a place where an implementer, reading the spine literally, would either weaken an invariant or discover an undeclared dependency. A batch of stale internal QL cross-references (draft numbering that leaked past the renumber) rounds out the set.

---

## Touchpoint walk (classification)

| QL | Touchpoint | Binding law | Class |
| --- | --- | --- | --- |
| QL-1 | QML imports qmf-core/registry/risk, never venue; default-deny "governs roster packages, not applications" | Dependency direction (default-deny); QMB precedent (B-3/B-6 consume qmf-risk) | **consistent** (matches ratified QMB precedent; reasoning made explicit) |
| QL-1 | QML pure per AD-15; registration writes + sandbox ride composition roots (AD-28) | AD-15, AD-28 | **consistent** (impure parts host-side) |
| QL-2 | logic distribution identity+version+content-fp are Bot identity fields; code change mints a new Bot | AD-2 (extension identity), AD-17 (identity is content), AD-30 (changed number = new identity) | **tightens-legally** |
| QL-3 | Bot kind CT-33 fills reserved kind, owned by qmf-registry, contents from this sitting | AD-16 ("Bot kind's contents come from its own sitting") | **consistent** |
| QL-3 | versioning = `branches-from`, multiple heads, current = dated pointer | AD-16 (supersedes linear), AD-30 (branches-from) | **consistent** |
| QL-3 | canonical-assignment law; governed seats run defaults only; overrides = B-3 run-spec | B-3 (run spec is the bot layer) | **consistent** |
| QL-3 | "checkable from the resolved run-config … no amendment to B-4" | B-4 (reader-derived fold) | **requires-sibling-change** (F3) |
| QL-3 | parameter space "verbatim B-8's schema … with a unit-kind on every parameter" | B-8; AD-40 | **requires-sibling-coordination** (F4) |
| QL-4 | producer templates resolve to a concrete CT-16 fp at compile/seat-admission | AD-22 (identity = whole config) | **consistent** (resolution step, not a second identity path) |
| QL-4 | warm-up/embargo derived at resolution, no second window | AD-21, B-2 | **consistent** |
| QL-4 | template resolution happens "at run-config compile or seat admission" | B-3 config compiler | **requires-sibling-change** (F6) |
| QL-5 | leg-role vocab `level\|trigger\|confirmation\|filter`; `filter` freshly minted | AD-17 (level/trigger/confirmation) | **tightens-legally / declared** (filter provenance-marked); one wording reading (F8) |
| QL-6 | strategy family = key, no authority; keys AD-33/AD-40/AD-41/AD-35 loci | AD-33, AD-40, AD-41, AD-35 | **consistent** |
| QL-6 | "exactly one family id per bot" | AD-17 (no hardcoded exactly-one except declared) | **tightens** but unflagged cardinality-one (F8) |
| QL-7 | bot never sizes / no clock / deterministic | AD-33, AD-8, B-2 | **consistent / tightens** |
| QL-7 | full-loss price on entry intent derived by bot via Book ExitLogicRef, Book recompute+verify | AD-33 (R single-authored; bot names a bound never a price), AD-40 | **consistent-in-outcome but underspecified** (F1) |
| QL-8 | prediction linter checks (a)-(d) | AD-32 Layer-1 pending slot | **consistent** |
| QL-8 | `evidence_requirements` gains two bot-side fields | AD-32 field list; CT-22; AD-5/AD-30 | **AMENDS-PARENT, not declared as a CT-22 mint** (F2) |
| QL-8 | registration writes / conformance sandbox ride platform/QMB roots | AD-28, B-5, B-15 | **consistent** |
| QL-9 | close-reason mapping onto CT-29 taxonomy; no exit_logic on the bot | AD-33 vocabulary (verified member-by-member) | **consistent** |
| QL-9 | closes AD-33 provenance flag, ratifies donor atoms as-is | AD-33 ("open to revision by the QML sitting") | **consistent** (QML exercising delegated authority) |
| QL-10 | QML before node; consumes QMF contracts only; node hosts seats | framework-vs-node split | **consistent** |
| CT-33 | references CT-23 intent kinds (permitted-intent) from within a qmf-registry kind | Dependency direction (no qmf-registry→qmf-risk edge) | **edge-risk if mis-implemented** (F5) |

---

## Findings (most severe first)

### F1 — HIGH — QL-7 entry-intent derivation: bot runs the Book's exit logic and puts a full-loss price on the intent; outcome-safe but underspecified in ways that can silently give the bot R-authority

**What the spine says.** QL-7: "the declared full-loss price on a CT-23 entry intent is derived **at intent mint** by executing the Book-declared family `ExitLogicRef` … consuming the bot's advisory stop proposal and cited evidence); the Book door deterministically **recomputes and verifies** at admission — a mismatch is an `invalid input` refusal — so the intent carries the field CT-23 names while R stays single-authored by the Book's declaration."

**Binding law.** AD-33 puts "the declared full-loss price (AD-40)" and "an advisory `proposed_r`" on the CT-23 entry intent, and is emphatic for the exit side: a `tighten_protective_stop` "names a **direction and a bound, never a price**; the Book's policy resolves the level, which is what keeps R single-authored." AD-40: "**how** the price is derived is a per-family declaration through `ExitLogicRef`"; "The envelope's `requested_r` is the **Book-resolved** value, never the bot's."

**Assessment.** Because the Book recomputes the same `ExitLogicRef` and refuses on mismatch, the bot cannot inject a price the Book would not itself compute — so in **outcome** R stays Book-authored, and delegation to a bot's proposal (where a Book so declares) is explicitly allowed by AD-33. This is not a flat contradiction. But the construction has four unaddressed gaps, each of which lets an implementer weaken the invariant or diverge:

- (a) **The recompute+verify is the load-bearing guarantee and is stated once, in passing.** An implementer who wires the bot to author the full-loss price but omits/mis-scopes the Book recompute has silently given the bot R-authority — exactly what AD-33 exists to prevent. The mandatory, refuse-on-mismatch recompute needs to be pinned as contract surface, not narrative.
- (b) **The bot must be handed the resolved Book `ExitLogicRef` at construction**, yet QL-7 also says the bot receives "only the declared footprint's evidence," "never performs I/O," and runs in QL-8's isolated sandbox. Executing the Book's exit module at intent-mint requires the host to inject that module+config into the factory — an injected surface the spine never lists among the factory's constructor inputs.
- (c) **Cross-site determinism** (bot-mint execution vs Book-door recompute, over identically-cited evidence) is a stronger obligation than single-site derivation and is not declared as a versioned contract requirement; a benign nondeterminism in the ExitLogicRef turns every entry into an `invalid input` refusal.
- (d) **Governed vs ungoverned split is undefined.** Conformant bots on governed seats derive-via-ExitLogicRef; but plain-Python (non-conformant) bots also mint CT-23 entry intents in QMB from day one (QL-10) and need an AD-40 full-loss price. For them there is no QL-7 conformance and no bot-side ExitLogicRef execution — so either they self-declare the price (fine, because their evidence is ungoverned per QL-8) or an implementer wrongly forces the derive path onto plain Python and breaks QL-1's "zero qml imports." The spine states neither.

**Fix.** Preferred: make the entry side **symmetric with the exit side** — the bot supplies only an **advisory stop proposal** (like `proposed_r`), and the **Book derives the full-loss price at admission** by executing its own per-family `ExitLogicRef`; the intent then carries a Book-authored price, single-sited, and no Book exit module is ever injected into the bot. This directly honors AD-33's "bot names a bound, never a price" and removes (b)/(c) entirely. If bot-mint-time derivation is retained, add an explicit clause pinning: (a) the Book recompute+verify is mandatory and grants the bot no authority beyond what the Book independently reproduces; (b) the resolved Book `ExitLogicRef` is a named injected surface in the factory constructor; (c) cross-site determinism is versioned contract surface; (d) the ungoverned path (plain-Python bot self-declares a full-loss price → ungoverned evidence only, per QL-8), so QL-1's zero-import promise is not broken.

### F2 — HIGH — QL-8 adds two fields to CT-22's `evidence_requirements` but does not declare it as a parent-contract (CT-22) format-version mint

**What the spine says.** QL-8: "AD-32's `evidence_requirements` vocabulary gains two bot-side declarable fields — a **registered-conformant-Bot cite** … and **canonical-assignment evidence**."

**Binding law.** AD-32 fixes the `evidence_requirements` field list as "world, account role, minimum evidence window, and the producer contract format versions the measurement must carry" — a closed list, not declared addable (unlike the close-reason and unit-kind vocabularies, which AD-33/AD-40 explicitly mark "addable never redefined"). `evidence_requirements` is part of CT-22's `admission_bar` section (a qmf-risk, parent-owned contract). AD-5: an incompatible change to a serialized contract "mints the next version plus a migration note"; AD-30: "A further section is a contract-format-version mint."

**Assessment.** Adding two fields to a parent-owned contract's shape is an **AMENDS-PARENT** touchpoint. The lens's rule is that such a change must be surfaced as a proposed parent-contract change, never silently absorbed. QL-8 does *name* the addition (so it is not fully silent), but it frames it as the vocabulary "gaining fields" rather than as a CT-22 `admission_bar` format-version increment — and it conflates it with the AD-30 `pending` slots. Those slots (`footprint_requirements`, the prediction linter) were **reserved** by AD-30/AD-32 for the Bot sitting; these two `evidence_requirements` fields are **not** among the reserved slots — they are net-new admission-bar surface. Left as written, the doc-factory may treat CT-22 as unchanged, and an implementer may add the fields under the old format version, defeating AD-5's read-old-evidence-forever guarantee.

**Fix.** Declare the two fields explicitly as a **CT-22 `admission_bar` format-version mint under AD-5** (proposed parent-contract change, carried by the documentation-factory increment against qmf-risk), distinct from the AD-30 pending slots. State that they are technical qualifiers (consistent with AD-32's technical-not-performance law and "no paper role gates live money"), and that pre-mint bars remain readable.

### F3 — MEDIUM — QL-3's "no amendment to B-4" understates the QMB change the canonical-assignment check requires

**What the spine says.** QL-3: a run whose resolved values differ from the canonical assignment "can satisfy no admission-bar requirement that declares canonical-assignment evidence …, **checkable from the resolved run-config with no amendment to B-4**." QL-8 makes "canonical-assignment evidence" an `evidence_requirements` field.

**Binding law.** B-4: the bar verdict is a "reader-derived" fold computing "per-requirement outcomes against the cited AD-32 bar (structural parity on producer contract versions, unit-kind, comparison rule)"; the ledger line carries "the CT-32 fingerprint, the run's raw … measures, the fingerprint of the Book bar AS RESOLVED, and a discriminated run role" — **not** the resolved bot-layer parameter values. B-3: the ledger key is the run-config fingerprint.

**Assessment.** The claim is half-right: no ledger *schema* field is strictly required, because the run-config is fingerprint-addressable. But to evaluate the new requirement the B-4 fold must (i) recognise a **new evidence qualifier kind** (equality-to-canonical, not a threshold comparison) and (ii) obtain the run's **resolved bot-layer assignment** — which is not on the ledger line, so the fold must dereference the run-config artifact or a new stamp must record it. Asserting "no amendment to B-4" invites QMB to skip the work and discover the gap at implementation.

**Fix.** Declare this as a **composed extension**: add a B-3 stamp recording whether a run used the canonical assignment (mirroring B-3's existing `seed_overridden` precedent — e.g. `assignment_is_canonical` or the resolved-assignment fingerprint), and state that B-4's fold gains a canonical-assignment qualifier that reads it. Frame it as "composes with B-4 via a new stamp + qualifier," not "no change."

### F4 — MEDIUM — "verbatim B-8's schema … with a unit-kind on every parameter" risks two divergent parameter-space schemas

**What the spine says.** QL-3: the declared parameter space is "**verbatim B-8's schema** — name, type ∈ …, bounds, step, **mandatory default**, optional hard constraint filters — **with a unit-kind on every parameter** (AD-40)."

**Binding law.** B-8's schema (as written in the QMB spine) is "name, type ∈ …, bounds, step, default plus optional hard constraint filters" — **no unit-kind**. AD-40 requires every declared variable to carry a unit-kind (null is a refusal).

**Assessment.** "Verbatim … plus a field" is self-contradictory. B-8's optimizer and CT-33's Bot definition must consume **one** parameter-space schema; if CT-33 carries unit-kinds and B-8's schema does not, an implementer can end up with two schemas and the shared-schema comparability B-8/QL-3 both rely on breaks. (AD-40 already binds B-8, so B-8's spine text is arguably the incomplete one.)

**Fix.** Declare CT-33's parameter space as the **one authoritative bot parameter-space contract**, AD-40-complete (unit-kind on every parameter), which B-8's optimizer consumes — i.e., B-8's schema is *completed* with unit-kinds, not duplicated. Drop "verbatim" or qualify it ("B-8's schema, completed with the AD-40 unit-kind every declared variable already requires").

### F5 — MEDIUM — CT-33/CT-34 referencing CT-23 (and CT-16/CT-17) must not induce a forbidden roster-internal edge

**What the spine says.** CT-33 is "a qmf-registry per-kind contract … owned by qmf-registry," and its content includes "the permitted-intent declaration — which CT-23 intent kinds the logic may mint." QL-8 Layer-1 validates "permitted-intent kinds within the ratified CT-23 vocabulary."

**Binding law.** Dependency direction (default-deny): "nothing imports `qmf-venue` or `qmf-risk`. Until an inter-library edge is ratified, no package may depend on any package other than `qmf-core`; adding an edge is a spine amendment." CT-23 is a qmf-risk contract (minted in AD-33).

**Assessment.** If an implementer types CT-33's permitted-intent field as a **qmf-risk enum**, `qmf-registry → qmf-risk` appears — a roster-internal edge the default-deny rule bars without a QMF spine amendment. The spine's design clearly intends the validation to live in **QML** (which legally imports qmf-risk) while qmf-registry stores the record — but it never states the constraint that makes this legal, so the edge can be introduced by accident.

**Fix.** State explicitly (mirroring AD-22's "declaring an input creates no package dependency edge" and AD-31's join-by-fingerprint pattern) that CT-33/CT-34 store CT-23 intent-kind identifiers, producer formula ids, and confluence/producer fingerprints as **opaque qmf-core-typed values**, validated by **QML-side linters**, so qmf-registry gains no new roster edge. Otherwise the addition would be an unratified inter-library edge (a QMF spine amendment).

### F6 — MEDIUM — QL-4 producer-template resolution is an unstated extension to QMB's B-3 config compiler (and the node seat-admission path)

**What the spine says.** QL-4: a producer template is "resolved to a concrete configured-producer fingerprint **at run-config compile or seat admission**," mapping named bot-space parameters into the producer configuration.

**Binding law.** B-3 owns the config compiler ("compiled from explicit layers with fixed precedence"); B-8 resolves sampled parameter *values* via named AD-7/AD-22 conversions. Neither currently **instantiates a producer configuration from a template** and fingerprints the resulting CT-16/CT-17 config.

**Assessment.** Template resolution (take resolved bot-space params → build the CT-16/CT-17 configured-producer → fingerprint) is a new responsibility the compiler must gain; "run-config compile" is B-3's job and "seat admission" is the node's. The spine composes with B-3 but does not name the new compiler step, so QMB may not budget for it.

**Fix.** Declare producer-template resolution as a **B-3 config-compiler extension** (and a node seat-admission responsibility), composing with B-8's value resolution: resolved bot-space params feed producer-config construction, whose CT-16/CT-17 fingerprint enters run identity (AD-22) — exactly as QL-4 already promises for dedup.

### F7 — MEDIUM — Stale internal QL cross-references (draft numbering leaked past the renumber)

The spine renumbered the draft rules (draft QL-3b→QL-4, draft QL-4..QL-9→final QL-5..QL-10), but eight cross-references still point at the old numbers, sending a reader/implementer to the wrong rule:

| Location | Reads | Should read |
| --- | --- | --- |
| Inherited table, AD-32 row (l.33) | bot-side fields "(QL-7)" | QL-8 |
| Inherited table, AD-33 row (l.34) | "QL-8 ratifies the donor atoms" | QL-9 |
| Inherited table, AD-40 row (l.35) | "entry-intent derivation (QL-6)" | QL-7 |
| Inherited table, QMB row (l.39) | "QL-7's ticket honors it" | QL-8 |
| QL-1 (l.49) | "runtime protocol (QL-6); … conformance gate (QL-7)" | QL-7; QL-8 |
| QL-2 (l.55) | "the QL-6 runtime protocol" | QL-7 |
| QL-3 (l.63) | "the strategy-family id (QL-5)" | QL-6 |
| QL-3 (l.71) | "canonical-assignment evidence (QL-7)" | QL-8 |

(For contrast, the Structural Seed comments, QL-5's "producer binding per QL-4", QL-6's "prediction linter (QL-8)", and QL-10's "QL-7 seats" already use correct final numbering — so the errors are localized, not wholesale.)

**Fix.** Renumber the eight references above to final numbering. The most consequential are l.34 ("QL-8 ratifies the donor atoms" → QL-9) and the QL-1 self-description (l.49), because they misname the two rules the whole surface hangs on.

### F8 — LOW — Two AD-17 wording reinterpretations left implicit

- **"Exactly one family id per bot" (QL-6)** is a deliberate cardinality-one in the bot vocabulary. AD-17 bars hardcoded exactly-one "anywhere in the bot vocabulary," and AD-29 handles this by explicitly marking each cardinality-one "a deliberate ruling under AD-17, not an assumption." QL-6 does not flag it, so it reads as the hardcoded exactly-one AD-17 forbids.
- **Confluence "one-or-more legs" of any role (QL-5)** silently resolves AD-17's ambiguous "a confluence contains one-or-more levels, triggers, **and** confirmations." QL-5 permits a confluence lacking a given role (e.g. trigger-only). This is the multiplicity-faithful reading (mandating one of each would itself be a foreclosing cardinality AD-17 exists to prevent), and `filter`'s addition to AD-17's enumerated set is already provenance-marked — but the relaxation from "one of each" to "≥1 of any" is not called out.

**Fix.** Add one clause each: mark one-family-per-bot as a deliberate AD-17 cardinality-one ruling (AD-29's pattern); and state that a confluence requires ≥1 leg of any role (not one of each), with `filter` extending AD-17's enumerated role set — confirming the intended reading rather than leaving it inferred.

---

## Confirmed-consistent (no action; recorded so the gate can see they were checked)

- **QL-3 versioning** vs AD-16 (supersedes linear) + AD-30 (branches-from, multiple heads, current = dated pointer): correct — Bot uses `branches-from`, `continues-performance` human-signed.
- **QL-9 close-reason mapping** vs AD-33's vocabulary: every target (`protective_stop_fill`, `target_fill`, `protection_amendment_fill`, `operator_close`, `protection_forced_flat`, `window_forced_flat`/`boundary_flat`/`hold_time_force_flat`, `venue_initiated_close`/`venue_liquidation`) is a real member; `kill_line_flat` correctly *not* used for the kill-switch class; `HEDGE_CLOSE → no successor` consistent with "no hedge machinery in V1." No exit_logic on the bot (AD-33).
- **QL-6 family keying** vs AD-33 (`ExitLogicRef` per family), AD-41 (`q` per family), AD-40 (`bench_consecutive_loss_threshold` per bot/family), AD-35 (paper balance family-scoped): each locus matches the parent verbatim; "key, no authority" does not strip any authority the parent granted (the parent never gave family constraint powers).
- **QL-4 producer templates** vs AD-22: a resolution step producing an ordinary CT-16 fingerprint, not a second identity path; resolved identity enters run identity, dedup lands on CT-16 fingerprints.
- **QL-4 warm-up** vs AD-21/B-2: derived from the resolved producer chain, "no second window" — honors B-2 verbatim.
- **QL-7 no-clock / determinism** vs AD-8/B-2: bot gets the evaluation instant on the callback, no Clock access below the host — stricter than and consistent with B-2's injected frontier clock and golden-slice determinism.
- **QL-1 dependency stance** vs default-deny: the "roster-internal, not applications" reading is the ratified QMB precedent (QMB's own library consumes qmf-risk CT-23 per B-3/B-6); QML is more restrictive (never imports qmf-venue). Legal. (The one residual edge risk is F5, at the CT-33-schema boundary, not the QML-import boundary.)
- **QL-10 build order** vs framework-vs-node split: QML is library/framework-side, node hosts QL-7 seats (runtime) — consistent; QMB's QL-7 adapter is a declared B-1 extensibility change.
- **QL-2 logic identity** vs AD-2/AD-17/AD-30: distribution identity + content fingerprint as Bot identity fields; a code change mints a new Bot "as a changed number mints a new Book." Legal tightening.
