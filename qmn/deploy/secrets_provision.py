"""Restricted ``just node-secrets-provision`` wizard (TN-12 / Story 27.1).

Human-only workstation step. Check mode plans the stdin → systemd-creds
host-key seal without reading Windows Credential Manager, without SSH, and
without writing secret values into the plan. Live ``--apply`` is refused
off-VPS. Fixture apply streams injected named secrets through stdin into a
recording seal transport — never argv, never a file, never echoed, never
logged. The VPS never mints the backup payload key; escrow is not this recipe.

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
from typing import Final, Literal, Protocol

__all__ = [
    "PROVISION_RECIPE",
    "MappingCredentialSource",
    "ProvisionPlan",
    "ProvisionStep",
    "RecordingSealTransport",
    "SealReceipt",
    "apply_plan_to_fixture",
    "build_provision_plan",
    "main",
    "write_plan",
]

_DEPLOY_ROOT: Final[Path] = Path(__file__).resolve().parent
PROVISION_RECIPE: Final[str] = "node-secrets-provision"
DEFAULT_IDENTITY_FILE: Final[str] = "~/.ssh/qmx_provisioning"
DEFAULT_HOST: Final[str] = "qmx-vps"


def _load_sibling(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_boundary = _load_sibling("qmn_deploy_boundary", _DEPLOY_ROOT / "boundary.py")
_creds = _load_sibling("qmn_deploy_creds", _DEPLOY_ROOT / "creds.py")
_safe_io = _load_sibling("qmn_deploy_safe_io", _DEPLOY_ROOT / "safe_io.py")
_units = _load_sibling("qmn_deploy_units", _DEPLOY_ROOT / "systemd" / "units.py")


class CredentialSource(Protocol):
    """Named ``qmx/<slot>`` provisioning source. Check mode never calls it."""

    def read_named(self, slot: str) -> str | None: ...


class EncryptTransport(Protocol):
    """Seal one named secret from stdin. Must never put material on argv."""

    def seal(self, *, name: str, material: str, argv: Sequence[str]) -> SealReceipt: ...


@dataclass(frozen=True, slots=True)
class SealReceipt:
    """``is_set`` metadata after a seal — never a value."""

    name: str
    is_set: bool
    stdin_used: bool


@dataclass
class MappingCredentialSource:
    """Injected named secrets for fixture apply. Never used in check mode."""

    values: Mapping[str, str]

    def read_named(self, slot: str) -> str | None:
        return self.values.get(slot)


@dataclass
class RecordingSealTransport:
    """Fixture seal: records slot names and argv, never persists plaintext."""

    sealed: list[str] = field(default_factory=list[str])
    argv_history: list[tuple[str, ...]] = field(default_factory=list[tuple[str, ...]])

    def seal(self, *, name: str, material: str, argv: Sequence[str]) -> SealReceipt:
        if _creds.argv_contains_plaintext(argv, material):
            raise RuntimeError("secret material appeared in argv")
        self.argv_history.append(tuple(argv))
        self.sealed.append(name)
        return SealReceipt(name=name, is_set=True, stdin_used=True)


@dataclass(frozen=True, slots=True)
class ProvisionStep:
    """One planned wizard action. ``detail`` never carries a secret value."""

    kind: str
    target: str
    detail: str
    stdin_origin: str
    check_mode_only: bool = False


@dataclass(frozen=True, slots=True)
class ProvisionPlan:
    """Check-mode or fixture-apply plan. JSON-able without secret values."""

    recipe: str
    principal: str
    mode: Literal["check", "apply"]
    ssh_identity: str
    seal_flag: str
    steps: tuple[ProvisionStep, ...]
    is_set: Mapping[str, bool]
    ok: bool
    findings: tuple[str, ...]
    notes: tuple[str, ...]

    def to_jsonable(self) -> dict[str, object]:
        return {
            "recipe": self.recipe,
            "principal": self.principal,
            "mode": self.mode,
            "ssh_identity": self.ssh_identity,
            "seal_flag": self.seal_flag,
            "ok": self.ok,
            "findings": list(self.findings),
            "notes": list(self.notes),
            "is_set": dict(self.is_set),
            "steps": [asdict(step) for step in self.steps],
        }


def _assert_boundary() -> None:
    allowed = _boundary.ALLOWED_NODE_RECIPES
    if PROVISION_RECIPE not in allowed:
        raise RuntimeError(f"{PROVISION_RECIPE} missing from ALLOWED_NODE_RECIPES")
    for action in _boundary.FORBIDDEN_RECIPE_ACTIONS:
        if _boundary.recipe_action_allowed(action):
            raise RuntimeError(f"forbidden action unexpectedly allowed: {action}")


def build_provision_plan(
    *,
    mode: Literal["check", "apply"] = "check",
    ssh_identity: str = _creds.PROVISIONING_SSH_IDENTITY,
    seal_flag: str = _creds.SEAL_FLAG,
    identity_file: str = DEFAULT_IDENTITY_FILE,
    host: str = DEFAULT_HOST,
    present_slots: frozenset[str] | None = None,
) -> ProvisionPlan:
    """Plan the restricted wizard. Check mode never reads secret values."""
    _assert_boundary()
    findings: list[str] = []
    identity_finding = _creds.validate_provisioning_identity(ssh_identity)
    if identity_finding is not None:
        findings.append(identity_finding)
    seal_finding = _creds.validate_seal_flag(seal_flag)
    if seal_finding is not None:
        findings.append(seal_finding)
    if seal_flag == _units.FORBIDDEN_SEAL_FLAG:
        findings.append("unit contract forbids --with-key=auto")

    present = present_slots if present_slots is not None else frozenset(_creds.WORKSTATION_SLOTS)
    check_only = mode == "check"
    steps: list[ProvisionStep] = [
        ProvisionStep(
            kind="mint_kek_on_vps",
            target=_creds.KEK_SLOT,
            detail=(
                "generate the KEK on the VPS and seal with systemd-creds "
                f"encrypt {_creds.SEAL_FLAG} --name=kek; stdin_origin=vps"
            ),
            stdin_origin="vps",
            check_mode_only=check_only,
        )
    ]
    is_set: dict[str, bool] = {_creds.KEK_SLOT: True}
    for slot in _creds.WORKSTATION_SLOTS:
        argv = _creds.ssh_stdin_encrypt_argv(host=host, identity_file=identity_file, slot=slot)
        if any(token == _creds.FORBIDDEN_SEAL_FLAG for token in argv):
            findings.append(f"{slot}: argv contains forbidden seal flag")
        if slot in _creds.NEVER_VPS_MINTED_SLOTS and slot not in present:
            findings.append(
                f"{slot} is workstation-generated and is never VPS-minted; "
                "escrow is not this recipe"
            )
            is_set[slot] = False
            steps.append(
                ProvisionStep(
                    kind="refuse_vps_mint",
                    target=slot,
                    detail="VPS mint of backup-payload-key is forbidden",
                    stdin_origin="none",
                    check_mode_only=check_only,
                )
            )
            continue
        stdin_origin = "workstation_credman"
        if slot not in present:
            is_set[slot] = False
            steps.append(
                ProvisionStep(
                    kind="missing_named_secret",
                    target=slot,
                    detail="named qmx/* entry absent; value is never logged",
                    stdin_origin="none",
                    check_mode_only=check_only,
                )
            )
            continue
        is_set[slot] = True
        steps.append(
            ProvisionStep(
                kind="stream_stdin_encrypt",
                target=slot,
                detail=(
                    "read qmx/"
                    + slot
                    + " and stream stdin into systemd-creds encrypt "
                    + _creds.SEAL_FLAG
                    + " --name="
                    + slot
                    + "; never argv/file/echo/log"
                ),
                stdin_origin=stdin_origin,
                check_mode_only=check_only,
            )
        )
    steps.append(
        ProvisionStep(
            kind="verify_is_set",
            target="secrets_is_set",
            detail=("operator-principal secrets_is_set metadata only; never values"),
            stdin_origin="none",
            check_mode_only=check_only,
        )
    )
    notes = (
        "DevOps only — never a trading control",
        f"principal={_boundary.OPS_PRINCIPAL_NAME}",
        "human-only workstation wizard; dedicated provisioning SSH identity",
        "plaintext on SSH stdin only; systemd-creds --with-key=host",
        "VPS never mints backup-payload-key; do not invent escrow",
        "check mode does not read Credential Manager or SSH to a VPS",
        "compromise drill uses demo credentials only",
    )
    return ProvisionPlan(
        recipe=PROVISION_RECIPE,
        principal=_boundary.OPS_PRINCIPAL_NAME,
        mode=mode,
        ssh_identity=ssh_identity,
        seal_flag=seal_flag,
        steps=tuple(steps),
        is_set=is_set,
        ok=not findings,
        findings=tuple(findings),
        notes=notes,
    )


def apply_plan_to_fixture(
    plan: ProvisionPlan,
    *,
    source: CredentialSource,
    transport: EncryptTransport,
    host: str = DEFAULT_HOST,
    identity_file: str = DEFAULT_IDENTITY_FILE,
) -> dict[str, bool]:
    """Fixture apply: stream named secrets through stdin into the seal transport."""
    if not plan.ok:
        raise RuntimeError(f"refusing to apply failed plan: {plan.findings}")
    is_set: dict[str, bool] = {}
    for step in plan.steps:
        if step.kind == "mint_kek_on_vps":
            argv = _creds.ssh_stdin_encrypt_argv(
                host=host, identity_file=identity_file, slot=_creds.KEK_SLOT
            )
            receipt = transport.seal(name=_creds.KEK_SLOT, material="", argv=argv)
            is_set[receipt.name] = receipt.is_set
            continue
        if step.kind == "refuse_vps_mint":
            is_set[step.target] = False
            continue
        if step.kind != "stream_stdin_encrypt":
            continue
        material = source.read_named(step.target)
        if material is None:
            is_set[step.target] = False
            continue
        argv = _creds.ssh_stdin_encrypt_argv(
            host=host, identity_file=identity_file, slot=step.target
        )
        if _creds.argv_contains_plaintext(argv, material):
            raise RuntimeError("secret material appeared in argv")
        receipt = transport.seal(name=step.target, material=material, argv=argv)
        is_set[receipt.name] = receipt.is_set
    return is_set


def write_plan(plan: ProvisionPlan, destination: Path) -> None:
    """Write the plan JSON. Payload contains names and is_set only."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    _safe_io.write_text_exclusive_no_follow(
        destination,
        json.dumps(plan.to_jsonable(), indent=2, sort_keys=True) + "\n",
        contain_within=destination.parent,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="node-secrets-provision",
        description=(
            "Plan or fixture-apply the restricted secrets wizard (DevOps only). "
            "Default is check mode. Never SSHes to a live VPS from this process."
        ),
    )
    parser.add_argument(
        "--check-mode",
        action="store_true",
        default=True,
        help="plan only; never read Credential Manager or SSH (default)",
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
        help="fixture apply root (CI/tests only); never a live VPS path",
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
            "refusing --apply without --fixture-root: do not provision a VPS "
            "from this process; CI and workstations use --check-mode or "
            "--fixture-root only",
            file=sys.stderr,
        )
        return 2

    mode: Literal["check", "apply"] = "apply" if args.fixture_root is not None else "check"
    plan = build_provision_plan(mode=mode)
    payload = json.dumps(plan.to_jsonable(), indent=2, sort_keys=True)
    if args.out is not None:
        write_plan(plan, args.out)
    else:
        print(payload)
    return 0 if plan.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
