"""Reference usage — port-set composition and fidelity identity (Story 17.1).

Executable::

    python qmb/examples/execution_composition_usage.py

Shows the things B-6 / AR-56 / LABEL-3 / SC-06 pin down:

1. Fill, slippage, and cost plus the financing scheduler bind ONLY from a
   resolved run-config, never by ambient discovery.
2. Composition order is fill → slippage → cost.
3. Inbound execution is a CT-23 authorized intent, never a bot-sized order.
4. An AD-40 full-loss price is required before any open; a risk-reducing exit
   is admitted without a new full-loss price.
5. Fidelity identity is adapter-id + composition-version + taint; taint is
   ``optimistic`` until GAP-0048.
6. A run's fidelity is the lowest of its bound adapters; mixed-fidelity
   Book-bar comparison without an explicit override is a typed refusal.
7. ``world=simulated`` is refused; replay-on-synthetic is invalid input.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.config import (
    CLOCK_REPLAY,
    CLOCK_SIMULATED,
    PROVENANCE_RECORDED,
    PROVENANCE_SYNTHETIC_TAINTED,
    mint_replay_binding,
)
from qmb.execution import (
    COMPOSITION_ORDER,
    COST_ADAPTER_KEY,
    COST_ADAPTER_ZERO,
    FILL_ADAPTER_DECLARED_PATH,
    FILL_ADAPTER_KEY,
    FINANCING_SCHEDULE_KEY,
    SLIPPAGE_ADAPTER_KEY,
    SLIPPAGE_ADAPTER_ZERO,
    TAINT_OPTIMISTIC,
    SlicePath,
    bind_execution_ports,
    compare_book_bar_fidelity,
    lowest_fidelity,
    stamp_fidelity,
)
from qmf.core.exact import ExactRational, Money, Price, Quantity, UnitKind
from qmf.core.fingerprint import World, fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.risk.door import Direction, EntryIntent, ExitIntent, ExitKind, ExitLogicRef, ReasonCode
from qmf.risk.paper import ExecutionTarget

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _fp(seed: str):
    return _unwrap(fingerprint({"seed": seed}), seed)


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value="venue-replay"), symbol="EURUSD")


def _price() -> Price:
    return _unwrap(Price.try_create(1_10000, _instrument(), 5), "price")


def _qty(value: int) -> Quantity:
    return _unwrap(Quantity.try_create(value, "lot", 0), "quantity")


def _resolved(
    *,
    clock: str = CLOCK_REPLAY,
    provenance: str = PROVENANCE_RECORDED,
    world: World | None = None,
    keys: dict[str, object] | None = None,
) -> qmb.ResolvedRunConfig:
    payload = {
        COST_ADAPTER_KEY: COST_ADAPTER_ZERO,
        FILL_ADAPTER_KEY: FILL_ADAPTER_DECLARED_PATH,
        FINANCING_SCHEDULE_KEY: "broker-swap-table",
        SLIPPAGE_ADAPTER_KEY: SLIPPAGE_ADAPTER_ZERO,
    }
    if keys is not None:
        payload.update(keys)
    derived = World.SIMULATED if provenance == PROVENANCE_SYNTHETIC_TAINTED else World.REPLAY
    bound_world = world if world is not None else derived
    book = _fp("book")
    bms = _fp("bms")
    bot = _fp("bot")
    binding = _unwrap(
        mint_replay_binding(
            book_fp1=book,
            bms_fp1=bms,
            bot_fp1=bot,
            starting_capital=Money(value=1_000_000, currency="USD", scale=2),
            seed_overridden=False,
            venue_id="venue-replay",
            account_id="acct-replay",
            clock=clock,
            data_provenance=provenance,
            keys=payload,
        ),
        "binding",
    )
    identity = {
        "book_fp1": book.value,
        "clock": clock,
        "data_provenance": provenance,
        "keys": payload,
        "world": bound_world.value,
    }
    return qmb.ResolvedRunConfig(
        format_version=1,
        book_fp1=book,
        bms_fp1=bms,
        bot_fp1=bot,
        book_fragment_fp1=_fp("book-frag"),
        bms_fragment_fp1=_fp("bms-frag"),
        keys=payload,
        clock=clock,
        data_provenance=provenance,
        world=bound_world,
        fingerprint=_unwrap(fingerprint(identity), "config fp"),
        binding_fp1=binding.fingerprint,
        replay_binding=binding,
    )


class _OffsetStop:
    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: object
    ) -> Result[Price]:
        del cited_evidence
        value = entry_price.value - 500 if direction is Direction.LONG else entry_price.value + 500
        return Price.try_create(value, entry_price.instrument, entry_price.scale)


def main() -> None:
    assert qmb.AMBIENT_DISCOVERY is False
    assert qmb.COMPOSITION_ORDER == COMPOSITION_ORDER == ("fill", "slippage", "cost")
    bound = _unwrap(bind_execution_ports(_resolved()), "bound execution")
    assert bound.fill_adapter_id == FILL_ADAPTER_DECLARED_PATH
    assert bound.ports.fill is not bound.ports.slippage
    print("bound from resolved run-config")
    print("fill → slippage → cost")

    class _BotSized:
        size = 1.0

    refused = bound.execute(
        intent=_BotSized(),
        path=_unwrap(SlicePath.try_create("eurusd", (_price(),)), "path"),
        requested_quantity=_qty(1),
        position_cap=_qty(1),
        lot_step=_qty(1),
    )
    assert is_refusal(refused)
    print("never a bot-sized order")

    path = _unwrap(SlicePath.try_create("eurusd", (_price(),)), "path")
    intent = _unwrap(
        EntryIntent.try_create(
            _instrument(),
            Direction.LONG,
            _unwrap(ReasonCode.try_create("breakout", "scalper-v1"), "reason"),
            _unwrap(
                ExecutionTarget.try_create("demo", VenueId(value="venue-replay"), "acct-replay"),
                "target",
            ),
        ),
        "entry",
    )
    opened = _unwrap(
        bound.execute(
            intent=intent,
            path=path,
            requested_quantity=_qty(1),
            position_cap=_qty(1),
            lot_step=_qty(1),
            entry_price=_price(),
            exit_logic_ref=_unwrap(
                ExitLogicRef.try_create("book.default.evidence_stop", {"style": "structure"}),
                "logic",
            ),
            module=_OffsetStop(),
            book_resolved_requested_r=_unwrap(
                ExactRational.try_create(1, 1, UnitKind.R_MULTIPLE), "requested_r"
            ),
        ),
        "open",
    )
    assert opened.fill.taint == TAINT_OPTIMISTIC
    print("full-loss price required before open")
    _unwrap(
        bound.execute(
            intent=_unwrap(
                ExitIntent.try_create(
                    ExitKind.CLOSE_FULL,
                    _unwrap(ReasonCode.try_create("done", "scalper-v1"), "reason"),
                    _fp("vp-1"),
                ),
                "exit",
            ),
            path=path,
            requested_quantity=_qty(1),
            position_cap=_qty(1),
            lot_step=_qty(1),
        ),
        "close",
    )
    print("risk-reducing exit admitted without new full-loss")

    stamped = _unwrap(stamp_fidelity(FILL_ADAPTER_DECLARED_PATH), "fidelity")
    assert stamped.adapter_id == FILL_ADAPTER_DECLARED_PATH
    assert stamped.taint == TAINT_OPTIMISTIC
    assert "taint" not in stamped.fp1_identity()
    print("fidelity identity is adapter-id + composition-version + taint")
    print("optimistic taint")
    run = _unwrap(lowest_fidelity(bound.fidelity.bound), "run fidelity")
    assert run.taint == TAINT_OPTIMISTIC
    print("lowest fidelity of bound adapters")
    other = _unwrap(
        lowest_fidelity((_unwrap(stamp_fidelity("quote-real"), "other"),)),
        "other fidelity",
    )
    mixed = compare_book_bar_fidelity(run, other)
    assert is_refusal(mixed)
    print("mixed-fidelity Book-bar comparison refused")
    assert is_ok(compare_book_bar_fidelity(run, other, override=True))

    simulated = bind_execution_ports(
        _resolved(
            clock=CLOCK_SIMULATED,
            provenance=PROVENANCE_SYNTHETIC_TAINTED,
            world=World.SIMULATED,
        )
    )
    assert is_refusal(simulated)
    print("world=simulated refused")
    replay_synth = bind_execution_ports(
        _resolved(
            clock=CLOCK_REPLAY,
            provenance=PROVENANCE_SYNTHETIC_TAINTED,
            world=World.SIMULATED,
        )
    )
    assert is_refusal(replay_synth)
    print("replay-on-synthetic is invalid input")
    print("execution composition ok")


if __name__ == "__main__":
    main()
