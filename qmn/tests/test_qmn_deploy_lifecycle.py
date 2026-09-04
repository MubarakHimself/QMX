"""Story 28.4 — lifecycle and security-probe DevOps recipes (check-mode)."""

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
_MAX_READ_BYTES = 1 << 20


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _read_contained(path: Path, *, contain_within: Path) -> str:
    name = "qmn_deploy_safe_io_lifecycle"
    module = sys.modules.get(name)
    if module is None:
        module = _load(name, _DEPLOY / "safe_io.py")
    return module.read_text_contained(
        path, contain_within=contain_within, max_bytes=_MAX_READ_BYTES
    )


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(_read_contained(path, contain_within=_QMN_ROOT), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


@pytest.fixture(scope="module")
def lifecycle_mod() -> ModuleType:
    return _load("qmn_deploy_lifecycle_28_4", _DEPLOY / "lifecycle.py")


@pytest.fixture(scope="module")
def security_mod() -> ModuleType:
    return _load("qmn_deploy_security_probes_28_4", _DEPLOY / "security_probes.py")


@pytest.fixture(scope="module")
def boundary_mod() -> ModuleType:
    return _load("qmn_deploy_boundary_test28_4", _DEPLOY / "boundary.py")


def test_recipes_are_on_the_closed_allow_list_and_cannot_trade(
    boundary_mod: ModuleType,
) -> None:
    assert "node-lifecycle-campaign" in boundary_mod.ALLOWED_NODE_RECIPES
    assert "node-security-probes" in boundary_mod.ALLOWED_NODE_RECIPES
    for action in (
        "place",
        "cancel",
        "amend",
        "flatten",
        "promote",
        "activate",
        "settings",
        "resurrect",
        "attestation",
        "countersign",
    ):
        assert boundary_mod.recipe_action_allowed(action) is False
    just_text = _read_contained(
        _DEPLOY / "justfile-recipes" / "node.just", contain_within=_QMN_ROOT
    )
    assert "node-lifecycle-campaign" in just_text
    assert "node-security-probes" in just_text
    assert "never a trading control" in just_text.lower() or "never trades" in just_text.lower()


def test_lifecycle_plan_lists_injections_and_skips_live_campaigns(
    lifecycle_mod: ModuleType, boundary_mod: ModuleType, tmp_path: Path
) -> None:
    plan = lifecycle_mod.build_lifecycle_campaign_plan(mode="check")
    assert plan.ok is True
    assert plan.recipe == "node-lifecycle-campaign"
    assert plan.principal == boundary_mod.OPS_PRINCIPAL_NAME
    assert plan.runs_live_vps_firewall is False
    assert plan.runs_live_bucket_restore is False
    assert plan.devops_unable_to_trade is True
    assert plan.injections == (
        "crash-loop",
        "preflight",
        "callback-wedge",
        "clock",
        "disk",
        "data-freshness",
        "shutdown",
    )
    kinds = {step.kind for step in plan.steps}
    assert "inject" in kinds
    assert "skip" in kinds
    targets = {step.target for step in plan.steps}
    assert "live-vps-firewall" in targets
    assert "live-bucket-restore" in targets
    out = lifecycle_mod.apply_plan_to_fixture(plan, tmp_path)
    payload = json.loads(_read_contained(out, contain_within=tmp_path))
    assert payload["ok"] is True
    assert payload["runs_live_vps_firewall"] is False


def test_lifecycle_main_refuses_live_apply_and_live_campaigns(
    lifecycle_mod: ModuleType, tmp_path: Path
) -> None:
    assert lifecycle_mod.main(["--live-firewall"]) == 2
    assert lifecycle_mod.main(["--live-bucket-restore"]) == 2
    assert lifecycle_mod.main(["--apply"]) == 2
    assert lifecycle_mod.main(["--fixture-root", str(tmp_path)]) == 0
    assert (tmp_path / "lifecycle-campaign.json").is_file()


def test_security_plan_inspects_units_and_refuses_live_firewall(
    security_mod: ModuleType, boundary_mod: ModuleType, tmp_path: Path
) -> None:
    plan = security_mod.build_security_probe_plan(mode="check")
    assert plan.ok is True, plan.findings
    assert plan.recipe == "node-security-probes"
    assert plan.principal == boundary_mod.OPS_PRINCIPAL_NAME
    assert plan.qmx_identity is True
    assert plan.no_dynamic_user is True
    assert plan.inbound_default_deny is True
    assert plan.loopback_unix_only_doors is True
    assert plan.no_automatic_reboot is True
    assert plan.devops_unable_to_trade is True
    assert plan.runs_live_vps_firewall is False
    assert "unknown-peer" in plan.probes
    assert "sandbox-promotion" in plan.probes
    out = security_mod.apply_plan_to_fixture(plan, tmp_path)
    payload = json.loads(_read_contained(out, contain_within=tmp_path))
    assert payload["no_dynamic_user"] is True
    assert payload["ok"] is True


def test_security_main_refuses_live_firewall(security_mod: ModuleType, tmp_path: Path) -> None:
    assert security_mod.main(["--live-firewall"]) == 2
    assert security_mod.main(["--apply"]) == 2
    assert security_mod.main(["--fixture-root", str(tmp_path)]) == 0
    assert (tmp_path / "security-probes.json").is_file()


def test_deploy_scripts_never_import_qmn() -> None:
    for name in ("lifecycle.py", "security_probes.py"):
        path = _DEPLOY / name
        for imported in _imported_modules(path):
            assert imported != "qmn"
            assert not imported.startswith("qmn.")


def test_deploy_scripts_stay_under_read_cap() -> None:
    for name in ("lifecycle.py", "security_probes.py"):
        size = (_DEPLOY / name).stat().st_size
        assert size <= _MAX_READ_BYTES
