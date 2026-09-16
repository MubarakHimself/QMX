"""Story 52.2 — concatenate CT-44 + library.search; no fourth store; no occupancy."""

from __future__ import annotations

import ast
import inspect
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from qma.core.ports.knowledge import (
    GAP_0073_KNOWLEDGE_HYBRID_INDEXING,
    CorpusSnapshot,
)
from qma.core.ports.qmb import qmb_opens_daemon_sqlite
from qma.daemon.discovery import (
    FEDERATED_SEARCH_HOLDS_CACHE,
    FEDERATED_SEARCH_IS_DOOR_RUN,
    FEDERATED_SEARCH_OCCUPANCY,
    FEDERATED_SEARCH_OPENS_FOURTH_STORE,
    FEDERATED_SEARCH_QMB_OPENS_DAEMON_SQLITE,
    FEDERATED_SEARCH_READS_STAGING,
    FEDERATED_SEARCH_SURFACES,
    FederatedDiscoveryService,
    federated_search_identity,
    refuse_copied_row_library_index,
    refuse_federated_fourth_store,
    refuse_federated_qma_staging_read,
    refuse_locator_as_fp1,
    refuse_unified_row_cache,
)
from qma.daemon.discovery import federated as federated_mod
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.knowledge import (
    KnowledgeService,
    KnowledgeSourceRegistry,
    PlainFileLibrarySource,
)
from qma.wire import (
    ArtifactHit,
    KnowledgeHit,
    library_kind_to_artifact_hit_kind,
)
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.core.refusal import RefusalCategory

_FP1 = "fp1:sha256:" + ("ab" * 32)
_FP1_B = "fp1:sha256:" + ("cd" * 32)
_SRC = Path(federated_mod.__file__).resolve()


def _corpus(tmp_path: Path) -> Path:
    root = tmp_path / "strats"
    root.mkdir()
    (root / "notes.md").write_text(
        "liquidity sweep near London open\nswing-high holds\n",
        encoding="utf-8",
    )
    (root / "ideas.md").write_text("unrelated note\n", encoding="utf-8")
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
    """Injected library.search stand-in — daemon never imports qmb."""

    def __init__(self, rows: Sequence[Mapping[str, object]] = ()) -> None:
        self.rows = tuple(rows)
        self.calls: list[dict[str, object | None]] = []

    def search(
        self,
        *,
        kind: str | None = None,
        fp1: str | None = None,
        query: str | None = None,
    ) -> Result[Sequence[Mapping[str, object]]]:
        self.calls.append({"kind": kind, "fp1": fp1, "query": query})
        return Ok(self.rows)


def test_identity_is_concatenate_with_occupancy_none() -> None:
    identity = federated_search_identity()
    assert identity["occupancy"] == "none"
    assert identity["is_door_run"] is False
    assert identity["opens_fourth_store"] is False
    assert identity["holds_cache"] is False
    assert identity["reads_staging"] is False
    assert identity["qmb_opens_daemon_sqlite"] is False
    assert identity["command"] == "facade_search"
    assert identity["surfaces"] == list(FEDERATED_SEARCH_SURFACES)
    assert identity["gap_0073"] == GAP_0073_KNOWLEDGE_HYBRID_INDEXING
    assert FEDERATED_SEARCH_OCCUPANCY == "none"
    assert FEDERATED_SEARCH_IS_DOOR_RUN is False
    assert FEDERATED_SEARCH_OPENS_FOURTH_STORE is False
    assert FEDERATED_SEARCH_HOLDS_CACHE is False
    assert FEDERATED_SEARCH_READS_STAGING is False
    assert FEDERATED_SEARCH_QMB_OPENS_DAEMON_SQLITE is False
    assert qmb_opens_daemon_sqlite() is False


def test_concatenates_knowledge_locators_and_artifact_fp1(tmp_path: Path) -> None:
    knowledge, snap = _knowledge(tmp_path)
    artifacts = _FakeArtifactPort(
        (
            {"fp1": _FP1, "kind": "bot-definition"},
            {"fp1": _FP1_B, "kind": "analysis-publication"},
            {"fp1": _FP1, "kind": "saved-view"},
        )
    )
    facade = FederatedDiscoveryService(knowledge=knowledge, artifacts=artifacts)

    result = facade.search("swing-high", source_id="strats", snapshot=snap, kind="bot-definition")
    assert is_ok(result)
    body = result.value
    assert body.occupancy == "none"
    assert body.is_door_run is False
    assert body.opens_fourth_store is False
    assert body.holds_cache is False
    assert body.reads_staging is False
    assert body.qmb_opens_daemon_sqlite is False
    assert body.surfaces == FEDERATED_SEARCH_SURFACES

    assert any(isinstance(hit, KnowledgeHit) for hit in body.hits)
    knowledge_hits = [hit for hit in body.hits if isinstance(hit, KnowledgeHit)]
    assert knowledge_hits
    assert all(hit.source_ref == "strats" for hit in knowledge_hits)
    assert all(hit.snapshot_ref == snap.id for hit in knowledge_hits)
    assert all("swing" in hit.locator or hit.locator.endswith(".md") for hit in knowledge_hits)

    artifact_hits = [hit for hit in body.hits if isinstance(hit, ArtifactHit)]
    assert len(artifact_hits) == 3
    assert artifact_hits[0].kind == "bot-definition"
    assert artifact_hits[1].kind == "analysis.published"
    assert artifact_hits[2].kind == "saved-view"
    assert library_kind_to_artifact_hit_kind("analysis-publication") == "analysis.published"

    # Knowledge first, then artifact — concatenate, not rank.
    first_artifact_idx = next(
        i for i, hit in enumerate(body.hits) if isinstance(hit, ArtifactHit)
    )
    assert all(isinstance(hit, KnowledgeHit) for hit in body.hits[:first_artifact_idx])

    assert artifacts.calls == [
        {"kind": "bot-definition", "fp1": None, "query": "swing-high"}
    ]
    payload = body.to_payload()
    assert payload["occupancy"] == "none"
    assert payload["is_door_run"] is False
    hits_payload = cast("Sequence[object]", payload["hits"])
    assert len(hits_payload) == len(body.hits)


def test_hybrid_semantic_ranked_is_unsupported_capability(tmp_path: Path) -> None:
    knowledge, snap = _knowledge(tmp_path)
    facade = FederatedDiscoveryService(knowledge=knowledge, artifacts=_FakeArtifactPort())
    for mode in ("hybrid", "semantic", "ranked", "embeddings"):
        refused = facade.search(
            "swing-high",
            source_id="strats",
            snapshot=snap,
            mode=mode,
        )
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
        assert refused.context["gap"] == GAP_0073_KNOWLEDGE_HYBRID_INDEXING
        assert refused.context.get("mode") == mode


def test_fourth_store_staging_and_unified_cache_refused(tmp_path: Path) -> None:
    knowledge, snap = _knowledge(tmp_path)
    facade = FederatedDiscoveryService(knowledge=knowledge, artifacts=_FakeArtifactPort())

    fourth = facade.search(
        "swing-high",
        source_id="strats",
        snapshot=snap,
        fourth_store=True,
    )
    assert is_refusal(fourth)
    assert fourth.category is RefusalCategory.POLICY_REJECTION
    assert fourth.context.get("opens_fourth_store") is False

    staging = facade.search(
        "swing-high",
        source_id="strats",
        snapshot=snap,
        qma_staging={"row": 1},
    )
    assert is_refusal(staging)
    assert staging.context.get("reads_staging") is False

    cache = facade.search(
        "swing-high",
        source_id="strats",
        snapshot=snap,
        unified_row_cache={},
    )
    assert is_refusal(cache)
    assert cache.context.get("holds_cache") is False

    copied = facade.search(
        "swing-high",
        source_id="strats",
        snapshot=snap,
        copied_row_library_index=[],
    )
    assert is_refusal(copied)

    assert is_refusal(refuse_federated_fourth_store())
    assert is_refusal(refuse_federated_qma_staging_read())
    assert is_refusal(refuse_unified_row_cache())
    assert is_refusal(refuse_copied_row_library_index())


def test_locators_are_not_fp1_and_qmb_never_opens_sqlite(tmp_path: Path) -> None:
    knowledge, snap = _knowledge(tmp_path)
    artifacts = _FakeArtifactPort(({"locator": "notes.md", "kind": "bot-definition"},))
    facade = FederatedDiscoveryService(knowledge=knowledge, artifacts=artifacts)

    missing_fp1 = facade.search("liquidity", source_id="strats", snapshot=snap)
    assert is_refusal(missing_fp1)
    assert "locator" in str(missing_fp1.context.get("field", "locator"))

    bare = facade.search(
        "liquidity",
        source_id="strats",
        snapshot=snap,
        fp1="dictionary/swing-high.md",
    )
    assert is_refusal(bare)
    assert is_refusal(refuse_locator_as_fp1())
    assert qmb_opens_daemon_sqlite() is False
    assert FEDERATED_SEARCH_QMB_OPENS_DAEMON_SQLITE is False


def test_module_never_imports_qmb_or_admits_door_run() -> None:
    source = _SRC.read_text(encoding="utf-8")
    assert "import qmb" not in source
    assert "from qmb" not in source
    assert "admit_qmb_job" not in source
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    assert not any(name == "qmb" or name.startswith("qmb.") for name in imports)
    assert "admit_qmb_job" not in inspect.getsource(FederatedDiscoveryService)
