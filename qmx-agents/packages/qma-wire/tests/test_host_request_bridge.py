"""Story 41.5 — RLM kernel host_request bridge contract (FR-Q19)."""

from __future__ import annotations

from qma.core.refusals import UnknownHostRequest
from qma.core.vocabulary import HOOK_EVENT_NAMES, JobHandleState
from qma.wire import (
    ALTERNATE_RLM_TRANSPORTS,
    HOST_REQUEST_BRIDGE_TRANSPORT,
    HOST_REQUEST_OWNING_AD,
    HOST_REQUEST_PRIMITIVE_MAP,
    HOST_REQUEST_VERBS,
    HOST_REQUEST_VOCABULARY_OWNER,
    JOB_HANDLE_NONTERMINAL_STATES,
    JOB_HANDLE_TERMINAL_STATES,
    RLM_DEPTH_CAP_DEFAULT,
    RLM_DEPTH_CAP_REGISTRY_KEY,
    JobHandleContract,
    MessageFamily,
    assert_no_alternate_rlm_transport,
    emit_host_request,
    enforce_spawn_depth,
    example_host_request_payloads,
    family_of,
    host_request_wire_family,
    parse_host_request_verb,
    parse_wire_type,
    resolve_host_request,
    validate_family_payload,
    validate_instance,
    validate_wire_envelope_dict,
)
from qma.wire.host_request import HostRequestVerbError
from qmf.core.refusal import Ok, is_ok, is_refusal

_TASK_SCOPE = (
    {"kind": "desk", "id": "analysis-1"},
    {"kind": "quant", "id": "q-1"},
    {"kind": "mission", "id": "m-1"},
    {"kind": "task", "id": "t-1"},
)


def test_ownership_and_registry_keys() -> None:
    assert HOST_REQUEST_VOCABULARY_OWNER == "qma-wire"
    assert HOST_REQUEST_OWNING_AD == "AD-14"
    assert HOST_REQUEST_BRIDGE_TRANSPORT == "qma-wire"
    assert RLM_DEPTH_CAP_REGISTRY_KEY == "rlm.depth_cap"
    assert RLM_DEPTH_CAP_DEFAULT == 2


def test_declared_verbs_map_one_to_one_onto_daemon_primitives() -> None:
    assert HOST_REQUEST_VERBS
    assert set(HOST_REQUEST_PRIMITIVE_MAP) == HOST_REQUEST_VERBS
    primitives: set[str] = set()
    for verb in HOST_REQUEST_VERBS:
        mapping = HOST_REQUEST_PRIMITIVE_MAP[verb]
        assert mapping.verb == verb
        assert mapping.daemon_primitive == verb
        assert mapping.before_hook == f"before_{mapping.daemon_primitive}"
        assert mapping.before_hook in HOOK_EVENT_NAMES
        assert mapping.wire_family in {"command", "query"}
        primitives.add(mapping.daemon_primitive)
        assert parse_host_request_verb(verb) == verb
    assert len(primitives) == len(HOST_REQUEST_VERBS)


def test_unmapped_verb_returns_unknown_host_request() -> None:
    refused = resolve_host_request("invented_spawn")
    assert is_refusal(refused)
    assert UnknownHostRequest.matches(refused)
    assert refused.context["verb"] == "invented_spawn"

    emission = emit_host_request(
        verb="invented_spawn",
        scope_path=_TASK_SCOPE,
        correlation_id="corr-1",
        producer_id="worker-1",
        id="hr-1",
        v="1.0.0",
    )
    assert is_refusal(emission)
    assert UnknownHostRequest.matches(emission)


def test_invented_verb_rejected_at_parse() -> None:
    try:
        parse_host_request_verb("invented_spawn")
        raise AssertionError("expected HostRequestVerbError")
    except HostRequestVerbError:
        pass


def test_host_call_is_wire_command_or_query_with_task_scope_and_correlation() -> None:
    result = emit_host_request(
        verb="ledger_append",
        scope_path=_TASK_SCOPE,
        correlation_id="corr-task-1",
        producer_id="analysis-worker",
        id="hr-ledger-1",
        v="1.0.0",
        args={"entry": "note"},
    )
    assert isinstance(result, Ok)
    emission = result.value
    assert emission.mapping.wire_family == "command"
    assert emission.before_hook == "before_ledger_append"
    envelope = emission.envelope
    assert envelope.correlation_id == "corr-task-1"
    assert [seg.kind for seg in envelope.scope_path] == [
        "desk",
        "quant",
        "mission",
        "task",
    ]
    assert envelope.type == "ledger_append"
    assert family_of(envelope.type) is MessageFamily.COMMAND
    assert host_request_wire_family("ledger_append") is MessageFamily.COMMAND
    assert parse_wire_type("ledger_append") == "ledger_append"
    assert envelope.payload["family"] == "host_request"
    assert envelope.payload["verb"] == "ledger_append"
    assert envelope.payload["before_hook"] == "before_ledger_append"
    assert is_ok(validate_wire_envelope_dict(envelope.to_dict()))


def test_query_classified_host_request_rides_query_family() -> None:
    result = emit_host_request(
        verb="graph_transition",
        scope_path=_TASK_SCOPE,
        correlation_id="corr-2",
        producer_id="analysis-worker",
        id="hr-q-1",
        v="1.0.0",
    )
    assert isinstance(result, Ok)
    assert result.value.mapping.wire_family == "query"
    assert family_of("graph_transition") is MessageFamily.QUERY
    assert result.value.async_result is None


def test_missing_task_scope_refused() -> None:
    refused = emit_host_request(
        verb="tool",
        scope_path=(
            {"kind": "desk", "id": "analysis-1"},
            {"kind": "quant", "id": "q-1"},
        ),
        correlation_id="corr-3",
        producer_id="w",
        id="hr-3",
        v="1.0.0",
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "scope_path"


def test_no_second_channel_or_shared_process_shortcut() -> None:
    assert is_ok(assert_no_alternate_rlm_transport("qma-wire"))
    for alt in ALTERNATE_RLM_TRANSPORTS:
        refused = assert_no_alternate_rlm_transport(alt)
        assert is_refusal(refused)
        assert refused.context["sanctioned"] == "qma-wire"

    emission = emit_host_request(
        verb="tool",
        scope_path=_TASK_SCOPE,
        correlation_id="corr-4",
        producer_id="w",
        id="hr-4",
        v="1.0.0",
        transport="shared_process",
    )
    assert is_refusal(emission)
    assert emission.context["field"] == "transport"


def test_async_spawn_returns_job_handle_not_fabricated_completion() -> None:
    result = emit_host_request(
        verb="subagent_spawn",
        scope_path=_TASK_SCOPE,
        correlation_id="corr-spawn",
        producer_id="w",
        id="spawn-1",
        v="1.0.0",
        args={"prompt": "fan-out"},
        job_id="job:spawn-1",
        job_state=JobHandleState.QUEUED.value,
    )
    assert isinstance(result, Ok)
    assert result.value.mapping.returns_job_handle is True
    async_result = result.value.async_result
    assert async_result is not None
    handle = async_result.job_handle
    assert handle.job_id == "job:spawn-1"
    assert handle.state == "queued"
    assert handle.state in JOB_HANDLE_NONTERMINAL_STATES
    assert handle.state not in JOB_HANDLE_TERMINAL_STATES
    assert handle.correlation_id == "corr-spawn"
    assert async_result.before_hook == "before_subagent_spawn"
    assert result.value.envelope.payload["job_handle"] == handle.to_dict()

    fabricated = JobHandleContract.try_create(
        job_id="job:x",
        state="done",
        correlation_id="corr-spawn",
    )
    assert is_refusal(fabricated)
    assert fabricated.context["field"] == "state"

    completed_emission = emit_host_request(
        verb="subagent_spawn",
        scope_path=_TASK_SCOPE,
        correlation_id="corr-spawn",
        producer_id="w",
        id="spawn-2",
        v="1.0.0",
        job_state="failed",
    )
    assert is_refusal(completed_emission)


def test_spawn_depth_enforced_by_rlm_depth_cap() -> None:
    assert isinstance(enforce_spawn_depth(0, depth_cap=2), Ok)
    assert isinstance(enforce_spawn_depth(1, depth_cap=2), Ok)
    refused = enforce_spawn_depth(2, depth_cap=2)
    assert is_refusal(refused)
    assert refused.context["registry_key"] == RLM_DEPTH_CAP_REGISTRY_KEY
    assert refused.context["depth_cap"] == 2

    over = emit_host_request(
        verb="env_create",
        scope_path=_TASK_SCOPE,
        correlation_id="corr-d",
        producer_id="w",
        id="env-1",
        v="1.0.0",
        current_spawn_depth=2,
        depth_cap=RLM_DEPTH_CAP_DEFAULT,
    )
    assert is_refusal(over)
    assert over.context["field"] == "spawn_depth"


def test_schemas_and_examples_preserve_bridge_requirements() -> None:
    examples = example_host_request_payloads()
    assert len(examples) >= 3
    spawn_example = examples[0]
    assert spawn_example["family"] == "host_request"
    assert spawn_example["verb"] == "subagent_spawn"
    assert spawn_example["before_hook"] == "before_subagent_spawn"
    assert spawn_example["wire_family"] == "command"
    assert "job_handle" in spawn_example
    assert is_ok(validate_instance(dict(spawn_example), "host_request"))

    query_example = examples[1]
    assert query_example["wire_family"] == "query"
    assert is_ok(validate_instance(dict(query_example), "host_request"))

    refusal_example = examples[2]
    assert refusal_example["family"] == "host_request"
    assert refusal_example["refusal"]["variant"] == "UnknownHostRequest"

    assert is_ok(
        validate_family_payload(
            "message_send",
            {"family": "host_request", "verb": "message_send", "args": {}},
        )
    )
    # Unregistered host verb is not a wire type and does not mint an alternate transport.
    assert is_refusal(validate_family_payload("invented_spawn", {}))
