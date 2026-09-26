"""Reference usage — read-time entity-journal projections (logbooks) (Story 3.6).

Executable::

    python packages/qmf-data/examples/logbooks_usage.py

Shows the four things Story 3.6 pins down, all as read-time projections over the ONE
recorded set of writer-scoped journal streams (a risk-authored stream and a venue-authored
stream) — no entity mints a stream of its own:

1. Entity journals are read-time projections selected by entity identity: the Book journal
   for one BookInstanceId is extracted on demand from the recorded streams (AC1).
2. Risk-authored events carry the binding identity; venue-authored orders and fills carry
   only the command fingerprint and are joined into the Book projection through the pinned
   command-fingerprint join — Book identity is never threaded into the neutral venue
   payload (AC2).
3. Paper and live are separated by construction: a single-role read resolves inside one
   role-scoped namespace; a projection over an entity that operated in two roles refuses
   (FM-11) unless a cross-role read is declared (AC3).
4. The legacy five Records streams survive as projection names only, mapped onto the seven
   event types by the one versioned CT-25 table; veto_ledger selects on the decision's
   declared outcome = refused-by-door (AC4).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    AccountRole,
    Result,
    World,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.data import (
    BindingIdentity,
    CommandIndex,
    CrossRoleRead,
    DecisionOutcome,
    EntitySelector,
    EvidenceStore,
    JournalEvent,
    JournalReader,
    JournalWriter,
    book_journal,
    records_stream,
    role_namespace,
)

T = TypeVar("T")


def _fp_str(content: object) -> str:
    """The ``fp1:sha256:<hex>`` string for identity content (fingerprints come from core)."""
    result = fingerprint(content)
    if is_ok(result):
        return result.value.value
    raise AssertionError(f"failed to fingerprint {content!r}")


_VENUE = "venue-1"
_BOOK = "book-instance-7"
_BMS = "bms-instance-3"
_ACCOUNT = "acct-42"
_BOOK_DEF_FP = _fp_str({"book": "definition-v1"})
_CMD_ORDER = _fp_str({"command": "place-order", "n": 1})
_CMD_VETO = _fp_str({"command": "place-order", "n": 2})


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def _require(condition: object, what: str) -> None:
    if not condition:
        raise AssertionError(f"expected {what}")


def _writer(role: str) -> WriterId:
    return _unwrap(WriterId.try_create("node-a", role, role, "boot-1"), "writer")


def _binding_payload(role: AccountRole) -> dict[str, object]:
    """The binding identity fields a risk-authored event carries (AC2)."""
    return {
        "book_instance_id": _BOOK,
        "bms_instance_id": _BMS,
        "venue_id": _VENUE,
        "account_id": _ACCOUNT,
        "book_definition_fp": _BOOK_DEF_FP,
        "role": role.value,
    }


def _record_streams(store: EvidenceStore) -> list[JournalEvent]:
    """Write the one recorded set of writer-scoped streams (risk-authored + venue-authored)."""
    journal = _unwrap(store.for_world(World.LIVE), "live journal").journal
    risk = JournalWriter(journal, _writer("risk"), stream_name="risk")
    venue = JournalWriter(journal, _writer("venue"), stream_name="venue")

    # A live-role decision that authorizes a command (the command record, carrying binding).
    live_decision = _binding_payload(AccountRole.LIVE)
    live_decision["command_fingerprint"] = _CMD_ORDER
    _unwrap(
        risk.record("decision", live_decision, instant=1_000, outcome=DecisionOutcome.AUTHORIZED),
        "live authorized decision",
    )
    # A live-role control action on the same Book.
    _unwrap(
        risk.record_control_action(
            "kill-line-raised", instant=1_010, payload=_binding_payload(AccountRole.LIVE)
        ),
        "live control action",
    )
    # A refused-by-door decision (the veto_ledger projection selects on this outcome).
    veto = _binding_payload(AccountRole.LIVE)
    veto["refusing_door"] = "spread-door"
    veto["command_fingerprint"] = _CMD_VETO
    _unwrap(
        risk.record("decision", veto, instant=1_020, outcome=DecisionOutcome.REFUSED_BY_DOOR),
        "refused-by-door decision",
    )
    # A paper-benched decision on the SAME Book — a benched seat inside a live Book.
    _unwrap(
        risk.record(
            "decision",
            _binding_payload(AccountRole.PAPER_BENCHED),
            instant=1_030,
            outcome=DecisionOutcome.AUTHORIZED,
        ),
        "paper-benched decision",
    )

    # Venue-authored order + fill carrying ONLY the command fingerprint (no Book identity).
    _unwrap(
        venue.record("order", {"command_fingerprint": _CMD_ORDER, "role": "live"}, instant=1_005),
        "venue order",
    )
    _unwrap(
        venue.record(
            "fill",
            {"command_fingerprint": _CMD_ORDER, "role": "live", "fill_qty": 100},
            instant=1_006,
        ),
        "venue fill",
    )

    reader = JournalReader(journal)
    risk_events = _unwrap(reader.read("risk", for_world=World.LIVE), "risk stream")
    venue_events = _unwrap(reader.read("venue", for_world=World.LIVE), "venue stream")
    return [*risk_events, *venue_events]


def book_projection_with_join(all_events: list[JournalEvent]) -> tuple[int, list[str]]:
    """The Book journal, live namespace, joining venue orders/fills through the command fp."""
    index = _unwrap(CommandIndex.build(all_events), "command index")
    logbook = _unwrap(
        book_journal(all_events, _BOOK, role=AccountRole.LIVE, command_index=index),
        "live Book journal",
    )
    _require(
        logbook.roles == frozenset({AccountRole.LIVE}), "the live namespace holds only live rows"
    )
    classes = [row.event_class.value for row in logbook.rows]
    _require("venue-authored" in classes, "orders/fills joined into the Book projection")
    return len(logbook.rows), [row.event.event_type.value for row in logbook.rows]


def cross_role_guard(all_events: list[JournalEvent]) -> tuple[str, int]:
    """A multi-role Book refuses (FM-11) unless a cross-role read is declared (AC3)."""
    refused = book_journal(all_events, _BOOK)
    _require(is_refusal(refused), "aggregating across roles without a declaration is refused")
    category = refused.category.value if is_refusal(refused) else "unexpected-ok"

    declared = _unwrap(
        book_journal(all_events, _BOOK, cross_role=CrossRoleRead.MULTI_ROLE_ENTITY),
        "declared multi-role Book journal",
    )
    _require(
        declared.roles == frozenset({AccountRole.LIVE, AccountRole.PAPER_BENCHED}),
        "the declared cross-role read carries both roles",
    )
    return category, len(declared.roles)


def legacy_records_projections(all_events: list[JournalEvent]) -> tuple[list[str], int, int]:
    """The legacy five Records streams survive as projection names only (AC4)."""
    veto = _unwrap(records_stream(all_events, "veto_ledger"), "veto_ledger")
    trade = _unwrap(records_stream(all_events, "trade_journal"), "trade_journal")
    doors = [str(dict(event.payload).get("refusing_door", "")) for event in veto]
    return doors, len(veto), len(trade)


def namespaces_separate_paper_and_live() -> tuple[str, str]:
    """Each account role resolves in its own namespace; live is the live evidence namespace."""
    live = _unwrap(role_namespace(AccountRole.LIVE), "live namespace")
    benched = _unwrap(role_namespace(AccountRole.PAPER_BENCHED), "paper-benched namespace")
    _require(live != benched, "paper and live never share a namespace")
    return live, benched


def binding_is_generic_identity() -> bool:
    """The binding identity is a generic qmf-core-noun value, not a risk type."""
    binding = _unwrap(
        BindingIdentity.try_create(
            book_instance_id=_BOOK,
            bms_instance_id=_BMS,
            venue_id=_VENUE,
            account_id=_ACCOUNT,
            world=World.LIVE,
        ),
        "binding identity",
    )
    selector = _unwrap(EntitySelector.for_binding(binding), "binding selector")
    return selector.binding == binding


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="qmf-logbooks-") as tmp:
        store = EvidenceStore(Path(tmp) / "store")
        all_events = _record_streams(store)

        row_count, types = book_projection_with_join(all_events)
        print(f"live Book journal (join): {row_count} rows, types={types}")

        category, role_count = cross_role_guard(all_events)
        print(
            f"cross-role guard: refusal={category}; "
            f"declared multi-role read spans {role_count} roles"
        )

        doors, veto_n, trade_n = legacy_records_projections(all_events)
        print(
            f"veto_ledger (refused-by-door) doors={doors}; "
            f"trade_journal rows={trade_n}; veto rows={veto_n}"
        )

        live_ns, benched_ns = namespaces_separate_paper_and_live()
        print(f"role-scoped namespaces: live={live_ns!r}, paper-benched={benched_ns!r}")

        print(f"binding identity is generic qmf-core-noun value: {binding_is_generic_identity()}")


if __name__ == "__main__":
    main()
