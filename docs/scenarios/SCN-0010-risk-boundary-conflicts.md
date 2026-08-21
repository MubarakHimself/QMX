---
id: SCN-0010
title: Same-Tick Risk Actions Arbitrate by Rank on One Command Stream
type: scenario
status: provisional
component: COMP-QMF-RISK
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA]
decisions: [DEC-0150, DEC-0151, DEC-0147, DEC-0143, DEC-0158]
sources: [docs/components/qmf-risk.md, docs/contracts/ct-30-control-action.yaml, docs/contracts/ct-29-exit-record.yaml, docs/contracts/ct-23-risk-evaluation.yaml, docs/contracts/ct-18-venue-capabilities.yaml, docs/registry/variables.yaml, _docwork/ledger.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# SCN-0010: Same-Tick Risk Actions Arbitrate by Rank on One Command Stream

This scenario pins the ratified same-tick arbitration: on one `(VenueId, account)` command stream, several protection and exit actions that fall due on the same tick resolve at exactly one arbitration point by BMS-declared rank — colliding actions collapse to one command, mutually exclusive ones let the higher rank win, composing ones both execute, and the exit-preservation invariant guarantees no control ever reduces the protection a lower-ranked act would have delivered. Execution status: **ratified design; implementation is authorized only through the factory pipeline, never from these docs alone.** [DEC-0151] [DEC-0150]

## Given

Priority is defined **per `(VenueId, account)` command stream with exactly one arbitration point per stream** — a deliberate cardinality-one, scoped per stream so the system still holds many arbiters; several Books may share one stream, and cross-stream ordering is a declared non-guarantee (two venues have two clocks and the replay tie-break carries no causal meaning). [DEC-0151] [DEC-0143]

The rank table is **BMS-declared, one per command stream**, matching the arbitration point's own cardinality (a Book-owned table would put two rank orders at one arbiter). Each control-action kind's rank is a **declared, mandatory, non-defaultable field — its existence is QMF's, its value is not**; ranks are a total order with uniqueness enforced at admission Layer 1 (two kinds may not share a rank), and arbitration resolves strictly by rank with no arrival-order input. The corpus-derived class ordering, highest first, is: **(0)** operator action; **(1)** protection actions (kill-switch class); **(2)** BMS/Book forced flats (kill-line stand-down, `window_forced_flat`, hold-time or boundary force-flat); **(3)** fast invalidation (risk-reducing bot exit proposals); **(4)** ordinary bot exits and protection amendments. The rank *ordering* is corpus-derived; the collapse and conflict rules below, and the unification of hold-time force-flat with no-overnight, are this sitting's own design. Scope resolution reads CT-18 `netting | hedging` **before** dispatch. [DEC-0151]

The **exit-preservation invariant is spine-level law:** no control action, of any authority, at any scope, may block a risk-reducing act — `cancel_order`, `close_position`, `close_all`, a risk-non-increasing `amend_protection`, a protection action, or the recording of evidence; the blocking half of any control is always **entries only**, and no control-action kind whose effect is a blanket command-pipe block may be minted. [DEC-0150]

## When

On one tick, on one command stream, several actions fall due on overlapping enforcement scope: a venue-resident protective stop fires; a kill-switch `suspend_new` (class 1) is in force; a kill-line breach raises a `flatten` (class 2) on the binding's scope; the Book's `window_forced_flat` (class 2, a distinct rank) targets the same scope; and a bot `close_full` exit proposal (class 4) targets the open position inside that scope.

## Then

**The venue-resident stop sits outside the ordering by construction.** It fires when it fires; nothing asks the node and the node assumes nothing. Its outcome arrives as an ordinary observation, and the node-close-versus-venue-stop race is resolved by the **superseded-by-fill** read-back rule — a node cancel or close resolved by read-back is accepted only if no fill appears at or after the submit stamp; otherwise it resolves `rejected-by-venue (superseded-by-terminal-subject)`, a named outcome, never a stream-blocking `UNKNOWN`. This resolution generalizes to every command whose subject can terminate independently. [DEC-0151] [DEC-0158]

**Collapse rule — same command, one emission.** The kill-line `flatten` (class 2), the `window_forced_flat` (class 2, distinct rank), and the bot `close_full` (class 4) would each produce the **same mechanical close command on the same enforcement scope**. Exactly **one** command is emitted; the rank winner (the kill-line flat, the highest-ranked of the three) supplies the authority (`book_policy`) and the reason (`kill_line_flat`), and every loser journals as a **suppressed control action**. Rank decides attribution, not whether the position closes. [DEC-0151]

**Conflict rule and the standing invariant — composing actions both execute.** The kill-switch `suspend_new` (class 1) and the kill-line `flatten` (class 2) have effects that **compose** (`suspend_new + flatten`), so **both execute** — the higher-ranked `suspend_new` does **not** suppress the lower-ranked `flatten`. The standing invariant is explicit: a higher-ranked action may never reduce the protection a lower-ranked action would have delivered. This is the single scenario the kill line exists for; unscoped arbitration would let the rank-1 `suspend_new` suppress the rank-2 `flatten` and leave the positions open. Only *mutually exclusive* commands arbitrate; the higher rank then wins outright and the lower is suppressed — never both, never queued, and a lower-ranked action may never undo a higher-ranked one. [DEC-0151]

**Suppression is first-class evidence.** Each suppressed loser journals as a control action carrying the suppressing authority, the suppressed authority, the reason class, the would-have-been action referenced **by its CT-30 control-action record fingerprint** (a command identity is minted only at submission — no phantom command record may exist), the enforcement scope, and the arbitration record's fingerprint. Enactment links back to intent by `enacts` edges, never by `correlation_id`; a door refusal (refused before authorization) would instead stay on the veto path. Whole-trade R still credits the Bot that opened the closed position, regardless of who closed it. [DEC-0150] [DEC-0147]

**Scope resolution refuses rather than widening.** Scope resolves at dispatch through the pinned versioned CT-30 resolution table; an unresolvable scope is an `unsupported capability` refusal, is never emulated at a wider scope, and where a `netting` position model makes a narrower scope indistinguishable from a wider one the action **refuses** rather than executing wider. A control action that fans out is a compound command, its parent outcome the meet of its children. [DEC-0150] [DEC-0143]

**One exit record carries the resolved authority.** The single emitted close mints one CT-29 exit record whose `closing_authority` is the arbitration winner (`book_policy`) with the `arbitration_record_ref`, and whose `close_reason` is `kill_line_flat` — minted apart from `protection_forced_flat` because the kill line (a per-Book capital floor) and the kill switch (the global authority) are two different things — resolved through the pinned versioned `(action kind x issuing authority) -> close_reason` table shared by CT-29 and CT-30. Suppression counting reads the control-action stream through `enacts` edges, never the exit record, which would double-count. [DEC-0147] [DEC-0151]

## Worked numbers

**No rank value is supplied by QMF.** The class ordering (0 operator, 1 protection, 2 forced flats, 3 fast invalidation, 4 ordinary exits) is corpus-derived; the concrete rank integers are BMS-declared non-defaultable fields in the rank table, one per command stream, with no spine value, and uniqueness is enforced at admission Layer 1. The kill line is `registry:kill_line_capital_floor` — the same number as `loss_floor` in the sizing ladder (`loss_runway = book_capital - loss_floor`), configurable UI-editable with no spine value; `registry:window_forced_flat` and `registry:hold_time_force_flat_trigger` likewise carry no spine value. An executable fixture supplies a BMS rank table, the pending actions on one enforcement scope, and the CT-18 `netting | hedging` declaration, then asserts: one emitted close command, the arbitration winner as `closing_authority`, `suspend_new + flatten` both executing, and each suppressed action's record referencing a real CT-30 fingerprint. If any registry key or the rank table changes, recompute from the BMS-declared table and the control-action stream, never from scenario-local literals.
