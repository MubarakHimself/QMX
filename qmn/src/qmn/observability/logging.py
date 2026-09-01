"""Structured operator logs — stdlib JSON-lines, never journals (TN-15 / DEC-0200).

One JSON object per journald line. Logs are diagnostic text and never satisfy
CT-13 evidence. Secret values and raw account numbers are forbidden; opaque ids
and credential reference ids only.
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

__all__ = [
    "FORBIDDEN_LOG_KEYS",
    "LOGS_ARE_NOT_JOURNALS",
    "LOGS_SATISFY_CT13_EVIDENCE",
    "NODE_LOG_REQUIRED_FIELDS",
    "JsonLineFormatter",
    "NodeLogContext",
    "bind_log_context",
    "configure_node_logging",
    "emit_node_event",
    "get_log_context",
    "log_record_is_journal_evidence",
    "reset_log_context",
]

LOGS_ARE_NOT_JOURNALS: Final[bool] = True
LOGS_SATISFY_CT13_EVIDENCE: Final[bool] = False

NODE_LOG_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "ts",
    "level",
    "logger",
    "event",
    "boot_epoch",
    "composition_fp",
    "world",
    "correlation_id",
)

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
    "qmn_node_log_context",
    default=None,
)


@dataclass(frozen=True, slots=True)
class NodeLogContext:
    """Boot-scoped fields stamped onto every operator log record."""

    boot_epoch: str
    composition_fp: str
    world: str = "live"
    correlation_id: str = ""
    stream: str | None = None
    account_opaque_id: str | None = None
    seat_id: str | None = None
    binding_id: str | None = None

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "boot_epoch": self.boot_epoch,
            "composition_fp": self.composition_fp,
            "world": self.world,
            "correlation_id": self.correlation_id,
        }
        if self.stream is not None:
            body["stream"] = self.stream
        if self.account_opaque_id is not None:
            body["account_opaque_id"] = self.account_opaque_id
        if self.seat_id is not None:
            body["seat_id"] = self.seat_id
        if self.binding_id is not None:
            body["binding_id"] = self.binding_id
        return MappingProxyType(body)


def bind_log_context(context: NodeLogContext) -> object:
    """Bind context for the current task; returns a token for :func:`reset_log_context`."""
    return _CONTEXT.set(context.as_mapping())


def reset_log_context(token: object) -> None:
    _CONTEXT.reset(token)  # type: ignore[arg-type]


def get_log_context() -> Mapping[str, object]:
    bound = _CONTEXT.get()
    return MappingProxyType(dict(bound)) if bound is not None else MappingProxyType({})


def log_record_is_journal_evidence(_record: object = None) -> bool:
    """Operator logs never satisfy CT-13 — always False (NFR-16)."""
    return False


def _utc_ts_ms(record: logging.LogRecord) -> str:
    instant = datetime.fromtimestamp(record.created, tz=UTC)
    return instant.strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(record.msecs):03d}Z"


def _scrub(payload: MutableMapping[str, object]) -> None:
    for key in list(payload):
        lowered = key.lower()
        if lowered in FORBIDDEN_LOG_KEYS or any(
            token in lowered for token in ("secret_value", "account_number", "raw_account")
        ):
            payload.pop(key)


class JsonLineFormatter(logging.Formatter):
    """Emit one JSON object per line for journald capture."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": _utc_ts_ms(record),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
            "boot_epoch": "",
            "composition_fp": "",
            "world": "live",
            "correlation_id": "",
        }
        payload.update(dict(get_log_context()))
        for key in (
            "boot_epoch",
            "composition_fp",
            "world",
            "correlation_id",
            "stream",
            "account_opaque_id",
            "seat_id",
            "binding_id",
            "failure_id",
            "category",
            "retryability",
            "after_condition",
            "event",
        ):
            if hasattr(record, key):
                value = getattr(record, key)
                if value is not None:
                    payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        _scrub(payload)
        payload["ct13_evidence"] = False
        payload["is_journal"] = False
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_node_logging(
    *,
    level: int = logging.INFO,
    handler: logging.Handler | None = None,
    logger_name: str = "qmn",
) -> logging.Logger:
    """Attach the JSON-lines formatter to the node logger (stdout → journald)."""
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.setLevel(level)
    logger.propagate = False
    target = handler if handler is not None else logging.StreamHandler()
    target.setFormatter(JsonLineFormatter())
    logger.addHandler(target)
    return logger


def emit_node_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    correlation_id: str | None = None,
    failure_id: str | None = None,
    category: str | None = None,
    retryability: str | None = None,
    after_condition: str | None = None,
    stream: str | None = None,
    account_opaque_id: str | None = None,
    seat_id: str | None = None,
    binding_id: str | None = None,
    **extra: object,
) -> None:
    """Emit one structured operator event; never writes a journal."""
    for banned in FORBIDDEN_LOG_KEYS:
        if banned in extra:
            msg = f"operator logs forbid field {banned!r}"
            raise ValueError(msg)
    record_extra: dict[str, object] = {"event": event}
    if correlation_id is not None:
        record_extra["correlation_id"] = correlation_id
    if failure_id is not None:
        record_extra["failure_id"] = failure_id
    if category is not None:
        record_extra["category"] = category
    if retryability is not None:
        record_extra["retryability"] = retryability
    if after_condition is not None:
        record_extra["after_condition"] = after_condition
    if stream is not None:
        record_extra["stream"] = stream
    if account_opaque_id is not None:
        record_extra["account_opaque_id"] = account_opaque_id
    if seat_id is not None:
        record_extra["seat_id"] = seat_id
    if binding_id is not None:
        record_extra["binding_id"] = binding_id
    for key, value in extra.items():
        record_extra[key] = value
    logger.log(level, event, extra=record_extra)
