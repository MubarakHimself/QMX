# Verification PLAN — Epic 16: qmb CLI & doors

**Audit tier:** T2 (integration/contract scrutiny — a thin adaptation layer, not an identity-minting core).
**Test-tier scope for T2:** L2 + L3 for every AC; targeted L1 unit/properties; an L6 requirements-fidelity review. L0 static gates support the thin-door directive. L4/L5 are minimal here and mostly bounded by cross-epic dependencies (see §5, §7).
**Package under test:** `qmb/src/qmb/doors/{cli,api,mcp}` — the three doors only. Seams (read-only, owned elsewhere): `qmb/src/qmb/config/` (the B-3 run-config compiler, Epic 13), `qmb/src/qmb/registryread/` (the single B-15 registry-read port, Epic 13), `qmb/src/qmb/orchestrator/` (the submit entry point, Epic 15), and the library pure-function surface the doors front (its capabilities landed by Epics 13/14/15/17–23).
**Delivers:** all of **FR-046** — the thin click-based `qmb` command tree, per-transport refusal rendering, the Python API pure re-export surface, registry-enumeration autocomplete through the B-15 port, the tier-2 door-parity contract test, and the MCP door scaffolded (shipped post-CLI-v1).
**Governing law:** QMB spine **B-1** (one library, thin doors, the CLI as the product face; door parity a tier-2 contract test) with **AR-58** (per-transport refusal rendering + door parity), **AR-55/B-15** (one registry-read port, no door-side cache), **AR-13** (return-not-raise), **AR-10/DEC-0168** (one wheel, `click==8.4.2`), **DEC-0185** (the `qmb` CLI is the single command-line surface), **SC-08** (CLI ships first, MCP post-v1).

> **PROCESS GAP (read first).** Two authorities named in the audit brief **do not exist in this worktree**:
> `_bmad-output/test-artifacts/test-design-qa.md` (the Per-Epic Test Plan Template + the L0–L6 test-level architecture) and
> `_bmad-output/test-artifacts/test-design/QMX-handoff.md` (the 15 P0/P1 assertions + this epic's risk-gate rows).
> Confirmed absent by full-tree search (`_bmad-output/test-artifacts/` is absent; only `archive/recovery/*/restart-handoff.md` match the handoff name). The sibling PLANs for Epics 13/14 record the same gap.
> **Consequence:** the 8-section structure below and the L0–L6 taxonomy in §5 are **reconstructed** from the two extant sibling PLANs (`epic_13_qmb-substrate`, `epic_14_qmb-run-loop`), the ratified quality tiers (AR-18/AR-19, DEC-0101/0102), and this project's vocabulary ("tier-2 = `poe check-integration`"; "one behaviour one level, lower level wins"). The **risk gate R-006** text and the **blocker B-3 directive** in §3 are taken **verbatim from the task brief**; the P0/P1 ladder is **derived** from B-1/AR-58 and the Epic-16 ACs, not transcribed from the missing handoff. When the two files are restored, re-reconcile §1 template order, §3 gate rows, and §5 level definitions against them before executing.

---

## Section 1 — Epic Context, Scope & Authorities

**What this epic is.** Epic 16 is the platform's **door layer** — pure adaptation, never behaviour. Every capability exists exactly once, in the library, as a pure function (B-1); a door only *parses, transports, renders refusals, and enumerates the registry for autocomplete through the B-15 port*. Two doors ship in V1 — the `qmb` **CLI** (the product face, `click==8.4.2`) and the **Python API** (in-process re-export for the UI backend and research) — plus a third, **MCP**, scaffolded as a sibling wrapper but explicitly not shipped until after CLI v1 (SC-08). The load-bearing guarantee is **parity**: an identical function surface and identical semantics across doors, proven by a **tier-2 contract test**, so no capability drifts between the agent-facing and human-facing surfaces (B-1 — Jesse's three-heterogeneous-stacks failure). Refusals are the library's typed CT-04 values, **returned not raised**, rendered per transport (AR-58): CLI → nonzero exit + machine-readable stderr JSON; Python → the refusal union verbatim; MCP → `error.data` verbatim (deferred).

**In scope (Stories 16.1–16.6):** the thin click command tree (no domain logic); CLI refusal rendering (nonzero exit + stderr JSON); the Python API pure re-export; autocomplete through the single B-15 registry-read port; the tier-2 door-parity contract test; the scaffolded-not-shipped MCP door.

**Out of scope (seams only — owned elsewhere; assert the door's *adaptation to* them, never their internals):**
- The **library pure functions themselves** (their correctness) → Epics 13/14/15/17–23. Door tests assert adaptation + parity, not library behaviour.
- The **B-3 run-config compiler** and its **run-id (resolved-config fp1) computation** → **Epic 13** (a door computes *no* run-id — R5).
- The **orchestrator** submit entry point, process-per-run, governor, ledger append → **Epic 15** (a door *submits*; it does not spawn or write the ledger).
- The **B-15 registry-read port + as-of set delivery** → **Epic 13** (a door *enumerates through* the port; it does not own the as-of machinery).
- The **capabilities "landed by Epic 14"** the parity test runs against (run loop, CT-32 result) → **Epic 14**. The parity *mechanism* is fully in scope; the *population* it ranges over is Epic-14-bounded (§7).
- The **MCP door's refusal rendering / runtime binding** → deferred **post-CLI-v1** (SC-08); only scaffold presence + no-HTTP structure are testable now (R22/R23 structural half; R24 deferred).

**Epic-binding confirmation.** FR-046 is Epic 16's, verbatim (epics.md FR Coverage Map: "FR-046: Epic 16 — qmb CLI, Python API, optional MCP door"). Every requirement below is drawn from Epic 16's own Stories 16.1–16.6. Cross-epic ids (FR-036/037 capabilities = Epic 14; the compiler/B-3 = Epic 13; the orchestrator/B-5 = Epic 15; B-15 as-of delivery = Epic 13) appear **only as seams the door adapts to** and are explicitly *not* tested here — noted, not asserted (§7).

**Two senses of "tier" (do not conflate).** *Audit tier* **T2** = this plan's scrutiny band (integration/contract, lighter than the T1 identity-cores). *Test tier* **tier-2** = the project's `poe check-integration` execution band (AR-18: adds integration + contract tests, each package isolated so an undeclared import fails) where the door-parity contract test and the CT-04 per-transport rendering tests run. §5 maps the L0–L6 levels onto those bands.

**Authorities, in precedence order:**
1. Epic 16 section of `_bmad-output/planning-artifacts/epics.md` (Stories 16.1–16.6, ACs; lines 3210–3356).
2. `docs/` knowledge base: `docs/components/qmb.md` (B-1 "One library, thin doors, the CLI as the product face"; B-15 registry delivery; module tree; the "may never let a door hold a second cache or compute a run-id differently" law); `docs/contracts/ct-04-typed-refusal.yaml` (the seven categories, return-not-raise, context present-non-null); `docs/registry/variables.yaml` (`qmb_cli_pin` = `click==8.4.2`, non-configurable); `docs/scenarios/SCN-0012-qmb-replay-run.md` (the door-fronted replay run — the CLI/API walk of the golden run).
3. The Additional-Requirements glossary in epics.md (AR-10, AR-13, AR-18, AR-19, AR-55, AR-58; SC-08) and `architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md` (B-1…B-15).
4. Ruling: **DEC-0185** (operator veto round) — "no second command line, ever in this shape; QMB's `qmb` CLI is the single command-line surface."
5. *(Missing — see Process Gap)* test-design-qa.md; QMX-handoff.md.

---

## Section 2 — Requirements → Behaviours Traceability

Every row is a testable behaviour extracted from a ratified source. IDs (R1–R25) are consumed by the independent test list (§4) and the matrix (§8). "Ref" cites the governing AC / spine law / contract.

| # | Behaviour (requirement, stated as an assertion) | Ref | Story |
|---|---|---|---|
| R1 | Every capability the CLI exposes exists **exactly once in the library as a pure function**; the door carries only adaptation logic (parse, transport, render refusal, autocomplete) — **no domain/business logic accretes in the door**. | B-1, DEC-0168, AR-10 | 16.1 |
| R2 | The CLI pins `click==8.4.2` — the `qmb_cli_pin` registry key (referenced, never a restated literal; a bump is a contract-versioning event). | DEC-0168, AR-10 | 16.1 |
| R3 | The CLI is the platform's **single** command-line surface, exposing capability groups (e.g. `backtest`, `data`, `optimize`, `ledger`, `config`); there is no second/sibling CLI. | B-1, AR-10, DEC-0185 | 16.1 |
| R4 | A CLI command that runs the tunnel declares its config/resource prerequisites and **returns a typed refusal** when they are absent. | B-1, CT-04 | 16.1 |
| R5 | A `backtest` invocation compiles the run-config via the **Epic 13 compiler** and submits it to the **orchestrator entry point**, computing **NO run-id of its own** (the run-id is the compiler's resolved-config fp1). | B-1, B-3 | 16.1 |
| R6 | A library-returned CT-04 typed refusal renders at the CLI as a **nonzero exit code + machine-readable stderr JSON** carrying `{category, context, retryability}`. | AR-58, Consistency Conventions | 16.2 |
| R7 | Every refusal crossing the door is **RETURNED by the library and RENDERED by the door — never raised, never swallowed**. | AR-58, CT-04 | 16.2 |
| R8 | A successful run **exits zero**. | CT-04 | 16.2 |
| R9 | A **programmer error** (not a typed refusal) surfaces as an **exception**, on a channel distinct from the refusal channel. | AR-13 | 16.2 |
| R10 | The Python API door is a **thin pure re-export** of the library's pure-function surface, importable from the uv-added `qmb` package. | B-1, B-13 | 16.3 |
| R11 | A refusal returned through the Python door is the library's **refusal union VERBATIM** (return-not-raise; exceptions only for programmer error). | AR-58, AR-13 | 16.3 |
| R12 | The UI backend consumes the Python API **in-process, never stacked over HTTP**. | B-1 | 16.3 |
| R13 | A direct library call **through the door in research returns values and produces NO governed evidence**. | B-4, B-9 | 16.3 |
| R14 | Autocomplete enumerates registry state through the **single library-owned registry-read port (B-15)** — never a door-side or second cache. | B-1, B-15, AR-55 | 16.4 |
| R15 | Resolution and autocomplete **can never answer differently** — one port over one as-of set. | B-15 | 16.4 |
| R16 | A newly created Book reaches the CLI as a **fresher as-of set** — never a door cache refresh or a live-service query. | B-15 | 16.4 |
| R17 | Autocomplete uses **click's native shell-completion** mechanism and adds no bespoke completion machinery. | B-1 | 16.4 |
| R18 | The parity contract test asserts an **identical function surface AND identical semantics across doors**, **DERIVED** by enumerating each door's capabilities programmatically (both sides computed) — never a hand-maintained map. | AR-58, B-1 | 16.5 |
| R19 | A capability present in one door but **absent (or semantically divergent) in the other FAILS** the parity test. | B-1 | 16.5 |
| R20 | The parity test **runs at Tier 2** (`poe check-integration`) and completes against the real capabilities **landed by Epic 14**. | AR-18, AR-19 | 16.5 |
| R21 | The parity test **confirms per-transport refusal rendering** — CLI: nonzero exit + stderr JSON; Python: refusal union verbatim. | AR-58 | 16.5 |
| R22 | `doors/mcp` is **scaffolded** as a sibling wrapper over the same library, explicitly marked **post-CLI-v1 and NOT shipped in V1**. | SC-08, B-1 | 16.6 |
| R23 | The MCP door is a **sibling over the same library — never stacked over HTTP** — and localhost-bound by default. | B-1 | 16.6 |
| R24 | When the MCP door later renders a refusal, `error.data` carries the refusal union **verbatim**. | AR-58 | 16.6 |
| R25 | **CLI v1 ships first and the MCP door does not gate it.** | SC-08, B-1 | 16.6 |

---

## Section 3 — Risk Assessment, Weak Spots & Priority

**Highest-value risk theme (from the brief + B-1).** A door is thin *by law*; the whole danger is that the law quietly breaks. Two ways it breaks, both silent:
1. **Parity drift.** If the two doors diverge — a capability in one and not the other, or the same capability with different semantics — an agent and the operator are no longer using the same platform, and the failure is invisible until a divergent result surfaces. B-1's answer is the tier-2 parity test; the test only has value if it **derives both surfaces and reconciles them**, so it cannot itself go stale.
2. **Logic leaking into the door.** The moment a door computes a run-id, holds a registry cache, sizes anything, or renders a refusal it invented, "the library decides, the door translates" is dead and identity/determinism guarantees leak out of the core into an untested wrapper.

**Risk gate R-006 (verbatim directive from the task brief).** *Door parity must be **DERIVED from the door surfaces** (enumerate capabilities programmatically from each door), **never asserted from a hand-maintained map** — write the parity test that computes both sides. Every capability reachable from every door; refusals rendered per transport (FR-046/AR-58).*
Covered by: **T-16.5-a** (the flagship derived-parity test — CLI command-tree walk vs API public-surface introspection, both projected onto the library, reconciled with zero expected-capability literal), **T-16.5-b** (fault injection: an added/removed door capability must diverge the computed sets and FAIL — the test has teeth), **T-16.5-d** (per-transport refusal parity for the *same* library refusal), **T-16.5-P** (semantic parity as a universally-quantified law), reinforced by **T-16.5-enumCLI/enumAPI** (the two enumeration functions are pure functions of their door's structure, so neither side can hide a hand-list).

**Blocker B-3 directive (verbatim intent).** *Thin doors: assert no business logic in the door layer (doors translate, the library decides); the `qmb` CLI is the single command-line surface (DEC-0185 Ruling C); the door computes no run-id — the B-3 compiler owns identity.*
Covered by: **T-16.0-thin** (package-wide AST/structural gate — no domain arithmetic, no fp1/run-id computation, no compiler/fragment logic, no store access, no door-side cache, no HTTP transport), **T-16.1-b** (each capability resolves to exactly one library pure function), **T-16.1-f** (backtest compiles via the compiler + submits to the orchestrator and mints **no** run-id), **T-16.0-onecli** (one `qmb` entry point, no second CLI — DEC-0185).

**Named weak spots (to confirm against the module inventory at execution — no `doors/` source was read for this plan):**

| Locus | Risk implication | Mitigation in this plan |
|---|---|---|
| The **parity test itself** | A parity test built on a hand-maintained expected-capability list is decorative: it passes while the doors drift, because it never reads the doors. This is the single highest-severity failure mode of the epic. | **T-16.5-a/-b** force both surfaces to be *computed*; **T-16.5-b** proves a real divergence fails; §6 forbids any static expected-capability list in the fixture. |
| `doors/cli` refusal path | A raised (not returned) refusal, a swallowed refusal rendered as exit 0, or a stderr blob that is prose not JSON — each defeats an agent that branches on structure (AR-58). | **T-16.2-a/-b** assert nonzero exit + `{category,context,retryability}` JSON and return-not-raise-not-swallow; **T-16.2-d** keeps the programmer-error channel distinct. |
| `doors/**` cache / run-id surface | A door-side registry cache (R14) or a door-computed run-id (R5) moves identity/consistency into the untested wrapper — exactly the "may never" line in B-1. | **T-16.0-thin** AST-scans for cache containers / `lru_cache`/memo on resolution paths and for fp1/run-id computation; **T-16.4-a** proves completion routes through the port. |

**Priority ladder (derived — see Process Gap re: the missing 15-assertion handoff):**
- **P0 (must-pass gate; block the epic on any failure):** R1, R5, R6, R7, R11, R14, R18, R19, R21.
- **P1 (high — surface honesty & single-surface law):** R3, R4, R8, R9, R10, R15, R17, R20, R22.
- **P2 (important — completeness & scaffold):** R2, R12, R13, R16, R23, R25.
- **P3 / deferred:** R24 (MCP refusal rendering — post-CLI-v1).

---

## Section 4 — Independent Test List (authored from requirements, BEFORE any src read)

> **Discipline statement.** This section — and the whole plan — was written having read **zero files** under `qmb/src/qmb/doors/`. Every test below asserts what a *requirement* demands, derived from epics.md ACs, the B-1 spine, AR-58/AR-55/AR-13, CT-04, and DEC-0185 — never what the code happens to do. A failing test here is a **finding**, not a licence to edit source or weaken the assertion. Test-file paths are planned targets under `qa/tests/epic_16/` created at execution time. Level assignment follows "one behaviour, one level; the lowest level that can prove it wins" (taxonomy in §5). Property tests use `hypothesis` (`uv run --with hypothesis ...` if not synced). The CLI is exercised through click's `CliRunner` (in-process, deterministic), never a spawned shell.

### Group A — Thin click command tree (Story 16.1) → R1–R5

- **T-16.1-b** *(L2)* For each enumerated CLI capability, invoking the command calls **exactly one library pure function** with the parsed arguments and returns its result unchanged (spy/stub library surface); no capability is defined only in the door. **[R1]** **P0** *(thin-door / B-3)*
- **T-16.1-d** *(L2)* The command tree exposes the platform's single command-line surface — the capability **groups** (`backtest`, `data`, `optimize`, `ledger`, `config`, …) are present and enumerable, and there is exactly one `qmb` entry point. **[R3]** **P1**
- **T-16.1-e** *(L2)* A tunnel-running command whose config/resource prerequisite is **absent RETURNS a CT-04 typed refusal** (rendered per transport) naming the missing prerequisite; it does not proceed to run. **[R4]** **P1**
- **T-16.1-f** *(L3)* A `backtest` invocation compiles the run-config via the **Epic 13 compiler seam** and submits the resolved config to the **orchestrator entry-point seam**, and the door computes **NO run-id of its own** — the run identity is the compiler's resolved-config fp1 (assert the door neither mints nor derives an fp1). **[R5]** **P0** *(B-3 directive)*

### Group B — CLI refusal rendering (Story 16.2) → R6–R9

- **T-16.2-a** *(L2)* A library-returned CT-04 typed refusal renders at the CLI as a **nonzero exit code AND machine-readable stderr JSON** carrying `{category ∈ the seven, context (present, non-null), retryability ∈ {yes,no,after-condition}}`. **[R6]** **P0**
- **T-16.2-b** *(L2)* **Return-not-raise-not-swallow:** the library RETURNS the refusal and the door RENDERS it; **no exception crosses the door boundary** for a typed refusal, and no refusal is dropped or converted to a zero exit. **[R7]** **P0**
- **T-16.2-c** *(L2)* A successful run **exits zero** with no stderr refusal JSON. **[R8]** **P1**
- **T-16.2-d** *(L2)* A **programmer error** (not a typed refusal) surfaces as an **exception on a channel distinct from the refusal channel** — it is NOT rendered as a CT-04 stderr-JSON refusal. **[R9]** **P1**

### Group C — Python API pure re-export (Story 16.3) → R10–R13

- **T-16.3-a** *(L2)* The Python API door's public names **resolve to the library's own pure functions** (identity/alias, not door re-implementations), importable from the uv-added `qmb` package. **[R10]** **P1**
- **T-16.3-d** *(L2)* A door-routed library call on the **research path returns values and writes NO governed evidence** — no ledger line, no governed record emitted by the pure call path. **[R13]** **P2** *(governed-evidence machinery is Epic 15 — §7)*
- **T-16.3-b** *(L3)* A refusal returned through the Python door is the library's **refusal union VERBATIM** — the identical CT-04 value (category/context/retryability), **returned not raised**; exceptions only for programmer error. **[R11]** **P0**

### Group D — Autocomplete through the B-15 port (Story 16.4) → R14–R17

- **T-16.4-a** *(L2)* Shell autocomplete **enumerates through the single library-owned registry-read port** — the completion path calls the port (behavioural), and no door-side cache/second store is consulted (paired with the structural gate T-16.0-thin). **[R14]** **P0** *(AR-55)*
- **T-16.4-b** *(L2)* Resolution and autocomplete **answer identically**: over one as-of set the completion candidates equal the resolvable set the compiler would see — one port, one as-of, never divergent. **[R15]** **P1**
- **T-16.4-c** *(L2)* A **newly created Book** re-enumerates through the port as a **fresher as-of set** — not via a door cache refresh and not via a live-service query. **[R16]** **P2** *(as-of delivery owned by Epic 13/B-15 — §7)*
- **T-16.4-d** *(L2)* Autocomplete uses **click's native shell-completion** hooks and adds no bespoke completion machinery. **[R17]** **P1**

### Group E — Door-parity contract test (Story 16.5) → R18–R21 **[FLAGSHIP / R-006]**

- **T-16.5-a** *(L3)* **FLAGSHIP — derived parity.** The test enumerates the **CLI** door's capability surface programmatically (walks the click command tree to its leaves + parameters) AND enumerates the **Python API** door's surface programmatically (introspects public re-exports + signatures), projects each onto the **underlying library function** it adapts, and asserts the two **computed** sets are **identical** — both sides derived, **zero hand-maintained expected-capability map**. **[R18]** **P0**
- **T-16.5-b** *(L3)* **Parity has teeth (fault injection).** A capability present in one door's derived surface but **absent or semantically divergent** in the other makes the two computed sets **diverge and the test FAIL**; a mutation that adds/removes a door capability MUST fail this test (else the parity test is decorative). **[R19]** **P0**
- **T-16.5-c** *(L3)* The parity test is **scheduled at Tier 2** (`poe check-integration`, each package isolated) and completes against the **real capabilities landed by Epic 14** — its population is whatever surface both doors actually expose at execution time (Epic-14-bounded; §7). **[R20]** **P1**
- **T-16.5-d** *(L3)* **Per-transport refusal parity.** For the **same** library-returned refusal, the test confirms **CLI** renders nonzero exit + stderr JSON and **Python** returns the refusal union verbatim — the two transports carry identical CT-04 semantics. **[R21]** **P0**

### Group F — MCP door scaffold (Story 16.6) → R22–R25 **[scaffold-only; R24 DEFERRED post-CLI-v1]**

- **T-16.6-a** *(L2)* `doors/mcp` is **present as a sibling wrapper over the same library**, explicitly marked **post-CLI-v1**, and **NOT wired into / shipped in** the CLI-v1 surface — invoking it as a shipped door is absent/refused. **[R22]** **P1**
- **T-16.6-b** *(L0)* The MCP door is a sibling **over the same library** and imports **no HTTP-server/transport stack** (never stacked over HTTP); "localhost-bound by default" is a scaffold declaration only — runtime binding deferred (§7). **[R23]** **P2**
- **T-16.6-c** *(L2)* **CLI v1 ships first and the MCP door does not gate it**: the CLI surface is complete and usable with `doors/mcp` unshipped — no CLI capability depends on the MCP door. **[R25]** **P2**
- **T-16.6-d** *(DEFERRED, post-CLI-v1)* When the MCP door later renders a refusal, `error.data` carries the refusal union verbatim — **not shippable/testable in V1**; scaffold-only now. **[R24]** *(see §7)*

### Group G — Targeted L1 units & properties (cross-cutting)

- **T-16.2-render** *(L1)* The refusal-rendering **pure function** maps any CT-04 `TypedRefusal` to `(exit_code ≠ 0, stderr-JSON{category, context, retryability})` — the shape, isolated from CLI wiring. **[R6]**
- **T-16.5-enumCLI** *(L1)* The CLI-capability enumeration is a **pure function of the click command tree** (walks to leaves), returning the same surface for the same tree — so the parity test can never smuggle in a hand-list. **[R18 mechanism]**
- **T-16.5-enumAPI** *(L1)* The API-capability enumeration is a **pure function of the module's public surface** (introspection of re-exports + signatures). **[R18 mechanism]**
- **T-16.3-P** *(L6, property)* Over arbitrary CT-04 refusals, the Python door returns the **field-identical** refusal value it received from the library — no transformation (hypothesis, ≥200 cases). **[R11]**
- **T-16.5-P** *(L6, property)* Over the derived capability set and arbitrary inputs, each capability invoked through the **CLI** door and through the **Python** door maps back to the **same library result** (value or refusal) — semantic parity as a universally-quantified law, not a spot check. **[R18]**

### Group H — Static / structural gates (L0, thin-door directive)

- **T-16.0-thin** *(L0)* AST/structural scan across `doors/{cli,api,mcp}`: **no domain/business logic** — no `Money`/`Price`/`Quantity` arithmetic, no fp1/**run-id computation**, no compiler/fragment/precedence logic, no direct store access; **no door-side cache** — no module-global mutable resolution cache, no `lru_cache`/memo on a resolution path, no import edge to a second store; **no HTTP transport import** in `api/` or `mcp/`. Doors translate; the library decides. **[R1, R5, R12, R14, R23]** **P0** *(B-3 directive; mirrors the Epic-13 T13-007 AST technique over `qmb/doors/**`)*
- **T-16.0-onecli** *(L0)* Exactly **one** console-script entry point (`qmb`); no second command-line surface anywhere in the package (DEC-0185 — "no second command line"). **[R3]** **P1**
- **T-16.0-pins** *(L0)* `click` is present at the **`qmb_cli_pin`** value `click==8.4.2` — referenced from the registry key, never a restated literal. **[R2]** **P2**
- **T-16.0-tree** *(L0)* `doors/` contains the three door subpackages `cli`, `api`, `mcp`. **[R22 presence]** **P1**

---

## Section 5 — Test-Level Architecture Mapping (L0–L6)

> Reconstructed taxonomy (test-design-qa.md absent — see Process Gap), harmonized with the two sibling PLANs. Rule enforced: **one behaviour, one level; the lowest level that can meaningfully assert it wins** — no behaviour re-asserted higher except where a property adds breadth a unit cannot (flagged). **T2 tier scope pulls the mass onto L2 + L3**, with targeted L1 and an L6 review.

| Level | Meaning here | Execution band | Epic-16 population |
|---|---|---|---|
| **L0** | Static / structural gates on door source (thin-door AST scan, one-CLI, pin, subpackage presence, no-HTTP import). | tier-1 lint/type gate | T-16.0-thin, T-16.0-onecli, T-16.0-pins, T-16.0-tree, T-16.6-b — **5** |
| **L1** | Pure unit — one pure function, no wiring (refusal→JSON shape; the two capability-enumeration functions). | tier-1 (`poe check`) | T-16.2-render, T-16.5-enumCLI, T-16.5-enumAPI — **3** |
| **L2** | Component/integration in-process — a door wired to a stubbed library surface, via `CliRunner` or a direct API import; deterministic, no OS process. **T2 workhorse.** | tier-1/2 | T-16.1-b/-d/-e, T-16.2-a/-b/-c/-d, T-16.3-a/-d, T-16.4-a/-b/-c/-d, T-16.6-a/-c — **15** |
| **L3** | Contract conformance — the **door-parity contract test** (AR-19 executable contract test), CT-04 per-transport rendering, compiler/orchestrator submit seam. **T2 workhorse.** | **tier-2** (`poe check-integration`) | T-16.1-f, T-16.3-b, T-16.5-a/-b/-c/-d — **6** |
| **L4** | Scenario / golden-path — the CLI/API walk of SCN-0012 (door-fronted replay run). | tier-2 | **0 shipped** — bounded by Epic 14/15 capabilities; the door half is covered piecewise by T-16.1-f + T-16.5-c (§7). |
| **L5** | System / orchestrated — CLI `backtest` → process-per-run → ledger line end to end. | tier-2/system | **0** — owned by **Epic 15** (the door only submits; §7). |
| **L6** | Property-based breadth **and the requirements-fidelity REVIEW** — in this project the L6 level carries the `L6-REVIEW.md` deliverable (one question per test: does it assert the requirement, or what the code does?) plus hypothesis properties. | tier-2 / review | T-16.3-P, T-16.5-P (properties) + **the L6-REVIEW pass** (all reqs). |

**Planned counts — L0: 5 · L1: 3 · L2: 15 · L3: 6 · L6: 2 properties + 1 review pass.** Executable total **31**, plus the L6 requirements-fidelity review, plus **1 deferred** (T-16.6-d). L4 = 0 (bounded), L5 = 0 (Epic 15).

**Lower-level-wins applications:**
- CLI refusal rendering: the *shape* is asserted once at **L1** (T-16.2-render); the *wired* nonzero-exit + stderr behaviour at **L2** (T-16.2-a). Two distinct behaviours (pure mapping vs door wiring), not a duplicate.
- Thin-door "no logic / no cache / no run-id" is a **structural** claim → **L0** (T-16.0-thin); the *behavioural* consequences (capability→one function, completion→port, backtest→no run-id) sit at **L2/L3** (T-16.1-b, T-16.4-a, T-16.1-f). Structural + behavioural halves, not a re-assertion.
- Parity: the **derivation mechanism** is unit-proven at **L1** (T-16.5-enumCLI/enumAPI), the **contract** at **L3** (T-16.5-a/-b/-d), the **semantic law** at **L6** (T-16.5-P). Each level proves what the one below cannot.
- The Python refusal-verbatim behaviour is asserted concretely at **L3** (T-16.3-b) with an **L6** property (T-16.3-P) for breadth — not a duplicate concrete case.

---

## Section 6 — Fixtures, Data & Parity/Refusal Strategy

**Runner.** `uv run pytest qa/tests/epic_16 -q` from the worktree root (tier-1 L0–L2); the parity/contract tests (L3) under the project's `poe check-integration` band (tier-2, isolated env per AR-18). Properties: `uv run --with hypothesis ...` if hypothesis is not in the synced dev group. The CLI is driven through click's **`CliRunner`** in-process (deterministic exit codes + captured stderr), never a spawned shell. No test edits source; a failing test is recorded as a **finding**.

**Fixtures (controlled test fixtures only; no product mock data — DEC-0007):**
- **Stub library surface.** A small in-memory stand-in for the library's pure-function surface exposing a handful of named capabilities, each returning a value *or* a CT-04 refusal on cue — the substrate for T-16.1-b, the refusal tests, and the parity tests. It lets a door be exercised without any real Epic-13/14/15 behaviour.
- **CT-04 refusal corpus.** Shape-faithful `TypedRefusal` values spanning **all seven categories**, `context` both empty-structured and populated (never null), and each `retryability` arm incl. `after-condition` with its descriptor — the substrate for T-16.2-a, T-16.3-b, T-16.2-render, and the properties. A test that passes against a shape-unfaithful refusal fake is itself a finding.
- **Registry as-of stub** for the B-15 port: an immutable fingerprinted as-of set plus a *fresher* as-of carrying a newly created Book (T-16.4-b/-c) — delivered as passive data, never a live-service call.
- **Compiler + orchestrator seam spies** (T-16.1-f): a spy compiler that records the resolved-config fp1 it computed, and a spy orchestrator entry point that records what was submitted — so the test can assert the door forwarded the compiler's fp1 and minted none of its own.

**Parity strategy (the spine of this audit — R-006):**
1. **Both sides derived, never listed.** The parity fixture contains **no static expected-capability list**. `enumerate_cli()` walks the live click command tree to its leaves; `enumerate_api()` introspects the API module's public re-export surface. The test reconciles the two *computed* sets through the library function each maps to (the library is the pivot). Any hand-maintained map in the fixture is itself a finding (T-16.5-enumCLI/enumAPI guard the enumerators' purity).
2. **The test must be able to fail.** T-16.5-b injects a divergence (a capability added to one derived surface, or one door's rendering of a shared refusal altered) and asserts the parity test FAILS — a parity test that cannot fail on real drift is decorative (the exact `findings.csv`-is-empty-because-nothing-could-fail trap the Epic-13 L6 review named).
3. **Per-transport, same refusal.** Refusal parity (T-16.5-d) takes *one* library refusal and checks both renderings against it: CLI → nonzero exit + stderr JSON with the three fields; Python → the identical value. Never two independently-authored expectations.

**Refusal discipline.** Every "is refused" assertion (T-16.1-e, T-16.2-a/-b, T-16.3-b, T-16.5-d) checks a **RETURNED** CT-04 typed refusal of the correct category, rendered per transport — never a raised exception across the door boundary (CT-04 invariant; exceptions reserved for programmer error, asserted distinct by T-16.2-d).

**Values referenced, never restated.** The click pin comes from the `qmb_cli_pin` registry key, not a literal (T-16.0-pins); refusal categories come from CT-04's enum. The plan names keys, not numbers.

---

## Section 7 — Coverage Targets, Weak-Spot & Untestable/Deferred

**Global posture.** Coverage is a *floor and a map*, never the goal — a green line with no assertion is a finding (the Epic-13 L6 review's central lesson: "N passed, 0 findings" can be an overstatement of what was *verified*). Targets are gates for the epic to pass audit; a shortfall is recorded, not waived.

| Target | Floor | Rationale |
|---|---|---|
| `doors/` package line coverage | ≥ 90% | Small, thin layer; there is no excuse for unexercised door branches. |
| `doors/cli` refusal-path branch coverage | ≥ 95% | The nonzero-exit / stderr-JSON / return-not-raise / programmer-error branches are the agent-facing contract (AR-58). |
| Parity **fault-sensitivity** | must-fail | T-16.5-b: a mutation adding/removing a door capability, or altering one door's refusal rendering, MUST fail the parity test. A surviving mutation means the parity test is decorative — record as a finding. |
| Thin-door structural gate | zero violations | T-16.0-thin: any domain arithmetic, fp1/run-id computation, door-side cache, or HTTP import in `doors/**` is a finding, not a warning. |

**Weak-spot execution order (do the risky work first):**
1. The **derived parity test** + its fault-injection twin (T-16.5-a/-b) — the epic's centre of gravity (R-006).
2. **CLI refusal rendering** (T-16.2-a/-b/-d) + **Python verbatim** (T-16.3-b) — the AR-58 per-transport contract.
3. **Thin-door structural** (T-16.0-thin) + **no run-id / compile-and-submit** (T-16.1-f) — the B-3 directive.
4. **Autocomplete-through-the-port** (T-16.4-a/-b) — the B-15 no-second-cache guarantee.

**Untestable / deferred / blocked in Epic 16 isolation (findings, not omissions):**
- **R24 (MCP refusal rendering — `error.data` verbatim).** The MCP door is scaffolded-not-shipped (SC-08/R22); its refusal-rendering behaviour is **not reachable in V1**. **Deferred to the post-CLI-v1 MCP shipment.** Testable now: scaffold presence (T-16.6-a) and the no-HTTP structure (T-16.6-b); the `error.data` rendering is not.
- **R23 runtime half (localhost-bound by default).** Only the **structural** "sibling over the same library, no HTTP stack" is assertable now (T-16.6-b, L0). Actual localhost binding is a runtime behaviour of the unshipped door — deferred with R24.
- **R20 parity population is Epic-14-bounded.** The parity **mechanism** (derived both-sides reconciliation) is fully testable now; the **set of capabilities** it ranges over is "the real capabilities landed by Epic 14." Where Epic-14 capabilities are not yet present, the parity surface is bounded to what both doors expose — the mechanism passes, the coverage is recorded as bounded, not as a gap in Epic 16. *(Epic-binding: Epic-14 capabilities are owned by Epic 14; not tested here.)*
- **R12 consumer (UI backend) does not exist in V1.** epics.md UX Design Requirements: "None. V1 has no UI surface." The **door property** — Python API is importable/in-process and imports no HTTP transport — is testable now (T-16.0-thin, T-16.3-a); the *"UI backend consumes it in-process"* consumer relationship has no consumer to exercise. Recorded as a door-side-only assertion.
- **R13 governed-evidence machinery is Epic 15.** At the door level we assert the research call path emits **no ledger line / no governed record** (T-16.3-d). The full governed-evidence semantics (what *would* make evidence governed — the orchestrator/ledger) are **Epic 15**; only the door's non-emission is in scope.
- **R5 / R16 seams are Epic 13.** The door asserts it *submits the compiler's resolved config and mints no run-id* (T-16.1-f) and *enumerates a fresher as-of* (T-16.4-c); the **compiler's fp1 computation** and the **as-of set delivery** themselves are Epic 13, exercised there.
- **Process authorities absent.** test-design-qa.md (template + L0–L6) and QMX-handoff.md (15 P0/P1 assertions + risk-gate rows) are missing from the worktree; §1/§3/§5 are reconstructed and R-006/B-3 are taken from the task brief. This is the single largest caveat on the plan's fidelity to the intended template — recorded, not worked around.

---

## Section 8 — Execution, Traceability Matrix & Exit Criteria

**Execution.**
- Run from the worktree root: `uv run pytest qa/tests/epic_16 -q` (L0–L2, tier-1); the L3 parity/contract band under `poe check-integration` (tier-2, isolated env per AR-18). Properties: `uv run --with hypothesis pytest ...`.
- All tests live under `qa/` per the audit's write-boundary; **source is read-only evidence.** A failing test is a **finding recorded in this epic's `findings.csv`**, never a reason to edit `doors/` source or soften an assertion.

**Traceability (requirement → test → priority → level → status):** every R1–R25 maps to ≥1 test.

| Req | Test IDs | Prio | Level(s) | Status |
|---|---|---|---|---|
| R1 | T-16.0-thin, T-16.1-b | P0 | L0,L2 | planned |
| R2 | T-16.0-pins | P2 | L0 | planned |
| R3 | T-16.0-onecli, T-16.1-d | P1 | L0,L2 | planned |
| R4 | T-16.1-e | P1 | L2 | planned |
| R5 | T-16.1-f, T-16.0-thin | P0 | L3,L0 | planned |
| R6 | T-16.2-a, T-16.2-render | P0 | L2,L1 | planned |
| R7 | T-16.2-b | P0 | L2 | planned |
| R8 | T-16.2-c | P1 | L2 | planned |
| R9 | T-16.2-d | P1 | L2 | planned |
| R10 | T-16.3-a | P1 | L2 | planned |
| R11 | T-16.3-b, T-16.3-P | P0 | L3,L6 | planned |
| R12 | T-16.0-thin, T-16.3-a | P2 | L0,L2 | planned (door-side only; consumer absent — §7) |
| R13 | T-16.3-d | P2 | L2 | planned (door-side; governed-evidence = Epic 15) |
| R14 | T-16.0-thin, T-16.4-a | P0 | L0,L2 | planned |
| R15 | T-16.4-b | P1 | L2 | planned |
| R16 | T-16.4-c | P2 | L2 | planned (as-of delivery = Epic 13) |
| R17 | T-16.4-d | P1 | L2 | planned |
| R18 | T-16.5-a, T-16.5-enumCLI, T-16.5-enumAPI, T-16.5-P | P0 | L3,L1,L6 | planned |
| R19 | T-16.5-b | P0 | L3 | planned |
| R20 | T-16.5-c | P1 | L3 | planned (population Epic-14-bounded — §7) |
| R21 | T-16.5-d | P0 | L3 | planned |
| R22 | T-16.0-tree, T-16.6-a | P1 | L0,L2 | planned |
| R23 | T-16.6-b | P2 | L0 | planned (structural half; runtime binding deferred) |
| R24 | T-16.6-d | P3 | L2 | **deferred (post-CLI-v1 MCP shipment)** |
| R25 | T-16.6-c | P2 | L2 | planned |

**Exit criteria (epic passes audit when):**
1. Every **P0** test is green, and the **parity fault-injection** T-16.5-b actually fails on an injected divergence (the parity test is proven able to fail).
2. **R-006 satisfied:** T-16.5-a computes both door surfaces with no hand-maintained map; T-16.5-b/-d/-P confirm drift-fails, per-transport refusal parity, and the semantic law.
3. **B-3 directive satisfied:** T-16.0-thin shows zero domain logic / no cache / no run-id in `doors/**`; T-16.1-f shows `backtest` compiles-and-submits and mints no run-id; T-16.0-onecli shows one `qmb` surface (DEC-0185).
4. **AR-58 satisfied:** every "is refused" test asserts a *returned* CT-04 refusal of the correct category, rendered per transport (CLI nonzero+JSON; Python verbatim), with the programmer-error channel distinct (T-16.2-d).
5. `doors/` meets the §7 coverage floors, each covered branch tied to an assertion.
6. Every deferred/bounded requirement (R24; R23 runtime; R20 population; R12 consumer; R13/R16/R5 seams) has a recorded reason and an owning epic (§7) — none silently counted as passed, none as failed.

**Coverage ledger** to be maintained alongside execution under `qa/epics/epic_16_qmb-cli-doors/` — one row per §4 test id → {level, status PASS/FINDING/DEFERRED, evidence path}, with `findings.csv`, `RESULTS.md`, and the `L6-REVIEW.md` requirements-fidelity pass as the closing artifacts.
