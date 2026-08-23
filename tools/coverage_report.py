"""Tier-1 coverage-floor enforcer (AR-20; enforcing the CT-01/CT-02 branch law).

``poe test`` runs one aggregate ``--cov=qmf --cov-branch --cov-fail-under=80`` over
all workspace packages. That single number is necessary but not sufficient: six
near-empty scaffold packages sit at 100% and can float the aggregate above 80% even
while ``qmf-core`` itself regresses, and the aggregate says nothing about *branch*
coverage on the two contract modules the spine requires to be exhaustively tested —
``qmf/core/exact.py`` (CT-01) and ``qmf/core/chrono.py`` (CT-02).

This script reads the machine-readable ``coverage.json`` that ``poe test`` writes and
mechanically enforces the two story acceptance criteria the aggregate cannot:

* **Per-package floor (AR-20).** Every workspace package's own combined
  line+branch coverage must be at least 80%. A package is derived from each measured
  file's ``packages/<pkg>/``, ``extensions/<pkg>/``, or application-root (``qml/``,
  ``qmb/``) path, so one package cratering can never hide behind another's fully-covered
  scaffold.
* **Full-branch contract modules.** ``qmf/core/exact.py`` and ``qmf/core/chrono.py``
  must have **100% branch** coverage — every decision exit taken. These modules must
  be present in the report; a contract module that was never measured fails the gate
  rather than passing by omission (fail-closed).

Wired into ``poe check`` right after ``test`` (which produces ``coverage.json``). A
single violation exits nonzero and fails the gate. Stdlib only; the SSSF root gate
(``adws``) is untouched. Run via ``python tools/coverage_report.py`` or ``poe
cov-report``.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / "coverage.json"

# Every workspace package's own coverage must clear this floor (AR-20).
PACKAGE_MIN_PERCENT = 80.0

# The CT-01/CT-02 contract modules that must be exhaustively branch-covered. Matched
# by path suffix so the check is independent of the absolute/relative form coverage
# happened to record.
FULL_BRANCH_MODULES: tuple[str, ...] = (
    "qmf/core/exact.py",
    "qmf/core/chrono.py",
)

# Pull the package name out of a measured file's path: packages/<pkg>/...,
# extensions/<pkg>/..., or an application root (qml/, qmb/).
_PACKAGE_RE = re.compile(r"(?:packages|extensions)/([^/]+)/|(qml|qmb)/")


def _norm(path: str) -> str:
    """A measured file path with forward slashes, for stable matching on any OS."""
    return path.replace("\\", "/")


def _package_of(path: str) -> str | None:
    """The workspace package a measured file belongs to, or ``None`` if it is not a
    workspace-package source file."""
    match = _PACKAGE_RE.search(_norm(path))
    if match is None:
        return None
    return match.group(1) or match.group(2)


def _as_mapping(value: object) -> Mapping[str, object]:
    """Narrow an arbitrary JSON value to a string-keyed mapping (empty if it is not).

    The parsed ``coverage.json`` is untyped ``object`` at every level; this is the one
    place the shape is checked, so the checks below read concrete ``object`` values
    instead of ``Unknown``.
    """
    return cast("Mapping[str, object]", value) if isinstance(value, Mapping) else {}


def evaluate(report: Mapping[str, object]) -> list[str]:
    """Return the list of coverage-floor violations in ``report`` (empty when clean).

    ``report`` is a parsed ``coverage.json`` document (``coverage[.py] json`` /
    ``pytest --cov-report=json`` schema). Two independent checks run over it — the
    per-package 80% floor and the 100%-branch contract-module rule — and every
    violation is collected so one run reports them all.
    """
    files = _as_mapping(report.get("files"))
    violations: list[str] = []
    violations.extend(_package_violations(files))
    violations.extend(_full_branch_violations(files))
    return violations


def _package_violations(files: Mapping[str, object]) -> list[str]:
    """Aggregate combined line+branch coverage per package and flag any below the
    floor."""
    # package -> [covered_units, total_units]
    tallies: dict[str, list[int]] = {}
    for path, info in files.items():
        package = _package_of(path)
        if package is None:
            continue
        summary = _as_mapping(_as_mapping(info).get("summary"))
        covered = _int(summary.get("covered_lines")) + _int(summary.get("covered_branches"))
        total = _int(summary.get("num_statements")) + _int(summary.get("num_branches"))
        tally = tallies.setdefault(package, [0, 0])
        tally[0] += covered
        tally[1] += total

    violations: list[str] = []
    for package, (covered, total) in sorted(tallies.items()):
        percent = 100.0 * covered / total if total else 100.0
        if percent + 1e-9 < PACKAGE_MIN_PERCENT:
            violations.append(
                f"{package}: {percent:.2f}% coverage is below the {PACKAGE_MIN_PERCENT:.0f}% "
                f"per-package floor (AR-20) [{covered}/{total} line+branch units]"
            )
    return violations


def _full_branch_violations(files: Mapping[str, object]) -> list[str]:
    """Require each contract module to be present and 100% branch-covered."""
    # suffix -> (num_branches, covered_branches) for the modules we found.
    found: dict[str, tuple[int, int]] = {}
    for path, info in files.items():
        norm = _norm(path)
        for suffix in FULL_BRANCH_MODULES:
            if norm.endswith(suffix):
                summary = _as_mapping(_as_mapping(info).get("summary"))
                found[suffix] = (
                    _int(summary.get("num_branches")),
                    _int(summary.get("covered_branches")),
                )

    violations: list[str] = []
    for suffix in FULL_BRANCH_MODULES:
        if suffix not in found:
            violations.append(
                f"{suffix}: contract module was not measured; 100% branch coverage cannot be "
                f"confirmed (fail-closed)"
            )
            continue
        num_branches, covered_branches = found[suffix]
        if covered_branches < num_branches:
            missing = num_branches - covered_branches
            violations.append(
                f"{suffix}: {covered_branches}/{num_branches} branches covered — {missing} "
                f"uncovered; CT-01/CT-02 contract modules require 100% branch coverage"
            )
    return violations


def _int(value: object) -> int:
    """A defensive int coercion for a summary field (missing/odd fields read as 0)."""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def main(report_path: Path = REPORT_PATH) -> int:
    """Load ``coverage.json`` and enforce the floors, exiting nonzero on any breach."""
    # "No usable report" is decided once, before the read, and covers every shape of it:
    # absent, a directory, a dangling symlink, a device. This replaces a
    # `except FileNotFoundError` further down that only ever saw the absent case — and
    # a FIFO, which that branch could not have caught, would have hung the gate on a
    # read that never returned. The check sits immediately before the read it guards.
    if not report_path.is_file():
        sys.stdout.write(
            f"cov-report: FAIL - no coverage report at {report_path}; run `poe test` first "
            f"so the JSON report is produced.\n"
        )
        return 1
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        sys.stdout.write(f"cov-report: FAIL - could not read {report_path}: {exc}\n")
        return 1

    violations = evaluate(report)
    if violations:
        sys.stdout.write("cov-report: FAIL - coverage floors breached:\n")
        for violation in violations:
            sys.stdout.write(f"  {violation}\n")
        return 1
    sys.stdout.write(
        f"cov-report: clean (per-package >= {PACKAGE_MIN_PERCENT:.0f}%; "
        f"{', '.join(FULL_BRANCH_MODULES)} at 100% branch).\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
