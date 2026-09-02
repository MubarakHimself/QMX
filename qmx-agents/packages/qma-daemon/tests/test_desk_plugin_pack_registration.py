"""Story 48.4 — register the five desk plugin packs (FR-Q71)."""

from __future__ import annotations

from pathlib import Path

from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.plugins import (
    DESK_PLUGIN_PACK_IDS,
    PluginContext,
    assert_no_daemon_import,
    parse_plugin_manifest,
)
from qma.core.ports.capabilities import RoleBase
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.memory import MemoryCandidate
from qma.core.ports.qmb import QMB_BACKTEST_TOOL_ID, QMB_OWNED_CONCERNS
from qma.core.ports.refinement import ProposalState
from qma.core.vocabulary.enums import (
    ExecutionEnvironmentKind,
    GraphArtifactKind,
    JobHandleState,
    PrincipalClass,
)
from qma.daemon.capabilities.spawn import SpawnRequest
from qma.daemon.plugins import DeskPluginRoster, PluginLoader, default_plugins_root
from qma.daemon.taskgraph.compiler import CompileRequest
from qmf.core import is_ok, is_refusal

PLUGINS_ROOT = default_plugins_root()
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "desk_plugin_packs_usage.py"


def _activate_roster() -> DeskPluginRoster:
    roster = DeskPluginRoster()
    result = roster.activate()
    assert is_ok(result), result
    return roster


def test_plugins_root_holds_five_first_party_packs() -> None:
    assert sorted(p.name for p in PLUGINS_ROOT.iterdir() if p.is_dir()) == sorted(
        DESK_PLUGIN_PACK_IDS
    )
    assert_no_daemon_import(PLUGINS_ROOT)


def test_activate_registers_through_plugin_manifest_and_context() -> None:
    roster = _activate_roster()
    assert tuple(roster.loader.loaded_ids()) == DESK_PLUGIN_PACK_IDS
    published = roster.loader.published_contributions()
    by_plugin: dict[str, set[str]] = {}
    for row in published:
        by_plugin.setdefault(row.plugin_id, set()).add(row.qualified_id or row.point)
    assert "MemoryProvider" in by_plugin["research-corpus"]
    assert "KnowledgeSource" in by_plugin["research-corpus"]
    assert "research-corpus:search" in by_plugin["research-corpus"]
    assert "analysis-backtest:qmb" in by_plugin["analysis-backtest"]
    assert "dev-factory:plan" in by_plugin["dev-factory"]
    assert "trading-readonly:positions" in by_plugin["trading-readonly"]
    assert "pm-coordination:status" in by_plugin["pm-coordination"]
    research = roster.loader.get("research-corpus")
    assert research is not None
    assert isinstance(research.context, PluginContext)


def test_analysis_backtest_is_existing_qmb_door_adapter() -> None:
    roster = _activate_roster()
    service = roster.backtesting
    assert service.plugin_id == "analysis-backtest"
    assert service.tool_id == QMB_BACKTEST_TOOL_ID
    assert service.scheduling_authority is None
    assert service.parallelism is None
    assert service.backtest_state is None
    assert service.qmb_owned_concerns() == QMB_OWNED_CONCERNS
    assert is_refusal(service.set_parallelism(4))
    assert is_refusal(service.append_run_ledger({"line": 1}))
    assert is_refusal(service.store_artifact({"ct32": True}))
    assert is_refusal(service.import_qmb_package())

    docker = ExecutionEnvironmentDeclaration.isolated(
        ExecutionEnvironmentKind.DOCKER, provider_ref="local-docker"
    )
    assert is_ok(service.environments.register_declaration(docker))
    owner = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(owner)
    first = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=owner.value,
        task_id="task-pack-1",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:spec-1",
        evidence_ref="evidence:recorded-1",
    )
    assert is_ok(first), first
    second = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=owner.value,
        task_id="task-pack-2",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:spec-2",
        evidence_ref="evidence:recorded-2",
    )
    assert is_refusal(second)
    assert second.context["field"] == "qmb_job"
    done = service.observe_outcome(first.value.handle.job_id, JobHandleState.DONE)
    assert is_ok(done)


def test_money_path_act_refused_before_pack_registration_completes() -> None:
    loader = PluginLoader()
    raw = parse_plugin_manifest(
        {
            "id": "trading-readonly",
            "version": "0.1.0",
            "qma_api": ">=0.1.0,<1.0.0",
            "desk": "trading",
            "entrypoint": "daemon.plugin:activate",
            "contributions": [{"point": "tool", "local_id": "place-order"}],
        }
    )

    def money(ctx: PluginContext) -> None:
        ctx.register_tool(
            "place-order",
            {"name": "place_order", "acts": ("submit_order",)},
        )

    refused = loader.install(
        {
            "id": raw.id,
            "version": raw.version,
            "qma_api": raw.qma_api,
            "desk": raw.desk,
            "entrypoint": raw.entrypoint,
            "contributions": [{"point": "tool", "local_id": "place-order"}],
            "dependencies": [],
            "permissions": [],
            "migrations": [],
        },
        activator=money,
    )
    assert is_refusal(refused)
    assert "money-path" in str(refused.context["reason"])
    assert loader.get("trading-readonly") is None


def test_worker_template_qmf_venue_image_refused_at_registration() -> None:
    loader = PluginLoader()

    def venue(ctx: PluginContext) -> None:
        ctx.register_worker_template(
            "broker-worker",
            {
                "role_ref": "trader",
                "toolset_ref": "trading-readonly:readonly",
                "model_class": "WORKHORSE_GENERAL",
                "environment_ref": "env:docker",
                "compute_requirement": {"cpus": 1},
                "permission_set": ["read"],
                "image": "qmf-venue:latest",
            },
        )

    refused = loader.install(
        {
            "id": "trading-readonly",
            "version": "0.1.0",
            "qma_api": ">=0.1.0,<1.0.0",
            "desk": "trading",
            "entrypoint": "daemon.plugin:activate",
            "contributions": [{"point": "worker_template", "local_id": "broker-worker"}],
            "dependencies": [],
            "permissions": [],
            "migrations": [],
        },
        activator=venue,
    )
    assert is_refusal(refused)
    assert "reachability" in str(refused.context["reason"])


def test_graph_template_stays_stateless_daemon_owns_task_graph() -> None:
    roster = _activate_roster()
    template = roster.templates.get("research-corpus:survey")
    assert template is not None
    assert template.artifact_kind is GraphArtifactKind.GRAPH_TEMPLATE
    payload = template.to_payload()
    assert payload["stateless"] is True
    assert payload["runtime_state"] is None

    minted = ActorId.mint(DeskSlug.RESEARCH, "alpha")
    assert is_ok(minted)
    owner = Quant(
        actor_id=minted.value,
        desk=DeskSlug.RESEARCH,
        quant_slug="alpha",
        role=RoleName.RESEARCHER,
        name="Quant alpha",
    )
    roster.compiler.remember_quant(owner.actor_id)
    compiled = roster.compiler.compile(
        CompileRequest(
            goal=Goal(text="survey corpus"),
            owner=owner,
            graph_template_ref="research-corpus:survey",
            intent="survey corpus",
            require_decomposition_reasoning=False,
        )
    )
    assert is_ok(compiled), compiled
    graph = compiled.value.task_graph
    assert graph.artifact_kind is GraphArtifactKind.TASK_GRAPH
    assert graph.artifact_kind is not template.artifact_kind
    assert template.qualified_id == "research-corpus:survey"


def test_memory_admitted_refinement_applied_promote_refused() -> None:
    roster = _activate_roster()
    candidate = MemoryCandidate(
        provenance={"source": "research-corpus"},
        supporting_artifacts=("artifact:note-1",),
        scope="research",
        proposer="quant:research/alpha",
        occurrence_time=1,
    )
    admitted = roster.memory.admit("research", candidate)
    assert is_ok(admitted), admitted
    assert admitted.value.candidate is not None
    assert admitted.value.path == "bound_gate"
    assert is_refusal(roster.memory.promote_refused("research"))
    assert is_refusal(roster.refuse_promote(surface="memory"))

    accepted = roster.proposals.accept(
        summary="add skill overlay",
        rationale="desk pack refinement",
        expected_outcome="skill applied",
        edits=[
            {
                "kind": "skill",
                "operation": "create",
                "id": "research-corpus:survey-overlay",
                "content": {"summary": "overlay"},
            }
        ],
    )
    assert is_ok(accepted)
    assert accepted.value.state is ProposalState.STAGED
    applied = roster.proposals.apply(
        accepted.value.id,
        principal_class=PrincipalClass.OPERATOR,
    )
    assert is_ok(applied), applied
    assert applied.value.state is ProposalState.APPLIED
    assert is_refusal(roster.proposals.promote_refused(accepted.value.id))
    assert is_refusal(roster.refuse_promote())


def test_spawn_constrains_unpublished_pack_tools() -> None:
    roster = _activate_roster()
    minted = ActorId.mint(DeskSlug.RESEARCH, "alpha")
    assert is_ok(minted)
    ok_spawn = roster.spawn_constrained(
        SpawnRequest(
            agent_id="agent-pack-1",
            owner=minted.value,
            session_id="sess-1",
            role_base=RoleBase(
                role="Researcher",
                tool_ids=frozenset({"research-corpus:search"}),
            ),
        )
    )
    assert is_ok(ok_spawn)
    refused = roster.spawn_constrained(
        SpawnRequest(
            agent_id="agent-pack-2",
            owner=minted.value,
            session_id="sess-2",
            role_base=RoleBase(
                role="Researcher",
                tool_ids=frozenset({"research-corpus:search", "trading-readonly:submit_order"}),
            ),
        )
    )
    assert is_refusal(refused)
    assert "submit_order" in str(refused.context.get("extras", []))


def test_reference_usage_example_runs() -> None:
    import runpy

    namespace = runpy.run_path(str(EXAMPLE))
    namespace["main"]()
