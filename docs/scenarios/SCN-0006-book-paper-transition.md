---
id: SCN-0006
title: Book Paper Transition Is a Dated Binding-Epoch Change
type: scenario
status: provisional
component: COMP-QMF-RISK
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA]
decisions: [DEC-0149, DEC-0143, DEC-0150, DEC-0157, DEC-0158, DEC-0041, DEC-0115]
sources: [docs/components/qmf-risk.md, docs/contracts/ct-24-book-mode.yaml, docs/contracts/ct-28-book-binding.yaml, docs/contracts/ct-23-risk-evaluation.yaml, docs/registry/variables.yaml, _docwork/ledger.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# SCN-0006: Book Paper Transition Is a Dated Binding-Epoch Change

This scenario pins the ratified paper-mode mechanism: a Book's flip to paper is a dated change of its execution binding — a record change that mints a new binding epoch, never a new Book and never a Bot twin — after which every intent routes to the paired demo target while the binding identity, the track record, and the money boundary stay intact. Execution status: **ratified design; implementation is authorized only through the factory pipeline, never from these docs alone.** [DEC-0149] [DEC-0143]

## Given

A Book is `LIVE` with a bound Bot. Book modes are exactly `LIVE | PAPER`; a bot seat is `active | benched`; a Book binding is `live | paper | stood-down` — three vocabularies never interchanged, and a mode-field write that names a seat or binding-state word is an `invalid input` refusal. `BENCHED` is a bot-seat word only and never appears in the Book-mode vocabulary. There are no Bot twins, ever — the dead parallel-Bot paper-twin design stays dead. [DEC-0149]

The Book's execution binding is the risk-domain binding `(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)`, aligned with the `(VenueId, account)` command stream; `world` is a constant `live` for every V1 binding, and `role` is deliberately not in the tuple — it rides the per-intent execution-target record. A Bot binds exactly one Book at a time, and re-binding never mints a new Bot, so performance stays comparable across a flip. Current mode is a **read-time fold** over the append-only CT-24 transition stream under the fold contract (declared stream, ordering key, knowledge-time bound, equal-instant disposition; resolved by rank across writers, never by `WriterId` byte order; never refuses on the trading path — most-restrictive-state, journal `data quality`, alarm), never a stored mutable field. [DEC-0143] [DEC-0149] [DEC-0150]

A paired demo account exists: a real account carrying its own paired BMS instance (one BMS per account everywhere), linked to the live BMS instance by a typed pairing record so the pair reads as one operational unit. The paper starting balance (`registry:paper_starting_balance`) is a Book/family-scoped configurable UI-editable default sized for data-collection realism, with no spine value. [DEC-0143] [DEC-0149] [DEC-0157]

## When

The operator ratifies a dated live-to-paper change of the Book's execution binding — appending one transition record to the CT-24 stream — or a declared control condition routes the Book's activity to paper.

## Then

No new object is created. The flip is a **dated change of the Book's execution binding, a record change** that mints a **new binding epoch, never a new Book** and never a Bot twin; the appended CT-24 transition record carries the resulting mode `PAPER`, its `transition_instant`, the occasioning `trigger_kind`, and the single resolved `paper_target_ref`, and the current mode becomes `PAPER` purely as the read-time fold over the transition stream — no stored field is mutated. [DEC-0149] [DEC-0143]

Routing is separated from binding. The per-intent `execution_target` is resolved once, at intent mint, from `(Book mode, seat state, active-control set)` and enters the CT-19 command record's identity; Book-mode `PAPER` selects the paired demo target **without changing the binding identity**, so one intent can never produce two submissions and a mode flip never replays, resubmits, or mirrors a command. Live and demo are distinct `(VenueId, account)` streams, so an outstanding `UNKNOWN` on one never gates the other. [DEC-0149] [DEC-0143]

**One active paper-routing target per live binding at an instant.** Plural demo accounts exist system-wide, but the binding resolves to exactly one target — re-pointable at any time by a superseding dated record — because two possible destinations is how an order fires twice. No resolvable target makes the paper transition an `unavailable dependency` refusal, and live trading is unaffected. [DEC-0149]

**Routing to paper is never a way around a control.** Every trigger kind declares its disposition `routes-to-paper | blocks-paper` as a mandatory field: a control that blocks live for **market-risk** reasons (a protection window, the kill switch) blocks paper too; a control that blocks live for **capital or authority** reasons (a kill-line stand-down, a benched seat) routes to paper. What continues under a control is the **recording** — the blocked decision on the veto path or the suppressed action on the control-action path, each carrying its would-have-been action — and recording is not trading. [DEC-0149] [DEC-0150]

**Paper money is frozen evidence.** The starting balance (`registry:paper_starting_balance`) is frozen at flip and never hand-adjusted; a reset is not an adjustment — it mints a new **operator-signed paper epoch record** (the `paper_epoch_reset` treasury boundary kind) carrying a fresh declared balance and a lineage edge to the epoch it follows, the running balance never mutated. Paper P&L never becomes Treasury cash, never crosses the money boundary, and never buys a seat. [DEC-0149] [DEC-0157] [DEC-0158]

**The paper target is reconciled as its own binding.** The live binding's reconciliation drift check excludes it (a demo account is *expected* to diverge), but a blocked stream or unresolved `UNKNOWN` on the paper target raises the same alarm class as a live one, because a silent paper outage corrupts every decay verdict computed after it. [DEC-0149] [DEC-0143]

**Return to live is not symmetric with the flip.** It is automatic only where the clearing cause is itself clocked and mechanical; anything touching real money — a first entry into live, a kill-line stand-down returning — requires an operator signature, and paper performance never authorizes a return. Mode transitions (CT-24) and control actions (CT-30) are distinct streams: a clocked mechanical clear mints a CT-24 transition and **never** a CT-30 `resume`, and a control-action stand-down clears only by an operator `resume`. [DEC-0149] [DEC-0041] [DEC-0150]

**Cohort comparison is what the whole mechanism exists to protect.** Decay is judged on decision quality denominated in R, never on realized cash; execution quality is a binding-scoped fact never folded into a decay verdict. Two streams enter one judgment only when a declared `cohort_key` matches (Bot identity, Book identity + template version, `world`, the pinned sensing feed, configured producer refit-series identities, calendar identity + version, instrument identity or a declared equivalence, the active-control set, and the active protection-window set); **account role is recorded and deliberately allowed to differ — that is what makes paper↔live comparison possible.** A decay cohort read is an explicitly permitted cross-role read within `world = live`, and a judgment spanning mismatched cohorts is a `policy rejection`, never a silent average. [DEC-0149]

## Worked numbers

No account count, transition delay, or balance is a ratified constant. The paper starting balance is `registry:paper_starting_balance` — a Book/family-scoped configurable UI-editable default with no spine value; the concrete figure frozen at flip is recorded evidence, non-authoritative, and is captured on the paper epoch record, never restated as a spine value. An executable fixture reads the CT-24 transition fields (`mode`, `transition_instant`, `trigger_kind`, `disposition`, `paper_target_ref`, `paper_epoch_ref`, `operator_signature`) and the resolved per-intent `execution_target`, computing current mode as the read-time fold over the transition stream rather than from any stored field. This scenario depends on the registry keys `registry:paper_starting_balance` and `registry:state_carry`; if either changes, recompute the fixture from the transition and binding records rather than from scenario-local literals.
