"""Story 24.2 / D008 — CT-18 verify-or-refuse at connection time."""

from __future__ import annotations

import pytest
from qmf.core import Account, AccountRole, Instant, VenueId, World, is_ok, is_refusal
from qmf.venue.observation import (
    REQUIRED_CONNECTION_CHECKS,
    ProbeCheck,
    ProbeVerdict,
    VenueEvidenceClass,
    evidence_class_for,
)
from qmn.venue import (
    DATA_QUALITY_EVENT_TYPE,
    BindingRevalidationState,
    ConformanceDouble,
    FieldDefectKind,
    VenueClientKind,
    VenueFactVerifier,
    conformance_measured_facts,
    ctrader_static_declaration,
    select_venue_client,
)


def _venue(value: str = "conformance:ctrader-demo") -> VenueId:
    result = VenueId.try_create(value)
    assert is_ok(result)
    return result.value


def _account(venue: VenueId | None = None) -> Account:
    anchor = venue if venue is not None else _venue()
    result = Account.try_create("demo-acct", anchor, AccountRole.DEMO)
    assert is_ok(result)
    return result.value


def _instant(ns: int = 1_700_000_000_000_000_000) -> Instant:
    result = Instant.try_create(ns)
    assert is_ok(result)
    return result.value


def test_required_connection_checks_cover_story_fields() -> None:
    names = {check.value for check in REQUIRED_CONNECTION_CHECKS}
    assert "spot-timestamp-unit" in names
    assert "daily-boundary" in names
    assert "bar-basis" in names
    assert "pip-formula" in names
    assert "money-exponent" in names
    assert "amend-atomicity" in names
    assert "position-model" in names
    assert "pacing-scope" in names
    assert "protective-stop-forms" in names
    for check in REQUIRED_CONNECTION_CHECKS:
        assert evidence_class_for(check) in VenueEvidenceClass


def test_static_declaration_distinct_from_measured_profile() -> None:
    declaration = ctrader_static_declaration()
    assert is_ok(declaration)
    decl = declaration.value
    # Measured roster fields carry no static value.
    measured = decl.fields
    from qmf.venue.capabilities import CapabilityFieldName, FieldMarking

    position = measured[CapabilityFieldName.POSITION_MODEL]
    protection = measured[CapabilityFieldName.PROTECTION_CAPABILITIES]
    assert position.marking is FieldMarking.MEASURED_AT_CONNECTION
    assert protection.marking is FieldMarking.MEASURED_AT_CONNECTION
    static_value = decl.static_value(CapabilityFieldName.POSITION_MODEL)
    assert is_refusal(static_value)

    verifier = VenueFactVerifier.try_create(decl, _venue(), _account())
    assert is_ok(verifier)
    bundle = conformance_measured_facts(received_at=_instant())
    assert is_ok(bundle)
    outcome = verifier.value.verify(bundle.value, received_at=_instant())
    assert is_ok(outcome)
    # Static artifact identity is unchanged by measured facts.
    assert outcome.value.static_declaration is decl
    assert outcome.value.measured_profile is not None
    assert outcome.value.static_declaration is not outcome.value.measured_profile  # type: ignore[comparison-overlap]
    assert outcome.value.command_sequencer_open is True
    assert outcome.value.market_data_recordable is True
    assert outcome.value.journal == ()


def test_conformance_double_verify_capabilities_runs_full_suite() -> None:
    built = ConformanceDouble.try_create(World.LIVE, _venue())
    assert is_ok(built)
    client = built.value
    assert is_ok(client.open_session(_account(client.venue_id)))
    caps = client.verify_capabilities()
    assert is_ok(caps)
    profile = caps.value
    assert profile["verified"] is True
    assert profile["static_declaration_present"] is True
    assert profile["measured_at_connection"] is True
    assert profile["command_sequencer_open"] is True
    assert set(profile["measured_checks"]) == {check.value for check in REQUIRED_CONNECTION_CHECKS}
    assert client.verification is not None
    assert client.verification.command_sequencer_open is True
    for check in REQUIRED_CONNECTION_CHECKS:
        fact = client.verification.require_field(check)
        assert is_ok(fact)
        assert fact.value.verdict is ProbeVerdict.VERIFIED


def test_absent_field_journals_data_quality_and_blocks_sequencer() -> None:
    declaration = ctrader_static_declaration()
    assert is_ok(declaration)
    verifier = VenueFactVerifier.try_create(
        declaration.value, _venue(), _account(), binding_ids=("book-a",)
    )
    assert is_ok(verifier)
    full = conformance_measured_facts(received_at=_instant())
    assert is_ok(full)
    # Drop money exponent — absent required field.
    partial = {
        check: fact
        for check, fact in full.value.facts.items()
        if check is not ProbeCheck.MONEY_EXPONENT
    }
    from qmn.venue import MeasuredFactBundle

    bundle = MeasuredFactBundle.try_create(partial)
    assert is_ok(bundle)
    outcome = verifier.value.verify(bundle.value, received_at=_instant())
    assert is_ok(outcome)
    result = outcome.value
    assert result.command_sequencer_open is False
    assert result.market_data_recordable is True  # spot still safe
    assert ProbeCheck.MONEY_EXPONENT.value in result.defects
    assert result.defects[ProbeCheck.MONEY_EXPONENT.value] is FieldDefectKind.ABSENT
    assert any(event.event_type == DATA_QUALITY_EVENT_TYPE for event in result.journal)
    assert is_refusal(verifier.value.require_command_sequencer(result))
    assert is_refusal(result.require_field(ProbeCheck.MONEY_EXPONENT))
    assert result.bindings["book-a"] is BindingRevalidationState.REFUSED


def test_refused_bar_basis_still_allows_market_data_recording() -> None:
    declaration = ctrader_static_declaration()
    assert is_ok(declaration)
    verifier = VenueFactVerifier.try_create(declaration.value, _venue(), _account())
    assert is_ok(verifier)
    full = conformance_measured_facts(received_at=_instant())
    assert is_ok(full)
    from qmf.venue.observation import MeasuredFact

    refused = MeasuredFact.try_create(
        ProbeCheck.BAR_BASIS,
        ProbeVerdict.REFUSED,
        _instant(),
        "conformance-session",
        "conformance-cred-ref",
        detail="OHLC mismatch",
    )
    assert is_ok(refused)
    facts = dict(full.value.facts)
    facts[ProbeCheck.BAR_BASIS] = refused.value
    from qmn.venue import MeasuredFactBundle

    bundle = MeasuredFactBundle.try_create(facts)
    assert is_ok(bundle)
    outcome = verifier.value.verify(bundle.value, received_at=_instant())
    assert is_ok(outcome)
    result = outcome.value
    assert result.command_sequencer_open is False
    assert result.market_data_recordable is True
    assert result.defects[ProbeCheck.BAR_BASIS.value] is FieldDefectKind.REFUSED
    assert is_refusal(result.require_field(ProbeCheck.BAR_BASIS))
    # Spot remains usable for recording.
    assert is_ok(result.require_field(ProbeCheck.SPOT_TIMESTAMP_UNIT))


def test_broker_fact_drift_retains_prior_and_refuses_bindings() -> None:
    declaration = ctrader_static_declaration()
    assert is_ok(declaration)
    verifier = VenueFactVerifier.try_create(
        declaration.value, _venue(), _account(), binding_ids=("binding-1", "binding-2")
    )
    assert is_ok(verifier)
    first_bundle = conformance_measured_facts(
        received_at=_instant(), utc_minute_of_day=1020, position_model="netting"
    )
    assert is_ok(first_bundle)
    first = verifier.value.verify(first_bundle.value, received_at=_instant())
    assert is_ok(first)
    assert first.value.profile_version == 1
    assert first.value.command_sequencer_open is True

    # Drift: daily boundary minute changes — prior fact retained via supersedes.
    second_bundle = conformance_measured_facts(
        received_at=_instant(1_700_000_000_100_000_000),
        utc_minute_of_day=0,
        position_model="netting",
    )
    assert is_ok(second_bundle)
    second = verifier.value.apply_remeasurement(
        second_bundle.value, received_at=_instant(1_700_000_000_100_000_000), prior=first.value
    )
    assert is_ok(second)
    drifted = second.value
    assert drifted.profile_version == 2
    assert drifted.command_sequencer_open is False
    assert ProbeCheck.DAILY_BOUNDARY.value in drifted.defects
    assert drifted.defects[ProbeCheck.DAILY_BOUNDARY.value] is FieldDefectKind.STALE
    # Prior fact still in profile history (append-only, not silently replaced).
    history = drifted.profile.facts_for(ProbeCheck.DAILY_BOUNDARY)
    assert len(history) == 2
    assert history[0].measured["utc_minute_of_day"] == 1020
    assert history[1].measured["utc_minute_of_day"] == 0
    assert history[1].supersedes == 0 or history[1].supersedes is not None
    assert drifted.bindings["binding-1"] is BindingRevalidationState.NEEDS_REVALIDATION
    assert is_refusal(drifted.binding_state("binding-1"))
    assert any(event.defect is FieldDefectKind.STALE for event in drifted.journal)

    # Revalidate both bindings once drift is acknowledged — sequencer reopens.
    step = verifier.value.revalidate_binding(drifted, "binding-1")
    assert is_ok(step)
    step2 = verifier.value.revalidate_binding(step.value, "binding-2")
    assert is_ok(step2)
    assert step2.value.command_sequencer_open is True
    assert step2.value.bindings["binding-1"] is BindingRevalidationState.VALID
    assert step2.value.bindings["binding-2"] is BindingRevalidationState.VALID


def test_selection_still_credential_free_for_conformance() -> None:
    selected = select_venue_client(World.LIVE, _venue("conformance:ctrader-demo"))
    assert is_ok(selected)
    assert selected.value.kind is VenueClientKind.CONFORMANCE


@pytest.mark.live
def test_live_credentialed_session_verification_separately_tagged() -> None:
    """Credentialed CT-18 session check — not this story's gate (SC-13; AR-87)."""
    pytest.skip("Spotware sandbox token not a Story 24.2 prerequisite")

