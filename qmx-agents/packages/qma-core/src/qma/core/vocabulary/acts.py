"""Distinct governed acts admit / apply / promote (FR-Q10; DEC-0345)."""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from qma.core.vocabulary.enums import GovernedAct
from qma.core.vocabulary.registry import VocabularyError

__all__ = [
    "ACT_TARGET",
    "GovernedAct",
    "GovernedActTarget",
    "validate_governed_act",
]


class GovernedActTarget(StrEnum):
    """Target kind each closed verb may govern."""

    MEMORY_CANDIDATE = "memory_candidate"
    REFINEMENT_PROPOSAL = "refinement_proposal"
    REGISTERED_ARTIFACT = "registered_artifact"


ACT_TARGET: Final[dict[GovernedAct, GovernedActTarget]] = {
    GovernedAct.ADMIT: GovernedActTarget.MEMORY_CANDIDATE,
    GovernedAct.APPLY: GovernedActTarget.REFINEMENT_PROPOSAL,
    GovernedAct.PROMOTE: GovernedActTarget.REGISTERED_ARTIFACT,
}


def validate_governed_act(
    act: GovernedAct | str,
    target: GovernedActTarget | str,
) -> None:
    """Reject interchange of admit / apply / promote across target kinds.

    A memory candidate is admitted, a RefinementProposal is applied from the
    staging store, and only a human outside QMA promotes a registered artifact.
    ``promote`` / ``promotion`` never apply to memory or refinement.
    """
    try:
        resolved_act = act if isinstance(act, GovernedAct) else GovernedAct(act)
    except ValueError as exc:
        raise VocabularyError(f"{act!r} is not a governed act") from exc
    try:
        resolved_target = (
            target if isinstance(target, GovernedActTarget) else GovernedActTarget(target)
        )
    except ValueError as exc:
        raise VocabularyError(f"{target!r} is not a governed-act target") from exc

    expected = ACT_TARGET[resolved_act]
    if resolved_target != expected:
        raise VocabularyError(
            f"governed act {resolved_act.value!r} applies only to "
            f"{expected.value!r}, not {resolved_target.value!r} "
            "(admit=memory, apply=refinement, promote=registered artifact outside QMA)"
        )
