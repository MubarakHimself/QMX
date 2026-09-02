"""Swappable telemetry export adapters (AD-23; FR-Q67).

OpenTelemetry conformance happens only here. This module never imports the
OpenTelemetry SDK into the daemon core — an adapter maps QMA-owned record types
onto an OTel-shaped payload at the port boundary, or a null/recording sink for
tests. Selecting an OTel-backed sink remains a composition-root choice.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

from qma.core.ports.telemetry import TelemetryRecord
from qmf.core import Ok, Result
from qmf.data.store.refusals import policy_rejection

__all__ = [
    "DAEMON_CORE_OTEL_IMPORT_FORBIDDEN",
    "NullTelemetryExporter",
    "OpenTelemetryExportAdapter",
    "RecordingTelemetryExporter",
    "otel_shaped_payload",
]


DAEMON_CORE_OTEL_IMPORT_FORBIDDEN: Final[bool] = True


def otel_shaped_payload(record: TelemetryRecord) -> Mapping[str, object]:
    """Map a QMA telemetry record onto an OpenTelemetry-compatible dict.

    Pure projection — no SDK import. Consumers behind the port may feed this
    shape into an OTel exporter of their choosing.
    """
    return MappingProxyType(
        {
            "name": f"qma.telemetry.{record.kind}",
            "trace_id": record.trace_ref,
            "attributes": {
                "qma.correlation_id": record.correlation_id,
                "qma.wire_id": record.wire_id,
                "qma.kind": record.kind,
                "qma.authored_by": record.authored_by,
                "qma.retention_exempt": record.retention_exempt,
                **{f"qma.payload.{key}": value for key, value in record.payload.items()},
            },
            "start_time_unix_nano": record.occurred_at,
            "end_time_unix_nano": record.recorded_at,
            "resource": {"service.name": "qma-daemon"},
        }
    )


@dataclass
class NullTelemetryExporter:
    """No-op export port binding — default when no sink is selected."""

    def export(self, records: Sequence[TelemetryRecord]) -> Result[int]:
        return Ok(len(tuple(records)))

    def flush(self) -> Result[None]:
        return Ok(None)


@dataclass
class RecordingTelemetryExporter:
    """In-memory export sink for tests and local observation."""

    _exported: list[TelemetryRecord] = field(default_factory=list[TelemetryRecord])
    _flushed: int = 0

    def export(self, records: Sequence[TelemetryRecord]) -> Result[int]:
        batch = tuple(records)
        self._exported.extend(batch)
        return Ok(len(batch))

    def flush(self) -> Result[None]:
        self._flushed += 1
        return Ok(None)

    @property
    def exported(self) -> tuple[TelemetryRecord, ...]:
        return tuple(self._exported)

    @property
    def flush_count(self) -> int:
        return self._flushed

    def clear(self) -> None:
        self._exported.clear()
        self._flushed = 0


@dataclass
class OpenTelemetryExportAdapter:
    """Swappable OTel conformance adapter — never imports the OTel SDK.

    Records are projected to OTel-shaped payloads and handed to an optional
    sink callback. The daemon core stays free of ``opentelemetry`` imports
    (AD-23; FR-Q67; DEC-0334).
    """

    sink: list[Mapping[str, object]] = field(default_factory=list[Mapping[str, object]])
    sdk_imported: bool = False

    def __post_init__(self) -> None:
        # Hard invariant: this adapter never loads the OpenTelemetry SDK.
        if self.sdk_imported:
            msg = (
                "OpenTelemetryExportAdapter must not import the OpenTelemetry "
                "SDK into the daemon core (AD-23; FR-Q67; DEC-0334)"
            )
            raise ValueError(msg)

    def export(self, records: Sequence[TelemetryRecord]) -> Result[int]:
        if self.sdk_imported:
            return policy_rejection(
                "otel_sdk",
                "daemon core must not import the OpenTelemetry SDK; conformance "
                "is at this export port only (AD-23; FR-Q67; DEC-0334)",
            )
        batch = tuple(records)
        for record in batch:
            self.sink.append(otel_shaped_payload(record))
        return Ok(len(batch))

    def flush(self) -> Result[None]:
        return Ok(None)

    @property
    def exported_payloads(self) -> tuple[Mapping[str, object], ...]:
        return tuple(self.sink)
