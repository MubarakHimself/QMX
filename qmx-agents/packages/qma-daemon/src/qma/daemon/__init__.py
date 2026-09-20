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

from qma.daemon.capabilities import (
    AGENT_PATH_ENFORCEMENT_EVENTS,
    AgentCapabilityStore,
    PermissionPolicyEnforcer,
    spawn_agent,
)
from qma.daemon.discovery import (
    CONTRIBUTION_LISTING_OCCUPANCY,
    FEDERATED_SEARCH_OCCUPANCY,
    ContributionListingService,
    FederatedDiscoveryService,
    FederatedSearch,
)
from qma.daemon.hooks import (
    AGENT_REACHABLE_WRITE_VERBS,
    BYPASS_WRITE_PATHS,
    HookRegistry,
)
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
from qma.daemon.knowledge import KnowledgeService, KnowledgeSourceRegistry
from qma.daemon.memory import MemoryAdmissionGate, MemoryProviderRegistry
from qma.daemon.persistence import (
    PersistenceStartupEvidence,
    PersistenceSubstrate,
)
from qma.daemon.persistence.lifecycle import DaemonStoreLifecycle
from qma.daemon.process import DaemonProcess
from qma.daemon.sessions import (
    PRODUCT_SESSION_EXISTED_AT_INSPECT_SHA,
    PRODUCT_SESSION_OCCUPANCY,
    PRODUCT_SESSION_OWNER,
    ProductSession,
    ProductSessionContext,
    ProductSessionService,
)
from qma.daemon.staging import AdmissionPipeline, ProposalGate
from qma.daemon.taskgraph import (
    CompileRequest,
    MissionCompiler,
    TaskGraphDispatcher,
    TaskGraphStateService,
    claim_durable_edges_at_inspect_sha,
    refuse_qmb_occupancy_write,
    refuse_second_scheduler,
)
from qma.daemon.telemetry import RetentionJob, TelemetryStore

__all__ = [
    "AGENT_PATH_ENFORCEMENT_EVENTS",
    "AGENT_REACHABLE_WRITE_VERBS",
    "BYPASS_WRITE_PATHS",
    "CONTRIBUTION_LISTING_OCCUPANCY",
    "FEDERATED_SEARCH_OCCUPANCY",
    "PRODUCT_SESSION_EXISTED_AT_INSPECT_SHA",
    "PRODUCT_SESSION_OCCUPANCY",
    "PRODUCT_SESSION_OWNER",
    "AdmissionPipeline",
    "AgentCapabilityStore",
    "AuthoritativeJournal",
    "CompileRequest",
    "ContributionListingService",
    "DaemonClock",
    "DaemonProcess",
    "DaemonStoreLifecycle",
    "FederatedDiscoveryService",
    "FederatedSearch",
    "FoldContract",
    "FoldContractRegistry",
    "FoldMetadata",
    "GovernedVariableRegistry",
    "HookRegistry",
    "KnowledgeService",
    "KnowledgeSourceRegistry",
    "MemoryAdmissionGate",
    "MemoryProviderRegistry",
    "MissionCompiler",
    "PermissionPolicyEnforcer",
    "PersistenceStartupEvidence",
    "PersistenceSubstrate",
    "ProductSession",
    "ProductSessionContext",
    "ProductSessionService",
    "ProposalGate",
    "RetentionJob",
    "StoreOwnershipRegistry",
    "StoreRegistry",
    "TaskGraphDispatcher",
    "TaskGraphStateService",
    "TelemetryStore",
    "__version__",
    "claim_durable_edges_at_inspect_sha",
    "order_by_announcement_journal_seq",
    "refuse_qmb_occupancy_write",
    "refuse_second_scheduler",
    "spawn_agent",
]

# Display-only provenance — never identity content (AR-Q11; DEC-0335).
__version__ = "0.1.0"
