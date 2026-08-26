"""Reference usage — the B-14 robustness module foundation (Story 22.1).

Executable::

    python qmb/examples/robustness_foundation_usage.py

Shows the things B-14 / Story 22.1 pin down for every ladder procedure (22.2-22.5):

1. Each rung is a pure library function under B-4 with a versioned
   statistical-procedure contract stamping its own AD-5 format version (format
   version 1); it writes no ledger line and no log.
2. Return-space statistics live in a bounded AD-7 float carve-out: P&L and equity
   stay exact integers, a float exists only inside the statistic, and it re-enters an
   exact value through one named rounding boundary — money re-entry needs a declared
   rounding mode.
3. A float-valued measure takes AD-41 label-derived identity — identical inputs
   yield identical identity, and no float bits ever enter the fingerprint.
4. The shared distribution-summary primitive returns percentile ranks, confidence
   bands, and a one-tailed empirical p-value as pure data — no pass/fail verdict, no
   invented alpha level.
5. Every threshold / iteration / scenario / block-length / minimum-observation input
   is a UI-editable configurable with no ratified value; unset, it is a typed
   invalid-input refusal, never a silently-applied default.
6. Every output claims robustness or infra-stress, never edge, and gates no live
   money while GAP-0048 is open.
"""

from __future__ import annotations

from fractions import Fraction
from typing import TypeVar

from qmb.doors import api
from qmf.core.exact import RoundingMode, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def main() -> None:
    # 1. Each rung is a pure library function with a format-version-1 contract.
    contract = _unwrap(api.procedure_contract("walk-forward"), "walk-forward contract")
    assert contract.contract_format_version == 1
    assert api.PROCEDURE_WRITES_LEDGER_LINE is False
    assert api.PROCEDURE_WRITES_LOG is False
    assert api.MODULE_HAS_GLOBAL_MUTABLE_STATE is False
    print(
        "each rung is a pure library function with a format-version-1 procedure contract; "
        "no ledger line, no log:",
        api.ROBUSTNESS_PROCEDURES,
    )

    # 2. Return-space float carve-out: floats live only inside the statistic; the
    # money path stays exact and re-entry needs a declared rounding mode.
    measure = _unwrap(api.carve_return_statistic("sharpe_ratio", 1.5), "carved sharpe")
    assert measure.magnitude == Fraction(3, 2)
    assert measure.unit_kind == UnitKind.DIMENSIONLESS_RATIO.value
    reentered = _unwrap(
        api.reenter_money_path(1.25, currency="USD", scale=2, rounding=RoundingMode.HALF_EVEN),
        "money re-entry",
    )
    assert reentered.as_fraction() == Fraction(5, 4)
    assert is_refusal(api.reenter_money_path(1.25, currency="USD", scale=2, rounding=None))
    print(
        "return-space stat lives in a bounded float carve-out; P&L stays exact integer and "
        "money re-entry needs a declared rounding mode:",
        measure.magnitude,
    )

    # 3. AD-41 label-derived identity: two distinct floats that round alike share it.
    base = _unwrap(api.carve_return_statistic("sharpe_ratio", 1.5), "base sharpe")
    nudged = _unwrap(api.carve_return_statistic("sharpe_ratio", 1.5 + 1e-15), "nudged sharpe")
    assert _unwrap(base.fingerprint(), "base fp").value == _unwrap(nudged.fingerprint(), "fp").value
    assert all(not isinstance(part, float) for part in base.fp1_identity().values())
    print("float-valued measure takes label-derived identity; no float bits enter the fingerprint")

    # 4. The distribution-summary primitive is pure data — no verdict, no alpha.
    distribution = [Fraction(value) for value in range(1, 101)]
    summary = _unwrap(
        api.summarize_distribution(
            distribution,
            90,
            api.DIRECTION_HIGHER_IS_BETTER,
            band_probabilities=[Fraction(1, 40), Fraction(39, 40)],
        ),
        "distribution summary",
    )
    assert summary.p_value == Fraction(11, 100)
    assert summary.emits_verdict is False
    assert [band.value for band in summary.bands] == [Fraction(3), Fraction(98)]
    assert is_refusal(api.refuse_pass_fail_verdict("pass"))
    print(
        "distribution summary returns percentile ranks, confidence bands, and a one-tailed "
        "p-value as pure data; no pass/fail verdict, no invented alpha:",
        f"p_value={summary.p_value}",
    )

    # 5. Required configurables: unset is a typed invalid-input refusal, no default.
    unset = api.require_positive_int({}, "qmb_mc_iterations")
    assert is_refusal(unset)
    assert unset.category is RefusalCategory.INVALID_INPUT
    assert _unwrap(api.require_positive_int({"n": 1000}, "n"), "configured iterations") == 1000
    assert api.MODULE_SHIPS_INVENTED_DEFAULT is False
    print(
        "every threshold / iteration / scenario / block-length input is a UI-editable "
        "configurable; unset is invalid input, never a silently-applied default"
    )

    # 6. Claim class is robustness or infra-stress, never edge; gates no live money.
    assert api.ROBUSTNESS_CLAIM_CLASSES == ("robustness", "infra-stress")
    assert api.CLAIM_CLASS_EDGE not in api.ROBUSTNESS_CLAIM_CLASSES
    assert is_refusal(api.refuse_edge_claim("walk-forward"))
    assert is_refusal(api.refuse_live_money_gate("walk-forward"))
    assert api.PROCEDURE_GATES_LIVE_MONEY is False
    print(
        "outputs claim robustness or infra-stress, never edge; no output gates live money "
        "while GAP-0048 is open:",
        api.CLAIM_GATED_BEHIND,
    )

    # Foundation identity is fingerprintable and carries no package SemVer.
    identity = api.robustness_foundation_identity()
    assert api.__version__ not in str(identity)
    assert is_ok(fingerprint(identity))
    print("robustness foundation ok")


if __name__ == "__main__":
    main()
