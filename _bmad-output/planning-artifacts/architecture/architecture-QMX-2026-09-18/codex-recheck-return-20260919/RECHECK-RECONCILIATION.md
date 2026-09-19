---
name: Focused Codex recheck reconciliation
date: 2026-09-19
candidate: qmx-workflows-arch-2026-09-19-c
return_zip: CODEX-RECHECK-RETURN-2026-09-19.zip
return_sha256: aa64bc8a431d543d86da77b182b2c18e449d3a6665fe837709902dc95b3adeb4
input_packet_sha256: 101ddefe89253ccb62ccbed83b2c3be71c0e312a30eae87f99db960171cdfab8
disposition: repairs-applied-on-desk — not Codex-ratified; epics unblocked after desk-fix
---

# Recheck reconciliation

Codex finished the focused AD-23..AD-31 recheck. Authenticity: return zip hashes match the sidecar; `EVIDENCE-MANIFEST.json` cites the outgoing packet SHA-256 `101ddefe…` (the packet this sitting built). 85 scenario IDs preserved. Pass-I not re-derived. OD-01 not reopened. Documentation Factory not re-run. No production code edited.

## Verdict (Codex)

**Repairs required; not ratified. Do not resume epics yet.**

AF-20 (claim honesty) holds. AF-01..AF-19 remain open as specification defects RC-01..RC-17. L36 substance in folded SCN-0020/ADR-0024 was not reversed.

## Desk-fix started this sitting (Grok)

Process/ledger drift (Codex DOCS-DRIFT.md):

- `CHALLENGE-RECONCILIATION.md` — OD-01 no longer a live venue gate; section 8 records the return zip; skip text replaced.
- `CONFLICT-REGISTER.md` — L36 option-A sentence removed.
- `REQUIREMENTS-ADDENDUM.md` — DF-already-ran / recheck-returned status.
- `docs/decisions/ADR-0024-workflows-construction-kit.md` — recheck ran, repairs-required, not approval.
- `docs/gap-report.md` + `_docwork/gaps.yaml` GAP-0092 — return recorded.
- `docs/scenarios/SCN-0019` — three-record split (request / validation / apply).
- `docs/scenarios/SCN-0020` — owner COMP-QMB (QMF-RISK is default shapes, not ATC owner).
- `docs/scenarios/SCN-0021` — at-least-once dispatch / exactly-once logical acceptance.
- `docs/scenarios/SCN-0022` — bounded ExportScanReport threat model.

Contract/spine field repairs RC-01..RC-17: landed in `CONTRACTS.md` and AD-3/AD-23..AD-31 (`DESK-FIX-CONTRACTS.md`). Envelope signing algorithm and pack qualification alternate formula remain named implementation choices, not missing architecture behavior.

Epics may resume. Do not claim Codex ratified AD-23..AD-31. Do not re-run Documentation Factory.
