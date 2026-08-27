"""Epic 20 · Story 20.4 (L3) — cross-run ranking as a read-time fold.

Over TEST-owned, shape-faithful ledger lines (built from the ratified value types):
no batch run is needed to exercise the read-time fold.

  T20-317  R17  read-time ordering by objective measure_identity; one sweep; no
                world/role mixing; the fold adds no computation of its own       (P0)
  T20-318  R18  constraint value is caller-supplied; no threshold invented        (P1)
  T20-319  R19  publishes & never acts; taint/world carried; no edge/verdict      (P0)
  T20-320  R20  a refused/incomplete combo is excluded AND reported, never zeroed (P0)
  T20-321  R21  recomputation is deterministic and reproducible                   (P1)
"""

from __future__ import annotations

from fractions import Fraction

from conftest import (
    aborted_line,
    completed_line,
    fp,
    max_drawdown,
    net_profit,
    ok,
    sweep_id_a,
    sweep_id_b,
)

from qmb._refuse import unavailable
from qmb.sweep import (
    INCOMPLETE_OBJECTIVE_UNDEFINED,
    INCOMPLETE_REFUSED,
    RANK_ASCENDING,
    RANK_DESCENDING,
    RANK_FORBIDDEN_ACTS,
    ConstraintFilter,
    rank_sweep,
    refuse_rank_act,
)
from qmf.core.exact import ExactRational, UnitKind
from qmf.core.fingerprint import World
from qmf.core.refusal import RefusalCategory, is_refusal
from qmf.risk.performance import UndefinedMeasure


def _rank(lines: object, **kwargs: object):
    defaults: dict[str, object] = {"sweep_id": sweep_id_a(), "objective": "net_profit", "world": World.REPLAY}
    defaults.update(kwargs)
    return ok(rank_sweep(lines, **defaults))


def _undefined_net_profit() -> dict[str, object]:
    refusal = unavailable("net_profit", "insufficient sample", code="undefined")
    return ok(UndefinedMeasure.try_create("net_profit", 1, refusal)).fp1_identity()


# --- T20-317 (R17) : read-time ordering, one sweep, no world/role mixing -------


def test_t20_317_ranks_by_objective_and_reads_only_this_sweep_world_role() -> None:
    a, b = sweep_id_a(), sweep_id_b()
    lines = [
        completed_line("c1", sweep_id=a, measures=(net_profit(3000),)),
        completed_line("c2", sweep_id=a, measures=(net_profit(1000),)),
        completed_line("c3", sweep_id=a, measures=(net_profit(2000),)),
        completed_line("x_other_sweep", sweep_id=b, measures=(net_profit(9000),)),
        completed_line("x_other_world", sweep_id=a, measures=(net_profit(5000),), world=World.SIMULATED),
        completed_line("x_other_role", sweep_id=a, measures=(net_profit(7000),), role="trial"),
    ]
    ranking = _rank(lines)
    # Only this sweep's confirmation/replay combos are ranked — no world/role mix.
    assert ranking.ranked_count == 3
    assert {c.run_id.value for c in ranking.ranked} == {
        fp("run", "c1").value, fp("run", "c2").value, fp("run", "c3").value
    }
    assert all(c.world == World.REPLAY.value for c in ranking.ranked)
    # Ordered best-to-worst by the objective magnitude.
    assert [c.objective_value for c in ranking.ranked] == [Fraction(30), Fraction(20), Fraction(10)]
    # The fold ADDS NO COMPUTATION: each objective magnitude equals the exact
    # measure from the input line (30 == 3000/100), never a recomputed number.
    assert ranking.best is not None and ranking.best.objective_value == Fraction(30)
    assert ranking.worst is not None and ranking.worst.objective_value == Fraction(10)


# --- T20-318 (R18) : constraint value is caller-supplied; no invented threshold --


def test_t20_318_constraint_value_is_caller_supplied_no_threshold_invented() -> None:
    a = sweep_id_a()
    lines = [
        completed_line("c1", sweep_id=a, measures=(net_profit(3000), max_drawdown(1, 10))),
        completed_line("c2", sweep_id=a, measures=(net_profit(5000), max_drawdown(3, 10))),
        completed_line("c3", sweep_id=a, measures=(net_profit(2000), max_drawdown(1, 5))),
    ]
    # With NO constraint, EVERY completed combo is ranked — no default threshold
    # is baked in (counter-case: a hidden default would filter some out).
    assert _rank(lines).ranked_count == 3

    # A caller-supplied max_drawdown <= 0.20 filter holds out only the violator.
    bound = ok(ConstraintFilter.try_create("max_drawdown", "le", ok(ExactRational.try_create(1, 5, UnitKind.DIMENSIONLESS_RATIO))))
    constrained = _rank(lines, constraints=(bound,))
    assert [c.run_id.value for c in constrained.ranked] == [fp("run", "c1").value, fp("run", "c3").value]
    assert constrained.constrained_out_count == 1
    assert constrained.constrained_out[0].run_id.value == fp("run", "c2").value
    assert constrained.constrained_out[0].failed_constraints  # names the violated bound

    # The comparison value is exact — a binary float threshold is refused.
    float_bound = ConstraintFilter.try_create("max_drawdown", "le", 0.2)
    assert is_refusal(float_bound)
    assert float_bound.category is RefusalCategory.INVALID_INPUT


# --- T20-319 (R19) : publishes & never acts; taint/world carried; no verdict ----


def test_t20_319_ranking_publishes_and_never_acts() -> None:
    a = sweep_id_a()
    lines = [completed_line("c1", sweep_id=a, measures=(net_profit(3000),))]
    ranking = _rank(lines)

    # Every forbidden downstream act is refused with a policy rejection.
    for act in RANK_FORBIDDEN_ACTS:
        refusal = refuse_rank_act(act)
        assert is_refusal(refusal), act
        assert refusal.category is RefusalCategory.POLICY_REJECTION

    # A composite score that could gate money is never invented — refused.
    composite = rank_sweep(lines, sweep_id=a, objective="composite_score", world=World.REPLAY)
    assert is_refusal(composite)

    # Every ranked combo carries the optimistic taint and world label FORWARD and
    # makes no edge claim; the ranking makes no pass/fail verdict.
    combo = ranking.ranked[0]
    assert combo.taint == "optimistic"
    assert combo.world == World.REPLAY.value
    assert combo.makes_edge_claim is False
    assert ranking.makes_edge_claim is False
    assert ranking.makes_pass_fail_verdict is False
    assert ranking.publishes_never_acts is True
    # No verdict/score/rating survives into the published identity content.
    identity = ranking.fp1_identity()
    assert {"verdict", "pass", "fail", "score", "rating", "tier"}.isdisjoint(identity)


# --- T20-320 (R20) : a refused/incomplete combo is excluded AND reported --------


def test_t20_320_refused_and_incomplete_combos_excluded_but_reported_never_zeroed() -> None:
    a = sweep_id_a()
    lines = [
        completed_line("c1", sweep_id=a, measures=(net_profit(3000),)),
        aborted_line("c2_refused", sweep_id=a),
        completed_line("c3_undef", sweep_id=a, measures=(_undefined_net_profit(),)),
    ]
    ranking = _rank(lines)
    assert ranking.ranked_count == 1  # only the combo with a defined objective
    assert ranking.incomplete_count == 2

    reasons = {(item.run_id.value, item.reason) for item in ranking.incomplete}
    assert (fp("run", "c2_refused").value, INCOMPLETE_REFUSED) in reasons
    assert (fp("run", "c3_undef").value, INCOMPLETE_OBJECTIVE_UNDEFINED) in reasons
    # Never coerced to a zero score: the excluded run ids never appear in ranked.
    ranked_ids = {c.run_id.value for c in ranking.ranked}
    assert fp("run", "c2_refused").value not in ranked_ids
    assert fp("run", "c3_undef").value not in ranked_ids


# --- T20-321 (R21) : recomputation is deterministic and reproducible -----------


def test_t20_321_recomputation_is_deterministic_and_reproducible() -> None:
    a = sweep_id_a()
    lines = [
        completed_line("c1", sweep_id=a, measures=(net_profit(3000),)),
        completed_line("c2", sweep_id=a, measures=(net_profit(1000),)),
        completed_line("c3", sweep_id=a, measures=(net_profit(2000),)),
        aborted_line("c4", sweep_id=a),
    ]
    first = _rank(lines)
    second = _rank(list(reversed(lines)))  # input order must not matter
    assert first.fp1_identity() == second.fp1_identity()
    assert ok(first.fingerprint()).value == ok(second.fingerprint()).value
    # The declared direction flips best/worst but stays a pure fold.
    asc = _rank(lines, direction=RANK_ASCENDING)
    desc = _rank(lines, direction=RANK_DESCENDING)
    assert asc.best is not None and asc.best.objective_value == Fraction(10)
    assert desc.best is not None and desc.best.objective_value == Fraction(30)
