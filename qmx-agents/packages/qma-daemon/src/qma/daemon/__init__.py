"""qma.daemon — sole QMA runtime and sole writer.

The persistence substrate (FR-Q22) is the sole durable-write boundary for the
event journal, SQLite store, and artifact store through qmf-data sinks. The
authoritative journal (FR-Q23–FR-Q25) allocates global ``journal_seq``, enforces
the closed store list, announcement law, durable-clock stamps, and v1 fold
contracts. Store-class ownership (FR-Q26) and the governed variable registry
(FR-Q36) bind write paths and configurable numbers. Store lifecycle (FR-Q37)
covers versioned migration, encrypted backup, and controlled restoration.
SemVer is display-only provenance in lockstep with the QMF workspace (AR-Q11).
"""

from __future__ import annotations

from qma.daemon.journal import (
    AuthoritativeJournal,
    DaemonClock,
    FoldContract,
    FoldContractRegistry,
    FoldMetadata,
    GovernedVariableRegistry,
    StoreOwnershipRegistry,
    StoreRegistry,
    order_by_announcement_journal_seq,
)
from qma.daemon.persistence import (
    PersistenceStartupEvidence,
    PersistenceSubstrate,
)
from qma.daemon.persistence.lifecycle import DaemonStoreLifecycle
from qma.daemon.staging import ProposalGate

__all__ = [
    "AuthoritativeJournal",
    "DaemonClock",
    "DaemonStoreLifecycle",
    "FoldContract",
    "FoldContractRegistry",
    "FoldMetadata",
    "GovernedVariableRegistry",
    "PersistenceStartupEvidence",
    "PersistenceSubstrate",
    "ProposalGate",
    "StoreOwnershipRegistry",
    "StoreRegistry",
    "order_by_announcement_journal_seq",
    "__version__",
]

# Display-only provenance — never identity content (AR-Q11; DEC-0335).
__version__ = "0.1.0"
