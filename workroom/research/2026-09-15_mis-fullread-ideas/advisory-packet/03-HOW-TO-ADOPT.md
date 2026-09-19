# How to adopt literally — architecture

There is no new MIS library. There is no `qmf-mis`. There is no CT-MIS-* in this packet.

## Seams that already exist (use these)

| Seam | Path on `integration` | Role |
|---|---|---|
| Snapshot mint / consume | `qmn/src/qmn/mis/signal_snapshot.py` | Governed output |
| V1 producers | `labelers.py`, `liquidity.py`, `catalog.py` | Leave them |
| Shadow register / publish / compare | `qmn/src/qmn/mis/shadow.py` | **Where new sensors land first** |
| Design / corpus / labels / train / eval / register | `regime_design.py` … `regime_register.py` | Offline pipeline; refuse governed/active |
| QMB lanes | `qmb` runloop / optimize / sweep / robustness | Ungoverned experiments (SCN-0015) |
| Book door | trading-node TN-19 | Later **policy**, not a new MIS authority |

## Adoption recipe (every candidate)

1. **Name the object** from `02-ADOPT.md` (one ID).
2. **Implement it as a shadow candidate labeler** (`register_shadow_candidate`). Identity goes to `shadow_composition_fp` only.
3. **Features as-of, closed bars/ticks.** Knowledge-time on every row.
4. **If it learns:** train on operator laptop with the existing refuse-paths (`regime_train` / `regime_register` sandbox|candidate only). Freeze a fingerprintable artifact. Live path **encodes**; it does not fit.
5. **Evaluate on a door task** (`04-EXPERIMENTS`), not on article win-rate.
6. **Compare to B1–B4.** If it loses, drop it. Do not ensemble the loser in.
7. **Promotion** is GAP-0051 + a sitting. This packet does not promote.

## Snapshot shape (only after a sitting)

V1 snapshot stays thin. Proposed **later** optional fields (at most one in the first sitting):

| Field | Type | Meaning | Must not |
|---|---|---|---|
| `market_state_class` | enum + `insufficient_evidence` | A1 or design LightGBM or A3 cell | Carry direction |
| `break_flag` | bool or [0,1] | C1/C2 | Be a side or a size |
| `activity_bin` | quiet/normal/elevated | D1/D2 | Be merged into SQS |

Do not add A1 **and** C1 **and** E1 to the governed snapshot in one sitting. Shadow may carry all three in parallel.

## Book door (policy is not MIS)

If experiments win, Book reads **one** snapshot field and applies a declared policy:

- sit-out / refuse new entries
- cooldown N bars after `break_flag`
- later: class-activation of bot *families* (not MIS switching bots)

Write the policy in Book/BMS terms. MIS only emits the number.

## What “literal” is **not**

| Article pattern | QMX move |
|---|---|
| Wizard Signal + MM class + RL head | Split: grid/sensor → MIS shadow; policy → bot; size → R-ladder |
| `OnTick` forming-bar updates | Closed bar / slice frontier only |
| `iCustom` from a .ex5 | Reimplement the **formula** in QMN/QMB Python/Rust as-of; do not wrap MT5 |
| Online `OnCalculate` retraining | Forbidden (L-RIVER, L-OFFLINE) |
| Multi-strategy switch inside one EA | Book class-activation later |
| SQS-like spread mixed with ATR | Keep SQS pure; ATR is D-family |

## Minimal delta (copy this into a sitting if asked)

1. Keep `regime_classifier_v1` unbound.
2. Add shadow candidates for **B2, A1, C1** (three only).
3. Run E1–E3 in QMB ungoverned/shadow.
4. No snapshot field, no Book policy, until those return.
5. If one wins on a sealed holdout door metric vs B1–B4, sit **that one field**.
