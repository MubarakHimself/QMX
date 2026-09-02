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

__all__ = [
    "FILE_WATCHER_ENABLED",
    "LOAD_PHASES",
    "DaemonPluginContext",
    "LoadedPlugin",
    "PluginActivator",
    "PluginContextError",
    "PluginExitStack",
    "PluginLoadError",
    "PluginLoader",
    "PublishedContribution",
    "check_qma_api_compatible",
    "topological_plugin_order",
]
