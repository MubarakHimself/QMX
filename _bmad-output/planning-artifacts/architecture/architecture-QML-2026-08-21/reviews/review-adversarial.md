# QML Spine — Adversarial Review

**Lens:** ADVERSARY. Construct pairs of units one level down that each obey every QL rule (and every inherited AD/B rule) to the letter yet still build incompatibly — clashing data shapes, two owners of one entity, conflicting identity/ordering, ambiguous vocabulary read two ways. Every incompatible pair is a hole to close with a tightened rule.

**Artifact:** `architecture-QML-2026-08-21/ARCHITECTURE-SPINE.md` (QL-1..QL-10), against parent QMF (AD-1..41), sibling QMB (B-1..15), and CT-23.

**Verdict:** The spine is thin, disciplined, and mostly seam-clean. But it carries one architecture-level contradiction (the intent-mint ExitLogicRef derivation) and a cluster of identity/ordering/parent-contract seams where two conformant builders diverge. Twelve of the thirteen findings below are concrete incompatible pairs; the last is a governance-authority gap. None is cosmetic.

---

## F1 — CRITICAL — The QL-7 intent-mint ExitLogicRef derivation breaks bot isolation, the determinism tuple, and the conformance sandbox — and needs a CT-23 field that does not exist

**The rule as written.** QL-7: *"the declared full-loss price on a CT-23 entry intent is derived at intent mint by executing the Book-declared family ExitLogicRef (module_id + config resolved read-only from the bound Book's exit_policy for the bot's family, consuming the bot's advisory stop proposal and cited evidence); the Book door deterministically recomputes and verifies at admission."* QL-7 also states the bot **"receives only the declared footprint's evidence"**, is deterministic on the tuple **"(declaration, assignment, evidence sequence, state)"**, and QL-8 Layer 2 tests it **in an isolated environment** (no Book present).

**The incompatible pair.**
- *Bot-author build:* reads QL-7 literally — the bot executes the bound Book's `ExitLogicRef` at intent mint to produce `declared_full_loss_price`. To do this the host must inject the Book's `ExitLogicRef` (module + config) as a read surface. But that surface is **not in the bot's declared footprint** (QL-4 footprint = streams, calendars, producer bindings — no Book exit logic), so QL-7's own "only the declared footprint's evidence" clause is violated, and the intent output now depends on Book state that is **not in the determinism tuple**. The same bot bound to two Books (or one Book re-versioned) yields different intents from identical `(declaration, assignment, evidence, state)` — QL-7's determinism claim is false.
- *Book-author build:* reads AD-33/AD-40 — the Book owns exit policy and the stop; the bot supplies only an advisory proposal; the Book fills the full-loss price. But CT-23 marks `entry.declared_full_loss_price` a **mandatory inbound field** and "the sole source of `original_risk_distance`," so the bot must present it. Under this reading the bot cannot present a price it is not allowed to derive.

Both readings obey the letter; they wire the derivation to opposite sides of the door.

**Second, harder break — the sandbox cannot run.** QL-8 Layer 2 loads the logic "in an isolated environment" and asserts "identical intents" twice. With no Book present the isolated bot has no `ExitLogicRef`, so it **cannot produce `declared_full_loss_price` at all** — the mandatory CT-23 field is unresolvable in the exact environment that is supposed to prove determinism. Either the sandbox must inject a Book's `ExitLogicRef` (contradicting "isolated" and making conformance Book-dependent, so a bot's registration verdict changes with the Book), or the full-loss price is not the bot's output (contradicting QL-7).

**Third break — a missing CT-23 field.** QL-7's `ExitLogicRef` consumes *"the bot's advisory stop proposal."* CT-23's entry intent has no such field: it carries `declared_full_loss_price`, `proposed_r` (an r-multiple, not a stop), `reason_code`, `direction`, `instrument`, `execution_target`. The door "recomputes and verifies" — but it cannot recompute without the advisory stop proposal and the cited evidence as inbound fields, and CT-23 carries neither. Adding them is a **CT-23 format-version mint** (see F4), not a spine assertion.

**Fix.** Pick one owner and pin it.
- Preferred: the **Book** derives `declared_full_loss_price` via `ExitLogicRef` at admission. The bot supplies only an **advisory stop proposal** (mint it as a new, explicitly optional CT-23 entry field via a CT-23 format-version bump) plus `proposed_r`. Reconcile CT-23's "mandatory `declared_full_loss_price`" to mean *the Book resolves and stamps it before the command record; a bot may not present one* — mirroring exactly how `requested_r` is already Book-resolved. The bot stays isolated, deterministic on its own tuple, and sandbox-testable with no Book.
- If instead the bot must run the `ExitLogicRef`: add the Book's family `ExitLogicRef` (module + config fingerprint) to the bot's determinism tuple **and** to the QL-8 sandbox harness as a pinned reference `ExitLogicRef`, and state that a bot's conformance verdict is scoped to that reference — accepting that "registered" is no longer a Book-independent fact. This is the worse path; state it only if chosen deliberately.

---

## F2 — HIGH — QL-8 prediction-linter check (b) makes the "honest V1 default" Book un-admittable for every bot

**The rules.** QL-3: the bot's permitted-intent declaration is *"a subset of the ratified vocabulary: **entry** plus zero-or-more exit kinds."* QL-8 check (b): *"the bot's permitted-intent kinds are a subset of the Book's `exit_policy` permitted kinds."* AD-33: *"A Book may declare **zero** permitted bot-intent kinds; a static-protective-stop-only Book is fully legal and is **the honest V1 default**."*

**The incompatible pair.** Every bot mints `entry` (its whole purpose), so `entry` is in every bot's permitted-intent set.
- *Builder A* takes check (b) literally: the bot's permitted set `{entry, ...}` must be a subset of the Book's `exit_policy` permitted kinds. A zero-kind Book permits the empty set; `{entry} ⊄ {}` → **check (b) fails**. The default static-stop Book can admit **no bot at all** — a direct contradiction of AD-33's "honest V1 default."
- *Builder B* silently reads "permitted-intent kinds" in check (b) as *exit* kinds only, and admits the bot.

Two Books built to the same words reach opposite admission verdicts for the same bot. This is precisely "ambiguous vocabulary two builders read two ways," and one reading bricks the default deployment.

**Fix.** Split the vocabulary. `entry` is always permitted and is **never** gated by `exit_policy`. Reword QL-3's permitted-intent declaration as *"entry (always permitted) plus a declared set of permitted **exit** kinds."* Reword QL-8 check (b) as *"the bot's declared permitted **exit**-intent kinds are a subset of the Book's `exit_policy` permitted **exit** kinds."* Reword AD-30/AD-33 references so `exit_policy`'s "permitted bot-intent kinds" is explicitly the exit-kind set (which may be empty).

---

## F3 — HIGH — Producer bindings are declared in two loci (Bot footprint and confluence legs) with no reconciliation rule; so is the stream set

**The rules.** QL-4: *"the footprint declares **everything the bot consumes**: the stream set; required calendars; and producer bindings."* QL-5: a confluence leg *"= (role, **producer binding per QL-4**, optional declared exact parameters)."* QL-7: *"Hosts provide **only** the declared footprint to the logic."* QL-3 lists, as separate CT-33 content bullets, both *"the footprint (below)"* and *"the stream-set requirement,"* while QL-4 says the footprint *includes* the stream set.

**The incompatible pair (producers).** A confluence (CT-34) is its own artifact, reusable across bots, and carries producer bindings on its legs. The Bot (CT-33) also carries a footprint of producer bindings.
- *Builder A* treats the footprint as the authoritative complete manifest and enforces at Layer 1 that every cited confluence's leg producers appear in the footprint. Consistent.
- *Builder B* treats each confluence as self-contained (it declares its own producers) and the Bot footprint as *additional* producers only. A bot then cites a confluence whose leg consumes producer P, but P is absent from the Bot's footprint. At runtime the host, obeying QL-7, provides **only the footprint** — so the logic's confluence evaluation is **starved of P**. Nothing in the spine refuses this bot at registration; the footprint's whole reason for existing (comparability, dedup, the prediction linter's `footprint_requirements` check) is silently incomplete.

**The incompatible pair (stream set).** QL-3 declares a top-level "stream-set requirement" field *and* the footprint (QL-4) declares "the stream set." Builder A nests the stream set inside the footprint; Builder B places it at CT-33 top level. Different canonical JSON nesting → **different CT-33 `fp1`** for identical bots (AD-16 dedup fails, two identical bots run two identities), and prediction-linter check (d) ("the bot's stream set lies within venue capabilities") reads a different locus in each build.

**Fix.** Make the footprint the single canonical consumption manifest. Pin in QL-4: *the footprint's producer-binding set MUST equal the transitive union of every cited confluence's leg producer bindings plus any bot-direct producers; a confluence-leg producer absent from the footprint is a Layer-1 registration refusal.* Pin the stream set in exactly one locus (recommend: a footprint sub-field, with QL-3's "stream-set requirement" bullet re-expressed as "declared within the footprint (QL-4)") so CT-33 has one nesting and one linter target.

---

## F4 — HIGH — QL-8 adds two fields to AD-32's closed `evidence_requirements` shape without declaring a parent-contract format-version mint; the silent-add path binds live money on wrong evidence

**The rules.** AD-32: `evidence_requirements` = *"(world, account role, minimum evidence window, and the producer contract format versions the measurement must carry)"* — a fixed four-part shape. QL-8: *"AD-32's `evidence_requirements` vocabulary **gains two bot-side declarable fields**"* (registered-conformant-Bot cite; canonical-assignment evidence). AD-5: *"a format version's meaning never changes after the fact — incompatible change mints the next version plus a migration note."* AD-30: *"Unknown sections under a known contract format version are ignored; an unknown format version refuses."*

**The incompatible pair.** QML (a child spine) is extending the field shape of a parent-owned contract (CT-22's `admission_bar.evidence_requirements`, owned by qmf-risk/qmf-registry).
- *Builder A* treats the addition as a **CT-22 admission-bar format-version mint** (v2): new bars carry the two fields; old bars refuse under a new-version parser; AD-5 migration note recorded.
- *Builder B* treats the two fields as an addable extension under the **existing** format version. Then, per AD-30, *"unknown sections under a known contract format version are **ignored**"* — so an **old parser silently ignores a `canonical-assignment-evidence` requirement**, treats it as absent, and admits a run whose resolved values differ from the canonical assignment as satisfying the bar. Live money binds on evidence the requirement was written to forbid — bypassing exactly the guarantee QL-3/QL-8 built.

**Fix.** State explicitly in QL-8: the two `evidence_requirements` fields are an **AD-5 format-version mint of the CT-22 admission-bar contract** (owned by qmf-risk; QML authors the field semantics, qmf-registry owns the shape), with a migration note; not a silent field addition. Same discipline for the `footprint_requirements` shape QL-4 fills — AD-30 reserved it as `pending(GAP-0047)`, so its resolution is a CT-22 format-version mint, not an in-place grammar change. Note who mints the version (the parent contract's owner acting on QML's authored semantics), since QML cannot amend a parent contract by assertion.

---

## F5 — HIGH — The QL-4 producer template under-declares AD-22's mandatory identity fields, so two run-config compilers resolve it to two different CT-16 fingerprints and dedup breaks

**The rules.** QL-4: a producer template = *"(formula id, contract format version, fixed exact parameters, and space-bound parameters …), resolved to a concrete configured-producer fingerprint … so … dedup still lands on ordinary CT-16 fingerprints."* AD-22: a CT-16 configured-indicator identity is *"the entire declared configuration"* — formula id, format version, exact parameters, **the ordered named input set, declared calendar requirements, alignment policy, missing-value policy, warm-up, output schema, supported modes, and the arithmetic-reference configuration.** *"An element missing from the fingerprint is a contract defect."*

**The incompatible pair.** The template carries four of AD-22's ~ eleven identity fields. The other seven (input set, calendars, alignment policy, missing-value policy, warm-up, output schema, modes, arithmetic-ref config) must be supplied at resolution.
- *Builder A*'s compiler fills alignment policy = "as-of last known," missing-value policy = "refuse," a default output schema, etc.
- *Builder B*'s compiler fills different defaults.

Both resolve "the same" template but produce **different CT-16 `fp1`s**. QL-4's promise that "dedup still lands on ordinary CT-16 fingerprints" is empty — dedup lands on *two* fingerprints. Downstream: the bot's canonical assignment resolves to different producer identities on different machines, so identical canonical runs get different run-config fingerprints, and QL-8's canonical-assignment-evidence equality check and B-15's as-of dedup both fail.

**Fix.** Require the template to be a **complete CT-16 configuration minus only the space-bound parameter values** — i.e., it carries every AD-22 identity field except the specific parameters bound to bot-space names. Resolution then substitutes only the space-bound values and is a **total, single-valued function** producing one deterministic CT-16 fingerprint. State that any AD-22 identity field the template omits is a Layer-1 registration refusal (mirroring AD-22's "missing element is a contract defect").

---

## F6 — HIGH — QL-3's "Content, all identity unless declared display-only" over the AD-16 header forks Bot identity on writer + sequence

**The rules.** QL-3: *"Content, **all identity unless declared display-only**: the AD-16 common header (stable id from `fp1`, contract format version, at-birth refs, **writer + sequence**); …"* AD-16/AD-8: the stable id is *derived* from `fp1` (never part of the hashed content), created-at is occurrence/display-only, and *"the identity of a stored record is its AD-10 fingerprint; `(instant, writer, sequence)` is an **ordering key only**."* AD-16's whole dedup property depends on writer/sequence/created-at being **excluded** from `fp1`.

**The incompatible pair.**
- *Builder A* applies AD-16's classification: writer, sequence, stable-id, created-at are ordering/occurrence, excluded from the Bot `fp1`; only the semantic content is hashed. Two composition roots minting the same Bot definition produce the same `fp1` → idempotent dedup (AD-16's design).
- *Builder B* reads QL-3 literally — "all identity unless declared display-only" — sees no explicit display-only tag on "writer + sequence" in the bullet, and **includes them in `fp1`**. Now the same Bot minted by two writers (QMB orchestrator vs the platform root vs the trading node — see F11) gets **different fingerprints**. Bot identity forks by who wrote it; dedup, cross-sandbox merge, and every fingerprint cite (confluence-set cites, seat cites, admission-bar cites) diverge.

**Fix.** In QL-3, replace the blanket "all identity unless declared display-only" preamble over the header bullet with an explicit carve-out: *"the AD-16 common header, whose `writer`, `sequence`, `stable id`, and `created-at` are AD-16/AD-8 ordering/occurrence fields **excluded from `fp1` identity**; only the contract format version and at-birth refs are identity. Bot identity is the semantic content only."* This is the one place the spine's own "identity by default" phrasing collides with AD-16's ordering-key law; name the exclusion so it cannot be read the wrong way.

---

## F7 — MEDIUM — The bot-state snapshot tuple inherits AD-22's `(OS, arithmetic-reference build)` scope but omits the logic identity and the protocol version, so a snapshot restores across code versions and breaks determinism

**The rules.** QL-7: *"snapshot/restore as a versioned contract **scoped per AD-22's tuple rule**."* AD-22: *"A state snapshot is … scoped to a declared **(OS, arithmetic-reference build)** tuple; restoring across tuples is an `unavailable dependency` refusal."* QL-2: a bot's logic is plain Python (may use no arithmetic reference at all), and *"a code change mints a new Bot."*

**The incompatible pair.** Bot state lives in bot logic, which is versioned independently of TA-Lib.
- *Builder A* scopes bot snapshots to `(OS, arithmetic-reference build)` verbatim. A snapshot taken under logic-artifact-v1 restores cleanly into a process running logic-artifact-v2 (same OS, same TA-Lib, possibly no TA-Lib) → **silently corrupt / non-deterministic state**, and for a pure-Python bot with no arithmetic reference the second tuple component is undefined.
- *Builder B* additionally scopes to the logic distribution's content fingerprint and the protocol format version, refusing cross-logic restore.

Two builders, two restore-admissibility rules; A admits restores that violate the very determinism QL-7 and QL-8 Layer 2 demand.

**Fix.** Pin the bot-state snapshot tuple explicitly as **`(OS, logic distribution identity + content fingerprint, QL-7 protocol format version, and arithmetic-reference build where the logic declares one)`**; restoring across any component is an `unavailable dependency` refusal. State that the arithmetic-reference component is present only when the logic declares an arithmetic-reference dependency.

---

## F8 — MEDIUM — The conformance sandbox has no pinned owner, isolation contract, or golden-slice provenance, so the same bot earns different verdicts at different hosts and "registered" means two things

**The rules.** QL-1: the library is *"pure per AD-15 (no threads, no I/O); registration writes and **sandbox processes ride the platform/QMB composition roots**."* QL-8 Layer 2: *"the logic artifact loads in an isolated environment; runs a **golden evidence slice** twice … (static import scan + sandbox denial)."* AD-15: QMF/QML never spawns processes; the application owns concurrency.

**The incompatible pair.** Because `qml` is pure, the isolating **process** and the **denial enforcement** are host-owned, and the golden slice's provenance is unstated.
- *Host A* (QMB) enforces no-network via a static import scan only, and generates a golden slice from the footprint one way.
- *Host B* (platform / trading node) enforces via OS sandboxing and generates a different golden slice.

A bot that passes A's sandbox fails B's (different denial strictness), or the two "twice-identical-intents" checks exercise different slices. Yet QL-8's ticket says *"the Bot registry kind mints only for artifacts passing both layers"* — a single global registry fact. Two hosts can now disagree on whether the same bot is registrable; the ticket's meaning is host-dependent.

**Fix.** Split the sandbox into a QML-owned versioned **conformance contract** and a host-owned **process runner**. QML owns, as format-versioned surface: the denial set (clock/I-O/network/randomness), the static-import-scan rules, the determinism harness, and a **deterministic golden-slice generator** keyed off the bot's declared footprint (or a bot-declared, identity-bearing conformance fixture). The host owns only raw process spawning and injects results back to QML's pure verdict function. State that a bot's conformance verdict is, by construction, host-independent.

---

## F9 — MEDIUM — QL-5's confluence-leg ordering default collides with AD-25's causal-composite default, forking CT-34 fingerprints for composed confluences

**The rules.** QL-5: legs are *"canonically ordered by leg-content fingerprint ascending … a confluence **may** declare its legs order-significant explicitly (**AD-25's causal-composite inversion available**, never silently assumed)."* AD-25: *"Children of a **causal composite are order-significant by default** (a family declares a collection unordered explicitly)."* AD-17: multiplicity collections are fingerprint-ascending *"unless the owning contract explicitly declares … order-significant — **causal structure composites invert that default**."*

**The incompatible pair.** A confluence whose legs cite CT-17 structure objects (or another confluence built from them) sits astride two defaults.
- *Builder A* follows QL-5: order-**insignificant** by default, fingerprint-ascending, unless opted in.
- *Builder B* reads "AD-25's causal-composite inversion available" as "AD-25 governs here" and, seeing structure children, applies AD-25's order-**significant**-by-default (declaration order).

The two produce **different canonical orderings → different CT-34 `fp1`** for the same legs. The bot's confluence-set cite (by fingerprint) then points at two different artifacts; dedup and comparability fail.

**Fix.** State one default unambiguously: *CT-34 confluence legs follow AD-17's fingerprint-ascending default (order-insignificant); a confluence is a CT-34 artifact, **not** a CT-17 causal-structure composite, so AD-25's order-significant-by-default does not reach it. Order-significance is opt-in per confluence and enters the fingerprint only when declared.* Drop or reword "AD-25's causal-composite inversion available" so it reads as an opt-in mechanism, not an inherited default.

---

## F10 — MEDIUM — QL-6's "catch-all default" extends AD-33's "ExitLogicRef per family" without ratifying the shape into `exit_policy`; prediction-linter check (c) depends on it

**The rules.** QL-6: *"A Book's `exit_policy` entries key by family id and **may declare one catch-all default entry**; a bot whose family resolves no entry fails the prediction linter."* QL-8 check (c): *"the bot's family resolves an `exit_policy` entry (**or the Book's declared catch-all**)."* AD-33/AD-30: `exit_policy` declares *"`ExitLogicRef` **per family**."*

**The incompatible pair.** "Per family" and "one wildcard for all unlisted families" are different shapes.
- *Builder A* implements `exit_policy` strictly per AD-33 (explicit per-family entries, no wildcard). A bot whose family lacks an explicit entry **fails check (c)** and is rejected.
- *Builder B* implements the QL-6 catch-all. The same bot **passes check (c)** via the wildcard and runs its exits through the catch-all `ExitLogicRef`.

The same bot at two Books built to the same corpus is admitted by one and rejected by the other; and under B two distinct families collapse onto one `ExitLogicRef`, which AD-41's exit record must key by "the Book-declared loss predicate" version — a wildcard makes that key family-ambiguous.

**Fix.** Either (a) ratify the catch-all into the CT-22 `exit_policy` shape as an explicit, optional, single default entry (a CT-22 format-version mint per F4 discipline), and state that the exit record's loss-predicate key records the *resolved* entry (explicit-or-catch-all) so attribution stays unambiguous; or (b) drop the catch-all and require explicit per-family entries, aligning check (c) with AD-33 verbatim. Do not leave it as a QL-6 assertion over an unamended parent shape.

---

## F11 — MEDIUM — QL-1 routes the Bot-registration write through AD-28's connection-manager pattern (venue path) rather than AD-25's root-mints pattern, leaving the WriterId owner and block-on-unpersistable unpinned for the registry mint

**The rules.** QL-1: *"registration writes and sandbox processes ride the platform/QMB composition roots through **AD-28's injected-sink pattern**."* AD-28 is the **venue** path, where *"the connection manager holds the WriterId"* and AD-28 explicitly says *"AD-25's root-mints pattern does **not** extend to the venue path."* AD-25 (the registry-record pattern): *"structure objects, lifecycle records … are registry record kinds, **minted by the composition root, which holds the WriterId** and the gapless per-(writer, kind) sequence; the library returns fingerprintable content, never stamped records."*

**The incompatible pair.** A Bot-definition mint is a registry-record write, not a venue write — so AD-25 governs, but QL-1 cites AD-28.
- *Builder A* follows the AD-25 pattern QL-1 should have cited: the composition root holds the WriterId and the gapless per-(writer, kind) sequence, sees the RecordSink refusal (block-on-unpersistable), and `qml` returns only fingerprintable content.
- *Builder B* follows QL-1's literal AD-28 citation and puts the WriterId in a connection-manager-like component (or, worse, tries to have `qml` hold it — impossible under QL-1's own purity clause), producing a different writer-unit and a different gap-detection owner for the Bot-kind stream.

Two builders, two WriterId owners for the same record stream → AD-21's gapless per-(writer, kind) sequence has no single owner, gap detection is undefined, and (compounding F6) if writer enters identity the fingerprints fork.

**Fix.** In QL-1, cite **AD-25's root-mints pattern** for the Bot-definition registration write (the composition root holds the WriterId and the gapless per-(writer, kind) sequence, sees the RecordSink refusal; `qml` returns fingerprintable content, never a stamped record). Reserve the AD-28 injected-sink reference for the sandbox's I/O only. Name the writer unit for the Bot-kind stream explicitly.

---

## F12 — MEDIUM — "The content fingerprint of the built artifact" is unpinned for reproducibility, so identical logic source can fork Bot identity

**The rules.** QL-2: the logic's *"distribution identity + version + **the content fingerprint of the built artifact** are identity fields of the Bot definition."* AD-2 (extension mechanics) uses *"distribution identity + version"* as the identity fields — it does **not** add a built-artifact content hash. AD-16: identical work must dedup to one `fp1`.

**The incompatible pair.** Python built artifacts (wheels) are not byte-reproducible by default (embedded timestamps, file ordering, build-host metadata).
- *Builder A* fingerprints the wheel bytes. Two CI builds of the same source → two content fingerprints → **two Bot identities for identical logic**; dedup and cross-sandbox merge fail; paper↔live comparability (which relies on stable Bot identity) breaks.
- *Builder B* fingerprints a normalized/reproducible basis (source tree hash, or relies on distribution identity + version alone).

**Fix.** Pin the identity basis: either use **distribution identity + version** alone (AD-2's own choice) and drop the built-artifact hash, or, if a content hash is wanted, require it to be computed over a **reproducible-build artifact or a normalized source manifest**, declared as fingerprinted contract surface, so identical source yields identical Bot identity. State that non-reproducible wheel bytes may not be the identity basis.

---

## F13 — LOW — QL-5 declares AD-17's confluence-role vocabulary "addable never redefined" and mints `filter`, but the authority to open a parent spine's closed-looking enum is not cited

**The rules.** AD-17 (read-only law): a confluence contains *"one-or-more **levels, triggers, and confirmations**"* — three roles, with no stated addability clause. QL-5: *"The leg-role vocabulary, **addable never redefined**: `level | trigger | confirmation | filter` — the first three verbatim from AD-17; `filter` is freshly minted here."*

**The incompatible pair.** AD-17 names three roles and grants addability nowhere (its "any governed kind" clause is about *composite children*, not leg roles).
- *Builder A* reads AD-17 as the closed anatomy (three roles) and builds a confluence consumer with exactly three role slots; a `filter` leg is an unknown role it cannot place.
- *Builder B* reads QL-5 and builds a four-role consumer.

A CT-34 artifact with a `filter` leg is consumed by B and rejected/mis-handled by A. The deeper issue: a **child spine cannot open a parent spine's enum by assertion** — that is a redefinition of AD-17's confluence anatomy.

**Fix.** Establish the authority. State that QL-5 is not amending AD-17 but formalizing an enum AD-17 left implicit, and pin the addability as **CT-34's own contract surface** ("leg-role vocabulary, closed-and-addable, addable never redefined; AD-17's three are the seed"), consistent with how AD-40/AD-33 treat the unit-kind and close-reason vocabularies. If AD-17 is meant to remain the authority on its own anatomy, route the `filter` addition as a parent-spine (AD-17) amendment rather than a QML assertion. The `filter` provenance mark is good; the missing piece is the *addability authority*, not the mint itself.

---

## Seams checked and found clean (no finding)

- **Canonical assignment vs B-3 run-spec overrides vs B-4 confirmation roles** — QL-3's "seats execute the canonical assignment only; overrides are B-3 run-spec labels; a run whose resolved values differ satisfies no canonical-assignment requirement, checkable from the resolved run-config with no B-4 amendment" is internally consistent and matches B-3/B-4. (Its only exposure is via F5: if template resolution is non-deterministic, the equality check itself becomes unstable — fixed by F5.)
- **Bot identity is content; re-binding/seats/paper flips never mint a Bot** — QL-3 aligns with AD-17 and AD-29's binding-epoch model; the paper flip minting a binding epoch (never a Bot) is honored verbatim.
- **CT-29 close-reason mapping (QL-9)** — the donor `CloseReason → CT-29` map is a recorded-evidence projection, not a second taxonomy; consistent with AD-33/AD-41.
- **`requested_r` Book-resolved; bot never sizes** — QL-7 honors AD-33/AD-40/CT-23 exactly. (The full-loss-price derivation is the exception — F1.)
