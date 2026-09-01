"""Regression tests for the isolated-build smoke's inspectable pieces (M9).

The full build-install-import smoke needs real ``uv`` builds and is exercised by the
``poe check-integration`` gate itself. This fast unit test pins the piece that does not
need a build: the wheel namespace-hygiene detector, which proves an accidental
``qmf/__init__.py`` in a *distribution* would be caught (M9 (a) at the distribution
level, complementing the source-tree check in ``test_workspace_structure.py``).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from workspace_meta import Member

import isolated_build_check as ibc


def _make_wheel(path: Path, names: list[str]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(name, "x = 1\n")
    return path


def _member(name: str = "qmf-core", version: str = "0.1.0") -> Member:
    return Member(
        name=name,
        directory=Path(name),
        module_name=name.replace("-", "."),
        dependencies=(),
        is_extension=False,
        version=version,
    )


def _try_symlink(link: Path, target: Path) -> None:
    """Create a symlink or skip where the platform forbids it (Windows without privilege)."""
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not permitted on this platform")


def test_namespace_init_leak_is_detected(tmp_path: Path) -> None:
    leaky = _make_wheel(
        tmp_path / "qmf_bad-0.1.0-py3-none-any.whl",
        ["qmf/__init__.py", "qmf/bad/__init__.py"],
    )
    assert ibc.wheels_with_namespace_init([leaky]) == [leaky.name]


def test_clean_namespace_submodule_wheel_passes(tmp_path: Path) -> None:
    clean = _make_wheel(
        tmp_path / "qmf_core-0.1.0-py3-none-any.whl",
        ["qmf/core/__init__.py", "qmf/core/exact.py", "qmf_core-0.1.0.dist-info/METADATA"],
    )
    assert ibc.wheels_with_namespace_init([clean]) == []


def test_workspace_constraints_writes_pins(tmp_path: Path) -> None:
    members = [_member("qmf-core", "0.1.0"), _member("qmb", "0.2.0")]
    path = ibc._workspace_constraints(members, tmp_path / "constraints.txt")
    assert path.read_text(encoding="utf-8") == "qmf-core==0.1.0\nqmb==0.2.0\n"


def test_workspace_constraints_refuses_symlink(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("do-not-overwrite\n", encoding="utf-8")
    link = tmp_path / "constraints.txt"
    _try_symlink(link, outside)
    with pytest.raises(ibc.SmokeError, match="symlink"):
        ibc._workspace_constraints([_member()], link)
    assert outside.read_text(encoding="utf-8") == "do-not-overwrite\n"


def test_workspace_constraints_refuses_existing_path(tmp_path: Path) -> None:
    path = tmp_path / "constraints.txt"
    path.write_text("stale\n", encoding="utf-8")
    with pytest.raises(ibc.SmokeError, match="exclusive no-follow create failed"):
        ibc._workspace_constraints([_member()], path)
    assert path.read_text(encoding="utf-8") == "stale\n"
