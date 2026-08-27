# L6 requirements-fidelity review — Epic 16: qmb CLI & doors (FR-046)

**Reviewer question, asked once per test:** does this test assert what the requirement
demands, or what the implementation happens to do?

**Verdict: GAPS.**

The epic's centre of gravity — the derived door-parity contract (T-16.5-a/-gap/-map) —
is genuinely well built and produced **two real, independently-verified findings**. But
five requirement clauses are recorded green or absent on evidence that cannot be
falsified, two clauses were silently narrowed with no UNPROVEN row, and one clause was
recorded UNPROVEN that is in fact statically provable from a file the author already
parses. Under the hardened author contract (rules 1, 3, 5, 6) that is a gaps verdict,
not an adequate one.

**Independent verification performed for this review** (read-only, no tests run, no
source edited, no git):
`qmb/src/qmb/doors/parity.py`, `qmb/src/qmb/doors/cli/tree.py`,
`qmb/src/qmb/doors/api/__init__.py`, `qmb/src/qmb/doors/mcp/__init__.py`,
`qmb/src/qmb/runloop/loop.py`, `qmb/src/qmb/optimize/__init__.py`,
`qmb/tests/test_door_parity.py`, `qmb/pyproject.toml`, root `pyproject.toml`,
`_bmad-output/planning-artifacts/epics.md` §"Epic 16".

---

## 0. Authority note (affects how one finding is scored)

`_bmad-output/test-artifacts/` **does not exist in this worktree** — neither
`test-design-qa.md` nor `test-design/QMX-handoff.md`. PLAN.md §Process-Gap records this
accurately and does not work around it. **`R-006` is therefore not a worktree authority
id**: PLAN.md L84 states it is quoted *verbatim from the task brief* as a risk-gate row.
It is legitimate as a brief-supplied directive, but it is **not** in epics.md, and it
must not be confused with `FR-006`, which epics.md L263 assigns to **Epic 2**
(fingerprint-keyed registration records, CT-06). See F01 below for the consequence.

---

## 1. Wrong-expectation / unfalsifiable tests

Ranked by severity. "Counter-case" = the concrete violation that ought to turn the test
red; where none is constructible, the test is a hollow green.

### 1.1 `test_t16_3_d_research_call_path_writes_no_governed_evidence` [R13] — HOLLOW GREEN

Requirement (Story 16.3 AC4, B-4/B-9): *a direct library call through the door in
research returns values and produces no governed evidence.*

The test calls `api.run(slices=…, stream_set=…, handler=…)` and then asserts
`list(tmp_path.rglob("*.jsonl")) == []`. **`tmp_path` is a freshly created empty
directory that is never passed to `api.run` and never made the cwd** — it is empty
before the call, during it, and after it, whatever `run` does. The second half builds a
`LedgerSink` at `tmp_path/ledger` *after* the call and reads an empty merge view; that
sink was never handed to `run` either, so it is empty by construction.

**Counter-case check:** none is constructible. `qmb/src/qmb/runloop/loop.py:794 run()`
takes no output path at all (its own docstring: *"Writes no log and no ledger"*), so a
hypothetical evidence-writing `run` would write somewhere the test does not observe. The
assertion cannot go red for any behaviour of the code under test.

Verdict: **asserts neither the requirement nor the implementation — it asserts a
property of `tmp_path`.** Rule 3 ("state absence-of-effect by observing the sink") is
formally cited in the docstring and materially not met: the sink is not wired to the
call. Correct shapes were available — pass a test-owned recorder as `observer=`, or
`monkeypatch.chdir(tmp_path)` so any relative write lands in the observed tree. As
written this belongs in RESULTS.md as **UNPROVEN**, not as PASS.

### 1.2 `test_t16_3_p_refusal_union_survives_the_door_field_identically` [R11] — half tautology

```python
library = lambda: refusal          # a stand-in library function
door = library                     # "the API door re-exports the library object"
assert door() is refusal
```

The API door is **never imported or invoked** in this half. `door` is literally the same
object as `library`, and `library` closes over the `refusal` the test was handed — this
is the banned shape "calling a function against itself / passing the conclusion in as an
argument". It proves that Python aliasing is reflexive, not that `qmb.doors.api`
preserves a refusal union.

The second half (`render_refusal` preserves category / retryability / context keys /
descriptor over 250 generated refusals) **is** real and falsifiable — a renderer that
dropped `after_condition_descriptor` fails it. Keep that half; the re-export half should
have used a real re-exported library function that returns a refusal, exactly as
`test_t16_3_b` already does with `api.parameter_space_from_bot`.

### 1.3 `test_t16_5_p_semantic_parity_cli_door_equals_python_door` [R18] — unreachable arm

The generator is `st.dictionaries(text(1..6), text(..6), max_size=4)`. Verified against
source: `parameter_space_from_bot` (`qmb/src/qmb/optimize/__init__.py:371`) routes every
non-`BotDefinition` input through `BotDefinition.try_from_mapping`, which no arbitrary
`dict[str, str]` of short random text can satisfy. **The accept arm is unreachable**;
all 200 examples exercise the invalid-input refusal path only, on both sides.

That is the banned shape "hypothesis generators whose refusal (or accept) arm is
unreachable". The law claimed — *"each capability invoked through the CLI door and the
Python door maps to the SAME library result over arbitrary inputs"* — is demonstrated
over exactly one semantic outcome. The value path of semantic parity is untested.
(A composite strategy building a well-formed `BotDefinition` mapping, or `st.one_of`
over a valid-declaration builder and the junk generator, would have reached both arms.)

### 1.4 `test_t16_2_d_programmer_error_is_exception_distinct_from_refusal_channel` [R9] — wrong level

Requirement (Story 16.2 AC4, AR-13): *a programmer error rather than a typed refusal
surfaces as an exception, distinct from the refusal channel.*

The real risk this clause exists to catch is a door with a broad
`except Exception: return refusal(...)` that launders bugs into the CT-04 channel. The
test never touches the CLI door's error path. It asserts (a) `render_refusal(object())`
raises — the renderer's own type strictness, and (b) `api.identity_payload("nope")`
raises `TypeError` — **Python's own arity enforcement**, which would hold for any
callable in any codebase and is not a QMX behaviour at all.

**Counter-case not constructed:** make an injected library seam raise a real
`RuntimeError` inside a `qmb backtest run` invocation under `catch_exceptions=False`,
and assert the exception propagates rather than being rendered as stderr CT-04 JSON.
That is the assertion R9 demands, and the harness for it already exists in this file
(`CompilerSpy` + `CliRunner(..., catch_exceptions=False)` are used two tests above).

### 1.5 `test_t16_4_b_autocomplete_and_resolution_cannot_answer_differently` [R15] — half the claim

Requirement (Story 16.4 AC2, B-15): *resolution and autocomplete can never answer
differently — one port over one as-of set.*

Autocomplete is driven **through the door** (`cli_tree.complete_registry`), but
resolution is driven **directly against the port** (`u.port.resolve`), never through the
door's resolution path. What is proven is that the library port's own `complete` and
`resolve` agree — an Epic-13-owned property. The counter-case the requirement targets —
*the door completes through the B-15 port but resolves through some other path or
cache* — is not constructible as written, because the door's resolution path is never
exercised.

### 1.6 `test_t16_5_b_parity_fails_on_injected_divergence` [R19] — teeth demonstrated on a stand-in

The fault injection runs against a **test-local `parity_gaps` helper over test-owned
sets**, not against the audit's actual reconciler in `test_t16_5_a`. Asserting
`parity_gaps(base | {"phantom.capability"}, base)["cli_only"] == ("phantom.capability",)`
is set arithmetic; it does not show that `cli_capability_targets()` /
`api_library_surface()` would *derive* a changed surface when a door changes (those two
read the live `qmb.doors.cli.main` and `tree.py` from disk and are not injectable).

**Redeemed in practice, not in shape:** `test_t16_5_gap` genuinely fails on a genuinely
divergent door, which is the strongest possible proof of teeth. Note it, do not re-file it.

### 1.7 `test_t16_1_d_single_surface_capability_groups_enumerable` [R3] — over-specified

epics.md Story 16.1 AC2 says *"for example, `backtest`, `data`, `optimize`, `ledger`, and
`config` groups"*. The test additionally requires a **`sweep`** group and five exact leaf
names (`backtest.run`, `data.download`, `optimize.run`, `ledger.merge`, `config.compile`)
that **no requirement names**. That is asserting what the implementation happens to
expose. Low severity — it can only produce a false red on a rename, never a false green —
but it is the wrong-expectation shape and should be relaxed to the epics.md example set
plus "the tree enumerates to leaves".

### 1.8 `test_t16_5_enumapi_is_a_pure_function_of_the_public_surface` [R18 mech] — tests a copy

The test defines a local `_derive` that re-implements `_e16.api_library_surface` and
exercises the copy, not the enumerator the flagship actually uses. Low severity: the very
next test (`…reflects_the_real_api_door_surface`) exercises the real one.

### 1.9 `test_t16_4_d` bespoke-completion scan [R17] — weak heuristic (noted, not filed)

`assert "Completion" not in node.name` over CLI-door class defs would not catch a bespoke
completer named e.g. `_RegistryCandidates`. The click-native half of the test (driving
`Parameter.shell_complete` over a ctx carrying the port) is genuine and carries the
requirement.

---

## 2. Tests that assert the requirement correctly (no action)

Recorded so the gaps above are read in proportion.

| Test | Req | Why it holds up |
|---|---|---|
| `test_t16_5_a_derived_parity_…` | R18 | **Flagship, genuinely derived.** CLI side = click-tree walk + AST of the `invoke_*` adapters + import-alias resolution; API side = introspection with `is`-identity against `qmb`. `CAPABILITY_LIBRARY` is touched by neither. Falsifiable, and its unfiltered twin actually fails. |
| `test_t16_5_gap_…` | R18,R19 | Fails on a real divergence — the counter-case is not hypothetical, it is the finding. |
| `test_t16_1_f_backtest_compiles_and_submits…` | R5 | Test-owned `CompilerSpy`/`OrchestratorSpy`; asserts the orchestrator received `is`-identical the compiled config and that `run_id == compiler fp1` — the door mints none. Would fail on a door-side identity. |
| `test_t16_1_e_tunnel_command_missing_prereq…` | R4 | Absence-of-effect stated by observing the spies (`compiler.calls == []`), not by trusting the returned flag. Exactly rule 3. |
| `test_t16_2_a` / `-b` / `-c` | R6,R7,R8 | A *specific* test-authored refusal is injected and traced to exit code + stderr JSON; `catch_exceptions=False` separates returned-from-raised; the success path pins stdout to the compiler's fingerprint. |
| `test_t16_1_b_each_capability_forwards_to_one_library_function` | R1 | Test-owned recorder replaces the seam; asserts exactly one library call and `result.value is sentinel` (verbatim forwarding). Sound — but see §3.5 for what it omits. |
| `test_t16_4_a` | R14 | Compares the door's output to the real test-built port's own answer, and shows a non-port yields `()` — no fallback store. |
| `test_t16_0_pins_click_pinned_at_registry_key_value` | R2 | Cross-checks two independent artifacts (`docs/registry/variables.yaml` vs `qmb/pyproject.toml`) rather than restating a literal. |
| `test_t16_6_a_mcp_scaffolded_not_shipped…` | R22 | **Correctly refuses the trap.** `doors/mcp` self-declares `SHIPPED`, `STACKED_OVER_HTTP`, `LOCALHOST_BOUND`, `HOLDS_CACHE`, `COMPUTES_RUN_ID`; the test asserts none of them, using the real `pyproject` manifest and the actual refusal `mcp.main()` returns. |
| `test_t16_0_thin_scanner_has_teeth` | (falsifiability) | The scanner is proven to flag injected violations, in a test-owned source string. Correct discipline. |

---

## 3. Missed requirements — Epic 16 clauses with no test that can fail

Every id below is confirmed to sit inside **this epic's** `epics.md` section
(L3210–L3355). Nothing from a neighbouring epic is filed here.

### 3.1 Story 16.3 AC1 — the **"pure"** half of "thin *pure* re-export" (R10) — UNRECORDED

`test_t16_3_a` proves *completeness in one direction*: every CLI-adapted public
capability is `is`-identical on the API door. **Nothing asserts the converse — that the
API door's public surface contains only library re-exports.** Verified by AST over both
`__all__` lists: `qmb.doors.api.__all__` carries **1097** names, of which **9 are not in
`qmb.__all__`**:

`CHANNEL`, `COMPUTES_RUN_ID`, `CONSUMER`, `HOLDS_CACHE`, `IN_PROCESS`,
`STACKED_OVER_HTTP`, `TRANSPORT`, `WRITES_GOVERNED_EVIDENCE`, `api_door_identity`.

Eight are self-declared marker constants — the exact artefact class the banned-shapes
rule exists to keep out of assertions — published on a door the requirement calls a
*pure* re-export. Whether they constitute a defect is a judgement call
(`api_door_identity` is plausibly adaptation); **that the clause was narrowed without an
UNPROVEN row is not** — it is a rule-5 silent narrowing. Note the sharp edge:
`WRITES_GOVERNED_EVIDENCE` is a door-declared flag standing exactly where §1.1's
unfalsifiable R13 test failed to observe the real thing.

### 3.2 Story 16.6 AC2 — "localhost-bound by default" (R23 runtime half) — UNRECORDED

`test_t16_6_b` proves only the structural half (no HTTP/transport import; imports `qmb`
as a sibling). The binding clause is untested. PLAN §7 defers it and the RESULTS.md row
says "(Runtime localhost-binding deferred (§7))" in passing — but **R23 is listed under
PASS in the coverage summary, appears in no UNPROVEN entry, and has no `findings.csv`
row**, unlike R12/R20/R24 which all got one. Rules 5 and 6 require the row. (The author
was right not to assert `LOCALHOST_BOUND = True` / `BIND_HOST = "127.0.0.1"` — that is
precisely why it should have become an UNPROVEN row instead of a green.)

### 3.3 Story 16.3 AC4 — "produces no governed evidence" (R13) — effectively uncovered

Per §1.1 the only test is unfalsifiable. R13 has no covering assertion.

### 3.4 Story 16.2 AC4 — the door-swallowing counter-case for R9 — uncovered

Per §1.4. R9's stated risk (programmer error laundered into the CT-04 channel) has no
covering assertion.

### 3.5 Story 16.1 AC1/AC2 — "no domain logic accretes in the door", `data` group — uncovered

`test_t16_1_b` covers **4 of the 15** capabilities in the shipped catalog
(`sweep.count`, `ledger.merge`, `optimize.space`, `config.show`) and omits **every
`data.*` command** — which is the one place door-side control flow actually lives:
`qmb/src/qmb/doors/cli/tree.py` `invoke_data` (~L450–520) does six-way token dispatch,
a `has_generator_config(...)` branch, and per-branch payload assembly
(`dict(receipt.value.as_mapping()); payload.update(data_front_identity())`).

The supporting static gate does not reach it either: `_scan_thin` looks only for HTTP /
store / money-type imports, `fingerprint()` calls, cache decorators and mutable module
globals. Its teeth test proves *the scanner works*, not that the blocklist covers "domain
logic". So R1's headline clause is proxied by a narrow blocklist plus a 4/15 sample, with
the sample deliberately missing the highest-risk group. Not a wrong expectation — a
coverage hole exactly where the requirement's risk lives, and an undisclosed narrowing.

### 3.6 Story 16.6 AC1 — "explicitly marked post-CLI-v1" (R22 second half) — narrowed, unrecorded

Testable only via the door's own `POST_CLI_V1` flag, which the author correctly declined
to assert. Correct call; still a narrowed clause that owed an UNPROVEN line. Minor.

---

## 4. Per-`findings.csv` row verdict

| Row | Req ids | Verdict | Basis |
|---|---|---|---|
| **E16-F01** — parity anchored on hand-maintained `CAPABILITY_LIBRARY` | R18, R-006 | **Genuine violation** (with two caveats) | Verified independently: `qmb/src/qmb/doors/parity.py` defines a 15-entry `MappingProxyType` capability→library literal; `flatten_capabilities()` returns `tuple(CAPABILITY_LIBRARY)`; `qmb/tests/test_door_parity.py` imports `CAPABILITY_LIBRARY`, `capability_gaps`, `flatten_capabilities` and reconciles the click tree and `api.__all__` **through the catalog**. The consequence is real and demonstrated, not stylistic: the catalog maps `data.generate → ("DATA_COMMANDS", "data_front_identity")`, both of which *are* in `qmb.__all__`, so `capability_gaps` reports clean while F02's genuine asymmetry stands. **Caveat 1:** the forbidding clause is the brief's risk gate `R-006`, not epics.md — Story 16.5 AC1 requires "identical function surface and semantics", it does not itself forbid a hand-maintained map. Genuine against the audit brief; do not re-cite it as an epics.md/FR obligation, and **do not let `R-006` be read as `FR-006`, which epics.md L263 assigns to Epic 2**. **Caveat 2:** the test's detector is an AST shape heuristic (module-level dict, ≥3 str keys, ≥3 collection values) — it would miss a 2-entry hand map and could trip on an unrelated mapping. The finding survives because the description rests on read source, not on the heuristic. |
| **E16-F02** — `generate` / `has_generator_config` on the CLI door, absent from the Python door | R18, R19 | **Genuine violation** | Verified independently: `doors/cli/tree.py` L31/L36 imports `has_generator_config` and `from qmb.data import generate as run_generate`, and `invoke_data` calls both at L511–512; AST over `qmb/src/qmb/__init__.py` `__all__` (1088 names) confirms **neither** is present, and the API door re-exports only `qmb.__all__`. Squarely violates Story 16.5 AC1 ("identical function surface across doors") and AC2 ("a capability present in one door and not the other **fails** the parity test"). Severity `medium` is defensible but arguably light — the shipped tier-2 gate is green over a live surface asymmetry. |
| **E16-F03** — MCP `error.data` verbatim unreachable in V1 | R24 | **UNPROVEN, correctly recorded** | Story 16.6 AC3 is explicitly conditional/future-tense ("**Given** the MCP door renders a refusal **later**"), and AC1 makes the door scaffolded-not-shipped. Not a code defect; the reason given is the right one. |
| **E16-F04** — tier-2 scheduling clause not executable | R20 | **UNPROVEN, but incorrectly scoped — over-broad** | The population half is correctly bounded. The *scheduling* half, however, is **statically provable from a file the author already parses with `tomllib` twice**: root `pyproject.toml` L475 `[tool.poe.tasks.check-integration] sequence = ["check", "build-all", "isolated-build"]`, and L465 `[tool.poe.tasks.check] sequence = [… "test" …]` — so `check-integration` transitively collects `qmb/tests/test_door_parity.py`. That is exactly the kind of declared-schedule fact T-16.0-pins and T-16.6-a already assert elsewhere. Rule 1 permits UNPROVEN only when *no failing counter-case is constructible*; here one is (rename the task, or move the parity test outside the collected path). A sharper reading is also available and untaken: because tier 2 includes tier 1, the parity test is really gated at Tier **1**, which the clause "runs at Tier 2" does not obviously contemplate. Re-file as a testable row, not a scope waiver. |
| **E16-F05** — no UI-backend consumer exists in V1 | R12 | **UNPROVEN, correctly recorded** | Confirmed at `epics.md` L252: *"None. V1 has no UI surface"*. The consumer relationship has no consumer; the door-side half is separately asserted. Correct. |

**Rule-6 check on `findings.csv` completeness:** the file is not empty, so the "empty only
if everything is green" clause does not bite — but it is **incomplete**. Missing rows,
per rules 5/6: R23 localhost-bound (§3.2), R10 purity half (§3.1), R13 (§3.3, currently a
PASS that should be UNPROVEN), R9's uncovered counter-case (§3.4), R1's `data`-group
narrowing (§3.5).

---

## 5. The single most important gap

**R13 — "a direct library call through the door in research returns values and produces
no governed evidence" (Story 16.3 AC4, B-4/B-9) is recorded PASS on a test that no
behaviour of the code under test can turn red.**

The observer (`tmp_path`) is never connected to the call: `api.run` receives no path,
`qmb/src/qmb/runloop/loop.py:794` accepts no output location, and the `LedgerSink` the
test builds is created *after* the call and never passed to it. Every assertion in that
test is a statement about an empty directory the production code has never heard of.

It matters more than the two filed findings because of what it is, not what it costs: a
**governance invariant** — research must not mint governed evidence — banked as green on
a structurally unfalsifiable observation. That is precisely the failure mode the hardened
author contract was written after tier-1 review to eliminate, reappearing in an epic whose
flagship test is otherwise a model of derived-both-sides rigour. It should be re-tested
with a wired observer (`observer=` recorder, or `monkeypatch.chdir(tmp_path)`) or demoted
to **UNPROVEN**; it must not stand as PASS.

Runner-up: §3.1 — the API door publishes 9 non-library public names, eight of them
self-declared markers, on a surface the requirement calls a *pure* re-export, and no test
looks in that direction.

---

## 6. Required corrections before this epic's artifacts are accepted

1. Demote R13 to **UNPROVEN** in RESULTS.md with a `findings.csv` row, or re-test it with
   a sink the call actually reaches. (§1.1, §3.3)
2. Add `findings.csv` UNPROVEN rows for the R23 localhost clause and the R10 purity
   clause; add the R1 `data`-group narrowing as a disclosed scope note. (§3.1, §3.2, §3.5)
3. Rewrite the re-export half of `test_t16_3_p` against the real API door
   (`api.parameter_space_from_bot` returns a refusal — use it). (§1.2)
4. Reach the accept arm in `test_t16_5_p`, or restate the property honestly as
   "refusal-path parity". (§1.3)
5. Re-test R9 through the CLI door with an injected raising seam under
   `catch_exceptions=False`. (§1.4)
6. Drive resolution **through the door** in `test_t16_4_b`, or narrow the claim. (§1.5)
7. Re-file E16-F04's scheduling half as a testable row against
   `[tool.poe.tasks.check-integration]`. (§4)
8. Keep F01/F02 as filed — but pin F01's authority to the brief's risk gate `R-006` and
   add a one-line guard that `R-006` is **not** `FR-006` (Epic 2). (§0, §4)

---

*Reviewed read-only. No test was run or edited; no source file was read for any purpose
other than evidence, and none was modified. No git command was issued. This file is the
only artifact written, inside `qa/`.*
