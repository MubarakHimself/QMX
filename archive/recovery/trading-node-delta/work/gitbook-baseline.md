# GitBook baseline — deterministic Trading Node

Scouting artifact for the Trading Node recovery comparison. Retrieved from the live QMX GitBook on 2026-08-15. This is an older semantic baseline, not a redesign, implementation plan, or statement that every reviewed contract is implementation-ready.

## Scope and evidence rules

- Included: the deterministic runtime described by GitBook as book-governed bots plus Book Template, Scalper Book, MIS-Live, MIS-Archive where it is directly relevant to MIS, BMS, Treasury, KSA, Paper Mode, Broker Adapter, Notification, Data Layer, QML shell, contracts, registries, runtime scenarios, and operational/safety lenses.
- Boundary only: the Examination Engine is treated as an external certificate/replay peer. Its battery, walk-forward behavior, cohort analysis, and certification internals are not catalogued.
- Excluded: the agentic R&D system, Backtest Engine behavior, WF1/WF2, desktop/UI, and prop-firm-book design. The published GitBook contains no Backtest Engine, WF1, or WF2 page; it explicitly excludes agentic R&D.
- Claims below are paraphrases unless a schema or formula is reproduced. A source citation names the page and the exact relevant heading.
- `Stable` means stated as a law, ratified decision, reviewed contract, or repeated invariant. It does **not** mean technically complete.
- `Gap` means GitBook itself marks the surface with `GAP-*` or explicitly says it remains open.
- `Tension` means two published pages do not line up cleanly, or an asserted behavior cannot be expressed by the published contract.

Primary navigation evidence: [QMX Documentation Index](https://elios-1.gitbook.io/qmx/qmx-documentation-index.md), headings `QMX Documentation Index`, `Components`, and `Machine-Readable Contracts`; [llms.txt](https://elios-1.gitbook.io/qmx/llms.txt).

### Evidence provenance and anti-duplication rule

- **This file is a live-GitBook baseline only.** Every substantive claim was read from `https://elios-1.gitbook.io/qmx` on 2026-08-15, primarily through GitBook's public `.md` representations and `llms.txt` index.
- GitBook's own latest visible [Changelog](https://elios-1.gitbook.io/qmx/changelog.md) entry is dated **2026-07-08**. That date describes the published documentation pass; it is not the retrieval date.
- The separate **immutable 2026-07-18 local capture was not used as evidence in this file**. It must be compared independently. Likewise, no local wiki, BMAD output, former-repository code, CI, or Git history was used here.
- Consequently, everything catalogued below is **already present in the older GitBook baseline** and must not be reported as a later local addition merely because it also appears in the 2026-07-18 capture or current wiki.
- A genuine recovery delta must pass a strict test: the local source adds a semantic claim, closes/changes a GitBook gap, resolves a listed tension, or removes/reverses a GitBook claim. Formatting changes, MkDocs conversion, renamed files/headings, copied contracts, or fuller prose that says the same thing are duplicates, not additions.
- If the live GitBook and the immutable capture differ, record that first as **baseline drift** with evidence from both snapshots. Do not silently pick whichever version is more convenient, and do not label the capture-only side a later project decision until its provenance supports that conclusion.

## 1. Baseline system identity and boundary

GitBook calls QMX “a deterministic trading architecture for book-governed bots.” It publishes a logical core rather than a single `COMP-TRADING-NODE` component. The runtime container contains Book Template, Scalper Book, MIS-Live, BMS, Treasury, KSA, Paper, Adapter, and Data; QML, MIS-Archive, and Examination are shown in a separate certification/research container. The KSA page is the only inspected page that explicitly uses the phrase “trading node,” saying the trading node enforces KSA effects through the adapter.

Evidence:

- [Overview](https://elios-1.gitbook.io/qmx/architecture/overview.md), headings `QMX Architecture Overview`, `System Context`, `Container View`, `Runtime Shape`, and `Scope Boundary`.
- [Dependency Graph](https://elios-1.gitbook.io/qmx/architecture/dependency-graph.md), heading `Dependency Graph`.
- [Kill-Switch Authority](https://elios-1.gitbook.io/qmx/components/kill-switch-authority.md), opening paragraph.

Logical runtime path as published:

1. A bot emits a trade intent.
2. A book runs its seven doors and sizing logic.
3. MIS-Live supplies a typed/versioned market snapshot used by the book.
4. Approved intent becomes a platform-blind adapter command.
5. KSA state constrains adapter effects.
6. The adapter translates to the broker.
7. BMS records refusals, fills/journals, modes, cycle events, news blocks, reconciliation, and reporting inputs.
8. Treasury owns the virtual capital ledger and book-to-treasury boundary.
9. Paper mode preserves counterfactual evidence without making paper gains into treasury cash.

The physical deployment boundary of the “Trading Node” is **not published**. There is no documented process topology, service protocol, message transport, host boundary, startup ordering, or ownership mapping that says which logical components run in one server versus separate services. This is the first comparison checkpoint for the local wiki.

## 2. Constitutional invariants

Source: [System Constitution](https://elios-1.gitbook.io/qmx/system-constitution.md), headings `Laws`, `Authority Hierarchy`, and `Precedence`; corroborated by [ADR-0001 Authority Hierarchy](https://elios-1.gitbook.io/qmx/decisions/adr-0001-authority-hierarchy.md), headings `Decision` and `Consequences`.

### Authority

- `Stable` — Bots trade; books control bots; BMS accounts for and constrains books; nothing above a bot touches the market.
- `Stable` — A bot owns market-facing entry/exit organs. The book owns admission, sizing, doors, leash, and profile selection. BMS owns accounting, constraints, journals, KSA policy, and reporting.
- `Stable` — MIS is information-only and may not size, block, or trade.
- `Stable` — Bots do not see broker platforms or KSA directly.
- `Stable` — Reporting computes from Records and has no authority.
- `Stable` — The operator’s runtime authority is limited to A1 resurrection and Sunday review; intraday human judgment is invalid.

### Risk, cycle, and protection

- `Stable` — Unclaimed or freed risk budget is never redistributed during a cycle.
- `Stable` — A cycle is seed-to-cap. Money resets between cycles; knowledge persists.
- `Stable` — Automatic KSA changes may escalate only. De-escalation requires A1 human authority.
- `Stable` — News-affected pairs are blocked for every live and paper book.
- `Stable` — Every refusal at every door/gate must sign the veto ledger.
- `Stable` — Graduated policy shrinks before blocking unless an event class requires immediate action.
- `Stable` — Paper mode is a frozen counterfactual diagnostic, not a cosmetic balance.
- `Stable` — Unexplained virtual-ledger versus broker drift is a technical kill.
- `Stable` — The leash handles damage; sunset review handles pointlessness.

### Documentation precedence

- `Stable` — Transcripts outrank concretizations when they disagree; proposals must remain visible as enhancements.
- `Limitation` — The full `DEC-*` ledger and `ENH-*` records are not published. [Decisions](https://elios-1.gitbook.io/qmx/decisions.md), heading `Decisions`, says the full ledger is an internal workshop artifact. Many public pages therefore cite decisions whose complete wording and rationale cannot be independently recovered from GitBook.

## 3. Book system baseline

### 3.1 Book Template

Source: [Book Template](https://elios-1.gitbook.io/qmx/components/book-template.md), headings `Authority Boundary`, `Interfaces`, `Behavior`, `Configuration`, and `Failure Modes`; [ADR-0002 Template and Instance Split](https://elios-1.gitbook.io/qmx/decisions/adr-0002-template-and-instance-split.md), headings `Decision` and `Consequences`.

- `Stable` — The reusable book grammar is separate from each book instance. The template carries common grammar; each book profile owns its values and capability selection.
- `Stable` — Global infrastructure remains fully specified after template Section 5. A profile can leave a capability dormant but does not delete it.
- `Stable` — Every charter fills: game played; money shape; customer plus headline metric; death condition.
- `Stable` — Seven admission doors run in order: footprint, viability veto, `R_max`, daily budget, breaker, exposure ledger, KSA.
- `Stable` — Leash escalation chain: ambient governor, day closure, bench-to-paper, chorus flag, kill-line stand-down, classed KSA, hold-time force-flat.
- `Stable` — The book never trades directly, may not redistribute unclaimed risk, and may not use session windows as authority.
- `Inputs` — `CT-BOOK-01` trade intent, `CT-EXAM-01` certificate, `CT-MIS-01` MIS snapshot.
- `Published output claim` — `CT-BOOK-02` book mode to BMS. This path conflicts with other pages; see T-03.
- `Gap` — `GAP-0001`: Section 6 workspace design.
- `Gap` — `GAP-0010`: BMS assignments for Book Sections 1–2.
- `Gap` — `GAP-0012`: certified leash-event/chorus frequency rules.

### 3.2 Scalper Book

Source: [Scalper Book](https://elios-1.gitbook.io/qmx/components/scalper-book.md), headings `Authority Boundary`, `Interfaces`, `Behavior`, `Configuration`, and `Failure Modes`.

- `Stable` — The first Book Template instance is a treasury-customered cash-flow machine, judged by swept cash per month per dollar of seed rather than headline equity curve.
- `Stable` — It applies the seven doors, offers risk seats, can bench bots to paper, and sweeps only at rollover.
- `Stable` — It compounds inside a cycle, not between cycles.
- `Stable` — Intraday cap contact does not cause an intraday sweep; rollover equity determines the sweep.
- `Stable` — Crossing the kill line moves the book to paper until cycle-boundary re-seed. Live restart from the remnant is forbidden.
- `Stable` — A MIS field not in the scalper profile manifest requires a profile/dormant-socket review.
- `Interfaces claimed` — MIS snapshot in; Treasury event out to Treasury; Paper transition out to Paper; Adapter command out to Adapter.
- `Gap` — The page refers to a “scalper MIS profile” and to an ENH-0008 dormant YELLOW/RED mapping, but neither full manifest nor mapping is published.
- `Gap` — Seat allocation, roster mutation, concurrent-bot arbitration, and exact daily-budget drain events are not specified beyond formulas and the `max_concurrent_live_bots` registry value.

### 3.3 Money ladder and sizing formulas

Sources: [Variables](https://elios-1.gitbook.io/qmx/registry/variables.md), heading `Variables`; [Formulas](https://elios-1.gitbook.io/qmx/registry/formulas.md), heading `Formulas`; [SCN-0001 Money Ladder](https://elios-1.gitbook.io/qmx/scenarios/scn-0001-money-ladder.md), headings `Given`, `When`, `Then`, and `Registry Recompute`.

Published scalper defaults:

| Key | Symbol | Value | Units / meaning | Ownership |
|---|---:|---:|---|---|
| `scalper_seed_capital` | S | 500 | USD | Scalper Book; configurable |
| `scalper_kill_line` | K | 200 | USD; fixed within cycle | Scalper Book; configurable |
| `scalper_cap_multiplier` | cap_multiple | 2.5 | ratio | Scalper Book; configurable |
| `scalper_runway_divisor` | n | 5 | count | Scalper Book; configurable |
| `scalper_breaker_threshold` | B | 2 | consecutive stop-outs | Scalper Book; configurable |
| `scalper_budget_shaping_factor` | b | 2 | ratio | Scalper Book; configurable |
| `scalper_mean_loss_r` | Lbar | measured per bot at exam | R | Measured, not configurable; 0.35R is only a reference expectation |
| `viability_cost_fraction_max` | v_cost | 0.10 | fraction of R | Book Template; configurable |
| `max_concurrent_live_bots` | N_live_max | 3 | bots | Scalper Book; configurable |

Published formulas:

| ID | Name | Expression | Stated semantics |
|---|---|---|---|
| FORM-0001 | cap equity | `C = cap_multiple * S` | Derived; checked at rollover only |
| FORM-0002 | runway | `U = E - K` | Current equity minus kill line |
| FORM-0003 | daily loss budget | `D = U / n` | Re-derived at rollover and drains intraday |
| FORM-0004 | offer per seat | `offer_R_usd = D / (B * b * Lbar)` | Book offer |
| FORM-0005 | take per seat | `take_R_usd = min(offer_R_usd, trust_bounded_cost_aware_kelly_R_usd)` | Bot/book validation responsibility |
| FORM-0006 | R-max ceiling | `R_max_usd <= B * b * Lbar` | Relationship-stated ceiling |
| FORM-0007 | viability floor | `round_trip_cost_R / expected_edge_R <= v_cost` | Cost-aware viability door |

Worked numbers in conversations are explicitly non-authoritative checksums. Scenario runners must re-read registry values and per-bot measured Lbar.

## 4. MIS and SQS baseline

### 4.1 MIS ownership

Source: [Market Intelligence Service](https://elios-1.gitbook.io/qmx/components/market-intelligence-service.md), headings `Authority Boundary`, `Interfaces`, `Behavior`, `Configuration`, and `Failure Modes`; [MLOps Data Pipeline](https://elios-1.gitbook.io/qmx/lenses/mlops-data-pipeline.md), headings `Pipeline` and `Gap`; [MLOps Model Lifecycle](https://elios-1.gitbook.io/qmx/lenses/mlops-model-lifecycle.md), headings `Lifecycle` and `Proposal Boundary`.

- `Stable` — MIS-Live computes and publishes typed hot snapshots. MIS-Archive stores immutable emissions for replay, committee analysis, and research.
- `Stable` — MIS computes a labeler/version/parameter-set/pair/resolution combination once, then fans it out to subscribers.
- `Stable` — MIS is sensing/information only. The book profile converts information into permission/refusal.
- `Stable` — Labeler version changes require re-certification; exam and live labeler versions must match.
- `Stable` — Model lifecycle: register version/parameters, replay through Archive, produce pinned certificates, publish Live only with parity, re-certify affected bots after version change.
- `Stable` — Failed labelers publish degraded fields and list sensors in `degraded_sensors`; dead feed prevents new entries.
- `Stable` — An unreachable SQS causes a hard door block.
- `Performance` — Tick-to-MIS publication ceiling 35 ms; end-to-end tick-to-order envelope 100 ms.
- `Gap` — Market-data provider, ingestion schema, clock/sequence guarantees, snapshot storage mechanics, replay response schema, and labeler inventory are not published.
- `Gap` — One full affected-book cycle is the ratified default for shadow rollout, but the referenced ENH-0005 detail is not published.

### 4.2 MIS-Live snapshot

Source: [CT-MIS-01 MIS-Live Snapshot](https://elios-1.gitbook.io/qmx/contracts/ct-mis-01-mis-live-snapshot.md), heading `CT-MIS-01 MIS-Live Snapshot`.

Required fields: `pair`, `resolution`, `snapshot_version`, `spread_state` (`normal|elevated|extreme`), `gap_event`, `liquidity_stress`, `feed_state` (`fresh|stale|dead`), `sqs_score`, `sqs_hard_block`, and `degraded_sensors`. Optional fields: `regime` (`trend|range|chaos`) and `regime_confidence`.

Rules: snapshot is information-only; dead feed prevents new entries through book-profile handling.

### 4.3 MIS-Archive replay query

Source: [CT-MIS-02 MIS-Archive Replay Query](https://elios-1.gitbook.io/qmx/contracts/ct-mis-02-mis-archive-replay-query.md), heading `CT-MIS-02 MIS-Archive Replay Query`.

Fields: `query_id`, `pair`, `start_utc`, `end_utc`, `labeler_versions`. Replay uses immutable archive emissions and is never in the hot path. The published contract gives a query envelope only; it has no response schema, pagination, ordering, snapshot payload reference, error model, or immutability verification mechanism.

### 4.4 SQS is referenced but not defined

The entire published GitBook was scanned for literal `SQS`. Its only prose occurrences are in the MIS component’s behavior and failure-mode rows. `CT-MIS-01` additionally exposes `sqs_score` and `sqs_hard_block`. GitBook does **not** publish:

- what SQS stands for;
- whether it is a service, sensor, labeler, or MIS-internal module;
- its owning component or dependency;
- score range, units, calibration, threshold, or hard-block derivation;
- request/response contract;
- timeout/health rule that constitutes “unreachable”;
- whether `sqs_hard_block` is emitted by SQS or derived by MIS.

This is a high-priority recovery delta target because SQS is safety-critical in GitBook but semantically absent.

## 5. BMS baseline

Source: [Book Management System](https://elios-1.gitbook.io/qmx/components/book-management-system.md), headings `Authority Boundary`, `Interfaces`, `Behavior`, `Configuration`, and `Failure Modes`; [Logging Spec](https://elios-1.gitbook.io/qmx/lenses/logging-spec.md), headings `Required Journals` and `Gaps`.

- `Stable` — BMS accounts for and constrains books; it never trades, sizes, mutates bot logic, reaches inside a book, overwrites journals, or bypasses the veto ledger.
- `Stable` — Four desks: Treasury, Exposure, Records, Reporting.
- `Stable` — BMS owns virtual ledger state, exposure measurement, mode registry, append-only journals, reporting metrics, KSA policy, and news directives.
- `Stable` — Records is append-only and owns the only journal-write path. Corrections append a new entry referencing the corrected entry.
- `Stable` — Reporting reads Records and has zero authority.
- `Stable` — BMS’s mode registry is described as the authoritative mode map.
- `Stable` — Every refusal must produce a journal append/veto-ledger record.
- `Stable` — Exposure can emit news-block directives in the published golden scenario.
- `Interfaces` — Treasury event in, reconciliation report in, mode-registry read out to KSA, news directive out to KSA, journal append in from journal producers.
- `Gap` — `GAP-0008`: Exposure Desk v2 and cross-book cap authority.
- `Gap` — `GAP-0009`: observability substrate.
- `Gap` — `GAP-0010`: unresolved BMS assignments for Book Sections 1–2.

Required journals:

| Journal | Published owner | Required content |
|---|---|---|
| Veto ledger | BMS | door, reason, candidate intent, timestamp |
| KSA audit log | KSA / BMS | trigger class, evidence refs, state level |
| Trade journal | BMS | fill, snapshot version, book, bot, pair |
| Book journal | BMS | mode changes, leash events, cycle events |
| Correlation ledger | BMS | chorus observations and cohort references |

Contract summaries:

- [CT-BMS-01 Treasury Event](https://elios-1.gitbook.io/qmx/contracts/ct-bms-01-treasury-event.md): `event_id`, `book_id`, `cycle_id`, `event_type` (`sweep|refund|re_seed`), USD `amount`, `reason`, `occurred_at_utc`. Only these three types may cross the boundary.
- [CT-BMS-02 Mode Registry Read](https://elios-1.gitbook.io/qmx/contracts/ct-bms-02-mode-registry-read.md): `book_id`, `mode` (`LIVE|PAPER|BENCHED|STOOD_DOWN`), `updated_at_utc`; declares BMS mode map authoritative.
- [CT-BMS-03 Reconciliation Report](https://elios-1.gitbook.io/qmx/contracts/ct-bms-03-reconciliation-report.md): `account_id`, `virtual_equity`, `broker_equity`, `explained_delta`, `verdict` (`reconciled|drift|unknown`); unexplained drift is a technical kill.
- [CT-BMS-04 News Block Directive](https://elios-1.gitbook.io/qmx/contracts/ct-bms-04-news-block-directive.md): `directive_id`, `affected_currency`, `affected_pairs`, start/end UTC, `reason`; applies to live and paper.
- [CT-BMS-05 Journal Append](https://elios-1.gitbook.io/qmx/contracts/ct-bms-05-journal-append.md): `journal`, `event_id`, `event_type`, free-form `payload`, `refs`, `occurred_at_utc`; corrections append references.

## 6. Treasury and cycle accounting baseline

Source: [Treasury Desk](https://elios-1.gitbook.io/qmx/components/treasury-desk.md), headings `Authority Boundary`, `Interfaces`, `Behavior`, `Configuration`, and `Failure Modes`; [SCN-0002 Rollover Sweep](https://elios-1.gitbook.io/qmx/scenarios/scn-0002-rollover-sweep.md), headings `Given`, `When`, `Then`, and `Worked Numbers`.

- `Stable` — Treasury owns the virtual capital ledger and book-to-treasury boundary.
- `Stable` — Only sweep, refund, and re-seed cross that boundary.
- `Stable` — Ledger state includes seed, equity, kill line, cap, cycle id/state, boundary events, and reconciliation verdicts.
- `Stable` — Cap is checked at rollover. Intraday cap contact does not re-anchor the book.
- `Stable` — At a valid sweep, Treasury records equity minus seed and resets virtual equity to seed; knowledge state persists.
- `Stable` — Physical broker withdrawal is not automatic.
- `Stable` — Mid-cycle top-up and live restart from kill-line remnant are forbidden.
- `Stable` — Unexplained broker/ledger drift halts trading.
- `Configuration` — `reconciliation_epsilon` defaults to 0 USD and requires operator review before any non-zero use.
- `Gap` — `GAP-0007`: refund reserve `rho` and cycles-per-month estimator. Interim formula is `reserve_usd ~= rho * N_cycles_month * S`.
- `Gap` — Exact rollover definition, time zone, sweep idempotency, transaction ordering, physical-cash workflow, and refund/re-seed preconditions are not published.

## 7. Paper-mode baseline

Source: [Paper Mode System](https://elios-1.gitbook.io/qmx/components/paper-mode-system.md), headings `Authority Boundary`, `Interfaces`, `Behavior`, `Configuration`, and `Failure Modes`; [CT-PAPER-01 Paper Mode Transition](https://elios-1.gitbook.io/qmx/contracts/ct-paper-01-paper-mode-transition.md), heading `CT-PAPER-01 Paper Mode Transition`.

- `Stable` — Paper mode freezes the counterfactual balance at transition and preserves sensing/paper execution evidence.
- `Stable` — Paper balance cannot be hand-adjusted and paper gains are not treasury cash.
- `Stable` — After the configured count of consecutive stop-outs, the affected bot moves to paper for the rest of the day and automatically resets at next open.
- `Stable` — Live restart from a kill-line remnant is forbidden.
- `Contract` — `CT-PAPER-01` has `book_id`, optional `bot_id`, `from_mode`, `to_mode`, `frozen_balance`, and `trigger_event_id`.
- `Gap` — `GAP-0006`: complete transition state machine. Only the breaker auto-reset path is ratified. Kill-line stand-down, discretionary promotion, freeze/demotion, and other return-to-live semantics are open.
- `Gap` — “rest of the day” and “next open” are not defined in terms of book calendar, rollover clock, market session, or time zone.

## 8. KSA and safety baseline

Source: [Kill-Switch Authority](https://elios-1.gitbook.io/qmx/components/kill-switch-authority.md), headings `Authority Boundary`, `Interfaces`, `Behavior`, `Configuration`, and `Failure Modes`; [CT-KSA-01 Kill-Switch State Event](https://elios-1.gitbook.io/qmx/contracts/ct-ksa-01-kill-switch-state-event.md), heading `CT-KSA-01 Kill-Switch State Event`; [SCN-0003 News Block](https://elios-1.gitbook.io/qmx/scenarios/scn-0003-news-block.md), headings `Given`, `When`, and `Then`.

- `Stable` — KSA is a global protection state machine; BMS owns policy; adapter enforces effects; bots never interpret KSA.
- `Stable` — Levels: `GREEN`, `YELLOW`, `ORANGE`, `RED`, `BLACK`.
- `Stable` — Trigger classes: `scheduled_news`, `black_swan`, `connectivity`, `unknown_state`.
- `Stable` — Automated changes escalate only; A1 is required for de-escalation.
- `Stable` — Unknown startup state blocks broker execution until reconciled.
- `Stable` — Scheduled-news directives block affected pairs in both live and paper, and refusals sign the veto ledger.
- `Stable` — The old `TIGHTEN`/half-size-through-bad-conditions state is forbidden.
- `Contract` — KSA event contains event id, level, trigger class, affected pairs, evidence refs, and effective UTC time.
- `Gap` — `GAP-0015`: full trigger-to-target-level matrix, especially connectivity and unknown state. The docs say “halt/block” but do not publish which KSA level or exact adapter effects implement it.
- `Gap` — ENH-0008 allegedly ratifies a scalper-specific dormant YELLOW/RED mapping, but that mapping is not visible in any published page.
- `Gap` — Black-swan detection, connectivity thresholds, scheduled-news source/mapping, evidence schema, state persistence/recovery, and concurrent-trigger precedence are not specified.

## 9. Broker Adapter baseline

Source: [Broker Adapter](https://elios-1.gitbook.io/qmx/components/broker-adapter.md), headings `Authority Boundary`, `Interfaces`, `Behavior`, `Configuration`, and `Failure Modes`; [CT-ADAPTER-01 Broker Adapter Command](https://elios-1.gitbook.io/qmx/contracts/ct-adapter-01-broker-adapter-command.md), heading `CT-ADAPTER-01 Broker Adapter Command`; [Security Model](https://elios-1.gitbook.io/qmx/lenses/security-model.md), headings `Trust Boundaries` and `Secret Handling Gap`.

- `Stable` — Adapter is the broker-facing boundary and translates platform-blind commands to broker-specific execution.
- `Stable` — It maintains account binding, enforces adapter fail-safes, exposes unknown state, and may not decide permission or hide drift.
- `Stable` — Commands: `place_order`, `cancel_order`, `close_position`, `close_all`, with `command_id`, `account_binding`, and free-form `payload`.
- `Stable` — Unknown broker state blocks execution until reconciliation and emits the `unknown_state` trigger class.
- `Performance` — Expected order-path range is 10–45 ms; only the upper bound is configurable.
- `Gap` — `GAP-0005`: broker/cTrader feasibility, credentials, account binding, and secret assumptions.
- `Gap` — Command payload schemas, validation, acknowledgement/fill/reject events, idempotency, retries, timeouts, partial fills, broker order mapping, position ownership, and reconnect/recovery are not published.
- `Gap` — Adapter is shown as depending on QML, but QML’s usable interfaces are `GAP-0013`.

## 10. Notification baseline

Source: [Notification System](https://elios-1.gitbook.io/qmx/components/notification-system.md), headings `Authority Boundary`, `Interfaces`, `Behavior`, `Configuration`, and `Failure Modes`; [CT-NOTIFY-01 Notification Candidate](https://elios-1.gitbook.io/qmx/contracts/ct-notify-01-notification-candidate.md), heading `CT-NOTIFY-01 Notification Candidate`; [Metrics and Alerts](https://elios-1.gitbook.io/qmx/lenses/metrics-and-alerts.md), headings `Metrics` and `Alerts`.

- `Stable` — Notifications derive from BMS Records journals and cannot create intraday human judgment loops or override protection.
- `Stable` — Notification may read events, propose severity, deduplicate, and deliver only after rules are ratified.
- `Interim` — Tiers `P1|P2|P3|P4` are ratified as interim defaults under ENH-0001.
- `Contract` — Candidate includes `event_id`, `source_journal`, required `proposed_tier`, `message`, and optional `delivery_policy_ref`.
- `Gap` — `GAP-0002`: final severity, channels, retries, dedupe, quiet hours, credentials, and paper-book digest policy.
- `Gap` — The actual ENH-0001 tier definitions are not published, so the enum exists without semantics.

## 11. Data, journaling, and observability baseline

Source: [Data Layer](https://elios-1.gitbook.io/qmx/components/data-layer.md), headings `Authority Boundary`, `Interfaces`, `Behavior`, and `Failure Modes`; [Data Layer Lens](https://elios-1.gitbook.io/qmx/lenses/data-layer-lens.md), headings `Data Layer Lens` and `Open Design`; [CT-DATA-01 Data Ownership Register](https://elios-1.gitbook.io/qmx/contracts/ct-data-01-data-ownership-register.md), heading `CT-DATA-01 Data Ownership Register`.

- `Stable island 1` — MIS archive emissions are immutable.
- `Stable island 2` — BMS journals are append-only; corrections append references rather than mutate.
- `Contract shell` — Data ownership record contains `dataset_id`, `owner_component`, `write_policy`, optional `retention_policy`, optional `schema_ref`.
- `Gap` — `GAP-0003`: authoritative ownership table, store list, retention, backup/restore, migrations, and schema boundaries.
- `Gap` — `GAP-0009`: observability substrate.
- `Gap` — No actual populated `CT-DATA-01` ownership records are published for the two stable islands.

Operational metrics named in GitBook: tick-to-MIS latency, order latency, end-to-end latency, veto count by door, sweep amount by cycle. [Performance Budgets](https://elios-1.gitbook.io/qmx/lenses/performance-budgets.md), headings `Budgets` and `Measurement Rule`, requires structured timestamps per hop and snapshot version when market state affects a decision.

## 12. QML baseline

Source: [QML Library Layer](https://elios-1.gitbook.io/qmx/components/qml-library-layer.md), headings `Authority Boundary`, `Interfaces`, `Behavior`, and `Failure Modes`; [CT-QML-01 QML Library Interface Register](https://elios-1.gitbook.io/qmx/contracts/ct-qml-01-qml-library-interface-register.md), heading `CT-QML-01 QML Library Interface Register`.

- `Shell only` — QML may eventually host shared domain types, adapter-neutral contracts, and reusable deterministic library interfaces.
- `Boundary` — QML may not become an agentic workflow surface.
- `Contract shell` — Interface record has `interface_id`, `owner`, `version`, and `schema_ref`.
- `Gap` — `GAP-0013`: complete QML interface scope. No actual registered interface entries, API surface, ownership table, package boundary, or versioning policy are published.

## 13. Operational and test baseline

Sources: [Ops Runbook](https://elios-1.gitbook.io/qmx/lenses/ops-runbook.md), headings `Start`, `Stop`, `Restart`, and `Open Items`; [Incident Playbook](https://elios-1.gitbook.io/qmx/lenses/incident-playbook.md), headings `Technical Drift`, `News Block`, and `KSA Escalation`; [Test Strategy](https://elios-1.gitbook.io/qmx/lenses/test-strategy.md), headings `Required Behavior Tests` and `Anti-Patterns`; [Fixtures and Scenarios](https://elios-1.gitbook.io/qmx/lenses/fixtures-and-scenarios.md), headings `Scenario Bank` and `Fixture Rules`.

Startup checks:

1. BMS virtual ledger reconciles to broker.
2. KSA state is known.
3. MIS labeler versions match active certificates.
4. Adapter binding and broker connection are confirmed.

Stop/restart rules:

- Stop via KSA/adapter authority, not bot-code intervention.
- Unknown state blocks unsafe execution.
- Restart requires reconciliation; unexplained drift remains a technical kill.

Named required behavior tests:

- exam/live labeler parity;
- live and paper news block;
- every refusal emits a journal append;
- paper balance freezes at transition;
- drift halts trading;
- registry-backed money ladder;
- rollover-only sweep.

Fixture rules: freeze clocks, read registry values, avoid network calls in unit tests, and assert journal side effects.

## 14. Explicit open gaps in Trading Node scope

Source: [Gap Report](https://elios-1.gitbook.io/qmx/gap-report.md), headings `Open Gaps`, `Answered Gaps`, `Deferred Gaps`, `Out Of Scope`, and `Old Vault Baseline Comparison`.

| Gap | Surface | Published question |
|---|---|---|
| GAP-0001 | Book Template / Scalper | Section 6 workspace design |
| GAP-0002 | Notification / BMS | severity, channels, retry, dedupe, quiet hours, credentials |
| GAP-0003 | Data / BMS / MIS-Archive | ownership, stores, retention, backup/restore, migration, schemas |
| GAP-0005 | Adapter / KSA / Paper | broker and cTrader feasibility |
| GAP-0006 | Paper / BMS | complete paper/live transition state machine |
| GAP-0007 | Treasury | exact refund-reserve rho estimator |
| GAP-0008 | BMS / KSA | Exposure Desk v2 authority and cross-book caps |
| GAP-0009 | BMS | observability substrate |
| GAP-0010 | BMS / Book Template | Section 1–2 BMS assignments |
| GAP-0012 | Book Template | certified leash-event/chorus frequency rules |
| GAP-0013 | QML | QML interface scope |
| GAP-0015 | KSA / Adapter / BMS | trigger-to-level matrix, especially connectivity/unknown state |

`GAP-0011` is answered: formulas and registry are authoritative; numeric conversation examples are checksums. `GAP-0004` prop-firm books is deferred and remains outside this recovery pass. `GAP-0014` UI is out of scope.

## 15. Dead ideas that must not be recovered

Source: [Dead Decisions](https://elios-1.gitbook.io/qmx/dead-decisions.md), heading `Dead Decisions`.

- RMF with declared weights; use measured/registry-backed quantities and formula derivations.
- TIGHTEN/half-size KSA level; escalate protection instead.
- Mid-cycle top-up; re-seed only at a valid cycle boundary.
- Region-shift budget rotation; never redistribute budget in-cycle.
- Human chorus review loop; intraday protection stays deterministic.
- Live restart from kill-line remnant; remain paper until cycle-boundary re-seed.
- Uniform values across books; profiles own values while global capability remains common.
- Session windows as trading authority; doors and KSA own permission.

## 16. Visible tensions, contradictions, and undocumented semantics

These are comparison targets, not proposed resolutions.

### T-01 — “Trading Node” has no published component or deployment boundary

[Overview](https://elios-1.gitbook.io/qmx/architecture/overview.md), `Container View`, publishes logical research/runtime groups. [Dependency Graph](https://elios-1.gitbook.io/qmx/architecture/dependency-graph.md) has no `COMP-TRADING-NODE`. [Kill-Switch Authority](https://elios-1.gitbook.io/qmx/components/kill-switch-authority.md) says “the trading node enforces effects through the adapter” without identifying which components/processes constitute it. The local wiki may be the only source for the server boundary.

### T-02 — SQS is safety-critical but undefined

[Market Intelligence Service](https://elios-1.gitbook.io/qmx/components/market-intelligence-service.md), `Behavior` and `Failure Modes`, makes unreachable SQS a hard block; [CT-MIS-01](https://elios-1.gitbook.io/qmx/contracts/ct-mis-01-mis-live-snapshot.md) requires `sqs_score` and `sqs_hard_block`. No published page defines SQS ownership, acronym, score, threshold, protocol, or health semantics.

### T-03 — Book-mode write path conflicts across pages

[Book Template](https://elios-1.gitbook.io/qmx/components/book-template.md), `Interfaces`, says it emits `CT-BOOK-02` to BMS. [Paper Mode System](https://elios-1.gitbook.io/qmx/components/paper-mode-system.md), `Interfaces`, says `CT-BOOK-02` is in/out with Book Template. [Book Management System](https://elios-1.gitbook.io/qmx/components/book-management-system.md), `Interfaces`, does not list `CT-BOOK-02`, even though [CT-BMS-02](https://elios-1.gitbook.io/qmx/contracts/ct-bms-02-mode-registry-read.md) declares BMS authoritative for modes. Producer, registry-write command, acknowledgement, and synchronization are missing.

### T-04 — Paper transition has two claimed producers/hops

[Scalper Book](https://elios-1.gitbook.io/qmx/components/scalper-book.md), `Interfaces`, emits `CT-PAPER-01` to Paper. [Paper Mode System](https://elios-1.gitbook.io/qmx/components/paper-mode-system.md), `Interfaces`, emits the same `CT-PAPER-01` to BMS. The single contract does not distinguish a requested transition from an authoritative transition event.

### T-05 — Treasury-event path is inconsistent

[Scalper Book](https://elios-1.gitbook.io/qmx/components/scalper-book.md), `Interfaces`, emits `CT-BMS-01` to Treasury. [Treasury Desk](https://elios-1.gitbook.io/qmx/components/treasury-desk.md), `Interfaces`, emits `CT-BMS-01` to BMS. [Overview](https://elios-1.gitbook.io/qmx/architecture/overview.md), `Container View`, instead draws Scalper → BMS → Treasury. The contract does not distinguish request, approved transaction, and recorded event.

### T-06 — Book-level modes cannot cleanly express bot-level breaker behavior

[Paper Mode System](https://elios-1.gitbook.io/qmx/components/paper-mode-system.md), `Behavior`, says the “affected bot” benches to paper. `CT-PAPER-01` has optional `bot_id`, but [CT-BOOK-02](https://elios-1.gitbook.io/qmx/contracts/ct-book-02-book-mode-state.md) and [CT-BMS-02](https://elios-1.gitbook.io/qmx/contracts/ct-bms-02-mode-registry-read.md) are keyed only by `book_id`. The authoritative mode model cannot unambiguously represent a mixed book with one benched bot and other live bots.

### T-07 — Notification severity ownership conflicts with its input contract

[Notification System](https://elios-1.gitbook.io/qmx/components/notification-system.md), `Authority Boundary`, says Notification may propose severity. Its incoming [CT-NOTIFY-01](https://elios-1.gitbook.io/qmx/contracts/ct-notify-01-notification-candidate.md) already requires `proposed_tier`. It is unclear whether BMS or Notification classifies the event. BMS’s interface table also omits CT-NOTIFY-01 despite its diagram showing Records → Notification.

### T-08 — BMS/KSA policy and state form an unresolved cyclic authority edge

[Book Management System](https://elios-1.gitbook.io/qmx/components/book-management-system.md) says BMS owns KSA policy and emits news directives/mode reads. [Kill-Switch Authority](https://elios-1.gitbook.io/qmx/components/kill-switch-authority.md) says KSA classifies triggers, issues/persists global state, consumes MIS, and drives Adapter. [Dependency Graph](https://elios-1.gitbook.io/qmx/architecture/dependency-graph.md) makes BMS depend on KSA and KSA depend on BMS. Trigger evaluation, state ownership, persistence ownership, initialization ordering, and recovery ordering are not separated.

### T-09 — “Bot is the only market-touching actor” needs an execution interpretation

[System Constitution](https://elios-1.gitbook.io/qmx/system-constitution.md), `L1` and `Authority Hierarchy`, calls the bot the only market-touching actor. [Broker Adapter](https://elios-1.gitbook.io/qmx/components/broker-adapter.md) mechanically calls broker-specific execution after receiving a book command. This is reconcilable if “market-touching” means “owns trade intent/entry-exit logic,” but that interpretation is not stated; literal wording conflicts with the adapter’s physical broker contact.

### T-10 — MIS parity cannot be verified from CT-MIS-01

[Ops Runbook](https://elios-1.gitbook.io/qmx/lenses/ops-runbook.md), `Start`, requires live labeler versions to match certificates. [MLOps Model Lifecycle](https://elios-1.gitbook.io/qmx/lenses/mlops-model-lifecycle.md), `Lifecycle`, pins certificates to versions. [CT-MIS-01](https://elios-1.gitbook.io/qmx/contracts/ct-mis-01-mis-live-snapshot.md) contains only `snapshot_version`, not labeler ids, labeler versions, parameter-set versions, emission time, or provenance. The documented startup/runtime parity check lacks a published data path.

### T-11 — MIS snapshot health fields lack timing and semantics

CT-MIS-01 requires `feed_state` and `degraded_sensors`, yet has no observed-at/published-at timestamps, sequence, freshness age, source, or degradation details. Optional regime fields have no absence behavior. SQS score has no scale. A “dead” state is enforceable, but `stale`, degraded fields, spread states, gaps, and liquidity stress have no published scalper-profile response.

### T-12 — Formula units are internally unclear

[Formulas](https://elios-1.gitbook.io/qmx/registry/formulas.md) defines Lbar in R, `offer_R_usd = D / (B*b*Lbar)`, and `R_max_usd <= B*b*Lbar`. The latter compares a name expressed as USD with a right-hand side expressed in counts/ratios/R. Even FORM-0004’s name mixes R and USD. The formulas may encode “USD value of one R,” but that unit model is not stated. Do not silently normalize this in reconstruction.

### T-13 — Cycle termination after kill-line stand-down is unclear

The cycle is defined as seed-to-cap, while kill-line crossing forces paper until cycle-boundary re-seed. If cap is never reached, GitBook does not define what closes the failed cycle or authorizes a new seed. It also does not say whether intraday cap contact followed by rollover below cap completes a cycle.

### T-14 — Reconciliation contract cannot show the unexplained amount or tolerance application

[CT-BMS-03](https://elios-1.gitbook.io/qmx/contracts/ct-bms-03-reconciliation-report.md) has virtual equity, broker equity, `explained_delta`, and a verdict, but no report id, timestamp, book/cycle id, raw delta, unexplained delta, evidence references, or epsilon used. The component law is strong (drift kills trading), but auditability and idempotency are not expressible.

### T-15 — Journal ownership language conflicts at the KSA audit log

[Book Management System](https://elios-1.gitbook.io/qmx/components/book-management-system.md), `Behavior`, says Records owns the only journal write path. [Logging Spec](https://elios-1.gitbook.io/qmx/lenses/logging-spec.md), `Required Journals`, lists the KSA audit log owner as `COMP-KSA / COMP-BMS`. This may mean KSA emits and BMS writes, but the contract/path is not stated.

### T-16 — Data ownership is asserted but not registered

[Data Layer](https://elios-1.gitbook.io/qmx/components/data-layer.md) calls immutable MIS emissions and append-only BMS records known ownership islands, but [CT-DATA-01](https://elios-1.gitbook.io/qmx/contracts/ct-data-01-data-ownership-register.md) publishes only a record schema and no actual entries. Owner, store, schema, and retention remain unrecoverable from GitBook.

### T-17 — KSA has levels but no published effects matrix

The KSA event enum is reviewed, and news/unknown state behaviors are asserted, but `GAP-0015` leaves trigger-to-level mapping open and no page defines per-level adapter effects (block new, cancel pending, close positions, close all, pair-scoped versus global). ENH-0008 is referenced but absent. The enum alone must not be treated as executable safety policy.

### T-18 — Adapter contract is too open to reconstruct execution

`CT-ADAPTER-01.payload` is an unconstrained object, and no response/fill contract is published. The book is said to own entry/exit organs and Adapter to execute, but required order fields, position identifiers, stop/target ownership, mutation rules, and broker event reconciliation are absent.

### T-19 — “Reviewed” contracts coexist with unresolved behavioral gaps

All inspected contracts report `status: reviewed`, including notification, data, paper, adapter, and QML contracts that explicitly carry gaps. [Changelog](https://elios-1.gitbook.io/qmx/changelog.md), heading `2026-07-08 - Operator Rulings Applied`, explains that gap-bearing documents use reviewed status. Therefore `reviewed` means the shell was reviewed, not that the behavior is closed or build-ready.

### T-20 — Published decision provenance is incomplete

Components cite DEC-0001 through DEC-0055 and ENH-0001 through ENH-0008, but only three ADRs and summary references are public. [ADR-0003 Transcript Authority](https://elios-1.gitbook.io/qmx/decisions/adr-0003-transcript-authority.md) establishes transcripts as higher authority, yet those transcripts and the full decision ledger are unavailable in GitBook. Where local wiki text differs, GitBook alone cannot resolve the conflict.

## 17. Golden baseline scenarios

- [SCN-0001 Money Ladder](https://elios-1.gitbook.io/qmx/scenarios/scn-0001-money-ladder.md): recompute runway, daily budget, offer, and take from the registry and measured per-bot Lbar; conversation numbers are checksums.
- [SCN-0002 Rollover Sweep](https://elios-1.gitbook.io/qmx/scenarios/scn-0002-rollover-sweep.md): no intraday sweep; at rollover sweep equity minus seed and reset virtual equity to seed; knowledge persists.
- [SCN-0003 News Block](https://elios-1.gitbook.io/qmx/scenarios/scn-0003-news-block.md): the same affected-pair refusal applies to live and paper, and both sign the veto ledger.

These are the only published golden scenarios. There are no published scenarios for SQS failure, dead/stale feed, KSA levels, unknown startup, reconciliation drift, breaker reset, kill-line cycle closure, partial fills, notification retry/dedupe, multi-book exposure, or concurrent bot seats.

## 18. Comparison-oriented baseline checklist

When comparing local wiki/BMAD material against GitBook, classify local Trading Node content against these buckets:

1. **Deployment definition** — Does local documentation define the actual Trading Node process/server boundary absent from GitBook?
2. **SQS closure** — Does it define SQS acronym, ownership, score, hard-block logic, and failure protocol?
3. **Contract routing** — Does it resolve CT-BOOK-02, CT-PAPER-01, CT-BMS-01, CT-NOTIFY-01, and mode-registry producer/consumer inconsistencies?
4. **Mode granularity** — Does it separate book mode from per-bot seat/bench state?
5. **Runtime state machines** — Does it close Paper, cycle failure/re-seed, KSA target/effect, adapter recovery, and startup ordering?
6. **MIS contract completeness** — Does it add labeler provenance, timestamps, freshness, score semantics, and profile response rules?
7. **Execution contract completeness** — Does it define adapter payloads, responses, idempotency, fills, positions, and reconciliation linkage?
8. **Accounting closure** — Does it define rollover, transaction boundaries, refund/re-seed preconditions, failed-cycle closure, and epsilon calculation?
9. **Persistence/ops closure** — Does it populate data ownership, journals, retention, recovery, observability, and credentials?
10. **Formula clarification** — Does it resolve R-versus-USD units without changing the ratified economic relationships?
11. **Published enhancements** — Does it supply the missing ENH-0001 tier semantics, ENH-0005 rollout details, ENH-0008 KSA mapping, or other operator rulings?
12. **Noise rejection** — Does the local item concern agentic R&D, Backtest Engine/WF1/WF2, UI, or prop-firm books? If yes, exclude it from this recovery delta.

## 19. Compact source catalogue

| Page | Most relevant headings | Baseline role |
|---|---|---|
| [System Constitution](https://elios-1.gitbook.io/qmx/system-constitution.md) | `Laws`, `Authority Hierarchy`, `Precedence` | Binding invariants |
| [Overview](https://elios-1.gitbook.io/qmx/architecture/overview.md) | `System Context`, `Container View`, `Runtime Shape`, `Scope Boundary` | Logical topology and boundary |
| [Dependency Graph](https://elios-1.gitbook.io/qmx/architecture/dependency-graph.md) | `Dependency Graph` | Component/interface graph |
| [Book Template](https://elios-1.gitbook.io/qmx/components/book-template.md) | `Authority Boundary`, `Behavior`, `Configuration`, `Failure Modes` | Global book grammar and doors |
| [Scalper Book](https://elios-1.gitbook.io/qmx/components/scalper-book.md) | same | First book instance |
| [Market Intelligence Service](https://elios-1.gitbook.io/qmx/components/market-intelligence-service.md) | same | MIS-Live/Archive and SQS references |
| [Book Management System](https://elios-1.gitbook.io/qmx/components/book-management-system.md) | same | Desks, records, modes, policy |
| [Treasury Desk](https://elios-1.gitbook.io/qmx/components/treasury-desk.md) | same | Capital ledger and cycle boundary |
| [Kill-Switch Authority](https://elios-1.gitbook.io/qmx/components/kill-switch-authority.md) | same | Protection state machine |
| [Paper Mode System](https://elios-1.gitbook.io/qmx/components/paper-mode-system.md) | same | Counterfactual mode |
| [Broker Adapter](https://elios-1.gitbook.io/qmx/components/broker-adapter.md) | same | Broker boundary |
| [Notification System](https://elios-1.gitbook.io/qmx/components/notification-system.md) | same | Journal-derived operator messages |
| [Data Layer](https://elios-1.gitbook.io/qmx/components/data-layer.md) | same | Persistence shell |
| [QML Library Layer](https://elios-1.gitbook.io/qmx/components/qml-library-layer.md) | same | Deterministic library shell |
| [Variables](https://elios-1.gitbook.io/qmx/registry/variables.md) | `Variables` | Exact published registry defaults |
| [Formulas](https://elios-1.gitbook.io/qmx/registry/formulas.md) | `Formulas` | Exact published relationships |
| [Contracts](https://elios-1.gitbook.io/qmx/contracts.md) and child CT pages | contract YAML | Interface shells |
| [Gap Report](https://elios-1.gitbook.io/qmx/gap-report.md) | `Open Gaps`, `Answered Gaps`, `Old Vault Baseline Comparison` | Explicit fog and baseline treatment |
| [Dead Decisions](https://elios-1.gitbook.io/qmx/dead-decisions.md) | `Dead Decisions` | Noise that must not be revived |
| [Ops Runbook](https://elios-1.gitbook.io/qmx/lenses/ops-runbook.md) | `Start`, `Stop`, `Restart` | Runtime operating checks |
| [Logging Spec](https://elios-1.gitbook.io/qmx/lenses/logging-spec.md) | `Required Journals`, `Gaps` | Journal baseline |
| [Performance Budgets](https://elios-1.gitbook.io/qmx/lenses/performance-budgets.md) | `Budgets`, `Measurement Rule` | Latency baseline |
| [Security Model](https://elios-1.gitbook.io/qmx/lenses/security-model.md) | `Trust Boundaries`, `Secret Handling Gap` | Authority/secret boundary |
| [Test Strategy](https://elios-1.gitbook.io/qmx/lenses/test-strategy.md) | `Required Behavior Tests`, `Anti-Patterns` | Required proofs |
| [Changelog](https://elios-1.gitbook.io/qmx/changelog.md) | `2026-07-08 - Operator Rulings Applied` | Baseline date and status semantics |

## Bottom line

GitBook supplies a strong policy/economic skeleton for the Trading Node: strict bot→book→BMS authority, seven book doors, registry-backed sizing, MIS as information-only, rollover-only cycles, append-only records, deterministic KSA escalation, frozen paper mode, broker isolation, and conservative failure. Its incompleteness is concentrated in deployment boundaries, SQS, contract routing, mode granularity, data/observability, KSA effects, broker execution mechanics, notification delivery, QML interfaces, and several state-machine edges. The local documentation comparison should seek closure or additions in exactly those areas while rejecting agentic/backtest/UI material and every explicitly dead decision.
