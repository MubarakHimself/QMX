---
id: DOC-CHANGELOG
title: QMF Documentation Changelog
type: changelog
status: provisional
sources: [_docwork/ledger.yaml, _docwork/gaps.yaml, _docwork/feature_inventory.yaml, _docwork/review-consistency.md, _docwork/review-redteam.md, docs/index.md]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 90d
---

# QMF Documentation Changelog

This records changes to the QMF knowledge base. It is not a software release log and does not convert provisional decisions into implementation authority.

## 2026-08-18 — Fresh documentation-factory build

| Field | Value |
|---|---|
| Mode | Fresh documentation from two transcript sources |
| Authority snapshot | 98 sequential decisions; 49 gaps; 431 source extractions |
| Documentation corpus | 82 files: 54 Markdown and 28 YAML |
| Public QMF roster | Five libraries and two modules |
| Component registry | 14 public, internal-seam, and external component records |
| Contracts | CT-01 through CT-26 |
| Component specifications | 14 |
| ADRs | 11 |
| Golden scenarios | 10, deliberately blocked where source rulings are missing |
| Active lens documents | 10 across data, testing, bugs, operations, security, observability, and performance |
| Feature handoff | 27 planned features in 14 dependency waves; none ratified |
| Mode status | Provisional; not implementation-ready or live-operation-ready |

Created the authority ledger, gap catalog, constitution, architecture maps, typed contract placeholders, component specifications, ADR set, variable registry, glossary, active lens documentation, scenario bank, agent entry point, traceability map, and ratification packet.

Independent consistency and source-blind adversarial reviews identified wiring and authority defects. The documentation pass corrected contract ownership and routing, added CT-26 for the Store-to-Backup seam, separated active from intended consumers, removed invented journal, restore, secret, and command assumptions, and preserved all true source gaps as explicit non-buildable gates.

The remaining human gate is intentional: the two conflicts, open decisions, and blocking gaps must be ruled on and the provisional packet signed before strict release validation can pass.
