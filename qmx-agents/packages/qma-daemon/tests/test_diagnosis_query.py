"""Story 61.2 — diagnosis query returns closed failure_class plus JobHandle."""

from __future__ import annotations

import json
import logging
import runpy
from io import StringIO
from pathlib import Path

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.jobs import JobHandle
from qma.core.refusals import GrantMismatch, NoEnvironment, StoreVersionMismatch
from qma.core.vocabulary.enums import FailureClass, JobHandleState
from qma.daemon.diagnosis import (
    DIAGNOSIS_EXISTED_AT_INSPECT_SHA,
    DIAGNOSIS_INSPECT_SHA,
    DIAGNOSIS_OWNER,
    DIAGNOSIS_QUERY_NAME,
    DIAGNOSIS_SQLITE_CLASS_MINTED,
    QMN_FAILURES_MD_EXTENDED_BY_KIT,
    DiagnosisQueryService,
    claim_diagnosis_query_at_inspect_sha,
    classify_failure_class,
    refuse_diagnosis_fourth_store,
    refuse_qmn_alert_failure_class,
    refuse_view_as_invoke,
)
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.journal.stores import CLOSED_INDEPENDENT_STORES, CLOSED_STORE_NAMES
from qma.daemon.operator_log import OPERATOR_LOG_REQUIRED_FIELDS
from qma.daemon.plugins import research_corpus_plugin_load_config
from qma.daemon.process import DaemonProcess
from qma.wire.diagnosis import DIAGNOSIS_NEW_CT_MINTED
from qma.wire.vocabulary import WireQuery
from qmf.core import is_ok, is_refusal

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "diagnosis_query_usage.py"


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "desk")
    assert is_ok(minted)
    return minted.value


def _log_line(correlation_id: str, *, event: str = "public_operation.failed") -> dict[str, object]:
    return {
        "ts": "2026-09-26T12:00:00.000Z",
        "level": "ERROR",
        "event": event,
        "correlation_id": correlation_id,
        "is_journal": False,
        "fp1_identity": False,
    }


def _lines(stream: StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def _compose(tmp_path: Path, *, boot: str, stream: StringIO) -> DaemonProcess:
    seed = tmp_path / "seed-corpus"
    seed.mkdir(exist_ok=True)
    result = DaemonProcess.compose(
        tmp_path,
        machine="test-host",
        boot_epoch_id=boot,
        bind_port=0,
        plugin_load_configs=research_corpus_plugin_load_config(seed),
        log_handler=logging.StreamHandler(stream),
    )
    assert is_ok(result), result
    return result.value


def test_inspect_sha_honesty_and_no_fourth_store() -> None:
    assert DIAGNOSIS_INSPECT_SHA == "34c148b"
    assert DIAGNOSIS_EXISTED_AT_INSPECT_SHA is False
    assert DIAGNOSIS_OWNER == "COMP-QMA-DAEMON"
    assert WireQuery.GET_DIAGNOSIS.value == DIAGNOSIS_QUERY_NAME
    assert DIAGNOSIS_SQLITE_CLASS_MINTED is False
    assert DIAGNOSIS_NEW_CT_MINTED is False
    assert QMN_FAILURES_MD_EXTENDED_BY_KIT is False
    assert "diagnosis" not in CLOSED_STORE_NAMES
    assert "diagnosis" not in CLOSED_INDEPENDENT_STORES
    claimed = claim_diagnosis_query_at_inspect_sha(True)
    assert is_refusal(claimed)
    assert claimed.context["existed_at_inspect_sha"] is False
    assert is_ok(claim_diagnosis_query_at_inspect_sha(False))
    fourth = refuse_diagnosis_fourth_store()
    assert is_refusal(fourth)
    assert fourth.context["minted"] is False
    qmn = refuse_qmn_alert_failure_class(given="protection-escalation")
    assert is_refusal(qmn)
    assert qmn.context["extended_qmn_failures_md"] is False


def test_classify_closed_failure_class_from_existing_surfaces() -> None:
    grant = classify_failure_class(
        refusal=GrantMismatch.of(field="instance_id", grant_id="g:1"),
    )
    assert is_ok(grant)
    assert grant.value is FailureClass.GRANT
    dep = classify_failure_class(refusal=NoEnvironment.of(kind="docker"))
    assert is_ok(dep)
    assert dep.value is FailureClass.DEPENDENCY
    host = classify_failure_class(
        refusal=StoreVersionMismatch.of(
            store="journal",
            expected_schema_version=1,
            store_schema_version=0,
        )
    )
    assert is_ok(host)
    assert host.value is FailureClass.HOST
    minted = JobHandle.try_create(
        job_id="job:wf",
        owner=_owner(),
        state=JobHandleState.FAILED,
        task_id="task:wf",
        correlation_id="corr-wf",
        attempt_id=2,
    )
    assert is_ok(minted)
    workflow = classify_failure_class(
        refusal=NoEnvironment.of(kind="docker"),
        job_handle=minted.value,
    )
    assert is_ok(workflow)
    assert workflow.value is FailureClass.WORKFLOW
    view = classify_failure_class(
        refusal=GrantMismatch.of(field="view_id", grant_id="g:view"),
        view_reason="unhealthy",
    )
    assert is_ok(view)
    assert view.value is FailureClass.VIEW
    mixed = classify_failure_class(
        refusal=GrantMismatch.of(field="view_id", grant_id="g:view"),
        job_handle=minted.value,
        view_reason="stale",
    )
    assert is_refusal(mixed)
    assert is_refusal(refuse_view_as_invoke())


def test_query_returns_failure_class_job_handle_correlation_id_healthy() -> None:
    jobs = JobHandleService()
    submitted = jobs.submit(
        owner=_owner(),
        task_id="task-diag",
        correlation_id="corr-run",
        attempt_id=4,
    )
    assert is_ok(submitted)
    started = jobs.start(submitted.value.job_id)
    assert is_ok(started)
    failed = jobs.complete(submitted.value.job_id, JobHandleState.FAILED)
    assert is_ok(failed)
    service = DiagnosisQueryService(jobs=jobs)
    observed = service.observe(
        correlation_id="corr-run",
        refusal=NoEnvironment.of(kind="docker"),
        healthy=False,
        log_line=_log_line("corr-run", event="task_graph.failed"),
        failure_class="workflow",
        job_handle=failed.value,
    )
    assert is_ok(observed)
    queried = service.query("corr-run")
    assert is_ok(queried)
    dto = queried.value
    assert dto.failure_class is FailureClass.WORKFLOW
    assert dto.job_handle is not None
    assert dto.job_handle.job_id == failed.value.job_id
    assert dto.job_handle.attempt_id == 4
    assert dto.correlation_id == "corr-run"
    assert dto.healthy is False
    assert dto.attempt_id == 4
    assert dto.log_line["event"] == "task_graph.failed"
    assert dto.refusal["category"] == "unavailable dependency"
    assert dto.job_handle.state is JobHandleState.FAILED
    assert service.opens_fourth_store() is False
    missing = service.query("corr-missing")
    assert is_refusal(missing)
    fp1 = service.query("fp1:sha256:" + ("cd" * 32))
    assert is_refusal(fp1)


def test_daemon_process_headless_diagnosis_of_failed_public_operation(
    tmp_path: Path,
) -> None:
    stream = StringIO()
    process = _compose(tmp_path, boot="boot-61-2", stream=stream)
    try:
        snap = process.snapshot()
        assert snap["diagnosis_query"] is True
        assert snap["diagnosis_existed_at_inspect_sha"] is False
        assert snap["diagnosis_sqlite_class"] is False
        assert snap["qmn_alert_failure_class_is_kit"] is False
        assert is_refusal(process.claim_diagnosis_query_at_inspect_sha(True))
        assert is_refusal(process.mint_diagnosis_sqlite_class())
        assert is_refusal(process.use_qmn_alert_failure_class("silent-degradation"))

        corr = "corr-public"
        emitted = process.emit_operator_event(
            "public_operation.failed",
            correlation_id=corr,
            instance_id="inst:1",
            op_id="qmb.analysis.project",
            logical_invocation_id="inv:1",
            graph_run_id="graph:1",
            level=logging.ERROR,
        )
        assert is_ok(emitted)
        public = [row for row in _lines(stream) if row.get("event") == "public_operation.failed"]
        assert len(public) == 1
        log_line = public[0]
        for field in OPERATOR_LOG_REQUIRED_FIELDS:
            assert field in log_line
        handle = JobHandle.try_create(
            job_id="job:public",
            owner=_owner(),
            state="failed",
            task_id="task:public",
            correlation_id=corr,
            attempt_id=1,
        )
        assert is_ok(handle)
        diagnosed = process.diagnose_failure(
            correlation_id=corr,
            refusal=GrantMismatch.of(field="grant_id", grant_id="g:1"),
            healthy=False,
            log_line=log_line,
            failure_class="grant",
            job_handle=None,
        )
        assert is_ok(diagnosed)
        assert diagnosed.value.failure_class is FailureClass.GRANT
        assert diagnosed.value.job_handle is None
        queried = process.get_diagnosis(corr)
        assert is_ok(queried)
        assert queried.value.correlation_id == corr
        assert queried.value.healthy is False
        assert queried.value.log_line["correlation_id"] == corr
        assert process.sqlite_connection_count() == 1

        view = process.diagnose_failure(
            correlation_id="corr-view",
            refusal=GrantMismatch.of(field="view_id", grant_id="g:view"),
            healthy=False,
            log_line=_log_line("corr-view"),
            failure_class="view",
            view_reason="unmounted",
        )
        assert is_ok(view)
        assert view.value.failure_class is FailureClass.VIEW
        assert view.value.job_handle is None
    finally:
        process.close()


def test_example_script() -> None:
    namespace = runpy.run_path(str(EXAMPLE), run_name="__main__")
    assert namespace["main"] is not None
