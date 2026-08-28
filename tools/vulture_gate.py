"""Vulture count-vs-baseline gate for the QA battery (card FC-34; OR-10b).

Runs Vulture over the shipped workspace and fails the build only if the number of
findings RISES above a committed baseline — the ratchet the operator ruled for the
dead-code family: never worse than today, ratchet DOWN as findings clear, never up.

Fail-closed, the same discipline as .github/workflows/skylos.yml: Vulture exits 0 when
it finds nothing and 3 when it finds dead code; ANY other exit code (1 = invalid input,
2 = CLI misuse, or a missing binary) means the scan itself broke, and a broken scan must
never read as clean — it exits nonzero here rather than reporting "0 findings".

Usage (the battery workflow provisions a pinned Vulture, then drives this script):

    uv run --with vulture==2.14 python tools/vulture_gate.py \\
        --baseline qa/_trace/battery/vulture/gate-baseline-min80.txt \\
        --min-confidence 80 -- packages extensions qml qmb tools

The baseline file's ``#`` comment and blank lines are ignored; only lines carrying an
``(NN% confidence)`` marker are counted, so the file can document its own provenance.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import cast

# A Vulture finding line: ``path:line: message (NN% confidence)``. Matching on the
# confidence marker keeps counting robust to path separators and message wording.
_FINDING = re.compile(r"\(\d+% confidence\)\s*$")

# Vulture's contract: 0 = nothing found, 3 = dead code found. Everything else is a
# broken run, never a clean one.
_CLEAN = 0
_FOUND = 3


def _count_findings(lines: list[str]) -> list[str]:
    return [line.rstrip() for line in lines if _FINDING.search(line)]


def _normalize(finding: str) -> str:
    # Drop the volatile ``:<line>:`` and unify path separators so a moved finding is
    # not mistaken for a new one when listing what changed (the verdict is by count).
    without_line = re.sub(r":\d+:", ":", finding.strip())
    return without_line.replace("\\", "/")


def _run_vulture(min_confidence: int, paths: list[str]) -> subprocess.CompletedProcess[str]:
    argv = [sys.executable, "-m", "vulture", *paths, "--min-confidence", str(min_confidence)]
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Vulture count-vs-baseline ratchet gate.")
    parser.add_argument("--baseline", required=True, help="committed baseline file to count")
    parser.add_argument("--min-confidence", type=int, default=80, help="vulture --min-confidence")
    parser.add_argument("paths", nargs="+", help="paths to scan")
    args = parser.parse_args(argv)

    baseline_path = Path(cast("str", args.baseline))
    min_confidence = cast("int", args.min_confidence)
    paths = cast("list[str]", args.paths)

    if not baseline_path.is_file():
        print(f"::error::vulture gate: baseline file not found at {baseline_path}", file=sys.stderr)
        return 2
    # Containment: the baseline is repo data named by the workflow's own pinned
    # argv, never external input; refuse a path resolving outside the working
    # tree so the argument cannot be turned into a traversal.
    resolved = baseline_path.resolve()
    if not resolved.is_relative_to(Path.cwd().resolve()):
        print(
            f"::error::vulture gate: baseline must live inside the repo, got {resolved}",
            file=sys.stderr,
        )
        return 2
    baseline = (
        # The path is contained above (resolved inside the working tree) and comes
        # from the workflow's own pinned argv, never user input.
        _count_findings(
            resolved.read_text(encoding="utf-8").splitlines()  # skylos: ignore[SKY-D215]
        )
    )
    baseline_count = len(baseline)

    try:
        result = _run_vulture(min_confidence, paths)
    except OSError as error:
        print(f"::error::vulture gate: could not run vulture at all ({error})", file=sys.stderr)
        return 2

    if result.returncode not in (_CLEAN, _FOUND):
        # A broken scan (bad input, CLI misuse) — refuse to treat it as clean.
        print(
            f"::error::vulture gate: vulture exited {result.returncode}; "
            f"refusing to treat that as a clean result",
            file=sys.stderr,
        )
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        return 2

    current = _count_findings(result.stdout.splitlines())
    current_count = len(current)

    print(
        f"vulture gate: {current_count} finding(s) at --min-confidence {min_confidence}; "
        f"baseline {baseline_count} ({baseline_path})"
    )

    if current_count > baseline_count:
        known = {_normalize(line) for line in baseline}
        added = [line for line in current if _normalize(line) not in known]
        print(
            f"::error::vulture gate: {current_count} findings exceed the committed "
            f"baseline of {baseline_count} — the dead-code floor may only ratchet DOWN",
            file=sys.stderr,
        )
        for line in added or current:
            print(f"  + {line}", file=sys.stderr)
        return 1

    if current_count < baseline_count:
        print(
            f"vulture gate: {baseline_count - current_count} finding(s) below baseline — "
            f"ratchet {baseline_path} down to {current_count} to lock in the improvement."
        )
    print("vulture gate: OK (not worse than baseline)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
