"""Reference usage — Task Graph edges persist in daemon sqlite (57.1)."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.ports.qmb import qmb_opens_daemon_sqlite
from qma.daemon.plugins import research_corpus_plugin_load_config
from qma.daemon.process import DaemonProcess
from qma.daemon.taskgraph import (
    DURABLE_EDGES_EXISTED_AT_INSPECT_SHA,
    OCCUPANCY_TABLE_MINTED,
    SECOND_SCHEDULER_MINTED,
    CompileRequest,
    CompileResult,
    GraphTemplate,
    GraphTemplateCatalog,
    MissionCompiler,
    claim_durable_edges_at_inspect_sha,
    refuse_qmb_occupancy_write,
    refuse_second_scheduler,
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
    assert DURABLE_EDGES_EXISTED_AT_INSPECT_SHA is False
    assert is_ok(claim_durable_edges_at_inspect_sha(False))
    assert is_refusal(claim_durable_edges_at_inspect_sha(True))
    assert OCCUPANCY_TABLE_MINTED is False
    assert SECOND_SCHEDULER_MINTED is False
    assert is_refusal(refuse_second_scheduler())
    assert is_refusal(refuse_qmb_occupancy_write())
    assert qmb_opens_daemon_sqlite() is False
    compiled = _compile()
    graph = compiled.task_graph
    assert graph.successor_ids("prepare") == ("survey",)
    with TemporaryDirectory() as raw:
        root = Path(raw)
        process = _compose(root, boot="boot-example")
        try:
            persisted = process.task_graphs.persist(graph)
            assert is_ok(persisted)
            print("persisted task_graph_state edges in daemon sqlite")
        finally:
            process.close()
        restarted = _compose(root, boot="boot-example-2")
        try:
            restored = restarted.task_graphs.get(graph.id)
            assert is_ok(restored)
            assert restored.value.successor_ids("prepare") == ("survey",)
            print("restart restored prepare->survey mapping=one")
        finally:
            restarted.close()


if __name__ == "__main__":
    main()
