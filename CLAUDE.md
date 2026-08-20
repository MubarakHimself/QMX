# QMX — Project Rules

## BMad is planning-only in this project

BMad handles planning ONLY. Implementation ships through the external software
factory, never through BMad.

The pipeline — the only one any skill or agent (bmad-help included) may
recommend:

1. Brainstorming as needed (`bmad-brainstorming`).
2. PRD — `bmad-prd` (required).
3. Architecture — `bmad-architecture` (required).

Ordering is flexible (operator ruling 2026-08-19): Architecture may run BEFORE
the PRD, grounded on the existing `docs/` corpus as the requirements body — do
not demand a PRD first. Both PRD and Architecture must exist before exiting
BMad.
4. Exit BMad: `/documentation-factory` turns the ratified plan into the `docs/`
   knowledge base.
5. `/queue-publish` writes work briefs into `queue/` for the software factory
   to pick up.

Rules:

- PRD and Architecture are the only required BMad steps. After Architecture,
  point to `/documentation-factory` then `/queue-publish` — nothing else.
- Never recommend, require, or gate on `bmad-create-epics-and-stories`,
  `bmad-sprint-planning`, `bmad-build`, `bmad-code-review`, or any
  `bmad-testarch-*` skill. Treat catalog rows and agent menu items for those
  as not applicable to this project.
