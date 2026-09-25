"""CT-40 additive ``copilot_profile`` request blob (Story 60.1; DEC-0452).

The pack SDK request lives on ``PluginManifest`` in COMP-QMA-CORE. This module
is the additive CT-40 family schema for the same blob. It is not a contribution
point, not a GrantRecord, and not a new CT number. Inspect SHA ``34c148b`` did
not have ``copilot_profile``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

from qma.core.plugins.pack_sdk import (
    COPILOT_PROFILE_IS_CONTRIBUTION_POINT,
    COPILOT_PROFILE_IS_GRANT,
    PACK_SDK_INSPECT_SHA,
    CopilotProfile,
    PackSdkError,
    parse_copilot_profile,
)
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)

__all__ = [
    "COPILOT_PROFILE_CONTRACT",
    "COPILOT_PROFILE_DTO_OWNER",
    "COPILOT_PROFILE_EXISTED_AT_INSPECT_SHA",
    "COPILOT_PROFILE_INSPECT_SHA",
    "COPILOT_PROFILE_IS_CONTRIBUTION_POINT",
    "COPILOT_PROFILE_IS_GRANT",
    "COPILOT_PROFILE_NEW_CT_MINTED",
    "COPILOT_PROFILE_REFUSED_CT",
    "COPILOT_PROFILE_SCHEMA",
    "COPILOT_PROFILE_SCHEMA_FILE",
    "COPILOT_PROFILE_SCHEMA_NAME",
    "CopilotProfile",
    "parse_wire_copilot_profile",
    "refuse_copilot_profile_as_contribution",
    "refuse_copilot_profile_as_grant",
    "validate_copilot_profile",
]


COPILOT_PROFILE_DTO_OWNER: Final[str] = "COMP-QMA-WIRE"
COPILOT_PROFILE_CONTRACT: Final[str] = "CT-40"
COPILOT_PROFILE_NEW_CT_MINTED: Final[bool] = False
COPILOT_PROFILE_REFUSED_CT: Final[str] = "CT-52"
COPILOT_PROFILE_SCHEMA: Final[str] = "qma.wire.copilot_profile.v1"
COPILOT_PROFILE_SCHEMA_NAME: Final[str] = "copilot_profile"
COPILOT_PROFILE_SCHEMA_FILE: Final[str] = "copilot_profile.v1.schema.json"
COPILOT_PROFILE_INSPECT_SHA: Final[str] = PACK_SDK_INSPECT_SHA
COPILOT_PROFILE_EXISTED_AT_INSPECT_SHA: Final[bool] = False


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def refuse_copilot_profile_as_grant(**extra: object) -> TypedRefusal:
    """``copilot_profile`` is a request blob, not a GrantRecord (DEC-0452)."""
    extra.setdefault("is_grant", False)
    extra.setdefault("is_contribution_point", False)
    extra.setdefault("existed_at_inspect_sha", False)
    extra.setdefault("inspect_sha", COPILOT_PROFILE_INSPECT_SHA)
    return _policy(
        str(extra.pop("field", "copilot_profile")),
        "copilot_profile is a request blob, not a grant (DEC-0452; FR-PG-01)",
        **extra,
    )


def refuse_copilot_profile_as_contribution(**extra: object) -> TypedRefusal:
    """``copilot_profile`` is not a contribution point (DEC-0452)."""
    extra.setdefault("is_grant", False)
    extra.setdefault("is_contribution_point", False)
    extra.setdefault("existed_at_inspect_sha", False)
    extra.setdefault("inspect_sha", COPILOT_PROFILE_INSPECT_SHA)
    return _policy(
        str(extra.pop("field", "copilot_profile")),
        "copilot_profile is not a contribution point (DEC-0452; FR-PG-01)",
        **extra,
    )


def parse_wire_copilot_profile(value: object) -> Result[CopilotProfile]:
    """Parse the CT-40 copilot_profile request blob. Omit is handled by the caller."""
    if isinstance(value, CopilotProfile):
        return Ok(value)
    if value is None:
        return _invalid(
            "copilot_profile",
            "copilot_profile must be omitted when unused, never null (DEC-0452)",
        )
    try:
        return Ok(parse_copilot_profile(value))
    except PackSdkError as exc:
        message = str(exc)
        if "not a grant" in message:
            return refuse_copilot_profile_as_grant(detail=message)
        if "not a contribution point" in message:
            return refuse_copilot_profile_as_contribution(detail=message)
        return _invalid("copilot_profile", message)


def validate_copilot_profile(value: object) -> Result[CopilotProfile]:
    """Schema-then-DTO validation for the additive CT-40 copilot_profile blob."""
    from qma.wire.schemas import validate_instance  # noqa: PLC0415

    if isinstance(value, CopilotProfile):
        payload = dict(value.to_payload())
    elif isinstance(value, Mapping):
        payload = dict(cast("Mapping[str, object]", value))
    else:
        return parse_wire_copilot_profile(value)
    checked = validate_instance(payload, COPILOT_PROFILE_SCHEMA_NAME)
    if is_refusal(checked):
        return checked
    return parse_wire_copilot_profile(checked.value)
