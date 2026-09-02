"""Deployment boundary and computer-use exclusion (CT-46; AD-25; FR-Q56).

On start the daemon sits on the operator workstation with Docker workers on
that host. Remote Quant / Mission / Worker placement goes through the
ExecutionEnvironment contract; the remote side dials out and never opens an
inbound port. Trading-node hosts are refused by identity. Dev and paper stay
read-only except the content-addressed dev-zone candidate. Computer-use stays
excluded until a desktop environment is registered (GAP-0070).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from qma.core.barriers.reachability import (
    GAP_0070_DESKTOP_EXCLUSION,
    parse_declaration,
    refuse_reachability,
    validate_execution_environment_declaration,
)
from qma.core.ports.compute import parse_compute_requirement
from qma.core.ports.deployment import (
    DAEMON_DIAL_DIRECTION,
    DEFAULT_DAEMON_HOST,
    DEFAULT_WORKER_ISOLATION,
    DEV_ZONE,
    PAPER_ACCOUNT_ROLE,
    PAPER_IS_SANDBOX,
    QMA_MINTED_PROMOTION_COMMAND,
    QMA_MINTED_ZONE_TRANSITION,
    REMOTE_DIAL_DIRECTION,
    SOLE_ZONE_WRITE,
    AccountZone,
    DeployableUnit,
    DeploymentEnvelope,
    HumanPromotionArtifactRef,
    RemoteDeploymentRequest,
    RemoteDeployTarget,
    ZoneMutation,
    admit_paper_role,
    admit_zone_access,
    default_deployment_envelope,
    kind_and_lifecycle_for,
    parse_remote_deployment_request,
    record_human_promotion_ref,
    refuse_computer_use_provision,
)
from qma.core.ports.execution import (
    ORDINARY_WORKER_IMAGE,
    ExecutionEnvironmentDeclaration,
)
from qma.core.ports.tools import ToolKind
from qma.core.refusals import NoEnvironment
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.daemon.envs.registry import ExecutionEnvironmentRegistry
from qma.daemon.envs.router import ComputeRouter, PlacementDecision
from qma.daemon.tools.parent_writes import DevZoneCandidate
from qma.daemon.tools.registry import ToolRegistry
from qma.wire.reachability import (
    DeployedSideConfig,
    ReachabilityPosture,
    validate_remote_dial_out,
)
from qmf.core import Ok, Result, is_refusal

__all__ = [
    "DeploymentBoundary",
    "RemoteDeployment",
]


@dataclass(frozen=True, slots=True)
class RemoteDeployment:
    """A remote unit bound through CT-46 with a validated dial-out posture."""

    request: RemoteDeploymentRequest
    declaration: ExecutionEnvironmentDeclaration
    dial_out: ReachabilityPosture

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "unit": self.request.unit.value,
                "target": self.request.target.value,
                "kind": self.declaration.kind.value,
                "host": self.request.host,
                "provider_ref": self.declaration.provider_ref,
                "remote_dial_direction": self.dial_out.remote_dial_direction,
                "daemon_dial_direction": self.dial_out.daemon_dial_direction,
                "daemon_is_sole_inbound": self.dial_out.daemon_is_sole_inbound,
                "deployed_exposes_listener": self.dial_out.deployed_exposes_listener,
            }
        )


class DeploymentBoundary:
    """Daemon-owned AD-25 envelope: workstation default, remote dial-out only."""

    def __init__(
        self,
        *,
        environments: ExecutionEnvironmentRegistry | None = None,
        tools: ToolRegistry | None = None,
        router: ComputeRouter | None = None,
    ) -> None:
        self._environments = (
            environments if environments is not None else ExecutionEnvironmentRegistry()
        )
        if tools is None:
            self._tools = ToolRegistry(environments=self._environments)
        else:
            self._tools = tools
            self._tools.bind_environments(self._environments)
        self._router = (
            router if router is not None else ComputeRouter(environments=self._environments)
        )
        self._envelope: DeploymentEnvelope | None = None
        self._remotes: dict[tuple[str, str], RemoteDeployment] = {}
        self._promotion_refs: list[HumanPromotionArtifactRef] = []

    @property
    def environments(self) -> ExecutionEnvironmentRegistry:
        return self._environments

    @property
    def tools(self) -> ToolRegistry:
        return self._tools

    @property
    def router(self) -> ComputeRouter:
        return self._router

    @property
    def envelope(self) -> DeploymentEnvelope | None:
        return self._envelope

    @property
    def minted_promotion_command(self) -> None:
        return QMA_MINTED_PROMOTION_COMMAND

    @property
    def minted_zone_transition(self) -> None:
        return QMA_MINTED_ZONE_TRANSITION

    @property
    def computer_use_excluded(self) -> bool:
        return ExecutionEnvironmentKind.DESKTOP.value not in self._environments.kinds()

    def start(self) -> Result[DeploymentEnvelope]:
        """Bind the workstation daemon and Docker-per-worker isolation."""
        if self._envelope is not None:
            return Ok(self._envelope)
        ordinary = ExecutionEnvironmentDeclaration.ordinary_docker_worker(
            provider_ref="operator-workstation-docker",
        )
        token = ExecutionEnvironmentKind.DOCKER.value
        if token not in self._environments.kinds():
            bound = self._environments.register_declaration(ordinary)
            if not isinstance(bound, Ok):
                return bound
        else:
            replaced = self._environments.replace_declaration(ordinary)
            if not isinstance(replaced, Ok):
                return replaced
        envelope = default_deployment_envelope()
        self._envelope = envelope
        return Ok(envelope)

    def deploy(
        self,
        *,
        unit: DeployableUnit | str,
        target: RemoteDeployTarget | str,
        host: str,
        daemon_address: str,
        dials_out_to_daemon: bool = True,
        exposes_inbound_listener: bool = False,
        second_transport_channel: bool = False,
        daemon_dials_in: bool = False,
        carries_trading_credential: bool = False,
        running_node: bool = False,
        provider_ref: str = "",
        capabilities: Sequence[str] = (),
        network: str = "none",
        reachable_hosts: Sequence[str] = (),
        image: str = "",
    ) -> Result[RemoteDeployment]:
        """Place a Quant, Mission, or Worker onto a remote CT-46 environment."""
        started = self.start()
        if not isinstance(started, Ok):
            return started
        request = parse_remote_deployment_request(
            unit=unit,
            target=target,
            host=host,
            daemon_address=daemon_address,
            dials_out_to_daemon=dials_out_to_daemon,
            exposes_inbound_listener=exposes_inbound_listener,
            second_transport_channel=second_transport_channel,
            daemon_dials_in=daemon_dials_in,
            carries_trading_credential=carries_trading_credential,
            running_node=running_node,
            provider_ref=provider_ref,
            capabilities=capabilities,
        )
        if not isinstance(request, Ok):
            return request
        parsed = request.value
        wire = DeployedSideConfig.try_create(
            dials_out_to_daemon=parsed.dial_out.dials_out_to_daemon,
            exposes_inbound_listener=parsed.dial_out.exposes_inbound_listener,
            second_transport_channel=parsed.dial_out.second_transport_channel,
            daemon_address=parsed.dial_out.daemon_address,
        )
        if not isinstance(wire, Ok):
            return wire
        posture = validate_remote_dial_out(wire.value)
        if not isinstance(posture, Ok):
            return posture
        if parsed.carries_trading_credential or parsed.running_node:
            reason = (
                "trading_credential_host"
                if parsed.carries_trading_credential
                else "running_node_host"
            )
            return refuse_reachability(
                surface="host",
                reason=reason,
                stage="registration",
                host=parsed.host,
                kind=parsed.target.value,
            )
        mapped = kind_and_lifecycle_for(parsed.target)
        if not isinstance(mapped, Ok):
            return mapped
        kind, lifecycle = mapped.value
        resolved_provider = parsed.provider_ref or f"{parsed.target.value}:{parsed.host}"
        resolved_image = image
        if kind is ExecutionEnvironmentKind.REMOTE_CONTAINER and not resolved_image:
            resolved_image = ORDINARY_WORKER_IMAGE
        declaration = parse_declaration(
            kind=kind,
            network=network,
            reachable_hosts=tuple(reachable_hosts),
            provider_ref=resolved_provider,
            image=resolved_image,
            host=parsed.host,
            lifecycle=lifecycle,
            capabilities=parsed.capabilities,
            carries_trading_credential=parsed.carries_trading_credential,
            running_node=parsed.running_node,
            stage="registration",
        )
        if not isinstance(declaration, Ok):
            return declaration
        bound = self._bind_declaration(declaration.value)
        if not isinstance(bound, Ok):
            return bound
        remote = RemoteDeployment(
            request=parsed,
            declaration=bound.value,
            dial_out=posture.value,
        )
        self._remotes[(parsed.unit.value, parsed.target.value)] = remote
        return Ok(remote)

    def _bind_declaration(
        self,
        declaration: ExecutionEnvironmentDeclaration,
    ) -> Result[ExecutionEnvironmentDeclaration]:
        token = declaration.kind.value
        if token not in self._environments.kinds():
            registered = self._environments.register_declaration(declaration)
            if not isinstance(registered, Ok):
                return registered
            stored = self._environments.declaration(token)
            if stored is None:
                return NoEnvironment.of(kind=token)
            return Ok(stored)
        barrier = validate_execution_environment_declaration(
            declaration,
            stage="registration",
            kind=declaration.kind,
        )
        if not isinstance(barrier, Ok):
            return barrier
        return Ok(self._environments.declaration(token) or barrier.value)

    def access_zone(
        self,
        *,
        zone: AccountZone | str,
        mutation: ZoneMutation | str,
    ) -> Result[tuple[str, str]]:
        """Expose zone authority: read-only except the dev-zone candidate."""
        admitted = admit_zone_access(zone=zone, mutation=mutation)
        if not isinstance(admitted, Ok):
            return admitted
        resolved_zone, resolved_mutation = admitted.value
        return Ok((resolved_zone.value, resolved_mutation.value))

    def write_dev_zone_candidate(
        self,
        payload: Mapping[str, object],
        *,
        origin: str = "qma",
        summary: str | None = None,
        zone: str = DEV_ZONE,
    ) -> Result[DevZoneCandidate]:
        """Sole writable parent surface: a content-addressed ``dev`` candidate."""
        admitted = admit_zone_access(zone=zone, mutation=ZoneMutation.CANDIDATE_WRITE)
        if not isinstance(admitted, Ok):
            return admitted
        return self._tools.write_dev_zone_candidate(
            payload,
            origin=origin,
            summary=summary,
            zone=zone,
        )

    def record_human_promotion(
        self,
        artifact_ref: object,
        *,
        promotion_command: object = None,
        zone_transition: object = None,
    ) -> Result[HumanPromotionArtifactRef]:
        """Record the artifact ref after a human promotes outside QMA."""
        recorded = record_human_promotion_ref(
            artifact_ref,
            promotion_command=promotion_command,
            zone_transition=zone_transition,
        )
        if not isinstance(recorded, Ok):
            return recorded
        self._promotion_refs.append(recorded.value)
        return recorded

    def attempt_promotion(self) -> Result[DevZoneCandidate]:
        """QMA mints no promotion command."""
        return self._tools.attempt_zone_transition()

    def attempt_zone_transition(self) -> Result[DevZoneCandidate]:
        """QMA mints no zone-transition command."""
        return self._tools.attempt_zone_transition()

    def admit_paper(self, *, treat_as_sandbox: bool = False) -> Result[str]:
        """Paper is a real-venue account role, never a sandbox."""
        return admit_paper_role(treat_as_sandbox=treat_as_sandbox)

    def register_computer_use_tool(
        self,
        tool_id: str = "computer:click",
    ) -> Result[str]:
        """Register a computer-use tool; it stays unavailable until desktop exists."""
        return self._tools.register(
            tool_id=tool_id,
            kind=ToolKind.COMPUTER_USE,
            schema={"name": tool_id.rsplit(":", 1)[-1]},
            acts=("click",),
        )

    def place_computer_use(
        self, *, task_id: str = "task:computer-use"
    ) -> Result[PlacementDecision]:
        """Desktop ComputeRequirement returns ``NoEnvironment`` while GAP-0070 holds."""
        requirement = parse_compute_requirement(
            kind=ExecutionEnvironmentKind.DESKTOP,
            cpu=1,
            memory=512,
            disk=1024,
            timeout=1_000_000_000,
            max_memory=512,
            isolation="shared",
            capabilities=("display",),
        )
        if not isinstance(requirement, Ok):
            return requirement
        return self._router.place_requirement(task_id=task_id, requirement=requirement.value)

    def provision_computer_use_vps(
        self,
        host: str | None = None,
    ) -> Result[ExecutionEnvironmentDeclaration]:
        """Refuse Windows VPS provision (Deferred GAP-0070)."""
        refused = self._router.provision_windows_vps(host=host)
        if is_refusal(refused):
            return refuse_computer_use_provision(host=host)
        return refused

    def remote(self, unit: str, target: str) -> RemoteDeployment | None:
        return self._remotes.get((unit, target))

    def snapshot(self) -> Mapping[str, object]:
        envelope: Mapping[str, object]
        if self._envelope is not None:
            envelope = self._envelope.to_payload()
        else:
            envelope = MappingProxyType({})
        return MappingProxyType(
            {
                "started": self._envelope is not None,
                "host": DEFAULT_DAEMON_HOST,
                "worker_isolation": DEFAULT_WORKER_ISOLATION,
                "docker_workers_on_host": True,
                "kinds": sorted(self._environments.kinds()),
                "desktop_registered": not self.computer_use_excluded,
                "computer_use_excluded": self.computer_use_excluded,
                "gap_0070": dict(GAP_0070_DESKTOP_EXCLUSION),
                "paper_is_sandbox": PAPER_IS_SANDBOX,
                "paper_account_role": PAPER_ACCOUNT_ROLE,
                "sole_write": SOLE_ZONE_WRITE,
                "minted_promotion_command": self.minted_promotion_command,
                "minted_zone_transition": self.minted_zone_transition,
                "remote_dial_direction": REMOTE_DIAL_DIRECTION,
                "daemon_dial_direction": DAEMON_DIAL_DIRECTION,
                "remote_deployments": [dict(item.to_payload()) for item in self._remotes.values()],
                "human_promotion_refs": [dict(item.to_payload()) for item in self._promotion_refs],
                "envelope": dict(envelope),
            }
        )
