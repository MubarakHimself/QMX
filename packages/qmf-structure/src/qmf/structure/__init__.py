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

Every ``fp1`` fingerprint is computed in ``qmf-core`` and nowhere else; this package
imports **only** ``qmf.core`` in V1 (the default-deny dependency direction, L30). The
library returns fingerprintable content and never stamps records — the composition root
holds the ``WriterId`` and the gapless per-(writer, kind) sequence and mints the registry
records (DEC-0120, DEC-0129).
"""

from __future__ import annotations

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
    "ConfirmationRule",
    "DeclaredFamily",
    "EmissionWitness",
    "FamilyIdentity",
    "StructureFamily",
    "StructureObject",
    "__version__",
    "check_emission_invariant",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
