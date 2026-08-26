"""Reference usage — train/test split discipline (Story 21.3, B-8, OPT-9).

Executable::

    python qmb/examples/optimize_splits_usage.py

Shows the things B-8 / OPT-9 / Story 21.3 pin down:

1. A Study names a TRAINING split manifest and a TESTING split manifest, each by
   CT-12 fingerprint. Every trial runs twice on the identical parameter set: the
   training run computes the objective, the testing run records its measures
   without contributing to the objective. Only the training run may feed the
   objective; letting the testing run feed it is a policy rejection.
2. Both split-manifest fingerprints appear on the trial label; "train"/"test" are
   display aliases only and are never substituted for the fingerprints in identity.
3. Any split read is served through qmf-data: the ~12-month seal, the embargo, the
   knowledge-time rule, and the calendar-in-band rule are enforced at the read
   boundary, and the sealed holdout is excluded from default access.
4. Every fill carries the optimistic taint, the run spends no split budget, and it
   claims no edge until GAP-0048.
5. A Study that would resolve to world=simulated (any store-tainted synthetic read)
   is a policy rejection — Studies run world=replay only in V1.
6. Warm-up length is the split manifest's declared embargo observation count (an
   AD-22 count, never a Duration) and the result-label evidence range is the
   trading interval only.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.doors import api
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


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _fp(*parts: object) -> Fingerprint:
    return _unwrap(fingerprint({"parts": list(parts)}), "fp")


def _instant(ns: int) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _manifest(offset: int) -> SplitManifest:
    """A CT-12 split manifest with instant boundaries, world=replay."""
    calendar = _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025b"), "calendar")
    segments = _unwrap(
        SplitManifest.default_split_segments([1000 + offset, 2000 + offset, 3000 + offset]),
        "segments",
    )
    seal_boundary = _unwrap(SplitBoundary.try_create(3000 + offset), "seal boundary")
    return _unwrap(
        SplitManifest.try_create(
            calendar_identity=calendar,
            segments=segments,
            seal_boundary=seal_boundary,
            purge_width=0,
            embargo_width=0,
            world=World.REPLAY,
        ),
        "split manifest",
    )


def main() -> None:
    train_manifest = _manifest(0)
    test_manifest = _manifest(5000)

    # 1. A Study names both splits by fingerprint; the trial runs twice on one
    #    parameter set — objective on train, recorded-only on test.
    splits = _unwrap(
        api.coerce_study_splits({"train": train_manifest, "test": test_manifest}),
        "study splits",
    )
    assert isinstance(splits, qmb.StudySplits)
    assert splits.world is World.REPLAY
    assert splits.objective_split == train_manifest.fingerprint
    parameter_set = _fp("params", "fast_ma=10", "slow_ma=30")
    plan = _unwrap(api.plan_trial_runs(splits, parameter_set), "trial plan")
    assert plan.train_run.contributes_to_objective is True
    assert plan.test_run.contributes_to_objective is False
    assert plan.train_run.split_fp1 == train_manifest.fingerprint
    assert plan.test_run.split_fp1 == test_manifest.fingerprint
    print("objective on train, recorded-only on test: two runs share one parameter set")

    # Only the training run computes the objective; the testing run cannot feed it.
    assert is_ok(api.admit_objective_run(plan.train_run))
    refused_objective = api.admit_objective_run(plan.test_run)
    assert is_refusal(refused_objective)
    assert refused_objective.category is RefusalCategory.POLICY_REJECTION
    print("only the training run computes the objective; the testing run cannot feed it")

    # 2. Both fingerprints ride on the trial label; train/test are display aliases only.
    label = plan.trial_label()
    assert label["train_split_fp1"] == train_manifest.split_id
    assert label["test_split_fp1"] == test_manifest.split_id
    display = label["display"]
    assert isinstance(display, dict)
    assert display["aliases"] == {
        "train": train_manifest.split_id,
        "test": test_manifest.split_id,
    }
    identity = splits.fp1_identity()
    assert identity["train_split_fp1"] == train_manifest.split_id
    assert identity["test_split_fp1"] == test_manifest.split_id
    assert "train" not in identity and "test" not in identity  # aliases never substitute the fp
    print(
        "both split-manifest fingerprints on the trial label; train/test are display aliases only"
    )

    # A distinct train and test are required: one fingerprint for both is refused.
    same = api.coerce_study_splits({"train": train_manifest, "test": train_manifest})
    assert is_refusal(same) and same.category is RefusalCategory.INVALID_INPUT
    print("naming one fingerprint for both splits is invalid input; no out-of-sample content")

    # 3. Any split read is served through qmf-data: seal, calendar, embargo, knowledge-time.
    seal = _unwrap(HoldoutSeal.from_manifest(train_manifest, 12), "holdout seal")
    unsealed = api.serve_split_read(
        seal=seal, position=_instant(1500), boundary=ReadBoundary.RESEARCH_DOOR
    )
    assert is_ok(unsealed)
    sealed = api.serve_split_read(
        seal=seal, position=_instant(4000), boundary=ReadBoundary.RESEARCH_DOOR
    )
    assert is_refusal(sealed) and sealed.category is RefusalCategory.POLICY_REJECTION
    foreign_calendar = _unwrap(CalendarIdentity.try_create("forex-17NY", "v9", "2025b"), "foreign")
    assert is_refusal(train_manifest.admits_calendar(foreign_calendar))  # calendar in-band
    record = _unwrap(
        KnowledgeRecord.try_create(
            observed_at=1200, knowledge_time=1200, kind=KnowledgeKind.INDICATOR
        ),
        "knowledge record",
    )
    partitioned = api.serve_split_read(
        seal=seal,
        position=_instant(1200),
        boundary=ReadBoundary.RESEARCH_DOOR,
        manifest=train_manifest,
        record=record,
    )
    assert is_ok(partitioned)
    print("12-month seal, calendar-in-band, embargo and knowledge-time enforced at the boundary")

    # The sealed holdout is excluded from default access; only train/validation are default.
    assert is_ok(api.admit_default_split_access(SegmentRole.TRAIN))
    assert is_ok(api.admit_default_split_access(SegmentRole.VALIDATION))
    holdout = api.admit_default_split_access(SegmentRole.SEALED_TEST)
    assert is_refusal(holdout) and holdout.category is RefusalCategory.POLICY_REJECTION
    print("the sealed holdout is excluded from default access")

    # 4. Every fill is optimistic; the run spends no split budget and claims no edge.
    assert is_ok(api.refuse_split_edge_or_budget())
    assert is_refusal(api.refuse_split_edge_or_budget(claims_edge=True))
    assert is_refusal(api.refuse_split_edge_or_budget(spends_split_budget=True))
    assert api.SPLIT_RUN_TAINT == "optimistic"
    assert api.SPLIT_RUN_CLAIMS_EDGE is False and api.SPLIT_RUN_SPENDS_BUDGET is False
    print("every fill optimistic; the run spends no split budget and claims no edge until GAP-0048")

    # 5. A world=simulated Study is a policy rejection; Studies run world=replay only.
    simulated_splits = api.StudySplits.try_create(
        train_manifest.split_id, test_manifest.split_id, world=World.SIMULATED
    )
    assert is_refusal(simulated_splits)
    assert simulated_splits.category is RefusalCategory.POLICY_REJECTION
    assert is_refusal(api.admit_study_world(World.SIMULATED))
    assert is_ok(api.admit_study_world(World.REPLAY))
    print("world=simulated is a policy rejection; Studies run world=replay only in V1")

    # 6. Warm-up length is the embargo observation count, never a Duration; evidence
    #    range is the trading interval only.
    warmup = _unwrap(api.study_warmup(3, split_fp1=train_manifest.split_id), "warmup")
    assert warmup.observation_count == 3 and warmup.unit == "observation-count"
    duration_refused = api.study_warmup(Duration(value_ns=1_000))
    assert is_refusal(duration_refused)
    evidence = _unwrap(
        api.trading_evidence_range([_instant(10), _instant(20)], empty_at=_instant(0)),
        "evidence range",
    )
    assert evidence.start.value_ns == 10 and evidence.end.value_ns == 21  # trading interval only
    print(
        "warm-up length is the embargo observation count, never a Duration; "
        "evidence range is the trading interval only"
    )

    # The qmb door is a thin wrapper over the one pure library surface.
    assert api.plan_trial_runs is qmb.plan_trial_runs
    assert api.coerce_study_splits is qmb.coerce_study_splits
    assert api.serve_split_read is qmb.serve_split_read
    print("the qmb door is a thin wrapper over one pure library split-discipline surface")

    print(f"qmb {qmb.__version__}")
    print("train/test split discipline ok")


if __name__ == "__main__":
    main()
