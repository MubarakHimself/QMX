"""Independent telemetry store — harness-authored, announcement-exempt (AD-23).

Telemetry is neither a ledger nor the event journal. Appends emit no journal
announcement, carry no ``journal_seq``, and order by ``recorded_at`` then
``correlation_id``. Only bounded non-exempt rows may be trimmed by a daemon job
inside registered retention windows; trajectories and session replay stay
retention-exempt. GAP-0089 / GAP-0090 stay Deferred.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

from qma.core.ports.telemetry import (
    GAP_0089_TRIM_WINDOW,
    GAP_0090_CONTEXT_COMPACTION,
    HARNESS_AUTHOR,
    TELEMETRY_RETENTION_EXEMPT_KINDS,
    TELEMETRY_RETENTION_KEYS,
    TelemetryExportPort,
    TelemetryRecord,
    parse_telemetry_record,
    refuse_context_compaction,
    refuse_trim_window_decision,
)
from qma.daemon.journal.stores import TELEMETRY_STORE
from qma.daemon.journal.variables import registry_key
from qma.daemon.telemetry.export import NullTelemetryExporter
from qmf.core import Clock, DataDrivenClock, Instant, Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "DAEMON_JOB_TRIM_STREAMS",
    "GAP_0089_TRIM_WINDOW",
    "GAP_0090_CONTEXT_COMPACTION",
    "TELEMETRY_RETENTION_KEYS",
    "TELEMETRY_STORE_NAME",
    "TelemetryStore",
    "TrimReceipt",
]


TELEMETRY_STORE_NAME: Final[str] = TELEMETRY_STORE

DAEMON_JOB_TRIM_STREAMS: Final[frozenset[str]] = frozenset(
    {
        "mailbox.delivery",
        "telemetry",
    }
)

_DEFAULT_CLOCK_TICKS: Final[int] = 256
_DEFAULT_CLOCK_BASE_NS: Final[int] = 1_700_000_000_000_000_000


def _default_clock() -> DataDrivenClock:
    walls = tuple(Instant(value_ns=_DEFAULT_CLOCK_BASE_NS + i) for i in range(_DEFAULT_CLOCK_TICKS))
    monos = tuple(i * 1_000 for i in range(_DEFAULT_CLOCK_TICKS))
    return DataDrivenClock(boot_epoch_id="boot-telemetry", wall_instants=walls, monotonic_ns=monos)


@dataclass(frozen=True, slots=True)
class TrimReceipt:
    """Recorded trim of a bounded non-evidence stream (AD-23; FR-Q67)."""

    stream: str
    window: str
    reason: str
    correlation_id: str
    trimmed_count: int
    retained_exempt_count: int
    retention_keys: tuple[str, ...]
    gap_0089: str = GAP_0089_TRIM_WINDOW

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "stream": self.stream,
                "window": self.window,
                "reason": self.reason,
                "correlation_id": self.correlation_id,
                "trimmed_count": self.trimmed_count,
                "retained_exempt_count": self.retained_exempt_count,
                "retention": list(self.retention_keys),
                "gap_0089": "deferred",
                "gap_0090": "deferred",
                "journal_records_deleted": False,
                "ledgers_trimmed": False,
                "artifacts_trimmed": False,
                "staging_trimmed": False,
                "quarantine_trimmed": False,
            }
        )


@dataclass
class TelemetryStore:
    """Harness-authored independent telemetry store (AD-23; FR-Q67).

    Distinct from the event journal, the three ledgers, artifacts and staging.
    Appends are announcement-exempt. Export rides a swappable
    :class:`TelemetryExportPort` that never pulls the OTel SDK into core.
    """

    _clock: Clock = field(default_factory=_default_clock)
    _exporter: TelemetryExportPort = field(default_factory=NullTelemetryExporter)
    _records: list[TelemetryRecord] = field(default_factory=list[TelemetryRecord])
    _trim_log: list[TrimReceipt] = field(default_factory=list[TrimReceipt])

    @property
    def store_name(self) -> str:
        return TELEMETRY_STORE_NAME

    @property
    def announcement_exempt(self) -> bool:
        return True

    @property
    def exporter(self) -> TelemetryExportPort:
        return self._exporter

    def bind_exporter(self, exporter: TelemetryExportPort) -> None:
        """Swap the export port adapter (composition-root / test seam)."""
        self._exporter = exporter

    def records(self) -> tuple[TelemetryRecord, ...]:
        """Snapshot ordered by ``recorded_at`` then ``correlation_id``."""
        return tuple(
            sorted(
                self._records,
                key=lambda row: (row.recorded_at, row.correlation_id, row.id),
            )
        )

    def trim_log(self) -> tuple[TrimReceipt, ...]:
        return tuple(self._trim_log)

    def event_count(self) -> int:
        return len(self._records)

    def approx_disk_bytes(self) -> int:
        """Approximate on-disk size used against ``trim_disk_bytes`` citations."""
        total = 0
        for record in self._records:
            total += len(record.id) + len(record.correlation_id) + len(record.kind)
            total += sum(len(str(k)) + len(str(v)) for k, v in record.payload.items())
        return total

    def append(self, raw: Mapping[str, object] | TelemetryRecord) -> Result[TelemetryRecord]:
        """Append one harness-authored telemetry record. No journal announcement."""
        parsed = parse_telemetry_record(raw)
        if is_refusal(parsed):
            return parsed
        record = parsed.value
        if record.authored_by != HARNESS_AUTHOR:
            return policy_rejection(
                "authored_by",
                "telemetry is harness-authored only (AD-23; FR-Q67)",
                given=record.authored_by,
            )

        occurred = record.occurred_at
        recorded = record.recorded_at
        if occurred == 0 or recorded == 0:
            stamped = self._clock.wall_now()
            if is_refusal(stamped):
                return stamped
            now_ns = stamped.value.value_ns
            occurred = now_ns if occurred == 0 else occurred
            recorded = now_ns if recorded == 0 else recorded
            record = TelemetryRecord(
                id=record.id,
                kind=record.kind,
                correlation_id=record.correlation_id,
                wire_id=record.wire_id,
                authored_by=HARNESS_AUTHOR,
                occurred_at=occurred,
                recorded_at=recorded,
                payload=record.payload,
            )

        self._records.append(record)
        return Ok(record)

    def export_pending(self) -> Result[int]:
        """Push current store contents through the bound export port."""
        return self._exporter.export(self.records())

    def compact_context(self, **_extra: object) -> Result[None]:
        """Context compaction is Deferred GAP-0090 — always refused."""
        return refuse_context_compaction()

    def decide_trim_window(self, **_extra: object) -> Result[None]:
        """Numeric trim-window decision is Deferred GAP-0089 — always refused."""
        return refuse_trim_window_decision()

    def trim(
        self,
        *,
        correlation_id: str,
        reason: str = "daemon_job_retention",
        inside_retention_window: bool = True,
        operator_principal: bool = False,
    ) -> Result[TrimReceipt]:
        """Trim bounded non-exempt telemetry inside a registered retention window.

        Retention-exempt ``trajectory`` / ``session_replay`` rows are retained.
        Outside the window only an operator-principal action may trim. The
        numeric window value stays Deferred GAP-0089 — this path cites registry
        keys only.
        """
        if correlation_id.strip() == "":
            return invalid_input(
                "correlation_id",
                "each telemetry trim records its correlation_id (AD-23; FR-Q67)",
                given=repr(correlation_id),
            )
        if reason.strip() == "":
            return invalid_input(
                "reason",
                "each telemetry trim records its reason (AD-23; FR-Q67)",
                given=repr(reason),
            )
        if not inside_retention_window and not operator_principal:
            return policy_rejection(
                "retention.trim",
                "outside registered retention windows a telemetry trim is only "
                "a recorded operator-principal action, never a background job "
                "(AD-23; FR-Q67; DEC-0322, DEC-0323)",
                stream="telemetry",
                inside_retention_window=False,
            )

        keep: list[TelemetryRecord] = []
        dropped = 0
        exempt = 0
        for record in self._records:
            if record.kind in TELEMETRY_RETENTION_EXEMPT_KINDS:
                keep.append(record)
                exempt += 1
                continue
            dropped += 1
        self._records = keep

        receipt = TrimReceipt(
            stream="telemetry",
            window=registry_key("telemetry.retention_window"),
            reason=reason.strip(),
            correlation_id=correlation_id.strip(),
            trimmed_count=dropped,
            retained_exempt_count=exempt,
            retention_keys=tuple(
                registry_key(name.removeprefix("registry:")) for name in TELEMETRY_RETENTION_KEYS
            ),
        )
        self._trim_log.append(receipt)
        return Ok(receipt)

    def eligible_daemon_job_streams(self) -> frozenset[str]:
        """Only telemetry and mailbox.delivery may be daemon-job trimmed."""
        return DAEMON_JOB_TRIM_STREAMS

    def refuse_foreign_trim(self, stream: str) -> Result[TrimReceipt]:
        """Refuse trimming journal, ledgers, artifacts, staging, quarantine."""
        if stream in DAEMON_JOB_TRIM_STREAMS:
            return invalid_input(
                "stream",
                "stream is already an eligible daemon-job trim target (AD-23)",
                stream=stream,
            )
        return policy_rejection(
            "stream",
            "only the telemetry store and the mailbox delivery projection are "
            "eligible for daemon-job trimming; journal, ledgers, artifacts, "
            "staging, quarantine and retention-exempt trajectory/replay streams "
            "are trimmed by neither path (AD-23; FR-Q67; DEC-0322)",
            stream=stream,
            allowed=sorted(DAEMON_JOB_TRIM_STREAMS),
            gap_0089=GAP_0089_TRIM_WINDOW,
            gap_0090=GAP_0090_CONTEXT_COMPACTION,
        )

    def assert_distinct_from_evidence_stores(self) -> Mapping[str, object]:
        """Evidence that telemetry is not journal / ledger / artifact / staging."""
        return MappingProxyType(
            {
                "store": TELEMETRY_STORE_NAME,
                "announcement_exempt": True,
                "journal_seq_present": False,
                "distinct_from": (
                    "event_journal",
                    "task_ledger",
                    "quant_ledger",
                    "experiment_ledger",
                    "artifact_store",
                    "staging_store",
                ),
                "author": HARNESS_AUTHOR,
                "export_port": type(self._exporter).__name__,
                "retention_keys": list(TELEMETRY_RETENTION_KEYS),
            }
        )
