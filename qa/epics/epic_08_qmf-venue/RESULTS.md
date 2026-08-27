# Epic 8 — qmf-venue port + cTrader adapter — Independent Verification RESULTS

Independent tests authored from the oracles (`epics.md` Epic 8, CT-18/19/20/21,
SCN-0005, constitution L34/L35) and run against the read-only implementation. Source
was never modified; no assertion was weakened to pass. Tests live under
`qa/tests/epic_08/`; all fakes are injected seams (sinks, secret store, probe
transport, clock) so no live venue was contacted.

## Run summary

```
uv run --with hypothesis pytest qa/tests/epic_08 -q
145 test nodes — 140 passed, 5 failed
```

- **Test functions written:** 108 (L1 = 12 functions, incl. one parametrized over 47
  boundary callables; L2 = 49; L3 = 41; L4 = 1). Node count 145 counts hypothesis /
  `parametrize` expansions.
- **Failures:** 5 nodes = **3 distinct findings** (E8-F01 is one defect surfaced across
  3 parametrized inputs; E8-F02 and E8-F03 are one node each).
- **One test-code iteration** (never an assertion): `test_l3_014_protobuf_declared_only_
  in_qmf_venue_pyproject` first matched the word "protobuf" inside a *comment* in
  `qmf-indicators/pyproject.toml`; the regex was tightened to match a quoted dependency
  token. The requirement holds — protobuf is genuinely a qmf-venue-only dependency.

## Authority note

`_bmad-output/test-artifacts/test-design-qa.md` and `.../QMX-handoff.md` (cited in the
task) are **not present in this worktree**; `_bmad-output/` holds only
`planning-artifacts/`. Their relevant content (T1 tiering, the 15 P0/P1 assertions, the
risk-gate rows) was already folded into `PLAN.md` Section 1, which was used as the
standing authority alongside the contracts, epics, and scenario.

---

## Findings (failing tests)

### E8-F01 — CT-21 opacity is not validated at `SecretRef` construction  (Medium)
`test_l1_005_secret_ref_construction_validates_opacity` (3 parametrized inputs, all fail).
CT-21 states a secret reference "never encod[es] venue, broker, account, environment, or
key material; construction validates opacity as an invalid-input refusal." `qmf-core`'s
`SecretRef.try_create` validates only non-emptiness, so a reference plainly encoding
deployment data (`venue=cTrader;broker=...;account=...;env=live;key=...`) is accepted.
`qmf-venue`'s `AccountBinding.try_create` delegates opacity to `SecretRef.try_create`, so
the delegated guard is a no-op. **Meaning:** the CT-21 construction-time opacity check is
absent; the boundary relies on operator discipline the contract says the type enforces.
(The type is in qmf-core but is the CT-21 gate Epic 8 owns; L1-005 is a P2 assertion.)

### E8-F02 — qmf-venue ships no `FAILURES.md` failure register  (Medium)
`test_l3_015_qmf_venue_ships_a_failure_register_covering_its_refusals`.
NFR-11 requires every designed failure mode to ship a register entry, and every sibling
roster package (qmf-core/data/indicators/registry/structure) ships a `FAILURES.md` under
`conventions/failure-register.md`. **Meaning:** the six venue-boundary refusal categories
have no register entry (class/detection/recovery/degraded-state/notification/affordance);
R-009's register reconciliation cannot be satisfied. Confirms plan F-E08-001 as an
isolated omission, not a design intent.

### E8-F03 — qmf-venue ships no `examples/` directory  (Low–Medium)
`test_l3_015_qmf_venue_ships_reference_usage_examples`.
Every other roster package (qmf-core/data/indicators/registry/risk/structure) ships an
`examples/` directory; qmf-venue does not (AR-21/L27 tier-1 obligation). **Meaning:** the
reference-usage-examples obligation is unmet for this distribution unit. Confirms plan
F-E08-002.

---

## Per-test results by level

Legend: **PASS** = the implementation satisfies the asserted contract clause.

### L1 — property tests (`hypothesis`)

| Test | Requirement | Result |
| ---- | ----------- | ------ |
| QA-E08-L1-001 `…public_boundary_never_raises` (47 callables × fuzz) | FR-004/CT-04/R-002; SCN-0005 Given | PASS |
| QA-E08-L1-001 `…unknown_gate_try_create_never_raises` | R-002 | PASS |
| QA-E08-L1-001 `…probe_try_create_never_raises` | R-002 | PASS |
| QA-E08-L1-002 `…secret_value_never_renders_its_value` | FR-025/CT-21/AR-37/L34/R-019 | PASS |
| QA-E08-L1-003 `…command_identity_distinguishes_ordering_ordinal` | FR-023/CT-19 | PASS |
| QA-E08-L1-003 `…observation_identity_excludes_occurrence_fields` | FR-024/CT-20 | PASS |
| QA-E08-L1-003 `…observation_identity_distinguishes_venue_native_key` | CT-20 | PASS |
| QA-E08-L1-004 `…execution_float_crosses_to_scaled_integer_no_float_in_identity` | FR-026/CT-18/DEC-0141 | PASS |
| QA-E08-L1-004 `…nan_and_infinity_cannot_cross_the_boundary` | CT-01 | PASS |
| QA-E08-L1-004 `…integer_decoders_refuse_binary_floats` | CT-01/DEC-0105 | PASS |
| QA-E08-L1-005 `…secret_ref_stable_and_blank_refused` | FR-025/CT-21/AD-9 | PASS |
| QA-E08-L1-005 `…secret_ref_construction_validates_opacity` | FR-025/CT-21/AD-9 | **FAIL → E8-F01** |

### L2 — contract tests (CT-18/19/20/21)

| Test | Requirement | Result |
| ---- | ----------- | ------ |
| L2-001 declaration static/credential-free/tag-91/identity-bearing | FR-022/CT-18 | PASS |
| L2-001 declaration identity excludes measured values | CT-18 | PASS |
| L2-001 profile occurrence-only, append-only w/ supersedes | CT-18 | PASS |
| L2-002 unmapped code fails closed to UNKNOWN + alarm | FR-022/CT-18/CT-19 | PASS |
| L2-002 rejected only where a row declares that class | CT-18 | PASS |
| L2-003 measured-at-connection value absent from declaration | FR-026/CT-18/AR-46 | PASS |
| L2-003 absent money exponent / refused check refuse via profile | CT-18 | PASS |
| L2-004 measured capability before profile is unavailable | FR-022/CT-18/AR-45 | PASS |
| L2-004 measured-but-refused capability is policy-rejection | CT-18 | PASS |
| L2-005 undeclared capability is unsupported | FR-022/CT-18 | PASS |
| L2-005 unsupported close scope refused, never widened | CT-18 | PASS |
| L2-006 vocabulary is exactly five kinds | FR-023/CT-19/AR-44 | PASS |
| L2-006 fractional/partial close is unsupported-capability | CT-19 | PASS |
| L2-006 kind-inappropriate field omitted, never null | CT-19 | PASS |
| L2-007 four-outcome law excludes partially-executed | FR-023/CT-19/L35 | PASS |
| L2-007 every outcome resolves to one law member + mints records | FR-023/CT-19 | PASS |
| L2-008 transport triggers resolve UNKNOWN, never rejection | FR-023/CT-19/L35 | PASS |
| L2-008 unmapped venue error is UNKNOWN not rejection | CT-19/CT-18 | PASS |
| L2-009 stop-side risk-increasing amendment refused | FR-023/CT-19/DEC-0148 | PASS |
| L2-009 stop check binds stop side only | CT-19 | PASS |
| L2-009 amend_protection is its own kind, not widened | CT-19 | PASS |
| L2-010 compound meet is never a success when a child fails | FR-023/CT-19 | PASS |
| L2-010 compound children have distinct derived identity | CT-19 | PASS |
| L2-011 binding idempotent accept + collision alarm | FR-023/CT-19/AR-48 | PASS |
| L2-011 injective-total mapping needs no binding | CT-19 | PASS |
| L2-011 storage failure before submission is surfaced | CT-19/AR-47 | PASS |
| L2-012 inbound event mandates receive-wall + monotonic stamps | FR-024/CT-20/AR-47 | PASS |
| L2-012 fill identity fields are mandatory | CT-20 | PASS |
| L2-012 recorder stores verbatim before journaling | CT-20/AR-47 | PASS |
| L2-013 terminal state only from fills/lifecycle, never absence | FR-024/CT-20 | PASS |
| L2-013 denied-locally has no venue order | CT-20 | PASS |
| L2-014 illegal transition annotated + forces UNKNOWN | FR-024/CT-20 | PASS |
| L2-014 adapter never synthesizes a venue observation | CT-20 | PASS |
| L2-015 partial write is storage-failure blocking command stream | FR-024/CT-20/AR-47 | PASS |
| L2-016 reconciliation verdict vocabulary + out-of-lookback | FR-024/CT-20/SCN-0005 | PASS |
| L2-016 reconciliation gates command pipe only, never sensing | CT-20 | PASS |
| L2-017 subject-terminal at/after submit is named rejected outcome | FR-024/CT-20/DEC-0148 | PASS |
| L2-017 subject absent at submission resolves without submission | CT-20 | PASS |
| L2-018 journal mapping total+unique over (kind × outcome) | FR-024/CT-20 | PASS |
| L2-018 journal mapping total+unique over observation kinds | CT-20 | PASS |
| L2-019 binding fp1 excludes secret reference | FR-025/CT-21 | PASS |
| L2-019 bindings differing only by credential fingerprint identically | CT-21 | PASS |
| L2-019 non-opaque secret_ref refused at binding construction | CT-21 | PASS |
| L2-020 secret value never crosses out of connection manager | FR-025/CT-21/AR-37 | PASS |
| L2-020 missing credential is unavailable-dependency carrying ref not value | CT-21 | PASS |
| L2-021 failed store after rotation alarms/blocks command/keeps old | FR-025/CT-21/AR-38 | PASS |
| L2-021 successful rotation stores then swaps | CT-21/AR-38 | PASS |
| L2-022 per-writer sequence strictly increasing | FR-025/CT-21/CT-19 | PASS |
| L2-022 one held value per credential + boot-epoch distinct | CT-21 | PASS |

### L3 — acceptance tests (epic-specific behaviour)

| Test | Requirement | Result |
| ---- | ----------- | ------ |
| L3-001 outstanding UNKNOWN refuses new command (after=resolution) | FR-023/SCN-0005/L35/CT-19 | PASS |
| L3-002 sensing pipe keeps flowing while command pipe gated | FR-024/SCN-0005/CT-20 | PASS |
| L3-003 UNKNOWN observation carries trigger/elapsed/receive/deadline | FR-023/SCN-0005/CT-19 | PASS |
| L3-003 record_unknown requires the mandatory UNKNOWN fields | CT-19 | PASS |
| L3-004 resolve_unknown records observation + clears only on resolution | FR-023/SCN-0005/CT-19 | PASS |
| L3-005 refused protection act held as standing intent, journaled | FR-023/SCN-0005 | PASS |
| L3-005 standing intent re-decides against reconciled only | SCN-0005/DEC-0158 | PASS |
| L3-006 risk-reducing dispatch ahead of place_order | FR-023/SCN-0005/CT-19 | PASS |
| L3-006 suspend-new local + instant, no venue round-trip | SCN-0005/CT-19 | PASS |
| L3-007 adapter never initiates flatten/resubmits/invents | FR-023/SCN-0005/L35/DEC-0150 | PASS |
| L3-008 every illegal (from-state, kind) pair yields a typed edge | FR-024/CT-20 | PASS |
| L3-008 illegal transition folds to UNKNOWN, never synthesizes | CT-20 | PASS |
| L3-009 timestamp decode records mandatory receive time | FR-026/AR-46/DEC-0135 | PASS |
| L3-009 market-data price is exact scaled integer at wire scale | FR-026/AR-46/DEC-0135 | PASS |
| L3-009 execution price raw double crosses the named boundary | FR-026/AR-46/DEC-0141 | PASS |
| L3-009 money decode governs nine messages, absent exponent refuses | FR-026/AR-46/DEC-0135 | PASS |
| L3-010 daily boundary/bar basis read from profile, not hardcoded | FR-026/AR-46/DEC-0135 | PASS |
| L3-010 unmeasured daily boundary refuses, never defaults | AR-45/DEC-0135 | PASS |
| L3-010 config names no broker, only opaque identity | FR-026/AR-46/AR-42 | PASS |
| L3-011 probe records unverified rather than defaulting | FR-022/AR-45/SC-02 | PASS |
| L3-011 probe stands alone (no port/journal dependency) | FR-022/AR-45 | PASS |
| L3-012 probe renders only reference, submits no order | FR-025/AR-37/SC-02 | PASS |
| L3-013 command-path storage failure blocks commands, sensing unaffected | FR-025/AR-47/CT-21 | PASS |
| L3-013 recorder blocks via the writer-holding connection manager | FR-024/AR-47 | PASS |
| L3-014 qmf-venue imports only qmf-core + protobuf | FR-026/AR-06/AR-42/AR-43 | PASS |
| L3-014 nothing imports qmf-venue; core stays clean | AR-06/AR-42 | PASS |
| L3-014 protobuf declared only in qmf-venue pyproject | AR-43 | PASS (after test-code fix) |
| L3-015 qmf-venue ships a failure register covering its refusals | NFR-11/R-009 | **FAIL → E8-F02** |
| L3-015 qmf-venue ships reference usage examples | AR-21/L27 | **FAIL → E8-F03** |
| L3-016 rate pacer enforces per-connection ceilings | FR-023/AR-46/DEC-0135 | PASS |
| L3-016 heartbeat bound / span cap / two-host topology | AR-46/DEC-0135 | PASS |
| L3-016 session recovery never resubmits | AR-46/FR-025 | PASS |
| L3-017 proto artifact names Spotware package + pinned tag 91 | FR-022/AR-43/DEC-0141 | PASS |
| L3-017 compiles from message definitions as data, not code | AR-43/DEC-0141 | PASS |
| L3-017 tag change mints new declaration + forces re-verification | AR-43/DEC-0141 | PASS |

### L4 — scenario test

| Test | Requirement | Result |
| ---- | ----------- | ------ |
| L4-001 uncertain submission end-to-end journey | SCN-0005/FR-023/FR-024/CT-19/CT-20/L35 | PASS |

---

## Notes, and requirements not testable this phase

- **`observation_journal_event_type(kind)` raises on a non-`ObservationKind`** (a
  `ValueError`, documented `# pragma: no cover`) rather than returning a typed refusal.
  It is public (`__all__`) but is an internal enum-mapping helper documented to take a
  real kind; L1-001 is scoped to *well-typed* input per the plan, so this is recorded as
  an observation, not a failing finding. Every actual input-validating boundary in the
  L1-001 sweep (47 factories/decoders) returns value-or-refusal and never raises.
- **Settlement-currency ↔ Book `accounting_currency` bind-time policy-rejection (CT-18):**
  the Book noun is qmf-risk (Epic 10) and does not exist in this worktree, so the
  *bind-time mismatch* verdict is cross-epic and untestable here. What IS testable at the
  venue seam was verified: an unmeasured settlement currency is an unavailable-dependency
  (L2-003), consistent with CT-18.
- **Measured-at-connection *values*** (daily-boundary minute, bar-basis quote side,
  pip-formula, amend-atomicity) — the verify-or-refuse *interface* is tested (L3-010/011);
  the actual measured verdicts need a live cTrader demo connection and stay DEFERRED
  (Plan §7; AR-45).
- **Reconciliation-verdict *consequences* / flatten severity policy** — node/BMS authority
  (`tracker/trading-node-notes.md`), deliberately not QMF contract surface; untestable by
  design (DEC-0142/0150).
- **Latency numeric budgets** — none exist (measure-then-budget); only the negative "a
  wall-computed rung is refused" is a contract fact and is enforced structurally in
  `MonotonicReading` (qmf-core). No number was invented.
- **Live cTrader interaction, store mechanics / key custody, Ubuntu tier-1** — OUT OF
  SCOPE per Plan §7; all venue tests used injected fakes.

## Existing-test audit (§5) — orientation

The author-written suites in `packages/qmf-venue/tests/` were read for API orientation
only; the independent suite asserts contract clauses directly and does not reuse their
assertions. No author test was found to *contradict* a requirement (no R-003 "contradicts"
row): the state-machine matrix (L3-008), the UNKNOWN-block stateful behaviour (L3-001..005),
and "market data keeps flowing" (L3-002) — the behaviours line coverage cannot see — all
hold under independent enumeration. Plan finding F-E08-004 (suspicion) is therefore **not**
elevated to a confirmed finding.
