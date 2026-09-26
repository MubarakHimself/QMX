"""L27 reference usage: additive CT-40 diagnosis DTO (Story 61.2)."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.jobs import JobHandle
from qma.core.refusals import GrantMismatch, NoEnvironment
from qma.wire import (
    DIAGNOSIS_CONTRACT,
    DIAGNOSIS_DTO_OWNER,
    DIAGNOSIS_EXISTED_AT_INSPECT_SHA,
    DIAGNOSIS_NEW_CT_MINTED,
    DIAGNOSIS_QUERY_NAME,
    FailureClass,
    claim_diagnosis_query_at_inspect_sha,
    parse_diagnosis,
    refuse_diagnosis_fourth_store,
    refuse_qmn_alert_failure_class,
    refuse_view_as_invoke,
    validate_diagnosis,
)
from qmf.core import is_ok, is_refusal


def _log_line(correlation_id: str) -> dict[str, object]:
    return {
        "ts": "2026-09-26T00:00:00.000Z",
        "level": "ERROR",
        "event": "public_operation.failed",
        "correlation_id": correlation_id,
        "is_journal": False,
        "fp1_identity": False,
    }


def main() -> None:
    assert DIAGNOSIS_DTO_OWNER == "COMP-QMA-WIRE"
    assert DIAGNOSIS_CONTRACT == "CT-40"
    assert DIAGNOSIS_NEW_CT_MINTED is False
    assert DIAGNOSIS_QUERY_NAME == "get_diagnosis"
    assert DIAGNOSIS_EXISTED_AT_INSPECT_SHA is False
    assert is_refusal(claim_diagnosis_query_at_inspect_sha(True))
    assert is_refusal(refuse_diagnosis_fourth_store())
    assert is_refusal(refuse_qmn_alert_failure_class())
    assert is_refusal(refuse_view_as_invoke())

    owner = ActorId.mint(DeskSlug.RESEARCH, "alpha")
    assert is_ok(owner)
    handle = JobHandle.try_create(
        job_id="job:ex",
        owner=owner.value,
        state="failed",
        task_id="task:ex",
        correlation_id="corr-ex",
        attempt_id=2,
    )
    assert is_ok(handle)
    workflow = parse_diagnosis(
        {
            "failure_class": "workflow",
            "job_handle": handle.value,
            "correlation_id": "corr-ex",
            "healthy": False,
            "how_it_failed": {
                "log_line": _log_line("corr-ex"),
                "attempt_id": 2,
                "refusal": NoEnvironment.of(kind="docker"),
            },
        }
    )
    assert is_ok(workflow)
    assert workflow.value.failure_class is FailureClass.WORKFLOW
    assert workflow.value.job_handle is not None
    assert workflow.value.attempt_id == 2
    assert is_ok(validate_diagnosis(dict(workflow.value.to_payload())))

    grant = parse_diagnosis(
        {
            "failure_class": "grant",
            "job_handle": None,
            "correlation_id": "corr-grant",
            "healthy": True,
            "how_it_failed": {
                "log_line": _log_line("corr-grant"),
                "attempt_id": None,
                "refusal": GrantMismatch.of(field="grant_id", grant_id="g:1"),
            },
        }
    )
    assert is_ok(grant)
    assert grant.value.job_handle is None
    print("diagnosis DTO: failure_class plus JobHandle or null")


if __name__ == "__main__":
    main()
