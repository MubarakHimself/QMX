"""Story 61.2 — closed kit failure_class on COMP-QMA-CORE (cheap-veto A7)."""

from __future__ import annotations

import pytest
from qma.core.vocabulary import CLOSED_VOCABULARIES, FailureClass, VocabularyError, parse_closed


def test_failure_class_is_closed_grant_workflow_view_dependency_host() -> None:
    assert {member.value for member in FailureClass} == {
        "grant",
        "workflow",
        "view",
        "dependency",
        "host",
    }
    names = {entry.name for entry in CLOSED_VOCABULARIES}
    assert "failure_class" in names
    owned = next(entry for entry in CLOSED_VOCABULARIES if entry.name == "failure_class")
    assert owned.owning_ad == "AD-5"
    assert owned.decision == "DEC-0456"
    assert owned.members is FailureClass
    assert parse_closed(FailureClass, "view") is FailureClass.VIEW
    with pytest.raises(VocabularyError):
        parse_closed(FailureClass, "widget")
    with pytest.raises(VocabularyError):
        parse_closed(FailureClass, "money-boundary")
    with pytest.raises(VocabularyError):
        parse_closed(FailureClass, "policy rejection")
