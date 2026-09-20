"""Story 58.5 — pack lifecycle, export scanner oracle, unsupported_door."""

from __future__ import annotations

import ast
import json
import runpy
from pathlib import Path
from typing import cast

from qma.core.refusals import UnsupportedDoor
from qma.daemon import (
    ExportScanReport,
    PackLifecycleFixture,
    PackTransition,
    claim_gap_0098_closed,
)
from qma.daemon.journal.stores import CLOSED_STORE_NAMES
from qma.daemon.plugins import (
    COMPOSITION_MODES,
    EXPORTS_SECRETS_AUTHORIZES_EXPORT,
    GAP_0098_ID,
    GAP_0098_STATUS,
    MISSING_DEP_WARN_AND_CONTINUE,
    PACK_LIFECYCLE_SIXTH_STORE_MINTED,
    PACK_LIFECYCLE_STORE,
    PACK_LIFECYCLE_WIRED_AT_INSPECT_SHA,
    PACK_STATES,
    SESSION_GRANTED_IS_PACK_STATE,
)
from qma.daemon.plugins.lifecycle import (
    COMPOSITION_MODES_REQUIRE_CORE_EDITS,
    E2E_ADOPTION_CLOSED,
    EXPORT_SCAN_DETECTORS,
    EXPORT_THREAT_CLASSES,
    LEGAL_PACK_TRANSITIONS,
    MIGRATION_MODES,
    MIGRATION_PHASES,
    P2_INT_001,
    PACK_LIFECYCLE_INSPECT_SHA,
    QMA_OPERATOR_CLI,
    QMN_OPERATOR_CLI,
)
from qmf.core import is_ok, is_refusal
from qmf.core.refusal import Result

_SRC = Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "plugins" / "lifecycle.py"
_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "pack_lifecycle_fixture_usage.py"
_AT = "2026-09-20T16:00:00Z"


def _ok[T](result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


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


def _fixture(tmp_path: Path) -> PackLifecycleFixture:
    return PackLifecycleFixture(root=tmp_path / "packs")


def _bring_to_validated(
    fixture: PackLifecycleFixture,
    raw: dict[str, object] | None = None,
    *,
    files: dict[str, str] | None = None,
) -> None:
    manifest = raw if raw is not None else _manifest()
    package_id = str(manifest["id"])
    _ok(fixture.download(manifest, files=files or {}, transitioned_at=_AT))
    _ok(fixture.install(package_id, transitioned_at=_AT))
    _ok(fixture.validate(package_id, transitioned_at=_AT))


def test_constants_and_closed_store() -> None:
    assert PACK_STATES == (
        "downloaded",
        "installed",
        "validated",
        "enabled",
        "disabled",
        "uninstalled",
    )
    assert "session-granted" not in PACK_STATES
    assert SESSION_GRANTED_IS_PACK_STATE is False
    assert ("validated", "enabled") in LEGAL_PACK_TRANSITIONS
    assert ("enabled", "disabled") in LEGAL_PACK_TRANSITIONS
    assert ("disabled", "enabled") in LEGAL_PACK_TRANSITIONS
    assert frozenset({"down", "forward_only"}) == MIGRATION_MODES
    assert frozenset({"prepare", "commit", "rollback"}) == MIGRATION_PHASES
    assert EXPORT_THREAT_CLASSES == ("secret_values", "private_paths", "transcripts")
    assert EXPORT_SCAN_DETECTORS == (
        "secret-regex-v3",
        "path-allowlist-v1",
        "transcript-marker-v1",
    )
    assert EXPORTS_SECRETS_AUTHORIZES_EXPORT is False
    assert MISSING_DEP_WARN_AND_CONTINUE is False
    assert PACK_LIFECYCLE_WIRED_AT_INSPECT_SHA is False
    assert PACK_LIFECYCLE_INSPECT_SHA.startswith("270e992")
    assert PACK_LIFECYCLE_SIXTH_STORE_MINTED is False
    assert PACK_LIFECYCLE_STORE == "plugin_install_records"
    assert PACK_LIFECYCLE_STORE in CLOSED_STORE_NAMES
    assert "pack_lifecycle" not in CLOSED_STORE_NAMES
    assert QMA_OPERATOR_CLI is False
    assert QMN_OPERATOR_CLI is False
    assert GAP_0098_ID == "GAP-0098"
    assert GAP_0098_STATUS == "open"
    assert P2_INT_001 == "P2-INT-001"
    assert E2E_ADOPTION_CLOSED is False
    assert COMPOSITION_MODES == (
        "consume_artifact_fp1",
        "invoke_exported_op_through_envelope",
        "graph_template_coordinates_two_apps",
        "composite_app_cites_contribution_ids",
    )
    assert COMPOSITION_MODES_REQUIRE_CORE_EDITS is False
    closed = claim_gap_0098_closed()
    assert is_refusal(closed)
    assert closed.context["gap_status"] == "open"
    assert closed.context["e2e_adoption_closed"] is False


def test_journaled_transitions_cas_and_atomic_roster(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    assert fixture.assert_store_closed() is True
    _bring_to_validated(fixture)
    enabled = _ok(fixture.enable("research-corpus", transitioned_at=_AT))
    assert isinstance(enabled, PackTransition)
    assert enabled.from_state == "validated"
    assert enabled.to_state == "enabled"
    assert enabled.cas_token == f"roster:{enabled.roster_generation}"
    assert enabled.principal == "operator"
    states = [row.to_state for row in fixture.transitions()]
    assert states == ["downloaded", "installed", "validated", "enabled"]
    live = fixture.roster.live_path
    assert live.is_file()
    assert not fixture.roster.stage_path.is_file()
    body = json.loads(live.read_text(encoding="utf-8"))
    assert body["roster_generation"] == fixture.roster_generation
    assert body["availability_revision"] == fixture.loader.availability_revision()
    assert body["availability_revision"] >= 1
    journal = (fixture.root / "pack_transitions.jsonl").read_text(encoding="utf-8")
    assert "research-corpus" in journal
    stale = fixture.enable(
        "research-corpus",
        transitioned_at=_AT,
        expected_generation=0,
    )
    assert is_refusal(stale)
    assert stale.context["branch"] == "E"
    pack = fixture.pack("research-corpus")
    assert pack is not None
    assert pack.state == "enabled"


def test_failed_validation_and_partial_install_restore_last_usable(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    _ok(fixture.download(_manifest(), transitioned_at=_AT))
    _ok(fixture.install("research-corpus", transitioned_at=_AT))
    before = fixture.roster_generation
    refused = fixture.validate("research-corpus", transitioned_at=_AT, fail=True)
    assert is_refusal(refused)
    assert refused.context["branch"] == "E"
    assert fixture.roster_generation == before
    installed = fixture.pack("research-corpus")
    assert installed is not None
    assert installed.state == "installed"
    partial = fixture.install("research-corpus", transitioned_at=_AT, fail=True)
    assert is_refusal(partial)
    assert installed.state == "installed"


def test_missing_dependency_is_hard_error_at_enable(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    _bring_to_validated(fixture)
    _ok(fixture.enable("research-corpus", transitioned_at=_AT))
    published = list(fixture.loader.published_contributions())
    _bring_to_validated(
        fixture,
        _manifest(
            id="research-notes",
            entrypoint="research_notes.activate",
            dependencies=["analysis-backtest"],
            contributions=[{"point": "tool", "local_id": "cite"}],
            contributes=[{"point": "tool", "local_id": "cite"}],
        ),
    )
    generation = fixture.roster_generation
    refused = fixture.enable("research-notes", transitioned_at=_AT)
    assert is_refusal(refused)
    assert refused.context["field"] == "dependencies"
    assert refused.context["warn_and_continue"] is False
    assert refused.context["hermes_advisory"] is False
    assert refused.context["branch"] == "A"
    missing = refused.context["missing"]
    assert isinstance(missing, (list, tuple))
    assert "analysis-backtest" in missing
    assert fixture.roster_generation == generation
    notes = fixture.pack("research-notes")
    corpus = fixture.pack("research-corpus")
    assert notes is not None and corpus is not None
    assert notes.state == "validated"
    assert corpus.state == "enabled"
    assert list(fixture.loader.published_contributions()) == published
    advisory = fixture.enable("research-notes", transitioned_at=_AT, warn_and_continue=True)
    assert is_refusal(advisory)
    assert advisory.context["warn_and_continue"] is False


def test_export_scanner_is_the_oracle(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    files = {
        "config.json": json.dumps({"token": "super-secret-value", "name": "sector"}),
        "notes.md": "public notes",
    }
    _bring_to_validated(fixture, files=files)
    _ok(fixture.enable("research-corpus", transitioned_at=_AT))
    pack = fixture.pack("research-corpus")
    assert pack is not None
    assert pack.exports_secrets is False
    trusted = fixture.export("research-corpus", trust_manifest=True)
    assert is_refusal(trusted)
    assert trusted.context["branch"] == "B"
    assert trusted.context["scanner_is_oracle"] is True
    exported = _ok(fixture.export("research-corpus"))
    assert exported.report.result == "fail-closed-pass"
    assert exported.report.report_version == 1
    assert exported.report.detectors == EXPORT_SCAN_DETECTORS
    assert exported.report.coverage.complete is True
    assert "super-secret-value" not in json.dumps(dict(exported.files))
    assert any(item.threat_class == "secret_values" for item in exported.report.findings)
    assert exported.files["config.json"].find("cred:") != -1
    incomplete = fixture.export("research-corpus", complete=False)
    assert is_refusal(incomplete)
    assert incomplete.context["result"] == "fail-closed-fail"
    dirty = {
        "leak.md": "token=still-secret",
        "C:\\Users\\operator\\notes.md": "home file",
        "transcript.json": '{"transcript":["hi"]}',
        "key.pem": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
    }
    leaked = fixture.export("research-corpus", files=dirty)
    assert is_refusal(leaked)
    assert leaked.context["branch"] == "C"
    fake = ExportScanReport(
        report_version=1,
        package_id="research-corpus",
        package_version="0.1.0",
        threat_model={"classes": list(EXPORT_THREAT_CLASSES), "scope": "export-bundle"},
        detectors=EXPORT_SCAN_DETECTORS,
        coverage=exported.report.coverage,
        findings=(),
        rewrite_map=(),
        post_rewrite_hash=exported.report.post_rewrite_hash,
        post_rewrite_signature="sig:forged",
        result="fail-closed-pass",
    )
    forged = fixture.export("research-corpus", report=fake)
    assert is_refusal(forged)
    assert forged.context["branch"] == "B"


def test_migrations_restore_or_record_forward_only(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    _bring_to_validated(fixture)
    _ok(fixture.enable("research-corpus", transitioned_at=_AT))
    down = _ok(
        fixture.migrate(
            "research-corpus",
            from_version="0.1.0",
            to_version="0.2.0",
            mode="down",
            phase="prepare",
        )
    )
    assert down.mode == "down"
    assert down.phase == "prepare"
    assert down.outcome == "ok"
    committed = _ok(
        fixture.migrate(
            "research-corpus",
            from_version="0.1.0",
            to_version="0.2.0",
            mode="down",
            phase="commit",
        )
    )
    assert committed.outcome == "ok"
    migrated = fixture.pack("research-corpus")
    assert migrated is not None
    assert migrated.version == "0.2.0"
    generation = fixture.roster_generation
    failed = fixture.migrate(
        "research-corpus",
        from_version="0.2.0",
        to_version="0.3.0",
        mode="down",
        phase="commit",
        fail=True,
    )
    assert is_refusal(failed)
    assert failed.context["branch"] == "E"
    assert fixture.roster_generation == generation
    still = fixture.pack("research-corpus")
    assert still is not None
    assert still.state == "enabled"
    unconfirmed = fixture.migrate(
        "research-corpus",
        from_version="0.2.0",
        to_version="0.3.0",
        mode="forward_only",
        phase="prepare",
    )
    assert is_refusal(unconfirmed)
    recovered = fixture.migrate(
        "research-corpus",
        from_version="0.2.0",
        to_version="0.3.0",
        mode="forward_only",
        phase="commit",
        operator_confirmed=True,
        fail=True,
    )
    assert is_refusal(recovered)
    assert recovered.context["recovery"] == "forward_only"


def test_unsupported_door_and_qmb_only_cli(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    admitted = _ok(fixture.invoke_door(op_id="qma.procedure.start", version=1, adapter="library"))
    assert admitted.adapter.value == "library"
    refused = fixture.invoke_door(op_id="qma.procedure.start", version=1, adapter="qmb-cli")
    assert is_refusal(refused)
    assert UnsupportedDoor.matches(refused)
    assert refused.context["unsupported_door"] is True
    assert refused.context["reason"] == "unsupported_door"
    for adapter in ("qma-cli", "qmn-cli"):
        minted = fixture.invoke_door(op_id="qmn.evidence.query", version=1, adapter=adapter)
        assert is_refusal(minted)
        assert UnsupportedDoor.matches(minted)
        assert minted.context["operator_cli"] == "qmb"
    assert is_refusal(fixture.mint_operator_cli("qma"))
    assert fixture.qma_operator_cli is False
    assert fixture.qmn_operator_cli is False
    parity = _ok(fixture.supported_door_parity(op_id="qmb.analysis.project", version=1))
    assert parity.op_id == "qmb.analysis.project"
    assert parity.effect_class == "read"
    assert "library" in parity.adapters
    assert "qmb-cli" in parity.adapters
    same = _ok(fixture.supported_door_parity(op_id="qmb.analysis.project", version=1))
    assert dict(same.to_payload()) == dict(parity.to_payload())


def test_disable_pin_is_tombstone_never_another_version(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    _bring_to_validated(fixture)
    _ok(fixture.enable("research-corpus", transitioned_at=_AT))
    pin = _ok(fixture.pin("research-corpus"))
    assert pin.as_tuple()[0] == "research-corpus:inspect"
    live = _ok(fixture.invoke_pin(pin))
    assert live.is_grant is False
    disabled = _ok(fixture.disable("research-corpus", transitioned_at=_AT))
    assert disabled.to_state == "disabled"
    later = fixture.invoke_pin(pin)
    assert is_refusal(later)
    assert later.context["availability"] in {"unavailable", "tombstone"}
    assert later.context["silent_retarget"] is False
    assert later.context["package_version"] == "0.1.0"
    _bring_to_validated(
        fixture,
        _manifest(
            id="research-notes",
            version="2.0.0",
            entrypoint="research_notes.activate",
            contributions=[{"point": "tool", "local_id": "inspect"}],
            contributes=[
                {
                    "point": "tool",
                    "local_id": "inspect",
                    "qualified_id": "research-corpus:inspect",
                }
            ],
        ),
    )
    _ok(fixture.enable("research-notes", transitioned_at=_AT))
    retarget = fixture.invoke_pin(pin)
    assert is_refusal(retarget)
    assert retarget.context["package_version"] == "0.1.0"
    assert retarget.context.get("retarget_refused") is True
    _ok(fixture.disable("research-notes", transitioned_at=_AT))
    receipt = _ok(fixture.uninstall("research-notes", transitioned_at=_AT))
    transition, departed = receipt
    assert transition.to_state == "uninstalled"
    assert departed.dependants == ()
    assert "session-granted" not in dict(departed.to_payload())
    assert fixture.composition_modes() == COMPOSITION_MODES
    assert COMPOSITION_MODES_REQUIRE_CORE_EDITS is False


def test_custom_pack_requires_operator_enable(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    _ok(
        fixture.download(
            _manifest(),
            custom=True,
            transitioned_at=_AT,
        )
    )
    _ok(fixture.install("research-corpus", transitioned_at=_AT))
    _ok(fixture.validate("research-corpus", transitioned_at=_AT))
    refused = fixture.enable("research-corpus", transitioned_at=_AT, operator_enable=False)
    assert is_refusal(refused)
    _ok(fixture.enable("research-corpus", transitioned_at=_AT, operator_enable=True))


def test_module_never_imports_qmb() -> None:
    source = _SRC.read_text(encoding="utf-8")
    assert "import qmb" not in source
    assert "from qmb" not in source
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    assert not any(name == "qmb" or name.startswith("qmb.") for name in imports)


def test_reference_usage_example_runs(tmp_path: Path) -> None:
    namespace = runpy.run_path(str(_EXAMPLE))
    main = cast("object", namespace["main"])
    assert callable(main)
    main(tmp_path / "example")
