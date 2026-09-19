---
name: Consequential unresolved choices
sitting: architecture-QMX-2026-09-18
stage: C
---

# Operator decisions (Stage C)

Ordinary technical choices were made in the spine. **OD-01 is closed from the original sitting transcript.** There is no remaining architecture question for the operator.

## OD-01 — CLOSED (transcript, not a new ask)

**Wrong frame (rejected):** “May a second system talk to a broker later, after you personally approve?”

That mixed three different things:

1. Architecture: can the kit host a non-Book portfolio/risk/sizing system.
2. Operating discipline: sequential paper-then-live; do not cut over tomorrow (already said).
3. L17 human promote of live money (already constitution).

**Transcript answer (operator):** Book and BMS are a **specific** portfolio-management, risk, and position-sizing system that arrived in this QMX version. Other versions used other stacks. The kit must let you **replace or improve** that stack. When you do, **everything attached adopts**: hypothesis/authoring (QML), backtest and optimization (QMB), MIS/intelligence binding, the trading node, paper, and live. Never fake a Book. Research/sensing is not that system. Two versions (scalping Book v1 vs v2, or Book vs Kelly) are distinct compositions and must not clash. Cutover is sequential, not hot-swap.

**Recorded ruling:** AD-11 / AD-23. L36 is a **named amendment**: Book/BMS remain the default implementation of those roles, not the ceiling. Constitution prose is Documentation Factory’s job. Live ATC still requires paper-then-live and L17 — that is how you already described working, not a hold on the architecture.

## OD-02 — Persist `task_graph_state` including outbox — YES (technical default)

Closed-store amendment of an already-named projection.

## OD-03 — ContributionHit on the Library facade — YES (technical default)

Third discovery class, never a registry kind.

## Not asked

- No sixth COMP
- No n8n/Hermes/OpenBB import (mental models only)
- mutmut optional, WSL, never on shared trees
- Portfolio Manager label only
- GAP-0081 chrome later
- Sequential not hot-swap; fenced
- Authoring vs app-use sessions
- Documentation Factory runs in a **fresh session**, operator-launched
