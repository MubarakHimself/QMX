"""Headless diagnosis query (Story 61.2; kit AD-5; DEC-0456).

COMP-QMA-DAEMON computes ``failure_class`` plus JobHandle plus
``correlation_id`` from existing surfaces: operator JSON-lines, JobHandle
``attempt_id``, and a typed refusal. Not a sqlite class, not a log grep
store, and not a fourth observability product. QMN alert ``failure_class``
is a different noun.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final, cast

from qma.core.ports.jobs import JobHandle
from qma.core.refusals import (
    GrantInactive,
    GrantMismatch,
    GrantWidenRefused,
    ManifestIsNotGrant,
    NoEligibleDeployment,
    NoEligibleReviewer,
    NoEnvironment,
    NoMemoryProvider,
    StoreVersionMismatch,
)
from qma.core.vocabulary.enums import FailureClass, JobHandleState
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.journal.stores import CLOSED_INDEPENDENT_STORES, CLOSED_STORE_NAMES
from qma.wire.diagnosis import (
    DIAGNOSIS_EXISTED_AT_INSPECT_SHA,
    DIAGNOSIS_FOURTH_STORE_MINTED,
    DIAGNOSIS_INSPECT_SHA,
    DIAGNOSIS_JOIN_KEY,
    DIAGNOSIS_NEW_CT_MINTED,
    DIAGNOSIS_QUERY_NAME,
    VIEW_FAILURE_REASONS,
    Diagnosis,
    claim_diagnosis_query_at_inspect_sha,
    parse_diagnosis,
    refuse_diagnosis_fourth_store,
    refuse_join_on_fp1,
    refuse_qmn_alert_failure_class,
    refuse_view_as_invoke,
)
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.core.refusal import RefusalCategory, TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "DIAGNOSIS_EXISTED_AT_INSPECT_SHA",
    "DIAGNOSIS_FOURTH_STORE_MINTED",
    "DIAGNOSIS_INSPECT_SHA",
    "DIAGNOSIS_JOIN_KEY",
    "DIAGNOSIS_NEW_CT_MINTED",
    "DIAGNOSIS_OWNER",
    "DIAGNOSIS_QUERY_NAME",
    "DIAGNOSIS_SQLITE_CLASS_MINTED",
    "QMN_FAILURES_MD_EXTENDED_BY_KIT",
    "Diagnosis",
    "DiagnosisQueryService",
    "FailureClass",
    "claim_diagnosis_query_at_inspect_sha",
    "classify_failure_class",
    "refuse_diagnosis_fourth_store",
    "refuse_join_on_fp1",
    "refuse_qmn_alert_failure_class",
    "refuse_view_as_invoke",
]


DIAGNOSIS_OWNER: Final[str] = "COMP-QMA-DAEMON"
DIAGNOSIS_SQLITE_CLASS_MINTED: Final[bool] = False
QMN_FAILURES_MD_EXTENDED_BY_KIT: Final[bool] = False

_GRANT_VARIANTS: Final[frozenset[str]] = frozenset(
    {
        GrantMismatch.VARIANT,
        GrantInactive.VARIANT,
        GrantWidenRefused.VARIANT,
        ManifestIsNotGrant.VARIANT,
    }
)
_DEPENDENCY_VARIANTS: Final[frozenset[str]] = frozenset(
    {
        NoEnvironment.VARIANT,
        NoMemoryProvider.VARIANT,
        NoEligibleDeployment.VARIANT,
        NoEligibleReviewer.VARIANT,
    }
)
_HOST_VARIANTS: Final[frozenset[str]] = frozenset({StoreVersionMismatch.VARIANT})
_WORKFLOW_JOB_STATES: Final[frozenset[JobHandleState]] = frozenset(
    {JobHandleState.FAILED, JobHandleState.ABORTED}
)


def classify_failure_class(
    *,
    refusal: TypedRefusal,
    job_handle: JobHandle | None = None,
    view_reason: str | None = None,
) -> Result[FailureClass]:
    """Map existing surfaces onto closed kit failure_class (cheap-veto A7)."""
    if view_reason not in (None, ""):
        if view_reason not in VIEW_FAILURE_REASONS:
            return policy_rejection(
                "view_reason",
                "view means the wire DTO failed to mount, was stale, or was unhealthy (DEC-0456)",
                given=view_reason,
                legal=sorted(VIEW_FAILURE_REASONS),
            )
        if job_handle is not None:
            return refuse_view_as_invoke(field="job_handle", given=job_handle.job_id)
        return Ok(FailureClass.VIEW)
    variant = refusal.context.get("variant")
    code = refusal.context.get("code")
    if (isinstance(variant, str) and variant in _GRANT_VARIANTS) or code == "GRANT_MISMATCH":
        return Ok(FailureClass.GRANT)
    if job_handle is not None and job_handle.state in _WORKFLOW_JOB_STATES:
        return Ok(FailureClass.WORKFLOW)
    if isinstance(variant, str) and variant in _DEPENDENCY_VARIANTS:
        return Ok(FailureClass.DEPENDENCY)
    if refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY:
        return Ok(FailureClass.DEPENDENCY)
    if isinstance(variant, str) and variant in _HOST_VARIANTS:
        return Ok(FailureClass.HOST)
    if refusal.category is RefusalCategory.STORAGE_FAILURE:
        return Ok(FailureClass.HOST)
    return Ok(FailureClass.HOST)


@dataclass
class DiagnosisQueryService:
    """Computed diagnosis query. In-process join index, not a sqlite class."""

    jobs: JobHandleService | None = None
    _by_correlation: dict[str, Diagnosis] = field(default_factory=dict[str, Diagnosis])

    @property
    def owner(self) -> str:
        return DIAGNOSIS_OWNER

    def sqlite_class_minted(self) -> bool:
        return DIAGNOSIS_SQLITE_CLASS_MINTED

    def opens_fourth_store(self) -> bool:
        return "diagnosis" in CLOSED_STORE_NAMES or "diagnosis" in CLOSED_INDEPENDENT_STORES

    def observe(
        self,
        *,
        correlation_id: str,
        refusal: TypedRefusal,
        healthy: bool,
        log_line: Mapping[str, object],
        failure_class: object = None,
        job_handle: object = None,
        view_reason: str | None = None,
    ) -> Result[Diagnosis]:
        """Record one failed public operation or Task Graph run for query."""
        handle: JobHandle | Mapping[str, object] | None
        if isinstance(job_handle, JobHandle) or job_handle is None:
            handle = job_handle
        elif isinstance(job_handle, Mapping):
            handle = cast("Mapping[str, object]", job_handle)
        else:
            return invalid_input(
                "job_handle",
                "job_handle is a parent JobHandle payload or null (FR-PG-20)",
                given=repr(job_handle),
            )
        if handle is None and self.jobs is not None:
            handle = self.jobs.handle_for_correlation(correlation_id)
        if failure_class is None:
            resolved_handle: JobHandle | None
            if handle is None or isinstance(handle, JobHandle):
                resolved_handle = handle
            else:
                parsed_handle = JobHandle.from_payload(handle)
                if is_refusal(parsed_handle):
                    return parsed_handle
                resolved_handle = parsed_handle.value
            classified = classify_failure_class(
                refusal=refusal,
                job_handle=resolved_handle,
                view_reason=view_reason,
            )
            if is_refusal(classified):
                return classified
            failure_class = classified.value
        if isinstance(handle, JobHandle):
            handle_payload: Mapping[str, object] | None = dict(handle.to_payload())
            attempt: int | None = handle.attempt_id
        elif handle is None:
            handle_payload = None
            attempt = None
        else:
            handle_payload = dict(handle)
            raw_attempt = handle.get("attempt_id")
            attempt = (
                raw_attempt
                if isinstance(raw_attempt, int) and not isinstance(raw_attempt, bool)
                else None
            )
        parsed = parse_diagnosis(
            {
                "failure_class": (
                    failure_class.value
                    if isinstance(failure_class, FailureClass)
                    else failure_class
                ),
                "job_handle": handle_payload,
                "correlation_id": correlation_id,
                "healthy": healthy,
                "how_it_failed": {
                    "log_line": dict(log_line),
                    "attempt_id": attempt,
                    "refusal": refusal,
                },
                "view_reason": view_reason,
            }
        )
        if is_ok(parsed):
            self._by_correlation[parsed.value.correlation_id] = parsed.value
        return parsed

    def query(self, correlation_id: object) -> Result[Diagnosis]:
        """Headless get_diagnosis snapshot for a correlation_id join key."""
        if not isinstance(correlation_id, str) or correlation_id.strip() == "":
            return invalid_input(
                "correlation_id",
                "diagnosis query requires correlation_id as the join key (never fp1)",
                join_key=DIAGNOSIS_JOIN_KEY,
            )
        token = correlation_id.strip()
        if token.casefold().startswith("fp1"):
            return refuse_join_on_fp1(given=token)
        found = self._by_correlation.get(token)
        if found is None:
            return invalid_input(
                "correlation_id",
                "no diagnosed failure for this correlation_id",
                given=token,
                query=DIAGNOSIS_QUERY_NAME,
            )
        return Ok(found)
