# qmf-indicators

The two-mode CT-16 indicator protocol and wrappers around the pinned canonical arithmetic reference.

`qmf-indicators` imports as `qmf.indicators` under the PEP 420 `qmf.*` implicit namespace
(there is no `qmf/__init__.py` in any distribution). It versions in SemVer lockstep with the other six roster packages (0.x until the V1 blueprint ships).

## Status

Scaffold (Story 1.1). The package declares its identity, its dependency
direction, a benchmark-harness slot, and its Tier-1 test surface. Public
contracts arrive in later stories. Build, lint, type-check, and test it through
the workspace `poe` tasks — never in isolation.
