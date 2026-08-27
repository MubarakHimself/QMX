# Verification PLAN — Epic 10: qmf-risk (Books, BMS & governance)

- Tier: **T1** (highest-scrutiny / highest-damage epic)
- Package under audit: `packages/qmf-risk` (`src/qmf/risk/`)
- FRs in scope: FR-027, FR-028, FR-029, FR-030, FR-031, FR-032, FR-033, FR-034, FR-035
- Contracts in scope: CT-22 (Book def), CT-23 (risk-eval door), CT-24 (Book mode), CT-25 (risk/entity journal), CT-27 (BMS def), CT-28 (Book binding), CT-29 (exit record), CT-30 (control action), CT-31 (control window), CT-32 (performance result)
- Constitution law in scope: L38 (configurable = UI-editable), L39 (exit-preservation invariant)
- Golden scenarios in scope: SCN-0006, SCN-0008, SCN-0010, SCN-0011 (SCN-0005 partial, standing-intent path)
- Author discipline: **Section 4 was written from requirements only, before opening any `src/` file of `qmf-risk`.** Sections 5–8 reconcile that fixed list against source.

> Template note (load-bearing): the canonical per-epic template lives in
> `_bmad-output/test-artifacts/test-design-qa.md` and the 15 P0/P1 assertions + risk-gate rows in
> `_bmad-output/test-artifacts/test-design/QMX-handoff.md`. **Neither file exists in this worktree**
> (confirmed by full-tree search — the `_bmad-output/test-artifacts/` directory is absent). This plan
> therefore follows the per-epic shape and L0–L6 rules the task prompt states verbatim (8 sections,
> order load-bearing; Section 4 = independent requirements-derived test list authored before any
> `src/` read; one behaviour → one level, lower level wins), and takes the gate rows (R-001, R-009)
> and P0 assertions 8/9 from the task prompt. If the two authority files are later restored, this plan
> must be re-reconciled against them — recorded as a blocked input in Section 7.

---

## Section 1 — Epic scope, authorities, and audit posture

**What the epic asserts (one line).** Every bot trade intent passes a Book's charter doors; the BMS
accounts for and constrains its Books but never trades, sizes, or reaches inside a Book; exits are
Book-owned and preserved; and performance measurement publishes and never acts.

**Authorities, in precedence order (as read):**
1. `epics.md` Epic 10 (Stories 10.1–10.10, ~60 acceptance criteria).
2. `docs/` knowledge base: CT-22..CT-25, CT-27..CT-32; `constitution.md` L38/L39; `ct-04-typed-refusal.yaml`
   (the seven-category register); scenarios SCN-0006/0008/0010/0011.
3. `test-design-qa.md` L0–L6 architecture — **absent** (template shape reconstructed from prompt).
4. `QMX-handoff.md` P0/P1 assertions + risk-gate rows — **absent** (P0-8, P0-9, R-001, R-009 taken from prompt).

**Audit posture (binding).** Source is READ-ONLY evidence. A failing planned assertion is a FINDING
recorded against the requirement — never a source edit and never a weakened test. Tests assert what the
contracts and constitution demand, not what the code happens to do.

**Defined-unwired caveat (critical for a risk audit).** Every Epic-10 contract is stamped
`wiring_status: defined-unwired` — "no code exists; records reach the registry / qmf-data only through the
composition root; no wiring is authorized from this doc." Two consequences the plan must carry:
- Where the factory has since implemented a contract's logic (control_action.py demonstrably exists —
  see Section 2 hot-spot), the planned assertions run against real code.
- Where a contract is still genuinely unwired, the planned assertion cannot execute at runtime; its
  outcome is a **coverage FINDING** ("requirement R has no implementing code / no executable path"),
  logged against the requirement, not a silent skip. Section 8 makes the runnable/blocked split explicit
  during the reconcile pass.

**qmf-risk is imported by nothing (AR-06, default-deny).** CT-22/CT-27 et al. are defined on qmf-core
nouns; qmf-risk imports only qmf-core and is imported by no package. Cross-package integration is
composition-root-mediated, so L3 integration tests here wire through **in-test composition-root fakes /
injected sinks**, never a real import edge from another package into qmf-risk.

---

## Section 2 — Risk assessment and gate rows

### Risk-gate rows (must-pass, T1)

| Gate | Statement | Requirement anchors | Planned test IDs | Level |
|------|-----------|---------------------|------------------|-------|
| **R-001** | Mixed unit-kind / currency refuses on the money path (never a silent conversion) | 10.1 AC2/AC4, 10.2 AC4–AC6, CT-22 dimensional law, CT-23 Money↔R rate, CT-28 settlement currency, CT-01 float ban, AD-40 | A4, A6, A9, A10, B12, B13, B15, C8, D8, I3, X3 | L1/L2 |
| **R-009** | Every door-reachable typed refusal has a register entry | CT-04 seven categories, all CT-22..CT-32 refusal-category enums | X1, X2 | L1/L2 |

### P0 assertions (from prompt; handoff absent)

| # | Assertion | Anchors | Discharged by |
|---|-----------|---------|---------------|
| **P0-8** | Every trade intent passes the Book charter doors with R **frozen at admission** and a **declared full-loss price required** | FR-027, FR-028, CT-22, CT-23 | B2, B3, B4, B6, F1, F3, X4 |
| **P0-9** | **No control ever blocks a risk-reducing act** | FR-033, CT-30, L39 | H1, H2, H8, H9 |

### Epic-specific damage ranking (why T1)

1. **Exit-preservation (L39 / P0-9)** — the single invariant whose violation traps risk behind our own
   protection. Highest damage. Verified as a **property** over the full (control-kind × authority × scope
   × risk-reducing-act) space, not by enumerated examples (H1).
2. **R frozen + full-loss-price-required (P0-8)** — a re-based R or an admitted no-stop entry silently
   corrupts every downstream −1R meaning and every bench/decay verdict.
3. **Same-tick arbitration (SCN-0010)** — the standing invariant "a higher rank never reduces the
   protection a lower rank would deliver" is the kill-line's whole reason to exist; the compose case
   (`suspend_new + flatten` both execute) is the exact trap.
4. **Currency / dimensional refusals (R-001)** — a silent non-USD conversion or an implicit Money↔R
   crossing is "the one error no report shows" (CT-28).

### Complexity hot-spot (pin by requirement, not by line)

`packages/qmf-risk/.../control_action.py` is the worst complexity hot-spot in the repo (cyclomatic 38).
**Behaviour there is pinned by requirement, never by line-chasing:** the arbitration collapse/conflict/
compose rules (H7, H8), the exit-preservation property (H1), scope resolution refuse-never-widen (H4),
flatten-authority closure (H9), and the standing-intent fold (H5) are each asserted from CT-30 / SCN-0010
text. The cyclomatic number raises the *priority* of these tests and flags branch-coverage as a Section-8
exit criterion; it does not change what is asserted.

---

## Section 3 — Test-level strategy (L0–L6)

Levels applied per the prompt's architecture ("one behaviour → one level; lower level wins"). Reconstructed
level semantics (canonical file absent):

- **L0 — static gates.** ruff, pyright-strict, the money-path float scanner and ambient-nondeterminism
  scanner (NFR-02), and the dependency-direction check (AR-06: qmf-risk imports only qmf-core, imported by
  nothing). Reported separately, not counted in the L1–L4 tally.
- **L1 — pure unit.** One value-type invariant, one formula, or one typed refusal on a single function —
  no fakes, no wiring. Frozen-R faces, unit-kind checks, discriminated-union thresholds, `realized_r`
  derivation, formula worked-examples.
- **L2 — contract-surface / component.** A whole contract's surface proven inside qmf-risk with in-memory
  fakes: admission ordering, arbitration collapse/conflict, the exit-preservation property, the
  widen-never-shrink window fold, journal projections, register conformance.
- **L3 — integration (composition-root fakes).** Behaviours that need ordering/persistence across records
  or streams: recording-precedes-interpretation (stale evidence), standing-intent re-decide on reconnect,
  storage-failure-blocks-dispatch, and the P0-8 admitted-entry lifecycle.
- **L4 — golden scenario.** Executable end-to-end fixtures for SCN-0006, SCN-0008, SCN-0010, SCN-0011.
- **L5 / L6 — NFR & adversarial/property fuzz.** Mostly out of Epic-10 functional scope; the one L6-flavored
  item (exit-preservation property fuzz) is folded into H1 at L2 with Hypothesis. Import-time / benching
  perf (NFR-04) is a platform/QMB concern, not asserted here.

Assignment rule applied: a behaviour provable at L1 is never re-asserted at L2+; the golden scenarios (L4)
re-exercise already-unit-covered behaviour only as end-to-end journeys, not as the primary proof.

---

## Section 4 — Independent test list (authored from requirements, before any `src/` read)

Legend: level in brackets; anchors cite Story.AC / CT / gate. IDs are stable.

### A. Template grammar, dimensional law, USD numeraire (Story 10.1) — R-001

- **A1 [L1]** A variable missing any of {unit_kind, value, ui_editable, admission_impact} → `invalid input`. (10.1 AC1, CT-22)
- **A2 [L1]** `unit_kind` must be drawn from the closed AD-40 vocabulary; an out-of-vocabulary kind → `invalid input`. (10.1 AC1)
- **A3 [L1]** Every variable `value` is exact-rational / scaled-integer; a binary float on any variable is a taint/refusal. (10.1 AC1, CT-01)
- **A4 [L1]** Dimensional checker: a formula declares the unit-kind of every input and its output and refuses on mismatch. (10.1 AC2) — **R-001**
- **A5 [L1]** Every formula ships an executable worked example; recomputation equals the declared result. (10.1 AC2)
- **A6 [L1]** The dead FORM-0006 is retained as a permanent negative test — the checker rejects it. (10.1 AC2) — **R-001**
- **A7 [L2]** A UI edit of a `ui-editable` variable mints a new version and never mutates one. (10.1 AC3, CT-22)
- **A8 [L1]** A recorded corpus/recollection number is evidence with a stated source layer + authority grade, never a spine constant. (10.1 AC3, L38)
- **A9 [L1]** USD is the sole V1 numeraire; any risk/sizing/window value expressed in non-USD at template level refuses. (10.1 AC4) — **R-001**
- **A10 [L1]** A Book-level limit in an instrument-native quantity (lots) → `policy rejection` at template validation. (10.1 AC4, CT-22)
- **A11 [L2]** Version graph is `branches-from` (multiple heads legal), `current` a separate dated pointer, `supersedes` linear; a changed number changes fp1 → new identity. (10.1 AC5)
- **A12 [L0/L1]** qmf-risk defines CT-22/CT-27 on qmf-core nouns, imports only qmf-core, is imported by nothing. (10.1 AC6, AR-06)

### B. R faces, sizing ladder, full-loss-price law (Story 10.2) — P0-8, R-001

- **B1 [L1]** R is three typed faces with correct unit-kinds: `original_risk_distance` PriceDelta(instrument), `original_risk_amount` Money(numeraire), `r_multiple` dimensionless exact rational. (10.2 AC1, CT-23)
- **B2 [L1]** Both money-bearing faces are frozen at admission; a **stop move** never re-bases them. (10.2 AC1) — **P0-8**
- **B3 [L1]** A **protection amendment** never re-bases the frozen faces. (10.2 AC1) — **P0-8**
- **B4 [L1]** A **budget re-derivation** never re-bases the frozen faces. (10.2 AC1) — **P0-8**
- **B5 [L1]** `r_multiple` semantics: −1 = a full original loss, 0 = breakeven. (10.2 AC1)
- **B6 [L1]** An entry that resolves to no full-loss price → `invalid input`; no `original_risk_distance`, no admission. (10.2 AC2, CT-23) — **P0-8**
- **B7 [L1]** Adding to an open position (scale-in) → `policy rejection` (V1 admits no scale-in). (10.2 AC2)
- **B8 [L1]** `money_rules` carries units only, no ratified values; `loss_runway = book_capital − loss_floor`. (10.2 AC3)
- **B9 [L1]** `seat_r_ceiling ≤ seat_loss_run_allowance` is enforced. (10.2 AC3)
- **B10 [L1]** `position_risk_amount = requested_r × r_unit_price`, frozen at admission. (10.2 AC3)
- **B11 [L1]** `loss_floor` is one value read by both `money_rules` and `control_policy` (the kill line). (10.2 AC3, CT-22)
- **B12 [L1]** B-split: `bench_consecutive_loss_threshold` [count] in `leash_grammar` vs `seat_loss_run_allowance` [r_multiple] in `money_rules`; a count standing where an r_multiple is declared refuses. (10.2 AC4) — **R-001**
- **B13 [L1]** A value-factor is sourced only from a venue instrument-metadata snapshot as an exact rational; absent → `unavailable dependency`, never a silent conversion. (10.2 AC5) — **R-001**
- **B14 [L1]** V1 never sizes by margin. (10.2 AC5)
- **B15 [L1]** A Money↔R crossing names a rate (`r_unit_price` = Money per r_multiple); an implicit crossing refuses. (10.2 AC6) — **R-001**
- **B16 [L1]** Only `r_multiple` averages across instruments and accounts. (10.2 AC6)

### C. Three-layer admission and admission bar (Story 10.3)

- **C1 [L2]** Admission passes strictly three ordered layers (L1 linters at registration → L2 shakedown on a demo/paper binding → L3 one operator signature on one assembled page carrying both proofs + binding identity + resolved BMS fingerprint). (10.3 AC1)
- **C2 [L2]** No trial period / probation window / paper-performance gate exists in admission. (10.3 AC1)
- **C3 [L1]** An admission-bar requirement carries {`measure_identity`, `unit`, `comparison`∈{at-least,at-most,within-band}, `threshold` discriminated-union ruled|not-yet-ruled with the key always present}. (10.3 AC2)
- **C4 [L2]** No composite score / rating / tier band / weighted aggregate may express a bar → refusal. (10.3 AC2)
- **C5 [L2]** A bar holding any `not-yet-ruled` threshold or `pending` slot registers + binds non-live freely; binding to `role=live` → `policy rejection` (blank blocks live money). (10.3 AC3, CT-22)
- **C6 [L2]** An `evidence_requirements.account_role` naming a paper role in a bar that gates a live binding → `policy rejection` at Layer 1. (10.3 AC4)
- **C7 [L2]** Layer-1 worked-example arithmetic is recomputed by invoking the cited producer contracts themselves, never linter-local arithmetic. (10.3 AC5)
- **C8 [L1]** Unit-kind coverage is enforced on every declared variable at Layer 1. (10.3 AC5) — **R-001**
- **C9 [L1]** Two control-action kinds sharing a rank → `invalid input`. (10.3 AC5, CT-30)
- **C10 [L1]** A float-valued measure vs an exact-rational threshold crosses the analytic→exact boundary under a declared comparison rule (scale, rounding, tie); an undeclared comparison → `invalid input`. (10.3 AC6, CT-22)

### D. Binding chain, identity trinity, bind-time capability (Story 10.4) — R-001 currency

- **D1 [L1]** Binding tuple = (BookInstanceId, BmsInstanceId, VenueId, AccountId, world), aligned with the (VenueId, account) stream and never coarser; `role` is not in the tuple. (10.4 AC1, CT-28)
- **D2 [L1]** Identity trinity: Book version = template fp1; Book instance = operator-minted deployment record; binding epoch = the binding record's own fingerprint. (10.4 AC2)
- **D3 [L1]** A binding record fingerprinting equal to an existing one → `invalid input`, never a silent idempotent accept. (10.4 AC2, CT-28)
- **D4 [L1]** Every binding carries a complete per-counter `state_carry` {ledger, cycle, budget, bench_counter, exposure}, each carry|reset; absent/partial → `invalid input`. (10.4 AC3)
- **D5 [L1]** `carry` on any counter is legal only under an accompanying human-signed `carries-ledger` edge; carry without the edge → `invalid`. (10.4 AC3)
- **D6 [L1]** `carries-ledger` and `continues-performance` edges are never inferred from each other. (10.4 AC3)
- **D7 [L2]** The bind-time capability check resolves against CT-18's declaration + the venue-observation profile; any shortfall refuses at **bind time, never trade time**. (10.4 AC4, CT-28)
- **D8 [L2]** A settlement currency not matching the Book's `accounting_currency` (non-USD in V1) → `policy rejection` at bind time; no silent conversion. (10.4 AC5, CT-28) — **R-001**
- **D9 [L2]** A second Book on a netting account with an overlapping instrument set → `unsupported capability` unless the operator signs the shared-flatten limitation (an identity field of the binding). (10.4 AC6)
- **D10 [L2]** A missing SQS baseline / absent live-path rung baseline at bind → `unavailable dependency`. (CT-28)
- **D11 [L2]** A Book `control_policy` contradicting the BMS rank table → `unsupported capability` at bind. (CT-28, CT-30)

### E. Paper as a dated binding-epoch change (Story 10.5) — SCN-0006

- **E1 [L1]** Book modes are exactly LIVE|PAPER; a mode-field write naming a seat/binding-state word → `invalid input`. (10.5 AC1, CT-24)
- **E2 [L2]** A flip is a dated change of the execution binding minting a new binding epoch — never a new Book, never a Bot twin; current mode is a read-time fold, never a stored field. (10.5 AC1)
- **E3 [L2]** `execution_target` is resolved once from (Book mode, seat state, active-control set); PAPER selects the paired target without changing binding identity; one intent never yields two submissions. (10.5 AC2)
- **E4 [L2]** Exactly one active paper-routing target per live binding at an instant; no resolvable target → `unavailable dependency`; live trading unaffected. (10.5 AC3)
- **E5 [L2]** Trigger disposition: routes-to-paper (capital/authority) vs blocks-paper (market-risk); recording continues under any control; recording is not trading. (10.5 AC4)
- **E6 [L2]** Paper starting balance is a UI-editable default frozen at flip, never hand-adjusted; a reset mints a new operator-signed `paper_epoch_reset` with a fresh balance + lineage edge; the running balance is never mutated; paper P&L never crosses the money boundary. (10.5 AC5)
- **E7 [L2]** Return to live is automatic only where the clearing cause is clocked + mechanical (mints a CT-24 transition, never a CT-30 resume); anything touching real money requires an operator signature; paper performance never authorizes a return. (10.5 AC6)
- **E8 [L4]** SCN-0006 executable golden fixture end-to-end.

### F. Risk-evaluation door (Story 10.6) — P0-8

- **F1 [L1]** The door carries exactly two families entry|exit + declared evidence slots and nothing else; an **inbound `requested_r` → `invalid input`** (the bot may not size). (10.6 AC1, CT-23) — **P0-8**
- **F2 [L1]** An entry intent carries instrument, direction, advisory `proposed_r`, a typed reason code, the execution target, and cited evidence slots (format 1). (10.6 AC2)
- **F3 [L2]** The declared full-loss price is derived at the Book door by the Book's per-family ExitLogicRef consuming the intent's cited evidence, stamped exactly as `requested_r` is resolved; no Book module is injected into bot logic. (10.6 AC2) — **P0-8**
- **F4 [L1]** V1 exit kinds are only `close_full` and `tighten_protective_stop`, each with a typed `reason_code`; `close_partial` → `unsupported capability`; a tighten names a direction + bound, never a price. (10.6 AC3, CT-23)
- **F5 [L1]** A risk-monotonic violation (widen stop, extend target beyond envelope, re-open a closed position, increase size) → `policy rejection`. (10.6 AC4)
- **F6 [L2]** The adopt-the-bot's-advisory-stop mode exists in the ExitLogicRef registry with input = CT-23 format-2 `advisory_stop_proposal`; invoking it while CT-23 sits at format 1 → `unavailable dependency`; `requested_r` stays Book-resolved and R stays frozen in every mode. (10.6 AC5)
- **F7 [L1]** Format-1 artifacts stay readable forever; an unknown optional field never breaks a format-1 consumer. (10.6 AC6, AD-5)

### G. Exit records, close reasons, bench fold (Story 10.7) — SCN-0011

- **G1 [L1]** Exactly one CT-29 exit record per virtual-position close (the Book noun, never the venue position) carrying frozen faces, fill refs, `realized_pnl`, an identity-bearing `cost_components` set, a single-sourced `realized_r`, the close reason, `closing_authority` + arbitration ref, and the account-binding role. (10.7 AC1)
- **G2 [L1]** `realized_r` is a derived display of the record's frozen fields under the pinned formula, never a second implementation; a stored `realized_r` disagreeing with the derivation → `invalid input`. (10.7 AC1, CT-29)
- **G3 [L1]** The close reason is exactly one taxonomy member; `mechanism` and `outcome` are separate fields; `kill_line_flat` is minted apart from `protection_forced_flat`. (10.7 AC2)
- **G4 [L2]** Whole-trade attribution: the full realized R credits the Bot that opened the position regardless of who closed it; reports partition by close reason. (10.7 AC3)
- **G5 [L2]** The bench counts qualifying-loss exits (`realized_r ≤ −q`) as a read-time fold bounded by the binding epoch; scratches and partial losses do not count; a breakeven never counts under any q (recorded as its own metric). (10.7 AC4) — SCN-0011
- **G6 [L3]** Recording precedes interpretation: a later same-`(Book,Bot)`-seat intent minted before the closing exit record is persisted + journaled → `stale evidence` refusal. (10.7 AC5)
- **G7 [L1]** A protective stop / breakeven ratchet moves only in the risk-non-increasing direction against the frozen `original_risk_distance`; R stays frozen so −1R keeps meaning a full original loss. (10.7 AC6)
- **G8 [L4]** SCN-0011 executable golden fixture (four exits, bench crossing, seat benched to paper, next-open reset).

### H. Control actions, kill switch vs kill line, arbitration (Story 10.8) — P0-9 / L39 / SCN-0010

- **H1 [L2]** **Exit-preservation property:** no control action of any authority at any scope blocks `cancel_order`, `close_position`, `close_all`, a risk-non-increasing `amend_protection`, a protection action, or the recording of evidence; the blocking half of any control is entries only, paper and live alike. (10.8 AC1, CT-30, L39) — **P0-9**, Hypothesis-driven over the full (kind × authority × scope × risk-reducing-act) space.
- **H2 [L2]** No CT-30 kind whose effect is a blanket command-pipe block may be minted. (10.8 AC1) — **P0-9**
- **H3 [L1]** Action vocabulary is exactly {suspend_new, drain, flatten, resume}; each carries an authority-kind ∈ {operator, book_policy, protection_authority, venue-delegated, adapter_self}; suspend_new and drain are never-auto by rule. (10.8 AC2, CT-30)
- **H4 [L2]** Subject scope resolves through the pinned versioned table; an unresolvable or netting-indistinguishable scope refuses, **never widened**. (10.8 AC2)
- **H5 [L3]** A protection action is journaled before dispatch as a standing intent (read-time fold, restart-proof), re-decided rather than retried on reconnect, never time-expiring; satisfied by flatten only on a reconciled verdict showing the scope flat; drift/unknown/out-of-lookback alarm and hold without dispatching. (10.8 AC3, CT-30, SCN-0005)
- **H6 [L1]** Kill switch (global; stops all new trading everywhere; escalates automatically; de-escalates only by a human) vs kill line (per-Book capital floor; breach auto-flattens that binding's scope and stands the Book down); resume is operator-only. (10.8 AC4)
- **H7 [L2]** Same-tick **collapse**: colliding actions collapse to one command; the rank winner supplies authority + reason; each loser journals as suppressed. (10.8 AC5, SCN-0010)
- **H8 [L2]** Same-tick **conflict/compose**: mutually exclusive commands → higher rank wins outright; composing effects (`suspend_new + flatten`) both execute; **a higher rank never reduces the protection a lower rank would deliver**. (10.8 AC5, SCN-0010) — **P0-9**
- **H9 [L1]** Flatten authority: only operator (unconditional, any scope), Book policy (pre-declared trigger classes only), and the protection authority (where node severity declares close_all) may flatten — never a venue adapter, a sensor, or a Bot; every other money boundary (rollover, sweep, re-seed, paper flip) leaves positions alone. (10.8 AC6)
- **H10 [L4]** SCN-0010 executable golden fixture (arbitration end-to-end).

### I. Protection windows (Story 10.9) — SCN-0008

- **I1 [L1]** A window record carries two instants (never an offset), a resolved instrument scope, a kind ∈ {news, daily_dead_zone, session_handover_buffer} (handover declares anchor side pre-close|post-open|both), a reason class, a format version, and the external-fact quadruple where feed-derived. (10.9 AC1)
- **I2 [L2]** A window blocks new entries live and paper alike on in-scope instruments and blocks nothing else (never an exit, a protection amendment, a protection action, or observation); the blocked decision is journaled on the veto path carrying the refusing door + would-have-been action + window fingerprint. (10.9 AC2)
- **I3 [L2]** Instrument scope resolves through dated per-instrument currency-exposure records; a missing record → the instrument is treated as affected + blocked, the absence journaled as data quality + alarmed; a multi-instrument bot is blocked only on in-scope instruments. (10.9 AC3) — R-001 (currency)
- **I4 [L2]** Widen-never-shrink, forward-only: a revision may pull a start earlier for not-yet-passed instants or push an end later, never narrow/cancel/retro-invalidate; the effective window is a read-time union fold with passed bounds frozen. (10.9 AC4)
- **I5 [L2]** Fail-closed: a failed calendar refresh / unknown coverage / uncertain window blocks; there is no live skip button; a standing per-instrument exemption is a dated fingerprinted record consumed at compile time. (10.9 AC5)
- **I6 [L1]** `window_forced_flat` enters arbitration at rank 2 (declaring none is the V1 posture); widths/anchors/buffers are UI-editable variables with no spine value. (10.9 AC6)
- **I7 [L4]** SCN-0008 executable golden fixture.

### J. Risk journals & publish-never-act performance (Story 10.10)

- **J1 [L2]** Book/BMS/per-bot journals are read-time projections over writer-scoped streams selected by entity identity; an entity holds no WriterId and mints no stream; the legacy five Records names survive as projection names mapped by one versioned table onto the seven event types. (10.10 AC1)
- **J2 [L2]** Risk-authored events carry the Book-definition fingerprint + binding identity; venue-authored events carry the command record's content fingerprint; the projection joins through the pinned versioned command-fingerprint join, never by threading Book identity into a venue payload. (10.10 AC2)
- **J3 [L3]** A control action is journaled before dispatch: a storage failure blocks the dispatch rather than losing the intent. (10.10 AC3, CT-25)
- **J4 [L2]** Paper and live projections resolve inside one role-scoped namespace with role on every row; a cross-role read is explicitly declared, never a silent union. (10.10 AC3)
- **J5 [L1]** The performance-result container carries the full result label + account-binding role, a fingerprinted population (binding-record fingerprints, never intervals), a declared period with a knowledge-time bound, an ordered measure set with a unit-kind on every emitted quantity, and both suppression accounting (by authority + reason) and veto accounting (by door). (10.10 AC4, CT-32)
- **J6 [L2]** No score/rating/tier band/weighted composite may express a result; a single result may never span account roles (multi-role → `policy rejection`); the authority to act belongs to the Book door (bench) or the operator (promotion). (10.10 AC5)
- **J7 [L2]** The bench fold is one governed producer published once and consumed by the Book door; a replay-world result (world=replay) can never gate live money. (10.10 AC6, CT-32)

### X. Cross-cutting gates and P0 aggregates

- **X1 [L2]** **R-009:** every door-reachable typed-refusal category across the CT-22..CT-32 door paths is a member of `registry:typed_refusal_codes`; no door emits an off-register category. — **R-009**
- **X2 [L1]** **R-009 corollary:** the register is exactly the seven categories {invalid input, unsupported capability, unavailable dependency, stale evidence, policy rejection, transient venue failure, storage failure}, addable never redefined. — **R-009**
- **X3 [L0/L2]** **R-001 aggregate:** no binary float enters any money/price/R identity in qmf-risk value types (money-path float scanner over the package + an assertion test). — **R-001**
- **X4 [L3]** **P0-8 lifecycle:** a representative admitted-entry lifecycle passes the charter doors with R frozen at admission and a declared full-loss price required (integration over B2–B6, F1, F3). — **P0-8**

**Planned counts (L0 static gates reported separately):**

| Level | Count |
|-------|-------|
| L1 | 53 |
| L2 | 39 |
| L3 | 4 |
| L4 | 4 |
| **Total (L1–L4)** | **100** |
| L0 static gates | 5 (float scanner, nondeterminism scanner, pyright-strict, ruff, AR-06 dep-direction) |

---

## Section 5 — Source-reconciliation plan and seam / hot-spot map

**This section executes only after Section 4 above is frozen.** The reconcile pass maps each planned
test to the module that should satisfy it and records, per requirement, one of: `runnable` (code exists
and the assertion can execute), `blocked-unwired` (contract still `defined-unwired` — planned test
becomes a coverage FINDING), or `absent` (no module at all — FINDING).

Reconcile procedure (no source edits, read-only):
1. Enumerate `packages/qmf-risk/src/qmf/risk/**` module + symbol names (structure only) and map to clusters A–J.
2. Enumerate existing `packages/qmf-risk/tests/**` and mark which planned IDs already have coverage vs are net-new.
3. For `control_action.py` (cyclomatic 38): confirm the requirement-pinned behaviours (H1, H2, H4, H5, H7, H8, H9)
   have branch coverage; a high-cyclomatic branch with no requirement anchor is itself a FINDING (untethered complexity).
4. Confirm the seven-category register `registry:typed_refusal_codes` is a single source (CT-04) and that every
   Epic-10 contract's refusal enum is a subset (X1 mechanization target).

Seam map (planned wiring the L2/L3 tests must fake, never real-import):
- Registry sink (CT-06/CT-16 record kinds) — injected sink; qmf-risk never imports qmf-registry.
- qmf-data journal/store (CT-11/CT-13) — injected sink for J3 storage-failure-blocks-dispatch and G6 persist-before-next-intent.
- Venue capability declaration (CT-18) + venue-observation profile — fake for D7–D11 bind-time checks and H4 scope resolution.
- Producer contracts (CT-16 SQS, CT-01/CT-02 exact values) — fakes for C7 worked-example recomputation.

---

## Section 6 — Traceability (FR → story/AC → CT → tests → level)

| FR | Story | Primary CT | Planned tests | Levels |
|----|-------|-----------|---------------|--------|
| FR-027 (Books gatekeep; BMS accounts/constrains) | 10.3, 10.4, 10.6 | CT-22, CT-27, CT-28, CT-23 | C1–C10, D1–D11, F1–F3, X4 | L1–L3 |
| FR-028 (Book-owned sizing; full-loss price; R faces) | 10.2, 10.6 | CT-23, CT-22 | B1–B16, F1, F3–F7, X4 | L1–L3 |
| FR-029 (paper as dated binding-epoch state) | 10.5 | CT-24 | E1–E8 | L1–L4 |
| FR-030 (read-time risk-journal projections) | 10.10 | CT-25 | J1–J4 | L2–L3 |
| FR-031 (one-Book bindings as dated epochs) | 10.4 | CT-28 | D1–D6 | L1 |
| FR-032 (Book-owned risk-monotonic exits) | 10.6, 10.7 | CT-23, CT-29 | F4, F5, G1–G8 | L1–L4 |
| FR-033 (exit-preservation controls; kill switch/line; windows) | 10.8, 10.9 | CT-30, CT-31 | H1–H10, I1–I7 | L1–L4 |
| FR-034 (publish-never-act performance; bench fold) | 10.10 | CT-32 | J5–J7 | L1–L2 |
| FR-035 (USD numeraire; UI-editable configurables) | 10.1 | CT-22, L38 | A1–A12, E6, I6 | L0–L2 |
| Gate R-001 | 10.1/10.2/10.4/10.9 | CT-22/23/28, CT-01 | A4,A6,A9,A10,B12,B13,B15,C8,D8,I3,X3 | L0–L2 |
| Gate R-009 | all doors | CT-04 | X1, X2 | L1–L2 |
| P0-8 | 10.2/10.6 | CT-22/23 | B2,B3,B4,B6,F1,F3,X4 | L1–L3 |
| P0-9 | 10.8 | CT-30, L39 | H1,H2,H8,H9 | L1–L2 |

Every Story 10.x acceptance criterion maps to at least one planned test ID above; no AC is left uncovered
(the reconcile pass in Section 5 records any AC whose implementing code is absent as a FINDING rather than
a coverage hole in this plan).

---

## Section 7 — Untestable / deferred / blocked requirements

Recorded honestly; each with the reason it cannot be a runtime assertion in this epic/package.

1. **Cryptographic authenticity of operator signatures** (Layer-3 admission signature, `carries-ledger`
   edge, operator `resume`, promotion). V1 signing is "the operator's recorded approval, taking no
   cryptographic dependency" (CT-22/ADR-0015). **Testable:** presence/absence and gating semantics of the
   recorded attestation. **Untestable:** authenticity / non-repudiation — there is no crypto to verify.
2. **Node severity policy — the KSA `trigger → level → effect` matrix and `severity → window` mapping**
   (CT-27, CT-30, CT-31). Ruled explicitly OUT of QMF surface ("QMF carries the contract, the scopes, the
   refusals and the evidence; never the matrix" — tracker/trading-node-notes.md). Untestable in this
   package by ratified boundary; belongs to the trading-node layer.
3. **Alpha-decay mathematics** (CT-29, CT-32). Decided-deferred (AD-41): only the evidence primitives ship
   now. The decay verdict math does not exist by design. **Testable:** the primitive collection
   (frozen faces, `realized_r`, suppression/veto accounting). **Untestable:** any decay score.
4. **The not-yet-ruled thresholds behind the format-2 admission-bar evidence fields**
   (`registered_conformant_bot_cite`, `canonical_assignment_evidence`; GAP-0048/0049). The interfaces
   exist; the thresholds are honestly blank. **Testable:** blank-blocks-live-money (C5) and the format-2
   readability rule (F7). **Untestable:** the actual threshold comparison — there is no ruled value.
5. **Cross-epic producer recomputation** (C7: "worked examples recomputed by invoking the cited producer
   contracts themselves"). Executable only when the cited producers (Epic 1 CT-01/CT-02, Epic 5/6
   indicators/structure) are available. In-package this is tested with producer **fakes**; a true
   end-to-end recomputation is a cross-epic (system-level) test, out of Epic-10 package scope.
6. **CT-32 reproducibility under a QMB replay run** (DEC-0163). The container-fingerprint determinism is
   testable inside qmf-risk (J5/J7); reproducing an actual QMB run id under its resolved run-config is
   COMP-QMB (Epic 13) territory, not this package.
7. **BLOCKED INPUT — absent authorities.** `test-design-qa.md` (the canonical L0–L6 template + per-epic
   template) and `QMX-handoff.md` (the 15 P0/P1 assertions + this epic's full risk-gate rows) are not
   present in the worktree. This plan reconstructs the template shape from the task prompt and uses P0-8,
   P0-9, R-001, R-009 as given there. If those files are restored, re-reconcile: the level definitions,
   the remaining P1 assertions, and any additional gate rows may refine Sections 3, 4, and 6.

---

## Section 8 — Execution plan, fixtures, tooling, exit criteria

**Tooling.** `uv run pytest` from the worktree root (dev group synced). The exit-preservation property
(H1) and the widen-never-shrink fold (I4) use Hypothesis (`uv run --with hypothesis pytest ...` if not in
the lock). Static gates via the repo's ruff + pyright-strict config and the two NFR-02 scanners.

**Fixtures (requirements-anchored, no scenario-local literals).**
- Golden fixtures E8/G8/H10/I7 read the scenario record fields and recompute folds from the record
  streams, never from literals; every numeric input (`q`, ranks, `paper_starting_balance`, window widths)
  is pulled from `docs/registry/variables.yaml` keys so a registry change re-derives the expectation
  (per each SCN's "Worked numbers" instruction).
- Shared builders: a Book definition (CT-22) with a complete `money_rules` + `admission_bar`; a BMS
  definition (CT-27) with a total, unique rank table; a binding record (CT-28) with a complete
  `state_carry`; an entry/exit intent (CT-23); a control-action stream (CT-30).

**Ordering (levels gate upward).** L0 static → L1 → L2 → L3 → L4. A red L0/L1 that reflects a real
contract violation is a FINDING and does not block authoring the higher-level tests (they are recorded as
blocked-by-finding, not skipped silently).

**Exit criteria for the Epic-10 audit.**
1. Every planned ID A1–X4 has a runtime result or an explicit `blocked-unwired` / `absent` FINDING.
2. R-001 and R-009 gate rows are green, or every failure is a filed FINDING with the violating door/path.
3. P0-8 (X4 + backing units) and P0-9 (H1 property) are green or filed as FINDINGs.
4. `control_action.py` branch coverage: every branch tied to a requirement anchor; untethered branches
   filed as complexity FINDINGs.
5. 100% branch coverage on any CT-01/CT-02-touching value type reached from qmf-risk (NFR-02 floor);
   80% line floor across the package.
6. No source file outside `qa/` modified; no test weakened to pass; every divergence between contract and
   code recorded as a FINDING.
