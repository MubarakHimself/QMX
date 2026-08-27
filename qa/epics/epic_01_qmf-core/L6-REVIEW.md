# Epic 1 — qmf-core — L6 requirements-fidelity review

**Scope of this pass.** One question per test: *does it assert what the requirement demands
(citable to an FR/AR/CT/SCN/DEC id), or what the implementation happens to do?* Plus: which
requirements in this epic's section of `_bmad-output/planning-artifacts/epics.md` (Stories
1.1–1.9, lines 430–737) have **no** test at all. Tests were not run and not edited; the source
was not re-reviewed. Four targeted `grep`s were used only to decide whether a narrowed test
hides a defect or merely leaves a requirement untested — those greps are cited inline.

**Authorities used, in precedence order:** epics.md Epic 1 (Stories 1.1–1.9) → `docs/contracts/`
CT-01..CT-05 (all `status: ratified`) → `docs/components/qmf-core.md` FM-1..FM-9 →
`docs/constitution.md` → `docs/lenses/testing/test-strategy.md`. The two authorities named in the
lane brief (`test-design-qa.md`, `test-design/QMX-handoff.md`) are absent from the worktree; the
PLAN's process finding on that is confirmed and stands.

---

## Verdict: **gaps**

86 tests, 85 pass, 1 fails. The suite is genuinely strong on the CT-01/CT-02/CT-04 value laws —
the ◆ mutmut pins are exact-value assertions, not presence checks, and the closed vocabularies
(seven categories, three retryabilities, five account roles, ten unit-kinds, three worlds) are
transcribed from the contracts rather than read back off the enums. **72 of 86 tests assert the
requirement.** The verdict is `gaps`, not `adequate`, for four reasons:

1. **One test was narrowed to fit the implementation and, in narrowing, hid a second requirement
   violation** — E1-C11 excludes CT-03 artifacts from the format-version stamp. CT-03's ratified
   invariant demands that stamp; the code does not implement it. `findings.csv` should carry two
   rows, not one.
2. **A P0 risk row this epic owns (R-002, "no public callable raises across the boundary") is
   verified over only the `try_create` factory surface** — no instance method is driven. And the
   one public core callable that *does* raise (`DataDrivenClock.wall_now`) is excluded from the
   property while a separate unit test (E1-U41) pins its raise, and its exact prose, as correct.
3. **Stories 1.7 and 1.8 have zero tests** — eight acceptance criteria, the whole of NFR-02, the
   mechanical enforcement of FR-001 and FR-002. Disclosed as out-of-ask, but uncovered.
4. **Story 1.1's scaffold/toolchain/register requirements are almost entirely uncovered** and are
   statically checkable today (workspace membership, no `qmf/__init__.py`, tool pins, uv.lock,
   DEPENDENCIES.md licence policy, SemVer lockstep, failure register, benchmark slots).

Nothing in the suite weakens an assertion to make source pass, no source was edited, and the one
failure is correctly recorded as a finding rather than chased away. The gaps are of omission and
of over-fitting, not of integrity.

---

## 1. Wrong-expectation tests

Ordered by how much the wrong expectation costs. Each entry: what the test asserts → what the
requirement actually says.

### 1.1 Material — the expectation is wrong enough to hide or invert a requirement

**E1-C11 — `test_e1_c11_every_serialized_artifact_stamps_format_version_1`** (`test_l2_contract.py:229`)
*Asserts:* `format_version == 1` on ten CT-01/CT-02/CT-05 artifacts, and excludes CT-03 by
docstring: *"CT-03 core nouns carry their stamp via the qmf-registry record — Epic 2 — and when
embedded in a CT-01/CT-05 artifact that stamps it."*
*The requirement:* CT-03 invariant (`ct-03-instrument-identity.yaml:22`), verbatim — **"Every
serialized identity artifact stamps this contract's integer format version, whose meaning never
mutates — an incompatible change mints the next version (DEC-0103)."** CT-03 also carries
`version: 1` in its own header. DEC-0103 is versioning-from-birth; the PLAN's own E1-C11 line
reads "Every serialized **CT-01..CT-05** artifact stamps integer format version = 1".
*Why it is wrong:* the exclusion is not requirement-backed — it is a rationalisation of what the
code does. Evidence: `grep -n "fp1_identity|format_version|CONTRACT_FORMAT_VERSION"
packages/qmf-core/src/qmf/core/identity.py` returns **zero matches**; `chrono.py` defines 5
`fp1_identity` methods, `exact.py` 6, `fingerprint.py` 2, `identity.py` **0**. CT-03 identity
values therefore carry neither a contract format version nor an identity projection. Deferring
the stamp to a qmf-registry *record* also contradicts CT-05's DEC-0138 invariant that consumers
cite the **content** fingerprint, "never the wrapping registry record's fingerprint".
*Consequence:* this is a **missing findings.csv row** (see §3), not a scope note.

**E1-U41 — `test_e1_u41_data_driven_clock_exhaustion_boundary_exact_message`** (`test_ct02_chrono.py:208`)
*Asserts:* `pytest.raises(LookupError)` and `str(exc.value) == "data-driven clock exhausted its
scripted wall instants"` (and the monotonic twin).
*The requirement:* CT-04 invariant (`ct-04-typed-refusal.yaml:16,18`) — **"Every public QMF
operation either succeeds or returns a typed refusal"**; **"Refusals are RETURNED across public
boundaries as one arm of a result union; exceptions are reserved for programmer error."**
epics.md Story 1.2 says the same. CT-02 (`:32`) makes `Clock` a **core-defined public protocol
seam** whose replay implementation is data-driven — so `wall_now()` is a public callable of the
core boundary, and running past the end of a replay script is a *data* condition in replay, not a
wrong-type/wrong-arity programmer error.
*Why it is wrong:* the test encodes the implementation's raise as the expected behaviour. Under
the requirement, exhaustion is at minimum arguable as `unavailable dependency` / `stale evidence`
via a returned `TypedRefusal`; the test forecloses the question instead of recording it. It also
pins two exact English message strings that PLAN §5 itself declares **not ratified surface**
("message wording is not ratified surface … recorded as accepted rather than chased with brittle
asserts") — the test does exactly what the plan said it would not do.
*What the test should have done:* assert the boundary (`>= len(script)`, not `> len`) and record
the raise-vs-refuse question as a finding for operator ruling.

**E1-A02 — `test_e1_a02_cross_producer_fp1_determinism_and_new_derivation_mints_new_id`** (`test_l4_acceptance.py:69`)
*Asserts:* `_fp(value) == _fp(value)` — the same function, called twice, in one interpreter,
labelled "two independent conformant producers … an independent recomputation".
*The requirement:* CT-05 purpose — identity "computed by one qmf-core implementation so **two
conformant producers and merging sandboxes always agree on identity**"; PLAN E1-A02 promised
"byte-identical fp1 over a **golden** artifact set".
*Why it is wrong:* calling a pure function twice tests referential transparency, not producer
agreement and not recipe stability. There is **no frozen golden digest anywhere in the suite** —
no test would fail if the canonicalisation recipe changed tomorrow (sort order, NFC, separators,
scale normalisation), because every expectation is recomputed from the same code. That is the
single thing a "replay reproducibility is a platform property" acceptance test exists to catch.
*Also:* line 84, `assert Fingerprint.try_create(producer_a)` is a **dead assertion** — both `Ok`
and `TypedRefusal` are truthy dataclass instances, so it passes unconditionally. It should be
`assert is_ok(...)`.

**E1-P02 — `test_e1_p02_mixed_scale_same_currency_is_exact_never_silent_round`** (`test_properties.py:127`)
*Asserts:* for every generated same-currency scale pair, `is_ok(total)` — i.e. mixed-scale
addition **always succeeds**.
*The requirement:* CT-01 invariant (`ct-01-money-quantity.yaml:14`) — "Mixed-scale arithmetic on
the same currency or unit **auto-promotes losslessly to the finer scale OR returns a typed
refusal**"; epics.md Story 1.4 states the same two arms; PLAN §6 promised the property would prove
"the set `{value, refusal}` is **total and disjoint**".
*Why it is wrong:* with scales drawn from 0..12 and promotion to `max(s1,s2)`, the non-promotable
arm is unreachable by construction, so the property asserts the implementation's totality on a
generator that can only produce the success arm. The refusal arm of FM-4 is exercised nowhere for
addition/subtraction (E1-U21 reaches it through `PriceDelta.to_money` at an explicit target scale,
a different code path). A generator that reaches `MAX_SCALE` or the int64 magnitude ceiling would
be the requirement-faithful version.

**E1-U53 — `test_e1_u53_result_label_identity_parts_occurrence_outside_identity`** (`test_ct05_fingerprint.py:130`)
*Asserts:* `label.computation_identity.value == _fp(label)` — a specific derivation function.
*The requirement:* CT-05 (`:25`, `:56`) — "**Computation identity is content-derived from the label
parts so identical work from two sandboxes deduplicates and merges**; the occurrence record …
is separate provenance outside identity."
*Why it is wrong:* the contract pins the *property* (dedup across sandboxes; occurrence excluded),
not the *function*. The test pins the function and never tests the property: no test builds two
labels with identical parts and different occurrence records and asserts their computation
identities are equal. `assert not hasattr(OccurrenceRecord, "fp1_identity")` is a name-absence
proxy for "outside identity", not a demonstration of it.

### 1.2 Over-fit — the requirement half is present, but an implementation detail rides along

| Test | Asserts (implementation) | Requirement actually says |
|---|---|---|
| **E1-U52** (`test_ct05_fingerprint.py:115`) | collision `category is POLICY_REJECTION`; `context["alarm"] is True` | CT-05 `:23`: a true collision is "**refused and alarmed**" — **no category is pinned**. PLAN §8(5) sets the discipline explicitly ("must not over-fit a category the spine leaves open") and E1-U34 honours it for FM-3; E1-U52 breaks it. The `"alarm"` key name is implementation naming. |
| **E1-U55** (`:158`) | `replay_ns == "replay"` | CT-05 `:27`: "A non-live world may never write into the live evidence namespace; world separation is delivered by **storage separation**". The requirement is `≠ live` (asserted on the line above) — the literal namespace string is the implementation's choice. |
| **E1-U25** (`test_ct01_exact.py:206`) | `context["given"] == repr(-1)` — the offending scale as a **repr string** | CT-04 `:38`: context is "structured, **machine-readable** diagnostic facts". A repr-stringified integer is the implementation's encoding; `context["given"] == -1` would be the machine-readable reading. Pinning the repr locks in the weaker form. |
| **E1-U27** (`:229`) | `set(context["allowed"]) == {m.value for m in RoundingMode}` | CT-01 `enums.rounding_mode` (`:44`): "the enumerated member set is **not pinned in the foundation spine**". The assertion compares the implementation to itself — tautological, and there is no requirement to compare against. The requirement half that matters (a missing rounding mode refuses, listing what is allowed) *is* asserted. |
| **E1-U36** (`test_ct02_chrono.py:142`) | `"tie-break" in context["reason"]`; `context["instant"] == 42`; `context["field"] == "earlier"` | CT-02/DEC-0106 pin that `(instant, writer, sequence)` carries **no causal meaning**, so equal instants are concurrent. The prose "tie-break" and the key names `instant`/`earlier` are implementation surface. Defensible as a mutmut pin, but it is implementation-shaped and PLAN §5 disclaims message wording. |
| **E1-U59** (`test_seams.py:73`) | `getattr(proto, "_is_protocol", False) is True` (a private CPython attribute) | epics.md Story 1.9 / AD-15 / DEC-0138: the seams are `typing.Protocol` **and** "**qmf-core itself performs no I/O and spawns no work**". The Protocol half is proved; the no-I/O half is asserted by docstring only — no static check that qmf-core's source is free of `open`/`socket`/`threading`/`asyncio`/`subprocess`/file writes. |
| **E1-U35 / U39 / U45** | `not hasattr(X, "from_instant")` / `not hasattr(X, "fp1_identity")` as proof of "never derived from an instant" / "excluded from identity" | The requirements are behavioural (CT-02 `:39`, CT-05 `:21`). Name-absence is weak: `identity.py` defines **no** `fp1_identity` on any type, so the same assertion would pass for a type that *should* be identity-bearing. E1-U62 shows the right shape — `is_refusal(fingerprint(ref))`. |

### 1.3 Disclosed proxies — honestly labelled, but the named requirement is not the one tested

These are recorded in PLAN §8 / RESULTS and are not deceptive; they are listed because the
requirement they carry an ID for remains unverified.

- **E1-I01** — the AC is "**an undeclared import fails the isolated build**" (AR-06/AR-18). The
  test asserts `"dependencies = []" in pyproject` plus a stdlib-only import scan. A package whose
  build is broken in isolation for any other reason passes.
- **E1-I04** — the AC is that `ruff check .`, `mypy adws`, `pytest -q adws/tests` **still pass**.
  The test asserts three substrings in the root `pyproject.toml` and that `adws/tests` contains
  files. The gate-never-RED clause is untested.
- **E1-C12** — the PLAN's C12 was "isolated per-package environment, owner **and** consumer"
  (DEC-0100/0102). The test asserts 16 names are in `qmf.core.__all__`. No isolation, no consumer.
- **E1-I03's detector** (the one that produced the finding) requires **both** `hashlib.sha256(` /
  `.hexdigest()` **and** a literal `f"fp1:sha256:` in the same file, and skips any path containing
  `tests/` or `/examples/`. A package that builds the string by concatenation, via `str.format`,
  through a helper, or that hashes canonical bytes and hands them to `Fingerprint.try_create`, is
  invisible. The requirement is "**no other package computes a fingerprint except by calling
  it**". The two offenders found are real; the true count may be higher.

---

## 2. Missed requirements — in this epic's section of epics.md, no test covers

Grouped by story. "Statically checkable now" means the requirement could be asserted in this lane
today, without the tier-2/CI harness.

### Story 1.1 (AR-01..AR-11, NFR-04, NFR-11) — the largest uncovered block

| # | Requirement (epics.md line) | Status |
|---|---|---|
| M1 | Workspace members are `packages/*` (the seven roster packages) **and** `extensions/*` (qmf-calendar-forex); each in `src/qmf/<name>/` layout; PEP 420 implicit namespace; **no distribution anywhere contains `qmf/__init__.py`** (444–445; AR-01/02/03) | No test. Statically checkable now — the `qmf/__init__.py` prohibition especially. |
| M2 | Every package declares every dependency (siblings included) in its own pyproject; `uv_build` backend; CPython 3.14 pinned; **one committed workspace-root `uv.lock`**; numpy 2.5.2 / pandas 3.0.5 / pyarrow 25.0.1 appear only in outer packages (449–450; AR-03/04/05) | No test. Only `qmf-core: dependencies = []` is checked (E1-I01). Statically checkable now. |
| M3 | An undeclared import **fails the isolated build** (455; AR-06/AR-18) | Proxy only (E1-I01). |
| M4 | `poe fmt \| lint \| types \| test \| check \| check-integration \| check-release` invoke ruff **0.16.3**, pyright **1.1.411 strict workspace-wide**, pytest **9.x**, poethepoet **0.48.0**, byte-identical across machines; **secret-scan gate inside `poe check` at Tier 1** (458–460; AR-11/23/24) | No test. The pinned versions are statically checkable now. |
| M5 | `DEPENDENCIES.md` register: every dependency listed with **name, licence, and why**; MIT/BSD/Apache/PSF allowed, GPL/AGPL + strategy-family + platform-imposing rejected, LGPL only unmodified and separately installed; the seven roster packages version in **SemVer lockstep**; qmf-calendar-forex rides its own ladder with tzdata pinned (467–470; AR-07/09/02) | No test. `DEPENDENCIES.md` exists at the root (verified by `ls`) but nothing asserts its shape, the licence policy, or version lockstep. Statically checkable now. |
| M6 | **NFR-11 failure register** alongside tests for every designed failure mode: failure class, detection, auto-recovery/retry semantics, visible degraded state, notification tier, product-user affordance — "a tier-1 artifact obligation on every subsequent story" (472–475) | No test. `conventions/failure-register.md` and `packages/qmf-core/FAILURES.md` exist (verified by `find`); their six required elements are unverified. PLAN §1 lists NFR-11 in scope. Statically checkable now. |
| M7 | AD-13 benchmark-harness slot in **each roster package's** scaffold: speed **and peak memory** at a package-native load ladder, with unit-test status; first measurements become fingerprinted (OS, CPU-class)-scoped baselines (477–480; NFR-04/AR-22) | Only the import-time budget (E1-S07) is tested. The per-package slot, the memory axis, and the baseline-fingerprinting convention are untested. Slot existence is statically checkable now. |

### Stories 1.7 and 1.8 — **entirely uncovered (8 ACs, 0 tests)**

| # | Requirement | Status |
|---|---|---|
| M8 | Money-path float scanner: must-flag any binary float reaching a money-path value (661); must-**not**-flag a sanctioned named-boundary crossing (664–667); wired into `poe check` with a **nonzero exit** on a flagged violation (669–672); ships its own must-flag/must-not-flag fixtures at the coverage floor (674–677) | Zero tests. Planned as E1-S01/S02/S05, run in neither this lane nor any lane this pass. |
| M9 | Ambient-nondeterminism scanner: must-flag `datetime.now` / `time.time` / `time.monotonic` / unseeded `random` below the composition root (687–690); must-**not**-flag injected `Clock` usage (692–695); wired into `poe check` with nonzero exit (697–699); own fixtures at the coverage floor (701–704) | Zero tests. Planned as E1-S03/S04/S05. |

These two stories are NFR-02 — the mechanism that makes FR-001 and FR-002 *mechanically*
enforceable "rather than review-dependent". RESULTS declares them "not part of the L1–L4 ask" and
"Not run this pass". That is a disclosed scope choice, not a defect in the tests written — but as
of this pass the epic's two enforcement stories carry no verification at all.

### Recurring across Stories 1.2–1.6 and 1.9

| # | Requirement | Status |
|---|---|---|
| M10 | AR-19/AR-21: an **executable contract test owned by qmf-core** plus **reference-usage examples** ship as tier-1 artifacts, for CT-01..CT-05 and the seam modules (507, 538, 575, 612, 649, 736) | No test asserts their existence or execution. `packages/qmf-core/examples/` and seven `tests/test_*_examples.py` files exist (verified by `ls`/`find`); this lane never checks them. PLAN exit criterion (h) unverified. Statically checkable now. |
| M11 | AR-20 coverage floors: **100% branch** on `exact.py` and `chrono.py`, **80%** on every other module (574, 611, 508, 538, 649, 736; DEC-0101) | Never measured. RESULTS reports pass/fail only. PLAN exit criterion (b) is unverified — and mutation adequacy (§5) was framed as the *backstop* to coverage, not its replacement. |

### Story 1.3 (CT-03)

| # | Requirement | Status |
|---|---|---|
| M12 | Venue and Account nouns are **defined only in qmf-core** (records/lifecycle owned by qmf-registry, never by an edge module); **Books bind to accounts, never to venues** (525; AR-08) | No test. The "defined only in qmf-core" half is statically checkable now. |
| M13 | CT-03 `:22` — every serialized identity artifact stamps the contract's integer format version | **Not covered, and violated** — see §1.1 E1-C11 and §3. |

### Story 1.4 (CT-01)

| # | Requirement | Status |
|---|---|---|
| M14 | The pinned canonical **form** itself (569; DEC-0158, CT-01 `:20`): exact rationals **reduced to lowest terms**, **denominator strictly positive**, **sign carried on the numerator**, **serialized as a two-key object with both keys always present**, plus the declared canonical storage scale per value class | Only the *consequence* is tested (E1-P05: equal value ⇒ equal fp1). Nothing inspects the form — e.g. that `ExactRational(1, -2)` canonicalises to numerator `-1` / denominator `2`, or that both keys are always emitted. A form regression that preserved equality would pass every test in the suite. |
| M15 | The money path is a **taint, not a location**: any value transitively contributing to an order quantity, price, P&L, or balance (CT-01 `:15`) | Cross-seam taint is deferred by PLAN §8(2) (accepted). But no test in this lane drives a *derived* value through arithmetic and asserts float cannot enter — E1-U18/U19 test direct construction only. |
| M16 | DEC-0141 venue-boundary decode: per-value-class pinned target scales, identity-bearing rounding mode, raw float retained only as integrity-checked provenance and **never the value a consumer reads** (CT-01 `:18`) | Untested. Mostly Epic 8 surface, but CT-01-owned and named in Story 1.4's citations. |

### Story 1.5 (CT-02)

| # | Requirement | Status |
|---|---|---|
| M17 | **qmf-core embeds no market-hours calendar rule set** (601–602; CT-02 `:46`) | No test. Statically checkable now. |
| M18 | Nothing below the composition root reads the system clock (596–598; AR-16) | Deferred to the L0 ambient scanner, which was not run. Not even the narrow form — that qmf-core's own source is free of `datetime.now`/`time.time`/`time.monotonic` — is asserted. Statically checkable now. |
| M19 | Duration's **operation restriction** (CT-02 `:27`): a duration used for latency/timeout/cooldown/cadence must be measured monotonically; a duration derived from two wall instants is an **evidence span, never an elapsed-time measurement** | Untested. E1-U37 tests the value type only. |
| M20 | Foreign timestamps stored verbatim with declared zone/offset/resolution plus a local receive wall time and optional boot-scoped receive-monotonic diagnostic (CT-02 `:48`) | Untested (CT-01's foreign-money twin *is* tested, E1-U28). |

### Story 1.6 (CT-05)

| # | Requirement | Status |
|---|---|---|
| M21 | Package **SemVer is display-only provenance that never enters identity** (646–648; CT-05 `:17`, AR-25/26) | Untested. Directly checkable: no package version string may appear in canonical bytes / fp1 identity. |
| M22 | "**Every contract field is identity by default; a display-only exclusion requires an explicit, versioned declaration in the contract — never an implementer's judgment call**" (630; CT-05 `:21`) | Untested. The suite's `not hasattr(X, "fp1_identity")` checks are the *opposite* shape — an implicit, undeclared exclusion inferred from a missing method. |
| M23 | `evidence_class` is the closed set **confirmed \| unconfirmed \| provisional** (634; CT-05 `:57`) | Never asserted. `World` gets the closed-set treatment twice (E1-U54, E1-C10); `EvidenceClass` gets none. |
| M24 | Computation identity **dedups identical work from two sandboxes**; the occurrence record is separate provenance outside identity (CT-05 `:25`) | Untested as a property — see §1.1 E1-U53. |
| M25 | Float-bearing artifacts take identity **from the result label**, with an integrity checksum plus (OS, library-version) provenance; cross-OS bit-identity is **not** promised (CT-05 `:22`) | Untested. The suite tests only that floats are refused, never the sanctioned float-payload path. |
| M26 | Label parts are "**addable in later label versions, never redefined**"; the `input_fingerprints` ordering rule (CT-05 `:24`, `:50`) | Untested (minor). |
| M27 | Re-derivation mints a new fingerprint **plus a lineage edge** (CT-05 `:18`) | Half-covered — E1-A02 proves the new fingerprint and explicitly defers the lineage edge to qmf-registry/CT-07/Epic 2. **Accepted deferral.** |

### Story 1.9 (seams)

| # | Requirement | Status |
|---|---|---|
| M28 | "**qmf-core itself performs no I/O and spawns no work**" (722; AD-15, DEC-0138) | Asserted only as "the protocols are Protocols" (E1-U59). No static check. Statically checkable now. |
| M29 | An outer package emits an observation/journal event/record, or reads a secret, **only** through the corresponding Protocol seam injected at the composition root (719–721) | Untested. Outer packages exist in this worktree, so the import-graph half is statically checkable now — this is the same class of check that caught E1-F01. |

---

## 3. `findings.csv` adjudication

The file carries a header plus **one** row.

### E1-F01 — **genuine requirement violation. Confirmed.**

*Row:* two `qmf-data` modules (`backup.py::_fp1_of` lines 932–935; `store/backup_input.py::_fp1`
lines 70–72 with `hashlib.sha256` at line 197) hand-roll `hashlib.sha256(payload).hexdigest()` and
emit `f"fp1:sha256:{digest}"` directly.

*Adjudication:* the requirement is quoted almost verbatim by the contract. CT-05
`ct-05-version-fingerprint.yaml:19`: **"One implementation: the canonical serializer and
fingerprint function live only in qmf-core; no other package computes a fingerprint except by
calling it (DEC-0108)."** epics.md Story 1.6 (622–625): "**Then** both live only in qmf-core and no
other package computes a fingerprint except by calling this single implementation." This is not a
strict-test artefact, not a style preference, and not an over-fit: the test asserts precisely the
ratified invariant, and the code contradicts it. Severity **High** is right for a T1 foundation
package — CT-05 `:20` notes the prefix versions the recipe (an upgrade mints fp2), which is
exactly the change that would make the duplicated copies fork identity silently. The cited
requirement ids (CT-05; DEC-0108; FR-005; RG-DEPGRAPH; AR-14) are all apt.

*One caveat, in the finding's favour:* the detector under-counts (§1.3). The row should be read as
"**at least** two duplicate implementations", not "exactly two".

**Wrong-expectation rows: 0. Genuine rows: 1.**

### E1-F02 — **a row that should exist and does not**

Uncovered by this review, from §1.1 (E1-C11) and §2 (M13):

| field | value |
|---|---|
| finding_id | E1-F02 (proposed) |
| epic | Epic 1 (qmf-core) |
| requirement_ids | CT-03;DEC-0103;FR-003;AR-25 |
| severity | Medium |
| test_path | `qa/tests/epic_01/test_l2_contract.py::test_e1_c11_every_serialized_artifact_stamps_format_version_1` (currently excludes CT-03) |
| description | CT-03 identity values carry no contract format version and no identity projection, so a CT-03 artifact cannot stamp the versioning-from-birth format version its own ratified contract requires. |
| expected | CT-03 `:22` — "Every serialized identity artifact stamps this contract's integer format version, whose meaning never mutates" (DEC-0103, versioning-from-birth). CT-03's header declares `version: 1`. |
| observed | `packages/qmf-core/src/qmf/core/identity.py` defines no `CONTRACT_FORMAT_VERSION` and no `fp1_identity` (0 matches, vs 5 in `chrono.py`, 6 in `exact.py`, 2 in `fingerprint.py`). E1-C11 excludes CT-03 from the stamp check by docstring, deferring it to a qmf-registry record — which DEC-0138 (CT-05 `:29`) forbids as the identity source ("never the wrapping registry record's fingerprint"). |

Recording this is the L6 pass's main output beyond the fidelity read: **the epic's evidence file
under-reports by one row because a test was narrowed to fit the code.**

---

## 4. What the suite gets right (so the gaps are read in proportion)

- **Closed vocabularies are transcribed from the contracts, not read off the enums** — the seven
  CT-04 categories, three retryabilities, five account roles, ten CT-01 unit-kinds and three worlds
  are literal sets in the test files, then compared to the implementation. That is the correct
  direction of authority, and it is the most common place a suite silently inverts.
- **The ◆ mutmut pins assert exact values, directions and payloads**, not presence: E1-U24 walks
  every rounding mode at `< 0`, `= 0`, `> 0` with the mathematically required integer; E1-U30
  asserts `INT64_MIN`/`INT64_MAX` are *accepted* and ±1 refused (killing `<`→`<=`); E1-U42 proves
  cursor advance-by-one over three reads. These are real mutation kills, not coverage theatre.
- **E1-U34 correctly refuses to over-fit** the cross-calendar refusal category, exactly as PLAN
  §8(5) requires — the discipline exists in the suite; §1.2 is about where it lapsed.
- **E1-U16's `assert not hasattr(price, "currency")`** is a model requirement assertion: CT-01
  says a Price is "an instrument-tagged ratio, **never** tagged with a single currency", and the
  test asserts the negative directly rather than inferring it.
- **The failing test was left failing.** Nothing was weakened, no source was touched, and the
  failure was written up with the contract citation. That is the behaviour the lane exists to get.

---

## 5. Recommended next actions (for the operator, not performed here)

1. Add **E1-F02** to `findings.csv` and un-narrow E1-C11 to cover CT-03 artifacts (it will fail —
   that is the point).
2. Put the **E1-U41 raise-vs-refuse** question to an operator ruling: is `Clock` script exhaustion
   programmer error (raise permitted) or a replay data condition (CT-04 refusal required)? Then
   fix the test to match the ruling, and drop the exact-prose assertions either way.
3. Widen **E1-P03** from the 33 `try_create`/module functions to the instance-method surface
   (`add`, `subtract`, `to_money`, `in_pips`, `compare`, `equals`, `contains`, `overlaps`,
   `elapsed_since`, `negate`, `add_duration`, `mint`, `wall_now`, `monotonic_now`) — R-002 is a P0
   row and the arithmetic surface is where consumers actually branch.
4. Add **frozen golden fp1 digests** for a small fixed artifact set, so a recipe or
   canonicalisation change fails a test instead of silently re-deriving new expectations.
5. Add the statically-checkable Story 1.1 / 1.3 / 1.5 / 1.6 / 1.9 checks flagged "statically
   checkable now" in §2 — no `qmf/__init__.py`, tool version pins, DEPENDENCIES.md shape and
   licence policy, SemVer lockstep, failure-register elements, benchmark slots, examples present,
   "Venue/Account defined only in qmf-core", "no calendar rule set in qmf-core", "no I/O in
   qmf-core", SemVer never in identity.
6. Report **branch coverage** for `exact.py` and `chrono.py` against the 100% floor (DEC-0101) —
   PLAN exit criterion (b) is currently unevidenced.
7. Schedule Stories **1.7 and 1.8** (NFR-02 scanners) into a lane; today they carry zero
   verification.
