"""Reference usage — crash-restart accepts one logical B (Story 59.2)."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from qma.core.refusals import BlindRetryRefused
from qma.core.vocabulary.enums import JobHandleState
from qma.daemon import OutboxRestartFixture, refuse_second_logical_b
from qma.daemon.taskgraph.restart_fixture import (
    OUTBOX_RESTART_NEW_SQLITE_CLASS,
    SECOND_LOGICAL_B_BRANCH,
)
from qma.wire import INVOCATION_ENVELOPE_IS_AUTHORITY, INVOCATION_ENVELOPE_REQUIRED_FIELDS
from qmf.core import is_ok, is_refusal


def main(root: Path | None = None) -> None:
    assert OUTBOX_RESTART_NEW_SQLITE_CLASS is False
    assert INVOCATION_ENVELOPE_IS_AUTHORITY is False
    duplicate = refuse_second_logical_b(logical_invocation_id="inv:dup")
    assert is_refusal(duplicate)
    assert duplicate.context["branch"] == SECOND_LOGICAL_B_BRANCH

    def _run(base: Path) -> None:
        j27 = OutboxRestartFixture(root=base / "j27")
        report = j27.crash_then_replay()
        assert is_ok(report)
        proven = report.value
        body = proven.to_payload()
        assert proven.outbox_row_count == 1
        assert proven.first_acceptance.replayed is False
        assert proven.replay_acceptance.replayed is True
        assert proven.dispatch_attempts >= 1
        assert body["outbox_row_count"] == 1
        envelope = proven.envelope.to_payload()
        for field in INVOCATION_ENVELOPE_REQUIRED_FIELDS:
            assert field in envelope
        assert envelope["logical_invocation_id"] == proven.logical_invocation_id
        second = refuse_second_logical_b(logical_invocation_id=proven.logical_invocation_id)
        assert is_refusal(second)

        j26 = OutboxRestartFixture(root=base / "j26")
        egress = j26.lost_egress_ack()
        assert is_ok(egress)
        assert egress.value.first_outcome.handle_state is JobHandleState.UNKNOWN
        assert egress.value.retry_outcome.handle_state is JobHandleState.UNKNOWN
        assert egress.value.retry_outcome.duplicated is False
        assert egress.value.side_effect_count == 1
        assert isinstance(egress.value.blind_retry, BlindRetryRefused)
        print("outbox restart fixture: one logical B after crash")

    if root is None:
        with TemporaryDirectory() as raw:
            _run(Path(raw))
    else:
        _run(root)


if __name__ == "__main__":
    main()
