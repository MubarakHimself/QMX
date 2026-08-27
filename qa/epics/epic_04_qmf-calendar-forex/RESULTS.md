# RESULTS — Epic 4: qmf-calendar-forex extension (T4 lightest gate)

**FR covered:** FR-021 (the only FR in this epic). **Contracts:** CT-02 (implemented as a
provider), CT-04 (typed refusals), CT-05 (fp1 identity — extension computes none of its own),
CT-07 (lineage edge). **Stories:** 4.1, 4.2, 4.3.

## Run

- Command (task): `uv run pytest qa/tests/epic_04 -q --tb=short` → **35 passed, 1 skipped** (the
  hypothesis property test skips gracefully when hypothesis is absent, via `pytest.importorskip`).
- Command (authoritative, property test executed): `uv run --with hypothesis pytest qa/tests/epic_04 -q`
  → **41 passed, 0 failed, 0 errored**.
- Tests **written:** 41 pytest nodes across 6 test files (`test_l0_gates.py`, `test_41_tzdb_verify.py`,
  `test_42_rollover_boundary.py`, `test_42_provider_refusals.py`, `test_43_registration_identity.py`,
  `test_acc1_identity_lineage.py`) + `conftest.py` (fixtures) + `_epic4_helpers.py` (independent oracle).
  These realise the plan's 12 planned executable tests (L0 G1–G3; L1 4.1-U1/U2, 4.2-U1/U2/U3/U4;
  L2 4.2-C1, 4.3-C1; L4 ACC-1), expanded with parametrizations and positive/negative controls.
- **Passed 41 / Failed 0 / Errored 0 / UNPROVEN requirements 2** (see findings.csv E4-F01, E4-F02).
- **Falsifiability verified:** an out-of-band harness confirmed each headline assertion FAILS when
  fed a violating expectation/input (rollover boundary, FM-1 mismatch, FM-3 formatted input, FM-2
  cross-calendar, binding-changes-identity) — no hollow greens. Independent observation: refusals are
  read as RETURNED `TypedRefusal` values (category asserted, never a parsed exception string); identity
  effects are read through qmf-core's own `fingerprint`/`GovernedEvidenceLedger` sinks owned by the test.

## Per-test results

### L0 static / documentation gates (source & pyproject read as read-only evidence)

| Node | Req | Result | Meaning |
|---|---|---|---|
| `test_g1_extension_has_own_pyproject_under_extensions_tree` | 4.1 b1 (FR-021, AR-02) | PASS | Extension builds from `extensions/qmf-calendar-forex/` with its own pyproject, not under the roster. |
| `test_g1_ships_no_namespace_owning_qmf_init` | 4.1 b1 (FM-5) | PASS | No `src/qmf/__init__.py` — PEP 420 implicit namespace; does not claim the qmf.* roster namespace. |
| `test_g1_declares_only_the_forex_submodule_not_a_roster_package` | 4.1 b1 | PASS | `module-name = "qmf.calendar_forex"`, own explicit SemVer, redefines no roster package. |
| `test_g2_exactly_one_pinned_tzdata_dependency` | 4.1 b1/b4 (AR-27) | PASS | Exactly one `tzdata==2025.2` exact pin (not a range), no second tzdata dep. |
| `test_g2_source_declares_no_alternate_or_fallback_tzdb_path` | 4.1 b2 | PASS | No system/OS tzdb path and no fallback in source — the pin is the one tzdb source. |
| `test_g3_extension_defines_no_shared_noun[Venue/Account/Instrument/WriterId/TradingDate/CivilDate/Instant/SessionWindow]` | 4.3 b4 / 4.2 b5 (FM-5) | PASS ×8 | The extension defines no shared noun (`class X` absent from every source file). |
| `test_g3_shared_nouns_used_are_the_qmf_core_types` | 4.2 b5 (FM-5) | PASS | The `TradingDate`/`CivilDate`/`CalendarIdentity` the provider emits ARE the qmf-core classes. |
| `test_g3_extension_computes_no_fingerprint_of_its_own` | 4.2 b5 (CT-05) | PASS | No `hashlib`/`sha256`/local serializer — fp1 is qmf-core's only. |
| `test_g3_extension_imports_only_qmf_core_not_other_roster_packages` | 4.1 b1 (deps) | PASS | Imports no other roster peer (registry/data/indicators/structure/venue/risk). |

### Story 4.1 — import-time tzdb verify-or-refuse (FM-1)

| Node | Req | Result | Meaning |
|---|---|---|---|
| `test_41_u1_match_arm_provider_ready_and_exposes_identity_and_tzdata` | 4.1-U1 (4.1 b2) | PASS | Match arm: provider is usable (produces a TradingDate + a real fp1) and exposes rule-set identity AND the resolved tzdata version. |
| `test_41_u1_match_arm_verify_import_tzdb_returns_ok_identity_when_versions_agree` | 4.1-U1 control | PASS | The extension's own import-time seam returns Ok(identity) when resolved==pin (positive control sharing the mismatch arm's machinery). |
| `test_41_u2_mismatch_arm_returns_unavailable_dependency_refusal` | 4.1-U2 (4.1 b3, FM-1) | PASS | A REAL resolved-tzdb ≠ pin (controlled `tzdata.zi` = 2019a vs pin 2025b) RETURNS an `unavailable dependency` refusal naming pinned/resolved. |
| `test_41_u2_mismatch_arm_is_not_a_usable_provider_and_attests_no_tzdb` | 4.1-U2 (FM-1) | PASS | On mismatch `provider_state` = (identity None, tzdata None, ready False): not usable, NO fingerprint attested against the unverified tzdb. |
| `test_41_u2_core_verify_seam_refuses_on_mismatch` | 4.1-U2 reinforcement | PASS | Fully-public `verify_tzdb_pin` refuses `unavailable dependency` on mismatch; accepts equal (both arms reachable). |

### Story 4.2 — forex-17NY provider (rollover, sessions, refusals)

| Node | Req | Result | Meaning |
|---|---|---|---|
| `test_42_c1_nanosecond_rollover_boundary[winter-EST]` | 4.2-C1 (4.2 b1, R-CAL-ROLLOVER) | PASS | 16:59:59.999999999 NY → D; 17:00:00.000000000 NY → D+1 (winter/EST), 1 ns apart, different dates. |
| `test_42_c1_nanosecond_rollover_boundary[summer-EDT]` | 4.2-C1 | PASS | Same nanosecond boundary holds in summer/EDT. |
| `test_42_c1_trading_date_carries_forex_identity_in_band[winter/summer]` | 4.2-C1 (4.2 b1) | PASS ×2 | Returned TradingDate carries `forex-17NY` + rule-set version + tzdata version in-band. |
| `test_42_c1_boundary_tracks_ny_zone_across_dst_not_a_fixed_utc_offset` | 4.2-C1 (R-CAL-ROLLOVER) | PASS | 17:00-NY boundary shifts exactly one hour in UTC across DST (EST 22:00 UTC vs EDT 21:00 UTC) — tracks the zone, not a fixed offset. |
| `test_42_c1_property_matches_independent_17ny_oracle` | 4.2-C1 (L1 property) | PASS (skipped w/o hypothesis) | 250 whole-second instants over 2000–2060 match the independent 17:00-NY oracle; both D and D+1 arms reachable. |
| `test_42_u1_fm3_formatted_inputs_are_refused_only_instant_is_accepted` | 4.2-U1 (4.2 b1′, FM-3) | PASS | A formatted instant (ISO string, date, datetime, CivilDate, bare int) is refused (INVALID_INPUT, field=instant); only an Instant is accepted. |
| `test_42_u1_fm3_no_format_an_instant_constructor_exists` | 4.2-U1 (FM-3) | PASS | TradingDate exposes no `from_instant`/`from_local_date`/`from_string` — the format-an-instant path does not exist. |
| `test_42_u2_weekend_gap_is_closed_and_sunday_reopens` | 4.2-U2 (4.2 b2) | PASS | Fri-18:00-NY (→Sat) and Sun-12:00-NY are closed (Ok(None)); Sun-18:00-NY (→Mon) reopens (SessionWindow). |
| `test_42_u2_holiday_is_data_closed_while_neighbouring_non_holiday_is_open` | 4.2-U2 (4.2 b2) | PASS | New Year's Day (in the pinned holiday DATA set) is a full-day closure; neighbouring non-holiday weekday is open. |
| `test_42_u2_session_bounds_are_rule_derived_rollover_instants_not_a_constant` | 4.2-U2 (4.2 b2) | PASS (see E4-F01) | Open-session bounds equal the independently-computed [prev-day 17:00 NY, this-day 17:00 NY) — length derived from the rule, not a baked constant. |
| `test_42_u3_fm2_cross_calendar_comparison_returns_a_typed_refusal` | 4.2-U3 (4.2 b3, FM-2) | PASS | Comparing/equating a forex TradingDate with a different-identity TradingDate RETURNS a typed refusal; within-identity equality returns a real bool (control). |
| `test_42_u4_fm4_day_boundary_and_news_questions_are_out_of_authority` | 4.2-U4 (4.2 b4, FM-4) | PASS | A day-boundary AND a news question EACH return an `unsupported capability` out-of-authority refusal; a market-hours question is answered (control). |

### Story 4.3 — registration, identity vs binding

| Node | Req | Result | Meaning |
|---|---|---|---|
| `test_43_u1_registration_via_named_surface_records_distribution_identity` | 4.3-U1 (4.3 b1) | PASS | `register_forex_17ny()` yields a working registration; distribution name+version are recorded and ride into the fp1 identity content (alongside the calendar identity). |
| `test_43_u1_no_ambient_discovery_declared_or_implemented` | 4.3-U1 (4.3 b1) | PASS | pyproject declares no plugin entry-points; source (parsed via `ast`) uses no pkgutil / entry_points / `__init_subclass__` — never ambient. |
| `test_43_u1_each_registration_call_is_explicit_and_independent` | 4.3-U1 (4.3 b1) | PASS | Each call returns its own handle; no import-time ambient global registry. |
| `test_43_c1_binding_only_change_leaves_derived_identity_unchanged` | 4.3-C1 (4.3 b3, R-CAL-IDENTITY) | PASS | A binding-only change (venues/accounts) leaves the artifact fingerprint unchanged; binding never appears in the fingerprinted content. |
| `test_43_c1_identity_moves_only_on_rule_set_or_tzdata_change` | 4.3-C1 (CT-05) | PASS | The fp1 changes on a rule-set change and on a tzdata change, and is stable for identical content — sensitive to identity, not binding. |

### Acceptance scenario (L4)

| Node | Req | Result | Meaning |
|---|---|---|---|
| `test_acc1_tzdata_pin_change_yields_new_fp_lineage_edge_and_no_rewrite` | ACC-1 (4.2 b5, 4.3 b1/b2; CT-05, CT-07) | PASS | Re-deriving the same instant after the tzdata pin changes → new distinct fp1; a `supersedes` lineage edge from fp(new) to fp(old); the earlier artifact is byte-unchanged and re-writes idempotently (never overwritten), observed through a `GovernedEvidenceLedger`. |
| `test_acc1_no_change_control_equal_pins_refuse_a_lineage_edge` | ACC-1 control | PASS | With no pin change, identities fingerprint equal AND `describe_tzdata_pin_lineage` refuses — proving the distinct fp + edge come specifically from the tzdata change. |

## UNPROVEN / narrowed requirements (rule 5 — scope honesty)

- **E4-F01 — Story 4.2 b2 "session/trading-day length treated as data, never assuming constant"
  (the two-different-lengths witness):** UNPROVEN as a positive witness. Under forex-17NY every OPEN
  session is exactly 24h, because US DST transitions occur only on Sundays at 02:00 NY, which fall
  inside the *closed* weekend gap `[Fri 17:00 NY, Sun 17:00 NY)`; no open session ever spans a DST
  transition, and holidays close a day rather than shorten it. So no non-24h open session is
  constructible to exhibit "two different lengths." This is **not a defect** — the provider supplies
  length as explicit rule-derived bounds (verified: open/close equal the independent 17:00-NY rollover
  instants) and bakes in no session-length constant (verified: G3 finds none). The *law* is proven;
  the plan's specific positive witness is not constructible. Recorded, not green.

- **E4-F02 — Story 4.1 b4 / AR-27 "a tzdata pin change is at minimum a minor SemVer bump":** UNPROVEN
  at runtime. This is a release-process rule over the changelog/pyproject, checkable only as an L0 doc
  gate at release time. A single-version static worktree (pin `tzdata==2025.2`, version `0.1.0`, no
  changelog history) cannot exercise a pin change. `DISTRIBUTION_VERSION == pyproject.version ==
  __version__` is consistent, but consistency at one version does not prove the bump discipline.

## Observations & scope notes (not findings)

- **Refusal categories the spine does not pin.** CT-02 (line 109) states cross-calendar comparison
  "returns a typed refusal; the specific CT-04 category is not pinned by the spine." Accordingly
  4.2-U3's hard gate is "a refusal, not an answer"; the observed category (`invalid input`, from
  qmf-core's `TradingDate.compare`) is recorded as evidence only, not gated as contract-required.
- **FM-3 category.** The FM-3 row's word "Unsupported" reads as prose: the provider refuses a formatted
  input with `invalid input` (field=instant), which is consistent with CT-02's `refusals_emitted`
  (invalid input | unavailable dependency) for a malformed calendar input. No finding.
- **FM-4 category.** Day-boundary/news out-of-authority refusals use `unsupported capability`, the
  natural reading of "out of authority" for a capability the calendar does not have. No finding.
- **Distribution identity vs calendar identity (Story 4.2 b5 vs 4.3 b1).** The *calendar-derived
  artifact's calendar identity* is rule set + tzdata only (4.2 b5, verified by 4.3-C1 + ACC-1). The
  extension's *registration artifact* additionally stamps distribution name+version as AD-2 identity
  fields (4.3 b1, verified by 4.3-U1). These are consistent, not contradictory; the binding is the
  field excluded from both.
- **The FM-2 refusal mechanism lives in qmf-core** (`TradingDate.compare`), but 4.2-U3 asserts it on
  the forex provider's *own identity-bearing output*, which is the in-scope behaviour (the provider's
  TradingDate carries `forex-17NY` in-band such that cross-calendar comparison refuses).

## Explicitly out of scope (Epic-Binding — noted, not tested; Epic 4's only duty is to refuse)

Per the PLAN's Epic-Binding boundary and the task's own epic-binding rule, these task-named priorities
are owned by other epics and are NOT tested here (Epic 4 only *refuses* them, proven by 4.2-U4 / FM-4):
dead zones + session-handover buffers and news-window instrument scoping (CT-31, COMP-QMF-RISK, Epic
10); "feed has no `actual` values / absence not silently defaulted" (COMP-CALENDAR-FEED, Epic 6 + CT-31
fail-closed, Epic 10); "R-009: refusals have register entries" (CT-25/CT-31 risk-journal, Epic 10 — a
market-hours calendar owns no register/journal). The specific holiday *dates*, exact session *instants*,
and the tzdata/rule-set *version strings* are extension-pinned data with no ratified spine oracle
(GAP-0037 answered as not-a-core-gap); the laws (holidays-as-data, weekend gap, participation-in-
fingerprints) are proven, the specific values are not asserted as correct.

## Plan-provenance caveat (carried from PLAN.md)

`_bmad-output/test-artifacts/test-design-qa.md` and `.../QMX-handoff.md` are absent from this worktree;
the L0–L6 level architecture and the L2=contract / L4=scenario index follow this lane's task binding.
No P0/P1 assertion from the absent 15-item handoff is confirmed to bind Epic 4, and `R-009` is
unresolvable here (it belongs to the CT-31/CT-25 risk surface, Epic 10). If the real handoff is
restored, reconcile the level numbering and P0/R-gate ids against it.
