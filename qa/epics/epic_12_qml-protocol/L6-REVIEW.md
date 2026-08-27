# L6-REVIEW — Epic 12 (qml-protocol)

**Verdict: GAPS.**

Reviewed: `PLAN.md`, `RESULTS.md`, `findings.csv`, and all 10 modules under `qa/tests/epic_12/`
(73 test functions). Authorities: `_bmad-output/planning-artifacts/epics.md` §"Epic 12: QML protocol
& conformance" (Stories 12.1–12.8), `docs/contracts/ct-33-bot-definition.yaml`,
`docs/contracts/ct-34-confluence.yaml`, `docs/components/qml.md`. The named system plan
(`test-design-qa.md`) and handoff (`QMX-handoff.md`) are **confirmed absent** from this worktree —
E12-F06 is accurate, independently verified.

The suite is, on the whole, a serious piece of work: fixtures are test-owned (`_world.py` builds
through public `mint_*` API and never imports the shipped example), refusal paths are almost always
paired with an admitting control, the L0 detectors are self-armed, and the two mid-run corrections
recorded in the stage summary were the right calls (fixing the test surface, not the source). Most
tests assert what the requirement demands.

But the audit's central scope ruling is **factually wrong**, and it is wrong in the direction that
hides the epic's one candidate P0. The ship-blocking triad clause (i) is rated GREEN on a surface
that nothing forces a caller through, while the actual registration surface — public, in-package,
and exercised by the shipped L27 example — was never opened.

---

## 1. The decisive finding: an ungated in-package Bot-kind mint

`RESULTS.md` §UNPROVEN and `findings.csv` E12-F01 both assert:

> "the actual registry record mint is **defined-unwired** at the AD-25 composition root … the
> registry package correctly has no bot-mint path; the minting host is QMB Story 14.8 / the trading
> node." · "L4 … has no realized in-package surface and is out of this T2 tier."

That is not true of the `qml` package. `qml/src/qml/declaration/bot.py:662`:

```python
def register_bot_definition(
    payload: object, *, registrar: object, writer: object, sequence: object,
    created_at: object, at_birth_parent_refs: object = None,
) -> Result[RegistrationReceipt]:
    ...
    content = mint_bot_definition(payload, at_birth_parent_refs=at_birth_parent_refs)
    if is_refusal(content):
        return content
    return registrar.register(kind=KIND_BOT_DEFINITION, body=content.value.body(), ...)
```

It is exported from `qml.declaration` **and from top-level `qml`** (`qml/src/qml/__init__.py:93`,
`__all__` line 284), alongside `install_bot_definition_kind`. It takes a raw declaration payload,
validates content shape, and **stamps and persists a CT-33 Bot-kind record** through an injected
`Registrar`, returning a `RegistrationReceipt` whose `outcome.value` is `"stored"`.

It consults **no Layer-1 verdict, no Layer-2 verdict, and no `ConformanceTicket`.** `grep` for
`ticket|Layer1Verdict|Layer2Verdict|conformance` over `declaration/bot.py` returns nothing.

Against the requirement:

- **epics.md Story 12.7 AC1** — "the Bot kind mints **only if** both Layer 1 and Layer 2 pass; a
  declaration failing either layer is refused `policy rejection` — there is no partial or
  probationary registration."
- **CT-33 line 44** — "Registration is the ticket: the Bot kind mints **ONLY** for a declaration
  passing both conformance layers … registration otherwise refuses (`policy rejection`)."
- **CT-33 line 67** — typed-refusal codes on this contract's registration paths include
  "`policy rejection` (registration attempted for a declaration that fails either conformance
  layer)."

`register_bot_definition` has no such path. A declaration that fails Layer 2 — or that was never
shown to either layer — mints and stores a Bot record through it.

This is not a hypothesis about unwired territory. The shipped reference bot itself drives that path:
`qml/examples/conformant_bot_usage.py:230-258` (`layers_pass_and_bot_kind_mints`) installs the kind,
builds a `Registrar`, calls `register_bot_definition(candidate.declaration, ...)`, and asserts
`receipt.record.kind == KIND_BOT_DEFINITION` and `receipt.outcome.value == "stored"`. It passes
`candidate.declaration`, never the ticket — the gate is decorative at the call site.

The plan set exactly the right tripwire and then aimed it one module too narrowly. PLAN.md §8-A:

> "If, at reconcile, `qml.conformance.registration` is found to itself stamp/persist a record …
> that inverts AD-25 and is a **P0 FINDING**."

The reconcile checked `qml.conformance.registration` (clean — it genuinely returns content + verdict)
and stopped. The stamping lives in `qml.declaration.bot`. Note the AD-25 half of the tripwire is
arguably satisfied — the host still supplies `WriterId`, `sequence`, `created_at` — so this may not
be an AD-25 inversion. But AD-25 was never the load-bearing clause: **Story 12.7 AC1 / CT-33 §44 is,
and it is unenforced on the one surface that actually mints.**

Secondary reading, equally a finding: `ct-33-bot-definition.yaml:9` declares
`wiring_status: defined-unwired  # no code exists … no wiring is authorized from this doc`. If the
doc is current, `install_bot_definition_kind` + `register_bot_definition` are unauthorized wiring of
a defined-unwired contract. If the code is current, the gate requirement bites. Either branch is a
finding; neither is "out of tier".

**Constructible counter-case the author owed (rule 1), never attempted:** mint a valid declaration;
obtain a `policy rejection` from `gate_registration` (or skip the gate entirely); then call
`qml.register_bot_definition(payload, registrar=Registrar(registry), writer=…, sequence=0,
created_at=…)` and observe the **test-owned registry sink**. If a record lands, the requirement is
violated. That is a four-line test against a public surface with an injected observer — it needed no
composition root, no live Book, and no L4 tier.

**Consequence for the RESULTS verdict table:** triad clause (i) — "Bot passes BOTH layers or is
`policy rejection`, no partial state" — is rated **GREEN** on `evaluate_ticket` / `gate_registration`
alone. Those are pure advisory functions. Nothing in `qml` requires a caller to pass through them
before minting. Clause (i) should read **FINDING (candidate P0)**, not GREEN.

---

## 2. Wrong-expectation tests

Ranked by consequence. Five of 73 — the rest hold up.

**W1 · `test_l2_determinism.py::test_e12_l2_13_conformance_gates_citation_and_seats_not_tunnel`
(P0-Q2, triad clause (ii)) — asserts self-declared constants; no counter-case exists.**
Two of its three claims cannot fail:
- `tunnel.value.fp1_identity()["tunnel_open"] is True` reads a hard-coded literal in
  `UngovernedTunnelAccess.fp1_identity()` (`registration.py:141`). Banned shape 2 — a module's
  self-declared marker asserted as proof of behaviour. No tunnel is observed; no sink exists.
- `cite_ungoverned_bot()` is called with **no arguments** and unconditionally returns a policy
  refusal — its body is `del cited_fp1, kind; return policy(...)` (`registration.py:305-315`). The
  test calls a function that has exactly one possible outcome and asserts that outcome. Banned
  shape 2 — calling a function against itself.

The third claim (registered `fp1` may be cited via `cite_registered_bot`) is real. And the sibling
`test_e12_l2_13_complexity_score_is_not_a_registration_gate` is genuinely good — the
hostile-value-does-not-block case plus the unknown-non-dropped-field control is a proper
discriminating pair (Story 12.7 AC5, GREEN). But clause (ii)'s "never tunnel entry" half rests on a
constant. E12-F05 correctly records the real tunnel as node territory; RESULTS then re-imports the
constant as "the qml-side is GREEN". It is not evidence.

**W2 · `test_l1_protocol_boundary.py::test_e12_l1_08_layer1_failures_are_returned_not_raised_and_journaled` —
the "journaled" clause is a self-declared flag.**
`assert refusal.context.get("journal") is True` reads the marker `layer1._journal()` stamps on its
own output (`layer1.py:60-63`). Story 12.3 AC4 demands the refusal be "journaled — never swallowed".
`qmf.core.sinks.JournalSink` exists (CT-13, `packages/qmf-core/src/qmf/core/sinks.py:123`) and is
exactly the injected observer rule 3 asks for; nothing is appended to one here, and nothing in `qml`
appends to one. The honest disposition is either an injected `JournalSink` recorder, or an UNPROVEN
row saying journaling is host-side. Neither was done — silent narrowing (rule 5). The
returned-not-raised half (the `try/except` that converts a raise into an AssertionError) is genuine
and good.

**W3 · `test_l3_conformance_contract.py::test_e12_l3_10_spawned_runner_yields_the_same_pure_verdict` —
real subprocess, degenerate payload.**
The child runs `factory_spec=None` → `FACTORY_KIND_SILENT`, and the in-process side uses
`FunctionFactory(logic=lambda evidence: ())`. Both traces are empty, `emitted_kinds` is empty, and
the two verdicts are equal for a bot that does nothing. Story 12.4 AC4 says "the same bot run through
two different hosts". The spawn is real (credit — this is the strongest structural test in the
suite), but it does not discriminate a host-dependent verdict for a bot that emits intents. It also
leaves the boundary's real hazard untouched: observations cross via `runner._jsonable`, whose final
fallback is `return str(value)` (`runner.py:608`) — precisely the lossy-serializer round-trip in
banned shape 2, never exercised because the payload is empty.
`FACTORY_KIND_SOURCE` accepts operator-authored Python and would have carried the real bot across.

**W4 · `test_l0_static.py::test_e12_l0_03_qml_contracts_are_local_not_ct_numbered` —
constant-reading, with a decorative counter-case.**
`proto["ladder"] == "qml-ad5"` is the module declaring its own ladder. The "counter-case armed" line
is `assert "CT-33".upper().startswith("CT-")` — that exercises `str.startswith`, not the SUT. The
requirement (Story 12.1 AC1) is itself about a declared identity, so some constant-reading is
unavoidable; the fix is to label it a declaration check, not to count it as a behaviour green.
Low severity.

**W5 · `test_l3_example_bot.py::test_e12_l3_12_example_declaration_boundary_is_honest` —
partially tautological.**
`for forbidden in ("exit_logic","requested_r","declared_full_loss_price","sizing"):
assert forbidden not in body` cannot fail: `body()` returns exactly the six fixed content groups, a
fact E12-L3-05 already asserts by set-equality. Duplicate-and-relabel. The `scan_logic_source(...)
.clean is True` line in the same test is real and carries the AC. Low severity.

---

## 3. Missed requirements — owned by Epic 12, no test covers them

**M1 · Story 12.7 AC1 + AC6 against the real registration surface.** §1 above. Zero tests touch
`qml.register_bot_definition` or `install_bot_definition_kind`. **This is the single most important
gap.**

**M2 · Story 12.4 AC2 — "the golden-slice generator produces a deterministic, identity-bearing
conformance fixture *keyed off that footprint*."** No test asserts it. `generate_golden_slice` is
called four times across the suite, always as an *input* to something else; no test asserts that two
generations from one footprint fingerprint alike, and none asserts that a *different* footprint
yields a *different* `golden_slice_fingerprint`. The Layer-2 verdict identity carries
`golden_slice_fingerprint` (asserted as a key name in E12-L2-02, never as a value with meaning). If
the generator were footprint-insensitive, every conformance identity in the epic would be hollow and
all 73 tests would still pass. Two assertions would close it. No UNPROVEN row.

**M3 · Story 12.2 AC3 — the protocol-format-version component of the restore tuple.** The AC names
four components ("logic identity + source-manifest fingerprint, protocol format version, or
arithmetic-reference build … **any one** of those"). `test_e12_l1_07` tests three and excludes the
fourth in its own comment: *"Only protocol format version 1 is known, so the OS / arithmetic-reference
/ logic-identity components exercise the differing-tuple seam."* That exclusion is correct
engineering judgement and a **rule-5 violation as recorded** — it appears nowhere in RESULTS.md's
UNPROVEN section and nowhere in findings.csv. RESULTS.md row E12-L1-07 reads "Restore across a
differing OS / arithmetic-reference / logic-identity is `unavailable dependency`" and the FM-6
disposition reads GREEN, with no note that a quarter of the clause is untested.

**M4 · Story 12.5 AC5 — "it is a Layer-2 conformance failure *before any process is spawned*."** The
ordering clause has no observer. E12-L2-06 calls `scan_logic_source` directly (no runner involved);
E12-L2-03(c) injects a `ScanFinding` into an observation record. Neither calls `run_sandbox` with
dirty source and observes that **no child was spawned**. The source does return pre-spawn
(`runner.py:149-150`), but the test suite takes that on the module's word. A test-owned recorder
around the spawn seam would settle it. No UNPROVEN row.

**M5 · Story 12.4 AC1/AC3 — four Layer-2 verdict arms have no counter-case.** `evaluate_layer2`
gates on seven conditions; E12-L2-03 flips three (`golden_slice_determinism`,
`permitted_intent_kinds`, `static_ast_import_scan`). Never flipped to their failing value:
`loaded_in_isolation=False` ("the logic artifact loads in isolation" — a named AC3 clause),
`book_present=True` ("no Book present or needed" — AC1 and AC4), `state_bound_holds=False`,
`restore_equivalent=False` (both named in AC3). Each is a one-line `dataclasses.replace` in the
pattern the test already uses. No UNPROVEN row.

**M6 · Story 12.1 AC2 — evidence-shape clauses.** "structure lifecycle folds per AD-25" and "each
sample carrying its knowable-at instant" are untested. `_world._series` supplies `knowable_at` but no
test removes it to confirm refusal, and structure-fold evidence appears nowhere in the suite.
E12-L2-05 covers the *key set* (declared vs undeclared vs forbidden), which is the other half of the
AC. No UNPROVEN row.

**M7 · Story 12.1 AC4 — "no Book module is ever injected into bot logic."** `construct_bot` is never
called with a book-bearing read surface. E12-L2-05 refuses a `"book"` key on `FootprintEvidence`, and
the runner's `_refuse_book_keys` / `_refuse_book` (`runner.py:518-540`) are never reached through any
public call in the suite. Adjacent coverage, not the clause.

**M8 · Story 12.6 AC1 — "runs statically on demand *and at seat time*."** Only the on-demand
invocation is tested. Seat-time invocation is plausibly host territory — but that is an UNPROVEN row,
not a silence.

Not counted as missed: Story 12.5 AC1–AC3 (correctly UNPROVEN, E12-F02), Story 12.6 AC5 thresholds
(correctly UNPROVEN, E12-F03), Story 12.8 (fully covered by E12-L3-12), Story 12.3 AC1/AC2/AC3/AC5
(covered), Story 12.7 AC5 (covered, and well).

---

## 4. Per-row adjudication of `findings.csv`

| Row | Requirement ids | Adjudication |
|---|---|---|
| **E12-F01** | FR-048; Story 12.7; CT-33; AD-25; ADR-0018 | **WRONG EXPECTATION.** Its `observed` states the mint is defined-unwired and host-territory and that no in-package surface exists. `qml.register_bot_definition` (`qml/src/qml/declaration/bot.py:662`, re-exported at top-level `qml`) stamps and stores a CT-33 Bot record and is called by the shipped example. The requirement was testable here and was not tested; the path it names is ungated by any conformance verdict, which is a candidate **P0 genuine violation** of Story 12.7 AC1 / CT-33 §44/§67. The `expected` column ("a wired registry-persisted Bot-kind mint enforcing both layers") is the right expectation — the `observed` column is the error. Re-file as a defect finding, severity high, not `info`. |
| **E12-F02** | FR-048; Story 12.5; AR-68; DEC-0178 | **UNPROVEN, CORRECTLY RECORDED.** Story 12.5 AC2/AC3 name hardened OS confinement as a deferred dependency and put the dynamically-evasive bot outside V1's threat model. "The sandbox stops a determined attacker" is untestable-positive; refusing to fake it is right. The V1 mechanisms it defers to are separately covered (E12-L2-06 real; E12-L3-10 weak per W3). |
| **E12-F03** | FR-048; Story 12.6; CT-22; DEC-0181 | **UNPROVEN, CORRECTLY RECORDED.** Story 12.6 AC5 explicitly holds the threshold at GAP-0048/0049, interfaces only (SC-07). Manufacturing a threshold value into a passing fixture would itself have been a finding, and the author says so. The behaviour that *is* ratified (blank passes registration, blocks live binding) is genuinely tested in E12-L3-11 with both arms. Model row. |
| **E12-F04** | FR-047; Story 12.7; CT-07 | **UNPROVEN recorded — on a premise now falsified.** The narrow claim holds: no CT-07 lineage-edge *record* is minted anywhere in `qml`, so edge persistence is genuinely unproven. But its stated reason — "persistence rides the same defined-unwired AD-25 composition-root mint as E12-F01" — inherits E12-F01's error, and `register_bot_definition` accepts `at_birth_parent_refs`, so the lineage seam is closer to in-package than recorded. Keep the row; rewrite the reason once E12-F01 is re-adjudicated. |
| **E12-F05** | FR-048; FR-050; Story 12.7; B-4 | **UNPROVEN, CORRECTLY RECORDED** for the claim it files. Whether the real tunnel admits ungoverned bots is genuinely QMB/node territory and cannot be observed from `qml`. Caveat: the "qml-side is GREEN" clause it cites is the W1 constant-reading, so the row is right and its supporting evidence is weaker than stated. |
| **E12-F06** | GAP-QA-01 | **UNPROVEN, CORRECTLY RECORDED — independently verified.** `_bmad-output/test-artifacts/` does not exist in this worktree (confirmed). Reconstructing the L0–L6 architecture from `LENS-TEST-STRATEGY` + `COMP-QML` + the lane brief and flagging it is the right call. Process finding, not a code defect. |

**Tally:** 0 rows filed as genuine violations · **1 wrong expectation (E12-F01)** + 1 contaminated
premise (E12-F04) · **4 UNPROVEN correctly recorded** (F02, F03, F05, F06).

Rule 6 is therefore **not** satisfied: `findings.csv` carries no genuine violation and no
unproven-requirement row for M2–M8, while RESULTS.md marks every owned requirement green. Six
requirement clauses were narrowed without a row.

---

## 5. What the suite got right

Recording this so the re-work does not discard it. The fixture discipline is genuinely good:
`_world.py` builds only through the public `mint_*` API, raises rather than returning on a broken
build (so a broken fixture can never look green), and the behavioural tests deliberately do **not**
import the shipped example's recipe — E12-L3-12 tests it separately. The refusal tests almost all
carry an admitting control on the same surface (L1-04, L1-06, L1-07, L2-04, L2-13, L3-03). The L0
detectors self-arm on an injected violation. The determinism canary (`FlakyFactory`, E12-L2-01) is
exactly the falsifiability rule 1 asks for, and the hypothesis generalization has a reachable domain.
E12-L2-11's nested-confluence transitive-union test is the best test in the suite: it builds a real
two-level confluence graph, computes the union, asserts exact key equality, then drives both the
complete and the missing-nested declaration through the linter. E12-L1-05's correction — recognizing
that `mint_bot_definition` re-stamps the version so the *read* surface is what must refuse v99 — is
precisely the discipline the hardened contract was written to enforce.

---

## 6. Required to clear this review

1. Re-file **E12-F01** as a defect against Story 12.7 AC1 / CT-33 §44/§67, and write the test:
   drive `qml.register_bot_definition` with a test-owned `Registrar` sink and a declaration that did
   not pass both layers; observe the sink. Correct the RESULTS triad table — clause (i) is not GREEN.
2. Close **M2** (golden-slice determinism + footprint-keying) — two assertions.
3. Close **M5** (four unflipped Layer-2 verdict arms) — four `dataclasses.replace` lines in an
   existing pattern.
4. Close **M4** with a test-owned spawn recorder, or record it UNPROVEN.
5. Add UNPROVEN rows for **M3** (protocol-format-version restore component), **M6** (knowable-at /
   structure folds), **M7** (Book injection through `construct_bot`), **M8** (seat-time invocation),
   and for the journaling half of W2.
6. Either strengthen **W3** to `FACTORY_KIND_SOURCE` with a bot that emits intents, or record the
   cross-host claim as proven only for the degenerate case.
7. Relabel **W1**'s two constant-reading assertions and **W5**'s tautological loop, or drop them; do
   not let them carry P0-Q2.
