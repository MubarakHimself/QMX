"""Story 53.3 — ContributionHit pin stores the three-tuple, never fp1 or a grant."""

from __future__ import annotations

from qma.wire import (
    CONTRIBUTION_PIN_CONTRACT,
    CONTRIBUTION_PIN_DTO_OWNER,
    CONTRIBUTION_PIN_IS_GRANT,
    CONTRIBUTION_PIN_NEW_CT_MINTED,
    CONTRIBUTION_PIN_PERSISTENCE_STORE,
    CONTRIBUTION_PIN_REFUSED_CT,
    CONTRIBUTION_PIN_SCHEMA,
    CONTRIBUTION_PIN_SCHEMA_FILE,
    CONTRIBUTION_PIN_SCHEMA_NAME,
    CONTRIBUTION_PIN_SIXTH_STORE_MINTED,
    CONTRIBUTION_PIN_WIRED_AT_INSPECT_SHA,
    FEDERATED_HIT_INSPECT_SHA,
    PIN_TUPLE_FIELDS,
    SCHEMA_FILES,
    ContributionHit,
    ContributionPin,
    parse_contribution_pin,
    refuse_contribution_pin_digest,
    refuse_contribution_pin_fp1,
    refuse_contribution_pin_grant,
    validate_contribution_pin,
    validate_instance,
)
from qmf.core import is_ok, is_refusal

_FP1 = "fp1:sha256:" + ("ab" * 32)


def _hit() -> ContributionHit:
    built = ContributionHit.try_create(
        plugin_id="research-corpus",
        point="tool",
        qualified_id="research-corpus:inspect",
        package_id="research-corpus",
        package_version="0.1.0",
        availability_revision=1,
        availability="enabled",
    )
    assert is_ok(built)
    return built.value


def test_inspect_sha_did_not_wire_contribution_pin() -> None:
    """Claiming pin/tombstone already existed at 270e992 fails the story."""
    assert FEDERATED_HIT_INSPECT_SHA == "270e992"
    assert CONTRIBUTION_PIN_WIRED_AT_INSPECT_SHA is False
    assert CONTRIBUTION_PIN_NEW_CT_MINTED is False
    assert CONTRIBUTION_PIN_REFUSED_CT == "CT-52"
    assert CONTRIBUTION_PIN_DTO_OWNER == "COMP-QMA-WIRE"
    assert CONTRIBUTION_PIN_CONTRACT == "CT-40"
    assert CONTRIBUTION_PIN_IS_GRANT is False
    assert CONTRIBUTION_PIN_SIXTH_STORE_MINTED is False
    assert CONTRIBUTION_PIN_PERSISTENCE_STORE == "plugin_install_records"
    assert SCHEMA_FILES[CONTRIBUTION_PIN_SCHEMA_NAME] == CONTRIBUTION_PIN_SCHEMA_FILE
    assert CONTRIBUTION_PIN_SCHEMA == "qma.wire.contribution_pin.v1"


def test_pin_stores_exactly_the_three_tuple() -> None:
    hit = _hit()
    pinned = ContributionPin.from_hit(hit)
    assert is_ok(pinned)
    pin = pinned.value
    assert (
        pin.as_tuple()
        == hit.pin_tuple()
        == (
            "research-corpus:inspect",
            "0.1.0",
            1,
        )
    )
    assert PIN_TUPLE_FIELDS == (
        "qualified_id",
        "package_version",
        "availability_revision",
    )
    payload = dict(pin.to_payload())
    assert set(payload) == set(PIN_TUPLE_FIELDS)
    assert "fp1" not in payload
    assert "digest" not in payload
    assert "plugin_id" not in payload
    assert "grant_id" not in payload
    parsed = parse_contribution_pin(payload)
    assert is_ok(parsed)
    assert parsed.value.as_tuple() == pin.as_tuple()
    schema_ok = validate_instance(payload, CONTRIBUTION_PIN_SCHEMA_NAME)
    assert is_ok(schema_ok)
    validated = validate_contribution_pin(payload)
    assert is_ok(validated)


def test_pin_refuses_fp1_digest_and_grant_identity() -> None:
    as_fp1 = parse_contribution_pin(
        {
            "qualified_id": "research-corpus:inspect",
            "package_version": "0.1.0",
            "availability_revision": 1,
            "fp1": _FP1,
        }
    )
    assert is_refusal(as_fp1)
    assert as_fp1.context["decision"] == "DEC-0415"

    fp1_version = ContributionPin.try_create(
        qualified_id="research-corpus:inspect",
        package_version=_FP1,
        availability_revision=1,
    )
    assert is_refusal(fp1_version)

    digest = parse_contribution_pin(
        {
            "qualified_id": "research-corpus:inspect",
            "package_version": "0.1.0",
            "availability_revision": 1,
            "descriptor_digest": "sha256:" + ("cd" * 32),
        }
    )
    assert is_refusal(digest)

    grant = parse_contribution_pin(
        {
            "qualified_id": "research-corpus:inspect",
            "package_version": "0.1.0",
            "availability_revision": 1,
            "grant_id": "grant-1",
        }
    )
    assert is_refusal(grant)
    assert grant.context.get("pin_is_grant") is False

    assert is_refusal(refuse_contribution_pin_fp1())
    assert is_refusal(refuse_contribution_pin_digest())
    assert is_refusal(refuse_contribution_pin_grant())
    assert CONTRIBUTION_PIN_IS_GRANT is False
