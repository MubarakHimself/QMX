"""Story 3.6 — role-scoped namespaces, FM-11, and decay-cohort reads (AC3)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from qmf.core import AccountRole, is_refusal
from qmf.core.refusal import RefusalCategory
from qmf.data import CrossRoleRead, DecisionOutcome, book_journal, decay_cohort_read

_path = Path(__file__).resolve().parent / "logbooks_cases.py"
_name = "qmf.data.tests.logbooks_cases"
_existing = sys.modules.get(_name)
if _existing is not None:
    _cases = _existing
else:
    _spec = importlib.util.spec_from_file_location(_name, _path)
    assert _spec is not None and _spec.loader is not None
    _cases = importlib.util.module_from_spec(_spec)
    sys.modules[_name] = _cases
    _spec.loader.exec_module(_cases)

_ok = _cases.ok
_binding_fields = _cases.binding_fields
_event = _cases.event
_multi_role_events = _cases.multi_role_events
_BOOK = _cases.BOOK


def test_single_role_scope_filters_to_one_namespace() -> None:
    logbook = _ok(book_journal(_multi_role_events(), _BOOK, role=AccountRole.LIVE))
    assert logbook.roles == frozenset({AccountRole.LIVE})
    assert len(logbook.rows) == 1


def test_multi_role_without_declaration_is_fm11_policy_rejection() -> None:
    refused = book_journal(_multi_role_events(), _BOOK)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert set(refused.context["roles"]) == {"live", "paper-benched"}  # type: ignore[arg-type]


def test_declared_multi_role_entity_read_spans_roles() -> None:
    logbook = _ok(
        book_journal(_multi_role_events(), _BOOK, cross_role=CrossRoleRead.MULTI_ROLE_ENTITY)
    )
    assert logbook.roles == frozenset({AccountRole.LIVE, AccountRole.PAPER_BENCHED})
    assert logbook.cross_role is CrossRoleRead.MULTI_ROLE_ENTITY


def test_single_role_matches_all_when_uniform() -> None:
    live = _event("decision", _binding_fields(AccountRole.LIVE), outcome=DecisionOutcome.AUTHORIZED)
    logbook = _ok(book_journal([live], _BOOK))
    assert logbook.roles == frozenset({AccountRole.LIVE})


def test_role_and_cross_role_together_is_invalid() -> None:
    refused = book_journal(
        _multi_role_events(),
        _BOOK,
        role=AccountRole.LIVE,
        cross_role=CrossRoleRead.MULTI_ROLE_ENTITY,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_invalid_role_and_invalid_cross_role() -> None:
    assert is_refusal(book_journal(_multi_role_events(), _BOOK, role="nope"))
    assert is_refusal(book_journal(_multi_role_events(), _BOOK, cross_role="not-declared"))


def test_decay_cohort_read_spans_roles_and_carries_role() -> None:
    events = _multi_role_events()
    no_role = _event("data quality", {"metric": "spread"}, sequence=2)
    # A cohort row that carries a role but declares no binding (a venue-authored data-quality
    # row) still projects, with binding None.
    role_no_binding = _event("data quality", {"metric": "spread", "role": "live"}, sequence=3)
    logbook = _ok(decay_cohort_read([*events, no_role, role_no_binding]))
    assert logbook.cross_role is CrossRoleRead.DECAY_COHORT
    assert logbook.selector is None
    assert logbook.roles == frozenset({AccountRole.LIVE, AccountRole.PAPER_BENCHED})
    # The event carrying no role is not a cohort row; the role-without-binding one is.
    assert len(logbook.rows) == 3
    assert any(row.binding is None for row in logbook.rows)
    assert all(isinstance(row.role, AccountRole) for row in logbook.rows)


def test_decay_cohort_absent_role_skipped_malformed_role_refused() -> None:
    # M7: an event with NO role key is not a cohort row and is skipped (pinned behavior),
    # but an event that DECLARES a role which is malformed (present but outside the closed
    # AccountRole set) is refused — matching every other projection — not silently dropped.
    absent = _event("data quality", {"metric": "spread"}, sequence=0)
    ok = _ok(decay_cohort_read([absent]))
    assert ok.rows == ()  # the absent-role event contributes no cohort row

    malformed = _event("data quality", {"metric": "spread", "role": "LIVE"}, sequence=0)
    refused = decay_cohort_read([malformed])
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context.get("field") == "role"


def test_decay_cohort_malformed_role_refused_like_book_journal() -> None:
    # The same malformed-role row book_journal refuses is refused by decay_cohort_read too,
    # rather than silently kept in the cohort read (the M7 parity the finding names).
    malformed = _event(
        "decision",
        _binding_fields() | {"role": "LIVE"},
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    assert is_refusal(book_journal([malformed], _BOOK))
    assert is_refusal(decay_cohort_read([malformed]))


def test_decay_cohort_read_treats_partial_binding_as_absent() -> None:
    partial = _event("risk transition", {"book_instance_id": _BOOK, "role": "live"})
    logbook = _ok(decay_cohort_read([partial]))
    assert len(logbook.rows) == 1
    assert logbook.rows[0].binding is None
