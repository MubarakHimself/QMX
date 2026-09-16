"""Story 49.3 — browse and cite pin a snapshot_ref first."""

from __future__ import annotations

from pathlib import Path

from qma.core.ports.knowledge import CorpusSnapshot, refuse_unpinned_live_tree
from qma.core.refusals import StaleSnapshot
from qma.daemon.knowledge import CiteOutcome, KnowledgeService, PlainFileLibrarySource
from qma.daemon.plugins import DeskPluginRoster, research_corpus_plugin_load_config
from qmf.core import Result, is_ok, is_refusal

_DIMS = (
    "extraction_confidence",
    "rule_explicitness",
    "source_quality_completeness",
    "ambiguity_unresolved_status",
    "empirical_status",
    "portability_market_transfer_status",
)


def _confidence(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = dict.fromkeys(_DIMS, 0.7)
    body.update(overrides)
    return body


def _corpus(tmp_path: Path, *, name: str = "strats") -> Path:
    root = tmp_path / name
    root.mkdir()
    (root / "README.md").write_text("seed readme\n", encoding="utf-8")
    (root / "notes.md").write_text(
        "liquidity sweep near London open\nrange holds\n",
        encoding="utf-8",
    )
    return root


def _bind(tmp_path: Path) -> tuple[KnowledgeService, PlainFileLibrarySource, Path]:
    service = KnowledgeService()
    root = _corpus(tmp_path)
    source = PlainFileLibrarySource(root_path=root, source_id="strats")
    bound = service.bind("strats", source, plugin_id="research-corpus")
    assert is_ok(bound)
    return service, source, root


def _cite(
    service: KnowledgeService,
    snapshot: CorpusSnapshot | str,
    locator: str = "notes.md",
) -> Result[CiteOutcome]:
    return service.cite(
        "strats",
        snapshot,
        locator,
        evidence_label="source-stated/explicit",
        evidence_confidence=_confidence(),
        authored_by="agent:research/quant/a1",
    )


def _browse_cite(
    service: KnowledgeService,
    locator: str = "notes.md",
    *,
    session_id: str,
) -> Result[CiteOutcome]:
    return service.browse_cite(
        "strats",
        locator,
        session_id=session_id,
        evidence_label="source-stated/explicit",
        evidence_confidence=_confidence(),
        authored_by="agent:research/quant/a1",
    )


def test_mission_pins_exactly_one_snapshot_ref_and_records_re_pin(tmp_path: Path) -> None:
    service, source, root = _bind(tmp_path)
    first = service.snapshot("strats")
    assert is_ok(first)
    pin = service.pin_mission_snapshot("mission-1", "strats", first.value)
    assert is_ok(pin)
    assert pin.value.snapshot_ref == first.value.id
    assert pin.value.previous_snapshot_ref is None
    assert service.mission_pin("mission-1", "strats") is pin.value

    same = service.pin_mission_snapshot("mission-1", "strats", first.value)
    assert is_ok(same)
    assert same.value.previous_snapshot_ref is None
    assert same.value.snapshot_ref == first.value.id

    (root / "notes.md").write_text("liquidity sweep revised\n", encoding="utf-8")
    source.invalidate_cache()
    second = service.snapshot("strats")
    assert is_ok(second)
    assert second.value.id != first.value.id
    re_pin = service.pin_mission_snapshot("mission-1", "strats", second.value)
    assert is_ok(re_pin)
    assert re_pin.value.snapshot_ref == second.value.id
    assert re_pin.value.previous_snapshot_ref == first.value.id
    assert re_pin.value.to_payload()["re_pin"] is True
    held = service.mission_pin("mission-1", "strats")
    assert held is not None
    assert held.snapshot_ref == second.value.id
    assert service.mission_pin("mission-1", "strats") is held


def test_strats_snapshots_form_linear_supersedes_chain(tmp_path: Path) -> None:
    seed = _corpus(tmp_path, name="seed-corpus")
    roster = DeskPluginRoster(plugin_load_configs=research_corpus_plugin_load_config(seed))
    result = roster.activate()
    assert is_ok(result), result
    loaded = roster.loader.get("research-corpus")
    assert loaded is not None
    source = loaded.context.snapshot()["singletons"][("KnowledgeSource", "strats")]
    assert isinstance(source, PlainFileLibrarySource)
    service = KnowledgeService()
    assert is_ok(service.bind("strats", source, plugin_id="research-corpus"))

    first = service.snapshot("strats")
    assert is_ok(first)
    assert first.value.supersedes is None
    (seed / "README.md").write_text("seed readme v2\n", encoding="utf-8")
    source.invalidate_cache()
    second = service.snapshot("strats")
    assert is_ok(second)
    assert second.value.supersedes == first.value.id
    (seed / "README.md").write_text("seed readme v3\n", encoding="utf-8")
    source.invalidate_cache()
    third = service.snapshot("strats")
    assert is_ok(third)
    assert third.value.supersedes == second.value.id
    chain = service.supersedes_chain("strats")
    assert is_ok(chain)
    assert chain.value == (first.value.id, second.value.id, third.value.id)


def test_browse_without_mission_pins_session_snapshot_before_read(tmp_path: Path) -> None:
    service, source, root = _bind(tmp_path)
    pinned_bytes = (root / "notes.md").read_bytes()
    assert service.session_pin("sess-browse", "strats") is None

    stale = service.browse_retrieve("strats", "notes.md", session_id="sess-browse")
    assert is_refusal(stale)
    assert StaleSnapshot.matches(stale)
    pin = service.session_pin("sess-browse", "strats")
    assert pin is not None
    assert pin.previous_snapshot_ref is None
    assert pin.snapshot_ref.startswith("fp1:sha256:")

    cited = _browse_cite(service, session_id="sess-browse")
    assert is_ok(cited)
    outcome = cited.value
    assert outcome.citation.snapshot_ref == pin.snapshot_ref
    assert outcome.artifact.content == pinned_bytes

    (root / "notes.md").write_text("live tree moved\n", encoding="utf-8")
    source.invalidate_cache()
    again = _browse_cite(service, session_id="sess-browse")
    assert is_ok(again)
    assert again.value.citation.snapshot_ref == pin.snapshot_ref
    assert again.value.artifact.content == pinned_bytes
    retrieved = service.browse_retrieve("strats", "notes.md", session_id="sess-browse")
    assert is_ok(retrieved)
    assert retrieved.value == pinned_bytes
    still = service.session_pin("sess-browse", "strats")
    assert still is not None
    assert still.snapshot_ref == pin.snapshot_ref

    re_pin = service.pin_session_snapshot("sess-browse", "strats")
    assert is_ok(re_pin)
    assert re_pin.value.previous_snapshot_ref == pin.snapshot_ref
    assert re_pin.value.snapshot_ref != pin.snapshot_ref
    assert re_pin.value.to_payload()["re_pin"] is True


def test_unpinned_live_tree_read_is_typed_refusal(tmp_path: Path) -> None:
    service, source, _root = _bind(tmp_path)
    live = source.snapshot()
    assert is_ok(live)

    cited = _cite(service, live.value)
    assert is_refusal(cited)
    assert cited.context["field"] == "snapshot_ref"
    assert "unpinned" in str(cited.context.get("reason", "")).lower()
    assert not StaleSnapshot.matches(cited)

    retrieved = service.retrieve("strats", live.value, "notes.md")
    assert is_refusal(retrieved)
    assert retrieved.context["field"] == "snapshot_ref"
    assert "unpinned" in str(retrieved.context.get("reason", "")).lower()

    helper = service.refuse_unpinned_live_tree(source_id="strats")
    assert is_refusal(helper)
    assert helper.context["field"] == refuse_unpinned_live_tree().context["field"]


def test_after_pin_retrieve_cite_use_pinned_bytes_not_live_tree(tmp_path: Path) -> None:
    service, source, root = _bind(tmp_path)
    original = (root / "notes.md").read_bytes()
    first = service.snapshot("strats")
    assert is_ok(first)
    pin = service.pin_mission_snapshot("mission-1", "strats", first.value)
    assert is_ok(pin)

    (root / "notes.md").write_text("silent live substitution would return this\n", encoding="utf-8")
    source.invalidate_cache()
    live = source.snapshot()
    assert is_ok(live)
    assert live.value.id != first.value.id

    cited = _cite(service, first.value)
    assert is_ok(cited)
    assert cited.value.citation.snapshot_ref == first.value.id
    assert cited.value.artifact.content == original
    assert cited.value.artifact.content != (root / "notes.md").read_bytes()

    retrieved = service.retrieve("strats", first.value.id, "notes.md")
    assert is_ok(retrieved)
    assert retrieved.value == original

    missing = service.retrieve("strats", first.value.id, "README.md")
    assert is_refusal(missing)
    assert StaleSnapshot.matches(missing)
    assert missing.context["snapshot_ref"] == first.value.id
