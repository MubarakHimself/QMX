"""Core-owned parent-library and capability barriers (FR-Q07, FR-Q09).

Default-deny parent surfaces, the six-rung capability ladder, the act-level
money-path deny-list, and QMA package dependency declarations — all code, never
settings or plugin contributions.
"""

from __future__ import annotations

from qma.core.barriers.capability import (
    CAPABILITY_LADDER,
    CAPABILITY_LADDER_OWNER,
    CapabilityError,
    CapabilityRung,
    assert_ladder_is_code_declared,
    capability_rung_rank,
    parse_capability_rung,
)
from qma.core.barriers.credential_allowlist import (
    ALLOWED_CREDENTIAL_REF_PREFIXES,
    CREDENTIAL_ALLOWLIST_OWNER,
    OUT_OF_SCOPE_CREDENTIAL_REF_PREFIXES,
    CredentialAllowlistCategory,
    CredentialAllowlistError,
    assert_allowlist_not_widenable,
    classify_credential_ref,
    is_credential_ref_allowed,
    refuse_credential_out_of_scope,
)
from qma.core.barriers.dependencies import (
    FORBIDDEN_QMA_IMPORT_ROOTS,
    QMA_CORE_ALLOWED_DEPS,
    QMA_DAEMON_ALLOWED_DEPS,
    QMA_PACKAGE_ALLOWED_DEPS,
    QMA_WIRE_ALLOWED_DEPS,
    DependencyBoundaryError,
    assert_no_qmf_venue_import,
    assert_package_deps_within,
    declared_project_dependencies,
    scan_qmf_venue_imports,
)
from qma.core.barriers.money_path import (
    MONEY_PATH_DENY_LIST,
    MONEY_PATH_DENY_LIST_OWNER,
    MoneyPathAct,
    MoneyPathDenyError,
    assert_deny_list_not_widenable,
    is_money_path_act_denied,
    parse_money_path_act,
    refuse_money_path_registration,
)
from qma.core.barriers.parent_surfaces import (
    PARENT_SURFACE_LIBRARIES,
    PERMITTED_PARENT_SURFACES,
    PROHIBITED_RECORD_FAMILIES,
    ParentLibrary,
    ParentSurfaceError,
    ParentSurfaceKind,
    ProhibitedMutation,
    ProhibitedRecordFamily,
    assert_no_zone_transition,
    assert_record_family_immutable,
    is_parent_surface_permitted,
    refuse_unlisted_parent_surface,
)

__all__ = [
    "ALLOWED_CREDENTIAL_REF_PREFIXES",
    "CAPABILITY_LADDER",
    "CAPABILITY_LADDER_OWNER",
    "CREDENTIAL_ALLOWLIST_OWNER",
    "FORBIDDEN_QMA_IMPORT_ROOTS",
    "MONEY_PATH_DENY_LIST",
    "MONEY_PATH_DENY_LIST_OWNER",
    "OUT_OF_SCOPE_CREDENTIAL_REF_PREFIXES",
    "PARENT_SURFACE_LIBRARIES",
    "PERMITTED_PARENT_SURFACES",
    "PROHIBITED_RECORD_FAMILIES",
    "QMA_CORE_ALLOWED_DEPS",
    "QMA_DAEMON_ALLOWED_DEPS",
    "QMA_PACKAGE_ALLOWED_DEPS",
    "QMA_WIRE_ALLOWED_DEPS",
    "CapabilityError",
    "CapabilityRung",
    "CredentialAllowlistCategory",
    "CredentialAllowlistError",
    "DependencyBoundaryError",
    "MoneyPathAct",
    "MoneyPathDenyError",
    "ParentLibrary",
    "ParentSurfaceError",
    "ParentSurfaceKind",
    "ProhibitedMutation",
    "ProhibitedRecordFamily",
    "assert_allowlist_not_widenable",
    "assert_deny_list_not_widenable",
    "assert_ladder_is_code_declared",
    "assert_no_qmf_venue_import",
    "assert_no_zone_transition",
    "assert_package_deps_within",
    "assert_record_family_immutable",
    "capability_rung_rank",
    "classify_credential_ref",
    "declared_project_dependencies",
    "is_credential_ref_allowed",
    "is_money_path_act_denied",
    "is_parent_surface_permitted",
    "parse_capability_rung",
    "parse_money_path_act",
    "refuse_credential_out_of_scope",
    "refuse_money_path_registration",
    "refuse_unlisted_parent_surface",
    "scan_qmf_venue_imports",
]
