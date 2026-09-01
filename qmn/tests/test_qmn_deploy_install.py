"""Story 25.12 — Ubuntu service + five governed units (check-mode / fixtures).

Covers FR-068 / AR-77 / AR-78 / NFR-14 unit hardening, credential scoping,
network posture, and the ops-toolkit ``node-install`` planner. Never SSHes
to Contabo; never imports trading controls.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

_QMN_ROOT = Path(__file__).resolve().parents[1]
_DEPLOY = _QMN_ROOT / "deploy"
_TEMPLATES = _DEPLOY / "systemd" / "templates"
_FIXTURES = _DEPLOY / "fixtures"
_WORKSPACE = _QMN_ROOT.parent
_MAX_READ_BYTES = 1 << 20  # 1 MiB


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _try_symlink(link: Path, target: Path) -> None:
    """Create a symlink or skip where the platform forbids it (Windows without privilege)."""
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not permitted on this platform")


@pytest.fixture(scope="module")
def units_mod() -> ModuleType:
    return _load("qmn_deploy_units_test", _DEPLOY / "systemd" / "units.py")


@pytest.fixture(scope="module")
def network_mod() -> ModuleType:
    return _load("qmn_deploy_network_test", _DEPLOY / "network.py")


@pytest.fixture(scope="module")
def install_mod() -> ModuleType:
    return _load("qmn_deploy_install_test", _DEPLOY / "install.py")


@pytest.fixture(scope="module")
def boundary_mod() -> ModuleType:
    return _load("qmn_deploy_boundary_test25_12", _DEPLOY / "boundary.py")


def test_five_node_unit_templates_plus_observability_exist() -> None:
    expected = {
        "qmn.service.in",
        "qmn-news-calendar.service.in",
        "qmn-news-calendar.timer",
        "qmn-backup.service.in",
        "qmn-backup.timer",
        "qmn-restore-sample.service.in",
        "qmn-restore-sample.timer",
        "qmn-restore-full.service.in",
        "qmn-restore-full.timer",
        "qmx-observability.service.in",
    }
    present = {p.name for p in _TEMPLATES.iterdir() if p.is_file()}
    assert expected <= present


def test_render_and_iac_security_contract(units_mod: ModuleType) -> None:
    values = json.loads((_FIXTURES / "render-values.json").read_text(encoding="utf-8"))
    rendered = units_mod.render_all_templates(
        drain_window=values["drain_window"],
        watchdog_interval=values["watchdog_interval"],
        deploy_root=_DEPLOY / "systemd",
    )
    assert "qmn.service" in rendered
    assert "qmx-observability.service" in rendered
    assert "@DRAIN_WINDOW_SEC@" not in rendered["qmn.service"]
    assert "@WATCHDOG_INTERVAL_SEC@" not in rendered["qmn.service"]
    assert "TimeoutStopSec=30s" in rendered["qmn.service"]
    assert "WatchdogSec=15s" in rendered["qmn.service"]

    inspections = units_mod.inspect_rendered_units(rendered)
    failures = [item for item in inspections if not item.ok]
    assert failures == [], [f"{f.name}: {f.findings}" for f in failures]

    node_names = units_mod.node_unit_names()
    assert "qmn.service" in node_names
    assert "qmx-observability.service" not in node_names
    assert units_mod.OBSERVABILITY_UNIT not in node_names


def test_node_units_fixed_qmx_no_dynamic_user(units_mod: ModuleType) -> None:
    rendered = units_mod.render_all_templates(
        drain_window="30s",
        watchdog_interval="15s",
        deploy_root=_DEPLOY / "systemd",
    )
    for name, text in rendered.items():
        if name.endswith(".timer"):
            continue
        if name == "qmx-observability.service":
            assert "User=qmxobs" in text
            assert "User=qmx\n" not in text.replace("User=qmxobs", "")
        else:
            assert "User=qmx" in text
        assert "DynamicUser=yes" not in text.lower()
        assert "ProtectSystem=strict" in text
        assert "NoNewPrivileges=true" in text
        assert "PrivateTmp=true" in text
        assert "ProtectHome=true" in text
        assert "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6" in text


def test_credential_scoping_and_host_key_seal_contract(
    units_mod: ModuleType, install_mod: ModuleType
) -> None:
    rendered = units_mod.render_all_templates(
        drain_window="30s",
        watchdog_interval="15s",
        deploy_root=_DEPLOY / "systemd",
    )
    qmn = rendered["qmn.service"]
    assert "LoadCredentialEncrypted=kek" in qmn
    assert "LoadCredentialEncrypted=venue-client-id" in qmn
    assert "LoadCredentialEncrypted=notification-token" in qmn
    assert "LoadCredential=" not in qmn.replace("LoadCredentialEncrypted=", "")

    backup = rendered["qmn-backup.service"]
    assert "LoadCredentialEncrypted=backup-payload-key" in backup
    assert "venue-client-id" not in backup
    for line in backup.splitlines():
        if line.startswith("LoadCredentialEncrypted="):
            cred = line.split("=", 1)[1]
            assert not cred.startswith("venue-")
            assert cred != "kek"

    news = rendered["qmn-news-calendar.service"]
    assert "LoadCredentialEncrypted=" not in news

    obs = rendered["qmx-observability.service"]
    assert "LoadCredentialEncrypted=grafana-admin" in obs
    assert "venue-client" not in obs
    assert "LogNamespace=qmn" in rendered["qmn.service"]

    plan = install_mod.build_install_plan(
        mode="check",
        render_values={"drain_window": "30s", "watchdog_interval": "15s"},
        deploy_root=_DEPLOY,
    )
    cred_steps = [s for s in plan.steps if s.kind == "credstore"]
    assert len(cred_steps) == 1
    assert units_mod.CREDENTIAL_SEAL_FLAG in cred_steps[0].detail
    assert units_mod.FORBIDDEN_SEAL_FLAG in cred_steps[0].detail


def test_network_posture_default_deny(network_mod: ModuleType) -> None:
    posture = network_mod.default_network_posture()
    findings = network_mod.validate_network_posture(posture)
    assert findings == ()
    assert posture.inbound_default == "deny"
    assert posture.egress_default == "deny"
    assert posture.public_node_doors is False
    assert posture.observability_public_inbound is False
    assert posture.powers_transport == "unix-socket"
    assert set(posture.ssh_identities) == {
        "operator",
        "provisioning",
        "hub-inbox-write",
    }
    assert "ctrader" in posture.egress_allow
    assert "forex-factory-news" in posture.egress_allow
    assert "ntp" in posture.egress_allow


def test_network_posture_rejects_public_doors(network_mod: ModuleType) -> None:
    bad = network_mod.NetworkPosture(
        inbound_default="deny",
        ssh_identities=network_mod.INBOUND_SSH_IDENTITIES,
        ssh_password_auth=False,
        public_node_doors=True,
        powers_transport="unix-socket",
        loopback_listeners=network_mod.LOOPBACK_ONLY_LISTENERS,
        egress_default="deny",
        egress_allow=network_mod.EGRESS_ALLOW_CLASSES,
        observability_public_inbound=True,
    )
    findings = network_mod.validate_network_posture(bad)
    assert any("public" in f for f in findings)
    assert any("observability" in f for f in findings)


def test_node_install_check_mode_plan(
    install_mod: ModuleType, boundary_mod: ModuleType, tmp_path: Path
) -> None:
    values = json.loads((_FIXTURES / "render-values.json").read_text(encoding="utf-8"))
    plan = install_mod.build_install_plan(
        mode="check",
        render_values=values,
        deploy_root=_DEPLOY,
    )
    assert plan.ok, (plan.unit_findings, plan.network_findings)
    assert plan.recipe == "node-install"
    assert plan.principal == boundary_mod.OPS_PRINCIPAL_NAME == "ops"
    assert plan.mode == "check"
    kinds = {s.kind for s in plan.steps}
    assert {
        "bootstrap",
        "account",
        "tree",
        "unit",
        "sync",
        "credstore",
        "network",
        "compose",
        "quota",
    } <= kinds
    assert any(s.detail == "uv sync --frozen" for s in plan.steps)
    assert any(s.target == "/opt/qmx" for s in plan.steps)
    assert any(s.target == "/var/lib/qmx/rooms" for s in plan.steps)
    assert any(s.target == "/run/qmn/powers.sock" for s in plan.steps)
    assert any(s.target == "qmx-observability.service" for s in plan.steps)
    assert any(s.target == "container-runtime" for s in plan.steps)
    assert any(s.target == "/var/lib/qmx-observability" for s in plan.steps if s.kind == "quota")
    assert all(s.check_mode_only for s in plan.steps)

    out = tmp_path / "plan.json"
    install_mod.write_plan(plan, out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    rendered_dir = tmp_path / "rendered-units"
    assert (rendered_dir / "qmn.service").is_file()
    assert (rendered_dir / "qmx-observability.service").is_file()


def test_node_install_cli_check_mode(install_mod: ModuleType, tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    code = install_mod.main(
        [
            "--check-mode",
            "--values",
            str(_FIXTURES / "render-values.json"),
            "--out",
            str(out),
        ]
    )
    assert code == 0
    assert out.is_file()
    apply_code = install_mod.main(["--apply"])
    assert apply_code == 2


def test_blank_drain_window_refuses_render(units_mod: ModuleType) -> None:
    with pytest.raises(ValueError, match="blank"):
        units_mod.duration_to_systemd_sec("")
    with pytest.raises(ValueError, match="drain_window"):
        units_mod.render_template(
            "TimeoutStopSec=@DRAIN_WINDOW_SEC@\n",
            drain_window=None,
            watchdog_interval="15s",
        )


def test_deploy_recipes_never_import_composition_or_trade(
    boundary_mod: ModuleType,
) -> None:
    for path in sorted(_DEPLOY.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("qmn."), path
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                assert not node.module.startswith("qmn."), path
                assert node.module != "qmn"

    just_text = (_DEPLOY / "justfile-recipes" / "node.just").read_text(encoding="utf-8")
    for action in boundary_mod.FORBIDDEN_RECIPE_ACTIONS:
        # Recipe names may mention reserved surfaces; bodies must not invoke acts.
        if action in {"settings", "resurrect", "attestation", "countersign"}:
            continue
        assert f" {action} " not in f" {just_text} "
    assert "node-install" in boundary_mod.ALLOWED_NODE_RECIPES
    assert boundary_mod.recipe_action_allowed("place") is False
    assert boundary_mod.deploy_may_import("qmn.host") is False


def test_root_justfile_imports_node_recipes() -> None:
    text = (_WORKSPACE / "justfile").read_text(encoding="utf-8")
    assert 'import "./qmn/deploy/justfile-recipes/node.just"' in text
    node_just = (_DEPLOY / "justfile-recipes" / "node.just").read_text(encoding="utf-8")
    assert "node-install" in node_just
    assert "trading" in node_just.lower() or "DevOps" in node_just


def test_write_plan_refuses_symlink_destination(
    install_mod: ModuleType, tmp_path: Path
) -> None:
    plan = install_mod.build_install_plan(
        mode="check",
        render_values={"drain_window": "30s", "watchdog_interval": "15s"},
        deploy_root=_DEPLOY,
    )
    outside = tmp_path / "outside.json"
    outside.write_text("keep\n", encoding="utf-8")
    link = tmp_path / "plan.json"
    _try_symlink(link, outside)
    with pytest.raises(OSError, match="symlink"):
        install_mod.write_plan(plan, link)
    assert outside.read_text(encoding="utf-8") == "keep\n"


def test_load_render_values_refuses_symlink_and_oversize(
    install_mod: ModuleType, tmp_path: Path
) -> None:
    outside = tmp_path / "secret.json"
    outside.write_text('{"drain_window":"1s","watchdog_interval":"1s"}\n', encoding="utf-8")
    link = tmp_path / "values.json"
    _try_symlink(link, outside)
    with pytest.raises(OSError, match="symlink"):
        install_mod.load_render_values(link)

    big = tmp_path / "big.json"
    big.write_text("x" * (_MAX_READ_BYTES + 1), encoding="utf-8")
    with pytest.raises(OSError, match="size cap"):
        install_mod.load_render_values(big)

    ok = install_mod.load_render_values(_FIXTURES / "render-values.json")
    assert ok["drain_window"]
    assert ok["watchdog_interval"]
