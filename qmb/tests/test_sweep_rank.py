"""Story 20.4 — cross-run ranking as a read-time fold over the sweep's ledger."""

from __future__ import annotations

from typing import TypeVar

from qmb._refuse import unavailable
from qmb.ledger import LedgerLine
from qmb.results import emit_measure
from qmb.sweep import (
    CONSTRAINT_OPERATORS,
    INCOMPLETE_OBJECTIVE_UNDEFINED,
    INCOMPLETE_REFUSED,
    RANK_ASCENDING,
    RANK_DESCENDING,
    ConstraintFilter,
    SweepRanking,
    rank_sweep,
    refuse_rank_act,
    sweep_rank_identity,
)
from qmf.core.exact import ExactRational, Money, UnitKind
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.performance import UndefinedMeasure

T = TypeVar("T")

_SWEEP_A = fingerprint({"class": "sweep", "id": "sweep-a"})
_SWEEP_B = fingerprint({"class": "sweep", "id": "sweep-b"})
_BAR = fingerprint({"class": "book-bar", "id": "bar-1"})
_BAR_SPEC = {"kind": "time-interval", "seconds": 60}


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _fp(*parts: object) -> Fingerprint:
    return _ok(fingerprint({"parts": list(parts)}))


def _sweep_id_a() -> Fingerprint:
    return _ok(_SWEEP_A)


def _sweep_id_b() -> Fingerprint:
    return _ok(_SWEEP_B)


def _coordinates(sweep_id: Fingerprint, instrument: str, param: str) -> dict[str, object]:
    return {
        "bar_spec": _BAR_SPEC,
        "class": "qmb-sweep-coordinates",
        "format_version": 1,
        "instrument": instrument,
        "param_hash": _fp("param", param).value,
        "sweep_id": sweep_id.value,
    }


def _net_profit(minor: int) -> dict[str, object]:
    quantity = Money(value=minor, currency="USD", scale=2)
    return _ok(emit_measure("net_profit", quantity)).fp1_identity()


def _max_drawdown(num: int, den: int) -> dict[str, object]:
    quantity = _ok(ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO))
    return _ok(emit_measure("max_drawdown", quantity)).fp1_identity()


def _undefined_net_profit() -> dict[str, object]:
    refusal = unavailable("net_profit", "insufficient sample", code="undefined")
    return _ok(UndefinedMeasure.try_create("net_profit", 1, refusal)).fp1_identity()


def _completed(
    run: str,
    *,
    sweep_id: Fingerprint,
    measures: tuple[dict[str, object], ...],
    instrument: str = "EURUSD",
    world: World = World.REPLAY,
    role: str = "confirmation",
) -> LedgerLine:
    return LedgerLine(
        run_id=_fp("run", run),
        role=role,
        world=world,
        result_label={"class": "result-label", "world": world.value, "run": run},
        book_bar_fp1=_ok(_BAR),
        measures=measures,
        ct32_fingerprint=_fp("ct32", run),
        sweep_coordinates=_coordinates(sweep_id, instrument, run),
    )


def _aborted(run: str, *, sweep_id: Fingerprint, instrument: str = "EURUSD") -> LedgerLine:
    return LedgerLine(
        run_id=_fp("run", run),
        role="aborted",
        world=World.REPLAY,
        result_label={"class": "result-label", "world": World.REPLAY.value, "run": run},
        book_bar_fp1=_ok(_BAR),
        measures=(),
        ct32_fingerprint=None,
        refusal={"category": "invalid input", "field": "terminal", "reason": "combo refused"},
        sweep_coordinates=_coordinates(sweep_id, instrument, run),
    )


def _rank(lines: object, **kwargs: object) -> SweepRanking:
    defaults: dict[str, object] = {
        "sweep_id": _sweep_id_a(),
        "objective": "net_profit",
        "world": World.REPLAY,
    }
    defaults.update(kwargs)
    return _ok(rank_sweep(lines, **defaults))


# --- AC1: read-time ordering by objective, one sweep, never mixing world/role --


def test_ranks_by_objective_measure_identity_descending() -> None:
    a = _sweep_id_a()
    lines = [
        _completed("c1", sweep_id=a, measures=(_net_profit(3000),)),
        _completed("c2", sweep_id=a, measures=(_net_profit(1000),)),
        _completed("c3", sweep_id=a, measures=(_net_profit(2000),)),
    ]
    ranking = _rank(lines)

    assert ranking.ranked_count == 3
    ordered = [combo.objective_value for combo in ranking.ranked]
    assert ordered == [30, 20, 10]  # exact rationals, descending
    assert ranking.best is not None and ranking.best.objective_value == 30
    assert ranking.worst is not None and ranking.worst.objective_value == 10
    # A pure downstream fold adds no computation of its own (B-10, NFR-03).
    assert ranking.adds_computation is False


def test_fold_reads_only_this_sweep_and_never_mixes_worlds() -> None:
    a = _sweep_id_a()
    b = _sweep_id_b()
    lines = [
        _completed("c1", sweep_id=a, measures=(_net_profit(3000),)),
        _completed("c2", sweep_id=b, measures=(_net_profit(9000),)),  # other sweep
        _completed(
            "c3", sweep_id=a, measures=(_net_profit(5000),), world=World.SIMULATED
        ),  # other world
    ]
    ranking = _rank(lines)

    ranked_runs = {combo.run_id.value for combo in ranking.ranked}
    assert ranked_runs == {_fp("run", "c1").value}
    assert ranking.ranked_count == 1
    assert all(combo.world == World.REPLAY.value for combo in ranking.ranked)


def test_a_trial_role_line_is_not_read_by_a_confirmation_ranking() -> None:
    a = _sweep_id_a()
    lines = [
        _completed("c1", sweep_id=a, measures=(_net_profit(3000),)),
        _completed("c2", sweep_id=a, measures=(_net_profit(9000),), role="trial"),
    ]
    ranking = _rank(lines, role="confirmation")
    assert {combo.run_id.value for combo in ranking.ranked} == {_fp("run", "c1").value}


# --- AC2: metric-operator-value constraints, caller-supplied value ------------


def test_constraint_filters_out_combos_violating_the_bound() -> None:
    a = _sweep_id_a()
    lines = [
        _completed("c1", sweep_id=a, measures=(_net_profit(3000), _max_drawdown(1, 10))),
        _completed("c2", sweep_id=a, measures=(_net_profit(5000), _max_drawdown(3, 10))),
        _completed("c3", sweep_id=a, measures=(_net_profit(2000), _max_drawdown(1, 5))),
    ]
    # max_drawdown <= 0.20, the value supplied by the caller (never invented).
    bound = _ok(
        ConstraintFilter.try_create(
            "max_drawdown", "le", _ok(ExactRational.try_create(1, 5, UnitKind.DIMENSIONLESS_RATIO))
        )
    )
    ranking = _rank(lines, constraints=(bound,))

    ranked_runs = [combo.run_id.value for combo in ranking.ranked]
    assert ranked_runs == [_fp("run", "c1").value, _fp("run", "c3").value]
    assert ranking.constrained_out_count == 1
    assert ranking.constrained_out[0].run_id.value == _fp("run", "c2").value
    assert ranking.constrained_out[0].failed_constraints  # names the violated bound


def test_no_constraint_ranks_every_completed_combo() -> None:
    a = _sweep_id_a()
    lines = [
        _completed("c1", sweep_id=a, measures=(_net_profit(3000),)),
        _completed("c2", sweep_id=a, measures=(_net_profit(1000),)),
    ]
    ranking = _rank(lines)
    assert ranking.ranked_count == 2
    assert ranking.constrained_out_count == 0


def test_constraint_accepts_a_mapping_and_triple_form() -> None:
    a = _sweep_id_a()
    lines = [_completed("c1", sweep_id=a, measures=(_net_profit(3000), _max_drawdown(1, 10)))]
    mapping_form = _rank(
        lines, constraints=({"metric": "max_drawdown", "operator": "lt", "value": 1},)
    )
    triple_form = _rank(lines, constraints=(("max_drawdown", "<", 1),))
    assert mapping_form.ranked_count == 1
    assert triple_form.ranked_count == 1


def test_constraint_value_rejects_a_binary_float() -> None:
    refusal = ConstraintFilter.try_create("max_drawdown", "le", 0.2)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


# --- AC3: publishes never acts; taint + world carried; no verdict -------------


def test_ranking_refuses_every_downstream_act() -> None:
    for act in ("size", "promote", "bench", "bind", "allocate", "demote", "change_mode"):
        refusal = refuse_rank_act(act)
        assert is_refusal(refusal), act
        assert refusal.category is RefusalCategory.POLICY_REJECTION


def test_every_ranked_combo_carries_optimistic_taint_and_world() -> None:
    a = _sweep_id_a()
    lines = [_completed("c1", sweep_id=a, measures=(_net_profit(3000),))]
    ranking = _rank(lines)
    combo = ranking.ranked[0]
    assert combo.taint == "optimistic"
    assert combo.world == World.REPLAY.value
    assert combo.makes_edge_claim is False
    assert ranking.makes_edge_claim is False
    assert ranking.makes_pass_fail_verdict is False
    assert ranking.publishes_never_acts is True


def test_objective_must_be_a_roster_measure_never_a_composite() -> None:
    a = _sweep_id_a()
    lines = [_completed("c1", sweep_id=a, measures=(_net_profit(3000),))]
    composite = rank_sweep(lines, sweep_id=a, objective="composite_score", world=World.REPLAY)
    assert is_refusal(composite)
    not_a_measure = rank_sweep(lines, sweep_id=a, objective="totally_made_up", world=World.REPLAY)
    assert is_refusal(not_a_measure)
    assert not_a_measure.category is RefusalCategory.INVALID_INPUT


def test_ranking_identity_carries_no_pass_fail_verdict_or_score() -> None:
    a = _sweep_id_a()
    lines = [_completed("c1", sweep_id=a, measures=(_net_profit(3000),))]
    identity = _rank(lines).fp1_identity()
    banned = {"verdict", "pass", "fail", "rated", "score", "rating", "tier"}
    assert banned.isdisjoint(identity)
    assert identity["makes_pass_fail_verdict"] is False
    assert identity["makes_edge_claim"] is False


# --- AC4: refused/incomplete combos excluded, never coerced to zero -----------


def test_aborted_combo_is_reported_incomplete_never_ranked_or_zeroed() -> None:
    a = _sweep_id_a()
    lines = [
        _completed("c1", sweep_id=a, measures=(_net_profit(3000),)),
        _aborted("c2", sweep_id=a),
    ]
    ranking = _rank(lines)

    assert ranking.ranked_count == 1  # the refusal is not ranked
    assert ranking.incomplete_count == 1
    incomplete = ranking.incomplete[0]
    assert incomplete.run_id.value == _fp("run", "c2").value
    assert incomplete.reason == INCOMPLETE_REFUSED
    # It is never coerced to a zero objective — no ranked combo carries its run id.
    assert all(combo.run_id.value != incomplete.run_id.value for combo in ranking.ranked)


def test_undefined_objective_measure_is_incomplete_not_zero() -> None:
    a = _sweep_id_a()
    lines = [
        _completed("c1", sweep_id=a, measures=(_net_profit(3000),)),
        _completed("c2", sweep_id=a, measures=(_undefined_net_profit(),)),
    ]
    ranking = _rank(lines)

    assert ranking.ranked_count == 1
    assert ranking.incomplete_count == 1
    assert ranking.incomplete[0].reason == INCOMPLETE_OBJECTIVE_UNDEFINED
    assert ranking.incomplete[0].run_id.value == _fp("run", "c2").value


# --- AC5: deterministic and reproducible --------------------------------------


def test_ranking_is_deterministic_regardless_of_input_order() -> None:
    a = _sweep_id_a()
    lines = [
        _completed("c1", sweep_id=a, measures=(_net_profit(3000),)),
        _completed("c2", sweep_id=a, measures=(_net_profit(1000),)),
        _completed("c3", sweep_id=a, measures=(_net_profit(2000),)),
        _aborted("c4", sweep_id=a),
    ]
    first = _rank(lines)
    second = _rank(list(reversed(lines)))
    assert first.fp1_identity() == second.fp1_identity()
    assert _ok(first.fingerprint()).value == _ok(second.fingerprint()).value


def test_ascending_direction_flips_best_and_worst() -> None:
    a = _sweep_id_a()
    lines = [
        _completed("c1", sweep_id=a, measures=(_net_profit(3000),)),
        _completed("c2", sweep_id=a, measures=(_net_profit(1000),)),
    ]
    descending = _rank(lines, direction=RANK_DESCENDING)
    ascending = _rank(lines, direction=RANK_ASCENDING)
    assert descending.best is not None and descending.best.objective_value == 30
    assert ascending.best is not None and ascending.best.objective_value == 10


# --- surface -----------------------------------------------------------------


def test_rank_identity_excludes_semver_and_declares_publish_only() -> None:
    identity = sweep_rank_identity()
    assert "version" not in identity
    assert identity["publishes_never_acts"] is True
    assert identity["makes_edge_claim"] is False
    assert identity["taint"] == "optimistic"
    assert tuple(CONSTRAINT_OPERATORS) == ("lt", "le", "gt", "ge", "eq", "ne")
