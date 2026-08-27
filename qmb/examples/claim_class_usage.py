"""Reference usage — synthetic-run claim-class labeling and the L20 edge refusal (Story 23.2).

Executable::

    python qmb/examples/claim_class_usage.py

Shows the things AC1-AC6 pin down for a synthetic run's claim class:

1. Every synthetic run carries exactly one claim class in
   {infra-stress, robustness, logic-smoke} as a field DISTINCT from world.
2. The claim class is bounded by the generator lineage: a from-scratch gbm run
   may not claim robustness (policy rejection); a history-seeded process may.
3. L20 is a contract: an edge / alpha / validation claim on synthetic data is
   refused under any process.
4. A robustness report's percentile-band / p-value fields exist as interface
   only; no threshold is invented — a threshold is a config-declared configurable
   recorded before the run, and a post-hoc threshold is refused.
5. A world=simulated run ships no verdict-bearing claim and refuses for
   governed-evidence use — infra-stress and logic-smoke only until GAP-0048.
6. A Gaussian-family robustness label carries a machine-readable caveat that the
   process destroys autocorrelation / volatility clustering / fat tails.
"""

from __future__ import annotations

from fractions import Fraction
from typing import TypeVar

from qmb.data import (
    PreregisteredThreshold,
    SyntheticCaveat,
    permittable_claim_classes,
    preregister_threshold,
    refuse_edge_claim,
    refuse_governed_evidence_use,
    resolve_claim_label,
    robustness_report_interface,
)
from qmf.core import RefusalCategory, Result, World, is_ok, is_refusal

T = TypeVar("T")

_REPLAY = World.REPLAY.value
_SIMULATED = World.SIMULATED.value


def _ok(result: Result[T]) -> T:
    if not is_ok(result):
        raise AssertionError(result)
    return result.value


def main() -> None:
    # 1. one claim class, a field distinct from world (AC1)
    label = _ok(resolve_claim_label(process="gbm", claim_class="infra-stress", world=_SIMULATED))
    identity = label.fp1_identity()
    assert identity["claim_class"] == "infra-stress"
    assert identity["world"] == _SIMULATED
    assert identity["claim_class"] != identity["world"]
    print("exactly one claim class, a field distinct from world; claims_edge=False")

    # 2. claim class bounded by generator lineage (AC2)
    gbm_robust = resolve_claim_label(process="gbm", claim_class="robustness", world=_REPLAY)
    assert is_refusal(gbm_robust) and gbm_robust.category is RefusalCategory.POLICY_REJECTION
    seeded = _ok(
        resolve_claim_label(process="block-bootstrap", claim_class="robustness", world=_REPLAY)
    )
    assert seeded.is_verdict_bearing is True
    print("from-scratch gbm robustness is a policy rejection; history-seeded permits robustness")
    print("gbm permits:", " ".join(_ok(permittable_claim_classes("gbm"))))

    # 3. L20 as a contract — edge / alpha / validation refused under any process (AC3)
    for forbidden in ("edge", "alpha", "validation"):
        refusal = resolve_claim_label(
            process="block-bootstrap", claim_class=forbidden, world=_REPLAY
        )
        assert is_refusal(refusal) and refusal.category is RefusalCategory.POLICY_REJECTION
    direct = refuse_edge_claim("edge", process="gbm")
    assert is_refusal(direct) and direct.category is RefusalCategory.POLICY_REJECTION
    print("edge / alpha / validation claim on synthetic data refused under any process")

    # 4. percentile-band / p-value fields exist as interface only; no threshold invented (AC4)
    interface = _ok(robustness_report_interface())
    assert interface.p_value is None and interface.threshold is None
    assert interface.emits_verdict is False and interface.invents_threshold is False
    populated = _ok(robustness_report_interface(p_value=Fraction(1, 20)))
    assert populated.p_value == Fraction(1, 20)
    threshold = _ok(preregister_threshold({"qmb_pass_threshold": "0.05"}, "qmb_pass_threshold"))
    assert isinstance(threshold, PreregisteredThreshold) and threshold.recorded_before_run is True
    post_hoc = robustness_report_interface(threshold="0.05")
    assert is_refusal(post_hoc) and post_hoc.category is RefusalCategory.POLICY_REJECTION
    print("percentile-band / p-value exist as interface only; no numeric threshold invented")
    print("a pass/fail threshold is a config-declared configurable recorded before the run")

    # 5. world=simulated ships no verdict-bearing claim until GAP-0048 (AC5)
    simulated_robust = resolve_claim_label(
        process="block-bootstrap", claim_class="robustness", world=_SIMULATED
    )
    assert is_refusal(simulated_robust)
    assert simulated_robust.category is RefusalCategory.POLICY_REJECTION
    gate = refuse_governed_evidence_use(_SIMULATED)
    assert is_refusal(gate) and gate.context.get("gap") == "GAP-0048"
    assert _ok(refuse_governed_evidence_use(_REPLAY)) is World.REPLAY
    print("world=simulated refuses for governed evidence; infra-stress and logic-smoke only")
    simulated_permits = _ok(permittable_claim_classes("block-bootstrap", _SIMULATED))
    print("simulated permits:", " ".join(simulated_permits))

    # 6. Gaussian-family robustness carries a destroy-structure caveat (AC6)
    caveated = _ok(
        resolve_claim_label(process="gaussian-noise", claim_class="robustness", world=_REPLAY)
    )
    assert isinstance(caveated.caveat, SyntheticCaveat)
    assert set(caveated.caveat.destroys) == {
        "autocorrelation",
        "volatility-clustering",
        "fat-tails",
    }
    assert caveated.caveat.hides_black_swan_risk is True
    print("gaussian-family robustness carries a caveat: destroys autocorrelation / vol / fat tails")

    print("claim class labeling ok")


if __name__ == "__main__":
    main()
