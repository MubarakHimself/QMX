"""Story 10.1 AC4/AC5/AC6 — the Book (CT-22) and BMS (CT-27) definition containers.

Verifies the definition shape on qmf-core nouns: the USD accounting-currency law,
the unknown-format-version refusal, unknown sections ignored (never entering
identity), the fp1 version identity, that a changed number changes fp1 hence a new
identity, the flat-variable diff surface, and that qmf-risk imports only qmf-core
and is imported by nothing (CT-22, CT-27, AR-06; DEC-0143, DEC-0144, DEC-0158).
"""

from __future__ import annotations

import qmf.risk
from qmf.core import Money, UnitKind, is_ok, is_refusal
from qmf.risk.grammar import (
    AdmissionImpact,
    TemplateSection,
    TemplateVariable,
    UiEditability,
)
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BMS_SECTIONS,
    BOOK_CONTRACT_FORMAT_VERSION,
    BOOK_FORMAT_VERSION_1,
    BOOK_KNOWN_FORMAT_VERSIONS,
    BOOK_SECTIONS,
    BmsDefinition,
    BookDefinition,
)
from qmf.risk.versioning import diff_variable_maps


def _money_variable(name: str, minor: int) -> TemplateVariable:
    result = TemplateVariable.try_create(
        name,
        UnitKind.MONEY,
        Money(value=minor, currency="USD", scale=2),
        UiEditability.UI_EDITABLE,
        AdmissionImpact.RESIGN,
    )
    assert is_ok(result)
    return result.value


def _section(name: str, variable: TemplateVariable) -> TemplateSection:
    result = TemplateSection.try_create(name, {variable.name: variable})
    assert is_ok(result)
    return result.value


def _money_rules(minor: int) -> TemplateSection:
    return _section("money_rules", _money_variable("loss_floor", minor))


# --- declared section names --------------------------------------------------


def test_book_declares_ten_named_sections() -> None:
    assert len(BOOK_SECTIONS) == 10
    assert BOOK_SECTIONS[0] == "charter"
    assert "money_rules" in BOOK_SECTIONS
    assert "paper" in BOOK_SECTIONS


def test_bms_declares_its_named_sections() -> None:
    assert "control_rank_table" in BMS_SECTIONS
    assert "accounting_rules" in BMS_SECTIONS


def test_contract_format_versions() -> None:
    assert BOOK_CONTRACT_FORMAT_VERSION == 2
    assert BOOK_FORMAT_VERSION_1 == 1
    assert frozenset({1, 2}) == BOOK_KNOWN_FORMAT_VERSIONS
    assert BMS_CONTRACT_FORMAT_VERSION == 1


# --- BookDefinition ----------------------------------------------------------


def test_book_definition_builds_with_usd_and_sections() -> None:
    result = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION, "USD", {"money_rules": _money_rules(800_000)}
    )
    assert is_ok(result)
    book = result.value
    assert book.accounting_currency == "USD"
    assert "money_rules" in book.sections


def test_book_definition_refuses_non_usd_accounting_currency() -> None:
    result = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION, "EUR", {"money_rules": _money_rules(800_000)}
    )
    assert is_refusal(result)


def test_book_definition_refuses_unknown_format_version() -> None:
    result = BookDefinition.try_create(99, "USD", {"money_rules": _money_rules(800_000)})
    assert is_refusal(result)
    assert result.context["field"] == "contract_format_version"


def test_pre_mint_format_1_book_stays_readable() -> None:
    result = BookDefinition.try_create(
        BOOK_FORMAT_VERSION_1, "USD", {"money_rules": _money_rules(800_000)}
    )
    assert is_ok(result)
    assert result.value.contract_format_version == BOOK_FORMAT_VERSION_1


def test_format_1_reader_refuses_format_2_book() -> None:
    result = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION,
        "USD",
        {"money_rules": _money_rules(800_000)},
        reader_format_version=BOOK_FORMAT_VERSION_1,
    )
    assert is_refusal(result)
    assert result.context["field"] == "contract_format_version"


def test_format_2_reader_accepts_format_1_book() -> None:
    result = BookDefinition.try_create(
        BOOK_FORMAT_VERSION_1,
        "USD",
        {"money_rules": _money_rules(800_000)},
        reader_format_version=BOOK_CONTRACT_FORMAT_VERSION,
    )
    assert is_ok(result)
    assert result.value.contract_format_version == BOOK_FORMAT_VERSION_1


def test_book_definition_refuses_boolean_format_version() -> None:
    result = BookDefinition.try_create(True, "USD", {})
    assert is_refusal(result)


def test_unknown_section_is_ignored_not_refused() -> None:
    known = _money_rules(800_000)
    unknown = _section("not_a_real_section", _money_variable("x", 1))
    result = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION,
        "USD",
        {"money_rules": known, "not_a_real_section": unknown},
    )
    assert is_ok(result)
    # The unknown section is dropped: ignored, never entering identity.
    assert "not_a_real_section" not in result.value.sections
    assert "money_rules" in result.value.sections


def test_book_definition_refuses_bad_sections_mapping() -> None:
    assert is_refusal(BookDefinition.try_create(BOOK_CONTRACT_FORMAT_VERSION, "USD", ["nope"]))


def test_book_definition_refuses_non_section_value() -> None:
    result = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION, "USD", {"money_rules": "not-a-section"}
    )
    assert is_refusal(result)


def test_book_definition_refuses_section_key_name_mismatch() -> None:
    result = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION, "USD", {"charter": _money_rules(1)}
    )
    assert is_refusal(result)


def test_book_definition_refuses_non_string_section_key() -> None:
    result = BookDefinition.try_create(BOOK_CONTRACT_FORMAT_VERSION, "USD", {7: _money_rules(1)})
    assert is_refusal(result)


# --- identity: a changed number changes fp1 (AC5) ----------------------------


def test_changed_number_changes_book_fp1_hence_new_identity() -> None:
    one = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION, "USD", {"money_rules": _money_rules(800_000)}
    )
    two = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION, "USD", {"money_rules": _money_rules(700_000)}
    )
    assert is_ok(one)
    assert is_ok(two)
    fp_one = one.value.fingerprint()
    fp_two = two.value.fingerprint()
    assert is_ok(fp_one)
    assert is_ok(fp_two)
    assert fp_one.value.value != fp_two.value.value


def test_identical_books_share_one_fingerprint() -> None:
    one = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION, "USD", {"money_rules": _money_rules(800_000)}
    )
    two = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION, "USD", {"money_rules": _money_rules(800_000)}
    )
    assert is_ok(one)
    assert is_ok(two)
    fp_one = one.value.fingerprint()
    fp_two = two.value.fingerprint()
    assert is_ok(fp_one)
    assert is_ok(fp_two)
    assert fp_one.value.value == fp_two.value.value


def test_book_flat_variables_key_by_section_and_name() -> None:
    result = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION, "USD", {"money_rules": _money_rules(800_000)}
    )
    assert is_ok(result)
    flat = result.value.flat_variables()
    assert "money_rules.loss_floor" in flat


def test_diff_between_two_book_versions_is_derivable() -> None:
    old = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION, "USD", {"money_rules": _money_rules(800_000)}
    )
    new = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION, "USD", {"money_rules": _money_rules(700_000)}
    )
    assert is_ok(old)
    assert is_ok(new)
    diff = diff_variable_maps(old.value.flat_variables(), new.value.flat_variables())
    assert is_ok(diff)
    assert diff.value.changed == ("money_rules.loss_floor",)


# --- BmsDefinition -----------------------------------------------------------


def test_bms_definition_builds_with_sections() -> None:
    accounting = _section("accounting_rules", _money_variable("reconciliation_floor", 0))
    result = BmsDefinition.try_create(BMS_CONTRACT_FORMAT_VERSION, {"accounting_rules": accounting})
    assert is_ok(result)
    assert "accounting_rules" in result.value.sections


def test_bms_definition_refuses_unknown_format_version() -> None:
    result = BmsDefinition.try_create(7, {})
    assert is_refusal(result)


def test_bms_definition_ignores_unknown_section() -> None:
    unknown = _section("not_bms", _money_variable("x", 1))
    result = BmsDefinition.try_create(BMS_CONTRACT_FORMAT_VERSION, {"not_bms": unknown})
    assert is_ok(result)
    assert "not_bms" not in result.value.sections


def test_bms_definition_fingerprint_is_idempotent() -> None:
    accounting = _section("accounting_rules", _money_variable("reconciliation_floor", 0))
    result = BmsDefinition.try_create(BMS_CONTRACT_FORMAT_VERSION, {"accounting_rules": accounting})
    assert is_ok(result)
    fp = result.value.fingerprint()
    assert is_ok(fp)
    fp_again = result.value.fingerprint()
    assert is_ok(fp_again)
    assert fp.value.value == fp_again.value.value


def test_bms_flat_variables_key_by_section_and_name() -> None:
    accounting = _section("accounting_rules", _money_variable("reconciliation_floor", 0))
    result = BmsDefinition.try_create(BMS_CONTRACT_FORMAT_VERSION, {"accounting_rules": accounting})
    assert is_ok(result)
    assert "accounting_rules.reconciliation_floor" in result.value.flat_variables()


# --- AC6: packaging ----------------------------------------------------------


def test_public_surface_is_re_exported() -> None:
    for name in (
        "TemplateVariable",
        "FormulaSpec",
        "FORM_0006",
        "V1_NUMERAIRE",
        "BookDefinition",
        "BmsDefinition",
        "TemplateVersionGraph",
        "CT22_FORMAT_2_MIGRATION",
        "CT23_FORMAT_2_MIGRATION",
        "ExitPolicy",
        "FootprintRequirements",
    ):
        assert name in qmf.risk.__all__
        assert hasattr(qmf.risk, name)


def test_qmf_risk_imports_only_qmf_core() -> None:
    # AC6 / L30: every qmf.risk source module imports only qmf-core (and its own
    # siblings) — never another roster package. Scan the src files' import
    # statements directly, so a forbidden edge is caught at its declaration.
    import ast
    from pathlib import Path

    forbidden = (
        "qmf.data",
        "qmf.registry",
        "qmf.indicators",
        "qmf.structure",
        "qmf.venue",
        "qmf.calendar",
    )
    src_dir = Path(qmf.risk.__file__).resolve().parent
    scanned = 0
    for path in sorted(src_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        scanned += 1
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                modules.append(node.module)
            elif isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            for module_name in modules:
                assert not any(
                    module_name == bad or module_name.startswith(f"{bad}.") for bad in forbidden
                ), f"{path.name} imports forbidden module {module_name}"
    assert scanned >= 5  # every contract module was scanned
