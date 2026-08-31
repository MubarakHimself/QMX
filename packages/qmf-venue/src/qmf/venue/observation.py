"""The per-(VenueId, account) venue-observation profile (COMP-QMF-VENUE; CT-18).

The capability surface is two artifacts (CT-18; DEC-0138): a static capability
declaration, and this — the **venue-observation profile**, produced post-connect by
the first-connection verification suite, holding every measured fact and its verdict
as *occurrence/provenance only*. This module owns that second artifact and the
verify-or-refuse consumption discipline that reads it. It imports only ``qmf-core``
(default-deny, L30/DEC-0120), and nothing imports ``qmf-venue``.

Three pieces:

* :class:`ProbeCheck` / :class:`ProbeVerdict` / :class:`VenueEvidenceClass` — the
  named first-connection checks, their three-valued verdicts, and the evidence class
  each check governs. A check is ``verified`` (its fact is available),
  ``unverified`` (unmeasured/unassertable — the class stays unavailable), or
  ``refused`` (the check ran and failed — the class is refused). Neither verdict
  ever defaults a value (AR-45; DEC-0135, DEC-0138).
* :class:`MeasuredFact` — one recorded (check, verdict, evidence-class) row plus its
  measured value (present, possibly empty, never null), the receive instant (recording
  a receive time is mandatory — the cTrader Open API exposes no server clock, DEC-0135),
  the session-epoch id (distinct from the boot epoch, DEC-0137), and the *reference id*
  of the credential the measurement ran under (a reference, never a value — CT-21,
  DEC-0136). A fact is occurrence/provenance only and deliberately exposes no
  ``fp1_identity``: it never enters a downstream fingerprint (CT-18; DEC-0138).
* :class:`VenueObservationProfile` — the append-only, per-(VenueId, account) record
  with ``supersedes`` edges. :meth:`~VenueObservationProfile.require_evidence` is the
  verify-or-refuse gate a consumer calls: a measured-but-unverified capability is a
  ``policy rejection`` and an unmeasured/unverified one is an ``unavailable dependency``
  refusal, so an unmeasured daily boundary leaves venue daily bars ungoverned rather
  than silently governed (AR-45, FM-6; DEC-0138).

Stdlib + qmf-core only. Frozen, immutable values throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, TypeVar, cast

from qmf.core import (
    Account,
    CalendarIdentity,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    VenueId,
)

__all__ = [
    "FIRST_CONNECTION_CHECKS",
    "PROBE_V1_CHECKS",
    "REQUIRED_CONNECTION_CHECKS",
    "MeasuredFact",
    "ProbeCheck",
    "ProbeVerdict",
    "VenueEvidenceClass",
    "VenueObservationProfile",
]

_EnumT = TypeVar("_EnumT", bound=StrEnum)


class ProbeCheck(StrEnum):
    """The named first-connection verify-or-refuse checks (CT-18; DEC-0135, DEC-0138).

    Each is a member of the verification suite the probe runs once per connection;
    the set is addable, never redefined. Story 8.1 minted the five sensing/decode
    checks; the trading-node first-connection suite (TN-10) adds amend-atomicity;
    Story 24.2 adds the remaining measured CT-18 connection facts (position model,
    pacing/throttle scope, protective-stop forms).
    """

    SPOT_TIMESTAMP_UNIT = "spot-timestamp-unit"
    DAILY_BOUNDARY = "daily-boundary"
    BAR_BASIS = "bar-basis"
    PIP_FORMULA = "pip-formula"
    MONEY_EXPONENT = "money-exponent"
    AMEND_ATOMICITY = "amend-atomicity"
    POSITION_MODEL = "position-model"
    PACING_SCOPE = "pacing-scope"
    PROTECTIVE_STOP_FORMS = "protective-stop-forms"


class ProbeVerdict(StrEnum):
    """The three-valued verdict of a verify-or-refuse check (AR-45; DEC-0135).

    ``VERIFIED`` — the check passed and its measured fact is available.
    ``UNVERIFIED`` — the fact could not be measured or asserted (an absent money
    exponent, an unassertable spot-timestamp unit, an unmeasured daily boundary); the
    governed evidence class stays *unavailable* and no value is defaulted.
    ``REFUSED`` — the check ran and failed (a bar-basis mismatch, a failed pip
    formula); the governed evidence class is *refused*.
    """

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    REFUSED = "refused"


class VenueEvidenceClass(StrEnum):
    """The class of venue evidence a passing check makes available (CT-18; DEC-0138).

    An unverified spot-timestamp unit refuses spot evidence; an unmeasured daily
    boundary leaves venue daily bars ungoverned; a failed bar-basis reconciliation
    refuses bar evidence; a failed pip-formula validation refuses metadata-derived
    parameters; an absent money exponent refuses that message's money decode.
    Amend-atomicity, position-model, pacing-scope, and protective-stop-forms gate
    their own dependent command/decode surfaces under the same verify-or-refuse law.
    """

    SPOT = "spot"
    VENUE_DAILY_BARS = "venue-daily-bars"
    BAR = "bar"
    METADATA_DERIVED_PARAMETERS = "metadata-derived-parameters"
    MONEY_DECODE = "money-decode"
    AMEND_ATOMICITY = "amend-atomicity"
    POSITION_MODEL = "position-model"
    PACING_SCOPE = "pacing-scope"
    PROTECTIVE_STOP_FORMS = "protective-stop-forms"


# Story 8.1's original five sensing/decode checks — still what CapabilityProbe records.
PROBE_V1_CHECKS: Final[tuple[ProbeCheck, ...]] = (
    ProbeCheck.SPOT_TIMESTAMP_UNIT,
    ProbeCheck.DAILY_BOUNDARY,
    ProbeCheck.BAR_BASIS,
    ProbeCheck.PIP_FORMULA,
    ProbeCheck.MONEY_EXPONENT,
)

# TN-10 six first-connection checks (adds amend atomicity).
FIRST_CONNECTION_CHECKS: Final[tuple[ProbeCheck, ...]] = (
    *PROBE_V1_CHECKS,
    ProbeCheck.AMEND_ATOMICITY,
)

# Story 24.2 required live-venue-fact checks at connection time.
REQUIRED_CONNECTION_CHECKS: Final[tuple[ProbeCheck, ...]] = (
    *FIRST_CONNECTION_CHECKS,
    ProbeCheck.POSITION_MODEL,
    ProbeCheck.PACING_SCOPE,
    ProbeCheck.PROTECTIVE_STOP_FORMS,
)

# The fixed 1:1 mapping from a check to the evidence class it governs (DEC-0138). A
# class-level constant, not a per-instance value; a read-only mapping so it cannot be
# mutated through the reference callers share.
_CHECK_EVIDENCE: Final[Mapping[ProbeCheck, VenueEvidenceClass]] = MappingProxyType(
    {
        ProbeCheck.SPOT_TIMESTAMP_UNIT: VenueEvidenceClass.SPOT,
        ProbeCheck.DAILY_BOUNDARY: VenueEvidenceClass.VENUE_DAILY_BARS,
        ProbeCheck.BAR_BASIS: VenueEvidenceClass.BAR,
        ProbeCheck.PIP_FORMULA: VenueEvidenceClass.METADATA_DERIVED_PARAMETERS,
        ProbeCheck.MONEY_EXPONENT: VenueEvidenceClass.MONEY_DECODE,
        ProbeCheck.AMEND_ATOMICITY: VenueEvidenceClass.AMEND_ATOMICITY,
        ProbeCheck.POSITION_MODEL: VenueEvidenceClass.POSITION_MODEL,
        ProbeCheck.PACING_SCOPE: VenueEvidenceClass.PACING_SCOPE,
        ProbeCheck.PROTECTIVE_STOP_FORMS: VenueEvidenceClass.PROTECTIVE_STOP_FORMS,
    }
)

# One shared immutable empty measured payload; a fact always carries a present
# mapping, never null (the same idiom qmf-core's refusal context uses).
_EMPTY_MEASURED: Final[Mapping[str, object]] = MappingProxyType({})


def evidence_class_for(check: ProbeCheck) -> VenueEvidenceClass:
    """The venue evidence class the given check governs (CT-18; DEC-0138)."""
    return _CHECK_EVIDENCE[check]


# --- refusal builders -------------------------------------------------------


def _invalid(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a profile construction returns."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _unavailable(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``unavailable dependency`` refusal an unmeasured/unverified capability
    returns when a consumer requires its evidence class (FM-6; DEC-0138)."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``policy rejection`` refusal a measured-but-refused capability returns
    when a consumer requires its evidence class in evidence-bearing work (FM-6)."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


# --- validation helpers -----------------------------------------------------


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _deep_freeze(value: object) -> object:
    """Recursively snapshot ``value`` into a shared-safe, read-only form.

    Mirrors qmf-core's idiom: a mapping becomes a :class:`~types.MappingProxyType` over
    deep-frozen values and a list/tuple becomes a tuple, so a measured payload the
    caller keeps a reference to can never be mutated through a stored fact.
    """
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return MappingProxyType({key: _deep_freeze(item) for key, item in mapping.items()})
    if isinstance(value, (list, tuple)):
        sequence = cast("Sequence[object]", value)
        return tuple(_deep_freeze(item) for item in sequence)
    return value


# --- the measured fact ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MeasuredFact:
    """One recorded verify-or-refuse result in a venue-observation profile (CT-18).

    ``measured`` holds the measured value(s) as a present, read-only mapping of
    fp1-clean scalars — empty for an unverified or refused check, because no value is
    ever defaulted (AR-45). ``received_at`` is the mandatory receive instant (the
    Open API exposes no server clock, DEC-0135), ``session_epoch`` the session-epoch id
    distinct from the boot epoch (DEC-0137), and ``credential_ref_id`` the opaque
    *reference id* of the credential the measurement ran under — a reference, never a
    value (CT-21; DEC-0136). ``supersedes`` is the index of the prior same-check fact
    this one replaces, forming the profile's append-only supersedes edge, or ``None``
    for the first fact of its check.

    A fact is occurrence/provenance only and deliberately exposes no ``fp1_identity``:
    the venue-observation profile never enters a downstream fingerprint (DEC-0138).
    """

    check: ProbeCheck
    verdict: ProbeVerdict
    evidence_class: VenueEvidenceClass
    received_at: Instant
    session_epoch: str
    credential_ref_id: str
    measured: Mapping[str, object] = field(default=_EMPTY_MEASURED)
    detail: str = ""
    supersedes: int | None = None

    def __post_init__(self) -> None:
        # Deep-snapshot the measured payload so a later mutation of the caller's dict
        # can never reach back into this frozen, append-only fact.
        object.__setattr__(self, "measured", _deep_freeze(self.measured))

    @property
    def available(self) -> bool:
        """Whether this fact makes its evidence class available (verdict verified)."""
        return self.verdict is ProbeVerdict.VERIFIED

    def summary(self) -> str:
        """A deterministic ``k=v;k=v`` rendering of the measured value, key-sorted.

        The comparable form a findings note reads to detect a contradiction with an
        upstream assumption; empty for a check that measured nothing.
        """
        return ";".join(f"{key}={self.measured[key]}" for key in sorted(self.measured))

    @classmethod
    def try_create(
        cls,
        check: object,
        verdict: object,
        received_at: object,
        session_epoch: object,
        credential_ref_id: object,
        *,
        measured: Mapping[str, object] | None = None,
        detail: str = "",
    ) -> Result[MeasuredFact]:
        """Validate and build a :class:`MeasuredFact`, returning value-or-refusal.

        The evidence class is derived from the check (the 1:1 mapping is contract, not
        caller input). A check or verdict outside its closed set, a non-:class:`Instant`
        receive time, or a blank session-epoch / credential reference id is an
        ``invalid input`` refusal (CT-04; DEC-0109).
        """
        resolved_check = _coerce(ProbeCheck, check)
        if resolved_check is None:
            return _invalid(
                "check",
                "not a member of the first-connection verification suite",
                given=repr(check),
                allowed=[member.value for member in ProbeCheck],
            )
        resolved_verdict = _coerce(ProbeVerdict, verdict)
        if resolved_verdict is None:
            return _invalid(
                "verdict",
                "a verify-or-refuse verdict is verified, unverified, or refused",
                given=repr(verdict),
                allowed=[member.value for member in ProbeVerdict],
            )
        if not isinstance(received_at, Instant):
            return _invalid(
                "received_at",
                "recording a receive instant is mandatory; the Open API exposes no "
                "server clock (DEC-0135)",
                given=repr(received_at),
            )
        epoch = _clean_str(session_epoch)
        if epoch is None:
            return _invalid(
                "session_epoch",
                "a session-epoch id (distinct from the boot epoch) is a non-empty token",
                given=repr(session_epoch),
            )
        ref_id = _clean_str(credential_ref_id)
        if ref_id is None:
            return _invalid(
                "credential_ref_id",
                "a credential appears only by its opaque reference id, never its value",
                given=repr(credential_ref_id),
            )
        return Ok(
            cls(
                check=resolved_check,
                verdict=resolved_verdict,
                evidence_class=evidence_class_for(resolved_check),
                received_at=received_at,
                session_epoch=epoch,
                credential_ref_id=ref_id,
                measured=measured if measured is not None else _EMPTY_MEASURED,
                detail=detail,
            )
        )


# --- the venue-observation profile ------------------------------------------


@dataclass(frozen=True, slots=True)
class VenueObservationProfile:
    """The append-only per-(VenueId, account) venue-observation profile (CT-18).

    Immutable: :meth:`with_fact` returns a *new* profile with one fact appended and
    its ``supersedes`` edge wired to the prior fact of the same check, so history is
    never rewritten (DEC-0138). :meth:`require_evidence` is the verify-or-refuse gate a
    consumer reads before treating a measured-at-connection capability as governed.
    """

    venue_id: VenueId
    account: Account
    facts: tuple[MeasuredFact, ...] = ()

    @classmethod
    def try_create(cls, venue_id: object, account: object) -> Result[VenueObservationProfile]:
        """Validate and build an empty profile, returning value-or-refusal.

        The profile is keyed per (VenueId, account); the account must belong to the
        venue, or the key would name a binding that cannot exist (CT-03; DEC-0107).
        """
        if not isinstance(venue_id, VenueId) or venue_id.value.strip() == "":
            return _invalid(
                "venue_id", "a profile is keyed by a valid VenueId", given=repr(venue_id)
            )
        if not isinstance(account, Account):
            return _invalid("account", "a profile is keyed by a valid Account", given=repr(account))
        if account.venue != venue_id:
            return _invalid(
                "account",
                "the account does not belong to this venue; the (VenueId, account) key "
                "would name a binding that cannot exist",
                venue=venue_id.value,
                account_venue=account.venue.value,
            )
        return Ok(cls(venue_id=venue_id, account=account))

    def facts_for(self, check: ProbeCheck) -> tuple[MeasuredFact, ...]:
        """Every recorded fact for one check, oldest first (append order)."""
        return tuple(fact for fact in self.facts if fact.check is check)

    def latest_for(self, check: ProbeCheck) -> MeasuredFact | None:
        """The most recent fact for one check, or ``None`` if none is recorded."""
        recorded = self.facts_for(check)
        return recorded[-1] if recorded else None

    def with_fact(self, fact: object) -> Result[VenueObservationProfile]:
        """Append ``fact``, wiring its supersedes edge, and return the new profile.

        The appended fact's ``supersedes`` is set to the index of the latest prior fact
        of the same check (or left ``None`` for the first), so the profile records the
        replacement without ever mutating the superseded fact — append-only with
        supersedes edges (DEC-0138). A value that is not a :class:`MeasuredFact` is an
        ``invalid input`` refusal.
        """
        if not isinstance(fact, MeasuredFact):
            return _invalid(
                "fact", "only a MeasuredFact is recorded into the profile", given=repr(fact)
            )
        prior_index: int | None = None
        for index, existing in enumerate(self.facts):
            if existing.check is fact.check:
                prior_index = index
        appended = dataclasses.replace(fact, supersedes=prior_index)
        return Ok(dataclasses.replace(self, facts=(*self.facts, appended)))

    def require_evidence(self, evidence_class: object) -> Result[bool]:
        """The verify-or-refuse gate over one evidence class (FM-6; DEC-0138).

        Returns ``Ok(True)`` only when the latest fact governing the class is
        ``verified``. An absent fact or an ``unverified`` one is an ``unavailable
        dependency`` refusal — the measured-at-connection capability is unavailable
        until the profile supplies it — and a ``refused`` one is a ``policy rejection``:
        consuming a measured-but-unverified capability in evidence-bearing work is
        refused, never silently governed. No value is ever defaulted.
        """
        resolved = _coerce(VenueEvidenceClass, evidence_class)
        if resolved is None:
            return _invalid(
                "evidence_class",
                "not a member of the venue evidence-class set",
                given=repr(evidence_class),
                allowed=[member.value for member in VenueEvidenceClass],
            )
        latest: MeasuredFact | None = None
        for fact in self.facts:
            if fact.evidence_class is resolved:
                latest = fact
        if latest is None:
            return _unavailable(
                "evidence_class",
                "no venue-observation profile fact governs this evidence class; the "
                "measured-at-connection capability is unavailable until the probe records it",
                evidence_class=resolved.value,
            )
        if latest.verdict is ProbeVerdict.VERIFIED:
            return Ok(True)
        if latest.verdict is ProbeVerdict.UNVERIFIED:
            return _unavailable(
                "evidence_class",
                "the governing check is unverified; the dependent evidence class stays "
                "unavailable and no value is defaulted",
                evidence_class=resolved.value,
                check=latest.check.value,
            )
        return _policy(
            "evidence_class",
            "the governing verify-or-refuse check was refused; consuming this "
            "measured-but-unverified capability in evidence-bearing work is refused",
            evidence_class=resolved.value,
            check=latest.check.value,
        )

    def mint_daily_boundary_calendar(
        self, rule_set_version: object, tzdata_version: object
    ) -> Result[CalendarIdentity]:
        """Mint the venue-scoped market-hours calendar identity for the measured D1
        boundary (CT-18; DEC-0135, DEC-0141).

        Verify-or-refuse: only a ``verified`` daily-boundary fact mints an identity;
        until the boundary is measured and verified the venue's daily bars stay
        ungoverned, so an unmeasured boundary is an ``unavailable dependency`` refusal.
        The identity *is* the rule set — the venue and the measured UTC minute-of-day
        are encoded into the rule-set token, never the demoted 17:00-New-York claim —
        and its version and pinned tzdata are supplied by the caller, never hardcoded.
        """
        latest = self.latest_for(ProbeCheck.DAILY_BOUNDARY)
        if latest is None or latest.verdict is not ProbeVerdict.VERIFIED:
            return _unavailable(
                "daily_boundary",
                "the venue's daily-bar boundary is unmeasured or unverified; venue daily "
                "bars stay ungoverned until it is measured and verified (DEC-0135)",
            )
        minute = latest.measured.get("utc_minute_of_day")
        if not isinstance(minute, int) or isinstance(minute, bool):
            return _unavailable(  # pragma: no cover - a verified boundary always carries its minute
                "daily_boundary",
                "the verified daily-boundary fact carries no measured minute-of-day",
            )
        rule_set = f"venue-daily::{self.venue_id.value}::utc_minute_of_day={minute}"
        return CalendarIdentity.try_create(rule_set, rule_set_version, tzdata_version)


def _coerce(enum_cls: type[_EnumT], value: object) -> _EnumT | None:
    """Return the enum member ``value`` names, or ``None`` if it names none."""
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            return None
    return None
