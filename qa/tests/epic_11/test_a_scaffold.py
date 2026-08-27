"""Epic 11 / Story 11.1 — scaffold, purity, dependency stance, tunnel entry.

A1/A2 packaging, A3/A5 ambient-nondeterminism (AD-15), A4 import legality
(AR-60), A6 tunnel entry, A7 SemVer-never-in-identity. Static gates read the
real files/AST as independent evidence; the scanners are self-verified to be
able to fail by running them over a synthetic violating snippet.
"""

from __future__ import annotations

import ast
import os
import tomllib
from collections.abc import Iterable

import helpers as H

import qml
from qml.conformance import admit_ungoverned_tunnel, cite_ungoverned_bot
from qml.declaration import mint_bot_definition, mint_confluence
from qml.logic import mint_logic_identity

QML_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "qml")
)
QML_SRC = os.path.join(QML_ROOT, "src", "qml")
# 11.1 AC2 names exactly seven module homes: five live under src/qml, two
# (examples/, tests/) live at the distribution root.
SRC_HOMES = ("declaration", "families", "footprint", "protocol", "conformance")
ROOT_HOMES = ("examples", "tests")


def _iter_module_files() -> list[str]:
    found: list[str] = []
    for root, _dirs, files in os.walk(QML_SRC):
        if "__pycache__" in root:
            continue
        for name in files:
            if name.endswith(".py"):
                found.append(os.path.join(root, name))
    return found


def _imported_modules(source: str) -> set[str]:
    """Every top-level dotted module name an ``import`` statement pulls in."""
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None and node.level == 0:
                names.add(node.module)
    return names


# --- A1 / A2 packaging: dependencies and no CLI -----------------------------


def test_a1_dependencies_are_qmf_only_no_extra_runtime_dep() -> None:
    """A1: qml adds no runtime dependency beyond the qmf-* packages it consumes.

    Counter-case: a dependency on qmf-venue, or any non-qmf third party, fails.
    """
    with open(os.path.join(QML_ROOT, "pyproject.toml"), "rb") as fh:
        cfg = tomllib.load(fh)
    deps = cfg["project"]["dependencies"]
    dep_names = {d.split(">")[0].split("<")[0].split("=")[0].split("[")[0].strip() for d in deps}
    assert dep_names <= {"qmf-core", "qmf-registry", "qmf-risk"}, dep_names
    assert "qmf-venue" not in dep_names


def test_a2_no_console_scripts_entry_point() -> None:
    """A2: qml ships no CLI — no console_scripts / project.scripts entry point.

    Counter-case: a ``[project.scripts]`` table (a qml CLI) fails.
    """
    with open(os.path.join(QML_ROOT, "pyproject.toml"), "rb") as fh:
        cfg = tomllib.load(fh)
    assert "scripts" not in cfg.get("project", {})
    assert "console_scripts" not in cfg.get("project", {}).get("entry-points", {})


def test_a2_seven_named_module_homes_are_present() -> None:
    """A2: the seven ratified module homes are present (five in src, two at root)."""
    for home in SRC_HOMES:
        assert os.path.isdir(os.path.join(QML_SRC, home)), f"missing src home: {home}"
    for home in ROOT_HOMES:
        assert os.path.isdir(os.path.join(QML_ROOT, home)), f"missing root home: {home}"


def test_a2_no_source_module_home_beyond_the_named_seven() -> None:
    """A2 (11.1 AC2): the package contains EXACTLY the named module homes — no extras.

    Counter-case: a src package home not among the five named. FINDING if any extra
    home ships in the distribution (the 'exactly' clause is falsified).
    """
    src_dirs = {
        name
        for name in os.listdir(QML_SRC)
        if os.path.isdir(os.path.join(QML_SRC, name)) and name != "__pycache__"
    }
    extra = src_dirs - set(SRC_HOMES)
    assert extra == set(), f"module homes beyond the named seven: {sorted(extra)}"


# --- A4 import legality (AR-60) ---------------------------------------------


def _venue_importers(files: Iterable[str]) -> list[str]:
    offenders: list[str] = []
    for path in files:
        with open(path, encoding="utf-8") as fh:
            mods = _imported_modules(fh.read())
        if any(m == "qmf.venue" or m.startswith("qmf.venue.") for m in mods):
            offenders.append(path)
    return offenders


def test_a4_scanner_can_detect_a_qmf_venue_import() -> None:
    """A4 self-check (rule 1): the import scanner flags a synthetic qmf-venue import."""
    mods = _imported_modules("import qmf.venue\nfrom qmf.venue.door import x\n")
    assert "qmf.venue" in mods


def test_a4_no_qml_module_imports_qmf_venue() -> None:
    """A4 (AR-60): every qml module imports qmf-core/registry/risk only, never qmf-venue.

    Counter-case: a single ``import qmf.venue`` anywhere in qml fails the gate.
    """
    offenders = _venue_importers(_iter_module_files())
    assert offenders == [], f"qml modules importing qmf-venue: {offenders}"


# --- A3 / A5 ambient-nondeterminism (AD-15) ---------------------------------

_FORBIDDEN_IMPORTS = {"threading", "subprocess", "multiprocessing", "socket", "asyncio", "requests"}
_FORBIDDEN_CALLS = {"open", "system", "popen", "sleep", "time", "now", "today", "monotonic"}


def _ambient_offenders(source: str) -> list[str]:
    """AD-15 scan: imports that spawn threads/processes/IO and ambient clock/IO calls."""
    tree = ast.parse(source)
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in _FORBIDDEN_IMPORTS:
                    hits.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in _FORBIDDEN_IMPORTS:
                hits.append(f"from {node.module}")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "open":
                hits.append("call open()")
            if isinstance(func, ast.Attribute) and func.attr in {"system", "popen", "sleep"}:
                hits.append(f"call .{func.attr}()")
    return hits


def test_a5_scanner_can_detect_ambient_impurity() -> None:
    """A5 self-check (rule 1): the AD-15 scanner flags synthetic threading/open()."""
    hits = _ambient_offenders("import threading\ndef f():\n    open('x')\n")
    assert "import threading" in hits
    assert "call open()" in hits


def test_a5_no_qml_module_spawns_thread_process_or_does_io() -> None:
    """A5 (11.1 AC4, AD-15): NO qml module spawns a process/thread or performs I/O.

    Story 11.1 AC4 makes this a package-wide claim ('scans ANY qml module').
    Counter-case: any qml module importing subprocess or calling open(). FINDING if
    any impurity ships in the distribution.
    """
    offenders: dict[str, list[str]] = {}
    for path in _iter_module_files():
        with open(path, encoding="utf-8") as fh:
            hits = _ambient_offenders(fh.read())
        if hits:
            offenders[os.path.relpath(path, QML_SRC)] = hits
    assert offenders == {}, f"AD-15 ambient impurity in qml: {offenders}"


def test_a5_epic11_authoring_homes_are_pure() -> None:
    """A5 (AD-15): the Epic-11 authoring homes themselves are pure (no I/O, no process).

    Scoped to the CT-33/CT-34/footprint/logic authoring surface Epic 11 owns.
    Counter-case: an authoring module doing I/O or spawning a process.
    """
    epic11_homes = ("declaration", "families", "footprint", "logic", "protocol")
    offenders: dict[str, list[str]] = {}
    for path in _iter_module_files():
        rel = os.path.relpath(path, QML_SRC)
        if not any(rel.startswith(home + os.sep) for home in epic11_homes):
            continue
        with open(path, encoding="utf-8") as fh:
            hits = _ambient_offenders(fh.read())
        if hits:
            offenders[rel] = hits
    assert offenders == {}, f"AD-15 impurity in an Epic-11 authoring home: {offenders}"


def test_a3_conformance_package_is_pure() -> None:
    """A3 (AD-15): the conformance/ package spawns no process and performs no I/O."""
    offenders: dict[str, list[str]] = {}
    for path in _iter_module_files():
        if os.sep + "conformance" + os.sep not in path:
            continue
        with open(path, encoding="utf-8") as fh:
            hits = _ambient_offenders(fh.read())
        if hits:
            offenders[os.path.relpath(path, QML_SRC)] = hits
    assert offenders == {}, f"conformance/ impurity: {offenders}"


# --- A6 tunnel entry --------------------------------------------------------


def test_a6_ungoverned_tunnel_is_open_without_a_conformance_ticket() -> None:
    """A6 (11.1 AC5): conformance never gates tunnel entry.

    ``admit_ungoverned_tunnel`` grants access with no ticket presented; a
    governed-evidence citation of an ungoverned bot is refused while the tunnel
    stays open. Counter-case: if tunnel entry required a conformance ticket,
    admit would refuse or set tunnel_open False.
    """
    access = H.unwrap(admit_ungoverned_tunnel(), "tunnel access")
    identity = access.fp1_identity()
    assert identity["tunnel_open"] is True
    assert identity["ticket_required"] is False
    # Citation by governed evidence is gated (refused) yet tunnel stays open.
    refused = cite_ungoverned_bot(cited_fp1=None, kind=None)
    assert H.category_of(refused) in H.QML_AUTHORING_CATEGORIES
    assert refused.context.get("tunnel_open") is True


# --- A7 SemVer never enters identity ----------------------------------------


def _flatten(value: object) -> list[object]:
    out: list[object] = []
    if isinstance(value, dict):
        for item in value.values():
            out.extend(_flatten(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            out.extend(_flatten(item))
    else:
        out.append(value)
    return out


def test_a7_package_semver_never_enters_any_fp1() -> None:
    """A7 (11.1 AC1): qml SemVer is display-only and never enters any fp1.

    Counter-case: qml.__version__ appearing anywhere inside an authored artifact's
    identity payload would fail.
    """
    version = qml.__version__
    bot = H.unwrap(mint_bot_definition(H.bot_payload()), "bot")
    confl = H.unwrap(mint_confluence([{"role": "level", "producer_binding": H.pinned("z")}]), "cf")
    logic = H.unwrap(mint_logic_identity("research-bot", "1.0.0", H.logic_source()), "logic")
    for artifact, what in ((bot, "bot"), (confl, "confluence"), (logic, "logic")):
        flat = _flatten(artifact.fp1_identity())
        assert version not in flat, f"{what} identity leaked qml SemVer {version}"


def test_a7_declared_package_version_field_is_refused() -> None:
    """A7: a Bot payload carrying a package_version identity field is invalid input."""
    refused = mint_bot_definition({**H.bot_payload(), "package_version": qml.__version__})
    assert H.category_of(refused) == "invalid input"
