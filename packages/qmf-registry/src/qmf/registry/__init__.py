"""qmf.registry — governed records, lineage, and promotion.

Roster package of the QMF V1 uv workspace. It re-exports the public CT-* surface as
it lands story by story. First landed (Story 2.1): CT-06 per-kind, fingerprint-keyed
registration records — the tiny common header plus a kind-specific body, the
addable-never-redefined :class:`KindRegistry`, and a pure in-memory :class:`Registrar`
whose stable id is derived from an ``fp1`` fingerprint and whose byte-identical
re-write is idempotent while a true collision is refused and alarmed (DEC-0114,
DEC-0108, DEC-0110).

Every ``fp1`` fingerprint is computed in ``qmf-core`` and nowhere else; this module
imports only ``qmf.core``. Under default-deny no library imports ``qmf-registry`` —
registration is invoked by the application at the composition root (DEC-0120).
Durable persistence through ``qmf-data``'s store-seam is Story 2.4.
"""

from __future__ import annotations

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
    "RESERVED_KIND_NAMES",
    "FieldSetKind",
    "KindContract",
    "KindRegistry",
    "Registrar",
    "RegistrationReceipt",
    "RegistrationRecord",
    "WriteOutcome",
    "__version__",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
