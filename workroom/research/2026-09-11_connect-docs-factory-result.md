CONNECT docs-factory CHANGE MODE Stage 9 — captain brief (2026-09-11)

Path: C:/Users/Mubarak/Desktop/QMX  Skill: documentation-factory Stage 9 only. No harvest, no epics, no factory.
Spine adopted: architecture-CONNECT-2026-09-11 AD-1..AD-5 as DEC-0263..DEC-0268. Preflight: reuse COMP-QMN + COMP-QMF-VENUE. ADR-0021.
Docs touched: ADR-0021; trading-node.md; qmf-venue.md; ctrader.md; CT-13/18/19/20/21; constitution L21/L22/L30; overview.md; stack.md; glossary.md; gap-report.md; traceability.md; index.md; AGENTS.md; SCN-0005; ADR-0019 follow-up; changelog.md.
CT-20 mapping corrected: position-read-back / balance-read-back journal as CT-13 data quality (DEC-0266 interprets DEC-0247).
Gates: validate_ledger PASS; validate_registry PASS; validate_inventory PASS (house-accepted warnings); check_citations PASS (dead-DEC class); lint_docs --strict CLEAN.
Leftover GAPs: GAP-0059 (FTR-02) deferred; GAP-0060 (canonical live source token) deferred; both non-blocking. Cheap-veto A1-A5 on DEC-0268.
Feature FEAT-0032 planned, blocked_by FEAT-0023/0024/0026/0031. Implementation still factory-pipeline-only.
Next skill: bmad-create-epics-and-stories then factory lane. Do not run those here.
