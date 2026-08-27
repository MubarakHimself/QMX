"""Epic 23 · Story 23.2 — claim-class labeling bounded by lineage + the L20 edge refusal.

Independent L3 acceptance tests T23-306..311. Each names the concrete counter-case that
would make it FAIL. Source is read-only evidence; a failing test is a FINDING.
"""

from __future__ import annotations

from conftest import (
    BASE_NS,
    assert_ct04_refusal,
    bb_resources,
    gbm_resources,
    is_ok,
    is_refusal,
    unwrap,
)

from qmf.core.fingerprint import World
from qmf.core.refusal import RefusalCategory
from qmb.data import (
    GENERATOR_PROCESSES,
    PreregisteredThreshold,
    permittable_claim_classes,
    preregister_threshold,
    read_synthetic_store,
    refuse_edge_claim,
    refuse_governed_evidence_use,
    refuse_post_hoc_threshold,
    resolve_claim_label,
    resolve_generator_config,
    robustness_report_interface,
    synthetic_caveat,
    tag_synthetic_artifact,
)

_CLAIM_CLASSES = ("infra-stress", "robustness", "logic-smoke")
_FORBIDDEN = ("edge", "alpha", "validation")


def _provenance():
    """A store-level synthetic provenance record derived from a resolved gbm config."""
    cfg = unwrap(resolve_generator_config(gbm_resources()), "config")
    return unwrap(tag_synthetic_artifact(cfg, generation_timestamp_ns=BASE_NS), "provenance")


# --- T23-306 (P0, B-7/R3): claim class is a field distinct from world ---------


def test_t23_306_label_carries_one_claim_class_distinct_from_world() -> None:
    """A completed run's label carries exactly one claim class as a field DISTINCT from
    ``world`` — both present and independently valued.

    Counter-case that FAILS: ``claim_class`` and ``world`` collapse to the same field, or the
    label carries no claim class, or an out-of-set claim class is accepted.
    """
    label = unwrap(
        resolve_claim_label(process="block-bootstrap", claim_class="infra-stress", world="simulated"),
        "label",
    )
    content = label.fp1_identity()
    assert "claim_class" in content and "world" in content
    assert content["claim_class"] == "infra-stress"
    assert content["world"] == "simulated"
    # distinct fields with independent values (claim class is not the world token).
    assert content["claim_class"] != content["world"]
    assert label.claim_class in _CLAIM_CLASSES

    # an out-of-set claim class is refused, RETURNED.
    assert_ct04_refusal(
        resolve_claim_label(process="gbm", claim_class="totally-made-up", world="replay"),
        RefusalCategory.INVALID_INPUT,
        what="out-of-set claim class",
    )


# --- T23-307 (P0, B-7/R3): claim class bounded by generator lineage -----------


def test_t23_307_from_scratch_gbm_cannot_claim_robustness_history_seeded_can() -> None:
    """A from-scratch ``gbm`` run's ``robustness`` claim is a ``policy rejection``; a
    history-seeded process additionally permits ``robustness``.

    Counter-case that FAILS: a gbm ``robustness`` label is produced, or a history-seeded
    ``robustness`` label (world=replay) is refused.
    """
    assert_ct04_refusal(
        resolve_claim_label(process="gbm", claim_class="robustness", world="replay"),
        RefusalCategory.POLICY_REJECTION,
        what="gbm robustness claim",
    )
    # lineage permittability: gbm excludes robustness, history-seeded includes it.
    gbm_permits = unwrap(permittable_claim_classes("gbm"), "gbm permits")
    bb_permits = unwrap(permittable_claim_classes("block-bootstrap"), "bb permits")
    assert "robustness" not in gbm_permits
    assert "robustness" in bb_permits

    # discriminator: a history-seeded robustness label (world=replay) is permitted.
    label = unwrap(
        resolve_claim_label(process="block-bootstrap", claim_class="robustness", world="replay"),
        "history-seeded robustness",
    )
    assert label.claim_class == "robustness"


# --- T23-308 (P0, L20): the central edge/alpha/validation firewall ------------


def test_t23_308_edge_alpha_validation_refused_under_every_process() -> None:
    """A request for an edge / alpha / validation claim on synthetic data, under ANY of the four
    processes, RETURNS a typed refusal; no permitted synthetic label ever asserts edge.

    Counter-case that FAILS: any process x forbidden-claim pair produces an ``Ok`` label, or a
    permitted label reports ``claims_edge == True``.
    """
    for process in GENERATOR_PROCESSES:
        for claim in _FORBIDDEN:
            assert_ct04_refusal(
                resolve_claim_label(process=process, claim_class=claim, world="replay"),
                RefusalCategory.POLICY_REJECTION,
                what=f"{process} {claim} claim",
            )
    # the direct L20 contract refusal.
    assert_ct04_refusal(
        refuse_edge_claim("edge", process="gbm"),
        RefusalCategory.POLICY_REJECTION,
        what="refuse_edge_claim",
    )
    # discriminator: a permitted claim is Ok AND never claims edge.
    label = unwrap(
        resolve_claim_label(process="gbm", claim_class="infra-stress", world="replay"),
        "permitted label",
    )
    assert label.claims_edge is False


# --- T23-309 (P1, SC-07/L38): thresholds deferred, no invented battery ---------


def test_t23_309_no_invented_threshold_preregistered_only() -> None:
    """The robustness report interface invents no threshold and emits no verdict; an unset
    threshold key RETURNS a refusal (no default), a bare number is a post-hoc refusal, and only a
    config-declared preregistered threshold is accepted.

    Counter-case that FAILS: an unset threshold silently yields a baked default; a bare number is
    accepted as a threshold; or the report interface materializes a numeric pass battery.
    """
    # unset threshold key -> RETURNED refusal, no invented default.
    assert_ct04_refusal(
        preregister_threshold({}, "alpha_level"),
        RefusalCategory.INVALID_INPUT,
        what="unset threshold key",
    )
    # a bare number threshold is post-hoc / invented -> refused.
    assert_ct04_refusal(
        refuse_post_hoc_threshold("alpha_level"),
        RefusalCategory.POLICY_REJECTION,
        what="post-hoc threshold",
    )
    assert_ct04_refusal(
        robustness_report_interface(threshold=0.05),
        RefusalCategory.POLICY_REJECTION,
        what="bare-number threshold on report interface",
    )
    # the interface carries no invented number when none is supplied.
    report = unwrap(robustness_report_interface(), "interface-only report")
    assert report.p_value is None
    assert report.percentile_bands == ()
    assert report.threshold is None
    assert report.emits_verdict is False

    # discriminator: a config-declared preregistered threshold IS accepted, recorded before run.
    threshold = unwrap(preregister_threshold({"alpha_level": "0.05"}, "alpha_level"), "preregistered")
    assert isinstance(threshold, PreregisteredThreshold)
    assert threshold.recorded_before_run is True
    assert threshold.value_token == "0.05"  # verbatim decimal token, never a binary float


# --- T23-310 (P0, SC-06/B-7): no verdict-bearing claim while GAP open ----------


def test_t23_310_world_simulated_read_refuses_governed_evidence() -> None:
    """A run reading store-persisted synthetic data (``world=simulated``) ships no verdict-bearing
    claim and RETURNS a ``policy rejection`` for governed-evidence use — infra-stress / logic-smoke
    only until GAP-0048.

    Counter-case that FAILS: a world=simulated read is admitted as governed evidence, or a
    world=replay source is refused.
    """
    provenance = _provenance()
    read = unwrap(read_synthetic_store(provenance), "store read classification")
    assert read.world == "simulated"
    assert read.governed_evidence_admissible is False
    assert set(read.permittable_claim_classes) == {"infra-stress", "logic-smoke"}
    assert_ct04_refusal(
        read.refuse_governed_evidence(),
        RefusalCategory.POLICY_REJECTION,
        what="world=simulated governed-evidence use",
    )
    # simulated world is refused; replay world passes through (discriminator).
    assert_ct04_refusal(
        refuse_governed_evidence_use(World.SIMULATED),
        RefusalCategory.POLICY_REJECTION,
        what="refuse_governed_evidence_use(simulated)",
    )
    assert is_ok(refuse_governed_evidence_use(World.REPLAY))


# --- T23-311 (P1, R2/spec §1): the machine-readable Gaussian caveat -----------


def test_t23_311_gaussian_family_robustness_carries_destroy_structure_caveat() -> None:
    """A ``gaussian-resample`` / ``gaussian-noise`` robustness label carries a machine-readable
    caveat that the process destroys autocorrelation / volatility clustering / fat tails ("hides
    Black Swan risk"); block-bootstrap and gbm carry none — the limitation is data, never implied.

    Counter-case that FAILS: a Gaussian-family robustness label carries no caveat, or a non-Gaussian
    process fabricates one.
    """
    for process in ("gaussian-resample", "gaussian-noise"):
        caveat = unwrap(synthetic_caveat(process), f"{process} caveat")
        assert caveat is not None
        assert set(caveat.destroys) == {"autocorrelation", "volatility-clustering", "fat-tails"}
        assert caveat.summary == "hides Black Swan risk"
        assert caveat.hides_black_swan_risk is True
        # the caveat rides the robustness label (world=replay so robustness is permitted).
        label = unwrap(
            resolve_claim_label(process=process, claim_class="robustness", world="replay"),
            f"{process} robustness label",
        )
        assert label.caveat is not None

    # discriminator: non-Gaussian processes carry no caveat.
    assert unwrap(synthetic_caveat("block-bootstrap"), "bb caveat") is None
    bb_label = unwrap(
        resolve_claim_label(process="block-bootstrap", claim_class="robustness", world="replay"),
        "bb robustness label",
    )
    assert bb_label.caveat is None
