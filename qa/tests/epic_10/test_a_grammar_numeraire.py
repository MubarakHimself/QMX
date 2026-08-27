"""Epic 10 independent audit — Cluster A (Story 10.1).

Template grammar, the dimensional law, the USD numeraire, git-logic versioning,
and packaging. Assertions are authored from the requirement text (Epic 10 Story
10.1 ACs, CT-22, CT-27, L38, AR-06, R-001 gate) — NOT from the source. A failing
assertion is a FINDING against the requirement, never a reason to weaken the test.

Planned IDs: A1-A12.
"""

from __future__ import annotations

import ast
import dataclasses
from fractions import Fraction
from pathlib import Path

import pytest
import qmf.risk
from qmf.core import (
    ExactRational,
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
from qmf.risk.dimensional import (
    FORM_0006,
    LADDER_FORMULAS,
    BinOp,
    FormulaOp,
    FormulaSpec,
    Ref,
    check_formula,
)
from qmf.risk.grammar import (
    AdmissionImpact,
    AuthorityGrade,
    NotYetRuled,
    SourceLayer,
    TemplateVariable,
    UiEditability,
    VariableEvidence,
)
from qmf.risk.numeraire import V1_NUMERAIRE, validate_accounting_currency, validate_book_limit
from qmf.risk.versioning import TemplateVersionGraph

# The closed AD-40 unit-kind vocabulary the requirement names (Story 10.1 AC1).
_AD40_VOCABULARY = {
    "money(currency)",
    "price-delta(instrument)",
    "quantity(unit)",
    "value-factor(instrument, currency)",
    "r-multiple",
    "rate(money-per-r)",
    "count",
    "dimensionless-ratio",
    "duration",
    "instant",
}


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")


def _usd(minor: int = 100_000) -> Money:
    return Money(value=minor, currency="USD", scale=2)


_UNSET = object()


def _var(
    *,
    name: str = "loss_floor",
    unit_kind: object = UnitKind.MONEY,
    value: object = _UNSET,
    ui_editable: object = UiEditability.UI_EDITABLE,
    admission_impact: object = AdmissionImpact.RESIGN,
):
    return TemplateVariable.try_create(
        name=name,
        unit_kind=unit_kind,
        value=_usd() if value is _UNSET else value,
        ui_editable=ui_editable,
        admission_impact=admission_impact,
    )


# --- A1: a variable missing any of the four parts -> invalid input -----------


def test_A1_variable_missing_any_of_four_parts_is_invalid_input() -> None:
    # The requirement: a variable carries {unit_kind, value, ui-editable, admission_impact};
    # missing any one is an invalid-input refusal (Story 10.1 AC1).
    assert is_ok(_var())  # all four present -> admitted
    for field, kwargs in (
        ("unit_kind", {"unit_kind": None}),
        ("value", {"value": None}),
        ("ui_editable", {"ui_editable": None}),
        ("admission_impact", {"admission_impact": None}),
    ):
        result = _var(**kwargs)  # type: ignore[arg-type]
        assert is_refusal(result), field
        assert result.category is RefusalCategory.INVALID_INPUT, field
        assert result.context["field"] == field


# --- A2: unit_kind drawn from the closed AD-40 vocabulary --------------------


def test_A2_unit_kind_is_the_closed_ad40_vocabulary() -> None:
    assert {member.value for member in UnitKind} == _AD40_VOCABULARY
    out_of_vocab = _var(unit_kind="furlongs")
    assert is_refusal(out_of_vocab)
    assert out_of_vocab.category is RefusalCategory.INVALID_INPUT
    assert out_of_vocab.context["field"] == "unit_kind"


# --- A3: every value is exact-rational / scaled-integer, no binary float -----


def test_A3_binary_float_value_is_refused_on_the_money_path() -> None:
    result = _var(unit_kind=UnitKind.MONEY, value=1.5)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "value"
    # A scaled-integer Money and an ExactRational value are both admissible carriers.
    assert is_ok(_var(unit_kind=UnitKind.MONEY, value=_usd()))
    r = ExactRational.try_create(2, 1, UnitKind.COUNT)
    assert is_ok(r)
    assert is_ok(_var(name="c", unit_kind=UnitKind.COUNT, value=r.value))


# --- A4 [R-001]: dimensional checker refuses on unit-kind mismatch -----------


def test_A4_dimensional_checker_refuses_a_unit_kind_mismatch() -> None:
    # A formula declaring money = money x money is undeclarable (no such product rule);
    # a formula claiming the wrong output unit-kind is refused. R-001: no silent crossing.
    bad_product = FormulaSpec.try_create(
        formula_id="AUDIT-bad-product",
        inputs={"a": UnitKind.MONEY, "b": UnitKind.MONEY},
        output=UnitKind.MONEY,
        expression=BinOp(FormulaOp.MULTIPLY, Ref("a"), Ref("b")),
    )
    assert is_refusal(bad_product)
    assert bad_product.category is RefusalCategory.INVALID_INPUT
    # add of mismatched kinds is refused (money + count is dimensionally unsound).
    mismatched_add = FormulaSpec.try_create(
        formula_id="AUDIT-bad-add",
        inputs={"a": UnitKind.MONEY, "b": UnitKind.COUNT},
        output=UnitKind.MONEY,
        expression=BinOp(FormulaOp.ADD, Ref("a"), Ref("b")),
    )
    assert is_refusal(mismatched_add)


# --- A5: every formula ships an executable worked example that recomputes -----


def test_A5_every_ladder_formula_has_a_recomputing_worked_example() -> None:
    assert len(LADDER_FORMULAS) >= 1
    for formula in LADDER_FORMULAS:
        assert is_ok(check_formula(formula)), formula.formula_id
        example = formula.worked_example
        assert example is not None, formula.formula_id
        # Recompute the expression's magnitude from the example inputs and compare.
        computed = _recompute(formula.expression, dict(example.inputs))
        expected = example.expected_output
        assert isinstance(expected, (Money, ExactRational))
        assert computed == expected.as_fraction(), formula.formula_id


def _recompute(expr: object, inputs: dict[str, object]) -> Fraction:
    if isinstance(expr, Ref):
        value = inputs[expr.name]
        assert isinstance(value, (Money, ExactRational))
        return value.as_fraction()
    assert isinstance(expr, BinOp)
    left = _recompute(expr.left, inputs)
    right = _recompute(expr.right, inputs)
    if expr.op is FormulaOp.ADD:
        return left + right
    if expr.op is FormulaOp.SUBTRACT:
        return left - right
    if expr.op is FormulaOp.MULTIPLY:
        return left * right
    return left / right


# --- A6 [R-001]: the dead FORM-0006 is a permanent negative test -------------


def test_A6_dead_form_0006_is_rejected_by_the_checker() -> None:
    result = check_formula(FORM_0006)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["formula_id"] == "FORM-0006"
    # And a clone of the same defect can never be minted through try_create.
    clone = FormulaSpec.try_create(
        formula_id="FORM-0006-audit-clone",
        inputs={"budget": UnitKind.MONEY, "n": UnitKind.COUNT},
        output=UnitKind.RATE,
        expression=BinOp(FormulaOp.DIVIDE, Ref("budget"), Ref("n")),
    )
    assert is_refusal(clone)


# --- A7 [L2]: a UI edit mints a new version and never mutates one -------------


def test_A7_ui_edit_mints_new_version_never_mutates() -> None:
    # A variable is immutable (frozen) — an edit cannot mutate it in place.
    base = _var(value=_usd(800_000))
    assert is_ok(base)
    with pytest.raises(dataclasses.FrozenInstanceError):
        base.value.value = _usd(700_000)  # type: ignore[misc,attr-defined]
    # The edited value is a NEW identity (different fp1), never the same version mutated.
    edited = _var(value=_usd(700_000))
    assert is_ok(edited)
    assert base.value.fp1_identity() != edited.value.fp1_identity()
    # Two identical declarations share identity — identity is content, not object.
    same = _var(value=_usd(800_000))
    assert is_ok(same)
    assert base.value.fp1_identity() == same.value.fp1_identity()


# --- A8: a recorded number is evidence w/ source layer + grade, never spine ---


def test_A8_recorded_number_is_non_spine_evidence_with_layer_and_grade() -> None:
    r = ExactRational.try_create(2, 1, UnitKind.COUNT)
    assert is_ok(r)
    evidence = VariableEvidence.try_create(
        recorded_value=r.value,
        source_layer=SourceLayer.QMX_DISCUSSION,
        authority_grade=AuthorityGrade.NON_AUTHORITATIVE,
    )
    assert is_ok(evidence)
    assert evidence.value.source_layer is SourceLayer.QMX_DISCUSSION
    assert evidence.value.authority_grade is AuthorityGrade.NON_AUTHORITATIVE
    # Even an authoritative recorded number is NEVER a ratified spine constant.
    authoritative = VariableEvidence.try_create(
        recorded_value=_usd(),
        source_layer=SourceLayer.GITBOOK,
        authority_grade=AuthorityGrade.AUTHORITATIVE,
    )
    assert is_ok(authoritative)
    assert authoritative.value.is_ratified_constant is False


# --- A9 [R-001]: USD is the sole V1 numeraire --------------------------------


def test_A9_usd_is_the_sole_v1_numeraire() -> None:
    assert V1_NUMERAIRE == "USD"
    assert is_ok(validate_accounting_currency("USD"))
    non_usd = validate_accounting_currency("EUR")
    assert is_refusal(non_usd)
    assert non_usd.category is RefusalCategory.POLICY_REJECTION
    # A non-numeraire money value at template level refuses, never silently converts.
    non_usd_notional = validate_book_limit(UnitKind.MONEY, currency="JPY")
    assert is_refusal(non_usd_notional)
    assert non_usd_notional.category is RefusalCategory.POLICY_REJECTION


# --- A10 [R-001]: a Book-level lots limit -> policy rejection -----------------


def test_A10_book_limit_in_lots_is_policy_rejection() -> None:
    result = validate_book_limit(UnitKind.QUANTITY)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    # Only R-multiple and USD money may express a Book limit.
    assert is_ok(validate_book_limit(UnitKind.R_MULTIPLE))
    assert is_ok(validate_book_limit(UnitKind.MONEY, currency="USD"))


# --- A11 [L2]: branches-from graph, multiple heads, separate dated current ----


def test_A11_version_graph_branches_from_multiple_heads_and_current_pointer() -> None:
    from qmf.core import Instant, fingerprint

    def _fp(tag: str):
        result = fingerprint({"tag": tag})
        assert is_ok(result)
        return result.value

    graph = TemplateVersionGraph()
    root, a, b = _fp("v1"), _fp("v2a"), _fp("v2b")
    assert is_ok(graph.append_version(root))
    assert is_ok(graph.append_version(a, branches_from=root))
    assert is_ok(graph.append_version(b, branches_from=root))
    # multiple heads are legal
    assert set(graph.heads()) == {a, b}
    # re-adding a version is refused, never idempotent (a changed number is a new identity)
    assert is_refusal(graph.append_version(root))
    # current is a SEPARATE dated pointer, unset until dated, and moves forward only
    assert graph.current() is None
    assert is_ok(graph.set_current(root, Instant(value_ns=1_000)))
    assert graph.current() == root
    assert is_ok(graph.set_current(a, Instant(value_ns=2_000)))
    assert graph.current() == a
    stale = graph.set_current(b, Instant(value_ns=1_500))
    assert is_refusal(stale)
    # every old version stays readable forever
    assert graph.is_readable(root) is True
    assert graph.is_readable(a) is True


# --- A12 [L0/L1]: qmf-risk imports only qmf-core and is imported by nothing ---


def test_A12_qmf_risk_imports_only_qmf_core() -> None:
    forbidden = ("qmf.data", "qmf.registry", "qmf.indicators", "qmf.structure", "qmf.venue")
    src_dir = Path(qmf.risk.__file__).resolve().parent
    scanned = 0
    for path in sorted(src_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        scanned += 1
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                names.append(node.module)
            elif isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            for name in names:
                assert not any(
                    name == bad or name.startswith(f"{bad}.") for bad in forbidden
                ), f"{path.name} imports forbidden {name}"
    assert scanned >= 5


def test_A12_qmf_risk_is_imported_by_no_other_package() -> None:
    # AR-06 default-deny: nothing imports qmf-risk. Scan every OTHER package's src.
    packages_dir = Path(qmf.risk.__file__).resolve().parents[4]  # .../packages
    offenders: list[str] = []
    for pkg in sorted(packages_dir.glob("qmf-*")):
        if pkg.name == "qmf-risk":
            continue
        for path in pkg.glob("src/**/*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.ImportFrom) and node.module is not None:
                    names.append(node.module)
                elif isinstance(node, ast.Import):
                    names.extend(alias.name for alias in node.names)
                for name in names:
                    if name == "qmf.risk" or name.startswith("qmf.risk."):
                        offenders.append(f"{pkg.name}:{path.name} imports {name}")
    assert offenders == [], offenders
