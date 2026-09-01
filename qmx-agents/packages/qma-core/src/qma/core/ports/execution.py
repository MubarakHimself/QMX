"""ExecutionEnvironment port — singleton per ``kind`` (CT-46; AD-1, AD-17).

Declaration shapes used by the AD-28 reachability barrier live here as
definitions. The daemon registry is the only registrar.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Protocol, cast, runtime_checkable

from qma.core.vocabulary.enums import (
    EnvironmentLifecycle,
    ExecutionEnvironmentKind,
    NetworkPolicy,
    VariableEditability,
)
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "CONTROL_CHANNEL_ENV_NAMES",
    "DECLARATION_SURFACE_FIELDS",
    "ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT",
    "ENVIRONMENT_MAX_IN_FLIGHT_KEY",
    "MOUNT_MODES",
    "ORDINARY_WORKER_IMAGE",
    "ORDINARY_WORKER_PROVIDER_REF",
    "PINNED_SINGLE_SLOT_KINDS",
    "ComputerUseProfile",
    "EnvironmentMount",
    "ExecutionEnvironment",
    "ExecutionEnvironmentDeclaration",
    "WorkerImageManifest",
    "is_control_channel_env_name",
    "is_pinned_single_slot_kind",
    "max_in_flight_editability",
    "parse_environment_mount",
    "resolve_max_in_flight",
]


# CT-46 surface a registered declaration must carry (FR-Q48).
DECLARATION_SURFACE_FIELDS: Final[tuple[str, ...]] = (
    "kind",
    "provider_ref",
    "image",
    "mounts",
    "environment_allowlist",
    "capabilities",
    "network",
    "lifecycle",
)

MOUNT_MODES: Final[frozenset[str]] = frozenset({"ro", "rw"})

ORDINARY_WORKER_PROVIDER_REF: Final[str] = "local-docker"
ORDINARY_WORKER_IMAGE: Final[str] = "qma-worker:isolated"

# Record-homed AD-26 row; default and pinned-kind ceiling are the registered value.
ENVIRONMENT_MAX_IN_FLIGHT_KEY: Final[str] = "registry:environment.max_in_flight"
ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT: Final[int] = 1
PINNED_SINGLE_SLOT_KINDS: Final[frozenset[ExecutionEnvironmentKind]] = frozenset(
    {
        ExecutionEnvironmentKind.REMOTE_HOST,
        ExecutionEnvironmentKind.DESKTOP,
    }
)

# Env-var names that would turn the allowlist into a control channel (AD-17).
CONTROL_CHANNEL_ENV_NAMES: Final[frozenset[str]] = frozenset(
    {
        "control_channel",
        "daemon_command",
        "daemon_control",
        "qma_command",
        "qma_control",
        "qma_control_channel",
        "qma_daemon_control",
        "qmn_control",
        "trading_node_control",
        "venue_control",
    }
)

_ENV_VAR_NAME: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@runtime_checkable
class ExecutionEnvironment(Protocol):
    """Definitions-only ExecutionEnvironment seam; one binding per environment kind.

    Cardinality: singleton, scope key ``kind`` (see ``PORT_CONTRACTS``).
    """


def _kind_value(kind: ExecutionEnvironmentKind | str) -> ExecutionEnvironmentKind:
    if isinstance(kind, ExecutionEnvironmentKind):
        return kind
    return parse_closed(ExecutionEnvironmentKind, kind)


def is_pinned_single_slot_kind(kind: ExecutionEnvironmentKind | str) -> bool:
    """True when ``remote_host`` / ``desktop`` pin capacity to one slot (FR-Q49)."""
    try:
        return _kind_value(kind) in PINNED_SINGLE_SLOT_KINDS
    except VocabularyError:
        return False


def max_in_flight_editability(
    kind: ExecutionEnvironmentKind | str,
) -> VariableEditability:
    """Per-kind editability of ``registry:environment.max_in_flight`` (AD-26).

    One variable: ``ui-editable`` for local, docker, remote_container and
    browser; pinned and ``uneditable`` for remote_host and desktop. No second
    registry key expresses the pin.
    """
    if is_pinned_single_slot_kind(kind):
        return VariableEditability.UNEDITABLE
    return VariableEditability.UI_EDITABLE


def _max_in_flight_refusal(reason: str, **ctx: object) -> TypedRefusal:
    context: dict[str, object] = {
        "field": "max_in_flight",
        "reason": reason,
        "registry_key": ENVIRONMENT_MAX_IN_FLIGHT_KEY,
    }
    context.update(ctx)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def resolve_max_in_flight(
    kind: ExecutionEnvironmentKind | str,
    declared: object = None,
) -> Result[int]:
    """Resolve declaration capacity from ``registry:environment.max_in_flight``.

    Pinned kinds may never exceed the registered single-slot ceiling.
    """
    try:
        resolved_kind = _kind_value(kind)
    except VocabularyError as exc:
        return _max_in_flight_refusal("invalid_kind", given=repr(kind), matched=str(exc))
    if declared is None:
        value = ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT
    elif isinstance(declared, bool) or not isinstance(declared, int):
        return _max_in_flight_refusal(
            "invalid_max_in_flight",
            kind=resolved_kind.value,
            given=repr(declared),
        )
    elif declared < ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT:
        return _max_in_flight_refusal(
            "invalid_max_in_flight",
            kind=resolved_kind.value,
            given=declared,
        )
    else:
        value = declared
    if resolved_kind in PINNED_SINGLE_SLOT_KINDS and value != ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT:
        return _max_in_flight_refusal(
            "max_in_flight_pinned",
            kind=resolved_kind.value,
            given=value,
            pinned=ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT,
            editability=VariableEditability.UNEDITABLE.value,
        )
    return Ok(value)


def _parse_max_in_flight(value: object) -> int:
    if value is None:
        return ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT
    if isinstance(value, bool) or not isinstance(value, int):
        raise VocabularyError(
            f"{value!r} is not a positive count for {ENVIRONMENT_MAX_IN_FLIGHT_KEY}"
        )
    if value < ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT:
        raise VocabularyError(
            f"{value!r} is not a positive count for {ENVIRONMENT_MAX_IN_FLIGHT_KEY}"
        )
    return value


def _tuple_of_str(values: Sequence[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(item.strip() for item in values if item.strip())


def is_control_channel_env_name(name: object) -> bool:
    """True when an env-var token would be a control channel, not a declared name."""
    if not isinstance(name, str) or not name.strip():
        return False
    raw = name.strip()
    if "=" in raw or any(ch.isspace() for ch in raw):
        return True
    token = raw.casefold()
    if token in CONTROL_CHANNEL_ENV_NAMES:
        return True
    return "control_channel" in token


def parse_environment_mount(value: object) -> EnvironmentMount:
    """Parse one mount; invented modes fail as ``VocabularyError``."""
    if isinstance(value, EnvironmentMount):
        source = value.source.strip()
        target = value.target.strip()
        mode = value.mode.strip().casefold()
        shared = value.shared
    elif isinstance(value, Mapping):
        mapping = cast(Mapping[str, object], value)
        source = str(mapping.get("source", "") or "").strip()
        target = str(mapping.get("target", "") or "").strip()
        mode = str(mapping.get("mode", "ro") or "ro").strip().casefold()
        shared = bool(mapping.get("shared", False))
    else:
        raise VocabularyError(f"{value!r} is not a member of closed vocabulary EnvironmentMount")
    if not source or not target:
        raise VocabularyError("environment mount requires source and target (CT-46; AD-17)")
    if mode not in MOUNT_MODES:
        raise VocabularyError(f"{mode!r} is not a member of closed vocabulary mount mode")
    return EnvironmentMount(source=source, target=target, mode=mode, shared=shared)


@dataclass(frozen=True, slots=True)
class EnvironmentMount:
    """One declared mount. Shared writable mounts are a dirty filesystem (AD-17)."""

    source: str
    target: str
    mode: str = "ro"
    shared: bool = False

    @property
    def writable(self) -> bool:
        return self.mode == "rw"

    def is_shared_dirty(self) -> bool:
        """Shared plus writable is the dirty shared filesystem AD-17 forbids."""
        return self.shared and self.writable


@dataclass(frozen=True, slots=True)
class WorkerImageManifest:
    """Installed and imported dependencies of a worker image (AD-28; FR-Q47)."""

    image: str = ""
    packages: tuple[str, ...] = ()
    imports: tuple[str, ...] = ()

    @classmethod
    def from_values(
        cls,
        *,
        image: str = "",
        packages: Sequence[str] = (),
        imports: Sequence[str] = (),
    ) -> WorkerImageManifest:
        return cls(
            image=image.strip(),
            packages=_tuple_of_str(packages),
            imports=_tuple_of_str(imports),
        )


@dataclass(frozen=True, slots=True)
class ComputerUseProfile:
    """Browser/computer-use profile inspected at registration (AD-28; FR-Q47)."""

    reachable_hosts: tuple[str, ...] = ()
    cookie_hosts: tuple[str, ...] = ()
    session_hosts: tuple[str, ...] = ()
    saved_credential_refs: tuple[str, ...] = ()
    venue_logins: tuple[str, ...] = ()
    handed_via: str | None = None

    @classmethod
    def from_values(
        cls,
        *,
        reachable_hosts: Sequence[str] = (),
        cookie_hosts: Sequence[str] = (),
        session_hosts: Sequence[str] = (),
        saved_credential_refs: Sequence[str] = (),
        venue_logins: Sequence[str] = (),
        handed_via: str | None = None,
    ) -> ComputerUseProfile:
        via = handed_via.strip().casefold() if isinstance(handed_via, str) else None
        return cls(
            reachable_hosts=_tuple_of_str(reachable_hosts),
            cookie_hosts=_tuple_of_str(cookie_hosts),
            session_hosts=_tuple_of_str(session_hosts),
            saved_credential_refs=_tuple_of_str(saved_credential_refs),
            venue_logins=_tuple_of_str(venue_logins),
            handed_via=via or None,
        )


def _parse_mounts(values: Sequence[object] | None) -> tuple[EnvironmentMount, ...]:
    if not values:
        return ()
    return tuple(parse_environment_mount(item) for item in values)


def _parse_env_var_names(values: Sequence[str] | None) -> tuple[str, ...]:
    names = _tuple_of_str(values)
    for name in names:
        if not _ENV_VAR_NAME.fullmatch(name):
            raise VocabularyError(
                f"{name!r} is not a declared environment-variable name (CT-46; AD-17)"
            )
    return names


@dataclass(frozen=True, slots=True)
class ExecutionEnvironmentDeclaration:
    """Reachability-bearing ExecutionEnvironment declaration (CT-46; AD-17, AD-28).

    ``network`` is required and closed to ``none`` | ``allowlist``. ``none``
    enumerates an empty reachable-host set. Host identity for ``remote_host``
    and ``desktop`` is ``host`` or ``provider_ref``. Lifecycle is ``ephemeral``
    or ``persistent``; docker-per-worker ephemeral is the ordinary default.
    The environment-variable allowlist is declarative names, never a control
    channel. Slot capacity is the record-homed
    ``registry:environment.max_in_flight`` value (default 1); ``remote_host``
    and ``desktop`` pin that one variable to 1 as ``uneditable``.
    """

    kind: ExecutionEnvironmentKind
    network: NetworkPolicy
    reachable_hosts: tuple[str, ...]
    provider_ref: str
    image: str = ""
    host: str = ""
    lifecycle: EnvironmentLifecycle = EnvironmentLifecycle.EPHEMERAL
    mounts: tuple[EnvironmentMount, ...] = ()
    environment_allowlist: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    carries_trading_credential: bool = False
    running_node: bool = False
    image_packages: tuple[str, ...] = ()
    image_imports: tuple[str, ...] = ()
    profile: ComputerUseProfile | None = None
    max_in_flight: int = ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT

    @classmethod
    def isolated(
        cls,
        kind: ExecutionEnvironmentKind | str = ExecutionEnvironmentKind.DOCKER,
        *,
        provider_ref: str = "local",
        image: str = "qma-worker:isolated",
    ) -> ExecutionEnvironmentDeclaration:
        """Explicit ``network=none`` isolated posture — never an open default."""
        if isinstance(kind, ExecutionEnvironmentKind):
            resolved = kind
        else:
            resolved = parse_closed(ExecutionEnvironmentKind, kind)
        return cls(
            kind=resolved,
            network=NetworkPolicy.NONE,
            reachable_hosts=(),
            provider_ref=provider_ref,
            image=image,
            lifecycle=EnvironmentLifecycle.EPHEMERAL,
        )

    @classmethod
    def ordinary_docker_worker(
        cls,
        *,
        provider_ref: str = ORDINARY_WORKER_PROVIDER_REF,
        image: str = ORDINARY_WORKER_IMAGE,
    ) -> ExecutionEnvironmentDeclaration:
        """Docker-per-worker ephemeral ordinary worker (CT-46; FR-Q48)."""
        return cls.isolated(
            ExecutionEnvironmentKind.DOCKER,
            provider_ref=provider_ref,
            image=image,
        )

    @classmethod
    def try_parse(
        cls,
        *,
        kind: ExecutionEnvironmentKind | str,
        network: NetworkPolicy | str | None,
        reachable_hosts: Sequence[str] | None = None,
        provider_ref: str = "",
        image: str = "",
        host: str = "",
        lifecycle: EnvironmentLifecycle | str | None = None,
        mounts: Sequence[object] | None = None,
        environment_allowlist: Sequence[str] | None = None,
        capabilities: Sequence[str] | None = None,
        carries_trading_credential: bool = False,
        running_node: bool = False,
        image_packages: Sequence[str] = (),
        image_imports: Sequence[str] = (),
        profile: ComputerUseProfile | None = None,
        max_in_flight: object = None,
    ) -> ExecutionEnvironmentDeclaration:
        """Parse closed kind/network/lifecycle; invented values fail as ``VocabularyError``."""
        if isinstance(kind, ExecutionEnvironmentKind):
            resolved_kind = kind
        else:
            resolved_kind = parse_closed(ExecutionEnvironmentKind, kind)
        if network is None:
            raise VocabularyError("network is required; no open default (AD-28; FR-Q47)")
        if isinstance(network, NetworkPolicy):
            resolved_network = network
        else:
            resolved_network = parse_closed(NetworkPolicy, network)
        if lifecycle is None:
            resolved_lifecycle = EnvironmentLifecycle.EPHEMERAL
        elif isinstance(lifecycle, EnvironmentLifecycle):
            resolved_lifecycle = lifecycle
        else:
            resolved_lifecycle = parse_closed(EnvironmentLifecycle, lifecycle)
        hosts = _tuple_of_str(reachable_hosts)
        return cls(
            kind=resolved_kind,
            network=resolved_network,
            reachable_hosts=hosts,
            provider_ref=provider_ref.strip(),
            image=image.strip(),
            host=host.strip(),
            lifecycle=resolved_lifecycle,
            mounts=_parse_mounts(mounts),
            environment_allowlist=_parse_env_var_names(environment_allowlist),
            capabilities=_tuple_of_str(capabilities),
            carries_trading_credential=carries_trading_credential,
            running_node=running_node,
            image_packages=_tuple_of_str(image_packages),
            image_imports=_tuple_of_str(image_imports),
            profile=profile,
            max_in_flight=_parse_max_in_flight(max_in_flight),
        )

    def image_manifest(self) -> WorkerImageManifest:
        return WorkerImageManifest.from_values(
            image=self.image,
            packages=self.image_packages,
            imports=self.image_imports,
        )

    def identity_hosts(self) -> tuple[str, ...]:
        """Host-identity tokens inspected for ``remote_host`` / ``desktop``."""
        tokens: list[str] = []
        if self.host:
            tokens.append(self.host)
        if self.provider_ref:
            tokens.append(self.provider_ref)
        return tuple(tokens)

    def is_docker_per_worker(self) -> bool:
        """Ordinary worker: docker, ephemeral, no shared dirty filesystem."""
        return (
            self.kind is ExecutionEnvironmentKind.DOCKER
            and self.lifecycle is EnvironmentLifecycle.EPHEMERAL
            and not any(mount.is_shared_dirty() for mount in self.mounts)
        )

    def surface(self) -> Mapping[str, object]:
        """Complete bounded execution surface named by CT-46 / FR-Q48."""
        return {
            "kind": self.kind.value,
            "provider_ref": self.provider_ref,
            "image": self.image,
            "mounts": tuple(
                {
                    "source": mount.source,
                    "target": mount.target,
                    "mode": mount.mode,
                    "shared": mount.shared,
                }
                for mount in self.mounts
            ),
            "environment_allowlist": self.environment_allowlist,
            "capabilities": self.capabilities,
            "network": self.network.value,
            "lifecycle": self.lifecycle.value,
        }

    def capacity(self) -> Mapping[str, object]:
        """Record-homed ``registry:environment.max_in_flight`` view (FR-Q49)."""
        return {
            "max_in_flight": self.max_in_flight,
            "registry_key": ENVIRONMENT_MAX_IN_FLIGHT_KEY,
            "editability": max_in_flight_editability(self.kind).value,
            "pinned_single_slot": is_pinned_single_slot_kind(self.kind),
        }
