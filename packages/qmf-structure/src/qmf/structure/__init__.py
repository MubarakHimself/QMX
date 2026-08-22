"""qmf.structure — causal chart-object families.

Roster package of the QMF V1 uv workspace. It re-exports the public CT-17 surface as it
lands story by story.

Landed (Story 9.1): the causal structure object mint and the in-component emission
invariant. :class:`FamilyIdentity` (opaque id + version + open, family-declared
geometry), :class:`ConfirmationRule` (the declared 'confirmed the moment X happens'
rule), and the :class:`StructureFamily` ``typing.Protocol`` seam with its reference
:class:`DeclaredFamily`; :class:`AnchorSpan` (start/end instants and exact-``Price``
bounds, frozen at observation); :class:`StructureObject`, minted **once at observation**
carrying family identity + version, exact-rational parameters, its confirmation rule,
its anchor span, ``observed_at`` (knowledge time — known-at, never event time), and its
evidence class — every field identity-bearing, the object never mutated; and
:func:`check_emission_invariant`, enforcing
``anchor.start <= anchor.end <= observed_at <= confirmed_at <= invalidated_at`` and
``observed_at >= the maximum evidence time of every consumed input`` as an
``invalid input`` refusal on violation (FM-1), the interim look-ahead guard independent
of the deferred GAP-0016 gate (DEC-0129, DEC-0121, DEC-0114).

Landed (Story 9.2): the append-only lifecycle and the read-time state fold.
:class:`ConfirmationRecord`, :class:`InvalidationRecord`, and :class:`InteractionRecord`
are separate append-only typed records referencing the object by ``fp1`` fingerprint, each
instant an identity field of its own record; interaction records are the only permitted
way an object's state evolves. :func:`resolve_state` folds an object's record stream to a
knowledge time T — "still valid at T" is a **read-time fold** (:class:`ResolvedState`),
never a stored field. :func:`refit` mints a new artifact with a ``supersedes``
:class:`LifecycleEdge` and keeps the lineage's first observed-at, so a correction never
overwrites (FM-3). :func:`admit_to_governed_library` is the FM-2 admission gate (imprecise
concepts stay in the ungoverned research lane; clock-confirmed is legal). Invalidation
never cascades automatically: a family declares an :class:`InvalidationPredicate` and a
reader calls :func:`resolve_cascade` to compute cascade at read time (DEC-0129, DEC-0131,
DEC-0114).

Every ``fp1`` fingerprint is computed in ``qmf-core`` and nowhere else; this package
imports **only** ``qmf.core`` in V1 (the default-deny dependency direction, L30). The
library returns fingerprintable content and never stamps records — the composition root
holds the ``WriterId`` and the gapless per-(writer, kind) sequence and mints the registry
records (DEC-0120, DEC-0129).
"""

from __future__ import annotations

from qmf.structure.lifecycle import (
    CascadeResolution,
    ConfirmationRecord,
    InteractionRecord,
    InvalidationPredicate,
    InvalidationRecord,
    LifecycleEdge,
    LifecycleEdgeKind,
    LifecycleRecord,
    Refit,
    ResolvedState,
    admit_to_governed_library,
    refit,
    resolve_cascade,
    resolve_state,
)
from qmf.structure.objects import (
    CONTRACT_FORMAT_VERSION,
    KNOWN_GEOMETRIES,
    AnchorSpan,
    ConfirmationRule,
    DeclaredFamily,
    EmissionWitness,
    FamilyIdentity,
    StructureFamily,
    StructureObject,
    check_emission_invariant,
)

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "KNOWN_GEOMETRIES",
    "AnchorSpan",
    "CascadeResolution",
    "ConfirmationRecord",
    "ConfirmationRule",
    "DeclaredFamily",
    "EmissionWitness",
    "FamilyIdentity",
    "InteractionRecord",
    "InvalidationPredicate",
    "InvalidationRecord",
    "LifecycleEdge",
    "LifecycleEdgeKind",
    "LifecycleRecord",
    "Refit",
    "ResolvedState",
    "StructureFamily",
    "StructureObject",
    "__version__",
    "admit_to_governed_library",
    "check_emission_invariant",
    "refit",
    "resolve_cascade",
    "resolve_state",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
