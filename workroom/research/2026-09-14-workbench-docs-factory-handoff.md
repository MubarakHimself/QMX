# Workbench docs-factory — handoff to bmad-create-epics-and-stories

Date: 2026-09-14. Skill just finished: documentation-factory Stage 9 (change mode). Next skill: `bmad-create-epics-and-stories`. Do not implement code in that sitting. Do not rewrite the PRD (GAP-0061).

## What landed (2026-09-14)

Spine `architecture-QMX-2026-09-14` local AD-1..AD-16 absorbed as DEC-0269..DEC-0284. Umbrella DEC-0285. Wiring-status reconcile DEC-0286 (`source-inspected` ≠ e2e). Cheap-veto DEC-0287. ADR-0022. Features FEAT-0033..FEAT-0039. Gaps GAP-0061, GAP-0062, GAP-0063 deferred; GAP-0085 ownership updated (nouns still open). No new COMP. No new CT id. Dead list preserved (DEC-0084, donor engines, QMA-paper).

Every doc this increment edited carries `verified: 2026-09-14`.

## Inventory commands (run from repo root)

```
python C:\Users\Mubarak\.agents\skills\documentation-factory\scripts\validate_inventory.py --root . --next
python C:\Users\Mubarak\.agents\skills\documentation-factory\scripts\validate_inventory.py --root . --waves
python C:\Users\Mubarak\.agents\skills\documentation-factory\scripts\validate_inventory.py --root . --handoff FEAT-0033
python C:\Users\Mubarak\.agents\skills\documentation-factory\scripts\validate_inventory.py --root . --handoff FEAT-0034
python C:\Users\Mubarak\.agents\skills\documentation-factory\scripts\validate_inventory.py --root . --handoff FEAT-0035
python C:\Users\Mubarak\.agents\skills\documentation-factory\scripts\validate_inventory.py --root . --handoff FEAT-0036
python C:\Users\Mubarak\.agents\skills\documentation-factory\scripts\validate_inventory.py --root . --handoff FEAT-0037
python C:\Users\Mubarak\.agents\skills\documentation-factory\scripts\validate_inventory.py --root . --handoff FEAT-0038
python C:\Users\Mubarak\.agents\skills\documentation-factory\scripts\validate_inventory.py --root . --handoff FEAT-0039
```

`--next` still prints FEAT-0001: the workbench slices sit on top of the existing planned inventory. Do not start FEAT-0033 before its blockers ship.

## Workbench features and actual waves (2026-09-14 inventory)

| FEAT | Wave | Blocked by | Wave-mates to serialize if they share a component |
|---|---|---|---|
| FEAT-0038 continuation + extensibility rungs 1–3 | 11 | FEAT-0042, FEAT-0041, FEAT-0027 | serialize with FEAT-0043 (both COMP-QMA-DAEMON) |
| FEAT-0039 QML generation authoring | 12 | FEAT-0030, FEAT-0007 | trails connect-wave by DEC-0287 A1 |
| FEAT-0034 Library projections | 14 | FEAT-0007, FEAT-0029, FEAT-0045 | serialize with FEAT-0035/0036 (COMP-QMB) |
| FEAT-0035 named analysis methods | 14 | FEAT-0029, FEAT-0027 | serialize with FEAT-0034/0036 |
| FEAT-0036 CLI robustness/sweep + data wrap | 14 | FEAT-0029 | serialize with FEAT-0034/0035 |
| FEAT-0033 QMA→QMB door + daemon compose + three lanes | 15 | FEAT-0044, FEAT-0042, FEAT-0029 | serialize with FEAT-0046 (COMP-QMA-CORE/DAEMON); delivers for FEAT-0037 |
| FEAT-0037 procedures as Graph Templates | 16 | FEAT-0033, FEAT-0046 | after the door |

Each spec must state, in its own prose: what must already exist (blockers with reasons), what this feature delivers that others wait on, what may run alongside (wave-mates).

## Do not

- Mint a sixth application
- Put a generator inside QMB
- Let QMA `import qmb` or assemble CT-33 JSON
- Extend CT-32 or B-4 with `lane` / `analysis_method`
- Fill GAP-0085 nouns, GAP-0063 algorithm, GAP-0062 host machine, or rewrite the PRD (GAP-0061)
- Revive DEC-0084 / donor engines / QMA-paper
- Treat source-inspected as e2e demonstrated
- Treat generated UI layouts as preference evidence

Implementation ships only through the factory lanes after epics exist.
