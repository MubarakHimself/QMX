"""Story 52.1 / 53.1 — federated hit DTO is KnowledgeHit | ArtifactHit | ContributionHit."""

from __future__ import annotations

from qma.wire import (
    ADDABLE_QUERY_COUNT,
    ARTIFACT_HIT_KINDS,
    ARTIFACT_QUERY_HIT_TAGS,
    ARTIFACT_ROSTER_KINDS,
    FEDERATED_HIT_CLASSES,
    FEDERATED_HIT_CONTRACT,
    FEDERATED_HIT_DTO_OWNER,
    FEDERATED_HIT_NEW_CT_MINTED,
    FEDERATED_HIT_SCHEMA,
    FEDERATED_HIT_SCHEMA_FILE,
    FEDERATED_HIT_SCHEMA_NAME,
    HIT_CLASS_ARTIFACT,
    HIT_CLASS_CONTRIBUTION,
    HIT_CLASS_KNOWLEDGE,
    SCHEMA_DIR,
    SCHEMA_FILES,
    SEED_QUERY_COUNT,
    WIRE_QUERIES,
    ArtifactHit,
    KnowledgeHit,
    WireQuery,
    parse_federated_hit,
    parse_wire_type,
    refuse_cite_copy_artifact_rail,
    refuse_qml_candidate_hit,
    refuse_strats_hit_class,
    validate_family_payload,
    validate_federated_hit,
)
from qmf.core import is_ok, is_refusal

_FP1 = "fp1:sha256:" + ("ab" * 32)


def test_owner_is_additive_ct40_without_new_contract() -> None:
    assert FEDERATED_HIT_DTO_OWNER == "COMP-QMA-WIRE"
    assert FEDERATED_HIT_CONTRACT == "CT-40"
    assert FEDERATED_HIT_NEW_CT_MINTED is False
    assert FEDERATED_HIT_SCHEMA == "qma.wire.federated_hit.v1"
    assert SCHEMA_FILES[FEDERATED_HIT_SCHEMA_NAME] == FEDERATED_HIT_SCHEMA_FILE
    assert (SCHEMA_DIR / FEDERATED_HIT_SCHEMA_FILE).is_file()
    assert {
        HIT_CLASS_KNOWLEDGE,
        HIT_CLASS_ARTIFACT,
        HIT_CLASS_CONTRIBUTION,
    } == FEDERATED_HIT_CLASSES


def test_facade_queries_are_additive_ct40_vocabulary() -> None:
    assert WireQuery.FACADE_SEARCH.value == "facade_search"
    assert WireQuery.FACADE_GET.value == "facade_get"
    assert "facade_search" in WIRE_QUERIES
    assert "facade_get" in WIRE_QUERIES
    assert ADDABLE_QUERY_COUNT == 4
    assert len(WIRE_QUERIES) == SEED_QUERY_COUNT + ADDABLE_QUERY_COUNT == 11
    assert parse_wire_type("facade_search") == "facade_search"
    assert is_ok(validate_family_payload("facade_search", {"query": "swing-high"}))
    assert is_ok(validate_family_payload("facade_get", {"hit_class": "knowledge"}))
    assert is_ok(validate_family_payload("facade_get", {"hit_class": "contribution"}))


def test_knowledge_hit_round_trips() -> None:
    checked = KnowledgeHit.try_create(
        source_ref="strats",
        snapshot_ref=_FP1,
        locator="dictionary/swing-high.md",
    )
    assert is_ok(checked)
    hit = checked.value
    assert hit.hit_class == "knowledge"
    assert hit.to_payload() == {
        "hit_class": "knowledge",
        "locator": "dictionary/swing-high.md",
        "snapshot_ref": _FP1,
        "source_ref": "strats",
    }
    parsed = parse_federated_hit(hit.to_payload())
    assert is_ok(parsed)
    assert isinstance(parsed.value, KnowledgeHit)
    schema_ok = validate_federated_hit(hit.to_payload())
    assert is_ok(schema_ok)


def test_artifact_hit_accepts_roster_and_query_tags() -> None:
    roster = ArtifactHit.try_create(fp1=_FP1, kind="bot-definition")
    assert is_ok(roster)
    assert roster.value.hit_class == "artifact"
    assert roster.value.kind == "bot-definition"

    saved = parse_federated_hit({"hit_class": "artifact", "fp1": _FP1, "kind": "saved-view"})
    assert is_ok(saved)
    assert isinstance(saved.value, ArtifactHit)
    assert saved.value.kind == "saved-view"

    published = validate_federated_hit(
        {"hit_class": "artifact", "fp1": _FP1, "kind": "analysis.published"}
    )
    assert is_ok(published)
    assert isinstance(published.value, ArtifactHit)
    assert published.value.kind == "analysis.published"

    assert "saved-view" in ARTIFACT_QUERY_HIT_TAGS
    assert "analysis.published" in ARTIFACT_QUERY_HIT_TAGS
    assert ARTIFACT_ROSTER_KINDS <= ARTIFACT_HIT_KINDS
    assert "analysis-publication" not in ARTIFACT_HIT_KINDS
    assert "strats" not in ARTIFACT_HIT_KINDS


def test_strats_and_qml_candidate_hit_classes_are_refused() -> None:
    strats = parse_federated_hit(
        {"hit_class": "strats", "source_ref": "x", "snapshot_ref": "y", "locator": "z"}
    )
    assert is_refusal(strats)
    assert strats.context["decision"] == "DEC-0412"
    assert strats.context["dead"] is True

    candidate = parse_federated_hit(
        {
            "hit_class": "qml_candidate",
            "source_ref": "x",
            "snapshot_ref": "y",
            "locator": "z",
        }
    )
    assert is_refusal(candidate)
    assert candidate.context["hit_class"] == "qml_candidate"

    typed = parse_federated_hit({"type": "QmlCandidateHit", "hit_class": "knowledge"})
    assert is_refusal(typed)

    assert is_refusal(refuse_strats_hit_class())
    assert is_refusal(refuse_qml_candidate_hit())


def test_cite_copy_artifact_ref_is_not_artifact_rail_hit() -> None:
    as_artifact = parse_federated_hit(
        {"hit_class": "artifact", "fp1": _FP1, "kind": "bot-definition", "artifact_ref": "copy:1"}
    )
    assert is_refusal(as_artifact)
    assert as_artifact.context["field"] == "artifact_ref"

    as_knowledge = parse_federated_hit(
        {
            "hit_class": "knowledge",
            "source_ref": "strats",
            "snapshot_ref": _FP1,
            "locator": "notes.md",
            "artifact_ref": "copy:1",
        }
    )
    assert is_refusal(as_knowledge)

    direct = ArtifactHit.try_create(
        fp1=_FP1,
        kind="performance-result",
        artifact_ref="copy:1",
    )
    assert is_refusal(direct)
    assert is_refusal(refuse_cite_copy_artifact_rail())


def test_library_kind_maps_onto_artifact_hit_tags() -> None:
    from qma.wire import library_kind_to_artifact_hit_kind

    assert library_kind_to_artifact_hit_kind("analysis-publication") == "analysis.published"
    assert library_kind_to_artifact_hit_kind("analysis.published") == "analysis.published"
    assert library_kind_to_artifact_hit_kind("saved-view") == "saved-view"
    assert library_kind_to_artifact_hit_kind("bot-definition") == "bot-definition"


def test_unknown_artifact_kind_and_invented_hit_class_refused() -> None:
    kind = ArtifactHit.try_create(fp1=_FP1, kind="graph-template")
    assert is_refusal(kind)
    invented = parse_federated_hit(
        {
            "hit_class": "hypothesis",
            "source_ref": "x",
            "snapshot_ref": "y",
            "locator": "z",
        }
    )
    assert is_refusal(invented)
    bad_fp = ArtifactHit.try_create(fp1="not-a-fingerprint", kind="saved-view")
    assert is_refusal(bad_fp)


def test_knowledge_hit_display_aliases_forbid_hypothesis_nouns() -> None:
    from qma.wire import (
        KNOWLEDGE_HIT_ALLOWED_DISPLAY_ALIASES,
        KNOWLEDGE_HIT_FORBIDDEN_DISPLAY_TOKENS,
        VIEWING_CITED_SEED_MINTS_RESEARCH_REF,
        refuse_knowledge_hit_display_alias,
        resolve_knowledge_hit_display_alias,
        viewing_cited_seed_mints_research_ref,
    )

    assert "hypothesis" in KNOWLEDGE_HIT_FORBIDDEN_DISPLAY_TOKENS
    assert "research candidate" in KNOWLEDGE_HIT_FORBIDDEN_DISPLAY_TOKENS
    assert "seed cite" in KNOWLEDGE_HIT_ALLOWED_DISPLAY_ALIASES
    assert VIEWING_CITED_SEED_MINTS_RESEARCH_REF is False
    assert viewing_cited_seed_mints_research_ref() is False

    ok = resolve_knowledge_hit_display_alias("dictionary entry")
    assert is_ok(ok)
    assert ok.value == "dictionary entry"

    banned = resolve_knowledge_hit_display_alias("research candidate")
    assert is_refusal(banned)
    assert is_refusal(refuse_knowledge_hit_display_alias())

    payload = KnowledgeHit.try_create(
        source_ref="strats",
        snapshot_ref=_FP1,
        locator="notes.md",
    )
    assert is_ok(payload)
    assert "research_ref" not in payload.value.to_payload()
