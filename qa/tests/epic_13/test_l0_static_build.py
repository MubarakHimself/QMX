"""Epic 13 — L0 static / build gate (T13-001..007).

Requirement-derived checks over packaging, the dependency manifest, the module
tree, the inherited vocabulary law, the tier-1 static gate, and the no-module-
global-mutable-state / pure-Python rules. A failing assertion is a FINDING.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

import qmb
from qmb._backends import BACKEND_PACKAGES, VENUE_PACKAGE
from qmb._display import STRUCTURAL_SEED

ROOT = Path(__file__).resolve().parents[3]
QMB_PYPROJECT = ROOT / "qmb" / "pyproject.toml"
QMB_SRC = ROOT / "qmb" / "src" / "qmb"

SIX_BACKENDS = frozenset(
    {"qmf-core", "qmf-registry", "qmf-data", "qmf-indicators", "qmf-structure", "qmf-risk"}
)
FORBIDDEN_VOCAB = frozenset({"engine", "kernel", "exam", "plugin", "snapshot"})
MODULE_TREE = (
    "runloop",
    "config",
    "registryread",
    "execution",
    "data",
    "optimize",
    "robustness",
    "results",
    "ledger",
    "orchestrator",
    "doors/cli",
    "doors/api",
    "doors/mcp",
)


def _manifest() -> dict:
    with QMB_PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)


def _dep_names(deps: list[str]) -> dict[str, str]:
    """Map a PEP 508 dependency list to {name: spec}."""
    out: dict[str, str] = {}
    for raw in deps:
        name = re.split(r"[<>=!~;\[ ]", raw, maxsplit=1)[0].strip()
        out[name] = raw.strip()
    return out


def _words(identifier: str) -> set[str]:
    """Split a snake_case / camelCase identifier into lowercased word parts."""
    parts: list[str] = []
    for chunk in re.split(r"[^A-Za-z0-9]+", identifier):
        parts.extend(re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z0-9]+|[A-Z]+|[0-9]+", chunk))
    return {part.lower() for part in parts if part}


def _tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for sub in ("Scripts", "bin"):
        candidate = Path(sys.prefix) / sub / name
        for suffix in ("", ".exe"):
            if (candidate.with_suffix(suffix)).exists():
                return str(candidate.with_suffix(suffix))
    return None


# --- T13-001 -----------------------------------------------------------------
def test_t13_001_one_wheel_import_and_cli() -> None:
    """qmb is ONE wheel (pure library + qmb CLI), imports as qmb. (13.1 AC1)"""
    manifest = _manifest()
    assert manifest["project"]["name"] == "qmb"
    # top-level import qmb, not a qmf.* namespace submodule
    assert manifest["tool"]["uv"]["build-backend"]["module-name"] == "qmb"
    # exactly one console script: the qmb CLI over the library
    scripts = manifest["project"]["scripts"]
    assert scripts == {"qmb": "qmb.doors.cli:main"}
    assert qmb.__name__ == "qmb"


# --- T13-002 -----------------------------------------------------------------
def test_t13_002_pinned_click_and_optuna() -> None:
    """click and optuna are pinned at exact versions. (13.1 AC1)"""
    deps = _dep_names(_manifest()["project"]["dependencies"])
    assert deps.get("click") == "click==8.4.2", deps.get("click")
    assert deps.get("optuna") == "optuna==4.9.0", deps.get("optuna")


# --- T13-003 -----------------------------------------------------------------
def test_t13_003_six_qmf_backends_no_venue() -> None:
    """qmf dependency set is exactly the six backends; no qmf-venue edge. (13.1 AC1b)"""
    deps = _dep_names(_manifest()["project"]["dependencies"])
    qmf_deps = {name for name in deps if name.startswith("qmf-")}
    assert qmf_deps == SIX_BACKENDS, qmf_deps
    assert VENUE_PACKAGE == "qmf-venue"
    assert VENUE_PACKAGE not in deps
    # library-level backend roster agrees and excludes venue
    assert frozenset(BACKEND_PACKAGES) == SIX_BACKENDS
    assert VENUE_PACKAGE not in BACKEND_PACKAGES


# --- T13-004 -----------------------------------------------------------------
def test_t13_004_module_tree_complete() -> None:
    """The structural-seed module tree is present, mcp scaffolded. (13.1 AC2)"""
    for rel in MODULE_TREE:
        pkg = QMB_SRC.joinpath(*rel.split("/"))
        assert (pkg / "__init__.py").is_file(), f"missing module tree package: {rel}"
    assert set(STRUCTURAL_SEED) == set(MODULE_TREE)
    # mcp is present in the seed (scaffolded); its shipment is asserted at T13-101
    assert "doors/mcp" in STRUCTURAL_SEED


# --- T13-005 -----------------------------------------------------------------
def test_t13_005_vocabulary_law() -> None:
    """No qmb module/symbol names use engine/kernel/exam/plugin; registry state is
    never a 'snapshot'. (13.1 AC3 / B-15)"""
    offenders: list[str] = []

    # (a) module / package / file names
    for path in QMB_SRC.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for part in path.relative_to(QMB_SRC).with_suffix("").parts:
            hit = _words(part) & FORBIDDEN_VOCAB
            if hit:
                offenders.append(f"module name {path.relative_to(ROOT)} -> {sorted(hit)}")

    # (b) qmb's own exported public symbol names (the __all__ surface)
    import importlib

    seen_mods: set[str] = set()
    for path in QMB_SRC.rglob("__init__.py"):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(QMB_SRC).parent
        mod = "qmb" if rel == Path(".") else "qmb." + ".".join(rel.parts)
        seen_mods.add(mod)
    for mod in sorted(seen_mods):
        module = importlib.import_module(mod)
        for name in getattr(module, "__all__", ()):  # noqa: B009 - dynamic surface
            hit = _words(name) & FORBIDDEN_VOCAB
            if hit:
                offenders.append(f"symbol {mod}.{name} -> {sorted(hit)}")

    # (c) 'snapshot' must never appear as a term for registry state, anywhere
    for path in QMB_SRC.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"\bsnapshots?\b", text, re.IGNORECASE):
            offenders.append(f"'snapshot' term in {path.relative_to(ROOT)}")

    assert not offenders, "vocabulary-law violations: " + "; ".join(offenders)


# --- T13-006 -----------------------------------------------------------------
def test_t13_006_tier1_static_gate_ruff_and_pyright() -> None:
    """The tier-1 gate is green over qmb: ruff clean and pyright-strict clean.
    (13.1 AC5) — pytest-green is observed via the independent suite, not re-run here.
    """
    ruff = _tool("ruff")
    assert ruff is not None, "ruff not found in the environment"
    ruff_run = subprocess.run(
        [ruff, "check", str(QMB_SRC), str(ROOT / "qmb" / "tests")],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=180,
    )
    assert ruff_run.returncode == 0, f"ruff not clean:\n{ruff_run.stdout}\n{ruff_run.stderr}"

    pyright = _tool("pyright")
    assert pyright is not None, "pyright not found in the environment"
    pyright_run = subprocess.run(
        [pyright, str(QMB_SRC)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=600,
    )
    assert pyright_run.returncode == 0, (
        f"pyright-strict not clean:\n{pyright_run.stdout[-2000:]}\n{pyright_run.stderr[-1000:]}"
    )


# --- T13-007 -----------------------------------------------------------------
def test_t13_007_no_module_global_mutable_state_and_pure_python() -> None:
    """No module-global mutable container state; package is pure-Python (no compiled
    extension). (13.1 AC5 / AR-11, AR-04, NFR-02)"""
    def _is_dunder(name: str) -> bool:
        # __all__, __version__ etc. are static module manifests/conventions, not
        # runtime state (AR-11 targets shared mutable STATE, not export lists).
        return name.startswith("__") and name.endswith("__")

    def _target_names(targets: list[ast.expr]) -> list[str]:
        return [t.id for t in targets if isinstance(t, ast.Name)]

    mutable_offenders: list[str] = []
    for path in QMB_SRC.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:  # module-level statements only
            targets: list[ast.expr] = []
            value: ast.expr | None = None
            if isinstance(node, ast.Assign):
                targets = node.targets
                value = node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets = [node.target]
                value = node.value
            elif isinstance(node, ast.AugAssign):
                name = getattr(node.target, "id", "?")
                if not _is_dunder(str(name)):
                    mutable_offenders.append(
                        f"{path.relative_to(ROOT)}:{node.lineno} augmented global {name}"
                    )
                continue
            else:
                continue
            if value is None:
                continue
            names = _target_names(targets)
            if names and all(_is_dunder(n) for n in names):
                continue  # module export/convention manifest, not state
            label = ",".join(names) or "?"
            if isinstance(value, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp,
                                  ast.SetComp)):
                mutable_offenders.append(
                    f"{path.relative_to(ROOT)}:{node.lineno} mutable literal -> {label}"
                )
            elif isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and (
                value.func.id in {"list", "dict", "set", "bytearray"}
            ):
                mutable_offenders.append(
                    f"{path.relative_to(ROOT)}:{node.lineno} mutable ctor {value.func.id}() "
                    f"-> {label}"
                )
    assert not mutable_offenders, "module-global mutable state: " + "; ".join(mutable_offenders)

    # pure-Python: no compiled extension modules shipped in the package source
    compiled = [
        str(p.relative_to(ROOT))
        for p in QMB_SRC.rglob("*")
        if p.suffix.lower() in {".so", ".pyd", ".dll", ".dylib"}
    ]
    assert not compiled, f"compiled extension artifacts under qmb/src: {compiled}"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
