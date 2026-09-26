"""``just node-demo-deploy`` planner (Story 28.2 / FR-059 / TN-9/16).

Plans the production VPS shape for the first-deployment demo window: qmn.service,
four node timers, separate observability unit, rooms/evidence/hub trees, doors,
chrony, backups, news intake, KSA, protection, seats, paired demo account, and
paper virtual ledger. Book routing is PAPER for the whole window.

Check mode by default. Live --apply is refused off-VPS; --fixture-root apply is
for CI/tests only. This recipe never procures a VPS, never SSHes to Contabo,
never opens live credentials, and never places/cancels/amends/flattens/promotes
or activates (AR-79 / DEC-0202).
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
    "DEMO_RECIPE",
    "DEMO_SHAPE_FIXTURE_NAME",
    "FIRST_DEPLOYMENT_BOOK_ROUTING",
    "LATE_LIVE_APPROVAL_DELAYS",
    "LIVE_SENSING_ALLOWED",
    "LIVE_SENSING_FORBIDDEN",
    "OPENS_LIVE_CREDENTIALS",
    "PROCURES_VPS",
    "DemoShapePlan",
    "DemoShapeStep",
    "apply_plan_to_fixture",
    "build_demo_shape_plan",
    "load_demo_shape_fixture",
    "main",
    "write_plan",
]

_DEPLOY_ROOT: Final[Path] = Path(__file__).resolve().parent

DEMO_RECIPE: Final[str] = "node-demo-deploy"
DEMO_SHAPE_FIXTURE_NAME: Final[str] = "demo-shape.json"
FIRST_DEPLOYMENT_BOOK_ROUTING: Final[str] = "PAPER"
PROCURES_VPS: Final[bool] = False
OPENS_LIVE_CREDENTIALS: Final[bool] = False
LIVE_SENSING_ALLOWED: Final[tuple[str, ...]] = (
    "sensing",
    "recording",
    "capability-verification",
    "baseline-accumulation",
)
LIVE_SENSING_FORBIDDEN: Final[tuple[str, ...]] = (
    "live-binding",
    "command-stream",
    "sequencer",
    "execution-target",
)
LATE_LIVE_APPROVAL_DELAYS: Final[tuple[str, ...]] = ("live-baseline", "go-live")
PRE_UNATTENDED_PROOFS: Final[tuple[str, ...]] = (
    "synthetic-alert",
    "missing-heartbeat-notification",
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
_units = _load_sibling("qmn_deploy_units", _DEPLOY_ROOT / "systemd" / "units.py")
_install = _load_sibling("qmn_deploy_install", _DEPLOY_ROOT / "install.py")
_safe_io = _load_sibling("qmn_deploy_safe_io", _DEPLOY_ROOT / "safe_io.py")


@dataclass(frozen=True, slots=True)
class DemoShapeStep:
    """One planned demo-shape action."""

    kind: str
    target: str
    detail: str
    check_mode_only: bool = False


@dataclass(frozen=True, slots=True)
class DemoShapePlan:
    """Full first-deployment demo-shape plan (check mode or fixture apply)."""

    recipe: str
    principal: str
    mode: Literal["check", "apply"]
    book_routing: str
    steps: tuple[DemoShapeStep, ...]
    units: tuple[str, ...]
    node_timers: tuple[str, ...]
    trees: tuple[str, ...]
    doors: tuple[str, ...]
    principals: tuple[str, ...]
    live_sensing_open: bool
    live_sensing_allowed: tuple[str, ...]
    live_sensing_forbidden: tuple[str, ...]
    late_live_delays: tuple[str, ...]
    pre_unattended: Mapping[str, bool]
    blocked_infra: tuple[str, ...]
    ok: bool
    findings: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)
    procures_vps: bool = False
    opens_live_credentials: bool = False
    auto_restart: bool = False
    auto_reboot: bool = False

    def to_jsonable(self) -> dict[str, object]:
        return {
            "auto_reboot": self.auto_reboot,
            "auto_restart": self.auto_restart,
            "blocked_infra": list(self.blocked_infra),
            "book_routing": self.book_routing,
            "doors": list(self.doors),
            "findings": list(self.findings),
            "late_live_delays": list(self.late_live_delays),
            "live_sensing_allowed": list(self.live_sensing_allowed),
            "live_sensing_forbidden": list(self.live_sensing_forbidden),
            "live_sensing_open": self.live_sensing_open,
            "mode": self.mode,
            "node_timers": list(self.node_timers),
            "notes": list(self.notes),
            "ok": self.ok,
            "opens_live_credentials": self.opens_live_credentials,
            "pre_unattended": dict(self.pre_unattended),
            "principal": self.principal,
            "principals": list(self.principals),
            "procures_vps": self.procures_vps,
            "recipe": self.recipe,
            "steps": [asdict(step) for step in self.steps],
            "trees": list(self.trees),
            "units": list(self.units),
        }


def load_demo_shape_fixture(path: Path | None = None) -> dict[str, object]:
    """Load the checked-in demo-shape inventory."""
    target = path if path is not None else _DEPLOY_ROOT / "fixtures" / DEMO_SHAPE_FIXTURE_NAME
    text = _safe_io.read_text_contained(target, contain_within=target.parent)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("demo-shape fixture must be a JSON object")
    return cast("dict[str, object]", data)


def build_demo_shape_plan(
    *,
    mode: Literal["check", "apply"] = "check",
    commit: str | None = None,
    config_version: str | None = None,
    live_credentials_present: bool = False,
    request_live_binding: bool = False,
    procure_vps: bool = False,
    open_live_credentials: bool = False,
    synthetic_alert_delivered: bool = False,
    missing_heartbeat_delivered: bool = False,
    vps_procured: bool = False,
    book_routing: str = FIRST_DEPLOYMENT_BOOK_ROUTING,
    deploy_root: Path | None = None,
    fixture: Mapping[str, object] | None = None,
) -> DemoShapePlan:
    """Plan the first-deployment demo shape. Check mode never mutates the host."""
    _assert_boundary()
    root = deploy_root or _DEPLOY_ROOT
    inventory = dict(fixture) if fixture is not None else load_demo_shape_fixture()
    findings: list[str] = []
    if procure_vps or PROCURES_VPS:
        findings.append("refusing to procure a VPS from node-demo-deploy")
    if open_live_credentials or OPENS_LIVE_CREDENTIALS:
        findings.append("refusing to open live credentials from node-demo-deploy")
    if book_routing != FIRST_DEPLOYMENT_BOOK_ROUTING:
        findings.append(
            f"Book routing must be PAPER for the first-deployment window, got {book_routing!r}"
        )
    if request_live_binding:
        findings.append(
            "live binding, command stream, sequencer, and execution target "
            "are forbidden during the first-deployment window"
        )
    fixture_routing = inventory.get("book_routing")
    if fixture_routing != FIRST_DEPLOYMENT_BOOK_ROUTING:
        findings.append("demo-shape fixture book_routing is not PAPER")

    install = _install.build_install_plan(
        mode="check",
        render_values={"drain_window": "30s", "watchdog_interval": "15s"},
        deploy_root=root,
    )
    if not install.ok:
        findings.append("install inventory refused — demo shape is the production shape")

    units = (
        "qmn.service",
        "qmn-news-calendar.service",
        "qmn-news-calendar.timer",
        "qmn-backup.service",
        "qmn-backup.timer",
        "qmn-restore-sample.service",
        "qmn-restore-sample.timer",
        "qmn-restore-full.service",
        "qmn-restore-full.timer",
        _units.OBSERVABILITY_UNIT,
    )
    rendered = frozenset(install.rendered_units)
    missing_units = tuple(name for name in units if name not in rendered)
    if missing_units:
        findings.append("missing unit renders: " + ",".join(missing_units))

    node_timers = (
        "qmn-news-calendar.timer",
        "qmn-backup.timer",
        "qmn-restore-sample.timer",
        "qmn-restore-full.timer",
    )
    trees = ("rooms", "evidence", "hub-inbox", "hub-published")
    doors = ("powers", "evidence")
    principals = (
        _units.NODE_SERVICE_ACCOUNT,
        _units.OBSERVABILITY_SERVICE_ACCOUNT,
        _boundary.OPS_PRINCIPAL_NAME,
    )

    check_only = mode == "check"
    steps: list[DemoShapeStep] = [
        DemoShapeStep(
            kind="inventory",
            target="production-shape",
            detail="same units/trees/doors as node-install — never a reduced paper substitute",
            check_mode_only=check_only,
        ),
        DemoShapeStep(
            kind="unit",
            target="qmn.service",
            detail="long-lived node under User=qmx",
            check_mode_only=check_only,
        ),
    ]
    for timer in node_timers:
        steps.append(
            DemoShapeStep(
                kind="timer",
                target=timer,
                detail="one of four node timers (news, backup, sample restore, full restore)",
                check_mode_only=check_only,
            )
        )
    steps.append(
        DemoShapeStep(
            kind="unit",
            target=_units.OBSERVABILITY_UNIT,
            detail="separate sixth unit — zero node authority",
            check_mode_only=check_only,
        )
    )
    for tree in trees:
        steps.append(
            DemoShapeStep(
                kind="tree",
                target=f"{_install.VAR_LIB_QMX}/{tree}",
                detail="writable tree owned by qmx",
                check_mode_only=check_only,
            )
        )
    steps.append(
        DemoShapeStep(
            kind="door",
            target=_units.POWERS_SOCKET_PATH,
            detail="unix-socket powers channel under SO_PEERCRED",
            check_mode_only=check_only,
        )
    )
    steps.append(
        DemoShapeStep(
            kind="door",
            target="127.0.0.1:8787",
            detail="localhost HTTP evidence channel",
            check_mode_only=check_only,
        )
    )
    steps.append(
        DemoShapeStep(
            kind="bootstrap",
            target="chrony",
            detail="chrony required by qmn.service After=",
            check_mode_only=check_only,
        )
    )
    for machinery in ("backups", "news-intake", "ksa", "protection", "seats"):
        steps.append(
            DemoShapeStep(
                kind="machinery",
                target=machinery,
                detail="production machinery on the demo binding — not a reduced substitute",
                check_mode_only=check_only,
            )
        )
    steps.append(
        DemoShapeStep(
            kind="routing",
            target="book-mode",
            detail="Book routing PAPER for the whole first-deployment window",
            check_mode_only=check_only,
        )
    )
    steps.append(
        DemoShapeStep(
            kind="account",
            target="paired-demo",
            detail="paired demo account + paper virtual ledger (role demo, world live)",
            check_mode_only=check_only,
        )
    )
    if live_credentials_present:
        steps.append(
            DemoShapeStep(
                kind="live-sensing",
                target="live-environment",
                detail=(
                    "sensing/recording/capability-verification/baseline only; "
                    "no live binding, command stream, sequencer, or execution target"
                ),
                check_mode_only=check_only,
            )
        )
        late_delays: tuple[str, ...] = ()
    else:
        steps.append(
            DemoShapeStep(
                kind="live-sensing",
                target="deferred",
                detail=(
                    "Spotware credentials absent — delay live baseline/go-live; demo week continues"
                ),
                check_mode_only=True,
            )
        )
        late_delays = LATE_LIVE_APPROVAL_DELAYS
    steps.append(
        DemoShapeStep(
            kind="pre-unattended",
            target="notify_test",
            detail="synthetic alert delivered end to end before unattended start",
            check_mode_only=check_only,
        )
    )
    steps.append(
        DemoShapeStep(
            kind="pre-unattended",
            target="missing-heartbeat",
            detail="missing-heartbeat notification delivered end to end",
            check_mode_only=check_only,
        )
    )
    steps.append(
        DemoShapeStep(
            kind="fault-injection",
            target="declared-boundary-only",
            detail="drills only at declared boundary/drill points — never continuous supervision",
            check_mode_only=True,
        )
    )
    if commit and config_version:
        steps.append(
            DemoShapeStep(
                kind="switch",
                target=f"{commit}+{config_version}",
                detail="node-switch check-mode boot of the (commit, config) pair",
                check_mode_only=check_only,
            )
        )

    blocked: list[str] = []
    if not vps_procured:
        blocked.append("vps_procurement")

    notes = (
        "DevOps only — never a trading control",
        f"principal={_boundary.OPS_PRINCIPAL_NAME}",
        "check mode plans only; apply requires ops-principal sudo on the VPS",
        "do not SSH to Contabo from CI or developer workstations for this story",
        "Book routing PAPER for the whole first-deployment window",
        "missing VPS/live credentials are blocked infra ACs, not unrelated-epic blockers",
    )
    ok = not findings
    return DemoShapePlan(
        recipe=DEMO_RECIPE,
        principal=_boundary.OPS_PRINCIPAL_NAME,
        mode=mode,
        book_routing=FIRST_DEPLOYMENT_BOOK_ROUTING,
        steps=tuple(steps),
        units=units,
        node_timers=node_timers,
        trees=trees,
        doors=doors,
        principals=principals,
        live_sensing_open=live_credentials_present and not request_live_binding,
        live_sensing_allowed=LIVE_SENSING_ALLOWED,
        live_sensing_forbidden=LIVE_SENSING_FORBIDDEN,
        late_live_delays=late_delays,
        pre_unattended={
            "synthetic_alert_delivered": synthetic_alert_delivered,
            "missing_heartbeat_delivered": missing_heartbeat_delivered,
        },
        blocked_infra=tuple(blocked),
        ok=ok,
        findings=tuple(findings),
        notes=notes,
        procures_vps=False,
        opens_live_credentials=False,
        auto_restart=False,
        auto_reboot=False,
    )


def apply_plan_to_fixture(plan: DemoShapePlan, fixture_root: Path) -> Path:
    """Materialize the demo-shape record under a scratch tree (CI/tests only)."""
    if not plan.ok:
        raise RuntimeError(f"refusing to apply failed plan: {plan.findings}")
    if plan.auto_reboot or plan.auto_restart:
        raise RuntimeError("plan must not auto-reboot or auto-restart the node")
    if plan.procures_vps or plan.opens_live_credentials:
        raise RuntimeError("plan must not procure a VPS or open live credentials")
    if plan.book_routing != FIRST_DEPLOYMENT_BOOK_ROUTING:
        raise RuntimeError("first-deployment Book routing must be PAPER")
    fixture_root.mkdir(parents=True, exist_ok=True)
    out = fixture_root / DEMO_SHAPE_FIXTURE_NAME
    _safe_io.write_text_exclusive_no_follow(
        out,
        json.dumps(plan.to_jsonable(), indent=2, sort_keys=True) + "\n",
        contain_within=fixture_root,
    )
    return out


def write_plan(plan: DemoShapePlan, destination: Path) -> None:
    """Write the plan JSON."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    _safe_io.write_text_exclusive_no_follow(
        destination,
        json.dumps(plan.to_jsonable(), indent=2, sort_keys=True) + "\n",
        contain_within=destination.parent,
    )


def _assert_boundary() -> None:
    allowed = _boundary.ALLOWED_NODE_RECIPES
    if DEMO_RECIPE not in allowed:
        raise RuntimeError(f"{DEMO_RECIPE} missing from ALLOWED_NODE_RECIPES")
    for action in _boundary.FORBIDDEN_RECIPE_ACTIONS:
        if _boundary.recipe_action_allowed(action):
            raise RuntimeError(f"forbidden action unexpectedly allowed: {action}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="node-demo-deploy",
        description=(
            "Plan or fixture-apply the first-deployment demo shape (DevOps only). "
            "Default is check mode. Never procures a VPS or opens live credentials."
        ),
    )
    parser.add_argument("--commit", default=None, help="candidate commit SHA")
    parser.add_argument(
        "--config-version",
        default=None,
        help="config version paired with the commit",
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
        help="apply on the VPS (refused off-VPS unless --fixture-root)",
    )
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=None,
        help="apply against a scratch tree (CI/tests only)",
    )
    parser.add_argument(
        "--live-credentials-present",
        action="store_true",
        help="Spotware credentials already exist — plan sensing-only live",
    )
    parser.add_argument(
        "--request-live-binding",
        action="store_true",
        help="forbidden: attempt a live binding during the first-deployment window",
    )
    parser.add_argument(
        "--procure-vps",
        action="store_true",
        help="forbidden: this story does not procure a VPS",
    )
    parser.add_argument(
        "--open-live-credentials",
        action="store_true",
        help="forbidden: this story does not open live credentials",
    )
    parser.add_argument(
        "--synthetic-alert-delivered",
        action="store_true",
        help="record that notify_test already delivered end to end",
    )
    parser.add_argument(
        "--missing-heartbeat-delivered",
        action="store_true",
        help="record that a missing-heartbeat notification already delivered",
    )
    parser.add_argument(
        "--vps-procured",
        action="store_true",
        help="record existing VPS procurement evidence (does not procure)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write plan JSON to this path",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.apply and args.fixture_root is None:
        print(
            "refusing --apply without --fixture-root: run on the VPS under the "
            "ops principal sudo path; CI and workstations use --check-mode or "
            "--fixture-root only; this story does not provision a VPS",
            file=sys.stderr,
        )
        return 2

    mode: Literal["check", "apply"] = "apply" if args.fixture_root is not None else "check"
    plan = build_demo_shape_plan(
        mode=mode,
        commit=args.commit,
        config_version=args.config_version,
        live_credentials_present=bool(args.live_credentials_present),
        request_live_binding=bool(args.request_live_binding),
        procure_vps=bool(args.procure_vps),
        open_live_credentials=bool(args.open_live_credentials),
        synthetic_alert_delivered=bool(args.synthetic_alert_delivered),
        missing_heartbeat_delivered=bool(args.missing_heartbeat_delivered),
        vps_procured=bool(args.vps_procured),
    )
    if args.out is not None:
        write_plan(plan, args.out)
    else:
        print(json.dumps(plan.to_jsonable(), indent=2, sort_keys=True))
    if not plan.ok:
        return 1
    if args.fixture_root is not None:
        apply_plan_to_fixture(plan, Path(args.fixture_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
