"""Story 38.3 — GAP-0085 nouns and GAP-0063 algorithm stay unfilled."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import TypeVar

from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qml.declaration import LEG_ROLES, LegRole
from qml.footprint import ProducerBinding
from qml.generation import (
    CHEAP_VETO_A1,
    CONNECT_WAVE_EPICS,
    DEFAULT_GENERATOR_ALGORITHM,
    DOES_NOT_BLOCK_EPICS,
    DOES_NOT_BLOCK_SURFACES,
    DOOR_EPIC,
    GAP_0063_ALGORITHM_CHOICES,
    GAP_0063_RECORD,
    GAP_0063_STATUS,
    GAP_0085_ID,
    GAP_0085_NOUNS,
    GAP_0085_RECORD,
    GAP_0085_STATUS,
    GAP_0085_WRITE_INCREMENT,
    GAP_0085_WRITE_OWNER,
    GENERATION_EPIC,
    GENERATOR_ALGORITHM_UNRULED,
    HOST_MINTS_MECHANISM_VOCABULARY,
    LIBRARY_EPIC,
    LOGIC_PATH,
    LOGIC_PATH_RUNG,
    LOGIC_PATH_STORY,
    MECHANISM_VOCABULARY_MINTED,
    TRAILS_CONNECT_WAVE,
    WHATIF_EPIC,
    admit_decided_generator_algorithm,
    author_new_structure,
    blocks_library_whatif_or_door,
    mint_mechanism_vocabulary,
    minted_mechanism_type_hits,
    prose_fills_gap_0063,
    refuse_gap_0085_nouns,
    refuse_generator_algorithm,
    refuse_no_code_authoring,
    trails_connect_wave,
    write_ownership_is_qml_host,
)

T = TypeVar("T")

_REPO = Path(__file__).resolve().parents[2]
_QML_SRC = _REPO / "qml" / "src" / "qml"
_QML_EXAMPLES = _REPO / "qml" / "examples"
_QMB_SRC = _REPO / "qmb" / "src" / "qmb"
_QMA_DAEMON_SRC = _REPO / "qmx-agents" / "packages" / "qma-daemon" / "src"
_SKIP_DIR_NAMES = {".git", "__pycache__", ".venv"}


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "test-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _iter_py(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in _SKIP_DIR_NAMES for part in path.parts):
            continue
        paths.append(path)
    return paths


def _class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def test_gap_0085_vocabulary_is_not_minted() -> None:
    assert MECHANISM_VOCABULARY_MINTED is False
    assert HOST_MINTS_MECHANISM_VOCABULARY is False
    assert GAP_0085_RECORD["gap"] == GAP_0085_ID
    assert GAP_0085_RECORD["status"] == GAP_0085_STATUS
    assert GAP_0085_RECORD["minted"] is False
    assert write_ownership_is_qml_host() is True
    assert GAP_0085_WRITE_OWNER == "qml-host"
    assert GAP_0085_WRITE_INCREMENT == "later"
    minted = mint_mechanism_vocabulary()
    assert is_refusal(minted)
    assert minted.category is RefusalCategory.POLICY_REJECTION
    assert minted.context["gap"] == "GAP-0085"
    assert minted.context["gap_status"] == "deferred"
    assert minted.context["minted"] is False
    assert minted.context["write_owner"] == "qml-host"
    assert minted.context["later_increment"] is True
    for noun in sorted(GAP_0085_NOUNS):
        refused = refuse_gap_0085_nouns(noun)
        assert is_refusal(refused)
        assert refused.context["gap"] == "GAP-0085"
        assert refused.context["minted"] is False


def test_epic_source_does_not_define_gap_0085_types() -> None:
    names: list[str] = []
    for path in _iter_py(_QML_SRC):
        names.extend(_class_names(path))
    hits = _ok(minted_mechanism_type_hits(names))
    assert hits == ()
    assert _ok(minted_mechanism_type_hits(("BotDefinition", "Confluence", "LegRole"))) == ()
    assert _ok(minted_mechanism_type_hits(("EntryMechanism", "HardConstraintFilter"))) == (
        "EntryMechanism",
    )


def test_ct34_filter_role_is_not_the_gap_0085_filter_noun() -> None:
    assert frozenset({"level", "trigger", "confirmation", "filter"}) == LEG_ROLES
    assert LegRole.FILTER.value == "filter"
    authored = _ok(
        author_new_structure(
            confluence_legs=[{"role": "filter", "producer_binding": _pinned("zone")}],
        )
    )
    assert authored.confluence is not None
    assert authored.confluence.legs[0].role is LegRole.FILTER
    nested = author_new_structure(
        confluence_legs=[
            {
                "role": "level",
                "producer_binding": _pinned("zone"),
                "EntryMechanism": {"kind": "breakout"},
            }
        ],
    )
    assert is_refusal(nested)
    assert nested.context["field"] == "mechanisms"
    assert nested.context["gap"] == "GAP-0085"


def test_ct33_ct34_contracts_do_not_mint_mechanism_nouns() -> None:
    contracts = (
        _REPO / "docs" / "contracts" / "ct-33-bot-definition.yaml",
        _REPO / "docs" / "contracts" / "ct-34-confluence.yaml",
    )
    for path in contracts:
        text = path.read_text(encoding="utf-8")
        for noun in GAP_0085_NOUNS:
            assert re.search(rf"\b{re.escape(noun)}\b", text) is None, f"{path.name} minted {noun}"


def test_decided_default_algorithm_is_refused_as_unruled() -> None:
    assert DEFAULT_GENERATOR_ALGORITHM is None
    assert GENERATOR_ALGORITHM_UNRULED is True
    assert GAP_0063_RECORD["status"] == GAP_0063_STATUS
    assert GAP_0063_RECORD["default"] is None
    unnamed = admit_decided_generator_algorithm()
    assert is_refusal(unnamed)
    assert unnamed.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert unnamed.context["gap"] == "GAP-0063"
    assert unnamed.context["gap_status"] == "unruled"
    assert unnamed.context["unruled"] is True
    assert unnamed.context["as_default"] is True
    assert unnamed.context["chosen"] is None
    for choice in sorted(GAP_0063_ALGORITHM_CHOICES):
        refused = admit_decided_generator_algorithm(choice)
        assert is_refusal(refused)
        assert refused.context["as_default"] is True
        assert refused.context["named_choice"] is True
        authored = author_new_structure(
            confluence_legs=[{"role": "level", "producer_binding": _pinned("zone")}],
            algorithm=choice,
        )
        assert is_refusal(authored)
        assert authored.context["field"] == "algorithm"
        assert authored.context["gap"] == "GAP-0063"


def test_no_prose_in_this_epic_fills_gap_0063() -> None:
    roots = (
        _QML_SRC / "generation",
        _QML_SRC / "host",
        _QML_EXAMPLES,
    )
    fills: list[str] = []
    for root in roots:
        paths = [root] if root.is_file() else list(root.rglob("*"))
        for path in paths:
            if not path.is_file() or path.suffix not in {".py", ".md"}:
                continue
            if any(part in _SKIP_DIR_NAMES for part in path.parts):
                continue
            text = path.read_text(encoding="utf-8")
            if _ok(prose_fills_gap_0063(text)):
                fills.append(str(path))
    assert fills == []
    assert _ok(prose_fills_gap_0063("the algorithm is unruled GAP-0063")) is False
    assert (
        _ok(
            prose_fills_gap_0063(
                "the first generator algorithm (placeholder-fill of CT-34 legs vs "
                "Python-logic synthesis) is unruled GAP-0063 and is not filled here"
            )
        )
        is False
    )
    assert _ok(prose_fills_gap_0063("the first algorithm is placeholder-fill")) is True
    assert _ok(prose_fills_gap_0063('DEFAULT_GENERATOR_ALGORITHM = "placeholder-fill"')) is True
    idle = refuse_generator_algorithm()
    assert is_ok(idle)


def test_generation_trails_connect_wave_and_does_not_block() -> None:
    assert TRAILS_CONNECT_WAVE is True
    assert CHEAP_VETO_A1 == "NFR-W06 A1"
    assert CONNECT_WAVE_EPICS == (32, 33, 34, 35, 36, 37)
    assert GENERATION_EPIC == 38
    assert max(CONNECT_WAVE_EPICS) < GENERATION_EPIC
    assert trails_connect_wave() is True
    assert LIBRARY_EPIC == 34
    assert WHATIF_EPIC == 35
    assert DOOR_EPIC == 36
    assert DOES_NOT_BLOCK_EPICS == (34, 35, 36)
    assert DOES_NOT_BLOCK_SURFACES == ("library", "what-if", "door")
    assert set(DOES_NOT_BLOCK_EPICS).issubset(set(CONNECT_WAVE_EPICS))
    assert blocks_library_whatif_or_door() is False


def test_library_whatif_and_door_do_not_import_qml_generation() -> None:
    surfaces = (
        _QMB_SRC / "registryread" / "library.py",
        _QMB_SRC / "analysis",
        _QMB_SRC / "doors",
        _QMA_DAEMON_SRC / "qma" / "daemon" / "backtest",
        _QMA_DAEMON_SRC / "qma" / "daemon" / "experiments",
    )
    hits: list[str] = []
    for surface in surfaces:
        paths = [surface] if surface.is_file() else _iter_py(surface)
        for path in paths:
            text = path.read_text(encoding="utf-8")
            if "qml.generation" in text or "from qml.generation" in text:
                hits.append(str(path))
    assert hits == []


def test_no_code_authoring_is_refused_ordinary_python_remains_logic_path() -> None:
    assert LOGIC_PATH == "ordinary_python"
    assert LOGIC_PATH_RUNG == 2
    assert LOGIC_PATH_STORY == "32.3"
    refused = refuse_no_code_authoring(True)
    assert is_refusal(refused)
    assert refused.context["field"] == "no_code"
    assert refused.context["logic_path"] == "ordinary_python"
    assert refused.context["logic_rung"] == 2
    assert refused.context["logic_path_story"] == "32.3"
    authored = author_new_structure(no_code=True)
    assert is_refusal(authored)
    assert authored.context["field"] == "no_code"
    assert authored.context["logic_path"] == LOGIC_PATH
