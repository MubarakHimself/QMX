"""Story 49.5 — vocabulary helper resolves swing-high from host-passed cited bytes."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import TypeVar, cast

import pytest
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qml.generation import GAP_0085_NOUNS, minted_mechanism_type_hits
from qml.research import DICTIONARY_FIELDS, DictionaryEntry, resolve_dictionary_entry

from qml import research

T = TypeVar("T")

FIXTURE_SEED = Path(__file__).resolve().parent / "fixtures" / "research-seed"
SWING_HIGH_PATH = "dictionary/market-structure-and-location/locations-and-structure.md"
SWING_HIGH_LOCATOR = f"{SWING_HIGH_PATH}#swing-high"
LIQUIDITY_SWEEP_LOCATION = (
    "dictionary/market-structure-and-location/locations-and-structure.md#liquidity-sweep"
)
LIQUIDITY_SWEEP_CONTEXT = (
    "dictionary/context-regime-and-intermarket/context-filters-confirmations.md#liquidity-sweep"
)
LIQUIDITY_SWEEP_TRIGGERS = (
    "dictionary/price-action-and-patterns/triggers-patterns-transitions.md#liquidity-sweep"
)
_QML_RESEARCH = Path(__file__).resolve().parents[1] / "src" / "qml" / "research"
_BANNED_IMPORTS = frozenset(
    {
        "asyncio",
        "concurrent",
        "http",
        "multiprocessing",
        "os",
        "pathlib",
        "socket",
        "subprocess",
        "threading",
        "urllib",
        "qmf.registry",
        "qmf.venue",
        "qml.declaration.confluence",
        "qml.footprint",
    }
)
_DNA_KEYS = frozenset(
    {
        "class",
        "dna",
        "entry_hypothesis",
        "F",
        "f_map",
        "producer_binding",
        "formula_id",
        "research_ref",
        "registry_kind",
        "admission_confidence",
    }
)


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _cited_bytes(relative: str) -> bytes:
    src = FIXTURE_SEED / relative
    if not src.is_file():
        pytest.fail(
            "AR-RES-10 requires fixtures/research-seed bytes copied from the "
            f"operator Stats tree — missing {relative}"
        )
    return src.read_bytes()


def _path_of(locator: str) -> str:
    return locator.split("#", 1)[0]


def test_swing_high_twelve_field_record_from_host_passed_bytes() -> None:
    cited = _cited_bytes(SWING_HIGH_PATH)
    entry = _ok(
        resolve_dictionary_entry(
            cited,
            file_path=SWING_HIGH_PATH,
            entry_id="swing-high",
        )
    )
    assert isinstance(entry, DictionaryEntry)
    assert entry.identity() == (SWING_HIGH_PATH, "swing-high")
    assert entry.id == "swing-high"
    assert entry.file_path == SWING_HIGH_PATH
    assert entry.title == "Swing High"
    assert tuple(entry.fields) == DICTIONARY_FIELDS
    assert len(entry.fields) == 12
    assert entry.fields["family"] == "Swing points & structural ranges"
    assert "pivot high" in entry.fields["aliases"]
    assert "local upper turning point" in entry.fields["definition"]
    assert "OHLC bar series" in entry.fields["observable_inputs"]
    payload = dict(entry.to_payload())
    assert payload["id"] == "swing-high"
    assert payload["file_path"] == SWING_HIGH_PATH
    assert "research_ref" not in payload
    for key in _DNA_KEYS:
        assert key not in payload
        assert key not in entry.fields


def test_swing_high_eligible_roles_include_location_trigger_invalidation() -> None:
    cited = _cited_bytes(SWING_HIGH_PATH)
    entry = _ok(
        resolve_dictionary_entry(
            cited,
            file_path=SWING_HIGH_LOCATOR,
        )
    )
    assert "location" in entry.eligible_roles
    assert "trigger" in entry.eligible_roles
    assert "invalidation" in entry.eligible_roles
    assert "context" in entry.eligible_roles
    assert "confirmation" in entry.eligible_roles
    assert "InvalidationRule" not in entry.eligible_roles
    assert entry.fields["eligible_roles"].startswith("location")


def test_collision_resolution_uses_file_path_and_id() -> None:
    location_bytes = _cited_bytes(_path_of(LIQUIDITY_SWEEP_LOCATION))
    context_bytes = _cited_bytes(_path_of(LIQUIDITY_SWEEP_CONTEXT))
    trigger_bytes = _cited_bytes(_path_of(LIQUIDITY_SWEEP_TRIGGERS))

    missing_path = resolve_dictionary_entry(
        location_bytes, file_path="", entry_id="liquidity-sweep"
    )
    assert is_refusal(missing_path)
    assert missing_path.category is RefusalCategory.INVALID_INPUT
    assert missing_path.context["field"] == "file_path"
    assert "file_path" in str(missing_path.context["reason"])

    missing_id = resolve_dictionary_entry(
        location_bytes, file_path=_path_of(LIQUIDITY_SWEEP_LOCATION)
    )
    assert is_refusal(missing_id)
    assert missing_id.context["field"] == "id"

    location = _ok(
        resolve_dictionary_entry(
            location_bytes,
            file_path=_path_of(LIQUIDITY_SWEEP_LOCATION),
            entry_id="liquidity-sweep",
        )
    )
    context = _ok(
        resolve_dictionary_entry(
            context_bytes,
            file_path=LIQUIDITY_SWEEP_CONTEXT,
        )
    )
    triggers = _ok(
        resolve_dictionary_entry(
            trigger_bytes,
            file_path=LIQUIDITY_SWEEP_TRIGGERS,
        )
    )
    assert location.identity() != context.identity()
    assert location.identity() != triggers.identity()
    assert location.id == context.id == triggers.id == "liquidity-sweep"
    assert location.fields["family"] != context.fields["family"]
    assert "invalidation" not in location.eligible_roles
    assert "invalidation" in context.eligible_roles

    concatenated = location_bytes + b"\n" + context_bytes
    colliding = resolve_dictionary_entry(
        concatenated,
        file_path=_path_of(LIQUIDITY_SWEEP_LOCATION),
        entry_id="liquidity-sweep",
    )
    assert is_refusal(colliding)
    assert colliding.context["field"] == "id"
    assert colliding.context["id"] == "liquidity-sweep"
    assert colliding.context["file_path"] == _path_of(LIQUIDITY_SWEEP_LOCATION)
    assert colliding.context["occurrences"] == 2


def test_helper_performs_no_filesystem_io_threads_or_process() -> None:
    source = inspect.getsource(resolve_dictionary_entry)
    assert "open(" not in source
    violations: list[str] = []
    for path in sorted(_QML_RESEARCH.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names.append(node.module)
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "open"
            ):
                violations.append(f"{path}: open()")
                continue
            for name in names:
                if name in _BANNED_IMPORTS or any(
                    name.startswith(banned + ".") for banned in _BANNED_IMPORTS
                ):
                    violations.append(f"{path}: imports {name}")
    assert violations == []


def test_meaning_is_computed_only_by_qml_research() -> None:
    cited = _cited_bytes(SWING_HIGH_PATH)
    adapter_payload = {
        "locator": SWING_HIGH_LOCATOR,
        "content": cited,
        "include": (
            "README.md",
            "dictionary/",
            "strategies/",
        ),
        "exclude": (".obsidian/", "backend/strats.sqlite"),
    }
    for key in (
        "family",
        "aliases",
        "definition",
        "eligible_roles",
        "class",
        "dna",
        "F",
        "research_ref",
    ):
        assert key not in adapter_payload
    entry = _ok(
        resolve_dictionary_entry(
            adapter_payload["content"],
            file_path=cast("str", adapter_payload["locator"]),
        )
    )
    assert entry.fields["family"]
    assert "location" in entry.eligible_roles


def test_does_not_register_registry_row_or_mint_ct16_or_research_ref() -> None:
    assert "Confluence" not in research.__all__
    assert "confluence" not in research.__all__
    assert not hasattr(research, "Confluence")
    assert not hasattr(research, "confluence")
    assert not hasattr(research, "research_ref")
    assert not hasattr(research, "mint_research_ref")
    assert not hasattr(research, "register_dictionary_entry")
    assert not hasattr(research, "mint_producer")
    cited = _cited_bytes(SWING_HIGH_PATH)
    entry = _ok(
        resolve_dictionary_entry(
            cited,
            file_path=SWING_HIGH_PATH,
            entry_id="swing-high",
        )
    )
    payload = dict(entry.to_payload())
    assert "producer_binding" not in payload
    assert "formula_id" not in payload
    assert "research_ref" not in payload
    assert "kind" not in payload
    signature = inspect.signature(resolve_dictionary_entry)
    assert "registrar" not in signature.parameters
    assert "producer" not in signature.parameters


def test_gap_0085_stays_unfilled_invalidation_is_stage_0_role() -> None:
    names: list[str] = []
    for path in _QML_RESEARCH.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names.extend(node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
    assert _ok(minted_mechanism_type_hits(names)) == ()
    for noun in GAP_0085_NOUNS:
        assert noun not in names
    cited = _cited_bytes(SWING_HIGH_PATH)
    entry = _ok(
        resolve_dictionary_entry(
            cited,
            file_path=SWING_HIGH_PATH,
            entry_id="swing-high",
        )
    )
    assert "invalidation" in entry.eligible_roles
    assert "InvalidationRule" not in names


def test_missing_entry_and_non_bytes_are_typed_refusals() -> None:
    cited = _cited_bytes(SWING_HIGH_PATH)
    missing = resolve_dictionary_entry(
        cited,
        file_path=SWING_HIGH_PATH,
        entry_id="not-a-seed-entry",
    )
    assert is_refusal(missing)
    assert missing.context["field"] == "id"
    assert missing.context["file_path"] == SWING_HIGH_PATH

    not_bytes = resolve_dictionary_entry(
        object(),
        file_path=SWING_HIGH_PATH,
        entry_id="swing-high",
    )
    assert is_refusal(not_bytes)
    assert not_bytes.context["field"] == "cited_bytes"
    assert "filesystem" in str(not_bytes.context["reason"])

    bad_utf8 = resolve_dictionary_entry(
        b"\xff\xfe",
        file_path=SWING_HIGH_PATH,
        entry_id="swing-high",
    )
    assert is_refusal(bad_utf8)

    mismatch = resolve_dictionary_entry(
        cited,
        file_path=SWING_HIGH_LOCATOR,
        entry_id="swing-low",
    )
    assert is_refusal(mismatch)
    assert mismatch.context["field"] == "id"
