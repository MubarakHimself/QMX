"""Reference usage — Book/BMS config fragments as derived fp1 artifacts (Story 13.3).

Executable::

    python qmb/examples/config_fragments_usage.py

Shows the things B-3 / Story 13.3 pin down:

1. A CT-22 Book definition resolved through the registry-read port materializes
   a schema-validated, fingerprinted DERIVED fragment with a CT-07
   ``occurrence-of`` lineage edge back to the Book source — never a new
   registry kind, never free-hand-edited.
2. A CT-27 BMS definition materializes the same way, lineaged to the BMS source.
3. Book and BMS key namespaces are DISJOINT (Book: admission/sizing/exit-door;
   BMS: accounting/constraints/kill-line/reporting).
4. Fragments stamp an AD-5 integer format version; old fragments stay readable.
5. A named condition preset (stress-spread) is a config fragment like any other.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.config import (
    BMS_NAMESPACES,
    BOOK_NAMESPACES,
    CONFIG_FRAGMENT_CLASS,
    FRAGMENT_FORMAT_VERSION,
    ConfigFragment,
    materialize_bms_fragment,
    materialize_book_fragment,
    materialize_condition_preset,
)
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import Money, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.registry import RESERVED_KIND_NAMES, EdgeType, KindRegistry, RegistrationRecord
from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BmsDefinition,
    BookDefinition,
)

import qmb

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _writer(stream: str) -> WriterId:
    return _unwrap(
        WriterId.try_create("node-a", "authoring", stream, "boot-1"),
        "writer",
    )


def _money_variable(name: str, minor: int) -> TemplateVariable:
    return _unwrap(
        TemplateVariable.try_create(
            name,
            UnitKind.MONEY,
            Money(value=minor, currency="USD", scale=2),
            UiEditability.UI_EDITABLE,
            AdmissionImpact.RESIGN,
        ),
        f"variable {name}",
    )


def _section(name: str, variable: TemplateVariable) -> TemplateSection:
    return _unwrap(TemplateSection.try_create(name, {variable.name: variable}), f"section {name}")


def _book() -> BookDefinition:
    return _unwrap(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _money_variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _money_variable("loss_floor", 800_000)),
                "exit_policy": _section("exit_policy", _money_variable("q", 100)),
                "charter": _section("charter", _money_variable("headline", 1)),
            },
        ),
        "book definition",
    )


def _bms() -> BmsDefinition:
    return _unwrap(
        BmsDefinition.try_create(
            BMS_CONTRACT_FORMAT_VERSION,
            {
                "accounting_rules": _section(
                    "accounting_rules", _money_variable("numeraire_unit", 1)
                ),
                "constraints": _section("constraints", _money_variable("exposure_ceiling", 50_000)),
                "ksa_policy": _section("ksa_policy", _money_variable("posture", 1)),
                "reporting": _section("reporting", _money_variable("cadence", 1)),
            },
        ),
        "bms definition",
    )


def _record(kind: str, definition: BookDefinition | BmsDefinition) -> RegistrationRecord:
    stamped = _unwrap(definition.fingerprint(), f"{kind} fp1")
    return _unwrap(
        RegistrationRecord.try_create(
            kind,
            definition.contract_format_version,
            (stamped,),
            definition.fp1_identity(),
            _writer(kind),
            0,
            _instant(),
        ),
        f"{kind} record",
    )


def main() -> None:
    book = _book()
    bms = _bms()
    book_record = _record("book-definition", book)
    bms_record = _record("bms-definition", bms)
    as_of = _unwrap(
        AsOfSet.try_create(
            _instant(),
            records=(book_record, bms_record),
            pointers=(
                _unwrap(
                    DatedPointer.try_create("scalping", book_record.stable_id, _instant()),
                    "book pointer",
                ),
                _unwrap(
                    DatedPointer.try_create("account-bms", bms_record.stable_id, _instant()),
                    "bms pointer",
                ),
            ),
        ),
        "as-of set",
    )
    port = _unwrap(
        RegistryReadPort.try_create(
            _unwrap(PassiveHub.try_create((as_of,)), "hub"),
            stale_evidence_severity=_SEVERITY,
        ),
        "port",
    )

    book_fragment = _unwrap(
        materialize_book_fragment(port, "scalping", _writer("config-fragment")),
        "book fragment",
    )
    bms_fragment = _unwrap(
        materialize_bms_fragment(port, "account-bms", _writer("config-fragment")),
        "bms fragment",
    )
    assert book_fragment.source_kind == "book"
    assert bms_fragment.source_kind == "bms"
    assert book_fragment.format_version == FRAGMENT_FORMAT_VERSION
    book_fp = _unwrap(book.fingerprint(), "book fp1")
    assert book_fragment.source_fp1 == book_fp
    assert book_fragment.lineage is not None
    assert book_fragment.lineage.edge_type is EdgeType.OCCURRENCE_OF
    assert book_fragment.lineage.from_ref == book_fragment.fingerprint
    assert book_fragment.lineage.to_ref == book_fp
    print(f"book fragment cites source {book_fragment.source_fp1.value}")
    print(f"lineage {book_fragment.lineage.edge_type.value} -> CT-22")

    assert BOOK_NAMESPACES.isdisjoint(BMS_NAMESPACES)
    assert set(book_fragment.keys).issubset(BOOK_NAMESPACES)
    assert set(bms_fragment.keys).issubset(BMS_NAMESPACES)
    assert set(book_fragment.keys).isdisjoint(set(bms_fragment.keys))
    assert "admission" in book_fragment.keys
    assert "sizing" in book_fragment.keys
    assert "exit-door" in book_fragment.keys
    assert "charter" not in book_fragment.keys
    assert "accounting" in bms_fragment.keys
    assert "kill-line" in bms_fragment.keys
    assert "reporting" in bms_fragment.keys
    print("Book vs BMS namespaces: DISJOINT")

    assert CONFIG_FRAGMENT_CLASS not in RESERVED_KIND_NAMES
    kinds = KindRegistry()
    assert is_refusal(kinds.contract_for(CONFIG_FRAGMENT_CLASS))
    print("config-fragment is derived, not a registry kind")

    reread = _unwrap(
        ConfigFragment.try_read(
            book_fragment.fp1_identity(),
            reader_format_version=2,
        ),
        "format-1 re-read under a later reader",
    )
    assert reread.fingerprint == book_fragment.fingerprint
    print("format 1 stays readable after a later format version ships")

    preset = _unwrap(
        materialize_condition_preset(
            port,
            "scalping",
            _writer("config-fragment"),
            name="stress-spread",
            keys={"spread-schedule": {"name": "stress-spread", "widening_bps": 20}},
        ),
        "stress-spread preset",
    )
    assert preset.source_kind == "named-condition-preset"
    assert preset.preset_name == "stress-spread"
    assert preset.lineage is not None
    assert preset.lineage.to_ref == book_fp
    print("named condition preset stress-spread is a config fragment")

    envelope = _unwrap(book_fragment.as_registry_fragment(), "registry envelope")
    from_envelope = _unwrap(ConfigFragment.try_read(envelope.body), "envelope re-read")
    assert from_envelope.fingerprint == book_fragment.fingerprint
    identity = book_fragment.fp1_identity()
    assert "version" not in identity
    assert qmb.__version__ not in str(identity)
    derived = _unwrap(fingerprint(identity), "fragment fp1")
    assert derived == book_fragment.fingerprint
    print(f"qmb {qmb.__version__}")
    print("config fragments ok")


if __name__ == "__main__":
    main()
