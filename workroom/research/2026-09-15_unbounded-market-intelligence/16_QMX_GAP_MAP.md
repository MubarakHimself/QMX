# 16 — QMX gap map (regime / changeover / placement)

Classifications from the research prompt. Evidence is current docs + `integration@8510c032496bb870824ecc5c4f807e8a4e4f167e` (`05_`, `07_`) plus in-repo recovery (`02_`). Article-derived rows stay provisional until `11_ARTICLE_CLAIMS.jsonl` is merged.

Legend: **AI** already implemented · **IAN** implemented under another name · **IBNG** implemented but not governed · **PI** partially implemented · **DNI** designed but not implemented · **PO** planned only · **LS** legacy superseded · **LWR** legacy worth recovering · **GG** genuine gap · **DUP** duplicate · **INCOMP** incompatible with current laws · **IE** insufficient evidence · **ROR** requires operator ruling

| Idea | Class | Evidence | Notes |
|---|---|---|---|
| Compute-once signal snapshot | **AI** | `qmn/mis/signal_snapshot.py`; TN-19; DEC-0204 | Book door + KSA only |
| Bots consume MIS | **INCOMP** | `refuse_bot_consumer`; DEC-0204 | Vault/wiki listed bots; current law closed |
| SQS ratio, block-only | **AI** | L23; DEC-0153; `evaluate_sqs` | Not a regime model |
| Snapshot-quality aggregate as SQS | **LS** | DEC-0073; recovery R-08 | Dead name |
| Rule-based six labelers | **AI** | catalog + labelers | identity, spread_state, gap_event, feed_state, SQS, degraded_sensors |
| `liquidity_stress_v1` fitted quantile | **AI** | `liquidity.py` | Not trained ML |
| Shadow-lane seam | **AI** | `shadow.py`; TN-19 | Empty of models; comparison gates nothing |
| `regime_classifier_v1` design artifact | **DNI / DNG** | `regime_design.py` Story 30.1 | Family chosen in **code** (`lightgbm-multiclass`); **not ratified** as governed law (glossary/GAP-0051 still say undesigned). See `04_` U1 vs `05_` |
| Regime corpus/labels/train/eval/register | **DNI** | Stories 30.2–30.6 | Offline seams exist; no money-path bind |
| Trained labeler on live path | **GG / PO** | GAP-0051 | Last node epic; operator-laptop script |
| Kronos / HMM / BOCPD / MS-GARCH as governed | **INCOMP** until sitting | `UNAUTHORITATIVE_CANDIDATES`; DEC-0262 | Evaluated, `authority=none` |
| Online-river continuous learning | **INCOMP** | `regime_design.evaluate_candidate_families` | Rejected for reproducibility |
| GitBook `trend\|range\|chaos` on snapshot | **LS** | gitbook-baseline; not DEC-0204 payload | Optional field dropped |
| Regime Match Filter (bot reads MIS to switch) | **INCOMP** | DEC-0204; OPERATING_LINE | Vault-only; conflicts with bots-never |
| `physics_multiplier` / Ising / Lyapunov as QMX law | **IE** in-repo; **INCOMP** with current sizing | ABSENT-IN-REPO (`02_`, `04_` U4); R-ladder replaced Kelly stack | New sitting if wanted; not a recovery |
| Session id as SQS baseline key | **AI / PI** | SQS baseline keyed venue/env/instrument + session window in formula law | Calendar kinds named apart |
| News window as SQS | **INCOMP** | L23; CT-31 | News is a control window |
| `session_handover_buffer` | **AI** as CT-31 kind | ct-31; registry vars | Calendar changeover, not a regime model |
| Compression/transition/expansion (20996) | **IE** as QMX binding; **GG** as competing vocabulary | article 20996; not in catalog | Descriptive, closed-candle, non-trading — MIS-shaped, different classes than quiet\|normal\|elevated\|stressed |
| Sequential CUSUM breakpoint (23043) | **IE**; cousin of unauthorized BOCPD | article 23043 Parts 1–2 | Causal sequential detector; Book/KSA *sensor* candidate, not a class |
| Continuous MA+ATR channel instead of discrete regimes (16856) | **IE**; challenges discrete classifier | article 16856 | Playbook-in-the-EA; win-rate claim is not a certificate |
| Look-ahead-safe filtered HMM | **GG** if sitting wants HMM | file 08 + DEC-0262 | Public hmmlearn decode leaks; custom forward step required |
| Jump models (`jumpmodels`) | **IE** | file 08 | Not in MQL5 title set; Python prior art only so far |
| ADX-low / σ-ratio 3-way as simple baseline | **GG** as *experiment baseline*, not a missing library | 10715, 17737; `regime_eval` already names majority / session-majority / spread-state-proxy | Must beat these before LightGBM is interesting |
| Class activation at Book door | **PO** | TN-19 “later class activation” | Not V1 |
| Placement = sit-out vs switch-EA | **ROR** on product intent | OPERATING_LINE; 17781 | Current law: MIS does not switch playbooks |

## Real missing capability (not “need Ising”)

The gap that is **named and unpaid** is GAP-0051: a **causal, cost-aware, abstaining market-state label** that can enter the **existing shadow seam** and, only after a sitting, the governed snapshot — without becoming a direction signal or a sizing knob.

Competing formulations the corpus already offers (none is privileged):

1. Discrete vol/risk buckets (current integration design: quiet|normal|elevated|stressed).
2. Discrete behavioural boxes (trend/range/volatile; or compression/transition/expansion).
3. Sequential *change* probability (BOCPD, CUSUM) — a break sensor, not a class.
4. Continuous boundary / channel (16856) — may be a bot/Book object, not a MIS class.

A classification F1 on (1) is not automatically decision value for (placement). That is the experiment criterion, not a new subsystem.
