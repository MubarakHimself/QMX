"""Story 45.5 — Dialogue Runtime and Analysis RLM Runtime (FR-Q52)."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.control.runtime import (
    ANALYSIS_NOTEBOOK_TOOL_ID,
    CLIENT_SESSION_AXIS,
    DEFERRED_RUNTIME_EXCLUSIONS,
    LOOP_AND_STATE_CONTRACT,
    LOOP_AND_STATE_SURFACES,
    RLM_DEPTH_CAP_REGISTRY_KEY,
    RLM_HOST_TRANSPORT,
    RLM_KERNEL_INTERPRETER,
    RLM_KERNEL_PLACEMENT,
)
from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.refusals import NoEnvironment, UnknownHostRequest
from qma.core.vocabulary.enums import (
    ExecutionEnvironmentKind,
    ExecutionModel,
    JobHandleState,
    SessionAttachment,
    SessionAutonomy,
)
from qma.daemon.envs import ComputeRouter, ExecutionEnvironmentRegistry
from qma.daemon.envs.runtime import DIALOGUE_RUNTIME, RLM_RUNTIME, RuntimeService
from qmf.core import is_ok, is_refusal


def _quant(desk: DeskSlug, slug: str) -> Quant:
    minted = ActorId.mint(desk, slug)
    assert is_ok(minted)
    role = {
        DeskSlug.RESEARCH: RoleName.RESEARCHER,
        DeskSlug.TRADING: RoleName.TRADER,
        DeskSlug.DEV: RoleName.DEVELOPER,
        DeskSlug.ANALYSIS: RoleName.ANALYST,
        DeskSlug.PM: RoleName.PRODUCT_MANAGER,
    }[desk]
    return Quant(
        actor_id=minted.value,
        desk=desk,
        quant_slug=slug,
        role=role,
        name=f"Quant {slug}",
    )


def _docker_service() -> RuntimeService:
    envs = ExecutionEnvironmentRegistry()
    assert is_ok(
        envs.register_declaration(
            ExecutionEnvironmentDeclaration.isolated(
                ExecutionEnvironmentKind.DOCKER,
                provider_ref="local-docker",
            )
        )
    )
    router = ComputeRouter(environments=envs)
    return RuntimeService(environments=envs, router=router)


def _analysis_scope(task_id: str, session_id: str) -> tuple[dict[str, str], ...]:
    return (
        {"kind": "desk", "id": "analysis"},
        {"kind": "quant", "id": "nova"},
        {"kind": "mission", "id": "m-1"},
        {"kind": "task", "id": task_id},
        {"kind": "session", "id": session_id},
        {"kind": "agent", "id": "agent-1"},
    )


def test_dialogue_every_desk_rlm_analysis_same_contract() -> None:
    service = RuntimeService()
    assert service.contract == LOOP_AND_STATE_CONTRACT
    assert service.dialogue.surfaces == service.rlm.surfaces == LOOP_AND_STATE_SURFACES
    assert DIALOGUE_RUNTIME.contract == RLM_RUNTIME.contract
    for desk in DeskSlug:
        available = service.available_models(desk)
        assert ExecutionModel.DIALOGUE in available
        selected = service.select(desk)
        assert is_ok(selected)
        assert selected.value.execution_model is ExecutionModel.DIALOGUE
        assert selected.value.kernel_placement is None
    rlm = service.select(DeskSlug.ANALYSIS, "rlm")
    assert is_ok(rlm)
    assert rlm.value.execution_model is ExecutionModel.RLM
    assert rlm.value.kernel_placement == RLM_KERNEL_PLACEMENT
    assert rlm.value.kernel_interpreter == RLM_KERNEL_INTERPRETER
    assert rlm.value.host_transport == RLM_HOST_TRANSPORT
    refused = service.select(DeskSlug.RESEARCH, ExecutionModel.RLM)
    assert is_refusal(refused)
    assert refused.context["gap"] == "GAP-0080"
    assert "GAP-0080" in service.deferred_exclusions


def test_durable_session_axes_and_client_attachment() -> None:
    service = RuntimeService()
    owner = _quant(DeskSlug.DEV, "dev1")
    opened = service.open_session(
        session_id="sess:dev",
        owner=owner,
        autonomy=SessionAutonomy.SEMI,
    )
    assert is_ok(opened)
    session = opened.value
    assert session.execution_model is ExecutionModel.DIALOGUE
    assert session.autonomy is SessionAutonomy.SEMI
    persisted = service.persist_session(session.id)
    assert is_ok(persisted)
    assert CLIENT_SESSION_AXIS not in persisted.value
    assert "attachment" not in persisted.value
    assert persisted.value["execution_model"] == "dialogue"
    attached = service.client_attachment(session.id)
    assert attached is not None
    assert attached.state is SessionAttachment.ATTACHED
    assert attached.to_payload()["durable"] is False
    detached = service.detach_client(session.id)
    assert is_ok(detached)
    assert detached.value.state is SessionAttachment.DETACHED
    still = service.session(session.id)
    assert still is not None
    assert still.execution_model is ExecutionModel.DIALOGUE
    restored = RuntimeService()
    loaded = restored.restore_session(dict(persisted.value))
    assert is_ok(loaded)
    assert restored.client_attachment(session.id) is None
    illegal = restored.restore_session({**dict(persisted.value), "attachment": "attached"})
    assert is_refusal(illegal)


def test_rlm_kernel_is_persistent_python_in_worker_docker() -> None:
    service = _docker_service()
    owner = _quant(DeskSlug.ANALYSIS, "nova")
    opened = service.open_session(
        session_id="sess:rlm",
        owner=owner,
        requested_model=ExecutionModel.RLM,
    )
    assert is_ok(opened)
    daemon = service.start_rlm_kernel(
        session_id="sess:rlm",
        task_id="task:rlm",
        in_daemon_process=True,
    )
    assert is_refusal(daemon)
    kernel = service.start_rlm_kernel(session_id="sess:rlm", task_id="task:rlm")
    assert is_ok(kernel)
    assert kernel.value.interpreter == "persistent_python"
    assert kernel.value.placement == "worker_docker_container"
    assert kernel.value.host_transport == "qma-wire"
    assert kernel.value.in_daemon_process is False
    assert kernel.value.environment_kind == "docker"


def test_host_request_uses_qma_wire_and_returns_job_handle() -> None:
    service = _docker_service()
    owner = _quant(DeskSlug.ANALYSIS, "nova")
    assert is_ok(
        service.open_session(
            session_id="sess:hr",
            owner=owner,
            requested_model="rlm",
        )
    )
    assert is_ok(service.start_rlm_kernel(session_id="sess:hr", task_id="t-hr"))
    unknown = service.accept_host_request(
        session_id="sess:hr",
        verb="invented_spawn",
        scope_path=_analysis_scope("t-hr", "sess:hr"),
        correlation_id="corr-hr",
        producer_id="worker-1",
        id="hr-1",
        v="1.0.0",
        owner=owner,
    )
    assert is_refusal(unknown)
    assert UnknownHostRequest.matches(unknown)

    alt = service.accept_host_request(
        session_id="sess:hr",
        verb="message_send",
        scope_path=_analysis_scope("t-hr", "sess:hr"),
        correlation_id="corr-hr",
        producer_id="worker-1",
        id="hr-2",
        v="1.0.0",
        owner=owner,
        transport="stdio_jsonl",
    )
    assert is_refusal(alt)

    accepted = service.accept_host_request(
        session_id="sess:hr",
        verb="subagent_spawn",
        scope_path=_analysis_scope("t-hr", "sess:hr"),
        correlation_id="corr-hr",
        producer_id="worker-1",
        id="hr-3",
        v="1.0.0",
        owner=owner,
        job_id="job:spawn-1",
        current_spawn_depth=0,
    )
    assert is_ok(accepted)
    assert accepted.value.host_transport == RLM_HOST_TRANSPORT
    assert accepted.value.emission.mapping.before_hook == "before_subagent_spawn"
    handle = accepted.value.job_handle
    assert handle is not None
    assert handle.job_id == "job:spawn-1"
    assert handle.state is JobHandleState.QUEUED
    assert handle.owner == owner.actor_id

    over = service.accept_host_request(
        session_id="sess:hr",
        verb="env_create",
        scope_path=_analysis_scope("t-hr-2", "sess:hr"),
        correlation_id="corr-hr",
        producer_id="worker-1",
        id="hr-4",
        v="1.0.0",
        owner=owner,
        current_spawn_depth=2,
    )
    assert is_refusal(over)
    assert over.context["gap"] == "GAP-0080"
    assert over.context["registry_key"] == RLM_DEPTH_CAP_REGISTRY_KEY
    cap = service.depth_cap()
    assert is_ok(cap)
    assert cap.value == 2
    assert service.depth_cap_key == RLM_DEPTH_CAP_REGISTRY_KEY


def test_dialogue_does_not_issue_host_request() -> None:
    service = RuntimeService()
    owner = _quant(DeskSlug.PM, "pm1")
    opened = service.open_session(session_id="sess:pm", owner=owner)
    assert is_ok(opened)
    refused = service.accept_host_request(
        session_id="sess:pm",
        verb="tool",
        scope_path=_analysis_scope("t-pm", "sess:pm"),
        correlation_id="corr-pm",
        producer_id="w",
        id="x",
        v="1.0.0",
        owner=owner,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "execution_model"


def test_in_house_notebook_and_deferred_exclusions() -> None:
    service = RuntimeService()
    registered = service.register_analysis_notebook()
    assert is_ok(registered)
    assert registered.value == ANALYSIS_NOTEBOOK_TOOL_ID
    entry = service.notebook_entry()
    assert entry is not None
    assert "in-house" in entry.tags
    assert entry.schema["hosted"] is False
    hosted = service.register_analysis_notebook(provider="colab")
    assert is_refusal(hosted)
    assert hosted.context["field"] == "notebook"

    kernel_service = _docker_service()
    owner = _quant(DeskSlug.ANALYSIS, "nova")
    assert is_ok(
        kernel_service.open_session(
            session_id="sess:gap",
            owner=owner,
            requested_model="rlm",
        )
    )
    envelope = kernel_service.start_rlm_kernel(
        session_id="sess:gap",
        task_id="t-gap",
        measure_performance_envelope=True,
    )
    assert is_refusal(envelope)
    assert envelope.context["gap"] == "GAP-0076"
    vendor = kernel_service.start_rlm_kernel(
        session_id="sess:gap",
        task_id="t-gap",
        sandbox_vendor="modal",
    )
    assert is_refusal(vendor)
    assert vendor.context["gap"] == "GAP-0075"
    browser = kernel_service.start_rlm_kernel(
        session_id="sess:gap",
        task_id="t-gap",
        browser_stack="egolite",
    )
    assert is_refusal(browser)
    assert browser.context["gap"] == "GAP-0078"
    remote = kernel_service.start_rlm_kernel(
        session_id="sess:gap",
        task_id="t-gap",
        environment_kind=ExecutionEnvironmentKind.REMOTE_CONTAINER,
    )
    assert is_refusal(remote)
    assert remote.context["gap"] == "GAP-0075"
    for gap in ("GAP-0080", "GAP-0076", "GAP-0075", "GAP-0078"):
        assert gap in DEFERRED_RUNTIME_EXCLUSIONS
        assert DEFERRED_RUNTIME_EXCLUSIONS[gap]


def test_rlm_kernel_requires_docker_environment() -> None:
    service = RuntimeService()
    owner = _quant(DeskSlug.ANALYSIS, "nova")
    assert is_ok(
        service.open_session(
            session_id="sess:empty",
            owner=owner,
            requested_model="rlm",
        )
    )
    missing = service.start_rlm_kernel(session_id="sess:empty", task_id="t-empty")
    assert is_refusal(missing)
    assert NoEnvironment.matches(missing)


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "dialogue_rlm_runtime_usage.py"
    runpy.run_path(str(path), run_name="__main__")
