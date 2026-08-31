"""Tier-1 mock-data static scanner (NFR-02; the "no constructed data ships" gate).

Statically flags **mock, placeholder and fabricated data in shipped source** — the
stand-in values a coding agent leaves behind when it needs something to return
before the real input exists. Hardcoded sample market data, placeholder literals
(``lorem ipsum``, ``dummy``, ``changeme``, ``xxx``), ``mock_``/``fake_``/``stub_``
identifiers outside a test tree, an imported mocking library, and fabricated
default values standing in for real inputs are all findings. Wired into
``poe check`` at Tier 1, a single finding fails the gate with a nonzero exit
(fail-closed; AR-11, AR-18), so "mock data never ships" is enforced mechanically
in every lane rather than left to whoever reads the diff.

**Why a gate and not a review note.** Constructed data is legitimate — in tests,
in benchmarks, in examples. It is illegitimate in the code a user runs, where a
placeholder is indistinguishable from a real value until it produces a wrong
number. Review catches this unreliably and agents reintroduce it cheaply; a gate
catches it every time, in every lane, without anyone having to remember.

**What is flagged.**

* ``mock-identifier`` — a function, class, assignment target or parameter whose
  name carries ``mock``/``fake``/``stub``/``dummy`` as a *word*. The name is split
  on underscores and CamelCase boundaries before matching, so ``MockClock`` and
  ``price_stub`` are findings while ``Faker`` (a name, not the word) and
  ``stubborn`` are not.
* ``mock-library-import`` — shipped source importing a mocking or test-double
  library (``unittest.mock``, ``pytest``, ``responses``, ``faker``, ``freezegun``,
  ...). Those belong to a test tree; in shipped code they are machinery for
  fabricating values.
* ``placeholder-literal`` — a string constant that *is* a placeholder rather than
  data: it equals a known placeholder token, or opens with one. Docstrings are
  exempt (documentation may name a placeholder; data may not be one).
* ``hardcoded-sample-data`` — a non-empty list/tuple/set/dict literal bound to a
  name that says it is fabricated *and* says it is data (``SAMPLE_PRICES``,
  ``EXAMPLE_MARKET_DATA``, ``demo_candles``).
* ``fabricated-default`` — a parameter that names a real input (``price``,
  ``balance``, ``quantity``, ``symbol``, ``bars``, ...) carrying a hardcoded
  literal default. A ``None`` sentinel, a boolean switch, a zero, an empty string
  or container, and any named constant or factory call are legitimate and are not
  flagged; a fabricated value standing in for the caller's real one is.

**The sanctioned exemption.** A line bearing ``# mock-data-scan: allow`` exempts
only the findings on that same line. The directive is line-scoped, not
file-scoped, and it states its reason inline next to what it sanctions — the same
discipline the ambient-nondeterminism gate uses.

**Scope.** The gate scans shipped product source only — ``packages/*/src``,
``extensions/*/src``, and the same ``src`` layout under the ``qmb`` and ``qml``
roots that later epics add (a root that does not exist yet is simply skipped, so
this needs no edit when they land). ``tests`` and ``fixtures`` trees, ``examples``
trees, ``conftest.py`` and the ``_bench.py`` measurement harnesses are exempt:
constructed data is the point in all of them. The ``tools`` tree is out of scope
too — unlike the money-path and ambient gates, this scanner would trip over the
gate machinery's own pattern tables, which necessarily spell out the very tokens
it hunts.

It is a gate, not a prover: a green result means "no constructed stand-in data was
seen in shipped source", not "provably free of fabricated values". Stdlib only;
run via ``python tools/mock_data_scan.py`` or ``poe mock-data-scan``.
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Shipped product-source roots. ``qmb`` and ``qml`` arrive in later epics; naming
# them now means the gate covers them the day they land. A root that does not
# exist is skipped.
SCAN_ROOTS: tuple[str, ...] = ("packages", "extensions", "qmb", "qml", "qmn")

# Trees where constructed data is legitimate, plus the usual machine noise.
SKIP_DIRS: frozenset[str] = frozenset(
    {
        "tests",
        "fixtures",
        "examples",
        "__pycache__",
        ".venv",
        ".git",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "build",
        "dist",
    }
)

# Files where constructed data is legitimate: the pytest collection hook and the
# per-package measurement harnesses (AR-22/NFR-04), which build their own ladders.
SKIP_FILES: frozenset[str] = frozenset({"conftest.py", "_bench.py"})

# The line-scoped opt-out. A source LINE bearing this directive exempts only the
# findings on that same line — never the whole file.
ALLOW_MARKER = re.compile(r"#\s*mock-data-scan:\s*allow\b")

# Words that mark an identifier as a test double wherever they appear as a word.
MOCK_WORDS: frozenset[str] = frozenset({"mock", "fake", "stub", "dummy"})

# Mocking / test-double libraries. Importing one into shipped source is machinery
# for fabricating values, whatever it is then used for.
MOCK_MODULES: frozenset[str] = frozenset(
    {
        "mock",
        "unittest.mock",
        "pytest",
        "pytest_mock",
        "responses",
        "requests_mock",
        "faker",
        "freezegun",
        "hypothesis",
        "factory_boy",
    }
)

# Literals that are a placeholder rather than a value. Matched against a
# normalized form (lowercased, ``_`` and ``-`` folded to spaces), either exactly
# or as the opening of a short string, so ``CHANGE_ME`` and
# ``"changeme - set in config"`` both land while ordinary prose does not.
PLACEHOLDER_TOKENS: frozenset[str] = frozenset(
    {
        "lorem ipsum",
        "dummy",
        "changeme",
        "change me",
        "placeholder",
        "xxx",
        "xxxx",
        "foobar",
        "foo bar",
        "tbd",
        "fixme",
        "your api key",
        "your key here",
        "your token here",
        "replace me",
        "asdf",
        "qwerty",
        "sample value",
        "example value",
    }
)
# A placeholder that merely *opens* a string is only believable in a short one;
# past this length the string is prose that happens to mention the word.
PLACEHOLDER_PREFIX_MAX_LEN = 60
# Characters that close the opening placeholder token in a longer string.
PLACEHOLDER_BOUNDARY: frozenset[str] = frozenset({" ", ":", "-", ".", ",", "!", "/", "="})

# A name says data is fabricated...
FABRICATION_WORDS: frozenset[str] = frozenset(
    {
        "sample",
        "example",
        "demo",
        "dummy",
        "fake",
        "mock",
        "stub",
        "synthetic",
        "placeholder",
        "canned",
    }
)
# ...and a name says it is data.
DATA_WORDS: frozenset[str] = frozenset(
    {
        "data",
        "price",
        "prices",
        "bar",
        "bars",
        "candle",
        "candles",
        "tick",
        "ticks",
        "quote",
        "quotes",
        "order",
        "orders",
        "trade",
        "trades",
        "row",
        "rows",
        "record",
        "records",
        "rate",
        "rates",
        "series",
        "values",
        "payload",
        "payloads",
        "response",
        "responses",
        "feed",
        "feeds",
        "market",
        "markets",
        "book",
        "books",
        "fill",
        "fills",
    }
)
# Parameters that name a real input the caller is supposed to supply. A hardcoded
# literal default on one of these is a fabricated stand-in.
INPUT_WORDS: frozenset[str] = DATA_WORDS | frozenset(
    {
        "balance",
        "quantity",
        "qty",
        "volume",
        "amount",
        "size",
        "pnl",
        "equity",
        "spread",
        "symbol",
        "ticker",
        "instrument",
        "account",
        "venue",
    }
)

_DOCSTRING_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)

RULE_IDENTIFIER = "mock-identifier"
RULE_IMPORT = "mock-library-import"
RULE_PLACEHOLDER = "placeholder-literal"
RULE_SAMPLE_DATA = "hardcoded-sample-data"
RULE_FABRICATED_DEFAULT = "fabricated-default"
# A file the gate could not parse or read. A fail-closed gate must not pass a file
# it could not inspect, so an unparseable/unreadable file is a finding, not silence.
RULE_UNSCANNABLE = "unscannable-source"

_WORD_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z]+|[a-z]+|[0-9]+")

_Flaggable = ast.stmt | ast.expr | ast.arg


@dataclass(frozen=True)
class Finding:
    """One mock-data violation located in a shipped source file."""

    path: str
    line: int
    col: int
    rule: str
    detail: str

    def render(self) -> str:
        return f"{self.path}:{self.line}:{self.col}: {self.rule}: {self.detail}"


# --- name and literal helpers ------------------------------------------------


def name_words(name: str) -> frozenset[str]:
    """The lowercased word tokens of an identifier.

    Splits on underscores and CamelCase boundaries, so ``MockClock`` yields
    ``{mock, clock}`` and ``price_stub`` yields ``{price, stub}``, while ``Faker``
    yields ``{faker}`` and ``stubborn`` yields ``{stubborn}`` — the word has to be
    a word, not the opening of a longer one.
    """
    return frozenset(word.lower() for part in name.split("_") for word in _WORD_RE.findall(part))


def is_mock_name(name: str) -> bool:
    """Does this identifier name a test double?"""
    return bool(name_words(name) & MOCK_WORDS)


def normalize_literal(text: str) -> str:
    """A string literal folded for placeholder matching: lowercased, with ``_``
    and ``-`` read as spaces, so ``CHANGE_ME`` and ``change-me`` are one shape."""
    return text.strip().lower().replace("_", " ").replace("-", " ")


def is_placeholder_literal(text: str) -> bool:
    """Is this string constant a placeholder rather than a value?"""
    normalized = normalize_literal(text)
    if not normalized:
        return False
    if "lorem ipsum" in normalized:
        return True
    for token in PLACEHOLDER_TOKENS:
        if normalized == token:
            return True
        if len(normalized) > PLACEHOLDER_PREFIX_MAX_LEN or not normalized.startswith(token):
            continue
        if normalized[len(token) : len(token) + 1] in PLACEHOLDER_BOUNDARY:
            return True
    return False


def is_populated_container(node: ast.expr) -> bool:
    """A collection literal that actually carries elements. An empty collection is
    an identity value, not fabricated data."""
    if isinstance(node, ast.Dict):
        return bool(node.keys)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return bool(node.elts)
    return False


def is_fabricated_default(node: ast.expr) -> bool:
    """Is this parameter default a fabricated value rather than a neutral one?

    A ``None`` sentinel, a boolean switch, a zero, an empty string or container,
    and any named constant or factory call are legitimate defaults. A non-empty
    literal — a number that is not zero, a non-empty string, a populated
    collection — is a value the caller was supposed to supply.
    """
    if is_populated_container(node):
        return True
    if not isinstance(node, ast.Constant):
        return False
    value = node.value
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float, complex)):
        return value != 0
    return False


# --- the scanner ------------------------------------------------------------


class _Analyzer:
    """Mock-data analysis over one module."""

    def __init__(self, filename: str, allowed_lines: frozenset[int] = frozenset()) -> None:
        self.filename = filename
        self._allowed_lines = allowed_lines
        self._docstrings: set[int] = set()
        self._findings: list[Finding] = []

    def run(self, tree: ast.Module) -> list[Finding]:
        self._collect_docstrings(tree)
        for node in ast.walk(tree):
            self._check(node)
        # Deterministic, source-ordered output regardless of walk order.
        unique = {(f.line, f.col, f.rule): f for f in self._findings}
        return sorted(unique.values(), key=lambda f: (f.line, f.col, f.rule))

    def _collect_docstrings(self, tree: ast.Module) -> None:
        """Record every docstring node, so documentation that *names* a
        placeholder is never mistaken for data that *is* one."""
        for node in ast.walk(tree):
            if not isinstance(node, _DOCSTRING_OWNERS) or not node.body:
                continue
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                self._docstrings.add(id(first.value))

    # -- dispatch ------------------------------------------------------------

    def _check(self, node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._check_named(node, node.name, "function")
            self._check_parameters(node.args)
        elif isinstance(node, ast.ClassDef):
            self._check_named(node, node.name, "class")
        elif isinstance(node, ast.Lambda):
            self._check_parameters(node.args)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                self._check_binding(node, target, node.value)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            self._check_binding(node, node.target, node.value)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            self._check_import(node)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            self._check_string(node)

    # -- the rules -----------------------------------------------------------

    def _check_named(self, node: ast.stmt, name: str, kind: str) -> None:
        if is_mock_name(name):
            self._flag(
                node,
                RULE_IDENTIFIER,
                f"{kind} '{name}' names a test double in shipped code",
            )

    def _check_parameters(self, args: ast.arguments) -> None:
        for arg, default in _parameters_with_defaults(args):
            if is_mock_name(arg.arg):
                self._flag(
                    arg,
                    RULE_IDENTIFIER,
                    f"parameter '{arg.arg}' names a test double in shipped code",
                )
            if default is None or not (name_words(arg.arg) & INPUT_WORDS):
                continue
            if is_fabricated_default(default):
                self._flag(
                    default,
                    RULE_FABRICATED_DEFAULT,
                    f"parameter '{arg.arg}' defaults to a fabricated stand-in for a real input",
                )

    def _check_binding(self, node: ast.stmt, target: ast.expr, value: ast.expr) -> None:
        for name, name_node in _bound_names(target):
            if is_mock_name(name):
                self._flag(
                    name_node,
                    RULE_IDENTIFIER,
                    f"'{name}' names a test double in shipped code",
                )
        # The sample-data rule needs the whole literal to be what the name binds,
        # so it applies to a plain target only: in ``a, sample_bars = 1, 2`` the
        # tuple is destructured, and no name holds that collection.
        if not isinstance(target, ast.Name) or not is_populated_container(value):
            return
        words = name_words(target.id)
        if words & FABRICATION_WORDS and words & DATA_WORDS:
            self._flag(
                node,
                RULE_SAMPLE_DATA,
                f"'{target.id}' binds hardcoded sample data in shipped code",
            )

    def _check_import(self, node: ast.Import | ast.ImportFrom) -> None:
        for module in _imported_modules(node):
            if module in MOCK_MODULES:
                self._flag(
                    node,
                    RULE_IMPORT,
                    f"shipped code imports the test-double library '{module}'",
                )
                return

    def _check_string(self, node: ast.Constant) -> None:
        if id(node) in self._docstrings:
            return
        text = node.value
        if isinstance(text, str) and is_placeholder_literal(text):
            self._flag(node, RULE_PLACEHOLDER, "a placeholder literal stands in for a real value")

    # -- reporting -----------------------------------------------------------

    def _flag(self, node: _Flaggable, rule: str, detail: str) -> None:
        # Line-scoped exemption: a finding on a line bearing the allow directive is
        # the sanctioned, stated-at-the-point-of-use case and is not reported.
        if node.lineno in self._allowed_lines:
            return
        self._findings.append(
            Finding(self.filename, node.lineno, node.col_offset + 1, rule, detail)
        )


# --- AST helpers ------------------------------------------------------------


def _parameters_with_defaults(args: ast.arguments) -> Iterator[tuple[ast.arg, ast.expr | None]]:
    """Every declared parameter paired with its default expression, if any."""
    positional = [*args.posonlyargs, *args.args]
    padding: list[ast.expr | None] = [None] * (len(positional) - len(args.defaults))
    yield from zip(positional, [*padding, *args.defaults], strict=True)
    yield from zip(args.kwonlyargs, args.kw_defaults, strict=True)
    for arg in (args.vararg, args.kwarg):
        if arg is not None:
            yield arg, None


def _bound_names(target: ast.expr) -> Iterator[tuple[str, ast.expr]]:
    """Every ``Name`` bound by an assignment target, with the node that binds it."""
    if isinstance(target, ast.Name):
        yield target.id, target
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            yield from _bound_names(element)
    elif isinstance(target, ast.Starred):
        yield from _bound_names(target.value)


def _imported_modules(node: ast.Import | ast.ImportFrom) -> Iterator[str]:
    """The dotted module paths an import brings in, including the
    ``from unittest import mock`` form that names its module in the alias."""
    if isinstance(node, ast.Import):
        for alias in node.names:
            yield alias.name
        return
    module = node.module
    if module is None:  # a relative import names no absolute module
        return
    yield module
    for alias in node.names:
        yield f"{module}.{alias.name}"


# --- public entry points ----------------------------------------------------


def allowed_lines(source: str) -> frozenset[int]:
    """The 1-based line numbers bearing a ``# mock-data-scan: allow`` directive.

    Line-scoped: a marker exempts only findings on its own line, so a marker in a
    docstring or module header cannot wave the whole file through."""
    return frozenset(
        lineno
        for lineno, line in enumerate(source.splitlines(), start=1)
        if ALLOW_MARKER.search(line)
    )


def scan_source(source: str, filename: str) -> list[Finding]:
    """Scan one module's source. Findings on a line bearing the
    ``# mock-data-scan: allow`` directive are exempt; every other one is reported.
    Unparseable source is itself a finding — a fail-closed gate must not silently
    pass a file it could not inspect (ruff owns syntax, but the gate never fails
    open)."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        return [
            Finding(
                filename,
                exc.lineno or 1,
                (exc.offset or 0) + 1,
                RULE_UNSCANNABLE,
                f"source could not be parsed ({exc.msg}); the gate fails closed on it",
            )
        ]
    return _Analyzer(filename, allowed_lines(source)).run(tree)


def scan_file(path: Path, *, root: Path = ROOT) -> list[Finding]:
    """Scan one file, reporting its path relative to ``root``.

    An unreadable file (a read or decode error) is itself a finding, not silence: a
    fail-closed gate must not pass a file it could not inspect."""
    try:
        rel = path.resolve().relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
    # A regular file, or nothing. A directory, a device or a FIFO would either raise
    # here or — for a FIFO — block the gate forever on a read that never ends, and a
    # dangling symlink would read as an absent file. Refusing up front keeps the
    # fail-closed promise literal, and keeps the check next to the read it guards.
    if not path.is_file():
        return [
            Finding(
                rel,
                1,
                1,
                RULE_UNSCANNABLE,
                "not a regular file (a directory, device, FIFO or dangling symlink); "
                "the gate fails closed rather than reading through it",
            )
        ]
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [
            Finding(
                rel,
                1,
                1,
                RULE_UNSCANNABLE,
                f"file could not be read ({exc}); the gate fails closed",
            )
        ]
    return scan_source(source, rel)


def iter_shipped_files(root: Path = ROOT) -> Iterator[Path]:
    """Yield the shipped product-source ``.py`` files the gate scans."""
    for scan_root in SCAN_ROOTS:
        base = root / scan_root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            dir_parts = path.relative_to(root).parts[:-1]
            if set(dir_parts) & SKIP_DIRS:
                continue
            if "src" not in dir_parts:
                continue
            if path.name in SKIP_FILES:
                continue
            yield path


def scan_workspace(root: Path = ROOT) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_shipped_files(root):
        findings.extend(scan_file(path, root=root))
    return findings


def main(root: Path = ROOT) -> int:
    findings = scan_workspace(root)
    if findings:
        sys.stdout.write("mock-data-scan: FAIL - mock or placeholder data in shipped source:\n")
        for finding in findings:
            sys.stdout.write(f"  {finding.render()}\n")
        return 1
    sys.stdout.write(f"mock-data-scan: clean ({', '.join(SCAN_ROOTS)}).\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
