# L6 — Requirements-fidelity review — Epic 6 (qmf-data — source intake)

**Reviewer:** independent L6 seat (this file replaces the author-written self-review that
previously occupied this path; a lane author's own "ACCEPT" is not an L6 verdict).
**Scope:** every test node under `qa/tests/epic_06/`, judged on one question — *does the
assertion state what the requirement demands, or what the implementation happens to do?*
**Authorities:** `_bmad-output/planning-artifacts/epics.md` § "Epic 6" (Stories 6.1–6.4);
`docs/contracts/ct-15-external-source-adapter.yaml` (ratified); `docs/contracts/ct-04`,
`ct-07`, `ct-10`, `ct-13`; `docs/components/{qmf-data-ingest,dukascopy,calendar-feed}.md`;
this epic's `PLAN.md` § 3–4 (R-007 gate).
*Note: `_bmad-output/test-artifacts/test-design-qa.md` and `.../QMX-handoff.md` do not
exist in this worktree; PLAN.md § 1 records the same absence. The L0–L6 level architecture
and the R-007 row were reconstructed in PLAN.md and are used here as the standing proxy.*

---

## Verdict: **GAPS**

The lane is **not** a rubber-stamp job — the 15 reds are real, correctly diagnosed, and
were not softened away, which is the failure mode this contract exists to prevent. But the
suite does not clear the hardened contract:

1. The epic's **headline structural claim** — one of the three named task emphases, "no
   intake path writes governed namespaces directly" — is asserted in `test_l3_001` through
   **two observers that are never connected to the system under test**. The green is
   structurally unfalsifiable.
2. **Two clauses that the shipped code actually implements are untested** and are not
   recorded as UNPROVEN: bid/ask **source timestamps** (CT-15 invariant + Story 6.2 AC1)
   and the calendar recorder's **own WriterId / provider event-time provenance** (6.4 AC2).
3. **Rule 2 is breached** in `test_l2_018` (asserting a module constant as proof of
   behaviour) and in the journal-payload assertions (asserting literals the producer
   hardcodes into its own report).
4. **Rule 5 is breached twice** by silent narrowing (6.1 AC3 conversion-under-lineage;
   6.1 AC1 "no package dependency on qmf-data") — mentioned in RESULTS.md prose but absent
   from `findings.csv` as UNPROVEN rows, which rule 6 requires.

None of this touches the reds. E6-F01/F02 stand as genuine defects.

---

## 1. Wrong-expectation / hollow-green tests

Ordered by how much requirement weight the hollow assertion is carrying.

### H1 — `test_l3_acceptance.py::test_l3_001_ingest_path_performs_no_governed_write` — **HOLLOW (severe)**

The test builds two test-owned observers and wires **neither** into the object under test:

```python
ing  = ExternalSourceIngest(port=adapter)     # ingest gets ONLY the port
door = H.RecordingBoundary()                  # never passed to `ing`
_tattle_boundary = SourceObservationBoundary(H.TattleStore())   # never passed to anything
receipts = H.unwrap(ing.fetch_and_intake(...))
assert door.admitted == [], "the ingest path wrote to the producer boundary without an explicit submit"
```

`ExternalSourceIngest` holds no reference to `door`, so **no possible implementation could
make `door.admitted` non-empty** — the counter-case named in rule 1 is unconstructible.
`_tattle_boundary` is constructed, bound to a throwaway name, and never touched again;
`SourceObservationBoundary.__init__` only stores the argument (`source_boundary.py:73`), so
the TattleStore's screaming `__getattr__` is never armed on any path the test drives. The
docstring's claim ("A TattleStore behind a real CT-10 boundary is never touched by the
ingest path") and RESULTS.md line 86 which repeats it are therefore **not evidence**.

The third assertion, `assert not hasattr(ing, "_store")`, probes one hardcoded private
attribute *name*; an implementation that called its store `_evidence_store` passes it. This
is rule-3-adjacent (private-surface probing) and near-tautological.

What *is* real in this test: **Phase 2** — `ing.submit(obs, door)` grows `door.admitted` to
exactly the produced count. That proves the routing helper works; it does not prove the
absence of a second, unrouted write path, which is what AC1 demands.

The load-bearing evidence for this requirement is actually `test_l0_001b`, an import-graph
gate whose ban list is three module names (`append_store`, `engines.parquet`, `facade`).
Note that `ingest.py:54` **does** import `SourceObservationBoundary`, which in turn imports
`EvidenceStore` — the gate passes only because the ratified door is not on the ban list.
That is a defensible reading of DEC-0117, but it means the whole "no direct governed write"
claim rests on a three-name denylist plus a vacuous runtime test.

**Fix shape:** inject the recording door (or a tattling store) into the object graph the
ingest path can actually reach, then assert absence at that sink.

### H2 — `test_l1_properties.py::test_l1_006_mapped_hostile_symbol_stays_opaque_data` — **HOLLOW**

```python
assert is_ok(result) or is_refusal(result)          # tautology: every Result is one or the other
for key in transport.calls:
    assert "\x00" not in key.path_reference          # the symbol under test is "../../evil" — no NUL exists to find
```

Assertion 1 cannot fail for any input. Assertion 2 searches for a NUL byte in a fixture that
contains no NUL, and the loop is a no-op if the adapter refuses before calling the transport.
Neither states the requirement (Story 6.3 AC3 / the plan's "never resolves a path outside the
raw-archive root"). The *sibling* test `test_l1_006_hostile_symbol_refused_no_path_escape`
(14 cases — RESULTS.md says ×14 in one place and "15 adversarial cases" in E6-F05; the list
has 14) is genuine: it drives real hostile identifiers and asserts a typed `invalid input`.
E6-F05 correctly records that no path-resolution surface exists here — so H2 should have
been **deleted in favour of that UNPROVEN row**, not left as a passing node.

### H3 — `test_l2_contract.py::test_l2_018_no_authorized_retention_claim` — **BANNED SHAPE (rule 2)**

```python
assert cal.LEGAL_ARCHIVING_POSTURE == "open-operator-item"
```

This is verbatim the banned shape: *asserting a module's self-declared constant as proof of
behaviour*. `calendar_feed.py:84` defines that string; the test reads it back. The claim in
the author's own review ("no test asserts a module's self-declared constants as proof of
behaviour") is false. The other half of the test — `claim_retention_authorized()` returning
a `policy rejection` — is a purpose-built refusal stub (see H5).

### H4 — journal-payload literals in `test_l2_017`, `test_l2_018`, `test_l4_002` — **PARTLY BANNED (rule 2/3)**

Reading the event back through a real `JournalReader` over a real `EvidenceStore` is exactly
right, and `event_type.value == "data quality"` is a **ratified** CT-13 type — that assertion
is genuine and load-bearing. But these are not:

```python
assert payload.get("defines_window") is False and payload.get("holds_permission") is False
assert payload.get("signal") == "calendar-import"
assert payload.get("legal_archiving_posture") == "open-operator-item"
```

`journal_import` (`calendar_feed.py:~618-630`) writes `"defines_window": False`,
`"holds_permission": False`, `"signal": "calendar-import"` and the posture constant as
**hardcoded literals into its own report**. Asserting them is using the implementation's own
trace as the only observer, and none of these payload keys is ratified prose. Story 6.4 AC2's
real content — *the feed defines no window and holds no permission* — is not proven by a
producer that says so about itself.

Same shape at `test_l4_002`: `assert not hasattr(ev, "window")` over a frozen slotted
dataclass is a structural self-declaration, falsifiable only by editing source.

### H5 — the refusal-stub family — **WEAK / should be UNPROVEN, not green**

`test_l3_002` (×3), `test_l3_005` (first arm), `test_l3_006` (second arm), `test_l2_016`,
`test_l2_018` (first arm) all call methods that exist **solely** to return a refusal:

| method | site | body |
|---|---|---|
| `start_scheduler` / `run_daemon` / `run_retry_loop` | `ingest.py:483-493` | `return refuse_schedule_ownership(...)` |
| `download_complete_corpus` / `checkpoint` / `recover_external` / `run_retry_loop` | `dukascopy.py:507-521` | one-line refusal |
| `mint_severity_scale` / `claim_retention_authorized` / `live_skip` | `calendar_feed.py:531-541` | one-line refusal |

These match AC6 / FM-5 **in letter**, and I am not calling them wrong expectations. But per
rule 1 there is no counter-case a test can construct: the method has no other behaviour to
exhibit, so the assertion carries no information about whether the seam *is* a running
downloader. The information actually lives in `test_l0_002` (no `asyncio`/`threading`/`sched`
import, no `while True`) — which is a good gate and should be named as the primary evidence
for AC6, with the stub tests recorded as corroborating-only. Two arms of these tests *are*
genuine and should be kept: `complete_corpus=true` and an over-max window refused inside
real `fetch` validation (`test_l3_005`), and the `mid`-presented refusals (`refuse_mid_merge`
is reached through real `TickQuote.try_create` / `normalize` paths).

### H6 — duplicated behaviours across levels — **rule 2 (duplicate-and-relabel) + "one behaviour, one level"**

| L2 node | L3 node | same behaviour? |
|---|---|---|
| `test_l2_008_bid_ask_never_merged_to_mid` | `test_l3_008_two_sources_bid_ask_separate_no_mid` | yes — L3 adds only a second source and a fp1-distinctness line |
| `test_l2_009_agreement_corroborates_disagreement_visible` | `test_l3_009_disagreement_inspectable_nothing_averaged` | yes — same three ticks, same two `relate_source_facts` calls, same edge-type + endpoint assertions |
| `test_l2_004_provider_unavailable_returns_refusal_no_fabrication` | `test_l3_006_unavailable_source_refuses_and_fabricates_nothing` (first arm) | yes — identical `BytesTransport(unavailable_refusal)` → `unavailable dependency` |

Lower level wins: the L3 nodes should collapse to their genuinely-additional arms
(`checkpoint`/`recover_external` posture in L3-006; nothing in L3-009). Counting them as
distinct coverage inflates the 84-green figure.

### Tests I checked and found **FAITHFUL** (no action)

- `test_l1_002_dukascopy/calendar_transport_raise_*` and `test_l1_002_ingest_over_raising_port_*`
  — the reds. They assert the ratified CT-15 sentence with real third-party exception types.
  See § 3.
- `test_l1_001_*` — quantified refusal universal with an explicit admitted control arm
  (`test_l1_001_control_valid_record_is_admitted`). Correct falsifiability construction.
- `test_l1_002_bi5_decode_never_raises` / `_calendar_decode_never_raises` — real
  `lzma.LZMAError` / `struct.error` / `UnicodeDecodeError` / `json.JSONDecodeError` surfaced
  through generated bytes; raise-arm caught and reported as failure. Genuine fault realism.
- `test_l1_003_*`, `test_l1_007_*`, `test_l2_002`, `test_l2_010`, `test_l4_001` — fp1
  collision/idempotence properties over generated revision sets, with `test_l4_001` reading
  the **original** back out of a real store after the correction lands. This is the strongest
  work in the lane.
- `test_l1_004_*`, `test_l2_006` — verbatim scaled-int money and zone/offset/resolution
  survival, with the float-refusal counter-arm and an int control.
- `test_l2_012` — license gate over `unknown`/`denied` with a licensed control.
- `test_l2_016` impact-label arm — an arbitrary provider label (`"Medium-Custom-Label"`)
  survives verbatim; a remap to a QMX severity would fail it. Genuinely falsifiable.
- `test_l2_009` / `test_l3_009` edge selection — `relate_source_facts` performs a real
  quote comparison (`ticks.py:296+`), so both arms are behavioural.
- `test_l3_003` second half — a CT-15 `SourceRequest` offered to a TattleStore-backed CT-10
  boundary is refused `invalid input` **before** any store access. Here the TattleStore *is*
  armed and the test is real (contrast H1).
- `test_l0_001` / `test_l0_002` / `test_l0_003` — honest static gates with named counter-cases.

---

## 2. Requirements in this epic's `epics.md` section that **no test covers**

Confirmed epic-bound (all are Story 6.1–6.4 clauses, none owned by another epic).

| # | Requirement clause | Where it lives | Status |
|---|---|---|---|
| M1 | **Story 6.2 AC1 / CT-15 invariant** — "bid and ask preserved separately **with their source timestamps kept**" | `ProviderRecord.bid_timestamp` / `ask_timestamp`; `dukascopy.py:_tick_to_record` populates both | **Implemented in source, asserted nowhere.** No test reads `bid_timestamp`/`ask_timestamp` on any record, `TickQuote`, or `SourceObservation`. Not in findings.csv. |
| M2 | **Story 6.4 AC2** — "recorded under **the recorder's own WriterId**" | `CalendarFeedImport.run(writer=...)`, `JournalWriter` | Untested. The harness passes two different writers (`stream="calendar"`, `stream="obs"`) and asserts nothing about either. Not in findings.csv. |
| M3 | **Story 6.4 AC2** — the event "carries **event-time**, known-at, source, and revision as source evidence" | `_parse_event_time_ns` parses the provider `date` into `event_time_ns` + a foreign block | Only `source`/`revision`/`source_native_id` are asserted (`test_l2_015`). No test asserts the calendar event's event-time equals the provider's declared instant, or that its foreign timestamp survives verbatim — even though the Dukascopy path's equivalent *is* tested. Not in findings.csv. |
| M4 | **Story 6.1 AC3** — "conversions to framework Time and Money **derived under lineage**, corrections appended, never overwritten" | Deliberately out of package: `observation.py:18-19,124,198` says a conversion "is a *derived* artifact carrying lineage, produced elsewhere" | The "corrections appended" half is green (L4-001). The conversion-under-lineage half is **silently narrowed** — rule 5 requires an UNPROVEN row. Not in findings.csv, only prose. |
| M5 | **Story 6.1 AC1** — "application-routed, **creating no package dependency on qmf-data**" | co-located component | Proven only by proxy, and the proxy (H1) is hollow. RESULTS.md § "Carried-forward" F-E06-002 admits the narrowing; rule 5/6 require it as an UNPROVEN row. Not in findings.csv. |
| M6 | **Story 6.1 AC4 / 6.3 AC3** — "**no valid CT-10 observation is emitted**" | — | Asserted only as a returned refusal. Rule 3 requires absence-of-effect to be stated at a sink; no test observes a boundary/store recorder staying empty on the refusal path. Low severity — the refusal short-circuits before construction — but it is the same class of gap as H1. |
| M7 | **Story 6.3 AC1** — "pulled a **single time**… runs never fetch from providers" | — | `test_l3_004` observes the injected transport's call count across a store read. That proves a *read* does not re-fetch; it does not exercise a second acquisition attempt against an already-acquired window. Weak-but-present, not a miss; flagged for honesty. |

Correctly **excluded** and not converted into a pass (epic-binding held — I re-checked both
against `epics.md`): the CT-31 blackout-window enforcement half of 6.4 AC4 belongs to Epic 10
(FR-033), and cTrader-as-source belongs to Epic 8. Both are named in RESULTS.md § Deferred.

---

## 3. Per-`findings.csv` row adjudication

| Row | Requirement ids | My adjudication | Reasoning |
|---|---|---|---|
| **E6-F01** | R-007; CT-15; FR-017; Story-6.3-AC1 | **GENUINE VIOLATION** | CT-15 states the invariant verbatim: *"Boundary failures return typed refusals … **returned, never raised across the boundary** (DEC-0109)."* CT-15's `layer_from: external → layer_to: middleware` puts the external/middleware seam at the adapter, and `dukascopy.py:605` calls `self._transport.fetch_hour(key)` bare — I read it; there is no `try`. The counter-argument (the `DukascopyTransport` Protocol declares `-> Result[bytes]`, so a raising fake breaks the port's own contract) is real but does not rescue the code: the docstring itself says "Production wires an HTTPS client", i.e. the raising thing is downstream of the declared port and *inside* COMP-DUKASCOPY, and PLAN.md § 4 (QA-E06-L1-002, P0) pre-committed to exactly this fault matrix with real exception types. The test asserts the requirement; the code violates it. |
| **E6-F02** | R-007; CT-15; FR-018; Story-6.4-AC1 | **GENUINE VIOLATION** | Same root cause, verified at `calendar_feed.py:564` — `fetched = self._transport.fetch_snapshot(...)` is unguarded while `decode_calendar_snapshot` *does* catch its payload faults. The consequence stated in the row is correct and is the reason this one matters more than F01: `CalendarFeedImport.run` converts a **returned** refusal into the fail-closed data-quality journal + alarm (SCN-0008 / 6.4 AC4); a **raised** exception bypasses the fail-closed path entirely, so a transport-level outage produces no journal entry and no alarm. |
| **E6-F03** | R-007; CT-15; FR-015; Story-6.1-AC5 | **GENUINE, but redundant** | `ingest.py:445` is indeed unguarded. The row is honest about being "the transitive manifestation / a missing defense-in-depth guard", and `medium` is the right severity. It is one defect with F01/F02, not a third; keep it as a distinct row only because the remediation site differs. |
| **E6-F04** | FR-017; Story-6.3-AC5; L18 | **UNPROVEN — CORRECTLY RECORDED** | "Kept forever" is a CT-11/L18 durability property of `COMP-QMF-DATA-STORE` (Epic 3). Correctly narrowed, correctly filed with reason, and the surviving Epic-6 obligation (partition identity) is tested. One caveat: the partition test's other assertion, `window.provenance["acquisition"] == "download-once"`, is a self-declared marker (H3 class) and is not evidence of download-once behaviour. |
| **E6-F05** | R-007; FR-017; Story-6.3-AC3; L18 | **UNPROVEN — CORRECTLY RECORDED** | Verified: `DukascopyAdapter` builds no filesystem path from provider input; the symbol reaches `DukascopyHourKey.path_reference` as opaque text and the byte transport is injected. Filing the plan's path-traversal clause as UNPROVEN rather than faking a pass is exactly rule 5. Two nits: the row says "15 adversarial cases" where `_HOSTILE` has **14** (RESULTS.md line 55 says ×14, line 109 says 15 — reconcile), and the test node it cites is the good one while the *other* node in that family (H2) is the hollow one. |

**Rows that should exist and do not:** M1, M2, M3 (untested implemented clauses →
`observed=UNPROVEN`), M4 and M5 (silent narrowing → rule 5/6 require a row each). An empty
or short `findings.csv` is legitimate only when RESULTS.md shows every owned requirement
green under rules 1–5; five clauses are not green under those rules.

---

## 4. What the author got right (so the repair does not undo it)

- **The reds were not softened.** No assertion was weakened, no source was edited, and the
  failure was confirmed empirically before authoring. Given that tier-1 review found hollow
  greens elsewhere, this lane's handling of R-007 is the correct behaviour.
- **Fault realism is real** where it is claimed: `lzma.LZMAError`, `struct.error`,
  `UnicodeDecodeError`, `json.JSONDecodeError`, `ConnectionResetError`, `socket.timeout`,
  `BrokenPipeError`, `urllib.error.URLError` — the package's own normalized refusals are
  never substituted for the third-party type.
- **Control arms** are present on every property universal (L1-001, L1-004, L2-005, L2-012),
  which is the falsifiability construction rule 1 asks for.
- **Real sinks** are used where it counts: a real `EvidenceStore` + `JournalReader` for the
  CT-13 assertions, and a real store read-back of the *original* artifact in L4-001.
- **Node counts are honest.** I recounted every parametrization statically: L0 16, L1 41,
  L2 28, L3 12, L4 2 = 99; failures 7 + 7 + 1 = 15. Both match RESULTS.md.

---

## 5. Required repairs (ordered)

1. **Rewire `test_l3_001`** so the recording door / tattling store sits on a path the ingest
   object can actually reach; until then, downgrade AC1's "no governed write" claim in
   RESULTS.md from green to UNPROVEN and file it in `findings.csv`.
2. **Delete `test_l1_006_mapped_hostile_symbol_stays_opaque_data`** (H2); E6-F05 already
   carries that clause honestly.
3. **Add the missing assertions** for M1 (`bid_timestamp`/`ask_timestamp` survival) and M3
   (calendar event-time / foreign-timestamp provenance) — both are implemented, so both are
   testable today and should be green, not UNPROVEN. Add M2 (recorder WriterId identity).
4. **Replace the self-declared-literal assertions** in H3/H4 with behavioural ones, or mark
   Story 6.4 AC2's "no window / no permission" clause UNPROVEN.
5. **File UNPROVEN rows** for M4 and M5.
6. **Collapse the H6 duplicates** to the lower level and restate the green count.

*Nothing in this review authorizes a source edit. Every item above is a test-side or
record-side repair; E6-F01/F02/F03 remain open defects against the code.*
