# Backtesting sitting — standing inputs (five-hats sweep) + current docs/ state

Research dossier for the QMX backtesting architecture sitting. Read-only survey; facts cited to file:line. Prepared 2026-08-20.

Sources:
- `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/reviews/five-hats-sweep.md` (44 findings + 6 cross-hat conflicts, dated 2026-08-19, target ARCHITECTURE-SPINE.md AD-1..AD-14).
- `docs/` knowledge base (change-mode absorbed spine AD-1..AD-41; risk sitting closed 2026-08-20).

---

## PART 1 — Five-hats entries the backtesting sitting must consume

### 1a. Findings the sweep EXPLICITLY routes to backtesting (inherited, not owned)

The sweep's own handoff table (`five-hats-sweep.md:283`) names exactly three as backtesting-inherited:

- **R-1** — SR\* denominator. The attempt counter needs a defined counting unit; the sweep proposes a **"search campaign"** (charter + dataset split + declared search space + generation/evaluation budget, minted before the search runs), with population size and realized evaluation count as campaign facts. Gives AD-12's computation-identity-vs-occurrence split a clean application: one campaign computation, many evaluation occurrences. This is the denominator GAP-0049's future SR\* threshold deflates against. Primary owner registry, but the SR\* denominator is backtesting's. (`five-hats-sweep.md:42-44`)
- **R-5** — purge/embargo reuse. Split manifests need declared **purge width** (drop boundary-adjacent region) and **embargo width** (delay test-window start), derived from the max look-forward horizon of consuming artifacts (indicator warm-up, structure observed-at/confirmed-at lag), recorded in the manifest and participating in the split fingerprint so a split reused with a longer-horizon artifact refuses rather than leaks. (`five-hats-sweep.md:58-60`)
- **A-2** — result-container reuse. The analyst's central object — a fingerprinted performance result over a declared population/period, produced by a versioned formula, carrying units — has no owning contract. Risk sitting mints the container (now CT-32, see Part 2); backtesting inherits/reuses it. (`five-hats-sweep.md:130-132`)

### 1b. Findings whose V1 workflow depends on backtesting mechanics (sweep flagged, scope-disciplined)

The sweep declined pure-backtesting attacks "except where a hat's V1 workflow depends on them (R-1, R-4, A-2)" (`five-hats-sweep.md:19`). So also load:

- **R-4** — sealed holdout consumed from a sandbox that may not write. L19 + the 12-month seal permit one logged final look per strategy, but AD-12's namespace rule forbids a non-live sandbox writing into the live evidence namespace — jointly unsatisfiable. Sweep's resolution: model a seal look as a **write-gated operation against the live registry** (requested, granted, recorded as a registered occurrence before the data is readable), else the seal is honor-system only. Owner named as data sitting colliding with AD-12; the seal/look mechanics are backtesting's concern. (`five-hats-sweep.md:54-56`)

### 1c. Researcher-hat findings (R-*) — the research/experimentation workflow the backtesting sitting frames

Full researcher workflow walked at `five-hats-sweep.md:40`: reads paper/transcript → forms hypothesis → genetic search over indicator/confluence parameter space in a disposable sandbox → discards 99.9% → registers survivors → checks against sealed holdout once → hands to developer.

- **R-1** (above) — attempt counter / search campaign — registry+backtesting.
- **R-2** — AD-13 load ladder has no research rung; researcher's load is 10^4–10^6 serializations/fingerprints/lineage-appends in a burst with cold cache, opposite shape to the ~40-bot live-latency node scenario. Needs a research throughput rung (fingerprints/s, registrations/s, edge-appends/s at burst). (`five-hats-sweep.md:46-48`) — see conflict X-4.
- **R-3** — negative results need a lifecycle state and cheap evidence form. Rejected population is the multiple-testing denominator; if only survivors get identities the operator can never compute a deflated statistic nor answer "did we already try this?". Decide: (a) `rejected`/`abandoned` lifecycle state, (b) whether rejected candidates consume attempt budget, (c) a bulk-summary evidence form so a million discarded genomes ≠ a million full records. (`five-hats-sweep.md:50-52`)
- **R-7** — two sandboxes producing one label with differing float bytes is the researcher's normal case; AD-10 currently classes same-hash-differing-bytes as a true collision (refused+alarmed). Sweep's fix (registry-side): label-identified float artifacts with differing content checksums are **lineage siblings under one label** with (OS, library-version) provenance; only identity-content hash divergence is a collision. (`five-hats-sweep.md:66-68`)
- **R-8** — seed and search-state provenance have no home in the result label. A stochastic search result is not reproducible from AD-12's five parts alone: needs RNG seed, generator identity, and (parallel) reduction order. Place them as identity-bearing inputs (reproducible, never deduplicated) or as occurrence provenance (deduplicating, not reproducible) — choosing by default loses one property silently. (`five-hats-sweep.md:70-72`)
- **R-9** — foreign research artifacts (sklearn, Optuna, statsmodels, torch) must be registerable as an **opaque foreign artifact kind** (content checksum + declared producer + environment provenance + typed "not a QMF contract" marker) or don't-box-in dies at the registry door. (`five-hats-sweep.md:74-76`) — see conflict X-1.
- **R-6, R-10** — R-6 (warm-up as declared fingerprinted property so the causality gate can test it — the GAP-0016 join) is indicator+registry owned but directly feeds the causality-gate design backtesting must ratify (GAP-0016). R-10 (hypothesis provenance as a registry kind) is registry-owned. (`five-hats-sweep.md:62-64, 78-80`)

### 1d. Cross-hat conflicts touching backtesting

- **X-1** — Researcher's open toolbox vs Trader's live-money strictness at the registry door. Resolution shape: explicit asymmetry — **registration permissive/cheap** (accepts opaque foreign artifacts w/ provenance), **promotion strict/total** (may refuse anything it cannot fully verify). DEC-0011's "strictness only at the harness and live-money gate" applied to registry kinds. (`five-hats-sweep.md:250`)
- **X-4** — one AD-13 benchmark ladder cannot serve a GA fan-out (R-2: throughput at burst, cold caches, vectorized/batch) and a 1-second scalping path (T-3: per-tick latency, bounded jitter, streaming). Resolution: indicator sitting makes the two modes explicit conformance targets of one protocol with a **stated equivalence obligation** (same inputs → same outputs across modes, itself a contract test per AD-4); AD-13 carries two rungs. GAP-0031 already gestures at "batch-and-incremental." (`five-hats-sweep.md:260-262`) NOTE: docs record this as **resolved** — indicators are now a two-mode library, batch+streaming bound by an equality law (DEC-0126/DEC-0128, see Part 2), so X-4's shape is largely absorbed; backtesting inherits the equality-law guarantee.

### 1e. Complete R-* ID roster (for the sitting's checklist)
R-1 (must, registry) · R-2 (should, registry+AD-13) · R-3 (must, registry) · R-4 (must, data/AD-12) · R-5 (should, data) · R-6 (must, indicator+registry) · R-7 (must, registry) · R-8 (must, registry) · R-9 (should, registry) · R-10 (note, registry). Cross-hat: X-1 (registry), X-4 (indicators). Inherited per handoff table: R-1, R-5, A-2. Scope-flagged: R-4.

---

## PART 2 — Current docs/ state on the backtesting surface

### 2a. Risk increment IS absorbed. GAP-0016/0017 ARE marked deferred-to-backtesting. QML is NOT planned in V1 (deferred).

**Headline:** the risk sitting (GAP-0039–0046) is fully absorbed into docs (change-mode, 2026-08-20; 44 gaps answered, 0 open — `docs/changelog.md:23-24`, `docs/gap-report.md:33`). What remains open is exactly the backtesting-sitting surface.

### 2b. GAP-0016 / GAP-0017 — DEFERRED to the backtesting sitting (DEC-0121), explicitly not closed

- Gap report: "**2 deferred to the backtesting sitting** — GAP-0016 (look-ahead/causality registration gate) and GAP-0017 (attempt counter), per DEC-0121" (`docs/gap-report.md:19`); dedicated section "These gaps are **not** closed; they remain owed" (`docs/gap-report.md:120-122`).
- GAP-0016 body: "What exact causality and look-ahead registration test must an artifact pass, and what evidence proves the pass?" Consequence knowingly accepted: **artifacts registered before the backtesting sitting carry no causality evidence, not retroactively reconstructible**; bitemporal ingredients (event-time vs knowledge-time) stay ratified via AD-8/CT-10; occurrence records still log every run so raw material accrues without a policy. (`docs/gap-report.md:126`)
- GAP-0017 body: "What does the attempt counter count, at which scope, when does it reset, and how does it constrain registration or research budget?" No attempt-count policy exists; raw material accrues without policy. (`docs/gap-report.md:127`)
- Traceability: both `deferred`, `false`, "Deferred by DEC-0121 to the backtesting sitting; CT-08" (`docs/knowledge/traceability.md:240-241`).
- **CT-08 gate-evidence is a deliberately empty skeleton**: purpose "Carry the evidence for look-ahead causality checks and immutable registration-attempt accounting"; every field `type: null / type_gap: GAP-0016`, `fields_gap: GAP-0016`, `enums_gap: GAP-0017`, `units_gap: GAP-0017`, `nullability_gap: GAP-0016` (`docs/contracts/ct-08-gate-evidence.yaml:11-26`). This is the contract the sitting fills.
- CT-06 registration: "Registration currently records occurrence evidence but enforces no look-ahead causality gate and no attempt counter; both deferred … artifacts registered before then carry no causality evidence (DEC-0121; GAP-0016, GAP-0017 deferred)" (`docs/contracts/ct-06-registration.yaml:29`). FM-3 failure mode makes the same promise (`docs/components/qmf-registry.md:99`).
- **Interim guards exist but are explicitly NOT the gate**: qmf-structure in-component emission invariant (DEC-0129) is "a cheap interim guard, not that gate" (`docs/components/qmf-structure.md:64`, `docs/decisions/ADR-0006-indicators-and-structure.md:45`). The 12-month seal (DEC-0119) is enforced now as a `policy rejection` refusal "independent of the deferred GAP-0016/0017 gates" (`docs/contracts/ct-11-evidence-persistence.yaml:25`, `docs/lenses/bugs/triage.md:50`).
- Attempt-counter variables exist as **unset, deferred registry vars**: `registry_attempt_scope`, `registry_attempt_budget`, `registry_attempt_reset_policy` all "Deferred to the backtesting sitting (DEC-0121); … unresolved" (`docs/registry/variables.yaml:198-223`, `docs/components/qmf-registry.md:87-89`, `docs/decisions/ADR-0015-registry-records-and-promotion.md:58`).

### 2c. GAP-0047 / GAP-0048 / GAP-0049 — deferred consumer gaps

- Gap report: "3 deferred consumer gaps — GAP-0047–GAP-0049, waiting on the QML, backtesting, and research-threshold sittings; GAP-0047 (QML reconciliation) rides the QML sitting, **GAP-0048 (backtesting library) and GAP-0049 (SR\*/preregistered search-quality threshold) ride the backtesting sitting**" (`docs/gap-report.md:20`; row `docs/gap-report.md:34`).
- **GAP-0048** — backtest fidelity taxonomy: "Ratify the backtest fidelity taxonomy (deferred to the backtesting sitting)" (`docs/scenarios/SCN-0001-core-freeze-gate.md:25`). Owns "the backtesting library's fidelity levels, fill models, and parity contracts" (`docs/glossary.md:198`). Still open under DEC-0134 (`docs/knowledge/traceability.md:175`). GAP-0048 is the type-gap on **CT-05 world enum**: `world = simulated` is "reserved but UNUSABLE in V1 — writing world=simulated into governed evidence is a policy-rejection refusal (CT-04) until the backtesting sitting defines simulated-time typing (DEC-0110, GAP-0048)" (`docs/contracts/ct-05-version-fingerprint.yaml:10,26,75`; AGENTS.md:24).
- **GAP-0049** — SR\* search-quality threshold: "Ratify the SR\* search-quality threshold (deferred with backtesting)" (`docs/scenarios/SCN-0001-core-freeze-gate.md:27`). Two of six qmf-core freeze choices remain open = backtest fidelity taxonomy + SR\* (DEC-0134 supersedes DEC-0124) (`docs/scenarios/SCN-0001-core-freeze-gate.md:23`, `docs/knowledge/traceability.md:175`).
- **GAP-0047** — QML reconciliation (NOT this sitting; QML sitting): "When QML is revisited, what Bot authoring, confluence composition, Book binding, lineage, and promotion contracts must it consume from QMF V1?" Resolution: defer QML until Bot schema + one-Bot-to-one-Book binding ratified, then make it a **consumer** of QMF contracts, not a new foundation layer (`docs/gap-report.md:139`). `Bot` is a reserved kind name whose full body awaits the QML sitting (`docs/contracts/ct-06-registration.yaml:52,55`; `docs/gap-report.md:168` DEC-0090).

### 2d. Does docs/ plan QML? — NO. Deferred, outside V1.

- ADR-0011 decision: "Backtesting, the future modular sandbox, the visual Simulator, MIS, the QML Bot library, and agentic runtime organs are **outside QMF V1**" (`docs/decisions/ADR-0011-deferred-consumer-products.md:30`; DEC-0083/0087/0088/0089/0090/0091). Note ADR-0011 status is still `provisional pending operator ratification` (`ADR-0011:5,16`).
- QML = "the deferred Bot-oriented library under the QMF umbrella … not part of the immediate QMF V1 roster" (`docs/glossary.md:406`); L11 "QML names the deferred Bot-oriented library rather than the whole foundation" (`docs/constitution.md:38`).
- Indicators are declared "consumer-blind across bots, structure, MIS, and **backtesting**" (`docs/glossary.md:386`) — the seam anticipates a backtesting consumer.

### 2e. DEC-0084 — DEAD (rejected), not deferred

- DEC-0084 "All agents and Books share one centralized always-on backtesting service" → **dead**: "Centralization could not supply enough compute for concurrent work" (`docs/gap-report.md:199`; `docs/knowledge/traceability.md:107` status `dead`; ADR-0011 option 1 dead, `ADR-0011:24`).
- Positive counterpart DEC-0087: any future backtesting capability is a **modular on-demand library or sandbox that can vary by Book, not a permanent central service** (`docs/gap-report.md:165`, `docs/glossary.md:204-206`).

### 2f. Other standing constraints on the backtesting design (from docs/)

- **Vocabulary law (AGENTS.md:49):** "backtesting is a **library**, never an 'engine'"; say **extensions** not "plugins". Glossary "Backtesting engine" → use "future backtesting library" (`docs/glossary.md:634-636`).
- **Operator vocabulary direction (2026-08-20, unratified):** "experimentation is the broad research activity, and backtesting is the verification step within it" — a candidate rename (ticket 008) to be settled at the backtesting sitting; until then no contract/component renames (`docs/glossary.md:196-198`).
- **L31 / DEC-0122:** everything downstream of QMF — trading node, **backtesting**, agentic system, product UI — must be built with QMF libraries and must not re-implement or bypass its contracts (`docs/constitution.md:78`, `docs/AGENTS.md:48`).
- **L13/L16:** qmf-core must contain no backtest runtime (`docs/constitution.md:42`, `docs/AGENTS.md:44`).
- **DEC-0064 / DEC-0063:** broker-vs-simulation parity deferred to the future backtesting library, not venue V1 (`docs/gap-report.md:162,192`).
- **DEC-0057:** genetic/custom-indicator discovery belongs to a future research lab, not V1 indicator library (`docs/gap-report.md:161`) — bounds the researcher's GA lane.
- **CT-12 dataset-split** already carries `gaps: [GAP-0016, GAP-0017]` and enforces time-ordered non-overlapping manifests + sealed-window no-peek (`docs/contracts/ct-12-dataset-split.yaml:10-11`) — this is the contract R-5's purge/embargo widths must extend.

---

## Net for the architect
Docs are clean and consistent: the risk increment is fully absorbed, and every backtesting-relevant surface is left as an explicit, owned, open gap (GAP-0016, GAP-0017 with the empty CT-08 skeleton; GAP-0048 gating `world=simulated`; GAP-0049 the SR\* threshold) plus dangling registry variables and the CT-12 split extension. The five-hats sweep hands the sitting a concrete research-workflow agenda (R-1..R-10, X-1, X-4, plus R-4) beyond the three formally inherited items. QML and the backtesting library itself stay deferred/outside V1; a central service is dead; the shape is a modular per-Book library.
