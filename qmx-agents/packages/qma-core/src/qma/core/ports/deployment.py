"""Deployment envelope and computer-use exclusion (CT-46; AD-25; FR-Q56).

The daemon host is the operator workstation with Docker workers on that host.
A Quant, Mission, or Worker deploys through the ExecutionEnvironment contract
to a remote workspace, research node, or sandbox. Remotes dial out; the daemon
never dials in. Dev and paper are read-only except the content-addressed
dev-zone candidate. Paper is an account role on a real venue, never a sandbox.
QMA mints no promotion or zone-transition command.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qma.core.barriers.parent_surfaces import (
    SOLE_PERMITTED_PARENT_WRITE,
    refuse_zone_transition_surface,
)
from qma.core.barriers.reachability import GAP_0070_DESKTOP_EXCLUSION
from qma.core.vocabulary.enums import EnvironmentLifecycle, ExecutionEnvironmentKind
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "DAEMON_DIAL_DIRECTION",
    "DEFAULT_DAEMON_HOST",
    "DEFAULT_WORKER_ISOLATION",
    "DEPLOYABLE_UNITS",
    "DEV_ZONE",
    "GAP_0070_COMPUTER_USE_EXCLUSION",
    "PAPER_ACCOUNT_ROLE",
    "PAPER_IS_SANDBOX",
    "PAPER_ZONE",
    "QMA_MINTED_PROMOTION_COMMAND",
    "QMA_MINTED_ZONE_TRANSITION",
    "REMOTE_DEPLOY_TARGETS",
    "REMOTE_DIAL_DIRECTION",
    "REMOTE_TARGET_KIND",
    "SOLE_ZONE_WRITE",
    "AccountZone",
    "DeployableUnit",
    "DeploymentEnvelope",
    "DialOutDeclaration",
    "HumanPromotionArtifactRef",
    "RemoteDeployTarget",
    "RemoteDeploymentRequest",
    "ZoneMutation",
    "admit_paper_role",
    "admit_zone_access",
    "default_deployment_envelope",
    "is_paper_sandbox_token",
    "kind_and_lifecycle_for",
    "parse_dial_out_declaration",
    "parse_remote_deployment_request",
    "record_human_promotion_ref",
    "refuse_computer_use_provision",
    "refuse_daemon_dial_in",
    "refuse_deployed_inbound_port",
    "refuse_paper_as_sandbox",
    "refuse_promotion_command",
    "validate_dial_out_declaration",
]


class DeployableUnit(StrEnum):
    """Units deployable through the ExecutionEnvironment contract (AD-25)."""

    QUANT = "quant"
    MISSION = "mission"
    WORKER = "worker"


class RemoteDeployTarget(StrEnum):
    """Remote placement targets; vendor identity is never an agent choice."""

    REMOTE_WORKSPACE = "remote_workspace"
    RESEARCH_NODE = "research_node"
    SANDBOX = "sandbox"


class AccountZone(StrEnum):
    """Registry zones QMA may name. Live stays unreachable (L17; AD-25)."""

    DEV = "dev"
    PAPER = "paper"
    LIVE = "live"


class ZoneMutation(StrEnum):
    """Closed access verbs against a named zone (FR-Q56)."""

    READ = "read"
    WRITE = "write"
    CANDIDATE_WRITE = "candidate_write"
    PROMOTE = "promote"
    ZONE_TRANSITION = "zone_transition"


DEPLOYABLE_UNITS: Final[frozenset[DeployableUnit]] = frozenset(DeployableUnit)
REMOTE_DEPLOY_TARGETS: Final[frozenset[RemoteDeployTarget]] = frozenset(RemoteDeployTarget)

DEFAULT_DAEMON_HOST: Final[str] = "operator_workstation"
DEFAULT_WORKER_ISOLATION: Final[str] = "docker_on_host"
REMOTE_DIAL_DIRECTION: Final[str] = "out"
DAEMON_DIAL_DIRECTION: Final[str] = "never_in"

DEV_ZONE: Final[str] = AccountZone.DEV.value
PAPER_ZONE: Final[str] = AccountZone.PAPER.value
PAPER_ACCOUNT_ROLE: Final[str] = "paper"
PAPER_IS_SANDBOX: Final[bool] = False
SOLE_ZONE_WRITE: Final[str] = "dev_zone_candidate"
QMA_MINTED_PROMOTION_COMMAND: Final[None] = None
QMA_MINTED_ZONE_TRANSITION: Final[None] = None

GAP_0070_COMPUTER_USE_EXCLUSION: Final[Mapping[str, str]] = GAP_0070_DESKTOP_EXCLUSION

REMOTE_TARGET_KIND: Final[Mapping[RemoteDeployTarget, ExecutionEnvironmentKind]] = MappingProxyType(
    {
        RemoteDeployTarget.REMOTE_WORKSPACE: ExecutionEnvironmentKind.REMOTE_HOST,
        RemoteDeployTarget.RESEARCH_NODE: ExecutionEnvironmentKind.REMOTE_HOST,
        RemoteDeployTarget.SANDBOX: ExecutionEnvironmentKind.REMOTE_CONTAINER,
    }
)

_PAPER_SANDBOX_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "paper_sandbox",
        "paper-sandbox",
        "sandbox_paper",
        "sandbox-paper",
        "paper_as_sandbox",
        "paper_sandbox_account",
    }
)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def _parse_enum[EnumT: StrEnum](enum_type: type[EnumT], value: object, field: str) -> Result[EnumT]:
    try:
        return Ok(parse_closed(enum_type, value))
    except VocabularyError as exc:
        return _invalid(field, str(exc), given=repr(value))


@dataclass(frozen=True, slots=True)
class DeploymentEnvelope:
    """Default AD-25 placement: workstation daemon, Docker workers on that host."""

    host: str = DEFAULT_DAEMON_HOST
    worker_isolation: str = DEFAULT_WORKER_ISOLATION
    docker_workers_on_host: bool = True
    computer_use_provisioned: bool = False
    paper_is_sandbox: bool = False
    minted_promotion_command: None = None
    minted_zone_transition: None = None

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "host": self.host,
                "worker_isolation": self.worker_isolation,
                "docker_workers_on_host": self.docker_workers_on_host,
                "computer_use_provisioned": self.computer_use_provisioned,
                "gap_0070": dict(GAP_0070_COMPUTER_USE_EXCLUSION),
                "paper_is_sandbox": self.paper_is_sandbox,
                "paper_account_role": PAPER_ACCOUNT_ROLE,
                "sole_write": SOLE_ZONE_WRITE,
                "permitted_parent_write": [
                    SOLE_PERMITTED_PARENT_WRITE[0].value,
                    SOLE_PERMITTED_PARENT_WRITE[1].value,
                ],
                "minted_promotion_command": self.minted_promotion_command,
                "minted_zone_transition": self.minted_zone_transition,
                "remote_dial_direction": REMOTE_DIAL_DIRECTION,
                "daemon_dial_direction": DAEMON_DIAL_DIRECTION,
            }
        )


def default_deployment_envelope() -> DeploymentEnvelope:
    """Operator workstation plus Docker-per-worker isolation (FR-Q56)."""
    return DeploymentEnvelope()


@dataclass(frozen=True, slots=True)
class DialOutDeclaration:
    """Remote connection posture: dial out only, no deployed inbound port."""

    dials_out_to_daemon: bool = True
    exposes_inbound_listener: bool = False
    second_transport_channel: bool = False
    daemon_dials_in: bool = False
    daemon_address: str = ""


@dataclass(frozen=True, slots=True)
class RemoteDeploymentRequest:
    """Quant / Mission / Worker placement onto a remote CT-46 target."""

    unit: DeployableUnit
    target: RemoteDeployTarget
    host: str
    dial_out: DialOutDeclaration
    carries_trading_credential: bool = False
    running_node: bool = False
    provider_ref: str = ""
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HumanPromotionArtifactRef:
    """Artifact reference recorded after a human promotes outside QMA (L17)."""

    artifact_ref: str
    recorded_outside_qma: bool = True
    minted_promotion_command: None = None
    minted_zone_transition: None = None

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "artifact_ref": self.artifact_ref,
                "recorded_outside_qma": self.recorded_outside_qma,
                "minted_promotion_command": self.minted_promotion_command,
                "minted_zone_transition": self.minted_zone_transition,
            }
        )


def kind_and_lifecycle_for(
    target: RemoteDeployTarget | str,
) -> Result[tuple[ExecutionEnvironmentKind, EnvironmentLifecycle]]:
    """Map a remote target onto the ExecutionEnvironment kind and lifecycle."""
    parsed = _parse_enum(RemoteDeployTarget, target, "target")
    if not isinstance(parsed, Ok):
        return parsed
    resolved = parsed.value
    kind = REMOTE_TARGET_KIND[resolved]
    lifecycle = (
        EnvironmentLifecycle.EPHEMERAL
        if resolved is RemoteDeployTarget.SANDBOX
        else EnvironmentLifecycle.PERSISTENT
    )
    return Ok((kind, lifecycle))


def refuse_daemon_dial_in() -> TypedRefusal:
    """The daemon never opens an outbound dial to a deployed side."""
    return _policy(
        "daemon_dials_in",
        "the daemon never dials in; remotes dial out (CT-46; AD-25; FR-Q56)",
        remote_dial_direction=REMOTE_DIAL_DIRECTION,
        daemon_dial_direction=DAEMON_DIAL_DIRECTION,
    )


def refuse_deployed_inbound_port() -> TypedRefusal:
    """The deployed side exposes no inbound listener."""
    return _policy(
        "exposes_inbound_listener",
        "no inbound port is opened on the deployed side (CT-46; AD-25; FR-Q56)",
        daemon_is_sole_inbound=True,
    )


def refuse_promotion_command() -> TypedRefusal:
    """QMA mints no promotion command; a human promotes outside QMA."""
    return refuse_zone_transition_surface()


def refuse_paper_as_sandbox(*, given: str | None = None) -> TypedRefusal:
    """Paper is an account role on a real venue, never a sandbox."""
    return _policy(
        "paper",
        "paper is an account role on a real venue, never a sandbox (AD-25; SCN-0014; FR-Q56)",
        paper_is_sandbox=False,
        given=given,
    )


def refuse_computer_use_provision(*, host: str | None = None) -> TypedRefusal:
    """GAP-0070: the planned Windows VPS desktop host is not provisioned."""
    return _policy(
        "desktop",
        (
            "Windows VPS computer-use provision is Deferred GAP-0070; no desktop "
            "environment is registered (DEC-0324; FR-Q56)"
        ),
        gap=GAP_0070_COMPUTER_USE_EXCLUSION["gap"],
        status=GAP_0070_COMPUTER_USE_EXCLUSION["status"],
        provisioned=GAP_0070_COMPUTER_USE_EXCLUSION["provisioned"],
        host=host,
        kind=ExecutionEnvironmentKind.DESKTOP.value,
    )


def is_paper_sandbox_token(value: object) -> bool:
    """True when a token treats paper as a sandbox rather than an account role."""
    if not isinstance(value, str) or not value.strip():
        return False
    token = value.strip().casefold().replace("-", "_")
    if token in _PAPER_SANDBOX_TOKENS:
        return True
    return "paper" in token and "sandbox" in token


def admit_paper_role(*, treat_as_sandbox: bool = False, given: str | None = None) -> Result[str]:
    """Admit paper as a real-venue account role; refuse a sandbox reading."""
    if treat_as_sandbox or (given is not None and is_paper_sandbox_token(given)):
        return refuse_paper_as_sandbox(given=given)
    return Ok(PAPER_ACCOUNT_ROLE)


def validate_dial_out_declaration(declaration: DialOutDeclaration) -> Result[DialOutDeclaration]:
    """Refuse daemon dial-in, a deployed inbound port, or a missing daemon address."""
    if declaration.daemon_dials_in:
        return refuse_daemon_dial_in()
    if not declaration.dials_out_to_daemon:
        return _policy(
            "dials_out_to_daemon",
            "remote worker or deployed Quant must dial out to the daemon (CT-46; FR-Q56)",
        )
    if declaration.exposes_inbound_listener:
        return refuse_deployed_inbound_port()
    if declaration.second_transport_channel:
        return _policy(
            "second_transport_channel",
            "deployed side must expose no second transport channel (CT-46; FR-Q56)",
        )
    if declaration.daemon_address.strip() == "":
        return _invalid(
            "daemon_address",
            "deployed side must hold the daemon address to dial out (CT-46; FR-Q56)",
        )
    return Ok(declaration)


def parse_dial_out_declaration(
    *,
    dials_out_to_daemon: object = True,
    exposes_inbound_listener: object = False,
    second_transport_channel: object = False,
    daemon_dials_in: object = False,
    daemon_address: object = "",
) -> Result[DialOutDeclaration]:
    """Parse then validate the remote dial-out posture."""
    if not isinstance(dials_out_to_daemon, bool):
        return _invalid(
            "dials_out_to_daemon",
            "dials_out_to_daemon must be a bool",
            given=repr(dials_out_to_daemon),
        )
    if not isinstance(exposes_inbound_listener, bool):
        return _invalid(
            "exposes_inbound_listener",
            "exposes_inbound_listener must be a bool",
            given=repr(exposes_inbound_listener),
        )
    if not isinstance(second_transport_channel, bool):
        return _invalid(
            "second_transport_channel",
            "second_transport_channel must be a bool",
            given=repr(second_transport_channel),
        )
    if not isinstance(daemon_dials_in, bool):
        return _invalid(
            "daemon_dials_in",
            "daemon_dials_in must be a bool",
            given=repr(daemon_dials_in),
        )
    if not isinstance(daemon_address, str):
        return _invalid(
            "daemon_address",
            "daemon_address must be a string",
            given=repr(daemon_address),
        )
    return validate_dial_out_declaration(
        DialOutDeclaration(
            dials_out_to_daemon=dials_out_to_daemon,
            exposes_inbound_listener=exposes_inbound_listener,
            second_transport_channel=second_transport_channel,
            daemon_dials_in=daemon_dials_in,
            daemon_address=daemon_address,
        )
    )


def parse_remote_deployment_request(
    *,
    unit: DeployableUnit | str,
    target: RemoteDeployTarget | str,
    host: object,
    daemon_address: object,
    dials_out_to_daemon: object = True,
    exposes_inbound_listener: object = False,
    second_transport_channel: object = False,
    daemon_dials_in: object = False,
    carries_trading_credential: object = False,
    running_node: object = False,
    provider_ref: object = "",
    capabilities: Sequence[str] | None = (),
) -> Result[RemoteDeploymentRequest]:
    """Parse a remote Quant/Mission/Worker deployment through CT-46."""
    parsed_unit = _parse_enum(DeployableUnit, unit, "unit")
    if not isinstance(parsed_unit, Ok):
        return parsed_unit
    parsed_target = _parse_enum(RemoteDeployTarget, target, "target")
    if not isinstance(parsed_target, Ok):
        return parsed_target
    if not isinstance(host, str) or not host.strip():
        return _invalid("host", "remote deployment requires a host identity", given=repr(host))
    if not isinstance(carries_trading_credential, bool):
        return _invalid(
            "carries_trading_credential",
            "carries_trading_credential must be a bool",
            given=repr(carries_trading_credential),
        )
    if not isinstance(running_node, bool):
        return _invalid(
            "running_node",
            "running_node must be a bool",
            given=repr(running_node),
        )
    if not isinstance(provider_ref, str):
        return _invalid("provider_ref", "provider_ref must be a string", given=repr(provider_ref))
    caps = tuple(item.strip() for item in (capabilities or ()) if item.strip())
    tokens = (host, provider_ref, parsed_target.value, *caps)
    for token in tokens:
        if is_paper_sandbox_token(token):
            return refuse_paper_as_sandbox(given=token)
    dial_out = parse_dial_out_declaration(
        dials_out_to_daemon=dials_out_to_daemon,
        exposes_inbound_listener=exposes_inbound_listener,
        second_transport_channel=second_transport_channel,
        daemon_dials_in=daemon_dials_in,
        daemon_address=daemon_address,
    )
    if not isinstance(dial_out, Ok):
        return dial_out
    return Ok(
        RemoteDeploymentRequest(
            unit=parsed_unit.value,
            target=parsed_target.value,
            host=host.strip(),
            dial_out=dial_out.value,
            carries_trading_credential=carries_trading_credential,
            running_node=running_node,
            provider_ref=provider_ref.strip(),
            capabilities=caps,
        )
    )


def admit_zone_access(
    *,
    zone: AccountZone | str,
    mutation: ZoneMutation | str,
) -> Result[tuple[AccountZone, ZoneMutation]]:
    """Dev/paper are read-only except the content-addressed dev-zone candidate."""
    parsed_zone = _parse_enum(AccountZone, zone, "zone")
    if not isinstance(parsed_zone, Ok):
        return parsed_zone
    parsed_mutation = _parse_enum(ZoneMutation, mutation, "mutation")
    if not isinstance(parsed_mutation, Ok):
        return parsed_mutation
    resolved_zone = parsed_zone.value
    resolved_mutation = parsed_mutation.value
    if resolved_mutation in {ZoneMutation.PROMOTE, ZoneMutation.ZONE_TRANSITION}:
        return refuse_promotion_command()
    if resolved_zone is AccountZone.LIVE:
        return _policy(
            "zone",
            "QMA cannot access the live zone; a human promotes outside QMA (L17; FR-Q56)",
            zone=resolved_zone.value,
            mutation=resolved_mutation.value,
        )
    if resolved_mutation is ZoneMutation.READ:
        return Ok((resolved_zone, resolved_mutation))
    if resolved_zone is AccountZone.DEV and resolved_mutation is ZoneMutation.CANDIDATE_WRITE:
        return Ok((resolved_zone, resolved_mutation))
    if resolved_zone is AccountZone.PAPER:
        return refuse_paper_as_sandbox(given=f"{resolved_zone.value}:{resolved_mutation.value}")
    return _policy(
        "zone",
        "dev and paper access is read-only except the content-addressed "
        "dev-zone candidate (AD-25; FR-Q56)",
        zone=resolved_zone.value,
        mutation=resolved_mutation.value,
        sole_write=SOLE_ZONE_WRITE,
    )


def record_human_promotion_ref(
    artifact_ref: object,
    *,
    promotion_command: object = None,
    zone_transition: object = None,
) -> Result[HumanPromotionArtifactRef]:
    """Record only the artifact ref after a human promotes outside QMA."""
    if promotion_command is not None:
        return refuse_promotion_command()
    if zone_transition is not None:
        return refuse_promotion_command()
    if not isinstance(artifact_ref, str) or not artifact_ref.strip():
        return _invalid(
            "artifact_ref",
            "human promotion records an artifact reference only (L17; FR-Q56)",
            given=repr(artifact_ref),
        )
    return Ok(HumanPromotionArtifactRef(artifact_ref=artifact_ref.strip()))
