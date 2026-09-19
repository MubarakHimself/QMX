"""Story 53.2 — pack contributes are {point, local_id} objects (RC-13)."""

from __future__ import annotations

import pytest
from qma.core.plugins import (
    DEFAULT_QUALIFIED_ID_RULE,
    ManifestError,
    PackContribute,
    PackContributeError,
    parse_pack_contributes,
    parse_plugin_manifest,
    qualify_pack_contribute,
)


def _manifest(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "research-corpus",
        "version": "0.1.0",
        "qma_api": ">=0.1.0,<1.0.0",
        "desk": "research",
        "entrypoint": "research_corpus.activate",
        "contributions": [{"point": "tool", "local_id": "inspect"}],
    }
    base.update(overrides)
    return base


def test_contributes_are_point_local_id_objects_not_opaque_strings() -> None:
    parsed = parse_pack_contributes(
        (
            {"point": "tool", "local_id": "inspect"},
            {"point": "graph_template", "local_id": "daily-brief"},
        ),
        package_id="sector-intel",
    )
    assert parsed == (
        PackContribute(point="tool", local_id="inspect"),
        PackContribute(point="graph_template", local_id="daily-brief"),
    )
    assert qualify_pack_contribute("sector-intel", parsed[0]) == "sector-intel:inspect"
    assert DEFAULT_QUALIFIED_ID_RULE == "package_id:local_id"

    with pytest.raises(PackContributeError, match="opaque string"):
        parse_pack_contributes(
            ["capability:qmb.analysis.project"],
            package_id="sector-intel",
        )
    with pytest.raises(PackContributeError, match="opaque string"):
        parse_pack_contributes(["tool:inspect"], package_id="sector-intel")
    with pytest.raises(ManifestError, match="opaque string"):
        parse_plugin_manifest(_manifest(contributes=["capability:qmb.analysis.project"]))


def test_qualified_id_defaults_to_package_id_colon_local_id() -> None:
    manifest = parse_plugin_manifest(
        _manifest(
            contributes=[{"point": "tool", "local_id": "inspect"}],
        )
    )
    assert manifest.contributes == (PackContribute(point="tool", local_id="inspect"),)
    assert (
        qualify_pack_contribute(manifest.id, manifest.contributes[0]) == "research-corpus:inspect"
    )
    declared = parse_pack_contributes(
        [{"point": "tool", "local_id": "inspect", "qualified_id": "research-notes:inspect"}],
        package_id="research-corpus",
    )
    assert declared[0].qualified_id == "research-notes:inspect"
    assert qualify_pack_contribute("research-corpus", declared[0]) == "research-notes:inspect"


def test_omitted_contributes_derive_from_multi_contributions() -> None:
    manifest = parse_plugin_manifest(_manifest())
    assert manifest.contributes == (PackContribute(point="tool", local_id="inspect"),)


def test_colliding_point_qualified_id_in_contributes_refuses() -> None:
    with pytest.raises(ManifestError, match="colliding"):
        parse_plugin_manifest(
            _manifest(
                contributes=[
                    {"point": "tool", "local_id": "inspect"},
                    {"point": "tool", "local_id": "inspect"},
                ]
            )
        )


def test_null_contributes_refused() -> None:
    with pytest.raises(ManifestError, match="never null"):
        parse_plugin_manifest(_manifest(contributes=None))
