# 17 — Legacy vs current reconciliation

**Current operational truth** is `docs/` + `integration` code (`05_`, `07_`).  
**Legacy** in this folder is archive/recovery + research notes (`02_`, `03_`). Desktop vaults were not re-opened this run.

| Legacy object | Where it lived (in-repo) | Current | Reconciliation |
|---|---|---|---|
| MIS as ensemble service / “ML ensembler” | tracker early notes; operator nickname | Labeler layer + snapshot | Nickname is not a bound family. Tracker later: “MIS assembler never existed” |
| Fat snapshot (HMM posteriors, chaos_score, DOM, RVOL, premium session) | GitBook CT-MIS-01 optional fields in `archive/recovery/.../gitbook-baseline.md` | Thin snapshot: SQS, feed_state, degraded_sensors, readiness | **LEGACY_SUPERSEDED**. Optional `regime` field not on V1 snapshot |
| Bots as MIS consumers | wiki/AD-19 conflict C-01 | Book + KSA only (DEC-0204) | **Resolved against bots** |
| SQS = snapshot quality / weighted floor | BMAD Story 3.1; DEC-0073 | Spread Quality Sensor ratio (DEC-0153) | **Killed-as-name**; do not recover aggregate as SQS |
| SQS ratio formula | recovery addendum | Adopted as V1 | **ALREADY_IMPLEMENTED** (law + `evaluate_sqs`) |
| Eight-labeler catalog | DEC-0262 | Same eight names | Six+fitted **AI**; trained **unbound** |
| Kronos / HMM / BOCPD / MS-GARCH | DEC-0262 recovered names | `UNAUTHORITATIVE_CANDIDATES`; design eval `authority=none` | Names recovered; **no authority** |
| `regime_classifier_v1` undesigned | glossary / GAP-0051 / epics 30.1 | Code on integration **does** choose LightGBM + quiet\|normal\|elevated\|stressed | **Docs lag code.** Design-only, not governed. Recovery agent U1 was correct *on main checkout*; `05_` verified the integration tree |
| Shadow lane | DEC-0204 planned seam | `shadow.py` implemented | **AI** as empty seam |
| Kelly × physics_multiplier | not in this repo | R-ladder in qmf-risk | **ABSENT-IN-REPO**; current sizing is R-ladder. Restoring physics as a multiplier would reopen sizing law |
| Ising / Lyapunov as QMX sensors | ABSENT-IN-REPO | Absent | Not a recovery. MQL5 article 15332 is **external method evidence**, D/C grade until reproduced |
| Regime Match Filter | not in this repo’s docs as law | Forbidden (bots never read MIS) | **INCOMPATIBLE** |
| MIS-Archive / CT-MIS-01,02 | gitbook-baseline | Not in `docs/contracts/` | **LEGACY_SUPERSEDED** as contracts |
| `qmf-mis` library | DEC-0089 out of scope | Node-owned MIS | **Dead library idea** |

## Two facts that must stay separate

1. **Operational:** current QMX does not run a physics stack or a trained regime classifier on the money path.
2. **Strategic:** some *legacy problem formulations* (change sensors, compression/expansion, sit-out filters) may still be better than “train LightGBM on forward range quantiles.” That is an experiment question, not a silent override of `integration` design.
