"""ExecutionEnvironment provider registry (CT-46; AD-17; FR-Q27, FR-Q47, FR-Q48).

Registration and placement run the AD-28 reachability barrier and the
FR-Q48 declaration-surface checks. A missing network posture, a deny-listed
host, a forbidden image, a dirty shared filesystem, a control-channel
env-var allowlist, or a dirty computer-use profile is refused here — never
as a runtime hook deny.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, cast

from qma.core.barriers.reachability import (
    parse_declaration,
    refuse_forbidden_model_adapter,
    refuse_handed_venue_login,
    refuse_reachability,
    refuse_reachability_waiver,
    validate_computer_use_profile,
    validate_execution_environment_declaration,
    validate_worker_image,
)
from qma.core.ports.execution import (
    ComputerUseProfile,
    ExecutionEnvironment,
    ExecutionEnvironmentDeclaration,
    WorkerImageManifest,
)
from qma.core.refusals import NoEnvironment, ProhibitedReachability
from qma.core.vocabulary.enums import EnvironmentLifecycle, ExecutionEnvironmentKind
from qmf.core import Ok, Result
from qmf.data.store.refusals import invalid_input

__all__ = [
    "EnvironmentLease",
    "ExecutionEnvironmentRegistry",
]


@dataclass(frozen=True, slots=True)
class EnvironmentLease:
    """Per-slot environment lease distinct from ``dispatch_lease`` (AD-17)."""

    task_id: str
    kind: str
    slot_id: str
    provider_id: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "lease": "environment_lease",
            "task_id": self.task_id,
            "kind": self.kind,
            "slot_id": self.slot_id,
        }
        if self.provider_id is not None:
            payload["provider_id"] = self.provider_id
        return MappingProxyType(payload)


def _kind_token(kind: ExecutionEnvironmentKind | str) -> str:
    return kind.value if isinstance(kind, ExecutionEnvironmentKind) else kind


def _coerce_declaration(
    kind: ExecutionEnvironmentKind | str,
    environment: object,
    *,
    provider_id: str | None,
    declaration: ExecutionEnvironmentDeclaration | None,
) -> Result[ExecutionEnvironmentDeclaration | None]:
    if declaration is not None:
        return Ok(declaration)
    if isinstance(environment, ExecutionEnvironmentDeclaration):
        return Ok(environment)
    network = getattr(environment, "network", None)
    if network is None:
        return Ok(None)
    hosts_raw = getattr(environment, "reachable_hosts", None)
    hosts: tuple[str, ...] | None
    if hosts_raw is None:
        hosts = None
    elif isinstance(hosts_raw, tuple):
        hosts = tuple(str(item) for item in cast(tuple[object, ...], hosts_raw))
    else:
        hosts = None
    mounts_raw = getattr(environment, "mounts", None)
    allowlist = getattr(environment, "environment_allowlist", None)
    capabilities = getattr(environment, "capabilities", None)
    lifecycle_raw = getattr(environment, "lifecycle", None)
    lifecycle: EnvironmentLifecycle | str | None
    if isinstance(lifecycle_raw, EnvironmentLifecycle) or lifecycle_raw is None:
        lifecycle = lifecycle_raw
    else:
        lifecycle = str(lifecycle_raw)
    mounts: tuple[object, ...] | None = (
        tuple(cast(tuple[object, ...], mounts_raw)) if isinstance(mounts_raw, tuple) else None
    )
    parsed = parse_declaration(
        kind=kind,
        network=network,
        reachable_hosts=hosts,
        provider_ref=str(getattr(environment, "provider_ref", None) or provider_id or ""),
        image=str(getattr(environment, "image", "") or ""),
        host=str(getattr(environment, "host", "") or ""),
        lifecycle=lifecycle,
        mounts=mounts,
        environment_allowlist=(
            tuple(str(item) for item in cast(tuple[object, ...], allowlist))
            if isinstance(allowlist, tuple)
            else None
        ),
        capabilities=(
            tuple(str(item) for item in cast(tuple[object, ...], capabilities))
            if isinstance(capabilities, tuple)
            else None
        ),
        carries_trading_credential=bool(getattr(environment, "carries_trading_credential", False)),
        running_node=bool(getattr(environment, "running_node", False)),
    )
    if not isinstance(parsed, Ok):
        return parsed
    return Ok(parsed.value)


class ExecutionEnvironmentRegistry:
    """In-memory singleton-per-kind registry for the ExecutionEnvironment port.

    Empty by default. Lease evaluation against an unbound kind returns
    ``NoEnvironment`` without affecting Mission compilation (FR-Q27).
    Reachability violations return ``ProhibitedReachability`` at registration
    or placement (FR-Q47).
    """

    def __init__(self) -> None:
        self._by_kind: dict[str, ExecutionEnvironment] = {}
        self._provider_ids: dict[str, str] = {}
        self._declarations: dict[str, ExecutionEnvironmentDeclaration] = {}
        self._profiles: dict[str, ComputerUseProfile] = {}

    def register(
        self,
        kind: ExecutionEnvironmentKind | str,
        environment: ExecutionEnvironment,
        *,
        provider_id: str | None = None,
        declaration: ExecutionEnvironmentDeclaration | None = None,
    ) -> Result[str]:
        """Bind one ExecutionEnvironment for ``kind`` (singleton cardinality).

        The reachability barrier runs before the binding is stored. An
        unenumerated network posture is refused; no hook is consulted.
        """
        token = _kind_token(kind)
        try:
            ExecutionEnvironmentKind(token)
        except ValueError:
            return invalid_input(
                "kind",
                "ExecutionEnvironment kind must be one of the six closed values (CT-46; AD-17)",
                given=repr(token),
            )
        if token in self._by_kind:
            return invalid_input(
                "kind",
                "ExecutionEnvironment is singleton per kind; duplicate binding refused (AD-1)",
                given=token,
            )
        coerced = _coerce_declaration(
            kind,
            environment,
            provider_id=provider_id,
            declaration=declaration,
        )
        if not isinstance(coerced, Ok):
            return coerced
        barrier = validate_execution_environment_declaration(
            coerced.value,
            stage="registration",
            kind=kind,
        )
        if not isinstance(barrier, Ok):
            return barrier
        stored = barrier.value
        self._by_kind[token] = environment
        self._declarations[token] = stored
        if provider_id is not None:
            self._provider_ids[token] = provider_id
        elif stored.provider_ref:
            self._provider_ids[token] = stored.provider_ref
        if stored.profile is not None:
            self._profiles[token] = stored.profile
        return Ok(token)

    def register_declaration(
        self,
        declaration: ExecutionEnvironmentDeclaration,
        *,
        provider_id: str | None = None,
    ) -> Result[str]:
        """Register a complete CT-46 declaration; reachability runs first."""
        return self.register(
            declaration.kind,
            declaration,
            provider_id=provider_id or declaration.provider_ref or None,
            declaration=declaration,
        )

    def select_ordinary_worker(self) -> Result[ExecutionEnvironmentDeclaration]:
        """Docker-per-worker ephemeral is the ordinary worker environment."""
        stored = self._declarations.get(ExecutionEnvironmentKind.DOCKER.value)
        if stored is None:
            return Ok(ExecutionEnvironmentDeclaration.ordinary_docker_worker())
        if not stored.is_docker_per_worker():
            return refuse_reachability(
                surface="environment",
                reason="ordinary_worker_not_ephemeral",
                stage="registration",
                kind=ExecutionEnvironmentKind.DOCKER.value,
                matched=stored.lifecycle.value,
            )
        return Ok(stored)

    def ensure_ordinary_worker(self) -> Result[ExecutionEnvironmentDeclaration]:
        """Bind the ordinary docker-per-worker environment when docker is unbound."""
        selected = self.select_ordinary_worker()
        if not isinstance(selected, Ok):
            return selected
        if ExecutionEnvironmentKind.DOCKER.value not in self._by_kind:
            bound = self.register_declaration(selected.value)
            if not isinstance(bound, Ok):
                return bound
        stored = self._declarations[ExecutionEnvironmentKind.DOCKER.value]
        return Ok(stored)

    def register_worker_image(
        self,
        manifest: WorkerImageManifest,
        *,
        kind: ExecutionEnvironmentKind | str | None = None,
    ) -> Result[WorkerImageManifest]:
        """Image validation at registration — forbidden SDKs never bind."""
        return validate_worker_image(
            manifest,
            stage="registration",
            kind=_kind_token(kind) if kind is not None else None,
        )

    def register_computer_use_profile(
        self,
        profile: ComputerUseProfile,
        *,
        kind: ExecutionEnvironmentKind | str = ExecutionEnvironmentKind.DESKTOP,
    ) -> Result[ComputerUseProfile]:
        """Refuse a dirty computer-use profile at registration (GAP-0070 excluded)."""
        checked = validate_computer_use_profile(
            profile,
            stage="registration",
            kind=_kind_token(kind),
            require=True,
        )
        if not isinstance(checked, Ok):
            return checked
        stored = checked.value
        if stored is None:
            return refuse_reachability(
                surface="profile",
                reason="missing_profile",
                stage="registration",
                kind=_kind_token(kind),
            )
        self._profiles[_kind_token(kind)] = stored
        return Ok(stored)

    def hand_profile_secret(
        self,
        *,
        via: str,
        payload: str,
    ) -> ProhibitedReachability:
        """Venue logins may not be handed through Knowledge, Memory, ledger, or tools."""
        return refuse_handed_venue_login(via=via, payload=payload, stage="registration")

    def refuse_waiver(self, *, via: str, host: str) -> ProhibitedReachability:
        """Role/Mission/plugin/permission/hook cannot lift a host denial."""
        return refuse_reachability_waiver(via=via, host=host, stage="registration")

    def refuse_openrouter_adapter(self, adapter: str) -> ProhibitedReachability | None:
        """OpenRouter is not a QMA model path."""
        return refuse_forbidden_model_adapter(adapter, stage="registration")

    def get(self, kind: str) -> ExecutionEnvironment | None:
        return self._by_kind.get(kind)

    def declaration(self, kind: str) -> ExecutionEnvironmentDeclaration | None:
        return self._declarations.get(kind)

    def is_empty(self) -> bool:
        return not self._by_kind

    def kinds(self) -> frozenset[str]:
        return frozenset(self._by_kind)

    def evaluate_environment_lease(
        self,
        *,
        task_id: str,
        kind: ExecutionEnvironmentKind | str,
        host: str | None = None,
    ) -> Result[EnvironmentLease]:
        """Issue an ``environment_lease`` or refuse at placement.

        Unbound kinds return ``NoEnvironment``. A reachability hit returns
        ``ProhibitedReachability`` rather than a hook deny. Does not mint
        durable placement state — Epic 45 owns slot governance.
        """
        if not task_id:
            return invalid_input("task_id", "environment_lease requires a task_id")
        token = _kind_token(kind)
        if token not in self._by_kind:
            return NoEnvironment.of(kind=token)
        stored = self._declarations.get(token)
        barrier = validate_execution_environment_declaration(
            stored,
            stage="placement",
            kind=kind,
        )
        if not isinstance(barrier, Ok):
            return barrier
        if host:
            identity = parse_declaration(
                kind=barrier.value.kind,
                network=barrier.value.network,
                reachable_hosts=barrier.value.reachable_hosts,
                provider_ref=barrier.value.provider_ref,
                image=barrier.value.image,
                host=host,
                lifecycle=barrier.value.lifecycle,
                mounts=barrier.value.mounts,
                environment_allowlist=barrier.value.environment_allowlist,
                capabilities=barrier.value.capabilities,
                carries_trading_credential=barrier.value.carries_trading_credential,
                running_node=barrier.value.running_node,
                image_packages=barrier.value.image_packages,
                image_imports=barrier.value.image_imports,
                profile=barrier.value.profile,
                stage="placement",
            )
            if not isinstance(identity, Ok):
                return identity
        slot_id = f"slot:{token}:0"
        return Ok(
            EnvironmentLease(
                task_id=task_id,
                kind=token,
                slot_id=slot_id,
                provider_id=self._provider_ids.get(token),
            )
        )

    def place(
        self,
        *,
        task_id: str,
        kind: ExecutionEnvironmentKind | str,
        host: str | None = None,
        declaration: ExecutionEnvironmentDeclaration | None = None,
    ) -> Result[EnvironmentLease]:
        """Placement entry: reachability first, then ``NoEnvironment`` if unbound."""
        if declaration is not None:
            barrier = validate_execution_environment_declaration(
                declaration,
                stage="placement",
                kind=kind,
            )
            if not isinstance(barrier, Ok):
                return barrier
        elif host:
            probed = parse_declaration(
                kind=kind,
                network="none",
                reachable_hosts=(),
                host=host,
                provider_ref=host,
                stage="placement",
            )
            if not isinstance(probed, Ok):
                return probed
        return self.evaluate_environment_lease(task_id=task_id, kind=kind, host=host)

    def snapshot(self) -> Mapping[str, Any]:
        ordinary = self._declarations.get(ExecutionEnvironmentKind.DOCKER.value)
        return MappingProxyType(
            {
                "kinds": sorted(self._by_kind),
                "empty": self.is_empty(),
                "lifecycles": {
                    kind: declaration.lifecycle.value
                    for kind, declaration in self._declarations.items()
                },
                "ordinary_worker": (
                    ordinary.is_docker_per_worker() if ordinary is not None else False
                ),
            }
        )
