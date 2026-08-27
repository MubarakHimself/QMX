"""L0 — static & documentation gates for Epic 2 (qmf-registry).

E2-L0-01  default-deny import graph (L30/AR-06, FR-008)
E2-L0-02  no database-server / graph-DB dependency (CT-06/CT-09 `May never`)
E2-L2-07  no fp1 computed except by qmf-core's single implementation (CT-05/AR-14)

These read the real source tree as read-only evidence and assert what the ratified
laws demand of the package's *shape*, not what any single function returns.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

# Locate the worktree packages/ dir from this test file (…/qa/tests/epic_02/).
_QA_ROOT = Path(__file__).resolve()
_WORKTREE = _QA_ROOT.parents[3]
_PACKAGES = _WORKTREE / "packages"
_REGISTRY_SRC = _PACKAGES / "qmf-registry" / "src" / "qmf" / "registry"

# The only inter-package imports the ratified edge set permits for qmf.registry:
# qmf.core (always), and qmf.data (the single ratified inter-library edge, FR-008/L30).
_ALLOWED_QMF_IMPORTS = {"core", "data", "registry"}

_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+qmf\.([a-z_]+)", re.MULTILINE)


def _registry_py_files() -> list[Path]:
    return [p for p in _REGISTRY_SRC.glob("*.py") if not p.name.startswith("_bench")]


def test_e2_l0_01_registry_imports_only_core_and_data() -> None:
    """qmf.registry imports only qmf.core and (via the one ratified edge) qmf.data."""
    offenders: dict[str, set[str]] = {}
    for path in _registry_py_files():
        text = path.read_text(encoding="utf-8")
        subpkgs = set(_IMPORT_RE.findall(text))
        bad = subpkgs - _ALLOWED_QMF_IMPORTS
        if bad:
            offenders[path.name] = bad
    assert offenders == {}, (
        f"qmf.registry imports a roster package beyond qmf.core + qmf.data: {offenders}"
    )


def test_e2_l0_01_no_library_imports_qmf_registry() -> None:
    """Under default-deny, no roster library imports qmf.registry (nothing consumes it)."""
    importers: dict[str, list[str]] = {}
    for pkg_dir in _PACKAGES.iterdir():
        if pkg_dir.name == "qmf-registry" or not pkg_dir.is_dir():
            continue
        src = pkg_dir / "src"
        if not src.exists():
            continue
        for path in src.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for m in re.finditer(r"^\s*(?:from|import)\s+qmf\.registry\b", text, re.MULTILINE):
                importers.setdefault(pkg_dir.name, []).append(path.name)
    assert importers == {}, f"a roster library imports qmf.registry (default-deny breach): {importers}"


def test_e2_l0_02_no_database_server_dependency_declared() -> None:
    """The package declares no database-server / graph-DB dependency (records are per-kind
    versioned records; lineage is pinned JSONL). SQLite is stdlib and reached through
    qmf-data, never a server dependency of qmf-registry."""
    pyproject = _PACKAGES / "qmf-registry" / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    deps: list[str] = list(data.get("project", {}).get("dependencies", []))
    banned = (
        "psycopg", "postgres", "mysql", "mariadb", "neo4j", "mongo", "pymongo",
        "redis", "cassandra", "sqlalchemy", "asyncpg", "motor", "arangodb", "duckdb",
    )
    hits = [d for d in deps if any(b in d.lower() for b in banned)]
    assert hits == [], f"qmf-registry declares a database-server / graph-DB dependency: {hits}"


def test_e2_l2_07_no_registry_local_hashing() -> None:
    """No fp1 is computed except by qmf-core's single implementation — the registry
    performs no local hashing (no hashlib / sha256 / blake in its source). (CT-05, AR-14)"""
    offenders: dict[str, list[str]] = {}
    # Real local-hashing signals — NOT the `fp1:sha256:<hex>` format literal that appears
    # in docstrings (that names qmf-core's recipe; it does not compute a hash here).
    banned = ("hashlib", "hexdigest", "blake2b(", "blake2s(", "md5(", "_hashlib")
    for path in _registry_py_files():
        text = path.read_text(encoding="utf-8")
        found = [b for b in banned if b in text]
        if found:
            offenders[path.name] = found
    assert offenders == {}, f"qmf.registry computes a hash locally instead of via qmf-core: {offenders}"
