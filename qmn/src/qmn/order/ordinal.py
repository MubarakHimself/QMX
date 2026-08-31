"""Lifetime-monotone command ordinal, distinct from the CT-13 journal sequence (TN-6).

The journal sequence is gapless per ``(writer, boot epoch)`` and restarts each
boot. The command ordinal is monotone for the life of a ``(VenueId, account)``
stream, never reused, with a durable high-water mark recovered before the
sequencer opens. A stream that cannot recover the high-water refuses to open
rather than restarting the count (DEC-0191, DEC-0224).
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    Account,
    Ok,
    RecordSink,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    VenueId,
    is_refusal,
)

__all__ = [
    "COMMAND_ORDINAL_RECORD_CLASS",
    "JOURNAL_SEQUENCE_RECORD_CLASS",
    "CommandOrdinalHighWater",
    "CommandOrdinalStore",
    "JournalSequenceCursor",
]


COMMAND_ORDINAL_RECORD_CLASS: Final[str] = "command-ordinal-high-water"
JOURNAL_SEQUENCE_RECORD_CLASS: Final[str] = "journal-sequence-cursor"


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context={"field": field, "reason": reason, **extra},
    )


@dataclass(frozen=True, slots=True)
class CommandOrdinalHighWater:
    """Durable high-water mark for one command stream's ordinal counter."""

    venue_id: str
    account_id: str
    high_water: int

    def as_mapping(self) -> MappingProxyType[str, object]:
        return MappingProxyType(
            {
                "class": COMMAND_ORDINAL_RECORD_CLASS,
                "venue_id": self.venue_id,
                "account_id": self.account_id,
                "high_water": self.high_water,
            }
        )


@dataclass(frozen=True, slots=True)
class JournalSequenceCursor:
    """CT-13 journal sequence cursor — gapless per ``(writer, boot epoch)``.

    Deliberately a different object from :class:`CommandOrdinalStore`. A journal
    sequence restarts at each boot epoch; a command ordinal never does.
    """

    writer_id: str
    boot_epoch: str
    next_seq: int = 1

    def allocate(self) -> tuple[JournalSequenceCursor, int]:
        """Return ``(advanced cursor, allocated sequence)`` for this boot epoch."""
        return (
            JournalSequenceCursor(
                writer_id=self.writer_id,
                boot_epoch=self.boot_epoch,
                next_seq=self.next_seq + 1,
            ),
            self.next_seq,
        )

    def restart_for_boot(self, boot_epoch: object) -> Result[JournalSequenceCursor]:
        """Restart the gapless journal sequence for a new boot epoch."""
        if not isinstance(boot_epoch, str) or boot_epoch.strip() == "":
            return _invalid(
                "boot_epoch",
                "journal sequence restarts per boot epoch; boot_epoch is a non-empty token",
                given=repr(boot_epoch),
            )
        return Ok(
            JournalSequenceCursor(
                writer_id=self.writer_id,
                boot_epoch=boot_epoch.strip(),
                next_seq=1,
            )
        )


class CommandOrdinalStore:
    """Lifetime-monotone ordinal allocator for one ``(VenueId, account)`` stream.

    Recover the durable high-water via :meth:`recover` **before** opening the
    command sequencer. :meth:`allocate` persists the new high-water before the
    ordinal is handed to command mint; reuse of a prior ordinal, or an
    unpersistable high-water write, blocks submission (DEC-0224).
    """

    __slots__ = (
        "_account",
        "_high_water",
        "_issued",
        "_record_sink",
        "_recovered",
        "_submitted",
        "_venue_id",
    )

    def __init__(
        self,
        venue_id: VenueId,
        account: Account,
        record_sink: RecordSink[object],
    ) -> None:
        self._venue_id = venue_id
        self._account = account
        self._record_sink = record_sink
        self._high_water = 0
        self._recovered = False
        self._issued: set[int] = set()
        self._submitted: set[int] = set()

    @classmethod
    def try_create(
        cls,
        venue_id: object,
        account: object,
        record_sink: object,
    ) -> Result[CommandOrdinalStore]:
        """Validate stream identity and the injected durable sink."""
        if not isinstance(venue_id, VenueId) or venue_id.value.strip() == "":
            return _invalid(
                "venue_id",
                "command ordinals are scoped to a VenueId",
                given=repr(venue_id),
            )
        if not isinstance(account, Account):
            return _invalid(
                "account",
                "command ordinals are scoped to an Account on the stream",
                given=repr(account),
            )
        if account.venue != venue_id:
            return _invalid(
                "account",
                "account does not belong to this VenueId stream",
                venue=venue_id.value,
                account_venue=account.venue.value,
            )
        if not isinstance(record_sink, RecordSink):
            return _invalid(
                "record_sink",
                "the composition root injects a RecordSink for the ordinal high-water",
                given=repr(record_sink),
            )
        return Ok(cls(venue_id, account, cast("RecordSink[object]", record_sink)))

    @property
    def venue_id(self) -> VenueId:
        return self._venue_id

    @property
    def account(self) -> Account:
        return self._account

    @property
    def high_water(self) -> int:
        return self._high_water

    @property
    def recovered(self) -> bool:
        """True after a successful :meth:`recover` — required before sequencer open."""
        return self._recovered

    @property
    def is_distinct_from_journal_sequence(self) -> bool:
        """The command ordinal is never the CT-13 journal sequence object."""
        return True

    def recover(self, prior_high_water: object = 0) -> Result[int]:
        """Recover the durable high-water before the command sequencer opens.

        ``prior_high_water`` is the last persisted mark (0 for a brand-new stream).
        Failure to recover leaves the store unrecovered so sequencer open refuses.
        """
        if not isinstance(prior_high_water, int) or isinstance(prior_high_water, bool):
            self._recovered = False
            return _invalid(
                "prior_high_water",
                "ordinal high-water is a non-negative integer; a stream that cannot "
                "recover it refuses to open rather than restarting the count",
                given=repr(prior_high_water),
            )
        if prior_high_water < 0:
            self._recovered = False
            return _invalid(
                "prior_high_water",
                "ordinal high-water is a non-negative integer; a stream that cannot "
                "recover it refuses to open rather than restarting the count",
                given=prior_high_water,
            )
        self._high_water = prior_high_water
        # Prior high-water ordinals were already lived; treat them as submitted so
        # they cannot be re-presented after recovery.
        lived = set(range(1, prior_high_water + 1))
        self._issued = set(lived)
        self._submitted = set(lived)
        self._recovered = True
        return Ok(self._high_water)

    def require_recovered_for_sequencer(self) -> Result[bool]:
        """Gate sequencer open on a recovered ordinal high-water (DEC-0224)."""
        if not self._recovered:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": "command_ordinal",
                    "reason": "command ordinal high-water must be recovered before "
                    "opening the sequencer; refuse rather than restart the count",
                    "venue_id": self._venue_id.value,
                    "account_id": self._account.account_id,
                },
                after_condition_descriptor="recover command-ordinal high-water",
            )
        return Ok(True)

    def allocate(self) -> Result[int]:
        """Allocate the next lifetime-monotone ordinal and persist the high-water.

        Ordinal reuse is refused. An unpersistable high-water write blocks
        submission — the in-memory counter does not advance (DEC-0224).
        """
        recovered = self.require_recovered_for_sequencer()
        if is_refusal(recovered):
            return recovered
        next_ordinal = self._high_water + 1
        if next_ordinal in self._issued:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "ordering_ordinal",
                    "reason": "command ordinal reuse is refused; ordinals are "
                    "lifetime-monotone and never reused on a stream",
                    "ordinal": next_ordinal,
                    "venue_id": self._venue_id.value,
                    "account_id": self._account.account_id,
                },
            )
        record = CommandOrdinalHighWater(
            venue_id=self._venue_id.value,
            account_id=self._account.account_id,
            high_water=next_ordinal,
        )
        persisted = self._record_sink.write(record.as_mapping())
        if is_refusal(persisted):
            return persisted
        self._high_water = next_ordinal
        self._issued.add(next_ordinal)
        return Ok(next_ordinal)

    def was_issued(self, ordinal: object) -> bool:
        """True when ``ordinal`` was allocated from this recovered store."""
        return (
            isinstance(ordinal, int)
            and not isinstance(ordinal, bool)
            and ordinal in self._issued
        )

    def mark_submitted(self, ordinal: object) -> Result[bool]:
        """Consume an allocated ordinal at first submission; reuse is refused."""
        if not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 0:
            return _invalid(
                "ordering_ordinal",
                "a command ordinal is a non-negative integer",
                given=repr(ordinal),
            )
        if ordinal not in self._issued:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "ordering_ordinal",
                    "reason": "command ordinal must be allocated before submission",
                    "ordinal": ordinal,
                    "high_water": self._high_water,
                },
            )
        if ordinal in self._submitted:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "ordering_ordinal",
                    "reason": "command ordinal reuse is refused; ordinals are "
                    "lifetime-monotone and never reused on a stream",
                    "ordinal": ordinal,
                    "high_water": self._high_water,
                },
            )
        self._submitted.add(ordinal)
        return Ok(True)

    def refuse_reuse(self, ordinal: object) -> Result[bool]:
        """Refuse presenting an already-submitted or historically lived ordinal."""
        if not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 0:
            return _invalid(
                "ordering_ordinal",
                "a command ordinal is a non-negative integer",
                given=repr(ordinal),
            )
        if ordinal in self._submitted:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "ordering_ordinal",
                    "reason": "command ordinal reuse is refused; ordinals are "
                    "lifetime-monotone and never reused on a stream",
                    "ordinal": ordinal,
                    "high_water": self._high_water,
                },
            )
        return Ok(True)
