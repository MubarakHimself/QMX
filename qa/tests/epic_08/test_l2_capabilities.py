"""L2 contract tests — CT-18 venue capability discovery (Story 8.4).

Oracle: docs/contracts/ct-18-venue-capabilities.yaml (verbatim invariants) and the
Story 8.4 acceptance criteria. Each test asserts what the contract demands; a failure
is a finding, never a reason to weaken the assertion.

Covers QA-E08-L2-001..005.
"""

from __future__ import annotations

from qmf.core import RefusalCategory, Retryability, is_ok, is_refusal
from qmf.venue import (
    CapabilityDiscovery,
    CapabilityFieldName,
    FieldMarking,
    MeasuredFact,
    ProbeCheck,
    ProbeVerdict,
    SubmissionOutcomeClass,
    VenueEvidenceClass,
    VenueObservationProfile,
)

import _helpers as H


# --- QA-E08-L2-001 — two-artifact split (P1) --------------------------------


def test_l2_001_declaration_static_credential_free_tag91_identity_bearing():
    """CT-18: the declaration is static, adapter-version-scoped, carries tag-91
    protocol identity, marks every roster field static|measured-at-connection, and
    its fingerprint is identity-bearing (moves on a static change)."""
    decl = H.build_declaration()

    # Every CT-18 roster field is covered exactly once, each marked static|measured.
    assert set(decl.fields) == set(CapabilityFieldName)
    for field in decl.fields.values():
        assert field.marking in (FieldMarking.STATIC, FieldMarking.MEASURED_AT_CONNECTION)

    # Venue protocol artifact identity carries the pinned Spotware release tag 91.
    assert decl.venue_protocol_artifact.release_tag == 91

    # Fingerprint is identity-bearing: identical declarations agree; a changed static
    # value (a different pinned tag) moves the identity.
    fp = decl.fingerprint()
    assert is_ok(fp)
    assert H.ok(H.build_declaration().fingerprint()) == fp.value
    other_tag = H.build_declaration(proto=H.build_proto_artifact(tag=92))
    assert H.ok(other_tag.fingerprint()) != fp.value


def test_l2_001_declaration_identity_excludes_measured_values():
    """CT-18: a measured-at-connection field contributes only name+marking to the
    declaration identity — a measured value never enters (or splits) it."""
    decl = H.build_declaration()
    content = dict(decl.fp1_identity())
    by_name = {f["name"]: f for f in content["fields"]}
    for name in H.DEFAULT_MEASURED:
        entry = by_name[name.value]
        assert entry["marking"] == FieldMarking.MEASURED_AT_CONNECTION.value
        assert "value" not in entry, f"measured field {name.value} leaked a value into identity"


def test_l2_001_profile_is_occurrence_only_append_only_with_supersedes():
    """CT-18: the venue-observation profile is per-(VenueId, account), append-only
    with supersedes edges, occurrence/provenance-only and never identity-bearing."""
    v = H.mk_venue()
    a = H.mk_account(v)
    profile = H.ok(VenueObservationProfile.try_create(v, a))

    # Occurrence/provenance-only: never identity-bearing downstream.
    assert not hasattr(MeasuredFact, "fp1_identity")
    assert not hasattr(VenueObservationProfile, "fp1_identity")

    # Append-only with a supersedes edge wired to the prior fact of the same check.
    f1 = H.ok(
        MeasuredFact.try_create(
            ProbeCheck.MONEY_EXPONENT, ProbeVerdict.VERIFIED, H.mk_instant(1), "se-1", "sref-1",
            measured={"money_digits": 2},
        )
    )
    f2 = H.ok(
        MeasuredFact.try_create(
            ProbeCheck.MONEY_EXPONENT, ProbeVerdict.VERIFIED, H.mk_instant(2), "se-1", "sref-1",
            measured={"money_digits": 3},
        )
    )
    p1 = H.ok(profile.with_fact(f1))
    p2 = H.ok(p1.with_fact(f2))
    facts = p2.facts_for(ProbeCheck.MONEY_EXPONENT)
    assert len(facts) == 2
    assert facts[0].supersedes is None
    assert facts[1].supersedes == 0  # append-only edge to the superseded fact
    # History is not rewritten: the original profile still has one fact.
    assert len(profile.facts) == 0


# --- QA-E08-L2-002 — error-map fail-closed default (P0) ---------------------


def test_l2_002_unmapped_code_fails_closed_to_unknown_plus_alarm():
    """CT-18: an unmapped (venue code, context) pair resolves fail-closed to
    (transient-venue-failure, retryable=no, UNKNOWN) plus an alarm."""
    decl = H.build_declaration()
    res = decl.resolve_error("NEVER-MAPPED-CODE", "place_order")
    assert is_ok(res)
    r = res.value
    assert r.mapped is False
    assert r.outcome_class is SubmissionOutcomeClass.UNKNOWN
    assert r.refusal_category is RefusalCategory.TRANSIENT_VENUE_FAILURE
    assert r.retryability is Retryability.NO
    assert r.alarm is True


def test_l2_002_rejected_only_where_a_row_declares_that_class():
    """CT-18: a venue code reads as rejected-by-venue ONLY where a pinned row declares
    it; category alone never implies retryability."""
    decl = H.build_declaration()  # error map has one REJECTED row + one UNKNOWN row
    rejected = decl.resolve_error("ORDER-REJECTED", "place_order")
    assert is_ok(rejected)
    assert rejected.value.outcome_class is SubmissionOutcomeClass.REJECTED_BY_VENUE
    assert rejected.value.mapped is True

    mapped_unknown = decl.resolve_error("TEMP-GLITCH", "place_order")
    assert is_ok(mapped_unknown)
    assert mapped_unknown.value.outcome_class is SubmissionOutcomeClass.UNKNOWN

    # Same code in an undeclared context is NOT rejected — it fails closed to UNKNOWN.
    other_ctx = decl.resolve_error("ORDER-REJECTED", "cancel_order")
    assert is_ok(other_ctx)
    assert other_ctx.value.outcome_class is SubmissionOutcomeClass.UNKNOWN
    assert other_ctx.value.mapped is False


# --- QA-E08-L2-003 — money/dependency nullability (P0) ----------------------


def test_l2_003_measured_at_connection_value_absent_from_declaration():
    """CT-18: a measured-at-connection capability (value factor, settlement currency)
    is absent from the static declaration — reading it as a static value is an
    unavailable-dependency refusal, never a silent default."""
    decl = H.build_declaration()
    for name in (
        CapabilityFieldName.VALUE_FACTOR_METADATA,
        CapabilityFieldName.SETTLEMENT_CURRENCY,
    ):
        res = decl.static_value(name)
        assert is_refusal(res), f"{name.value} should be unavailable as a static value"
        assert res.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_l2_003_absent_money_exponent_and_absent_check_refuse_via_profile():
    """CT-18 nullability: an unmeasured/unverified capability's evidence class is an
    unavailable-dependency refusal (never a default); a *refused* verify-or-refuse
    check consumed in evidence-bearing work is a policy-rejection refusal."""
    v = H.mk_venue()
    a = H.mk_account(v)
    profile = H.ok(VenueObservationProfile.try_create(v, a))

    # No money-exponent fact recorded at all -> unavailable (never a default to 2).
    absent = profile.require_evidence(VenueEvidenceClass.MONEY_DECODE)
    assert is_refusal(absent)
    assert absent.category is RefusalCategory.UNAVAILABLE_DEPENDENCY

    # An UNVERIFIED money exponent stays unavailable (no value defaulted).
    unverified = H.ok(
        MeasuredFact.try_create(
            ProbeCheck.MONEY_EXPONENT, ProbeVerdict.UNVERIFIED, H.mk_instant(1), "se", "sref"
        )
    )
    p_unv = H.ok(profile.with_fact(unverified))
    assert is_refusal(p_unv.require_evidence(VenueEvidenceClass.MONEY_DECODE))
    assert p_unv.require_evidence(VenueEvidenceClass.MONEY_DECODE).category is (
        RefusalCategory.UNAVAILABLE_DEPENDENCY
    )

    # A REFUSED bar-basis check consumed in evidence-bearing work is policy-rejection.
    refused = H.ok(
        MeasuredFact.try_create(
            ProbeCheck.BAR_BASIS, ProbeVerdict.REFUSED, H.mk_instant(2), "se", "sref"
        )
    )
    p_ref = H.ok(profile.with_fact(refused))
    bar = p_ref.require_evidence(VenueEvidenceClass.BAR)
    assert is_refusal(bar)
    assert bar.category is RefusalCategory.POLICY_REJECTION


# --- QA-E08-L2-004 — fixed wiring order (P1) --------------------------------


def test_l2_004_measured_capability_before_profile_is_unavailable():
    """CT-18: a measured-at-connection capability consumed before its venue-observation
    profile exists is an unavailable-dependency refusal (fixed wiring order)."""
    v = H.mk_venue()
    a = H.mk_account(v)
    discovery = H.ok(CapabilityDiscovery.try_create(H.build_declaration(), v, a))
    assert discovery.profile_present is False

    # Before the profile: not ready for command, and evidence is unavailable.
    ready = discovery.require_ready_for_command()
    assert is_refusal(ready) and ready.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    ev = discovery.require_evidence(VenueEvidenceClass.MONEY_DECODE)
    assert is_refusal(ev) and ev.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_l2_004_measured_but_refused_capability_is_policy_rejection():
    """CT-18: a measured-but-unverified capability consumed in evidence-bearing work is
    a policy-rejection refusal (delegated to the profile's verify-or-refuse gate)."""
    v = H.mk_venue()
    a = H.mk_account(v)
    profile = H.ok(VenueObservationProfile.try_create(v, a))
    refused = H.ok(
        MeasuredFact.try_create(
            ProbeCheck.BAR_BASIS, ProbeVerdict.REFUSED, H.mk_instant(1), "se", "sref"
        )
    )
    profile = H.ok(profile.with_fact(refused))
    discovery = H.ok(
        H.ok(CapabilityDiscovery.try_create(H.build_declaration(), v, a)).observe(profile)
    )
    res = discovery.require_evidence(VenueEvidenceClass.BAR)
    assert is_refusal(res)
    assert res.category is RefusalCategory.POLICY_REJECTION


# --- QA-E08-L2-005 — unsupported invocation, never widened (P1) -------------


def test_l2_005_undeclared_capability_is_unsupported():
    """CT-18: invoking a name outside the CT-18 roster is an unsupported-capability
    refusal — never emulated."""
    decl = H.build_declaration()
    res = decl.field_for("no-such-capability")
    assert is_refusal(res)
    assert res.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_l2_005_unsupported_close_scope_is_refused_never_widened():
    """CT-18: an unsupported close scope is refused, never emulated at a wider scope."""
    # A declaration that natively supports only the narrowest scope.
    decl = H.build_declaration(command_scopes=["instrument-within-binding"])
    # A wider scope the venue does not declare is refused (never widened to it).
    wide = decl.close_scope("account")
    assert is_refusal(wide)
    assert wide.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    # An unknown scope token is likewise unsupported.
    unknown = decl.close_scope("galaxy-wide")
    assert is_refusal(unknown)
    assert unknown.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    # The natively-declared scope resolves.
    assert is_ok(decl.close_scope("instrument-within-binding"))
