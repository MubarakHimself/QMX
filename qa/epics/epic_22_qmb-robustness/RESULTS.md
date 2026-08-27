# Epic 22 — QMB robustness ladder — independent test RESULTS (audit tier T3)

Executed band: **L3 acceptance/contract + the two regression pins + the L0 register
gate**, per the PLAN. Runner: `uv run pytest qa/tests/epic_22 -q --tb=short` from the
worktree root. Every assertion states what a *requirement* of Epic 22 demands; a failing
test is a FINDING and source was never edited to make a test pass, nor any assertion
weakened. Where a requirement is structurally unprovable at this tier or narrowed, it is
recorded UNPROVEN below (never counted as green).

## Run summary

- **Tests written:** 54 · **passed:** 51 · **failed:** 3 · **errored:** 0
- **Findings:** F-22-01 (P0, confirmed, 2 failing pins), F-22-02 (P1, confirmed, 1 failing gate)
- **UNPROVEN requirements:** T22-328 admission single-frozen-as-of (E22-F03); T22-302 forward-compat reader sub-clause (E22-F04)
- The 3 failures are the two **expected** advisory-finding pins (F-22-01 at both carve-out
  boundaries, F-22-02 register gap). All 51 owned-requirement acceptance tests are green
  under the hardened author rules (independent recompute / injected discriminator per test).

Files: `qa/tests/epic_22/conftest.py` (shape-faithful builders + CT-04 refusal harness),
`test_e22_a_foundation.py`, `test_e22_b_shuffle.py`, `test_e22_c_perturbation.py`,
`test_e22_d_significance.py`, `test_e22_e_walkforward.py`, `test_e22_f_static_pins.py`.

## Per-test results

### Story 22.1 — foundation, float carve-out, distribution-summary primitive

| Test id | Requirement | Status | One-line meaning |
|---|---|---|---|
| T22-301 | 22.1-AC1/AC3, B-4, NFR-02 | PASS | A ladder procedure RETURNS its result; repeated + interleaved runs are bit-identical (no module-global mutable state); no bare list/dict/set at module scope. |
| T22-302 | 22.1-AC1, AD-5, CT-05 | PASS (sub-clause UNPROVEN) | Contract stamps an integer format version (v1) into identity; an out-of-roster procedure is a returned invalid-input refusal. Forward-read-of-unknown-version refusal not exercisable at v1 → UNPROVEN (E22-F04). |
| T22-303 | 22.1-AC2, **R-001**, AD-7/AD-22 | PASS (P0) | Raw Money is refused at the carve-out; the carved statistic is stored as an exact scaled rational (den divides 10**scale — a raw binary float would not); money re-entry requires a declared rounding mode and yields exact Money. |
| T22-304 | 22.1-AC2, **R-001**, FR-001/NFR-02 | PASS (P0) | The tier-1 money-path float scanner flags an injected `Money(3.5,…)` (it can fail) and finds every robustness/*.py source file clean. |
| T22-305 | 22.1-AC3, AD-41, NFR-03 | PASS | Two floats that round alike share one label-derived identity (no float bits in identity); two different values do not — identity is label-derived, not float bit-identity. |
| T22-306 | 22.1-AC4, FR-040 | PASS | One-tailed p-value equals the independently-recomputed at-or-beyond fraction (11/100), flips correctly with declared direction (90/100); bands are caller-declared empirical quantiles; every measure exact. |
| T22-307 | 22.1-AC4, **SC-07/L20** | PASS (P0) | Summary identity keys are disjoint from any pass/fail/alpha vocabulary; no bands invented when none supplied; reading a pass/fail verdict is a returned policy rejection. |
| T22-308 | 22.1-AC5, **AR-13/NFR-07** | PASS (P0) | Unset required input → returned invalid-input refusal; float/bool/zero counts refused; procedures refuse (never default) when their count is unset. |
| T22-309 | 22.1-AC6, **L20/SC-06** | PASS (P0) | A real perturbation output labels claim_class robustness (never edge), world replay; edge-claim and live-money-gate reads are returned policy rejections. |
| T22-PIN-01 | P0-assertion-3, **F-22-01**, CT-04/DEC-0109 | **FAIL → F-22-01** | The public carve-out boundaries raise `OverflowError` on an un-floatable int instead of returning a CT-04 refusal (both `carve_return_statistic` and `reenter_money_path`). Expected fail; recorded. |

### Story 22.2 — Monte Carlo trade-shuffle

| Test id | Requirement | Status | One-line meaning |
|---|---|---|---|
| T22-310 | 22.2-AC1, **R-001**, AD-7/CT-29 | PASS | The shuffle is an order-only permutation: order-invariant net_profit has one distinct value across scenarios, path-dependent max_drawdown varies, every scenario magnitude is an exact quantity (no float on the equity path). |
| T22-311 | 22.2-AC1, **B-7** | PASS (P0) | The shuffle mints no synthetic series: world stays replay, and the result label carries the procedure identity, base seed, and procedure-ephemeral provenance. |
| T22-312 | 22.2-AC2, **AR-59/B-10** | PASS (P0) | scenario_seed = base+index (≠ a constant); a re-run reproduces the fingerprint bit-for-bit; provenance records RNG family, base seed, the seed rule, count, and the exact data-window ns bounds. |
| T22-313 | 22.2-AC3, FR-043 | PASS | Each metric distribution is chart-series data (a `values` array, no image/png/svg/base64 key); no verdict, no image payload. |
| T22-314 | 22.2-AC4, SC-07 | PASS | Scenario count required from config/argument — a run with neither refuses (MC-1000 not baked); supplied via the config key it resolves. |

### Story 22.3 — Monte Carlo candle-perturbation

| Test id | Requirement | Status | One-line meaning |
|---|---|---|---|
| T22-315 | 22.3-AC1, **R-001**, AD-7 | PASS (P0) | Exact-integer OHLC deltas cumulative-sum back to the exact input; scenario 0 is the true history verbatim; every scenario is strictly positive and high/low-bounded; block length required (unset refuses). |
| T22-316 | 22.3-AC2, **B-7** | PASS (P0) | The minted synthetic series is never persisted: world stays replay, claim robustness, label carries procedure + seed + procedure-ephemeral provenance. |
| T22-317 | 22.3-AC3, **SC-06** | PASS (P0) | Persistence seam: ephemeral (replay clock) OK; persist+simulated → policy rejection with world=simulated context; persist+replay → invalid input. Both named refusal builders return (never raise) the right categories. |
| T22-318 | 22.3-AC4, AR-59 | PASS | A re-run reproduces the fingerprint; provenance records the moving-block-bootstrap scheme, block length, count, seed rule, and exact data-window bounds. |
| T22-319 | 22.3-AC6, L20 | PASS | The objective distribution is data (no verdict, no image payload); a bar-verdict read is a returned policy rejection; the standalone objective summariser returns direction-aware exact data. |

### Story 22.4 — pre-build rule-significance gate

| Test id | Requirement | Status | One-line meaning |
|---|---|---|---|
| T22-320 | 22.4-AC1, **B-2** | PASS (P0) | The signal-only pass drives the real B-2 loop and stays flat (returns Ok only when no fill and every slice warming-up); minting an entry/exit/command is a returned policy rejection. |
| T22-321 | 22.4-AC2, **look-ahead/R-001** | PASS (P0) | Return t = ln(close[t+1]/close[t]) (n−1 returns, next-bar aligned; first return independently recomputed via the named AD-22 carve; stored as exact scaled rationals); a float close is refused; a last-only fired bar has no next return → refusal (anti-look-ahead). |
| T22-322 | 22.4-AC3 | PASS | The reported statistic equals the independently-recomputed fraction of null resample means ≥ observed mean; the null is re-centred to zero (its means centre near 0, not the non-zero observed mean). Internal detrend-by-mean arithmetic is L1-deferred-by-tier; its observable outcomes are proven. |
| T22-323 | 22.4-AC5, **AR-13/AR-59** | PASS (P0) | Below the configured floor → returned invalid-input refusal (no fabricated p-value); unset floor → low-confidence label; the null reproduces bit-for-bit; provenance records seed/scheme/iterations/window bounds. |
| T22-324 | 22.4-AC4, SC-07 | PASS | Scheme/iterations/block-length required (each unset refuses); iid/block/stationary each accepted with its params; an off-vocabulary scheme is refused. |
| T22-325 | 22.4-AC6, **L20/SC-06** | PASS (P0) | Result world is replay (never live), claim robustness; auto-merge and a live result world are returned policy rejections. |

### Story 22.5 — walk-forward as a sequence of split-manifest runs

| Test id | Requirement | Status | One-line meaning |
|---|---|---|---|
| T22-326 | 22.5-AC1, AD-21/FR-012 | PASS | A window materializes two first-class runs; train/test are display aliases (never in fp1_identity); identity carries both split fingerprints; identical splits and a simulated-world split are refused. |
| T22-327 | 22.5-AC2, **SC-06/B-4** | PASS (P0) | The in-sample run ledgers role=trial; no window run is a bar-verdict role; the OOS bar outcome is a read-time fold returning `not-yet-ruled`; reading a bar verdict is a returned policy rejection. |
| T22-328 | 22.5-AC3, SC-11/B-15 | PARTIAL PASS + UNPROVEN | Splits resolve by fingerprint and the alias is never substituted (round-trip proven); an unknown alias is refused. The SC-11 single-frozen-registry-as-of admission mechanism is UNPROVEN (E22-F03 — Epic-13 B-15 port fixture). |
| T22-329 | 22.5-AC4, SC-07 | PASS | Window count / spans / step required (unset plan refuses); a window-count mismatch is refused (not truncated); applying a WF/PBO/CSCV battery threshold is a returned policy rejection. |
| T22-330 | 22.5-AC5, B-12 | PASS | The aggregation is a read-time view (is_merged_run False, no verdict); its CT-32 payload is series-data feeding the deferred PBO/CSCV battery with no ratified thresholds; a merged run and a missing/mixed-unit fold are refused. |
| T22-331 | 22.5-AC6, AR-59/B-10 | PASS (sub-clause UNPROVEN) | Window and aggregation fingerprints reproduce bit-for-bit; window identity carries both split fingerprints, world, and evidence class. The frozen registry_as_of stamp is admission-owned → UNPROVEN (E22-F03). |

### Regression pins / static gate

| Test id | Requirement | Status | One-line meaning |
|---|---|---|---|
| T22-PIN-02 | NFR-11/L27, **F-22-02** | **FAIL → F-22-02** | qmb/FAILURES.md carries zero genuine Epic-22 register entries; the gate fails on the unset-required-input, insufficient-data, and overflow designed failures. Expected fail; recorded. |

## Deferred / UNPROVEN / out-of-scope (recorded, never counted green)

- **E22-F03 — T22-328 admission single-frozen-as-of (UNPROVEN, P1).** The SC-11 `admit_walk_forward`
  invariant (one registry as-of resolved and frozen for every window; fragments by explicit
  fingerprint not name@latest; frozen as-of stamped into every window label) is reachable only
  through the Epic-13-owned B-15 `RegistryReadPort` and Epic-13/15-owned fragment materialization
  (RegistrationRecord + registry hub + risk templates + WriterId). Per the EPIC-BINDING RULE
  registryread is an Epic-13 seam consumed-not-owned; that fixture is out of Epic-22's independent
  surface. The robustness-side fingerprint-not-alias resolution discipline IS proven (T22-326/328).
- **E22-F04 — T22-302 forward-compat reader sub-clause (UNPROVEN, P2).** No multi-format result
  reader ships at format version 1, so the "unknown/later format version → unsupported-capability
  refusal" counter-case is not constructible. The AD-5 integer-stamp discipline that makes forward
  readability possible IS verified (T22-302 PASS).
- **L0/L1/L2/L4/L5 independent suite — deferred-by-tier (PLAN §7.7), not a coverage gap.** Under T3
  the pure-unit statistic arithmetic (percentile/p-value edge cases), hypothesis properties over the
  bootstrap and seed derivation, mutation sensitivity on the carve-out/refusal guards, and an
  end-to-end governed run (needs Epic 14/15) are not authored; each P0/P1 behaviour they would prove
  is pinned once at L3 above.
- **Epic-owned seams, noted-not-tested (PLAN §7.2–7.6):** orchestrator governor / process-per-run
  fan-out / one-ledger-line-per-run (Epic 15); B-2 loop internals — sub-phase order, warm-up lock,
  forming-bar prevention (Epic 14); CT-32 minting + fingerprint engine (Epic 14/19); qmf-data split
  governance — seal/embargo/purge/knowledge-time (Epic 3); GAP-0048-gated fidelity content.
- **PLAN-INTEGRITY caveat (PLAN §7.8):** the task-named authorities
  `_bmad-output/test-artifacts/test-design-qa.md` and `.../test-design/QMX-handoff.md` do not exist
  in this worktree (`_bmad-output/test-artifacts/` is absent). R-001 and P0-assertion-3 were taken
  from the task brief; the L-level scheme was reconstructed from the ratified LENS-TEST-STRATEGY and
  the sibling epic_13 plan. Recorded, not worked around.

## Exit-criteria check

1. Every P0/P1 AC in the PLAN maps to ≥1 executed L3 test with a recorded PASS or FINDING — met.
2. **R-001 satisfied:** T22-303/304/305 PASS, reinforced by T22-310/315/321 — money/P&L/equity stay
   exact-integer, a float lives only inside the declared statistic (scaled rational), money re-entry
   only via the named AD-22 conversion, float measures take label-derived identity.
3. **L20/SC-06/SC-07 firewalls green:** T22-307 (no verdict), T22-309/319/325 (robustness never edge,
   no money gating), T22-317 (persist-synthetic → policy rejection), T22-327 (OOS not-yet-ruled),
   T22-314/324/329 (no baked default).
4. **Refusal discipline:** T22-308/317/323/327/T22-PIN-01 each assert a RETURNED CT-04 refusal of the
   correct category — and T22-PIN-01 records where the source instead RAISES (F-22-01).
5. **Confirmed findings recorded:** F-22-01 (OverflowError, P0) and F-22-02 (FAILURES.md gap, P1).
6. Deferred / UNPROVEN items above are each recorded with owning epic or deferral reason — none
   silently counted as passed or failed.
