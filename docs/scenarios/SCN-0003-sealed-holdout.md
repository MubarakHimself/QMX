---
id: SCN-0003
title: Default Research Access Excludes the Sealed Holdout
type: scenario
status: ratified
component: COMP-QMF-DATA
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY]
decisions: [DEC-0044, DEC-0046, DEC-0119]
sources: [docs/components/qmf-data.md, docs/registry/variables.yaml, docs/contracts/ct-12-dataset-split.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# SCN-0003: Default Research Access Excludes the Sealed Holdout

This scenario exercises the sealed-holdout research boundary, now ratified with enforcement. The architecture sitting ratified that the 12-month seal is a no-peek lock (not retention — data is kept regardless) enforced now as a `policy rejection` refusal at every qmf-data read boundary — raw, processed, research door, and restored backups alike — independent of the deferred causality gates; the seal boundary is a frozen stored TradingDate never re-derived under later tzdata; the sealed period gets one logged final look journaled as a named `control action` subtype. Execution status: **seal enforcement ratified**. [DEC-0119]

## Given

History is preserved according to `registry:raw_history_retention_policy` (raw originals and lineage are kept forever). A CT-12 release divides governed research data from the newest sealed period. Dataset splits are fingerprinted, time-ordered, non-overlapping manifests, each pinning exactly one calendar identity and version in-band; boundaries are explicit stored TradingDates or instants, never civil dates, and the seal boundary is a frozen TradingDate. [DEC-0044] [DEC-0119]

`GAP(GAP-0016): Ratify the look-ahead/causality registration gate (deferred to the backtesting sitting, DEC-0121) — the seal enforcement here stands independent of this gate.`

## When

A normal research consumer requests the default dataset release, or any read crosses the qmf-data raw, processed, research-door, or restored-backup boundary into the sealed period.

## Then

The sealed identities are absent from the research release, and any read touching the sealed period is refused with a `policy rejection` typed refusal at every read boundary including restored backups — enforced now, independent of the deferred GAP-0016/0017 gates. The underlying source evidence remains retained. The consumer must not reopen or recycle the sealed set: the one authorized final look is journaled as a `control action` subtype and is never silently recycled. [DEC-0044] [DEC-0046] [DEC-0119]

## Worked numbers

The seal boundary is a frozen stored TradingDate, never re-derived under a later tzdata version (DEC-0119); the 12-month no-peek lock is ratified. The executable fixture computes membership from the fingerprinted CT-12 manifest and its pinned calendar identity, and asserts a `policy rejection` refusal on any sealed-period read rather than a silent empty result.
