"""Tier-1 ambient-nondeterminism static scanner (NFR-02 enforcing FR-002; CT-02 / AR-16).

Statically flags any read of the **system clock** or other ambient nondeterminism
below the composition root — ``datetime.now`` / ``datetime.utcnow`` / ``datetime.today``,
``date.today``, the ``time`` clock readers (``time.time``/``time.monotonic``/
``time.perf_counter`` and their ``_ns`` and process/thread variants), draws from
the **unseeded global** ``random`` RNG, and the **OS-entropy** sources that are the
opposite of a seeded instance: ``os.urandom`` / ``os.getrandom``, the ``secrets``
CSPRNG helpers, the nondeterministic ``uuid`` constructors (``uuid1`` clock+node,
``uuid4`` entropy), and a draw off ``random.SystemRandom()``. FR-002 requires that
time is *injected* and that nothing below the composition root reads the system clock
or other ambient nondeterminism; this scanner makes that mechanically enforceable at
the gate instead of leaving it to code review. Wired into ``poe check`` at Tier 1, a
single finding fails the gate with a nonzero exit (fail-closed; AR-11, AR-18).

**The injected-Clock seam is the sanctioned path.** Clock access is the core-defined
:class:`qmf.core.chrono.Clock` :class:`typing.Protocol`, injected at the composition
root — a real clock in production, a ``DataDrivenClock`` in replay (CT-02; AR-16).
Usage through that seam (``clock.wall_now()``, ``clock.monotonic_now()``,
``self._clock.wall_now()``) reads a *value*, not the ``datetime``/``time``/``random``
modules, so it never matches a banned shape and is **not** flagged. A direct
system-clock read below the root **is** flagged.

**The composition root itself.** The root — where the real clock is constructed and
injected — and any sanctioned measurement harness (a benchmark that must read real
wall-clock time, AR-22/NFR-04) may read ambient nondeterminism. Each such read
declares itself with an explicit, auditable comment directive — ``# ambient-scan:
allow`` — on the **same line** as the read; only reads on a directive-bearing line are
exempt, everything else is enforced. The directive is **line-scoped**, not
file-scoped: a marker buried in a docstring or a module header no longer waves the
whole file through, so a real ambient read added later on an unmarked line is still
flagged. The directive is the "named exemption stated at the point of use": it is
deliberate, greppable, and states its reason inline next to the read it sanctions.

**Import-aware detection.** The scanner resolves each module's imports first, so it
follows aliases: ``import datetime as dt`` then ``dt.datetime.now()``,
``from datetime import datetime`` then ``datetime.now()``, ``from time import monotonic``
then ``monotonic()``, ``import random as rng`` then ``rng.random()`` are all caught. It
also catches a **bound-reference laundering** — a banned callable stashed in a local
and called later (``f = time.time`` then ``f()``; ``n = datetime.now`` then ``n()``) —
by binding the local to the callable it aliases. A *seeded* instance
(``random.Random(0).random()``) and plain construction (``datetime(2020, 1, 1)``,
``date.fromisoformat(s)``, ``timedelta(...)``, a bare ``random.SystemRandom()`` that is
never drawn from) are not flagged. It is a gate, not a prover: a green result means
"no banned ambient read was seen below the root", not "provably deterministic".
``from time import *``, dynamic ``getattr`` access, and an entropy instance stashed in
a local before it is drawn from are outside its precision boundary (documented,
deliberately conservative).

**Scope.** The gate scans shipped source only — ``packages/*/src``, ``extensions/*/src``,
the same ``src`` layout under ``qml/`` (and later ``qmb/``), and the top-level ``tools``
scripts — and skips ``tests`` trees, whose fixtures deliberately feed banned reads to
assert they are flagged. Stdlib only; run via ``python tools/ambient_scan.py`` or
``poe ambient-scan``.
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()

# Shipped-source roots. Test trees are excluded (see module docstring).
SCAN_ROOTS: tuple[str, ...] = ("packages", "extensions", "qml", "qmb", "qmn", "tools")
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

# The composition-root / sanctioned-reader opt-out. A source LINE bearing this
# comment directive (the composition root where the real clock is injected, or a
# sanctioned measurement harness, AR-22/NFR-04) exempts only the ambient reads on
# that same line — the exemption is line-scoped, never whole-file.
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
# *seeded* explicit-instance construction (``seed``, ``Random``, ``getstate``/
# ``setstate``) are not draws and are not flagged. ``SystemRandom`` is deliberately
# NOT sanctioned here: it reads OS entropy — the opposite of a seeded instance — so a
# draw off it is flagged as an OS-entropy source (see ``_check_attribute_call``).
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

# os functions that read OS entropy (nondeterministic); the opposite of a seed.
_OS_ENTROPY: frozenset[str] = frozenset({"urandom", "getrandom"})

# secrets-module helpers, all of which draw from the OS-entropy CSPRNG.
_SECRETS_ENTROPY: frozenset[str] = frozenset(
    {"token_bytes", "token_hex", "token_urlsafe", "randbelow", "randbits", "choice"}
)

# uuid constructors that read ambient nondeterminism: ``uuid1`` (host node + wall
# clock) and ``uuid4`` (OS entropy). ``uuid3``/``uuid5`` are deterministic namespace
# hashes (name -> md5/sha1) and are NOT flagged.
_UUID_ENTROPY: frozenset[str] = frozenset({"uuid1", "uuid4"})

# Whole-module imports whose bound name resolves to a module origin.
_MODULE_ORIGINS: dict[str, str] = {
    "datetime": "mod:datetime",
    "time": "mod:time",
    "random": "mod:random",
    "os": "mod:os",
    "secrets": "mod:secrets",
    "uuid": "mod:uuid",
}

RULE_CLOCK = "system-clock-read"
RULE_RANDOM = "unseeded-random"
RULE_ENTROPY = "os-entropy"
# A file the gate could not parse or read. A fail-closed gate must not pass a file
# it could not inspect, so an unparseable/unreadable file is a finding, not silence.
RULE_UNSCANNABLE = "unscannable-source"

# The origin token for a SystemRandom class reference (from ``random`` or ``secrets``);
# constructing it yields an OS-entropy RNG, so a draw off it is flagged.
_SYSTEM_RANDOM = "cls:random.SystemRandom"


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
        if name in _RANDOM_DRAW:
            return f"fn:random.{name}"
        if name == "SystemRandom":
            return _SYSTEM_RANDOM
        return None
    if module == "os":
        return f"fn:os.{name}" if name in _OS_ENTROPY else None
    if module == "secrets":
        if name in _SECRETS_ENTROPY:
            return f"fn:secrets.{name}"
        if name == "SystemRandom":
            return _SYSTEM_RANDOM
        return None
    if module == "uuid":
        return f"fn:uuid.{name}" if name in _UUID_ENTROPY else None
    return None


def _fn_finding(origin: str) -> tuple[str, str] | None:
    """Map an ``fn:<module>.<name>`` callable origin to its ``(rule, detail)``.

    Shared by a bare-name call to an imported ambient function and by a laundered
    bound reference resolved to the same origin; ``None`` for any non-``fn:`` token.
    """
    if not origin.startswith("fn:"):
        return None
    module, _, name = origin[len("fn:") :].partition(".")
    if module == "time":
        return RULE_CLOCK, f"time.{name}() reads the system clock"
    if module == "datetime":
        return RULE_CLOCK, f"datetime.{name}() reads the system wall clock"
    if module == "date":
        return RULE_CLOCK, f"date.{name}() reads the system wall clock"
    if module == "random":
        return RULE_RANDOM, f"random.{name}() draws from the unseeded global RNG"
    if module == "os":
        return RULE_ENTROPY, f"os.{name}() reads OS entropy (nondeterministic)"
    if module == "secrets":
        return RULE_ENTROPY, f"secrets.{name}() draws from OS entropy"
    if module == "uuid":
        return RULE_ENTROPY, f"uuid.{name}() draws from ambient nondeterminism"
    return None


# --- the scanner ------------------------------------------------------------


class _Analyzer:
    """Import-aware ambient-nondeterminism analysis over one module."""

    def __init__(self, filename: str, allow_lines: frozenset[int] = frozenset()) -> None:
        self.filename = filename
        self._allow_lines = allow_lines
        self._aliases: dict[str, str] = {}
        self._findings: list[Finding] = []

    def run(self, tree: ast.Module) -> list[Finding]:
        self._collect_imports(tree)
        self._collect_bindings(tree)
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

    def _collect_bindings(self, tree: ast.Module) -> None:
        """Bind a local assigned a laundered ambient *callable reference*.

        ``f = time.time`` (later ``f()``) or ``n = datetime.now`` (later ``n()``)
        stashes a banned callable in a local; binding the local to that callable's
        ``fn:`` origin makes the later call flag. Only a reference to a callable is
        bound — an *instance* construction (``rng = random.Random(0)``) is a call, not
        a reference, and is not bound, so seeded-instance draws stay clean.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                self._bind_targets(node.targets, node.value)
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                self._bind_targets([node.target], node.value)

    def _bind_targets(self, targets: Sequence[ast.expr], value: ast.expr) -> None:
        """Bind each ``Name`` in ``targets`` to the callable ``value`` references."""
        origin = self._resolve_callable_ref(value)
        if origin is None:
            return
        for target in targets:
            if isinstance(target, ast.Name):
                self._aliases[target.id] = origin

    def _resolve(self, node: ast.expr) -> str | None:
        """Resolve a call receiver to an ambient origin token, or ``None``.

        Handles a bare imported name, the ``datetime.datetime`` / ``datetime.date``
        attribute chain reached through ``import datetime``, and the
        ``random.SystemRandom`` / ``secrets.SystemRandom`` class reference; anything
        else (an injected clock, an arbitrary object) resolves to ``None`` and is
        never flagged.
        """
        if isinstance(node, ast.Name):
            return self._aliases.get(node.id)
        if isinstance(node, ast.Attribute):
            base = self._resolve(node.value)
            if base == "mod:datetime":
                if node.attr == "datetime":
                    return "cls:datetime.datetime"
                if node.attr == "date":
                    return "cls:datetime.date"
            elif base in {"mod:random", "mod:secrets"} and node.attr == "SystemRandom":
                return _SYSTEM_RANDOM
            return None
        return None

    def _construction_origin(self, node: ast.expr) -> str | None:
        """The origin of the instance a call constructs (``random.SystemRandom()``),
        or ``None`` when ``node`` is not such a construction."""
        if isinstance(node, ast.Call):
            return self._resolve(node.func)
        return None

    def _resolve_callable_ref(self, node: ast.expr) -> str | None:
        """Resolve an expression used as a *value* (not called) to the ambient
        callable it references, so a laundered bound reference is caught later.

        Returns an ``fn:`` origin token or ``None``. A bare name already bound to an
        ``fn:`` origin (``m = monotonic``) forwards that origin; an attribute chain
        (``time.time``, ``datetime.now``) resolves through the import aliases.
        """
        if isinstance(node, ast.Name):
            origin = self._aliases.get(node.id)
            return origin if origin is not None and origin.startswith("fn:") else None
        if isinstance(node, ast.Attribute):
            base = self._resolve(node.value)
            attr = node.attr
            if base == "cls:datetime.datetime" and attr in _DATETIME_NOW:
                return f"fn:datetime.{attr}"
            if base == "cls:datetime.date" and attr in _DATE_TODAY:
                return f"fn:date.{attr}"
            if base == "mod:time" and attr in _TIME_CLOCK:
                return f"fn:time.{attr}"
            if base == "mod:random" and attr in _RANDOM_DRAW:
                return f"fn:random.{attr}"
            if base == "mod:os" and attr in _OS_ENTROPY:
                return f"fn:os.{attr}"
            if base == "mod:secrets" and attr in _SECRETS_ENTROPY:
                return f"fn:secrets.{attr}"
            if base == "mod:uuid" and attr in _UUID_ENTROPY:
                return f"fn:uuid.{attr}"
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
        if origin is None:
            # A draw off a freshly constructed ``random.SystemRandom()`` reads OS
            # entropy — the opposite of a seeded instance — so it is flagged even
            # though the receiver is a call, not a resolvable name.
            if attr in _RANDOM_DRAW and self._construction_origin(func.value) == _SYSTEM_RANDOM:
                self._flag(
                    node,
                    RULE_ENTROPY,
                    f"random.SystemRandom().{attr}() draws from OS entropy, not a seeded instance",
                )
            return
        if origin == "cls:datetime.datetime" and attr in _DATETIME_NOW:
            self._flag(node, RULE_CLOCK, f"datetime.{attr}() reads the system wall clock")
        elif origin == "cls:datetime.date" and attr in _DATE_TODAY:
            self._flag(node, RULE_CLOCK, "date.today() reads the system wall clock")
        elif origin == "mod:time" and attr in _TIME_CLOCK:
            self._flag(node, RULE_CLOCK, f"time.{attr}() reads the system clock")
        elif origin == "mod:random" and attr in _RANDOM_DRAW:
            self._flag(node, RULE_RANDOM, f"random.{attr}() draws from the unseeded global RNG")
        elif origin == "mod:os" and attr in _OS_ENTROPY:
            self._flag(node, RULE_ENTROPY, f"os.{attr}() reads OS entropy (nondeterministic)")
        elif origin == "mod:secrets" and attr in _SECRETS_ENTROPY:
            self._flag(node, RULE_ENTROPY, f"secrets.{attr}() draws from OS entropy")
        elif origin == "mod:uuid" and attr in _UUID_ENTROPY:
            self._flag(node, RULE_ENTROPY, f"uuid.{attr}() draws from ambient nondeterminism")

    def _check_name_call(self, node: ast.Call, func: ast.Name) -> None:
        origin = self._aliases.get(func.id)
        if origin is None:
            return
        finding = _fn_finding(origin)
        if finding is not None:
            self._flag(node, finding[0], finding[1])

    def _flag(self, node: ast.Call, rule: str, detail: str) -> None:
        # Line-scoped exemption: a read on a line bearing ``# ambient-scan: allow`` is
        # the sanctioned composition-root / harness read and is not reported.
        if node.lineno in self._allow_lines:
            return
        self._findings.append(
            Finding(self.filename, node.lineno, node.col_offset + 1, rule, detail)
        )


# --- public entry points ----------------------------------------------------


def _allow_lines(source: str) -> frozenset[int]:
    """The 1-based line numbers bearing a ``# ambient-scan: allow`` directive.

    Line-scoped: a marker exempts only ambient reads on its own line, so a marker in
    a docstring or module header no longer waves the whole file through."""
    return frozenset(
        lineno
        for lineno, line in enumerate(source.splitlines(), start=1)
        if ALLOW_MARKER.search(line)
    )


def scan_source(source: str, filename: str) -> list[Finding]:
    """Scan one module's source. Ambient reads on a line bearing the
    ``# ambient-scan: allow`` directive (the composition root or a sanctioned
    harness) are exempt; every other ambient read is a finding. Unparseable source
    is itself a finding — a fail-closed gate must not silently pass a file it could
    not inspect (ruff owns syntax, but the gate never fails open)."""
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
    return _Analyzer(filename, _allow_lines(source)).run(tree)


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
