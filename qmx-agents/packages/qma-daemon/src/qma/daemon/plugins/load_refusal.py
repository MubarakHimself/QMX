"""Load-refusal law and daemon continuity across plugin refusal (FR-Q70; CT-42).

Hard startup errors abort naming the offending unit. Explicit install / enable /
reload commands return a typed refusal, dispose that plugin's scope LIFO, and
leave the running daemon, leases, Tasks, and pending evidence appends intact.
Trust is first-party only in v1. GAP-0077 and GAP-0081 stay explicit exclusions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal

from qma.core.ports.cardinality import PORT_CONTRACT_BY_NAME, Cardinality
from qmf.core import Ok, Result
from qmf.core.refusal import TypedRefusal
from qmf.data.store.refusals import policy_rejection

__all__ = [
    "CUT_PLUGIN_SURFACES",
    "DAEMON_PLUGIN_RENDERS",
    "EXCLUDED_CONTRIBUTION_POINTS",
    "FIRST_PARTY_TRUST_MODE",
    "GAP_0077_STATUS",
    "GAP_0081_STATUS",
    "PEER_INTEGRATION_BOUNDARY",
    "SHARED_PROCESS_MEMORY_AS_INTEGRATION",
    "ContinuityLedger",
    "DaemonContinuitySnapshot",
    "LoadSurface",
    "PluginStartupAbort",
    "RequiredSingletonBinding",
    "assert_peer_integration_boundary",
    "assess_plugin_trust",
    "excluded_contribution_refusal",
    "refuse_cut_plugin_surface",
    "require_singleton_bindings_met",
    "runtime_load_refusal",
    "startup_abort_from_load_error",
]

LoadSurface = Literal["startup", "runtime_command"]

# Trust is first-party only in v1 — these surfaces stay Cut (DEC-0361, DEC-0362).
FIRST_PARTY_TRUST_MODE: Final[str] = "first_party_only"
CUT_PLUGIN_SURFACES: Final[frozenset[str]] = frozenset(
    {
        "trust_tier",
        "marketplace",
        "plugin_store",
        "install_count",
        "capability_solver",
    }
)

# Logical plugin halves meet only over qma-wire (CT-42; FR-Q70; SCN-0014).
PEER_INTEGRATION_BOUNDARY: Final[str] = "qma_wire_only"
DAEMON_PLUGIN_RENDERS: Final[bool] = False
SHARED_PROCESS_MEMORY_AS_INTEGRATION: Final[bool] = False

# Explicit exclusions — deferred gaps, never closed by this story (FR-Q70).
GAP_0077_STATUS: Final[str] = "deferred"
GAP_0081_STATUS: Final[str] = "deferred"
EXCLUDED_CONTRIBUTION_POINTS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "threading_node": "GAP-0077",
        "threading": "GAP-0077",
        "ui_view": "GAP-0081",
        "ui_package": "GAP-0081",
        "ui_extension": "GAP-0081",
    }
)


class PluginStartupAbort(Exception):
    """Hard startup abort naming the offending load unit (FR-Q70; CT-42).

    Raised only on the startup surface. Runtime install / enable / reload must
    never raise this — they return a typed refusal instead.
    """

    def __init__(
        self,
        message: str,
        *,
        plugin_id: str | None = None,
        field: str | None = None,
        port: str | None = None,
        key: str | None = None,
        conflicting_plugin_ids: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.plugin_id = plugin_id
        self.field = field
        self.port = port
        self.key = key
        self.conflicting_plugin_ids = conflicting_plugin_ids

    def named_fields(self) -> Mapping[str, object]:
        payload: dict[str, object] = {"reason": str(self), "startup": True}
        if self.plugin_id is not None:
            payload["plugin_id"] = self.plugin_id
        if self.field is not None:
            payload["field"] = self.field
        if self.port is not None:
            payload["port"] = self.port
        if self.key is not None:
            payload["key"] = self.key
        if self.conflicting_plugin_ids:
            payload["conflicting_plugin_ids"] = self.conflicting_plugin_ids
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class RequiredSingletonBinding:
    """A singleton key required by a roster entry, manifest, or Role grant."""

    port: str
    key: str
    requiring_unit: str


@dataclass(frozen=True, slots=True)
class DaemonContinuitySnapshot:
    """Markers that a load refusal must leave untouched (FR-Q70; L39).

    The loader never mutates these collections. A runtime load failure proves
    continuity by comparing a before/after snapshot.
    """

    daemon_running: bool = True
    dispatch_leases: tuple[str, ...] = ()
    environment_leases: tuple[str, ...] = ()
    running_tasks: tuple[str, ...] = ()
    pending_evidence_appends: tuple[str, ...] = ()

    def intact_after(self, other: DaemonContinuitySnapshot) -> bool:
        return (
            self.daemon_running is other.daemon_running is True
            and self.dispatch_leases == other.dispatch_leases
            and self.environment_leases == other.environment_leases
            and self.running_tasks == other.running_tasks
            and self.pending_evidence_appends == other.pending_evidence_appends
        )


@dataclass
class ContinuityLedger:
    """In-memory continuity markers owned outside the plugin load path."""

    daemon_running: bool = True
    dispatch_leases: list[str] = field(default_factory=list[str])
    environment_leases: list[str] = field(default_factory=list[str])
    running_tasks: list[str] = field(default_factory=list[str])
    pending_evidence_appends: list[str] = field(default_factory=list[str])

    def snapshot(self) -> DaemonContinuitySnapshot:
        return DaemonContinuitySnapshot(
            daemon_running=self.daemon_running,
            dispatch_leases=tuple(self.dispatch_leases),
            environment_leases=tuple(self.environment_leases),
            running_tasks=tuple(self.running_tasks),
            pending_evidence_appends=tuple(self.pending_evidence_appends),
        )


def assess_plugin_trust(
    *,
    trust_mode: object = FIRST_PARTY_TRUST_MODE,
    declared_surfaces: Mapping[str, object] | Sequence[str] | None = None,
) -> Result[str]:
    """Accept only first-party plugins; refuse Cut trust/marketplace surfaces."""
    if trust_mode != FIRST_PARTY_TRUST_MODE:
        return policy_rejection(
            "trust_mode",
            "v1 accepts first-party plugins only; trust tiers are Cut (DEC-0361; FR-Q70)",
            trust_mode=trust_mode,
            required=FIRST_PARTY_TRUST_MODE,
        )
    if declared_surfaces is None:
        return Ok(FIRST_PARTY_TRUST_MODE)

    if isinstance(declared_surfaces, Mapping):
        hits = [name for name in CUT_PLUGIN_SURFACES if name in declared_surfaces]
    else:
        hits = [name for name in declared_surfaces if name in CUT_PLUGIN_SURFACES]
    if hits:
        return refuse_cut_plugin_surface(hits[0])
    return Ok(FIRST_PARTY_TRUST_MODE)


def refuse_cut_plugin_surface(surface: str) -> Result[str]:
    """Typed refusal for a Cut marketplace / trust / solver surface."""
    return policy_rejection(
        surface,
        f"{surface!r} is Cut in v1 — first-party plugins only "
        "(DEC-0361, DEC-0362; FR-Q70; CT-42)",
        cut_surfaces=sorted(CUT_PLUGIN_SURFACES),
    )


def assert_peer_integration_boundary(
    *,
    peer_channel: object = PEER_INTEGRATION_BOUNDARY,
    daemon_renders: object = False,
    shared_process_memory: object = False,
) -> Result[str]:
    """Require wire-only peer integration; daemon plugins never render."""
    if peer_channel != PEER_INTEGRATION_BOUNDARY:
        return policy_rejection(
            "peer_integration",
            "plugin halves communicate only over qma-wire, never shared process "
            "memory (FR-Q70; CT-42; SCN-0014)",
            peer_channel=peer_channel,
            required=PEER_INTEGRATION_BOUNDARY,
        )
    if daemon_renders is not False or DAEMON_PLUGIN_RENDERS is not False:
        return policy_rejection(
            "daemon_plugin_render",
            "a daemon plugin does not render (FR-Q70; CT-42)",
            daemon_renders=daemon_renders,
        )
    if shared_process_memory is not False or SHARED_PROCESS_MEMORY_AS_INTEGRATION:
        return policy_rejection(
            "shared_process_memory",
            "shared process memory is not an integration boundary (FR-Q70; CT-42)",
            shared_process_memory=shared_process_memory,
        )
    return Ok(PEER_INTEGRATION_BOUNDARY)


def excluded_contribution_refusal(point: str) -> Result[str]:
    """Refuse a contribution point held out by GAP-0077 or GAP-0081."""
    gap = EXCLUDED_CONTRIBUTION_POINTS.get(point)
    if gap is None:
        return Ok(point)
    status = GAP_0077_STATUS if gap == "GAP-0077" else GAP_0081_STATUS
    return policy_rejection(
        "contributions",
        f"contribution point {point!r} is an explicit exclusion ({gap}; status={status}); "
        "not minted in v1 (FR-Q70; CT-42)",
        contribution_point=point,
        gap=gap,
        gap_status=status,
    )


def require_singleton_bindings_met(
    *,
    required: Sequence[RequiredSingletonBinding],
    bound: Mapping[tuple[str, str], object],
) -> None:
    """Raise PluginStartupAbort when a required singleton key stays unbound."""
    for req in required:
        contract = PORT_CONTRACT_BY_NAME.get(req.port)
        if contract is None or contract.cardinality is not Cardinality.SINGLETON:
            raise PluginStartupAbort(
                f"required singleton port {req.port!r} is unresolvable "
                f"(requiring_unit={req.requiring_unit!r})",
                plugin_id=req.requiring_unit,
                field="required_singleton",
                port=req.port,
                key=req.key,
            )
        if (req.port, req.key) not in bound:
            raise PluginStartupAbort(
                f"required singleton {req.port} key {req.key!r} is unbound "
                f"(requiring_unit={req.requiring_unit!r})",
                plugin_id=req.requiring_unit,
                field="required_singleton",
                port=req.port,
                key=req.key,
            )


def runtime_load_refusal(
    *,
    field_name: str,
    reason: str,
    plugin_id: str | None = None,
    port: str | None = None,
    key: str | None = None,
    conflicting_plugin_ids: tuple[str, ...] = (),
    continuity: DaemonContinuitySnapshot | None = None,
) -> TypedRefusal:
    """Typed refusal for an explicit install / enable / reload load failure."""
    extra: dict[str, object] = {"startup": False, "load_surface": "runtime_command"}
    if plugin_id is not None:
        extra["plugin_id"] = plugin_id
    if port is not None:
        extra["port"] = port
    if key is not None:
        extra["key"] = key
    if conflicting_plugin_ids:
        extra["conflicting_plugin_ids"] = conflicting_plugin_ids
    if continuity is not None:
        extra["continuity_intact"] = True
        extra["dispatch_leases"] = continuity.dispatch_leases
        extra["environment_leases"] = continuity.environment_leases
        extra["running_tasks"] = continuity.running_tasks
        extra["pending_evidence_appends"] = continuity.pending_evidence_appends
        extra["daemon_running"] = continuity.daemon_running
    return policy_rejection(field_name, reason, **extra)


def startup_abort_from_load_error(
    message: str,
    *,
    plugin_id: str | None = None,
    field: str | None = None,
    port: str | None = None,
    key: str | None = None,
    conflicting_plugin_ids: tuple[str, ...] = (),
) -> PluginStartupAbort:
    """Build a hard startup abort from a load-error naming payload."""
    return PluginStartupAbort(
        message,
        plugin_id=plugin_id,
        field=field,
        port=port,
        key=key,
        conflicting_plugin_ids=conflicting_plugin_ids,
    )
