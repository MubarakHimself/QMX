"""Conformance examples for the RLM host_request bridge (Story 41.5 / FR-Q19)."""

from __future__ import annotations

from qma.core.refusals import UnknownHostRequest
from qma.wire import (
    HOST_REQUEST_BRIDGE_TRANSPORT,
    RLM_DEPTH_CAP_DEFAULT,
    RLM_DEPTH_CAP_REGISTRY_KEY,
    emit_host_request,
    example_host_request_payloads,
    resolve_host_request,
    validate_instance,
)
from qmf.core.refusal import Ok, is_ok, is_refusal

_TASK_SCOPE = (
    {"kind": "desk", "id": "analysis-main"},
    {"kind": "quant", "id": "analyst-1"},
    {"kind": "mission", "id": "agg-800"},
    {"kind": "task", "id": "task-fanout"},
)


def main() -> None:
    assert HOST_REQUEST_BRIDGE_TRANSPORT == "qma-wire"
    assert RLM_DEPTH_CAP_REGISTRY_KEY == "rlm.depth_cap"
    assert RLM_DEPTH_CAP_DEFAULT == 2

    spawn = emit_host_request(
        verb="subagent_spawn",
        scope_path=_TASK_SCOPE,
        correlation_id="corr-fanout-1",
        producer_id="analysis-worker-1",
        id="hr-spawn-1",
        v="1.0.0",
        args={"prompt": "aggregate 800 variants"},
        job_id="job:spawn-1",
        current_spawn_depth=0,
        depth_cap=RLM_DEPTH_CAP_DEFAULT,
    )
    assert isinstance(spawn, Ok)
    assert spawn.value.async_result is not None
    assert spawn.value.envelope.correlation_id == "corr-fanout-1"
    assert spawn.value.before_hook == "before_subagent_spawn"

    unknown = resolve_host_request("invented_spawn")
    assert is_refusal(unknown)
    assert UnknownHostRequest.matches(unknown)

    for example in example_host_request_payloads()[:2]:
        assert is_ok(validate_instance(dict(example), "host_request"))

    print("host_request bridge examples ok")


if __name__ == "__main__":
    main()
