"""Story 53.4 — view:* are AD-17 wire DTOs, not ContributionHits (GAP-0081)."""

from __future__ import annotations

from qma.wire import (
    CONTRIBUTION_HIT_IS_GRANT,
    SCHEMA_FILES,
    VIEW_IS_CONTRIBUTION_HIT,
    VIEW_IS_PLUGIN_CONTRIBUTION_POINT,
    VIEW_PRESENTATION_CONTRACT,
    VIEW_PRESENTATION_DTO_OWNER,
    VIEW_PRESENTATION_GAP,
    VIEW_PRESENTATION_NEW_CT_MINTED,
    VIEW_PRESENTATION_OCCUPANCY,
    VIEW_PRESENTATION_REFUSED_CT,
    VIEW_PRESENTATION_SCHEMA,
    VIEW_PRESENTATION_SCHEMA_FILE,
    VIEW_PRESENTATION_SCHEMA_NAME,
    VIEW_UI_CONTRIBUTION_POINT_MINTED,
    ContributionHit,
    ViewPresentation,
    parse_federated_hit,
    parse_view_presentation,
    refuse_view_as_contribution_hit,
    refuse_view_contribution_hit,
    refuse_view_durable_work,
    validate_view_presentation,
)
from qmf.core import is_ok, is_refusal

_VIEW = {
    "view_id": "view:heatmap",
    "view_version": 1,
    "op_id": "sector-intel.inspect",
    "mount": "mounted",
    "parameter_binding": {
        "schema": "sector-intel.inspect.v1",
        "values": {"as_of": "2026-09-01"},
    },
    "snapshot_cursor": 9,
    "stale": False,
    "is_contribution_hit": False,
    "is_plugin_contribution_point": False,
    "occupancy": "none",
}


def test_view_dto_identity_is_not_a_contribution() -> None:
    assert VIEW_PRESENTATION_DTO_OWNER == "COMP-QMA-WIRE"
    assert VIEW_PRESENTATION_CONTRACT == "CT-40"
    assert VIEW_PRESENTATION_NEW_CT_MINTED is False
    assert VIEW_PRESENTATION_REFUSED_CT == "CT-52"
    assert VIEW_PRESENTATION_GAP == "GAP-0081"
    assert VIEW_IS_CONTRIBUTION_HIT is False
    assert VIEW_IS_PLUGIN_CONTRIBUTION_POINT is False
    assert VIEW_UI_CONTRIBUTION_POINT_MINTED is False
    assert VIEW_PRESENTATION_OCCUPANCY == "none"
    assert CONTRIBUTION_HIT_IS_GRANT is False
    assert SCHEMA_FILES[VIEW_PRESENTATION_SCHEMA_NAME] == VIEW_PRESENTATION_SCHEMA_FILE
    assert VIEW_PRESENTATION_SCHEMA == "qma.wire.view_presentation.v1"


def test_view_star_parses_as_presentation_not_hit() -> None:
    built = ViewPresentation.try_create(
        view_id=_VIEW["view_id"],
        view_version=_VIEW["view_version"],
        op_id=_VIEW["op_id"],
        mount=_VIEW["mount"],
        parameter_binding=_VIEW["parameter_binding"],
        snapshot_cursor=_VIEW["snapshot_cursor"],
        stale=_VIEW["stale"],
    )
    assert is_ok(built)
    view = built.value
    assert view.view_id == "view:heatmap"
    assert view.is_contribution_hit is False
    assert view.is_plugin_contribution_point is False
    assert view.occupancy == "none"
    assert view.starts_durable_work is False
    assert view.kills_durable_work is False
    assert not isinstance(view, ContributionHit)
    parsed = parse_view_presentation(dict(view.to_payload()))
    assert is_ok(parsed)
    schema_ok = validate_view_presentation(dict(_VIEW))
    assert is_ok(schema_ok)

    as_hit = parse_federated_hit(
        {
            "hit_class": "contribution",
            "plugin_id": "desk-ui",
            "point": "view:heatmap",
            "qualified_id": "desk-ui:heatmap",
            "package_id": "desk-ui",
            "package_version": "1.0.0",
            "availability_revision": 1,
            "availability": "enabled",
        }
    )
    assert is_refusal(as_hit)
    assert as_hit.context["gap"] == "GAP-0081"
    assert is_refusal(refuse_view_as_contribution_hit())
    assert is_refusal(refuse_view_contribution_hit())


def test_ui_view_point_and_durable_work_refuse() -> None:
    ui_view = ViewPresentation.try_create(
        view_id="ui_view",
        view_version=1,
        op_id="sector-intel.inspect",
        mount="mounted",
        parameter_binding={"schema": "sector-intel.inspect.v1", "values": {}},
        snapshot_cursor=0,
        stale=False,
    )
    assert is_refusal(ui_view)
    assert ui_view.context["gap"] == "GAP-0081"

    as_hit = parse_view_presentation({**_VIEW, "hit_class": "contribution"})
    assert is_refusal(as_hit)

    work = ViewPresentation.try_create(
        view_id="view:heatmap",
        view_version=1,
        op_id="sector-intel.inspect",
        mount="mounted",
        parameter_binding={"schema": "sector-intel.inspect.v1", "values": {}},
        snapshot_cursor=0,
        stale=False,
        starts_durable_work=True,
    )
    assert is_refusal(work)
    assert work.context["starts_durable_work"] is False
    assert is_refusal(refuse_view_durable_work())

    grant = parse_view_presentation({**_VIEW, "authorizes_invoke": True})
    assert is_refusal(grant)
    assert grant.context["hit_is_grant"] is False
