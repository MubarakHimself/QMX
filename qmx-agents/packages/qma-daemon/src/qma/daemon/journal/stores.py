"""Closed store list and declaration validator (FR-Q23; AD-6, AD-8).

Journal-derived projections are never independent append targets. Declared
independent stores each have exactly one named writer and one append path through
the daemon. A store not on this list may not be created. Declaration commits only
the list and fold metadata; consumer schemas materialize on first in-scope write.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Literal

from qmf.core import Ok, Result, is_refusal
from qmf.data.store.refusals import policy_rejection

__all__ = [
    "ANNOUNCEMENT_EVENT_BY_STORE",
    "ANNOUNCEMENT_REQUIRED_STORES",
    "CLOSED_INDEPENDENT_STORES",
    "CLOSED_PROJECTIONS",
    "CLOSED_STORE_NAMES",
    "DEFINITION_STORE_MEMBERS",
    "TELEMETRY_STORE",
    "EqualInstantDisposition",
    "FoldMetadata",
    "StoreClass",
    "StoreDeclaration",
    "StoreRegistry",
    "announce_event_for_store",
    "is_announcement_required",
    "is_closed_store",
]


class StoreClass(StrEnum):
    """The two AD-6 store classes."""

    JOURNAL_DERIVED_PROJECTION = "journal_derived_projection"
    INDEPENDENT_STORE = "independent_store"


EqualInstantDisposition = Literal["ascending_journal_seq"]
KnowledgeTimeBound = Literal["as_of_recorded_at"]
ORDERING_KEY_JOURNAL_SEQ: Final[str] = "journal_seq"
EQUAL_INSTANT_ASCENDING_JOURNAL_SEQ: Final[EqualInstantDisposition] = "ascending_journal_seq"
KNOWLEDGE_TIME_BOUND_AS_OF_RECORDED_AT: Final[KnowledgeTimeBound] = "as_of_recorded_at"


@dataclass(frozen=True, slots=True)
class FoldMetadata:
    """Full fold-contract metadata committed at declaration (FR-Q23–FR-Q25).

    Declares source stream, ``journal_seq`` ordering, ``as_of`` over
    ``recorded_at`` as the knowledge-time bound, and ascending-``journal_seq``
    equal-instant disposition. Filtered projections may omit ``source_stream``.
    """

    ordering_key: str = ORDERING_KEY_JOURNAL_SEQ
    equal_instant_disposition: EqualInstantDisposition = EQUAL_INSTANT_ASCENDING_JOURNAL_SEQ
    knowledge_time_bound: KnowledgeTimeBound = KNOWLEDGE_TIME_BOUND_AS_OF_RECORDED_AT
    source_stream: str | None = None

    def __post_init__(self) -> None:
        if self.ordering_key != ORDERING_KEY_JOURNAL_SEQ:
            msg = "fold ordering_key must be journal_seq (FR-Q24, FR-Q25; AD-6)"
            raise ValueError(msg)
        if self.equal_instant_disposition != EQUAL_INSTANT_ASCENDING_JOURNAL_SEQ:
            msg = (
                "equal instants dispose by ascending journal_seq, never by timestamp "
                "(FR-Q24, FR-Q25; AD-6)"
            )
            raise ValueError(msg)
        if self.knowledge_time_bound != KNOWLEDGE_TIME_BOUND_AS_OF_RECORDED_AT:
            msg = (
                "fold knowledge-time bound must be as_of over recorded_at "
                "(FR-Q25; AD-6)"
            )
            raise ValueError(msg)


# --- closed vocabulary (DEC-0305) -------------------------------------------

CLOSED_PROJECTIONS: Final[frozenset[str]] = frozenset(
    {
        "per_scope_event_streams",
        "mailboxes_and_delivery_state",
        "operator_approval_queue",
        "task_graph_state",
        "session_records",
        "agent_records",
        "desk_ledger_views",
        "ledger_quarantine_stream",
        "definition_store",
    }
)

DEFINITION_STORE_MEMBERS: Final[tuple[str, ...]] = (
    "desk_records",
    "role_records",
    "quant_records",
    "deployment_registry",
    "tool_registry",
    "tool_adapter_records",
    "toolset_records",
    "worker_template_records",
    "hook_registrations",
    "skill_registrations",
    "graph_template_registrations",
    "loop_registrations",
    "routine_records",
    "execution_environment_declarations",
    "variable_registry",
    "plugin_install_records",
)

CLOSED_INDEPENDENT_STORES: Final[frozenset[str]] = frozenset(
    {
        "task_ledger",
        "quant_ledger",
        "experiment_ledger",
        "artifact_store",
        "telemetry_store",
        "staging_store",
        "memory_provider_store",
    }
)

TELEMETRY_STORE: Final[str] = "telemetry_store"

CLOSED_STORE_NAMES: Final[frozenset[str]] = (
    CLOSED_PROJECTIONS | CLOSED_INDEPENDENT_STORES | frozenset(DEFINITION_STORE_MEMBERS)
)

# Evidence stores bound by the announcement law (telemetry exempt).
ANNOUNCEMENT_REQUIRED_STORES: Final[frozenset[str]] = frozenset(
    {
        "task_ledger",
        "quant_ledger",
        "experiment_ledger",
        "artifact_store",
        "staging_store",
        "memory_provider_store",
    }
)

ANNOUNCEMENT_EVENT_BY_STORE: Final[Mapping[str, str]] = MappingProxyType(
    {
        "task_ledger": "ledger.appended",
        "quant_ledger": "ledger.appended",
        "experiment_ledger": "ledger.appended",
        "artifact_store": "artifact.registered",
        "staging_store": "staging.appended",
        "memory_provider_store": "memory.admitted",
    }
)

_STORE_CLASS: Final[Mapping[str, StoreClass]] = MappingProxyType(
    {
        **dict.fromkeys(CLOSED_PROJECTIONS, StoreClass.JOURNAL_DERIVED_PROJECTION),
        **dict.fromkeys(
            DEFINITION_STORE_MEMBERS, StoreClass.JOURNAL_DERIVED_PROJECTION
        ),
        **dict.fromkeys(CLOSED_INDEPENDENT_STORES, StoreClass.INDEPENDENT_STORE),
    }
)


def is_closed_store(name: str) -> bool:
    """Return True when ``name`` is on the AD-6 closed store list."""
    return name in CLOSED_STORE_NAMES


def is_announcement_required(store: str) -> bool:
    """Return True when an append to ``store`` must emit a journal announcement."""
    return store in ANNOUNCEMENT_REQUIRED_STORES


def announce_event_for_store(store: str) -> str | None:
    """Return the ``noun.verb`` announcement event for ``store``, or None if exempt."""
    return ANNOUNCEMENT_EVENT_BY_STORE.get(store)


def _default_fold_metadata(name: str) -> FoldMetadata:
    """Attach the v1 fold contract when ``name`` is a fold; else ordering defaults.

    Filtered projections (per-scope streams, quarantine) are not folds and carry
    no ``source_stream``. Independent stores are not folds either.
    """
    # Lazy import avoids a stores ↔ fold_contracts cycle at module load.
    from qma.daemon.journal.fold_contracts import (  # noqa: PLC0415
        FILTERED_PROJECTIONS_NOT_FOLDS,
        fold_id_for_store,
        v1_fold_contract,
    )

    if name in FILTERED_PROJECTIONS_NOT_FOLDS or name in CLOSED_INDEPENDENT_STORES:
        return FoldMetadata()
    fold_id = fold_id_for_store(name)
    if fold_id is None:
        return FoldMetadata()
    contract = v1_fold_contract(fold_id)
    if contract is None:
        return FoldMetadata()
    return FoldMetadata(
        ordering_key=contract.ordering_key,
        equal_instant_disposition=contract.equal_instant_disposition,
        knowledge_time_bound=contract.knowledge_time_bound,
        source_stream=contract.source_stream,
    )


@dataclass(frozen=True, slots=True)
class StoreDeclaration:
    """A committed store/projection declaration (list + fold metadata only)."""

    name: str
    store_class: StoreClass
    fold_metadata: FoldMetadata
    materialized: bool = False


@dataclass
class StoreRegistry:
    """In-memory registry of declared closed stores; schemas materialize later."""

    _declarations: dict[str, StoreDeclaration] = field(default_factory=dict)

    @property
    def closed_list(self) -> frozenset[str]:
        """The closed store vocabulary this registry validates against."""
        return CLOSED_STORE_NAMES

    def declared(self) -> Mapping[str, StoreDeclaration]:
        """Snapshot of committed declarations (list + fold metadata)."""
        return MappingProxyType(dict(self._declarations))

    def declare(
        self,
        name: object,
        *,
        fold_metadata: FoldMetadata | None = None,
    ) -> Result[StoreDeclaration]:
        """Accept only a closed-list name; refuse anything outside it (FR-Q23).

        Commits the list entry and fold metadata. Does not materialize a consumer
        projection or independent-store schema — that happens on first write.
        """
        if not isinstance(name, str) or name.strip() == "":
            return policy_rejection(
                "store_declaration",
                "a store or projection declaration must name a non-empty closed-list "
                "member (FR-Q23; AD-6, AD-8)",
                given=repr(name),
            )
        if name not in CLOSED_STORE_NAMES:
            return policy_rejection(
                "store_declaration",
                "a store not on the closed AD-6 list may not be created (FR-Q23; AD-6, "
                "AD-8)",
                store=name,
                closed_list=sorted(CLOSED_STORE_NAMES),
            )
        existing = self._declarations.get(name)
        if existing is not None:
            return Ok(existing)
        meta = (
            fold_metadata if fold_metadata is not None else _default_fold_metadata(name)
        )
        declaration = StoreDeclaration(
            name=name,
            store_class=_STORE_CLASS[name],
            fold_metadata=meta,
            materialized=False,
        )
        self._declarations[name] = declaration
        return Ok(declaration)

    def materialize_on_first_write(self, name: str) -> Result[StoreDeclaration]:
        """Mark the consumer schema materialized on its first in-scope write.

        The store must already be declared (or is declared here as a convenience
        for the first write path). Outside the closed list is still refused.
        """
        declared = self.declare(name)
        if is_refusal(declared):
            return declared
        current = self._declarations[name]
        if current.materialized:
            return Ok(current)
        updated = StoreDeclaration(
            name=current.name,
            store_class=current.store_class,
            fold_metadata=current.fold_metadata,
            materialized=True,
        )
        self._declarations[name] = updated
        return Ok(updated)
