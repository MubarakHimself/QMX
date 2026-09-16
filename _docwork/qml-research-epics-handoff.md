---
name: QML-research-epics-handoff
type: next-session-prompt
status: ready-to-paste
created: 2026-09-16
architecture_review_status: proposed — operator has not accepted the 2026-09-16 spine
---

# Next session — create epics and stories (do not launch from documentation-factory)

Paste the block below into a new session. Do not start videos/n8n/Hermes. Do not fill GAP-0085. Do not implement code. Documentation-factory has not launched this skill.

---

## Prompt to paste

Use the installed `bmad-create-epics-and-stories` skill on `C:/Users/Mubarak/Desktop/QMX`.

Slice from the **proposed** QML research-expansion absorption (not yet operator-accepted as architecture). If the operator has accepted ADR-0023 since this file was written, record that; if not, keep stories stamped against provisional DECs.

### Authority (read these, do not invent)

- `_docwork/riders/qml-research-expansion-2026-09-16.md` (operator-direct, ratified DEC-0380)
- `docs/decisions/ADR-0023-qml-research-expansion.md` (provisional)
- `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/ARCHITECTURE-SPINE.md` (local AD-1..AD-21, proposed)
- `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/REQUIREMENTS-ADDENDUM.md` (FR-RES-* proposed; sibling to GAP-0061; do not rewrite the 2026-08-21 PRD)
- `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/QML-EXPANSION.md`
- `docs/components/qml.md`, `qma-core.md`, `qma-daemon.md`, `qma-wire.md`, `qmb.md`
- `docs/scenarios/SCN-0017-stage0-honesty-envelope.md`
- `_docwork/feature_inventory.yaml` FEAT-0047..FEAT-0050
- `_docwork/qml-research-increment-brief.md`

Parents bind read-only: QL-1..QL-10, Workbench AD-1..AD-16, QMA AD-19, L17/L33. No new COMP. No new CT.

### First epic (mandatory)

**FEAT-0047 — seed bind + Stage 0 view (architecture AD-14 / DEC-0394).**

Acceptance (slice 0):

1. Configure `root_path` to the Stats seed tree; `PlainFileLibrarySource(root_path, source_id="strats")` replaces the in-memory two-file stub.
2. Snapshot per AD-4 include/exclude (research-corpus plugin config, not qma-core).
3. Mission/session pin `snapshot_ref`; `search` / `retrieve` / `cite` of `STRAT-000001` and dictionary entry `swing-high`.
4. QML vocabulary helper resolves `swing-high` from cited bytes the host passed in (no filesystem I/O in qml; no registry row).
5. Read-only Stage 0 projection of LAYOUT-DEMO preserves `entry_hypothesis` and unresolved F. No invented exits. No invented short side. Does **not** mint `research_ref`.
6. `register_library_kind("strats")` still refuses. No CT-33 mint. No population ingest.

Blocked by FEAT-0045, FEAT-0046, FEAT-0030 (see inventory reasons).

### Later epics (do not reorder ahead of FEAT-0047)

- FEAT-0048 — `qml.research` types + `research_ref` + host `research_root` blob store
- FEAT-0049 — mill `graduate_to_governed` + optional `seed_cite` (`origin` stays `"qma"`)
- FEAT-0050 — federated KnowledgeHit | ArtifactHit DTO (no `qml_candidate`, no `strats` hit_class)

Use `python C:/Users/Mubarak/.agents/skills/documentation-factory/scripts/validate_inventory.py --root C:/Users/Mubarak/Desktop/QMX --handoff FEAT-0047` (then 0048, 0049, 0050) so each epic inherits blockers, dependents, and wave-mates.

### Out of scope for these epics

GAP-0085 nouns; GAP-0063 generator; GAP-0073 hybrid index; GAP-0081 UI SDK; GAP-0061 (do not close); videos/n8n/Hermes; Workflows runtime; rewriting 239 dictionary entries; inventing exits on STRAT-000001; git subtree of Stats; a sixth COMP.

### After epics/stories

Stop. Mubarak's existing factory automation (attended epic-factory / Grok `/run-epics`, or `/queue-publish` + kanban) handles implementation. Do not launch factory lanes from the epics session. `main` moves only by the operator's squash-merge click.
