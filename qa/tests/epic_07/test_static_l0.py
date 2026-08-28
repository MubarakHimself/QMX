"""L0 static / structural gates for Epic 7 (qmf-indicators).

T7-S1..S5 — default-deny import graph; no bare "timeframe"; no trading-school name;
vendor-neutral public surface; pure-computation foundation. These assert structural
laws the acceptance tests cannot reach; each names its falsifying counter-case.
"""

from __future__ import annotations

import ast
import inspect
import os
import re
import sys

import qmf.indicators as pkg

_SRC_DIR = os.path.dirname(inspect.getfile(pkg))


def _source_files() -> list[str]:
    files = [
        os.path.join(_SRC_DIR, name)
        for name in sorted(os.listdir(_SRC_DIR))
        if name.endswith(".py")
    ]
    assert files, f"no source files found under {_SRC_DIR!r}"
    return files


def _imported_roots() -> set[str]:
    """Every top-level module path a static `import`/`from ... import` reaches."""
    roots: set[str] = set()
    for path in _source_files():
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    roots.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                roots.add(node.module)
    return roots


def _is_import_module_call(func: ast.expr) -> bool:
    """True for an `importlib.import_module(...)` or bare `import_module(...)` call target."""
    if isinstance(func, ast.Attribute):
        return func.attr == "import_module"
    if isinstance(func, ast.Name):
        return func.id == "import_module"
    return False


def _dynamic_import_targets() -> set[str]:
    """Every module name reached via `importlib.import_module(...)` in the package source.

    A module resolved by name at call time (never a static `import`) is invisible to an
    AST-root scan — the exact gap QMX-F033 rode in on. This resolves both a direct string
    literal (`import_module("numpy")`, batch.py) and a module-level string constant passed
    by name (`import_module(_REFERENCE_MODULE_NAME)` where `_REFERENCE_MODULE_NAME = "talib"`,
    _reference.py), so a dependency pulled in dynamically is seen exactly as a static import
    would be. A computed (non-constant) argument is skipped — it names no single module."""
    targets: set[str] = set()
    for path in _source_files():
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)
        constants: dict[str, str] = {}
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        constants[target.id] = node.value.value
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
                and isinstance(node.target, ast.Name)
            ):
                constants[node.target.id] = node.value.value
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _is_import_module_call(node.func) and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    targets.add(arg.value)
                elif isinstance(arg, ast.Name) and arg.id in constants:
                    targets.add(constants[arg.id])
    return targets


def _package_pyproject() -> str:
    """The qmf-indicators pyproject.toml, found by walking up from the package source
    (the nearest manifest above src/qmf/indicators/ is the package's own)."""
    here = _SRC_DIR
    for _ in range(10):
        candidate = os.path.join(here, "pyproject.toml")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    raise AssertionError(f"pyproject.toml not found walking up from {_SRC_DIR!r}")


def _distribution_name(spec: str) -> str:
    """The bare distribution name from a PEP 508 dependency spec (drops the version):
    `ta-lib==0.7.1` -> `ta-lib`; `qmf-core` -> `qmf-core`."""
    for sep in ("==", ">=", "<=", "~=", "!=", ">", "<", "[", ";", " "):
        idx = spec.find(sep)
        if idx != -1:
            spec = spec[:idx]
    return spec.strip()


def _declared_distributions() -> set[str]:
    """The distribution names in `[project].dependencies` of qmf-indicators' own pyproject."""
    import tomllib

    with open(_package_pyproject(), "rb") as handle:
        data = tomllib.load(handle)
    deps = data.get("project", {}).get("dependencies", [])
    return {_distribution_name(spec) for spec in deps}


def _canonical(name: str) -> str:
    """A PEP 503-style fold so a distribution name and its import root compare equal:
    lowercased with `-`, `_`, `.` stripped (`ta-lib` -> `talib`; `numpy` -> `numpy`)."""
    return re.sub(r"[-_.]", "", name.lower())


# --- T7-S1: default-deny import graph [R5, AR-06] ---------------------------


def test_s1_static_imports_reach_only_qmf_core_and_own_package() -> None:
    """Counter-case that must fail: a static `from qmf.data import ...` (or any sibling
    roster package) appearing in the source. Only qmf.core and qmf.indicators.* are legal."""
    offenders = [
        root
        for root in _imported_roots()
        if root.split(".")[0] == "qmf"
        and not (root == "qmf.core" or root == "qmf.indicators" or root.startswith("qmf.indicators."))
    ]
    assert offenders == [], f"default-deny violated: qmf sibling imports {offenders!r}"


def test_s1_every_reached_third_party_module_is_declared() -> None:
    """AR-06 default-deny [R5]: every non-stdlib, non-first-party module the package reaches
    — by static `import`/`from` AND by `importlib.import_module` (string literal or module-level
    string constant) — must be declared in qmf-indicators' OWN pyproject, never merely satisfied
    transitively through another dependency's closure.

    This widens the T7-S1 scanner past its `root.split(".")[0] == "qmf"` blind spot: the old
    reach analysis filtered to `qmf` roots, so a non-`qmf` undeclared import was structurally
    invisible, and an AST-root scan saw no dynamic import at all.

    Counter-case that must fail (and did, as QMX-F033): `batch.py` resolves
    `importlib.import_module("numpy")` on the compute path while the pyproject declares only
    `qmf-core` + `ta-lib`; numpy arrives transitively via ta-lib but is not declared. The
    isolated-build smoke (AR-18) cannot catch it — ta-lib pulls numpy into the isolated env
    regardless — so a missing own-pyproject declaration is a governance/gate defect."""
    reached = {root.split(".")[0] for root in (_imported_roots() | _dynamic_import_targets())}
    third_party = {
        root for root in reached if root != "qmf" and root not in sys.stdlib_module_names
    }
    declared = {_canonical(name) for name in _declared_distributions()}
    undeclared = sorted(root for root in third_party if _canonical(root) not in declared)
    assert undeclared == [], (
        "third-party modules reached but not declared in qmf-indicators' own pyproject "
        f"(AR-06 default-deny; transitive availability is not a declaration): {undeclared!r}"
    )


def test_s1_no_static_vendor_import_crosses_module_top_level() -> None:
    """talib is resolved by name at call time, never statically imported (so a missing
    reference is a returned refusal, not an import error) — but being resolved lazily does
    NOT exempt it from declaration. AR-06 default-deny [R5] requires the lazily-resolved
    vendor to appear in qmf-indicators' own pyproject exactly as a static import would, which
    the widened T7-S1 scanner above now enforces for every dynamically reached module (the
    gap QMX-F033 found for numpy). Counter-cases: a bare `import talib` (would fail), or the
    reference resolved by name yet absent from the declared dependencies."""
    roots = _imported_roots()
    assert "talib" not in roots, "the reference must be imported lazily by name, not statically"
    declared = {_canonical(name) for name in _declared_distributions()}
    assert _canonical("ta-lib") in declared, (
        "the lazily-resolved arithmetic reference (ta-lib) must still be a declared dependency "
        "of qmf-indicators (AR-06 default-deny), not resolved by name alone"
    )


# --- T7-S2: no bare "timeframe" [R13 vocabulary half] -----------------------


def test_s2_no_bare_timeframe_token_in_public_source() -> None:
    """Counter-case: the token `timeframe` used anywhere as an aggregation discriminant.
    BarSpec (registry:barspec_kinds) is the only aggregation vocabulary."""
    pattern = re.compile(r"\btimeframe\b", re.IGNORECASE)
    hits: list[str] = []
    for path in _source_files():
        with open(path, encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, 1):
                if pattern.search(line):
                    hits.append(f"{os.path.basename(path)}:{lineno}: {line.strip()}")
    assert hits == [], f"bare 'timeframe' vocabulary found: {hits!r}"


# --- T7-S3: no trading-school name [R29 school-name half] -------------------

# A fixed lexicon of trading-SCHOOL / methodology names (not mechanical indicator
# abbreviations). CT-16 DEC-0132: school concepts enter only as mechanically stated
# capability terms.
_SCHOOL_NAMES = (
    "wyckoff",
    "elliott",
    "ichimoku",
    "gann",
    "fibonacci",
    "fibo",
    "bollinger",
    "dow theory",
    "harmonic",
    "smart money",
    "order block",
    "fair value gap",
    "ict",
    "supply and demand",
)


def test_s3_no_trading_school_name_in_public_source() -> None:
    """Counter-case: any name from the school-name lexicon in a rule, vocabulary, or
    exported identifier. School concepts must enter only as mechanical capability terms."""
    hits: list[str] = []
    for path in _source_files():
        with open(path, encoding="utf-8") as handle:
            text = handle.read().lower()
        for name in _SCHOOL_NAMES:
            if re.search(rf"\b{re.escape(name)}\b", text):
                hits.append(f"{os.path.basename(path)}: {name!r}")
    assert hits == [], f"trading-school vocabulary found: {hits!r}"


def test_s3_lexicon_is_discriminating_not_vacuous() -> None:
    """Falsifiability guard: the school-name scan can fire — a synthetic string carrying a
    school name is detected. (Proves the S3 assertion is not trivially always-green.)"""
    sample = "this rule uses an elliott wave count"
    assert any(re.search(rf"\b{re.escape(n)}\b", sample) for n in _SCHOOL_NAMES)


# --- T7-S4: vendor-neutral surface [R11 structural half] --------------------


def _annotation_strings() -> list[tuple[str, str]]:
    """Every annotation string on the public (__all__) surface: dataclass field types
    and function signature annotations. Under `from __future__ import annotations` these
    are strings, so a leaked vendor type would appear verbatim as text."""
    import dataclasses

    out: list[tuple[str, str]] = []
    for name in pkg.__all__:
        obj = getattr(pkg, name)
        if dataclasses.is_dataclass(obj) and isinstance(obj, type):
            for field in dataclasses.fields(obj):
                out.append((name, str(field.type)))
        annotations = getattr(obj, "__annotations__", None)
        if isinstance(annotations, dict):
            for key, value in annotations.items():
                out.append((f"{name}.{key}", str(value)))
        if callable(obj) and hasattr(obj, "__annotations__"):
            for key, value in getattr(obj, "__annotations__", {}).items():
                out.append((f"{name}({key})", str(value)))
    return out


def test_s4_no_vendor_type_on_public_signatures() -> None:
    """Counter-case: a public CT-16 signature or dataclass field typed as a talib/TA-Lib
    vendor object. The public surface stays package-neutral."""
    banned = re.compile(r"\btalib\b|ta_lib|TA_Lib|TALib", re.IGNORECASE)
    offenders = [(where, ann) for where, ann in _annotation_strings() if banned.search(ann)]
    assert offenders == [], f"vendor type on public surface: {offenders!r}"


# --- T7-S5: pure-computation foundation [component Foundation; R18 boundary] -


def test_s5_no_async_or_thread_surface() -> None:
    """Counter-case: an `async def`, `import asyncio`, or `import threading` anywhere in
    the package. It is a pure-computation library: no background work, no async API."""
    async_hits: list[str] = []
    for path in _source_files():
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.AsyncFunctionDef, ast.AsyncFor, ast.AsyncWith)):
                async_hits.append(f"{os.path.basename(path)}: async construct")
    roots = _imported_roots()
    assert async_hits == [], f"async surface found: {async_hits!r}"
    assert "asyncio" not in roots, "asyncio must not be imported (pure computation)"
    assert "threading" not in roots, "threading must not be imported (no background work)"


def test_s5_health_is_only_on_the_streaming_stateful_class() -> None:
    """Only the one named stateful class exposes health(); pure batch value types do not
    (AD-14 long-lived state). Counter-case: a pure batch type exposing health()."""
    assert hasattr(pkg.StreamingIndicator, "health")
    for name in ("BatchResult", "IndicatorSeries", "ConfiguredIndicator", "Catalog"):
        obj = getattr(pkg, name)
        assert not hasattr(obj, "health"), f"{name} must not expose health() (not stateful)"


def test_s5_no_module_global_indicator_instance_registry() -> None:
    """Dedup is per-process and application-owned; the package ships no global instance
    registry. Counter-case: building two instances registers them in a package-global that
    can be listed back. Here there is no such retrieval surface."""
    assert not hasattr(pkg, "REGISTRY")
    assert not hasattr(pkg, "INSTANCES")
    # The catalog is explicit-registration and immutable (returned, never a global sink):
    assert not any(
        name.lower() in {"register_global", "scan", "discover", "autoload"} for name in pkg.__all__
    )
