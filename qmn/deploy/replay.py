"""Restricted ``just node-replay`` recipe (TN-21 / Story 27.7).

Plans or spawns a credential-free recorded-day decision diff OUTSIDE the
node process. Check mode by default. Never imports ``qmn.host`` / ``qmn.doors``,
never resolves a secret, never opens a live sink, never places/cancels/amends/
flattens/promotes/activates (AR-79 / DEC-0202).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Final, Literal

__all__ = [
    "REPLAY_RECIPE",
    "ReplayPlan",
    "ReplayStep",
    "build_replay_plan",
    "main",
    "write_plan",
]

_DEPLOY_ROOT: Final[Path] = Path(__file__).resolve().parent
REPLAY_RECIPE: Final[str] = "node-replay"
REPLAY_MODULE: Final[str] = "qmn.replay"
DEFAULT_EVIDENCE: Final[str] = "/var/lib/qmx/evidence"


def _load_sibling(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_boundary = _load_sibling("qmn_deploy_boundary", _DEPLOY_ROOT / "boundary.py")
_safe_io = _load_sibling("qmn_deploy_safe_io", _DEPLOY_ROOT / "safe_io.py")


@dataclass(frozen=True, slots=True)
class ReplayStep:
    kind: str
    target: str
    detail: str
    check_mode_only: bool = False


@dataclass(frozen=True, slots=True)
class ReplayPlan:
    recipe: str
    principal: str
    ok: bool
    mode: str
    world: str
    day_or_range: str
    evidence_root: str
    live_network: bool
    secrets_resolved: bool
    fill_simulation: bool
    argv: tuple[str, ...]
    steps: tuple[ReplayStep, ...]
    findings: tuple[str, ...]

    def to_jsonable(self) -> dict[str, object]:
        return {
            "recipe": self.recipe,
            "principal": self.principal,
            "ok": self.ok,
            "mode": self.mode,
            "world": self.world,
            "day_or_range": self.day_or_range,
            "evidence_root": self.evidence_root,
            "live_network": self.live_network,
            "secrets_resolved": self.secrets_resolved,
            "fill_simulation": self.fill_simulation,
            "argv": list(self.argv),
            "steps": [
                {
                    "kind": step.kind,
                    "target": step.target,
                    "detail": step.detail,
                    "check_mode_only": step.check_mode_only,
                }
                for step in self.steps
            ],
            "findings": list(self.findings),
        }


def build_replay_plan(
    *,
    mode: Literal["check", "apply"] = "check",
    day_or_range: str = "recorded-day",
    evidence_root: str = DEFAULT_EVIDENCE,
    spec: str | None = None,
    output: str | None = None,
) -> ReplayPlan:
    """Plan a process-per-job replay spawn. Never a trading control."""
    findings: list[str] = []
    if not day_or_range.strip():
        findings.append("node-replay requires a day or range")
    argv = (
        sys.executable,
        "-m",
        REPLAY_MODULE,
        "--spec",
        spec or "<spec.json>",
        "--output",
        output or "<diff.json>",
    )
    steps = (
        ReplayStep(
            kind="spawn_outside_node",
            target=REPLAY_MODULE,
            detail="stdlib process-per-job spawn; never a second loop on the node thread",
        ),
        ReplayStep(
            kind="world",
            target="replay",
            detail="composition world is replay; WriterIds are disjoint",
        ),
        ReplayStep(
            kind="import_port",
            target="replay-import",
            detail="one-way sealed-archive read; no cross-world write",
        ),
        ReplayStep(
            kind="reuse_snapshots",
            target="signal-snapshot",
            detail="reuse recorded SQS snapshots; never recompute",
        ),
        ReplayStep(
            kind="refuse_fill_and_submit",
            target="GAP-0056",
            detail="no fill simulation and no command submit; GAP-0056 remains deferred",
        ),
        ReplayStep(
            kind="diagnostic_only",
            target="decision-diff",
            detail="ungoverned diagnostic report; never an admission or live gate",
        ),
        ReplayStep(
            kind="refuse_secrets_network",
            target="preflight",
            detail="resolves no secret, opens no socket, constructs no live sink",
            check_mode_only=True,
        ),
    )
    return ReplayPlan(
        recipe=REPLAY_RECIPE,
        principal=_boundary.OPS_PRINCIPAL_NAME,
        ok=len(findings) == 0,
        mode=mode,
        world="replay",
        day_or_range=day_or_range.strip(),
        evidence_root=evidence_root,
        live_network=False,
        secrets_resolved=False,
        fill_simulation=False,
        argv=argv,
        steps=steps,
        findings=tuple(findings),
    )


def write_plan(plan: ReplayPlan, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    _safe_io.write_text_exclusive_no_follow(
        destination,
        json.dumps(plan.to_jsonable(), indent=2, sort_keys=True) + "\n",
        contain_within=destination.parent,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="node-replay",
        description=(
            "Plan or spawn a credential-free recorded-day decision diff "
            "(DevOps only). Default is check mode. Never a trading control."
        ),
    )
    parser.add_argument(
        "--check-mode",
        action="store_true",
        default=True,
        help="plan the spawn only (default)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="spawn the replay child (refused without --fixture-root)",
    )
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=None,
        help="isolated evidence tree for CI/tests; never a live venue path",
    )
    parser.add_argument(
        "--day",
        default="recorded-day",
        help="recorded day or range token",
    )
    parser.add_argument("--spec", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None, help="write plan JSON")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.apply and args.fixture_root is None:
        print(
            "refusing --apply without --fixture-root: factory tests spawn against "
            "an isolated sealed-archive fixture; live VPS replay is soak-local",
            file=sys.stderr,
        )
        return 2

    mode: Literal["check", "apply"] = "apply" if args.fixture_root is not None else "check"
    evidence = str(args.fixture_root) if args.fixture_root is not None else DEFAULT_EVIDENCE
    plan = build_replay_plan(
        mode=mode,
        day_or_range=args.day,
        evidence_root=evidence,
        spec=str(args.spec) if args.spec is not None else None,
        output=str(args.output) if args.output is not None else None,
    )
    if args.fixture_root is not None and args.spec is not None and args.output is not None:
        spawned = subprocess.run(
            [
                sys.executable,
                "-m",
                REPLAY_MODULE,
                "--spec",
                str(args.spec),
                "--output",
                str(args.output),
            ],
            check=False,
        )
        if spawned.returncode != 0:
            return spawned.returncode
    payload = json.dumps(plan.to_jsonable(), indent=2, sort_keys=True)
    if args.out is not None:
        write_plan(plan, args.out)
    else:
        print(payload)
    return 0 if plan.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
