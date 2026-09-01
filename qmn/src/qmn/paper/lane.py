"""No per-bot paper lane on the node (DEC-0261; Story 26.5 AC3).

Bots arrive backtested, iterated, and paper-tested outside the node. The node
hosts only operator-approved bots and grants no per-bot warm-up, probation,
ramp, paper namespace, or paper-performance gate. The only post-activation
route back to paper is a BMS/Book protective demotion (AD-35).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qmf.core import Ok, Result, TypedRefusal

from qmn.paper._refuse import clean_token, invalid, policy

__all__ = [
    "FORBIDDEN_PER_BOT_PAPER_SURFACES",
    "POST_ACTIVATION_PAPER_ROUTE",
    "BotNodeJourney",
    "inspect_bot_node_journey",
    "refuse_per_bot_paper_lane",
]

FORBIDDEN_PER_BOT_PAPER_SURFACES: Final[frozenset[str]] = frozenset(
    {
        "per-bot-warm-up",
        "probation",
        "ramp",
        "paper-namespace",
        "paper-performance-gate",
        "bot-paper-twin",
        "book-paper-twin",
        "per-bot-paper-lane",
    }
)

POST_ACTIVATION_PAPER_ROUTE: Final[str] = "bms-book-protective-demotion"


@dataclass(frozen=True, slots=True)
class BotNodeJourney:
    """Inspection of a newly promoted bot's node journey (DEC-0261).

    Confirms the absence of every forbidden per-bot paper surface and names the
    sole post-activation paper route.
    """

    bot_id: str
    promoted: bool
    activated: bool
    per_bot_warm_up: bool = False
    probation: bool = False
    ramp: bool = False
    paper_namespace: bool = False
    paper_performance_gate: bool = False
    post_activation_paper_route: str = POST_ACTIVATION_PAPER_ROUTE

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "activated": self.activated,
                "bot_id": self.bot_id,
                "paper_namespace": self.paper_namespace,
                "paper_performance_gate": self.paper_performance_gate,
                "per_bot_warm_up": self.per_bot_warm_up,
                "post_activation_paper_route": self.post_activation_paper_route,
                "probation": self.probation,
                "promoted": self.promoted,
                "ramp": self.ramp,
            }
        )


def refuse_per_bot_paper_lane(surface: object) -> TypedRefusal:
    """Refuse any attempt to open a forbidden per-bot paper surface."""
    token = clean_token(surface)
    if token is None:
        return invalid(
            "surface",
            "a per-bot paper surface name is a non-empty token",
            given=repr(surface),
        )
    normalized = token.strip().lower().replace("_", "-").replace(" ", "-")
    if normalized in FORBIDDEN_PER_BOT_PAPER_SURFACES or token in FORBIDDEN_PER_BOT_PAPER_SURFACES:
        return policy(
            "surface",
            "the node grants no per-bot warm-up, probation, ramp, paper "
            "namespace, paper-performance gate, or paper twin; the only "
            "post-activation paper route is a BMS/Book protective demotion",
            given=token,
            forbidden=sorted(FORBIDDEN_PER_BOT_PAPER_SURFACES),
            sole_route=POST_ACTIVATION_PAPER_ROUTE,
        )
    return policy(
        "surface",
        "unknown per-bot paper surface; the node admits none of the forbidden "
        "lane vocabulary and invents no replacement",
        given=token,
        forbidden=sorted(FORBIDDEN_PER_BOT_PAPER_SURFACES),
    )


def inspect_bot_node_journey(
    *,
    bot_id: object,
    promoted: object = True,
    activated: object = True,
    request_warm_up: object = False,
    request_probation: object = False,
    request_ramp: object = False,
    request_paper_namespace: object = False,
    request_paper_performance_gate: object = False,
) -> Result[BotNodeJourney]:
    """Inspect a promoted bot's node journey — every per-bot lane request fails.

    Returns the journey record only when no forbidden surface was requested.
    """
    token = clean_token(bot_id)
    if token is None:
        return invalid(
            "bot_id",
            "a bot node journey names a non-empty bot id",
            given=repr(bot_id),
        )
    if not isinstance(promoted, bool) or not isinstance(activated, bool):
        return invalid(
            "promoted",
            "promoted and activated are bool flags",
            given=repr((promoted, activated)),
        )

    requested: dict[str, object] = {
        "per-bot-warm-up": request_warm_up,
        "probation": request_probation,
        "ramp": request_ramp,
        "paper-namespace": request_paper_namespace,
        "paper-performance-gate": request_paper_performance_gate,
    }
    for surface, flag in requested.items():
        if flag is True:
            return refuse_per_bot_paper_lane(surface)
        if flag is not False:
            return invalid(
                surface,
                "per-bot lane request flags are bool",
                given=repr(flag),
            )

    return Ok(
        BotNodeJourney(
            bot_id=token,
            promoted=promoted,
            activated=activated,
            per_bot_warm_up=False,
            probation=False,
            ramp=False,
            paper_namespace=False,
            paper_performance_gate=False,
            post_activation_paper_route=POST_ACTIVATION_PAPER_ROUTE,
        )
    )
