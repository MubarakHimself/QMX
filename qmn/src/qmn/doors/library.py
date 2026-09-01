"""One pure function per node door capability (TN-17 / DEC-0202).

Doors carry only adaptation. Shared evidence reads and powers acts call these
functions and return equivalent typed values or refusals. No product UI and no
operator CLI live here.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, MutableSequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, cast

from qmf.core.refusal import Ok, Result, is_refusal

from qmn.config.toolkit import config_explain, config_validate
from qmn.doors._refuse import clean_token, invalid, policy, stale
from qmn.doors.catalog import CLOSED_POWERS, OPS_ALLOWED_POWERS
from qmn.doors.wire import (
    AUTHORITY_LIVE,
    AUTHORITY_SOURCES,
    WIRE_FORMAT_VERSION,
    refusal_wire_shape,
)

_OPS_PRINCIPAL: Final[str] = "ops"

__all__ = [
    "EVIDENCE_CAPABILITIES",
    "EVIDENCE_CHANNEL_BUDGET_UNIT",
    "LIBRARY_SURFACE",
    "POWERS_CAPABILITIES",
    "DoorRuntime",
    "PowersEnactment",
    "enact_power",
    "library_capability_names",
    "read_config_explanation",
    "read_failure_detail",
    "read_health",
    "read_metrics",
    "read_projections",
    "read_status",
    "stamp_evidence",
]

LIBRARY_SURFACE: Final[str] = "qmn.doors.library"

# AR-81: unit-kind chosen at implementation — request count per boot epoch.
EVIDENCE_CHANNEL_BUDGET_UNIT: Final[str] = "request-count-per-boot-epoch"

EVIDENCE_CAPABILITIES: Final[tuple[str, ...]] = (
    "read_status",
    "read_health",
    "read_projections",
    "read_config_explanation",
    "read_failure_detail",
    "read_metrics",
)

POWERS_CAPABILITIES: Final[tuple[str, ...]] = ("enact_power",)


@dataclass(frozen=True, slots=True)
class PowersEnactment:
    """Outcome of one powers act — requested and enforced stay distinct."""

    power: str
    artifact_key: str
    principal: str
    requested: Mapping[str, object]
    enforced: Mapping[str, object]
    was_idempotent: bool
    boot_epoch: str
    composition_fp: str

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "power": self.power,
                "artifact_key": self.artifact_key,
                "principal": self.principal,
                "requested": dict(self.requested),
                "enforced": dict(self.enforced),
                "was_idempotent": self.was_idempotent,
                "boot_epoch": self.boot_epoch,
                "composition_fp": self.composition_fp,
                "wire_format_version": WIRE_FORMAT_VERSION,
            }
        )


@dataclass
class DoorRuntime:
    """Injectable node view for door library calls (no ambient I/O)."""

    boot_epoch: str
    composition_fp: str
    knowledge_time_ns: int
    watermark_ns: int
    source_time_ns: int
    receive_time_ns: int
    evidence_channel_budget: int
    authority_source: str = AUTHORITY_LIVE
    evidence_reads: int = 0
    lifecycle: str = "running"
    config: object | None = None
    health_states: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType(
            {
                "safety": "ok",
                "execution_readiness": "ok",
                "connection": "ok",
                "reconciliation": "ok",
                "data_freshness": "ok",
                "lifecycle": "running",
                "sync": "ok",
            }
        )
    )
    projections: Mapping[str, object] = field(default_factory=dict[str, object])
    metrics: Mapping[str, object] = field(default_factory=dict[str, object])
    failures: Mapping[str, Mapping[str, object]] = field(
        default_factory=dict[str, Mapping[str, object]]
    )
    enacted: MutableMapping[str, PowersEnactment] = field(
        default_factory=dict[str, PowersEnactment]
    )
    journals: MutableSequence[Mapping[str, object]] = field(
        default_factory=list[Mapping[str, object]]
    )
    hub_published: MutableSequence[str] = field(default_factory=list[str])
    notify_tests: int = 0
    restore_drills: int = 0

    def __post_init__(self) -> None:
        if self.authority_source not in AUTHORITY_SOURCES:
            msg = f"authority_source must be one of {sorted(AUTHORITY_SOURCES)}"
            raise ValueError(msg)
        object.__setattr__(
            self,
            "health_states",
            MappingProxyType(dict(self.health_states)),
        )
        object.__setattr__(self, "projections", MappingProxyType(dict(self.projections)))
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))
        frozen_failures = {
            key: MappingProxyType(dict(value)) for key, value in self.failures.items()
        }
        object.__setattr__(self, "failures", MappingProxyType(frozen_failures))


def library_capability_names() -> frozenset[str]:
    """Public library capability names every shared door adapts."""
    return frozenset(EVIDENCE_CAPABILITIES) | frozenset(POWERS_CAPABILITIES)


def stamp_evidence(
    runtime: DoorRuntime,
    body: Mapping[str, object],
) -> Mapping[str, object]:
    """Attach required epoch + provenance fields to an evidence payload."""
    payload = dict(body)
    payload.update(
        {
            "wire_format_version": WIRE_FORMAT_VERSION,
            "boot_epoch": runtime.boot_epoch,
            "composition_fp": runtime.composition_fp,
            "knowledge_time_ns": runtime.knowledge_time_ns,
            "authority_source": runtime.authority_source,
            "source_time_ns": runtime.source_time_ns,
            "receive_time_ns": runtime.receive_time_ns,
            "watermark_ns": runtime.watermark_ns,
            "publishes": True,
            "acts": False,
        }
    )
    return MappingProxyType(payload)


def _consume_budget(runtime: DoorRuntime) -> Result[None]:
    if runtime.evidence_channel_budget < 0:
        return invalid(
            "evidence_channel_budget",
            "evidence_channel_budget is a non-negative request count per boot epoch",
            unit=EVIDENCE_CHANNEL_BUDGET_UNIT,
        )
    if runtime.evidence_reads >= runtime.evidence_channel_budget:
        return policy(
            "evidence_channel_budget",
            "evidence channel budget exhausted for this boot epoch",
            budget=runtime.evidence_channel_budget,
            reads=runtime.evidence_reads,
            unit=EVIDENCE_CHANNEL_BUDGET_UNIT,
        )
    runtime.evidence_reads += 1
    return Ok(None)


def read_status(runtime: object) -> Result[Mapping[str, object]]:
    """Publish node status — never acts."""
    view = _as_runtime(runtime)
    if is_refusal(view):
        return view
    budget = _consume_budget(view.value)
    if is_refusal(budget):
        return budget
    return Ok(
        stamp_evidence(
            view.value,
            {
                "capability": "read_status",
                "lifecycle": view.value.lifecycle,
                "doors": ("python_api", "evidence_http", "powers_unix"),
            },
        )
    )


def read_health(runtime: object) -> Result[Mapping[str, object]]:
    """Independent health states with per-state provenance — never one colour."""
    view = _as_runtime(runtime)
    if is_refusal(view):
        return view
    budget = _consume_budget(view.value)
    if is_refusal(budget):
        return budget
    states = {
        name: {
            "state": state,
            "authority_source": view.value.authority_source,
            "source_time_ns": view.value.source_time_ns,
            "receive_time_ns": view.value.receive_time_ns,
            "watermark_ns": view.value.watermark_ns,
        }
        for name, state in view.value.health_states.items()
    }
    return Ok(
        stamp_evidence(
            view.value,
            {
                "capability": "read_health",
                "states": states,
                "collapsed_global_colour": False,
            },
        )
    )


def read_projections(runtime: object) -> Result[Mapping[str, object]]:
    """Journal / entity projections — publish-never-act."""
    view = _as_runtime(runtime)
    if is_refusal(view):
        return view
    budget = _consume_budget(view.value)
    if is_refusal(budget):
        return budget
    return Ok(
        stamp_evidence(
            view.value,
            {
                "capability": "read_projections",
                "projections": dict(view.value.projections),
            },
        )
    )


def read_config_explanation(runtime: object) -> Result[Mapping[str, object]]:
    """Config explain over the sealed artifact — same pure function as toolkit."""
    view = _as_runtime(runtime)
    if is_refusal(view):
        return view
    budget = _consume_budget(view.value)
    if is_refusal(budget):
        return budget
    if view.value.config is None:
        return invalid(
            "config",
            "config explanation requires a resolved node-config on the runtime",
        )
    explained = config_explain(view.value.config)
    if is_refusal(explained):
        return explained
    return Ok(
        stamp_evidence(
            view.value,
            {
                "capability": "read_config_explanation",
                "explanation": dict(explained.value),
            },
        )
    )


def read_failure_detail(runtime: object, failure_id: object) -> Result[Mapping[str, object]]:
    """Typed failure detail for the evidence channel."""
    view = _as_runtime(runtime)
    if is_refusal(view):
        return view
    budget = _consume_budget(view.value)
    if is_refusal(budget):
        return budget
    token = clean_token(failure_id)
    if token is None:
        return invalid("failure_id", "failure detail names a non-blank failure id")
    detail = view.value.failures.get(token)
    if detail is None:
        return stale(
            "failure_id",
            "no failure detail is known for this id at the current knowledge time",
            failure_id=token,
            knowledge_time_ns=view.value.knowledge_time_ns,
        )
    return Ok(
        stamp_evidence(
            view.value,
            {
                "capability": "read_failure_detail",
                "failure_id": token,
                "detail": dict(detail),
            },
        )
    )


def read_metrics(runtime: object) -> Result[Mapping[str, object]]:
    """Metrics exposition payload for the evidence listener."""
    view = _as_runtime(runtime)
    if is_refusal(view):
        return view
    budget = _consume_budget(view.value)
    if is_refusal(budget):
        return budget
    return Ok(
        stamp_evidence(
            view.value,
            {
                "capability": "read_metrics",
                "metrics": dict(view.value.metrics),
                "evidence_reads": view.value.evidence_reads,
                "evidence_channel_budget": view.value.evidence_channel_budget,
                "evidence_channel_budget_unit": EVIDENCE_CHANNEL_BUDGET_UNIT,
            },
        )
    )


def enact_power(
    runtime: object,
    *,
    power: object,
    principal: object,
    artifact_key: object,
    evidence_knowledge_time_ns: object,
    requested: object,
) -> Result[PowersEnactment]:
    """Enact one closed-list power against fresh state.

    Revalidates the caller-supplied evidence stamp against the runtime's current
    ``knowledge_time_ns`` (stale evidence cannot authorize). Idempotent by
    ``artifact_key``: a retry with the same key returns the first enactment and
    never duplicates the act. Requested and enforced outcomes are journaled as
    separate records.
    """
    view = _as_runtime(runtime)
    if is_refusal(view):
        return view
    power_token = clean_token(power)
    if power_token is None:
        return invalid("power", "powers call names a non-blank power")
    if power_token not in CLOSED_POWERS:
        return policy(
            "power",
            "powers list is closed; a capability not on it does not exist",
            given=power_token,
        )
    principal_token = clean_token(principal)
    if principal_token is None:
        return invalid("principal", "powers enactment names a non-blank principal")
    if principal_token == _OPS_PRINCIPAL and power_token not in OPS_ALLOWED_POWERS:
        return policy(
            "power",
            "ops principal is refused this power by the library (transport also refuses)",
            principal=principal_token,
            power=power_token,
        )
    key = clean_token(artifact_key)
    if key is None:
        return invalid("artifact_key", "powers acts are idempotent by a non-blank artifact key")
    if not isinstance(evidence_knowledge_time_ns, int) or isinstance(
        evidence_knowledge_time_ns, bool
    ):
        return invalid(
            "evidence_knowledge_time_ns",
            "powers authorization carries the evidence knowledge-time as int nanoseconds",
            given=repr(evidence_knowledge_time_ns),
        )
    if evidence_knowledge_time_ns < view.value.knowledge_time_ns:
        return stale(
            "evidence_knowledge_time_ns",
            "stale evidence cannot authorize a powers call",
            evidence_knowledge_time_ns=evidence_knowledge_time_ns,
            knowledge_time_ns=view.value.knowledge_time_ns,
        )
    if not isinstance(requested, Mapping):
        return invalid(
            "requested",
            "powers requested outcome is a mapping shown apart from enforced",
            given=type(requested).__name__,
        )
    requested_body = MappingProxyType(dict(cast("Mapping[str, object]", requested)))

    prior = view.value.enacted.get(key)
    if prior is not None:
        if prior.power != power_token:
            return policy(
                "artifact_key",
                "artifact key already enacted a different power; retries cannot retarget",
                artifact_key=key,
                prior_power=prior.power,
                power=power_token,
            )
        view.value.journals.append(
            MappingProxyType(
                {
                    "event_type": "control action",
                    "kind": "powers-enactment",
                    "phase": "idempotent-replay",
                    "power": power_token,
                    "artifact_key": key,
                    "principal": principal_token,
                    "requested": dict(requested_body),
                    "enforced": dict(prior.enforced),
                }
            )
        )
        return Ok(
            PowersEnactment(
                power=prior.power,
                artifact_key=prior.artifact_key,
                principal=prior.principal,
                requested=prior.requested,
                enforced=prior.enforced,
                was_idempotent=True,
                boot_epoch=prior.boot_epoch,
                composition_fp=prior.composition_fp,
            )
        )

    view.value.journals.append(
        MappingProxyType(
            {
                "event_type": "control action",
                "kind": "powers-enactment",
                "phase": "requested",
                "power": power_token,
                "artifact_key": key,
                "principal": principal_token,
                "requested": dict(requested_body),
            }
        )
    )

    enforced = _apply_power(view.value, power=power_token, requested=requested_body)
    if is_refusal(enforced):
        view.value.journals.append(
            MappingProxyType(
                {
                    "event_type": "control action",
                    "kind": "powers-enactment",
                    "phase": "enforced-refusal",
                    "power": power_token,
                    "artifact_key": key,
                    "principal": principal_token,
                    "refusal": dict(refusal_wire_shape(enforced)),
                }
            )
        )
        return enforced

    enactment = PowersEnactment(
        power=power_token,
        artifact_key=key,
        principal=principal_token,
        requested=requested_body,
        enforced=enforced.value,
        was_idempotent=False,
        boot_epoch=view.value.boot_epoch,
        composition_fp=view.value.composition_fp,
    )
    view.value.enacted[key] = enactment
    view.value.journals.append(
        MappingProxyType(
            {
                "event_type": "control action",
                "kind": "powers-enactment",
                "phase": "enforced",
                "power": power_token,
                "artifact_key": key,
                "principal": principal_token,
                "requested": dict(requested_body),
                "enforced": dict(enforced.value),
            }
        )
    )
    return Ok(enactment)


def _apply_power(
    runtime: DoorRuntime,
    *,
    power: str,
    requested: Mapping[str, object],
) -> Result[Mapping[str, object]]:
    """Domain side-effects for closed powers available in this story."""
    if power == "notify_test":
        runtime.notify_tests += 1
        return Ok(
            MappingProxyType(
                {
                    "power": power,
                    "status": "notified",
                    "notify_tests": runtime.notify_tests,
                }
            )
        )
    if power == "config_validate":
        if runtime.config is None:
            return invalid("config", "config_validate requires a resolved node-config")
        validated = config_validate(runtime.config)
        if is_refusal(validated):
            return validated
        return Ok(
            MappingProxyType(
                {
                    "power": power,
                    "status": "validated",
                    "fingerprint": validated.value.fingerprint.value,
                    "config_version": validated.value.config_version,
                }
            )
        )
    if power == "hub_publish":
        fragment = clean_token(requested.get("fragment_fp1"))
        if fragment is None:
            return invalid("fragment_fp1", "hub_publish names the fragment fp1 to publish")
        provenance = requested.get("provenance")
        if provenance == "sandbox":
            return policy(
                "provenance",
                "hub_publish refuses provenance = sandbox at publish",
                provenance=provenance,
            )
        runtime.hub_published.append(fragment)
        return Ok(
            MappingProxyType(
                {
                    "power": power,
                    "status": "published",
                    "fragment_fp1": fragment,
                }
            )
        )
    if power == "restore_drill_run":
        runtime.restore_drills += 1
        return Ok(
            MappingProxyType(
                {
                    "power": power,
                    "status": "drill-started",
                    "restore_drills": runtime.restore_drills,
                }
            )
        )
    # Remaining closed powers are UI-ready: accepted, journaled, no second act.
    return Ok(
        MappingProxyType(
            {
                "power": power,
                "status": "accepted",
                "requested_keys": tuple(sorted(requested)),
            }
        )
    )


def _as_runtime(runtime: object) -> Result[DoorRuntime]:
    if not isinstance(runtime, DoorRuntime):
        return invalid(
            "runtime",
            "door library capabilities require a DoorRuntime",
            given=type(runtime).__name__,
        )
    return Ok(runtime)
