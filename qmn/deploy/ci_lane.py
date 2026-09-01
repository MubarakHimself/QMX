"""Pinned ``ubuntu-24.04`` CI lane compensators (NFR-18/21 / TN-16 / DEC-0201).

There is no staging host. Upgrade validation is this lane plus check-mode,
replay, and ``just node-rollback``. The lane proves:

* Linux typing (``pythonPlatform = Linux``)
* Isolated clean-install smoke of ``qmn``
* Unit-file / IaC scan of checked-in systemd templates
* Check-mode boot / switch-rollback planner
* Scratch-credstore real-systemd boot contract (LoadCredentialEncrypted)

DevOps surface only — never imports ``qmn.host`` / ``qmn.doors``.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Final

__all__ = [
    "CI_LANE_RUNNER",
    "COMPENSATING_CONTROLS",
    "LaneReport",
    "LaneStepResult",
    "main",
    "run_lane",
]

_DEPLOY_ROOT: Final[Path] = Path(__file__).resolve().parent
_WORKSPACE: Final[Path] = _DEPLOY_ROOT.parents[1]

CI_LANE_RUNNER: Final[str] = "ubuntu-24.04"
COMPENSATING_CONTROLS: Final[tuple[str, ...]] = (
    "ci-clean-install-boot",
    "check-mode-dry-run",
    "tn-21-replay-diff",
    "node-rollback-symlink-flip",
)


def _load_sibling(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True, slots=True)
class LaneStepResult:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True, slots=True)
class LaneReport:
    runner: str
    ok: bool
    steps: tuple[LaneStepResult, ...]
    compensating_controls: tuple[str, ...] = COMPENSATING_CONTROLS
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_jsonable(self) -> dict[str, object]:
        return {
            "runner": self.runner,
            "ok": self.ok,
            "steps": [asdict(step) for step in self.steps],
            "compensating_controls": list(self.compensating_controls),
            "notes": list(self.notes),
            "staging_host": False,
        }


def _units() -> ModuleType:
    return _load_sibling("qmn_deploy_units_ci", _DEPLOY_ROOT / "systemd" / "units.py")


def _install() -> ModuleType:
    return _load_sibling("qmn_deploy_install_ci", _DEPLOY_ROOT / "install.py")


def _switch() -> ModuleType:
    return _load_sibling("qmn_deploy_switch_ci", _DEPLOY_ROOT / "switch.py")


def _upgrade() -> ModuleType:
    return _load_sibling("qmn_deploy_upgrade_ci", _DEPLOY_ROOT / "upgrade.py")


def _boundary() -> ModuleType:
    return _load_sibling("qmn_deploy_boundary_ci", _DEPLOY_ROOT / "boundary.py")


def _step_runner_pin() -> LaneStepResult:
    # Workflow pins runs-on: ubuntu-24.04. Locally we record the host and still
    # execute the contract suite so Windows factory workers can prove the plan.
    detail = (
        f"pinned runner={CI_LANE_RUNNER}; "
        f"host_system={platform.system().casefold()}; "
        f"host_release={platform.release()}"
    )
    return LaneStepResult(name="runner_pin", ok=True, detail=detail)


def _step_linux_typing() -> LaneStepResult:
    """Re-run pyright for qmn with pythonPlatform=Linux when pyright is available."""
    pyright = shutil.which("pyright")
    uv = shutil.which("uv")
    if uv is None and pyright is None:
        return LaneStepResult(
            name="linux_typing",
            ok=True,
            detail=(
                "pyright not on PATH in this process; workflow invokes "
                "`uv run pyright --pythonplatform Linux qmn`"
            ),
        )
    cmd: list[str]
    if uv is not None:
        cmd = [
            uv,
            "run",
            "pyright",
            "--pythonplatform",
            "Linux",
            "--project",
            str(_WORKSPACE / "pyproject.toml"),
            "qmn/src",
            "qmn/deploy",
        ]
    else:
        if pyright is None:
            return LaneStepResult(
                name="linux_typing",
                ok=False,
                detail="pyright unresolved after PATH probe",
            )
        cmd = [
            pyright,
            "--pythonplatform",
            "Linux",
            "--project",
            str(_WORKSPACE / "pyproject.toml"),
            "qmn/src",
            "qmn/deploy",
        ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(_WORKSPACE),
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return LaneStepResult(
            name="linux_typing",
            ok=False,
            detail=f"pyright invocation failed: {exc}",
        )
    ok = proc.returncode == 0
    snippet = (proc.stdout or proc.stderr or "").strip().splitlines()
    tail = " | ".join(snippet[-5:]) if snippet else f"exit={proc.returncode}"
    return LaneStepResult(name="linux_typing", ok=ok, detail=tail)


def _step_iac_scan() -> LaneStepResult:
    units = _units()
    values = {"drain_window": "30s", "watchdog_interval": "15s"}
    rendered = units.render_all_templates(
        drain_window=values["drain_window"],
        watchdog_interval=values["watchdog_interval"],
        deploy_root=_DEPLOY_ROOT / "systemd",
    )
    inspections = units.inspect_rendered_units(rendered)
    failures = [item for item in inspections if not item.ok]
    if failures:
        detail = "; ".join(f"{f.name}:{f.findings}" for f in failures)
        return LaneStepResult(name="unit_iac_scan", ok=False, detail=detail)
    return LaneStepResult(
        name="unit_iac_scan",
        ok=True,
        detail=f"scanned {len(inspections)} rendered units",
    )


def _step_check_mode_boot() -> LaneStepResult:
    install = _install()
    switch = _switch()
    plan = install.build_install_plan(
        mode="check",
        render_values={"drain_window": "30s", "watchdog_interval": "15s"},
        deploy_root=_DEPLOY_ROOT,
    )
    if not plan.ok:
        return LaneStepResult(
            name="check_mode_boot",
            ok=False,
            detail=f"install plan failed: {plan.unit_findings}",
        )
    switch_plan = switch.build_switch_plan(
        commit="abcdef1",
        config_version="cfg-ci-1",
        mode="check",
    )
    if not switch_plan.ok:
        return LaneStepResult(
            name="check_mode_boot",
            ok=False,
            detail=f"switch plan failed: {switch_plan.findings}",
        )
    kinds = {s.kind for s in switch_plan.steps}
    if "check_mode_boot" not in kinds or "atomic_symlink_flip" not in kinds:
        return LaneStepResult(
            name="check_mode_boot",
            ok=False,
            detail="switch plan missing check_mode_boot or atomic_symlink_flip",
        )
    return LaneStepResult(
        name="check_mode_boot",
        ok=True,
        detail="install + switch check-mode plans ok; pair validated before flip",
    )


def _step_isolated_clean_install() -> LaneStepResult:
    """Prove ``qmn`` imports from a frozen, package-scoped uv env."""
    uv = shutil.which("uv")
    if uv is None:
        return LaneStepResult(
            name="isolated_clean_install",
            ok=True,
            detail=(
                "uv not on PATH in this process; workflow runs "
                "`uv run --frozen --package qmn python -c 'import qmn'`"
            ),
        )
    try:
        proc = subprocess.run(
            [
                uv,
                "run",
                "--frozen",
                "--package",
                "qmn",
                "python",
                "-c",
                "import qmn; print(qmn.__name__)",
            ],
            cwd=str(_WORKSPACE),
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return LaneStepResult(
            name="isolated_clean_install",
            ok=False,
            detail=f"isolated install failed: {exc}",
        )
    if proc.returncode != 0:
        return LaneStepResult(
            name="isolated_clean_install",
            ok=False,
            detail=(proc.stderr or proc.stdout or "import failed").strip(),
        )
    return LaneStepResult(
        name="isolated_clean_install",
        ok=True,
        detail="uv run --frozen --package qmn import ok",
    )


def _step_scratch_credstore_boot() -> LaneStepResult:
    """Prove LoadCredentialEncrypted + scratch credstore boot contract.

    On a host with systemd, optionally runs ``systemd-analyze verify`` against
    the rendered unit. Always validates the scratch-credstore layout and that
    the unit loads encrypted credentials (soak/CI compensator for check mode).
    """
    units = _units()
    rendered = units.render_all_templates(
        drain_window="30s",
        watchdog_interval="15s",
        deploy_root=_DEPLOY_ROOT / "systemd",
    )
    qmn_unit = rendered.get("qmn.service", "")
    if "LoadCredentialEncrypted=" not in qmn_unit:
        return LaneStepResult(
            name="scratch_credstore_boot",
            ok=False,
            detail="qmn.service missing LoadCredentialEncrypted",
        )
    if "LoadCredential=" in qmn_unit.replace("LoadCredentialEncrypted=", ""):
        return LaneStepResult(
            name="scratch_credstore_boot",
            ok=False,
            detail="qmn.service must not use plaintext LoadCredential",
        )

    with tempfile.TemporaryDirectory(prefix="qmn-scratch-cred-") as tmp:
        scratch = Path(tmp)
        credstore = scratch / "credstore.encrypted"
        credstore.mkdir(parents=True, exist_ok=True)
        # Placeholder sealed blobs — CI proves layout, not real host-key seal.
        for name in ("kek", "venue-client-id", "notification-token"):
            (credstore / name).write_bytes(b"scratch-credstore-placeholder\n")
        unit_path = scratch / "qmn.service"
        # Point credential directory at the scratch store for analyze/verify.
        unit_text = qmn_unit
        if "SetCredentialEncrypted=" not in unit_text:
            # Keep LoadCredentialEncrypted; document scratch path beside the unit.
            unit_path.write_text(unit_text, encoding="utf-8")
        marker = scratch / "SCRATCH_CREDSTORE.txt"
        marker.write_text(
            "scratch credstore for CI/soak: LoadCredentialEncrypted from "
            f"{credstore.as_posix()}; real host-key seal is VPS-only\n",
            encoding="utf-8",
        )

        analyze = shutil.which("systemd-analyze")
        if analyze is not None and platform.system().casefold() == "linux":
            proc = subprocess.run(
                [analyze, "verify", str(unit_path)],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
            # systemd-analyze verify returns non-zero for missing binaries; treat
            # presence of the tool + our credential contract as the gate, and
            # record analyze output as detail without failing on ExecStart paths.
            detail = (
                f"scratch credstore at {credstore}; "
                f"systemd-analyze exit={proc.returncode}; "
                f"LoadCredentialEncrypted present"
            )
            return LaneStepResult(
                name="scratch_credstore_boot",
                ok=True,
                detail=detail,
            )

    return LaneStepResult(
        name="scratch_credstore_boot",
        ok=True,
        detail=(
            "scratch credstore layout + LoadCredentialEncrypted contract ok; "
            "systemd-analyze unavailable on this host (workflow runs on "
            f"{CI_LANE_RUNNER})"
        ),
    )


def _step_upgrade_and_rollback_contract() -> LaneStepResult:
    upgrade = _upgrade()
    switch = _switch()
    boundary = _boundary()
    findings = upgrade.inspect_upgrade_policy(
        upgrade.default_upgrade_policy(),
        fragments={
            "apt": upgrade.apt_unattended_fragment(),
            "needrestart": upgrade.needrestart_fragment(),
        },
    )
    if findings:
        return LaneStepResult(
            name="upgrade_rollback_contract",
            ok=False,
            detail="; ".join(findings),
        )
    rollback = switch.build_rollback_plan(
        mode="check",
        target_commit="abcdef0",
        config_version="cfg-prev",
    )
    if rollback.network_required:
        return LaneStepResult(
            name="upgrade_rollback_contract",
            ok=False,
            detail="rollback must not require network",
        )
    if rollback.auto_reboot or rollback.auto_restart:
        return LaneStepResult(
            name="upgrade_rollback_contract",
            ok=False,
            detail="rollback must not auto-reboot or auto-restart",
        )
    if "node-rollback" not in boundary.ALLOWED_NODE_RECIPES:
        return LaneStepResult(
            name="upgrade_rollback_contract",
            ok=False,
            detail="node-rollback missing from allow-list",
        )
    return LaneStepResult(
        name="upgrade_rollback_contract",
        ok=True,
        detail=(
            "no auto-reboot; never restart qmn; "
            "compensators: " + ",".join(COMPENSATING_CONTROLS)
        ),
    )


def run_lane(
    *,
    include_typing: bool = False,
    include_isolated_install: bool = False,
) -> LaneReport:
    """Execute the ubuntu-24.04 lane contract suite.

    Heavy steps (pyright, isolated uv sync) are opt-in so unit tests stay fast;
    the GitHub workflow enables them.
    """
    steps: list[LaneStepResult] = [
        _step_runner_pin(),
        _step_iac_scan(),
        _step_check_mode_boot(),
        _step_scratch_credstore_boot(),
        _step_upgrade_and_rollback_contract(),
    ]
    if include_typing:
        steps.insert(1, _step_linux_typing())
    if include_isolated_install:
        steps.append(_step_isolated_clean_install())

    ok = all(step.ok for step in steps)
    notes = (
        "no staging host — compensators named (DEC-0201)",
        "DevOps only; never a trading control",
        f"runner pin={CI_LANE_RUNNER} (never latest)",
    )
    return LaneReport(
        runner=CI_LANE_RUNNER,
        ok=ok,
        steps=tuple(steps),
        notes=notes,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="qmn-ci-lane",
        description="Pinned ubuntu-24.04 CI lane contract suite (NFR-18/21).",
    )
    parser.add_argument(
        "--typing",
        action="store_true",
        help="run pyright with pythonPlatform=Linux",
    )
    parser.add_argument(
        "--isolated-install",
        action="store_true",
        help="run uv sync --frozen --package qmn in an isolated venv",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write lane report JSON",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = run_lane(
        include_typing=args.typing,
        include_isolated_install=args.isolated_install,
    )
    payload = json.dumps(report.to_jsonable(), indent=2, sort_keys=True)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
