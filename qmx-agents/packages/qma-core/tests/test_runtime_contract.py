"""Story 45.5 — loop-and-state contract and session axes (FR-Q52)."""

from __future__ import annotations

import pytest
from qma.core.control.runtime import (
    ANALYSIS_NOTEBOOK_TOOL_ID,
    BACKGROUND_SESSION_TYPES,
    CLIENT_SESSION_AXIS,
    DEFERRED_RUNTIME_EXCLUSIONS,
    DIALOGUE_RUNTIME_DESKS,
    DURABLE_SESSION_AXES,
    HOSTED_NOTEBOOK_SERVICES,
    LOOP_AND_STATE_CONTRACT,
    LOOP_AND_STATE_SURFACES,
    RLM_DEPTH_CAP_REGISTRY_KEY,
    RLM_HOST_TRANSPORT,
    RLM_KERNEL_INTERPRETER,
    RLM_KERNEL_PLACEMENT,
    RLM_RUNTIME_DESK,
    available_execution_models,
    durable_session_payload,
    is_analysis_desk,
    is_rlm_runtime_in_scope,
    mint_durable_session,
    parse_session_attachment,
    select_execution_model,
)
from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.vocabulary.enums import ExecutionModel, SessionAttachment, SessionAutonomy
from qma.core.vocabulary.registry import CLOSED_VOCABULARIES, VocabularyError, parse_closed
from qmf.core import is_ok, is_refusal


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "nova")
    assert is_ok(minted)
    return minted.value


def test_dialogue_available_every_desk_rlm_analysis_only() -> None:
    assert frozenset(member.value for member in DeskSlug) == DIALOGUE_RUNTIME_DESKS
    for desk in DeskSlug:
        models = available_execution_models(desk)
        assert ExecutionModel.DIALOGUE in models
        selected = select_execution_model(desk)
        assert is_ok(selected)
        assert selected.value is ExecutionModel.DIALOGUE
        if desk is DeskSlug.ANALYSIS:
            assert ExecutionModel.RLM in models
            rlm = select_execution_model(desk, ExecutionModel.RLM)
            assert is_ok(rlm)
        else:
            assert ExecutionModel.RLM not in models
            refused = select_execution_model(desk, "rlm")
            assert is_refusal(refused)
            assert refused.context["gap"] == "GAP-0080"


def test_rlm_scoped_by_desk_never_by_role() -> None:
    assert RLM_RUNTIME_DESK is DeskSlug.ANALYSIS
    assert is_analysis_desk(DeskSlug.ANALYSIS)
    assert is_analysis_desk("analysis")
    assert is_analysis_desk("analysis-backtest")
    assert not is_analysis_desk("analyst")
    assert not is_analysis_desk(DeskSlug.RESEARCH)
    assert not is_rlm_runtime_in_scope(RoleName.ANALYST)
    assert not is_analysis_desk("the Analyst desk")


def test_shared_loop_and_state_contract() -> None:
    assert LOOP_AND_STATE_CONTRACT == "daemon-owned-loop-and-state"
    assert "hooks" in LOOP_AND_STATE_SURFACES
    assert "compute_router" in LOOP_AND_STATE_SURFACES
    assert "tool_registry" in LOOP_AND_STATE_SURFACES
    assert RLM_KERNEL_INTERPRETER == "persistent_python"
    assert RLM_KERNEL_PLACEMENT == "worker_docker_container"
    assert RLM_HOST_TRANSPORT == "qma-wire"
    assert RLM_DEPTH_CAP_REGISTRY_KEY == "registry:rlm.depth_cap"


def test_durable_session_axes_exclude_attachment() -> None:
    owner = _owner()
    minted = mint_durable_session(
        session_id="sess:1",
        owner=owner,
        execution_model="rlm",
        autonomy="autonomous",
    )
    assert is_ok(minted)
    session = minted.value
    assert session.execution_model is ExecutionModel.RLM
    assert session.autonomy is SessionAutonomy.AUTONOMOUS
    payload = durable_session_payload(session)
    assert tuple(DURABLE_SESSION_AXES) == ("execution_model", "autonomy")
    assert CLIENT_SESSION_AXIS not in payload
    assert "attachment" not in payload
    assert payload["execution_model"] == "rlm"
    assert payload["autonomy"] == "autonomous"
    assert payload["contract"] == LOOP_AND_STATE_CONTRACT

    attached = mint_durable_session(
        session_id="sess:2",
        owner=owner,
        attachment="attached",
    )
    assert is_refusal(attached)
    assert attached.context["field"] == "attachment"

    from_payload = mint_durable_session(
        session_id="sess:3",
        owner=owner,
        payload={"attachment": "detached"},
    )
    assert is_refusal(from_payload)


def test_no_background_session_type() -> None:
    assert "background" in BACKGROUND_SESSION_TYPES
    refused = select_execution_model(DeskSlug.ANALYSIS, "background")
    assert is_refusal(refused)
    minted = mint_durable_session(
        session_id="sess:bg",
        owner=_owner(),
        session_type="background_session",
    )
    assert is_refusal(minted)


def test_session_attachment_is_closed_client_vocabulary() -> None:
    assert {member.value for member in SessionAttachment} == {"attached", "detached"}
    assert {member.value for member in ExecutionModel} == {"dialogue", "rlm"}
    parsed = parse_session_attachment("attached")
    assert is_ok(parsed)
    assert parsed.value is SessionAttachment.ATTACHED
    with pytest.raises(VocabularyError):
        parse_closed(ExecutionModel, "background")
    names = {entry.name for entry in CLOSED_VOCABULARIES}
    assert "execution_model" in names
    assert "session_attachment" in names
    assert "session_autonomy" in names


def test_deferred_runtime_gaps_remain_open() -> None:
    for gap in ("GAP-0080", "GAP-0076", "GAP-0075", "GAP-0078"):
        assert gap in DEFERRED_RUNTIME_EXCLUSIONS
        assert "deferred" in DEFERRED_RUNTIME_EXCLUSIONS[gap].casefold()
    assert ANALYSIS_NOTEBOOK_TOOL_ID == "qma-inhouse:analysis-notebook"
    assert "colab" in HOSTED_NOTEBOOK_SERVICES


def test_quant_owner_accepted() -> None:
    actor = _owner()
    quant = Quant(
        actor_id=actor,
        desk=DeskSlug.ANALYSIS,
        quant_slug="nova",
        role=RoleName.ANALYST,
        name="Nova",
    )
    minted = mint_durable_session(session_id="sess:q", owner=quant)
    assert is_ok(minted)
    assert minted.value.owner == actor
    assert minted.value.execution_model is ExecutionModel.DIALOGUE
