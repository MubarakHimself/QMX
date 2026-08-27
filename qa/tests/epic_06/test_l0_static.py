"""L0 — static / structural gates for Epic 6 (qmf-data source intake).

Oracle = the import graph + dependency manifest + directory listing (not runtime
behaviour). Each gate names the concrete counter-case that would fail it.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

# packages/qmf-data/src/qmf/data/
_SRC = pathlib.Path(__file__).resolve().parents[3] / "packages" / "qmf-data" / "src" / "qmf" / "data"
_PKG_ROOT = pathlib.Path(__file__).resolve().parents[3] / "packages" / "qmf-data"

_INTAKE_MODULES = ["ingest.py", "source_boundary.py", "ticks.py", "dukascopy.py", "calendar_feed.py"]

# Sibling QMF libraries an intake module must never import (default-deny, L30).
_FORBIDDEN_ROOTS = {"qmf.venue", "qmf.risk", "qmf.indicators", "qmf.structure", "qml", "qmb"}
# qmf.registry is a separate library too; the ratified edge is qmf-registry -> qmf-data,
# never the reverse, so an intake module importing qmf.registry is a violation.
_FORBIDDEN_ROOTS_EXACT = _FORBIDDEN_ROOTS | {"qmf.registry"}


def _imported_modules(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names.add(node.module)
    return names


@pytest.mark.parametrize("module", _INTAKE_MODULES)
def test_l0_001_no_forbidden_inter_library_import(module: str) -> None:
    """QA-E06-L0-001 (FR-015, DEC-0120, L30): the intake modules import only qmf.core
    and their own qmf.data.* seam — never qmf.venue / qmf.risk / qmf.registry / qml / qmb.

    Counter-case: an ``import qmf.risk`` in any intake module fails this gate.
    """
    imports = _imported_modules(_SRC / module)
    offenders = {
        name for name in imports
        if any(name == root or name.startswith(root + ".") for root in _FORBIDDEN_ROOTS_EXACT)
    }
    assert not offenders, f"{module} imports forbidden inter-library modules: {sorted(offenders)}"
    # Positive check: every qmf.* import is qmf.core or qmf.data (own package).
    qmf_imports = {n for n in imports if n.split(".")[0] == "qmf"}
    for name in qmf_imports:
        head = ".".join(name.split(".")[:2])
        assert head in {"qmf.core", "qmf.data"}, f"{module} imports unexpected qmf module {name}"


@pytest.mark.parametrize("module", _INTAKE_MODULES)
def test_l0_001b_ingest_holds_no_store_reference(module: str) -> None:
    """QA-E06-L0-001 (behavioural proxy): no intake module names a concrete governed
    store engine / EvidenceStore write surface (the no-direct-governed-write boundary).

    Counter-case: an intake module importing EvidenceStore/AppendStore/ParquetColumnarEngine
    (a governed writer) would fail — the seam must route producer VALUES only.
    """
    imports = _imported_modules(_SRC / module)
    banned_names = {
        "qmf.data.store.append_store",
        "qmf.data.store.engines.parquet",
        "qmf.data.store.facade",
    }
    offenders = imports & banned_names
    # source_boundary.py legitimately owns the CT-10 store hand-off (it IS the boundary);
    # the four *ingest-side* modules must not reach a governed writer directly.
    if module != "source_boundary.py":
        assert not offenders, f"{module} imports a governed store writer directly: {sorted(offenders)}"


@pytest.mark.parametrize("module", _INTAKE_MODULES)
def test_l0_002_no_scheduler_daemon_or_loop(module: str) -> None:
    """QA-E06-L0-002 (Story 6.1 AC6 / 6.3 AC4; CT-15 lifecycle): no intake module
    imports a scheduler/daemon/event-loop runtime, and contains no ``while True`` poll.

    Counter-case: ``import asyncio`` / ``import threading`` / a ``while True:`` loop
    inside an intake module would fail — the seam is a called port, not a runner.
    """
    path = _SRC / module
    imports = _imported_modules(path)
    banned = {"asyncio", "threading", "sched", "schedule", "multiprocessing", "concurrent.futures"}
    offenders = {n for n in imports if n.split(".")[0] in {b.split(".")[0] for b in banned}}
    assert not offenders, f"{module} imports a scheduler/daemon runtime: {sorted(offenders)}"
    # No `while True` polling surface.
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            is_true = isinstance(node.test, ast.Constant) and node.test.value is True
            assert not is_true, f"{module} contains a `while True` polling loop"


def test_l0_003_no_dukascopy_node_donor_code() -> None:
    """QA-E06-L0-003 (Story 6.3 AC4; D1 build-our-own): no dukascopy-node donor runtime
    dependency is declared and no donor module is vendored in the package tree.

    Counter-case: a ``dukascopy-node`` / ``dukascopy`` runtime dependency in the package
    pyproject, or a vendored ``dukascopy_node`` module, would fail this gate.
    """
    pyproject = (_PKG_ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    # Dependencies block only: a mention in a comment/docstring is not a runtime dep.
    for token in ("dukascopy-node", "dukascopy_node"):
        assert token not in pyproject, f"donor dependency token {token!r} in qmf-data pyproject"
    vendored = list(_SRC.rglob("*dukascopy_node*")) + list(_SRC.rglob("*dukascopy-node*"))
    assert not vendored, f"donor code vendored in tree: {vendored}"
    # The QMF-authored adapter is stdlib-only for decode (lzma + struct), no donor import.
    duk_imports = _imported_modules(_SRC / "dukascopy.py")
    third_party = {n for n in duk_imports if n.split(".")[0] not in {
        "qmf", "lzma", "struct", "datetime", "enum", "types", "typing", "collections",
        "dataclasses", "__future__"}}
    assert not third_party, f"dukascopy.py imports an unexpected third-party module: {sorted(third_party)}"
