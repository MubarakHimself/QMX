"""qma.core — definitions-only QMA SDK package.

Ontology, ports, plugin contribution surface, refusal variants, content
addressing, and closed vocabularies. Depends only on ``qmf-core``. Runs nothing
and writes nothing (DEC-0335). SemVer is display-only provenance in lockstep with
the QMF workspace (AR-Q11).
"""

from __future__ import annotations

from qma.core.content import content_address, tree_digest
from qma.core.foundation import (
    CorrelationId,
    Fingerprint,
    Instant,
    Money,
    Ok,
    Result,
    TypedRefusal,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
)

__all__ = [
    "CorrelationId",
    "Fingerprint",
    "Instant",
    "Money",
    "Ok",
    "Result",
    "TypedRefusal",
    "WriterId",
    "__version__",
    "content_address",
    "fingerprint",
    "is_ok",
    "is_refusal",
    "tree_digest",
]

# Display-only provenance — never identity content (AR-Q11; DEC-0335).
__version__ = "0.1.0"
