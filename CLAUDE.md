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
5. `bmad-create-epics-and-stories` breaks the plan into epics and stories
   (re-enabled by operator ruling 2026-08-20).
6. Implementation runs in the factory lanes only: the attended epic-factory
   (Claude plugin *or* Grok plugin — one background workflow per epic in a
   worktree, merging to `integration`) or `/queue-publish` + to-kanban cards
   for the unattended engine lane. Grok models: 4.5 workhorse, 4.6
   orchestrator + reviewer. `main` moves only by the operator's own
   squash-merge click.

Rules:

- PRD and Architecture are the only required BMad steps. After Architecture:
  documentation-factory, then epics-and-stories, then a factory lane —
  nothing else.
- Never recommend, require, or gate on `bmad-sprint-planning`, `bmad-build`,
  or any `bmad-testarch-*` skill. Treat catalog rows and agent menu items for
  those as not applicable to this project. (`bmad-code-review` is allowed —
  it is the reviewer's skill inside the factory lanes.)
