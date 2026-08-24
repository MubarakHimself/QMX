"""Story 13.3 — Book and BMS config fragments as derived fp1 artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import FrozenInstanceError
from typing import TypeVar

from qmb.config import (
    BMS_NAMESPACES,
    BMS_RECORD_KIND,
    BOOK_NAMESPACES,
    BOOK_RECORD_KIND,
    CONFIG_FRAGMENT_CLASS,
    FRAGMENT_FORMAT_VERSION,
    FRAGMENT_FORMAT_VERSION_1,
    FRAGMENT_KNOWN_FORMAT_VERSIONS,
    FRAGMENT_LINEAGE_EDGE_TYPE,
    SOURCE_BMS,
    SOURCE_BOOK,
    SOURCE_PRESET,
    ConfigFragment,
    fragment_identity,
    materialize_bms_fragment,
    materialize_book_fragment,
    materialize_condition_preset,
)
from qmb.config.fragments import BMS_SECTION_NAMESPACE, BOOK_SECTION_NAMESPACE
from qmb.doors import api
from qmb.registryread import (
    AsOfSet,
    DatedPointer,
    PassiveHub,
    RegistryFragment,
    RegistryReadPort,
)
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import Money, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RESERVED_KIND_NAMES, EdgeType, KindRegistry, RegistrationRecord
from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BOOK_FORMAT_VERSION_1,
    BmsDefinition,
    BookDefinition,
)

import qmb

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer(stream: str = "config-fragment", machine: str = "node-a") -> WriterId:
    return _ok(WriterId.try_create(machine, "authoring", stream, "boot-1"))


def _money_variable(name: str, minor: int) -> TemplateVariable:
    return _ok(
        TemplateVariable.try_create(
            name,
            UnitKind.MONEY,
            Money(value=minor, currency="USD", scale=2),
            UiEditability.UI_EDITABLE,
            AdmissionImpact.RESIGN,
        )
    )


def _section(name: str, variable: TemplateVariable) -> TemplateSection:
    return _ok(TemplateSection.try_create(name, {variable.name: variable}))


def _book(
    *,
    include_unmapped: bool = True,
    format_version: int = BOOK_CONTRACT_FORMAT_VERSION,
) -> BookDefinition:
    sections = {
        "admission_bar": _section("admission_bar", _money_variable("bar_floor", 1)),
        "footprint_requirements": _section(
            "footprint_requirements", _money_variable("min_bars", 1)
        ),
        "money_rules": _section("money_rules", _money_variable("loss_floor", 800_000)),
        "paper": _section("paper", _money_variable("starting_balance", 10_000)),
        "exit_policy": _section("exit_policy", _money_variable("q", 100)),
    }
    if include_unmapped:
        sections["charter"] = _section("charter", _money_variable("headline", 1))
        sections["control_policy"] = _section(
            "control_policy", _money_variable("kill_line_value", 800_000)
        )
    return _ok(BookDefinition.try_create(format_version, "USD", sections))


def _bms(*, include_unmapped: bool = True) -> BmsDefinition:
    sections = {
        "accounting_rules": _section("accounting_rules", _money_variable("numeraire_unit", 1)),
        "constraints": _section("constraints", _money_variable("exposure_ceiling", 50_000)),
        "control_rank_table": _section("control_rank_table", _money_variable("rank_unit", 1)),
        "ksa_policy": _section("ksa_policy", _money_variable("posture", 1)),
        "reporting": _section("reporting", _money_variable("cadence", 1)),
    }
    if include_unmapped:
        sections["charter"] = _section("charter", _money_variable("purpose", 1))
        sections["admission_bar"] = _section("admission_bar", _money_variable("bms_bar", 1))
    return _ok(BmsDefinition.try_create(BMS_CONTRACT_FORMAT_VERSION, sections))


def _record(kind: str, definition: BookDefinition | BmsDefinition) -> RegistrationRecord:
    stamped = _ok(definition.fingerprint())
    return _ok(
        RegistrationRecord.try_create(
            kind,
            definition.contract_format_version,
            (stamped,),
            definition.fp1_identity(),
            _writer(kind),
            0,
            _instant(),
        )
    )


def _port(
    records: tuple[RegistrationRecord, ...],
    *,
    fragments: tuple[RegistryFragment, ...] = (),
    pointers: tuple[DatedPointer, ...] = (),
) -> RegistryReadPort:
    as_of = _ok(
        AsOfSet.try_create(
            _instant(),
            records=records,
            fragments=fragments,
            pointers=pointers,
        )
    )
    hub = _ok(PassiveHub.try_create((as_of,)))
    return _ok(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY))


def test_namespaces_are_disjoint_by_construction() -> None:
    assert BOOK_NAMESPACES.isdisjoint(BMS_NAMESPACES)
    assert frozenset({"admission", "sizing", "exit-door"}) == BOOK_NAMESPACES
    assert frozenset({"accounting", "constraints", "kill-line", "reporting"}) == BMS_NAMESPACES
    assert set(BOOK_SECTION_NAMESPACE.values()) <= BOOK_NAMESPACES
    assert set(BMS_SECTION_NAMESPACE.values()) <= BMS_NAMESPACES
    assert set(BOOK_SECTION_NAMESPACE).isdisjoint(set(BMS_SECTION_NAMESPACE))
    assert "admission" not in set(BMS_SECTION_NAMESPACE.values())
    assert "kill-line" not in set(BOOK_SECTION_NAMESPACE.values())


def test_book_fragment_is_derived_with_occurrence_of_lineage() -> None:
    book = _book()
    record = _record(BOOK_RECORD_KIND, book)
    pointer = _ok(DatedPointer.try_create("scalping", record.stable_id, _instant()))
    port = _port((record,), pointers=(pointer,))
    fragment = _ok(materialize_book_fragment(port, "scalping", _writer()))
    source = _ok(book.fingerprint())
    assert fragment.source_kind == SOURCE_BOOK
    assert fragment.source_fp1 == source
    assert fragment.format_version == FRAGMENT_FORMAT_VERSION == FRAGMENT_FORMAT_VERSION_1
    assert fragment.fingerprint.value.startswith("fp1:sha256:")
    assert fragment.lineage is not None
    assert fragment.lineage.edge_type is EdgeType.OCCURRENCE_OF
    assert fragment.lineage.edge_type is FRAGMENT_LINEAGE_EDGE_TYPE
    assert fragment.lineage.from_ref == fragment.fingerprint
    assert fragment.lineage.to_ref == source
    assert "admission" in fragment.keys
    assert "sizing" in fragment.keys
    assert "exit-door" in fragment.keys
    assert "charter" not in fragment.keys
    assert "kill-line" not in fragment.keys
    assert "control_policy" not in fragment.keys
    sizing = fragment.keys["sizing"]
    assert isinstance(sizing, Mapping)
    assert sizing["accounting_currency"] == "USD"
    identity = fragment.fp1_identity()
    assert identity["class"] == CONFIG_FRAGMENT_CLASS
    assert "lineage" not in identity
    assert qmb.__version__ not in str(identity)
    assert _ok(fingerprint(identity)) == fragment.fingerprint


def test_bms_fragment_is_derived_with_ct27_lineage() -> None:
    bms = _bms()
    record = _record(BMS_RECORD_KIND, bms)
    port = _port((record,))
    fragment = _ok(materialize_bms_fragment(port, record.stable_id, _writer()))
    source = _ok(bms.fingerprint())
    assert fragment.source_kind == SOURCE_BMS
    assert fragment.source_fp1 == source
    assert fragment.lineage is not None
    assert fragment.lineage.edge_type is EdgeType.OCCURRENCE_OF
    assert fragment.lineage.to_ref == source
    assert "accounting" in fragment.keys
    assert "constraints" in fragment.keys
    assert "kill-line" in fragment.keys
    assert "reporting" in fragment.keys
    assert "admission" not in fragment.keys
    assert "charter" not in fragment.keys
    assert "admission_bar" not in fragment.keys


def test_book_and_bms_fragment_keys_are_disjoint() -> None:
    book = _book()
    bms = _bms()
    book_record = _record(BOOK_RECORD_KIND, book)
    bms_record = _record(BMS_RECORD_KIND, bms)
    port = _port((book_record, bms_record))
    book_fragment = _ok(materialize_book_fragment(port, book_record.stable_id, _writer()))
    bms_fragment = _ok(materialize_bms_fragment(port, bms_record.stable_id, _writer()))
    assert set(book_fragment.keys) <= BOOK_NAMESPACES
    assert set(bms_fragment.keys) <= BMS_NAMESPACES
    assert set(book_fragment.keys).isdisjoint(bms_fragment.keys)


def test_fragment_is_not_a_registry_kind() -> None:
    assert CONFIG_FRAGMENT_CLASS not in RESERVED_KIND_NAMES
    kinds = KindRegistry()
    missing = kinds.contract_for(CONFIG_FRAGMENT_CLASS)
    assert is_refusal(missing)
    assert is_refusal(kinds.contract_for("config-fragment"))
    book = _book()
    record = _record(BOOK_RECORD_KIND, book)
    fragment = _ok(materialize_book_fragment(_port((record,)), record.stable_id, _writer()))
    envelope = _ok(fragment.as_registry_fragment())
    assert isinstance(envelope, RegistryFragment)
    assert envelope.source_fp1 == fragment.source_fp1
    reread = _ok(ConfigFragment.try_read(envelope.body))
    assert reread.fingerprint == fragment.fingerprint


def test_old_fragments_stay_readable_forever() -> None:
    book = _book(format_version=BOOK_FORMAT_VERSION_1)
    record = _record(BOOK_RECORD_KIND, book)
    fragment = _ok(materialize_book_fragment(_port((record,)), record.stable_id, _writer()))
    assert fragment.format_version == FRAGMENT_FORMAT_VERSION_1
    assert FRAGMENT_FORMAT_VERSION_1 in FRAGMENT_KNOWN_FORMAT_VERSIONS
    later_reader = _ok(ConfigFragment.try_read(fragment.fp1_identity(), reader_format_version=2))
    assert later_reader.fingerprint == fragment.fingerprint
    tampered = dict(fragment.fp1_identity())
    tampered["format_version"] = 2
    refused = ConfigFragment.try_read(tampered, reader_format_version=1)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    unknown = ConfigFragment.try_read(tampered, reader_format_version=2)
    assert is_refusal(unknown)
    assert unknown.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_named_condition_preset_is_a_config_fragment() -> None:
    book = _book()
    record = _record(BOOK_RECORD_KIND, book)
    pointer = _ok(DatedPointer.try_create("scalping", record.stable_id, _instant()))
    port = _port((record,), pointers=(pointer,))
    preset = _ok(
        materialize_condition_preset(
            port,
            "scalping",
            _writer(),
            name="stress-spread",
            keys={"spread-schedule": {"name": "stress-spread", "widening_bps": 20}},
        )
    )
    assert preset.source_kind == SOURCE_PRESET
    assert preset.preset_name == "stress-spread"
    assert preset.format_version == FRAGMENT_FORMAT_VERSION
    assert preset.lineage is not None
    assert preset.lineage.edge_type is EdgeType.OCCURRENCE_OF
    assert preset.lineage.to_ref == _ok(book.fingerprint())
    assert preset.fp1_identity()["preset_name"] == "stress-spread"
    again = _ok(
        materialize_condition_preset(
            port,
            "scalping",
            _writer(machine="node-b"),
            name="stress-spread",
            keys={"spread-schedule": {"name": "stress-spread", "widening_bps": 20}},
        )
    )
    assert again.fingerprint == preset.fingerprint
    assert again.lineage is not None
    assert preset.lineage is not None
    assert again.lineage.edge_fingerprint != preset.lineage.edge_fingerprint


def test_writer_is_excluded_from_fragment_identity() -> None:
    book = _book()
    record = _record(BOOK_RECORD_KIND, book)
    port = _port((record,))
    first = _ok(materialize_book_fragment(port, record.stable_id, _writer(machine="node-a")))
    second = _ok(materialize_book_fragment(port, record.stable_id, _writer(machine="node-b")))
    assert first.fingerprint == second.fingerprint
    assert first.lineage is not None and second.lineage is not None
    assert first.lineage.edge_fingerprint != second.lineage.edge_fingerprint


def test_materialize_refuses_wrong_kind_and_free_hand_fragment() -> None:
    book = _book()
    bms = _bms()
    book_record = _record(BOOK_RECORD_KIND, book)
    bms_record = _record(BMS_RECORD_KIND, bms)
    port = _port((book_record, bms_record))
    wrong = materialize_book_fragment(port, bms_record.stable_id, _writer())
    assert is_refusal(wrong)
    assert wrong.category is RefusalCategory.INVALID_INPUT
    fragment = _ok(materialize_book_fragment(port, book_record.stable_id, _writer()))
    envelope = _ok(fragment.as_registry_fragment())
    with_frag = _port((book_record,), fragments=(envelope,))
    free_hand = materialize_book_fragment(with_frag, envelope.fingerprint, _writer())
    assert is_refusal(free_hand)
    assert free_hand.category is RefusalCategory.INVALID_INPUT
    named = materialize_book_fragment(port, "scalping@1", _writer())
    assert is_refusal(named)
    assert named.category is RefusalCategory.INVALID_INPUT


def test_preset_refuses_mixed_namespaces_and_floats() -> None:
    book = _book()
    record = _record(BOOK_RECORD_KIND, book)
    port = _port((record,))
    mixed = materialize_condition_preset(
        port,
        record.stable_id,
        _writer(),
        name="mixed",
        keys={"admission": {"x": 1}, "accounting": {"y": 1}},
    )
    assert is_refusal(mixed)
    assert mixed.category is RefusalCategory.INVALID_INPUT
    floated = materialize_condition_preset(
        port,
        record.stable_id,
        _writer(),
        name="stress-spread",
        keys={"spread": 1.5},
    )
    assert is_refusal(floated)
    assert floated.category is RefusalCategory.INVALID_INPUT
    blank = materialize_condition_preset(
        port, record.stable_id, _writer(), name="  ", keys={"spread-schedule": {"n": 1}}
    )
    assert is_refusal(blank)


def test_materialize_passthrough_port_refusals_and_bad_args() -> None:
    book = _book()
    record = _record(BOOK_RECORD_KIND, book)
    port = _port((record,))
    missing = materialize_book_fragment(port, "unknown", _writer())
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    bad_port = materialize_book_fragment("port", record.stable_id, _writer())
    assert is_refusal(bad_port)
    assert bad_port.category is RefusalCategory.INVALID_INPUT
    bad_writer = materialize_book_fragment(port, record.stable_id, "writer")
    assert is_refusal(bad_writer)
    assert is_refusal(materialize_bms_fragment("port", record.stable_id, _writer()))
    assert is_refusal(materialize_bms_fragment(port, record.stable_id, "writer"))
    assert is_refusal(
        materialize_condition_preset("port", record.stable_id, _writer(), name="p", keys={})
    )
    assert is_refusal(
        materialize_condition_preset(port, record.stable_id, "writer", name="p", keys={})
    )
    assert is_refusal(
        materialize_condition_preset(port, record.stable_id, _writer(), name="p", keys="body")
    )


def test_malformed_definition_body_is_refused() -> None:
    stub = _ok(
        RegistrationRecord.try_create(
            BOOK_RECORD_KIND,
            1,
            [],
            {"alias": "scalping", "note": "v1"},
            _writer("book-definition"),
            0,
            _instant(),
        )
    )
    port = _port((stub,))
    refused = materialize_book_fragment(port, stub.stable_id, _writer())
    assert is_refusal(refused)
    no_currency = _ok(
        RegistrationRecord.try_create(
            BOOK_RECORD_KIND,
            2,
            [],
            {"class": "book-definition", "sections": {}},
            _writer("book-definition"),
            1,
            _instant(),
        )
    )
    missing_ccy = materialize_book_fragment(_port((no_currency,)), no_currency.stable_id, _writer())
    assert is_refusal(missing_ccy)
    no_sections = _ok(
        RegistrationRecord.try_create(
            BMS_RECORD_KIND,
            1,
            [],
            {"class": "bms-definition", "note": "no-sections"},
            _writer("bms-definition"),
            0,
            _instant(),
        )
    )
    missing_sections = materialize_bms_fragment(
        _port((no_sections,)), no_sections.stable_id, _writer()
    )
    assert is_refusal(missing_sections)


def test_try_read_validates_schema() -> None:
    book = _book()
    record = _record(BOOK_RECORD_KIND, book)
    fragment = _ok(materialize_book_fragment(_port((record,)), record.stable_id, _writer()))
    assert is_refusal(ConfigFragment.try_read("body"))
    assert is_refusal(ConfigFragment.try_read({"class": "other"}))
    bool_version = {"class": CONFIG_FRAGMENT_CLASS, "format_version": True}
    assert is_refusal(ConfigFragment.try_read(bool_version))
    identity = fragment.fp1_identity()
    identity["keys"] = "nope"
    assert is_refusal(ConfigFragment.try_read(identity))
    mixed = fragment.fp1_identity()
    mixed["keys"] = {"admission": {"x": 1}, "accounting": {"y": 1}}
    assert is_refusal(ConfigFragment.try_read(mixed))
    extra = fragment.fp1_identity()
    extra["keys"] = {"admission": {"x": 1}, "not-owned": {"y": 1}}
    assert is_refusal(ConfigFragment.try_read(extra))
    with_preset = fragment.fp1_identity()
    with_preset["preset_name"] = "stress-spread"
    assert is_refusal(ConfigFragment.try_read(with_preset))
    assert is_refusal(ConfigFragment.try_read(fragment.fp1_identity(), reader_format_version="1"))
    bad_source = fragment.fp1_identity()
    bad_source["source_kind"] = "other"
    assert is_refusal(ConfigFragment.try_read(bad_source))
    bad_fp = fragment.fp1_identity()
    bad_fp["source_fp1"] = "not-fp1"
    assert is_refusal(ConfigFragment.try_read(bad_fp))
    preset_id = {
        "class": CONFIG_FRAGMENT_CLASS,
        "format_version": 1,
        "keys": {"spread-schedule": {"n": 1}},
        "source_fp1": fragment.source_fp1.value,
        "source_kind": SOURCE_PRESET,
    }
    assert is_refusal(ConfigFragment.try_read(preset_id))
    preset_id["preset_name"] = "stress-spread"
    assert is_ok(ConfigFragment.try_read(preset_id))


def test_fragment_is_immutable_and_api_matches() -> None:
    book = _book()
    record = _record(BOOK_RECORD_KIND, book)
    fragment = _ok(materialize_book_fragment(_port((record,)), record.stable_id, _writer()))
    try:
        fragment.keys = {}  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("config fragment mutated")
    assert api.ConfigFragment is qmb.ConfigFragment
    assert api.materialize_book_fragment is qmb.materialize_book_fragment
    assert api.materialize_bms_fragment is qmb.materialize_bms_fragment
    assert api.materialize_condition_preset is qmb.materialize_condition_preset
    assert api.BOOK_NAMESPACES == qmb.BOOK_NAMESPACES == BOOK_NAMESPACES
    assert api.BMS_NAMESPACES == qmb.BMS_NAMESPACES
    assert "version" not in fragment_identity()
    assert qmb.__version__ not in fragment_identity().values()
    assert fragment_identity()["class"] == CONFIG_FRAGMENT_CLASS


def test_preset_from_non_definition_source_cites_record_fp1() -> None:
    stub = _ok(
        RegistrationRecord.try_create(
            "workspace-defaults",
            1,
            [],
            {"alias": "workspace"},
            _writer("workspace-defaults"),
            0,
            _instant(),
        )
    )
    port = _port((stub,))
    preset = _ok(
        materialize_condition_preset(
            port,
            stub.stable_id,
            _writer(),
            name="stress-spread",
            keys={"spread-schedule": {"name": "stress-spread"}},
        )
    )
    assert preset.source_fp1 == stub.stable_id


def test_bad_section_payload_is_refused() -> None:
    bad_sections = _ok(
        RegistrationRecord.try_create(
            BOOK_RECORD_KIND,
            2,
            [],
            {
                "class": "book-definition",
                "accounting_currency": "USD",
                "sections": {"money_rules": "not-a-mapping"},
            },
            _writer("book-definition"),
            0,
            _instant(),
        )
    )
    refused = materialize_book_fragment(_port((bad_sections,)), bad_sections.stable_id, _writer())
    assert is_refusal(refused)
    numbered = RegistrationRecord.try_create(
        BMS_RECORD_KIND,
        1,
        [],
        {
            "class": "bms-definition",
            "sections": {1: {"name": "accounting_rules"}},
        },
        _writer("bms-definition"),
        0,
        _instant(),
    )
    assert is_refusal(numbered)


def test_try_read_accepts_fingerprint_object_and_attached_lineage() -> None:
    book = _book()
    record = _record(BOOK_RECORD_KIND, book)
    fragment = _ok(materialize_book_fragment(_port((record,)), record.stable_id, _writer()))
    identity = fragment.fp1_identity()
    identity["source_fp1"] = fragment.source_fp1
    reread = _ok(ConfigFragment.try_read(identity, lineage=fragment.lineage))
    assert reread.fingerprint == fragment.fingerprint
    assert reread.lineage is fragment.lineage
    zero = fragment.fp1_identity()
    zero["format_version"] = 0
    assert is_refusal(ConfigFragment.try_read(zero))


def test_preset_falls_back_when_source_body_is_not_a_definition() -> None:
    stub = _ok(
        RegistrationRecord.try_create(
            BOOK_RECORD_KIND,
            1,
            [],
            {"class": "not-a-definition", "alias": "scalping"},
            _writer("book-definition"),
            0,
            _instant(),
        )
    )
    preset = _ok(
        materialize_condition_preset(
            _port((stub,)),
            stub.stable_id,
            _writer(),
            name="stress-spread",
            keys={"spread-schedule": {"name": "stress-spread"}},
        )
    )
    assert preset.source_fp1 == stub.stable_id
