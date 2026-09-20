"""AD-17 ``view:*`` presentation DTO — wire only (Stories 53.4 / 55.4; GAP-0081).

Pack ``view:*`` is a wire-owned presentation DTO (CONTRACTS §14). It is not a
plugin contribution point and not a ContributionHit until a named GAP-0081
``ui_view`` increment (AD-17; FR-WF-12). A tab/window/view is not a
``product_session`` and does not own grants or occupancy (Story 55.4; AD-8).
JSON Render / MCP Apps are presentation adapters — not identity, not
persistence, not a runtime, and not authority. Mount/dispose must not start
or kill durable backend work. Occupancy none. GAP-0081 chrome is not filled.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal, cast

from qma.core.ports.extensibility import (
    GAP_0081_STATUS,
    UI_VIEW_CONTRIBUTION_POINT,
    ui_view_contribution_point_minted,
)
from qma.wire.contribution_listing import (
    CONTRIBUTION_LISTING_OCCUPANCY,
    refuse_hit_as_grant,
)
from qma.wire.federated_discovery import refuse_view_contribution_hit
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)

__all__ = [
    "VIEW_FILLS_GAP_0081_CHROME",
    "VIEW_IS_CONTRIBUTION_HIT",
    "VIEW_IS_PLUGIN_CONTRIBUTION_POINT",
    "VIEW_IS_PRODUCT_SESSION",
    "VIEW_OWNS_GRANTS",
    "VIEW_OWNS_OCCUPANCY",
    "VIEW_PRESENTATION_CONTRACT",
    "VIEW_PRESENTATION_DTO_OWNER",
    "VIEW_PRESENTATION_GAP",
    "VIEW_PRESENTATION_MOUNTS",
    "VIEW_PRESENTATION_NEW_CT_MINTED",
    "VIEW_PRESENTATION_OCCUPANCY",
    "VIEW_PRESENTATION_REFUSED_CT",
    "VIEW_PRESENTATION_SCHEMA",
    "VIEW_PRESENTATION_SCHEMA_FILE",
    "VIEW_PRESENTATION_SCHEMA_NAME",
    "VIEW_UI_CONTRIBUTION_POINT_MINTED",
    "ViewPresentation",
    "parse_view_presentation",
    "refuse_view_as_contribution_hit",
    "refuse_view_as_product_session",
    "refuse_view_durable_work",
    "refuse_view_owns_grants",
    "validate_view_presentation",
]


VIEW_PRESENTATION_DTO_OWNER: Final[str] = "COMP-QMA-WIRE"
VIEW_PRESENTATION_CONTRACT: Final[str] = "CT-40"
VIEW_PRESENTATION_NEW_CT_MINTED: Final[bool] = False
VIEW_PRESENTATION_REFUSED_CT: Final[str] = "CT-52"
VIEW_PRESENTATION_SCHEMA: Final[str] = "qma.wire.view_presentation.v1"
VIEW_PRESENTATION_SCHEMA_NAME: Final[str] = "view_presentation"
VIEW_PRESENTATION_SCHEMA_FILE: Final[str] = "view_presentation.v1.schema.json"
VIEW_PRESENTATION_GAP: Final[str] = "GAP-0081"
VIEW_PRESENTATION_OCCUPANCY: Final[str] = CONTRIBUTION_LISTING_OCCUPANCY
VIEW_IS_CONTRIBUTION_HIT: Final[bool] = False
VIEW_IS_PLUGIN_CONTRIBUTION_POINT: Final[bool] = False
VIEW_IS_PRODUCT_SESSION: Final[bool] = False
VIEW_OWNS_GRANTS: Final[bool] = False
VIEW_OWNS_OCCUPANCY: Final[bool] = False
VIEW_FILLS_GAP_0081_CHROME: Final[bool] = False
VIEW_UI_CONTRIBUTION_POINT_MINTED: Final[bool] = ui_view_contribution_point_minted()
VIEW_PRESENTATION_MOUNTS: Final[frozenset[str]] = frozenset({"mounted", "unmounted"})
_GRANT_IDENTITY_KEYS: Final[frozenset[str]] = frozenset({"grant_id", "granted_ops"})
_SESSION_IDENTITY_KEYS: Final[frozenset[str]] = frozenset({"product_session", "product_session_id"})
_CHROME_IDENTITY_KEYS: Final[frozenset[str]] = frozenset({"tab_id", "window_id", "pane_id"})

_FORBIDDEN_VIEW_KEYS: Final[frozenset[str]] = frozenset(
    {
        "hit_class",
        "plugin_id",
        "point",
        "qualified_id",
        "package_id",
        "package_version",
        "availability_revision",
        "availability",
        "fp1",
        "kind",
        "artifact_ref",
        "research_ref",
        "grant_id",
        "granted_ops",
        "product_session",
        "product_session_id",
        "authorizes_invoke",
        "tab_id",
        "window_id",
        "pane_id",
    }
)


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


def refuse_view_as_contribution_hit(**extra: object) -> TypedRefusal:
    """``view:*`` is AD-17 wire DTO only — not a ContributionHit (GAP-0081)."""
    extra.setdefault("is_contribution_hit", False)
    extra.setdefault("is_plugin_contribution_point", False)
    extra.setdefault("is_product_session", False)
    extra.setdefault("gap_status", GAP_0081_STATUS)
    extra.setdefault("ui_contribution_minted", VIEW_UI_CONTRIBUTION_POINT_MINTED)
    extra.setdefault("plugin_contribution_point", UI_VIEW_CONTRIBUTION_POINT)
    extra.setdefault("fills_gap_0081_chrome", False)
    return refuse_view_contribution_hit(**extra)


def refuse_view_as_product_session(**extra: object) -> TypedRefusal:
    """A tab/window/view is not a product_session (Story 55.4; AD-8; AD-17)."""
    field = str(extra.pop("field", "view"))
    return _policy(
        field,
        "a tab/window/view is not a product_session and does not own grants "
        "or occupancy (AD-8; AD-17; Story 55.4)",
        is_product_session=False,
        occupancy=VIEW_PRESENTATION_OCCUPANCY,
        gap="GAP-0081",
        fills_gap_0081_chrome=False,
        **extra,
    )


def refuse_view_owns_grants(**extra: object) -> TypedRefusal:
    """view:* does not own grants (AD-8; SCN-0018 Branch B; Story 55.4)."""
    field = str(extra.pop("field", "grant_id"))
    return _policy(
        field,
        "view:* does not own grants; product_session.granted_ops and GrantRecord "
        "do (AD-8; SCN-0018 Branch B; Story 55.4)",
        chrome_owns_grants=False,
        hit_is_grant=False,
        authorizes_invoke=False,
        branch="B",
        scn="SCN-0018",
        occupancy=VIEW_PRESENTATION_OCCUPANCY,
        **extra,
    )


def refuse_view_durable_work(**extra: object) -> TypedRefusal:
    """Mount/dispose must not start or kill durable backend work (AD-17)."""
    field = str(extra.pop("field", "occupancy"))
    return _policy(
        field,
        "view:* mount/dispose must not start or kill durable backend work; "
        "occupancy stays none (AD-17; FR-WF-05; FR-WF-12)",
        occupancy=VIEW_PRESENTATION_OCCUPANCY,
        starts_durable_work=False,
        kills_durable_work=False,
        **extra,
    )


def _parse_nonempty_str(value: object, field: str) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(
            field,
            f"ViewPresentation.{field} is a non-empty string (AD-17; CONTRACTS §14)",
            given=repr(value),
        )
    return Ok(value.strip())


def _parse_view_id(value: object) -> Result[str]:
    parsed = _parse_nonempty_str(value, "view_id")
    if is_refusal(parsed):
        return parsed
    token = parsed.value
    folded = token.casefold()
    if folded == UI_VIEW_CONTRIBUTION_POINT or folded.replace("-", "_") == "ui_view":
        return refuse_view_as_contribution_hit(field="view_id", given=token)
    if not folded.startswith("view:"):
        return refuse_view_as_contribution_hit(field="view_id", given=token)
    return Ok(token)


def _parse_view_version(value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return _invalid(
            "view_version",
            "ViewPresentation.view_version is a positive integer (AD-17)",
            given=repr(value),
        )
    if value < 1:
        return _invalid(
            "view_version",
            "ViewPresentation.view_version is a positive integer (AD-17)",
            given=value,
        )
    return Ok(value)


def _parse_mount(value: object) -> Result[str]:
    parsed = _parse_nonempty_str(value, "mount")
    if is_refusal(parsed):
        return parsed
    token = parsed.value
    if token not in VIEW_PRESENTATION_MOUNTS:
        return _policy(
            "mount",
            "ViewPresentation.mount is mounted | unmounted (AD-17; CONTRACTS §14)",
            given=token,
            legal=sorted(VIEW_PRESENTATION_MOUNTS),
        )
    return Ok(token)


def _parse_snapshot_cursor(value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return _invalid(
            "snapshot_cursor",
            "ViewPresentation.snapshot_cursor is a non-negative integer (AD-17)",
            given=repr(value),
        )
    if value < 0:
        return _invalid(
            "snapshot_cursor",
            "ViewPresentation.snapshot_cursor is a non-negative integer (AD-17)",
            given=value,
        )
    return Ok(value)


def _parse_binding(value: object) -> Result[Mapping[str, object]]:
    if not isinstance(value, Mapping):
        return _invalid(
            "parameter_binding",
            "ViewPresentation.parameter_binding is a mapping (AD-17; CONTRACTS §14)",
            given=repr(value),
        )
    body = cast("Mapping[str, object]", value)
    schema = body.get("schema")
    if not isinstance(schema, str) or schema.strip() == "":
        return _invalid(
            "parameter_binding.schema",
            "parameter_binding.schema names an existing AD-3 input_schema (AD-17)",
            given=repr(schema),
        )
    raw_values = body.get("values", {})
    if raw_values is None:
        raw_values = {}
    if not isinstance(raw_values, Mapping):
        return _invalid(
            "parameter_binding.values",
            "parameter_binding.values is a mapping (AD-17)",
            given=repr(raw_values),
        )
    return Ok(
        MappingProxyType(
            {
                "schema": schema.strip(),
                "values": dict(cast("Mapping[str, object]", raw_values)),
            }
        )
    )


@dataclass(frozen=True, slots=True)
class ViewPresentation:
    """AD-17 ``view:*`` wire DTO — not a ContributionHit, not a plugin point."""

    view_id: str
    view_version: int
    op_id: str
    mount: str
    parameter_binding: Mapping[str, object]
    snapshot_cursor: int
    stale: bool
    is_contribution_hit: Literal[False] = False
    is_plugin_contribution_point: Literal[False] = False
    occupancy: str = VIEW_PRESENTATION_OCCUPANCY
    starts_durable_work: Literal[False] = False
    kills_durable_work: Literal[False] = False

    @classmethod
    def try_create(
        cls,
        *,
        view_id: object,
        view_version: object,
        op_id: object,
        mount: object,
        parameter_binding: object,
        snapshot_cursor: object,
        stale: object,
        occupancy: object = VIEW_PRESENTATION_OCCUPANCY,
        starts_durable_work: object = False,
        kills_durable_work: object = False,
        authorizes_invoke: object = False,
        **extra: object,
    ) -> Result[ViewPresentation]:
        """Validate a view:* DTO. Refuses contribution-hit / plugin-point identity."""
        stolen = tuple(sorted(name for name in extra if name in _FORBIDDEN_VIEW_KEYS))
        if stolen:
            names = frozenset(stolen)
            if "authorizes_invoke" in names or extra.get("authorizes_invoke") is True:
                return refuse_hit_as_grant(fields=stolen, given=stolen)
            if names & _GRANT_IDENTITY_KEYS:
                return refuse_view_owns_grants(fields=stolen, given=stolen)
            if names & (_SESSION_IDENTITY_KEYS | _CHROME_IDENTITY_KEYS):
                return refuse_view_as_product_session(fields=stolen, given=stolen)
            return refuse_view_as_contribution_hit(fields=stolen, given=stolen)
        if authorizes_invoke is True:
            return refuse_hit_as_grant(field="authorizes_invoke", given=True)
        if starts_durable_work is True or kills_durable_work is True:
            return refuse_view_durable_work(
                given={"starts": starts_durable_work, "kills": kills_durable_work}
            )
        if occupancy != VIEW_PRESENTATION_OCCUPANCY:
            return refuse_view_durable_work(given=repr(occupancy))
        if not isinstance(stale, bool):
            return _invalid("stale", "ViewPresentation.stale is a boolean", given=repr(stale))
        vid = _parse_view_id(view_id)
        if is_refusal(vid):
            return vid
        version = _parse_view_version(view_version)
        if is_refusal(version):
            return version
        op = _parse_nonempty_str(op_id, "op_id")
        if is_refusal(op):
            return op
        mounted = _parse_mount(mount)
        if is_refusal(mounted):
            return mounted
        binding = _parse_binding(parameter_binding)
        if is_refusal(binding):
            return binding
        cursor = _parse_snapshot_cursor(snapshot_cursor)
        if is_refusal(cursor):
            return cursor
        return Ok(
            cls(
                view_id=vid.value,
                view_version=version.value,
                op_id=op.value,
                mount=mounted.value,
                parameter_binding=binding.value,
                snapshot_cursor=cursor.value,
                stale=stale,
                is_contribution_hit=False,
                is_plugin_contribution_point=False,
                occupancy=VIEW_PRESENTATION_OCCUPANCY,
                starts_durable_work=False,
                kills_durable_work=False,
            )
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "is_contribution_hit": False,
                "is_plugin_contribution_point": False,
                "mount": self.mount,
                "occupancy": VIEW_PRESENTATION_OCCUPANCY,
                "op_id": self.op_id,
                "parameter_binding": dict(self.parameter_binding),
                "snapshot_cursor": self.snapshot_cursor,
                "stale": self.stale,
                "view_id": self.view_id,
                "view_version": self.view_version,
            }
        )


def parse_view_presentation(value: object) -> Result[ViewPresentation]:
    """Parse an AD-17 view:* mapping. Contribution identity keys refuse."""
    if isinstance(value, ViewPresentation):
        return ViewPresentation.try_create(
            view_id=value.view_id,
            view_version=value.view_version,
            op_id=value.op_id,
            mount=value.mount,
            parameter_binding=value.parameter_binding,
            snapshot_cursor=value.snapshot_cursor,
            stale=value.stale,
            occupancy=value.occupancy,
        )
    if not isinstance(value, Mapping):
        return _invalid(
            "view",
            "ViewPresentation is a mapping of AD-17 view:* fields (CT-40; GAP-0081)",
            given=repr(value),
        )
    body = cast("Mapping[str, object]", value)
    named = {
        "authorizes_invoke",
        "starts_durable_work",
        "kills_durable_work",
        "occupancy",
    }
    stolen = sorted(key for key in _FORBIDDEN_VIEW_KEYS if key in body and key not in named)
    extras = {key: body[key] for key in stolen} if stolen else {}
    return ViewPresentation.try_create(
        view_id=body.get("view_id"),
        view_version=body.get("view_version"),
        op_id=body.get("op_id"),
        mount=body.get("mount"),
        parameter_binding=body.get("parameter_binding"),
        snapshot_cursor=body.get("snapshot_cursor"),
        stale=body.get("stale"),
        occupancy=body.get("occupancy", VIEW_PRESENTATION_OCCUPANCY),
        starts_durable_work=body.get("starts_durable_work", False),
        kills_durable_work=body.get("kills_durable_work", False),
        authorizes_invoke=body.get("authorizes_invoke", False),
        **extras,
    )


def validate_view_presentation(value: object) -> Result[ViewPresentation]:
    """Schema-then-DTO validation for the AD-17 view:* overlay."""
    from qma.wire.schemas import validate_instance  # noqa: PLC0415

    if isinstance(value, ViewPresentation):
        payload = dict(value.to_payload())
    elif isinstance(value, Mapping):
        payload = dict(cast("Mapping[str, object]", value))
    else:
        return parse_view_presentation(value)
    checked = validate_instance(payload, VIEW_PRESENTATION_SCHEMA_NAME)
    if is_refusal(checked):
        return checked
    return parse_view_presentation(checked.value)
