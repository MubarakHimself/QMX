# qmf-calendar-forex

The first market-hours calendar extension. Off-roster, on its own SemVer ladder, with tzdata pinned.

`qmf-calendar-forex` imports as `qmf.calendar_forex` under the PEP 420 `qmf.*` implicit namespace
(there is no `qmf/__init__.py` in any distribution). As an off-roster extension it rides its own SemVer ladder, independent of roster lockstep; a tzdata pin change is at minimum a minor bump.

## Status

Scaffold (Story 1.1). The package declares its identity, its dependency
direction, a benchmark-harness slot, and its Tier-1 test surface. Public
contracts arrive in later stories. Build, lint, type-check, and test it through
the workspace `poe` tasks — never in isolation.
