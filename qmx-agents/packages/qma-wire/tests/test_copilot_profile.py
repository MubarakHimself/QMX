"""Story 60.1 — optional copilot_profile is additive CT-40, not a grant."""

from __future__ import annotations

from qma.wire import (
    COPILOT_PROFILE_CONTRACT,
    COPILOT_PROFILE_DTO_OWNER,
    COPILOT_PROFILE_EXISTED_AT_INSPECT_SHA,
    COPILOT_PROFILE_INSPECT_SHA,
    COPILOT_PROFILE_IS_CONTRIBUTION_POINT,
    COPILOT_PROFILE_IS_GRANT,
    COPILOT_PROFILE_NEW_CT_MINTED,
    COPILOT_PROFILE_REFUSED_CT,
    COPILOT_PROFILE_SCHEMA,
    COPILOT_PROFILE_SCHEMA_FILE,
    COPILOT_PROFILE_SCHEMA_NAME,
    SCHEMA_FILES,
    CopilotProfile,
    parse_wire_copilot_profile,
    refuse_copilot_profile_as_contribution,
    refuse_copilot_profile_as_grant,
    validate_copilot_profile,
)
from qmf.core import is_ok, is_refusal

_PROFILE = {
    "prompts": ["You are a research copilot."],
    "suggested_ops": [
        {
            "op_id": "qmb.analysis.project",
            "op_version": 1,
            "qualified_id": "research-corpus:inspect",
        }
    ],
}


def test_copilot_profile_ct40_identity_and_inspect_honesty() -> None:
    assert COPILOT_PROFILE_DTO_OWNER == "COMP-QMA-WIRE"
    assert COPILOT_PROFILE_CONTRACT == "CT-40"
    assert COPILOT_PROFILE_NEW_CT_MINTED is False
    assert COPILOT_PROFILE_REFUSED_CT == "CT-52"
    assert COPILOT_PROFILE_INSPECT_SHA == "34c148b"
    assert COPILOT_PROFILE_EXISTED_AT_INSPECT_SHA is False
    assert COPILOT_PROFILE_IS_CONTRIBUTION_POINT is False
    assert COPILOT_PROFILE_IS_GRANT is False
    assert SCHEMA_FILES[COPILOT_PROFILE_SCHEMA_NAME] == COPILOT_PROFILE_SCHEMA_FILE
    assert COPILOT_PROFILE_SCHEMA == "qma.wire.copilot_profile.v1"


def test_optional_copilot_profile_parses_as_request_blob() -> None:
    parsed = parse_wire_copilot_profile(_PROFILE)
    assert is_ok(parsed)
    profile = parsed.value
    assert isinstance(profile, CopilotProfile)
    assert profile.is_contribution_point is False
    assert profile.is_grant is False
    assert profile.prompts == ("You are a research copilot.",)
    schema_ok = validate_copilot_profile(dict(_PROFILE))
    assert is_ok(schema_ok)
    empty = parse_wire_copilot_profile({})
    assert is_ok(empty)
    assert empty.value.prompts == ()
    assert empty.value.suggested_ops == ()


def test_copilot_profile_refuses_grant_and_contribution_identity() -> None:
    as_grant = parse_wire_copilot_profile({"grant_id": "grant:1", "prompts": []})
    assert is_refusal(as_grant)
    assert as_grant.context["is_grant"] is False
    as_point = parse_wire_copilot_profile({"point": "copilot"})
    assert is_refusal(as_point)
    assert as_point.context["is_contribution_point"] is False
    assert is_refusal(refuse_copilot_profile_as_grant())
    assert is_refusal(refuse_copilot_profile_as_contribution())
    null = parse_wire_copilot_profile(None)
    assert is_refusal(null)
