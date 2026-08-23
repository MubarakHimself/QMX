"""Story 10.3 AC5 — the control-rank table and rank uniqueness.

Verifies the BMS-declared control-rank table on qmf-core nouns: a rank is a
mandatory non-defaultable count, the table is a total order canonically ordered by
rank, and **two control-action kinds sharing a rank is an invalid-input refusal**
(and a kind appearing twice too) — enforced at admission Layer 1 (CT-27, CT-30;
DEC-0151).
"""

from __future__ import annotations

from qmf.core import RefusalCategory, is_ok, is_refusal
from qmf.risk.control_rank import (
    ControlActionKind,
    ControlRankRow,
    ControlRankTable,
    check_control_rank_uniqueness,
)


def _row(kind: ControlActionKind, rank: int) -> ControlRankRow:
    result = ControlRankRow.try_create(kind, rank)
    assert is_ok(result)
    return result.value


def _total_table() -> list[ControlRankRow]:
    return [
        _row(ControlActionKind.FLATTEN, 0),
        _row(ControlActionKind.DRAIN, 1),
        _row(ControlActionKind.SUSPEND_NEW, 2),
        _row(ControlActionKind.RESUME, 3),
    ]


def test_control_action_kind_has_four_members() -> None:
    assert {k.value for k in ControlActionKind} == {"suspend_new", "drain", "flatten", "resume"}


def test_row_builds_and_refuses_bad_parts() -> None:
    assert is_ok(ControlRankRow.try_create(ControlActionKind.FLATTEN, 0))
    assert is_ok(ControlRankRow.try_create("drain", 5))
    assert is_refusal(ControlRankRow.try_create("not-a-kind", 0))
    assert is_refusal(ControlRankRow.try_create(ControlActionKind.FLATTEN, True))
    assert is_refusal(ControlRankRow.try_create(ControlActionKind.FLATTEN, "0"))
    assert is_refusal(ControlRankRow.try_create(ControlActionKind.FLATTEN, -1))


def test_table_builds_and_orders_by_rank() -> None:
    result = ControlRankTable.try_create(list(reversed(_total_table())))
    assert is_ok(result)
    assert [row.rank for row in result.value.rows] == [0, 1, 2, 3]
    ranks = result.value.ranks_by_kind()
    assert ranks[ControlActionKind.FLATTEN] == 0
    assert ranks[ControlActionKind.RESUME] == 3


def test_table_refuses_empty_and_non_collection() -> None:
    assert is_refusal(ControlRankTable.try_create([]))
    assert is_refusal(ControlRankTable.try_create(42))
    assert is_refusal(ControlRankTable.try_create("drain"))
    assert is_refusal(ControlRankTable.try_create({"flatten": 0}))
    assert is_refusal(ControlRankTable.try_create([_row(ControlActionKind.FLATTEN, 0), "x"]))


def test_two_kinds_sharing_a_rank_is_invalid_input() -> None:
    rows = [_row(ControlActionKind.FLATTEN, 1), _row(ControlActionKind.DRAIN, 1)]
    result = ControlRankTable.try_create(rows)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_kind_appearing_twice_is_invalid_input() -> None:
    rows = [_row(ControlActionKind.FLATTEN, 0), _row(ControlActionKind.FLATTEN, 1)]
    result = ControlRankTable.try_create(rows)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_check_uniqueness_standalone_and_on_a_table() -> None:
    good = _total_table()
    assert is_ok(check_control_rank_uniqueness(good))
    table = ControlRankTable.try_create(good)
    assert is_ok(table)
    # A built table's rows are also accepted directly.
    assert is_ok(check_control_rank_uniqueness(table.value))
    dup_rank = [_row(ControlActionKind.FLATTEN, 2), _row(ControlActionKind.DRAIN, 2)]
    assert is_refusal(check_control_rank_uniqueness(dup_rank))
    dup_kind = [_row(ControlActionKind.DRAIN, 0), _row(ControlActionKind.DRAIN, 1)]
    assert is_refusal(check_control_rank_uniqueness(dup_kind))


def test_check_uniqueness_refuses_bad_inputs() -> None:
    assert is_refusal(check_control_rank_uniqueness(42))
    assert is_refusal(check_control_rank_uniqueness("drain"))
    assert is_refusal(check_control_rank_uniqueness({"flatten": 0}))
    assert is_refusal(check_control_rank_uniqueness([_row(ControlActionKind.FLATTEN, 0), "x"]))


def test_row_and_table_fp1_identity() -> None:
    row = _row(ControlActionKind.FLATTEN, 0)
    content = row.fp1_identity()
    assert content["control_action_kind"] == "flatten"
    assert content["rank"] == 0
    table = ControlRankTable.try_create(_total_table())
    assert is_ok(table)
    identity = table.value.fp1_identity()
    assert identity["class"] == "control-rank-table"
    assert len(table.value.rows) == 4


def test_table_identity_is_order_independent() -> None:
    forward = ControlRankTable.try_create(_total_table())
    reverse = ControlRankTable.try_create(list(reversed(_total_table())))
    assert is_ok(forward)
    assert is_ok(reverse)
    assert forward.value.fp1_identity() == reverse.value.fp1_identity()
