"""Executable tests for the mock-data scanner (the "no constructed data ships" gate).

The scanner is exercised two ways: over the shipped ``must_flag`` / ``must_not_flag``
fixture corpus (every ``must_flag`` file must raise at least one finding; every
``must_not_flag`` file must raise none), and through targeted unit cases that pin
each detection family, the whole-word identifier matching, the docstring exemption,
the line-scoped allow directive, the shipped-source file discovery, and the
fail-closed gate entry point.
"""

from __future__ import annotations

from pathlib import Path

import mock_data_scan as scanner
import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "mock_data"
MUST_FLAG = sorted((FIXTURES / "must_flag").glob("*.py"))
MUST_NOT_FLAG = sorted((FIXTURES / "must_not_flag").glob("*.py"))


# --- the fixture corpus -----------------------------------------------------


def test_fixture_corpus_is_populated() -> None:
    assert MUST_FLAG, "expected must-flag fixtures"
    assert MUST_NOT_FLAG, "expected must-not-flag fixtures"


@pytest.mark.parametrize("path", MUST_FLAG, ids=lambda p: p.stem)
def test_must_flag_fixtures_are_flagged(path: Path) -> None:
    findings = scanner.scan_file(path)
    assert findings, f"{path.name} must be flagged but was clean"


@pytest.mark.parametrize("path", MUST_NOT_FLAG, ids=lambda p: p.stem)
def test_must_not_flag_fixtures_are_clean(path: Path) -> None:
    findings = scanner.scan_file(path)
    assert findings == [], f"{path.name} must be clean but flagged {[f.render() for f in findings]}"


# --- helpers ----------------------------------------------------------------


def _rules(source: str) -> list[str]:
    return [f.rule for f in scanner.scan_source(source, "<case>")]


# --- mock identifiers -------------------------------------------------------


def test_mock_function_and_class_names_are_flagged() -> None:
    assert _rules("def mock_price():\n    pass") == [scanner.RULE_IDENTIFIER]
    assert _rules("class FakeVenue:\n    pass") == [scanner.RULE_IDENTIFIER]


def test_mock_assignment_target_is_flagged() -> None:
    assert _rules("price_stub = 5") == [scanner.RULE_IDENTIFIER]
    assert _rules("dummy: int = 5") == [scanner.RULE_IDENTIFIER]


def test_mock_tuple_target_is_flagged() -> None:
    assert _rules("real, fake_price = 1, 2") == [scanner.RULE_IDENTIFIER]


def test_mock_starred_target_is_flagged() -> None:
    assert _rules("head, *stub_tail = [1, 2, 3]") == [scanner.RULE_IDENTIFIER]


def test_mock_parameter_names_are_flagged() -> None:
    assert _rules("def build(mock_clock):\n    pass") == [scanner.RULE_IDENTIFIER]
    assert _rules("def build(*, fake_feed=None):\n    pass") == [scanner.RULE_IDENTIFIER]
    assert _rules("def build(*dummy_args):\n    pass") == [scanner.RULE_IDENTIFIER]


def test_lambda_parameters_are_checked() -> None:
    assert _rules("f = lambda stub_value: stub_value") == [scanner.RULE_IDENTIFIER]


def test_async_function_names_are_flagged() -> None:
    assert _rules("async def fake_fetch():\n    pass") == [scanner.RULE_IDENTIFIER]


def test_words_that_merely_open_with_a_banned_word_are_not_flagged() -> None:
    # The match is on whole words, not prefixes.
    assert _rules("class Faker:\n    pass") == []
    assert _rules("def stubborn_retry():\n    pass") == []
    assert _rules("mockingbird = 1") == []


def test_name_words_splits_snake_and_camel_case() -> None:
    assert scanner.name_words("mock_price_feed") == frozenset({"mock", "price", "feed"})
    assert scanner.name_words("FakeVenueAdapter") == frozenset({"fake", "venue", "adapter"})
    assert scanner.name_words("HTTPStub") == frozenset({"http", "stub"})
    assert scanner.name_words("_stub") == frozenset({"stub"})


def test_is_mock_name_is_word_scoped() -> None:
    assert scanner.is_mock_name("mock")
    assert scanner.is_mock_name("order_fake")
    assert not scanner.is_mock_name("faker")
    assert not scanner.is_mock_name("stubborn")


# --- test-double library imports --------------------------------------------


def test_mock_library_imports_are_flagged() -> None:
    assert _rules("import pytest") == [scanner.RULE_IMPORT]
    assert _rules("import unittest.mock") == [scanner.RULE_IMPORT]
    assert _rules("from unittest import mock") == [scanner.RULE_IMPORT]
    assert _rules("from freezegun import freeze_time") == [scanner.RULE_IMPORT]


def test_ordinary_imports_are_not_flagged() -> None:
    assert _rules("import datetime") == []
    assert _rules("from decimal import Decimal") == []
    assert _rules("import unittest") == []


def test_relative_import_is_ignored() -> None:
    # A relative import names no absolute module and cannot resolve to a library.
    assert _rules("from . import helpers") == []


def test_one_import_statement_reports_once() -> None:
    assert _rules("from unittest.mock import MagicMock, patch") == [scanner.RULE_IMPORT]


# --- placeholder literals ---------------------------------------------------


def test_placeholder_literals_are_flagged() -> None:
    assert _rules('X = "changeme"') == [scanner.RULE_PLACEHOLDER]
    assert _rules('X = "CHANGE_ME"') == [scanner.RULE_PLACEHOLDER]
    assert _rules('X = "xxx"') == [scanner.RULE_PLACEHOLDER]
    assert _rules('X = "TBD"') == [scanner.RULE_PLACEHOLDER]


def test_placeholder_opening_a_short_string_is_flagged() -> None:
    assert _rules('X = "placeholder: set in config"') == [scanner.RULE_PLACEHOLDER]


def test_lorem_ipsum_anywhere_is_flagged() -> None:
    assert _rules('X = "Header. Lorem ipsum dolor sit amet."') == [scanner.RULE_PLACEHOLDER]


def test_docstrings_are_exempt() -> None:
    # Documentation may NAME a placeholder; data may not BE one.
    assert _rules('"""changeme"""') == []
    assert _rules('def f():\n    """dummy"""') == []
    assert _rules('class C:\n    """placeholder"""') == []


def test_prose_that_merely_mentions_a_placeholder_is_not_flagged() -> None:
    long_prose = (
        "the placeholder value is replaced by the composition root before any "
        "order is ever submitted to a venue"
    )
    assert _rules(f'X = "{long_prose}"') == []


def test_ordinary_and_empty_literals_are_not_flagged() -> None:
    assert _rules('X = "EURUSD"') == []
    assert _rules('X = ""') == []
    assert _rules("X = '   '") == []


def test_is_placeholder_literal_boundaries() -> None:
    assert scanner.is_placeholder_literal("dummy")
    assert scanner.is_placeholder_literal("dummy-value")
    assert not scanner.is_placeholder_literal("dummies")
    assert not scanner.is_placeholder_literal("")


def test_normalize_literal_folds_separators() -> None:
    assert scanner.normalize_literal("  CHANGE_ME  ") == "change me"
    assert scanner.normalize_literal("Replace-Me") == "replace me"


# --- hardcoded sample data --------------------------------------------------


def test_sample_data_containers_are_flagged() -> None:
    assert _rules("SAMPLE_PRICES = [1, 2, 3]") == [scanner.RULE_SAMPLE_DATA]
    assert _rules('EXAMPLE_MARKET_DATA = {"a": 1}') == [scanner.RULE_SAMPLE_DATA]
    assert _rules("demo_candles = (1, 2)") == [scanner.RULE_SAMPLE_DATA]
    assert _rules("synthetic_rows: list[int] = [1]") == [scanner.RULE_SAMPLE_DATA]


def test_sample_name_without_a_container_is_not_flagged() -> None:
    assert _rules("SAMPLE_PRICES = build_prices()") == []


def test_empty_sample_container_is_not_flagged() -> None:
    # An empty collection is an identity value, not fabricated data.
    assert _rules("SAMPLE_PRICES: list[int] = []") == []
    assert _rules("EXAMPLE_DATA = {}") == []


def test_data_name_without_a_fabrication_word_is_not_flagged() -> None:
    assert _rules("PRICE_LADDER = [1, 2, 3]") == []


def test_is_populated_container_discriminates() -> None:
    import ast

    def value_of(source: str) -> ast.expr:
        statement = ast.parse(source).body[0]
        assert isinstance(statement, ast.Assign)
        return statement.value

    assert scanner.is_populated_container(value_of("x = [1]"))
    assert scanner.is_populated_container(value_of("x = {1: 2}"))
    assert not scanner.is_populated_container(value_of("x = []"))
    assert not scanner.is_populated_container(value_of("x = {}"))
    assert not scanner.is_populated_container(value_of("x = 1"))


# --- fabricated defaults ----------------------------------------------------


def test_fabricated_defaults_on_real_inputs_are_flagged() -> None:
    assert _rules('def q(symbol="EURUSD"):\n    pass') == [scanner.RULE_FABRICATED_DEFAULT]
    assert _rules("def q(price=100):\n    pass") == [scanner.RULE_FABRICATED_DEFAULT]
    assert _rules("def q(*, balance=10_000):\n    pass") == [scanner.RULE_FABRICATED_DEFAULT]
    assert _rules("def q(bars=(1, 2)):\n    pass") == [scanner.RULE_FABRICATED_DEFAULT]


def test_positional_only_parameter_defaults_are_checked() -> None:
    assert _rules("def q(price=9, /):\n    pass") == [scanner.RULE_FABRICATED_DEFAULT]


def test_neutral_defaults_are_not_flagged() -> None:
    assert _rules("def q(price=None):\n    pass") == []
    assert _rules("def q(price=0):\n    pass") == []
    assert _rules("def q(price=0.0):\n    pass") == []
    assert _rules('def q(symbol=""):\n    pass') == []
    assert _rules("def q(bars=()):\n    pass") == []
    assert _rules("def q(enabled=True):\n    pass") == []


def test_named_and_computed_defaults_are_not_flagged() -> None:
    assert _rules("def q(price=DEFAULT_PRICE):\n    pass") == []
    assert _rules("def q(payload=build_payload()):\n    pass") == []


def test_default_on_a_parameter_that_is_not_a_real_input_is_not_flagged() -> None:
    assert _rules('def q(field="stream"):\n    pass') == []
    assert _rules("def q(start=1):\n    pass") == []


def test_is_fabricated_default_rejects_exotic_constants() -> None:
    import ast

    def default_of(source: str) -> ast.expr:
        statement = ast.parse(source).body[0]
        assert isinstance(statement, ast.FunctionDef)
        return statement.args.defaults[0]

    assert scanner.is_fabricated_default(default_of("def f(x=1j):\n    pass"))
    assert not scanner.is_fabricated_default(default_of("def f(x=0j):\n    pass"))
    assert not scanner.is_fabricated_default(default_of("def f(x=...):\n    pass"))


# --- the line-scoped allow directive ----------------------------------------


def test_allow_directive_on_the_finding_line_exempts_it() -> None:
    assert _rules('X = "changeme"  # mock-data-scan: allow - documented sentinel') == []


def test_allow_directive_is_line_scoped_not_file_scoped() -> None:
    source = '# mock-data-scan: allow\nX = "changeme"'
    assert _rules(source) == [scanner.RULE_PLACEHOLDER]


def test_allow_directive_in_a_docstring_does_not_exempt_the_file() -> None:
    source = '"""mock-data-scan: allow — mentioned in prose."""\nX = "changeme"'
    assert _rules(source) == [scanner.RULE_PLACEHOLDER]


def test_allow_directive_exempts_only_its_own_line_among_many() -> None:
    source = 'A = "changeme"  # mock-data-scan: allow - sentinel\nB = "dummy"\n'
    findings = scanner.scan_source(source, "<case>")
    assert [(f.line, f.rule) for f in findings] == [(2, scanner.RULE_PLACEHOLDER)]


def test_allowed_lines_reports_marked_lines() -> None:
    assert scanner.allowed_lines("a = 1\nb = 2  # mock-data-scan: allow\n") == frozenset({2})


# --- Finding, rendering, ordering -------------------------------------------


def test_finding_render_is_stable() -> None:
    findings = scanner.scan_source('X = "changeme"', "sample.py")
    assert len(findings) == 1
    assert findings[0].render().startswith("sample.py:1:5: placeholder-literal:")


def test_findings_are_source_ordered_and_deduplicated() -> None:
    source = 'import pytest\nSAMPLE_BARS = [1]\nX = "dummy"\n'
    findings = scanner.scan_source(source, "s.py")
    assert [f.line for f in findings] == [1, 2, 3]
    assert [f.rule for f in findings] == [
        scanner.RULE_IMPORT,
        scanner.RULE_SAMPLE_DATA,
        scanner.RULE_PLACEHOLDER,
    ]


# --- malformed input --------------------------------------------------------


def test_syntax_error_is_reported_as_a_finding() -> None:
    # A fail-closed gate must not silently pass an unparseable file.
    findings = scanner.scan_source("def broken(:\n", "bad.py")
    assert len(findings) == 1
    assert findings[0].rule == scanner.RULE_UNSCANNABLE
    assert findings[0].path == "bad.py"


def test_unreadable_path_is_reported_as_a_finding(tmp_path: Path) -> None:
    findings = scanner.scan_file(tmp_path / "does_not_exist.py")
    assert len(findings) == 1
    assert findings[0].rule == scanner.RULE_UNSCANNABLE


def test_non_regular_path_is_reported_as_a_finding(tmp_path: Path) -> None:
    # A directory (or a device, FIFO or dangling symlink) is not a source file. The
    # gate refuses it up front rather than reading through it — a FIFO would otherwise
    # block the scan on a read that never returns.
    directory = tmp_path / "looks_like.py"
    directory.mkdir()
    findings = scanner.scan_file(directory)
    assert len(findings) == 1
    assert findings[0].rule == scanner.RULE_UNSCANNABLE
    assert "not a regular file" in findings[0].detail


def test_undecodable_file_is_reported_as_a_finding(tmp_path: Path) -> None:
    bad = tmp_path / "latin1.py"
    bad.write_bytes(b"x = '\xff\xfe not utf-8'\n")
    findings = scanner.scan_file(bad)
    assert len(findings) == 1
    assert findings[0].rule == scanner.RULE_UNSCANNABLE


def test_scan_file_outside_root_uses_absolute_path(tmp_path: Path) -> None:
    outside = tmp_path / "loose.py"
    outside.write_text('X = "changeme"\n', encoding="utf-8")
    findings = scanner.scan_file(outside, root=Path("C:/definitely/other/root"))
    assert findings
    assert findings[0].path == outside.as_posix()


# --- shipped-source discovery and the gate ----------------------------------


def _make_workspace(root: Path) -> Path:
    src_dir = root / "packages" / "qmf-demo" / "src" / "qmf" / "demo"
    src_dir.mkdir(parents=True)
    return src_dir


def test_iter_shipped_files_scopes_to_src_and_skips_test_trees(tmp_path: Path) -> None:
    src_dir = _make_workspace(tmp_path)
    (src_dir / "engine.py").write_text("x = 1\n", encoding="utf-8")
    # Outside src: package scaffolding, not shipped source.
    (tmp_path / "packages" / "qmf-demo" / "setup_helper.py").write_text("y = 1\n", encoding="utf-8")
    # Constructed data is the point in a test tree.
    tests = tmp_path / "packages" / "qmf-demo" / "tests"
    tests.mkdir()
    (tests / "test_engine.py").write_text('X = "changeme"\n', encoding="utf-8")
    assert {p.name for p in scanner.iter_shipped_files(tmp_path)} == {"engine.py"}


def test_iter_shipped_files_skips_examples_conftest_and_bench(tmp_path: Path) -> None:
    src_dir = _make_workspace(tmp_path)
    (src_dir / "engine.py").write_text("x = 1\n", encoding="utf-8")
    (src_dir / "conftest.py").write_text('X = "dummy"\n', encoding="utf-8")
    (src_dir / "_bench.py").write_text('X = "dummy"\n', encoding="utf-8")
    examples = src_dir / "examples"
    examples.mkdir()
    (examples / "walkthrough.py").write_text('X = "dummy"\n', encoding="utf-8")
    assert {p.name for p in scanner.iter_shipped_files(tmp_path)} == {"engine.py"}


def test_iter_shipped_files_covers_a_future_top_level_root(tmp_path: Path) -> None:
    # qmb/ and qml/ arrive in later epics; the gate covers them the day they land.
    future = tmp_path / "qmb" / "qmb-core" / "src" / "qmb"
    future.mkdir(parents=True)
    (future / "engine.py").write_text("x = 1\n", encoding="utf-8")
    assert {p.name for p in scanner.iter_shipped_files(tmp_path)} == {"engine.py"}


def test_iter_shipped_files_ignores_absent_roots(tmp_path: Path) -> None:
    assert list(scanner.iter_shipped_files(tmp_path)) == []


def test_scan_workspace_flags_a_planted_violation(tmp_path: Path) -> None:
    src_dir = _make_workspace(tmp_path)
    (src_dir / "feed.py").write_text("SAMPLE_PRICES = [1, 2, 3]\n", encoding="utf-8")
    findings = scanner.scan_workspace(tmp_path)
    assert len(findings) == 1
    assert findings[0].rule == scanner.RULE_SAMPLE_DATA


def test_main_is_clean_on_the_real_workspace(capsys: pytest.CaptureFixture[str]) -> None:
    assert scanner.main() == 0
    assert "clean" in capsys.readouterr().out


def test_main_fails_closed_on_a_violation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src_dir = _make_workspace(tmp_path)
    (src_dir / "adapter.py").write_text("class FakeVenue:\n    pass\n", encoding="utf-8")
    assert scanner.main(tmp_path) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert scanner.RULE_IDENTIFIER in out


def test_main_fails_closed_on_an_unparseable_shipped_file(tmp_path: Path) -> None:
    src_dir = _make_workspace(tmp_path)
    (src_dir / "broken.py").write_text("def broken(:\n", encoding="utf-8")
    assert scanner.main(tmp_path) == 1
