"""Epic 3 — L0 static / documentation gates (PLAN Section 4).

G1 — Import-graph gate (FR-011/FR-016; DEC-0120, L30): every module under ``qmf.data``
imports only ``qmf.core`` (+ stdlib + its own declared engine libraries) and its own
``qmf.data.*`` seam — no *other* ``qmf.*`` roster package (default-deny).

G2 — No-server gate (FR-016; AR-30, DEC-0117): the package declares no database-server /
graph-DB client dependency; the only physical engines are Parquet / DuckDB / SQLite /
JSONL, each behind a CT-11/CT-13/CT-09-owned contract.

These read source/config as static evidence only; no source is edited.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import qmf.data as qdata

_SRC_ROOT = Path(qdata.__file__).resolve().parent  # .../qmf-data/src/qmf/data
# parents: [0]=qmf, [1]=src, [2]=qmf-data -> the package root holding pyproject.toml
_PYPROJECT = _SRC_ROOT.parents[2] / "pyproject.toml"  # packages/qmf-data/pyproject.toml

# The only qmf.* prefixes a qmf.data module may import: qmf.core (the fp1 + refusal
# vocabulary) and its own qmf.data.* seam. Any other qmf.* import is a default-deny breach.
_ALLOWED_QMF_PREFIXES = ("qmf.core", "qmf.data")

# Database-server / graph-DB client libraries that must NEVER be a dependency (no DB server
# anywhere in V1). Substring match over the declared dependency tokens.
_FORBIDDEN_DB_CLIENTS = (
    "psycopg",
    "asyncpg",
    "mysql",
    "pymysql",
    "neo4j",
    "redis",
    "pymongo",
    "mongo",
    "cassandra",
    "sqlalchemy",
    "clickhouse",
    "influx",
    "elasticsearch",
    "kafka",
    "postgres",
    "mariadb",
)

# The four ratified engines (Story 3.1 AC1). SQLite and JSONL are stdlib (sqlite3 / json),
# so only Parquet and DuckDB appear as declared third-party dependencies.
_RATIFIED_ENGINE_DEPS = ("pyarrow", "duckdb")


def _iter_qmf_data_modules() -> list[Path]:
    return sorted(_SRC_ROOT.rglob("*.py"))


def _imported_qmf_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("qmf."):
                    names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            # Only absolute imports carry a module; relative imports (level>0) stay in-package.
            if node.level == 0 and node.module is not None and node.module.startswith("qmf."):
                names.add(node.module)
    return names


def test_g1_import_graph_only_qmf_core_and_own_seam() -> None:
    """G1: no qmf.data module imports any qmf.* package but qmf.core and qmf.data (DEC-0120)."""
    offenders: dict[str, set[str]] = {}
    modules = _iter_qmf_data_modules()
    assert modules, "expected to find qmf.data source modules to scan"
    for path in modules:
        bad = {
            name
            for name in _imported_qmf_names(path)
            if not any(name == p or name.startswith(p + ".") for p in _ALLOWED_QMF_PREFIXES)
        }
        if bad:
            offenders[str(path.relative_to(_SRC_ROOT))] = bad
    assert offenders == {}, (
        "qmf.data must import only qmf.core and its own qmf.data.* seam (default-deny, "
        f"DEC-0120); cross-package imports found: {offenders}"
    )


def test_g2_no_database_server_dependency() -> None:
    """G2: qmf-data declares no DB-server/graph-DB client; only Parquet+DuckDB engines (AR-30)."""
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    deps = list(data["project"].get("dependencies", []))
    # Optional / dev groups too (a DB server must not sneak in anywhere).
    for group in data.get("dependency-groups", {}).values():
        deps.extend(str(item) for item in group)
    for extra in data["project"].get("optional-dependencies", {}).values():
        deps.extend(str(item) for item in extra)

    lowered = [d.lower() for d in deps]
    forbidden_hits = sorted(
        d for d in lowered for token in _FORBIDDEN_DB_CLIENTS if token in d
    )
    assert forbidden_hits == [], (
        "qmf-data must introduce no database server or graph-DB client (FR-016); "
        f"forbidden dependency tokens found: {forbidden_hits}"
    )

    # The runtime dependency set beyond qmf-core is exactly the two non-stdlib ratified
    # engines (Parquet, DuckDB); SQLite (sqlite3) and JSONL (json) are stdlib.
    runtime = [d.lower() for d in data["project"].get("dependencies", [])]
    non_core = [d for d in runtime if not d.startswith("qmf-core")]
    for dep in non_core:
        assert any(engine in dep for engine in _RATIFIED_ENGINE_DEPS), (
            f"unexpected runtime dependency {dep!r}: only the ratified Parquet/DuckDB engines "
            "may be declared beyond qmf-core (DEC-0117)"
        )
