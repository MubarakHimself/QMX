"""Story 10.1 AC1/AC3 — the template variable grammar and evidence law.

Verifies the four-part template variable (unit-kind, exact value, ui-editable
flag, admission_impact), the invalid-input refusal when any of the four is
missing, the no-binary-float and unit-kind-match discipline on the value, the
explicit NotYetRuled blank, and that attached evidence carries a source layer and
authority grade and is never a ratified constant (CT-22, CT-27, FR-035, L38;
DEC-0144, DEC-0157).
"""

from __future__ import annotations

from qmf.core import (
    Duration,
    ExactRational,
    Instant,
    Instrument,
    Money,
    PriceDelta,
    Quantity,
    RefusalCategory,
    UnitKind,
    VenueId,
    is_ok,
    is_refusal,
)
from qmf.risk.grammar import (
    AdmissionImpact,
    AuthorityGrade,
    NotYetRuled,
    SourceLayer,
    TemplateSection,
    TemplateVariable,
    UiEditability,
    VariableEvidence,
    value_unit_kind,
)

_USD_MONEY = Money(value=100_000, currency="USD", scale=2)
_R_COUNT = ExactRational(numerator=2, denominator=1, unit_kind=UnitKind.COUNT)


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")


# --- the closed enums --------------------------------------------------------


def test_ui_editability_values() -> None:
    assert {m.value for m in UiEditability} == {"ui-editable", "uneditable"}


def test_admission_impact_values() -> None:
    assert {m.value for m in AdmissionImpact} == {"resign", "relint", "none"}


def test_authority_grade_values() -> None:
    assert {m.value for m in AuthorityGrade} == {"authoritative", "non-authoritative"}


def test_source_layer_has_gitbook_and_qmx_discussion() -> None:
    values = {m.value for m in SourceLayer}
    assert "gitbook" in values
    assert "qmx-discussion" in values


# --- value_unit_kind ---------------------------------------------------------


def test_value_unit_kind_resolves_each_core_carrier() -> None:
    assert value_unit_kind(_USD_MONEY) is UnitKind.MONEY
    assert value_unit_kind(_R_COUNT) is UnitKind.COUNT
    assert value_unit_kind(PriceDelta(value=5, instrument=_instrument(), scale=5)) is (
        UnitKind.PRICE_DELTA
    )
    assert value_unit_kind(Quantity(value=1, unit="lot", scale=2)) is UnitKind.QUANTITY
    assert value_unit_kind(Duration(value_ns=10)) is UnitKind.DURATION
    assert value_unit_kind(Instant(value_ns=10)) is UnitKind.INSTANT


def test_value_unit_kind_rejects_non_carriers() -> None:
    assert value_unit_kind(True) is None  # bool is not a scaled integer value
    assert value_unit_kind(1.5) is None  # a binary float never carries a unit-kind
    assert value_unit_kind(7) is None  # a bare int is ambiguous, not a typed value
    assert value_unit_kind("USD") is None
    assert value_unit_kind(None) is None


# --- the four-part variable (AC1) --------------------------------------------


def test_valid_variable_carries_all_four_parts() -> None:
    result = TemplateVariable.try_create(
        name="loss_floor",
        unit_kind=UnitKind.MONEY,
        value=_USD_MONEY,
        ui_editable=UiEditability.UI_EDITABLE,
        admission_impact=AdmissionImpact.RESIGN,
    )
    assert is_ok(result)
    variable = result.value
    assert variable.unit_kind is UnitKind.MONEY
    assert variable.ui_editable is UiEditability.UI_EDITABLE
    assert variable.admission_impact is AdmissionImpact.RESIGN
    assert variable.is_blank is False


def test_missing_unit_kind_is_invalid_input() -> None:
    result = TemplateVariable.try_create(
        name="x",
        unit_kind=None,
        value=_USD_MONEY,
        ui_editable=UiEditability.UI_EDITABLE,
        admission_impact=AdmissionImpact.NONE,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "unit_kind"


def test_missing_value_is_invalid_input() -> None:
    result = TemplateVariable.try_create(
        name="x",
        unit_kind=UnitKind.MONEY,
        value=None,
        ui_editable=UiEditability.UI_EDITABLE,
        admission_impact=AdmissionImpact.NONE,
    )
    assert is_refusal(result)
    assert result.context["field"] == "value"


def test_missing_ui_flag_is_invalid_input() -> None:
    result = TemplateVariable.try_create(
        name="x",
        unit_kind=UnitKind.MONEY,
        value=_USD_MONEY,
        ui_editable=None,
        admission_impact=AdmissionImpact.NONE,
    )
    assert is_refusal(result)
    assert result.context["field"] == "ui_editable"


def test_missing_admission_impact_is_invalid_input() -> None:
    result = TemplateVariable.try_create(
        name="x",
        unit_kind=UnitKind.MONEY,
        value=_USD_MONEY,
        ui_editable=UiEditability.UI_EDITABLE,
        admission_impact=None,
    )
    assert is_refusal(result)
    assert result.context["field"] == "admission_impact"


def test_blank_name_is_invalid_input() -> None:
    result = TemplateVariable.try_create(
        name="   ",
        unit_kind=UnitKind.MONEY,
        value=_USD_MONEY,
        ui_editable=UiEditability.UI_EDITABLE,
        admission_impact=AdmissionImpact.NONE,
    )
    assert is_refusal(result)
    assert result.context["field"] == "name"


def test_unrecognised_unit_kind_is_invalid_input() -> None:
    result = TemplateVariable.try_create(
        name="x",
        unit_kind="furlongs",
        value=_USD_MONEY,
        ui_editable=UiEditability.UI_EDITABLE,
        admission_impact=AdmissionImpact.NONE,
    )
    assert is_refusal(result)
    assert result.context["field"] == "unit_kind"


def test_binary_float_value_is_refused_off_the_money_path() -> None:
    result = TemplateVariable.try_create(
        name="x",
        unit_kind=UnitKind.MONEY,
        value=1.5,
        ui_editable=UiEditability.UI_EDITABLE,
        admission_impact=AdmissionImpact.NONE,
    )
    assert is_refusal(result)
    assert result.context["field"] == "value"


def test_unit_kind_mismatch_between_declared_and_value_is_refused() -> None:
    # A count value declared where a money variable is stated — the dimensional
    # discipline begins at declaration (a count cannot stand where money is declared).
    result = TemplateVariable.try_create(
        name="x",
        unit_kind=UnitKind.MONEY,
        value=_R_COUNT,
        ui_editable=UiEditability.UI_EDITABLE,
        admission_impact=AdmissionImpact.NONE,
    )
    assert is_refusal(result)
    assert result.context["field"] == "value"
    assert result.context["declared"] == "money(currency)"


def test_not_yet_ruled_blank_is_a_legal_declared_value() -> None:
    blank = NotYetRuled.try_create("GAP-0048")
    assert is_ok(blank)
    result = TemplateVariable.try_create(
        name="sharpe_threshold",
        unit_kind=UnitKind.DIMENSIONLESS_RATIO,
        value=blank.value,
        ui_editable=UiEditability.UI_EDITABLE,
        admission_impact=AdmissionImpact.RESIGN,
    )
    assert is_ok(result)
    assert result.value.is_blank is True


def test_not_yet_ruled_requires_a_gap_reference() -> None:
    assert is_refusal(NotYetRuled.try_create("  "))
    assert is_refusal(NotYetRuled.try_create(None))


# --- evidence (AC3): source layer + authority grade, never a ratified constant


def test_evidence_carries_source_layer_and_authority_grade() -> None:
    result = VariableEvidence.try_create(
        recorded_value=_R_COUNT,
        source_layer=SourceLayer.QMX_DISCUSSION,
        authority_grade=AuthorityGrade.NON_AUTHORITATIVE,
        note="a value of two for a scalper — recorded evidence",
    )
    assert is_ok(result)
    evidence = result.value
    assert evidence.source_layer is SourceLayer.QMX_DISCUSSION
    assert evidence.authority_grade is AuthorityGrade.NON_AUTHORITATIVE
    assert evidence.is_ratified_constant is False


def test_evidence_is_never_a_ratified_constant_even_when_authoritative() -> None:
    result = VariableEvidence.try_create(
        recorded_value=_USD_MONEY,
        source_layer=SourceLayer.GITBOOK,
        authority_grade=AuthorityGrade.AUTHORITATIVE,
    )
    assert is_ok(result)
    assert result.value.is_ratified_constant is False
    assert result.value.fp1_identity()["is_ratified_constant"] is False


def test_evidence_rejects_a_blank_recorded_value() -> None:
    blank = NotYetRuled.try_create("GAP-0048")
    assert is_ok(blank)
    result = VariableEvidence.try_create(
        recorded_value=blank.value,
        source_layer=SourceLayer.GITBOOK,
        authority_grade=AuthorityGrade.AUTHORITATIVE,
    )
    assert is_refusal(result)
    assert result.context["field"] == "recorded_value"


def test_evidence_rejects_bad_layer_grade_and_note() -> None:
    assert is_refusal(
        VariableEvidence.try_create(_USD_MONEY, "hearsay", AuthorityGrade.AUTHORITATIVE)
    )
    assert is_refusal(VariableEvidence.try_create(_USD_MONEY, SourceLayer.GITBOOK, "supreme"))
    assert is_refusal(
        VariableEvidence.try_create(
            _USD_MONEY, SourceLayer.GITBOOK, AuthorityGrade.AUTHORITATIVE, note="   "
        )
    )


def test_configurable_variable_may_ship_blank_with_evidence_beside_it() -> None:
    # The AC3 shape: a UI-editable variable whose value is not yet ruled, carrying
    # non-authoritative recorded evidence that never becomes its ratified constant.
    blank = NotYetRuled.try_create("GAP-0048")
    evidence = VariableEvidence.try_create(
        _R_COUNT, SourceLayer.QMX_DISCUSSION, AuthorityGrade.NON_AUTHORITATIVE
    )
    assert is_ok(blank)
    assert is_ok(evidence)
    result = TemplateVariable.try_create(
        name="bench_consecutive_loss_threshold",
        unit_kind=UnitKind.COUNT,
        value=blank.value,
        ui_editable=UiEditability.UI_EDITABLE,
        admission_impact=AdmissionImpact.RELINT,
        evidence=evidence.value,
    )
    assert is_ok(result)
    variable = result.value
    assert variable.is_blank is True
    assert variable.evidence is not None
    assert variable.evidence.is_ratified_constant is False


def test_variable_rejects_non_evidence_object() -> None:
    result = TemplateVariable.try_create(
        name="x",
        unit_kind=UnitKind.MONEY,
        value=_USD_MONEY,
        ui_editable=UiEditability.UI_EDITABLE,
        admission_impact=AdmissionImpact.NONE,
        evidence=_USD_MONEY,
    )
    assert is_refusal(result)
    assert result.context["field"] == "evidence"


# --- fingerprint content: a changed number changes fp1 (AC5 support) ----------


def test_changed_number_changes_variable_fp1_identity() -> None:
    base = TemplateVariable.try_create(
        "loss_floor", UnitKind.MONEY, _USD_MONEY, UiEditability.UI_EDITABLE, AdmissionImpact.RESIGN
    )
    changed = TemplateVariable.try_create(
        "loss_floor",
        UnitKind.MONEY,
        Money(value=200_000, currency="USD", scale=2),
        UiEditability.UI_EDITABLE,
        AdmissionImpact.RESIGN,
    )
    assert is_ok(base)
    assert is_ok(changed)
    assert base.value.fp1_identity() != changed.value.fp1_identity()


def test_identical_variables_share_fp1_identity() -> None:
    one = TemplateVariable.try_create(
        "loss_floor", UnitKind.MONEY, _USD_MONEY, UiEditability.UI_EDITABLE, AdmissionImpact.RESIGN
    )
    two = TemplateVariable.try_create(
        "loss_floor", UnitKind.MONEY, _USD_MONEY, UiEditability.UI_EDITABLE, AdmissionImpact.RESIGN
    )
    assert is_ok(one)
    assert is_ok(two)
    assert one.value.fp1_identity() == two.value.fp1_identity()


# --- TemplateSection ---------------------------------------------------------


def _money_variable(name: str) -> TemplateVariable:
    result = TemplateVariable.try_create(
        name, UnitKind.MONEY, _USD_MONEY, UiEditability.UI_EDITABLE, AdmissionImpact.RESIGN
    )
    assert is_ok(result)
    return result.value


def test_template_section_builds_from_named_variables() -> None:
    variable = _money_variable("loss_floor")
    result = TemplateSection.try_create("money_rules", {"loss_floor": variable})
    assert is_ok(result)
    section = result.value
    assert section.name == "money_rules"
    assert "loss_floor" in section.variables


def test_template_section_rejects_blank_name() -> None:
    assert is_refusal(TemplateSection.try_create("", {}))


def test_template_section_rejects_non_mapping_variables() -> None:
    result = TemplateSection.try_create("money_rules", ["not", "a", "map"])
    assert is_refusal(result)
    assert result.context["field"] == "variables"


def test_template_section_rejects_non_variable_value() -> None:
    result = TemplateSection.try_create("money_rules", {"loss_floor": _USD_MONEY})
    assert is_refusal(result)


def test_template_section_rejects_key_name_mismatch() -> None:
    variable = _money_variable("loss_floor")
    result = TemplateSection.try_create("money_rules", {"kill_line": variable})
    assert is_refusal(result)


def test_template_section_rejects_blank_key() -> None:
    variable = _money_variable("loss_floor")
    result = TemplateSection.try_create("money_rules", {"   ": variable})
    assert is_refusal(result)


def test_template_section_variables_are_frozen() -> None:
    variable = _money_variable("loss_floor")
    source: dict[str, TemplateVariable] = {"loss_floor": variable}
    result = TemplateSection.try_create("money_rules", source)
    assert is_ok(result)
    source["injected"] = variable  # mutating the source must not leak in
    assert "injected" not in result.value.variables
