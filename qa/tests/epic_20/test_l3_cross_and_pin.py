"""Epic 20 (L3) — cross-cutting CT-04 discipline and the R-004 regression pin.

  T20-322    R22    every Epic-20 refusal is a RETURNED CT-04 value (category in the
                    seven, context present) — no public boundary RAISES        (P0)
  T20-302c   R2     a true ledger-key collision (same run_id, differing bytes) is
                    REFUSED and ALARMED, never overwritten (CT-05/AR-51)        (P0 · R-004)
  T20-PIN-01 R-004  the sweep drops NO combination: two combos differing ONLY in a
                    swept parameter each produce a distinct run id AND a distinct
                    ledger line, end to end  (finding F-20-01 probe)            (P0)
"""

from __future__ import annotations

from pathlib import Path

from conftest import (
    TF_1M,
    admit,
    bms_definition,
    book_definition,
    bot_record,
    completed_line,
    declaration,
    fp,
    instant,
    make_ledger,
    make_port,
    ok,
    record,
    run_batch,
    run_settings,
    sweep_id_a,
    writer,
)

import qmb
from qmb.ledger.line import merge_ledger_lines
from qmb.registryread import DatedPointer, SupersedesRef
from qmb.sweep import (
    ConstraintFilter,
    SweepDeclaration,
    admit_sweep,
    rank_sweep,
    refuse_rank_act,
)
from qmf.core.fingerprint import World
from qmf.core.refusal import RefusalCategory, TypedRefusal, is_refusal

_SEVEN = {c.value for c in RefusalCategory}


def _superseded_admission() -> object:
    """Admit a sweep citing a superseded Book — returns the (stale) refusal."""
    book_v1 = record("book-definition", book_definition(q=100))
    book_v2 = record("book-definition", book_definition(q=200))
    bms = record("bms-definition", bms_definition())
    bot = bot_record()
    pointers = (
        ok(DatedPointer.try_create("mean-reversion", bot.stable_id, instant())),
        ok(DatedPointer.try_create("scalping", book_v2.stable_id, instant())),
    )
    supersedes = (ok(SupersedesRef.try_create(book_v2.stable_id, book_v1.stable_id)),)
    port = make_port(book_v1, book_v2, bms, bot, pointers=pointers, supersedes=supersedes)
    decl = declaration(bot=bot.stable_id, book=book_v1.stable_id, bms=bms.stable_id)
    return admit_sweep(decl, port, writer())


# --- T20-322 (R22) : every refusal is a RETURNED CT-04 value, never raised -----


def test_t20_322_every_epic20_refusal_is_a_returned_ct04_value() -> None:
    a = sweep_id_a()
    good_line = [completed_line("c1", sweep_id=a, measures=())]
    refusals: dict[str, object] = {
        "empty_axis": SweepDeclaration.try_create(
            bot="b", book="k", bms="m", instruments=[], timeframes=(TF_1M,)
        ),
        "superseded_ref": _superseded_admission(),
        "bad_port": admit_sweep(
            declaration(bot="b", book="k", bms="m"), object(), writer()
        ),
        "non_roster_objective": rank_sweep(
            good_line, sweep_id=a, objective="totally_made_up", world=World.REPLAY
        ),
        "forbidden_act": refuse_rank_act("promote"),
        "float_constraint": ConstraintFilter.try_create("max_drawdown", "le", 0.2),
    }
    for name, refusal in refusals.items():
        assert is_refusal(refusal), name
        # RETURNED, not raised: a TypedRefusal is NOT an exception type.
        assert isinstance(refusal, TypedRefusal), name
        assert not isinstance(refusal, BaseException), name
        # Category is one of the seven ratified CT-04 categories.
        assert refusal.category.value in _SEVEN, name
        # Machine-readable context is present and non-empty.
        assert isinstance(refusal.context, dict) or refusal.context, name
        assert len(dict(refusal.context)) > 0, name


# --- T20-302c (R2 · R-004) : a true ledger-key collision refuses-and-alarms -----


def test_t20_302c_true_collision_refuses_and_alarms_never_overwrites() -> None:
    a = sweep_id_a()
    run = "shared-run-id"
    # Two lines share a run_id but carry DIFFERING identity content (different
    # measures). This is the CT-05/AR-51 true collision — it must REFUSE and
    # ALARM on the ledger-key path, never silently overwrite one with the other.
    line_1 = completed_line(run, sweep_id=a, measures=(_measure(3000),))
    line_2 = completed_line(run, sweep_id=a, measures=(_measure(9000),))
    refused = merge_ledger_lines([line_1, line_2], world=World.REPLAY, role="confirmation")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context.get("alarm") is True
    # By contrast, a byte-identical idempotent re-write collapses silently to one.
    idempotent = ok(merge_ledger_lines([line_1, line_1], world=World.REPLAY, role="confirmation"))
    assert len(idempotent) == 1


def _measure(minor: int) -> dict[str, object]:
    from conftest import net_profit  # local import keeps the helper set explicit

    return net_profit(minor)


# --- T20-PIN-01 (R-004) : F-20-01 probe — no combination is dropped -------------


def test_t20_pin_01_two_combos_differing_only_in_a_param_are_not_dropped(tmp_path: Path) -> None:
    """The sharpest F-20-01 probe: one instrument x one timeframe x TWO parameter
    values — two combinations that are IDENTICAL except for the swept parameter.
    If the swept parameter were dropped from run-config identity (a lossy key),
    the two combos would collapse to one run id and one would be silently
    dropped/overwritten. The assertions below FAIL in that case."""
    admitted = admit(instruments=("EURUSD",), timeframes=(TF_1M,), parameters={"lookback": [10, 20]})
    assert admitted.run_count == 2

    # (write side) the two resolved run-config fp1 (run-id root + ledger key) differ.
    configs = ok(admitted.compile_all(**run_settings()))
    assert len({c.fingerprint.value for c in configs}) == 2

    # (end to end) run the real batch; two distinct combos -> two distinct ledger
    # lines. distinct-combo count == distinct-run-id count == ledger-line count.
    report = run_batch(admitted, tmp_path, runs_sub="pin_runs", ledger_sub="pin_ledger")
    assert report.run_count == 2
    assert report.completed_count == 2
    lines = ok(qmb.read_merge_view(make_ledger(tmp_path, "pin_ledger").root, world=World.REPLAY, role="confirmation"))
    assert len(lines) == 2  # never one (a drop), never three (a double)
    assert len({line.run_id.value for line in lines}) == 2
    # The two lines differ only in their swept-parameter coordinate — both present.
    param_hashes = {line.sweep_coordinates["param_hash"] for line in lines}
    assert len(param_hashes) == 2
    # No combination fell out between admission and the ledger.
    assert {o.run_id.value for o in report.outcomes} == {line.run_id.value for line in lines}
