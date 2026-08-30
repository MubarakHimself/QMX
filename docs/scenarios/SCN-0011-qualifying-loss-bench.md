---
id: SCN-0011
title: A Day of Exits Benches a Seat by Qualifying-Loss Count
type: scenario
status: ratified
component: COMP-QMF-RISK
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA]
decisions: [DEC-0155, DEC-0149, DEC-0143, DEC-0147, DEC-0154, DEC-0157, DEC-0158, DEC-0208, DEC-0209]
sources: [docs/components/qmf-risk.md, docs/components/trading-node.md, docs/contracts/ct-29-exit-record.yaml, docs/contracts/ct-23-risk-evaluation.yaml, docs/contracts/ct-24-book-mode.yaml, docs/contracts/ct-30-control-action.yaml, docs/registry/variables.yaml, _docwork/ledger.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md, _bmad-output/planning-artifacts/architecture/architecture-NODE-2026-08-28/ARCHITECTURE-SPINE.md, docs/decisions/ADR-0019-trading-node.md]
generated: 2026-08-20
verified: 2026-08-29
stale_after: 30d
---

# SCN-0011: A Day of Exits Benches a Seat by Qualifying-Loss Count

This scenario pins the bench mechanism end to end: over one day a bot's four virtual-position closes are recorded as CT-29 exit records, the qualifying-loss predicate `realized_r <= -q` counts exactly the two qualifying losses and ignores the breakeven and the scratch, the read-time bench fold crosses the per-family threshold inside the binding epoch, the seat flips `active -> benched` and routes to the paired demo target while the Book stays `LIVE`, and the seat's next-open reset clears the benched state as a clocked CT-24 transition. Execution status: **ratified design; implementation is authorized only through the factory pipeline, never from these docs alone.** [DEC-0155]

## Given

A Book is `LIVE` with a bound Bot whose seat is `active` on the Bot-Book binding. Seat state is `active | benched`, Book mode is `LIVE | PAPER`, binding state is `live | paper | stood-down` — three vocabularies never interchanged; a seat-state write never writes a Book-mode row, and `ADMITTED` is not a state at all (it is the absence of a binding). [DEC-0155] [DEC-0149]

The Book declares its bench inputs in its template. The bench predicate's loss threshold is `q` (`registry:qualifying_loss_threshold`, an `r-multiple`, configurable UI-editable, no spine value); the bench count is `registry:bench_consecutive_loss_threshold` (a `count`, keyed per bot or bot family in `leash_grammar`, configurable UI-editable, no spine value — the recorded value of two for a scalper is evidence, non-authoritative). The recorded defaults are honest evidence attached to the operator's *"we only count losses at negative 1R"* ruling, never ratified constants. [DEC-0155] [DEC-0157]

Every virtual (Book) position close mints **exactly one CT-29 exit record** — the Book-side noun, not the venue position, or a netted account produces fewer records than admissions and every fold under-counts. Each record carries the frozen `original_risk_distance` and `original_risk_amount` (so `r_multiple` recomputes forever), the fill references, `realized_pnl`, an identity-bearing `cost_components` set, a single-sourced `realized_r` net of exactly that set, the typed `close_reason`, `mechanism` and `outcome` as **separate fields**, the `closing_authority` plus `arbitration_record_ref`, the `result_label` with account-binding role, and the `loss_predicate_format_version`. [DEC-0155] [DEC-0154]

The bench counter is a **read-time fold** over the exit-record stream, never a mutable counter; its stream boundary is the **binding epoch** (a new epoch starts the count at zero unless a signed `carries-ledger` edge spans it), and its knowledge-time bound is the last exit record persisted and journaled at the intent-mint instant. **Recording precedes interpretation:** a fill closing a virtual position must have its CT-29 record persisted and journaled before any later intent on the same `(Book, Bot)` seat is minted, else that intent refuses (`stale evidence`) — otherwise the (N+1)th entry races the Nth exit record and the leash misses the crossing it exists to catch. [DEC-0155] [DEC-0143] [DEC-0158]

## When

Over one trading day the bot opens and closes four virtual positions in sequence: a breakeven, a `-0.15R` scratch, a `-1.02R` protective-stop fill, and a `-1.2R` hold-time forced flat.

## Then

Each close mints one CT-29 exit record, and each records mechanism and outcome as separate fields so no rule is ever written over the mechanism alone:

1. **Breakeven.** `mechanism = protective_stop_fill` after a move-to-breakeven ratchet (`registry:breakeven_ratchet_trigger` / `registry:breakeven_ratchet_offset`); `outcome` a breakeven. `realized_pnl` is approximately zero gross and `realized_r` is marginally negative once `cost_components` are netted. A **breakeven never counts under any `q`** and is recorded as its own metric (a clustering watch), which keeps the ruling reversible from evidence. [DEC-0155] [DEC-0147]
2. **Scratch.** `mechanism = bot_intent` — a fast-invalidation `close_full` the Bot proposed through the CT-23 door and the Book resolved and executed; `outcome` a `-0.15R` loss. `realized_r = -0.15R` fails `realized_r <= -q`, so it **does not count by default** — a `-0.15R` scratch is not the damage a leash exists to stop, and two of them must not bench a scalper. [DEC-0155] [DEC-0147]
3. **Protective-stop full loss.** `mechanism = protective_stop_fill` from the venue-resident stop attached at entry; `outcome` a full original loss. `realized_r` nets to `-1.02R` — a hair beyond `-1R` once commission and financing in `cost_components` are subtracted. `realized_r <= -q` holds, so this is a **qualifying loss exit**. The close is venue-authored: `closing_authority = venue` carrying the venue observation reference in place of a node `arbitration_record_ref`. [DEC-0155] [DEC-0154]
4. **Hold-time forced flat.** `mechanism = hold_time_force_flat` — the Book-declared force-flat rule fired because the position age exceeded its declared `Duration` (`registry:hold_time_force_flat_trigger`), a rung entering arbitration at rank 2; `outcome` a `-1.2R` loss. `closing_authority = book_policy` with an `arbitration_record_ref`. `realized_r = -1.2R <= -q`, so this is a **qualifying loss exit** — a forced flat counts only because it realized a qualifying loss; the system's own protection never benches the bot merely for the act of protecting it. [DEC-0155] [DEC-0147] [DEC-0143]

**Whole-trade attribution holds throughout:** the full realized R of every virtual position credits the Bot that opened it, regardless of who closed it — the venue-resident stop and the Book's forced flat both credit the opening bot, and reports partition by `close_reason` so the bot's edge and what our own gates cost read as one dataset two ways. [DEC-0147]

**The read-time bench fold now crosses the threshold.** Exits 3 and 4 are two `qualifying_loss_exit` closes in the binding epoch; the breakeven and the scratch are recorded but do not increment the qualifying-loss fold. The fold reaches `registry:bench_consecutive_loss_threshold`. The bench fold is **one governed producer, published once and consumed by the door** — measurement never acts, it publishes, and the authority to bench belongs to the Book door. [DEC-0155]

**The Book door benches the seat.** Seat state flips `active -> benched` on the Bot-Book binding. Because a benched seat is a **capital/authority** reason, its disposition is `routes-to-paper`: the benched seat routes to the paired demo target **through its seat record's execution target while the Book stays `LIVE`**. The binding is not re-minted — `role` rides the execution-target record, not the binding tuple — and the Book-mode vocabulary is untouched, because `BENCHED` is a bot-seat word only and never a Book mode. The bench event remains on the record after any later reset. [DEC-0155] [DEC-0149] [DEC-0143]

**The next-open reset is a clocked CT-24 transition.** The benched seat's return is automatic only because its clearing cause is clocked and mechanical — the seat's next-open bench reset. That reset mints a **CT-24 transition (a clocked mechanical clear), never a CT-30 `resume`**, and carries no operator signature because it touches no real money; the historical bench event stays on the record and is never erased. The qualifying-loss fold's stream boundary remains the binding epoch, so the reset clears the seat state without discarding the recorded exit history, and the exact re-arming arithmetic across a fresh session is the bench fold's pinned governed-producer contract — configurable, never a spine constant. [DEC-0155] [DEC-0149] [DEC-0143]

## Worked numbers

The predicate is `realized_r <= -q`. This fixture uses `q = 1R` (`registry:qualifying_loss_threshold`) and `registry:bench_consecutive_loss_threshold = 2` purely as illustrative inputs — both are configurable UI-editable variables with **no spine value**, and the recorded defaults (`q` approximately one R; two for a scalper) are non-authoritative evidence, never restated as ratified constants.

The four exits' `realized_r` values are scenario fixture inputs, each net of that record's declared `cost_components` and derived from the record's own frozen `original_risk_amount` under the pinned `realized_r` formula (a declared derived display of the record's frozen fields, never a second governed implementation of the division):

| Exit | `mechanism` | `outcome` | `realized_r` (net) | `realized_r <= -q`? | Bench fold |
| --- | --- | --- | --- | --- | --- |
| 1 | `protective_stop_fill` (breakeven ratchet) | breakeven | approximately `0` | no — breakeven never counts | not counted, clustering-watch metric |
| 2 | `bot_intent` (`close_full`) | `-0.15R` scratch | `-0.15R` | no (`-0.15 > -1`) | not counted (scratch) |
| 3 | `protective_stop_fill` (venue-resident) | full loss | `-1.02R` | yes (`-1.02 <= -1`) | qualifying loss exit #1 |
| 4 | `hold_time_force_flat` | `-1.2R` loss | `-1.2R` | yes (`-1.2 <= -1`) | qualifying loss exit #2 |

Qualifying-loss count in the binding epoch = 2 = `registry:bench_consecutive_loss_threshold` -> the fold publishes the crossing and the door benches the seat. If `registry:qualifying_loss_threshold` or `registry:bench_consecutive_loss_threshold` changes, recompute from the CT-29 exit-record stream, never from these literals; the fixture depends on both keys plus `registry:hold_time_force_flat_trigger`, `registry:breakeven_ratchet_trigger`, and `registry:breakeven_ratchet_offset`.

## Wired by the trading node (2026-08-29)

This golden scenario stays **defined-unwired** until the trading node (COMP-QMN, FEAT-0031) wires it: no integration or runtime proof of the bench mechanism exists until then, and the node is the sole application that supplies it (DEC-0208). The node proves it on its week-long unattended soak acceptance gate (DEC-0208). The soak checklist item that exercises this scenario is the **bench fold benching a seat on qualifying losses, the seat routing to the paired demo target while the Book stays `LIVE`** — with the breakeven ratchet also proven to amend single-sided — and SCN-0011 wired and proven alongside the other three risk golden scenarios (DEC-0208). The node runs the disposition vocabulary verbatim: breakevens never count under any `q`, and scratches and partial losses count only where the Book's declared `q` reaches them (DEC-0209). Nothing here grants order, seat-promotion, or live-money authority; that arrives only through the factory pipeline.
