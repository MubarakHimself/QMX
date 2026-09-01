"""Daemon wire listener bind posture (CT-40; AD-5, AD-24; FR-Q17).

Default bind is loopback. A non-loopback bind requires TLS (``wss://`` plus
HTTPS queries) AND an explicit recorded operator configuration. An
unauthenticated bind, or a plaintext non-loopback bind, is a hard startup
refusal — never a warning, fallback listener, or implicit external config.
"""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
from typing import Final, Literal

from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "DEFAULT_BIND_HOST",
    "ListenerBindConfig",
    "ListenerPosture",
    "is_loopback_host",
    "validate_listener_startup",
]


DEFAULT_BIND_HOST: Final[str] = "127.0.0.1"

_LOOPBACK_NAMES: Final[frozenset[str]] = frozenset(
    {"localhost", "127.0.0.1", "::1", "0:0:0:0:0:0:0:1"}
)


def _startup(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Hard startup refusal — process must not proceed (DEC-0304, DEC-0323)."""
    context: dict[str, object] = {"field": field, "reason": reason, "startup": True}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def is_loopback_host(host: object) -> bool:
    """True when ``host`` is a loopback name or address."""
    if not isinstance(host, str) or host.strip() == "":
        return False
    normalized = host.strip().lower().strip("[]")
    if normalized in _LOOPBACK_NAMES:
        return True
    try:
        return bool(ip_address(normalized).is_loopback)
    except ValueError:
        return False


@dataclass(frozen=True, slots=True)
class ListenerBindConfig:
    """Declared listener posture presented at daemon startup validation.

    ``host`` omitted or empty defaults to loopback. ``operator_recorded_config``
    is true only when an explicit operator-recorded non-default bind exists —
    never implied by environment defaults.
    """

    host: str = DEFAULT_BIND_HOST
    websocket_scheme: Literal["ws", "wss"] = "ws"
    query_scheme: Literal["http", "https"] = "http"
    require_authentication: bool = True
    operator_recorded_config: bool = False

    @classmethod
    def try_create(
        cls,
        *,
        host: object = None,
        websocket_scheme: object = "ws",
        query_scheme: object = "http",
        require_authentication: object = True,
        operator_recorded_config: object = False,
    ) -> Result[ListenerBindConfig]:
        if host is None:
            resolved_host = DEFAULT_BIND_HOST
        elif isinstance(host, str) and host.strip() != "":
            resolved_host = host.strip()
        else:
            return _startup(
                "host",
                "listener host must be a non-empty string when supplied",
                given=repr(host),
            )
        if websocket_scheme not in ("ws", "wss"):
            return _startup(
                "websocket_scheme",
                "websocket scheme must be 'ws' or 'wss'",
                given=repr(websocket_scheme),
            )
        if query_scheme not in ("http", "https"):
            return _startup(
                "query_scheme",
                "query scheme must be 'http' or 'https'",
                given=repr(query_scheme),
            )
        if not isinstance(require_authentication, bool):
            return _startup(
                "require_authentication",
                "require_authentication must be a bool",
                given=repr(require_authentication),
            )
        if not isinstance(operator_recorded_config, bool):
            return _startup(
                "operator_recorded_config",
                "operator_recorded_config must be a bool",
                given=repr(operator_recorded_config),
            )
        return Ok(
            cls(
                host=resolved_host,
                websocket_scheme=websocket_scheme,  # type: ignore[arg-type]
                query_scheme=query_scheme,  # type: ignore[arg-type]
                require_authentication=require_authentication,
                operator_recorded_config=operator_recorded_config,
            )
        )


@dataclass(frozen=True, slots=True)
class ListenerPosture:
    """Validated startup posture — safe to bind."""

    host: str
    loopback: bool
    websocket_url_prefix: str
    query_url_prefix: str
    authentication_required: bool
    operator_recorded_config: bool


def validate_listener_startup(config: object) -> Result[ListenerPosture]:
    """Validate listener bind posture at startup.

    Hard-refuses plaintext non-loopback and unauthenticated binds. Never warns,
    never falls back to an implicit external listener.
    """
    if not isinstance(config, ListenerBindConfig):
        return _startup(
            "listener",
            "validate_listener_startup requires ListenerBindConfig",
            given=repr(config),
        )

    loopback = is_loopback_host(config.host)

    if not config.require_authentication:
        return _startup(
            "require_authentication",
            "unauthenticated bind is a hard startup refusal",
            host=config.host,
            loopback=loopback,
        )

    if not loopback:
        plaintext = config.websocket_scheme != "wss" or config.query_scheme != "https"
        if plaintext:
            return _startup(
                "transport",
                "plaintext non-loopback bind is a hard startup refusal; "
                "non-loopback requires wss:// plus HTTPS queries",
                host=config.host,
                websocket_scheme=config.websocket_scheme,
                query_scheme=config.query_scheme,
            )
        if not config.operator_recorded_config:
            return _startup(
                "operator_recorded_config",
                "non-loopback bind requires an explicit recorded operator configuration",
                host=config.host,
            )

    return Ok(
        ListenerPosture(
            host=config.host,
            loopback=loopback,
            websocket_url_prefix=f"{config.websocket_scheme}://",
            query_url_prefix=f"{config.query_scheme}://",
            authentication_required=True,
            operator_recorded_config=config.operator_recorded_config,
        )
    )
