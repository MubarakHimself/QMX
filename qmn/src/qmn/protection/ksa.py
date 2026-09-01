"""Scoped KSA severity fold and operator-only ``resume`` (Story 26.1 / TN-7).

Five fixed levels ``GREEN | YELLOW | ORANGE | RED | BLACK`` and four addable
trigger classes ``scheduled_news | black_swan | connectivity | unknown_state``.
The level is a read-time fold per enforcement scope — global or
``(VenueId, account)`` — monotone non-decreasing within a level epoch.
``WriterId`` byte order and elapsed quiet time never lower severity. Only an
operator ``resume`` that names the exact scope and passes fresh-state
validation opens a new level epoch (DEC-0192, DEC-0237; FTR-07).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qmf.core import Instant, Ok, Result, VenueId, is_refusal

from qmn.protection._refuse import clean_token, invalid, policy

__all__ = [
    "AUTO_DEESCALATION_EVENTS",
    "KSA_LEVELS",
    "KSA_TRIGGER_CLASSES",
    "LEVEL_RANK",
    "OPERATOR_AUTHORITY",
    "PAPER_DISPOSITION_BY_TRIGGER",
    "KsaEnforcementScope",
    "KsaEscalationRecord",
    "KsaLevel",
    "KsaTriggerClass",
    "LevelEpoch",
    "PaperDisposition",
    "ResumeRecord",
    "effective_ksa_level",
    "fold_ksa_level",
    "ksa_levels",
    "ksa_trigger_classes",
    "mint_escalation",
    "mint_level_epoch",
    "paper_disposition_for",
    "resume",
    "scope_covers_stream",
    "stream_blocked_by_escalation",
]

OPERATOR_AUTHORITY: Final[str] = "operator"

# Events that never de-escalate on their own (DEC-0192 / DEC-0218).
AUTO_DEESCALATION_EVENTS: Final[frozenset[str]] = frozenset(
    {
        "reconnect",
        "reconciliation",
        "reconciled",
        "restart",
        "absence_of_triggers",
        "quiet_time",
        "trigger_cleared",
        "standing_intent_satisfied",
        "clocked_clear",
    }
)


class KsaLevel(StrEnum):
    """Fixed KSA severity levels — uneditable closed enum (DEC-0192)."""

    GREEN = "GREEN"
    YELLOW = "YELLOW"
    ORANGE = "ORANGE"
    RED = "RED"
    BLACK = "BLACK"


class KsaTriggerClass(StrEnum):
    """Addable-never-redefined KSA trigger classes (DEC-0192)."""

    SCHEDULED_NEWS = "scheduled_news"
    BLACK_SWAN = "black_swan"
    CONNECTIVITY = "connectivity"
    UNKNOWN_STATE = "unknown_state"


class PaperDisposition(StrEnum):
    """AD-35 paper disposition every trigger kind must declare (DEC-0192)."""

    ROUTES_TO_PAPER = "routes-to-paper"
    BLOCKS_PAPER = "blocks-paper"


# Severity ordinal — higher is more restrictive; fold takes the maximum.
LEVEL_RANK: Final[Mapping[KsaLevel, int]] = MappingProxyType(
    {
        KsaLevel.GREEN: 0,
        KsaLevel.YELLOW: 1,
        KsaLevel.ORANGE: 2,
        KsaLevel.RED: 3,
        KsaLevel.BLACK: 4,
    }
)

KSA_LEVELS: Final[tuple[KsaLevel, ...]] = (
    KsaLevel.GREEN,
    KsaLevel.YELLOW,
    KsaLevel.ORANGE,
    KsaLevel.RED,
    KsaLevel.BLACK,
)

KSA_TRIGGER_CLASSES: Final[tuple[KsaTriggerClass, ...]] = (
    KsaTriggerClass.SCHEDULED_NEWS,
    KsaTriggerClass.BLACK_SWAN,
    KsaTriggerClass.CONNECTIVITY,
    KsaTriggerClass.UNKNOWN_STATE,
)

# Market-risk KSA classes block paper; capital/authority routes live elsewhere.
PAPER_DISPOSITION_BY_TRIGGER: Final[Mapping[KsaTriggerClass, PaperDisposition]] = MappingProxyType(
    {
        KsaTriggerClass.SCHEDULED_NEWS: PaperDisposition.BLOCKS_PAPER,
        KsaTriggerClass.BLACK_SWAN: PaperDisposition.BLOCKS_PAPER,
        KsaTriggerClass.CONNECTIVITY: PaperDisposition.BLOCKS_PAPER,
        KsaTriggerClass.UNKNOWN_STATE: PaperDisposition.BLOCKS_PAPER,
    }
)


@dataclass(frozen=True, slots=True)
class KsaEnforcementScope:
    """V1 KSA enforcement scope: ``global`` or one ``(VenueId, account)`` stream.

    The scope is part of the level's identity and of its level epoch (DEC-0192).
    """

    kind: str
    venue_id: VenueId | None = None
    account_id: str | None = None

    @classmethod
    def global_scope(cls) -> KsaEnforcementScope:
        """The node-wide global enforcement scope."""
        return cls(kind="global")

    @classmethod
    def stream(cls, venue_id: object, account_id: object) -> Result[KsaEnforcementScope]:
        """Build a ``(VenueId, account)`` stream scope."""
        if not isinstance(venue_id, VenueId):
            return invalid(
                "venue_id",
                "a stream KSA scope is keyed by VenueId",
                given=repr(venue_id),
            )
        account = clean_token(account_id)
        if account is None:
            return invalid(
                "account_id",
                "a stream KSA scope is keyed by a non-empty account id",
                given=repr(account_id),
            )
        return Ok(cls(kind="stream", venue_id=venue_id, account_id=account))

    def token(self) -> str:
        """Opaque scope token used as fold / resume identity."""
        if self.kind == "global":
            return "global"
        venue = self.venue_id
        account = self.account_id
        if venue is None or account is None:
            return "stream:invalid"
        return f"stream:{venue.value}:{account}"

    def matches(self, other: KsaEnforcementScope) -> bool:
        """Exact scope identity — resume must name this, never widen silently."""
        return self.token() == other.token()


@dataclass(frozen=True, slots=True)
class LevelEpoch:
    """Monotone window of the KSA fold for one named scope (DEC-0192)."""

    epoch_id: str
    scope: KsaEnforcementScope
    opened_at: Instant
    opened_by: str

    def fp1_identity(self) -> dict[str, object]:
        """Pinned identity content for the level epoch."""
        return {
            "class": "ksa-level-epoch",
            "epoch_id": self.epoch_id,
            "scope": self.scope.token(),
            "opened_by": self.opened_by,
            "opened_at_ns": self.opened_at.value_ns,
        }


@dataclass(frozen=True, slots=True)
class KsaEscalationRecord:
    """One escalation observation folded into a level epoch (DEC-0192).

    Ordering across writers uses ``arbitration_rank`` (AD-37), never
    ``writer_id`` byte order. Quiet elapsed time is evidence only.
    """

    level: KsaLevel
    trigger_class: KsaTriggerClass
    scope: KsaEnforcementScope
    level_epoch_id: str
    issued_at: Instant
    writer_id: str
    arbitration_rank: int
    quiet_elapsed_ns: int = 0


@dataclass(frozen=True, slots=True)
class ResumeRecord:
    """Operator ``resume`` that opens a new level epoch at a named scope."""

    scope: KsaEnforcementScope
    authority: str
    issued_at: Instant
    prior_epoch_id: str
    new_epoch: LevelEpoch
    fresh_state_validated: bool


def ksa_levels() -> tuple[KsaLevel, ...]:
    """The fixed five-level vocabulary."""
    return KSA_LEVELS


def ksa_trigger_classes() -> tuple[KsaTriggerClass, ...]:
    """The four V1 trigger classes (extensions are addable, never redefined)."""
    return KSA_TRIGGER_CLASSES


def paper_disposition_for(trigger_class: object) -> Result[PaperDisposition]:
    """Return the fixed AD-35 disposition for a registered KSA trigger class."""
    resolved = _coerce_trigger(trigger_class)
    if is_refusal(resolved):
        return resolved
    return Ok(PAPER_DISPOSITION_BY_TRIGGER[resolved.value])


def mint_level_epoch(
    *,
    epoch_id: object,
    scope: object,
    opened_at: object,
    opened_by: object = "boot",
) -> Result[LevelEpoch]:
    """Open a level epoch at a named scope (boot or operator resume)."""
    eid = clean_token(epoch_id)
    if eid is None:
        return invalid(
            "epoch_id",
            "a level epoch carries a non-empty epoch_id",
            given=repr(epoch_id),
        )
    if not isinstance(scope, KsaEnforcementScope):
        return invalid(
            "scope",
            "a level epoch is qualified by a KsaEnforcementScope",
            given=repr(scope),
        )
    if not isinstance(opened_at, Instant):
        return invalid(
            "opened_at",
            "a level epoch is dated with an injected Instant",
            given=repr(opened_at),
        )
    by = clean_token(opened_by)
    if by is None:
        return invalid("opened_by", "opened_by is a non-empty token", given=repr(opened_by))
    return Ok(LevelEpoch(epoch_id=eid, scope=scope, opened_at=opened_at, opened_by=by))


def mint_escalation(
    *,
    level: object,
    trigger_class: object,
    scope: object,
    level_epoch_id: object,
    issued_at: object,
    writer_id: object,
    arbitration_rank: object,
    quiet_elapsed_ns: object = 0,
) -> Result[KsaEscalationRecord]:
    """Validate and mint one escalation record for the KSA fold."""
    resolved_level = _coerce_level(level)
    if is_refusal(resolved_level):
        return resolved_level
    resolved_trigger = _coerce_trigger(trigger_class)
    if is_refusal(resolved_trigger):
        return resolved_trigger
    if not isinstance(scope, KsaEnforcementScope):
        return invalid(
            "scope",
            "an escalation names a KsaEnforcementScope",
            given=repr(scope),
        )
    epoch = clean_token(level_epoch_id)
    if epoch is None:
        return invalid(
            "level_epoch_id",
            "an escalation binds to a non-empty level epoch id",
            given=repr(level_epoch_id),
        )
    if not isinstance(issued_at, Instant):
        return invalid(
            "issued_at",
            "an escalation is dated with an injected Instant",
            given=repr(issued_at),
        )
    writer = clean_token(writer_id)
    if writer is None:
        return invalid("writer_id", "an escalation carries a WriterId token", given=repr(writer_id))
    if isinstance(arbitration_rank, bool) or not isinstance(arbitration_rank, int):
        return invalid(
            "arbitration_rank",
            "equal-instant disposition uses an AD-37 integer rank, never WriterId order",
            given=repr(arbitration_rank),
        )
    if (
        isinstance(quiet_elapsed_ns, bool)
        or not isinstance(quiet_elapsed_ns, int)
        or quiet_elapsed_ns < 0
    ):
        return invalid(
            "quiet_elapsed_ns",
            "quiet elapsed time is a non-negative int64 nanosecond count and never lowers severity",
            given=repr(quiet_elapsed_ns),
        )
    return Ok(
        KsaEscalationRecord(
            level=resolved_level.value,
            trigger_class=resolved_trigger.value,
            scope=scope,
            level_epoch_id=epoch,
            issued_at=issued_at,
            writer_id=writer,
            arbitration_rank=arbitration_rank,
            quiet_elapsed_ns=quiet_elapsed_ns,
        )
    )


def fold_ksa_level(
    records: Sequence[object] | Iterable[object],
    *,
    scope: object,
    epoch: object,
) -> Result[KsaLevel]:
    """Monotone non-decreasing KSA fold within one level epoch at ``scope``.

    Takes the maximum severity over escalation records for this scope and epoch.
    ``WriterId`` lexicographic order and ``quiet_elapsed_ns`` never reduce the
    folded level. Records outside the named scope or epoch are ignored.
    """
    if not isinstance(scope, KsaEnforcementScope):
        return invalid("scope", "fold reads a KsaEnforcementScope", given=repr(scope))
    if not isinstance(epoch, LevelEpoch):
        return invalid("epoch", "fold reads a LevelEpoch", given=repr(epoch))
    if not epoch.scope.matches(scope):
        return invalid(
            "scope",
            "fold scope must match the level epoch's named scope",
            fold_scope=scope.token(),
            epoch_scope=epoch.scope.token(),
        )

    folded = KsaLevel.GREEN
    # Sort by (issued_at, arbitration_rank) — never writer_id — so equal-instant
    # disposition is rank-stable and WriterId byte order cannot lower severity.
    scoped = [
        record
        for record in records
        if isinstance(record, KsaEscalationRecord)
        and record.scope.matches(scope)
        and record.level_epoch_id == epoch.epoch_id
    ]
    scoped.sort(key=lambda r: (r.issued_at.value_ns, r.arbitration_rank, r.writer_id))
    for record in scoped:
        if LEVEL_RANK[record.level] > LEVEL_RANK[folded]:
            folded = record.level
        # Quiet time is ignored for severity — intentional no-op read.
        _ = record.quiet_elapsed_ns
    return Ok(folded)


def effective_ksa_level(
    *,
    global_level: object,
    stream_level: object,
) -> Result[KsaLevel]:
    """Most restrictive covering scope at a decision point (DEC-0192)."""
    g = _coerce_level(global_level)
    if is_refusal(g):
        return g
    s = _coerce_level(stream_level)
    if is_refusal(s):
        return s
    if LEVEL_RANK[g.value] >= LEVEL_RANK[s.value]:
        return Ok(g.value)
    return Ok(s.value)


def resume(
    *,
    scope: object,
    authority: object,
    issued_at: object,
    prior_epoch: object,
    new_epoch_id: object,
    fresh_state_validated: object,
) -> Result[ResumeRecord]:
    """Operator-only de-escalation: name exact scope, open a new level epoch.

    Reconnect, reconciliation, restart, or absence of triggers never call this
    path — those events are refused here when presented as authority (DEC-0192).
    """
    if not isinstance(scope, KsaEnforcementScope):
        return invalid(
            "scope",
            "resume must name an exact KsaEnforcementScope",
            given=repr(scope),
        )
    auth = clean_token(authority)
    if auth is None:
        return invalid("authority", "resume carries an issuing authority", given=repr(authority))
    if auth != OPERATOR_AUTHORITY:
        return policy(
            "authority",
            "resume is operator-only — escalation automates, de-escalation does not",
            authority=auth,
        )
    if auth in AUTO_DEESCALATION_EVENTS:
        return policy(
            "authority",
            "reconnect, reconciliation, restart, or absence of triggers never de-escalate",
            authority=auth,
        )
    if not isinstance(issued_at, Instant):
        return invalid(
            "issued_at",
            "resume is dated with an injected Instant",
            given=repr(issued_at),
        )
    if not isinstance(prior_epoch, LevelEpoch):
        return invalid(
            "prior_epoch",
            "resume closes a named prior level epoch",
            given=repr(prior_epoch),
        )
    if not prior_epoch.scope.matches(scope):
        return policy(
            "scope",
            "resume names the exact scope whose epoch it opens — never silently every scope",
            named_scope=scope.token(),
            prior_scope=prior_epoch.scope.token(),
        )
    if fresh_state_validated is not True:
        return policy(
            "fresh_state_validated",
            "resume opens a new level epoch only after fresh-state validation",
            given=repr(fresh_state_validated),
        )
    new_epoch = mint_level_epoch(
        epoch_id=new_epoch_id,
        scope=scope,
        opened_at=issued_at,
        opened_by="resume",
    )
    if is_refusal(new_epoch):
        return new_epoch
    return Ok(
        ResumeRecord(
            scope=scope,
            authority=auth,
            issued_at=issued_at,
            prior_epoch_id=prior_epoch.epoch_id,
            new_epoch=new_epoch.value,
            fresh_state_validated=True,
        )
    )


def scope_covers_stream(
    scope: KsaEnforcementScope,
    *,
    venue_id: VenueId,
    account_id: str,
) -> bool:
    """True when ``scope`` covers the named ``(VenueId, account)`` stream."""
    if scope.kind == "global":
        return True
    return (
        scope.venue_id is not None
        and scope.account_id is not None
        and scope.venue_id.value == venue_id.value
        and scope.account_id == account_id
    )


def stream_blocked_by_escalation(
    escalation_scope: KsaEnforcementScope,
    *,
    target_venue_id: VenueId,
    target_account_id: str,
    target_is_paired_demo: bool = False,
) -> bool:
    """Whether an escalation blocks ``target`` (DEC-0192 stream isolation).

    A live-stream connectivity / unknown_state escalation does **not** block the
    separate paired-demo stream unless the escalation scope is global. A global
    escalation blocks live and paper alike.
    """
    if escalation_scope.kind == "global":
        return True
    covers = scope_covers_stream(
        escalation_scope,
        venue_id=target_venue_id,
        account_id=target_account_id,
    )
    # Paired demo is a distinct (VenueId, account) stream — stream-scoped live
    # escalations never gate it unless they name that demo stream.
    if target_is_paired_demo and escalation_scope.kind == "stream" and not covers:
        return False
    return covers


def _coerce_level(value: object) -> Result[KsaLevel]:
    if isinstance(value, KsaLevel):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(KsaLevel(value))
        except ValueError:
            pass
    return invalid(
        "level",
        "KSA levels are exactly GREEN|YELLOW|ORANGE|RED|BLACK",
        given=repr(value),
        allowed=[level.value for level in KSA_LEVELS],
    )


def _coerce_trigger(value: object) -> Result[KsaTriggerClass]:
    if isinstance(value, KsaTriggerClass):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(KsaTriggerClass(value))
        except ValueError:
            pass
    return invalid(
        "trigger_class",
        "KSA trigger classes are scheduled_news|black_swan|connectivity|unknown_state "
        "(addable, never redefined)",
        given=repr(value),
        allowed=[trigger.value for trigger in KSA_TRIGGER_CLASSES],
    )
