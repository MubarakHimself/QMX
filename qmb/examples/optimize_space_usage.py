"""Reference usage — typed parameter search space schema, Study creation (Story 21.1).

Executable::

    python qmb/examples/optimize_space_usage.py

Shows the things B-8 / Story 21.1 pin down:

1. A Study declares its parameter space as a typed, bounded schema — each variable
   a type in {exact integer, exact rational, categorical, boolean}, numeric with
   min/max/step/default, categorical with non-empty options + default. The schema
   is authoritative in the CT-33 Bot definition and read through the ONE schema
   coercer; QMB keeps no second copy.
2. The validated space is identity-bearing: two Studies declaring the same space
   (in any order) share one space fingerprint, and it materializes as identity
   content of the resolved run-config — declaring the space is config, never a
   code edit to swap the tunnel.
3. A numeric step wider than the max - min span is a typed invalid-input refusal
   naming the parameter — never a silent clamp; min > max and step <= 0 are
   refused too.
4. A categorical parameter with empty options, or a default outside its options,
   is a typed invalid-input refusal.
5. A money parameter is exact-integer minor units; declaring money as an exact
   rational, or letting a binary float appear anywhere in the space, is invalid
   input — the money path never sees a float in identity.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.doors import api
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _int(name: str, low: int, high: int, step: int) -> dict[str, object]:
    return {
        "name": name,
        "type": "exact integer",
        "bounds": {"min": low, "max": high},
        "step": step,
        "default": low,
        "unit_kind": UnitKind.COUNT,
        "ui": "ui-editable",
    }


def _money(name: str, low: int, high: int, step: int) -> dict[str, object]:
    return {**_int(name, low, high, step), "unit_kind": UnitKind.MONEY}


def _categorical(name: str, options: list[str], default: str) -> dict[str, object]:
    return {
        "name": name,
        "type": "categorical",
        "options": options,
        "default": default,
        "unit_kind": UnitKind.COUNT,
        "ui": "ui-editable",
    }


def _boolean(name: str) -> dict[str, object]:
    return {
        "name": name,
        "type": "boolean",
        "default": True,
        "unit_kind": UnitKind.COUNT,
        "ui": "ui-editable",
    }


def _rational(name: str) -> dict[str, object]:
    return {
        "name": name,
        "type": "exact rational",
        "bounds": {
            "min": {"num": 5, "den": 10, "unit_kind": UnitKind.DIMENSIONLESS_RATIO},
            "max": {"num": 30, "den": 10, "unit_kind": UnitKind.DIMENSIONLESS_RATIO},
        },
        "step": {"num": 5, "den": 10, "unit_kind": UnitKind.DIMENSIONLESS_RATIO},
        "default": {"num": 10, "den": 10, "unit_kind": UnitKind.DIMENSIONLESS_RATIO},
        "unit_kind": UnitKind.DIMENSIONLESS_RATIO,
        "ui": "ui-editable",
    }


def _space() -> list[dict[str, object]]:
    return [
        _int("lookback", 1, 200, 1),
        _rational("atr_mult"),
        _categorical("mode", ["fast", "slow"], "fast"),
        _boolean("use_atr"),
        _money("stop", 10, 100, 5),
    ]


def main() -> None:
    space = _unwrap(qmb.coerce_study_space(_space()), "study parameter space")
    assert isinstance(space, qmb.StudyParameterSpace)
    # One CT-33 schema, canonically ordered by name.
    assert space.parameter_names == ("atr_mult", "lookback", "mode", "stop", "use_atr")
    print(f"typed search space validated at Study creation: {len(space.parameters)} parameters")

    # Identity-bearing: same space in any order shares one fingerprint.
    reordered = _unwrap(qmb.coerce_study_space(list(reversed(_space()))), "reordered space")
    assert _unwrap(space.fingerprint(), "fp") == _unwrap(reordered.fingerprint(), "fp reordered")
    layer = space.run_config_layer()
    assert layer[qmb.STUDY_SPACE_KEY] == space.fp1_identity()
    assert _unwrap(fingerprint(layer[qmb.STUDY_SPACE_KEY]), "layer fp").value.startswith("fp1:")
    print("same space shares one fingerprint; it materializes as run-config identity content")

    # OPT-3: a numeric step wider than the span is refused, naming the parameter.
    wide = qmb.coerce_study_space([_int("lookback", 10, 20, 50)])
    assert is_refusal(wide)
    assert wide.category is RefusalCategory.INVALID_INPUT
    assert wide.context["parameter"] == "lookback"
    bad_bounds = qmb.coerce_study_space([_int("lb", 50, 10, 1)])
    assert is_refusal(bad_bounds)
    print("a step wider than max - min is invalid input naming the parameter, never clamped")

    # OPT-1/3: categorical options rules.
    empty_options = qmb.coerce_study_space([_categorical("mode", [], "x")])
    assert is_refusal(empty_options)
    missing_default = qmb.coerce_study_space([_categorical("mode", ["fast", "slow"], "medium")])
    assert is_refusal(missing_default)
    assert missing_default.context["field"] == "default"
    print("empty categorical options, or a default outside options, is invalid input")

    # OPT-4: money is exact-integer minor units; a binary float is banned everywhere.
    money = _unwrap(qmb.coerce_study_space([_money("stop", 10, 100, 5)]), "money space")
    low, high = money.parameters[0].bounds  # type: ignore[misc]
    assert isinstance(low, int) and isinstance(high, int)
    money_rational = qmb.coerce_study_space(
        [
            {
                "name": "stop_r",
                "type": "exact rational",
                "bounds": {
                    "min": {"num": 5, "den": 1, "unit_kind": UnitKind.MONEY},
                    "max": {"num": 50, "den": 1, "unit_kind": UnitKind.MONEY},
                },
                "step": {"num": 5, "den": 1, "unit_kind": UnitKind.MONEY},
                "default": {"num": 10, "den": 1, "unit_kind": UnitKind.MONEY},
                "unit_kind": UnitKind.MONEY,
                "ui": "ui-editable",
            }
        ]
    )
    assert is_refusal(money_rational)
    assert money_rational.context["parameter"] == "stop_r"
    float_bound = qmb.coerce_study_space([{**_money("stop", 10, 100, 5), "default": 12.5}])
    assert is_refusal(float_bound)
    print("money is exact-integer minor units; a binary float never enters the space's identity")

    # The qmb door is a thin wrapper over the one pure library function.
    assert api.coerce_study_space is qmb.coerce_study_space
    door = api.coerce_study_space(_space())
    assert is_ok(door)
    assert _unwrap(door.value.fingerprint(), "door fp") == _unwrap(space.fingerprint(), "lib fp")
    print("the qmb door is a thin wrapper over one pure library validation function")

    print(f"qmb {qmb.__version__}")
    print("study parameter space ok")


if __name__ == "__main__":
    main()
