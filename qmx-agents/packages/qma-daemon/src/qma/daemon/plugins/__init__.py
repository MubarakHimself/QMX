"""Plugin loader, reversible scopes, migrations, roster (AD-21).

``DaemonPluginContext`` implements the ``qma-core`` ``PluginContext`` protocol.
Plugin authors import contribution types from ``qma-core``, never from here.
"""

from __future__ import annotations

from qma.daemon.plugins.context import DaemonPluginContext, PluginContextError
from qma.daemon.plugins.exit_stack import PluginExitStack
from qma.daemon.plugins.loader import (
    FILE_WATCHER_ENABLED,
    LOAD_PHASES,
    LoadedPlugin,
    PluginActivator,
    PluginLoader,
    PluginLoadError,
    PublishedContribution,
    check_qma_api_compatible,
    topological_plugin_order,
)
from qma.daemon.plugins.migrations import (
    CHECKPOINT_IS_RECOVERY_COPY,
    DAEMON_CORE_MIGRATION_TARGETS,
    FORWARD_ONLY_CONFIRM_COMMAND,
    JOURNAL_CHECKPOINT_EVENT,
    MIGRATION_OWNER_DAEMON_CORE,
    MIGRATION_OWNER_PLUGIN,
    PLUGIN_INSTALL_PREFLIGHT_QUERY,
    REVERSIBLE_BY_DOWN,
    DaemonCoreMigrationDeclaration,
    DisableReceipt,
    ForwardOnlyConfirmation,
    InstallPreflightResult,
    JournalCheckpointEvidence,
    PluginDataSnapshot,
    PluginMigrationReport,
    PluginMigrationRunner,
    rollback_mode_for_manifest,
)

__all__ = [
    "CHECKPOINT_IS_RECOVERY_COPY",
    "DAEMON_CORE_MIGRATION_TARGETS",
    "FILE_WATCHER_ENABLED",
    "FORWARD_ONLY_CONFIRM_COMMAND",
    "JOURNAL_CHECKPOINT_EVENT",
    "LOAD_PHASES",
    "MIGRATION_OWNER_DAEMON_CORE",
    "MIGRATION_OWNER_PLUGIN",
    "PLUGIN_INSTALL_PREFLIGHT_QUERY",
    "REVERSIBLE_BY_DOWN",
    "DaemonCoreMigrationDeclaration",
    "DaemonPluginContext",
    "DisableReceipt",
    "ForwardOnlyConfirmation",
    "InstallPreflightResult",
    "JournalCheckpointEvidence",
    "LoadedPlugin",
    "PluginActivator",
    "PluginContextError",
    "PluginDataSnapshot",
    "PluginExitStack",
    "PluginLoadError",
    "PluginLoader",
    "PluginMigrationReport",
    "PluginMigrationRunner",
    "PublishedContribution",
    "check_qma_api_compatible",
    "rollback_mode_for_manifest",
    "topological_plugin_order",
]
