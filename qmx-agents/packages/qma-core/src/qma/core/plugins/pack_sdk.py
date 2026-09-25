"""Pack SDK request surface (Story 60.1; kit AD-1; DEC-0452).

A pack **requests** operation contributes, optional ``view:*`` wire DTOs,
optional ``copilot_profile``, and requested capabilities. Installing is not
granting. Enabling after validate is not granting. A session GrantRecord is
granting (Story 54.4). ``copilot_profile`` is not a contribution point and
not a grant. ``requested_capabilities`` is the AMEND/alias of existing
``permissions`` — one request field, not two.

Honesty at inspect SHA ``34c148b``: ``contributes`` already existed as
``{point, local_id}`` objects and ``permissions`` already existed as the
empty-collection request tuple. ``copilot_profile`` did not exist.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal, cast

__all__ = [
    "BROKER_VENUE_OP_OWNER",
    "CLOSED_QMA_STORE_CLASSES_STAY_CLOSED",
    "CONTRIBUTES_EXISTED_AT_INSPECT_SHA",
    "COPILOT_PROFILE_EXISTED_AT_INSPECT_SHA",
    "COPILOT_PROFILE_IS_CONTRIBUTION_POINT",
    "COPILOT_PROFILE_IS_GRANT",
    "ENABLE_AFTER_VALIDATE_IS_GRANT",
    "HEADLESS_HAS_COPILOT_PANEL",
    "HEADLESS_HAS_NAVIGATION",
    "INSTALL_IS_GRANT",
    "PACK_SDK_INSPECT_SHA",
    "PACK_SDK_NEW_CT_MINTED",
    "PERMISSIONS_EXISTED_AT_INSPECT_SHA",
    "QMA_IS_HOST_RUNTIME",
    "QMF_IS_APPLICATION_LAYER_OWNER",
    "REQUESTED_CAPABILITIES_IS_PERMISSIONS_ALIAS",
    "SESSION_GRANT_RECORD_IS_GRANT",
    "VIEW_STAR_IS_CONTRIBUTION_POINT",
    "VIEW_STAR_IS_JSON_RENDER_RUNTIME_ID",
    "WIDGETS_OWN_INVOKE",
    "CopilotProfile",
    "PackSdkError",
    "PackViewRequest",
    "SuggestedOp",
    "parse_copilot_profile",
    "parse_optional_copilot_profile",
    "parse_pack_views",
    "parse_requested_capabilities",
]


PACK_SDK_INSPECT_SHA: Final[str] = "34c148b"
PACK_SDK_NEW_CT_MINTED: Final[bool] = False
CONTRIBUTES_EXISTED_AT_INSPECT_SHA: Final[bool] = True
PERMISSIONS_EXISTED_AT_INSPECT_SHA: Final[bool] = True
COPILOT_PROFILE_EXISTED_AT_INSPECT_SHA: Final[bool] = False
COPILOT_PROFILE_IS_CONTRIBUTION_POINT: Final[bool] = False
COPILOT_PROFILE_IS_GRANT: Final[bool] = False
REQUESTED_CAPABILITIES_IS_PERMISSIONS_ALIAS: Final[bool] = True
INSTALL_IS_GRANT: Final[bool] = False
ENABLE_AFTER_VALIDATE_IS_GRANT: Final[bool] = False
SESSION_GRANT_RECORD_IS_GRANT: Final[bool] = True
VIEW_STAR_IS_CONTRIBUTION_POINT: Final[bool] = False
VIEW_STAR_IS_JSON_RENDER_RUNTIME_ID: Final[bool] = False
WIDGETS_OWN_INVOKE: Final[bool] = False
HEADLESS_HAS_NAVIGATION: Final[bool] = False
HEADLESS_HAS_COPILOT_PANEL: Final[bool] = False
QMA_IS_HOST_RUNTIME: Final[bool] = True
QMF_IS_APPLICATION_LAYER_OWNER: Final[bool] = False
BROKER_VENUE_OP_OWNER: Final[str] = "COMP-QMN"
CLOSED_QMA_STORE_CLASSES_STAY_CLOSED: Final[bool] = True

_GRANT_IDENTITY_KEYS: Final[frozenset[str]] = frozenset(
    {"grant_id", "granted_ops", "GrantRecord", "authorizes_invoke"}
)
_CONTRIBUTION_IDENTITY_KEYS: Final[frozenset[str]] = frozenset(
    {"point", "hit_class", "plugin_id", "package_id", "availability_revision"}
)
_VIEW_FORBIDDEN_KEYS: Final[frozenset[str]] = frozenset(
    {
        "point",
        "hit_class",
        "plugin_id",
        "package_id",
        "grant_id",
        "granted_ops",
        "GrantRecord",
        "json_render",
        "json-render",
        "runtime_id",
        "authorizes_invoke",
        "owns_invoke",
        "widget_invoke",
        "invoke",
    }
)
_SUGGESTED_OP_KEYS: Final[frozenset[str]] = frozenset({"op_id", "op_version", "qualified_id"})
_COPILOT_PROFILE_KEYS: Final[frozenset[str]] = frozenset({"prompts", "suggested_ops"})
_VIEW_REQUEST_KEYS: Final[frozenset[str]] = frozenset({"view_id", "op_id", "view_version"})


class PackSdkError(ValueError):
    """Raised when pack SDK request fields violate Story 60.1 law."""


@dataclass(frozen=True, slots=True)
class SuggestedOp:
    """Display hint on a copilot profile. Never a grant (DEC-0452; M-2)."""

    op_id: str
    op_version: int
    qualified_id: str

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "op_id": self.op_id,
                "op_version": self.op_version,
                "qualified_id": self.qualified_id,
            }
        )


@dataclass(frozen=True, slots=True)
class CopilotProfile:
    """Optional pack copilot request blob — not a contribution point, not a grant."""

    prompts: tuple[str, ...] = ()
    suggested_ops: tuple[SuggestedOp, ...] = ()
    is_contribution_point: Literal[False] = False
    is_grant: Literal[False] = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "prompts": list(self.prompts),
                "suggested_ops": [dict(item.to_payload()) for item in self.suggested_ops],
            }
        )


@dataclass(frozen=True, slots=True)
class PackViewRequest:
    """Optional pack ``view:*`` wire DTO request (parent AD-17).

    Not a plugin contribution point, not a json-render runtime id, and not an
    invoke owner. Widgets never own invoke.
    """

    view_id: str
    op_id: str
    view_version: int = 1
    is_contribution_point: Literal[False] = False
    is_json_render_runtime_id: Literal[False] = False
    widgets_own_invoke: Literal[False] = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "op_id": self.op_id,
                "view_id": self.view_id,
                "view_version": self.view_version,
            }
        )


def parse_requested_capabilities(raw: Mapping[str, object]) -> tuple[str, ...]:
    """Return the single request tuple from ``permissions`` or its kit alias.

    ``requested_capabilities`` is the AMEND/alias of ``permissions``. Both keys
    at once are two live request fields and are refused (FR-PG-01; DEC-0452).
    """
    has_permissions = "permissions" in raw
    has_requested = "requested_capabilities" in raw
    if has_permissions and has_requested:
        raise PackSdkError(
            "requested_capabilities is the AMEND/alias of permissions; "
            "do not leave two live request fields (DEC-0452; FR-PG-01)"
        )
    key = "requested_capabilities" if has_requested else "permissions"
    if key in raw and raw[key] is None:
        raise PackSdkError(
            f"{key} must be an empty collection when undeclared, never null (CT-42; FR-Q68)"
        )
    value = raw.get(key, ())
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise PackSdkError(f"{key} must be a sequence")
    items = cast(Sequence[object], value)
    parsed: list[str] = []
    for item in items:
        if not isinstance(item, str):
            raise PackSdkError(f"{key} entries must be strings; got {item!r}")
        parsed.append(item)
    return tuple(parsed)


def parse_optional_copilot_profile(raw: Mapping[str, object]) -> CopilotProfile | None:
    """Omit is valid. Null is refused. Present blob is a request, never a grant."""
    if "copilot_profile" not in raw:
        return None
    value = raw["copilot_profile"]
    if value is None:
        raise PackSdkError("copilot_profile must be omitted when unused, never null (DEC-0452)")
    return parse_copilot_profile(value)


def parse_copilot_profile(value: object) -> CopilotProfile:
    """Parse the optional copilot request blob (prompts + suggested ops)."""
    if not isinstance(value, Mapping):
        raise PackSdkError(
            f"copilot_profile must be a mapping request blob; got {type(value).__name__}"
        )
    body = {str(key): item for key, item in cast(Mapping[object, object], value).items()}
    stolen_grant = sorted(key for key in body if key in _GRANT_IDENTITY_KEYS)
    if stolen_grant:
        raise PackSdkError(
            "copilot_profile is a request blob, not a grant "
            f"(fields={stolen_grant}; DEC-0452; FR-PG-01)"
        )
    stolen_point = sorted(key for key in body if key in _CONTRIBUTION_IDENTITY_KEYS)
    if stolen_point:
        raise PackSdkError(
            "copilot_profile is not a contribution point "
            f"(fields={stolen_point}; DEC-0452; FR-PG-01)"
        )
    extra = sorted(key for key in body if key not in _COPILOT_PROFILE_KEYS)
    if extra:
        raise PackSdkError(f"copilot_profile unknown fields {extra}")
    prompts = _parse_str_tuple(body.get("prompts", ()), field="copilot_profile.prompts")
    suggested = _parse_suggested_ops(body.get("suggested_ops", ()))
    return CopilotProfile(
        prompts=prompts,
        suggested_ops=suggested,
        is_contribution_point=False,
        is_grant=False,
    )


def parse_pack_views(raw: Mapping[str, object]) -> tuple[PackViewRequest, ...]:
    """Parse optional ``views`` as parent AD-17 ``view:*`` request DTOs."""
    if "views" not in raw:
        return ()
    value = raw["views"]
    if value is None:
        raise PackSdkError("views must be an empty collection when undeclared, never null (CT-42)")
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise PackSdkError("views must be a sequence of view:* wire DTO requests")
    parsed: list[PackViewRequest] = []
    seen: set[str] = set()
    for item in cast(Sequence[object], value):
        view = _parse_one_view(item)
        if view.view_id in seen:
            raise PackSdkError(f"duplicate view_id {view.view_id!r} on the pack")
        seen.add(view.view_id)
        parsed.append(view)
    return tuple(parsed)


def _parse_str_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise PackSdkError(f"{field} must be a sequence of strings")
    items: list[str] = []
    for item in cast(Sequence[object], value):
        if not isinstance(item, str) or item.strip() == "":
            raise PackSdkError(f"{field} entries must be non-empty strings; got {item!r}")
        items.append(item)
    return tuple(items)


def _parse_suggested_ops(value: object) -> tuple[SuggestedOp, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise PackSdkError("copilot_profile.suggested_ops must be a sequence")
    parsed: list[SuggestedOp] = []
    for item in cast(Sequence[object], value):
        if not isinstance(item, Mapping):
            raise PackSdkError(
                "suggested_ops entries must be {op_id, op_version, qualified_id} objects"
            )
        body = {str(key): val for key, val in cast(Mapping[object, object], item).items()}
        extra = sorted(key for key in body if key not in _SUGGESTED_OP_KEYS)
        if extra:
            raise PackSdkError(f"suggested_ops unknown fields {extra}")
        grantish = sorted(key for key in body if key in _GRANT_IDENTITY_KEYS)
        if grantish:
            raise PackSdkError(
                f"suggested_ops are display hints, not grants (fields={grantish}; DEC-0452)"
            )
        op_id = body.get("op_id")
        if not isinstance(op_id, str) or op_id.strip() == "":
            raise PackSdkError(f"suggested_ops.op_id must be a non-empty string; got {op_id!r}")
        version = body.get("op_version")
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise PackSdkError(
                f"suggested_ops.op_version must be a positive integer; got {version!r}"
            )
        qualified = body.get("qualified_id")
        if not isinstance(qualified, str) or qualified.strip() == "":
            raise PackSdkError(
                f"suggested_ops.qualified_id must be a non-empty string; got {qualified!r}"
            )
        parsed.append(
            SuggestedOp(op_id=op_id.strip(), op_version=version, qualified_id=qualified.strip())
        )
    return tuple(parsed)


def _parse_one_view(item: object) -> PackViewRequest:
    if not isinstance(item, Mapping):
        raise PackSdkError(
            "views entries must be view:* wire DTO mappings, never a contribution point"
        )
    body = {str(key): val for key, val in cast(Mapping[object, object], item).items()}
    stolen = sorted(key for key in body if key in _VIEW_FORBIDDEN_KEYS)
    if stolen:
        if any(key in {"json_render", "json-render", "runtime_id"} for key in stolen):
            raise PackSdkError(
                f"view:* is not a json-render runtime id (fields={stolen}; DEC-0452; FR-PG-04)"
            )
        invoke_keys = {"authorizes_invoke", "owns_invoke", "widget_invoke", "invoke"}
        if any(key in invoke_keys for key in stolen):
            raise PackSdkError(
                "widgets never own invoke; view:* is a wire DTO "
                f"(fields={stolen}; DEC-0452; FR-PG-04)"
            )
        raise PackSdkError(
            "view:* is a parent AD-17 wire DTO, not a plugin contribution point "
            f"(fields={stolen}; DEC-0452; FR-PG-04)"
        )
    extra = sorted(key for key in body if key not in _VIEW_REQUEST_KEYS)
    if extra:
        raise PackSdkError(f"views unknown fields {extra}")
    view_id = body.get("view_id")
    if not isinstance(view_id, str) or view_id.strip() == "":
        raise PackSdkError(f"views.view_id must be a non-empty view:* id; got {view_id!r}")
    token = view_id.strip()
    folded = token.casefold()
    retired_ids = {"ui_view", "view", "copilot", "copilot_profile"}
    if folded in retired_ids or folded.replace("-", "_") == "ui_view":
        raise PackSdkError(
            f"view:* is not a plugin contribution point; got view_id={token!r} (DEC-0452)"
        )
    if folded.startswith("json-render") or folded.startswith("json_render"):
        raise PackSdkError(
            f"view:* is not a json-render runtime id (view_id={token!r}; DEC-0452; FR-PG-04)"
        )
    if not folded.startswith("view:"):
        raise PackSdkError(
            f"views.view_id must use the view:* prefix; got {token!r} (parent AD-17)"
        )
    op_id = body.get("op_id")
    if not isinstance(op_id, str) or op_id.strip() == "":
        raise PackSdkError(
            "views.op_id names an existing AD-3 operation; widgets never own invoke "
            f"(got {op_id!r})"
        )
    version_raw = body.get("view_version", 1)
    if isinstance(version_raw, bool) or not isinstance(version_raw, int) or version_raw < 1:
        raise PackSdkError(f"views.view_version must be a positive integer; got {version_raw!r}")
    return PackViewRequest(
        view_id=token,
        op_id=op_id.strip(),
        view_version=version_raw,
        is_contribution_point=False,
        is_json_render_runtime_id=False,
        widgets_own_invoke=False,
    )
