"""Workspace-structure metadata: members, module names, and the dependency map.

Shared reader used by the workspace-structure tests (the ``no qmf/__init__.py`` and
dependency-direction assertions) and by the isolated-build smoke. It parses each
member's ``pyproject.toml`` with the stdlib ``tomllib`` and exposes the facts the two
callers need without either re-implementing the parse.

The invariants this metadata lets a caller enforce (AR-06/AR-18; L30; DEC-0104):

* Every distribution is a **PEP 420 namespace submodule** — the code lives at
  ``src/qmf/<name>/`` with **no** ``src/qmf/__init__.py`` anywhere, so the seven
  roster wheels and the calendar extension can co-occupy the ``qmf`` namespace.
* **Dependency direction is default-deny.** ``qmf-core`` depends on nothing;
  ``qmf-registry`` is the sole roster package with a second inter-library edge
  (``-> qmf-data``); every other roster package depends only on ``qmf-core``; and
  the two edge modules ``qmf-venue`` / ``qmf-risk`` are depended on by nobody.

Stdlib only. Read-only over the workspace tree; no build, no install.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent

PACKAGES_DIR = ROOT / "packages"
EXTENSIONS_DIR = ROOT / "extensions"

# The seven roster packages, in SemVer lockstep (AR-09; DEC-0103).
ROSTER_PACKAGES: frozenset[str] = frozenset(
    {
        "qmf-core",
        "qmf-registry",
        "qmf-data",
        "qmf-indicators",
        "qmf-structure",
        "qmf-venue",
        "qmf-risk",
    }
)

# The edge modules nothing may depend on or import (AD-29..41 for risk; the venue
# edge). They are leaves of the dependency DAG.
EDGE_MODULES: frozenset[str] = frozenset({"qmf-venue", "qmf-risk"})

# The expected roster dependency map (workspace deps only). qmf-core depends on
# nothing; qmf-registry additionally depends on qmf-data; the rest depend only on
# qmf-core. This is the contract the direction test compares against (AR-06; L30).
EXPECTED_ROSTER_DEPS: dict[str, frozenset[str]] = {
    "qmf-core": frozenset(),
    "qmf-data": frozenset({"qmf-core"}),
    "qmf-indicators": frozenset({"qmf-core"}),
    "qmf-registry": frozenset({"qmf-core", "qmf-data"}),
    "qmf-risk": frozenset({"qmf-core"}),
    "qmf-structure": frozenset({"qmf-core"}),
    "qmf-venue": frozenset({"qmf-core"}),
}


@dataclass(frozen=True)
class Member:
    """One workspace member (a roster package or an off-roster extension)."""

    name: str
    directory: Path
    module_name: str
    dependencies: tuple[str, ...]
    is_extension: bool

    @property
    def import_name(self) -> str:
        """The importable module, e.g. ``qmf.core`` — the build-backend module name."""
        return self.module_name

    @property
    def roster_dependencies(self) -> frozenset[str]:
        """The member's workspace (``qmf-*``) dependencies only, third-party dropped."""
        return frozenset(d for d in self.dependencies if d.startswith("qmf-"))

    def source_package_dir(self) -> Path:
        """The ``src/qmf/<name>`` directory holding the member's source."""
        return self.directory / "src" / Path(*self.module_name.split("."))


def _load_member(directory: Path, *, is_extension: bool) -> Member:
    """Parse one member's ``pyproject.toml`` into a :class:`Member`."""
    data = tomllib.loads((directory / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})
    name = project.get("name", directory.name)
    dependencies = tuple(_dep_name(spec) for spec in project.get("dependencies", []))
    module_name = data.get("tool", {}).get("uv", {}).get("build-backend", {}).get("module-name", "")
    return Member(
        name=name,
        directory=directory,
        module_name=module_name,
        dependencies=dependencies,
        is_extension=is_extension,
    )


def _dep_name(spec: str) -> str:
    """The bare distribution name from a PEP 508 dependency spec (drops any version).

    ``qmf-core`` -> ``qmf-core``; ``tzdata==2025.2`` -> ``tzdata``.
    """
    for sep in ("==", ">=", "<=", "~=", "!=", ">", "<", "[", ";", " "):
        idx = spec.find(sep)
        if idx != -1:
            spec = spec[:idx]
    return spec.strip()


def iter_members(root: Path = ROOT) -> Iterator[Member]:
    """Yield every workspace member — roster packages then extensions, name-sorted."""
    packages = root / "packages"
    extensions = root / "extensions"
    for directory in sorted(p for p in packages.glob("*") if (p / "pyproject.toml").is_file()):
        yield _load_member(directory, is_extension=False)
    for directory in sorted(p for p in extensions.glob("*") if (p / "pyproject.toml").is_file()):
        yield _load_member(directory, is_extension=True)


def find_qmf_init_files(root: Path = ROOT) -> list[Path]:
    """Every ``src/qmf/__init__.py`` in the workspace — expected to be empty.

    A namespace-breaking ``qmf/__init__.py`` would make two wheels collide on the
    ``qmf`` package; the invariant is that none exists.
    """
    found: list[Path] = []
    for member in iter_members(root):
        candidate = member.directory / "src" / "qmf" / "__init__.py"
        if candidate.is_file():
            found.append(candidate)
    return found
