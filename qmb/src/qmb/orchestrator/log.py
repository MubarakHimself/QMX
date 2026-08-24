"""Per-run AD-14 operational logs. Orchestrator-owned injected sink (B-4, AR-35).

The library's ``run()`` writes no log. This module is the impure owner of the
injected per-run log sink: JSONL records streamed into the run's output
directory, flushed so a live run is tail-able. Logs are never evidence —
under CT-11 only the raw archive and the journal bear evidence. Structured
records that cross a package boundary carry ``correlation_id``, excluded from
fp1 identity by versioned declaration. A crashed run leaves a partial log in
its own room and never writes a sibling directory or the ledger.
"""

from __future__ import annotations

import json
import os
import secrets
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import BinaryIO, Final, cast

from qmf.core.chrono import Instant, render_utc_iso8601
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qmb._refuse import clean_token, invalid, policy, storage, unavailable
from qmb.orchestrator.paths import MAX_JSONL_BYTES, open_write_handle, read_contained_bytes

__all__ = [
    "CORRELATION_ID_EXCLUDED_FROM_FP1",
    "EVENT_RUN_ABORTED",
    "EVENT_RUN_COMPLETED",
    "EVENT_RUN_CRASHED",
    "EVENT_RUN_REFUSED",
    "EVENT_RUN_STARTED",
    "EVENT_SPAWNED",
    "EVIDENCE_BEARING_FORMATS",
    "LOGGER_NAME",
    "LOG_FILENAME",
    "LOG_IS_EVIDENCE",
    "LOG_KIND",
    "LOG_RECORD_CLASS",
    "TIMESTAMP_ENCODING",
    "TIMESTAMP_EXCLUDED_FROM_FP1",
    "LogSink",
    "LogSinkHealth",
    "OperationalRecord",
    "append_run_log",
    "inject_run_log",
    "mint_correlation_id",
    "operational_log_identity",
    "propagate_correlation",
    "read_run_log",
    "run_log_path",
    "structured_log_fp1_identity",
]

CORRELATION_ID_EXCLUDED_FROM_FP1: Final[bool] = True
TIMESTAMP_EXCLUDED_FROM_FP1: Final[bool] = True
TIMESTAMP_ENCODING: Final[str] = "UTC-ISO-8601-Z"
LOG_FILENAME: Final[str] = "run.log"
LOG_IS_EVIDENCE: Final[bool] = False
LOG_KIND: Final[str] = "ad-14-operational"
LOG_RECORD_CLASS: Final[str] = "qmb-operational-log-v1"
LOGGER_NAME: Final[str] = "qmb.orchestrator"
LOG_OWNER: Final[str] = "orchestrator"
EVIDENCE_BEARING_FORMATS: Final[tuple[str, ...]] = ("raw archive", "journal")
EVENT_SPAWNED: Final[str] = "spawned"
EVENT_RUN_STARTED: Final[str] = "run-started"
EVENT_RUN_COMPLETED: Final[str] = "run-completed"
EVENT_RUN_REFUSED: Final[str] = "run-refused"
EVENT_RUN_ABORTED: Final[str] = "run-aborted"
EVENT_RUN_CRASHED: Final[str] = "run-crashed"
_EMPTY_FIELDS: Final[Mapping[str, object]] = MappingProxyType({})


def operational_log_identity() -> dict[str, object]:
    """Identity-bearing operational-log fields. Package SemVer is omitted."""
    return {
        "log_owner": LOG_OWNER,
        "log_filename": LOG_FILENAME,
        "log_is_evidence": LOG_IS_EVIDENCE,
        "log_kind": LOG_KIND,
        "log_format": "jsonl",
        "log_record_class": LOG_RECORD_CLASS,
        "correlation_id_excluded_from_fp1": CORRELATION_ID_EXCLUDED_FROM_FP1,
        "timestamp_excluded_from_fp1": TIMESTAMP_EXCLUDED_FROM_FP1,
        "timestamp_encoding": TIMESTAMP_ENCODING,
        "evidence_bearing_formats": EVIDENCE_BEARING_FORMATS,
    }


def mint_correlation_id() -> str:
    """Opaque linking annotation. Never an fp1 identity field (AR-35)."""
    return secrets.token_hex(16)  # ambient-scan: allow - orchestrator composition root


def run_log_path(output_dir: object) -> Result[Path]:
    """The per-run operational log path inside an isolated output directory."""
    directory = _as_output_dir(output_dir)
    if is_refusal(directory):
        return directory
    return Ok(directory.value / LOG_FILENAME)


def propagate_correlation(
    payload: object,
    *,
    correlation_id: object,
) -> Result[dict[str, object]]:
    """Stamp ``correlation_id`` onto a structured log mapping at a package boundary.

    Pure value contracts never take ``correlation_id`` in their signature
    (DEC-0131); the annotation rides the caller's context. It is excluded from
    fp1 identity (AR-35, DEC-0112).
    """
    if not isinstance(payload, Mapping):
        return invalid(
            "payload",
            "a structured log that crosses a package boundary is a mapping",
            given=repr(type(payload).__name__),
        )
    token = _as_correlation_id(correlation_id)
    if is_refusal(token):
        return token
    bound = {str(key): value for key, value in cast("Mapping[object, object]", payload).items()}
    bound["correlation_id"] = token.value
    return Ok(bound)


def structured_log_fp1_identity(payload: object) -> Result[dict[str, object]]:
    """fp1 identity of a structured log mapping. Excludes linking/display fields."""
    if not isinstance(payload, Mapping):
        return invalid(
            "payload",
            "structured-log identity is taken from a mapping",
            given=repr(type(payload).__name__),
        )
    identity: dict[str, object] = {}
    for key, value in cast("Mapping[object, object]", payload).items():
        name = str(key)
        if name in {"correlation_id", "timestamp", "display_time"}:
            continue
        identity[name] = value
    return Ok(identity)


def inject_run_log(
    output_dir: object,
    *,
    run_id: object,
    correlation_id: object,
) -> Result[Path]:
    """Create the per-run log file and emit the orchestrator's injected-sink record."""
    path = run_log_path(output_dir)
    if is_refusal(path):
        return path
    sink = LogSink.try_create(
        path.value,
        run_id=run_id,
        correlation_id=correlation_id,
        append=False,
    )
    if is_refusal(sink):
        return sink
    bound = sink.value
    emitted = bound.emit(
        EVENT_SPAWNED,
        "orchestrator injected the per-run operational log sink",
    )
    bound.close()
    if is_refusal(emitted):
        return emitted
    return Ok(path.value)


def append_run_log(
    output_dir: object,
    *,
    run_id: object,
    correlation_id: object,
    event: object,
    message: object,
    fields: object = None,
) -> Result[OperationalRecord]:
    """Append one operational record after the previous writer has released the file."""
    path = run_log_path(output_dir)
    if is_refusal(path):
        return path
    sink = LogSink.try_create(
        path.value,
        run_id=run_id,
        correlation_id=correlation_id,
        append=True,
    )
    if is_refusal(sink):
        return sink
    bound = sink.value
    emitted = bound.emit(event, message, fields=fields)
    bound.close()
    return emitted


def read_run_log(output_dir: object) -> Result[tuple[OperationalRecord, ...]]:
    """Read JSONL operational records from a run directory or a log file."""
    target = _as_log_file(output_dir)
    if is_refusal(target):
        return target
    loaded = read_contained_bytes(
        target.value,
        contain_within=target.value.parent,
        max_bytes=MAX_JSONL_BYTES,
        field="log_path",
    )
    if is_refusal(loaded):
        return loaded
    raw = loaded.value
    records: list[OperationalRecord] = []
    for line in raw.split(b"\n"):
        if line == b"":
            continue
        try:
            parsed: object = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return unavailable(
                "log_path",
                "the per-run operational log is JSONL",
                path=str(target.value),
            )
        loaded = OperationalRecord.from_row(parsed)
        if is_refusal(loaded):
            return loaded
        records.append(loaded.value)
    return Ok(tuple(records))


@dataclass(frozen=True, slots=True)
class LogSinkHealth:
    """Typed health report for the injected per-run log sink (AD-14)."""

    owner: str
    path: str
    is_open: bool
    is_evidence: bool
    records_emitted: int
    correlation_id: str


@dataclass(frozen=True, slots=True)
class OperationalRecord:
    """One AD-14 operational log record. Never CT-11 evidence."""

    event: str
    message: str
    run_id: str
    correlation_id: str
    timestamp: str
    logger: str = LOGGER_NAME
    fields: Mapping[str, object] = _EMPTY_FIELDS
    is_evidence: bool = LOG_IS_EVIDENCE

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))
        object.__setattr__(self, "is_evidence", LOG_IS_EVIDENCE)

    @classmethod
    def try_create(
        cls,
        *,
        event: object,
        message: object,
        run_id: object,
        correlation_id: object,
        timestamp: object = None,
        logger: object = LOGGER_NAME,
        fields: object = None,
    ) -> Result[OperationalRecord]:
        """Build one structured operational record. ``correlation_id`` is required."""
        event_token = clean_token(event)
        if event_token is None:
            return invalid(
                "event",
                "an operational log record names a non-empty event token",
                given=repr(event),
            )
        message_token = clean_token(message)
        if message_token is None:
            return invalid(
                "message",
                "an operational log record carries a non-empty message",
                given=repr(message),
            )
        run_token = _as_run_id_token(run_id)
        if is_refusal(run_token):
            return run_token
        correlation = _as_correlation_id(correlation_id)
        if is_refusal(correlation):
            return correlation
        logger_token = clean_token(logger)
        if logger_token is None:
            return invalid(
                "logger",
                "an operational log record names a non-empty logger",
                given=repr(logger),
            )
        stamp = _as_timestamp(timestamp)
        if is_refusal(stamp):
            return stamp
        bound_fields = _as_fields(fields)
        if is_refusal(bound_fields):
            return bound_fields
        return Ok(
            cls(
                event=event_token,
                message=message_token,
                run_id=run_token.value,
                correlation_id=correlation.value,
                timestamp=stamp.value,
                logger=logger_token,
                fields=bound_fields.value,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. ``correlation_id`` and timestamp are excluded (AR-35)."""
        return {
            "class": LOG_RECORD_CLASS,
            "event": self.event,
            "message": self.message,
            "run_id": self.run_id,
            "logger": self.logger,
            "fields": dict(self.fields),
            "is_evidence": LOG_IS_EVIDENCE,
        }

    def to_row(self) -> dict[str, object]:
        """JSON-native row: identity plus linking/display annotations."""
        row = dict(self.fp1_identity())
        row["correlation_id"] = self.correlation_id
        row["timestamp"] = self.timestamp
        return row

    @classmethod
    def from_row(cls, row: object) -> Result[OperationalRecord]:
        """Rebuild a record from a persisted :meth:`to_row` mapping."""
        if not isinstance(row, Mapping):
            return invalid(
                "row",
                "an operational log row is a mapping",
                given=repr(type(row).__name__),
            )
        mapping = cast("Mapping[str, object]", row)
        return cls.try_create(
            event=mapping.get("event"),
            message=mapping.get("message"),
            run_id=mapping.get("run_id"),
            correlation_id=mapping.get("correlation_id"),
            timestamp=mapping.get("timestamp"),
            logger=mapping.get("logger", LOGGER_NAME),
            fields=mapping.get("fields"),
        )


class LogSink:
    """One-writer append sink bound to one run's operational log file. Impure."""

    __slots__ = ("_correlation_id", "_emitted", "_handle", "_path", "_run_id")

    def __init__(
        self,
        path: Path,
        *,
        run_id: str,
        correlation_id: str,
        handle: BinaryIO,
    ) -> None:
        self._path = path
        self._run_id = run_id
        self._correlation_id = correlation_id
        self._handle: BinaryIO | None = handle
        self._emitted = 0

    @classmethod
    def try_create(
        cls,
        path: object,
        *,
        run_id: object,
        correlation_id: object,
        append: bool = False,
    ) -> Result[LogSink]:
        """Open the per-run log file. Exclusive create unless ``append``."""
        target = _as_log_file(path, must_exist=False)
        if is_refusal(target):
            return target
        run_token = _as_run_id_token(run_id)
        if is_refusal(run_token):
            return run_token
        correlation = _as_correlation_id(correlation_id)
        if is_refusal(correlation):
            return correlation
        opened = open_write_handle(
            target.value,
            contain_within=target.value.parent,
            append=append,
            field="log_path",
        )
        if is_refusal(opened):
            if not append and opened.context.get("given") == "FileExistsError":
                return policy(
                    "log_path",
                    "two writers never share the per-run operational log; the log "
                    "file in this run directory is already present",
                    path=str(target.value),
                    run_id=run_token.value,
                )
            extra = dict(opened.context)
            extra["run_id"] = run_token.value
            return TypedRefusal(
                category=opened.category,
                retryability=opened.retryability,
                context=extra,
                after_condition_descriptor=opened.after_condition_descriptor,
            )
        return Ok(
            cls(
                target.value,
                run_id=run_token.value,
                correlation_id=correlation.value,
                handle=opened.value,
            )
        )

    @property
    def path(self) -> Path:
        """Filesystem path of this run's operational log."""
        return self._path

    @property
    def correlation_id(self) -> str:
        """Linking annotation stamped on every record this sink emits."""
        return self._correlation_id

    @property
    def run_id(self) -> str:
        """Run id (resolved-config fingerprint) this sink is bound to."""
        return self._run_id

    def health(self) -> LogSinkHealth:
        """No-argument typed health report (AD-14)."""
        handle = self._handle
        return LogSinkHealth(
            owner=LOG_OWNER,
            path=str(self._path),
            is_open=handle is not None and not handle.closed,
            is_evidence=LOG_IS_EVIDENCE,
            records_emitted=self._emitted,
            correlation_id=self._correlation_id,
        )

    def emit(
        self,
        event: object,
        message: object,
        *,
        fields: object = None,
    ) -> Result[OperationalRecord]:
        """Append one JSONL record and flush so a live tail sees it."""
        handle = self._handle
        if handle is None or handle.closed:
            return unavailable(
                "log_path",
                "the injected operational log sink is closed",
                path=str(self._path),
                run_id=self._run_id,
            )
        record = OperationalRecord.try_create(
            event=event,
            message=message,
            run_id=self._run_id,
            correlation_id=self._correlation_id,
            fields=fields,
        )
        if is_refusal(record):
            return record
        payload = json.dumps(record.value.to_row(), ensure_ascii=False).encode("utf-8")
        try:
            handle.write(payload + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        except OSError as exc:
            return storage(
                "log_path",
                "the orchestrator could not stream the per-run operational log",
                given=type(exc).__name__,
                path=str(self._path),
                run_id=self._run_id,
            )
        self._emitted += 1
        return record

    def close(self) -> None:
        """Release the file so a later writer (abort record) can append."""
        handle = self._handle
        self._handle = None
        if handle is not None and not handle.closed:
            handle.close()


def _as_correlation_id(value: object) -> Result[str]:
    token = clean_token(value)
    if token is None:
        return invalid(
            "correlation_id",
            "correlation_id is a non-blank linking annotation excluded from fp1 "
            "identity and propagated across package boundaries (AR-35, DEC-0112)",
            given=repr(value),
        )
    return Ok(token)


def _as_run_id_token(value: object) -> Result[str]:
    if isinstance(value, Fingerprint):
        return Ok(value.value)
    token = clean_token(value)
    if token is None:
        return invalid(
            "run_id",
            "the operational log is bound to the run id (resolved-config fingerprint)",
            given=repr(type(value).__name__),
        )
    return Ok(token)


def _as_timestamp(value: object) -> Result[str]:
    if value is None:
        return _display_now()
    token = clean_token(value)
    if token is None or not token.endswith("Z"):
        return invalid(
            "timestamp",
            "operator-facing log timestamps render UTC ISO-8601 with an explicit Z (AD-14)",
            given=repr(value),
        )
    return Ok(token)


def _display_now() -> Result[str]:
    ns = time.time_ns()  # ambient-scan: allow - AD-14 operational display timestamp
    instant = Instant.try_create(ns)
    if is_refusal(instant):
        return instant
    rendered = render_utc_iso8601(instant.value)
    if is_refusal(rendered):
        return rendered
    return Ok(rendered.value.text)


def _as_fields(value: object) -> Result[Mapping[str, object]]:
    if value is None:
        return Ok(_EMPTY_FIELDS)
    if not isinstance(value, Mapping):
        return invalid(
            "fields",
            "operational log fields are a mapping of JSON-native values",
            given=repr(type(value).__name__),
        )
    mapping = cast("Mapping[object, object]", value)
    return Ok({str(key): _jsonable(item) for key, item in mapping.items()})


def _as_output_dir(value: object) -> Result[Path]:
    if isinstance(value, Path):
        root = value
    elif isinstance(value, str) and value.strip() != "":
        root = Path(value)
    else:
        return invalid(
            "output_dir",
            "the per-run operational log lives in the isolated output directory",
            given=repr(type(value).__name__),
        )
    if not root.is_dir():
        return invalid(
            "output_dir",
            "the per-run operational log lives in the isolated output directory",
            given=str(root),
        )
    return Ok(root)


def _as_log_file(value: object, *, must_exist: bool = True) -> Result[Path]:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str) and value.strip() != "":
        path = Path(value)
    else:
        return invalid(
            "log_path",
            "the operational log path is a filesystem path",
            given=repr(type(value).__name__),
        )
    if path.is_dir():
        path = path / LOG_FILENAME
    if path.name != LOG_FILENAME:
        return policy(
            "log_path",
            "the injected log sink streams into the per-run log file in the run directory",
            given=path.name,
        )
    if must_exist and not path.is_file():
        return unavailable(
            "log_path",
            "the per-run operational log is not present",
            path=str(path),
        )
    return Ok(path)


def _jsonable(value: object) -> object:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, Fingerprint):
        return value.value
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return {str(key): _jsonable(item) for key, item in mapping.items()}
    identity = getattr(value, "value", None)
    if isinstance(identity, str):
        return identity
    return str(value)
