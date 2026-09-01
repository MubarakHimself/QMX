"""MIS surface: governed signal snapshot and later zero-authority shadow lane.

Story 26.3 lands the compute-once environment-keyed signal snapshot dispatched
to the Book door and the KSA only. Shadow-lane candidates remain TN-19 follow-on.
"""

from __future__ import annotations

from typing import Final

from qmn.mis.signal_snapshot import (
    DECISION_FRESHNESS_BOUND_VARIABLE,
    GOVERNED_CONSUMERS,
    SIGNAL_SNAPSHOT_FORMAT_VERSION,
    SIGNAL_SNAPSHOT_SURFACE,
    SQS_PRODUCER_ID,
    CanonicalFeedState,
    GovernedConsumer,
    ProducerReadiness,
    ProducerSlot,
    SignalSnapshot,
    SqsBaselineKey,
    SqsReading,
    check_snapshot_freshness,
    consume_signal_snapshot,
    mint_signal_snapshot,
    refuse_bot_consumer,
    sqs_baseline_key,
)

__all__ = [
    "DECISION_FRESHNESS_BOUND_VARIABLE",
    "GOVERNED_CONSUMERS",
    "MIS_SURFACE",
    "SIGNAL_SNAPSHOT_FORMAT_VERSION",
    "SIGNAL_SNAPSHOT_SURFACE",
    "SQS_PRODUCER_ID",
    "CanonicalFeedState",
    "GovernedConsumer",
    "ProducerReadiness",
    "ProducerSlot",
    "SignalSnapshot",
    "SqsBaselineKey",
    "SqsReading",
    "check_snapshot_freshness",
    "consume_signal_snapshot",
    "mint_signal_snapshot",
    "refuse_bot_consumer",
    "sqs_baseline_key",
]

MIS_SURFACE: Final[str] = "qmn.mis"
