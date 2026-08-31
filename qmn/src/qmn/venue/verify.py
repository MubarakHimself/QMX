"""CT-18 verify-or-refuse at connection time (Story 24.2 / D008).

Runs the required live-venue-fact suite against a newly established session:
timestamp unit, venue daily boundary, BID/ASK trendbar basis, pip formula,
account money exponent, netting-versus-hedging, amend atomicity, pacing scope,
protective-stop forms, and every other CT-18 required connection check.

The **static capability declaration** stays distinct from the measured per-account
**venue-observation profile**. Absent, contradictory, stale, or unverified fields
yield a typed refusal, journal ``data quality``, and keep the command sequencer
closed — market data remains recordable where the dependent evidence class is
safe. Broker-fact drift retains the prior profile (append-only supersedes), mints
a new measured version, and refuses affected bindings until revalidated; no
measured fact is silently rewritten in place.

The credential-free FEAT-0023 conformance double supplies synthetic measured
facts so this story's gate needs no Spotware token. A separately tagged live
acceptance exercises the same verifier against a credentialed session.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qmf.core import (
    Account,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    VenueId,
    is_refusal,
)
from qmf.venue.capabilities import (
    CapabilityDeclaration,
    CapabilityDiscovery,
    CapabilityField,
    CapabilityFieldName,
    ErrorMap,
    FieldMarking,
)
from qmf.venue.observation import (
    REQUIRED_CONNECTION_CHECKS,
    MeasuredFact,
    ProbeCheck,
    ProbeVerdict,
    VenueObservationProfile,
    evidence_class_for,
)
from qmf.venue.proto import ProtoArtifact

__all__ = [
    "DATA_QUALITY_EVENT_TYPE",
    "BindingRevalidationState",
    "DataQualityJournalEvent",
    "FieldDefectKind",
    "MeasuredFactBundle",
    "VenueFactVerification",
    "VenueFactVerifier",
    "conformance_measured_facts",
    "ctrader_static_declaration",
]


DATA_QUALITY_EVENT_TYPE: Final[str] = "data quality"


class FieldDefectKind(StrEnum):
    """Why a required CT-18 connection field refuses use (Story 24.2)."""

    ABSENT = "absent"
    CONTRADICTORY = "contradictory"
    STALE = "stale"
    UNVERIFIED = "unverified"
    REFUSED = "refused"


class BindingRevalidationState(StrEnum):
    """Per-binding readiness after a measured-fact drift event."""

    VALID = "valid"
    NEEDS_REVALIDATION = "needs-revalidation"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class DataQualityJournalEvent:
    """A venue-authored ``data quality`` journal row for a verification defect.

    Uses the AD-21 event-type token verbatim. qmn does not import qmf-risk; the
    string is the contract surface consumers join on (DEC-0145, DEC-0138).
    """

    event_type: str
    check: str
    defect: FieldDefectKind
    detail: str
    venue_id: str
    account_id: str
    profile_version: int
    received_at_ns: int

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "event_type": self.event_type,
                "check": self.check,
                "defect": self.defect.value,
                "detail": self.detail,
                "venue_id": self.venue_id,
                "account_id": self.account_id,
                "profile_version": self.profile_version,
                "received_at_ns": self.received_at_ns,
            }
        )


@dataclass(frozen=True, slots=True)
class MeasuredFactBundle:
    """Synthetic or live measured facts keyed by :class:`ProbeCheck`.

    The conformance double builds a fully-verified bundle; a live session fills
    the same shape from wire samples. Facts are occurrence payloads only — they
    never mutate a prior profile in place.
    """

    facts: Mapping[ProbeCheck, MeasuredFact]

    @classmethod
    def try_create(cls, facts: object) -> Result[MeasuredFactBundle]:
        if not isinstance(facts, Mapping):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "facts",
                    "reason": "measured fact bundle requires a ProbeCheck → MeasuredFact map",
                    "given": type(facts).__name__,
                },
            )
        resolved: dict[ProbeCheck, MeasuredFact] = {}
        for key, value in facts.items():
            check = key if isinstance(key, ProbeCheck) else None
            if check is None and isinstance(key, str):
                try:
                    check = ProbeCheck(key)
                except ValueError:
                    check = None
            if check is None:
                return TypedRefusal(
                    category=RefusalCategory.INVALID_INPUT,
                    retryability=Retryability.NO,
                    context={
                        "field": "facts",
                        "reason": "each key must be a ProbeCheck",
                        "given": repr(key),
                    },
                )
            if not isinstance(value, MeasuredFact):
                return TypedRefusal(
                    category=RefusalCategory.INVALID_INPUT,
                    retryability=Retryability.NO,
                    context={
                        "field": "facts",
                        "reason": "each value must be a MeasuredFact",
                        "check": check.value,
                    },
                )
            if value.check is not check:
                return TypedRefusal(
                    category=RefusalCategory.INVALID_INPUT,
                    retryability=Retryability.NO,
                    context={
                        "field": "facts",
                        "reason": "MeasuredFact.check must match its bundle key",
                        "key": check.value,
                        "fact_check": value.check.value,
                    },
                )
            resolved[check] = value
        return Ok(cls(facts=MappingProxyType(resolved)))


@dataclass(frozen=True, slots=True)
class VenueFactVerification:
    """Outcome of one connection-time CT-18 verification pass."""

    declaration: CapabilityDeclaration
    discovery: CapabilityDiscovery
    profile: VenueObservationProfile
    profile_version: int
    journal: tuple[DataQualityJournalEvent, ...]
    defects: Mapping[str, FieldDefectKind]
    command_sequencer_open: bool
    market_data_recordable: bool
    bindings: Mapping[str, BindingRevalidationState] = field(
        default_factory=lambda: MappingProxyType({})
    )

    @property
    def static_declaration(self) -> CapabilityDeclaration:
        """The static artifact — never conflated with the measured profile."""
        return self.declaration

    @property
    def measured_profile(self) -> VenueObservationProfile:
        """The per-account measured observation profile."""
        return self.profile

    def require_field(self, check: object) -> Result[MeasuredFact]:
        """Verify-or-refuse one required field before command or evidence use."""
        resolved = check if isinstance(check, ProbeCheck) else None
        if resolved is None and isinstance(check, str):
            try:
                resolved = ProbeCheck(check)
            except ValueError:
                resolved = None
        if resolved is None:
            return TypedRefusal(
                category=RefusalCategory.UNSUPPORTED_CAPABILITY,
                retryability=Retryability.NO,
                context={
                    "field": "check",
                    "reason": "not a CT-18 required connection check",
                    "given": repr(check),
                },
            )
        defect = self.defects.get(resolved.value)
        fact = self.profile.latest_for(resolved)
        if defect is not None:
            if defect in {
                FieldDefectKind.REFUSED,
                FieldDefectKind.CONTRADICTORY,
                FieldDefectKind.STALE,
            }:
                return TypedRefusal(
                    category=RefusalCategory.POLICY_REJECTION,
                    retryability=Retryability.NO
                    if defect is not FieldDefectKind.STALE
                    else Retryability.AFTER_CONDITION,
                    context={
                        "field": resolved.value,
                        "reason": f"required CT-18 field is {defect.value}",
                        "defect": defect.value,
                        "evidence_class": evidence_class_for(resolved).value,
                    },
                    after_condition_descriptor=(
                        "revalidate venue-observation profile"
                        if defect is FieldDefectKind.STALE
                        else None
                    ),
                )
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": resolved.value,
                    "reason": f"required CT-18 field is {defect.value}",
                    "defect": defect.value,
                    "evidence_class": evidence_class_for(resolved).value,
                },
                after_condition_descriptor="complete connection-time verification suite",
            )
        if fact is None or fact.verdict is not ProbeVerdict.VERIFIED:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": resolved.value,
                    "reason": "required CT-18 field is absent or unverified",
                    "evidence_class": evidence_class_for(resolved).value,
                },
                after_condition_descriptor="complete connection-time verification suite",
            )
        return Ok(fact)

    def binding_state(self, binding_id: object) -> Result[BindingRevalidationState]:
        """Readiness of one binding against the current measured profile version."""
        if not isinstance(binding_id, str) or binding_id.strip() == "":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "binding_id",
                    "reason": "binding id is a non-empty token",
                    "given": repr(binding_id),
                },
            )
        state = self.bindings.get(binding_id)
        if state is None:
            if self.command_sequencer_open:
                return Ok(BindingRevalidationState.VALID)
            return Ok(BindingRevalidationState.REFUSED)
        if state is BindingRevalidationState.NEEDS_REVALIDATION:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": "binding",
                    "reason": "broker-fact drift requires revalidation before use",
                    "binding_id": binding_id,
                    "profile_version": self.profile_version,
                },
                after_condition_descriptor="revalidate binding against new observation profile",
            )
        if state is BindingRevalidationState.REFUSED:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "binding",
                    "reason": "binding refused against current observation profile",
                    "binding_id": binding_id,
                },
            )
        return Ok(state)


@dataclass
class VenueFactVerifier:
    """Connection-time CT-18 verifier keeping static and measured artifacts distinct.

    Constructed with the static :class:`CapabilityDeclaration` (present at wiring).
    :meth:`verify` attaches a fresh measured profile from a :class:`MeasuredFactBundle`
    and returns a :class:`VenueFactVerification`. Drift is applied through
    :meth:`apply_remeasurement`, which retains the prior profile history via
    supersedes edges and marks bindings for revalidation.
    """

    declaration: CapabilityDeclaration
    venue_id: VenueId
    account: Account
    _prior: VenueFactVerification | None = None
    _binding_ids: tuple[str, ...] = ()

    @classmethod
    def try_create(
        cls,
        declaration: object,
        venue_id: object,
        account: object,
        *,
        binding_ids: object = (),
    ) -> Result[VenueFactVerifier]:
        if not isinstance(declaration, CapabilityDeclaration):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "declaration",
                    "reason": "static CapabilityDeclaration is required at construction",
                    "given": type(declaration).__name__,
                },
            )
        if not isinstance(venue_id, VenueId) or venue_id.value.strip() == "":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "venue_id",
                    "reason": "valid VenueId required",
                    "given": repr(venue_id),
                },
            )
        if not isinstance(account, Account):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "account",
                    "reason": "valid Account required",
                    "given": repr(account),
                },
            )
        if account.venue != venue_id:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "account",
                    "reason": "account does not belong to this VenueId",
                    "venue": venue_id.value,
                    "account_venue": account.venue.value,
                },
            )
        ids = _coerce_binding_ids(binding_ids)
        if is_refusal(ids):
            return ids
        # Static must stay distinct: every measured-at-connection roster field is
        # marked measured and carries no static value.
        for name, capability_field in declaration.fields.items():
            if (
                name in _MEASURED_ROSTER
                and capability_field.marking is not FieldMarking.MEASURED_AT_CONNECTION
            ):
                return TypedRefusal(
                    category=RefusalCategory.POLICY_REJECTION,
                    retryability=Retryability.NO,
                    context={
                        "field": name.value,
                        "reason": "measured CT-18 field must not carry a static declaration value",
                        "marking": capability_field.marking.value,
                    },
                )
        return Ok(
            cls(
                declaration=declaration,
                venue_id=venue_id,
                account=account,
                _binding_ids=ids.value,
            )
        )

    def verify(self, measured: object, *, received_at: object) -> Result[VenueFactVerification]:
        """Run verify-or-refuse over the required connection checks."""
        if not isinstance(received_at, Instant):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "received_at",
                    "reason": "verification requires an injected receive Instant",
                    "given": repr(received_at),
                },
            )
        bundle = (
            measured
            if isinstance(measured, MeasuredFactBundle)
            else MeasuredFactBundle.try_create(measured)
        )
        if is_refusal(bundle):
            return bundle
        if not isinstance(bundle, MeasuredFactBundle):
            # try_create returned Ok
            bundle = bundle.value

        discovery = CapabilityDiscovery.try_create(self.declaration, self.venue_id, self.account)
        if is_refusal(discovery):
            return discovery

        profile = VenueObservationProfile(venue_id=self.venue_id, account=self.account)
        journal: list[DataQualityJournalEvent] = []
        defects: dict[str, FieldDefectKind] = {}

        for check in REQUIRED_CONNECTION_CHECKS:
            fact = bundle.facts.get(check)
            if fact is None:
                defects[check.value] = FieldDefectKind.ABSENT
                journal.append(
                    _data_quality(
                        check,
                        FieldDefectKind.ABSENT,
                        "required CT-18 field absent from measured bundle",
                        self.venue_id,
                        self.account,
                        profile_version=1,
                        received_at=received_at,
                    )
                )
                continue
            if fact.verdict is ProbeVerdict.UNVERIFIED:
                defects[check.value] = FieldDefectKind.UNVERIFIED
                journal.append(
                    _data_quality(
                        check,
                        FieldDefectKind.UNVERIFIED,
                        fact.detail or "required CT-18 field unverified",
                        self.venue_id,
                        self.account,
                        profile_version=1,
                        received_at=fact.received_at,
                    )
                )
            elif fact.verdict is ProbeVerdict.REFUSED:
                defects[check.value] = FieldDefectKind.REFUSED
                journal.append(
                    _data_quality(
                        check,
                        FieldDefectKind.REFUSED,
                        fact.detail or "required CT-18 field refused",
                        self.venue_id,
                        self.account,
                        profile_version=1,
                        received_at=fact.received_at,
                    )
                )
            recorded = profile.with_fact(fact)
            if is_refusal(recorded):
                return recorded
            profile = recorded.value

        observed = discovery.value.observe(profile)
        if is_refusal(observed):
            return observed

        command_open = len(defects) == 0
        # Market data stays recordable when the spot timestamp unit itself is verified
        # (or at least not refused) — sensing outage narrowing: refuse decode of the
        # defective class, keep recording where safe (TN-11 / Story 24.2).
        spot_defect = defects.get(ProbeCheck.SPOT_TIMESTAMP_UNIT.value)
        market_recordable = spot_defect not in {
            FieldDefectKind.REFUSED,
            FieldDefectKind.CONTRADICTORY,
        }

        binding_state = (
            BindingRevalidationState.VALID
            if command_open
            else BindingRevalidationState.REFUSED
        )
        bindings = dict.fromkeys(self._binding_ids, binding_state)
        outcome = VenueFactVerification(
            declaration=self.declaration,
            discovery=observed.value,
            profile=profile,
            profile_version=1,
            journal=tuple(journal),
            defects=MappingProxyType(defects),
            command_sequencer_open=command_open,
            market_data_recordable=market_recordable,
            bindings=MappingProxyType(bindings),
        )
        self._prior = outcome
        return Ok(outcome)

    def apply_remeasurement(
        self,
        measured: object,
        *,
        received_at: object,
        prior: VenueFactVerification | None = None,
    ) -> Result[VenueFactVerification]:
        """Detect broker-fact drift: retain prior profile, mint a new version.

        Never mutates measured facts in place. Prior facts remain in the append-only
        profile via supersedes edges. Affected bindings move to
        ``needs-revalidation`` and refuse until revalidated.
        """
        base = prior if prior is not None else self._prior
        if base is None:
            return self.verify(measured, received_at=received_at)
        if not isinstance(received_at, Instant):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "received_at",
                    "reason": "re-measurement requires an injected receive Instant",
                    "given": repr(received_at),
                },
            )
        bundle_result = (
            measured
            if isinstance(measured, MeasuredFactBundle)
            else MeasuredFactBundle.try_create(measured)
        )
        if is_refusal(bundle_result):
            return bundle_result
        bundle = (
            bundle_result if isinstance(bundle_result, MeasuredFactBundle) else bundle_result.value
        )

        profile = base.profile
        journal: list[DataQualityJournalEvent] = list(base.journal)
        defects: dict[str, FieldDefectKind] = {}
        drifted: list[str] = []
        new_version = base.profile_version + 1

        for check in REQUIRED_CONNECTION_CHECKS:
            new_fact = bundle.facts.get(check)
            prior_fact = profile.latest_for(check)
            if new_fact is None:
                defects[check.value] = FieldDefectKind.ABSENT
                journal.append(
                    _data_quality(
                        check,
                        FieldDefectKind.ABSENT,
                        "remeasurement omitted a required CT-18 field",
                        self.venue_id,
                        self.account,
                        profile_version=new_version,
                        received_at=received_at,
                    )
                )
                continue
            if (
                prior_fact is not None
                and prior_fact.verdict is ProbeVerdict.VERIFIED
                and new_fact.verdict is ProbeVerdict.VERIFIED
                and prior_fact.summary() != new_fact.summary()
            ):
                drifted.append(check.value)
                journal.append(
                    _data_quality(
                        check,
                        FieldDefectKind.STALE,
                        "broker fact drifted; prior profile retained, new version minted",
                        self.venue_id,
                        self.account,
                        profile_version=new_version,
                        received_at=new_fact.received_at,
                    )
                )
            if new_fact.verdict is ProbeVerdict.UNVERIFIED:
                defects[check.value] = FieldDefectKind.UNVERIFIED
            elif new_fact.verdict is ProbeVerdict.REFUSED:
                defects[check.value] = FieldDefectKind.REFUSED
            recorded = profile.with_fact(new_fact)
            if is_refusal(recorded):
                return recorded
            profile = recorded.value

        # Drift marks the prior measurement stale for dependents even when the new
        # fact verified — bindings must revalidate against the new profile version.
        for check_name in drifted:
            defects.setdefault(check_name, FieldDefectKind.STALE)

        discovery = CapabilityDiscovery.try_create(self.declaration, self.venue_id, self.account)
        if is_refusal(discovery):
            return discovery
        observed = discovery.value.observe(profile)
        if is_refusal(observed):
            return observed

        command_open = len(defects) == 0 and len(drifted) == 0
        # After drift, sequencer stays closed until bindings revalidate even if
        # every new fact verified (no silent in-place change).
        if drifted:
            command_open = False
            for check_name in drifted:
                defects[check_name] = FieldDefectKind.STALE

        spot_defect = defects.get(ProbeCheck.SPOT_TIMESTAMP_UNIT.value)
        market_recordable = spot_defect not in {
            FieldDefectKind.REFUSED,
            FieldDefectKind.CONTRADICTORY,
        }
        binding_state = (
            BindingRevalidationState.NEEDS_REVALIDATION
            if drifted or defects
            else BindingRevalidationState.VALID
        )
        bindings = dict.fromkeys(self._binding_ids, binding_state)
        # Preserve prior binding keys even when the verifier was built without them.
        for binding_id in base.bindings:
            bindings.setdefault(binding_id, binding_state)

        outcome = VenueFactVerification(
            declaration=self.declaration,
            discovery=observed.value,
            profile=profile,
            profile_version=new_version,
            journal=tuple(journal),
            defects=MappingProxyType(defects),
            command_sequencer_open=command_open,
            market_data_recordable=market_recordable,
            bindings=MappingProxyType(bindings),
        )
        self._prior = outcome
        return Ok(outcome)

    def require_command_sequencer(self, verification: VenueFactVerification) -> Result[bool]:
        """Gate opening the command sequencer — typed refusal while defects remain."""
        if verification.command_sequencer_open:
            return Ok(True)
        return TypedRefusal(
            category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
            retryability=Retryability.AFTER_CONDITION,
            context={
                "field": "command_sequencer",
                "reason": "command sequencer stays closed until every required CT-18 "
                "field is verified and bindings are validated",
                "defects": {key: value.value for key, value in verification.defects.items()},
                "journal_event_type": DATA_QUALITY_EVENT_TYPE,
                "profile_version": verification.profile_version,
                "market_data_recordable": verification.market_data_recordable,
            },
            after_condition_descriptor="complete connection-time verification suite",
        )

    def revalidate_binding(
        self, verification: VenueFactVerification, binding_id: object
    ) -> Result[VenueFactVerification]:
        """Clear a binding's needs-revalidation once the operator revalidates it."""
        if not isinstance(binding_id, str) or binding_id.strip() == "":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "binding_id",
                    "reason": "binding id is a non-empty token",
                    "given": repr(binding_id),
                },
            )
        # Stale-only defects from drift clear once every binding is revalidated and
        # the new measured facts themselves verified; lingering absent/refused/unverified
        # defects still block revalidation.
        blocking = {
            key: value
            for key, value in verification.defects.items()
            if value is not FieldDefectKind.STALE
        }
        if blocking:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": "binding",
                    "reason": "cannot revalidate binding while profile defects remain",
                    "defects": {key: value.value for key, value in blocking.items()},
                },
                after_condition_descriptor="clear observation-profile defects",
            )
        updated = dict(verification.bindings)
        updated[binding_id] = BindingRevalidationState.VALID
        remaining_stale = any(
            state is BindingRevalidationState.NEEDS_REVALIDATION for state in updated.values()
        )
        cleared_defects = (
            MappingProxyType({})
            if not remaining_stale
            else verification.defects
        )
        command_open = (not remaining_stale) and (not cleared_defects)
        outcome = replace(
            verification,
            bindings=MappingProxyType(updated),
            defects=cleared_defects,
            command_sequencer_open=command_open,
        )
        self._prior = outcome
        return Ok(outcome)


def _data_quality(
    check: ProbeCheck,
    defect: FieldDefectKind,
    detail: str,
    venue_id: VenueId,
    account: Account,
    *,
    profile_version: int,
    received_at: Instant,
) -> DataQualityJournalEvent:
    return DataQualityJournalEvent(
        event_type=DATA_QUALITY_EVENT_TYPE,
        check=check.value,
        defect=defect,
        detail=detail,
        venue_id=venue_id.value,
        account_id=account.account_id,
        profile_version=profile_version,
        received_at_ns=received_at.value_ns,
    )


def _coerce_binding_ids(value: object) -> Result[tuple[str, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, str):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "binding_ids",
                "reason": "binding ids are a sequence of non-empty tokens",
                "given": repr(value),
            },
        )
    if not isinstance(value, Sequence):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "binding_ids",
                "reason": "binding ids are a sequence of non-empty tokens",
                "given": repr(value),
            },
        )
    resolved: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or item.strip() == "":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "binding_ids",
                    "reason": "each binding id is a non-empty token",
                    "index": index,
                    "given": repr(item),
                },
            )
        resolved.append(item)
    return Ok(tuple(resolved))


_MEASURED_ROSTER: Final[frozenset[CapabilityFieldName]] = frozenset(
    {
        CapabilityFieldName.POSITION_MODEL,
        CapabilityFieldName.SETTLEMENT_CURRENCY,
        CapabilityFieldName.MARGIN_SURFACE,
        CapabilityFieldName.VALUE_FACTOR_METADATA,
        CapabilityFieldName.PROTECTION_CAPABILITIES,
    }
)


# --- static declaration + conformance measured facts ------------------------


def ctrader_static_declaration(
    *,
    adapter_version: str = "qmn.venue/24.2",
    proto_release_tag: int = 91,
    descriptor_digest: str = "sha256:" + ("a" * 64),
) -> Result[CapabilityDeclaration]:
    """Build the credential-free static CT-18 declaration for the cTrader adapter.

    Measured-at-connection roster fields carry no static value. The verification
    suite field lists every Story 24.2 required check.
    """
    artifact = ProtoArtifact.try_create(
        "openapi-proto-messages", proto_release_tag, descriptor_digest
    )
    if is_refusal(artifact):
        return artifact
    error_map = ErrorMap.try_create(1, ())
    if is_refusal(error_map):
        return error_map

    def _static(name: CapabilityFieldName, value: object) -> Result[CapabilityField]:
        return CapabilityField.static(name, value)

    def _measured(name: CapabilityFieldName) -> Result[CapabilityField]:
        return CapabilityField.measured(name)

    fields_spec: list[tuple[CapabilityFieldName, object | None]] = [
        (CapabilityFieldName.MARKET_DATA_KINDS, ["tick", "bar", "depth"]),
        (
            CapabilityFieldName.ORDER_PARAMETER_SUBSET,
            {
                "order_types": ["market", "limit", "stop", "stop-limit"],
                "protective_stop_attachment": "entry-relative",
            },
        ),
        (
            CapabilityFieldName.COMMAND_SCOPES,
            ["account", "account-binding", "instrument-within-binding"],
        ),
        (CapabilityFieldName.ACKNOWLEDGEMENT_MODES, {"place_order": "explicit-event"}),
        (CapabilityFieldName.POSITION_MODEL, None),
        (CapabilityFieldName.SESSION_TOPOLOGY, "two-connections-demo-live-separate-hosts"),
        (CapabilityFieldName.THROTTLE_SCOPE, "connection"),
        (
            CapabilityFieldName.RATE_LIMITS,
            {"non_historical_per_second": 50, "historical_per_second": 5},
        ),
        (
            CapabilityFieldName.SPAN_CAPS_AND_PAGING,
            {"historical_span_cap_ms": 604_800_000, "paging": "hasMore"},
        ),
        (
            CapabilityFieldName.TOKEN_LIFECYCLE_CLASS,
            {"access_token_days": 30, "refresh_token": "never-expiring"},
        ),
        (CapabilityFieldName.EQUITY_NATIVENESS, "derived"),
        (CapabilityFieldName.SERVER_CLOCK_AVAILABILITY, False),
        (CapabilityFieldName.INSTRUMENT_METADATA_SURFACE, "full-symbol-record-required"),
        (CapabilityFieldName.ATTRIBUTION_LABEL_SUPPORT, False),
        (CapabilityFieldName.PROTECTION_PRIMITIVES, ["suspend-new", "drain", "close_all"]),
        (CapabilityFieldName.SETTLEMENT_CURRENCY, None),
        (CapabilityFieldName.MARGIN_SURFACE, None),
        (CapabilityFieldName.VALUE_FACTOR_METADATA, None),
        (CapabilityFieldName.RECONCILIATION_LOOKBACK, "do-not-default"),
        (CapabilityFieldName.PROTECTION_CAPABILITIES, None),
        (CapabilityFieldName.COMMAND_ID_MAPPING, {"injective_total": True}),
        (
            CapabilityFieldName.FLOAT_TARGET_SCALES,
            {
                "execution_price": "declared-digits",
                "money": "account-money-exponent",
                "market_data": "wire-scale",
            },
        ),
        (
            CapabilityFieldName.VERIFICATION_SUITE,
            [check.value for check in REQUIRED_CONNECTION_CHECKS],
        ),
    ]
    fields: list[CapabilityField] = []
    for name, value in fields_spec:
        built = _measured(name) if value is None else _static(name, value)
        if is_refusal(built):
            return built
        fields.append(built.value)
    return CapabilityDeclaration.try_create(
        adapter_version, artifact.value, error_map.value, fields
    )


def conformance_measured_facts(
    *,
    received_at: Instant,
    session_epoch: str = "conformance-session",
    credential_ref_id: str = "conformance-cred-ref",
    position_model: str = "netting",
    amend_atomicity: str = "non-atomic",
    pacing_scope: str = "connection",
    protective_stop_forms: Sequence[str] | None = None,
    quote_type: str = "bid",
    utc_minute_of_day: int = 1020,
    money_digits: int = 2,
    pip_position: int = 4,
) -> Result[MeasuredFactBundle]:
    """Fully-verified measured fact bundle for the FEAT-0023 conformance double."""
    forms = (
        list(protective_stop_forms)
        if protective_stop_forms is not None
        else ["entry-relative"]
    )
    payloads: dict[ProbeCheck, dict[str, object]] = {
        ProbeCheck.SPOT_TIMESTAMP_UNIT: {"unit": "milliseconds"},
        ProbeCheck.DAILY_BOUNDARY: {"utc_minute_of_day": utc_minute_of_day},
        ProbeCheck.BAR_BASIS: {"quote_type": quote_type},
        ProbeCheck.PIP_FORMULA: {
            "pip_position": pip_position,
            "pip_size_num": 1,
            "pip_size_den": 10**pip_position,
        },
        ProbeCheck.MONEY_EXPONENT: {"money_digits": money_digits},
        ProbeCheck.AMEND_ATOMICITY: {"atomicity": amend_atomicity},
        ProbeCheck.POSITION_MODEL: {"position_model": position_model},
        ProbeCheck.PACING_SCOPE: {"throttle_scope": pacing_scope},
        ProbeCheck.PROTECTIVE_STOP_FORMS: {
            "forms_per_order_type": {"market": forms[0], "limit": "absolute"}
        },
    }
    facts: dict[ProbeCheck, MeasuredFact] = {}
    for check, measured in payloads.items():
        built = MeasuredFact.try_create(
            check,
            ProbeVerdict.VERIFIED,
            received_at,
            session_epoch,
            credential_ref_id,
            measured=measured,
            detail=f"conformance double verified {check.value}",
        )
        if is_refusal(built):
            return built
        facts[check] = built.value
    return MeasuredFactBundle.try_create(facts)
