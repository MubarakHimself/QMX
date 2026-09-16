"""KnowledgeSource binding, plain-file adapter and citation copy gate (CT-44; FR-Q65)."""

from __future__ import annotations

from qma.daemon.knowledge.plain_file import (
    DEFAULT_PLAIN_FILE_CONFIDENCE_DIMENSIONS,
    PlainFileLibrarySource,
)
from qma.daemon.knowledge.seed_root import qmx_worktree_root, validate_seed_root_path
from qma.daemon.knowledge.service import (
    GAP_0073_KNOWLEDGE_HYBRID_INDEXING,
    KNOWLEDGE_QUERY_SURFACE,
    KNOWLEDGE_SOURCE_OPERATIONS,
    UNSCORED_CONFIDENCE_VALUE,
    ArtifactCopy,
    CiteOutcome,
    KnowledgeService,
    KnowledgeSourceRegistry,
    MissionSnapshotPin,
    SessionSnapshotPin,
    SourceBinding,
    unscored_evidence_confidence,
)

__all__ = [
    "DEFAULT_PLAIN_FILE_CONFIDENCE_DIMENSIONS",
    "GAP_0073_KNOWLEDGE_HYBRID_INDEXING",
    "KNOWLEDGE_QUERY_SURFACE",
    "KNOWLEDGE_SOURCE_OPERATIONS",
    "UNSCORED_CONFIDENCE_VALUE",
    "ArtifactCopy",
    "CiteOutcome",
    "KnowledgeService",
    "KnowledgeSourceRegistry",
    "MissionSnapshotPin",
    "PlainFileLibrarySource",
    "SessionSnapshotPin",
    "SourceBinding",
    "qmx_worktree_root",
    "unscored_evidence_confidence",
    "validate_seed_root_path",
]
