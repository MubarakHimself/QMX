"""Reference usage — three-surface concatenate including live contributions (Story 53.2)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

from qma.core.plugins import PluginContext
from qma.daemon.discovery import (
    FEDERATED_SEARCH_OCCUPANCY,
    FEDERATED_SEARCH_SURFACES,
    FederatedDiscoveryService,
    federated_search_identity,
)
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.knowledge import (
    KnowledgeService,
    KnowledgeSourceRegistry,
    PlainFileLibrarySource,
)
from qma.daemon.plugins import DaemonPluginContext, PluginLoader
from qma.wire import ArtifactHit, ContributionHit, KnowledgeHit
from qmf.core import Ok, Result, is_ok, is_refusal

_FP1 = "fp1:sha256:" + ("11" * 32)


class _RecordingArtifactPort:
    def search(
        self,
        *,
        kind: str | None = None,
        fp1: str | None = None,
        query: str | None = None,
    ) -> Result[Sequence[Mapping[str, object]]]:
        _ = (kind, fp1, query)
        return Ok(({"fp1": _FP1, "kind": "saved-view"},))


def _activate(ctx: PluginContext) -> None:
    assert isinstance(ctx, DaemonPluginContext)
    ctx.register_tool("inspect", {"name": "inspect"})


def main() -> None:
    identity = federated_search_identity()
    assert identity["occupancy"] == FEDERATED_SEARCH_OCCUPANCY == "none"
    assert identity["is_door_run"] is False
    assert identity["opens_fourth_store"] is False
    assert len(FEDERATED_SEARCH_SURFACES) == 3
    print("federated search occupancy=none; three surfaces; no fourth store")

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "notes.md").write_text("swing-high near London\n", encoding="utf-8")

        registry = KnowledgeSourceRegistry()
        source = PlainFileLibrarySource(root_path=root, source_id="strats")
        assert is_ok(registry.bind("strats", source, plugin_id="example"))
        knowledge = KnowledgeService(registry, hooks=HookRegistry())
        snapped = knowledge.snapshot("strats")
        assert is_ok(snapped)

        loader = PluginLoader()
        enabled = loader.enable(
            {
                "id": "research-corpus",
                "version": "0.1.0",
                "qma_api": ">=0.1.0,<1.0.0",
                "desk": "research",
                "entrypoint": "research_corpus.activate",
                "contributions": [{"point": "tool", "local_id": "inspect"}],
                "contributes": [{"point": "tool", "local_id": "inspect"}],
            },
            activator=_activate,
        )
        assert is_ok(enabled)
        assert loader.availability_revision() == 1

        facade = FederatedDiscoveryService(
            knowledge=knowledge,
            artifacts=_RecordingArtifactPort(),
            contributions=loader,
        )
        found = facade.search("swing-high", source_id="strats", snapshot=snapped.value)
        assert is_ok(found)
        assert any(isinstance(hit, KnowledgeHit) for hit in found.value.hits)
        assert any(isinstance(hit, ArtifactHit) for hit in found.value.hits)
        assert any(isinstance(hit, ContributionHit) for hit in found.value.hits)
        print(f"concatenated hits={len(found.value.hits)}")

        hybrid = facade.search(
            "swing-high",
            source_id="strats",
            snapshot=snapped.value,
            mode="hybrid",
        )
        assert is_refusal(hybrid)
        print("ranked/semantic/hybrid → unsupported-capability (GAP-0073)")


if __name__ == "__main__":
    main()
