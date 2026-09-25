"""Story 60.2 — selected_refs kind instance_id is additive CT-40."""

from __future__ import annotations

from qma.wire import (
    ADR_0024_DECISION_REWRITTEN,
    DEC_0421_SUPERSEDED_BY,
    DEC_0463_FOLLOWS_DEC_0421,
    INSTANCE_ID_KIND,
    INSTANCE_ID_KIND_EXISTED_AT_INSPECT_SHA,
    PARENT_AD8_SELECTED_REF_KINDS,
    SCHEMA_FILES,
    SELECTED_REF_CONTRACT,
    SELECTED_REF_DTO_OWNER,
    SELECTED_REF_INSPECT_SHA,
    SELECTED_REF_KINDS,
    SELECTED_REF_NEW_CT_MINTED,
    SELECTED_REF_PARENT_KINDS_EXISTED_AT_INSPECT_SHA,
    SELECTED_REF_REFUSED_CT,
    SELECTED_REF_SCHEMA,
    SELECTED_REF_SCHEMA_FILE,
    SELECTED_REF_SCHEMA_NAME,
    SelectedRef,
    claim_instance_id_selected_ref_kind_at_inspect_sha,
    parse_selected_ref,
    parse_selected_refs,
    parse_wire_selected_ref,
    refuse_layout_widget_json_render_ref,
    validate_selected_ref,
)
from qmf.core import is_ok, is_refusal


def test_selected_ref_kind_instance_id_ct40_and_inspect_honesty() -> None:
    assert SELECTED_REF_DTO_OWNER == "COMP-QMA-WIRE"
    assert SELECTED_REF_CONTRACT == "CT-40"
    assert SELECTED_REF_NEW_CT_MINTED is False
    assert SELECTED_REF_REFUSED_CT == "CT-52"
    assert SELECTED_REF_INSPECT_SHA == "34c148b"
    assert INSTANCE_ID_KIND_EXISTED_AT_INSPECT_SHA is False
    assert SELECTED_REF_PARENT_KINDS_EXISTED_AT_INSPECT_SHA is True
    assert {
        "artifact",
        "research_ref",
        "contribution",
        "template",
        "dataset",
        "run",
        "attempt",
        "node_ids",
    } == PARENT_AD8_SELECTED_REF_KINDS
    assert INSTANCE_ID_KIND == "instance_id"
    assert INSTANCE_ID_KIND in SELECTED_REF_KINDS
    assert PARENT_AD8_SELECTED_REF_KINDS < SELECTED_REF_KINDS
    assert SCHEMA_FILES[SELECTED_REF_SCHEMA_NAME] == SELECTED_REF_SCHEMA_FILE
    assert SELECTED_REF_SCHEMA == "qma.wire.selected_ref.v1"
    assert DEC_0463_FOLLOWS_DEC_0421 == "DEC-0463"
    assert DEC_0421_SUPERSEDED_BY is None
    assert ADR_0024_DECISION_REWRITTEN is False
    claimed = claim_instance_id_selected_ref_kind_at_inspect_sha(True)
    assert is_refusal(claimed)
    assert claimed.context["existed_at_inspect_sha"] is False
    honest = claim_instance_id_selected_ref_kind_at_inspect_sha(False)
    assert is_ok(honest)
    assert honest.value is False


def test_parse_instance_id_kind_and_parent_ad8_kinds() -> None:
    parsed = parse_wire_selected_ref({"kind": "instance_id", "id": "inst:1"})
    assert is_ok(parsed)
    assert isinstance(parsed.value, SelectedRef)
    assert parsed.value.kind == "instance_id"
    assert parsed.value.id == "inst:1"
    schema_ok = validate_selected_ref({"kind": "instance_id", "id": "inst:home"})
    assert is_ok(schema_ok)
    assert schema_ok.value.kind == "instance_id"
    collected = parse_selected_refs(
        [
            {"kind": "artifact", "id": "fp1:sha256:aa"},
            {"kind": "instance_id", "id": "inst:1"},
            {"kind": "run", "id": "fp1:sha256:ab"},
        ]
    )
    assert is_ok(collected)
    assert {ref.kind for ref in collected.value} == {"artifact", "instance_id", "run"}
    unknown = parse_selected_ref({"kind": "layout", "id": "x"})
    assert is_refusal(unknown)


def test_layout_widget_json_render_trees_remain_refused() -> None:
    layout = parse_selected_ref({"kind": "run", "id": "x", "layout": {"x": 1}})
    assert is_refusal(layout)
    widgets = parse_selected_ref({"kind": "run", "id": "x", "widgets": ["chart"]})
    assert is_refusal(widgets)
    render = parse_selected_ref({"kind": "instance_id", "id": "inst:1", "json-render": {}})
    assert is_refusal(render)
    refused = refuse_layout_widget_json_render_ref()
    assert is_refusal(refused)
    allowed = refused.context["allowed"]
    assert isinstance(allowed, (list, tuple))
    assert "instance_id" in allowed
