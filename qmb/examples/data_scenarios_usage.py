"""Reference usage — deterministic multi-scenario generation & the pinned RNG (Story 23.4).

Executable::

    python qmb/examples/data_scenarios_usage.py

Shows the things R5/R3/R7/R8 pin down for multi-scenario synthetic generation:

1. The generator draws every random value through a QMX-owned, version-pinned RNG
   (``qmx-splitmix64-v1``) — never a runtime stdlib ``Random`` (spec section 2A.3) —
   and records its algorithm and version in the artifact provenance.
2. The full artifact is bit-reproducible from ``{process, seed, source-dataset id,
   generator-config fp1}``; re-generation reproduces the artifact fingerprint or
   returns a typed refusal (B-10 reproduce-or-refuse).
3. Each scenario's substream is ``base_seed + scenario_index`` so scenario k
   reproduces in isolation, and each scenario is tagged by its index.
4. For a history-seeded process, scenario 0 is the untouched original real path and
   scenarios >0 are perturbed (the Jesse anchor pattern).
5. A from-scratch ``gbm`` has no scenario-0 anchor and no computable robustness band
   or p-value — the run emits only infra-stress / logic-smoke verdicts.
6. Scenarios fan out process-per-run under the min(cpu, memory) governor with
   enqueue-when-full; scenario failures are counted and reported as typed refusals.
"""

from __future__ import annotations

from typing import TypeVar, cast

from qmb.data import (
    admit_scenario_fanout,
    derive_substream_seed,
    generate,
    generate_scenarios,
    regenerate_scenario,
    reproduce_generation,
)
from qmb.data.gap_check import AlwaysOpenCalendar, MarketHoursCalendar
from qmb.data.rng import RNG_FAMILY, rng_provenance
from qmf.core import RefusalCategory, Result, is_ok, is_refusal
from qmf.core.chrono import CalendarIdentity

T = TypeVar("T")

_STEP = 60_000_000_000  # 1-minute bars


def _ok(result: Result[T]) -> T:
    if not is_ok(result):
        raise AssertionError(result)
    return result.value


def _calendar() -> MarketHoursCalendar:
    identity = _ok(CalendarIdentity.try_create("always-open", "v1", "none"))
    return cast("MarketHoursCalendar", AlwaysOpenCalendar(identity=identity))


def _source_bars() -> tuple[dict[str, object], ...]:
    bars: list[dict[str, object]] = []
    price = 110_000
    for index in range(40):
        close = price + (60 if index % 3 else -40)
        bars.append(
            {
                "instant_ns": index * _STEP,
                "open": price,
                "high": max(price, close) + 30,
                "low": min(price, close) - 30,
                "close": close,
                "scale": 5,
            }
        )
        price = close
    return tuple(bars)


def _base(**extra: object) -> dict[str, object]:
    body: dict[str, object] = {
        "venue": "dukascopy-fx",
        "symbol": "EURUSD",
        "scale": 5,
        "tick_size": 1,
        "resolution": "M1",
        "bar_step_ns": _STEP,
        "start_ns": 0,
        "end_ns": 600_000_000_000,
        "seed": 7,
        "claim_class": "logic-smoke",
    }
    body.update(extra)
    return body


def _gbm(**extra: object) -> dict[str, object]:
    return _base(process="gbm", seed_price=110_000, volatility="0.001", **extra)


def _history(process: str = "block-bootstrap", **extra: object) -> dict[str, object]:
    return _base(
        process=process,
        seed=11,
        block_length=5,
        source_dataset={
            "venue": "dukascopy-fx",
            "symbol": "EURUSD",
            "resolution": "M1",
            "side": "bid",
        },
        **extra,
    )


def main() -> None:
    calendar = _calendar()

    # 1. QMX-owned, version-pinned RNG — never a runtime stdlib Random.
    provenance = rng_provenance()
    assert provenance["is_runtime_stdlib_random"] is False
    print(
        f"RNG is QMX-owned {RNG_FAMILY}, version-pinned; "
        f"is_runtime_stdlib_random={provenance['is_runtime_stdlib_random']}"
    )

    # 2. Reproduce-or-refuse from {process, seed, source-dataset id, config fp1}.
    original = _ok(generate(_gbm(), calendar=calendar))
    reproduced = _ok(
        reproduce_generation(
            _gbm(), expected_artifact_fingerprint=original.artifact_fingerprint, calendar=calendar
        )
    )
    assert reproduced.artifact_fingerprint == original.artifact_fingerprint
    mismatch = reproduce_generation(
        _gbm(seed=999),
        expected_artifact_fingerprint=original.artifact_fingerprint,
        calendar=calendar,
    )
    assert is_refusal(mismatch) and mismatch.context["field"] == "artifact_fingerprint"
    print("reproduce-or-refuse: same inputs reproduce the artifact fingerprint; a mismatch refuses")

    # 3. Per-scenario substreams base_seed + scenario_index, tagged by index, isolated.
    fanout = _ok(generate_scenarios(_gbm(scenario_count=4), calendar=calendar))
    indices = [s.scenario_index for s in fanout.scenarios]
    seeds = [s.seed for s in fanout.scenarios]
    isolated = _ok(regenerate_scenario(_gbm(scenario_count=4), 2, calendar=calendar))
    inside = fanout.scenario_at(2)
    assert inside is not None
    assert isolated.series_fingerprint.value == inside.series_fingerprint.value
    assert seeds == [derive_substream_seed(7, i) for i in indices]
    print(
        f"scenario substreams seed=base+index {seeds}; scenario 2 reproduces in isolation="
        f"{isolated.series_fingerprint.value == inside.series_fingerprint.value}"
    )

    # 4. History-seeded scenario 0 is the untouched original; scenarios >0 perturbed.
    source = _source_bars()
    hist = _ok(
        generate_scenarios(_history(scenario_count=4), calendar=calendar, source_series=source)
    )
    anchor = hist.original_anchor()
    assert anchor is not None and anchor.scenario_index == 0 and anchor.is_original_anchor
    untouched = all(
        (bar.open, bar.high, bar.low, bar.close)
        == (source[i]["open"], source[i]["high"], source[i]["low"], source[i]["close"])
        for i, bar in enumerate(anchor.bars)
    )
    perturbed = hist.scenarios[1].bars != anchor.bars
    print(
        f"history-seeded scenario 0 is the untouched original real path (untouched={untouched}); "
        f"scenarios >0 are perturbed (perturbed={perturbed})"
    )

    # 5. From-scratch gbm has no anchor and no computable robustness band or p-value.
    assert fanout.has_original_anchor is False and fanout.robustness_band_computable is False
    band_refusal = fanout.robustness_band_refusal()
    assert band_refusal is not None and band_refusal.category is RefusalCategory.POLICY_REJECTION
    print(
        "from-scratch gbm has no scenario-0 anchor and no robustness band or p-value; "
        f"the run emits only {list(fanout.permittable_claim_classes)} verdicts"
    )

    # 6. Governed process-per-run fan-out (min(cpu, memory), enqueue-when-full); typed failures.
    governed = _ok(
        generate_scenarios(_gbm(scenario_count=4), calendar=calendar, projected_peak_memory=1000)
    )
    plan = _ok(
        admit_scenario_fanout(
            governed, budgets={"qmb_governor_cpu_budget": 2, "qmb_governor_memory_budget": 2500}
        )
    )
    assert plan.silent_oversubscription is False
    failing = _ok(
        generate_scenarios(
            _history("gaussian-noise", sigma="0.3", scenario_count=16),
            calendar=calendar,
            source_series=source,
        )
    )
    assert failing.produced_count + failing.filtered_count == failing.scenario_count
    print(
        f"governor min(cpu,memory) bound={plan.parallelism_bound}, admitted={len(plan.admitted)}, "
        f"queued={len(plan.queued)}, never silent oversubscription; "
        f"scenario failures counted as typed refusals (filtered_count={failing.filtered_count})"
    )
    print("data scenarios ok")


if __name__ == "__main__":
    main()
