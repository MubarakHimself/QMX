"""qma.daemon — sole QMA runtime and sole writer.

The persistence substrate (FR-Q22) is the sole durable-write boundary for the
event journal, SQLite store, and artifact store through qmf-data sinks. SemVer
is display-only provenance in lockstep with the QMF workspace (AR-Q11).
"""

from __future__ import annotations

from qma.daemon.persistence import (
    PersistenceStartupEvidence,
    PersistenceSubstrate,
)

__all__ = [
    "PersistenceStartupEvidence",
    "PersistenceSubstrate",
    "__version__",
]

# Display-only provenance — never identity content (AR-Q11; DEC-0335).
__version__ = "0.1.0"
