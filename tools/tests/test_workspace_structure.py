"""Workspace-structure tests (M9; AR-06/AR-18, L30).

Two invariants the ``check-integration`` build cannot prove on its own, asserted here
against the live workspace tree via :mod:`workspace_meta`:

* **(a) No ``qmf/__init__.py`` anywhere.** Every distribution is a PEP 420 namespace
  submodule; a package init would collide two wheels on the ``qmf`` namespace.
* **(b) Dependency direction is default-deny.** ``qmf-core`` depends on nothing; the
  sole inter-library edge beyond ``-> qmf-core`` is ``qmf-registry -> qmf-data``; the
  edge modules ``qmf-venue`` / ``qmf-risk`` are depended on by nobody, and no member
  imports them either.

The install-and-import proof that an *undeclared* import fails lives in the Tier-2
isolated-build smoke (``tools/isolated_build_check.py``); these Tier-1 tests pin the
declared structure that the smoke then verifies against real wheels.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import workspace_meta
from workspace_meta import (
    EDGE_MODULES,
    EXPECTED_ROSTER_DEPS,
    ROSTER_PACKAGES,
    Member,
)

MEMBERS = list(workspace_meta.iter_members())
MEMBERS_BY_NAME = {m.name: m for m in MEMBERS}


def test_all_roster_packages_are_present() -> None:
    names = {m.name for m in MEMBERS if not m.is_extension}
    assert ROSTER_PACKAGES <= names, f"missing roster packages: {ROSTER_PACKAGES - names}"


# --- (a) no qmf/__init__.py in any distribution -----------------------------


def test_no_qmf_namespace_init_anywhere() -> None:
    offenders = workspace_meta.find_qmf_init_files()
    assert offenders == [], (
        "these src/qmf/__init__.py files break the PEP 420 namespace (two wheels would "
        f"collide on the qmf package): {[str(p) for p in offenders]}"
    )


@pytest.mark.parametrize("member", MEMBERS, ids=lambda m: m.name)
def test_member_ships_a_namespace_submodule_not_a_package_init(member: Member) -> None:
    # The source lives at src/qmf/<name>/ and there is no src/qmf/__init__.py above it.
    assert member.source_package_dir().is_dir(), f"{member.name}: no {member.source_package_dir()}"
    assert not (member.directory / "src" / "qmf" / "__init__.py").is_file()


# --- (b) dependency direction -----------------------------------------------


@pytest.mark.parametrize("name", sorted(EXPECTED_ROSTER_DEPS), ids=lambda n: n)
def test_roster_dependency_direction_matches_contract(name: str) -> None:
    member = MEMBERS_BY_NAME[name]
    assert member.roster_dependencies == EXPECTED_ROSTER_DEPS[name], (
        f"{name} declares workspace deps {sorted(member.roster_dependencies)}, "
        f"expected {sorted(EXPECTED_ROSTER_DEPS[name])}"
    )


def test_qmf_core_depends_on_nothing() -> None:
    assert MEMBERS_BY_NAME["qmf-core"].dependencies == ()


def test_sole_second_inter_library_edge_is_registry_to_data() -> None:
    # Every roster edge beyond "-> qmf-core" must be exactly qmf-registry -> qmf-data.
    extra_edges = {
        m.name: sorted(m.roster_dependencies - {"qmf-core"})
        for m in MEMBERS
        if not m.is_extension and (m.roster_dependencies - {"qmf-core"})
    }
    assert extra_edges == {"qmf-registry": ["qmf-data"]}


def test_edge_modules_are_depended_on_by_nobody() -> None:
    for member in MEMBERS:
        offending = member.roster_dependencies & EDGE_MODULES
        assert not offending, f"{member.name} depends on edge module(s) {sorted(offending)}"


def test_no_member_imports_an_edge_module() -> None:
    # Static check: no member's source contains `import qmf.venue` / `import qmf.risk`
    # (nothing depends on OR imports the edge modules).
    edge_imports = {"qmf.venue", "qmf.risk"}
    violations: list[str] = []
    for member in MEMBERS:
        for path in sorted(member.source_package_dir().rglob("*.py")):
            for imported in _imported_modules(path):
                is_edge = imported in edge_imports or any(
                    imported.startswith(edge + ".") for edge in edge_imports
                )
                # A module never imports itself into a violation.
                if is_edge and not imported.startswith(member.module_name):
                    violations.append(f"{path}: imports {imported}")
    assert violations == [], f"edge-module imports found: {violations}"


def _imported_modules(path: Path) -> set[str]:
    """The dotted module names imported by one source file (import + from-import)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError):
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


# --- extension direction ----------------------------------------------------


def test_calendar_extension_depends_only_on_core_and_tzdata() -> None:
    ext = MEMBERS_BY_NAME["qmf-calendar-forex"]
    assert ext.roster_dependencies == {"qmf-core"}
    assert "tzdata" in ext.dependencies
