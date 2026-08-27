"""Cross-run ranking as a read-time fold over a sweep's ledger (Story 20.4).

Ranking is a **pure read-time view** over the world-and-role-scoped ledger merge
(:func:`~qmb.ledger.line.merge_ledger_lines`) — never a merged or re-run
computation (B-12; B-4; B-10; spec R11). It orders a completed sweep's
combinations by a declared objective ``measure_identity`` from the AD-23/AD-41
roster and applies optional metric-operator-value constraint filters whose
comparison value the operator or agent supplies — no threshold number is invented
(spec R11; SC-07; NFR-07).

The fold reads only combos belonging to one ``sweep_id`` and never mixes worlds
or roles (B-4): the ranked ordering is over a single ``(world, role)`` merge, and
the refused/incomplete list is the same world's ``role = aborted`` lines. Ranking
**publishes and never acts** — it produces no composite score that gates money,
mints no promotion, and binds nothing; every ranked combo carries its
``optimistic`` taint and world label forward, and the ranking makes no edge claim
and no unbiased pass/fail verdict — the per-combo verdict rule and the
multiple-comparisons statistic stay deferred to GAP-0048/0049 (B-10; B-14;
SC-06; SC-07; FR-034; FR-038; DEC-0162, DEC-0169).

A combo whose ledger line is a refusal/``aborted`` outcome with no CT-32 measures
— or a completed combo whose objective (or a constraint metric) is an
:class:`~qmf.risk.performance.UndefinedMeasure` — is excluded from the objective
ordering and reported in a separate refused/incomplete list: never silently
dropped and never coerced to a zero score (AD-11; spec R12). Recomputing the same
sweep under the same objective plus constraints is deterministic and reproducible
— a pure downstream function of the CT-32 artifacts and the ledger, adding no
computation of its own (B-10; NFR-03).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.performance import FORBIDDEN_COMPOSITE_EXPRESSIONS, reject_composite_expression

from qmb._refuse import clean_token, invalid, policy
from qmb.execution.ports import TAINT_OPTIMISTIC, refuse_optimistic_edge_claim
from qmb.ledger.line import ROLE_ABORTED, ROLE_CONFIRMATION, LedgerLine, merge_ledger_lines
from qmb.results.measures import MEASURE_IDENTITIES

__all__ = [
    "CONSTRAINT_OPERATORS",
    "INCOMPLETE_CONSTRAINT_MISSING",
    "INCOMPLETE_CONSTRAINT_UNDEFINED",
    "INCOMPLETE_OBJECTIVE_MISSING",
    "INCOMPLETE_OBJECTIVE_UNDEFINED",
    "INCOMPLETE_REASONS",
    "INCOMPLETE_REFUSED",
    "RANKING_CLASS",
    "RANKING_FORMAT_VERSION",
    "RANK_ADDS_COMPUTATION",
    "RANK_ASCENDING",
    "RANK_DESCENDING",
    "RANK_DIRECTIONS",
    "RANK_FORBIDDEN_ACTS",
    "RANK_MAKES_EDGE_CLAIM",
    "RANK_MAKES_PASS_FAIL_VERDICT",
    "RANK_PUBLISHES_NEVER_ACTS",
    "ConstraintFilter",
    "IncompleteCombo",
    "RankedCombo",
    "SweepRanking",
    "rank_sweep",
    "refuse_rank_act",
    "sweep_rank_identity",
]

RANKING_CLASS: Final[str] = "qmb-sweep-ranking"
RANKING_FORMAT_VERSION: Final[int] = 1
_RANKED_COMBO_CLASS: Final[str] = "qmb-ranked-combo"
_INCOMPLETE_COMBO_CLASS: Final[str] = "qmb-incomplete-combo"
_CONSTRAINT_CLASS: Final[str] = "qmb-rank-constraint"

# The ordering sense the caller declares. "best" and "worst" are the two ends of
# the ordering under this direction — the caller declares which end is best for
# the objective's polarity (maximize net_profit vs minimize max_drawdown). The
# fold never decides goodness on its own: that would be an edge claim.
RANK_DESCENDING: Final[str] = "descending"
RANK_ASCENDING: Final[str] = "ascending"
RANK_DIRECTIONS: Final[tuple[str, ...]] = (RANK_DESCENDING, RANK_ASCENDING)

# The closed metric-operator vocabulary. The value is always caller-supplied.
CONSTRAINT_OPERATORS: Final[tuple[str, ...]] = ("lt", "le", "gt", "ge", "eq", "ne")
_OPERATOR_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "<": "lt",
        "<=": "le",
        "=<": "le",
        ">": "gt",
        ">=": "ge",
        "=>": "ge",
        "==": "eq",
        "=": "eq",
        "!=": "ne",
        "<>": "ne",
    }
)

# Reasons a combo is reported in the refused/incomplete list, never ranked and
# never coerced to a zero score (AD-11; spec R12).
INCOMPLETE_REFUSED: Final[str] = "refused"
INCOMPLETE_OBJECTIVE_UNDEFINED: Final[str] = "objective-undefined"
INCOMPLETE_OBJECTIVE_MISSING: Final[str] = "objective-missing"
INCOMPLETE_CONSTRAINT_UNDEFINED: Final[str] = "constraint-undefined"
INCOMPLETE_CONSTRAINT_MISSING: Final[str] = "constraint-missing"
INCOMPLETE_REASONS: Final[tuple[str, ...]] = (
    INCOMPLETE_REFUSED,
    INCOMPLETE_OBJECTIVE_UNDEFINED,
    INCOMPLETE_OBJECTIVE_MISSING,
    INCOMPLETE_CONSTRAINT_UNDEFINED,
    INCOMPLETE_CONSTRAINT_MISSING,
)

# Ranking publishes, never acts (B-10; FR-034). Named acts a downstream read of
# the ranking may never take — the authority belongs to the Book door or operator.
RANK_FORBIDDEN_ACTS: Final[tuple[str, ...]] = (
    "allocate",
    "bench",
    "bind",
    "change_mode",
    "demote",
    "promote",
    "size",
)
RANK_PUBLISHES_NEVER_ACTS: Final[bool] = True
RANK_MAKES_EDGE_CLAIM: Final[bool] = False
RANK_MAKES_PASS_FAIL_VERDICT: Final[bool] = False
RANK_ADDS_COMPUTATION: Final[bool] = False


@dataclass(frozen=True, slots=True)
class ConstraintFilter:
    """One metric-operator-value hard constraint (spec R11; SC-07).

    ``metric`` is a ``measure_identity`` from the AD-23/AD-41 roster; ``operator``
    is one of :data:`CONSTRAINT_OPERATORS`; ``value`` is the exact comparison
    magnitude the operator or agent supplied — never a binary float, never an
    invented threshold. ``currency`` is carried when the value is Money so a
    cross-currency bound is refused rather than compared by bare magnitude.
    """

    metric: str
    operator: str
    value: Fraction
    unit_kind: str | None = None
    currency: str | None = None

    @classmethod
    def try_create(
        cls,
        metric: object,
        operator: object,
        value: object,
        *,
        unit_kind: object = None,
        currency: object = None,
    ) -> Result[ConstraintFilter]:
        """Validate and build a :class:`ConstraintFilter`, value-or-refusal."""
        identity = _as_roster_identity(metric, "metric")
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
                metric=identity.value,
                operator=op.value,
                value=parsed_value,
                unit_kind=declared_kind,
                currency=declared_currency,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. The exact value is stored as num/den."""
        content: dict[str, object] = {
            "class": _CONSTRAINT_CLASS,
            "metric": self.metric,
            "operator": self.operator,
            "value_den": self.value.denominator,
            "value_num": self.value.numerator,
        }
        if self.unit_kind is not None:
            content["unit_kind"] = self.unit_kind
        if self.currency is not None:
            content["currency"] = self.currency
        return content


@dataclass(frozen=True, slots=True)
class RankedCombo:
    """One combo placed in the objective ordering, or held out by a constraint.

    Carries the ``optimistic`` taint and world label forward and makes no edge
    claim (B-6; B-14; SC-06). ``failed_constraints`` is empty for a ranked combo
    and names the violated constraints for a constraint-excluded combo.
    """

    run_id: Fingerprint
    world: str
    objective: str
    objective_num: int
    objective_den: int
    objective_unit_kind: str
    sweep_coordinates: Mapping[str, object]
    objective_currency: str | None = None
    taint: str = TAINT_OPTIMISTIC
    makes_edge_claim: bool = RANK_MAKES_EDGE_CLAIM
    failed_constraints: tuple[Mapping[str, object], ...] = ()

    @property
    def objective_value(self) -> Fraction:
        """The exact objective magnitude this combo is ordered by."""
        return Fraction(self.objective_num, self.objective_den)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical, fp1-clean identity content. No binary float enters here."""
        content: dict[str, object] = {
            "class": _RANKED_COMBO_CLASS,
            "makes_edge_claim": self.makes_edge_claim,
            "objective": self.objective,
            "objective_den": self.objective_den,
            "objective_num": self.objective_num,
            "objective_unit_kind": self.objective_unit_kind,
            "run_id": self.run_id.value,
            "sweep_coordinates": dict(self.sweep_coordinates),
            "taint": self.taint,
            "world": self.world,
        }
        if self.objective_currency is not None:
            content["objective_currency"] = self.objective_currency
        if self.failed_constraints:
            content["failed_constraints"] = [dict(item) for item in self.failed_constraints]
        return content


@dataclass(frozen=True, slots=True)
class IncompleteCombo:
    """A combo excluded from the ordering and never coerced to a zero score.

    A refusal/``aborted`` combo carries no CT-32 measures; a completed combo whose
    objective or a constraint metric is an :class:`UndefinedMeasure` is reported
    here rather than treated as zero (AD-11; spec R12).
    """

    run_id: Fingerprint
    world: str
    role: str
    reason: str
    taint: str = TAINT_OPTIMISTIC
    sweep_coordinates: Mapping[str, object] | None = None
    detail: Mapping[str, object] | None = None

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content for one refused/incomplete combo."""
        content: dict[str, object] = {
            "class": _INCOMPLETE_COMBO_CLASS,
            "reason": self.reason,
            "role": self.role,
            "run_id": self.run_id.value,
            "taint": self.taint,
            "world": self.world,
        }
        if self.sweep_coordinates is not None:
            content["sweep_coordinates"] = dict(self.sweep_coordinates)
        if self.detail is not None:
            content["detail"] = dict(self.detail)
        return content


@dataclass(frozen=True, slots=True)
class SweepRanking:
    """The read-time ranking view of one sweep. Publishes; never acts (B-10).

    ``ranked`` is ordered best-to-worst under ``direction``; ``constrained_out``
    holds combos with a defined objective that a hard constraint held out; and
    ``incomplete`` is the refused/incomplete list. The whole object is a pure
    deterministic function of the ledger merge (NFR-03).
    """

    sweep_id: Fingerprint
    objective: str
    direction: str
    world: str
    role: str
    constraints: tuple[ConstraintFilter, ...]
    ranked: tuple[RankedCombo, ...]
    constrained_out: tuple[RankedCombo, ...]
    incomplete: tuple[IncompleteCombo, ...]
    publishes_never_acts: bool = RANK_PUBLISHES_NEVER_ACTS
    makes_edge_claim: bool = RANK_MAKES_EDGE_CLAIM
    makes_pass_fail_verdict: bool = RANK_MAKES_PASS_FAIL_VERDICT
    adds_computation: bool = RANK_ADDS_COMPUTATION

    @property
    def best(self) -> RankedCombo | None:
        """The first ranked combo under the declared direction, or None if empty."""
        return self.ranked[0] if self.ranked else None

    @property
    def worst(self) -> RankedCombo | None:
        """The last ranked combo under the declared direction, or None if empty."""
        return self.ranked[-1] if self.ranked else None

    @property
    def ranked_count(self) -> int:
        """Combinations placed in the objective ordering."""
        return len(self.ranked)

    @property
    def constrained_out_count(self) -> int:
        """Combinations a hard constraint held out of the ordering."""
        return len(self.constrained_out)

    @property
    def incomplete_count(self) -> int:
        """Refused/incomplete combinations, never coerced to a zero score."""
        return len(self.incomplete)

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint. Same sweep + objective + constraints reproduce it."""
        return fingerprint(self.fp1_identity())

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Deterministic and reproducible (NFR-03)."""
        return {
            "class": RANKING_CLASS,
            "constrained_out": [item.fp1_identity() for item in self.constrained_out],
            "constraints": [item.fp1_identity() for item in self.constraints],
            "direction": self.direction,
            "format_version": RANKING_FORMAT_VERSION,
            "incomplete": [item.fp1_identity() for item in self.incomplete],
            "makes_edge_claim": self.makes_edge_claim,
            "makes_pass_fail_verdict": self.makes_pass_fail_verdict,
            "objective": self.objective,
            "publishes_never_acts": self.publishes_never_acts,
            "ranked": [item.fp1_identity() for item in self.ranked],
            "role": self.role,
            "sweep_id": self.sweep_id.value,
            "world": self.world,
        }


def sweep_rank_identity() -> dict[str, object]:
    """Identity-bearing ranking-fold fields. Package SemVer is omitted."""
    return {
        "adds_computation": RANK_ADDS_COMPUTATION,
        "class": RANKING_CLASS,
        "constraint_operators": CONSTRAINT_OPERATORS,
        "directions": RANK_DIRECTIONS,
        "forbidden_acts": RANK_FORBIDDEN_ACTS,
        "format_version": RANKING_FORMAT_VERSION,
        "incomplete_reasons": INCOMPLETE_REASONS,
        "makes_edge_claim": RANK_MAKES_EDGE_CLAIM,
        "makes_pass_fail_verdict": RANK_MAKES_PASS_FAIL_VERDICT,
        "publishes_never_acts": RANK_PUBLISHES_NEVER_ACTS,
        "taint": TAINT_OPTIMISTIC,
    }


def refuse_rank_act(act: object) -> Result[None]:
    """Refuse size / promote / bench / bind / mode-change / allocate / demote.

    Ranking publishes and never acts: it produces no composite score that gates
    money, mints no promotion, and binds nothing (B-10; FR-034).
    """
    token = act if isinstance(act, str) else clean_token(act)
    if not isinstance(token, str) or token.strip() == "":
        return invalid(
            "act",
            "publish-only ranking refuses a named act; the name is required",
            given=repr(act),
            forbidden=list(RANK_FORBIDDEN_ACTS),
        )
    normalized = token.casefold().replace("-", "_").replace(" ", "_")
    if normalized in RANK_FORBIDDEN_ACTS:
        return policy(
            "act",
            "ranking publishes and never acts: it may not size, promote, bench, bind, "
            "allocate, demote, or change a mode — authority belongs to the Book door "
            "or the operator (B-10, FR-034)",
            act=normalized,
            forbidden=list(RANK_FORBIDDEN_ACTS),
        )
    return invalid(
        "act",
        "ranking is a publish-only read-time view and does not size, promote, bench, "
        "bind, allocate, demote, or change a mode (B-10, FR-034)",
        given=token,
        forbidden=list(RANK_FORBIDDEN_ACTS),
    )


def rank_sweep(
    lines: object,
    *,
    sweep_id: object,
    objective: object,
    world: object,
    role: object = ROLE_CONFIRMATION,
    constraints: object = (),
    direction: object = RANK_DESCENDING,
) -> Result[SweepRanking]:
    """Rank one sweep's combinations as a read-time fold over its ledger (Story 20.4).

    ``lines`` is the sweep's ledger lines (``LedgerLine`` values or fp1-canonical
    mappings). Ranking merges them world-and-role-scoped, keeps only combos whose
    ``sweep_coordinates.sweep_id`` equals ``sweep_id``, orders the ones with a
    defined objective and satisfying every constraint, and returns the
    refused/incomplete combos separately — adding no computation of its own.
    """
    parsed_objective = _as_roster_identity(objective, "objective")
    if is_refusal(parsed_objective):
        return parsed_objective
    parsed_direction = _as_direction(direction)
    if is_refusal(parsed_direction):
        return parsed_direction
    parsed_sweep_id = _as_fingerprint(sweep_id, "sweep_id")
    if is_refusal(parsed_sweep_id):
        return parsed_sweep_id
    parsed_role = _as_ranking_role(role)
    if is_refusal(parsed_role):
        return parsed_role
    parsed_constraints = _as_constraints(constraints)
    if is_refusal(parsed_constraints):
        return parsed_constraints
    # Optimistic-tainted evidence claims no edge and gates no money (B-6, FM-9).
    claimed = refuse_optimistic_edge_claim()
    if is_refusal(claimed):
        return claimed
    # The ranked ordering is over exactly one (world, role) merge; the refused
    # list is the same world's aborted lines. Neither ever mixes worlds (B-4).
    ranked_merge = merge_ledger_lines(lines, world=world, role=parsed_role.value)
    if is_refusal(ranked_merge):
        return ranked_merge
    aborted_merge = merge_ledger_lines(lines, world=world, role=ROLE_ABORTED)
    if is_refusal(aborted_merge):
        return aborted_merge
    sweep_key = parsed_sweep_id.value.value
    folded = _fold(
        sweep_key=sweep_key,
        objective=parsed_objective.value,
        constraints=parsed_constraints.value,
        ranked_lines=ranked_merge.value,
        aborted_lines=aborted_merge.value,
    )
    if is_refusal(folded):
        return folded
    ranked, constrained_out, incomplete = folded.value
    _order(ranked, parsed_direction.value)
    return Ok(
        SweepRanking(
            sweep_id=parsed_sweep_id.value,
            objective=parsed_objective.value,
            direction=parsed_direction.value,
            world=_world_token(world),
            role=parsed_role.value,
            constraints=parsed_constraints.value,
            ranked=tuple(ranked),
            constrained_out=tuple(constrained_out),
            incomplete=tuple(incomplete),
        )
    )


# --- the fold ----------------------------------------------------------------


class _Buckets:
    """Instance-owned fold accumulators. Never module-global mutable state."""

    __slots__ = ("constrained_out", "incomplete", "ranked")

    def __init__(self) -> None:
        self.ranked: list[RankedCombo] = []
        self.constrained_out: list[RankedCombo] = []
        self.incomplete: list[IncompleteCombo] = []


def _fold(
    *,
    sweep_key: str,
    objective: str,
    constraints: tuple[ConstraintFilter, ...],
    ranked_lines: tuple[LedgerLine, ...],
    aborted_lines: tuple[LedgerLine, ...],
) -> Result[tuple[list[RankedCombo], list[RankedCombo], list[IncompleteCombo]]]:
    buckets = _Buckets()
    for line in ranked_lines:
        if not _belongs_to_sweep(line, sweep_key):
            continue
        placed = _place_completed(line, objective, constraints, buckets)
        if is_refusal(placed):
            return placed
    for line in aborted_lines:
        if not _belongs_to_sweep(line, sweep_key):
            continue
        buckets.incomplete.append(
            IncompleteCombo(
                run_id=line.run_id,
                world=line.world.value,
                role=line.role,
                reason=INCOMPLETE_REFUSED,
                sweep_coordinates=line.sweep_coordinates,
                detail=_refusal_detail(line),
            )
        )
    buckets.incomplete.sort(key=lambda item: (item.reason, item.run_id.value))
    buckets.constrained_out.sort(key=lambda item: item.run_id.value)
    return Ok((buckets.ranked, buckets.constrained_out, buckets.incomplete))


def _place_completed(
    line: LedgerLine,
    objective: str,
    constraints: tuple[ConstraintFilter, ...],
    buckets: _Buckets,
) -> Result[None]:
    """Place one completed combo: ranked, constraint-held-out, or incomplete."""
    empty: Mapping[str, object] = {}
    coordinates = line.sweep_coordinates if line.sweep_coordinates is not None else empty
    # A refusal/aborted line reaching the ranked-role merge, or one with no CT-32
    # measures, carries no objective and is reported, never coerced to zero.
    if line.refusal is not None or line.ct32_fingerprint is None:
        buckets.incomplete.append(
            _incomplete(line, INCOMPLETE_REFUSED, detail=_refusal_detail(line))
        )
        return Ok(None)
    objective_slot = _objective_magnitude(line, objective)
    if is_refusal(objective_slot):
        return objective_slot
    resolved_objective = objective_slot.value
    if resolved_objective is None:
        # Missing from the roster set on this line — malformed, never dropped.
        buckets.incomplete.append(_incomplete(line, INCOMPLETE_OBJECTIVE_MISSING))
        return Ok(None)
    if resolved_objective.undefined:
        buckets.incomplete.append(
            _incomplete(line, INCOMPLETE_OBJECTIVE_UNDEFINED, detail={"measure": objective})
        )
        return Ok(None)
    failed = _evaluate_constraints(line, constraints, buckets)
    if is_refusal(failed):
        return failed
    verdict = failed.value
    if verdict is None:
        return Ok(None)  # a constraint metric was undefined/missing → incomplete
    combo = RankedCombo(
        run_id=line.run_id,
        world=line.world.value,
        objective=objective,
        objective_num=resolved_objective.value.numerator,
        objective_den=resolved_objective.value.denominator,
        objective_unit_kind=resolved_objective.unit_kind,
        objective_currency=resolved_objective.currency,
        sweep_coordinates=coordinates,
        failed_constraints=tuple(verdict),
    )
    if verdict:
        buckets.constrained_out.append(combo)
    else:
        buckets.ranked.append(combo)
    return Ok(None)


def _evaluate_constraints(
    line: LedgerLine,
    constraints: tuple[ConstraintFilter, ...],
    buckets: _Buckets,
) -> Result[list[Mapping[str, object]] | None]:
    """Return the violated constraints, or None when a metric can't be evaluated.

    A missing or undefined constraint metric is reported as incomplete (never
    silently dropped, never coerced to zero) and returns None so the caller skips
    the combo.
    """
    violated: list[Mapping[str, object]] = []
    for constraint in constraints:
        slot = _objective_magnitude(line, constraint.metric)
        if is_refusal(slot):
            return slot
        resolved = slot.value
        if resolved is None:
            buckets.incomplete.append(
                _incomplete(
                    line,
                    INCOMPLETE_CONSTRAINT_MISSING,
                    detail={"metric": constraint.metric},
                )
            )
            return Ok(None)
        if resolved.undefined:
            buckets.incomplete.append(
                _incomplete(
                    line,
                    INCOMPLETE_CONSTRAINT_UNDEFINED,
                    detail={"metric": constraint.metric},
                )
            )
            return Ok(None)
        satisfied = _compare(constraint, resolved)
        if is_refusal(satisfied):
            return satisfied
        if not satisfied.value:
            violated.append(
                {
                    "metric": constraint.metric,
                    "operator": constraint.operator,
                    "value_den": constraint.value.denominator,
                    "value_num": constraint.value.numerator,
                }
            )
    return Ok(violated)


@dataclass(frozen=True, slots=True)
class _Magnitude:
    """A resolved measure slot: an exact value, or an undefined marker."""

    undefined: bool
    value: Fraction
    unit_kind: str
    currency: str | None


def _objective_magnitude(line: LedgerLine, identity: str) -> Result[_Magnitude | None]:
    """Reconstruct the exact magnitude of one measure by identity.

    Returns None when the identity is absent from the line's measures, an
    undefined marker when the slot is an :class:`UndefinedMeasure`, and the exact
    rational magnitude otherwise. No binary float is ever reconstructed.
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


def _compare(constraint: ConstraintFilter, resolved: _Magnitude) -> Result[bool]:
    """Compare a combo's exact metric magnitude against the constraint value."""
    if (
        constraint.currency is not None
        and resolved.currency is not None
        and constraint.currency != resolved.currency
    ):
        return policy(
            "currency",
            "a money constraint bound must share the metric's currency; there is no "
            "silent conversion",
            metric=constraint.metric,
            bound_currency=constraint.currency,
            metric_currency=resolved.currency,
        )
    left = resolved.value
    right = constraint.value
    operator = constraint.operator
    if operator == "lt":
        return Ok(left < right)
    if operator == "le":
        return Ok(left <= right)
    if operator == "gt":
        return Ok(left > right)
    if operator == "ge":
        return Ok(left >= right)
    if operator == "eq":
        return Ok(left == right)
    return Ok(left != right)


def _order(ranked: list[RankedCombo], direction: str) -> None:
    """Order best-to-worst deterministically: objective, then run_id tiebreak."""
    ranked.sort(key=lambda combo: combo.run_id.value)
    ranked.sort(key=lambda combo: combo.objective_value, reverse=direction == RANK_DESCENDING)


# --- parsing / helpers -------------------------------------------------------


def _belongs_to_sweep(line: LedgerLine, sweep_key: str) -> bool:
    coordinates = line.sweep_coordinates
    if coordinates is None:
        return False
    return coordinates.get("sweep_id") == sweep_key


def _incomplete(
    line: LedgerLine,
    reason: str,
    *,
    detail: Mapping[str, object] | None = None,
) -> IncompleteCombo:
    return IncompleteCombo(
        run_id=line.run_id,
        world=line.world.value,
        role=line.role,
        reason=reason,
        sweep_coordinates=line.sweep_coordinates,
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
            "ranking orders by a measure_identity from the AD-23/AD-41 roster; a "
            "composite score is never invented (B-10, FR-038)",
            given=token,
            allowed=list(MEASURE_IDENTITIES),
        )
    return Ok(token)


def _as_operator(value: object) -> Result[str]:
    token = clean_token(value)
    if token is None:
        return invalid(
            "operator",
            "a constraint operator is one of the closed metric-operator vocabulary",
            given=repr(value),
            allowed=list(CONSTRAINT_OPERATORS),
        )
    normalized = token.casefold()
    if normalized in _OPERATOR_ALIASES:
        normalized = _OPERATOR_ALIASES[normalized]
    if normalized not in CONSTRAINT_OPERATORS:
        return invalid(
            "operator",
            "a constraint operator is one of the closed metric-operator vocabulary",
            given=token,
            allowed=list(CONSTRAINT_OPERATORS),
        )
    return Ok(normalized)


def _coerce_exact_value(value: object) -> Result[tuple[Fraction, str | None, str | None]]:
    """Coerce a caller-supplied comparison value to an exact rational.

    Returns ``(magnitude, currency, unit_kind)``. A binary float is refused — the
    money path and the exact-rational discipline never accept float bytes, and no
    threshold number is invented (spec R11; NFR-07).
    """
    if isinstance(value, bool):
        return invalid(
            "value",
            "a constraint value is an exact number, never a boolean",
            given=repr(value),
        )
    if isinstance(value, float):
        return invalid(
            "value",
            "a constraint value is exact; a binary float on the comparison path is "
            "refused (no invented threshold, exact-rational discipline)",
            given=repr(value),
        )
    if isinstance(value, int):
        return Ok((Fraction(value), None, None))
    if isinstance(value, Fraction):
        return Ok((value, None, None))
    # Money / ExactRational (their fp1_identity carries num/den + unit_kind).
    identity = getattr(value, "fp1_identity", None)
    if callable(identity):
        body = identity()
        if isinstance(body, Mapping):
            return _value_from_mapping(cast("Mapping[str, object]", body))
    if isinstance(value, Mapping):
        return _value_from_mapping(cast("Mapping[str, object]", value))
    return invalid(
        "value",
        "a constraint value is an int, Fraction, Money, ExactRational, or their "
        "fp1-canonical mapping",
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
            "an exact constraint value carries an integer numerator, never a float",
            given=repr(num),
        )
    if isinstance(den, bool) or not isinstance(den, int) or den == 0:
        return invalid(
            "value",
            "an exact constraint value carries a non-zero integer denominator",
            given=repr(den),
        )
    currency = clean_token(body.get("currency"))
    unit_kind = clean_token(body.get("unit_kind"))
    return Ok((Fraction(num, den), currency, unit_kind))


def _as_direction(value: object) -> Result[str]:
    token = clean_token(value)
    if token is None or token not in RANK_DIRECTIONS:
        return invalid(
            "direction",
            "the ordering direction is descending or ascending; the caller declares "
            "which end is best for the objective's polarity",
            given=repr(value),
            allowed=list(RANK_DIRECTIONS),
        )
    return Ok(token)


def _as_ranking_role(value: object) -> Result[str]:
    token = clean_token(value)
    if token is None:
        return invalid(
            "role",
            "ranking reads one run role; confirmation, trial, or replicate",
            given=repr(value),
        )
    if token == ROLE_ABORTED:
        return invalid(
            "role",
            "ranking orders completed combos, never the aborted role; refused combos "
            "are reported separately in the incomplete list (spec R12)",
            given=token,
        )
    return Ok(token)


def _as_constraints(value: object) -> Result[tuple[ConstraintFilter, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, ConstraintFilter):
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "constraints",
            "constraints are a sequence of metric-operator-value filters",
            given=repr(type(value).__name__),
        )
    out: list[ConstraintFilter] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        parsed = _as_one_constraint(item, index)
        if is_refusal(parsed):
            return parsed
        out.append(parsed.value)
    return Ok(tuple(out))


def _as_one_constraint(item: object, index: int) -> Result[ConstraintFilter]:
    given = type(item).__name__
    if isinstance(item, ConstraintFilter):
        return Ok(item)
    if isinstance(item, Mapping):
        body = cast("Mapping[str, object]", item)
        return ConstraintFilter.try_create(
            body.get("metric"),
            body.get("operator"),
            body.get("value"),
            unit_kind=body.get("unit_kind"),
            currency=body.get("currency"),
        )
    if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
        parts = tuple(cast("Sequence[object]", item))
        if len(parts) == 3:
            return ConstraintFilter.try_create(parts[0], parts[1], parts[2])
    return invalid(
        "constraints",
        "each constraint is a ConstraintFilter, a {metric, operator, value} mapping, "
        "or a (metric, operator, value) triple",
        index=index,
        given=repr(given),
    )


def _as_fingerprint(value: object, field_name: str) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    if isinstance(value, str):
        return Fingerprint.try_create(value)
    return invalid(
        field_name,
        "the sweep id is the sweep declaration's fp1 fingerprint",
        given=repr(value),
    )


def _world_token(value: object) -> str:
    if isinstance(value, World):
        return value.value
    token = clean_token(value)
    return token if token is not None else str(value)
