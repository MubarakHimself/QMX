"""Opaque ``ActorId`` address grammar (AD-7; DEC-0306; FR-Q06).

Grammar: ``quant:<desk_slug>/<quant_slug>`` over the five fixed desk slugs.
The value is opaque to every consumer — desk membership is a field on the Quant
record, never parsed from either slug substring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from qma.core.ontology.desks import DESK_SLUG_VALUES, DeskSlug
from qma.core.refusals.variants import SlugUnavailable
from qmf.core.refusal import Ok, Result, is_ok

__all__ = [
    "ACTOR_ID_PREFIX",
    "SLUG_MAX_LEN",
    "SLUG_MIN_LEN",
    "SLUG_PATTERN",
    "ActorId",
    "is_valid_slug_form",
    "validate_slug_form",
]

ACTOR_ID_PREFIX: Final[str] = "quant:"
SLUG_MIN_LEN: Final[int] = 2
SLUG_MAX_LEN: Final[int] = 32

# Lower-case only; length enforced separately so error messages stay precise.
SLUG_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[a-z0-9](?:[a-z0-9_-]{0,30}[a-z0-9])?$"
)

_ACTOR_ID_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^quant:([a-z0-9](?:[a-z0-9_-]{0,30}[a-z0-9])?)/"
    r"([a-z0-9](?:[a-z0-9_-]{0,30}[a-z0-9])?)$"
)


def is_valid_slug_form(slug: str) -> bool:
    """True when ``slug`` is already lower-case and 2..32 characters."""
    return (
        isinstance(slug, str)
        and SLUG_MIN_LEN <= len(slug) <= SLUG_MAX_LEN
        and SLUG_PATTERN.fullmatch(slug) is not None
    )


def validate_slug_form(slug: object, *, slug_kind: str) -> Result[str]:
    """Return a well-formed lower-case slug or ``SlugUnavailable``."""
    if not isinstance(slug, str) or not slug:
        return SlugUnavailable.of(slug=repr(slug), slug_kind=slug_kind)
    if slug != slug.casefold() or not is_valid_slug_form(slug):
        return SlugUnavailable.of(slug=slug, slug_kind=slug_kind)
    return Ok(slug)


@dataclass(frozen=True, slots=True)
class ActorId:
    """Opaque Quant address ``quant:<desk_slug>/<quant_slug>`` (AD-7).

    Stores a single opaque ``value``. No desk or Quant slug accessors — consumers
    read desk membership from the Quant record (FR-Q06).
    """

    value: str

    def __str__(self) -> str:
        return self.value

    def serialize(self) -> str:
        """Wire / storage form — identical to the opaque value."""
        return self.value

    @classmethod
    def mint(cls, desk_slug: DeskSlug | str, quant_slug: str) -> Result[ActorId]:
        """Mint an ``ActorId`` during ``desk.create`` / ``quant.create``.

        Validates grammar only. Collision policy lives in ``creation``.
        """
        if isinstance(desk_slug, DeskSlug):
            desk = desk_slug.value
        else:
            desk_result = validate_slug_form(desk_slug, slug_kind="desk_slug")
            if not is_ok(desk_result):
                return desk_result
            desk = desk_result.value
            if desk not in DESK_SLUG_VALUES:
                return SlugUnavailable.of(slug=desk, slug_kind="desk_slug")

        quant_result = validate_slug_form(quant_slug, slug_kind="quant_slug")
        if not is_ok(quant_result):
            return quant_result
        return Ok(cls(value=f"{ACTOR_ID_PREFIX}{desk}/{quant_result.value}"))

    @classmethod
    def try_create(cls, value: object) -> Result[ActorId]:
        """Validate an opaque serialized ``ActorId`` without exposing slug parts."""
        if not isinstance(value, str) or not value:
            return SlugUnavailable.of(slug=repr(value), slug_kind="actor_id")
        match = _ACTOR_ID_PATTERN.fullmatch(value)
        if match is None:
            return SlugUnavailable.of(slug=value, slug_kind="actor_id")
        desk = match.group(1)
        quant = match.group(2)
        if desk not in DESK_SLUG_VALUES:
            return SlugUnavailable.of(slug=desk, slug_kind="desk_slug")
        if not is_valid_slug_form(desk) or not is_valid_slug_form(quant):
            return SlugUnavailable.of(slug=value, slug_kind="actor_id")
        return Ok(cls(value=value))
