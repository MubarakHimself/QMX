"""Group B — Study objective & hard constraints (Story 21.2) -> R6-R12, R9.

Public surfaces driven: ``StudyObjective.try_create``, ``coerce_study_criteria``,
``MinTradesGate.resolve``, and the read-time fold ``compute_winner_set`` over
``role = trial`` ledger lines. Includes REGRESSION PIN-1 (T21-309).
"""

from __future__ import annotations

from conftest import (
    Fraction,
    RefusalCategory,
    assert_ct04_refusal,
    collect_string_values,
    is_ok,
    is_refusal,
    money_measure,
    run_id_of,
    trial_line,
    unwrap,
    usd,
)

from qmb.optimize.objective import (
    MinTradesGate,
    StudyConstraint,
    StudyCriteria,
    StudyObjective,
    coerce_study_criteria,
    compute_winner_set,
)
from qmf.core.fingerprint import World


def _criteria(objective: StudyObjective, *constraints: StudyConstraint) -> StudyCriteria:
    return unwrap(StudyCriteria.try_create(objective, constraints=tuple(constraints)), "criteria")


# --- T21-306 [R6] ------------------------------------------------------------


def test_t21_306_objective_direction_admission() -> None:
    """min/max are accepted; a direction outside {min,max} refuses invalid input.

    Counter-case that would FAIL: a bogus direction accepted, or min/max rejected.
    """
    assert is_ok(StudyObjective.try_create("net_profit", "max"))
    assert is_ok(StudyObjective.try_create("max_drawdown", "min"))
    bad = StudyObjective.try_create("net_profit", "sideways")
    assert_ct04_refusal(bad, RefusalCategory.INVALID_INPUT, what="bad direction")


# --- T21-307 [R7] ------------------------------------------------------------


def test_t21_307_unknown_metric_refused_at_creation() -> None:
    """A metric absent from the roster refuses at Study creation, never at trial time.

    Counter-case that would FAIL: an off-roster measure accepted at creation.
    coerce_study_criteria schedules no trial, so a refusal here is creation-time.
    """
    good = coerce_study_criteria({"objective": {"measure": "net_profit", "direction": "max"}})
    assert is_ok(good), f"a roster metric must be accepted, got {good!r}"

    bad_objective = coerce_study_criteria({"objective": {"measure": "totally_made_up", "direction": "max"}})
    assert_ct04_refusal(bad_objective, RefusalCategory.INVALID_INPUT, what="off-roster objective")

    bad_constraint = coerce_study_criteria(
        {
            "objective": {"measure": "net_profit", "direction": "max"},
            "constraints": [{"measure": "not_a_metric", "op": ">=", "value": 1}],
        }
    )
    assert_ct04_refusal(bad_constraint, RefusalCategory.INVALID_INPUT, what="off-roster constraint")


# --- T21-308 [R8] ------------------------------------------------------------


def test_t21_308_constraint_violator_excluded_but_present() -> None:
    """A constraint-violating trial is held out of the winner set yet named in the ledger.

    Counter-case that would FAIL: the violator ranked as a winner, or dropped entirely
    (absent from both winners and excluded), or excluded without naming the constraint.
    """
    objective = unwrap(StudyObjective.try_create("net_profit", "max"))
    constraint = unwrap(StudyConstraint.try_create("max_drawdown", "<=", 100))
    criteria = _criteria(objective, constraint)

    passing = trial_line("pass", [money_measure("net_profit", 50000), money_measure("max_drawdown", 5000)])
    violating = trial_line("viol", [money_measure("net_profit", 60000), money_measure("max_drawdown", 20000)])

    result = compute_winner_set([passing, violating], criteria, world=World.REPLAY)
    ws = unwrap(result, "winner set")

    winner_ids = {trial.run_id.value for trial in ws.winners}
    excluded_ids = {trial.run_id.value for trial in ws.excluded}
    assert run_id_of("pass") in winner_ids, "the constraint-passing trial ranks"
    assert run_id_of("viol") not in winner_ids, "the violator is not a winner"
    assert run_id_of("viol") in excluded_ids, "the violator still appears (excluded, not dropped)"

    excluded = next(t for t in ws.excluded if t.run_id.value == run_id_of("viol"))
    named = [c.get("measure") for c in excluded.failed_constraints]
    assert "max_drawdown" in named, "the excluded trial names the violated constraint"


# --- T21-309 [R10] P0 REGRESSION PIN-1 (cross-currency target_value) ---------


def test_t21_309_cross_currency_target_is_typed_refusal() -> None:
    """A target_value in a different currency than the measure must be a typed refusal.

    PIN-1 [R-001]. The requirement (CT-01 unit-kind law): a money-kind objective whose
    optional target_value is declared in a *different* currency must return a CT-04
    refusal at the point the "trial meets target_value" test is evaluated — never a
    silent numeric comparison treating the other currency's count as this one's.

    Falsifiability / meaningfulness companion runs first: a SAME-currency target
    compares cleanly (Ok, target reached). Then the cross-currency case is asserted to
    refuse. Expected to FAIL against current source if the finding is real; the actual
    outcome is recorded honestly.
    """
    measure_line = trial_line("t", [money_measure("net_profit", 50000, "USD")])  # net_profit = 500 USD

    # Companion (same currency): a valid USD target below 500 is reached, cleanly.
    same = unwrap(StudyObjective.try_create("net_profit", "max", target_value=usd(30000, "USD")))
    same_ws = unwrap(
        compute_winner_set([measure_line], _criteria(same), world=World.REPLAY), "same-currency"
    )
    assert same_ws.target_reached is True, "a same-currency target of 300 USD is reached by 500 USD"

    # PIN-1: a EUR target against a USD measure must be a typed refusal, not a silent compare.
    cross = unwrap(StudyObjective.try_create("net_profit", "max", target_value=usd(30000, "EUR")))
    result = compute_winner_set([measure_line], _criteria(cross), world=World.REPLAY)
    assert is_refusal(result), (
        "a cross-currency target_value (EUR target vs USD measure) must return a CT-04 "
        f"typed refusal, never a silent numeric 'meets it' comparison; got {result!r}"
    )
    assert result.category in (RefusalCategory.POLICY_REJECTION, RefusalCategory.INVALID_INPUT)


# --- T21-310 [R11] -----------------------------------------------------------


def test_t21_310_valid_target_reached_preserves_partial_results() -> None:
    """A valid same-unit target that a trial meets flags target_reached with winners kept.

    Counter-case that would FAIL: target_reached True when no trial meets the target,
    or the winners emptied when the target is reached.
    """
    objective = unwrap(StudyObjective.try_create("net_profit", "max", target_value=usd(40000, "USD")))
    criteria = _criteria(objective)

    below = trial_line("lo", [money_measure("net_profit", 20000)])  # 200 < 400 target
    at_or_above = trial_line("hi", [money_measure("net_profit", 50000)])  # 500 >= 400 target

    reached = unwrap(compute_winner_set([below, at_or_above], criteria, world=World.REPLAY), "reached")
    assert reached.target_reached is True
    assert reached.winner_count >= 1, "partial winners are preserved when the target is reached"
    assert any(t.meets_target for t in reached.winners)

    not_reached = unwrap(compute_winner_set([below], criteria, world=World.REPLAY), "not reached")
    assert not_reached.target_reached is False, "no trial meets the target -> no early stop"


# --- T21-311 [R12] -----------------------------------------------------------


def test_t21_311_winner_is_ranking_no_edge_no_verdict() -> None:
    """The winner is a read-time ranking carrying the optimistic taint, no edge, no verdict.

    Counter-case that would FAIL: the ranking wrong (a non-best trial named winner), the
    winner's taint not optimistic, or an edge/bar-verdict token present in identity.
    """
    objective = unwrap(StudyObjective.try_create("net_profit", "max"))
    criteria = _criteria(objective)
    lines = [
        trial_line("a", [money_measure("net_profit", 10000)]),
        trial_line("b", [money_measure("net_profit", 90000)]),  # best
        trial_line("c", [money_measure("net_profit", 50000)]),
    ]
    ws = unwrap(compute_winner_set(lines, criteria, world=World.REPLAY), "winner set")

    # read-time ranking: best objective first (behavioural, not a self-declared flag).
    assert ws.winner is not None
    assert ws.winner.run_id.value == run_id_of("b"), "the max-objective trial ranks first"
    assert ws.winner.objective_value == Fraction(900, 1)

    # optimistic taint carried; no edge/bar verdict minted.
    assert ws.winner.taint == "optimistic"
    identity = ws.fp1_identity()
    strings = set(collect_string_values(identity))
    forbidden = {"bar-pass", "bar-fail", "pass", "fail", "rated", "verdict", "edge"}
    assert not (strings & forbidden), f"winner-set identity carries a verdict/edge token: {strings & forbidden}"


# --- R9 (min-trades gate, folded into Group B) -------------------------------


def test_t21_r9_min_trades_gate_default_on_blank_floor_invents_nothing() -> None:
    """The gate is on by default; a blank floor excludes nothing and invents no number.

    Counter-case that would FAIL: a blank floor synthesising a threshold (an active
    constraint), or the gate off by default, or a configured floor not producing a
    total_trades >= floor constraint.
    """
    blank = unwrap(MinTradesGate.resolve(None), "blank gate")
    assert blank.enabled is True, "the minimum-trades gate is on by default"
    assert blank.is_active is False, "a blank floor excludes nothing (no invented number)"
    assert blank.as_constraint() is None, "no total_trades constraint is invented while blank"

    configured = unwrap(MinTradesGate.resolve(5), "configured gate")
    assert configured.is_active is True
    constraint = configured.as_constraint()
    assert constraint is not None
    assert constraint.measure == "total_trades"
    assert constraint.operator == ">="
    assert constraint.value == Fraction(5)

    # A non-integer floor invents nothing — it is refused, not coerced.
    assert_ct04_refusal(MinTradesGate.resolve(2.5), RefusalCategory.INVALID_INPUT, what="float floor")
