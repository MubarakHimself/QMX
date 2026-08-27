"""Run the independent QA verification suites — one pytest run per epic directory.

The ``qa/tests`` tree holds 23 per-epic suites written and verified as separate
pytest invocations (duplicate test-module basenames and per-epic ``conftest``
modules make a single collection of the whole tree impossible by construction).
This runner is the ``uv run poe qa-verify`` gate: it runs each ``epic_NN``
directory as its own pytest session, in order, and fails if ANY suite fails —
including an empty collection, which must never read green. Extra command-line
arguments are passed through to every pytest invocation (e.g. ``-k`` filters).

The gate stays deliberately separate from the default ``poe test`` task.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent / "tests"
    epic_dirs = sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("epic_"))
    if not epic_dirs:
        print("qa-verify: no epic suites found under qa/tests — failing closed")
        return 1
    failed: list[str] = []
    for epic in epic_dirs:
        print(f"=== qa-verify: {epic.name} ===", flush=True)
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(epic), "-q", *sys.argv[1:]],
            check=False,
        )
        if proc.returncode != 0:
            failed.append(epic.name)
    if failed:
        print("qa-verify FAILED in: " + ", ".join(failed))
        return 1
    print(f"qa-verify: all {len(epic_dirs)} epic suites green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
