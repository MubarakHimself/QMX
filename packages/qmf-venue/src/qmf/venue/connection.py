"""The connection manager, the secret lifecycle, and injected-sink wiring (Story 8.3).

`COMP-QMF-VENUE`'s stateful heart: the connection manager is the sole owner of venue
sessions and the single named component permitted to hold secret *values* in memory,
for a session's lifetime, through a composition-root-injected :class:`~qmf.core.SecretStore`
port (read + atomic replace). It holds the venue-path ``WriterId`` — minted at the
``(machine, adapter role, VenueId, account)`` granularity, the same unit as the command
stream — and it calls the injected core sink protocols
(:class:`~qmf.core.ObservationSink`, :class:`~qmf.core.JournalSink`,
:class:`~qmf.core.RecordSink`) **synchronously**, so the writer that holds the
``WriterId`` sees every persistence failure (CT-21, AR-37, AR-38, AR-47; DEC-0136,
DEC-0138).

The discipline this module encodes:

* **Credentials never leave, never render.** A :class:`~qmf.core.SecretValue` lives only
  inside the connection manager, in a private slot with no getter; no method returns a
  plaintext value or a :class:`~qmf.core.SecretValue`, and nothing a caller can read —
  a return value, a :meth:`~ConnectionManager.health` field, a refusal context, or the
  ``repr`` — carries anything but the opaque *reference id* (AR-37; DEC-0136).
* **Rotation is store-before-discard.** :meth:`~ConnectionManager.rotate_secret` stores
  the new secret through ``atomic_replace`` **before** the old is discarded; a failed
  store after rotation is an ``unavailable dependency`` alarm plus a command-pipe block
  (retryable ``after-condition`` = successful store or operator re-provision) and the old
  value is kept, never dropped (AR-38, CT-21; DEC-0136).
* **Block-on-unpersistable.** A ``storage failure`` from any command-path sink call
  blocks the command stream in this writer-holding component; the block clears when the
  store demonstrably recovers (a subsequent successful command-path write). The **sensing
  pipe is unaffected** by that block — sensing observations keep flowing (AR-47, FM-2;
  DEC-0138). No store is ever written directly: every persistence crosses an injected
  sink, so injecting one creates no dependency edge (default-deny, L30/DEC-0120).
* **A missing/expired/rejected credential** is an ``unavailable dependency`` refusal that
  carries the reference id and never the value; an :class:`AccountBinding`'s secret
  reference is occurrence/display-only and **excluded from fp1** (a credential is a
  deployment fact, never a market fact); a non-opaque reference is an ``invalid input``
  refusal (CT-21; DEC-0136).

Stdlib + qmf-core only. The connection manager is deliberately **not** a frozen value:
it owns an external resource (the venue session) and mutable pipe state, following
one-writer-per-stream with unlimited readers (DEC-0113). Every value type it exposes is
frozen and immutable (DEC-0101, DEC-0113). Nothing imports ``qmf-venue`` (L30/DEC-0120).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

from qmf.core import (
    Account,
    Fingerprint,
    Instant,
    JournalSink,
    ObservationSink,
    Ok,
    OrderingKey,
    RecordSink,
    RefusalCategory,
    Result,
    Retryability,
    SecretRef,
    SecretStore,
    SecretValue,
    SinkResult,
    TypedRefusal,
    VenueId,
    World,
    WriterId,
    WriterSequencer,
    fingerprint,
    is_refusal,
    is_unpersistable,
)

__all__ = [
    "AccountBinding",
    "BlockCause",
    "CommandPipeStatus",
    "ConnectionManager",
    "HealthReport",
    "PipeState",
    "venue_command_stream",
    "venue_writer_id",
]

# The separator that joins a VenueId and an AccountId into the command-stream token
# carried in a venue WriterId's ``stream`` slot. A stable internal join, not a registry
# value; both parts are opaque and never parsed, so the separator only has to be one that
# does not appear in an identity token by construction.
_STREAM_SEP: Final[str] = "::"

# The retry gate a rotation-store failure carries and the command-pipe block waits on: the
# store must succeed, or the operator must re-provision the credential. Stated at its point
# of use per CT-21's rotation invariant, not a registry value (DEC-0136).
_ROTATION_AFTER_CONDITION: Final[str] = "successful store or operator re-provision"


# --- refusal builders -------------------------------------------------------


def _invalid(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a construction or wiring guard returns.

    The offending *value* is never echoed for a secret; a caller passes a ``given`` only
    for non-secret fields (CT-04; DEC-0109).
    """
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _unavailable_credential(secret_ref: SecretRef, reason: str) -> TypedRefusal:
    """Build the ``unavailable dependency`` refusal a missing/expired/rejected credential
    returns — carrying the reference id, **never the value** (CT-21; DEC-0136)."""
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context={"field": "credential", "reason": reason, "secret_ref": secret_ref.value},
    )


def _rotation_store_failure(secret_ref: SecretRef) -> TypedRefusal:
    """Build the ``unavailable dependency`` alarm a failed store-after-rotation returns.

    Retryable ``after-condition`` — the retry gate is a successful store or an operator
    re-provision (AR-38, CT-21; DEC-0136) — carrying the reference id and never the value,
    and marked as an ``alarm`` so its caller raises one and blocks the command pipe.
    """
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.AFTER_CONDITION,
        context={
            "field": "rotation_store",
            "reason": "the new secret failed to store after rotation; the old material is "
            "kept undiscarded and the command pipe is blocked",
            "secret_ref": secret_ref.value,
            "alarm": True,
        },
        after_condition_descriptor=_ROTATION_AFTER_CONDITION,
    )


# --- the venue-path WriterId ------------------------------------------------


def venue_command_stream(venue_id: VenueId, account: Account) -> str:
    """The ``(VenueId, account)`` command-stream token a venue ``WriterId`` carries.

    The command stream — the unit of ``WriterId`` ownership and the gapless per-writer
    sequence — is the ``(VenueId, account)`` pair (DEC-0137). Both parts are opaque and
    stored verbatim; this join only names the pair, it never parses either token.
    """
    return f"{venue_id.value}{_STREAM_SEP}{account.account_id}"


def venue_writer_id(
    machine: object,
    adapter_role: object,
    venue_id: object,
    account: object,
    boot_epoch_id: object,
) -> Result[WriterId]:
    """Mint the venue-path ``WriterId`` at the ``(machine, adapter role, VenueId, account)``
    granularity, returning value-or-refusal (CT-21; DEC-0136, DEC-0138).

    The core :class:`~qmf.core.WriterId` is ``(machine, role, stream, boot_epoch_id)``; on
    the venue path ``role`` is the adapter role and ``stream`` is the ``(VenueId, account)``
    command-stream token, so a restart is visible through a new ``boot_epoch_id`` without
    changing the writer identity. The account must belong to the venue, or the writer would
    name a command stream that cannot exist (CT-03; DEC-0107).
    """
    if not isinstance(venue_id, VenueId) or venue_id.value.strip() == "":
        return _invalid("venue_id", "a venue writer targets a valid VenueId", given=repr(venue_id))
    if not isinstance(account, Account):
        return _invalid("account", "a venue writer targets a valid Account", given=repr(account))
    if account.venue != venue_id:
        return _invalid(
            "account",
            "the account does not belong to this venue; the (VenueId, account) command "
            "stream would name a binding that cannot exist",
            venue=venue_id.value,
            account_venue=account.venue.value,
        )
    return WriterId.try_create(
        machine, adapter_role, venue_command_stream(venue_id, account), boot_epoch_id
    )


# --- the account-binding record ---------------------------------------------


@dataclass(frozen=True, slots=True)
class AccountBinding:
    """A venue account binding whose identity excludes its secret reference (CT-21).

    Identity is ``(VenueId, AccountId, role, world)`` — the account already carries its
    single :class:`~qmf.core.AccountRole`, so the tuple is fully determined by the account
    plus the :class:`~qmf.core.World`. The ``secret_ref`` names the credential the binding
    uses; it is **occurrence/display-only and excluded from fp1** — a credential is a
    deployment fact, never a market fact — so :meth:`fp1_identity` deliberately omits it
    and two bindings that differ only by credential fingerprint identically (DEC-0136,
    DEC-0140).
    """

    venue_id: VenueId
    account: Account
    world: World
    secret_ref: SecretRef

    @classmethod
    def try_create(
        cls, venue_id: object, account: object, world: object, secret_ref: object
    ) -> Result[AccountBinding]:
        """Validate and build an :class:`AccountBinding`, returning value-or-refusal.

        A malformed venue, an account that does not belong to the venue, a world outside
        the fixed set, or a ``secret_ref`` that is not a bare opaque
        :class:`~qmf.core.SecretRef` each yields an ``invalid input`` refusal. A non-opaque
        reference is refused at :meth:`~qmf.core.SecretRef.try_create`; passing anything
        but a constructed reference here is likewise refused, so a binding can never fork
        identity on a malformed credential handle (CT-21; DEC-0136).
        """
        if not isinstance(venue_id, VenueId) or venue_id.value.strip() == "":
            return _invalid(
                "venue_id", "a binding is keyed by a valid VenueId", given=repr(venue_id)
            )
        if not isinstance(account, Account):
            return _invalid("account", "a binding is keyed by a valid Account", given=repr(account))
        if account.venue != venue_id:
            return _invalid(
                "account",
                "the account does not belong to this venue; the binding identity "
                "(VenueId, AccountId, role, world) would name a binding that cannot exist",
                venue=venue_id.value,
                account_venue=account.venue.value,
            )
        resolved_world = _coerce_world(world)
        if resolved_world is None:
            return _invalid(
                "world",
                "a binding's world is one of live | replay | simulated",
                given=repr(world),
                allowed=[member.value for member in World],
            )
        if not isinstance(secret_ref, SecretRef):
            return _invalid(
                "secret_ref",
                "a binding names its credential by a bare opaque SecretRef, never a value; "
                "a non-opaque reference is refused at construction",
            )
        validated_ref = SecretRef.try_create(secret_ref.value)
        if is_refusal(validated_ref):
            return _invalid(
                "secret_ref",
                "a binding names its credential by a construction-validated opaque SecretRef",
            )
        return Ok(
            cls(
                venue_id=venue_id,
                account=account,
                world=resolved_world,
                secret_ref=validated_ref.value,
            )
        )

    @property
    def command_stream(self) -> str:
        """The ``(VenueId, account)`` command-stream token this binding runs under."""
        return venue_command_stream(self.venue_id, self.account)

    def fp1_identity(self) -> Mapping[str, object]:
        """The binding's canonical fp1 identity content — ``(VenueId, AccountId, role,
        world)`` and **never** the secret reference (CT-05; DEC-0136, DEC-0140).

        The secret reference is occurrence/display-only, so it is omitted here: a credential
        never enters a market-fact fingerprint. Every value is a JSON-native string, so the
        canonical serializer resolves it directly.
        """
        return {
            "class": "account-binding",
            "venue_id": self.venue_id.value,
            "account_id": self.account.account_id,
            "role": self.account.role.value,
            "world": self.world.value,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """The binding's fp1 fingerprint over its identity, returning value-or-refusal.

        Excludes the secret reference by construction (see :meth:`fp1_identity`), so a
        rotated credential never changes a binding's identity.
        """
        return fingerprint(self)


# --- the command / sensing pipe state ---------------------------------------


class CommandPipeStatus(StrEnum):
    """Whether the command stream accepts dispatch or is blocked (AR-47; DEC-0138)."""

    OPEN = "open"
    BLOCKED = "blocked"


class BlockCause(StrEnum):
    """Why the command pipe is blocked — the after-condition a clear must satisfy.

    ``STORAGE_FAILURE`` clears when the store recovers (a subsequent successful
    command-path sink write); ``ROTATION_STORE_FAILURE`` clears only on a successful store
    or operator re-provision of the credential (AR-38, AR-47; DEC-0136, DEC-0138).
    """

    STORAGE_FAILURE = "storage-failure"
    ROTATION_STORE_FAILURE = "rotation-store-failure"


@dataclass(frozen=True, slots=True)
class PipeState:
    """An immutable snapshot of a command block: its cause and the refusal that set it.

    ``refusal`` is the typed refusal the writer saw — a sink's ``storage failure`` or the
    rotation-store ``unavailable dependency`` alarm — carrying context (a reference id,
    never a value). A ``None`` :class:`PipeState` means the command pipe is open.
    """

    cause: BlockCause
    refusal: TypedRefusal


@dataclass(frozen=True, slots=True)
class HealthReport:
    """The connection manager's typed health report — reference ids only, no values.

    Every field is safe to log, expose in a metric, or render: the ``held_secret_ref_ids``
    are opaque *references*, and no plaintext secret ever appears here — no getter, log
    line, refusal context, health field, or metric label carries a secret value (CT-21,
    AR-37; DEC-0136).
    """

    machine: str
    adapter_role: str
    command_stream: str
    boot_epoch_id: str
    command_pipe: CommandPipeStatus
    command_block_cause: BlockCause | None
    sensing_pipe: CommandPipeStatus
    open_session_count: int
    held_secret_ref_ids: tuple[str, ...]


# --- the connection manager -------------------------------------------------


class ConnectionManager:
    """The sole owner of venue sessions and the single in-memory holder of secret values.

    Constructed through :meth:`try_create` from the venue-path ``WriterId`` and the four
    composition-root-injected core seams (:class:`~qmf.core.SecretStore`,
    :class:`~qmf.core.ObservationSink`, :class:`~qmf.core.JournalSink`,
    :class:`~qmf.core.RecordSink`). It reads and rotates credentials through the store,
    holds each :class:`~qmf.core.SecretValue` in a private slot for the session's lifetime,
    and forwards every persistence to an injected sink — never a direct store write. A
    ``storage failure`` on the command path blocks the command stream; the sensing pipe is
    unaffected. Secret values never cross back out: no getter, log line, refusal context,
    health field, or metric label carries one (CT-21, AR-37, AR-38, AR-47; DEC-0136,
    DEC-0138).

    Deliberately not a frozen dataclass: it owns an external resource and mutable pipe
    state (DEC-0113). The private ``_secrets`` slot is the only place a secret value lives.
    """

    __slots__ = (
        "_block",
        "_journal_sink",
        "_observation_sink",
        "_record_sink",
        "_secret_store",
        "_secrets",
        "_sequencer",
        "_writer_id",
    )

    _writer_id: WriterId
    _secret_store: SecretStore
    _observation_sink: ObservationSink[object]
    _journal_sink: JournalSink[object]
    _record_sink: RecordSink[object]
    _secrets: dict[SecretRef, SecretValue]
    _block: PipeState | None
    _sequencer: WriterSequencer

    def __init__(
        self,
        writer_id: WriterId,
        secret_store: SecretStore,
        observation_sink: ObservationSink[object],
        journal_sink: JournalSink[object],
        record_sink: RecordSink[object],
    ) -> None:
        # Unchecked trusted-internal constructor; callers use try_create.
        self._writer_id = writer_id
        self._secret_store = secret_store
        self._observation_sink = observation_sink
        self._journal_sink = journal_sink
        self._record_sink = record_sink
        self._secrets = {}
        self._block = None
        self._sequencer = WriterSequencer(writer_id)

    @classmethod
    def try_create(
        cls,
        writer_id: object,
        secret_store: object,
        observation_sink: object,
        journal_sink: object,
        record_sink: object,
    ) -> Result[ConnectionManager]:
        """Validate the injected wiring and build a :class:`ConnectionManager`.

        The ``writer_id`` must be a venue-granularity :class:`~qmf.core.WriterId`, and each
        of the four seams must satisfy its core protocol. A missing or malformed seam is an
        ``invalid input`` refusal — the composition root wires real seams, and a mis-wired
        manager must never silently hold no store or sink (CT-21, AR-15; DEC-0138).
        """
        if not isinstance(writer_id, WriterId):
            return _invalid(
                "writer_id",
                "the connection manager holds a venue-path WriterId (machine, adapter role, "
                "VenueId, account)",
                given=repr(writer_id),
            )
        if not isinstance(secret_store, SecretStore):
            return _invalid(
                "secret_store",
                "the composition root injects a SecretStore port (read + atomic replace)",
                given=repr(secret_store),
            )
        if not isinstance(observation_sink, ObservationSink):
            return _invalid(
                "observation_sink",
                "the composition root injects an ObservationSink",
                given=repr(observation_sink),
            )
        if not isinstance(journal_sink, JournalSink):
            return _invalid(
                "journal_sink",
                "the composition root injects a JournalSink",
                given=repr(journal_sink),
            )
        if not isinstance(record_sink, RecordSink):
            return _invalid(
                "record_sink",
                "the composition root injects a RecordSink",
                given=repr(record_sink),
            )
        # isinstance narrows a generic protocol only to its Unknown-parameterized form;
        # the manager forwards arbitrary payloads, so it holds each sink at ``[object]``.
        return Ok(
            cls(
                writer_id,
                secret_store,
                cast("ObservationSink[object]", observation_sink),
                cast("JournalSink[object]", journal_sink),
                cast("RecordSink[object]", record_sink),
            )
        )

    # -- identity and pipe state ---------------------------------------------

    @property
    def writer_id(self) -> WriterId:
        """The venue-path ``WriterId`` this component holds (a safe, renderable value)."""
        return self._writer_id

    @property
    def command_pipe_open(self) -> bool:
        """Whether the command stream accepts dispatch (no outstanding block)."""
        return self._block is None

    @property
    def sensing_pipe_open(self) -> bool:
        """Whether the sensing stream is flowing. A command-pipe block never gates it — the
        sensing pipe is unaffected by a command-path storage failure (AR-47; DEC-0138)."""
        return True

    @property
    def command_block(self) -> PipeState | None:
        """The outstanding command block, or ``None`` when the command pipe is open. The
        block's refusal carries reference ids only, never a secret value."""
        return self._block

    def require_command_pipe_open(self) -> Result[bool]:
        """The gate a command dispatcher reads before submitting (AR-47; DEC-0138).

        Returns ``Ok(True)`` when the command pipe is open, or the outstanding block's typed
        refusal — surfaced, never swallowed — so no command is dispatched while a store
        failure or a rotation-store failure stands unresolved.
        """
        if self._block is None:
            return Ok(True)
        return self._block.refusal

    def next_command_key(self, instant: object) -> Result[OrderingKey]:
        """Mint the next command-stream :class:`~qmf.core.OrderingKey` for this writer.

        Stamps the venue ``WriterId`` and the strictly-increasing per-writer sequence onto
        a caller-supplied :class:`~qmf.core.Instant` (read through the injected clock at the
        composition root, never an ambient clock here). Ordering carries no causal meaning
        (CT-02; DEC-0106).
        """
        if not isinstance(instant, Instant):
            return _invalid(
                "instant", "an ordering key is stamped on an Instant", given=repr(instant)
            )
        return Ok(self._sequencer.mint(instant))

    # -- secret lifecycle ----------------------------------------------------

    def open_session(self, binding: object) -> Result[SecretRef]:
        """Open a session for ``binding``: read its credential and hold it in memory.

        Reads the credential through the injected :class:`~qmf.core.SecretStore`; a missing,
        expired, or rejected credential is an ``unavailable dependency`` refusal carrying the
        reference id, never the value. On success the :class:`~qmf.core.SecretValue` is held
        in the private slot for the session's lifetime and **only the reference** is returned
        — a secret value never crosses back out. The binding must run under this manager's own
        ``(VenueId, account)`` command stream (CT-21; DEC-0136).
        """
        if not isinstance(binding, AccountBinding):
            return _invalid("binding", "a session opens for an AccountBinding", given=repr(binding))
        if binding.command_stream != self._writer_id.stream:
            return _invalid(
                "binding",
                "the binding runs under a different (VenueId, account) command stream than "
                "this connection manager holds",
                writer_stream=self._writer_id.stream,
                binding_stream=binding.command_stream,
            )
        read = self._secret_store.read(binding.secret_ref)
        if is_refusal(read):
            return _unavailable_credential(
                binding.secret_ref,
                "the credential is missing, expired, or rejected at the secret store",
            )
        value = read.value
        if value.ref != binding.secret_ref:
            # Defense in depth: a store must return the value of the reference it was asked
            # for; a mismatch is a store contract violation, refused rather than trusted.
            return _unavailable_credential(
                binding.secret_ref,
                "the secret store returned a value for a different reference",
            )
        self._secrets[binding.secret_ref] = value
        return Ok(binding.secret_ref)

    def holds_secret(self, secret_ref: object) -> bool:
        """Whether a secret value for ``secret_ref`` is held in memory (a boolean, never the
        value). The safe query a health check or test reads — it exposes presence, not
        plaintext (AR-37; DEC-0136)."""
        return isinstance(secret_ref, SecretRef) and secret_ref in self._secrets

    def close_session(self, secret_ref: object) -> Result[SecretRef]:
        """Discard the held secret value for ``secret_ref``, ending its session.

        Removes the :class:`~qmf.core.SecretValue` from the private slot so it no longer
        lives in memory. Closing an unheld reference is an ``invalid input`` refusal naming
        the reference (never a value).
        """
        if not isinstance(secret_ref, SecretRef):
            return _invalid("secret_ref", "close_session takes a SecretRef", given=repr(secret_ref))
        if secret_ref not in self._secrets:
            return _invalid(
                "secret_ref",
                "no session is open for this reference",
                secret_ref=secret_ref.value,
            )
        del self._secrets[secret_ref]
        return Ok(secret_ref)

    def rotate_secret(self, binding: object, new_secret: object) -> Result[SecretRef]:
        """Rotate a credential store-before-discard, returning value-or-refusal (AR-38).

        The new secret is stored through ``atomic_replace`` **before** the old is discarded.
        On a successful store the held value is swapped to the new one, the old is discarded,
        and a standing ``rotation-store-failure`` command block clears (the after-condition
        is met). On a failed store the old value is **kept undiscarded**, an
        ``unavailable dependency`` alarm is returned, and the command pipe is blocked (retry
        gate = successful store or operator re-provision); the sensing pipe is unaffected.
        The new secret must be a :class:`~qmf.core.SecretValue` for the binding's own
        reference (CT-21; DEC-0136, DEC-0140).
        """
        if not isinstance(binding, AccountBinding):
            return _invalid("binding", "rotation targets an AccountBinding", given=repr(binding))
        if not isinstance(new_secret, SecretValue):
            # Report the presence/type only; a SecretValue never renders its plaintext, and
            # a non-SecretValue is a caller mistake named without echoing any value.
            return _invalid(
                "new_secret",
                "rotation stores a qmf-core SecretValue, never a bare plaintext",
                given=type(new_secret).__name__,
            )
        if new_secret.ref != binding.secret_ref:
            return _invalid(
                "new_secret",
                "the new secret's reference does not match the binding's credential reference",
                secret_ref=binding.secret_ref.value,
            )
        stored = self._secret_store.atomic_replace(binding.secret_ref, new_secret)
        if is_refusal(stored):
            # Store-before-discard: the store failed, so the old material is NOT discarded.
            alarm = _rotation_store_failure(binding.secret_ref)
            self._block = PipeState(cause=BlockCause.ROTATION_STORE_FAILURE, refusal=alarm)
            return alarm
        # Stored durably; now — and only now — the old value is discarded by overwrite.
        self._secrets[binding.secret_ref] = new_secret
        self._clear_block(BlockCause.ROTATION_STORE_FAILURE)
        return Ok(binding.secret_ref)

    # -- injected-sink wiring: the command path ------------------------------

    def emit_command_observation(self, observation: object) -> SinkResult:
        """Record a command-path observation through the injected ``ObservationSink``.

        Recording precedes interpretation (AR-47): the observation is persisted verbatim. A
        ``storage failure`` blocks the command stream in this writer-holding component and is
        surfaced, never swallowed; a successful write clears a standing storage-failure block
        (the store recovered). No store is ever written directly.
        """
        return self._settle_command_write(self._observation_sink.emit(observation))

    def append_command_journal(self, event: object) -> SinkResult:
        """Append a command-path event through the injected ``JournalSink`` (gapless
        per-(writer, boot-epoch)). A ``storage failure`` blocks the command stream and is
        surfaced, never a silent drop; a successful append clears a storage-failure block."""
        return self._settle_command_write(self._journal_sink.append(event))

    def write_command_record(self, record: object) -> SinkResult:
        """Write a command-path registry record through the injected ``RecordSink``. A
        ``storage failure`` blocks the command stream and is surfaced; a successful write
        clears a storage-failure block. The record is minted by the root and written only
        through this injected sink — never a direct store write (AR-47; DEC-0138)."""
        return self._settle_command_write(self._record_sink.write(record))

    def _settle_command_write(self, result: SinkResult) -> SinkResult:
        """Apply block-on-unpersistable to one command-path sink result (AR-47; FM-2).

        A ``storage failure`` sets (or refreshes) a storage-failure command block; any other
        successful write demonstrates the store recovered and clears a standing storage-failure
        block. A rotation-store block is untouched here — only a successful store or operator
        re-provision clears that one. The result is returned unchanged, never swallowed.
        """
        if is_refusal(result):
            # A storage failure is block-on-unpersistable; any other refusal is surfaced
            # but never blocks (it is a caller/shape error, not a store outage).
            if is_unpersistable(result):
                self._block = PipeState(cause=BlockCause.STORAGE_FAILURE, refusal=result)
            return result
        # A successful command-path write demonstrates the store recovered.
        self._clear_block(BlockCause.STORAGE_FAILURE)
        return result

    def _clear_block(self, cause: BlockCause) -> None:
        """Clear an outstanding command block only if it was set by ``cause``.

        A storage-failure block clears when the store recovers; a rotation-store block clears
        only on a successful store or operator re-provision. Clearing is scoped to the cause
        so a recovered sink write never masks an unresolved rotation-store alarm.
        """
        if self._block is not None and self._block.cause is cause:
            self._block = None

    # -- injected-sink wiring: the sensing path ------------------------------

    def emit_sensing_observation(self, observation: object) -> SinkResult:
        """Record a sensing-path observation through the injected ``ObservationSink``.

        The sensing pipe is a separate stream: it is **never gated by a command-pipe block**
        and a persistence failure here does not block the command stream — the sensing pipe
        is unaffected (AR-47, FM-2; DEC-0138). The sink result is surfaced, never swallowed,
        and the observation is recorded only through the injected sink, never a direct write.
        """
        return self._observation_sink.emit(observation)

    # -- health --------------------------------------------------------------

    def health(self) -> HealthReport:
        """A typed health report carrying reference ids only — never a secret value.

        Renderable and safe to expose as a metric or log line: the ``held_secret_ref_ids``
        are opaque references and no plaintext appears anywhere in the report (CT-21, AR-37;
        DEC-0136).
        """
        return HealthReport(
            machine=self._writer_id.machine,
            adapter_role=self._writer_id.role,
            command_stream=self._writer_id.stream,
            boot_epoch_id=self._writer_id.boot_epoch_id,
            command_pipe=(
                CommandPipeStatus.OPEN if self._block is None else CommandPipeStatus.BLOCKED
            ),
            command_block_cause=None if self._block is None else self._block.cause,
            sensing_pipe=CommandPipeStatus.OPEN,
            open_session_count=len(self._secrets),
            held_secret_ref_ids=tuple(sorted(ref.value for ref in self._secrets)),
        )

    def __repr__(self) -> str:
        # Never renders a secret: only the writer's command stream and the session count.
        return (
            f"ConnectionManager(command_stream={self._writer_id.stream!r}, "
            f"sessions={len(self._secrets)}, command_pipe_open={self._block is None})"
        )


def _coerce_world(value: object) -> World | None:
    """Return the :class:`~qmf.core.World` member ``value`` names, or ``None``."""
    if isinstance(value, World):
        return value
    if isinstance(value, str):
        try:
            return World(value)
        except ValueError:
            return None
    return None
