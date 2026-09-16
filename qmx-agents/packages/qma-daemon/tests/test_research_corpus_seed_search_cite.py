"""Story 49.4 — search, retrieve, and cite STRAT-000001 and swing-high."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from qma.core.ports.knowledge import GAP_0073_KNOWLEDGE_HYBRID_INDEXING
from qma.core.refusals import ProvenanceShapeMismatch, StaleSnapshot
from qma.daemon.knowledge import (
    UNSCORED_CONFIDENCE_VALUE,
    KnowledgeService,
    PlainFileLibrarySource,
)
from qma.daemon.plugins import DeskPluginRoster, research_corpus_plugin_load_config
from qmf.core import is_ok, is_refusal
from qmf.core.refusal import RefusalCategory

OPERATOR_SEED = Path(r"C:/Users/Mubarak/Desktop/Stats")

_DIMS = (
    "extraction_confidence",
    "rule_explicitness",
    "source_quality_completeness",
    "ambiguity_unresolved_status",
    "empirical_status",
    "portability_market_transfer_status",
)

SWING_HIGH_PATH = "dictionary/market-structure-and-location/locations-and-structure.md"
SWING_HIGH_LOCATOR = f"{SWING_HIGH_PATH}#swing-high"
STRAT_IDENTITY = "strategies/STRAT-000001-asian-high-london-reversal/identity.md"
LIQUIDITY_SWEEP_LOCATION = (
    "dictionary/market-structure-and-location/locations-and-structure.md#liquidity-sweep"
)
LIQUIDITY_SWEEP_CONTEXT = (
    "dictionary/context-regime-and-intermarket/context-filters-confirmations.md#liquidity-sweep"
)
LIQUIDITY_SWEEP_TRIGGERS = (
    "dictionary/price-action-and-patterns/triggers-patterns-transitions.md#liquidity-sweep"
)
OPAQUE_LABEL = "source-stated/explicit"

_SEED_RELATIVE = (
    "README.md",
    "strategies/STRAT-000001-asian-high-london-reversal",
    SWING_HIGH_PATH,
    "dictionary/price-action-and-patterns/triggers-patterns-transitions.md",
    "dictionary/context-regime-and-intermarket/context-filters-confirmations.md",
)


def _copy_real_seed_bytes(tmp_path: Path) -> Path:
    """Copy STRAT-000001 and swing-high bytes from the operator seed (AR-RES-10)."""
    if not OPERATOR_SEED.is_dir():
        pytest.fail(
            "AR-RES-10 requires operator seed at C:/Users/Mubarak/Desktop/Stats "
            "or a fixture of bytes copied from that tree — not the two-file stub"
        )
    dest = tmp_path / "seed-corpus"
    dest.mkdir()
    for rel in _SEED_RELATIVE:
        src = OPERATOR_SEED / rel
        target = dest / rel
        if src.is_dir():
            shutil.copytree(src, target)
        elif src.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
        else:
            pytest.fail(f"AR-RES-10 seed path missing: {rel}")
    return dest


def _bind_copied_seed(
    tmp_path: Path,
) -> tuple[KnowledgeService, PlainFileLibrarySource, Path]:
    seed = _copy_real_seed_bytes(tmp_path)
    roster = DeskPluginRoster(plugin_load_configs=research_corpus_plugin_load_config(seed))
    result = roster.activate()
    assert is_ok(result), result
    loaded = roster.loader.get("research-corpus")
    assert loaded is not None
    source = loaded.context.snapshot()["singletons"][("KnowledgeSource", "strats")]
    assert isinstance(source, PlainFileLibrarySource)
    service = KnowledgeService()
    bound = service.bind("strats", source, plugin_id="research-corpus")
    assert is_ok(bound)
    return service, source, seed


def _locator_path(locator: str) -> str:
    return locator.split("#", 1)[0]


def test_literal_search_finds_strat_000001_and_swing_high_in_copied_seed(
    tmp_path: Path,
) -> None:
    service, _source, seed = _bind_copied_seed(tmp_path)
    snapped = service.snapshot("strats")
    assert is_ok(snapped)
    pin = service.pin_mission_snapshot("mission-49-4", "strats", snapped.value)
    assert is_ok(pin)
    digests = snapped.value.file_digests
    assert STRAT_IDENTITY in digests
    assert SWING_HIGH_PATH in digests
    assert "notes/liquidity.md" not in digests
    assert "notes/session.md" not in digests

    strat_hits = service.search("strats", snapped.value, "STRAT-000001")
    assert is_ok(strat_hits)
    assert STRAT_IDENTITY in strat_hits.value
    assert all(_locator_path(hit) in digests for hit in strat_hits.value)

    swing_hits = service.search("strats", snapped.value, "swing-high")
    assert is_ok(swing_hits)
    assert SWING_HIGH_PATH in swing_hits.value
    assert SWING_HIGH_LOCATOR in swing_hits.value
    assert all(_locator_path(hit) in digests for hit in swing_hits.value)

    by_locator = service.search("strats", snapped.value, SWING_HIGH_LOCATOR)
    assert is_ok(by_locator)
    assert by_locator.value == (SWING_HIGH_LOCATOR,)

    identity_bytes = (seed / STRAT_IDENTITY).read_bytes()
    assert b"LAYOUT-DEMO" in identity_bytes
    assert b"STRAT-000001" in identity_bytes
    assert b"entry_hypothesis" in identity_bytes
    assert (seed / SWING_HIGH_PATH).read_bytes().startswith(b"# Candidate Dictionary")


def test_hybrid_semantic_ranked_search_is_unsupported_capability(tmp_path: Path) -> None:
    service, _source, _seed = _bind_copied_seed(tmp_path)
    snapped = service.snapshot("strats")
    assert is_ok(snapped)
    for mode in ("hybrid", "semantic", "ranked", "embeddings"):
        refused = service.search("strats", snapped.value, "STRAT-000001", mode=mode)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
        assert refused.context["gap"] == GAP_0073_KNOWLEDGE_HYBRID_INDEXING
        assert refused.context.get("deferred") is True
        assert refused.context.get("mode") == mode


def test_cite_copies_strat_bytes_uncopied_retrieve_is_stale(tmp_path: Path) -> None:
    service, source, seed = _bind_copied_seed(tmp_path)
    original = (seed / STRAT_IDENTITY).read_bytes()
    snapped = service.snapshot("strats")
    assert is_ok(snapped)

    stale = service.retrieve("strats", snapped.value, STRAT_IDENTITY)
    assert is_refusal(stale)
    assert StaleSnapshot.matches(stale)
    assert stale.context["snapshot_ref"] == snapped.value.id

    cited = service.cite(
        "strats",
        snapped.value,
        STRAT_IDENTITY,
        evidence_label=OPAQUE_LABEL,
        authored_by="agent:research/quant/a1",
    )
    assert is_ok(cited)
    outcome = cited.value
    assert outcome.artifact.content == original
    assert b"LAYOUT-DEMO" in outcome.artifact.content
    assert b"entry_hypothesis" in outcome.artifact.content
    assert outcome.citation.locator == STRAT_IDENTITY
    resolved = service.resolve_citation(outcome.citation)
    assert is_ok(resolved)
    assert resolved.value == original

    retrieved = service.retrieve("strats", snapped.value, STRAT_IDENTITY)
    assert is_ok(retrieved)
    assert retrieved.value == original

    (seed / STRAT_IDENTITY).write_bytes(b"live-tree-must-not-substitute\n")
    source.invalidate_cache()
    still = service.resolve_citation(outcome.citation)
    assert is_ok(still)
    assert still.value == original
    assert still.value != (seed / STRAT_IDENTITY).read_bytes()


def test_swing_high_fragment_is_stripped_and_file_bytes_returned(tmp_path: Path) -> None:
    service, _source, seed = _bind_copied_seed(tmp_path)
    file_bytes = (seed / SWING_HIGH_PATH).read_bytes()
    snapped = service.snapshot("strats")
    assert is_ok(snapped)

    stale = service.retrieve("strats", snapped.value, SWING_HIGH_LOCATOR)
    assert is_refusal(stale)
    assert StaleSnapshot.matches(stale)

    cited = service.cite(
        "strats",
        snapped.value,
        SWING_HIGH_LOCATOR,
        evidence_label=OPAQUE_LABEL,
        authored_by="agent:research/quant/a1",
    )
    assert is_ok(cited)
    assert cited.value.citation.locator == SWING_HIGH_LOCATOR
    assert cited.value.artifact.content == file_bytes
    assert b"## swing-high" in cited.value.artifact.content
    retrieved = service.retrieve("strats", snapped.value, SWING_HIGH_LOCATOR)
    assert is_ok(retrieved)
    assert retrieved.value == file_bytes
    by_path = service.retrieve("strats", snapped.value, SWING_HIGH_PATH)
    assert is_ok(by_path)
    assert by_path.value == file_bytes


def test_colliding_slug_requires_file_path_and_id(tmp_path: Path) -> None:
    service, _source, seed = _bind_copied_seed(tmp_path)
    snapped = service.snapshot("strats")
    assert is_ok(snapped)
    hits = service.search("strats", snapped.value, "liquidity-sweep")
    assert is_ok(hits)
    for locator in (
        LIQUIDITY_SWEEP_LOCATION,
        LIQUIDITY_SWEEP_CONTEXT,
        LIQUIDITY_SWEEP_TRIGGERS,
    ):
        assert locator in hits.value

    colliding = service.cite(
        "strats",
        snapped.value,
        "liquidity-sweep",
        evidence_label=OPAQUE_LABEL,
        authored_by="agent:research/quant/a1",
    )
    assert is_refusal(colliding)
    assert colliding.context["field"] == "locator"
    assert "file_path" in str(colliding.context.get("reason", "")).lower()
    paths = colliding.context.get("file_path")
    assert isinstance(paths, tuple)
    assert _locator_path(LIQUIDITY_SWEEP_LOCATION) in paths
    assert _locator_path(LIQUIDITY_SWEEP_CONTEXT) in paths
    assert _locator_path(LIQUIDITY_SWEEP_TRIGGERS) in paths

    location = service.cite(
        "strats",
        snapped.value,
        LIQUIDITY_SWEEP_LOCATION,
        evidence_label=OPAQUE_LABEL,
        authored_by="agent:research/quant/a1",
    )
    context = service.cite(
        "strats",
        snapped.value,
        LIQUIDITY_SWEEP_CONTEXT,
        evidence_label=OPAQUE_LABEL,
        authored_by="agent:research/quant/a1",
    )
    assert is_ok(location)
    assert is_ok(context)
    location_bytes = (seed / _locator_path(LIQUIDITY_SWEEP_LOCATION)).read_bytes()
    context_bytes = (seed / _locator_path(LIQUIDITY_SWEEP_CONTEXT)).read_bytes()
    assert location.value.artifact.content == location_bytes
    assert context.value.artifact.content == context_bytes
    assert location.value.artifact.content != context.value.artifact.content
    unique = service.cite(
        "strats",
        snapped.value,
        "swing-high",
        evidence_label=OPAQUE_LABEL,
        authored_by="agent:research/quant/a1",
    )
    assert is_ok(unique)
    assert unique.value.citation.locator == SWING_HIGH_LOCATOR
    assert unique.value.artifact.content == (seed / SWING_HIGH_PATH).read_bytes()


def test_first_slice_cite_emits_six_unscored_keys_not_admission_confidence(
    tmp_path: Path,
) -> None:
    service, _source, _seed = _bind_copied_seed(tmp_path)
    snapped = service.snapshot("strats")
    assert is_ok(snapped)
    cited = service.cite(
        "strats",
        snapped.value,
        SWING_HIGH_LOCATOR,
        evidence_label=OPAQUE_LABEL,
        authored_by="agent:research/quant/a1",
    )
    assert is_ok(cited)
    confidence = dict(cited.value.citation.evidence_confidence)
    assert tuple(confidence) == _DIMS
    assert confidence == dict.fromkeys(_DIMS, UNSCORED_CONFIDENCE_VALUE)
    assert all(value == "unscored" for value in confidence.values())
    assert all(not isinstance(value, (int, float)) for value in confidence.values())
    payload = dict(cited.value.citation.to_payload())
    assert "admission_confidence" not in payload
    assert "admission_confidence" not in confidence
    provenance = dict(cited.value.citation.provenance.to_payload())
    assert provenance["evidence_confidence"] == confidence


def test_mismatched_confidence_keys_remain_provenance_shape_mismatch(
    tmp_path: Path,
) -> None:
    service, _source, _seed = _bind_copied_seed(tmp_path)
    snapped = service.snapshot("strats")
    assert is_ok(snapped)
    bad = service.cite(
        "strats",
        snapped.value,
        SWING_HIGH_LOCATOR,
        evidence_label=OPAQUE_LABEL,
        evidence_confidence={"extraction_confidence": 1.0, "admission_confidence": 0.9},
        authored_by="agent:research/quant/a1",
    )
    assert is_refusal(bad)
    assert ProvenanceShapeMismatch.matches(bad)

    extra = service.cite(
        "strats",
        snapped.value,
        SWING_HIGH_LOCATOR,
        evidence_label=OPAQUE_LABEL,
        evidence_confidence={**dict.fromkeys(_DIMS, "unscored"), "seventh": "x"},
        authored_by="agent:research/quant/a1",
    )
    assert is_refusal(extra)
    assert ProvenanceShapeMismatch.matches(extra)


def test_evidence_label_is_opaque_verbatim_not_parsed(tmp_path: Path) -> None:
    service, _source, seed = _bind_copied_seed(tmp_path)
    snapped = service.snapshot("strats")
    assert is_ok(snapped)
    label = "source-stated/explicit|eligible-roles=location|not-a-registry-field"
    cited = service.cite(
        "strats",
        snapped.value,
        SWING_HIGH_LOCATOR,
        evidence_label=label,
        authored_by="agent:research/quant/a1",
    )
    assert is_ok(cited)
    citation = cited.value.citation
    assert citation.evidence_label == label
    payload = dict(citation.to_payload())
    assert payload["evidence_label"] == label
    for forbidden in (
        "eligible_roles",
        "family",
        "definition",
        "aliases",
        "registry_kind",
        "admission_confidence",
    ):
        assert forbidden not in payload
    file_text = (seed / SWING_HIGH_PATH).read_text(encoding="utf-8")
    assert "**Eligible roles:**" in file_text
    assert "eligible_roles" not in payload


def test_operator_seed_tree_search_cite_when_present() -> None:
    if not OPERATOR_SEED.is_dir():
        pytest.fail("AR-RES-10 operator seed tree is required for slice 0 search/cite")
    roster = DeskPluginRoster(plugin_load_configs=research_corpus_plugin_load_config(OPERATOR_SEED))
    result = roster.activate()
    assert is_ok(result), result
    loaded = roster.loader.get("research-corpus")
    assert loaded is not None
    source = loaded.context.snapshot()["singletons"][("KnowledgeSource", "strats")]
    assert isinstance(source, PlainFileLibrarySource)
    service = KnowledgeService()
    assert is_ok(service.bind("strats", source, plugin_id="research-corpus"))
    snapped = service.snapshot("strats")
    assert is_ok(snapped)
    assert "notes/liquidity.md" not in snapped.value.file_digests
    hits = service.search("strats", snapped.value, "STRAT-000001")
    assert is_ok(hits)
    assert STRAT_IDENTITY in hits.value
    swing = service.search("strats", snapped.value, "swing-high")
    assert is_ok(swing)
    assert SWING_HIGH_LOCATOR in swing.value
    cited = service.cite(
        "strats",
        snapped.value,
        SWING_HIGH_LOCATOR,
        evidence_label=OPAQUE_LABEL,
        authored_by="agent:research/quant/a1",
    )
    assert is_ok(cited)
    assert cited.value.artifact.content == (OPERATOR_SEED / SWING_HIGH_PATH).read_bytes()
    assert dict(cited.value.citation.evidence_confidence) == dict.fromkeys(
        _DIMS, UNSCORED_CONFIDENCE_VALUE
    )
