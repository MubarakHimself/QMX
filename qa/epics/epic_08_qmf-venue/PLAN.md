# Epic 8 — qmf-venue port + cTrader adapter — Independent Verification PLAN

> Per-epic template compliance: the eight sections below run in the template's
> fixed order. **Section 4 (the independent test list) was authored before any
> `packages/qmf-venue/src/**` implementation body was opened.** Only the public
> module/file *names* and the directory layout were listed prior to Section 4;
> no implementation was read. Oracles are `epics.md`, the CT-* YAML, SCN-0005,
> and the constitution — never the code.

---

## Section 1 — Header and baseline

- **Epic:** 8 — qmf-venue port + cTrader adapter (Wave 3, H; Story 8.1 hoisted to Wave 2).
- **Tier:** **T1** — full independent suite: L1 properties + L2 contracts + L3 acceptance for every AC + L4 participation + L5 mutation targets + L6 review (test-design-qa.md, T1 definition; ranked #3 — "the literal live-money boundary").
- **Package in scope:** `qmf-venue` (`packages/qmf-venue/`, import root `qmf.venue`, src/ layout `src/qmf/venue/`).
- **Modules in scope** (names only, no body read before Section 4):
  `blocking.py` (UNKNOWN stream block, Story 8.7), `capabilities.py` (CT-18 two-artifact discovery, Story 8.4), `commands.py` (CT-19 five kinds + four-outcome law, Story 8.5), `connection.py` (CT-21 connection manager / secret boundary, Story 8.3), `ctrader.py` (adapter #1, Stories 8.1/8.8), `events.py` (CT-20 record-before-interpret + reconciliation, Story 8.6), `observation.py` (venue-observation records), `probe.py` (first-connection capability probe, Story 8.1), `proto.py` (in-house Spotware proto tag 91, Story 8.2), `_bench.py` (benchmark harness — **present**).
- **Requirement ids this epic owns** (copied from the epics.md FR Coverage Map and Epic 8 story headers — not re-derived):
  - **FR:** FR-022 (verify-or-refuse capability discovery, CT-18), FR-023 (five commands, four-outcome law, CT-19), FR-024 (record-before-interpret, reconciliation, CT-20), FR-025 (secret references, connection manager, CT-21), FR-026 (cTrader adapter behind the neutral port).
  - **CT:** CT-18, CT-19, CT-20, CT-21.
  - **SCN:** SCN-0005 (Uncertain Venue Submission Resolves to UNKNOWN).
  - **Constitution laws:** L34 (secret references, never values), L35 (four-outcome law; timeout ≠ rejection; UNKNOWN blocks its command stream until explicit recorded resolution).
  - **AR:** AR-42 (one neutral port, four contracts, venue-blind, never MQL), AR-43 (Spotware proto compiled in-house, pinned tag 91, protobuf a qmf-venue-only dependency, OpenApiPy reference-only), AR-44 (exactly five typed command kinds), AR-45 (first-connection verify-or-refuse; measured-at-connection is an unavailable dependency until its profile exists), AR-46 (cTrader ratified venue facts; boundary/basis/broker are per-broker config, never hardcoded), AR-47 (recording precedes interpretation; ordered/atomic multi-room write or stream block), AR-48 (durable command-id-binding when the client-id field cannot carry the fingerprint), AR-37 (SecretRef/SecretValue render guard), AR-38 (rotation store-before-discard), AR-06 (default-deny: qmf-venue imports only qmf-core; nothing imports qmf-venue).
  - **NFR:** NFR-05 (secrets as references only; tier-1 scan gate; credentials never leave the connection manager), NFR-11 (every designed failure mode ships a register entry).
- **Owned risk-gate rows** (handoff §Risk-to-Story Mapping): **R-009** (every door-reachable typed refusal has a register entry) — owning lanes include E8; **R-019** (secret rendering paths) — E1/E8, one L1 property. R-002 (no public callable raises) and R-003 (existing-test audit) apply to this lane as they apply to all.
- **Evidence baseline** (from test-design-qa.md ranked list, row 3, and `docs/`): line **99.13% / branch 96.99%**; Skylos **132 findings**; **no CRITICAL complexity hit** called out for the package in the ranked list. Dependency fact (DEPENDENCIES.md): `protobuf ==7.36.0` (BSD-3-Clause), declared **only** in `packages/qmf-venue/pyproject.toml`, tag **91**, zero Spotware code executes.
- **Build report:** **None.** Epic 8 is < 20, so no epic build/advisory-review report exists (stated explicitly per the template rather than left blank). The Epic 20–23 advisory reviews are used only as the fault-family source in Section 3.
- **Known distribution-unit gaps** (confirmed by directory listing only): **no `FAILURES.md`** (against NFR-11) and **no `examples/` directory** (against AR-21/L27). `_bench.py` is present. These are recorded as findings in Section 8 — **not** remediated here.

---

## Section 2 — Requirement extract

The oracle. Acceptance criteria are quoted verbatim from `epics.md`; contract clauses verbatim from the CT-* YAML; scenario clauses verbatim from SCN-0005. Nothing paraphrased. Ambiguities are logged in Section 8, never resolved by reading code.

### 2.1 Story acceptance criteria (verbatim, `epics.md`)

**Story 8.1 — cTrader capability probe.**
- "**Then** it connects to the cTrader demo host … and executes the named verify-or-refuse checks — spot-timestamp-unit assertion, daily-boundary measurement, bar-basis reconciliation, pip-formula validation, money-exponent presence — recording each measured fact and verdict into a per-(VenueId, account) venue-observation profile."
- "**And** the probe stands alone: it depends on no port contract, connection manager, or Epic 3 journal, so it can run as the earliest factory work unit (FR-022, FR-026, SC-02, AR-45)."
- "**Then** both are stored as per-broker configuration in the venue-observation profile, and neither the 17:00-New-York boundary nor the BID basis is hardcoded anywhere in the probe (AR-46, DEC-0135)."
- "**Then** it records the check as unverified/refused rather than defaulting any value, and the dependent evidence class stays unavailable — an unmeasured daily boundary leaves venue daily bars ungoverned (AR-45, edge)."
- "**Then** the credential value is never rendered (only its reference id appears), and no live host is contacted and no order is submitted (FR-025, AR-37, SC-02)."

**Story 8.2 — In-house proto pinned at tag 91.**
- "**Then** it names the Spotware openapi-proto-messages integer release tag 91, and only the proto message definitions (data, not code) are consumed (AR-43, FR-026, DEC-0141)."
- "**Then** the SDK is reference-only, no Spotware code executes in QMX, and the protobuf runtime is declared a dependency of qmf-venue alone (AR-43, AR-06)."
- "**Then** the change mints a new CT-18 capability declaration and forces re-verification …"
- "**Then** it never leaks into qmf-core: default-deny holds, qmf-venue imports only qmf-core, and nothing imports qmf-venue (AR-06, AR-42)."

**Story 8.3 — Secret lifecycle, connection manager, injected-sink wiring.**
- "**Then** it yields only its opaque reference id and never the value, and the tier-1 secret-scan gate rides poe check (FR-025, CT-21, AR-37, NFR-05)."
- "**Then** it cannot — the connection manager is the single value-holder, and no secret crosses back out through a getter, log line, refusal context, health field, or metric label (FR-025, CT-21, AR-37)."
- "**Then** it is stored via atomic replace before the old is discarded; a failed store after rotation is an unavailable-dependency alarm plus a command-pipe block (after-condition = successful store or operator re-provision), the sensing pipe unaffected (FR-025, AR-38, CT-21, edge)."
- "**Then** an unavailable-dependency refusal carries the reference id, never the value; an account-binding record's secret reference is occurrence/display-only and excluded from fp1, and a non-opaque reference construction is an invalid-input refusal (CT-21, edge)."
- "**Then** the writer-holding component blocks the command stream, the sensing pipe is unaffected, and no store is ever written directly rather than through an injected sink (AR-47, CT-21)."

**Story 8.4 — Two-artifact capability discovery + first-connection suite.**
- "**Then** it is static, adapter-version-scoped, and credential-free, carries the venue protocol artifact identity (tag 91), marks every field static or measured-at-connection, and its fingerprint is identity-bearing for any decode that depends on it (FR-022, CT-18)."
- "**Then** the declaration is present at construction and the venue-observation profile must exist before the first command and before any evidence-bearing decode; a measured-at-connection capability consumed before its profile exists is an unavailable-dependency refusal (FR-022, CT-18, AR-45, SC-09)."
- "**Then** the result is a policy-rejection refusal; the venue-observation profile is append-only with supersedes edges and is occurrence/provenance-only, never identity-bearing downstream (CT-18, edge)."
- "**Then** it returns an unsupported-capability refusal and never emulates the capability or widens the scope (CT-18, edge)."
- "**Then** the fail-closed default applies — (transient venue failure, retryable = no, outcome = UNKNOWN) plus an alarm — and a code reads as rejected-by-venue only where the pinned error-map row declares that class (CT-18, edge)."
- "**Then** it becomes a venue-scoped market-hours calendar identity anchoring venue-native BarSpec, while a failed bar-basis reconciliation refuses bar evidence and an absent money exponent refuses that message's money decode (CT-18, AR-46)."

**Story 8.5 — Five typed command kinds under the four-outcome law.**
- "**Then** it is exactly one of place_order, cancel_order, close_position, close_all, amend_protection — typed per kind on qmf-core nouns with no free-form payload; kinds are addable, never redefined, and a fractional or partial close is an unsupported-capability refusal (FR-023, CT-19, AR-44)."
- "**Then** it resolves to exactly one of accepted-by-venue, rejected-by-venue, denied-locally, or UNKNOWN; denied-locally is an outcome and never a refusal, and every outcome mints an observation record and a journal event (FR-023, CT-19)."
- "**Then** it is UNKNOWN — a state, not an error — and a venue-returned error resolves rejected-by-venue only where the CT-18 error table declares that class; a timeout is never read as a rejection (FR-023, CT-19, edge)."
- "**Then** a durable command-id-binding record persists through the injected sink before submission; re-presenting the same command is an idempotent accept, and differing content under a reused identity is refused and alarmed (CT-19, AR-48, edge)."
- "**Then** it is constrained at contract level to risk-non-increasing changes per protection side (the stop side checked against the frozen original_risk_distance), and it is never emulated by cancel-then-place nor widened into a general amend_order (CT-19, edge)."
- "**Then** the parent outcome is the meet of its children — any child UNKNOWN makes the parent UNKNOWN, and any child rejected makes the parent partially-executed, a named outcome that is never a success (CT-19, edge)."

**Story 8.6 — Record-before-interpret events + on-demand reconciliation.**
- "**Then** it is stored verbatim (with mandatory receive wall time and boot-scoped monotonic stamp) and journaled before any state evaluation, and a fill observation's price, quantity, venue instant, and receive instant are mandatory identity fields (FR-024, CT-20, AR-47)."
- "**Then** it is a read-time fold over the observation stream and never a stored field; command outcome and order state are separate streams, and a terminal state is decided only by fills and venue lifecycle events, never inferred from a command outcome or from absence alone (CT-20)."
- "**Then** it is annotated with a typed out-of-sequence edge and forces its owning command to UNKNOWN; adapters never synthesize a venue observation to paper over the gap (CT-20, edge)."
- "**Then** it completes as one ordered unit with a named transaction boundary (atomic or ordered-with-recovery); a partial write is a storage-failure refusal that blocks the command stream and is journaled on recovery (CT-20, AR-47, edge)."
- "**Then** the verdict is one of reconciled, drift, unknown, or out-of-lookback — the fourth so 'I cannot see that far back' is never read as 'the position closed' — and it gates the command pipe only, never the sensing pipe (FR-024, CT-20, SCN-0005)."
- "**Then** it resolves rejected-by-venue (superseded-by-terminal-subject) — a named outcome, never UNKNOWN, never a stream block — and a subject absent or already terminal at submission resolves without submission (CT-20, edge)."

**Story 8.7 — UNKNOWN blocks the command stream until explicit reconciliation.**
- "**Then** it is an explicit observation carrying its trigger (timeout | transport-error | disconnect), the monotonic elapsed measurement, the wall receive instant, and the injected submission deadline in force — whose existence is mandatory but whose value is never QMF's (FR-023, SCN-0005, CT-19)."
- "**Then** the adapter refuses it (transient-venue-failure, after-condition = resolution); the adapter never clears its own block, and no component retries, assumes an outcome, flattens, or invents a terminal state (FR-023, SCN-0005, L35)."
- "**Then** the protection act never evaporates — it stands as a standing protection intent, journaled before dispatch, re-decided (explicitly not retried) against a reconciled verdict only, while drift, unknown, and out-of-lookback verdicts alarm and hold it open without dispatching (SCN-0005, edge)."
- "**Then** the risk-reducing kinds dispatch ahead of place_order on every shared throttle, and suspend-new takes local effect instantly with no venue round-trip (SCN-0005, CT-19)."
- "**Then** the resolution is one of observed-accepted, observed-absent, or operator-attested, the call is itself recorded as an observation, and the block clears on that resolution — never on a reconciliation verdict alone (SCN-0005, CT-19, edge)."

**Story 8.8 — cTrader adapter honoring ratified venue facts as per-broker config.**
- "**Then** it honors per-field Unix-ms UTC timestamps with mandatory receive-time recording (no server clock exists), the 1/100000 market-data wire scale, execution prices as raw doubles crossing the named money-path boundary, and a moneyDigits exponent on the nine money-bearing messages — an absent exponent refusing that message's money decode (FR-026, AR-46, DEC-0135)."
- "**Then** it respects 50 requests/second non-historical plus 5/second historical per connection, adopts the 10-second heartbeat bound, and enforces the one-week historical tick-span cap; demo and live are separate hosts requiring two simultaneous connections (AR-46, DEC-0135)."
- "**Then** heartbeat, token refresh, reconnect, gap replay, and verification monitors are declared schedulable duties the application's scheduler drives, and session recovery never resubmits a command (AR-46, FR-025)."
- "**Then** it measures each per broker at first connection, re-verifies with a continuous monitor, and stores the result as per-broker configuration in the venue-observation profile — never hardcoded (FR-026, AR-46, edge)."
- "**Then** opaque VenueId/AccountId identity and account bindings suffice, no broker is named in code, and the platform stays venue-blind above the port (FR-026, AR-46, AR-42)."

### 2.2 Contract clauses (verbatim, load-bearing invariants)

- **CT-19 four-outcome law:** "every well-formed submission resolves to accepted-by-venue | rejected-by-venue | denied-locally | UNKNOWN; denied-locally is an outcome, never a refusal — typed refusals are reserved for a malformed command, an undeclared capability, and a blocked stream — and every outcome, denied-locally included, mints an observation record and a journal event."
- **CT-19 UNKNOWN trigger:** "A transport error, timeout, or disconnect yields UNKNOWN — a state, not an error; a venue-returned error resolves rejected-by-venue only where the CT-18 error table declares that outcome class, and every other path is UNKNOWN."
- **CT-19 stream = (VenueId, account):** "The command stream — the unit of UNKNOWN blocking, of WriterId ownership, and of the gapless per-writer sequence — is the (VenueId, account) pair … strictly finer than a connection (a shared connection never couples distinct accounts' uncertainty)."
- **CT-19 block:** "While an UNKNOWN is outstanding on a command stream the adapter refuses new commands on that stream (transient-venue-failure, after-condition = resolution); protection commands are not exempt from the block — but a protection act the block refuses NEVER EVAPORATES … and cancel_order, close_position, close_all, and amend_protection dispatch ahead of place_order on every shared throttle."
- **CT-19 no self-clear:** "No QMF component retries, assumes an outcome, flattens, or invents terminal state on UNKNOWN; the adapter never clears its own block — unblocking is an explicit typed resolve_unknown(command identity, resolution in observed-accepted | observed-absent | operator-attested) call by the application … the block is per command and clears on resolution, never on a reconciliation verdict."
- **CT-19 command identity:** "Command identity is the command record's fp1 — including the (VenueId, account) stream qualification, the session epoch, and the caller's opaque ordering ordinal; a venue-native id is never sufficient alone. The CT-18-declared mapping into the venue's client-id field must be injective and total … or a durable command-id-binding record … persists through the sink BEFORE submission."
- **CT-18 error map + fail-closed:** "a venue code reads as rejected-by-venue only where the table declares it, category alone never implies retryability, and every other path is UNKNOWN"; "The unmapped-code default is fail-closed: (transient venue failure, retryable = no, outcome = UNKNOWN) plus an alarm; UNKNOWN is a state, never an error."
- **CT-18 two artifacts + money nullability:** "consuming a measured-but-unverified capability in evidence-bearing work is a policy-rejection refusal"; "an absent money exponent is a refusal, never a default to 2"; "an absent value factor is an unavailable-dependency refusal, never a silent conversion."
- **CT-20 recording precedes interpretation:** "every inbound venue event is stored verbatim (with the mandatory receive stamps) and journaled BEFORE any state evaluation; no state machine gates the immutable store."
- **CT-20 order-state fold:** order state is a "read-time fold over the observation stream … never a gate on recording"; enum "client-submitted | venue-accepted | venue-rejected | UNKNOWN | partially-filled | filled | cancelled | expired | closed-by-venue."
- **CT-20 out-of-sequence:** "An observation with no legal transition is recorded, annotated with a typed out-of-sequence edge, and forces the owning command to UNKNOWN pending resolution; adapters never synthesize venue observations."
- **CT-20 reconciliation:** verdict "reconciled | drift | unknown | out-of-lookback, the fourth term added so that 'I cannot see that far back' is NEVER read as 'the position closed' … Reconciliation gates the command pipe only — the sensing pipe never blocks on it."
- **CT-20 cardinality:** "exactly one journal event per recorded observation, one per submission, one per outcome."
- **CT-21 render guard / single value-holder:** "a SecretValue never renders its value — repr, str, serialization, and logging all yield the reference id"; "The connection manager is the single named component permitted to hold secret values in memory … values never cross back out — no getter, no log line, no refusal context, no health field, no metric label."
- **CT-21 binding identity:** "An account-binding record's identity is (VenueId, AccountId, role, world); its secret reference is declared occurrence/display-only and excluded from fp1."
- **CT-21 rotation:** "the new secret is stored via atomic replace before the old is discarded; a failed store after rotation is an alarm and a command-pipe block (unavailable dependency …) with the sensing pipe unaffected."

### 2.3 Scenario clauses (verbatim, SCN-0005)

- "The submission resolves to `UNKNOWN` — a state, not an error … the observation is recorded verbatim and journaled before any state evaluation (recording precedes interpretation)."
- "While the `UNKNOWN` is outstanding, the adapter refuses new commands on that command stream (`transient venue failure`, after-condition = resolution), and `suspend-new` takes local effect instantly; no QMF component retries, assumes an outcome, flattens, or invents a terminal state. The adapter never clears its own block."
- "a standing protection intent re-evaluates only against a `reconciled` verdict, while `drift`, `unknown`, and `out-of-lookback` **alarm and hold the intent open without dispatching**, so a protection mechanism can never open a position against state it cannot see."
- "Throughout, the sensing pipe never blocks — `UNKNOWN` and reconciliation gate the command pipe only."
- "The 17:00-New-York daily-bar boundary and BID-derived trend bars … are never hardcoded — they are measured per broker at first connection and re-verified by a continuous monitor, stored as per-broker configuration."

---

## Section 3 — Fault-family checklist

The eight families the Epic 20–23 reviews found. "None" is a result.

| # | Family | Member in Epic 8? | Where / how it manifests |
| - | ------ | ----------------- | ------------------------ |
| a | Unit-kind / currency treated as optional on a numeric path | **YES** | Money decode: `moneyDigits`/money exponent may be absent (CT-18/AR-46 require refusal, "never a default to 2"); `value_factor` money-per-price-delta may be absent (unavailable-dependency, "never a silent conversion"); account `settlement_currency` vs Book `accounting_currency` mismatch is a bind-time policy-rejection. Sites: `capabilities.py`, `events.py`, `ctrader.py` decode path. **L2-003, L3-010.** |
| b | An exception where a typed refusal was contracted | **YES** | SCN-0005 Given: "every public venue boundary succeeds or returns a typed refusal." R-002 universal claim over the venue export surface. **L1-001.** |
| c | A fingerprint that omits a distinguishing input | **YES** | Command fp1 must include (VenueId, account) stream qualification, session epoch, ordering ordinal (CT-19); the capability *declaration* fingerprint is identity-bearing but the venue-observation *profile* must be excluded (occurrence-only); the account-binding `secret_ref` must be excluded from fp1; occurrence fields (receive stamps, monotonic, epochs, correlation_id) must never enter identity. **L1-003.** |
| d | A governance gate implemented at one input shape | **YES** | The error-map / four-outcome resolution is the gate; the fail-closed unmapped-code default must hold over *every* unmapped (code, context) pair, not one; the UNKNOWN block must hold over *all five* command kinds on the stream (protection not exempt). **L2-002, L2-007/008, L3-001.** |
| e | An external input trusted without validation | **YES** | Venue wire is the untrusted edge: raw `double` execution prices, uint64 `1/100000` market-data wire scale, unmapped venue error codes, foreign floats, non-opaque secret refs. Each must bound-and-check / refuse: unmapped code → fail-closed UNKNOWN + alarm; absent money exponent → refuse; absent value factor → refuse; non-opaque `secret_ref` construction → invalid-input refusal. **L1-004, L1-005, L2-002/003, L2-020.** |
| f | A capability reachable from one door only | **None (for door parity).** | qmf-venue sits *below* the door surface (no CLI/MCP door on this package; door parity is E16/AR-58). The analogous discipline here is R-009 register reconciliation — see (g)/register test **L3-015**. Recorded as "none" for the door-parity sense. |
| g | A ledger or journal line missing on a failure path | **YES** | CT-20 cardinality: "exactly one journal event per recorded observation, per submission, per outcome" — *including* `denied-locally`, `UNKNOWN`, and the partial multi-room write (storage-failure blocks the stream **and is journaled on recovery**). A failure path that mints no journal event is the defect. **L2-007, L2-015, L2-018.** |
| h | An existing test that pins the implementation rather than the requirement | **SUSPECT — to be confirmed in Section 5.** | 99.13% line coverage is author-written (R-003). The state-machine transition laws, the UNKNOWN-block stateful behaviour, and "market data keeps flowing" are precisely what line coverage cannot see (test-design-qa.md §"Where independent tests still matter", qmf-venue row). High risk that `test_blocking_ct19.py` / `test_events_ct20.py` pin the code's fold rather than the contract's matrix. |

---

## Section 4 — Independent test list

> **Authored before any `src/` implementation body was read.** Reading a public
> signature to *call* it is permitted afterwards; reading a body before this
> table existed was not. Test ID = `QA-E08-L<level>-<seq>`. Oracle = the exact
> document + clause (never the code). Duplicate-coverage guard applied: a
> contract fact lives at L2 and is not restated at L3; an epic-specific behaviour
> lives at L3; the cross-package journey lives at L4.

### L1 — Property tests (`hypothesis`); oracle = a contract/law invariant, quantified

| Test ID | Requirement | Level | Oracle | Pri | Assertion (one sentence) |
| ------- | ----------- | ----- | ------ | --- | ------------------------ |
| QA-E08-L1-001 | FR-004, CT-04, AR-13, R-002 | L1 | SCN-0005 Given ("every public venue boundary succeeds or returns a typed refusal"); CT-19 refusal invariant | P0 | Every public callable enumerated from the `qmf.venue` export surface returns a value or a typed refusal and never raises for any generated well-typed input. |
| QA-E08-L1-002 | FR-025, CT-21, AR-37, L34, NFR-05, R-019 | L1 | CT-21 invariant ("repr, str, serialization, and logging all yield the reference id") | P0 | A `SecretValue` yields only its opaque reference id under `repr`, `str`, every serialization path, and logging, for every generated value — the value string never appears. |
| QA-E08-L1-003 | FR-023, CT-19, CT-20, AR-52 | L1 | CT-19 command-identity invariant; CT-20 occurrence-exclusion list | P1 | Two command records differing in any identity input ((VenueId, account), session epoch, ordering ordinal, kind, params) produce distinct fp1, while records differing only in occurrence fields (receive stamps, monotonic, epochs, correlation_id) produce identical fp1. |
| QA-E08-L1-004 | FR-026, CT-18 (float_target_scales), CT-19 units, DEC-0141 | L1 | CT-18 "a foreign binary float is never identity … crosses AD-7's named boundary … to a scaled integer at the CT-18-declared target scale" | P1 | For every generated foreign float, crossing the money-path boundary yields a scaled integer at the declared target scale with the declared rounding mode, no binary float ever appears in command parameters or identity, and the raw float survives only as integrity-checked provenance. |
| QA-E08-L1-005 | FR-025, CT-21, AD-9 | L1 | CT-21 secret_ref opacity invariant | P2 | Constructing a `SecretRef` from any input that encodes venue, broker, account, environment, or key material is an invalid-input refusal, and minted ids are stable and never reused. |

### L2 — Contract tests; oracle = the CT-* YAML clause

| Test ID | Requirement | Level | Oracle | Pri | Assertion (one sentence) |
| ------- | ----------- | ----- | ------ | --- | ------------------------ |
| QA-E08-L2-001 | FR-022, CT-18 | L2 | CT-18 invariants (two-artifact split) | P1 | The capability declaration is static, credential-free, adapter-version-scoped, carries tag-91 protocol identity with every field marked static\|measured-at-connection and an identity-bearing fingerprint; the venue-observation profile is per-(VenueId, account), append-only with supersedes edges, occurrence/provenance-only and never identity-bearing downstream. |
| QA-E08-L2-002 | FR-022, CT-18, CT-19 | L2 | CT-18 error-map + fail-closed default | **P0** | An unmapped (venue code, context) pair resolves fail-closed to (transient-venue-failure, retryable=no, UNKNOWN) plus alarm, and a code resolves rejected-by-venue only where the pinned error-map row declares that class — category alone never implies retryability. |
| QA-E08-L2-003 | FR-026, CT-18, AR-46 | L2 | CT-18 nullability clauses | **P0** | An absent money exponent refuses that message's money decode (never defaults to 2), an absent value factor is an unavailable-dependency refusal (never a silent conversion), an unmeasured settlement currency is unavailable-dependency, and a settlement currency not matching the Book's accounting_currency is a bind-time policy-rejection. |
| QA-E08-L2-004 | FR-022, CT-18, AR-45 | L2 | CT-18 fixed-wiring-order invariant | P1 | A measured-at-connection capability consumed before its venue-observation profile exists is an unavailable-dependency refusal, and a measured-but-unverified capability consumed in evidence-bearing work is a policy-rejection refusal. |
| QA-E08-L2-005 | FR-022, CT-18 | L2 | CT-18 unsupported-invocation invariant | P1 | Invoking an undeclared capability, an undeclared order parameter, or an unsupported close scope returns an unsupported-capability refusal and is never emulated or widened to a broader scope. |
| QA-E08-L2-006 | FR-023, CT-19, AR-44 | L2 | CT-19 command-vocabulary invariant | P1 | The command vocabulary is exactly {place_order, cancel_order, close_position, close_all, amend_protection} typed on core nouns with no free-form payload; a fractional or partial close is an unsupported-capability refusal; a kind-inappropriate field is an omitted key, never null. |
| QA-E08-L2-007 | FR-023, CT-19, L35 | L2 | CT-19 four-outcome-law invariant | **P0** | Every well-formed submission resolves to exactly one of {accepted-by-venue, rejected-by-venue, denied-locally, UNKNOWN}; denied-locally is an outcome and never a refusal; and every outcome (denied-locally included) mints exactly one observation record and one journal event. |
| QA-E08-L2-008 | FR-023, CT-19, L35 | L2 | CT-19 UNKNOWN-trigger invariant | **P0** | A transport error, timeout, or disconnect resolves UNKNOWN (a state, not an error), and a venue-returned error resolves rejected-by-venue only where the CT-18 table declares that class — a timeout is never read as a rejection. |
| QA-E08-L2-009 | FR-023, CT-19, DEC-0148 | L2 | CT-19 amend_protection invariant | **P0** | amend_protection is constrained to risk-non-increasing changes per protection side (stop side checked against the frozen original_risk_distance, binding the stop side only), is never emulated by cancel-then-place, and is never widened into a general amend_order. |
| QA-E08-L2-010 | FR-023, CT-19 | L2 | CT-19 compound-command invariant | P1 | A compound command's parent outcome is the meet of its children — any child UNKNOWN makes the parent UNKNOWN, any child rejected makes the parent partially-executed (a named outcome, never a success) — and each child is individually observation- and journal-bearing. |
| QA-E08-L2-011 | FR-023, CT-19, AR-48 | L2 | CT-19 command-id-mapping invariant | P1 | Where the CT-18 mapping into the venue client-id field is not injective-and-total, a durable command-id-binding record persists through the injected sink before submission; re-presenting the same command is an idempotent accept and differing content under a reused identity is refused and alarmed. |
| QA-E08-L2-012 | FR-024, CT-20, AR-47 | L2 | CT-20 recording-precedes-interpretation invariant | **P0** | Every inbound venue event is stored verbatim with mandatory receive wall time and boot-scoped monotonic stamp and journaled before any state evaluation, and a fill observation's price, quantity, venue instant, and receive instant are all mandatory identity fields. |
| QA-E08-L2-013 | FR-024, CT-20 | L2 | CT-20 order-state-fold invariant | P1 | Order state is a read-time fold over the observation stream and never a stored field, command outcome and order state are separate streams, and a terminal state is decided only by fills and venue lifecycle events — never inferred from a command outcome or from absence alone. |
| QA-E08-L2-014 | FR-024, CT-20 | L2 | CT-20 out-of-sequence invariant | P1 | An observation with no legal transition is recorded, annotated with a typed out-of-sequence edge, and forces its owning command to UNKNOWN, and no adapter synthesizes a venue observation to paper over the gap. |
| QA-E08-L2-015 | FR-024, CT-20, AR-47 | L2 | CT-20 multi-room-write invariant | P1 | A multi-room write completes as one ordered unit with a named transaction boundary (atomic\|ordered-with-recovery), and a partial write is a storage-failure refusal that blocks the command stream and is journaled on recovery. |
| QA-E08-L2-016 | FR-024, CT-20, SCN-0005 | L2 | CT-20 reconciliation-verdict invariant | **P0** | A reconciliation verdict is one of {reconciled, drift, unknown, out-of-lookback}, out-of-lookback is never read as position-closed, and reconciliation gates the command pipe only and never the sensing pipe. |
| QA-E08-L2-017 | FR-024, CT-20, DEC-0148 | L2 | CT-20 subject-terminal-resolution invariant | P1 | A close_position/close_all/amend_protection whose subject is observed terminal at or after the submit stamp resolves rejected-by-venue (superseded-by-terminal-subject) — a named outcome, never UNKNOWN, never a stream block — and a subject absent or already terminal at submission resolves without submission. |
| QA-E08-L2-018 | FR-024, CT-20 | L2 | CT-20 cardinality invariant | P1 | The (command kind × outcome) and (observation kind) → journal-event mappings are exhaustive and total, minting exactly one journal event per recorded observation, per submission, and per outcome. |
| QA-E08-L2-019 | FR-025, CT-21 | L2 | CT-21 binding-identity invariant | P1 | An account-binding record's fp1 is (VenueId, AccountId, role, world) and excludes its secret reference as occurrence/display-only. |
| QA-E08-L2-020 | FR-025, CT-21, AR-37 | L2 | CT-21 single-value-holder invariant | **P0** | No secret value crosses out of the connection manager through any getter, log line, refusal context, health field, or metric label, and a missing/expired/rejected credential is an unavailable-dependency refusal carrying the reference id and never the value. |
| QA-E08-L2-021 | FR-025, CT-21, AR-38 | L2 | CT-21 rotation invariant | P1 | On rotation the new secret is stored via atomic replace before the old is discarded, and a failed store after rotation is an alarm plus a command-pipe block (after-condition = successful store or operator re-provision) with the sensing pipe unaffected. |
| QA-E08-L2-022 | FR-025, CT-21, CT-19 | L2 | CT-21 one-writer / session-epoch invariant | P2 | Exactly one live refresher exists per credential, a session-epoch id distinct from the boot epoch rides every venue observation, and the per-writer sequence resets only on boot with a cursor durable through the observation sink. |

### L3 — Acceptance tests; oracle = the `epics.md` AC / SCN-0005 sentence (epic-specific behaviour only)

| Test ID | Requirement | Level | Oracle | Pri | Assertion (one sentence) |
| ------- | ----------- | ----- | ------ | --- | ------------------------ |
| QA-E08-L3-001 | FR-023, SCN-0005, L35, CT-19 | L3 | Story 8.7 AC-2; SCN-0005 Then | **P0** | With an outstanding UNKNOWN on a (venue, account) stream, a new command on that stream is refused (transient-venue-failure, after-condition = resolution), and the adapter never clears its own block. |
| QA-E08-L3-002 | FR-024, SCN-0005, CT-20 | L3 | SCN-0005 Then ("the sensing pipe never blocks") | **P0** | While an UNKNOWN (or any reconciliation) gates the command pipe, the sensing/market-data pipe keeps flowing and never blocks. |
| QA-E08-L3-003 | FR-023, SCN-0005, CT-19 | L3 | Story 8.7 AC-1 | **P0** | An UNKNOWN is minted as an explicit observation carrying its trigger (timeout\|transport-error\|disconnect), the monotonic elapsed measurement, the wall receive instant, and the injected submission deadline in force — the deadline's existence mandatory, its value never QMF's. |
| QA-E08-L3-004 | FR-023, SCN-0005, CT-19 | L3 | Story 8.7 AC-5 | **P0** | resolve_unknown(command identity, resolution ∈ {observed-accepted, observed-absent, operator-attested}) is itself recorded as an observation and clears the block only on that resolution — never on a reconciliation verdict alone. |
| QA-E08-L3-005 | FR-023, SCN-0005 | L3 | Story 8.7 AC-3; SCN-0005 Then | **P0** | A protection act refused by the block never evaporates: it stands as a standing protection intent, journaled before dispatch, re-decided (not retried) only against a reconciled verdict, while drift/unknown/out-of-lookback alarm and hold it open without dispatching. |
| QA-E08-L3-006 | FR-023, SCN-0005, CT-19 | L3 | Story 8.7 AC-4 | P1 | The risk-reducing kinds (cancel_order, close_position, close_all, amend_protection) dispatch ahead of place_order on every shared throttle, and suspend-new takes local effect instantly with no venue round-trip. |
| QA-E08-L3-007 | FR-023, SCN-0005, L35, DEC-0150 | L3 | Story 8.7 AC-2; SCN-0005 Then (flatten authority) | **P0** | No QMF component retries, assumes an outcome, flattens, or invents a terminal state on UNKNOWN, and the venue adapter never initiates a flatten (its adapter_self actions are limited to suspend_new, drain, throttle, session state). |
| QA-E08-L3-008 | FR-024, CT-20 | L3 | Story 8.6 AC-3; CT-20 order-state enum | **P0** | Enumerating CT-20's declared transition graph, every (from-state, observation-kind) pair absent from the matrix, when folded, produces a typed out-of-sequence edge and forces the owning command to UNKNOWN — never a silent accept and never a synthesized observation. *(The state-machine matrix line coverage cannot reach.)* |
| QA-E08-L3-009 | FR-026, AR-46, DEC-0135 | L3 | Story 8.8 AC-1 | **P0** | The adapter decodes per-field Unix-ms UTC with mandatory receive-time recording, the 1/100000 wire scale, execution prices as raw doubles crossing the named money-path boundary, and a moneyDigits exponent on the nine money-bearing messages — an absent exponent refusing that message's money decode. |
| QA-E08-L3-010 | FR-026, AR-46, DEC-0135 | L3 | Story 8.8 AC-4; Story 8.1 AC-2 | P1 | The 17:00-New-York daily boundary and BID trendbar basis are measured per broker and stored as per-broker configuration in the venue-observation profile, and neither is hardcoded anywhere in the probe or adapter. |
| QA-E08-L3-011 | FR-022, CT-18, AR-45, SC-02 | L3 | Story 8.1 AC-1/AC-3 | P1 | The first-connection probe records each verify-or-refuse check's measured fact and verdict into a per-(VenueId, account) profile, records an unpassable check as unverified/refused rather than defaulting any value, and stands alone (no port contract, connection manager, or journal dependency) — driven by an injected fake transport, never a live host. |
| QA-E08-L3-012 | FR-025, AR-37, SC-02 | L3 | Story 8.1 AC-4 | P1 | The probe renders only the credential reference id (never the value), contacts no live host, and submits no order. |
| QA-E08-L3-013 | FR-025, AR-47, CT-21 | L3 | Story 8.3 AC-5 | P1 | When an injected core sink (ObservationSink\|JournalSink\|RecordSink\|SecretStore) returns a storage-failure refusal, the writer-holding component blocks the command stream, the sensing pipe is unaffected, and no store is ever written directly rather than through the injected sink. |
| QA-E08-L3-014 | FR-026, AR-06, AR-42, AR-43 | L3 | Story 8.2 AC-2/AC-4; DEPENDENCIES.md | P1 | qmf-venue imports only qmf-core, nothing imports qmf-venue, protobuf is declared only in qmf-venue's pyproject, and no compiled proto message leaks into qmf-core (structural import/dependency test). |
| QA-E08-L3-015 | NFR-11, R-009 | L3 | NFR-11 register-discipline clause | P1 | Every typed refusal reachable at the venue boundary — enumerated from CT-18/19/20/21 refusal categories (invalid-input, unsupported-capability, unavailable-dependency, policy-rejection, transient-venue-failure, storage-failure) — has a register entry stating class, detection, recovery semantics, degraded state, notification tier, and product-user affordance; a missing entry is a finding. |
| QA-E08-L3-016 | FR-023, CT-19, AR-46, DEC-0135 | L3 | Story 8.8 AC-2/AC-3 | P2 | The adapter respects 50/5 req/s per connection, the 10-second heartbeat bound, and the one-week historical tick-span cap, treats demo and live as separate hosts (two connections), and its session recovery never resubmits a command. |
| QA-E08-L3-017 | FR-022, AR-43, DEC-0141 | L3 | Story 8.2 AC-1/AC-3 | P2 | The venue protocol artifact names Spotware openapi-proto-messages integer tag 91 consuming only proto message definitions (data, not code), and a tag change mints a new CT-18 capability declaration and forces re-verification. |

### L4 — Scenario test; oracle = the SCN-0005 prose walkthrough (cross-package journey only)

| Test ID | Requirement | Level | Oracle | Pri | Assertion (one sentence) |
| ------- | ----------- | ----- | ------ | --- | ------------------------ |
| QA-E08-L4-001 | SCN-0005, FR-023, FR-024, CT-19, CT-20, L35 | L4 | `docs/scenarios/SCN-0005-*.md` | P1 | End to end over qmf-core nouns, injected sinks, and a fake cTrader transport: a lost-certainty submission resolves UNKNOWN, records-before-interpret, blocks its (venue, account) command stream, keeps the sensing pipe flowing, preserves a refused protection act as a standing intent, and clears only on an explicit resolve_unknown. |

**Planned counts — L1: 5 · L2: 22 · L3: 17 · L4: 1 (45 planned rows; each L2/L3 family expands to several cases at implementation).**

---

## Section 5 — Existing-test audit

Author-written suites in `packages/qmf-venue/tests/` (99.13%/96.99% coverage is theirs). For every requirement in Section 2, the lane names the covering test and classifies it **keep** / **suspect** / **contradicts**; every "contradicts" row goes to `findings.csv` with the requirement id (this is where R-003 gets its evidence). Existing modules and their audit mandate:

| Existing test module | Requirements it claims | Audit focus (classify per requirement) |
| -------------------- | ---------------------- | -------------------------------------- |
| `test_commands_ct19.py` | FR-023, CT-19 (five kinds, four-outcome) | Confirm it asserts *totality* (every well-formed submission resolves to one of four) and denied-locally-is-an-outcome, not just the happy accept path. Suspect if it enumerates only kinds it constructed. |
| `test_blocking_ct19.py` | FR-023, SCN-0005, L35 (UNKNOWN block) | **Highest suspicion (family h).** Confirm it asserts the block refuses across *all five* kinds and that the sensing pipe keeps flowing, not just that one place_order is refused. Confirm resolve_unknown, not a reconciliation verdict, clears it. |
| `test_events_ct20.py` | FR-024, CT-20 (fold, out-of-sequence, reconciliation) | Confirm the transition matrix is asserted against the *contract enum*, not the code's fold; confirm out-of-lookback ≠ position-closed. Suspect if the illegal-transition set is hand-picked rather than enumerated. |
| `test_capabilities_ct18.py` | FR-022, CT-18 (two artifacts, error map) | Confirm the fail-closed unmapped-code default and the money-exponent/value-factor/settlement refusals are asserted, not only the declared-capability happy path. |
| `test_connection_ct21.py` | FR-025, CT-21, AR-37/38 (secret boundary) | Confirm no-leak is asserted across getter/log/refusal-context/health/metric (not just repr), and rotation store-before-discard with the failed-store command-pipe block. |
| `test_probe_ct18.py` | FR-022, AR-45, SC-02 (probe) | Confirm verify-or-refuse records unverified rather than defaulting; confirm no live host is contacted (injected transport). |
| `test_ctrader_dec0135.py` | FR-026, AR-46 (venue facts) | Confirm the daily boundary / BID basis are read from the profile, not hardcoded — grep the module for literal `17:00`/`BID`/`America/New_York` as a contradiction signal. |
| `test_proto_tag91.py` | AR-43, DEC-0141 (tag 91) | Confirm tag 91 pin + protobuf scoping; keep unless it imports Spotware SDK code. |
| `test_venue.py` | cross-cutting | Classify per assertion. |

R-002/no-raise and R-019/render are **L1 universal** claims the existing per-behaviour tests cannot make; they are net-new independent tests regardless of the audit outcome.

---

## Section 6 — Mutation targets (`mutmut` roster)

Inclusion rule: a surviving mutant here would leave a money or governance claim unasserted.

| Module | Justification |
| ------ | ------------- |
| `commands.py` | The four-outcome resolution and amend_protection risk-non-increasing check are the governance core; a survivor means an outcome or a risk-increase slips unasserted. |
| `events.py` | The read-time fold, out-of-sequence detection, subject-terminal resolution, and reconciliation-verdict vocabulary; a survivor means an illegal transition or an out-of-lookback ≡ closed confusion goes uncaught. |
| `blocking.py` | The UNKNOWN stream block and its clear-only-on-resolve logic; a survivor means the live-money block can be bypassed. |
| `capabilities.py` | The error-map fail-closed default and the money-exponent / value-factor / settlement refusals; a survivor means a foreign value or unmapped code passes silently. |
| `connection.py` | The single-value-holder / render-guard / rotation-block logic; a survivor means a secret can leak or a rotation failure not block. |
| `ctrader.py` — money-decode path only | The foreign-float boundary and moneyDigits handling; a survivor means a float or an absent exponent enters the money path. |

**Excluded** (the rule excludes reports/formatting): `_bench.py`, `proto.py` (compiled proto *data*, not behaviour), `probe.py` reporting/formatting, and any pure rendering helper.

---

## Section 7 — Deferred and out of scope

| Item | Disposition | Reference |
| ---- | ----------- | --------- |
| Live cTrader interaction (real connection, real order) | **OUT OF SCOPE** — no credentials in a verification phase; "a real order is a real order." All venue tests use injected fake transports/sinks. The port is verified against CT-18..CT-21 and recorded venue facts at the seam. | test-design-qa.md "Not in Scope"; DEC-0135/0139/0141 |
| Measured-at-connection *values* (daily-boundary measurement, bar-basis reconciliation, pip-formula validation, amend-atomicity establishment) | **UNPROVEN / DEFERRED** — the verify-or-refuse *interface* is tested (L3-011); the actual measured verdicts need a live connection. Proof-map = UNPROVEN with reason. | CT-18 verification_suite; AR-45 |
| Reconciliation-verdict *consequences*, flatten severity policy, which effect fires at which severity | **OUT OF SCOPE** — node/BMS/trading-node authority, a pointer to `tracker/trading-node-notes.md`, deliberately not QMF contract surface. | DEC-0142, DEC-0150; CT-19/CT-20 |
| Latency numeric budgets (six-stage decomposition) | **DEFERRED (measure-then-budget)** — no budgets exist; only the negative "a wall-computed rung is refused as a baseline" is asserted; no number is invented. | CT-18 latency clause; NFR-04 |
| Store mechanics / key custody (systemd-creds-class on the VPS) | **OUT OF SCOPE** — deployment/ops sitting, not QMF contract surface. | CT-21 |
| Ubuntu tier-1 platform verification | **DEFERRED** — Ubuntu untested until a remote exists; Windows 11 x86-64 is the platform. | AR-23 |
| Secret-scan / CVE / AI-defect re-scan | **OUT OF SCOPE** — Skylos already 100/A+; consumed as L0 evidence; one L1 render property only. | test-design-qa.md "Not in Scope"; R-019 |

---

## Section 8 — Findings (authored while writing this plan; **no fixes**)

Appended to `qa/_trace/findings.csv`. Reproducers are directory/documentary — no `src/` body was read.

| Finding ID | Requirement | Severity | Reproducer | Description |
| ---------- | ----------- | -------- | ---------- | ----------- |
| F-E08-001 | NFR-11, AR-21/L27 | Medium | `ls packages/qmf-venue/` → `pyproject.toml README.md src tests` (no `FAILURES.md`) | The qmf-venue distribution unit ships **no `FAILURES.md`** — the failure-register discipline required of every distribution unit is absent. **Not created here** (per lane constraint); recorded as a finding for the fix-card backlog. |
| F-E08-002 | AR-21, L27 | Low–Medium | `ls packages/qmf-venue/` shows no `examples/` directory | The package ships **no `examples/` directory**, against the tier-1 reference-usage-examples obligation. (`_bench.py` is present, so the benchmark artifact exists.) |
| F-E08-003 | FR-023, CT-19, CT-20 | Info (testability) | CT-19/CT-20 `consumers: []`, `caller_status: unassigned` | The four-outcome-law caller is deliberately unassigned in QMF (wiring is factory-mediated). Consequence for verification: there is no in-tree consumer to drive the command law, so every L2/L3/L4 test must inject a caller and a fake transport. Not a defect — a testability note that shapes the suite. |
| F-E08-004 | R-003, FR-023, SCN-0005 | Info (to confirm in §5) | test-design-qa.md qmf-venue row; coverage 99.13% author-written | The UNKNOWN-block, the state-machine transition matrix, and "market data keeps flowing" are exactly what line coverage cannot see; high prior that `test_blocking_ct19.py`/`test_events_ct20.py` pin the code's fold rather than the contract's matrix. Elevated to a confirmed finding only if the Section 5 audit yields a "contradicts" or "suspect" row. |

**Lane completion criterion (template):** all eight sections present; every Section 4 test exists and has run (pass or fail); Section 5 covers every Section 2 requirement; the L6 requirements-fidelity seat has reviewed the lane; every finding is in the inventory.
