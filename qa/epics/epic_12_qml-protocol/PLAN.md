# Verification PLAN — Epic 12: qml-protocol (bot runtime protocol & two-layer conformance gate)

- **Audit tier:** **T2**. Tier scope executed here: **L2 (property/invariant) + L3 (contract) for every acceptance criterion; targeted L1 unit properties on the highest-consequence boundaries; a lean L0 static/purity gate; one L6 requirements-fidelity review pass.** L4 (wired integration) and L5 (acceptance scenario) are **out of this tier's execution scope** by ratified reason (the record mint is defined-unwired at the AD-25 composition root) — see §3 and §8.
- **Epic:** Epic 12 — `qml-protocol` (Wave 5, **H**). FRs owned: **FR-048** (technical-never-performance two-layer conformance) and **FR-050** (the bot runtime protocol QMB — and later the trading node — hosts). After Epic 11.
- **Package under audit:** the `qml` distribution (`import qml`), `qml/src/qml/**`, READ-ONLY evidence. QML is an application-layer library built ON QMF (AD-2 / L11), never a QMF roster package.
- **Epic thesis (from epics.md §Epic 12 + QL-1..QL-10):** *One runtime protocol both hosts drive per evaluation instant, and a two-layer conformance gate that is **technical, never performance** — the ticket into governed evidence citation and Book seats, and into nothing else. Ungoverned plain-Python bots keep full tunnel access throughout; the bot never sizes, never sets its own full-loss price, never reads a clock, and is never handed a Book module.*

### Provenance & reconstruction note (load-bearing — read before trusting section numbering)

The two authority files named in the lane brief —
`_bmad-output/test-artifacts/test-design-qa.md` (the Per-Epic Test Plan Template + the L0–L6 test-level architecture) and
`_bmad-output/test-artifacts/test-design/QMX-handoff.md` (the 15 P0/P1 assertions + this epic's risk-gate rows) —
**do not exist in this worktree** (confirmed by full-tree search; the entire `_bmad-output/test-artifacts/` tree is absent, matching what every sibling PLAN — epic_02, epic_10, epic_13, epic_14 — records). This plan therefore **reconstructs** the 8-section template and the L0–L6 architecture from the ratified authority that *is* present: the per-epic shape used by the sibling plans, `docs/lenses/testing/test-strategy.md` (`LENS-TEST-STRATEGY`, status: ratified — its six Test-levels, the Contract-test matrix, the Law/authority matrix, the FM convention), and `docs/components/qml.md` (`COMP-QML`, ratified — QL-1..QL-10 and FM-1..FM-12). The **risk-gate rows R-009 and R-011** and the **P0 assertion set** are taken from the **task brief** and bound to the ratified spine, not cross-checked against the missing handoff. The absence is recorded as **finding-candidate GAP-QA-01** in §8.

**Section-4 discipline honoured.** Section 4 (the independent test list) was authored **in full from requirements only** — the Epic 12 slice of `epics.md` (Stories 12.1–12.8), `docs/components/qml.md`, `docs/contracts/{CT-33, CT-34, CT-23, CT-22, CT-28, CT-29, CT-06, CT-16, CT-17, CT-18, CT-04, CT-05, CT-07}`, and `docs/constitution.md` (L11, L27, L30) — **before any `qml/src/**.py` file content was read.** Only the **directory/file names** of the package (a `find` listing, not source) informed the *planned test-target paths* in §6/§7; no source body was opened until §5–§8's reconcile pass. That ordering is the template's core discipline and is preserved here.

---

## 1. Epic scope and requirements binding

| Story / Requirement | Statement (abridged) | Contract / law | QL |
|---|---|---|---|
| **12.1 / FR-050** | The bot runtime protocol: a bot is a **factory** `(declaration, resolved assignment, injected read surfaces) → callback` the host drives per evaluation instant; the callback receives **only the declared footprint's evidence** and returns **zero-or-more CT-23 intents**; the denial set (no sizing, no venue command, no clock, no I/O/network/undeclared randomness); the advisory stop proposal is advisory and the full-loss price is Book-derived single-sited; deterministic replay. | CT-23 v2, AD-33/AD-40, B-2 | QL-7 |
| **12.2 / FR-050** | Bot state **snapshot/restore** as a versioned contract scoped to the tuple `(OS, logic identity + source-manifest fp, protocol format version, arithmetic-reference build)`; round-trip equivalence on an identical tuple; any differing component ⇒ `unavailable dependency`; declared state is bounded. | AD-67 (state), CT-05 | QL-7 |
| **12.3 / FR-048** | The **Layer-1 declaration linter**: schema completeness vs declared format version; every parameter unit-kinded with a valid canonical assignment; every reference resolvable; footprint transitive-union + template completeness; permitted exit-intent kinds within the CT-23 vocabulary; every failure an AD-11 typed refusal, journaled; unknown format version ⇒ `unsupported capability`. | CT-33, CT-34, CT-04, AR-64 | QL-8 |
| **12.4 / FR-048** | The **Layer-2 pure conformance surface**: QML owns (format-versioned, pure) the denial set, static AST/import-scan rules, determinism harness, golden-slice generator (keyed off the declared footprint), and the verdict function; the host owns only spawn+isolation; **host-independent verdict by construction**; determinism/permitted-kind failures ⇒ Layer-2 failure. | CT-33, AR-64 | QL-8 |
| **12.5 / FR-048** | The **host sandbox runner** (V1 enforcement scope): no-clock/no-I/O/no-network enforced by static AST/import scan + capability starvation + host process isolation and **nothing else**; hardened OS-level confinement is a **named deferred dependency**; a dynamically-evasive malicious bot is **out of V1 scope**; a scan-detected clock/fs/network access is a Layer-2 failure **before any process spawns**; the runner owns spawn+isolation, never the verdict. | AR-68, B-5 | QL-8 |
| **12.6 / FR-048** | The **prediction linter** (static, on demand + at seat time against the CT-28 binding context), pinned check list (addable never redefined): (a) footprint satisfies Book `footprint_requirements`; (b) permitted exit kinds ⊆ Book `exit_policy`; (c) family resolves an `exit_policy` entry (explicit or catch-all); (d) stream set ⊆ binding CT-18 venue capabilities; blank requirement passes registration, blocks live binding (thresholds GAP-0048/0049). | CT-28, CT-22 v2, CT-18, AR-66 | QL-8 |
| **12.7 / FR-048 + FR-050** | **Gate registration on both layers**: the Bot kind mints **only if both Layer 1 and Layer 2 pass**, else `policy rejection`, **no partial/probationary**; registration is the ticket into governed evidence (CT-32) citation and seats, **never tunnel entry**; ungoverned plain-Python bots keep full tunnel access; `max_acceptable_complexity_score` **not revived**; **the host composition root holds the WriterId and mints (AD-25 root-mints); qml returns only fingerprintable content + the pass/fail verdict, never a stamped record.** | CT-33, ADR-0018, AD-25 | QL-8 |
| **12.8 / FR-047 + FR-050** | Ship **one complete conformant bot** in `examples/` (CT-33 declaration + plain-Python logic) that passes **both** layers and mints the Bot kind — a tier-1 reference-usage artifact (L27); driven per instant it consumes only its footprint's evidence, emits only permitted CT-23 kinds with an advisory stop on entry, is deterministic, and carries **no** exit-logic field, no sizing, no clock, no I/O. | L27, CT-33, CT-34 | QL-8 |

**Constitution laws in scope:** **L11** (QMF is the framework umbrella; QML is the Bot-oriented *library* built ON QMF — never a framework/engine/kernel/roster package). **L27** (every factory-built component ships executable tests **and reference usage** demonstrating its public contract — Story 12.8 is the L27 artifact). **L30** (default-deny inter-library edges, **roster-scoped** per the 2026-08-21 annotation: an application-layer product ON QMF may consume `qmf-risk`/`qmf-core`/`qmf-registry`, but **never imports `qmf-venue`**; impure steps ride the app's own composition root).

**Architecture rules / decisions in scope (from epics.md + COMP-QML):** **AR-64** (both conformance layers must pass before a Bot mints), **AR-65** (one runtime protocol, both hosts), **AR-66** (prediction linter at bind time), **AR-67** (state snapshot/restore tuple scoping), **AR-68** (V1 enforcement = static scan + capability starvation + process isolation, OS-confinement deferred), **AD-25** (root-mints: the host holds the WriterId, qml returns content+verdict), **AD-33/AD-40** (Book-resolved `requested_r` and frozen R; the bot never sizes), **AD-16/AD-22/AD-30** (record identity carve-out, producer templates, template/version-graph discipline), **DEC-0171..0185** (the QML sitting), notably **DEC-0177** (protocol; advisory stop; Book-side single-sited full-loss), **DEC-0178** (two layers + ticket; technical-never-performance; complexity gate dropped), **DEC-0182** (CT-23 v2 advisory-stop field), **DEC-0185** (operator veto round: NO inbound-refusal posture for a bot's advisory stop; the adopt-the-bot's-advisory-stop Book mode; `qml` CLI ruled out).

**Component authority boundary (`COMP-QML` "May never") → negative assertions:** never a roster package / framework / engine / kernel / cross-component contract layer; **never mint a new CT-\* shared contract** (the runtime protocol and conformance contract are QML-local on QML's own AD-5 ladder); **never import `qmf-venue`**; **never spawn a thread, perform I/O, or spawn a process in the pure library** (every impure step — registration writes, sandbox execution — is host-owned); **never let a bot size, touch venue commands, read a clock, do I/O/network/undeclared randomness, or be handed a Book module**; **never carry an `exit_logic` field on the Bot definition**; **never gate on performance** (no `max_acceptable_complexity_score`); **never gate ungoverned bots' tunnel entry** (conformance gates citation + seats only); **never add the CT-22 admission-bar / `footprint_requirements` fields as a silent addition** (only via the CT-22 format mint).

**The two Tier-1 registry-lane findings this lane must adjudicate (task directive).** Epic 2's `findings.csv` filed **E2-F01** and **E2-F02** against **FR-048 / CT-33** — "no both-conformance-layers mint path on the `qmf.registry` surface" and "no CT-33 bot-definition kind / cardinality / transitive-union rule in `qmf.registry`." **`epics.md` assigns FR-048 to Epic 12, not Epic 2** (Epic 2's own L6-REVIEW W2 already flags this mis-binding). Those two findings are **out of scope for Epic 2** and are re-adjudicated here (verdict recorded in §8, item **A**): the question is whether **QML** owns and realizes the two-layer verdict + the "policy rejection on either fail" decision (Epic 12 territory — assertions E12-L1-03, E12-L3-02), while the **registry record mint** is legitimately **defined-unwired at the AD-25 composition root** (not a `qml` or `qmf-registry` defect).

---

## 2. Risk assessment, priorities, and risk-gate rows

Priority scale: **P0** (a defect lets an unconformant/ungoverned bot be cited by governed evidence or take a live/paper seat, OR lets a bot breach the sizing / full-loss / determinism boundary that keeps R single-authored) → **P3** (cosmetic). Epic 12 is disproportionately P0 because conformance is the **governance gate** into evidence citation and seats.

| # | Risk (probability × impact) | Pri | Where it lives | Planned coverage |
|---|---|---|---|---|
| **R-009** (brief) | **The conformance gate admits a bot that has not passed BOTH layers**, or the gate leaks its scope — gating *tunnel entry* or gating on *performance/complexity* rather than technical conformance; a `pending`/blank admission-bar threshold silently *passes as satisfied* instead of blocking live binding. | **P0** | `conformance/registration.py`, `conformance/layer1.py`, `conformance/layer2.py`, `conformance/prediction.py` | E12-L1-03, **E12-L3-02**, E12-L2-02/03, **E12-L2-13**, E12-L3-07/08/11 |
| **R-011** (brief) | **The QL-7 authority boundary is breached** — a bot sizes (inbound `requested_r` accepted), supplies its own full-loss price through a bot-side channel, reads a clock / does I/O / network / undeclared randomness, is handed a Book module, or is non-deterministic; the door admits a non-entry/non-exit family. | **P0** | `protocol/factory.py`, `protocol/intents.py`, `protocol/evidence.py`, `conformance/scan.py`, `conformance/slice.py` | **E12-L1-01/02**, **E12-L3-04**, **E12-L2-01**, E12-L2-05/06 |
| R-12a | A footprint's producer-binding set is not the transitive union of cited confluence-leg + bot-direct producers, so the bot consumes evidence it never declared (comparability/lineage broken). | **P0** | `footprint/manifest.py`, `footprint/template.py`, `declaration/confluence.py` | **E12-L2-04**, E12-L2-11, E12-L2-07 |
| R-12b | Identical logic source yields two Bot `fp1` (wheel-byte identity), or a header/occurrence field leaks into `fp1`, or a tuned assignment silently wears the original's track record. | **P0** | `declaration/bot.py`, `declaration/versioning.py` | E12-L2-08, E12-L2-09 |
| R-12c | Snapshot/restore succeeds across a differing tuple (OS / logic identity / protocol version / arithmetic build) — a "restored bot" that is not the same bot on the same substrate. | P1 | `protocol/state.py` | E12-L1-07, E12-L3-09, E12-L2-10 |
| R-12d | A Layer-1 refusal is *raised* (not returned) across the seam, or is swallowed / best-effort-passed instead of journaled. | P1 | `_refuse.py`, `conformance/layer1.py` | E12-L1-08, E12-L3-03 |
| R-12e | QML imports `qmf-venue`, mints a new CT-\* contract, or the pure library performs I/O / spawns a process/thread outside the host runner. | P1 | package deps, `host/` | E12-L0-01, E12-L0-02, E12-L0-03 |
| R-12f | The Layer-2 **verdict** is computed inside the impure host runner (host-dependent), rather than by QML's pure verdict function fed by the runner's results. | P1 | `conformance/contract.py`, `host/runner.py` | E12-L3-10, E12-L2-02 |

**P0 ship-blocking assertions binding this epic** (derived from the brief's epic priorities + the ratified spine; provenance-flagged per GAP-QA-01):
- **P0-Q1 — Both-layers gate.** The Bot mints **only when both Layer 1 and Layer 2 pass**; either fail ⇒ `policy rejection`; no partial/probationary. (FR-048, QL-8, DEC-0178, AR-64.) Bound to R-009.
- **P0-Q2 — Technical-never-performance, ticket-scope.** Conformance gates **evidence citation and seats only, never tunnel entry**, and exposes **no** performance/complexity input as a registration gate. (FR-048, QL-8, DEC-0178.) Bound to R-009.
- **P0-Q3 — Book-side single-sited full-loss / no bot sizing.** The protocol supplies **no bot-side full-loss channel** (bot carries only `advisory_stop_proposal`; `declared_full_loss_price` is Book-derived at the door via the per-family `ExitLogicRef`; no Book module injected), and an **inbound `requested_r` is `invalid input`.** (QL-7, CT-23 v2, DEC-0177/0182/0185.) Bound to R-011.
- **P0-Q4 — Determinism + host-independent verdict.** Identical `(declaration, assignment, evidence sequence, state)` ⇒ identical intents; the same bot through two hosts ⇒ identical verdict. (QL-7, QL-8, B-2, DEC-0177/0178.) Bound to R-011/R-12f.
- **P0-Q5 — Footprint transitive-union completeness.** A confluence-leg producer absent from the footprint is a Layer-1 refusal. (QL-4, CT-33, DEC-0174, FM-1.) Bound to R-12a.

---

## 3. Test-level architecture and routing (L0–L6; one behaviour, one level, lower level wins)

Reconstructed from `LENS-TEST-STRATEGY` "Test levels" (six ratified rows) mapped onto the brief's L0–L6 spine plus the QA lane's L6 review level:

| L | Name | In this T2 plan? | Scope for Epic 12 |
|---|---|---|---|
| **L0** | Static & purity gates | **Yes (lean)** | Import graph (never `qmf-venue`; nothing imports `qml`); pure-library purity (no thread/I/O/process-spawn outside `qml.host`); QML-local (non-CT) contract versioning. |
| **L1** | Unit — **targeted only** | **Yes (targeted)** | The highest-consequence boundary decisions driven through public seams with injected verdicts: inbound-`requested_r` refusal, non-entry/exit family rejection, the both-layers gate decision, unit-kind/format-version/family-cardinality refusals, returned-not-raised typed refusals. |
| **L2** | Property / invariant | **Yes (core)** | ∀-style invariants: determinism, host-independent verdict, transitive-union completeness, footprint-only evidence, denial-set scan, source-manifest identity, versioning identity, technical-never-performance absence-invariant. |
| **L3** | Contract (tier 2) | **Yes (core)** | The QML-local runtime-protocol + conformance contract boundaries, and CT-33/CT-34/CT-23 v2/CT-22 v2 shape conformance **as authored**, in an isolated per-package env. **Defined-unwired kinds are asserted shape-only — never wired into a passing mint.** |
| **L4** | Integration (wired) | **No — out of tier** | A real registry-persisted Bot mint is **defined-unwired at the AD-25 composition root**; the host that mints is QMB Story 14.8 / the trading node, not the `qml` package. No realized in-package wired path exists — recorded in §8-A, not silently skipped. |
| **L5** | Acceptance scenario | **No — out of tier** | An end-to-end seat/citation chain needs the wired composition root + a live Book/registry — node/QMB territory (SCN-0012 replay is Epic 14). Out of scope here; the example-bot end-to-end (E12-L3-12) is the strongest in-package proxy. |
| **L6** | Requirements-fidelity review | **Yes** | One adversarial review pass over the authored tests + `qml` source: *does each test assert what the requirement demands, or what the code happens to do?* Deliverable: `L6-REVIEW.md`. |

**Routing rule applied — one behaviour, one level, lowest that can prove it wins.** Consequences for Epic 12:
- "identical inputs ⇒ identical intents" and "verdict host-independent" are **properties → L2** (not re-asserted at L3).
- "both layers ⇒ mint, else policy rejection" is a single **gate decision → L1** (E12-L1-03) with the **contract-boundary** face (all four pass/fail combinations + "content-not-record returned") at **L3** (E12-L3-02) — the L3 row adds only the return-shape proof, not the gate logic.
- Denial-set enforcement is a **property → L2** (E12-L2-06, scan over generated logic); the single "inbound `requested_r` refused" and "venue-command family rejected" decisions are **units → L1**.
- The CT-33/CT-34 registry kinds are **defined-unwired** — provable only **shape-only at L3**; their real mint is L4 and is out of tier (§8-A).

---

## 4. Independent test list (authored from requirements, before any src read)

Each row: ID · level · priority · assertion (what the requirement demands, not what the code does) · requirement trace. IDs are stable planning handles.

### L0 — Static & purity gates (planned: 3)
- **E12-L0-01** · P1 · `qml` imports only `qmf.core`, `qmf.registry`, and `qmf.risk` (CT-23/CT-29 types); it **never imports `qmf.venue`**, and no QMF roster package imports `qml`. — L30 (roster-scoped), DEC-0171/0180
- **E12-L0-02** · P1 · The pure library performs **no thread spawn, no I/O, and no process spawn** — the only impure step (process spawning/isolation for the sandbox) lives under `qml.host`, host-owned; the protocol contract and conformance verdict surfaces are pure. — AD-15, DEC-0171/0178, COMP-QML "May never"
- **E12-L0-03** · P2 · The runtime protocol and conformance contracts are **QML-local, format-versioned on QML's own AD-5 ladder, not CT-numbered**; `qml` mints no new `CT-*` shared contract. — DEC-0171/0177

### L1 — Targeted unit (planned: 8)
- **E12-L1-01** · **P0** · An **inbound `requested_r`** on an intent through the door is **`invalid input`** — the bot may not size; only the Book-resolved value sizes. — **P0-Q3**, QL-7, CT-23, DEC-0147/0154
- **E12-L1-02** · **P0** · An intent that is **not** of the `entry`/`exit` families — a venue command, or a `close_partial` exit kind — is **rejected** (`unsupported capability` for `close_partial`; the door carries only the two families). — QL-7, CT-23, Story 12.1, DEC-0148
- **E12-L1-03** · **P0** · The registration gate returns a **pass verdict only when both Layer-1 and Layer-2 verdicts pass**; pass/fail, fail/pass, and fail/fail each return **`policy rejection`**; there is no partial/probationary outcome. (Verdicts injected.) — **P0-Q1**, FR-048, QL-8, AR-64, DEC-0178, FM-4
- **E12-L1-04** · P1 · A declaration naming a permitted **exit-intent kind outside** the ratified CT-23 vocabulary (`close_full | tighten_protective_stop`) is a Layer-1 **`invalid input`**; `entry` is never declared or gated here. — FR-048, QL-8, CT-33, CT-23, FM-3
- **E12-L1-05** · P1 · An **unknown declaration contract format version** is an **`unsupported capability`** refusal at Layer 1, never a best-effort read. — QL-8, CT-33, FM-12
- **E12-L1-06** · P1 · A declaration with **`strategy_family_id` cardinality ≠ exactly one** (zero, or more than one) is **`invalid input`**. — QL-6, CT-33, DEC-0176, FM-10
- **E12-L1-07** · P1 · A **restore across a differing tuple component** (OS / logic identity + source-manifest fp / protocol format version / arithmetic-reference build) is an **`unavailable dependency`** refusal — scoped to the exact tuple, never best-effort. — QL-7, Story 12.2, AR-67, FM-6
- **E12-L1-08** · P1 · Every Layer-1 failure is a **returned** AD-11 typed refusal (`invalid input | unsupported capability | unavailable dependency`) — never raised across the public seam — and is journaled, never swallowed. — CT-04, QL-8, Story 12.3, DEC-0109

### L2 — Property / invariant (planned: 13)
- **E12-L2-01** · **P0** · ∀ `(declaration, assignment, evidence sequence, state)`: replay yields **identical intents** — deterministic golden-slice (B-2 property). — **P0-Q4**, QL-7, DEC-0177
- **E12-L2-02** · **P0** · ∀ bots run through **two different hosts**: the conformance **verdict is identical** — host-independent by construction, with no Book present. — **P0-Q4**, QL-8, DEC-0178
- **E12-L2-03** · **P0** · ∀ conformance runs where a golden slice yields **differing intents on two runs** OR a **non-permitted intent kind** is emitted: the Layer-2 verdict is a **conformance failure**. — QL-8, DEC-0177/0178, FM-5
- **E12-L2-04** · **P0** · ∀ footprints: the producer-binding set **MUST equal the transitive union** of every cited confluence's leg producers + bot-direct producers; a confluence-leg producer **absent from the footprint** ⇒ Layer-1 refusal. — **P0-Q5**, QL-4, CT-33, DEC-0174, FM-1
- **E12-L2-05** · **P0** · ∀ callback invocations: the bot receives **only its declared footprint's evidence** (presence-mapped series per AD-22, structure lifecycle folds per AD-25, each sample carrying its knowable-at instant); undeclared evidence is never delivered. — QL-7, CT-33, Story 12.1
- **E12-L2-06** · **P0** · ∀ bot logic: a **clock read, filesystem access, network import, or undeclared randomness** is flagged by the static AST/import scan as a Layer-2 failure **before any process is spawned**. — QL-8, AR-68, DEC-0178, Story 12.5, FM-5
- **E12-L2-07** · P1 · ∀ producer **templates**: an omitted AD-22 identity field is a Layer-1 refusal; template resolution is a **total, single-valued function** producing one deterministic CT-16/CT-17 fingerprint (identical canonical runs fingerprint identically). — QL-4, CT-33, DEC-0174, FM-2
- **E12-L2-08** · **P0** · ∀ identical logic source built in two sandboxes: **one Bot `fp1`** — logic identity is the reproducible **source-manifest fingerprint over the source tree, never wheel/built-artifact bytes**; the AD-16 header's `writer`/`sequence`/`stable id`/`created-at` are excluded from `fp1`. — CT-33, DEC-0172/0173, AD-16, FM-10
- **E12-L2-09** · **P0** · ∀ Bot definitions: identity is **semantic content only** (the six groups) + format version + at-birth refs; a changed default / leg / footprint entry / logic artifact mints a **new** `fp1`, while re-binding, seats, and paper flips **never** mint a new Bot. — CT-33, DEC-0173, AD-30
- **E12-L2-10** · P1 · ∀ snapshot/restore on an **identical tuple**: the round-trip is **equivalent** (identical continued intents); bot state is **bounded and declared** — exceeding the declared bound is a Layer-2 concern; a restored-state fingerprint enters downstream labels. — QL-7, Story 12.2, AR-67
- **E12-L2-11** · **P0** · ∀ CT-34 confluences: **at least one leg of any role mix** (never one-of-each, never zero legs); a leg carries a producer binding and/or a child-confluence cite (≥1 required, role mandatory); **every leg producer of every cited (nested) confluence reaches the citing bot's footprint** (transitive-union). — CT-34, QL-5, DEC-0175, FM-1
- **E12-L2-12** · P1 · ∀ declared parameters: each carries an **AD-40 unit-kind** (missing ⇒ `invalid input`); bounds/step/default are exact rationals or scaled integers (**no binary float** anywhere); the mandatory defaults together form the canonical assignment. — CT-33, DEC-0154, AD-40
- **E12-L2-13** · **P0** · **Technical-never-performance, ticket-scope invariant:** the conformance surface exposes **no** performance/complexity input (no `max_acceptable_complexity_score`, no perf metric) as a registration gate, and conformance gates **evidence citation + seats only** — an ungoverned plain-Python bot needs **zero `qml` imports** and retains full tunnel access. — **P0-Q2**, FR-048, QL-8, DEC-0178

### L3 — Contract (Tier 2, owner-conformance, isolated per-package env) (planned: 12)
- **E12-L3-01** · P0 · **Runtime-protocol contract (QML-owned, AD-5) round-trip + boundary:** a conformant bot is a **factory** `(declaration, resolved assignment, injected read surfaces)` returning a **callback** driven per evaluation instant that returns **zero-or-more CT-23 intents**; a factory violating the shape (wrong arity, returns a non-callback, emits a non-CT-23 value) is refused. — QL-7, DEC-0177
- **E12-L3-02** · **P0** · **Both-layers gate as a contract boundary:** pass/pass ⇒ a pass verdict **plus fingerprintable content returned — never a stamped record**; pass/fail, fail/pass, fail/fail ⇒ `policy rejection`. Asserts the AD-25 return shape (content + verdict, not a persisted record). — **P0-Q1**, FR-048, QL-8, CT-33, DEC-0178/AD-25, FM-4
- **E12-L3-03** · P0 · **Layer-1 declaration-linter boundary:** schema completeness vs the declared format version; every parameter unit-kinded with a valid canonical assignment; every reference (family record, confluence fingerprints, producer formulas at their declared format versions, logic distribution) resolvable — an **unresolvable** reference is `unavailable dependency`. — QL-8, CT-33, Story 12.3
- **E12-L3-04** · **P0** · **CT-23 v2 door boundary — no bot-side full-loss channel:** an entry intent carries only the OPTIONAL `advisory_stop_proposal`; `declared_full_loss_price` is **Book-derived at the door** (per-family `ExitLogicRef`) and stamped mirroring `requested_r`; **an inbound `requested_r` is `invalid input`**; a format-2 reader accepts format-1 intents unchanged. *(Framing note per DEC-0185: there is NO inbound-refusal posture on the advisory stop itself — the "refusal of a bot-supplied full-loss price" is structural, the protocol provides no such field, plus the inbound-`requested_r` refusal.)* — **P0-Q3**, QL-7, CT-23 v2, DEC-0177/0182/0185
- **E12-L3-05** · P0 · **CT-33 shape-only (defined-unwired):** bot-definition semantic-content round-trip; the AD-16 header excluded from `fp1`; exactly the six content groups; **no `exit_logic` field**. *Must not turn a defined-unwired slot into a wired mint fixture.* — CT-33, DEC-0173
- **E12-L3-06** · P1 · **CT-34 shape-only:** confluence leg-set round-trip; role vocabulary `level | trigger | confirmation | filter` closed-and-addable; one-or-more legs; a leg carries a producer binding and/or a `confluence_ref` (≥1 required); fingerprint-ascending default, order-significance opt-in and entering the fingerprint only when declared. — CT-34, DEC-0175
- **E12-L3-07** · P0 · **Prediction-linter check list** against an **injected CT-28 binding context** (QML never imports `qmf-venue` — the context is a fixture): (a) footprint satisfies `footprint_requirements`; (b) permitted exit-intent kinds ⊆ Book `exit_policy` permitted kinds; (c) family resolves an `exit_policy` entry (explicit or catch-all); (d) stream set ⊆ binding CT-18 venue capabilities. — QL-8, CT-28, AR-66, Story 12.6
- **E12-L3-08** · P1 · **Prediction-linter default/negative cases:** a **zero-exit-kind Book admits an entry-only bot** (entry never gated); a family resolving **neither** explicit **nor** catch-all **fails** (c); a stream set **exceeding** venue capabilities **fails** (d) at bind time (AD-29). — QL-8, DEC-0176/0178, FM-7/FM-8/FM-9
- **E12-L3-09** · P1 · **State snapshot/restore contract:** round-trip equivalence on an identical tuple; a differing tuple component ⇒ `unavailable dependency`; the restored-state fingerprint enters downstream labels. — QL-7, Story 12.2, AR-67, FM-6
- **E12-L3-10** · P1 · **Layer-2 pure-surface split:** QML owns (pure, format-versioned) the denial set, static AST/import-scan rules, determinism harness, golden-slice generator, and **verdict function**; the host runner owns **only spawn + isolation** and feeds results to the verdict function — **the verdict never lives in the runner** (host-independence by construction). — QL-8, AR-68, DEC-0178, Story 12.4/12.5
- **E12-L3-11** · P1 · **CT-22 v2 / admission-bar interface boundary:** the two `evidence_requirements` fields (a registered-conformant-Bot cite; canonical-assignment evidence) and the `footprint_requirements` shape land **only via the CT-22 format mint** — never as a silent AD-30 field addition an old parser would ignore; a **blank** requirement **passes registration but blocks live binding** (thresholds stay GAP-0048/0049). — QL-8, CT-22 v2, DEC-0181, FM-11/FM-12
- **E12-L3-12** · **P0** · **Example conformant bot (L27) end-to-end within tier:** the shipped `qml/examples/conformant_bot` **passes both Layer 1 and Layer 2**; inspection confirms one family, ≥1 CT-34 confluence, a unit-kinded parameter space with a canonical assignment, a complete footprint, and a permitted exit-intent declaration; it carries **no** `exit_logic` field, does **not** size, read a clock, or perform I/O; driven per instant it emits **only** permitted CT-23 kinds with an advisory stop on entry and is deterministic under the golden slice. — Story 12.8, L27, FR-047/FR-050, CT-33

### L6 — Requirements-fidelity review (planned: 1 review pass; deliverable `L6-REVIEW.md`)
- **E12-L6-01** · One adversarial pass over the authored tests and the `qml` source. Per-test question: *does it assert what the requirement demands, or what the code happens to do?* Mandatory focus checks:
  - **(a)** No test manufactures an **admission-bar / `footprint_requirement` threshold** (GAP-0048/0049) into a passing fixture (DEC-0004: naming a GAP preserves uncertainty, never satisfies a gate).
  - **(b)** No test turns the **defined-unwired CT-33 registry mint** into a wired pass — CT-33/CT-34 are asserted shape-only.
  - **(c)** The "refuses a bot-supplied full-loss price" assertion (E12-L3-04) is framed **structurally** (no bot-side channel + inbound-`requested_r` refusal), **not** as a non-existent inbound-refusal on the advisory stop (DEC-0185).
  - **(d)** Conformance is asserted to gate **citation + seats only, never tunnel entry**, and **never performance/complexity** (E12-L2-13).
  - **(e)** Determinism/host-independence assertions run the **pure verdict function**, not the impure host runner, for the verdict.
  - **(f)** The two Tier-1 registry findings **E2-F01/E2-F02** are re-bound to Epic 12 and resolved to the correct verdict (QML owns the two-layer verdict; the mint is AD-25 root-territory, defined-unwired).

**Planned executable totals: L0 = 3 · L1 = 8 · L2 = 13 · L3 = 12 → 36 assertions**, plus **1 L6 review pass** (six focus checks). L4/L5 carry **0** by ratified out-of-tier reason (§8-A).

---

## 5. Coverage & traceability matrix

Every acceptance criterion of Stories 12.1–12.8 is covered by at least one L2 or L3 assertion (the T2 mandate), most with a targeted L1 or L0 adjunct.

| Story / AC theme | Assertions | Lowest level |
|---|---|---|
| 12.1 factory shape + per-instant callback + CT-23 out | E12-L3-01 · E12-L2-05 | L2 |
| 12.1 denial set (no size/venue/clock/IO/net/rand) | E12-L1-01,02 · **E12-L2-06** | L1 |
| 12.1 advisory stop / Book-side full-loss / no Book module | **E12-L3-04** | L3 |
| 12.1 deterministic replay | **E12-L2-01** | L2 |
| 12.1 size/venue-command through door rejected | E12-L1-01,02 | L1 |
| 12.2 snapshot/restore round-trip + fingerprint in labels | E12-L2-10 · E12-L3-09 | L2 |
| 12.2 differing-tuple restore ⇒ unavailable dependency | E12-L1-07 · E12-L3-09 | L1 |
| 12.2 declared state bound enforced (Layer-2) | E12-L2-10 | L2 |
| 12.3 Layer-1 schema/unit-kind/reference resolvability | E12-L3-03 · E12-L2-12 · E12-L1-05,06 | L1 |
| 12.3 footprint transitive-union + template completeness | **E12-L2-04** · E12-L2-07,11 | L2 |
| 12.3 permitted exit kinds ⊆ CT-23 vocab | E12-L1-04 | L1 |
| 12.3 every failure a journaled AD-11 typed refusal | E12-L1-08 | L1 |
| 12.4 QML-owned pure surface split; host feeds verdict | E12-L3-10 · **E12-L2-02** | L2 |
| 12.4 golden-slice generator keyed off footprint | E12-L2-01 · E12-L3-12 | L2 |
| 12.4 suite asserts load-isolation/determinism/permitted-kind/state-bound | E12-L2-03 · E12-L3-12 | L2 |
| 12.4 same bot two hosts ⇒ identical verdict | **E12-L2-02** | L2 |
| 12.4 non-determinism / non-permitted kind ⇒ Layer-2 failure | **E12-L2-03** | L2 |
| 12.5 V1 enforcement = scan + starvation + isolation only | E12-L2-06 · E12-L3-10 | L2 |
| 12.5 scan catches clock/fs/net before spawn | **E12-L2-06** | L2 |
| 12.5 runner owns spawn+isolation, never the verdict | E12-L3-10 · E12-L0-02 | L3 |
| 12.5 OS-confinement deferred / malicious bot out of scope | — **§8-C (untestable-positive)** | — |
| 12.6 prediction-linter check list (a)(b)(c)(d) | **E12-L3-07** | L3 |
| 12.6 zero-exit-kind Book admits entry-only; (c)/(d) failures | E12-L3-08 | L3 |
| 12.6 blank requirement passes registration, blocks binding | E12-L3-11 · **§8-D** | L3 |
| 12.7 both layers ⇒ mint, else policy rejection, no partial | **E12-L1-03 · E12-L3-02** | L1 |
| 12.7 citation+seats valid; never tunnel entry; never performance | **E12-L2-13** | L2 |
| 12.7 ungoverned plain-Python keeps tunnel access | E12-L2-13 · E12-L0-01 | L2 |
| 12.7 graduation mints two artifacts + lineage edge to research | E12-L3-05/06 (shape) · **§8-E (edge realization)** | L3 |
| 12.7 `max_acceptable_complexity_score` not revived | **E12-L2-13** | L2 |
| 12.7 root holds WriterId & mints; qml returns content+verdict | **E12-L3-02** · **§8-A** | L3 |
| 12.8 one complete conformant bot passes both layers (L27) | **E12-L3-12** | L3 |
| 12.8 example: no size/clock/IO/exit_logic; only permitted intents | E12-L3-12 | L3 |
| L11 QML is a library, not framework/roster | E12-L0-01,03 | L0 |
| L27 reference usage shipped | E12-L3-12 | L3 |
| L30 never imports qmf-venue; pure library | E12-L0-01,02 | L0 |
| FM-1 footprint ≠ transitive union | E12-L2-04,11 | L2 |
| FM-2 template missing identity field | E12-L2-07 | L2 |
| FM-3 exit kind outside vocab | E12-L1-04 | L1 |
| FM-4 registration fails either layer | E12-L1-03 · E12-L3-02 | L1 |
| FM-5 non-deterministic / non-permitted kind | E12-L2-03,06 | L2 |
| FM-6 restore across differing tuple | E12-L1-07 · E12-L3-09 | L1 |
| FM-7/8/9 prediction-linter failures | E12-L3-08 | L3 |
| FM-10 two family ids / wheel-byte identity | E12-L1-06 · E12-L2-08 | L1 |
| FM-11 non-canonical run as canonical evidence | E12-L3-11 | L3 |
| FM-12 format-1 reader vs format-2 / silent field add | E12-L1-05 · E12-L3-04,11 | L1 |

Every FR/story-AC and FM-1..FM-12 has at least one planned L2/L3 assertion **except** the OS-confinement/malicious-bot AC (12.5, §8-C untestable-positive), the admission-bar/footprint threshold VALUES (§8-D), the CT-33 registry mint wiring (§8-A), and the graduation lineage-edge realization (§8-E) — each recorded in §8, none silently skipped. No coverage percentage substitutes for a behaviour assertion.

---

## 6. Fixtures, data, and environment

- **Runner:** `uv run` from the worktree root (its `.venv` has the dev group synced). Property tests (L2) need hypothesis: `uv run --with hypothesis pytest qa/tests/epic_12 -q`. Confirm whether hypothesis is already a `qml` test dep during the reconcile pass; if not, L2 is a net-new addition run via `--with`.
- **Test home:** planned targets under `qa/tests/epic_12/` (created at execution time), one file per level/theme, e.g. `test_l0_static.py`, `test_l1_protocol_boundary.py`, `test_l1_gate.py`, `test_l2_determinism.py`, `test_l2_footprint.py`, `test_l3_conformance_contract.py`, `test_l3_prediction.py`, `test_l3_example_bot.py`. (Module/dir names below were read as a directory listing only — no source body was opened before §4.)
- **Public surface to drive (from the `qml` module tree, for test authoring only — not yet read):** `qml.protocol` (factory, evidence, intents, state, contract); `qml.conformance` (layer1, layer2, prediction, scan, slice, harness, contract, registration); `qml.declaration` (bot, confluence, parameters, versioning); `qml.footprint` (manifest, template, horizon, vocab); `qml.host` (runner, worker — the impure host-owned sandbox runner); `qml._refuse`. Tests assert through public seams (`qml.__init__` exports), never private helpers.
- **Injected verdicts (L1-03, L3-02):** conformance-layer verdicts are **injected** (pass/pass, pass/fail, fail/pass, fail/fail) so the gate decision is exercised without building a real QL-8 sandbox run — the both-layers logic is the unit under test.
- **Injected binding context (L3-07/08):** the CT-28 binding context (Book `footprint_requirements` / `exit_policy` / declared CT-18 venue capabilities) is a **fixture** — QML never imports `qmf-venue`; the prediction linter reads a supplied context object, so no venue integration is stood up.
- **Golden-slice / determinism (L2-01/02/03, L3-12):** drive the golden-slice generator off a declared footprint, run twice, assert identical intents; run the same bot through two distinct host stubs and assert one verdict. A declared RNG seed is used for any hypothesis run so failures reproduce.
- **Denial-set scan (L2-06):** feed the static AST/import scanner generated logic snippets that read a clock / open a file / import a network module / call unseeded `random` and assert a **Layer-2 failure before any process spawns** (pure-scan path, no `qml.host` process).
- **Example-bot fixture (L3-12):** the real `qml/examples/conformant_bot` is the input — run both layers against it; this is the strongest in-package proxy for the (out-of-tier) wired mint.
- **Refusal assertions:** assert the returned `TypedRefusal.category` and `context`, **never** a parsed exception message (DEC-0109). A failure-mode proof that observes a **raised** exception across the seam is itself a **finding**.
- **Injected clock (never system clock):** the evaluation instant rides the callback (QL-7); any test needing time injects it — no test reads the system clock (AR-16).
- **Synthetic-data limit:** synthetic fixtures may exercise the protocol and conformance machinery but may never be cited as proof of trading edge (DEC-0007/0054).

---

## 7. Execution plan and tooling

1. **L0** — import-graph + purity + QML-local-contract-versioning gates (`uv run poe types` semantics + a targeted import test). Cheapest, run first: a `qmf-venue` import here voids the boundary.
2. **L1 + L2** — targeted unit + property (`uv run --with hypothesis pytest qa/tests/epic_12 -q`), coverage measured against the 80% floor (no CT-01/CT-02 primitive module lives in this epic, so no 100%-branch module here).
3. **L3** — contract, **each package in an isolated per-package environment** so an undeclared import fails rather than resolving through the shared workspace venv (`poe check-integration` semantics). Defined-unwired CT-33/CT-34 asserted **shape-only**.
4. **L3-12** — run both layers against the shipped example bot (the in-package end-to-end proxy for the out-of-tier wired mint).
5. **L6** — the requirements-fidelity review pass → `L6-REVIEW.md` (six focus checks in §4).
- **Order matters** only in that a red L1 denial-set/gate assertion makes higher-level results uninterpretable; run low→high and record findings at the lowest failing level.
- **Discipline (binding):** source is READ-ONLY evidence. A failing planned assertion is a **FINDING to record against the requirement** — never a source edit and never a weakened test. Tests assert what the contracts and constitution demand, not what the code happens to do. A test that manufactures a defined-unwired mint, or a GAP-0048/0049 threshold, into a passing fixture is itself a finding.

---

## 8. Untestable requirements, deferrals & exit criteria

**A. The two Tier-1 registry findings — re-adjudicated verdict (task directive).**
`epics.md` assigns **FR-048 to Epic 12**, not Epic 2; Epic 2's E2-F01/E2-F02 (and its own L6-REVIEW W2) are **mis-bound out of scope for Epic 2**. Verdict in this lane: **there is no single "minting path" that both enforces the two layers and writes the record — by ratified design the responsibility is split.** (1) The **two-layer conformance verdict** and the "policy rejection on either fail, no partial" decision are **QML's** (Epic 12) — `qml.conformance` (`layer1`/`layer2`/`registration`) — and are **realized code, testable now** with injected verdicts (E12-L1-03, E12-L3-02). (2) The **actual CT-33 registry record mint** is **defined-unwired at the AD-25 composition root**: QML returns fingerprintable content + the pass/fail verdict, **never a stamped record**; the host that holds the `WriterId` and writes the record is QMB (Story 14.8, "waits for Epics 12 and 13") or the trading node — **not the `qml` package.** So the registry lane was correct that the **registry package** has no bot-mint path, but wrong to file it against Epic 2 and wrong to read it as a defect: the mint is **root-territory, correctly defined-unwired**. **L4 (a real registry-persisted mint) has no realized in-package surface and is out of this T2 tier** — a coverage-boundary, not a code defect. If, at reconcile, `qml.conformance.registration` is found to itself **stamp/persist a record** (rather than return content + verdict), that inverts AD-25 and is a **P0 FINDING**.

**B. L4/L5 out-of-tier by ratified reason.** Wired integration (L4) and the end-to-end seat/citation acceptance chain (L5) both require the wired composition root + a live Book/registry, which are node/QMB territory and defined-unwired here. The example-bot end-to-end (E12-L3-12) is the strongest in-package proxy and is retained; a full L4/L5 pass is deferred to the host epic (QMB 14.8 / node sitting), recorded, not skipped.

**C. Hardened OS-level sandbox confinement — untestable-positive in V1 (AR-68 / DEC-0178).** V1 promises **only** static AST/import scanning + capability starvation + host process isolation; restricted tokens/job objects (Windows) and seccomp-class (Linux) are a **named deferred dependency of the node/platform sitting**, and a **dynamically-evasive malicious bot is explicitly out of V1's threat model** (bots are operator- or operator's-agent-authored). Therefore "the sandbox actually prevents a determined malicious bot from reaching a clock/network at the OS level" **cannot be asserted** in V1 — only the scan/starvation/isolation behaviours (E12-L2-06, E12-L3-10) are testable. A test claiming OS-level confinement would be a **finding**, not coverage.

**D. Admission-bar / `footprint_requirement` threshold VALUES — untestable-positive (GAP-0048/0049).** QL-8 ships the **interfaces only**; no threshold value is ruled. The testable behaviour is that a **blank** requirement **passes registration but blocks live binding** (E12-L3-11) and that the two fields land only via the CT-22 format mint. The **threshold itself cannot be tested** (no ratified value); a test that manufactures a threshold into a passing fixture is a finding (DEC-0004).

**E. Graduation lineage edge (Story 12.7 AC4).** An ungoverned experiment graduating by minting the two artifacts with a **CT-07 `branches-from`/graduation edge back to its originating research artifact** is testable at **shape level** (the author-side helper produces the edge), but the edge's **persistence** rides the same defined-unwired composition-root mint as §8-A. Assert the authored edge shape; flag the persisted-edge realization for the host epic; verify in the L6 pass that no test fakes a persisted graduation edge.

**F. Prediction-linter check (d) as a LIVE venue integration.** CT-18 venue capabilities are read **through** the CT-28 binding context; CT-18/CT-28 are defined-unwired `qmf-venue`/`qmf-risk` surface and **QML never imports `qmf-venue`.** Check (d) is therefore testable **only with an injected binding context** (E12-L3-07/08), never as a wired venue integration — recorded, not skipped.

**G. Live seat-time runtime enforcement** (how the node polices footprint reads on a live seat) is **node-sitting territory**; QL-7 states the guarantee, hosts implement it. Out of scope here.

**Process gaps logged as finding-candidates:**
- **GAP-QA-01** — the named authority files `test-design-qa.md` and `QMX-handoff.md` (and the whole `_bmad-output/test-artifacts/` tree) are **absent**; this plan reconstructs the 8-section template and the L0–L6 architecture from `LENS-TEST-STRATEGY` + `COMP-QML`, and takes the risk-gate rows **R-009 / R-011** and the P0 set from the task brief, uncross-checked against the missing handoff. If the files are restored, re-reconcile §1 template order, §2 risk-gate rows, and §3 level definitions against them before executing.

**Exit criteria for the Epic 12 verification run:**
- Every L0–L3 assertion above is executed and each result recorded at its lowest level; each **P0** assertion (E12-L1-01/02/03, E12-L2-01/02/03/04/05/06/08/09/11/13, E12-L3-02/04/12) is **GREEN or carries a written FINDING**.
- The L6 requirements-fidelity pass is delivered as `L6-REVIEW.md` with all six focus checks resolved.
- Coverage ≥ the 80% floor for the `qml` conformance/protocol/declaration/footprint modules (informational; a percentage never substitutes for a behaviour assertion).
- FM-1..FM-12 each resolved to GREEN or FINDING, except FM-relevant OS-confinement (§8-C) and threshold VALUES (§8-D), which exit as **documented-deferral** (must stay unenforced / interface-only).
- The **ship-blocking triad** for this epic — *(i) the Bot passes both layers or is `policy rejection` with no partial state; (ii) conformance gates citation + seats only, never tunnel entry and never performance; (iii) the bot never sizes and never sets its own full-loss price (Book-side single-sited, inbound `requested_r` refused), and is deterministic* — any FINDING on these blocks the epic regardless of other results.
- The §8-A verdict on E2-F01/E2-F02 is recorded in `findings.csv` re-bound to Epic 12 (QML owns the verdict; the mint is AD-25 root-territory defined-unwired), and no test fakes the defined-unwired mint.
