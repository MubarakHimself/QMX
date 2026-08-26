"""Reference usage — sweep axis declaration, Cartesian expansion, pre-flight count (Story 20.1).

Executable::

    python qmb/examples/sweep_axes_usage.py

Shows the things B-12 / Story 20.1 pin down:

1. A sweep is declared as axes — instruments[], timeframes[] (a BarSpec list),
   and parameters{name: values[]} — over a bot/Book/BMS context, and expands to
   the full Cartesian product: one run spec per combination, in a deterministic
   declaration-order enumeration (instruments slowest, last parameter fastest).
2. The pre-flight run count equals the product of the axis lengths and is a pure
   inspection: it spawns no process, writes no ledger line, and admits no batch.
3. A single run is representable as a 1x1x1 sweep — the same object at unit scale.
4. An empty axis (a zero-length instrument, BarSpec, or parameter-value list) is a
   typed invalid-input refusal naming the empty axis — never a silent zero-combo batch.
5. Exact integers, categorical tokens, and booleans are carried verbatim; a
   money/rational value crosses a named AD-7/AD-22 conversion (rounding + scale)
   before entering a run spec, so a binary float never appears in identity content.
6. The qmb CLI/API door is a thin wrapper over the one pure library function; the
   axes-to-count computation lives once in the library.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.doors import api
from qmf.core.exact import ExactRational, Money
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_TF_1M = {"kind": "time-interval", "seconds": 60}
_TF_5M = {"kind": "time-interval", "seconds": 300}


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def main() -> None:
    declaration = _unwrap(
        qmb.SweepDeclaration.try_create(
            bot="mean-reversion",
            book="scalping",
            bms="acct-1",
            instruments=["EURUSD", "GBPUSD"],
            timeframes=[_TF_1M, _TF_5M],
            parameters={"lookback": [10, 20, 30], "use_atr": [True, False]},
        ),
        "sweep declaration",
    )

    combos = _unwrap(qmb.expand_sweep(declaration), "expansion")
    assert len(combos) == 2 * 2 * 3 * 2 == 24
    # Deterministic declaration order: instruments vary slowest, the last-declared
    # parameter (use_atr) varies fastest.
    assert combos[0].instrument == "EURUSD"
    assert combos[0].timeframe.parameters["seconds"] == 60
    assert combos[0].parameters == {"lookback": 10, "use_atr": True}
    assert combos[1].parameters == {"lookback": 10, "use_atr": False}
    assert combos[-1].instrument == "GBPUSD"
    fingerprints = {_unwrap(combo.fingerprint(), "combo fp1").value for combo in combos}
    assert len(fingerprints) == 24
    print(f"Cartesian product: {len(combos)} isolated run specs, declaration order")

    count = _unwrap(qmb.preflight_run_count(declaration), "pre-flight count")
    assert count == 24 == declaration.run_count
    assert qmb.PREFLIGHT_SPAWNS_PROCESS is False
    assert qmb.PREFLIGHT_WRITES_LEDGER_LINE is False
    assert qmb.PREFLIGHT_ADMITS_BATCH is False
    assert qmb.PREFLIGHT_IS_PURE_INSPECTION is True
    print(f"pre-flight run count {count} is a pure inspection, spawns no process")

    # A single run = a 1x1x1 sweep: the same object at unit scale.
    unit = _unwrap(
        qmb.SweepDeclaration.try_create(
            bot="mean-reversion",
            book="scalping",
            bms="acct-1",
            instruments=["EURUSD"],
            timeframes=[_TF_1M],
        ),
        "1x1x1 sweep",
    )
    unit_runs = _unwrap(qmb.expand_sweep(unit), "unit expansion")
    assert len(unit_runs) == 1
    assert _unwrap(qmb.preflight_run_count(unit), "unit count") == 1
    layer = unit_runs[0].run_spec_layer()
    assert layer["bot"] == "mean-reversion"
    assert "stream_set" in layer
    print("a single run is a 1x1x1 sweep - the same object at unit scale (spec R13)")

    # An empty axis is a typed invalid-input refusal naming the empty axis.
    empty_bars = qmb.SweepDeclaration.try_create(
        bot="mean-reversion",
        book="scalping",
        bms="acct-1",
        instruments=["EURUSD"],
        timeframes=[],
    )
    assert is_refusal(empty_bars)
    assert empty_bars.category is RefusalCategory.INVALID_INPUT
    assert empty_bars.context["field"] == "timeframes"
    empty_param = qmb.SweepDeclaration.try_create(
        bot="mean-reversion",
        book="scalping",
        bms="acct-1",
        instruments=["EURUSD"],
        timeframes=[_TF_1M],
        parameters={"lookback": []},
    )
    assert is_refusal(empty_param)
    assert empty_param.context["parameter"] == "lookback"
    print("an empty axis is invalid input naming the axis, never a silent zero-combo batch")

    # A bare binary float is refused; money/rational cross a named AD-7/AD-22 conversion.
    bare_float = qmb.SweepDeclaration.try_create(
        bot="mean-reversion",
        book="scalping",
        bms="acct-1",
        instruments=["EURUSD"],
        timeframes=[_TF_1M],
        parameters={"stop": [1.5]},
    )
    assert is_refusal(bare_float)
    assert bare_float.category is RefusalCategory.INVALID_INPUT
    converted = _unwrap(
        qmb.SweepDeclaration.try_create(
            bot="mean-reversion",
            book="scalping",
            bms="acct-1",
            instruments=["EURUSD"],
            timeframes=[_TF_1M],
            parameters={
                "stop": [
                    {
                        "kind": "money",
                        "value": 1.5,
                        "currency": "USD",
                        "scale": 2,
                        "rounding": "half-up",
                    }
                ],
                "atr_mult": [
                    {
                        "kind": "rational",
                        "value": 2.5,
                        "unit_kind": "dimensionless-ratio",
                        "scale": 1,
                        "rounding": "half-up",
                    }
                ],
                "lookback": [10, 20],
                "mode": ["fast", "slow"],
                "use_atr": [True, False],
            },
        ),
        "converted sweep",
    )
    converted_runs = _unwrap(qmb.expand_sweep(converted), "converted expansion")
    first = converted_runs[0]
    assert isinstance(first.parameters["stop"], Money)
    assert isinstance(first.parameters["atr_mult"], ExactRational)
    assert first.parameters["lookback"] == 10
    assert first.parameters["mode"] == "fast"
    assert first.parameters["use_atr"] is True
    identity = first.fp1_identity()
    stop_identity = identity["parameters"]["stop"]  # type: ignore[index]
    assert stop_identity == {
        "class": "money",
        "currency": "USD",
        "den": 2,
        "format_version": 1,
        "num": 3,
        "storage_scale": 18,
        "unit_kind": "money(currency)",
    }
    # No binary float survives into identity content — the fp1 is computed clean.
    assert _unwrap(first.fingerprint(), "converted fp1").value.startswith("fp1:sha256:")
    print("money/rational cross a named conversion; a binary float never enters identity")

    # The door is a thin wrapper over the one pure library function.
    door_count = api.preflight_run_count(declaration)
    assert is_ok(door_count)
    assert door_count.value == count
    assert api.preflight_run_count is qmb.preflight_run_count
    door_refusal = api.preflight_run_count(
        {"bot": "b", "book": "k", "bms": "m", "instruments": [], "timeframes": [_TF_1M]}
    )
    assert is_refusal(door_refusal)
    print("the qmb door is a thin wrapper over one pure library expansion function")

    print(f"qmb {qmb.__version__}")
    print("sweep axes ok")


if __name__ == "__main__":
    main()
