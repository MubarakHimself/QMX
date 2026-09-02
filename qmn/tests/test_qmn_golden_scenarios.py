"""Story 28.5 — four golden node scenarios through the sealed composition."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import Duration, ExactRational, Money, UnitKind, VenueId, World
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmn.host import (
    GOLDEN_PROOF_KEYS,
    GOLDEN_SCENARIO_CLASS,
    GOLDEN_SCENARIO_SURFACE,
    SOURCE_CLASS_SYNTHETIC,
    TRADING_EDGE_IS_PROOF,
    GoldenScenarioInputs,
    refuse_golden_invented_ksa_or_latency,
    refuse_golden_trading_edge_claim,
    run_paper_milestone_golden_scenarios,
)
from qmn.time import VpsClock
from qmn.venue import ConformanceDouble, VenueClientKind

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SEED = "story-28-5"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _clock() -> VpsClock:
    return _ok(
        VpsClock.try_create(
            boot_epoch_id="boot-28-5",
            wall_ns=lambda: _NS,
            monotonic_ns=lambda: _NS,
        )
    )


def _venue() -> ConformanceDouble:
    venue_id = _ok(VenueId.try_create("conformance:paper-28-5"))
    double = _ok(ConformanceDouble.try_create(World.LIVE, venue_id))
    assert double.kind is VenueClientKind.CONFORMANCE
    return double


def _inputs(**overrides: object) -> GoldenScenarioInputs:
    kwargs: dict[str, object] = {
        "clock": _clock(),
        "venue": _venue(),
        "paper_starting_balance": _ok(Money.try_create(50_000_00, "USD", 2)),
        "qualifying_loss_threshold": _ok(ExactRational.try_create(1, 1, UnitKind.R_MULTIPLE)),
        "bench_consecutive_loss_threshold": 2,
        "news_calendar_max_staleness": _ok(Duration.try_create(86_400_000_000_000)),
        "seed": _SEED,
    }
    kwargs.update(overrides)
    return GoldenScenarioInputs(**kwargs)  # type: ignore[arg-type]


def test_surface_markers_pin_synthetic_and_ftr07() -> None:
    assert GOLDEN_SCENARIO_SURFACE == "qmn.host.golden_scenarios"
    assert GOLDEN_SCENARIO_CLASS == "paper-milestone-golden-scenarios"
    assert TRADING_EDGE_IS_PROOF is False
    assert SOURCE_CLASS_SYNTHETIC == "synthetic"
    assert GOLDEN_PROOF_KEYS == (
        "qmn/paper-transition",
        "qmn/news-window",
        "qmn/news-window/narrowing-revision",
        "qmn/compose-pair/suspend-plus-flatten",
        "qmn/bench-fold",
    )


def test_four_golden_scenarios_run_through_sealed_composition() -> None:
    report = _ok(run_paper_milestone_golden_scenarios(_inputs()))
    assert report.composition_sealed is True
    assert report.scenarios_proven == ("SCN-0006", "SCN-0008", "SCN-0010", "SCN-0011")
    assert report.source_class == SOURCE_CLASS_SYNTHETIC
    assert report.invents_ksa_or_latency is False
    assert report.ksa_matrix_values_supplied is False
    assert report.trading_edge_is_proof is False
    assert report.synthetic_proves_infrastructure_only is True
    assert tuple(item.proof_key for item in report.fixtures) == GOLDEN_PROOF_KEYS
    mapped = report.as_mapping()
    assert mapped["fingerprint"] == report.fingerprint.value
    assert mapped["surface"] == GOLDEN_SCENARIO_SURFACE


def test_each_fixture_carries_tn23_metadata() -> None:
    report = _ok(run_paper_milestone_golden_scenarios(_inputs()))
    for fixture in report.fixtures:
        assert fixture.proof_key in GOLDEN_PROOF_KEYS
        assert fixture.scenario.startswith("SCN-00")
        assert fixture.components
        assert all(item.startswith("COMP-") for item in fixture.components)
        assert fixture.contracts
        assert all(item.startswith("CT-") for item in fixture.contracts)
        assert fixture.decisions
        assert all(item.startswith("DEC-") for item in fixture.decisions)
        assert fixture.gaps == ("GAP-0050",)
        assert fixture.given
        assert fixture.when
        assert fixture.then
        assert fixture.clock_ns == _NS
        assert fixture.seed == _SEED
        assert fixture.source_class == SOURCE_CLASS_SYNTHETIC
        assert fixture.fingerprint.value
        assert fixture.trading_edge_claimed is False
        body = fixture.as_mapping()
        assert body["fingerprint"] == fixture.fingerprint.value
        assert "trading_edge_claimed" in body


def test_scn0006_paper_transition_invariants() -> None:
    report = _ok(run_paper_milestone_golden_scenarios(_inputs()))
    fixture = next(item for item in report.fixtures if item.scenario == "SCN-0006")
    evidence = fixture.evidence
    assert evidence["append_only_epoch"] is True
    assert evidence["book_mode"] == "PAPER"
    assert evidence["bot_twin_minted"] is False
    assert evidence["book_twin_minted"] is False
    assert evidence["frozen_per_intent_target"] is True
    assert evidence["separate_stream_unknown"] is True
    assert evidence["immutable_paper_money"] is True
    assert evidence["human_signed_return"] is True
    assert evidence["paper_performance_authorizes_return"] is False
    assert evidence["restart_does_not_rearm_paper"] is True
    assert evidence["live_connectivity_does_not_block_demo"] is True
    assert evidence["clears_only_by"] == "operator-signature"


def test_scn0008_news_window_and_narrowing() -> None:
    report = _ok(run_paper_milestone_golden_scenarios(_inputs()))
    news = next(item for item in report.fixtures if item.proof_key == "qmn/news-window")
    narrowing = next(
        item for item in report.fixtures if item.proof_key == "qmn/news-window/narrowing-revision"
    )
    evidence = news.evidence
    assert evidence["declared_exposure"] is True
    assert evidence["fail_closed_missing_scope"] is True
    assert evidence["fail_closed_staleness"] is True
    assert evidence["entry_only_block"] is True
    assert evidence["exit_preservation"] is True
    assert evidence["live_and_paper_blocked"] is True
    assert evidence["narrowing_held"] is True
    assert evidence["widen_not_shrink"] == "narrowing-held"
    assert evidence["sole_free_source"] == "forex-factory-free-weekly"
    assert "ff_calendar_thisweek.json" in str(evidence["sole_weekly_file"])
    assert narrowing.evidence["narrowing_held"] is True


def test_scn0010_arbitration_compose_conflict_scope() -> None:
    report = _ok(run_paper_milestone_golden_scenarios(_inputs()))
    fixture = next(item for item in report.fixtures if item.scenario == "SCN-0010")
    evidence = fixture.evidence
    assert evidence["one_arbiter_per_stream"] is True
    assert evidence["total_unique_rank"] is True
    assert evidence["compose_both_execute"] is True
    assert evidence["collapse_one_flatten"] is True
    assert evidence["conflict_higher_rank_wins"] is True
    assert evidence["scope_refusal"] is True
    assert evidence["exit_preservation"] is True
    assert evidence["suppressed_count"] == 2


def test_scn0011_bench_fold_routes_seat_book_stays_live() -> None:
    report = _ok(run_paper_milestone_golden_scenarios(_inputs()))
    fixture = next(item for item in report.fixtures if item.scenario == "SCN-0011")
    evidence = fixture.evidence
    assert evidence["one_ct29_per_close"] is True
    assert evidence["breakeven_excluded"] is True
    assert evidence["stale_evidence_refused"] is True
    assert evidence["binding_epoch_bounded"] is True
    assert evidence["qualifying_loss_count"] == 2
    assert evidence["threshold_crossed"] is True
    assert evidence["seat_state"] == "benched"
    assert evidence["book_mode"] == "LIVE"
    assert evidence["routed_paper"] is True
    assert evidence["trading_edge_claimed"] is False


def test_identical_inputs_fingerprint_identically() -> None:
    first = _ok(run_paper_milestone_golden_scenarios(_inputs()))
    second = _ok(run_paper_milestone_golden_scenarios(_inputs()))
    assert first.fingerprint == second.fingerprint
    assert tuple(item.fingerprint for item in first.fixtures) == tuple(
        item.fingerprint for item in second.fixtures
    )


def test_ftr07_refuses_invented_ksa_or_latency() -> None:
    ksa = _refusal(run_paper_milestone_golden_scenarios(_inputs(invent_ksa_matrix_values=True)))
    assert ksa.category is RefusalCategory.POLICY_REJECTION
    assert ksa.context["failure_id"] == "golden_scenarios.invented_ksa_or_latency"
    latency = _refusal(run_paper_milestone_golden_scenarios(_inputs(invent_latency_gate=True)))
    assert latency.context["failure_id"] == "golden_scenarios.invented_ksa_or_latency"
    direct = refuse_golden_invented_ksa_or_latency()
    assert is_refusal(direct)


def test_synthetic_never_proves_trading_edge() -> None:
    refused = _refusal(run_paper_milestone_golden_scenarios(_inputs(claim_trading_edge=True)))
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["failure_id"] == "golden_scenarios.trading_edge"
    assert refused.context["source_class"] == SOURCE_CLASS_SYNTHETIC
    assert refused.context["trading_edge_is_proof"] is False
    direct = refuse_golden_trading_edge_claim()
    assert is_refusal(direct)


def test_invalid_inputs_refuse() -> None:
    refused = _refusal(run_paper_milestone_golden_scenarios("not-inputs"))
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["failure_id"] == "golden_scenarios.inputs"


def test_fixture_evidence_is_mapping_not_edge_claim() -> None:
    report = _ok(run_paper_milestone_golden_scenarios(_inputs()))
    for fixture in report.fixtures:
        evidence = fixture.evidence
        assert evidence.get("trading_edge_claimed") is False
        assert "win_rate" not in evidence
        assert "expectancy" not in evidence
        assert "alpha" not in evidence
