"""L27 reference usage: Dialogue Runtime and Analysis RLM Runtime (Story 45.5)."""

from __future__ import annotations

from qma.core.control.runtime import (
    ANALYSIS_NOTEBOOK_TOOL_ID,
    LOOP_AND_STATE_CONTRACT,
    RLM_DEPTH_CAP_REGISTRY_KEY,
)
from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.refusals import UnknownHostRequest
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, ExecutionModel
from qma.daemon.envs import ComputeRouter, ExecutionEnvironmentRegistry
from qma.daemon.envs.runtime import RuntimeService
from qmf.core import is_ok, is_refusal


def main() -> None:
    envs = ExecutionEnvironmentRegistry()
    assert is_ok(
        envs.register_declaration(
            ExecutionEnvironmentDeclaration.isolated(
                ExecutionEnvironmentKind.DOCKER,
                provider_ref="local-docker",
            )
        )
    )
    service = RuntimeService(environments=envs, router=ComputeRouter(environments=envs))
    assert service.dialogue.contract == service.rlm.contract == LOOP_AND_STATE_CONTRACT

    research = ActorId.mint(DeskSlug.RESEARCH, "alpha")
    assert is_ok(research)
    research_quant = Quant(
        actor_id=research.value,
        desk=DeskSlug.RESEARCH,
        quant_slug="alpha",
        role=RoleName.RESEARCHER,
        name="Quant alpha",
    )
    dialogue = service.open_session(session_id="sess:research", owner=research_quant)
    assert is_ok(dialogue)
    assert dialogue.value.execution_model is ExecutionModel.DIALOGUE
    persisted = service.persist_session("sess:research")
    assert is_ok(persisted)
    assert "attachment" not in persisted.value
    assert is_refusal(service.select(DeskSlug.RESEARCH, "rlm"))

    analysis = ActorId.mint(DeskSlug.ANALYSIS, "nova")
    assert is_ok(analysis)
    analysis_quant = Quant(
        actor_id=analysis.value,
        desk=DeskSlug.ANALYSIS,
        quant_slug="nova",
        role=RoleName.ANALYST,
        name="Quant nova",
    )
    rlm = service.open_session(
        session_id="sess:analysis",
        owner=analysis_quant,
        requested_model="rlm",
    )
    assert is_ok(rlm)
    kernel = service.start_rlm_kernel(session_id="sess:analysis", task_id="t-1")
    assert is_ok(kernel)
    assert kernel.value.placement == "worker_docker_container"
    assert kernel.value.in_daemon_process is False

    scope = (
        {"kind": "desk", "id": "analysis"},
        {"kind": "quant", "id": "nova"},
        {"kind": "mission", "id": "m-1"},
        {"kind": "task", "id": "t-1"},
        {"kind": "session", "id": "sess:analysis"},
        {"kind": "agent", "id": "a-1"},
    )
    unknown = service.accept_host_request(
        session_id="sess:analysis",
        verb="invented_spawn",
        scope_path=scope,
        correlation_id="corr-1",
        producer_id="w",
        id="hr-1",
        v="1.0.0",
        owner=analysis_quant,
    )
    assert is_refusal(unknown)
    assert UnknownHostRequest.matches(unknown)
    spawn = service.accept_host_request(
        session_id="sess:analysis",
        verb="subagent_spawn",
        scope_path=scope,
        correlation_id="corr-1",
        producer_id="w",
        id="hr-2",
        v="1.0.0",
        owner=analysis_quant,
        job_id="job:spawn-1",
    )
    assert is_ok(spawn)
    assert spawn.value.job_handle is not None
    over = service.accept_host_request(
        session_id="sess:analysis",
        verb="env_create",
        scope_path=scope,
        correlation_id="corr-1",
        producer_id="w",
        id="hr-3",
        v="1.0.0",
        owner=analysis_quant,
        current_spawn_depth=2,
    )
    assert is_refusal(over)
    assert over.context["registry_key"] == RLM_DEPTH_CAP_REGISTRY_KEY
    assert over.context["gap"] == "GAP-0080"

    notebook = service.register_analysis_notebook()
    assert is_ok(notebook)
    assert notebook.value == ANALYSIS_NOTEBOOK_TOOL_ID
    assert is_refusal(service.register_analysis_notebook(provider="colab"))
    assert is_refusal(
        service.start_rlm_kernel(
            session_id="sess:analysis",
            task_id="t-perf",
            measure_performance_envelope=True,
        )
    )
    print("Dialogue every desk, RLM Analysis kernel over host_request, gaps deferred")


if __name__ == "__main__":
    main()
