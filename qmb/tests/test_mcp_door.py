"""Story 16.6 — MCP door is an unshipped localhost sibling (SC-08, B-1, AR-58)."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import tomllib
from qmb.doors import MCP_IN_DOOR_SET, MCP_SHIPPED, SHIPPED_DOORS
from qmb.doors.cli.render import render_refusal
from qmb.doors.mcp import (
    BIND_HOST,
    COMPUTES_RUN_ID,
    HOLDS_CACHE,
    LIBRARY,
    LOCALHOST_BOUND,
    POST_CLI_V1,
    SHIPPED,
    STACKED_OVER_HTTP,
    TRANSPORT,
    WRAPPER,
    error_data,
    is_shipped,
    main,
    mcp_door_identity,
    render_error,
    serve,
)
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal, is_refusal

import qmb

_QMB_ROOT = Path(__file__).resolve().parents[1]
_MCP_SRC = _QMB_ROOT / "src" / "qmb" / "doors" / "mcp"
_HTTP_MODULES = frozenset(
    {
        "aiohttp",
        "django",
        "fastapi",
        "flask",
        "http",
        "httpx",
        "requests",
        "socket",
        "starlette",
        "urllib",
        "uvicorn",
    }
)
_HTTP_DEPENDENCIES = frozenset(
    {
        "aiohttp",
        "django",
        "fastapi",
        "flask",
        "httpx",
        "mcp",
        "requests",
        "starlette",
        "uvicorn",
    }
)


def test_is_shipped_is_false() -> None:
    assert is_shipped() is False
    assert SHIPPED is False
    assert MCP_SHIPPED is False
    assert POST_CLI_V1 is True
    assert qmb.MCP_SHIPPED is False


def test_invocation_is_typed_unsupported_capability() -> None:
    refused = main()
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refused.retryability is Retryability.NO
    assert refused.context["field"] == "door"
    served = serve()
    assert is_refusal(served)
    assert served == refused
    assert served.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_sibling_over_the_same_library_never_http_localhost_bound() -> None:
    identity = mcp_door_identity()
    assert WRAPPER == "sibling"
    assert LIBRARY == "qmb"
    assert STACKED_OVER_HTTP is False
    assert LOCALHOST_BOUND is True
    assert BIND_HOST == "127.0.0.1"
    assert TRANSPORT == "mcp"
    assert HOLDS_CACHE is False
    assert COMPUTES_RUN_ID is False
    assert identity["wrapper"] == "sibling"
    assert identity["library"] == "qmb"
    assert identity["stacked_over_http"] is False
    assert identity["localhost_bound"] is True
    assert identity["bind_host"] == "127.0.0.1"
    assert identity["shipped"] is False
    assert identity["post_cli_v1"] is True
    assert identity["in_door_set"] is False
    assert identity["transport"] == "mcp"
    assert qmb.__version__ not in identity.values()


def test_error_data_carries_the_refusal_union_verbatim() -> None:
    refused = main()
    assert is_refusal(refused)
    payload = error_data(refused)
    assert payload == json.loads(render_refusal(refused))
    assert payload["category"] == RefusalCategory.UNSUPPORTED_CAPABILITY.value
    assert payload["retryability"] == Retryability.NO.value
    assert "context" in payload
    error = render_error(refused)
    assert error["data"] == payload
    later = TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context={"field": "prerequisites", "missing": ["port"]},
    )
    later_data = error_data(later)
    assert later_data == json.loads(render_refusal(later))
    assert render_error(later)["data"] == later_data


def test_error_data_includes_after_condition_descriptor() -> None:
    refusal = TypedRefusal(
        category=RefusalCategory.TRANSIENT_VENUE_FAILURE,
        retryability=Retryability.AFTER_CONDITION,
        context={"source": "probe"},
        after_condition_descriptor="retry after 2s",
    )
    payload = error_data(refusal)
    assert payload["after_condition_descriptor"] == "retry after 2s"
    assert payload == json.loads(render_refusal(refusal))
    empty = TypedRefusal(RefusalCategory.POLICY_REJECTION, Retryability.NO)
    empty_data = error_data(empty)
    assert empty_data["context"] == {}
    assert empty_data["context"] is not None
    assert "after_condition_descriptor" not in empty_data


def test_cli_v1_is_not_gated_by_mcp() -> None:
    data = tomllib.loads((_QMB_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project["scripts"] == {"qmb": "qmb.doors.cli:main"}
    scripts = project.get("scripts", {})
    assert all("mcp" not in name for name in scripts)
    entry = project.get("entry-points", {})
    assert "console_scripts" not in entry or "mcp" not in str(entry)
    deps = tuple(str(item) for item in project["dependencies"])
    for dep in deps:
        token = dep.split("=", 1)[0].split(">", 1)[0].split("<", 1)[0].strip().casefold()
        assert token not in _HTTP_DEPENDENCIES
        assert token != "mcp"
    assert SHIPPED_DOORS == ("cli", "api")
    assert MCP_IN_DOOR_SET is False
    assert "mcp" not in qmb.__all__


def test_mcp_door_source_is_not_stacked_over_http() -> None:
    imported: list[str] = []
    offenders: list[str] = []
    for path in sorted(_MCP_SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            if isinstance(node, ast.Raise) and node.exc is not None:
                target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
                name: str | None = None
                if isinstance(target, ast.Name):
                    name = target.id
                elif isinstance(target, ast.Attribute):
                    name = target.attr
                if name == "TypedRefusal":
                    offenders.append(f"{path.name}: raise TypedRefusal")
    for name in imported:
        root = name.split(".", 1)[0]
        if name in _HTTP_MODULES or root in _HTTP_MODULES:
            offenders.append(f"imports {name}")
    assert "click" not in imported
    assert "qmf.venue" not in imported
    assert "mcp" not in imported
    assert offenders == []
