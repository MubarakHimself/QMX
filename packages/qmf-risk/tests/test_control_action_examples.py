"""The Story 10.8 CT-30 reference-usage example must stay executable (L27)."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "control_action_usage.py"
_CORE_SRC = _PKG_ROOT.parent / "qmf-core" / "src"


def test_reference_usage_example_runs_clean() -> None:
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(_PKG_ROOT / "src"), str(_CORE_SRC)]),
    }
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "exit-preservation: close_all block refused (policy rejection)" in completed.stdout
    assert "no blanket command-pipe block kind may be minted" in completed.stdout
    assert "kill_switch class / kill_line class: kill-switch / kill-line" in completed.stdout
    assert "close reasons distinct: kill_line_flat != protection_forced_flat" in completed.stdout
    assert "flatten authority: operator ok; adapter_self refused" in completed.stdout
    assert "scope resolution: netting-indistinguishable refused (never widened)" in completed.stdout
    assert "journal-before-dispatch: storage failure blocks; success proceeds" in completed.stdout
    assert "standing intent: unknown verdict holds flatten open (held-alarm)" in completed.stdout
    assert "same-tick compose: emit=['flatten', 'suspend_new']; suppressed=0" in completed.stdout


def test_example_uses_no_bare_assert() -> None:
    tree = ast.parse(_EXAMPLE.read_text(encoding="utf-8"))
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
