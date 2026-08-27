# Epic 13 — QMB substrate — Verification PLAN (audit tier T1)

> Per-epic verification plan. Eight sections, order load-bearing. **Section 4 (the
> independent test list) was authored entirely from requirements BEFORE any `qmb/`
> source file of this epic's package was opened.** As of authoring, zero files under
> `qmb/` have been read — the whole plan is requirement-derived. Test file paths named
> below are planned targets under `qa/` to be created at execution time.

---

## 1. Epic under test and authorities

- **Epic:** 13 — QMB substrate. **Wave 5, priority H** (per epics.md wave table). **Audit tier:** T1.
- **Package under test:** `qmb/` (one wheel: pure library + `qmb` CLI), module tree
  `runloop/ config/ registryread/ execution/ data/ optimize/ robustness/ results/
  ledger/ orchestrator/ doors/{cli,api,mcp}` (source: `docs/components/qmb.md` structural seed — a doc, not src).
- **What this epic delivers (scope of verification):** the config-compiler half of FR-036 —
  the structural-seed scaffold (13.1); the single library-owned registry-read port over
  immutable fingerprinted as-of sets (13.2); Book/BMS config-fragment materialization as
  derived `fp1` artifacts with CT-07 lineage (13.3); the layered, fixed-precedence run-config
  compiler whose fingerprint is the run id (13.4); the `starting_capital` seed and the
  per-run `world=replay` binding mint (13.5).
- **Explicitly OUT of scope (delivered by later epics, see §7):** the run loop / event slices /
  fills / CT-32 *result* artifact (Epic 14, incl. Story 14.7 golden-slice determinism);
  the orchestrator, ledger writes, governor, process-per-run (Epic 15); door parity as a full
  contract test and the MCP door shipment (Epic 16).

**Authorities consulted (precedence order):**
1. `_bmad-output/planning-artifacts/epics.md` — Epic 13 (stories 13.1–13.5, lines 2723–2862).
2. `docs/` knowledge base: `docs/components/qmb.md` (B-1..B-15 behavior; FM-1..FM-12);
   contracts `ct-22` (Book), `ct-27` (BMS), `ct-28` (Book binding), `ct-32` (performance
   result), `ct-05` (version/fingerprint/fp1 recipe), `ct-07` (lineage edge), `ct-04` (typed
   refusal); `docs/scenarios/SCN-0012-qmb-replay-run.md`; `docs/lenses/testing/fixtures-and-scenarios.md`.
3. **MISSING AUTHORITIES (plan-integrity caveat, see §7.5):** the task named
   `_bmad-output/test-artifacts/test-design-qa.md` (Per-Epic Test Plan Template + L0–L6
   architecture) and `_bmad-output/test-artifacts/test-design/QMX-handoff.md` (15 P0/P1
   assertions + risk-gate rows). **Neither file exists in this worktree.** The 8-section
   template and the L0–L6 level scheme below are reconstructed from the ratified quality-tier
   structure (`docs/lenses/testing/fixtures-and-scenarios.md`, DEC-0101/0102) and the epic
   priorities supplied in the task brief; risk gates **R-004**, **R-008** and **P0 assertion 13**
   are taken verbatim from the task brief.

---

## 2. Requirements inventory and traceability

Every acceptance criterion of Epic 13, keyed to the independent test(s) in §4.

| Story | AC (abbreviated) | Contract / DEC / FM | Test id(s) |
|---|---|---|---|
| 13.1 | ONE wheel, `uv add qmb`, imports `qmb`, pins `click==8.4.2` + `optuna==4.9.0` | B-13, DEC-0167/0168 | T13-001, T13-002 |
| 13.1 | outside qmf roster; depends only on six qmf backends; NO qmf-venue edge | AR-06, B-13 | T13-003 |
| 13.1 | module tree complete; `doors/mcp` scaffolded, not shipped V1 | B-1, SC-08 | T13-004, T13-101 |
| 13.1 | vocabulary law (no engine/kernel/exam/plugin/snapshot-for-registry) | Consistency Conventions | T13-005 |
| 13.1 | QMB SemVer display-only, never identity | AR-26, B-13 | T13-307 |
| 13.1 | Tier-1 gate: ruff + pyright-strict + pytest; no module-global mutable state; pure-Python, OS-neutral | AR-11, AR-04, NFR-02 | T13-006, T13-007 |
| 13.2 | ONE library-owned registry-read port; no door-side/second cache | AR-55, B-15 | T13-201 |
| 13.2 | alias resolves → record by `fp1`; caller cites by fingerprint, never `name@version` | B-13, B-15 | T13-102 |
| 13.2 | superseded ref → AD-11 stale-evidence refusal at `qmb_stale_evidence_severity`, RETURNED | AR-55, B-15, FM-7 | T13-103, T13-308 |
| 13.2 | batch/sweep freezes ONE as-of; thereafter by fingerprint, never `name@latest` | SC-11, B-15 | T13-203 |
| 13.2 | hub is dumb passive storage, not the dead DEC-0084 service; never "snapshot" | B-15 | T13-202, T13-005 |
| 13.3 | Book fragment = schema-valid, fingerprinted DERIVED artifact + CT-07 lineage to CT-22; not a new registry kind, not free-hand-edited | AR-52, B-3 | T13-301 |
| 13.3 | BMS fragment = derived, fingerprinted + CT-07 lineage to CT-27 | AR-52, B-3 | T13-302 |
| 13.3 | **Book/BMS fragment key namespaces DISJOINT** (Book: admission/sizing/exit-door; BMS: accounting/constraints/kill-line/reporting) | B-3, DEC-0143 | **T13-405** |
| 13.3 | fragment stamps AD-5 integer format version; old fragments readable forever | AR-25, B-3 | T13-303 |
| 13.3 | named condition preset is an ordinary config fragment | B-3 | T13-104 |
| 13.4 | layers `flags > run spec > BMS > Book > defaults` → exactly ONE resolved, read-only, schema-valid config; deterministic & pure (byte-identical) | AR-52, B-3 | T13-105, T13-106, **T13-402** |
| 13.4 | **key collision across Book/BMS → compile-time typed refusal; sanctioned overlap ⇒ BMS outranks Book** | B-3, FM-1 | **T13-107**, T13-108 |
| 13.4 | resolved artifact cites Book/BMS/binding by `fp1`, never `name@version`, even from an alias | B-3, B-13 | T13-109, **T13-403** |
| 13.4 | stamps AD-5 format version + AD-10 identity-vs-display classification; **all doors compute the SAME fingerprint = run-id root = ledger key**; written to run output dir named by run id | AR-52, B-3 | T13-204, T13-304, **T13-401**, **T13-404** |
| 13.4 | replay clock bound to synthetic-tainted data → `invalid input` (B-7 wins) | FM-3, SC-06 | T13-110 |
| 13.5 | `starting_capital` mandatory run-spec field (Book may default); seeds virtual ledger | AR-52, B-3 | T13-111, T13-206 |
| 13.5 | seed override flag → binding `seed_overridden`; fold forced `unrated` | B-3, FM-12 | T13-112 |
| 13.5 | mints exactly ONE CT-28 `world=replay` binding; distinct + incomparable to any live binding of the same Book instance | B-3, FR-036 | T13-205, T13-305, T13-306 |
| 13.5 | sizing/R-freeze/exits consume CT-23 inbound / CT-29 exits; AD-40 full-loss price required before any open | B-3, B-6, AR-56 | T13-207, T13-309 (both PARTIAL — see §7) |
| cross | every refusal is a valid CT-04 typed value, returned not raised | CT-04 | T13-308 |
| P0-13 | re-run under resolved config reproduces CT-32 fingerprint or refuses (NFR-03) | DEC-0163, FM-11 | **T13-406** (config-side) + §7.1 (result-side deferred) |

FR/NFR roots: **FR-036** (config-compiler half), **NFR-02** (determinism, no ambient
nondeterminism, pure-Python/OS-neutral), **NFR-03** (reproducibility of identity).

---

## 3. Risk gates and priority assertions

The epic-specific focus. Config identity underlies every run — it is the run's whole identity,
so the gates below are the audit's centre of gravity.

**R-004 — distinct semantic inputs ⇒ distinct `fp1`, no silent overwrite (config `fp1` IS run identity).**
Covered by: **T13-401** (identity-field change ⇒ fp1 change), **T13-402** (identical inputs ⇒
byte-identical fp1 — the converse), **T13-107** (collision refuses, never silently overwrites),
**T13-306** (equal-fingerprint re-binding refuses, no silent idempotent accept), **T13-404**
(display change does not, identity change does, move fp1). The disjointness precondition
**T13-405** guarantees two semantic domains cannot silently alias one key.

**R-008 — every accepted input shape yields the same gate verdict.**
Covered by: **T13-403** (input-shape invariance property: alias vs `fp1`, key ordering, CT-01
canonical rational forms → one resolved `fp1` AND one accept/refuse verdict), reinforced by
**T13-204** (same fingerprint at the run-id-root role) and **T13-109** (alias never leaks
`name@version`). Full cross-door parity is Epic 16 (§7.3); here the gate is single-source
fingerprint agreement.

**P0 assertion 13 — re-running a run id under its resolved config reproduces the CT-32
fingerprint or refuses (NFR-03).**
Epic-13 (config-side) portion covered by **T13-406**: re-resolving a run id under its stored
resolved config reproduces the SAME config `fp1` (the run-id root) or returns a typed refusal on
mismatch. The CT-32 *result*-fingerprint reproduction requires the run loop and is **deferred to
Epic 14 / Story 14.7** (§7.1).

**Config compiler is a complexity hot-spot (stated cyclomatic 36).** The precedence engine and
the disjointness/collision arbitration carry the most branches and the most identity weight, so
they get the densest coverage: **T13-105** (precedence order), **T13-107/T13-108** (collision
refusal + sanctioned BMS-over-Book precedence), **T13-405** (namespace disjointness), plus the
identity properties T13-401/402/403/404. The contract precedence to assert is explicit:
namespaces are DISJOINT; the only sanctioned overlap resolves **BMS outranks Book**; an
unsanctioned collision is a **compile-time typed refusal**, never a silent write.

---

## 4. Independent test list (authored from requirements before reading src)

> This section was written purely from the authorities in §1 (epics.md, contracts, component
> spec, scenario). No `qmb/` source file was read before or during its authoring. Each row
> asserts what the REQUIREMENT demands. A test that fails is a FINDING; source is read-only
> evidence and is never edited to make a test pass.

### 4.0 Static / build gate (L0)
- **T13-001** — `qmb` builds as exactly ONE wheel (pure library + `qmb` CLI); `uv add qmb`
  installs it; `import qmb` succeeds. *(13.1 AC1)*
- **T13-002** — pinned dependencies present at exact versions `click==8.4.2` and
  `optuna==4.9.0`. *(13.1 AC1)*
- **T13-003** — declared dependency set = exactly the six qmf backends
  {qmf-core, qmf-registry, qmf-data, qmf-indicators, qmf-structure, qmf-risk}; **no dependency
  edge to qmf-venue**; qmb sits outside the qmf roster. *(13.1 AC1b)*
- **T13-004** — module tree contains all of `runloop/ config/ registryread/ execution/ data/
  optimize/ robustness/ results/ ledger/ orchestrator/ doors/{cli,api,mcp}`. *(13.1 AC2)*
- **T13-005** — vocabulary scan of modules/symbols/docstrings finds **no** use of
  "engine", "kernel", "exam", "plugin", or "snapshot" for registry state. *(13.1 AC3 / B-15)*
- **T13-006** — `poe check` over qmb: ruff clean, pyright-strict clean, pytest green. *(13.1 AC5)*
- **T13-007** — no module-global mutable state anywhere in the library; package is pure-Python
  and OS-neutral (no compiled/platform-specific extension). *(13.1 AC5 / AR-11, AR-04, NFR-02)*

### 4.1 Unit (L1)
- **T13-101** — `doors/mcp` is scaffolded but NOT shipped in V1: it is not wired into the CLI-v1
  surface (invoking it in V1 is absent/refused). *(13.1 AC2 / SC-08)*
- **T13-102** — registry-read port: a human alias resolves to the record **by `fp1`**; the
  returned handle is cited by fingerprint, never `name@version`. *(13.2 AC2)*
- **T13-103** — registry-read port: a ref a fresher as-of shows superseded → an AD-11
  **stale-evidence refusal RETURNED (not raised)** at severity `qmb_stale_evidence_severity`. *(13.2 AC3 / FM-7)*
- **T13-104** — a named condition preset (e.g. stress-spread) materializes as an **ordinary
  config fragment** under the same grammar/fingerprint/lineage discipline. *(13.3 AC5)*
- **T13-105** — compiler precedence: layers resolve strictly `invocation flags > run spec >
  BMS fragment > Book fragment > workspace defaults`; each layer overrides the one below on a
  resolvable key. *(13.4 AC1)*
- **T13-106** — compiler emits **exactly ONE** fully-resolved, **read-only**, schema-validated
  run-config artifact. *(13.4 AC1)*
- **T13-107** — compiler: an unsanctioned key collision across Book and BMS fragments → a
  **compile-time CT-04 typed refusal**; the colliding value is **never silently overwritten**. *(13.4 AC2 / FM-1)* **[R-004, hot-spot]**
- **T13-108** — compiler: in a sanctioned overlap, the **BMS value outranks the Book value**. *(13.4 AC2)*
- **T13-109** — resolved artifact cites Book, BMS, and any binding by `fp1` even when the
  invocation used a human alias; no `name@version` leaks into the artifact. *(13.4 AC3)*
- **T13-110** — a config binding a replay clock to synthetic-tainted data → a CT-04
  **`invalid input`** refusal (world is provenance-derived, B-7 wins; a caller may not declare world). *(13.4 AC5 / FM-3)*
- **T13-111** — `starting_capital`: mandatory run-spec field — absent with no Book default →
  refusal; a Book-fragment default applies when the run spec omits it. *(13.5 AC1)*
- **T13-112** — a seed-overriding invocation flag → the binding is stamped `seed_overridden`
  **and** the run's fold is forced to `unrated`. *(13.5 AC2 / FM-12)*

### 4.2 Integration / component (L2)
- **T13-201** — the ONE library-owned registry-read port is the sole resolution path; there is
  **no door-side and no second cache** (config compiler and door-autocomplete resolve through it). *(13.2 AC1)*
- **T13-202** — registry state resolves from an immutable, fingerprinted **as-of set** delivered
  by passive storage — **no live/central-service call path** (DEC-0084 service stays dead). *(13.2 AC5)*
- **T13-203** — a batch/sweep admission freezes **ONE as-of** for every trial; after admission
  fragments resolve by **explicit fingerprint**, never `name@latest`. *(13.2 AC4 / SC-11)*
- **T13-204** — the resolved-config fingerprint is the **run-id root and the ledger key**, and
  the artifact is written into the run's output directory **named by the run id**. *(13.4 AC4)*
- **T13-205** — each run mints **exactly ONE** CT-28 binding with `world=replay` (compile → mint). *(13.5 AC3)*
- **T13-206** — `starting_capital` seeds the binding's **virtual ledger**. *(13.5 AC1)*
- **T13-207** — *(PARTIAL, §7.2)* sizing / R-freeze / exit resolution consumes the CT-23 inbound
  intent and CT-29 exit seams (the wiring/consumption point exists and is bound per run-config). *(13.5 AC4)*

### 4.3 Contract conformance (L3)
- **T13-301** — the Book config fragment is a schema-validated, fingerprinted **DERIVED**
  artifact carrying a **CT-07 lineage edge** (edge_type back to the CT-22 source `fp1`); it is
  **not a newly minted registry kind** and **not free-hand-edited**. *(13.3 AC1)*
- **T13-302** — the BMS config fragment is a derived, fingerprinted artifact carrying a **CT-07
  lineage edge** back to the CT-27 source `fp1`. *(13.3 AC2)*
- **T13-303** — a fragment stamps its own **AD-5 integer format version**; a format-N fragment
  stays readable after format-(N+1) ships; an unknown format version is an `unsupported
  capability` refusal, never a best-effort read. *(13.3 AC4 / CT-05, CT-22 unknown-version invariant)*
- **T13-304** — the resolved run-config stamps its own **AD-5 format version** and declares its
  **AD-10 identity-vs-display** field classification; old resolved artifacts remain readable forever. *(13.4 AC4)*
- **T13-305** — the minted binding is a valid **CT-28** record with `world=replay`, a **different
  identity** from any live binding of the same Book instance and **incomparable** to it. *(13.5 AC3)*
- **T13-306** — a binding record fingerprinting **equal** to an existing one → a CT-28
  `invalid input` refusal (never AD-10's silent idempotent accept — that path is for byte-identical
  rewrites of the same work, not a second pot of money). *(13.5 AC3 / CT-28 invariant)* **[R-004]**
- **T13-307** — QMB SemVer rides as **display-only provenance**, excluded from every `fp1`/identity
  computation (a SemVer change changes no fingerprint). *(13.1 AC4 / CT-05)*
- **T13-308** — every refusal on an Epic-13 path is a valid **CT-04** value: category ∈ the seven,
  machine-readable context present (may be empty, never null), retryability present — **RETURNED**
  across the public boundary, never raised. *(cross-cutting, CT-04)*
- **T13-309** — *(PARTIAL, §7.2)* an AD-40 full-loss price is required before any open (the
  precondition is declared/enforced at the config-and-binding seed level). *(13.5 AC4)*

### 4.4 Property / invariant / golden-scenario (L4)
- **T13-401** — **[R-004]** distinct semantic inputs ⇒ distinct config `fp1`: any change to an
  identity-classified field of the resolved config changes its `fp1`; no two semantically-distinct
  configs share a run identity (hypothesis property over the field set). *(13.4 AC4)*
- **T13-402** — **[R-004 converse / NFR-03]** identical inputs ⇒ **byte-identical** resolved
  artifact / equal `fp1`; layering is pure with no ambient nondeterminism (property). *(13.4 AC1)*
- **T13-403** — **[R-008]** input-shape invariance: semantically-equal input encodings — human
  alias vs `fp1`, object-key ordering, CT-01 canonical exact-rational forms — yield **one**
  resolved `fp1` **and one** gate verdict (identical accept/refuse). *(13.4 AC1/AC3)*
- **T13-404** — **[AD-10]** a change to a display-only field produces **NO** `fp1` change; a
  change to an identity field **DOES** change `fp1` (classification invariant). *(13.4 AC4)*
- **T13-405** — **[disjointness, hot-spot]** Book-fragment key namespace ∩ BMS-fragment key
  namespace = ∅ over the full declared surface; each declared key resolves to its owner domain
  (Book: admission/sizing/exit-door; BMS: accounting/constraints/kill-line/reporting). *(13.3 AC3)*
- **T13-406** — **[P0-13, config-side]** re-resolving a run id under its stored resolved config
  reproduces the **SAME config `fp1`** (the run-id root), or returns a **typed refusal** on
  mismatch. *(NFR-03 / DEC-0163; CT-32 result-side reproduction deferred — §7.1)*

---

## 5. Test-level allocation (L0–L6; one behaviour one level, lower level wins)

Reconstructed from the ratified quality tiers (DEC-0101/0102; `fixtures-and-scenarios.md`), since
`test-design-qa.md` is absent (§1.3). Each behaviour is allocated to the **lowest** level that can
prove it; it is not re-asserted higher.

| Level | Definition | Maps to ratified tier | Epic-13 tests | Count |
|---|---|---|---|---|
| **L0** | Static / build gate: ruff, pyright-strict, packaging, dependency-manifest, vocabulary scan, no module-global mutable state | Tier 1 (`poe check`) | T13-001..007 | 7 |
| **L1** | Unit: one pure function, injected inputs, deterministic, no network | Tier 1 | T13-101..112 | **12** |
| **L2** | Integration/component: multiple qmb modules composed (compiler ← registry-read ← fragment materializer; compile → binding mint), in-process | Tier 2 (`poe check-integration`) | T13-201..207 | **7** |
| **L3** | Contract conformance: CT-* round-trip / boundary / invalid-refusal + `fp1` identity via the single qmf-core implementation | Tier 2 | T13-301..309 | **9** |
| **L4** | Property / invariant / golden-scenario: hypothesis over laws + SCN-0012 identity chain | Tier 1 (property) / Tier 2 (scenario) | T13-401..406 | **6** |
| **L5** | End-to-end governed run (loop → CT-32 → ledger line) | Tier 2/3 | *none in Epic 13* — Epic 14/15 (§7.1) | 0 |
| **L6** | Non-functional: performance, concurrency, governor budgets | Tier 3 (`poe check-release`) | *none in Epic 13* — Epic 15 | 0 |

**Planned counts — L1: 12 · L2: 7 · L3: 9 · L4: 6** (L1–L4 total **34**; with L0 gate = **41** checks).

Allocation notes (lower-level-wins arbitration):
- Compiler precedence/collision/refusal behaviors sit at **L1** because the compiler is a pure
  function of already-materialized fragments; only run-id-root wiring and binding mint, which need
  the registry-read port and the mint path composed, rise to **L2**.
- Determinism and identity **properties** (R-004, R-008, AD-10, P0-13 config-side) sit at **L4**
  as universally-quantified laws, not duplicated as L1 examples.
- Fragment/config/binding **shape** conformance sits at **L3**; the *triggering* behavior of a
  refusal (e.g. stale ref, synthetic clock) sits at **L1**, its CT-04 *shape* folded once into T13-308.

---

## 6. Fixtures, data and determinism harness

- **Runner:** `uv run ...` from the worktree root (dev group synced). Property tests:
  `uv run --with hypothesis ...`. No test edits source; a failing test is recorded as a finding.
- **Determinism rules (from `fixtures-and-scenarios.md`):** unit/property fixtures make **no
  network calls**; time is an **injected CT-02 clock (int64 UTC ns)** at the composition root —
  no fixture below the root reads the system clock; randomized/property fixtures **declare their
  seed**; equal semantic inputs must replay to equal CT-05 `fp1` identities, computed by the
  **single qmf-core implementation** with floats refused in identity content.
- **Fixture classes used:** contract round-trip/boundary/invalid (L3), component failure-mode
  (`COMP-QMB/FM-1,3,7,12`), law/invariant property (R-004/R-008/AD-10/disjointness), and the
  golden-scenario binding **SCN-0012** for the identity chain (resolved-config fp1 = run-id root
  = ledger key; replay binding distinct/incomparable; re-resolution reproduces or refuses).
- **`fp1` canonicalization corpus (for T13-403/T13-401/T13-404):** semantically-equal encodings —
  alias vs `fp1` cite; permuted object-key order; CT-01 canonical exact-rational forms (reduced,
  positive denominator, sign on numerator) — must collapse to one identity; display-only field
  perturbations must NOT move `fp1`; identity-field perturbations MUST move it.
- **Refusal harness (T13-308):** assert refusals are RETURNED as one arm of a result union and
  carry `{category ∈ 7, context (present, non-null), retryability}`; assert absence of prohibited
  side effects (no ledger line, no log write from the pure library, no second cache).
- **Values are referenced, never restated:** governor/limit/severity/pin values come from
  registry keys (`qmb_stale_evidence_severity`, `qmb_cli_pin`, `qmb_sampler_pin`, …), never
  invented literals — the walk names keys, not numbers (SCN-0012 discipline).

---

## 7. Untestable / deferred / blocked requirements

### 7.1 P0-13 CT-32 *result*-fingerprint reproduction — DEFERRED to Epic 14
The full P0 assertion 13 ("re-running a run id reproduces the **CT-32** fingerprint or refuses")
needs the event-slice run loop and the CT-32 result artifact, which do not exist in Epic 13 (they
are Epic 14, whose **Story 14.7** owns the tier-2 golden-slice determinism test). At Epic 13 only
the **config-side** reproduction is testable (**T13-406**: the run-id root / resolved-config `fp1`
reproduces or refuses). The result-side half is recorded here as knowingly out of Epic-13 reach —
not a coverage gap in this epic.

### 7.2 Story 13.5 AC4 runtime — PARTIAL (seam only)
Sizing, R-freeze, exit execution, and the **AD-40 full-loss-price-before-open** enforcement fire
inside the loop that opens positions — Epic 14. In Epic 13 only the **seam/consumption wiring**
(CT-23 inbound, CT-29 exits bound per run-config) and the config/binding-level precondition are
testable (**T13-207**, **T13-309** marked PARTIAL). The runtime refusal on an open lacking a
full-loss price is an Epic-14 assertion.

### 7.3 Door parity — Epic 16, and MCP door untestable in V1
Full door-parity (identical function surface and semantics across CLI / API / MCP) is Epic 16's
tier-2 contract test. Epic 13 asserts only **single-source fingerprint agreement** (folded into
T13-403 / T13-204). The **MCP door is scaffolded-not-shipped (SC-08)**, so its parity cannot be
exercised in V1 — only its presence-without-wiring (T13-101).

### 7.4 GAP-0048-gated behavior — deferred by seam
`world=simulated` unlock, the fidelity taxonomy values, and forex fill/slippage/financing
**calibration content** are gated on GAP-0048 and cannot be asserted. Only the **refusal seams**
are testable now: synthetic-tainted-store → `policy rejection` / synthetic-clock-binding →
`invalid input` (T13-110). The calibration numbers themselves are decided-deferred, not a gap to
test against.

### 7.5 Defined-unwired contracts — conformance bounded to what QMB mints here
CT-22/23/27/28/29/32 are ratified **defined-unwired**; QMB is the first sanctioned wiring, in
`world=replay` only. Epic-13 contract conformance is therefore bounded to the artifacts QMB
actually mints in this epic — the Book/BMS **fragments**, the **resolved config**, and the
**replay binding** — plus the CT-07 lineage edges. Downstream CT-23/CT-29/CT-32 runtime behavior
is a seam exercised in Epic 14.

### 7.6 PLAN-INTEGRITY CAVEAT — named authorities absent
`_bmad-output/test-artifacts/test-design-qa.md` and `.../test-design/QMX-handoff.md` — named as
authorities for the L0–L6 architecture, the Per-Epic template, the 15 P0/P1 assertions, and this
epic's risk-gate rows — **do not exist in this worktree** (`_bmad-output/test-artifacts/` is
absent). The 8-section template and L-level scheme here are reconstructed from the ratified tier
structure; R-004, R-008, and P0-13 are taken from the task brief. If those files are later
supplied, §5's L-level mapping and §2's assertion set should be reconciled against them. This is a
**finding**, recorded, not worked around.

---

## 8. Exit criteria and coverage ledger

The epic's verification passes when:

1. **Every AC in §2 maps to at least one executed test in §4**, and every §4 test has a recorded
   PASS or a FINDING (a FINDING is a requirement the source does not satisfy — never resolved by
   editing source or weakening the test).
2. **L0 gate green:** `poe check` passes (ruff + pyright-strict + pytest); dependency manifest
   shows the six qmf backends and **no qmf-venue edge**; vocabulary scan clean; no module-global
   mutable state.
3. **Risk gates satisfied:**
   - **R-004** — T13-401, T13-402, T13-107, T13-306, T13-404 all PASS (distinct semantics ⇒
     distinct `fp1`; no silent overwrite; identity moves only on identity change).
   - **R-008** — T13-403 PASS (every accepted input shape ⇒ one `fp1` and one verdict).
   - **P0-13 (config-side)** — T13-406 PASS (re-resolution reproduces the run-id root or refuses).
4. **Config-compiler hot-spot cleared:** T13-105/107/108/405 and the identity properties
   (401/402/403/404) all PASS — precedence exact, disjointness proven, collision refuses,
   sanctioned overlap resolves BMS-over-Book.
5. **Contract conformance:** T13-301..308 PASS — fragments are derived + CT-07-lineaged + AD-5
   versioned; resolved config carries AD-5 + AD-10 classification; the replay binding is a valid
   CT-28 `world=replay` record, distinct/incomparable, equal-fp re-binding refused; all refusals
   are valid CT-04 values.
6. **Deferred items (§7) are explicitly recorded as deferred**, each with its owning epic — none
   silently counted as passed, none silently counted as failed.

Coverage ledger to be maintained alongside execution: `qa/epics/epic_13_qmb-substrate/` — one row
per §4 test id → {level, status PASS/FINDING/DEFERRED, evidence path}.
