"""Reference usage — one sqlite transaction publishes A-terminal, B-ready, outbox."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, JobHandleState, TaskMissionState
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.plugins import research_corpus_plugin_load_config
from qma.daemon.process import DaemonProcess
from qma.daemon.taskgraph import (
    OUTBOX_PROVES_EXACTLY_ONCE_EFFECT,
    OUTBOXES_MERGED,
    CompileRequest,
    CompileResult,
    GraphTemplate,
    GraphTemplateCatalog,
    JobHandleEvidence,
    MissionCompiler,
    TaskGraphDispatcher,
    refuse_merge_remote_worker_outbox,
)
from qmf.core import is_ok, is_refusal


def _quant() -> Quant:
    minted = ActorId.mint(DeskSlug.RESEARCH, "alpha")
    assert is_ok(minted)
    return Quant(
        actor_id=minted.value,
        desk=DeskSlug.RESEARCH,
        quant_slug="alpha",
        role=RoleName.RESEARCHER,
        name="Quant alpha",
    )


def _compile() -> CompileResult:
    owner = _quant()
    catalog = GraphTemplateCatalog()
    template = GraphTemplate(
        qualified_id="research-corpus:two-step",
        version="1",
        nodes=(
            {"id": "prepare", "kind": "task", "intent": "prepare"},
            {"id": "survey", "kind": "task", "intent": "survey"},
        ),
        edges=(
            {
                "from": "prepare",
                "to": "survey",
                "mapping": "one",
                "from_port": "data",
                "to_port": "data",
            },
        ),
    )
    assert is_ok(catalog.register(template))
    compiler = MissionCompiler(
        templates=catalog,
        known_quant_actor_ids={owner.actor_id.value},
    )
    compiled = compiler.compile(
        CompileRequest(
            goal=Goal(text="survey after prepare"),
            owner=owner,
            graph_template_ref="research-corpus:two-step",
        )
    )
    assert is_ok(compiled)
    return compiled.value


def _compose(root: Path, *, boot: str) -> DaemonProcess:
    seed = root / "seed-corpus"
    seed.mkdir(exist_ok=True)
    result = DaemonProcess.compose(
        root,
        machine="example-host",
        boot_epoch_id=boot,
        bind_port=0,
        plugin_load_configs=research_corpus_plugin_load_config(seed),
    )
    assert is_ok(result)
    return result.value


def main() -> None:
    assert OUTBOXES_MERGED is False
    assert OUTBOX_PROVES_EXACTLY_ONCE_EFFECT is False
    assert is_refusal(refuse_merge_remote_worker_outbox())
    compiled = _compile()
    with TemporaryDirectory() as raw:
        root = Path(raw)
        process = _compose(root, boot="boot-outbox")
        try:
            envs = ExecutionEnvironmentRegistry()
            assert is_ok(
                envs.register_declaration(
                    ExecutionEnvironmentDeclaration.isolated(
                        ExecutionEnvironmentKind.DOCKER,
                        provider_ref="local-docker",
                    )
                )
            )
            dispatcher = TaskGraphDispatcher(environments=envs, durable=process.task_graphs)
            dispatcher.materialize(compiled.task_graph, mission=compiled.mission)
            prepare = compiled.task_graph.ready_tasks()[0]
            assert is_ok(
                dispatcher.dispatch_task(
                    task_id=prepare.id,
                    holder_agent_id="agent-1",
                    environment_kind=ExecutionEnvironmentKind.DOCKER,
                )
            )
            applied = dispatcher.apply_job_handle_evidence(
                JobHandleEvidence(
                    job_id="job-a",
                    task_id=prepare.id,
                    state=JobHandleState.DONE,
                )
            )
            assert is_ok(applied)
            rows = process.task_graphs.outbox_rows(compiled.task_graph.id)
            assert len(rows) == 1
            print("published A-terminal, B-ready, and outbox in one sqlite transaction")
        finally:
            process.close()
        restarted = _compose(root, boot="boot-outbox-2")
        try:
            restored = restarted.task_graphs.get(compiled.task_graph.id)
            assert is_ok(restored)
            survey = restored.value.task_for_node("survey")
            assert survey is not None
            assert survey.state is TaskMissionState.READY
            pending = restarted.task_graphs.replayable_rows(compiled.task_graph.id)
            assert len(pending) == 1
            logical_id = pending[0].logical_invocation_id
            assert is_ok(restarted.task_graphs.ack_dispatch(logical_invocation_id=logical_id))
            first = restarted.task_graphs.accept_logical(logical_id, result={"ok": True})
            assert is_ok(first) and first.value.replayed is False
            second = restarted.task_graphs.accept_logical(logical_id, result={"ok": False})
            assert is_ok(second) and second.value.replayed is True
            print("restart replayed unacked outbox; receiver returned prior result")
        finally:
            restarted.close()


if __name__ == "__main__":
    main()
