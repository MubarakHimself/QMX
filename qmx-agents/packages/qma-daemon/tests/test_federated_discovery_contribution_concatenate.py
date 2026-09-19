"""Story 53.2 — concatenate live published_contributions(); pack contributes at enable."""

from __future__ import annotations

import ast
import inspect
from collections.abc import Mapping, Sequence
from pathlib import Path

from qma.core.plugins import PluginContext
from qma.core.ports.knowledge import (
    GAP_0073_KNOWLEDGE_HYBRID_INDEXING,
    CorpusSnapshot,
)
from qma.core.ports.qmb import qmb_opens_daemon_sqlite
from qma.daemon.discovery import (
    FEDERATED_SEARCH_IS_DOOR_RUN,
    FEDERATED_SEARCH_OCCUPANCY,
    FEDERATED_SEARCH_OPENS_FOURTH_STORE,
    FEDERATED_SEARCH_SURFACES,
    SURFACE_ARTIFACT_LIBRARY,
    SURFACE_KNOWLEDGE,
    SURFACE_PUBLISHED_CONTRIBUTIONS,
    FederatedDiscoveryService,
    federated_search_identity,
)
from qma.daemon.discovery import federated as federated_mod
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.knowledge import (
    KnowledgeService,
    KnowledgeSourceRegistry,
    PlainFileLibrarySource,
)
from qma.daemon.plugins import DaemonPluginContext, PluginLoader
from qma.wire import ArtifactHit, ContributionHit, KnowledgeHit
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.core.refusal import RefusalCategory

_FP1 = "fp1:sha256:" + ("ab" * 32)
_SRC = Path(federated_mod.__file__).resolve()
_LOADER_SRC = (
    Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "plugins" / "loader.py"
)
_EXAMPLE = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "federated_discovery_contribution_concatenate_usage.py"
)


def _corpus(tmp_path: Path) -> Path:
    root = tmp_path / "strats"
    root.mkdir()
    (root / "notes.md").write_text("liquidity sweep near London open\n", encoding="utf-8")
    return root


def _knowledge(tmp_path: Path) -> tuple[KnowledgeService, CorpusSnapshot]:
    registry = KnowledgeSourceRegistry()
    source = PlainFileLibrarySource(root_path=_corpus(tmp_path), source_id="strats")
    bound = registry.bind("strats", source, plugin_id="research-strats")
    assert is_ok(bound)
    service = KnowledgeService(registry, hooks=HookRegistry())
    snapped = service.snapshot("strats")
    assert is_ok(snapped)
    return service, snapped.value


class _FakeArtifactPort:
    def __init__(self, rows: Sequence[Mapping[str, object]] = ()) -> None:
        self.rows = tuple(rows)

    def search(
        self,
        *,
        kind: str | None = None,
        fp1: str | None = None,
        query: str | None = None,
    ) -> Result[Sequence[Mapping[str, object]]]:
        _ = (kind, fp1, query)
        return Ok(self.rows)


def _manifest(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "research-corpus",
        "version": "0.1.0",
        "qma_api": ">=0.1.0,<1.0.0",
        "desk": "research",
        "entrypoint": "research_corpus.activate",
        "dependencies": [],
        "contributions": [{"point": "tool", "local_id": "inspect"}],
        "contributes": [{"point": "tool", "local_id": "inspect"}],
        "permissions": [],
        "migrations": [],
    }
    base.update(overrides)
    return base


def _activate_inspect(ctx: PluginContext) -> None:
    assert isinstance(ctx, DaemonPluginContext)
    ctx.register_tool("inspect", {"name": "inspect"})


def _activate_cite(ctx: PluginContext) -> None:
    ctx.register_tool("cite", {"name": "cite"})


def test_identity_concatenates_three_surfaces_occupancy_none() -> None:
    identity = federated_search_identity()
    assert identity["occupancy"] == "none" == FEDERATED_SEARCH_OCCUPANCY
    assert identity["is_door_run"] is False is FEDERATED_SEARCH_IS_DOOR_RUN
    assert identity["opens_fourth_store"] is False is FEDERATED_SEARCH_OPENS_FOURTH_STORE
    assert identity["qmb_opens_daemon_sqlite"] is False
    assert qmb_opens_daemon_sqlite() is False
    assert identity["surfaces"] == list(FEDERATED_SEARCH_SURFACES)
    assert FEDERATED_SEARCH_SURFACES == (
        SURFACE_KNOWLEDGE,
        SURFACE_ARTIFACT_LIBRARY,
        SURFACE_PUBLISHED_CONTRIBUTIONS,
    )


def test_concatenates_knowledge_artifact_and_published_contributions(tmp_path: Path) -> None:
    knowledge, snap = _knowledge(tmp_path)
    loader = PluginLoader()
    enabled = loader.enable(_manifest(), activator=_activate_inspect)
    assert is_ok(enabled)
    artifacts = _FakeArtifactPort(({"fp1": _FP1, "kind": "saved-view"},))
    facade = FederatedDiscoveryService(
        knowledge=knowledge,
        artifacts=artifacts,
        contributions=loader,
    )
    result = facade.search("liquidity", source_id="strats", snapshot=snap)
    assert is_ok(result)
    body = result.value
    assert body.occupancy == "none"
    assert body.is_door_run is False
    assert body.opens_fourth_store is False
    assert body.qmb_opens_daemon_sqlite is False
    assert body.surfaces == FEDERATED_SEARCH_SURFACES

    knowledge_hits = [hit for hit in body.hits if isinstance(hit, KnowledgeHit)]
    artifact_hits = [hit for hit in body.hits if isinstance(hit, ArtifactHit)]
    contribution_hits = [hit for hit in body.hits if isinstance(hit, ContributionHit)]
    assert knowledge_hits
    assert len(artifact_hits) == 1
    assert artifact_hits[0].kind == "saved-view"
    assert artifact_hits[0].fp1.value == _FP1
    assert len(contribution_hits) == 1
    hit = contribution_hits[0]
    assert hit.hit_class == "contribution"
    assert hit.plugin_id == "research-corpus"
    assert hit.point == "tool"
    assert hit.qualified_id == "research-corpus:inspect"
    assert hit.package_id == "research-corpus"
    assert hit.package_version == "0.1.0"
    assert hit.availability == "enabled"
    assert hit.availability_revision == loader.availability_revision() == 1
    assert "fp1" not in hit.to_payload()
    assert "kind" not in hit.to_payload()

    first_artifact = next(i for i, item in enumerate(body.hits) if isinstance(item, ArtifactHit))
    first_contrib = next(i for i, item in enumerate(body.hits) if isinstance(item, ContributionHit))
    assert all(isinstance(item, KnowledgeHit) for item in body.hits[:first_artifact])
    assert first_contrib > first_artifact


def test_hybrid_ranked_semantic_unsupported_capability(tmp_path: Path) -> None:
    knowledge, snap = _knowledge(tmp_path)
    facade = FederatedDiscoveryService(
        knowledge=knowledge,
        artifacts=_FakeArtifactPort(),
        contributions=PluginLoader(),
    )
    for mode in ("hybrid", "semantic", "ranked"):
        refused = facade.search("liquidity", source_id="strats", snapshot=snap, mode=mode)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
        assert refused.context["gap"] == GAP_0073_KNOWLEDGE_HYBRID_INDEXING


def test_fourth_store_and_door_run_still_refused(tmp_path: Path) -> None:
    knowledge, snap = _knowledge(tmp_path)
    facade = FederatedDiscoveryService(knowledge=knowledge, artifacts=_FakeArtifactPort())
    fourth = facade.search("liquidity", source_id="strats", snapshot=snap, fourth_store=True)
    assert is_refusal(fourth)
    assert fourth.context.get("opens_fourth_store") is False


def test_enable_collision_keeps_previous_roster(tmp_path: Path) -> None:
    knowledge, snap = _knowledge(tmp_path)
    loader = PluginLoader()
    first = loader.enable(_manifest(), activator=_activate_inspect)
    assert is_ok(first)
    before = loader.published_contributions()
    before_rev = loader.availability_revision()
    before_ids = loader.loaded_ids()

    colliding = loader.enable(
        _manifest(
            id="research-notes",
            entrypoint="research_notes.activate",
            contributions=[{"point": "tool", "local_id": "inspect"}],
            contributes=[
                {
                    "point": "tool",
                    "local_id": "inspect",
                    "qualified_id": "research-corpus:inspect",
                }
            ],
        ),
        activator=_activate_inspect,
    )
    assert is_refusal(colliding)
    assert colliding.context.get("field") == "contributes"
    assert "colliding" in str(colliding.context.get("reason", ""))
    assert loader.published_contributions() == before
    assert loader.availability_revision() == before_rev
    assert loader.loaded_ids() == before_ids

    facade = FederatedDiscoveryService(
        knowledge=knowledge,
        artifacts=_FakeArtifactPort(),
        contributions=loader,
    )
    found = facade.search("liquidity", source_id="strats", snapshot=snap)
    assert is_ok(found)
    contribs = [hit for hit in found.value.hits if isinstance(hit, ContributionHit)]
    assert [hit.qualified_id for hit in contribs] == ["research-corpus:inspect"]
    assert all(hit.availability_revision == before_rev for hit in contribs)


def test_successful_enable_publishes_revision_atomically(tmp_path: Path) -> None:
    knowledge, snap = _knowledge(tmp_path)
    loader = PluginLoader()
    assert loader.availability_revision() == 0
    enabled = loader.enable(_manifest(), activator=_activate_inspect)
    assert is_ok(enabled)
    assert loader.availability_revision() == 1
    published = [row for row in loader.published_contributions() if row.qualified_id]
    assert published
    assert all(row.availability_revision == 1 for row in published)
    assert all(row.availability == "enabled" for row in published)

    second = loader.enable(
        _manifest(
            id="research-notes",
            entrypoint="research_notes.activate",
            contributions=[{"point": "tool", "local_id": "cite"}],
            contributes=[{"point": "tool", "local_id": "cite"}],
        ),
        activator=_activate_cite,
    )
    assert is_ok(second)
    assert loader.availability_revision() == 2
    by_id = {row.qualified_id: row for row in loader.published_contributions() if row.qualified_id}
    assert by_id["research-corpus:inspect"].availability_revision == 1
    assert by_id["research-notes:cite"].availability_revision == 2

    facade = FederatedDiscoveryService(
        knowledge=knowledge,
        artifacts=_FakeArtifactPort(),
        contributions=loader,
    )
    found = facade.search("liquidity", source_id="strats", snapshot=snap)
    assert is_ok(found)
    ids = {hit.qualified_id for hit in found.value.hits if isinstance(hit, ContributionHit)}
    assert ids == {"research-corpus:inspect", "research-notes:cite"}


def test_module_never_imports_qmb_or_opens_daemon_sqlite() -> None:
    for path in (_SRC, _LOADER_SRC):
        source = path.read_text(encoding="utf-8")
        assert "import qmb" not in source
        assert "from qmb" not in source
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.append(node.module)
        assert not any(name == "qmb" or name.startswith("qmb.") for name in imports)
    assert "admit_qmb_job" not in inspect.getsource(FederatedDiscoveryService)
    assert qmb_opens_daemon_sqlite() is False


def test_reference_usage_example_runs() -> None:
    import runpy

    namespace = runpy.run_path(str(_EXAMPLE))
    namespace["main"]()
