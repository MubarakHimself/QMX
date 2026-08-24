"""Story 11.7 — CT-22 / CT-23 format-version-2 mints with migration notes.

Locks the AD-5 mint: CT-22 adds exactly three things, CT-23 adds exactly one
optional entry field, pre-mint format-1 artifacts stay readable forever, a
format-1 reader confronting format 2 refuses unsupported capability, and the
new admission-bar fields cannot land as a silent format-1 addition. Thresholds
behind those interfaces stay GAP-0048/GAP-0049 (DEC-0181, DEC-0182).
"""

from __future__ import annotations

from qmf.core import AccountRole, Duration, RefusalCategory, World, is_ok, is_refusal
from qmf.risk.admission_bar import EvidenceRequirements
from qmf.risk.door import (
    CT23_ACTIVE_FORMAT_VERSION,
    CT23_FORMAT_VERSION_1,
    CT23_KNOWN_FORMAT_VERSIONS,
)
from qmf.risk.migrations import (
    CT22_FORMAT_2_MIGRATION,
    CT23_FORMAT_2_MIGRATION,
    THRESHOLD_GAPS_BEHIND_NEW_ADMISSION_BAR_FIELDS,
)
from qmf.risk.templates import (
    BOOK_CONTRACT_FORMAT_VERSION,
    BOOK_FORMAT_VERSION_1,
    BOOK_KNOWN_FORMAT_VERSIONS,
    BookDefinition,
)


def test_ct22_mint_adds_exactly_three_things() -> None:
    note = CT22_FORMAT_2_MIGRATION
    assert note.contract_id == "CT-22"
    assert note.from_version == 1
    assert note.to_version == 2
    assert len(note.added) == 3
    joined = " ".join(note.added)
    assert "registered_conformant_bot_cite" in joined
    assert "canonical_assignment_evidence" in joined
    assert "catch_all_default_entry" in joined
    assert "footprint_requirements" in joined
    assert note.pre_mint_readable_versions == (1,)
    assert note.format_1_reader_on_newer == "unsupported capability"
    assert "GAP-0048" in note.notes
    assert "GAP-0049" in note.notes


def test_ct23_mint_adds_exactly_one_optional_entry_field() -> None:
    note = CT23_FORMAT_2_MIGRATION
    assert note.contract_id == "CT-23"
    assert note.from_version == 1
    assert note.to_version == 2
    assert note.added == ("entry.advisory_stop_proposal",)
    assert note.pre_mint_readable_versions == (1,)
    assert note.format_1_reader_on_newer == "unsupported capability"
    assert "Book-resolved" in note.notes
    assert "optional" in note.notes.lower()
    identity = note.fp1_identity()
    assert identity["class"] == "format-migration-note"
    assert identity == note.fp1_identity()


def test_active_versions_are_two_and_format_1_stays_known() -> None:
    assert BOOK_CONTRACT_FORMAT_VERSION == 2
    assert BOOK_FORMAT_VERSION_1 == 1
    assert frozenset({1, 2}) == BOOK_KNOWN_FORMAT_VERSIONS
    assert CT23_ACTIVE_FORMAT_VERSION == 2
    assert CT23_FORMAT_VERSION_1 == 1
    assert frozenset({1, 2}) == CT23_KNOWN_FORMAT_VERSIONS


def test_thresholds_behind_new_admission_bar_fields_stay_gap_0048_0049() -> None:
    assert THRESHOLD_GAPS_BEHIND_NEW_ADMISSION_BAR_FIELDS == ("GAP-0048", "GAP-0049")


def test_format_1_evidence_cannot_silently_add_the_two_bot_side_fields() -> None:
    # The two fields land ONLY through the format-2 mint. Asserting them at
    # format 1 is invalid input — a silent addition would let a format-1 parser
    # ignore them and admit the evidence they exist to refuse (DEC-0178).
    dur = Duration(value_ns=1)
    result = EvidenceRequirements.try_create(
        World.LIVE,
        AccountRole.LIVE,
        dur,
        {},
        registered_conformant_bot_cite=True,
        canonical_assignment_evidence=True,
        contract_format_version=1,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    format_1 = EvidenceRequirements.try_create(
        World.LIVE, AccountRole.LIVE, dur, {}, contract_format_version=1
    )
    assert is_ok(format_1)
    identity = format_1.value.fp1_identity()
    assert "registered_conformant_bot_cite" not in identity
    assert "canonical_assignment_evidence" not in identity


def test_migration_note_identity_is_stable() -> None:
    one = CT22_FORMAT_2_MIGRATION.fp1_identity()
    two = CT22_FORMAT_2_MIGRATION.fp1_identity()
    assert one == two
    assert one["added"] == list(CT22_FORMAT_2_MIGRATION.added)


def test_book_definition_boolean_reader_version_is_invalid() -> None:
    from qmf.core import Money, UnitKind
    from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability

    variable = TemplateVariable.try_create(
        "loss_floor",
        UnitKind.MONEY,
        Money(value=1, currency="USD", scale=2),
        UiEditability.UI_EDITABLE,
        AdmissionImpact.RESIGN,
    )
    assert is_ok(variable)
    section = TemplateSection.try_create("money_rules", {variable.value.name: variable.value})
    assert is_ok(section)
    result = BookDefinition.try_create(
        BOOK_FORMAT_VERSION_1,
        "USD",
        {"money_rules": section.value},
        reader_format_version=True,
    )
    assert is_refusal(result)
