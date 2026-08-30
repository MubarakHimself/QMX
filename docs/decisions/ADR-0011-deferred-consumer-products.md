---
id: ADR-0011
title: Defer consumer runtimes and products beyond QMF V1
type: adr
status: ratified
depends_on: []
decisions: [DEC-0083, DEC-0087, DEC-0088, DEC-0089, DEC-0090, DEC-0091, DEC-0204, DEC-0259]
sources: [DEC-0083, DEC-0087, DEC-0088, DEC-0089, DEC-0090, DEC-0091]
generated: 2026-08-18
verified: 2026-08-29
stale_after: 1y
---

# ADR-0011: Defer consumer runtimes and products beyond QMF V1

Date: 2026-08-18. status: ratified — corpus signed off by the operator 2026-08-21 (conditional go-ahead in the PRD session; the independent contradiction sweep passed).

## Context

Backtesting, MIS, QML Bots, an agentic runtime, and a visual Simulator all consume QMF foundations but require contracts that the current sessions deliberately did not finish.

## Options considered

1. **Central always-on backtesting service** — dead because it cannot supply the required isolation and Book-specific variation (DEC-0084).
2. **Adopt Nautilus or run an adoption spike** — dead because QMX retains locally owned contracts (DEC-0085, DEC-0086).
3. **Defer consumer systems and build stable foundations first** — selected.

## Decision

Backtesting, the future modular sandbox, the visual Simulator, MIS, the QML Bot library, and agentic runtime organs are outside QMF V1. (DEC-0083, DEC-0087, DEC-0088, DEC-0089, DEC-0090, DEC-0091)

## Consequences

QMF V1 exposes reusable contracts without pretending to be a complete trading node. Deferred products require later design sessions and cannot be inferred from the current feature inventory.

## Follow-up (2026-08-29)

Three of the deferred consumers have since taken ratified homes, recorded here as a dated note without disturbing the 2026-08-18 decision above. **QMB** realizes experimentation and backtesting ([ADR-0017](ADR-0017-qmb-experimentation-library.md)); **QML** realizes the Bot authoring library ([ADR-0018](ADR-0018-qml-bot-authoring-library.md)); and the **trading node** realizes the supervised runtime that consumes all three ([ADR-0019](ADR-0019-trading-node.md), adopted in full by DEC-0259).

**MIS stays outside V1.** The node builds only the SEAM — a compute-once, versioned signal snapshot dispatched to a closed consumer set (the Book door and the KSA), a shadow lane, and an ungoverned comparison read model that gates nothing — with the labelers rule-based and no trained model bound; MIS training and shadow rollout are a named follow-on epic under GAP-0051 (DEC-0204). The visual Simulator and the agentic runtime organs remain deferred, with the agent/MCP door carried under GAP-0053. This note records realized homes and adds no new grant.
