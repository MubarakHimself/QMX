"""Reference usage — suppression and veto accounting (Story 19.3).

Executable::

    python qmb/examples/accounting_usage.py

Shows the things R-RPT-8 / R-RPT-3 pin down:

1. Tallies fold only from the run's CT-13 journal streams, never a parallel log.
2. A quiet run still emits explicit zero counts — keys are never omitted.
3. Each count carries the AD-40 ``count`` unit-kind, in a field group apart from
   returns/trade measures.
4. Unresolvable authority or reason is a typed refusal, never dropped or bucketed.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.results import (
    MEASURE_IDENTITIES,
    TALLY_FIELD_GROUP,
    TALLY_UNIT_KIND,
    VETO_DOOR_IDENTITIES,
    assemble_suppression_and_veto_accounting,
)
from qmf.core.chrono import WriterId
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import World
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.data.journal import DecisionOutcome, JournalEvent, JournalEventType
from qmf.risk.control_action import AuthorityKind

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _writer() -> WriterId:
    return _unwrap(WriterId.try_create("qmb-replay", "risk", "decisions", "boot-1"), "writer")


def _event(
    *,
    sequence: int,
    payload: dict[str, object],
    outcome: object | None = None,
    event_type: object = JournalEventType.DECISION,
) -> JournalEvent:
    return _unwrap(
        JournalEvent.try_create(
            event_type=event_type,
            writer=_writer(),
            sequence=sequence,
            instant=_NS + sequence,
            world=World.REPLAY,
            payload=payload,
            outcome=outcome,
        ),
        "journal event",
    )


def quiet_run_keeps_every_key_at_zero() -> None:
    """No suppressions and no vetoes still list every closed key at count zero."""
    suppressions, vetoes = _unwrap(assemble_suppression_and_veto_accounting(), "quiet tally")
    assert all(row.count == 0 for row in suppressions)
    assert all(row.count == 0 for row in vetoes)
    assert {row.door_identity for row in vetoes} == set(VETO_DOOR_IDENTITIES)
    assert all(row.fp1_identity()["unit_kind"] == UnitKind.COUNT.value for row in suppressions)
    assert all(row.fp1_identity()["unit_kind"] == UnitKind.COUNT.value for row in vetoes)
    print("quiet run keeps explicit zero counts; keys are never omitted")


def journals_attribute_control_versus_strategy() -> None:
    """Door vetoes and arbitration suppressions are counted from CT-13 only."""
    veto = _event(
        sequence=0,
        outcome=DecisionOutcome.REFUSED_BY_DOOR,
        payload={"refusing_door": "control-window"},
    )
    suppressed = _event(
        sequence=1,
        outcome=DecisionOutcome.SUPPRESSED,
        payload={
            "suppressing_authority": AuthorityKind.OPERATOR.value,
            "reason_class": "conflict-higher-rank-wins",
        },
    )
    extra = _event(
        sequence=2,
        outcome=DecisionOutcome.REFUSED_BY_DOOR,
        payload={"refusing_door": "spread-door"},
    )
    suppressions, vetoes = _unwrap(
        assemble_suppression_and_veto_accounting((veto, suppressed, extra)),
        "journal tally",
    )
    by_suppression = {(row.authority, row.reason_class): row.count for row in suppressions}
    by_veto = {row.door_identity: row.count for row in vetoes}
    assert by_suppression[(AuthorityKind.OPERATOR, "conflict-higher-rank-wins")] == 1
    assert by_veto["control-window"] == 1
    assert by_veto["spread-door"] == 1
    assert by_veto["sqs"] == 0
    assert TALLY_UNIT_KIND is UnitKind.COUNT
    assert TALLY_FIELD_GROUP == "control-accounting"
    assert TALLY_FIELD_GROUP not in MEASURE_IDENTITIES
    print("tallies fold CT-13 journals; count unit-kind; distinct from measure_set")


def unresolvable_key_is_typed_refusal() -> None:
    """Missing/unknown authority or reason refuses rather than dropping the event."""
    bad = _event(
        sequence=0,
        outcome=DecisionOutcome.SUPPRESSED,
        payload={"suppressing_authority": "kill-switch", "reason_class": "kill_switch"},
    )
    refused = assemble_suppression_and_veto_accounting((bad,))
    assert is_refusal(refused)
    parallel = assemble_suppression_and_veto_accounting(
        ({"authority": "operator", "reason": "other", "count": 1},)
    )
    assert is_refusal(parallel)
    print("unresolvable authority is typed refusal; parallel log is refused")


def main() -> None:
    assert qmb.assemble_suppression_and_veto_accounting is assemble_suppression_and_veto_accounting
    assert qmb.TALLY_UNIT_KIND is TALLY_UNIT_KIND
    quiet_run_keeps_every_key_at_zero()
    journals_attribute_control_versus_strategy()
    unresolvable_key_is_typed_refusal()
    print("suppression and veto accounting ok")


if __name__ == "__main__":
    main()
