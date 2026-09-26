"""Reference usage — Study objective, hard constraints, and the winner set (Story 21.2).

Executable::

    python qmb/examples/optimize_objective_usage.py

Shows the things B-8 / B-10 / Story 21.2 pin down:

1. A Study names ONE objective { measure_identity, direction in min|max } plus any
   number of hard { measure_identity, op, value } constraints, all validated at
   Study creation. A direction outside {min, max} is a typed invalid-input refusal;
   a metric absent from the AD-23/AD-41 roster is refused up front, never at trial
   time.
2. The winner set is a read-time ranking over ledger role=trial lines. A trial that
   violates a hard constraint is excluded from the winner set yet still carries the
   violated constraint named; the winner makes no edge claim and no bar verdict, and
   every trial keeps its optimistic taint until GAP-0048.
3. The minimum-trades gate rides as a hard constraint, on by default. Its floor is a
   UI-editable configurable with no spine constant: blank leaves it inert (no
   invented number); a configured floor excludes a degenerate low-trade fit.
4. An optional target_value lets a completed generation stop the Study early, with
   the partial winner set preserved.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.doors import api
from qmf.core.exact import ExactRational, Money, UnitKind
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _fp(*parts: object) -> Fingerprint:
    return _unwrap(fingerprint({"parts": list(parts)}), "fp")


def _net_profit(minor: int) -> dict[str, object]:
    money = Money(value=minor, currency="USD", scale=2)
    return _unwrap(api.emit_measure("net_profit", money), "np").fp1_identity()


def _max_drawdown(num: int, den: int) -> dict[str, object]:
    quantity = _unwrap(ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO), "dd")
    return _unwrap(api.emit_measure("max_drawdown", quantity), "dd measure").fp1_identity()


def _total_trades(count: int) -> dict[str, object]:
    quantity = _unwrap(ExactRational.try_create(count, 1, UnitKind.COUNT), "count")
    return _unwrap(api.emit_measure("total_trades", quantity), "tt measure").fp1_identity()


def _trial(run: str, *measures: dict[str, object]) -> api.LedgerLine:
    return api.LedgerLine(
        run_id=_fp("run", run),
        role="trial",
        world=World.REPLAY,
        result_label={"class": "result-label", "world": World.REPLAY.value, "run": run},
        book_bar_fp1=_fp("book-bar", "bar-1"),
        measures=measures,
        ct32_fingerprint=_fp("ct32", run),
    )


def main() -> None:
    # 1. Objective + constraints validated at Study creation.
    criteria = _unwrap(
        api.coerce_study_criteria(
            {
                "objective": {"measure": "net_profit", "direction": "max"},
                "constraints": [
                    {"measure": "max_drawdown", "op": "<=", "value": {"num": 1, "den": 5}}
                ],
            }
        ),
        "study criteria",
    )
    assert isinstance(criteria, qmb.StudyCriteria)
    assert criteria.objective.direction == "max"
    print("objective { net_profit, max } and one hard constraint validated at Study creation")

    # A direction outside {min, max}, and a metric absent from the roster, are both
    # typed refusals returned at creation time, never deferred to trial time.
    bad_direction = api.coerce_study_criteria(
        {"objective": {"measure": "net_profit", "direction": "up"}}
    )
    assert is_refusal(bad_direction)
    assert bad_direction.category is RefusalCategory.INVALID_INPUT
    absent = api.coerce_study_criteria({"objective": {"measure": "made_up", "direction": "max"}})
    assert is_refusal(absent)
    print("direction outside min|max and an off-roster metric refused at creation, not at trial")

    # 2. Winner set over role=trial lines: the constraint-violator is excluded but named.
    lines = [
        _trial("t1", _net_profit(3000), _max_drawdown(1, 10)),
        _trial("t2", _net_profit(5000), _max_drawdown(3, 10)),  # drawdown 0.30 > 0.20 bound
        _trial("t3", _net_profit(2000), _max_drawdown(1, 5)),
    ]
    winner_set = _unwrap(api.compute_winner_set(lines, criteria, world=World.REPLAY), "winners")
    winner_runs = [trial.run_id.value for trial in winner_set.winners]
    assert winner_runs == [_fp("run", "t1").value, _fp("run", "t3").value]
    assert winner_set.excluded_count == 1
    assert winner_set.excluded[0].failed_constraints[0]["measure"] == "max_drawdown"
    assert winner_set.winner is not None
    assert winner_set.winner.run_id.value == _fp("run", "t1").value
    print("winner set ranks role=trial lines; the constraint-violating trial is excluded but named")

    # The winner claims no edge and mints no bar verdict; the taint stands until GAP-0048.
    assert winner_set.makes_edge_claim is False
    assert winner_set.makes_bar_verdict is False
    assert winner_set.verdict_deferred_to == "GAP-0048"
    assert all(trial.taint == "optimistic" for trial in winner_set.winners)
    print("the winner keeps the optimistic taint, no edge claim, no bar verdict until GAP-0048")

    # 3. The minimum-trades gate: on by default, blank floor invents no number.
    degenerate = [
        _trial("d1", _net_profit(9000), _total_trades(1)),
        _trial("d2", _net_profit(3000), _total_trades(40)),
    ]
    blank = _unwrap(
        api.coerce_study_criteria({"objective": {"measure": "net_profit", "direction": "max"}}),
        "blank-floor criteria",
    )
    assert blank.min_trades_gate.enabled is True
    assert blank.min_trades_gate.is_active is False  # blank floor excludes nothing
    blank_won = _unwrap(api.compute_winner_set(degenerate, blank, world=World.REPLAY), "blank")
    assert blank_won.winner_count == 2 and blank_won.excluded_count == 0
    print("the min-trades gate is on by default; a blank floor excludes nothing, invents no number")

    floored = _unwrap(
        api.coerce_study_criteria(
            {"objective": {"measure": "net_profit", "direction": "max"}, "min_trades_floor": 5}
        ),
        "floored criteria",
    )
    floored_won = _unwrap(api.compute_winner_set(degenerate, floored, world=World.REPLAY), "won")
    assert [t.run_id.value for t in floored_won.winners] == [_fp("run", "d2").value]
    assert floored_won.excluded[0].failed_constraints[0]["measure"] == "total_trades"
    print("a configured UI-editable floor excludes the degenerate low-trade fit as a named bound")

    # 4. An optional target_value stops the Study early, partial results preserved.
    target = _unwrap(
        api.coerce_study_criteria(
            {
                "objective": {
                    "measure": "net_profit",
                    "direction": "max",
                    "target_value": {"num": 40, "den": 1},
                },
                "min_trades_enabled": False,
            }
        ),
        "target criteria",
    )
    partial = [_trial("p1", _net_profit(2000)), _trial("p2", _net_profit(5000))]  # 50 >= 40
    early = _unwrap(api.compute_winner_set(partial, target, world=World.REPLAY), "early winners")
    assert early.target_reached is True
    assert {t.run_id.value for t in early.target_trials} == {_fp("run", "p2").value}
    assert early.winner_count == 2  # the partial winner set is preserved
    print("an optional target_value stops the Study early with the partial winner set preserved")

    # The qmb door is a thin wrapper over the one pure library function.
    assert api.compute_winner_set is qmb.compute_winner_set
    assert api.coerce_study_criteria is qmb.coerce_study_criteria
    print("the qmb door is a thin wrapper over one pure library winner-set function")

    print(f"qmb {qmb.__version__}")
    print("study objective and constraints ok")


if __name__ == "__main__":
    main()
