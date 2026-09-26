"""Shared builders for CT-25 logbooks tests.

Loaded by sibling test modules via importlib under the first-party name
``qmf.data.tests.logbooks_cases`` so Skylos D222 does not treat the helper as a
hallucinated third-party import.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    AccountRole,
    Fingerprint,
    Result,
    World,
    WriterId,
    fingerprint,
    is_ok,
)
from qmf.data import DecisionOutcome, JournalEvent

T = TypeVar("T")

VENUE = "venue-1"
BOOK = "book-7"
BMS = "bms-3"
ACCOUNT = "acct-42"


def ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def fp(content: object) -> Fingerprint:
    return ok(fingerprint(content))


BOOK_DEF = fp({"book": "def"})
BOT_DEF = fp({"bot": "def"})
CMD_A = fp({"cmd": "a"})
CMD_B = fp({"cmd": "b"})


def writer(stream: str = "s") -> WriterId:
    return ok(WriterId.try_create("m", "r", stream, "boot-1"))


def binding_fields(role: AccountRole = AccountRole.LIVE, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "book_instance_id": BOOK,
        "bms_instance_id": BMS,
        "venue_id": VENUE,
        "account_id": ACCOUNT,
        "book_definition_fp": BOOK_DEF.value,
        "role": role.value,
    }
    payload.update(extra)
    return payload


def event(
    event_type: str,
    payload: dict[str, object],
    *,
    outcome: DecisionOutcome | None = None,
    world: World = World.LIVE,
    sequence: int = 0,
    instant: int = 1_000,
) -> JournalEvent:
    return ok(
        JournalEvent.try_create(
            event_type=event_type,
            writer=writer(),
            sequence=sequence,
            instant=instant,
            world=world,
            payload=payload,
            outcome=outcome,
        )
    )


def multi_role_events() -> list[JournalEvent]:
    live = event(
        "decision",
        binding_fields(AccountRole.LIVE),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    benched = event(
        "decision",
        binding_fields(AccountRole.PAPER_BENCHED),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=1,
    )
    return [live, benched]
