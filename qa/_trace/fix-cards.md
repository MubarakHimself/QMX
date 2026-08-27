# QMX fix-card backlog

Lane-agnostic. Each card can be picked up by the attended epic-factory (Claude or Grok plugin) or
published to `queue/` for the unattended engine lane. Nothing here selects itself — the operator
picks, in the order the operator wants.

**Ranking.** Severity first, then damage (how far a defect propagates before anything notices).
Findings cluster into one card wherever one change fixes them.

**The rule that makes a card done.** Every card names a **proving test** that must move
FAILING → PROVEN *without being edited to suit the fix*. Where a red test already exists it is named;
where it does not, the card's first task is to write it and watch it fail. A card whose proving test
was relaxed to accommodate the code is not done — that is the exact failure mode this phase exists to
catch, and it was found in five lanes.

**Size.** S ≈ one file, one surgical change. M ≈ a few files or one seam re-wired. L ≈ a design
decision plus its wiring.

**Count: 35 cards — 4 critical · 14 high · 12 medium · 2 low · 3 process/policy.
By size: 20 S · 11 M · 1 M–L · 3 L.** (Three of the 35 are non-code: FC-33 and FC-35 are process,
FC-34 is a gate policy.)

---

## CRITICAL

### FC-01 — Enforce the exit-preservation invariant on the path that withholds acts
- **Findings:** QMX-F001, QMX-F002 · **Severity:** critical · **Size:** L
- **Requirements:** 10.8-AC1, CT-30, CT-24-AC2, L39, FR-033, P0-9, SCN-0010, handoff assertion 9
- **Files:** `packages/qmf-risk/src/qmf/risk/control_action.py` (215, 347), `packages/qmf-risk/src/qmf/risk/paper.py:435`, `packages/qmf-risk/src/qmf/risk/door.py:770`
- **Change:** `check_exit_preservation` is an exported guard with **no caller** anywhere in
  `packages/qmf-risk/src`. Give `resolve_execution_target` the parameter it needs to see what it is
  resolving (an intent-family or act discriminator), and route it — plus every other path that can
  withhold an act (`arbitrate_same_tick`, `EnforcementScope`, `mint_control_action`) — through the
  guard before withholding. `ExitIntent` carries no `execution_target` while `EntryIntent` does;
  deciding which branch is correct (exits route and must survive, or exits resolve no target at all)
  is the design decision inside this card and belongs in an ADR either way. Do **not** resolve it by
  making the guard advisory-with-a-caller — the invariant is that a control *may never* block a
  risk-reducing act.
- **Proving test:** `qa/tests/epic_10/test_h_control_action.py` — put a control in force
  (`BLOCKS_PAPER`, a protection window, the kill switch) and propose each of the six
  `RiskReducingAct`s against the real enforcement path; each must survive. Then the specific case: an
  exit intent under an active `BLOCKS_PAPER` control must not be withheld. Delete the three dead
  property parameters (`kind`, `authority`, `scope`) — the one-argument function cannot accept them,
  so 200 Hypothesis examples currently explore 6 distinct calls.
- **Why first:** 107/107 Epic-10 tests pass today, with an empty `findings.csv`, against an invariant
  nothing enforces.

### FC-02 — Close the nested-config replay-clock bypass
- **Findings:** QMX-F003 · **Severity:** critical · **Size:** S
- **Requirements:** 23.3-AC5, B-7, B-2, FM-3, DEC-0164, R-008, handoff assertion 7
- **Files:** `qmb/src/qmb/data/generate.py:592-602` (`resolve_generator_config`), `:1851-1876` (`_refuse_replay_clock_on_synthetic`)
- **Change:** the nested-body merge carries forward only `destination`, `output_root`, `calendar` and
  `source_series`, so the outer `clock` and `world` are already gone when the guard runs against the
  merged body. Either carry `clock` and `world` into the merged body before the guard, or run the
  guard against the outer body as well. The guard itself is correct — do not touch it. Reachable from
  the shipped operator door: `qmb/src/qmb/doors/cli/tree.py:511` routes nested bodies and
  `_is_generation_request` treats a nested `generator_config` mapping as a generation request.
- **Proving test:** `qa/tests/epic_23` T23-PIN-03 — already FAILING; must go green unedited.

### FC-03 — Persist the CT-15 money path on download
- **Findings:** QMX-F004 · **Severity:** critical · **Size:** M
- **Requirements:** 18.1-AC3, RQ5, RQ6, RQ7, AR-46, CT-01, CT-10, AR-15, handoff assertion 1
- **Files:** `qmb/src/qmb/data/download.py:307`, `packages/qmf-data/src/qmf/data/ingest.py:201-217`
- **Change:** `IntakeReceipt` already carries `quote: TickQuote | None` and
  `tick: TickObservation | None` alongside `observation`; `download` submits
  `receipt.value.observation` only and discards the quote, and `SourceObservation.foreign_money` is
  populated from `record.foreign_money` which the download path never sets. Thread the quote's
  scaled-integer bid/ask through to the persisted CT-10 observation. Do not widen the CT-10 schema —
  the field already exists.
- **Proving test:** `qa/tests/epic_18` — the two existing reds (L2 behaviour, L3 shape) must both go
  green unedited. Add one read-back assertion: the archived observation carries a non-null
  `foreign_money` that is an exact integer at the declared scale.

### FC-04 — Ledger every reaped run on partial spawn failure
- **Findings:** QMX-F010 · **Severity:** critical (damage: a governed run's only record vanishes) · **Size:** M
- **Requirements:** FR-045, AR-51, B-4, B-5, R-010, handoff assertion 11
- **Files:** `qmb/src/qmb/orchestrator/spawn.py:197` (`spawn_governed`), `:255` (`spawn_concurrent`), `:283` (`_reap_live`)
- **Change:** neither batch function takes a ledger parameter, so no line can be minted through them;
  on a start failure `spawn_concurrent` kills already-started siblings and returns the refusal with
  zero accounting for them. Give the batch path the same `finally`-class ledger obligation the
  single-run `finish_run` door has — the handoff names this exactly ("ledger writes as a
  `finally`-class obligation, not a happy-path step"). Each reaped run gets exactly one line,
  cause = reaped/abandoned.
- **Proving test:** TO-BE-WRITTEN, `qa/tests/epic_15` — spawn N runs where run k fails to start, read
  the merge view off the real on-disk fragment directory, assert exactly one line per already-started
  run and zero for the never-started one. This test cannot be written against today's public surface,
  which is itself part of the fix: the door has to exist.

---

## HIGH

### FC-05 — Gate `register_bot_definition` on both conformance verdicts
- **Findings:** QMX-F005 · **Severity:** high (candidate P0) · **Size:** M
- **Requirements:** FR-048, 12.7-AC1, CT-33 §44 and §67, AR-64, ADR-0018, handoff assertion 14
- **Files:** `qml/src/qml/declaration/bot.py:662`, `qml/src/qml/__init__.py:93,284`, `qml/examples/conformant_bot_usage.py:230-258`
- **Change:** the function takes a raw declaration payload and stamps + persists a CT-33 Bot-kind
  record through an injected `Registrar` with no ticket and no verdict consulted. Require a
  `ConformanceTicket` (or both layer verdicts) as a parameter and refuse `policy rejection` when
  either layer fails or when no verdict is presented. Update the shipped example to pass the ticket —
  it currently passes `candidate.declaration`, which is what makes the gate decorative at the call
  site. **Blocked on operator ruling OR-06:** CT-33 declares `wiring_status: defined-unwired`. If the
  doc is current, `install_bot_definition_kind` + `register_bot_definition` are unauthorized wiring
  and the fix is removal, not gating.
- **Proving test:** TO-BE-WRITTEN, `qa/tests/epic_12` — mint a valid declaration, obtain a
  `policy rejection` from `gate_registration` (or skip the gate entirely), call
  `qml.register_bot_definition(payload, registrar=Registrar(registry), …)` and observe a **test-owned
  registry sink**. If a record lands, the requirement is violated. Four lines, public surface,
  injected observer — no composition root needed.

### FC-06 — Derive the seal position from the evidence on every read path
- **Findings:** QMX-F006 (unblocks QMX-F091) · **Severity:** high · **Size:** M–L
- **Requirements:** FR-012, CT-12, CT-11:25, 3.4-AC4, L19, SCN-0003, P0-6, R-012, handoff assertion 6
- **Files:** `packages/qmf-data/src/qmf/data/store/append_store.py` (`read_raw`), the `read_view` path, `store/backup_input.py:97` (`read_room`); reference pattern at `rooms.py:303-308`
- **Change:** `resolve_series` already derives its knowledge position from the resolved evidence and
  says why in its own docstring ("never a caller argument, so the seal cannot be bypassed by omitting
  a position nor by an under-stated window"). The other three paths gate on the caller-supplied `at`.
  Apply the same derivation. **Design note:** the raw archive stores opaque rows and may genuinely be
  unable to derive a content position — in which case this is a CT-12 specification gap (the contract
  defines no rule for a raw artifact's knowledge position) and the card's output is a contract
  amendment plus a fail-closed refusal. Either outcome is acceptable; returning sealed rows is not.
- **Proving test:** TO-BE-WRITTEN, `qa/tests/epic_03` — archive an artifact whose rows sit inside the
  sealed window and read at an under-stated position through **every** real entry point (`read_raw`,
  `read_raw_self_guarded`, `read_view`, `resolve_series`, `BackupInput.read_room`), collecting leaks
  by name. Rewrite `3.4-P1` on the `3.3-P2` pattern — a quantifier over *paths*, not over enum labels
  — and assert `{b.value for b in ReadBoundary}` equals AC4's four named boundaries so a dropped
  boundary cannot pass silently. Three currently-passing assertions (`test_3_4_u5` line 167,
  `test_acc_2` line 162, `test_3_4_i1` line 333) must be inverted, not deleted.

### FC-07 — Return typed refusals across every external transport seam
- **Findings:** QMX-F007, QMX-F008, QMX-F009 · **Severity:** high · **Size:** M
- **Requirements:** R-007, CT-15, FR-015, FR-017, FR-018, 6.1-AC5, 6.3-AC1, 6.4-AC1, DEC-0109, SCN-0008, handoff assertion 3
- **Files:** `packages/qmf-data/src/qmf/data/dukascopy.py:605`, `calendar_feed.py:564`, `ingest.py:445`
- **Change:** three bare calls to an injected transport with no `try`/`except`. Wrap each and
  translate the third-party exception into a returned CT-04 typed refusal.
  `decode_calendar_snapshot` already does this correctly for payload faults — follow that shape.
  F008 matters most: a raised exception at `calendar_feed.py:564` bypasses `CalendarFeedImport.run`'s
  fail-closed data-quality journal *and* its alarm, so a transport outage produces no journal entry
  at all. One defect at three sites; clustered.
- **Proving test:** `qa/tests/epic_06` — `test_l1_002_dukascopy_transport_raise_*`,
  `test_l1_002_calendar_transport_raise_*` and `test_l1_002_ingest_over_raising_port_*` are already
  FAILING with real third-party exception types (`ConnectionResetError`, `socket.timeout`,
  `BrokenPipeError`, `urllib.error.URLError`). All must go green unedited.

### FC-08 — Bound-and-check before `float()` at every magnitude boundary
- **Findings:** QMX-F012 · **Severity:** high · **Size:** S
- **Requirements:** CT-04, DEC-0109, 22.1-AC2, T22-PIN-01, handoff assertion 3
- **Files:** `qmb/src/qmb/robustness/carveout.py:137,192`, `qmb/src/qmb/robustness/significance.py:414`
- **Change:** all three sites coerce `float(value)` *before* the `math.isfinite` guard, on a value
  validated only as `isinstance(value, (int, float))`. `int` is unbounded. Move the magnitude bound
  ahead of the coercion and return a typed refusal — the handoff names this as a testability
  requirement ("bound-and-check before conversion at every named conversion boundary").
  `significance.py:414` (`math.log(float(ratio))` inside `next_bar_log_returns`) is the site the lane
  missed; it sits on the P0 anti-look-ahead return series and is reachable from `run_significance_gate`
  with two legally-constructed positive `Price` closes.
- **Proving test:** `qa/tests/epic_22` T22-PIN-01 already FAILING for both carve-out sites. Add a
  third arm for `next_bar_log_returns` with closes `1` and `10**400` at one scale — write it, watch
  it fail, then fix.

### FC-09 — Enforce currency and unit-kind on the Study objective comparison
- **Findings:** QMX-F011 · **Severity:** high · **Size:** S
- **Requirements:** R10, CT-01, 21.2-AC4, FR-001, handoff assertion 2
- **Files:** `qmb/src/qmb/optimize/objective.py:200-217,224-234`
- **Change:** `StudyObjective` stores `target_currency` and `target_unit_kind` and then `meets_target`
  compares bare `Fraction` magnitudes with no guard, on the path `_place_trial` calls. Route the
  comparison through the qmf-core money law (`exact.py:33-35` — a cross-kind operand returns a typed
  refusal) or guard explicitly and return `invalid input`. One function.
- **Proving test:** `qa/tests/epic_21` T21-PIN-01 already FAILING; its same-currency companion passes
  first, so the red is isolated and not vacuous. Must go green unedited.

### FC-10 — Honour the source dataset's declared scale in the synthetic generator
- **Findings:** QMX-F013 · **Severity:** high · **Size:** M
- **Requirements:** 23.1-AC3, R-007, DEC-0105, CT-10, AR-15, AD-7, AD-22, handoff assertion 1
- **Files:** `qmb/src/qmb/data/generate.py:1445-1446` (`_coerce_source_bars`), `:1108,1166,1206` (draw adapters), `:1260-1281` (`_FloatToScaledInt`)
- **Change:** the source row's declared scale is read into `SyntheticBar.scale` and then never
  consulted — every adapter divides by `float(10**config.scale)` and the one float→integer boundary is
  constructed with `config.scale`. Either convert with lineage across the AD-22 boundary (the exact
  `10^(target−source)` factor, recorded as a derived value) or refuse when the scales differ.
  DEC-0105 forbids the silent rescale that happens today, and 23.1-AC3's tick-size quantization is
  wrong for the target instrument.
- **Proving test:** `qa/tests/epic_23` T23-PIN-02 already FAILING — but **tighten it before it is
  used as the lock**: today it asserts a magnitude proxy (`min(closes) > max_source_magnitude * 10`)
  which would also pass on a wrong-by-2× conversion. Pin the exact factor and add a lineage assertion.

### FC-11 — Emit chart series inside the CT-32 artifact
- **Findings:** QMX-F014 (folds in QMX-F087's R20 half) · **Severity:** high · **Size:** L
- **Requirements:** R18, R20, AC19.4, R-RPT-11, R-RPT-12, R-RPT-13, CT-32 QMB-extension invariant, DEC-0163
- **Files:** `qmb/src/qmb/results/ct32.py:174`, `packages/qmf-risk/src/qmf/risk/performance.py:510-549`, `qmb/src/qmb/results/charts.py`, `render.py`, `interpret.py`
- **Change:** the CT-32 `PerformanceResult` container has no chart-series and no
  trade-event-reference field — the two *declared QMB extensions* of the container. `charts.py` is
  1,406 lines reachable only by a caller who already knows to ask, and
  `assemble_run_performance_result` writes `results/ct-32.json` and nothing else. Add the declared
  extension fields, call `assemble_v1_chart_set` from the assembly path, and give the chart set a
  canonical identity representation. Fold in R20's three unbuilt series while you are here — the
  monthly-returns grid (with annual column), the monthly-return distribution and the trade-P&L
  distribution are all already implemented and have zero tests, because the test adopted the module's
  own four-name `V1_CHART_SERIES_NAMES` constant as its oracle.
- **Proving test:** TO-BE-WRITTEN, `qa/tests/epic_19` — a stored artifact carries a machine-readable
  series, retrievable by an agent that reads only the artifact.
  **Three existing assertions change with the fix and must not be relaxed before it:** `test_a19`'s
  `assert not hasattr(ChartSet, "fp1_identity")` (which will fail once the fix lands — correctly),
  `test_a19`'s `"chart" not in flat`, and `test_c1`'s `all_files == ["ct-32.json"]`. Until the fix
  ships they stay in place *with this finding filed against them*, so their green does not read as
  coverage.

### FC-12 — Bind the cost port into the handler the run loop actually drives
- **Findings:** QMX-F015 · **Severity:** high · **Size:** M
- **Requirements:** 17.1-AC1, 17.4-AC2, 17.5-AC4, AR-56, R18, R29
- **Files:** `qmb/src/qmb/execution/handler.py` (`ExecutionSliceHandler`), `qmb/src/qmb/execution/ports.py:1024` (`apply_execution_ports`), `qmb/src/qmb/runloop/loop.py:600`
- **Change:** two disjoint execution paths exist. `apply_execution_ports` composes
  fill → slippage → cost correctly, with the never-resize and taint guards, and is called **nowhere**
  in `qmb/runloop/`. `ExecutionSliceHandler` — the `SliceHandler` the six sub-phases drive — takes
  `fill` and `slippage` only: no `CostPort` field, no `itemize` call, no `cost` token in the file.
  Bind the cost port and route `execute_resting` through the composed path. Consequence today: no
  commission is itemized on any real run, 17.4-AC2's per-partial pro-rated commission has no
  producer, and 17.5-AC4's four-line cost-drag decomposition can never be assembled from live output.
- **Proving test:** TO-BE-WRITTEN, `qa/tests/epic_17` — drive `ExecutionSliceHandler` end-to-end for
  one slice with test-owned `RecordingFill` / `RecordingSlippage` / `RecordingCost` and assert the
  cost recorder saw the post-slip fill. Expect it to fail (or to be unwireable) first.

### FC-13 — Derive door parity from the door surfaces, and publish the missing capability
- **Findings:** QMX-F016, QMX-F017 (and E23-F01, the same defect) · **Severity:** high · **Size:** M
- **Requirements:** 16.5-AC1, 16.5-AC2, FR-046, AR-58, R18, R19, R-006, handoff assertion 12
- **Files:** `qmb/src/qmb/doors/parity.py` (`CAPABILITY_LIBRARY`), `qmb/src/qmb/doors/cli/tree.py:31,36,511-512`, `qmb/src/qmb/__init__.py` `__all__`, `qmb/tests/test_door_parity.py`
- **Change:** two halves of one problem. (a) Export `generate` and `has_generator_config` from
  `qmb.__all__` so the API door re-exports them. (b) Replace the hand-maintained 15-entry
  `CAPABILITY_LIBRARY` reconciliation with a derived one — walk the click tree plus an AST of the
  `invoke_*` adapters on one side, introspect `is`-identity against `qmb` on the other. The catalog
  is what masked (a): its `data.generate` row is `("DATA_COMMANDS", "data_front_identity")` and omits
  the library-function element every sibling row carries, so `capability_gaps` had nothing to compare
  and reported clean. **Authority note (see OR-08):** the ban on a hand-maintained map comes from the
  brief's risk gate `R-006`, not from epics.md — Story 16.5 AC1 requires "identical function surface
  and semantics" and does not itself forbid a catalog. And `R-006` must never be read as `FR-006`,
  which epics.md assigns to Epic 2.
- **Proving test:** `qa/tests/epic_16` T-16.5-gap already FAILING on the real divergence; T-16.5-a is
  the derived reconciler that should replace the catalog-based `qmb/tests/test_door_parity.py`.
  `qa/tests/epic_23` T23-PIN-01 covers the same defect — re-home it as a cross-reference so one
  defect is not counted as two P0s (OR-09). Also relax T23-PIN-01's CLI half, which hard-codes the
  adapter attribute name `run_generate` and would fail on an unrelated rename.

### FC-14 — Fix the ambient clock read in the download path
- **Findings:** QMX-F018 · **Severity:** high · **Size:** S
- **Requirements:** FIND-001, RQ-CLOCK, RQ2, FR-002, CT-02, DEC-0106
- **Files:** `qmb/src/qmb/data/download.py:127,150,124`
- **Change:** `download.py:127` reads `datetime.now(timezone.utc)` below the composition root and
  `parse_download_request` calls `resolve_end_ns` without a `now=`, so end-defaults-to-today tracks
  the real wall clock with no injection path. `resolve_end_ns` already *takes* `now=` — thread an
  injected `Clock` from the composition root. Do **not** invent the injection key: the current test
  guesses `now` / `clock` / `now_ns` and no ratified authority defines it; pick one and record it.
  The finding stands on DEC-0106 — the `AR-16` id the lane cited does not exist in the worktree.
- **Proving test:** `qa/tests/epic_18` already FAILING, **and** `ambient-scan` must return exit 0 over
  the whole tree (it is FAIL today, which is how this was found). Narrow the test's assertion first:
  as written it bans *any* attribute named `now`/`utcnow`/`today`/`perf_counter`/`monotonic`, so a
  DEC-0106-compliant `injected_clock.now()` would also fail it.

### FC-15 — Route every fp1 through qmf-core's single implementation
- **Findings:** QMX-F019 · **Severity:** high · **Size:** S
- **Requirements:** CT-05, DEC-0108, FR-005, RG-DEPGRAPH, AR-14, handoff assertion 4
- **Files:** `packages/qmf-data/src/qmf/data/backup.py:932-935` (`_fp1_of`), `packages/qmf-data/src/qmf/data/store/backup_input.py:70-72,197` (`_fp1`)
- **Change:** both hand-roll `hashlib.sha256(payload).hexdigest()` and emit `f"fp1:sha256:{digest}"`
  directly, duplicating qmf-core's private `_fingerprint_of_bytes`. Call `qmf.core` instead. The
  damage is latent rather than present: CT-05:20 notes the prefix versions the recipe, so an fp2
  upgrade would silently fork identity across the duplicated copies.
- **Proving test:** `qa/tests/epic_01` `test_e1_i03_single_fp1_implementation_only_in_qmf_core`
  already FAILING. **Widen the detector as part of the card** — it currently requires both
  `hashlib.sha256(` and a literal `f"fp1:sha256:` in the same file and skips any path containing
  `tests/` or `/examples/`, so an offender that concatenates, uses `str.format`, routes through a
  helper, or hashes canonical bytes into `Fingerprint.try_create` is invisible. Read the finding as
  **at least** two duplicates.

### FC-16 — Return a typed refusal from `observation_journal_event_type`
- **Findings:** QMX-F020 · **Severity:** high · **Size:** S
- **Requirements:** R-002, CT-04, AR-13, SCN-0005, handoff assertion 3
- **Files:** `packages/qmf-venue/src/qmf/venue` (`observation_journal_event_type`)
- **Change:** the function is in `qmf.venue.__all__` and raises `ValueError` on a non-`ObservationKind`.
  R-002 as the plan states it, and SCN-0005's Given, are both unqualified: every public venue
  boundary succeeds or returns a typed refusal. Convert the raise to a returned refusal — or, on the
  operator's call, declare the mapping helpers a documented non-boundary and record that as a scope
  decision. What must not happen again is what happened the first time: the behaviour was found,
  confirmed, and then written out of scope by narrowing the test's hand-list after the fact.
- **Proving test:** TO-BE-WRITTEN, `qa/tests/epic_08` — replace `L1-001`'s 47 hand-typed lambdas with
  a programmatic enumeration of `qmf.venue.__all__` (136 names), so a public factory added tomorrow
  falls inside R-002's claim rather than silently outside it.

### FC-17 — Move `qml/host/` out of the qml wheel
- **Findings:** QMX-F021 (shares a root cause with QMX-F035) · **Severity:** high · **Size:** M
- **Requirements:** 11.1-AC4, AD-15, DEC-0171
- **Files:** `qml/src/qml/host/runner.py`, `qml/src/qml/host/worker.py`, `qml/src/qml/host/__init__.py`
- **Change:** `host/` ships inside the qml distribution and imports `subprocess`, `os`, `tempfile`,
  `json`, `uuid` and calls `open()`; its own package docstring concedes it is impure and owns stdlib
  process spawning. AD-15 makes the qml library pure (no threads, no I/O, no process spawning) and
  the ratified Hosting seed (`docs/components/qml.md:126`) places the conformance sandbox runner at
  **QMB's** composition root. Relocate the sandbox runner and the worker entry point to QMB.
  **Interacts with OR-04** (whether `logic/` is a defect in the AC text or in the code) — settle that
  first, then treat `host/` as the substantive half regardless of how `logic/` is ruled.
- **Proving test:** `qa/tests/epic_11` already FAILING (the AD-15 purity scan over `qml/src/qml`).
  Must go green unedited.

### FC-18 — Re-derive `qmb data list` coverage from the CT-10 observations
- **Findings:** QMX-F022 · **Severity:** high (damage: four green tests certify the wrong artifact) · **Size:** L
- **Requirements:** 18.3-AC1, 18.3-AC2, 18.3-AC4, 18.1-AC5, RQ11, RQ18, RQ19, RQ21, R-011
- **Files:** `qmb/src/qmb/data/download.py:346-360` (`persist_coverage_windows` call), `qmb/src/qmb/data/catalog.py:138-164,168-189,307-334` (`list_data`)
- **Change:** the catalog's entire answer — coverage window, per-side presence, observation count,
  provenance, licence tag, revision — is the download **request** round-tripping through a
  `qmb-data-coverage` summary row qmb wrote itself. `list_data` reads back only rows whose
  `kind == COVERAGE_KIND` and never inspects a single CT-10 observation. Three consequences the ACs
  forbid: those rows *are* the authoritative second store (18.3-AC2), side presence can never diverge
  from what the operator asked for so "detect the shortfall before the run starts" is unreachable
  (18.3-AC4), and the licence tag rides the envelope instead of the CT-10 observation R-011 names
  (18.1-AC5). Re-derive coverage from the persisted observations; keep the envelope only as a cache
  that is checked *against* them.
- **Proving test:** TO-BE-WRITTEN, `qa/tests/epic_18` — seed with `side="bid"` only while the request
  asked for `both`, and assert `ask: ABSENT`. Then re-run RQ11, RQ18, RQ19 and RQ21: four currently
  green tests are expected to turn red first, which is the point. RQ19's rebuild test must delete the
  coverage rows, not only the DuckDB projection.

---

## MEDIUM

### FC-19 — Validate `SecretRef` opacity at construction
- **Findings:** QMX-F109 · **Severity:** medium · **Size:** S
- **Requirements:** FR-025, CT-21, AD-9, L34, DEC-0136, DEC-0140
- **Files:** `packages/qmf-core/src/qmf/core/secret.py` (`SecretRef.try_create`); consumer `packages/qmf-venue/src/qmf/venue` (`AccountBinding.try_create`)
- **Change:** CT-21 states verbatim that construction **validates opacity as an invalid-input
  refusal**, and `SecretRef.try_create` enforces zero opacity checks — the gate is absent rather than
  imperfect. Four independent authorities restate the clause with no hedge (the CT-21 invariant, the
  schema field line, `docs/glossary.md`, `docs/components/qmf-core.md`,
  `docs/lenses/security/security-model.md`). "Encodes account data" is not fully decidable, so refuse
  the decidable forms: an embedded venue, broker, account or environment token, and any non-minted
  shape. **Ownership note:** the defective type is `qmf.core.SecretRef`, so the repair lands in
  qmf-core with qmf-venue as the affected consumer — the E8 finding's `requirement_ids` should carry
  that.
- **Proving test:** `qa/tests/epic_08` `test_l2_019` family already FAILING; must go green unedited.

### FC-20 — Ship the missing failure registers
- **Findings:** QMX-F023, QMX-F024 · **Severity:** medium · **Size:** M
- **Requirements:** NFR-11, R-009, AR-21, L27, epics.md:475, 22.1-AC5, 22.3-AC3, 22.4-AC5, handoff assertion 15
- **Files:** `packages/qmf-venue/FAILURES.md` (absent), `packages/qmf-risk/FAILURES.md` (absent), `qmb/FAILURES.md` (present, 765 lines, Stories 14–19 only)
- **Change:** one card, three artifacts, because it is one convention. Write the register for
  qmf-venue (its six door-reachable refusal categories are all live-money paths), for qmf-risk, and
  add the Epic-22 designed failure modes to `qmb/FAILURES.md`. Each entry carries the six NFR-11
  elements: failure class, detection, auto-recovery/retry semantics, visible degraded state,
  notification tier, product-user affordance — written for someone who was not in the design room.
  Sibling parity today is 5 of 7 roster packages, not 5 of 6 as the E8 finding text implies.
- **Proving test:** `qa/tests/epic_08` (qmf-venue) and `qa/tests/epic_22` T22-PIN-02 (qmb) are already
  FAILING; a qmf-risk gate is TO-BE-WRITTEN. **Strengthen all three to the six-field check** — both
  shipped gates are keyword-substring proxies where the plans promised the six fields, and E22-F02's
  `expected` column still claims a form its test never checks.

### FC-21 — Ship `examples/` in qmf-venue
- **Findings:** QMX-F025 · **Severity:** medium · **Size:** S
- **Requirements:** AR-21, L27, DEC-0096
- **Files:** `packages/qmf-venue/examples/` (absent)
- **Change:** all six sibling roster packages ship `examples/`; qmf-venue is the only package missing
  both it and `FAILURES.md`. AR-21 and constitution L27 require every package to ship executable
  tests **and** reference-usage examples that demonstrate its public contract, as tier-1 artifacts.
- **Proving test:** `qa/tests/epic_08` already FAILING; must go green unedited.

### FC-22 — Stamp the CT-03 contract format version and identity projection
- **Findings:** QMX-F026 · **Severity:** medium · **Size:** S
- **Requirements:** CT-03:22, DEC-0103, FR-003, AR-25, DEC-0138
- **Files:** `packages/qmf-core/src/qmf/core/identity.py`
- **Change:** `identity.py` defines no `CONTRACT_FORMAT_VERSION` and no `fp1_identity` — zero matches,
  against 5 in `chrono.py`, 6 in `exact.py` and 2 in `fingerprint.py` — so a CT-03 identity artifact
  carries neither a contract format version nor an identity projection and cannot stamp the
  versioning-from-birth version its own ratified contract requires. Add both. Note why the current
  deferral is wrong, not just absent: E1-C11 excludes CT-03 by docstring and defers the stamp to a
  qmf-registry *record*, which DEC-0138 forbids as the identity source ("never the wrapping registry
  record's fingerprint").
- **Proving test:** TO-BE-WRITTEN, `qa/tests/epic_01` — un-narrow E1-C11 to include CT-03 artifacts.
  It will fail; that is the point.

### FC-23 — Stop routing adapter refusal contexts through `unpersistable`
- **Findings:** QMX-F027 · **Severity:** medium · **Size:** S
- **Requirements:** FR-014, CT-14, 5.1-AC4, 5.2-AC1, R-007, FM-2, DEC-0109, handoff assertion 3
- **Files:** `packages/qmf-data/src/qmf/data/backup.py:299-308` (`copy_export`), `:401-410` (`restore_copy`), `:938-944` (`_storage_failure`); trigger at `packages/qmf-core/src/qmf/core/sinks.py:180-185`
- **Change:** both call sites build `remapped = dict(put.context)` and hand it to
  `qmf.core.unpersistable`, which **raises `ValueError`** when the context carries the reserved key
  `reason` — a key both project refusal builders (`store/refusals.py:35` and `:73`) set
  unconditionally. So a refusal is raised, not returned, across a boundary that
  `docs/components/object-storage.md:31` makes unconditional. Strip or namespace the reserved key
  before remapping, or stop copying the adapter's context. Two call sites, one root; clustered.
- **Proving test:** `qa/tests/epic_05` — both reds already FAILING (each does a `pytest.fail` on
  *any* raise, then asserts a `storage failure` category). Must go green unedited.

### FC-24 — Refuse unknown top-level fields in `Footprint.try_from_mapping`
- **Findings:** QMX-F028 · **Severity:** medium · **Size:** S
- **Requirements:** 11.4-AC5, CT-33
- **Files:** `qml/src/qml/footprint/manifest.py:268-300` (`try_from_mapping`), reference at `:241-266` (`try_create`), reachable via `:593` (`report_completeness`)
- **Change:** `try_create` collects `**rejected`, refuses `FORBIDDEN_HORIZON_FIELDS`, then refuses any
  remaining extra top-level field ("the stream set is nested here, never a second top-level field").
  `try_from_mapping` checks only `FORBIDDEN_HORIZON_FIELDS` and `stream_set` presence, reads exactly
  three keys and silently drops everything else. Make the mapping path enforce the same closed set.
  Reachable: `report_completeness` routes any non-`Footprint` input through the permissive path.
- **Proving test:** `qa/tests/epic_11` already FAILING; must go green unedited.

### FC-25 — Recompute `composition_version` from the bound port set
- **Findings:** QMX-F029 · **Severity:** medium · **Size:** S
- **Requirements:** 17.1-AC4, R8
- **Files:** `qmb/src/qmb/execution/ports.py:93`
- **Change:** `COMPOSITION_VERSION` is `Final[int] = 1`, never recomputed, and
  `BoundExecution.composition_version` defaults to it. AC4 is unambiguous: composition-version changes
  whenever the bound port set **or its order** changes, so identity never silently drifts. Derive it
  from the bound set. The lane substituted a passing `fp1_identity` surrogate — the implementation's
  anti-drift mechanism, not the requirement's — and filed the real gap as UNPROVEN (E17-F04); L6
  re-adjudicated it as a defect with a constructible failing test, so R8 must not be counted green.
- **Proving test:** TO-BE-WRITTEN, `qa/tests/epic_17` —
  `bind(cost=zero).composition_version != bind(cost=percent-of-notional).composition_version`.
  Note `test_t171h` currently asserts `composition_version == 1`, i.e. it asserts the constant this
  card says is wrong; it must be re-pointed, not deleted.

### FC-26 — Close the composite-expression guard on `emit_measure`
- **Findings:** QMX-F031 · **Severity:** medium · **Size:** S
- **Requirements:** R13, AC19.2, R-RPT-10, DEC-0162
- **Files:** `packages/qmf-risk/src/qmf/risk/performance.py` (`FORBIDDEN_COMPOSITE_EXPRESSIONS`), `qmb/src/qmb/results/measures.py` (`emit_measure`)
- **Change:** the roster has no `grade` token and its `weighted-*` members are hyphenated, so they
  substring-match only hyphenated identities. `grade`, `overall_grade`, `letter_grade` and
  `weighted_aggregate` all pass the guard through the exported Epic-19 surface, so a composite score
  is mintable and storable. The AC names "grade" and "weighted rating" explicitly. Normalise
  separators and add the missing tokens. Severity is medium because the shipped 27-name roster is
  clean today and `test_a10`'s deep artifact scan confirms no artifact carries one.
- **Proving test:** `qa/tests/epic_19` already FAILING; doubles as the regression pin.

### FC-27 — Refuse unrostered veto doors and reason classes instead of bucketing them
- **Findings:** QMX-F032 · **Severity:** medium · **Size:** S
- **Requirements:** R17, AC19.3, R-RPT-8, AR-13, AD-36, DEC-0150
- **Files:** `qmb/src/qmb/results/accounting.py:127-139` and `_suppression_key`
- **Change:** only an **absent** door token refuses; an unrostered door string is silently bucketed
  into a brand-new tally key outside the ratified `VETO_DOOR_IDENTITIES` spine roster — exactly the
  "silently bucketing" the module's own refusal message disclaims. `_suppression_key` has the same
  hole for reason classes: any non-empty reason string becomes a new key. The sibling
  `_resolve_authority` **does** close its vocabulary and refuse; follow that shape in both places.
- **Proving test:** TO-BE-WRITTEN, `qa/tests/epic_19` — an unrostered `refusing_door` (e.g.
  `"mystery-door"`) and an unrostered `reason_class` are each typed refusals. Note the existing
  `test_a14_unresolvable_door_...` tests *another epic's* surface
  (`qmf.data.journal.JournalEvent.try_create`) and concludes something about Epic 19; re-point it.

### FC-28 — Declare `numpy` in the qmf-indicators pyproject
- **Findings:** QMX-F033 · **Severity:** medium · **Size:** S
- **Requirements:** R5, AR-06, AR-18, 7.1-AC
- **Files:** `packages/qmf-indicators/pyproject.toml`, `packages/qmf-indicators/src/qmf/indicators/batch.py:374`
- **Change:** `batch.py` calls `importlib.import_module("numpy")` unguarded on the main compute path —
  a `ModuleNotFoundError` there would *raise*, not return a CT-04 refusal — while the pyproject
  declares `dependencies = ["qmf-core", "ta-lib==0.7.1"]`. numpy arrives only transitively through
  ta-lib in `uv.lock`. AR-06 default-deny requires every dependency declared in the package's own
  pyproject. Transitively satisfied today, so this is a governance/gate defect rather than a runtime
  break — which is why it is medium and not high.
- **Proving test:** TO-BE-WRITTEN, `qa/tests/epic_07` — enumerate every non-stdlib module the package
  reaches (static AST **and** `importlib.import_module` string arguments) and require each in
  `pyproject.toml`. **Widen the S1 scanner in the same card:** it filters
  `root.split(".")[0] == "qmf"`, so it is structurally incapable of seeing a non-`qmf` undeclared
  import, and a sibling test currently reads that blind spot as a virtue ("talib is resolved lazily").

### FC-29 — Emit ETA on download progress samples
- **Findings:** QMX-F034 · **Severity:** medium · **Size:** S
- **Requirements:** 18.1-AC5, RQ10
- **Files:** `qmb/src/qmb/data/download.py:369`
- **Change:** every emitted progress sample hard-codes `eta_ns=None` while AC5 requires percent,
  date-reached **and** ETA. Compute the ETA from completed batches against the declared window.
  Note the shape of the miss: the lane's deferral row (E18-U04) defers the supervising-agent
  transport half — fairly Epic 15/16's — while the broken Epic-18 half went unrecorded, which made a
  live defect look scoped.
- **Proving test:** TO-BE-WRITTEN, `qa/tests/epic_18` — assert `eta_ns` is present and monotonically
  decreasing across the sample stream.

### FC-30 — Implement or strike the per-run stochastic slippage seed
- **Findings:** QMX-F030 · **Severity:** medium · **Size:** S (implement) or S (amend the AC) · **Blocked on OR-11**
- **Requirements:** 17.3-AC6, R23, NFR-03
- **Files:** `qmb/src/qmb/execution/slippage.py:285`
- **Change:** `slip_fill` does `del seed` and all five V1 slippage models are deterministic, so AC6's
  "any stochastic term draws from a per-run seed so replay reproduces the same draw" has no
  implementation at all. Two honest resolutions: wire the seed through so a future stochastic model
  is reproducible by construction, or strike the clause from the AC because V1 ships no stochastic
  model. The lane filed it UNPROVEN, which is right for testability but leaves R23 counted green.
  **The operator picks (OR-11).** Note the existing `test_t173n` cannot help either way:
  `derive_slippage_seed(run_a) == derive_slippage_seed(run_a)` is true of any pure function.

---

## LOW

### FC-31 — Kill the corroborated dead symbols
- **Findings:** QMX-F039 · **Severity:** low · **Size:** S
- **Files:** `tools/workspace_meta.py:35,36` (`PACKAGES_DIR`, `EXTENSIONS_DIR`), `packages/qmf-core/src/qmf/core/secret.py:198,219` (`format_spec`, `protocol`), `packages/qmf-registry/src/qmf/registry/persistence.py:402` (`exc_info`), `packages/qmf-core/tests/test_sinks.py:165` (`thing`)
- **Change:** delete these six and nothing else. The 3-way intersection (Skylos × vulture ×
  never-executed coverage) is **empty** — 0 THREE_WAY, 2 TWO_WAY_VULTURE, 0 TWO_WAY_COVERAGE, 77
  SKYLOS_ONLY — and 75 of Skylos's 79 dead-code findings are `unused_parameters`, overwhelmingly
  Protocol method signatures where an unused parameter is *correct*. **Do not run a dead-code
  campaign off the raw 79.**
- **Proving test:** n/a; the Skylos `max_dead_code` ratchet in FC-33 is the gate.

### FC-32 — Close the four real mutation holes in qmf-core
- **Findings:** QMX-F040, QMX-F041, QMX-F042, QMX-F043 · **Severity:** low–medium · **Size:** S
- **Requirements:** CT-01, CT-02, CT-03, DEC-0158, AR-20, DEC-0101
- **Files:** `packages/qmf-core/src/qmf/core/exact.py:304,251`, `chrono.py:171,756,764` — **test-side only**
- **Change:** these are missing assertions, not source defects. Four pins: (a) `_round_fraction_to_int`
  at exactly `value == 0` for every rounding mode — `value < 0` mutated to `<= 0` and to `< 1`
  survives in both branches, so the zero boundary of money-path rounding is unpinned; (b) `chrono`'s
  `_checked_int64` at `INT64_MIN` and `INT64_MAX` and ±1 (E1-U30 pins this for `exact.py` and chrono
  has no equivalent); (c) `DataDrivenClock.wall_now`/`monotonic_now` exhaustion at `len(script)` and
  the cursor advancing by one (E1-U41 pins the exact English message instead, which PLAN §5 itself
  declares not ratified surface — drop the prose assertions, and see OR-03); (d) an empty or
  whitespace-only instrument symbol refuses. Overall kill rate on the two modules is 68%; the rest of
  the survivor set is string-literal noise on unratified prose and should be left alone.
- **Proving test:** the four assertions above; re-run mutmut on `exact.py` and `chrono.py` and confirm
  the named mutants are killed.

---

## PROCESS AND POLICY

### FC-33 — PROCESS: the factory merge gate must run the tier-1 scanners
- **Findings:** QMX-F036 (and QMX-F018, which is what it let through) · **Severity:** high · **Size:** M · **Non-code**
- **Requirements:** FIND-002, NFR-02, AR-11, AR-23, AR-24, FR-001, FR-002
- **Files:** the factory merge-gate configuration (epic-factory plugin and `/queue-publish` engine lane); reference `[tool.poe.tasks.check]` in the root `pyproject.toml`
- **Change:** the gate that shipped epics 4 and later ran **ruff, pyright and pytest only**. `poe check`
  sequences ten steps — `fmt-check, lint, types, test, cov-report, test-tools, money-path-scan,
  ambient-scan, mock-data-scan, secret-scan` — and the four tier-1 scanners are the mechanism NFR-02
  exists to provide, making FR-001 and FR-002 *mechanically* enforced rather than review-dependent.
  Wire the merge gate to invoke `poe check` in full and fail on any nonzero exit. Epic 13's L6 makes
  the same finding from the other side: its lane invoked two of the ten steps.
  **Second half of the same card:** Stories 1.7 and 1.8 — the two scanners themselves — have **zero
  tests** (eight ACs, no must-flag fixture, no must-not-flag fixture, no nonzero-exit assertion).
  A gate nobody tests is a gate nobody can trust; author those fixtures here (QMX-F100).
- **Proving test:** a CI assertion that the merge gate invokes `poe check` in full, plus the Story
  1.7/1.8 must-flag and must-not-flag fixtures at the coverage floor. `ambient-scan` returning exit 0
  is FC-14's gate, not this one's.

### FC-34 — POLICY: the Skylos quality ratchet
- **Findings:** QMX-F038, QMX-F039 · **Severity:** medium · **Size:** M · **Non-code, operator sets the numbers (OR-10)**
- **Baseline (run `33039677890`, `head_sha=2c8d495`, 650 files / 200,886 LOC):** overall grade **C+ (77)**;
  quality **8 / F**; 4,084 quality findings — **25 CRITICAL**, **361 HIGH**, 165 WARN, 1,252 MEDIUM,
  2,281 LOW; dead code **79** (A+ at 0.4 per 1K LOC); **security A+, secrets A+, ai_defects A+,
  dependency_vulnerabilities 0, ai_authored 2 of 4,163**. Every danger bucket is already clean — the
  entire deficit is complexity.
- **Proposal:**
  1. **`max_dead_code = 80` now.** The current count is 79 and the 3-way intersection is empty, so
    this locks in no-regression at essentially zero cost and no cleanup debt. Ratchet down only after
    FC-31 lands (→ 74).
  2. **Work quality off by family, not by number.** The 25 CRITICAL first: 21 `SKY-Q301` cyclomatic
    (to 38) and 4 `SKY-Q306` cognitive (to 64). Concentrated in seven files —
    `qmf-risk/control_action.py` (647, 1486), `qmb/data/download.py:200`, `qmb/data/verify.py:292`,
    `qmb/config/compiler.py` (291, 475), `qmb/data/catalog.py:279`, `qmb/results/measures.py`
    (286, 358), `qmb/results/charts.py:863` — and four of those files are already being opened by
    FC-03, FC-11, FC-14 and FC-18. **Split branches as a side effect of the fix cards that touch them,
    not as a standalone campaign.** Then the 361 HIGH (78 `SKY-Q301`, 103 `SKY-Q502`, 83 `SKY-C304`,
    56 `SKY-Q802`, 21 `SKY-Q702`), family by family.
  3. **Set `max_quality` at today's 4,084 and ratchet down as counts drop** — after CRITICAL is
    cleared, to ≈4,059; after HIGH, to ≈3,698. Never ratchet up.
  4. **Do not gate on the overall letter grade.** It is dominated by the quality bucket (score 8) and
    would block every merge from day one while telling the operator nothing the family counts do not.
- **Note:** complexity is a real signal here, not noise — `qmb/data/download.py:200` at cyclomatic 35
  and cognitive 64 is the same function that carries QMX-F004, QMX-F018, QMX-F022 and QMX-F034. Four
  of the platform's confirmed defects live in one over-branched function.
- **Proving test:** n/a; this is a gate threshold. The operator sets the numbers.

### FC-35 — PROCESS: restore the named authorities into the verification worktree
- **Findings:** QMX-F037 · **Severity:** medium · **Size:** S · **Non-code**
- **Requirements:** GAP-QA-01, and the handoff's own phase-transition gate
- **Change:** `_bmad-output/test-artifacts/` is absent from the verification worktree and **16 of 23
  lanes independently confirmed it**. Every lane therefore reconstructed the L0–L6 taxonomy, the 15
  P0/P1 assertions and its own risk-gate ids from its task brief, so every per-lane P0/P1 label is
  self-assigned rather than read from the authority — and several of them move in this
  consolidation's proof map. Ship the tree into the worktree the lanes run in, and add a lane-entry
  gate that **fails** when a brief names an authority file that is not present, rather than letting
  the lane proceed on a reconstruction.
- **Proving test:** a lane-entry assertion that every authority path named in the brief resolves.
  The lanes' own honesty here was exemplary — every one of them recorded the absence rather than
  papering over it — which is the only reason this is recoverable.

---

## Cards deliberately **not** written

Recorded so the absence is a decision, not an oversight.

- **E4-F01** (session-length-as-data "structurally not constructible") — L6 disproved it by running
  the shipped pin: 1942-02-09 gives a 23.0h open session against 24.0h on 2026-02-04, both resolving
  correctly. The implementation is right; the *row* was wrong. What is owed is a test
  (QMX-F055), not a fix.
- **E2-F01 / E2-F02** (Bot-mint gate absent from `qmf.registry`) — accurate observation, wrong epic:
  epics.md assigns FR-048 to Epic 12, CT-33 is `defined-unwired`, and absence in qmf-registry is the
  ratified build order. Superseded by FC-05. **Also delete the two permanently-red `assert False`
  tests** from the Epic-2 suite so it can go green.
- **The 64 UNPROVEN rows in `findings.csv`** are test work, not fix work. They belong to a
  re-verification lane, not to this backlog — with the exception of the nine the operator may want
  promoted because they carry a P0/P1 assertion: QMX-F045 (human-only signer), QMX-F060 (no numeric
  oracle), QMX-F062 (venue stream granularity), QMX-F063 (amend atomicity), QMX-F070 (admission-bar
  evidence fields), QMX-F074 (equal-fingerprint re-binding), QMX-F076 (sub-phase order),
  QMX-F091 (sealed-holdout admission door), QMX-F096 (synthetic taint surviving persistence).
