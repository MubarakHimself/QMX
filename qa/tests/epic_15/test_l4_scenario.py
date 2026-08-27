"""L4 golden scenario: SCN-0012 orchestrator + ledger path, and Branch B
(synthetic/simulated store never enters the governed ledger).
"""

from __future__ import annotations

import os

from _e15 import REFUSAL_REGISTER, config, ledger_line, line_count, make_ledger, ok, sim_config, slices

from qmf.core.fingerprint import World, governed_namespace
from qmf.core.refusal import is_ok, is_refusal

from qmb.orchestrator import finish_run, read_book_bar, start_run
from qmb.ledger import ROLE_CONFIRMATION
from qmb.ledger.line import mint_completed_line


# -- T-15.SCN-a [R1, R13, R14] the governed replay run ----------------------
def test_scn0012_one_governed_run_one_confirmation_line(tmp_path):
    """One backtest spawns ONE governed isolated process; the pure run() returns a
    CT-32 artifact; the orchestrator appends EXACTLY ONE role=confirmation ledger
    line carrying the AD-12 label + CT-32 fp + AD-40 measures + Book-bar fp; NO
    pass/fail is stored.

    Counter-case that FAILS: zero or two ledger lines, a non-confirmation role, a
    line missing the CT-32 fp, or a stored verdict.
    """
    out = tmp_path / "out"
    out.mkdir()
    led = tmp_path / "led"
    led.mkdir()
    cfg = config("scn")
    live = ok(start_run(config=cfg, slices=slices(), output_root=out))
    assert live.pid > 0

    collected = finish_run(live, config=cfg, ledger=make_ledger(led), role=ROLE_CONFIRMATION)
    assert is_ok(collected), "the governed run completes and ledgers"
    isolated = collected.value
    assert isolated.worker_pid != os.getpid(), "the run executed in a separate OS process"
    assert isolated.ct32_fingerprint is not None, "the pure run() returned a CT-32 artifact"

    assert line_count(led) == 1, "exactly ONE governed ledger line for the run"
    book_bar = ok(read_book_bar(led, world="replay"))
    assert len(book_bar) == 1 and book_bar[0].role == ROLE_CONFIRMATION
    assert book_bar[0].ct32_fingerprint == isolated.ct32_fingerprint
    identity = book_bar[0].fp1_identity()
    assert not ({"pass", "fail", "verdict", "rated"} & set(identity)), "no pass/fail is stored"


# -- T-15.SCN-b [R13, R16 / CT-11] synthetic/simulated store excluded --------
def test_scn0012_branch_b_simulated_store_never_governed(tmp_path):
    """A world=simulated (synthetic-store) run is a policy rejection for governed
    evidence — the orchestrator appends no governed (confirmation) ledger line.

    Counter-case that FAILS: a governed namespace resolving for world=simulated, a
    CT-32 minting for a simulated run, or a simulated ledger line persisting.
    """
    # The governed namespace itself refuses world=simulated (reserved-unusable, GAP-0048).
    ns = governed_namespace(World.SIMULATED)
    assert is_refusal(ns) and ns.category.value in REFUSAL_REGISTER

    # Minting a completed line for a simulated run is refused (CT-32 is replay-only).
    sim = sim_config("branchb")
    minted = mint_completed_line(
        sim,
        outcome_identity={"stream_order": ["synthetic"]},
        ct32_fingerprint="fp1:sha256:" + "0" * 64,
    )
    assert is_refusal(minted), "no CT-32 governed line is minted for world=simulated"
    assert minted.category.value in REFUSAL_REGISTER

    # Appending a hand-built simulated line is refused; nothing persists.
    led = tmp_path / "led"
    led.mkdir()
    sink = make_ledger(led)
    appended = sink.append(ledger_line(sim, role=ROLE_CONFIRMATION, tag="sim", world=World.SIMULATED))
    assert is_refusal(appended), "a simulated-world line never enters the governed ledger"
    assert line_count(led, world="simulated") == 0
    assert line_count(led, world="replay") == 0
