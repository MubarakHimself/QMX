"""Composition root surface (TN-2): doors → preflight → compose → fingerprint → seal.

The host is the only impure shell that owns ambient time, broker sessions,
secrets, async at the venue edge and doors, and real money. Story 25.3 mints
identity-bearing Compose records through the qmf-registry Registrar exactly
once per fingerprint. Story 25.4 persists the sealed composition occurrence
and append-only CT-07 lineage through the registry→data edge; a sink refusal
blocks readiness rather than dropping an edge. Story 25.5 binds doors first,
writes the boot-attempt record under the reserved supervisor WriterId, then
runs the ordered ceremony — only a door-bind failure exits nonzero; later
detected refusals enter stand-down-alive. Story 25.6 owns safe points,
stand-down-alive, watchdog/slice-progress, requested-restart exit 75, and the
SIGTERM/UNKNOWN shutdown contract. Story 25.14 evaluates light/heavy four-bound
claims over assembled definitions at Compose and refuses contradictions before
Seal — child modules never self-approve the effective composition class.
Story 25.16 proves host concurrency and backpressure under deterministic load
without inventing capacity numbers; seat concurrency is Story 26.19.
Child modules and doors never restamp, never hold a registry cache, and never
persist lineage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from qmn.host.boot_ceremony import (
    BOOT_BOUND_SURFACES,
    BOOT_CEREMONY_SURFACE,
    BOOT_STAGES,
    CHECK_MODE_EXIT_ON_REFUSAL,
    CHECK_MODE_OPENS_SEQUENCER,
    CHECK_MODE_PREFLIGHT_CHECKS,
    DOOR_BIND_FAILURE_EXIT_CODE,
    FULL_PREFLIGHT_CHECKS,
    HAS_OPERATOR_CLI,
    SUPERVISOR_ROLE,
    SUPERVISOR_STREAM,
    BootAttemptRecord,
    BootCeremonyOutcome,
    BoundSupervisorDoors,
    CompositionFingerprintInputs,
    InMemoryBootAttemptSink,
    PreflightFacts,
    SealedBootEpoch,
    WriterAllocation,
    allocate_writer_ids,
    bind_supervisor_doors,
    compute_composition_fp,
    preflight_checks_for_mode,
    reserved_supervisor_writer,
    run_boot_ceremony,
    run_check_mode,
    supervisor_writer_is_reserved,
)
from qmn.host.concurrency import (
    CONCURRENCY_SURFACE,
    SEAT_CONCURRENCY_OWNED_BY,
    BoundCrossingKind,
    BoundCrossingRecord,
    ConcurrencyLoad,
    ConcurrencyProofReport,
    InjectedBounds,
    prove_host_concurrency,
)
from qmn.host.light_heavy import (
    CHILD_MODULES_MAY_SELF_APPROVE,
    LIGHT_HEAVY_SURFACE,
    WORKLOAD_KINDS,
    CompositionClass,
    CompositionClassAssignment,
    FourBoundDeclaration,
    ResolvedCompositionClasses,
    WorkloadClaim,
    WorkloadKind,
    evaluate_workload_claim,
    guard_synchronous_placement,
    resolve_composition_classes,
    workload_claim_identity_content,
)
from qmn.host.lineage_persist import (
    COMPOSITION_LINEAGE_STREAM,
    COMPOSITION_OCCURRENCE_FORMAT_VERSION,
    COMPOSITION_OCCURRENCE_KIND,
    LINEAGE_PERSIST_SURFACE,
    OCCURRENCE_LINEAGE_EDGE_TYPE,
    CarriesLedgerEdgeRequest,
    CompositionCiteSet,
    CompositionLineageReceipt,
    carries_ledger_edge,
    composition_cite_set,
    continues_performance_edge,
    install_composition_occurrence_kind,
    persist_composition_lineage,
    persist_explicit_lineage_edge,
)
from qmn.host.registry_mint import (
    COMPOSE_KIND_FORMAT_VERSION,
    COMPOSE_RECORD_KINDS,
    DOOR_LOCAL_REGISTRY_CACHE,
    HAS_ALTERNATE_IDENTITY_FUNCTION,
    IDENTITY_FORBIDDEN_OCCURRENCE_KEYS,
    REGISTRY_MINT_SURFACE,
    ComposeOccurrenceEvidence,
    CompositionRootRegistry,
    compose_kind_contract,
    install_compose_kinds,
    mint_compose_record,
)
from qmn.host.supervise import (
    ASYNC_ALLOWED_SURFACES,
    CLEAN_STOP_EXIT_CODE,
    DOMAIN_BACKGROUND_THREADS_ALLOWED,
    DRAIN_WINDOW_BREACH_EXIT_CODE,
    EVENT_LOOP_COUNT,
    NODE_RESURRECT_SUBTYPE,
    OPERATOR_PRINCIPAL,
    REQUESTED_RESTART_EXIT_CODE,
    REQUESTED_RESTART_REASON,
    SUPERVISION_SURFACE,
    CommandFate,
    CrashLoopFold,
    CrashLoopVerdict,
    DrainOutcome,
    LifecycleState,
    LifecycleSupervisor,
    NotifyTransport,
    RecordingNotifyTransport,
    ResurrectReceipt,
    SafePointSnapshot,
    ShutdownKind,
    SliceProgressTrip,
    StandDownTrigger,
    StdlibSdNotifyTransport,
    SupervisionConfig,
    admit_under_lifecycle,
    evaluate_safe_point,
    notify_ready,
    notify_watchdog,
    notify_watchdog_trigger,
    sd_notify,
    supervision_process_model,
)

__all__ = [
    "ASYNC_ALLOWED_SURFACES",
    "BOOT_BOUND_SURFACES",
    "BOOT_CEREMONY_STEPS",
    "BOOT_CEREMONY_SURFACE",
    "BOOT_STAGES",
    "CHECK_MODE_EXIT_ON_REFUSAL",
    "CHECK_MODE_OPENS_SEQUENCER",
    "CHECK_MODE_PREFLIGHT_CHECKS",
    "CHILD_MODULES_MAY_SELF_APPROVE",
    "CLEAN_STOP_EXIT_CODE",
    "COMPOSE_KIND_FORMAT_VERSION",
    "COMPOSE_RECORD_KINDS",
    "COMPOSITION_LINEAGE_STREAM",
    "COMPOSITION_OCCURRENCE_FORMAT_VERSION",
    "COMPOSITION_OCCURRENCE_KIND",
    "COMPOSITION_ROOT_SURFACE",
    "CONCURRENCY_SURFACE",
    "DOMAIN_BACKGROUND_THREADS_ALLOWED",
    "DOOR_BIND_FAILURE_EXIT_CODE",
    "DOOR_LOCAL_REGISTRY_CACHE",
    "DRAIN_WINDOW_BREACH_EXIT_CODE",
    "EVENT_LOOP_COUNT",
    "FULL_PREFLIGHT_CHECKS",
    "HAS_ALTERNATE_IDENTITY_FUNCTION",
    "HAS_OPERATOR_CLI",
    "IDENTITY_FORBIDDEN_OCCURRENCE_KEYS",
    "LIGHT_HEAVY_SURFACE",
    "LINEAGE_PERSIST_SURFACE",
    "NODE_RESURRECT_SUBTYPE",
    "OCCURRENCE_LINEAGE_EDGE_TYPE",
    "OPERATOR_PRINCIPAL",
    "REGISTRY_MINT_SURFACE",
    "REQUESTED_RESTART_EXIT_CODE",
    "REQUESTED_RESTART_REASON",
    "SEAT_CONCURRENCY_OWNED_BY",
    "SUPERVISION_SURFACE",
    "SUPERVISOR_ROLE",
    "SUPERVISOR_STREAM",
    "WORKLOAD_KINDS",
    "BootAttemptRecord",
    "BootCeremonyOutcome",
    "BoundCrossingKind",
    "BoundCrossingRecord",
    "BoundSupervisorDoors",
    "CarriesLedgerEdgeRequest",
    "CommandFate",
    "ComposeOccurrenceEvidence",
    "CompositionCiteSet",
    "CompositionClass",
    "CompositionClassAssignment",
    "CompositionFingerprintInputs",
    "CompositionLineageReceipt",
    "CompositionRootRegistry",
    "ConcurrencyLoad",
    "ConcurrencyProofReport",
    "CrashLoopFold",
    "CrashLoopVerdict",
    "DrainOutcome",
    "FourBoundDeclaration",
    "InMemoryBootAttemptSink",
    "InjectedBounds",
    "LifecycleState",
    "LifecycleSupervisor",
    "NotifyTransport",
    "PreflightFacts",
    "RecordingNotifyTransport",
    "ResolvedCompositionClasses",
    "ResurrectReceipt",
    "SafePointSnapshot",
    "SealedBootEpoch",
    "SealedComposition",
    "ShutdownKind",
    "SliceProgressTrip",
    "StandDownTrigger",
    "StdlibSdNotifyTransport",
    "SupervisionConfig",
    "WorkloadClaim",
    "WorkloadKind",
    "WriterAllocation",
    "admit_under_lifecycle",
    "allocate_writer_ids",
    "bind_supervisor_doors",
    "carries_ledger_edge",
    "ceremony_steps",
    "compose_kind_contract",
    "composition_cite_set",
    "compute_composition_fp",
    "continues_performance_edge",
    "evaluate_safe_point",
    "evaluate_workload_claim",
    "guard_synchronous_placement",
    "install_compose_kinds",
    "install_composition_occurrence_kind",
    "mint_compose_record",
    "notify_ready",
    "notify_watchdog",
    "notify_watchdog_trigger",
    "persist_composition_lineage",
    "persist_explicit_lineage_edge",
    "preflight_checks_for_mode",
    "prove_host_concurrency",
    "reserved_supervisor_writer",
    "resolve_composition_classes",
    "run_boot_ceremony",
    "run_check_mode",
    "sd_notify",
    "supervision_process_model",
    "supervisor_writer_is_reserved",
    "workload_claim_identity_content",
]

COMPOSITION_ROOT_SURFACE: Final[str] = "qmn.host"
BOOT_CEREMONY_STEPS: Final[tuple[str, ...]] = (
    "preflight",
    "compose",
    "fingerprint",
    "seal",
)


@dataclass(frozen=True, slots=True)
class SealedComposition:
    """Marker for one sealed boot-epoch composition.

    Lineage persistence (Story 25.4) binds ``composition_fp`` and readiness after
    the registry→data sink accepts the occurrence and its edges. The scaffold
    defaults keep ceremony labels available before that write. Story 25.5 seals
    through :func:`run_boot_ceremony` / :class:`SealedBootEpoch`.
    """

    surface: str = COMPOSITION_ROOT_SURFACE
    sealed: bool = True
    ready: bool = False

    def steps(self) -> tuple[str, ...]:
        return BOOT_CEREMONY_STEPS


def ceremony_steps() -> tuple[str, ...]:
    """Ordered compose → fingerprint → seal ceremony (plus preflight gate)."""
    return BOOT_CEREMONY_STEPS
