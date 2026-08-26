"""Parameter schema, pure sampler port, and sensitivity-analysis home (B-8).

The default sampler adapter is TPE-class, pinned by ``registry:qmb_sampler_pin``.
Adapters run ``n_jobs=1``: process fan-out belongs to the orchestrator, never
the sampler (DEC-0168, DEC-0161). The pin value lives in the registry and
the distribution manifest, never restated here.

The typed parameter-space schema is ONE schema, authoritative in the CT-33
Bot definition — B-8 reads it; QMB never keeps a second local copy
(DEC-0173, DEC-0183).
"""

from __future__ import annotations

from typing import Final

from qmf.core.refusal import Ok, Result, is_refusal
from qml.declaration.bot import BotDefinition
from qml.declaration.parameters import ParameterSpec

from qmb.optimize.objective import (
    DIRECTION_MAX,
    DIRECTION_MIN,
    INCOMPLETE_TRIAL_CONSTRAINT_MISSING,
    INCOMPLETE_TRIAL_CONSTRAINT_UNDEFINED,
    INCOMPLETE_TRIAL_OBJECTIVE_MISSING,
    INCOMPLETE_TRIAL_OBJECTIVE_UNDEFINED,
    INCOMPLETE_TRIAL_REASONS,
    INCOMPLETE_TRIAL_REFUSED,
    MIN_TRADES_FLOOR_KEY,
    MIN_TRADES_GATE_DEFAULT_ON,
    MIN_TRADES_HAS_SPINE_CONSTANT,
    MIN_TRADES_MEASURE,
    MIN_TRADES_OPERATOR,
    OBJECTIVE_DIRECTIONS,
    STUDY_CONSTRAINT_CLASS,
    STUDY_CONSTRAINT_OPERATORS,
    STUDY_CRITERIA_CLASS,
    STUDY_CRITERIA_FORMAT_VERSION,
    STUDY_CRITERIA_KEY,
    STUDY_OBJECTIVE_CLASS,
    WINNER_MAKES_BAR_VERDICT,
    WINNER_MAKES_EDGE_CLAIM,
    WINNER_ROLE,
    WINNER_SET_CLASS,
    WINNER_SET_FORMAT_VERSION,
    WINNER_VERDICT_DEFERRED_TO,
    IncompleteTrial,
    MinTradesGate,
    ScoredTrial,
    StudyConstraint,
    StudyCriteria,
    StudyObjective,
    StudyWinnerSet,
    coerce_study_criteria,
    compute_winner_set,
    study_criteria_identity,
)
from qmb.optimize.space import (
    STUDY_SPACE_CLASS,
    STUDY_SPACE_FORMAT_VERSION,
    STUDY_SPACE_KEY,
    StudyParameterSpace,
    coerce_study_space,
    study_space_from_bot,
    study_space_identity,
)

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
    "SAMPLER_JOBS",
    "SAMPLER_PIN_KEY",
    "STUDY_CONSTRAINT_CLASS",
    "STUDY_CONSTRAINT_OPERATORS",
    "STUDY_CRITERIA_CLASS",
    "STUDY_CRITERIA_FORMAT_VERSION",
    "STUDY_CRITERIA_KEY",
    "STUDY_OBJECTIVE_CLASS",
    "STUDY_SPACE_CLASS",
    "STUDY_SPACE_FORMAT_VERSION",
    "STUDY_SPACE_KEY",
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
    "StudyParameterSpace",
    "StudyWinnerSet",
    "coerce_study_criteria",
    "coerce_study_space",
    "compute_winner_set",
    "parameter_space_from_bot",
    "sampler_identity",
    "study_criteria_identity",
    "study_space_from_bot",
    "study_space_identity",
]

SAMPLER_PIN_KEY: Final[str] = "qmb_sampler_pin"
SAMPLER_JOBS: Final[int] = 1


def parameter_space_from_bot(declaration: object) -> Result[tuple[ParameterSpec, ...]]:
    """Read the CT-33-authoritative parameter-space schema (B-8, DEC-0183).

    Mandatory defaults are the Bot definition's canonical assignment. A swept
    non-default assignment is a B-3 run-spec override, never a silent new default.
    """
    if isinstance(declaration, BotDefinition):
        bot = declaration
    else:
        parsed = BotDefinition.try_from_mapping(declaration)
        if is_refusal(parsed):
            return parsed
        bot = parsed.value
    return Ok(tuple(bot.parameter_space))


def sampler_identity() -> dict[str, object]:
    """Identity-bearing sampler-port fields. Package SemVer is omitted."""
    return {
        "pin_key": SAMPLER_PIN_KEY,
        "jobs": SAMPLER_JOBS,
        "stepping": "generation-barrier",
    }
