"""Story 10.1 AC4 — the USD numeraire and the Book-limit unit law.

Verifies USD as the sole V1 numeraire, the mandatory ``accounting_currency``
declaration (non-USD a policy rejection so a later currency is a version change),
and that a Book-level limit stated in an instrument-native quantity (lots) — or in
a non-numeraire notional currency — is a policy rejection at template validation
(CT-22, FR-035; DEC-0154).
"""

from __future__ import annotations

from qmf.core import RefusalCategory, UnitKind, is_ok, is_refusal
from qmf.risk.numeraire import (
    BOOK_LIMIT_UNIT_KINDS,
    V1_NUMERAIRE,
    validate_accounting_currency,
    validate_book_limit,
)


def test_v1_numeraire_is_usd() -> None:
    assert V1_NUMERAIRE == "USD"


def test_book_limit_unit_kinds_are_r_and_money_only() -> None:
    assert frozenset({UnitKind.R_MULTIPLE, UnitKind.MONEY}) == BOOK_LIMIT_UNIT_KINDS


# --- accounting_currency -----------------------------------------------------


def test_accounting_currency_accepts_usd() -> None:
    result = validate_accounting_currency("USD")
    assert is_ok(result)
    assert result.value == "USD"


def test_accounting_currency_missing_is_invalid_input() -> None:
    result = validate_accounting_currency("   ")
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "accounting_currency"


def test_accounting_currency_non_usd_is_policy_rejection() -> None:
    result = validate_accounting_currency("EUR")
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context["numeraire"] == "USD"


# --- Book-level limit unit law -----------------------------------------------


def test_limit_in_r_multiple_is_legal() -> None:
    result = validate_book_limit(UnitKind.R_MULTIPLE)
    assert is_ok(result)
    assert result.value is UnitKind.R_MULTIPLE


def test_notional_limit_in_usd_is_legal() -> None:
    result = validate_book_limit(UnitKind.MONEY, currency="USD")
    assert is_ok(result)


def test_notional_limit_in_non_numeraire_is_policy_rejection() -> None:
    result = validate_book_limit(UnitKind.MONEY, currency="EUR")
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context["field"] == "currency"


def test_notional_limit_without_currency_is_invalid_input() -> None:
    result = validate_book_limit(UnitKind.MONEY, currency=None)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_lots_limit_is_policy_rejection_at_template_validation() -> None:
    result = validate_book_limit(UnitKind.QUANTITY)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert "lots" in str(result.context["reason"])


def test_other_unit_kinds_may_not_express_a_limit() -> None:
    result = validate_book_limit(UnitKind.PRICE_DELTA)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_unrecognised_unit_kind_is_invalid_input() -> None:
    result = validate_book_limit("furlongs")
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
