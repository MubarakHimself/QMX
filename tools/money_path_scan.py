"""Tier-1 money-path float scanner (NFR-02 enforcing FR-001; CT-01 / DEC-0105).

Statically flags any binary ``float`` that reaches a value on the **money path**
— any value that transitively contributes to an order quantity, price, P&L, or
balance (CT-01; DEC-0105). FR-001 bans binary float on the money path and treats
it as a taint; this scanner makes that ban mechanically enforceable at the gate
instead of leaving it to code review. Wired into ``poe check`` at Tier 1, a
single finding fails the gate with a nonzero exit (fail-closed; AR-11, AR-18).

**What is the money path.** The money path is a *taint*, not a location. The
concrete carriers of order quantity, price, P&L, and balance are the CT-01 exact
value types — :class:`Money`, :class:`Price`, :class:`Quantity`,
:class:`PriceDelta`, :class:`ValueFactor`, and the exact-parameter
:class:`ExactRational`. A binary float is a violation when it reaches the
value-bearing argument of one of those value constructors (or its ``try_create``
factory), is assigned to a money-path-typed target, or is returned as one.

**The sanctioned crossing.** A float re-enters an exact value only through a
*named conversion boundary that states its rounding mode* — the ``from_float``
factories on the CT-01 value types (``Money.from_float(x, ..., rounding=...)``).
A ``from_float`` on one of those types that declares a rounding mode is NOT
flagged; one that carries a float but declares no rounding mode IS flagged (an
undeclared crossing). ``from_float`` on any *other* receiver is an ordinary call —
it launders nothing, so the taint flows straight through it. ``Decimal(...)`` and
``Fraction(...)`` construction clears the taint only when the argument is not
itself a binary float: ``Decimal(str(x))`` reparses decimal text and is exact, but
``Decimal(px)`` / ``Fraction(px)`` capture the float's binary representation error
verbatim and stay tainted.

**Taint tracking.** Within each function/module/class scope the scanner tracks
which local names carry float taint: float literals, ``float(...)`` calls, and
``float``-annotated parameters are sources, and taint flows through arithmetic,
assignment chains, and ordinary calls (so ``int(x * 1.5)`` laundering is caught).
The analysis is intraprocedural and monotone — deliberately conservative: it does
not follow taint across function boundaries or through closures, and once a name
is tainted in a scope it stays tainted (a name reused for both a float and a later
integer money value is flagged rather than silently cleared). It is a gate, not a
prover: a green result means "no binary float was seen reaching a money-path
value", not "provably float-free on the money path".

**Scope.** The gate scans shipped source only — ``packages/*/src``,
``extensions/*/src``, and the top-level ``tools`` scripts — and skips ``tests``
trees, whose negative cases deliberately feed floats to money constructors to
assert they are refused. Stdlib only; run via ``python tools/money_path_scan.py``
or ``poe money-path-scan``.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterable, Iterator
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

# The CT-01 exact value types — the concrete carriers of order quantity, price,
# P&L, and balance. A binary float reaching one of these is on the money path.
MONEY_PATH_TYPES: frozenset[str] = frozenset(
    {"Money", "Price", "Quantity", "PriceDelta", "ValueFactor", "ExactRational"}
)

# The value-bearing constructor argument(s) per type: (positional index, keyword).
# Money/Price/Quantity/PriceDelta take a single ``value``; the rational-backed
# types take ``numerator`` and ``denominator``.
_VALUE_ARGS: dict[str, tuple[tuple[int, str], ...]] = {
    "Money": ((0, "value"),),
    "Price": ((0, "value"),),
    "Quantity": ((0, "value"),),
    "PriceDelta": ((0, "value"),),
    "ValueFactor": ((0, "numerator"), (1, "denominator")),
    "ExactRational": ((0, "numerator"), (1, "denominator")),
}

# The named conversion boundary: a float re-enters an exact value only here, and
# only with an explicit rounding mode.
BOUNDARY_METHOD = "from_float"
ROUNDING_KEYWORD = "rounding"

# Exact constructors that clear float taint — but only when their argument is not
# itself a binary float. ``Decimal(str(x))`` reparses decimal text (exact);
# ``Decimal(px)`` captures the float's binary error verbatim (stays tainted).
EXACT_CLEANSERS: frozenset[str] = frozenset({"Decimal", "Fraction"})

# Stringify calls break the binary-float chain: their result is decimal text, so
# an exact constructor wrapping ``str(x)`` reparses a decimal string, not a float.
STRINGIFIERS: frozenset[str] = frozenset({"str", "repr", "format", "ascii"})

_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)

RULE_CONSTRUCTION = "money-path-float"
RULE_UNDECLARED_BOUNDARY = "undeclared-rounding-boundary"
# A file the gate could not parse or read. A fail-closed gate must not pass a file
# it could not inspect, so an unparseable/unreadable file is a finding, not silence.
RULE_UNSCANNABLE = "unscannable-source"


@dataclass(frozen=True)
class Finding:
    """One money-path float violation located in a source file."""

    path: str
    line: int
    col: int
    rule: str
    detail: str

    def render(self) -> str:
        return f"{self.path}:{self.line}:{self.col}: {self.rule}: {self.detail}"


# --- AST helpers ------------------------------------------------------------


def _callee_tail(func: ast.expr) -> str | None:
    """The final name of a call target: ``Money`` for ``Money`` or ``x.Money``,
    ``try_create`` for ``Money.try_create``, or ``None`` for anything else."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _owner_tail(func: ast.expr) -> str | None:
    """For an attribute call ``X.method``, the final name of ``X`` (so the owning
    type of ``Money.try_create`` resolves to ``Money``); ``None`` otherwise."""
    if isinstance(func, ast.Attribute):
        return _callee_tail(func.value)
    return None


def _annotation_names(annotation: ast.expr) -> set[str]:
    """Every type name mentioned in an annotation subtree (so ``Money``,
    ``Money | None``, and ``Result[Money]`` all surface ``Money``)."""
    names: set[str] = set()
    for node in ast.walk(annotation):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def _is_float_annotation(annotation: ast.expr) -> bool:
    return "float" in _annotation_names(annotation)


def _is_money_annotation(annotation: ast.expr) -> bool:
    return bool(_annotation_names(annotation) & MONEY_PATH_TYPES)


def _names_of(target: ast.expr) -> Iterator[str]:
    """Every bound :class:`ast.Name` id under an assignment target."""
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            yield from _names_of(element)
    elif isinstance(target, ast.Starred):
        yield from _names_of(target.value)


# --- the scanner ------------------------------------------------------------


class _Analyzer:
    """Intraprocedural money-path float taint analysis over one module."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self._findings: list[Finding] = []

    def run(self, tree: ast.Module) -> list[Finding]:
        self._analyze_scope(list(tree.body), params=())
        # Deterministic, source-ordered output regardless of walk order.
        unique = {(f.line, f.col, f.rule): f for f in self._findings}
        return sorted(unique.values(), key=lambda f: (f.line, f.col, f.rule))

    # -- scope walking -------------------------------------------------------

    def _analyze_scope(
        self,
        roots: list[ast.expr | ast.stmt],
        params: Iterable[str],
        return_ann: ast.expr | None = None,
    ) -> None:
        tainted = self._tainted_names(roots, params)
        for node in self._local_nodes(roots):
            self._check_sink(node, tainted, return_ann)
        for scope in self._nested_scopes(roots):
            self._enter(scope)

    def _enter(self, scope: ast.AST) -> None:
        if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._analyze_scope(list(scope.body), self._float_params(scope.args), scope.returns)
        elif isinstance(scope, ast.ClassDef):
            self._analyze_scope(list(scope.body), ())
        elif isinstance(scope, ast.Lambda):
            self._analyze_scope([scope.body], self._float_params(scope.args))

    def _local_nodes(self, roots: Iterable[ast.AST]) -> Iterator[ast.AST]:
        """Every node in the subtrees of ``roots`` that belongs to this scope —
        never descending into a nested function, class, or lambda."""
        stack: list[ast.AST] = [r for r in roots if not isinstance(r, _SCOPE_NODES)]
        while stack:
            node = stack.pop()
            yield node
            for child in ast.iter_child_nodes(node):
                if isinstance(child, _SCOPE_NODES):
                    continue
                stack.append(child)

    def _nested_scopes(self, roots: Iterable[ast.AST]) -> list[ast.AST]:
        """The immediate nested scopes reachable without crossing another scope."""
        found: list[ast.AST] = []
        stack: list[ast.AST] = list(roots)
        while stack:
            node = stack.pop()
            if isinstance(node, _SCOPE_NODES):
                found.append(node)
                continue
            stack.extend(ast.iter_child_nodes(node))
        return found

    @staticmethod
    def _float_params(args: ast.arguments) -> list[str]:
        annotated = (
            *args.posonlyargs,
            *args.args,
            *args.kwonlyargs,
            args.vararg,
            args.kwarg,
        )
        return [
            arg.arg
            for arg in annotated
            if arg is not None
            and arg.annotation is not None
            and _is_float_annotation(arg.annotation)
        ]

    # -- taint set -----------------------------------------------------------

    def _tainted_names(self, roots: Iterable[ast.AST], params: Iterable[str]) -> set[str]:
        roots = list(roots)
        tainted: set[str] = set(params)
        changed = True
        while changed:
            changed = False
            for node in self._local_nodes(roots):
                for name in self._assigned_taints(node, tainted):
                    if name not in tainted:
                        tainted.add(name)
                        changed = True
        return tainted

    def _assigned_taints(self, node: ast.AST, tainted: set[str]) -> Iterator[str]:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                yield from self._bind(target, node.value, tainted)
        elif isinstance(node, ast.AnnAssign):
            if _is_float_annotation(node.annotation):
                yield from _names_of(node.target)
            if node.value is not None:
                yield from self._bind(node.target, node.value, tainted)
        elif isinstance(node, ast.AugAssign):
            if self._is_tainted(node.value, tainted) or (
                isinstance(node.target, ast.Name) and node.target.id in tainted
            ):
                yield from _names_of(node.target)
        elif isinstance(node, ast.NamedExpr) and self._is_tainted(node.value, tainted):
            yield from _names_of(node.target)

    def _bind(self, target: ast.expr, value: ast.expr, tainted: set[str]) -> Iterator[str]:
        if isinstance(target, (ast.Tuple, ast.List)):
            if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(target.elts):
                for element_target, element_value in zip(target.elts, value.elts, strict=True):
                    yield from self._bind(element_target, element_value, tainted)
            elif self._is_tainted(value, tainted):
                yield from _names_of(target)
        elif self._is_tainted(value, tainted):
            yield from _names_of(target)

    # -- taint of an expression ----------------------------------------------

    def _is_tainted(self, node: ast.expr, tainted: set[str]) -> bool:
        if isinstance(node, ast.Constant):
            # A ``bool`` literal is int-typed, not float, so it is never a source.
            return isinstance(node.value, float)
        if isinstance(node, ast.Name):
            return node.id in tainted
        if isinstance(node, ast.NamedExpr):
            return self._is_tainted(node.value, tainted)
        if isinstance(node, ast.BinOp):
            return self._is_tainted(node.left, tainted) or self._is_tainted(node.right, tainted)
        if isinstance(node, (ast.UnaryOp, ast.Starred, ast.Await)):
            return self._is_tainted(
                node.operand if isinstance(node, ast.UnaryOp) else node.value, tainted
            )
        if isinstance(node, ast.BoolOp):
            return any(self._is_tainted(value, tainted) for value in node.values)
        if isinstance(node, ast.IfExp):
            return self._is_tainted(node.body, tainted) or self._is_tainted(node.orelse, tainted)
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return any(self._is_tainted(element, tainted) for element in node.elts)
        if isinstance(node, ast.Dict):
            return any(self._is_tainted(value, tainted) for value in node.values)
        if isinstance(node, (ast.Subscript, ast.Attribute)):
            return self._is_tainted(node.value, tainted)
        if isinstance(node, ast.Call):
            return self._call_is_tainted(node, tainted)
        return False

    def _call_is_tainted(self, node: ast.Call, tainted: set[str]) -> bool:
        tail = _callee_tail(node.func)
        owner = _owner_tail(node.func)
        if tail in EXACT_CLEANSERS:
            # Decimal(...)/Fraction(...) yield an exact value, clearing the taint —
            # but only when no argument is itself a binary float. Decimal(px) and
            # Fraction(px) capture the float's binary error verbatim, so the taint
            # survives; Decimal(str(x)) and Decimal(an_int) are exact.
            return any(self._preserves_binary_float(arg, tainted) for arg in node.args) or any(
                self._preserves_binary_float(kw.value, tainted) for kw in node.keywords
            )
        if tail == BOUNDARY_METHOD and owner in MONEY_PATH_TYPES:
            # A sanctioned qmf.core from_float yields a Result value, not a float.
            # from_float on any other receiver launders nothing (falls through).
            return False
        if tail == "float":
            return True
        if tail in MONEY_PATH_TYPES:
            return False
        if tail == "try_create" and owner in MONEY_PATH_TYPES:
            return False
        return any(self._is_tainted(arg, tainted) for arg in node.args) or any(
            self._is_tainted(kw.value, tainted) for kw in node.keywords
        )

    def _preserves_binary_float(self, node: ast.expr, tainted: set[str]) -> bool:
        """Does ``node`` hand a binary float — its representation error intact — to
        a wrapping ``Decimal``/``Fraction``?

        A stringify call (``str``/``repr``/``format``/``ascii``) breaks the chain:
        ``Decimal(str(x))`` reparses decimal text, so its argument is not a binary
        float. Every other float-tainted argument preserves the binary error and
        keeps the taint alive.
        """
        if isinstance(node, ast.Call) and _callee_tail(node.func) in STRINGIFIERS:
            return False
        return self._is_tainted(node, tainted)

    # -- sinks ---------------------------------------------------------------

    def _check_sink(self, node: ast.AST, tainted: set[str], return_ann: ast.expr | None) -> None:
        if isinstance(node, ast.Call):
            self._check_call(node, tainted)
        elif (
            isinstance(node, ast.AnnAssign)
            and node.value is not None
            and _is_money_annotation(node.annotation)
            and self._is_tainted(node.value, tainted)
        ):
            self._flag(
                node, RULE_CONSTRUCTION, "a binary float is bound to a money-path-typed target"
            )
        elif (
            isinstance(node, ast.Return)
            and return_ann is not None
            and node.value is not None
            and _is_money_annotation(return_ann)
            and self._is_tainted(node.value, tainted)
        ):
            self._flag(node, RULE_CONSTRUCTION, "a binary float is returned as a money-path value")

    def _check_call(self, node: ast.Call, tainted: set[str]) -> None:
        tail = _callee_tail(node.func)
        owner = _owner_tail(node.func)
        if tail == BOUNDARY_METHOD and owner in MONEY_PATH_TYPES:
            # The undeclared-rounding rule guards the sanctioned qmf.core boundary
            # only. from_float on any other receiver is an ordinary call whose
            # float taint is caught downstream at the real money-path sink.
            value_arg = self._arg(node, 0, "value")
            if (
                value_arg is not None
                and self._is_tainted(value_arg, tainted)
                and not self._declares_rounding(node)
            ):
                self._flag(
                    node,
                    RULE_UNDECLARED_BOUNDARY,
                    "a binary float crosses a from_float boundary without a declared rounding mode",
                )
            return
        type_name: str | None = None
        if tail in MONEY_PATH_TYPES:
            type_name = tail
        elif tail == "try_create" and owner in MONEY_PATH_TYPES:
            type_name = owner
        if type_name is None:
            return
        for index, keyword in _VALUE_ARGS[type_name]:
            arg = self._arg(node, index, keyword)
            if arg is not None and self._is_tainted(arg, tainted):
                self._flag(
                    node,
                    RULE_CONSTRUCTION,
                    f"a binary float reaches the {type_name} money-path value",
                )
                return

    @staticmethod
    def _arg(node: ast.Call, index: int, keyword: str) -> ast.expr | None:
        if not any(isinstance(arg, ast.Starred) for arg in node.args) and index < len(node.args):
            return node.args[index]
        for kw in node.keywords:
            if kw.arg == keyword:
                return kw.value
        return None

    @staticmethod
    def _declares_rounding(node: ast.Call) -> bool:
        for kw in node.keywords:
            if kw.arg is None:
                # A ``**kwargs`` unpack might carry the rounding mode; do not flag.
                return True
            if kw.arg == ROUNDING_KEYWORD:
                value = kw.value
                declares_none = isinstance(value, ast.Constant) and value.value is None
                return not declares_none
        return False

    def _flag(self, node: ast.expr | ast.stmt, rule: str, detail: str) -> None:
        self._findings.append(
            Finding(self.filename, node.lineno, node.col_offset + 1, rule, detail)
        )


# --- public entry points ----------------------------------------------------


def scan_source(source: str, filename: str) -> list[Finding]:
    """Scan one module's source. Unparseable source is itself a finding — a
    fail-closed gate must not silently pass a file it could not inspect (ruff owns
    syntax, but the gate never fails open)."""
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
    return _Analyzer(filename).run(tree)


def scan_file(path: Path, *, root: Path = ROOT) -> list[Finding]:
    """Scan one file, reporting its path relative to ``root``.

    An unreadable file (a read or decode error) is itself a finding, not silence: a
    fail-closed gate must not pass a file it could not inspect."""
    try:
        rel = path.resolve().relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
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
        sys.stdout.write("money-path-scan: FAIL - binary float on the money path:\n")
        for finding in findings:
            sys.stdout.write(f"  {finding.render()}\n")
        return 1
    sys.stdout.write(f"money-path-scan: clean ({', '.join(SCAN_ROOTS)}).\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
