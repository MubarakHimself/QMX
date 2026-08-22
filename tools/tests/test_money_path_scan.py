"""Executable tests for the money-path float scanner (Story 1.7; NFR-02 / FR-001).

The scanner is exercised two ways: over the shipped ``must_flag`` /
``must_not_flag`` fixture corpus (every ``must_flag`` file must raise at least one
finding; every ``must_not_flag`` file must raise none), and through targeted
unit cases that pin the taint engine, the named-boundary discrimination, the
shipped-source file discovery, and the fail-closed gate entry point.
"""

from __future__ import annotations

from pathlib import Path

import money_path_scan as scanner
import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MUST_FLAG = sorted((FIXTURES / "must_flag").glob("*.py"))
MUST_NOT_FLAG = sorted((FIXTURES / "must_not_flag").glob("*.py"))


# --- the fixture corpus -----------------------------------------------------


def test_fixture_corpus_is_populated() -> None:
    # The story requires both must-flag and must-not-flag fixtures to exist.
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


# --- taint sources ----------------------------------------------------------


def _rules(source: str) -> list[str]:
    return [f.rule for f in scanner.scan_source(source, "<case>")]


def test_direct_constructor_float_literal_is_flagged() -> None:
    assert _rules('Money(3.5, "USD", 2)') == [scanner.RULE_CONSTRUCTION]


def test_try_create_via_variable_is_flagged() -> None:
    assert _rules("p = 1.089\nPrice.try_create(p, inst, 5)") == [scanner.RULE_CONSTRUCTION]


def test_float_call_source_is_flagged() -> None:
    assert _rules('Quantity.try_create(float(x), "lot", 0)') == [scanner.RULE_CONSTRUCTION]


def test_float_annotated_parameter_is_a_source() -> None:
    src = 'def f(x: float):\n    return Money.try_create(x, "USD", 2)'
    assert _rules(src) == [scanner.RULE_CONSTRUCTION]


def test_bool_constant_is_not_a_float_source() -> None:
    # ``True`` is an int subclass, not a binary float.
    assert _rules('Money.try_create(True, "USD", 2)') == []


# --- taint propagation ------------------------------------------------------


def test_arithmetic_binop_propagates_taint() -> None:
    assert _rules('q = 100.0 + 1\nQuantity.try_create(q, "lot", 2)') == [scanner.RULE_CONSTRUCTION]


def test_unaryop_propagates_taint() -> None:
    assert _rules('v = -1.5\nMoney.try_create(v, "USD", 2)') == [scanner.RULE_CONSTRUCTION]


def test_boolop_propagates_taint() -> None:
    assert _rules('v = a or 1.5\nMoney.try_create(v, "USD", 2)') == [scanner.RULE_CONSTRUCTION]


def test_ifexp_propagates_taint() -> None:
    assert _rules('v = 1.5 if cond else 2\nMoney.try_create(v, "USD", 2)') == [
        scanner.RULE_CONSTRUCTION
    ]


def test_subscript_and_attribute_propagate_taint() -> None:
    assert _rules('v = 1.5\nMoney.try_create(v.real, "USD", 2)') == [scanner.RULE_CONSTRUCTION]
    assert _rules('row = [1.5]\nMoney.try_create(row[0], "USD", 2)') == [scanner.RULE_CONSTRUCTION]


def test_dict_and_set_containers_propagate_taint() -> None:
    assert _rules('d = {"k": 1.5}\nMoney.try_create(d["k"], "USD", 2)') == [
        scanner.RULE_CONSTRUCTION
    ]
    assert _rules('s = {1.5}\nMoney.try_create(next(iter(s)), "USD", 2)') == [
        scanner.RULE_CONSTRUCTION
    ]


def test_augassign_propagates_taint() -> None:
    src = 'total = 0.0\ntotal += 1\nMoney.try_create(total, "USD", 2)'
    assert _rules(src) == [scanner.RULE_CONSTRUCTION]


def test_walrus_binding_propagates_taint() -> None:
    assert _rules('Money.try_create((y := 1.5), "USD", 2)') == [scanner.RULE_CONSTRUCTION]


def test_await_propagates_taint() -> None:
    src = 'async def f(x: float):\n    return Money.try_create(await wrap(x), "USD", 2)'
    assert _rules(src) == [scanner.RULE_CONSTRUCTION]


def test_chained_assignment_propagates_taint() -> None:
    src = 'a = 1.5\nb = a\nc = b\nMoney.try_create(c, "USD", 2)'
    assert _rules(src) == [scanner.RULE_CONSTRUCTION]


def test_int_laundering_does_not_clear_taint() -> None:
    assert _rules('raw = 1.5\nMoney.try_create(int(raw * 100), "USD", 2)') == [
        scanner.RULE_CONSTRUCTION
    ]


def test_call_keyword_argument_propagates_taint() -> None:
    src = 'raw = 1.5\nMoney.try_create(helper(x=raw), "USD", 2)'
    assert _rules(src) == [scanner.RULE_CONSTRUCTION]


# --- tuple / list unpacking -------------------------------------------------


def test_tuple_unpack_is_element_wise() -> None:
    src = 'a, b = 2, 1.5\nMoney.try_create(b, "USD", 2)'
    assert _rules(src) == [scanner.RULE_CONSTRUCTION]


def test_tuple_unpack_leaves_integer_element_clean() -> None:
    src = 'a, b = 2, 1.5\nMoney.try_create(a, "USD", 2)'
    assert _rules(src) == []


def test_uneven_unpack_taints_whole_target_including_starred() -> None:
    src = 'first, *rest = 1.5, 2, 3\nMoney.try_create(rest, "USD", 2)'
    assert _rules(src) == [scanner.RULE_CONSTRUCTION]


# --- the named conversion boundary ------------------------------------------


def test_from_float_with_rounding_is_sanctioned() -> None:
    src = 'Money.from_float(1.5, currency="USD", scale=2, rounding=RoundingMode.HALF_UP)'
    assert _rules(src) == []


def test_from_float_with_string_rounding_is_sanctioned() -> None:
    assert _rules('Quantity.from_float(1.5, unit="lot", scale=2, rounding="half-up")') == []


def test_from_float_without_rounding_is_flagged() -> None:
    assert _rules('Money.from_float(1.5, currency="USD", scale=2)') == [
        scanner.RULE_UNDECLARED_BOUNDARY
    ]


def test_from_float_with_rounding_none_is_flagged() -> None:
    assert _rules('Money.from_float(1.5, currency="USD", scale=2, rounding=None)') == [
        scanner.RULE_UNDECLARED_BOUNDARY
    ]


def test_from_float_with_kwargs_unpack_is_not_flagged() -> None:
    # A ``**opts`` unpack might carry the rounding mode; give it the benefit of doubt.
    src = "def f(x: float, opts):\n    return Money.from_float(x, **opts)"
    assert _rules(src) == []


def test_from_float_with_integer_value_is_not_flagged() -> None:
    # No money-path float in the first place, so nothing to flag at the boundary.
    assert _rules('Money.from_float(5, currency="USD", scale=2)') == []


# --- annotation and return sinks --------------------------------------------


def test_annotated_money_target_from_float_is_flagged() -> None:
    assert _rules("bal: Money = 1234.56") == [scanner.RULE_CONSTRUCTION]


def test_annotated_money_target_from_boundary_is_clean() -> None:
    src = 'bal: Money = Money.from_float(1.5, currency="USD", scale=2, rounding="down")'
    assert _rules(src) == []


def test_return_money_annotation_with_float_is_flagged() -> None:
    assert _rules("def f() -> Money:\n    return 3.14") == [scanner.RULE_CONSTRUCTION]


def test_return_without_money_annotation_is_clean() -> None:
    assert _rules("def f() -> float:\n    return 3.14") == []


def test_optional_and_generic_money_annotations_are_recognized() -> None:
    assert _rules("bal: Money | None = 1.5") == [scanner.RULE_CONSTRUCTION]
    assert _rules("def f() -> Result[Money]:\n    return 1.5") == [scanner.RULE_CONSTRUCTION]


# --- value-factor / exact-rational sinks ------------------------------------


def test_value_factor_numerator_float_is_flagged() -> None:
    assert _rules('ValueFactor.try_create(1.0, 1, inst, "USD")') == [scanner.RULE_CONSTRUCTION]


def test_value_factor_denominator_float_is_flagged() -> None:
    assert _rules('ValueFactor.try_create(1, 2.0, inst, "USD")') == [scanner.RULE_CONSTRUCTION]


def test_value_argument_by_keyword_is_flagged() -> None:
    assert _rules('Money.try_create(value=1.5, currency="USD", scale=2)') == [
        scanner.RULE_CONSTRUCTION
    ]


def test_starred_positional_falls_back_to_keyword() -> None:
    assert _rules("Money.try_create(*rest, value=1.5)") == [scanner.RULE_CONSTRUCTION]


# --- clean cases ------------------------------------------------------------


def test_exact_integer_construction_is_clean() -> None:
    assert _rules('Money.try_create(350, "USD", 2)') == []


def test_decimal_and_fraction_cleanse_the_taint() -> None:
    # ``str(...)`` reparses the float as decimal text — the sanctioned cleanse.
    assert _rules('raw = 1.5\nMoney.try_create(int(Decimal(str(raw)) * 100), "USD", 2)') == []
    assert _rules('raw = 1.5\nMoney.try_create(Fraction(str(raw)).numerator, "USD", 2)') == []


def test_decimal_of_a_tainted_float_keeps_the_taint() -> None:
    # Decimal(px) on a binary float captures its representation error verbatim —
    # the cleanse only applies when the argument is not itself a float.
    assert _rules('raw = 1.5\nMoney.try_create(int(Decimal(raw) * 100), "USD", 2)') == [
        scanner.RULE_CONSTRUCTION
    ]


def test_fraction_of_a_tainted_float_keeps_the_taint() -> None:
    assert _rules('raw = 1.5\nMoney.try_create(Fraction(raw).numerator, "USD", 2)') == [
        scanner.RULE_CONSTRUCTION
    ]


def test_from_float_on_unrelated_receiver_does_not_cleanse() -> None:
    # ``from_float`` launders taint only on the CT-01 value types; on any other
    # receiver a declared rounding keyword does not sanctify it.
    src = 'v = helper.from_float(raw, rounding="half-up")\nMoney.try_create(v, "USD", 2)'
    assert _rules("raw = 1.5\n" + src) == [scanner.RULE_CONSTRUCTION]


def test_float_off_the_money_path_is_clean() -> None:
    assert _rules("start = perf_counter()\nelapsed = perf_counter() - start\nx = elapsed * 2") == []


def test_unrelated_constructor_is_not_a_sink() -> None:
    assert _rules("Widget(1.5)\nlog(3.14)") == []


def test_cls_try_create_is_not_name_anchored() -> None:
    # ``cls.try_create`` inside a classmethod is out of the scanner's precision
    # boundary (documented); it must not raise a false positive.
    src = (
        "class Money:\n    @classmethod\n    def f(cls, x):\n"
        "        return cls.try_create(x, 'USD', 2)"
    )
    assert _rules(src) == []


# --- nested scopes ----------------------------------------------------------


def test_nested_function_scope_is_isolated() -> None:
    # ``rate`` is an outer-scope float; the scanner does not follow the closure,
    # so the inner constructor is not flagged (documented conservative limit).
    src = (
        "def outer():\n"
        "    rate = 1.5\n"
        "    def inner():\n"
        "        return Money.try_create(rate, 'USD', 2)\n"
        "    return inner\n"
    )
    assert _rules(src) == []


def test_class_body_annotation_sink_is_flagged() -> None:
    assert _rules("class Book:\n    balance: Money = 1.5") == [scanner.RULE_CONSTRUCTION]


def test_lambda_body_float_sink_is_flagged() -> None:
    assert _rules('make = lambda: Money(1.5, "USD", 2)') == [scanner.RULE_CONSTRUCTION]


def test_vararg_and_kwarg_without_annotation_are_ignored() -> None:
    src = 'def f(*args, **kwargs):\n    return Money.try_create(args, "USD", 2)'
    assert _rules(src) == []


# --- Finding and rendering --------------------------------------------------


def test_finding_render_is_stable() -> None:
    findings = scanner.scan_source('Money(1.5, "USD", 2)', "sample.py")
    assert len(findings) == 1
    rendered = findings[0].render()
    assert rendered.startswith("sample.py:1:1: money-path-float:")


def test_findings_are_source_ordered_and_deduplicated() -> None:
    src = 'Money(1.5, "USD", 2)\nPrice.try_create(2.5, inst, 5)'
    findings = scanner.scan_source(src, "s.py")
    assert [f.line for f in findings] == [1, 2]


# --- malformed input --------------------------------------------------------


def test_syntax_error_is_reported_as_a_finding() -> None:
    # Regression (L9): a fail-closed gate must not silently pass an unparseable
    # file. An unparseable source is itself a finding, not clean silence.
    findings = scanner.scan_source("def broken(:\n", "bad.py")
    assert len(findings) == 1
    assert findings[0].rule == scanner.RULE_UNSCANNABLE
    assert findings[0].path == "bad.py"


def test_unreadable_path_is_reported_as_a_finding(tmp_path: Path) -> None:
    # Regression (L9): an unreadable file must fail the gate closed, not vanish.
    missing = tmp_path / "does_not_exist.py"
    findings = scanner.scan_file(missing)
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
    # Regression (L9): a file that is not valid UTF-8 is a finding, never silence.
    bad = tmp_path / "latin1.py"
    bad.write_bytes(b"x = '\xff\xfe not utf-8'\n")
    findings = scanner.scan_file(bad)
    assert len(findings) == 1
    assert findings[0].rule == scanner.RULE_UNSCANNABLE


def test_scan_workspace_fails_closed_on_an_unparseable_shipped_file(tmp_path: Path) -> None:
    # Regression (L9): a broken shipped file surfaces through scan_workspace so the
    # gate entry point returns nonzero rather than passing over it.
    _make_workspace(tmp_path)
    shipped = tmp_path / "packages" / "qmf-demo" / "src" / "qmf" / "demo" / "broken.py"
    shipped.write_text("def broken(:\n", encoding="utf-8")
    findings = scanner.scan_workspace(tmp_path)
    assert any(f.rule == scanner.RULE_UNSCANNABLE for f in findings)
    assert scanner.main(tmp_path) == 1


def test_scan_file_outside_root_uses_absolute_path(tmp_path: Path) -> None:
    outside = tmp_path / "loose.py"
    outside.write_text('Money(1.5, "USD", 2)\n', encoding="utf-8")
    findings = scanner.scan_file(outside, root=Path("C:/definitely/other/root"))
    assert findings
    assert findings[0].path == outside.as_posix()


# --- shipped-source discovery and the gate ----------------------------------


def _make_workspace(root: Path) -> None:
    src_dir = root / "packages" / "qmf-demo" / "src" / "qmf" / "demo"
    src_dir.mkdir(parents=True)
    (root / "packages" / "qmf-demo" / "tests").mkdir(parents=True)


def test_iter_shipped_files_scopes_to_src_and_skips_tests(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    shipped = tmp_path / "packages" / "qmf-demo" / "src" / "qmf" / "demo" / "values.py"
    shipped.write_text("x = 1\n", encoding="utf-8")
    # A package-level file outside src is not shipped source.
    (tmp_path / "packages" / "qmf-demo" / "conftest.py").write_text("y = 1\n", encoding="utf-8")
    # A test-tree file is excluded (its float negatives are intentional).
    (tmp_path / "packages" / "qmf-demo" / "tests" / "test_values.py").write_text(
        'Money(1.5, "USD", 2)\n', encoding="utf-8"
    )
    found = {p.name for p in scanner.iter_shipped_files(tmp_path)}
    assert found == {"values.py"}


def test_iter_shipped_files_includes_top_level_tools(tmp_path: Path) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "helper.py").write_text("z = 1\n", encoding="utf-8")
    (tools / "tests").mkdir()
    (tools / "tests" / "test_helper.py").write_text('Money(1.5, "USD", 2)\n', encoding="utf-8")
    found = {p.name for p in scanner.iter_shipped_files(tmp_path)}
    assert found == {"helper.py"}


def test_scan_workspace_flags_planted_violation(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    shipped = tmp_path / "packages" / "qmf-demo" / "src" / "qmf" / "demo" / "bad.py"
    shipped.write_text(
        'from qmf.core.exact import Money\nMoney(9.99, "USD", 2)\n', encoding="utf-8"
    )
    findings = scanner.scan_workspace(tmp_path)
    assert len(findings) == 1
    assert findings[0].rule == scanner.RULE_CONSTRUCTION


def test_main_is_clean_on_the_real_workspace(capsys: pytest.CaptureFixture[str]) -> None:
    assert scanner.main() == 0
    assert "clean" in capsys.readouterr().out


def test_main_fails_closed_on_a_violation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _make_workspace(tmp_path)
    shipped = tmp_path / "packages" / "qmf-demo" / "src" / "qmf" / "demo" / "bad.py"
    shipped.write_text('Money(9.99, "USD", 2)\n', encoding="utf-8")
    assert scanner.main(tmp_path) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "money-path-float" in out
