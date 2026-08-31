"""Core creation policy for Desk and Quant (AD-7; DEC-0306; FR-Q06).

Only ``desk.create`` and ``quant.create`` from an ``operator`` principal mint
identities. Case-folding collisions, reserved desk-prefix tokens, Role-name
collisions, and retired-slug reuse all return ``SlugUnavailable``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from qma.core.ontology.actor_id import ActorId, validate_slug_form
from qma.core.ontology.desks import (
    DESK_DISPLAY_NAMES,
    DESK_PREFIX_TOKENS,
    DESK_SLUG_VALUES,
    DeskSlug,
    RoleName,
    role_slug_collision_key,
)
from qma.core.ontology.records import Desk, Quant, SlugTombstone
from qma.core.refusals.variants import OperatorPrincipalRequired, SlugUnavailable
from qma.core.vocabulary.enums import PrincipalClass
from qmf.core.refusal import Ok, Result, is_ok

__all__ = [
    "CREATION_ACTS",
    "CreationAct",
    "CreationRequest",
    "SlugIndex",
    "authorize_creation",
    "create_desk",
    "create_quant",
    "validate_desk_slug",
    "validate_quant_slug",
]


class CreationAct(StrEnum):
    """Wire acts that may mint Desk / Quant identities (AD-7)."""

    DESK_CREATE = "desk.create"
    QUANT_CREATE = "quant.create"


CREATION_ACTS: Final[frozenset[str]] = frozenset(member.value for member in CreationAct)

_ROLE_COLLISION_KEYS: Final[frozenset[str]] = frozenset(
    role_slug_collision_key(name.value) for name in RoleName
)


@dataclass(frozen=True, slots=True)
class CreationRequest:
    """Operator-principal creation request validated by core policy."""

    act: CreationAct
    principal: PrincipalClass


@dataclass(frozen=True, slots=True)
class SlugIndex:
    """Active and retired slug sets consulted by creation policy.

    Definitions-only stand-in for the daemon definition store.
    """

    active_desk_slugs: frozenset[str] = frozenset()
    active_quant_slugs: frozenset[str] = frozenset()
    retired_slugs: frozenset[str] = frozenset()

    @classmethod
    def from_tombstones(
        cls,
        *,
        active_desks: Iterable[str] = (),
        active_quants: Iterable[str] = (),
        tombstones: Iterable[SlugTombstone] = (),
    ) -> SlugIndex:
        retired = frozenset(stone.slug.casefold() for stone in tombstones)
        return cls(
            active_desk_slugs=frozenset(s.casefold() for s in active_desks),
            active_quant_slugs=frozenset(s.casefold() for s in active_quants),
            retired_slugs=retired,
        )


def authorize_creation(
    act: CreationAct | str,
    principal: PrincipalClass | str,
) -> Result[CreationRequest]:
    """Accept only ``desk.create`` / ``quant.create`` from an operator principal."""
    if isinstance(act, CreationAct):
        resolved_act = act
    elif act in CREATION_ACTS:
        resolved_act = CreationAct(act)
    else:
        return OperatorPrincipalRequired.of(
            command=str(act),
            principal_class=str(principal),
        )

    if isinstance(principal, PrincipalClass):
        resolved_principal = principal
    else:
        try:
            resolved_principal = PrincipalClass(principal)
        except ValueError:
            return OperatorPrincipalRequired.of(
                command=resolved_act.value,
                principal_class=str(principal),
            )

    if resolved_principal is not PrincipalClass.OPERATOR:
        return OperatorPrincipalRequired.of(
            command=resolved_act.value,
            principal_class=resolved_principal.value,
        )
    return Ok(CreationRequest(act=resolved_act, principal=resolved_principal))


def _quant_slug_unavailable(candidate: str, index: SlugIndex) -> bool:
    """True when a quant_slug case-folds onto a reserved or colliding token."""
    folded = candidate.casefold()
    if folded in index.active_desk_slugs:
        return True
    if folded in index.active_quant_slugs:
        return True
    if folded in index.retired_slugs:
        return True
    if folded in DESK_PREFIX_TOKENS:
        return True
    return role_slug_collision_key(candidate) in _ROLE_COLLISION_KEYS


def validate_desk_slug(slug: object, index: SlugIndex) -> Result[DeskSlug]:
    """Validate a desk slug against the five fixed values and collision policy."""
    form = validate_slug_form(slug, slug_kind="desk_slug")
    if not is_ok(form):
        return form
    token = form.value

    if token not in DESK_SLUG_VALUES:
        return SlugUnavailable.of(slug=token, slug_kind="desk_slug")

    folded = token.casefold()
    if folded in index.active_desk_slugs or folded in index.retired_slugs:
        return SlugUnavailable.of(slug=token, slug_kind="desk_slug")
    return Ok(DeskSlug(token))


def validate_quant_slug(slug: object, index: SlugIndex) -> Result[str]:
    """Validate a quant slug; refuse reserved, Role, active, and retired collisions."""
    form = validate_slug_form(slug, slug_kind="quant_slug")
    if not is_ok(form):
        return form
    token = form.value
    if _quant_slug_unavailable(token, index):
        return SlugUnavailable.of(slug=token, slug_kind="quant_slug")
    return Ok(token)


def create_desk(
    *,
    desk_slug: object,
    principal: PrincipalClass | str,
    index: SlugIndex,
) -> Result[Desk]:
    """Mint a Desk via ``desk.create`` from an operator principal."""
    auth = authorize_creation(CreationAct.DESK_CREATE, principal)
    if not is_ok(auth):
        return auth
    slug = validate_desk_slug(desk_slug, index)
    if not is_ok(slug):
        return slug
    desk = slug.value
    return Ok(
        Desk(
            slug=desk,
            display_name=DESK_DISPLAY_NAMES[desk],
            retired=False,
        )
    )


def create_quant(
    *,
    desk_slug: DeskSlug | str,
    quant_slug: object,
    role: RoleName | str,
    name: str,
    principal: PrincipalClass | str,
    index: SlugIndex,
    lead: bool = False,
) -> Result[Quant]:
    """Mint a Quant via ``quant.create`` from an operator principal."""
    auth = authorize_creation(CreationAct.QUANT_CREATE, principal)
    if not is_ok(auth):
        return auth

    if isinstance(desk_slug, DeskSlug):
        desk = desk_slug
    else:
        form = validate_slug_form(desk_slug, slug_kind="desk_slug")
        if not is_ok(form):
            return form
        if form.value not in DESK_SLUG_VALUES:
            return SlugUnavailable.of(slug=form.value, slug_kind="desk_slug")
        desk = DeskSlug(form.value)

    if desk.value.casefold() not in index.active_desk_slugs:
        # Desk must already exist (bootstrapped / desk.create) before quant.create.
        return SlugUnavailable.of(slug=desk.value, slug_kind="desk_slug")

    qslug = validate_quant_slug(quant_slug, index)
    if not is_ok(qslug):
        return qslug

    if isinstance(role, RoleName):
        resolved_role = role
    else:
        try:
            resolved_role = RoleName(role)
        except ValueError:
            return SlugUnavailable.of(slug=str(role), slug_kind="role_name")

    actor = ActorId.mint(desk, qslug.value)
    if not is_ok(actor):
        return actor

    return Ok(
        Quant(
            actor_id=actor.value,
            desk=desk,
            quant_slug=qslug.value,
            role=resolved_role,
            name=name,
            lead=lead,
            retired=False,
        )
    )
