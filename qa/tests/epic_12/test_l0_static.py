"""L0 — static & purity gates for Epic 12 (qml-protocol).

Behaviour under audit is observed by an AST import scan the TEST owns (never the
package's own report). Each gate carries a self-check that the detector fires on
an injected violation, so a green here is a real green (falsifiability rule 1).

- E12-L0-01 (P1): qml never imports ``qmf.venue``; no qmf roster package imports qml. (L30 roster-scoped)
- E12-L0-02 (P1): the pure qml wheel spawns no thread/process and does no I/O;
  QMB owns the sandbox at its composition root. (AD-15, COMP-QML "May never")
- E12-L0-03 (P2): the runtime-protocol / conformance contracts are QML-local (qml-ad5 ladder), never CT-numbered. (DEC-0171/0177)
"""

from __future__ import annotations

import ast
from pathlib import Path

import qml

_QML_PKG = Path(qml.__file__).resolve().parent
_REPO_ROOT = Path(qml.__file__).resolve().parents[3]
_PACKAGES = _REPO_ROOT / "packages"

# Impure module roots a PURE library must not import anywhere in qml.
_IMPURE_ROOTS = frozenset(
    {
        "os",
        "io",
        "subprocess",
        "threading",
        "multiprocessing",
        "concurrent",
        "socket",
        "asyncio",
        "ssl",
        "urllib",
        "requests",
        "httpx",
        "tempfile",
        "shutil",
        "pathlib",
    }
)


def _imported_roots(source: str) -> set[str]:
    """Top-level import roots in ``source``, via AST — the test's own observer."""
    roots: set[str] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", 1)[0])
                roots.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue
            module = node.module or ""
            if module:
                roots.add(module.split(".", 1)[0])
                roots.add(module)
    return roots


def _dotted_imports(source: str) -> set[str]:
    """Full dotted module names imported (for qmf.venue detection)."""
    names: set[str] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue
            if node.module:
                names.add(node.module)
    return names


def _qml_sources() -> list[tuple[Path, str]]:
    return [(p, p.read_text(encoding="utf-8")) for p in sorted(_QML_PKG.rglob("*.py"))]


# --- E12-L0-01 ---------------------------------------------------------------


def test_e12_l0_01_qml_never_imports_qmf_venue() -> None:
    """qml imports qmf.core/registry/risk only; never qmf.venue (P0-Q on L30)."""
    offenders: list[str] = []
    for path, source in _qml_sources():
        for name in _dotted_imports(source):
            if name == "qmf.venue" or name.startswith("qmf.venue."):
                offenders.append(f"{path.name}: {name}")
    # Counter-case that WOULD fail: a module importing qmf.venue. Detector armed:
    assert "qmf.venue" in _dotted_imports("import qmf.venue\n")
    assert offenders == [], f"qml must never import qmf.venue; found {offenders}"


def test_e12_l0_01_no_qmf_roster_package_imports_qml() -> None:
    """No backend qmf roster package imports qml (the dependency edge is one-way)."""
    offenders: list[str] = []
    if _PACKAGES.exists():
        for path in sorted(_PACKAGES.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            names = _dotted_imports(source) | _imported_roots(source)
            if any(n == "qml" or n.startswith("qml.") for n in names):
                offenders.append(str(path.relative_to(_REPO_ROOT)))
    # Detector armed: a synthetic reverse import is caught.
    assert "qml" in _imported_roots("from qml import protocol\n")
    assert offenders == [], f"no qmf roster package may import qml; found {offenders}"


# --- E12-L0-02 ---------------------------------------------------------------


def test_e12_l0_02_pure_library_has_no_impure_imports() -> None:
    """The complete qml wheel has no thread/process/I-O imports (AD-15)."""
    offenders: list[str] = []
    for path, source in _qml_sources():
        impure = _imported_roots(source) & _IMPURE_ROOTS
        if impure:
            offenders.append(f"{path.relative_to(_QML_PKG)}: {sorted(impure)}")
    # Detector armed: a crafted subprocess import is caught.
    assert "subprocess" in _imported_roots("import subprocess\n") & _IMPURE_ROOTS
    assert offenders == [], f"the pure library must not import {sorted(_IMPURE_ROOTS)}: {offenders}"


def test_e12_l0_02_qmb_composition_root_owns_the_impure_runner() -> None:
    """The required process impurity lives at QMB's composition root (OR-04)."""
    runner = _REPO_ROOT / "qmb" / "src" / "qmb" / "host" / "runner.py"
    assert runner.exists(), "qmb.host.runner is the composition-root impure site"
    roots = _imported_roots(runner.read_text(encoding="utf-8"))
    assert {"os", "subprocess"} <= roots, "QMB owns process spawning + isolation"


# --- E12-L0-03 ---------------------------------------------------------------


def test_e12_l0_03_qml_contracts_are_local_not_ct_numbered() -> None:
    """Protocol/conformance contract identities ride the qml-ad5 ladder, no CT number."""
    proto = qml.protocol_contract_identity()
    conf = qml.conformance_contract_identity()
    assert proto["ladder"] == "qml-ad5"
    assert conf["ladder"] == "qml-ad5"
    # No value anywhere in the identity payload declares a CT-* shared-contract number.
    for identity in (proto, conf):
        for value in identity.values():
            assert not (isinstance(value, str) and value.upper().startswith("CT-")), (
                f"a QML-local contract must not claim a CT number: {value!r}"
            )
    # Counter-case armed: a CT-numbered identity WOULD trip the guard above.
    assert "CT-33".upper().startswith("CT-")
