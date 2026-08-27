"""L3 — the CT-23 v2 door boundary: no bot-side full-loss channel (E12-L3-04, P0).

Framed STRUCTURALLY per DEC-0185: there is no inbound-refusal posture on the
advisory stop itself. The protocol simply provides no bot-side full-loss field
(the entry type carries only the optional advisory stop), and an inbound
``requested_r`` is invalid input. P0-Q3 / QL-7 / CT-23 v2 / DEC-0177/0182/0185.
"""

from __future__ import annotations

import _world as w
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import RefusalCategory, is_ok, is_refusal
from qmf.risk.door import Direction, EntryIntent, ReasonCode
from qmf.risk.paper import ExecutionTarget
from qml.protocol import accept_intents


def _entry_without_advisory_stop() -> EntryIntent:
    venue = w.unwrap(VenueId.try_create("ctrader"), "venue")
    instrument = w.unwrap(Instrument.try_create(venue, "EURUSD"), "instrument")
    target = w.unwrap(ExecutionTarget.try_create("live", venue, "acct-1"), "target")
    reason = w.unwrap(ReasonCode.try_create("breakout", w.FAMILY), "reason")
    return w.unwrap(
        EntryIntent.try_create(instrument, Direction.LONG, reason, target), "entry (no stop)"
    )


def test_e12_l3_04_no_bot_side_full_loss_field_exists() -> None:
    """Structural: an entry intent carries no requested_r and no full-loss price field."""
    entry = w.make_entry()
    assert entry.advisory_stop_proposal is not None, "the entry carries only an advisory stop"
    assert not hasattr(entry, "requested_r")
    assert not hasattr(entry, "declared_full_loss_price")
    assert not hasattr(entry, "full_loss_price")


def test_e12_l3_04_inbound_requested_r_refused() -> None:
    """An inbound requested_r is invalid input — sizing is Book-resolved, never bot-supplied."""
    refusal = accept_intents([{"intent_family": "entry", "requested_r": 2}])
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context.get("field") == "requested_r"


def test_e12_l3_04_inbound_full_loss_price_refused() -> None:
    """A bot-supplied full-loss price through the door is invalid input (Book-side, single-sited)."""
    refusal = accept_intents([{"intent_family": "entry", "declared_full_loss_price": "1.2345"}])
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context.get("field") == "declared_full_loss_price"


def test_e12_l3_04_advisory_stop_entry_admitted() -> None:
    """An entry with the OPTIONAL advisory stop proposal is admitted unchanged."""
    admitted = accept_intents([w.make_entry()], permitted_exit_intents=("close_full",))
    assert is_ok(admitted)
    assert len(admitted.value) == 1
    assert admitted.value[0].advisory_stop_proposal is not None


def test_e12_l3_04_format2_reader_accepts_format1_entry() -> None:
    """A format-2 reader accepts a format-1 entry (no advisory stop) unchanged (AD-5)."""
    admitted = accept_intents([_entry_without_advisory_stop()])
    assert is_ok(admitted)
    assert len(admitted.value) == 1
    assert admitted.value[0].advisory_stop_proposal is None
