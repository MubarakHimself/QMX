"""Story 28.4 — powers and secret probes; DevOps recipes cannot trade."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from collections.abc import Mapping
from typing import TypeVar, cast

from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmn.host import (
    DEVOPS_FORBIDDEN_ACTIONS,
    SECURITY_PROBE_NAMES,
    SECURITY_PROBES_CLASS,
    SECURITY_PROBES_SURFACE,
    SecurityProbeInputs,
    devops_recipe_may_trade,
    refuse_live_vps_firewall_probe,
    run_paper_milestone_security_probes,
)
from qmn.observability.failures_gate import DESIGNED_TYPED_FAILURE_IDS

T = TypeVar("T")

_DEPLOY = Path(__file__).resolve().parents[1] / "deploy"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _load_boundary():
    path = _DEPLOY / "boundary.py"
    spec = importlib.util.spec_from_file_location("qmn_deploy_boundary_28_4", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_surface_markers_and_probe_names() -> None:
    assert SECURITY_PROBES_SURFACE == "qmn.host.security_probes"
    assert SECURITY_PROBES_CLASS == "paper-milestone-security-probes"
    assert SECURITY_PROBE_NAMES == (
        "unknown-peer",
        "ops-principal-forbidden",
        "automated-operator-uid",
        "secret-leak-pattern",
        "stale-state-authorization",
        "sandbox-promotion",
    )


def test_probes_refuse_and_journal_without_secret() -> None:
    report = _ok(run_paper_milestone_security_probes(SecurityProbeInputs()))
    assert report.each_refused is True
    assert report.journaled_without_secret is True
    assert report.devops_unable_to_trade is True
    assert report.runs_live_vps_firewall is False
    assert tuple(report.probes) == SECURITY_PROBE_NAMES
    for name in SECURITY_PROBE_NAMES:
        section = report.sections[name]
        assert isinstance(section, Mapping)
        mapped_section = cast("Mapping[str, object]", section)
        assert mapped_section["refused"] is True
        assert mapped_section["journaled"] is True
    mapped = report.as_mapping()
    assert "fixture-secret-zzzzzzzz" not in str(mapped)
    assert mapped["fingerprint"] == report.fingerprint.value


def test_identical_inputs_fingerprint_identically() -> None:
    first = _ok(run_paper_milestone_security_probes(SecurityProbeInputs()))
    second = _ok(run_paper_milestone_security_probes(SecurityProbeInputs()))
    assert first.fingerprint == second.fingerprint


def test_devops_recipes_remain_unable_to_trade() -> None:
    boundary = _load_boundary()
    assert DEVOPS_FORBIDDEN_ACTIONS == boundary.FORBIDDEN_RECIPE_ACTIONS
    for action in sorted(DEVOPS_FORBIDDEN_ACTIONS):
        assert devops_recipe_may_trade(action) is False
        assert boundary.recipe_action_allowed(action) is False
    refused = _refusal(
        run_paper_milestone_security_probes(SecurityProbeInputs(claim_devops_can_trade=True))
    )
    assert refused.context["failure_id"] == "security_probes.devops_trade"


def test_refuses_live_vps_firewall_probe() -> None:
    refused = _refusal(
        run_paper_milestone_security_probes(SecurityProbeInputs(run_live_vps_firewall=True))
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["failure_id"] == "security_probes.live_vps_firewall"
    assert refuse_live_vps_firewall_probe().context["failure_id"] == (
        "security_probes.live_vps_firewall"
    )


def test_designed_failure_ids_are_registered() -> None:
    for failure_id in (
        "security_probes.devops_trade",
        "security_probes.incomplete_probe",
        "security_probes.inputs",
        "security_probes.live_vps_firewall",
        "security_probes.secret_exposed",
    ):
        assert failure_id in DESIGNED_TYPED_FAILURE_IDS
