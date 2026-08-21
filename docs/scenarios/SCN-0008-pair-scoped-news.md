---
id: SCN-0008
title: News Windows Block Entries by Instrument Scope, Live and Paper
type: scenario
status: provisional
component: COMP-QMF-RISK
depends_on: [COMP-QMF-CORE, COMP-QMF-DATA]
decisions: [DEC-0152, DEC-0157, DEC-0156, DEC-0150, DEC-0119]
sources: [docs/components/qmf-risk.md, docs/contracts/ct-31-control-window.yaml, docs/contracts/ct-10-source-observation.yaml, docs/contracts/ct-23-risk-evaluation.yaml, docs/registry/variables.yaml, _docwork/ledger.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# SCN-0008: News Windows Block Entries by Instrument Scope, Live and Paper

This scenario pins the ratified protection-window mechanism for news: a window blocks new entries on the instruments in scope — live and paper entries alike — resolves that scope through declared currency-exposure records rather than by parsing a symbol, journals every blocked decision on the veto path, widens but never shrinks, and fails closed. Execution status: **ratified design; implementation is authorized only through the factory pipeline, never from these docs alone.** [DEC-0152]

One control-window contract (CT-31) serves every no-trade band, and this ruling **supersedes the dated 2026-08-18 pair-scoped ruling** (*"while blocked, bots may continue in paper mode so alpha-decay data keeps flowing"*): the instrument scoping survives, re-mechanised through per-instrument currency-exposure records, while the keep-paper-flowing lead is overridden — a news window blocks live and paper entries alike. [DEC-0152]

## Given

A Book enables the `news` window kind (kinds are addable never redefined; the three ratified kinds are `news`, `daily_dead_zone`, and `session_handover_buffer`, and a Book declares which it enables). A CT-31 window record carries the window as **two instants** (never an offset — an offset stored instead of bounds would make a record's meaning depend on a policy version and break replay), a resolved instrument scope, the window kind, a reason class, a format version, and — where it derives from a feed — the external-fact quadruple `(source, source-native event id, revision, known-at)` from the news-calendar recorder's ratified idempotent `(source, source-native id, revision)` intake. [DEC-0152] [DEC-0119]

**Instrument scope is declared, never parsed.** It resolves through dated per-instrument currency-exposure records (instrument-metadata records populated from venue-declared metadata where it exists, operator-declarable and correctable otherwise) — a set of exposures, so a non-pair instrument is expressible; reading a currency out of a symbol is prohibited. Widths and buffers are configurable UI-editable variables with **no spine value**: `registry:news_blackout_before` and `registry:news_blackout_after` carry the lead and trailing widths as configuration the operator sets between sessions, and the plus-or-minus-15-minute news buffer is **on record as withdrawn** (recorded evidence, non-authoritative). [DEC-0152] [DEC-0157]

## When

At a decision instant a news window of an enabled kind is in force over one instrument the bot trades, and the bot proposes an entry on that instrument (and, separately, an exit on an open position).

## Then

**The window blocks the new entry, and nothing else.** It blocks new entries on the instruments in scope — **live and paper entries alike** — and never blocks an exit, a protection amendment, a protection action, or observation: recording is not trading. The proposed exit is unaffected, because blocking exits would trap risk behind the very window meant to reduce it; a window that closes open positions exists only as a Book declaration entering arbitration at rank 2 as `window_forced_flat` (`registry:window_forced_flat`), and declaring none is the V1 posture. [DEC-0152] [DEC-0150]

**The blocked decision is journaled on the veto path** — a `decision` event carrying the refusing-door identity, the would-have-been action fingerprint, and the controlling window's fingerprint. A window is a door-class refusal (it refuses intents before authorization, on the veto path, never the suppression path), so decay sensing keeps its data points without a trade being placed. [DEC-0152] [DEC-0150]

**Scope resolution is fail-closed and per-instrument.** A missing currency-exposure record means the instrument is **treated as affected and blocked** while a window of an enabled kind is in force, the absence journaled as `data quality` and raising an alarm — a permanently blocked instrument is otherwise indistinguishable from a quiet one. A **multi-instrument bot is blocked only on the instruments in scope**; its other instruments keep trading. [DEC-0152]

**Widen-never-shrink, forward-only.** A later revision may pull a start earlier for instants not yet passed or push an end later; it may never narrow, cancel, or retro-invalidate a window that has had effect. Enforcement is at read time, never at intake (intake keeps provider evidence verbatim and appends corrections): the effective window at decision instant T is the union of the bounds of every revision known at T, with any bound already passed frozen, so replay resolves the same window. Decisions already taken under an older revision stand and are tagged with it. [DEC-0152]

**Fail closed, no live skip.** A failed calendar refresh, unknown coverage, or an uncertain window blocks; there is no live skip button. The operator's control is upstream configuration exercised between sessions, and a standing per-instrument exemption is a dated fingerprinted record consumed at compile time, never a click. Provider impact labels are stored verbatim; QMX mints no severity scale in V1, and severity-to-window is a declared node mapping, not QMF surface. [DEC-0152] [DEC-0156]

**Evidence stays comparable.** Evidence produced while a window was in force links to the window record by a typed edge, and the active protection-window set enters the decay cohort key, so a news-heavy period is never compared against a quiet one and read as alpha decay. [DEC-0152]

## Worked numbers

No before/after duration is authorized as a constant. `registry:news_blackout_before` and `registry:news_blackout_after` are configurable UI-editable variables with **no spine value**; a window record is carried as two instants, never as these offsets, which exist only as configuration the operator sets between sessions. The withdrawn plus-or-minus-15-minute news buffer is recorded evidence, non-authoritative, and never a ratified constant. An executable fixture reads the CT-31 window record (`window_bounds`, `window_kind`, `instrument_scope`, `feed_quadruple`, `reason_class`) and the resolved currency-exposure records, computing the effective window at a decision instant as the widen-never-shrink read-time fold — never from scenario-local literals. The recorder's intake key `(source, source-native id, revision)` is ratified per DEC-0119; the disagreeing `daily_dead_zone` widths (`registry:daily_dead_zone_width`) are recorded, never merged, and cited for the window definition only under the named corpus-precedence exemption (DEC-0156).
