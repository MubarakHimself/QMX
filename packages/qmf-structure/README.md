# qmf-structure

QMX-owned causal chart-object families under the CT-17 lifecycle law.

`qmf-structure` imports as `qmf.structure` under the PEP 420 `qmf.*` implicit namespace
(there is no `qmf/__init__.py` in any distribution). It versions in SemVer lockstep with the other six roster packages (0.x until the V1 blueprint ships).

## Status

Story 9.1 — the causal structure object mint and the in-component emission
invariant. `FamilyIdentity`, `ConfirmationRule`, and the `StructureFamily`
`typing.Protocol` seam (with its reference `DeclaredFamily`); `AnchorSpan`
(start/end instants and exact-`Price` bounds, frozen at observation);
`StructureObject`, minted **once at observation** carrying family identity +
version, exact-rational parameters, its confirmation rule, its anchor span,
`observed_at` (knowledge time — known-at, never event time), and its evidence
class, every field identity-bearing and the object never mutated; and
`check_emission_invariant`, enforcing
`anchor.start <= anchor.end <= observed_at <= confirmed_at <= invalidated_at`
and `observed_at >= max consumed-input evidence time` as an `invalid input`
refusal on violation (FM-1) — the interim look-ahead guard, independent of the
deferred GAP-0016 gate. The library returns fingerprintable content and never
stamps records; the composition root holds the `WriterId` and the per-writer
sequence. It imports **only** `qmf-core`. Later CT-17 surface (lifecycle and
interaction records, composites, sloped and calendar-anchored families, splits)
arrives in later stories. Build, lint, type-check, and test it through the
workspace `poe` tasks — never in isolation.
