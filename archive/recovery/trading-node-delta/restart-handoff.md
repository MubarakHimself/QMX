# Fresh-session handoff — deterministic Trading Node

## Mission

Re-document and then rebuild only the deterministic Trading Node. Start from the GitBook's stable conceptual skeleton, apply the later operator-ratified clarifications, and force explicit decisions where later BMAD proof detail conflicts with or outruns the wiki. Do not transplant the former repository's module graph.

## Hard scope

In scope:

- Book grammar, Books, bots only at their Book boundary, seven doors, registration, lifecycle, and sequencer;
- BMS, Treasury, Records, journals, reconciliation, news directives, and fail mechanisms;
- MIS-Live/SQS and only the archive/sync edge needed by Trading;
- KSA and the Adapter/Connection Manager enforcement edge;
- Trading SQLite authority, CT-SYNC boundary, monitoring, secrets, and Powers API;
- QML only as the bot-authoring/runtime surface ending at the Book.

Out of scope:

- agentic runtime/harness and WF1/WF2;
- Backtest, examination, and certification internals;
- recovered attic/DPR/slot machinery;
- redesigning Backend beyond the contracts Trading depends upon;
- GitHub archaeology or reuse of old code merely because a story was marked done.

## Starting architecture

1. Three deterministic nodes exist: one-process Trading Node, always-on Backend Node, UI-only Console.
2. The authority path is bot intent → Book gates/sequencer → Adapter execution. BMS accounting/constraints and KSA protection are authoritative side boundaries, not an inline allocation/execution hop; operator-only powers sit outside the automatic path.
3. MIS informs; KSA decides protection; Adapter enforces. Reporting and Console evidence never authorize.
4. One Trading SQLite WAL database owns Class 1/2. Records is sole physical writer of five append-only streams. State and required evidence commit atomically.
5. Backend is a read/evidence/archive sink, not a second writer. CT-SYNC is one-way data with verified ACK and control-only re-request.
6. Every live account binding has paired demo execution for paper/fail mechanisms, but the pinned live connection remains the sensing source.
7. All Book-affecting operations are sequenced; time, exact money, quantities, and serialization are deterministic.

## Apply these recovered changes first

1. Write the physical Trading Node boundary and direct in-process CT-call rule; GitBook never had this deployment boundary.
2. Write the four data classes, one-database rule, five Records streams, exact owner/writer distinction, and verify-before-purge CT-SYNC behavior.
3. Replace the old six-transition lifecycle with human promotion → `ADMITTED` → explicit activation/birth; restrict Trading paper to kill-line and breaker fail mechanisms.
4. Separate Book mode (`LIVE/PAPER`), bot-seat state (`LIVE/BENCHED`), supervision stand-down, and admission/activation state.
5. Add CT-BOOK-03: versioned JSON Schema, typed core fields, sparse inert attribute bag, hot-attribute promotion metadata, and no EAV.
6. Add unified Book/bot registration, click-time revalidation, paired-demo binding, and no silent feed failover.
7. Define Connection Manager inside Adapter as sole platform-session owner; keep platform constraints distinct from product defaults.
8. Define SQS as **Spread Quality Sensor**. Recover its spread-baseline/current-spread mechanism, keep MIS information-only and unreachable quality fail-closed, and reject the later “snapshot quality score” aggregate as SQS.
9. Put news import/compilation in BMS Exposure and retain MIS→KSA→Adapter protection authority.
10. Make Console read from Backend but execute powers only against Trading, with server-side precondition revalidation.

## Decisions to close before execution semantics are called build-ready

Close these in this order because the earlier choices affect the later contracts:

1. **MIS consumers:** direct CT-MIS-01 access for manifest-bounded bots/QML versus Book/KSA-only fanout plus a separate assembled bot-input surface.
2. **State machines:** exact admission→activation→birth order; Book mode vs seat vs supervision enums; what birth does to paper balance.
3. **Position safety:** stop-policy grammar, SL/TP computation owner, amendment/partial-close semantics, close priority, and PE-7 boundary fate.
4. **Adapter core:** command/request/result/fill schemas, idempotency, timeout/retry, startup gates, recovery, and `amend_order`.
5. **Protection:** KSA trigger→level→Adapter-effects matrix, initialization, persistence, concurrent trigger precedence, and de-escalation evidence.
6. **Money/reconciliation:** dimensionally explicit formulas, Kelly input, cross-currency equity, as-of Treasury evidence, freshness, open-position `unknown`, and resume authority.
7. **Persistence/sync:** AD-41 countersign, canonical serialization/hash, CT-SYNC auth/cadence/retention, global Book identity, and public atomic Records transaction seam.
8. **Operational contracts:** Powers catalog, failure taxonomy, notification ownership/delivery, metrics/thresholds, crash-loop limits, and preflight reachability.

## Candidate choices that need a new explicit ratification

Do not let these appear as invisible defaults simply because a completed story used them:

- file-sync JSONL + manifest for CT-SYNC and HTTP/JSON RPC for the three request/command crossings;
- concrete CT-SYNC envelope fields and message types;
- `book:{slug}` local identity;
- exact cTrader pool ceilings, retry count/backoff, label limit, message scaling, and heartbeat/rate numbers;
- DuckDB/pyarrow/custom-kernel stack and every excluded/allowed numerical library;
- the Spread Quality Sensor's exact baseline conditioning, score formula, hysteresis, thresholds, freshness, and identifier; do not reuse `snapshot_quality_score_v1` or its six-component weights as SQS;
- Story 5.8's expanded local CT-PAPER-01 fields;
- concrete failure-register seed enum and the “only `ratify_registry_value`” first Powers surface.

## Do not claim the former system completed these

The old sprint ledger left the four-command Adapter, `amend_order`, startup gates, canonical-feed capture/shadow readiness, kill-line detector, missed-rollover catch-up **implementation**, Reporting, BMS non-authority enforcement, monitoring endpoint, later Doors, KSA, QML, and promotion work unfinished. Missed-rollover catch-up/reconstruction semantics were ratified in AD-10; the driver was not built. Completed equity/fill/pool/paper/reconciliation proof slices are not an end-to-end trading path.

## Suggested documentation order

1. Scope and authority constitution.
2. Three-node context and one-process Trading runtime.
3. Domain/state model with separate modes and identities.
4. Persistence, Records, exact arithmetic, and ordering laws.
5. Component boundaries: Book, BMS/Treasury/Records, MIS/SQS, KSA, Adapter/CM.
6. Lifecycle, registration/promotion, paper, reconciliation, and position safety.
7. Contracts and refusal/evidence matrices.
8. Registry/formulas and explicit nulls.
9. Golden scenarios and failure/restart scenarios.
10. Implementation plan only after the reopened decisions are visible.

## Acceptance test for the new documentation

The restart documentation is ready to drive code only when a reader can answer, without consulting the old repository:

- who may decide, write, execute, and authorize each state transition;
- which process owns each mutable fact and how its evidence commits;
- how every command is ordered, retried or refused, and reconciled;
- how dead/stale/unknown market, broker, backend, and protection states fail;
- how admission, activation, live, paper, bench, stand-down, rollover, and resume differ;
- which values are ratified, measured, provisional, or still `null`;
- which later proof choices were accepted anew and which were replaced.

Use `trading-node-delta.md` as the detailed register and the three `work/` inventories for evidence. They are scouting material, not documents to copy wholesale.
