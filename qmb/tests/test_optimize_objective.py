"""Story 21.2 — Study objective, hard constraints, and the read-time winner set."""

from __future__ import annotations

from fractions import Fraction
from typing import TypeVar

from qmb._refuse import unavailable
from qmb.doors import api
from qmb.ledger import LedgerLine
from qmb.optimize import (
    DIRECTION_MAX,
    DIRECTION_MIN,
    INCOMPLETE_TRIAL_CONSTRAINT_MISSING,
    INCOMPLETE_TRIAL_OBJECTIVE_UNDEFINED,
    INCOMPLETE_TRIAL_REFUSED,
    MIN_TRADES_FLOOR_KEY,
    MIN_TRADES_GATE_DEFAULT_ON,
    MIN_TRADES_HAS_SPINE_CONSTANT,
    MIN_TRADES_MEASURE,
    OBJECTIVE_DIRECTIONS,
    STUDY_CONSTRAINT_OPERATORS,
    STUDY_CRITERIA_KEY,
    MinTradesGate,
    StudyConstraint,
    StudyCriteria,
    StudyObjective,
    StudyWinnerSet,
    coerce_study_criteria,
    compute_winner_set,
    study_criteria_identity,
)
from qmb.results import emit_measure
from qmf.core.exact import ExactRational, Money, UnitKind
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.performance import UndefinedMeasure

import qmb

T = TypeVar("T")

_BAR = fingerprint({"class": "book-bar", "id": "bar-1"})


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _fp(*parts: object) -> Fingerprint:
    return _ok(fingerprint({"parts": list(parts)}))


def _net_profit(minor: int) -> dict[str, object]:
    measure = _ok(emit_measure("net_profit", Money(value=minor, currency="USD", scale=2)))
    return measure.fp1_identity()


def _max_drawdown(num: int, den: int) -> dict[str, object]:
    quantity = _ok(ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO))
    return _ok(emit_measure("max_drawdown", quantity)).fp1_identity()


def _total_trades(count: int) -> dict[str, object]:
    quantity = _ok(ExactRational.try_create(count, 1, UnitKind.COUNT))
    return _ok(emit_measure("total_trades", quantity)).fp1_identity()


def _undefined(identity: str) -> dict[str, object]:
    refusal = unavailable(identity, "insufficient sample", code="undefined")
    return _ok(UndefinedMeasure.try_create(identity, 1, refusal)).fp1_identity()


def _trial(
    run: str,
    *,
    measures: tuple[dict[str, object], ...],
    world: World = World.REPLAY,
    role: str = "trial",
) -> LedgerLine:
    return LedgerLine(
        run_id=_fp("run", run),
        role=role,
        world=world,
        result_label={"class": "result-label", "world": world.value, "run": run},
        book_bar_fp1=_ok(_BAR),
        measures=measures,
        ct32_fingerprint=_fp("ct32", run),
    )


def _aborted(run: str) -> LedgerLine:
    return LedgerLine(
        run_id=_fp("run", run),
        role="aborted",
        world=World.REPLAY,
        result_label={"class": "result-label", "world": World.REPLAY.value, "run": run},
        book_bar_fp1=_ok(_BAR),
        measures=(),
        ct32_fingerprint=None,
        refusal={"category": "invalid input", "field": "terminal", "reason": "trial refused"},
    )


def _criteria(**kwargs: object) -> StudyCriteria:
    defaults: dict[str, object] = {"objective": {"measure": "net_profit", "direction": "max"}}
    defaults.update(kwargs)
    return _ok(coerce_study_criteria(defaults))


def _winners(lines: object, criteria: StudyCriteria) -> StudyWinnerSet:
    return _ok(compute_winner_set(lines, criteria, world=World.REPLAY))


# --- AC1: objective { measure, direction } with direction ∈ {min, max} --------


def test_objective_accepts_min_and_max_directions() -> None:
    maximize = _ok(StudyObjective.try_create("net_profit", "max"))
    minimize = _ok(StudyObjective.try_create("max_drawdown", "min"))
    assert maximize.direction == DIRECTION_MAX
    assert minimize.direction == DIRECTION_MIN
    assert OBJECTIVE_DIRECTIONS == ("min", "max")


def test_direction_outside_min_max_is_invalid_input() -> None:
    for bad in ("ascending", "descending", "minimize", "", None, "MAX "):
        refusal = StudyObjective.try_create("net_profit", bad)
        assert is_refusal(refusal), bad
        assert refusal.category is RefusalCategory.INVALID_INPUT
        assert refusal.context["field"] == "direction"


def test_criteria_created_from_mapping_and_pair_forms() -> None:
    declaration = {"objective": {"measure": "net_profit", "direction": "max"}}
    from_mapping = _ok(coerce_study_criteria(declaration))
    from_pair = _ok(StudyCriteria.try_create(("net_profit", "max")))
    assert from_mapping.objective.measure == "net_profit"
    assert from_pair.objective.direction == DIRECTION_MAX


# --- AC2: unresolvable metric → typed refusal at Study creation ---------------


def test_objective_metric_absent_from_roster_refused_at_creation() -> None:
    refusal = coerce_study_criteria({"objective": {"measure": "made_up", "direction": "max"}})
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "objective"


def test_constraint_metric_absent_from_roster_refused_at_creation() -> None:
    refusal = coerce_study_criteria(
        {
            "objective": {"measure": "net_profit", "direction": "max"},
            "constraints": [{"measure": "invented_metric", "op": "<", "value": 1}],
        }
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "constraint"


def test_composite_objective_is_refused_never_invented() -> None:
    refusal = StudyObjective.try_create("composite_score", "max")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION


def test_refusal_is_at_creation_time_not_trial_time() -> None:
    # No ledger line is ever consulted: the metric miss is caught building the criteria.
    refusal = coerce_study_criteria({"objective": {"measure": "nope", "direction": "min"}})
    assert is_refusal(refusal)


# --- AC3: hard constraints exclude a trial yet name the violation -------------


def test_constraint_violating_trial_excluded_but_named() -> None:
    lines = [
        _trial("t1", measures=(_net_profit(3000), _max_drawdown(1, 10))),
        _trial("t2", measures=(_net_profit(5000), _max_drawdown(3, 10))),
        _trial("t3", measures=(_net_profit(2000), _max_drawdown(1, 5))),
    ]
    # max_drawdown <= 0.20, caller-supplied bound (never invented).
    bound = _ok(
        StudyConstraint.try_create(
            "max_drawdown", "<=", _ok(ExactRational.try_create(1, 5, UnitKind.DIMENSIONLESS_RATIO))
        )
    )
    winner_set = _winners(lines, _criteria(constraints=(bound,)))

    winner_runs = [trial.run_id.value for trial in winner_set.winners]
    assert winner_runs == [_fp("run", "t1").value, _fp("run", "t3").value]
    # The violating trial is excluded from the winner set...
    assert winner_set.excluded_count == 1
    excluded = winner_set.excluded[0]
    assert excluded.run_id.value == _fp("run", "t2").value
    # ...yet still appears (in the ledger fold) with the violated constraint named.
    assert excluded.failed_constraints
    assert excluded.failed_constraints[0]["measure"] == "max_drawdown"
    assert excluded.failed_constraints[0]["operator"] == "<="


def test_all_six_symbolic_operators_are_accepted() -> None:
    assert STUDY_CONSTRAINT_OPERATORS == ("<", "<=", ">", ">=", "=", "!=")
    for op in STUDY_CONSTRAINT_OPERATORS:
        built = StudyConstraint.try_create("total_trades", op, 5)
        assert is_ok(built), op
        assert built.value.operator == op


def test_unknown_operator_is_invalid_input() -> None:
    refusal = StudyConstraint.try_create("total_trades", "lt", 5)
    assert is_refusal(refusal)
    assert refusal.context["field"] == "operator"


def test_no_constraint_ranks_every_completed_trial() -> None:
    lines = [
        _trial("t1", measures=(_net_profit(3000),)),
        _trial("t2", measures=(_net_profit(1000),)),
    ]
    winner_set = _winners(lines, _criteria(min_trades_enabled=False))
    assert winner_set.winner_count == 2
    assert winner_set.excluded_count == 0


def test_constraint_value_rejects_a_binary_float() -> None:
    refusal = StudyConstraint.try_create("max_drawdown", "<=", 0.2)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


# --- AC4: minimum-trades gate on by default; floor a blank-permitted configurable


def test_min_trades_gate_is_on_by_default_with_no_spine_constant() -> None:
    gate = MinTradesGate()
    assert gate.enabled is MIN_TRADES_GATE_DEFAULT_ON is True
    assert gate.configurable_key == MIN_TRADES_FLOOR_KEY
    assert MIN_TRADES_HAS_SPINE_CONSTANT is False
    assert MIN_TRADES_MEASURE == "total_trades"
    # On by default, but with a blank floor it is not yet active — no invented number.
    assert gate.floor is None
    assert gate.is_active is False


def test_blank_floor_is_permitted_and_excludes_nothing() -> None:
    # The default criteria leaves the floor blank: a degenerate 0-trade trial is
    # NOT excluded, because no threshold number is invented (thresholds deferred).
    lines = [_trial("t1", measures=(_net_profit(3000), _total_trades(0)))]
    winner_set = _winners(lines, _criteria())
    assert winner_set.winner_count == 1
    assert winner_set.excluded_count == 0
    # The gate contributes no constraint while the floor is blank.
    assert winner_set.constraints == ()


def test_a_configured_floor_excludes_the_degenerate_low_trade_trial() -> None:
    lines = [
        _trial("t1", measures=(_net_profit(9000), _total_trades(2))),
        _trial("t2", measures=(_net_profit(3000), _total_trades(50))),
    ]
    # The operator sets the floor through the UI-editable configurable.
    winner_set = _winners(lines, _criteria(min_trades_floor=5))
    winner_runs = [trial.run_id.value for trial in winner_set.winners]
    assert winner_runs == [_fp("run", "t2").value]
    assert winner_set.excluded_count == 1
    excluded = winner_set.excluded[0]
    assert excluded.run_id.value == _fp("run", "t1").value
    assert excluded.failed_constraints[0]["measure"] == MIN_TRADES_MEASURE


def test_min_trades_floor_rejects_a_binary_float_never_invents_a_number() -> None:
    refusal = MinTradesGate.resolve(3.5)
    assert is_refusal(refusal)
    assert refusal.context["field"] == "min_trades_floor"
    assert refusal.context["configurable"] == MIN_TRADES_FLOOR_KEY


def test_min_trades_gate_can_be_turned_off() -> None:
    criteria = _criteria(min_trades_enabled=False, min_trades_floor=5)
    assert criteria.min_trades_gate.is_active is False
    assert criteria.effective_constraints == ()


# --- AC5: optional target_value may stop the Study early ----------------------


def test_target_value_reached_signals_early_stop_with_partial_preserved() -> None:
    objective = {"measure": "net_profit", "direction": "max", "target_value": {"num": 40, "den": 1}}
    criteria = _criteria(objective=objective, min_trades_enabled=False)
    # Only two of a planned larger Study have completed — a partial generation.
    partial = [
        _trial("t1", measures=(_net_profit(2000),)),
        _trial("t2", measures=(_net_profit(5000),)),  # net_profit 50 >= target 40
    ]
    winner_set = _winners(partial, criteria)
    assert winner_set.target_reached is True
    reached = {trial.run_id.value for trial in winner_set.target_trials}
    assert reached == {_fp("run", "t2").value}
    # Partial results are preserved: the winner set ranks exactly the trials seen.
    assert winner_set.winner_count == 2
    assert winner_set.winner is not None
    assert winner_set.winner.run_id.value == _fp("run", "t2").value


def test_min_direction_target_is_reached_at_or_below() -> None:
    objective = {
        "measure": "max_drawdown",
        "direction": "min",
        "target_value": {"num": 1, "den": 10},
    }
    criteria = _criteria(objective=objective, min_trades_enabled=False)
    lines = [
        _trial("t1", measures=(_max_drawdown(3, 10),)),
        _trial("t2", measures=(_max_drawdown(1, 20),)),  # 0.05 <= 0.10 target
    ]
    winner_set = _winners(lines, criteria)
    assert winner_set.target_reached is True
    assert winner_set.winner is not None
    assert winner_set.winner.objective_value == Fraction(1, 20)


def test_no_target_never_stops_early() -> None:
    criteria = _criteria(min_trades_enabled=False)  # no target_value
    lines = [_trial("t1", measures=(_net_profit(999999),))]
    winner_set = _winners(lines, criteria)
    assert winner_set.target_reached is False
    assert winner_set.target_trials == ()


def test_target_only_counts_a_constraint_passing_trial() -> None:
    # A trial that meets the target but violates a hard constraint must NOT trigger
    # early stop — a degenerate fit never wins.
    objective = {"measure": "net_profit", "direction": "max", "target_value": {"num": 40, "den": 1}}
    bound = _ok(
        StudyConstraint.try_create(
            "max_drawdown", "<=", _ok(ExactRational.try_create(1, 5, UnitKind.DIMENSIONLESS_RATIO))
        )
    )
    criteria = _criteria(objective=objective, constraints=(bound,), min_trades_enabled=False)
    # t1 meets the target (net_profit 50 >= 40) but its drawdown 0.40 violates the bound.
    lines = [_trial("t1", measures=(_net_profit(5000), _max_drawdown(4, 10)))]
    winner_set = _winners(lines, criteria)
    assert winner_set.target_reached is False
    assert winner_set.excluded_count == 1


# --- AC6: winner is a read-time ranking over role=trial lines, no verdict ------


def test_winner_is_ranked_over_role_trial_lines_only() -> None:
    lines = [
        _trial("t1", measures=(_net_profit(3000),), role="trial"),
        _trial("c1", measures=(_net_profit(9000),), role="confirmation"),
    ]
    winner_set = _winners(lines, _criteria(min_trades_enabled=False))
    assert winner_set.role == "trial"
    assert {trial.run_id.value for trial in winner_set.winners} == {_fp("run", "t1").value}


def test_winner_ordering_respects_direction() -> None:
    lines = [
        _trial("t1", measures=(_net_profit(3000),)),
        _trial("t2", measures=(_net_profit(1000),)),
        _trial("t3", measures=(_net_profit(2000),)),
    ]
    maximize = _winners(lines, _criteria(min_trades_enabled=False))
    assert [t.objective_value for t in maximize.winners] == [30, 20, 10]
    assert maximize.winner is not None and maximize.winner.objective_value == 30

    minimize = _winners(lines, _criteria(objective=("net_profit", "min"), min_trades_enabled=False))
    assert [t.objective_value for t in minimize.winners] == [10, 20, 30]
    assert minimize.winner is not None and minimize.winner.objective_value == 10


def test_winner_carries_optimistic_taint_and_makes_no_edge_or_verdict() -> None:
    lines = [_trial("t1", measures=(_net_profit(3000),))]
    winner_set = _winners(lines, _criteria(min_trades_enabled=False))
    trial = winner_set.winners[0]
    assert trial.taint == "optimistic"
    assert trial.makes_edge_claim is False
    assert winner_set.makes_edge_claim is False
    assert winner_set.makes_bar_verdict is False
    assert winner_set.verdict_deferred_to == "GAP-0048"


def test_winner_set_identity_carries_no_verdict_or_score() -> None:
    lines = [_trial("t1", measures=(_net_profit(3000),))]
    identity = _winners(lines, _criteria(min_trades_enabled=False)).fp1_identity()
    banned = {"verdict", "pass", "fail", "rated", "score", "rating", "tier"}
    assert banned.isdisjoint(identity)
    assert identity["makes_bar_verdict"] is False
    assert identity["makes_edge_claim"] is False


def test_aborted_trial_is_incomplete_never_ranked_or_zeroed() -> None:
    lines = [
        _trial("t1", measures=(_net_profit(3000),)),
        _aborted("t2"),
    ]
    winner_set = _winners(lines, _criteria(min_trades_enabled=False))
    assert winner_set.winner_count == 1
    assert winner_set.incomplete_count == 1
    assert winner_set.incomplete[0].reason == INCOMPLETE_TRIAL_REFUSED
    assert all(t.run_id.value != _fp("run", "t2").value for t in winner_set.winners)


def test_undefined_objective_is_incomplete_not_zero() -> None:
    lines = [
        _trial("t1", measures=(_net_profit(3000),)),
        _trial("t2", measures=(_undefined("net_profit"),)),
    ]
    winner_set = _winners(lines, _criteria(min_trades_enabled=False))
    assert winner_set.winner_count == 1
    assert winner_set.incomplete_count == 1
    assert winner_set.incomplete[0].reason == INCOMPLETE_TRIAL_OBJECTIVE_UNDEFINED


def test_missing_constraint_metric_is_incomplete() -> None:
    # total_trades floor is active but the trial never emitted total_trades.
    lines = [_trial("t1", measures=(_net_profit(3000),))]
    winner_set = _winners(lines, _criteria(min_trades_floor=5))
    assert winner_set.winner_count == 0
    assert winner_set.incomplete_count == 1
    assert winner_set.incomplete[0].reason == INCOMPLETE_TRIAL_CONSTRAINT_MISSING


def test_winner_set_is_deterministic_regardless_of_input_order() -> None:
    lines = [
        _trial("t1", measures=(_net_profit(3000),)),
        _trial("t2", measures=(_net_profit(1000),)),
        _trial("t3", measures=(_net_profit(2000),)),
        _aborted("t4"),
    ]
    criteria = _criteria(min_trades_enabled=False)
    first = _winners(lines, criteria)
    second = _winners(list(reversed(lines)), criteria)
    assert first.fp1_identity() == second.fp1_identity()
    assert _ok(first.fingerprint()).value == _ok(second.fingerprint()).value


# --- criteria as identity-bearing config -------------------------------------


def test_criteria_is_identity_bearing_and_reproducible() -> None:
    declaration = {
        "objective": {"measure": "net_profit", "direction": "max"},
        "constraints": [{"measure": "max_drawdown", "op": "<=", "value": {"num": 1, "den": 5}}],
        "min_trades_floor": 5,
    }
    criteria = _ok(coerce_study_criteria(declaration))
    layer = criteria.run_config_layer()
    assert layer[STUDY_CRITERIA_KEY] == criteria.fp1_identity()
    assert _ok(criteria.fingerprint()).value.startswith("fp1:")
    # Same objective + constraints reproduce one fingerprint (NFR-03) — no binary
    # float ever enters identity because the value carries num/den, not a float.
    twin = _ok(coerce_study_criteria(dict(declaration)))
    assert _ok(criteria.fingerprint()).value == _ok(twin.fingerprint()).value


def test_criteria_identity_excludes_semver() -> None:
    identity = study_criteria_identity()
    assert "version" not in identity
    assert identity["objective_directions"] == OBJECTIVE_DIRECTIONS
    assert identity["min_trades_has_spine_constant"] is False
    assert identity["winner_makes_edge_claim"] is False
    assert identity["winner_makes_bar_verdict"] is False


# --- door parity --------------------------------------------------------------


def test_door_reexports_the_study_objective_surface() -> None:
    assert api.compute_winner_set is qmb.compute_winner_set
    assert api.coerce_study_criteria is qmb.coerce_study_criteria
    assert api.StudyCriteria is qmb.StudyCriteria
    for name in (
        "StudyObjective",
        "StudyConstraint",
        "StudyCriteria",
        "StudyWinnerSet",
        "MinTradesGate",
        "coerce_study_criteria",
        "compute_winner_set",
        "study_criteria_identity",
        "STUDY_CRITERIA_KEY",
        "MIN_TRADES_FLOOR_KEY",
    ):
        assert name in qmb.__all__
        assert name in api.__all__
