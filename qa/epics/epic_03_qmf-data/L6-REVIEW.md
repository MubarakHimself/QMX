# L6 Requirements-Fidelity Review — Epic 3: qmf-data (evidence store & journals)

- **Reviewed artifacts:** `qa/epics/epic_03_qmf-data/PLAN.md`, `RESULTS.md`, `findings.csv`, and the eight files under `qa/tests/epic_03/` (80 pytest nodes).
- **Authorities used (precedence order):** `_bmad-output/planning-artifacts/epics.md` §Epic 3 (Stories 3.1–3.6, AC1–AC6) → `docs/contracts/ct-10/11/12/13/25/04` → `docs/lenses/testing/*`. `_bmad-output/test-artifacts/` **does not exist in this worktree** (confirmed), so the plan's reconstruction of the L0–L6 architecture and the P0/R-gate ids stands unreconciled; that caveat is carried forward, not resolved here.
- **Method:** one question per test — *does it assert what the requirement demands, or what the implementation happens to do?* No test was run or edited. Source was consulted only as citable evidence for a fidelity judgement (enum membership, guard signatures, exception-translation sites), never re-reviewed for quality.

---

## Verdict: **gaps**

The suite is well above average: it is requirement-traced, it asserts CT-04 *categories* rather than message strings, it enumerates real read paths where it matters (3.3-P2), and its refusal-first weighting matches the epic's irreversibility priority. It is not adequate as a requirements-fidelity proof, for four reasons:

1. The epic's headline assertion **P0-6** is proven against a *caller-declared read position* and a *label-parameterized predicate*, not against sealed rows at real read paths. Three passing assertions in the suite return sealed-period evidence and record that as correct.
2. The **R-007** fault matrix injects qmf-data's own already-normalized `StoreEngineError`; the half of the seam where a store-library exception would actually escape is never exercised.
3. One planned property (**3.6-P1 / FM-11**) was silently replaced by a different, weaker assertion, and `RESULTS.md` reports the substitute under the original requirement ids.
4. Roughly two dozen ratified requirement clauses across Stories 3.1–3.6 and CT-11/12/13 have no test and are not listed in PLAN Section 8 as blocked — so they are silently uncovered rather than knowingly deferred.

`findings.csv` holding zero rows is therefore not warranted. At least four rows are owed (Section 4).

---

## 1. Wrong-expectation and wrong-level tests

### W1 — CRITICAL: the seal is asserted against the caller's declared position, not against sealed rows

**Tests:** `test_3_4_u5_sealed_read_refused_never_silent_empty` (line 167), `test_acc_2_scn_0003_sealed_holdout_excluded_everywhere` step (e) (line 162), `test_3_4_i1_seal_survives_restore` (line 333).

**What they assert.** Each archives an artifact whose stored content lies **inside** the sealed window (`[{"t": 1_500_000, "px": 1}]` against a seal at `1_000_000`), then asserts:

```python
open_read = ws.append_store.read_raw(receipt.fingerprint, for_world=World.LIVE, at=500_000)
assert is_ok(open_read)          # 3.4-U5
assert is_ok(ws.append_store.read_raw(sealed_artifact.fingerprint, for_world=World.LIVE, at=100_000))   # ACC-2 (e)
```

That is: *sealed-period evidence is returned Ok because the caller declared an open position.* ACC-2 labels this "underlying evidence stays RETAINED".

**What the requirement says.** Story 3.4 AC4: "the **sealed rows** are refused with a `policy rejection` at every read boundary … and never returned as a silent empty result". CT-12 invariant: "The seal is enforced now as a policy-rejection refusal at every qmf-data read boundary (raw archive, processed, research door, and restored backups alike)". CT-11 invariant (line 25) repeats it. AC4's "all history is kept regardless" is a statement about **retention** — the bytes are never deleted — not a licence to read them back. The suite conflates the two: retention is proven by reading the sealed rows out, which is precisely the act AC4 forbids.

**Why this is a fidelity failure, not a style quibble.** The seal on `read_raw` / `read_view` / `BackupInput.read_room` consults only the caller-supplied `at`. A caller that under-states its position reads the sealed period. The implementation itself concedes the hazard where it *does* defend against it — `rooms.py:303-308` on `resolve_series`: the position is "**derived from the resolved evidence itself** … never a caller argument, so the seal cannot be bypassed by omitting a position nor by an under-stated window". No such derivation exists on the raw, processed, or backup paths, and no test probes for it; instead three tests assert the bypass as the expected happy path.

**Fair caveat.** The raw archive stores opaque rows, so the store may genuinely be unable to derive a content position — in which case this is a **specification** gap (CT-12 defines no rule for deriving a raw artifact's knowledge position) rather than a code defect. Either way it belongs in `findings.csv` as an escalation. Recording it as a pass is the error.

### W2 — HIGH: `3.4-P1`, the designated P0-6/R-012 property, quantifies over labels, not paths

**Test:** `test_3_4_p1_sealed_read_refused_at_every_boundary`.

**What it asserts.** It iterates `ReadBoundary` and calls `seal.guard(sealed_position, boundary=boundary)`.

**What the code does.** `seal.py:232-268` — `guard` does not branch on `boundary`. The decision is `self.is_sealed(position)`; `boundary` only decorates the refusal message and context. Iterating the four enum members runs the *same predicate four times with a different label*.

**What the requirement says.** AC4 / CT-12: refusal "at every read boundary". PLAN Section 5 states the reason this test exists: "'Refuses at **every** read path' … is a *quantifier over paths*, so it lives at L2 property (enumerate the paths) — a single L1 case cannot prove universality." PLAN Section 3 names the failure shape it must catch: "A sealed row returned through a *non-canonical* path (processed room, restored backup) while the research-door path correctly refuses." **This test cannot fail for that failure shape** — a read entry point that never calls the seal is invisible to it.

Real-path evidence does exist, but only as four single examples: raw (3.4-U5), processed (ACC-2 `read_view`), research door (ACC-2 `resolve_series`), restored backup (3.4-I1). Nothing asserts that `{b.value for b in ReadBoundary}` equals AC4's four named boundaries (so a boundary dropped from the enum would pass silently), and nothing asserts that every read entry point in the package — `read_raw`, `read_raw_self_guarded`, `read_view`, `BackupInput.read_room`, `resolve_series` — consults the seal. Contrast `3.3-P2`, which does this correctly by invoking five real read paths; that is the pattern 3.4-P1 should have followed.

### W3 — HIGH: R-007's fault matrix injects the package's own normalized error, never a store-library exception

**Tests:** `test_3_1_p2_no_engine_exception_escapes`, `test_3_1_u6_engine_faults_returned_as_storage_failure[write/read/view]`, `test_3_5_u6_unpersistable_blocks_stream`.

**What they assert.** Fake engines (`_RaisingColumnar`, `_RaisingAnalytics`, `_RaisingAppendStream`) raise `qmf.data.store.engines.StoreEngineError` — qmf-data's **own** already-translated error type — with `"disk full"` / `"locked"` / `"truncated"` / `"corrupt"` as message strings. The boundary is then shown to return a `storage failure`.

**What the requirement says.** Story 3.1 AC4: "the **store-library exception** is translated to a `storage failure` typed refusal at the boundary and is never propagated as an exception across a package seam". CT-11 invariant: "Store-library exceptions are translated to storage-failure typed refusals at the qmf-data boundary … storage-failure covers disk-full, corrupt files, and locked or truncated stores."

The store-library exceptions are `pa.ArrowException`, `duckdb.Error`, `sqlite3.Error`, and `OSError`. The real translation sites are `store/engines/parquet.py:87,113,129`, `store/engines/duckdb_views.py:50,74,113,143,161,181,195`, `store/engines/jsonl.py:169,189,212,264,298,368,435,484`, `store/engines/sqlite_meta.py:72,82`. **None is exercised by any test.** The suite proves the outer half (`StoreEngineError` → returned refusal) and skips the inner half — which is exactly where an escape would occur (an unwrapped library call, a fault class outside the `except` tuple). The named fault modes are simulated as strings, not produced: no test truncates, corrupts, locks, or fills a real store file, and no test drives a real engine at all.

This asserts the implementation's internal convention, not the requirement.

### W4 — HIGH: `3.6-P1` was substituted, and RESULTS reports the substitute under the original requirement ids

**Test:** `test_3_6_p1_event_class_total_and_stable`.

**Planned (PLAN Section 4):** "3.6-P1 (L2) — Property (**FM-11**): no write ever crosses role namespaces (writes stay role-scoped without exception). *(AC3)*"

**Delivered:** an assertion that `event_class_of` is total over the seven event types and partitions cleanly into risk-authored / venue-authored. Its own docstring waives the requirement: "FM-11's 'no write ever crosses roles' is upheld **by construction**: the logbooks module is read-only."

**What the requirement says.** Story 3.6 AC3: "only the two declared exceptions … may span roles, each carrying `role` on every row, and **no write ever crosses roles**". "Upheld by construction" is an argument, not evidence — and it is an argument about one module, while the writes that could cross roles are the store and journal writes (`AppendStore`, `JournalStore`, `RegistryRoom`), which the test never touches. `RESULTS.md` records this node under "CT-25 AC2/AC3, **FM-11**" as PASS, which overstates what was proven.

### W5 — MEDIUM: `3.1-U3` tests a presented-fingerprint mismatch, not a true collision; the "alarmed" half of AC2 is nowhere asserted

**Test:** `test_3_1_u3_true_collision_refused_and_original_unchanged`.

**What it asserts.** A caller presents a genuine fp1 alongside *different* bytes → `invalid input`, original unchanged.

**What the requirement says.** Story 3.1 AC2 / CT-11 invariant: "a true collision — the same hash with differing bytes — is refused **and alarmed**, never overwritten (DEC-0108)."

Two divergences. (a) A presented-fp mismatch is a different behaviour: the store computes fp1 from bytes, so differing bytes yield a *different* fp1 and are simply stored as a distinct artifact — which `3.1-P1` asserts as correct on the very next lines. The true-collision arm is unmanufacturable and is neither tested nor declared untestable in PLAN Section 8. (b) **The alarm is never asserted anywhere in the 80 nodes.** The concept exists in the implementation (`store/identity.py:13,126`, `store/append_store.py:12,82`, `store/registry_room.py:13,90`); the string "alarm" does not appear in any test file. Half of AC2's consequent is unproven.

### W6 — MEDIUM: `3.4-P2` never performs a re-derivation, and its key assertion cannot fail

**Test:** `test_3_4_p2_seal_boundary_frozen_new_derivation_mints_new_manifest`.

**What it asserts.** Two independently-constructed manifests over two different `CalendarIdentity` values have different `split_id`s; then `assert m_old.calendar_identity.tzdata_version == "2025a"` — an assertion on a frozen value object built two lines earlier from that same literal. It cannot fail unless the constructor mangles its input.

**What the requirement says.** AC5 / CT-12 invariant 4: "the seal boundary is a frozen TradingDate, never re-derived under a later tzdata version; re-derivation under a newer calendar rule-set or tzdata version mints a new manifest with its own fingerprint **and a lineage edge**, never a rewrite". No re-derivation operation is invoked, and the **lineage edge** — the element that makes the re-derivation auditable — is never asserted (PLAN 3.4-P2 named it explicitly). Also filed as a property but carries no `hypothesis` quantifier.

### W7 — MEDIUM: `3.3-P1` quantifies over receipt attributes, not over deletion paths

**Test:** `test_3_3_p1_no_deletion_path_removes_evidence_or_cited`.

It constructs `StoreReceipt` objects directly and checks `RetentionPolicy.verdict_for` / `may_delete` across `(role, is_evidence, cited)`. PLAN 3.3-P1 is "no **reachable deletion path** removes a raw original or a cited artifact"; Story 3.3 AC3 is about what may actually be erased. The only physical removal in the package (`store/engines/duckdb_views.py:174 drop`, `store/engines/__init__.py:152`) is never shown to be gated by a retention verdict. The test proves the policy object answers correctly; it does not prove the policy is on the path.

### W8 — LOW: `3.2-C1`'s exclusion assertion is vacuous, and the ordering-key rule is asserted backwards

**Test:** `test_3_2_c1_identity_is_fp1_not_ordering_key`.

`assert a.to_row() == H.unwrap(H.observation(sequence=0)).to_row()`, annotated "the receive-monotonic diagnostic is excluded from identity" — but both observations are built from identical defaults (`receive_wall_time=2_500`), so nothing varies and nothing about exclusion is shown; the assertion proves construction determinism only. The first half (different `sequence` ⇒ different fp1) shows the ordering key is *inside* the fingerprint, which is not what CT-10 / DEC-0108 demand: the force of "`(instant, writer, sequence)` is an ordering key, never identity" is that no lookup, dedup, or join path may key on it. That is untested.

### W9 — LOW: `3.3-P2` is a fixed example in a property's clothing, and the enumeration is short by two real read paths

`@given(other=st.sampled_from([World.REPLAY]))` is a one-element strategy. More materially, the five enumerated paths omit two public read entry points that exist in the package: `SourceObservationBoundary.read` (`source_boundary.py:112`) — the CT-10 read that **Story 3.2 AC5 names explicitly** — and `BackupInput.read_room` (`store/backup_input.py:97`). "Every enumerated read path" is enumerated short of the paths that exist. (The test is otherwise the best-constructed property in the suite and is the model W2 should have followed.)

### W10 — LOW: refusal categories pinned to an unratified mapping

`test_3_3_u1_seven_roles_instantiated_per_world` and `test_3_1_c2_read_requires_declared_world_and_missing_is_stale` assert `stale evidence` for a well-formed key naming no artifact, citing "M4/M5". `stale evidence` is a ratified CT-04 category, but no ratified source assigns *artifact-absent ⇒ stale evidence*: the M4/M5 ids appear nowhere in `docs/contracts/ct-11-evidence-persistence.yaml`. The behaviour asserted is reasonable; the *category* is the implementation's choice, not a requirement's. Low severity — over-specification, not a wrong expectation.

---

## 2. Requirements from epics.md §Epic 3 with no test coverage

Not listed in PLAN Section 8 as blocked, so these are silent gaps rather than knowing deferrals.

### Story 3.1 (FR-016 / CT-11)
| Requirement | Source | Status |
|---|---|---|
| "append-with-**fsync**" | AC3 | No durability assertion. Implemented at `jsonl.py:263,479,483`; untested. |
| "size rotation under a **monotonic ordinal**" | AC3 | 3.1-I1 asserts ≥2 files + full recovery; ordinal monotonicity never asserted. |
| "refused **and alarmed**" | AC2 | See W5 — no test references the alarm. |
| "each engine stays behind its owned contract so it is **swappable**" | AC1 | Only implicit (fault fakes). No test swaps an engine and shows equivalent behaviour. |
| Format-version / migration law: "preflight checks → backup first → dry-run → migrate → verify … never in-place mutation of the only copy" | CT-11 inv. 8 (DEC-0103, DEC-0118) | Zero coverage. 3.1-C1 asserts only `format_version == 1`. Arguably Epic 5's, but CT-11 is Epic-3-owned and it is not in Section 8. |

### Story 3.2 (FR-010 / CT-10)
| Requirement | Source | Status |
|---|---|---|
| **AC5 cross-world observation read** — "a read requests observations from a different world than the caller's … is a `policy rejection`" | AC5 | **Entirely uncovered.** 3.2-U4, 3.2-P2 and ACC-1 all read same-world; 3.3-P2's enumeration omits `SourceObservationBoundary.read`. Only the simulated-write half (3.3-U2) is proven. |
| "conversions to framework Time and Money are **derived values carrying lineage**, never silent rewrites or rescales" | AC2 (DEC-0105/0106) | Verbatim storage proven; the derived-value-with-lineage half never exercised. |
| "(instant, writer, sequence) is an ordering key, never identity" as a *use* rule | CT-10 / DEC-0108 | See W8. |

### Story 3.3 (FR-011 / CT-11)
| Requirement | Source | Status |
|---|---|---|
| "**a rebuild** pins the original calendar identity and tzdata version" | AC2 / CT-11 inv. 3 | 3.3-U3 asserts pins are recorded at materialize time; no rebuild is ever performed. |
| "no reachable deletion path" | AC3 | See W7. |

### Story 3.4 (FR-012 / CT-12)
| Requirement | Source | Status |
|---|---|---|
| Widths "**default to the maximum declared warm-up-plus-confirmation-delay bound across every producer the split cites**" | AC2 / CT-12 inv. 9 (DEC-0131) | Untested. Every fixture passes explicit widths with `cited_producers=()`; only the over-horizon *refusal* (3.4-P3) is proven, never the defaulting rule. |
| Indicator knowledge time — "the knowable-at of the **last contributing input** for indicator results" | AC3 / CT-12 inv. 10 | Only `KnowledgeKind.STRUCTURE` is exercised. `KnowledgeKind.INDICATOR` (`splits.py:110-118`) appears in no test. |
| Re-derivation mints a **lineage edge** | AC5 / CT-12 inv. 4 | See W6. |
| "Split manifests are instantiated per world; a read that crosses worlds is a policy-rejection refusal" | CT-12 inv. 11 | No cross-world manifest test at all. |
| "Every manifest stamps its integer contract format version" | CT-12 inv. 13 | 3.4-C1 asserts roles, ordering and calendar; never the format version. |
| Sealed window = `registry:historical_holdout_months` (~12mo) | AC4 / CT-12 units | `holdout_months=12` is a hardcoded helper default; nothing ties it to the registry key, contra PLAN §7 ("membership computed from the manifest, not hardcoded"). |

### Story 3.5 (FR-013 / CT-13)
| Requirement | Source | Status |
|---|---|---|
| "optional **`display_time`** excluded from identity" | AC4 | Untested — only `correlation_id` is exercised (3.5-U5, 3.5-P2), though `display_time` exists (`journal.py:343`, `render_display_time`). |
| "journals store int64 UTC ns + writer + sequence, while logs render UTC **ISO-8601 with an explicit Z**" | AC4 / CT-13 inv. 1 | The evidence-vs-display encoding distinction is never asserted. |
| "…and **is journaled on recovery**" | AC5 / CT-13 inv. 16 | 3.5-I1 proves the retry unblocks and replays `[0, 1]`; it never asserts the failure/recovery is itself journaled. |
| Control action carries a declared "**suppressed**" subtype for an authorized action discarded at arbitration | CT-13 inv. 4 (DEC-0150/0158) | Untested. |
| "The promotion event carries **only** the promotion-card fp1 + correlation_id; the journal never holds a second promotion schema" | CT-13 inv. 9 (DEC-0116) | Untested. |
| "`correlation_id` … **propagates across every package boundary**" | AC4 / CT-13 inv. 7 | Only its exclusion from fp1 is tested; propagation is not. |
| "a read **or write** that crosses worlds is a policy rejection" (journal) | CT-13 inv. 17 | Cross-world journal *read* covered (3.3-P2); cross-world journal *write* is not. |
| "unlimited readers" | AC1 | Untested (only the one-writer refusal). |

### Story 3.6 (FR-013 / CT-13, CT-25)
| Requirement | Source | Status |
|---|---|---|
| "**no write ever crosses roles**" | AC3 / FM-11 | See W4 — planned property substituted; no write path exercised. |
| "risk-authored events carry the **Book-definition fingerprint**" | AC2 / CT-13 inv. 5 | Fixtures carry `book_instance_id`/`bms_instance_id`/`venue_id`/`account_id`/`role`; the Book-*definition* fingerprint field is never asserted. |
| "where one bot is concerned, the **CT-33 Bot definition fp1 plus its AD-41 seat binding**" | AC2 (DEC-0173) | Untested — and DEC-0173 explicitly ruled this field out of pending status, so it is not a blocked spec. |
| Binding identity includes `world` | AC2 | `BindingIdentity` assertions check `book_instance_id` only. |
| "**BMS journal** and **per-bot journal**" | AC1 | Only the Book projection is exercised; `entity_journal` appears once, for an input-guard refusal. |

### Cross-cutting
| Requirement | Source | Status |
|---|---|---|
| Exit criterion 2 — "`cycle.py` and `verify.py` raised to ≥80% line and their refusal branches covered, **or each residual partial recorded as a finding with the missing branch named**" | PLAN §8 | **Unmet and unrecorded.** `RESULTS.md` asserts the probes "drive" those branches but reports no coverage measurement, and concedes they are the Epic-5 backup/verify modules. Neither arm of the criterion was satisfied. |

**Correctly excluded (agreed).** PLAN §8's U-A (CT-08 gate, GAP-0016/0017), U-B (CT-25 risk runtime, defined-unwired), U-C (numeric backup RPO/RTO), U-D (BarSpec arithmetic), U-E (journal trim numerics) are genuinely blocked specs, are named with their GAP/DEC ids, and no test converts any of them into a pass. That discipline held.

---

## 3. What holds up

Credit where due — these assert the requirement, not the implementation:

- **3.3-P2** — five *real* read paths invoked, leaks collected and reported by name. The correct shape for a path quantifier.
- **3.3-U2 (P0-7)** — both arms: the simulated world's rooms cannot be requested *and* an admission is refused.
- **3.2-P2 / 3.2-U4 / ACC-1** — evidence integrity across a correction chain, asserting the original's **row equality**, not merely its presence.
- **3.2-P3** — a genuine two-arm fuzz: any `Ok` must be fully formed on every required field, else a typed refusal. Cannot be satisfied by an admitted-incomplete record.
- **3.5-U1** — the seven event types asserted against the requirement's literal names, as a closed set.
- **3.5-U4** — `veto_ledger` selects on `outcome`, with a negative case (a decision lacking its refusing-door reference) proving it is not key-presence selection. Exactly DEC-0158.
- **3.5-U6** — asserts the event is *retained* and the sequence *not advanced*, not merely that a refusal came back.
- **3.4-U7 / ACC-2 (d)** — the one final look journaled as the named control-action subtype, second refused.
- **3.4-U3 / 3.4-P3** — widths in the fingerprint, `split_id` re-derived and compared, over-horizon producer refused.
- **G1** — a real AST scan of every module, default-deny, offenders reported by name.
- **The refusal harness** — CT-04 `category` throughout, never a parsed message. Plan §7's rule, honoured without exception across all 80 nodes.

---

## 4. `findings.csv` adjudication

**The file contains a header row and zero data rows.** There is therefore nothing to adjudicate: **0 genuine requirement violations recorded, 0 wrong test expectations recorded.**

The empty set is itself the finding. `RESULTS.md` states "The `qmf-data` implementation faithfully meets the five FRs and the CT-10/11/12/13 contracts **as written**" — a claim the evidence does not support, because the assertions that would have tested the contested clauses were either not written (Section 2) or written at a level that cannot fail (W1–W4).

Four rows are owed:

| # | Requirement ids | Severity | Description | Kind |
|---|---|---|---|---|
| 1 | FR-012 / CT-12 AC4 / CT-11 inv. 25 / P0-6 / R-012 | **high** | The seal on `read_raw`, `read_view` and `BackupInput.read_room` is enforced against the **caller-declared** `at` only; a caller declaring an open position reads sealed-period content. `resolve_series` derives its position from the evidence *precisely because* a caller-supplied position is bypassable (`rooms.py:303-308`); the other three paths do not. Expected: sealed rows refused at every read boundary. Observed: `is_ok` at `at=500_000` for an artifact whose rows sit at `t=1_500_000` (`test_3_4_u5` line 167, `test_acc_2` line 162). | Requirement violation **or** spec gap — CT-12 defines no derivation rule for a raw artifact's knowledge position. Escalate; do not close as a pass. |
| 2 | FR-016 / CT-11 AC4 / R-007 | **medium** | No test drives a real store-library exception (`pa.ArrowException`, `duckdb.Error`, `sqlite3.Error`, `OSError`) through the translation sites; only qmf-data's own `StoreEngineError` is injected. The named fault modes (disk-full, locked, truncated, corrupt) are simulated as message strings. R-007's gate is unproven on the half of the seam where an escape would occur. | Coverage gap in the verification, not (yet) a code defect. |
| 3 | FR-016 / CT-11 AC2 (DEC-0108) | **low** | The "**and alarmed**" half of the true-collision requirement has no assertion anywhere in the suite, and the true-collision arm itself is neither tested nor declared untestable in PLAN §8. | Coverage gap. |
| 4 | PLAN §8 exit criterion 2 | **low** | `cycle.py` / `verify.py` were neither measured to ≥80% line nor had their residual partial branches recorded as findings with the missing branch named. Neither arm of the exit criterion was satisfied; `RESULTS.md` asserts the outcome without a coverage artifact. | Process gap. |

---

## 5. Recommended remediation (verification only — no source edits)

1. **Rewrite 3.4-P1 as a path quantifier.** Follow 3.3-P2: build one seal-wired store, then invoke every real read entry point (`read_raw`, `read_raw_self_guarded`, `read_view`, `resolve_series`, `BackupInput.read_room`) at a sealed position and collect leaks by name. Add an assertion that `{b.value for b in ReadBoundary}` equals AC4's four named boundaries, so a dropped boundary cannot pass silently.
2. **Add the content-position probe** that produces finding #1: archive sealed-period rows, read at an under-stated position, record the result as a finding either way.
3. **Fault a real engine.** Truncate a rotated `.jsonl`, corrupt a Parquet file, make a directory read-only, and assert the boundary returns `storage failure` with no library exception crossing the seam — closing R-007's inner half.
4. **Restore the planned 3.6-P1** (FM-11: no write crosses role namespaces) against the actual write paths, and correct the `RESULTS.md` row that reports the substitute under FM-11.
5. **Cover Story 3.2 AC5** — a cross-world `SourceObservationBoundary.read` — and add that path plus `BackupInput.read_room` to 3.3-P2's enumeration.
6. Add assertions for the Section 2 clauses, or move each into PLAN §8 with a named GAP/DEC reason. Silence is the problem; a declared block is not.
