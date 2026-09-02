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
    EMPTY_COLLECTION_KEYS,
    OPERATOR_ASSIGNED_MANIFEST_FIELDS,
    ContributionDecl,
    ManifestError,
    PluginManifest,
    PluginRosterEntry,
    parse_plugin_manifest,
    require_desk_prefix_plugin_id,
)
from qma.core.plugins.secret_schema import (
    FORBIDDEN_SECRET_PAYLOAD_KEYS,
    HOOK_SECRET_EXCLUDED_FIELDS,
    assert_no_secret_in_hook_payloads,
    assert_no_secret_in_mapping,
)
from qma.core.vocabulary.enums import HandleKind
from qma.core.vocabulary.handles import (
    CLOSED_HANDLE_KINDS,
    FORBIDDEN_LIVE_MONEY_PATH_HANDLE_TARGETS,
    HANDLE_KIND_CONTRIBUTION_POINTS,
    MONEY_PATH_LIVE_WRITABLE_HANDLE_KINDS,
    MONEY_PATH_RELEVANT_FIELDS,
    QMA_OWNED_CANDIDATE_ORIGIN,
    READ_ONLY_EVIDENCE_HANDLE_KINDS,
    STRATEGY_CANDIDATE_ZONE,
    assert_handle_kind_not_money_path,
    is_handle_kind_contribution_point,
    refuse_plugin_handle_kind_extension,
)

__all__ = [
    "CLOSED_HANDLE_KINDS",
    "DESK_PREFIX_TOKENS",
    "EMPTY_COLLECTION_KEYS",
    "FORBIDDEN_HOOK_IMPLEMENTATION_KINDS",
    "FORBIDDEN_LIVE_MONEY_PATH_HANDLE_TARGETS",
    "FORBIDDEN_SECRET_PAYLOAD_KEYS",
    "HANDLE_KIND_CONTRIBUTION_POINTS",
    "HOOK_SECRET_EXCLUDED_FIELDS",
    "MONEY_PATH_LIVE_WRITABLE_HANDLE_KINDS",
    "MONEY_PATH_RELEVANT_FIELDS",
    "OPERATOR_ASSIGNED_MANIFEST_FIELDS",
    "QMA_OWNED_CANDIDATE_ORIGIN",
    "READ_ONLY_EVIDENCE_HANDLE_KINDS",
    "STRATEGY_CANDIDATE_ZONE",
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
    "is_handle_kind_contribution_point",
    "parse_credential_ref",
    "parse_hook_implementation_kind",
    "parse_plugin_manifest",
    "refuse_plugin_handle_kind_extension",
    "require_desk_prefix_plugin_id",
    "scan_daemon_imports",
    "scan_forbidden_runtime_calls",
]
