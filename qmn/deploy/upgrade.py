"""Routine upgrade posture for the Trading VPS (NFR-18 / TN-16 / DEC-0201).

Package, runtime, OS, and application updates may stage and verify artifacts
but MUST NEVER reboot the VPS or restart/switch the node automatically. Only an
explicit ops-principal ``just node-switch`` at a node safe point changes the
running release.

DevOps surface only — never imports ``qmn.host`` / ``qmn.doors``.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Final

__all__ = [
    "APT_UNATTENDED_FRAGMENT_NAME",
    "FORBIDDEN_AUTO_ACTIONS",
    "NEEDRESTART_FRAGMENT_NAME",
    "NEVER_RESTART_UNITS",
    "UPGRADE_INVARIANTS",
    "UpgradePolicy",
    "apt_unattended_fragment",
    "default_upgrade_policy",
    "inspect_upgrade_policy",
    "needrestart_fragment",
]

_DEPLOY_ROOT: Final[Path] = Path(__file__).resolve().parent


def _load_sibling(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_safe_io = _load_sibling("qmn_deploy_safe_io", _DEPLOY_ROOT / "safe_io.py")

APT_UNATTENDED_FRAGMENT_NAME: Final[str] = "52qmx-no-auto-reboot"
NEEDRESTART_FRAGMENT_NAME: Final[str] = "qmx-never-restart.conf"
NEVER_RESTART_UNITS: Final[tuple[str, ...]] = (
    "qmn.service",
    "qmn-news-calendar.service",
    "qmn-backup.service",
    "qmn-restore-sample.service",
    "qmn-restore-full.service",
)

FORBIDDEN_AUTO_ACTIONS: Final[frozenset[str]] = frozenset(
    {
        "auto-reboot",
        "auto-restart-qmn",
        "auto-node-switch",
        "auto-node-rollback",
    }
)

UPGRADE_INVARIANTS: Final[tuple[str, ...]] = (
    "stage_and_verify_only",
    "no_automatic_reboot",
    "never_restart_qmn_service",
    "release_change_only_via_explicit_node_switch",
    "ops_principal_required_for_switch",
)


@dataclass(frozen=True, slots=True)
class UpgradePolicy:
    """Declared unattended-upgrade / needrestart posture."""

    automatic_reboot: bool
    allow_auto_node_switch: bool
    allow_auto_restart_units: tuple[str, ...]
    never_restart_units: tuple[str, ...]
    may_stage_and_verify: bool
    release_change_recipe: str

    def to_jsonable(self) -> dict[str, object]:
        return {
            "automatic_reboot": self.automatic_reboot,
            "allow_auto_node_switch": self.allow_auto_node_switch,
            "allow_auto_restart_units": list(self.allow_auto_restart_units),
            "never_restart_units": list(self.never_restart_units),
            "may_stage_and_verify": self.may_stage_and_verify,
            "release_change_recipe": self.release_change_recipe,
            "forbidden_auto_actions": sorted(FORBIDDEN_AUTO_ACTIONS),
            "invariants": list(UPGRADE_INVARIANTS),
        }


def default_upgrade_policy() -> UpgradePolicy:
    return UpgradePolicy(
        automatic_reboot=False,
        allow_auto_node_switch=False,
        allow_auto_restart_units=(),
        never_restart_units=NEVER_RESTART_UNITS,
        may_stage_and_verify=True,
        release_change_recipe="node-switch",
    )


def apt_unattended_fragment() -> str:
    """``/etc/apt/apt.conf.d/52qmx-no-auto-reboot`` body."""
    return (
        '// QMX Trading VPS — unattended upgrades stage/verify only (NFR-18).\n'
        '// Never reboot; never restart qmn.service. Release changes require\n'
        '// an explicit ops-principal `just node-switch` at a safe point.\n'
        'Unattended-Upgrade::Automatic-Reboot "false";\n'
        'Unattended-Upgrade::Automatic-Reboot-WithUsers "false";\n'
        'Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";\n'
    )


def needrestart_fragment() -> str:
    """``/etc/needrestart/conf.d/qmx-never-restart.conf`` body."""
    lines = [
        "# QMX Trading VPS — needrestart must never restart node units (NFR-18).",
        "# Package upgrades may stage; only `just node-switch` flips the release.",
        "$nrconf{override_rc} = {",
    ]
    for unit in NEVER_RESTART_UNITS:
        lines.append(f'  qr(^{unit}$) => 0,')
    lines.append("};")
    lines.append("")
    return "\n".join(lines) + "\n"


def inspect_upgrade_policy(
    policy: UpgradePolicy | None = None,
    *,
    fragments: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Return findings if the upgrade posture would auto-reboot or auto-switch."""
    posture = policy or default_upgrade_policy()
    findings: list[str] = []
    if posture.automatic_reboot:
        findings.append("automatic_reboot must be false")
    if posture.allow_auto_node_switch:
        findings.append("allow_auto_node_switch must be false")
    if not posture.may_stage_and_verify:
        findings.append("routine upgrades must be allowed to stage and verify")
    if posture.release_change_recipe != "node-switch":
        findings.append("release_change_recipe must be node-switch")
    for unit in NEVER_RESTART_UNITS:
        if unit not in posture.never_restart_units:
            findings.append(f"missing never-restart unit: {unit}")
    for unit in posture.allow_auto_restart_units:
        if unit in NEVER_RESTART_UNITS or unit.startswith("qmn"):
            findings.append(f"auto-restart of {unit} is forbidden")

    texts = dict(fragments or {})
    if "apt" in texts:
        apt = texts["apt"]
        if 'Automatic-Reboot "false"' not in apt and "Automatic-Reboot \"false\"" not in apt:
            findings.append("apt fragment must disable Automatic-Reboot")
        if "true" in apt.lower() and "automatic-reboot \"true\"" in apt.lower():
            findings.append("apt fragment enables Automatic-Reboot")
    if "needrestart" in texts:
        nr = texts["needrestart"]
        for unit in NEVER_RESTART_UNITS:
            if unit not in nr:
                findings.append(f"needrestart fragment missing {unit}")
            if f"{unit}" in nr and "=> 0" not in nr:
                findings.append(f"needrestart must override {unit} to 0 (never restart)")
    return tuple(findings)


def write_fragments(destination: Path) -> None:
    """Write apt + needrestart fragments under a fixture/CI directory."""
    destination.mkdir(parents=True, exist_ok=True)
    _safe_io.write_text_exclusive_no_follow(
        destination / APT_UNATTENDED_FRAGMENT_NAME,
        apt_unattended_fragment(),
        contain_within=destination,
    )
    _safe_io.write_text_exclusive_no_follow(
        destination / NEEDRESTART_FRAGMENT_NAME,
        needrestart_fragment(),
        contain_within=destination,
    )
