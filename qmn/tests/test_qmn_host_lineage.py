"""Story 25.4 — persist composition lineage and occurrence evidence (E12-F04)."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import TypeVar, cast

from qmf.core import World
from qmf.core.chrono import Instant, WriterId
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.data.store import EvidenceStore, RegistryRoom, StoreEngineError, jsonl_opener
from qmf.registry import EdgeType, RegistryPersistence, WriteOutcome
from qmn.host import (
    COMPOSITION_LINEAGE_STREAM,
    COMPOSITION_OCCURRENCE_KIND,
    LINEAGE_PERSIST_SURFACE,
    OCCURRENCE_LINEAGE_EDGE_TYPE,
    SealedComposition,
    carries_ledger_edge,
    continues_performance_edge,
    persist_composition_lineage,
    persist_explicit_lineage_edge,
)

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000
_QMN_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _fp(label: str) -> Fingerprint:
    return _ok(fingerprint({"class": "cite", "label": label}))


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer(boot: str = "boot-1") -> WriterId:
    return _ok(WriterId.try_create("node-a", "composition", "lineage", boot))


def _persistence(tmp_path: Path) -> RegistryPersistence:
    store = EvidenceStore(tmp_path / "store")
    return _ok(RegistryPersistence.open(store, World.LIVE))


def _cites(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "composition_fp": _fp("composition"),
        "config_version_fp": _fp("config-v1"),
        "definition_refs": (_fp("book-def"), _fp("bms-def")),
        "capability_profile_refs": (_fp("cap-profile"),),
        "deployment_tuple_fp": _fp("deploy-tuple"),
        "code_commit_fp": _fp("git-commit"),
        "calendar_identity_refs": (
            _fp("market-hours-cal"),
            _fp("day-boundary-cal"),
            _fp("news-cal"),
        ),
    }
    base.update(overrides)
    return base


class _RaisingMetadata:
    def put(self, digest: str, canonical: bytes, /, *, kind: str, format_version: int) -> None:
        raise StoreEngineError("disk full", engine="sqlite", detail={"digest": digest})

    def get(self, digest: str, /) -> bytes | None:
        raise StoreEngineError("read failed", engine="sqlite", detail={"digest": digest})

    def meta(self, digest: str, /) -> Mapping[str, object] | None:
        return None

    def digests(self) -> list[str]:
        return []


def _persistence_with_raising_records(tmp_path: Path) -> RegistryPersistence:
    store = EvidenceStore(tmp_path / "store")
    world_store = store.for_world(World.LIVE)
    assert is_ok(world_store)
    broken = RegistryRoom(
        World.LIVE,
        record_engine=_RaisingMetadata(),
        lineage_dir=tmp_path / "lineage",
        open_stream=jsonl_opener(),
    )
    return RegistryPersistence(store, replace(world_store.value, registry_room=broken))


def test_lineage_surface_markers() -> None:
    assert LINEAGE_PERSIST_SURFACE == "qmn.host"
    assert COMPOSITION_OCCURRENCE_KIND == "composition-occurrence"
    assert OCCURRENCE_LINEAGE_EDGE_TYPE is EdgeType.OCCURRENCE_OF
    assert COMPOSITION_LINEAGE_STREAM == "composition-lineage"
    sealed = SealedComposition()
    assert sealed.sealed is True
    assert sealed.ready is False


def test_persist_composition_occurrence_and_occurrence_of_edges(tmp_path: Path) -> None:
    persistence = _persistence(tmp_path)
    cites = _cites()
    receipt = _ok(
        persist_composition_lineage(
            **cites,
            persistence=persistence,
            writer=_writer(),
            sequence=0,
            created_at=_instant(),
        )
    )
    assert receipt.ready is True
    assert receipt.occurrence.kind == COMPOSITION_OCCURRENCE_KIND
    assert receipt.occurrence_outcome is WriteOutcome.STORED
    assert receipt.composition_fp == cites["composition_fp"]
    assert receipt.occurrence.at_birth_parent_refs == ()

    body = cast("Mapping[str, object]", receipt.occurrence.body["content"])
    assert "composition_fp" not in body
    assert body["config_version_fp"] == cast("Fingerprint", cites["config_version_fp"]).value

    targets = {edge.to_ref for edge in receipt.edges}
    assert cites["composition_fp"] in targets
    assert cites["config_version_fp"] in targets
    assert cites["deployment_tuple_fp"] in targets
    assert cites["code_commit_fp"] in targets
    for ref in cast("tuple[Fingerprint, ...]", cites["definition_refs"]):
        assert ref in targets
    for ref in cast("tuple[Fingerprint, ...]", cites["capability_profile_refs"]):
        assert ref in targets
    for ref in cast("tuple[Fingerprint, ...]", cites["calendar_identity_refs"]):
        assert ref in targets
    assert all(edge.edge_type is EdgeType.OCCURRENCE_OF for edge in receipt.edges)
    assert all(edge.from_ref == receipt.occurrence_fp for edge in receipt.edges)

    loaded = _ok(persistence.load_record(receipt.occurrence_fp, for_world=World.LIVE))
    assert loaded.stable_id == receipt.occurrence_fp
    edges = _ok(persistence.read_edges(COMPOSITION_LINEAGE_STREAM, for_world=World.LIVE))
    assert len(edges) == len(receipt.edges)
    persistence.close()


def test_sink_refusal_blocks_readiness_rather_than_losing_edge(tmp_path: Path) -> None:
    persistence = _persistence_with_raising_records(tmp_path)
    refused = persist_composition_lineage(
        **_cites(),
        persistence=persistence,
        writer=_writer(),
        sequence=0,
        created_at=_instant(),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    # No ready receipt — callers must not treat the boot as eligible.
    assert not hasattr(refused, "ready") or getattr(refused, "ready", False) is False
    persistence.close()


def test_changed_config_mints_new_occurrence_without_rewriting_prior(tmp_path: Path) -> None:
    persistence = _persistence(tmp_path)
    first = _ok(
        persist_composition_lineage(
            **_cites(config_version_fp=_fp("config-v1")),
            persistence=persistence,
            writer=_writer("boot-a"),
            sequence=0,
            created_at=_instant(),
        )
    )
    second = _ok(
        persist_composition_lineage(
            **_cites(
                composition_fp=_fp("composition-b"),
                config_version_fp=_fp("config-v2"),
                definition_refs=(_fp("book-def-v2"),),
            ),
            persistence=persistence,
            writer=_writer("boot-b"),
            sequence=0,
            created_at=_instant(_CREATED_NS + 1),
        )
    )
    assert first.occurrence_fp != second.occurrence_fp
    assert first.ready and second.ready

    prior = _ok(persistence.load_record(first.occurrence_fp, for_world=World.LIVE))
    assert prior.stable_id == first.occurrence_fp
    prior_body = cast("Mapping[str, object]", prior.body["content"])
    assert prior_body["config_version_fp"] == _fp("config-v1").value

    later = _ok(persistence.load_record(second.occurrence_fp, for_world=World.LIVE))
    later_body = cast("Mapping[str, object]", later.body["content"])
    assert later_body["config_version_fp"] == _fp("config-v2").value

    edges = _ok(persistence.read_edges(COMPOSITION_LINEAGE_STREAM, for_world=World.LIVE))
    first_edge_fps = {edge.edge_fingerprint for edge in first.edges}
    assert first_edge_fps.issubset({edge.edge_fingerprint for edge in edges})
    persistence.close()


def test_continues_performance_and_carries_ledger_are_explicit_and_independent(
    tmp_path: Path,
) -> None:
    binding_a = _fp("binding-a")
    binding_b = _fp("binding-b")
    writer = _writer()

    unsigned_perf = continues_performance_edge(
        from_ref=binding_b,
        to_ref=binding_a,
        writer=writer,
        human_signed=False,
    )
    assert is_refusal(unsigned_perf)
    assert unsigned_perf.category is RefusalCategory.POLICY_REJECTION

    unsigned_ledger = carries_ledger_edge(
        from_ref=binding_b,
        to_ref=binding_a,
        writer=writer,
        human_signed=False,
    )
    assert is_refusal(unsigned_ledger)

    perf = _ok(
        continues_performance_edge(
            from_ref=binding_b,
            to_ref=binding_a,
            writer=writer,
            human_signed=True,
        )
    )
    assert perf.edge_type is EdgeType.CONTINUES_PERFORMANCE

    ledger = _ok(
        carries_ledger_edge(
            from_ref=binding_b,
            to_ref=binding_a,
            writer=writer,
            human_signed=True,
        )
    )
    assert ledger.edge_type is EdgeType.CARRIES_LEDGER
    assert perf.edge_fingerprint != ledger.edge_fingerprint

    persistence = _persistence(tmp_path)
    # Persisting continues-performance alone never implies carries-ledger.
    _ok(persist_explicit_lineage_edge(edge=perf, persistence=persistence))
    edges = _ok(persistence.read_edges(COMPOSITION_LINEAGE_STREAM, for_world=World.LIVE))
    assert len(edges) == 1
    assert edges[0].edge_type is EdgeType.CONTINUES_PERFORMANCE
    assert all(edge.edge_type is not EdgeType.CARRIES_LEDGER for edge in edges)

    _ok(persist_explicit_lineage_edge(edge=ledger, persistence=persistence))
    edges = _ok(persistence.read_edges(COMPOSITION_LINEAGE_STREAM, for_world=World.LIVE))
    kinds = {edge.edge_type for edge in edges}
    assert EdgeType.CONTINUES_PERFORMANCE in kinds
    assert EdgeType.CARRIES_LEDGER in kinds
    persistence.close()


def test_non_persistence_argument_refuses() -> None:
    refused = persist_composition_lineage(
        **_cites(),
        persistence=object(),
        writer=_writer(),
        sequence=0,
        created_at=_instant(),
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "persistence"


def test_only_host_persists_composition_lineage() -> None:
    """Child packages never import lineage persistence or registry persistence."""
    banned_roots = (
        "loop",
        "venue",
        "order",
        "protection",
        "ledger",
        "paper",
        "reconcile",
        "seats",
        "promotion",
        "mis",
        "data",
        "time",
        "secrets",
        "config",
        "observability",
        "doors",
        "replay",
        "bench",
    )
    violations: list[str] = []
    banned_modules = (
        "qmf.registry",
        "qmn.host.registry_mint",
        "qmn.host.lineage_persist",
    )
    for package in banned_roots:
        root = _QMN_SRC / package
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or not node.module:
                    continue
                module = node.module
                if any(
                    module == banned or module.startswith(f"{banned}.")
                    for banned in banned_modules
                ):
                    violations.append(f"{path.relative_to(_QMN_SRC)}: imports {module}")
    assert violations == [], f"child/door lineage persist surface leak: {violations}"
