"""``just node-switch`` / ``just node-rollback`` planner (TN-16 / FR-068 / NFR-18).

Privileged host acts on Ubuntu 24.04: materialize an immutable per-commit tree
under ``/opt/qmx``, run check-mode boot against the ``(commit, config)`` pair,
atomically flip the ``current`` symlink at a safe-point restart, prune to the
declared depth, and mint a deployment record. Rollback flips onto the previous
retained tree and its config pair with no network.

DevOps only: never imports ``qmn.host`` / ``qmn.doors``, never places, cancels,
amends, flattens, promotes, or activates (AR-79 / DEC-0202). Check mode and
fixture-root apply never SSH to Contabo.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Final, Literal, cast

__all__ = [
    "COMMIT_SHA_RE",
    "CURRENT_LINK_NAME",
    "DEFAULT_OPT_QMX",
    "DEFAULT_PRUNE_DEPTH",
    "DEPLOYMENT_RECORD_DIR",
    "REQUESTED_RESTART_EXIT",
    "ROLLBACK_RECIPE",
    "SWITCH_RECIPE",
    "TREES_DIR_NAME",
    "UV_SYNC_COMMAND",
    "DeploymentRecord",
    "ReleasePlan",
    "ReleaseStep",
    "apply_plan_to_fixture",
    "build_rollback_plan",
    "build_switch_plan",
    "load_deployment_record",
    "main",
    "read_current_commit",
    "write_plan",
]

_DEPLOY_ROOT: Final[Path] = Path(__file__).resolve().parent

SWITCH_RECIPE: Final[str] = "node-switch"
ROLLBACK_RECIPE: Final[str] = "node-rollback"
DEFAULT_OPT_QMX: Final[str] = "/opt/qmx"
TREES_DIR_NAME: Final[str] = "trees"
CURRENT_LINK_NAME: Final[str] = "current"
DEPLOYMENT_RECORD_DIR: Final[str] = "deployments"
UV_SYNC_COMMAND: Final[str] = "uv sync --frozen"
# Evidence default for check-mode / fixtures only — not a ratified constant (L38).
DEFAULT_PRUNE_DEPTH: Final[int] = 3
REQUESTED_RESTART_EXIT: Final[int] = 75
COMMIT_SHA_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{7,40}$")


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
class DeploymentRecord:
    """Paired commit + config version on the same version graph (DEC-0201)."""

    commit: str
    config_version: str
    previous_commit: str | None = None
    previous_config_version: str | None = None
    recipe: str = SWITCH_RECIPE
    check_mode_ok: bool = True

    def to_jsonable(self) -> dict[str, object]:
        return {
            "commit": self.commit,
            "config_version": self.config_version,
            "previous_commit": self.previous_commit,
            "previous_config_version": self.previous_config_version,
            "recipe": self.recipe,
            "check_mode_ok": self.check_mode_ok,
            "pair": [self.commit, self.config_version],
        }


@dataclass(frozen=True, slots=True)
class ReleaseStep:
    """One planned switch/rollback action."""

    kind: str
    target: str
    detail: str
    check_mode_only: bool = False
    requires_network: bool = False


@dataclass(frozen=True, slots=True)
class ReleasePlan:
    """Full switch or rollback plan (check mode or fixture apply)."""

    recipe: str
    principal: str
    mode: Literal["check", "apply"]
    steps: tuple[ReleaseStep, ...]
    record: DeploymentRecord
    ok: bool
    findings: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)
    auto_restart: bool = False
    auto_reboot: bool = False
    network_required: bool = False

    def to_jsonable(self) -> dict[str, object]:
        return {
            "recipe": self.recipe,
            "principal": self.principal,
            "mode": self.mode,
            "ok": self.ok,
            "steps": [asdict(step) for step in self.steps],
            "record": self.record.to_jsonable(),
            "findings": list(self.findings),
            "notes": list(self.notes),
            "auto_restart": self.auto_restart,
            "auto_reboot": self.auto_reboot,
            "network_required": self.network_required,
            "requested_restart_exit": REQUESTED_RESTART_EXIT,
        }


def _normalize_commit(commit: str) -> str:
    value = commit.strip().casefold()
    if not COMMIT_SHA_RE.fullmatch(value):
        raise ValueError(
            f"commit must be a 7-40 hex SHA, got {commit!r}"
        )
    return value


def _opt_root(root: Path | str | None) -> Path:
    if root is None:
        return Path(DEFAULT_OPT_QMX)
    return Path(root)


def trees_dir(opt_qmx: Path) -> Path:
    return opt_qmx / TREES_DIR_NAME


def current_link(opt_qmx: Path) -> Path:
    return opt_qmx / CURRENT_LINK_NAME


def deployments_dir(opt_qmx: Path) -> Path:
    return opt_qmx / DEPLOYMENT_RECORD_DIR


def tree_path(opt_qmx: Path, commit: str) -> Path:
    return trees_dir(opt_qmx) / commit


def record_path(opt_qmx: Path, commit: str) -> Path:
    return deployments_dir(opt_qmx) / f"{commit}.json"


def load_deployment_record(path: Path) -> DeploymentRecord:
    text = _safe_io.read_text_contained(path, contain_within=path.parent)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("deployment record must be a JSON object")
    record = cast("dict[str, object]", data)
    commit = record.get("commit")
    config_version = record.get("config_version")
    if not isinstance(commit, str) or not isinstance(config_version, str):
        raise ValueError("deployment record requires commit and config_version")
    previous_commit = record.get("previous_commit")
    previous_config = record.get("previous_config_version")
    recipe = record.get("recipe", SWITCH_RECIPE)
    check_ok = record.get("check_mode_ok", True)
    return DeploymentRecord(
        commit=_normalize_commit(commit),
        config_version=config_version,
        previous_commit=(
            _normalize_commit(previous_commit)
            if isinstance(previous_commit, str) and previous_commit
            else None
        ),
        previous_config_version=(
            previous_config if isinstance(previous_config, str) else None
        ),
        recipe=str(recipe),
        check_mode_ok=bool(check_ok),
    )


def read_current_commit(opt_qmx: Path) -> str | None:
    link = current_link(opt_qmx)
    if link.is_symlink():
        raw = os.readlink(link)
        name = Path(raw).name
        if COMMIT_SHA_RE.fullmatch(name.casefold()):
            return name.casefold()
        resolved = link.resolve()
        name = resolved.name
        if COMMIT_SHA_RE.fullmatch(name.casefold()):
            return name.casefold()
        return None
    if link.is_file():
        # Fixture fallback when the host cannot create symlinks (Windows without
        # Developer Mode). Production VPS always uses a real symlink.
        text = link.read_text(encoding="utf-8").strip()
        if COMMIT_SHA_RE.fullmatch(text.casefold()):
            return text.casefold()
        return None
    return None


def _assert_boundary(recipe: str) -> None:
    allowed = _boundary.ALLOWED_NODE_RECIPES
    if recipe not in allowed:
        raise RuntimeError(f"{recipe} missing from ALLOWED_NODE_RECIPES")
    for action in _boundary.FORBIDDEN_RECIPE_ACTIONS:
        if _boundary.recipe_action_allowed(action):
            raise RuntimeError(f"forbidden action unexpectedly allowed: {action}")


def build_switch_plan(
    *,
    commit: str,
    config_version: str,
    mode: Literal["check", "apply"] = "check",
    opt_qmx: Path | str | None = None,
    previous_commit: str | None = None,
    previous_config_version: str | None = None,
    prune_depth: int = DEFAULT_PRUNE_DEPTH,
    check_mode_ok: bool = True,
) -> ReleasePlan:
    """Plan a release switch. Check mode never mutates the host."""
    _assert_boundary(SWITCH_RECIPE)
    findings: list[str] = []
    target_commit = _normalize_commit(commit)
    if not config_version or not str(config_version).strip():
        findings.append("config_version is blank — commit/config pair refused")
    if prune_depth < 1:
        findings.append("prune_depth must be >= 1 (vps_disk_budget line item)")
    if not check_mode_ok:
        findings.append("check-mode boot refused — symlink flip blocked")

    root = _opt_root(opt_qmx)
    prev = (
        _normalize_commit(previous_commit)
        if previous_commit
        else read_current_commit(root)
    )
    prev_config = previous_config_version
    if prev is not None and prev_config is None:
        prev_record_file = record_path(root, prev)
        if prev_record_file.is_file():
            loaded = load_deployment_record(prev_record_file)
            prev_config = loaded.config_version

    check_only = mode == "check"
    steps: list[ReleaseStep] = [
        ReleaseStep(
            kind="preflight",
            target=target_commit,
            detail="validate commit SHA and paired config_version",
            check_mode_only=check_only,
        ),
        ReleaseStep(
            kind="backup",
            target=str(root / "staging"),
            detail="backup-first before materializing a new tree",
            check_mode_only=check_only,
        ),
        ReleaseStep(
            kind="materialize",
            target=str(tree_path(root, target_commit)),
            detail=(
                f"immutable clone at pinned commit into "
                f"{TREES_DIR_NAME}/{target_commit}"
            ),
            check_mode_only=check_only,
            requires_network=True,
        ),
        ReleaseStep(
            kind="sync",
            target=str(tree_path(root, target_commit)),
            detail=UV_SYNC_COMMAND,
            check_mode_only=check_only,
            requires_network=False,
        ),
        ReleaseStep(
            kind="check_mode_boot",
            target=f"{target_commit}+{config_version}",
            detail=(
                "dry-run boot against the new tree validating the exact "
                "(commit, config) pair; never opens a sequencer"
            ),
            check_mode_only=check_only,
        ),
        ReleaseStep(
            kind="atomic_symlink_flip",
            target=str(current_link(root)),
            detail=(
                f"atomic flip of {CURRENT_LINK_NAME} at safe-point restart "
                f"(exit {REQUESTED_RESTART_EXIT}); never rewrites a running tree"
            ),
            check_mode_only=check_only,
        ),
        ReleaseStep(
            kind="deployment_record",
            target=str(record_path(root, target_commit)),
            detail="mint deployment record pairing commit and config_version",
            check_mode_only=check_only,
        ),
        ReleaseStep(
            kind="prune",
            target=str(trees_dir(root)),
            detail=(
                f"prune per-commit trees to depth={prune_depth}; "
                "previous retained tree stays recoverable for rollback"
            ),
            check_mode_only=check_only,
        ),
    ]

    record = DeploymentRecord(
        commit=target_commit,
        config_version=str(config_version).strip(),
        previous_commit=prev,
        previous_config_version=prev_config,
        recipe=SWITCH_RECIPE,
        check_mode_ok=check_mode_ok,
    )
    notes = (
        "DevOps only — never a trading control",
        f"principal={_boundary.OPS_PRINCIPAL_NAME}",
        "check mode plans only; apply requires ops-principal sudo on the VPS",
        "routine upgrades never auto-switch or reboot; only explicit node-switch",
        "do not SSH to Contabo from CI or developer workstations for this story",
    )
    ok = not findings
    return ReleasePlan(
        recipe=SWITCH_RECIPE,
        principal=_boundary.OPS_PRINCIPAL_NAME,
        mode=mode,
        steps=tuple(steps),
        record=record,
        ok=ok,
        findings=tuple(findings),
        notes=notes,
        auto_restart=False,
        auto_reboot=False,
        network_required=True,
    )


def build_rollback_plan(
    *,
    mode: Literal["check", "apply"] = "check",
    opt_qmx: Path | str | None = None,
    target_commit: str | None = None,
    config_version: str | None = None,
) -> ReleasePlan:
    """Plan a rollback onto the previous retained tree — no network."""
    _assert_boundary(ROLLBACK_RECIPE)
    findings: list[str] = []
    root = _opt_root(opt_qmx)
    current = read_current_commit(root)

    resolved_commit = target_commit
    resolved_config = config_version
    previous_of_current: str | None = None
    previous_config_of_current: str | None = None

    if resolved_commit is None and current is not None:
        current_record_file = record_path(root, current)
        if current_record_file.is_file():
            current_record = load_deployment_record(current_record_file)
            resolved_commit = current_record.previous_commit
            resolved_config = current_record.previous_config_version
            previous_of_current = current
            previous_config_of_current = current_record.config_version
        else:
            findings.append(
                f"no deployment record for current commit {current}; "
                "cannot resolve previous pair"
            )
    elif resolved_commit is not None:
        resolved_commit = _normalize_commit(resolved_commit)
        if resolved_config is None:
            target_record_file = record_path(root, resolved_commit)
            if target_record_file.is_file():
                loaded = load_deployment_record(target_record_file)
                resolved_config = loaded.config_version
            else:
                findings.append(
                    f"no deployment record for rollback target {resolved_commit}"
                )
        previous_of_current = current

    if resolved_commit is None:
        findings.append("rollback target commit unresolved")
    if not resolved_config:
        findings.append("rollback config_version unresolved — pair refused")

    check_only = mode == "check"
    commit_label = resolved_commit or "unresolved"
    config_label = resolved_config or "unresolved"
    steps: list[ReleaseStep] = [
        ReleaseStep(
            kind="preflight",
            target=commit_label,
            detail="resolve previous retained tree and its config pair",
            check_mode_only=check_only,
        ),
        ReleaseStep(
            kind="verify_retained",
            target=str(tree_path(root, commit_label)),
            detail="confirm previous per-commit tree still retained (no network)",
            check_mode_only=check_only,
            requires_network=False,
        ),
        ReleaseStep(
            kind="atomic_symlink_flip",
            target=str(current_link(root)),
            detail=(
                f"atomic flip of {CURRENT_LINK_NAME} onto previous retained tree "
                f"at safe-point restart (exit {REQUESTED_RESTART_EXIT})"
            ),
            check_mode_only=check_only,
        ),
        ReleaseStep(
            kind="deployment_record",
            target=str(record_path(root, commit_label)),
            detail=(
                "record rollback onto previous (commit, config) pair; "
                "pair remains joined"
            ),
            check_mode_only=check_only,
        ),
    ]

    # Refuse any step that would pull or sync over the network.
    if any(step.requires_network for step in steps):
        findings.append("rollback must not require network")

    record = DeploymentRecord(
        commit=commit_label if resolved_commit else "unresolved",
        config_version=config_label,
        previous_commit=previous_of_current,
        previous_config_version=previous_config_of_current,
        recipe=ROLLBACK_RECIPE,
        check_mode_ok=True,
    )
    notes = (
        "DevOps only — never a trading control",
        f"principal={_boundary.OPS_PRINCIPAL_NAME}",
        "rollback needs no network — previous retained tree only",
        "never auto-triggered by package/OS upgrades",
    )
    ok = not findings and resolved_commit is not None and bool(resolved_config)
    return ReleasePlan(
        recipe=ROLLBACK_RECIPE,
        principal=_boundary.OPS_PRINCIPAL_NAME,
        mode=mode,
        steps=tuple(steps),
        record=record,
        ok=ok,
        findings=tuple(findings),
        notes=notes,
        auto_restart=False,
        auto_reboot=False,
        network_required=False,
    )


def _atomic_symlink_to(link: Path, target: Path) -> None:
    """Flip ``link`` to ``target`` atomically via a temporary sibling name.

    Production path is a real symlink. When the host cannot create symlinks
    (common on Windows factory workers without Developer Mode), fall back to an
    atomic pointer-file replace that still pairs ``current`` to one commit SHA.
    The ubuntu-24.04 CI lane exercises the real symlink form.
    """
    link.parent.mkdir(parents=True, exist_ok=True)
    tmp = link.parent / f".{link.name}.tmp-{os.getpid()}"
    if tmp.exists() or tmp.is_symlink():
        if tmp.is_dir() and not tmp.is_symlink():
            _remove_tree(tmp)
        else:
            tmp.unlink()
    try:
        rel = os.path.relpath(target, start=link.parent)
    except ValueError:
        rel = str(target)
    try:
        tmp.symlink_to(rel, target_is_directory=True)
        os.replace(tmp, link)
        return
    except OSError:
        if tmp.exists() or tmp.is_symlink():
            tmp.unlink(missing_ok=True)
        # Atomic pointer-file fallback for fixture hosts without symlink rights.
        tmp.write_text(target.name.casefold() + "\n", encoding="utf-8")
        os.replace(tmp, link)


def apply_plan_to_fixture(plan: ReleasePlan, opt_qmx: Path) -> DeploymentRecord:
    """Apply a switch/rollback plan against a fixture ``/opt/qmx`` tree.

    Used by tests and the CI lane. Never touches the live VPS path unless the
    caller deliberately passes ``/opt/qmx`` (refused for apply off-VPS in
    ``main``).
    """
    if not plan.ok:
        raise RuntimeError(f"refusing to apply failed plan: {plan.findings}")
    if plan.auto_reboot or plan.auto_restart:
        raise RuntimeError("plan must not auto-reboot or auto-restart the node")

    trees = trees_dir(opt_qmx)
    trees.mkdir(parents=True, exist_ok=True)
    deployments_dir(opt_qmx).mkdir(parents=True, exist_ok=True)
    record = plan.record

    if plan.recipe == SWITCH_RECIPE:
        new_tree = tree_path(opt_qmx, record.commit)
        new_tree.mkdir(parents=True, exist_ok=True)
        # Marker proving materialize + sync landed in the new tree only.
        _safe_io.write_text_exclusive_no_follow(
            new_tree / ".qmx-release",
            json.dumps(
                {
                    "commit": record.commit,
                    "config_version": record.config_version,
                    "synced": UV_SYNC_COMMAND,
                },
                sort_keys=True,
            )
            + "\n",
            contain_within=new_tree,
        )
        if not record.check_mode_ok:
            raise RuntimeError("check-mode boot must pass before symlink flip")
        _atomic_symlink_to(current_link(opt_qmx), new_tree)
        out = record_path(opt_qmx, record.commit)
        _safe_io.write_text_exclusive_no_follow(
            out,
            json.dumps(record.to_jsonable(), indent=2, sort_keys=True) + "\n",
            contain_within=deployments_dir(opt_qmx),
        )
        _prune_trees(opt_qmx, keep_commit=record.commit, depth=DEFAULT_PRUNE_DEPTH)
        return record

    if plan.recipe == ROLLBACK_RECIPE:
        target = tree_path(opt_qmx, record.commit)
        if not target.is_dir():
            raise RuntimeError(
                f"previous retained tree missing: {target} (rollback needs no network)"
            )
        _atomic_symlink_to(current_link(opt_qmx), target)
        # Re-assert the pair; do not invent a new config under a forward commit.
        out = record_path(opt_qmx, record.commit)
        rollback_record = DeploymentRecord(
            commit=record.commit,
            config_version=record.config_version,
            previous_commit=record.previous_commit,
            previous_config_version=record.previous_config_version,
            recipe=ROLLBACK_RECIPE,
            check_mode_ok=True,
        )
        _safe_io.write_text_exclusive_no_follow(
            out,
            json.dumps(rollback_record.to_jsonable(), indent=2, sort_keys=True)
            + "\n",
            contain_within=deployments_dir(opt_qmx),
        )
        return rollback_record

    raise RuntimeError(f"unknown recipe {plan.recipe!r}")


def _remove_tree(path: Path) -> None:
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_file() or child.is_symlink():
            child.unlink(missing_ok=True)
        elif child.is_dir():
            child.rmdir()
    path.rmdir()


def _prune_trees(opt_qmx: Path, *, keep_commit: str, depth: int) -> None:
    """Retain up to ``depth`` newest trees by mtime; always keep ``keep_commit``."""
    trees = trees_dir(opt_qmx)
    if not trees.is_dir() or depth < 1:
        return
    entries = [p for p in trees.iterdir() if p.is_dir()]
    entries.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    keep_names: set[str] = {keep_commit}
    for entry in entries:
        if len(keep_names) >= depth:
            break
        keep_names.add(entry.name)
    for entry in entries:
        if entry.name not in keep_names:
            _remove_tree(entry)


def write_plan(plan: ReleasePlan, destination: Path) -> None:
    """Write the plan JSON."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    _safe_io.write_text_exclusive_no_follow(
        destination,
        json.dumps(plan.to_jsonable(), indent=2, sort_keys=True) + "\n",
        contain_within=destination.parent,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="node-switch/node-rollback",
        description=(
            "Plan or fixture-apply a node release switch/rollback (DevOps only). "
            "Default is check mode."
        ),
    )
    parser.add_argument(
        "recipe",
        choices=(SWITCH_RECIPE, ROLLBACK_RECIPE, "switch", "rollback"),
        help="node-switch or node-rollback",
    )
    parser.add_argument(
        "--commit",
        default=None,
        help="target commit SHA (required for switch)",
    )
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
        help="apply against a scratch /opt/qmx fixture (CI/tests only)",
    )
    parser.add_argument(
        "--prune-depth",
        type=int,
        default=DEFAULT_PRUNE_DEPTH,
        help="retained per-commit tree depth (vps_disk_budget line item)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write plan JSON to this path",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    recipe = args.recipe
    if recipe == "switch":
        recipe = SWITCH_RECIPE
    elif recipe == "rollback":
        recipe = ROLLBACK_RECIPE

    if args.apply and args.fixture_root is None:
        print(
            "refusing --apply without --fixture-root: run on the VPS under the "
            "ops principal sudo path; CI and workstations use --check-mode or "
            "--fixture-root only",
            file=sys.stderr,
        )
        return 2

    mode: Literal["check", "apply"] = (
        "apply" if args.fixture_root is not None else "check"
    )

    if recipe == SWITCH_RECIPE:
        if not args.commit:
            print("node-switch requires --commit", file=sys.stderr)
            return 2
        if not args.config_version:
            print("node-switch requires --config-version", file=sys.stderr)
            return 2
        plan = build_switch_plan(
            commit=args.commit,
            config_version=args.config_version,
            mode=mode,
            opt_qmx=args.fixture_root,
            prune_depth=args.prune_depth,
        )
    else:
        plan = build_rollback_plan(
            mode=mode,
            opt_qmx=args.fixture_root,
            target_commit=args.commit,
            config_version=args.config_version,
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
