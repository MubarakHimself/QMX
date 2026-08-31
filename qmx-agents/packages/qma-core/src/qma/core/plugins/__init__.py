"""Plugin contribution surface defined in qma-core (CT-42; AD-1).

Plugin authors import ``PluginManifest``, ``PluginContext``, ``HookEvent``,
``HookResult``, handle kinds, and ``credential_ref`` from here — never from
``qma-daemon``. The daemon implements ``PluginContext``.
"""

from __future__ import annotations

from qma.core.plugins.boundaries import (
    BoundaryError,
    assert_core_definitions_only,
    assert_no_daemon_import,
    scan_daemon_imports,
    scan_forbidden_runtime_calls,
)
from qma.core.plugins.context import Disposer, HookHandler, PluginContext
from qma.core.plugins.credential import (
    CredentialRef,
    CredentialRefError,
    parse_credential_ref,
)
from qma.core.plugins.hooks import (
    HookEvent,
    HookPhase,
    HookResult,
    HookSource,
    build_hook_event,
    build_hook_result,
)
from qma.core.plugins.manifest import (
    DESK_PREFIX_TOKENS,
    ContributionDecl,
    ManifestError,
    PluginManifest,
    PluginRosterEntry,
    parse_plugin_manifest,
)
from qma.core.vocabulary.enums import HandleKind
from qma.core.vocabulary.handles import (
    MONEY_PATH_LIVE_WRITABLE_HANDLE_KINDS,
    READ_ONLY_EVIDENCE_HANDLE_KINDS,
    assert_handle_kind_not_money_path,
)

__all__ = [
    "DESK_PREFIX_TOKENS",
    "MONEY_PATH_LIVE_WRITABLE_HANDLE_KINDS",
    "READ_ONLY_EVIDENCE_HANDLE_KINDS",
    "BoundaryError",
    "ContributionDecl",
    "CredentialRef",
    "CredentialRefError",
    "Disposer",
    "HandleKind",
    "HookEvent",
    "HookHandler",
    "HookPhase",
    "HookResult",
    "HookSource",
    "ManifestError",
    "PluginContext",
    "PluginManifest",
    "PluginRosterEntry",
    "assert_core_definitions_only",
    "assert_handle_kind_not_money_path",
    "assert_no_daemon_import",
    "build_hook_event",
    "build_hook_result",
    "parse_credential_ref",
    "parse_plugin_manifest",
    "scan_daemon_imports",
    "scan_forbidden_runtime_calls",
]
