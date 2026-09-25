"""Story 60.1 — enable after validate does not mint a GrantRecord."""

from __future__ import annotations

from pathlib import Path

from qma.core.plugins import (
    ENABLE_AFTER_VALIDATE_IS_GRANT,
    INSTALL_IS_GRANT,
    SESSION_GRANT_RECORD_IS_GRANT,
)
from qma.daemon.plugins import (
    ENABLE_AFTER_VALIDATE_MINTS_GRANT_RECORD,
    INSTALL_MINTS_GRANT_RECORD,
    PackLifecycleFixture,
)
from qma.wire import HOST_GRANTS, MANIFESTS_GRANT, HostGrantLedger, refuse_manifest_grant
from qmf.core import is_ok, is_refusal

_AT = "2026-09-25T16:00:00Z"


def _manifest(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "id": "research-corpus",
        "version": "0.1.0",
        "qma_api": ">=0.1.0,<1.0.0",
        "desk": "research",
        "entrypoint": "research_corpus.activate",
        "dependencies": [],
        "contributions": [{"point": "tool", "local_id": "inspect"}],
        "contributes": [{"point": "tool", "local_id": "inspect"}],
        "permissions": [],
        "migrations": [],
        "exports_secrets": False,
    }
    body.update(overrides)
    return body


def _bring_to_validated(fixture: PackLifecycleFixture, raw: dict[str, object]) -> None:
    package_id = str(raw["id"])
    assert is_ok(fixture.download(raw, files={}, transitioned_at=_AT))
    assert is_ok(fixture.install(package_id, transitioned_at=_AT))
    assert is_ok(fixture.validate(package_id, transitioned_at=_AT))


def test_enable_after_validate_does_not_mint_grant_record(tmp_path: Path) -> None:
    assert INSTALL_IS_GRANT is False
    assert ENABLE_AFTER_VALIDATE_IS_GRANT is False
    assert SESSION_GRANT_RECORD_IS_GRANT is True
    assert INSTALL_MINTS_GRANT_RECORD is False
    assert ENABLE_AFTER_VALIDATE_MINTS_GRANT_RECORD is False
    assert MANIFESTS_GRANT is False
    assert HOST_GRANTS is True

    fixture = PackLifecycleFixture(root=tmp_path / "packs")
    _bring_to_validated(fixture, _manifest())
    assert fixture.grant_ids() == ()
    enabled = fixture.enable("research-corpus", transitioned_at=_AT)
    assert is_ok(enabled)
    assert enabled.value.to_state == "enabled"
    assert fixture.grant_ids() == ()
    loaded = fixture.loader.get("research-corpus")
    assert loaded is not None
    assert loaded.manifest.copilot_profile is None
    assert loaded.manifest.views == ()
    assert loaded.manifest.is_headless is True
    assert loaded.grant_record_ids == ()
    points = {row.point for row in loaded.published}
    assert "view" not in points
    assert "copilot" not in points
    assert "copilot_profile" not in points
    assert "tool" in points


def test_headless_and_copilot_packs_enable_without_grants(tmp_path: Path) -> None:
    fixture = PackLifecycleFixture(root=tmp_path / "packs")
    with_copilot = _manifest(
        copilot_profile={
            "prompts": ["Stay in the library."],
            "suggested_ops": [
                {
                    "op_id": "qmb.analysis.project",
                    "op_version": 1,
                    "qualified_id": "research-corpus:inspect",
                }
            ],
        },
        views=[{"view_id": "view:heatmap", "op_id": "qmb.analysis.project"}],
    )
    _bring_to_validated(fixture, with_copilot)
    enabled = fixture.enable("research-corpus", transitioned_at=_AT)
    assert is_ok(enabled)
    loaded = fixture.loader.get("research-corpus")
    assert loaded is not None
    assert loaded.manifest.copilot_profile is not None
    assert loaded.manifest.copilot_profile.is_grant is False
    assert loaded.manifest.views[0].is_contribution_point is False
    assert loaded.grant_record_ids == ()
    assert fixture.grant_ids() == ()
    points = {row.point for row in loaded.published}
    assert points == {"tool"}

    ledger = HostGrantLedger()
    refused = ledger.mint(
        issuer="manifest",
        grant_id="grant:1",
        principal="operator",
        audience="psess:session",
        contribution={"qualified_id": "research-corpus:inspect", "package_version": "0.1.0"},
        instance_id="inst:1",
        config_revision=4,
        op_id="qmb.analysis.project",
        op_version=1,
        effect_class="read",
        parameter_ceiling={"allow_keys": ["run_fp1", "as_of"]},
        expires_at="2026-12-31T00:00:00Z",
    )
    assert is_refusal(refused)
    assert is_refusal(refuse_manifest_grant())
    assert list(ledger.grants) == []
