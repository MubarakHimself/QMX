"""L3 acceptance — Story 7.6 first wrapper set + upgrade gate (T7-A22..A24)."""

from __future__ import annotations

import os

import _fixtures as F
import pytest
from qmf.core import World, is_ok, is_refusal
from qmf.indicators import (
    WRAPPER_FORMULAS,
    ModeEqualityComparator,
    PresenceState,
    ReferenceKernel,
    StreamingIndicator,
    assert_mode_equality,
    compare_reference_outputs,
    compute_batch,
    configure_wrapper,
    reference_lookback,
    reference_status,
    series_equal_within_ulps,
    wrapper_set_conformance_defects,
)


def _wrapper_config(formula_id: str, period_n: int = 3):
    return F.unwrap(
        configure_wrapper(
            formula_id=formula_id,
            period=F.period(period_n),
            inputs=[F.series_input("close")],
            calendar_requirements=[F.calendar()],
            arithmetic_reference_configuration=reference_status().value,
        )
    )


def _stream(cfg, values):
    inst = F.unwrap(
        StreamingIndicator.try_create(
            cfg, kernel=ReferenceKernel(), world=World.REPLAY, writer_id=F.writer(), scope=F.scope(),
            input_scales={"close": 2},
        )
    )
    for i, v in enumerate(values):
        assert is_ok(inst.update({"close": F.observation(v, PresenceState.PRESENT, 1_000 + i)}))
    return F.unwrap(inst.result())


# --- T7-A22 [R29, R30] P0 — each wrapper wraps + passes equality ------------


def test_a22_wrapper_set_is_conformant_wrapping_not_reimplementing() -> None:
    """Every wrapper wraps the reference formula the registry assigns it (no
    re-implementation). Counter-case: a wrapper whose delegate mismatches its owner."""
    assert wrapper_set_conformance_defects() == ()


@pytest.mark.parametrize("formula_id", sorted(WRAPPER_FORMULAS))
def test_a22_each_wrapper_declares_both_modes_and_passes_the_equality_law(formula_id: str) -> None:
    """Each wrapper is both-modes with warm-up ≥ the reference lookback, and its streaming
    output equals its batch output under the declared integer-ULP tolerance."""
    cfg = _wrapper_config(formula_id, period_n=3)
    assert {m.value for m in cfg.supported_modes} == {"batch", "streaming"}
    assert cfg.warm_up >= F.unwrap(reference_lookback(formula_id, F.period(3)))
    values = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
    batch = F.unwrap(compute_batch(cfg, {"close": F.input_series(values)}, kernel=ReferenceKernel(), world=World.REPLAY))
    streamed = _stream(cfg, values)
    equal = assert_mode_equality(cfg, batch, streamed, ModeEqualityComparator())
    assert is_ok(equal) and equal.value is True, f"{formula_id}: streaming != batch"


def test_a22_sma_wrapper_passes_restore_equivalence() -> None:
    cfg = _wrapper_config("sma", period_n=3)
    values = [100, 102, 101, 103, 105, 104]
    inst = F.unwrap(
        StreamingIndicator.try_create(
            cfg, kernel=ReferenceKernel(), world=World.REPLAY, writer_id=F.writer(), scope=F.scope(),
            input_scales={"close": 2},
        )
    )
    for i, v in enumerate(values[:3]):
        F.unwrap(inst.update({"close": F.observation(v, PresenceState.PRESENT, 1_000 + i)}))
    snapshot = F.unwrap(inst.snapshot())
    restored = F.unwrap(
        StreamingIndicator.restore(snapshot, configuration=cfg, kernel=ReferenceKernel(), world=World.REPLAY, current_scope=F.scope())
    )
    for i, v in enumerate(values[3:]):
        F.unwrap(restored.update({"close": F.observation(v, PresenceState.PRESENT, 1_003 + i)}))
    restored_result = F.unwrap(restored.result())
    cold_result = _stream(cfg, values)
    for channel, cold in cold_result.outputs.items():
        assert F.unwrap(series_equal_within_ulps(cold, restored_result.outputs[channel], 0)) is True


def test_a22_warm_up_below_reference_lookback_is_refused() -> None:
    """A wrapper warm-up below the reference lookback is refused before compute would."""
    refusal = configure_wrapper(
        formula_id="sma", period=F.period(5),
        inputs=[F.series_input("close")], calendar_requirements=[F.calendar()],
        arithmetic_reference_configuration=reference_status().value,
        warm_up=1,  # sma period 5 ⇒ lookback 4
    )
    assert is_refusal(refusal)
    assert refusal.context["field"] == "warm_up"


# --- T7-A23 [R31] P1 — executable tests + reference examples ----------------


def test_a23_wrapper_ships_tests_and_reference_usage_examples() -> None:
    """Each wrapper ships executable tests and reference-usage examples as tier-1 artifacts.
    Counter-case: the example/test artifacts absent from the distribution."""
    import inspect

    import qmf.indicators as pkg

    # getfile → .../qmf-indicators/src/qmf/indicators/__init__.py; the package root
    # (holding src/, examples/, tests/) is four directories up.
    pkg_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(inspect.getfile(pkg))))
    )
    examples = os.path.join(pkg_root, "examples")
    tests = os.path.join(pkg_root, "tests")
    assert os.path.isfile(os.path.join(examples, "configured_wrapper_set_usage.py"))
    assert os.path.isfile(os.path.join(tests, "test_wrappers.py"))


# --- T7-A24 [R32] P0 — the upgrade gate mints, never silently accepts -------


def test_a24_output_changing_upgrade_mints_a_format_version_with_evidence() -> None:
    """An upgrade that changes output for identical canonical inputs is caught and mints the
    per-configured-indicator format version (previous+1) with before/after evidence — never a
    silent accept, never a protocol-wide bump. Counter-case: a silent accept (mint None)."""
    cfg = F.config(warm_up=2)
    series = F.input_series([100, 102, 101, 103, 105, 104, 106])
    before = F.unwrap(compute_batch(cfg, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY))
    # A "candidate reference" that yields DIFFERENT output over the SAME config/inputs:
    after = F.unwrap(compute_batch(cfg, {"close": series}, kernel=F.EchoKernel(lookback=2, bias=1), world=World.REPLAY))
    report = F.unwrap(compare_reference_outputs(cfg, before, after))
    assert report.verdict.value == "changed"
    assert report.mint is not None, "a changed output was silently accepted (no mint)"
    assert report.mint.minted_format_version == cfg.contract_format_version + 1
    assert report.mint.before_evidence and report.mint.after_evidence
    # The CT-16 protocol format version is NOT bumped by a per-indicator arithmetic upgrade:
    assert report.protocol_format_version == 1


def test_a24_identical_output_is_not_a_change_and_mints_nothing() -> None:
    """The unchanged arm: identical output over identical inputs is not a change — no mint
    (proves the CHANGED arm above is not vacuous)."""
    cfg = F.config(warm_up=2)
    series = F.input_series([100, 102, 101, 103, 105, 104, 106])
    before = F.unwrap(compute_batch(cfg, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY))
    after = F.unwrap(compute_batch(cfg, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY))
    report = F.unwrap(compare_reference_outputs(cfg, before, after))
    assert report.verdict.value == "unchanged"
    assert report.mint is None
