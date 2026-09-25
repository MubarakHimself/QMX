"""Story 60.1 — pack manifest requests ops and an optional copilot; install is not a grant."""

from __future__ import annotations

import pytest
from qma.core.plugins import (
    CONTRIBUTES_EXISTED_AT_INSPECT_SHA,
    COPILOT_PROFILE_EXISTED_AT_INSPECT_SHA,
    COPILOT_PROFILE_IS_CONTRIBUTION_POINT,
    COPILOT_PROFILE_IS_GRANT,
    ENABLE_AFTER_VALIDATE_IS_GRANT,
    HEADLESS_HAS_COPILOT_PANEL,
    HEADLESS_HAS_NAVIGATION,
    INSTALL_IS_GRANT,
    PACK_SDK_INSPECT_SHA,
    PACK_SDK_NEW_CT_MINTED,
    PERMISSIONS_EXISTED_AT_INSPECT_SHA,
    QMA_IS_HOST_RUNTIME,
    QMF_IS_APPLICATION_LAYER_OWNER,
    REQUESTED_CAPABILITIES_IS_PERMISSIONS_ALIAS,
    SESSION_GRANT_RECORD_IS_GRANT,
    VIEW_STAR_IS_CONTRIBUTION_POINT,
    VIEW_STAR_IS_JSON_RENDER_RUNTIME_ID,
    WIDGETS_OWN_INVOKE,
    CopilotProfile,
    ManifestError,
    PackContribute,
    PackViewRequest,
    PluginManifest,
    SuggestedOp,
    parse_plugin_manifest,
)


def _manifest(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "research-corpus",
        "version": "0.1.0",
        "qma_api": ">=0.1.0,<1.0.0",
        "desk": "research",
        "entrypoint": "research_corpus.activate",
        "contributions": [{"point": "tool", "local_id": "inspect"}],
        "permissions": [],
    }
    base.update(overrides)
    return base


def test_inspect_sha_honesty_for_pack_sdk_fields() -> None:
    assert PACK_SDK_INSPECT_SHA == "34c148b"
    assert PACK_SDK_NEW_CT_MINTED is False
    assert CONTRIBUTES_EXISTED_AT_INSPECT_SHA is True
    assert PERMISSIONS_EXISTED_AT_INSPECT_SHA is True
    assert COPILOT_PROFILE_EXISTED_AT_INSPECT_SHA is False
    assert "copilot_profile" in PluginManifest.__dataclass_fields__
    assert "permissions" in PluginManifest.__dataclass_fields__
    assert "contributes" in PluginManifest.__dataclass_fields__
    assert "requested_capabilities" not in PluginManifest.__dataclass_fields__
    assert REQUESTED_CAPABILITIES_IS_PERMISSIONS_ALIAS is True


def test_omitted_copilot_profile_and_views_are_valid_headless() -> None:
    manifest = parse_plugin_manifest(_manifest())
    assert manifest.copilot_profile is None
    assert manifest.views == ()
    assert manifest.is_headless is True
    assert manifest.contributes == (PackContribute(point="tool", local_id="inspect"),)
    assert manifest.permissions == ()
    assert manifest.requested_capabilities is manifest.permissions
    assert HEADLESS_HAS_NAVIGATION is False
    assert HEADLESS_HAS_COPILOT_PANEL is False
    assert INSTALL_IS_GRANT is False
    assert ENABLE_AFTER_VALIDATE_IS_GRANT is False
    assert SESSION_GRANT_RECORD_IS_GRANT is True


def test_requested_capabilities_is_alias_of_permissions() -> None:
    via_permissions = parse_plugin_manifest(_manifest(permissions=["library.read"]))
    assert via_permissions.permissions == ("library.read",)
    assert via_permissions.requested_capabilities == ("library.read",)

    alias_raw = _manifest()
    del alias_raw["permissions"]
    alias_raw["requested_capabilities"] = ["library.read"]
    via_alias = parse_plugin_manifest(alias_raw)
    assert via_alias.permissions == ("library.read",)
    assert via_alias.requested_capabilities == ("library.read",)

    with pytest.raises(ManifestError, match="two live request fields"):
        parse_plugin_manifest(
            _manifest(permissions=["library.read"], requested_capabilities=["library.read"])
        )
    with pytest.raises(ManifestError, match="two live request fields"):
        parse_plugin_manifest(
            _manifest(permissions=["library.read"], requested_capabilities=["library.write"])
        )


def test_null_requested_capabilities_and_copilot_profile_refused() -> None:
    with pytest.raises(ManifestError, match="never null"):
        parse_plugin_manifest(
            {
                "id": "research-corpus",
                "version": "0.1.0",
                "qma_api": ">=0.1.0,<1.0.0",
                "desk": "research",
                "entrypoint": "research_corpus.activate",
                "requested_capabilities": None,
            }
        )
    with pytest.raises(ManifestError, match="never null"):
        parse_plugin_manifest(_manifest(copilot_profile=None))
    with pytest.raises(ManifestError, match="never null"):
        parse_plugin_manifest(_manifest(views=None))


def test_optional_copilot_profile_is_request_not_grant_or_point() -> None:
    assert COPILOT_PROFILE_IS_CONTRIBUTION_POINT is False
    assert COPILOT_PROFILE_IS_GRANT is False
    manifest = parse_plugin_manifest(
        _manifest(
            copilot_profile={
                "prompts": ["You are a research copilot."],
                "suggested_ops": [
                    {
                        "op_id": "qmb.analysis.project",
                        "op_version": 1,
                        "qualified_id": "research-corpus:inspect",
                    }
                ],
            }
        )
    )
    assert manifest.is_headless is False
    profile = manifest.copilot_profile
    assert isinstance(profile, CopilotProfile)
    assert profile.is_contribution_point is False
    assert profile.is_grant is False
    assert profile.prompts == ("You are a research copilot.",)
    assert profile.suggested_ops == (
        SuggestedOp(
            op_id="qmb.analysis.project",
            op_version=1,
            qualified_id="research-corpus:inspect",
        ),
    )

    with pytest.raises(ManifestError, match="not a grant"):
        parse_plugin_manifest(_manifest(copilot_profile={"grant_id": "grant:1"}))
    with pytest.raises(ManifestError, match="not a contribution point"):
        parse_plugin_manifest(_manifest(copilot_profile={"point": "copilot"}))
    with pytest.raises(ManifestError, match="undeclared or retired"):
        parse_plugin_manifest(_manifest(contributes=[{"point": "copilot", "local_id": "default"}]))
    with pytest.raises(ManifestError, match="undeclared or retired"):
        parse_plugin_manifest(
            _manifest(contributes=[{"point": "copilot_profile", "local_id": "panel"}])
        )


def test_optional_view_star_is_wire_dto_not_contribution_or_json_render() -> None:
    assert VIEW_STAR_IS_CONTRIBUTION_POINT is False
    assert VIEW_STAR_IS_JSON_RENDER_RUNTIME_ID is False
    assert WIDGETS_OWN_INVOKE is False
    manifest = parse_plugin_manifest(
        _manifest(views=[{"view_id": "view:heatmap", "op_id": "sector-intel.inspect"}])
    )
    assert manifest.is_headless is False
    assert manifest.views == (
        PackViewRequest(view_id="view:heatmap", op_id="sector-intel.inspect"),
    )
    assert manifest.views[0].is_contribution_point is False
    assert manifest.views[0].is_json_render_runtime_id is False
    assert manifest.views[0].widgets_own_invoke is False

    with pytest.raises(ManifestError, match="not a plugin contribution point"):
        parse_plugin_manifest(
            _manifest(views=[{"view_id": "view:heatmap", "op_id": "x", "point": "view"}])
        )
    with pytest.raises(ManifestError, match="json-render"):
        parse_plugin_manifest(_manifest(views=[{"view_id": "json-render:heatmap", "op_id": "x"}]))
    with pytest.raises(ManifestError, match="widgets never own invoke"):
        parse_plugin_manifest(
            _manifest(
                views=[
                    {
                        "view_id": "view:heatmap",
                        "op_id": "x",
                        "authorizes_invoke": True,
                    }
                ]
            )
        )
    with pytest.raises(ManifestError, match="undeclared or retired"):
        parse_plugin_manifest(_manifest(contributes=[{"point": "view", "local_id": "heatmap"}]))
    with pytest.raises(ManifestError, match="undeclared or retired"):
        parse_plugin_manifest(_manifest(contributes=[{"point": "ui_view", "local_id": "panel"}]))


def test_host_runtime_and_toolbox_law_constants() -> None:
    assert QMA_IS_HOST_RUNTIME is True
    assert QMF_IS_APPLICATION_LAYER_OWNER is False
