"""Story 21.3 — train/test split discipline with fingerprinted split manifests."""

from __future__ import annotations

from typing import TypeVar

from qmb.doors import api
from qmb.optimize import (
    DEFAULT_ACCESS_ROLES,
    OBJECTIVE_SPLIT_ALIAS,
    SEALED_HOLDOUT_ROLE,
    SPLIT_RUN_CLAIMS_EDGE,
    SPLIT_RUN_SPENDS_BUDGET,
    SPLIT_RUN_TAINT,
    STUDIES_RUN_REPLAY_ONLY,
    STUDY_SPLITS_KEY,
    StudySplits,
    TrialSplitPlan,
    TrialSplitRun,
    admit_default_split_access,
    admit_objective_run,
    admit_study_world,
    coerce_study_splits,
    plan_trial_runs,
    refuse_split_edge_or_budget,
    serve_split_read,
    study_splits_identity,
    study_warmup,
)
from qmf.core.chrono import CalendarIdentity, Duration, Instant
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.data.seal import HoldoutSeal, ReadBoundary
from qmf.data.splits import (
    KnowledgeKind,
    KnowledgeRecord,
    SegmentRole,
    SplitBoundary,
    SplitManifest,
)

import qmb

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _fp(*parts: object) -> Fingerprint:
    return _ok(fingerprint({"parts": list(parts)}))


def _instant(ns: int) -> Instant:
    return _ok(Instant.try_create(ns))


def _manifest(offset: int = 0, *, world: World = World.REPLAY) -> SplitManifest:
    calendar = _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025b"))
    segments = _ok(
        SplitManifest.default_split_segments([1000 + offset, 2000 + offset, 3000 + offset])
    )
    seal_boundary = _ok(SplitBoundary.try_create(3000 + offset))
    return _ok(
        SplitManifest.try_create(
            calendar_identity=calendar,
            segments=segments,
            seal_boundary=seal_boundary,
            purge_width=0,
            embargo_width=0,
            world=world,
        )
    )


# --- AC1 / AC2: two-run plan, objective on train, both fingerprints on label ---


def test_study_splits_names_both_manifests_by_fingerprint() -> None:
    train = _manifest(0)
    test = _manifest(5000)
    splits = _ok(StudySplits.try_create(train, test))
    assert splits.train_split == train.fingerprint
    assert splits.test_split == test.fingerprint
    assert splits.world is World.REPLAY
    assert splits.objective_split == train.fingerprint
    assert splits.recorded_split == test.fingerprint


def test_trial_runs_score_train_and_record_test_on_one_parameter_set() -> None:
    splits = _ok(StudySplits.try_create(_manifest(0), _manifest(5000)))
    params = _fp("params", "v1")
    plan = _ok(plan_trial_runs(splits, params))
    assert isinstance(plan, TrialSplitPlan)
    assert plan.parameter_set_fp1 == params
    # both runs execute the identical parameter set (one shared fingerprint)
    assert plan.train_run.contributes_to_objective is True
    assert plan.test_run.contributes_to_objective is False
    assert plan.objective_run is plan.train_run
    assert plan.recorded_run is plan.test_run
    assert plan.runs == (plan.train_run, plan.test_run)
    assert plan.train_run.split_fp1 == splits.train_split
    assert plan.test_run.split_fp1 == splits.test_split


def test_only_training_run_may_feed_the_objective() -> None:
    splits = _ok(StudySplits.try_create(_manifest(0), _manifest(5000)))
    plan = _ok(plan_trial_runs(splits, _fp("params", "v1")))
    assert _ok(admit_objective_run(plan.train_run)) is plan.train_run
    refused = admit_objective_run(plan.test_run)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_admit_objective_run_rejects_non_run() -> None:
    refused = admit_objective_run(object())
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_trial_label_carries_both_fingerprints_aliases_display_only() -> None:
    train = _manifest(0)
    test = _manifest(5000)
    splits = _ok(StudySplits.try_create(train, test))
    plan = _ok(plan_trial_runs(splits, _fp("params", "v1")))
    label = plan.trial_label()
    # both split-manifest fingerprints appear on the trial label
    assert label["train_split_fp1"] == train.split_id
    assert label["test_split_fp1"] == test.split_id
    assert label["objective_split_fp1"] == train.split_id
    # "train"/"test" are display aliases only — never substituted for the fingerprints
    display = label["display"]
    assert isinstance(display, dict)
    assert display["aliases"] == {"train": train.split_id, "test": test.split_id}


def test_aliases_never_enter_split_identity() -> None:
    train = _manifest(0)
    test = _manifest(5000)
    splits = _ok(StudySplits.try_create(train, test))
    identity = splits.fp1_identity()
    assert identity["train_split_fp1"] == train.split_id
    assert identity["test_split_fp1"] == test.split_id
    assert "train" not in identity
    assert "test" not in identity
    assert identity["objective_split_alias"] == OBJECTIVE_SPLIT_ALIAS
    # the display alias map is separate and never in identity
    assert splits.display_aliases() == {"train": train.split_id, "test": test.split_id}


def test_alias_resolution_round_trips() -> None:
    train = _manifest(0)
    test = _manifest(5000)
    splits = _ok(StudySplits.try_create(train, test))
    assert _ok(splits.split_for("train")) == train.fingerprint
    assert _ok(splits.split_for("test")) == test.fingerprint
    assert _ok(splits.alias_for(train.fingerprint)) == "train"
    assert _ok(splits.alias_for(test.fingerprint)) == "test"
    assert is_refusal(splits.split_for("holdout"))
    assert is_refusal(splits.alias_for(_fp("stranger")))


def test_split_pair_is_identity_bearing_and_reproducible() -> None:
    train = _manifest(0)
    test = _manifest(5000)
    first = _ok(StudySplits.try_create(train, test))
    second = _ok(StudySplits.try_create(train.split_id, test.split_id))
    assert _ok(first.fingerprint()).value == _ok(second.fingerprint()).value
    layer = first.run_config_layer()
    assert layer[STUDY_SPLITS_KEY] == first.fp1_identity()


def test_distinct_splits_required() -> None:
    train = _manifest(0)
    refused = StudySplits.try_create(train, train)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_coerce_study_splits_accepts_mapping_and_aliases() -> None:
    train = _manifest(0)
    test = _manifest(5000)
    from_short = _ok(coerce_study_splits({"train": train, "test": test}))
    from_long = _ok(
        coerce_study_splits({"train_split": train.split_id, "test_split": test.split_id})
    )
    assert from_short.train_split == from_long.train_split
    assert from_short.test_split == from_long.test_split
    assert is_ok(coerce_study_splits(from_short))  # idempotent
    assert is_refusal(coerce_study_splits({"train": train.split_id}))  # missing test
    assert is_refusal(coerce_study_splits(["train", "test"]))  # not a mapping


def test_split_reference_must_be_a_fingerprint() -> None:
    test = _manifest(5000)
    refused = StudySplits.try_create(12345, test)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


# --- AC5: world=replay only --------------------------------------------------


def test_simulated_world_split_is_policy_rejection() -> None:
    train = _manifest(0)
    test = _manifest(5000)
    refused = StudySplits.try_create(train.split_id, test.split_id, world=World.SIMULATED)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    live = StudySplits.try_create(train.split_id, test.split_id, world=World.LIVE)
    assert is_refusal(live)
    assert live.category is RefusalCategory.POLICY_REJECTION


def test_simulated_manifest_world_is_policy_rejection() -> None:
    sim_train = _manifest(0, world=World.SIMULATED)
    test = _manifest(5000)
    refused = StudySplits.try_create(sim_train, test)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_admit_study_world_replay_only() -> None:
    assert _ok(admit_study_world(World.REPLAY)) is World.REPLAY
    simulated = admit_study_world(World.SIMULATED)
    assert is_refusal(simulated)
    assert simulated.category is RefusalCategory.POLICY_REJECTION
    # provenance token that resolves to simulated is likewise refused
    tainted = admit_study_world("synthetic-tainted")
    assert is_refusal(tainted)
    assert tainted.category is RefusalCategory.POLICY_REJECTION
    assert _ok(admit_study_world("recorded")) is World.REPLAY


def test_replay_only_constant() -> None:
    assert STUDIES_RUN_REPLAY_ONLY is True


# --- AC3: split-read enforcement + sealed-holdout exclusion ------------------


def test_seal_enforced_at_the_read_boundary() -> None:
    train = _manifest(0)
    seal = _ok(HoldoutSeal.from_manifest(train, 12))
    admitted = serve_split_read(
        seal=seal, position=_instant(1500), boundary=ReadBoundary.RESEARCH_DOOR
    )
    assert is_ok(admitted)
    refused = serve_split_read(
        seal=seal, position=_instant(9000), boundary=ReadBoundary.RESEARCH_DOOR
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_serve_split_read_requires_a_seal() -> None:
    refused = serve_split_read(seal=object(), position=_instant(1500))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_serve_split_read_partitions_record_by_knowledge_time() -> None:
    train = _manifest(0)
    seal = _ok(HoldoutSeal.from_manifest(train, 12))
    record = _ok(
        KnowledgeRecord.try_create(
            observed_at=1200, knowledge_time=1200, kind=KnowledgeKind.INDICATOR
        )
    )
    role = serve_split_read(
        seal=seal,
        position=_instant(1200),
        boundary=ReadBoundary.RESEARCH_DOOR,
        manifest=train,
        record=record,
    )
    assert is_ok(role)
    assert role.value in DEFAULT_ACCESS_ROLES


def test_serve_split_read_record_needs_a_manifest() -> None:
    train = _manifest(0)
    seal = _ok(HoldoutSeal.from_manifest(train, 12))
    record = _ok(
        KnowledgeRecord.try_create(
            observed_at=1200, knowledge_time=1200, kind=KnowledgeKind.INDICATOR
        )
    )
    refused = serve_split_read(seal=seal, position=_instant(1200), record=record, manifest=object())
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_calendar_in_band_enforced() -> None:
    train = _manifest(0)
    foreign = _ok(CalendarIdentity.try_create("forex-17NY", "v9", "2025b"))
    refused = train.admits_calendar(foreign)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_sealed_holdout_excluded_from_default_access() -> None:
    assert _ok(admit_default_split_access(SegmentRole.TRAIN)) is SegmentRole.TRAIN
    assert _ok(admit_default_split_access(SegmentRole.VALIDATION)) is SegmentRole.VALIDATION
    refused = admit_default_split_access(SegmentRole.SEALED_TEST)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert SEALED_HOLDOUT_ROLE is SegmentRole.SEALED_TEST
    assert SegmentRole.SEALED_TEST not in DEFAULT_ACCESS_ROLES


def test_admit_default_split_access_rejects_unknown_role() -> None:
    refused = admit_default_split_access("holdout")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


# --- AC4: optimistic taint, no edge, no split budget -------------------------


def test_split_fills_optimistic_no_edge_no_budget() -> None:
    assert is_ok(refuse_split_edge_or_budget())
    claim = refuse_split_edge_or_budget(claims_edge=True)
    assert is_refusal(claim)
    assert claim.category is RefusalCategory.POLICY_REJECTION
    budget = refuse_split_edge_or_budget(spends_split_budget=True)
    assert is_refusal(budget)
    assert budget.category is RefusalCategory.POLICY_REJECTION
    wrong_taint = refuse_split_edge_or_budget(taint="pessimistic")
    assert is_refusal(wrong_taint)
    assert wrong_taint.category is RefusalCategory.INVALID_INPUT


def test_split_run_constants() -> None:
    assert SPLIT_RUN_TAINT == "optimistic"
    assert SPLIT_RUN_CLAIMS_EDGE is False
    assert SPLIT_RUN_SPENDS_BUDGET is False
    run = TrialSplitRun(
        split_alias="train",
        split_fp1=_fp("train"),
        contributes_to_objective=True,
    )
    assert run.taint == "optimistic"
    assert run.fp1_identity()["taint"] == "optimistic"
    # the alias is carried on the object but never enters identity
    assert "split_alias" not in run.fp1_identity()
    assert run.fp1_identity()["split_fp1"] == _fp("train").value


# --- AC6: warm-up = embargo observation count; trading-only evidence range ----


def test_warmup_length_is_embargo_observation_count() -> None:
    train = _manifest(0)
    warmup = _ok(study_warmup(4, split_fp1=train.split_id))
    assert warmup.observation_count == 4
    assert warmup.unit == "observation-count"
    assert warmup.split_fp1 == train.split_id


def test_warmup_duration_is_refused() -> None:
    refused = study_warmup(Duration(value_ns=1_000))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_trading_evidence_range_is_trading_interval_only() -> None:
    evidence = _ok(api.trading_evidence_range([_instant(10), _instant(20)], empty_at=_instant(0)))
    assert evidence.start.value_ns == 10
    assert evidence.end.value_ns == 21  # half-open past the last trading instant
    # an all-warm-up run yields the empty interval at the anchor, never covering warm-up
    empty = _ok(api.trading_evidence_range([], empty_at=_instant(7)))
    assert empty.start.value_ns == empty.end.value_ns == 7


# --- surface / identity ------------------------------------------------------


def test_study_splits_identity_excludes_semver() -> None:
    payload = study_splits_identity()
    assert qmb.__version__ not in payload.values()
    assert payload["run_config_key"] == STUDY_SPLITS_KEY
    assert payload["studies_run_replay_only"] is True
    stamped = fingerprint(payload)
    assert is_ok(stamped)


def test_door_is_thin_wrapper() -> None:
    assert api.plan_trial_runs is qmb.plan_trial_runs
    assert api.coerce_study_splits is qmb.coerce_study_splits
    assert api.serve_split_read is qmb.serve_split_read
    assert api.StudySplits is qmb.StudySplits
    assert api.admit_study_world is qmb.admit_study_world
