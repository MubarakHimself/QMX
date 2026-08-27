"""L0 static/structural gates over the source (read-only evidence).

R2/R3/R15/R17/R18 have a structural face: the pure library writes nothing, all
ledger/log writes originate at the composition root, nothing below the root
spawns a process, there is no Ray/daemon runtime platform, and the impure
package holds no module-global mutable state. Each gate names the concrete
counter-case that would fail it; a real violation is a FINDING, not a mistuned
test.

R-017 gate (T-15.2-f): no throughput/latency/concurrency-count literal is a
governor pass criterion — the "12-14 concurrent" figure is a motivating
reference only, budgets resolve from registry keys.
"""

from __future__ import annotations

import ast
from pathlib import Path

import qmb

SRC = Path(qmb.__file__).resolve().parent
ORCH = SRC / "orchestrator"
LEDGER = SRC / "ledger"
RUNLOOP = SRC / "runloop"

_WRITE_TOKENS = (
    "open_write_handle",
    "append_bytes_no_follow",
    "write_bytes_exclusive_no_follow",
    "os.fsync",
    "O_WRONLY",
    "O_APPEND",
)


def _pyfiles(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*.py") if "__pycache__" not in p.parts)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# -- T-15.0-purity [R2, R17] -------------------------------------------------
def test_run_loop_surface_writes_nothing():
    """The pure run-loop surface performs no ledger/log/file write.

    Counter-case that FAILS: loop.py (where run() lives) or observe.py opening a
    file for write, calling fsync, or importing a write primitive. Then a write
    would escape the pure run() and B-4 would be broken.
    """
    offenders: list[str] = []
    for path in _pyfiles(RUNLOOP):
        body = _text(path)
        for token in _WRITE_TOKENS:
            if token in body:
                offenders.append(f"{path.name}:{token}")
    assert offenders == [], (
        "the pure run-loop surface must perform no write; found write primitives: "
        f"{offenders}"
    )


# -- T-15.0-writer-ownership [R2, R15, R18] ----------------------------------
def test_per_run_log_write_primitive_only_at_composition_root():
    """The per-run log write handle (open_write_handle) is used ONLY under orchestrator/.

    Counter-case that FAILS: any module outside orchestrator/ opening the log
    write handle — a log write below the composition root (R18).
    Note: the generic archive primitives (append_bytes_no_follow /
    write_bytes_exclusive_no_follow) are legitimately reused by data/ for the
    RAW DATA ARCHIVE (Epic 18/23), which is a different concern from the ledger
    and the per-run log; the ledger append is checked separately below.
    """
    users: list[str] = []
    for path in _pyfiles(SRC):
        if "open_write_handle" in _text(path):
            users.append(str(path.relative_to(SRC)).replace("\\", "/"))
    assert all(u.startswith("orchestrator/") for u in users), (
        f"open_write_handle (per-run log write) must live only under orchestrator/; users: {users}"
    )


def test_ledger_fragment_written_only_by_orchestrator_ledger():
    """The ledger fragment sink (LedgerSink append) lives ONLY in orchestrator/ledger.py.

    Counter-case that FAILS: another module defining a LedgerSink append or
    writing the ``ledger.jsonl`` fragment — a second, non-composition-root
    ledger writer (R15 "written ONLY by the orchestrator").
    """
    frag_users: list[str] = []
    for path in _pyfiles(SRC):
        body = _text(path)
        if 'FRAGMENT_FILENAME: Final[str] = "ledger.jsonl"' in body or "class LedgerSink" in body:
            frag_users.append(str(path.relative_to(SRC)).replace("\\", "/"))
    assert frag_users == ["orchestrator/ledger.py"], (
        f"the ledger fragment writer must be the sole orchestrator/ledger.py sink; found: {frag_users}"
    )


# -- T-15.0-no-spawn-below-root [R2] -----------------------------------------
def test_process_spawn_only_at_composition_root():
    """No module below the composition root spawns a process/thread.

    Counter-case that FAILS: any module outside orchestrator/ importing
    subprocess / multiprocessing / threading — concurrency owned below the root
    (AD-15 says the library spawns nothing).
    """
    spawners: list[str] = []
    for path in _pyfiles(SRC):
        rel = str(path.relative_to(SRC)).replace("\\", "/")
        if rel.startswith("orchestrator/"):
            continue
        body = _text(path)
        for token in ("import subprocess", "import multiprocessing", "import threading"):
            if token in body:
                spawners.append(f"{rel}:{token}")
    assert spawners == [], f"only the composition root may spawn; found below-root spawners: {spawners}"


# -- T-15.0-no-runtime-platform [R3] -----------------------------------------
def test_no_ray_no_daemon_runtime_platform():
    """No Ray import, no daemonised runtime anywhere in qmb.

    Counter-case that FAILS: an ``import ray`` / ``from ray`` or a daemon thread
    start — a required runtime platform the spec forbids (sandbox and laptop
    must run the same bare uv-installed package).
    """
    ray_imports: list[str] = []
    daemons: list[str] = []
    for path in _pyfiles(SRC):
        body = _text(path)
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ray") or stripped.startswith("from ray"):
                ray_imports.append(str(path.relative_to(SRC)))
            if "daemon=True" in stripped:
                daemons.append(str(path.relative_to(SRC)))
    assert ray_imports == [], f"no Ray runtime is permitted; found: {ray_imports}"
    assert daemons == [], f"no daemonised thread is permitted; found: {daemons}"


# -- T-15.0-state [cross-cutting; Consistency Conventions] -------------------
def test_no_module_global_mutable_state_in_impure_package():
    """orchestrator/ and ledger/ hold no module-global mutable container state.

    Impurity lives in explicit context objects / injected sinks (DEC-0161).
    Counter-case that FAILS: a module-level ``= []`` / ``= {}`` / ``= set()``
    (or list()/dict()/set() call) bound to a non-Final name — shared mutable
    state two concurrent runs could fight over.
    """
    offenders: list[str] = []
    for path in _pyfiles(ORCH) + _pyfiles(LEDGER):
        tree = ast.parse(_text(path))
        for node in tree.body:
            targets: list[ast.expr] = []
            annotated_final = False
            if isinstance(node, ast.Assign):
                targets = node.targets
                value = node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets = [node.target]
                value = node.value
                ann = node.annotation
                annotated_final = "Final" in ast.dump(ann)
            else:
                continue
            if annotated_final:
                continue
            is_mutable = isinstance(value, (ast.List, ast.Dict, ast.Set)) or (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id in {"list", "dict", "set"}
            )
            if not is_mutable:
                continue
            for tgt in targets:
                # __all__ and other dunder export declarations are static
                # module conventions, not shared mutable RUN state (DEC-0161).
                if isinstance(tgt, ast.Name) and not (
                    tgt.id.startswith("__") and tgt.id.endswith("__")
                ):
                    offenders.append(f"{path.name}:{tgt.id}")
    assert offenders == [], (
        f"the impure package must hold no module-global mutable state; found: {offenders}"
    )


# -- T-15.2-f [R8, R-017] no perf/count literal is a governor gate -----------
def test_governor_has_no_invented_budget_literal():
    """No 12/13/14 concurrency literal is a governor admission criterion (R-017).

    The governor admits by min(cpu, memory) read from registry keys; the
    "12-14 concurrent" figure is a motivating reference under AD-13, never a gate.
    Counter-case that FAILS: a numeric comparison against 12/13/14 in an
    admission/branch expression, or a baked default budget.
    """
    governor_src = _text(ORCH / "governor.py")
    tree = ast.parse(governor_src)
    bad_comparisons: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            for operand in operands:
                if isinstance(operand, ast.Constant) and operand.value in (12, 13, 14):
                    bad_comparisons.append(ast.dump(node))
    assert bad_comparisons == [], (
        f"no 12-14 concurrency literal may be an admission comparison; found: {bad_comparisons}"
    )
    # The motivating figure surfaces only as a documented not-a-budget marker,
    # not as an admission number.
    assert "not-a-validated-budget" in governor_src


def test_governor_refuses_to_run_without_declared_budgets():
    """Budgets come from registry keys, never a baked default (R-017 behavioural face).

    Constructing a governor with no declared cpu/memory budget is REFUSED, not
    silently defaulted to an invented number. Counter-case that FAILS: a spine
    default budget would let ``try_create()`` succeed with no declared values.
    """
    from qmf.core.refusal import is_refusal

    from qmb.orchestrator import ResourceGovernor

    from _e15 import REFUSAL_REGISTER  # noqa: PLC0415

    refused = ResourceGovernor.try_create()
    assert is_refusal(refused), "no-budget governor must refuse (no spine default)"
    assert refused.category.value in REFUSAL_REGISTER
