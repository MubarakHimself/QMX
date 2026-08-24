"""Executable tests for the coverage-floor enforcer (M1; AR-20).

Pins both floors the enforcer adds on top of the aggregate ``--cov-fail-under=80``:
the per-package 80% floor (so one package cannot hide behind another's fully-covered
scaffold) and the 100%-branch contract-module rule for ``qmf/core/exact.py`` and
``qmf/core/chrono.py``. Also exercises the fail-closed file-loading entry point and
asserts the enforcer passes on the workspace's real ``coverage.json`` when present.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import coverage_report as cov
import pytest

FileEntry = dict[str, dict[str, int]]
Report = dict[str, dict[str, FileEntry]]


def _file(
    covered_lines: int, num_statements: int, covered_branches: int, num_branches: int
) -> FileEntry:
    return {
        "summary": {
            "covered_lines": covered_lines,
            "num_statements": num_statements,
            "covered_branches": covered_branches,
            "num_branches": num_branches,
        }
    }


def _report(files: dict[str, FileEntry]) -> Report:
    return {"files": files}


def _clean_report() -> Report:
    return _report(
        {
            "packages/qmf-core/src/qmf/core/refusal.py": _file(90, 100, 40, 40),
            "packages/qmf-core/src/qmf/core/exact.py": _file(10, 10, 8, 8),
            "packages/qmf-core/src/qmf/core/chrono.py": _file(10, 10, 8, 8),
            "packages/qmf-data/src/qmf/data/__init__.py": _file(5, 5, 0, 0),
            "extensions/qmf-calendar-forex/src/qmf/calendar_forex/_bench.py": _file(20, 20, 2, 2),
        }
    )


# --- a clean report passes --------------------------------------------------


def test_clean_report_has_no_violations() -> None:
    assert cov.evaluate(_clean_report()) == []


# --- per-package floor ------------------------------------------------------


def test_package_below_floor_is_flagged() -> None:
    report = _clean_report()
    # Drop qmf-data well under 80% combined line+branch.
    report["files"]["packages/qmf-data/src/qmf/data/big.py"] = _file(10, 100, 0, 0)
    violations = cov.evaluate(report)
    assert any("qmf-data" in v and "per-package floor" in v for v in violations)


def test_package_floor_uses_combined_line_and_branch() -> None:
    # 80/100 lines but 0/100 branches => 80/200 = 40% combined, below the floor.
    report = _report({"packages/qmf-venue/src/qmf/venue/m.py": _file(80, 100, 0, 100)})
    violations = cov.evaluate(report)
    assert any("qmf-venue" in v for v in violations)


def test_package_exactly_at_floor_passes() -> None:
    report = _report({"packages/qmf-risk/src/qmf/risk/m.py": _file(80, 100, 0, 0)})
    # exact.py/chrono.py absent -> those violations appear, but no qmf-risk floor breach.
    violations = cov.evaluate(report)
    assert not any("qmf-risk" in v for v in violations)


def test_application_root_qml_is_its_own_package() -> None:
    report = _report(
        {
            "qml/src/qml/__init__.py": _file(7, 10, 0, 0),
            "packages/qmf-core/src/qmf/core/exact.py": _file(10, 10, 8, 8),
            "packages/qmf-core/src/qmf/core/chrono.py": _file(10, 10, 8, 8),
        }
    )
    violations = cov.evaluate(report)
    assert any("qml" in v and "per-package floor" in v for v in violations)


def test_application_root_qmb_is_its_own_package() -> None:
    report = _report(
        {
            "qmb/src/qmb/__init__.py": _file(7, 10, 0, 0),
            "packages/qmf-core/src/qmf/core/exact.py": _file(10, 10, 8, 8),
            "packages/qmf-core/src/qmf/core/chrono.py": _file(10, 10, 8, 8),
        }
    )
    violations = cov.evaluate(report)
    assert any("qmb" in v and "per-package floor" in v for v in violations)


# --- contract-module full-branch rule ---------------------------------------


def test_exact_with_uncovered_branch_is_flagged() -> None:
    report = _clean_report()
    report["files"]["packages/qmf-core/src/qmf/core/exact.py"] = _file(10, 10, 6, 8)
    violations = cov.evaluate(report)
    assert any("qmf/core/exact.py" in v and "branches covered" in v for v in violations)


def test_chrono_with_uncovered_branch_is_flagged() -> None:
    report = _clean_report()
    report["files"]["packages/qmf-core/src/qmf/core/chrono.py"] = _file(10, 10, 7, 8)
    violations = cov.evaluate(report)
    assert any("qmf/core/chrono.py" in v for v in violations)


def test_missing_contract_module_fails_closed() -> None:
    # A report that never measured chrono.py must fail rather than pass by omission.
    report = _report({"packages/qmf-core/src/qmf/core/exact.py": _file(10, 10, 8, 8)})
    violations = cov.evaluate(report)
    assert any("qmf/core/chrono.py" in v and "not measured" in v for v in violations)


def test_windows_backslash_paths_are_matched() -> None:
    report = _report(
        {
            "packages\\qmf-core\\src\\qmf\\core\\exact.py": _file(10, 10, 8, 8),
            "packages\\qmf-core\\src\\qmf\\core\\chrono.py": _file(10, 10, 4, 8),
        }
    )
    violations = cov.evaluate(report)
    assert any("qmf/core/chrono.py" in v for v in violations)
    assert not any("exact.py" in v for v in violations)


# --- the file-loading entry point -------------------------------------------


def test_main_passes_on_clean_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report_path = tmp_path / "coverage.json"
    report_path.write_text(json.dumps(_clean_report()), encoding="utf-8")
    assert cov.main(report_path) == 0
    assert "clean" in capsys.readouterr().out


def test_main_fails_on_breached_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = _clean_report()
    report["files"]["packages/qmf-core/src/qmf/core/exact.py"] = _file(10, 10, 1, 8)
    report_path = tmp_path / "coverage.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    assert cov.main(report_path) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "exact.py" in out


def test_main_fails_closed_when_report_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cov.main(tmp_path / "nope.json") == 1
    assert "no coverage report" in capsys.readouterr().out


def test_main_fails_closed_on_a_non_regular_report_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A directory where the report should be is "no report" as truly as a missing file.
    directory = tmp_path / "coverage.json"
    directory.mkdir()
    assert cov.main(directory) == 1
    assert "no coverage report" in capsys.readouterr().out


def test_main_fails_closed_on_malformed_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report_path = tmp_path / "coverage.json"
    report_path.write_text("{not json", encoding="utf-8")
    assert cov.main(report_path) == 1
    assert "FAIL" in capsys.readouterr().out


def test_real_workspace_report_passes_when_present() -> None:
    # If a prior `poe test` produced coverage.json, the enforcer must accept it.
    if not cov.REPORT_PATH.is_file():
        pytest.skip("coverage.json not present (run `poe test` first)")
    report: Any = json.loads(cov.REPORT_PATH.read_text(encoding="utf-8"))
    assert cov.evaluate(report) == []
