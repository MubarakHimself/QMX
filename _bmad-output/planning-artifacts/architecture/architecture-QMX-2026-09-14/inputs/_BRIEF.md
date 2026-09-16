# Investigation brief — QMX strategy-experimentation architecture

This sitting: **architecture only**. Planning on `main` (this checkout). Product source lives on `integration` at `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`. Do not switch branches, commit, merge, implement UI, or use Penpot. Ignore generated layouts and reactions to them.

## Standing laws (do not reopen)

- QMF is a toolbox, not an application. Applications (QMB, QML, QMN, QMA) are built ON it.
- Default-deny QMF imports; only `qmf-registry → qmf-data` inside the roster. Nothing but `qmn.venue` imports `qmf-venue`. QMB/QML/QMA never import `qmf-venue`.
- Exact money/time/fingerprints/typed refusals. Worlds: `live | replay | simulated` (simulated reserved-unusable until GAP-0048).
- Bots trade; Books control bots; BMS accounts for Books; only a human promotes into the live zone.
- QMB is a library + CLI, never an engine/kernel. Pure `run()` returns values; the orchestrator writes evidence.
- QMA's only money-path output is a candidate a human promotes. No QMA execution tool, paper included.
- Paper-before-promotion happens OUTSIDE the node (DEC-0261). Node has no per-bot paper lane.
- Ordinary Python is always legal; governed evidence requires graduation (L33).
- Build-our-own: borrow donor mechanisms, never donor engines or foreign platform contracts.
- Configurable = UI-editable at platform level.

## Classification required for every capability

`reuse | connect | extend | new | undecided`

Evidence levels: `user-intent | documented-design | source-inspected | behavior-demonstrated`

Class/test existence is not end-to-end proof. Stale docs are not proof code is absent. CT-47 is `defined-unwired` in docs while integration source exists — reconcile, do not pick one silently.

## Output contract

Write one Markdown file at the path given in your prompt. Lead with a compact table, then source-linked findings. End with: (1) what already exists, (2) missing wiring vs missing function, (3) recommended architectural ownership, (4) open questions that need an AD vs can stay Deferred. Cite `path:line` or `git show integration:path`.
