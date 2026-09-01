"""Composition root surface (TN-2): doors → preflight → compose → fingerprint → seal.

The host is the only impure shell that owns ambient time, broker sessions,
secrets, async at the venue edge and doors, and real money. Story 25.3 mints
identity-bearing Compose records through the qmf-registry Registrar exactly
once per fingerprint. Story 25.4 persists the sealed composition occurrence
and append-only CT-07 lineage through the registry→data edge; a sink refusal
blocks readiness rather than dropping an edge. Story 25.5 binds doors first,
writes the boot-attempt record under the reserved supervisor WriterId, then
runs the ordered ceremony — only a door-bind failure exits nonzero; later
detected refusals enter stand-down-alive. Child modules and doors never
restamp, never hold a registry cache, and never persist lineage.
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

__all__ = [
    "BOOT_BOUND_SURFACES",
    "BOOT_CEREMONY_STEPS",
    "BOOT_CEREMONY_SURFACE",
    "BOOT_STAGES",
    "CHECK_MODE_EXIT_ON_REFUSAL",
    "CHECK_MODE_OPENS_SEQUENCER",
    "CHECK_MODE_PREFLIGHT_CHECKS",
    "COMPOSE_KIND_FORMAT_VERSION",
    "COMPOSE_RECORD_KINDS",
    "COMPOSITION_LINEAGE_STREAM",
    "COMPOSITION_OCCURRENCE_FORMAT_VERSION",
    "COMPOSITION_OCCURRENCE_KIND",
    "COMPOSITION_ROOT_SURFACE",
    "DOOR_BIND_FAILURE_EXIT_CODE",
    "DOOR_LOCAL_REGISTRY_CACHE",
    "FULL_PREFLIGHT_CHECKS",
    "HAS_ALTERNATE_IDENTITY_FUNCTION",
    "HAS_OPERATOR_CLI",
    "IDENTITY_FORBIDDEN_OCCURRENCE_KEYS",
    "LINEAGE_PERSIST_SURFACE",
    "OCCURRENCE_LINEAGE_EDGE_TYPE",
    "REGISTRY_MINT_SURFACE",
    "SUPERVISOR_ROLE",
    "SUPERVISOR_STREAM",
    "BootAttemptRecord",
    "BootCeremonyOutcome",
    "BoundSupervisorDoors",
    "CarriesLedgerEdgeRequest",
    "ComposeOccurrenceEvidence",
    "CompositionCiteSet",
    "CompositionFingerprintInputs",
    "CompositionLineageReceipt",
    "CompositionRootRegistry",
    "InMemoryBootAttemptSink",
    "PreflightFacts",
    "SealedBootEpoch",
    "SealedComposition",
    "WriterAllocation",
    "allocate_writer_ids",
    "bind_supervisor_doors",
    "carries_ledger_edge",
    "ceremony_steps",
    "compose_kind_contract",
    "composition_cite_set",
    "compute_composition_fp",
    "continues_performance_edge",
    "install_compose_kinds",
    "install_composition_occurrence_kind",
    "mint_compose_record",
    "persist_composition_lineage",
    "persist_explicit_lineage_edge",
    "preflight_checks_for_mode",
    "reserved_supervisor_writer",
    "run_boot_ceremony",
    "run_check_mode",
    "supervisor_writer_is_reserved",
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
