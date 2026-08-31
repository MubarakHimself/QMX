"""Tier-2 isolated-install smoke (AR-06/AR-18; enforcing the undeclared-import law).

``poe check-integration`` builds every workspace package with ``uv build
--all-packages``, but a workspace build resolves every member against every sibling
on the path — so it can never reveal a package that imports a sibling it did not
**declare**. Story 1.1's acceptance criterion is exactly that "an undeclared import
fails the isolated build", and only an install of one package *alone*, with only its
declared dependency closure, can prove it.

This smoke does that install-and-import, per member:

1. Build every member to wheels in a throwaway directory (``uv build
   --all-packages --wheel``).
2. Assert **no wheel ships ``qmf/__init__.py``** — the distributions are PEP 420
   namespace submodules, so an accidental package init that would collide two wheels
   on the ``qmf`` namespace fails the gate.
3. For each member, create a fresh empty virtualenv, ``uv pip install`` **that
   member alone** resolving only from the built wheels (plus its declared third-party
   deps, e.g. ``tzdata``), and ``import`` its ``qmf.*`` module in that env. If the
   member imports a sibling it did not declare, the module is absent from the isolated
   env and the import raises — the gate fails, exactly as the story requires.

Fail-closed: a build error, a namespace-init leak, an install failure, or an import
error exits nonzero. Read-only over the workspace source; all build and install output
lands in a temp dir that is removed on exit. Requires ``uv`` on PATH (the same tool the
rest of the gate uses). Run via ``python tools/isolated_build_check.py`` or ``poe
isolated-build``.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path

import workspace_meta
from workspace_meta import ROOT, Member

# The member modules must import under the same CPython the workspace pins
# (requires-python >=3.14,<3.15). Build the isolated envs against the running
# interpreter's minor version so uv resolves the same Python.
_PY_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"


class SmokeError(RuntimeError):
    """A fail-closed smoke failure with an operator-legible message."""


def _run(cmd: Sequence[str], *, what: str) -> subprocess.CompletedProcess[str]:
    """Run ``cmd``, capturing output; raise :class:`SmokeError` on a nonzero exit."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise SmokeError(f"{what}: cannot run {cmd[0]!r} ({exc}); is uv on PATH?") from exc
    if proc.returncode != 0:
        raise SmokeError(
            f"{what}: command failed (exit {proc.returncode})\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  stdout: {proc.stdout.strip()}\n"
            f"  stderr: {proc.stderr.strip()}"
        )
    return proc


def _venv_python(venv: Path) -> Path:
    """The interpreter path inside ``venv`` (Windows ``Scripts`` vs POSIX ``bin``)."""
    windows = venv / "Scripts" / "python.exe"
    return windows if windows.exists() else venv / "bin" / "python"


def build_wheels(dist_dir: Path, *, root: Path = ROOT) -> list[Path]:
    """Build every workspace member to a wheel in ``dist_dir`` and return the wheels."""
    _run(
        ["uv", "build", "--all-packages", "--wheel", "-o", str(dist_dir), "--project", str(root)],
        what="build",
    )
    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        raise SmokeError(f"build: no wheels were produced in {dist_dir}")
    return wheels


def wheels_with_namespace_init(wheels: Sequence[Path]) -> list[str]:
    """Return the names of any wheels that ship a ``qmf/__init__.py`` (should be none).

    The distributions are PEP 420 namespace submodules; a ``qmf/__init__.py`` in any
    wheel would collide the ``qmf`` namespace across packages.
    """
    offenders: list[str] = []
    for wheel in wheels:
        with zipfile.ZipFile(wheel) as archive:
            names = set(archive.namelist())
        if "qmf/__init__.py" in names:
            offenders.append(wheel.name)
    return offenders


def _workspace_constraints(members: Sequence[Member], path: Path) -> Path:
    """Write a constraints file pinning every workspace member to its built version.

    Unpinned workspace deps (e.g. ``qmb`` → ``qml``) would otherwise resolve a
    same-named PyPI distribution over the local wheel; pinning keeps isolation
    inside the built tree while third-party runtime deps still use the index.
    """
    lines = [f"{member.name}=={member.version}\n" for member in members]
    path.write_text("".join(lines), encoding="utf-8")
    return path


def check_member_in_isolation(
    member: Member,
    dist_dir: Path,
    work_dir: Path,
    constraints: Path,
) -> None:
    """Install ``member`` alone from ``dist_dir`` and import its module; raise on failure."""
    if not member.module_name:
        raise SmokeError(f"{member.name}: no build-backend module-name declared")
    venv = work_dir / f"venv-{member.name}"
    _run(["uv", "venv", "--python", _PY_VERSION, str(venv)], what=f"{member.name} venv")
    _run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(_venv_python(venv)),
            "--find-links",
            str(dist_dir),
            "--constraint",
            str(constraints),
            f"{member.name}=={member.version}",
        ],
        what=f"{member.name} isolated install",
    )
    # Import the member's own module. An undeclared sibling import is absent from this
    # env and raises ModuleNotFoundError here — the failure the smoke exists to catch.
    _run(
        [str(_venv_python(venv)), "-c", f"import {member.module_name}"],
        what=f"{member.name} import {member.module_name}",
    )


def run_smoke(root: Path = ROOT) -> None:
    """Build, verify namespace hygiene, and isolated-install-and-import every member."""
    members = list(workspace_meta.iter_members(root))
    if not members:
        raise SmokeError(
            "no workspace members found under packages/, extensions/, or application roots"
        )
    with tempfile.TemporaryDirectory(prefix="qmf-isolated-build-") as tmp:
        work_dir = Path(tmp)
        dist_dir = work_dir / "dist"
        dist_dir.mkdir()
        wheels = build_wheels(dist_dir, root=root)
        offenders = wheels_with_namespace_init(wheels)
        if offenders:
            raise SmokeError(
                "namespace hygiene: these wheels ship qmf/__init__.py (must be PEP 420 "
                f"namespace submodules): {', '.join(offenders)}"
            )
        constraints = _workspace_constraints(members, work_dir / "constraints.txt")
        for member in members:
            check_member_in_isolation(member, dist_dir, work_dir, constraints)


def main(root: Path = ROOT) -> int:
    try:
        run_smoke(root)
    except SmokeError as exc:
        sys.stdout.write(f"isolated-build: FAIL - {exc}\n")
        return 1
    sys.stdout.write(
        "isolated-build: clean (every member installs alone from its declared deps and "
        "imports; no wheel ships qmf/__init__.py).\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
