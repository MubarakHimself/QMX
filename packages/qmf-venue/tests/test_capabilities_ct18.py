"""Story 8.4 tests — two-artifact capability discovery wired in a fixed order.

Fixture-driven throughout: a representative cTrader-platform capability declaration is
built as *data* (markings, static values, and the pinned error map), never read from a
host, and venue-observation profiles are assembled directly from measured facts. These
pin every acceptance criterion — the static, credential-free, adapter-version-scoped
declaration carrying the venue protocol artifact identity (tag 91) with an
identity-bearing fingerprint; the fixed wiring order (declaration at construction,
profile before the first command and before any evidence-bearing decode); the
measured-but-unverified policy-rejection; the undeclared-capability and unsupported-close
-scope refusals never widened; the fail-closed error-map default; and the verified daily
boundary anchoring a venue-scoped market-hours calendar for venue-native BarSpec
(FR-022, CT-18, AR-45, AR-46, SC-09; DEC-0135, DEC-0137, DEC-0138, DEC-0141).
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Account,
    AccountRole,
    CalendarIdentity,
    Fingerprint,
    Instant,
    RefusalCategory,
    Result,
    Retryability,
    SecretRef,
    TypedRefusal,
    VenueId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.venue import (
    CapabilityDeclaration,
    CapabilityDiscovery,
    CapabilityField,
    CapabilityFieldName,
    CloseScope,
    ErrorMap,
    ErrorMapResolution,
    ErrorMapRow,
    FieldMarking,
    MeasuredFact,
    ProbeCheck,
    ProbeVerdict,
    ProtoArtifact,
    SubmissionOutcomeClass,
    VenueEvidenceClass,
    VenueObservationProfile,
)

T = TypeVar("T")

_PROTO_TAG = 91
_ADAPTER_VERSION = "ctrader-adapter-1.0.0"
_SESSION_EPOCH = "session-epoch-1"
_CRED_REF_ID = "venue-demo-cred-ref-0001"
_DIGEST = "sha256:" + "a" * 64
_ALT_DIGEST = "sha256:" + "b" * 64
_WALL_NS = 1_724_000_000 * 1_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]) -> TypedRefusal:
    assert is_refusal(result), result
    return result


def _venue() -> VenueId:
    return _ok(VenueId.try_create("venue-ctrader-demo"))


def _account(venue: VenueId | None = None) -> Account:
    anchor = venue if venue is not None else _venue()
    return _ok(Account.try_create("acct-001", anchor, AccountRole.DEMO))


def _instant(value_ns: int = _WALL_NS) -> Instant:
    return _ok(Instant.try_create(value_ns))


def _artifact(release_tag: int = _PROTO_TAG, digest: str = _DIGEST) -> ProtoArtifact:
    return _ok(ProtoArtifact.try_create("openapi-proto-messages", release_tag, digest))


# --- a representative cTrader-platform declaration (test data) ---------------


def _static(name: CapabilityFieldName, value: object) -> CapabilityField:
    return _ok(CapabilityField.static(name, value))


def _measured(name: CapabilityFieldName) -> CapabilityField:
    return _ok(CapabilityField.measured(name))


def _roster(
    *,
    command_scopes: object = None,
) -> list[CapabilityField]:
    """The full CT-18 roster with representative cTrader-platform markings and values."""
    scopes = (
        command_scopes
        if command_scopes is not None
        else ["account", "account-binding", "instrument-within-binding"]
    )
    return [
        _static(CapabilityFieldName.MARKET_DATA_KINDS, ["tick", "bar", "depth"]),
        _static(
            CapabilityFieldName.ORDER_PARAMETER_SUBSET,
            {
                "order_types": ["market", "limit", "stop", "stop-limit"],
                "protective_stop_attachment": "entry-relative",
            },
        ),
        _static(CapabilityFieldName.COMMAND_SCOPES, scopes),
        _static(CapabilityFieldName.ACKNOWLEDGEMENT_MODES, {"place_order": "explicit-event"}),
        _measured(CapabilityFieldName.POSITION_MODEL),
        _static(CapabilityFieldName.SESSION_TOPOLOGY, "two-connections-demo-live-separate-hosts"),
        _static(CapabilityFieldName.THROTTLE_SCOPE, "connection"),
        _static(
            CapabilityFieldName.RATE_LIMITS,
            {"non_historical_per_second": 50, "historical_per_second": 5},
        ),
        _static(
            CapabilityFieldName.SPAN_CAPS_AND_PAGING,
            {"historical_span_cap_ms": 604_800_000, "paging": "hasMore"},
        ),
        _static(
            CapabilityFieldName.TOKEN_LIFECYCLE_CLASS,
            {"access_token_days": 30, "refresh_token": "never-expiring"},
        ),
        _static(CapabilityFieldName.EQUITY_NATIVENESS, "derived"),
        _static(CapabilityFieldName.SERVER_CLOCK_AVAILABILITY, False),
        _static(CapabilityFieldName.INSTRUMENT_METADATA_SURFACE, "full-symbol-record-required"),
        _static(CapabilityFieldName.ATTRIBUTION_LABEL_SUPPORT, False),
        _static(CapabilityFieldName.PROTECTION_PRIMITIVES, ["suspend-new", "drain", "close_all"]),
        _measured(CapabilityFieldName.SETTLEMENT_CURRENCY),
        _measured(CapabilityFieldName.MARGIN_SURFACE),
        _measured(CapabilityFieldName.VALUE_FACTOR_METADATA),
        _static(CapabilityFieldName.RECONCILIATION_LOOKBACK, "do-not-default"),
        _measured(CapabilityFieldName.PROTECTION_CAPABILITIES),
        _static(CapabilityFieldName.COMMAND_ID_MAPPING, {"injective_total": True}),
        _static(
            CapabilityFieldName.FLOAT_TARGET_SCALES,
            {
                "execution_price": "declared-digits",
                "money": "account-money-exponent",
                "market_data": "wire-scale",
            },
        ),
        _static(
            CapabilityFieldName.VERIFICATION_SUITE,
            ["spot-timestamp-unit", "daily-boundary", "bar-basis", "pip-formula", "money-exponent"],
        ),
    ]


def _error_rows() -> list[ErrorMapRow]:
    return [
        _ok(
            ErrorMapRow.try_create(
                "ORDER_REJECTED",
                "place_order",
                RefusalCategory.POLICY_REJECTION,
                Retryability.NO,
                SubmissionOutcomeClass.REJECTED_BY_VENUE,
            )
        ),
        _ok(
            ErrorMapRow.try_create(
                "THROTTLED",
                "place_order",
                RefusalCategory.TRANSIENT_VENUE_FAILURE,
                Retryability.AFTER_CONDITION,
                SubmissionOutcomeClass.UNKNOWN,
                "rate window reopens",
            )
        ),
    ]


def _error_map(version: int = 1) -> ErrorMap:
    return _ok(ErrorMap.try_create(version, _error_rows()))


def _declaration(
    *,
    adapter_version: str = _ADAPTER_VERSION,
    artifact: ProtoArtifact | None = None,
    error_map: ErrorMap | None = None,
    command_scopes: object = None,
) -> CapabilityDeclaration:
    return _ok(
        CapabilityDeclaration.try_create(
            adapter_version,
            artifact if artifact is not None else _artifact(),
            error_map if error_map is not None else _error_map(),
            _roster(command_scopes=command_scopes),
        )
    )


def _fact(
    check: ProbeCheck,
    verdict: ProbeVerdict,
    *,
    measured: dict[str, object] | None = None,
) -> MeasuredFact:
    return _ok(
        MeasuredFact.try_create(
            check,
            verdict,
            _instant(),
            _SESSION_EPOCH,
            _CRED_REF_ID,
            measured=measured,
        )
    )


def _profile(*facts: MeasuredFact) -> VenueObservationProfile:
    profile = _ok(VenueObservationProfile.try_create(_venue(), _account()))
    for fact in facts:
        profile = _ok(profile.with_fact(fact))
    return profile


def _discovery(profile: VenueObservationProfile | None = None) -> CapabilityDiscovery:
    discovery = _ok(CapabilityDiscovery.try_create(_declaration(), _venue(), _account()))
    if profile is not None:
        discovery = _ok(discovery.observe(profile))
    return discovery


# === AC1 — the static capability declaration ================================


def test_declaration_is_static_credential_free_and_adapter_version_scoped() -> None:
    declaration = _declaration()
    assert declaration.adapter_version == _ADAPTER_VERSION
    # Every roster field is present and marked exactly one of the two markings.
    assert set(declaration.fields) == set(CapabilityFieldName)
    for capability_field in declaration.fields.values():
        assert capability_field.marking in (
            FieldMarking.STATIC,
            FieldMarking.MEASURED_AT_CONNECTION,
        )


def test_declaration_carries_the_venue_protocol_artifact_identity_tag_91() -> None:
    declaration = _declaration()
    assert declaration.venue_protocol_artifact.release_tag == _PROTO_TAG
    identity = declaration.fp1_identity()
    artifact_identity = identity["venue_protocol_artifact"]
    assert isinstance(artifact_identity, dict)
    assert artifact_identity["release_tag"] == _PROTO_TAG


def test_declaration_fingerprint_is_identity_bearing_and_stable() -> None:
    one = _declaration().fingerprint()
    two = _declaration().fingerprint()
    assert isinstance(_ok(one), Fingerprint)
    # Two builds of the same declaration fingerprint identically (identity, not occurrence).
    assert _ok(one).value == _ok(two).value
    # The fingerprint over the declaration value equals the direct fingerprint of it.
    assert _ok(fingerprint(_declaration())).value == _ok(one).value


def test_declaration_fingerprint_moves_when_the_protocol_tag_changes() -> None:
    base = _ok(_declaration().fingerprint())
    changed = _ok(_declaration(artifact=_artifact(release_tag=92)).fingerprint())
    assert base.value != changed.value


def test_declaration_fingerprint_moves_when_the_descriptor_digest_changes() -> None:
    base = _ok(_declaration().fingerprint())
    changed = _ok(_declaration(artifact=_artifact(digest=_ALT_DIGEST)).fingerprint())
    assert base.value != changed.value


def test_declaration_fingerprint_moves_when_the_error_map_changes() -> None:
    base = _ok(_declaration().fingerprint())
    changed = _ok(_declaration(error_map=_error_map(version=2)).fingerprint())
    assert base.value != changed.value


def test_declaration_refuses_an_incomplete_roster() -> None:
    partial = _roster()[:-1]  # drop the last roster field
    refusal = _refusal(
        CapabilityDeclaration.try_create(_ADAPTER_VERSION, _artifact(), _error_map(), partial)
    )
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "fields"
    missing = refusal.context["missing"]
    assert isinstance(missing, tuple)  # refusal context deep-freezes lists to tuples
    assert "verification_suite" in missing


def test_declaration_refuses_a_duplicate_field() -> None:
    doubled = [*_roster(), _static(CapabilityFieldName.THROTTLE_SCOPE, "account")]
    refusal = _refusal(
        CapabilityDeclaration.try_create(_ADAPTER_VERSION, _artifact(), _error_map(), doubled)
    )
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["name"] == "throttle_scope"


def test_declaration_refuses_a_blank_adapter_version() -> None:
    refusal = _refusal(CapabilityDeclaration.try_create("  ", _artifact(), _error_map(), _roster()))
    assert refusal.context["field"] == "adapter_version"


def test_declaration_refuses_a_non_artifact_protocol_identity() -> None:
    refusal = _refusal(
        CapabilityDeclaration.try_create(_ADAPTER_VERSION, object(), _error_map(), _roster())
    )
    assert refusal.context["field"] == "venue_protocol_artifact"


def test_declaration_refuses_a_non_error_map() -> None:
    refusal = _refusal(
        CapabilityDeclaration.try_create(_ADAPTER_VERSION, _artifact(), object(), _roster())
    )
    assert refusal.context["field"] == "error_map"


def test_declaration_refuses_non_sequence_fields() -> None:
    refusal = _refusal(
        CapabilityDeclaration.try_create(_ADAPTER_VERSION, _artifact(), _error_map(), "fields")
    )
    assert refusal.context["field"] == "fields"


def test_declaration_refuses_a_non_field_item() -> None:
    refusal = _refusal(
        CapabilityDeclaration.try_create(
            _ADAPTER_VERSION, _artifact(), _error_map(), [*_roster(), object()]
        )
    )
    assert refusal.context["field"] == "fields"


def test_static_field_refuses_a_binary_float_value() -> None:
    # The declaration is identity-bearing, so a binary float can never enter it (DEC-0105).
    refusal = _refusal(CapabilityField.static(CapabilityFieldName.RATE_LIMITS, 3.14))
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "value"


def test_static_field_refuses_a_credential_value() -> None:
    # Credential-free: a SecretRef is not fp1-clean identity content and never serializes.
    secret_ref = _ok(SecretRef.try_create(_CRED_REF_ID))
    refusal = _refusal(
        CapabilityField.static(CapabilityFieldName.TOKEN_LIFECYCLE_CLASS, secret_ref)
    )
    assert refusal.category is RefusalCategory.INVALID_INPUT


def test_static_field_refuses_a_none_value() -> None:
    refusal = _refusal(CapabilityField.static(CapabilityFieldName.THROTTLE_SCOPE, None))
    assert refusal.context["field"] == "value"


def test_field_refuses_a_non_roster_name() -> None:
    assert _refusal(CapabilityField.static("not-a-field", "x")).context["field"] == "name"
    assert _refusal(CapabilityField.measured("not-a-field")).context["field"] == "name"


def test_measured_field_carries_no_value() -> None:
    capability_field = _measured(CapabilityFieldName.SETTLEMENT_CURRENCY)
    assert capability_field.marking is FieldMarking.MEASURED_AT_CONNECTION
    assert capability_field.value is None
    assert capability_field.is_static is False
    # A measured field's fp1 identity omits the value key (never a null; DEC-0108).
    assert "value" not in capability_field.fp1_identity()


def test_static_field_value_is_deep_frozen_against_caller_mutation() -> None:
    mutable = ["tick"]
    capability_field = _static(CapabilityFieldName.MARKET_DATA_KINDS, mutable)
    mutable.append("mutated")
    assert capability_field.value == ("tick",)


def test_declaration_refuses_malformed_command_scopes() -> None:
    refusal = _refusal(
        CapabilityDeclaration.try_create(
            _ADAPTER_VERSION, _artifact(), _error_map(), _roster(command_scopes="account")
        )
    )
    assert refusal.context["field"] == "command_scopes"


def test_declaration_refuses_empty_command_scopes() -> None:
    refusal = _refusal(
        CapabilityDeclaration.try_create(
            _ADAPTER_VERSION, _artifact(), _error_map(), _roster(command_scopes=[])
        )
    )
    assert refusal.context["field"] == "command_scopes"


def test_declaration_refuses_an_unknown_close_scope_token() -> None:
    refusal = _refusal(
        CapabilityDeclaration.try_create(
            _ADAPTER_VERSION, _artifact(), _error_map(), _roster(command_scopes=["planet"])
        )
    )
    assert refusal.context["field"] == "command_scopes"


# === AC2 — the fixed wiring order ===========================================


def test_discovery_requires_the_declaration_at_construction() -> None:
    refusal = _refusal(CapabilityDiscovery.try_create(object(), _venue(), _account()))
    assert refusal.context["field"] == "declaration"


def test_discovery_refuses_an_account_that_does_not_belong_to_the_venue() -> None:
    other = _ok(VenueId.try_create("venue-other"))
    refusal = _refusal(CapabilityDiscovery.try_create(_declaration(), _venue(), _account(other)))
    assert refusal.context["field"] == "account"


def test_discovery_refuses_a_bad_venue_or_account() -> None:
    assert (
        _refusal(CapabilityDiscovery.try_create(_declaration(), object(), _account())).context[
            "field"
        ]
        == "venue_id"
    )
    assert (
        _refusal(CapabilityDiscovery.try_create(_declaration(), _venue(), object())).context[
            "field"
        ]
        == "account"
    )


def test_command_is_refused_until_the_profile_exists() -> None:
    discovery = _discovery()
    assert discovery.profile_present is False
    refusal = _refusal(discovery.require_ready_for_command())
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refusal.context["field"] == "venue_observation_profile"


def test_evidence_decode_is_refused_until_the_profile_exists() -> None:
    refusal = _refusal(_discovery().require_evidence(VenueEvidenceClass.SPOT))
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refusal.context["evidence_class"] == VenueEvidenceClass.SPOT.value


def test_profile_before_first_command_opens_the_command_gate() -> None:
    verified = _fact(ProbeCheck.SPOT_TIMESTAMP_UNIT, ProbeVerdict.VERIFIED, measured={"unit": "ms"})
    discovery = _discovery(_profile(verified))
    assert discovery.profile_present is True
    assert _ok(discovery.require_ready_for_command()) is True


def test_observe_refuses_a_non_profile() -> None:
    refusal = _refusal(_discovery().observe(object()))
    assert refusal.context["field"] == "profile"


def test_observe_refuses_a_profile_for_a_different_binding() -> None:
    other_venue = _ok(VenueId.try_create("venue-other"))
    other_account = _account(other_venue)
    other_profile = _ok(VenueObservationProfile.try_create(other_venue, other_account))
    refusal = _refusal(_discovery().observe(other_profile))
    assert refusal.context["field"] == "profile"


def test_reobserving_with_a_later_profile_returns_a_new_discovery() -> None:
    first = _profile(_fact(ProbeCheck.SPOT_TIMESTAMP_UNIT, ProbeVerdict.UNVERIFIED))
    discovery = _discovery(first)
    later = _ok(
        first.with_fact(
            _fact(ProbeCheck.SPOT_TIMESTAMP_UNIT, ProbeVerdict.VERIFIED, measured={"unit": "ms"})
        )
    )
    updated = _ok(discovery.observe(later))
    assert updated is not discovery
    assert _ok(updated.require_evidence(VenueEvidenceClass.SPOT)) is True


# === AC3 — measured-but-unverified in evidence-bearing work =================


def test_verified_check_makes_the_evidence_class_available() -> None:
    profile = _profile(
        _fact(ProbeCheck.SPOT_TIMESTAMP_UNIT, ProbeVerdict.VERIFIED, measured={"unit": "ms"})
    )
    assert _ok(_discovery(profile).require_evidence(VenueEvidenceClass.SPOT)) is True


def test_refused_check_is_a_policy_rejection_in_evidence_bearing_work() -> None:
    # A measured-but-unverified capability consumed in evidence-bearing work → policy rejection.
    profile = _profile(_fact(ProbeCheck.BAR_BASIS, ProbeVerdict.REFUSED))
    refusal = _refusal(_discovery(profile).require_evidence(VenueEvidenceClass.BAR))
    assert refusal.category is RefusalCategory.POLICY_REJECTION


def test_unverified_check_is_an_unavailable_dependency() -> None:
    profile = _profile(_fact(ProbeCheck.SPOT_TIMESTAMP_UNIT, ProbeVerdict.UNVERIFIED))
    refusal = _refusal(_discovery(profile).require_evidence(VenueEvidenceClass.SPOT))
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_profile_is_append_only_with_supersedes_edges() -> None:
    first = _fact(ProbeCheck.DAILY_BOUNDARY, ProbeVerdict.UNVERIFIED)
    profile = _profile(first)
    second = _fact(
        ProbeCheck.DAILY_BOUNDARY, ProbeVerdict.VERIFIED, measured={"utc_minute_of_day": 0}
    )
    updated = _ok(profile.with_fact(second))
    boundary_facts = updated.facts_for(ProbeCheck.DAILY_BOUNDARY)
    assert len(boundary_facts) == 2  # append-only: the first fact is never rewritten
    assert boundary_facts[0].supersedes is None
    assert boundary_facts[1].supersedes == 0  # supersedes edge points at the prior fact


def test_measured_fact_is_never_identity_bearing_downstream() -> None:
    # The venue-observation profile is occurrence/provenance only; a fact never enters fp1.
    fact = _fact(ProbeCheck.MONEY_EXPONENT, ProbeVerdict.VERIFIED, measured={"money_digits": 2})
    assert is_refusal(fingerprint(fact))


# === AC4 — undeclared capability and unsupported close scope ================


def test_undeclared_capability_is_an_unsupported_capability_refusal() -> None:
    refusal = _refusal(_declaration().field_for("teleport_position"))
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_static_value_of_an_undeclared_capability_is_unsupported() -> None:
    refusal = _refusal(_discovery().static_value("teleport_position"))
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_static_value_of_a_measured_field_is_unavailable_not_defaulted() -> None:
    # A measured-at-connection value is absent from the static declaration.
    refusal = _refusal(_declaration().static_value(CapabilityFieldName.SETTLEMENT_CURRENCY))
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_static_value_of_a_static_field_returns_the_declared_value() -> None:
    assert _ok(_discovery().static_value(CapabilityFieldName.THROTTLE_SCOPE)) == "connection"


def test_declared_close_scope_resolves() -> None:
    assert (
        _ok(_discovery().close_scope("instrument-within-binding"))
        is CloseScope.INSTRUMENT_WITHIN_BINDING
    )


def test_unsupported_close_scope_is_refused_never_widened() -> None:
    # A declaration offering only 'account' must refuse a finer scope, never widen to account.
    discovery = _ok(
        CapabilityDiscovery.try_create(
            _declaration(command_scopes=["account"]), _venue(), _account()
        )
    )
    refusal = _refusal(discovery.close_scope("instrument-within-binding"))
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refusal.context["requested"] == "instrument-within-binding"
    assert refusal.context["declared"] == ("account",)  # deep-frozen to a tuple


def test_unknown_close_scope_token_is_unsupported() -> None:
    refusal = _refusal(_discovery().close_scope("whole-galaxy"))
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_non_string_close_scope_is_unsupported() -> None:
    refusal = _refusal(_discovery().close_scope(123))
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_measured_command_scopes_declares_no_scope_until_the_profile_supplies_it() -> None:
    # If command_scopes is measured-at-connection, the declaration offers no native scope,
    # so every scope is refused until the venue-observation profile supplies it.
    fields = [f for f in _roster() if f.name is not CapabilityFieldName.COMMAND_SCOPES]
    fields.append(_measured(CapabilityFieldName.COMMAND_SCOPES))
    declaration = _ok(
        CapabilityDeclaration.try_create(_ADAPTER_VERSION, _artifact(), _error_map(), fields)
    )
    refusal = _refusal(declaration.close_scope("account"))
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY


# === AC5 — the error map and the fail-closed default ========================


def test_mapped_code_reads_rejected_by_venue_only_where_declared() -> None:
    resolution = _ok(_discovery().resolve_error("ORDER_REJECTED", "place_order"))
    assert isinstance(resolution, ErrorMapResolution)
    assert resolution.mapped is True
    assert resolution.outcome_class is SubmissionOutcomeClass.REJECTED_BY_VENUE
    assert resolution.refusal_category is RefusalCategory.POLICY_REJECTION
    assert resolution.alarm is False


def test_the_same_code_in_a_different_context_is_unmapped() -> None:
    # A code reads rejected-by-venue only in the (code, context) the table declares.
    resolution = _ok(_discovery().resolve_error("ORDER_REJECTED", "cancel_order"))
    assert resolution.mapped is False
    assert resolution.outcome_class is SubmissionOutcomeClass.UNKNOWN


def test_unmapped_code_takes_the_fail_closed_default() -> None:
    resolution = _ok(_discovery().resolve_error("MYSTERY_9000", "place_order"))
    assert resolution.mapped is False
    assert resolution.outcome_class is SubmissionOutcomeClass.UNKNOWN
    assert resolution.refusal_category is RefusalCategory.TRANSIENT_VENUE_FAILURE
    assert resolution.retryability is Retryability.NO
    assert resolution.alarm is True


def test_mapped_after_condition_row_carries_its_descriptor() -> None:
    resolution = _ok(_discovery().resolve_error("THROTTLED", "place_order"))
    assert resolution.retryability is Retryability.AFTER_CONDITION
    assert resolution.after_condition == "rate window reopens"
    assert resolution.outcome_class is SubmissionOutcomeClass.UNKNOWN


def test_error_map_resolve_refuses_a_blank_code_or_context() -> None:
    assert _refusal(_error_map().resolve("  ", "place_order")).context["field"] == "venue_code"
    assert _refusal(_error_map().resolve("CODE", "  ")).context["field"] == "context"


def test_error_map_refuses_a_bad_version() -> None:
    assert _refusal(ErrorMap.try_create(0, _error_rows())).context["field"] == "version"
    assert _refusal(ErrorMap.try_create(True, _error_rows())).context["field"] == "version"


def test_error_map_refuses_non_sequence_rows() -> None:
    assert _refusal(ErrorMap.try_create(1, "rows")).context["field"] == "rows"


def test_error_map_refuses_a_non_row_item() -> None:
    assert _refusal(ErrorMap.try_create(1, [object()])).context["field"] == "rows"


def test_error_map_refuses_a_duplicate_key() -> None:
    rows = _error_rows()
    refusal = _refusal(ErrorMap.try_create(1, [*rows, rows[0]]))
    assert refusal.context["field"] == "rows"
    assert refusal.context["venue_code"] == "ORDER_REJECTED"


def test_error_map_row_refuses_bad_enums() -> None:
    assert (
        _refusal(
            ErrorMapRow.try_create(
                "C", "ctx", "not-a-category", Retryability.NO, SubmissionOutcomeClass.UNKNOWN
            )
        ).context["field"]
        == "refusal_category"
    )
    assert (
        _refusal(
            ErrorMapRow.try_create(
                "C", "ctx", RefusalCategory.INVALID_INPUT, "maybe", SubmissionOutcomeClass.UNKNOWN
            )
        ).context["field"]
        == "retryability"
    )
    assert (
        _refusal(
            ErrorMapRow.try_create(
                "C", "ctx", RefusalCategory.INVALID_INPUT, Retryability.NO, "half"
            )
        ).context["field"]
        == "outcome_class"
    )


def test_error_map_row_refuses_a_blank_code_or_context() -> None:
    assert (
        _refusal(
            ErrorMapRow.try_create(
                " ",
                "ctx",
                RefusalCategory.INVALID_INPUT,
                Retryability.NO,
                SubmissionOutcomeClass.UNKNOWN,
            )
        ).context["field"]
        == "venue_code"
    )
    assert (
        _refusal(
            ErrorMapRow.try_create(
                "C",
                " ",
                RefusalCategory.INVALID_INPUT,
                Retryability.NO,
                SubmissionOutcomeClass.UNKNOWN,
            )
        ).context["field"]
        == "context"
    )


def test_error_map_row_enforces_the_after_condition_pairing() -> None:
    # after-condition retryability requires a descriptor.
    missing = _refusal(
        ErrorMapRow.try_create(
            "C",
            "ctx",
            RefusalCategory.TRANSIENT_VENUE_FAILURE,
            Retryability.AFTER_CONDITION,
            SubmissionOutcomeClass.UNKNOWN,
        )
    )
    assert missing.context["field"] == "after_condition"
    # a descriptor without after-condition retryability is refused too.
    spurious = _refusal(
        ErrorMapRow.try_create(
            "C",
            "ctx",
            RefusalCategory.TRANSIENT_VENUE_FAILURE,
            Retryability.NO,
            SubmissionOutcomeClass.UNKNOWN,
            "descriptor",
        )
    )
    assert spurious.context["field"] == "after_condition"


# === AC6 — daily boundary anchors a venue-scoped market-hours calendar ======


def _verified_boundary_profile(minute: int = 0) -> VenueObservationProfile:
    return _profile(
        _fact(
            ProbeCheck.DAILY_BOUNDARY,
            ProbeVerdict.VERIFIED,
            measured={"utc_minute_of_day": minute, "bars": 3},
        )
    )


def test_verified_boundary_anchors_a_venue_scoped_calendar_identity() -> None:
    discovery = _discovery(_verified_boundary_profile(minute=0))
    calendar = _ok(discovery.mint_venue_bar_calendar("v1", "2025.2"))
    assert isinstance(calendar, CalendarIdentity)
    # Identity is the rule set: the venue and the MEASURED minute, never 17:00-New-York.
    assert calendar.rule_set == "venue-daily::venue-ctrader-demo::utc_minute_of_day=0"
    assert calendar.rule_set_version == "v1"
    assert calendar.tzdata_version == "2025.2"


def test_calendar_mint_is_refused_until_the_profile_exists() -> None:
    refusal = _refusal(_discovery().mint_venue_bar_calendar("v1", "2025.2"))
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_calendar_mint_is_refused_until_the_boundary_is_verified() -> None:
    unverified = _profile(_fact(ProbeCheck.DAILY_BOUNDARY, ProbeVerdict.UNVERIFIED))
    refusal = _refusal(_discovery(unverified).mint_venue_bar_calendar("v1", "2025.2"))
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_failed_bar_basis_reconciliation_refuses_bar_evidence() -> None:
    profile = _profile(_fact(ProbeCheck.BAR_BASIS, ProbeVerdict.REFUSED))
    refusal = _refusal(_discovery(profile).require_evidence(VenueEvidenceClass.BAR))
    assert refusal.category is RefusalCategory.POLICY_REJECTION


def test_absent_money_exponent_refuses_the_money_decode() -> None:
    # An absent money exponent is recorded UNVERIFIED — the money decode stays unavailable.
    profile = _profile(_fact(ProbeCheck.MONEY_EXPONENT, ProbeVerdict.UNVERIFIED))
    refusal = _refusal(_discovery(profile).require_evidence(VenueEvidenceClass.MONEY_DECODE))
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
