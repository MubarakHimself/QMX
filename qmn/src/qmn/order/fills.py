"""Duplicate-fill disposition by venue-native deal/execution identity (TN-24b).

Within one account the venue-native deal or execution id is the durable fill key
(AD-27). The first durable copy stands. An equal-content redelivery is
idempotently ignored. Different content under the same key raises a data-quality
alarm, preserves both pieces of evidence, never overwrites the first, and never
mints a second virtual-ledger effect (DEC-0209; Story 24.9).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Ok, RefusalCategory, Result, Retryability, TypedRefusal

__all__ = [
    "DATA_QUALITY_EVENT_TYPE",
    "DUPLICATE_FILL_ALARM_CLASS",
    "AccountFillStore",
    "DurableFill",
    "FillIngestDisposition",
    "FillIngestResult",
]


DATA_QUALITY_EVENT_TYPE: Final[str] = "data quality"
DUPLICATE_FILL_ALARM_CLASS: Final[str] = "data-quality"


class FillIngestDisposition(StrEnum):
    """How one inbound fill resolves against the durable account store (TN-24b)."""

    ACCEPTED = "accepted"
    IDEMPOTENT_IGNORE = "idempotent-ignore"
    DATA_QUALITY_CONFLICT = "data-quality-conflict"


@dataclass(frozen=True, slots=True)
class DurableFill:
    """One durable fill copy keyed by venue-native deal/execution identity."""

    account_id: str
    venue_native_id: str
    content: Mapping[str, object]
    copy_index: int

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "account_id": self.account_id,
                "venue_native_id": self.venue_native_id,
                "content": dict(self.content),
                "copy_index": self.copy_index,
            }
        )


@dataclass(frozen=True, slots=True)
class FillIngestResult:
    """Evidence of one fill ingest against the durable store (TN-24b)."""

    disposition: FillIngestDisposition
    first: DurableFill
    retained: tuple[DurableFill, ...]
    virtual_ledger_effect: bool
    data_quality_alarm: bool
    journal_event_type: str | None = None

    @property
    def overwritten(self) -> bool:
        return False


def _freeze_content(content: Mapping[str, object]) -> Mapping[str, object]:
    frozen: dict[str, object] = {}
    for key, value in content.items():
        if isinstance(value, Mapping):
            nested = cast("Mapping[str, object]", value)
            frozen[key] = dict(_freeze_content(nested))
        elif isinstance(value, list):
            frozen[key] = tuple(cast("list[object]", value))
        elif isinstance(value, tuple):
            frozen[key] = cast("tuple[object, ...]", value)
        else:
            frozen[key] = value
    return MappingProxyType(frozen)


def _content_equal(left: Mapping[str, object], right: Mapping[str, object]) -> bool:
    return dict(left) == dict(right)


@dataclass
class AccountFillStore:
    """Per-account durable fill store keyed by venue-native deal/execution id.

    Equal redeliveries are ignored after the first durable copy. Conflicting
    content preserves every copy, alarms data quality, and never applies a
    second virtual-ledger effect.
    """

    _by_key: dict[tuple[str, str], list[DurableFill]] = field(
        default_factory=dict[tuple[str, str], list[DurableFill]]
    )
    _virtual_ledger_effects: int = 0

    @property
    def virtual_ledger_effect_count(self) -> int:
        return self._virtual_ledger_effects

    def retained_for(self, account_id: object, venue_native_id: object) -> tuple[DurableFill, ...]:
        key = self._key(account_id, venue_native_id)
        if isinstance(key, TypedRefusal):
            return ()
        copies = self._by_key.get(key)
        if copies is None:
            return ()
        return tuple(copies)

    def ingest(
        self,
        *,
        account_id: object,
        venue_native_id: object,
        content: object,
    ) -> Result[FillIngestResult]:
        """Ingest one fill under the venue-native deal/execution identity (TN-24b)."""
        key = self._key(account_id, venue_native_id)
        if isinstance(key, TypedRefusal):
            return key
        if not isinstance(content, Mapping):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "content",
                    "reason": "fill content is a mapping compared for equality under "
                    "the venue-native identity",
                    "given": type(content).__name__,
                },
            )
        frozen = _freeze_content(cast("Mapping[str, object]", content))
        acct, native = key
        existing = self._by_key.get(key)
        if existing is None:
            first = DurableFill(
                account_id=acct,
                venue_native_id=native,
                content=frozen,
                copy_index=0,
            )
            self._by_key[key] = [first]
            self._virtual_ledger_effects += 1
            return Ok(
                FillIngestResult(
                    disposition=FillIngestDisposition.ACCEPTED,
                    first=first,
                    retained=(first,),
                    virtual_ledger_effect=True,
                    data_quality_alarm=False,
                )
            )

        first = existing[0]
        if _content_equal(first.content, frozen):
            return Ok(
                FillIngestResult(
                    disposition=FillIngestDisposition.IDEMPOTENT_IGNORE,
                    first=first,
                    retained=tuple(existing),
                    virtual_ledger_effect=False,
                    data_quality_alarm=False,
                )
            )

        conflict = DurableFill(
            account_id=acct,
            venue_native_id=native,
            content=frozen,
            copy_index=len(existing),
        )
        existing.append(conflict)
        return Ok(
            FillIngestResult(
                disposition=FillIngestDisposition.DATA_QUALITY_CONFLICT,
                first=first,
                retained=tuple(existing),
                virtual_ledger_effect=False,
                data_quality_alarm=True,
                journal_event_type=DATA_QUALITY_EVENT_TYPE,
            )
        )

    @staticmethod
    def _key(account_id: object, venue_native_id: object) -> tuple[str, str] | TypedRefusal:
        if not isinstance(account_id, str) or account_id.strip() == "":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "account_id",
                    "reason": "duplicate-fill identity is scoped within one account",
                    "given": repr(account_id),
                },
            )
        if not isinstance(venue_native_id, str) or venue_native_id.strip() == "":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "venue_native_id",
                    "reason": "fill dedup key is the venue-native deal or execution id",
                    "given": repr(venue_native_id),
                },
            )
        return account_id.strip(), venue_native_id.strip()
