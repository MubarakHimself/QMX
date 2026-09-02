"""Story 47.1 — MemoryProvider port definitions (CT-43; FR-Q64)."""

from __future__ import annotations

from qma.core.ports import (
    GAP_0072_EXTERNAL_MEMORY_BACKEND,
    MEMORY_PROVIDER_OPERATIONS,
    MEMORY_PROVIDER_OPTIONAL_OFF,
    NO_PROMOTE_OPERATION,
    MemoryCandidate,
    MemoryProvider,
    compute_admission_confidence,
    parse_memory_candidate,
    refuse_external_memory_backend,
    refuse_memory_promote,
    stage_unbound_memory_edit,
)
from qma.core.vocabulary.enums import MemoryValidationState
from qmf.core import is_ok, is_refusal


def _candidate(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "mem-1",
        "provenance": {"source": "agent.observation", "derivation": "summary"},
        "supporting_artifacts": ["artifact://a1", "artifact://a2"],
        "scope": "desk.research/mission.m1",
        "proposer": "agent:research/quant-a/agent-1",
        "occurrence_time": 1_700_000_000_000_000_000,
        "content": {"statement": "EURUSD respects London open"},
    }
    base.update(overrides)
    return base


def test_operation_surface_excludes_promote_and_keeps_reflect_off() -> None:
    assert (
        frozenset(
            {
                "propose",
                "admit",
                "recall",
                "get",
                "list",
                "history",
                "supersede",
                "invalidate",
                "expire",
                "scopes",
            }
        )
        == MEMORY_PROVIDER_OPERATIONS
    )
    assert "promote" not in MEMORY_PROVIDER_OPERATIONS
    assert frozenset({"reflect"}) == MEMORY_PROVIDER_OPTIONAL_OFF
    assert NO_PROMOTE_OPERATION is True
    assert "promote" not in dir(MemoryProvider) or not hasattr(MemoryProvider, "promote")


def test_parse_requires_mandatory_fields_and_seven_states() -> None:
    ok = parse_memory_candidate(_candidate())
    assert is_ok(ok)
    assert ok.value.validation_state is MemoryValidationState.PROPOSED
    assert ok.value.supersession is None

    missing = parse_memory_candidate({"scope": "s", "proposer": "p"})
    assert is_refusal(missing)

    bad_state = parse_memory_candidate(_candidate(validation_state="pending"))
    assert is_refusal(bad_state)

    with_super = parse_memory_candidate(_candidate(supersession="mem-0"))
    assert is_ok(with_super)
    assert with_super.value.supersession == "mem-0"

    null_super = parse_memory_candidate(_candidate(supersession=None))
    assert is_refusal(null_super)


def test_propose_refuses_admission_confidence() -> None:
    refused = parse_memory_candidate(
        _candidate(admission_confidence=0.9),
        for_propose=True,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "admission_confidence"

    stamped = MemoryCandidate(
        provenance={"source": "x"},
        supporting_artifacts=("a",),
        scope="s",
        proposer="p",
        occurrence_time=1,
        admission_confidence=0.5,
    )
    refused_obj = parse_memory_candidate(stamped, for_propose=True)
    assert is_refusal(refused_obj)


def test_admission_confidence_is_deterministic_gate_output() -> None:
    first = compute_admission_confidence(
        provenance={"source": "obs"},
        supporting_artifacts=("a1", "a2"),
        corroboration_count=2,
        validation_history=("proposed",),
    )
    second = compute_admission_confidence(
        provenance={"source": "obs"},
        supporting_artifacts=("a1", "a2"),
        corroboration_count=2,
        validation_history=("proposed",),
    )
    assert first == second
    assert 0.0 <= first <= 1.0

    richer = compute_admission_confidence(
        provenance={"source": "obs", "extra": True},
        supporting_artifacts=("a1", "a2", "a3", "a4"),
        corroboration_count=4,
        validation_history=("proposed", "validated"),
    )
    assert richer >= first


def test_unbound_stage_wraps_exactly_one_memory_edit() -> None:
    parsed = parse_memory_candidate(_candidate())
    assert is_ok(parsed)
    edit = stage_unbound_memory_edit(parsed.value)
    assert edit["kind"] == "memory"
    assert edit["operation"] == "create"
    assert edit["id"] == "mem-1"
    assert "admission_confidence" not in edit["content"]  # type: ignore[operator]


def test_gap_0072_and_promote_refusals() -> None:
    backend = refuse_external_memory_backend()
    assert is_refusal(backend)
    assert backend.context["gap"] == GAP_0072_EXTERNAL_MEMORY_BACKEND
    assert backend.context.get("deferred") is True

    promote = refuse_memory_promote()
    assert is_refusal(promote)
    assert promote.context["act"] == "promote"
