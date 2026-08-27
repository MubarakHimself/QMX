"""Epic 20 · Story 20.1 (L3) — axis declaration, Cartesian expansion, pre-flight count.

Requirement-derived acceptance conformance. Each assertion names the concrete
counter-case that would make it FAIL; source is read-only evidence.

  T20-301  R1   expansion == full Cartesian product, deterministic order, 1x1x1 unit
  T20-302  R2   distinct combos -> distinct fp1 run-ids AND distinct resolved-config
                fp1 (run-id/ledger-key) -> no combo dropped/overwritten  (P0 · R-004)
  T20-303  R3   pre-flight count == product of axis lengths, a pure inspection (P0)
  T20-304  R4   the qmb door is a thin wrapper over the ONE library function   (P1)
  T20-305  R5   an empty axis -> typed `invalid input` naming the axis         (P0)
  T20-306  R6   exact values verbatim; money/rational cross AD-7/AD-22; float refused (P0)
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from conftest import (
    SEED,
    TF_1M,
    TF_5M,
    admit,
    declaration,
    fixture_port,
    ok,
    run_settings,
)

from qmb.doors import api
from qmb.doors.cli import invoke_sweep_count
from qmb.sweep import SweepDeclaration, SweepRunSpec, expand_sweep, preflight_run_count
from qmf.core.exact import ExactRational, Money
from qmf.core.refusal import RefusalCategory, is_refusal


def _decl(**kwargs: object) -> object:
    """A raw try_create call (may return a refusal), for the empty-axis cases."""
    base: dict[str, object] = {
        "bot": "mean-reversion",
        "book": "scalping",
        "bms": "acct-1",
        "instruments": ("EURUSD", "GBPUSD"),
        "timeframes": (TF_1M,),
        "parameters": None,
    }
    base.update(kwargs)
    return SweepDeclaration.try_create(**base)  # type: ignore[arg-type]


# --- T20-301 (R1) : full Cartesian product in deterministic declaration order --


def test_t20_301_expansion_is_full_cartesian_product_and_unit_scale() -> None:
    decl = ok(
        _decl(
            instruments=("EURUSD", "GBPUSD"),
            timeframes=(TF_1M, TF_5M),
            parameters={"lookback": [10, 20]},
        )
    )
    combos = ok(expand_sweep(decl))
    # Counter-case: a missing/duplicated/extra combination changes the count.
    assert len(combos) == 2 * 2 * 2 == 8
    # Instruments vary slowest, the last-declared parameter varies fastest.
    seen = [(c.instrument, c.timeframe.parameters["seconds"], c.parameters["lookback"]) for c in combos]
    assert seen == [
        ("EURUSD", 60, 10), ("EURUSD", 60, 20),
        ("EURUSD", 300, 10), ("EURUSD", 300, 20),
        ("GBPUSD", 60, 10), ("GBPUSD", 60, 20),
        ("GBPUSD", 300, 10), ("GBPUSD", 300, 20),
    ]
    # Deterministic: a second expansion of the same declaration is identical.
    again = ok(expand_sweep(decl))
    assert [c.fp1_identity() for c in again] == [c.fp1_identity() for c in combos]
    # A 1x1x1 declaration is a single run spec — the same object at unit scale.
    unit = ok(_decl(instruments=("EURUSD",), timeframes=(TF_1M,), parameters=None))
    unit_combos = ok(expand_sweep(unit))
    assert len(unit_combos) == 1
    assert isinstance(unit_combos[0], SweepRunSpec)
    assert unit_combos[0].parameters == {}


# --- T20-302 (R2 · R-004) : distinct combos -> distinct fp1, nothing collapsed --


def test_t20_302_distinct_combos_have_distinct_run_and_config_fingerprints() -> None:
    admitted = admit(instruments=("EURUSD", "GBPUSD"), parameters={"lookback": [10, 20]})
    combos = admitted.combos
    assert admitted.run_count == 4

    # (a) every semantically-distinct combination has a distinct combo fp1.
    combo_fps = {ok(c.fingerprint()).value for c in combos}
    assert len(combo_fps) == len(combos) == 4

    # (b) THE key assertion (R-004): every combination's RESOLVED-config fp1 —
    # the run-id root, ledger key, and output-dir name — is distinct. If the
    # compiler dropped a swept parameter out of identity, two combos would
    # collapse to the same run id and one would be silently overwritten. Counter-
    # case: len(config fp set) < run_count.
    configs = ok(admitted.compile_all(**run_settings()))
    config_fps = {c.fingerprint.value for c in configs}
    assert len(config_fps) == admitted.run_count == 4
    # The run-id root IS the resolved-config fingerprint (B-3): distinct here too.
    assert len({c.run_id.value for c in configs}) == 4

    # (c) two combos differing only in the swept lookback (same instrument)
    # still resolve to distinct run ids — the parameter is identity-bearing.
    eur = [c for c, combo in zip(configs, combos, strict=True) if combo.instrument == "EURUSD"]
    assert len(eur) == 2
    assert eur[0].fingerprint.value != eur[1].fingerprint.value


# --- T20-303 (R3) : pre-flight count is the product, a pure inspection ---------


def test_t20_303_preflight_count_is_the_product_and_a_pure_inspection() -> None:
    decl = ok(
        _decl(
            instruments=("EURUSD", "GBPUSD", "USDJPY"),
            timeframes=(TF_1M, TF_5M),
            parameters={"lookback": [10, 20, 30, 40]},
        )
    )
    assert ok(preflight_run_count(decl)) == 3 * 2 * 4 == 24

    # Purity, observed behaviourally: a declaration whose Cartesian product is a
    # BILLION run specs returns its count instantly. If the count spawned a
    # process / expanded / admitted the batch (the impure paths), a billion-combo
    # count could never return — it would exhaust memory or never terminate.
    huge = ok(
        _decl(
            instruments=tuple(f"INSTR{i}" for i in range(1000)),
            timeframes=tuple({"kind": "time-interval", "seconds": 60 * (i + 1)} for i in range(1000)),
            parameters={"n": list(range(1000))},
        )
    )
    assert ok(preflight_run_count(huge)) == 1000 * 1000 * 1000 == 1_000_000_000


# --- T20-304 (R4) : the CLI/API door is a thin wrapper over the one library fn --


def test_t20_304_door_count_equals_library_and_the_logic_lives_once() -> None:
    _port, book, bms, bot = fixture_port()
    decl = declaration(
        bot=bot.stable_id, book=book.stable_id, bms=bms.stable_id, parameters={"lookback": [10, 20, 30]}
    )
    library = ok(preflight_run_count(decl))
    # The door returns the identical count — it computes no count of its own.
    assert ok(invoke_sweep_count(declaration=decl)) == library == 2 * 1 * 3 == 6
    # The axes-to-count logic lives ONCE: the API surface IS the library object,
    # not a re-implementation. Counter-case: a door-local copy would be a distinct
    # function object and could diverge.
    assert api.preflight_run_count is preflight_run_count
    assert api.expand_sweep is expand_sweep


# --- T20-305 (R5) : an empty axis is a typed invalid-input naming the axis -----


def test_t20_305_empty_axis_is_a_typed_invalid_input_naming_the_axis() -> None:
    empty_instruments = _decl(instruments=[])
    assert is_refusal(empty_instruments)
    assert empty_instruments.category is RefusalCategory.INVALID_INPUT
    assert empty_instruments.context["field"] == "instruments"

    empty_bars = _decl(timeframes=[])
    assert is_refusal(empty_bars)
    assert empty_bars.category is RefusalCategory.INVALID_INPUT
    assert empty_bars.context["field"] == "timeframes"

    empty_values = _decl(parameters={"lookback": []})
    assert is_refusal(empty_values)
    assert empty_values.category is RefusalCategory.INVALID_INPUT
    assert empty_values.context["field"] == "parameters"
    assert empty_values.context["parameter"] == "lookback"
    # A refusal is a RETURNED value, never a raised exception (CT-04).
    assert not isinstance(empty_instruments, BaseException)


# --- T20-306 (R6) : exact values verbatim; money/rational convert; float refused --


def test_t20_306_exact_values_verbatim_money_converts_float_refused() -> None:
    # exact-integer / categorical / boolean carried verbatim into identity.
    decl = ok(
        _decl(
            instruments=("EURUSD",),
            timeframes=(TF_1M,),
            parameters={"lookback": [10], "mode": ["fast"], "use_atr": [True]},
        )
    )
    run = ok(expand_sweep(decl))[0]
    assert run.parameters["lookback"] == 10
    assert run.parameters["mode"] == "fast"
    assert run.parameters["use_atr"] is True
    identity = cast("Mapping[str, object]", run.fp1_identity()["parameters"])
    assert identity == {"lookback": 10, "mode": "fast", "use_atr": True}

    # A money value crosses a NAMED AD-7/AD-22 conversion (rounding + scale)
    # before entering identity; the identity content is the exact reduced form.
    money_decl = ok(
        _decl(
            instruments=("EURUSD",),
            timeframes=(TF_1M,),
            parameters={"stop": [{"kind": "money", "value": 1.5, "currency": "USD", "scale": 2, "rounding": "half-up"}]},
        )
    )
    money_run = ok(expand_sweep(money_decl))[0]
    stop = money_run.parameters["stop"]
    assert isinstance(stop, Money)
    assert stop == Money(value=150, currency="USD", scale=2)
    stop_identity = cast("Mapping[str, object]", money_run.fp1_identity()["parameters"])["stop"]
    assert stop_identity == stop.fp1_identity()  # exact num/den, never a float
    assert ok(money_run.fingerprint()).value.startswith("fp1:sha256:")

    # A rational value likewise crosses a named conversion to an ExactRational.
    ratio_decl = ok(
        _decl(
            instruments=("EURUSD",),
            timeframes=(TF_1M,),
            parameters={"atr": [{"kind": "rational", "value": 2.5, "unit_kind": "dimensionless-ratio", "scale": 1, "rounding": "half-up"}]},
        )
    )
    atr = ok(expand_sweep(ratio_decl))[0].parameters["atr"]
    assert isinstance(atr, ExactRational)
    assert atr.as_fraction().numerator == 5 and atr.as_fraction().denominator == 2

    # A BARE binary float never appears in a run spec's identity content — refused.
    float_refusal = _decl(instruments=("EURUSD",), timeframes=(TF_1M,), parameters={"stop": [1.5]})
    assert is_refusal(float_refusal)
    assert float_refusal.category is RefusalCategory.INVALID_INPUT
    assert float_refusal.context["parameter"] == "stop"


def test_t20_306_conversion_without_rounding_and_scale_is_refused() -> None:
    # The AD-7/AD-22 crossing MUST state its rounding mode and target scale; a bare
    # {kind, value} conversion is invalid input (no unstated rounding of money).
    missing = _decl(
        instruments=("EURUSD",),
        timeframes=(TF_1M,),
        parameters={"stop": [{"kind": "money", "value": 1.5, "currency": "USD"}]},
    )
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.INVALID_INPUT
    # SEED referenced only to keep the exact-Money import path honest in this file.
    assert isinstance(SEED, Money)
