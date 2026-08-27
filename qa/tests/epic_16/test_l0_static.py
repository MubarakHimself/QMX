"""Epic 16 — L0 static / structural thin-door gates.

Requirement-derived structural checks over the three door subpackages: thin-door
directive (no identity computation, no cache, no HTTP transport, no store
access), the single console-script surface, the click pin referenced from the
registry key, the three-subpackage tree, and the MCP no-HTTP structure. A
failing assertion is a FINDING, never a licence to edit source.

Tests: T-16.0-thin [R1,R5,R12,R14,R23] · T-16.0-onecli [R3] · T-16.0-pins [R2]
       · T-16.0-tree [R22] · T-16.6-b [R23].
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

import _e16 as e

ROOT = e.ROOT
DOORS_SRC = e.DOORS_SRC
QMB_PYPROJECT = ROOT / "qmb" / "pyproject.toml"
VARIABLES_YAML = ROOT / "docs" / "registry" / "variables.yaml"

# HTTP / transport stacks a thin in-process/CLI/MCP door must never import.
_HTTP_MODULES = frozenset(
    {
        "aiohttp", "django", "fastapi", "flask", "http", "httpx", "requests",
        "socket", "starlette", "urllib", "uvicorn", "mcp", "grpc", "websockets",
    }
)
# Direct data-store libraries a door must never reach (the library owns storage).
_STORE_MODULES = frozenset({"duckdb", "pyarrow", "sqlite3"})
# Identity-computation functions a door must never call (the compiler owns fp1).
_IDENTITY_CALLS = frozenset({"fingerprint", "canonical_bytes", "_fingerprint_of_bytes"})
# Money-path value types whose presence would imply door-side domain arithmetic.
_ARITHMETIC_TYPES = frozenset({"Money", "Price", "Quantity", "Exact"})
_CACHE_DECORATORS = frozenset({"lru_cache", "cache", "cached", "cached_property", "memoize"})


def _door_pyfiles() -> list[Path]:
    return [p for p in sorted(DOORS_SRC.rglob("*.py")) if "__pycache__" not in p.parts]


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def _scan_thin(tree: ast.AST) -> list[str]:
    """Return thin-door violations found in one parsed door module."""
    hits: list[str] = []
    for node in ast.walk(tree):
        # (b) identity computation
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in _IDENTITY_CALLS:
                hits.append(f"identity-call {node.func.id}() @L{node.lineno}")
        # (a) HTTP + store imports; (a') money-path type imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _HTTP_MODULES:
                    hits.append(f"http-import {alias.name} @L{node.lineno}")
                if root in _STORE_MODULES:
                    hits.append(f"store-import {alias.name} @L{node.lineno}")
        if isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in _HTTP_MODULES:
                hits.append(f"http-import {node.module} @L{node.lineno}")
            if root in _STORE_MODULES:
                hits.append(f"store-import {node.module} @L{node.lineno}")
            for alias in node.names:
                if alias.name in _ARITHMETIC_TYPES:
                    hits.append(f"money-type import {alias.name} @L{node.lineno}")
        # (c) cache decorators on any def
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                target = dec.func if isinstance(dec, ast.Call) else dec
                dname = (
                    target.attr if isinstance(target, ast.Attribute)
                    else target.id if isinstance(target, ast.Name)
                    else ""
                )
                if dname in _CACHE_DECORATORS:
                    hits.append(f"cache-decorator @{node.name} @L{node.lineno}")
    return hits


def _scan_module_globals(tree: ast.Module) -> list[str]:
    """Module-global mutable container assignments (door-side cache surface)."""
    hits: list[str] = []
    for node in tree.body:
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        elif isinstance(node, ast.AugAssign):
            name = getattr(node.target, "id", "?")
            if not _is_dunder(str(name)):
                hits.append(f"augmented global {name} @L{node.lineno}")
            continue
        else:
            continue
        names = [t.id for t in targets if isinstance(t, ast.Name)]
        if names and all(_is_dunder(n) for n in names):
            continue
        if value is None:
            continue
        if isinstance(value, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)):
            hits.append(f"mutable literal -> {','.join(names) or '?'} @L{node.lineno}")
        elif (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id in {"list", "dict", "set", "bytearray"}
        ):
            hits.append(f"mutable ctor {value.func.id}() -> {','.join(names) or '?'} @L{node.lineno}")
    return hits


# --- T-16.0-thin -------------------------------------------------------------
def test_t16_0_thin_no_logic_no_cache_no_identity_no_http() -> None:
    """doors/{cli,api,mcp} carry only adaptation: no fp1/run-id computation, no
    door-side cache, no HTTP transport, no direct store access, no money-path
    arithmetic types. The library decides; the door translates. [R1,R5,R12,R14,R23]
    """
    offenders: list[str] = []
    for path in _door_pyfiles():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        rel = path.relative_to(ROOT)
        offenders += [f"{rel}: {h}" for h in _scan_thin(tree)]
        offenders += [f"{rel}: {h}" for h in _scan_module_globals(tree)]
    assert offenders == [], "thin-door violations: " + "; ".join(offenders)


def test_t16_0_thin_scanner_has_teeth() -> None:
    """Falsifiability guard: the thin scanner FLAGS an injected violation (proving
    the green result above is not vacuous). The violation is injected into a
    TEST-OWNED source string — never into door source."""
    bad = (
        "from qmf.core.fingerprint import fingerprint\n"
        "import requests\n"
        "from qmf.core.exact import Money\n"
        "def x():\n"
        "    return fingerprint({'a': 1})\n"
    )
    tree = ast.parse(bad)
    hits = _scan_thin(tree)
    joined = " ".join(hits)
    assert any("identity-call fingerprint" in h for h in hits), joined
    assert any("http-import requests" in h for h in hits), joined
    assert any("money-type import Money" in h for h in hits), joined
    cache_src = "import functools\n@functools.lru_cache\ndef y():\n    return 1\n"
    assert any("cache-decorator" in h for h in _scan_thin(ast.parse(cache_src)))
    mut = ast.parse("_CACHE = {}\n_SECOND = list()\n")
    mods = _scan_module_globals(mut)
    assert any("mutable literal" in h for h in mods) and any("mutable ctor" in h for h in mods)


# --- T-16.0-onecli -----------------------------------------------------------
def test_t16_0_onecli_single_console_script_surface() -> None:
    """Exactly one console-script — the qmb CLI over the library. No second/
    sibling command-line surface anywhere (DEC-0185). [R3]"""
    with QMB_PYPROJECT.open("rb") as fh:
        manifest = tomllib.load(fh)
    scripts = manifest["project"].get("scripts", {})
    assert scripts == {"qmb": "qmb.doors.cli:main"}, scripts
    entry = manifest["project"].get("entry-points", {})
    assert "console_scripts" not in entry, entry
    # No door module registers a second click entry group named as a program.
    from qmb.doors.cli import main
    import click

    assert isinstance(main, click.Group)
    assert main.name == "qmb"


# --- T-16.0-pins -------------------------------------------------------------
def test_t16_0_pins_click_pinned_at_registry_key_value() -> None:
    """click is pinned at exactly the ``qmb_cli_pin`` registry value — referenced
    from the registry key, never a restated literal. [R2]"""
    text = VARIABLES_YAML.read_text(encoding="utf-8")
    # Locate the qmb_cli_pin registry row and read its declared value.
    block = re.search(r"name:\s*qmb_cli_pin(.*?)(?:\n  - name:|\Z)", text, re.DOTALL)
    assert block is not None, "qmb_cli_pin key not found in the registry"
    value_m = re.search(r"value:\s*(\S+)", block.group(1))
    configurable_m = re.search(r"configurable:\s*(\S+)", block.group(1))
    assert value_m is not None, "qmb_cli_pin has no value"
    registry_pin = value_m.group(1).strip()
    assert configurable_m is not None and configurable_m.group(1).strip() == "false"
    with QMB_PYPROJECT.open("rb") as fh:
        deps = tomllib.load(fh)["project"]["dependencies"]
    click_specs = [d for d in deps if d.split("=", 1)[0].split(">", 1)[0].strip() == "click"]
    assert click_specs == [registry_pin], (click_specs, registry_pin)


# --- T-16.0-tree -------------------------------------------------------------
def test_t16_0_tree_three_door_subpackages_present() -> None:
    """doors/ contains the three door subpackages cli, api, mcp, each a package. [R22]"""
    for sub in ("cli", "api", "mcp"):
        pkg = DOORS_SRC / sub
        assert (pkg / "__init__.py").is_file(), f"missing door subpackage: {sub}"


# --- T-16.6-b ----------------------------------------------------------------
def test_t16_6_b_mcp_door_imports_no_http_stack() -> None:
    """The MCP door is a sibling over the same library and imports no HTTP-server
    / transport stack — never stacked over HTTP (runtime binding deferred). [R23]"""
    offenders: list[str] = []
    imported: list[str] = []
    for path in sorted((DOORS_SRC / "mcp").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
    for name in imported:
        root = name.split(".")[0]
        if root in _HTTP_MODULES:
            offenders.append(name)
    assert offenders == [], f"MCP door imports HTTP/transport stack: {offenders}"
    # The scaffold imports the library (qmb) — a sibling over the same library.
    assert any(n.startswith("qmb") for n in imported)
