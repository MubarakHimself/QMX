"""Plugin loader, reversible scopes, migrations, roster (AD-21).

``DaemonPluginContext`` implements the ``qma-core`` ``PluginContext`` protocol.
"""

from __future__ import annotations

from qma.daemon.plugins.context import DaemonPluginContext, PluginContextError

__all__ = ["DaemonPluginContext", "PluginContextError"]
