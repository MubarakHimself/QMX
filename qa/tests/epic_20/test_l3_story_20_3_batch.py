"""Epic 20 · Story 20.3 (L3) — one isolated run per combo, exactly one ledger line.

Driven through the REAL never-forked run loop under the REAL orchestrator/governor/
ledger (module-scoped `happy_batch` / `victim_batch` fixtures run the process fan-out
once). Observations read the on-disk ledger lines and the returned report.

  T20-312  R12  each combo -> one resolved config (fp1 = run id) + isolated output dir (P0)
  T20-313  R13  concurrency never changes a combo's result or CT-32 fingerprint      (P1)
  T20-314  R14  admitted-combo count == ledger-line count; full payload; 1 line/combo (P0 · R-010)
  T20-315  R15  a combo refusal is its aborted line + refusal context; batch continues (P0)
  T20-316  R16  world derives from provenance; optimistic taint; no edge claim        (P0)
  T20-323  R23  role discriminant + confirmation-only fold (WHICH role = UNPROVEN)    (UNPROVEN)
"""

from __future__ import annotations

from pathlib import Path

from conftest import (
    BatchRun,
    admit,
    good_slices,
    make_ledger,
    ok,
    run_batch,
    run_settings,
    runs_dir,
)

import qmb
from qmb.config import CLOCK_REPLAY, PROVENANCE_SYNTHETIC_TAINTED, STARTING_CAPITAL_KEY
from qmb.execution.ports import refuse_optimistic_edge_claim, refuse_store_synthetic_governed_evidence
from qmb.sweep import run_sweep_batch
from qmf.core.exact import Money
from qmf.core.fingerprint import World
from qmf.core.refusal import RefusalCategory, is_refusal

_ROLE_VOCAB = {"confirmation", "trial", "replicate", "aborted"}
_SEED = Money(value=1_000_000, currency="USD", scale=2)


# --- T20-312 (R12) : one resolved config (fp1 = run id) + isolated output dir --


def test_t20_312_each_combo_is_one_isolated_run_with_its_own_output_dir(happy_batch: BatchRun) -> None:
    report = happy_batch.report
    admitted = happy_batch.admitted
    assert report.run_count == len(admitted.combos) == 4
    assert report.completed_count == 4
    # Each combination compiles to exactly one resolved config whose fp1 is the run id.
    for combo, outcome in zip(admitted.combos, report.outcomes, strict=True):
        config = ok(admitted.compile_combo(combo, **run_settings()))
        assert outcome.run_id == config.fingerprint
        assert outcome.output_dir is not None
    # One ISOLATED output directory per combination — never shared.
    dirs = [o.output_dir for o in report.outcomes]
    assert len(set(dirs)) == 4


# --- T20-313 (R13) : concurrency never changes a result or CT-32 fingerprint ---


def test_t20_313_concurrency_never_changes_result_or_ct32(tmp_path: Path) -> None:
    admitted = admit(instruments=("EURUSD",), parameters={"lookback": [10, 20]})
    serial = run_batch(admitted, tmp_path, cpu_budget=1, runs_sub="seq", ledger_sub="seq_l")
    concurrent = run_batch(admitted, tmp_path, cpu_budget=4, runs_sub="par", ledger_sub="par_l")
    # Same run ids and same CT-32 fingerprints regardless of parallelism/order.
    assert serial.fp1_identity() == concurrent.fp1_identity()
    assert [o.ct32_fingerprint for o in serial.outcomes] == [o.ct32_fingerprint for o in concurrent.outcomes]


# --- T20-314 (R14 · R-010) : one ledger line per combo, full payload -----------


def test_t20_314_exactly_one_ledger_line_per_combo_with_full_payload(happy_batch: BatchRun) -> None:
    report = happy_batch.report
    admitted = happy_batch.admitted
    lines = ok(qmb.read_merge_view(happy_batch.ledger_root, world=World.REPLAY, role="confirmation"))
    # admitted-combo count == ledger-line count: never zero (a drop), never two (a
    # double). Counter-case: a silently dropped combo shows as a MISSING line here.
    assert len(lines) == report.run_count == len(admitted.combos) == 4
    assert len({line.run_id.value for line in lines}) == 4  # each run id appears once

    by_run = {line.run_id.value: line for line in lines}
    for outcome in report.outcomes:
        line = by_run[outcome.run_id.value]
        assert line.ct32_fingerprint == outcome.ct32_fingerprint  # CT-32 fingerprint
        assert line.measures  # raw AD-40 measures, non-empty
        assert all(
            "unit_kind" in m or m.get("class") == "undefined-measure" for m in line.measures
        )
        assert line.result_label  # the full AD-12 label
        coords = line.sweep_coordinates
        assert coords is not None
        # sweep coordinates {sweep_id, instrument, BarSpec, param-hash}.
        assert coords["sweep_id"] == admitted.label.sweep_id.value
        assert coords["instrument"] == outcome.sweep_coordinates["instrument"]
        assert "bar_spec" in coords
        assert "param_hash" in coords


# --- T20-315 (R15) : a combo refusal is its aborted line; the batch continues --


def test_t20_315_a_combo_refusal_is_its_line_and_the_batch_continues(victim_batch: BatchRun) -> None:
    report = victim_batch.report
    root = victim_batch.ledger_root
    # The whole batch ran; exactly one combo aborted, three completed.
    assert report.run_count == 4
    assert report.completed_count == 3
    assert report.refused_count == 1

    aborted = ok(qmb.read_merge_view(root, world=World.REPLAY, role="aborted"))
    assert len(aborted) == 1
    assert aborted[0].refusal is not None  # refusal context recorded on the line
    assert aborted[0].sweep_coordinates is not None
    # The confirmation book-bar sees ONLY the three survivors — the batch continued.
    bar = ok(qmb.read_book_bar(root, world=World.REPLAY))
    assert len(bar) == 3
    assert all(line.role == "confirmation" for line in bar)

    refused = [o for o in report.outcomes if o.status == "refused"]
    assert len(refused) == 1
    assert refused[0].refusal is not None
    assert refused[0].role == "aborted"


# --- T20-316 (R16) : world from provenance; optimistic taint; no edge claim ----


def test_t20_316_world_derives_from_provenance_and_no_edge_is_claimed(happy_batch: BatchRun) -> None:
    admitted = happy_batch.admitted
    combo = admitted.combos[0]
    defaults = run_settings()["workspace_defaults"]

    # (a) recorded provenance derives world=replay on every combo.
    replay_config = ok(admitted.compile_combo(combo, **run_settings()))
    assert replay_config.world is World.REPLAY

    # (b) a caller-declared world is NOT accepted — world is provenance-derived.
    caller_world = admitted.compile_combo(
        combo,
        invocation_flags={STARTING_CAPITAL_KEY: _SEED, "world": "replay"},
        workspace_defaults=defaults,
    )
    assert is_refusal(caller_world)
    assert caller_world.category is RefusalCategory.INVALID_INPUT

    # (c) a replay clock bound to synthetic-tainted data is invalid input (FM-3).
    synthetic = admitted.compile_combo(
        combo,
        invocation_flags={STARTING_CAPITAL_KEY: _SEED},
        workspace_defaults={**defaults, "clock": CLOCK_REPLAY, "data_provenance": PROVENANCE_SYNTHETIC_TAINTED},
    )
    assert is_refusal(synthetic)
    assert synthetic.category is RefusalCategory.INVALID_INPUT

    # (d) a store-tainted read is world=simulated and a policy rejection until GAP-0048.
    sim_refusal = refuse_store_synthetic_governed_evidence(World.SIMULATED)
    assert is_refusal(sim_refusal)
    assert sim_refusal.category is RefusalCategory.POLICY_REJECTION

    # (e) every fill carries the optimistic taint; an edge claim is refused.
    assert ok(refuse_optimistic_edge_claim()) is None
    edge = refuse_optimistic_edge_claim(claims_edge=True)
    assert is_refusal(edge)
    assert edge.category is RefusalCategory.POLICY_REJECTION

    # (f) on the real batch lines, world is replay and NO pass/fail verdict is stored.
    lines = ok(qmb.read_merge_view(happy_batch.ledger_root, world=World.REPLAY, role="confirmation"))
    for line in lines:
        assert line.world is World.REPLAY
        identity = line.fp1_identity()
        assert "verdict" not in identity and "pass" not in identity and "fail" not in identity


# --- T20-323 (R23 · UNPROVEN) : role discriminant + confirmation-only fold -----


def test_t20_323_role_discriminant_and_confirmation_only_fold(happy_batch: BatchRun) -> None:
    """STRUCTURAL only. Asserts the role is one of the closed vocabulary and that
    the Book-bar fold selects confirmation-role lines. It does NOT assert WHICH
    role a plain sweep combo SHOULD take — that is the OPEN operator-ruling item
    (recorded UNPROVEN in RESULTS.md), and is not invented here."""
    report = happy_batch.report
    for outcome in report.outcomes:
        assert outcome.role in _ROLE_VOCAB
    lines = ok(qmb.read_merge_view(happy_batch.ledger_root, world=World.REPLAY, role="confirmation"))
    for line in lines:
        assert line.role in _ROLE_VOCAB
    # The confirmation-only fold: the Book-bar reads confirmation lines only.
    bar = ok(qmb.read_book_bar(happy_batch.ledger_root, world=World.REPLAY))
    assert all(line.role == "confirmation" for line in bar)
    assert len(bar) == 4


def test_t20_315_run_over_budget_is_each_combos_refused_line(tmp_path: Path) -> None:
    """R15 corollary: a projected peak that can never be admitted makes every
    combination a refused line and the batch STILL returns a complete report —
    no combination is silently dropped even when none can run."""
    admitted = admit(instruments=("EURUSD",), parameters={"lookback": [10, 20]})
    report = ok(
        run_sweep_batch(
            admitted,
            output_root=runs_dir(tmp_path, "ob_runs"),
            ledger=make_ledger(tmp_path, "ob_ledger"),
            combo_slices=good_slices,
            projected_peak_memory=4096,
            cpu_budget=4,
            memory_budget=1024,  # budget // peak == 0 -> never fits
            **run_settings(),
        )
    )
    assert report.run_count == 2
    assert report.completed_count == 0
    assert report.refused_count == 2
    aborted = ok(qmb.read_merge_view(make_ledger(tmp_path, "ob_ledger").root, world=World.REPLAY, role="aborted"))
    assert len(aborted) == 2
    assert all(line.refusal is not None for line in aborted)
