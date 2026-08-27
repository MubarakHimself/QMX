"""Epic 14 · Group I — static/structural gates + poisoned-clock proof (L0, R1/R22/R32).

T-14.0-imports [R1]: no module below the composition root (runloop/) imports a
system-clock source. T-14.0-state [R32]: no module-global MUTABLE state anywhere
in runloop/. T-14.0-protocol [R22]: fill/slippage/cost are three distinct
typing.Protocol seams. T-14.1-g [R1]: a poisoned system clock is never touched
by a full replay slice sequence.
"""

from __future__ import annotations

import ast
import time
from pathlib import Path

from _e14 import inst, ok, slices

from qmb.config import CLOCK_REPLAY
from qmb.runloop import FrontierClock, run

_RUNLOOP = Path(__file__).resolve().parents[3] / "qmb" / "src" / "qmb" / "runloop"
_MODULES = sorted(p for p in _RUNLOOP.glob("*.py"))

# System-clock sources that must never appear below the composition root (AR-16).
_BANNED_IMPORTS = {"time", "datetime"}
_BANNED_CALLS = {"perf_counter", "monotonic", "process_time", "now", "utcnow", "today"}


def test_modules_present() -> None:
    names = {p.name for p in _MODULES}
    assert {"loop.py", "bars.py", "frontier.py", "warmup.py", "observe.py"} <= names


# --- T-14.0-imports (L0) no system-clock import in runloop/ [R1] --------------
def test_t140imports_no_system_clock_source() -> None:
    offenders: list[str] = []
    for path in _MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in _BANNED_IMPORTS:
                        offenders.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root in _BANNED_IMPORTS:
                    offenders.append(f"{path.name}: from {node.module} import ...")
            elif isinstance(node, ast.Attribute) and node.attr in {"perf_counter", "process_time"}:
                offenders.append(f"{path.name}: .{node.attr}()")
    assert offenders == [], offenders


# --- T-14.0-state (L0) no module-global mutable state in runloop/ [R32] --------
def test_t140state_no_module_global_mutable_state() -> None:
    offenders: list[str] = []
    mutable_ctor = {"list", "dict", "set", "bytearray", "defaultdict", "Counter", "deque"}
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
            # __all__ is the conventional export manifest (a list by Python
            # convention), not mutable program state; it is not what R32 bans.
            names = [
                t.id
                for t in targets
                if isinstance(t, ast.Name) and not (t.id.startswith("__") and t.id.endswith("__"))
            ]
            if not names:
                continue
            if isinstance(value, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)):
                offenders.append(f"{path.name}: {names} = <mutable literal>")
            elif isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
                if value.func.id in mutable_ctor:
                    offenders.append(f"{path.name}: {names} = {value.func.id}(...)")
    assert offenders == [], offenders


# --- T-14.0-protocol (L0) fill/slippage/cost are three distinct Protocols [R22]
def test_t140protocol_three_distinct_typing_protocols() -> None:
    from qmb.execution.ports import CostPort, FillPort, FinancingPort, SlippagePort, ports_identity

    ports = (FillPort, SlippagePort, CostPort)
    for port in ports:
        assert getattr(port, "_is_protocol", False) is True, f"{port.__name__} is not a Protocol"
    assert len({id(p) for p in ports}) == 3
    assert FinancingPort not in ports and getattr(FinancingPort, "_is_protocol", False) is True
    roles = ports_identity()["port_roles"]
    assert roles[:3] == ("fill", "slippage", "cost")


# --- T-14.1-g (L2) a poisoned system clock is never touched [R1] --------------
def test_t141g_poisoned_system_clock_never_touched(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def _poison(*_args: object, **_kwargs: object) -> float:
        raise AssertionError("runloop touched the system clock below the composition root")

    monkeypatch.setattr(time, "time", _poison)
    monkeypatch.setattr(time, "monotonic", _poison)
    monkeypatch.setattr(time, "perf_counter", _poison)
    clock = ok(FrontierClock.try_create(boot_epoch_id="boot", clock_binding=CLOCK_REPLAY))
    # A full replay slice sequence completes without ever reading the poisoned clock.
    outcome = ok(run(slices=slices(("eurusd",), n=3), stream_set=("eurusd",), clock=clock))
    assert outcome.data_points_processed == 3
    assert inst().value_ns > 0  # sanity: fixtures still build
