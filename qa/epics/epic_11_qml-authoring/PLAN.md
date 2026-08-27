# Verification PLAN — Epic 11: QML authoring

- Tier: **T2** (contract-surface-heavy authoring epic; damage is a mis-minted identity or an off-register refusal, not live money at trade time)
- Package under audit: `packages/qml` (`src/qml/`), module homes `declaration/`, `families/`, `footprint/`, `protocol/`, `conformance/`, `examples/`, `tests/` (Story 11.1 Structural Seed)
- FRs in scope: **FR-047** (CT-33 Bot declaration + plain-Python logic), **FR-049** (CT-34 confluence artifacts). *(FR-048 conformance gate and FR-050 runtime protocol are Epic 12 — out of scope.)*
- Contracts in scope: **CT-33** (Bot definition / declaration kind), **CT-34** (confluence / leg-set kind). Plus the **CT-22 v2 / CT-23 v2 mint DELTA** owned by Story 11.7 — the format-2 shape additions and migration/back-compat only; the base CT-22/CT-23 door behaviour is Epic 10's territory and is NOT re-tested here (epic-binding).
- Constitution / spine law in scope: L11 (QML = the bot-authoring library built ON QMF); spine QL-1..QL-8; AR-60/AR-10/AR-06 (dependency stance), AR-62/AR-63/AR-64 (identity/footprint laws), AD-16/AD-17/AD-21/AD-22/AD-25/AD-30/AD-40/AD-9/AD-7/AD-15/AD-5.
- Golden scenarios in scope: **none** — Epic 11 is an authoring epic; no `docs/scenarios/SCN-*` exercises QML authoring (SCN-0012 is Epic 14's replay run). No L4/L5 golden fixture is planned here; T2 puts the weight on L2+L3.
- Gate rows (this epic): **R-009** (refusal-register conformance) and **R-011** (worst-covered file `footprint/_coerce.py` — assert by requirement, never by line-chasing).
- Author discipline: **Section 4 was written from requirements only (CT-33, CT-34, CT-04, and Epic 11's story ACs), before opening any `src/qml` file.** Sections 5–8 are the reconcile procedure to run against source at test-writing time; no `src/` file was read to author this plan.

> Template note (load-bearing): the canonical per-epic template lives in
> `_bmad-output/test-artifacts/test-design-qa.md` and the 15 P0/P1 assertions + risk-gate rows in
> `_bmad-output/test-artifacts/test-design/QMX-handoff.md`. **Neither file exists in this worktree**
> (confirmed by full-tree search — the entire `_bmad-output/test-artifacts/` directory is absent; only
> `_bmad-output/planning-artifacts/` is present). This plan therefore follows the per-epic 8-section
> shape and the L0–L6 rules the task prompt states verbatim (order load-bearing; Section 4 = an
> independent requirements-derived test list authored before any `src/` read; one behaviour → one level,
> lower level wins), and takes the gate rows (**R-009**, **R-011**) from the task prompt. No QML-specific
> P0/P1 assertion appears among the 15 (those are runtime-damage assertions; QML authoring is a
> registration-side, no-live-money epic). If the two authority files are later restored, this plan must
> be re-reconciled against them — recorded as a blocked input in Section 7.

---

## Section 1 — Epic scope, authorities, and audit posture

**What the epic asserts (one line).** A governed bot is exactly two artifacts — a CT-33 Bot *declaration*
whose identity is its semantic content only, plus a referenced plain-Python logic distribution whose
reproducible source-manifest fingerprint enters that identity — and confluences are reusable CT-34
leg-set artifacts deduplicated by fingerprint; qml authors both on qmf-core nouns, returns fingerprintable
content the host composition root mints, imports no qmf-venue, and never gates a plain-Python bot's tunnel
entry.

**Authorities, in precedence order (as read):**
1. `epics.md` **Epic 11** (Stories 11.1–11.7, ~40 acceptance criteria).
2. `docs/` knowledge base: `ct-33-bot-definition.yaml`, `ct-34-confluence.yaml`, `ct-04-typed-refusal.yaml`
   (the seven-category register), `constitution.md` L11. (CT-22 v2 / CT-23 v2 read for the Story-11.7 delta only.)
3. `test-design-qa.md` L0–L6 architecture — **absent** (level semantics reconstructed from the prompt).
4. `QMX-handoff.md` P0/P1 assertions + risk-gate rows — **absent** (R-009, R-011 taken from the prompt;
   no QML P0/P1 among the 15).

**Audit posture (binding).** Source is READ-ONLY evidence. A failing planned assertion is a FINDING recorded
against the requirement — never a source edit, never a weakened test. Tests assert what CT-33/CT-34 and the
spine demand, not what the code happens to do. Coverage numbers (e.g. `footprint/_coerce.py` 58.3% line /
48.8% branch) raise the *priority* of the requirement-anchored tests and set a Section-8 exit criterion;
they never become the assertion (R-011).

**Defined-unwired caveat.** CT-33 and CT-34 both carry `wiring_status: defined-unwired` ("the kind is
ratified surface; no code exists; records reach qmf-registry through the composition root under the AD-25
root-mints pattern; no wiring is authorized from this doc"). Two consequences the plan carries:
- Where the factory has since implemented the author-side machinery (`footprint/_coerce.py` demonstrably
  exists — it has a coverage number), the planned assertions run against real code.
- Where a surface is still genuinely unwired, the planned assertion cannot execute; its outcome is a
  **coverage FINDING** ("requirement R has no implementing code / no executable path"), logged against the
  requirement, never a silent skip. Section 8 makes the runnable/blocked split explicit at reconcile.

**qml's dependency stance (AR-60/AR-10/AR-06).** qml imports **only** qmf-core, qmf-registry, and qmf-risk;
any import of qmf-venue fails the L0 gate. The CT-33/CT-34 kinds are *consumer-blind*: qml returns
fingerprintable content and the host composition root mints and persists the record, so **no package import
edge** exists from qml into a consumer or from a consumer into qml. Every L2/L3 test therefore wires the
registry sink, the qmf-risk per-family law, and the qmf-core fp1 function through **in-test composition-root
fakes / injected sinks**, never a real cross-package import edge.

---

## Section 2 — Risk assessment and gate rows

### Risk-gate rows (must-pass, T2)

| Gate | Statement | Requirement anchors | Planned test IDs | Level |
|------|-----------|---------------------|------------------|-------|
| **R-009** | Every authoring-door typed refusal is a member of the seven-category register; no path emits an off-register category | CT-04 seven categories; CT-33 & CT-34 `enums.refusal categories`; 11.7 version-mismatch path | X1, X2, B4, C4, D2, E5, G4 | L1/L2 |
| **R-011** | `footprint/_coerce.py` (worst-covered file, 58.3% line / 48.8% branch) is asserted BY REQUIREMENT — template resolution totality, deterministic coercion, missing-identity-field refusal — never by line-chasing | 11.4 AC1/AC2, CT-33 footprint law (DEC-0174), AD-22 | D1, D2, D6, X3 | L1/L2 |

### Epic-specific damage ranking (why the weight sits where it does)

1. **Identity carve-out (F1 / CT-33 AC1)** — the guarantee that a bot's meaning lives *inside* its `fp1`
   and that a tuned assignment can never silently wear the original's track record. If the AD-16 header
   (`writer`, `sequence`, `stable id`, `created-at`) leaks into `fp1`, or a semantic-content group is
   dropped from it, every downstream seat cite (CT-28) and every governed-evidence cite (CT-32) is anchored
   to a corrupt identity. Highest damage; verified as a **property** over (header-field × semantic-group).
2. **Template resolution totality + `_coerce` determinism (D1/D6 / R-011)** — "identical canonical runs
   fingerprint identically on every machine" rests on template resolution being a total, single-valued
   function landing on ordinary CT-16/CT-17 producer fingerprints. A non-total or order-sensitive coercion
   splits identity across machines — the worst-covered file in the repo is exactly this locus.
3. **Reproducible source-manifest logic identity (C2/C3)** — a code change must mint a new Bot exactly as a
   changed default does, and identical source built twice must yield one Bot `fp1`. Build-artifact bytes
   (wheel timestamps) leaking into identity would fork identity on rebuild; a missed source change would let
   changed logic wear the old identity.
4. **Confluence leg law + counts-never-bounded (E1/E2/E6 / DEC-0185)** — the operator veto round ruled a leg
   MAY carry BOTH a producer binding and a child-confluence cite, at least one required, role always
   mandatory, and that leg/component counts are NEVER bounded. A spurious cardinality ceiling or an
   "exactly one of the two" reading is the exact foreclosing-cardinality trap AD-17 refuses.
5. **Forward-compat refusal (G4 / R-009)** — a format-1 reader confronting a format-2 CT-22/CT-23 artifact
   must refuse `unsupported capability`, and the two new admission-bar fields must land ONLY through the
   mint — never as a silent AD-30 field addition an old parser would ignore and thereby admit the very
   evidence they exist to refuse.

### Complexity hot-spot (pin by requirement, not by line) — R-011

`packages/qml/.../footprint/_coerce.py` is the worst-covered file in the repo (58.3% line / 48.8% branch).
**Behaviour there is pinned by requirement, never by line-chasing:** template resolution is a total,
single-valued function (D1); an omitted AD-22 identity field is a Layer-1 refusal (D2); the coercion of a
space-bound value set into the template's parameter slots is deterministic and order-stable so equal inputs
yield one CT-16/CT-17 fingerprint (D6). The coverage number raises the *priority* of these tests and makes
branch coverage on `_coerce.py` a Section-8 exit criterion; a branch with no requirement anchor is itself a
FINDING (untethered complexity), never a reason to add a line-chasing test.

---

## Section 3 — Test-level strategy (L0–L6), T2 profile

T2 scope (from the prompt): **L2 + L3 for every AC, targeted L1 properties, L6 review.** Levels applied per
"one behaviour → one level; lower level wins." Reconstructed level semantics (canonical file absent):

- **L0 — static gates.** ruff, pyright-strict, the isolated-environment import check (imports ⊆
  {qmf-core, qmf-registry, qmf-risk}; any qmf-venue import fails — AR-60), the ambient-nondeterminism
  scanner (no thread / no I/O / no process; `conformance/` pure — AD-15), the packaging gate (exactly the
  seven module homes; no `console_scripts`), and the exact-rational float-ban scanner over qml value types
  (bounds/step/default/leg-parameters — AD-7). Reported separately; not counted in the L1–L3 tally.
- **L1 — pure property / unit.** Reserved (T2) for the pure-function *properties* where a property earns its
  keep over examples: fingerprint reproducibility and sensitivity, canonical fingerprint-ascending ordering,
  template-resolution totality, `_coerce` determinism, the identity carve-out, the canonical-assignment
  derivation, and the DEC-0185 counts-never-bounded law. Hypothesis-driven where the input space is open.
- **L2 — contract-surface / component (PRIMARY).** A whole kind's author-side surface proven inside qml with
  in-memory fakes: CT-33 declaration validation (parameter space, family cardinality, permitted-intent
  subset, confluence-set ordering), CT-34 leg validation (role vocabulary, binding/child/both, refusals),
  the footprint transitive-union reporting, the family-record shape, and the Story-11.7 format-2 additions
  and version-mismatch refusal. Every AC that is a validation/refusal/shape rule lands here.
- **L3 — integration (composition-root fakes) (PRIMARY).** Behaviours that need ordering/persistence or a
  cross-surface flow: the root-mints hand-off (qml returns fingerprintable content only; a fake composition
  root holds the WriterId + gapless sequence and sees every RecordSink refusal), the branches-from version
  graph over time, the warm-up horizon derived from a resolved producer chain, the family-variable
  resolution through qmf-risk law, format-1↔format-2 back-compat reads, and the "plain-Python bot runs
  unchanged" tunnel-entry guarantee.
- **L4 / L5 — golden scenario / NFR.** Not applicable to Epic 11 (no authoring golden scenario; import-time
  and purity NFRs are covered at L0).
- **L6 — adversarial review.** One requirement-anchored review pass over `footprint/_coerce.py` (R-011) and
  the qml purity/dependency-direction posture: read the coercion/resolution branches against CT-33's
  footprint law and AD-22, flag any branch with no requirement anchor as untethered complexity, and confirm
  no impure step (I/O, process, thread) or qmf-venue edge hides in an author-side module.

Assignment rule applied: a rule provable as an L2 surface refusal is not re-asserted at L3; the L1 layer is
*only* the pure properties, not a re-run of the L2 examples; L3 exercises cross-surface flows and time, not
single-refusal rules.

---

## Section 4 — Independent test list (authored from requirements, before any `src/` read)

Legend: level in brackets; anchors cite Story.AC / CT / DEC / gate. IDs are stable. **[L0]** items are
static gates, reported separately (Section 3), listed here for traceability.

### A. Scaffold, purity, dependency stance, tunnel-entry (Story 11.1)

- **A1 [L0]** `uv add qml` resolves and `import qml` runs; qml installs as one wheel **outside** the
  seven-package roster, adding no runtime dependency beyond the `qmf-*` packages it consumes. (11.1 AC1)
- **A2 [L0]** The package contains **exactly** the module homes `declaration/`, `families/`, `footprint/`,
  `protocol/`, `conformance/`, `examples/`, `tests/` and ships **no** `console_scripts` entry point (QMB's
  `qmb` CLI is the single command-line surface). (11.1 AC2)
- **A3 [L0]** `conformance/` is pure — the ambient-nondeterminism scanner confirms it spawns no process and
  performs no I/O. (11.1 AC2, AD-15)
- **A4 [L0]** Isolated-environment import check + pyright-strict: qml imports **only** qmf-core, qmf-registry,
  and qmf-risk; any import of qmf-venue **fails the gate**. (11.1 AC3, AR-60)
- **A5 [L0]** Ambient-nondeterminism scanner over every qml module: no thread, no I/O, no process; every
  impure step (registration writes, sandbox execution) is left to a host composition root. (11.1 AC4, AD-15)
- **A6 [L3]** A plain-Python bot with **zero** qml imports runs unchanged in a host / research lane, because
  conformance is never required for tunnel entry; the `.qml` DSL and its Monaco surface are not revived in
  V1. (11.1 AC5)
- **A7 [L1]** The qml distribution's SemVer is display-only provenance and **never enters any `fp1`** (vary
  the distribution version → every authored `fp1` is unchanged). (11.1 AC1)

### B. Strategy-family metadata records (Story 11.2)

- **B1 [L2]** A minted strategy-family id is an opaque operator-minted id (AD-9) resolving to a **dated CT-06
  metadata record** — the same machinery as `instrument_class`, with **no new CT number**; qml adds no
  `qml_*` configurable row and no version pin to the registry. (11.2 AC1, CT-06)
- **B2 [L2]** A minted family record inspected for constraint powers (permitted timeframes, permitted feature
  families, mutation allowances) exposes **none** — a family is a keying token with no authority;
  constraining is the Book's job. (11.2 AC2)
- **B3 [L3]** A family id in use resolves the per-family variables the ratified qmf-risk law already reaches
  for — the Book's `exit_policy` `ExitLogicRef` per family, the family-scoped paper starting balance, the
  per-family bench threshold — while the family itself decides nothing. (11.2 AC3) *(qmf-risk law via fake.)*
- **B4 [L2]** A declaration citing a family id that resolves to **no** family record at Layer 1 →
  `unavailable dependency` typed refusal, **journaled** — never a silent pass. (11.2 AC4, CT-04) — **R-009**

### C. Reproducible source-manifest logic identity (Story 11.3)

- **C1 [L1]** The logic source-manifest fingerprint is a **normalized, reproducible** hash over the source
  tree in `fp1:sha256:<hex>` form. (11.3 AC1, AR-63)
- **C2s [L2]** The source-manifest fingerprint is computed **only by calling qmf-core's canonical fp1
  function** — never re-implemented in qml (seam assertion: the qmf-core fp1 fake is the sole computation
  path). (11.3 AC1, AR-63)
- **C2 [L1]** The **same** logic source built in two different sandboxes yields **one identical** Bot `fp1`;
  non-reproducible built-artifact bytes (wheel timestamps, build metadata) **never enter identity** (property
  over injected build-env noise). (11.3 AC2)
- **C3 [L1]** A **one-character** change to the logic source → a **different** source-manifest fingerprint →
  the containing Bot definition mints a **new** `fp1` — a code change mints a new Bot exactly as a changed
  default mints a new Book. (11.3 AC3)
- **C4 [L2]** A declaration whose referenced logic distribution cannot be resolved → `unavailable dependency`
  refusal at Layer 1 (the logic reference is mandatory — a governed bot is exactly two artifacts). (11.3 AC4,
  CT-04) — **R-009**

### D. Footprint, producer templates, horizon derivation (Story 11.4) — R-011

- **D1 [L1]** Producer-template resolution is a **total, single-valued** function: substituting the
  space-bound values yields exactly one deterministic CT-16/CT-17 configured-producer fingerprint, so dedup
  lands on ordinary producer fingerprints (property over the space-bound value domain). (11.4 AC1, DEC-0174)
  — **R-011**
- **D2 [L2]** A producer template missing **any** AD-22 identity field (formula id, contract format version,
  ordered named input set, calendar requirements, alignment policy, missing-value policy, warm-up, output
  schema, supported modes, arithmetic-reference configuration) → a **Layer-1 registration refusal**
  (`invalid input`). (11.4 AC2, AD-22) — **R-011 / R-009**
- **D3 [L2]** Given a footprint plus every cited confluence's leg producer bindings and any bot-direct
  producers, the module **reports** whether the footprint's producer-binding set **equals** that transitive
  union — the raw material Epic 12's Layer-1 linter consumes. (11.4 AC3, DEC-0174) *(The reporting function
  is Epic 11; the linter that turns the report into a refusal is Epic 12 — see Section 7.)*
- **D4 [L3]** The warm-up / embargo horizon is **derived** from the resolved producer chain (AD-21/AD-22 law);
  there is **no** second, hand-declared window field on the declaration. (11.4 AC4, AD-21/AD-22)
- **D5 [L2]** The stream set (instrument-role + `BarSpec` list in B-12's shape, trading vs data-only roles)
  is nested **inside** the footprint as the one stream-set locus — never a second top-level field; hosts
  provide only the declared footprint to the logic. (11.4 AC5, CT-33)
- **D6 [L1]** `footprint/_coerce.py`: coercing a space-bound value set into the template's parameter slots is
  **deterministic and order-stable** — equal inputs yield the same coerced CT-16/CT-17 configuration and the
  same fingerprint, regardless of input ordering (property; asserts the requirement, not the lines). (11.4
  AC1, DEC-0174) — **R-011**

### E. CT-34 confluence kind (Story 11.5) — FR-049

- **E1 [L2]** Each leg carries a **mandatory role** from the closed-and-addable vocabulary
  `level | trigger | confirmation | filter`; **at least one leg** is present (a zero-leg confluence is
  `invalid input`); leg and component counts are **never bounded**. (11.5 AC1, DEC-0185)
- **E2 [L2]** A single leg carries a producer binding (a pinned CT-16/CT-17 fingerprint or a QL-4 template),
  a `leg.confluence_ref` to a child confluence, or **BOTH** — at least one of the two is required, the role
  always mandatory. (11.5 AC2, DEC-0185)
- **E3 [L1]** A confluence with no declared order-significance fingerprints its legs **fingerprint-ascending**
  (order-insignificant) with display-only ordinals that never enter identity; order-significance is opt-in
  per confluence and enters the fingerprint **only when declared** (a confluence is a declaration artifact,
  not a CT-17 causal composite, so AD-25's order-significant-by-default does not reach it). (11.5 AC3)
- **E4 [L1]** Two bots citing the same confluence content mint **no** new confluence (reuse), while a changed
  leg, role, producer binding, leg parameter, child cite, or a newly-declared order-significance **always**
  mints a new confluence fingerprint. (11.5 AC4)
- **E5 [L2]** A leg whose role is outside the vocabulary, or that carries neither a producer binding nor a
  child-confluence cite → `invalid input`; an unresolvable producer fingerprint or cited child confluence →
  `unavailable dependency`; condition semantics (WHEN a leg is satisfied) live in the Python logic — the
  declaration carries only WHAT is consumed and WHICH role each plays. (11.5 AC5, CT-04) — **R-009**
- **E6 [L1]** **DEC-0185 counts-never-bounded property:** N `level` legs + M `trigger` legs + arbitrary
  nesting depth all validate; no count ceiling exists anywhere (Hypothesis over N, M, depth). (11.5 AC1,
  DEC-0185)

### F. CT-33 Bot definition — identity, parameter space, versioning (Story 11.6) — FR-047

- **F1 [L1]** **Identity carve-out property:** the AD-16 header's `writer`, `sequence`, `stable id`, and
  `created-at` are **excluded** from `fp1` (the stable id is derived FROM the fingerprint, never hashed INTO
  it); identity is the six semantic-content groups plus the contract format version and at-birth refs and
  nothing more (vary a header field → `fp1` unchanged; vary any semantic group → `fp1` changes). (11.6 AC1,
  CT-33)
- **F2 [L2]** Each declared variable carries a type in `{exact integer, exact rational, categorical,
  boolean}`, bounds, step, a **mandatory default**, an optional hard-constraint filter, and an **AD-40
  unit-kind**; a variable missing its unit-kind → `invalid input`; the mandatory defaults taken together
  ARE the canonical assignment (one identity locus, not a separate declared field). (11.6 AC2, CT-33)
- **F3 [L2]** A declaration carrying **zero or more than one** strategy-family id → `invalid input`
  (deliberate AD-17 cardinality-one ruling); the confluence set is one-or-more CT-34 fingerprints,
  canonically ordered by **child fingerprint ascending** with display-only ordinals. (11.6 AC3, AD-17)
- **F4 [L2]** The permitted-intent declaration names **only** permitted exit-intent kinds — a **subset** of
  the ratified CT-23 exit vocabulary (`close_full | tighten_protective_stop`), which **may be empty** (an
  entry-only bot is legal); `entry` is always permitted and is never declared here; the declaration carries
  **no sizing, no venue command, and no exit-logic field**. (11.6 AC4, CT-33)
- **F5 [L1]** The **canonical assignment** is the mandatory-default projection of the parameter space taken
  together — one identity locus; deriving it twice yields the same value, and it is never a separately stored
  field. (11.6 AC2)
- **F6 [L3]** AD-30 versioning: versions ride an append-only `branches-from` graph (multiple heads legal)
  with a **separate dated `current` pointer**, every version readable forever; re-binding, seat assignment,
  and paper flips **never** mint a new Bot, while a changed default, confluence leg, footprint entry, or
  logic artifact **always** does. (11.6 AC5, AD-30)
- **F7 [L3]** **Root-mints (AD-25):** qml returns **fingerprintable content only, never a stamped record**;
  the host composition root holds the `WriterId` and the gapless per-`(writer, kind)` sequence, mints the
  record, and sees every `RecordSink` refusal; the writer unit is `(machine, authoring role, kind)`. (11.6
  AC6, AD-25) *(Fake composition root / RecordSink.)*

### G. CT-22 / CT-23 format-version 2 mint + migration (Story 11.7) — delta only

- **G1 [L2]** CT-22 minted to format 2 adds **exactly three things and nothing more**: two
  `admission_bar.evidence_requirements` fields (`registered_conformant_bot_cite`;
  `canonical_assignment_evidence`), one explicit **optional** `exit_policy` catch-all default entry, and the
  `footprint_requirements` requirement-set shape filling its reserved pending slot. (11.7 AC1)
- **G2 [L2]** CT-23 minted to format 2 adds **exactly one OPTIONAL** entry-intent field,
  `entry.advisory_stop_proposal` (a Price or PriceDelta bound, advisory exactly as `proposed_r`), and
  documents the declared full-loss price as Book-resolved at the door — and nothing more. (11.7 AC2)
- **G3 [L3]** A pre-mint format-1 Book definition or intent stays **readable forever** at format 1; because
  `advisory_stop_proposal` is optional, format-2 readers accept format-1 intents unchanged. (11.7 AC3, AD-5)
- **G4 [L2]** A **format-1 reader** confronting a format-2 CT-22 or CT-23 artifact refuses `unsupported
  capability` on the version mismatch — **never a best-effort read**; and the two new admission-bar fields
  land **only through this mint**, never as a silent AD-30 field addition an old parser would ignore and
  thereby admit the very evidence they exist to refuse. (11.7 AC4, CT-04) — **R-009**
- **G5 [L2]** The thresholds behind the admission-bar interfaces stay **GAP-0048/0049** (interfaces only,
  SC-07); any not-yet-ruled requirement still **passes registration while blocking live binding**. (11.7 AC5)

### X. Cross-cutting gates and aggregates

- **X1 [L2]** **R-009:** every door-reachable typed-refusal category across the CT-33 and CT-34 Layer-1
  authoring paths **and** the Story-11.7 format-2 version-mismatch path is a member of
  `registry:typed_refusal_codes`; no path emits an off-register category. — **R-009**
- **X2 [L1]** **R-009 corollary:** the register is exactly the seven CT-04 categories, **addable never
  redefined**; qml's authoring paths emit only the four the contracts declare — `invalid input`,
  `unsupported capability`, `unavailable dependency`, `policy rejection`. — **R-009**
- **X3 [L2]** **R-011 aggregate:** `footprint/_coerce.py` behaviour is pinned by requirement (D1, D2, D6);
  branch coverage on `_coerce.py` is a Section-8 exit criterion; a branch with **no** requirement anchor is
  itself a FINDING (untethered complexity), never a reason to add a line-chasing test. — **R-011**
- **X4 [L0]** Exact-rational float-ban scanner: no binary float enters any `bounds`/`step`/`default` or
  `leg.declared_parameters` field in qml value types (AD-7). — cross-cuts CT-33 & CT-34 units.

**Planned counts (L0 static gates + L6 review reported separately):**

| Level | Count |
|-------|-------|
| L1 (targeted properties) | 12 |
| L2 (contract-surface, PRIMARY) | 19 |
| L3 (integration, PRIMARY) | 6 |
| **Total (L1–L3, counted)** | **37** |
| L0 static gates | 6 (ruff, pyright-strict, import-legality A4, nondeterminism A3/A5, packaging A2/A1, float-ban X4) |
| L6 review pass | 1 (`footprint/_coerce.py` + purity/dep-direction, R-011) |

---

## Section 5 — Source-reconciliation plan and seam / hot-spot map

**This section executes only after Section 4 above is frozen** (it is frozen; no `src/qml` file was read to
author this plan). The reconcile pass maps each planned test to the module that should satisfy it and
records, per requirement, one of: `runnable` (code exists and the assertion can execute), `blocked-unwired`
(surface still `defined-unwired` — the planned test becomes a coverage FINDING), or `absent` (no module at
all — FINDING).

Reconcile procedure (no source edits, read-only):
1. Enumerate `packages/qml/src/qml/**` module + symbol names (structure only) and map to clusters A–G:
   `declaration/` → F, G; `families/` → B; `footprint/` (incl. `_coerce.py`) → D, and the confluence
   producer-binding path shared with E; `conformance/` → the Layer-1 half of F7/registration (Layer-2 is
   Epic 12); `protocol/` → the CT-23 permitted-intent id validation (F4) surface; `examples/` → the
   worked-example fixtures the tests read, never author.
2. Enumerate any existing `packages/qml/tests/**` and mark which planned IDs already have coverage vs are
   net-new; a pre-existing test that asserts what the code does rather than what CT-33/CT-34 demand is itself
   a FINDING to re-derive, not to trust.
3. For `footprint/_coerce.py` (R-011, 58.3%/48.8%): confirm the requirement-pinned behaviours (D1 totality,
   D2 missing-identity-field refusal, D6 deterministic order-stable coercion) reach every branch tied to a
   requirement; a branch with no requirement anchor is a FINDING (untethered complexity) — not covered by a
   new line-chasing test.
4. Confirm the seven-category register `registry:typed_refusal_codes` is a single source (CT-04) and that
   both CT-33's and CT-34's `enums.refusal categories` are subsets (X1/X2 mechanization target).
5. Confirm the source-manifest fingerprint path (C2s) resolves to a **call into qmf-core's canonical fp1**,
   with no local hash re-implementation in qml.

Seam map (planned wiring the L2/L3 tests fake, never real-import — qml has no consumer import edge):
- **Registry sink** (CT-06 family record, CT-33 Bot kind, CT-34 confluence kind) — injected `RecordSink`;
  qml returns fingerprintable content, the fake composition root mints (F7, B1).
- **qmf-core fp1 function** — the sole fingerprint computation path (C1, C2, C2s, F1, E3/E4); qml never
  re-implements a hash.
- **qmf-risk per-family law** — fake for B3 (Book `exit_policy` `ExitLogicRef`, paper starting balance,
  bench threshold resolution by family id).
- **CT-16/CT-17 producer identity** — fakes for D1/D3/D6 (template resolution, transitive-union reporting,
  coercion) and E2/E5 (leg producer bindings).
- **Format-1 / format-2 readers** — paired fakes for G3/G4 back-compat and version-mismatch refusal.

---

## Section 6 — Traceability (FR → story/AC → CT → tests → level)

| FR / gate | Story | Primary CT / law | Planned tests | Levels |
|-----------|-------|------------------|---------------|--------|
| **FR-047** (CT-33 declaration + plain-Python logic) | 11.1, 11.2, 11.3, 11.4, 11.6 | CT-33, CT-06, AR-60/63/64, AD-16/17/21/22/25/30/40 | A1–A7, B1–B4, C1–C4, D1–D6, F1–F7 | L0–L3 |
| **FR-049** (CT-34 confluence artifacts) | 11.4 (footprint reach), 11.5 | CT-34, DEC-0175/0185 | D3, E1–E6 | L1–L2 |
| **FR-047/FR-049** (CT-22 v2 / CT-23 v2 mint delta) | 11.7 | CT-22 v2, CT-23 v2, AD-5, SC-05/SC-07 | G1–G5 | L2–L3 |
| Gate **R-009** | 11.2/11.3/11.4/11.5/11.7 + all doors | CT-04, CT-33/CT-34 refusal enums | X1, X2, B4, C4, D2, E5, G4 | L1–L2 |
| Gate **R-011** | 11.4 | CT-33 footprint law (DEC-0174), AD-22 | D1, D2, D6, X3 | L0–L2 |

Every Story 11.x acceptance criterion maps to at least one planned test ID above; no AC is left uncovered.
The reconcile pass in Section 5 records any AC whose implementing code is absent or unwired as a FINDING
rather than a coverage hole in this plan. **Epic-binding confirmations:** FR-048 (conformance gate / sandbox
runner) and FR-050 (runtime protocol) are Epic 12 and appear here only as boundaries (Section 7); the base
CT-22/CT-23 door behaviour is Epic 10 and is tested only for the format-2 delta and back-compat, never
re-asserted.

---

## Section 7 — Untestable / deferred / blocked requirements

Recorded honestly; each with the reason it cannot be a runtime assertion in this epic/package.

1. **Layer-2 sandboxed execution conformance and the host-owned conformance sandbox runner.** CT-33's
   "registration is the ticket" mints the Bot kind only when **both** conformance layers pass, but the
   Layer-2 sandbox and the runner are **Epic 12** (FR-048 / QL-7). **Testable here:** the Layer-1 half —
   declaration linting and the `policy rejection` when qml's own Layer-1 gate fails, plus root-mints
   returning fingerprintable content only (F7). **Untestable here by epic-binding:** the Layer-2 sandbox
   verdict and the two-layer composition.
2. **The Epic 12 Layer-1 linter's *refusal* of an incomplete footprint.** Story 11.4 AC3 explicitly makes
   qml **report** whether the footprint's producer-binding set equals the transitive union — "the raw
   material the Epic 12 Layer-1 linter consumes." **Testable here:** the reporting function (D3).
   **Untestable here:** the linter that turns the boolean into a registration refusal (Epic 12).
3. **Not-yet-ruled admission-bar threshold VALUES (GAP-0048/0049, SC-07).** The format-2 interfaces exist;
   the thresholds are honestly blank. **Testable:** not-yet-ruled passes registration but blocks live
   binding (G5). **Untestable:** the actual threshold comparison — there is no ruled value to compare
   against.
4. **Confluence leg condition / predicate semantics ("WHEN a leg is satisfied").** Deferred by DEC-0175 — in
   V1 this lives in the Python logic; there is **no declarative predicate grammar**. **Testable:** that the
   declaration carries only WHAT is consumed and WHICH role each plays (E5). **Untestable:** any "when
   satisfied" assertion — there is nothing declarative to assert.
5. **Two-physical-sandbox reproducibility (C2).** A true dual-machine build is an infra/CI concern. **In
   package:** C2 is asserted as a **property over injected build-env noise** (wheel timestamps, build
   metadata) — a real two-machine build is a cross-environment (system) test, out of this package's scope.
6. **Cross-package family-variable resolution end-to-end (B3).** The per-family variables live in qmf-risk
   law (Book `exit_policy` `ExitLogicRef`, paper starting balance, bench threshold). **In package:** tested
   with a qmf-risk fake; a true end-to-end resolution is a cross-epic (Epic 10 + Epic 11) system test.
7. **Cryptographic authenticity of the human-signed `continues-performance` edge (AD-30) and of the
   operator-minted family id's authorship.** V1 signing is the operator's recorded approval, taking no
   cryptographic dependency. **Testable:** presence/absence and gating of the recorded attestation.
   **Untestable:** authenticity / non-repudiation — there is no crypto to verify.
8. **BLOCKED INPUT — absent authorities.** `test-design-qa.md` (the canonical L0–L6 + per-epic template) and
   `QMX-handoff.md` (the 15 P0/P1 assertions + this epic's full risk-gate rows) are not present in the
   worktree (full-tree search: `_bmad-output/test-artifacts/` is absent). This plan reconstructs the level
   semantics from the task prompt and uses R-009 and R-011 as given there; no QML-specific P0/P1 exists among
   the 15 (those are runtime-damage assertions; QML authoring is registration-side, no-live-money). If those
   files are restored, re-reconcile: the level definitions, any additional gate rows, and any P1 that turns
   out to touch a CT-33/CT-34 identity path may refine Sections 3, 4, and 6.

---

## Section 8 — Execution plan, fixtures, tooling, exit criteria

**Tooling.** `uv run pytest` from the worktree root (dev group synced). The property tests (C2, C3, D1, D6,
E3, E4, E6, F1, F5) use Hypothesis (`uv run --with hypothesis pytest ...` if not in the lock). Static gates
via the repo's ruff + pyright-strict config, the isolated-environment import check (A4), the
ambient-nondeterminism scanner (A3/A5), the packaging gate (A2), and the exact-rational float-ban scanner
(X4). The L6 review is a manual requirement-anchored read, its findings filed like any other.

**Fixtures (requirements-anchored, no ad-hoc literals).**
- Shared builders: a **CT-33 Bot definition** with a complete six-group semantic content (one family id, a
  one-or-more confluence set, a parameter space with unit-kinds + mandatory defaults, a footprint with a
  nested stream set + producer bindings, a permitted-exit-intent set possibly empty, a logic reference); a
  **CT-34 confluence** with legs of mixed roles, a leg carrying BOTH a producer binding and a child cite
  (E2), and a nested child confluence (E6); a **producer template** complete-minus-space-bound-values (D1)
  and a defective one missing an AD-22 identity field (D2); a **format-1** and a **format-2** CT-22/CT-23
  artifact pair (G3/G4).
- Every fingerprint expectation is recomputed through the **qmf-core fp1 fake**, never a literal hash; every
  refusal expectation asserts a **CT-04 category value**, never error prose.

**Ordering (levels gate upward).** L0 static → L1 properties → L2 surface → L3 integration → L6 review. A red
L0/L1 that reflects a real contract violation is a FINDING and does not block authoring the higher-level
tests (they are recorded blocked-by-finding, not skipped silently).

**Exit criteria for the Epic-11 audit.**
1. Every planned ID A1–X4 has a runtime result or an explicit `blocked-unwired` / `absent` FINDING.
2. **R-009** gate green (X1/X2 + the per-door refusals B4, C4, D2, E5, G4), or every failure is a filed
   FINDING naming the door/path and the off-register category.
3. **R-011**: `footprint/_coerce.py` behaviour green by requirement (D1, D2, D6); every `_coerce.py` branch
   ties to a requirement anchor or is filed as an untethered-complexity FINDING; branch coverage on
   `_coerce.py` reported (target: full branch coverage on requirement-anchored branches — the low 48.8%
   baseline is the reason this is an exit criterion, not the assertion).
4. The identity guarantees green: identity carve-out (F1), template totality + coercion determinism (D1/D6),
   reproducible source-manifest identity (C2/C3), confluence content-identity (E3/E4) — or each filed as a
   FINDING.
5. 100% branch coverage on any CT-01/exact-rational value type reached from qml (AD-7 floor); no binary float
   in any qml identity field (X4). 80% line floor across the package, with `footprint/_coerce.py` called out
   explicitly against its 58.3% baseline.
6. No source file outside `qa/` modified; no test weakened to pass; every divergence between contract and
   code recorded as a FINDING.
