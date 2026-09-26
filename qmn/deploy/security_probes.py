"""``just node-security-probes`` planner (Story 28.4 / QMX-F045/F064).

Plans powers/secret probes and inspects unit/network/upgrade posture from
checked-in templates. Check mode by default. Never applies a live VPS firewall,
never trades, never imports the composition root.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Final, Literal

__all__ = [
    "SECURITY_RECIPE",
    "SecurityProbePlan",
    "SecurityProbeStep",
    "apply_plan_to_fixture",
    "build_security_probe_plan",
    "main",
    "write_plan",
]

_DEPLOY_ROOT: Final[Path] = Path(__file__).resolve().parent

SECURITY_RECIPE: Final[str] = "node-security-probes"
SECURITY_PROBES: Final[tuple[str, ...]] = (
    "unknown-peer",
    "ops-principal-forbidden",
    "automated-operator-uid",
    "secret-leak-pattern",
    "stale-state-authorization",
    "sandbox-promotion",
)


def _load_sibling(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_boundary = _load_sibling("qmn_deploy_boundary", _DEPLOY_ROOT / "boundary.py")
_units = _load_sibling("qmn_deploy_units_28_4", _DEPLOY_ROOT / "systemd" / "units.py")
_network = _load_sibling("qmn_deploy_network_28_4", _DEPLOY_ROOT / "network.py")
_upgrade = _load_sibling("qmn_deploy_upgrade_28_4", _DEPLOY_ROOT / "upgrade.py")
_safe_io = _load_sibling("qmn_deploy_safe_io", _DEPLOY_ROOT / "safe_io.py")


@dataclass(frozen=True, slots=True)
class SecurityProbeStep:
    """One planned probe or fixture security assertion."""

    kind: str
    target: str
    detail: str
    check_mode_only: bool = True


@dataclass(frozen=True, slots=True)
class SecurityProbePlan:
    """Fixture security campaign — no live firewall, no trading controls."""

    recipe: str
    principal: str
    mode: Literal["check", "apply"]
    probes: tuple[str, ...]
    steps: tuple[SecurityProbeStep, ...]
    ok: bool
    findings: tuple[str, ...]
    notes: tuple[str, ...]
    qmx_identity: bool
    no_dynamic_user: bool
    inbound_default_deny: bool
    loopback_unix_only_doors: bool
    no_automatic_reboot: bool
    devops_unable_to_trade: bool
    runs_live_vps_firewall: bool = False

    def to_jsonable(self) -> dict[str, object]:
        return {
            "devops_unable_to_trade": self.devops_unable_to_trade,
            "findings": list(self.findings),
            "inbound_default_deny": self.inbound_default_deny,
            "loopback_unix_only_doors": self.loopback_unix_only_doors,
            "mode": self.mode,
            "no_automatic_reboot": self.no_automatic_reboot,
            "no_dynamic_user": self.no_dynamic_user,
            "notes": list(self.notes),
            "ok": self.ok,
            "principal": self.principal,
            "probes": list(self.probes),
            "qmx_identity": self.qmx_identity,
            "recipe": self.recipe,
            "runs_live_vps_firewall": self.runs_live_vps_firewall,
            "steps": [asdict(step) for step in self.steps],
        }


def build_security_probe_plan(
    *,
    mode: Literal["check", "apply"] = "check",
    run_live_vps_firewall: bool = False,
) -> SecurityProbePlan:
    """Inspect templates + network/upgrade contracts; refuse live firewall apply."""
    _assert_boundary()
    findings: list[str] = []
    if run_live_vps_firewall:
        findings.append("live VPS firewall campaign is skipped (soak-local)")

    values_path = _DEPLOY_ROOT / "fixtures" / "render-values.json"
    values_text = _safe_io.read_text_contained(
        values_path, contain_within=_DEPLOY_ROOT / "fixtures"
    )
    values = json.loads(values_text)
    rendered = _units.render_all_templates(
        drain_window=values["drain_window"],
        watchdog_interval=values["watchdog_interval"],
        deploy_root=_DEPLOY_ROOT / "systemd",
    )
    inspections = _units.inspect_rendered_units(rendered)
    unit_failures = [item for item in inspections if not item.ok]
    for item in unit_failures:
        findings.append(f"{item.name}: {list(item.findings)}")

    qmx_identity = True
    no_dynamic_user = True
    for name, text in rendered.items():
        if name.endswith(".timer"):
            continue
        lowered = text.lower()
        if "dynamicuser=yes" in lowered:
            no_dynamic_user = False
            findings.append(f"{name} declares DynamicUser=yes")
        if name == "qmx-observability.service":
            if "User=qmxobs" not in text:
                qmx_identity = False
                findings.append("observability unit must run as qmxobs")
        elif "User=qmx" not in text:
            qmx_identity = False
            findings.append(f"{name} must run as User=qmx")

    posture = _network.default_network_posture()
    network_findings = _network.validate_network_posture(posture)
    findings.extend(network_findings)
    inbound_default_deny = posture.inbound_default == "deny" and not posture.public_node_doors
    loopback_unix = posture.powers_transport == "unix-socket" and not posture.public_node_doors

    upgrade = _upgrade.default_upgrade_policy()
    upgrade_findings = _upgrade.inspect_upgrade_policy(
        upgrade,
        fragments={
            "apt": _upgrade.apt_unattended_fragment(),
            "needrestart": _upgrade.needrestart_fragment(),
        },
    )
    findings.extend(upgrade_findings)
    no_automatic_reboot = upgrade.automatic_reboot is False

    for action in _boundary.FORBIDDEN_RECIPE_ACTIONS:
        if _boundary.recipe_action_allowed(action):
            findings.append(f"forbidden action unexpectedly allowed: {action}")

    steps = [
        SecurityProbeStep(
            kind="probe",
            target=name,
            detail=f"refuse {name} at the powers/secret boundary and journal without secrets",
        )
        for name in SECURITY_PROBES
    ]
    steps.append(
        SecurityProbeStep(
            kind="inspect",
            target="systemd-units",
            detail="fixed qmx identity, no DynamicUser, hardening, host-sealed credentials",
        )
    )
    steps.append(
        SecurityProbeStep(
            kind="inspect",
            target="network-posture",
            detail="inbound default-deny except SSH; loopback/unix doors; egress allow-list",
        )
    )
    steps.append(
        SecurityProbeStep(
            kind="inspect",
            target="upgrade-policy",
            detail="no automatic reboot or node restart on upgrade",
        )
    )
    steps.append(
        SecurityProbeStep(
            kind="skip",
            target="live-vps-firewall",
            detail="real VPS firewall apply is not a Story 28.4 factory AC",
        )
    )
    notes = (
        "DevOps only — never a trading control",
        f"principal={_boundary.OPS_PRINCIPAL_NAME}",
        "fixture inspection only; never nftables/ufw apply on a live VPS",
        "powers/secret proofs run as qmn.host.security_probes tests",
    )
    return SecurityProbePlan(
        recipe=SECURITY_RECIPE,
        principal=_boundary.OPS_PRINCIPAL_NAME,
        mode=mode,
        probes=SECURITY_PROBES,
        steps=tuple(steps),
        ok=not findings,
        findings=tuple(findings),
        notes=notes,
        qmx_identity=qmx_identity,
        no_dynamic_user=no_dynamic_user,
        inbound_default_deny=inbound_default_deny,
        loopback_unix_only_doors=loopback_unix,
        no_automatic_reboot=no_automatic_reboot,
        devops_unable_to_trade=True,
        runs_live_vps_firewall=False,
    )


def apply_plan_to_fixture(plan: SecurityProbePlan, fixture_root: Path) -> Path:
    """Materialize the security-probe plan under a scratch tree (CI/tests)."""
    if not plan.ok:
        raise RuntimeError(f"refusing to apply failed plan: {plan.findings}")
    if plan.runs_live_vps_firewall:
        raise RuntimeError("plan must not run a live VPS firewall campaign")
    fixture_root.mkdir(parents=True, exist_ok=True)
    out = fixture_root / "security-probes.json"
    _safe_io.write_text_exclusive_no_follow(
        out,
        json.dumps(plan.to_jsonable(), indent=2, sort_keys=True) + "\n",
        contain_within=fixture_root,
    )
    return out


def write_plan(plan: SecurityProbePlan, destination: Path) -> None:
    """Write the plan JSON."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    _safe_io.write_text_exclusive_no_follow(
        destination,
        json.dumps(plan.to_jsonable(), indent=2, sort_keys=True) + "\n",
        contain_within=destination.parent,
    )


def _assert_boundary() -> None:
    allowed = _boundary.ALLOWED_NODE_RECIPES
    if SECURITY_RECIPE not in allowed:
        raise RuntimeError(f"{SECURITY_RECIPE} missing from ALLOWED_NODE_RECIPES")
    for action in _boundary.FORBIDDEN_RECIPE_ACTIONS:
        if _boundary.recipe_action_allowed(action):
            raise RuntimeError(f"forbidden action unexpectedly allowed: {action}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="node-security-probes",
        description=(
            "Plan Story 28.4 powers/secret probes and inspect unit/network posture. "
            "Never applies a live VPS firewall."
        ),
    )
    parser.add_argument("--check-mode", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--fixture-root", type=Path, default=None)
    parser.add_argument("--live-firewall", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.apply and args.fixture_root is None:
        print(
            "refusing --apply without --fixture-root: this recipe never SSHes to "
            "a VPS and never applies a live firewall",
            file=sys.stderr,
        )
        return 2
    if args.live_firewall:
        print(
            "refusing live VPS firewall campaign: Story 28.4 skips that AC",
            file=sys.stderr,
        )
        return 2

    mode: Literal["check", "apply"] = "apply" if args.fixture_root is not None else "check"
    plan = build_security_probe_plan(mode=mode, run_live_vps_firewall=False)
    if args.fixture_root is not None:
        apply_plan_to_fixture(plan, args.fixture_root)
    if args.out is not None:
        write_plan(plan, args.out)
    else:
        print(json.dumps(plan.to_jsonable(), indent=2, sort_keys=True))
    return 0 if plan.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
