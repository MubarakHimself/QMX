"""The UNKNOWN command-stream block and its explicit resolution (Story 8.7; CT-19).

`COMP-QMF-VENUE`'s uncertainty-blocking law on qmf-core nouns: while an ``UNKNOWN`` is
outstanding on a ``(VenueId, account)`` command stream, the adapter **refuses new
commands** on that stream and **never clears its own block** — the block clears only on
an explicit application ``resolve_unknown`` call, never on a reconciliation verdict alone
(CT-19, SCN-0005; DEC-0137, DEC-0148, DEC-0150, DEC-0158).

The law this module encodes:

* **An outstanding UNKNOWN blocks the whole stream** (:class:`UnknownGate`,
  :meth:`~UnknownGate.record_unknown`, :meth:`~UnknownGate.admit`). A submission that
  resolved to ``UNKNOWN`` is registered as outstanding on its ``(VenueId, account)``
  stream; while any is outstanding, a new command is refused with ``transient venue
  failure`` (after-condition = ``resolution``). The adapter never retries, assumes an
  outcome, flattens, or invents a terminal state, and never clears its own block (L35;
  DEC-0137).
* **A refused protection act never evaporates** (:class:`StandingProtectionIntent`,
  :meth:`~UnknownGate.redecide_standing_intent`). A refused **risk-reducing** command —
  ``cancel_order``, ``close_position``, ``close_all``, ``amend_protection`` — is preserved
  as a **standing protection intent**, journaled before dispatch, and **re-decided**
  (explicitly *not* retried) against a reconciled verdict only; ``drift``, ``unknown``,
  and ``out-of-lookback`` alarm and hold it open without dispatching, so a protection
  mechanism never opens a position against state it cannot see (DEC-0150, DEC-0158).
* **Risk-reducing kinds dispatch ahead of place_order on a shared throttle**
  (:func:`order_for_shared_throttle`, :func:`is_risk_reducing`), and **suspend-new takes
  local effect instantly** with no venue round-trip (:meth:`~UnknownGate.suspend_new`),
  refusing a new ``place_order`` while risk-reducing commands still flow (SCN-0005, CT-19).
* **Resolution is explicit and recorded** (:class:`ResolveResolution`,
  :class:`ResolveObservation`, :meth:`~UnknownGate.resolve_unknown`). ``resolve_unknown``
  carries the command identity and one of ``observed-accepted | observed-absent |
  operator-attested``; the call is itself recorded as an observation, and the block clears
  **on that resolution** — never on a reconciliation verdict alone (DEC-0137).

This module holds the **shape and the law**, never a broker fact or a policy value: no
retry, pool, throttle, or deadline constant lives here (retry is prohibited outright — a
standing intent is *re-decided*, never resubmitted). It reads no clock — every instant is
injected at the composition root (AR-16). It imports only ``qmf-core`` and the sibling
command/connection/event modules; nothing imports ``qmf-venue`` (default-deny,
L30/DEC-0120). No binary float touches the money path (DEC-0105). The gate is deliberately
**not** a frozen value: it owns the mutable per-stream block state, following
one-writer-per-stream (DEC-0113); every value it exposes is frozen and immutable
(DEC-0101, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, TypeVar, cast

from qmf.core import (
    Duration,
    Fingerprint,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)
from qmf.venue.commands import (
    Command,
    CommandKind,
    SubmissionOutcome,
    SubmissionResult,
    UnknownTrigger,
)
from qmf.venue.connection import ConnectionManager, venue_command_stream
from qmf.venue.events import Reconciliation, ReconciliationVerdict

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "RISK_REDUCING_KINDS",
    "AdmissionDisposition",
    "AdmissionResult",
    "ResolveObservation",
    "ResolveResolution",
    "StandingIntentDecision",
    "StandingIntentDisposition",
    "StandingIntentJournalEvent",
    "StandingProtectionIntent",
    "StreamBlockCause",
    "UnknownBlock",
    "UnknownGate",
    "is_risk_reducing",
    "order_for_shared_throttle",
    "throttle_priority",
]

# Every serialized artifact this module stamps carries the CT-19 contract format version;
# its meaning never mutates — an incompatible change mints the next version (DEC-0103;
# versioning-from-birth L15). CT-19 is at format version 1.
CONTRACT_FORMAT_VERSION: Final[int] = 1

# The after-condition an UNKNOWN block carries: it clears only on an explicit application
# resolve_unknown call, never on a reconciliation verdict alone (DEC-0137). Stated at its
# point of use, not a registry value.
_RESOLUTION_AFTER_CONDITION: Final[str] = "resolution"

# The after-condition a suspend-new refusal carries: a new order is refused until the
# adapter_self suspend-new state is lifted. suspend-new is a local, instant control with no
# venue round-trip (DEC-0137, DEC-0150).
_SUSPEND_NEW_AFTER_CONDITION: Final[str] = "suspend-new lifted"

_EnumT = TypeVar("_EnumT", bound=StrEnum)


# --- the risk-reducing throttle ordering ------------------------------------


# The four risk-reducing command kinds — the ones that reduce or close exposure. They
# dispatch ahead of place_order on every shared throttle and, once refused by a block, are
# preserved as standing protection intents (DEC-0148, DEC-0150, DEC-0158).
RISK_REDUCING_KINDS: Final[frozenset[CommandKind]] = frozenset(
    {
        CommandKind.CANCEL_ORDER,
        CommandKind.CLOSE_POSITION,
        CommandKind.CLOSE_ALL,
        CommandKind.AMEND_PROTECTION,
    }
)

# The shared-throttle dispatch priority per command kind: a lower number dispatches first,
# so every risk-reducing kind (0) precedes place_order (1). A read-only mapping over the
# closed five-kind vocabulary (DEC-0150, DEC-0158).
_THROTTLE_PRIORITY: Final[MappingProxyType[CommandKind, int]] = MappingProxyType(
    {
        CommandKind.CANCEL_ORDER: 0,
        CommandKind.CLOSE_POSITION: 0,
        CommandKind.CLOSE_ALL: 0,
        CommandKind.AMEND_PROTECTION: 0,
        CommandKind.PLACE_ORDER: 1,
    }
)


def is_risk_reducing(kind: object) -> bool:
    """Whether ``kind`` is a risk-reducing command kind (CT-19; DEC-0150, DEC-0158).

    A safe read: only the four risk-reducing kinds return ``True``; ``place_order`` and any
    non-kind return ``False``. The risk-reducing kinds dispatch ahead of ``place_order`` on
    a shared throttle and are preserved as standing protection intents when refused by a
    block.
    """
    return isinstance(kind, CommandKind) and kind in RISK_REDUCING_KINDS


def throttle_priority(kind: object) -> int:
    """The shared-throttle dispatch priority of a command kind (CT-19; DEC-0150).

    ``0`` for a risk-reducing kind (dispatches first), ``1`` for ``place_order``, and ``1``
    (last) for any value outside the closed kind vocabulary — so an unknown value never
    jumps ahead of a risk-reducing act.
    """
    if not isinstance(kind, CommandKind):
        return 1
    return _THROTTLE_PRIORITY[kind]


def order_for_shared_throttle(commands: object) -> Result[tuple[Command, ...]]:
    """Order commands sharing one throttle, risk-reducing kinds first (CT-19; DEC-0150).

    Given a sequence of commands contending for one shared throttle (CT-18 declares the
    throttle scope: connection | account | binding), returns them ordered so every
    risk-reducing kind — ``cancel_order``, ``close_position``, ``close_all``,
    ``amend_protection`` — dispatches **ahead of** ``place_order``, preserving the caller's
    original order within each priority class (a stable ordering). An empty sequence orders
    to an empty tuple; a non-sequence or a non-:class:`~qmf.venue.commands.Command` element
    is an ``invalid input`` refusal.
    """
    if isinstance(commands, (str, bytes)) or not isinstance(commands, Sequence):
        return _invalid(
            "commands",
            "a shared-throttle ordering reads a sequence of typed Commands",
            given=repr(commands),
        )
    resolved: list[Command] = []
    for index, item in enumerate(cast("Sequence[object]", commands)):
        if not isinstance(item, Command):
            return _invalid(
                "commands",
                "each pending command sharing a throttle is a typed Command",
                index=index,
                given=repr(item),
            )
        resolved.append(item)
    ordered = sorted(resolved, key=lambda command: throttle_priority(command.kind))
    return Ok(tuple(ordered))


# --- refusal builders -------------------------------------------------------


def _invalid(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a malformed call returns (CT-04; DEC-0109)."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _blocked_unknown(kind: CommandKind, command_fp1: Fingerprint) -> TypedRefusal:
    """Build the ``transient venue failure`` refusal a blocked command returns (CT-19).

    Carries the after-condition ``resolution`` — the block clears only on an explicit
    ``resolve_unknown`` call — and marks its cause. The adapter never clears its own block,
    retries, assumes an outcome, flattens, or invents a terminal state (DEC-0137).
    """
    return TypedRefusal(
        category=RefusalCategory.TRANSIENT_VENUE_FAILURE,
        retryability=Retryability.AFTER_CONDITION,
        context={
            "field": "command_stream",
            "reason": (
                "an UNKNOWN is outstanding on this (VenueId, account) command stream; new "
                "commands are refused until an explicit resolve_unknown call — the adapter "
                "never clears its own block, retries, assumes an outcome, flattens, or invents "
                "a terminal state"
            ),
            "command_fp1": command_fp1.value,
            "command_kind": kind.value,
            "block_cause": StreamBlockCause.OUTSTANDING_UNKNOWN.value,
        },
        after_condition_descriptor=_RESOLUTION_AFTER_CONDITION,
    )


def _blocked_suspend_new(command_fp1: Fingerprint) -> TypedRefusal:
    """Build the ``transient venue failure`` refusal a suspend-new place_order returns.

    ``suspend-new`` is a local, instant adapter_self control (no venue round-trip): while it
    is in effect a new ``place_order`` is refused with the after-condition ``suspend-new
    lifted`` while risk-reducing commands still dispatch (CT-19; DEC-0137, DEC-0150).
    """
    return TypedRefusal(
        category=RefusalCategory.TRANSIENT_VENUE_FAILURE,
        retryability=Retryability.AFTER_CONDITION,
        context={
            "field": "command_stream",
            "reason": (
                "suspend-new is in local effect; a new place_order is refused while "
                "risk-reducing commands still dispatch — suspend-new takes local effect "
                "instantly with no venue round-trip"
            ),
            "command_fp1": command_fp1.value,
            "command_kind": CommandKind.PLACE_ORDER.value,
            "block_cause": StreamBlockCause.SUSPEND_NEW.value,
        },
        after_condition_descriptor=_SUSPEND_NEW_AFTER_CONDITION,
    )


def _coerce(enum_cls: type[_EnumT], value: object) -> _EnumT | None:
    """Return the enum member ``value`` names, or ``None`` if it names none."""
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            return None
    return None


# --- vocabulary -------------------------------------------------------------


class ResolveResolution(StrEnum):
    """The resolution an application ``resolve_unknown`` call carries (CT-19; DEC-0137).

    Exactly one of these three: the application observed the command accepted, observed it
    absent (never landed), or an operator attested the resolution. The block clears on this
    resolution — never on a reconciliation verdict alone.
    """

    OBSERVED_ACCEPTED = "observed-accepted"
    OBSERVED_ABSENT = "observed-absent"
    OPERATOR_ATTESTED = "operator-attested"


class StreamBlockCause(StrEnum):
    """Why a command was refused at the stream gate (CT-19; DEC-0137, DEC-0150).

    ``OUTSTANDING_UNKNOWN`` — an UNKNOWN is outstanding, so the whole stream is blocked (a
    protection command is not exempt but is preserved as a standing intent).
    ``SUSPEND_NEW`` — suspend-new is in local effect, refusing a new ``place_order`` only
    while risk-reducing commands still dispatch.
    """

    OUTSTANDING_UNKNOWN = "outstanding-unknown"
    SUSPEND_NEW = "suspend-new"


class AdmissionDisposition(StrEnum):
    """The disposition of a command at the stream gate (CT-19; DEC-0137, DEC-0150)."""

    ADMITTED = "admitted"
    REFUSED = "refused"
    HELD_AS_STANDING_INTENT = "held-as-standing-intent"


class StandingIntentDisposition(StrEnum):
    """The re-decision of a standing protection intent (CT-19; DEC-0150, DEC-0158).

    ``DISPATCH`` — re-decided against a ``reconciled`` verdict; the intent dispatches fresh
    (never a retry). ``HOLD_OPEN`` — the block has not cleared, or the verdict is ``drift``,
    ``unknown``, or ``out-of-lookback``; the intent alarms and holds open without
    dispatching, so protection never opens against state it cannot see.
    """

    DISPATCH = "dispatch"
    HOLD_OPEN = "hold-open"


# --- the outstanding-UNKNOWN block ------------------------------------------


@dataclass(frozen=True, slots=True)
class UnknownBlock:
    """One outstanding ``UNKNOWN`` registered on a command stream (CT-19; DEC-0137).

    Provenance for the block an UNKNOWN submission places on its ``(VenueId, account)``
    stream: the command identity, the transport ``trigger`` (``timeout | transport-error |
    disconnect``), the monotonic elapsed measurement, the wall receive instant, and the
    injected submission deadline in force — whose existence is mandatory but whose value is
    never QMF's. It is occurrence/provenance only and exposes no ``fp1_identity``. The block
    clears only on an explicit ``resolve_unknown`` call (``after_condition = resolution``).
    """

    command_fp1: Fingerprint
    kind: CommandKind
    trigger: UnknownTrigger
    receive_instant: Instant
    monotonic_elapsed: Duration
    submission_deadline: Instant
    after_condition: str = _RESOLUTION_AFTER_CONDITION


# --- the standing protection intent -----------------------------------------


@dataclass(frozen=True, slots=True)
class StandingIntentJournalEvent:
    """The journal event minted when a refused protection act is held (CT-13, CT-20).

    A refused risk-reducing act is journaled **before dispatch** so it never evaporates; the
    ``event_type`` is the deterministic held marker keyed to the command identity and kind
    (DEC-0150, DEC-0158).
    """

    command_fp1: Fingerprint
    kind: CommandKind
    event_type: str

    @classmethod
    def held(cls, command_fp1: Fingerprint, kind: CommandKind) -> StandingIntentJournalEvent:
        """Mint the held journal event for a standing protection intent (one per hold)."""
        return cls(
            command_fp1=command_fp1,
            kind=kind,
            event_type=f"command.standing-protection-intent.held.{kind.value}",
        )


@dataclass(frozen=True, slots=True)
class StandingProtectionIntent:
    """A refused protection act preserved for re-decision, never a retry (CT-19; DEC-0150).

    A risk-reducing command the block refused is preserved as this standing intent —
    journaled before dispatch (``journal_event``), holding the original ``command`` so a
    later re-decision dispatches a **freshly-decided** act, never a resubmission. It is
    re-decided against a ``reconciled`` verdict only; ``drift``, ``unknown``, and
    ``out-of-lookback`` alarm and hold it open without dispatching (DEC-0150, DEC-0158).
    """

    command: Command
    command_fp1: Fingerprint
    kind: CommandKind
    held_at: Instant
    journal_event: StandingIntentJournalEvent
    detail: str = ""


@dataclass(frozen=True, slots=True)
class StandingIntentDecision:
    """The re-decision of a standing protection intent against a verdict (CT-19; DEC-0158).

    ``disposition`` is ``dispatch`` only against a ``reconciled`` verdict once the block has
    cleared; otherwise ``hold-open`` with ``alarm`` raised. ``verdict`` is the reconciliation
    verdict the re-decision read — never a retry of the original command.
    """

    intent: StandingProtectionIntent
    disposition: StandingIntentDisposition
    verdict: ReconciliationVerdict
    alarm: bool
    detail: str

    @property
    def dispatches(self) -> bool:
        """Whether the intent dispatches (re-decided against a reconciled verdict)."""
        return self.disposition is StandingIntentDisposition.DISPATCH


# --- the resolve-unknown observation ----------------------------------------


@dataclass(frozen=True, slots=True)
class ResolveObservation:
    """The observation minted by an application ``resolve_unknown`` call (CT-19; DEC-0137).

    The ``resolve_unknown`` call is itself recorded as an observation carrying the command
    identity it resolves, the ``resolution`` (``observed-accepted | observed-absent |
    operator-attested``), and the mandatory wall receive instant. It is occurrence/provenance
    only and exposes no ``fp1_identity``: the block clears on this resolution, never on a
    reconciliation verdict alone.
    """

    command_fp1: Fingerprint
    kind: CommandKind
    resolution: ResolveResolution
    receive_instant: Instant
    detail: str = ""


# --- the admission result ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    """The disposition of one command at the stream gate (CT-19; DEC-0137, DEC-0150).

    ``disposition`` is ``admitted`` (dispatch may proceed), ``refused`` (a new command
    refused by the block or by suspend-new — ``refusal`` carries the typed
    ``transient venue failure``), or ``held-as-standing-intent`` (a refused protection act
    preserved as ``standing_intent`` and still carrying its ``refusal`` for the current
    submission). ``block_cause`` names why a refused/held command was not admitted.
    """

    disposition: AdmissionDisposition
    command_fp1: Fingerprint
    kind: CommandKind
    block_cause: StreamBlockCause | None
    refusal: TypedRefusal | None
    standing_intent: StandingProtectionIntent | None
    detail: str

    @property
    def admitted(self) -> bool:
        """Whether the command was admitted for dispatch."""
        return self.disposition is AdmissionDisposition.ADMITTED


# --- the stream gate --------------------------------------------------------


class UnknownGate:
    """The per-(VenueId, account) UNKNOWN command-stream block gate (CT-19; DEC-0137).

    Constructed through :meth:`try_create` from the composition-root-wired
    :class:`~qmf.venue.connection.ConnectionManager` — the writer that holds the
    ``WriterId`` for this ``(VenueId, account)`` stream and sees every persistence failure.
    It tracks the outstanding ``UNKNOWN`` submissions on the stream, refuses new commands
    while any is outstanding (:meth:`admit`), preserves a refused protection act as a
    standing intent journaled before dispatch, and clears a block only on an explicit
    :meth:`resolve_unknown` call — never on a reconciliation verdict. It also owns the local
    ``suspend-new`` control and the risk-reducing shared-throttle ordering.

    Deliberately **not** a frozen value: it owns the mutable per-stream block state,
    following one-writer-per-stream (DEC-0113). The connection manager's own command-pipe
    block (storage/rotation failure) is a **separate** gate a dispatcher also honors via
    :meth:`~qmf.venue.connection.ConnectionManager.require_command_pipe_open`; this gate
    governs the UNKNOWN block and suspend-new only.
    """

    __slots__ = ("_cm", "_outstanding", "_standing_intents", "_stream", "_suspended_new")

    _cm: ConnectionManager
    _stream: str
    _outstanding: dict[str, UnknownBlock]
    _standing_intents: list[StandingProtectionIntent]
    _suspended_new: bool

    def __init__(self, connection_manager: ConnectionManager) -> None:
        # Unchecked trusted-internal constructor; callers use try_create.
        self._cm = connection_manager
        self._stream = connection_manager.writer_id.stream
        self._outstanding = {}
        self._standing_intents = []
        self._suspended_new = False

    @classmethod
    def try_create(cls, connection_manager: object) -> Result[UnknownGate]:
        """Validate the injected wiring and build an :class:`UnknownGate`.

        The gate journals standing intents and records ``resolve_unknown`` observations
        through the venue :class:`~qmf.venue.connection.ConnectionManager` (the ``WriterId``
        holder), so a mis-wired gate that silently holds no writer is refused.
        """
        if not isinstance(connection_manager, ConnectionManager):
            return _invalid(
                "connection_manager",
                "the gate writes through the venue ConnectionManager (the WriterId holder)",
                given=repr(connection_manager),
            )
        return Ok(cls(connection_manager))

    # -- identity and state --------------------------------------------------

    @property
    def stream(self) -> str:
        """The ``(VenueId, account)`` command-stream token this gate governs."""
        return self._stream

    @property
    def stream_open(self) -> bool:
        """Whether the command stream is open — no ``UNKNOWN`` is outstanding.

        suspend-new does not close the whole stream; it refuses a new ``place_order`` only
        while risk-reducing commands still dispatch, so the stream stays open here.
        """
        return len(self._outstanding) == 0

    @property
    def outstanding_count(self) -> int:
        """How many ``UNKNOWN`` submissions are outstanding on the stream."""
        return len(self._outstanding)

    @property
    def outstanding(self) -> tuple[UnknownBlock, ...]:
        """The outstanding ``UNKNOWN`` blocks on the stream (a safe, immutable read)."""
        return tuple(self._outstanding.values())

    @property
    def standing_intents(self) -> tuple[StandingProtectionIntent, ...]:
        """The standing protection intents held on the stream (a safe, immutable read)."""
        return tuple(self._standing_intents)

    @property
    def is_new_suspended(self) -> bool:
        """Whether suspend-new is in local effect (a new ``place_order`` is refused)."""
        return self._suspended_new

    def require_stream_open(self) -> Result[bool]:
        """The gate a dispatcher reads before submitting (CT-19; DEC-0137).

        Returns ``Ok(True)`` when no ``UNKNOWN`` is outstanding, or the outstanding block's
        typed ``transient venue failure`` refusal (after-condition = ``resolution``) —
        surfaced, never swallowed — so no command is dispatched while an ``UNKNOWN`` stands
        unresolved. This is the coarse whole-stream gate; :meth:`admit` is the per-command
        gate that also preserves a refused protection act.
        """
        if not self._outstanding:
            return Ok(True)
        block = next(iter(self._outstanding.values()))
        return _blocked_unknown(block.kind, block.command_fp1)

    # -- recording an outstanding UNKNOWN ------------------------------------

    def record_unknown(self, submission_result: object) -> Result[UnknownBlock]:
        """Register a submission that resolved ``UNKNOWN`` as outstanding on the stream.

        The result must be a genuine ``UNKNOWN`` :class:`~qmf.venue.commands.SubmissionResult`
        whose observation carries the mandatory UNKNOWN fields — its trigger, the monotonic
        elapsed measurement, the wall receive instant, and the submission deadline in force
        (whose existence is mandatory but whose value is never QMF's). Re-recording the same
        command's UNKNOWN is idempotent. The observation itself is minted and recorded on the
        submission path (CT-19/CT-20); this only tracks the block (DEC-0137).
        """
        if not isinstance(submission_result, SubmissionResult):
            return _invalid(
                "submission_result",
                "an outstanding block is recorded from a typed SubmissionResult",
                given=repr(submission_result),
            )
        if submission_result.outcome is not SubmissionOutcome.UNKNOWN:
            return _invalid(
                "submission_result",
                "only an UNKNOWN submission blocks the command stream; a resolved outcome does not",
                outcome=submission_result.outcome.value,
            )
        observation = submission_result.observation
        if observation.unknown_trigger is None:
            return _invalid(
                "submission_result",
                "an UNKNOWN observation carries its trigger "
                "(timeout | transport-error | disconnect)",
            )
        if observation.monotonic_elapsed is None:
            return _invalid(
                "submission_result",
                "an UNKNOWN observation carries the monotonic elapsed measurement",
            )
        if observation.submission_deadline is None:
            return _invalid(
                "submission_result",
                "an UNKNOWN observation carries the injected submission deadline in force — its "
                "existence is mandatory though its value is never QMF's",
            )
        key = submission_result.command_fp1.value
        existing = self._outstanding.get(key)
        if existing is not None:
            # Re-recording the same command's UNKNOWN is idempotent; the block is unchanged.
            return Ok(existing)
        block = UnknownBlock(
            command_fp1=submission_result.command_fp1,
            kind=submission_result.kind,
            trigger=observation.unknown_trigger,
            receive_instant=observation.receive_instant,
            monotonic_elapsed=observation.monotonic_elapsed,
            submission_deadline=observation.submission_deadline,
        )
        self._outstanding[key] = block
        return Ok(block)

    # -- admitting a new command ---------------------------------------------

    def admit(self, command: object, *, receive_instant: object) -> Result[AdmissionResult]:
        """Decide one command's disposition at the stream gate (CT-19; DEC-0137, DEC-0150).

        While an ``UNKNOWN`` is outstanding the whole stream is blocked: a **risk-reducing**
        command (``cancel_order``, ``close_position``, ``close_all``, ``amend_protection``)
        is refused **and preserved** as a standing protection intent journaled before
        dispatch (``held-as-standing-intent``); any other new command (``place_order``) is
        refused (``refused``) with a ``transient venue failure`` (after-condition =
        ``resolution``). With no ``UNKNOWN`` outstanding but suspend-new in local effect a new
        ``place_order`` is refused (``refused``, cause ``suspend-new``) while risk-reducing
        commands are admitted. Otherwise the command is ``admitted``. The command must run on
        this gate's own ``(VenueId, account)`` stream.
        """
        if not isinstance(command, Command):
            return _invalid("command", "the gate admits a typed Command", given=repr(command))
        if not isinstance(receive_instant, Instant):
            return _invalid(
                "receive_instant",
                "recording a wall receive instant is mandatory at the stream gate",
                given=repr(receive_instant),
            )
        if venue_command_stream(command.venue_id, command.account) != self._stream:
            return _invalid(
                "command",
                "the command runs on a different (VenueId, account) command stream than this gate",
                gate_stream=self._stream,
                command_stream=venue_command_stream(command.venue_id, command.account),
            )
        fp = command.fingerprint()
        if is_refusal(fp):  # pragma: no cover - a validly constructed command always fingerprints
            return fp
        command_fp1 = fp.value
        if self._outstanding:
            if is_risk_reducing(command.kind):
                return self._hold_as_standing_intent(command, command_fp1, receive_instant)
            return Ok(
                AdmissionResult(
                    disposition=AdmissionDisposition.REFUSED,
                    command_fp1=command_fp1,
                    kind=command.kind,
                    block_cause=StreamBlockCause.OUTSTANDING_UNKNOWN,
                    refusal=_blocked_unknown(command.kind, command_fp1),
                    standing_intent=None,
                    detail=(
                        "an UNKNOWN is outstanding; a new command is refused (transient venue "
                        "failure, after-condition = resolution) and not preserved"
                    ),
                )
            )
        if self._suspended_new and command.kind is CommandKind.PLACE_ORDER:
            return Ok(
                AdmissionResult(
                    disposition=AdmissionDisposition.REFUSED,
                    command_fp1=command_fp1,
                    kind=command.kind,
                    block_cause=StreamBlockCause.SUSPEND_NEW,
                    refusal=_blocked_suspend_new(command_fp1),
                    standing_intent=None,
                    detail="suspend-new is in local effect; a new place_order is refused",
                )
            )
        return Ok(
            AdmissionResult(
                disposition=AdmissionDisposition.ADMITTED,
                command_fp1=command_fp1,
                kind=command.kind,
                block_cause=None,
                refusal=None,
                standing_intent=None,
                detail="the stream is open; the command is admitted for dispatch",
            )
        )

    def _hold_as_standing_intent(
        self, command: Command, command_fp1: Fingerprint, held_at: Instant
    ) -> Result[AdmissionResult]:
        """Preserve a refused risk-reducing act as a standing intent (CT-19; DEC-0150).

        The refused protection act never evaporates: it is journaled **before dispatch**
        through the connection manager (a storage failure blocks the command stream and is
        surfaced, never swallowed — the intent is not preserved until it is journaled) and
        then held for re-decision against a reconciled verdict. The command is still refused
        now (``transient venue failure``, after-condition = ``resolution``).
        """
        journal_event = StandingIntentJournalEvent.held(command_fp1, command.kind)
        appended = self._cm.append_command_journal(journal_event)
        if is_refusal(appended):
            # Journaling-before-dispatch failed (storage failure); the intent is not preserved
            # yet and the command stream is blocked. Surface the failure, never swallow it.
            return appended
        intent = StandingProtectionIntent(
            command=command,
            command_fp1=command_fp1,
            kind=command.kind,
            held_at=held_at,
            journal_event=journal_event,
            detail=(
                "a protection act the UNKNOWN block refused; it never evaporates — journaled "
                "before dispatch and re-decided (not retried) against a reconciled verdict only"
            ),
        )
        self._standing_intents.append(intent)
        return Ok(
            AdmissionResult(
                disposition=AdmissionDisposition.HELD_AS_STANDING_INTENT,
                command_fp1=command_fp1,
                kind=command.kind,
                block_cause=StreamBlockCause.OUTSTANDING_UNKNOWN,
                refusal=_blocked_unknown(command.kind, command_fp1),
                standing_intent=intent,
                detail=(
                    "an UNKNOWN is outstanding; the protection act is refused now but preserved "
                    "as a standing protection intent, journaled before dispatch"
                ),
            )
        )

    # -- suspend-new (local, instant) ----------------------------------------

    def suspend_new(self) -> Result[bool]:
        """Suspend new orders locally and instantly, with no venue round-trip (CT-19).

        ``suspend-new`` is an adapter_self control that takes **local effect instantly**: it
        flips a local flag synchronously — no venue call, no sink write — after which a new
        ``place_order`` is refused while risk-reducing commands still dispatch (DEC-0137,
        DEC-0150).
        """
        self._suspended_new = True
        return Ok(True)

    def resume_new(self) -> Result[bool]:
        """Lift the local suspend-new state, re-admitting new ``place_order`` commands.

        The mirror of :meth:`suspend_new`: a local, instant flag change with no venue
        round-trip. It does not touch an outstanding ``UNKNOWN`` block — that clears only on
        :meth:`resolve_unknown`.
        """
        self._suspended_new = False
        return Ok(True)

    # -- resolving an UNKNOWN ------------------------------------------------

    def resolve_unknown(
        self, command_fp1: object, resolution: object, *, receive_instant: object
    ) -> Result[ResolveObservation]:
        """Clear one command's ``UNKNOWN`` block on an explicit resolution (CT-19; DEC-0137).

        Unblocking is an explicit typed call by the application: it names the command identity
        and a ``resolution`` (``observed-accepted | observed-absent | operator-attested``),
        the call is **itself recorded as an observation** through the connection manager, and
        the block clears **on that resolution** — never on a reconciliation verdict alone. A
        storage failure recording the observation is surfaced and the block is **kept** (the
        resolution must be recorded before the block clears); an identity with no outstanding
        ``UNKNOWN`` is an ``invalid input`` refusal.
        """
        if not isinstance(command_fp1, Fingerprint):
            return _invalid(
                "command_fp1",
                "resolve_unknown names the command identity as its fp1 fingerprint",
                given=repr(command_fp1),
            )
        resolved = _coerce(ResolveResolution, resolution)
        if resolved is None:
            return _invalid(
                "resolution",
                "a resolution is one of observed-accepted | observed-absent | operator-attested",
                given=repr(resolution),
                allowed=[member.value for member in ResolveResolution],
            )
        if not isinstance(receive_instant, Instant):
            return _invalid(
                "receive_instant",
                "recording a wall receive instant is mandatory on the resolve_unknown observation",
                given=repr(receive_instant),
            )
        key = command_fp1.value
        block = self._outstanding.get(key)
        if block is None:
            return _invalid(
                "command_fp1",
                "no outstanding UNKNOWN for this command identity on the stream; a block clears "
                "on resolution, never on a reconciliation verdict alone",
                command_fp1=command_fp1.value,
            )
        observation = ResolveObservation(
            command_fp1=command_fp1,
            kind=block.kind,
            resolution=resolved,
            receive_instant=receive_instant,
            detail=(
                "an explicit application resolve_unknown call, itself recorded as an observation; "
                "the block clears on this resolution"
            ),
        )
        emitted = self._cm.emit_command_observation(observation)
        if is_refusal(emitted):
            # The resolution must be recorded before the block clears; a storage failure blocks
            # the command stream and the UNKNOWN block is kept. Surface, never swallow.
            return emitted
        del self._outstanding[key]
        return Ok(observation)

    # -- re-deciding a standing protection intent ----------------------------

    def redecide_standing_intent(
        self, intent: object, reconciliation: object
    ) -> Result[StandingIntentDecision]:
        """Re-decide a standing protection intent against a verdict (CT-19; DEC-0158).

        The intent is **re-decided, explicitly not retried**: only once the ``UNKNOWN`` block
        has cleared and the reconciliation verdict is ``reconciled`` does it dispatch (a fresh
        act, never a resubmission), and it is then dropped from the standing set. While the
        block stands, or when the verdict is ``drift``, ``unknown``, or ``out-of-lookback``,
        the intent **alarms and holds open without dispatching** — protection never opens a
        position against state it cannot see. The intent must be one currently held here.
        """
        if not isinstance(intent, StandingProtectionIntent):
            return _invalid(
                "intent",
                "a re-decision reads a StandingProtectionIntent held on this stream",
                given=repr(intent),
            )
        if not isinstance(reconciliation, Reconciliation):
            return _invalid(
                "reconciliation",
                "a standing intent is re-decided against a Reconciliation verdict",
                given=repr(reconciliation),
            )
        if not self._holds_intent(intent.command_fp1):
            return _invalid(
                "intent",
                "not a standing protection intent held on this stream",
                command_fp1=intent.command_fp1.value,
            )
        if self._outstanding:
            return Ok(
                StandingIntentDecision(
                    intent=intent,
                    disposition=StandingIntentDisposition.HOLD_OPEN,
                    verdict=reconciliation.verdict,
                    alarm=True,
                    detail=(
                        "the UNKNOWN block has not cleared; the standing protection intent holds "
                        "open without dispatching until an explicit resolve_unknown clears it"
                    ),
                )
            )
        if reconciliation.standing_intent_may_dispatch:
            self._drop_intent(intent.command_fp1)
            return Ok(
                StandingIntentDecision(
                    intent=intent,
                    disposition=StandingIntentDisposition.DISPATCH,
                    verdict=reconciliation.verdict,
                    alarm=False,
                    detail=(
                        "re-decided against a reconciled verdict; the protection act dispatches "
                        "fresh — a re-decision, explicitly never a retry"
                    ),
                )
            )
        return Ok(
            StandingIntentDecision(
                intent=intent,
                disposition=StandingIntentDisposition.HOLD_OPEN,
                verdict=reconciliation.verdict,
                alarm=True,
                detail=(
                    "a drift, unknown, or out-of-lookback verdict alarms and holds the intent "
                    "open without dispatching; protection never opens against state it cannot see"
                ),
            )
        )

    def _holds_intent(self, command_fp1: Fingerprint) -> bool:
        """Whether a standing intent for ``command_fp1`` is currently held."""
        return any(held.command_fp1.value == command_fp1.value for held in self._standing_intents)

    def _drop_intent(self, command_fp1: Fingerprint) -> None:
        """Drop the standing intent for ``command_fp1`` (re-decided to dispatch)."""
        self._standing_intents = [
            held for held in self._standing_intents if held.command_fp1.value != command_fp1.value
        ]

    def __repr__(self) -> str:
        return (
            f"UnknownGate(stream={self._stream!r}, outstanding={len(self._outstanding)}, "
            f"standing_intents={len(self._standing_intents)}, "
            f"suspended_new={self._suspended_new})"
        )
