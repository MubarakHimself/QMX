"""Story 54.1 - versioned operation descriptor is complete and door-aware."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

import pytest
from qma.core.operations import (
    APPLICATION_LAYER_OP_OWNERS,
    BROKER_VENUE_OP_OWNER,
    ERROR_REFUSAL_FAMILY,
    FORBIDDEN_DESCRIPTOR_FIELDS,
    FORBIDDEN_OPERATOR_CLI_ADAPTERS,
    OPERATION_DESCRIPTOR_CONTRACT,
    OPERATION_DESCRIPTOR_FIELDS,
    OPERATION_DESCRIPTOR_INSPECT_SHAS,
    OPERATION_DESCRIPTOR_NEW_CT_MINTED,
    OPERATION_DESCRIPTOR_OWNER,
    OPERATION_DESCRIPTOR_WIRED_AT_INSPECT_SHA,
    OPERATOR_CLI_ADAPTER,
    OPERATOR_CLI_ADAPTERS,
    PUBLIC_OPERATION_PAYLOADS,
    QMA_IS_HOST_RUNTIME,
    QMA_OPERATOR_CLI,
    QMF_IS_APPLICATION_LAYER_OP_OWNER,
    QMN_OPERATOR_CLI,
    REQUIRED_REFUSAL_CODES,
    admit_operation_door,
    descriptor_for,
    door_matrix,
    is_operator_cli_adapter,
    owner_door_summary,
    parse_operation_descriptor,
    public_operation_descriptors,
    publish_operation_descriptor,
)
from qma.core.ports.cardinality import Cardinality
from qma.core.refusals import UnsupportedDoor
from qma.core.vocabulary import (
    CLOSED_VOCABULARIES,
    DoorAdapter,
    EdgeMapping,
    EffectClass,
    EffectRetryOutcome,
    EmptyPolicy,
    GrantEvaluationMoment,
    LifecycleVerb,
    OperationCardinality,
    OperationPlacement,
    OutputShape,
    PortKind,
    ReconcilePolicy,
    VocabularyError,
    parse_closed,
)
from qmf.core import is_ok, is_refusal


def _refusal_codes(payload: Mapping[str, object]) -> set[str]:
    shape = payload.get("error_refusal_shape")
    assert isinstance(shape, dict)
    typed = cast(dict[str, object], shape)
    raw = typed.get("codes")
    assert isinstance(raw, list)
    return {str(item) for item in cast(list[object], raw)}


_CONTRACTS_PROJECT = {
    "op_id": "qmb.analysis.project",
    "owner": "COMP-QMB",
    "version": 1,
    "input_schema": "qmb.analysis.project.v1",
    "output_shape": "artifact_ref",
    "input_cardinality": "one",
    "output_cardinality": "one",
    "empty_policy": "refuse",
    "configuration": {
        "defaults": {"as_of": None},
        "required_keys": ["run_fp1"],
        "optional_keys": ["as_of"],
    },
    "declared_operation_dependencies": [],
    "resource_needs": {
        "occupancy": "query",
        "memory_class": "light",
        "requires_environment": False,
    },
    "documentation_refs": ["docs/components/qmb.md#analysis-project"],
    "validation_class": "schema+semantic",
    "units": None,
    "compatibility": {"qmb": ">=0.1"},
    "effect_class": "read",
    "permission_requests": ["library.read"],
    "placement": "local-library",
    "error_refusal_shape": {
        "family": "CT-04",
        "codes": [
            "INVALID_INPUT",
            "UNAVAILABLE",
            "UNSUPPORTED_DOOR",
            "STALE_OBSERVATION",
            "GRANT_MISMATCH",
        ],
    },
    "progress": True,
    "lifecycle_verbs": ["start", "query-state", "cancel", "await"],
    "supported_doors": [
        {"adapter": "library", "door": "qmb.analysis.project"},
        {"adapter": "qmb-cli", "door": "qmb analysis project"},
        {"adapter": "qma-wire", "door": "via CT-47"},
    ],
}


def test_inspect_sha_did_not_wire_operation_descriptors() -> None:
    """Claiming Operation descriptor existed at 270e992/580b49a fails the story."""
    assert OPERATION_DESCRIPTOR_INSPECT_SHAS == ("270e992", "580b49a")
    assert OPERATION_DESCRIPTOR_WIRED_AT_INSPECT_SHA is False
    assert OPERATION_DESCRIPTOR_NEW_CT_MINTED is False
    assert OPERATION_DESCRIPTOR_OWNER == "COMP-QMA-CORE"
    assert OPERATION_DESCRIPTOR_CONTRACT == "CONTRACTS §1"
    assert ERROR_REFUSAL_FAMILY == "CT-04"


def test_contracts_section_1_example_is_complete() -> None:
    published = publish_operation_descriptor(_CONTRACTS_PROJECT)
    assert is_ok(published)
    descriptor = published.value
    payload = descriptor.to_payload()
    for field in OPERATION_DESCRIPTOR_FIELDS:
        assert field in payload
    assert "cardinality" not in payload
    assert "mapping" not in payload
    assert frozenset({"cardinality", "mapping"}) == FORBIDDEN_DESCRIPTOR_FIELDS
    assert payload["op_id"] == "qmb.analysis.project"
    assert payload["owner"] == "COMP-QMB"
    assert payload["version"] == 1
    assert payload["input_cardinality"] == "one"
    assert payload["output_cardinality"] == "one"
    assert payload["output_shape"] == "artifact_ref"
    assert payload["effect_class"] == "read"
    assert payload["placement"] == "local-library"
    assert payload["lifecycle_verbs"] == ["start", "query-state", "cancel", "await"]
    assert _refusal_codes(payload) >= set(REQUIRED_REFUSAL_CODES)
    assert descriptor.door_key == ("qmb.analysis.project", 1)
    round_trip = parse_operation_descriptor(payload)
    assert is_ok(round_trip)
    assert round_trip.value.to_payload() == payload


def test_merged_cardinality_field_is_refused() -> None:
    merged = dict(_CONTRACTS_PROJECT)
    merged["cardinality"] = "one"
    refused = parse_operation_descriptor(merged)
    assert is_refusal(refused)
    assert refused.context["field"] == "cardinality"

    port_shaped = dict(_CONTRACTS_PROJECT)
    port_shaped["input_cardinality"] = "singleton"
    refused_port = parse_operation_descriptor(port_shaped)
    assert is_refusal(refused_port)
    assert refused_port.context["field"] == "input_cardinality"


def test_mapping_is_not_on_the_descriptor() -> None:
    mapped = dict(_CONTRACTS_PROJECT)
    mapped["mapping"] = "broadcast"
    refused = parse_operation_descriptor(mapped)
    assert is_refusal(refused)
    assert refused.context["field"] == "mapping"


def test_closed_vocabularies_reject_invented_values() -> None:
    names = {entry.name for entry in CLOSED_VOCABULARIES}
    assert "output_shape" in names
    assert "effect_class" in names
    assert "operation_placement" in names
    assert "operation_cardinality" in names
    assert "lifecycle_verb" in names
    assert "empty_policy" in names
    assert "edge_mapping" in names
    assert "port_kind" in names
    assert "door_adapter" in names
    assert "reconcile_policy" in names
    assert "effect_retry_outcome" in names
    assert {member.value for member in OutputShape} == {
        "value",
        "artifact_ref",
        "job_handle",
        "event",
        "stream",
    }
    assert OutputShape.EVENT is not OutputShape.STREAM
    assert {member.value for member in EffectClass} == {
        "none",
        "read",
        "append-evidence",
        "mutate-config",
        "place-run",
        "external-egress",
    }
    assert {member.value for member in OperationPlacement} == {
        "local-library",
        "daemon",
        "worker",
        "node",
    }
    assert {member.value for member in OperationCardinality} == {"one", "many"}
    assert {member.value for member in LifecycleVerb} == {
        "start",
        "query-state",
        "cancel",
        "await",
    }
    assert {member.value for member in EmptyPolicy} == {"refuse", "skip"}
    assert {member.value for member in EdgeMapping} == {
        "one",
        "zip",
        "broadcast",
        "keyed-join",
        "cartesian",
    }
    assert {member.value for member in PortKind} == {
        "reference",
        "data",
        "event",
        "control",
    }
    assert {member.value for member in ReconcilePolicy} == {
        "query-then-decide",
        "unknown-manual",
        "never-retry",
    }
    with pytest.raises(VocabularyError):
        parse_closed(OutputShape, "blob")
    with pytest.raises(VocabularyError):
        parse_closed(EffectClass, "write")
    with pytest.raises(VocabularyError):
        parse_closed(OperationPlacement, "cloud")
    with pytest.raises(VocabularyError):
        parse_closed(LifecycleVerb, "pause")
    with pytest.raises(VocabularyError):
        parse_closed(OperationCardinality, "singleton")
    with pytest.raises(VocabularyError):
        parse_closed(DoorAdapter, "qma-cli")
    with pytest.raises(VocabularyError):
        parse_closed(DoorAdapter, "qmn-cli")
    with pytest.raises(VocabularyError):
        parse_closed(ReconcilePolicy, "blind-retry")
    assert {member.value for member in EffectRetryOutcome} == {
        "may-retry",
        "dedupe",
        "cas",
        "run-identity",
        "receipt-or-unknown",
    }
    with pytest.raises(VocabularyError):
        parse_closed(EffectRetryOutcome, "blind-retry")
    assert {member.value for member in GrantEvaluationMoment} == {
        "accept",
        "dispatch",
        "nested_call",
        "retry",
        "external_commit",
    }
    with pytest.raises(VocabularyError):
        parse_closed(GrantEvaluationMoment, "silent-latest")


def test_missing_refusal_codes_are_refused() -> None:
    incomplete = dict(_CONTRACTS_PROJECT)
    incomplete["error_refusal_shape"] = {
        "family": "CT-04",
        "codes": ["INVALID_INPUT", "UNAVAILABLE"],
    }
    refused = parse_operation_descriptor(incomplete)
    assert is_refusal(refused)
    assert refused.context["field"] == "error_refusal_shape.codes"

    new_ct = dict(_CONTRACTS_PROJECT)
    new_ct["error_refusal_shape"] = {
        "family": "CT-52",
        "codes": list(REQUIRED_REFUSAL_CODES),
    }
    refused_ct = parse_operation_descriptor(new_ct)
    assert is_refusal(refused_ct)
    assert refused_ct.context["field"] == "error_refusal_shape.family"


def test_fragment_descriptor_is_refused() -> None:
    refused = parse_operation_descriptor({"op_id": "qmb.analysis.project", "version": 1})
    assert is_refusal(refused)
    assert refused.context["field"] == "descriptor"
    missing = refused.context["missing"]
    assert isinstance(missing, (list, tuple))
    assert "input_cardinality" in missing
    assert "supported_doors" in missing


def test_public_operations_publish_complete_descriptors() -> None:
    descriptors = public_operation_descriptors()
    assert len(descriptors) == len(PUBLIC_OPERATION_PAYLOADS)
    ids = {item.op_id for item in descriptors}
    assert ids == {
        "qmb.analysis.project",
        "qmb.backtest.run",
        "qma.procedure.start",
        "qmn.evidence.query",
        "qml.research.browse",
    }
    for descriptor in descriptors:
        payload = descriptor.to_payload()
        assert list(payload) == list(OPERATION_DESCRIPTOR_FIELDS)
        assert _refusal_codes(payload) >= set(REQUIRED_REFUSAL_CODES)
        assert descriptor.door_key == (descriptor.op_id, descriptor.version)


def test_door_matrix_is_keyed_by_op_id_and_version() -> None:
    descriptors = public_operation_descriptors()
    matrix = door_matrix(descriptors)
    assert ("qmb.analysis.project", 1) in matrix
    assert ("qmb.backtest.run", 1) in matrix
    for key in matrix:
        assert isinstance(key, tuple)
        assert len(key) == 2
        op_id, version = key
        assert isinstance(op_id, str)
        assert isinstance(version, int)
        assert not isinstance(op_id, str) or not op_id.startswith("COMP-")
    project = descriptor_for(descriptors, op_id="qmb.analysis.project", version=1)
    run = descriptor_for(descriptors, op_id="qmb.backtest.run", version=1)
    assert project is not None and run is not None
    assert project.owner == run.owner == "COMP-QMB"
    project_adapters = {door.adapter for door in project.supported_doors}
    run_adapters = {door.adapter for door in run.supported_doors}
    assert project_adapters != run_adapters
    assert DoorAdapter.QMN_RUN_SLICE in run_adapters
    assert DoorAdapter.QMN_RUN_SLICE not in project_adapters
    summary = owner_door_summary(descriptors)
    assert "COMP-QMB" in summary
    # Owner union is a summary only: it is not the per-op supported set.
    assert set(summary["COMP-QMB"]) != {door.adapter.value for door in project.supported_doors}


def test_unsupported_door_is_typed_unsupported_door() -> None:
    descriptors = public_operation_descriptors()
    admitted = admit_operation_door(
        descriptors,
        op_id="qma.procedure.start",
        version=1,
        adapter="library",
    )
    assert is_ok(admitted)
    refused = admit_operation_door(
        descriptors,
        op_id="qma.procedure.start",
        version=1,
        adapter="qmb-cli",
    )
    assert is_refusal(refused)
    assert isinstance(refused, UnsupportedDoor)
    assert refused.context["unsupported_door"] is True
    assert refused.context["code"] == "UNSUPPORTED_DOOR"
    assert refused.context["reason"] == "unsupported_door"
    assert refused.context["adapter"] == "qmb-cli"
    node = admit_operation_door(
        descriptors,
        op_id="qma.procedure.start",
        version=1,
        adapter="node",
    )
    assert is_refusal(node)
    assert UnsupportedDoor.matches(node)


def test_qmb_is_the_only_operator_cli() -> None:
    assert OPERATOR_CLI_ADAPTER == "qmb-cli"
    assert frozenset({"qmb-cli"}) == OPERATOR_CLI_ADAPTERS
    assert QMA_OPERATOR_CLI is False
    assert QMN_OPERATOR_CLI is False
    assert is_operator_cli_adapter(DoorAdapter.QMB_CLI) is True
    assert is_operator_cli_adapter("qma-cli") is False
    assert is_operator_cli_adapter("qmn-cli") is False
    assert frozenset({"qma-cli", "qmn-cli"}) == FORBIDDEN_OPERATOR_CLI_ADAPTERS
    descriptors = public_operation_descriptors()
    for adapter in ("qma-cli", "qmn-cli"):
        refused = admit_operation_door(
            descriptors,
            op_id="qmn.evidence.query",
            version=1,
            adapter=adapter,
        )
        assert is_refusal(refused)
        assert isinstance(refused, UnsupportedDoor)
        assert refused.context["operator_cli"] == "qmb"
        assert refused.context["adapter"] == adapter

    minted_qma_cli = dict(_CONTRACTS_PROJECT)
    minted_qma_cli["owner"] = "COMP-QMA"
    minted_qma_cli["op_id"] = "qma.procedure.start"
    minted_qma_cli["supported_doors"] = [{"adapter": "qma-cli", "door": "qma procedure start"}]
    published = publish_operation_descriptor(minted_qma_cli)
    assert is_refusal(published)
    assert published.context["adapter"] == "qma-cli"

    qmb_cli_on_qma = dict(_CONTRACTS_PROJECT)
    qmb_cli_on_qma["owner"] = "COMP-QMA"
    qmb_cli_on_qma["op_id"] = "qma.procedure.start"
    qmb_cli_on_qma["supported_doors"] = [{"adapter": "qmb-cli", "door": "qmb procedure start"}]
    refused_cli = publish_operation_descriptor(qmb_cli_on_qma)
    assert is_refusal(refused_cli)
    assert refused_cli.context["owner"] == "COMP-QMA"


def test_port_cardinality_is_not_operation_cardinality() -> None:
    # Port contribution cardinality stays singleton|multi; descriptor uses one|many.
    assert {member.value for member in Cardinality} == {"singleton", "multi"}
    assert {member.value for member in OperationCardinality} == {"one", "many"}
    assert not set(Cardinality) & set(OperationCardinality)


def test_op_owner_is_comp_among_qma_qmb_qml_qmn() -> None:
    assert QMA_IS_HOST_RUNTIME is True
    assert QMF_IS_APPLICATION_LAYER_OP_OWNER is False
    assert BROKER_VENUE_OP_OWNER == "COMP-QMN"
    owners = {item["owner"] for item in PUBLIC_OPERATION_PAYLOADS}
    assert owners <= APPLICATION_LAYER_OP_OWNERS
    assert "COMP-QMF" not in APPLICATION_LAYER_OP_OWNERS

    toolbox = dict(_CONTRACTS_PROJECT)
    toolbox["owner"] = "COMP-QMF-CORE"
    refused_qmf = parse_operation_descriptor(toolbox)
    assert is_refusal(refused_qmf)
    assert refused_qmf.context["field"] == "owner"
    assert refused_qmf.context["qmf_is_application_layer_owner"] is False

    unknown = dict(_CONTRACTS_PROJECT)
    unknown["owner"] = "COMP-OTHER"
    refused_other = parse_operation_descriptor(unknown)
    assert is_refusal(refused_other)
    assert refused_other.context["field"] == "owner"
