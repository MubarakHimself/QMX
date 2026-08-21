# Spine Index — ARCHITECTURE-SPINE.md (for the backtesting sitting)

Source: `ARCHITECTURE-SPINE.md` (632 lines, status `final`, created 2026-08-19, updated 2026-08-20). All line numbers below are into that file unless another path is named.

## Named paradigm

**Contract-hub library workspace (hexagonal at workspace scale)** (frontmatter L6; §Design Paradigm L19–21). `qmf-core` is a dependency-free hub carrying only definitions (value types, domain nouns, typed refusals, fingerprints, protocols); all other packages depend inward on it; runtime concerns enter through protocols outer packages/extensions implement. **Nothing in QMF is an application — trading node, backtest workspaces, and the QMX app are built *with* QMF, outside this repo's scope** (L21). This is the single most load-bearing line for a backtesting CLI: a backtester is an *application built on QMF*, not a QMF package.

## AD index (AD-1 … AD-41), one line each

- **AD-1** Runtime matrix (L46): CPython 3.14 pinned everywhere; Tier-1 Windows 11 + Ubuntu LTS x86-64; pure-Python OS-neutral. Prevents version skew making results non-comparable across sandboxes.
- **AD-2** One repo, seven packages (L52): uv workspace, seven `qmf.*` packages; PEP 420 namespace (no `qmf/__init__.py`); extensions are separate versioned packages outside the roster on their own SemVer ladder; shared nouns defined in core, records owned by registry.
- **AD-3** Quality toolchain (L58): ruff + pyright strict + pytest; coverage floor 80%, 100% branch on CT-01/CT-02; every package ships tests AND reference usage; `poe fmt|lint|types|test|check`.
- **AD-4** Three quality tiers bound to factory events (L64): tier1 `poe check`; tier2 `poe check-integration` (+ integration + **contract tests** per package isolated); tier3 `poe check-release` (+ build + clean-install smoke on both OSes). Defines "contract test".
- **AD-5** Two version ladders; meanings never mutate (L70): SemVer lockstep for roster; every serialized contract carries integer format version whose meaning never changes; append-only history; re-derivation under new calendar/tzdata mints a **new artifact with a lineage edge**, never a rewrite.
- **AD-6** Dependency/licence tiers; zero-dep core (L76): permissive OK, GPL/AGPL + strategy-family + platform-imposing deps prohibited; core is stdlib-only; `DEPENDENCIES.md` register.
- **AD-7** Exact money (L82): Money/Price/Quantity as scaled integers; money path is a **taint not a location**; float banned on money path except at named conversion boundaries; foreign money/floats are evidence never identity; PriceDelta first-class; canonical rational form pinned for identity.
- **AD-8** Exact time (L95): int64 UTC ns; CivilDate vs TradingDate (carries calendar identity in-band); wall vs monotonic clocks type-separated; per-writer sequence `(instant, writer, sequence)` is a **replay-determinism device with no causal meaning**; calendars (market-hours / day-boundary / news) defined; clock is a core protocol injected at root, **replay injects a data-driven clock**.
- **AD-9** Instrument/venue/account identity (L113): instrument = (venue, opaque symbol); VenueId opaque/operator-minted; broker identity is deployment config never architecture; platform-family adapter profiles legitimate.
- **AD-10** Deterministic fingerprints (L119): one `fp1` implementation in core; SHA-256 recipe pinned; floats refused in identity; float-bearing artifacts get label-derived identity; collisions split (idempotent re-write accepted, true collision refused/alarmed).
- **AD-11** Typed refusals (L130): every public op returns success or typed refusal (7 categories incl. `policy rejection`, `stale evidence`, `unsupported capability`); refusals returned not thrown.
- **AD-12** Result label and **worlds** (L136): every result carries producer identity, format version, input fingerprints, evidence time range, **evidence class**, and **world**. **Worlds defined:** `live` (real venue clocks/quotes; demo & paper are world=live via account role), `replay` (data-driven injected clock over recorded history, real UTC instants, implementable today), **`simulated` (synthetic data — RESERVED BUT UNUSABLE IN V1: writing `world = simulated` into governed evidence is a `policy rejection` refusal until the backtesting sitting defines simulated-time typing)**. Namespace rule: non-live world may never write into live evidence namespace; factory sandboxes carry `provenance = sandbox`.
- **AD-13** Measure-then-budget performance (L146): **no invented performance numbers**; every component ships a benchmark harness measuring speed + peak memory at a load ladder in framework-native units; ~40-bot node scenario (+10/100/200 marks) as sizing reference; first measurements = fingerprinted baselines scoped to (OS, CPU-class); regression thresholds as multiple of variance; core imports <1s; **benchmark/test data generated at runtime or controlled fixtures — never shipped as product; synthetic data stresses infrastructure, never validates edge (L6/L20).**
- **AD-14** Loud failure, traceable behavior (L152): refusals never swallowed; `correlation_id` across boundaries; `health()` per component; logs = ISO-8601 Z display, journals = int64 ns evidence.
- **AD-15** Concurrency stance (L158): QMF values immutable; purity binds core/indicators/structure; one-writer-per-stream for stateful resource owners; QMF never spawns threads — the application owns all concurrency; async only at venue network edge.
- **AD-16** Registry records and lineage (L164): per-kind versioned schemas + tiny common header; stable id derived from `fp1`; lineage lives only in append-only typed edge records (incl. `continues-performance`, `carries-ledger`, `enacts`, `branches-from`); `supersedes` is linear; JSONL edge files; no database server.
- **AD-17** Multiplicity at every layer (L170): Bot ⊇ 1+ confluences ⊇ 1+ levels/triggers/confirmations; no hardcoded cardinality-one; Bot identity = content; Bot↔Book↔account binding is a separate dated record.
- **AD-18** Promotion record skeleton (L176): reserved promotion-occurrence card; human-only signer; plain-words summary is an identity field; "signing" = recorded operator approval attesting an `fp1` string.
- **AD-19** Data rooms, stores, bitemporal law (L182): **seven room-roles instantiated PER WORLD (AD-12); a read that crosses worlds is a `policy rejection` refusal**; Parquet/DuckDB/SQLite/JSONL behind QMF contracts; only raw-archive + journal are evidence-bearing; every external fact carries event-time/known-at/source/revision.
- **AD-20** Migrations, retention, backup (L188): preflight→backup→dry-run→migrate→verify; raw + lineage kept forever; QMF provides backup/restore/verify primitives, schedule is app/ops-owned.
- **AD-21** Splits, journal events, doors to outside (L194): **dataset splits are fingerprinted, time-ordered, non-overlapping manifests, each pinning one calendar identity**; records partition into splits by knowledge time; purge/embargo widths required; **12-month seal is a no-peek `policy rejection` at every qmf-data read boundary, independent of the deferred GAP-0016/0017 gates**; journal = N writer-scoped streams, seven event types (decision, order, fill, risk transition, promotion, data quality, control action); tick sources separately identified (Dukascopy history vs broker feed).
- **AD-22** Indicator protocol and series vocabulary (L200): Bar/Tick/Quote/**BarSpec** defined in core; BarSpec replaces "timeframe"; bulk form pinned (memoryview of int64 bytes + presence map, no NaN/sentinels); identity = entire declared configuration; batch/streaming equality law; warm-up = integer observation count; extensions via explicit registration; graduation path from plain-Python research.
- **AD-23** Canonical arithmetic: pinned references, upgrades gated (L220): wrap-not-reimplement TA-Lib (0.7.1) where it implements a formula; QMX impl canonical elsewhere; upgrades gated by comparison suite; no governed producer re-implements another's arithmetic.
- **AD-24** Light vs heavy: budget-declared, benchmark-policed (L231): light iff declared AND benchmark-proven (latency rung, bounded state, bounded window/anchor-reset, synchronous availability); **until the live-path rung has a recorded baseline, every config is heavy by default and a light claim is refused**; heavy runs off the trading path; verdict never enters identity.
- **AD-25** Causal structure lifecycle (L242): structure family = a chart-object type never a strategy; object minted once at observation with anchor span + observed-at (earliest causally-derivable instant); lifecycle records append-only; **emission invariant `anchor.start ≤ anchor.end ≤ observed-at ≤ confirmed-at ≤ invalidated-at` + observed-at ≥ max input evidence-time — a cheap look-ahead guard that binds NOW, independent of the deferred GAP-0016 gate**; precise-rule bar; evidence class in the label.
- **AD-26** Venue secret lifecycle (L260): components handle opaque secret references never values; `SecretRef`/`SecretValue` in core; connection manager is the sole holder of secret values; rotation = one-writer stream; tested compromise drill; sandboxes never hold live secrets.
- **AD-27** Venue commands and the uncertainty law (L272): command stream = (VenueId, account); **five command kinds** (`place_order`, `cancel_order`, `close_position`, `close_all`, `amend_protection`); **four-outcome law** (`accepted-by-venue | rejected-by-venue | denied-locally | UNKNOWN`); UNKNOWN blocks the stream until `resolve_unknown`; recording precedes interpretation; order state is a read-time fold; no retry; reconciliation vocabulary `reconciled | drift | unknown | out-of-lookback`.
- **AD-28** Venue adapter contract and capability discovery (L285): one neutral port, four contracts (CT-18 capability, CT-19 command, CT-20 event+reconciliation, CT-21 secret/session); injected-sink wiring; **market data enters as CT-10 source observations through CT-15 intake** (no fifth contract); capability declaration (static) + venue-observation profile (measured-at-connection, verify-or-refuse); foreign floats verbatim; `converted_by = venue` provenance; error-mapping row shape pinned.
- **AD-29** Book, BMS, and the binding chain (L301): authority order bot→book→BMS→operator; one BMS per account serving many Books; **the risk domain is the binding `(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)`, aligned with AD-27's command stream**; **`world` is a constant (`live`) for every V1 binding — a replay of a binding mints a different binding identity, and AD-19 refuses cross-world reads, so replay-derived and live evidence are DELIBERATELY INCOMPARABLE BY BINDING; the backtesting sitting inherits a stated position, not an accident** (L310); bind-time capability check.
- **AD-30** Templates as configuration artifacts; git-logic versioning (L330): Book/BMS template = structured config artifact; every variable declares `ui-editable | uneditable` + `admission_impact` + unit-kind; numbers inline and identity-bearing; version graph via `branches-from`; `pending(<gap id>)` slots pass registration and block live binding.
- **AD-31** Risk record kinds and per-entity journals (L346): entity journals (Book/BMS/per-bot) are read-time projections over writer-scoped streams; risk-authored vs venue-authored event classes; paper/live separated by construction; risk-domain writer unit `(machine, risk role, binding)`.
- **AD-32** Book/BMS admission: linters, shakedown, one signature (L359): three layers (machine linters at registration; **technical shakedown on demo/paper — proves the machinery works, proves NOTHING about edge**; one operator signature); **no trial period/probation/paper-performance gate**; `admission_bar` is a set; **no paper role may gate live money**; blank threshold blocks live money.
- **AD-33** Exit ownership: Book policy, Bot proposals, typed closes (L374): CT-23 is the risk-evaluation door; `requested_r` is Book-resolved not bot-supplied; Book owns exit policy; V1 exit kinds `close_full` + `tighten_protective_stop` (**`close_partial` is not a V1 kind — partial exit is `unsupported capability`**); venue-resident stop at placement; typed close-reason taxonomy; whole-trade attribution to the opening Bot in R.
- **AD-34** `amend_protection`: the fifth venue command (L387): risk-non-increasing protection amendment, never emulated by cancel-then-place; amend atomicity UNDOCUMENTED → measured-at-connection verify-or-refuse; venue-managed trailing = a declared capability; V1 dynamic SL/TP = move-to-breakeven ratchet only.
- **AD-35** Paper mode (L398): paper is a Book-level mode (`LIVE | PAPER`), no Bot twins; per-seat routing on the seat record; paper is a standing evidence state; paper money frozen, reset mints a new epoch; **comparison cohort rule — decay judged in R; `cohort_key` must match (Bot id, Book id + template version, `world`, sensing feed, producer fingerprints, calendar id, instrument id, active-control set, active-window set); a decay cohort read is an explicitly permitted cross-role read within `world = live`**.
- **AD-36** Control actions: kill switch, kill line, flatten authority (L413): kill switch (global, stops all new trading live+paper, human de-escalates) vs kill line (per-Book capital floor, auto-flattens); **exit-preservation invariant — no control may block a risk-reducing act; blocking half is entries-only**; CT-30 contract; flatten authority assigned; standing intent (journaled before dispatch, read-time fold, re-decided not retried, never time-expires); **fold contract stated once for every read-time fold** (stream, ordering key, knowledge-time bound, equal-instant disposition; no fold on the trading path may refuse — returns most restrictive).
- **AD-37** Same-tick priority (L431): priority per (VenueId, account) stream, one arbitration point; **cross-stream ordering is a declared non-guarantee**; Tier1 venue-resident actions outside the ordering; Tier2 node ranks 0 operator / 1 protection / 2 forced flats / 3 fast invalidation / 4 ordinary exits; ranks total-ordered, uniqueness at Layer 1; collapse + conflict rules.
- **AD-38** Protection windows: news, dead zone, handover buffers (L445): one control-window contract; window = two instants never an offset; three kinds `news | daily_dead_zone | session_handover_buffer`, calendar-derived; widths are UI-editable variables with no spine value; entries-only effect (never blocks exits/recording); widen-never-shrink forward-only; fail closed; instrument scope declared via currency-exposure records never parsed.
- **AD-39** Spread Quality Sensor V1 (L462): SQS is a CT-16 configured producer; V1 formula = historical avg spread / current spread; baseline is a fingerprinted input artifact with refit-series identity; hard-block + hysteresis + outlier guard + conservative sentinel; every parameter UI-editable with no spine value; sensor computes, Book door decides; V1 blocks only, never shrinks size.
- **AD-40** R, numeraire, capital, and the dimensional law (L479): R = one relationship, three typed faces; `Position`/`Order` anchored as core shared nouns (venue position vs **virtual/Book position** = fold over fills by command identity); frozen at admission (one re-basing only, on partial entry fill); **numeraire USD system-wide in V1, non-USD binding = `policy rejection` until rate source ratified**; the dimensional law + closed unit-kind vocabulary; sizing ladder shape ratified (values/evaluation are node's).
- **AD-41** Stop-out, bench counter, performance evidence (L497): exit record CT-29 one per virtual-position close; bench counts qualifying loss exits (`realized_r ≤ −q`); bench counter is a read-time fold over exit-record stream, stream boundary = binding epoch; `venue_liquidation` vs QMX protective-stop sense; performance-result container CT-32 (population by binding-record fingerprints, declared period + knowledge-time bound, suppression + veto accounting); **alpha decay ships as evidence primitives only, the mathematics is deferred; measurement never acts, it publishes**.

## Contract (CT-*) index

The frontmatter binds CT-01 … CT-32 (no CT-08 by number is separately defined; AD-18 is "CT-08-adjacent"). Mapping to the AD that owns/defines each:

| CT | Subject | Owned/defined at |
| --- | --- | --- |
| CT-01 | Exact money (Money/Price/Quantity) | AD-7 (also AD-40) |
| CT-02 | Exact time | AD-8 |
| CT-03 | Instrument/venue/account identity | AD-9 |
| CT-04 | Typed refusals | AD-11 |
| CT-05 | Fingerprints + result label + worlds | AD-10, AD-12 |
| CT-06 | Registry structure-object record kind | AD-16 (also AD-25) |
| CT-07 | Registry lifecycle/comparison record kind | AD-16 (also AD-25) |
| CT-08 | (promotion-adjacent, not separately numbered in body) | AD-18 "CT-08-adjacent" |
| CT-09 | Registry lineage/edge records | AD-16 |
| CT-10 | Market-data / source observation store | AD-19, AD-28 (market data), AD-38, AD-39 |
| CT-11 | Append-store / data-room contract | AD-19, AD-20 |
| CT-12 | Dataset split manifests | AD-21 |
| CT-13 | Journal streams / event types | AD-21 (also AD-31) |
| CT-14 | Backup/restore/verify primitive | AD-20 |
| CT-15 | Source-adapter intake | AD-21, AD-28 (market-data intake) |
| CT-16 | Indicator protocol + series vocabulary | AD-22, AD-23, AD-24, AD-39 (SQS) |
| CT-17 | Causal structure lifecycle | AD-23, AD-24, AD-25 |
| CT-18 | Venue capability declaration | AD-28 (also AD-27, AD-34) |
| CT-19 | Venue command contract | AD-27, AD-28, AD-34 |
| CT-20 | Venue event + reconciliation contract | AD-27, AD-28 |
| CT-21 | Secret / session contract | AD-26, AD-28 |
| CT-22 | Book definition | AD-29, AD-30, AD-32, AD-33, AD-37, AD-40 |
| CT-23 | Risk-evaluation door (bot→Book intent) | AD-33 (also AD-29, AD-37, AD-39, AD-40) |
| CT-24 | Binding transition record | AD-29, AD-31, AD-35 |
| CT-25 | Journal event mapping / interaction record | AD-31 (also AD-25 lifecycle) |
| CT-26 | Migration/retention record | AD-20 |
| CT-27 | BMS definition | AD-29, AD-30, AD-32, AD-37 |
| CT-28 | Book binding record | AD-29, AD-31, AD-32, AD-35 |
| CT-29 | Exit record | AD-31, AD-33, AD-41 |
| CT-30 | Control-action record | AD-31, AD-36, AD-37 |
| CT-31 | Control-window record | AD-31, AD-38 |
| CT-32 | Performance-result container | AD-31, AD-41 |

## Inherited-invariant rows (verbatim topics, §Inherited Invariants L27–40)

1. Build-our-own boundary: QMX-owned contracts implemented locally; no foreign platform contract — DEC-0013 — binds AD-6 prohibited tier; paradigm choice.
2. Definitions-only qmf-core: no broker, loop, backtest, downloads — DEC-0022 — binds AD-6 zero-dep rule; AD-8 protocol-only clock. **(Note for backtesting: "no backtest in core" is an explicit inherited invariant.)**
3. Five libraries + two modules roster — DEC-0024 / spec §2b — binds AD-2 package list.
4. Don't-box-in: open toolbox, strictness only at harness + live-money gate — DEC-0011 — binds AD-6/AD-8/AD-9 neutrality; note in AD-3.
5. No futures/options ever; nouns must not preclude stocks/crypto — DEC-0015 — binds AD-8/AD-9/AD-7.
6. Framework-vs-node split: kill switch, news windows, SL/TP, Book runtime = node — circle-back ruling 2026-08-19 — binds AD-8 seams; AD-13 scaling; AD-33..AD-39 carry contracts never runtime.
7. Authority order (constitutional hierarchy): bot → book → BMS → operator — Constitution L1 — binds AD-29/AD-36/AD-37.
8. Corpus precedence for risk/position-sizing/live-trading — Operator standing ruling 2026-08-20 — GitBook + trading-node docs authoritative; QMX-discussion **barred as a risk/sizing source**; non-risk structural definitions citable only under a named at-point-of-use exemption (AD-38 dead-zone is the single such citation) — binds AD-33/37/38/40/41, the PRD, documentation factory, and every downstream sitting.
9. Configurable means UI-editable at platform level — Operator standing rule 2026-08-20 — binds AD-30/34/38/39/41.
10. Code legible to humans AND agents — L5 — binds AD-3.
11. **No shipped mock market data, fake Bots, or default strategies; synthetic data stresses, never validates edge — L6, L20 — binds AD-13 benchmark data rule.** (Directly load-bearing for a backtester: synthetic/simulated data may not validate edge.)
12. Every component ships executable tests AND reference usage demonstrating its public contract — L27 — binds AD-3.

## Everything touching backtesting / simulation / worlds / sim-time / benchmarks / quality gates / extensions

### World labels & sim-time typing (the central hooks)
- **AD-12 (L143):** `simulated` world is **reserved but unusable in V1**; `world = simulated` into governed evidence is a `policy rejection` **until the backtesting sitting defines simulated-time typing**. `replay` (data-driven injected clock over recorded history, real UTC instants) **is implementable today**. Non-live worlds may never write into the live evidence namespace; storage separation (not identity distinctness) delivers world separation.
- **AD-8 (L103):** clock access is a core protocol; **replay injects a data-driven clock**; nothing below the composition root reads the system clock. Clock injection seam diagram L535–545 shows `real system clock` and `replay clock (pure function of data cursor)` both injected into the core `Clock` protocol.
- **AD-19 (L186):** seven rooms **instantiated per world**; a cross-world read is a `policy rejection` refusal.
- **AD-29 (L310):** `world` is a constant `live` for every V1 binding; **a replay of a binding mints a different binding identity; replay-derived and live evidence are deliberately incomparable by binding — the backtesting sitting inherits a stated position, not an accident**; `world` is carried in AD-35's cohort key.
- **AD-35 (L410):** `world` is a mandatory `cohort_key` component; a judgment spanning mismatched cohorts is a `policy rejection`.

### Backtesting explicitly deferred (§Deferred L599–632, verbatim topics below)
- **Look-ahead registration gate + attempt counter (GAP-0016, GAP-0017)** — "Operator-deferred to the backtesting sitting, consequence accepted: artifacts registered before then carry no causality evidence."
- **Backtesting (GAP-0048, ticket 008) incl. simulated-time typing (unlocks `world = simulated`) and backtest-mimics-live idea** — "Own sitting; operator not ready."
- **Admission-bar threshold values and the measures behind them** — "Backtesting sitting; AD-32's container ships complete with `not yet ruled` thresholds, which block live binding until filled."
- **SR* / search-quality threshold (GAP-0049)** — "Deferred with backtesting."
- **Promotion evidence checklist** — "causality ← backtesting."
- **Alpha-decay mathematics** — deferred; AD-41 mints evidence primitives now.

### Look-ahead guards that already bind NOW (independent of the deferred gate)
- **AD-25 emission invariant (L249):** `anchor.start ≤ anchor.end ≤ observed-at ≤ confirmed-at ≤ invalidated-at` and observed-at ≥ max input evidence-time — "cheap look-ahead guard binds now, independent of the deferred GAP-0016 gate."
- **AD-21 (L198):** the **12-month no-peek seal is enforced now** as a `policy rejection` at every qmf-data read boundary, **independent of the deferred GAP-0016/0017 gates**; dataset splits are fingerprinted, non-overlapping, calendar-pinned manifests partitioned by knowledge time with required purge/embargo widths.
- **AD-22 (L213):** `provisional` samples never enter governed evidence; as-of last-known-at-or-before is the only permitted governed alignment (forward-fill/interpolation across the evaluation instant is `policy rejection`).

### Benchmarks — AD-13 (quality/perf gate)
- No invented performance numbers; benchmark harness (speed + peak memory) at a load ladder in framework-native units; ~40-bot scenario + 10/100/200 marks; fingerprinted baselines scoped to (OS, CPU-class); regression beyond declared threshold fails the merge gate; core import <1s. **Benchmark/test data generated at runtime or held as controlled fixtures — never shipped as product artifacts; synthetic data stresses infrastructure, never validates edge.**

### Quality gates — AD-4 (+AD-3)
- Tier1 `poe check` per work unit; Tier2 `poe check-integration` (+ integration + contract tests, each package isolated) on landing to integration; Tier3 `poe check-release` (+ build + clean-install smoke on both OSes) on ship. Contract test defined. AD-3: ruff/pyright-strict/pytest, coverage floor 80% (100% branch on CT-01/CT-02).

### Extension shapes / don't-box-in (open toolbox)
- **AD-2 (L56):** extensions (calendar, indicator, structure) are **separate versioned packages outside the roster, own SemVer ladder**, discovery by explicit registration at the composition root, never ambient scanning.
- **AD-22 (L216):** custom indicators authorable as plain Python outside governed evidence always; to enter governed evidence they conform to CT-16 as extensions; **graduation path** from a plain-Python experiment with a lineage edge.
- **AD-25 (L257):** operator-authored from-scratch structure families are first-class peers; family authoring via the AD-22 extension shape is the primary use case.
- **Inherited "Don't-box-in" (DEC-0011):** open toolbox; strictness only at harness + live-money gate; governs consumers, not QMF's own source.

## Collision flags — where a "QMX backtesting CLI" proposal could collide with the spine

1. **AD-12 `world = simulated` is a hard `policy rejection` until the backtesting sitting rules sim-time typing.** A CLI that writes simulated-data results into *governed evidence* is illegal today. A CLI operating in `world = replay` (real recorded UTC history, injected data-driven clock) is legal now — **replay ≠ simulated**; the CLI must pick the right world and must not conflate them.
2. **Paradigm boundary (L21) + inherited DEC-0022 ("definitions-only qmf-core: no backtest").** A backtester is an **application built with QMF, not a QMF package**. A proposal that adds a `qmf-backtest` package to the roster, or puts backtest logic in core/any library, collides with AD-2's seven-package roster and the zero-dep/no-backtest core rule. Backtest workspaces are named as out-of-scope applications.
3. **AD-13 + Inherited L6/L20: synthetic data stresses infrastructure, never validates edge; no shipped mock market data.** A CLI that ships or generates synthetic price data and reports it as strategy/edge validation collides head-on. Backtests must run on recorded evidence (replay), not synthetic series, for any edge claim.
4. **AD-19 per-world room instantiation + cross-world read = `policy rejection`.** A CLI that reads live evidence and backtest/replay evidence in one query, or writes backtest output into the live namespace, collides. Storage separation is mandatory.
5. **AD-29: replay bindings mint a different binding identity and are deliberately incomparable-by-binding to live.** A CLI presenting backtest P&L as directly comparable to a live binding's ledger collides; comparison is legal only through AD-35's `cohort_key` in R, never by binding.
6. **AD-21 12-month seal + split manifests (enforced now).** A backtesting CLI that reads sealed/held-out data, or runs over data without a fingerprinted non-overlapping split manifest with declared purge/embargo widths, collides — even before GAP-0016/0017 land. Research-door reads are split-governed.
7. **AD-25 / AD-22 look-ahead guards.** A CLI feeding structure/indicator evidence must honor observed-at ≥ input evidence-time and the as-of-last-known alignment rule; a naive backtester using future bars collides (`invalid input` / `policy rejection`).
8. **AD-11 typed refusals + AD-14 loud failure.** A CLI must surface refusals as typed results, not swallow them; and AD-15 — QMF never spawns concurrency, so a CLI is the *application* that owns the loop/clock/cursor.
9. **AD-32 admission-bar thresholds are deferred to the backtesting sitting; blank blocks live money.** A CLI that hard-codes or infers admission thresholds from backtest output collides with "no paper/backtest-performance gate to live money" (AD-32) and the deferred-threshold posture.
10. **Banned vocabulary (Conventions L551):** "kernel", "plugins", **"engine" for backtesting**, and "exam" are banned. A CLI named/branded as a "backtesting engine" collides with the naming convention — use another term.
11. **GAP-0048 says "operator not ready" for the backtesting sitting.** Any CLI proposal presumes an unratified sitting; it must be framed as replay-tooling within today's rules, or explicitly flagged as pre-empting a deferred sitting.

## Notes / ABSENT
- CT-08 has no standalone numbered definition in the body — AD-18 is labelled "CT-08-adjacent" (L178). The frontmatter `binds` list (L11) does **not** include CT-08; it lists CT-01..CT-07, CT-09..CT-32 (CT-08 ABSENT from the bind list).
- No AD beyond AD-41 exists; the task's "AD-1..AD-41" is the complete set (no AD-42+). ABSENT: any AD numbered above 41.
- The spine names no backtesting AD; all backtesting substance is in the Deferred table + the reserved `world = simulated` hook.
