"""One QuantMind/QMX Copilot product identity (Story 60.4; kit AD-3; DEC-0454).

One product over independently scoped ``psess:`` sessions. The in-app panel is
an optional contract over an app-use ``psess:``, not GAP-0081 chrome and not a
second copilot. ``sess:`` remains the engine run, not a third chat. Tool
availability is parent AD-9 intersection. Skills describe; they do not grant.
Hooks cannot override a failed privilege gate.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

from qma.core.control.primitives import Skill
from qma.core.ports.capabilities import assert_skill_is_not_capability_grant
from qma.core.vocabulary.enums import HookResultDecision
from qmf.core import Ok, Result, is_ok
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "APP_USE_MAY_APPLY",
    "CONTEXT_TRANSFER_KINDS",
    "CONTRIBUTION_HIT_IS_GRANT",
    "COPILOT_PRODUCT_ALIASES",
    "COPILOT_PRODUCT_IDENTITY",
    "COPILOT_SEAT_PROFILES",
    "ENGINE_RUN_ID_PREFIX",
    "ENGINE_RUN_IS_THIRD_CHAT",
    "GAP_0081_CHROME_FILLED",
    "HOOKS_OVERRIDE_PRIVILEGE_GATE",
    "INSTANCE_MAY_OMIT_PANEL",
    "IN_APP_PANEL_IS_CONTRACT",
    "IN_APP_PANEL_IS_GAP_0081_CHROME",
    "IN_APP_PANEL_IS_SECOND_COPILOT",
    "PACK_MAY_OMIT_COPILOT_PROFILE",
    "PANEL_DISPOSE_CANCELS_JOB_HANDLE",
    "PRODUCT_SESSION_ID_PREFIX",
    "RECONNECT_REPLAYS_UNACKED_INTENT",
    "SECOND_COPILOT_PRODUCT_MINTED",
    "SKILLS_GRANT",
    "intersect_tool_availability",
    "parse_copilot_product_identity",
    "privilege_gate_holds",
    "refuse_context_transfer",
    "refuse_engine_run_as_chat",
    "refuse_hooks_override_privilege_gate",
    "refuse_panel_as_second_copilot",
    "refuse_second_copilot_product",
    "refuse_skill_as_grant",
]


COPILOT_PRODUCT_IDENTITY: Final[str] = "QuantMind/QMX Copilot"
COPILOT_PRODUCT_ALIASES: Final[frozenset[str]] = frozenset(
    {
        COPILOT_PRODUCT_IDENTITY,
        "QuantMind Copilot",
        "QMX Copilot",
    }
)
COPILOT_SEAT_PROFILES: Final[frozenset[str]] = frozenset({"authoring", "app-use"})
PRODUCT_SESSION_ID_PREFIX: Final[str] = "psess:"
ENGINE_RUN_ID_PREFIX: Final[str] = "sess:"
SECOND_COPILOT_PRODUCT_MINTED: Final[bool] = False
ENGINE_RUN_IS_THIRD_CHAT: Final[bool] = False
IN_APP_PANEL_IS_CONTRACT: Final[bool] = True
IN_APP_PANEL_IS_GAP_0081_CHROME: Final[bool] = False
IN_APP_PANEL_IS_SECOND_COPILOT: Final[bool] = False
GAP_0081_CHROME_FILLED: Final[bool] = False
PACK_MAY_OMIT_COPILOT_PROFILE: Final[bool] = True
INSTANCE_MAY_OMIT_PANEL: Final[bool] = True
PANEL_DISPOSE_CANCELS_JOB_HANDLE: Final[bool] = False
RECONNECT_REPLAYS_UNACKED_INTENT: Final[bool] = False
APP_USE_MAY_APPLY: Final[bool] = False
SKILLS_GRANT: Final[bool] = False
CONTRIBUTION_HIT_IS_GRANT: Final[bool] = False
HOOKS_OVERRIDE_PRIVILEGE_GATE: Final[bool] = False
CONTEXT_TRANSFER_KINDS: Final[frozenset[str]] = frozenset({"selected_refs", "change_request"})


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def parse_copilot_product_identity(value: object) -> Result[str]:
    """One product identity. Aliases collapse; a second copilot is refused."""
    if not isinstance(value, str) or value.strip() == "":
        return _policy(
            "copilot_identity",
            "copilot product identity is QuantMind/QMX Copilot (DEC-0454; FR-PG-07)",
            given=repr(value),
            second_copilot=False,
        )
    token = value.strip()
    if token in COPILOT_PRODUCT_ALIASES:
        return Ok(COPILOT_PRODUCT_IDENTITY)
    return refuse_second_copilot_product(given=token)


def refuse_second_copilot_product(**extra: object) -> TypedRefusal:
    extra.setdefault("second_copilot", False)
    extra.setdefault("identity", COPILOT_PRODUCT_IDENTITY)
    extra.setdefault("minted", SECOND_COPILOT_PRODUCT_MINTED)
    return _policy(
        str(extra.pop("field", "copilot_identity")),
        "QuantMind/QMX Copilot is one product identity; a second copilot is refused "
        "(DEC-0454; FR-PG-07; UX-DR-PG-01)",
        **extra,
    )


def refuse_panel_as_second_copilot(**extra: object) -> TypedRefusal:
    extra.setdefault("is_contract", IN_APP_PANEL_IS_CONTRACT)
    extra.setdefault("is_gap_0081_chrome", IN_APP_PANEL_IS_GAP_0081_CHROME)
    extra.setdefault("is_second_copilot", IN_APP_PANEL_IS_SECOND_COPILOT)
    extra.setdefault("gap_0081_chrome_filled", GAP_0081_CHROME_FILLED)
    return _policy(
        str(extra.pop("field", "panel")),
        "the in-app panel is an optional contract over an app-use psess:, "
        "not GAP-0081 chrome and not a second copilot (DEC-0454; SCN-0024)",
        **extra,
    )


def refuse_engine_run_as_chat(**extra: object) -> TypedRefusal:
    extra.setdefault("third_chat", ENGINE_RUN_IS_THIRD_CHAT)
    extra.setdefault("prefix", ENGINE_RUN_ID_PREFIX)
    extra.setdefault("product_session_prefix", PRODUCT_SESSION_ID_PREFIX)
    return _policy(
        str(extra.pop("field", "session_id")),
        "QMA sess: remains the engine run, not a third chat (DEC-0454; FR-PG-13)",
        **extra,
    )


def refuse_hooks_override_privilege_gate(**extra: object) -> TypedRefusal:
    extra.setdefault("hooks_override", HOOKS_OVERRIDE_PRIVILEGE_GATE)
    extra.setdefault("skills_grant", SKILLS_GRANT)
    extra.setdefault("hit_is_grant", CONTRIBUTION_HIT_IS_GRANT)
    return _policy(
        str(extra.pop("field", "privilege_gate")),
        "hooks cannot override a failed privilege gate; skills describe and "
        "ContributionHit is not a grant (DEC-0458; FR-PG-16; parent AD-9)",
        **extra,
    )


def refuse_skill_as_grant(skill: Skill, **extra: object) -> Result[str]:
    """Skills describe; they do not grant (parent AD-9; DEC-0458)."""
    asserted = assert_skill_is_not_capability_grant(skill)
    if not is_ok(asserted):
        return asserted
    extra.setdefault("skills_grant", SKILLS_GRANT)
    extra.setdefault("qualified_id", skill.qualified_id)
    if extra.get("treat_as_grant") is True:
        return _policy(
            "skill",
            "skills describe; they do not grant (DEC-0458; FR-PG-16; parent AD-9)",
            **extra,
        )
    return Ok(skill.qualified_id)


def refuse_context_transfer(kind: object, **extra: object) -> TypedRefusal:
    extra.setdefault("allowed", sorted(CONTEXT_TRANSFER_KINDS))
    extra.setdefault("given", kind)
    return _policy(
        str(extra.pop("field", "context_transfer")),
        "context transfer is explicit selected_refs or change_request only "
        "(DEC-0454; FR-PG-13)",
        **extra,
    )


def intersect_tool_availability(
    published: Iterable[str],
    host_grants: Iterable[str],
    session_grants: Iterable[str],
    healthy: Iterable[str],
) -> frozenset[str]:
    """Parent AD-9: published ContributionHits ∩ host grants ∩ session GrantRecords ∩ health."""
    return (
        frozenset(item for item in published if str(item).strip())
        & frozenset(item for item in host_grants if str(item).strip())
        & frozenset(item for item in session_grants if str(item).strip())
        & frozenset(item for item in healthy if str(item).strip())
    )


def privilege_gate_holds(
    *,
    available: Iterable[str],
    qualified_id: str,
    hook_decision: HookResultDecision | str | None = None,
) -> Result[str]:
    """A failed intersection is not rescued by a hook allow (DEC-0458)."""
    live = frozenset(item for item in available if str(item).strip())
    if qualified_id in live:
        return Ok(qualified_id)
    if hook_decision in {HookResultDecision.ALLOW, "allow"}:
        return refuse_hooks_override_privilege_gate(
            qualified_id=qualified_id,
            hook_decision="allow",
        )
    return refuse_hooks_override_privilege_gate(qualified_id=qualified_id)
