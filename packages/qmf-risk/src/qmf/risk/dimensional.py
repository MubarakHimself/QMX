"""Story 10.1 — the dimensional law and the FORM-0006 negative test (COMP-QMF-RISK).

The dimensional law is what makes a second FORM-0006 **undeclarable** (AD-40;
DEC-0154). Every declared variable carries a unit-kind from the closed ``qmf-core``
:class:`~qmf.core.UnitKind` vocabulary (see :mod:`qmf.risk.grammar`); every formula
declares the unit-kind of each input and its output; and a **symbolic checker
refuses on mismatch** — addition and subtraction require identical unit-kinds, and
multiplication and division follow a pinned dimensional table, so a ``count`` can
never stand where an ``r-multiple`` is declared.

The checker is symbolic — it reasons over *unit-kinds*, never numbers: this module
never evaluates the sizing ladder against live book state (that evaluation is the
node's, DEC-0142). Each ratified formula additionally ships an **executable worked
example** — concrete exact inputs and the expected exact output — that the Tier-2
suite recomputes by invoking the cited ``qmf-core`` value arithmetic itself, never
a linter-local re-implementation of the governed formula (CT-22 Layer 1; DEC-0146).
The worked-example numbers are illustrative, non-authoritative demonstration inputs
— they are **not** ratified thresholds or spine values (every risk number is a
configurable UI-editable variable with no spine value, DEC-0157).

The dead **FORM-0006** is retained as the checker's permanent negative test: a
declared formula whose derived output disagrees with its declared output, refused
every run — because a dead formula that can still be typed is a dead formula that
comes back (DEC-0077, DEC-0154). Its pure-R-space re-expression,
``seat_r_ceiling ≤ seat_loss_run_allowance``, is the sound
:data:`SEAT_R_CEILING_CONSTRAINT`.

Imports only ``qmf-core`` and the sibling grammar module; nothing imports
``qmf.risk`` (default-deny, L30/DEC-0120). Ratified ``defined-unwired`` surface.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import cast

from qmf.core import (
    ExactRational,
    Money,
    Ok,
    Result,
    TypedRefusal,
    UnitKind,
    is_refusal,
)
from qmf.risk._common import clean_str, coerce_enum, invalid
from qmf.risk.grammar import VariableValue, value_unit_kind

__all__ = [
    "FORM_0006",
    "LADDER_FORMULAS",
    "SEAT_R_CEILING_CONSTRAINT",
    "BinOp",
    "ComparisonOp",
    "ConstraintSpec",
    "FormulaOp",
    "FormulaSpec",
    "Ref",
    "WorkedExample",
    "check_constraint",
    "check_formula",
    "derive_unit_kind",
]

_DIMENSIONAL_FORMAT_VERSION = 1


class FormulaOp(StrEnum):
    """The arithmetic operators the symbolic checker knows (AD-40; DEC-0154)."""

    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"


class ComparisonOp(StrEnum):
    """The comparison operators a constraint may use (AD-40; DEC-0146, DEC-0154).

    A comparison yields truth, not a value: it produces no unit-kind, and its two
    sides must share a unit-kind (``seat_r_ceiling ≤ seat_loss_run_allowance`` is
    pure ``r-multiple`` space). The set mirrors CT-22's admission-bar comparisons.
    """

    AT_LEAST = "at-least"
    AT_MOST = "at-most"
    WITHIN_BAND = "within-band"
    EQUAL = "equal"


@dataclass(frozen=True, slots=True)
class Ref:
    """A reference to a declared formula input by name."""

    name: str


@dataclass(frozen=True, slots=True)
class BinOp:
    """A binary arithmetic node over two sub-expressions (AD-40; DEC-0154)."""

    op: FormulaOp
    left: FormulaExpr
    right: FormulaExpr


# A symbolic formula expression: a leaf input reference or a binary arithmetic
# node. Numbers never appear — the tree carries dimensions, not values.
FormulaExpr = Ref | BinOp


def _mul_key(left: UnitKind, right: UnitKind) -> tuple[str, str]:
    """A canonical, order-independent key for the commutative multiply table."""
    return cast("tuple[str, str]", tuple(sorted((left.value, right.value))))


# Multiplication is commutative, so the table is keyed order-independently. The
# only ratified money-path product is r-multiple x rate(money-per-r) = money
# (position_risk_amount = requested_r x r_unit_price); further products are
# added as spine amendments, never invented per-Book (DEC-0154).
_MUL_TABLE: dict[tuple[str, str], UnitKind] = {
    _mul_key(UnitKind.R_MULTIPLE, UnitKind.RATE): UnitKind.MONEY,
}

# Division is directional, so the table is keyed ``(numerator, denominator)``.
# These are the ratified sizing-ladder quotients: ``money ÷ count = money``
# (``period_loss_budget``), ``money ÷ r-multiple = rate`` (``r_unit_price``), and
# the dimensionless ratios a sensor/attribution read forms (DEC-0153, DEC-0154).
_DIV_TABLE: dict[tuple[UnitKind, UnitKind], UnitKind] = {
    (UnitKind.MONEY, UnitKind.COUNT): UnitKind.MONEY,
    (UnitKind.MONEY, UnitKind.R_MULTIPLE): UnitKind.RATE,
    (UnitKind.PRICE_DELTA, UnitKind.PRICE_DELTA): UnitKind.DIMENSIONLESS_RATIO,
    (UnitKind.MONEY, UnitKind.MONEY): UnitKind.DIMENSIONLESS_RATIO,
}


def _apply(op: FormulaOp, left: UnitKind, right: UnitKind) -> UnitKind | None:
    """The dimensional result of one operation, or ``None`` on a mismatch.

    Addition and subtraction require identical unit-kinds; multiplication and
    division consult the pinned tables. ``None`` means the operation is
    dimensionally undeclarable — the checker turns it into a refusal.
    """
    if op in (FormulaOp.ADD, FormulaOp.SUBTRACT):
        return left if left is right else None
    if op is FormulaOp.MULTIPLY:
        return _MUL_TABLE.get(_mul_key(left, right))
    return _DIV_TABLE.get((left, right))


def derive_unit_kind(expr: FormulaExpr, inputs: Mapping[str, UnitKind]) -> Result[UnitKind]:
    """Symbolically derive the unit-kind an expression produces (AD-40; DEC-0154).

    Resolves each :class:`Ref` against the declared ``inputs`` and applies the
    dimensional algebra bottom-up. An unresolved reference or a dimensional
    mismatch (adding a ``count`` to a ``money``, dividing to claim a unit the table
    does not yield) is an ``invalid input`` refusal, returned never raised.
    """
    if isinstance(expr, Ref):
        kind = inputs.get(expr.name)
        if kind is None:
            return invalid(
                "expression",
                "a formula references an input it does not declare",
                reference=expr.name,
                declared=sorted(inputs),
            )
        return Ok(kind)
    left = derive_unit_kind(expr.left, inputs)
    if is_refusal(left):
        return left
    right = derive_unit_kind(expr.right, inputs)
    if is_refusal(right):
        return right
    result = _apply(expr.op, left.value, right.value)
    if result is None:
        return invalid(
            "expression",
            "dimensional mismatch: the operation is undeclarable over these unit-kinds "
            "(a count cannot stand where an r-multiple is declared)",
            op=expr.op.value,
            left=left.value.value,
            right=right.value.value,
        )
    return Ok(result)


@dataclass(frozen=True, slots=True)
class WorkedExample:
    """An executable worked example for a formula (CT-22 Layer 1; DEC-0146).

    Carries concrete exact ``inputs`` (one per declared formula input) and the
    ``expected_output`` — all ``qmf-core`` exact values, fp1-clean. The Tier-2
    suite recomputes it by invoking the cited ``qmf-core`` value arithmetic and
    asserts equality; this module never evaluates it numerically (DEC-0142). The
    numbers are illustrative, non-authoritative demonstration data, never spine
    values (DEC-0157).
    """

    inputs: Mapping[str, VariableValue]
    expected_output: VariableValue

    def __post_init__(self) -> None:
        object.__setattr__(self, "inputs", MappingProxyType(dict(self.inputs)))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this worked example."""
        return {
            "class": "worked-example",
            "inputs": {name: value.fp1_identity() for name, value in self.inputs.items()},
            "expected_output": self.expected_output.fp1_identity(),
            "format_version": _DIMENSIONAL_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class FormulaSpec:
    """A declared value-producing formula under the dimensional law (AD-40; DEC-0154).

    Declares a ``formula_id``, the unit-kind of every ``inputs`` reference, the
    ``output`` unit-kind, the symbolic ``expression``, and an optional
    :class:`WorkedExample`. The unchecked constructor is the trusted-internal path
    (it is how the dead :data:`FORM_0006` is carried as data); :meth:`try_create`
    is the validating path that additionally runs the symbolic checker, so an
    unsound formula is undeclarable through it.
    """

    formula_id: str
    inputs: Mapping[str, UnitKind]
    output: UnitKind
    expression: FormulaExpr
    worked_example: WorkedExample | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "inputs", MappingProxyType(dict(self.inputs)))

    @classmethod
    def try_create(
        cls,
        formula_id: object,
        inputs: object,
        output: object,
        expression: object,
        worked_example: object = None,
    ) -> Result[FormulaSpec]:
        """Validate and build a dimensionally-sound :class:`FormulaSpec`.

        Refuses a blank id, an empty/ill-typed input map, an output outside the
        closed vocabulary, an expression whose derived unit-kind disagrees with the
        declared output (the symbolic checker — this is what makes a second
        FORM-0006 undeclarable), and a worked example whose dimensions disagree with
        the declaration. Returned never raised.
        """
        token = clean_str(formula_id)
        if token is None:
            return invalid(
                "formula_id", "a formula declares a non-empty id", given=repr(formula_id)
            )
        resolved_inputs = _coerce_inputs(inputs)
        if is_refusal(resolved_inputs):
            return resolved_inputs
        resolved_output = coerce_enum(UnitKind, output)
        if resolved_output is None:
            return invalid(
                "output",
                "a formula declares an output unit-kind from the closed AD-40 vocabulary",
                given=repr(output),
                allowed=[member.value for member in UnitKind],
            )
        if not isinstance(expression, (Ref, BinOp)):
            return invalid(
                "expression",
                "a formula expression is a Ref or a BinOp over declared inputs",
                given=repr(expression),
            )
        spec = cls(
            formula_id=token,
            inputs=resolved_inputs.value,
            output=resolved_output,
            expression=expression,
            worked_example=None,
        )
        checked = check_formula(spec)
        if is_refusal(checked):
            return checked
        if worked_example is not None:
            if not isinstance(worked_example, WorkedExample):
                return invalid(
                    "worked_example",
                    "a worked example is a WorkedExample value",
                    given=repr(worked_example),
                )
            example_refusal = _validate_worked_example(spec, worked_example)
            if example_refusal is not None:
                return example_refusal
            spec = cls(
                formula_id=token,
                inputs=resolved_inputs.value,
                output=resolved_output,
                expression=expression,
                worked_example=worked_example,
            )
        return Ok(spec)

    def check(self) -> Result[UnitKind]:
        """Run the symbolic checker on this formula (see :func:`check_formula`)."""
        return check_formula(self)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this formula."""
        content: dict[str, object] = {
            "class": "formula-spec",
            "formula_id": self.formula_id,
            "inputs": {name: kind.value for name, kind in self.inputs.items()},
            "output": self.output.value,
            "expression": _expression_content(self.expression),
            "format_version": _DIMENSIONAL_FORMAT_VERSION,
        }
        if self.worked_example is not None:
            content["worked_example"] = self.worked_example.fp1_identity()
        return content


def check_formula(spec: FormulaSpec) -> Result[UnitKind]:
    """The symbolic dimensional checker (AD-40; DEC-0154).

    Derives the expression's unit-kind from the declared inputs and requires it to
    equal the declared output. A mismatch — the FORM-0006 defect — is an
    ``invalid input`` refusal. Returns the derived (and confirmed) output unit-kind
    on success.
    """
    derived = derive_unit_kind(spec.expression, spec.inputs)
    if is_refusal(derived):
        return derived
    if derived.value is not spec.output:
        return invalid(
            "output",
            "the formula's derived unit-kind disagrees with its declared output; the "
            "dimensional checker refuses it (a dead formula that can still be typed comes "
            "back — FORM-0006)",
            formula_id=spec.formula_id,
            declared_output=spec.output.value,
            derived_output=derived.value.value,
        )
    return Ok(derived.value)


@dataclass(frozen=True, slots=True)
class ConstraintSpec:
    """A declared comparison constraint (AD-40; DEC-0146, DEC-0154).

    A comparison produces no unit-kind; both sides must share one. This carries the
    two operand unit-kinds and the :class:`ComparisonOp`. ``seat_r_ceiling ≤
    seat_loss_run_allowance`` — pure ``r-multiple`` space — is the sound
    re-expression that supersedes FORM-0006.
    """

    constraint_id: str
    left: UnitKind
    op: ComparisonOp
    right: UnitKind

    @classmethod
    def try_create(
        cls, constraint_id: object, left: object, op: object, right: object
    ) -> Result[ConstraintSpec]:
        """Validate and build a dimensionally-sound :class:`ConstraintSpec`.

        Refuses a blank id, an operand outside the vocabulary, an unknown operator,
        or two sides whose unit-kinds differ (comparison requires identical
        unit-kinds). Returned never raised.
        """
        token = clean_str(constraint_id)
        if token is None:
            return invalid(
                "constraint_id", "a constraint declares a non-empty id", given=repr(constraint_id)
            )
        resolved_left = coerce_enum(UnitKind, left)
        if resolved_left is None:
            return invalid("left", "a constraint operand is a unit-kind", given=repr(left))
        resolved_op = coerce_enum(ComparisonOp, op)
        if resolved_op is None:
            return invalid(
                "op",
                "a constraint declares a comparison operator",
                given=repr(op),
                allowed=[member.value for member in ComparisonOp],
            )
        resolved_right = coerce_enum(UnitKind, right)
        if resolved_right is None:
            return invalid("right", "a constraint operand is a unit-kind", given=repr(right))
        spec = cls(constraint_id=token, left=resolved_left, op=resolved_op, right=resolved_right)
        checked = check_constraint(spec)
        if is_refusal(checked):
            return checked
        return Ok(spec)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this constraint."""
        return {
            "class": "constraint-spec",
            "constraint_id": self.constraint_id,
            "left": self.left.value,
            "op": self.op.value,
            "right": self.right.value,
            "format_version": _DIMENSIONAL_FORMAT_VERSION,
        }


def check_constraint(spec: ConstraintSpec) -> Result[None]:
    """The symbolic checker for a comparison constraint (AD-40; DEC-0154).

    Both sides must share a unit-kind; a mismatch is an ``invalid input`` refusal.
    """
    if spec.left is not spec.right:
        return invalid(
            "operands",
            "comparison requires identical unit-kinds on both sides",
            constraint_id=spec.constraint_id,
            left=spec.left.value,
            right=spec.right.value,
        )
    return Ok(None)


# --- expression / input helpers ---------------------------------------------


def _coerce_inputs(inputs: object) -> Result[Mapping[str, UnitKind]]:
    """Resolve a declared input map ``name -> UnitKind`` (non-empty)."""
    if not isinstance(inputs, Mapping):
        return invalid(
            "inputs",
            "a formula declares its inputs as a name→unit-kind mapping",
            given=repr(type(inputs).__name__),
        )
    input_map = cast("Mapping[object, object]", inputs)
    if len(input_map) == 0:
        return invalid("inputs", "a formula declares at least one input")
    resolved: dict[str, UnitKind] = {}
    for key, kind in input_map.items():
        token = clean_str(key)
        if token is None:
            return invalid("inputs", "an input name is a non-empty string", given=repr(key))
        resolved_kind = coerce_enum(UnitKind, kind)
        if resolved_kind is None:
            return invalid(
                "inputs",
                "an input declares a unit-kind from the closed vocabulary",
                name=token,
                given=repr(kind),
            )
        resolved[token] = resolved_kind
    return Ok(resolved)


def _validate_worked_example(spec: FormulaSpec, example: WorkedExample) -> TypedRefusal | None:
    """Validate a worked example's dimensions against its formula's declaration.

    Returns ``None`` when consistent, or the ``TypedRefusal`` to return. Every
    declared input must be present with a matching unit-kind, no extra inputs may
    appear, and the expected output's unit-kind must equal the declared output.
    This is dimensional validation only — the numeric recompute is a Tier-2 test.
    """
    for name, declared_kind in spec.inputs.items():
        if name not in example.inputs:
            return invalid(
                "worked_example",
                "a worked example is missing a declared input",
                formula_id=spec.formula_id,
                missing=name,
            )
        provided = value_unit_kind(example.inputs[name])
        if provided is not declared_kind:
            return invalid(
                "worked_example",
                "a worked-example input's unit-kind disagrees with the declaration",
                formula_id=spec.formula_id,
                name=name,
                declared=declared_kind.value,
                provided=None if provided is None else provided.value,
            )
    for name in example.inputs:
        if name not in spec.inputs:
            return invalid(
                "worked_example",
                "a worked example supplies an input the formula does not declare",
                formula_id=spec.formula_id,
                extra=name,
            )
    output_kind = value_unit_kind(example.expected_output)
    if output_kind is not spec.output:
        return invalid(
            "worked_example",
            "a worked-example expected output's unit-kind disagrees with the declaration",
            formula_id=spec.formula_id,
            declared=spec.output.value,
            provided=None if output_kind is None else output_kind.value,
        )
    return None


def _expression_content(expr: FormulaExpr) -> dict[str, object]:
    """The canonical fp1 fragment for a symbolic expression tree."""
    if isinstance(expr, Ref):
        return {"node": "ref", "name": expr.name}
    return {
        "node": "binop",
        "op": expr.op.value,
        "left": _expression_content(expr.left),
        "right": _expression_content(expr.right),
    }


# --- the ratified sizing-ladder formulas and the FORM-0006 negative test -----
#
# The worked-example numbers below are ILLUSTRATIVE, non-authoritative
# demonstration inputs — USD (the V1 numeraire) amounts chosen to make the
# arithmetic legible — NEVER ratified thresholds or spine values. Every real risk
# number is a configurable UI-editable variable with no spine value (DEC-0157);
# these exist only so the dimensional law ships an executable worked example per
# formula (CT-22 Layer 1; DEC-0146). Built through the trusted-internal
# constructors so the module carries them as fixed data.

_USD = "USD"

# loss_runway = book_capital - loss_floor   (money - money = money)
_LOSS_RUNWAY = FormulaSpec(
    formula_id="FORM-loss-runway",
    inputs={"book_capital": UnitKind.MONEY, "loss_floor": UnitKind.MONEY},
    output=UnitKind.MONEY,
    expression=BinOp(FormulaOp.SUBTRACT, Ref("book_capital"), Ref("loss_floor")),
    worked_example=WorkedExample(
        inputs={
            "book_capital": Money(value=1_000_000, currency=_USD, scale=2),
            "loss_floor": Money(value=800_000, currency=_USD, scale=2),
        },
        expected_output=Money(value=200_000, currency=_USD, scale=2),
    ),
)

# period_loss_budget = loss_runway ÷ runway_periods   (money ÷ count = money)
_PERIOD_LOSS_BUDGET = FormulaSpec(
    formula_id="FORM-period-loss-budget",
    inputs={"loss_runway": UnitKind.MONEY, "runway_periods": UnitKind.COUNT},
    output=UnitKind.MONEY,
    expression=BinOp(FormulaOp.DIVIDE, Ref("loss_runway"), Ref("runway_periods")),
    worked_example=WorkedExample(
        inputs={
            "loss_runway": Money(value=200_000, currency=_USD, scale=2),
            "runway_periods": ExactRational(numerator=20, denominator=1, unit_kind=UnitKind.COUNT),
        },
        expected_output=Money(value=10_000, currency=_USD, scale=2),
    ),
)

# r_unit_price = period_loss_budget ÷ seat_loss_run_allowance   (money ÷ r = rate)
_R_UNIT_PRICE = FormulaSpec(
    formula_id="FORM-r-unit-price",
    inputs={
        "period_loss_budget": UnitKind.MONEY,
        "seat_loss_run_allowance": UnitKind.R_MULTIPLE,
    },
    output=UnitKind.RATE,
    expression=BinOp(FormulaOp.DIVIDE, Ref("period_loss_budget"), Ref("seat_loss_run_allowance")),
    worked_example=WorkedExample(
        inputs={
            "period_loss_budget": Money(value=10_000, currency=_USD, scale=2),
            "seat_loss_run_allowance": ExactRational(
                numerator=4, denominator=1, unit_kind=UnitKind.R_MULTIPLE
            ),
        },
        expected_output=ExactRational(numerator=25, denominator=1, unit_kind=UnitKind.RATE),
    ),
)

# position_risk_amount = requested_r x r_unit_price   (r x rate = money)
_POSITION_RISK_AMOUNT = FormulaSpec(
    formula_id="FORM-position-risk-amount",
    inputs={"requested_r": UnitKind.R_MULTIPLE, "r_unit_price": UnitKind.RATE},
    output=UnitKind.MONEY,
    expression=BinOp(FormulaOp.MULTIPLY, Ref("requested_r"), Ref("r_unit_price")),
    worked_example=WorkedExample(
        inputs={
            "requested_r": ExactRational(numerator=2, denominator=1, unit_kind=UnitKind.R_MULTIPLE),
            "r_unit_price": ExactRational(numerator=25, denominator=1, unit_kind=UnitKind.RATE),
        },
        expected_output=Money(value=5_000, currency=_USD, scale=2),
    ),
)

# The ratified value-producing sizing-ladder formulas, each dimensionally sound
# and shipping a worked example (DEC-0154).
LADDER_FORMULAS: tuple[FormulaSpec, ...] = (
    _LOSS_RUNWAY,
    _PERIOD_LOSS_BUDGET,
    _R_UNIT_PRICE,
    _POSITION_RISK_AMOUNT,
)

# seat_r_ceiling ≤ seat_loss_run_allowance — the sound pure-R-space re-expression
# that supersedes FORM-0006, with no money on either side (DEC-0154).
SEAT_R_CEILING_CONSTRAINT = ConstraintSpec(
    constraint_id="CONSTRAINT-seat-r-ceiling",
    left=UnitKind.R_MULTIPLE,
    op=ComparisonOp.AT_MOST,
    right=UnitKind.R_MULTIPLE,
)

# FORM-0006 — the permanent negative test. The overloaded legacy symbol ``B`` (a
# count: bench depth) stood as the divisor in the money ladder, so this declares
# ``period_loss_budget[money] ÷ B[count]`` as a rate. The checker derives
# ``money ÷ count = money`` and REFUSES the declared ``rate`` output: a count
# cannot stand where an r-multiple/rate belongs. Carried through the unchecked
# constructor precisely because :meth:`FormulaSpec.try_create` would refuse it
# (DEC-0077, DEC-0154).
FORM_0006 = FormulaSpec(
    formula_id="FORM-0006",
    inputs={"period_loss_budget": UnitKind.MONEY, "B": UnitKind.COUNT},
    output=UnitKind.RATE,
    expression=BinOp(FormulaOp.DIVIDE, Ref("period_loss_budget"), Ref("B")),
    worked_example=None,
)
