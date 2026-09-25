"""Story 60.3 — closed InvocationEnvelope caller_kind on COMP-QMA-CORE."""

from __future__ import annotations

import pytest
from qma.core.vocabulary import CLOSED_VOCABULARIES, CallerKind, VocabularyError, parse_closed


def test_caller_kind_is_closed_user_agent_workflow() -> None:
    assert {member.value for member in CallerKind} == {"user", "agent", "workflow"}
    assert CallerKind.USER == "user"
    assert CallerKind.AGENT == "agent"
    assert CallerKind.WORKFLOW == "workflow"
    names = {entry.name for entry in CLOSED_VOCABULARIES}
    assert "caller_kind" in names
    owned = next(entry for entry in CLOSED_VOCABULARIES if entry.name == "caller_kind")
    assert owned.owning_ad == "AD-24"
    assert owned.decision == "DEC-0464"
    assert owned.members is CallerKind
    assert parse_closed(CallerKind, "user") is CallerKind.USER
    assert parse_closed(CallerKind, CallerKind.WORKFLOW) is CallerKind.WORKFLOW
    with pytest.raises(VocabularyError):
        parse_closed(CallerKind, "widget")
    with pytest.raises(VocabularyError):
        parse_closed(CallerKind, "system")
    with pytest.raises(VocabularyError):
        parse_closed(CallerKind, "copilot")
