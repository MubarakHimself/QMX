"""Structural-seed smoke for qma-daemon (Story 40.1).

The scaffold starts no process and writes no durable state.
"""

from __future__ import annotations

import qma.daemon
import qma.daemon.bus
import qma.daemon.capabilities
import qma.daemon.context
import qma.daemon.envs
import qma.daemon.hooks
import qma.daemon.journal
import qma.daemon.ledgers
import qma.daemon.persistence
import qma.daemon.plugins
import qma.daemon.proxy
import qma.daemon.scheduler
import qma.daemon.staging
import qma.daemon.taskgraph
import qma.daemon.telemetry
import qma.daemon.tools


def test_version_display_only() -> None:
    assert qma.daemon.__version__ == "0.1.0"


def test_structural_modules_importable() -> None:
    modules = (
        qma.daemon.journal,
        qma.daemon.persistence,
        qma.daemon.taskgraph,
        qma.daemon.ledgers,
        qma.daemon.hooks,
        qma.daemon.capabilities,
        qma.daemon.bus,
        qma.daemon.scheduler,
        qma.daemon.staging,
        qma.daemon.proxy,
        qma.daemon.tools,
        qma.daemon.envs,
        qma.daemon.context,
        qma.daemon.plugins,
        qma.daemon.telemetry,
    )
    assert all(m.__doc__ for m in modules)
    from qma.daemon.plugins import DaemonPluginContext

    assert DaemonPluginContext.__name__ == "DaemonPluginContext"
    assert qma.daemon.PersistenceSubstrate.__name__ == "PersistenceSubstrate"
    assert qma.daemon.AuthoritativeJournal.__name__ == "AuthoritativeJournal"
    assert qma.daemon.journal.AuthoritativeJournal is qma.daemon.AuthoritativeJournal
    assert qma.daemon.DaemonClock.__name__ == "DaemonClock"
    assert qma.daemon.FoldContractRegistry.__name__ == "FoldContractRegistry"
    assert qma.daemon.MissionCompiler.__name__ == "MissionCompiler"
    assert qma.daemon.TaskGraphDispatcher.__name__ == "TaskGraphDispatcher"
    assert qma.daemon.taskgraph.MissionCompiler is qma.daemon.MissionCompiler
