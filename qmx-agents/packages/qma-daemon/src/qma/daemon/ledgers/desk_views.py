"""Read-time desk ledger views over the three ledger stores (AD-9; FR-Q59).

Research, Trading, Development, Analysis and PM ledgers are views, never
stores. The fold streams ``ledger.appended`` announcements from Task, Quant
and Experiment Ledgers. Mission reports stay Deferred GAP-0082.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

from qma.core.ontology import DESK_DISPLAY_NAMES, DeskSlug, Quant
from qma.daemon.journal.fold_contracts import v1_fold_contract
from qma.daemon.journal.ordering import AnnouncedRecord, order_by_announcement_journal_seq
from qma.daemon.journal.stores import CLOSED_INDEPENDENT_STORES
from qma.daemon.ledgers.announcements import (
    DESK_LEDGER_INDEX_KEYS,
    LEDGER_STORE_NAMES,
    LedgerAppendAnnouncement,
)
from qma.daemon.ledgers.experiment import ExperimentLedgerStore
from qma.daemon.ledgers.quant import QuantLedgerStore
from qma.daemon.ledgers.task import TaskLedgerStore
from qmf.core import Ok, Result, TypedRefusal, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "DESK_LEDGER_INDEX_KEYS",
    "DESK_LEDGER_VIEW_FOLD_ID",
    "GAP_0082_DEFERRED",
    "LEDGER_STORE_NAMES",
    "DeskLedgerView",
    "DeskLedgerViews",
    "refuse_fourth_ledger_store",
    "refuse_mission_report",
]


DESK_LEDGER_VIEW_FOLD_ID: Final[str] = "desk_ledger_views"
GAP_0082_DEFERRED: Final[str] = "GAP-0082"

# Names that would mint a fourth ledger store or a per-desk store.
_FOURTH_LEDGER_STORE_NAMES: Final[frozenset[str]] = frozenset(
    {
        "research_ledger",
        "trading_ledger",
        "development_ledger",
        "dev_ledger",
        "analysis_ledger",
        "pm_ledger",
        "desk_ledger",
        "mission_ledger",
        "mission_report",
        "mission_reports",
    }
)


def refuse_mission_report(*, mission_id: object = None) -> TypedRefusal:
    """Mission-level ledger reports are Deferred GAP-0082 (DEC-0338; FR-Q59)."""
    return policy_rejection(
        "mission_report",
        "Mission reports — an agent-derived synthesis over a mission's task "
        "ledgers — are Deferred GAP-0082; in v1 no mission-level ledger or "
        "report synthesizes over Task Ledgers (DEC-0338; FR-Q59)",
        gap=GAP_0082_DEFERRED,
        deferred=True,
        mission_id=mission_id,
    )


def refuse_fourth_ledger_store(name: object) -> Result[str]:
    """Refuse a fourth ledger store; the three stores are closed (AD-9)."""
    if not isinstance(name, str) or name.strip() == "":
        return invalid_input("store", "a ledger store name is a non-empty string")
    if name in LEDGER_STORE_NAMES:
        return Ok(name)
    if name == DESK_LEDGER_VIEW_FOLD_ID:
        return policy_rejection(
            "store",
            "desk_ledger_views is a read-time fold, never an independent ledger "
            "store (AD-9; FR-Q59)",
            store=name,
        )
    return policy_rejection(
        "store",
        "Research, Trading, Development, Analysis and PM ledgers are read-time "
        "views over Task, Quant and Experiment Ledgers; no fourth ledger store "
        "is created (CT-51; AD-9; FR-Q59)",
        store=name,
        ledger_stores=sorted(LEDGER_STORE_NAMES),
        closed_independent_stores=sorted(CLOSED_INDEPENDENT_STORES),
        excluded_fourth_stores=sorted(_FOURTH_LEDGER_STORE_NAMES),
    )


def _parse_desk(desk: DeskSlug | str) -> Result[DeskSlug]:
    if isinstance(desk, DeskSlug):
        return Ok(desk)
    try:
        return Ok(DeskSlug(desk))
    except ValueError:
        return invalid_input(
            "desk",
            "desk ledger views are Research, Trading, Development, Analysis, or PM",
            given=repr(desk),
        )


@dataclass(frozen=True, slots=True)
class DeskLedgerView:
    """One derived desk ledger — a view, never a store."""

    desk: DeskSlug
    rows: tuple[LedgerAppendAnnouncement, ...]
    as_of: int | None = None
    index: Mapping[str, str] = field(default_factory=dict[str, str])

    def __post_init__(self) -> None:
        object.__setattr__(self, "index", MappingProxyType(dict(self.index)))

    @property
    def is_store(self) -> bool:
        return False

    @property
    def fold_id(self) -> str:
        return DESK_LEDGER_VIEW_FOLD_ID

    def to_payload(self) -> Mapping[str, object]:
        contract = v1_fold_contract(DESK_LEDGER_VIEW_FOLD_ID)
        payload: dict[str, object] = {
            "view": DESK_DISPLAY_NAMES[self.desk],
            "desk": self.desk.value,
            "is_store": False,
            "fold_id": DESK_LEDGER_VIEW_FOLD_ID,
            "stores": sorted(LEDGER_STORE_NAMES),
            "index_keys": sorted(DESK_LEDGER_INDEX_KEYS),
            "rows": [dict(row.to_payload()) for row in self.rows],
            "gap_0082": "deferred",
        }
        if contract is not None:
            payload["source_stream"] = contract.source_stream
            payload["ordering_key"] = contract.ordering_key
            payload["knowledge_time_bound"] = contract.knowledge_time_bound
            payload["equal_instant_disposition"] = contract.equal_instant_disposition
        if self.as_of is not None:
            payload["as_of"] = self.as_of
        if self.index:
            payload["index"] = dict(self.index)
        return MappingProxyType(payload)


@dataclass
class DeskLedgerViews:
    """Derive the five desk ledgers at read time from the three stores."""

    task_ledgers: TaskLedgerStore | None = None
    quant_ledgers: QuantLedgerStore | None = None
    experiment_ledgers: ExperimentLedgerStore | None = None
    _quants: dict[str, Quant] = field(default_factory=dict[str, Quant])

    def remember_quant(self, quant: Quant) -> None:
        """Index a Quant so desk membership is not parsed from ``ActorId``."""
        self._quants[quant.actor_id.value] = quant

    def mission_report(self, mission_id: object) -> TypedRefusal:
        """Explicit GAP-0082 exclusion — never a derived mission ledger."""
        _ = self
        return refuse_mission_report(mission_id=mission_id)

    def declare_store(self, name: object) -> Result[str]:
        """Refuse minting a per-desk or mission ledger store."""
        _ = self
        if isinstance(name, str) and name in LEDGER_STORE_NAMES:
            return Ok(name)
        return refuse_fourth_ledger_store(name)

    def derive(
        self,
        desk: DeskSlug | str,
        *,
        as_of: int | None = None,
        quant: str | None = None,
        agent: str | None = None,
        mission: str | None = None,
        task: str | None = None,
        experiment: str | None = None,
        date: str | None = None,
        mission_report: bool = False,
    ) -> Result[DeskLedgerView]:
        """Fold Task, Quant, and Experiment Ledgers at read time (FR-Q59)."""
        if mission_report:
            return refuse_mission_report(mission_id=mission)
        parsed = _parse_desk(desk)
        if is_refusal(parsed):
            return parsed
        desk_slug = parsed.value
        filters: dict[str, str] = {"desk": desk_slug.value}
        if quant is not None:
            filters["quant"] = quant
        if agent is not None:
            filters["agent"] = agent
        if mission is not None:
            filters["mission"] = mission
        if task is not None:
            filters["task"] = task
        if experiment is not None:
            filters["experiment"] = experiment
        if date is not None:
            filters["date"] = date

        rows = self._collect()
        matched: list[LedgerAppendAnnouncement] = []
        for row in rows:
            if as_of is not None and row.recorded_at > as_of:
                continue
            if not self._row_matches(row, desk_slug=desk_slug, filters=filters):
                continue
            matched.append(row)

        ordered_records = order_by_announcement_journal_seq(
            [
                AnnouncedRecord(
                    journal_seq=row.journal_seq,
                    store=row.store,
                    record_fp1=str(row.journal_seq),
                    recorded_at=row.recorded_at,
                    payload=row,
                )
                for row in matched
            ]
        )
        ordered = tuple(
            cast_row.payload
            for cast_row in ordered_records
            if isinstance(cast_row.payload, LedgerAppendAnnouncement)
        )
        return Ok(
            DeskLedgerView(
                desk=desk_slug,
                rows=ordered,
                as_of=as_of,
                index=filters,
            )
        )

    def _collect(self) -> tuple[LedgerAppendAnnouncement, ...]:
        rows: list[LedgerAppendAnnouncement] = []
        if self.task_ledgers is not None:
            rows.extend(self.task_ledgers.announcements())
        if self.quant_ledgers is not None:
            rows.extend(self.quant_ledgers.announcements())
        if self.experiment_ledgers is not None:
            rows.extend(self.experiment_ledgers.announcements())
        return tuple(rows)

    def _desk_for(self, actor_id: str | None) -> DeskSlug | None:
        if actor_id is None:
            return None
        known = self._quants.get(actor_id)
        if known is not None:
            return known.desk
        if self.quant_ledgers is not None:
            for quant in self.quant_ledgers.quants():
                if quant.actor_id.value == actor_id:
                    return quant.desk
        return None

    def _row_matches(
        self,
        row: LedgerAppendAnnouncement,
        *,
        desk_slug: DeskSlug,
        filters: Mapping[str, str],
    ) -> bool:
        row_desk = row.desk
        if row_desk is None:
            resolved = self._desk_for(row.quant)
            row_desk = None if resolved is None else resolved.value
        if row_desk != desk_slug.value:
            return False
        for key, wanted in filters.items():
            if key == "desk":
                continue
            actual = row.index_value(key)
            if actual != wanted:
                return False
        return True
