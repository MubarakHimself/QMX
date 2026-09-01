"""V1 fold-contract registry (FR-Q25; AD-6).

Every v1 fold declares its source stream, ``journal_seq`` ordering key,
``as_of`` over ``recorded_at`` knowledge-time bound, and ascending-``journal_seq``
equal-instant disposition. Per-scope event streams and the ledger quarantine
stream are filtered projections, not folds. A new fold is refused unless a spine
amendment adds its contract. Consumer projections do not materialize before the
first in-scope write (StoreRegistry).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal

from qma.daemon.journal.stores import DEFINITION_STORE_MEMBERS
from qmf.core import Ok, Result
from qmf.data.store.refusals import policy_rejection

__all__ = [
    "EQUAL_INSTANT_ASCENDING_JOURNAL_SEQ",
    "FILTERED_PROJECTIONS_NOT_FOLDS",
    "KNOWLEDGE_TIME_BOUND_AS_OF_RECORDED_AT",
    "ORDERING_KEY_JOURNAL_SEQ",
    "V1_FOLD_IDS",
    "FoldContract",
    "FoldContractRegistry",
    "v1_fold_contract",
]

ORDERING_KEY_JOURNAL_SEQ: Final[str] = "journal_seq"
KNOWLEDGE_TIME_BOUND_AS_OF_RECORDED_AT: Final[str] = "as_of_recorded_at"
EQUAL_INSTANT_ASCENDING_JOURNAL_SEQ: Final[str] = "ascending_journal_seq"

EqualInstantDisposition = Literal["ascending_journal_seq"]
KnowledgeTimeBound = Literal["as_of_recorded_at"]


@dataclass(frozen=True, slots=True)
class FoldContract:
    """The four fold-contract elements every v1 fold must declare (FR-Q25)."""

    fold_id: str
    source_stream: str
    ordering_key: str = ORDERING_KEY_JOURNAL_SEQ
    knowledge_time_bound: KnowledgeTimeBound = KNOWLEDGE_TIME_BOUND_AS_OF_RECORDED_AT
    equal_instant_disposition: EqualInstantDisposition = (
        EQUAL_INSTANT_ASCENDING_JOURNAL_SEQ
    )

    def __post_init__(self) -> None:
        if self.ordering_key != ORDERING_KEY_JOURNAL_SEQ:
            msg = "fold ordering_key must be journal_seq (FR-Q25; AD-6)"
            raise ValueError(msg)
        if self.knowledge_time_bound != KNOWLEDGE_TIME_BOUND_AS_OF_RECORDED_AT:
            msg = (
                "fold knowledge-time bound must be as_of over recorded_at "
                "(FR-Q25; AD-6)"
            )
            raise ValueError(msg)
        if self.equal_instant_disposition != EQUAL_INSTANT_ASCENDING_JOURNAL_SEQ:
            msg = (
                "equal instants dispose by ascending journal_seq, never by "
                "timestamp (FR-Q25; AD-6)"
            )
            raise ValueError(msg)
        if not self.fold_id or not self.source_stream:
            msg = "fold_id and source_stream are required (FR-Q25; AD-6)"
            raise ValueError(msg)


def _contract(fold_id: str, source_stream: str) -> FoldContract:
    return FoldContract(fold_id=fold_id, source_stream=source_stream)


# Filtered projections — not folds; declare no fold contract (AD-6).
FILTERED_PROJECTIONS_NOT_FOLDS: Final[frozenset[str]] = frozenset(
    {
        "per_scope_event_streams",
        "ledger_quarantine_stream",
    }
)

# Core v1 folds named by AD-6 / FR-Q25 (excluding definition-store members).
_CORE_V1_FOLDS: Final[dict[str, FoldContract]] = {
    "desk_ledger_views": _contract(
        "desk_ledger_views",
        "ledger.appended",
    ),
    "task_state": _contract("task_state", "task.*"),
    "mission_state": _contract("mission_state", "mission.*"),
    "session_state": _contract("session_state", "session.*"),
    "agent_state": _contract("agent_state", "agent.*"),
    "mailbox_delivery_state": _contract("mailbox_delivery_state", "message.*"),
    "deployment_provider_health": _contract(
        "deployment_provider_health",
        "deployment.*",
    ),
    "staging_application_state": _contract(
        "staging_application_state",
        "proposal.*",
    ),
}

# Definition-store registries are each a v1 fold over their noun.verb stream.
_DEFINITION_FOLD_STREAMS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "desk_records": "desk.*",
        "role_records": "role.*",
        "quant_records": "quant.*",
        "deployment_registry": "deployment.*",
        "tool_registry": "tool.*",
        "tool_adapter_records": "tool_adapter.*",
        "toolset_records": "toolset.*",
        "worker_template_records": "worker_template.*",
        "hook_registrations": "hook.*",
        "skill_registrations": "skill.*",
        "graph_template_registrations": "graph_template.*",
        "loop_registrations": "loop.*",
        "routine_records": "routine.*",
        "execution_environment_declarations": "execution_environment.*",
        "variable_registry": "variable.*",
        "plugin_install_records": "plugin.*",
    }
)


def _build_v1_contracts() -> Mapping[str, FoldContract]:
    contracts: dict[str, FoldContract] = dict(_CORE_V1_FOLDS)
    for member in DEFINITION_STORE_MEMBERS:
        stream = _DEFINITION_FOLD_STREAMS[member]
        contracts[member] = _contract(member, stream)
    return MappingProxyType(contracts)


V1_FOLD_CONTRACTS: Final[Mapping[str, FoldContract]] = _build_v1_contracts()
V1_FOLD_IDS: Final[frozenset[str]] = frozenset(V1_FOLD_CONTRACTS)

# Closed-list projection names that share a v1 fold contract (store → fold_id).
_STORE_TO_FOLD: Final[Mapping[str, str]] = MappingProxyType(
    {
        "desk_ledger_views": "desk_ledger_views",
        "task_graph_state": "task_state",
        "session_records": "session_state",
        "agent_records": "agent_state",
        "mailboxes_and_delivery_state": "mailbox_delivery_state",
        "operator_approval_queue": "mailbox_delivery_state",
        "deployment_registry": "deployment_registry",
        **{member: member for member in DEFINITION_STORE_MEMBERS},
    }
)


def v1_fold_contract(fold_id: str) -> FoldContract | None:
    """Return the ratified v1 contract for ``fold_id``, or None if unknown."""
    return V1_FOLD_CONTRACTS.get(fold_id)


def fold_id_for_store(store_name: str) -> str | None:
    """Map a closed-list projection name to its v1 fold id, if it is a fold."""
    if store_name in FILTERED_PROJECTIONS_NOT_FOLDS:
        return None
    return _STORE_TO_FOLD.get(store_name)


@dataclass
class FoldContractRegistry:
    """Registers only the ratified v1 fold contracts (FR-Q25; AD-6).

    A fold outside the v1 list is refused — adding one requires a spine amendment.
    Registration commits metadata only; materialization stays on first write.
    """

    _registered: dict[str, FoldContract] = field(default_factory=dict[str, FoldContract])

    @property
    def v1_fold_ids(self) -> frozenset[str]:
        return V1_FOLD_IDS

    def registered(self) -> Mapping[str, FoldContract]:
        return MappingProxyType(dict(self._registered))

    def register(self, fold_id: object) -> Result[FoldContract]:
        """Register a v1 fold contract; refuse anything outside the ratified set."""
        if not isinstance(fold_id, str) or fold_id.strip() == "":
            return policy_rejection(
                "fold_contract",
                "a fold contract registration names a non-empty v1 fold id "
                "(FR-Q25; AD-6)",
                given=repr(fold_id),
            )
        if fold_id in FILTERED_PROJECTIONS_NOT_FOLDS:
            return policy_rejection(
                "fold_contract",
                "per-scope event streams and the ledger quarantine stream are "
                "filtered projections, not folds, and declare no fold contract "
                "(FR-Q25; AD-6)",
                fold_id=fold_id,
            )
        contract = V1_FOLD_CONTRACTS.get(fold_id)
        if contract is None:
            return policy_rejection(
                "fold_contract",
                "a new fold is refused unless a spine amendment adds its "
                "contract; only the ratified v1 fold list may be registered "
                "(FR-Q25; AD-6)",
                fold_id=fold_id,
                v1_folds=sorted(V1_FOLD_IDS),
            )
        existing = self._registered.get(fold_id)
        if existing is not None:
            return Ok(existing)
        self._registered[fold_id] = contract
        return Ok(contract)

    def register_all_v1(self) -> Mapping[str, FoldContract]:
        """Register every ratified v1 fold contract (idempotent)."""
        for fold_id in sorted(V1_FOLD_IDS):
            self.register(fold_id)
        return self.registered()

    def require(self, fold_id: str) -> Result[FoldContract]:
        """Return a previously registered contract, or refuse if missing."""
        contract = self._registered.get(fold_id)
        if contract is None:
            return policy_rejection(
                "fold_contract",
                "fold contract is not registered; register the v1 contract "
                "before exposing the fold (FR-Q25; AD-6)",
                fold_id=fold_id,
            )
        return Ok(contract)
