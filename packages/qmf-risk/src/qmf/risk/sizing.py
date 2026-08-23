"""Story 10.2 — the units-only sizing shape and the B-split (COMP-QMF-RISK).

The replacement sizing shape carries **units only, no ratified values** (AD-40;
DEC-0154, DEC-0157). A Book's ``money_rules`` section declares each sizing variable
with a unit-kind from the closed ``qmf-core`` vocabulary and an exact value or an
explicit :class:`~qmf.risk.grammar.NotYetRuled` blank — never a spine constant:

* ``book_capital`` [``money``] — the binding's virtual-ledger equity at period-open;
* ``loss_floor`` [``money``] — **the same number the kill line names**, one value read
  by both the sizing ladder and the ``control_policy`` kill line, never two floors
  that drift (DEC-0150, DEC-0154);
* ``loss_runway`` [``money``] — ``book_capital − loss_floor``;
* ``period_loss_budget`` [``money``] — the runway spread across ``runway_periods``;
* ``r_unit_price`` [``rate``] — ``period_loss_budget ÷ seat_loss_run_allowance``, the
  Money-per-``r_multiple`` rate that prices one R;
* ``seat_loss_run_allowance`` [``r_multiple``] — the money-ladder divisor;
* ``seat_r_ceiling`` [``r_multiple``] — bounded ``seat_r_ceiling ≤ seat_loss_run_allowance``
  (pure R-space, no money on either side — the sound re-expression that superseded the
  dead FORM-0006);
* ``position_risk_amount`` [``money``] — ``requested_r × r_unit_price``, frozen at
  admission.

The **B split** closes a legacy defect where one symbol ``B`` did two unrelated jobs
(bench depth in loss events, and a divisor in the money ladder), so changing the bench
rule silently re-sized every seat. Two typed variables replace it — a ``count``
``bench_consecutive_loss_threshold`` in ``leash_grammar`` and an ``r_multiple``
``seat_loss_run_allowance`` in ``money_rules`` — and **the unit-kind checker refuses a
``count`` standing where an ``r_multiple`` is declared** (AD-40; DEC-0154, DEC-0155).

This module validates the *template* shape — the declared unit-kind of every sizing
variable and the pure-R value bound — never the ladder's runtime evaluation against
live book state (that is the node's, DEC-0142). Imports only ``qmf-core`` and sibling
``qmf.risk`` modules; nothing imports ``qmf.risk`` (default-deny, L30/DEC-0120).
Ratified ``defined-unwired`` surface — no wiring is authorized here (DEC-0158).
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

from qmf.core import ExactRational, Money, Ok, Result, TypedRefusal, UnitKind, is_refusal
from qmf.risk._common import invalid, policy
from qmf.risk.grammar import NotYetRuled, TemplateSection

__all__ = [
    "BENCH_THRESHOLD_VARIABLE",
    "LEASH_B_SPLIT_UNIT_KINDS",
    "MONEY_RULES_UNIT_KINDS",
    "SEAT_LOSS_RUN_ALLOWANCE_VARIABLE",
    "check_b_split",
    "check_seat_r_ceiling",
    "reconcile_loss_floor",
    "validate_money_rules",
]

# The name of the B-split's r_multiple divisor (money_rules) and its count sibling
# (leash_grammar) — declared apart so a count never stands where an r_multiple does.
SEAT_LOSS_RUN_ALLOWANCE_VARIABLE: Final[str] = "seat_loss_run_allowance"
BENCH_THRESHOLD_VARIABLE: Final[str] = "bench_consecutive_loss_threshold"
_SEAT_R_CEILING_VARIABLE: Final[str] = "seat_r_ceiling"

# The units-only ``money_rules`` sizing shape: every required variable keyed to the
# unit-kind it must be DECLARED with. No values live here — the shape carries
# unit-kinds only, and every real number is a configurable UI-editable variable with
# no spine value (DEC-0154, DEC-0157). A variable declared with any other unit-kind
# is refused (the B-split: seat_loss_run_allowance is an r_multiple, never a count).
MONEY_RULES_UNIT_KINDS: Final[MappingProxyType[str, UnitKind]] = MappingProxyType(
    {
        "book_capital": UnitKind.MONEY,
        "loss_floor": UnitKind.MONEY,
        "loss_runway": UnitKind.MONEY,
        "period_loss_budget": UnitKind.MONEY,
        "r_unit_price": UnitKind.RATE,
        "seat_loss_run_allowance": UnitKind.R_MULTIPLE,
        "seat_r_ceiling": UnitKind.R_MULTIPLE,
        "position_risk_amount": UnitKind.MONEY,
    }
)

# The B-split's leash_grammar side: the bench threshold is a count, keyed per bot or
# bot family (DEC-0155). Declared here so check_b_split reads one source of truth.
LEASH_B_SPLIT_UNIT_KINDS: Final[MappingProxyType[str, UnitKind]] = MappingProxyType(
    {BENCH_THRESHOLD_VARIABLE: UnitKind.COUNT}
)


def _require_section(field: str, section: object, expected_name: str) -> TemplateSection | None:
    """Return ``section`` if it is a :class:`TemplateSection` of the expected name."""
    if isinstance(section, TemplateSection) and section.name == expected_name:
        return section
    return None


def validate_money_rules(section: object) -> Result[TemplateSection]:
    """Validate the units-only ``money_rules`` sizing shape (AD-40; DEC-0154).

    ``section`` must be a :class:`~qmf.risk.grammar.TemplateSection` named
    ``money_rules``. Every variable in :data:`MONEY_RULES_UNIT_KINDS` must be declared
    with exactly its required unit-kind — a missing one, or one declared with the
    wrong unit-kind (a ``count`` where an ``r_multiple`` belongs), is ``invalid
    input``. Values may be exact or explicit :class:`~qmf.risk.grammar.NotYetRuled`
    blanks — the shape ratifies **no values**. When both ``seat_r_ceiling`` and
    ``seat_loss_run_allowance`` are ruled, ``seat_r_ceiling ≤ seat_loss_run_allowance``
    is enforced (:func:`check_seat_r_ceiling`). Returns the validated section.
    """
    resolved = _require_section("section", section, "money_rules")
    if resolved is None:
        return invalid(
            "section",
            "the sizing shape is a TemplateSection named 'money_rules'",
            given=repr(section),
        )
    for name, expected_kind in MONEY_RULES_UNIT_KINDS.items():
        variable = resolved.variables.get(name)
        if variable is None:
            return invalid(
                "money_rules",
                "the units-only sizing shape is missing a required variable",
                missing=name,
                expected_unit_kind=expected_kind.value,
            )
        if variable.unit_kind is not expected_kind:
            return invalid(
                "money_rules",
                "a sizing variable is declared with the wrong unit-kind; the B-split holds "
                "(a count never stands where an r_multiple is declared)",
                variable=name,
                declared=variable.unit_kind.value,
                expected=expected_kind.value,
            )
    ceiling = resolved.variables[_SEAT_R_CEILING_VARIABLE].value
    allowance = resolved.variables[SEAT_LOSS_RUN_ALLOWANCE_VARIABLE].value
    bound = check_seat_r_ceiling(ceiling, allowance)
    if is_refusal(bound):
        return bound
    return Ok(resolved)


def check_seat_r_ceiling(seat_r_ceiling: object, seat_loss_run_allowance: object) -> Result[None]:
    """Enforce ``seat_r_ceiling ≤ seat_loss_run_allowance`` in pure R-space (DEC-0154).

    The sound re-expression that superseded the dead FORM-0006: both operands are
    ``r_multiple`` with **no money on either side**. Both must be ``r-multiple``
    :class:`~qmf.core.ExactRational` values (else ``invalid input``) — unless either is
    an explicit :class:`~qmf.risk.grammar.NotYetRuled` blank, in which case the value
    bound cannot yet be checked and the blank-blocks-live-money rule stands elsewhere,
    so this passes. A ruled ceiling above the ruled allowance is a ``policy rejection``.
    """
    if isinstance(seat_r_ceiling, NotYetRuled) or isinstance(seat_loss_run_allowance, NotYetRuled):
        return Ok(None)
    if not isinstance(seat_r_ceiling, ExactRational) or (
        seat_r_ceiling.unit_kind is not UnitKind.R_MULTIPLE
    ):
        return invalid(
            "seat_r_ceiling",
            "seat_r_ceiling is a ruled r-multiple ExactRational or a not-yet-ruled blank",
            given=repr(seat_r_ceiling),
        )
    if not isinstance(seat_loss_run_allowance, ExactRational) or (
        seat_loss_run_allowance.unit_kind is not UnitKind.R_MULTIPLE
    ):
        return invalid(
            "seat_loss_run_allowance",
            "seat_loss_run_allowance is a ruled r-multiple ExactRational or a not-yet-ruled blank",
            given=repr(seat_loss_run_allowance),
        )
    if seat_r_ceiling.as_fraction() > seat_loss_run_allowance.as_fraction():
        return policy(
            "seat_r_ceiling",
            "seat_r_ceiling must not exceed seat_loss_run_allowance (pure R-space, no money "
            "on either side)",
            seat_r_ceiling=str(seat_r_ceiling.as_fraction()),
            seat_loss_run_allowance=str(seat_loss_run_allowance.as_fraction()),
        )
    return Ok(None)


def check_b_split(money_rules: object, leash_grammar: object) -> Result[None]:
    """Enforce the B-split across the two sections (AD-40; DEC-0154, DEC-0155).

    ``seat_loss_run_allowance`` must be declared ``r_multiple`` in ``money_rules`` and
    ``bench_consecutive_loss_threshold`` must be declared ``count`` in ``leash_grammar``
    — the unit-kind checker refuses a ``count`` standing where an ``r_multiple`` is
    declared, and vice versa. A missing variable, a wrong section, or a wrong declared
    unit-kind is ``invalid input``. Returns ``Ok(None)`` when the split holds.
    """
    money_section = _require_section("money_rules", money_rules, "money_rules")
    if money_section is None:
        return invalid(
            "money_rules",
            "the B-split reads a TemplateSection named 'money_rules'",
            given=repr(money_rules),
        )
    leash_section = _require_section("leash_grammar", leash_grammar, "leash_grammar")
    if leash_section is None:
        return invalid(
            "leash_grammar",
            "the B-split reads a TemplateSection named 'leash_grammar'",
            given=repr(leash_grammar),
        )
    allowance_bad = _require_declared_kind(
        money_section, SEAT_LOSS_RUN_ALLOWANCE_VARIABLE, UnitKind.R_MULTIPLE
    )
    if allowance_bad is not None:
        return allowance_bad
    bench_bad = _require_declared_kind(leash_section, BENCH_THRESHOLD_VARIABLE, UnitKind.COUNT)
    if bench_bad is not None:
        return bench_bad
    return Ok(None)


def _require_declared_kind(
    section: TemplateSection, name: str, expected_kind: UnitKind
) -> TypedRefusal | None:
    """Return a refusal if ``section`` lacks ``name`` at ``expected_kind``, else ``None``."""
    variable = section.variables.get(name)
    if variable is None:
        return invalid(
            "b_split",
            "the B-split requires a declared variable that is absent",
            section=section.name,
            missing=name,
            expected_unit_kind=expected_kind.value,
        )
    if variable.unit_kind is not expected_kind:
        return invalid(
            "b_split",
            "a B-split variable is declared with the wrong unit-kind; a count never stands "
            "where an r_multiple is declared",
            section=section.name,
            variable=name,
            declared=variable.unit_kind.value,
            expected=expected_kind.value,
        )
    return None


def reconcile_loss_floor(loss_floor: object, kill_line: object) -> Result[None]:
    """Enforce one floor: ``loss_floor`` is the same number the kill line names (DEC-0150).

    The sizing ladder's ``loss_floor`` and the ``control_policy`` kill-line value are
    **one value, one name, read by both** — never two floors that drift. Both ruled
    :class:`~qmf.core.Money` values must be equal in magnitude and currency; two equal
    values pass, a mismatch is a ``policy rejection``. Two matching
    :class:`~qmf.risk.grammar.NotYetRuled` blanks (same gap reference) pass; a ruled
    value paired with a blank, or two blanks awaiting different gaps, has drifted and
    is refused. A non-Money, non-blank value is ``invalid input``.
    """
    floor_blank = isinstance(loss_floor, NotYetRuled)
    kill_blank = isinstance(kill_line, NotYetRuled)
    if floor_blank or kill_blank:
        if floor_blank and kill_blank:
            if loss_floor.gap_ref == kill_line.gap_ref:
                return Ok(None)
            return policy(
                "loss_floor",
                "loss_floor and the kill line are one number; two blanks awaiting different "
                "gaps have drifted",
                loss_floor_gap=loss_floor.gap_ref,
                kill_line_gap=kill_line.gap_ref,
            )
        return policy(
            "loss_floor",
            "loss_floor is the same number the kill line names; a ruled value paired with a "
            "not-yet-ruled blank has drifted",
        )
    if not isinstance(loss_floor, Money):
        return invalid(
            "loss_floor",
            "loss_floor is a ruled Money(numeraire) value or a not-yet-ruled blank",
            given=repr(loss_floor),
        )
    if not isinstance(kill_line, Money):
        return invalid(
            "kill_line",
            "the kill-line value is a ruled Money(numeraire) value or a not-yet-ruled blank",
            given=repr(kill_line),
        )
    if loss_floor.currency != kill_line.currency or (
        loss_floor.as_fraction() != kill_line.as_fraction()
    ):
        return policy(
            "loss_floor",
            "loss_floor and the kill line must be one value, one name — they have drifted",
            loss_floor=f"{loss_floor.as_fraction()} {loss_floor.currency}",
            kill_line=f"{kill_line.as_fraction()} {kill_line.currency}",
        )
    return Ok(None)
