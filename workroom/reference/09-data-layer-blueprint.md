# 09 - QMX Data-Layer Blueprint

**Written:** 2026-08-18. **Status:** research synthesis, NOT ratified - produced for the operator verdict pass; open questions at the end are his to answer.

# QMX DATA-LAYER BLUEPRINT — for ratification
*Sources: operator dictation 2026-08-18 (authoritative); `research/02-data-foundation.md`; `research/10-macro-micro-analysis-data.md`; `reference/05-trading-node-primer.md` + telemetry catalog; `recorder/README.md` (running).*

**The three concerns, kept apart (dictation ruling 1).** *Ingestion* = getting bytes in and proving what we got. *Processed collection* = the curated datasets that exist as artefacts. *Processing method* = the recipe/code that turned one into the other. They are separate layers with separate stores, and nothing in the platform is allowed to blur them — a processed file that cannot name its raw inputs and its recipe version is treated as unowned data.

## 1. THE LAYERS

**L0 — Ingest (recorders).** One small, dumb, dependency-free program per source. It fetches, stamps UTC, writes the payload exactly as received, and appends one manifest line (`fetched_at_utc, url, sha256, bytes, http_status`). It never parses, normalises, or judges. This is already live for the FairEconomy calendar (`recorder/`). Two rules carry over to every future recorder: a failed fetch must never be recorded as "nothing happened" (Dukascopy returned HTTP 503 on 4 of 8 unpaced hourly requests — `02` §1), and sources with no vintage API (BIS, ECB, OECD, Eurostat, IMF, most central banks — `10` §4.3) can only ever have the history we start banking today. Ingestion is the one layer where being late is unrecoverable.

**L1 — Raw evidence archive.** The immutable, append-only record of what the world said. Three families: *price* (ticks and bars, long format `ts, symbol, price, source`, sorted by `(symbol, ts)`, zstd Parquet, Hive `symbol/year/month` for ticks — `02` §4.3); *facts* (every macro/calendar/news number as a bitemporal row: what period it is about, and when we first believed it — `10` §9.1–9.2); *own-execution evidence* (our order log and quote stream from the VPS, which cannot be re-downloaded later — `10` §7.1). Nothing here is ever edited. A correction is a new row; a re-download is a new file plus a manifest entry. Live collection lands first in a small SQLite inbox and is compacted into Parquet nightly, verified by row count, and only then deleted from the inbox (`02` §4.4).

**L2 — Processed / curated.** Everything derived: resampled bars, spread profiles by pair × hour × day-of-week, tick-arrival rates, tradeability scores, regime labels, feature tables, ML inference outputs. Every processed artefact carries three things: the recipe id + version that built it, the sha256 manifest of every raw partition it read, and the build timestamp. That makes the whole layer *disposable by design* — if a recipe is wrong we delete the outputs and rebuild, and no one has to argue about which copy was right. Heavy work (regime models, vol forecasts, correlation matrices, ML inference) is built here and served to the MIS; light indicators stay inside the bot and are never persisted as platform data (dictation ruling 9).

**L3 — Telemetry / journal.** The record of what *our system* did, as a real portfolio manager would keep it: every intent, fill, veto, mode change, money-ladder recompute, MIS snapshot, SQS score, kill-switch transition, treasury sweep and reconciliation. It is append-only like L1 — a journal that can be edited is not evidence. It is the input to daily and Sunday review, to agent post-mortems, to alpha-decay sensing, and to the auto-detection flags in §5. Detail in §3.

**L4 — Research access (splits by default).** One accessor function is the front door for all training, backtesting and evaluation. You ask it for a *named split*, never for a date range; it returns data already cut into in-sample / out-of-sample with embargo gaps applied, and it records what you read. The most recent stretch of history is sealed and simply never returned by this door. Detail in §4.

**L5 — Backup (an inbuilt feature, not a chore).** Because L1 files are immutable and content-named, backup is a copy-forward, not a database dump: nightly the VPS pushes its inbox + journal to the workstation, the workstation snapshots the whole lake to an external drive, and the small-but-irreplaceable stores (journal, facts, split registry, manifests, recipes) go encrypted offsite monthly — they are megabytes, not gigabytes. Restore is tested on a schedule and is itself a journaled event; an untested backup is a rumour. The same job verifies manifest sha256s, so silent bit-rot surfaces as a flag rather than as a bad backtest two years later.

## 2. STORES PER PURPOSE

| Layer | Store | Why | Must NOT be used for |
|---|---|---|---|
| L0 ingest | Raw files on disk + `manifest.jsonl` | Zero dependencies; provable bytes; survives every future rewrite | Querying, analysis, or anything that requires the payload to be parsed |
| L1 price archive | Parquet (zstd), Hive-partitioned, read by DuckDB | Columnar, portable, engine-agnostic, no server for one operator (`02` §3, §4.3) | Live concurrent writes; row-by-row updates; anything mutable |
| L1 live inbox | SQLite in WAL mode | The only zero-dependency local store where a collector writes while research reads (`02` §3.4) | The archive itself (row-oriented, no pruning); any network/mapped drive |
| L1 facts (macro/calendar/news) | Parquet, append-only bitemporal rows | `ref_period_start > known_at` *is* the definition of future data (`10` §9.1) | Filtering by `ref_period` in a backtest — only `known_at` is a legal filter |
| L1 own-execution evidence | SQLite inbox on VPS → Parquet | Must be captured live; cannot be reconstructed from broker history (`10` §7.1) | Deletion for space — this is the rarest data we own |
| L2 processed | Parquet, one dataset per recipe+version | Rebuildable, cheap, comparable across versions | Being treated as evidence; hand-patching |
| L3 journal | SQLite (live, VPS) → Parquet (archive), append-only | Same inbox/archive split as prices; small enough that everything survives | Updates or deletes of any kind |
| L4 split registry | JSON/CSV in git | A split is *data, not code*; git gives immutable, reviewable history (`02` §5) | Being generated on the fly at query time |
| L5 backup | Plain file copies + checksums | Immutable files make backup trivial and restore verifiable | Being the only copy of anything |
| Query engine | DuckDB (MIT) | Zero-server, reads Parquet in place, `ASOF JOIN` built in (`02` §3.1, `10` §9.3) | Sharing one DuckDB file between a live writer and a reader — that deadlocks |
| Transform layer | Polars | Declarative `join_asof` / `group_by_dynamic`; safer for agents than mutable pandas (`02` §3.2) | `join_asof(strategy="forward"/"nearest")` outside research — lookahead generators |

**Reject:** PostgreSQL/TimescaleDB for the archive — real operational surface (patch, tune, monitor, back up) bought for no gain at one-operator scale (`02` §3.4).

**ArcticDB — honest verdict: no, and not for the licence reason.** File `02` blocked it on licence; file `10` §9.3 says that block was stronger than the BSL text supports — a solo operator running it inside his own system is not offering a "Database Service", though Man Group's own FAQ reads more broadly, so the legal position is genuinely ambiguous. Set the licence aside: the technical reason is decisive. ArcticDB's versioning (`as_of`) is *transaction-time only* — it versions writes to a symbol. It has no valid-time axis, so it cannot answer "what did we believe about March-2020 CPI on 15-April-2020" without re-encoding valid time in the payload anyway — at which point Parquet + DuckDB `ASOF JOIN` does the same job with no licence question and no extra binary on the VPS. Verdict: **not in v1**. Revisit only if we outgrow one workstation and one VPS.

**Lineage is graph-shaped — but don't buy a graph database.** The shape is real: run → inputs → recipe → outputs → results, with many-to-many edges. Recommendation: **graph-in-files first.** One append-only `lineage.jsonl` of edges (`{from_id, to_id, edge_type, run_id, ts}`) plus the manifests already produced by L1/L2. Ancestor/descendant walks over tens of thousands of edges are milliseconds in plain Python or DuckDB recursive CTEs. It backs up like everything else, diffs in git, and reads fine without any tool. If lineage questions ever get genuinely interactive and multi-hop, the same JSONL loads into Neo4j/Kùzu unchanged — the file *is* the export format. So: adopt the graph model now, defer the graph engine, and never make a database the only way to read our own lineage (dictation ruling 7).

## 3. THE JOURNAL

Every journal row shares a common header: `event_id, ts_utc, run_id, component, mode (live|paper_shadow|paper_forced|bench), book_id, bot_id, pair, snapshot_version, schema_version`. `mode` on every row is what makes paper and live comparable without a second pipeline.

| Stream | What is recorded | Cadence | Retention |
|---|---|---|---|
| `intent_journal` | Trade intent envelope: `requested_r`, `footprint_version`, `snapshot_version`, refused-or-passed | per decision attempt | forever |
| `trade_journal` | Fill price/size/time, decision→submit→fill latency, slippage vs decision, slippage vs arrival, spread paid, exit reason, realised R | per fill | forever |
| `veto_ledger` | Door, reason, candidate intent | per refusal (any of 7 doors) | forever |
| `book_journal` | Mode state + `reason` + `trigger_decision`; leash escalations; money ladder `D`/`offer_R`/`take_R`; cycle boundary | per event; ladder per rollover/seat | forever |
| `mis_snapshot` | CT-MIS-01: `sqs_score`, `sqs_hard_block`, `feed_state`, regime, `degraded_sensors`, labeler versions | per snapshot (native resolution) | raw 90 days; then per-minute summary + **all** transitions forever |
| `ksa_audit` | Level and trigger-class transition (GREEN…BLACK; `scheduled_news`/`black_swan`/`connectivity`/`unknown_state`), **affected pairs**, protection effect | per trigger | forever |
| `adapter_log` | `place_order`/`cancel`/`close`/`close_all`, connectivity state, `broker_equity` | per order / per check | 400 days, then monthly compaction |
| `treasury_journal` | CT-BMS-01 sweep/refund/re_seed; CT-BMS-03 `virtual_equity`/`broker_equity`/`explained_delta`/verdict | per cycle boundary / per reconciliation | forever |
| `correlation_ledger` | Correlation evaluations and resulting refusals | per evaluation | 400 days + monthly summary forever |
| `exam_certificates` | EV by regime, `Lbar`, fire-rate band, cost ratio, labeler versions | per certificate | forever |
| `flags` | Auto-detection flag opened/closed, rule id+version, observed value, operator range (see §5) | per transition | forever |
| `heartbeat` | Bot/book alive, current mode, `feed_state`, snapshot age | every 60s per bot, always | 400 days |

**Quantity, honestly.** Everything above except `mis_snapshot` is well under a gigabyte a year at one-operator scale; MIS snapshots dominate and are the only stream needing a downsample rule. There is no storage-cost problem here (`10` §4.5) — the cost is write discipline, not disk.

**Paper-mode continuity — the guarantee (dictation ruling 6).** Paper is not a fallback state, it is the **standing state**: every bot runs its paper twin permanently, including while it is trading live. Live execution is an *additional* route layered on the same decision stream, never a replacement for it. Three mechanics enforce the guarantee: (1) the kill switch and news blocks stop *execution*, not *recording* — a pair-scoped block must leave that pair's paper twin running, or alpha-decay sensing goes blind exactly when it matters most; (2) the `heartbeat` row is written even when nothing happens, so "no trades" and "no data" are distinguishable — the same rule as never conflating an HTTP 503 with an empty market hour (`02` §1); (3) the alpha-decay estimator reads a coverage figure from the heartbeat stream and **refuses to emit a verdict** below the operator's coverage threshold rather than quietly averaging over a hole.

## 4. SPLITS BY DEFAULT

**The door.** `qmf.data.load(split_id=...)` is the front door. It takes a *named split*, never raw dates — so an agent cannot ask for "2019 to today" and accidentally train on the future (`02` §5). The registry is a git-versioned table of `{split_id, kind: is|oos|embargo, symbol_set, t_start, t_end, created_at, created_by}`. Embargo gaps are first-class rows, not a flag buried in a training loop, which puts purged/embargoed cross-validation at the data layer where it can be audited. The door also stamps every read into the lineage file: which split, which partitions, which sha256s.

**The sealed holdout.** The most recent N months are never returned by any research call, at any severity, to anyone. Unsealing goes through a separate, fully logged `final_validation` path that records who asked, for which candidate, when. This is the single strongest defence against a solo operator's own iteration bias, because it defends against the operator too.

**Reconciling with don't-box-in (dictation ruling 7).** The door is the *easy* path, not the *only* path. Plain Python can open any Parquet file directly, and that stays true forever — the lake is files, and files have no gatekeeper. What the door controls is not access but **standing**: a result carrying a `split_id` and a manifest hash is *registered* and can be ratified, promoted, or put in front of a Book; a result without them is a personal note. No walls, no permission errors, no wrapper you must fight. The discipline is enforced at the point where it actually matters — what gets believed — not at the point where it would only be annoying.

**Practical default.** The door's zero-argument call returns the current standard split set, so the lazy path and the correct path are the same path. Agents get properly-split data by default because *default* is what the function does when you don't argue with it (dictation ruling 2).

## 5. AUTO-DETECTION WITH OPERATOR RANGES

**Shape.** One plain-text `rules.yaml` in git, owned by the operator, read on every evaluation. Each rule is one sentence in the operator's own terms:

```yaml
- id: spread-blowout
  metric: spread_p90_points        # picked from a named catalog, not written
  scope:  {pair: EURUSD, hour: any}
  range:  {max: 2.5}               # operator sets the number
  for:    3                        # consecutive evaluation periods
  then:   warn
  say:    "EURUSD spreads above your ceiling for 45 minutes."
```

**Why it stays simple.** The operator never writes a query. `metric` comes from a fixed catalog of named measurements, each defined once as a one-line query over the journal (spread p90, tick-arrival rate, fire rate vs exam band, live-vs-paper divergence, slippage vs decision, unexplained equity delta, MIS `degraded_sensors` duration, heartbeat gap, recorder missed fetch, days since last fill). The operator only ever chooses *which* measurement, *what range*, and *how long*. Adding a new measurement is a small engineering task; changing a range is a one-line edit.

**Evaluation and behaviour.** A single evaluator runs on a fixed tick (every 15 minutes, plus at each rollover) over the journal, and does four things: computes each rule's metric; opens a flag when the value has been outside the operator's range for `for` consecutive periods; keeps the flag open (no re-notification) until the value returns inside range for the same count — hysteresis, so one noisy print doesn't spam; and closes it with a journaled row. Flags are written into the journal as `flags` rows with the rule version and observed value, so "why did this fire in March" is answerable a year later.

**Hard boundary: flags notify, flags never act.** Only the kill switch and the Book have authority to change trading state. An auto-detection rule that could stand down a Book would be a second, undocumented risk system. Notification channel is deliberately left open (GAP-0002 is unresolved); default is a line in the journal plus the operator status screen, same pattern as `recorder/status.py`.

## 6. OPEN QUESTIONS FOR MUBARAK

1. **ArcticDB — drop it for v1?** *Recommend: yes, drop it.* Not the licence (that's genuinely arguable) — it simply can't record "what we believed when" without us re-encoding that ourselves anyway, which Parquet + DuckDB already do for free. **Yes/no?**
2. **Lineage — files now, graph database never bought until proven needed?** *Recommend: yes.* Use the graph *model* in an append-only edge file; it loads into Neo4j unchanged if we ever need it, and stays readable in plain Python meanwhile. **Yes/no?**
3. **Dukascopy — download for private research only, never redistribute, and treat our own live VPS recording as the authoritative archive?** *Recommend: yes.* Their terms forbid automated scraping and "constructing a database"; this is your risk call, not an engineering one, and our own live capture is the data no one can take away. **Yes/no?**
4. **Sealed holdout — the most recent 12 months, unsealed only once per strategy, logged?** *Recommend: yes, 12 months.* Long enough to contain a regime change, short enough to leave usable training history. **Yes/no?**
5. **Paper twin permanently on — every bot runs its paper self even while trading live?** *Recommend: yes.* It costs a little compute and is the only way alpha-decay sensing has an unbroken series across kill-switch and news blocks. **Yes/no?**
6. **Pair-scoped blocks stop execution but never stop recording — including the paper twin for the blocked pair?** *Recommend: yes.* Otherwise we go blind exactly during the events we most need to study. **Yes/no?**
7. **MIS snapshots — keep 90 days at full resolution, then keep per-minute summaries plus every state transition forever?** *Recommend: yes.* Full-resolution history is the only stream large enough to matter, and transitions are what post-mortems actually read. **Yes/no?**
8. **Backup — nightly VPS→workstation, weekly workstation→external drive, monthly encrypted offsite of the small irreplaceable stores only, with a scheduled restore test?** *Recommend: yes.* The offsite set (journal, facts, splits, manifests, recipes) is megabytes; price ticks are re-downloadable, our own journal is not. **Yes/no?**