# RESULTS — Epic 17: QMB fill/slippage/fee/financing ports (FR-044)

**Audit tier:** T2 (evidence-honesty epic; execution taint gates every downstream edge claim).
**Package under test (read-only evidence):** `qmb/src/qmb/execution/` — `binder.py`, `fidelity.py`,
`ports.py`, `fill.py`, `slippage.py`, `cost.py`, `financing.py`, `spread.py`, `risk.py`,
`handler.py`, `adapters.py`.

## How to run

```
# L0-L2 + L3 contract tests (property module skips cleanly when hypothesis is absent):
uv run pytest qa/tests/epic_17 -q --tb=short
# full suite incl. the L6 hypothesis properties:
uv run --with hypothesis pytest qa/tests/epic_17 -q --tb=short
```

## Headline

| Metric | Count |
|---|---|
| Tests authored | 51 (+ 1 manual L6 review) |
| Passed | **51** |
| Failed | **0** |
| Errored | **0** |
| Skipped (task command, hypothesis absent) | property module only; runs green under `--with hypothesis` |
| Requirements owned (R1–R33) | 33 |
| Requirements green under rules 1–5 | 33 (each with ≥1 substantive, falsifiable test) |
| UNPROVEN / partial rows recorded (findings.csv) | 8 (GAP-0048 deferrals, one CT-13 ambiguity, one AC-clause gap, scope boundaries) |

All 33 owned requirements are met by the source at the level Epic-17 can prove in isolation.
There is **no behavioural defect / failing test**. The 8 findings.csv rows are
structurally-deferred or under-specified requirement facets (rule 6): they are recorded as
`observed=UNPROVEN`, not as green claims. Properties are stable under `PYTHONHASHSEED` 0 and 12345.

---

## Per-test results

### Group A — port-set composition & fidelity identity (Story 17.1) · `test_a_composition.py`

| Test | Req | Lvl | Prio | Status | Meaning (one line) |
|---|---|---|---|---|---|
| T-17.1-a | R1 | L2 | P1 | PASS | Binder composes three SEPARATE Protocol ports + a financing scheduler, each by adapter-id; missing-adapter config refuses. |
| T-17.1-b | R1 | L2 | P1 | PASS | Composition order is observed as fill→slippage→cost via test-owned recorders (slippage sees no post-slip; cost sees post-slip set). |
| T-17.1-c | R2 | L3 | P2 | PASS | Binding is only from the resolved config: unknown/absent adapter-id refuses (no ambient default); same config binds deterministically. |
| T-17.1-d | R3 | L3 | P0 | PASS | A bot-sized order / bare string / None returns a CT-04 invalid-input refusal and **no port executes** (recorders empty); a real intent does drive them. |
| T-17.1-e | R4 | L2 | P0 | PASS | A CT-23 intent is executed unchanged (same object, quantity preserved); a cost port that re-sizes is refused by the never-resize guard. |
| T-17.1-f | R5 | L3 | P0 | PASS | An opening intent with no AD-40 full-loss price refuses **before any fill** (recorders empty); with a derivable stop it executes. |
| T-17.1-g | R6 | L2 | P1 | PASS | A risk-reducing CT-29 exit executes with no entry_price/module/full-loss supplied. |
| T-17.1-h | R7 | L2 | P0 | PASS | Fidelity identity = adapter-id + composition-version + taint; taint is a field OMITTED from fp1; a non-optimistic taint is refused. |
| T-17.1-i | R8 | L2 | P1 | PASS* | Two different bound sets → different execution fingerprints; same set → identical fingerprint (identity never silently drifts). *See E17-F04 on the version ordinal. |
| T-17.1-j | R9 | L1 | P0 | PASS | Run fidelity is a lowest-wins fold; moving the min flips the winner; no taxonomy → no invented ordinal; missing rank → refusal. |
| T-17.1-k | R10 | L3 | P0 | PASS | Mixed-fidelity Book-bar comparison without an explicit bool-True override is a CT-04 policy rejection; non-bool override refused; equal → ok. |
| T-17.1-l | R11 | L3 | P1 | PASS | Replay-on-synthetic config is invalid input; store-persisted synthetic → world=simulated policy rejection; recorded → world=replay. |
| T-17.1-m | R12 | L3 | P0 | PASS | Optimistic taint bars edge/verdict claim and split-budget spend (policy rejections); non-optimistic taint refused. |

### Group B — synthetic-spread model & SQS input (Story 17.2) · `test_b_spread.py`

| Test | Req | Lvl | Prio | Status | Meaning (one line) |
|---|---|---|---|---|---|
| T-17.2-a | R13 | L2 | P0 | PASS | Trade-only bars get keyed synthetic bid/ask; buy(ask) ≠ sell(bid); a buy=sell calibration cell is itself refused. |
| T-17.2-b | R14 | L3 | P0 | PASS | An absent artifact for the instrument (and an empty table) refuses (unavailable dependency), never a silent zero; calibration is fingerprinted per-broker. |
| T-17.2-c | R15 | L2 | P1 | PASS | Real quotes take precedence over the synthetic model (basis quote-real, values from the feed); the two bases are distinct fidelity tokens. |
| T-17.2-d | R16 | L3 | P1 | PASS | The SQS door consumes the modeled series of exact Prices; non-live → ok, live → policy rejection, non-series → invalid. |
| T-17.2-e | R17 | L3 | P1 | PASS | The spread calibration fingerprint is declared in the fidelity label and on the modeled series; a different calibration → different fingerprint. |

### Group C — fill & slippage price-forming pipeline (Story 17.3, R-011 locus) · `test_c_fill_slippage.py`

| Test | Req | Lvl | Prio | Status | Meaning (one line) |
|---|---|---|---|---|---|
| T-17.3-a | R18 | L2 | P0 | PASS | All eight order-type arms dispatch (market/limit/stop/stop-limit/trailing/MOO/MOC/AON-group each fill as required). |
| T-17.3-b | R18 | L2 | P1 | PASS | An all-or-none group with one failing leg returns NoFill(all_or_none_leg_failed) for the WHOLE group. |
| T-17.3-c | R19 | L1 | P0 | PASS | Worst-case math is exact: buy limit=min(high,limit)=99000; sell limit=max(low,limit)=101000; buy stop=max(stop,current)=101000. |
| T-17.3-d | R19 | L2 | P1 | PASS | Optimistic-exact fills at the order price (100000) with a distinct fill-basis; worst-case at 99000; both stay optimistic-tainted. |
| T-17.3-e | R20 | L2 | P0 | PASS | A reduce_only fill caps to open position size (4/10, remaining 6) with its own fee reference; a lot step of 3 snaps 10→9. |
| T-17.3-f | R20 | L1 | P0 | PASS | Lot-step rounding is exact-integer (Fraction(9)), never a binary float; an evenly-dividing step keeps the fill whole. |
| T-17.3-g | R21 | L2 | P0 | PASS | stale_data / market_closed / not_triggered / insufficient_liquidity are typed NoFills from the closed reason set. |
| T-17.3-h | R21 | L2 | P1 | PASS | A between-bar gap fills at the gapped (open) price with gap_fill=True, not skipped. |
| T-17.3-i | R22 | L2 | P0 | PASS | Resting orders rank deterministically by first-cross along the declared path; two runs → identical sequence; A before B. |
| T-17.3-j | R22 | L2 | P1 | PASS* | The execution handler mints no mid-slice intent. *Cross-sub-phase "new intents rest" is Epic-14-owned — see E17-F08. |
| T-17.3-k | R23 | L2 | P2 | PASS | All five slippage models map pre→post (buy +, sell −); zero shape leaves post=pre. |
| T-17.3-l | R23 | L2 | P0 | PASS | Slippage vetoes (NoFill illegal-print) when the slipped price leaves the bar; a wide bar makes the same print legal. |
| T-17.3-m | R23 | L2 | P2 | PASS | Passive limits skip slippage by default (post=pre); explicitly configured, the offset is applied. |
| T-17.3-n | R23 | L3 | P2 | PASS* | The per-run seed is deterministic from run identity and differs per run. *No stochastic model consumes it in V1 — see E17-F07. |

### Group D — cost port: exact-integer itemized commissions (Story 17.4) · `test_d_cost.py`

| Test | Req | Lvl | Prio | Status | Meaning (one line) |
|---|---|---|---|---|---|
| T-17.4-a | R24 | L2 | P0 | PASS | Commission is a typed Money line in its own currency; a float rate is refused at the calibration boundary (never on the money path). |
| T-17.4-b | R26 | L1 | P1 | PASS | Shape math is exact: zero=$0.00; per-lot=$2×10=$20.00; percent=1%×$10=$0.10; min-shape=max(prorated-min, %×notional) picks $5.00 then $1.00. |
| T-17.4-c | R25 | L2 | P0 | PASS | A partial's commission is per_lot × its filled qty ($8.00 for 4/10), a distinct line, never folded into P&L; full fill charges $20.00. |
| T-17.4-d | R27 | L3 | P0 | PASS | The admission query and the fill-time charge return the identical amount ($20.00); the quote is a pure re-computation. |
| T-17.4-e | R28 | L3 | P0 | PASS | A non-zero shape with no calibration refuses (unavailable dependency), never a silent zero; the named zero shape is a legitimate empty cost set. |
| T-17.4-f | R26 | L3 | P1 | PASS | Calibration is versioned + per-broker + fingerprinted; a model mismatch refuses; a non-catalog model refuses at construction. |

### Group E — daily-swap financing (Story 17.5) · `test_e_financing.py`

| Test | Req | Lvl | Prio | Status | Meaning (one line) |
|---|---|---|---|---|---|
| T-17.5-a | R29 | L2 | P0 | PASS | Financing applies at the calendar rollover as exact Money per instrument×direction (long −$0.50, short +$0.30 for 10 lots); off-rollover → 0 events; no calendar → invalid. |
| T-17.5-b | R30 | L2 | P1 | PASS | Triple-swap weekday=TUESDAY (3×, not hardcoded Wednesday), credit sign preserved (+$0.30 short), weekend skip vs apply read from the artifact. |
| T-17.5-c | R31 | L3 | P0 | PASS | An absent swap table (scheduler, lookup, and rollover) refuses (unavailable dependency), never a silent zero; a covered instrument charges. |
| T-17.5-d | R32 | L3 | P1 | PASS* | A swap is a distinct journal event (event_type ≠ fill/order, kind=financing). *The exact CT-13 event-type mapping is under-specified — see E17-F01. |
| T-17.5-e | R32 | L2 | P1 | PASS | Cost drag decomposes into four attributable lines (fill-pnl/slippage/commission/financing); total exact; currency mismatch refused. |
| T-17.5-f | R33 | L3 | P1 | PASS | The financing calibration fingerprint is declared in the label; run stays optimistic-tainted, barred from edge/split-budget claims. |

### Group F — static / structural gates · `test_f_static.py`

| Test | Req | Lvl | Prio | Status | Meaning (one line) |
|---|---|---|---|---|---|
| T-17.0-protocol | R1 | L0 | P1 | PASS | fill/slippage/cost/financing are four distinct runtime-checkable Protocols; behaviourally distinguishable; same-object binding refused. |
| T-17.0-nofloat | R24;R16 | L0 | P0 | PASS | AST scan: no binary float literal and no `float()` call anywhere under `execution/`; the scanner is self-checked to actually catch a float. |
| T-17.0-noconst | R14;R23;R26;R30;R29 | L0 | P0 | PASS | No calibration constant is a fallback: absent spread/slip/commission/swap content and a missing rollover calendar each REFUSE, never substitute a number. |

### Group F — property-based invariants (L6) · `test_g_properties.py` (run under `--with hypothesis`)

| Test | Req | Lvl | Prio | Status | Meaning (one line) |
|---|---|---|---|---|---|
| T-17.2-P | R13;R14 | L6 | P0 | PASS | Over arbitrary (hour, session, bid, spread): a present cell quotes buy<ask; an absent key refuses — never a silent zero. |
| T-17.3-P | R19 | L6 | P0 | PASS | Over arbitrary OHLC + limit: the worst-case fill stays inside [low,high] and never beats the order price (≤ limit buys, ≥ limit sells). |
| T-17.F-taint | R7;R9;R12;R33 | L6 | P0 | PASS | Over arbitrary bound sets: the composed label keeps the optimistic taint AND names the lowest-rank adapter; a non-optimistic taint is refused. |
| T-17.F-partial | R20;R25 | L6 | P0 | PASS | Over arbitrary partial splits: Σ per-partial pro-rated commission == the whole-fill commission exactly (no float drift); reduce_only cap holds. |

### L6 adversarial review (T-17.F-review) — conclusion

An adversarial read of all eleven `execution/` modules against B-6 + DEC-0135, hunting the
epic's failure spine, found **no silent-flattering path**:

- **Silent-zero paths:** every calibration consumer (spread / slippage / commission / swap)
  returns a typed `unavailable dependency` refusal on absent content; the only zeros are the
  explicitly-named `zero` catalog shapes (SLIP-2/FEE-2), not fallbacks. Verified behaviourally
  (T-17.2-b, T-17.3-l branch, T-17.4-e, T-17.5-c, T-17.0-noconst) and by property (T-17.2-P).
- **Taint drops:** every fill/label/costed-fill validates its taint to `optimistic`; the fold
  refuses a non-optimistic set; `apply_execution_ports` re-checks the taint after cost. No path
  drops the taint or raises fidelity above the lowest adapter (T-17.F-taint).
- **Invented constants:** the calibration dataclasses default their numeric content to `None`
  (or require it); no spread/fee/swap number and no rollover hour is embedded — the rollover
  instant is answered by the bound `RolloverCalendar` (T-17.0-noconst, T-17.5-a).
- **Float leaks on the money path:** none (AST scan, T-17.0-nofloat); money is exact `Money`,
  quantities exact `Quantity`, rates exact `ExactRational`/scaled-integer.
- **Composition-order violations:** the order is pinned and observed fill→slippage→cost
  (T-17.1-b); slippage/cost never re-size (guarded, T-17.1-e).

Two adversarial observations became findings for ruling rather than defects: the CT-13
event-type overload for a swap (**E17-F01**) and the constant composition-version ordinal
(**E17-F04**).

---

## UNPROVEN / partial requirement roster (findings.csv)

Per rule 6, requirement facets that are structurally deferred, under-specified, or owned by
another epic are recorded as `observed=UNPROVEN` — they are **not** counted as green claims.

| ID | Req | Why UNPROVEN in Epic-17 isolation |
|---|---|---|
| E17-F01 | R32 | CT-13 has no financing/swap event type; the swap is mapped onto `risk transition`. Distinctness-from-fill is proven at shape level; the exact mapping needs a ruling. |
| E17-F02 | R14;R23;R26;R30 | Calibration **content** (spread/slip/fee/swap numbers) is GAP-0048-deferred; asserting a number would assert an unratified value. Mechanism + refusal proven. |
| E17-F03 | R10;R15 | Fidelity **ordinal** taxonomy is GAP-0048-deferred; only relative precedence + refuse-to-fabricate are provable now. |
| E17-F04 | R8 | `composition_version` is a fixed V1 constant; the AC's "version changes when the bound set changes" is unimplemented. Anti-drift is carried by the execution fingerprint (proven). |
| E17-F05 | R12;R33 | Split-budget **spend** enforcement is qmf-data(CT-12)/Epic-14-owned; only the taint-carried claim-class gate is provable here. |
| E17-F06 | R16 | SQS modeled-series ↔ DEC-0153 freshness/quote-sampling reconciliation is a GAP-0048 pending slot; only read-point + exact-Price are provable now. |
| E17-F07 | R23 | The stochastic slippage term is unimplemented in V1 (models deterministic; `slip_fill` discards the seed); seed derivation proven deterministic, but no draw is taken. |
| E17-F08 | R11;R22 | Provenance→world derivation (B-7) and cross-sub-phase "new intents rest" (B-2) are Epic-14-owned; Epic 17 proves only its refuse-to-compose and no-mid-slice-mint halves. |

---

## Exit-criteria assessment (PLAN §8)

1. **Every P0 test green + mutation-sensitive on its guard** — MET. P0 guards assert exact
   values/winners (worst-case price 99000 vs 100000; lowest-rank fold; absent-artifact refusal
   vs Ok on a matching artifact; per-partial pro-rata sum equality), each of which flips under the
   obvious mutation (`min`→`max`, refusal→zero, pro-rata→whole, argmin→argmax).
2. **Fill order-type dispatch + every model-catalog / absent-artifact branch tied to an
   assertion (R-011 gate)** — MET. All eight order-type arms (T-17.3-a/b), all five slippage
   models (T-17.3-k) and their absent-artifact edges (T-17.0-noconst), all four commission
   shapes (T-17.4-b) and their absent edge (T-17.4-e), the swap table + absent edge (T-17.5-a/c).
3. **`T-17.F-taint` and `T-17.F-partial` green under PYTHONHASHSEED variation** — MET (0 and 12345).
4. **Every "is refused" test asserts a RETURNED CT-04 refusal of the correct category; every
   NoFill carries a reason code from the closed set** — MET (categories asserted throughout;
   NoFill reasons ∈ NOFILL_REASONS in T-17.3-g).
5. **Every blocked/partial requirement has a recorded reason + owning epic/gap** — MET (E17-F01..F08).
6. **L6 review complete with no un-triaged silent-zero / taint-drop / invented-constant finding**
   — MET (see the L6 review conclusion; the two triaged observations are E17-F01/E17-F04).

**Process caveat (unchanged from PLAN §1):** the two named authorities `test-design-qa.md`
(L0–L6 template) and `QMX-handoff.md` (15 P0/P1 assertions + the R-011 risk-gate row) are
absent from the worktree; the level taxonomy, priority ladder, and the R-011 interpretation are
reconstructed from the ratified spine + ACs + the fill/fees source spec, and should be
reconciled when those files are restored.
