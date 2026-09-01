"""Local-proxy Deployment custody validation (CT-45; AD-15; FR-Q40).

A local-proxy Deployment (OpenCodex first) is permitted only on a verified
loopback bind with ``auth_mode: none``. No QMA-resolved secret crosses into the
proxy process; provider credentials remain the proxy's own custody.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qma.core.ports.model import (
    AUTH_MODE_NONE,
    PROXY_ALLOW_UNAUTHENTICATED_LOOPBACK_KEY,
    DeploymentRecord,
    is_local_proxy_deployment,
)
from qma.core.refusals import NonLoopbackProxy, UnauthenticatedProxy
from qma.wire.listener import is_loopback_host
from qmf.core import Ok, Result
from qmf.data.store.refusals import invalid_input

__all__ = [
    "ALLOW_UNAUTHENTICATED_LOOPBACK_DEFAULT",
    "LocalProxyStartupEvidence",
    "format_bind_address",
    "record_local_proxy_startup_evidence",
    "validate_local_proxy_registration",
]

ALLOW_UNAUTHENTICATED_LOOPBACK_DEFAULT: Final[bool] = True


def format_bind_address(host: str, port: int | None) -> str:
    """Render ``host`` or ``host:port`` for refusal context."""
    if port is None:
        return host
    if ":" in host and not host.startswith("["):
        return f"[{host}]:{port}"
    return f"{host}:{port}"


def validate_local_proxy_registration(
    record: DeploymentRecord,
    *,
    allow_unauthenticated_loopback: bool = ALLOW_UNAUTHENTICATED_LOOPBACK_DEFAULT,
) -> Result[DeploymentRecord]:
    """Validate local-proxy bind and custody at registration (FR-Q40).

    Non-local-proxy records pass through unchanged. Local-proxy records must
    carry ``auth_mode: none``, a loopback ``bind_host``, and no
    ``credential_ref``. An unauthenticated loopback proxy is refused with
    ``UnauthenticatedProxy`` when the registry variable disallows it.
    """
    if not is_local_proxy_deployment(record):
        return Ok(record)

    if record.auth_mode != AUTH_MODE_NONE:
        return invalid_input(
            "auth_mode",
            "local-proxy Deployments require auth_mode: none; "
            "no QMA-resolved secret crosses into the proxy (CT-45; AD-15)",
            given=repr(record.auth_mode),
            deployment_id=record.deployment_id,
        )

    if record.credential_ref is not None:
        return invalid_input(
            "credential_ref",
            "local-proxy Deployments carry no QMA credential_ref; "
            "provider credentials stay outside QMA's namespace (CT-45; AD-15)",
            given=record.credential_ref,
            deployment_id=record.deployment_id,
        )

    host = record.bind_host
    if host is None or str(host).strip() == "":
        return NonLoopbackProxy.of(address="<missing>")

    if not is_loopback_host(host):
        return NonLoopbackProxy.of(address=format_bind_address(host, record.bind_port))

    if record.accepts_unauthenticated and not allow_unauthenticated_loopback:
        return UnauthenticatedProxy.of(deployment_id=record.deployment_id)

    return Ok(record)


@dataclass(frozen=True, slots=True)
class LocalProxyStartupEvidence:
    """Startup evidence naming each proxy Deployment and the loopback setting."""

    proxy_deployment_ids: tuple[str, ...]
    allow_unauthenticated_loopback: bool
    allow_unauthenticated_loopback_key: str = PROXY_ALLOW_UNAUTHENTICATED_LOOPBACK_KEY

    def to_dict(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "proxy_deployments": list(self.proxy_deployment_ids),
                "allow_unauthenticated_loopback": self.allow_unauthenticated_loopback,
                "allow_unauthenticated_loopback_key": self.allow_unauthenticated_loopback_key,
            }
        )


def record_local_proxy_startup_evidence(
    catalog: Sequence[DeploymentRecord],
    *,
    allow_unauthenticated_loopback: bool,
) -> LocalProxyStartupEvidence:
    """Record each registered local-proxy Deployment and the registry setting."""
    proxy_ids = tuple(
        entry.deployment_id for entry in catalog if is_local_proxy_deployment(entry)
    )
    return LocalProxyStartupEvidence(
        proxy_deployment_ids=proxy_ids,
        allow_unauthenticated_loopback=allow_unauthenticated_loopback,
    )
