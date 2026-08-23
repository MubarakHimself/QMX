"""Story 10.2 AC3/AC4 — the units-only sizing shape and the B-split.

Verifies the money_rules sizing shape carries units only with no ratified values
(book_capital, loss_floor, loss_runway, period_loss_budget, r_unit_price,
seat_loss_run_allowance, seat_r_ceiling, position_risk_amount), that loss_floor is the
same number the kill line names (read by both, never two floors that drift), that
seat_r_ceiling ≤ seat_loss_run_allowance holds in pure R-space, and that the B-split
holds — bench_consecutive_loss_threshold [count] in leash_grammar and
seat_loss_run_allowance [r_multiple] in money_rules — with the unit-kind checker
refusing a count standing where an r_multiple is declared (CT-22; DEC-0154, DEC-0155).
"""

from __future__ import annotations

from qmf.core import ExactRational, Money, RefusalCategory, UnitKind, is_ok, is_refusal
from qmf.risk.grammar import (
    AdmissionImpact,
    NotYetRuled,
    TemplateSection,
    TemplateVariable,
    UiEditability,
    VariableValue,
)
from qmf.risk.sizing import (
    BENCH_THRESHOLD_VARIABLE,
    LEASH_B_SPLIT_UNIT_KINDS,
    MONEY_RULES_UNIT_KINDS,
    SEAT_LOSS_RUN_ALLOWANCE_VARIABLE,
    check_b_split,
    check_seat_r_ceiling,
    reconcile_loss_floor,
    validate_money_rules,
)


def _blank() -> NotYetRuled:
    result = NotYetRuled.try_create("GAP-0048")
    assert is_ok(result)
    return result.value


def _variable(
    name: str, unit_kind: UnitKind, value: VariableValue | NotYetRuled
) -> TemplateVariable:
    result = TemplateVariable.try_create(
        name=name,
        unit_kind=unit_kind,
        value=value,
        ui_editable=UiEditability.UI_EDITABLE,
        admission_impact=AdmissionImpact.RESIGN,
    )
    assert is_ok(result)
    return result.value


def _money(value: int) -> Money:
    return Money(value=value, currency="USD", scale=2)


def _r(numerator: int, denominator: int = 1) -> ExactRational:
    result = ExactRational.try_create(numerator, denominator, UnitKind.R_MULTIPLE)
    assert is_ok(result)
    return result.value


def _rate(numerator: int) -> ExactRational:
    result = ExactRational.try_create(numerator, 1, UnitKind.RATE)
    assert is_ok(result)
    return result.value


def _count(value: int) -> ExactRational:
    result = ExactRational.try_create(value, 1, UnitKind.COUNT)
    assert is_ok(result)
    return result.value


def _money_rules(
    *,
    seat_loss_run_allowance: TemplateVariable | None = None,
    seat_r_ceiling: TemplateVariable | None = None,
    drop: str | None = None,
) -> TemplateSection:
    """Build a money_rules section with every required variable (units only)."""
    variables: dict[str, TemplateVariable] = {
        "book_capital": _variable("book_capital", UnitKind.MONEY, _money(1_000_000)),
        "loss_floor": _variable("loss_floor", UnitKind.MONEY, _money(800_000)),
        "loss_runway": _variable("loss_runway", UnitKind.MONEY, _money(200_000)),
        "period_loss_budget": _variable("period_loss_budget", UnitKind.MONEY, _money(10_000)),
        "r_unit_price": _variable("r_unit_price", UnitKind.RATE, _rate(25)),
        SEAT_LOSS_RUN_ALLOWANCE_VARIABLE: seat_loss_run_allowance
        or _variable(SEAT_LOSS_RUN_ALLOWANCE_VARIABLE, UnitKind.R_MULTIPLE, _r(4)),
        "seat_r_ceiling": seat_r_ceiling or _variable("seat_r_ceiling", UnitKind.R_MULTIPLE, _r(2)),
        "position_risk_amount": _variable("position_risk_amount", UnitKind.MONEY, _money(5_000)),
    }
    if drop is not None:
        del variables[drop]
    result = TemplateSection.try_create("money_rules", variables)
    assert is_ok(result)
    return result.value


def _leash_grammar(bench: TemplateVariable | None = None) -> TemplateSection:
    bench_variable = bench or _variable(BENCH_THRESHOLD_VARIABLE, UnitKind.COUNT, _count(2))
    result = TemplateSection.try_create("leash_grammar", {BENCH_THRESHOLD_VARIABLE: bench_variable})
    assert is_ok(result)
    return result.value


# --- the units-only shape (AC3) ----------------------------------------------


def test_money_rules_unit_kinds_are_the_ratified_units_only_shape() -> None:
    assert MONEY_RULES_UNIT_KINDS["book_capital"] is UnitKind.MONEY
    assert MONEY_RULES_UNIT_KINDS["loss_floor"] is UnitKind.MONEY
    assert MONEY_RULES_UNIT_KINDS["loss_runway"] is UnitKind.MONEY
    assert MONEY_RULES_UNIT_KINDS["period_loss_budget"] is UnitKind.MONEY
    assert MONEY_RULES_UNIT_KINDS["r_unit_price"] is UnitKind.RATE
    assert MONEY_RULES_UNIT_KINDS["seat_loss_run_allowance"] is UnitKind.R_MULTIPLE
    assert MONEY_RULES_UNIT_KINDS["seat_r_ceiling"] is UnitKind.R_MULTIPLE
    assert MONEY_RULES_UNIT_KINDS["position_risk_amount"] is UnitKind.MONEY
    assert LEASH_B_SPLIT_UNIT_KINDS[BENCH_THRESHOLD_VARIABLE] is UnitKind.COUNT


def test_valid_money_rules_shape_passes() -> None:
    result = validate_money_rules(_money_rules())
    assert is_ok(result)


def test_money_rules_shape_ratifies_no_values_all_blanks_pass() -> None:
    # Units only, no ratified values: every number may ship as a NotYetRuled blank.
    variables = {
        name: _variable(name, kind, _blank()) for name, kind in MONEY_RULES_UNIT_KINDS.items()
    }
    section = TemplateSection.try_create("money_rules", variables)
    assert is_ok(section)
    assert is_ok(validate_money_rules(section.value))


def test_money_rules_rejects_wrong_section_name() -> None:
    ok = _money_rules()
    renamed = TemplateSection.try_create("charter", dict(ok.variables))
    assert is_ok(renamed)
    result = validate_money_rules(renamed.value)
    assert is_refusal(result)
    assert result.context["field"] == "section"


def test_money_rules_rejects_non_section() -> None:
    result = validate_money_rules({"book_capital": "money"})
    assert is_refusal(result)


def test_money_rules_rejects_a_missing_required_variable() -> None:
    result = validate_money_rules(_money_rules(drop="r_unit_price"))
    assert is_refusal(result)
    assert result.context["missing"] == "r_unit_price"


def test_money_rules_refuses_a_count_where_an_r_multiple_is_declared() -> None:
    # The B-split at the shape level: seat_loss_run_allowance declared as a count.
    miscast = _variable(SEAT_LOSS_RUN_ALLOWANCE_VARIABLE, UnitKind.COUNT, _count(4))
    result = validate_money_rules(_money_rules(seat_loss_run_allowance=miscast))
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["variable"] == SEAT_LOSS_RUN_ALLOWANCE_VARIABLE
    assert result.context["declared"] == "count"
    assert result.context["expected"] == "r-multiple"


def test_money_rules_enforces_seat_r_ceiling_value_bound() -> None:
    # seat_r_ceiling (5) above seat_loss_run_allowance (4) is a policy rejection.
    ceiling = _variable("seat_r_ceiling", UnitKind.R_MULTIPLE, _r(5))
    result = validate_money_rules(_money_rules(seat_r_ceiling=ceiling))
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


# --- seat_r_ceiling <= seat_loss_run_allowance in pure R-space ---------------


def test_seat_r_ceiling_at_or_below_allowance_passes() -> None:
    assert is_ok(check_seat_r_ceiling(_r(4), _r(4)))
    assert is_ok(check_seat_r_ceiling(_r(2), _r(4)))


def test_seat_r_ceiling_above_allowance_is_policy_rejection() -> None:
    result = check_seat_r_ceiling(_r(5), _r(4))
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_seat_r_ceiling_blank_passes_blank_blocks_live_money_elsewhere() -> None:
    assert is_ok(check_seat_r_ceiling(_blank(), _r(4)))
    assert is_ok(check_seat_r_ceiling(_r(2), _blank()))


def test_seat_r_ceiling_rejects_non_r_multiple_operands() -> None:
    assert is_refusal(check_seat_r_ceiling(_count(2), _r(4)))
    assert is_refusal(check_seat_r_ceiling(_r(2), _count(4)))
    assert is_refusal(check_seat_r_ceiling("2", _r(4)))


# --- the B-split across sections (AC4) ---------------------------------------


def test_b_split_holds_across_sections() -> None:
    assert is_ok(check_b_split(_money_rules(), _leash_grammar()))


def test_b_split_refuses_a_count_seat_loss_run_allowance() -> None:
    miscast = _variable(SEAT_LOSS_RUN_ALLOWANCE_VARIABLE, UnitKind.COUNT, _count(4))
    result = check_b_split(_money_rules(seat_loss_run_allowance=miscast), _leash_grammar())
    assert is_refusal(result)
    assert result.context["variable"] == SEAT_LOSS_RUN_ALLOWANCE_VARIABLE
    assert result.context["expected"] == "r-multiple"


def test_b_split_refuses_an_r_multiple_bench_threshold() -> None:
    miscast = _variable(BENCH_THRESHOLD_VARIABLE, UnitKind.R_MULTIPLE, _r(2))
    result = check_b_split(_money_rules(), _leash_grammar(bench=miscast))
    assert is_refusal(result)
    assert result.context["variable"] == BENCH_THRESHOLD_VARIABLE
    assert result.context["expected"] == "count"


def test_b_split_refuses_missing_bench_threshold() -> None:
    empty = TemplateSection.try_create("leash_grammar", {})
    assert is_ok(empty)
    result = check_b_split(_money_rules(), empty.value)
    assert is_refusal(result)
    assert result.context["missing"] == BENCH_THRESHOLD_VARIABLE


def test_b_split_refuses_missing_allowance() -> None:
    result = check_b_split(_money_rules(drop=SEAT_LOSS_RUN_ALLOWANCE_VARIABLE), _leash_grammar())
    assert is_refusal(result)


def test_b_split_rejects_wrong_sections() -> None:
    assert is_refusal(check_b_split("money_rules", _leash_grammar()))
    assert is_refusal(check_b_split(_money_rules(), "leash_grammar"))


# --- loss_floor is the same number the kill line names (AC3) ------------------


def test_loss_floor_equals_kill_line_passes() -> None:
    assert is_ok(reconcile_loss_floor(_money(800_000), _money(800_000)))


def test_loss_floor_drift_from_kill_line_is_policy_rejection() -> None:
    result = reconcile_loss_floor(_money(800_000), _money(750_000))
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_loss_floor_cross_currency_drift_is_refused() -> None:
    result = reconcile_loss_floor(_money(800_000), Money(value=800_000, currency="JPY", scale=2))
    assert is_refusal(result)


def test_loss_floor_two_matching_blanks_pass() -> None:
    assert is_ok(reconcile_loss_floor(_blank(), _blank()))


def test_loss_floor_blank_vs_ruled_has_drifted() -> None:
    result = reconcile_loss_floor(_blank(), _money(800_000))
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_loss_floor_two_blanks_awaiting_different_gaps_have_drifted() -> None:
    other = NotYetRuled.try_create("GAP-0049")
    assert is_ok(other)
    result = reconcile_loss_floor(_blank(), other.value)
    assert is_refusal(result)


def test_loss_floor_rejects_non_money_non_blank() -> None:
    assert is_refusal(reconcile_loss_floor("800000", _money(800_000)))
    assert is_refusal(reconcile_loss_floor(_money(800_000), "800000"))
