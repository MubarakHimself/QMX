"""Reference usage -- cross-run ranking as a read-time fold (Story 20.4).

Executable::

    python qmb/examples/sweep_rank_usage.py

Shows the things B-4 / B-10 / B-12 / B-14 / spec R11-R12 / Story 20.4 pin down:

1. Ranking is a pure read-time view over the world-and-role-scoped ledger merge:
   a completed sweep's combos are ordered by a declared objective measure_identity
   from the AD-23/AD-41 roster, never a merged or re-run computation. The fold
   reads only this sweep_id and never mixes worlds or roles.
2. An optional metric-operator-value constraint (for example max_drawdown <= 0.20)
   filters the ordering; the operator or agent supplies the comparison value, no
   threshold number is invented.
3. Ranking publishes and never acts: it produces no composite score that gates
   money, mints no promotion, and binds nothing; every ranked combo carries its
   optimistic taint and world label forward and makes no edge claim.
4. A refused/aborted combo (no CT-32 measures), or a completed combo whose
   objective is undefined, is reported in a separate refused/incomplete list --
   never silently dropped and never coerced to a zero score.
5. Re-ranking the same sweep under the same objective plus constraints is
   deterministic: the ranking fingerprints identically regardless of input order.
"""

from __future__ import annotations

from typing import TypeVar

from qmb._refuse import unavailable
from qmf.core.exact import ExactRational, Money, UnitKind
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.risk.performance import UndefinedMeasure

import qmb

T = TypeVar("T")

_TF_1M = {"kind": "time-interval", "seconds": 60}


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _fp(*parts: object) -> Fingerprint:
    return _unwrap(fingerprint({"parts": list(parts)}), "fingerprint")


def _sweep_id() -> Fingerprint:
    return _fp("sweep", "demo")


def _coordinates(sweep_id: Fingerprint, instrument: str, run: str) -> dict[str, object]:
    return {
        "bar_spec": _TF_1M,
        "class": "qmb-sweep-coordinates",
        "format_version": 1,
        "instrument": instrument,
        "param_hash": _fp("param", run).value,
        "sweep_id": sweep_id.value,
    }


def _net_profit(minor: int) -> dict[str, object]:
    quantity = Money(value=minor, currency="USD", scale=2)
    return _unwrap(qmb.emit_measure("net_profit", quantity), "net_profit").fp1_identity()


def _max_drawdown(num: int, den: int) -> dict[str, object]:
    quantity = _unwrap(ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO), "ratio")
    return _unwrap(qmb.emit_measure("max_drawdown", quantity), "max_drawdown").fp1_identity()


def _undefined_net_profit() -> dict[str, object]:
    refusal = unavailable("net_profit", "insufficient sample", code="undefined")
    return _unwrap(
        UndefinedMeasure.try_create("net_profit", 1, refusal), "undefined"
    ).fp1_identity()


def _completed(
    run: str,
    *,
    sweep_id: Fingerprint,
    measures: tuple[dict[str, object], ...],
    instrument: str = "EURUSD",
    world: World = World.REPLAY,
) -> qmb.LedgerLine:
    return qmb.LedgerLine(
        run_id=_fp("run", run),
        role=qmb.ROLE_CONFIRMATION,
        world=world,
        result_label={"class": "result-label", "world": world.value, "run": run},
        book_bar_fp1=_fp("bar"),
        measures=measures,
        ct32_fingerprint=_fp("ct32", run),
        sweep_coordinates=_coordinates(sweep_id, instrument, run),
    )


def _aborted(run: str, *, sweep_id: Fingerprint) -> qmb.LedgerLine:
    return qmb.LedgerLine(
        run_id=_fp("run", run),
        role=qmb.ROLE_ABORTED,
        world=World.REPLAY,
        result_label={"class": "result-label", "world": World.REPLAY.value, "run": run},
        book_bar_fp1=_fp("bar"),
        measures=(),
        ct32_fingerprint=None,
        refusal={"category": "invalid input", "field": "terminal", "reason": "combo refused"},
        sweep_coordinates=_coordinates(sweep_id, run, run),
    )


def objective_ordering_is_a_read_time_fold() -> None:
    sweep_id = _sweep_id()
    other = _fp("sweep", "other")
    lines = [
        _completed("c1", sweep_id=sweep_id, measures=(_net_profit(3000),)),
        _completed("c2", sweep_id=sweep_id, measures=(_net_profit(1000),)),
        _completed("c3", sweep_id=sweep_id, measures=(_net_profit(2000),)),
        _completed("other", sweep_id=other, measures=(_net_profit(9000),)),  # different sweep
        _completed(  # different world
            "sim", sweep_id=sweep_id, measures=(_net_profit(8000),), world=World.SIMULATED
        ),
    ]
    ranking = _unwrap(
        qmb.rank_sweep(lines, sweep_id=sweep_id, objective="net_profit", world=World.REPLAY),
        "ranking",
    )
    assert [combo.objective_value for combo in ranking.ranked] == [30, 20, 10]
    assert ranking.best is not None and ranking.best.objective_value == 30
    assert ranking.worst is not None and ranking.worst.objective_value == 10
    assert ranking.adds_computation is False  # a pure downstream fold
    assert all(combo.world == World.REPLAY.value for combo in ranking.ranked)  # never mixed
    print("ranked best to worst by net_profit over one sweep_id, one world, one role")


def a_constraint_filters_without_inventing_a_threshold() -> None:
    sweep_id = _sweep_id()
    lines = [
        _completed("c1", sweep_id=sweep_id, measures=(_net_profit(3000), _max_drawdown(1, 10))),
        _completed("c2", sweep_id=sweep_id, measures=(_net_profit(5000), _max_drawdown(3, 10))),
    ]
    bound = _unwrap(
        qmb.ConstraintFilter.try_create(
            "max_drawdown",
            "le",
            _unwrap(ExactRational.try_create(1, 5, UnitKind.DIMENSIONLESS_RATIO), "bound"),
        ),
        "constraint",
    )
    ranking = _unwrap(
        qmb.rank_sweep(
            lines,
            sweep_id=sweep_id,
            objective="net_profit",
            world=World.REPLAY,
            constraints=(bound,),
        ),
        "ranking",
    )
    assert ranking.ranked_count == 1  # only the combo satisfying max_drawdown <= 0.20
    assert ranking.constrained_out_count == 1
    assert ranking.constrained_out[0].failed_constraints
    print("caller-supplied max_drawdown bound filtered the ordering; no threshold invented")


def ranking_publishes_and_never_acts() -> None:
    sweep_id = _sweep_id()
    lines = [_completed("c1", sweep_id=sweep_id, measures=(_net_profit(3000),))]
    ranking = _unwrap(
        qmb.rank_sweep(lines, sweep_id=sweep_id, objective="net_profit", world=World.REPLAY),
        "ranking",
    )
    assert ranking.ranked[0].taint == "optimistic"  # taint carried forward
    assert ranking.ranked[0].makes_edge_claim is False
    assert ranking.makes_pass_fail_verdict is False
    assert "verdict" not in ranking.fp1_identity()
    for act in ("promote", "bench", "bind", "size"):
        assert is_refusal(qmb.refuse_rank_act(act)), act
    # A composite score is never a legal objective.
    assert is_refusal(
        qmb.rank_sweep(lines, sweep_id=sweep_id, objective="composite_score", world=World.REPLAY)
    )
    print("ranking makes no edge claim, no pass/fail verdict, and refuses every act")


def refused_and_undefined_combos_are_reported_never_zeroed() -> None:
    sweep_id = _sweep_id()
    lines = [
        _completed("c1", sweep_id=sweep_id, measures=(_net_profit(3000),)),
        _completed("c2", sweep_id=sweep_id, measures=(_undefined_net_profit(),)),
        _aborted("c3", sweep_id=sweep_id),
    ]
    ranking = _unwrap(
        qmb.rank_sweep(lines, sweep_id=sweep_id, objective="net_profit", world=World.REPLAY),
        "ranking",
    )
    assert ranking.ranked_count == 1
    reasons = {item.reason for item in ranking.incomplete}
    assert reasons == {qmb.INCOMPLETE_OBJECTIVE_UNDEFINED, qmb.INCOMPLETE_REFUSED}
    ranked_runs = {combo.run_id.value for combo in ranking.ranked}
    for item in ranking.incomplete:
        assert item.run_id.value not in ranked_runs  # never coerced into the ordering
    print("refused and undefined combos land in the incomplete list, never a zero score")


def re_ranking_is_deterministic() -> None:
    sweep_id = _sweep_id()
    lines = [
        _completed("c1", sweep_id=sweep_id, measures=(_net_profit(3000),)),
        _completed("c2", sweep_id=sweep_id, measures=(_net_profit(1000),)),
        _aborted("c3", sweep_id=sweep_id),
    ]
    first = _unwrap(
        qmb.rank_sweep(lines, sweep_id=sweep_id, objective="net_profit", world=World.REPLAY),
        "first",
    )
    second = _unwrap(
        qmb.rank_sweep(
            list(reversed(lines)), sweep_id=sweep_id, objective="net_profit", world=World.REPLAY
        ),
        "second",
    )
    assert first.fp1_identity() == second.fp1_identity()
    print("same sweep, same objective: identical ranking regardless of input order")


def main() -> None:
    assert callable(qmb.rank_sweep)
    assert qmb.RANK_PUBLISHES_NEVER_ACTS is True
    assert qmb.RANK_ADDS_COMPUTATION is False
    objective_ordering_is_a_read_time_fold()
    a_constraint_filters_without_inventing_a_threshold()
    ranking_publishes_and_never_acts()
    refused_and_undefined_combos_are_reported_never_zeroed()
    re_ranking_is_deterministic()
    print("sweep rank ok")


if __name__ == "__main__":
    main()
