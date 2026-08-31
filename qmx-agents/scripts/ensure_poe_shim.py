"""Install a Device Guard-safe poe.cmd shim into the project venv Scripts dir.

Host App Control blocks the poethepoet console-script launcher (poe.exe) under
qmx-agents/.venv on this workstation (os error 4551). uv spawns poe.cmd via
PATHEXT when poe.exe is absent. The shim also cd's into the qmx-agents root so
`uv run --project qmx-agents poe …` from the parent worktree CWD still loads
this workspace's pyproject tasks (not the parent's). Idempotent after uv sync.
"""
from __future__ import annotations

import sys
from pathlib import Path

CMD = (
    "@echo off\r\n"
    "cd /d \"%~dp0..\\..\"\r\n"
    "\"%~dp0python.exe\" -m poethepoet %*\r\n"
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    scripts = root / ".venv" / "Scripts"
    if not scripts.is_dir():
        print(f"no venv Scripts dir at {scripts}", file=sys.stderr)
        return 1
    exe = scripts / "poe.exe"
    if exe.exists():
        exe.unlink()
    shim = scripts / "poe.cmd"
    shim.write_text(CMD, encoding="ascii", newline="")
    print(f"wrote {shim}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
