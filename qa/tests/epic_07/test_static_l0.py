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


def test_s1_no_static_vendor_import_crosses_module_top_level() -> None:
    """talib is resolved by name at call time, never statically imported (so a missing
    reference is a returned refusal, not an import error). A bare `import talib` would fail."""
    roots = _imported_roots()
    assert "talib" not in roots, "the reference must be imported lazily by name, not statically"


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
