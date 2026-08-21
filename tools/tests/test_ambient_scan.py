"""Executable tests for the ambient-nondeterminism scanner (Story 1.8; NFR-02 / FR-002).

The scanner is exercised two ways: over the shipped ``must_flag`` / ``must_not_flag``
fixture corpus (every ``must_flag`` file must raise at least one finding; every
``must_not_flag`` file must raise none), and through targeted unit cases that pin the
import-aware detection, the injected-Clock discrimination, the composition-root allow
directive, the shipped-source file discovery, and the fail-closed gate entry point.
"""

from __future__ import annotations

from pathlib import Path

import ambient_scan as scanner
import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ambient"
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


# --- helpers ----------------------------------------------------------------


def _rules(source: str) -> list[str]:
    return [f.rule for f in scanner.scan_source(source, "<case>")]


# --- datetime clock reads ---------------------------------------------------


def test_from_imported_datetime_now_is_flagged() -> None:
    assert _rules("from datetime import datetime\nx = datetime.now()") == [scanner.RULE_CLOCK]


def test_module_datetime_now_is_flagged() -> None:
    assert _rules("import datetime\nx = datetime.datetime.now(datetime.timezone.utc)") == [
        scanner.RULE_CLOCK
    ]


def test_datetime_utcnow_and_today_are_flagged() -> None:
    assert _rules("from datetime import datetime\nx = datetime.utcnow()") == [scanner.RULE_CLOCK]
    assert _rules("from datetime import datetime\nx = datetime.today()") == [scanner.RULE_CLOCK]


def test_date_today_is_flagged() -> None:
    assert _rules("from datetime import date\nd = date.today()") == [scanner.RULE_CLOCK]


def test_module_date_today_is_flagged() -> None:
    assert _rules("import datetime\nd = datetime.date.today()") == [scanner.RULE_CLOCK]


def test_aliased_datetime_module_is_flagged() -> None:
    assert _rules("import datetime as dt\nx = dt.datetime.now()") == [scanner.RULE_CLOCK]


def test_aliased_from_import_datetime_is_flagged() -> None:
    assert _rules("from datetime import datetime as clock\nx = clock.now()") == [scanner.RULE_CLOCK]


# --- time clock reads -------------------------------------------------------


def test_time_time_and_monotonic_are_flagged() -> None:
    assert _rules("import time\nt = time.time()") == [scanner.RULE_CLOCK]
    assert _rules("import time\nt = time.monotonic()") == [scanner.RULE_CLOCK]


def test_time_perf_counter_ns_is_flagged() -> None:
    assert _rules("import time\nt = time.perf_counter_ns()") == [scanner.RULE_CLOCK]


def test_from_imported_time_reader_is_flagged() -> None:
    assert _rules("from time import monotonic\nt = monotonic()") == [scanner.RULE_CLOCK]


def test_from_imported_time_reader_alias_is_flagged() -> None:
    assert _rules("from time import perf_counter as pc\nt = pc()") == [scanner.RULE_CLOCK]


def test_aliased_time_module_is_flagged() -> None:
    assert _rules("import time as wc\nt = wc.monotonic()") == [scanner.RULE_CLOCK]


def test_time_sleep_and_conversion_helpers_are_not_flagged() -> None:
    # sleep is not a clock read; gmtime/strftime with args are conversions.
    assert _rules("import time\ntime.sleep(1)") == []
    assert _rules("import time\ns = time.strftime('%Y', time.gmtime(0))") == []


# --- random draws -----------------------------------------------------------


def test_unseeded_random_module_draw_is_flagged() -> None:
    assert _rules("import random\nr = random.random()") == [scanner.RULE_RANDOM]
    assert _rules("import random\nn = random.randint(1, 6)") == [scanner.RULE_RANDOM]


def test_from_imported_random_draw_is_flagged() -> None:
    assert _rules("from random import randint\nn = randint(1, 6)") == [scanner.RULE_RANDOM]


def test_aliased_random_module_draw_is_flagged() -> None:
    assert _rules("import random as rng\nx = rng.uniform(0, 1)") == [scanner.RULE_RANDOM]


def test_seeded_random_instance_is_not_flagged() -> None:
    assert _rules("import random\nr = random.Random(0).random()") == []
    assert _rules("import random\nrng = random.Random(0)\nx = rng.random()") == []


def test_random_seed_is_not_a_draw() -> None:
    assert _rules("import random\nrandom.seed(1234)") == []


def test_system_random_construction_is_not_a_draw() -> None:
    assert _rules("import random\ns = random.SystemRandom()") == []


# --- OS-entropy and CSPRNG sources ------------------------------------------


def test_os_urandom_and_getrandom_are_flagged() -> None:
    assert _rules("import os\nn = os.urandom(16)") == [scanner.RULE_ENTROPY]
    assert _rules("import os\nn = os.getrandom(8)") == [scanner.RULE_ENTROPY]


def test_from_imported_os_urandom_is_flagged() -> None:
    assert _rules("from os import urandom\nn = urandom(16)") == [scanner.RULE_ENTROPY]


def test_ordinary_os_call_is_not_flagged() -> None:
    # Only the entropy readers are in scope; os.getcwd() is deterministic here.
    assert _rules("import os\np = os.getcwd()") == []


def test_secrets_helpers_are_flagged() -> None:
    assert _rules("import secrets\nk = secrets.token_hex()") == [scanner.RULE_ENTROPY]
    assert _rules("import secrets\nk = secrets.token_bytes(16)") == [scanner.RULE_ENTROPY]
    assert _rules("import secrets\nk = secrets.randbelow(10)") == [scanner.RULE_ENTROPY]


def test_from_imported_secrets_helper_is_flagged() -> None:
    assert _rules("from secrets import token_urlsafe\nk = token_urlsafe()") == [
        scanner.RULE_ENTROPY
    ]


def test_uuid1_and_uuid4_are_flagged() -> None:
    assert _rules("import uuid\nu = uuid.uuid4()") == [scanner.RULE_ENTROPY]
    assert _rules("import uuid\nu = uuid.uuid1()") == [scanner.RULE_ENTROPY]


def test_from_imported_uuid4_is_flagged() -> None:
    assert _rules("from uuid import uuid4\nu = uuid4()") == [scanner.RULE_ENTROPY]


def test_deterministic_namespace_uuids_are_not_flagged() -> None:
    assert _rules("import uuid\nu = uuid.uuid5(uuid.NAMESPACE_DNS, 'x')") == []
    assert _rules("import uuid\nu = uuid.uuid3(uuid.NAMESPACE_DNS, 'x')") == []


# --- SystemRandom: OS entropy, not a seeded instance ------------------------


def test_system_random_draw_is_flagged() -> None:
    assert _rules("import random\nx = random.SystemRandom().random()") == [scanner.RULE_ENTROPY]


def test_from_imported_system_random_draw_is_flagged() -> None:
    assert _rules("from random import SystemRandom\nx = SystemRandom().randint(1, 6)") == [
        scanner.RULE_ENTROPY
    ]


def test_secrets_system_random_draw_is_flagged() -> None:
    assert _rules("import secrets\nx = secrets.SystemRandom().random()") == [scanner.RULE_ENTROPY]


def test_from_imported_secrets_system_random_draw_is_flagged() -> None:
    assert _rules("from secrets import SystemRandom\nx = SystemRandom().random()") == [
        scanner.RULE_ENTROPY
    ]


def test_seeded_random_stays_sanctioned_after_system_random_change() -> None:
    # The seeded instance is still the sanctioned deterministic path.
    assert _rules("import random\nx = random.Random(0).random()") == []


# --- bound-reference laundering ---------------------------------------------


def test_bound_time_reference_is_flagged() -> None:
    assert _rules("import time\nf = time.time\nx = f()") == [scanner.RULE_CLOCK]


def test_bound_datetime_now_reference_is_flagged() -> None:
    assert _rules("from datetime import datetime\nn = datetime.now\nx = n()") == [
        scanner.RULE_CLOCK
    ]


def test_bound_date_today_reference_is_flagged() -> None:
    assert _rules("from datetime import date\nd = date.today\nx = d()") == [scanner.RULE_CLOCK]


def test_bound_random_draw_reference_is_flagged() -> None:
    assert _rules("import random\ng = random.random\nx = g()") == [scanner.RULE_RANDOM]


def test_bound_entropy_reference_is_flagged() -> None:
    assert _rules("import uuid\ng = uuid.uuid4\nx = g()") == [scanner.RULE_ENTROPY]
    assert _rules("import os\ng = os.urandom\nx = g(8)") == [scanner.RULE_ENTROPY]
    assert _rules("import secrets\ng = secrets.token_hex\nx = g()") == [scanner.RULE_ENTROPY]


def test_annotated_bound_reference_is_flagged() -> None:
    assert _rules("import time\nf: object = time.monotonic\nx = f()") == [scanner.RULE_CLOCK]


def test_bare_annotation_binds_nothing() -> None:
    # A bare annotation carries no value to resolve; it binds nothing.
    assert _rules("import time\nf: object\ndef use(f):\n    return f()") == []


def test_bound_non_ambient_reference_is_not_flagged() -> None:
    # Binding an ordinary callable reference is not an ambient read.
    assert _rules("def build():\n    g = sorted\n    return g([3, 1])") == []


# --- the injected Clock seam ------------------------------------------------


def test_injected_clock_wall_now_is_not_flagged() -> None:
    assert _rules("def f(clock):\n    return clock.wall_now()") == []


def test_injected_clock_monotonic_now_is_not_flagged() -> None:
    assert _rules("def f(clock):\n    return clock.monotonic_now()") == []


def test_injected_clock_attribute_receiver_is_not_flagged() -> None:
    assert _rules("def f(self):\n    return self._clock.wall_now()") == []


# --- deterministic construction ---------------------------------------------


def test_datetime_and_date_construction_are_not_flagged() -> None:
    assert _rules("from datetime import datetime, timezone\nx = datetime(2020, 1, 1)") == []
    assert _rules("from datetime import date\nd = date(2020, 1, 1)") == []


def test_deterministic_datetime_helpers_are_not_flagged() -> None:
    assert _rules("from datetime import date\nd = date.fromisoformat('2020-01-01')") == []
    assert _rules("from datetime import datetime\nx = datetime.fromtimestamp(0)") == []


def test_unrelated_now_method_is_not_flagged() -> None:
    # ``.now()`` on an object that is not the datetime class is out of scope.
    assert _rules("def f(session):\n    return session.now()") == []


def test_unrelated_random_name_is_not_flagged() -> None:
    # A local ``random`` that was never imported as the module is not resolved.
    assert _rules("def f(random):\n    return random.random()") == []


# --- the composition-root allow directive -----------------------------------


def test_allow_directive_exempts_the_whole_file() -> None:
    src = "# ambient-scan: allow\nimport time\nt = time.monotonic()"
    assert _rules(src) == []


def test_allow_directive_with_reason_is_recognized() -> None:
    src = "import time  # ambient-scan: allow - measurement harness\nt = time.time()"
    assert _rules(src) == []


def test_missing_directive_still_flags() -> None:
    assert _rules("import time\nt = time.monotonic()") == [scanner.RULE_CLOCK]


# --- Finding, rendering, ordering -------------------------------------------


def test_finding_render_is_stable() -> None:
    findings = scanner.scan_source("from datetime import datetime\nx = datetime.now()", "sample.py")
    assert len(findings) == 1
    rendered = findings[0].render()
    assert rendered.startswith("sample.py:2:5: system-clock-read:")


def test_findings_are_source_ordered_and_deduplicated() -> None:
    src = "import time\nimport random\na = time.time()\nb = random.random()"
    findings = scanner.scan_source(src, "s.py")
    assert [f.line for f in findings] == [3, 4]
    assert [f.rule for f in findings] == [scanner.RULE_CLOCK, scanner.RULE_RANDOM]


# --- receiver-resolution edges ----------------------------------------------


def test_non_clock_datetime_attribute_chain_is_not_flagged() -> None:
    # datetime.timezone.* resolves to no ambient origin, so the call is clean.
    assert _rules("import datetime\nx = datetime.timezone.utc.utcoffset(None)") == []


def test_call_target_that_is_neither_name_nor_attribute_is_ignored() -> None:
    # A call whose callee is a subscript (or another call) is not a resolvable read.
    assert _rules("handlers = []\nhandlers[0]()") == []


def test_non_ambient_from_import_binds_nothing() -> None:
    # A from-import of an unrelated module resolves to no origin and is never flagged.
    assert _rules("from os import getcwd\nx = getcwd()") == []


def test_relative_import_is_ignored() -> None:
    # A relative import names no module and cannot resolve to an ambient origin.
    assert _rules("from . import helpers\nx = helpers.now()") == []


# --- malformed input --------------------------------------------------------


def test_syntax_error_yields_no_findings() -> None:
    assert scanner.scan_source("def broken(:\n", "bad.py") == []


def test_star_import_is_outside_precision_boundary() -> None:
    # A star import cannot be resolved to a bound name; documented conservative miss.
    assert _rules("from time import *\nt = monotonic()") == []


def test_scan_file_handles_unreadable_path(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.py"
    assert scanner.scan_file(missing) == []


def test_scan_file_outside_root_uses_absolute_path(tmp_path: Path) -> None:
    outside = tmp_path / "loose.py"
    outside.write_text("import time\nt = time.time()\n", encoding="utf-8")
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
    shipped = tmp_path / "packages" / "qmf-demo" / "src" / "qmf" / "demo" / "clocks.py"
    shipped.write_text("x = 1\n", encoding="utf-8")
    # A package-level file outside src is not shipped source.
    (tmp_path / "packages" / "qmf-demo" / "conftest.py").write_text("y = 1\n", encoding="utf-8")
    # A test-tree file is excluded (its ambient negatives are intentional).
    (tmp_path / "packages" / "qmf-demo" / "tests" / "test_clocks.py").write_text(
        "import time\nt = time.time()\n", encoding="utf-8"
    )
    found = {p.name for p in scanner.iter_shipped_files(tmp_path)}
    assert found == {"clocks.py"}


def test_iter_shipped_files_includes_top_level_tools(tmp_path: Path) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "helper.py").write_text("z = 1\n", encoding="utf-8")
    (tools / "tests").mkdir()
    (tools / "tests" / "test_helper.py").write_text(
        "import time\nt = time.time()\n", encoding="utf-8"
    )
    found = {p.name for p in scanner.iter_shipped_files(tmp_path)}
    assert found == {"helper.py"}


def test_scan_workspace_flags_planted_violation(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    shipped = tmp_path / "packages" / "qmf-demo" / "src" / "qmf" / "demo" / "bad.py"
    shipped.write_text("import time\nt = time.monotonic()\n", encoding="utf-8")
    findings = scanner.scan_workspace(tmp_path)
    assert len(findings) == 1
    assert findings[0].rule == scanner.RULE_CLOCK


def test_main_is_clean_on_the_real_workspace(capsys: pytest.CaptureFixture[str]) -> None:
    assert scanner.main() == 0
    assert "clean" in capsys.readouterr().out


def test_main_fails_closed_on_a_violation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _make_workspace(tmp_path)
    shipped = tmp_path / "packages" / "qmf-demo" / "src" / "qmf" / "demo" / "bad.py"
    shipped.write_text("import random\nx = random.random()\n", encoding="utf-8")
    assert scanner.main(tmp_path) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "unseeded-random" in out
