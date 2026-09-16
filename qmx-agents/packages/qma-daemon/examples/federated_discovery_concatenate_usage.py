"""Reference usage — federated CT-44 + library.search concatenate (Story 52.2)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

from qma.daemon.discovery import (
    FEDERATED_SEARCH_OCCUPANCY,
    FederatedDiscoveryService,
    federated_search_identity,
)
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.knowledge import (
    KnowledgeService,
    KnowledgeSourceRegistry,
    PlainFileLibrarySource,
)
from qma.wire import ArtifactHit, KnowledgeHit
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


def main() -> None:
    identity = federated_search_identity()
    assert identity["occupancy"] == FEDERATED_SEARCH_OCCUPANCY == "none"
    assert identity["is_door_run"] is False
    assert identity["opens_fourth_store"] is False
    assert identity["qmb_opens_daemon_sqlite"] is False
    print("federated search occupancy=none; never a door run; no fourth store")

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "notes.md").write_text("swing-high near London\n", encoding="utf-8")

        registry = KnowledgeSourceRegistry()
        source = PlainFileLibrarySource(root_path=root, source_id="strats")
        assert is_ok(registry.bind("strats", source, plugin_id="example"))
        knowledge = KnowledgeService(registry, hooks=HookRegistry())
        snapped = knowledge.snapshot("strats")
        assert is_ok(snapped)

        facade = FederatedDiscoveryService(
            knowledge=knowledge,
            artifacts=_RecordingArtifactPort(),
        )
        found = facade.search("swing-high", source_id="strats", snapshot=snapped.value)
        assert is_ok(found)
        assert any(isinstance(hit, KnowledgeHit) for hit in found.value.hits)
        assert any(isinstance(hit, ArtifactHit) for hit in found.value.hits)
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
