"""Concatenate CT-44 Knowledge search and QMB ``library.search`` (Stories 52.2–52.3).

Federated discovery is a read-time concatenate of two existing queries — never a
fourth store, never a door **run**, and Workbench AD-8 occupancy is unchanged
(this path consumes none). COMP-QMA-DAEMON owns Knowledge search; COMP-QMB owns
Artifact search via an injected port (the daemon never imports ``qmb`` and QMB
never opens daemon sqlite). Locators are not ``fp1``. Unified row caches,
copied-row Library indexes, and QMA staging reads are refused. Ranked /
semantic / hybrid retrieval stays ``unsupported-capability`` (GAP-0073).
Stage 0 hypotheses stay on ``qml.research`` and are refused as federated hits.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Protocol, runtime_checkable

from qma.core.ports.knowledge import (
    GAP_0073_KNOWLEDGE_HYBRID_INDEXING,
    CorpusSnapshot,
    refuse_hybrid_knowledge_indexing,
)
from qma.core.ports.qmb import QMB_OPENS_DAEMON_SQLITE, qmb_opens_daemon_sqlite
from qma.daemon.discovery.research_surface import (
    HYPOTHESES_ARE_FEDERATED_HITS,
    HYPOTHESIS_LISTING_SURFACE,
    REFUSED_HYPOTHESIS_KIND_TOKENS,
    refuse_federated_hypothesis_kwargs,
    refuse_hypothesis_kind_on_federated_search,
)
from qma.daemon.knowledge.service import KnowledgeService
from qma.wire.federated_discovery import (
    ARTIFACT_HIT_KINDS,
    ArtifactHit,
    FederatedHit,
    KnowledgeHit,
    library_kind_to_artifact_hit_kind,
)
from qmf.core import Ok, Result, is_refusal
from qmf.core.refusal import TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

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
    "SURFACE_ARTIFACT_LIBRARY",
    "SURFACE_KNOWLEDGE",
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


FEDERATED_SEARCH_CLASS: Final[str] = "qma-federated-search"
FEDERATED_SEARCH_OWNER: Final[str] = "COMP-QMA-DAEMON"
FEDERATED_SEARCH_OCCUPANCY: Final[str] = "none"
FEDERATED_SEARCH_IS_DOOR_RUN: Final[bool] = False
FEDERATED_SEARCH_OPENS_FOURTH_STORE: Final[bool] = False
FEDERATED_SEARCH_HOLDS_CACHE: Final[bool] = False
FEDERATED_SEARCH_READS_STAGING: Final[bool] = False
FEDERATED_SEARCH_QMB_OPENS_DAEMON_SQLITE: Final[bool] = QMB_OPENS_DAEMON_SQLITE

SURFACE_KNOWLEDGE: Final[str] = "ct-44-knowledge"
SURFACE_ARTIFACT_LIBRARY: Final[str] = "qmb-library-search"
FEDERATED_SEARCH_SURFACES: Final[tuple[str, ...]] = (
    SURFACE_KNOWLEDGE,
    SURFACE_ARTIFACT_LIBRARY,
)

_FOURTH_STORE_FIELDS: Final[tuple[str, ...]] = (
    "store",
    "sqlite",
    "database",
    "fourth_store",
    "new_store",
    "identity_store",
)
_STAGING_FIELDS: Final[tuple[str, ...]] = (
    "staging",
    "qma_staging",
    "refinement_proposals",
)
_CACHE_FIELDS: Final[tuple[str, ...]] = (
    "unified_row_cache",
    "copied_row_index",
    "copied_row_library_index",
    "row_cache",
    "library_index",
)


def federated_search_identity() -> dict[str, object]:
    """Identity-bearing federated-search fields. Package SemVer is omitted."""
    return {
        "class": FEDERATED_SEARCH_CLASS,
        "command": "facade_search",
        "gap_0073": GAP_0073_KNOWLEDGE_HYBRID_INDEXING,
        "holds_cache": FEDERATED_SEARCH_HOLDS_CACHE,
        "hypotheses_are_federated_hits": HYPOTHESES_ARE_FEDERATED_HITS,
        "hypothesis_listing_surface": HYPOTHESIS_LISTING_SURFACE,
        "is_door_run": FEDERATED_SEARCH_IS_DOOR_RUN,
        "occupancy": FEDERATED_SEARCH_OCCUPANCY,
        "opens_fourth_store": FEDERATED_SEARCH_OPENS_FOURTH_STORE,
        "owner": FEDERATED_SEARCH_OWNER,
        "qmb_opens_daemon_sqlite": FEDERATED_SEARCH_QMB_OPENS_DAEMON_SQLITE,
        "reads_staging": FEDERATED_SEARCH_READS_STAGING,
        "surfaces": list(FEDERATED_SEARCH_SURFACES),
        "tab_close_cancels": False,
    }


def refuse_federated_fourth_store(**extra: object) -> TypedRefusal:
    """Federated search never opens a fourth store (DEC-0389; FR-RES-07)."""
    field = str(extra.pop("field", "fourth_store"))
    return policy_rejection(
        field,
        "federated discovery concatenates CT-44 Knowledge search and QMB "
        "library.search over existing surfaces; it never opens a fourth store "
        "(FR-RES-07; DEC-0389; Workbench AD-14)",
        opens_fourth_store=False,
        occupancy=FEDERATED_SEARCH_OCCUPANCY,
        surfaces=list(FEDERATED_SEARCH_SURFACES),
        **extra,
    )


def refuse_federated_qma_staging_read(**extra: object) -> TypedRefusal:
    """Federated search does not read QMA staging (DEC-0389; Workbench AD-14)."""
    field = str(extra.pop("field", "staging"))
    return policy_rejection(
        field,
        "federated discovery does not read QMA staging; a fold of staging into "
        "Library discovery is refused (DEC-0389; Workbench AD-14; FR-RES-07)",
        reads_staging=False,
        occupancy=FEDERATED_SEARCH_OCCUPANCY,
        **extra,
    )


def refuse_unified_row_cache(**extra: object) -> TypedRefusal:
    """Refuse a unified / copied-row Library index on this path (DEC-0389)."""
    field = str(extra.pop("field", "unified_row_cache"))
    return policy_rejection(
        field,
        "federated discovery must not persist a unified row cache or copied-row "
        "Library index (DEC-0389; Workbench AD-14; FR-RES-07)",
        holds_cache=False,
        occupancy=FEDERATED_SEARCH_OCCUPANCY,
        **extra,
    )


def refuse_copied_row_library_index(**extra: object) -> TypedRefusal:
    """Alias refusal for a copied-row Library index proposal."""
    extra.setdefault("field", "copied_row_library_index")
    return refuse_unified_row_cache(**extra)


def refuse_locator_as_fp1(**extra: object) -> TypedRefusal:
    """Knowledge locators are not Artifact ``fp1`` identities (AD-9)."""
    field = str(extra.pop("field", "locator"))
    return policy_rejection(
        field,
        "Knowledge locators are cite handles, never fp1 Artifact identities "
        "(AD-9; FR-RES-07; DEC-0389)",
        **extra,
    )


def _requested_field(
    values: Mapping[str, object | None],
    names: Sequence[str],
) -> str | None:
    for name in names:
        if values.get(name) is not None:
            return name
    return None


def _snapshot_ref_of(
    snapshot: CorpusSnapshot | Mapping[str, object] | str,
) -> Result[str]:
    if isinstance(snapshot, CorpusSnapshot):
        return Ok(snapshot.id)
    if isinstance(snapshot, str):
        token = snapshot.strip()
        if token == "":
            return invalid_input(
                "snapshot",
                "federated search requires a non-empty snapshot_ref (CT-44)",
                given=repr(snapshot),
            )
        return Ok(token)
    for key in ("id", "snapshot_ref"):
        value = snapshot.get(key)
        if isinstance(value, str) and value.strip() != "":
            return Ok(value.strip())
    return invalid_input(
        "snapshot",
        "federated search requires a CorpusSnapshot or snapshot_ref (CT-44)",
        given=repr(type(snapshot).__name__),
    )


def _source_ref_of(source_id: object) -> Result[str]:
    if not isinstance(source_id, str) or source_id.strip() == "":
        return invalid_input(
            "source_id",
            "federated search requires a non-empty Knowledge source_id (CT-44)",
            given=repr(source_id),
        )
    return Ok(source_id.strip())


@runtime_checkable
class ArtifactLibrarySearchPort(Protocol):
    """Injected COMP-QMB ``library.search`` surface (Story 34.2 / B-15).

    Returns ``{fp1, kind}`` mappings only. The daemon never imports ``qmb`` and
    QMB never opens daemon sqlite through this port.
    """

    def search(
        self,
        *,
        kind: str | None = None,
        fp1: str | None = None,
        query: str | None = None,
    ) -> Result[Sequence[Mapping[str, object]]]:
        """Fold B-15 / ledger merge / Experiment Ledger refs into hit rows."""
        ...


@dataclass(frozen=True, slots=True)
class FederatedSearch:
    """Concatenated KnowledgeHit + ArtifactHit result. Occupancy is none."""

    hits: tuple[FederatedHit, ...]
    query: str
    occupancy: str = FEDERATED_SEARCH_OCCUPANCY
    surfaces: tuple[str, ...] = FEDERATED_SEARCH_SURFACES
    opens_fourth_store: bool = False
    holds_cache: bool = False
    reads_staging: bool = False
    is_door_run: bool = False
    qmb_opens_daemon_sqlite: bool = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "class": FEDERATED_SEARCH_CLASS,
                "command": "facade_search",
                "holds_cache": False,
                "hits": [dict(hit.to_payload()) for hit in self.hits],
                "is_door_run": False,
                "occupancy": FEDERATED_SEARCH_OCCUPANCY,
                "opens_fourth_store": False,
                "owner": FEDERATED_SEARCH_OWNER,
                "qmb_opens_daemon_sqlite": False,
                "query": self.query,
                "reads_staging": False,
                "surfaces": list(FEDERATED_SEARCH_SURFACES),
            }
        )


def _map_artifact_row(row: Mapping[str, object]) -> Result[ArtifactHit]:
    if row.get("research_ref") is not None:
        return refuse_hypothesis_kind_on_federated_search(
            given=repr(row.get("research_ref")),
            field="research_ref",
        )
    hit_class = row.get("hit_class")
    if isinstance(hit_class, str) and hit_class.strip().casefold() not in {
        "artifact",
        "",
    }:
        return refuse_hypothesis_kind_on_federated_search(
            given=hit_class,
            field="hit_class",
        )
    if "locator" in row and "fp1" not in row:
        return refuse_locator_as_fp1(given=repr(row.get("locator")))
    if "locator" in row and row.get("locator") is not None and row.get("fp1") == row.get(
        "locator"
    ):
        return refuse_locator_as_fp1(given=repr(row.get("locator")))
    raw_kind = row.get("kind")
    if not isinstance(raw_kind, str) or raw_kind.strip() == "":
        return invalid_input(
            "kind",
            "artifact library.search rows carry a Workbench AD-3 kind or "
            "query-hit tag (FR-RES-07)",
            given=repr(raw_kind),
        )
    kind_fold = raw_kind.strip().casefold().replace("_", "-")
    if (
        raw_kind.strip() in REFUSED_HYPOTHESIS_KIND_TOKENS
        or kind_fold in REFUSED_HYPOTHESIS_KIND_TOKENS
        or kind_fold.replace("-", " ") in REFUSED_HYPOTHESIS_KIND_TOKENS
    ):
        return refuse_hypothesis_kind_on_federated_search(given=raw_kind)
    mapped = library_kind_to_artifact_hit_kind(raw_kind)
    if mapped not in ARTIFACT_HIT_KINDS:
        return policy_rejection(
            "kind",
            "federated ArtifactHit.kind is a Workbench AD-3 roster kind or "
            "closed query-hit tag saved-view | analysis.published (FR-RES-07)",
            given=mapped,
            legal=sorted(ARTIFACT_HIT_KINDS),
        )
    return ArtifactHit.try_create(fp1=row.get("fp1"), kind=mapped)


@dataclass(slots=True)
class FederatedDiscoveryService:
    """Daemon-side concatenate of CT-44 search and injected library.search."""

    knowledge: KnowledgeService
    artifacts: ArtifactLibrarySearchPort

    def search(
        self,
        query: object,
        *,
        source_id: object,
        snapshot: CorpusSnapshot | Mapping[str, object] | str,
        kind: object = None,
        fp1: object = None,
        mode: str = "literal",
        store: object = None,
        sqlite: object = None,
        database: object = None,
        fourth_store: object = None,
        new_store: object = None,
        identity_store: object = None,
        staging: object = None,
        qma_staging: object = None,
        refinement_proposals: object = None,
        unified_row_cache: object = None,
        copied_row_index: object = None,
        copied_row_library_index: object = None,
        row_cache: object = None,
        library_index: object = None,
        hypothesis: object = None,
        hypotheses: object = None,
        research_candidate: object = None,
        research_candidates: object = None,
        qml_candidate: object = None,
        stage0_hypothesis: object = None,
        research_ref: object = None,
    ) -> Result[FederatedSearch]:
        """Concatenate Knowledge locators and Artifact ``fp1`` hits.

        Occupancy is ``none`` — never a door run. QMB never opens daemon sqlite.
        Stage 0 hypotheses are refused here; they list on ``qml.research``.
        """
        hypothesis_refusal = refuse_federated_hypothesis_kwargs(
            {
                "hypothesis": hypothesis,
                "hypotheses": hypotheses,
                "research_candidate": research_candidate,
                "research_candidates": research_candidates,
                "qml_candidate": qml_candidate,
                "stage0_hypothesis": stage0_hypothesis,
                "research_ref": research_ref,
            }
        )
        if hypothesis_refusal is not None:
            return hypothesis_refusal

        store_field = _requested_field(
            {
                "store": store,
                "sqlite": sqlite,
                "database": database,
                "fourth_store": fourth_store,
                "new_store": new_store,
                "identity_store": identity_store,
            },
            _FOURTH_STORE_FIELDS,
        )
        if store_field is not None:
            return refuse_federated_fourth_store(field=store_field, given=store_field)
        staging_field = _requested_field(
            {
                "staging": staging,
                "qma_staging": qma_staging,
                "refinement_proposals": refinement_proposals,
            },
            _STAGING_FIELDS,
        )
        if staging_field is not None:
            return refuse_federated_qma_staging_read(
                field=staging_field,
                given=staging_field,
            )
        cache_field = _requested_field(
            {
                "unified_row_cache": unified_row_cache,
                "copied_row_index": copied_row_index,
                "copied_row_library_index": copied_row_library_index,
                "row_cache": row_cache,
                "library_index": library_index,
            },
            _CACHE_FIELDS,
        )
        if cache_field is not None:
            return refuse_unified_row_cache(field=cache_field, given=cache_field)

        if mode != "literal":
            return refuse_hybrid_knowledge_indexing(mode=mode)

        if not isinstance(query, str) or query.strip() == "":
            return invalid_input(
                "query",
                "federated search query is a non-empty literal string "
                "(CT-44; FR-RES-03; FR-RES-07)",
                given=repr(query),
            )
        query_text = query.strip()

        source = _source_ref_of(source_id)
        if is_refusal(source):
            return source
        snap_ref = _snapshot_ref_of(snapshot)
        if is_refusal(snap_ref):
            return snap_ref

        knowledge_hits = self.knowledge.search(
            source.value,
            snapshot,
            query_text,
            mode=mode,
        )
        if is_refusal(knowledge_hits):
            return knowledge_hits

        hits: list[FederatedHit] = []
        for locator in knowledge_hits.value:
            built = KnowledgeHit.try_create(
                source_ref=source.value,
                snapshot_ref=snap_ref.value,
                locator=locator,
            )
            if is_refusal(built):
                return built
            hits.append(built.value)

        kind_token: str | None = None
        if kind is not None:
            if not isinstance(kind, str) or kind.strip() == "":
                return invalid_input(
                    "kind",
                    "artifact library.search kind is a non-empty string when set",
                    given=repr(kind),
                )
            kind_token = kind.strip()
            kind_fold = kind_token.casefold().replace("_", "-")
            if (
                kind_token in REFUSED_HYPOTHESIS_KIND_TOKENS
                or kind_fold in REFUSED_HYPOTHESIS_KIND_TOKENS
                or kind_fold.replace("-", " ") in REFUSED_HYPOTHESIS_KIND_TOKENS
            ):
                return refuse_hypothesis_kind_on_federated_search(given=kind_token)

        fp1_token: str | None = None
        if fp1 is not None:
            if isinstance(fp1, str) and not fp1.startswith("fp1:"):
                # A bare locator / path is not an Artifact identity (AD-9).
                return refuse_locator_as_fp1(given=repr(fp1), field="fp1")
            if not isinstance(fp1, str) or fp1.strip() == "":
                return invalid_input(
                    "fp1",
                    "artifact library.search fp1 is an fp1 fingerprint when set",
                    given=repr(fp1),
                )
            fp1_token = fp1.strip()

        artifact_rows = self.artifacts.search(
            kind=kind_token,
            fp1=fp1_token,
            query=query_text,
        )
        if is_refusal(artifact_rows):
            return artifact_rows

        for row in artifact_rows.value:
            mapped = _map_artifact_row(row)
            if is_refusal(mapped):
                return mapped
            hits.append(mapped.value)

        return Ok(
            FederatedSearch(
                hits=tuple(hits),
                query=query_text,
                occupancy=FEDERATED_SEARCH_OCCUPANCY,
                surfaces=FEDERATED_SEARCH_SURFACES,
                opens_fourth_store=False,
                holds_cache=False,
                reads_staging=False,
                is_door_run=False,
                # Law: QMB never opens daemon sqlite (FR-W24); constant is False.
                qmb_opens_daemon_sqlite=qmb_opens_daemon_sqlite(),
            )
        )
