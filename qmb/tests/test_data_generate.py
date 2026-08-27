"""Tier-1 tests for ``qmb data generate`` config-selected adapters (Story 23.1).

Covers the story acceptance criteria: the four-process v1 menu and the resolved,
schema-validated, fingerprinted config artifact recorded alongside its run (AC1);
history-seeded source-dataset citation versus from-scratch gbm (AC2); exact
scaled-integer tick-quantized money on a market-hours-aware int64 UTC-ns grid with
float statistics re-entering only through the named AD-7 conversion (AC3); the
OHLC integrity gate that refuses, never corrects (AC4); and the typed refusal
surface for an unknown process and a process x instrument mismatch (AC5).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar, cast

from click.testing import CliRunner
from qmb.data import (
    CLAIM_CLASSES,
    DEFAULT_GENERATOR_PROCESS,
    GENERATOR_PROCESSES,
    SOURCE_DATASET_NONE,
    SYNTHETIC_ORIGIN,
    GenerateReceipt,
    ResolvedGeneratorConfig,
    SourceDatasetRef,
    SyntheticBar,
    data_front_identity,
    generate,
    generate_identity,
    has_generator_config,
    resolve_generator_config,
)
from qmb.data.gap_check import AlwaysOpenCalendar, MarketHoursCalendar
from qmb.doors.cli import main
from qmb.doors.cli.tree import invoke_data
from qmf.calendar_forex import get_provider
from qmf.core import RefusalCategory, Result, World, is_ok, is_refusal
from qmf.core.chrono import CalendarIdentity, Instant
from qmf.core.fingerprint import fingerprint

T = TypeVar("T")

_STEP = 60_000_000_000  # 1-minute bars
_START = 0
_END = 600_000_000_000  # ten 1-minute slots


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _always_open() -> MarketHoursCalendar:
    identity = _ok(CalendarIdentity.try_create("always-open", "v1", "none"))
    return cast("MarketHoursCalendar", AlwaysOpenCalendar(identity=identity))


def _source_bars(count: int = 40, *, scale: int = 5) -> tuple[dict[str, object], ...]:
    """A gently-trending, strictly-positive source series."""
    bars: list[dict[str, object]] = []
    price = 110_000
    for index in range(count):
        close = price + (60 if index % 3 else -40)
        bars.append(
            {
                "instant_ns": index * _STEP,
                "open": price,
                "high": max(price, close) + 30,
                "low": min(price, close) - 30,
                "close": close,
                "scale": scale,
            }
        )
        price = close
    return tuple(bars)


def _gbm_resources(**extra: object) -> dict[str, object]:
    body: dict[str, object] = {
        "process": "gbm",
        "venue": "dukascopy-fx",
        "symbol": "EURUSD",
        "scale": 5,
        "tick_size": 1,
        "resolution": "M1",
        "bar_step_ns": _STEP,
        "start_ns": _START,
        "end_ns": _END,
        "seed_price": 110_000,
        "volatility": "0.001",
        "seed": 7,
    }
    body.update(extra)
    return body


def _history_resources(process: str, **extra: object) -> dict[str, object]:
    body: dict[str, object] = {
        "process": process,
        "venue": "dukascopy-fx",
        "symbol": "EURUSD",
        "scale": 5,
        "tick_size": 1,
        "resolution": "M1",
        "bar_step_ns": _STEP,
        "start_ns": _START,
        "end_ns": _END,
        "seed": 11,
        "source_dataset": {
            "venue": "dukascopy-fx",
            "symbol": "EURUSD",
            "resolution": "M1",
            "side": "bid",
        },
    }
    body.update(extra)
    return body


def _valid_bar(bar: SyntheticBar) -> bool:
    return (
        bar.low <= min(bar.open, bar.close) and max(bar.open, bar.close) <= bar.high and bar.low > 0
    )


# --- AC1: the four-process menu and the fingerprinted config artifact ---------


def test_process_menu_is_exactly_four() -> None:
    assert GENERATOR_PROCESSES == (
        "block-bootstrap",
        "gaussian-resample",
        "gaussian-noise",
        "gbm",
    )
    assert DEFAULT_GENERATOR_PROCESS == "block-bootstrap"


def test_resolved_config_is_schema_validated_and_fingerprinted() -> None:
    config = _ok(resolve_generator_config(_gbm_resources()))
    assert isinstance(config, ResolvedGeneratorConfig)
    assert config.process == "gbm"
    run_id = _ok(config.fingerprint())
    assert run_id.value.startswith("fp1:sha256:")
    # The identity content is canonical (fingerprintable) and carries no float.
    assert is_ok(fingerprint(config.fp1_identity()))
    assert config.artifact_relative_path(run_id).endswith("/generator-config.json")


def test_generate_records_config_artifact_alongside_its_run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        receipt = _ok(generate(_gbm_resources(destination=tmp), calendar=_always_open()))
        assert isinstance(receipt, GenerateReceipt)
        assert receipt.world == World.SIMULATED.value
        assert receipt.origin == SYNTHETIC_ORIGIN
        assert receipt.config_fingerprint.startswith("fp1:sha256:")
        assert receipt.config_artifact_written is True
        written = Path(tmp) / receipt.config_artifact_path
        assert written.is_file()
        assert receipt.config_fingerprint.replace(":", "-") in receipt.config_artifact_path


def test_generate_without_a_root_still_reports_the_fingerprinted_artifact() -> None:
    receipt = _ok(generate(_gbm_resources(), calendar=_always_open()))
    assert receipt.config_artifact_written is False
    assert receipt.config_fingerprint.startswith("fp1:sha256:")
    assert receipt.config_artifact_path.endswith("/generator-config.json")


# --- AC2: history-seeded citation vs from-scratch gbm -------------------------


def test_gbm_is_from_scratch_and_records_source_none() -> None:
    receipt = _ok(generate(_gbm_resources(), calendar=_always_open()))
    assert receipt.process == "gbm"
    assert receipt.source_dataset_id == SOURCE_DATASET_NONE


def test_history_seeded_processes_cite_a_source_dataset() -> None:
    for process in ("block-bootstrap", "gaussian-resample", "gaussian-noise"):
        extra: dict[str, object] = {"source_series": _source_bars()}
        if process == "block-bootstrap":
            extra["block_length"] = 5
        if process == "gaussian-noise":
            extra["sigma"] = "0.00005"
        receipt = _ok(generate(_history_resources(process, **extra), calendar=_always_open()))
        assert receipt.source_dataset_id == "dukascopy-fx:EURUSD:M1:bid"
        assert all(_valid_bar(bar) for bar in receipt.bars)


def test_history_seeded_without_citation_is_invalid_input() -> None:
    body = _history_resources("block-bootstrap", block_length=5)
    del body["source_dataset"]
    refusal = resolve_generator_config(body)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "source_dataset"


def test_history_seeded_missing_source_series_is_unavailable_dependency() -> None:
    refusal = generate(
        _history_resources("block-bootstrap", block_length=5), calendar=_always_open()
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_gbm_cannot_cite_a_source_dataset() -> None:
    refusal = resolve_generator_config(
        _gbm_resources(
            source_dataset={"venue": "v", "symbol": "s", "resolution": "M1", "side": "bid"}
        )
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


# --- AC3: exact tick-quantized money on a market-hours int64 UTC-ns grid ------


def test_prices_are_scaled_integers_quantized_to_tick() -> None:
    receipt = _ok(generate(_gbm_resources(tick_size=5), calendar=_always_open()))
    for bar in receipt.bars:
        for price in (bar.open, bar.high, bar.low, bar.close):
            assert isinstance(price, int)
            assert price % 5 == 0


def test_timestamps_are_int64_ns_on_a_market_hours_grid() -> None:
    # Real forex-17NY calendar: a multi-day window; every emitted bar must fall in
    # an open session (weekend gap and session boundaries respected).
    calendar = cast("MarketHoursCalendar", _ok(get_provider()))
    start = 1_787_140_800_000_000_000  # 2026-08-19 12:00 UTC (open, Wednesday)
    end = start + (4 * 24 * 3_600_000_000_000)  # four days, crossing the weekend gap
    receipt = _ok(
        generate(
            _gbm_resources(
                start_ns=start,
                end_ns=end,
                bar_step_ns=3_600_000_000_000,  # 1-hour bars
                resolution="H1",
            ),
            calendar=calendar,
        )
    )
    assert receipt.bars
    for bar in receipt.bars:
        instant = _ok(Instant.try_create(bar.instant_ns))
        window = calendar.session_window(instant)
        assert is_ok(window), bar.instant_ns
        assert window.value is not None, bar.instant_ns


def test_all_four_processes_emit_valid_positive_ohlc() -> None:
    for process in GENERATOR_PROCESSES:
        if process == "gbm":
            body = _gbm_resources()
            calendar = _always_open()
            receipt = _ok(generate(body, calendar=calendar))
        else:
            extra: dict[str, object] = {"source_series": _source_bars()}
            if process == "block-bootstrap":
                extra["block_length"] = 5
            if process == "gaussian-noise":
                extra["sigma"] = "0.00005"
            receipt = _ok(generate(_history_resources(process, **extra), calendar=_always_open()))
        assert receipt.bar_count == 10
        assert all(_valid_bar(bar) for bar in receipt.bars)


# --- AC4: the OHLC integrity gate refuses, never corrects ---------------------


def test_bar_gate_refuses_high_below_body() -> None:
    refusal = SyntheticBar.try_create(0, 100, 90, 95, 100, 5)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "high"


def test_bar_gate_refuses_low_above_body() -> None:
    refusal = SyntheticBar.try_create(0, 100, 120, 105, 110, 5)
    assert is_refusal(refusal)
    assert refusal.context["field"] == "low"


def test_bar_gate_refuses_non_positive_price() -> None:
    refusal = SyntheticBar.try_create(0, 100, 110, 0, 105, 5)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "low"


def test_bar_gate_accepts_a_valid_bar() -> None:
    bar = _ok(SyntheticBar.try_create(0, 100, 110, 95, 105, 5))
    assert bar.high == 110
    assert bar.low == 95


# --- AC5: the typed refusal surface ------------------------------------------


def test_unknown_process_is_unsupported_capability() -> None:
    refusal = resolve_generator_config(_gbm_resources(process="brownian-bridge"))
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refusal.context["field"] == "process"


def test_deferred_regime_process_is_unsupported_capability() -> None:
    refusal = resolve_generator_config(_gbm_resources(process="regime-switching"))
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_corporate_action_on_forex_is_category_appropriate_refusal() -> None:
    refusal = resolve_generator_config(_gbm_resources(events=["corporate-action"]))
    assert is_refusal(refusal)
    # A process x instrument mismatch is invalid input — distinct from the unknown
    # process 'unsupported capability' category.
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "events"


def test_missing_required_process_variable_refuses() -> None:
    body = _gbm_resources()
    del body["volatility"]
    refusal = resolve_generator_config(body)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


# --- epic invariants: world derivation and claim-class labeling ---------------


def test_replay_clock_on_synthetic_is_invalid_input() -> None:
    refusal = resolve_generator_config(_gbm_resources(clock="replay"))
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "clock"


def test_caller_declared_non_simulated_world_is_invalid_input() -> None:
    refusal = resolve_generator_config(_gbm_resources(world="replay"))
    assert is_refusal(refusal)
    assert refusal.context["field"] == "world"


def test_robustness_claim_requires_a_history_seeded_process() -> None:
    refusal = resolve_generator_config(_gbm_resources(claim_class="robustness"))
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "claim_class"


def test_claim_class_defaults_to_infra_stress() -> None:
    config = _ok(resolve_generator_config(_gbm_resources()))
    assert config.claim_class == "infra-stress"
    assert set(CLAIM_CLASSES) == {"infra-stress", "robustness", "logic-smoke"}


# --- determinism (R5 foundation) ---------------------------------------------


def test_same_seed_reproduces_the_series_bit_for_bit() -> None:
    first = _ok(generate(_gbm_resources(), calendar=_always_open()))
    second = _ok(generate(_gbm_resources(), calendar=_always_open()))
    assert first.config_fingerprint == second.config_fingerprint
    assert tuple(b.as_mapping() for b in first.bars) == tuple(b.as_mapping() for b in second.bars)


def test_different_seed_changes_the_series_but_not_the_grid() -> None:
    first = _ok(generate(_gbm_resources(seed=1), calendar=_always_open()))
    second = _ok(generate(_gbm_resources(seed=2), calendar=_always_open()))
    assert first.config_fingerprint != second.config_fingerprint
    assert [b.instant_ns for b in first.bars] == [b.instant_ns for b in second.bars]
    assert [b.close for b in first.bars] != [b.close for b in second.bars]


# --- identity and the door surface -------------------------------------------


def test_generate_identity_excludes_semver_and_is_fingerprintable() -> None:
    import qmb

    identity = generate_identity()
    assert qmb.__version__ not in identity.values()
    assert is_ok(fingerprint(identity))
    assert is_ok(fingerprint(data_front_identity()))


def test_has_generator_config_detects_a_resolved_config() -> None:
    assert has_generator_config(_gbm_resources()) is True
    assert has_generator_config({"destination": "synth"}) is False
    assert has_generator_config("not-a-mapping") is False


def test_cli_generate_destination_only_reports_the_front() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["data", "generate", "--destination", "synth"])
    assert result.exit_code == 0, result.output


def test_cli_generate_bare_refuses_missing_destination() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["data", "generate"])
    assert result.exit_code != 0


def test_cli_generate_with_injected_config_runs_the_adapter() -> None:
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        obj = _gbm_resources(calendar=_always_open())
        obj["destination"] = tmp
        result = runner.invoke(main, ["data", "generate", "--destination", tmp], obj=obj)
        assert result.exit_code == 0, result.output


def test_invoke_data_generate_yields_a_simulated_receipt() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        resources = _gbm_resources(calendar=_always_open(), destination=tmp)
        payload = _ok(invoke_data("generate", resources))
        assert payload["world"] == World.SIMULATED.value
        assert payload["origin"] == SYNTHETIC_ORIGIN
        assert payload["process"] == "gbm"
        assert payload["bar_count"] == 10


# --- rounding modes, string citations, and dataclass surfaces ----------------


def test_every_declared_rounding_mode_quantizes_to_tick() -> None:
    for mode in ("half-up", "half-even", "floor", "ceiling", "up", "down"):
        receipt = _ok(
            generate(
                _gbm_resources(tick_size=10, rounding_mode=mode),
                calendar=_always_open(),
            )
        )
        for bar in receipt.bars:
            assert bar.open % 10 == 0
            assert bar.high % 10 == 0
            assert bar.low % 10 == 0
            assert bar.close % 10 == 0
            assert _valid_bar(bar)


def test_invalid_rounding_mode_refuses() -> None:
    refusal = resolve_generator_config(_gbm_resources(rounding_mode="banker"))
    assert is_refusal(refusal)
    assert refusal.context["field"] == "rounding_mode"


def test_source_dataset_as_string_id_resolves() -> None:
    config = _ok(
        resolve_generator_config(
            _history_resources("block-bootstrap", block_length=5, source_dataset="v:s:M1:bid")
        )
    )
    assert config.source_dataset_id == "v:s:M1:bid"


def test_source_dataset_id_key_resolves() -> None:
    body = _history_resources("block-bootstrap", block_length=5)
    del body["source_dataset"]
    body["source_dataset_id"] = "v:s:M1:ask"
    config = _ok(resolve_generator_config(body))
    assert config.source_dataset_id == "v:s:M1:ask"


def test_gbm_may_state_source_dataset_none_string() -> None:
    config = _ok(resolve_generator_config(_gbm_resources(source_dataset="none")))
    assert config.source_dataset_id == SOURCE_DATASET_NONE


def test_malformed_source_dataset_string_refuses() -> None:
    refusal = resolve_generator_config(
        _history_resources("block-bootstrap", block_length=5, source_dataset="only:three:parts")
    )
    assert is_refusal(refusal)
    assert refusal.context["field"] == "source_dataset"


def test_source_dataset_ref_surface() -> None:
    ref = SourceDatasetRef("dukascopy-fx", "EURUSD", "M1", "bid")
    assert ref.dataset_id == "dukascopy-fx:EURUSD:M1:bid"
    assert is_ok(fingerprint(ref.fp1_identity()))


def test_resolved_config_as_mapping_matches_identity() -> None:
    config = _ok(resolve_generator_config(_gbm_resources()))
    assert config.as_mapping() == config.fp1_identity()
    assert config.as_mapping()["world"] == World.SIMULATED.value


def test_synthetic_bar_surface() -> None:
    bar = _ok(SyntheticBar.try_create(5, 100, 110, 95, 105, 5))
    assert bar.as_mapping()["close"] == 105
    assert is_ok(fingerprint(bar.fp1_identity()))


# --- malformed inputs and degenerate processes -------------------------------


def test_bad_window_refuses() -> None:
    refusal = resolve_generator_config(_gbm_resources(end_ns=0, start_ns=10))
    assert is_refusal(refusal)
    assert refusal.context["field"] == "window"


def test_non_mapping_resources_refuses() -> None:
    assert is_refusal(resolve_generator_config("not-a-mapping"))


def test_missing_instrument_parts_refuse() -> None:
    body = _gbm_resources()
    del body["venue"]
    assert resolve_generator_config(body).context["field"] == "venue"
    body = _gbm_resources()
    del body["symbol"]
    assert resolve_generator_config(body).context["field"] == "symbol"


def test_non_integer_scale_refuses() -> None:
    refusal = resolve_generator_config(_gbm_resources(scale="five"))
    assert is_refusal(refusal)
    assert refusal.context["field"] == "scale"


def test_empty_market_hours_grid_refuses() -> None:
    # A window entirely inside the forex-17NY weekend gap yields no open bar.
    calendar = cast("MarketHoursCalendar", _ok(get_provider()))
    weekend_start = 1_787_346_000_000_000_000  # Friday 17:00 NY -> Saturday trading date
    refusal = generate(
        _gbm_resources(
            start_ns=weekend_start,
            end_ns=weekend_start + (10 * _STEP),
            bar_step_ns=_STEP,
        ),
        calendar=calendar,
    )
    assert is_refusal(refusal)
    assert refusal.context["field"] == "window"


def test_source_bar_with_broken_ohlc_refuses() -> None:
    bad = list(_source_bars())
    broken = dict(bad[3])
    broken["high"] = 1  # high below the body
    bad[3] = broken
    refusal = generate(
        _history_resources("block-bootstrap", block_length=5, source_series=tuple(bad)),
        calendar=_always_open(),
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


def test_gaussian_noise_source_shorter_than_grid_refuses() -> None:
    refusal = generate(
        _history_resources("gaussian-noise", sigma="0.00005", source_series=_source_bars(count=3)),
        calendar=_always_open(),
    )
    assert is_refusal(refusal)
    assert refusal.context["field"] == "source_series"


def test_gbm_non_positive_volatility_refuses() -> None:
    refusal = resolve_generator_config(_gbm_resources(volatility="0"))
    assert is_refusal(refusal)
    assert refusal.context["field"] == "volatility"


def test_block_length_out_of_range_refuses() -> None:
    refusal = generate(
        _history_resources("block-bootstrap", block_length=99, source_series=_source_bars()),
        calendar=_always_open(),
    )
    assert is_refusal(refusal)
    assert refusal.context["field"] == "block_length"


def test_gbm_divergent_volatility_is_invalid_input() -> None:
    refusal = generate(_gbm_resources(volatility="100000"), calendar=_always_open())
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT


def test_nested_generator_config_is_merged() -> None:
    body: dict[str, object] = {
        "generator_config": _gbm_resources(),
        "calendar": _always_open(),
    }
    receipt = _ok(generate(body))
    assert receipt.process == "gbm"


def test_source_series_accepts_synthetic_bar_instances() -> None:
    bars = tuple(
        _ok(
            SyntheticBar.try_create(
                row["instant_ns"], row["open"], row["high"], row["low"], row["close"], row["scale"]
            )
        )
        for row in _source_bars()
    )
    receipt = _ok(
        generate(
            _history_resources("block-bootstrap", block_length=5, source_series=bars),
            calendar=_always_open(),
        )
    )
    assert receipt.bar_count == 10


def test_logic_smoke_claim_allowed_for_gbm() -> None:
    config = _ok(resolve_generator_config(_gbm_resources(claim_class="logic-smoke")))
    assert config.claim_class == "logic-smoke"


# --- internal calendar resolution (no injected calendar) ---------------------


def test_always_open_rule_set_builds_its_own_calendar() -> None:
    receipt = _ok(generate(_gbm_resources(calendar_rule_set="always-open")))
    assert receipt.bar_count == 10


def test_forex_rule_set_loads_the_extension_provider() -> None:
    start = 1_787_140_800_000_000_000  # 2026-08-19 12:00 UTC (open)
    receipt = _ok(
        generate(
            _gbm_resources(
                calendar_rule_set="forex-17NY",
                start_ns=start,
                end_ns=start + (5 * _STEP),
            )
        )
    )
    assert receipt.bar_count >= 1


# --- more malformed-input branches -------------------------------------------


def test_events_must_be_a_list() -> None:
    refusal = resolve_generator_config(_gbm_resources(events="corporate-action"))
    assert is_refusal(refusal)
    assert refusal.context["field"] == "events"


def test_source_series_must_be_a_sequence() -> None:
    refusal = generate(
        _history_resources("block-bootstrap", block_length=5, source_series=123),
        calendar=_always_open(),
    )
    assert is_refusal(refusal)
    assert refusal.context["field"] == "source_series"


def test_source_bar_item_must_be_a_mapping_or_bar() -> None:
    refusal = generate(
        _history_resources("block-bootstrap", block_length=5, source_series=(1, 2, 3)),
        calendar=_always_open(),
    )
    assert is_refusal(refusal)
    assert refusal.context["field"] == "source_series"


def test_process_params_may_be_an_explicit_mapping() -> None:
    body = _gbm_resources()
    del body["volatility"]
    del body["seed_price"]
    body["process_params"] = {"seed_price": 110_000, "volatility": "0.001", "drift": "0.0001"}
    config = _ok(resolve_generator_config(body))
    assert config.process_params["drift"] == "0.0001"


def test_iso_timestamp_and_negative_seed_are_rejected_appropriately() -> None:
    # start as an int string is accepted; a non-numeric start is invalid.
    ok = _ok(resolve_generator_config(_gbm_resources(start_ns="0", end_ns="600000000000")))
    assert ok.start_ns == 0
    bad = resolve_generator_config(_gbm_resources(start_ns="not-a-number"))
    assert is_refusal(bad)
    assert bad.context["field"] == "start_ns"
