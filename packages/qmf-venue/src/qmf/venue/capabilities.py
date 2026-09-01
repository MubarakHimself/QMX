"""Two-artifact capability discovery, wired in a fixed order (Story 8.4; CT-18).

`COMP-QMF-VENUE`'s capability surface is **two artifacts, never one** (CT-18; DEC-0138,
DEC-0140):

* the **static capability declaration** — this module's :class:`CapabilityDeclaration`:
  importable without credentials, adapter-version-scoped, containing no measured or
  tunable value, carrying the venue protocol artifact identity (the pinned Spotware
  release tag, e.g. 91), with every roster field marked ``static`` or
  ``measured-at-connection``, and a fingerprint that is **identity-bearing** for any
  artifact whose decode depended on it; and
* the **venue-observation profile** — :class:`~qmf.venue.observation.VenueObservationProfile`,
  produced post-connect by the first-connection verification suite (Story 8.1),
  append-only with supersedes edges, occurrence/provenance only and **never**
  identity-bearing downstream.

:class:`CapabilityDiscovery` is the orchestrator that wires the two in a **fixed order**
(SC-09, AR-45; DEC-0138): the declaration is present at construction, and the
venue-observation profile must exist before the first command and before any
evidence-bearing decode. A ``measured-at-connection`` capability consumed before its
profile exists is an ``unavailable dependency`` refusal; a measured-but-unverified
capability consumed in evidence-bearing work is a ``policy rejection`` refusal; invoking
an undeclared capability, an undeclared order parameter, or an unsupported close scope is
an ``unsupported capability`` refusal, never emulated at a wider scope.

The declaration carries the pinned **error map** (:class:`ErrorMap`): a versioned table
of ``(venue code, context) -> (refusal category, retryability, after-condition,
submission-outcome class)`` rows. A venue code reads as ``rejected-by-venue`` only where
a pinned row declares that class; every unmapped code takes the **fail-closed default**
— ``(transient venue failure, retryable = no, outcome = UNKNOWN)`` plus an alarm, where
``UNKNOWN`` is a state, never an error (CT-18; DEC-0137, DEC-0138).

Once the daily boundary is measured and verified, the profile mints a venue-scoped
market-hours calendar identity that anchors venue-native ``BarSpec`` — the mechanism that
turns the venue's own daily-bar slicing into governed evidence without ever assuming it
aligns to QMF's own forex accounting calendar (AR-46; DEC-0135, DEC-0141).

This module holds the **shape and the law** of the two-artifact surface, never a broker
fact: markings, static values, and the error map are declaration *data* an adapter's
composition root supplies, so a broker's measured behavior lives in the profile and per
-broker configuration, never in code (DEC-0139). It imports only ``qmf-core`` and the two
sibling venue modules; nothing imports ``qmf-venue`` (default-deny, L30/DEC-0120). No
binary float touches identity — every declared value is fp1-clean (DEC-0105, DEC-0108).
Frozen, immutable values throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from types import MappingProxyType
from typing import Final, TypeVar, cast

from qmf.core import (
    Account,
    CalendarIdentity,
    Fingerprint,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    VenueId,
    canonical_bytes,
    fingerprint,
    is_refusal,
)
from qmf.venue.observation import VenueEvidenceClass, VenueObservationProfile
from qmf.venue.proto import ProtoArtifact

__all__ = [
    "CapabilityDeclaration",
    "CapabilityDiscovery",
    "CapabilityField",
    "CapabilityFieldName",
    "CloseScope",
    "ErrorMap",
    "ErrorMapResolution",
    "ErrorMapRow",
    "FieldMarking",
    "SubmissionOutcomeClass",
]

_EnumT = TypeVar("_EnumT", bound=StrEnum)


# --- CT-18 vocabulary -------------------------------------------------------


class FieldMarking(StrEnum):
    """How a capability-declaration field is sourced (CT-18 ``field marking``; DEC-0138).

    ``STATIC`` — the value is fixed and adapter-version-scoped, present in the
    declaration and identity-bearing. ``MEASURED_AT_CONNECTION`` — the value is *absent*
    from the declaration and supplied post-connect by the venue-observation profile;
    consuming it before that profile exists is an ``unavailable dependency`` refusal.
    Every roster field carries exactly one marking (DEC-0140).
    """

    STATIC = "static"
    MEASURED_AT_CONNECTION = "measured-at-connection"


class CloseScope(StrEnum):
    """The close scope a ``close_position`` / ``close_all`` command carries (CT-18/CT-19).

    An adapter declares the scopes it natively supports; an unsupported scope is an
    ``unsupported capability`` refusal, **never emulated at a wider scope** (DEC-0137,
    DEC-0138).
    """

    ACCOUNT = "account"
    ACCOUNT_BINDING = "account-binding"
    INSTRUMENT_WITHIN_BINDING = "instrument-within-binding"


class SubmissionOutcomeClass(StrEnum):
    """The error-map submission-outcome class (CT-18 ``submission-outcome class``).

    A venue code reads as ``REJECTED_BY_VENUE`` only where a pinned error-map row
    declares that class; every other path is ``UNKNOWN`` — a state, never an error
    (DEC-0137, DEC-0138).
    """

    REJECTED_BY_VENUE = "rejected-by-venue"
    UNKNOWN = "UNKNOWN"


class CapabilityFieldName(StrEnum):
    """The CT-18-owned capability-declaration field roster (DEC-0138, DEC-0148, DEC-0158).

    The closed set of declared capability names. Invoking any name outside this set is
    an ``unsupported capability`` refusal — the adapter never emulates an undeclared
    capability. The venue protocol artifact, the error map, and the measured-fact
    profile are carried as their own first-class members of the declaration and the
    profile, so they are not roster names here; the roster is otherwise the full CT-18
    field list, each field marked ``static`` or ``measured-at-connection``.
    """

    MARKET_DATA_KINDS = "market_data_kinds"
    ORDER_PARAMETER_SUBSET = "order_parameter_subset"
    COMMAND_SCOPES = "command_scopes"
    ACKNOWLEDGEMENT_MODES = "acknowledgement_modes"
    POSITION_MODEL = "position_model"
    SESSION_TOPOLOGY = "session_topology"
    THROTTLE_SCOPE = "throttle_scope"
    RATE_LIMITS = "rate_limits"
    SPAN_CAPS_AND_PAGING = "span_caps_and_paging"
    TOKEN_LIFECYCLE_CLASS = "token_lifecycle_class"  # noqa: S105 - a field NAME, never a secret value
    EQUITY_NATIVENESS = "equity_nativeness"
    SERVER_CLOCK_AVAILABILITY = "server_clock_availability"
    INSTRUMENT_METADATA_SURFACE = "instrument_metadata_surface"
    ATTRIBUTION_LABEL_SUPPORT = "attribution_label_support"
    PROTECTION_PRIMITIVES = "protection_primitives"
    SETTLEMENT_CURRENCY = "settlement_currency"
    MARGIN_SURFACE = "margin_surface"
    VALUE_FACTOR_METADATA = "value_factor_metadata"
    RECONCILIATION_LOOKBACK = "reconciliation_lookback"
    PROTECTION_CAPABILITIES = "protection_capabilities"
    COMMAND_ID_MAPPING = "command_id_mapping"
    FLOAT_TARGET_SCALES = "float_target_scales"
    VERIFICATION_SUITE = "verification_suite"


# The full roster the declaration must cover: every field marked exactly once (DEC-0140).
_ROSTER: Final[frozenset[CapabilityFieldName]] = frozenset(CapabilityFieldName)


# --- refusal builders -------------------------------------------------------


def _invalid(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a construction guard returns."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _unsupported(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``unsupported capability`` refusal an undeclared capability or an
    unsupported close scope returns (FM-4; DEC-0137, DEC-0138)."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNSUPPORTED_CAPABILITY,
        retryability=Retryability.NO,
        context=context,
    )


def _unavailable(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``unavailable dependency`` refusal a measured-at-connection capability
    consumed before its profile exists returns (FM-6; DEC-0138)."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context=context,
    )


# --- helpers ----------------------------------------------------------------


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


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


def _deep_freeze(value: object) -> object:
    """Recursively snapshot ``value`` into a shared-safe, read-only form.

    Mirrors qmf-core's idiom: a mapping becomes a :class:`~types.MappingProxyType` over
    deep-frozen values and a list/tuple becomes a tuple, so a declared value the caller
    keeps a reference to can never be mutated through a stored, frozen declaration.
    """
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return MappingProxyType({key: _deep_freeze(item) for key, item in mapping.items()})
    if isinstance(value, (list, tuple)):
        sequence = cast("Sequence[object]", value)
        return tuple(_deep_freeze(item) for item in sequence)
    return value


def _fp1_clean(value: object) -> TypedRefusal | None:
    """Return a refusal if ``value`` is not fp1-clean identity content, else ``None``.

    The declaration is credential-free and identity-bearing, so a static value must be
    JSON-native fp1 content: a binary float, a null, a bytes/``Decimal``/``Fraction``, or
    a :class:`~qmf.core.SecretRef` / :class:`~qmf.core.SecretValue` is refused at
    construction (the last two would never serialize, so a credential can never enter the
    declaration). Validated by round-tripping through the one canonical serializer.
    """
    encoded = canonical_bytes(value)
    if is_refusal(encoded):
        return _invalid(
            "value",
            "a static declaration value must be fp1-clean identity content (JSON-native, "
            "credential-free, no binary float); the declaration is identity-bearing",
            detail=str(encoded.context.get("reason", "")),
        )
    return None


# --- the pinned error map ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class ErrorMapRow:
    """One pinned error-map row (CT-18 ``error_map``; DEC-0137, DEC-0138).

    Keyed by ``(venue_code, context)`` — the venue code and the command-or-event context
    it applies in — and mapping to ``(refusal_category, retryability, after_condition,
    outcome_class)``. A row may declare ``outcome_class = REJECTED_BY_VENUE``; it is the
    **only** way a venue code reads as rejected-by-venue. ``after_condition`` is present
    only when ``retryability`` is ``after-condition`` (its field-level shape is unpinned).
    """

    venue_code: str
    context: str
    refusal_category: RefusalCategory
    retryability: Retryability
    outcome_class: SubmissionOutcomeClass
    after_condition: str | None = None

    @classmethod
    def try_create(
        cls,
        venue_code: object,
        context: object,
        refusal_category: object,
        retryability: object,
        outcome_class: object,
        after_condition: object = None,
    ) -> Result[ErrorMapRow]:
        """Validate and build an :class:`ErrorMapRow`, returning value-or-refusal.

        A blank code or context, a category/retryability/outcome outside its closed set,
        or an ``after_condition`` that is present without ``retryability = after-condition``
        (or absent when it is required) is an ``invalid input`` refusal — category alone
        never implies retryability, so the pairing is stated explicitly (DEC-0109).
        """
        code = _clean_str(venue_code)
        if code is None:
            return _invalid(
                "venue_code", "an error-map row keys on a venue code", given=repr(venue_code)
            )
        ctx = _clean_str(context)
        if ctx is None:
            return _invalid(
                "context",
                "an error-map row keys on a command-or-event context",
                given=repr(context),
            )
        category = _coerce(RefusalCategory, refusal_category)
        if category is None:
            return _invalid(
                "refusal_category",
                "an error-map row maps to one of the seven refusal categories",
                given=repr(refusal_category),
                allowed=[member.value for member in RefusalCategory],
            )
        retry = _coerce(Retryability, retryability)
        if retry is None:
            return _invalid(
                "retryability",
                "an error-map row declares retryability explicitly; category never implies it",
                given=repr(retryability),
                allowed=[member.value for member in Retryability],
            )
        outcome = _coerce(SubmissionOutcomeClass, outcome_class)
        if outcome is None:
            return _invalid(
                "outcome_class",
                "an error-map row maps to rejected-by-venue or UNKNOWN",
                given=repr(outcome_class),
                allowed=[member.value for member in SubmissionOutcomeClass],
            )
        descriptor = _clean_str(after_condition)
        if retry is Retryability.AFTER_CONDITION and descriptor is None:
            return _invalid(
                "after_condition",
                "retryability after-condition requires an after-condition descriptor",
                given=repr(after_condition),
            )
        if retry is not Retryability.AFTER_CONDITION and descriptor is not None:
            return _invalid(
                "after_condition",
                "an after-condition descriptor is present only with retryability after-condition",
                retryability=retry.value,
            )
        return Ok(
            cls(
                venue_code=code,
                context=ctx,
                refusal_category=category,
                retryability=retry,
                outcome_class=outcome,
                after_condition=descriptor,
            )
        )

    def fp1_identity(self) -> Mapping[str, object]:
        """The row's canonical fp1 identity content (an absent after-condition is an
        omitted key, never a null; DEC-0108)."""
        content: dict[str, object] = {
            "venue_code": self.venue_code,
            "context": self.context,
            "refusal_category": self.refusal_category.value,
            "retryability": self.retryability.value,
            "outcome_class": self.outcome_class.value,
        }
        if self.after_condition is not None:
            content["after_condition"] = self.after_condition
        return content


@dataclass(frozen=True, slots=True)
class ErrorMapResolution:
    """The resolution of a venue code against the error map (CT-18; DEC-0137, DEC-0138).

    ``mapped`` is ``True`` when a pinned row matched, ``False`` when the fail-closed
    default applied. The fail-closed default is ``(transient venue failure, retryable =
    no, outcome = UNKNOWN)`` plus an ``alarm`` — ``UNKNOWN`` a state, never an error.
    ``outcome_class`` is ``REJECTED_BY_VENUE`` only when a row declared it.
    """

    venue_code: str
    context: str
    outcome_class: SubmissionOutcomeClass
    refusal_category: RefusalCategory
    retryability: Retryability
    after_condition: str | None
    mapped: bool
    alarm: bool
    detail: str


@dataclass(frozen=True, slots=True)
class ErrorMap:
    """The versioned, pinned error-map table (CT-18 ``error_map``; DEC-0137, DEC-0138).

    ``version`` versions the table per adapter. ``rows`` are the pinned
    ``(venue_code, context)`` rows; the key must be unique. :meth:`resolve` is fail-closed
    — an unmapped code takes the ``(transient venue failure, retryable = no, outcome =
    UNKNOWN)`` default plus an alarm, and reads as ``rejected-by-venue`` only where a row
    declares that class.
    """

    version: int
    rows: tuple[ErrorMapRow, ...] = ()

    @classmethod
    def try_create(cls, version: object, rows: object) -> Result[ErrorMap]:
        """Validate and build an :class:`ErrorMap`, returning value-or-refusal.

        A non-positive version, a non-sequence of rows, a row that is not an
        :class:`ErrorMapRow`, or a duplicate ``(venue_code, context)`` key is an
        ``invalid input`` refusal — a versioned table must have one row per key.
        """
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            return _invalid(
                "version",
                "an error map is versioned per adapter (a positive integer)",
                given=repr(version),
            )
        if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
            return _invalid(
                "rows", "an error map's rows are a sequence of ErrorMapRow", given=repr(rows)
            )
        seen: set[tuple[str, str]] = set()
        resolved: list[ErrorMapRow] = []
        for index, item in enumerate(cast("Sequence[object]", rows)):
            if not isinstance(item, ErrorMapRow):
                return _invalid(
                    "rows", "each error-map row is an ErrorMapRow", index=index, given=repr(item)
                )
            key = (item.venue_code, item.context)
            if key in seen:
                return _invalid(
                    "rows",
                    "a (venue_code, context) key appears twice; the table maps each key once",
                    venue_code=item.venue_code,
                    context=item.context,
                )
            seen.add(key)
            resolved.append(item)
        return Ok(cls(version=version, rows=tuple(resolved)))

    def resolve(self, venue_code: object, context: object) -> Result[ErrorMapResolution]:
        """Resolve a venue code in a context against the pinned table, value-or-refusal.

        A matching pinned row yields its declared ``(category, retryability,
        after-condition, outcome)`` — the only path to ``rejected-by-venue``. An unmapped
        code takes the fail-closed default: ``(transient venue failure, retryable = no,
        outcome = UNKNOWN)`` plus an alarm. A blank code or context is an ``invalid
        input`` refusal.
        """
        code = _clean_str(venue_code)
        if code is None:
            return _invalid(
                "venue_code", "a venue code is a non-empty string", given=repr(venue_code)
            )
        ctx = _clean_str(context)
        if ctx is None:
            return _invalid("context", "an error-map lookup names its context", given=repr(context))
        for row in self.rows:
            if row.venue_code == code and row.context == ctx:
                return Ok(
                    ErrorMapResolution(
                        venue_code=code,
                        context=ctx,
                        outcome_class=row.outcome_class,
                        refusal_category=row.refusal_category,
                        retryability=row.retryability,
                        after_condition=row.after_condition,
                        mapped=True,
                        alarm=False,
                        detail=f"venue code '{code}' in context '{ctx}' maps to "
                        f"{row.outcome_class.value} per the pinned error map v{self.version}",
                    )
                )
        return Ok(
            ErrorMapResolution(
                venue_code=code,
                context=ctx,
                outcome_class=SubmissionOutcomeClass.UNKNOWN,
                refusal_category=RefusalCategory.TRANSIENT_VENUE_FAILURE,
                retryability=Retryability.NO,
                after_condition=None,
                mapped=False,
                alarm=True,
                detail=f"venue code '{code}' in context '{ctx}' is unmapped; the fail-closed "
                "default applies — transient venue failure, retryable = no, outcome = UNKNOWN "
                "(a state) — plus an alarm",
            )
        )

    def fp1_identity(self) -> Mapping[str, object]:
        """The error map's canonical fp1 identity content — version plus rows sorted by
        their ``(venue_code, context)`` key, so identity is order-independent (DEC-0108)."""
        ordered = sorted(self.rows, key=lambda row: (row.venue_code, row.context))
        return {
            "version": self.version,
            "rows": [dict(row.fp1_identity()) for row in ordered],
        }


# --- one declaration field --------------------------------------------------


@dataclass(frozen=True, slots=True)
class CapabilityField:
    """One capability-declaration field, marked static or measured-at-connection (CT-18).

    A ``static`` field carries its fp1-clean ``value`` (present, identity-bearing); a
    ``measured-at-connection`` field carries **no value** — it is absent from the
    declaration and supplied post-connect by the venue-observation profile (nullability:
    an absent measured value is an omitted key, never a null; DEC-0138, DEC-0140).
    """

    name: CapabilityFieldName
    marking: FieldMarking
    value: object | None = None

    @property
    def is_static(self) -> bool:
        """Whether this field is static (its value is present and identity-bearing)."""
        return self.marking is FieldMarking.STATIC

    @classmethod
    def static(cls, name: object, value: object) -> Result[CapabilityField]:
        """Build a static field carrying an fp1-clean value, returning value-or-refusal.

        The name must be a roster member and the value fp1-clean identity content
        (JSON-native, credential-free, no binary float); the value is deep-frozen so a
        later mutation of the caller's container can never reach the frozen field.
        """
        resolved = _coerce(CapabilityFieldName, name)
        if resolved is None:
            return _invalid(
                "name",
                "a capability field names a CT-18 roster member",
                given=repr(name),
                allowed=[member.value for member in CapabilityFieldName],
            )
        if value is None:
            return _invalid(
                "value", "a static field carries a present value, never a null", name=resolved.value
            )
        unclean = _fp1_clean(value)
        if unclean is not None:
            return unclean
        return Ok(cls(name=resolved, marking=FieldMarking.STATIC, value=_deep_freeze(value)))

    @classmethod
    def measured(cls, name: object) -> Result[CapabilityField]:
        """Build a measured-at-connection field carrying no value, value-or-refusal.

        The name must be a roster member; the value is absent by construction — it rides
        the venue-observation profile, not the declaration (DEC-0138, DEC-0140).
        """
        resolved = _coerce(CapabilityFieldName, name)
        if resolved is None:
            return _invalid(
                "name",
                "a capability field names a CT-18 roster member",
                given=repr(name),
                allowed=[member.value for member in CapabilityFieldName],
            )
        return Ok(cls(name=resolved, marking=FieldMarking.MEASURED_AT_CONNECTION, value=None))

    def fp1_identity(self) -> Mapping[str, object]:
        """The field's canonical fp1 identity content — name, marking, and (only when
        static) its value; a measured field omits the value key (DEC-0108)."""
        content: dict[str, object] = {"name": self.name.value, "marking": self.marking.value}
        if self.marking is FieldMarking.STATIC and self.value is not None:
            content["value"] = self.value
        return content


# --- the static capability declaration --------------------------------------


@dataclass(frozen=True, slots=True)
class CapabilityDeclaration:
    """The static, adapter-version-scoped, credential-free capability declaration (CT-18).

    The first of the two capability artifacts (DEC-0138, DEC-0140). Built through
    :meth:`try_create` from an adapter version, the pinned :class:`~qmf.venue.proto.ProtoArtifact`
    venue protocol identity (carrying the injected release tag, e.g. 91), the pinned
    :class:`ErrorMap`, and the full :class:`CapabilityFieldName` roster — each field
    marked static or measured-at-connection. It contains no measured or tunable value and
    no credential; :meth:`fingerprint` is identity-bearing for any artifact whose decode
    depended on it.
    """

    adapter_version: str
    venue_protocol_artifact: ProtoArtifact
    error_map: ErrorMap
    fields: Mapping[CapabilityFieldName, CapabilityField]

    @classmethod
    def try_create(
        cls,
        adapter_version: object,
        venue_protocol_artifact: object,
        error_map: object,
        fields: object,
    ) -> Result[CapabilityDeclaration]:
        """Validate and build a :class:`CapabilityDeclaration`, returning value-or-refusal.

        A blank adapter version, a non-:class:`~qmf.venue.proto.ProtoArtifact` protocol
        identity, a non-:class:`ErrorMap`, a ``fields`` sequence that is not the full
        roster covered exactly once, a duplicate field, or a malformed ``command_scopes``
        static value each yields an ``invalid input`` refusal. Requiring the *full* roster
        is what makes "every field is marked static or measured-at-connection" a
        construction guarantee, not a hope (DEC-0140).
        """
        version = _clean_str(adapter_version)
        if version is None:
            return _invalid(
                "adapter_version",
                "the declaration is adapter-version-scoped (a non-empty version token)",
                given=repr(adapter_version),
            )
        if not isinstance(venue_protocol_artifact, ProtoArtifact):
            return _invalid(
                "venue_protocol_artifact",
                "the declaration carries the pinned venue protocol artifact identity",
                given=repr(venue_protocol_artifact),
            )
        if not isinstance(error_map, ErrorMap):
            return _invalid(
                "error_map", "the declaration carries a pinned ErrorMap", given=repr(error_map)
            )
        if isinstance(fields, (str, bytes)) or not isinstance(fields, Sequence):
            return _invalid(
                "fields",
                "the declaration's fields are a sequence of CapabilityField",
                given=repr(fields),
            )
        by_name: dict[CapabilityFieldName, CapabilityField] = {}
        for index, item in enumerate(cast("Sequence[object]", fields)):
            if not isinstance(item, CapabilityField):
                return _invalid(
                    "fields", "each field is a CapabilityField", index=index, given=repr(item)
                )
            if item.name in by_name:
                return _invalid("fields", "a field is declared twice", name=item.name.value)
            by_name[item.name] = item
        missing = _ROSTER - set(by_name)
        if missing:
            return _invalid(
                "fields",
                "the declaration must cover the full CT-18 field roster, each marked exactly once",
                missing=sorted(member.value for member in missing),
            )
        scopes_refusal = _validate_command_scopes(by_name[CapabilityFieldName.COMMAND_SCOPES])
        if scopes_refusal is not None:
            return scopes_refusal
        return Ok(
            cls(
                adapter_version=version,
                venue_protocol_artifact=venue_protocol_artifact,
                error_map=error_map,
                fields=MappingProxyType(dict(by_name)),
            )
        )

    def field_for(self, name: object) -> Result[CapabilityField]:
        """The declared field for ``name``, or an ``unsupported capability`` refusal.

        A name outside the CT-18 roster — an undeclared capability — is refused, never
        emulated (FM-4; DEC-0138). The roster is covered in full at construction, so a
        valid roster name always resolves.
        """
        resolved = _coerce(CapabilityFieldName, name)
        if resolved is None:
            return _unsupported(
                "capability",
                "the venue declares no such capability; an undeclared capability is refused, "
                "never emulated",
                given=repr(name),
            )
        declared = self.fields.get(resolved)
        if declared is None:  # pragma: no cover - the full roster is covered at construction
            return _unsupported(
                "capability", "the venue declares no such capability", given=resolved.value
            )
        return Ok(declared)

    def static_value(self, name: object) -> Result[object]:
        """The static value declared for ``name``, returning value-or-refusal.

        An undeclared name is an ``unsupported capability`` refusal; a declared
        ``measured-at-connection`` field is an ``unavailable dependency`` refusal — its
        value is absent from the declaration and rides the venue-observation profile, so
        it can never be read as a static declaration value (FM-6; DEC-0138, DEC-0140).
        """
        declared = self.field_for(name)
        if is_refusal(declared):
            return declared
        capability_field = declared.value
        if not capability_field.is_static:
            return _unavailable(
                "capability",
                "this capability is measured-at-connection; its value is absent from the static "
                "declaration and is supplied only by the venue-observation profile",
                capability=capability_field.name.value,
            )
        # A static field always carries a present value (guaranteed at construction).
        return Ok(cast("object", capability_field.value))

    def close_scope(self, scope: object) -> Result[CloseScope]:
        """Resolve a requested close scope against the declared ``command_scopes``.

        Returns the :class:`CloseScope` only when it is among the natively declared
        scopes; an unknown scope token or a scope the venue does not declare is an
        ``unsupported capability`` refusal — **never emulated at a wider scope** (FM-4;
        DEC-0137, DEC-0138).
        """
        requested = _coerce(CloseScope, scope)
        if requested is None:
            return _unsupported(
                "close_scope",
                "a close scope is one of account | account-binding | instrument-within-binding",
                given=repr(scope),
                allowed=[member.value for member in CloseScope],
            )
        declared = _declared_close_scopes(self.fields[CapabilityFieldName.COMMAND_SCOPES])
        if requested not in declared:
            return _unsupported(
                "close_scope",
                "the venue does not natively support this close scope; it is refused, "
                "never emulated at a wider scope",
                requested=requested.value,
                declared=[member.value for member in declared],
            )
        return Ok(requested)

    def order_parameter(
        self,
        *,
        order_type: object = None,
        time_in_force: object = None,
    ) -> Result[Mapping[str, str]]:
        """Admit an order-type / time-in-force pair against ``order_parameter_subset``.

        Each adapter declares its supported subset in CT-18. Invoking an undeclared
        order type or time-in-force is an ``unsupported capability`` refusal — never
        emulated (CT-18/CT-19; QMX-F064). At least one of ``order_type`` or
        ``time_in_force`` must be supplied.
        """
        if order_type is None and time_in_force is None:
            return _invalid(
                "order_parameter",
                "order_parameter checks require order_type and/or time_in_force",
            )
        declared = _declared_order_parameters(
            self.fields[CapabilityFieldName.ORDER_PARAMETER_SUBSET]
        )
        admitted: dict[str, str] = {}
        if order_type is not None:
            token = _order_parameter_token(order_type)
            if token is None:
                return _unsupported(
                    "order_type",
                    "an order type is a non-empty token declared by the adapter subset",
                    given=repr(order_type),
                )
            if token not in declared["order_types"]:
                return _unsupported(
                    "order_type",
                    "the venue does not declare this order type; invoking an undeclared "
                    "order parameter is refused, never emulated",
                    requested=token,
                    declared=sorted(declared["order_types"]),
                )
            admitted["order_type"] = token
        if time_in_force is not None:
            token = _order_parameter_token(time_in_force)
            if token is None:
                return _unsupported(
                    "time_in_force",
                    "a time-in-force is a non-empty token declared by the adapter subset",
                    given=repr(time_in_force),
                )
            if token not in declared["time_in_force"]:
                return _unsupported(
                    "time_in_force",
                    "the venue does not declare this time-in-force; invoking an undeclared "
                    "order parameter is refused, never emulated",
                    requested=token,
                    declared=sorted(declared["time_in_force"]),
                )
            admitted["time_in_force"] = token
        return Ok(MappingProxyType(admitted))

    def resolve_error(self, venue_code: object, context: object) -> Result[ErrorMapResolution]:
        """Resolve a venue error code through the pinned error map (see ErrorMap.resolve)."""
        return self.error_map.resolve(venue_code, context)

    def fp1_identity(self) -> Mapping[str, object]:
        """The declaration's canonical fp1 identity content (CT-18; DEC-0138, DEC-0140).

        Identity-bearing over the adapter version, the venue protocol artifact identity
        (package, release tag, descriptor-set digest — a tag change moves the identity),
        the pinned error map, and every roster field sorted by name (order-independent).
        A measured-at-connection field contributes only its name and marking, so a
        measured value never enters — and never splits — the declaration's identity.
        """
        ordered = sorted(self.fields.values(), key=lambda declared: declared.name.value)
        return {
            "class": "capability-declaration",
            "adapter_version": self.adapter_version,
            "venue_protocol_artifact": {
                "package_name": self.venue_protocol_artifact.package_name,
                "release_tag": self.venue_protocol_artifact.release_tag,
                "descriptor_set_digest": self.venue_protocol_artifact.descriptor_set_digest,
            },
            "error_map": dict(self.error_map.fp1_identity()),
            "fields": [dict(declared.fp1_identity()) for declared in ordered],
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """The declaration's identity-bearing fp1 fingerprint, returning value-or-refusal.

        Two adapter builds sharing every static capability and the same pinned protocol
        tag fingerprint identically; a changed tag, a changed static value, or a changed
        error-map row moves the fingerprint — so any artifact whose decode depended on the
        declaration can bind to this identity (CT-18; DEC-0138, DEC-0141).
        """
        return fingerprint(self)


# --- the two-artifact discovery orchestrator --------------------------------


@dataclass(frozen=True, slots=True)
class CapabilityDiscovery:
    """The two-artifact capability surface wired in a fixed order (SC-09, AR-45; CT-18).

    Constructed per ``(VenueId, account)`` with the static declaration **present at
    construction**; the per-``(VenueId, account)`` venue-observation profile is attached
    through :meth:`observe` and must exist **before the first command and before any
    evidence-bearing decode** (DEC-0138). A ``measured-at-connection`` capability consumed
    before the profile exists is an ``unavailable dependency`` refusal; a
    measured-but-unverified capability consumed in evidence-bearing work is a ``policy
    rejection`` refusal (delegated to the profile's verify-or-refuse gate). Immutable:
    :meth:`observe` returns a *new* discovery with the profile attached.
    """

    declaration: CapabilityDeclaration
    venue_id: VenueId
    account: Account
    profile: VenueObservationProfile | None = field(default=None)

    @classmethod
    def try_create(
        cls, declaration: object, venue_id: object, account: object
    ) -> Result[CapabilityDiscovery]:
        """Validate the wiring and build a :class:`CapabilityDiscovery`, value-or-refusal.

        The declaration is required at construction (the fixed wiring order's first
        phase); the account must belong to the venue, or the ``(VenueId, account)`` key
        would name a binding that cannot exist (CT-03; DEC-0107). The profile is attached
        later through :meth:`observe`.
        """
        if not isinstance(declaration, CapabilityDeclaration):
            return _invalid(
                "declaration",
                "the capability declaration is present at construction (the fixed wiring order)",
                given=repr(declaration),
            )
        if not isinstance(venue_id, VenueId) or venue_id.value.strip() == "":
            return _invalid("venue_id", "discovery targets a valid VenueId", given=repr(venue_id))
        if not isinstance(account, Account):
            return _invalid("account", "discovery targets a valid Account", given=repr(account))
        if account.venue != venue_id:
            return _invalid(
                "account",
                "the account does not belong to this venue; the (VenueId, account) key "
                "would name a binding that cannot exist",
                venue=venue_id.value,
                account_venue=account.venue.value,
            )
        return Ok(cls(declaration=declaration, venue_id=venue_id, account=account))

    @property
    def profile_present(self) -> bool:
        """Whether the venue-observation profile has been attached (post-connect)."""
        return self.profile is not None

    def observe(self, profile: object) -> Result[CapabilityDiscovery]:
        """Attach the post-connect venue-observation profile, returning a new discovery.

        The profile must be a :class:`~qmf.venue.observation.VenueObservationProfile` for
        this discovery's own ``(VenueId, account)`` — a profile for a different binding is
        an ``invalid input`` refusal. Re-observing with a later profile (the continuous
        monitor appending facts) is allowed and returns a new discovery (DEC-0138).
        """
        if not isinstance(profile, VenueObservationProfile):
            return _invalid(
                "profile",
                "the second artifact is a per-(VenueId, account) VenueObservationProfile",
                given=repr(profile),
            )
        if profile.venue_id != self.venue_id or profile.account != self.account:
            return _invalid(
                "profile",
                "the venue-observation profile is for a different (VenueId, account) than "
                "this discovery",
                discovery_venue=self.venue_id.value,
                profile_venue=profile.venue_id.value,
            )
        return Ok(replace(self, profile=profile))

    def require_ready_for_command(self) -> Result[bool]:
        """The gate a command dispatcher reads before the first command (SC-09; DEC-0138).

        The declaration is present by construction; this asserts the second half of the
        fixed wiring order — the venue-observation profile must exist before the first
        command. No profile is an ``unavailable dependency`` refusal.
        """
        if self.profile is None:
            return _unavailable(
                "venue_observation_profile",
                "the venue-observation profile must exist before the first command; it is produced "
                "post-connect by the first-connection verification suite",
                venue=self.venue_id.value,
                account=self.account.account_id,
            )
        return Ok(True)

    def require_evidence(self, evidence_class: object) -> Result[bool]:
        """The verify-or-refuse gate before an evidence-bearing decode (FM-6; DEC-0138).

        No profile is an ``unavailable dependency`` refusal — a measured-at-connection
        capability consumed before its profile exists (SC-09, AR-45). With a profile, the
        profile's own gate applies: ``verified`` is ``Ok(True)``, an ``unverified`` or
        absent check is an ``unavailable dependency`` refusal, and a ``refused`` check —
        a measured-but-unverified capability consumed in evidence-bearing work — is a
        ``policy rejection`` refusal (never silently governed; DEC-0138, DEC-0140).
        """
        if self.profile is None:
            resolved = _coerce(VenueEvidenceClass, evidence_class)
            return _unavailable(
                "venue_observation_profile",
                "the venue-observation profile must exist before any evidence-bearing decode; a "
                "measured-at-connection capability is unavailable until the profile supplies it",
                evidence_class=resolved.value if resolved is not None else repr(evidence_class),
            )
        return self.profile.require_evidence(evidence_class)

    def mint_venue_bar_calendar(
        self, rule_set_version: object, tzdata_version: object
    ) -> Result[CalendarIdentity]:
        """Mint the venue-scoped market-hours calendar identity anchoring venue-native
        ``BarSpec`` (CT-18, AR-46; DEC-0135, DEC-0141).

        No profile is an ``unavailable dependency`` refusal; with a profile, the mint is
        verify-or-refuse — only a *verified* daily boundary mints an identity, and until
        then the venue's daily bars stay ungoverned. The identity is the rule set: the
        venue and the measured UTC minute-of-day, never the demoted 17:00-New-York claim
        (delegated to the profile).
        """
        if self.profile is None:
            return _unavailable(
                "venue_observation_profile",
                "the venue-observation profile must exist before the venue daily boundary "
                "can anchor a market-hours calendar for venue-native BarSpec",
                venue=self.venue_id.value,
            )
        return self.profile.mint_daily_boundary_calendar(rule_set_version, tzdata_version)

    def static_value(self, name: object) -> Result[object]:
        """The static declaration value for ``name``; forwards to the declaration."""
        return self.declaration.static_value(name)

    def close_scope(self, scope: object) -> Result[CloseScope]:
        """Resolve a requested close scope (see :meth:`CapabilityDeclaration.close_scope`)."""
        return self.declaration.close_scope(scope)

    def order_parameter(
        self,
        *,
        order_type: object = None,
        time_in_force: object = None,
    ) -> Result[Mapping[str, str]]:
        """Admit order parameters (see :meth:`CapabilityDeclaration.order_parameter`)."""
        return self.declaration.order_parameter(
            order_type=order_type, time_in_force=time_in_force
        )

    def resolve_error(self, venue_code: object, context: object) -> Result[ErrorMapResolution]:
        """Resolve a venue error code through the pinned error map (see ErrorMap.resolve)."""
        return self.declaration.resolve_error(venue_code, context)


# --- module-level helpers ---------------------------------------------------


def _declared_close_scopes(scopes_field: CapabilityField) -> frozenset[CloseScope]:
    """The set of close scopes a static ``command_scopes`` field declares.

    A measured-at-connection ``command_scopes`` field (no value in the declaration)
    declares no natively supported scope until the profile supplies it, so the set is
    empty and every scope is refused until then.
    """
    if not scopes_field.is_static or scopes_field.value is None:
        return frozenset()
    resolved: set[CloseScope] = set()
    for item in cast("Sequence[object]", scopes_field.value):
        scope = _coerce(CloseScope, item)
        # Every declared token is validated at declaration construction, so it always
        # resolves; the guard is defensive against the unchecked constructor path.
        if scope is not None:  # pragma: no branch
            resolved.add(scope)
    return frozenset(resolved)


def _order_parameter_token(raw: object) -> str | None:
    """Normalize an order-type or time-in-force token from an enum or string."""
    if isinstance(raw, StrEnum):
        token = raw.value
    elif isinstance(raw, str):
        token = raw
    else:
        token = getattr(raw, "value", None)
        if not isinstance(token, str):
            return None
    cleaned = token.strip()
    return cleaned if cleaned else None


def _declared_order_parameters(
    subset_field: CapabilityField,
) -> dict[str, frozenset[str]]:
    """Extract declared ``order_types`` / ``time_in_force`` tokens from the subset field."""
    empty: dict[str, frozenset[str]] = {
        "order_types": frozenset(),
        "time_in_force": frozenset(),
    }
    if not subset_field.is_static or subset_field.value is None:
        return empty
    raw = subset_field.value
    if not isinstance(raw, Mapping):
        return empty
    body = cast("Mapping[str, object]", raw)

    def _tokens(key: str) -> frozenset[str]:
        value = body.get(key)
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
            return frozenset()
        out: set[str] = set()
        for item in cast("Sequence[object]", value):
            token = _order_parameter_token(item)
            if token is not None:
                out.add(token)
        return frozenset(out)

    return {
        "order_types": _tokens("order_types"),
        "time_in_force": _tokens("time_in_force"),
    }


def _validate_command_scopes(scopes_field: CapabilityField) -> TypedRefusal | None:
    """Validate the ``command_scopes`` field's static value at declaration construction.

    When ``command_scopes`` is static its value must be a non-empty sequence of valid
    close-scope tokens — the declaration of "the natively supported close scopes" is
    contract-critical, so a malformed one is refused rather than silently offering no
    scope. A measured-at-connection ``command_scopes`` field is left to the profile.
    """
    if not scopes_field.is_static:
        return None
    value = scopes_field.value
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid(
            "command_scopes",
            "the static command_scopes value is a sequence of close-scope tokens",
            given=repr(value),
        )
    tokens = cast("Sequence[object]", value)
    if len(tokens) == 0:
        return _invalid(
            "command_scopes", "a static command_scopes declaration names at least one close scope"
        )
    for item in tokens:
        if _coerce(CloseScope, item) is None:
            return _invalid(
                "command_scopes",
                "each declared close scope is one of account | account-binding | "
                "instrument-within-binding",
                given=repr(item),
                allowed=[member.value for member in CloseScope],
            )
    return None
