"""Reference usage — Story 7.5: the conformance harness, the light/heavy benchmark budgets,
and the one named catalog surface (COMP-QMF-INDICATORS; CT-16; DEC-0126, DEC-0128, DEC-0111,
DEC-0133).

Executable::

    python packages/qmf-indicators/examples/conformance_and_catalog_usage.py

Shows the four things Story 7.5 pins down:

1. The CT-16 conformance register keeps its concept-walk list expressible: a governed
   configuration expresses each concept and :func:`run_conformance` proves coverage.
2. The benchmark harness measures two rungs (burst throughput, per-tick latency) with the
   no-op tick path separate, and :func:`regression_gate` fails the tier-2 gate on a latency,
   throughput, or peak-memory regression alike.
3. Light versus heavy is per configuration: a configuration is heavy by default and its
   synchronous entry point returns ``unsupported capability``; a benchmark-proven light claim
   is light.
4. Extensions register explicitly through the one named catalog surface, carrying their
   distribution identity and version in every artifact; a plain-Python experiment graduates
   into governed evidence only with a lineage edge back to its research artifact.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    ExactRational,
    Instrument,
    Result,
    UnitKind,
    VenueId,
    is_ok,
    is_refusal,
)
from qmf.indicators import (
    EXTENSION_DISTRIBUTION_FIELD,
    AlignmentPolicy,
    ArithmeticReference,
    BenchmarkBaseline,
    BenchmarkMeasurement,
    BenchmarkRung,
    Catalog,
    ChannelKind,
    ConceptExpression,
    ConceptWalk,
    ConfiguredIndicator,
    DeclaredBudget,
    LightHeavyVerdict,
    MissingValuePolicy,
    NoOpTickMeasurement,
    OutputArity,
    OutputChannel,
    QuoteSide,
    RungMeasurement,
    SeriesInput,
    SupportedMode,
    evaluate_light_claim,
    graduate,
    guard_synchronous_entry,
    regression_gate,
    require_extension_identity,
    run_conformance,
    stamp_extension_identity,
)

T = TypeVar("T")


def _unwrap(result: Result[T]) -> T:
    assert is_ok(result), f"expected Ok, got {result}"
    return result.value


def _config(**overrides: object) -> ConfiguredIndicator:
    instrument = _unwrap(Instrument.try_create(_unwrap(VenueId.try_create("venue-ic")), "EURUSD"))
    close = _unwrap(
        SeriesInput.try_create(
            name="close",
            source=instrument,
            bar_spec={"kind": "time-interval", "seconds": 60},
            channel_kind=ChannelKind.EXACT_PRICE,
            quote_side=QuoteSide.MID,
        )
    )
    channel = _unwrap(
        OutputChannel.try_create(
            "sma", ChannelKind.FLOAT_ANALYTIC, OutputArity.SCALAR_PER_SAMPLE, 0
        )
    )
    kwargs: dict[str, object] = {
        "formula_id": "sma",
        "contract_format_version": 1,
        "parameters": {"period": _unwrap(ExactRational.try_create(2, 1, UnitKind.COUNT))},
        "inputs": [close],
        "calendar_requirements": [
            _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))
        ],
        "alignment_policy": AlignmentPolicy.AS_OF,
        "missing_value_policy": MissingValuePolicy.MARK_GAP,
        "warm_up": 1,
        "output_schema": [channel],
        "supported_modes": [SupportedMode.BATCH, SupportedMode.STREAMING],
        "arithmetic_reference_configuration": _unwrap(
            ArithmeticReference.try_create(
                "ta-lib-c==0.7.1",
                "ta-lib==0.7.1",
                {"compatibility_mode": "default", "candle_settings": "reference-default"},
            )
        ),
    }
    kwargs.update(overrides)
    return _unwrap(ConfiguredIndicator.try_create(**kwargs))


def _measurement(fingerprint: str, *, latency_ns: int, peak_bytes: int) -> BenchmarkMeasurement:
    return BenchmarkMeasurement(
        configuration_fingerprint=fingerprint,
        burst=RungMeasurement(BenchmarkRung.BURST_THROUGHPUT, 2_000, 1_000_000_000, peak_bytes),
        latency=RungMeasurement(BenchmarkRung.PER_TICK_LATENCY, 10, 10 * latency_ns, peak_bytes),
        noop_tick=NoOpTickMeasurement(100, 100, peak_bytes),
        peak_bytes=peak_bytes,
    )


def main() -> None:
    # 1. Conformance: two concepts expressed and proven.
    multi_instrument = _config(
        inputs=[
            _unwrap(
                SeriesInput.try_create(
                    name="eur",
                    source=_unwrap(
                        Instrument.try_create(_unwrap(VenueId.try_create("venue-ic")), "EURUSD")
                    ),
                    bar_spec={"kind": "time-interval", "seconds": 60},
                    channel_kind=ChannelKind.EXACT_PRICE,
                    quote_side=QuoteSide.MID,
                )
            ),
            _unwrap(
                SeriesInput.try_create(
                    name="gbp",
                    source=_unwrap(
                        Instrument.try_create(_unwrap(VenueId.try_create("venue-ic")), "GBPUSD")
                    ),
                    bar_spec={"kind": "time-interval", "seconds": 60},
                    channel_kind=ChannelKind.EXACT_PRICE,
                    quote_side=QuoteSide.MID,
                )
            ),
        ]
    )
    batch_only = _config(supported_modes=[SupportedMode.BATCH])
    report = _unwrap(
        run_conformance(
            [
                ConceptExpression(ConceptWalk.MULTI_INSTRUMENT, multi_instrument),
                ConceptExpression(ConceptWalk.BATCH_ONLY_STATISTICAL, batch_only),
            ]
        )
    )
    print(f"conformance concepts checked: {len(report.checks)}")
    print(f"conformance all expressible: {all(check.expressible for check in report.checks)}")

    # 2. Benchmark: the gate passes within budget and fails on a peak-memory regression.
    heavy_config = _config()
    fingerprint = _unwrap(heavy_config.fp1()).value
    baseline = _unwrap(
        BenchmarkBaseline.try_create(
            configuration_fingerprint=fingerprint,
            os="windows-11",
            cpu_class="x86-64-avx2",
            burst_throughput_per_second=2_000,
            per_tick_latency_ns=500,
            peak_bytes=1_000,
        )
    )
    within = regression_gate(baseline, _measurement(fingerprint, latency_ns=500, peak_bytes=1_000))
    print(f"benchmark within budget: {is_ok(within)}")
    regressed = regression_gate(
        baseline, _measurement(fingerprint, latency_ns=500, peak_bytes=4_000)
    )
    print(f"peak-memory regression refused: {is_refusal(regressed)}")

    # 3. Budget: heavy by default; the synchronous entry is unsupported; a proven claim is light.
    heavy = _unwrap(evaluate_light_claim(heavy_config))
    print(f"heavy by default: {heavy.verdict is LightHeavyVerdict.HEAVY}")
    heavy_entry = guard_synchronous_entry(heavy)
    assert is_refusal(heavy_entry)
    print(f"heavy synchronous entry: {heavy_entry.context['reason']}")
    light_config = _config(
        declared_budget=_unwrap(
            DeclaredBudget.try_create(
                per_update_cost_rung="live-path",
                bounded_state=True,
                window_or_anchor_rule="bounded-window-200",
                synchronous_availability=True,
            )
        )
    )
    light_fp = _unwrap(light_config.fp1()).value
    light_baseline = _unwrap(
        BenchmarkBaseline.try_create(
            configuration_fingerprint=light_fp,
            os="windows-11",
            cpu_class="x86-64-avx2",
            burst_throughput_per_second=2_000,
            per_tick_latency_ns=500,
            peak_bytes=1_000,
        )
    )
    light = _unwrap(
        evaluate_light_claim(
            light_config,
            baseline=light_baseline,
            measurement=_measurement(light_fp, latency_ns=500, peak_bytes=1_000),
        )
    )
    print(f"proven light claim: {light.verdict is LightHeavyVerdict.LIGHT}")

    # 4. Catalog + graduation: a plain-Python experiment graduates with a lineage edge.
    extension = _unwrap(
        graduate(
            distribution="qmf-ind-ext-zigzag",
            version="1.0.0",
            formula_ids=["research_zigzag"],
            research_artifact="research://experiment-42",
        )
    )
    catalog = _unwrap(Catalog.empty().register(extension))
    resolved = _unwrap(catalog.resolve_formula("research_zigzag"))
    print(f"graduated lineage: {resolved.lineage.research_artifact}")
    artifact = _unwrap(stamp_extension_identity(extension.identity, {"class": "extension-output"}))
    print(f"artifact carries extension distribution: {artifact[EXTENSION_DISTRIBUTION_FIELD]}")
    print(f"artifact identity mandatory-check: {is_ok(require_extension_identity(artifact))}")


if __name__ == "__main__":
    main()
