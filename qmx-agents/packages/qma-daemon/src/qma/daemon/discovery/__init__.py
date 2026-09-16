"""Federated discovery — concatenate CT-44 + QMB library.search (Story 52.2)."""

from __future__ import annotations

from qma.daemon.discovery.federated import (
    FEDERATED_SEARCH_CLASS,
    FEDERATED_SEARCH_HOLDS_CACHE,
    FEDERATED_SEARCH_IS_DOOR_RUN,
    FEDERATED_SEARCH_OCCUPANCY,
    FEDERATED_SEARCH_OPENS_FOURTH_STORE,
    FEDERATED_SEARCH_OWNER,
    FEDERATED_SEARCH_QMB_OPENS_DAEMON_SQLITE,
    FEDERATED_SEARCH_READS_STAGING,
    FEDERATED_SEARCH_SURFACES,
    ArtifactLibrarySearchPort,
    FederatedDiscoveryService,
    FederatedSearch,
    federated_search_identity,
    refuse_copied_row_library_index,
    refuse_federated_fourth_store,
    refuse_federated_qma_staging_read,
    refuse_locator_as_fp1,
    refuse_unified_row_cache,
)

__all__ = [
    "FEDERATED_SEARCH_CLASS",
    "FEDERATED_SEARCH_HOLDS_CACHE",
    "FEDERATED_SEARCH_IS_DOOR_RUN",
    "FEDERATED_SEARCH_OCCUPANCY",
    "FEDERATED_SEARCH_OPENS_FOURTH_STORE",
    "FEDERATED_SEARCH_OWNER",
    "FEDERATED_SEARCH_QMB_OPENS_DAEMON_SQLITE",
    "FEDERATED_SEARCH_READS_STAGING",
    "FEDERATED_SEARCH_SURFACES",
    "ArtifactLibrarySearchPort",
    "FederatedDiscoveryService",
    "FederatedSearch",
    "federated_search_identity",
    "refuse_copied_row_library_index",
    "refuse_federated_fourth_store",
    "refuse_federated_qma_staging_read",
    "refuse_locator_as_fp1",
    "refuse_unified_row_cache",
]
