---
review: reconcile — intake fidelity
target: architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md
authority: research-backtesting/specs/ (INDEX + 13 intake dossiers), challenge-mechanics.md, challenge-economics.md, challenge-override.md; secondary: backtesting-direction-position.md v2 (ADs demoted; QMB spine supersedes premature AD-42..45)
lens: independent reconcile of load-bearing intake against the B-id spine
date: 2026-08-20
verdict: PASS WITH FINDINGS — 2 material, 5 medium, 8 low
---

# Reconcile review — intake dossiers vs QMB spine

The `research-backtesting/specs/` files are **intake dossiers**, not specs. The campaign method was called spec-driven; the artifacts are reverse-engineering intake. This pass checks every INDEX key finding and every challenge BROKEN/WOUNDED item against `ARCHITECTURE-SPINE.md` (B-1..B-14 + Deferred). Direction-position v2 is context only: the QMB spine is the authority that was supposed to absorb the v2 fixes.

**Scoring:** LANDED IN FULL / LANDED WEAKENED / DID NOT LAND / DEFERRED EXPLICITLY. Deferred rows are not misses unless the finding was load-bearing for v1 **and** the spine is silent (neither a B-id nor a Deferred row). No new product direction. No re-decision of QMF law.

---

## Verdict

The organizing intake — injected frontier clock, config compiler, logs-then-ledger, process-per-run, three fill/cost ports, provenance-derived world, TPE-class sampler, same-library research surface, canonical artifact with downstream render, fetch-at-runtime data, declarative streams + Cartesian sweeps, validation ladder — all reached a B-id, and the challenge BROKEN synthetic-taint hole closed in full at B-7. Two load-bearing INDEX differentiators did **not** land as named obligations: Lean-style **parameter-sensitivity / clustering** (the anti-overfit half of `spec-optimization.md`'s verdict) and the **completed-bar visibility / forming-bar** look-ahead rule (loop R6 + routes R2/R7), which B-2/B-12 prevent by slogan but never bind. The snapshot-vs-live BROKEN finding landed as a hub diagram, not a freshness contract. Several quieter intake constraints (optimize constraints and Grid, lowest-fidelity-wins, license-tag at ingest, secrets-out-of-fingerprint, per-run cancel/limits) have neither a B-id nor a Deferred row.

Nothing ratified was inverted. Jesse's three-stack failure, np.random-as-Optuna, synthetic-as-edge, and MCP-over-HTTP topology are named and refused. GAP-0048/0049 cargo is correctly deferred.

---

## Part A — INDEX rows (13)

Each row starts from the INDEX one-line verdict, then scores the load-bearing requirements behind it.

### A.1 `spec-backtest-loop.md` — one seam: injected frontier clock; borrow split-candle fills

**Intake finding:** engines diverge on one axis — Jesse fixed 1-minute grid with no clock seam; LEAN data-driven frontier clock, injected, so one loop serves backtest/live by swapping handlers. Adopt LEAN slice+clock; borrow Jesse split-candle intra-bar fill. 11 requirements.

| Req | Intake | Where | Verdict |
|---|---|---|---|
| R1 one loop, injected clock | single run-loop; worlds differ only by clock + handlers | B-2 | **LANDED IN FULL** |
| R2 data-driven frontier, monotonic, UTC-ns | min next-emit; never rewind | B-2 + inherited AD-8 | **LANDED IN FULL** (B-2 even names the clock is *not* AD-8's diagnostic kind) |
| R3 event slice as time unit; time pulses | all data at an instant in one slice; empty pulse still advances clock | B-2 "event-slice"; pulses un-named | **LANDED WEAKENED** |
| R4 deterministic sub-phase + instrument order | documented order; bit-reproducible | B-2 "per-slice sub-phase order and instrument order are fixed and documented" | **LANDED IN FULL** |
| R5 warm-up pre-seed, trading-locked | refuse orders; `is_warming_up`; one `on_warmup_finished`; missing data names instrument+range | B-2 "pre-seeded, trading-locked phase; acting during warm-up is a typed refusal" | **LANDED WEAKENED** — flag, finished-callback, corporate-action skip, and missing-range refusal dropped |
| R6 higher-TF aggregation without look-ahead | bars emit only on completed boundaries; **a bar MUST NOT be visible before its close** | B-12 declared streams; B-2 prevents "look-ahead via time arithmetic" | **DID NOT LAND** as a bar-visibility rule — see Finding 1 |
| R7 intra-bar fill fidelity | split at fill price; residual re-eval; declared path | B-6 "declared-path bar splitting … never end-of-bar teleporting" | **LANDED IN FULL** |
| R8 config-materialized handlers | data/clock/fill/sink from config | B-3 | **LANDED IN FULL** |
| R9 log-during, save-at-completion | unbiased verdict; equity sampled on a fixed cadence; non-positive portfolio halts | B-4 logs + one ledger line + pass/fail/`unrated`/`aborted` | **LANDED WEAKENED** — cadence sampling and non-positive halt absent |
| R10 bounded, cancellable, observable | per-step and total time/memory limits; cancel token; throughput; typed terminal | B-5 process isolation + 12–14 as AD-13 reference | **DID NOT LAND** — no B-id, not Deferred. See Finding 5 |
| R11 sparse/heterogeneous first-class; fill-forward opt-in | typed event with own emit-time; fill-forward per subscription | B-2 event-slice implies the unit; fill-forward un-named | **LANDED WEAKENED** |

**Row verdict: LANDED IN FULL** on the INDEX axis (the seam). Two load-bearing sub-rules (bar-not-visible-before-close; per-run cancel/limits) are silent.

---

### A.2 `spec-fill-fees.md` — neither donor has a usable retail-forex model

**Intake finding:** take LEAN's three pluggable interfaces (fill/slippage/fee) + Jesse split_candle sequencing; QMX originates forex spread/slippage/swap content. GAP-0048 confirmed as original work.

| Req | Intake | Where | Verdict |
|---|---|---|---|
| Three separate ports | fill, slippage, fee as distinct contracts | B-6 "fills, slippage, and costs are three separate ports" | **LANDED IN FULL** |
| FILL-1 Fill \| NoFill + typed refusal | no silent zero-fills; itemized costs; exact-integer money | B-6 `Fill \| NoFill + itemized costs` | **LANDED IN FULL** |
| FILL-2 order-type catalog | Market/Limit/Stop/Stop-Limit/Trailing/MOO/MOC/OCO | GAP-0048 "forex fill … content" | **DEFERRED EXPLICITLY** |
| FILL-3 direction-aware bid/ask; synthetic spread when no quotes | never silently fill buy=sell | B-6 names spread as QMX-original; content in GAP-0048 | **DEFERRED EXPLICITLY** (seam held) |
| FILL-4 worst-case default; optimistic exact-price as labeled option | honest default vs Jesse-exact as a distinct fidelity | B-6 **all** fills carry `optimistic` taint until GAP-0048 | **LANDED WEAKENED** — conservative substitution, undisclosed against FILL-4's default. Acceptable as interim; the spine does not record that it overrode the intake default |
| FILL-5 trigger rules + stale-data guard | refuse resting fills when bar end precedes order; hold market fills past `stale_price_span` | GAP-0048 content | **DEFERRED EXPLICITLY** |
| FILL-6 intra-slice sequencing | split_candle | B-6 | **LANDED IN FULL** |
| FILL-7 gap handling + `gap_fill` marker | gapped price, not skip | GAP-0048 (weekend gaps named as fill-engine work in direction v2) | **DEFERRED EXPLICITLY** |
| FILL-8 partial fills & partial lots | Jesse has them; LEAN backtest does not; retail FX needs them | GAP-0048 content; not named even as a seam | **DEFERRED EXPLICITLY** as fill content — quiet as a v1 *capability* (see Part C) |
| SLIP catalog / SPREAD hour-of-day / FEE catalog / FEE-4 swap+triple-Wednesday | originated content | GAP-0048 "forex fill/slippage/swap content"; B-6 "financing/admin fee" vocabulary | **DEFERRED EXPLICITLY** |
| FEE-3 fee queryable before fill (margin admission) and at fill | LEAN double-call, same amount | silent | neither B-6 nor Deferred — **quiet drop** (Part C). Not v1-blocking while GAP-0048 owns content |
| LABEL-1 fidelity identity on every Fill | world, price basis, fill basis, models engaged | B-6 "declared fidelity identity that enters the result label" | **LANDED IN FULL** at identity; composition of the label **LANDED WEAKENED** |
| LABEL-2 lowest-fidelity-wins | one optimistic fill downgrades the whole run | silent | **DID NOT LAND** — see Finding 4 |
| LABEL-3 refuse to compare Books at different fidelities without override | machine-comparable labels | silent | **DID NOT LAND** (same finding family) |
| Optimistic taint cannot spend split / claim edge | direction v2 / challenge A7 fix | B-6 | **LANDED IN FULL** |

**Row verdict: LANDED IN FULL** on the INDEX finding (interfaces + original-work + GAP-0048). Fidelity *comparison* rules (LABEL-2/3) are the silent load-bearing remainder.

---

### A.3 `spec-optimization.md` — TPE-class sampler + Lean post-hoc sensitivity

**Intake finding:** Jesse's marketed Optuna is uniform `np.random` with Optuna as a SQLite ledger. Lean ships grid/Euler-zoom. Neither is Bayesian. QMB differentiator: genuinely adaptive sampler (TPE-class) **+ Lean-style post-hoc parameter-sensitivity for overfit detection**.

| Req | Intake | Where | Verdict |
|---|---|---|---|
| OPT-12 TPE-class default; reject Jesse random | real sampler, past trials inform next | B-8 + stack `optuna 4.9.0`; B-8 Prevents names Jesse's failure | **LANDED IN FULL** |
| OPT-1 schema int/float/**categorical**, min/max/step/default | Jesse schema, not Lean numeric-only | B-8 "name, type, bounds, step, default" | **LANDED WEAKENED** — categorical not named |
| OPT-2/3 space in config; invalid → typed refusal | never a code edit | B-8 + B-3 + inherited AD-11 | **LANDED IN FULL** (validation implied by schema-validated config) |
| OPT-5 objective = `{metric, direction}` not Jesse compound fitness | named metric + min/max; optional target_value | B-8 "Objectives are named metrics from B-10's canonical set" | **LANDED WEAKENED** — direction and early-stop target dropped |
| OPT-6 hard constraints `{metric, op, value}` | Lean; "Drawdown <= 0.25"; violating trial logged but excluded from winner | silent | **DID NOT LAND** — see Finding 2 |
| OPT-7 min-trades gate as a constraint | Jesse `<5` generalized | silent | **DID NOT LAND** (rides with OPT-6) |
| OPT-9 train/test split; score on train, record test | Jesse split | B-8 "Train/test separation is declared in the run spec and enforced by split-manifest reads (AD-21)" | **LANDED IN FULL** |
| OPT-10 locked **validation** window never touched during the Study | third window; ledger pass/fail MAY require it | silent | **DID NOT LAND** — not Deferred (GAP-0049 is thresholds/attempt-count, not the window) |
| OPT-13 Grid + Euler as optional modes | Grid for small spaces + reproducibility; Euler local zoom; mode is a config field | silent | **DID NOT LAND** |
| OPT-14 bounded pool 12–14; pending queue | Lean enqueue-on-full | B-5 | **LANDED WEAKENED** — cap exists; enqueue/backpressure unstated (see A.12) |
| OPT-16 one trial crash = failed, does not abort the Study | Lean failed-count | B-4 `aborted` per run; B-8 every trial is a run | **LANDED WEAKENED** — implied by isolation, not stated for the Study |
| OPT-17 trial budget explicit | fixed N / scale-with-params / until-target | GAP-0049 attempt counting | **DEFERRED EXPLICITLY** |
| OPT-18 terminable `stopped` with partial preserved | Jesse termination poll | B-4 `aborted` | **LANDED WEAKENED** — aborted ≠ clean stopped-with-partial |
| OPT-19/20 per-trial log + Study ledger with top-N + param fingerprint | DNA/hash; train/test/validation metrics | B-4 + B-8 every trial a ledger line; B-12 aggregation is a read view | **LANDED WEAKENED** — top-N, DNA, Study-level record un-named |
| OPT-21 unbiased pass/fail on reserved validation | or explicitly "not validated" | B-4 vs Book bar / `unrated` | **LANDED WEAKENED** — Book bar is not the locked holdout |
| **OPT-22 parameter-sensitivity / clustering / isolated-spike flag** | **INDEX differentiator; Lean OptimizationAnalyzer** | **nowhere** | **DID NOT LAND** — Finding 2 |
| OPT-23 resume from persisted trials | Jesse session | silent | **DID NOT LAND** (useful, not INDEX-load-bearing) |
| OPT-24 dry-run estimate | Lean `--estimate` | silent | **DID NOT LAND** (not load-bearing) |

**Row verdict: LANDED WEAKENED.** The TPE half of the INDEX verdict is B-8. The sensitivity half is absent from B-ids and Deferred.

---

### A.4 `spec-synthetic-data.md` — L20 survives contact; store-level taint

**Intake finding:** LEAN "Brownian" is a bounded uniform random walk with **no provenance tag** (indistinguishable from real — the backdoor QMB taints against). Jesse moving-block bootstrap (perturbing real history) is the only method that can claim robustness. Claim class derives from whether the process was seeded from real data.

| Req | Intake | Where | Verdict |
|---|---|---|---|
| R3 claim classes; refuse edge on synthetic | infra-stress / robustness / logic-smoke; never edge | B-7 two classes: random-walk → infra-stress; block-bootstrap → robustness under B-14; nothing synthetic validates edge | **LANDED WEAKENED** — `logic-smoke` dropped |
| R4 store-level `origin=synthetic` taint; world derived, never caller-declared | closes LEAN's indistinguishable-files gap | B-7 | **LANDED IN FULL** — the INDEX finding |
| R2 process menu | block-bootstrap default; gaussian-resample/noise; gbm infra-only; regime-switching OPEN | B-7 two *classes*, not five processes | **LANDED WEAKENED** — classes hold; named processes (incl. "correct GBM vs Lean's uniform walk") dropped |
| R1 generator config is a first-class artifact | wind-tunnel | B-3 + B-11 `generate` | **LANDED IN FULL** |
| R5 QMX-owned pinned RNG; scenario 0 = untouched original | do not depend on runtime stdlib Random | B-13 RNG provenance; scenario-0 un-named | **LANDED WEAKENED** |
| R6 exact money, UTC-ns, **market-hours-aware** FX grid | weekend gap / session boundaries (Lean lesson Jesse crypto lacks) | inherited AD-7/AD-8; B-11 calendars | **LANDED WEAKENED** — calendar exists; synthetic generator is not bound to it |
| R7 percentile bands / CI / p-value / pre-declared threshold | Jesse robustness table = ledger-native | B-14 procedures versioned as contracts; thresholds GAP-0048/0049 | **LANDED IN FULL** on mechanics; **DEFERRED EXPLICITLY** on threshold values |
| R8 typed refusals | edge-claim, promote-to-replay, missing source | inherited AD-11 + B-7 policy rejection | **LANDED IN FULL** |

**Row verdict: LANDED IN FULL** on the INDEX finding (taint + claim-from-provenance). Process menu and logic-smoke are weakenings, not inversions.

---

### A.5 `spec-reports.md` — one canonical artifact; charts as data; render downstream

**Intake finding:** both engines compute chart data then throw it away into PNGs/strings. QMB inverts: ONE canonical unit-kinded exact-money artifact (CT-32), chart series as data, HTML a pure downstream function.

| Req | Intake | Where | Verdict |
|---|---|---|---|
| R-RPT-1 one CT-32 artifact, two audiences | no separate report JSON that can drift | B-10 + inherited AD-41/CT-32 | **LANDED IN FULL** |
| R-RPT-2..7 full AD-12 label; unit-kinded; exact money/time; versioned arithmetic; float-identity ban; one account role | CT-32 invariants | B-10 + inherited AD-7/10/12/40 | **LANDED IN FULL** |
| R-RPT-5 metric arithmetic change mints a contract version | Lean 252 vs Jesse 365 made identity | B-10 "metric arithmetic changes mint a contract version" | **LANDED IN FULL** |
| R-RPT-8 suppression + veto accounting | QMX-native; no donor analogue | inherited AD-41/CT-32; **B-10 does not restate** | **LANDED WEAKENED** — inherited, quiet at QMB altitude |
| R-RPT-9/10 measurement never acts; no composite score | CT-32 invariants 12/13 | inherited AD-32/CT-32; not restated in B-10 | **LANDED WEAKENED** (quiet) |
| R-RPT-11/12 series as data, never pixels; no color in data | reject both donors' PNG default | B-10 "chart series as data … All human-facing rendering is a pure downstream function … adds no computation" | **LANDED IN FULL** on the INDEX finding; series *shape* un-specified (**WEAKENED** at schema) |
| R-RPT-13 analytics chart set | equity, drawdown, underwater, monthly grid, distributions, allocation, leverage | B-10 lists *price* series (candles, execution markers, overlays, extra panes) | **LANDED WEAKENED** — report analytics series collapsed into "chart series as data" without the curated set |
| Curated V1 metric union | Sharpe/Sortino/Calmar/win-rate/streaks/…; extended vs rejected (crisis windows, capacity, magic-cap-10) | B-10 "the named metric set, versioned" — set never named | **LANDED WEAKENED** |
| R-RPT-14 derive holdings/leverage from the fill/position stream | Lean PortfolioLooper | B-10 "the trade record" | **LANDED WEAKENED** |
| R-RPT-15 benchmark optional + labeled | absent ⇒ omit, never fake | silent | **DID NOT LAND** |
| R-RPT-16..20 ledger line; structural pass/fail vs Book bar; not a score | operator unbiased end result | B-4 | **LANDED IN FULL** |
| R-RPT-21 HTML + **markdown**; renderer computes nothing | Lean token-replace instinct | B-10 "HTML report, UI charts"; markdown un-named | **LANDED WEAKENED** |
| R-RPT-22 in-house skills read the artifact, never HTML | agent-consumable | B-10 | **LANDED IN FULL** |
| R-RPT-23 annualization / rf / benchmark from Book config | identity of Sharpe | B-3 config; annualization/rf un-named at QMB | **LANDED WEAKENED** |
| Rejected: US-equity crisis list, strategy capacity, formatted-string KPIs, magic-cap-10 | intake explicit rejects | correctly absent | **LANDED** as absence |

**Row verdict: LANDED IN FULL** on the INDEX inversion (artifact-first, render-downstream). Benchmark optionality and the curated metric/chart lists are the silent remainder.

---

### A.6 `spec-research-jupyter.md` — same library; Jesse functions + Lean DataFrame ergonomics

**Intake finding:** both prove the research surface must be the SAME library. Jesse: pure importable functions (portable, uv-installable). Lean: Docker/CoreCLR. Take Jesse's function architecture **with Lean's DataFrame ergonomics**.

| Req | Intake | Where | Verdict |
|---|---|---|---|
| R1 importable, server-free, Docker-free; no implicit project dir | fixes Jesse `is_jesse_project()` guard | B-9 | **LANDED IN FULL** on portability; implicit-project-dir fix is quiet |
| R2 same config as CLI; no surviving global state | wind-tunnel; Jesse reset is a facade | B-3 + Conventions "No module-global mutable state" | **LANDED IN FULL** — and names the donors' central defect |
| R3 day-one surface | history, indicator-over-history, backtest, `portfolio_statistics` (score any equity curve), MC, optimize, significance; ML optional extra | B-9 "the library's own pure functions"; B-14 ladder | **LANDED WEAKENED** — indicator-over-history and score-any-curve un-named |
| **DataFrame ergonomics** | INDEX verdict half; typed array underneath | **nowhere** | **DID NOT LAND** — Finding 6 |
| R4 pure + process-safe for 12–14 | Jesse stated goal, QMF makes it real | B-5, B-9 | **LANDED IN FULL** |
| R5 QMF law + injected clock (must not read `UtcNow`) | Lean QuantBook ctor reads wall clock — reject | inherited AD-8/11/12; B-2 | **LANDED IN FULL** |
| R6 logged then ledgered | progress + completion record | B-4 | **LANDED IN FULL** |
| R7 sealed never leaves controlled rooms; portable gets unsealed only | challenge Attack 5 fix | B-9 | **LANDED IN FULL** |
| R8 MCP optional, not required to use the library | | B-1 MCP later; B-9 is the library | **LANDED IN FULL** |

**Row verdict: LANDED WEAKENED.** Same-library + portable + seal scoping landed. The INDEX's "with Lean's DataFrame ergonomics" half is gone.

---

### A.7 `spec-data-mgmt.md` — acquire like Jesse, organize like Lean

**Intake finding:** Jesse's "ship no data, fetch at run-time under the user's own exchange relationship" clears QMX's licensing gate. Lean's map-files/factor-files/market-hours-DB is the organization model for `(venue,symbol)+calendar`.

| Req | Intake | Where | Verdict |
|---|---|---|---|
| Acquisition posture | fetch at runtime; ship/redistribute nothing | B-11 Dukascopy primary; "QMB ships and redistributes no market data" | **LANDED IN FULL** — the INDEX finding |
| Bid+ask preserved; rooms; bitemporal; UTC-ns; exact money | Lean tickType split; reject Jesse Float OHLCV | B-11 "CT-10/CT-15 intake, rooms, bitemporal law, bid+ask preserved" | **LANDED IN FULL** |
| `(venue, symbol) + resolution + world-scoped rooms` | Lean addressing tuple | B-11 | **LANDED IN FULL** |
| Calendars from QMF calendar contracts | Lean market-hours DB (two tz, sessions, holidays, always-open) | B-11 | **LANDED IN FULL** as pointer |
| R1 machine-observable progress (percent/ETA/date-reached) | Jesse Redis pattern; agents watch long imports | silent | **DID NOT LAND** |
| R1 provenance + **license tag**; typed refusal when source lacks the right | old Dukascopy corpus failed this gate | B-11 posture only; tag/refusal un-named at QMB | **LANDED WEAKENED** — Finding 3 |
| R2 `verify` / gap-check against calendar | distinguish closed vs missing; range-integrity; no silent fabricate | B-11 command `verify` exists; mechanism unstated | **LANDED WEAKENED** |
| R3 catalog | "do I already have this window?" | B-11 `catalog` | **LANDED IN FULL** as command |
| R4 factor/split manifest + symbol-identity map | Lean factor files / map files | inherited AD-21 split manifests; map-files un-named | **LANDED WEAKENED** — FX-primary, intake itself asked whether to defer maps |
| R6 12–14 concurrent import; per-provider rate-limit | | B-5; rate-limit un-named | **LANDED WEAKENED** |

**Row verdict: LANDED IN FULL** on the INDEX split (acquire-like-Jesse / organize-like-Lean-via-QMF). License-tag *enforcement* and import progress are the silent remainder.

---

### A.8 `spec-cli-config.md` — CLI is a config compiler

**Intake finding:** Lean's CLI is a config COMPILER — the engine only ever reads one fully-resolved, read-only config.json per run; that artifact is the run definition, the fingerprint source, and the ledger key. Precedence: flag > project config > workspace config > defaults.

| Req | Intake | Where | Verdict |
|---|---|---|---|
| R-CLI-1 one resolved immutable config; engine does not re-layer | Lean read-only mount | B-3 | **LANDED IN FULL** |
| R-CLI-2 Book/BMS compile to versioned fragments, never mutate | | B-3 "never free-hand-edited"; fragments DERIVED with AD-16 lineage | **LANDED IN FULL** |
| R-CLI-3 precedence | intake: flags > bot > BMS > Book > defaults | B-3: flags > run spec > **Book fragment + BMS fragment** > workspace defaults | **LANDED WEAKENED** — Book vs BMS not ordered against each other (Finding 8) |
| R-CLI-4 deterministic; layer attribution (which layer set which key) | audit | B-3 deterministic implied; attribution un-named | **LANDED WEAKENED** |
| R-CLI-5 unfittable Book/BMS = typed refusal; **"test = can a bot fit the Book"** | compile-time fit | inherited AD-32 prediction linter; QMB B-3 does not bind fit | **LANDED WEAKENED** — quiet at QMB (Part C) |
| R-CLI-6 secrets/infra **out of the fingerprint region** | Lean credentials Storage; Jesse `.env` | silent | **DID NOT LAND** — Finding 7 |
| R-CLI-9/10/11 resolved artifact in run dir; fingerprint; run id | Lean `:latest` trap named as the thing we fix | B-3 Prevents "Lean’s `:latest` determinism trap"; artifact + fingerprint = ledger key | **LANDED IN FULL** |
| R-CLI-12/13 logs + ledger; crash-safe under 12–14; no shared mutable config | reject Jesse global dict | B-4 WriterId fragments; B-5; Conventions no globals | **LANDED IN FULL** |
| R-CLI-14 typed machine-authored fragments; CLI the only writer | not hand-edited JSON5 | B-3 | **LANDED IN FULL** |
| R-CLI-15 researcher-friendly input expanded to strict | Jesse `_format_config` | silent | **DID NOT LAND** (convenience, not INDEX-load-bearing) |
| R-CLI-16 `uv tool` as npm analog | operator update story | B-13 **demotes** `uv tool` to CLI-only convenience; primary = `uv add qmb` because the Python API must be importable | **LANDED WEAKENED** — a disclosed correction, not a miss. The reason is load-bearing and stated |
| R-CLI-17 throttled outdated-check; print upgrade command; never auto-upgrade | Lean 24h warn | silent | **DID NOT LAND** |
| R-CLI-18 engine-image digest auto-update | Lean Docker | spine rejects required Docker; N/A | correctly absent |
| Command tree (init/book/bms/bot/backtest/optimize/research/report/data/config/ledger/self) | Lean-shaped | capability map + structural seed `doors/cli`; tree not enumerated | **LANDED WEAKENED** |
| Config format JSON, schema-validated, comments in docs | | Conventions | **LANDED IN FULL** |
| Click + autocomplete | Lean stock Click; QMB adds registry enumeration | B-1 + stack click 8.4.2 | **LANDED IN FULL** |

**Row verdict: LANDED IN FULL** on the INDEX finding (compiler + one artifact + fingerprint + `:latest` trap). Secrets-out-of-fingerprint and Book/BMS co-layering are the silent remainder.

---

### A.9 `spec-multi-routes.md` — declarative streams + Cartesian isolated runs

**Intake finding:** Jesse declarative routes for the per-run stream set + Lean's Cartesian batch generalized to symbol×TF×params — each combo one isolated, labeled ledger run.

| Req | Intake | Where | Verdict |
|---|---|---|---|
| R1 declared stream set; trading vs data-only | Jesse routes / data_routes | B-12 | **LANDED IN FULL** |
| R2 **1m (or finest native) spine; higher TF folded; emit only on aligned boundaries** | Jesse deterministic core; Lean consolidators as future bar-types | B-2 is LEAN event-slice, not a 1m spine | **LANDED WEAKENED** — mechanism substituted, **undisclosed** (Finding 1 family) |
| R3 candle contract `[t,O,H,L,C,V]` UTC-ns exact integer; not Jesse O,C,H,L | footgun | QMF data contracts; not restated at QMB | quiet / inherited |
| R4 uniqueness relaxed | one *position* per (venue,instrument); many TFs as data; many TFs across sweep runs | silent | **DID NOT LAND** |
| R5 settlement uniformity | all trading streams share one quote asset | silent | **DID NOT LAND** |
| R6 `get_bars` only through declared set; undeclared = typed refusal | Jesse `RouteNotFound` | B-12 "strategies read other streams only through the declared set" | **LANDED WEAKENED** — refusal un-named |
| R7 forming-bar policy; completeness inspectable | no future in live; opt-in in replay | silent | **DID NOT LAND** — Finding 1 |
| R8 `on_peer_*` callbacks | Jesse `on_route_*`; intake's multi-agent primitive | silent | **DID NOT LAND** |
| R9 Cartesian product; **pre-flight total count** before commit | operator sees size | B-12 Cartesian; pre-flight un-named | **LANDED WEAKENED** |
| R10 each combo one isolated labeled run | | B-12 | **LANDED IN FULL** |
| R11 aggregation/ranking is a read view over the ledger, never a merged run | | B-12 | **LANDED IN FULL** on the anti-merge; ranking/constraints un-named |
| R12 one combo's refusal does not abort the batch | | implied by B-5 isolation | **LANDED WEAKENED** |

**Row verdict: LANDED WEAKENED.** The INDEX composition (declarative per-run set + Cartesian isolated runs) is B-12. The 1m-spine / completed-boundary / forming-bar cluster is the look-ahead hole. Uniqueness, settlement, and peer callbacks are dropped primitives.

---

### A.10 `spec-mc-significance.md` — pre-build signal-only gate; Lean has none

**Intake finding:** Jesse "test the edge before you build": signal-only pass through the real engine with **orders disabled**, then bootstrap of signal×next-bar detrended log-returns against a zero null. Lean has no pre-build test.

| Req | Intake | Where | Verdict |
|---|---|---|---|
| R-MC-1 rule-significance gate | signal-only; next-bar alignment; detrend then re-centre H0; one-tailed p; iid vs block as config; n≥2000; min-obs refusal | B-14 "signal-only run-loop pass with orders disabled, bootstrap against a detrended zero-edge null"; procedure versioned as a contract | **LANDED IN FULL** on the INDEX finding; statistical knobs (next-bar, iid/block, n, min-obs, advisory-not-auto-merge) live in the versioned contract, not the B-id — **acceptable WEAKENING** at spine altitude |
| R-MC-2 two MC modes | trade-shuffle (sequence risk) + moving-block candle bootstrap (alternate history); scenario 0 = original; percentiles/CI/p; seeds `base+index` | B-14 "Monte Carlo (trade-shuffle; real-seeded candle perturbation)" | **LANDED IN FULL** on modes; output-shape/scenario-0 **WEAKENED** |
| **R-MC-3 findings, not just numbers** | Lean ResultsAnalyzer: `{verdict, metric, statistic, threshold, plain-language issue, suggested action, weight}`; time/finding budget; muteable | **nowhere** | **DID NOT LAND** — Finding 2 family |
| R-MC-4 RNG family, seed derivation, scheme, window, world in the label | R-8 | B-13 RNG provenance; B-8 sampler identity + seed | **LANDED IN FULL** |
| R-MC-5 PBO bands, CSCV S=16, chain gate→backtest→MC/PBO/CSCV | old governance battery | Deferred "PBO bands, CSCV remain candidates for GAP-0048/0049"; B-14 walk-forward mechanics ship | **DEFERRED EXPLICITLY** on batteries; walk-forward **LANDED** as a procedure |
| Reject Lean 5-sim / integer-division percentile | anti-pattern | correctly un-copied | **LANDED** as absence |

**Row verdict: LANDED IN FULL** on the INDEX finding (the pre-build gate). The Lean-shaped findings layer is the silent take-from-Lean half of §3.

---

### A.11 `spec-charts-ui.md` — Lean domain model + SeriesSampler; reject TradingView coupling

**Intake finding:** Jesse's chart JSON is coupled to TradingView Lightweight-Charts field names and never downsamples. Lean keeps a renderer-agnostic domain model with wire converters + SeriesSampler. Copy Lean's separation; emit self-describing per-bot chart JSON agents read directly.

| Req | Intake | Where | Verdict |
|---|---|---|---|
| Domain vs renderer split | payload is not the frontend library's model | B-10 rendering is downstream; adds no computation | **LANDED IN FULL** |
| CH-7 downsampling by a declared sampler | the Lean lesson Jesse lacks; bound size for 12–14 | B-10 "downsampled by a declared sampler" | **LANDED IN FULL** |
| Candles, execution markers, overlays, extra panes | | B-10 | **LANDED IN FULL** as the series kinds |
| CH-1 one artifact per (run, bot); never collapse bots | Jesse per-route slicing | B-10 one canonical result artifact | **LANDED WEAKENED** — per-bot slicing un-named |
| CH-4 semantic `side`/`effect`, not `aboveBar`/`arrowUp` | reject Jesse frontend vocab | un-named; implied by renderer-agnostic | **LANDED WEAKENED** |
| CH-5 pane by integer index, not name-string | Lean Index/ZIndex | "extra panes" only | **LANDED WEAKENED** |
| CH-8 self-describing (schema_version, time_unit, price_scale, columns legend) | agents `json.load` with no external context | un-named | **LANDED WEAKENED** |
| Live/streaming deltas | intake v1 = completion snapshot | Deferred UI rendering; correctly out of v1 | **DEFERRED EXPLICITLY** (UI) |
| Portfolio-analytics charts vs price charts | intake recommends split | B-10 mixes both under "chart series as data" | **LANDED WEAKENED** (see A.5 R-RPT-13) |

**Row verdict: LANDED IN FULL** on the INDEX finding (separation + sampler). Schema-level CH-* rules are altitude-appropriate weakenings except per-bot slicing, which is a real agent-scoping rule.

---

### A.12 `spec-concurrency.md` — process-per-run because donors hold globals; QMF makes it a CPU choice

**Intake finding:** both isolate by OS process **because** they hold mutable globals. QMF's immutable core makes process-per-run a free CPU-parallelism choice, not a crutch. The operator's log-during/save-at-completion ledger is Lean's `process.Exited → read result.json → record` cycle. 12–14 concurrent: process-per-run, bounded by cores.

| Req | Intake | Where | Verdict |
|---|---|---|---|
| C-1 library never spawns | parallelism is the caller's | inherited AD-15; B-5 process management is the orchestrator (CLI/runner) | **LANDED IN FULL** |
| C-2 isolation by process | stdlib; no Ray required; no Docker required | B-5 "stdlib process management"; "No Ray, no required Docker, no daemon" | **LANDED IN FULL** |
| C-3 per-run isolated output room | Lean "else they fight for log.txt" | B-5 isolated output directory | **LANDED IN FULL** |
| C-4 streamed per-run logs | logs, not journals | B-4 append-only per-run logs in the run dir | **LANDED IN FULL** |
| C-5 ledger append is the single write-back | Lean Exited → NewResult | B-4 ONE ledger entry at completion; WriterId-scoped fragments; Windows non-atomic-append caveat carried | **LANDED IN FULL** — more precise than intake |
| C-6 governed cap + **enqueue-on-full** + typed refusal over ceiling | Lean PendingParameterSet | B-5 "parallelism is bounded by cores" | **LANDED WEAKENED** — cap yes; enqueue vs drop vs refuse unstated |
| C-7 cap ≈ physical cores; **memory is the real limiter**; IO-phase MAY oversubscribe | Ryzen-9 12–14 as a measured target | B-5 12–14 is "a motivating reference under AD-13, never a validated budget" | **LANDED WEAKENED** — AD-13 honesty is better than a fake budget; memory-min and phase-aware oversubscribe dropped |
| C-8 determinism across the fan-out | concurrency MUST NOT touch computed values | B-2 identical inputs → identical slices; B-5 isolation | **LANDED IN FULL** |
| C-9 abort one process; crashed run does not append a half row | Lean AbortLean; absence is a typed outcome | B-4 crashed/aborted ledger as `aborted` with refusal context — never silently absent | **LANDED IN FULL** (and stronger: aborted *is* a row) |
| Reject Jesse globals / Lean Docker-per-run / billed cloud nodes | | B-5; Deferred cloud-burst | **LANDED IN FULL** |

**Row verdict: LANDED IN FULL** on the INDEX finding. Backpressure and memory-as-limiter are the operational weakenings.

---

### A.13 `website-visuals.md` — provenance as trust axis; validation ladder as table stakes

**Intake finding:** both platforms market **provenance** — Jesse's "Real results, not hallucinations: every number comes from the engine; the agent calls real tools." The validation ladder (backtest → optimize → MC → significance → walk-forward) is table stakes. Local-first / self-hosted is the headline trust claim.

| Claim | Where | Verdict |
|---|---|---|
| Provenance: agents read real artifacts, never renderings | B-10 "Agents and in-house skills read the artifact, never renderings" | **LANDED IN FULL** |
| Validation ladder as table stakes | B-14 names the full ladder including walk-forward; thresholds Deferred | **LANDED IN FULL** |
| Local-first / no daemon / same package on laptop and sandbox | B-5, B-9, B-13 | **LANDED IN FULL** |
| MCP as agent day-to-day | B-1 MCP post-CLI-v1; Deferred "MCP door details" | **DEFERRED EXPLICITLY** |
| Jesse Benchmark (batch compare across TF/symbol/strategy) | B-12 permutation sweeps + ledger read-view | **LANDED IN FULL** as sweeps |
| Interactive charts | B-10 series; Deferred UI rendering | **LANDED** data; **DEFERRED** UI |
| No look-ahead bias (Jesse homepage) | B-2 / B-12 Prevents lines; GAP-0016/0017 look-ahead *gate* Deferred | **LANDED WEAKENED** — slogan yes; bar-visibility rule no (Finding 1) |
| ML pipeline (Jesse marketed) | research R3 said optional extra | correctly absent from v1 B-ids; not Deferred. **Quiet drop** — not load-bearing for v1 |
| Walk-forward / train-test / overfitting warnings | B-14 WF; B-8 train/test; OPT-22 sensitivity **missing** | ladder yes; anti-overfit *analysis* no (Finding 2) |

**Row verdict: LANDED IN FULL** on provenance + ladder. MCP is the honest post-v1 deferral.

---

## Part B — Challenge BROKEN / WOUNDED items

Direction v2 folded these in; the QMB spine is what was supposed to absorb the fold. ADs 42–45 were demoted; this spine supersedes them.

### B.1 Mechanics (`challenge-mechanics.md`)

| Item | Finding | Spine | Verdict |
|---|---|---|---|
| **A1 BROKEN** snapshot is both frozen and live; auto-update fails on offline sandboxes | fingerprinted snapshot cannot also be live; DEC-0084 killed the always-on service | Structural diagram: `HUB[(sync hub: registry + ledger files)]`; B-13 `registry-state as-of`; B-3 compiler; inherited DEC-0084 "no central always-on service". **No B-rule for re-sync, honest staleness, or `stale-evidence` refusal** | **LANDED WEAKENED** — topology drawn, freshness contract not bound. Finding 3 |
| **A2 BROKEN** writes ignored; N sandboxes minting vs AD-15 one-writer; R-7 siblings vs AD-10 collisions | write-back unspecified | B-4 WriterId-scoped fragments; B-5 "merging happens only in read views"; completion is the single write-back. **R-7 "label-identified float-differing artifacts are lineage siblings"** not restated | **LANDED WEAKENED** — write path yes; sibling-vs-collision clause quiet (inherited AD-10 may alarm legitimate parallel minting) |
| **A3 WOUNDED** "no door carries logic" | doors necessarily carry adaptation (parse, transport, refusal render, autocomplete) | B-1 "thin hand-written wrappers carrying only adaptation logic (parsing, transport, refusal rendering, registry enumeration for autocomplete)"; parity by tier-2 contract test, not codegen | **LANDED IN FULL** |
| **A4 WOUNDED** UI backend unbound; Jesse MCP stacked on HTTP | rule UI as consumer; MCP sibling in-process | B-1 "UI backend consumes the Python API in-process; MCP is a sibling door over the same library (never stacked over HTTP)" | **LANDED IN FULL** |
| **A5 WOUNDED** MCP long-lived; auto-update worst at the agent door | per-call re-resolve or stamp `registry_as_of` in every tool result | B-1 MCP after CLI v1; Deferred "MCP door details (tool list, exposure beyond localhost)" | **DEFERRED EXPLICITLY** — acceptable (post-v1). The freshness hole remains for CLI/sandbox via A1 |
| **A6 BROKEN** `data generate` + `world=replay` is the edge backdoor | world must be derived from store-level taint | B-7 | **LANDED IN FULL** |
| **A7 WOUNDED** "replay-first ships now" oversells; fill is GAP-0048 | clock legal; verdict-bearing backtest waits; interim = `fidelity=optimistic` | B-6 optimistic taint; cannot spend split budget; cannot claim edge; GAP-0048 Deferred | **LANDED IN FULL** |
| **A8 WOUNDED** two-item label; need QMB+QMF ladders, R-8 seeds, as-of, fidelity | do not restate a shorter list than AD-12 | B-13 QMB version, QMF roster version (separate ladders), resolved-config fp, registry-state as-of, data/split fps, world, RNG provenance; B-6 fidelity identity | **LANDED IN FULL** |

### B.2 Economics (`challenge-economics.md`)

| Item | Finding | Spine | Verdict |
|---|---|---|---|
| §1 fork-and-gut deletes the wrong 90%; forex fill has no reference | build-our-own HOLDS, was under-argued | inherited D1 "No donor code ever (shapes only); build-our-own"; B-6 "no donor reference exists" | **LANDED IN FULL** (costing paragraph is not spine altitude) |
| **2a WOUNDED/BROKEN** Jesse "pure-function API" is a facade over globals | only the bare signature ports | B-9 real pure functions; Conventions ban module-global mutable state "the donors' central defect" | **LANDED IN FULL** |
| **2b BROKEN** "the Jesse lesson" is a misattribution — Jesse is three heterogeneous stacks | present the shape as QMX's own; name Jesse as counter-example | B-1 Prevents "**Jesse's three-heterogeneous-stacks failure**" | **LANDED IN FULL** |
| **2c WOUNDED** LEAN composition skeleton is already QMX's; reflection banned | demote the donor row | Paradigm is QMB's own hexagonal config-composition; inherited AD-2 never ambient scanning | **LANDED IN FULL** as owned, not borrowed |
| **2d WOUNDED** Jesse sampler is np.random; reject it | use real Optuna samplers | B-8 TPE-class; Prevents "Jesse's naive-random-search-marketed-as-Optuna failure"; stack optuna 4.9.0 | **LANDED IN FULL** |
| **§3 WOUNDED/BROKEN** "mechanically" implies unbudgeted codegen; CLI has no clear user | thin hand-written wrappers + tier-2 test | B-1 hand-written; door parity by tier-2 contract test | **LANDED IN FULL** |
| **§4 WOUNDED** do not mint AD-42..45 onto the QMF spine | application-side; L21 | QMB is its own spine; inherited L21 "QMB is an application outside the QMF repo scope"; QMF stays AD-1..41 | **LANDED IN FULL** |
| **§5 WOUNDED** "80% already ratified" anchors a cheap increment; fill engine is the real cost | separate ratified contracts from unbuilt engineering | B-6 original-work sentence + GAP-0048 "irreversible; needs its own sitting" | **LANDED IN FULL** at honesty-of-deferral; no cost paragraph (not required at this altitude) |

### B.3 Override (`challenge-override.md`)

| Item | Finding | Spine | Verdict |
|---|---|---|---|
| **A1 BROKEN** snapshot vs live vs portable vs no central service | force the either/or | Hub diagram = option (a) snapshot+hub; DEC-0084 inherited | **LANDED WEAKENED** (same as Mechanics A1) |
| **A2 WOUNDED** central service returns through live registry | shared live state vs DEC-0084/0087 | Hub is files, not compute (diagram + DEC-0084); no live registry service | **LANDED IN FULL** on the choice; freshness still weak |
| **A3 WOUNDED** campaign budget minted before the run is the friction the dictation removes | strip it or ask; GAP-0017 deferred | GAP-0049 + GAP-0016/0017 Deferred "attempt counting (search-campaign candidate)"; B-8 every trial is a run so raw material accrues; **no pre-registration ceremony in B-8** | **DEFERRED EXPLICITLY** — v1 retraction held |
| **A4 WOUNDED** "synthetic sorts our problem" silently overruled; replay corpus failed licensing | name L20 vs dictation; do not assume a legal corpus | B-7 holds L20; B-11 fetch-at-runtime under the user's relationship (does not bundle the failed corpus) | **LANDED IN FULL** as posture. No ruling-ask belongs in a spine |
| **A5 WOUNDED** "Jupyter anywhere" guts the 12-month seal | sealed never leaves controlled rooms | B-9 | **LANDED IN FULL** |
| **A6 WOUNDED** AD-44 unexamined bundle (LEAN skeleton, MCP 0.0.0.0, shapes, "cloud" = sandboxes) | unbundle | Paradigm owned; B-1 MCP localhost-bound by default; B-8 schema; B-5 sandboxes are the scale story; Deferred cloud-burst | **LANDED IN FULL** |
| **A7 WOUNDED** asks omit liveness / MCP security / synthetic-vs-L20 / pre-reg / engine ban | convert buried decisions into asks | Spine *decided* them: hub, localhost MCP, L20, GAP-0049, Conventions ban "engine" | **LANDED IN FULL** as decisions (asks were a direction-paper defect) |
| **A8 WOUNDED** AD-42..45 on the QMF spine blur framework/app | record as app architecture | QMB spine; L21 inherited | **LANDED IN FULL** |
| **A9 WOUNDED** parts-count cannot refute a gestalt override | reframe as new organizing architecture at the interface, invariants untouched | QMB is a new feature-altitude spine; QMF AD-1..41 inherited read-only | **LANDED IN FULL** |
| HOLDS: Lean vs Jesse choice dissolves; `.qml` → GAP-0047 | | Deferred QML GAP-0047; D1 inherited | **LANDED IN FULL** |

---

## Part C — Quiet requirements the B-id structure dropped

Tone, constraint, and operator-slogan items that the AD/B compression tends to kill because they govern *how to read or refuse*, not *what to build*. Not all are misses (some are inherited QMF; some are altitude). Listed so they cannot die silently.

1. **"Test = can a bot fit the Book"** as a compile-time typed refusal (cli-config R-CLI-5). The operator's wind-tunnel slogan. AD-32 prediction linter exists on the QMF side; QMB B-3 never binds fit at the config compiler.
2. **Layer attribution** — which layer set which key, for audit (R-CLI-4).
3. **Secrets and infra out of the fingerprint region** (R-CLI-6). Without it, a credential rotation or a data-provider endpoint change retints every result label.
4. **Book vs BMS fragment precedence when both set the same key** (R-CLI-3). Spine adds them as one layer.
5. **Researcher-friendly flat input expanded to strict** (Jesse `_format_config`, R-CLI-15). Agents author simple; compiler is strict.
6. **`uv tool` outdated-check, never auto-upgrade, fail-open** (R-CLI-17) — the npm analog's *warning* half, after B-13 correctly demoted `uv tool` as a provisioner.
7. **Categorical parameters** in the bot schema (OPT-1) — Jesse had them; Lean did not; intake chose Jesse.
8. **Objective direction (min\|max) and optional early-stop target** (OPT-5).
9. **Hard optimize constraints** and the min-trades gate as a constraint (OPT-6/7).
10. **Locked validation window** never touched during the Study (OPT-10) — distinct from B-8's train/test split.
11. **Grid (and Euler) as optional sampler adapters** (OPT-13) — reproducibility mode for small spaces.
12. **Study-level top-N + stable parameter fingerprint ("DNA")** (OPT-20).
13. **Lean DataFrame ergonomics** (INDEX research verdict half) and the two QuantBook conveniences: indicator-over-history, score-any-equity-curve.
14. **No implicit project directory** for research (Jesse defect to refuse by name).
15. **Completed-bar visibility / forming-bar inspectability** (loop R6, routes R2/R7) — the look-ahead law at the bar, not just at the clock and the stream set.
16. **Time pulses** for empty slices (loop R3).
17. **Warm-up: `is_warming_up`, one finished callback, missing-range refusal naming instrument+dates** (R5).
18. **Equity sampled on a fixed cadence independent of trades; halt on non-positive portfolio** (R9).
19. **Per-run time/memory limits and cancellation** (R10) — 12–14 fail fast, not hang.
20. **Fill-forward opt-in per subscription** (R11).
21. **Lowest-fidelity-wins + refuse cross-fidelity comparison** (LABEL-2/3).
22. **Optimistic-vs-worst-case default** — intake wanted worst-case as honest default; spine taints all fills optimistic until GAP-0048. Substitution is defensible; **undisclosed**.
23. **Partial fills as a v1 retail-FX *capability*** — deferred as GAP-0048 content, never named as a seam the taxonomy must cover.
24. **Fee double-call** (query before fill for admission, at fill for charge) (FEE-3).
25. **Scheduled financing as its own port vs folded into "costs"** — B-6 three ports; intake's `IMarginInterestRateModel` was a fourth scheduled applicator. Content is GAP-0048; the seam is quietly three, not four.
26. **`logic-smoke` claim class** (synthetic R3).
27. **Scenario 0 = untouched original** in MC (synthetic R5, R-MC-2).
28. **Synthetic generator bound to the FX market-hours grid** (weekend gap).
29. **Process menu named** (block-bootstrap default, gaussian-*, gbm infra-only) not just two classes.
30. **Curated V1 metric set** (core vs extended vs rejected) and **analytics chart set** (equity/drawdown/monthly/distribution) as distinct from price-chart series.
31. **Benchmark optional + labeled; omit, never fake** (R-RPT-15).
32. **Markdown as an agent-consumable render target** (R-RPT-21).
33. **Suppression/veto accounting and "no composite score / measurement never acts"** restated at B-10 (inherited, quiet).
34. **Annualization basis and rf model as part of metric identity** (R-RPT-5/23).
35. **Machine-observable import progress** (percent / ETA / date-reached).
36. **License tag + typed refusal at ingest** (the enforcement half of the licensing gate).
37. **Symbol-identity map files** (Lean; intake left FX-deferral open).
38. **One position per (venue, instrument); one settlement asset per run** (routes R4/R5) as typed refusals.
39. **`on_peer_*` multi-strategy coordination** (routes R8).
40. **Pre-flight Cartesian size** before committing a sweep (R9).
41. **Sweep: one combo's refusal does not abort the batch** (R12) — implied, not said.
42. **Enqueue-on-full backpressure + typed refusal over the concurrency ceiling** (C-6).
43. **Memory as the real limiter; phase-aware oversubscribe** (C-7).
44. **R-7 lineage-sibling semantics** for parallel minting (mechanics A2).
45. **Snapshot freshness contract**: re-sync when hub reachable, honest staleness when not, `stale-evidence` on superseded refs, `registry_as_of` on every label (mechanics A1; direction v2 wrote this; spine drew the hub).
46. **CLI command tree** as a named surface (`init`, `book`, `bms`, `ledger`, `self`, `report`) — capability map is close, not the tree.
47. **Jesse ML pipeline** — marketed table-adjacent; intake marked optional. Correctly not a B-id; not Deferred either. Fine if v1-silent.
48. **Naming:** direction DC-5 proposed command `qmx`; spine uses `qmb`. That is a sitting landing, not an intake miss.

---

## Part D — Findings

### Finding 1 — MATERIAL — Look-ahead is a Prevents slogan; the bar-visibility rule did not land

**Intake:** loop R6 — aggregated bars emit only on completed boundaries; **a bar MUST NOT be visible to strategy code before its close time under the clock**. Routes R2 — higher TFs folded from a finest-native spine and emitted only on aligned boundaries. Routes R7 — forming-bar completeness must be inspectable so agents cannot act on a forming bar. Website claim: "No look-ahead bias."

**What the spine says:** B-2 Prevents "look-ahead via time arithmetic"; B-12 Prevents "look-ahead via ad-hoc cross-stream access" and requires a declared stream set. Neither says a forming bar is invisible, refused, or flagged. B-2 adopted LEAN event-slice (correct INDEX axis) and **silently dropped** Jesse's 1m-spine / completed-boundary emission rule that was the other half of the loop+routes pair.

**How it weakens:** an agent can read a higher-TF bar whose period has not closed under the frontier clock, or a forming bar synthesized from the tail of a base stream, and the spine has no typed refusal. GAP-0016/0017 is the *registration gate* (Deferred — correct). This is the *mechanical* look-ahead rule, which B-2 claimed to prevent.

**Fix:** one clause on B-2 or B-12: higher-TF / aggregated bars are visible to strategy code only at period close under the injected clock; a forming bar, if exposed at all, is a distinct typed object whose incompleteness is inspectable; acting on it is a typed refusal. Disclose that the 1m-spine was substituted by event-slice, not forgotten.

---

### Finding 2 — MATERIAL — The optimization differentiator landed as TPE only; sensitivity and the Lean findings layer did not

**Intake INDEX:** "QMB's differentiator: a genuinely adaptive sampler (TPE-class) **+ Lean-style post-hoc parameter-sensitivity for overfit detection**." OPT-22: per-parameter slices, objective distribution, clustering of good regions; isolated-spike winners flagged. Independent take-from-Lean: R-MC-3 structured findings `{verdict, metric, statistic, threshold, plain-language issue, suggested action}`. OPT-6 hard constraints are how an agent says "Drawdown <= 0.25".

**What the spine says:** B-8 TPE-class, every trial a run, train/test via split manifests, objectives = B-10 named metrics. B-14 procedures versioned as contracts. B-12 aggregation is a read-time view. **No sensitivity, no clustering, no spike flag, no constraints, no findings objects.**

**How it weakens:** the ledger will contain every trial (good) and will not contain the analysis both donors proved is the anti-overfit deliverable. Website "overfitting warnings" and Jesse's dedicated Overfitting docs page have no QMB home. GAP-0049 is thresholds and attempt-counting, not this analysis.

**Fix:** extend B-8 (or B-14) with: (a) a versioned post-hoc sensitivity/clustering view over a Study's ledger lines, (b) hard constraints as config, violating trials ledgered but ineligible to win, (c) robustness toolkit emits structured findings as data, not only scalars. Grid as an optional sampler adapter is the cheap reproducibility companion and should ride the same amendment.

---

### Finding 3 — MEDIUM — Snapshot freshness is a picture, not a contract; license-tag enforcement is posture only

**Intake / challenge:** Mechanics A1 BROKEN and Override A1 BROKEN — auto-update is false on the offline topology the architecture is built for. Direction v2 wrote the fix: snapshot + dumb hub; auto-resync when reachable; honest staleness when not; `registry_as_of` + snapshot fp on every label; stale-evidence on superseded refs. Data-mgmt R1: every ingested window records provenance **and a license tag**; typed refusal when the source lacks the right — the old corpus failed this gate.

**What the spine says:** a mermaid hub of "registry + ledger files"; B-13 `registry-state as-of`; B-11 "ships and redistributes no market data" / fetch at runtime. No re-sync rule, no stale-evidence, no license-tag, no ingest refusal.

**How it weakens:** an agent on a Wednesday sandbox still runs `scalping@2` after `@3` exists, and the spine cannot refuse it. A future data adapter can ingest a corpus the licensing gate already failed, because the *posture* is a sentence and the *gate* is not a B-rule. CT-10 may carry license at QMF; QMB's `qmb data download` is the door that must refuse.

**Fix:** (a) a B-3/B-13 clause: hub is files-only; snapshot fp + as-of on every label; stale-evidence when a resolved ref is superseded in a fresher snapshot; unreachable hub is honest staleness, not a hang. (b) B-11: ingest records a license tag; missing/denied right is a typed refusal, never a silent write.

---

### Finding 4 — MEDIUM — Mixed-fidelity comparison is unruled

**Intake LABEL-2/3:** a run's ledger result carries the **lowest** fidelity of any fill in it; labels are machine-comparable so the CLI refuses to compare Books run at different fidelities without an explicit override.

**What the spine says:** B-6 every adapter has a declared fidelity identity in the result label; until GAP-0048 everything is `optimistic`. The comparison rule and the min-across-fills rule are absent. GAP-0048 is the *taxonomy values*, not the comparison algebra.

**How it weakens:** once GAP-0048 mints more than one fidelity, nothing stops a mixed-fidelity run from being compared to a quote-real run, which is exactly the flattery LABEL-2 exists to prevent. The algebra is load-bearing for v1 the moment any second fidelity exists, including the optimistic taint itself (an all-optimistic run compared to a later honest run).

**Fix:** one B-6 sentence: a run's fidelity is the minimum of its fills; comparing result labels whose fidelity identities differ is a typed refusal without an explicit override.

---

### Finding 5 — MEDIUM — 12–14 concurrent runs have no fail-fast envelope

**Intake loop R10 + concurrency C-6/C-7:** per-step and total time/memory limits, cancellation, typed terminal states, enqueue-on-full, refuse over the ceiling, size the cap by `min(cpu, ram)`.

**What the spine says:** B-5 process-per-run, bounded by cores, 12–14 as an unvalidated AD-13 reference. No cancel, no limit, no enqueue, no memory governor.

**How it weakens:** the motivating load is named; the thing that keeps 14 runs from hanging a sandbox is not. Lean Isolator + Jesse Termination exist because this is how concurrent backtests die in production.

**Fix:** B-5: orchestrator enforces a host-derived cap with enqueue-on-full; over-ceiling is a typed refusal; a run that exceeds its declared time/memory budget ledgers `aborted`; memory projected peak may shrink the cap. Numbers stay AD-13 (no invented budget).

---

### Finding 6 — MEDIUM — Research INDEX half (DataFrame ergonomics) dropped

**Intake INDEX:** "Take Jesse's function architecture with **Lean’s DataFrame ergonomics**." R3: history returns a typed-array fast path **and** a pandas-DataFrame view; indicator-over-history; `portfolio_statistics` over an arbitrary equity curve.

**What the spine says:** B-9 pure functions, portable, seal-scoped. No frame, no indicator-over-history, no score-any-curve.

**How it weakens:** the portable library lands; the *interactive/agent inspection* shape does not. Open question in the intake (DataFrame vs `.to_frame()` to keep pandas out of core) is fine to leave open — **the ergonomics obligation itself** is not. A one-line B-9 "interactive returns are a frame view over the typed artifact; pandas is a projection, not a core dependency" would hold the finding without pinning the open question.

---

### Finding 7 — LOW — Secrets/infra can enter the fingerprint

**Intake R-CLI-6/10:** credentials, endpoints, concurrency limits live in a separate global layer and **MUST NOT enter the resolved run-config's fingerprint region**.

**What the spine says:** B-3 fingerprint of the resolved artifact is the ledger key. No semantic-vs-excluded classification.

**How it weakens:** rotating a Dukascopy credential or changing a sandbox core-cap retints every subsequent result, breaking "identical semantics → identical fingerprint" and poisoning cache/dedupe. Low because AD-26 already forbids secrets *in* repos/logs/evidence — this is the adjacent fingerprint-boundary rule.

**Fix:** B-3: fingerprint covers Book/BMS fragments, bot, data window, run variables, QMB+QMF versions; excludes secrets, infra, timestamps, worker names.

---

### Finding 8 — LOW — Book and BMS fragments are co-equal; intake ordered them

**Intake R-CLI-3:** flags > bot > **BMS > Book** > defaults.

**What the spine says:** flags > run spec > **Book fragment + BMS fragment** > workspace defaults.

**How it weakens:** a Book config fragment and a BMS config fragment that set the same key have no winner. "Test = can a bot fit the Book" also lives here (fit is a *combination* refusal). Low because B-3 still compiles one artifact; the conflict is a compiler rule, not an architecture fork.

**Fix:** state BMS-over-Book or Book-over-BMS (intake was BMS-over-Book) and that an unfittable combination is a typed refusal at compile, not at run.

---

### Finding 9 — LOW — Several named primitives dropped without a Deferred row

Not material alone; together they are the "B-id compression tax":

- Routes **R4/R5** uniqueness (one position per venue+instrument) and one settlement asset — typed refusals, not crashes.
- Routes **R8** `on_peer_*` — the multi-strategy coordination primitive the intake chose from Jesse.
- LABEL-2/3 covered in Finding 4.
- OPT-1 categorical; OPT-13 Grid; OPT-10 locked validation window (Finding 2 family).
- Synthetic `logic-smoke`; scenario-0 = original.
- R-RPT-15 benchmark optional.
- Machine-observable `data` progress.
- R-CLI-17 outdated-check.

None of these invert a ruling. Each is a named intake constraint with no B-id and no Deferred home, so a factory story can drop them as "unspecified."

---

### Finding 10 — LOW — Undisclosed substitutions that read as landed

Two substitutions are sound and **invisible**:

1. **FILL-4 default.** Intake: worst-case honest default, Jesse-exact as a labeled option. Spine: all fills `optimistic` until GAP-0048. More conservative; does not record the override.
2. **1m-spine → event-slice** for higher-TF generation (Finding 1). Correct INDEX axis; the routes dossier's deterministic folding rule was not marked superseded.

Same failure mode as the risk-reconcile "mechanism substitution, undisclosed." One clause each.

---

## Part E — Scoreboard

### INDEX key findings (13)

| Spec | Key finding | Verdict |
|---|---|---|
| backtest-loop | LEAN slice+clock; Jesse split-candle | **LANDED IN FULL** (B-2, B-6) |
| fill-fees | three ports; forex content original; GAP-0048 | **LANDED IN FULL** (B-6) + **DEFERRED EXPLICITLY** (content) |
| optimization | TPE-class **+** parameter-sensitivity | **LANDED WEAKENED** (B-8 TPE; sensitivity DID NOT LAND) |
| synthetic-data | store-level taint; claim class from provenance | **LANDED IN FULL** (B-7) |
| reports | one artifact; series as data; render downstream | **LANDED IN FULL** (B-10) |
| research-jupyter | same library, portable; DataFrame ergonomics | **LANDED WEAKENED** (B-9; DataFrame DID NOT LAND) |
| data-mgmt | fetch-at-runtime; Lean organization via QMF | **LANDED IN FULL** (B-11) |
| cli-config | CLI is a config compiler | **LANDED IN FULL** (B-3) |
| multi-routes | declarative set + Cartesian isolated runs | **LANDED WEAKENED** (B-12; bar-visibility/uniqueness/peers dropped) |
| mc-significance | signal-only pre-build gate | **LANDED IN FULL** (B-14) |
| charts-ui | Lean separation + SeriesSampler | **LANDED IN FULL** (B-10) |
| concurrency | process-per-run; logs then ledger | **LANDED IN FULL** (B-4, B-5) |
| website-visuals | provenance + validation ladder | **LANDED IN FULL** (B-10, B-14); MCP **DEFERRED EXPLICITLY** |

**13 key findings:** 9 full, 3 weakened, 0 silent, plus fill *content* and MCP correctly deferred.

### Challenge BROKEN (unique)

| Item | Verdict |
|---|---|
| Mechanics/Override A1 snapshot-vs-live | **LANDED WEAKENED** |
| Mechanics A2 write-back / R-7 | **LANDED WEAKENED** |
| Mechanics A6 synthetic taint | **LANDED IN FULL** |
| Economics 2b Jesse-lesson misattribution | **LANDED IN FULL** |

### Challenge WOUNDED (load-bearing)

14 of 16 landed in full (B-1 adaptation logic, UI consumer, MCP sibling not stacked, optimistic taint, complete label, pure functions for real, TPE, no codegen, own spine, DEC-0084 hub-as-files, L20+fetch posture, seal scoping, AD-44 unbundled, framework/app split, gestalt-as-new-spine). 1 deferred explicitly (MCP lifecycle / campaign pre-reg). 0 inversions.

### Deferred correctly (not misses)

GAP-0048 fidelity taxonomy + forex fill/slippage/swap content + simulated-time typing; GAP-0049/0016/0017 thresholds, look-ahead *gate*, attempt counting; pass batteries (WF windows, OOS counts, PBO, CSCV); MCP door details; live wiring; UI rendering; QML GAP-0047; cloud-burst; prop-firm Books socketed.

### Load-bearing DID NOT LAND (neither B-id nor Deferred)

1. Parameter-sensitivity / clustering (OPT-22) — INDEX differentiator
2. Completed-bar / forming-bar visibility (loop R6, routes R2/R7)
3. Optimize hard constraints (OPT-6) and optional Grid (OPT-13)
4. R-MC-3 structured findings
5. LABEL-2/3 lowest-fidelity-wins + comparison refusal
6. Snapshot freshness / stale-evidence contract (challenge BROKEN A1 remainder)
7. License-tag + ingest refusal (data R1 remainder)
8. Secrets excluded from fingerprint (R-CLI-6)
9. Per-run cancel / time / memory envelope (R10, C-6/C-7 remainder)
10. DataFrame ergonomics (research INDEX half)
11. Routes uniqueness + settlement refusals (R4/R5)
12. `on_peer_*` callbacks (R8)
13. Locked validation window (OPT-10)
14. Benchmark optional (R-RPT-15)
15. Import progress (data R1)
16. CLI outdated-check (R-CLI-17)

Items 1–2 are Finding 1–2 (material). Items 3–10 feed Findings 2–7. Items 11–16 are Finding 9.

---

## Part F — Items to put to the operator

None of these re-open QMF law or invent product direction. They are intake that the B-id pass dropped, for a yes/no on whether the spine should name them before exit.

1. **Finding 1 (bar visibility).** "Intake said a higher-TF bar is invisible until it closes under the clock. The spine prevents look-ahead in two other ways and never says this. Confirm the completed-bar rule belongs on B-2/B-12."
2. **Finding 2 (sensitivity + constraints).** "The optimization dossier's differentiator was TPE *and* Lean's post-hoc sensitivity/clustering. Only TPE landed. Do you want the analysis as a B-8/B-14 obligation, or is 'every trial is a ledger line' enough raw material for later?"
3. **Finding 3 (freshness).** "The hub is drawn. Direction v2's stale-evidence / as-of / honest-staleness sentences are not a B-rule. Confirm they should be, so an offline sandbox cannot silently accumulate against a superseded Book."

---

## Companion coverage

Walked: `specs/INDEX.md` and all 13 files it lists (`spec-backtest-loop`, `spec-fill-fees`, `spec-optimization`, `spec-synthetic-data`, `spec-reports`, `spec-research-jupyter`, `spec-data-mgmt`, `spec-cli-config`, `spec-concurrency`, `spec-multi-routes`, `spec-mc-significance`, `spec-charts-ui`, `website-visuals.md`); `challenge-mechanics.md`, `challenge-economics.md`, `challenge-override.md`; `backtesting-direction-position.md` v2 as the demotion/context document. Open questions inside the dossiers were treated as open, not as misses. Screenshots under `specs/screens/` were not re-interpreted beyond `website-visuals.md`'s transcript.
