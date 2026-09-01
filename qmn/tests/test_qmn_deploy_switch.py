"""Story 25.18 — switch, roll back, and verify the Ubuntu release.

Covers FR-068 / TN-16 / NFR-18/21: check-mode-first switch, atomic current
symlink flip, paired (commit, config) deployment records, recoverable previous
tree, no auto-reboot/auto-restart from routine upgrades, and the pinned
ubuntu-24.04 lane compensators. Never SSHes to Contabo; never imports trading
controls.
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
_FIXTURES = _DEPLOY / "fixtures"
_WORKSPACE = _QMN_ROOT.parent
_MAX_FIXTURE_BYTES = 1 << 20  # 1 MiB


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _read_fixture_text(path: Path) -> str:
    """Read a fixture as a regular in-root non-symlink file under a size cap."""
    resolved = path.resolve()
    assert not path.is_symlink(), resolved
    assert resolved.is_file() and resolved.is_relative_to(_WORKSPACE), resolved
    size = resolved.stat().st_size
    assert size <= _MAX_FIXTURE_BYTES, resolved
    return resolved.read_text(encoding="utf-8")


def _try_symlink(link: Path, target: Path) -> None:
    """Create a symlink or skip where the platform forbids it (Windows without privilege)."""
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not permitted on this platform")


@pytest.fixture(scope="module")
def switch_mod() -> ModuleType:
    return _load("qmn_deploy_switch_test", _DEPLOY / "switch.py")


@pytest.fixture(scope="module")
def upgrade_mod() -> ModuleType:
    return _load("qmn_deploy_upgrade_test", _DEPLOY / "upgrade.py")


@pytest.fixture(scope="module")
def ci_lane_mod() -> ModuleType:
    return _load("qmn_deploy_ci_lane_test", _DEPLOY / "ci_lane.py")


@pytest.fixture(scope="module")
def boundary_mod() -> ModuleType:
    return _load("qmn_deploy_boundary_test25_18", _DEPLOY / "boundary.py")


def test_switch_check_mode_plan_orders_check_before_flip(
    switch_mod: ModuleType, boundary_mod: ModuleType
) -> None:
    plan = switch_mod.build_switch_plan(
        commit="abc1234",
        config_version="cfg-1",
        mode="check",
    )
    assert plan.ok, plan.findings
    assert plan.recipe == "node-switch"
    assert plan.principal == boundary_mod.OPS_PRINCIPAL_NAME == "ops"
    assert plan.mode == "check"
    assert plan.auto_reboot is False
    assert plan.auto_restart is False
    kinds = [s.kind for s in plan.steps]
    assert kinds.index("check_mode_boot") < kinds.index("atomic_symlink_flip")
    assert kinds.index("preflight") == 0
    assert "deployment_record" in kinds
    assert "prune" in kinds
    assert plan.record.commit == "abc1234"
    assert plan.record.config_version == "cfg-1"
    assert plan.record.to_jsonable()["pair"] == ["abc1234", "cfg-1"]
    assert all(s.check_mode_only for s in plan.steps)
    assert switch_mod.REQUESTED_RESTART_EXIT == 75


def test_switch_refuses_blank_config_or_failed_check(switch_mod: ModuleType) -> None:
    bad = switch_mod.build_switch_plan(
        commit="abc1234",
        config_version="",
        mode="check",
    )
    assert bad.ok is False
    assert any("config_version" in f for f in bad.findings)

    refused = switch_mod.build_switch_plan(
        commit="abc1234",
        config_version="cfg-1",
        mode="check",
        check_mode_ok=False,
    )
    assert refused.ok is False
    assert any("check-mode" in f for f in refused.findings)


def test_fixture_switch_atomic_flip_pairs_commit_and_config(
    switch_mod: ModuleType, tmp_path: Path
) -> None:
    root = tmp_path / "opt-qmx"
    plan_a = switch_mod.build_switch_plan(
        commit="aaaaaaa1",
        config_version="cfg-a",
        mode="apply",
        opt_qmx=root,
    )
    assert plan_a.ok
    switch_mod.apply_plan_to_fixture(plan_a, root)
    assert switch_mod.read_current_commit(root) == "aaaaaaa1"
    record_a = switch_mod.load_deployment_record(
        switch_mod.record_path(root, "aaaaaaa1")
    )
    assert record_a.config_version == "cfg-a"
    assert (root / "trees" / "aaaaaaa1" / ".qmx-release").is_file()

    plan_b = switch_mod.build_switch_plan(
        commit="bbbbbbb2",
        config_version="cfg-b",
        mode="apply",
        opt_qmx=root,
        previous_commit="aaaaaaa1",
        previous_config_version="cfg-a",
    )
    switch_mod.apply_plan_to_fixture(plan_b, root)
    assert switch_mod.read_current_commit(root) == "bbbbbbb2"
    record_b = switch_mod.load_deployment_record(
        switch_mod.record_path(root, "bbbbbbb2")
    )
    assert record_b.previous_commit == "aaaaaaa1"
    assert record_b.previous_config_version == "cfg-a"
    assert (root / "trees" / "aaaaaaa1").is_dir()


def test_rollback_recovers_previous_pair_without_network(
    switch_mod: ModuleType, tmp_path: Path
) -> None:
    root = tmp_path / "opt-qmx"
    switch_mod.apply_plan_to_fixture(
        switch_mod.build_switch_plan(
            commit="aaaaaaa1",
            config_version="cfg-a",
            mode="apply",
            opt_qmx=root,
        ),
        root,
    )
    switch_mod.apply_plan_to_fixture(
        switch_mod.build_switch_plan(
            commit="bbbbbbb2",
            config_version="cfg-b",
            mode="apply",
            opt_qmx=root,
        ),
        root,
    )
    assert switch_mod.read_current_commit(root) == "bbbbbbb2"

    rollback = switch_mod.build_rollback_plan(mode="apply", opt_qmx=root)
    assert rollback.ok, rollback.findings
    assert rollback.network_required is False
    assert rollback.auto_reboot is False
    assert all(not s.requires_network for s in rollback.steps)
    applied = switch_mod.apply_plan_to_fixture(rollback, root)
    assert applied.commit == "aaaaaaa1"
    assert applied.config_version == "cfg-a"
    assert switch_mod.read_current_commit(root) == "aaaaaaa1"
    assert (root / "trees" / "bbbbbbb2").is_dir()


def test_upgrade_policy_never_auto_reboots_or_restarts_node(
    upgrade_mod: ModuleType,
) -> None:
    policy = upgrade_mod.default_upgrade_policy()
    assert policy.automatic_reboot is False
    assert policy.allow_auto_node_switch is False
    assert policy.may_stage_and_verify is True
    assert policy.release_change_recipe == "node-switch"
    assert "qmn.service" in policy.never_restart_units

    apt = upgrade_mod.apt_unattended_fragment()
    nr = upgrade_mod.needrestart_fragment()
    findings = upgrade_mod.inspect_upgrade_policy(
        policy, fragments={"apt": apt, "needrestart": nr}
    )
    assert findings == ()

    fixture_apt = _read_fixture_text(
        _FIXTURES / "upgrade-policy" / upgrade_mod.APT_UNATTENDED_FRAGMENT_NAME
    )
    fixture_nr = _read_fixture_text(
        _FIXTURES / "upgrade-policy" / upgrade_mod.NEEDRESTART_FRAGMENT_NAME
    )
    assert 'Automatic-Reboot "false"' in fixture_apt
    assert "qmn.service" in fixture_nr

    bad = upgrade_mod.UpgradePolicy(
        automatic_reboot=True,
        allow_auto_node_switch=True,
        allow_auto_restart_units=("qmn.service",),
        never_restart_units=(),
        may_stage_and_verify=True,
        release_change_recipe="apt-unattended",
    )
    bad_findings = upgrade_mod.inspect_upgrade_policy(bad)
    assert any("automatic_reboot" in f for f in bad_findings)
    assert any("allow_auto_node_switch" in f for f in bad_findings)


def test_ci_lane_contract_and_compensators(ci_lane_mod: ModuleType) -> None:
    assert ci_lane_mod.CI_LANE_RUNNER == "ubuntu-24.04"
    assert "latest" not in ci_lane_mod.CI_LANE_RUNNER
    assert "node-rollback-symlink-flip" in ci_lane_mod.COMPENSATING_CONTROLS
    assert "check-mode-dry-run" in ci_lane_mod.COMPENSATING_CONTROLS

    report = ci_lane_mod.run_lane(
        include_typing=False,
        include_isolated_install=False,
    )
    assert report.ok, [(s.name, s.detail) for s in report.steps if not s.ok]
    assert report.to_jsonable()["staging_host"] is False
    names = {s.name for s in report.steps}
    assert {
        "runner_pin",
        "unit_iac_scan",
        "check_mode_boot",
        "scratch_credstore_boot",
        "upgrade_rollback_contract",
    } <= names


def test_cli_check_mode_and_apply_refusal(
    switch_mod: ModuleType, tmp_path: Path
) -> None:
    out = tmp_path / "plan.json"
    code = switch_mod.main(
        [
            "node-switch",
            "--commit",
            "abc1234",
            "--config-version",
            "cfg-1",
            "--check-mode",
            "--out",
            str(out),
        ]
    )
    assert code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["recipe"] == "node-switch"

    apply_code = switch_mod.main(
        ["node-switch", "--commit", "abc1234", "--config-version", "cfg-1", "--apply"]
    )
    assert apply_code == 2

    fixture = tmp_path / "fixture-opt"
    code_fix = switch_mod.main(
        [
            "node-switch",
            "--commit",
            "abc1234",
            "--config-version",
            "cfg-1",
            "--fixture-root",
            str(fixture),
        ]
    )
    assert code_fix == 0
    assert switch_mod.read_current_commit(fixture) == "abc1234"


def test_deploy_surface_never_imports_composition_or_trade(
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
    assert "node-switch" in just_text
    assert "node-rollback" in just_text
    assert "switch.py" in just_text
    assert "node-switch" in boundary_mod.ALLOWED_NODE_RECIPES
    assert "node-rollback" in boundary_mod.ALLOWED_NODE_RECIPES
    assert boundary_mod.deploy_may_import("qmn.host") is False
    assert boundary_mod.recipe_action_allowed("promote") is False


def test_workflow_pins_ubuntu_24_04_never_latest() -> None:
    workflow = (
        _WORKSPACE / ".github" / "workflows" / "qmn-ubuntu-24.04.yml"
    ).read_text(encoding="utf-8")
    assert "ubuntu-24.04" in workflow
    assert "runs-on: ubuntu-24.04" in workflow
    assert not any(
        line.strip().startswith("runs-on:") and "latest" in line
        for line in workflow.splitlines()
    )
    assert "pythonplatform Linux" in workflow.casefold() or "--pythonplatform" in workflow
    assert "ci_lane.py" in workflow
    assert "LoadCredentialEncrypted" in workflow or "scratch" in workflow.casefold()
    assert "node-rollback" in workflow or "rollback" in workflow


def test_write_plan_refuses_symlink_destination(
    switch_mod: ModuleType, tmp_path: Path
) -> None:
    plan = switch_mod.build_switch_plan(
        commit="abc1234",
        config_version="cfg-1",
        mode="check",
    )
    outside = tmp_path / "outside.json"
    outside.write_text("keep\n", encoding="utf-8")
    link = tmp_path / "plan.json"
    _try_symlink(link, outside)
    with pytest.raises(OSError, match="symlink"):
        switch_mod.write_plan(plan, link)
    assert outside.read_text(encoding="utf-8") == "keep\n"


def test_load_deployment_record_refuses_symlink_and_oversize(
    switch_mod: ModuleType, tmp_path: Path
) -> None:
    deployments = tmp_path / "deployments"
    deployments.mkdir()
    outside = tmp_path / "secret.json"
    outside.write_text('{"commit":"deadbeef","config_version":"x"}\n', encoding="utf-8")
    link = deployments / "deadbeef.json"
    _try_symlink(link, outside)
    with pytest.raises(OSError, match="symlink"):
        switch_mod.load_deployment_record(link)

    big = deployments / "big.json"
    big.write_text("x" * ((_MAX_FIXTURE_BYTES) + 1), encoding="utf-8")
    with pytest.raises(OSError, match="size cap"):
        switch_mod.load_deployment_record(big)


def test_write_fragments_refuses_symlink(
    upgrade_mod: ModuleType, tmp_path: Path
) -> None:
    dest = tmp_path / "upgrade-policy"
    dest.mkdir()
    outside = tmp_path / "outside.conf"
    outside.write_text("keep\n", encoding="utf-8")
    link = dest / upgrade_mod.APT_UNATTENDED_FRAGMENT_NAME
    _try_symlink(link, outside)
    with pytest.raises(OSError, match="symlink"):
        upgrade_mod.write_fragments(dest)
    assert outside.read_text(encoding="utf-8") == "keep\n"


def test_apply_plan_refuses_symlinked_release_marker(
    switch_mod: ModuleType, tmp_path: Path
) -> None:
    root = tmp_path / "opt-qmx"
    plan = switch_mod.build_switch_plan(
        commit="ccccccc3",
        config_version="cfg-c",
        mode="apply",
        opt_qmx=root,
    )
    tree = switch_mod.tree_path(root, "ccccccc3")
    tree.mkdir(parents=True)
    outside = tmp_path / "outside-release"
    outside.write_text("keep\n", encoding="utf-8")
    marker = tree / ".qmx-release"
    _try_symlink(marker, outside)
    with pytest.raises(OSError, match="symlink"):
        switch_mod.apply_plan_to_fixture(plan, root)
    assert outside.read_text(encoding="utf-8") == "keep\n"


def test_atomic_symlink_pointer_fallback_uses_exclusive_no_follow(
    switch_mod: ModuleType,
) -> None:
    source = (_DEPLOY / "switch.py").read_text(encoding="utf-8")
    assert "write_text_exclusive_no_follow" in source
    assert "tmp.write_text" not in source
    # Pointer-file fallback must stay contained under the link parent.
    assert "contain_within=link.parent" in source


def test_atomic_symlink_to_writes_pointer_when_symlink_unavailable(
    switch_mod: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    link = tmp_path / "current"
    target = tmp_path / "trees" / "abc1234"
    target.mkdir(parents=True)

    def _refuse_symlink(self: Path, *args: object, **kwargs: object) -> None:
        raise OSError("symlink unavailable")

    monkeypatch.setattr(Path, "symlink_to", _refuse_symlink)
    switch_mod._atomic_symlink_to(link, target)
    assert link.is_file() and not link.is_symlink()
    assert link.read_text(encoding="utf-8") == "abc1234\n"
