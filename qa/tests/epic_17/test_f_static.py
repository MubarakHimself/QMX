"""Epic 17 · Group F — static / structural gates (T-17.0-protocol/nofloat/noconst).

L0 gates over the execution package: the three fill/slippage/cost seams are distinct
runtime-checkable Protocols plus a separate financing scheduler (R1); no binary float
touches the money/price/quantity path (R24/R16); and no calibration content constant
(spread/slip/commission/swap-point/rollover-hour) is embedded as a fallback — absence
refuses instead (R14/R23/R26/R30/R29). A failing test is a FINDING, never a licence
to soften the assertion or edit source.
"""

from __future__ import annotations

import ast
import pathlib

from _e17 import FakeCalendar, inst, instrument, ok, price, qty, writer

from qmf.core.refusal import RefusalCategory, is_refusal
from qmf.risk.door import Direction
from qmb.execution.cost import CommissionCalibration, PercentOfNotionalCostAdapter, charge_commission
from qmb.execution.financing import (
    FinancingScheduler,
    OpenPosition,
    SwapCalibration,
    SwapRate,
    apply_financing_rollover,
)
from qmb.execution.fill import Fill
from qmb.execution.ports import (
    CostPort,
    ExecutionPorts,
    FillPort,
    FinancingPort,
    SlippagePort,
)
from qmb.execution.slippage import SlippageCalibration, slip_fill
from qmb.execution.spread import SpreadCalibration, SpreadFeed, resolve_spread

_EXECUTION_DIR = pathlib.Path("qmb/src/qmb/execution")


# --- T-17.0-protocol (L0) three distinct Protocol seams + financing scheduler [R1]
def test_t170_three_distinct_protocol_seams() -> None:
    seams = (FillPort, SlippagePort, CostPort, FinancingPort)
    # Four DISTINCT types, each a runtime-checkable typing.Protocol.
    assert len({id(s) for s in seams}) == 4
    for seam in seams:
        assert getattr(seam, "_is_protocol", False) is True
        assert getattr(seam, "_is_runtime_protocol", False) is True
    # The seams are behaviourally distinct: a fill stub is not a cost port.
    from _e17 import RecordingCost, RecordingFill

    assert isinstance(RecordingFill(), FillPort)
    assert not isinstance(RecordingFill(), CostPort)
    assert isinstance(RecordingCost(), CostPort)
    assert not isinstance(object(), FillPort)
    # fill, slippage and cost must be SEPARATE bound objects (B-6, AR-56).
    from _e17 import RecordingFinancing, RecordingSlippage

    one = RecordingFill()
    same = ExecutionPorts.try_create(one, one, RecordingCost(), RecordingFinancing())
    assert is_refusal(same)


# --- T-17.0-nofloat (L0) no binary float on the money/price/quantity path [R24/R16]
def test_t170_no_binary_float_on_money_path() -> None:
    offenders: list[str] = []
    for path in sorted(_EXECUTION_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                offenders.append(f"{path.name}:{node.lineno} float literal {node.value!r}")
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "float"):
                offenders.append(f"{path.name}:{node.lineno} float() call")
    assert offenders == [], f"binary float on the money path: {offenders}"
    # Self-check: the scanner DOES catch a float (so a green above is a real negative).
    probe = ast.parse("rate = 0.01\n")
    found = [n for n in ast.walk(probe) if isinstance(n, ast.Constant) and isinstance(n.value, float)]
    assert found


# --- T-17.0-noconst (L0) no calibration constant is a fallback; absence refuses [R14/R23/R26/R30/R29]
def test_t170_no_embedded_calibration_constant_absence_refuses() -> None:
    fill = ok(Fill.try_create(qty(10), qty(10), price(100_000), post_slip_price=price(100_000),
                              side=Direction.LONG))
    wide = _wide_path()

    # spread: an empty (content-deferred) calibration REFUSES — no embedded spread number.
    empty_spread = ok(SpreadCalibration.try_create("broker-x", ()))
    feed = ok(SpreadFeed.try_create(instrument("EURUSD")))
    assert is_refusal(resolve_spread(feed, at=inst(), session="london", calibration=empty_spread))

    # slippage: a constant-percent calibration with NO percent refuses — no embedded rate.
    slip_cal = ok(SlippageCalibration.try_create("constant-percent", "broker-x"))
    slipped = slip_fill(fill, wide, model="constant-percent", calibration=slip_cal,
                        apply_to_passive_limits=False)
    assert is_refusal(slipped) and slipped.category is RefusalCategory.UNAVAILABLE_DEPENDENCY

    # commission: a percent-of-notional calibration with NO percent refuses — no embedded rate.
    fee_cal = ok(CommissionCalibration.try_create("percent-of-notional", "broker-x",
                                                  currency="USD"))
    assert fee_cal.percent is None  # no default rate is baked in
    charged = charge_commission(fill, model="percent-of-notional", calibration=fee_cal)
    assert is_refusal(charged) and charged.category is RefusalCategory.UNAVAILABLE_DEPENDENCY

    # swap: a scheduler with no swap table refuses — no embedded swap point.
    assert is_refusal(FinancingScheduler(schedule_ref="fx", calibration=None)
                      .schedule(stream_id="eurusd", direction=Direction.LONG))

    # rollover instant: financing needs the bound calendar — no hardcoded rollover hour.
    swap = ok(SwapCalibration.try_create("broker-x",
                                         rates=(ok(SwapRate.try_create("eurusd", Direction.LONG,
                                                                       _money(-5))),),
                                         weekend_holiday_handling="apply"))
    pos = ok(OpenPosition.try_create("eurusd", Direction.LONG, qty(10)))
    no_calendar = apply_financing_rollover(FinancingScheduler(schedule_ref="fx", calibration=swap),
                                           (pos,), frontier=inst(), calendar="09:00",
                                           writer=writer(), world=_replay())
    assert is_refusal(no_calendar) and no_calendar.context.get("field") == "calendar"


def _wide_path():
    from _e17 import slice_path

    return slice_path(open=100_000, high=110_000, low=90_000, close=100_000, prints=(90_000, 110_000))


def _money(minor):
    from _e17 import money

    return money(minor)


def _replay():
    from qmf.core.fingerprint import World

    return World.REPLAY
