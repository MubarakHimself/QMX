"""Story 25.17 — separate zero-authority observability stack (FR-067 / AR-83).

Compose + dashboard seeds under ``qmn/deploy/observability/``. Never deploys
to a live VPS; never imports trading controls. The node must remain acceptable
with this entire stack absent.
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
_OBS = _DEPLOY / "observability"
_SRC = _QMN_ROOT / "src" / "qmn"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def stack_mod() -> ModuleType:
    return _load("qmn_deploy_obs_stack_test", _OBS / "stack.py")


@pytest.fixture(scope="module")
def install_mod() -> ModuleType:
    return _load("qmn_deploy_install_obs_test", _DEPLOY / "install.py")


@pytest.fixture(scope="module")
def units_mod() -> ModuleType:
    return _load("qmn_deploy_units_obs_test", _DEPLOY / "systemd" / "units.py")


def test_required_stack_tree_present(stack_mod: ModuleType) -> None:
    inspection = stack_mod.inspect_stack_tree(_OBS)
    assert inspection.missing_files == (), inspection.missing_files
    assert inspection.ok, inspection.findings


def test_pinned_images_never_float(stack_mod: ModuleType) -> None:
    refs = stack_mod.PINNED_IMAGE_REFS
    assert len(refs) == 4
    for ref in refs:
        assert ":latest" not in ref
        assert ref.count(":") == 1
        _repo, tag = ref.split(":", 1)
        assert tag
        assert "latest" not in tag
        assert tag[0].isdigit() or tag.startswith("v")
    compose = (_OBS / "compose.yml").read_text(encoding="utf-8")
    for ref in refs:
        assert ref in compose
    findings = stack_mod.inspect_compose_text(compose)
    assert findings == (), findings


def test_loopback_binds_and_host_network(stack_mod: ModuleType) -> None:
    compose = (_OBS / "compose.yml").read_text(encoding="utf-8")
    assert "network_mode: host" in compose
    assert "127.0.0.1:9090" in compose
    assert "127.0.0.1:3000" in compose or 'GF_SERVER_HTTP_ADDR: 127.0.0.1' in compose
    assert "0.0.0.0:" not in compose
    loki = (_OBS / "loki" / "loki.yml").read_text(encoding="utf-8")
    assert "http_listen_address: 127.0.0.1" in loki
    assert "http_listen_port: 3100" in loki
    assert stack_mod.EVIDENCE_METRICS_SCRAPE == "127.0.0.1:8787"
    prom = (_OBS / "prometheus" / "prometheus.yml").read_text(encoding="utf-8")
    assert stack_mod.EVIDENCE_METRICS_SCRAPE in prom
    assert "metrics_path: /metrics" in prom


def test_dashboard_and_alert_seeds_exist(stack_mod: ModuleType) -> None:
    for name in stack_mod.DASHBOARD_SEED_NAMES:
        path = _OBS / "grafana" / "dashboards" / name
        assert path.is_file(), name
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["title"]
        assert "qmn" in payload.get("tags", []) or "qmn" in payload["title"].lower()
    alerts = (_OBS / "prometheus" / "alerts.yml").read_text(encoding="utf-8")
    assert "QmnMetricsTargetDown" in alerts
    assert "authority: none" in alerts


def test_read_only_journal_namespace_and_quota(stack_mod: ModuleType) -> None:
    assert stack_mod.JOURNAL_NAMESPACE == "qmn"
    promtail = (_OBS / "promtail" / "promtail.yml").read_text(encoding="utf-8")
    assert "namespace: qmn" in promtail
    assert "_SYSTEMD_UNIT=qmn.service" in promtail
    quota = (_OBS / "quota.txt").read_text(encoding="utf-8")
    assert stack_mod.OBSERVABILITY_STORAGE in quota
    assert "qmxobs" in quota


def test_compose_has_no_node_authority_mounts(stack_mod: ModuleType) -> None:
    compose = (_OBS / "compose.yml").read_text(encoding="utf-8")
    for forbidden in (
        "/var/lib/qmx/rooms",
        "/var/lib/qmx/state",
        "/var/lib/qmx/evidence",
        "/run/qmn",
        "qmn.host",
        "powers.sock",
    ):
        assert forbidden not in compose
    assert "/var/lib/qmx-observability" in compose
    assert "grafana-admin" in compose


def test_only_observability_dir_mentions_container_images() -> None:
    """Containers are permitted under deploy/observability/ only."""
    banned_roots = (
        _DEPLOY / "systemd",
        _DEPLOY / "justfile-recipes",
        _SRC,
    )
    image_tokens = (
        "prom/prometheus:",
        "grafana/grafana:",
        "grafana/loki:",
        "grafana/promtail:",
    )
    violations: list[str] = []
    for root in banned_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix in {".pyc", ".png"} or path.name == "README.txt":
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for token in image_tokens:
                if token in text:
                    violations.append(f"{path.relative_to(_QMN_ROOT)}: {token}")
    assert violations == [], violations


def test_observability_unit_distinct_account(units_mod: ModuleType) -> None:
    rendered = units_mod.render_all_templates(
        drain_window="30s",
        watchdog_interval="15s",
        deploy_root=_DEPLOY / "systemd",
    )
    obs = rendered["qmx-observability.service"]
    assert "User=qmxobs" in obs
    assert "compose.yml" in obs
    assert "LoadCredentialEncrypted=grafana-admin" in obs
    assert "venue-client" not in obs
    qmn = rendered["qmn.service"]
    assert "LogNamespace=qmn" in qmn
    assert "User=qmx" in qmn
    assert "User=qmxobs" not in qmn


def test_node_install_plans_compose_and_quota(install_mod: ModuleType) -> None:
    plan = install_mod.build_install_plan(
        mode="check",
        render_values={"drain_window": "30s", "watchdog_interval": "15s"},
        deploy_root=_DEPLOY,
    )
    assert plan.ok, (plan.unit_findings, plan.network_findings)
    kinds = {s.kind for s in plan.steps}
    assert "compose" in kinds
    assert "quota" in kinds
    assert any(s.target == "container-runtime" for s in plan.steps)
    assert any("observability" in s.detail for s in plan.steps if s.kind == "compose")
    assert all(s.check_mode_only for s in plan.steps)


def test_stack_py_never_imports_qmn_runtime() -> None:
    source = (_OBS / "stack.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("qmn"), alias.name
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("qmn"), node.module


def test_zero_authority_invariants_documented(stack_mod: ModuleType) -> None:
    invariants = set(stack_mod.ZERO_AUTHORITY_INVARIANTS)
    assert "no_public_inbound" in invariants
    assert "node_runs_without_stack" in invariants
    assert "read_only_journal_namespace" in invariants
    assert stack_mod.OBSERVABILITY_SERVICE_ACCOUNT == "qmxobs"
    assert stack_mod.OBSERVABILITY_UNIT == "qmx-observability.service"
