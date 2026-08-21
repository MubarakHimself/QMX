"""CT-03 — instrument, venue, and account identity (COMP-QMF-CORE).

The identity nouns every QMF package shares, defined here in ``qmf-core`` and
nowhere else — their *records and lifecycle* are owned by ``qmf-registry`` later,
never by an edge module (CT-03; DEC-0107, DEC-0100).

* :class:`VenueId` — an **operator-minted, opaque, stable** token. It is never
  derived from a mutable broker attribute and never reused: a prop firm
  white-labeling cTrader is its own venue, and a broker migration is a new venue
  plus accounts, old evidence untouched. Stability, non-reuse, and
  non-derivation are operator disciplines the type cannot enforce; construction
  validates only that the token is a non-empty opaque string.
* :class:`Instrument` — the opaque pair ``(venue, venue's own symbol)``. The
  symbol is stored **verbatim and never parsed**: no package splits, prefixes,
  upper-cases, or otherwise interprets its internal structure. Validation is a
  presence check (non-blank), never a structural read.
* :class:`Venue` and :class:`Account` — the first-class market nouns. An
  ``Account`` carries **exactly one** :class:`AccountRole` from the fixed set
  ``live | demo | paper-validation | paper-benched | prop-firm``; one venue may
  hold many accounts, and Books bind to accounts, never to venues.
* :class:`DatedRecord` — a rename, alias, asset-class, or metadata change is a
  **separate dated record pointing at an identity**, append-only: stored history
  never rewrites, and a correction is a new dated record, never an edit.

Every value type follows the one CT-04 construction pattern: an **unchecked
constructor** (the frozen dataclass) for trusted internal use, plus a validating
:meth:`try_create` factory returning ``Result[T] = Ok[T] | TypedRefusal``. A
missing or invalid part returns a typed refusal via CT-04 — never a default
(DEC-0109). Null is prohibited in ``fp1`` identity content: absent metadata is an
omitted key or simply no dated record, never a null field (DEC-0108).

Stdlib only (DEC-0104). Frozen dataclasses and immutable values throughout
(DEC-0101, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qmf.core.refusal import Ok, RefusalCategory, Result, Retryability, TypedRefusal

__all__ = [
    "Account",
    "AccountRole",
    "DatedRecord",
    "Instrument",
    "Venue",
    "VenueId",
]


class AccountRole(StrEnum):
    """The fixed, exhaustive account-role set (CT-03 ``enums.account_role``;
    DEC-0107).

    An account carries exactly one of these. ``PROP_FIRM`` is a reserved seam in
    V1 — no prop firm is modeled — but the value exists so the vocabulary never
    has to change to admit one.
    """

    LIVE = "live"
    DEMO = "demo"
    PAPER_VALIDATION = "paper-validation"
    PAPER_BENCHED = "paper-benched"
    PROP_FIRM = "prop-firm"


# One shared immutable empty payload, reused as the unchecked-constructor default
# for a dated record's content. `content` is always a present mapping, never null.
_EMPTY_CONTENT: Final[Mapping[str, object]] = MappingProxyType({})


def _invalid_refusal(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal every identity factory returns.

    ``retryability`` is ``no`` — a malformed identity part is a caller mistake,
    not a transient condition — and ``context`` always names the offending
    ``field`` and a human-legible ``reason`` (returned, never raised; CT-04).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _clean_token(value: object) -> str | None:
    """Return ``value`` unchanged if it is a non-blank string, else ``None``.

    The blank check is presence-only: the returned token is the caller's string
    **verbatim** — never stripped, cased, or otherwise transformed — so an opaque
    identity token is stored exactly as minted and is never parsed.
    """
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _require_venue_id(value: object) -> VenueId | None:
    """Return ``value`` if it is a well-formed :class:`VenueId`, else ``None``.

    Defense in depth against a :class:`VenueId` built through the unchecked
    constructor with a blank token: a valid venue reference must carry a
    non-blank opaque value.
    """
    if isinstance(value, VenueId) and value.value.strip() != "":
        return value
    return None


def _coerce_role(value: object) -> AccountRole | None:
    """Resolve ``value`` to an :class:`AccountRole` member, or ``None`` if it
    names none."""
    if isinstance(value, AccountRole):
        return value
    if isinstance(value, str):
        try:
            return AccountRole(value)
        except ValueError:
            return None
    return None


def _canonical_date(value: date | str) -> str | None:
    """Return the ISO-8601 date string for ``value``, or ``None`` if invalid.

    A dated record stores its date as a canonical ISO-8601 string — JSON-native
    and ``fp1``-clean — validated here as a real calendar date whether it arrives
    as a :class:`datetime.date` or an ISO string.
    """
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class VenueId:
    """An operator-minted, opaque, stable venue token (CT-03; DEC-0107).

    The value is stored verbatim and never parsed. The unchecked constructor is
    the trusted-internal path; :meth:`try_create` validates that the token is a
    non-empty opaque string. Stability, non-reuse, and non-derivation from a
    mutable broker attribute are operator disciplines this type cannot enforce.
    """

    value: str

    @classmethod
    def try_create(cls, value: object) -> Result[VenueId]:
        """Validate and build a :class:`VenueId`, returning value-or-refusal."""
        token = _clean_token(value)
        if token is None:
            return _invalid_refusal(
                "value",
                "a VenueId is a non-empty opaque token; it is operator-minted, "
                "stable, and never derived from a mutable broker attribute",
                given=repr(value),
            )
        return Ok(cls(token))


@dataclass(frozen=True, slots=True)
class Instrument:
    """Instrument identity: the opaque pair ``(venue, venue's own symbol)``
    (CT-03; DEC-0107).

    The symbol is stored **verbatim and never parsed** — no package interprets
    its internal structure. Both parts are required; a missing or invalid part
    returns a typed refusal via :meth:`try_create`, never a default.
    """

    venue: VenueId
    symbol: str

    @classmethod
    def try_create(cls, venue: object, symbol: object) -> Result[Instrument]:
        """Validate and build an :class:`Instrument`, returning value-or-refusal.

        A missing or invalid ``venue`` or ``symbol`` yields an ``invalid input``
        refusal naming the offending field (CT-04; DEC-0109).
        """
        venue_ref = _require_venue_id(venue)
        if venue_ref is None:
            return _invalid_refusal(
                "venue",
                "an Instrument identity needs a valid VenueId",
                given=repr(venue),
            )
        token = _clean_token(symbol)
        if token is None:
            return _invalid_refusal(
                "symbol",
                "an Instrument needs the venue's own symbol as a non-empty "
                "opaque string; the symbol is never parsed",
                given=repr(symbol),
            )
        return Ok(cls(venue=venue_ref, symbol=token))


@dataclass(frozen=True, slots=True)
class Venue:
    """The Venue noun, defined in ``qmf-core`` (CT-03; DEC-0107, DEC-0100).

    The noun is the identity handle a dated record points at; its record body and
    lifecycle (name, legal entity, asset class, aliases) live in ``qmf-registry``
    as append-only :class:`DatedRecord`\\ s, never inline here.
    """

    venue_id: VenueId

    @classmethod
    def try_create(cls, venue_id: object) -> Result[Venue]:
        """Validate and build a :class:`Venue`, returning value-or-refusal."""
        venue_ref = _require_venue_id(venue_id)
        if venue_ref is None:
            return _invalid_refusal(
                "venue_id",
                "a Venue must name a valid VenueId",
                given=repr(venue_id),
            )
        return Ok(cls(venue_ref))


@dataclass(frozen=True, slots=True)
class Account:
    """The Account noun, defined in ``qmf-core`` (CT-03; DEC-0107, DEC-0100).

    An account is opaque and scoped to its venue, carries **exactly one**
    :class:`AccountRole`, and Books bind to accounts, never to venues. One venue
    may hold many accounts; the record and lifecycle are owned by
    ``qmf-registry``.
    """

    account_id: str
    venue: VenueId
    role: AccountRole

    @classmethod
    def try_create(
        cls,
        account_id: object,
        venue: object,
        role: object,
    ) -> Result[Account]:
        """Validate and build an :class:`Account`, returning value-or-refusal.

        A blank ``account_id``, an invalid ``venue``, or a ``role`` outside the
        fixed set each yields an ``invalid input`` refusal (CT-04; DEC-0109).
        """
        token = _clean_token(account_id)
        if token is None:
            return _invalid_refusal(
                "account_id",
                "an account id is a non-empty opaque token scoped to its venue",
                given=repr(account_id),
            )
        venue_ref = _require_venue_id(venue)
        if venue_ref is None:
            return _invalid_refusal(
                "venue",
                "an account must name a valid VenueId",
                given=repr(venue),
            )
        resolved_role = _coerce_role(role)
        if resolved_role is None:
            return _invalid_refusal(
                "role",
                "an account carries exactly one role from the fixed set",
                given=repr(role),
                allowed=[member.value for member in AccountRole],
            )
        return Ok(cls(account_id=token, venue=venue_ref, role=resolved_role))


@dataclass(frozen=True, slots=True)
class DatedRecord:
    """A dated, append-only fact pointing at an identity (CT-03; DEC-0107).

    A rename, alias, asset-class, or metadata change is recorded as one of these,
    pointing at a :class:`VenueId` or :class:`Instrument`. Stored history never
    rewrites: the value is frozen, and a correction is a **new** dated record,
    never an edit of an old one. ``content`` carries the fact as a key→value
    mapping; null is prohibited (an absent field is an omitted key, never a null
    value; DEC-0108).
    """

    target: VenueId | Instrument
    effective_date: str
    content: Mapping[str, object] = _EMPTY_CONTENT

    def __post_init__(self) -> None:
        # Snapshot content into a read-only mapping so a later mutation of the
        # caller's dict can never reach back into this frozen record.
        object.__setattr__(self, "content", MappingProxyType(dict(self.content)))

    @classmethod
    def try_create(
        cls,
        target: VenueId | Instrument,
        effective_date: date | str,
        content: Mapping[str, object],
    ) -> Result[DatedRecord]:
        """Validate and build a :class:`DatedRecord`, returning value-or-refusal.

        The ``effective_date`` must be a real calendar date; ``content`` must
        carry at least one field, with non-empty string keys and **no null
        value** — null is prohibited in identity content (CT-03; DEC-0108).
        """
        iso = _canonical_date(effective_date)
        if iso is None:
            return _invalid_refusal(
                "effective_date",
                "a dated record needs an effective date (a datetime.date or an "
                "ISO-8601 date string)",
                given=repr(effective_date),
            )
        if len(content) == 0:
            return _invalid_refusal(
                "content",
                "a dated record must carry at least one metadata field",
            )
        for key, value in content.items():
            if key == "":
                return _invalid_refusal(
                    "content",
                    "metadata keys must be non-empty strings",
                )
            if value is None:
                return _invalid_refusal(
                    "content",
                    "null is prohibited in identity content; omit the key instead",
                    key=key,
                )
        return Ok(cls(target=target, effective_date=iso, content=content))
