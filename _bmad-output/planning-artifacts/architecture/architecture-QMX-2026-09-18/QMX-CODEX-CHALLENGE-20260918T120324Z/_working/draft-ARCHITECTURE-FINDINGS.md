# Stage B independent architecture findings (draft)

## Scope and verdict discipline

This is an adversarial Pass-II supplement to the frozen `INDEPENDENT-SCENARIO-BASELINE.md`. It does not ratify the candidate. “Supported” means an explicit contract, owner, and observable journey; “partial” means a semantic statement without a complete transition/oracle; “unsupported” means design-only or absent; “contradictory” means the candidate refuses a frozen requirement. Evidence is classified as existing behavior, proposed design, or unsupported claim.

## Findings

| ID / severity | Finding | Evidence and impact | Required disposition |
|---|---|---|---|
| F-01 Critical | The candidate refuses an accepted non-Book path. | Proposed AD-11 and `IMPLEMENTATION-SEQUENCE.md:34,40` defer live/non-Book deployment pending L36. This contradicts BR-MKT-02 and P1-MKT-002/003/004/009; no-dummy Book/BMS is not equivalent to a complete alternative. | Amend constitution/scope explicitly, or add a typed non-Book command/risk/accounting contract and journey. |
| F-02 High | Task-graph reuse overstates durability and control flow. | Existing `TaskGraphStore` is an in-memory dict/set projection; dispatcher does not walk successors or persist edges. CT-07 ExperimentSpec lineage is not workflow execution. | Treat as proposed ownership only; add sqlite restart/recovery and A→B successor tests before claiming reuse. |
| F-03 High | DAG validation is incomplete. | Existing validator rejects direct reverse edges but permits self-loops and A→B→C→A. Plugin dependency DFS is not graph-template validation. | Replace/cover topology validator and require compiler/registration parity. |
| F-04 High | Job failure semantics omit partial-artifact completeness. | `CONTRACTS.md:98-112` names states but not inventory/completeness or worker-loss reconciliation. A consumer can treat a partial artifact as complete. | Add artifact inventory, completeness, terminal unknown, and reconcile transitions. |
| F-05 High | Stream overload and replay gaps are not observable. | `CONTRACTS.md:114-128` covers phase/cancel but not buffer bounds, drop/gap, ordering, dedupe, or reference-counted ownership. | Add explicit backpressure/gap/ref-count schema and journeys. |
| F-06 High | Wire/session architecture is design-only at runtime. | Listener accepts/drains frames; no command-to-owner dispatch. Product-session, grant intersection, and `psess:` persistence are not implemented. | Add authenticated dispatch, typed refusal, CAS context revision, idempotency, reconnect tests. |
| F-07 High | Extension/index lifecycle has no atomic preservation oracle. | AD-18 describes install/enable/rollback but no transaction/state machine for duplicate or incompatible packages. | Add atomic index rebuild and migration-failure journey preserving last usable index. |
| F-08 Medium | Data/ML provenance and placement remain partial. | AD-12/`CONTRACTS.md:81-96` state recipe identity, but provider disagreement, entitlement/unavailable states, weight completeness, and portable artifact staging lack oracles. | Add source-resolution, weight completeness, preflight, and staging contracts. |
| F-09 Medium | UI adapter boundaries are clear but lifecycle is unproven. | AD-17/`UI-HOST.md` correctly make JSON Render/MCP Apps presentation-only; mount, dispose, reconnect, stale snapshots, and gaps are not journeyed. | Add host lifecycle and resync journeys; never infer execution from layout. |
| F-10 Medium | Mutation/evaluation is documented, not evidenced. | AD-19/`STACK-AND-EVALUATION.md` recognize current mutmut WSL constraints, but no executable disposable-run evidence exists. | Make mutmut optional; run only in disposable WSL copy, never shared worktree, preserving raw outcomes. |

## Confirmed strengths (not ratification)

Existing evidence supports QML mill/stage-0 persistence and graduation tests, QMF data/risk ownership, QMB Book/BMS-gated doors, and QMN closed venue selection. These are bounded package proofs, not cross-component workflow proof. Specialists remain first-class; QMF is one framework. Book/BMS is the default, not the ceiling. PM is the trading-floor label “Portfolio Manager.” Sessions own context and grants; visible tabs do not. App-use may stage a change request but cannot edit implementation.

## Pass-II additions only

The candidate adds change-request staging; four cross-app modes with intersection authority; explicit no-dummy Book prohibition; recipe release identity and CT-07 lineage; product-session journal projection; UI DTO/presentation adapter boundaries; first-party enable failures; WSL-only mutmut guidance; and PM label preservation. These improve semantic precision but do not close the transition gaps above.

## Overall assessment

The candidate is directionally coherent but not implementation-ready as a complete architecture. The highest-risk unresolved seam is the explicit BR-MKT contradiction, followed by durable task-graph execution, atomic extension lifecycle, partial-artifact truthfulness, stream overload, and live wire dispatch. No verdict should ratify until those seams have contract-level oracles.
