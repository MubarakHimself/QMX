# Epic 23 — QMB synthetic data — RESULTS (audit tier T3)

Independent verification of Epic 23 (Stories 23.1–23.4) per
`qa/epics/epic_23_qmb-synthetic-data/PLAN.md`. Tests assert what a *requirement*
demands (B-7, L20, AR-33, SC-06/07, spec R1–R8, the CT-* contracts, the
constitution) — never what the source happens to do. A failing test is a FINDING;
source is read-only evidence, never edited to make a test pass, no assertion
weakened to pass.

**Run:** `uv run pytest qa/tests/epic_23 -q --tb=short` from the worktree root.

## Summary

| Metric | Count |
|---|---|
| Test functions authored & executed | **30** |
| Passed | **27** |
| Failed (= FINDINGS, the 3 regression pins) | **3** |
| Errored | 0 |
| UNPROVEN Epic-23-owned requirements | 0 |
| Deferred-by-tier / out-of-scope (noted, not counted pass or fail) | see §Deferred |
| Findings recorded in `findings.csv` | **3** (E23-F01/02/03) |

The 26 planned §4 test ids are realised across 30 pytest functions (AC 23.1.3 →
4 functions T23-303-*, AC 23.1.5 → 2 functions T23-305-*). Every P0/P1 AC owned
by Epic 23 maps to at least one executed L3 test; all 3 regression pins failed
exactly as the plan predicted (the failure IS the evidence). No unexpected
additional failing test surfaced.

## Per-test ledger (L3 acceptance conformance)

| Test id | Requirement | Prio/Level | Status | One-line meaning |
|---|---|---|---|---|
| T23-301 | R1/B-3/AR-14 (23.1 AC1) | P1/L3 | PASS | Config selects exactly one of 4 processes; fp1 is the qmf-core canonical fingerprint; artifact written alongside the run. |
| T23-302 | R2/CT-10 (23.1 AC2) | P1/L3 | PASS | History-seeded without a source-dataset id RETURNS invalid input; gbm records `source_dataset_id=none`; gbm citing a dataset refused. |
| T23-303-scanner | R6/AR-15/NFR-02 (23.1 AC3) | P0/L0-borrow | PASS | NFR-02 money-path float scanner flags 0 findings over all 15 `qmb/data` files. |
| T23-303-tick | R6/AR-15 (23.1 AC3) | P0/L3 | PASS | Every emitted price is an exact int, strictly positive, quantized to the instrument tick (tick=25). |
| T23-303-grid | R6 (23.1 AC3) | P0/L3 | PASS | Timestamps are int64 UTC-ns; the grid honors an injected market-hours calendar's weekend gap (no bar in the closed span). |
| T23-303-rounding | R6/AD-7 (23.1 AC3) | P0/L3 | PASS | The declared rounding mode governs the single float→int money crossing (FLOOR vs CEILING differ; both tick-quantized). |
| T23-304 | R6/R8 (23.1 AC4) | P0/L3 | PASS | OHLC-gate violation (high<body, low>body, non-positive) RETURNS invalid input; valid bar accepted unchanged — never silently corrected. |
| T23-305-menu | R2/R8/B-1 (23.1 AC5) | P1/L3 | PASS | Deferred & unknown processes → unsupported capability; corporate-action on forex CFD → invalid input; never a silent drop. |
| T23-305-select | B-1 (23.1 AC5) | P1/L3 | PASS | All 4 processes produced by the same `generate` entry point, config-selected (library never swapped). |
| T23-306 | B-7/R3 (23.2 AC1) | P0/L3 | PASS | Label carries exactly one claim class as a field distinct from `world`; out-of-set class refused. |
| T23-307 | B-7/R3 (23.2 AC2) | P0/L3 | PASS | From-scratch gbm robustness → policy rejection; history-seeded additionally permits robustness. |
| T23-308 | L20/R3/R8 (23.2 AC3) | P0/L3 | PASS | Edge/alpha/validation claim under any of the 4 processes → policy rejection; a permitted label never claims edge. |
| T23-309 | SC-07/L38 (23.2 AC4) | P1/L3 | PASS | Unset threshold refused (no invented default); bare-number threshold refused post-hoc; interface invents no number; preregistered threshold accepted. |
| T23-310 | SC-06/B-7 (23.2 AC5) | P0/L3 | PASS | world=simulated store read is inadmissible as governed evidence → policy rejection; replay world passes. |
| T23-311 | R2/spec §1 (23.2 AC6) | P1/L3 | PASS | Gaussian-family robustness label carries the machine-readable destroy-structure caveat; block-bootstrap/gbm carry none. |
| T23-312 | R4/AR-14 (23.3 AC1) | P0/L3 | PASS | Store-level `origin=synthetic` record with all six provenance fields present; carried in the record and the generate receipt (not a filename). |
| T23-313 | B-7/SC-06 (23.3 AC2) | P0/L3 | PASS | World derived `simulated` from provenance; caller-declared world=replay/live on synthetic input → invalid input (cannot override). |
| T23-314 | B-2/B-3/B-7 (23.3 AC3) | P0/L3 | PASS | Replay clock / replay adapter on synthetic store → invalid input (top-level); simulated clock binds; flat generator-config replay clock refused. |
| T23-315 | R4/R8 (23.3 AC4) | P0/L3 | PASS | Synthetic load into replay/live and promotion toward live money → policy rejection; world=simulated is its legal home. |
| T23-316 | B-7/B-14 (23.3 AC5) | P1/L3 | PASS | Procedure-ephemeral perturbation stays world=replay, creates no store partition, robustness-only; procedure+seed enter the label; admission-evidence use refused. |
| T23-317 | AR-33/B-7 (23.3 AC6) | P0/L3 | PASS | Synthetic write routes only to the synthetic-tainted partition; a write at live/governed namespace → policy rejection; generation persists only to the tainted partition. |
| T23-318 | R5/B-10 (23.4 AC1) | P1/L3 | PASS | Artifact bit-reproducible across runs; reproduce against a mismatched fingerprint → invalid input (reproduce-or-refuse); different seed → different id. |
| T23-319 | R4/R5/spec §2A.3 (23.4 AC2) | P1/L3 | PASS | Pinned RNG deterministic and NOT stdlib Random; generation unaffected by the stdlib global random state; algorithm+version recorded in provenance. |
| T23-320 | R5/spec §2B (23.4 AC3) | P1/L3 | PASS | Substream = base_seed+index; scenario k regenerates in isolation to the same fingerprint as inside the fan-out; each tagged by index. |
| T23-321 | R5/spec §2B (23.4 AC4) | P1/L3 | PASS | History-seeded scenario 0 is the untouched original (source OHLC verbatim on the grid); scenario 1 is perturbed. |
| T23-322 | spec §5 Q7/R3/L20 (23.4 AC5) | P0/L3 | PASS | From-scratch gbm fan-out: no anchor, robustness_band_computable False, band request → policy rejection, infra-stress/logic-smoke only; history-seeded differs. |
| T23-323 | B-5/R7/R8 (23.4 AC6) | P2/L3 | PASS (synthetic-side) | Divergent gbm fan-out: failing scenarios counted & typed (filtered_count + failures), survivors returned, produced+filtered==count — never silently dropped. Governor mechanics = Epic-15 (see §Deferred). |
| **T23-PIN-01** | R-006/FR-046/B-1 | P0/L3 | **FAIL → E23-F01** | generate capability CLI-only, absent from the Python API door (B-1 door-parity break). |
| **T23-PIN-02** | R-007/R6/DEC-0105 | P0/L3 | **FAIL → E23-F02** | History-seeded generator silently reuses the source's declared scale at the target scale — no named AD-7/AD-22 conversion, no refusal. |
| **T23-PIN-03** | R-008/B-7/FM-3 | P0/L3 | **FAIL → E23-F03** | Replay-clock-vs-provenance guard evaded when the generator config is nested under a composed config — re-opened synthetic-on-money-path backdoor (highest severity). |

## Findings (3) — every regression pin failed exactly as authored

- **E23-F01 (R-006 / F-23-01, P0):** the `qmb data generate` capability is reachable
  from the CLI door but ABSENT from the Python API door. The shipped parity catalog
  (`doors/parity.py CAPABILITY_LIBRARY`) maps `data.generate` → `(DATA_COMMANDS,
  data_front_identity)`, omitting the `generate` function, so the door-parity contract
  never flags the gap. **Cross-confirmed by Epic 16 F16-F02** (jointly owned; Epic 16
  owns the parity mechanism, this pin locks the specific missing capability).
- **E23-F02 (R-007 / F-23-02, P0):** a history-seeded generator ignores the cited
  source dataset's declared scale — the draw adapters use `config.scale` and the raw
  source integers, never the source bars' declared scale. A source at scale 3 into a
  target at scale 5 produced closes `[1201..1205]` at scale 5 (source magnitude reused
  verbatim, 100x mis-scaled), with no named AD-7/AD-22 conversion and no refusal
  (DEC-0105: never a silent rescale).
- **E23-F03 (R-008 / F-23-03, P0, highest severity):** the B-7 replay-clock guard in
  `resolve_generator_config` fires flat but is evaded when the config is nested under a
  `generator_config` key — the nested-merge drops the outer `clock`/`world` before the
  guard runs. Flat `clock=replay` refuses; nested `{generator_config, clock=replay}`
  and `{generator_config, world=live}` both resolve `Ok`. A re-opened
  synthetic-on-money-path backdoor.

## L6 independent review (folded in — no additional findings)

Adversarial read of `qmb/src/qmb/data/` against B-7 / L20 / AR-33 / SC-06/07 and the
four stories' ACs (this level reads source; §4.3's requirement-derived discipline does
not bind it):

1. **Store-level taint is genuine store metadata (T23-312):** `SyntheticStoreProvenance`
   is a structured `Result`-returning value type with a `fp1_identity` + `as_record`
   carrying all six fields; `generate()` routes it as a partition sidecar, not a filename
   convention. Confirmed.
2. **`world=simulated` derived on every store-read path (T23-313):** the sole world
   derivation (`derive_world_from_store_provenance` / `read_synthetic_store` /
   `resolve_store_clock_binding`) reads provenance and refuses a caller-declared
   non-simulated world; no store-read path lets a caller declare world. Confirmed.
3. **Claim class bounded by lineage (T23-307/T23-322):** `permittable_claim_classes` and
   `_refuse_impermissible_claim` bound robustness to history-seeded lineage AND drop it
   under `world=simulated`; the from-scratch fan-out sets `robustness_band_computable=False`
   with a policy-rejection band refusal. No path lets a gbm run emit robustness or a band.
4. **No synthetic path writes a governed/live namespace (AR-33 / T23-317):** the only
   store-write router (`route_synthetic_persist`) hardwires the `synthetic-tainted`
   partition and refuses any governed/live target; `GOVERNED_EVIDENCE_NAMESPACES` is
   derived from qmf-core. Confirmed.
5. **F-23-03 confirmed by tracing the guard through composed compilation:** the
   `resolve_generator_config` nested-merge (`generator_config` inner) carries only
   `destination/output_root/calendar/source_series`, dropping outer `clock`/`world`
   before `_refuse_replay_clock_on_synthetic` — the nested binding evades the guard.
6. **F-23-02 confirmed by tracing source scale into quantization:** the source bars'
   declared `scale` is never consulted by the draw adapters or `_assemble_bars`; only
   `config.scale`/`config.tick_size` govern the money-path crossing → silent reuse.
7. **F-23-01 confirmed by enumerating both door surfaces:** `qmb.data.generate` is
   adapted by `doors/cli/tree.py` but is not among `qmb.doors.api`'s re-exports.
8. **RNG is QMX-owned/version-pinned (T23-319):** `PinnedRng` is an explicitly-seeded
   SplitMix64 instance (no module global, not `random.Random`); generation is
   stdlib-random-independent by test; algorithm/version recorded in provenance.
9. **Every `raise` on the synthetic surface enumerated:** the ONLY `raise` in
   `qmb/data/*.py` is `rng.py:107` `raise ValueError` in `PinnedRng.randrange(n<=0)` — a
   documented programmer-error guard on an INTERNAL RNG primitive (AR-13 sanctions
   exceptions for programmer error), unreachable from the public `generate` path (block
   bootstrap always calls `randrange(num_starts>=1)`). All public domain boundaries
   RETURN CT-04 refusals. **Not a finding.**

## Deferred / out-of-scope (recorded per §7; none counted as pass or fail)

- **AC 23.4.6 governor mechanics — OWNED BY Epic 15 (AR-50/B-5).** Process-per-run,
  `min(cpu,memory)`, enqueue-when-full are Epic-15 requirements; T23-323 asserts only the
  synthetic-side scenario-failure honesty (typed + counted + filtered_count). The governor
  admission (`admit_scenario_fanout`) is exercised in Epic 15, not here (EPIC-BINDING).
- **Market-hours calendar correctness — DEPENDS ON Epic 4 (qmf-calendar-forex).** T23-303
  proves the grid honors an *injected* calendar's weekend gap; which sessions/holidays are
  correct is Epic 4's authority (§7.5). Bounded, not a gap.
- **GAP-0048-gated content — DEFERRED by seam (SC-06).** The actual `world=simulated`
  unlock, verdict-bearing claims, and fill/slippage/financing fidelity cannot be exercised;
  only the refusal seams (T23-310/313/314/315/317) are testable now. Deferred by design.
- **Threshold values / α levels / percentile-band numbers — DEFERRED (SC-07).** Ship as
  config-declared configurables with no ratified value; only the discipline (no invented
  default) is testable (T23-309). Deferred, not a gap.
- **L0/L1/L2/L4/L5 independent suite — DEFERRED-BY-TIER (T3).** The pure-unit
  tick/RNG/bootstrap math, hypothesis properties over seeds and OHLC deltas, mutation
  sensitivity on the taint/refusal guards, and the end-to-end governed run are the T1
  treatment; each behaviour they would prove is pinned once at L3 here (§7.7). Not a
  requirement gap.
- **Door-parity mechanism (FR-046) — OWNED BY Epic 16.** T23-PIN-01 asserts only the
  synthetic capability's presence in both surfaces; the parity engine is Epic 16's
  (`T-16.5`); this finding is jointly owned and cross-confirmed by Epic 16 F16-F02.
- **PLAN-INTEGRITY CAVEAT (§7.8):** `_bmad-output/test-artifacts/test-design-qa.md` and
  `.../test-design/QMX-handoff.md` (named authorities for the L0–L6 architecture, the
  Per-Epic template, and the 15 P0/P1 assertions) are ABSENT from this worktree
  (`_bmad-output/test-artifacts/` does not exist; confirmed by full-tree search). The T3
  scope, the L-level scheme, and the risk gates were reconstructed from the ratified tiers,
  the sibling `epic_22` plan, and the task brief. Recorded, not worked around.

## Exit criteria (per PLAN §8)

1. Every P0/P1 AC maps to ≥1 executed L3 test with a recorded PASS or FINDING — **met**.
2. L20/AR-33/SC-06 firewall green (T23-307/308/310/312/313/315/317/322) — **met**.
3. Money & integrity contracts (T23-303 scanner+tick+grid, T23-304) — **met**.
4. Refusal discipline: every "is refused" test asserts a RETURNED CT-04 refusal of the
   correct category (context present-non-null, retryability present); no public boundary
   raises (only the sanctioned internal `randrange` guard) — **met**.
5. Confirmed findings recorded, each pin FAILED as predicted (E23-F01/02/03) — **met**.
6. L6 review delivered (folded in above; every public-boundary path returns CT-04) — **met**.
7. Deferred / out-of-scope items explicitly recorded with owning epic / reason — **met**.
