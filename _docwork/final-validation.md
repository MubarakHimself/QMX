# QMX / QMF V1 final validation

Date: 2026-08-18  
Documentation mode: transcript reconstruction, provisional run-through  
Outcome: **assembled and internally validated; awaiting operator ratification**

## Handoff status

The documentation factory has produced a complete, navigable QMF V1 blueprint from both supplied transcripts. The corpus is suitable for operator review and subsequent Kanban planning, but it grants no implementation, credential, deployment, order-submission, live-money, recovery, or destructive authority while its decisions and documents remain provisional.

Stage 7 consistency review: **PASS / 0 open documentation defects**.  
Stage 7 source-blind red team: **PASS / 0 open documentation defects**.  
Stage 8 assembly: **complete as a provisional corpus**.  
Stage 8 strict release gate: **withheld pending operator ratification and blocking-gap resolution**.

## Source coverage

| Source | Chunks covered | Result |
|---|---:|---|
| QMX2 (`SRC-01`) | 31 / 31 | 100% |
| QMF1 (`SRC-02`) | 39 / 39 | 100% |
| Total | 70 / 70 | 100% |

The extraction set contains 431 source-ordered findings. QMX2 carries the stronger later correction authority where the two sessions differ. The export omission around `SRC-01-C0022` and the assistant-recap-only evidence for several paper-mode rulings remain disclosed in the ratification packet and ledger.

## Authority artifacts

| Artifact | Count / status |
|---|---|
| Decision ledger | 98 decisions: 55 provisional, 8 open, 2 conflict, 18 dead, 6 superseded, 9 out-of-scope |
| Gap ledger | 49 gaps: 46 open, 3 deferred; 45 are blocking |
| Feature inventory | 27 planned features in 14 dependency-derived waves; 26 one-pass and 1 fenced multi-pass reconciliation |
| Variables registry | 31 variables |
| Component registry | 14 components |
| Typed contracts | CT-01 through CT-26 |

The two deliberate unresolved conflicts are:

- `DEC-0040`: Bot/confluence cardinality.
- `DEC-0067`: ordinary exit ownership versus Book-owned exit policy.

Neither conflict was silently resolved. `FEAT-0027` remains a specification-and-reconciliation pass, not permission to implement Risk, Book, or BMS behavior.

## Documentation corpus

| Type | Count |
|---|---:|
| All files under `docs/` | 82 |
| Markdown | 54 |
| YAML | 28 |
| Component specifications | 14 |
| Contracts | 26 |
| ADRs | 11 |
| Golden scenarios | 10 |
| Active lens documents | 10 |

The documentation index covers 82 / 82 files with no missing, extra, duplicate, or broken local target. All 14 component specs have scenario backlinks. The traceability view covers 98 / 98 decisions, 49 / 49 gaps, and 27 / 27 features.

## Final gate snapshot

| Gate | Result |
|---|---|
| `lint_docs.py --root .` | PASS — `OK: docs lint clean` |
| `check_citations.py --root .` | PASS — `OK: citations valid` |
| `coverage_report.py --root .` | PASS — 70 / 70 chunks |
| `validate_registry.py --root . --strict` | PASS — `OK: registry valid` |
| `validate_ledger.py --root .` | PASS — `OK: ledger valid` |
| Inventory default | PASS — 27 features |
| Inventory order | PASS — blocker-first order resolves |
| Inventory waves | PASS — 14 waves; only the expected same-component serialization advisories |
| Inventory strict | PASS |
| Dependency DAG | PASS — 14 nodes, 21 edges, no cycle |
| Active contract roles | PASS — 73 / 73 endpoints align with the manifest |
| Component frontmatter vs manifest | PASS — 14 / 14 |
| Relative Markdown links | PASS — 0 broken |
| Independent consistency review | PASS — 0 open defects |
| Independent source-blind red team | PASS — 0 open defects |

CT-13 is cycle-safe: the only active path is `COMP-QMF-DATA` to `COMP-QMF-DATA-STORE`; Registry, Venue, and Risk are intended but unwired. Venue has no active dependency on cTrader; CT-18 through CT-20 remain reserved/unwired and CT-21 remains a no-operation gate.

## Strict release gate

`lint_docs.py --root . --strict` exits 1 by design:

- 54 provisional-status diagnostics.
- 1,009 references to blocking gaps.
- 0 other strict diagnostics.

This is the correct result for an unsigned reconstruction. Removing those markers without operator decisions would turn recommendations and missing semantics into false authority.

## Operator gate

The next authorized action is review and signature of [`ratification-packet.md`](ratification-packet.md). The operator must confirm or amend the provisional decisions, explicitly resolve or preserve both conflicts, and answer the blocking gaps needed by any selected first wave. Only after that signature may provisional stamps be promoted and strict lint be expected to pass.

Primary entry points:

- [`docs/index.md`](../docs/index.md)
- [`docs/AGENTS.md`](../docs/AGENTS.md)
- [`ratification-packet.md`](ratification-packet.md)
- [`feature_inventory.yaml`](feature_inventory.yaml)
- [`docs/gap-report.md`](../docs/gap-report.md)
- [`review-consistency.md`](review-consistency.md)
- [`review-redteam.md`](review-redteam.md)

