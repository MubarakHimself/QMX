"""Tier-1 ambient-nondeterminism static scanner (NFR-02 enforcing FR-002; CT-02 / AR-16).

Statically flags any read of the **system clock** or other ambient nondeterminism
below the composition root — ``datetime.now`` / ``datetime.utcnow`` / ``datetime.today``,
``date.today``, the ``time`` clock readers (``time.time``/``time.monotonic``/
``time.perf_counter`` and their ``_ns`` and process/thread variants), and draws from
the **unseeded global** ``random`` RNG. FR-002 requires that time is *injected* and
that nothing below the composition root reads the system clock; this scanner makes
that mechanically enforceable at the gate instead of leaving it to code review.
Wired into ``poe check`` at Tier 1, a single finding fails the gate with a nonzero
exit (fail-closed; AR-11, AR-18).

**The injected-Clock seam is the sanctioned path.** Clock access is the core-defined
:class:`qmf.core.chrono.Clock` :class:`typing.Protocol`, injected at the composition
root — a real clock in production, a ``DataDrivenClock`` in replay (CT-02; AR-16).
Usage through that seam (``clock.wall_now()``, ``clock.monotonic_now()``,
``self._clock.wall_now()``) reads a *value*, not the ``datetime``/``time``/``random``
modules, so it never matches a banned shape and is **not** flagged. A direct
system-clock read below the root **is** flagged.

**The composition root itself.** The root — where the real clock is constructed and
injected — and any sanctioned measurement harness (a benchmark that must read real
wall-clock time, AR-22/NFR-04) may read ambient nondeterminism. Such a file declares
itself with an explicit, auditable comment directive — ``# ambient-scan: allow`` — and
is then exempt as a whole. Everything *below* the root carries no such directive and
is enforced. The directive is the "named exemption stated at the point of use": it is
deliberate, greppable, and states its reason inline.

**Import-aware detection.** The scanner resolves each module's imports first, so it
follows aliases: ``import datetime as dt`` then ``dt.datetime.now()``,
``from datetime import datetime`` then ``datetime.now()``, ``from time import monotonic``
then ``monotonic()``, ``import random as rng`` then ``rng.random()`` are all caught,
while a *seeded* instance (``random.Random(0).random()``) and plain construction
(``datetime(2020, 1, 1)``, ``date.fromisoformat(s)``, ``timedelta(...)``) are not. It is
a gate, not a prover: a green result means "no banned ambient read was seen below the
root", not "provably deterministic". ``from time import *`` and dynamic ``getattr``
access are outside its precision boundary (documented, deliberately conservative).

**Scope.** The gate scans shipped source only — ``packages/*/src``, ``extensions/*/src``,
and the top-level ``tools`` scripts — and skips ``tests`` trees, whose fixtures
deliberately feed banned reads to assert they are flagged. Stdlib only; run via
``python tools/ambient_scan.py`` or ``poe ambient-scan``.
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()

# Shipped-source roots. Test trees are excluded (see module docstring).
SCAN_ROOTS: tuple[str, ...] = ("packages", "extensions", "tools")
SKIP_DIRS: frozenset[str] = frozenset(
    {
        "tests",
        "fixtures",
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

# The composition-root / sanctioned-reader opt-out. A file bearing this comment
# directive is the composition root (where the real clock is injected) or a
# sanctioned measurement harness (AR-22/NFR-04); it is exempt as a whole.
ALLOW_MARKER = re.compile(r"#\s*ambient-scan:\s*allow\b")

# datetime.datetime classmethods that read the system wall clock.
_DATETIME_NOW: frozenset[str] = frozenset({"now", "utcnow", "today"})
# datetime.date classmethods that read the system wall clock.
_DATE_TODAY: frozenset[str] = frozenset({"today"})

# time-module functions that read the system clock (wall or monotonic). All read
# the clock regardless of arguments; conversion helpers (gmtime/localtime with an
# explicit argument, strftime, sleep) are deliberately out of scope.
_TIME_CLOCK: frozenset[str] = frozenset(
    {
        "time",
        "time_ns",
        "monotonic",
        "monotonic_ns",
        "perf_counter",
        "perf_counter_ns",
        "process_time",
        "process_time_ns",
        "thread_time",
        "thread_time_ns",
    }
)

# random-module functions that draw from the unseeded global RNG. Seeding and
# explicit-instance construction (``seed``, ``Random``, ``SystemRandom``,
# ``getstate``/``setstate``) are not draws and are not flagged.
_RANDOM_DRAW: frozenset[str] = frozenset(
    {
        "random",
        "randint",
        "randrange",
        "randbytes",
        "getrandbits",
        "choice",
        "choices",
        "sample",
        "shuffle",
        "uniform",
        "triangular",
        "betavariate",
        "expovariate",
        "gammavariate",
        "gauss",
        "lognormvariate",
        "normalvariate",
        "vonmisesvariate",
        "paretovariate",
        "weibullvariate",
    }
)

# Whole-module imports whose bound name resolves to a module origin.
_MODULE_ORIGINS: dict[str, str] = {
    "datetime": "mod:datetime",
    "time": "mod:time",
    "random": "mod:random",
}

RULE_CLOCK = "system-clock-read"
RULE_RANDOM = "unseeded-random"


@dataclass(frozen=True)
class Finding:
    """One ambient-nondeterminism violation located in a source file."""

    path: str
    line: int
    col: int
    rule: str
    detail: str

    def render(self) -> str:
        return f"{self.path}:{self.line}:{self.col}: {self.rule}: {self.detail}"


# --- import resolution ------------------------------------------------------


def _from_origin(module: str, name: str) -> str | None:
    """The origin token a ``from <module> import <name>`` binding resolves to, or
    ``None`` when the imported name is not an ambient source."""
    if module == "datetime":
        if name == "datetime":
            return "cls:datetime.datetime"
        if name == "date":
            return "cls:datetime.date"
        return None
    if module == "time":
        return f"fn:time.{name}" if name in _TIME_CLOCK else None
    if module == "random":
        return f"fn:random.{name}" if name in _RANDOM_DRAW else None
    return None


# --- the scanner ------------------------------------------------------------


class _Analyzer:
    """Import-aware ambient-nondeterminism analysis over one module."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self._aliases: dict[str, str] = {}
        self._findings: list[Finding] = []

    def run(self, tree: ast.Module) -> list[Finding]:
        self._collect_imports(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                self._check_call(node)
        # Deterministic, source-ordered output regardless of walk order.
        unique = {(f.line, f.col, f.rule): f for f in self._findings}
        return sorted(unique.values(), key=lambda f: (f.line, f.col, f.rule))

    def _collect_imports(self, tree: ast.Module) -> None:
        """Bind every local name that refers to an ambient ``datetime``/``time``/
        ``random`` module, class, or function — following ``as`` aliases."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    origin = _MODULE_ORIGINS.get(alias.name)
                    if origin is not None:
                        self._aliases[alias.asname or alias.name] = origin
            elif isinstance(node, ast.ImportFrom):
                module = node.module
                if module is None:  # a relative import (from . import x) names no module
                    continue
                for alias in node.names:
                    origin = _from_origin(module, alias.name)
                    if origin is not None:
                        self._aliases[alias.asname or alias.name] = origin

    def _resolve(self, node: ast.expr) -> str | None:
        """Resolve a call receiver to an ambient origin token, or ``None``.

        Handles a bare imported name and the ``datetime.datetime`` / ``datetime.date``
        attribute chain reached through ``import datetime``; anything else (an
        injected clock, an arbitrary object) resolves to ``None`` and is never flagged.
        """
        if isinstance(node, ast.Name):
            return self._aliases.get(node.id)
        if isinstance(node, ast.Attribute):
            if self._resolve(node.value) == "mod:datetime":
                if node.attr == "datetime":
                    return "cls:datetime.datetime"
                if node.attr == "date":
                    return "cls:datetime.date"
            return None
        return None

    def _check_call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute):
            self._check_attribute_call(node, func)
        elif isinstance(func, ast.Name):
            self._check_name_call(node, func)

    def _check_attribute_call(self, node: ast.Call, func: ast.Attribute) -> None:
        origin = self._resolve(func.value)
        attr = func.attr
        if origin == "cls:datetime.datetime" and attr in _DATETIME_NOW:
            self._flag(node, RULE_CLOCK, f"datetime.{attr}() reads the system wall clock")
        elif origin == "cls:datetime.date" and attr in _DATE_TODAY:
            self._flag(node, RULE_CLOCK, "date.today() reads the system wall clock")
        elif origin == "mod:time" and attr in _TIME_CLOCK:
            self._flag(node, RULE_CLOCK, f"time.{attr}() reads the system clock")
        elif origin == "mod:random" and attr in _RANDOM_DRAW:
            self._flag(node, RULE_RANDOM, f"random.{attr}() draws from the unseeded global RNG")

    def _check_name_call(self, node: ast.Call, func: ast.Name) -> None:
        origin = self._aliases.get(func.id)
        if origin is None:
            return
        if origin.startswith("fn:time."):
            name = origin.split(".", 1)[1]
            self._flag(node, RULE_CLOCK, f"time.{name}() reads the system clock")
        elif origin.startswith("fn:random."):
            name = origin.split(".", 1)[1]
            self._flag(node, RULE_RANDOM, f"random.{name}() draws from the unseeded global RNG")

    def _flag(self, node: ast.Call, rule: str, detail: str) -> None:
        self._findings.append(
            Finding(self.filename, node.lineno, node.col_offset + 1, rule, detail)
        )


# --- public entry points ----------------------------------------------------


def scan_source(source: str, filename: str) -> list[Finding]:
    """Scan one module's source. A file bearing the ``# ambient-scan: allow``
    directive (the composition root or a sanctioned harness) yields no findings, and
    unparseable source yields none too (the gate never crashes on a malformed file;
    ruff owns syntax)."""
    if ALLOW_MARKER.search(source):
        return []
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return []
    return _Analyzer(filename).run(tree)


def scan_file(path: Path, *, root: Path = ROOT) -> list[Finding]:
    """Scan one file, reporting its path relative to ``root``."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        rel = path.resolve().relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
    return scan_source(source, rel)


def iter_shipped_files(root: Path = ROOT) -> Iterator[Path]:
    """Yield the shipped-source ``.py`` files the gate scans."""
    for scan_root in SCAN_ROOTS:
        base = root / scan_root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            dir_parts = path.relative_to(root).parts[:-1]
            if set(dir_parts) & SKIP_DIRS:
                continue
            if scan_root != "tools" and "src" not in dir_parts:
                continue
            if path.resolve() == SELF:
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
        sys.stdout.write(
            "ambient-scan: FAIL - ambient nondeterminism below the composition root:\n"
        )
        for finding in findings:
            sys.stdout.write(f"  {finding.render()}\n")
        return 1
    sys.stdout.write(f"ambient-scan: clean ({', '.join(SCAN_ROOTS)}).\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
