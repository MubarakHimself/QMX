"""Epic 23 · Story 23.4 — deterministic multi-scenario generation with a pinned RNG.

Independent L3 acceptance tests T23-318..323. Each names the concrete counter-case that
would make it FAIL. Source is read-only evidence; a failing test is a FINDING.
"""

from __future__ import annotations

import random

from conftest import (
    SEVEN_CATEGORIES,
    assert_ct04_refusal,
    bb_resources,
    gbm_resources,
    is_ok,
    is_refusal,
    source_rows,
    unwrap,
)

from qmf.core.refusal import RefusalCategory
from qmb.data import (
    PinnedRng,
    derive_scenario_seeds,
    derive_substream_seed,
    generate,
    generate_scenarios,
    refuse_robustness_band_for_from_scratch,
    regenerate_scenario,
    reproduce_generation,
)


# --- T23-318 (P1, R5/B-10): reproduce-or-refuse -------------------------------


def test_t23_318_full_artifact_is_bit_reproducible_or_refuses() -> None:
    """With a seed set, the artifact is bit-reproducible; re-generation reproduces the recorded
    fingerprint or RETURNS a typed refusal on a mismatch — never a best-effort near-match.

    Counter-case that FAILS: two runs of the same resources differ; or a mismatched expected
    fingerprint is silently accepted.
    """
    res = gbm_resources(seed=21)
    first = unwrap(generate(res), "first generate")
    second = unwrap(generate(res), "second generate")
    assert first.artifact_fingerprint == second.artifact_fingerprint

    # reproduce against the correct recorded fingerprint -> Ok.
    assert is_ok(reproduce_generation(res, expected_artifact_fingerprint=first.artifact_fingerprint))
    # reproduce against a wrong fingerprint -> RETURNED refusal (reproduce-or-refuse).
    assert_ct04_refusal(
        reproduce_generation(res, expected_artifact_fingerprint="fp1:deadbeefdeadbeef"),
        RefusalCategory.INVALID_INPUT,
        what="reproduce against a mismatched fingerprint",
    )
    # a different seed is a different artifact fingerprint (determinism is content-addressed).
    other = unwrap(generate(gbm_resources(seed=22)), "other seed")
    assert other.artifact_fingerprint != first.artifact_fingerprint


# --- T23-319 (P1, R4/R5/spec §2A.3): QMX-owned version-pinned RNG --------------


def test_t23_319_pinned_rng_is_deterministic_and_independent_of_stdlib_random() -> None:
    """The generator draws from a QMX-owned deterministic RNG, not a runtime stdlib ``Random``:
    two instances seeded alike produce identical streams, and generation is unaffected by the
    Python global ``random`` state.

    Counter-case that FAILS: reseeding the stdlib global ``random`` between two generations changes
    the produced artifact (i.e. the generator leaked through stdlib Random); or equal seeds produce
    diverging streams.
    """
    # the pinned RNG is not the stdlib Random and is deterministic for equal seeds.
    assert not isinstance(PinnedRng(0), random.Random)
    a = PinnedRng(1234)
    b = PinnedRng(1234)
    assert [a.next_u64() for _ in range(8)] == [b.next_u64() for _ in range(8)]
    c = PinnedRng(1235)
    assert [PinnedRng(1234).next_u64() for _ in range(8)] != [c.next_u64() for _ in range(8)]

    # generation is independent of the stdlib global random state.
    res = bb_resources(seed=9)
    src = source_rows()
    random.seed(1)
    run1 = unwrap(generate(res, source_series=src), "run1")
    random.seed(999999)
    _ = [random.random() for _ in range(50)]
    run2 = unwrap(generate(res, source_series=src), "run2")
    assert run1.artifact_fingerprint == run2.artifact_fingerprint

    # the RNG algorithm + version are recorded in provenance (non-empty).
    assert isinstance(run1.rng_algorithm, str) and run1.rng_algorithm != ""
    assert isinstance(run1.rng_version, int)
    assert run1.store_provenance.get("rng_algorithm") == run1.rng_algorithm
    assert run1.store_provenance.get("rng_is_runtime_stdlib_random") is False


# --- T23-320 (P1, R5/spec §2B): deterministic per-scenario substreams ---------


def test_t23_320_scenario_substreams_are_seed_plus_index_and_reproduce_in_isolation() -> None:
    """Each scenario's substream is ``base_seed + scenario_index`` so scenario ``k`` reproduces in
    isolation, and every scenario is tagged by its index.

    Counter-case that FAILS: the substream rule is not ``base+index``; or regenerating scenario ``k``
    alone does not reproduce the fingerprint it had inside the full fan-out; or two scenarios collide.
    """
    base = 40
    seeds = unwrap(derive_scenario_seeds(base, 4), "scenario seeds")
    assert seeds == tuple(base + k for k in range(4))
    assert all(derive_substream_seed(base, k) == base + k for k in range(4))

    res = bb_resources(seed=base, scenario_count=4)
    src = source_rows()
    fanout = unwrap(generate_scenarios(res, source_series=src), "fanout")
    for k in range(4):
        inside = fanout.scenario_at(k)
        assert inside is not None and inside.scenario_index == k
        isolated = unwrap(regenerate_scenario(res, k, source_series=src), f"isolated scenario {k}")
        assert isolated.series_fingerprint.value == inside.series_fingerprint.value
    # discriminator: distinct scenarios do not collide.
    assert fanout.scenario_at(1).series_fingerprint.value != fanout.scenario_at(2).series_fingerprint.value


# --- T23-321 (P1, R5/spec §2B): history-seeded scenario 0 = untouched original -


def test_t23_321_history_seeded_scenario_zero_is_untouched_original() -> None:
    """For a history-seeded process, scenario 0 is the untouched original real path and scenarios
    ``>0`` are perturbed (Jesse anchor).

    Counter-case that FAILS: scenario 0's OHLC differs from the cited source, or scenario 1 equals
    scenario 0 (no perturbation).
    """
    src = source_rows(n=10)
    res = bb_resources(seed=7, scenario_count=3, count=5)
    fanout = unwrap(generate_scenarios(res, source_series=src), "fanout")
    s0 = fanout.scenario_at(0)
    s1 = fanout.scenario_at(1)
    assert s0.is_original_anchor is True
    # scenario 0 carries the source OHLC verbatim on the grid (the real anchor).
    for i, bar in enumerate(s0.bars):
        assert bar.open == src[i]["open"]
        assert bar.high == src[i]["high"]
        assert bar.low == src[i]["low"]
        assert bar.close == src[i]["close"]
    # scenario 1 is a perturbation (differs from the untouched original).
    assert s1.is_original_anchor is False
    assert tuple(b.close for b in s1.bars) != tuple(b.close for b in s0.bars)


# --- T23-322 (P0, spec §5 Q7/R3/L20): from-scratch gbm has no anchor / no band -


def test_t23_322_from_scratch_gbm_has_no_anchor_and_no_robustness_band() -> None:
    """A from-scratch ``gbm`` fan-out has no scenario-0 anchor and NO robustness percentile band /
    p-value; a band request RETURNS a ``policy rejection``; only infra-stress / logic-smoke ship.

    Counter-case that FAILS: a gbm fan-out reports an original anchor or a computable robustness
    band; a gbm band request is not refused; or a history-seeded fan-out is treated the same.
    """
    gbm_fanout = unwrap(generate_scenarios(gbm_resources(seed=5, scenario_count=4)), "gbm fanout")
    assert gbm_fanout.has_original_anchor is False
    assert gbm_fanout.robustness_band_computable is False
    assert gbm_fanout.original_anchor() is None
    assert set(gbm_fanout.permittable_claim_classes) == {"infra-stress", "logic-smoke"}
    assert_ct04_refusal(
        gbm_fanout.robustness_band_refusal(),
        RefusalCategory.POLICY_REJECTION,
        what="gbm fan-out robustness-band request",
    )
    assert_ct04_refusal(
        refuse_robustness_band_for_from_scratch("gbm"),
        RefusalCategory.POLICY_REJECTION,
        what="refuse_robustness_band_for_from_scratch",
    )
    # discriminator: a history-seeded fan-out DOES anchor and permits a band.
    hs = unwrap(generate_scenarios(bb_resources(seed=5, scenario_count=4), source_series=source_rows()), "hs fanout")
    assert hs.has_original_anchor is True
    assert hs.robustness_band_computable is True
    assert hs.robustness_band_refusal() is None


# --- T23-323 (P2, B-5/R7/R8; Epic-15 seam): scenario failures are counted -----


def test_t23_323_scenario_failures_are_counted_and_typed_never_silently_dropped() -> None:
    """Under multi-scenario fan-out, failing scenarios are COUNTED and reported as typed refusals
    (``filtered_count`` + ``failures``), surviving scenarios are still returned, and
    ``produced + filtered == scenario_count`` — never a silent drop.

    Counter-case that FAILS: ``produced + filtered < scenario_count`` (a scenario vanished), a
    failure carries no CT-04 category, or failures are raised instead of returned.

    NOTE: the governor mechanics (process-per-run, min(cpu,memory), enqueue-when-full) are
    Epic-15-owned (AR-50/B-5) and are asserted there, not here (§7.2).
    """
    # a divergent gbm config where SOME scenarios overflow and some survive (deterministic).
    res = gbm_resources(count=60, scenario_count=24, seed=1, volatility="0.60")
    fanout = unwrap(generate_scenarios(res), "divergent gbm fanout")
    assert fanout.scenario_count == 24
    assert fanout.produced_count > 0, "some scenarios must survive"
    assert fanout.filtered_count > 0, "some scenarios must fail (this config is divergent)"
    assert fanout.produced_count + fanout.filtered_count == fanout.scenario_count
    assert len(fanout.failures) == fanout.filtered_count
    for failure in fanout.failures:
        # each failure is a typed refusal record carrying one of the seven CT-04 categories.
        assert any(failure.category == cat.value for cat in SEVEN_CATEGORIES)
        assert isinstance(failure.scenario_index, int)
