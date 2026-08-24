"""Workspace-structure metadata: members, module names, and the dependency map.

Shared reader used by the workspace-structure tests (the ``no qmf/__init__.py`` and
dependency-direction assertions) and by the isolated-build smoke. It parses each
member's ``pyproject.toml`` with the stdlib ``tomllib`` and exposes the facts the two
callers need without either re-implementing the parse.

The invariants this metadata lets a caller enforce (AR-06/AR-18; L30; DEC-0104):

* Roster and extension distributions are **PEP 420 namespace submodules** — the
  code lives at ``src/qmf/<name>/`` with **no** ``src/qmf/__init__.py`` anywhere,
  so the seven roster wheels and the calendar extension can co-occupy the ``qmf``
  namespace. Application-layer products (``qml``, later ``qmb``) import as their
  own top-level package and still must not ship ``qmf/__init__.py``.
* **Dependency direction is default-deny and roster-scoped.** ``qmf-core``
  depends on nothing; ``qmf-registry`` is the sole roster package with a second
  inter-library edge (``-> qmf-data``); every other roster package depends only on
  ``qmf-core``; and the two edge modules ``qmf-venue`` / ``qmf-risk`` are depended
  on by no roster package. Application-layer products may consume ``qmf-risk``
  (never ``qmf-venue``) at their composition root (DEC-0171, DEC-0184).

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

# The edge modules no *roster* package may depend on or import (AD-29..41 for
# risk; the venue edge). They are leaves of the roster DAG. Applications may
# consume qmf-risk; nothing consumes qmf-venue (DEC-0171).
EDGE_MODULES: frozenset[str] = frozenset({"qmf-venue", "qmf-risk"})
VENUE_EDGE: str = "qmf-venue"

# Application-layer products live at the repo root (not packages/, not
# extensions/). A missing directory is skipped so a later product can land.
APPLICATION_ROOTS: tuple[str, ...] = ("qml", "qmb")

# Expected workspace deps for application members. qml consumes qmf-core,
# qmf-registry, and qmf-risk only (Story 11.1; DEC-0171). qmb consumes the six
# backend qmf packages and never qmf-venue (Story 13.1; DEC-0169).
EXPECTED_APPLICATION_DEPS: dict[str, frozenset[str]] = {
    "qml": frozenset({"qmf-core", "qmf-registry", "qmf-risk"}),
    "qmb": frozenset(
        {
            "qmf-core",
            "qmf-registry",
            "qmf-data",
            "qmf-indicators",
            "qmf-structure",
            "qmf-risk",
        }
    ),
}

# Application-layer workspace peers (not roster, not third-party). qmb hosts
# CT-33 bots through the QL-7 adapter and may import qml (Story 14.8).
EXPECTED_APPLICATION_PEERS: dict[str, frozenset[str]] = {
    "qml": frozenset(),
    "qmb": frozenset({"qml"}),
}

# Third-party runtime deps for application members (workspace qmf-* dropped).
EXPECTED_APPLICATION_THIRD_PARTY: dict[str, frozenset[str]] = {
    "qml": frozenset(),
    "qmb": frozenset({"click", "optuna"}),
}

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
    """One workspace member (roster package, off-roster extension, or application)."""

    name: str
    directory: Path
    module_name: str
    dependencies: tuple[str, ...]
    is_extension: bool
    is_application: bool = False

    @property
    def is_roster(self) -> bool:
        """True for the seven lockstep ``qmf-*`` packages under ``packages/``."""
        return not self.is_extension and not self.is_application

    @property
    def import_name(self) -> str:
        """The importable module, e.g. ``qmf.core`` or ``qml``."""
        return self.module_name

    @property
    def roster_dependencies(self) -> frozenset[str]:
        """The member's workspace (``qmf-*``) dependencies only, third-party dropped."""
        return frozenset(d for d in self.dependencies if d.startswith("qmf-"))

    def source_package_dir(self) -> Path:
        """The ``src/...`` directory holding the member's importable package."""
        return self.directory / "src" / Path(*self.module_name.split("."))


def _load_member(directory: Path, *, is_extension: bool, is_application: bool = False) -> Member:
    """Parse one member's ``pyproject.toml`` into a :class:`Member`."""
    manifest = directory / "pyproject.toml"
    # A workspace member is defined by a real manifest file; anything else (a missing
    # one, a directory of that name, a dangling symlink) is a broken member, and the
    # check belongs immediately before the read it guards. `iter_members` already
    # filters on the same predicate, so this is defence in depth for a direct caller
    # rather than a reachable path through the public surface.
    if not manifest.is_file():  # pragma: no cover - defensive: iter_members pre-filters
        raise FileNotFoundError(f"workspace member {directory} has no pyproject.toml manifest")
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
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
        is_application=is_application,
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
    """Yield every workspace member — roster, then extensions, then applications."""
    packages = root / "packages"
    extensions = root / "extensions"
    for directory in sorted(p for p in packages.glob("*") if (p / "pyproject.toml").is_file()):
        yield _load_member(directory, is_extension=False)
    for directory in sorted(p for p in extensions.glob("*") if (p / "pyproject.toml").is_file()):
        yield _load_member(directory, is_extension=True)
    for name in APPLICATION_ROOTS:
        directory = root / name
        if (directory / "pyproject.toml").is_file():
            yield _load_member(directory, is_extension=False, is_application=True)


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
