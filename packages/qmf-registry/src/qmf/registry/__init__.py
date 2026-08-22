"""qmf.registry — governed records, lineage, and promotion.

Roster package of the QMF V1 uv workspace. It re-exports the public CT-* surface as
it lands story by story.

Landed (Story 2.1): CT-06 per-kind, fingerprint-keyed registration records — the tiny
common header plus a kind-specific body, the addable-never-redefined
:class:`KindRegistry`, and a pure in-memory :class:`Registrar` whose stable id is
derived from an ``fp1`` fingerprint and whose byte-identical re-write is idempotent
while a true collision is refused and alarmed (DEC-0114, DEC-0108, DEC-0110).

Landed (Story 2.2): CT-07 append-only typed lineage edges — the ratified
:class:`EdgeType` vocabulary, the frozen :class:`LineageEdge` whose id is derived from
its ``fp1`` fingerprint and which serializes to the pinned JSONL line, and a pure
in-memory single-writer :class:`EdgeLog` that holds ``supersedes`` linear (one
resolvable head), leaves ``branches-from`` multi-headed, keeps a byte-identical
re-append idempotent while refusing and alarming a true collision, and rebuilds its
derived indexes from the edge evidence (DEC-0114, DEC-0158, DEC-0144, DEC-0119).

Every ``fp1`` fingerprint is computed in ``qmf-core`` and nowhere else; this module
imports only ``qmf.core``. Under default-deny no library imports ``qmf-registry`` —
registration and lineage are invoked by the application at the composition root
(DEC-0120). Durable persistence through ``qmf-data``'s store-seam is Story 2.4.
"""

from __future__ import annotations

from qmf.registry.lineage import (
    EDGE_CONTRACT_FORMAT_VERSION,
    EdgeAppendReceipt,
    EdgeLog,
    EdgeType,
    LineageEdge,
)
from qmf.registry.records import (
    CONTRACT_FORMAT_VERSION,
    RESERVED_KIND_NAMES,
    FieldSetKind,
    KindContract,
    KindRegistry,
    Registrar,
    RegistrationReceipt,
    RegistrationRecord,
    WriteOutcome,
)

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "EDGE_CONTRACT_FORMAT_VERSION",
    "RESERVED_KIND_NAMES",
    "EdgeAppendReceipt",
    "EdgeLog",
    "EdgeType",
    "FieldSetKind",
    "KindContract",
    "KindRegistry",
    "LineageEdge",
    "Registrar",
    "RegistrationReceipt",
    "RegistrationRecord",
    "WriteOutcome",
    "__version__",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
