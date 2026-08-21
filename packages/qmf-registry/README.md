# qmf-registry

Per-kind records, fingerprint-derived ids, append-only typed lineage edges, and the human-signed promotion skeleton.

`qmf-registry` imports as `qmf.registry` under the PEP 420 `qmf.*` implicit namespace
(there is no `qmf/__init__.py` in any distribution). It versions in SemVer lockstep with the other six roster packages (0.x until the V1 blueprint ships).

## Status

Scaffold (Story 1.1). The package declares its identity, its dependency
direction, a benchmark-harness slot, and its Tier-1 test surface. Public
contracts arrive in later stories. Build, lint, type-check, and test it through
the workspace `poe` tasks — never in isolation.
