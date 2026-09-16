---
gate: finalize (update restart)
date: 2026-09-16
lint: pass (0 findings) after amendment
---

# Reviewer gate summary — QML research expansion

| Lens | File | Verdict |
|---|---|---|
| lint_spine.py | — | pass, 0 findings (before and after amendment) |
| Rubric walker | review-rubric.md | return-for-amendment → H-1/H-2/M-1/M-2 applied |
| Currency | review-currency.md | pass; H-1 origin-vs-`"qma"` and H-2 fp1 encoding applied; L-3/L-4 applied |
| Adversarial | review-adversarial.md | return-for-amendment → C-1..C-4 and H-1..H-5 applied |
| Parent consistency | review-parent-consistency.md | pass with medium; F-1/F-2/F-3 applied |
| Reconcile inputs | reconcile-inputs.md | landed with quiet misses; source-agnostic mill, taxonomy, seed_cite, three entries, compare-note stamp applied |

Spine remains **proposed**. Operator has not accepted. `status: draft`.

## Applied (clear fixes)

- `research_ref` = qmf-core fingerprint `{ class: qml-research-hypothesis, contract_format_version, body }` — fp1-shaped, not a registry kind.
- `originating_research_ref` for mill graduation is that `research_ref` only; Citation digest illegal; live `graduate_to_governed` encoding honored.
- Live StrategyHandle `origin` stays `"qma"`; seed handoff is distinct `seed_cite`.
- Single hypothesis writer = QML authoring composition root blob store; QMA daemon must not persist hypotheses or bind a second CT-44 source in v1.
- Stage 0 lives in public `qml.research`; QL-1 four-count is a docs-factory obligation, not an implementation veto.
- Viewing LAYOUT-DEMO is a read-only projection (no `research_ref` mint).
- Three legal entries, none a toll booth.
- AD-4 include/exclude lives in research-corpus plugin, not `qma-core`.
- Stage 0 field is `graph`, never `Confluence`.
- `saved-view` live token; `unscored` is first-slice work not current adapter behaviour.
- Source-agnostic mill; QMF=framework / QML QMB QMA=libraries.

## Not applied (operator / later)

- Parent QL-1 text change, Workbench AD-3 commentary, QMA AD-19 empty-corpus sentence — still `[PROPOSAL]` for documentation-factory after acceptance.
- Confirm `source_id=strats` freeze and AD-4 include/exclude lists.
- Optuna 4.9.0 vs 5.0.0 and uv patch drift — inherited, not this sitting.
