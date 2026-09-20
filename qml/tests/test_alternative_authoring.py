"""Story 58.2 — QML authors a complete PolicyPair; Book keys stay absent."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qml.declaration import author_policy_pair

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _assert_invalid(result: Result[T], *, field: str | None = None) -> None:
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    if field is not None:
        assert result.context["field"] == field


def _bodies() -> dict[str, object]:
    return {
        "accounting": {
            "cash_identity": "internal-cash",
            "currency": "USD",
            "fill_application": "fifo",
            "position_identity": "instrument+account",
            "residual_meaning": "open-qty",
            "valuation": "last-mark",
        },
        "risk": {
            "halt": "on-unknown-or-limit",
            "max_gross": "100000",
            "override_principal": "operator",
            "sizing": "fixed-fraction",
        },
    }


def test_author_policy_pair_omits_book_keys_and_hashes_bodies() -> None:
    authored = _ok(
        author_policy_pair(_bodies(), policy_pair_id="pp:kelly-v1", policy_pair_version=1)
    )
    assert authored.policy_pair_id == "pp:kelly-v1"
    assert authored.policy_pair_version == 1
    assert authored.policy_pair_hash.value.startswith("fp1:sha256:")
    identity = authored.identity()
    assert "accounting" not in identity
    assert "risk" not in identity
    for key in ("book", "book_fp1", "bms_fp1", "bot_fp1"):
        assert key not in authored.inline_bodies()
        assert key not in identity


def test_author_policy_pair_refuses_book_keys_dummy_and_sensing_as_atc() -> None:
    _assert_invalid(
        author_policy_pair(
            {**_bodies(), "book_fp1": None},
            policy_pair_id="pp:kelly-v1",
            policy_pair_version=1,
        ),
        field="book_fp1",
    )
    dummy = _bodies()
    risk = dict(cast("Mapping[str, object]", dummy["risk"]))
    risk["halt"] = "no-op"
    dummy["risk"] = risk
    _assert_invalid(
        author_policy_pair(dummy, policy_pair_id="pp:kelly-v1", policy_pair_version=1),
        field="halt",
    )
    _assert_invalid(
        author_policy_pair(
            {**_bodies(), "class": "research", "label": "atc"},
            policy_pair_id="pp:kelly-v1",
            policy_pair_version=1,
        ),
        field="label",
    )
    _assert_invalid(
        author_policy_pair(_bodies(), policy_pair_id="NULL_POLICY_PAIR", policy_pair_version=1),
        field="policy_pair_id",
    )
