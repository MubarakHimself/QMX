"""Story 10.1 AC2 — the dimensional law and the FORM-0006 negative test.

Verifies the closed-vocabulary unit-kind checker (add/subtract require identical
kinds; multiply/divide follow the pinned tables), that every ratified sizing-ladder
formula is dimensionally sound and its worked example recomputes at Tier 2 by
invoking the cited qmf-core arithmetic, that a second FORM-0006 is undeclarable
through try_create, and that the dead FORM-0006 is retained as the permanent
negative case the checker refuses every run (CT-22, L38; DEC-0146, DEC-0154).
"""

from __future__ import annotations

from fractions import Fraction

from qmf.core import ExactRational, Money, RefusalCategory, UnitKind, is_ok, is_refusal
from qmf.risk.dimensional import (
    FORM_0006,
    LADDER_FORMULAS,
    SEAT_R_CEILING_CONSTRAINT,
    BinOp,
    ComparisonOp,
    ConstraintSpec,
    FormulaOp,
    FormulaSpec,
    Ref,
    WorkedExample,
    check_constraint,
    check_formula,
    derive_unit_kind,
)
from qmf.risk.grammar import VariableValue


def _frac(value: object) -> Fraction:
    """The exact magnitude of a worked-example value (a Money or ExactRational)."""
    assert isinstance(value, (Money, ExactRational))
    return value.as_fraction()


def _recompute(expr: object, inputs: dict[str, VariableValue]) -> Fraction:
    """A Tier-2, test-local numeric evaluator over the symbolic expression.

    Walks the same tree the dimensional checker walks, doing exact Fraction
    arithmetic over the worked-example inputs' own magnitudes — the recompute lives
    in the test, never in shipped qmf-risk (the sizing ladder is never evaluated at
    runtime there; DEC-0142).
    """
    if isinstance(expr, Ref):
        return _frac(inputs[expr.name])
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


# --- the symbolic checker over the derivation algebra ------------------------


def test_derive_resolves_a_reference() -> None:
    result = derive_unit_kind(Ref("a"), {"a": UnitKind.MONEY})
    assert is_ok(result)
    assert result.value is UnitKind.MONEY


def test_derive_refuses_an_unresolved_reference() -> None:
    result = derive_unit_kind(Ref("missing"), {"a": UnitKind.MONEY})
    assert is_refusal(result)
    assert result.context["reference"] == "missing"


def test_add_requires_identical_unit_kinds() -> None:
    same = derive_unit_kind(
        BinOp(FormulaOp.ADD, Ref("a"), Ref("b")), {"a": UnitKind.MONEY, "b": UnitKind.MONEY}
    )
    assert is_ok(same)
    assert same.value is UnitKind.MONEY
    mixed = derive_unit_kind(
        BinOp(FormulaOp.SUBTRACT, Ref("a"), Ref("b")),
        {"a": UnitKind.MONEY, "b": UnitKind.COUNT},
    )
    assert is_refusal(mixed)


def test_multiply_r_by_rate_is_money() -> None:
    result = derive_unit_kind(
        BinOp(FormulaOp.MULTIPLY, Ref("r"), Ref("p")),
        {"r": UnitKind.R_MULTIPLE, "p": UnitKind.RATE},
    )
    assert is_ok(result)
    assert result.value is UnitKind.MONEY


def test_divide_table_covers_the_ratified_quotients() -> None:
    money_over_count = derive_unit_kind(
        BinOp(FormulaOp.DIVIDE, Ref("m"), Ref("n")),
        {"m": UnitKind.MONEY, "n": UnitKind.COUNT},
    )
    money_over_r = derive_unit_kind(
        BinOp(FormulaOp.DIVIDE, Ref("m"), Ref("r")),
        {"m": UnitKind.MONEY, "r": UnitKind.R_MULTIPLE},
    )
    assert is_ok(money_over_count)
    assert money_over_count.value is UnitKind.MONEY
    assert is_ok(money_over_r)
    assert money_over_r.value is UnitKind.RATE


def test_undeclarable_product_is_refused() -> None:
    result = derive_unit_kind(
        BinOp(FormulaOp.MULTIPLY, Ref("a"), Ref("b")),
        {"a": UnitKind.MONEY, "b": UnitKind.MONEY},
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


# --- the ratified ladder formulas are sound and recompute --------------------


def test_every_ladder_formula_is_dimensionally_sound() -> None:
    for formula in LADDER_FORMULAS:
        checked = check_formula(formula)
        assert is_ok(checked), formula.formula_id
        assert checked.value is formula.output


def test_every_ladder_formula_worked_example_recomputes_at_tier_2() -> None:
    for formula in LADDER_FORMULAS:
        example = formula.worked_example
        assert example is not None, formula.formula_id
        computed = _recompute(formula.expression, dict(example.inputs))
        assert computed == _frac(example.expected_output), formula.formula_id


def test_loss_runway_recomputes_via_the_money_producer_contract() -> None:
    # Exercise the cited producer contract itself (CT-01 Money.subtract), not just
    # Fraction arithmetic — the worked example is recomputed, never re-implemented.
    loss_runway = next(f for f in LADDER_FORMULAS if f.formula_id == "FORM-loss-runway")
    example = loss_runway.worked_example
    assert example is not None
    book_capital = example.inputs["book_capital"]
    loss_floor = example.inputs["loss_floor"]
    assert isinstance(book_capital, Money)
    assert isinstance(loss_floor, Money)
    difference = book_capital.subtract(loss_floor)
    assert is_ok(difference)
    assert difference.value.as_fraction() == _frac(example.expected_output)


# --- FORM-0006: the permanent negative test ----------------------------------


def test_form_0006_is_refused_by_the_checker() -> None:
    result = check_formula(FORM_0006)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["formula_id"] == "FORM-0006"
    # money ÷ count derives money, never the declared rate.
    assert result.context["derived_output"] == "money(currency)"
    assert result.context["declared_output"] == "rate(money-per-r)"


def test_a_second_form_0006_is_undeclarable_through_try_create() -> None:
    # Declaring an unsound formula (money ÷ count claimed as a rate) is refused at
    # construction: try_create runs the checker, so the defect can never be minted.
    result = FormulaSpec.try_create(
        formula_id="FORM-0006-clone",
        inputs={"budget": UnitKind.MONEY, "b": UnitKind.COUNT},
        output=UnitKind.RATE,
        expression=BinOp(FormulaOp.DIVIDE, Ref("budget"), Ref("b")),
    )
    assert is_refusal(result)


def test_seat_r_ceiling_constraint_is_sound_pure_r_space() -> None:
    result = check_constraint(SEAT_R_CEILING_CONSTRAINT)
    assert is_ok(result)


# --- FormulaSpec.try_create validation ---------------------------------------


def test_try_create_builds_a_sound_formula_with_a_worked_example() -> None:
    result = FormulaSpec.try_create(
        formula_id="FORM-loss-runway-copy",
        inputs={"book_capital": UnitKind.MONEY, "loss_floor": UnitKind.MONEY},
        output=UnitKind.MONEY,
        expression=BinOp(FormulaOp.SUBTRACT, Ref("book_capital"), Ref("loss_floor")),
        worked_example=WorkedExample(
            inputs={
                "book_capital": Money(value=1_000_000, currency="USD", scale=2),
                "loss_floor": Money(value=800_000, currency="USD", scale=2),
            },
            expected_output=Money(value=200_000, currency="USD", scale=2),
        ),
    )
    assert is_ok(result)
    assert result.value.worked_example is not None


def test_try_create_rejects_blank_id_and_empty_inputs_and_bad_output() -> None:
    assert is_refusal(FormulaSpec.try_create("  ", {"a": UnitKind.MONEY}, UnitKind.MONEY, Ref("a")))
    assert is_refusal(FormulaSpec.try_create("F", {}, UnitKind.MONEY, Ref("a")))
    assert is_refusal(FormulaSpec.try_create("F", {"a": UnitKind.MONEY}, "widgets", Ref("a")))


def test_try_create_rejects_bad_input_map_and_expression() -> None:
    assert is_refusal(FormulaSpec.try_create("F", ["a"], UnitKind.MONEY, Ref("a")))
    assert is_refusal(FormulaSpec.try_create("F", {"a": "widgets"}, UnitKind.MONEY, Ref("a")))
    assert is_refusal(FormulaSpec.try_create("F", {"a": UnitKind.MONEY}, UnitKind.MONEY, "a"))
    assert is_refusal(FormulaSpec.try_create("F", {"  ": UnitKind.MONEY}, UnitKind.MONEY, Ref("a")))


def test_try_create_rejects_worked_example_dimension_mismatch() -> None:
    # An expected output whose unit-kind disagrees with the declared output.
    bad_output = FormulaSpec.try_create(
        "F",
        {"a": UnitKind.MONEY, "b": UnitKind.MONEY},
        UnitKind.MONEY,
        BinOp(FormulaOp.SUBTRACT, Ref("a"), Ref("b")),
        worked_example=WorkedExample(
            inputs={
                "a": Money(value=10, currency="USD", scale=2),
                "b": Money(value=5, currency="USD", scale=2),
            },
            expected_output=ExactRational(numerator=5, denominator=1, unit_kind=UnitKind.COUNT),
        ),
    )
    assert is_refusal(bad_output)


def test_try_create_rejects_worked_example_missing_and_extra_inputs() -> None:
    missing = FormulaSpec.try_create(
        "F",
        {"a": UnitKind.MONEY, "b": UnitKind.MONEY},
        UnitKind.MONEY,
        BinOp(FormulaOp.SUBTRACT, Ref("a"), Ref("b")),
        worked_example=WorkedExample(
            inputs={"a": Money(value=10, currency="USD", scale=2)},
            expected_output=Money(value=10, currency="USD", scale=2),
        ),
    )
    assert is_refusal(missing)
    extra = FormulaSpec.try_create(
        "F",
        {"a": UnitKind.MONEY},
        UnitKind.MONEY,
        Ref("a"),
        worked_example=WorkedExample(
            inputs={
                "a": Money(value=10, currency="USD", scale=2),
                "z": Money(value=1, currency="USD", scale=2),
            },
            expected_output=Money(value=10, currency="USD", scale=2),
        ),
    )
    assert is_refusal(extra)


def test_try_create_rejects_worked_example_wrong_input_kind() -> None:
    wrong = FormulaSpec.try_create(
        "F",
        {"a": UnitKind.MONEY},
        UnitKind.MONEY,
        Ref("a"),
        worked_example=WorkedExample(
            inputs={"a": ExactRational(numerator=1, denominator=1, unit_kind=UnitKind.COUNT)},
            expected_output=Money(value=1, currency="USD", scale=2),
        ),
    )
    assert is_refusal(wrong)


def test_try_create_rejects_non_worked_example_object() -> None:
    result = FormulaSpec.try_create(
        "F", {"a": UnitKind.MONEY}, UnitKind.MONEY, Ref("a"), worked_example="nope"
    )
    assert is_refusal(result)


def test_formula_check_method_matches_check_formula() -> None:
    formula = LADDER_FORMULAS[0]
    assert is_ok(formula.check())


# --- ConstraintSpec ----------------------------------------------------------


def test_constraint_try_create_accepts_matched_kinds() -> None:
    result = ConstraintSpec.try_create(
        "C", UnitKind.R_MULTIPLE, ComparisonOp.AT_MOST, UnitKind.R_MULTIPLE
    )
    assert is_ok(result)


def test_constraint_try_create_refuses_mismatched_kinds() -> None:
    result = ConstraintSpec.try_create(
        "C", UnitKind.MONEY, ComparisonOp.AT_MOST, UnitKind.R_MULTIPLE
    )
    assert is_refusal(result)


def test_constraint_try_create_validates_its_parts() -> None:
    assert is_refusal(
        ConstraintSpec.try_create("  ", UnitKind.MONEY, ComparisonOp.EQUAL, UnitKind.MONEY)
    )
    assert is_refusal(ConstraintSpec.try_create("C", "widgets", ComparisonOp.EQUAL, UnitKind.MONEY))
    assert is_refusal(ConstraintSpec.try_create("C", UnitKind.MONEY, "gt", UnitKind.MONEY))
    assert is_refusal(ConstraintSpec.try_create("C", UnitKind.MONEY, ComparisonOp.EQUAL, "widgets"))


# --- fp1 content -------------------------------------------------------------


def test_formula_fp1_identity_is_deterministic_and_carries_worked_example() -> None:
    formula = LADDER_FORMULAS[0]
    content = formula.fp1_identity()
    assert content == formula.fp1_identity()
    assert "worked_example" in content


def test_form_0006_fp1_identity_has_no_worked_example() -> None:
    content = FORM_0006.fp1_identity()
    assert "worked_example" not in content
    assert content["formula_id"] == "FORM-0006"


def test_constraint_fp1_identity_is_deterministic() -> None:
    content = SEAT_R_CEILING_CONSTRAINT.fp1_identity()
    assert content == SEAT_R_CEILING_CONSTRAINT.fp1_identity()
    assert content["op"] == "at-most"
