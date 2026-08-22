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
deferred GAP-0016 gate.

Story 9.2 — the append-only lifecycle and the read-time state fold.
`ConfirmationRecord`, `InvalidationRecord`, and `InteractionRecord` are separate
append-only typed records referencing the object by `fp1`, each instant an
identity field of its own record; interaction records are the only permitted way
an object's state evolves, and each emits its CT-07 `LifecycleEdge` intent
(`confirmation` / `invalidation` / `interaction` / `confirmed-as`). `resolve_state`
folds an object's record stream to a knowledge time T — "still valid at T" is a
**read-time fold** (`ResolvedState`), never a stored field, and a record whose
instant follows T is not yet visible (look-ahead-safe). `refit` mints a **new**
artifact with a `supersedes` edge and keeps the lineage's first observed-at, so a
correction/refit never overwrites (FM-3). `admit_to_governed_library` is the FM-2
admission gate — an imprecise concept stays free in the ungoverned research lane,
clock-confirmed is legal. Invalidation never cascades automatically: a family
declares an `InvalidationPredicate` and a reader calls `resolve_cascade` to compute
cascade at read time from lineage.

Story 9.3 — evidence class as first-class identity, knowledge-time provenance, and
split-manifest governance. `read_confirmed` is the governed read requesting confirmed
evidence — it refuses an unconfirmed or provisional row with a `policy rejection`,
**never a silent filter** (FM-4), over the `EvidenceRow` seam both a `StructureObject`
and a `ResultLabel` satisfy. `may_consume` is the knowledge-time consumption rule
(`confirmed-at <= T`; equality is consumption), and `causally_precedes` the distinct
refuse-at-equal causality test. `structure_result_label` builds the CT-05 result label
from the **configured-family** producer identity plus input fingerprints, so an object
computed on a revised input receives a different label by construction; `world =
simulated` is refused (GAP-0048). `evaluate_citation` (`CitationKind`,
`GovernanceVerdict`) is the governed-evidence citation law — in-memory persists nothing,
a journal-event or result-label citation makes the object governed evidence — and
`promote_scanned` promotes only confirmed scan hits. `required_embargo_width` turns a
family's confirmation-delay bound into a split embargo width (an unbounded family is
excluded from split-governed evidence), and `admit_across_boundary` (`SplitAdmission`)
is the FM-7 boundary refusal, partitioning by confirmed-at.

The library returns fingerprintable content and never stamps records; the
composition root holds the `WriterId` and the per-writer sequence. It imports
**only** `qmf-core`. Later CT-17 surface (composites, sloped and
calendar-anchored families) arrives in later stories. Build, lint,
type-check, and test it through the workspace `poe` tasks — never in isolation.
