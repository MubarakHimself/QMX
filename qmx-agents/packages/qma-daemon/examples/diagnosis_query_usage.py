"""L27 reference usage: headless diagnosis query (Story 61.2)."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.jobs import JobHandle
from qma.core.refusals import GrantMismatch, NoEnvironment
from qma.core.vocabulary.enums import FailureClass, JobHandleState
from qma.daemon.diagnosis import (
    DIAGNOSIS_EXISTED_AT_INSPECT_SHA,
    DIAGNOSIS_OWNER,
    DIAGNOSIS_SQLITE_CLASS_MINTED,
    DiagnosisQueryService,
    claim_diagnosis_query_at_inspect_sha,
    classify_failure_class,
    refuse_diagnosis_fourth_store,
    refuse_qmn_alert_failure_class,
)
from qma.daemon.journal.stores import CLOSED_STORE_NAMES
from qmf.core import is_ok, is_refusal


def _log_line(correlation_id: str) -> dict[str, object]:
    return {
        "ts": "2026-09-26T12:00:00.000Z",
        "level": "ERROR",
        "event": "task_graph.failed",
        "correlation_id": correlation_id,
        "is_journal": False,
        "fp1_identity": False,
    }


def main() -> None:
    assert DIAGNOSIS_OWNER == "COMP-QMA-DAEMON"
    assert DIAGNOSIS_EXISTED_AT_INSPECT_SHA is False
    assert DIAGNOSIS_SQLITE_CLASS_MINTED is False
    assert "diagnosis" not in CLOSED_STORE_NAMES
    assert is_refusal(claim_diagnosis_query_at_inspect_sha(True))
    assert is_refusal(refuse_diagnosis_fourth_store())
    assert is_refusal(refuse_qmn_alert_failure_class())

    owner = ActorId.mint(DeskSlug.ANALYSIS, "desk")
    assert is_ok(owner)
    handle = JobHandle.try_create(
        job_id="job:ex-61-2",
        owner=owner.value,
        state=JobHandleState.FAILED,
        task_id="task:ex-61-2",
        correlation_id="corr-ex-61-2",
        attempt_id=3,
    )
    assert is_ok(handle)
    classified = classify_failure_class(
        refusal=NoEnvironment.of(kind="docker"),
        job_handle=handle.value,
    )
    assert is_ok(classified)
    assert classified.value is FailureClass.WORKFLOW

    service = DiagnosisQueryService()
    observed = service.observe(
        correlation_id="corr-ex-61-2",
        refusal=NoEnvironment.of(kind="docker"),
        healthy=False,
        log_line=_log_line("corr-ex-61-2"),
        job_handle=handle.value,
    )
    assert is_ok(observed)
    queried = service.query("corr-ex-61-2")
    assert is_ok(queried)
    dto = queried.value
    assert dto.failure_class is FailureClass.WORKFLOW
    assert dto.job_handle is not None
    assert dto.job_handle.attempt_id == 3
    assert dto.correlation_id == "corr-ex-61-2"
    assert dto.healthy is False
    assert dto.attempt_id == 3

    grant = service.observe(
        correlation_id="corr-grant",
        refusal=GrantMismatch.of(field="grant_id", grant_id="g:1"),
        healthy=True,
        log_line=_log_line("corr-grant"),
        job_handle=None,
    )
    assert is_ok(grant)
    assert grant.value.failure_class is FailureClass.GRANT
    assert grant.value.job_handle is None
    print("diagnosis query: closed failure_class plus JobHandle")


if __name__ == "__main__":
    main()
