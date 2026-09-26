"""Story 61.2 — additive CT-40 diagnosis DTO on COMP-QMA-WIRE."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.jobs import JobHandle
from qma.core.refusals import GrantMismatch, NoEnvironment
from qma.wire import (
    ADDABLE_QUERY_COUNT,
    DIAGNOSIS_CONTRACT,
    DIAGNOSIS_DTO_OWNER,
    DIAGNOSIS_EXISTED_AT_INSPECT_SHA,
    DIAGNOSIS_FOURTH_STORE_MINTED,
    DIAGNOSIS_INSPECT_SHA,
    DIAGNOSIS_JOIN_KEY,
    DIAGNOSIS_NEW_CT_MINTED,
    DIAGNOSIS_QUERY_NAME,
    DIAGNOSIS_REFUSED_CT,
    DIAGNOSIS_SCHEMA,
    DIAGNOSIS_SCHEMA_FILE,
    DIAGNOSIS_SCHEMA_NAME,
    FAILURE_CLASSES,
    QMN_ALERT_FAILURE_CLASSES,
    SCHEMA_DIR,
    SCHEMA_FILES,
    SEED_QUERY_COUNT,
    VIEW_FAILURE_REASONS,
    WIRE_QUERIES,
    FailureClass,
    WireQuery,
    claim_diagnosis_query_at_inspect_sha,
    parse_diagnosis,
    parse_wire_type,
    refuse_diagnosis_fourth_store,
    refuse_join_on_fp1,
    refuse_qmn_alert_failure_class,
    refuse_view_as_invoke,
    validate_diagnosis,
    validate_family_payload,
)
from qmf.core import is_ok, is_refusal


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.RESEARCH, "alpha")
    assert is_ok(minted)
    return minted.value


def _handle(*, correlation_id: str, attempt_id: int = 2) -> JobHandle:
    minted = JobHandle.try_create(
        job_id="job:diag-1",
        owner=_owner(),
        state="failed",
        task_id="task:diag-1",
        correlation_id=correlation_id,
        attempt_id=attempt_id,
        logical_run_id=correlation_id,
    )
    assert is_ok(minted)
    return minted.value


def _log_line(correlation_id: str) -> dict[str, object]:
    return {
        "ts": "2026-09-26T00:00:00.000Z",
        "level": "ERROR",
        "event": "public_operation.failed",
        "correlation_id": correlation_id,
        "is_journal": False,
        "fp1_identity": False,
    }


def test_additive_ct40_query_and_inspect_sha_honesty() -> None:
    assert DIAGNOSIS_DTO_OWNER == "COMP-QMA-WIRE"
    assert DIAGNOSIS_CONTRACT == "CT-40"
    assert DIAGNOSIS_NEW_CT_MINTED is False
    assert DIAGNOSIS_REFUSED_CT == "CT-52"
    assert DIAGNOSIS_QUERY_NAME == "get_diagnosis"
    assert DIAGNOSIS_JOIN_KEY == "correlation_id"
    assert DIAGNOSIS_INSPECT_SHA == "34c148b"
    assert DIAGNOSIS_EXISTED_AT_INSPECT_SHA is False
    assert DIAGNOSIS_FOURTH_STORE_MINTED is False
    assert SCHEMA_FILES[DIAGNOSIS_SCHEMA_NAME] == DIAGNOSIS_SCHEMA_FILE
    assert DIAGNOSIS_SCHEMA == "qma.wire.diagnosis.v1"
    assert (SCHEMA_DIR / DIAGNOSIS_SCHEMA_FILE).is_file()
    assert WireQuery.GET_DIAGNOSIS.value == "get_diagnosis"
    assert "get_diagnosis" in WIRE_QUERIES
    assert ADDABLE_QUERY_COUNT == 5
    assert len(WIRE_QUERIES) == SEED_QUERY_COUNT + ADDABLE_QUERY_COUNT == 12
    assert parse_wire_type("get_diagnosis") == "get_diagnosis"
    assert is_ok(validate_family_payload("get_diagnosis", {"correlation_id": "corr-1"}))
    claimed = claim_diagnosis_query_at_inspect_sha(True)
    assert is_refusal(claimed)
    assert claimed.context["existed_at_inspect_sha"] is False
    assert claimed.context["inspect_sha"] == "34c148b"
    assert is_ok(claim_diagnosis_query_at_inspect_sha(False))
    assert is_refusal(claim_diagnosis_query_at_inspect_sha("maybe"))
    assert is_refusal(refuse_diagnosis_fourth_store())
    assert refuse_diagnosis_fourth_store().context["minted"] is False


def test_closed_failure_class_and_qmn_noun_is_different() -> None:
    assert {member.value for member in FailureClass} == FAILURE_CLASSES
    assert frozenset({"unmounted", "stale", "unhealthy"}) == VIEW_FAILURE_REASONS
    widget = parse_diagnosis(
        {
            "failure_class": "widget",
            "job_handle": None,
            "correlation_id": "corr-w",
            "healthy": False,
            "how_it_failed": {
                "log_line": _log_line("corr-w"),
                "attempt_id": None,
                "refusal": GrantMismatch.of(field="grant_id", grant_id="g:1"),
            },
        }
    )
    assert is_refusal(widget)
    qmn = parse_diagnosis(
        {
            "failure_class": "money-boundary",
            "job_handle": None,
            "correlation_id": "corr-qmn",
            "healthy": False,
            "how_it_failed": {
                "log_line": _log_line("corr-qmn"),
                "attempt_id": None,
                "refusal": GrantMismatch.of(field="grant_id", grant_id="g:1"),
            },
        }
    )
    assert is_refusal(qmn)
    assert qmn.context.get("qmn_alert_noun") is True
    assert "money-boundary" in QMN_ALERT_FAILURE_CLASSES
    assert is_refusal(refuse_qmn_alert_failure_class(given="money-boundary"))


def test_workflow_diagnosis_carries_job_handle_attempt_id_and_refusal() -> None:
    corr = "corr-workflow"
    handle = _handle(correlation_id=corr, attempt_id=3)
    body = parse_diagnosis(
        {
            "failure_class": "workflow",
            "job_handle": handle,
            "correlation_id": corr,
            "healthy": True,
            "how_it_failed": {
                "log_line": _log_line(corr),
                "attempt_id": 3,
                "refusal": NoEnvironment.of(kind="docker"),
            },
        }
    )
    assert is_ok(body)
    dto = body.value
    assert dto.failure_class is FailureClass.WORKFLOW
    assert dto.job_handle is not None
    assert dto.job_handle.attempt_id == 3
    assert dto.correlation_id == corr
    assert dto.healthy is True
    payload = dict(dto.to_payload())
    assert payload["failure_class"] == "workflow"
    handle_payload = payload["job_handle"]
    assert isinstance(handle_payload, dict)
    assert handle_payload["attempt_id"] == 3
    assert handle_payload["state"] == "failed"
    assert dto.attempt_id == 3
    assert dto.log_line["event"] == "public_operation.failed"
    assert dto.refusal["category"] == "unavailable dependency"
    assert "succeeded" not in str(handle_payload["state"])
    checked = validate_diagnosis(payload)
    assert is_ok(checked)


def test_example_script() -> None:
    example = Path(__file__).resolve().parents[1] / "examples" / "diagnosis_usage.py"
    namespace = runpy.run_path(str(example), run_name="__main__")
    assert namespace["main"] is not None


def test_grant_view_dependency_host_and_null_handle() -> None:
    grant = parse_diagnosis(
        {
            "failure_class": "grant",
            "job_handle": None,
            "correlation_id": "corr-grant",
            "healthy": False,
            "how_it_failed": {
                "log_line": _log_line("corr-grant"),
                "attempt_id": None,
                "refusal": GrantMismatch.of(field="instance_id", grant_id="g:1"),
            },
        }
    )
    assert is_ok(grant)
    assert grant.value.job_handle is None
    assert grant.value.attempt_id is None
    view = parse_diagnosis(
        {
            "failure_class": "view",
            "job_handle": None,
            "correlation_id": "corr-view",
            "healthy": False,
            "view_reason": "stale",
            "how_it_failed": {
                "log_line": _log_line("corr-view"),
                "attempt_id": None,
                "refusal": GrantMismatch.of(field="view_id", grant_id="g:view"),
            },
        }
    )
    assert is_ok(view)
    assert view.value.failure_class is FailureClass.VIEW
    assert view.value.view_reason == "stale"
    invoked = parse_diagnosis(
        {
            "failure_class": "view",
            "job_handle": _handle(correlation_id="corr-view-job"),
            "correlation_id": "corr-view-job",
            "healthy": False,
            "view_reason": "unmounted",
            "how_it_failed": {
                "log_line": _log_line("corr-view-job"),
                "attempt_id": 2,
                "refusal": GrantMismatch.of(field="view_id", grant_id="g:view"),
            },
        }
    )
    assert is_refusal(invoked)
    assert invoked.context.get("is_invoke") is False
    assert is_refusal(refuse_view_as_invoke())
    dep = parse_diagnosis(
        {
            "failure_class": "dependency",
            "job_handle": None,
            "correlation_id": "corr-dep",
            "healthy": False,
            "how_it_failed": {
                "log_line": _log_line("corr-dep"),
                "attempt_id": None,
                "refusal": NoEnvironment.of(kind="docker"),
            },
        }
    )
    assert is_ok(dep)
    host = parse_diagnosis(
        {
            "failure_class": "host",
            "job_handle": None,
            "correlation_id": "corr-host",
            "healthy": False,
            "how_it_failed": {
                "log_line": _log_line("corr-host"),
                "attempt_id": None,
                "refusal": NoEnvironment.of(kind="docker"),
            },
        }
    )
    assert is_ok(host)


def test_correlation_id_is_join_key_never_fp1_or_succeeded_handle() -> None:
    fp1 = parse_diagnosis(
        {
            "failure_class": "host",
            "job_handle": None,
            "correlation_id": "fp1:sha256:" + ("ab" * 32),
            "healthy": False,
            "how_it_failed": {
                "log_line": _log_line("fp1:sha256:" + ("ab" * 32)),
                "attempt_id": None,
                "refusal": NoEnvironment.of(kind="docker"),
            },
        }
    )
    assert is_refusal(fp1)
    assert is_refusal(refuse_join_on_fp1())
    succeeded = JobHandle.try_create(
        job_id="job:bad",
        owner=_owner(),
        state="succeeded",
        task_id="task:bad",
        correlation_id="corr-bad",
    )
    assert is_refusal(succeeded)
    awaiting = parse_diagnosis(
        {
            "failure_class": "workflow",
            "job_handle": {
                "job_id": "job:await",
                "owner": _owner().value,
                "state": "awaiting_approval",
                "task_id": "task:await",
                "attempt_id": 1,
            },
            "correlation_id": "corr-await",
            "healthy": False,
            "how_it_failed": {
                "log_line": _log_line("corr-await"),
                "attempt_id": 1,
                "refusal": NoEnvironment.of(kind="docker"),
            },
        }
    )
    assert is_refusal(awaiting)
    workflow_null = parse_diagnosis(
        {
            "failure_class": "workflow",
            "job_handle": None,
            "correlation_id": "corr-wf-null",
            "healthy": False,
            "how_it_failed": {
                "log_line": _log_line("corr-wf-null"),
                "attempt_id": None,
                "refusal": NoEnvironment.of(kind="docker"),
            },
        }
    )
    assert is_refusal(workflow_null)
