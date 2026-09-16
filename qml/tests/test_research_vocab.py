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


def _resolve(cited: bytes, file_path: str, entry_id: str | None = None) -> DictionaryEntry:
    if entry_id is None:
        return _ok(resolve_dictionary_entry(cited, file_path=file_path))
    return _ok(resolve_dictionary_entry(cited, file_path=file_path, entry_id=entry_id))


def _swing_high() -> DictionaryEntry:
    return _resolve(_cited_bytes(SWING_HIGH_PATH), SWING_HIGH_PATH, "swing-high")


def _import_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
        return [node.module]
    return []


def _is_open_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open"


def _name_is_banned(name: str, banned: frozenset[str]) -> bool:
    return name in banned or any(name.startswith(item + ".") for item in banned)


def _node_ban_hits(path: Path, node: ast.AST, banned: frozenset[str]) -> list[str]:
    if _is_open_call(node):
        return [f"{path}: open()"]
    return [
        f"{path}: imports {name}" for name in _import_names(node) if _name_is_banned(name, banned)
    ]


def _file_ban_violations(path: Path, banned: frozenset[str]) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        found.extend(_node_ban_hits(path, node, banned))
    return found


def _research_ban_violations(banned: frozenset[str]) -> list[str]:
    found: list[str] = []
    for path in sorted(_QML_RESEARCH.rglob("*.py")):
        found.extend(_file_ban_violations(path, banned))
    return found


def _class_names_in_research() -> list[str]:
    names: list[str] = []
    for path in _QML_RESEARCH.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names.extend(node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
    return names


def _assert_collision_refusals(location_bytes: bytes) -> None:
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


def _resolve_sweep_trio() -> tuple[DictionaryEntry, DictionaryEntry, DictionaryEntry]:
    location = _resolve(
        _cited_bytes(_path_of(LIQUIDITY_SWEEP_LOCATION)),
        _path_of(LIQUIDITY_SWEEP_LOCATION),
        "liquidity-sweep",
    )
    context = _resolve(
        _cited_bytes(_path_of(LIQUIDITY_SWEEP_CONTEXT)),
        LIQUIDITY_SWEEP_CONTEXT,
    )
    triggers = _resolve(
        _cited_bytes(_path_of(LIQUIDITY_SWEEP_TRIGGERS)),
        LIQUIDITY_SWEEP_TRIGGERS,
    )
    return location, context, triggers


def _assert_sweep_identities_distinct(
    location: DictionaryEntry,
    context: DictionaryEntry,
    triggers: DictionaryEntry,
) -> None:
    assert location.identity() != context.identity()
    assert location.identity() != triggers.identity()
    assert location.id == context.id == triggers.id == "liquidity-sweep"
    assert location.fields["family"] != context.fields["family"]
    assert "invalidation" not in location.eligible_roles
    assert "invalidation" in context.eligible_roles


def _assert_concatenated_collision(location_bytes: bytes, context_bytes: bytes) -> None:
    colliding = resolve_dictionary_entry(
        location_bytes + b"\n" + context_bytes,
        file_path=_path_of(LIQUIDITY_SWEEP_LOCATION),
        entry_id="liquidity-sweep",
    )
    assert is_refusal(colliding)
    assert colliding.context["field"] == "id"
    assert colliding.context["id"] == "liquidity-sweep"
    assert colliding.context["file_path"] == _path_of(LIQUIDITY_SWEEP_LOCATION)
    assert colliding.context["occurrences"] == 2


def _assert_swing_high_fields(entry: DictionaryEntry) -> None:
    assert entry.title == "Swing High"
    assert tuple(entry.fields) == DICTIONARY_FIELDS
    assert len(entry.fields) == 12
    assert entry.fields["family"] == "Swing points & structural ranges"
    assert "pivot high" in entry.fields["aliases"]
    assert "local upper turning point" in entry.fields["definition"]
    assert "OHLC bar series" in entry.fields["observable_inputs"]


def _assert_no_dna_keys(entry: DictionaryEntry) -> None:
    payload = dict(entry.to_payload())
    assert payload["id"] == "swing-high"
    assert payload["file_path"] == SWING_HIGH_PATH
    assert "research_ref" not in payload
    for key in _DNA_KEYS:
        assert key not in payload
        assert key not in entry.fields


def test_swing_high_twelve_field_record_from_host_passed_bytes() -> None:
    entry = _swing_high()
    assert isinstance(entry, DictionaryEntry)
    assert entry.identity() == (SWING_HIGH_PATH, "swing-high")
    assert entry.id == "swing-high"
    assert entry.file_path == SWING_HIGH_PATH
    _assert_swing_high_fields(entry)
    _assert_no_dna_keys(entry)


def test_swing_high_eligible_roles_include_location_trigger_invalidation() -> None:
    entry = _resolve(_cited_bytes(SWING_HIGH_PATH), SWING_HIGH_LOCATOR)
    for role in ("location", "trigger", "invalidation", "context", "confirmation"):
        assert role in entry.eligible_roles
    assert "InvalidationRule" not in entry.eligible_roles
    assert entry.fields["eligible_roles"].startswith("location")


def test_collision_resolution_uses_file_path_and_id() -> None:
    location_bytes = _cited_bytes(_path_of(LIQUIDITY_SWEEP_LOCATION))
    context_bytes = _cited_bytes(_path_of(LIQUIDITY_SWEEP_CONTEXT))
    _assert_collision_refusals(location_bytes)
    location, context, triggers = _resolve_sweep_trio()
    _assert_sweep_identities_distinct(location, context, triggers)
    _assert_concatenated_collision(location_bytes, context_bytes)


def test_helper_performs_no_filesystem_io_threads_or_process() -> None:
    source = inspect.getsource(resolve_dictionary_entry)
    assert "open(" not in source
    assert _research_ban_violations(_BANNED_IMPORTS) == []


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
    entry = _resolve(
        cast("bytes", adapter_payload["content"]),
        cast("str", adapter_payload["locator"]),
    )
    assert entry.fields["family"]
    assert "location" in entry.eligible_roles


def _assert_research_exports_have_no_registry_surface() -> None:
    assert "Confluence" not in research.__all__
    assert "confluence" not in research.__all__
    for name in (
        "Confluence",
        "confluence",
        "research_ref",
        "mint_research_ref",
        "register_dictionary_entry",
        "mint_producer",
    ):
        assert not hasattr(research, name)


def test_does_not_register_registry_row_or_mint_ct16_or_research_ref() -> None:
    _assert_research_exports_have_no_registry_surface()
    payload = dict(_swing_high().to_payload())
    for key in ("producer_binding", "formula_id", "research_ref", "kind"):
        assert key not in payload
    signature = inspect.signature(resolve_dictionary_entry)
    assert "registrar" not in signature.parameters
    assert "producer" not in signature.parameters


def test_gap_0085_stays_unfilled_invalidation_is_stage_0_role() -> None:
    names = _class_names_in_research()
    assert _ok(minted_mechanism_type_hits(names)) == ()
    for noun in GAP_0085_NOUNS:
        assert noun not in names
    entry = _swing_high()
    assert "invalidation" in entry.eligible_roles
    assert "InvalidationRule" not in names


def _assert_missing_and_bad_buffers() -> None:
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
    assert is_refusal(
        resolve_dictionary_entry(
            b"\xff\xfe",
            file_path=SWING_HIGH_PATH,
            entry_id="swing-high",
        )
    )


def test_missing_entry_and_non_bytes_are_typed_refusals() -> None:
    _assert_missing_and_bad_buffers()
    mismatch = resolve_dictionary_entry(
        _cited_bytes(SWING_HIGH_PATH),
        file_path=SWING_HIGH_LOCATOR,
        entry_id="swing-low",
    )
    assert is_refusal(mismatch)
    assert mismatch.context["field"] == "id"
