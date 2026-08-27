"""L2 component/integration: the orchestrator wired to a stub run(), injected
ledger/log sinks, and a scriptable fake process. The abort/cancel/crash matrix
is observed through the REAL ledger fragment directory the test owns.

FLAGSHIP: the exactly-one-line law (R-010) across every terminal cause.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from _e15 import (
    REFUSAL_REGISTER,
    cancelled_token,
    config,
    duration,
    fake_live,
    FakeProcess,
    ledger_line,
    line_count,
    lines_for_role,
    make_ledger,
    ok,
    slices,
)

from qmf.core.refusal import is_ok, is_refusal

from qmb.orchestrator import (
    GovernedRequest,
    LiveSpawn,
    ResourceGovernor,
    collect_run,
    finish_run,
    inject_run_log,
    read_book_bar,
    read_merge_view,
    read_run_log,
    run_directory_name,
    start_run,
)
from qmb.orchestrator.watch import is_aborted_refusal
from qmb.ledger import ROLE_ABORTED, ROLE_CONFIRMATION, ROLE_TRIAL
from qmb.ledger.line import LedgerLine
from qmb.runloop.loop import run
from qmb.runloop.observe import RunLimits, ScriptedLimitProbe
from qmf.core.fingerprint import fingerprint


# ============ Group A — process-per-run & isolation (R1, R2, R4) ============
def test_no_write_escapes_pure_run(tmp_path, monkeypatch):
    """T-15.1-c [R2] The pure run() writes nothing and returns a value.

    Driven in an empty working directory the test owns; run() takes no sink and
    must leave the directory empty. Counter-case that FAILS: run() creating any
    file (a result, a log, a ledger fragment) — a write escaping the pure run().
    """
    workdir = tmp_path / "purity"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    outcome = run(slices=slices(), config=config("purity"))
    assert is_ok(outcome), "the pure run() returns a result-or-refusal value"
    assert list(workdir.iterdir()) == [], "run() must create no file — no write escapes run()"


def test_isolated_output_directories_keyed_by_run_id(tmp_path):
    """T-15.1-f [R1] Distinct run ids get distinct output directory names; the
    same run id spawned twice is refused (two runs never share a writer).

    Counter-case that FAILS: two distinct run ids mapping to one directory name,
    or a second spawn of the same id silently reusing the directory.
    """
    name_a = ok(run_directory_name(config("A").fingerprint))
    name_b = ok(run_directory_name(config("B").fingerprint))
    assert name_a != name_b, "distinct run ids must key distinct output directories"

    out = tmp_path / "out"
    out.mkdir()
    cfg = config("dup")
    first = start_run(config=cfg, slices=slices(), output_root=out)
    assert is_ok(first)
    ok(collect_run(first.value))  # let the child finish
    second = start_run(config=cfg, slices=slices(), output_root=out)
    assert is_refusal(second), "the same run id must not re-open an existing writer directory"
    assert second.category.value in REFUSAL_REGISTER


# ============ Group B — governor enqueue-then-admit (R7) ====================
def test_finish_then_admit_next_queued_run():
    """T-15.2-c [R7] With the governor full, a further submit enqueues; when a
    running slot finishes, exactly the next queued run (FIFO) is admitted and the
    concurrent count never exceeds the bound.

    Counter-case that FAILS: releasing admits more than one, admits out of FIFO
    order, or lets the running count exceed the bound at any instant.
    """
    governor = ok(ResourceGovernor.try_create(cpu_budget=2, memory_budget=100))

    def req(tag: str):
        return ok(GovernedRequest.try_create(ok(fingerprint({"r": tag})), 10, 1))

    first = req("first")
    governor.submit(first)
    governor.submit(req("second"))
    third = governor.submit(req("third"))
    fourth = governor.submit(req("fourth"))
    assert third.value.decision == "queued" and fourth.value.decision == "queued"
    assert governor.running_count == 2

    admitted = ok(governor.release(first.run_id))
    assert len(admitted) == 1, "finishing one run admits exactly one queued run"
    assert admitted[0].run_id.value == req("third").run_id.value, "FIFO: the head is admitted first"
    assert governor.running_count == 2, "the running count never exceeds the min bound"
    assert governor.queue_depth == 1


# ============ Group C — cancel tokens & per-run limits (R9, R10, R12) =======
def test_submitted_run_carries_cancel_token_and_declared_limits(tmp_path):
    """T-15.3-a [R9] A submitted run carries a cancel token and the declared
    per-run time/memory limits (values from the run-config keys).

    Counter-case that FAILS: a spawned run with no cancel token, or limits that
    do not reflect the declared qmb_run_time_limit / qmb_run_memory_limit keys.
    """
    from qmb.runloop.observe import CancelToken, MEMORY_LIMIT_KEY, TIME_LIMIT_KEY

    out = tmp_path / "out"
    out.mkdir()
    cfg = config("limits", **{TIME_LIMIT_KEY: 5_000_000_000, MEMORY_LIMIT_KEY: 512 * 1024 * 1024})
    live = ok(start_run(config=cfg, slices=slices(), output_root=out))
    try:
        assert isinstance(live.cancel, CancelToken), "every submitted run carries a cancel token"
        assert live.limits.time_limit is not None and live.limits.time_limit.value_ns == 5_000_000_000
        assert live.limits.memory_limit_bytes == 512 * 1024 * 1024
    finally:
        ok(collect_run(live))


def test_signalled_cancel_yields_typed_aborted(tmp_path):
    """T-15.3-b [R10] A signalled cancel produces a typed ``aborted`` outcome with
    context, RETURNED not raised.

    Counter-case that FAILS: a completion, a raise, or an outcome whose terminal
    context is not ``aborted``.
    """
    out = tmp_path / "run"
    out.mkdir()
    cfg = config("cancel")
    live = fake_live(
        cfg,
        process=FakeProcess(alive=True),
        cancel=cancelled_token("cancel"),
        output_dir=str(out),
    )
    outcome = collect_run(live)
    assert is_refusal(outcome), "a cancel yields a returned typed refusal"
    assert is_aborted_refusal(outcome), "the terminal context is aborted"
    assert outcome.context.get("cause") == "cancel"


@pytest.mark.parametrize(
    ("cause", "limits", "probe"),
    [
        ("time-limit", RunLimits(time_limit=duration(10)), ScriptedLimitProbe(elapsed_ns=[10**9])),
        ("memory-limit", RunLimits(memory_limit_bytes=1000), ScriptedLimitProbe(memory_bytes=[9000])),
    ],
)
def test_per_run_limit_breach_yields_typed_aborted(tmp_path, cause, limits, probe):
    """T-15.3-c [R10] A per-run time-limit breach and a memory-limit breach each
    yield a typed ``aborted`` outcome with context.

    Counter-case that FAILS: a breach that does not abort (silent overrun) or one
    that raises instead of returning a typed refusal.
    """
    out = tmp_path / cause
    out.mkdir()
    live = fake_live(config(cause), process=FakeProcess(alive=True), limits=limits, probe=probe,
                     output_dir=str(out))
    outcome = collect_run(live)
    assert is_refusal(outcome) and is_aborted_refusal(outcome)
    assert outcome.category.value in REFUSAL_REGISTER


def test_abort_declares_no_partial_governed_result(tmp_path):
    """T-15.3-f [R12] An aborted run writes no partial governed result; the aborted
    ledger line carries no CT-32 fingerprint and the refusal declares
    partial_governed_result=False.

    Counter-case that FAILS: an aborted line carrying a CT-32 result fingerprint,
    or a refusal claiming a partial governed result was emitted.
    """
    out = tmp_path / "run"
    out.mkdir()
    led = tmp_path / "led"
    led.mkdir()
    cfg = config("nopartial")
    sink = make_ledger(led)
    live = fake_live(cfg, process=FakeProcess(alive=True), cancel=cancelled_token("cancel"),
                     output_dir=str(out))
    result = finish_run(live, config=cfg, ledger=sink, role=ROLE_CONFIRMATION)
    assert is_refusal(result)
    assert result.context.get("partial_governed_result") is False
    aborted_lines = lines_for_role(led, ROLE_ABORTED)
    assert len(aborted_lines) == 1
    assert aborted_lines[0].ct32_fingerprint is None, "no partial governed CT-32 result on abort"


# ============ Group D — the one-ledger-line law (R13, R17) — R-010 =========
@pytest.mark.parametrize(
    ("cause", "make"),
    [
        (
            "cancel",
            lambda cfg, out: fake_live(cfg, process=FakeProcess(alive=True),
                                       cancel=cancelled_token("cancel"), output_dir=str(out)),
        ),
        (
            "time-limit",
            lambda cfg, out: fake_live(cfg, process=FakeProcess(alive=True),
                                       limits=RunLimits(time_limit=duration(10)),
                                       probe=ScriptedLimitProbe(elapsed_ns=[10**9]), output_dir=str(out)),
        ),
        (
            "memory-limit",
            lambda cfg, out: fake_live(cfg, process=FakeProcess(alive=True),
                                       limits=RunLimits(memory_limit_bytes=1000),
                                       probe=ScriptedLimitProbe(memory_bytes=[9000]), output_dir=str(out)),
        ),
        (
            "hard-crash",
            lambda cfg, out: fake_live(cfg, process=FakeProcess(alive=False, returncode=1),
                                       output_dir=str(out)),
        ),
    ],
)
def test_exactly_one_ledger_line_across_terminal_cause_matrix(tmp_path, cause, make):
    """T-15.4-a / T-15.4-c [R13, R-010] Every terminal cause appends EXACTLY ONE
    ledger line — an aborted line carrying refusal context — never zero, never two.

    The matrix {cancel, time-breach, memory-breach, hard-crash-mid-flight} is
    built from B-4/B-5 before observing; each is observed through the injected
    ledger directory. (The completion arm -> one confirmation line is proven with
    a real process at L4.) Counter-case that FAILS: zero lines (a crash that never
    reports) or two lines (a completion/observer race).
    """
    out = tmp_path / "run"
    out.mkdir()
    led = tmp_path / "led"
    led.mkdir()
    cfg = config(cause)
    sink = make_ledger(led)
    live = make(cfg, out)
    result = finish_run(live, config=cfg, ledger=sink, role=ROLE_CONFIRMATION)
    assert is_refusal(result), "a terminal cause returns the run's refusal to the caller"
    assert line_count(led) == 1, f"{cause}: exactly ONE ledger line — never zero, never two"
    aborted_lines = lines_for_role(led, ROLE_ABORTED)
    assert len(aborted_lines) == 1, f"{cause}: the single line is the aborted-role line"
    assert aborted_lines[0].refusal is not None, "the aborted line is never silently absent of context"


def test_never_two_idempotent_and_collision(tmp_path):
    """T-15.4-b [R13, R-010] A single-owner sink collapses a repeated append to ONE
    line (idempotent), and refuses a DIFFERING second line for the same run id
    (collision, never an overwrite) — so a completion/death-observer race for one
    run can never yield two lines.

    Counter-case that FAILS: a second physical line on the repeat, or a silent
    overwrite of a differing line.
    """
    led = tmp_path / "led"
    led.mkdir()
    sink = make_ledger(led)
    cfg = config("race")
    same = ledger_line(cfg, role=ROLE_CONFIRMATION, tag="same")
    first = sink.append(same)
    second = sink.append(same)
    assert is_ok(first) and is_ok(second), "a byte-identical re-append is accepted idempotently"
    assert line_count(led) == 1, "a repeated append must not add a second physical line"

    differing = ledger_line(cfg, role=ROLE_CONFIRMATION, tag="different")
    collision = sink.append(differing)
    assert is_refusal(collision), "a differing second line for one run id is refused (never two)"
    assert collision.category.value in REFUSAL_REGISTER
    assert line_count(led) == 1, "the differing line must not be written"


def test_admission_refusal_produces_zero_lines(tmp_path):
    """T-15.4-d [R13, R6] A run refused at admission (over-budget) produces ZERO
    ledger lines — no run occurred — and the refusal is returned to the caller.

    This pins the boundary so a naive "every submit => a line" reading cannot
    misfire. Counter-case that FAILS: a phantom ledger line for a never-spawned run.
    """
    led = tmp_path / "led"
    led.mkdir()
    make_ledger(led)  # a sink exists but nothing is finished through it
    governor = ok(ResourceGovernor.try_create(cpu_budget=2, memory_budget=100))
    refused = governor.submit(ok(GovernedRequest.try_create(ok(fingerprint({"r": "big"})), 1000, 1)))
    assert is_refusal(refused)
    assert line_count(led) == 0, "a run never admitted must produce no ledger line"


def test_direct_library_call_ledgers_nothing(tmp_path):
    """T-15.4-h [R17] A direct library run() call produces no governed evidence —
    runs enter the governed ledger only through the orchestrator.

    Counter-case that FAILS: a governed ledger line appearing after a bare run()
    (a write escaping the composition root, the read-twin of the purity law).
    """
    led = tmp_path / "led"
    led.mkdir()
    outcome = run(slices=slices(), config=config("direct"))
    assert is_ok(outcome), "the direct library call returns a value"
    for role in (ROLE_CONFIRMATION, ROLE_TRIAL, ROLE_ABORTED):
        merged = read_merge_view(led, world="replay", role=role)
        assert is_ok(merged) and merged.value == (), "a direct run() writes no governed ledger line"


def test_merge_view_book_bar_selects_confirmation_only(tmp_path):
    """T-15.4-g [R16] A Book-bar read is a world-and-role-scoped merge selecting
    ``role=confirmation`` lines only; aborted/trial lines are excluded.

    Counter-case that FAILS: an aborted or trial line surfacing in a Book-bar read.
    """
    led = tmp_path / "led"
    led.mkdir()
    sink = make_ledger(led)
    ok(sink.append(ledger_line(config("c1"), role=ROLE_CONFIRMATION, tag="c1")))
    ok(sink.append(ledger_line(config("c2"), role=ROLE_CONFIRMATION, tag="c2")))
    ok(sink.append(ledger_line(config("t1"), role=ROLE_TRIAL, tag="t1")))

    book_bar = ok(read_book_bar(led, world="replay"))
    roles = {line.role for line in book_bar}
    assert roles == {ROLE_CONFIRMATION}, "the Book-bar read selects confirmation lines only"
    assert len(book_bar) == 2

    aborted_view = ok(read_merge_view(led, world="replay", role=ROLE_ABORTED))
    assert aborted_view == (), "no aborted lines were written, so the aborted view is empty"


# ============ Group E — per-run operational logs (R18, R21) ================
def test_orchestrator_streams_per_run_log_into_run_directory(tmp_path):
    """T-15.5-a [R18] The orchestrator streams each run's operational log into a
    per-run log file (run.log) inside that run's output directory.

    Counter-case that FAILS: a log written outside the run directory, or a run
    directory with no operational log after injection.
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    cfg = config("log")
    path = ok(inject_run_log(run_dir, run_id=cfg.fingerprint, correlation_id="corr-1"))
    assert path == run_dir / "run.log", "the per-run log lives inside the run's own directory"
    assert path.is_file()
    records = ok(read_run_log(run_dir))
    assert any(rec.event == "spawned" for rec in records), "the injected sink emits its record"


def test_crashed_run_leaves_partial_log_in_its_own_room(tmp_path):
    """T-15.5-d [R21] A crashed run leaves a partial log in its own room and
    corrupts neither a sibling's log nor the ledger.

    Counter-case that FAILS: a crash in room A mutating room B's log, or writing
    a ledger line into the shared ledger root.
    """
    room_a = tmp_path / "a"
    room_a.mkdir()
    room_b = tmp_path / "b"
    room_b.mkdir()
    led = tmp_path / "led"
    led.mkdir()
    cfg_a = config("a")
    cfg_b = config("b")
    ok(inject_run_log(room_a, run_id=cfg_a.fingerprint, correlation_id="corr-a"))
    ok(inject_run_log(room_b, run_id=cfg_b.fingerprint, correlation_id="corr-b"))
    b_before = (room_b / "run.log").read_bytes()

    # Room A crashes mid-flight (fake process, no result file).
    sink = make_ledger(led)
    live = fake_live(cfg_a, process=FakeProcess(alive=False, returncode=1), output_dir=str(room_a))
    result = finish_run(live, config=cfg_a, ledger=sink, role=ROLE_CONFIRMATION)
    assert is_refusal(result)

    assert (room_b / "run.log").read_bytes() == b_before, "the sibling's log must be untouched"
    # Exactly one aborted line for A's run; nothing for B.
    assert line_count(led) == 1
    b_lines = [ln for ln in lines_for_role(led, ROLE_ABORTED) if ln.run_id == cfg_b.fingerprint]
    assert b_lines == [], "the sibling run got no ledger line from A's crash"
