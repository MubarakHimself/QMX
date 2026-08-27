"""Epic 23 — regression pins for the three confirmed advisory findings (each EXPECTED to FAIL).

Each pin asserts the CORRECT required behaviour; the FAILURE against current source IS the
evidence, never a licence to soften the assertion. Source is read-only; a failing test is a
FINDING recorded in findings.csv, never fixed by editing source.

* T23-PIN-01 / R-006 / F-23-01 — the ``qmb data generate`` capability is CLI-only, absent from
  the Python API door (B-1 door-parity break). Jointly owned with Epic 16's derived-parity test.
* T23-PIN-02 / R-007 / F-23-02 — a history-seeded generator trusts/reuses the cited source
  dataset's declared scale instead of converting to the target instrument's tick via the named
  AD-7/AD-22 boundary, and does not refuse a scale-incompatible source (DEC-0105: never a silent
  rescale).
* T23-PIN-03 / R-008 / F-23-03 — the B-7 replay-clock-vs-provenance guard fires at the top-level
  config root but is EVADED when the replay-clock-on-synthetic binding is nested in a composed
  config (highest severity: a re-opened synthetic-on-money-path backdoor).
"""

from __future__ import annotations

from conftest import (
    BASE_NS,
    DAY_NS,
    assert_ct04_refusal,
    gbm_resources,
    is_ok,
    is_refusal,
    unwrap,
)

import qmb.data as qdata
from qmf.core.refusal import RefusalCategory
from qmb.data import generate, resolve_generator_config


# --- T23-PIN-01 (R-006, F-23-01): API-door parity gap -------------------------


def test_t23_pin_01_generate_capability_present_in_both_cli_and_api_doors() -> None:
    """B-1 door parity: the ``generate`` library capability must be reachable from BOTH the CLI door
    and the Python API door. Each door's surface is enumerated programmatically (identity against the
    library function), never a hand-list.

    CROSS-REFERENCE (OR-09): this pin covers the SAME defect as Epic 16's T-16.5-gap
    (QMX-F016/QMX-F017) — one defect, counted once; the Epic 16 suite owns the fix.
    Counter-case that would make this FAIL: the Python API door dropping the ``generate``
    re-export, or the CLI tree no longer adapting the library function.
    """
    lib_generate = qdata.generate

    # CLI door surface (derived): SOME public attribute of the CLI tree module is
    # identity-equal to the library function (never a hard-coded adapter attribute
    # name, which would fail on an unrelated rename), and the command is listed.
    from qmb.doors.cli import tree

    cli_reaches_generate = any(
        getattr(tree, name, None) is lib_generate for name in dir(tree) if not name.startswith("_")
    ) and "generate" in qdata.DATA_COMMANDS

    # API door surface (derived): a public attribute of the API door identity-equal to the fn.
    from qmb.doors import api

    api_reaches_generate = any(
        getattr(api, name, None) is lib_generate for name in dir(api) if not name.startswith("_")
    )

    assert cli_reaches_generate, "the generate capability must be reachable from the CLI door"
    # B-1: the same capability must be reachable identically from the API door.
    assert api_reaches_generate, (
        "B-1 door-parity break (F-23-01): the qmb data generate synthetic capability is reachable "
        "from the CLI door but absent from the Python API door surface"
    )


# --- T23-PIN-02 (R-007, F-23-02): source-scale trust --------------------------


def test_t23_pin_02_source_scale_is_converted_or_refused_never_silently_reused() -> None:
    """A history-seeded generator whose cited source dataset declares a scale DIFFERENT from the
    target instrument's tick scale must EITHER quantize to the target tick via the named AD-7/AD-22
    conversion OR RETURN a typed ``invalid input`` — never silently reuse the source scale (DEC-0105).

    EXPECTED TO FAIL against current source: a source declared at scale 3 is fed to a target at
    scale 5; the generator reuses the source integers verbatim at the target scale (a 100x
    mis-scaling) with no conversion and no refusal. The FAILURE records F-23-02.
    Counter-case that would make this PASS: the prices are target-scale-converted (~100x the source
    magnitude), or a scale-incompatible source is refused.
    """
    # source declared at scale 3 (e.g. 1200 == 1.200); target config scale 5 (that price == 120000).
    src_scale3 = []
    for i in range(10):
        o = 1200 + i
        c = o + 1
        src_scale3.append(
            {
                "instant_ns": BASE_NS + i * DAY_NS,
                "open": o,
                "high": max(o, c) + 2,
                "low": min(o, c) - 2,
                "close": c,
                "scale": 3,
            }
        )
    res = {
        "process": "block-bootstrap",
        "venue": "SIM",
        "symbol": "EURUSD",
        "scale": 5,
        "tick_size": 1,
        "resolution": "1d",
        "bar_step_ns": DAY_NS,
        "start_ns": BASE_NS,
        "end_ns": BASE_NS + 5 * DAY_NS,
        "calendar_rule_set": "always-open",
        "source_dataset_id": "SIM:EURUSD:1d:mid",
        "seed": 7,
        "scenario_count": 1,
        "claim_class": "infra-stress",
        "process_params": {"block_length": 3},
    }
    result = generate(res, source_series=src_scale3)
    if is_refusal(result):
        # option (b): a scale-incompatible source is refused as invalid input — acceptable.
        assert_ct04_refusal(
            result, RefusalCategory.INVALID_INPUT, what="scale-incompatible source dataset"
        )
        return
    receipt = result.value
    closes = [bar.close for bar in receipt.bars]
    # option (a), TIGHTENED lock (the original >10x magnitude proxy would also pass a
    # wrong-by-2x conversion): the AD-22 conversion factor is EXACTLY 10^(target-source)
    # = 10^(5-3) = 100, recorded on the receipt as a derived value (lineage), every
    # produced price is an exact integer multiple of it, and the closes sit inside the
    # converted source's magnitude window.
    factor = 10 ** (5 - 3)
    recorded = getattr(receipt, "source_scale_factor", None)
    assert recorded == factor, (
        "F-23-02: the AD-22 source-scale conversion factor (10^(target-source) = 100) must be "
        f"recorded on the receipt as a derived value (lineage); got {recorded!r}"
    )
    assert all(close % factor == 0 for close in closes), (
        f"F-23-02: a converted close must be an exact integer multiple of the AD-22 factor "
        f"{factor}; got {closes}"
    )
    window_lo = (min(row["low"] for row in src_scale3) - 20) * factor
    window_hi = (max(row["high"] for row in src_scale3) + 20) * factor
    assert all(window_lo <= close <= window_hi for close in closes), (
        "F-23-02: converted closes must sit in the converted source's magnitude window "
        f"[{window_lo}, {window_hi}]; got {closes} (a silent reuse or a wrong-factor "
        "conversion falls outside it; DEC-0105: never a silent rescale)"
    )
    assert all(bar.scale == 5 for bar in receipt.bars), "output bars carry the target scale"


# --- T23-PIN-03 (R-008, F-23-03): nested-config replay-clock bypass -----------


def test_t23_pin_03_nested_replay_clock_on_synthetic_returns_invalid_input() -> None:
    """A composed/nested config that binds a replay clock (or a non-simulated world) to the
    synthetic generator config must RETURN a typed ``invalid input`` — identical to the top-level
    case (B-7 wins over B-2; the guard must check every nested binding, not just the root).

    EXPECTED TO FAIL against current source: with the generator config nested under
    ``generator_config`` and the ``clock=replay`` (or ``world=live``) declared at the outer composed
    level, the merge drops the outer directive, so the guard never sees it and the config resolves
    instead of refusing — a re-opened synthetic-on-money-path backdoor. The FAILURE records F-23-03.
    Counter-case that would make this PASS: the nested case refuses exactly like the flat case.
    """
    inner = gbm_resources()

    # discriminator (proves the guard exists at the root and the test discriminates): the FLAT
    # replay clock IS refused.
    flat = dict(inner)
    flat["clock"] = "replay"
    assert_ct04_refusal(
        resolve_generator_config(flat),
        RefusalCategory.INVALID_INPUT,
        what="flat replay clock (top-level guard)",
    )

    # the nested/composed case must refuse identically — but currently it is silently accepted.
    nested_clock = {"generator_config": inner, "clock": "replay"}
    assert_ct04_refusal(
        resolve_generator_config(nested_clock),
        RefusalCategory.INVALID_INPUT,
        what="nested replay clock on synthetic (F-23-03 bypass)",
    )

    nested_world = {"generator_config": inner, "world": "live"}
    assert_ct04_refusal(
        resolve_generator_config(nested_world),
        RefusalCategory.INVALID_INPUT,
        what="nested world=live on synthetic (F-23-03 bypass)",
    )
