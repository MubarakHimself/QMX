# Code inventory — QML runtime, qmf-core, qmf-registry, analytics streaming halves

Read-only inventory for the trading-node architecture sitting. Scope: the QL-7 bot
runtime + conformance in `qml/`, the foundation vocabularies in `packages/qmf-core`,
the governed-record layer in `packages/qmf-registry`, and the streaming halves of
`packages/qmf-indicators` + `packages/qmf-structure`. Worktree root:
`C:/Users/Mubarak/Desktop/QMX-worktrees/node-inventory/`. All citations are
repo-relative to that root. Status vocabulary: **exists-as-is**,
**exists-needs-live-adapter**, **does-not-exist**.

Vocabulary note: the corpus itself uses the banned words ("engine", "plugins",
"minimal core") only inside quoted source; this dossier avoids them in its own prose.

## LOC and test-count census (target scope)

| Package / tree | src LOC | test LOC | test fns |
|---|---|---|---|
| `qml/src` | 11,447 | 6,264 (tests) | 252 |
| `qml/examples` | 3,418 | — | — |
| `packages/qmf-core/src` | 4,592 | 3,639 | 317 |
| `packages/qmf-registry/src` | 3,751 | 3,096 | 163 |
| `packages/qmf-indicators/src` | 7,302 | 5,318 | 265 |
| `packages/qmf-structure/src` | 5,004 | 3,847 | 218 |

Per-file src LOC of the load-bearing files cited: `qml/src/qml/protocol/factory.py`
588, `evidence.py` 758, `state.py` 399, `intents.py` 232, `contract.py` 71;
`qml/src/qml/conformance/layer2.py` 712, `prediction.py` 528, `registration.py` 462,
`layer1.py` 761, `scan.py` 366, `slice.py` 168, `harness.py` 196;
`packages/qmf-core/src/qmf/core/chrono.py` 1086, `exact.py` 1050, `fingerprint.py` 851,
`secret.py` 320, `refusal.py` 260, `sinks.py` 213;
`packages/qmf-registry/src/qmf/registry/records.py` 913, `promotion.py` 745,
`lineage.py` 679, `persistence.py` 1232; `qmf-indicators/streaming.py` 1186,
`budget.py` 232; `qmf-structure/lifecycle.py` 954.

---

## CAPABILITY TABLE

### QML — the QL-7 runtime protocol

| Capability | path:line | Status | What the node must add |
|---|---|---|---|
| Protocol contract (format-versioned, QML-owned `qml-ad5` ladder, not CT-numbered) | qml/src/qml/protocol/contract.py:25-35 | exists-as-is | Nothing; `PROTOCOL_FORMAT_VERSION=1`, `PROTOCOL_DENIAL_SET={clock,io,network,undeclared_randomness}`. |
| Factory → callback object (host constructs with declaration+assignment+read surfaces) | qml/src/qml/protocol/factory.py:212 (`construct_bot`), :473 (`HostedBot`), :558 (`FunctionFactory`) | exists-as-is | Node is the host: builds the factory input and drives the returned callback. No Book/clock/venue injected (factory.py:394-399, :385-390). |
| Evidence delivery per evaluation instant | qml/src/qml/protocol/factory.py:493 (`HostedBot.on_instant`); qml/src/qml/protocol/evidence.py:611 (`collect_evidence`), :338 (`FootprintEvidence`) | exists-needs-live-adapter | Node must supply live `ReadSurface` objects implementing `.at(instant)` (evidence.py:699-712) drawn from qmf-data/indicators/structure; the protocol only consumes injected surfaces. Look-ahead is refused (evidence.py:436-444). |
| Intents out (zero-or-more CT-23 entry/exit; sizing + venue commands refused) | qml/src/qml/protocol/intents.py:76 (`accept_intents`), :168-191 (reject requested_r / venue / book-side) | exists-as-is | Node routes accepted `BotIntent = EntryIntent|ExitIntent` (intents.py:35) into Book/BMS; requested_r stays Book-resolved. |
| Bounded state + snapshot/restore contract | qml/src/qml/protocol/state.py:122 (`BotStateScope` four-tuple), :272 (`BotStateSnapshot`), :362 (`capture_bot_state`), :75 (`assert_declared_state_bound`), :253 (`refuse_scope_mismatch`) | exists-needs-live-adapter | Node injects the scope tuple `(os, logic_identity, protocol_format_version, arithmetic_reference_build)` — "the OS is never read ambiently" (state.py:123-124, factory.py:519-526). Cross-tuple restore = `unavailable dependency` (state.py:260-269). |
| Example conformant bot (factory + callback reference) | qml/examples/conformant_bot/bot.py:1-11 | exists-as-is | Reference only; uses `qmf.risk.door.EntryIntent` + `qmf.risk.paper.ExecutionTarget`. |

### QML — conformance runner split

| Capability | path:line | Status | What the node must add |
|---|---|---|---|
| Pure verdict fn vs host-owned process spawning | qml/src/qml/conformance/layer2.py:1-6 (docstring), :200 (`evaluate_layer2` PURE), :271 (`collect_layer2_observations`), :430 (`run_layer2_suite`) | exists-needs-live-adapter | QML "owns the pure format-versioned surface. Hosts own only process spawning and isolation and feed results back" (layer2.py:2-4); collector "Spawns no process; hosts may isolate this" (:280). Node builds the sandbox/subprocess isolation and feeds `Layer2Observations` to `evaluate_layer2`. |
| Static AST/import scan (no file/process/thread) | qml/src/qml/conformance/scan.py:200 (`scan_logic_source`), :36-139 (`DENIED_IMPORTS`/`DENIED_CALL_SUFFIXES`) | exists-as-is | Node supplies the in-memory source tree; "never opens a file, never spawns a process, never starts a thread" (scan.py:5-6). |
| Determinism harness (golden slice, pure) | qml/src/qml/conformance/harness.py:81 (`drive_golden_slice`); qml/src/qml/conformance/slice.py:70 (`generate_golden_slice`) | exists-as-is | Deterministic golden slice keyed off footprint fp1; node reuses it or its own trace shape. |
| Prediction linter (a–d checks) | qml/src/qml/conformance/prediction.py:174 (`lint_prediction`), :364/:447/:467/:482 (checks a–d), :504 (blank-blocks-live) | exists-needs-live-adapter | Four pinned checks (contract.py:43-48): footprint_satisfies_requirements, exit_intent_subset, family_resolves_exit_policy, stream_set_within_venue_capabilities. Reads CT-18 through a host-built `PredictionBindingContext` (prediction.py:79-95); QML never imports qmf-venue. Node assembles the binding projection at seat time from the Book's CT-22 exit_policy/footprint_requirements + venue CT-18 tokens. |

### QML — registration gating & seat machinery

| Capability | path:line | Status | What the node must add |
|---|---|---|---|
| Registration gate (both layers or no mint; pure) | qml/src/qml/conformance/registration.py:214 (`gate_registration`), :190 (`evaluate_ticket`), :326 (`graduate_to_governed`) | exists-as-is | Returns `RegistrationCandidate` = fingerprintable content + pass verdict, **never a stamped record** (registration.py:6-8). |
| `register_bot_definition` / `install_bot_definition_kind` (QA F005 fix, OR-06) | qml/src/qml/declaration/bot.py:628-635 (`bot_definition_kind_contract`, "defined-unwired"); confirmed **not defined in `qml/src`** (grep) | does-not-exist (by design) | **FC-05/QMX-F005 PROVEN** (FIX-LEDGER.md:18) deleted both symbols under OR-06 (2026-08-27). The dated CT-06 Bot-kind mint is relocated to the host composition root — "Records reach qmf-registry only through a host composition root...to be built at the QMB composition root" (bot.py:632-635). Node/QMB composition root must build the mint wiring (holds `WriterId`, stamps CT-06 via `Registrar`). |
| Seat / roster / binding-to-Book runtime | qml/src/qml/conformance/registration.py:108-113 (`CitationKind.SEAT`, citation only), :268 (`cite_registered_bot`); qml/src/qml/declaration/versioning.py:35 ("seats cite a Bot fp1"); `PredictionBindingContext` prediction.py:79 | does-not-exist | Only **declaration/citation types** exist — a seat is a citation of a Bot fp1, not a runtime binding. No seat/roster/binding-to-Book runtime, and **no AD-41 active\|benched seat record** anywhere in `qml/src` or the registry (grep: none). Node must build the seat/roster/binding-to-Book runtime and the active\|benched seat state. |

### qmf-core — time / money / secrets / refusals / identity

| Capability | path:line | Status | What the node must add |
|---|---|---|---|
| Clock seam (injected Protocol) + DataDrivenClock | packages/qmf-core/src/qmf/core/chrono.py:711 (`Clock` Protocol), :739 (`DataDrivenClock`) | exists-needs-live-adapter | There is **no concrete WallClock class** — only the `Clock` `typing.Protocol` and the replay `DataDrivenClock`. Node's composition root injects a real wall clock satisfying the protocol; "nothing below the root reads the system clock" (chrono.py:28-29, 713-726). |
| Instant (int64 UTC-ns), Duration, Interval | chrono.py:230 (`Instant`), :323 (`Duration`), :394 (`Interval`) | exists-as-is | Checked arithmetic, overflow refused never wrapped (FM-2). |
| Calendar-identity-in-TradingDate | chrono.py:502 (`CalendarIdentity`), :558 (`TradingDate`), :1053 (`verify_tzdb_pin`) | exists-as-is | qmf-core embeds no rule set; the forex calendar extension (off-roster) supplies rules and drives `verify_tzdb_pin`. |
| Wall vs monotonic separation; WriterId/WriterSequencer/OrderingKey | chrono.py:641 (`MonotonicReading`), :807 (`WriterId`), :902 (`WriterSequencer`), :858 (`OrderingKey`) | exists-as-is | Node mints `WriterId` per (machine, role, stream) + boot epoch. |
| Exact money (scaled ints) + money-path taint | packages/qmf-core/src/qmf/core/exact.py:385 (`Money`), :495 (`Price`), :782 (`Quantity`), :616 (`PriceDelta`), :877 (`ExactRational`); float refusal FM-1 e.g. :411-419; `from_float` named boundary :432 | exists-as-is | Node uses these on every order/PnL path; float re-enters only through `from_float` with explicit rounding. |
| SecretRef / SecretValue / SecretStore (opacity validation) | packages/qmf-core/src/qmf/core/secret.py:149 (`SecretRef`), :122 (`_opaque_minted_token`), :179 (`SecretValue`, reveal-only :241), :291 (`SecretStore` Protocol) | exists-needs-live-adapter | **Opacity fix LANDED** — FC-19/QMX-F109 PROVEN (FIX-LEDGER.md:32): `SecretRef.try_create` admits only opaque minted namespaces, refuses venue/broker/account/env/key markers without echoing. (Task called this "E8-F01"; ledger card is QMX-F109, Epic-8.) Node injects a real `SecretStore` (read + atomic_replace store-before-discard) and the venue connection manager that is its sole holder. |
| Typed refusals (categories + retryability) | packages/qmf-core/src/qmf/core/refusal.py:50-64 (`RefusalCategory`), :66-72 (`Retryability`), :125 (`TypedRefusal`) | exists-as-is | **SEVEN categories, not six**: invalid input, unsupported capability, unavailable dependency, stale evidence, policy rejection, transient venue failure, storage failure. Retryability = yes\|no\|after-condition. Categories addable-never-redefined. (Contradiction with the brief's "six" — see below.) |
| fp1 fingerprint (single impl) + canonical serialization + F019 dup fix | packages/qmf-core/src/qmf/core/fingerprint.py:288 (`canonical_bytes`), :394 (`fingerprint`), :383 (`fingerprint_bytes`) | exists-as-is | **F019 duplicate fix LANDED** — FC-15/QMX-F019 PROVEN (FIX-LEDGER.md:28) added the public `fingerprint_bytes` route and removed every qmf-data SHA-256/fp1 duplicate; fingerprint.py is the single fp1 impl "and nowhere else" (fingerprint.py:6-8). qml never hashes (state.py:7). |
| CONTRACT_FORMAT_VERSION stamps | chrono.py:91, exact.py:88, fingerprint.py:108, refusal.py (n/a), records.py:97, lineage.py:101 | exists-as-is | Every serialized contract stamps `=1`; FC-22/QMX-F026 stamped the five CT-03 identity artifacts (FIX-LEDGER.md:37). Package SemVer never enters identity (two-ladder discipline). |
| AD-14 loud-failure / traceable-behaviour signals (structured event/log/metrics helpers) | packages/qmf-core/src/qmf/core/sinks.py:150 (`unpersistable`), :205 (`is_unpersistable`), :81 (`SinkAck`); `StreamingHealth` at qmf-indicators/streaming.py:320 | does-not-exist (as an emitter) | qmf-core has **no structured event / log / metrics emission helper and no metrics hooks**. Loud failure is delivered via `TypedRefusal` (returned never raised) + block-on-unpersistable (`storage failure` refusal → block command stream). The only AD-14 "health" type is `StreamingHealth` (renderable as metric/log, no secret). Node must build the structured event bus, log emission, and metrics surface (an AD-14 traceable-behaviour layer). |
| Config/settings schema helpers with 'ui-editable' flags (AD-30) + generic configurable-variable registry | **absent in qmf-core**; nearest is qml/src/qml/declaration/parameters.py:69 (`UiFlag` UI_EDITABLE\|UNEDITABLE), :96 (`parse_ui_flag`), :225 (`ui: UiFlag` on ParameterSpec) | does-not-exist | qmf-core has **no config/settings schema and no generic configurable-variable registry**. The only ui-editable flag machinery is qml's `UiFlag` — per bot-parameter, "exactly one ui-editable\|uneditable flag per declared variable" (parameters.py:6, :70; AD-30/DEC-0144). Templates are validated in qml's Layer-1 linter (layer1.py:386 `_template_identity_complete`) + footprint/template. Node's config surface (CLI/API/UI-later) must build its own generic ui-editable variable registry; it can mirror the `UiFlag` pattern but there is no reusable node-config registry today. |
| Injected persistence seams (RecordSink/JournalSink/ObservationSink) | packages/qmf-core/src/qmf/core/sinks.py:104/121/136 | exists-needs-live-adapter | `RecordSink` holds root-mints WriterId + per-(writer,kind) sequence (sinks.py:136-147). Node injects real sinks at the composition root; unpersistable = block. |

### qmf-registry — record kinds, promotion, lineage, sinks

| Capability | path:line | Status | What the node must add |
|---|---|---|---|
| Per-kind fingerprint-keyed registration records + RecordSink + WriterId + per-(writer,kind) sequence | packages/qmf-registry/src/qmf/registry/records.py:257 (`RegistrationRecord`, writer+sequence header :281-282), :540 (`FieldSetKind`), :657 (`KindRegistry`), :764 (`Registrar`, per-writer monotonicity :876); RecordSink at qmf-core/sinks.py:136 | exists-as-is (mechanism) | The generic mechanism exists (addable-never-redefined kinds, derived fp1 stable id, FM-6 idempotent/collision). |
| Book/BMS instance + binding records (concrete kinds) | **not shipped**; only the generic `FieldSetKind`/`KindRegistry` path (records.py:540, :657) | does-not-exist | No Book-instance, BMS-instance, or binding record kind ships in the registry. Node declares each as a `FieldSetKind` contract at the composition root and registers it in a `KindRegistry`. |
| Promotion record (human-signed; is-head / current pointer) | packages/qmf-registry/src/qmf/registry/promotion.py:210 (`PromotionCard`, plain_words_summary identity field), :508 (`authorize_live_promotion`), :390 (`correct_summary`), :643 (`PromotionEvent`) | exists-as-is | The **only path to live money** (promotion.py:2). "Current head" is **derived from the supersedes chain**, not a stored is-head field — `authorize_live_promotion` takes a required `superseded` state arg and refuses a superseded card (promotion.py:578-605); an AD-32 card additionally requires `in_force_template_fp1` (:606-636). Node must own head-tracking (supply supersession state) and the promotion workflow/UI/timing (explicitly platform territory, promotion.py:6-7). |
| Seat records (AD-41 active\|benched) | **absent** (grep: no `AD-41`/`benched` in registry) | does-not-exist | Node must declare a seat record kind and the active\|benched state model. |
| Lineage edges (CT-07 typed) | packages/qmf-registry/src/qmf/registry/lineage.py:104 (`EdgeType` closed set), :269 (`LineageEdge`), `EdgeLog` | exists-as-is | Includes `supersedes`, `promoted-from`, `branches-from` (AD-30 Book/BMS branching graph, "current is a separate dated pointer record", lineage.py:126-127), `continues-performance`, `carries-ledger`, `enacts`. The AD-30 dated current-pointer record for the branching graph is **not implemented** — node builds it. |
| Registry persistence (CT-09 through qmf-data, per-world room) | packages/qmf-registry/src/qmf/registry/__init__.py:31-44 (`RegistryPersistence`); persistence.py | exists-as-is | Content-addressed on fp1, per-world separation, cross-world/`simulated` = policy rejection. |

### qmf-indicators — streaming half

| Capability | path:line | Status | What the node must add |
|---|---|---|---|
| Streaming-mode instance + incremental update API (per tick/bar) | packages/qmf-indicators/src/qmf/indicators/streaming.py:685 (`StreamingIndicator`), :838 (`update()` → `StreamingSample`), :761 (`try_create`) | exists-as-is | The one named stateful class; single-feeder law (one `WriterId` holder, streaming.py:838-862); each `update()` recomputes through the identical `BatchKernel` so numbers are equal-to-batch by construction. Node drives `update()` per tick/bar on the live path and injects the feeder `WriterId` + `SnapshotScope`. |
| Snapshot / restore (restore-equivalence) | streaming.py:938 (`snapshot`), :969 (`restore`), :189 (`SnapshotScope` = OS + arithmetic-reference build), :462 (`StreamingSnapshot`) | exists-needs-live-adapter | Node injects the `(OS, arithmetic-reference build)` scope; cross-tuple restore = `unavailable dependency` (FM-7). |
| Light / heavy verdicts | packages/qmf-indicators/src/qmf/indicators/budget.py:55 (`LightHeavyVerdict`), :68 (`BudgetVerdict`), :103 (`evaluate_light_claim`), :210 (`guard_synchronous_entry`) | exists-as-is | Heavy by default until four bounds are declared + benchmark-proven; a heavy config's synchronous (live-path) entry returns `unsupported capability` — "heavy runs off the trading path, computed once and fanned out through the same contract" (budget.py:213-215). Node must run heavy configs off the trading path and place light configs on it. |
| AD-24 fan-out staleness stamps | **absent** (grep: no `AD-24`/`staleness`/`fan-out` in qmf-indicators src) | does-not-exist | The fan-out concept exists only as the heavy-off-path gate (`guard_synchronous_entry`); there are **no AD-24 staleness stamps** on fanned-out results. Node must build staleness stamping for fanned-out heavy evidence. |
| Warm-up horizon derivation | streaming.py:124 (`LEADING_UNDEFINED_MAPPING` → not_ready during warm-up); qml/src/qml/footprint/horizon.py:50 (`derive_horizon` → `Horizon(warm_up, embargo)`) | exists-as-is | Indicator warm-up = reference leading-undefined prefix → marked `not_ready` (never a number). Bot-side horizon is derived (never hand-declared) from the resolved producer chain (qml horizon.py:23-37, AD-21/AD-22). |
| AD-14 health (long-lived-state component) | streaming.py:320 (`StreamingHealth`), :918 (`health()`) | exists-as-is | Renderable as metric/log; carries no value data, no secret. Node surfaces this in its health/telemetry doors. |

### qmf-structure — streaming half

| Capability | path:line | Status | What the node must add |
|---|---|---|---|
| Streaming-mode / incremental update for structure | **no stateful streaming class**; the live model is AD-25 lifecycle: `StructureObject` minted once at observation + append-only records | does-not-exist (as a streaming class) | Structure is **not** a stateful per-tick streaming class. Node drives it by minting `ConfirmationRecord`/`InvalidationRecord`/`InteractionRecord` and folding at read time. |
| Read-time state fold (the node's per-instant driver) | packages/qmf-structure/src/qmf/structure/lifecycle.py:607 (`resolve_state` → :554 `ResolvedState`), :906 (`resolve_cascade`), :712 (`refit` supersedes) | exists-needs-live-adapter | "still valid at T" is a read-time fold, never a stored field (lifecycle.py:20-21). Node calls `resolve_state(obj, records, at=instant)` per evaluation instant and maps the result into a QL-7 `StructureFold` (evidence.py:242) with `knowable_at` (look-ahead-safe, lifecycle.py:663). |
| Light / heavy verdicts (structure) | **absent** in qmf-structure | does-not-exist | Structure ships no light/heavy budget gate; node governs structure cost separately. |
| AD-24 fan-out staleness stamps (structure) | **absent** | does-not-exist | As with indicators. |
| Warm-up / embargo horizon (structure) | packages/qmf-structure/src/qmf/structure/splits.py (`required_embargo_width`) | exists-as-is | Turns a family's confirmation-delay bound into a split embargo width; an unbounded family is excluded from split-governed evidence. |

---

## Verdict rollup by task target

- **QL-7 runtime protocol**: exists-as-is as a pure contract (factory → callback,
  evidence per instant, intents out, bounded state + snapshot/restore). The node's
  work is all **live adapters**: real `ReadSurface.at(instant)` producers, the injected
  scope tuple, and the intent → Book/BMS routing.
- **Conformance runner split**: pure verdicts exist (`evaluate_layer2`, `scan_logic_source`,
  `lint_prediction`); the node owns process spawning / sandbox isolation and feeds
  observations back (explicit host duty).
- **Prediction linter (a–d)**: exists-as-is; node assembles the `PredictionBindingContext`.
- **register_bot_definition gating**: F005/OR-06 removal PROVEN — the mint is
  defined-unwired; the node/QMB composition root must build the wiring.
- **Seat machinery**: only declaration + citation types; **no seat/roster/binding-to-Book
  runtime, no AD-41 active|benched record** — node builds it.
- **qmf-core**: time/money/secrets/fingerprint/serialization/refusals all exist-as-is;
  Clock and SecretStore need live-adapter injection (no concrete WallClock class);
  **no AD-14 event/log/metrics emitter and no config/settings ui-editable registry** —
  node builds both. Opacity (F109) and fp1-dedup (F019) fixes both LANDED.
- **qmf-registry**: the generic record mechanism + promotion + lineage + persistence
  exist-as-is; **Book/BMS-instance, binding, and seat record kinds are not shipped** —
  node declares them as `FieldSetKind` contracts and owns the current-head/is-head
  pointer for the AD-30 branching graph.
- **qmf-indicators streaming**: stateful streaming class + light/heavy + warm-up +
  AD-14 health exist-as-is; **AD-24 fan-out staleness stamps do not exist**.
- **qmf-structure streaming**: no streaming class — it is an AD-25 read-time fold
  (`resolve_state`) the node drives per instant into QL-7 `StructureFold` evidence.

## Contradictions / discrepancies for the adjudicators

1. **Refusal-category count.** The discovery brief says "six categories + retryability";
   the corpus defines **seven** — packages/qmf-core/src/qmf/core/refusal.py:50-64
   (invalid input, unsupported capability, unavailable dependency, stale evidence,
   policy rejection, transient venue failure, storage failure). The node's error
   surface must handle seven.
2. **SecretRef opacity fix card id.** The brief names it "QA E8-F01"; the FIX-LEDGER
   records the landed fix as FC-19 / QMX-F109 (FIX-LEDGER.md:32). Same fix, different id.

## Open items (brief expects; code lacks — node scope)

- AD-24 fan-out staleness stamps: not present in qmf-indicators or qmf-structure src
  (grep). Looked in `streaming.py`, `budget.py`, and every structure src module.
- AD-41 active|benched seat records: not present in qmf-registry or qml src (grep).
- Concrete production WallClock: only the `Clock` Protocol + `DataDrivenClock` exist
  (chrono.py:711, :739); the real wall clock is a composition-root injection.
- Generic node config / "configurable variable" registry with ui-editable flags: only
  qml's per-bot-parameter `UiFlag` exists (parameters.py:69); no reusable node-config
  registry — checked qmf-core (grep: no config/settings/editable).
- AD-14 structured event/log/metrics emitter: only `TypedRefusal` + block-on-unpersistable
  + `StreamingHealth`; no dedicated emitter or metrics hooks in qmf-core.
- Book/BMS-instance, binding, and seat record KINDS: only the generic `FieldSetKind`
  mechanism (records.py:540); no concrete kinds shipped.
