"""Story 3.6 — entity selectors and the pinned command-fingerprint join (AC1, AC2)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from qmf.core import World, is_ok, is_refusal
from qmf.data import (
    BindingIdentity,
    BotSeat,
    CommandAttribution,
    CommandIndex,
    DecisionOutcome,
    EntityKind,
    EntitySelector,
    bms_journal,
    book_journal,
    bot_logbook,
    entity_journal,
)

_path = Path(__file__).resolve().parent / "logbooks_cases.py"
_name = "qmf.data.tests.logbooks_cases"
_existing = sys.modules.get(_name)
if _existing is not None:
    _cases = _existing
else:
    _spec = importlib.util.spec_from_file_location(_name, _path)
    assert _spec is not None and _spec.loader is not None
    _cases = importlib.util.module_from_spec(_spec)
    sys.modules[_name] = _cases
    _spec.loader.exec_module(_cases)

_ok = _cases.ok
_binding_fields = _cases.binding_fields
_event = _cases.event
_BOOK = _cases.BOOK
_BMS = _cases.BMS
_VENUE = _cases.VENUE
_ACCOUNT = _cases.ACCOUNT
_BOT_DEF = _cases.BOT_DEF
_CMD_A = _cases.CMD_A
_CMD_B = _cases.CMD_B


def test_entity_selector_factories_and_refusals() -> None:
    assert _ok(EntitySelector.for_book(_BOOK)).kind is EntityKind.BOOK
    assert _ok(EntitySelector.for_bms(_BMS)).kind is EntityKind.BMS
    bot = _ok(EntitySelector.for_bot(_BOT_DEF, "seat-1"))
    assert bot.kind is EntityKind.BOT
    assert bot.bot_seat == BotSeat(bot_definition_fp=_BOT_DEF, seat_binding="seat-1")
    binding = _ok(
        BindingIdentity.try_create(
            book_instance_id=_BOOK,
            bms_instance_id=_BMS,
            venue_id=_VENUE,
            account_id=_ACCOUNT,
            world=World.LIVE,
        )
    )
    assert _ok(EntitySelector.for_binding(binding)).kind is EntityKind.BINDING

    assert is_refusal(EntitySelector.for_book(""))
    assert is_refusal(EntitySelector.for_bms(" "))
    assert is_refusal(EntitySelector.for_bot("bad-fp", "seat"))
    assert is_refusal(EntitySelector.for_bot(_BOT_DEF, ""))
    assert is_refusal(EntitySelector.for_binding("not-a-binding"))


def test_command_index_build_lookup_conflict_and_bad_fp() -> None:
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
    )
    index = _ok(CommandIndex.build([decision]))
    attribution = index.attribution_for(_CMD_A)
    assert attribution is not None
    assert attribution.binding.book_instance_id == _BOOK
    assert index.attribution_for(_CMD_B) is None

    # A byte-identical duplicate command record is idempotent.
    assert is_ok(CommandIndex.build([decision, decision]))

    # A conflicting attribution for one command fingerprint is refused.
    other = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value) | {"book_instance_id": "other-book"},
        outcome=DecisionOutcome.AUTHORIZED,
    )
    assert is_refusal(CommandIndex.build([decision, other]))

    # A malformed command fingerprint on a command record is refused.
    bad = _event(
        "decision", _binding_fields(command_fingerprint="nope"), outcome=DecisionOutcome.AUTHORIZED
    )
    assert is_refusal(CommandIndex.build([bad]))

    # A command record carrying a command fp but no binding is refused.
    no_binding = _event("promotion", {"command_fingerprint": _CMD_A.value, "role": "live"})
    assert is_refusal(CommandIndex.build([no_binding]))

    # An empty index (default) resolves nothing.
    assert CommandIndex().attribution_for(_CMD_A) is None


def test_entity_journal_requires_a_selector() -> None:
    refused = entity_journal([], selector="book-7")  # type: ignore[arg-type]
    assert is_refusal(refused)
    assert refused.context["field"] == "selector"


def test_convenience_wrappers_propagate_selector_refusals() -> None:
    assert is_refusal(book_journal([], ""))
    assert is_refusal(bms_journal([], ""))
    assert is_refusal(bot_logbook([], "bad-fp", "seat"))


def test_command_attribution_value() -> None:
    binding = _ok(
        BindingIdentity.try_create(
            book_instance_id=_BOOK,
            bms_instance_id=_BMS,
            venue_id=_VENUE,
            account_id=_ACCOUNT,
            world=World.LIVE,
        )
    )
    attribution = CommandAttribution(binding=binding)
    assert attribution.bot_seat is None
    assert attribution.binding.book_instance_id == _BOOK
