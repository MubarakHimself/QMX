"""Story 44.1 — Deterministic ModelClass routing and Deployment-family governance."""

from __future__ import annotations

from dataclasses import fields

import pytest
from qma.core.plugins.manifest import ManifestError, parse_plugin_manifest
from qma.core.ports.model import (
    DeploymentRecord,
    ModelClassRequest,
    NeedsFlags,
    ReviewPolicy,
    assign_model_family,
    eligible_pool,
    resolve_model_request,
    select_reviewer,
)
from qma.core.refusals import NoEligibleDeployment, NoEligibleReviewer, OperatorPrincipalRequired
from qma.core.vocabulary.enums import ModelClass, PrincipalClass, RoutingPolicy
from qma.daemon.proxy import DeploymentRegistry, ModelRouter
from qmf.core import is_ok, is_refusal


def _dep(
    deployment_id: str,
    model_class: ModelClass,
    *,
    tools: bool = False,
    vision: bool = False,
    reasoning: bool = False,
    parallel: bool = False,
    context: int = 8_000,
    weight: int = 1,
    quota: int = 0,
    fill_units: int = 0,
    fill_capacity: int = 10,
    family: str | None = None,
) -> DeploymentRecord:
    return DeploymentRecord(
        deployment_id=deployment_id,
        model_class=model_class,
        model_family=family,
        supports_tools=tools,
        supports_vision=vision,
        supports_reasoning_effort=reasoning,
        supports_parallel_tool_calls=parallel,
        context_tokens=context,
        weight=weight,
        quota_remaining=quota,
        fill_units=fill_units,
        fill_capacity=fill_capacity,
    )


def test_resolve_chain_is_modelclass_deployment_credential_broker() -> None:
    registry = DeploymentRegistry()
    assert is_ok(
        registry.register(_dep("work-1", ModelClass.WORKHORSE_GENERAL, tools=True, context=32_000))
    )
    router = ModelRouter(registry)
    decision = router.resolve(
        ModelClassRequest(
            model_class=ModelClass.WORKHORSE_GENERAL,
            needs=NeedsFlags(tools=True),
            min_context_tokens=16_000,
        )
    )
    assert is_ok(decision)
    assert decision.value.chain == ("ModelClass", "Deployment", "CredentialBroker")
    assert decision.value.deployment.deployment_id == "work-1"
    assert decision.value.capabilities.deployment_id == "work-1"
    assert decision.value.capabilities.supports_tools is True
    assert decision.value.capabilities.context_window == 32_000


def test_request_has_no_vendor_or_deployment_choice() -> None:
    names = {item.name for item in fields(ModelClassRequest)}
    assert "vendor" not in names
    assert "deployment_id" not in names
    assert "provider" not in names
    assert names == {"model_class", "needs", "min_context_tokens"}


def test_eligible_pool_filters_only_by_needs_and_min_context() -> None:
    catalog = (
        _dep("a", ModelClass.CODING_HIGH, tools=True, context=8_000),
        _dep("b", ModelClass.CODING_HIGH, tools=True, vision=True, context=128_000),
        _dep("c", ModelClass.CODING_HIGH, tools=False, vision=True, context=128_000),
        _dep("other", ModelClass.FAST_CHEAP, tools=True, vision=True, context=128_000),
    )
    request = ModelClassRequest(
        model_class=ModelClass.CODING_HIGH,
        needs=NeedsFlags(tools=True, vision=True),
        min_context_tokens=64_000,
    )
    pool = eligible_pool(request, catalog)
    assert [entry.deployment_id for entry in pool] == ["b"]
    # Cross-class candidate never enters the pool.
    assert all(entry.model_class is ModelClass.CODING_HIGH for entry in pool)


def test_empty_pool_names_class_and_unmet_constraint_never_crosses_class() -> None:
    catalog = (
        _dep("cheap", ModelClass.FAST_CHEAP, tools=True, context=200_000),
        _dep("code", ModelClass.CODING_HIGH, tools=False, context=8_000),
    )
    request = ModelClassRequest(
        model_class=ModelClass.CODING_HIGH,
        needs=NeedsFlags(tools=True),
        min_context_tokens=100_000,
    )
    outcome = resolve_model_request(request, catalog)
    assert is_refusal(outcome)
    assert NoEligibleDeployment.matches(outcome)
    assert outcome.context["model_class"] == "CODING_HIGH"
    assert outcome.context["unmet_constraint"] in {
        "tools",
        "min_context_tokens",
        "needs",
    }
    # The FAST_CHEAP deployment is never substituted.
    assert "cheap" not in str(outcome.context)


def test_routing_policies_failover_wrr_quota_fill() -> None:
    registry = DeploymentRegistry()
    for record in (
        _dep("f1", ModelClass.REASONING_HIGH, context=100_000, weight=1, quota=10, fill_units=0),
        _dep("f2", ModelClass.REASONING_HIGH, context=100_000, weight=3, quota=50, fill_units=4),
        _dep("f3", ModelClass.REASONING_HIGH, context=100_000, weight=1, quota=20, fill_units=9),
    ):
        assert is_ok(registry.register(record))
    router = ModelRouter(registry)
    request = ModelClassRequest(model_class=ModelClass.REASONING_HIGH)

    failover = router.resolve(request, policy=RoutingPolicy.FAILOVER)
    assert is_ok(failover)
    assert failover.value.deployment.deployment_id == "f1"
    assert failover.value.capabilities.model_class is ModelClass.REASONING_HIGH

    quota = router.resolve(request, policy="quota_lowest")
    assert is_ok(quota)
    assert quota.value.deployment.deployment_id == "f2"

    fill = router.resolve(request, policy=RoutingPolicy.FILL_FIRST)
    assert is_ok(fill)
    assert fill.value.deployment.deployment_id == "f3"

    first = router.resolve(request, policy=RoutingPolicy.WEIGHTED_ROUND_ROBIN)
    second = router.resolve(request, policy=RoutingPolicy.WEIGHTED_ROUND_ROBIN)
    third = router.resolve(request, policy=RoutingPolicy.WEIGHTED_ROUND_ROBIN)
    fourth = router.resolve(request, policy=RoutingPolicy.WEIGHTED_ROUND_ROBIN)
    assert is_ok(first) and is_ok(second) and is_ok(third) and is_ok(fourth)
    # weight 1,3,1 → expanded order f1,f2,f2,f2,f3
    assert first.value.deployment.deployment_id == "f1"
    assert second.value.deployment.deployment_id == "f2"
    assert third.value.deployment.deployment_id == "f2"
    assert fourth.value.deployment.deployment_id == "f2"


def test_registration_refuses_model_family_and_plugin_manifest_names_field() -> None:
    registry = DeploymentRegistry(allowed_families=("family-a", "family-b"))
    refused = registry.register(
        _dep("bad", ModelClass.WORKHORSE_GENERAL, family="family-a", context=16_000)
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "model_family"

    with pytest.raises(ManifestError, match="model_family"):
        parse_plugin_manifest(
            {
                "id": "research-corpus",
                "version": "0.1.0",
                "qma_api": ">=0.1.0,<1.0.0",
                "desk": "research",
                "entrypoint": "research_corpus.activate",
                "model_family": "opus",
                "contributions": [{"point": "tool", "local_id": "search"}],
            }
        )


def test_operator_assigns_model_family_machine_refused_unassigned_review_ineligible() -> None:
    registry = DeploymentRegistry(allowed_families=("family-a", "family-b"))
    assert is_ok(registry.register(_dep("d1", ModelClass.WORKHORSE_GENERAL, context=16_000)))
    assert is_ok(registry.register(_dep("d2", ModelClass.REASONING_HIGH, context=16_000)))

    machine = registry.assign_family(
        "d1",
        "family-a",
        principal=PrincipalClass.MACHINE,
    )
    assert is_refusal(machine)
    assert OperatorPrincipalRequired.matches(machine)
    assert machine.context["command"] == "model_family.assign"

    outside = registry.assign_family(
        "d1",
        "not-allowed",
        principal=PrincipalClass.OPERATOR,
    )
    assert is_refusal(outside)
    assert outside.context["field"] == "model_family"

    assigned = registry.assign_family(
        "d1",
        "family-a",
        principal="operator",
    )
    assert is_ok(assigned)
    assert assigned.value.model_family == "family-a"

    # Unassigned d2 remains routable.
    routed = ModelRouter(registry).resolve(ModelClassRequest(model_class=ModelClass.REASONING_HIGH))
    assert is_ok(routed)
    assert routed.value.deployment.deployment_id == "d2"
    assert routed.value.deployment.model_family is None

    # Unassigned family is ReviewPolicy-ineligible.
    catalog = registry.catalog()
    review = select_reviewer("family-a", catalog)
    assert is_refusal(review)
    assert NoEligibleReviewer.matches(review)

    assert is_ok(registry.assign_family("d2", "family-b", principal=PrincipalClass.OPERATOR))
    again = ReviewPolicy().select_reviewer("family-a", registry.catalog())
    assert is_ok(again)
    assert again.value.deployment_id == "d2"
    assert again.value.model_family == "family-b"


def test_core_assign_model_family_helper_matches_registry_gate() -> None:
    record = _dep("x", ModelClass.FAST_CHEAP, context=4_000)
    refused = assign_model_family(
        record,
        "alpha",
        principal=PrincipalClass.MACHINE,
        allowed_families=("alpha",),
    )
    assert OperatorPrincipalRequired.matches(refused)
    ok = assign_model_family(
        record,
        "alpha",
        principal=PrincipalClass.OPERATOR,
        allowed_families=("alpha",),
    )
    assert is_ok(ok)
    assert ok.value.model_family == "alpha"
