"""Executable tests for the secret-scan gate (M7; AR-24).

The scanner is exercised two ways: over a ``must_flag`` / ``must_not_flag`` fixture
corpus (every ``must_flag`` file must raise at least one finding; every
``must_not_flag`` file must raise none), and through targeted unit cases pinning each
detection pattern, the whole-tree file discovery with its ``SKIP_DIRS`` discipline,
and the fail-closed gate entry point. The live gate is also asserted clean on the real
workspace.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import secret_scan as scanner

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "secret"
MUST_FLAG = sorted(p for p in (FIXTURES / "must_flag").glob("*") if p.is_file())
MUST_NOT_FLAG = sorted(p for p in (FIXTURES / "must_not_flag").glob("*") if p.is_file())


# --- the fixture corpus -----------------------------------------------------


def test_fixture_corpus_is_populated() -> None:
    assert MUST_FLAG, "expected must-flag fixtures"
    assert MUST_NOT_FLAG, "expected must-not-flag fixtures"


@pytest.mark.parametrize("path", MUST_FLAG, ids=lambda p: p.name)
def test_must_flag_fixtures_are_flagged(path: Path) -> None:
    findings = scanner.scan_file(path)
    assert findings, f"{path.name} must be flagged but was clean"


@pytest.mark.parametrize("path", MUST_NOT_FLAG, ids=lambda p: p.name)
def test_must_not_flag_fixtures_are_clean(path: Path) -> None:
    findings = scanner.scan_file(path)
    assert findings == [], f"{path.name} must be clean but flagged {[f.render() for f in findings]}"


# --- helpers ----------------------------------------------------------------


def _rules(text: str) -> list[str]:
    return [f.rule for f in scanner.scan_text(text, "<case>")]


# --- the detection patterns -------------------------------------------------


def test_private_key_block_is_flagged() -> None:
    assert _rules("-----BEGIN RSA PRIVATE KEY-----") == ["private-key-block"]
    assert _rules("-----BEGIN PRIVATE KEY-----") == ["private-key-block"]


def test_aws_access_key_id_is_flagged() -> None:
    assert _rules('key = "AKIAIOSFODNN7EXAMPLE"') == ["aws-access-key-id"]


def test_google_api_key_is_flagged() -> None:
    assert _rules("k: AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ0123456") == ["google-api-key"]


def test_slack_token_is_flagged() -> None:
    assert _rules("SLACK=xoxb-2088888888-abcdefGHIJKL") == ["slack-token"]


def test_quoted_credential_assignment_is_flagged() -> None:
    assert _rules('password = "hunter2-p@ssw0rd"') == ["quoted-credential-assignment"]
    assert _rules('client_secret: "s3cr3t-Value-9f2a1b"') == ["quoted-credential-assignment"]
    assert _rules('api_key = "abcdefgh12345678"') == ["quoted-credential-assignment"]


# --- deliberate non-matches (high precision) --------------------------------


def test_unquoted_assignment_is_not_flagged() -> None:
    assert _rules("API_KEY=your-key-here") == []
    assert _rules("password: changeme") == []


def test_short_quoted_value_is_not_flagged() -> None:
    assert _rules('token = "abc"') == []


def test_prose_mention_is_not_flagged() -> None:
    assert _rules("Rotate the password and each API key through the secret store.") == []


def test_secret_reference_by_path_is_not_flagged() -> None:
    assert _rules('SecretRef.try_create(store="vault", path="prod/db/password")') == []


# --- Finding rendering ------------------------------------------------------


def test_finding_render_is_stable() -> None:
    findings = scanner.scan_text('password = "hunter2-p@ssw0rd"', "sample.env")
    assert len(findings) == 1
    assert findings[0].render() == "sample.env:1: quoted-credential-assignment"


def test_findings_are_line_numbered() -> None:
    text = 'clean line\nAWS = "AKIAIOSFODNN7EXAMPLE"\n'
    findings = scanner.scan_text(text, "s.py")
    assert [f.line for f in findings] == [2]


# --- whole-tree file discovery and SKIP_DIRS --------------------------------


def test_iter_scanned_files_includes_root_and_widened_roots(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("root file\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("on: push\n", encoding="utf-8")
    (tmp_path / "queue").mkdir()
    (tmp_path / "queue" / "001-brief.md").write_text("brief\n", encoding="utf-8")
    (tmp_path / "packages" / "qmf-demo" / "src").mkdir(parents=True)
    (tmp_path / "packages" / "qmf-demo" / "src" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    found = {p.name for p in scanner.iter_scanned_files(tmp_path)}
    assert found == {"README.md", "ci.yml", "001-brief.md", "mod.py"}


def test_iter_scanned_files_prunes_skip_dirs_and_fixtures(tmp_path: Path) -> None:
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "real.py").write_text("x = 1\n", encoding="utf-8")
    # A fixtures corpus with a planted secret must be pruned (not descended into).
    fixtures = tmp_path / "tools" / "tests" / "fixtures"
    fixtures.mkdir(parents=True)
    (fixtures / "planted.py").write_text('key = "AKIAIOSFODNN7EXAMPLE"\n', encoding="utf-8")
    # A virtualenv is machine noise, pruned too.
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "leak.py").write_text('key = "AKIAIOSFODNN7EXAMPLE"\n', encoding="utf-8")
    found = {p.name for p in scanner.iter_scanned_files(tmp_path)}
    assert found == {"real.py"}


def test_non_text_suffixes_are_skipped(tmp_path: Path) -> None:
    (tmp_path / "blob.bin").write_text("AKIAIOSFODNN7EXAMPLE\n", encoding="utf-8")
    assert list(scanner.iter_scanned_files(tmp_path)) == []


def test_scan_file_handles_unreadable_path(tmp_path: Path) -> None:
    assert scanner.scan_file(tmp_path / "missing.py") == []


# --- the gate entry point ---------------------------------------------------


def test_scan_workspace_flags_a_planted_root_secret(tmp_path: Path) -> None:
    (tmp_path / "config.env").write_text(
        'client_secret = "s3cr3t-Value-9f2a1b"\n', encoding="utf-8"
    )
    findings = scanner.scan_workspace(tmp_path)
    assert len(findings) == 1
    assert findings[0].rule == "quoted-credential-assignment"


def test_main_is_clean_on_the_real_workspace(capsys: pytest.CaptureFixture[str]) -> None:
    assert scanner.main() == 0
    assert "clean" in capsys.readouterr().out


def test_main_fails_closed_on_a_violation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "deploy.yml").write_text(
        "env:\n  AWS: AKIAIOSFODNN7EXAMPLE\n", encoding="utf-8"
    )
    assert scanner.main(tmp_path) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "aws-access-key-id" in out
