"""Independent provenance-stamped health states — never one colour (TN-15).

``/health`` aggregates every component ``health()`` into seven independent
states. A consumer that wants an overall colour computes it itself; the node
never collapses them. Requested protection stays apart from enforced.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Protocol

__all__ = [
    "AUTHORITY_LIVE",
    "AUTHORITY_REPLICATED",
    "AUTHORITY_SOURCES",
    "COLLAPSES_TO_GLOBAL_COLOUR",
    "HEALTH_STATE_NAMES",
    "HealthProvenance",
    "HealthStateName",
    "HealthStatus",
    "IndependentHealthReport",
    "IndependentHealthState",
    "NodeHealthView",
    "aggregate_health",
    "default_health_report",
    "health",
]

# Mirrors door wire vocabulary without importing doors (layering).
AUTHORITY_LIVE: Final[str] = "live-authoritative"
AUTHORITY_REPLICATED: Final[str] = "replicated-evidence"
AUTHORITY_SOURCES: Final[frozenset[str]] = frozenset({AUTHORITY_LIVE, AUTHORITY_REPLICATED})

COLLAPSES_TO_GLOBAL_COLOUR: Final[bool] = False

HEALTH_STATE_NAMES: Final[tuple[str, ...]] = (
    "safety",
    "execution_readiness",
    "connection",
    "reconciliation",
    "data_freshness",
    "lifecycle",
    "sync",
)


class HealthStateName(StrEnum):
    """The seven independent /health states (DEC-0200 / DEC-0238)."""

    SAFETY = "safety"
    EXECUTION_READINESS = "execution_readiness"
    CONNECTION = "connection"
    RECONCILIATION = "reconciliation"
    DATA_FRESHNESS = "data_freshness"
    LIFECYCLE = "lifecycle"
    SYNC = "sync"


class HealthStatus(StrEnum):
    """Per-state status vocabulary — never folded into a global colour."""

    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"
    RUNNING = "running"
    STAND_DOWN = "stand-down"


@dataclass(frozen=True, slots=True)
class HealthProvenance:
    """Per-read provenance stamped on every independent health state."""

    authority_source: str
    source_time_ns: int
    receive_time_ns: int
    watermark_ns: int

    def __post_init__(self) -> None:
        if self.authority_source not in AUTHORITY_SOURCES:
            msg = f"authority_source must be one of {sorted(AUTHORITY_SOURCES)}"
            raise ValueError(msg)

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "authority_source": self.authority_source,
                "source_time_ns": self.source_time_ns,
                "receive_time_ns": self.receive_time_ns,
                "watermark_ns": self.watermark_ns,
            }
        )


@dataclass(frozen=True, slots=True)
class IndependentHealthState:
    """One independent health state with its own provenance."""

    name: str
    state: str
    provenance: HealthProvenance
    detail: Mapping[str, object] = field(default_factory=dict[str, object])

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "state": self.state,
            **dict(self.provenance.as_mapping()),
        }
        if self.detail:
            body["detail"] = dict(self.detail)
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class IndependentHealthReport:
    """Seven independent states — ``collapsed_global_colour`` is always False."""

    states: Mapping[str, IndependentHealthState]
    requested_protection: Mapping[str, object] = field(default_factory=dict[str, object])
    enforced_protection: Mapping[str, object] = field(default_factory=dict[str, object])

    def __post_init__(self) -> None:
        missing = [name for name in HEALTH_STATE_NAMES if name not in self.states]
        if missing:
            msg = f"health report missing independent states: {missing}"
            raise ValueError(msg)
        object.__setattr__(self, "states", MappingProxyType(dict(self.states)))
        object.__setattr__(
            self, "requested_protection", MappingProxyType(dict(self.requested_protection))
        )
        object.__setattr__(
            self, "enforced_protection", MappingProxyType(dict(self.enforced_protection))
        )

    @property
    def collapsed_global_colour(self) -> bool:
        return False

    def health(self) -> IndependentHealthReport:
        """No-argument health() — returns this report (AD-14)."""
        return self

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "states": {name: state.as_mapping() for name, state in self.states.items()},
                "collapsed_global_colour": False,
                "requested_protection": dict(self.requested_protection),
                "enforced_protection": dict(self.enforced_protection),
            }
        )


class NodeHealthView(Protocol):
    """Minimal injectable view a component may contribute into aggregation."""

    def health(self) -> Mapping[str, object]: ...


def default_health_report(
    *,
    authority_source: str = AUTHORITY_LIVE,
    source_time_ns: int = 0,
    receive_time_ns: int = 0,
    watermark_ns: int = 0,
    lifecycle: str = "running",
    overrides: Mapping[str, str] | None = None,
) -> IndependentHealthReport:
    """Build the seven independent states with shared provenance defaults."""
    provenance = HealthProvenance(
        authority_source=authority_source,
        source_time_ns=source_time_ns,
        receive_time_ns=receive_time_ns,
        watermark_ns=watermark_ns,
    )
    status_by_name: dict[str, str] = {
        "safety": HealthStatus.OK.value,
        "execution_readiness": HealthStatus.OK.value,
        "connection": HealthStatus.OK.value,
        "reconciliation": HealthStatus.OK.value,
        "data_freshness": HealthStatus.OK.value,
        "lifecycle": lifecycle,
        "sync": HealthStatus.OK.value,
    }
    if overrides:
        for key, value in overrides.items():
            if key in status_by_name:
                status_by_name[key] = value
    states = {
        name: IndependentHealthState(name=name, state=status, provenance=provenance)
        for name, status in status_by_name.items()
    }
    return IndependentHealthReport(states=states)


def aggregate_health(
    *,
    authority_source: str,
    source_time_ns: int,
    receive_time_ns: int,
    watermark_ns: int,
    component_states: Mapping[str, str] | None = None,
    requested_protection: Mapping[str, object] | None = None,
    enforced_protection: Mapping[str, object] | None = None,
) -> IndependentHealthReport:
    """Aggregate independent states — never derive one from another."""
    report = default_health_report(
        authority_source=authority_source,
        source_time_ns=source_time_ns,
        receive_time_ns=receive_time_ns,
        watermark_ns=watermark_ns,
        overrides=component_states,
    )
    if requested_protection is None and enforced_protection is None:
        return report
    return IndependentHealthReport(
        states=report.states,
        requested_protection=dict(requested_protection or {}),
        enforced_protection=dict(enforced_protection or {}),
    )


def health(
    report: IndependentHealthReport | None = None,
    **provenance_kwargs: object,
) -> IndependentHealthReport:
    """Module-level no-argument-style health entry (AD-14 / DEC-0112).

    When ``report`` is supplied it is returned unchanged. Otherwise a default
    independent report is built from optional provenance kwargs.
    """
    if report is not None:
        return report.health()
    allowed = {
        "authority_source",
        "source_time_ns",
        "receive_time_ns",
        "watermark_ns",
        "lifecycle",
    }
    kwargs: MutableMapping[str, object] = {
        key: value for key, value in provenance_kwargs.items() if key in allowed
    }
    return default_health_report(
        authority_source=str(kwargs.get("authority_source", AUTHORITY_LIVE)),
        source_time_ns=int(kwargs.get("source_time_ns", 0)),  # type: ignore[arg-type]
        receive_time_ns=int(kwargs.get("receive_time_ns", 0)),  # type: ignore[arg-type]
        watermark_ns=int(kwargs.get("watermark_ns", 0)),  # type: ignore[arg-type]
        lifecycle=str(kwargs.get("lifecycle", "running")),
    )
