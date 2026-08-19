# Backtesting Engine recovery scout

This is a temporary, documentation-only recovery package built from the former repository at `C:\Users\Mubarak\Documents\QMX`. It does not copy old implementation code, run Git operations, or modify the files Claude is currently producing in the clean repository.

## Retrieval verdict

The old repository did **not** contain a completed Backtesting Engine. It contained three different things that must not be conflated:

1. a strong but unratified old-vault Backtest Engine specification embedded in obsolete WF2 mechanics;
2. a later, current architecture for a backend-node **Examination Engine** with an in-house deterministic replay harness;
3. a real Dukascopy acquisition pipeline and large raw tick corpus that failed the canonical licensing gate, plus verifier-backed MIS-Archive storage, bounded replay-input query execution, and labeler-materialization proofs that deliberately stop before bot/Book strategy execution, fill simulation, examination, or certificate generation.

The recoverable product is therefore not the old WF2 engine wholesale. It is a backend-node, process-per-run, book-specific Examination Engine whose replay physics must be re-anchored to the new Book/doors/protection model.

## Package

- [recovered-backtesting-engine.md](./recovered-backtesting-engine.md) — reconstructed boundary, invariants, contracts, lifecycle, implementation verdict, recovery candidates, and open design.
- [restart-handoff.md](./restart-handoff.md) — compact brief for the fresh design/build session.
- [source-ledger.md](./source-ledger.md) — source authority, chronology, and inspected evidence.
- [work/wiki-design.md](./work/wiki-design.md) — detailed wiki and recovered-design archaeology.
- [work/bmad-status.md](./work/bmad-status.md) — BMAD requirements, topology, story status, and deferred-gate audit.
- [work/implementation-evidence.md](./work/implementation-evidence.md) — old-code and verifier evidence. This file describes what existed; it is not code to transplant.

## Recovery labels

| Label | Meaning |
| --- | --- |
| `KEEP` | Binding architecture or requirement from the later active source layer. |
| `SUBSTRATE` | Implemented prerequisite/proof that is useful but is not the Backtesting Engine. |
| `RECONFIRM` | Valuable old/recovered mechanic or exact value that needs a fresh explicit decision. |
| `DESIGN` | Required behavior for which the old repository contains no authoritative complete design. |
| `DROP` | Obsolete WF/authority coupling, reverted agentic material, or misleading implementation claim. |

The work reports are evidence. The consolidated recovered specification is the handoff; none of these files creates new architectural authority by itself.
