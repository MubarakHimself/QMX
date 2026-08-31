"""Story 41.1 — message families and seed vocabulary (FR-Q12, FR-Q21)."""

from __future__ import annotations

from pathlib import Path

import pytest
import qma.wire
from qma.core.vocabulary import HOOK_EVENT_NAMES
from qma.wire import (
    FAMILY_CONTRACTS,
    SEED_COMMAND_COUNT,
    SEED_EVENT_COUNT,
    SEED_QUERY_COUNT,
    SEED_VOCABULARY_COUNT,
    WIRE_COMMANDS,
    WIRE_EVENTS,
    WIRE_QUERIES,
    WIRE_VOCABULARY_OWNER,
    MessageFamily,
    WireCommand,
    WireEvent,
    WireQuery,
    WireVocabularyError,
    assert_client_close_safe,
    contract_for,
    contract_for_type,
    family_of,
    parse_wire_type,
    progress_is_authoritative,
    snapshots_are_authoritative,
    validate_family_payload,
)
from qmf.core.refusal import is_ok, is_refusal


def test_seed_vocabulary_counts_and_owner() -> None:
    assert WIRE_VOCABULARY_OWNER == "qma-wire"
    assert len(WIRE_COMMANDS) == SEED_COMMAND_COUNT == 9
    assert len(WIRE_QUERIES) == SEED_QUERY_COUNT == 7
    assert len(WIRE_EVENTS) == SEED_EVENT_COUNT == 10
    assert SEED_VOCABULARY_COUNT == 26
    assert {member.value for member in WireCommand} == WIRE_COMMANDS
    assert {member.value for member in WireQuery} == WIRE_QUERIES
    assert {member.value for member in WireEvent} == WIRE_EVENTS


def test_seed_members_match_ratified_packet() -> None:
    assert {
        "start_mission",
        "send_message",
        "steer_agent",
        "stop_run",
        "approve_hook_action",
        "install_enable_plugin",
        "update_configuration",
        "launch_task",
        "retry_task",
    } == WIRE_COMMANDS
    assert "get_quant" in WIRE_QUERIES
    assert "get_bot" not in WIRE_QUERIES
    assert {
        "agent.started",
        "message.delta",
        "tool.started",
        "task.completed",
        "hook.blocked",
        "ledger.updated",
        "mission.updated",
        "worker.detached",
        "provider.cooldown",
        "artifact.created",
    } == WIRE_EVENTS


def test_hook_names_are_not_wire_event_families() -> None:
    for name in HOOK_EVENT_NAMES:
        assert name not in WIRE_EVENTS
        with pytest.raises(WireVocabularyError):
            parse_wire_type(name)
    assert "before_tool" in HOOK_EVENT_NAMES
    assert "after_tool" in HOOK_EVENT_NAMES


def test_invented_wire_type_rejected() -> None:
    with pytest.raises(WireVocabularyError):
        parse_wire_type("invented.event")
    with pytest.raises(WireVocabularyError):
        family_of("start bot")


def test_family_transport_contracts() -> None:
    assert set(FAMILY_CONTRACTS) == {
        MessageFamily.COMMAND,
        MessageFamily.QUERY,
        MessageFamily.EVENT,
    }
    command = contract_for(MessageFamily.COMMAND)
    assert command.transport == "jsonrpc_websocket"
    assert command.mutates is True
    assert command.ack_immediate is True
    assert command.effects_async is True

    query = contract_for_type("get_quant")
    assert query.transport == "http_get"
    assert query.reads_durable_state is True
    assert query.mutates is False

    event = contract_for_type("agent.started")
    assert event.transport == "durable_stream"
    assert event.durable_stream is True
    assert event.authoritative is False


def test_snapshots_authoritative_progress_not_client_close_safe() -> None:
    assert snapshots_are_authoritative() is True
    assert progress_is_authoritative() is False
    assert assert_client_close_safe() is True


def test_family_payloads_validate_against_json_schema() -> None:
    assert is_ok(validate_family_payload("start_mission", {"goal": "x"}))
    assert is_ok(validate_family_payload("get_quant", {"quant_id": "q-1"}))
    assert is_ok(validate_family_payload("agent.started", {"agent_id": "a-1"}))
    assert is_refusal(validate_family_payload("before_tool", {}))


def test_ui_contract_remains_stub_only() -> None:
    stub = Path(__file__).resolve().parents[3] / "packages" / "qma-ui-contract" / "STUB.md"
    assert stub.is_file()
    text = stub.read_text(encoding="utf-8")
    assert "GAP-0081" in text
    assert "deferred" in text.lower()
    ui_pkg = stub.parent
    assert not (ui_pkg / "pyproject.toml").exists()
    assert not (ui_pkg / "src").exists()
    assert "qma-ui-contract" not in qma.wire.__all__
