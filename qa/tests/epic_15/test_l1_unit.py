"""L1 pure-unit gates: governor admission arithmetic and the ledger-line builder.

One pure function at a time, driven on its public surface. Every refusal
assertion checks a RETURNED CT-04 value of a register-legal category.
"""

from __future__ import annotations

from _e15 import REFUSAL_REGISTER, RUN_ROLE_SET, config, ok

from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import is_ok, is_refusal

from qmb.orchestrator import GovernedRequest, ResourceGovernor
from qmb.ledger import ROLE_ABORTED
from qmb.ledger.line import mint_aborted_line, mint_completed_line
from qmb.runloop.observe import refuse_aborted, RunProgress


def _req(tag: str, peak: int = 10, cost: int = 1) -> GovernedRequest:
    fp = ok(fingerprint({"req": tag}))
    return ok(GovernedRequest.try_create(fp, peak, cost))


# -- T-15.2-a [R5] admission bound == min(cpu, memory) -----------------------
def test_admission_bound_is_min_cpu_memory():
    """The governor admits no more than min(cpu slots, memory slots).

    Counter-case that FAILS: admitting a (min+1)-th run (oversubscription), or a
    bound equal to the LARGER budget. Here cpu=3, mem=100/peak10 => mem slots 10,
    so min = 3; the 4th submit must NOT be admitted.
    """
    governor = ok(ResourceGovernor.try_create(cpu_budget=3, memory_budget=100))
    bound = ok(governor.parallelism_bound(projected_peak_memory=10))
    assert bound == 3, f"min(cpu=3, mem_slots=10) must be 3, got {bound}"
    decisions = [governor.submit(_req(f"r{i}", peak=10)).value.decision for i in range(3)]
    assert decisions == ["admitted", "admitted", "admitted"]
    fourth = governor.submit(_req("r3", peak=10))
    assert is_ok(fourth) and fourth.value.decision == "queued", (
        "the (bound+1)-th run must enqueue, never be admitted (no oversubscription)"
    )
    assert governor.running_count == 3, "concurrently admitted runs must never exceed the min bound"


def test_admission_bound_memory_is_the_constraint():
    """When memory is the tighter budget, min follows memory, not cpu.

    Counter-case that FAILS: admitting cpu_budget runs when only 2 fit in memory.
    """
    governor = ok(ResourceGovernor.try_create(cpu_budget=8, memory_budget=25))
    bound = ok(governor.parallelism_bound(projected_peak_memory=10))  # mem slots = 2
    assert bound == 2
    a = governor.submit(_req("a", peak=10))
    b = governor.submit(_req("b", peak=10))
    c = governor.submit(_req("c", peak=10))
    assert (a.value.decision, b.value.decision, c.value.decision) == (
        "admitted",
        "admitted",
        "queued",
    ), "memory must bound admission to 2 even with 8 cpu slots"


# -- T-15.2-b [R6] over-budget => refused-or-enqueued, never oversubscribe ----
def test_over_total_budget_run_is_refused_not_crashed():
    """A run whose projected peak exceeds the TOTAL memory budget is refused.

    It can never fit; enqueue-on-full does not apply. Counter-case that FAILS:
    admitting it, or crashing (raising) instead of returning a typed refusal.
    """
    governor = ok(ResourceGovernor.try_create(cpu_budget=4, memory_budget=100))
    refused = governor.submit(_req("too-big", peak=1000))
    assert is_refusal(refused), "an over-total-budget run must return a typed refusal"
    assert refused.category.value in REFUSAL_REGISTER
    assert governor.running_count == 0, "a refused run must never be admitted (no oversubscription)"


def test_over_remaining_budget_enqueues_or_refuses_never_admits():
    """A run that fits the total but not the remaining budget enqueues (default) or
    refuses (on_full=refuse) — never a silent third state.

    Counter-case that FAILS: a decision that is neither queued/admitted nor a
    typed refusal, i.e. a silent oversubscription.
    """
    enqueue_gov = ok(ResourceGovernor.try_create(cpu_budget=2, memory_budget=20))
    enqueue_gov.submit(_req("a", peak=10))
    enqueue_gov.submit(_req("b", peak=10))  # remaining memory now 0
    third = enqueue_gov.submit(_req("c", peak=10))
    assert is_ok(third) and third.value.decision == "queued"

    refuse_gov = ok(ResourceGovernor.try_create(cpu_budget=2, memory_budget=20, on_full="refuse"))
    refuse_gov.submit(_req("a", peak=10))
    refuse_gov.submit(_req("b", peak=10))
    denied = refuse_gov.submit(_req("c", peak=10))
    assert is_refusal(denied) and denied.category.value in REFUSAL_REGISTER
    assert refuse_gov.running_count == 2, "on_full=refuse must not oversubscribe"


# -- T-15.4-j [R14] ledger-line builder schema ------------------------------
def test_aborted_line_builder_is_aborted_role_with_refusal_and_no_ct32():
    """mint_aborted_line yields an aborted-ROLE line carrying refusal context,
    no CT-32 fingerprint, and NO pass/fail verdict.

    Counter-case that FAILS: a non-aborted role, a stored ct32 on an abort, a
    missing refusal, or a verdict field.
    """
    cfg = config("abline")
    refusal = refuse_aborted(
        cause="cancel",
        progress=RunProgress(data_points_processed=0, slices_completed=0, is_warming_up=False),
    )
    line = ok(mint_aborted_line(cfg, refusal))
    assert line.role == ROLE_ABORTED
    assert line.role in RUN_ROLE_SET
    assert line.ct32_fingerprint is None, "an aborted line carries no CT-32 result fingerprint"
    assert line.refusal is not None, "an aborted line is never silently absent of refusal context"
    identity = line.fp1_identity()
    verdict_keys = {"pass", "fail", "verdict", "rated", "bar-pass", "bar-fail"}
    assert not (verdict_keys & set(identity)), "a ledger line stores no pass/fail verdict"


def test_completed_line_builder_refuses_aborted_role():
    """The completed-line builder refuses role=aborted (aborted is minted only
    from a typed refusal), returned not raised.

    Counter-case that FAILS: minting a 'completed' line whose role is aborted.
    """
    cfg = config("compline")
    refused = mint_completed_line(
        cfg,
        outcome_identity={"stream_order": ["eurusd"]},
        ct32_fingerprint=ok(fingerprint({"ct": "x"})),
        role=ROLE_ABORTED,
    )
    assert is_refusal(refused), "a completed run never carries the aborted role"
    assert refused.category.value in REFUSAL_REGISTER
