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

import isolated_build_check as ibc


def _make_wheel(path: Path, names: list[str]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(name, "x = 1\n")
    return path


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
