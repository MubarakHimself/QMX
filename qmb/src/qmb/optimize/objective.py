"""Study objective, hard constraints, and the read-time winner set (B-8, B-10).

A parameter-optimization Study names ONE objective — a ``measure_identity`` from
the AD-23/AD-41 governed-producer roster plus a ``direction`` in ``{min, max}`` —
and any number of hard ``{measure_identity, op, value}`` constraint filters. The
whole objective-and-constraints config is validated at **Study creation**: an
objective or constraint naming a metric absent from the roster is a typed refusal
returned up front, never deferred to trial time (OPT-8, AD-11); a ``direction``
outside ``{min, max}`` is a typed ``invalid input`` refusal (OPT-5).

The **winner set** is a read-time ranking over ledger ``role = trial`` lines
(:func:`compute_winner_set`). A trial whose result violates any hard constraint is
**excluded** from the winner set yet still appears in the ledger with the violated
constraint named — never silently dropped, never coerced to a zero objective
(OPT-6, B-8). The winner it names carries **no edge claim and no bar verdict** —
every trial keeps its ``optimistic`` taint and the no-verdict rule stands until
GAP-0048 (B-4, B-6, SC-06).

The **minimum-trades gate** rides as a hard constraint over ``total_trades``,
``on by default`` so degenerate zero-trade fits never win. Its floor is a
UI-editable configurable (:data:`MIN_TRADES_FLOOR_KEY`) with **no spine constant**:
a blank floor is permitted and excludes nothing — no threshold number is invented,
thresholds stay deferred (OPT-7, NFR-07, SC-07, L38).

An optional ``target_value`` on the objective lets a completed generation stop the
Study early: :meth:`StudyWinnerSet.target_reached` is true once a constraint-passing
trial meets the target, at which point the orchestrator may transition to a clean
terminal state with the partial winner set preserved (OPT-5, OPT-18). Naming the
winner adds no computation of its own — it is a pure deterministic fold over the
CT-32 measures on the ledger (B-10, NFR-03).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.performance import FORBIDDEN_COMPOSITE_EXPRESSIONS, reject_composite_expression

from qmb._refuse import clean_token, invalid, policy
from qmb.execution.ports import TAINT_OPTIMISTIC, refuse_optimistic_edge_claim
from qmb.ledger.line import ROLE_ABORTED, ROLE_TRIAL, LedgerLine, merge_ledger_lines
from qmb.results.measures import MEASURE_IDENTITIES

__all__ = [
    "DIRECTION_MAX",
    "DIRECTION_MIN",
    "INCOMPLETE_TRIAL_CONSTRAINT_MISSING",
    "INCOMPLETE_TRIAL_CONSTRAINT_UNDEFINED",
    "INCOMPLETE_TRIAL_OBJECTIVE_MISSING",
    "INCOMPLETE_TRIAL_OBJECTIVE_UNDEFINED",
    "INCOMPLETE_TRIAL_REASONS",
    "INCOMPLETE_TRIAL_REFUSED",
    "MIN_TRADES_FLOOR_KEY",
    "MIN_TRADES_GATE_DEFAULT_ON",
    "MIN_TRADES_HAS_SPINE_CONSTANT",
    "MIN_TRADES_MEASURE",
    "MIN_TRADES_OPERATOR",
    "OBJECTIVE_DIRECTIONS",
    "STUDY_CONSTRAINT_CLASS",
    "STUDY_CONSTRAINT_OPERATORS",
    "STUDY_CRITERIA_CLASS",
    "STUDY_CRITERIA_FORMAT_VERSION",
    "STUDY_CRITERIA_KEY",
    "STUDY_OBJECTIVE_CLASS",
    "WINNER_MAKES_BAR_VERDICT",
    "WINNER_MAKES_EDGE_CLAIM",
    "WINNER_ROLE",
    "WINNER_SET_CLASS",
    "WINNER_SET_FORMAT_VERSION",
    "WINNER_VERDICT_DEFERRED_TO",
    "IncompleteTrial",
    "MinTradesGate",
    "ScoredTrial",
    "StudyConstraint",
    "StudyCriteria",
    "StudyObjective",
    "StudyWinnerSet",
    "coerce_study_criteria",
    "compute_winner_set",
    "study_criteria_identity",
]

STUDY_OBJECTIVE_CLASS: Final[str] = "qmb-study-objective"
STUDY_CONSTRAINT_CLASS: Final[str] = "qmb-study-constraint"
STUDY_CRITERIA_CLASS: Final[str] = "qmb-study-criteria"
STUDY_CRITERIA_FORMAT_VERSION: Final[int] = 1
WINNER_SET_CLASS: Final[str] = "qmb-study-winner-set"
WINNER_SET_FORMAT_VERSION: Final[int] = 1
_SCORED_TRIAL_CLASS: Final[str] = "qmb-scored-trial"
_INCOMPLETE_TRIAL_CLASS: Final[str] = "qmb-incomplete-trial"

# The resolved-run-config key the validated criteria are materialized under, so a
# Study's objective + constraints ride in the run-config's fp1 identity — declared
# as config, never a code edit (OPT-2 discipline, mirroring the search space).
STUDY_CRITERIA_KEY: Final[str] = "study_criteria"

# The objective direction the Study declares. The caller states which pole of the
# objective it wants: minimize (e.g. max_drawdown) or maximize (e.g. net_profit).
# A direction outside this pair is a typed invalid-input refusal (OPT-5, AD-11).
DIRECTION_MIN: Final[str] = "min"
DIRECTION_MAX: Final[str] = "max"
OBJECTIVE_DIRECTIONS: Final[tuple[str, ...]] = (DIRECTION_MIN, DIRECTION_MAX)

# The closed hard-constraint operator vocabulary, exactly as OPT-6 lists it. The
# comparison value is always caller-supplied; no threshold number is invented.
STUDY_CONSTRAINT_OPERATORS: Final[tuple[str, ...]] = ("<", "<=", ">", ">=", "=", "!=")

# The minimum-trades gate (OPT-7): a hard constraint over total_trades, on by
# default so a degenerate zero-trade fit never wins. Its floor is a UI-editable
# configurable with NO spine constant — a blank floor is permitted and excludes
# nothing (no invented threshold; thresholds deferred to the SC-07 sitting).
MIN_TRADES_MEASURE: Final[str] = "total_trades"
MIN_TRADES_OPERATOR: Final[str] = ">="
MIN_TRADES_FLOOR_KEY: Final[str] = "qmb_study_min_trades_floor"
MIN_TRADES_GATE_DEFAULT_ON: Final[bool] = True
MIN_TRADES_HAS_SPINE_CONSTANT: Final[bool] = False

# The winner set publishes a read-time ranking and nothing more: it names no edge
# and mints no bar verdict until GAP-0048 rules the fidelity taxonomy (B-6, SC-06).
WINNER_ROLE: Final[str] = ROLE_TRIAL
WINNER_MAKES_EDGE_CLAIM: Final[bool] = False
WINNER_MAKES_BAR_VERDICT: Final[bool] = False
WINNER_VERDICT_DEFERRED_TO: Final[str] = "GAP-0048"

# Reasons a trial is reported in the refused/incomplete list, never ranked and
# never coerced to a zero objective (AD-11).
INCOMPLETE_TRIAL_REFUSED: Final[str] = "refused"
INCOMPLETE_TRIAL_OBJECTIVE_UNDEFINED: Final[str] = "objective-undefined"
INCOMPLETE_TRIAL_OBJECTIVE_MISSING: Final[str] = "objective-missing"
INCOMPLETE_TRIAL_CONSTRAINT_UNDEFINED: Final[str] = "constraint-undefined"
INCOMPLETE_TRIAL_CONSTRAINT_MISSING: Final[str] = "constraint-missing"
INCOMPLETE_TRIAL_REASONS: Final[tuple[str, ...]] = (
    INCOMPLETE_TRIAL_REFUSED,
    INCOMPLETE_TRIAL_OBJECTIVE_UNDEFINED,
    INCOMPLETE_TRIAL_OBJECTIVE_MISSING,
    INCOMPLETE_TRIAL_CONSTRAINT_UNDEFINED,
    INCOMPLETE_TRIAL_CONSTRAINT_MISSING,
)


def study_criteria_identity() -> dict[str, object]:
    """Identity-bearing objective-and-constraints schema fields. SemVer omitted."""
    return {
        "class": STUDY_CRITERIA_CLASS,
        "constraint_operators": STUDY_CONSTRAINT_OPERATORS,
        "format_version": STUDY_CRITERIA_FORMAT_VERSION,
        "min_trades_default_on": MIN_TRADES_GATE_DEFAULT_ON,
        "min_trades_floor_key": MIN_TRADES_FLOOR_KEY,
        "min_trades_has_spine_constant": MIN_TRADES_HAS_SPINE_CONSTANT,
        "objective_directions": OBJECTIVE_DIRECTIONS,
        "run_config_key": STUDY_CRITERIA_KEY,
        "winner_makes_bar_verdict": WINNER_MAKES_BAR_VERDICT,
        "winner_makes_edge_claim": WINNER_MAKES_EDGE_CLAIM,
        "winner_role": WINNER_ROLE,
        "winner_verdict_deferred_to": WINNER_VERDICT_DEFERRED_TO,
    }


# --- objective ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StudyObjective:
    """One named objective metric with a direction and an optional target (OPT-5).

    ``measure`` is a ``measure_identity`` from the AD-23/AD-41 roster; ``direction``
    is ``min`` or ``max`` (never a hard-wired compound score); ``target_value`` is
    the optional exact early-stop threshold. A binary float never enters identity.
    """

    measure: str
    direction: str
    target_value: Fraction | None = None
    target_unit_kind: str | None = None
    target_currency: str | None = None

    @classmethod
    def try_create(
        cls,
        measure: object,
        direction: object,
        *,
        target_value: object = None,
        target_unit_kind: object = None,
        target_currency: object = None,
    ) -> Result[StudyObjective]:
        """Validate and build a :class:`StudyObjective`, value-or-refusal (OPT-5, OPT-8)."""
        identity = _as_roster_identity(measure, "objective")
        if is_refusal(identity):
            return identity
        parsed_direction = _as_direction(direction)
        if is_refusal(parsed_direction):
            return parsed_direction
        target: Fraction | None = None
        unit: str | None = clean_token(target_unit_kind) if target_unit_kind is not None else None
        currency: str | None = clean_token(target_currency) if target_currency is not None else None
        if target_value is not None:
            magnitude = _coerce_exact_value(target_value)
            if is_refusal(magnitude):
                return magnitude
            target, value_currency, value_kind = magnitude.value
            currency = currency if currency is not None else value_currency
            unit = unit if unit is not None else value_kind
        return Ok(
            cls(
                measure=identity.value,
                direction=parsed_direction.value,
                target_value=target,
                target_unit_kind=unit,
                target_currency=currency,
            )
        )

    @property
    def has_target(self) -> bool:
        """Whether an optional early-stop target is declared (OPT-5)."""
        return self.target_value is not None

    def meets_target(self, magnitude: Fraction) -> bool:
        """Whether ``magnitude`` reaches the target under the objective's direction.

        ``max`` reaches the target at or above it; ``min`` at or below it. No target
        is never reached — the Study runs to its budget rather than stop early.
        """
        if self.target_value is None:
            return False
        if self.direction == DIRECTION_MAX:
            return magnitude >= self.target_value
        return magnitude <= self.target_value

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. The exact target is stored as num/den."""
        content: dict[str, object] = {
            "class": STUDY_OBJECTIVE_CLASS,
            "direction": self.direction,
            "measure": self.measure,
        }
        if self.target_value is not None:
            content["target_value_den"] = self.target_value.denominator
            content["target_value_num"] = self.target_value.numerator
        if self.target_unit_kind is not None:
            content["target_unit_kind"] = self.target_unit_kind
        if self.target_currency is not None:
            content["target_currency"] = self.target_currency
        return content


# --- hard constraint ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StudyConstraint:
    """One hard ``{measure_identity, op, value}`` constraint filter (OPT-6).

    ``measure`` is a roster ``measure_identity``; ``operator`` is one of
    :data:`STUDY_CONSTRAINT_OPERATORS`; ``value`` is the exact caller-supplied
    comparison magnitude — never a binary float, never an invented threshold.
    ``currency`` is carried when the value is Money so a cross-currency bound is
    refused rather than compared by bare magnitude.
    """

    measure: str
    operator: str
    value: Fraction
    unit_kind: str | None = None
    currency: str | None = None

    @classmethod
    def try_create(
        cls,
        measure: object,
        operator: object,
        value: object,
        *,
        unit_kind: object = None,
        currency: object = None,
    ) -> Result[StudyConstraint]:
        """Validate and build a :class:`StudyConstraint`, value-or-refusal (OPT-6, OPT-8)."""
        identity = _as_roster_identity(measure, "constraint")
        if is_refusal(identity):
            return identity
        op = _as_operator(operator)
        if is_refusal(op):
            return op
        magnitude = _coerce_exact_value(value)
        if is_refusal(magnitude):
            return magnitude
        parsed_value, value_currency, value_kind = magnitude.value
        declared_currency = clean_token(currency) if currency is not None else value_currency
        declared_kind = clean_token(unit_kind) if unit_kind is not None else value_kind
        return Ok(
            cls(
                measure=identity.value,
                operator=op.value,
                value=parsed_value,
                unit_kind=declared_kind,
                currency=declared_currency,
            )
        )

    def evaluate(self, magnitude: _Magnitude) -> Result[bool]:
        """Whether the trial's exact metric magnitude satisfies this constraint."""
        if (
            self.currency is not None
            and magnitude.currency is not None
            and self.currency != magnitude.currency
        ):
            return policy(
                "currency",
                "a money constraint bound must share the metric's currency; there is "
                "no silent conversion",
                metric=self.measure,
                bound_currency=self.currency,
                metric_currency=magnitude.currency,
            )
        left = magnitude.value
        right = self.value
        operator = self.operator
        if operator == "<":
            return Ok(left < right)
        if operator == "<=":
            return Ok(left <= right)
        if operator == ">":
            return Ok(left > right)
        if operator == ">=":
            return Ok(left >= right)
        if operator == "=":
            return Ok(left == right)
        return Ok(left != right)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. The exact value is stored as num/den."""
        content: dict[str, object] = {
            "class": STUDY_CONSTRAINT_CLASS,
            "measure": self.measure,
            "operator": self.operator,
            "value_den": self.value.denominator,
            "value_num": self.value.numerator,
        }
        if self.unit_kind is not None:
            content["unit_kind"] = self.unit_kind
        if self.currency is not None:
            content["currency"] = self.currency
        return content

    def violated_content(self) -> dict[str, object]:
        """The named-constraint record attached to an excluded trial (OPT-6)."""
        return {
            "measure": self.measure,
            "operator": self.operator,
            "value_den": self.value.denominator,
            "value_num": self.value.numerator,
        }


# --- minimum-trades gate -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class MinTradesGate:
    """The minimum-trades gate as a hard constraint, on by default (OPT-7, SC-07).

    ``enabled`` defaults on so degenerate zero-trade fits never win. ``floor`` is a
    UI-editable configurable read from :data:`MIN_TRADES_FLOOR_KEY` with NO spine
    constant — ``None`` is a blank floor, permitted, and excludes nothing: no
    threshold number is invented (thresholds deferred). Only a configured floor
    turns the gate into an active ``total_trades >= floor`` constraint.
    """

    enabled: bool = MIN_TRADES_GATE_DEFAULT_ON
    floor: int | None = None
    configurable_key: str = MIN_TRADES_FLOOR_KEY

    @classmethod
    def resolve(
        cls,
        floor: object = None,
        *,
        enabled: object = MIN_TRADES_GATE_DEFAULT_ON,
    ) -> Result[MinTradesGate]:
        """Build the gate from an optional configured floor (OPT-7).

        A blank (``None``) floor is permitted and invents no number; a configured
        floor is a non-negative exact integer count. The gate is on unless the
        caller turns it off explicitly.
        """
        if not isinstance(enabled, bool):
            return invalid(
                "min_trades_enabled",
                "the minimum-trades gate is on or off; it is a boolean flag",
                given=repr(enabled),
            )
        resolved_floor: int | None
        if floor is None:
            resolved_floor = None
        elif isinstance(floor, bool) or not isinstance(floor, int):
            return invalid(
                "min_trades_floor",
                "the minimum-trades floor is a non-negative exact-integer trade count, "
                "or blank; no threshold number is invented (OPT-7, SC-07)",
                given=repr(floor),
                configurable=MIN_TRADES_FLOOR_KEY,
            )
        elif floor < 0:
            return invalid(
                "min_trades_floor",
                "a trade-count floor is not negative",
                given=repr(floor),
                configurable=MIN_TRADES_FLOOR_KEY,
            )
        else:
            resolved_floor = floor
        return Ok(cls(enabled=enabled, floor=resolved_floor))

    @property
    def is_active(self) -> bool:
        """Whether the gate excludes trials: on AND a floor is configured.

        A blank floor leaves the gate on but excludes nothing — no invented number.
        """
        return self.enabled and self.floor is not None

    def as_constraint(self) -> StudyConstraint | None:
        """The ``total_trades >= floor`` constraint, or None while the floor is blank."""
        if not self.is_active or self.floor is None:
            return None
        return StudyConstraint(
            measure=MIN_TRADES_MEASURE,
            operator=MIN_TRADES_OPERATOR,
            value=Fraction(self.floor),
            unit_kind="count",
        )

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content for the gate. A blank floor is recorded as such."""
        content: dict[str, object] = {
            "class": "qmb-min-trades-gate",
            "configurable_key": self.configurable_key,
            "enabled": self.enabled,
            "has_spine_constant": MIN_TRADES_HAS_SPINE_CONSTANT,
            "measure": MIN_TRADES_MEASURE,
            "operator": MIN_TRADES_OPERATOR,
        }
        content["floor"] = self.floor  # None when blank — no invented number
        return content


# --- objective + constraints config ------------------------------------------


@dataclass(frozen=True, slots=True)
class StudyCriteria:
    """A Study's validated objective-and-constraints config (B-8, B-10, OPT-5..8).

    Validated at Study creation: every objective and constraint metric resolves in
    the roster up front. The config is identity-bearing and materializes as content
    of the resolved run-config, so re-running a Study under the same criteria is
    deterministic and reproducible.
    """

    objective: StudyObjective
    constraints: tuple[StudyConstraint, ...] = ()
    min_trades_gate: MinTradesGate = field(default_factory=MinTradesGate)

    @classmethod
    def try_create(
        cls,
        objective: object,
        *,
        constraints: object = (),
        min_trades_floor: object = None,
        min_trades_enabled: object = MIN_TRADES_GATE_DEFAULT_ON,
    ) -> Result[StudyCriteria]:
        """Admit an objective plus hard constraints at Study creation (OPT-5..8)."""
        parsed_objective = _as_objective(objective)
        if is_refusal(parsed_objective):
            return parsed_objective
        parsed_constraints = _as_constraints(constraints)
        if is_refusal(parsed_constraints):
            return parsed_constraints
        gate = MinTradesGate.resolve(min_trades_floor, enabled=min_trades_enabled)
        if is_refusal(gate):
            return gate
        return Ok(
            cls(
                objective=parsed_objective.value,
                constraints=parsed_constraints.value,
                min_trades_gate=gate.value,
            )
        )

    @property
    def effective_constraints(self) -> tuple[StudyConstraint, ...]:
        """The declared constraints plus the min-trades gate constraint when active."""
        gate_constraint = self.min_trades_gate.as_constraint()
        if gate_constraint is None:
            return self.constraints
        return (*self.constraints, gate_constraint)

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint. Same objective + constraints reproduce it (NFR-03)."""
        return fingerprint(self.fp1_identity())

    def fp1_identity(self) -> dict[str, object]:
        """Canonical, fp1-clean identity content. No binary float enters here."""
        return {
            "class": STUDY_CRITERIA_CLASS,
            "constraints": [item.fp1_identity() for item in self.constraints],
            "format_version": STUDY_CRITERIA_FORMAT_VERSION,
            "min_trades_gate": self.min_trades_gate.fp1_identity(),
            "objective": self.objective.fp1_identity(),
        }

    def run_config_layer(self) -> dict[str, object]:
        """The identity-bearing config layer materializing this criteria (OPT-2)."""
        return {STUDY_CRITERIA_KEY: self.fp1_identity()}


def coerce_study_criteria(declaration: object) -> Result[StudyCriteria]:
    """Validate a Study's objective + constraints at Study creation (OPT-5..8).

    ``declaration`` is an already-built :class:`StudyCriteria`, or a mapping carrying
    ``objective`` (a ``{measure, direction, target_value?}`` mapping or
    :class:`StudyObjective`), an optional ``constraints`` list, and optional
    ``min_trades_floor`` / ``min_trades_enabled``. A metric absent from the roster,
    or a direction outside ``{min, max}``, is refused here — never at trial time.
    """
    if isinstance(declaration, StudyCriteria):
        return Ok(declaration)
    if not isinstance(declaration, Mapping):
        return invalid(
            "declaration",
            "a Study criteria config is a StudyCriteria or a mapping carrying an "
            "`objective` and an optional `constraints` list",
            given=repr(type(declaration).__name__),
        )
    body = cast("Mapping[str, object]", declaration)
    if "objective" not in body:
        return invalid(
            "objective",
            "a Study criteria config names one `objective` { measure, direction }",
            given=sorted(str(key) for key in body),
        )
    return StudyCriteria.try_create(
        body["objective"],
        constraints=body.get("constraints", ()),
        min_trades_floor=body.get("min_trades_floor"),
        min_trades_enabled=body.get("min_trades_enabled", MIN_TRADES_GATE_DEFAULT_ON),
    )


# --- winner set --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ScoredTrial:
    """One trial placed in the winner ordering, or excluded by a hard constraint.

    Carries the ``optimistic`` taint and world label forward and makes no edge
    claim (B-6, SC-06). ``failed_constraints`` is empty for a winner-eligible trial
    and names the violated constraints for a constraint-excluded trial (OPT-6).
    """

    run_id: Fingerprint
    world: str
    objective: str
    objective_num: int
    objective_den: int
    objective_unit_kind: str
    objective_currency: str | None = None
    meets_target: bool = False
    taint: str = TAINT_OPTIMISTIC
    makes_edge_claim: bool = WINNER_MAKES_EDGE_CLAIM
    failed_constraints: tuple[Mapping[str, object], ...] = ()

    @property
    def objective_value(self) -> Fraction:
        """The exact objective magnitude this trial is ordered by."""
        return Fraction(self.objective_num, self.objective_den)

    @property
    def excluded_by_constraint(self) -> bool:
        """Whether a hard constraint held this trial out of the winner set."""
        return bool(self.failed_constraints)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical, fp1-clean identity content. No binary float enters here."""
        content: dict[str, object] = {
            "class": _SCORED_TRIAL_CLASS,
            "makes_edge_claim": self.makes_edge_claim,
            "meets_target": self.meets_target,
            "objective": self.objective,
            "objective_den": self.objective_den,
            "objective_num": self.objective_num,
            "objective_unit_kind": self.objective_unit_kind,
            "run_id": self.run_id.value,
            "taint": self.taint,
            "world": self.world,
        }
        if self.objective_currency is not None:
            content["objective_currency"] = self.objective_currency
        if self.failed_constraints:
            content["failed_constraints"] = [dict(item) for item in self.failed_constraints]
        return content


@dataclass(frozen=True, slots=True)
class IncompleteTrial:
    """A trial excluded from the ordering and never coerced to a zero objective.

    A refusal/``aborted`` trial carries no CT-32 measures; a completed trial whose
    objective or a constraint metric is an :class:`UndefinedMeasure` is reported
    here rather than treated as zero (AD-11).
    """

    run_id: Fingerprint
    world: str
    role: str
    reason: str
    taint: str = TAINT_OPTIMISTIC
    detail: Mapping[str, object] | None = None

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content for one refused/incomplete trial."""
        content: dict[str, object] = {
            "class": _INCOMPLETE_TRIAL_CLASS,
            "reason": self.reason,
            "role": self.role,
            "run_id": self.run_id.value,
            "taint": self.taint,
            "world": self.world,
        }
        if self.detail is not None:
            content["detail"] = dict(self.detail)
        return content


@dataclass(frozen=True, slots=True)
class StudyWinnerSet:
    """The read-time winner set of one Study over its ``role = trial`` ledger lines.

    ``winners`` is ordered best-first under the objective's direction and holds only
    constraint-passing trials; ``excluded`` holds trials a hard constraint held out,
    each naming the violated constraint; ``incomplete`` is the refused/incomplete
    list. The whole object makes no edge claim and no bar verdict (B-4, B-6, SC-06),
    and is a pure deterministic function of the ledger merge (NFR-03).
    """

    objective: str
    direction: str
    world: str
    role: str
    constraints: tuple[StudyConstraint, ...]
    winners: tuple[ScoredTrial, ...]
    excluded: tuple[ScoredTrial, ...]
    incomplete: tuple[IncompleteTrial, ...]
    makes_edge_claim: bool = WINNER_MAKES_EDGE_CLAIM
    makes_bar_verdict: bool = WINNER_MAKES_BAR_VERDICT
    verdict_deferred_to: str = WINNER_VERDICT_DEFERRED_TO

    @property
    def winner(self) -> ScoredTrial | None:
        """The best constraint-passing trial under the direction, or None if empty."""
        return self.winners[0] if self.winners else None

    @property
    def winner_count(self) -> int:
        """Constraint-passing trials placed in the winner ordering."""
        return len(self.winners)

    @property
    def excluded_count(self) -> int:
        """Trials a hard constraint held out of the winner set (OPT-6)."""
        return len(self.excluded)

    @property
    def incomplete_count(self) -> int:
        """Refused/incomplete trials, never coerced to a zero objective."""
        return len(self.incomplete)

    @property
    def target_trials(self) -> tuple[ScoredTrial, ...]:
        """Winner-eligible trials that reach the objective's early-stop target."""
        return tuple(trial for trial in self.winners if trial.meets_target)

    @property
    def target_reached(self) -> bool:
        """Whether a constraint-passing trial meets the target — the Study may stop early."""
        return any(trial.meets_target for trial in self.winners)

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint. Same trials + criteria reproduce it (NFR-03)."""
        return fingerprint(self.fp1_identity())

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Deterministic and reproducible (NFR-03)."""
        return {
            "class": WINNER_SET_CLASS,
            "constraints": [item.fp1_identity() for item in self.constraints],
            "direction": self.direction,
            "excluded": [item.fp1_identity() for item in self.excluded],
            "format_version": WINNER_SET_FORMAT_VERSION,
            "incomplete": [item.fp1_identity() for item in self.incomplete],
            "makes_bar_verdict": self.makes_bar_verdict,
            "makes_edge_claim": self.makes_edge_claim,
            "objective": self.objective,
            "role": self.role,
            "verdict_deferred_to": self.verdict_deferred_to,
            "winners": [item.fp1_identity() for item in self.winners],
            "world": self.world,
        }


def compute_winner_set(
    lines: object,
    criteria: object,
    *,
    world: object,
    role: object = WINNER_ROLE,
) -> Result[StudyWinnerSet]:
    """Name the winner set as a read-time fold over a Study's trial ledger (OPT-6, B-10).

    ``lines`` is the Study's ledger lines (``LedgerLine`` values or fp1-canonical
    mappings); ``criteria`` is a :class:`StudyCriteria` (or a mapping coerced through
    :func:`coerce_study_criteria`). The fold reads only ``role = trial`` completed
    lines, orders the constraint-passing trials by the objective, holds out the
    constraint-violating trials (naming each violated constraint), and reports the
    refused/incomplete trials separately — adding no computation of its own.
    """
    parsed_criteria = coerce_study_criteria(criteria)
    if is_refusal(parsed_criteria):
        return parsed_criteria
    crit = parsed_criteria.value
    parsed_role = _as_trial_role(role)
    if is_refusal(parsed_role):
        return parsed_role
    # Optimistic-tainted evidence claims no edge and gates no money (B-6, FM-9).
    claimed = refuse_optimistic_edge_claim()
    if is_refusal(claimed):
        return claimed
    trial_merge = merge_ledger_lines(lines, world=world, role=parsed_role.value)
    if is_refusal(trial_merge):
        return trial_merge
    aborted_merge = merge_ledger_lines(lines, world=world, role=ROLE_ABORTED)
    if is_refusal(aborted_merge):
        return aborted_merge
    folded = _fold(crit, trial_merge.value, aborted_merge.value)
    if is_refusal(folded):
        return folded
    winners, excluded, incomplete = folded.value
    _order(winners, crit.objective.direction)
    return Ok(
        StudyWinnerSet(
            objective=crit.objective.measure,
            direction=crit.objective.direction,
            world=_world_token(world),
            role=parsed_role.value,
            constraints=crit.effective_constraints,
            winners=tuple(winners),
            excluded=tuple(excluded),
            incomplete=tuple(incomplete),
        )
    )


# --- the fold ----------------------------------------------------------------


class _Buckets:
    """Instance-owned fold accumulators. Never module-global mutable state."""

    __slots__ = ("excluded", "incomplete", "winners")

    def __init__(self) -> None:
        self.winners: list[ScoredTrial] = []
        self.excluded: list[ScoredTrial] = []
        self.incomplete: list[IncompleteTrial] = []


def _fold(
    criteria: StudyCriteria,
    trial_lines: tuple[LedgerLine, ...],
    aborted_lines: tuple[LedgerLine, ...],
) -> Result[tuple[list[ScoredTrial], list[ScoredTrial], list[IncompleteTrial]]]:
    buckets = _Buckets()
    constraints = criteria.effective_constraints
    for line in trial_lines:
        placed = _place_trial(line, criteria.objective, constraints, buckets)
        if is_refusal(placed):
            return placed
    for line in aborted_lines:
        buckets.incomplete.append(
            IncompleteTrial(
                run_id=line.run_id,
                world=line.world.value,
                role=line.role,
                reason=INCOMPLETE_TRIAL_REFUSED,
                detail=_refusal_detail(line),
            )
        )
    buckets.incomplete.sort(key=lambda item: (item.reason, item.run_id.value))
    buckets.excluded.sort(key=lambda item: item.run_id.value)
    return Ok((buckets.winners, buckets.excluded, buckets.incomplete))


def _place_trial(
    line: LedgerLine,
    objective: StudyObjective,
    constraints: tuple[StudyConstraint, ...],
    buckets: _Buckets,
) -> Result[None]:
    """Place one completed trial: winner, constraint-held-out, or incomplete."""
    if line.refusal is not None or line.ct32_fingerprint is None:
        buckets.incomplete.append(
            _incomplete(line, INCOMPLETE_TRIAL_REFUSED, detail=_refusal_detail(line))
        )
        return Ok(None)
    objective_slot = _measure_magnitude(line, objective.measure)
    if is_refusal(objective_slot):
        return objective_slot
    resolved_objective = objective_slot.value
    if resolved_objective is None:
        buckets.incomplete.append(_incomplete(line, INCOMPLETE_TRIAL_OBJECTIVE_MISSING))
        return Ok(None)
    if resolved_objective.undefined:
        buckets.incomplete.append(
            _incomplete(
                line, INCOMPLETE_TRIAL_OBJECTIVE_UNDEFINED, detail={"measure": objective.measure}
            )
        )
        return Ok(None)
    failed = _evaluate_constraints(line, constraints, buckets)
    if is_refusal(failed):
        return failed
    verdict = failed.value
    if verdict is None:
        return Ok(None)  # a constraint metric was undefined/missing → incomplete
    trial = ScoredTrial(
        run_id=line.run_id,
        world=line.world.value,
        objective=objective.measure,
        objective_num=resolved_objective.value.numerator,
        objective_den=resolved_objective.value.denominator,
        objective_unit_kind=resolved_objective.unit_kind,
        objective_currency=resolved_objective.currency,
        meets_target=objective.meets_target(resolved_objective.value),
        failed_constraints=tuple(verdict),
    )
    if verdict:
        buckets.excluded.append(trial)
    else:
        buckets.winners.append(trial)
    return Ok(None)


def _evaluate_constraints(
    line: LedgerLine,
    constraints: tuple[StudyConstraint, ...],
    buckets: _Buckets,
) -> Result[list[Mapping[str, object]] | None]:
    """Return the violated constraints, or None when a metric can't be evaluated.

    A missing or undefined constraint metric is reported as incomplete (never
    silently dropped, never coerced to zero) and returns None so the caller skips
    the trial.
    """
    violated: list[Mapping[str, object]] = []
    for constraint in constraints:
        slot = _measure_magnitude(line, constraint.measure)
        if is_refusal(slot):
            return slot
        resolved = slot.value
        if resolved is None:
            buckets.incomplete.append(
                _incomplete(
                    line,
                    INCOMPLETE_TRIAL_CONSTRAINT_MISSING,
                    detail={"measure": constraint.measure},
                )
            )
            return Ok(None)
        if resolved.undefined:
            buckets.incomplete.append(
                _incomplete(
                    line,
                    INCOMPLETE_TRIAL_CONSTRAINT_UNDEFINED,
                    detail={"measure": constraint.measure},
                )
            )
            return Ok(None)
        satisfied = constraint.evaluate(resolved)
        if is_refusal(satisfied):
            return satisfied
        if not satisfied.value:
            violated.append(constraint.violated_content())
    return Ok(violated)


@dataclass(frozen=True, slots=True)
class _Magnitude:
    """A resolved measure slot: an exact value, or an undefined marker."""

    undefined: bool
    value: Fraction
    unit_kind: str
    currency: str | None


def _measure_magnitude(line: LedgerLine, identity: str) -> Result[_Magnitude | None]:
    """Reconstruct the exact magnitude of one measure by identity.

    Returns None when the identity is absent from the line's measures, an undefined
    marker when the slot is an :class:`UndefinedMeasure`, and the exact rational
    magnitude otherwise. No binary float is ever reconstructed.
    """
    for measure in line.measures:
        if measure.get("measure_identity") != identity:
            continue
        if measure.get("class") == "undefined-measure":
            return Ok(_Magnitude(undefined=True, value=Fraction(0), unit_kind="", currency=None))
        quantity = measure.get("quantity")
        if not isinstance(quantity, Mapping):
            return invalid(
                "measures",
                "a performance-measure carries its quantity as an fp1-canonical object",
                measure_identity=identity,
            )
        body = cast("Mapping[str, object]", quantity)
        num = body.get("num")
        den = body.get("den")
        if isinstance(num, bool) or not isinstance(num, int):
            return invalid(
                "measures",
                "an exact measure quantity carries an integer numerator, never a float",
                measure_identity=identity,
                given=repr(num),
            )
        if isinstance(den, bool) or not isinstance(den, int) or den == 0:
            return invalid(
                "measures",
                "an exact measure quantity carries a non-zero integer denominator",
                measure_identity=identity,
                given=repr(den),
            )
        unit = clean_token(measure.get("unit_kind")) or clean_token(body.get("unit_kind")) or ""
        currency = clean_token(body.get("currency"))
        return Ok(
            _Magnitude(
                undefined=False,
                value=Fraction(num, den),
                unit_kind=unit,
                currency=currency,
            )
        )
    return Ok(None)


def _order(trials: list[ScoredTrial], direction: str) -> None:
    """Order best-first: min ascends, max descends; run_id is the tiebreak."""
    trials.sort(key=lambda trial: trial.run_id.value)
    trials.sort(key=lambda trial: trial.objective_value, reverse=direction == DIRECTION_MAX)


# --- parsing / helpers -------------------------------------------------------


def _incomplete(
    line: LedgerLine,
    reason: str,
    *,
    detail: Mapping[str, object] | None = None,
) -> IncompleteTrial:
    return IncompleteTrial(
        run_id=line.run_id,
        world=line.world.value,
        role=line.role,
        reason=reason,
        detail=detail,
    )


def _refusal_detail(line: LedgerLine) -> Mapping[str, object] | None:
    if line.refusal is None:
        return None
    detail: dict[str, object] = {}
    category = line.refusal.get("category")
    if isinstance(category, str) and category.strip() != "":
        detail["category"] = category
    field_name = line.refusal.get("field")
    if isinstance(field_name, str) and field_name.strip() != "":
        detail["field"] = field_name
    return detail or None


def _as_objective(value: object) -> Result[StudyObjective]:
    given = type(value).__name__
    if isinstance(value, StudyObjective):
        return Ok(value)
    if isinstance(value, Mapping):
        body = cast("Mapping[str, object]", value)
        return StudyObjective.try_create(
            body.get("measure", body.get("measure_identity")),
            body.get("direction"),
            target_value=body.get("target_value"),
            target_unit_kind=body.get("target_unit_kind"),
            target_currency=body.get("target_currency"),
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        parts = tuple(cast("Sequence[object]", value))
        if len(parts) == 2:
            return StudyObjective.try_create(parts[0], parts[1])
        if len(parts) == 3:
            return StudyObjective.try_create(parts[0], parts[1], target_value=parts[2])
    return invalid(
        "objective",
        "a Study objective is a StudyObjective, a { measure, direction, target_value? } "
        "mapping, or a (measure, direction) pair",
        given=repr(given),
    )


def _as_constraints(value: object) -> Result[tuple[StudyConstraint, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, StudyConstraint):
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "constraints",
            "constraints are a sequence of { measure, op, value } filters",
            given=repr(type(value).__name__),
        )
    out: list[StudyConstraint] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        parsed = _as_one_constraint(item, index)
        if is_refusal(parsed):
            return parsed
        out.append(parsed.value)
    return Ok(tuple(out))


def _as_one_constraint(item: object, index: int) -> Result[StudyConstraint]:
    given = type(item).__name__
    if isinstance(item, StudyConstraint):
        return Ok(item)
    if isinstance(item, Mapping):
        body = cast("Mapping[str, object]", item)
        return StudyConstraint.try_create(
            body.get("measure", body.get("measure_identity")),
            body.get("operator", body.get("op")),
            body.get("value"),
            unit_kind=body.get("unit_kind"),
            currency=body.get("currency"),
        )
    if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
        parts = tuple(cast("Sequence[object]", item))
        if len(parts) == 3:
            return StudyConstraint.try_create(parts[0], parts[1], parts[2])
    return invalid(
        "constraints",
        "each constraint is a StudyConstraint, a { measure, op, value } mapping, or a "
        "(measure, op, value) triple",
        index=index,
        given=repr(given),
    )


def _as_roster_identity(value: object, field_name: str) -> Result[str]:
    token = clean_token(value)
    if token is None:
        return invalid(
            field_name,
            "an objective or constraint metric is a measure_identity from the AD-23/AD-41 roster",
            given=repr(value),
        )
    lowered = token.casefold()
    for forbidden in FORBIDDEN_COMPOSITE_EXPRESSIONS:
        if forbidden in lowered:
            return reject_composite_expression(token)
    if token not in MEASURE_IDENTITIES:
        return invalid(
            field_name,
            "an objective or constraint names a measure_identity from the AD-23/AD-41 "
            "roster; the miss is refused at Study creation, never at trial time "
            "(OPT-8, AD-11)",
            given=token,
            allowed=list(MEASURE_IDENTITIES),
        )
    return Ok(token)


def _as_direction(value: object) -> Result[str]:
    token = clean_token(value)
    if token is None or token not in OBJECTIVE_DIRECTIONS:
        return invalid(
            "direction",
            "the objective direction is min or max; the Study minimizes or maximizes "
            "one named metric, never a hard-wired compound score (OPT-5)",
            given=repr(value),
            allowed=list(OBJECTIVE_DIRECTIONS),
        )
    return Ok(token)


def _as_operator(value: object) -> Result[str]:
    token = clean_token(value)
    if token is None or token not in STUDY_CONSTRAINT_OPERATORS:
        return invalid(
            "operator",
            "a hard-constraint operator is one of the closed vocabulary { <, <=, >, >=, =, != }",
            given=repr(value),
            allowed=list(STUDY_CONSTRAINT_OPERATORS),
        )
    return Ok(token)


def _as_trial_role(value: object) -> Result[str]:
    token = clean_token(value)
    if token is None:
        return invalid(
            "role",
            "the winner set reads one completed run role; trial, confirmation, or replicate",
            given=repr(value),
        )
    if token == ROLE_ABORTED:
        return invalid(
            "role",
            "the winner set ranks completed trials, never the aborted role; refused "
            "trials are reported separately in the incomplete list",
            given=token,
        )
    return Ok(token)


def _coerce_exact_value(value: object) -> Result[tuple[Fraction, str | None, str | None]]:
    """Coerce a caller-supplied comparison/target value to an exact rational.

    Returns ``(magnitude, currency, unit_kind)``. A binary float is refused — the
    money path and the exact-rational discipline never accept float bytes, and no
    threshold number is invented (NFR-07).
    """
    if isinstance(value, bool):
        return invalid(
            "value",
            "a constraint or target value is an exact number, never a boolean",
            given=repr(value),
        )
    if isinstance(value, float):
        return invalid(
            "value",
            "a constraint or target value is exact; a binary float on the comparison "
            "path is refused (no invented threshold, exact-rational discipline)",
            given=repr(value),
        )
    if isinstance(value, int):
        return Ok((Fraction(value), None, None))
    if isinstance(value, Fraction):
        return Ok((value, None, None))
    identity = getattr(value, "fp1_identity", None)
    if callable(identity):
        body = identity()
        if isinstance(body, Mapping):
            return _value_from_mapping(cast("Mapping[str, object]", body))
    if isinstance(value, Mapping):
        return _value_from_mapping(cast("Mapping[str, object]", value))
    return invalid(
        "value",
        "a constraint or target value is an int, Fraction, Money, ExactRational, or "
        "their fp1-canonical mapping",
        given=repr(type(value).__name__),
    )


def _value_from_mapping(
    body: Mapping[str, object],
) -> Result[tuple[Fraction, str | None, str | None]]:
    num = body.get("num")
    den = body.get("den")
    if isinstance(num, bool) or not isinstance(num, int):
        return invalid(
            "value",
            "an exact constraint or target value carries an integer numerator, never a float",
            given=repr(num),
        )
    if isinstance(den, bool) or not isinstance(den, int) or den == 0:
        return invalid(
            "value",
            "an exact constraint or target value carries a non-zero integer denominator",
            given=repr(den),
        )
    currency = clean_token(body.get("currency"))
    unit_kind = clean_token(body.get("unit_kind"))
    return Ok((Fraction(num, den), currency, unit_kind))


def _world_token(value: object) -> str:
    if isinstance(value, World):
        return value.value
    token = clean_token(value)
    return token if token is not None else str(value)
