"""Pack ``contributes`` entries — ``{point, local_id}`` objects (AD-2; RC-13).

Workflows pack discovery expands these to ContributionHit at enable. Opaque
strings such as ``"capability:qmb.analysis.project"`` are refused. Qualification
defaults to ``package_id + ":" + local_id`` (or a pack-declared ``qualified_id``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

from qma.core.ports.cardinality import (
    PortError,
    qualified_contribution_id,
    validate_contribution_point,
    validate_multi_contribution_key,
)

__all__ = [
    "DEFAULT_QUALIFIED_ID_RULE",
    "PackContribute",
    "PackContributeError",
    "parse_pack_contributes",
    "qualify_pack_contribute",
]


class PackContributeError(ValueError):
    """Raised when pack ``contributes`` violate AD-2 / RC-13 object shape."""


DEFAULT_QUALIFIED_ID_RULE: Final[str] = "package_id:local_id"


@dataclass(frozen=True, slots=True)
class PackContribute:
    """One pack ``contributes`` entry. Never an opaque string."""

    point: str
    local_id: str
    qualified_id: str | None = None


def qualify_pack_contribute(
    package_id: str,
    contrib: PackContribute,
    *,
    rule: str | None = None,
) -> str:
    """Qualify a contribute to ``qualified_id``.

    Default is ``package_id + ":" + local_id``. A pack-declared ``qualified_id``
    on the entry wins. ``rule`` must be the default or omitted.
    """
    if contrib.qualified_id is not None:
        return contrib.qualified_id
    chosen = DEFAULT_QUALIFIED_ID_RULE if rule is None else rule
    if chosen != DEFAULT_QUALIFIED_ID_RULE:
        raise PackContributeError(
            f"unknown qualified_id rule {chosen!r}; v1 default is "
            f"{DEFAULT_QUALIFIED_ID_RULE!r} (FR-WF-09; RC-13)"
        )
    try:
        return qualified_contribution_id(package_id, contrib.local_id)
    except PortError as exc:
        raise PackContributeError(str(exc)) from exc


def parse_pack_contributes(
    raw: object,
    *,
    package_id: str,
    rule: str | None = None,
) -> tuple[PackContribute, ...]:
    """Parse ``contributes`` as ``{point, local_id}`` objects; refuse strings."""
    if raw is None:
        raise PackContributeError(
            "contributes must be an empty collection when undeclared, never null (CT-42; FR-WF-09)"
        )
    if isinstance(raw, (str, bytes)):
        raise PackContributeError(
            "contributes entries must be {point, local_id} objects, never an "
            "opaque string such as 'capability:qmb.analysis.project' "
            "(AD-2; RC-13; FR-WF-09)"
        )
    if not isinstance(raw, Sequence):
        raise PackContributeError("contributes must be a sequence of {point, local_id} objects")

    items = cast(Sequence[object], raw)
    parsed: list[PackContribute] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        contrib = _parse_one(item, package_id=package_id)
        qualified = qualify_pack_contribute(package_id, contrib, rule=rule)
        key = (contrib.point, qualified)
        if key in seen:
            raise PackContributeError(
                f"colliding (point, qualified_id) {key!r} in contributes (FR-WF-09; SCN-0022)"
            )
        seen.add(key)
        parsed.append(contrib)
    return tuple(parsed)


def _parse_one(item: object, *, package_id: str) -> PackContribute:
    if isinstance(item, (str, bytes)):
        raise PackContributeError(
            "contributes entries must be {point, local_id} objects, never an "
            f"opaque string such as {item!r} (AD-2; RC-13; FR-WF-09)"
        )
    if not isinstance(item, Mapping):
        raise PackContributeError(
            "contributes entries must be {point, local_id} objects, never an "
            f"opaque string; got {type(item).__name__} (AD-2; RC-13; FR-WF-09)"
        )
    body = {str(key): value for key, value in cast(Mapping[object, object], item).items()}
    point_raw = body.get("point")
    local_raw = body.get("local_id")
    if isinstance(point_raw, str) and ":" in point_raw and local_raw is None:
        raise PackContributeError(
            "contributes entries must be {point, local_id} objects, never an "
            f"opaque string such as {point_raw!r} (AD-2; RC-13; FR-WF-09)"
        )
    try:
        point = validate_contribution_point(point_raw)
    except PortError as exc:
        raise PackContributeError(str(exc)) from exc
    if not isinstance(local_raw, str) or local_raw.strip() == "":
        raise PackContributeError(
            f"contributes local_id is a non-empty string; got {local_raw!r} (FR-WF-09)"
        )
    local_id = local_raw.strip()
    if ":" in local_id:
        raise PackContributeError(f"local_id must not contain ':'; got {local_id!r}")

    declared = body.get("qualified_id")
    qualified_id: str | None = None
    if declared is not None:
        if not isinstance(declared, str) or declared.strip() == "":
            raise PackContributeError(
                f"pack-declared qualified_id is a non-empty string; got {declared!r}"
            )
        token = declared.strip()
        if token.casefold().startswith("fp1:"):
            raise PackContributeError("contributes qualified_id is never fp1 (DEC-0415; FR-WF-03)")
        try:
            validate_multi_contribution_key(token)
        except PortError as exc:
            raise PackContributeError(str(exc)) from exc
        qualified_id = token

    contrib = PackContribute(point=point, local_id=local_id, qualified_id=qualified_id)
    qualify_pack_contribute(package_id, contrib)
    return contrib
