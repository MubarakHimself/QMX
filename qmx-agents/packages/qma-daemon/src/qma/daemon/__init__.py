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
from qma.daemon.diagnosis import (
    DIAGNOSIS_EXISTED_AT_INSPECT_SHA,
    DIAGNOSIS_OWNER,
    DIAGNOSIS_QUERY_NAME,
    Diagnosis,
    DiagnosisQueryService,
    claim_diagnosis_query_at_inspect_sha,
    classify_failure_class,
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
from qma.daemon.observability_boundary import (
    QMB_LOGSINK_MAY_REMAIN,
    THIRD_LOGGER_MINTED,
    emit_telemetry_from_hook,
    mint_third_logger,
    place_typed_failure,
)
from qma.daemon.operator_log import (
    FOURTH_OBSERVABILITY_COMP_MINTED,
    LOGS_ARE_NOT_EVIDENCE,
    LOGS_ARE_NOT_JOURNALS,
    OPERATOR_LOG_REQUIRED_FIELDS,
    OPERATOR_LOGGER_EXISTED_AT_INSPECT_SHA,
    JsonLineFormatter,
    claim_operator_logger_at_inspect_sha,
    configure_daemon_logging,
    emit_operator_event,
)
from qma.daemon.persistence import (
    PersistenceStartupEvidence,
    PersistenceSubstrate,
)
from qma.daemon.persistence.lifecycle import DaemonStoreLifecycle
from qma.daemon.plugins import (
    ExportScanReport,
    PackLifecycleFixture,
    PackTransition,
    claim_gap_0098_closed,
)
from qma.daemon.process import DaemonProcess
from qma.daemon.sessions import (
    PRODUCT_SESSION_EXISTED_AT_INSPECT_SHA,
    PRODUCT_SESSION_OCCUPANCY,
    PRODUCT_SESSION_OWNER,
    ProductSession,
    ProductSessionContext,
    ProductSessionService,
)
from qma.daemon.staging import (
    AdmissionPipeline,
    ChangeRequest,
    ChangeRequestFixture,
    ProposalGate,
)
from qma.daemon.taskgraph import (
    CompileRequest,
    MissionCompiler,
    TaskGraphDispatcher,
    TaskGraphStateService,
    claim_durable_edges_at_inspect_sha,
    refuse_merge_remote_worker_outbox,
    refuse_qmb_occupancy_write,
    refuse_second_scheduler,
)
from qma.daemon.taskgraph.restart_fixture import (
    OutboxRestartFixture,
    refuse_second_logical_b,
)
from qma.daemon.telemetry import RetentionJob, TelemetryStore

__all__ = [
    "AGENT_PATH_ENFORCEMENT_EVENTS",
    "AGENT_REACHABLE_WRITE_VERBS",
    "BYPASS_WRITE_PATHS",
    "CONTRIBUTION_LISTING_OCCUPANCY",
    "DIAGNOSIS_EXISTED_AT_INSPECT_SHA",
    "DIAGNOSIS_OWNER",
    "DIAGNOSIS_QUERY_NAME",
    "FEDERATED_SEARCH_OCCUPANCY",
    "FOURTH_OBSERVABILITY_COMP_MINTED",
    "LOGS_ARE_NOT_EVIDENCE",
    "LOGS_ARE_NOT_JOURNALS",
    "OPERATOR_LOGGER_EXISTED_AT_INSPECT_SHA",
    "OPERATOR_LOG_REQUIRED_FIELDS",
    "PRODUCT_SESSION_EXISTED_AT_INSPECT_SHA",
    "PRODUCT_SESSION_OCCUPANCY",
    "PRODUCT_SESSION_OWNER",
    "QMB_LOGSINK_MAY_REMAIN",
    "THIRD_LOGGER_MINTED",
    "AdmissionPipeline",
    "AgentCapabilityStore",
    "AuthoritativeJournal",
    "ChangeRequest",
    "ChangeRequestFixture",
    "CompileRequest",
    "ContributionListingService",
    "DaemonClock",
    "DaemonProcess",
    "DaemonStoreLifecycle",
    "Diagnosis",
    "DiagnosisQueryService",
    "ExportScanReport",
    "FederatedDiscoveryService",
    "FederatedSearch",
    "FoldContract",
    "FoldContractRegistry",
    "FoldMetadata",
    "GovernedVariableRegistry",
    "HookRegistry",
    "JsonLineFormatter",
    "KnowledgeService",
    "KnowledgeSourceRegistry",
    "MemoryAdmissionGate",
    "MemoryProviderRegistry",
    "MissionCompiler",
    "OutboxRestartFixture",
    "PackLifecycleFixture",
    "PackTransition",
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
    "claim_diagnosis_query_at_inspect_sha",
    "claim_durable_edges_at_inspect_sha",
    "claim_gap_0098_closed",
    "claim_operator_logger_at_inspect_sha",
    "classify_failure_class",
    "configure_daemon_logging",
    "emit_operator_event",
    "emit_telemetry_from_hook",
    "mint_third_logger",
    "order_by_announcement_journal_seq",
    "place_typed_failure",
    "refuse_merge_remote_worker_outbox",
    "refuse_qmb_occupancy_write",
    "refuse_second_logical_b",
    "refuse_second_scheduler",
    "spawn_agent",
]

# Display-only provenance — never identity content (AR-Q11; DEC-0335).
__version__ = "0.1.0"
