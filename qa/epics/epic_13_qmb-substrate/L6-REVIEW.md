# Epic 13 — QMB substrate — L6 requirements-fidelity review

**Verdict: GAPS.**

Scope of this review: one question per test — *does it assert what the requirement demands, or
what the implementation happens to do?* — plus the requirements in Epic 13's section of
`epics.md` that no test covers. Tests were not run and not edited; source was not re-reviewed.
Authorities read: `_bmad-output/planning-artifacts/epics.md` Epic 13 (stories 13.1–13.5),
`docs/contracts/ct-07-lineage-edge.yaml`, `docs/contracts/ct-28-book-binding.yaml`,
`docs/scenarios/SCN-0012-qmb-replay-run.md`, `docs/registry/variables.yaml`, root `pyproject.toml`
(`[tool.poe.tasks.check]`, `[tool.pyright]`).

**Confirmation of the PLAN §7.6 caveat:** `_bmad-output/test-artifacts/` does not exist in this
worktree. `test-design-qa.md` and `test-design/QMX-handoff.md` — named as authorities for the
L0–L6 architecture, the Per-Epic template, the 15 P0/P1 assertions and the risk-gate rows —
are absent. The L-level scheme and the R-004 / R-008 / P0-13 gate text used by the PLAN are
reconstructions. This review therefore judges fidelity against `epics.md` + `docs/` only.

The suite is strong where it is strong: the identity-law properties (T13-401/402/403/404),
namespace disjointness (T13-405), CT-01 canonical-form collapse, AD-5 format-version handling
(T13-303/304), SemVer-display-only (T13-307) and the CT-04 refusal harness (T13-308) all assert
the requirement, not the code. The gaps below are concentrated in three places: **money-safety
invariants of CT-28**, **assertions that read a self-declared marker constant instead of a
behaviour**, and **the Tier-1 gate's unexecuted half**.

---

## 1. Wrong-expectation tests

Ordered by severity. "What the requirement actually says" quotes the governing authority.

### 1.1 T13-306 — the assertion the PLAN promised was replaced by a duplicate of T13-305 (MATERIAL)

*`qa/tests/epic_13/test_l3_contract.py:206-222`*

**What the test asserts.** That the minted replay binding fingerprints differently from a
world=LIVE binding, and that `check_incomparable_to_live(...)` returns a refusal. Both facts are
already asserted, verbatim, by T13-305 at lines 186-202 (`binding.fingerprint != live_epoch`;
`check_incomparable_to_live(...)` refuses). T13-306 adds no distinct assertion.

**What the requirement actually says.** CT-28 invariant, ratified:

> "A binding record that fingerprints **equal to an existing one** is an `invalid input` refusal,
> never AD-10's silent idempotent accept — that path exists for byte-identical re-writes of the
> same work, **not for a second pot of money**; two copies of one Book version on one account are
> distinct by mint and are never merged (DEC-0143)."

CT-28's own refusal-category row repeats it: "*invalid input (an equal-fingerprint re-binding;
an absent state_carry declaration)*". PLAN §4.3 planned exactly this — "a binding record
fingerprinting **equal** to an existing one → a CT-28 `invalid input` refusal (never AD-10's
silent idempotent accept …)" — and PLAN §3 counts T13-306 as one of the five tests that satisfy
risk gate **R-004** ("no silent overwrite").

**Why this is a wrong expectation, not merely a thin one.** The delivered test's docstring and
its RESULTS row were rewritten to describe what the code can show ("fingerprints apart from live
(world in identity)") rather than what the contract demands. The equal-fingerprint refusal path
is never exercised anywhere in the 43-test suite. RESULTS line 119 nevertheless records
"R-004 satisfied: … T13-306 … PASS". That exit-criterion claim is not supported.

### 1.2 T13-205 — asserts the *accept* side of the same invariant (MATERIAL)

*`qa/tests/epic_13/test_l2_integration.py:161-172`*

**What the test asserts.** `again.binding_fp1 == config.binding_fp1` under the comment
"*exactly one identity: same inputs -> the same single binding*" — i.e. a second mint over
identical inputs yields an identical binding fingerprint and is accepted.

**What the requirement actually says.** 13.5 AC3 is "*mints exactly ONE AD-29/CT-28 binding with
`world=replay`*" — a cardinality statement about one run, which this test conflates with
determinism across two runs. Under CT-28 the *second* record fingerprinting equal to the first is
the precise thing that must refuse. Nothing in the suite separates "the compiler is deterministic"
(legitimate, and already covered by T13-402) from "a second binding record may carry an existing
fingerprint" (a CT-28 `invalid input`). As written, T13-205 documents the accepting behaviour of
the mint path as though it were the requirement.

**What the requirement demands instead:** exactly-one-per-run should be asserted by counting the
bindings a single compile mints; equal-fingerprint re-mint should be asserted as a refusal.

### 1.3 T13-112 — cannot distinguish "override forces unrated" from "always unrated" (MATERIAL)

*`qa/tests/epic_13/test_l1_unit.py:295-309`*

**What the test asserts.** `overridden.fold_rating == FOLD_UNRATED` on the seed-overridden compile.
It never asserts anything about `base.fold_rating` — the non-overridden compile it already built
on line 299.

**What the requirement actually says.** 13.5 AC2: "*Given an invocation flag that overrides the
seed, When it is applied, Then the binding is stamped `seed_overridden` and the run's fold is
forced to `unrated`*". SCN-0012 step (2) pins the counterfactual explicitly: "*here it is supplied
and not overridden, so the run's fold **stays rated** — a flag override would stamp
`seed_overridden` and force the fold to unrated*".

**Why it is wrong.** An implementation that hard-codes every fold to `unrated` passes this test.
The requirement is a *forcing* relation; the test only samples one side of it. The rated baseline
(`base.fold_rating != FOLD_UNRATED`, and `base.replay_binding.seed_overridden is False`) is the
half that gives the assertion its meaning, and it is absent.

### 1.4 T13-401c — premises that a `world=simulated` compile succeeds (MATERIAL)

*`qa/tests/epic_13/test_l4_property.py:72-98`*

**What the test asserts.** It compiles a config with `clock="simulated"` +
`data_provenance="synthetic-tainted"` through `_fp(...)`, which `unwrap`s — so the test *requires
that compile to succeed* — and then asserts the resulting fp1 differs from the replay baseline.

**What the requirement actually says.** SCN-0012 step (5): "*Simulated-Instant typing is
**refused** until GAP-0048*". SCN-0012 Branch B: a store-persisted synthetic read is typed
`world = simulated`, and "*for governed evidence that is a **policy rejection** until
GAP-0048*". PLAN §7.4 records `world=simulated` unlock as GAP-0048-gated and explicitly *not*
assertable in this epic.

**Why it is wrong.** The test converts a GAP-0048-gated, refused-until-unlocked path into a
success premise in order to demonstrate an unrelated law (that world is an identity field).
It bakes an implementation behaviour into the requirement-side scaffolding of an R-004 property,
and it silently certifies as working a path the corpus says is not unlocked. The identity law it
wants is fully demonstrable without it (T13-401/401b already carry R-004); if the simulated path
is exercised at all, the requirement-faithful assertion is *refusal or distinct identity*, never
plain success. Note the tension inside the suite itself: T13-110 requires
`clock=replay + synthetic-tainted` to refuse `invalid input`, while T13-401c requires
`clock=simulated + synthetic-tainted` to succeed — and no test asks whether `world=simulated`
should be reachable in V1 at all.

### 1.5 T13-201, T13-202, T13-207 — assertions over self-declared marker constants (MATERIAL as a class)

*`test_l2_integration.py:53-54, 62-65, 212-213`*

These read a constant the source declares about itself and assert it has the value the requirement
would want:

| Test | Assertion | Problem |
|---|---|---|
| T13-201 | `cli_door.HOLDS_CACHE is False`, `api_door.HOLDS_CACHE is False`, `COMPUTES_RUN_ID is False` | An implementation that holds a cache and sets the flag `False` passes. |
| T13-202 | `u.hub.kind == HUB_KIND == "passive-storage"`, `STATE_KIND == "as-of set"`, `identity["hub"] == "passive-storage"` | Constant-equals-constant. Proves a string literal, not that no live/central-service path exists. |
| T13-207 | `BOUND_FROM_RESOLVED_CONFIG is True`, `AMBIENT_DISCOVERY is False` | Self-description; asserts nothing about how the seam actually obtains its binding. |

**What the requirements actually say.** 13.2 AC1: "*it resolves through the ONE library-owned
registry-read port, and **no door-side or second cache exists***". 13.2 AC5: "*it is dumb passive
storage — **never the dead DEC-0084 central service***". SCN-0012 Given: "*the CLI door enumerates
through it for autocomplete, so resolution and autocomplete can never answer differently — there
is no door-side cache*".

These are structural/behavioural claims. The suite already demonstrates it knows how to assert
one structurally — T13-007 AST-scans the whole package for module-global mutable state. The same
technique applied to `qmb/doors/**` (no module-level cache containers, no `lru_cache`/memo on a
resolution path, no import edge to a second store) would assert the requirement; a declared
boolean does not. T13-201's behavioural half is also mis-aimed: it calls **`u.port.complete(...)`**
— the port's own enumeration — where the requirement is about the **CLI door's** autocomplete
routing through that port. The door's autocomplete is never invoked.

Partial credit where it is due: T13-202's "*a set fingerprint not stored is an
`unavailable dependency` refusal, not a live fetch*" (lines 72-79) **is** a requirement-faithful
behavioural assertion of the no-live-service rule, and T13-101's `serve()`/`main()` refusal is a
real behavioural assertion beside its `SHIPPED is False` markers.

### 1.6 T13-107 — the collision refusal is never asserted at the compiler boundary (MODERATE)

*`test_l1_unit.py:191-204`* (and the `"collision"` entry of T13-308 at `test_l3_contract.py:313`)

**What the test asserts.** `merge_book_bms_keys({...}, {...})` — a helper called directly with two
hand-built dicts — returns `invalid input`.

**What the requirement actually says.** 13.4 AC2: "*Given a key that collides across the Book and
BMS fragments, **When compilation runs**, Then it returns a **compile-time** typed refusal*".

**Why it matters.** The subject of the AC is the compiler. Nothing asserts that
`compile_run_config` propagates the collision refusal rather than swallowing or bypassing it —
and the compiler is the epic's declared complexity hot-spot (cyclomatic 36). If colliding
fragments are genuinely unconstructible through the materializer (T13-405 shows a mixed-namespace
fragment is refused), that should be recorded as the reason the compiler-boundary case is
unreachable — not left as an untested assumption behind a helper-level test.

### 1.7 T13-204 — pins the implementation's directory-naming scheme; no write is ever performed (MODERATE)

*`test_l2_integration.py:123-127`*

`assert run_dir == config.fingerprint.value.replace(":", "-")` asserts the exact sanitisation the
source chose. The requirement (13.4 AC4) is "*the artifact **is written into** the run's output
directory **named by the run id***". Nothing in the suite writes or reads a file; the assertion is
over a returned string. The requirement-faithful shape is: the artifact lands on disk, in a
directory that identifies the run id, and re-reading it yields the same fp1. The `:`→`-` mapping
is an implementation detail that a requirement-derived test would not have known to predict.

Also on this line: "*all doors compute the SAME fingerprint*" is asserted for the **API door
only** (line 129). See §2.7.

### 1.8 T13-301 / T13-302 — pins an edge type the requirement never names (MINOR)

*`test_l3_contract.py:71, 92`* — `assert frag.lineage.edge_type is EdgeType.OCCURRENCE_OF`.

13.3 AC1/AC2 say only "*carrying an AD-16/CT-07 lineage edge back to the CT-22 source*" — no edge
type is named. CT-07 ratifies fourteen V1 edge types; `occurrence-of` is described there as
relating "*the occurrence*" to "*the computation identity*", which is a defensible but not
required reading for a config fragment derived from a Book charter. The requirement-faithful
assertion is `edge_type ∈` CT-07's ratified enum with the from_ref/to_ref roles correct (which the
test does assert, on the following two lines). The `is OCCURRENCE_OF` line is the source's choice
promoted to a requirement. Harmless today; it will produce a false FAIL if the edge type is ever
corrected.

### 1.9 T13-108 — asserts an implementation choice alongside the requirement (MINOR)

*`test_l1_unit.py:210`* — `assert SANCTIONED_OVERLAP_KEYS == frozenset()`.

No authority says the V1 sanctioned-overlap set is empty; that is the source's decision. The rest
of T13-108 (passing `sanctioned_overlap={"reporting"}` and asserting BMS wins) **is**
requirement-faithful and correctly asserts 13.4 AC2's "*in any sanctioned overlap BMS outranks
Book*". Keep the second half; the first line documents rather than verifies.

---

## 2. Requirements in Epic 13's section of `epics.md` that NO test covers

Fourteen, grouped by story. Items marked **(gate)** are part of the ratified Tier-1 command the
AC names.

| # | Requirement (epics.md Epic 13) | Status |
|---|---|---|
| 2.1 | **13.1 AC5** — "*ruff + pyright-strict + **pytest** pass*" **(gate)** | T13-006 runs ruff and pyright only; its docstring states "pytest-green is observed via the independent suite, not re-run here". The independent suite is this audit's own tests — qmb's shipped suite and the `cov-report` per-package/contract-module coverage floors are never executed. |
| 2.2 | **13.1 AC5 / NFR-02** — "*no ambient nondeterminism*" as enforced by the ratified gate **(gate)** | `[tool.poe.tasks.check]` sequences `fmt-check, lint, types, test, cov-report, test-tools, money-path-scan, **ambient-scan**, mock-data-scan, secret-scan`. The suite invokes two of the ten. `ambient-scan` is the tier-1 scanner for exactly the NFR-02 property the PLAN maps onto this AC; `money-path-scan` (NFR-02 enforcing FR-001, relevant to `starting_capital`/`Money`) is likewise never run over qmb. T13-402 samples determinism on one integer field; it is not a substitute for the scanner. |
| 2.3 | **13.1 AC1** — "*it **builds** as ONE wheel … **installs via `uv add qmb`***" | No build and no install is performed. T13-001 reads `project.name`, `module-name` and the `scripts` table from `pyproject.toml`. That the package actually builds to one wheel, and that an isolated install resolves, is asserted nowhere (the workspace has `poe check-integration` → `build-all` + `isolated-build` for precisely this). |
| 2.4 | **13.1 AC5** — "*the package is pure-Python and **OS-neutral***" | T13-007 asserts only the absence of `.so/.pyd/.dll/.dylib` under `qmb/src`. OS-neutrality (no platform-conditional imports, no OS-specific path or API assumptions) is untested. |
| 2.5 | **13.1 AC3** — "*When any module, symbol, or **docstring** is named, Then none uses "engine", "kernel", "exam", "plugin"*" | T13-005 scans file/directory names and `__all__` exports for those four words, and full file text **only for "snapshot"**. Docstrings and non-exported symbols are never scanned for engine/kernel/exam/plugin — the exact surface the AC names. |
| 2.6 | **13.2 AC4** — "*When one as-of is resolved, Then it is **frozen for every trial***" | T13-203 asserts `frozen.frozen is True` (a declared flag) and that alias/`name@latest` refuse after admission. It never lands a **fresher as-of into the hub after admission** and re-resolves to prove the frozen set still answers. The freeze invariant — the entire point of SC-11 — is untested. |
| 2.7 | **13.4 AC4** — "*When **any door** fingerprints it, Then **all doors** compute the SAME fingerprint*" | Only `qmb.doors.api` is compared against the library (T13-204:129-139). The **CLI door is shipped in V1** and is never asked to compute a fingerprint. PLAN §7.3 correctly defers *full* door parity to Epic 16, but "all doors agree on the run-id root" is a 13.4 AC4 assertion about the doors that ship now. |
| 2.8 | **13.2 AC1 / SCN-0012 Given** — the **CLI door's autocomplete** resolves through the one port | The test calls `u.port.complete(...)` directly (§1.5). No door-side entry point is exercised. |
| 2.9 | **13.4 AC2** — collision refusal "*when compilation runs*" | Asserted only at the `merge_book_bms_keys` helper (§1.6). |
| 2.10 | **13.5 AC3 / CT-28** — equal-fingerprint re-binding is an `invalid input` refusal, never a silent idempotent accept | Planned as T13-306, then dropped (§1.1). This is the epic's money-safety invariant. |
| 2.11 | **13.5 AC2 / SCN-0012 (2)** — the non-overridden run's fold **stays rated** | Only the `unrated` branch is asserted (§1.3). |
| 2.12 | **13.4 AC4** — the artifact "*is **written into** the run's output directory*" | No filesystem write or read occurs anywhere in the suite (§1.7). |
| 2.13 | **13.4 AC1** — the **middle** of the precedence chain: run spec > BMS fragment, and BMS fragment > Book fragment | T13-105 asserts the `LAYER_PRECEDENCE` tuple (correctly, against the AC's own ordering) and behaviourally proves only flags > run spec, run spec > defaults, and Book fragment > defaults. The two mid-chain relations — including BMS-over-Book, the one the AC calls out by name — are never observed through `compile_run_config`. If the disjoint namespaces plus an empty sanctioned-overlap set make them unobservable, that is the finding to record. |
| 2.14 | **13.5 AC3** — "*mints **exactly ONE** … binding*" | Asserted as "two compiles agree on one fingerprint" (§1.2), not as a count of bindings minted by a single compile. |

Correctly and explicitly deferred (PLAN §7, RESULTS "Deferred / partial"), **not** counted as gaps
above: the CT-32 *result*-fingerprint half of P0-13 (Epic 14 / Story 14.7); the 13.5 AC4 runtime
(sizing, R-freeze, exit execution, AD-40 enforcement at the open — Epic 14); full CLI/API/MCP door
parity and the MCP door's shipment (Epic 16, SC-08); GAP-0048-gated content. Those deferrals are
sound and properly recorded.

One further PLAN commitment not delivered: PLAN §6 names "*the golden-scenario **SCN-0012** for the
identity chain*" as a fixture class. No test file references SCN-0012 or walks its steps; the L4
level contains properties only. The scenario's identity chain (resolved-config fp1 = run-id root =
ledger key, replay binding distinct/incomparable, re-resolution reproduces or refuses) is covered
piecemeal by T13-204/305/406, so this is a traceability gap rather than a coverage hole.

---

## 3. Adjudication of `findings.csv`

`findings.csv` contains **the header row and nothing else** — zero findings.

- **Genuine requirement violations among the rows: 0.**
- **Wrong test expectations among the rows: 0.**
- Nothing to adjudicate: there are no rows.

The adjudication that *is* needed runs the other way. The zero-findings result is not corroborated
by the suite, because in the areas listed in §1 and §2 the suite could not have produced a finding:
an equal-fingerprint re-binding is never attempted, an always-`unrated` fold would pass, a
door-side cache would pass, a fresher as-of arriving mid-sweep is never introduced, the CLI door
never fingerprints anything, and eight of the ten steps of the Tier-1 gate the AC names are never
run. "43 passed, 0 findings" is an accurate report of what was executed and an overstatement of
what was verified.

Two items the RESULTS file records as *observations* rather than rows are correctly classified:

- **Book-fragment `starting_capital` default honoured by the resolver but never emitted by the
  materializer.** 13.5 AC1 is permissive — "*the Book fragment **may** default it*" — so no AC is
  violated. Correctly an observation, not a finding. Its severity is understated, though: it means
  the *only* reachable source of `starting_capital` through the shipped path is the run spec or a
  flag, which makes the Book-default branch of T13-111 a test of an unreachable code path. Worth
  carrying into Epic 14 as a wiring item, as RESULTS says.
- **PLAN-integrity caveat (missing `test-artifacts/`).** Confirmed independently above.
  Correctly recorded outside `findings.csv` — no test asserts those files exist — but it is a real
  audit-integrity item, since the 15 P0/P1 assertions and this epic's risk-gate rows were never
  read from their authority.

Three exit-criterion claims in RESULTS §"Exit-criteria ledger" do not hold as stated:

1. "*R-004 satisfied: … T13-306 … PASS*" — T13-306 no longer asserts the no-silent-accept limb of
   R-004 (§1.1). R-004 remains well covered by T13-401/401b/402/404/107; the T13-306 leg is void.
2. "*Every §2 AC maps to ≥1 executed test with a recorded PASS*" — true as a mapping, but §2
   above lists fourteen AC clauses whose substance the mapped test does not reach.
3. "*L0 gate green (ruff + pyright-strict; …)*" — accurate for ruff and pyright (`typeCheckingMode
   = "strict"` is confirmed set workspace-wide at `pyproject.toml:317`, with `qmb` in `include`),
   but the AC's pytest clause and the rest of `poe check` were not executed.

---

## 4. What would close the gaps

Ranked. Items 1–4 are the ones that change the verdict.

1. **Restore the planned T13-306**: mint a binding record, attempt a second record that
   fingerprints equal to it, assert a returned CT-04 `invalid input` refusal — never an accept.
   Re-scope T13-205 to count the bindings one compile mints.
2. **Give T13-112 its rated baseline**: assert the non-overridden compile's fold is *not*
   `unrated` and its binding is not stamped `seed_overridden`.
3. **Replace the marker-constant assertions** (T13-201/202/207) with structural or behavioural
   ones — the T13-007 AST technique over `qmb/doors/**`, plus driving the CLI door's own
   autocomplete through the port.
4. **Run the Tier-1 gate the AC names**: `poe check` over qmb (or at minimum `test`, `cov-report`,
   `ambient-scan`, `money-path-scan`, `fmt-check`), recording any failure as a finding.
5. **Re-premise T13-401c** so it does not require a `world=simulated` compile to succeed;
   assert *refusal or distinct identity*, and add a test asking whether `world=simulated` is
   reachable at all pre-GAP-0048.
6. Land a fresher as-of after `admit_batch` and assert the frozen set still answers (2.6);
   compare the CLI door's fingerprint to the library's (2.7); drive the collision through
   `compile_run_config` (2.9); write and re-read the artifact from a run-id-named directory (2.12);
   scan docstrings and internal symbols for the four banned words (2.5).
