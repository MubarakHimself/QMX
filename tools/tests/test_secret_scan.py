"""Executable tests for the secret-scan gate (M7; AR-24).

The scanner is exercised two ways: over a ``must_flag`` / ``must_not_flag`` fixture
corpus (every ``must_flag`` file must raise at least one finding; every
``must_not_flag`` file must raise none), and through targeted unit cases pinning each
detection pattern, the whole-tree file discovery with its ``SKIP_DIRS`` discipline,
and the fail-closed gate entry point. The live gate is also asserted clean on the real
workspace.

**Why the must-flag corpus ships as templates.** A fixture that matches this gate's
patterns also matches every real-world secret scanner's — GitHub's Google-API-key
pattern is the same shape as ours, so any value our rule catches, theirs catches too,
and it raised an alert on exactly that fixture. "Defusing" the value is not possible
for that class of credential: anything narrow enough to stay invalid for GitHub is
also invalid for us, and the test stops testing anything.

So the credential *shapes* live here, in :data:`SECRET_SHAPES`, assembled from
fragments that no scanner's pattern spans, and the ``must_flag`` files carry a
``{{PLACEHOLDER}}`` where the credential goes. The test substitutes the shape into a
temporary copy and scans that. No tracked file in this repository ever carries a
live-shaped credential, the gate is still exercised against one, and
:func:`test_must_flag_templates_carry_no_live_shaped_credential` fails the build if
anyone ever pastes one back in.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import secret_scan as scanner

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "secret"
MUST_FLAG = sorted(p for p in (FIXTURES / "must_flag").glob("*") if p.is_file())
MUST_NOT_FLAG = sorted(p for p in (FIXTURES / "must_not_flag").glob("*") if p.is_file())

# The marker every assembled shape carries, so a finding printed by the gate during
# a test run is unmistakably a fixture and never a real credential.
_FAKE = "FAKE"

# The credential shapes, built from fragments no scanner's pattern spans: the
# concatenation exists only at run time, never as a matchable literal in a tracked
# file. Each is sized to the rule it exercises (see tools/secret_scan.py PATTERNS).
SECRET_SHAPES: dict[str, str] = {
    # AIza + exactly 35 characters of [0-9A-Za-z_-]
    "GOOGLE_API_KEY": "AIza" + "Sy" + _FAKE + "FIXTURE" + "0" * 22,
    # AKIA + exactly 16 characters of [0-9A-Z]
    "AWS_ACCESS_KEY_ID": "AKIA" + _FAKE + "FIXTURE00000",
    # xox[baprs]- + 10 or more characters of [0-9A-Za-z-]
    "SLACK_BOT_TOKEN": "xoxb" + "-" + _FAKE + "FIXTURE-000000",
    "PRIVATE_KEY_HEADER": "-----BEGIN RSA " + "PRIVATE KEY-----",
    "PRIVATE_KEY_FOOTER": "-----END RSA " + "PRIVATE KEY-----",
    # A quoted value of 8 or more non-quote, non-space characters. The quotes are
    # part of the shape so the tracked template holds an unquoted placeholder.
    "QUOTED_CREDENTIAL": '"' + _FAKE + "-fixture-credential" + '"',
}


def _render(path: Path, tmp_path: Path) -> Path:
    """Materialize a must-flag template into ``tmp_path`` with the real shapes in
    place of its ``{{PLACEHOLDER}}`` tokens."""
    text = path.read_text(encoding="utf-8")
    for name, shape in SECRET_SHAPES.items():
        text = text.replace("{{" + name + "}}", shape)
    target = tmp_path / path.name
    target.write_text(text, encoding="utf-8")
    return target


# --- the fixture corpus -----------------------------------------------------


def test_fixture_corpus_is_populated() -> None:
    assert MUST_FLAG, "expected must-flag fixtures"
    assert MUST_NOT_FLAG, "expected must-not-flag fixtures"


@pytest.mark.parametrize("path", MUST_FLAG, ids=lambda p: p.name)
def test_must_flag_fixtures_are_flagged(path: Path, tmp_path: Path) -> None:
    findings = scanner.scan_file(_render(path, tmp_path))
    assert findings, f"{path.name} must be flagged but was clean"


@pytest.mark.parametrize("path", MUST_FLAG, ids=lambda p: p.name)
def test_must_flag_templates_use_a_placeholder(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "{{" in text, f"{path.name} must hold a {{{{PLACEHOLDER}}}}, not a credential"


@pytest.mark.parametrize("path", MUST_FLAG, ids=lambda p: p.name)
def test_must_flag_templates_carry_no_live_shaped_credential(path: Path) -> None:
    # The whole point of the template corpus: the TRACKED file must be clean, so a
    # real-world scanner has nothing to alert on. Pasting a credential shape back
    # into a fixture fails here.
    findings = scanner.scan_file(path)
    assert findings == [], (
        f"{path.name} carries a live-shaped credential: {[f.render() for f in findings]}. "
        "Fixtures hold a {{PLACEHOLDER}}; the shape belongs in SECRET_SHAPES."
    )


@pytest.mark.parametrize("path", MUST_NOT_FLAG, ids=lambda p: p.name)
def test_must_not_flag_fixtures_are_clean(path: Path) -> None:
    findings = scanner.scan_file(path)
    assert findings == [], f"{path.name} must be clean but flagged {[f.render() for f in findings]}"


# --- helpers ----------------------------------------------------------------


def _rules(text: str) -> list[str]:
    return [f.rule for f in scanner.scan_text(text, "<case>")]


def _shape(name: str) -> str:
    return SECRET_SHAPES[name]


# --- the detection patterns -------------------------------------------------


def test_private_key_block_is_flagged() -> None:
    assert _rules(_shape("PRIVATE_KEY_HEADER")) == ["private-key-block"]
    assert _rules("-----BEGIN " + "PRIVATE KEY-----") == ["private-key-block"]


def test_aws_access_key_id_is_flagged() -> None:
    assert _rules(f'key = "{_shape("AWS_ACCESS_KEY_ID")}"') == ["aws-access-key-id"]


def test_google_api_key_is_flagged() -> None:
    assert _rules(f"k: {_shape('GOOGLE_API_KEY')}") == ["google-api-key"]


def test_slack_token_is_flagged() -> None:
    assert _rules(f"SLACK={_shape('SLACK_BOT_TOKEN')}") == ["slack-token"]


def test_quoted_credential_assignment_is_flagged() -> None:
    quoted = _shape("QUOTED_CREDENTIAL")
    assert _rules(f"password = {quoted}") == ["quoted-credential-assignment"]
    assert _rules(f"client_secret: {quoted}") == ["quoted-credential-assignment"]
    assert _rules(f"api_key = {quoted}") == ["quoted-credential-assignment"]


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
    findings = scanner.scan_text(f"password = {_shape('QUOTED_CREDENTIAL')}", "sample.env")
    assert len(findings) == 1
    assert findings[0].render() == "sample.env:1: quoted-credential-assignment"


def test_findings_are_line_numbered() -> None:
    text = f'clean line\nAWS = "{_shape("AWS_ACCESS_KEY_ID")}"\n'
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
    planted = f'key = "{_shape("AWS_ACCESS_KEY_ID")}"\n'
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "real.py").write_text("x = 1\n", encoding="utf-8")
    # A fixtures corpus with a planted secret must be pruned (not descended into).
    fixtures = tmp_path / "tools" / "tests" / "fixtures"
    fixtures.mkdir(parents=True)
    (fixtures / "planted.py").write_text(planted, encoding="utf-8")
    # A virtualenv is machine noise, pruned too.
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "leak.py").write_text(planted, encoding="utf-8")
    found = {p.name for p in scanner.iter_scanned_files(tmp_path)}
    assert found == {"real.py"}


def test_non_text_suffixes_are_skipped(tmp_path: Path) -> None:
    (tmp_path / "blob.bin").write_text(f"{_shape('AWS_ACCESS_KEY_ID')}\n", encoding="utf-8")
    assert list(scanner.iter_scanned_files(tmp_path)) == []


def test_scan_file_handles_unreadable_path(tmp_path: Path) -> None:
    assert scanner.scan_file(tmp_path / "missing.py") == []


# --- the gate entry point ---------------------------------------------------


def test_scan_workspace_flags_a_planted_root_secret(tmp_path: Path) -> None:
    (tmp_path / "config.env").write_text(
        f"client_secret = {_shape('QUOTED_CREDENTIAL')}\n", encoding="utf-8"
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
        f"env:\n  AWS: {_shape('AWS_ACCESS_KEY_ID')}\n", encoding="utf-8"
    )
    assert scanner.main(tmp_path) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "aws-access-key-id" in out
