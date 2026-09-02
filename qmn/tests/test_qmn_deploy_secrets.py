"""Story 27.1 — restricted wizard and systemd-creds recipes (check-mode / fixtures)."""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

_QMN_ROOT = Path(__file__).resolve().parents[1]
_DEPLOY = _QMN_ROOT / "deploy"
_WORKSPACE = _QMN_ROOT.parent


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_wizard_and_creds_modules_never_import_qmn_or_connection() -> None:
    banned = (
        "qmn.host",
        "qmn.doors",
        "qmn.venue",
        "qmf.venue",
        "qmf.venue.connection",
    )
    for path in (
        _DEPLOY / "creds.py",
        _DEPLOY / "secrets_provision.py",
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imported.add(node.module)
        for name in imported:
            assert not name.startswith("qmn."), path
            assert name not in banned
            assert "connection" not in name
            assert name != "subprocess"
        text = path.read_text(encoding="utf-8")
        assert "rotate_secret" not in text
        assert "ConnectionManager" not in text


def test_check_mode_plan_uses_host_key_stdin_and_provisioning_identity() -> None:
    creds = _load("qmn_deploy_creds_s271", _DEPLOY / "creds.py")
    wizard = _load("qmn_deploy_secrets_s271", _DEPLOY / "secrets_provision.py")
    plan = wizard.build_provision_plan(mode="check")
    assert plan.ok, plan.findings
    assert plan.recipe == "node-secrets-provision"
    assert plan.principal == "ops"
    assert plan.ssh_identity == creds.PROVISIONING_SSH_IDENTITY
    assert plan.seal_flag == creds.SEAL_FLAG == "--with-key=host"
    kinds = {step.kind for step in plan.steps}
    assert "mint_kek_on_vps" in kinds
    assert "stream_stdin_encrypt" in kinds
    assert "verify_is_set" in kinds
    kek = next(step for step in plan.steps if step.kind == "mint_kek_on_vps")
    assert kek.stdin_origin == "vps"
    assert plan.is_set["kek"] is True
    assert plan.is_set["backup-payload-key"] is True
    assert "backup-payload-key" in creds.NEVER_VPS_MINTED_SLOTS
    argv = creds.ssh_stdin_encrypt_argv(
        host="qmx-vps",
        identity_file="~/.ssh/qmx_provisioning",
        slot="venue-refresh-token",
    )
    assert "ssh" in argv
    assert "--with-key=host" in argv
    assert "--with-key=auto" not in argv
    assert "-" in argv
    assert not any(token.startswith("--name=") and " " in token for token in argv)
    payload = json.dumps(plan.to_jsonable())
    assert "fixture-" not in payload
    assert "--with-key=auto" not in payload


def test_plan_refuses_operator_identity_and_auto_seal() -> None:
    wizard = _load("qmn_deploy_secrets_s271b", _DEPLOY / "secrets_provision.py")
    bad_id = wizard.build_provision_plan(ssh_identity="operator")
    assert bad_id.ok is False
    assert any("provisioning" in item for item in bad_id.findings)
    bad_seal = wizard.build_provision_plan(seal_flag="--with-key=auto")
    assert bad_seal.ok is False
    assert any("with-key=host" in item for item in bad_seal.findings)


def test_missing_payload_key_is_not_vps_minted() -> None:
    wizard = _load("qmn_deploy_secrets_s271c", _DEPLOY / "secrets_provision.py")
    present = frozenset(
        {
            "venue-client-id",
            "venue-client-secret",
            "venue-access-token",
            "venue-refresh-token",
            "venue-ctid-accounts",
            "object-storage",
            "notification-token",
            "grafana-admin",
            "log-shipper-token",
        }
    )
    plan = wizard.build_provision_plan(present_slots=present)
    assert any(step.kind == "refuse_vps_mint" for step in plan.steps)
    assert plan.is_set["backup-payload-key"] is False
    assert any("never VPS-minted" in item for item in plan.findings)


def test_fixture_apply_streams_stdin_never_argv() -> None:
    wizard = _load("qmn_deploy_secrets_s271d", _DEPLOY / "secrets_provision.py")
    creds = _load("qmn_deploy_creds_s271d", _DEPLOY / "creds.py")
    plan = wizard.build_provision_plan(mode="apply")
    assert plan.ok
    source_values = {
        slot: f"fixture-{slot.replace('-', '')}-zzzzzzzz" for slot in creds.WORKSTATION_SLOTS
    }
    source = wizard.MappingCredentialSource(source_values)
    transport = wizard.RecordingSealTransport()
    is_set = wizard.apply_plan_to_fixture(plan, source=source, transport=transport)
    assert is_set["kek"] is True
    assert set(transport.sealed) >= {"kek", *creds.WORKSTATION_SLOTS}
    for argv in transport.argv_history:
        assert "--with-key=host" in argv
        assert "--with-key=auto" not in argv
        for material in source_values.values():
            assert not creds.argv_contains_plaintext(argv, material)
    dumped = json.dumps(plan.to_jsonable())
    for material in source_values.values():
        assert material not in dumped


def test_cli_refuses_apply_without_fixture_root() -> None:
    wizard = _load("qmn_deploy_secrets_s271e", _DEPLOY / "secrets_provision.py")
    assert wizard.main(["--apply"]) == 2


def test_cli_check_mode_writes_names_only(tmp_path: Path) -> None:
    wizard = _load("qmn_deploy_secrets_s271f", _DEPLOY / "secrets_provision.py")
    out = tmp_path / "plan.json"
    code = wizard.main(["--check-mode", "--out", str(out)])
    assert code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["recipe"] == "node-secrets-provision"
    assert payload["is_set"]["kek"] is True
    text = out.read_text(encoding="utf-8")
    assert "fixture-" not in text
    assert "--with-key=host" in text


def test_root_justfile_recipe_points_at_wizard() -> None:
    node_just = (_DEPLOY / "justfile-recipes" / "node.just").read_text(encoding="utf-8")
    assert "secrets_provision.py" in node_just
    assert "--with-key=host" in node_just
    assert "node-secrets-provision" in node_just
    root = (_WORKSPACE / "justfile").read_text(encoding="utf-8")
    assert 'import "./qmn/deploy/justfile-recipes/node.just"' in root


def test_unit_templates_match_creds_catalog() -> None:
    creds = _load("qmn_deploy_creds_s271g", _DEPLOY / "creds.py")
    units = _load("qmn_deploy_units_s271g", _DEPLOY / "systemd" / "units.py")
    rendered = units.render_all_templates(
        drain_window="30s",
        watchdog_interval="15s",
        deploy_root=_DEPLOY / "systemd",
    )
    qmn = rendered["qmn.service"]
    backup = rendered["qmn-backup.service"]
    obs = rendered["qmx-observability.service"]
    for slot in (
        "kek",
        "venue-client-id",
        "venue-refresh-token",
        "notification-token",
    ):
        assert f"LoadCredentialEncrypted={slot}" in qmn
    assert "LoadCredentialEncrypted=backup-payload-key" in backup
    assert "LoadCredentialEncrypted=grafana-admin" in obs
    assert creds.SEAL_FLAG == units.CREDENTIAL_SEAL_FLAG
    assert creds.FORBIDDEN_SEAL_FLAG == units.FORBIDDEN_SEAL_FLAG
    from qmn.secrets.holders import BOOTSTRAP_SLOT_NAMES, WORKSTATION_SLOTS

    assert set(creds.WORKSTATION_SLOTS) == set(WORKSTATION_SLOTS)
    assert set(creds.BOOTSTRAP_SLOT_NAMES) == set(BOOTSTRAP_SLOT_NAMES)
