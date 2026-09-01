"""Idempotent ``just node-install`` planner (TN-16 / FR-068 / AR-77).

Privileged host act on Ubuntu 24.04 — creates accounts, trees, renders unit
files, lays out the credstore, and records the network posture. Check mode
plans every step against a fixture tree without touching the live host, and
never SSHes to Contabo.

DevOps only: never imports ``qmn.host`` / ``qmn.doors``, never places, cancels,
amends, flattens, promotes, or activates (AR-79 / DEC-0202).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Final, Literal, cast

__all__ = [
    "INSTALL_RECIPE",
    "OPT_QMX",
    "PINNED_JUST_VERSION",
    "PINNED_PYTHON",
    "UV_SYNC_COMMAND",
    "VAR_LIB_QMX",
    "VAR_LIB_QMX_OBS",
    "InstallPlan",
    "InstallStep",
    "build_install_plan",
    "load_render_values",
    "main",
    "write_plan",
]

_DEPLOY_ROOT: Final[Path] = Path(__file__).resolve().parent

INSTALL_RECIPE: Final[str] = "node-install"
OPT_QMX: Final[str] = "/opt/qmx"
VAR_LIB_QMX: Final[str] = "/var/lib/qmx"
VAR_LIB_QMX_OBS: Final[str] = "/var/lib/qmx-observability"
PINNED_PYTHON: Final[str] = "3.14"
PINNED_JUST_VERSION: Final[str] = "1.58.0"
UV_SYNC_COMMAND: Final[str] = "uv sync --frozen"
CREDSTORE_ENCRYPTED: Final[str] = "/etc/credstore.encrypted"


def _load_sibling(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    # Register before exec so @dataclass(slots=True) can resolve annotations.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_boundary = _load_sibling("qmn_deploy_boundary", _DEPLOY_ROOT / "boundary.py")
_network = _load_sibling("qmn_deploy_network", _DEPLOY_ROOT / "network.py")
_units = _load_sibling("qmn_deploy_units", _DEPLOY_ROOT / "systemd" / "units.py")
_obs = _load_sibling(
    "qmn_deploy_obs_stack", _DEPLOY_ROOT / "observability" / "stack.py"
)
_safe_io = _load_sibling("qmn_deploy_safe_io", _DEPLOY_ROOT / "safe_io.py")


@dataclass(frozen=True, slots=True)
class InstallStep:
    """One planned install action."""

    kind: str
    target: str
    detail: str
    check_mode_only: bool = False


@dataclass(frozen=True, slots=True)
class InstallPlan:
    """Full install plan produced in check mode or for a live run."""

    recipe: str
    principal: str
    mode: Literal["check", "apply"]
    steps: tuple[InstallStep, ...]
    rendered_units: Mapping[str, str]
    unit_findings: tuple[str, ...]
    network: object
    network_findings: tuple[str, ...]
    ok: bool
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_jsonable(self) -> dict[str, object]:
        network = self.network
        to_jsonable = getattr(network, "to_jsonable", None)
        network_payload: object = (
            to_jsonable() if callable(to_jsonable) else repr(network)
        )
        return {
            "recipe": self.recipe,
            "principal": self.principal,
            "mode": self.mode,
            "ok": self.ok,
            "steps": [asdict(step) for step in self.steps],
            "rendered_unit_names": sorted(self.rendered_units),
            "unit_findings": list(self.unit_findings),
            "network": network_payload,
            "network_findings": list(self.network_findings),
            "notes": list(self.notes),
        }


def load_render_values(path: Path | None) -> dict[str, object]:
    """Load drain_window / watchdog_interval (+ optional extras) from JSON."""
    if path is None:
        # Evidence defaults recorded in the registry notes (not ratified constants).
        return {"drain_window": "30s", "watchdog_interval": "15s"}
    text = _safe_io.read_text_contained(path, contain_within=path.parent)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("render values must be a JSON object")
    return cast("dict[str, object]", data)


def build_install_plan(
    *,
    mode: Literal["check", "apply"] = "check",
    render_values: Mapping[str, object] | None = None,
    deploy_root: Path | None = None,
    network: object | None = None,
) -> InstallPlan:
    """Plan the Ubuntu install. Check mode never mutates the host."""
    allowed = _boundary.ALLOWED_NODE_RECIPES
    if INSTALL_RECIPE not in allowed:
        raise RuntimeError(f"{INSTALL_RECIPE} missing from ALLOWED_NODE_RECIPES")
    for action in _boundary.FORBIDDEN_RECIPE_ACTIONS:
        if _boundary.recipe_action_allowed(action):
            raise RuntimeError(f"forbidden action unexpectedly allowed: {action}")

    values = dict(render_values or load_render_values(None))
    drain = values.get("drain_window")
    watchdog = values.get("watchdog_interval")
    root = deploy_root or _DEPLOY_ROOT

    rendered = _units.render_all_templates(
        drain_window=drain,
        watchdog_interval=watchdog,
        deploy_root=root / "systemd",
    )
    inspections = _units.inspect_rendered_units(rendered)
    unit_findings = tuple(
        f"{item.name}: {finding}"
        for item in inspections
        for finding in item.findings
    )

    posture = network if network is not None else _network.default_network_posture()
    network_findings = _network.validate_network_posture(posture)

    steps: list[InstallStep] = []
    check_only = mode == "check"

    steps.append(
        InstallStep(
            kind="bootstrap",
            target="uv",
            detail=f"ensure pinned uv + CPython {PINNED_PYTHON}",
            check_mode_only=check_only,
        )
    )
    steps.append(
        InstallStep(
            kind="bootstrap",
            target="just",
            detail=f"ensure just=={PINNED_JUST_VERSION}",
            check_mode_only=check_only,
        )
    )
    steps.append(
        InstallStep(
            kind="bootstrap",
            target="chrony",
            detail="install or verify chrony (Ubuntu 24.04)",
            check_mode_only=check_only,
        )
    )
    steps.append(
        InstallStep(
            kind="account",
            target=_units.NODE_SERVICE_ACCOUNT,
            detail="fixed service account for all five node units",
            check_mode_only=check_only,
        )
    )
    steps.append(
        InstallStep(
            kind="account",
            target=_units.OBSERVABILITY_SERVICE_ACCOUNT,
            detail="distinct non-qmx account for observability stack",
            check_mode_only=check_only,
        )
    )
    steps.append(
        InstallStep(
            kind="account",
            target="qmxops",
            detail="ops-principal group for powers socket ownership qmx:qmxops",
            check_mode_only=check_only,
        )
    )
    steps.append(
        InstallStep(
            kind="tree",
            target=OPT_QMX,
            detail="immutable per-commit trees + current symlink root",
            check_mode_only=check_only,
        )
    )
    for name in _units.WRITABLE_TREE_NAMES:
        steps.append(
            InstallStep(
                kind="tree",
                target=f"{VAR_LIB_QMX}/{name}",
                detail=f"writable tree owned by {_units.NODE_SERVICE_ACCOUNT}",
                check_mode_only=check_only,
            )
        )
    steps.append(
        InstallStep(
            kind="tree",
            target=VAR_LIB_QMX_OBS,
            detail=(
                "observability storage owned by "
                f"{_units.OBSERVABILITY_SERVICE_ACCOUNT}"
            ),
            check_mode_only=check_only,
        )
    )
    steps.append(
        InstallStep(
            kind="socket",
            target=_units.POWERS_SOCKET_PATH,
            detail="RuntimeDirectory=qmn creates /run/qmn for powers.sock",
            check_mode_only=check_only,
        )
    )
    steps.append(
        InstallStep(
            kind="sync",
            target=f"{OPT_QMX}/current",
            detail=UV_SYNC_COMMAND,
            check_mode_only=check_only,
        )
    )
    steps.append(
        InstallStep(
            kind="credstore",
            target=CREDSTORE_ENCRYPTED,
            detail=(
                "layout for LoadCredentialEncrypted; seal with "
                f"systemd-creds encrypt {_units.CREDENTIAL_SEAL_FLAG} "
                f"(forbidden: {_units.FORBIDDEN_SEAL_FLAG})"
            ),
            check_mode_only=check_only,
        )
    )
    for role in _units.NODE_UNIT_ROLES:
        steps.append(
            InstallStep(
                kind="unit",
                target=role,
                detail="render and install governed unit from templates/",
                check_mode_only=check_only,
            )
        )
    steps.append(
        InstallStep(
            kind="unit",
            target=_units.OBSERVABILITY_UNIT,
            detail="separate sixth unit — not a node unit",
            check_mode_only=check_only,
        )
    )
    steps.append(
        InstallStep(
            kind="network",
            target="ufw+egress",
            detail=(
                "inbound default-deny + SSH for "
                + ",".join(_network.INBOUND_SSH_IDENTITIES)
                + "; egress "
                + ",".join(sorted(_network.EGRESS_ALLOW_CLASSES))
            ),
            check_mode_only=check_only,
        )
    )
    steps.append(
        InstallStep(
            kind="journald",
            target="SystemMaxUse",
            detail=(
                "journald limits + read-only LogNamespace="
                f"{_obs.JOURNAL_NAMESPACE} for qmxobs"
            ),
            check_mode_only=check_only,
        )
    )
    runtime = _obs.CONTAINER_RUNTIME_PIN
    steps.append(
        InstallStep(
            kind="bootstrap",
            target="container-runtime",
            detail=(
                f"pin {runtime['engine']}=={runtime['engine_version']} "
                f"+ compose plugin=={runtime['compose_plugin_version']} "
                "(observability stack only)"
            ),
            check_mode_only=check_only,
        )
    )
    steps.append(
        InstallStep(
            kind="compose",
            target=str((root / "observability" / _obs.COMPOSE_FILE_NAME).as_posix()),
            detail=(
                "checked-in observability compose with pinned images; "
                "loopback listeners; zero node authority"
            ),
            check_mode_only=check_only,
        )
    )
    steps.append(
        InstallStep(
            kind="quota",
            target=VAR_LIB_QMX_OBS,
            detail=(
                "filesystem quota on observability storage for "
                f"{_units.OBSERVABILITY_SERVICE_ACCOUNT}"
            ),
            check_mode_only=check_only,
        )
    )

    obs_inspection = _obs.inspect_stack_tree(root / "observability")
    obs_findings = obs_inspection.findings

    notes = (
        "DevOps only — never a trading control",
        f"principal={_boundary.OPS_PRINCIPAL_NAME}",
        "check mode plans only; apply requires ops-principal sudo on the VPS",
        "do not SSH to Contabo from CI or developer workstations for this story",
        "observability stack is optional to node operation (DEC-0212)",
    )

    ok = not unit_findings and not network_findings and not obs_findings
    rendered_names = frozenset(rendered)
    expected_node = {
        "qmn.service",
        "qmn-news-calendar.service",
        "qmn-news-calendar.timer",
        "qmn-backup.service",
        "qmn-backup.timer",
        "qmn-restore-sample.service",
        "qmn-restore-sample.timer",
        "qmn-restore-full.service",
        "qmn-restore-full.timer",
    }
    missing = set(expected_node - rendered_names)
    if _units.OBSERVABILITY_UNIT not in rendered_names:
        missing.add(_units.OBSERVABILITY_UNIT)
    if missing:
        ok = False
        unit_findings = unit_findings + tuple(
            f"missing template render: {m}" for m in sorted(missing)
        )
    if obs_findings:
        unit_findings = unit_findings + tuple(
            f"observability: {finding}" for finding in obs_findings
        )

    return InstallPlan(
        recipe=INSTALL_RECIPE,
        principal=_boundary.OPS_PRINCIPAL_NAME,
        mode=mode,
        steps=tuple(steps),
        rendered_units=rendered,
        unit_findings=unit_findings,
        network=posture,
        network_findings=network_findings,
        ok=ok,
        notes=notes,
    )


def write_plan(plan: InstallPlan, destination: Path) -> None:
    """Write the plan JSON and rendered units beside it."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    _safe_io.write_text_exclusive_no_follow(
        destination,
        json.dumps(plan.to_jsonable(), indent=2, sort_keys=True) + "\n",
        contain_within=destination.parent,
    )
    units_dir = destination.parent / "rendered-units"
    units_dir.mkdir(parents=True, exist_ok=True)
    for name, text in plan.rendered_units.items():
        _safe_io.write_text_exclusive_no_follow(
            units_dir / name,
            text,
            contain_within=units_dir,
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="node-install",
        description=(
            "Plan or apply the Ubuntu node install (DevOps only). "
            "Default is check mode."
        ),
    )
    parser.add_argument(
        "--check-mode",
        action="store_true",
        default=True,
        help="plan only; never mutate the host (default)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="apply on the VPS (requires ops-principal sudo; not for CI)",
    )
    parser.add_argument(
        "--values",
        type=Path,
        default=None,
        help="JSON file with drain_window and watchdog_interval",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write plan JSON to this path",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.apply:
        # Live apply is a VPS-only privileged path. This story proves the plan
        # via check mode/fixtures and never SSHes to Contabo.
        print(
            "refusing --apply in this process: run on the VPS under the ops "
            "principal sudo path; CI and workstations use --check-mode only",
            file=sys.stderr,
        )
        return 2

    values = load_render_values(args.values)
    plan = build_install_plan(mode="check", render_values=values)
    payload = json.dumps(plan.to_jsonable(), indent=2, sort_keys=True)
    if args.out is not None:
        write_plan(plan, args.out)
    else:
        print(payload)
    return 0 if plan.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
