# PARTS BIN — what the trading node can take off the shelf at `integration@ef9bb25`

Synthesis input for the trading-node spine. Source of truth: the five code dossiers in this
folder, the DevOps dossier, the QA section of `dig-prd-docwork-tracker-qa.md`, and — where a
dossier was missing or a claim was load-bearing and doubtful — my own read-only reading of the
worktree `C:/Users/Mubarak/Desktop/QMX-worktrees/node-inventory` (detached at
`integration@ef9bb253fc87ec3a66d5c6a78f3cb95bb45c760c`). Nothing was modified.

## Provenance caveats (read these before trusting a row)

1. **`code-qmf-risk.md` was never written to disk.** The dossier the sitting commissioned for
   `qmf-risk` (the node's whole risk pipeline, protections, and paper mode — 16,905 src LOC,
   613 test functions, 4 example scripts, a 134-line `FAILURES.md`) does not exist in
   `inputs/`. Every row in **§C Risk pipeline & protections** and **§D Paper mode** below is
   sourced from my own primary reading of `packages/qmf-risk/src/qmf/risk/` in the worktree,
   not from a dossier. Those rows carry evidence confidence `high` where I read the symbol and
   its docstring, `med` where I read only the package's own spine map
   (`packages/qmf-risk/src/qmf/risk/__init__.py:1-270`).
2. **One dossier claim is wrong as a platform statement and I corrected it.**
   `code-qmb-host.md` reports `resolve_execution_target` / paper routing as
   `does-not-exist` and calls "the entire paper-vs-live routing layer node-new". That is true
   *of QMB* and false *of the platform*: the function exists at
   `packages/qmf-risk/src/qmf/risk/paper.py:436`, with the `ExecutionTarget` /
   `ExecutionResolution` types at `paper.py:326` and the one-active-target-per-binding
   `PaperTargetLog` at `paper.py:962`. It was also the subject of a critical QA finding
   (QMX-F002) fixed and PROVEN in FC-01 (`FIX-LEDGER.md:14`). Budgeting paper routing as
   greenfield would be a material over-estimate of node work.
3. Two per-epic QA numbers in circulation are from different snapshots. `proof_map.md` (branch
   coverage qml 65.96% / qmb 66.46%, ambient-scan FAIL) is the **pre-fix** trace against
   `integration@2c8d495`. `FINAL-REPORT.md:48-74` is the **post-fix** state at `ef9bb25`:
   `poe check` fully green, 3,932 passed, 86.86% coverage, all four tier-1 scanners clean,
   Skylos + QA Battery green. Do not quote the pre-fix numbers as current.

Status vocabulary, used exactly:
- **exists-as-is** — the contract and its logic are present and correct to call; the node's work
  is wiring, injecting values, and choosing.
- **exists-needs-live-adapter** — the shape, the law, or the seam is present, but the live half
  (transport, scheduler, concrete implementation, or a caller-supplied observation) is not.
- **does-not-exist** — no code. The node writes it.

---

# 1. THE PARTS-BIN TABLE

## §A — Composition root & boot

| # | Capability | Exists where (path:line) | Status | Node work needed (one line) | Ev. |
|---|---|---|---|---|---|
| A1 | Composition-root pattern: compose → fingerprint → freeze | `qmb/src/qmb/config/compiler.py:474` (`compile_run_config`), `:731` (`_finish`) | exists-needs-live-adapter | Build a live variant that reads the wall clock at its own edge and binds live adapters instead of replay ones | high |
| A2 | `world=live` binding mint | absent — `qmb/src/qmb/config/replay.py:119` "Always `replay` — QMB never mints a live binding" | does-not-exist | Mint exactly one AD-29/CT-28 binding with `world=live` at the node root | high |
| A3 | Book binding record + append-only binding log (epoch uniqueness, one BMS at a time) | `packages/qmf-risk/src/qmf/risk/binding.py:1049` (`BookBindingRecord`), `:1270` (`BookBindingLog`) | exists-as-is | Construct the `(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)` tuple and append | high |
| A4 | Bind-time capability check against the CT-18 projection | `packages/qmf-risk/src/qmf/risk/binding.py:892` (`bind_time_capability_check`), `:657` (`VenueBindingProfile`) | exists-as-is | Build the `VenueBindingProfile` from the venue declaration at the root and call it before any live bind | high |
| A5 | Real wall-clock adapter satisfying the `Clock` seam | seam only: `packages/qmf-core/src/qmf/core/chrono.py:711` (`Clock` Protocol); replay impl `:739` (`DataDrivenClock`). No concrete wall clock ships anywhere | exists-needs-live-adapter | Write the ~20-line real-clock adapter at the root under `# ambient-scan: allow`, mirroring `qmb/src/qmb/doors/cli/__init__.py:263` | high |
| A6 | Concrete `SecretStore` (`systemd-creds`-class) | seam only: `packages/qmf-core/src/qmf/core/secret.py:291`; only impl is `InMemorySecretStore` in `packages/qmf-core/examples/secret_usage.py:50` | exists-needs-live-adapter | Implement read + `atomic_replace` over the VPS protected store; key custody is this sitting's (DEC-0136) | high |
| A7 | Injected sink wiring (`ObservationSink`/`JournalSink`/`RecordSink`) | `packages/qmf-core/src/qmf/core/sinks.py:104`, `:121`, `:136`; consumed at `packages/qmf-venue/src/qmf/venue/connection.py:391-405` | exists-needs-live-adapter | Build durable concrete sinks over the qmf-data store and wire all four at the root | high |
| A8 | Startup / recovery ordering (boot-epoch mint, standing-intent re-evaluation on reconnect, sequence reset) | `packages/qmf-core/src/qmf/core/chrono.py:807` (`WriterId`), `:902` (`WriterSequencer`); reconnect duty described at `packages/qmf-risk/src/qmf/risk/control_action.py:1239` | exists-needs-live-adapter | Write the boot sequence itself: mint boot-epoch, replay gaps, re-evaluate standing intents, then admit commands | high |
| A9 | Service entry point / console script for the node | absent — the only `[project.scripts]` in the workspace is `qmb` (`qmb/pyproject.toml:20-21`) | does-not-exist | New package + console script + long-lived main | high |

## §B — Venue session & order path

| # | Capability | Exists where (path:line) | Status | Node work needed | Ev. |
|---|---|---|---|---|---|
| B1 | Live cTrader transport (socket / TLS / framing / length-prefix / message loop) | **absent** — grep for `twisted\|websocket\|ssl\|socket\|asyncio\|reactor\|tcp\|tls\|connect(\|sendall\|recv\|aiohttp\|requests\|urllib` over `packages/qmf-venue/src/` returns only string message names, a comment rejecting the Twisted reactor (`proto.py:10`), and a pure decision method | does-not-exist | Build the entire wire client on stdlib (no platform-imposing dep — `DEPENDENCIES.md:11-13`, `:47`) | high |
| B2 | Outbound ProtoOA request encoding (e.g. `place_order` → `ProtoOANewOrderReq`) | absent — `packages/qmf-venue/src/qmf/venue/proto.py:276` (`CompiledProto.decode`) is decode-only | does-not-exist | Write the request builders for the five commands | high |
| B3 | In-house proto compilation from a descriptor set + pin governance | `packages/qmf-venue/src/qmf/venue/proto.py:329` (`compile_descriptor_set`), `:412` (`assess_tag_change`), `:177` (`ProtoArtifact`) | exists-needs-live-adapter | Supply the compiled Spotware `openapi-proto-messages` descriptor bytes (no `.proto` or descriptor set ships in the package) | high |
| B4 | `ProbeTransport` implementation (credential-free demo probe) | seam only: `packages/qmf-venue/src/qmf/venue/probe.py:224` — the **only** Protocol in `qmf-venue`; no concrete implementation ships | exists-needs-live-adapter | Implement `ProbeTransport` against the real cTrader demo host at the pinned proto tag | high |
| B5 | CT-18 verify-or-refuse first-connection probe (five measured checks) | `packages/qmf-venue/src/qmf/venue/probe.py:359` (`CapabilityProbe`), `:470` (`.run`), checks at `:538,:583,:625,:677,:722` | exists-as-is | Run it once at first connection; it never places an order (`probe.py:366-368`) | high |
| B6 | CT-18 capability declaration (23 field markings, adapter-version-scoped, fingerprinted) | `packages/qmf-venue/src/qmf/venue/capabilities.py:587`, roster `:130-166`, `fingerprint()` `:769`; adapter supplies **4 of 23** at `packages/qmf-venue/src/qmf/venue/ctrader.py:1048-1084` | exists-needs-live-adapter | Author the other 19 field markings and the pinned `ErrorMap` rows as node data | high |
| B7 | Error map with fail-closed default (unmapped ⇒ transient-venue-failure / UNKNOWN + alarm) | `packages/qmf-venue/src/qmf/venue/capabilities.py:451-499` (`ErrorMap.resolve`), row validation `:288` | exists-as-is | Inject the pinned rows; only a declared row can yield `rejected-by-venue` | high |
| B8 | The five commands typed on core nouns with required close scope | `packages/qmf-venue/src/qmf/venue/commands.py:126-140` (`CommandKind`), factories `:701,:732,:764,:794,:875`, `CloseScope` `:822` | exists-as-is | Build Commands and pick a declared close scope; partial/fractional close refuses | high |
| B9 | Four-outcome model + resolver (accepted \| rejected \| denied-locally \| UNKNOWN) | `packages/qmf-venue/src/qmf/venue/commands.py:183-222`, producers `:1070,:1085,:1115,:1153` | exists-as-is | Decide which producer to call from a venue response the node already holds | high |
| B10 | Submit / dispatch path that transmits a Command | absent — grep finds no submit/dispatch/send in `packages/qmf-venue/src/` | does-not-exist | Write it, on top of B1+B2 | high |
| B11 | `clientMsgId` wire generate + match | binding discipline exists (`packages/qmf-venue/src/qmf/venue/commands.py:1291` `CommandIdBinding`, `:1317` `bind_before_submission`); the wire-level generate/match does not — `correlation_id` is stored verbatim as provenance only (`events.py:505`) | exists-needs-live-adapter | Generate a clientMsgId on each outbound request and match the inbound response | high |
| B12 | Per-writer gapless command sequencer / `OrderingKey` | `packages/qmf-venue/src/qmf/venue/connection.py:511` (`next_command_key`), `:417` (`WriterSequencer`), writer identity `:162` | exists-needs-live-adapter | "the node owns the sequencer and QMF carries the field" (`commands.py:691-693`) — mint one writer per `(VenueId, account)` | high |
| B13 | Rate pacing (50/s non-historical, 5/s historical, 1-week historical span cap) | `packages/qmf-venue/src/qmf/venue/ctrader.py:507-590` (`RatePacer`), ceilings `:131-132`, span cap `:591`, `:139` | exists-as-is | One pacer per connection (`ctrader.py:1043`); supply monotonic stamps and the below-ceiling cadence (node value, do-not-default) | high |
| B14 | Session-duty scheduler (heartbeat / token-refresh / reconnect / gap-replay / verification-monitor) | duties **declared** at `packages/qmf-venue/src/qmf/venue/ctrader.py:742-784`; only heartbeat has a venue-bound cadence (≤10s, `:757-775`). **No runner.** "The adapter *defines* the work; the application *runs* it" (`ctrader.py:745`) | exists-needs-live-adapter | Build the scheduler that fires all five duties | high |
| B15 | Session recovery on disconnect (every in-flight → UNKNOWN, never resubmits) | `packages/qmf-venue/src/qmf/venue/ctrader.py:802-851` (`SessionRecovery.on_disconnect`, `resubmits_command = False` `:808-810`) | exists-as-is | Call it from the reconnect path; it is a pure decision function, not a socket handler | high |
| B16 | UNKNOWN command-stream block + `resolve_unknown` | `packages/qmf-venue/src/qmf/venue/blocking.py:464` (`UnknownGate`), `:567`, `:625`, `:767` (`resolve_unknown`), resolutions `:275-286` | exists-as-is | The node **originates** the typed resolution; the block never clears on a reconciliation verdict alone (`blocking.py:772-778`) | high |
| B17 | Standing protection intents (risk-reducing acts held + journaled before dispatch, re-decided on reconciled) | `packages/qmf-venue/src/qmf/venue/blocking.py:372`, `:698`, `:829`; shared-throttle priority `:164` | exists-as-is | Drive the re-decision on reconnect | high |
| B18 | Record-before-interpret inbound events + multi-room atomic-or-recovery | `packages/qmf-venue/src/qmf/venue/events.py:476` (`InboundVenueEvent`), `:1157`/`:1172`/`:1241` (`EventRecorder`), `:999` (`MultiRoomWrite`), `:1072` (`PartialWriteRecovery`) | exists-as-is | Inject the three sink rooms; a partial write blocks the command pipe and is journaled on recovery | high |
| B19 | Order-state fold, UNKNOWN-is-a-state, legal-prior table, out-of-sequence detection | `packages/qmf-venue/src/qmf/venue/events.py:144-165`, `:878` (`fold_order_state`), `:238-280`, `:826` | exists-as-is | Nothing — call it. Terminal state comes only from fills + venue lifecycle events | high |
| B20 | Reconciliation verdict vocabulary + lookback gating + subject-terminal resolution | `packages/qmf-venue/src/qmf/venue/events.py:181-194`, `:1304` (`ReconciliationReadback`), `:1391` (`.verdict`), `:1452` | exists-needs-live-adapter | `.verdict()` takes caller-supplied expected/observed — the node must **read the venue back** and fold orders/fills/positions/balance into an observed state; `declared_lookback` is mandatory, never defaulted (`:1307-1308`) | high |
| B21 | CT-21 secret lifecycle: single in-memory holder, open/close/rotate store-before-discard | `packages/qmf-venue/src/qmf/venue/connection.py:361` (`ConnectionManager`), `:527`, `:570`, `:588` (`rotate_secret`), block causes `:312-322` | exists-as-is | Inject the store + three sinks; rotation-store failure blocks the command pipe until re-provision | high |
| B22 | Two simultaneous connections (demo + live are separate hosts) | requirement declared: `packages/qmf-venue/src/qmf/venue/ctrader.py:645-706` (`SessionTopology`, `required_connection_count = 2`). **No code opens or holds a connection** | exists-needs-live-adapter | Open and hold both sessions concurrently | high |
| B23 | Price decode, 1/100000 exact scale-5 integer | `packages/qmf-venue/src/qmf/venue/ctrader.py:339-362`, exponent `:127` | exists-as-is | Call with wire value + Instrument | high |
| B24 | Money decode via per-account `moneyDigits` (absent exponent refuses, never defaults to 2) | `packages/qmf-venue/src/qmf/venue/ctrader.py:438-486`, nine money-bearing messages `:144-159` | exists-as-is | Supply the per-account exponent from the probe/profile plus the declared rounding mode | high |
| B25 | Execution-price raw-double crossing at instrument digits | `packages/qmf-venue/src/qmf/venue/ctrader.py:365-437`, crossing at `:423` | exists-as-is | Choose the identity-bearing rounding mode (see red flag R7) | high |
| B26 | Volume decode (cTrader cents = 1/100 lot) ↔ `Quantity` | **absent** — no volume/cents/lot decoder anywhere in `packages/qmf-venue/src/` | does-not-exist | Write the third scale system; only price and money are implemented | high |
| B27 | Equity derivation (balance + unrealized PnL) | **absent** — `EQUITY_NATIVENESS` is a capability *field name only* (`capabilities.py:151`); `ProtoOAGetPositionUnrealizedPnLRes` is a *message name only* (`ctrader.py:154`) | does-not-exist | Derive equity from decoded money messages; it feeds the kill line and sizing | high |
| B28 | Position / balance event ingestion as first-class journaled kinds | **absent** — `ObservationKind` has six members, the order-lifecycle five plus out-of-sequence (`events.py:127-142`); positions/balance appear only as money-decode message names and reconciliation evidence keys (`events.py:1335,:1367`) | does-not-exist | Add position- and balance-event ingestion (this is the CT-20 "seven journaled types" gap) | high |
| B29 | Market depth / Level-2 / order book | **absent** — grep for depth/L2/orderbook/ladder/spread returns nothing | does-not-exist | Greenfield if the node needs it; likely out of V1 scope | high |

## §C — Risk pipeline & protections *(sourced from the worktree; no dossier)*

| # | Capability | Exists where (path:line) | Status | Node work needed | Ev. |
|---|---|---|---|---|---|
| C1 | CT-23 risk-evaluation door: two typed intent families, declared evidence slots, inbound `requested_r` refused | `packages/qmf-risk/src/qmf/risk/door.py:560` (`EntryIntent`), `:770` (`ExitIntent`), `:866` (`RiskEvaluationRequest`), `:1213` (`admit_entry_intent`) | exists-as-is | Call the door per bot intent; the bot may not size | high |
| C2 | `ExitLogicModule` — per-family full-loss-price derivation at the door | seam only: `packages/qmf-risk/src/qmf/risk/door.py:469`; the per-family arithmetic is "application/node territory (DEC-0142)" (`door.py:475-478`) | exists-needs-live-adapter | Implement one module per exit family; no price ⇒ no admission (`refuse_no_full_loss_price`, `door.py:488`) | high |
| C3 | R's three typed faces, full-loss law, no-scale-in guard, Money↔R crossing | `packages/qmf-risk/src/qmf/risk/r_faces.py:111` (`RFaces`), `:271` (`admit_entry_r_faces`), `:314` (`check_no_scale_in`) | exists-as-is | Supply the venue value-factor and the seat's open-position state | high |
| C4 | Units-only `money_rules` shape, B-split, seat R ceiling, one-floor law | `packages/qmf-risk/src/qmf/risk/sizing.py:95` (`validate_money_rules`) and siblings | exists-as-is | Author the Book's money-rules section | high |
| C5 | Sizing-ladder **runtime evaluation** against live Book state | **absent by design** — `ProducerContract` Protocol at `packages/qmf-risk/src/qmf/risk/admission.py:143`; "the sizing ladder's runtime evaluation is the node's (DEC-0142)" `:149-150`, `:757-759` | does-not-exist | Implement the cited producers that read live book capital and return governed arithmetic | high |
| C6 | Four risk-monotonic exit guards (stop not widened, target in envelope, no reopen, no size increase) | `packages/qmf-risk/src/qmf/risk/door.py` — `check_stop_not_widened`, `check_target_within_envelope`, `check_no_reopen`, `check_no_size_increase` (exported `__init__.py`) | exists-as-is | Nothing — call them on every exit intent | med |
| C7 | Three-layer admission (linters → shakedown → page) + human operator signature | `packages/qmf-risk/src/qmf/risk/admission.py:316`, `:441`, `:545`, `:618` (`OperatorSignature`), `:662` (`sign_admission`), `:697` (`admit`) | exists-as-is | Wire the layers; Layer-2 shakedown is the demo/paper soak the node runs (see QA debt Q6) | high |
| C8 | Admission bar: per-requirement verdicts, no composite score, blank-blocks-live, no-paper-role-gates-live | `packages/qmf-risk/src/qmf/risk/admission_bar.py` — `AdmissionBar`, `evaluate_bar`, `check_live_binding_admissible`, `check_no_paper_role_gates_live` | exists-as-is | Author the requirement rows and thresholds; blanks block live money | high |
| C9 | CT-30 control actions (`suspend_new\|drain\|flatten\|resume`) + exit-preservation invariant | `packages/qmf-risk/src/qmf/risk/control_action.py` — `mint_control_action`, `check_exit_preservation`, `reject_blanket_command_pipe_block`, `resolve_subject_scope` | exists-as-is | Issue actions from operator doors and sensors; the exit-preservation guard now has a caller (FC-01) | high |
| C10 | Kill switch (global, sensor-fed, human de-escalation) and kill line (per-Book capital floor, auto-flatten) named apart | `packages/qmf-risk/src/qmf/risk/control_action.py:929` (`KillSwitch`), `:1014` (`KillLine`), `:1083`, `:1115` | exists-as-is | Feed the sensors; supply the capital floor and the equity reading (see B27) | high |
| C11 | KSA severity → effect matrix (which level fires suspend-new vs drain vs close-all) | **absent** — "which additional effect a severity carries is **node severity policy** — QMF carries the contract, never the matrix" (`control_action.py:934-935`); also `check_flatten_authority` gates flatten on it (`:420-431`) | does-not-exist | Author the matrix; it is node authority under do-not-default | high |
| C12 | Same-tick rank arbitration at exactly one point per command stream | `packages/qmf-risk/src/qmf/risk/control_action.py:1494` (`arbitrate_same_tick`); rank table + uniqueness law `control_rank.py:22` | exists-as-is | Declare the BMS rank table | high |
| C13 | Control-action stream, journal-before-dispatch, standing-intent fold + re-evaluation | `packages/qmf-risk/src/qmf/risk/control_action.py:1150` (`journal_before_dispatch`), `:1262` (`ControlActionStream`), `:1306` (`fold_standing_intents`), `:1230` (`reevaluate_standing_intent`) | exists-as-is | Enforce the happens-before at runtime (see QA debt Q8 — it is proven only by passing a failure in) | high |
| C14 | CT-31 protection windows (news \| daily dead zone \| session handover buffer), entries-only, fail-closed | `packages/qmf-risk/src/qmf/risk/control_window.py:617` (`ControlWindowRecord`), `:878` (`evaluate_entry_under_windows`), `:1057` (`fold_effective_window`), `:1159` (`fail_closed_on_uncertainty`), `:1441` (`mint_veto_decision`) | exists-as-is | Supply the window widths (declared variables at `:` `PROTECTION_WINDOW_VARIABLE_NAMES`) and drive it per entry | high |
| C15 | Per-instrument currency-exposure records that scope a window | `packages/qmf-risk/src/qmf/risk/control_window.py:354` (`CurrencyExposureRecord`), `resolve_instrument_scope`, `reject_symbol_currency_parse` | exists-as-is (shape) | Author the dated exposure records — symbol-string parsing is refused, so this is real node data | high |
| C16 | Wiring the news feed into protection windows | **absent bridge** — the recorder writes raw bytes, `CalendarFeedAdapter` decodes snapshots, `ControlWindowRecord` consumes resolved scope; nothing joins them | does-not-exist | Build feed → adapter → window-record pipeline | high |
| C17 | CT-29 exit records, close-reason taxonomy, whole-trade attribution, read-time bench fold | `packages/qmf-risk/src/qmf/risk/exit_record.py:304` (`ExitRecord`), `:814` (`fold_bench`), `:1042` (`ExitRecordStream`) | exists-as-is | Mint one per virtual close; `kill_line_flat` is minted apart from `protection_forced_flat` | high |
| C18 | **A live Book/BMS runtime that holds state and drives all of the above** | **absent** — every `qmf-risk` module is ratified `defined-unwired`: "no live binding, order, mode transition, or flatten is authorized by this code" (`packages/qmf-risk/src/qmf/risk/__init__.py:7-9`; repeated per module) | does-not-exist | This is the node's largest single build: the long-lived object that holds positions, equity, standing intents, and calls the pure law | high |
| C19 | Kill-switch behaviour when the broker connection is down | **nowhere designed** — `tracker/map.md:79`, `:92` (dossier PART G2) | does-not-exist | Design it; it is the highest-cost undesigned failure mode in the corpus | med |

## §D — Paper mode *(the most complete concern in the bin)*

| # | Capability | Exists where (path:line) | Status | Node work needed | Ev. |
|---|---|---|---|---|---|
| D1 | `BookMode` LIVE\|PAPER, `SeatState` active\|benched, binding state — three vocabularies never interchanged | `packages/qmf-risk/src/qmf/risk/paper.py:111`, `:125`, `:216` (`validate_book_mode` refuses a seat word in the mode field) | exists-as-is | Nothing | high |
| D2 | CT-24 binding-transition stream + read-time most-restrictive mode fold | `packages/qmf-risk/src/qmf/risk/paper.py:764` (`BindingTransitionStream.current_mode`) | exists-as-is | Append transitions; mode is a fold, never a stored flag | high |
| D3 | `resolve_execution_target` — routing decision from (mode, seat state, active controls) | `packages/qmf-risk/src/qmf/risk/paper.py:436` | exists-as-is | Resolve **once at intent mint**; a `blocks-paper` control dominates and blocks live and paper alike | high |
| D4 | `ExecutionTarget` + one-active-target-per-binding log | `packages/qmf-risk/src/qmf/risk/paper.py:326`, `:962` (`PaperTargetLog`) | exists-as-is | Supply the concrete live target (live role) and paired demo target (non-live role) | high |
| D5 | Frozen paper money: paper epoch record/log, reset, no paper PnL to treasury | `packages/qmf-risk/src/qmf/risk/paper.py:1227` (`PaperEpochLog`), `:1334` (`reset_paper_epoch`), `reject_paper_pnl_to_treasury` | exists-as-is | Wire the reset to an operator door | high |
| D6 | Return-to-live asymmetry (paper→live needs authorization, live→paper does not) | `packages/qmf-risk/src/qmf/risk/paper.py:1396` (`authorize_return_to_live`), `mint_return_to_live_transition` | exists-as-is | Wire to the operator door | high |
| D7 | Paper/live evidence separation by role-scoped namespace | `packages/qmf-data/src/qmf/data/logbooks.py:33-41` — live namespace admits only `role = live`; cross-role aggregation without an explicit declaration is a policy rejection | exists-as-is | Nothing — separation is by construction | high |
| D8 | Simulated fills for a paper lane that does **not** use a demo account | `qmb/src/qmb/execution/ports.py:905` (`FillPort` crossing a declared `SlicePath`) — simulation-shaped, not venue-shaped | exists-needs-live-adapter | Only needed if paper ≠ paired demo account; note every fill carries an `optimistic` taint until GAP-0048 (`ports.py:7,:95`) | high |

## §E — Bot seats & runtime protocol

| # | Capability | Exists where (path:line) | Status | Node work needed | Ev. |
|---|---|---|---|---|---|
| E1 | QL-7 factory → callback construction (no Book, clock, or venue surface injected) | `qml/src/qml/protocol/factory.py:212` (`construct_bot`), `:473` (`HostedBot`), `:558` (`FunctionFactory`); guards `:385-399` | exists-as-is | The node is the host: build the factory input and drive the callback | high |
| E2 | `drive_instant` host bridge | `qmb/src/qmb/host/adapter.py:62` | exists-as-is | Reuse directly | high |
| E3 | Live `ReadSurface.at(instant)` evidence producers | seam only: `qml/src/qml/protocol/evidence.py:699-712`; collector `:611`; look-ahead refused `:436-444` | does-not-exist | Build the live surfaces over qmf-data / indicators / structure — a substantial build | high |
| E4 | Bounded state + snapshot/restore contract | `qml/src/qml/protocol/state.py:122` (`BotStateScope` four-tuple), `:272`, `:362`; cross-tuple restore refuses `:260-269` | exists-needs-live-adapter | Inject the scope tuple — "the OS is never read ambiently" (`state.py:123-124`) | high |
| E5 | Per-seat state persistence across restarts | absent — QMB only *observes* restore-equivalence (`qmb/src/qmb/host/runner.py:446-447`) | does-not-exist | Persist and restore each seat's snapshot across a node restart | high |
| E6 | Intents out (zero-or-more CT-23; sizing and venue commands refused) | `qml/src/qml/protocol/intents.py:76` (`accept_intents`), rejections `:168-191` | exists-as-is | Route accepted intents into the Book door | high |
| E7 | Conformance Layer-1 static scan + Layer-2 pure verdict | `qml/src/qml/conformance/scan.py:200`, `qml/src/qml/conformance/layer2.py:200` (`evaluate_layer2`), `:271`, `:430` | exists-as-is | Supply the in-memory source tree and feed observations back | high |
| E8 | Layer-2 sandbox process isolation | soft version exists: `qmb/src/qmb/host/runner.py:115` (`run_sandbox`). Hardened OS confinement is "a named deferred dependency of the node/platform sitting" (`runner.py:10-13`, `:77-81`) | exists-needs-live-adapter | Harden it (seccomp-class on Linux) or accept the deferral explicitly | high |
| E9 | Prediction linter checks a–d + binding-context assembly | `qml/src/qml/conformance/prediction.py:174` (`lint_prediction`), context seam `:79-95` | exists-needs-live-adapter | Assemble the `PredictionBindingContext` at seat time from the Book's CT-22 exit policy + venue CT-18 tokens | high |
| E10 | Seat / roster / binding-to-Book **runtime** | **absent** — only declaration and citation types: `qml/src/qml/conformance/registration.py:108-113` (`CitationKind.SEAT`), `:268` | does-not-exist | Build the seat runtime and the roster | high |
| E11 | AD-41 `active\|benched` seat **record** | **absent** in both `qml/src` and `packages/qmf-registry/src` (grep clean) | does-not-exist | Declare the record kind and the state model | high |
| E12 | Slice handler that mints intents from a hosted bot in sub-phase 5 | `qmb/src/qmb/host/adapter.py:73` (`ConformantSliceHandler`), `:85-127` | exists-as-is | Reuse or write a live sibling | high |

## §F — Live data recording, bootstrap & backup

| # | Capability | Exists where (path:line) | Status | Node work needed | Ev. |
|---|---|---|---|---|---|
| F1 | Seven room-roles per world; live and replay each get their own set | `packages/qmf-data/src/qmf/data/store/rooms.py:50-71`; `packages/qmf-data/src/qmf/data/rooms.py:1-16` | exists-as-is | Instantiate for `world=live`; `world=simulated` is reserved-unusable | high |
| F2 | CT-11 content-addressed append store (Parquet, idempotent re-write, refused collision) | `packages/qmf-data/src/qmf/data/store/append_store.py:71-119` | exists-as-is | Call `append_raw` from the live writer with WriterId + sequence | high |
| F3 | CT-10 source-observation boundary (bitemporal, corrections append) | `packages/qmf-data/src/qmf/data/source_boundary.py:1`; `observation.py:1-22` | exists-as-is | Route live producer values through it | high |
| F4 | **Live venue market-data producer** (tick/spot → CT-10 observations) | **absent** — the value type exists (`packages/qmf-data/src/qmf/data/observation.py:240` `MarketDataContext`) but "future venue market-data adapters" are named as not-yet-built (`ingest.py:297`) | does-not-exist | Build the live producer; this is the largest data-side item | high |
| F5 | Venue market-data subscription on the wire | absent (subset of B1/B2) | does-not-exist | Subscribe, decode, and hand to F4 | high |
| F6 | Any running downloader / retry loop / scheduler | **refused by contract** — `packages/qmf-data/src/qmf/data/ingest.py:31`; `cycle.py:307-315` (`own_schedule()`/`start_daemon()` always return typed refusals) | does-not-exist | The node owns every loop that *calls* the ports | high |
| F7 | Dukascopy history bootstrap (bounded bi5 decode, download-once, license-tagged) | `packages/qmf-data/src/qmf/data/dukascopy.py:1`; bid/ask money fix landed (`:702-716`, FC-03) | exists-as-is | Drive bounded windows to bootstrap history | high |
| F8 | Concrete `DukascopyTransport` | seam only: `packages/qmf-data/src/qmf/data/dukascopy.py:23` | does-not-exist | Implement the byte transport | high |
| F9 | CT-13 journals: seven event types, one JSONL stream per producing component, block-on-unpersistable | `packages/qmf-data/src/qmf/data/journal.py:108-126`; `packages/qmf-data/src/qmf/data/store/journal.py:1-9`; `journal_producer.py:33-45` | exists-as-is | One writer per producing component; call `retry_blocked` on recovery | high |
| F10 | Sequence-gap detection = surfaced loss, never swallowed | `packages/qmf-data/src/qmf/data/journal.py:769` | exists-as-is | Alarm on the loss signal | high |
| F11 | Twelve-month research seal enforced at every read boundary (content-derived, post-FC-06) | `packages/qmf-data/src/qmf/data/seal.py:1-8`, `:82-97`; guards at `store/append_store.py:158`, `:165`, `:333` | exists-as-is | Supply `holdout_months` from config; it is never hardcoded | high |
| F12 | Entity-journal projections (Book / BMS / per-bot logbooks) | `packages/qmf-data/src/qmf/data/logbooks.py:1`; risk-side twin `packages/qmf-risk/src/qmf/risk/journal.py:858` | exists-as-is | Surface through operator doors | high |
| F13 | CT-14 encrypted versioned off-machine backup primitive | `packages/qmf-data/src/qmf/data/backup.py:1-8`; `ENCRYPTION_REQUIRED = True` `:75` | exists-needs-live-adapter | Inject the backend and the cipher | high |
| F14 | Concrete `ObjectStorage` backend | seam only: `packages/qmf-data/src/qmf/data/backup.py:120` — "Object-key layout, provider selection, and credentials stay outside QMF" | does-not-exist | Pick and build (local / S3-compatible / rclone — none chosen anywhere) | high |
| F15 | `PayloadCipher` + key custody | seam only: `packages/qmf-data/src/qmf/data/backup.py:100` — "the crypto dependency is node/ops-owned" | does-not-exist | Build; DEC-0136 assigns key custody to this sitting | high |
| F16 | Sample-restore + full-restore rehearsal (the only source of a recoverability claim) | `packages/qmf-data/src/qmf/data/verify.py:1-6` | exists-as-is | Schedule them | high |
| F17 | Nightly off-machine cycle (`run_once`) | `packages/qmf-data/src/qmf/data/cycle.py:1-16` — no threads, cron, or daemon in qmf-data | exists-needs-live-adapter | Add the scheduler that calls it | high |
| F18 | Numeric RPO / RTO / retention depth / verification cadence | **null node/ops pointers, never filled** — `verify.py:10`, `:67`; `cycle.py:124-137` | does-not-exist | Rule the numbers (DEC-0118 assigns them here) | high |

## §G — Calendar & time

| # | Capability | Exists where (path:line) | Status | Node work needed | Ev. |
|---|---|---|---|---|---|
| G1 | Market-hours calendar: 17:00 NY rollover, session windows, weekend gap Fri 17:00 → Sun 17:00 | `extensions/qmf-calendar-forex/src/qmf/calendar_forex/_provider.py:38-40`, `:135`, `:155-180` | exists-as-is | `register_forex_17ny()` at the node root — named registration only, never scanning | high |
| G2 | tz database pin + verification (tzdata 2025.2 → IANA 2025b), calendar identity in `TradingDate` | `extensions/qmf-calendar-forex/src/qmf/calendar_forex/_tzdb.py:20-27`, `:83-101`; `packages/qmf-core/src/qmf/core/chrono.py:1053` | exists-as-is | Nothing — but see red flag R4 | high |
| G3 | Instant / Duration / Interval / TradingDate / CalendarIdentity, checked arithmetic, overflow refused | `packages/qmf-core/src/qmf/core/chrono.py:230`, `:323`, `:394`, `:502`, `:558` | exists-as-is | Nothing | high |
| G4 | Wall vs monotonic separation; WriterId / WriterSequencer / OrderingKey | `packages/qmf-core/src/qmf/core/chrono.py:641`, `:807`, `:902`, `:858` | exists-as-is | Mint WriterIds per (machine, role, stream) + boot epoch | high |
| G5 | News-calendar recorder (FairEconomy weekly feed, raw bytes, sha256-deduped, append-only) | `recorder/fetch_calendar.py:1`, `:29-35`, `:48-52`, `:179-183` | exists-as-is (standalone) | Re-home scheduling from the Windows Scheduled Task (`recorder/README.md:15`) to the Linux VPS; an unrecorded week is permanently lost evidence | high |
| G6 | `CalendarFeedAdapter` — decode a snapshot into CT-15 evidence + CT-13 data-quality journal, fail-closed, no live skip button | `packages/qmf-data/src/qmf/data/calendar_feed.py:1-14`, `:82`, `:94-105` | exists-needs-live-adapter | Inject `CalendarFeedTransport`; legal archiving posture is still an open operator item (`:84`, `:221-232`) | high |
| G7 | Recorder → adapter bridge | **absent** — the two halves are not wired (dossier §9) | does-not-exist | Build the bridge, or fold the recorder into the adapter | high |
| G8 | Day-boundary / evaluation-day calendar | **refused as out-of-authority** — `extensions/qmf-calendar-forex/src/qmf/calendar_forex/_provider.py:195-201` | does-not-exist | Only if the node needs one; it is a new named kind | high |
| G9 | Clock-sync monitoring (chrony offset / stratum / sync-age, per-venue skew, clock-step counter) | **absent anywhere in code**; named as an obligation in `docs/lenses/observability/metrics-and-alerts.md:20` | does-not-exist | Build it — the venue exposes no server clock (`ctrader.py:333-335`, `SERVER_CLOCK_AVAILABILITY: False` `:1083`) | high |

## §H — Registry & promotion

| # | Capability | Exists where (path:line) | Status | Node work needed | Ev. |
|---|---|---|---|---|---|
| H1 | Registration records, `Registrar`, per-(writer,kind) monotonic sequence, addable-never-redefined kinds | `packages/qmf-registry/src/qmf/registry/records.py:257`, `:540`, `:657`, `:764`, `:876` | exists-as-is | Hold the WriterId at the root and stamp records | high |
| H2 | Promotion card + `authorize_live_promotion` — the only path to live money | `packages/qmf-registry/src/qmf/registry/promotion.py:210`, `:508`, `:643` | exists-as-is | Supply the supersession state; a superseded card refuses | high |
| H3 | Current-head tracking (head is derived from the supersedes chain, not stored) | node-owned: `promotion.py:578-605` requires a `superseded` state argument | does-not-exist | Own head tracking | high |
| H4 | CT-07 typed lineage edges (supersedes, promoted-from, branches-from, continues-performance, carries-ledger, enacts) | `packages/qmf-registry/src/qmf/registry/lineage.py:104`, `:269` | exists-as-is | Author the edges | high |
| H5 | AD-30 dated current-pointer record for the branching graph | **absent** — the edge type exists, the pointer record does not (`lineage.py:126-127`) | does-not-exist | Build it | high |
| H6 | Book-instance / BMS-instance / binding record **kinds** | **absent** — only the generic `FieldSetKind` mechanism (`records.py:540`) | does-not-exist | Declare each as a `FieldSetKind` contract at the root | high |
| H7 | CT-33 Bot-kind mint at the composition root (post-OR-06) | deleted from qml by FC-05; marker at `qml/src/qml/declaration/bot.py:628-635` "defined-unwired" | does-not-exist | Build the mint at the node root — this is exactly what OR-06 relocated | high |
| H8 | Registry-read port over immutable as-of sets (no second cache) | `qmb/src/qmb/registryread/port.py:1-6`; `qmb/src/qmb/registryread/as_of.py` | exists-as-is | Read through it; store location + sync cadence are node/ops (`registryread/hub.py:5`) | high |
| H9 | Registry persistence per world, content-addressed on fp1 | `packages/qmf-registry/src/qmf/registry/__init__.py:31-44`; `persistence.py` | exists-as-is | Wire the live world's room | high |
| H10 | Human-signed promotion **workflow** (UI, timing, signer identity) | **absent** — "explicitly platform territory" (`promotion.py:6-7`) | does-not-exist | Build the workflow and the door; see QA debt Q1 | high |

## §I — Operator doors, CLI, config

| # | Capability | Exists where (path:line) | Status | Node work needed | Ev. |
|---|---|---|---|---|---|
| I1 | Thin-door pattern + a click CLI precedent to copy | `qmb/src/qmb/doors/__init__.py:1-6`; `qmb/src/qmb/doors/cli/__init__.py:1`; command tree `qmb/src/qmb/doors/cli/tree.py:93-102` | exists-as-is (pattern only) | Copy the shape; no live/paper/node/start/stop command exists anywhere | high |
| I2 | Node operator commands (start, stop, status, flatten, kill, resume, promote, mode, seat) | **absent** — the whole command set | does-not-exist | Build them; every operator control gets a CLI/API door now, screen later | high |
| I3 | In-process Python API door (the UI-later backend seam) | `qmb/src/qmb/doors/api/__init__.py:1-8` — never stacked over HTTP | exists-as-is | Mirror the pattern for the node | high |
| I4 | Agent/MCP door | scaffold only — `qmb/src/qmb/doors/mcp/__init__.py:37-43`, `SHIPPED=False`, localhost-bound | does-not-exist | Ships after CLI v1 | high |
| I5 | Door parity derived programmatically, never a hand catalog | `qmb/src/qmb/doors/parity.py:1-14` (OR-08; the retired catalog is what masked QMX-F016/F017) | exists-as-is | Reuse the derivation approach for node doors | high |
| I6 | Generic ui-editable **configurable-variable registry** (AD-30 / L38) | **absent** — the only ui-editable machinery is per-bot-parameter `UiFlag` (`qml/src/qml/declaration/parameters.py:69`, `:225`) and the risk template's `UiEditability` (`packages/qmf-risk/src/qmf/risk/grammar.py`) | does-not-exist | Build the node's own registry; mirror the `UiFlag` pattern | high |
| I7 | Config format for a long-lived service | absent — QMB has Book/BMS fragments + a run-spec for *finite* runs, emitted as `run-config.json` (`qmb/src/qmb/config/compiler.py:93`, `:187`) | does-not-exist | Decide and build; no bespoke config file exists to extend | high |
| I8 | Refusal rendering at the door (stderr JSON) | `qmb/src/qmb/doors/cli/render.py` (`render_refusal`) | exists-as-is | Reuse | med |

## §J — Logging, metrics, health

| # | Capability | Exists where (path:line) | Status | Node work needed | Ev. |
|---|---|---|---|---|---|
| J1 | Typed refusals — **seven** categories + retryability, returned never raised | `packages/qmf-core/src/qmf/core/refusal.py:50-64`, `:66-72`, `:125`; per-package builders e.g. `qmb/src/qmb/_refuse.py:39-70` | exists-as-is | Handle all seven (the discovery brief said six — the corpus has seven) | high |
| J2 | Tail-able JSONL operational log, correlation-id excluded from fp1 | `qmb/src/qmb/orchestrator/log.py:1-9`, `:6-8` — per-**run** directory, flushed so a live run is tail-able | exists-needs-live-adapter | Convert per-run rooms into a long-lived rotating stream | high |
| J3 | Operator log framework: levels, logger names, file paths, query | **absent** — no `logging`, `structlog`, `loguru`, `journald`, or `getLogger` in shipped source. Only the UTC ISO-8601 `Z` convention binds (`docs/lenses/observability/logging-spec.md:16`, `:25`) | does-not-exist | Build it | high |
| J4 | Structured event / metrics emitter (AD-14 traceable behaviour) | **absent in qmf-core** — loud failure is delivered only via `TypedRefusal` + block-on-unpersistable (`packages/qmf-core/src/qmf/core/sinks.py:150`, `:205`) | does-not-exist | Build the event bus and metrics surface | high |
| J5 | Prometheus-class exporter with push alerting | **absent** — the exportability obligation binds now, nothing implemented (`docs/lenses/observability/metrics-and-alerts.md:16`, `:20`); no `prometheus_client` anywhere | does-not-exist | Build the exporter | high |
| J6 | Per-component in-process `health()` | `packages/qmf-venue/src/qmf/venue/connection.py:338`, `:694`; `packages/qmf-indicators/src/qmf/indicators/streaming.py:918`; `qmb/src/qmb/orchestrator/log.py:451` | exists-as-is | Call them; a component with no working `health()` is a defect (`docs/lenses/bugs/triage.md:25`) | high |
| J7 | Aggregated node health surface / endpoint | **absent** — `/health` appears only in factory prompt templates and prose | does-not-exist | Build the aggregation and the door | high |
| J8 | Metrics schema, aggregation window, dashboards, alert thresholds, severity tiers, paging routes | **absent and explicitly unratified** (`docs/lenses/observability/metrics-and-alerts.md:16`, `:46`, `:48`) | does-not-exist | Rule and build | high |
| J9 | `correlation_id` propagation, excluded from identity | `packages/qmf-data/src/qmf/data/journal.py:27`, `:296`; `qmb/src/qmb/orchestrator/log.py:6-8` | exists-as-is | Propagate across node boundaries | high |
| J10 | `FAILURES.md` register convention (six NFR-11 fields per designed failure) | `conventions/failure-register.md:1-49`; exemplars `packages/qmf-venue/FAILURES.md:9-124` (FR-1..6), `packages/qmf-risk/FAILURES.md` (134 lines, seven entries) | exists-as-is | Follow it for every node failure mode — connection loss, credential expiry, drift, kill switch, flatten | high |
| J11 | Benchmark harness (AD-13 measure-then-budget) | present per package, but `packages/qmf-venue/src/qmf/venue/_bench.py:50` and `packages/qmf-risk/src/qmf/risk/_bench.py:50` are deliberate **placeholders** (`_bench.py:7`) | exists-needs-live-adapter | Write the real workloads for the two packages the node's hot path runs through | high |

## §K — Process, scheduler, async driver

| # | Capability | Exists where (path:line) | Status | Node work needed | Ev. |
|---|---|---|---|---|---|
| K1 | **Async live event-loop driver** | **absent, and `asyncio`/`threading`/`sched`/`multiprocessing` are banned inside the libraries by conformance tests** — `packages/qmf-data/tests/test_cycle.py:225`; `qml/src/qml/conformance/scan.py:72-73`. Zero `async def`/`await` in the whole product tree (grep clean) | does-not-exist | Build it strictly **above** the library boundary; stdlib only (no platform-imposing dep, `DEPENDENCIES.md:11-13`) | high |
| K2 | Push-to-pull sample accumulator (append a live tick and advance) | **absent** — `qmb/src/qmb/runloop/bars.py:324` `UnderlyingSeries.samples` is an immutable fingerprinted `tuple`; `run()` materializes a `Sequence` up front (`loop.py:1530-1550`) and iterates it (`:877`) | does-not-exist | Build an appendable series + frontier advance per incoming sample | high |
| K3 | Single-slice pure primitive (`run_slice`) threading frontier + resting in and out | `qmb/src/qmb/runloop/loop.py:687`, returns `SliceOutcome` `:776-791` | exists-as-is | Call once per live slice, carrying `current` and `resting` between calls — the reusable half of the loop | high |
| K4 | Six pinned identity-bearing sub-phases; same-slice new intent never fills | `qmb/src/qmb/runloop/loop.py:112-119`, `:120` (`SAME_SLICE_NEW_INTENT_FILL = False`), enforced `:1256-1261` | exists-as-is | Preserve the order — changing it is identity-bearing | high |
| K5 | `SliceHandler` seam (update_stream, scheduled_position_event, execute_resting, update_closed_data, mint_intents) | `qmb/src/qmb/runloop/loop.py:599-644`; default no-op `:647` | exists-as-is | Inject the node's own live handler | high |
| K6 | `LiveExecutionPort` — same CT-23 `AuthorizedIntent` in, venue out | **absent** — "Nothing here imports `qmf-venue`" (`qmb/src/qmb/execution/ports.py:10-11`); no venue-shaped execution Protocol exists | does-not-exist | Build it; it slots at `bind_execution_ports` (`binder.py:235`) / `execute_authorized` (`ports.py:1120`) with the CT-23 checks reusable around it | high |
| K7 | Fill / slippage / cost / financing ports (simulation-shaped) | `qmb/src/qmb/execution/ports.py:905`, `:920`, `:933`, `:952`; composition order `:93`; admission==fill parity landed `cost.py:6-8` | exists-as-is (for a simulated lane) | Reuse for a simulated paper lane only; rate content deferred to GAP-0048 | high |
| K8 | Scheduler for session duties, the nightly cycle, and the recorder | **absent and refused by the libraries** (see B14, F6) | does-not-exist | Build one scheduler the node owns | high |
| K9 | Long-lived process supervisor | **absent** — `qmb/src/qmb/orchestrator/spawn.py:179` spawns *finite* one-shot processes; the only `while True` in product code is a bounded run-scoped watch (`spawn.py:508`) | does-not-exist | Build supervision for continuously-running seats and the order path | high |
| K10 | Resource governor: min(cpu, memory) admission with enqueue-on-full, reservation derived from the running set | `qmb/src/qmb/orchestrator/governor.py:75`; budgets are registry keys, never baked (`:2-7`) | exists-as-is | Reuse; long-lived seats differ from finite runs | high |
| K11 | Process spawn / isolation + real peak-memory probe | `qmb/src/qmb/orchestrator/spawn.py:179`, `:402-409`; `qmb/src/qmb/orchestrator/watch.py` (`ProcessLimitProbe`, `/proc` VmHWM on POSIX) | exists-as-is | Reuse; extend for long-lived RSS watch | high |
| K12 | OS-enforced hard cap (job objects / rlimit / seccomp) | **absent and deferred** — `qmb/src/qmb/host/runner.py:10-13`, `:77-81`; grep for `setrlimit`/`RLIMIT` in `orchestrator/` is clean | does-not-exist | Named deferred dependency of *this* sitting | high |
| K13 | Cancel / cooperative abort at slice boundaries | `qmb/src/qmb/runloop/observe.py:60` (`CancelToken`), `:365` | exists-as-is | Reuse at slice boundaries; "No threads" model | high |
| K14 | Signal handling / graceful shutdown | **absent** — no `signal.signal` anywhere in product code | does-not-exist | Define the shutdown contract (drain, flush journals, close sessions) | high |

## §L — Deployment & CI

| # | Capability | Exists where (path:line) | Status | Node work needed | Ev. |
|---|---|---|---|---|---|
| L1 | uv workspace, pinned toolchain, poe task surface | `pyproject.toml:85-92`, `:137-141`, `:452-507` | exists-as-is | Add the node package as a workspace member | high |
| L2 | Four tier-1 static scanners (money-path float, ambient nondeterminism, mock data, secret) | `pyproject.toml:470-479`; `tools/money_path_scan.py`, `tools/ambient_scan.py`, `tools/mock_data_scan.py`, `tools/secret_scan.py` | exists-as-is | The node's code is in scope the moment it lands (scanners subtract by name, not include-list) | high |
| L3 | Skylos gate + QA Battery CI (check / vulture ratchet / nightly mutation) | `.github/workflows/skylos.yml`, `.github/workflows/battery.yml:30-153`; hard-zero buckets + two ratchets `pyproject.toml:402-450` | exists-as-is | Keep the node inside the gates; the vulture baseline ratcheted to zero (`FINAL-REPORT.md:71-74`) | high |
| L4 | CI exercising the node's actual OS | CI is 100% `ubuntu-latest` (`skylos.yml:36`; `battery.yml:35,57,85`) but the type gate renders the **Windows** view (`pyproject.toml:307-312`) and the Ubuntu clean-install smoke is deferred until a remote exists (`:503-506`) | exists-needs-live-adapter | Add a Linux lane that actually validates the Linux view | high |
| L5 | Service unit for the node on the VPS | **absent** — no `Dockerfile`, compose file, `.service`, Procfile, terraform, ansible, cloud-init, or install.sh exists anywhere. The only precedent is the factory's `sdl-engine.service`, referenced in comments and never committed (`justfile:99-110`) | does-not-exist | Write the unit (`Restart=on-failure`, start-limit counters; crash-loop K/T thresholds are open) | high |
| L6 | Node package + console script | absent (see A9) | does-not-exist | Create | high |
| L7 | VPS provisioning / install path | absent | does-not-exist | Build | high |
| L8 | Secret provisioning on the VPS (`systemd-creds`-class) | **docs only** — `docs/contracts/ct-21-venue-secret-session.yaml:28`, `docs/lenses/security/security-model.md:61`, `docs/lenses/ops/runbook.md:122`, all deferring mechanics and key custody to this sitting (DEC-0136). No `keyring` anywhere; no venue credentials in `.env.sample` | does-not-exist | Build; secrets never enter repo, config, `.env`, CLI, journals, evidence, fingerprints, or logs | high |

**Row census: 154 capabilities — 78 exists-as-is, 24 exists-needs-live-adapter, 52 does-not-exist.**

---

# 2. THE VERDICT

## Method (stated so it can be argued with)

Two different questions hide inside "is 60% already built?", and they give different answers.

**Method 1 — capability count.** Of 154 node capabilities, how many are *touched* by an existing
part (exists-as-is or exists-needs-live-adapter)?

> (78 + 24) / 154 = **66%**. With adapter rows at half credit: (78 + 12) / 154 = **58%**.

**Method 2 — node-effort weighting (the one I trust).** Each row carries an effort weight `W`
(1–10, my estimate of what delivering that capability costs the node **from scratch**, with the
heaviest weights on the live transport, the async driver, the Book/BMS runtime, and the live
evidence surfaces), and a coverage fraction `S` — `0.85–1.0` for exists-as-is (wiring and
value-authoring still cost something), `0.3–0.6` for exists-needs-live-adapter depending on how
much of the live half is missing, `0` for does-not-exist.

> Σ(W·S) / Σ(W) = 274.85 / 567 = **48.5%**.

**Verdict: 45–60% of node effort is already in the bin — call it "about half", not "about
60%".** The honest band is 45–60% because the effort weights are estimates, not measurements
(and AD-13 says budgets come from measurement — `packages/qmf-venue/src/qmf/venue/_bench.py:7`
and `packages/qmf-risk/src/qmf/risk/_bench.py` are still placeholders, so no measurement exists
for the two packages the node's hot path runs through). I will not give a single number.

**The operator's ~60% is defensible but it is the top of the band, and its shape is wrong.**
Directionally the instinct is right and the "adaptation, not rebuild" framing is correct for
*law*. But the parts are not evenly distributed. Sorted by concern, coverage runs:

| Concern | Effort covered |
|---|---|
| §D Paper mode | **81%** |
| §G Calendar & time | 60% |
| §C Risk pipeline & protections | 59% |
| §B Venue session & order path | 53% |
| §F Live data recording & backup | 53% |
| §A Composition root & boot | 48% |
| §H Registry & promotion | 45% |
| §E Bot seats & runtime protocol | 45% |
| §L Deployment & CI | 38% |
| §K Process / scheduler / driver | 33% |
| §J Logging / metrics / health | 33% |
| §I Operator doors / CLI / config | **26%** |

The parts bin is ~60–80% full where the problem is **law** (what is legal, what is exact, what
refuses) and ~25–35% full where the problem is **runtime** (what runs continuously, what a human
can see and press). The node is not "40% of a trading system"; it is **100% of a runtime plus the
wiring of a very complete rulebook**. Plan the epics accordingly: the law rows are one-line
wiring stories, the runtime rows are the real build.

## The three biggest `does-not-exist` clusters

**Cluster 1 — the continuously-running node itself (≈44 effort units).** The async live driver
(K1), the push-to-pull accumulator (K2), the scheduler for session duties and the nightly cycle
(K8, B14, F17), the long-lived process supervisor (K9), graceful shutdown (K14), the seat/roster
runtime (E10), and the live Book/BMS object that actually holds positions, equity, and standing
intents (C18). Nothing in the corpus runs continuously; the libraries *refuse by contract* to
(`packages/qmf-data/src/qmf/data/cycle.py:307-315`, `ingest.py:31`) and *ban* the primitives
(`packages/qmf-data/tests/test_cycle.py:225`; `qml/src/qml/conformance/scan.py:72-73`). This
cluster was deliberately reserved for this sitting, and it is the largest.

**Cluster 2 — operator doors plus supervision and observability (≈40 effort units).** The node's
whole operator command set (I2), the ui-editable configurable-variable registry (I6), a config
format for a long-lived service (I7), the agent door (I4), the operator log framework (J3), the
structured event and metrics emitter (J4), the Prometheus-class exporter (J5), the aggregated
health surface (J7), and the alert/severity/paging design (J8). The contract separates logs from
journals (DEC-0112) and the journal half is fully built; the operator half is entirely prose.

**Cluster 3 — a real cTrader transport and the live market-data path (≈34 effort units).** The
socket/TLS/framing/message loop (B1), outbound request encoding (B2), the submit path (B10), the
market-data subscription (F5), and the live producer that mints CT-10 observations from venue
ticks (F4). `qmf-venue` is 9,180 lines of decoders, law, and a facade — with no wire at all.
Note the two smaller but sharp gaps riding alongside: the **cents/volume decoder** (B26) and
**equity derivation** (B27). Equity is not a nicety; the kill line is a capital floor and there
is no function anywhere that computes balance + unrealized PnL.

*(A fourth cluster, smaller but worth naming for the epic split: live evidence surfaces for bots
(E3) plus per-seat state persistence (E5) — the seats cannot be driven without them.)*

## The three biggest `exists-as-is` wins

**Win 1 — the risk and control law is finished and tested.** `qmf-risk` is 16,905 src LOC across
24 modules with 613 test functions, four executable examples, and a 134-line failure register: the
CT-23 door, R's three typed faces and the full-loss law, three-layer admission with a human
signature, the admission bar with no composite score and blank-blocks-live, CT-30 control actions
with the exit-preservation invariant, kill switch and kill line named apart, CT-31 protection
windows, CT-29 exit records, and same-tick rank arbitration. Every module is `defined-unwired` on
purpose. The node wires it; it does not design it.

**Win 2 — the venue uncertainty law and the order-state fold.** The four-outcome model where
`denied-locally` is never a refusal and `UNKNOWN` is never an error
(`packages/qmf-venue/src/qmf/venue/commands.py:183-238`), the UNKNOWN gate with an
application-originated `resolve_unknown` that never clears on a reconciliation verdict alone
(`blocking.py:464`, `:767-778`), record-before-interpret with multi-room atomic-or-recovery
(`events.py:1157`), and the read-time order-state fold where a terminal state can come only from
fills and venue lifecycle events, never from a command outcome (`events.py:878`). This is the part
of a live trading system that is hardest to get right and easiest to get subtly wrong, and it is
done, with 407 tests.

**Win 3 — paper mode, at 81% the most complete node concern in the bin.** `BookMode`, `SeatState`
and binding state as three vocabularies that can never be interchanged; CT-24 transitions with a
most-restrictive read-time fold; `resolve_execution_target` resolving once at intent mint so a mode
flip can never replay a command or double-submit; one active target per binding; frozen paper money
with an epoch reset and a hard refusal on paper PnL reaching the treasury; the return-to-live
asymmetry; and live/paper evidence separated by role-scoped namespace rather than by discipline.
Milestone 1 — paper on the demo account under full logging — is mostly a wiring exercise against
already-ratified law. *(This is precisely the win the QMB dossier's `does-not-exist` row would have
hidden.)*

*Honorable mention, and load-bearing for everything above:* exact money and time in `qmf-core`
(scaled integers, float refused except at named boundaries, checked arithmetic that refuses
overflow), the single fp1 implementation, and seven typed refusal categories returned never
raised. These make the whole bin composable.

---

# 3. ADAPTATION SEAMS — the design input for the spine

Every `exists-needs-live-adapter` row resolves to a named protocol or port the node must implement
or fill. These are the spine's real interface list.

| Seam | Where | What the node implements |
|---|---|---|
| `ProbeTransport` (Protocol) | `packages/qmf-venue/src/qmf/venue/probe.py:224` | The credential-free demo transport for the first-connection probe. **The only Protocol in `qmf-venue`** — there is no `VenuePort`/`OrderPort`/`VenueAdapter` seam; the venue contract is realized as concrete typed values, so the node's live client is composed *around* them, not injected *into* them |
| `Clock` (Protocol) — `wall_now() -> Result[Instant]`, `monotonic_now() -> Result[MonotonicReading]` | `packages/qmf-core/src/qmf/core/chrono.py:711`, methods `:730-735` | The real wall clock, at the composition root only. There is no `WallClock` class; only `DataDrivenClock` (`:739`) exists |
| `SecretStore` (Protocol) — read + `atomic_replace` | `packages/qmf-core/src/qmf/core/secret.py:291` | The `systemd-creds`-class store; the venue `ConnectionManager` is its sole in-memory holder |
| `ObservationSink` / `JournalSink` / `RecordSink` | `packages/qmf-core/src/qmf/core/sinks.py:104` / `:121` / `:136` | Durable concrete sinks; unpersistable blocks the command stream (`sinks.py:150`) |
| `ExitLogicModule` (Protocol) — `derive_full_loss_price(entry_price, direction, cited_evidence)` | `packages/qmf-risk/src/qmf/risk/door.py:469` | One module per exit family; the per-family arithmetic is node territory (DEC-0142) |
| `ProducerContract` (Protocol) | `packages/qmf-risk/src/qmf/risk/admission.py:143` | The cited producers for admission recompute and the sizing ladder's runtime evaluation against live Book state |
| `ExecutionTarget` values (live role + paired demo role) | `packages/qmf-risk/src/qmf/risk/paper.py:326`, log `:962` | The two concrete targets `resolve_execution_target` (`:436`) selects between |
| `SliceHandler` (Protocol) — `update_stream`, `scheduled_position_event`, `execute_resting`, `update_closed_data`, `mint_intents` | `qmb/src/qmb/runloop/loop.py:599-644` | The node's live handler, injected the way `ExecutionSliceHandler` is for backtest |
| `FillPort` / `SlippagePort` / `CostPort` / `FinancingPort` | `qmb/src/qmb/execution/ports.py:905` / `:920` / `:933` / `:952` | Only for a simulated paper lane; a live lane needs a new venue-shaped port instead |
| `SlippageModel.offset(..., seed=)` | `qmb/src/qmb/execution/ports.py` (FC-30, `FIX-LEDGER.md:43`) | Plumbing exists; no stochastic model does, by ruling (OR-11) |
| `ExternalSourcePort` (Protocol) — `fetch(request) -> Result[tuple[ProviderRecord, ...]]` | `packages/qmf-data/src/qmf/data/ingest.py:295` | One bounded call per invocation; the node owns the loop that calls it |
| `DukascopyTransport` | `packages/qmf-data/src/qmf/data/dukascopy.py:23` | The bi5 byte transport for history bootstrap |
| `CalendarFeedTransport` / `decode_calendar_snapshot` | `packages/qmf-data/src/qmf/data/calendar_feed.py:1-14` | Feed the recorder's raw FairEconomy bytes through the adapter |
| `ObjectStorage` (Protocol) — `put(world, copy_version, source_room_role, payload, format_version)` / `get(...)` | `packages/qmf-data/src/qmf/data/backup.py:120` | The off-machine backend; provider, key layout, and credentials all stay outside QMF |
| `PayloadCipher` (Protocol) | `packages/qmf-data/src/qmf/data/backup.py:100` | Encryption is required (`ENCRYPTION_REQUIRED = True`, `:75`); key custody is node/ops |
| `ReadSurface` — `.at(instant)` | `qml/src/qml/protocol/evidence.py:699-712` | The live evidence surfaces bots read; look-ahead is refused (`:436-444`) |
| `BotStateScope` four-tuple `(os, logic_identity, protocol_format_version, arithmetic_reference_build)` | `qml/src/qml/protocol/state.py:122-124` | Injected — "the OS is never read ambiently"; cross-tuple restore refuses (`:260-269`) |
| `PredictionBindingContext` | `qml/src/qml/conformance/prediction.py:79-95` | Assembled at seat time from CT-22 exit policy + footprint requirements + venue CT-18 tokens |
| `SnapshotScope` `(OS, arithmetic-reference build)` | `packages/qmf-indicators/src/qmf/indicators/streaming.py:189`; snapshot/restore `:938`/`:969` | Injected for streaming-indicator restore-equivalence |
| `StreamingIndicator.update()` feeder `WriterId` (single-feeder law) | `packages/qmf-indicators/src/qmf/indicators/streaming.py:685`, `:838-862` | One holder per streaming instance on the live path |
| `SessionDuty` / `SchedulableDuty` / `SESSION_DUTIES` | `packages/qmf-venue/src/qmf/venue/ctrader.py:742-755`, `:757-775`, `:778-784` | The node's scheduler runs the five declared duties; only heartbeat carries a venue-bound cadence |
| `RatePacer.admit` + injected `MonotonicReading` | `packages/qmf-venue/src/qmf/venue/ctrader.py:507`, `:541` | Supply monotonic stamps and the below-ceiling cadence (node value, do-not-default) |
| `WriterSequencer` / `next_command_key` | `packages/qmf-venue/src/qmf/venue/connection.py:511`, `:417` | The node owns the sequencer; QMF carries the field (`commands.py:691-693`) |
| `ReconciliationReadback.verdict(expected, observed)` + mandatory `declared_lookback` | `packages/qmf-venue/src/qmf/venue/events.py:1391`, `:1307-1308` | Read the venue back and fold orders/fills/positions/balance into an observed state |
| `RegistryReadPort` over immutable as-of sets | `qmb/src/qmb/registryread/port.py:1-6` | Read through it only; no second cache (DEC-0165) |
| `ProviderAdapter` (batch, Jesse-`CandleExchange`-shaped) + `ProgressSink` | `qmb/src/qmb/data/ports.py:87`, `:64-83` | For history download only, never a live feed |
| `CancelToken` / `LimitProbe` | `qmb/src/qmb/runloop/observe.py:60`, `:280`; real probe in `qmb/src/qmb/orchestrator/watch.py` | Cooperative abort at slice boundaries; long-lived RSS watch |
| `register_forex_17ny()` (named composition-root registration) | `extensions/qmf-calendar-forex/src/qmf/calendar_forex/__init__.py:14-17` | Register explicitly — never package scanning, entry points, or `pkgutil` |

**Do-not-default values the node must rule (each refuses rather than defaulting):** the submission
deadline that turns an order UNKNOWN (`packages/qmf-venue/src/qmf/venue/commands.py:47`, `:1167`);
the reconciliation lookback (`events.py:1307-1308`); pacing and backoff cadence
(`ctrader.py:130`, `:135`, `:516`); `holdout_months` (`packages/qmf-data/src/qmf/data/seal.py:16`);
numeric RPO/RTO/retention/verification cadence (`verify.py:10`, `:67`; `cycle.py:124-137`);
governor CPU and memory budgets (`qmb/src/qmb/orchestrator/governor.py:2-7`); the KSA severity →
effect matrix (`packages/qmf-risk/src/qmf/risk/control_action.py:934-935`); protection-window
widths (`control_window.py` `PROTECTION_WINDOW_VARIABLE_NAMES`); crash-loop K/T thresholds
(`docs/lenses/ops/runbook.md:122`).

---

# 4. QA DEBT TOUCHING THE NODE

Baseline: 1,379 tests, 131 consolidated findings — **44 CONFIRMED, 64 UNPROVEN, 23
VERIFICATION-DEBT**. All 44 CONFIRMED were fixed and PROVEN in Fix Round 1 (35 cards). The 64
UNPROVEN and 23 VERIFICATION-DEBT rows were **out of scope for that round and are inherited by the
node phase**. Each row below is classified `node story` (the node must build or prove it, because
only a running node can) or `foundation debt` (a gap in a shipped package the node merely inherits).

| # | Item | Sev / status | Classification |
|---|---|---|---|
| Q1 | **QMX-F045** — human-only promotion signer never asserted; `PromotionCard.sign(signer="agent:...")` never tested; "can an agent mint a card `authorize_live_promotion` accepts?" is unanswered (`proof_map.md:35`) | high / UNPROVEN | **node story** — the node owns the promotion workflow and the signer identity (`promotion.py:6-7`). This is the gate on live money and it is unproven |
| Q2 | **QMX-F062** — UNKNOWN block proven on exactly one stream; CT-19 `(venue, account)` granularity untested in both directions: a whole-connection block and a submitting-binding-only block both pass every test | high / UNPROVEN | **node story** — the node *chooses* the granularity and must prove it |
| Q3 | **QMX-F063** — CT-18 amend-atomicity verify-or-refuse rule has zero tests; dual-side amend refusal never driven | high / UNPROVEN | **node story** — `amend_protection` sits on the node's order path |
| Q4 | **QMX-F064** — Spotware/Twisted SDK ban, secret-scan gate, undeclared order-parameter refusal, and **boot sequence-reset** all untested | medium / UNPROVEN | **node story** — boot sequence-reset is startup ordering, which only the node has |
| Q5 | **QMX-D008** — 15 missed venue clauses: CT-19 stream granularity, CT-18 amend atomicity, the ban, boot sequence-reset, **the five schedulable duties**, continuous re-verification, venue-managed trailing, retry-after mapping | high / verification-debt | **node story** — the duties and re-verification exist only when something runs them |
| Q6 | **QMX-F067** — five Epic-10 gaps: colliding-action collapse rank winner; window retro-invalidation; fingerprinted population; **Layer-2 demo/paper shakedown never called**; cardinality Bot↔Book↔BMS↔account untested | high / UNPROVEN | **node story** — the Layer-2 shakedown *is* the paper soak; the other four are runtime properties |
| Q7 | **QMX-F068** — frozen-money-face R at admission proven only on a function the door path is never shown to call (handoff assertion #8, PARTIAL) | high / UNPROVEN | **node story** — the node wires the door path, so the node proves it |
| Q8 | **QMX-F069** — refusal-register completeness unfalsifiable; storage-failure-blocks-dispatch proven by passing the failure *in*, with **no happens-before (journal-before-dispatch) observed** | medium / UNPROVEN | **node story** — ordering is a runtime property (`control_action.py:1150`) |
| Q9 | **QMX-D010** — 19 missed risk clauses; 107/107 passing against an empty findings file; the two cross-cutting gates (P0-9, R-009) mechanized as assertions that cannot fail | high / verification-debt | **node story** — re-mechanize the gates against a running node |
| Q10 | **QMX-D002 / QMX-F046** — CT-13 promotion event, signed-record immutability, treasury-boundary reserved kind untested | high / medium | **split** — immutability is foundation debt (qmf-registry); the promotion event and signer workflow are node stories |
| Q11 | **E12-F01 / E12-F04** — CT-33 registry record mint and graduation lineage-edge persistence are defined-unwired at the composition root; explicitly "host territory" | info-low / UNPROVEN | **node story** — this is the OR-06 relocation the node must complete (H7) |
| Q12 | **E12-F05** — the ungoverned plain-Python bot tunnel's non-gating claim is unproven in `qml`, "node/QMB territory" | low / UNPROVEN | **node story** |
| Q13 | **E15-F01** — exactly-one-ledger-line UNPROVEN for orchestrator teardown and governed-batch partial failure; reaped siblings can get zero lines | — / UNPROVEN | **node story** — a long-lived supervisor's teardown path is exactly this shape |
| Q14 | **E15-F02** — "12–14 concurrent runs" is not a validated budget; asserting a count would invent a performance claim | — / UNPROVEN | **node story** — AD-13 measure-then-budget on real node hardware |
| Q15 | **E15-F03** — no OS-enforced hard memory cap; the watchdog only observes and kills | — / UNPROVEN | **node story** — hardened confinement is the named deferred dependency of this sitting (`host/runner.py:10-13`) |
| Q16 | **E7 R28 + R24/R25 numeric half** — light/heavy enforcement lives at the composition root, out of the indicators package | — / UNPROVEN | **node story** — the node must keep heavy configs off the trading path (`budget.py:210-215`) |
| Q17 | **E9-F04** — no concrete benchmark budget numbers exist anywhere (measure-then-budget); only the negatives are proven. `qmf-venue` and `qmf-risk` `_bench.py` are deliberate placeholders | low / UNPROVEN | **node story** — the node's hot path is exactly these two packages |
| Q18 | **E5-F04..F08 / QMX-F102** — node/ops numeric targets, crypto strength, object-key layout, schedule execution, rehearsal cadence, RPO/RTO/retention, key custody — all blocked-spec UNPROVEN rows deferred by DEC-0118 | low / UNPROVEN | **node story** — assigned to this sitting by name |
| Q19 | **QMX-F085** — verify/gap-check never exercised over the rooms; the licence gate is an oracle-from-implementation and the four-state licence taxonomy is never pinned | medium / UNPROVEN | **foundation debt** — but the node inherits it the moment live venue data needs its own licence decision |
| Q20 | **QMX-F053 / F054 / F055** — TZPATH never observed; `get_provider`/`register_forex_17ny` not-ready branches on an unverified tzdb never executed; Swap-Wednesday not modeled (V1 swap-free) | medium / medium / low | **split** — foundation debt today, but TZPATH-never-observed becomes a node story the moment the node runs on a Linux VPS with a system tzdb (red flag R4) |
| Q21 | **QMX-F056 / F057** — backup boundary refusal-category set silently shrunk; int64-ns-verbatim through a later calendar identity never round-tripped | medium | **foundation debt** |
| Q22 | **QMX-F030 / FC-30** — the "same seed reproduces the same draw" half stays UNPROVEN by design because no stochastic model exists; OR-11 says do not build one now | medium | **foundation debt (deferred by ruling to GAP-0048)** |
| Q23 | **QMX-F107** — the download path keeps its own small dedup ledger file (a second data layer); the one deliberately-red QA test | low / UNPROVEN | **foundation debt** |
| Q24 | **E11-F04/F05/F06** — CT-22 format-2 "nothing more" is non-falsifiable; CT-23 `advisory_stop_proposal` field-carrying and the intent half of back-compat need Epic-10 door fixtures | low | **foundation debt** — but cheap for the node to close once it drives the real door |
| Q25 | **E4-F01/F02, E6-F04/F05, E9-F02/F03/F05/F06** — scope-narrowed rows: session-length witness, tzdata SemVer bump, retain-forever ownership, raw-archive path safety, isolated per-package import gate, SemVer lockstep, governed-evidence persistence, CT-08 gate deferred to GAP-0016 | low | **foundation debt** |

**Two more that are not findings but behave like debt:** the handoff scoreboard is 0 PROVEN · 4
PARTIAL · 1 UNPROVEN · 10 FAILED (`proof_map.md:47`) — the 10 FAILED were fixed in Fix Round 1,
but the assertions were re-mechanized, not re-earned from a running system; and
`CLAUDE.md` on `integration` is an older copy that still bans every `bmad-testarch-*` skill, which
the working tree re-allows (dossier §3.4).

---

# 5. RED FLAGS — what in the code will fight a live runtime

**R1 — Everything is synchronous, and asynchrony is banned below the node line.** There is not one
`async def` or `await` in the entire product tree. Worse, the ban is *enforced by conformance
tests*: `packages/qmf-data/tests/test_cycle.py:225` and `qml/src/qml/conformance/scan.py:72-73`
assert that `asyncio`, `threading`, `sched`, `multiprocessing`, `concurrent`, and `crontab` are
absent. The node's driver must sit strictly above the library boundary, or those tests go red the
day it lands. Design the seam deliberately; do not discover it.

**R2 — The run loop is pull-over-a-materialized-tuple, which is the exact opposite of a live
feed.** `run()` refuses anything that is not a `Sequence` and materializes a tuple up front
(`qmb/src/qmb/runloop/loop.py:1530-1550`), then iterates it (`:877`). Bars derive from an
**immutable, fingerprinted** `UnderlyingSeries.samples: tuple[SeriesSample, ...]`
(`qmb/src/qmb/runloop/bars.py:324`). You cannot append a live tick to a fingerprinted tuple. The
escape hatch is real and good — `run_slice` (`loop.py:687`) is a pure single-slice function that
threads `current_frontier` and `resting` in and out — but the node must build the accumulator and
the driver around it, and must preserve the six pinned sub-phase order (`loop.py:112-119`) because
changing it is identity-bearing.

**R3 — Two packages *refuse at runtime* to be given a schedule.** `own_schedule()` and
`start_daemon()` in `packages/qmf-data/src/qmf/data/cycle.py:307-315` always return typed refusals,
and `ingest.py:31` makes owning "a scheduler, daemon, process supervisor, or retry loop" a policy
rejection. A node design that puts the loop inside the data layer fails in production, not in code
review. The scheduler must be node-side and must *call in*.

**R4 — Process-global mutation at import time.** `force_tzpath`
(`extensions/qmf-calendar-forex/src/qmf/calendar_forex/_tzdb.py:38-49`) sets
`os.environ["TZPATH"]` and calls `reset_tzpath((path,))` for the whole process, forced at package
import. In a short-lived CLI run that is harmless. In a long-lived node hosting many seats, it is a
global side effect that any later `zoneinfo` consumer inherits — and QMX-F054 records that this
path is **never observed in any test**. Prove it once on the Linux VPS before trusting it.

**R5 — Windows-only assumptions on a Linux target.** `recorder/status.py:183` shells `schtasks`,
and the calendar recorder is scheduled today as the Windows Scheduled Task
`QMX-Calendar-Recorder` (06:00 + 18:00, `recorder/README.md:15`) — that scheduling has **no POSIX
path** and must be re-homed. `qmb/src/qmb/orchestrator/watch.py:274-275` uses
`ctypes.WinDLL("kernel32"/"psapi")`, though it does have a `/proc`-based POSIX branch (`:111`,
`:366`). The recorder also derives its BASE_DIR from `__file__` (`recorder/fetch_calendar.py:48`,
`status.py:18`) and reads `datetime.now` directly (`:59`, `:120`) — acceptable for a standalone
stdlib tool, but it means the recorder is not injectable the way the platform store is.

**R6 — The node's actual OS is the least-exercised one.** CI is 100% `ubuntu-latest`
(`.github/workflows/skylos.yml:36`; `battery.yml:35,57,85`), yet the type gate is pinned to render
the **Windows** platform view (`pyproject.toml:307-312`) and the Ubuntu clean-install smoke is
deferred until a remote exists (`:503-506`). So the node ships to Linux while the strict type gate
validates a Windows surface that Linux never runs. Add a lane.

**R7 — One float on the money path, right at the venue boundary.** `Price.from_float` at
`packages/qmf-venue/src/qmf/venue/ctrader.py:423` (inside `decode_execution_price`) is the sole
sanctioned crossing: cTrader execution prices, stops, targets, and conversion rates arrive as raw
doubles (DEC-0135). It is governed — declared `digits`, an identity-bearing rounding mode, NaN and
infinity refused, the raw double retained as provenance only and never the value a consumer reads
(`:365-437`). But it is still a float on the money path at the exact boundary where money enters,
and **the node chooses the rounding mode**, which is identity-bearing. A second declared crossing
lives at `packages/qmf-risk/src/qmf/risk/admission_bar.py:1022`/`:1039` (`_quantize_float` under a
declared `ComparisonRule`). Everything else refuses float (FM-1, e.g.
`packages/qmf-core/src/qmf/core/exact.py:411-419`).

**R8 — Nothing has a safe default; forgetting a number is a refusal, not a bad value.** Submission
deadline, reconciliation lookback, pacing cadence, `holdout_months`, RPO/RTO, governor budgets, the
KSA effect matrix, protection-window widths — all are do-not-default. That is the right design, but
it means the node cannot boot until a human has ruled roughly a dozen numbers, and the corpus values
are RECONFIRM-grade only. Budget a ruling pass, not a config file.

**R9 — `world = simulated` is reserved-unusable and every fill is taint-marked.** A read or write
under `world=simulated` is a policy rejection (`packages/qmf-data/src/qmf/data/rooms.py:14-16`;
`store/facade.py:74`), every fill carries an `optimistic` taint until GAP-0048
(`qmb/src/qmb/execution/ports.py:7`, `:95`), and asserting a simulated Instant as wall or replay is
refused (`qmb/src/qmb/runloop/frontier.py:196-204`). A paper-mode design that reaches for
`simulated` will be refused; paper must ride the demo account plus role-scoped namespaces.

**R10 — No shutdown contract exists.** No `signal.signal` anywhere in product code, no drain path,
no flush-then-exit. A supervised service that is restarted by the unit file has nothing to inherit,
and the interaction with block-on-unpersistable (a pending journal write retained, the sequence not
advanced) is undesigned.

**R11 — Two `_bench.py` placeholders sit exactly on the node's hot path.**
`packages/qmf-venue/src/qmf/venue/_bench.py:50` (explicitly "a deliberate placeholder", `:7`) and
`packages/qmf-risk/src/qmf/risk/_bench.py:50`. AD-13 says measure then budget; for the two packages
the order path runs through, nothing has been measured, so no latency budget the node states can be
anything but an invention (and GAP-0013 forbids invented numbers).

**R12 — The venue exposes no server clock.** `SERVER_CLOCK_AVAILABILITY: False`
(`packages/qmf-venue/src/qmf/venue/ctrader.py:1083`); recording a local receive instant is
mandatory (`:333-335`). Every ordering claim the node makes rests on its own clock, and no
clock-sync monitoring exists anywhere (G9). Skew is not detectable today.

**R13 — Stale documentation inside a package that is 9,180 lines complete.**
`packages/qmf-venue/README.md:10-13` still says "Scaffold (Story 1.1)… Public contracts arrive in
later stories". Trust the code and `src/qmf/venue/__init__.py:7-141`, not the README. Anyone
scoping node work from package READMEs will size this badly wrong.

**R14 — One un-recorded week of the news calendar is permanently lost evidence.** The FairEconomy
feed serves the **current week only**; `nextweek`/`lastweek`/`thismonth` all 404
(`recorder/fetch_calendar.py:29-31`). Combined with R5 (the scheduling is a Windows task with no
POSIX path) and G7 (the recorder is not wired to the adapter), a VPS migration gap costs evidence
that cannot be re-acquired.

**R15 — Kill-switch behaviour when the broker connection is down is nowhere designed.** Flagged in
the corpus itself (`tracker/map.md:79`, `:92`) as an unbounded failure cost. The parts bin has a
kill switch, a kill line, a flatten authority table, and standing intents that survive a
disconnect — but no ruling on what "flatten" means when there is no wire.
