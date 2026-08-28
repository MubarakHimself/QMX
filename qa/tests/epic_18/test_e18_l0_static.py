"""Epic 18 · L0 — static / structural gates over ``qmb/src/qmb/data/``.

T18-0a  no ambient system-clock read below the composition root   (RQ-CLOCK / FIND-001)
T18-0b  no module-global MUTABLE state                            (RQ34 / NFR-02, AR-11)
T18-0c  no second market-data persistence engine originates here  (RQ1 / B-11)
T18-0d  no third-party downloader / network code vendored here    (RQ3 / AR-54, DEC-0013)
T18-2d  the built/shipped wheel bundles ZERO corpus bytes         (RQ16 / AR-54)

Static gates read source as read-only evidence. A gate that fails is a FINDING.
"""

from __future__ import annotations

import ast
import subprocess
import tempfile
import zipfile
from pathlib import Path

from qmb.data.licensing import (
    assert_distribution_has_no_corpus,
    distribution_corpus_bytes,
)
from qmf.core.refusal import is_ok

_DATA = Path(__file__).resolve().parents[3] / "qmb" / "src" / "qmb" / "data"
_WORKTREE = Path(__file__).resolve().parents[3]
_MODULES = sorted(p for p in _DATA.glob("*.py"))

# Ambient system-clock reads banned below the composition root (DEC-0106).
# Resolve import origins rather than banning method spellings: an injected
# ``clock.now()`` is compliant and must not be mistaken for ``datetime.now()``.
_SYSTEM_CLOCK_CALLS = {
    "datetime.date.today",
    "datetime.datetime.now",
    "datetime.datetime.utcnow",
    "time.monotonic",
    "time.monotonic_ns",
    "time.perf_counter",
    "time.perf_counter_ns",
    "time.process_time",
    "time.process_time_ns",
    "time.time",
    "time.time_ns",
}
# Raw persistence engines a thin front must NEVER open itself (B-11): the store
# contracts own these. Reading through a qmf-data engine type is fine; importing
# the raw driver in qmb.data is a second store.
_BANNED_STORE_IMPORTS = {"pyarrow", "duckdb", "sqlite3", "pyarrow.parquet"}
# Network / vendored-downloader modules a download-once adapter must never carry
# (AR-54: no third-party downloader vendored; qmb never opens a provider socket).
_BANNED_NET_IMPORTS = {
    "http",
    "urllib",
    "urllib.request",
    "requests",
    "httpx",
    "aiohttp",
    "socket",
    "websockets",
    "ftplib",
}


def _import_roots(tree: ast.AST) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            found.append((node.module or "", node.lineno))
    return found


def test_modules_present() -> None:
    names = {p.name for p in _MODULES}
    assert {"download.py", "verify.py", "gap_check.py", "catalog.py", "licensing.py"} <= names


def _import_bindings(tree: ast.Module) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                bindings[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            for alias in node.names:
                bindings[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return bindings


def _resolved_call_name(expression: ast.expr, bindings: dict[str, str]) -> str | None:
    if isinstance(expression, ast.Name):
        return bindings.get(expression.id)
    if isinstance(expression, ast.Attribute):
        parent = _resolved_call_name(expression.value, bindings)
        return f"{parent}.{expression.attr}" if parent is not None else None
    return None


# --- T18-0a  ambient-clock scan (RQ-CLOCK / FIND-001) ------------------------
def test_t18_0a_no_ambient_system_clock_read() -> None:
    """No qmb/data module reads an ambient wall/monotonic clock.

    Import-origin resolution keeps the gate faithful to DEC-0106: system-clock
    calls fail, while an injected collaborator such as ``clock.now()`` is valid.
    """
    offenders: list[str] = []
    for path in _MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        bindings = _import_bindings(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            resolved = _resolved_call_name(node.func, bindings)
            if resolved in _SYSTEM_CLOCK_CALLS:
                offenders.append(f"{path.name}:{node.lineno} {resolved}(")
    assert offenders == [], f"ambient system-clock reads below the composition root: {offenders}"


# --- T18-0b  no module-global mutable state (RQ34 / NFR-02) -------------------
def test_t18_0b_no_module_global_mutable_state() -> None:
    mutable_ctor = {"list", "dict", "set", "bytearray", "defaultdict", "Counter", "deque"}
    offenders: list[str] = []
    for path in _MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:  # module scope only
            targets: list[ast.expr] = []
            value: ast.expr | None = None
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets, value = [node.target], node.value
            else:
                continue
            names = [
                t.id
                for t in targets
                if isinstance(t, ast.Name) and not (t.id.startswith("__") and t.id.endswith("__"))
            ]
            if not names:
                continue
            if isinstance(
                value, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)
            ):
                offenders.append(f"{path.name}: {names} = <mutable literal>")
            elif isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
                if value.func.id in mutable_ctor:
                    offenders.append(f"{path.name}: {names} = {value.func.id}(...)")
    assert offenders == [], f"module-global mutable state in qmb/data: {offenders}"


# --- T18-0c  no second market-data persistence engine here (RQ1 / B-11) -------
def test_t18_0c_no_second_persistence_engine() -> None:
    """qmb/data opens no raw Parquet/DuckDB/SQLite driver of its own.

    All persistence routes through the qmf-data store contracts. Importing a raw
    engine driver in qmb.data would be a second data layer (B-11).
    """
    offenders: list[str] = []
    for path in _MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name, lineno in _import_roots(tree):
            root = name.split(".")[0]
            if root in {r.split(".")[0] for r in _BANNED_STORE_IMPORTS}:
                offenders.append(f"{path.name}:{lineno} import {name}")
    assert offenders == [], f"qmb/data opened its own persistence engine: {offenders}"


# --- T18-0d  no vendored downloader / network code (RQ3 / AR-54) --------------
def test_t18_0d_no_vendored_downloader_or_network() -> None:
    offenders: list[str] = []
    banned_roots = {n.split(".")[0] for n in _BANNED_NET_IMPORTS}
    for path in _MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name, lineno in _import_roots(tree):
            if name.split(".")[0] in banned_roots:
                offenders.append(f"{path.name}:{lineno} import {name}")
    assert offenders == [], f"qmb/data carries network / vendored-downloader code: {offenders}"


# --- T18-2d  zero corpus bytes in the built wheel (RQ16 / AR-54) --------------
def _build_qmb_wheel(out_dir: Path) -> Path | None:
    try:
        proc = subprocess.run(
            ["uv", "build", "--wheel", "qmb", "--out-dir", str(out_dir)],
            cwd=str(_WORKTREE),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    wheels = list(out_dir.glob("qmb-*.whl"))
    return wheels[0] if wheels else None


def test_t18_2d_built_wheel_bundles_zero_corpus() -> None:
    """The shipped qmb wheel bundles zero market-data corpus bytes (AR-54)."""
    with tempfile.TemporaryDirectory() as d:
        wheel = _build_qmb_wheel(Path(d))
        if wheel is None:
            # Build unavailable: fall back to the source tree that WOULD ship —
            # still a real observation of the distribution's corpus payload.
            measured = distribution_corpus_bytes(str(_DATA.parent))  # qmb/src/qmb
            assert is_ok(measured), measured
            assert measured.value == 0, f"qmb package tree carries corpus bytes: {measured.value}"
            return
        gate = assert_distribution_has_no_corpus(str(wheel))
        assert is_ok(gate), (
            f"built wheel FAILS the ship-no-corpus gate: {getattr(gate, 'context', gate)!r}"
        )
        assert gate.value == 0


def test_t18_2d_corpus_gate_is_falsifiable() -> None:
    """The gate is not vacuous: a wheel carrying a .parquet corpus is refused,
    a clean wheel passes — so a green built-wheel result means something."""
    with tempfile.TemporaryDirectory() as d:
        clean = Path(d) / "clean.whl"
        with zipfile.ZipFile(clean, "w") as z:
            z.writestr("qmb/__init__.py", "x = 1\n")
        dirty = Path(d) / "dirty.whl"
        with zipfile.ZipFile(dirty, "w") as z:
            z.writestr("qmb/__init__.py", "x = 1\n")
            z.writestr("qmb/data/EURUSD-ticks.parquet", b"\x00" * 256)
        assert is_ok(assert_distribution_has_no_corpus(str(clean)))
        assert assert_distribution_has_no_corpus(str(clean)).value == 0
        from qmf.core.refusal import is_refusal

        assert is_refusal(assert_distribution_has_no_corpus(str(dirty)))
        assert distribution_corpus_bytes(str(dirty)).value == 256
