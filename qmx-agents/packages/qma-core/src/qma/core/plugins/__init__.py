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
    FORBIDDEN_HOOK_IMPLEMENTATION_KINDS,
    HookEvent,
    HookImplementationKind,
    HookPhase,
    HookResult,
    HookSource,
    assert_hook_result_phase_law,
    build_hook_event,
    build_hook_result,
    parse_hook_implementation_kind,
)
from qma.core.plugins.manifest import (
    DESK_PREFIX_TOKENS,
    ContributionDecl,
    ManifestError,
    PluginManifest,
    PluginRosterEntry,
    parse_plugin_manifest,
)
from qma.core.plugins.secret_schema import (
    FORBIDDEN_SECRET_PAYLOAD_KEYS,
    HOOK_SECRET_EXCLUDED_FIELDS,
    assert_no_secret_in_hook_payloads,
    assert_no_secret_in_mapping,
)
from qma.core.vocabulary.enums import HandleKind
from qma.core.vocabulary.handles import (
    MONEY_PATH_LIVE_WRITABLE_HANDLE_KINDS,
    READ_ONLY_EVIDENCE_HANDLE_KINDS,
    assert_handle_kind_not_money_path,
)

__all__ = [
    "DESK_PREFIX_TOKENS",
    "FORBIDDEN_HOOK_IMPLEMENTATION_KINDS",
    "FORBIDDEN_SECRET_PAYLOAD_KEYS",
    "HOOK_SECRET_EXCLUDED_FIELDS",
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
    "HookImplementationKind",
    "HookPhase",
    "HookResult",
    "HookSource",
    "ManifestError",
    "PluginContext",
    "PluginManifest",
    "PluginRosterEntry",
    "assert_core_definitions_only",
    "assert_handle_kind_not_money_path",
    "assert_hook_result_phase_law",
    "assert_no_daemon_import",
    "assert_no_secret_in_hook_payloads",
    "assert_no_secret_in_mapping",
    "build_hook_event",
    "build_hook_result",
    "parse_credential_ref",
    "parse_hook_implementation_kind",
    "parse_plugin_manifest",
    "scan_daemon_imports",
    "scan_forbidden_runtime_calls",
]
