"""ExecutionEnvironment port — singleton per ``kind`` (CT-46; AD-1, AD-17).

Declaration shapes used by the AD-28 reachability barrier live here as
definitions. The daemon registry is the only registrar.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from qma.core.vocabulary.enums import ExecutionEnvironmentKind, NetworkPolicy
from qma.core.vocabulary.registry import VocabularyError, parse_closed

__all__ = [
    "ComputerUseProfile",
    "ExecutionEnvironment",
    "ExecutionEnvironmentDeclaration",
    "WorkerImageManifest",
]


@runtime_checkable
class ExecutionEnvironment(Protocol):
    """Definitions-only ExecutionEnvironment seam; one binding per environment kind.

    Cardinality: singleton, scope key ``kind`` (see ``PORT_CONTRACTS``).
    """


def _tuple_of_str(values: Sequence[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(item.strip() for item in values if item.strip())


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


@dataclass(frozen=True, slots=True)
class ExecutionEnvironmentDeclaration:
    """Reachability-bearing ExecutionEnvironment declaration (CT-46; AD-28).

    ``network`` is required and closed to ``none`` | ``allowlist``. ``none``
    enumerates an empty reachable-host set. Host identity for ``remote_host``
    and ``desktop`` is ``host`` or ``provider_ref``.
    """

    kind: ExecutionEnvironmentKind
    network: NetworkPolicy
    reachable_hosts: tuple[str, ...]
    provider_ref: str
    image: str = ""
    host: str = ""
    carries_trading_credential: bool = False
    running_node: bool = False
    image_packages: tuple[str, ...] = ()
    image_imports: tuple[str, ...] = ()
    profile: ComputerUseProfile | None = None

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
        carries_trading_credential: bool = False,
        running_node: bool = False,
        image_packages: Sequence[str] = (),
        image_imports: Sequence[str] = (),
        profile: ComputerUseProfile | None = None,
    ) -> ExecutionEnvironmentDeclaration:
        """Parse closed kind/network; invented values fail as ``VocabularyError``."""
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
        hosts = _tuple_of_str(reachable_hosts)
        return cls(
            kind=resolved_kind,
            network=resolved_network,
            reachable_hosts=hosts,
            provider_ref=provider_ref.strip(),
            image=image.strip(),
            host=host.strip(),
            carries_trading_credential=carries_trading_credential,
            running_node=running_node,
            image_packages=_tuple_of_str(image_packages),
            image_imports=_tuple_of_str(image_imports),
            profile=profile,
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
