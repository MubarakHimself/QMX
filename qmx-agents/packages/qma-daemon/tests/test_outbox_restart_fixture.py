"""Story 59.2 — outbox restart fixture: one logical B after crash."""

from __future__ import annotations

import ast
import runpy
from pathlib import Path
from typing import cast

from qma.core.refusals import BlindRetryRefused
from qma.core.vocabulary.enums import JobHandleState
from qma.daemon import OutboxRestartFixture, refuse_second_logical_b
from qma.daemon.taskgraph import TASK_GRAPH_OUTBOX_TABLE, TASK_GRAPH_RECEIVER_TABLE
from qma.daemon.taskgraph.restart_fixture import (
    EGRESS_FIXTURE_OP_ID,
    OUTBOX_RESTART_FIXTURE_OWNER,
    OUTBOX_RESTART_NEW_SQLITE_CLASS,
    SECOND_LOGICAL_B_BRANCH,
)
from qma.wire import (
    INVOCATION_ENVELOPE_FIELDS,
    INVOCATION_ENVELOPE_IS_AUTHORITY,
    INVOCATION_ENVELOPE_REQUIRED_FIELDS,
)
from qmf.core import is_ok, is_refusal
from qmf.core.refusal import Result

_SRC = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "qma"
    / "daemon"
    / "taskgraph"
    / "restart_fixture.py"
)
_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "outbox_restart_fixture_usage.py"


def _ok[T](result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def test_crash_replays_unacked_and_accepts_b_once(tmp_path: Path) -> None:
    fixture = OutboxRestartFixture(root=tmp_path / "j27")
    report = _ok(fixture.crash_then_replay())
    assert fixture.owner == OUTBOX_RESTART_FIXTURE_OWNER == "COMP-QMA-DAEMON"
    assert fixture.new_sqlite_class is False
    assert report.outbox_row_count == 1
    assert report.dispatch_attempts >= 2
    assert report.first_acceptance.replayed is False
    assert report.replay_acceptance.replayed is True
    assert report.replay_acceptance.result == report.first_acceptance.result
    assert (
        report.replay_acceptance.receiver_acceptance_id
        == report.first_acceptance.receiver_acceptance_id
    )
    assert report.bound.envelope.logical_invocation_id == report.logical_invocation_id
    assert report.bound.is_authority is False
    assert INVOCATION_ENVELOPE_IS_AUTHORITY is False
    payload = report.envelope.to_payload()
    for field in INVOCATION_ENVELOPE_REQUIRED_FIELDS:
        assert field in payload
    assert set(payload) <= set(INVOCATION_ENVELOPE_FIELDS)
    assert payload["op_id"] == "qmb.analysis.project"
    assert report.successor_node_id == "survey"
    body = report.to_payload()
    assert body["outbox_row_count"] == 1
    assert body["acceptance_replayed"] is True


def test_second_logical_b_fails_the_fixture(tmp_path: Path) -> None:
    fixture = OutboxRestartFixture(root=tmp_path / "branch-a")
    report = _ok(fixture.crash_then_replay(slug="branch-a"))
    refused = refuse_second_logical_b(logical_invocation_id=report.logical_invocation_id)
    assert is_refusal(refused)
    assert refused.context["branch"] == SECOND_LOGICAL_B_BRANCH == "A"
    assert refused.context["fixture_failed"] is True
    assert refused.context["logical_invocation_id"] == report.logical_invocation_id
    assert report.outbox_row_count == 1


def test_lost_external_egress_ack_stays_unknown_without_duplicate(tmp_path: Path) -> None:
    fixture = OutboxRestartFixture(root=tmp_path / "j26")
    report = _ok(fixture.lost_egress_ack())
    assert report.envelope.op_id == EGRESS_FIXTURE_OP_ID
    assert report.envelope.effect_class.value == "external-egress"
    assert report.first_outcome.handle_state is JobHandleState.UNKNOWN
    assert report.retry_outcome.handle_state is JobHandleState.UNKNOWN
    assert report.retry_outcome.duplicated is False
    assert report.retry_outcome.disposition == "replay"
    assert report.side_effect_count == 1
    assert isinstance(report.blind_retry, BlindRetryRefused)
    assert report.blind_retry.context["reason"] == "external_egress_must_not_blind_retry"
    assert report.reconciled.disposition == "replay"
    assert report.reconciled.duplicated is False
    body = report.to_payload()
    assert body["side_effect_count"] == 1
    assert body["retry_duplicated"] is False
    assert body["first_handle_state"] == "unknown"


def test_no_new_sqlite_class_and_tables_stay_on_task_graph_state() -> None:
    assert OUTBOX_RESTART_NEW_SQLITE_CLASS is False
    tree = ast.parse(_SRC.read_text(encoding="utf-8"))
    assigned: dict[str, object] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
            and isinstance(node.value, (ast.Constant, ast.Tuple, ast.List))
        ):
            assigned[node.target.id] = ast.literal_eval(node.value)
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, (ast.Constant, ast.Tuple, ast.List))
        ):
            assigned[node.targets[0].id] = ast.literal_eval(node.value)
    assert assigned.get("OUTBOX_RESTART_NEW_SQLITE_CLASS") is False
    assert assigned.get("SECOND_LOGICAL_B_BRANCH") == "A"
    assert assigned.get("OUTBOX_RESTART_FIXTURE_OWNER") == "COMP-QMA-DAEMON"
    source = _SRC.read_text(encoding="utf-8")
    assert "CREATE TABLE" not in source
    assert TASK_GRAPH_OUTBOX_TABLE in source or "task_graphs" in source
    assert TASK_GRAPH_RECEIVER_TABLE in source or "accept_logical" in source


def test_module_never_imports_qmb() -> None:
    tree = ast.parse(_SRC.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    assert not any(name == "qmb" or name.startswith("qmb.") for name in imports)


def test_reference_usage_example_runs(tmp_path: Path) -> None:
    namespace = runpy.run_path(str(_EXAMPLE))
    main = cast("object", namespace["main"])
    assert callable(main)
    main(tmp_path / "example")
