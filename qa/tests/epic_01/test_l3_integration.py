"""Epic 1 — L3 integration / dependency discipline (E1-I01..I04).

Static import-graph and workspace checks over the shipped source. Authored from
Story 1.1 ACs, AR-06/AR-18, DEC-0100/0104/0108/0120. The worktree root is resolved
from this file's location. Source is read-only evidence.
"""

from __future__ import annotations

import ast
from pathlib import Path

# .../qa-audit/qa/tests/epic_01/this_file -> worktree root is parents[3].
ROOT = Path(__file__).resolve().parents[3]
PACKAGES = ROOT / "packages"
ROSTER = {
    "qmf-core",
    "qmf-registry",
    "qmf-data",
    "qmf-indicators",
    "qmf-structure",
    "qmf-venue",
    "qmf-risk",
}
# import root `qmf.<name>` maps to package dir `qmf-<name>`
_NAME_TO_PKG = {pkg.split("-", 1)[1]: pkg for pkg in ROSTER}
THIRD_PARTY = {"numpy", "pandas", "pyarrow", "duckdb"}


def _imported_roots(py: Path) -> set[str]:
    """The set of top-level import targets ('qmf.core', 'numpy', ...) in a file."""
    tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module)
    return roots


def _pkg_of_import(module: str) -> str | None:
    """Owning roster package for an imported module like 'qmf.data.store', else None."""
    parts = module.split(".")
    if len(parts) >= 2 and parts[0] == "qmf" and parts[1] in _NAME_TO_PKG:
        return _NAME_TO_PKG[parts[1]]
    return None


def _src_files(pkg: str) -> list[Path]:
    return list((PACKAGES / pkg / "src").rglob("*.py"))


def _is_static_string_expression(node: ast.AST) -> bool:
    """Whether ``node`` builds a string with no runtime digest/value input."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, (str, int))
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mult)):
        return _is_static_string_expression(node.left) and _is_static_string_expression(node.right)
    return False


def _contains_fp1_recipe_literal(node: ast.AST) -> bool:
    fragments = [
        part.value
        for part in ast.walk(node)
        if isinstance(part, ast.Constant) and isinstance(part.value, str)
    ]
    return "fp1:sha256:" in "".join(fragments)


# E1-I01 — isolated per-package build: undeclared import fails ------------------
def test_e1_i01_qmf_core_stdlib_only_makes_isolated_build_sound() -> None:
    """AR-06/AR-18 / DEC-0104 (static proxy for the isolated-build gate): qmf-core
    declares zero dependencies and its source imports only stdlib + its own package, so
    an isolated build succeeds on stdlib alone — an undeclared import would break it."""
    pyproject = (PACKAGES / "qmf-core" / "pyproject.toml").read_text(encoding="utf-8")
    assert "dependencies = []" in pyproject
    offenders: list[str] = []
    for py in _src_files("qmf-core"):
        for module in _imported_roots(py):
            root = module.split(".")[0]
            owner = _pkg_of_import(module)
            if root in THIRD_PARTY or (owner is not None and owner != "qmf-core"):
                offenders.append(f"{py.relative_to(ROOT)} -> {module}")
    assert offenders == [], f"qmf-core has undeclared/non-stdlib imports: {offenders}"


# E1-I02 — dependency-graph default-deny ---------------------------------------
def test_e1_i02_dependency_graph_default_deny_edges_hold() -> None:
    """DEC-0104/0120 / Story 1.1 AC: qmf-core depends on nothing; every other roster
    package depends only on qmf-core; the sole inter-library edge is
    qmf-registry->qmf-data; and nothing imports qmf-venue or qmf-risk."""
    edges: set[tuple[str, str]] = set()
    for pkg in ROSTER:
        for py in _src_files(pkg):
            for module in _imported_roots(py):
                target = _pkg_of_import(module)
                if target is not None and target != pkg:
                    edges.add((pkg, target))
    # qmf-core depends on nothing
    assert not any(src == "qmf-core" for src, _ in edges), edges
    # nothing imports qmf-venue or qmf-risk (no inbound edge from another package)
    inbound_forbidden = {(s, t) for s, t in edges if t in {"qmf-venue", "qmf-risk"}}
    assert inbound_forbidden == set(), f"forbidden edges into venue/risk: {inbound_forbidden}"
    # the only non-core inter-library edge is qmf-registry -> qmf-data
    non_core_edges = {(s, t) for s, t in edges if t != "qmf-core"}
    assert non_core_edges == {("qmf-registry", "qmf-data")}, non_core_edges


# E1-I03 — single fp1 implementation -------------------------------------------
def test_e1_i03_single_fp1_implementation_only_in_qmf_core() -> None:
    """CT-05 / DEC-0108: no package computes a fingerprint except by calling qmf-core —
    the canonical serializer and fp1 function live ONLY in qmf-core.

    Inspect every package Python file, including tests and examples.  Looking for one
    exact f-string beside one exact ``hashlib`` spelling misses split helpers,
    concatenation/format recipes, imported aliases, and callers which feed a locally
    computed digest into ``Fingerprint.try_create``.
    """
    sanctioned_sha256 = {
        # The one CT-05 implementation and its independent recipe test.
        "packages/qmf-core/src/qmf/core/fingerprint.py",
        "packages/qmf-core/tests/test_ct05_fingerprint.py",
        # These are explicitly non-fp1 protocol/checksum digests.
        "packages/qmf-indicators/src/qmf/indicators/series.py",
        "packages/qmf-venue/src/qmf/venue/proto.py",
    }
    offenders: set[str] = set()
    for py in PACKAGES.rglob("*.py"):
        rel = py.relative_to(ROOT).as_posix()
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        hashlib_aliases = {"hashlib"}
        sha256_aliases: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                hashlib_aliases.update(
                    alias.asname or alias.name for alias in node.names if alias.name == "hashlib"
                )
            elif isinstance(node, ast.ImportFrom) and node.module == "hashlib":
                sha256_aliases.update(
                    alias.asname or alias.name for alias in node.names if alias.name == "sha256"
                )

        computes_sha256 = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            target = node.func
            if (
                (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id in hashlib_aliases
                    and target.attr == "sha256"
                )
                or isinstance(target, ast.Name)
                and target.id in sha256_aliases
            ):
                computes_sha256 = True
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id in hashlib_aliases
                and target.attr == "new"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "sha256"
            ):
                computes_sha256 = True
        if computes_sha256 and rel not in sanctioned_sha256:
            offenders.add(rel)

        # A dynamic recipe construction is a second fp1 implementation even when
        # hashing was routed through another helper/module.
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                literals = "".join(
                    part.value
                    for part in node.values
                    if isinstance(part, ast.Constant) and isinstance(part.value, str)
                )
                if "fp1:sha256:" in literals and any(
                    isinstance(part, ast.FormattedValue) for part in node.values
                ):
                    offenders.add(rel)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "format" and isinstance(node.func.value, ast.Constant):
                    template = node.func.value.value
                    if (
                        isinstance(template, str)
                        and "fp1:sha256:" in template
                        and (node.args or node.keywords)
                    ):
                        offenders.add(rel)
            elif (
                isinstance(node, ast.BinOp)
                and isinstance(node.op, (ast.Add, ast.Mod))
                and _contains_fp1_recipe_literal(node)
                and not _is_static_string_expression(node)
            ):
                offenders.add(rel)

    assert sorted(offenders) == [], (
        "packages computing an fp1 fingerprint outside qmf-core (DEC-0108 single "
        f"implementation): {sorted(offenders)}"
    )


# E1-I04 — SSSF factory-gate stamp preserved -----------------------------------
def test_e1_i04_sssf_factory_gate_stamp_survives() -> None:
    """Story 1.1 AC / root pyproject comments: the workspace-root pyproject preserves
    the SSSF gate contract — the [dependency-groups] dev list and
    testpaths = ["adws/tests"] survive, and adws/tests is present and runnable."""
    root_pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[dependency-groups]" in root_pyproject
    assert 'testpaths = ["adws/tests"]' in root_pyproject
    assert "\ndev = [" in root_pyproject
    adws_tests = ROOT / "adws" / "tests"
    assert adws_tests.is_dir()
    assert list(adws_tests.glob("test_*.py")), "adws/tests carries no runnable test files"
