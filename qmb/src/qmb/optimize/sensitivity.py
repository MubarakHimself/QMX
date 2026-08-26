"""Anti-overfit parameter-sensitivity report over a completed Study (B-8, OPT-22).

A completed Study emits a **parameter-sensitivity analysis** as a pure read-time
fold over its ledger ``role = trial`` lines joined to each trial's exact parameter
assignment (:func:`build_sensitivity_report`). The report describes the objective
landscape so a robust parameter region can be told apart from a fragile lucky
point before a winner is trusted (B-8; OPT-22).

What the report carries:

* an **objective distribution summary** — mean, std, min, max, median, count —
  over every completed ``role = trial`` line with a defined objective (AC1);
* **per-parameter objective slices** — for each declared parameter, the objective
  distribution at every distinct value it took. Each slice is a chart **series as
  data**: every point cites the exact Bar/Price-derived parameter value and the
  exact objective magnitude, and no image, base64, or PNG is ever the canonical
  payload (AC1; AC2; B-10);
* **good-region clusters** — the favourable-side trials clustered by adjacency in
  normalized parameter space, each cluster described as data: its member run ids,
  its per-parameter value ranges, and its own objective distribution (AC2; B-10);
* a **winner stability** flag — the objective-best trial is flagged
  :data:`STABILITY_ISOLATED_SPIKE` when its good-region cluster is a singleton (an
  unstable neighbourhood, no adjacent favourable trial), and
  :data:`STABILITY_STABLE_CLUSTER` when it sits inside a cluster of two or more
  favourable trials (AC3).

The report **describes structure and neighbourhood stability only**. It emits no
SR*/search-quality pass/fail verdict and invents no threshold — the favourable /
unfavourable divider is the distribution's own **median** (a data-derived value,
never an invented number), the neighbourhood is a described k-nearest graph whose
size is recorded as data, and the whole search-quality-threshold sitting stays
deferred to GAP-0049 (SC-07; AC4). Every trial keeps its ``optimistic`` taint and
world label forward; the report makes no edge claim (B-6; SC-06).

The sensitivity statistics are analytic floats living in the B-14 return-space
carve-out. P&L and equity **inputs stay exact-integer** — each trial's objective
magnitude is reconstructed as an exact rational from the ledger measure, never a
binary float. A float exists only transiently **inside** the standard-deviation
statistic, crosses back through the one named ``ExactRational.from_float`` rounding
boundary under a fixed ``{rounding, scale}`` contract, and the stored value is that
label-derived scaled rational — never a raw binary float in identity (AC5; AD-41;
AD-7). Recomputing the report over the same trials and parameters is deterministic
and reproducible — a pure downstream function adding no run of its own (B-10;
NFR-03).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final, cast

from qmf.core.exact import ExactRational, RoundingMode, UnitKind
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.performance import FORBIDDEN_COMPOSITE_EXPRESSIONS, reject_composite_expression

from qmb._refuse import clean_token, invalid, policy
from qmb.execution.ports import TAINT_OPTIMISTIC, refuse_optimistic_edge_claim
from qmb.ledger.line import ROLE_ABORTED, ROLE_TRIAL, LedgerLine, merge_ledger_lines
from qmb.optimize.objective import DIRECTION_MAX, OBJECTIVE_DIRECTIONS
from qmb.results.measures import MEASURE_IDENTITIES

__all__ = [
    "EXCLUDED_REASONS",
    "REPORT_EMITS_IMAGE_PAYLOAD",
    "REPORT_INVENTS_THRESHOLD",
    "REPORT_MAKES_EDGE_CLAIM",
    "REPORT_MAKES_SEARCH_QUALITY_VERDICT",
    "REPORT_VERDICT_DEFERRED_TO",
    "SENSITIVITY_CANONICAL_PAYLOAD",
    "SENSITIVITY_FORBIDDEN_VERDICTS",
    "SENSITIVITY_OBJECTIVE_MISSING",
    "SENSITIVITY_OBJECTIVE_UNDEFINED",
    "SENSITIVITY_REPORT_CLASS",
    "SENSITIVITY_REPORT_FORMAT_VERSION",
    "SENSITIVITY_STAT_DDOF",
    "SENSITIVITY_STAT_ROUNDING",
    "SENSITIVITY_STAT_SCALE",
    "SENSITIVITY_TRIAL_REFUSED",
    "SENSITIVITY_UNMAPPED",
    "STABILITY_ISOLATED_SPIKE",
    "STABILITY_NO_WINNER",
    "STABILITY_STABLE_CLUSTER",
    "WINNER_STABILITIES",
    "ExcludedTrial",
    "GoodRegionCluster",
    "ObjectiveDistribution",
    "ParameterSlice",
    "SensitivityReport",
    "SliceBin",
    "WinnerStability",
    "build_sensitivity_report",
    "refuse_search_quality_verdict",
    "sensitivity_identity",
]

SENSITIVITY_REPORT_CLASS: Final[str] = "qmb-sensitivity-report"
SENSITIVITY_REPORT_FORMAT_VERSION: Final[int] = 1
_DISTRIBUTION_CLASS: Final[str] = "qmb-objective-distribution"
_SLICE_CLASS: Final[str] = "qmb-parameter-slice"
_SLICE_BIN_CLASS: Final[str] = "qmb-parameter-slice-bin"
_CLUSTER_CLASS: Final[str] = "qmb-good-region-cluster"
_WINNER_STABILITY_CLASS: Final[str] = "qmb-winner-stability"
_EXCLUDED_CLASS: Final[str] = "qmb-excluded-trial"

# The one fixed rounding contract the float-domain statistic crosses back through.
# The standard deviation is the only summary that leaves the exact-rational domain
# (sqrt of an exact variance); it re-enters an exact value only through the named
# ExactRational.from_float boundary, at this fixed scale and rounding, so the stored
# value is a label-derived scaled rational and never a raw binary float (AC5, AD-7).
SENSITIVITY_STAT_SCALE: Final[int] = 12
SENSITIVITY_STAT_ROUNDING: Final[RoundingMode] = RoundingMode.HALF_EVEN
# Population standard deviation (ddof=0): the summary describes THESE trials, so a
# single-trial group has a well-defined std of zero rather than an undefined one.
SENSITIVITY_STAT_DDOF: Final[int] = 0

# Chart series are data, never an image (AC2, B-10, R-RPT-11): every slice point
# cites the exact parameter value and exact objective magnitude, and no image,
# base64, or PNG is ever the canonical payload.
SENSITIVITY_CANONICAL_PAYLOAD: Final[str] = "series-data"
REPORT_EMITS_IMAGE_PAYLOAD: Final[bool] = False

# The report publishes structure and neighbourhood stability only. It names no
# edge, mints no SR*/search-quality pass/fail verdict, and invents no threshold —
# the favourable divider is the data's own median, and the threshold sitting stays
# deferred (SC-07, GAP-0049, AC4).
REPORT_MAKES_EDGE_CLAIM: Final[bool] = False
REPORT_MAKES_SEARCH_QUALITY_VERDICT: Final[bool] = False
REPORT_INVENTS_THRESHOLD: Final[bool] = False
REPORT_VERDICT_DEFERRED_TO: Final[str] = "GAP-0049"
SENSITIVITY_FORBIDDEN_VERDICTS: Final[tuple[str, ...]] = (
    "pass",
    "fail",
    "sr",
    "sr_star",
    "search_quality",
    "significance",
)

# The winner stability flag (AC3). The objective-best trial is an isolated spike
# when its good-region cluster is a singleton — an unstable neighbourhood with no
# adjacent favourable trial — and a stable cluster when it sits inside a cluster of
# two or more favourable trials.
STABILITY_ISOLATED_SPIKE: Final[str] = "isolated-spike"
STABILITY_STABLE_CLUSTER: Final[str] = "stable-cluster"
STABILITY_NO_WINNER: Final[str] = "no-winner"
WINNER_STABILITIES: Final[tuple[str, ...]] = (
    STABILITY_ISOLATED_SPIKE,
    STABILITY_STABLE_CLUSTER,
    STABILITY_NO_WINNER,
)

# Reasons a trial is set aside from the analysis, never silently dropped and never
# coerced to a zero objective (AD-11).
SENSITIVITY_TRIAL_REFUSED: Final[str] = "refused"
SENSITIVITY_OBJECTIVE_UNDEFINED: Final[str] = "objective-undefined"
SENSITIVITY_OBJECTIVE_MISSING: Final[str] = "objective-missing"
SENSITIVITY_UNMAPPED: Final[str] = "unmapped"
EXCLUDED_REASONS: Final[tuple[str, ...]] = (
    SENSITIVITY_TRIAL_REFUSED,
    SENSITIVITY_OBJECTIVE_UNDEFINED,
    SENSITIVITY_OBJECTIVE_MISSING,
    SENSITIVITY_UNMAPPED,
)


def sensitivity_identity() -> dict[str, object]:
    """Identity-bearing sensitivity-report fields. Package SemVer is omitted."""
    return {
        "canonical_payload": SENSITIVITY_CANONICAL_PAYLOAD,
        "class": SENSITIVITY_REPORT_CLASS,
        "emits_image_payload": REPORT_EMITS_IMAGE_PAYLOAD,
        "excluded_reasons": EXCLUDED_REASONS,
        "format_version": SENSITIVITY_REPORT_FORMAT_VERSION,
        "invents_threshold": REPORT_INVENTS_THRESHOLD,
        "makes_edge_claim": REPORT_MAKES_EDGE_CLAIM,
        "makes_search_quality_verdict": REPORT_MAKES_SEARCH_QUALITY_VERDICT,
        "stat_ddof": SENSITIVITY_STAT_DDOF,
        "stat_rounding": SENSITIVITY_STAT_ROUNDING.value,
        "stat_scale": SENSITIVITY_STAT_SCALE,
        "verdict_deferred_to": REPORT_VERDICT_DEFERRED_TO,
        "winner_stabilities": WINNER_STABILITIES,
    }


def refuse_search_quality_verdict(name: object) -> Result[None]:
    """Refuse turning the sensitivity report into an SR*/search-quality verdict (AC4).

    The report describes parameter structure and neighbourhood stability only. Any
    attempt to read a preregistered search-quality threshold, an SR* label, or a
    significance pass/fail out of it is refused ``policy rejection`` — the whole
    threshold sitting is deferred to GAP-0049 and invents nothing here (SC-07).
    """
    token = name if isinstance(name, str) else clean_token(name)
    if not isinstance(token, str) or token.strip() == "":
        return invalid(
            "verdict",
            "a search-quality verdict name is required to refuse it",
            given=repr(name),
            deferred_to=REPORT_VERDICT_DEFERRED_TO,
        )
    return policy(
        "verdict",
        "the sensitivity report describes structure and neighbourhood stability only; "
        "it emits no SR*/search-quality pass/fail verdict and invents no threshold — the "
        "threshold sitting is deferred (SC-07, GAP-0049)",
        verdict=token,
        deferred_to=REPORT_VERDICT_DEFERRED_TO,
    )


# --- the objective distribution summary (AC1, AC5) ---------------------------


@dataclass(frozen=True, slots=True)
class ObjectiveDistribution:
    """Mean, std, min, max, median of an objective over a set of trials (AC1, AC5).

    ``mean``, ``minimum``, ``maximum``, and ``median`` are exact rationals folded
    from the exact-integer objective inputs — no binary float touches them. ``std``
    is the one float-domain statistic: computed as the sqrt of the exact variance,
    crossed back through the named ``ExactRational.from_float`` boundary under the
    fixed :data:`SENSITIVITY_STAT_ROUNDING` / :data:`SENSITIVITY_STAT_SCALE`
    contract, and stored as that label-derived scaled rational — never a raw float.
    """

    count: int
    unit_kind: str
    mean_num: int
    mean_den: int
    minimum_num: int
    minimum_den: int
    maximum_num: int
    maximum_den: int
    median_num: int
    median_den: int
    std_num: int
    std_den: int
    std_rounding: str
    std_scale: int
    currency: str | None = None

    @property
    def mean(self) -> Fraction:
        """The exact mean objective."""
        return Fraction(self.mean_num, self.mean_den)

    @property
    def minimum(self) -> Fraction:
        """The exact minimum objective."""
        return Fraction(self.minimum_num, self.minimum_den)

    @property
    def maximum(self) -> Fraction:
        """The exact maximum objective."""
        return Fraction(self.maximum_num, self.maximum_den)

    @property
    def median(self) -> Fraction:
        """The exact median objective."""
        return Fraction(self.median_num, self.median_den)

    @property
    def std(self) -> Fraction:
        """The label-derived scaled-rational standard deviation (never a raw float)."""
        return Fraction(self.std_num, self.std_den)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Every measure is an exact num/den pair."""
        content: dict[str, object] = {
            "class": _DISTRIBUTION_CLASS,
            "count": self.count,
            "maximum_den": self.maximum_den,
            "maximum_num": self.maximum_num,
            "mean_den": self.mean_den,
            "mean_num": self.mean_num,
            "median_den": self.median_den,
            "median_num": self.median_num,
            "minimum_den": self.minimum_den,
            "minimum_num": self.minimum_num,
            "std": {
                "den": self.std_den,
                "num": self.std_num,
                "rounding": self.std_rounding,
                "scale": self.std_scale,
            },
            "unit_kind": self.unit_kind,
        }
        if self.currency is not None:
            content["currency"] = self.currency
        return content


# --- the per-parameter objective slices (AC1, AC2) ---------------------------


@dataclass(frozen=True, slots=True)
class SliceBin:
    """One value of one parameter and the objective distribution it took (AC1, AC2).

    ``value`` is the exact Bar/Price-derived parameter value's canonical identity —
    an int, an :class:`ExactRational` identity, a categorical token, or a bool — and
    ``distribution`` summarizes the objective over the trials that took that value.
    ``run_ids`` cites those trials. This is one canonical chart-series point: data,
    never an image (B-10, R-RPT-11).
    """

    value: object
    distribution: ObjectiveDistribution
    run_ids: tuple[str, ...]

    def fp1_identity(self) -> dict[str, object]:
        """Canonical slice-point identity content."""
        return {
            "class": _SLICE_BIN_CLASS,
            "distribution": self.distribution.fp1_identity(),
            "run_ids": list(self.run_ids),
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class ParameterSlice:
    """The objective series across one parameter's values — a chart as data (AC2).

    ``bins`` is ordered by value (numeric ascending; categorical by token; boolean
    false-then-true), so the series reads as a curve of the objective against the
    parameter. ``canonical_payload`` is :data:`SENSITIVITY_CANONICAL_PAYLOAD`; no
    image, base64, or PNG is ever the canonical payload (B-10, R-RPT-11).
    """

    parameter: str
    kind: str
    bins: tuple[SliceBin, ...]
    canonical_payload: str = SENSITIVITY_CANONICAL_PAYLOAD

    def fp1_identity(self) -> dict[str, object]:
        """Canonical parameter-slice identity content."""
        return {
            "bins": [item.fp1_identity() for item in self.bins],
            "canonical_payload": self.canonical_payload,
            "class": _SLICE_CLASS,
            "kind": self.kind,
            "parameter": self.parameter,
        }


# --- good-region clusters (AC2) ----------------------------------------------


@dataclass(frozen=True, slots=True)
class GoodRegionCluster:
    """One cluster of favourable-side trials, described as data (AC2, B-10).

    Favourable trials are clustered by adjacency in normalized parameter space.
    ``member_run_ids`` names the cluster's trials; ``parameter_ranges`` describes,
    per parameter, the exact value range the cluster spans; ``distribution`` is the
    cluster's own objective distribution; ``contains_winner`` marks the cluster the
    objective-best trial sits in. The cluster makes no edge claim.
    """

    index: int
    member_run_ids: tuple[str, ...]
    parameter_ranges: Mapping[str, Mapping[str, object]]
    distribution: ObjectiveDistribution
    contains_winner: bool

    @property
    def size(self) -> int:
        """Favourable trials in this cluster."""
        return len(self.member_run_ids)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical cluster identity content."""
        return {
            "class": _CLUSTER_CLASS,
            "contains_winner": self.contains_winner,
            "distribution": self.distribution.fp1_identity(),
            "index": self.index,
            "member_run_ids": list(self.member_run_ids),
            "parameter_ranges": {
                name: dict(body) for name, body in sorted(self.parameter_ranges.items())
            },
            "size": self.size,
        }


# --- winner stability (AC3) --------------------------------------------------


@dataclass(frozen=True, slots=True)
class WinnerStability:
    """The objective-best trial's neighbourhood stability, as data (AC3, AC4).

    ``stability`` is :data:`STABILITY_ISOLATED_SPIKE` when the winner's good-region
    cluster is a singleton (no adjacent favourable trial), or
    :data:`STABILITY_STABLE_CLUSTER` when its cluster holds two or more favourable
    trials; :data:`STABILITY_NO_WINNER` when no trial was analysed. ``neighbour_run_ids``
    are the winner's nearest neighbours in normalized parameter space,
    ``neighbourhood`` is their objective distribution (with the winner), and
    ``good_neighbour_count`` counts how many are on the favourable side of the
    median — the neighbourhood stability described as data, no verdict.
    """

    stability: str
    winner_run_id: str | None
    cluster_index: int | None
    cluster_size: int
    neighbour_run_ids: tuple[str, ...]
    good_neighbour_count: int
    neighbourhood: ObjectiveDistribution | None = None

    @property
    def is_isolated_spike(self) -> bool:
        """Whether the winner sits alone in an unstable neighbourhood (AC3)."""
        return self.stability == STABILITY_ISOLATED_SPIKE

    def fp1_identity(self) -> dict[str, object]:
        """Canonical winner-stability identity content."""
        content: dict[str, object] = {
            "class": _WINNER_STABILITY_CLASS,
            "cluster_size": self.cluster_size,
            "good_neighbour_count": self.good_neighbour_count,
            "neighbour_run_ids": list(self.neighbour_run_ids),
            "stability": self.stability,
        }
        if self.winner_run_id is not None:
            content["winner_run_id"] = self.winner_run_id
        if self.cluster_index is not None:
            content["cluster_index"] = self.cluster_index
        if self.neighbourhood is not None:
            content["neighbourhood"] = self.neighbourhood.fp1_identity()
        return content


# --- excluded trials ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExcludedTrial:
    """A trial set aside from the analysis, never coerced to a zero objective.

    A refusal/``aborted`` trial carries no CT-32 measures; a completed trial whose
    objective is an :class:`UndefinedMeasure` or absent, or a completed trial with
    no supplied parameter assignment, is reported here rather than treated as zero
    (AD-11).
    """

    run_id: str
    world: str
    role: str
    reason: str
    taint: str = TAINT_OPTIMISTIC
    detail: Mapping[str, object] | None = None

    def fp1_identity(self) -> dict[str, object]:
        """Canonical excluded-trial identity content."""
        content: dict[str, object] = {
            "class": _EXCLUDED_CLASS,
            "reason": self.reason,
            "role": self.role,
            "run_id": self.run_id,
            "taint": self.taint,
            "world": self.world,
        }
        if self.detail is not None:
            content["detail"] = dict(self.detail)
        return content


# --- the report --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SensitivityReport:
    """The read-time parameter-sensitivity report of one completed Study (B-8, OPT-22).

    ``distribution`` is the objective summary over every analysed trial;
    ``parameter_slices`` are the per-parameter objective series; ``clusters`` are the
    good regions; ``winner_stability`` flags the objective-best trial; ``excluded``
    lists the trials set aside. The whole object describes structure and
    neighbourhood stability only — it makes no edge claim, mints no search-quality
    verdict, and invents no threshold (AC4, B-6, SC-06, SC-07) — and is a pure
    deterministic function of the ledger merge and the parameter assignments (NFR-03).
    """

    objective: str
    direction: str
    world: str
    role: str
    analysed_count: int
    neighbourhood_size: int
    distribution: ObjectiveDistribution | None
    parameter_slices: tuple[ParameterSlice, ...]
    clusters: tuple[GoodRegionCluster, ...]
    winner_stability: WinnerStability
    excluded: tuple[ExcludedTrial, ...]
    canonical_payload: str = SENSITIVITY_CANONICAL_PAYLOAD
    emits_image_payload: bool = REPORT_EMITS_IMAGE_PAYLOAD
    makes_edge_claim: bool = REPORT_MAKES_EDGE_CLAIM
    makes_search_quality_verdict: bool = REPORT_MAKES_SEARCH_QUALITY_VERDICT
    invents_threshold: bool = REPORT_INVENTS_THRESHOLD
    verdict_deferred_to: str = REPORT_VERDICT_DEFERRED_TO

    @property
    def cluster_count(self) -> int:
        """Good regions the favourable-side trials clustered into."""
        return len(self.clusters)

    @property
    def excluded_count(self) -> int:
        """Trials set aside from the analysis, never coerced to a zero objective."""
        return len(self.excluded)

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint. Same trials + parameters + objective reproduce it."""
        return fingerprint(self.fp1_identity())

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Deterministic and reproducible (NFR-03)."""
        content: dict[str, object] = {
            "analysed_count": self.analysed_count,
            "canonical_payload": self.canonical_payload,
            "class": SENSITIVITY_REPORT_CLASS,
            "clusters": [item.fp1_identity() for item in self.clusters],
            "direction": self.direction,
            "emits_image_payload": self.emits_image_payload,
            "excluded": [item.fp1_identity() for item in self.excluded],
            "format_version": SENSITIVITY_REPORT_FORMAT_VERSION,
            "invents_threshold": self.invents_threshold,
            "makes_edge_claim": self.makes_edge_claim,
            "makes_search_quality_verdict": self.makes_search_quality_verdict,
            "neighbourhood_size": self.neighbourhood_size,
            "objective": self.objective,
            "parameter_slices": [item.fp1_identity() for item in self.parameter_slices],
            "role": self.role,
            "verdict_deferred_to": self.verdict_deferred_to,
            "winner_stability": self.winner_stability.fp1_identity(),
            "world": self.world,
        }
        if self.distribution is not None:
            content["distribution"] = self.distribution.fp1_identity()
        return content


def build_sensitivity_report(
    lines: object,
    *,
    parameters: object,
    objective: object,
    world: object,
    direction: object = DIRECTION_MAX,
    role: object = ROLE_TRIAL,
    neighbourhood_size: object = None,
) -> Result[SensitivityReport]:
    """Build the parameter-sensitivity report as a read-time fold (B-8, OPT-22, AC1).

    ``lines`` is the Study's ledger lines (``LedgerLine`` values or fp1-canonical
    mappings); ``parameters`` maps each trial's ``run_id`` to its exact parameter
    assignment (a run-id -> {name: exact value} mapping, or a sequence of
    ``{run_id, parameters}`` records). The fold reads only completed ``role = trial``
    lines, joins each to its assignment by run id, and describes the objective
    landscape — adding no run of its own. A trial with no defined objective, or with
    no supplied assignment, is set aside in ``excluded`` (never coerced to zero).
    ``neighbourhood_size`` sizes the described nearest-neighbour graph; ``None``
    derives it from the parameter dimensionality and is recorded in the report.
    """
    parsed_objective = _as_roster_identity(objective, "objective")
    if is_refusal(parsed_objective):
        return parsed_objective
    parsed_direction = _as_direction(direction)
    if is_refusal(parsed_direction):
        return parsed_direction
    parsed_role = _as_trial_role(role)
    if is_refusal(parsed_role):
        return parsed_role
    parsed_neighbourhood = _as_optional_size(neighbourhood_size)
    if is_refusal(parsed_neighbourhood):
        return parsed_neighbourhood
    assignments = _coerce_parameters(parameters)
    if is_refusal(assignments):
        return assignments
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
    collected = _collect_trials(
        parsed_objective.value,
        assignments.value,
        trial_merge.value,
        aborted_merge.value,
    )
    if is_refusal(collected):
        return collected
    analysed, excluded = collected.value
    return _assemble_report(
        objective=parsed_objective.value,
        direction=parsed_direction.value,
        world=_world_token(world),
        role=parsed_role.value,
        neighbourhood_override=parsed_neighbourhood.value,
        analysed=analysed,
        excluded=excluded,
    )


# --- collecting the analysed trials ------------------------------------------


@dataclass(frozen=True, slots=True)
class _AnalysedTrial:
    """One completed trial with a defined objective and an exact parameter assignment."""

    run_id: str
    world: str
    objective: Fraction
    unit_kind: str
    currency: str | None
    assignment: Mapping[str, _ParamValue]


def _collect_trials(
    objective: str,
    assignments: Mapping[str, Mapping[str, _ParamValue]],
    trial_lines: tuple[LedgerLine, ...],
    aborted_lines: tuple[LedgerLine, ...],
) -> Result[tuple[list[_AnalysedTrial], list[ExcludedTrial]]]:
    analysed: list[_AnalysedTrial] = []
    excluded: list[ExcludedTrial] = []
    for line in trial_lines:
        placed = _place_trial(line, objective, assignments, analysed, excluded)
        if is_refusal(placed):
            return placed
    for line in aborted_lines:
        excluded.append(
            ExcludedTrial(
                run_id=line.run_id.value,
                world=line.world.value,
                role=line.role,
                reason=SENSITIVITY_TRIAL_REFUSED,
                detail=_refusal_detail(line),
            )
        )
    _validate_one_space(analysed)
    excluded.sort(key=lambda item: (item.reason, item.run_id))
    return Ok((analysed, excluded))


def _place_trial(
    line: LedgerLine,
    objective: str,
    assignments: Mapping[str, Mapping[str, _ParamValue]],
    analysed: list[_AnalysedTrial],
    excluded: list[ExcludedTrial],
) -> Result[None]:
    if line.refusal is not None or line.ct32_fingerprint is None:
        excluded.append(_excluded(line, SENSITIVITY_TRIAL_REFUSED, detail=_refusal_detail(line)))
        return Ok(None)
    slot = _objective_magnitude(line, objective)
    if is_refusal(slot):
        return slot
    resolved = slot.value
    if resolved is None:
        excluded.append(_excluded(line, SENSITIVITY_OBJECTIVE_MISSING))
        return Ok(None)
    if resolved.undefined:
        excluded.append(
            _excluded(line, SENSITIVITY_OBJECTIVE_UNDEFINED, detail={"measure": objective})
        )
        return Ok(None)
    assignment = assignments.get(line.run_id.value)
    if assignment is None:
        excluded.append(_excluded(line, SENSITIVITY_UNMAPPED))
        return Ok(None)
    analysed.append(
        _AnalysedTrial(
            run_id=line.run_id.value,
            world=line.world.value,
            objective=resolved.value,
            unit_kind=resolved.unit_kind,
            currency=resolved.currency,
            assignment=assignment,
        )
    )
    return Ok(None)


def _validate_one_space(analysed: list[_AnalysedTrial]) -> Result[None]:
    """Every analysed trial shares one parameter name set (B-8: one schema)."""
    if not analysed:
        return Ok(None)
    names = frozenset(analysed[0].assignment)
    for trial in analysed[1:]:
        if frozenset(trial.assignment) != names:
            return invalid(
                "parameters",
                "every Study trial shares one parameter space; a trial whose assignment "
                "names a different parameter set is refused (B-8)",
                run_id=trial.run_id,
                expected=sorted(names),
                given=sorted(trial.assignment),
            )
    return Ok(None)


# --- assembling the report ---------------------------------------------------


def _assemble_report(
    *,
    objective: str,
    direction: str,
    world: str,
    role: str,
    neighbourhood_override: int | None,
    analysed: list[_AnalysedTrial],
    excluded: list[ExcludedTrial],
) -> Result[SensitivityReport]:
    names = _ordered_names(analysed)
    consistency = _validate_one_space(analysed)
    if is_refusal(consistency):
        return consistency
    kinds = _parameter_kinds(analysed, names)
    if is_refusal(kinds):
        return kinds
    overall = _distribution_over([trial.objective for trial in analysed], analysed)
    if is_refusal(overall):
        return overall
    slices = _parameter_slices(analysed, names, kinds.value)
    if is_refusal(slices):
        return slices
    size = _resolve_neighbourhood(neighbourhood_override, len(names), len(analysed))
    graph = _neighbour_graph(analysed, names, kinds.value, size)
    if is_refusal(graph):
        return graph
    median = overall.value.median if overall.value is not None else None
    clustering = _cluster_good_regions(analysed, names, kinds.value, graph.value, direction, median)
    if is_refusal(clustering):
        return clustering
    clusters, cluster_of = clustering.value
    stability = _winner_stability(analysed, direction, median, graph.value, cluster_of, clusters)
    if is_refusal(stability):
        return stability
    ordered_excluded = tuple(sorted(excluded, key=lambda item: (item.reason, item.run_id)))
    return Ok(
        SensitivityReport(
            objective=objective,
            direction=direction,
            world=world,
            role=role,
            analysed_count=len(analysed),
            neighbourhood_size=size,
            distribution=overall.value,
            parameter_slices=slices.value,
            clusters=clusters,
            winner_stability=stability.value,
            excluded=ordered_excluded,
        )
    )


def _distribution_over(
    magnitudes: list[Fraction], carriers: list[_AnalysedTrial]
) -> Result[ObjectiveDistribution | None]:
    """Fold an objective distribution over exact-rational magnitudes (AC1, AC5)."""
    if not magnitudes:
        return Ok(None)
    unit_result = _shared_unit(carriers)
    if is_refusal(unit_result):
        return unit_result
    unit_kind, currency = unit_result.value
    count = len(magnitudes)
    ordered = sorted(magnitudes)
    total = sum(ordered, Fraction(0))
    mean = total / count
    minimum = ordered[0]
    maximum = ordered[-1]
    median = _median(ordered)
    variance = sum(((value - mean) ** 2 for value in ordered), Fraction(0)) / (
        count - SENSITIVITY_STAT_DDOF
    )
    std = _std_from_variance(variance)
    if is_refusal(std):
        return std
    return Ok(
        ObjectiveDistribution(
            count=count,
            unit_kind=unit_kind,
            mean_num=mean.numerator,
            mean_den=mean.denominator,
            minimum_num=minimum.numerator,
            minimum_den=minimum.denominator,
            maximum_num=maximum.numerator,
            maximum_den=maximum.denominator,
            median_num=median.numerator,
            median_den=median.denominator,
            std_num=std.value.numerator,
            std_den=std.value.denominator,
            std_rounding=SENSITIVITY_STAT_ROUNDING.value,
            std_scale=SENSITIVITY_STAT_SCALE,
            currency=currency,
        )
    )


def _median(ordered: list[Fraction]) -> Fraction:
    """The exact median of a sorted list; an even count averages the two middles."""
    count = len(ordered)
    middle = count // 2
    if count % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _std_from_variance(variance: Fraction) -> Result[Fraction]:
    """The one float-domain statistic (AC5).

    The variance is exact; its square root leaves the rational domain, so a binary
    float exists here transiently and re-enters an exact value only through the named
    ``ExactRational.from_float`` boundary under the fixed rounding contract. The raw
    float never becomes identity — the label-derived scaled rational does.
    """
    if variance < 0:
        return invalid("variance", "an objective variance is never negative")
    root = math.sqrt(float(variance))
    converted = ExactRational.from_float(
        root,
        unit_kind=UnitKind.DIMENSIONLESS_RATIO,
        scale=SENSITIVITY_STAT_SCALE,
        rounding=SENSITIVITY_STAT_ROUNDING,
    )
    if is_refusal(converted):
        return converted
    return Ok(converted.value.as_fraction())


def _shared_unit(carriers: list[_AnalysedTrial]) -> Result[tuple[str, str | None]]:
    """One unit-kind and currency across the trials; a mix is refused, never merged."""
    unit_kind = carriers[0].unit_kind
    currency = carriers[0].currency
    for trial in carriers[1:]:
        if trial.unit_kind != unit_kind or trial.currency != currency:
            return policy(
                "unit_kind",
                "an objective distribution summary shares one AD-40 unit-kind and "
                "currency; a cross-unit or cross-currency mix is refused, never merged",
                unit_kind=unit_kind,
                currency=currency,
                other_unit_kind=trial.unit_kind,
                other_currency=trial.currency,
            )
    return Ok((unit_kind, currency))


# --- per-parameter slices ----------------------------------------------------


def _parameter_slices(
    analysed: list[_AnalysedTrial],
    names: tuple[str, ...],
    kinds: Mapping[str, str],
) -> Result[tuple[ParameterSlice, ...]]:
    out: list[ParameterSlice] = []
    for name in names:
        grouped: dict[object, list[_AnalysedTrial]] = {}
        order: dict[object, tuple[int, object]] = {}
        for trial in analysed:
            value = trial.assignment[name]
            grouped.setdefault(value.group_key, []).append(trial)
            order[value.group_key] = value.sort_key
        bins: list[SliceBin] = []
        for key in sorted(grouped, key=lambda item: order[item]):
            members = grouped[key]
            distribution = _distribution_over([trial.objective for trial in members], members)
            if is_refusal(distribution):
                return distribution
            summary = distribution.value
            if summary is None:
                continue
            bins.append(
                SliceBin(
                    value=members[0].assignment[name].identity,
                    distribution=summary,
                    run_ids=tuple(sorted(trial.run_id for trial in members)),
                )
            )
        out.append(ParameterSlice(parameter=name, kind=kinds[name], bins=tuple(bins)))
    return Ok(tuple(out))


# --- neighbourhood graph and good-region clustering --------------------------


def _resolve_neighbourhood(override: int | None, dimensions: int, trials: int) -> int:
    """The described nearest-neighbour graph size, recorded as data (AC4).

    A caller-supplied size is honoured; otherwise it is derived from the parameter
    dimensionality (a d-dimensional neighbourhood needs d+1 points) and capped by the
    trials available — a data-derived structural count, never an invented threshold.
    """
    if trials <= 1:
        return 0
    if override is not None:
        return min(override, trials - 1)
    return min(dimensions + 1, trials - 1)


def _neighbour_graph(
    analysed: list[_AnalysedTrial],
    names: tuple[str, ...],
    kinds: Mapping[str, str],
    size: int,
) -> Result[tuple[tuple[int, ...], ...]]:
    """Each trial's ``size`` nearest neighbours by exact normalized-space distance."""
    ranges = _numeric_ranges(analysed, names, kinds)
    count = len(analysed)
    distances: list[list[Fraction]] = [[Fraction(0)] * count for _ in range(count)]
    for i in range(count):
        for j in range(i + 1, count):
            gap = _squared_distance(analysed[i], analysed[j], names, kinds, ranges)
            distances[i][j] = gap
            distances[j][i] = gap
    neighbours: list[tuple[int, ...]] = []
    for i in range(count):
        others = [j for j in range(count) if j != i]
        row = distances[i]
        others.sort(key=lambda j, row=row: (row[j], analysed[j].run_id))
        neighbours.append(tuple(others[:size]))
    return Ok(tuple(neighbours))


def _numeric_ranges(
    analysed: list[_AnalysedTrial],
    names: tuple[str, ...],
    kinds: Mapping[str, str],
) -> Mapping[str, tuple[Fraction, Fraction]]:
    ranges: dict[str, tuple[Fraction, Fraction]] = {}
    for name in names:
        if kinds[name] != _KIND_NUMERIC:
            continue
        values = [_fraction_of_value(trial.assignment[name]) for trial in analysed]
        present = [value for value in values if value is not None]
        if present:
            ranges[name] = (min(present), max(present))
    return ranges


def _squared_distance(
    a: _AnalysedTrial,
    b: _AnalysedTrial,
    names: tuple[str, ...],
    kinds: Mapping[str, str],
    ranges: Mapping[str, tuple[Fraction, Fraction]],
) -> Fraction:
    total = Fraction(0)
    for name in names:
        if kinds[name] == _KIND_NUMERIC:
            span = ranges.get(name)
            if span is None or span[1] == span[0]:
                continue
            lo, hi = span
            width = hi - lo
            av = _fraction_of_value(a.assignment[name])
            bv = _fraction_of_value(b.assignment[name])
            if av is None or bv is None:
                continue
            delta = (av - bv) / width
            total += delta * delta
        elif a.assignment[name].group_key != b.assignment[name].group_key:
            total += Fraction(1)
    return total


def _cluster_good_regions(
    analysed: list[_AnalysedTrial],
    names: tuple[str, ...],
    kinds: Mapping[str, str],
    neighbours: tuple[tuple[int, ...], ...],
    direction: str,
    median: Fraction | None,
) -> Result[tuple[tuple[GoodRegionCluster, ...], dict[int, int]]]:
    """Connected components of the favourable-side trials over the neighbour graph.

    Adjacency is **mutual** nearest-neighbourship: two favourable trials are linked
    only when each is inside the other's nearest-neighbour set. A lone favourable
    spike far from a dense region reaches its nearest neighbours but they do not
    reciprocate, so it stays a singleton — an isolated spike — without any invented
    distance threshold (AC3, AC4).
    """
    good = [i for i in range(len(analysed)) if _is_good(analysed[i].objective, direction, median)]
    good_set = frozenset(good)
    neighbour_sets = [frozenset(row) for row in neighbours]
    parent = {i: i for i in good}

    def find(node: int) -> int:
        root = node
        while parent[root] != root:
            root = parent[root]
        while parent[node] != root:
            parent[node], node = root, parent[node]
        return root

    for i in good:
        for j in neighbours[i]:
            if j in good_set and i in neighbour_sets[j]:
                parent[find(i)] = find(j)
    components: dict[int, list[int]] = {}
    for i in good:
        components.setdefault(find(i), []).append(i)
    winner_index = _winner_index(analysed, direction)
    ordered_components = sorted(
        components.values(),
        key=lambda group: (-len(group), min(analysed[k].run_id for k in group)),
    )
    clusters: list[GoodRegionCluster] = []
    cluster_of: dict[int, int] = {}
    for index, group in enumerate(ordered_components):
        members = sorted(group, key=lambda k: analysed[k].run_id)
        contains_winner = winner_index is not None and winner_index in group
        distribution = _distribution_over(
            [analysed[k].objective for k in members], [analysed[k] for k in members]
        )
        if is_refusal(distribution):
            return distribution
        summary = distribution.value
        if summary is None:
            continue
        clusters.append(
            GoodRegionCluster(
                index=index,
                member_run_ids=tuple(analysed[k].run_id for k in members),
                parameter_ranges=_cluster_ranges(analysed, members, names, kinds),
                distribution=summary,
                contains_winner=contains_winner,
            )
        )
        for k in group:
            cluster_of[k] = index
    return Ok((tuple(clusters), cluster_of))


def _cluster_ranges(
    analysed: list[_AnalysedTrial],
    members: list[int],
    names: tuple[str, ...],
    kinds: Mapping[str, str],
) -> Mapping[str, Mapping[str, object]]:
    ranges: dict[str, Mapping[str, object]] = {}
    for name in names:
        kind = kinds[name]
        if kind == _KIND_NUMERIC:
            values = [_fraction_of_value(analysed[k].assignment[name]) for k in members]
            present = [value for value in values if value is not None]
            if not present:
                continue
            low = min(present)
            high = max(present)
            ranges[name] = {
                "kind": kind,
                "maximum": {"den": high.denominator, "num": high.numerator},
                "minimum": {"den": low.denominator, "num": low.numerator},
            }
        else:
            tokens = sorted({_group_token(analysed[k].assignment[name].group_key) for k in members})
            ranges[name] = {"kind": kind, "values": tokens}
    return ranges


# --- winner stability --------------------------------------------------------


def _winner_stability(
    analysed: list[_AnalysedTrial],
    direction: str,
    median: Fraction | None,
    neighbours: tuple[tuple[int, ...], ...],
    cluster_of: dict[int, int],
    clusters: tuple[GoodRegionCluster, ...],
) -> Result[WinnerStability]:
    winner_index = _winner_index(analysed, direction)
    if winner_index is None:
        return Ok(
            WinnerStability(
                stability=STABILITY_NO_WINNER,
                winner_run_id=None,
                cluster_index=None,
                cluster_size=0,
                neighbour_run_ids=(),
                good_neighbour_count=0,
            )
        )
    winner = analysed[winner_index]
    neighbour_indices = neighbours[winner_index]
    neighbour_run_ids = tuple(analysed[j].run_id for j in neighbour_indices)
    good_count = sum(
        1 for j in neighbour_indices if _is_good(analysed[j].objective, direction, median)
    )
    local = [winner_index, *neighbour_indices]
    neighbourhood = _distribution_over(
        [analysed[k].objective for k in local], [analysed[k] for k in local]
    )
    if is_refusal(neighbourhood):
        return neighbourhood
    cluster_index = cluster_of.get(winner_index)
    cluster_size = clusters[cluster_index].size if cluster_index is not None else 1
    stability = STABILITY_STABLE_CLUSTER if cluster_size >= 2 else STABILITY_ISOLATED_SPIKE
    return Ok(
        WinnerStability(
            stability=stability,
            winner_run_id=winner.run_id,
            cluster_index=cluster_index,
            cluster_size=cluster_size,
            neighbour_run_ids=neighbour_run_ids,
            good_neighbour_count=good_count,
            neighbourhood=neighbourhood.value,
        )
    )


def _winner_index(analysed: list[_AnalysedTrial], direction: str) -> int | None:
    """The objective-best trial's index; ties break by run id (deterministic)."""
    if not analysed:
        return None
    best = 0
    for i in range(1, len(analysed)):
        if _prefers(analysed[i], analysed[best], direction):
            best = i
    return best


def _prefers(candidate: _AnalysedTrial, incumbent: _AnalysedTrial, direction: str) -> bool:
    if candidate.objective == incumbent.objective:
        return candidate.run_id < incumbent.run_id
    if direction == DIRECTION_MAX:
        return candidate.objective > incumbent.objective
    return candidate.objective < incumbent.objective


def _is_good(objective: Fraction, direction: str, median: Fraction | None) -> bool:
    """Whether the objective is on the favourable side of the median (AC4).

    The median is the data's own value, never an invented threshold. ``max`` favours
    at-or-above the median; ``min`` favours at-or-below it.
    """
    if median is None:
        return True
    if direction == DIRECTION_MAX:
        return objective >= median
    return objective <= median


# --- parameter-value canonicalization ----------------------------------------

_KIND_NUMERIC: Final[str] = "numeric"
_KIND_CATEGORICAL: Final[str] = "categorical"
_KIND_BOOLEAN: Final[str] = "boolean"


@dataclass(frozen=True, slots=True)
class _ParamValue:
    """One canonicalized parameter value: exact, hashable, and identity-bearing."""

    kind: str
    identity: object
    group_key: object
    sort_key: tuple[int, object]
    fraction: Fraction | None


def _ordered_names(analysed: list[_AnalysedTrial]) -> tuple[str, ...]:
    if not analysed:
        return ()
    return tuple(sorted(analysed[0].assignment))


def _parameter_kinds(
    analysed: list[_AnalysedTrial], names: tuple[str, ...]
) -> Result[Mapping[str, str]]:
    """One kind per parameter across trials; a mixed numeric/non-numeric is refused."""
    kinds: dict[str, str] = {}
    for name in names:
        seen: set[str] = set()
        for trial in analysed:
            value = trial.assignment.get(name)
            if value is None:
                continue
            seen.add(value.kind)
        numeric = _KIND_NUMERIC in seen
        non_numeric = seen - {_KIND_NUMERIC}
        if numeric and non_numeric:
            return invalid(
                "parameters",
                "a parameter takes one kind across a Study; a numeric value and a "
                "categorical/boolean value under one name is refused (B-8)",
                parameter=name,
                kinds=sorted(seen),
            )
        if numeric:
            kinds[name] = _KIND_NUMERIC
        elif seen:
            kinds[name] = next(iter(seen))
        else:
            kinds[name] = _KIND_CATEGORICAL
    return Ok(kinds)


def _fraction_of_value(value: _ParamValue) -> Fraction | None:
    return value.fraction


def _group_token(group_key: object) -> str:
    if isinstance(group_key, tuple):
        return "|".join(str(part) for part in cast("tuple[object, ...]", group_key))
    return str(group_key)


def _canon_value(name: str, raw: object) -> Result[_ParamValue]:
    """Canonicalize one parameter value; a binary float is refused (AD-10)."""
    if isinstance(raw, bool):
        return Ok(
            _ParamValue(
                kind=_KIND_BOOLEAN,
                identity=raw,
                group_key=("bool", raw),
                sort_key=(2, int(raw)),
                fraction=None,
            )
        )
    if isinstance(raw, int):
        magnitude = Fraction(raw)
        return Ok(
            _ParamValue(
                kind=_KIND_NUMERIC,
                identity=raw,
                group_key=("num", magnitude.numerator, magnitude.denominator),
                sort_key=(0, magnitude),
                fraction=magnitude,
            )
        )
    if isinstance(raw, ExactRational):
        magnitude = raw.as_fraction()
        return Ok(
            _ParamValue(
                kind=_KIND_NUMERIC,
                identity=raw.fp1_identity(),
                group_key=("num", magnitude.numerator, magnitude.denominator),
                sort_key=(0, magnitude),
                fraction=magnitude,
            )
        )
    if isinstance(raw, Fraction):
        return Ok(
            _ParamValue(
                kind=_KIND_NUMERIC,
                identity={"den": raw.denominator, "num": raw.numerator},
                group_key=("num", raw.numerator, raw.denominator),
                sort_key=(0, raw),
                fraction=raw,
            )
        )
    if isinstance(raw, float):
        return invalid(
            "parameters",
            "an exact parameter value is never a binary float (AD-10)",
            parameter=name,
            given=repr(raw),
        )
    token = clean_token(raw)
    if token is not None:
        return Ok(
            _ParamValue(
                kind=_KIND_CATEGORICAL,
                identity=token,
                group_key=("cat", token),
                sort_key=(1, token),
                fraction=None,
            )
        )
    return invalid(
        "parameters",
        "a parameter value is an int, ExactRational, Fraction, categorical token, or bool",
        parameter=name,
        given=repr(type(raw).__name__),
    )


def _coerce_parameters(value: object) -> Result[dict[str, dict[str, _ParamValue]]]:
    """Coerce the per-trial parameter assignments keyed by run id."""
    out: dict[str, dict[str, _ParamValue]] = {}
    if isinstance(value, Mapping):
        for key, assignment in cast("Mapping[object, object]", value).items():
            run_id = _run_id_token(key)
            if run_id is None:
                return invalid(
                    "parameters",
                    "a parameter assignment is keyed by the trial's run id",
                    given=repr(key),
                )
            parsed = _coerce_assignment(run_id, assignment)
            if is_refusal(parsed):
                return parsed
            out[run_id] = parsed.value
        return Ok(out)
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "parameters",
            "the parameter assignments are a run-id -> {name: value} mapping or a "
            "sequence of {run_id, parameters} records",
            given=repr(type(value).__name__),
        )
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, Mapping):
            return invalid(
                "parameters",
                "each parameter record is a {run_id, parameters} mapping",
                index=index,
                given=repr(type(item).__name__),
            )
        body = cast("Mapping[str, object]", item)
        run_id = _run_id_token(body.get("run_id"))
        if run_id is None:
            return invalid(
                "parameters",
                "each parameter record names the trial's run id",
                index=index,
                given=repr(body.get("run_id")),
            )
        parsed = _coerce_assignment(run_id, body.get("parameters"))
        if is_refusal(parsed):
            return parsed
        out[run_id] = parsed.value
    return Ok(out)


def _coerce_assignment(run_id: str, assignment: object) -> Result[dict[str, _ParamValue]]:
    if not isinstance(assignment, Mapping):
        return invalid(
            "parameters",
            "a trial's parameter assignment is a {name: exact value} mapping",
            run_id=run_id,
            given=repr(type(assignment).__name__),
        )
    out: dict[str, _ParamValue] = {}
    for key, raw in cast("Mapping[object, object]", assignment).items():
        name = clean_token(key)
        if name is None:
            return invalid(
                "parameters",
                "a parameter assignment is keyed by non-empty parameter names",
                run_id=run_id,
                given=repr(key),
            )
        canon = _canon_value(name, raw)
        if is_refusal(canon):
            return canon
        out[name] = canon.value
    if not out:
        return invalid(
            "parameters",
            "a trial's parameter assignment names at least one parameter",
            run_id=run_id,
        )
    return Ok(out)


def _run_id_token(value: object) -> str | None:
    if isinstance(value, Fingerprint):
        return value.value
    return clean_token(value)


# --- objective-magnitude reconstruction (exact, no binary float) -------------


@dataclass(frozen=True, slots=True)
class _Magnitude:
    """A resolved measure slot: an exact value, or an undefined marker."""

    undefined: bool
    value: Fraction
    unit_kind: str
    currency: str | None


def _objective_magnitude(line: LedgerLine, identity: str) -> Result[_Magnitude | None]:
    """Reconstruct the exact magnitude of one measure by identity.

    Returns None when the identity is absent from the line's measures, an undefined
    marker when the slot is an :class:`UndefinedMeasure`, and the exact rational
    magnitude otherwise. No binary float is ever reconstructed (AC5).
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


# --- small parsing helpers ---------------------------------------------------


def _excluded(
    line: LedgerLine,
    reason: str,
    *,
    detail: Mapping[str, object] | None = None,
) -> ExcludedTrial:
    return ExcludedTrial(
        run_id=line.run_id.value,
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


def _as_roster_identity(value: object, field_name: str) -> Result[str]:
    token = clean_token(value)
    if token is None:
        return invalid(
            field_name,
            "the objective is a measure_identity from the AD-23/AD-41 roster",
            given=repr(value),
        )
    lowered = token.casefold()
    for forbidden in FORBIDDEN_COMPOSITE_EXPRESSIONS:
        if forbidden in lowered:
            return reject_composite_expression(token)
    if token not in MEASURE_IDENTITIES:
        return invalid(
            field_name,
            "the sensitivity report analyses one measure_identity from the AD-23/AD-41 "
            "roster; a composite score is never invented (B-10, FR-038)",
            given=token,
            allowed=list(MEASURE_IDENTITIES),
        )
    return Ok(token)


def _as_direction(value: object) -> Result[str]:
    token = clean_token(value)
    if token is None or token not in OBJECTIVE_DIRECTIONS:
        return invalid(
            "direction",
            "the objective direction is min or max; the favourable side of the "
            "distribution is read from it, never an invented threshold (OPT-5, SC-07)",
            given=repr(value),
            allowed=list(OBJECTIVE_DIRECTIONS),
        )
    return Ok(token)


def _as_trial_role(value: object) -> Result[str]:
    token = clean_token(value)
    if token is None:
        return invalid(
            "role",
            "the sensitivity report reads one completed run role; trial, confirmation, "
            "or replicate",
            given=repr(value),
        )
    if token == ROLE_ABORTED:
        return invalid(
            "role",
            "the sensitivity report analyses completed trials, never the aborted role; "
            "refused trials are set aside in the excluded list",
            given=token,
        )
    return Ok(token)


def _as_optional_size(value: object) -> Result[int | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(
            "neighbourhood_size",
            "the neighbourhood size is a positive exact integer, or blank to derive it",
            given=repr(value),
        )
    if value < 1:
        return invalid(
            "neighbourhood_size",
            "the neighbourhood size is at least one nearest neighbour",
            given=repr(value),
        )
    return Ok(value)


def _world_token(value: object) -> str:
    if isinstance(value, World):
        return value.value
    token = clean_token(value)
    return token if token is not None else str(value)
