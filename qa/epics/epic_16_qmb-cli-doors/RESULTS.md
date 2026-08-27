# RESULTS — Epic 16: qmb CLI & doors (FR-046)

**Runner:** `uv run --with hypothesis pytest qa/tests/epic_16 -q` (worktree root).
**Outcome:** 36 tests — **34 PASSED, 2 FAILED**. The 2 failures are **intended findings**
(each asserts what a requirement demands; the failure IS the finding, per the
falsifiability contract). Plain `uv run pytest qa/tests/epic_16` skips the 2 L6
property tests (hypothesis absent) and is otherwise identical.

Source was read-only evidence throughout. No test edits source; no assertion was
softened to pass. Both parity sides are COMPUTED from the live door structure —
zero use of the shipped `CAPABILITY_LIBRARY` catalog in any assertion.

Legend: PASS = requirement upheld · **FINDING** = requirement violated (test fails) ·
UNPROVEN = not constructible in Epic-16 isolation (scope-bounded, recorded not waived).

---

## Per-test results

### L0 — static / structural thin-door gates
| Test | Req | Status | Meaning |
|---|---|---|---|
| `test_t16_0_thin_no_logic_no_cache_no_identity_no_http` | R1,R5,R12,R14,R23 | PASS | `doors/{cli,api,mcp}` compute no fp1/run-id, hold no module-global cache / lru_cache, import no HTTP/store stack, import no money-path value types. |
| `test_t16_0_thin_scanner_has_teeth` | (falsifiability) | PASS | The thin scanner FLAGS an injected `fingerprint()`, HTTP import, money-type import, cache decorator, mutable global — proving the green gate is not vacuous. |
| `test_t16_0_onecli_single_console_script_surface` | R3 | PASS | Exactly one console script `qmb = qmb.doors.cli:main`; no second/sibling CLI (DEC-0185); `main` is the one `qmb` click Group. |
| `test_t16_0_pins_click_pinned_at_registry_key_value` | R2 | PASS | The qmb `click` dependency equals the `qmb_cli_pin` registry value (`click==8.4.2`, `configurable: false`) — referenced from the key, not a restated literal. |
| `test_t16_0_tree_three_door_subpackages_present` | R22 | PASS | `doors/` holds the three door subpackages `cli`, `api`, `mcp`, each a package. |
| `test_t16_6_b_mcp_door_imports_no_http_stack` | R23 | PASS | The MCP door imports no HTTP-server/transport stack and imports the library (`qmb`) as a sibling. Runtime localhost-binding deferred (§7). |

### L1 — targeted pure units
| Test | Req | Status | Meaning |
|---|---|---|---|
| `test_t16_2_render_maps_refusal_to_machine_readable_json_shape` | R6 | PASS | `render_refusal` maps every CT-04 refusal in the corpus to JSON `{category∈7, context present-non-null, retryability∈3}`; the after-condition descriptor is present iff retryability is after-condition. |
| `test_t16_2_render_emits_canonical_category_strings_not_enum_names` | R6 | PASS | The rendered category is CT-04's canonical spaced string (`invalid input`), not the enum member name; nested context round-trips. |
| `test_t16_5_enumcli_is_a_pure_function_of_the_click_tree` | R18 (mech) | PASS | The CLI-leaf enumeration is a pure function of a click Group; a leaf added to the tree changes the derived surface (no hand-list can hide). |
| `test_t16_5_enumapi_is_a_pure_function_of_the_public_surface` | R18 (mech) | PASS | The API-surface enumeration reflects exactly a module's re-exported objects; a door-local reimplementation drops out of the derived set. |
| `test_t16_5_enumapi_reflects_the_real_api_door_surface` | R18 (mech) | PASS | The real API door surface is non-empty and every derived name is identity-equal to `qmb.<name>`. |

### L2 — component / integration (in-process)
| Test | Req | Status | Meaning |
|---|---|---|---|
| `test_t16_1_b_each_capability_forwards_to_one_library_function` | R1 | PASS | sweep.count / ledger.merge / optimize.space / config.show each call exactly ONE library function (test-owned recorder) and return its result verbatim. |
| `test_t16_1_d_single_surface_capability_groups_enumerable` | R3 | PASS | The command tree exposes the single surface: `backtest/data/optimize/sweep/ledger/config` groups present, enumerable to leaves, one `qmb` entry. |
| `test_t16_1_e_tunnel_command_missing_prereq_returns_typed_refusal` | R4 | PASS | `backtest` with prerequisites absent RETURNS a CT-04 `unavailable dependency` naming the missing prereqs and never reaches the compiler/orchestrator spies. |
| `test_t16_2_a_library_refusal_renders_nonzero_exit_and_stderr_json` | R6 | PASS | A specific injected library refusal renders as nonzero exit + stderr JSON matching its `{category,context,retryability}`. |
| `test_t16_2_b_refusal_is_returned_and_rendered_never_raised_never_swallowed` | R7 | PASS | Under `catch_exceptions=False` a typed refusal crosses the door as a return (exit≠0, no exception), never swallowed to zero; the invoker returns it. |
| `test_t16_2_c_successful_run_exits_zero_no_stderr_refusal` | R8 | PASS | A successful backtest exits zero, empty stderr, stdout = the compiler's fingerprint. |
| `test_t16_2_d_programmer_error_is_exception_distinct_from_refusal_channel` | R9 | PASS | A programmer error (bad type / wrong arity) raises `AttributeError`/`TypeError` — never rendered as a CT-04 refusal. |
| `test_t16_3_a_api_names_resolve_to_library_pure_functions` | R10 | PASS | Every public-surface capability the CLI adapts is identity-equal on the API door (`api.f is qmb.f`), importable from `qmb`. |
| `test_t16_3_d_research_call_path_writes_no_governed_evidence` | R13 | PASS | `api.run(...)` on the research path returns a value and writes no ledger `.jsonl`; a fresh merge view is empty. (Governed-evidence machinery = Epic 15; §7.) |
| `test_t16_4_a_autocomplete_routes_through_the_one_port_no_door_cache` | R14 | PASS | The door returns exactly the port's candidates; a non-port yields `()` — no door-side cache / live query. |
| `test_t16_4_b_autocomplete_and_resolution_cannot_answer_differently` | R15 | PASS | Every candidate autocomplete offers, `resolve` accepts through the SAME port to the SAME fp1 — one port, one as-of. |
| `test_t16_4_c_new_book_arrives_as_fresher_as_of_not_door_cache` | R16 | PASS | A new Book appears via a FRESHER as-of set (new port binding); the stale port stays empty — no door memo pins the first answer. (As-of delivery = Epic 13; §7.) |
| `test_t16_4_d_autocomplete_uses_click_native_completion_over_the_port` | R17 | PASS | click's native `Parameter.shell_complete` over a ctx carrying the port returns the port's aliases, each citing `fp1:sha256:`; no bespoke completion class in the CLI door. |
| `test_t16_6_a_mcp_scaffolded_not_shipped_invocation_refused` | R22 | PASS | `mcp.main()`/`mcp.serve()` return `unsupported capability`; `mcp` is not a console script and not in `qmb.__all__`. |
| `test_t16_6_c_cli_v1_usable_without_mcp_and_does_not_depend_on_it` | R25 | PASS | `qmb config show` works with mcp unshipped; no CLI-door module imports `qmb.doors.mcp`. |

### L3 — contract conformance
| Test | Req | Status | Meaning |
|---|---|---|---|
| `test_t16_1_f_backtest_compiles_and_submits_minting_no_run_id` | R5 | PASS | Backtest calls the compiler spy then submits the compiled config to the orchestrator spy; `run_id` == the compiler's resolved-config fp1 (the door mints none of its own). |
| `test_t16_3_b_python_door_returns_refusal_union_verbatim` | R11 | PASS | `api.parameter_space_from_bot is qmb.parameter_space_from_bot`; a refusal is returned (not raised) and the CLI invoker returns the identical value; CLI render fields match. |
| `test_t16_5_a_derived_parity_public_capabilities_identical_across_doors` | R18 | PASS | **FLAGSHIP.** Every public-surface CLI capability (derived: click walk + AST of the `invoke_*` adapters) is identity-equal on the API door's introspected surface — both sides computed, reconciled through the library, no `CAPABILITY_LIBRARY`. |
| `test_t16_5_b_parity_fails_on_injected_divergence` | R19 | PASS | The parity reconciler FLAGS a capability dropped from one derived surface, and a phantom capability added to one — the parity check has teeth (can fail on real drift). |
| `test_t16_5_c_parity_ranges_over_real_capabilities_landed_by_epic14` | R20 | PASS (bounded) | The derived surface is real and non-empty and includes the Epic-14/15 run-loop capabilities (`run`, `spawn_run`, `compile_run_config`). The *scheduling-at-tier-2* clause is UNPROVEN here (see F04). |
| `test_t16_5_d_per_transport_refusal_parity_same_library_refusal` | R21 | PASS | For ONE library refusal, CLI renders nonzero exit + stderr JSON and the Python door returns the union verbatim — identical CT-04 semantics both transports. |
| `test_t16_5_map_parity_is_derived_not_a_hand_maintained_map` | R18 (method) | **FINDING (F01)** | The shipped parity is anchored on a hand-maintained `CAPABILITY_LIBRARY` map — R-006 requires both surfaces be DERIVED, never a hand-list. |
| `test_t16_5_gap_every_cli_capability_is_reachable_on_the_python_door` | R18,R19 | **FINDING (F02)** | `data generate` (`qmb.data.generate` / `has_generator_config`) is reachable via the CLI door but ABSENT from the pure-re-export Python door — a real door-surface asymmetry. |

### L6 — property-based breadth (hypothesis)
| Test | Req | Status | Meaning |
|---|---|---|---|
| `test_t16_3_p_refusal_union_survives_the_door_field_identically` | R11 | PASS | Over 250 arbitrary CT-04 refusals, the pure re-export preserves the value field-identically and the CLI renderer preserves category/retryability/context-keys/descriptor. |
| `test_t16_5_p_semantic_parity_cli_door_equals_python_door` | R18 | PASS | Over 200 arbitrary declarations, `invoke_optimize_space` / `invoke_sweep_count` (CLI door) equal `parameter_space_from_bot` / `preflight_run_count` (Python door) — semantic parity as a law. |

---

## Requirement coverage summary (R1–R25)

PASS: R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R13, R14, R15, R16, R17,
R21, R22, R23, R25 — and R18/R20 in their derived/population halves.

**FINDINGS (code/design):**
- **R18 (method clause) — F01.** Shipped parity anchored on the hand-maintained
  `CAPABILITY_LIBRARY` catalog, contravening R-006 ("never a hand-maintained
  map"). The doors are functionally in parity today (T-16.5-a green), but the
  shipped *mechanism* is not derived-both-sides and — per F02 — masks a real gap.
- **R18/R19 (surface) — F02.** `data generate` is a CLI-door capability with no
  equivalent on the Python API door; the shipped catalog maps `data.generate` to
  `DATA_COMMANDS`/`data_front_identity` rather than the real generator, hiding the
  asymmetry.

**UNPROVEN (scope-bounded — NOT code defects; recorded per rules 5/6):**
- **R24 — F03 (DEFERRED).** MCP `error.data`-verbatim rendering is unreachable in
  V1: the door refuses to serve (SC-08). The scaffold's `error_data`/`render_error`
  functions exist and shape the union, but the door's *operational* rendering
  cannot be exercised until the door ships post-CLI-v1.
- **R20 (scheduling clause) — F04.** "The parity test runs at Tier 2
  (`poe check-integration`)" is a CI-scheduling fact not executable inside this
  audit harness; the population half (real landed capabilities) is proven
  (T-16.5-c).
- **R12 (consumer clause) — F05.** The door-side property (Python API in-process,
  imports no HTTP — T-16.0-thin over `doors/api`) is proven; the "UI backend
  consumes it in-process" *consumer relationship* has no consumer in V1
  (epics.md: "None. V1 has no UI surface").

**Cross-epic seams asserted only as door adaptation (not tested here — §7):** the
B-3 compiler fp1 (Epic 13), orchestrator process-per-run/ledger (Epic 15), B-15
as-of delivery (Epic 13), the library pure-function correctness (Epics 13/14/17–23).

## Exit-criteria check (PLAN §8)
1. All P0 tests green **and** the parity fault-injection T-16.5-b fails on injected
   drift — **met** (the parity test is proven able to fail).
2. R-006: T-16.5-a computes both surfaces with no hand-maintained map — **met** for
   the independent test; **F01** records that the *shipped* parity does not.
3. B-3: T-16.0-thin (no logic/cache/run-id) + T-16.1-f (compile-and-submit, no
   run-id) + T-16.0-onecli — **met**.
4. AR-58: every "is refused" test asserts a *returned* CT-04 refusal rendered per
   transport, programmer-error channel distinct — **met**.
5. Coverage floors — not measured in this harness (coverage not run); each covered
   branch is tied to an assertion by construction.
6. Every deferred/bounded requirement has a recorded owner (F03/F04/F05; §7) —
   **met**.
