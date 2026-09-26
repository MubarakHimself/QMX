"""CT-40 additive diagnosis query DTO (Story 61.2; kit AD-5; DEC-0456).

Headless query returns ``failure_class``, ``job_handle`` (or null),
``correlation_id``, and ``healthy``. How-it-failed is the operator log line
plus JobHandle ``attempt_id`` plus typed refusal. No fourth store. ``view``
is mount/stale/unhealthy of a wire DTO — not an invoke. ``correlation_id``
is the join key (never fp1). JobHandle stays on QMA AD-17 vocabulary
(Story 57.3). QMN alert ``failure_class`` is a different noun. Inspect SHA
``34c148b`` did not have this query. No new CT number (do not mint CT-52).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qma.core.ports.jobs import (
    JOB_HANDLE_FORBIDDEN_STATES,
    JobHandle,
    is_forbidden_job_handle_state,
)
from qma.core.vocabulary.enums import FailureClass
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)

__all__ = [
    "DIAGNOSIS_CONTRACT",
    "DIAGNOSIS_DTO_OWNER",
    "DIAGNOSIS_EXISTED_AT_INSPECT_SHA",
    "DIAGNOSIS_FOURTH_STORE_MINTED",
    "DIAGNOSIS_INSPECT_SHA",
    "DIAGNOSIS_JOIN_KEY",
    "DIAGNOSIS_NEW_CT_MINTED",
    "DIAGNOSIS_QUERY_NAME",
    "DIAGNOSIS_REFUSED_CT",
    "DIAGNOSIS_SCHEMA",
    "DIAGNOSIS_SCHEMA_FILE",
    "DIAGNOSIS_SCHEMA_NAME",
    "FAILURE_CLASSES",
    "FORBIDDEN_FAILURE_CLASSES",
    "QMN_ALERT_FAILURE_CLASSES",
    "VIEW_FAILURE_REASONS",
    "Diagnosis",
    "FailureClass",
    "claim_diagnosis_query_at_inspect_sha",
    "parse_diagnosis",
    "refuse_diagnosis_fourth_store",
    "refuse_join_on_fp1",
    "refuse_qmn_alert_failure_class",
    "refuse_view_as_invoke",
    "validate_diagnosis",
]


DIAGNOSIS_DTO_OWNER: Final[str] = "COMP-QMA-WIRE"
DIAGNOSIS_CONTRACT: Final[str] = "CT-40"
DIAGNOSIS_NEW_CT_MINTED: Final[bool] = False
DIAGNOSIS_REFUSED_CT: Final[str] = "CT-52"
DIAGNOSIS_SCHEMA: Final[str] = "qma.wire.diagnosis.v1"
DIAGNOSIS_SCHEMA_NAME: Final[str] = "diagnosis"
DIAGNOSIS_SCHEMA_FILE: Final[str] = "diagnosis.v1.schema.json"
DIAGNOSIS_INSPECT_SHA: Final[str] = "34c148b"
DIAGNOSIS_EXISTED_AT_INSPECT_SHA: Final[bool] = False
DIAGNOSIS_FOURTH_STORE_MINTED: Final[bool] = False
DIAGNOSIS_JOIN_KEY: Final[str] = "correlation_id"
DIAGNOSIS_QUERY_NAME: Final[str] = "get_diagnosis"

FAILURE_CLASSES: Final[frozenset[str]] = frozenset(member.value for member in FailureClass)
VIEW_FAILURE_REASONS: Final[frozenset[str]] = frozenset({"unmounted", "stale", "unhealthy"})

# QMN alert allow-list nouns plus CT-04 categories used as a false kit class.
QMN_ALERT_FAILURE_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "money-boundary",
        "money boundary",
        "protection-escalation",
        "protection escalation",
        "silent-degradation",
        "silent degradation",
        "stand-down",
        "stand-down alarm",
    }
)
_CT04_AS_KIT_CLASS: Final[frozenset[str]] = frozenset(
    member.value.replace("_", " ") for member in RefusalCategory
) | frozenset(member.value for member in RefusalCategory)

FORBIDDEN_FAILURE_CLASSES: Final[frozenset[str]] = (
    frozenset({"widget", "invoke", "succeeded", "awaiting_approval"})
    | QMN_ALERT_FAILURE_CLASSES
    | _CT04_AS_KIT_CLASS
    | JOB_HANDLE_FORBIDDEN_STATES
)

_LOG_REQUIRED_FIELDS: Final[tuple[str, ...]] = ("ts", "level", "event", "correlation_id")
_REFUSAL_REQUIRED_FIELDS: Final[tuple[str, ...]] = ("category", "retryability", "context")


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def refuse_qmn_alert_failure_class(**extra: object) -> TypedRefusal:
    """QMN alert failure_class is a different noun (NFR-PG-14; DEC-0456)."""
    extra.setdefault("qmn_alert_noun", True)
    extra.setdefault("kit_classes", sorted(FAILURE_CLASSES))
    extra.setdefault("extended_qmn_failures_md", False)
    return _policy(
        str(extra.pop("field", "failure_class")),
        "QMN alert failure_class is a different noun; kit diagnosis is closed "
        "grant | workflow | view | dependency | host and must not extend "
        "qmn/FAILURES.md (NFR-PG-14; DEC-0456; SCN-0027 Branch C)",
        **extra,
    )


def refuse_view_as_invoke(**extra: object) -> TypedRefusal:
    """``failure_class=view`` is mount/stale/unhealthy, not an invoke."""
    extra.setdefault("is_invoke", False)
    extra.setdefault("view_reasons", sorted(VIEW_FAILURE_REASONS))
    return _policy(
        str(extra.pop("field", "failure_class")),
        "view means the wire DTO failed to mount, was stale, or was unhealthy "
        "— it is not an invoke (DEC-0456; FR-PG-19; cheap-veto A7)",
        **extra,
    )


def refuse_join_on_fp1(**extra: object) -> TypedRefusal:
    """Diagnosis joins on correlation_id, never fp1 (kit AD-5; parent AD-16)."""
    extra.setdefault("join_key", DIAGNOSIS_JOIN_KEY)
    extra.setdefault("fp1_identity", False)
    return _policy(
        str(extra.pop("field", "correlation_id")),
        "correlation_id is the diagnosis join key and never fp1 (DEC-0456; FR-PG-20; parent AD-16)",
        **extra,
    )


def refuse_diagnosis_fourth_store(**extra: object) -> TypedRefusal:
    """Diagnosis is a computed query, not a fourth store (NFR-PG-02)."""
    extra.setdefault("minted", DIAGNOSIS_FOURTH_STORE_MINTED)
    extra.setdefault("new_ct_minted", DIAGNOSIS_NEW_CT_MINTED)
    extra.setdefault("contract", DIAGNOSIS_CONTRACT)
    return _policy(
        str(extra.pop("field", "sqlite_class")),
        "how-it-failed is the log line plus JobHandle attempt_id plus typed "
        "refusal; no fourth store (FR-PG-20; NFR-PG-02; DEC-0456)",
        **extra,
    )


def claim_diagnosis_query_at_inspect_sha(existed: object) -> Result[bool]:
    """Claiming this diagnosis query existed at inspect SHA 34c148b fails."""
    if existed is True or existed == "true":
        return _policy(
            "diagnosis_query",
            "kit failure_class diagnosis query was absent at inspect SHA "
            "34c148b; it is Story 61.2 (DEC-0465; NFR-PG-04; SCN-0027)",
            existed_at_inspect_sha=False,
            inspect_sha=DIAGNOSIS_INSPECT_SHA,
        )
    if existed is not False:
        return _invalid(
            "existed_at_inspect_sha",
            "inspect-SHA claim is a boolean",
            given=repr(existed),
        )
    return Ok(False)


def _looks_like_fp1(value: str) -> bool:
    folded = value.strip().casefold()
    return folded.startswith("fp1:") or folded.startswith("fp1")


def _parse_correlation_id(value: object) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(
            "correlation_id",
            "diagnosis correlation_id is a non-empty join key (never fp1)",
            given=repr(value),
            join_key=DIAGNOSIS_JOIN_KEY,
        )
    token = value.strip()
    if _looks_like_fp1(token):
        return refuse_join_on_fp1(given=token)
    return Ok(token)


def _parse_failure_class(value: object) -> Result[FailureClass]:
    raw = value.value if isinstance(value, FailureClass) else value
    if isinstance(raw, str):
        token = raw.strip()
        folded = token.casefold()
        if folded in FORBIDDEN_FAILURE_CLASSES or token in FORBIDDEN_FAILURE_CLASSES:
            if folded in QMN_ALERT_FAILURE_CLASSES or token in QMN_ALERT_FAILURE_CLASSES:
                return refuse_qmn_alert_failure_class(given=token)
            if folded == "widget":
                return refuse_view_as_invoke(
                    field="failure_class",
                    given=token,
                    widget_class_refused=True,
                )
            return _policy(
                "failure_class",
                "failure_class is closed grant | workflow | view | dependency | "
                "host (DEC-0456; cheap-veto A7; FR-PG-19)",
                given=token,
                legal=sorted(FAILURE_CLASSES),
            )
    try:
        return Ok(parse_closed(FailureClass, value))
    except VocabularyError as exc:
        given = value.value if isinstance(value, FailureClass) else value
        return _policy(
            "failure_class",
            str(exc),
            given=repr(given),
            legal=sorted(FAILURE_CLASSES),
        )


def _parse_healthy(value: object) -> Result[bool]:
    if not isinstance(value, bool):
        return _invalid(
            "healthy",
            "diagnosis healthy is the listing-axis boolean (DEC-0456)",
            given=repr(value),
        )
    return Ok(value)


def _parse_job_handle(value: object) -> Result[JobHandle | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, JobHandle):
        if is_forbidden_job_handle_state(value.state):
            return _policy(
                "job_handle.state",
                "JobHandle stays on QMA AD-17 vocabulary; never succeeded or "
                "awaiting_approval (FR-PG-20; Story 57.3)",
                given=value.state.value,
            )
        return Ok(value)
    if not isinstance(value, Mapping):
        return _invalid(
            "job_handle",
            "job_handle is a parent JobHandle payload or null (FR-PG-20)",
            given=repr(value),
        )
    body = cast("Mapping[str, object]", value)
    raw_state = body.get("state")
    if is_forbidden_job_handle_state(raw_state):
        return _policy(
            "job_handle.state",
            "JobHandle stays on QMA AD-17 vocabulary; never succeeded or "
            "awaiting_approval (FR-PG-20; Story 57.3)",
            given=raw_state,
        )
    parsed = JobHandle.from_payload(body)
    if is_refusal(parsed):
        return parsed
    return Ok(parsed.value)


def _parse_log_line(value: object, *, correlation_id: str) -> Result[Mapping[str, object]]:
    if not isinstance(value, Mapping):
        return _invalid(
            "how_it_failed.log_line",
            "how-it-failed log line is the operator JSON-line object (FR-PG-20)",
            given=repr(value),
        )
    body = {str(key): item for key, item in cast("Mapping[object, object]", value).items()}
    missing = [field for field in _LOG_REQUIRED_FIELDS if field not in body]
    if missing:
        return _invalid(
            "how_it_failed.log_line",
            "operator log line requires ts, level, event, correlation_id (FR-PG-21)",
            missing=missing,
        )
    line_corr = body.get("correlation_id")
    if not isinstance(line_corr, str) or line_corr.strip() != correlation_id:
        return _invalid(
            "how_it_failed.log_line.correlation_id",
            "log line joins diagnosis on correlation_id (never fp1)",
            given=repr(line_corr),
            expected=correlation_id,
            join_key=DIAGNOSIS_JOIN_KEY,
        )
    if body.get("fp1_identity") is True or "fp1" in body:
        return refuse_join_on_fp1(field="how_it_failed.log_line")
    if body.get("is_journal") is True:
        return _policy(
            "how_it_failed.log_line",
            "operator logs are never a journal (FR-PG-22; DEC-0456)",
            is_journal=False,
        )
    return Ok(MappingProxyType(body))


def _parse_refusal(value: object) -> Result[Mapping[str, object]]:
    if isinstance(value, TypedRefusal):
        payload: dict[str, object] = {
            "category": value.category.value,
            "retryability": value.retryability.value,
            "context": dict(value.context),
        }
        if value.after_condition_descriptor is not None:
            payload["after_condition_descriptor"] = value.after_condition_descriptor
        return Ok(MappingProxyType(payload))
    if not isinstance(value, Mapping):
        return _invalid(
            "how_it_failed.refusal",
            "how-it-failed refusal is a CT-04 typed refusal (FR-PG-20)",
            given=repr(value),
        )
    body = {str(key): item for key, item in cast("Mapping[object, object]", value).items()}
    missing = [field for field in _REFUSAL_REQUIRED_FIELDS if field not in body]
    if missing:
        return _invalid(
            "how_it_failed.refusal",
            "typed refusal requires category, retryability, and context (CT-04)",
            missing=missing,
        )
    category = body["category"]
    retryability = body["retryability"]
    if not isinstance(category, str) or not isinstance(retryability, str):
        return _invalid(
            "how_it_failed.refusal",
            "typed refusal category and retryability are strings (CT-04)",
        )
    raw_context = body.get("context")
    context: Mapping[str, object] | None
    if isinstance(raw_context, Mapping):
        context = cast("Mapping[str, object]", raw_context)
    else:
        context = None
    raw_descriptor = body.get("after_condition_descriptor")
    descriptor = raw_descriptor if isinstance(raw_descriptor, str) else None
    checked = TypedRefusal.try_create(
        category,
        retryability,
        context=context,
        after_condition_descriptor=descriptor,
    )
    if is_refusal(checked):
        return checked
    return _parse_refusal(checked.value)


def _parse_how_it_failed(
    value: object,
    *,
    correlation_id: str,
    job_handle: JobHandle | None,
) -> Result[tuple[Mapping[str, object], Mapping[str, object], int | None]]:
    if not isinstance(value, Mapping):
        return _invalid(
            "how_it_failed",
            "how-it-failed is the log line plus JobHandle attempt_id plus typed refusal (FR-PG-20)",
            given=repr(value),
        )
    body = cast("Mapping[str, object]", value)
    log_line = _parse_log_line(body.get("log_line"), correlation_id=correlation_id)
    if is_refusal(log_line):
        return log_line
    refusal = _parse_refusal(body.get("refusal"))
    if is_refusal(refusal):
        return refusal
    raw_attempt = body.get("attempt_id")
    expected = None if job_handle is None else job_handle.attempt_id
    if raw_attempt is None:
        if expected is not None:
            return _invalid(
                "how_it_failed.attempt_id",
                "attempt_id is the JobHandle attempt_id when a handle is present",
                expected=expected,
            )
        attempt: int | None = None
    elif isinstance(raw_attempt, bool) or not isinstance(raw_attempt, int) or raw_attempt < 1:
        return _invalid(
            "how_it_failed.attempt_id",
            "attempt_id is a positive integer or null when job_handle is null",
            given=repr(raw_attempt),
        )
    else:
        if expected is None:
            return _invalid(
                "how_it_failed.attempt_id",
                "attempt_id is null when job_handle is null (no job was accepted)",
                given=raw_attempt,
            )
        if raw_attempt != expected:
            return _invalid(
                "how_it_failed.attempt_id",
                "attempt_id must match JobHandle.attempt_id (FR-PG-20)",
                given=raw_attempt,
                expected=expected,
            )
        attempt = raw_attempt
    return Ok((log_line.value, refusal.value, attempt))


def _parse_view_reason(
    value: object,
    *,
    failure_class: FailureClass,
    job_handle: JobHandle | None,
) -> Result[str | None]:
    if value in (None, ""):
        if failure_class is FailureClass.VIEW:
            return _invalid(
                "view_reason",
                "view diagnosis names unmounted | stale | unhealthy (DEC-0456)",
            )
        return Ok(None)
    if not isinstance(value, str):
        return _invalid("view_reason", "view_reason is a closed view failure token")
    token = value.strip()
    if token not in VIEW_FAILURE_REASONS:
        return _policy(
            "view_reason",
            "view means the wire DTO failed to mount, was stale, or was unhealthy",
            given=token,
            legal=sorted(VIEW_FAILURE_REASONS),
        )
    if failure_class is not FailureClass.VIEW:
        return refuse_view_as_invoke(field="view_reason", given=token)
    if job_handle is not None:
        return refuse_view_as_invoke(field="job_handle", given=job_handle.job_id)
    return Ok(token)


@dataclass(frozen=True, slots=True)
class Diagnosis:
    """Headless kit diagnosis DTO — additive CT-40, not a new contract id."""

    failure_class: FailureClass
    job_handle: JobHandle | None
    correlation_id: str
    healthy: bool
    log_line: Mapping[str, object]
    refusal: Mapping[str, object]
    view_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "log_line", MappingProxyType(dict(self.log_line)))
        object.__setattr__(self, "refusal", MappingProxyType(dict(self.refusal)))

    @property
    def attempt_id(self) -> int | None:
        return None if self.job_handle is None else self.job_handle.attempt_id

    @property
    def how_it_failed(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "log_line": dict(self.log_line),
                "attempt_id": self.attempt_id,
                "refusal": dict(self.refusal),
            }
        )

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "correlation_id": self.correlation_id,
            "failure_class": self.failure_class.value,
            "healthy": self.healthy,
            "how_it_failed": dict(self.how_it_failed),
            "job_handle": (None if self.job_handle is None else dict(self.job_handle.to_payload())),
        }
        if self.view_reason is not None:
            payload["view_reason"] = self.view_reason
        return MappingProxyType(payload)

    @classmethod
    def try_create(
        cls,
        *,
        failure_class: object,
        job_handle: object = None,
        correlation_id: object,
        healthy: object,
        how_it_failed: object,
        view_reason: object = None,
        fp1: object = None,
        **extra: object,
    ) -> Result[Diagnosis]:
        if fp1 not in (None, ""):
            return refuse_join_on_fp1(field="fp1", given=repr(fp1))
        if "fp1" in extra:
            return refuse_join_on_fp1(field="fp1")
        parsed_class = _parse_failure_class(failure_class)
        if is_refusal(parsed_class):
            return parsed_class
        parsed_corr = _parse_correlation_id(correlation_id)
        if is_refusal(parsed_corr):
            return parsed_corr
        parsed_healthy = _parse_healthy(healthy)
        if is_refusal(parsed_healthy):
            return parsed_healthy
        parsed_handle = _parse_job_handle(job_handle)
        if is_refusal(parsed_handle):
            return parsed_handle
        if parsed_class.value is FailureClass.VIEW and parsed_handle.value is not None:
            return refuse_view_as_invoke(
                field="job_handle",
                given=parsed_handle.value.job_id,
            )
        if parsed_class.value is FailureClass.WORKFLOW and parsed_handle.value is None:
            return _invalid(
                "job_handle",
                "workflow diagnosis carries the failed Task Graph JobHandle",
            )
        parsed_view = _parse_view_reason(
            view_reason,
            failure_class=parsed_class.value,
            job_handle=parsed_handle.value,
        )
        if is_refusal(parsed_view):
            return parsed_view
        parsed_how = _parse_how_it_failed(
            how_it_failed,
            correlation_id=parsed_corr.value,
            job_handle=parsed_handle.value,
        )
        if is_refusal(parsed_how):
            return parsed_how
        log_line, refusal, _attempt = parsed_how.value
        return Ok(
            cls(
                failure_class=parsed_class.value,
                job_handle=parsed_handle.value,
                correlation_id=parsed_corr.value,
                healthy=parsed_healthy.value,
                log_line=log_line,
                refusal=refusal,
                view_reason=parsed_view.value,
            )
        )


def parse_diagnosis(value: object) -> Result[Diagnosis]:
    """Parse the additive CT-40 diagnosis query DTO."""
    if isinstance(value, Diagnosis):
        return Diagnosis.try_create(
            failure_class=value.failure_class,
            job_handle=value.job_handle,
            correlation_id=value.correlation_id,
            healthy=value.healthy,
            how_it_failed=dict(value.how_it_failed),
            view_reason=value.view_reason,
        )
    if not isinstance(value, Mapping):
        return _invalid(
            "diagnosis",
            "Diagnosis is a mapping of kit AD-5 query fields (CT-40; DEC-0456)",
            given=repr(value),
        )
    body = cast("Mapping[str, object]", value)
    how = body.get("how_it_failed")
    if how is None and {"log_line", "refusal"} <= set(body):
        how = {
            "log_line": body.get("log_line"),
            "attempt_id": body.get("attempt_id"),
            "refusal": body.get("refusal"),
        }
    return Diagnosis.try_create(
        failure_class=body.get("failure_class"),
        job_handle=body.get("job_handle"),
        correlation_id=body.get("correlation_id"),
        healthy=body.get("healthy"),
        how_it_failed=how,
        view_reason=body.get("view_reason"),
        fp1=body.get("fp1"),
    )


def validate_diagnosis(value: object) -> Result[Diagnosis]:
    """Schema-then-DTO validation for the additive CT-40 diagnosis query."""
    from qma.wire.schemas import validate_instance  # noqa: PLC0415

    if isinstance(value, Diagnosis):
        payload = dict(value.to_payload())
    elif isinstance(value, Mapping):
        payload = dict(cast("Mapping[str, object]", value))
    else:
        return parse_diagnosis(value)
    checked = validate_instance(payload, DIAGNOSIS_SCHEMA_NAME)
    if is_refusal(checked):
        return checked
    return parse_diagnosis(checked.value)
