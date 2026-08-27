"""L6 non-functional / property gates. BEHAVIOUR only — no throughput, latency,
or run-count number is ever a pass criterion (R-017).

Run with: uv run --with hypothesis pytest qa/tests/epic_15/test_l6_property.py
"""

from __future__ import annotations

from pathlib import Path

from _e15 import (
    cancelled_token,
    config,
    duration,
    fake_live,
    FakeProcess,
    line_count,
    make_ledger,
    ok,
    slices,
)
from hypothesis import given, settings
from hypothesis import strategies as st

from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import is_refusal

from qmb.orchestrator import (
    GovernedRequest,
    ResourceGovernor,
    SpawnJob,
    finish_run,
    spawn_concurrent,
    spawn_run,
)
from qmb.ledger import ROLE_CONFIRMATION
from qmb.runloop.observe import RunLimits, ScriptedLimitProbe


# -- T-15.2-e [R5, R6] governor never oversubscribes under any interleaving ---
@settings(max_examples=200, deadline=None)
@given(
    cpu_budget=st.integers(min_value=1, max_value=6),
    memory_budget=st.integers(min_value=1, max_value=64),
    peak=st.integers(min_value=1, max_value=16),
    ops=st.lists(st.sampled_from(["submit", "release"]), min_size=1, max_size=40),
)
def test_governor_property_never_exceeds_min_bound(cpu_budget, memory_budget, peak, ops):
    """Under an arbitrary interleaving of submit/release, concurrently-admitted
    runs never exceed min(cpu, memory) and reserved budgets never exceed the
    declared totals — no over-budget run is ever admitted. No throughput number
    is asserted.

    Counter-case that FAILS: any step where running_count exceeds the bound, or
    reserved cpu/memory exceeds the declared budget.
    """
    governor = ok(ResourceGovernor.try_create(cpu_budget=cpu_budget, memory_budget=memory_budget))
    bound = ok(governor.parallelism_bound(projected_peak_memory=peak))
    counter = 0
    for op in ops:
        if op == "submit":
            req = ok(GovernedRequest.try_create(ok(fingerprint({"r": counter})), peak, 1))
            counter += 1
            governor.submit(req)  # admitted, queued, or refused — never oversubscribe
        elif governor.running:
            governor.release(governor.running[0].run_id)
        # Invariant after every op:
        assert governor.running_count <= bound, "running runs never exceed min(cpu, memory)"
        assert governor.reserved_cpu <= cpu_budget, "reserved cpu never exceeds the budget"
        assert governor.reserved_memory <= memory_budget, "reserved memory never exceeds the budget"


# -- T-15.4-i [R13, R-010] exactly-one-line over arbitrary terminal sequences -
@settings(max_examples=100, deadline=None)
@given(
    causes=st.lists(
        st.sampled_from(["cancel", "time", "memory", "crash"]), min_size=1, max_size=8
    )
)
def test_exactly_one_line_per_finished_run_property(tmp_path_factory, causes):
    """Over arbitrary sequences of terminal causes across N runs, the ledger line
    count equals EXACTLY the number of runs finished, each appearing exactly once.

    Counter-case that FAILS: any run yielding zero lines (lost evidence) or two
    lines (double-counted evidence) — line_count != number of finished runs.
    """
    root = Path(tmp_path_factory.mktemp("oneline"))
    led = root / "led"
    led.mkdir()
    sink = make_ledger(led)
    for index, cause in enumerate(causes):
        cfg = config(f"run-{index}-{cause}")
        run_dir = root / f"r{index}"
        run_dir.mkdir()
        if cause == "cancel":
            live = fake_live(cfg, process=FakeProcess(alive=True), cancel=cancelled_token("cancel"),
                             output_dir=str(run_dir))
        elif cause == "time":
            live = fake_live(cfg, process=FakeProcess(alive=True),
                             limits=RunLimits(time_limit=duration(10)),
                             probe=ScriptedLimitProbe(elapsed_ns=[10**9]), output_dir=str(run_dir))
        elif cause == "memory":
            live = fake_live(cfg, process=FakeProcess(alive=True),
                             limits=RunLimits(memory_limit_bytes=1000),
                             probe=ScriptedLimitProbe(memory_bytes=[9000]), output_dir=str(run_dir))
        else:  # crash
            live = fake_live(cfg, process=FakeProcess(alive=False, returncode=1), output_dir=str(run_dir))
        result = finish_run(live, config=cfg, ledger=sink, role=ROLE_CONFIRMATION)
        assert is_refusal(result), "every terminal cause returns the run's refusal"
    assert line_count(led) == len(causes), (
        "each finished run appears exactly once — never zero, never two"
    )


# -- T-15.6-conc [R33 shared] concurrency is scheduling only: identical fp -----
def test_concurrency_fingerprint_invariance(tmp_path):
    """A run alongside real concurrent siblings yields a byte-identical CT-32
    fingerprint to the isolated run — concurrency is a scheduling decision only.
    An identity assertion, never a speed one.

    Counter-case that FAILS: a different CT-32 fingerprint under concurrency,
    which would mean concurrency changed the governed result.
    """
    solo_root = tmp_path / "solo"
    solo_root.mkdir()
    conc_root = tmp_path / "conc"
    conc_root.mkdir()
    cfg = config("conc-subject")

    solo = ok(spawn_run(config=cfg, slices=slices(), output_root=solo_root))

    jobs = [
        SpawnJob(config=config("conc-subject"), slices=slices()),  # same identity as subject
        SpawnJob(config=config("conc-neighbour"), slices=slices()),
    ]
    concurrent = ok(spawn_concurrent(jobs, output_root=conc_root))
    subject = next(r for r in concurrent if r.run_id == cfg.fingerprint)
    assert subject.ct32_fingerprint == solo.ct32_fingerprint, (
        "concurrency must not change the CT-32 fingerprint (scheduling only)"
    )
