"""L0 structural gates for Epic 9 (qmf-structure).

Oracles: constitution L30 (default-deny: qmf-structure imports only qmf-core; nothing
imports qmf-structure in V1), Story 9.1 AC-1 ("frozen dataclasses with typing.Protocol
seams"), FM-9 / L32 (no trading-school name in any rule or vocabulary), L27 / NFR-11
(ships FAILURES.md + examples + _bench + py.typed; typed-refusal register present).

These read the package's own source files and export surface as READ-ONLY structural
evidence — never the runtime behaviour. Covers QA-E09-L0-001..004.
"""

from __future__ import annotations

import ast
import dataclasses
import sys
from pathlib import Path

import pytest
import qmf.structure as structure

import _helpers as H

_STRUCTURE_INIT = Path(structure.__file__).resolve()
_STRUCTURE_SRC = _STRUCTURE_INIT.parent
_PACKAGES_DIR = _STRUCTURE_INIT.parents[4]  # .../packages/qmf-structure/src/qmf/structure/__init__.py

_STDLIB = set(sys.stdlib_module_names)
_ALLOWED_QMF_PREFIXES = ("qmf.core", "qmf.structure")


# --- QA-E09-L0-001: the default-deny import graph (L30) ----------------------


def _imported_modules(source_path: Path) -> set[str]:
    """Every module name imported (absolute) by one source file, via AST — no execution."""
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            # level > 0 is a relative import (within qmf.structure) — always allowed.
            if node.level == 0 and node.module is not None:
                modules.add(node.module)
    return modules


def _foreign_imports(modules: set[str]) -> set[str]:
    """The subset of imported module names that break the default-deny rule."""
    foreign: set[str] = set()
    for module in modules:
        root = module.split(".")[0]
        if module.startswith("qmf."):
            if not module.startswith(_ALLOWED_QMF_PREFIXES):
                foreign.add(module)  # a cross-package qmf import other than qmf.core/qmf.structure
        elif root == "qmf" or root == "__future__" or root in _STDLIB:
            continue
        else:
            foreign.add(module)  # a third-party import
    return foreign


def test_l0_001_detector_flags_a_forbidden_import() -> None:
    # Falsifiability guard: the checker's reject arm is reachable — a qmf.data or numpy
    # import IS flagged, a qmf.core / stdlib import is NOT.
    assert _foreign_imports({"qmf.data", "numpy", "qmf.core", "dataclasses"}) == {
        "qmf.data",
        "numpy",
    }


def test_l0_001_structure_imports_only_qmf_core_and_stdlib() -> None:
    offenders: dict[str, set[str]] = {}
    for source in sorted(_STRUCTURE_SRC.glob("*.py")):
        foreign = _foreign_imports(_imported_modules(source))
        if foreign:
            offenders[source.name] = foreign
    assert offenders == {}, f"qmf.structure modules import outside qmf.core/stdlib: {offenders}"


def test_l0_001_no_roster_package_imports_qmf_structure() -> None:
    # L30: nothing in the roster imports qmf.structure in V1.
    importers: dict[str, set[str]] = {}
    for pkg in sorted(_PACKAGES_DIR.iterdir()):
        if not pkg.is_dir() or pkg.name == "qmf-structure":
            continue
        src = pkg / "src"
        if not src.exists():
            continue
        for source in src.rglob("*.py"):
            hits = {
                module
                for module in _imported_modules(source)
                if module == "qmf.structure" or module.startswith("qmf.structure.")
            }
            if hits:
                importers.setdefault(pkg.name, set()).update(hits)
    assert importers == {}, f"roster packages import qmf.structure (forbidden in V1): {importers}"


# --- QA-E09-L0-002: frozen dataclasses + Protocol seams (Story 9.1 AC-1) ------

_PROTOCOL_SEAMS = (
    "StructureFamily",
    "EvidenceRow",
    "IndicatorResultInput",
    "InvalidationPredicate",
    "PriceObservation",
)


def test_l0_002_every_public_dataclass_is_frozen() -> None:
    non_frozen: list[str] = []
    for name in structure.__all__:
        obj = getattr(structure, name)
        if isinstance(obj, type) and dataclasses.is_dataclass(obj):
            params = getattr(obj, "__dataclass_params__", None)
            if params is None or not params.frozen:
                non_frozen.append(name)
    assert non_frozen == [], f"public value types must be frozen dataclasses: {non_frozen}"


def test_l0_002_frozen_instance_rejects_mutation() -> None:
    # A concrete, falsifiable observation: a minted object cannot be mutated in place.
    obj = H.minted()
    with pytest.raises(dataclasses.FrozenInstanceError):
        obj.observed_at = None  # type: ignore[misc,assignment]


def test_l0_002_seams_are_runtime_checkable_protocols() -> None:
    for seam_name in _PROTOCOL_SEAMS:
        seam = getattr(structure, seam_name)
        assert getattr(seam, "_is_protocol", False) is True, f"{seam_name} must be a typing.Protocol"
        # runtime_checkable so families can be duck-typed at the composition root.
        assert hasattr(seam, "__instancecheck__") or getattr(
            seam, "_is_runtime_protocol", False
        ), f"{seam_name} should be runtime_checkable"


# --- QA-E09-L0-003: no trading-school name in the vocabulary (FM-9 / L32) -----

# A conservative roster of trading-school / method names. A school name may appear in
# prose docs, but never in a public symbol, a family id, a rule descriptor, or an enum
# vocabulary value.
_SCHOOL_NAMES = (
    "wyckoff",
    "elliott",
    "gann",
    "dow theory",
    "ict",
    "smart money",
    "smc",
    "order block",
    "fair value gap",
    "fibonacci",
    "liquidity grab",
    "supply and demand",
    "harmonic",
    "renko",
)


def _words(text: str) -> list[str]:
    """Split an identifier / phrase into lowercased word tokens, breaking on both
    separators (``-`` ``_`` space) and camelCase boundaries, so ``GovernanceVerdict``
    tokenizes to ``[governance, verdict]`` and a short school token like ``ict`` matches
    only a whole word, never a substring of ``verdict``."""
    import re

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return [w for w in re.split(r"[^A-Za-z0-9]+", spaced) if w]


def _has_school_name(text: str) -> bool:
    words = _words(text)
    joined = " ".join(words).lower()
    word_set = {w.lower() for w in words}
    for token in _SCHOOL_NAMES:
        if " " in token:
            if token in joined:  # a multi-word school phrase (e.g. "order block")
                return True
        elif token in word_set:  # a single-word school name as a whole word
            return True
    return False


def test_l0_003_detector_reject_arm_is_reachable() -> None:
    # Falsifiability guard: the detector DOES flag a school-named token, and does NOT
    # misfire on innocuous words that merely contain a short school token as a substring.
    assert _has_school_name("elliott-wave-family") is True
    assert _has_school_name("order_block_zone") is True
    assert _has_school_name("swing-point") is False
    assert _has_school_name("GovernanceVerdict") is False  # 'ict' is not a whole word here


def test_l0_003_no_school_name_across_the_export_surface() -> None:
    from enum import Enum

    vocabulary: list[str] = list(structure.__all__)  # every exported public symbol name
    vocabulary.append(structure.SWING_POINT_CONFIRMATION_RULE)
    # Every StrEnum value across the public modules is vocabulary too.
    for name in structure.__all__:
        obj = getattr(structure, name)
        if isinstance(obj, type) and issubclass(obj, Enum):
            vocabulary.extend(str(member.value) for member in obj)
    # The seed geometry set and the concept-walk register are vocabulary.
    vocabulary.extend(structure.KNOWN_GEOMETRIES)
    vocabulary.extend(str(item.value) for item in structure.CONCEPT_WALK_REGISTER)
    offenders = [term for term in vocabulary if _has_school_name(term)]
    assert offenders == [], f"trading-school names in CT-17 vocabulary (FM-9): {offenders}"


def test_l0_003_seed_family_names_no_school() -> None:
    fam = H.swing_family()
    haystack = " ".join(
        [fam.identity.family_id, fam.identity.geometry, fam.confirmation_rule.descriptor]
    )
    assert not _has_school_name(haystack)


# --- QA-E09-L0-004: distribution-unit artifacts + refusal register (L27) ------


def _package_root() -> Path:
    # .../packages/qmf-structure/src/qmf/structure -> up to .../packages/qmf-structure
    return _STRUCTURE_SRC.parents[2]


def test_l0_004_distribution_artifacts_present() -> None:
    root = _package_root()
    assert (root / "FAILURES.md").is_file()
    assert (root / "examples" / "structure_usage.py").is_file()
    assert (_STRUCTURE_SRC / "_bench.py").is_file()
    assert (_STRUCTURE_SRC / "py.typed").is_file()
    assert (root / "README.md").is_file()


def test_l0_004_failure_register_names_the_ct17_refusal_categories() -> None:
    # The two typed-refusal categories CT-17's paths actually return must be registered.
    text = (_package_root() / "FAILURES.md").read_text(encoding="utf-8").lower()
    assert "invalid input" in text
    assert "policy rejection" in text
