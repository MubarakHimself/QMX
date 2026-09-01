"""Story 44.2 — OpenCodex local-proxy custody and Credential Broker egress."""

from __future__ import annotations

import pytest
from qma.core.barriers import (
    ALLOWED_CREDENTIAL_REF_PREFIXES,
    OUT_OF_SCOPE_CREDENTIAL_REF_PREFIXES,
    CredentialAllowlistError,
    assert_allowlist_not_widenable,
    is_credential_ref_allowed,
)
from qma.core.plugins import (
    assert_no_secret_in_hook_payloads,
    build_hook_result,
)
from qma.core.ports.model import (
    AUTH_MODE_NONE,
    OPENCODEX_ADAPTER,
    PROXY_ALLOW_UNAUTHENTICATED_LOOPBACK_KEY,
    DeploymentRecord,
    ModelClassRequest,
    NeedsFlags,
    is_local_proxy_deployment,
)
from qma.core.refusals import (
    CredentialOutOfScope,
    NonLoopbackProxy,
    UnauthenticatedProxy,
)
from qma.core.vocabulary.enums import ModelClass, PrincipalClass
from qma.core.vocabulary.registry import VocabularyError
from qma.daemon.proxy import (
    WINDOWS_CREDENTIAL_MANAGER_BACKEND,
    AdapterLayerCaller,
    CredentialBroker,
    DeploymentRegistry,
    EgressFrameError,
    MemoryCredentialBackend,
    ModelRouter,
    OpenCodexDeployment,
    WindowsCredentialManagerBackend,
    build_opencodex_deployment_record,
    execute_quant_model_request,
    validate_local_proxy_registration,
)
from qmf.core import is_ok, is_refusal


def test_opencodex_sits_behind_deployment_not_broker() -> None:
    record = build_opencodex_deployment_record(
        "opencodex-workhorse",
        ModelClass.WORKHORSE_GENERAL,
    )
    assert record.adapter == OPENCODEX_ADAPTER
    assert record.auth_mode == AUTH_MODE_NONE
    assert record.credential_ref is None
    assert is_local_proxy_deployment(record)

    deployment = OpenCodexDeployment(record=record)
    assert deployment.behind_credential_broker is False

    registry = DeploymentRegistry()
    assert is_ok(registry.register(record))
    router = ModelRouter(registry)
    decision = router.resolve(
        ModelClassRequest(
            model_class=ModelClass.WORKHORSE_GENERAL,
            needs=NeedsFlags(tools=True),
        )
    )
    assert is_ok(decision)
    assert decision.value.deployment.deployment_id == "opencodex-workhorse"
    # One logical Deployment; true id recorded — no pooling/masquerade.
    assert decision.value.deployment.deployment_id == record.deployment_id


def test_non_loopback_proxy_refused() -> None:
    record = build_opencodex_deployment_record(
        "remote-proxy",
        ModelClass.FAST_CHEAP,
        bind_host="10.0.0.8",
        bind_port=8080,
    )
    outcome = validate_local_proxy_registration(record)
    assert is_refusal(outcome)
    assert NonLoopbackProxy.matches(outcome)
    assert outcome.context["address"] == "10.0.0.8:8080"

    registry = DeploymentRegistry()
    registered = registry.register(record)
    assert is_refusal(registered)
    assert NonLoopbackProxy.matches(registered)


def test_unauthenticated_proxy_gated_by_registry_variable() -> None:
    record = build_opencodex_deployment_record(
        "loop-proxy",
        ModelClass.CODING_HIGH,
        accepts_unauthenticated=True,
    )
    assert is_ok(validate_local_proxy_registration(record, allow_unauthenticated_loopback=True))

    refused = validate_local_proxy_registration(record, allow_unauthenticated_loopback=False)
    assert is_refusal(refused)
    assert UnauthenticatedProxy.matches(refused)
    assert refused.context["deployment_id"] == "loop-proxy"

    registry = DeploymentRegistry(allow_unauthenticated_loopback=False)
    assert is_refusal(registry.register(record))


def test_startup_evidence_records_proxies_and_setting() -> None:
    registry = DeploymentRegistry(allow_unauthenticated_loopback=True)
    assert is_ok(
        registry.register(
            build_opencodex_deployment_record("p1", ModelClass.WORKHORSE_GENERAL)
        )
    )
    assert is_ok(
        registry.register(
            build_opencodex_deployment_record(
                "p2",
                ModelClass.REASONING_HIGH,
                bind_host="::1",
                bind_port=4000,
            )
        )
    )
    # Non-proxy Deployment for contrast.
    assert is_ok(
        registry.register(
            DeploymentRecord(
                deployment_id="cloud-1",
                model_class=ModelClass.FAST_CHEAP,
                context_tokens=8_000,
                credential_ref="cred://models/openai",
            )
        )
    )

    evidence = registry.startup_evidence()
    assert evidence.proxy_deployment_ids == ("p1", "p2")
    assert evidence.allow_unauthenticated_loopback is True
    assert evidence.allow_unauthenticated_loopback_key == PROXY_ALLOW_UNAUTHENTICATED_LOOPBACK_KEY
    payload = evidence.to_dict()
    assert "secret" not in payload
    assert payload["proxy_deployments"] == ["p1", "p2"]


def test_local_proxy_rejects_qma_credential_ref_and_wrong_auth_mode() -> None:
    with pytest.raises(VocabularyError):
        DeploymentRecord(
            deployment_id="bad-auth",
            model_class=ModelClass.FAST_CHEAP,
            adapter=OPENCODEX_ADAPTER,
            auth_mode="api_key",
            bind_host="127.0.0.1",
        )

    record = DeploymentRecord(
        deployment_id="bad-cred",
        model_class=ModelClass.FAST_CHEAP,
        adapter=OPENCODEX_ADAPTER,
        auth_mode=AUTH_MODE_NONE,
        bind_host="127.0.0.1",
        credential_ref="cred://models/openai",
    )
    outcome = validate_local_proxy_registration(record)
    assert is_refusal(outcome)


def test_credential_allowlist_is_code_declared_and_default_deny() -> None:
    assert is_credential_ref_allowed("cred://models/openai")
    assert is_credential_ref_allowed("cred://compute/sandbox-a")
    assert is_credential_ref_allowed("cred://corpus/docs")
    assert is_credential_ref_allowed("cred://telemetry/otlp")
    assert not is_credential_ref_allowed("cred://venue/ctrader")
    assert not is_credential_ref_allowed("cred://broker/icmarkets")
    assert not is_credential_ref_allowed("cred://exchange/binance")
    assert not is_credential_ref_allowed("cred://trading-node/vps")
    assert not is_credential_ref_allowed("cred://platform-registry/promo")
    assert not is_credential_ref_allowed("cred://unknown/x")

    assert OUT_OF_SCOPE_CREDENTIAL_REF_PREFIXES
    assert_allowlist_not_widenable()
    with pytest.raises(CredentialAllowlistError):
        assert_allowlist_not_widenable(ALLOWED_CREDENTIAL_REF_PREFIXES | {"cred://venue/"})


def test_broker_exact_reference_windows_backend_and_out_of_scope() -> None:
    backend = MemoryCredentialBackend()
    backend.put("cred://models/openai", "sk-test-value")
    broker = CredentialBroker(backend)
    assert broker.backend_id == WINDOWS_CREDENTIAL_MANAGER_BACKEND

    caller = AdapterLayerCaller(layer="model_proxy")
    frame = broker.resolve("cred://models/openai", caller=caller)
    assert is_ok(frame)
    with frame.value as opened:
        assert opened.reveal() == "sk-test-value"
        assert opened.to_diagnostic()["credential_ref"] == "cred://models/openai"
        assert "secret" not in opened.to_diagnostic()
    with pytest.raises(EgressFrameError):
        frame.value.reveal()

    out = broker.resolve("cred://venue/ctrader", caller=caller)
    assert is_refusal(out)
    assert CredentialOutOfScope.matches(out)
    assert out.context["credential_ref"] == "cred://venue/ctrader"

    # Non-adapter caller refused.
    bad_caller = broker.resolve("cred://models/openai", caller="hook")  # type: ignore[arg-type]
    assert is_refusal(bad_caller)

    # Sole v1 backend identity enforced.
    class OtherBackend:
        backend_id = "hashicorp_vault"

        def read_exact(self, credential_ref: str):
            raise AssertionError("must not be called")

    with pytest.raises(ValueError, match="sole v1"):
        CredentialBroker(OtherBackend())  # type: ignore[arg-type]

    win = WindowsCredentialManagerBackend(_reader={"cred://inference/x": "v"})
    assert win.backend_id == WINDOWS_CREDENTIAL_MANAGER_BACKEND
    assert is_ok(CredentialBroker(win).resolve("cred://inference/x", caller=caller))


def test_broker_backend_rejects_enumeration_surfaces() -> None:
    class ListingBackend:
        backend_id = WINDOWS_CREDENTIAL_MANAGER_BACKEND

        def read_exact(self, credential_ref: str):
            return None

        def enumerate(self) -> list[str]:
            return []

    with pytest.raises(ValueError, match="enumerate"):
        CredentialBroker(ListingBackend())  # type: ignore[arg-type]


def test_hook_payloads_exclude_secrets_by_schema() -> None:
    assert is_ok(
        assert_no_secret_in_hook_payloads(
            updated_input={"credential_ref": "cred://models/openai"},
            injected_context={"note": "ok"},
        )
    )
    refused = assert_no_secret_in_hook_payloads(
        updated_output={"api_key": "literally-secret"},
    )
    assert is_refusal(refused)

    with pytest.raises(VocabularyError):
        build_hook_result("allow", updated_input={"secret": "nope"})

    ok = build_hook_result(
        "allow",
        updated_input={"credential_ref": "cred://models/openai"},
        injected_context={"hint": "ref-only"},
    )
    assert ok.updated_input is not None
    assert "secret" not in ok.updated_input


def test_milestone_harness_opencodex_over_wire_preserves_provenance() -> None:
    registry = DeploymentRegistry()
    record = build_opencodex_deployment_record(
        "opencodex-main",
        ModelClass.WORKHORSE_GENERAL,
    )
    assert is_ok(registry.register(record))
    router = ModelRouter(registry)
    deployment = OpenCodexDeployment(record=record)

    # OpenCodex refuses a crossed secret.
    assert is_refusal(
        deployment.call(
            ModelClassRequest(model_class=ModelClass.WORKHORSE_GENERAL),
            prompt="hi",
            resolved_secret="sk-leaked",
        )
    )

    result = execute_quant_model_request(
        router=router,
        request=ModelClassRequest(
            model_class=ModelClass.WORKHORSE_GENERAL,
            needs=NeedsFlags(tools=True),
            min_context_tokens=1_000,
        ),
        scope_path=(
            {"kind": "desk", "id": "research"},
            {"kind": "quant", "id": "quant-alpha"},
            {"kind": "mission", "id": "m1"},
            {"kind": "task", "id": "t1"},
        ),
        correlation_id="corr-milestone-44-2",
        principal_class=PrincipalClass.OPERATOR,
        prompt="ping",
        deployments={"opencodex-main": deployment},
    )
    assert is_ok(result)
    value = result.value
    assert value.correlation_id == "corr-milestone-44-2"
    assert [seg.kind for seg in value.scope_path] == ["desk", "quant", "mission", "task"]
    assert value.routing.model_class == "WORKHORSE_GENERAL"
    assert value.routing.deployment_id == "opencodex-main"
    assert value.routing.principal_class == "operator"
    assert value.routing.behind_credential_broker is False
    assert value.routing.chain == ("ModelClass", "Deployment", "OpenCodex")
    assert value.model.credential_crossed is False
    assert value.model.auth_mode == AUTH_MODE_NONE

    wire = value.to_wire()
    assert wire["correlation_id"] == "corr-milestone-44-2"
    assert "secret" not in wire
    routing = wire["routing"]
    assert isinstance(routing, dict)
    assert "secret" not in routing
    model = wire["model"]
    assert isinstance(model, dict)
    assert model["credential_crossed"] is False
