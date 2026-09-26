"""Stdlib JSON-lines operator logs for qma-daemon (Story 61.1; kit AD-5).

Required fields: ``ts``, ``level``, ``event``, ``correlation_id``. Join fields
``instance_id``, ``op_id``, ``logical_invocation_id``, ``graph_run_id`` appear
only when known (cheap-veto A8). Lines are never a journal, never secret
values, never ``fp1`` identity, and never evidence (parent AD-16; DEC-0456).
Not a fourth observability product and not a new sqlite class. QMA telemetry
store remains the trace/metric plane; OTel remains export-port only.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, MutableMapping
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Final

from qma.daemon.journal.stores import CLOSED_INDEPENDENT_STORES, CLOSED_STORE_NAMES
from qma.daemon.telemetry.export import DAEMON_CORE_OTEL_IMPORT_FORBIDDEN
from qmf.core import Ok, Result
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "DAEMON_CORE_OTEL_IMPORT_FORBIDDEN",
    "EPIC_60_TIP_SHA",
    "FORBIDDEN_LOG_KEYS",
    "FOURTH_OBSERVABILITY_COMP_MINTED",
    "LOGS_ARE_NOT_EVIDENCE",
    "LOGS_ARE_NOT_JOURNALS",
    "LOGS_ENTER_FP1_IDENTITY",
    "LOGS_SATISFY_CT13_EVIDENCE",
    "OPERATOR_LOGGER_EXISTED_AT_EPIC_60_TIP",
    "OPERATOR_LOGGER_EXISTED_AT_INSPECT_SHA",
    "OPERATOR_LOG_INSPECT_SHA",
    "OPERATOR_LOG_JOIN_FIELDS",
    "OPERATOR_LOG_LOGGER_NAME",
    "OPERATOR_LOG_REQUIRED_FIELDS",
    "OPERATOR_LOG_SQLITE_CLASS_MINTED",
    "OTEL_REMAINS_EXPORT_PORT_ONLY",
    "QMN_FAILURES_MD_EXTENDED",
    "TELEMETRY_STORE_REMAINS_TRACE_METRIC_PLANE",
    "JsonLineFormatter",
    "OperatorLogContext",
    "bind_log_context",
    "claim_operator_logger_at_inspect_sha",
    "configure_daemon_logging",
    "emit_operator_event",
    "fingerprint_operator_log",
    "get_log_context",
    "log_record_is_journal_evidence",
    "refuse_fourth_observability_comp",
    "refuse_operator_log_sqlite_class",
    "refuse_qmn_failures_extension",
    "reset_log_context",
]


OPERATOR_LOG_INSPECT_SHA: Final[str] = "34c148b"
EPIC_60_TIP_SHA: Final[str] = "7223e1a"
OPERATOR_LOGGER_EXISTED_AT_INSPECT_SHA: Final[bool] = False
OPERATOR_LOGGER_EXISTED_AT_EPIC_60_TIP: Final[bool] = False

OPERATOR_LOG_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "ts",
    "level",
    "event",
    "correlation_id",
)
OPERATOR_LOG_JOIN_FIELDS: Final[tuple[str, ...]] = (
    "instance_id",
    "op_id",
    "logical_invocation_id",
    "graph_run_id",
)
OPERATOR_LOG_LOGGER_NAME: Final[str] = "qma.daemon.operator"

LOGS_ARE_NOT_JOURNALS: Final[bool] = True
LOGS_ARE_NOT_EVIDENCE: Final[bool] = True
LOGS_SATISFY_CT13_EVIDENCE: Final[bool] = False
LOGS_ENTER_FP1_IDENTITY: Final[bool] = False
FOURTH_OBSERVABILITY_COMP_MINTED: Final[bool] = False
OPERATOR_LOG_SQLITE_CLASS_MINTED: Final[bool] = False
QMN_FAILURES_MD_EXTENDED: Final[bool] = False
OTEL_REMAINS_EXPORT_PORT_ONLY: Final[bool] = DAEMON_CORE_OTEL_IMPORT_FORBIDDEN
TELEMETRY_STORE_REMAINS_TRACE_METRIC_PLANE: Final[bool] = True

FORBIDDEN_LOG_KEYS: Final[frozenset[str]] = frozenset(
    {
        "secret",
        "secret_value",
        "password",
        "token",
        "credential",
        "account_number",
        "raw_account",
        "api_key",
        "private_key",
    }
)

_CONTEXT: ContextVar[Mapping[str, object] | None] = ContextVar(
    "qma_daemon_operator_log_context",
    default=None,
)


@dataclass(frozen=True, slots=True)
class OperatorLogContext:
    """Join fields stamped onto operator log records when known."""

    correlation_id: str
    instance_id: str | None = None
    op_id: str | None = None
    logical_invocation_id: str | None = None
    graph_run_id: str | None = None

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {"correlation_id": self.correlation_id}
        _put_join_field(body, "instance_id", self.instance_id)
        _put_join_field(body, "op_id", self.op_id)
        _put_join_field(body, "logical_invocation_id", self.logical_invocation_id)
        _put_join_field(body, "graph_run_id", self.graph_run_id)
        return MappingProxyType(body)


def bind_log_context(context: OperatorLogContext) -> object:
    """Bind join fields for the current task; token is for :func:`reset_log_context`."""
    return _CONTEXT.set(context.as_mapping())


def reset_log_context(token: object) -> None:
    _CONTEXT.reset(token)  # type: ignore[arg-type]


def get_log_context() -> Mapping[str, object]:
    bound = _CONTEXT.get()
    return MappingProxyType(dict(bound)) if bound is not None else MappingProxyType({})


def log_record_is_journal_evidence(_record: object = None) -> bool:
    """Operator logs never satisfy CT-13 — always False (parent AD-16)."""
    return False


def _put_join_field(body: MutableMapping[str, object], key: str, value: object) -> None:
    if isinstance(value, str) and value.strip():
        body[key] = value.strip()


def _utc_ts_ms(record: logging.LogRecord) -> str:
    instant = datetime.fromtimestamp(record.created, tz=UTC)
    return instant.strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(record.msecs):03d}Z"


def _key_is_forbidden(key: str) -> bool:
    lowered = key.lower()
    if lowered in FORBIDDEN_LOG_KEYS:
        return True
    return any(token in lowered for token in FORBIDDEN_LOG_KEYS)


def _forbidden_present(payload: Mapping[str, object]) -> tuple[str, ...]:
    return tuple(sorted(key for key in payload if _key_is_forbidden(str(key))))


def _scrub(payload: MutableMapping[str, object]) -> None:
    for key in _forbidden_present(payload):
        payload.pop(key, None)


def _record_join_fields(record: logging.LogRecord) -> dict[str, object]:
    body: dict[str, object] = {}
    for key in ("correlation_id", *OPERATOR_LOG_JOIN_FIELDS):
        if hasattr(record, key):
            _put_join_field(body, key, getattr(record, key))
    return body


class JsonLineFormatter(logging.Formatter):
    """Emit one JSON object per line. Never a journal and never fp1 identity."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": _utc_ts_ms(record),
            "level": record.levelname,
            "event": getattr(record, "event", record.getMessage()),
            "correlation_id": "",
        }
        payload.update(dict(get_log_context()))
        payload.update(_record_join_fields(record))
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        _scrub(payload)
        payload["is_journal"] = False
        payload["ct13_evidence"] = False
        payload["fp1_identity"] = False
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_daemon_logging(
    *,
    level: int = logging.INFO,
    handler: logging.Handler | None = None,
    logger_name: str = OPERATOR_LOG_LOGGER_NAME,
) -> logging.Logger:
    """Attach the JSON-lines formatter. Stdlib logging, not a new logger product."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.propagate = False
    if handler is not None:
        logger.handlers.clear()
        target = handler
    elif logger.handlers:
        return logger
    else:
        target = logging.NullHandler()
    target.setFormatter(JsonLineFormatter())
    logger.addHandler(target)
    return logger


def emit_operator_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    correlation_id: str,
    instance_id: str | None = None,
    op_id: str | None = None,
    logical_invocation_id: str | None = None,
    graph_run_id: str | None = None,
    **extra: object,
) -> Result[None]:
    """Emit one structured operator event; never writes a journal or sqlite class."""
    if not event.strip():
        return invalid_input("event", "operator logs require a non-empty event name")
    if not correlation_id.strip():
        return invalid_input(
            "correlation_id",
            "operator logs require correlation_id (kit AD-5; DEC-0456)",
        )
    banned = _forbidden_present(extra)
    if banned:
        return policy_rejection(
            "operator_log",
            "operator logs never carry secret values (FR-PG-22; DEC-0456)",
            keys=list(banned),
            is_journal=False,
            fp1_identity=False,
        )
    record_extra: dict[str, object] = {
        "event": event.strip(),
        "correlation_id": correlation_id.strip(),
    }
    _put_join_field(record_extra, "instance_id", instance_id)
    _put_join_field(record_extra, "op_id", op_id)
    _put_join_field(record_extra, "logical_invocation_id", logical_invocation_id)
    _put_join_field(record_extra, "graph_run_id", graph_run_id)
    record_extra.update(extra)
    logger.log(level, event.strip(), extra=record_extra)
    return Ok(None)


def claim_operator_logger_at_inspect_sha(existed: object) -> Result[bool]:
    """Claiming the operator logger existed at inspect SHA 34c148b fails."""
    if existed is True or existed == "true":
        return policy_rejection(
            "operator_logger",
            "qma-daemon stdlib JSON-lines operator logger was absent at inspect SHA "
            "34c148b and at epic 60 tip 7223e1a; it is Story 61.1 (DEC-0465; "
            "SCN-0027 Branch E)",
            existed_at_inspect_sha=False,
            inspect_sha=OPERATOR_LOG_INSPECT_SHA,
            epic_60_tip_sha=EPIC_60_TIP_SHA,
            existed_at_epic_60_tip=False,
        )
    if existed is not False:
        return invalid_input(
            "existed_at_inspect_sha",
            "inspect-SHA claim is a boolean",
            given=repr(existed),
        )
    return Ok(False)


def refuse_fourth_observability_comp(**extra: object) -> Result[None]:
    """A new observability COMP for mini-app logs is refused (NFR-PG-02)."""
    extra.setdefault("minted", FOURTH_OBSERVABILITY_COMP_MINTED)
    extra.setdefault("telemetry_store_remains", TELEMETRY_STORE_REMAINS_TRACE_METRIC_PLANE)
    extra.setdefault("otel_export_port_only", OTEL_REMAINS_EXPORT_PORT_ONLY)
    return policy_rejection(
        str(extra.pop("field", "observability_comp")),
        "refuse a new observability COMP; QMA telemetry store remains the "
        "trace/metric plane and OTel remains export-port only (NFR-PG-02; "
        "SCN-0027 Branch A; DEC-0456)",
        **extra,
    )


def refuse_operator_log_sqlite_class(**extra: object) -> Result[None]:
    """Operator logs are not a new sqlite class on the closed store list."""
    extra.setdefault("minted", OPERATOR_LOG_SQLITE_CLASS_MINTED)
    extra.setdefault("closed_independent_stores", sorted(CLOSED_INDEPENDENT_STORES))
    extra.setdefault("operator_logs_on_closed_list", "operator_logs" in CLOSED_STORE_NAMES)
    return policy_rejection(
        str(extra.pop("field", "sqlite_class")),
        "operator logs are stdlib JSON-lines, not a new sqlite class and not a "
        "fourth observability store (NFR-PG-02; DEC-0305; DEC-0456)",
        **extra,
    )


def refuse_qmn_failures_extension(**extra: object) -> Result[None]:
    """Mini-app / daemon logs do not extend qmn/FAILURES.md."""
    extra.setdefault("extended", QMN_FAILURES_MD_EXTENDED)
    return policy_rejection(
        str(extra.pop("field", "qmn_failures")),
        "do not extend qmn/FAILURES.md; daemon JSON-lines stay on COMP-QMA-DAEMON "
        "(DEC-0456; SCN-0027 Branch C)",
        **extra,
    )


def fingerprint_operator_log(_payload: object = None) -> Result[None]:
    """Operator log lines never enter fp1 identity (parent AD-16)."""
    return policy_rejection(
        "fp1",
        "operator log lines do not enter fp1 identity and are not evidence "
        "(parent AD-16; FR-PG-22; DEC-0456; SCN-0027 Branch B)",
        fp1_identity=False,
        is_journal=False,
        is_evidence=False,
        logs_enter_fp1=LOGS_ENTER_FP1_IDENTITY,
    )
