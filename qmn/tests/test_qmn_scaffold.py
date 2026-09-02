"""Tier-1 scaffold gates for the qmn distribution (Stories 24.1 and 25.1)."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import tomllib
from qmn.bench import BENCH_SURFACE
from qmn.data import DATA_SURFACE
from qmn.ledger import LEDGER_SURFACE
from qmn.mis import MIS_SURFACE
from qmn.observability import OBSERVABILITY_SURFACE
from qmn.paper import PAPER_SURFACE
from qmn.promotion import PROMOTION_SURFACE
from qmn.protection import PROTECTION_SURFACE
from qmn.reconcile import RECONCILE_SURFACE
from qmn.replay import REPLAY_SURFACE
from qmn.seats import SEATS_SURFACE
from qmn.secrets import SECRETS_SURFACE

import qmn
from qmn import config, doors, host, seed, time

_QMN_ROOT = Path(__file__).resolve().parents[1]
_SRC = _QMN_ROOT / "src" / "qmn"
_VENUE = _SRC / "venue"
_DEPLOY = _QMN_ROOT / "deploy"
_WORKSPACE_ROOT = _QMN_ROOT.parent
_MAX_SOURCE_BYTES = 1 << 20  # 1 MiB


def _load_deploy_boundary():
    path = _DEPLOY / "boundary.py"
    spec = importlib.util.spec_from_file_location("qmn_deploy_boundary", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_version_is_display_only_semver_0x() -> None:
    assert qmn.__version__ == "0.1.0"


def test_no_console_scripts() -> None:
    data = tomllib.loads((_QMN_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})
    assert not project.get("scripts"), "qmn ships no operator CLI entry point"
    entry = project.get("entry-points", {})
    assert "console_scripts" not in entry


def test_no_publishable_index_target() -> None:
    data = tomllib.loads((_QMN_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})
    assert "urls" not in project or "Homepage" not in project.get("urls", {})
    # No tool that marks a PyPI publish target.
    assert "poetry" not in data.get("tool", {})
    assert data.get("project", {}).get("classifiers") is None or not any(
        "Distribution" in c for c in project.get("classifiers", [])
    )


def test_declared_dependencies_include_qmf_venue_and_qmb() -> None:
    data = tomllib.loads((_QMN_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = set(data["project"]["dependencies"])
    assert "qmf-core" in deps
    assert "qmf-data" in deps
    assert "qmf-risk" in deps
    assert "qmf-venue" in deps
    assert "qmb" in deps
    assert "qml" in deps
    assert "prometheus-client==0.26.0" in deps
    assert "cryptography==50.0.1" in deps


def test_only_venue_subpackage_imports_qmf_venue() -> None:
    violations: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        relative = path.relative_to(_SRC)
        under_venue = relative.parts and relative.parts[0] == "venue"
        for imported in _imported_modules(path):
            is_venue = imported == "qmf.venue" or imported.startswith("qmf.venue.")
            if is_venue and not under_venue:
                violations.append(f"{relative}: imports {imported}")
    assert violations == [], f"qmf.venue imports outside qmn.venue: {violations}"


def test_venue_subpackage_does_import_qmf_venue() -> None:
    imported: set[str] = set()
    for path in sorted(_VENUE.rglob("*.py")):
        imported |= _imported_modules(path)
    assert any(name == "qmf.venue" or name.startswith("qmf.venue.") for name in imported)


def test_no_spotware_or_twisted_imports() -> None:
    banned = ("twisted", "ctrader_open_api", "openapi_client", "spotware")
    violations: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        for imported in _imported_modules(path):
            root = imported.split(".", 1)[0].lower()
            if root in banned or any(token in imported.lower() for token in banned):
                violations.append(f"{path.relative_to(_SRC)}: {imported}")
    assert violations == [], f"banned SDK imports: {violations}"


def test_feat_0031_structural_seed_packages_exist() -> None:
    for name in seed.structural_seed_packages():
        path = _SRC / name
        assert path.is_dir(), f"missing structural seed package: {name}"
        assert (path / "__init__.py").is_file(), f"missing __init__.py for {name}"


def test_composition_config_doors_time_surfaces() -> None:
    assert host.COMPOSITION_ROOT_SURFACE == "qmn.host"
    assert host.REGISTRY_MINT_SURFACE == "qmn.host"
    assert host.BOOT_CEREMONY_SURFACE == "qmn.host"
    assert host.DOOR_LOCAL_REGISTRY_CACHE is False
    assert host.HAS_ALTERNATE_IDENTITY_FUNCTION is False
    assert host.HAS_OPERATOR_CLI is False
    assert len(host.COMPOSE_RECORD_KINDS) == 7
    assert host.ceremony_steps() == ("preflight", "compose", "fingerprint", "seal")
    assert host.BOOT_BOUND_SURFACES == (
        "evidence_channel",
        "preflight_status",
        "resurrect_power",
    )
    assert host.CHECK_MODE_OPENS_SEQUENCER is False
    assert host.SealedComposition().sealed is True
    assert config.CONFIG_SURFACE == "qmn.config"
    assert config.HAS_INVOCATION_OVERRIDE_LAYER is False
    assert config.compile_layers() == ("roster", "bms", "book", "node_defaults")
    assert doors.HAS_OPERATOR_CLI_DOOR is False
    assert doors.shipped_doors() == ("python_api", "evidence_http", "powers_unix")
    assert not (_SRC / "doors" / "cli").exists()
    assert time.calendar_identities() == (
        "market_hours_calendar",
        "day_boundary_calendar",
        "news_calendar",
    )


def test_remaining_seed_surface_markers() -> None:
    assert PROTECTION_SURFACE == "qmn.protection"
    assert LEDGER_SURFACE == "qmn.ledger"
    assert PAPER_SURFACE == "qmn.paper"
    assert RECONCILE_SURFACE == "qmn.reconcile"
    assert SEATS_SURFACE == "qmn.seats"
    assert PROMOTION_SURFACE == "qmn.promotion"
    assert MIS_SURFACE == "qmn.mis"
    assert DATA_SURFACE == "qmn.data"
    assert SECRETS_SURFACE == "qmn.secrets"
    assert OBSERVABILITY_SURFACE == "qmn.observability"
    assert REPLAY_SURFACE == "qmn.replay"
    assert BENCH_SURFACE == "qmn.bench"


def test_deploy_ops_toolkit_boundary() -> None:
    assert _DEPLOY.is_dir()
    for name in seed.DEPLOY_SEED_DIRS:
        assert (_DEPLOY / name).is_dir(), f"missing deploy seed dir: {name}"
    boundary = _load_deploy_boundary()
    assert boundary.OPS_TOOLKIT_SURFACE == "qmn.deploy"
    assert boundary.toolkit_principal() == "ops"
    assert boundary.OPS_PRINCIPAL_NAME == "ops"
    assert "node-install" in boundary.ALLOWED_NODE_RECIPES
    assert "node-config-validate" in boundary.ALLOWED_NODE_RECIPES
    for action in (
        "place",
        "cancel",
        "amend",
        "flatten",
        "promote",
        "activate",
        "settings",
        "resurrect",
        "attestation",
        "countersign",
    ):
        assert boundary.recipe_action_allowed(action) is False
    assert boundary.deploy_may_import("qmn.host") is False
    assert boundary.deploy_may_import("qmn.doors.api") is False
    assert boundary.deploy_may_import("pathlib") is True


def test_deploy_tree_never_imports_composition_or_api() -> None:
    violations: list[str] = []
    for path in sorted(_DEPLOY.rglob("*.py")):
        for imported in _imported_modules(path):
            if imported == "qmn" or imported.startswith("qmn."):
                # boundary.py is stdlib-only; any qmn.* import is forbidden here.
                violations.append(f"{path.relative_to(_DEPLOY)}: imports {imported}")
    assert violations == [], f"deploy imports composition/API surface: {violations}"


def test_nothing_outside_qmn_imports_qmn() -> None:
    """Nothing in the workspace imports qmn (AR-73)."""
    scan_roots = (
        _WORKSPACE_ROOT / "packages",
        _WORKSPACE_ROOT / "extensions",
        _WORKSPACE_ROOT / "qml",
        _WORKSPACE_ROOT / "qmb",
        _WORKSPACE_ROOT / "tools",
    )
    violations: list[str] = []
    for root in scan_roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            # Skip this test file's own package and tools that only name qmn.
            if "qmn" in path.parts and path.parts[path.parts.index("qmn")] == "qmn":
                continue
            for imported in _imported_modules(path):
                if imported == "qmn" or imported.startswith("qmn."):
                    violations.append(f"{path.relative_to(_WORKSPACE_ROOT)}: {imported}")
    assert violations == [], f"workspace imports qmn: {violations}"


def _imported_modules(path: Path) -> set[str]:
    """Every dotted module name imported by one source file (import + from-import).

    The path is resolved and must be a regular file inside the workspace — never a
    symlink, never resolving out of the workspace — and its size is capped before
    the read, so a planted symlink or an oversized file can neither redirect nor
    unbound it.
    """
    resolved = path.resolve()
    assert not path.is_symlink(), resolved
    assert resolved.is_file() and resolved.is_relative_to(_WORKSPACE_ROOT), resolved
    size = resolved.stat().st_size
    assert size <= _MAX_SOURCE_BYTES, resolved
    tree = ast.parse(resolved.read_text(encoding="utf-8"), filename=str(resolved))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names
