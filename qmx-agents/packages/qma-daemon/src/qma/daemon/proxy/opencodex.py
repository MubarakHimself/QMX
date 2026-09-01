"""OpenCodex — first ModelDeployment, behind the Deployment contract (FR-Q40).

OpenCodex sits deliberately NOT behind the Credential Broker. QMA passes it no
credential (``auth_mode: none``); the proxy's own provider credentials remain
outside QMA's namespace. Each proxy target is one logical Deployment; QMA does
not pool, rotate, or masquerade accounts.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final

from qma.core.ports.model import (
    AUTH_MODE_NONE,
    OPENCODEX_ADAPTER,
    DeploymentRecord,
    ModelCapabilities,
    ModelClassRequest,
    capabilities_for,
)
from qma.core.vocabulary.enums import ModelClass
from qma.daemon.proxy.local_proxy import format_bind_address
from qmf.core import Ok, Result
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "OPENCODEX_ADAPTER",
    "OpenCodexDeployment",
    "OpenCodexCallResult",
    "build_opencodex_deployment_record",
]

_DEFAULT_LOOPBACK: Final[str] = "127.0.0.1"
_DEFAULT_PORT: Final[int] = 3921


@dataclass(frozen=True, slots=True)
class OpenCodexCallResult:
    """Result of a loopback OpenCodex call — never carries a resolved secret."""

    deployment_id: str
    bind_address: str
    model_class: ModelClass
    content: str
    auth_mode: str = AUTH_MODE_NONE
    credential_crossed: bool = False

    def to_wire(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "deployment_id": self.deployment_id,
                "bind_address": self.bind_address,
                "model_class": self.model_class.value,
                "content": self.content,
                "auth_mode": self.auth_mode,
                "credential_crossed": self.credential_crossed,
            }
        )


def build_opencodex_deployment_record(
    deployment_id: str,
    model_class: ModelClass,
    *,
    bind_host: str = _DEFAULT_LOOPBACK,
    bind_port: int = _DEFAULT_PORT,
    accepts_unauthenticated: bool = True,
    context_tokens: int = 128_000,
    supports_tools: bool = True,
    supports_vision: bool = False,
    supports_reasoning_effort: bool = False,
    supports_parallel_tool_calls: bool = True,
    weight: int = 1,
) -> DeploymentRecord:
    """Build an OpenCodex local-proxy Deployment row (auth_mode none, loopback)."""
    return DeploymentRecord(
        deployment_id=deployment_id,
        model_class=model_class,
        adapter=OPENCODEX_ADAPTER,
        auth_mode=AUTH_MODE_NONE,
        bind_host=bind_host,
        bind_port=bind_port,
        accepts_unauthenticated=accepts_unauthenticated,
        context_tokens=context_tokens,
        supports_tools=supports_tools,
        supports_vision=supports_vision,
        supports_reasoning_effort=supports_reasoning_effort,
        supports_parallel_tool_calls=supports_parallel_tool_calls,
        weight=weight,
        credential_ref=None,
        model_family=None,
    )


@dataclass
class OpenCodexDeployment:
    """First ModelDeployment implementation — behind Deployment, not Broker.

    The daemon talks to the verified loopback bind only. No QMA-resolved secret
    is accepted or forwarded. Pooling stays inside the operator's own proxy.
    """

    record: DeploymentRecord
    _handler: Any = None

    def __post_init__(self) -> None:
        if self.record.adapter != OPENCODEX_ADAPTER:
            raise ValueError(
                f"OpenCodexDeployment requires adapter={OPENCODEX_ADAPTER!r}; "
                f"got {self.record.adapter!r}"
            )
        if self.record.auth_mode != AUTH_MODE_NONE:
            raise ValueError("OpenCodexDeployment requires auth_mode: none (FR-Q40)")
        if self.record.credential_ref is not None:
            raise ValueError(
                "OpenCodexDeployment must not carry a QMA credential_ref (FR-Q40)"
            )

    @property
    def deployment_id(self) -> str:
        return self.record.deployment_id

    @property
    def behind_credential_broker(self) -> bool:
        """OpenCodex is deliberately not behind the Credential Broker."""
        return False

    @property
    def capabilities(self) -> ModelCapabilities:
        return capabilities_for(self.record)

    def call(
        self,
        request: ModelClassRequest,
        *,
        prompt: str,
        resolved_secret: object = None,
    ) -> Result[OpenCodexCallResult]:
        """Invoke the loopback proxy without any QMA-resolved secret."""
        if resolved_secret is not None:
            return policy_rejection(
                "resolved_secret",
                "no QMA-resolved secret may cross into an OpenCodex local-proxy "
                "process (auth_mode: none; CT-45; AD-15)",
                deployment_id=self.record.deployment_id,
            )
        if request.model_class is not self.record.model_class:
            return invalid_input(
                "model_class",
                "OpenCodex call must match the Deployment's registered ModelClass",
                given=request.model_class.value,
                deployment_id=self.record.deployment_id,
            )
        host = self.record.bind_host or _DEFAULT_LOOPBACK
        port = self.record.bind_port
        bind = format_bind_address(host, port)
        if self._handler is not None:
            content = str(self._handler(prompt=prompt, bind=bind, request=request))
        else:
            content = f"opencodex:{self.record.deployment_id}:{prompt}"
        return Ok(
            OpenCodexCallResult(
                deployment_id=self.record.deployment_id,
                bind_address=bind,
                model_class=self.record.model_class,
                content=content,
                auth_mode=AUTH_MODE_NONE,
                credential_crossed=False,
            )
        )
