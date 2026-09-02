"""``just node-lifecycle-campaign`` planner (Story 28.4 / TN-4/14/19/23).

Plans crash-loop, preflight, callback-wedge, clock, disk, data-freshness, and
SIGTERM injections. Check mode by default. Never applies a live VPS firewall,
never restores from a live bucket, and never trades (AR-79 / DEC-0202).
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
    "LIFECYCLE_RECIPE",
    "LifecycleCampaignPlan",
    "LifecycleCampaignStep",
    "apply_plan_to_fixture",
    "build_lifecycle_campaign_plan",
    "main",
    "write_plan",
]

_DEPLOY_ROOT: Final[Path] = Path(__file__).resolve().parent

LIFECYCLE_RECIPE: Final[str] = "node-lifecycle-campaign"
LIFECYCLE_INJECTIONS: Final[tuple[str, ...]] = (
    "crash-loop",
    "preflight",
    "callback-wedge",
    "clock",
    "disk",
    "data-freshness",
    "shutdown",
)
RUNS_LIVE_VPS_FIREWALL: Final[bool] = False
RUNS_LIVE_BUCKET_RESTORE: Final[bool] = False


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
class LifecycleCampaignStep:
    """One planned lifecycle injection or soak-local skip."""

    kind: str
    target: str
    detail: str
    check_mode_only: bool = True


@dataclass(frozen=True, slots=True)
class LifecycleCampaignPlan:
    """Check-mode lifecycle campaign plan — DevOps only, never a trading control."""

    recipe: str
    principal: str
    mode: Literal["check", "apply"]
    injections: tuple[str, ...]
    steps: tuple[LifecycleCampaignStep, ...]
    ok: bool
    findings: tuple[str, ...]
    notes: tuple[str, ...]
    runs_live_vps_firewall: bool = False
    runs_live_bucket_restore: bool = False
    devops_unable_to_trade: bool = True

    def to_jsonable(self) -> dict[str, object]:
        return {
            "devops_unable_to_trade": self.devops_unable_to_trade,
            "findings": list(self.findings),
            "injections": list(self.injections),
            "mode": self.mode,
            "notes": list(self.notes),
            "ok": self.ok,
            "principal": self.principal,
            "recipe": self.recipe,
            "runs_live_bucket_restore": self.runs_live_bucket_restore,
            "runs_live_vps_firewall": self.runs_live_vps_firewall,
            "steps": [asdict(step) for step in self.steps],
        }


def build_lifecycle_campaign_plan(
    *,
    mode: Literal["check", "apply"] = "check",
    run_live_vps_firewall: bool = False,
    run_live_bucket_restore: bool = False,
) -> LifecycleCampaignPlan:
    """Plan the Story 28.4 lifecycle injections; refuse live firewall/bucket."""
    _assert_boundary()
    findings: list[str] = []
    if run_live_vps_firewall:
        findings.append("live VPS firewall campaign is skipped (soak-local)")
    if run_live_bucket_restore:
        findings.append("live bucket restore is skipped (soak-local / AR-87)")
    for action in _boundary.FORBIDDEN_RECIPE_ACTIONS:
        if _boundary.recipe_action_allowed(action):
            findings.append(f"forbidden action unexpectedly allowed: {action}")

    steps = [
        LifecycleCampaignStep(
            kind="inject",
            target=name,
            detail=f"prove {name} degraded state through host campaign tests",
        )
        for name in LIFECYCLE_INJECTIONS
    ]
    steps.append(
        LifecycleCampaignStep(
            kind="skip",
            target="live-vps-firewall",
            detail="real VPS firewall campaign is not a Story 28.4 factory AC",
        )
    )
    steps.append(
        LifecycleCampaignStep(
            kind="skip",
            target="live-bucket-restore",
            detail="real Backblaze bucket restore is soak-local; local fixtures own restore proofs",
        )
    )
    notes = (
        "DevOps only — never a trading control",
        f"principal={_boundary.OPS_PRINCIPAL_NAME}",
        "check mode plans only; campaign proofs run as qmn.host tests",
        "do not SSH to Contabo from CI or developer workstations for this story",
        "stand-down keeps doors serving; only resurrect clears it",
        "quarantine survives restart until seat_reinstate",
        "SIGTERM flushes, mints UNKNOWN, never flattens",
    )
    return LifecycleCampaignPlan(
        recipe=LIFECYCLE_RECIPE,
        principal=_boundary.OPS_PRINCIPAL_NAME,
        mode=mode,
        injections=LIFECYCLE_INJECTIONS,
        steps=tuple(steps),
        ok=not findings,
        findings=tuple(findings),
        notes=notes,
        runs_live_vps_firewall=RUNS_LIVE_VPS_FIREWALL,
        runs_live_bucket_restore=RUNS_LIVE_BUCKET_RESTORE,
        devops_unable_to_trade=True,
    )


def apply_plan_to_fixture(plan: LifecycleCampaignPlan, fixture_root: Path) -> Path:
    """Materialize the lifecycle campaign plan under a scratch tree (CI/tests)."""
    if not plan.ok:
        raise RuntimeError(f"refusing to apply failed plan: {plan.findings}")
    if plan.runs_live_vps_firewall or plan.runs_live_bucket_restore:
        raise RuntimeError("plan must not run a live firewall or live bucket restore")
    fixture_root.mkdir(parents=True, exist_ok=True)
    out = fixture_root / "lifecycle-campaign.json"
    _safe_io.write_text_exclusive_no_follow(
        out,
        json.dumps(plan.to_jsonable(), indent=2, sort_keys=True) + "\n",
        contain_within=fixture_root,
    )
    return out


def write_plan(plan: LifecycleCampaignPlan, destination: Path) -> None:
    """Write the plan JSON."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    _safe_io.write_text_exclusive_no_follow(
        destination,
        json.dumps(plan.to_jsonable(), indent=2, sort_keys=True) + "\n",
        contain_within=destination.parent,
    )


def _assert_boundary() -> None:
    allowed = _boundary.ALLOWED_NODE_RECIPES
    if LIFECYCLE_RECIPE not in allowed:
        raise RuntimeError(f"{LIFECYCLE_RECIPE} missing from ALLOWED_NODE_RECIPES")
    for action in _boundary.FORBIDDEN_RECIPE_ACTIONS:
        if _boundary.recipe_action_allowed(action):
            raise RuntimeError(f"forbidden action unexpectedly allowed: {action}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="node-lifecycle-campaign",
        description=(
            "Plan the Story 28.4 lifecycle campaign (DevOps only). "
            "Default is check mode. Never applies a live firewall or live bucket restore."
        ),
    )
    parser.add_argument("--check-mode", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--fixture-root", type=Path, default=None)
    parser.add_argument("--live-firewall", action="store_true")
    parser.add_argument("--live-bucket-restore", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.apply and args.fixture_root is None:
        print(
            "refusing --apply without --fixture-root: this recipe never SSHes to "
            "a VPS and never applies a live firewall or live bucket restore",
            file=sys.stderr,
        )
        return 2
    if args.live_firewall:
        print(
            "refusing live VPS firewall campaign: Story 28.4 skips that AC",
            file=sys.stderr,
        )
        return 2
    if args.live_bucket_restore:
        print(
            "refusing live bucket restore: Story 28.4 skips that AC (AR-87)",
            file=sys.stderr,
        )
        return 2

    mode: Literal["check", "apply"] = "apply" if args.fixture_root is not None else "check"
    plan = build_lifecycle_campaign_plan(
        mode=mode,
        run_live_vps_firewall=False,
        run_live_bucket_restore=False,
    )
    if args.fixture_root is not None:
        apply_plan_to_fixture(plan, args.fixture_root)
    if args.out is not None:
        write_plan(plan, args.out)
    else:
        print(json.dumps(plan.to_jsonable(), indent=2, sort_keys=True))
    return 0 if plan.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
