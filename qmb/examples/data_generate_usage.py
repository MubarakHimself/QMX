"""Reference usage — ``qmb data generate`` config-selected adapters (Story 23.1).

Executable::

    python qmb/examples/data_generate_usage.py

Shows the things R1/R2/R6/R8 pin down for synthetic-series generation:

1. The v1 process menu is exactly four config-selected adapters; the library is
   never swapped, only the config's ``process`` variable changes.
2. From-scratch ``gbm`` records source-dataset id ``none``; a history-seeded
   process (``block-bootstrap``) cites a source-dataset id from a qmf-data room.
3. Every price is exact scaled-integer money quantized to the instrument tick;
   every timestamp is int64 UTC-ns on a market-hours-aware grid.
4. Generated data derives ``world = simulated`` and carries a store-level
   ``origin = synthetic`` taint — infra-stress / logic-smoke only, never edge.
5. The resolved config is a schema-validated, fingerprinted artifact recorded
   alongside the run it produced.
6. Refusals are typed: an unknown process is ``unsupported capability``; a
   corporate-action request on a forex instrument is a category-appropriate
   ``invalid input`` mismatch; a replay clock on synthetic data is invalid input.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar, cast

from qmb.data import (
    GENERATOR_PROCESSES,
    SOURCE_DATASET_NONE,
    generate,
    resolve_generator_config,
)
from qmb.data.gap_check import AlwaysOpenCalendar, MarketHoursCalendar
from qmf.core import RefusalCategory, Result, World, is_ok, is_refusal
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
        "tick_size": 5,
        "resolution": "M1",
        "bar_step_ns": _STEP,
        "start_ns": 0,
        "end_ns": 600_000_000_000,
        "seed": 7,
    }
    body.update(extra)
    return body


def main() -> None:
    calendar = _calendar()
    print("processes:", " ".join(GENERATOR_PROCESSES))
    print("the library is never swapped — only config variables change")

    # from-scratch gbm — no source dataset (records 'none')
    with tempfile.TemporaryDirectory() as tmp:
        gbm = _ok(
            generate(
                _base(process="gbm", seed_price=110_000, volatility="0.001", destination=tmp),
                calendar=calendar,
            )
        )
        assert gbm.source_dataset_id == SOURCE_DATASET_NONE
        assert gbm.world == World.SIMULATED.value
        assert gbm.origin == "synthetic"
        assert gbm.config_artifact_written is True
        assert (Path(tmp) / gbm.config_artifact_path).is_file()
        tick_ok = all(
            price % 5 == 0 for bar in gbm.bars for price in (bar.open, bar.high, bar.low, bar.close)
        )
        ohlc_ok = all(
            bar.low <= min(bar.open, bar.close) <= max(bar.open, bar.close) <= bar.high
            and bar.low > 0
            for bar in gbm.bars
        )
        print(
            f"gbm: {gbm.bar_count} bars, source={gbm.source_dataset_id}, "
            f"world={gbm.world}, origin={gbm.origin}"
        )
        print(f"gbm: tick-quantized integer money={tick_ok}; OHLC invariant holds={ohlc_ok}")
        print(f"gbm: config artifact recorded at {gbm.config_artifact_path}")

    # history-seeded block-bootstrap — cites a CT-10 source dataset
    block = _ok(
        generate(
            _base(
                process="block-bootstrap",
                block_length=5,
                claim_class="robustness",
                source_dataset={
                    "venue": "dukascopy-fx",
                    "symbol": "EURUSD",
                    "resolution": "M1",
                    "side": "bid",
                },
                source_series=_source_bars(),
            ),
            calendar=calendar,
        )
    )
    print(
        f"block-bootstrap: cites source-dataset id {block.source_dataset_id}, "
        f"claim={block.claim_class}"
    )

    # determinism: same seed reproduces the series and its fingerprint
    again = _ok(
        generate(_base(process="gbm", seed_price=110_000, volatility="0.001"), calendar=calendar)
    )
    once = _ok(
        generate(_base(process="gbm", seed_price=110_000, volatility="0.001"), calendar=calendar)
    )
    print("deterministic:", again.config_fingerprint == once.config_fingerprint)

    # typed refusals (R8)
    unknown = resolve_generator_config(_base(process="regime-switching"))
    assert is_refusal(unknown) and unknown.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    mismatch = resolve_generator_config(
        _base(process="gbm", seed_price=110_000, volatility="0.001", events=["corporate-action"])
    )
    assert is_refusal(mismatch) and mismatch.category is RefusalCategory.INVALID_INPUT
    replay = resolve_generator_config(
        _base(process="gbm", seed_price=110_000, volatility="0.001", clock="replay")
    )
    assert is_refusal(replay) and replay.category is RefusalCategory.INVALID_INPUT
    print(
        "refusals: unknown process=unsupported capability; "
        "corporate-action=invalid input; replay clock=invalid input"
    )
    print("data generate ok")


if __name__ == "__main__":
    main()
