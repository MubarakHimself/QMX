# L6 REQUIREMENTS-FIDELITY REVIEW — Epic 4 (qmf-calendar-forex)

**Verdict: GAPS**

Reviewer scope: one question per test — does it assert what the requirement demands, or what
the implementation happens to do? Authorities read: `_bmad-output/planning-artifacts/epics.md`
Epic 4 section (lines 1096–1180: FR-021; Stories 4.1/4.2/4.3), `docs/contracts/ct-02-time-calendar.yaml`,
`docs/contracts/ct-04/ct-05/ct-07`. The task-named `test-design-qa.md` and `QMX-handoff.md` are
absent from this worktree (the author flagged this; confirmed).

Nothing was run or edited under `qa/tests/epic_04/`. Two read-only `uv run python -c` probes were
executed against the installed extension to adjudicate the E4-F01 UNPROVEN claim (evidence below).
No source file was touched; no git command was run.

---

## Headline

The suite is **honest and above the tier-1 bar on the four laws it actually drives** (17:00-NY
rollover at nanosecond resolution, FM-3 formatted-input refusal, FM-2 cross-calendar refusal,
FM-4 out-of-authority refusal). Refusals are read as **returned `TypedRefusal` values with the
category branched on structure**, never parsed exception strings; the rollover oracle in
`_epic4_helpers.py` is genuinely independent (stdlib `zoneinfo`, never the source's helpers);
positive/negative controls are present on every refusal test. That part is real.

The gaps are all of one kind: **the epic's safety-critical clauses are proven one step short of
the surface the requirement names**, and two of those short-falls are not recorded as UNPROVEN.
Specifically: FM-1 is proven on a private helper instead of the public provider; the TZPATH pin
— the mechanism the whole "identical across server moves" claim rests on — is never observed at
all; and **one of the two UNPROVEN rows is factually wrong** — the witness the author declared
structurally unconstructible is constructible, and I constructed it.

---

## 1. The UNPROVEN claim in E4-F01 is false — verified

`findings.csv` E4-F01 and `RESULTS.md` state, of Story 4.2 b2 / CT-02 line 40 ("session and
trading-day length are data no consumer may assume constant"):

> "every open session is exactly 24h because US DST transitions (Sun 02:00 NY) fall only inside
> the closed weekend gap [Fri 17:00 NY, Sun 17:00 NY); **no non-24h open session exists to observe**."

That is true of *modern* US DST practice only. The **pinned tzdb itself** contains US war-time
transitions that do not fall on a Sunday, and they are inside `Instant`'s representable range
(`qmf/core/chrono.py` line 249: "1677 through 2262").

Evidence, run against the real `cf.get_provider()` through public surfaces only:

```
war-Mon-1942-02-09  session hours: 23.0     # America/New_York EWT begins Mon 1942-02-09 02:00
normal-2026-02-04   session hours: 24.0
```

Both instants resolve correctly; both sessions are open; their lengths differ. That is **exactly**
the plan's requested positive witness — "two open sessions of different length, both resolving
correctly" — obtainable in six lines against the shipped pin, with no fake and no private helper.

Consequences:

- E4-F01 is a **wrong expectation**, not a correctly-recorded UNPROVEN. Rule 5 was invoked to
  excuse a clause that rule 1 could have proven.
- The surviving test, `test_42_u2_session_bounds_are_rule_derived_rollover_instants_not_a_constant`,
  asserts bounds on a **single 24-hour day**. A counter-implementation computing
  `close = open + 24h` — the literal "assuming a constant" that CT-02 line 40 forbids — passes it.
  That is a hollow green in the exact place the tier-1 review was hardening.
- The implementation is **not** at fault: it derives both bounds from `_rollover_instant_on` and
  correctly returns 23h. The requirement holds; only the test fails to prove it.

## 2. FM-1 is proven on a private helper, never on the public provider (unrecorded narrowing)

Story 4.1 b3 (epics.md 1120–1123) and CT-02 line 46 both bind the behaviour to **package import**:
"*When the package initializes* … it returns an `unavailable dependency` typed refusal **and does
not become a usable provider**."

Every mismatch-arm test drives `qmf.calendar_forex._tzdb.verify_import_tzdb(pinned=…, zone_dir=…)`
and `_tzdb.provider_state(...)` — a **private module**, with the pin hand-passed as an argument.
This violates the author contract rule 3 ("drive public surfaces only, never private `_helpers`").

What is therefore never observed:

- `cf.get_provider()` returning a refusal on a mismatched tzdb. Its not-ready branch
  (`__init__.py` lines 121–133) is **never executed by any test**.
- `cf.get_calendar_identity()` on a mismatch.
- `cf.register_forex_17ny()` on a mismatch — `_registration.py` lines 154–166 duplicate the same
  not-ready branch, and are likewise never executed. Story 4.3's registration-on-an-unverified-tzdb
  path is entirely untested.

This is **constructible**, so it is a narrowing, not an impossibility: a subprocess with a shadow
`tzdata` package on `PYTHONPATH` whose `zoneinfo/tzdata.zi` header declares a different IANA
version, then `import qmf.calendar_forex; cf.get_provider()`, exercises the real import path with a
real resolved-version mismatch. Not done, and **not recorded as UNPROVEN** — a rule 5 violation.

Stakes: the untested branch is the one that decides whether a fingerprint can be attested against
an unverified tzdb. That is FM-1's entire purpose.

## 3. TZPATH forcing — the mechanism the epic exists for — has no test

Story 4.1 b2: "it **forces the timezone path (TZPATH) to its pinned tzdata** and reads the resolved
tzdb version". CT-02 line 46 repeats it; CT-02 line 15 states the point ("results stay identical
across server moves, DST shifts, tzdata updates").

No test observes TZPATH at all. The only proxy is
`test_g2_source_declares_no_alternate_or_fallback_tzdb_path`, which greps lowercased source for the
literal substrings `"/usr/share/zoneinfo"`, `"fallback"`, `"system tzdb"`,
`"except zoneinfonotfounderror"`. That gate:

- forbids a **word**, not a behaviour — a future docstring reading "no fallback path" fails it,
  while a real fallback written `except Exception: return Path("/etc/zoneinfo")` passes it;
- is a banned shape under rule 2 (source prose as the observer);
- cannot show that `zoneinfo` actually resolves the pinned directory.

The direct check is trivial and behavioural: after import, assert `zoneinfo.TZPATH` equals
`(str(Path(tzdata.__file__).parent / "zoneinfo"),)`; and/or set a bogus `TZPATH` before import and
show the extension overrides it. Neither exists. Not recorded as UNPROVEN.

---

## Wrong-expectation tests

Ranked. "Wrong expectation" here = asserts something other than what the cited requirement demands,
or asserts something that cannot fail.

| # | Test node | What is wrong |
|---|---|---|
| W1 | `test_42_provider_refusals.py::test_42_u2_session_bounds_are_rule_derived_rollover_instants_not_a_constant` | Asserts CT-02 line 40 on one 24h day. `close = open + 24h` passes it. The 23h witness (1942-02-09) exists and is unused. Backed by the false E4-F01 row. |
| W2 | `test_41_tzdb_verify.py::test_41_u2_*` (3 nodes) | Drive private `_tzdb.verify_import_tzdb` / `_tzdb.provider_state`; the requirement is stated at package initialization and at the public provider. Rule 3 violation; public refusal branches never executed. |
| W3 | `test_l0_gates.py::test_g2_source_declares_no_alternate_or_fallback_tzdb_path` | Substring-greps source prose for the word "fallback"; first assertion (`PINNED_TZDATA_PACKAGE` is a non-empty str) is a self-declared constant asserted as proof of behaviour — banned shape, rule 2. |
| W4 | `test_41_tzdb_verify.py::test_41_u1_match_arm_provider_ready_and_exposes_identity_and_tzdata` | `assert identity.tzdata_version == cf.PINNED_TZDB_VERSION` is unfalsifiable: `verify_import_tzdb` returns `Ok` **only** when resolved == `PINNED_TZDB_VERSION`, so given the preceding `is_ok`, no counter-case exists. The surrounding behavioural assertions are sound; this line proves nothing. |
| W5 | `test_acc1_identity_lineage.py` (final assertion) | `bytes_a_before.value == canonical_bytes(td_a.value.fp1_identity()).value` recomputes the same expression and compares it to itself — it cannot fail, yet is presented as the "A's canonical bytes are unchanged" evidence. The real no-rewrite evidence is the ledger `IDEMPOTENT` outcome above it. |
| W6 | `test_43_registration_identity.py::test_43_c1_identity_moves_only_on_rule_set_or_tzdata_change` | Builds three `CalendarIdentity` values by hand and fingerprints them via qmf-core. It never touches the extension. It evidences qmf-core's fp1 sensitivity (Epic 1, CT-05), not Epic 4's "the **exposed** calendar identity differs after a pin change". |
| W7 | `test_43_registration_identity.py::test_43_u1_each_registration_call_is_explicit_and_independent` | `a.value is not b.value` proves object freshness, not absence of ambient discovery. The requirement's content is carried entirely by the sibling `ast` gate. |
| W8 | `test_l0_gates.py::test_g1_declares_only_the_forex_submodule_not_a_roster_package` | Docstring claims it checks the version is "not marked dynamic/lockstep-synced"; the assertions only check that a non-empty version string exists. "SemVer **independent of the roster's lockstep ladder**" (Story 4.1 b1) is asserted nowhere. |

Softer notes (recorded, not counted as wrong expectations):

- `test_42_u2_holiday_is_data_closed_...` selects its date by reading the implementation's own
  `RECURRING_HOLIDAYS` table. Defensible — CT-02 line 102 makes the holiday list extension data with
  no spine oracle (GAP-0037 answered) — and the behavioural law (table entry ⇒ closed day, neighbour
  ⇒ open) is falsifiable. But the admitted narrowing lives only in RESULTS.md prose; rule 6 wants it
  as an UNPROVEN row in `findings.csv`.
- ACC-1 simulates the pin change by constructing `CalendarIdentity(..., "2026a")` and
  `Forex17NYCalendar(identity=identity_b)` rather than changing the pin. Acceptable in isolation,
  and the missing link (exposed tzdata version tracks the *resolved* tzdb) is covered by the 4.1-U1
  positive control — but no single test spans the chain, and the shadow-`tzdata` subprocess of §2
  would have closed it end to end.
- `test_42_u1_fm3_no_format_an_instant_constructor_exists` asserts on `TradingDate`, a qmf-core
  noun (Epic 1). Harmless, but it is Epic 1's surface.

---

## Missed requirements (Epic 4 clauses with no covering test)

All confirmed as belonging to **this** epic's section of `epics.md` before listing.

| # | Requirement clause (source) | Status |
|---|---|---|
| M1 | Story 4.1 b2 — "**forces the timezone path (TZPATH) to its pinned tzdata**" (CT-02 line 46; purpose at line 15) | No test. Only a source-prose grep. Not recorded UNPROVEN. |
| M2 | Story 4.1 b3 — "*When the package initializes* … does not become a usable provider" at the **public** surface (`get_provider`, `get_calendar_identity`) | No test. Private helper only. Not recorded UNPROVEN. |
| M3 | Story 4.2 b2 — "**Swap-Wednesday is not modeled** (V1 accounts are swap-free; the extension models neither swap nor dated financing)" (CT-02 line 43) | **Zero coverage, zero mention** in RESULTS.md or findings.csv. Silent omission — rule 5 violation. Cheaply gated: no swap/financing member on the public surface, and a Wednesday session window identical in shape to any other weekday's. |
| M4 | Story 4.2 b2 — the non-constant session-length witness | Provable (§1), untested, wrongly filed as UNPROVEN. |
| M5 | Story 4.1 b1 — "**When the extension is built with uv_build**" | Nothing asserts `build-backend = "uv_build"`, nor that the distribution actually builds, nor that the built wheel contains no `qmf/__init__.py`. G1 checks `module-name` and an on-disk absence only. |
| M6 | Story 4.1 b1 — "carrying a SemVer version **independent of the roster's lockstep ladder**" | Not asserted (see W8). |
| M7 | Story 4.3 b1 / 4.1 b4 — pin-and-version consistency | RESULTS.md asserts in prose that "`DISTRIBUTION_VERSION == pyproject version == __version__` is consistent" and that `PINNED_TZDATA_PACKAGE` matches the declared pin. **No test asserts either.** Both are one-line static gates. A report claim with no test behind it. |
| M8 | Story 4.3 b4 — "**Given the extension's conformance test suite / When it runs at the Tier-2 gate**" | The *property* is gated (G3 grep); the existence of a conformance suite wired to the Tier-2 gate is not observed. Also the grep is line-anchored `^\s*class <Noun>\b`, so `TradingDate = NewType(...)` or a re-export alias slips through (partly mitigated by `test_g3_shared_nouns_used_are_the_qmf_core_types`). |

Correctly excluded (noted, not tested — other epics own them): CT-31 dead zones / session-handover
buffers and news-window scoping (Epic 10), the calendar **feed**'s `actual`-value handling (Epic 6),
R-009 register entries for refusals (CT-25/CT-31, Epic 10), and the venue-measured daily-bar
boundary of CT-02 lines 44–45 (Epic 8). Epic 4's only duty toward these is to refuse, and
`test_42_u4` proves the refusal. The author's epic-binding discipline here was correct.

---

## Per findings.csv row

| Row | Requirement | Verdict |
|---|---|---|
| **E4-F01** — session-length-as-data, two-differing-lengths witness "structurally not constructible" | FR-021 / CT-02 line 40 (Story 4.2 b2) | **WRONG EXPECTATION.** The claim is factually false. Verified against the shipped pin through public surfaces: trading date Mon 1942-02-09 yields a **23.0h** open session vs **24.0h** on 2026-02-04, both resolving correctly. The reasoning generalized modern US Sunday-02:00 DST practice to the whole tzdb; the pinned tzdb carries a Monday war-time transition inside `Instant`'s 1677–2262 range. The requirement is provable, the implementation satisfies it, and the row should be deleted in favour of a real test. |
| **E4-F02** — tzdata pin change ⇒ ≥ minor SemVer bump, unprovable at runtime | FR-021 / AR-27 (Story 4.1 b4) | **UNPROVEN, CORRECTLY RECORDED** — with one caveat. The release-process core (a *change* forcing a bump) genuinely cannot be exercised in a single-version static worktree; recording it is right. But the row's own supporting claim — that `DISTRIBUTION_VERSION == pyproject version == __version__` and that `PINNED_TZDATA_PACKAGE` matches the declared `tzdata==` pin — is asserted **in prose only, by no test** (M7). The provable half of the clause was left unproven inside a row that says the whole clause is unprovable. |

**Genuine violations of source behaviour: 0.** No test in this suite exposes a defect in
`extensions/qmf-calendar-forex/`, and every behaviour I probed independently (rollover, session
derivation including the 23h case, refusal categories) matched the requirement. The epic's problems
are in the **evidence**, not the code.

---

## Required to reach "adequate"

1. Replace the E4-F01 row with a real test: two open sessions of different length
   (1942-02-09 → 23h, 2026-02-04 → 24h), both correct, driven through `provider.session_window`.
   Falsifiability arm: a `close = open + 24h` expectation fails it.
2. Prove FM-1 at the public surface — shadow-`tzdata` subprocess, `import qmf.calendar_forex`,
   assert `cf.get_provider()` and `cf.register_forex_17ny()` both return an
   `unavailable dependency` refusal and expose no identity. Retire the private `_tzdb` drivers to
   supporting evidence.
3. Assert TZPATH is forced to the pinned `tzdata` zoneinfo directory, behaviourally. Delete the
   `"fallback"`-word grep or demote it to a comment.
4. Add the Swap-Wednesday / no-dated-financing gate (M3), or file it as an explicit UNPROVEN row —
   silence on it is the one omission with no paper trail at all.
5. Add the one-line static gates for M5/M6/M7, or file each as UNPROVEN.
6. Delete W4's tautological equality and W5's self-comparison; they are the only two assertions in
   the suite that cannot fail.
