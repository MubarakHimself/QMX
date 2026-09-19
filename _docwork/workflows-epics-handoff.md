---
name: Workflows-epics-handoff
type: next-session-prompt
status: ready-to-paste
created: 2026-09-19
architecture_review_status: docs folded (ADR-0024); Codex focused recheck of AD-23..AD-31 returned repairs-required; Grok desk-fix of RC-01..RC-17 landed; not Codex-ratified
---

# Next session — create epics and stories (Workflows construction kit)

Codex recheck returned 2026-09-19 (`CODEX-RECHECK-RETURN-2026-09-19.zip`). Desk-fix of RC-01..RC-17 is in `CONTRACTS.md` / spine AD-23..31 and folded SCN-0019..22. **This prompt is unpaused.** Do not start videos/n8n/Hermes. Do not implement code. Do not re-run Documentation Factory. Do not claim Codex ratified AD-23..AD-31.

Paste follows. Do not re-open architecture.

The `docs/` fold is still **uncommitted working tree** on `main`. Run the epics session in this same workspace so it sees the dirty tree. Do not use `_docwork/qml-research-epics-handoff.md` (that is FEAT-0047 mill).

---

## Prompt to paste

Use the installed `bmad-create-epics-and-stories` skill on `C:/Users/Mubarak/Desktop/QMX`.

Slice from the **ratified** 2026-09-19 Workflows construction-kit absorption (`ADR-0024`, DEC-0414..DEC-0451). Docs authority only — stories specify factory work; they do not authorize live trading, credentials, or go-live.

### Authority (read these, do not invent)

- `_docwork/riders/workflows-construction-kit-2026-09-19.md`
- `docs/decisions/ADR-0024-workflows-construction-kit.md`
- `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/ARCHITECTURE-SPINE.md` (local AD-1..AD-31, candidate `qmx-workflows-arch-2026-09-19-c`)
- `docs/scenarios/SCN-0018` .. `SCN-0022`
- `_docwork/feature_inventory.yaml` **FEAT-0051..FEAT-0057**
- `_docwork/workflows-increment-brief.md`
- `_docwork/workflows-increment/confirmation/RUBRIC.md` (source-read confirmation; do not re-fold)

Parents bind read-only. No new COMP. No new CT. Additive CT-40 family annotations only until FEAT-0051 lands a format mint of existing CT-40 fields.

### First epic (mandatory)

**FEAT-0051 — ContributionHit concatenate + pin/tombstone.**

Blocked by FEAT-0050, FEAT-0041, FEAT-0046. Do not start from FEAT-0001. Do not start from mill FEAT-0047.

Then FEAT-0052..FEAT-0057 in inventory order. Use `python C:/Users/Mubarak/.agents/skills/documentation-factory/scripts/validate_inventory.py --root C:/Users/Mubarak/Desktop/QMX --handoff FEAT-0051` (then 0052..0057) so each epic inherits blockers, dependents, and wave-mates.

### Operator gap rulings (2026-09-19) — do not design these

- **GAP-0092** — focused Codex recheck of AD-23..AD-31 is **not required** to write stories. Do not claim Codex approved those ADs. Optional later; not a gate.
- **GAP-0099** — QMN supervision-mode taxonomy is **out of scope until the platform is live**.
- **GAP-0100** — cutover readiness dashboard is **UI, later**. AD-25 fencing stays the transition machine.

Also stay out: GAP-0081 chrome, GAP-0058, GAP-0085, GAP-0061/0062/0063, marketplace, dummy Book, sensing-as-ATC, sixth COMP.

Cheap-veto A1–A6 (PolicyPair field list, fencing enum, envelope fields, pin tuple, recipe identity, checkpoint order) remain individually overturnable. Stories may cite them; they must not treat them as operator-spoken schemas.

### After epics/stories

Stop. Mubarak's existing factory automation (attended epic-factory / Grok `/run-epics`, or `/queue-publish` + kanban) handles implementation. Do not launch factory lanes from the epics session. `main` moves only by the operator's squash-merge click.
