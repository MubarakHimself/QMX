"""Localhost HTTP evidence channel — publish-never-act (TN-17 / DEC-0202).

Stdlib-shaped request handling over loopback. Authority-free beyond the bind;
refusals return as evidence on the wire. Budgeted by
``registry:evidence_channel_budget`` (unit: request-count-per-boot-epoch).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Final

from qmf.core.refusal import Result, is_refusal

from qmn.doors._refuse import invalid, policy
from qmn.doors.library import (
    DoorRuntime,
    read_config_explanation,
    read_failure_detail,
    read_health,
    read_metrics,
    read_projections,
    read_status,
)
from qmn.doors.wire import WIRE_FORMAT_VERSION, refusal_wire_shape

__all__ = [
    "EVIDENCE_BIND_HOST",
    "EVIDENCE_DOOR",
    "EVIDENCE_ROUTES",
    "evidence_capability_surface",
    "evidence_door_name",
    "evidence_identity",
    "handle_evidence_request",
    "render_evidence_http",
]

EVIDENCE_DOOR: Final[str] = "evidence_http"
EVIDENCE_BIND_HOST: Final[str] = "127.0.0.1"
_HTTP_GET: Final[str] = "GET"

# Route → library callable. This table IS the evidence door surface (derived parity).
EVIDENCE_ROUTES: Final[Mapping[str, Callable[..., Result[Mapping[str, object]]]]] = (
    MappingProxyType(
        {
            "/status": read_status,
            "/health": read_health,
            "/projections": read_projections,
            "/config/explain": read_config_explanation,
            "/metrics": read_metrics,
        }
    )
)


def evidence_door_name() -> str:
    return EVIDENCE_DOOR


def evidence_capability_surface() -> frozenset[str]:
    """Library names the evidence HTTP door adapts — derived from routes."""
    names = {fn.__name__ for fn in EVIDENCE_ROUTES.values()}
    names.add(read_failure_detail.__name__)
    return frozenset(names)


def evidence_identity() -> Mapping[str, object]:
    return MappingProxyType(
        {
            "door": EVIDENCE_DOOR,
            "bind_host": EVIDENCE_BIND_HOST,
            "publishes": True,
            "acts": False,
            "authentication": "loopback-only",
            "routes": tuple(sorted(EVIDENCE_ROUTES)),
            "wire_format_version": WIRE_FORMAT_VERSION,
        }
    )


def handle_evidence_request(
    runtime: object,
    *,
    method: object,
    path: object,
) -> Result[Mapping[str, object]]:
    """Dispatch one evidence request to the shared library (parity surface).

    Only ``GET`` publishes. Mutations are refused — the channel never acts.
    Library refusals are returned as ``TypedRefusal`` values (same shape as the
    Python API); ``render_evidence_http`` places them on the wire as evidence.
    """
    if not isinstance(runtime, DoorRuntime):
        return invalid(
            "runtime",
            "evidence channel requires a DoorRuntime",
            given=type(runtime).__name__,
        )
    method_token = method.strip().upper() if isinstance(method, str) else None
    if method_token is None:
        return invalid("method", "evidence request names an HTTP method")
    if method_token != _HTTP_GET:
        return policy(
            "method",
            "evidence channel is publish-never-act; only GET is served",
            method=method_token,
            acts=False,
        )
    path_token = path.strip() if isinstance(path, str) else None
    if path_token is None or path_token == "":
        return invalid("path", "evidence request names a path")

    if path_token.startswith("/failures/"):
        failure_id = path_token.removeprefix("/failures/")
        return read_failure_detail(runtime, failure_id)

    handler = EVIDENCE_ROUTES.get(path_token)
    if handler is None:
        return invalid(
            "path",
            "evidence channel has no route for this path",
            path=path_token,
            routes=tuple(sorted(EVIDENCE_ROUTES)),
        )
    return handler(runtime)


def render_evidence_http(
    result: Result[Mapping[str, object]],
) -> Mapping[str, object]:
    """Transport rendering: values and refusals become JSON evidence bodies.

    ``/metrics`` carries Prometheus text in ``exposition`` with
    ``http_content_type`` so a scraper reads the existing evidence listener
    without a library-spawned server thread.
    """
    if is_refusal(result):
        return MappingProxyType(
            {
                **dict(refusal_wire_shape(result)),
                "publishes": True,
                "acts": False,
                "as_evidence": True,
                "http_status": 422,
            }
        )
    body: dict[str, object] = dict(result.value)
    body.setdefault("http_status", 200)
    if body.get("capability") == "read_metrics" and "exposition" in body:
        content_type = body.get("content_type")
        if isinstance(content_type, str) and content_type:
            body["http_content_type"] = content_type
        body["http_body"] = body["exposition"]
        body["scrape_format"] = "prometheus"
    return MappingProxyType(body)
