"""Story 28.2 — first-deployment demo-shape deploy planner (check-mode / fixtures)."""

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
_TEMPLATES = _DEPLOY / "systemd" / "templates"
_WORKSPACE = _QMN_ROOT.parent
_MAX_READ_BYTES = 1 << 20


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _try_symlink(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not permitted on this platform")


@pytest.fixture(scope="module")
def demo_mod() -> ModuleType:
    return _load("qmn_deploy_demo_test", _DEPLOY / "demo.py")


@pytest.fixture(scope="module")
def boundary_mod() -> ModuleType:
    return _load("qmn_deploy_boundary_test28_2", _DEPLOY / "boundary.py")


def test_fixture_inventory_is_production_shape_with_paper_routing() -> None:
    payload = json.loads((_FIXTURES / "demo-shape.json").read_text(encoding="utf-8"))
    assert payload["book_routing"] == "PAPER"
    assert payload["procures_vps"] is False
    assert payload["opens_live_credentials"] is False
    assert payload["window"] == "first-deployment"
    units = set(payload["units"])
    assert "qmn.service" in units
    assert "qmx-observability.service" in units
    assert set(payload["node_timers"]) == {
        "qmn-news-calendar.timer",
        "qmn-backup.timer",
        "qmn-restore-sample.timer",
        "qmn-restore-full.timer",
    }
    for name in payload["units"]:
        if name.endswith(".timer"):
            assert (_TEMPLATES / name).is_file()
        else:
            assert (_TEMPLATES / f"{name}.in").is_file()
    assert payload["trees"] == ["rooms", "evidence", "hub-inbox", "hub-published"]
    assert payload["doors"] == ["powers", "evidence"]
    assert "live-binding" in payload["live_sensing"]["forbidden"]
    assert "sensing" in payload["live_sensing"]["allowed"]
    docs = (_DEPLOY / "DEMO-SHAPE.txt").read_text(encoding="utf-8")
    assert "Book routing" in docs
    assert "PAPER" in docs
    assert "does not procure a VPS" in docs


def test_check_mode_plan_is_paper_and_lists_production_inventory(
    demo_mod: ModuleType, boundary_mod: ModuleType
) -> None:
    plan = demo_mod.build_demo_shape_plan(mode="check")
    assert plan.ok is True
    assert plan.recipe == "node-demo-deploy"
    assert plan.principal == boundary_mod.OPS_PRINCIPAL_NAME
    assert plan.book_routing == "PAPER"
    assert plan.procures_vps is False
    assert plan.opens_live_credentials is False
    assert plan.auto_reboot is False
    assert plan.auto_restart is False
    assert "qmn.service" in plan.units
    assert "qmx-observability.service" in plan.units
    assert plan.node_timers == (
        "qmn-news-calendar.timer",
        "qmn-backup.timer",
        "qmn-restore-sample.timer",
        "qmn-restore-full.timer",
    )
    assert plan.trees == ("rooms", "evidence", "hub-inbox", "hub-published")
    assert plan.doors == ("powers", "evidence")
    kinds = {step.kind for step in plan.steps}
    assert {"unit", "timer", "tree", "door", "routing", "account", "live-sensing"} <= kinds
    assert plan.live_sensing_open is False
    assert plan.late_live_delays == ("live-baseline", "go-live")
    assert "vps_procurement" in plan.blocked_infra
    assert any("PAPER" in note for note in plan.notes)


def test_live_credentials_plan_sensing_only_never_live_binding(
    demo_mod: ModuleType,
) -> None:
    plan = demo_mod.build_demo_shape_plan(
        mode="check",
        live_credentials_present=True,
    )
    assert plan.ok is True
    assert plan.live_sensing_open is True
    assert plan.late_live_delays == ()
    assert "live-binding" in plan.live_sensing_forbidden
    assert "command-stream" in plan.live_sensing_forbidden
    sensing = [step for step in plan.steps if step.kind == "live-sensing"]
    assert sensing
    assert "no live binding" in sensing[0].detail

    refused = demo_mod.build_demo_shape_plan(
        mode="check",
        live_credentials_present=True,
        request_live_binding=True,
    )
    assert refused.ok is False
    assert any("live binding" in finding for finding in refused.findings)


def test_forbidden_provisioning_flags_fail_the_plan(demo_mod: ModuleType) -> None:
    procure = demo_mod.build_demo_shape_plan(mode="check", procure_vps=True)
    assert procure.ok is False
    assert any("procure" in finding for finding in procure.findings)
    opened = demo_mod.build_demo_shape_plan(mode="check", open_live_credentials=True)
    assert opened.ok is False
    assert any("live credentials" in finding for finding in opened.findings)
    live_route = demo_mod.build_demo_shape_plan(mode="check", book_routing="LIVE")
    assert live_route.ok is False
    assert any("PAPER" in finding for finding in live_route.findings)


def test_apply_without_fixture_root_is_refused(demo_mod: ModuleType) -> None:
    code = demo_mod.main(["--apply"])
    assert code == 2


def test_fixture_apply_writes_paper_shape(demo_mod: ModuleType, tmp_path: Path) -> None:
    fixture = tmp_path / "opt-qmx"
    code = demo_mod.main(
        [
            "--apply",
            "--fixture-root",
            str(fixture),
            "--commit",
            "abc1234",
            "--config-version",
            "cfg-1",
            "--synthetic-alert-delivered",
            "--missing-heartbeat-delivered",
        ]
    )
    assert code == 0
    record = fixture / "demo-shape.json"
    assert record.is_file()
    payload = json.loads(record.read_text(encoding="utf-8"))
    assert payload["book_routing"] == "PAPER"
    assert payload["ok"] is True
    assert payload["procures_vps"] is False
    assert payload["opens_live_credentials"] is False
    assert payload["pre_unattended"]["synthetic_alert_delivered"] is True
    assert payload["pre_unattended"]["missing_heartbeat_delivered"] is True


def test_write_plan_refuses_symlink_destination(demo_mod: ModuleType, tmp_path: Path) -> None:
    plan = demo_mod.build_demo_shape_plan(mode="check")
    outside = tmp_path / "outside.json"
    outside.write_text("keep\n", encoding="utf-8")
    link = tmp_path / "plan.json"
    _try_symlink(link, outside)
    with pytest.raises(OSError, match="symlink"):
        demo_mod.write_plan(plan, link)
    assert outside.read_text(encoding="utf-8") == "keep\n"


def test_recipe_is_on_the_allow_list_and_justfile(
    boundary_mod: ModuleType,
) -> None:
    assert "node-demo-deploy" in boundary_mod.ALLOWED_NODE_RECIPES
    assert boundary_mod.recipe_action_allowed("place") is False
    assert boundary_mod.deploy_may_import("qmn.host") is False
    just_text = (_DEPLOY / "justfile-recipes" / "node.just").read_text(encoding="utf-8")
    assert "node-demo-deploy" in just_text
    assert "demo.py" in just_text
    assert "Book routing PAPER" in just_text
    docs = (_DEPLOY / "justfile-recipes" / "README.txt").read_text(encoding="utf-8")
    assert "node-demo-deploy" in docs


def test_non_paper_fixture_and_failed_apply_are_refused(
    demo_mod: ModuleType, tmp_path: Path
) -> None:
    live_fixture = tmp_path / "live.json"
    live_fixture.write_text('{"book_routing": "LIVE"}\n', encoding="utf-8")
    live_plan = demo_mod.build_demo_shape_plan(
        mode="check",
        fixture=demo_mod.load_demo_shape_fixture(live_fixture),
    )
    assert live_plan.ok is False
    assert any("PAPER" in finding for finding in live_plan.findings)

    array_fixture = tmp_path / "array.json"
    array_fixture.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        demo_mod.load_demo_shape_fixture(array_fixture)

    procured = demo_mod.build_demo_shape_plan(mode="check", vps_procured=True)
    assert procured.ok is True
    assert procured.blocked_infra == ()

    failed = demo_mod.build_demo_shape_plan(mode="check", procure_vps=True)
    with pytest.raises(RuntimeError, match="failed plan"):
        demo_mod.apply_plan_to_fixture(failed, tmp_path / "scratch")


def test_main_writes_plan_and_refuses_forbidden_flags(demo_mod: ModuleType, tmp_path: Path) -> None:
    out = tmp_path / "plan.json"
    written = demo_mod.main(["--out", str(out), "--vps-procured"])
    assert written == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["book_routing"] == "PAPER"
    assert payload["ok"] is True
    assert payload["blocked_infra"] == []

    refused = demo_mod.main(["--procure-vps"])
    assert refused == 1


def test_demo_planner_never_imports_qmn(demo_mod: ModuleType) -> None:
    path = _DEPLOY / "demo.py"
    resolved = path.resolve()
    assert not path.is_symlink()
    assert resolved.is_relative_to(_WORKSPACE)
    assert resolved.stat().st_size <= _MAX_READ_BYTES
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("qmn.")
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            assert not node.module.startswith("qmn.")
    assert demo_mod.PROCURES_VPS is False
    assert demo_mod.OPENS_LIVE_CREDENTIALS is False
    assert demo_mod.FIRST_DEPLOYMENT_BOOK_ROUTING == "PAPER"
