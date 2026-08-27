"""Tier-1 tests for synthetic-run claim-class labeling and the L20 edge refusal (Story 23.2).

Covers the story acceptance criteria: exactly one machine-readable claim class as a
field distinct from world (AC1); the generator-lineage bound with the from-scratch
robustness policy rejection (AC2); L20 as a contract refusing edge / alpha /
validation claims (AC3); the interface-only percentile-band / p-value report with no
invented threshold and a preregistered config-declared threshold (AC4); the
world=simulated governed-evidence gate that ships no verdict-bearing claim until
GAP-0048 (AC5); and the Gaussian-family destroy-structure caveat (AC6).
"""

from __future__ import annotations

from fractions import Fraction
from typing import ClassVar, TypeVar

from qmb.data import (
    CLAIM_CLASSES,
    GENERATOR_PROCESSES,
    ClaimClassLabel,
    PercentileBand,
    PreregisteredThreshold,
    RobustnessReportInterface,
    SyntheticCaveat,
    claim_class_identity,
    data_front_identity,
    generator_lineage,
    permittable_claim_classes,
    preregister_threshold,
    refuse_edge_claim,
    refuse_governed_evidence_use,
    refuse_post_hoc_threshold,
    resolve_claim_label,
    robustness_report_interface,
    synthetic_caveat,
)
from qmb.data.claim_class import (
    CAVEAT_DESTROYS,
    CAVEAT_SUMMARY,
    CLAIMS_EDGE,
    FORBIDDEN_CLAIM_CLASSES,
    LINEAGE_FROM_SCRATCH,
    LINEAGE_HISTORY_SEEDED,
    SIMULATED_PERMITS,
)
from qmf.core import RefusalCategory, Result, World, is_ok, is_refusal

T = TypeVar("T")

_REPLAY = World.REPLAY.value
_SIMULATED = World.SIMULATED.value


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


# --- AC1: exactly one claim class, a field distinct from world ---------------


def test_label_carries_one_claim_class_distinct_from_world() -> None:
    label = _ok(resolve_claim_label(process="gbm", claim_class="infra-stress", world=_SIMULATED))
    assert isinstance(label, ClaimClassLabel)
    assert label.claim_class == "infra-stress"
    assert label.claim_class in CLAIM_CLASSES
    assert label.world == _SIMULATED
    identity = label.fp1_identity()
    # claim_class and world are DISTINCT keys on the label (AC1, B-7).
    assert identity["claim_class"] == "infra-stress"
    assert identity["world"] == _SIMULATED
    assert identity["claim_class"] != identity["world"]
    assert identity["claims_edge"] is False


def test_label_fingerprint_is_deterministic() -> None:
    first = _ok(resolve_claim_label(process="gbm", claim_class="logic-smoke", world=_REPLAY))
    second = _ok(resolve_claim_label(process="gbm", claim_class="logic-smoke", world=_REPLAY))
    assert _ok(first.fingerprint()) == _ok(second.fingerprint())
    assert first.as_label() == second.as_label()


def test_label_accepts_world_enum_and_run_config_like() -> None:
    from_enum = _ok(
        resolve_claim_label(process="gbm", claim_class="infra-stress", world=World.REPLAY)
    )
    assert from_enum.world == _REPLAY

    class _ConfigLike:
        world = World.SIMULATED

    from_config = _ok(
        resolve_claim_label(process="gbm", claim_class="infra-stress", world=_ConfigLike())
    )
    assert from_config.world == _SIMULATED


def test_a_synthetic_run_is_never_world_live() -> None:
    refusal = resolve_claim_label(process="gbm", claim_class="infra-stress", world="live")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION


def test_unknown_world_token_is_invalid_input() -> None:
    refusal = resolve_claim_label(process="gbm", claim_class="infra-stress", world="wonderland")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


def test_unknown_claim_class_token_is_invalid_input() -> None:
    refusal = resolve_claim_label(process="gbm", claim_class="cromulent", world=_REPLAY)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


# --- AC2: claim class bounded by generator lineage ---------------------------


def test_generator_lineage_maps_process_to_lineage() -> None:
    assert _ok(generator_lineage("gbm")) == LINEAGE_FROM_SCRATCH
    assert _ok(generator_lineage("block-bootstrap")) == LINEAGE_HISTORY_SEEDED
    assert _ok(generator_lineage("gaussian-resample")) == LINEAGE_HISTORY_SEEDED
    assert _ok(generator_lineage("gaussian-noise")) == LINEAGE_HISTORY_SEEDED


def test_unknown_process_lineage_is_invalid_input() -> None:
    refusal = generator_lineage("regime-switching")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


def test_from_scratch_gbm_robustness_is_policy_rejection() -> None:
    refusal = resolve_claim_label(process="gbm", claim_class="robustness", world=_REPLAY)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert refusal.context.get("lineage") == LINEAGE_FROM_SCRATCH


def test_from_scratch_gbm_permits_infra_and_logic_only() -> None:
    assert _ok(resolve_claim_label(process="gbm", claim_class="infra-stress", world=_REPLAY))
    assert _ok(resolve_claim_label(process="gbm", claim_class="logic-smoke", world=_REPLAY))
    assert set(_ok(permittable_claim_classes("gbm"))) == set(SIMULATED_PERMITS)


def test_history_seeded_replay_additionally_permits_robustness() -> None:
    label = _ok(
        resolve_claim_label(process="block-bootstrap", claim_class="robustness", world=_REPLAY)
    )
    assert label.claim_class == "robustness"
    assert label.is_verdict_bearing is True
    permits = _ok(permittable_claim_classes("block-bootstrap", _REPLAY))
    assert "robustness" in permits


# --- AC3: L20 as a contract, edge / alpha / validation refused ---------------


def test_edge_alpha_validation_claims_are_refused_under_any_process() -> None:
    for forbidden in FORBIDDEN_CLAIM_CLASSES:
        for process in GENERATOR_PROCESSES:
            refusal = resolve_claim_label(process=process, claim_class=forbidden, world=_REPLAY)
            assert is_refusal(refusal), (process, forbidden)
            assert refusal.category is RefusalCategory.POLICY_REJECTION


def test_refuse_edge_claim_is_policy_rejection() -> None:
    refusal = refuse_edge_claim("edge", process="gbm")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert refusal.context.get("requested_claim") == "edge"


def test_no_label_ever_claims_edge() -> None:
    assert CLAIMS_EDGE is False
    for process, claim, world in (
        ("gbm", "infra-stress", _SIMULATED),
        ("block-bootstrap", "robustness", _REPLAY),
        ("gaussian-noise", "logic-smoke", _REPLAY),
    ):
        label = _ok(resolve_claim_label(process=process, claim_class=claim, world=world))
        assert label.claims_edge is False


# --- AC4: interface-only percentile-band / p-value, no invented threshold -----


def test_robustness_report_interface_exists_with_no_invented_number() -> None:
    report = _ok(robustness_report_interface())
    assert isinstance(report, RobustnessReportInterface)
    assert report.claim_class == "robustness"
    assert report.p_value is None
    assert report.percentile_bands == ()
    assert report.threshold is None
    assert report.emits_verdict is False
    assert report.invents_threshold is False


def test_report_carries_supplied_pure_data() -> None:
    band = _ok(PercentileBand.try_create(Fraction(95, 100), Fraction(3, 2)))
    report = _ok(robustness_report_interface(p_value=Fraction(1, 20), percentile_bands=(band,)))
    assert report.p_value == Fraction(1, 20)
    assert report.percentile_bands == (band,)


def test_report_refuses_raw_binary_float_p_value() -> None:
    refusal = robustness_report_interface(p_value=0.05)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


def test_percentile_band_refuses_float_and_out_of_range_probability() -> None:
    assert is_refusal(PercentileBand.try_create(0.95, Fraction(1, 1)))
    out_of_range = PercentileBand.try_create(Fraction(3, 2), Fraction(1, 1))
    assert is_refusal(out_of_range)
    assert out_of_range.category is RefusalCategory.INVALID_INPUT


def test_report_interface_is_robustness_only() -> None:
    refusal = robustness_report_interface(claim_class="infra-stress")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


def test_preregistered_threshold_from_config_recorded_before_run() -> None:
    config = {"qmb_pass_threshold": "0.05"}
    threshold = _ok(preregister_threshold(config, "qmb_pass_threshold"))
    assert isinstance(threshold, PreregisteredThreshold)
    assert threshold.value_token == "0.05"
    assert threshold.recorded_before_run is True
    report = _ok(robustness_report_interface(threshold=threshold))
    assert report.threshold == threshold


def test_preregister_threshold_unset_is_invalid_input() -> None:
    refusal = preregister_threshold({}, "qmb_pass_threshold")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


def test_preregister_threshold_refuses_binary_float_value() -> None:
    refusal = preregister_threshold({"qmb_pass_threshold": 0.05}, "qmb_pass_threshold")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


def test_post_hoc_or_bare_threshold_is_refused() -> None:
    refusal = robustness_report_interface(threshold="0.05")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION

    direct = refuse_post_hoc_threshold("chosen-after-the-run")
    assert is_refusal(direct)
    assert direct.category is RefusalCategory.POLICY_REJECTION


def test_report_reads_run_config_keys_mapping() -> None:
    class _ConfigLike:
        keys: ClassVar[dict[str, str]] = {"qmb_pass_threshold": "10"}

    threshold = _ok(preregister_threshold(_ConfigLike(), "qmb_pass_threshold"))
    assert threshold.value_token == "10"


def test_robustness_label_carries_report_interface() -> None:
    report = _ok(robustness_report_interface())
    label = _ok(
        resolve_claim_label(
            process="block-bootstrap",
            claim_class="robustness",
            world=_REPLAY,
            report=report,
        )
    )
    assert label.report is report
    assert "report" in label.fp1_identity()


def test_non_robustness_label_refuses_a_report() -> None:
    report = _ok(robustness_report_interface())
    refusal = resolve_claim_label(
        process="gbm", claim_class="infra-stress", world=_REPLAY, report=report
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


# --- AC5: world=simulated ships no verdict-bearing claim until GAP-0048 -------


def test_simulated_history_seeded_robustness_is_policy_rejection() -> None:
    refusal = resolve_claim_label(
        process="block-bootstrap", claim_class="robustness", world=_SIMULATED
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert refusal.context.get("gap") == "GAP-0048"


def test_simulated_permits_infra_and_logic_only() -> None:
    assert set(_ok(permittable_claim_classes("block-bootstrap", _SIMULATED))) == set(
        SIMULATED_PERMITS
    )
    assert _ok(
        resolve_claim_label(process="block-bootstrap", claim_class="infra-stress", world=_SIMULATED)
    )
    assert _ok(
        resolve_claim_label(process="block-bootstrap", claim_class="logic-smoke", world=_SIMULATED)
    )


def test_refuse_governed_evidence_use_gates_simulated_only() -> None:
    refusal = refuse_governed_evidence_use(_SIMULATED)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert refusal.context.get("gap") == "GAP-0048"
    assert _ok(refuse_governed_evidence_use(_REPLAY)) is World.REPLAY


def test_refuse_governed_evidence_use_accepts_world_enum() -> None:
    assert _ok(refuse_governed_evidence_use(World.REPLAY)) is World.REPLAY
    assert is_refusal(refuse_governed_evidence_use(World.SIMULATED))


# --- AC6: Gaussian-family destroy-structure caveat ---------------------------


def test_gaussian_family_robustness_label_carries_caveat() -> None:
    for process in ("gaussian-resample", "gaussian-noise"):
        label = _ok(resolve_claim_label(process=process, claim_class="robustness", world=_REPLAY))
        assert isinstance(label.caveat, SyntheticCaveat)
        assert label.caveat.destroys == CAVEAT_DESTROYS
        assert label.caveat.summary == CAVEAT_SUMMARY
        assert label.caveat.hides_black_swan_risk is True
        assert set(label.caveat.destroys) == {
            "autocorrelation",
            "volatility-clustering",
            "fat-tails",
        }
        assert "caveat" in label.fp1_identity()


def test_block_bootstrap_robustness_has_no_caveat() -> None:
    label = _ok(
        resolve_claim_label(process="block-bootstrap", claim_class="robustness", world=_REPLAY)
    )
    assert label.caveat is None
    assert "caveat" not in label.fp1_identity()


def test_synthetic_caveat_only_for_gaussian_family() -> None:
    assert _ok(synthetic_caveat("gaussian-resample")) is not None
    assert _ok(synthetic_caveat("gaussian-noise")) is not None
    assert _ok(synthetic_caveat("block-bootstrap")) is None
    assert _ok(synthetic_caveat("gbm")) is None
    refusal = synthetic_caveat("no-such-process")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


# --- identity fold -----------------------------------------------------------


def test_claim_class_identity_is_folded_into_data_front_identity() -> None:
    identity = claim_class_identity()
    assert identity["claims_edge"] is False
    assert identity["thresholds_deferred_to"] == "GAP-0048/GAP-0049"
    front = data_front_identity()
    for key, value in identity.items():
        assert front[key] == value


# --- value types and coercion edge cases -------------------------------------


def test_percentile_band_exposes_exact_ratios_and_identity() -> None:
    band = _ok(PercentileBand.try_create(Fraction(95, 100), Fraction(7, 4)))
    assert band.probability == Fraction(95, 100)
    assert band.value == Fraction(7, 4)
    identity = band.fp1_identity()
    assert identity["probability_num"] == 19  # Fraction(95, 100) reduces to 19/20
    assert identity["probability_den"] == 20
    assert identity["value_den"] == 4


def test_percentile_band_refuses_float_value_and_non_numeric() -> None:
    assert is_refusal(PercentileBand.try_create(Fraction(1, 2), 0.25))
    assert is_refusal(PercentileBand.try_create(Fraction(1, 2), "x"))
    assert is_refusal(PercentileBand.try_create(True, Fraction(1, 2)))


def test_report_carries_single_band_and_emits_identity() -> None:
    band = _ok(PercentileBand.try_create(Fraction(9, 10), Fraction(2, 1)))
    report = _ok(robustness_report_interface(p_value=Fraction(1, 4), percentile_bands=band))
    assert report.percentile_bands == (band,)
    identity = report.fp1_identity()
    assert identity["p_value_num"] == 1
    assert identity["p_value_den"] == 4
    assert identity["emits_verdict"] is False


def test_report_threshold_enters_identity() -> None:
    threshold = _ok(preregister_threshold({"k": "3"}, "k"))
    report = _ok(robustness_report_interface(threshold=threshold))
    assert threshold.fp1_identity()["value"] == "3"
    assert "threshold" in report.fp1_identity()


def test_report_refuses_non_sequence_and_bad_band_item() -> None:
    assert is_refusal(robustness_report_interface(percentile_bands=5))
    assert is_refusal(robustness_report_interface(percentile_bands=["not-a-band"]))


def test_report_refuses_out_of_range_and_non_numeric_p_value() -> None:
    assert is_refusal(robustness_report_interface(p_value=Fraction(3, 2)))
    assert is_refusal(robustness_report_interface(p_value="half"))


def test_preregister_threshold_rejects_bool_and_bad_config() -> None:
    assert is_refusal(preregister_threshold({"k": True}, "k"))
    assert is_refusal(preregister_threshold({"k": ["a"]}, "k"))
    assert is_refusal(preregister_threshold(123, "k"))
    assert is_refusal(preregister_threshold({"k": "1"}, "  "))


def test_refuse_post_hoc_threshold_and_edge_claim_without_names() -> None:
    assert is_refusal(refuse_post_hoc_threshold(None))
    bare = refuse_edge_claim("alpha")
    assert is_refusal(bare)
    assert "process" not in bare.context
    assert is_refusal(refuse_edge_claim(None))


def test_permittable_claim_classes_refuses_live_world() -> None:
    refusal = permittable_claim_classes("gbm", "live")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert set(_ok(permittable_claim_classes("gbm"))) == set(SIMULATED_PERMITS)


def test_governed_evidence_gate_refuses_unresolvable_source() -> None:
    assert is_refusal(refuse_governed_evidence_use("bogus-world"))
    assert is_refusal(refuse_governed_evidence_use(123))
