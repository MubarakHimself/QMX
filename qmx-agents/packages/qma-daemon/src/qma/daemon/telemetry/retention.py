"""Daemon-job retention for the two bounded non-evidence streams (AD-23; FR-Q67).

Only the telemetry store and the mailbox delivery projection may be trimmed by a
daemon job, and only inside their registered retention windows. Each trim
records window, reason and ``correlation_id``. GAP-0089 / GAP-0090 stay Deferred.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from qma.core.ports.telemetry import (
    GAP_0089_TRIM_WINDOW,
    GAP_0090_CONTEXT_COMPACTION,
    TELEMETRY_RETENTION_KEYS,
)
from qma.daemon.bus.mailbox import DELIVERY_RETENTION_KEYS, MailboxStore
from qma.daemon.telemetry.store import DAEMON_JOB_TRIM_STREAMS, TelemetryStore
from qma.wire.principals import is_daemon_job_trim
from qmf.core import Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "DAEMON_JOB_TRIM_STREAMS",
    "GAP_0089_TRIM_WINDOW",
    "GAP_0090_CONTEXT_COMPACTION",
    "RetentionJob",
    "RetentionJobReport",
]


@dataclass(frozen=True, slots=True)
class RetentionJobReport:
    """Combined trim report for eligible bounded streams."""

    correlation_id: str
    reason: str
    telemetry: Mapping[str, object] | None
    mailbox_delivery: Mapping[str, object] | None
    gap_0089: str = GAP_0089_TRIM_WINDOW
    gap_0090: str = GAP_0090_CONTEXT_COMPACTION

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "correlation_id": self.correlation_id,
                "reason": self.reason,
                "telemetry": None if self.telemetry is None else dict(self.telemetry),
                "mailbox_delivery": (
                    None if self.mailbox_delivery is None else dict(self.mailbox_delivery)
                ),
                "eligible_streams": sorted(DAEMON_JOB_TRIM_STREAMS),
                "gap_0089": "deferred",
                "gap_0090": "deferred",
                "context_compaction": False,
            }
        )


@dataclass
class RetentionJob:
    """Runs the two AD-23 daemon-job trims inside their retention windows."""

    telemetry: TelemetryStore
    mailbox: MailboxStore | None = None

    def run(
        self,
        *,
        correlation_id: str,
        reason: str = "daemon_job_retention",
        streams: frozenset[str] | None = None,
        inside_retention_window: bool = True,
        operator_principal: bool = False,
    ) -> Result[RetentionJobReport]:
        """Trim requested eligible streams; refuse any foreign stream."""
        if correlation_id.strip() == "":
            return invalid_input(
                "correlation_id",
                "each retention trim records its correlation_id (AD-23; FR-Q67)",
            )
        corr = correlation_id.strip()
        requested = DAEMON_JOB_TRIM_STREAMS if streams is None else frozenset(streams)
        foreign = requested - DAEMON_JOB_TRIM_STREAMS
        if foreign:
            return policy_rejection(
                "stream",
                "only the telemetry store and the mailbox delivery projection are "
                "eligible for daemon-job trimming; journal, ledgers, artifacts, "
                "staging, quarantine and retention-exempt trajectory/replay streams "
                "are trimmed by neither path (AD-23; FR-Q67; DEC-0322)",
                stream=sorted(foreign)[0],
                allowed=sorted(DAEMON_JOB_TRIM_STREAMS),
                gap_0089=GAP_0089_TRIM_WINDOW,
                gap_0090=GAP_0090_CONTEXT_COMPACTION,
            )

        for stream in requested:
            if not is_daemon_job_trim(
                "retention.trim",
                stream=stream,
                inside_retention_window=inside_retention_window,
            ) and not operator_principal:
                return policy_rejection(
                    "retention.trim",
                    "daemon-job trims run only inside registered retention "
                    "windows; outside those windows only an operator-principal "
                    "action may trim (AD-23; FR-Q67; DEC-0323)",
                    stream=stream,
                    inside_retention_window=inside_retention_window,
                )

        telemetry_payload: Mapping[str, object] | None = None
        mailbox_payload: Mapping[str, object] | None = None

        if "telemetry" in requested:
            trimmed = self.telemetry.trim(
                correlation_id=corr,
                reason=reason,
                inside_retention_window=inside_retention_window,
                operator_principal=operator_principal,
            )
            if is_refusal(trimmed):
                return trimmed
            telemetry_payload = trimmed.value.to_payload()

        if "mailbox.delivery" in requested:
            if self.mailbox is None:
                return policy_rejection(
                    "mailbox",
                    "mailbox delivery trim requires a bound MailboxStore (AD-23; FR-Q67)",
                )
            mailbox_payload = self.mailbox.trim_delivery_projection(
                correlation_id=corr,
                reason=reason,
            )

        return Ok(
            RetentionJobReport(
                correlation_id=corr,
                reason=reason,
                telemetry=telemetry_payload,
                mailbox_delivery=mailbox_payload,
            )
        )

    def cite_retention_keys(self) -> Mapping[str, object]:
        """Registry citations only — never numeric window values (GAP-0089)."""
        return MappingProxyType(
            {
                "telemetry": list(TELEMETRY_RETENTION_KEYS),
                "mailbox.delivery": list(DELIVERY_RETENTION_KEYS),
                "gap_0089": GAP_0089_TRIM_WINDOW,
                "gap_0090": GAP_0090_CONTEXT_COMPACTION,
                "deferred": True,
            }
        )
