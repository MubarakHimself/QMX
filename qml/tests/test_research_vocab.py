"""Story 49.5 — vocabulary helper resolves swing-high from host-passed cited bytes."""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import cast

from qmf.core.refusal import RefusalCategory, is_refusal
from qml.generation import GAP_0085_NOUNS, minted_mechanism_type_hits
from qml.research import DICTIONARY_FIELDS, DictionaryEntry, resolve_dictionary_entry

from qml import research


def _load_research_vocab_helpers() -> ModuleType:
    path = Path(__file__).resolve().parent / "research_vocab_helpers.py"
    name = "qml.tests.research_vocab_helpers"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_helpers = _load_research_vocab_helpers()
SWING_HIGH_PATH = _helpers.SWING_HIGH_PATH
cited_bytes = _helpers.cited_bytes
class_names_in_research = _helpers.class_names_in_research
ok = _helpers.ok
path_of = _helpers.path_of
research_ban_violations = _helpers.research_ban_violations
resolve = _helpers.resolve
swing_high = _helpers.swing_high

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


def _assert_collision_refusals(location_bytes: bytes) -> None:
    missing_path = resolve_dictionary_entry(
        location_bytes, file_path="", entry_id="liquidity-sweep"
    )
    assert is_refusal(missing_path)
    assert missing_path.category is RefusalCategory.INVALID_INPUT
    assert missing_path.context["field"] == "file_path"
    assert "file_path" in str(missing_path.context["reason"])

    missing_id = resolve_dictionary_entry(
        location_bytes, file_path=path_of(LIQUIDITY_SWEEP_LOCATION)
    )
    assert is_refusal(missing_id)
    assert missing_id.context["field"] == "id"


def _resolve_sweep_trio() -> tuple[DictionaryEntry, DictionaryEntry, DictionaryEntry]:
    location = resolve(
        cited_bytes(path_of(LIQUIDITY_SWEEP_LOCATION)),
        path_of(LIQUIDITY_SWEEP_LOCATION),
        "liquidity-sweep",
    )
    context = resolve(
        cited_bytes(path_of(LIQUIDITY_SWEEP_CONTEXT)),
        LIQUIDITY_SWEEP_CONTEXT,
    )
    triggers = resolve(
        cited_bytes(path_of(LIQUIDITY_SWEEP_TRIGGERS)),
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
        file_path=path_of(LIQUIDITY_SWEEP_LOCATION),
        entry_id="liquidity-sweep",
    )
    assert is_refusal(colliding)
    assert colliding.context["field"] == "id"
    assert colliding.context["id"] == "liquidity-sweep"
    assert colliding.context["file_path"] == path_of(LIQUIDITY_SWEEP_LOCATION)
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
    entry = swing_high()
    assert isinstance(entry, DictionaryEntry)
    assert entry.identity() == (SWING_HIGH_PATH, "swing-high")
    assert entry.id == "swing-high"
    assert entry.file_path == SWING_HIGH_PATH
    _assert_swing_high_fields(entry)
    _assert_no_dna_keys(entry)


def test_swing_high_eligible_roles_include_location_trigger_invalidation() -> None:
    entry = resolve(cited_bytes(SWING_HIGH_PATH), SWING_HIGH_LOCATOR)
    for role in ("location", "trigger", "invalidation", "context", "confirmation"):
        assert role in entry.eligible_roles
    assert "InvalidationRule" not in entry.eligible_roles
    assert entry.fields["eligible_roles"].startswith("location")


def test_collision_resolution_uses_file_path_and_id() -> None:
    location_bytes = cited_bytes(path_of(LIQUIDITY_SWEEP_LOCATION))
    context_bytes = cited_bytes(path_of(LIQUIDITY_SWEEP_CONTEXT))
    _assert_collision_refusals(location_bytes)
    location, context, triggers = _resolve_sweep_trio()
    _assert_sweep_identities_distinct(location, context, triggers)
    _assert_concatenated_collision(location_bytes, context_bytes)


def test_helper_performs_no_filesystem_io_threads_or_process() -> None:
    source = inspect.getsource(resolve_dictionary_entry)
    assert "open(" not in source
    assert research_ban_violations(_BANNED_IMPORTS) == []


def test_meaning_is_computed_only_by_qml_research() -> None:
    cited = cited_bytes(SWING_HIGH_PATH)
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
    entry = resolve(
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
    payload = dict(swing_high().to_payload())
    for key in ("producer_binding", "formula_id", "research_ref", "kind"):
        assert key not in payload
    signature = inspect.signature(resolve_dictionary_entry)
    assert "registrar" not in signature.parameters
    assert "producer" not in signature.parameters


def test_gap_0085_stays_unfilled_invalidation_is_stage_0_role() -> None:
    names = class_names_in_research()
    assert ok(minted_mechanism_type_hits(names)) == ()
    for noun in GAP_0085_NOUNS:
        assert noun not in names
    entry = swing_high()
    assert "invalidation" in entry.eligible_roles
    assert "InvalidationRule" not in names


def _assert_missing_and_bad_buffers() -> None:
    cited = cited_bytes(SWING_HIGH_PATH)
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
        cited_bytes(SWING_HIGH_PATH),
        file_path=SWING_HIGH_LOCATOR,
        entry_id="swing-low",
    )
    assert is_refusal(mismatch)
    assert mismatch.context["field"] == "id"
