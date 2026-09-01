"""Story 40.2 — closed vocabulary registry and distinct governed acts."""

from __future__ import annotations

import pytest
from qma.core import vocabulary as vocab
from qma.core.vocabulary import (
    ACT_TARGET,
    CLOSED_VOCABULARIES,
    HOOK_CONTROLS,
    HOOK_EVENT_NAMES,
    HOOK_RESULT_PRECEDENCE,
    HOOK_VERBS,
    HOST_REQUEST_OWNING_AD,
    HOST_REQUEST_VOCABULARY_OWNER,
    MONEY_PATH_LIVE_WRITABLE_HANDLE_KINDS,
    READ_ONLY_EVIDENCE_HANDLE_KINDS,
    TASK_EMITTING_NODE_KINDS,
    DeliveryState,
    ExecutionEnvironmentKind,
    GovernedAct,
    GovernedActTarget,
    GraphArtifactKind,
    HandleKind,
    HookControl,
    HookResultDecision,
    HookVerb,
    JobHandleState,
    MemoryValidationState,
    MessageKind,
    ModelClass,
    NetworkPolicy,
    NodeKind,
    PrincipalClass,
    RefinementEditKind,
    RoutingPolicy,
    TaskMissionState,
    VariableScope,
    VocabularyError,
    assert_handle_kind_not_money_path,
    assert_no_principal_conversion,
    hook_result_rank,
    may_convert_principal,
    most_restrictive_hook_result,
    parse_closed,
    parse_hook_event_name,
    validate_governed_act,
)


def test_every_closed_vocabulary_declares_owning_ad() -> None:
    assert len(CLOSED_VOCABULARIES) >= 20
    names = {entry.name for entry in CLOSED_VOCABULARIES}
    assert "hook_verb" in names
    assert "governed_act" in names
    assert "variable_editability" in names
    for entry in CLOSED_VOCABULARIES:
        assert entry.owning_ad.startswith("AD-")
        assert entry.decision.startswith("DEC-")
        assert len(tuple(entry.members)) >= 2


def test_invented_values_rejected() -> None:
    with pytest.raises(VocabularyError):
        parse_closed(HookResultDecision, "approve")
    with pytest.raises(VocabularyError):
        parse_closed(HandleKind, "OrderHandle")
    with pytest.raises(VocabularyError):
        parse_closed(ModelClass, "REASONING_LOW")
    with pytest.raises(VocabularyError):
        parse_closed(PrincipalClass, "admin")
    with pytest.raises(VocabularyError):
        parse_hook_event_name("before_invented")


def test_hook_verbs_and_controls() -> None:
    assert len(HOOK_VERBS) == 23
    assert set(HOOK_VERBS) == {
        HookVerb.TOOL,
        HookVerb.TASK_CREATE,
        HookVerb.TASK_COMPLETE,
        HookVerb.LEDGER_APPEND,
        HookVerb.MEMORY_WRITE,
        HookVerb.SKILL_WRITE,
        HookVerb.ARTIFACT_REGISTER,
        HookVerb.EXPERIMENT_REGISTER,
        HookVerb.ENV_CREATE,
        HookVerb.ENV_REMOVE,
        HookVerb.SUBAGENT_SPAWN,
        HookVerb.MESSAGE_SEND,
        HookVerb.GRAPH_TRANSITION,
        HookVerb.SESSION_START,
        HookVerb.SESSION_END,
        HookVerb.MISSION_START,
        HookVerb.MISSION_COMPLETE,
        HookVerb.PLUGIN_ACTIVATE,
        HookVerb.PLUGIN_DEACTIVATE,
        HookVerb.ROUTINE_FIRE,
        HookVerb.HOOK_REGISTER,
        HookVerb.PROPOSAL_STAGE,
        HookVerb.PROPOSAL_APPLY,
    }
    assert HOOK_CONTROLS == (HookControl.AGENT_STOP, HookControl.REVIEW_REQUIRED)
    assert len(HOOK_EVENT_NAMES) == 23 * 2 + 2
    assert "before_tool" in HOOK_EVENT_NAMES
    assert "after_proposal_apply" in HOOK_EVENT_NAMES
    assert "agent_stop" in HOOK_EVENT_NAMES
    assert "review_required" in HOOK_EVENT_NAMES
    assert parse_hook_event_name("before_ledger_append") == "before_ledger_append"


def test_hook_result_total_precedence() -> None:
    assert HOOK_RESULT_PRECEDENCE == (
        HookResultDecision.BLOCK_STOP,
        HookResultDecision.DENY,
        HookResultDecision.DEFER,
        HookResultDecision.ASK,
        HookResultDecision.ALLOW,
        HookResultDecision.OBSERVE,
    )
    assert hook_result_rank("block_stop") < hook_result_rank("deny")
    assert hook_result_rank("deny") < hook_result_rank("defer")
    assert hook_result_rank("defer") < hook_result_rank("ask")
    assert hook_result_rank("ask") < hook_result_rank("allow")
    assert hook_result_rank("allow") < hook_result_rank("observe")
    assert most_restrictive_hook_result(("allow", "deny", "observe")) is HookResultDecision.DENY


def test_handle_and_work_states() -> None:
    assert {member.value for member in HandleKind} == {
        "BacktestHandle",
        "ExperimentHandle",
        "TradeLogHandle",
        "StrategyHandle",
        "KnowledgeHandle",
        "MarketDataHandle",
    }
    assert frozenset() == MONEY_PATH_LIVE_WRITABLE_HANDLE_KINDS
    assert {
        HandleKind.TRADE_LOG_HANDLE,
        HandleKind.MARKET_DATA_HANDLE,
    } == READ_ONLY_EVIDENCE_HANDLE_KINDS
    for kind in HandleKind:
        assert assert_handle_kind_not_money_path(kind) is kind

    assert {member.value for member in JobHandleState} == {
        "queued",
        "running",
        "done",
        "failed",
        "cancelled",
        "aborted",
        "unknown",
    }
    assert {member.value for member in TaskMissionState} == {
        "pending",
        "ready",
        "running",
        "blocked",
        "unknown",
        "done",
        "failed",
        "cancelled",
    }


def test_message_model_routing_principal() -> None:
    assert len(tuple(MessageKind)) == 7
    assert len(tuple(DeliveryState)) == 5
    assert {member.value for member in ModelClass} == {
        "REASONING_HIGH",
        "WORKHORSE_GENERAL",
        "CODING_HIGH",
        "FAST_CHEAP",
    }
    assert {member.value for member in RoutingPolicy} == {
        "failover",
        "weighted_round_robin",
        "quota_lowest",
        "fill_first",
    }
    assert {member.value for member in PrincipalClass} == {"operator", "machine"}
    assert may_convert_principal("operator", "operator") is True
    assert may_convert_principal("machine", "operator") is False
    assert_no_principal_conversion("machine", "machine")
    with pytest.raises(VocabularyError):
        assert_no_principal_conversion("machine", "operator")


def test_memory_graph_environment_refinement_scopes() -> None:
    assert len(tuple(MemoryValidationState)) == 7
    assert len(tuple(NodeKind)) == 10
    assert {
        NodeKind.TASK,
        NodeKind.AGENT,
        NodeKind.LOOP,
    } == TASK_EMITTING_NODE_KINDS
    assert len(tuple(ExecutionEnvironmentKind)) == 6
    assert {member.value for member in NetworkPolicy} == {"none", "allowlist"}
    assert len(tuple(RefinementEditKind)) == 9
    assert "variable" not in {member.value for member in RefinementEditKind}
    assert len(tuple(VariableScope)) == 8

    assert GraphArtifactKind.GRAPH_TEMPLATE.value == "graph_template"
    assert GraphArtifactKind.TASK_GRAPH.value == "task_graph"
    assert GraphArtifactKind.GRAPH_TEMPLATE is not GraphArtifactKind.TASK_GRAPH


def test_host_request_owned_by_qma_wire() -> None:
    assert HOST_REQUEST_VOCABULARY_OWNER == "qma-wire"
    assert HOST_REQUEST_OWNING_AD == "AD-14"
    assert vocab.HOST_REQUEST_VOCABULARY_OWNER == "qma-wire"


def test_governed_acts_are_distinct() -> None:
    assert ACT_TARGET[GovernedAct.ADMIT] is GovernedActTarget.MEMORY_CANDIDATE
    assert ACT_TARGET[GovernedAct.APPLY] is GovernedActTarget.REFINEMENT_PROPOSAL
    assert ACT_TARGET[GovernedAct.PROMOTE] is GovernedActTarget.REGISTERED_ARTIFACT

    validate_governed_act("admit", "memory_candidate")
    validate_governed_act("apply", "refinement_proposal")
    validate_governed_act("promote", "registered_artifact")

    with pytest.raises(VocabularyError):
        validate_governed_act("promote", "memory_candidate")
    with pytest.raises(VocabularyError):
        validate_governed_act("promote", "refinement_proposal")
    with pytest.raises(VocabularyError):
        validate_governed_act("admit", "refinement_proposal")
    with pytest.raises(VocabularyError):
        validate_governed_act("apply", "memory_candidate")
    with pytest.raises(VocabularyError):
        validate_governed_act("admit", "registered_artifact")
