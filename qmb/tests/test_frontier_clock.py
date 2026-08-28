"""Story 14.1 — the injected frontier clock (AR-16, B-2, FR-037, SC-06)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

from qmb.config import CLOCK_REPLAY, CLOCK_SIMULATED
from qmb.doors import api
from qmb.runloop import (
    CLOCK_DOES_NOT_CHOOSE_WORLD,
    FrontierClock,
    StreamNextEmit,
    advance_frontier,
    as_wall_replay_instant,
    frontier_clock_name,
    loop_identity,
    min_next_emit,
    read_frontier,
    script_replay_clock,
)
from qmf.core.chrono import Clock, DataDrivenClock, Instant, MonotonicReading
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SRC = Path(__file__).resolve().parents[1] / "src" / "qmb"
_RUNLOOP = _SRC / "runloop"
_SYSTEM_CLOCK_MODULES = frozenset({"time", "datetime", "uuid", "calendar"})
_SYSTEM_CLOCK_ATTRS = frozenset(
    {
        "time",
        "monotonic",
        "perf_counter",
        "now",
        "utcnow",
        "today",
        "uuid1",
    }
)


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _stream(stream_id: str, next_ns: int | None) -> StreamNextEmit:
    nxt = None if next_ns is None else _instant(next_ns)
    return _ok(StreamNextEmit.try_create(stream_id, nxt))


def test_frontier_clock_is_qmf_core_clock_protocol() -> None:
    assert frontier_clock_name() == "qmf.core.chrono.Clock"
    assert qmb.frontier_clock_name() == frontier_clock_name()
    clock = _ok(
        FrontierClock.try_create(
            boot_epoch_id="boot-1",
            clock_binding=CLOCK_REPLAY,
            initial=_instant(),
            monotonic_ns=(1,),
        )
    )
    assert isinstance(clock, Clock)
    typed: Clock = clock
    assert typed.boot_epoch_id == "boot-1"
    assert _ok(typed.wall_now()).value_ns == _NS
    assert isinstance(_ok(typed.monotonic_now()), MonotonicReading)


def test_injected_clock_is_used_including_data_driven_clock() -> None:
    scripted: Clock = script_replay_clock(
        boot_epoch_id="boot-script",
        wall_instants=(_instant(10), _instant(20)),
        monotonic_ns=(1, 2),
    )
    assert isinstance(scripted, DataDrivenClock)
    assert _ok(read_frontier(scripted)).value_ns == 10
    assert _ok(read_frontier(scripted)).value_ns == 20

    frontier = _ok(FrontierClock.try_create(boot_epoch_id="boot-2", clock_binding=CLOCK_REPLAY))
    first = _ok(frontier.advance((_stream("a", _NS + 5), _stream("b", _NS + 9))))
    assert _ok(read_frontier(frontier)).value_ns == first.value_ns == _NS + 5


def test_runloop_source_never_reads_system_clock() -> None:
    offenders: list[str] = []
    for path in sorted(_RUNLOOP.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".", 1)[0]
                    if root in _SYSTEM_CLOCK_MODULES:
                        offenders.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".", 1)[0]
                if root in _SYSTEM_CLOCK_MODULES:
                    offenders.append(f"{path.name}: from {node.module}")
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id in _SYSTEM_CLOCK_MODULES and node.attr in _SYSTEM_CLOCK_ATTRS:
                    offenders.append(f"{path.name}: {node.value.id}.{node.attr}")
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in {"uuid1"}
            ):
                offenders.append(f"{path.name}: uuid1()")
    assert offenders == []


def test_min_next_emit_pull_is_deterministic() -> None:
    streams = (
        _stream("eurusd", _NS + 30),
        _stream("gbpusd", _NS + 10),
        _stream("usdjpy", _NS + 20),
        _stream("done", None),
    )
    first = _ok(min_next_emit(streams))
    second = _ok(min_next_emit(streams))
    assert first.value_ns == second.value_ns == _NS + 10
    reversed_order = (
        _stream("usdjpy", _NS + 20),
        _stream("done", None),
        _stream("gbpusd", _NS + 10),
        _stream("eurusd", _NS + 30),
    )
    assert _ok(min_next_emit(reversed_order)).value_ns == _NS + 10


def test_advance_frontier_refuses_rewind_and_allows_equal() -> None:
    current = _instant(_NS + 100)
    advanced = _ok(
        advance_frontier(
            current,
            (_stream("a", _NS + 150), _stream("b", _NS + 200)),
        )
    )
    assert advanced.value_ns == _NS + 150

    equal = _ok(advance_frontier(current, (_stream("a", _NS + 100),)))
    assert equal.value_ns == current.value_ns

    rewind = advance_frontier(current, (_stream("a", _NS + 50), _stream("b", _NS + 80)))
    assert is_refusal(rewind)
    assert rewind.category is RefusalCategory.INVALID_INPUT
    assert rewind.context["field"] == "next_emit"

    initial = _ok(advance_frontier(None, (_stream("a", _NS + 7), _stream("b", _NS + 3))))
    assert initial.value_ns == _NS + 3


def test_frontier_clock_advance_is_monotone_pure_of_data_cursor() -> None:
    clock = _ok(FrontierClock.try_create(boot_epoch_id="boot-3"))
    assert clock.clock_binding == CLOCK_REPLAY
    assert clock.current is None
    t1 = _ok(clock.advance((_stream("s1", _NS + 1), _stream("s2", _NS + 5))))
    t2 = _ok(clock.advance((_stream("s1", _NS + 1), _stream("s2", _NS + 5))))
    t3 = _ok(clock.advance((_stream("s1", None), _stream("s2", _NS + 5))))
    assert t1.value_ns == _NS + 1
    assert t2.value_ns == _NS + 1
    assert t3.value_ns == _NS + 5
    assert _ok(clock.wall_now()).value_ns == _NS + 5
    refused = clock.advance((_stream("s2", _NS + 4),))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_monotonic_as_wall_is_refused() -> None:
    reading = _ok(MonotonicReading.try_create(42, "boot-1"))
    refused = as_wall_replay_instant(reading, clock_binding=CLOCK_REPLAY)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "candidate"

    stream = StreamNextEmit.try_create("s", reading)
    assert is_refusal(stream)
    assert stream.context["field"] == "next_emit"


def test_simulated_instant_as_wall_replay_refused_until_gap_0048() -> None:
    instant = _instant()
    refused = as_wall_replay_instant(instant, clock_binding=CLOCK_SIMULATED)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["gap"] == "GAP-0048"

    seam = _ok(
        FrontierClock.try_create(
            boot_epoch_id="boot-sim",
            clock_binding=CLOCK_SIMULATED,
        )
    )
    assert seam.clock_binding == CLOCK_SIMULATED
    advanced = seam.advance((_stream("a", _NS),))
    assert is_refusal(advanced)
    assert advanced.category is RefusalCategory.POLICY_REJECTION
    assert advanced.context["gap"] == "GAP-0048"

    seeded = FrontierClock.try_create(
        boot_epoch_id="boot-sim",
        clock_binding=CLOCK_SIMULATED,
        initial=instant,
    )
    assert is_refusal(seeded)
    assert seeded.context["gap"] == "GAP-0048"


def test_clock_does_not_choose_world() -> None:
    assert CLOCK_DOES_NOT_CHOOSE_WORLD is True
    assert qmb.CLOCK_DOES_NOT_CHOOSE_WORLD is True
    identity = loop_identity()
    assert identity["clock_chooses_world"] is False
    assert identity["clock_does_not_choose_world"] is True
    assert "world" not in identity
    clock = _ok(FrontierClock.try_create(boot_epoch_id="boot-w"))
    assert not hasattr(clock, "world")


def test_loop_never_forked_same_read_path() -> None:
    replay = script_replay_clock(
        boot_epoch_id="boot-r",
        wall_instants=(_instant(1),),
        monotonic_ns=(0,),
    )
    frontier = _ok(
        FrontierClock.try_create(
            boot_epoch_id="boot-f",
            initial=_instant(1),
            monotonic_ns=(0,),
        )
    )
    assert _ok(read_frontier(replay)).value_ns == _ok(read_frontier(frontier)).value_ns == 1
    assert api.FrontierClock is qmb.FrontierClock
    assert api.read_frontier is qmb.read_frontier
    assert api.advance_frontier is qmb.advance_frontier
    assert api.script_replay_clock is qmb.script_replay_clock


def test_frontier_clock_wall_now_requires_advance() -> None:
    # OR-03 / CT-04 (DEC-0109): reading the clock before the frontier has advanced (and
    # reading a spent monotonic script) is a RETURNED `unavailable dependency` refusal,
    # never a raise -- value-or-refusal holds at the clock seam. The category is
    # asserted, not the message prose.
    clock = _ok(FrontierClock.try_create(boot_epoch_id="boot-empty"))
    unadvanced = clock.wall_now()
    assert is_refusal(unadvanced)
    assert unadvanced.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    spent_mono = clock.monotonic_now()
    assert is_refusal(spent_mono)
    assert spent_mono.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_public_exports_surface() -> None:
    assert "FrontierClock" in qmb.__all__
    assert "advance_frontier" in qmb.__all__
    assert "as_wall_replay_instant" in qmb.__all__
    assert "min_next_emit" in qmb.__all__
    assert "read_frontier" in qmb.__all__
    assert "script_replay_clock" in qmb.__all__
    assert "StreamNextEmit" in qmb.__all__
    assert api.CLOCK_DOES_NOT_CHOOSE_WORLD is qmb.CLOCK_DOES_NOT_CHOOSE_WORLD
