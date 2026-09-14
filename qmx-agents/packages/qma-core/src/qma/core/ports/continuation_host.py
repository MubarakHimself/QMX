"""Laptop-off continuation as a daemon property (DEC-0278; FR-W35).

Work that must survive workstation sleep is owned by ``qma-daemon`` plus at
least one registered remote ExecutionEnvironment plus the durable ordered /
fsynced outbox. A configuration whose daemon and every reachable env live only
on the sleeping laptop is a typed refusal, not a silent promise. The concrete
always-on host remains GAP-0062 — operator config; this module does not name a
machine. A governed QMB orchestrator spawn (not CT-47) keeps process-per-run
lifetime and is never classified as laptop-off continuation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Literal

from qma.core.refusals.variants import LaptopOffContinuationRefused
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "CONTINUATION_LAPTOP_OFF_PROMISED_KEY",
    "GAP_0062_ALWAYS_ON_HOST",
    "GAP_0062_HOST_MACHINE",
    "LAPTOP_OFF_OWNERS",
    "REMOTE_CONTINUATION_KINDS",
    "WORKSTATION_COLOCATED_KINDS",
    "ContinuationDoor",
    "ContinuationEnvView",
    "DurableOutboxPosture",
    "JobLifetime",
    "LaptopOffAdmission",
    "classify_job_lifetime",
    "evaluate_laptop_off_configuration",
    "is_laptop_off_continuation",
    "is_remote_continuation_kind",
    "is_workstation_colocated_kind",
    "parse_continuation_door",
    "parse_laptop_off_promised",
    "refuse_laptop_off_continuation",
]


CONTINUATION_LAPTOP_OFF_PROMISED_KEY: Final[str] = "registry:continuation.laptop_off_promised"
GAP_0062_HOST_MACHINE: Final[str] = "operator_config"
GAP_0062_ALWAYS_ON_HOST: Final[Mapping[str, str]] = MappingProxyType(
    {
        "gap": "GAP-0062",
        "status": "deferred",
        "host_machine": GAP_0062_HOST_MACHINE,
        "effect": (
            "laptop-off continuation is a daemon property: qma-daemon plus a "
            "reachable remote ExecutionEnvironment plus the durable ordered/"
            "fsynced outbox; the concrete always-on host remains operator config"
        ),
    }
)
LAPTOP_OFF_OWNERS: Final[tuple[str, str, str]] = (
    "qma-daemon",
    "remote_execution_environment",
    "durable_outbox",
)
WORKSTATION_COLOCATED_KINDS: Final[frozenset[ExecutionEnvironmentKind]] = frozenset(
    {
        ExecutionEnvironmentKind.LOCAL,
        ExecutionEnvironmentKind.DOCKER,
        ExecutionEnvironmentKind.BROWSER,
    }
)
REMOTE_CONTINUATION_KINDS: Final[frozenset[ExecutionEnvironmentKind]] = frozenset(
    {
        ExecutionEnvironmentKind.REMOTE_CONTAINER,
        ExecutionEnvironmentKind.REMOTE_HOST,
        ExecutionEnvironmentKind.DESKTOP,
    }
)


class ContinuationDoor(StrEnum):
    """Door that produced the job. Not a CT-32 field and not a B-4 role."""

    UNGOVERNED = "ungoverned"
    GOVERNED_ORCHESTRATOR = "governed_orchestrator"
    CT47_COORDINATED = "ct47_coordinated"


class JobLifetime(StrEnum):
    """Where a job's lifetime lives. Laptop-off is daemon continuation only."""

    DAEMON_CONTINUATION = "daemon_continuation"
    QMB_PROCESS_PER_RUN = "qmb_process_per_run"
    UNGOVERNED_CALLER_PROCESS = "ungoverned_caller_process"


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _kind(kind: ExecutionEnvironmentKind | str) -> ExecutionEnvironmentKind:
    if isinstance(kind, ExecutionEnvironmentKind):
        return kind
    return ExecutionEnvironmentKind(kind)


def is_workstation_colocated_kind(kind: ExecutionEnvironmentKind | str) -> bool:
    """True when the kind runs on the same workstation as the default daemon."""
    return _kind(kind) in WORKSTATION_COLOCATED_KINDS


def is_remote_continuation_kind(kind: ExecutionEnvironmentKind | str) -> bool:
    """True when the kind can sit off the sleeping laptop."""
    return _kind(kind) in REMOTE_CONTINUATION_KINDS


def parse_continuation_door(value: ContinuationDoor | str) -> Result[ContinuationDoor]:
    """Parse a continuation door token."""
    try:
        return Ok(parse_closed(ContinuationDoor, value))
    except VocabularyError as exc:
        return _invalid("door", str(exc), given=repr(value))


def classify_job_lifetime(door: ContinuationDoor | str) -> Result[JobLifetime]:
    """Map a door onto job lifetime. Governed-not-CT-47 stays process-per-run."""
    parsed = parse_continuation_door(door)
    if not isinstance(parsed, Ok):
        return parsed
    match parsed.value:
        case ContinuationDoor.CT47_COORDINATED:
            return Ok(JobLifetime.DAEMON_CONTINUATION)
        case ContinuationDoor.GOVERNED_ORCHESTRATOR:
            return Ok(JobLifetime.QMB_PROCESS_PER_RUN)
        case ContinuationDoor.UNGOVERNED:
            return Ok(JobLifetime.UNGOVERNED_CALLER_PROCESS)


def is_laptop_off_continuation(lifetime: JobLifetime | str) -> bool:
    """True only for daemon-owned continuation, never QMB process-per-run."""
    if isinstance(lifetime, JobLifetime):
        return lifetime is JobLifetime.DAEMON_CONTINUATION
    return lifetime == JobLifetime.DAEMON_CONTINUATION.value


def parse_laptop_off_promised(value: object) -> Result[bool]:
    """Accept only a boolean promise. Absence of a promise is not continuation."""
    if isinstance(value, bool):
        return Ok(value)
    return _invalid(
        CONTINUATION_LAPTOP_OFF_PROMISED_KEY,
        "continuation.laptop_off_promised is a boolean registry-homed promise (DEC-0278; FR-W35)",
        given=repr(value),
    )


def refuse_laptop_off_continuation(
    *,
    reason: str,
    detail: str | None = None,
    **extra: object,
) -> LaptopOffContinuationRefused:
    """Typed refusal for a laptop-only or incomplete laptop-off configuration."""
    return LaptopOffContinuationRefused.of(reason=reason, detail=detail, **extra)


@dataclass(frozen=True, slots=True)
class ContinuationEnvView:
    """Registered env as seen by the laptop-off gate.

    ``env_id`` is a fixture or kind token, never the GAP-0062 host machine.
    ``reachable`` is a declared/fixture mark — Tier 1 does not probe a live host.
    """

    env_id: str
    kind: ExecutionEnvironmentKind
    colocated_with_daemon: bool
    reachable: bool

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "env_id": self.env_id,
                "kind": self.kind.value,
                "colocated_with_daemon": self.colocated_with_daemon,
                "reachable": self.reachable,
            }
        )


@dataclass(frozen=True, slots=True)
class DurableOutboxPosture:
    """Story 41.4 outbox: ordered, fsynced, never a journal."""

    present: bool
    ordered: bool
    fsynced: bool
    never_a_journal: Literal[True] = True

    @property
    def durable(self) -> bool:
        return self.present and self.ordered and self.fsynced

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "present": self.present,
                "ordered": self.ordered,
                "fsynced": self.fsynced,
                "never_a_journal": self.never_a_journal,
                "durable": self.durable,
            }
        )


@dataclass(frozen=True, slots=True)
class LaptopOffAdmission:
    """Resolved laptop-off posture. ``host_machine`` stays GAP-0062 operator config."""

    promised: bool
    laptop_off: bool
    lifetime: JobLifetime
    daemon: bool
    remote_env: bool
    outbox: bool
    reason: str
    host_machine: str = GAP_0062_HOST_MACHINE
    gap: str = "GAP-0062"
    owners: tuple[str, ...] = LAPTOP_OFF_OWNERS

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "promised": self.promised,
                "laptop_off": self.laptop_off,
                "lifetime": self.lifetime.value,
                "daemon": self.daemon,
                "remote_env": self.remote_env,
                "outbox": self.outbox,
                "reason": self.reason,
                "host_machine": self.host_machine,
                "gap": self.gap,
                "owners": list(self.owners),
            }
        )


def _admission(
    *,
    promised: bool,
    laptop_off: bool,
    lifetime: JobLifetime,
    daemon: bool,
    remote_env: bool,
    outbox: bool,
    reason: str,
) -> LaptopOffAdmission:
    return LaptopOffAdmission(
        promised=promised,
        laptop_off=laptop_off,
        lifetime=lifetime,
        daemon=daemon,
        remote_env=remote_env,
        outbox=outbox,
        reason=reason,
        host_machine=GAP_0062_HOST_MACHINE,
        gap=GAP_0062_ALWAYS_ON_HOST["gap"],
        owners=LAPTOP_OFF_OWNERS,
    )


def evaluate_laptop_off_configuration(
    *,
    promised: bool,
    daemon_present: bool,
    daemon_on_workstation: bool,
    envs: Sequence[ContinuationEnvView],
    outbox: DurableOutboxPosture,
    lifetime: JobLifetime = JobLifetime.DAEMON_CONTINUATION,
) -> Result[LaptopOffAdmission]:
    """Admit laptop-off only when daemon + reachable remote env + durable outbox.

    A governed QMB orchestrator spawn is never admitted as laptop-off
    continuation. GAP-0062's machine is not named.
    """
    if not is_laptop_off_continuation(lifetime):
        return Ok(
            _admission(
                promised=promised,
                laptop_off=False,
                lifetime=lifetime,
                daemon=daemon_present,
                remote_env=False,
                outbox=outbox.durable,
                reason=lifetime.value,
            )
        )
    remote_registered = tuple(env for env in envs if is_remote_continuation_kind(env.kind))
    reachable_remote = tuple(env for env in remote_registered if env.reachable)
    reachable = tuple(env for env in envs if env.reachable)
    reachable_only_colocated = bool(reachable) and all(
        env.colocated_with_daemon for env in reachable
    )
    if not promised:
        return Ok(
            _admission(
                promised=False,
                laptop_off=False,
                lifetime=lifetime,
                daemon=daemon_present,
                remote_env=bool(reachable_remote),
                outbox=outbox.durable,
                reason="not_promised",
            )
        )
    if not daemon_present:
        return refuse_laptop_off_continuation(
            reason="daemon_missing",
            detail="laptop_off requires qma-daemon",
            gap="GAP-0062",
            host_machine=GAP_0062_HOST_MACHINE,
            owners=list(LAPTOP_OFF_OWNERS),
        )
    if not remote_registered:
        return refuse_laptop_off_continuation(
            reason="laptop_only",
            detail="no_remote_env",
            gap="GAP-0062",
            host_machine=GAP_0062_HOST_MACHINE,
            owners=list(LAPTOP_OFF_OWNERS),
            daemon_on_workstation=daemon_on_workstation,
        )
    if not reachable_remote:
        return refuse_laptop_off_continuation(
            reason="laptop_only",
            detail="remote_unreachable",
            gap="GAP-0062",
            host_machine=GAP_0062_HOST_MACHINE,
            owners=list(LAPTOP_OFF_OWNERS),
            daemon_on_workstation=daemon_on_workstation,
            unreachable_env_ids=[env.env_id for env in remote_registered],
        )
    if daemon_on_workstation and reachable_only_colocated:
        return refuse_laptop_off_continuation(
            reason="laptop_only",
            detail="reachable_envs_colocated",
            gap="GAP-0062",
            host_machine=GAP_0062_HOST_MACHINE,
            owners=list(LAPTOP_OFF_OWNERS),
            daemon_on_workstation=True,
        )
    if not outbox.durable:
        return refuse_laptop_off_continuation(
            reason="outbox_missing",
            detail="laptop_off requires the durable ordered/fsynced outbox",
            gap="GAP-0062",
            host_machine=GAP_0062_HOST_MACHINE,
            owners=list(LAPTOP_OFF_OWNERS),
            outbox_present=outbox.present,
            outbox_ordered=outbox.ordered,
            outbox_fsynced=outbox.fsynced,
        )
    return Ok(
        _admission(
            promised=True,
            laptop_off=True,
            lifetime=JobLifetime.DAEMON_CONTINUATION,
            daemon=True,
            remote_env=True,
            outbox=True,
            reason="admitted",
        )
    )
