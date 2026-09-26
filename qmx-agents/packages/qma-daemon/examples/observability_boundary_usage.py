"""L27 reference usage: mini-app failures stay off QMN; agents do not write telemetry."""

from __future__ import annotations

import logging

from qma.core.plugins.hooks import HookSource
from qma.core.ports.telemetry import HARNESS_AUTHOR
from qma.daemon.hooks.agent_authored import AgentAuthoredHookRegistrar
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.observability_boundary import (
    LOGS_REMAIN_LOGS,
    QMB_LOGSINK_MAY_REMAIN,
    QMN_FAILURES_MD,
    QMN_FAILURES_MD_EXTENDED,
    THIRD_LOGGER_MINTED,
    emit_telemetry_from_hook,
    mint_third_logger,
    owning_failures_md,
    page_qmn_alert_with_mini_app_failure,
    place_typed_failure,
)
from qma.daemon.operator_log import JsonLineFormatter
from qma.daemon.telemetry.store import TelemetryStore
from qmf.core import is_ok, is_refusal


def main() -> None:
    assert QMN_FAILURES_MD_EXTENDED is False
    assert LOGS_REMAIN_LOGS is True
    assert QMB_LOGSINK_MAY_REMAIN is True
    assert THIRD_LOGGER_MINTED is False
    assert issubclass(JsonLineFormatter, logging.Formatter)

    home = owning_failures_md("qma-daemon")
    assert is_ok(home)
    assert is_ok(place_typed_failure(owner="qma-daemon", target_failures_md=home.value))
    assert is_refusal(place_typed_failure(owner="qma-daemon", target_failures_md=QMN_FAILURES_MD))
    assert is_refusal(page_qmn_alert_with_mini_app_failure("FR-83"))
    assert is_refusal(mint_third_logger("MiniAppLogger"))

    store = TelemetryStore()
    model = emit_telemetry_from_hook(
        store,
        {"kind": "trace", "correlation_id": "corr-ex", "authored_by": "model"},
        source=HookSource.MISSION,
        authored_by="model",
    )
    assert is_refusal(model)
    registrar = AgentAuthoredHookRegistrar(registry=HookRegistry())
    assert is_refusal(registrar.emit_telemetry({"kind": "log", "correlation_id": "corr-ex-agent"}))
    harness = emit_telemetry_from_hook(
        store,
        {
            "kind": "hook_timeout",
            "correlation_id": "corr-ex-harness",
            "authored_by": HARNESS_AUTHOR,
        },
        source=HookSource.PLUGIN,
        authored_by=HARNESS_AUTHOR,
    )
    assert is_ok(harness)
    assert store.event_count() == 1


if __name__ == "__main__":
    main()
