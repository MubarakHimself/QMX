---
id: SCN-0001
title: Core Freeze Choices Block Implementation
type: scenario
status: ratified
component: COMP-QMF-CORE
depends_on: []
decisions: [DEC-0004, DEC-0022, DEC-0026, DEC-0027, DEC-0028, DEC-0029, DEC-0030, DEC-0031, DEC-0105, DEC-0106, DEC-0107, DEC-0108, DEC-0109, DEC-0110, DEC-0127, DEC-0131, DEC-0134]
sources: [docs/constitution.md, docs/components/qmf-core.md, docs/registry/variables.yaml, docs/contracts/ct-01-money-quantity.yaml, docs/contracts/ct-02-time-calendar.yaml, docs/contracts/ct-03-instrument-identity.yaml, docs/contracts/ct-04-typed-refusal.yaml, docs/contracts/ct-05-version-fingerprint.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# SCN-0001: Core Freeze Choices Block Implementation

This scenario proves that an implementation choice is authority only where a contract is ratified, never where a freeze choice is still open. The architecture sittings (2026-08-19/20) ratified the qmf-core money, time, instrument-identity, typed-refusal, fingerprint, and result-label contracts, so those boundaries are now buildable; two qmf-core freeze choices remain open and still block their own implementations. Execution status: **foundation contracts buildable; two freeze choices remain open**. [DEC-0134]

## Given

An agent is asked to implement exact money, exact time, Instrument identity, typed refusals, result identity, and version fingerprints in `COMP-QMF-CORE`. CT-01 through CT-05 now carry ratified content: exact money as scaled integers on a per-value declared scale (DEC-0105), exact time as int64 UTC nanoseconds with distinct civil and trading dates (DEC-0106), instrument-venue-account identity (DEC-0107), the `fp1` fingerprint recipe (DEC-0108), the seven-category typed-refusal vocabulary (DEC-0109), and the result label whose parts — now including producer contract identity and evidence class — are its identity (DEC-0110, DEC-0131). qmf-core stays definitions-only and asset-neutral. [DEC-0022] [DEC-0031] [DEC-0105] [DEC-0106] [DEC-0107] [DEC-0108] [DEC-0109] [DEC-0110]

Two of the six original qmf-core freeze choices remain open and are not contracts (DEC-0134): the backtest fidelity taxonomy and the SR* search-quality threshold. Canonical indicator arithmetic is ratified — TA-Lib 0.7.1 + 0.7.1 pinned as lockfile artifact hashes plus an import-asserted reference-configuration record (DEC-0127).

`GAP(GAP-0048): Ratify the backtest fidelity taxonomy (deferred to the backtesting sitting).`

`GAP(GAP-0049): Ratify the SR* search-quality threshold (deferred with backtesting).`

## When

The agent implements a ratified money, time, identity, refusal, fingerprint, or result-label boundary, or proposes a concrete indicator-arithmetic reference, a backtest fidelity level, or an SR* value and attempts to treat that proposal as a public contract.

## Then

Implementation of the six ratified boundaries proceeds by conforming to the ratified CT-01 through CT-05 contracts (DEC-0105 through DEC-0110) — never by re-inventing their fields. For the two still-open freeze choices, the implementation must stop before code or serialized data fixes a value; a proposal may be recorded for operator review but cannot replace a null contract field. qmf-core remains definitions-only and asset-neutral. [DEC-0004] [DEC-0022] [DEC-0031] [DEC-0134]

## Worked numbers

The timestamp encoding is now ratified as int64 UTC nanoseconds (DEC-0106), and money, price, and quantity carry a declared per-value scale rather than one global decimal constant (DEC-0105) — so `registry:money_decimal_scale`, `registry:price_decimal_scale`, `registry:quantity_decimal_scale`, and `registry:timestamp_precision` describe ratified per-value or encoding-level facts, not a manufactured universal number. Indicator arithmetic is pinned by DEC-0127; no backtest-fidelity or SR* number is authorized — those two freeze choices remain open under DEC-0134.
