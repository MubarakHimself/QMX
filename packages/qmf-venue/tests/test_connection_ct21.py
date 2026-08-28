"""Story 8.3 tests — secret lifecycle, connection manager, and injected-sink wiring.

Fixture-driven throughout: the secret store and the three sinks are canned in-memory
fakes that contact no host and no filesystem, so every persistence crosses an injected
seam. These pin every acceptance criterion (CT-21, AR-37, AR-38, AR-47; DEC-0136,
DEC-0138):

* a ``SecretValue`` renders only its reference id under repr/str/format/serialization,
  and the tier-1 secret-scan gate rides ``poe check``;
* the connection manager holds the venue ``WriterId`` and the injected ``SecretStore``,
  is the single in-memory value-holder, and lets no secret cross back out through a
  getter, log line, refusal context, health field, or metric label;
* rotation is store-before-discard, and a failed store after rotation is an
  unavailable-dependency alarm plus a command-pipe block with the sensing pipe unaffected;
* a missing/expired/rejected credential is an unavailable-dependency refusal carrying the
  reference id, never the value; a binding's secret reference is excluded from fp1; a
  non-opaque reference construction is an invalid-input refusal;
* a command-path sink storage failure blocks the command stream, the sensing pipe is
  unaffected, and no store is ever written directly rather than through an injected sink.
"""

from __future__ import annotations

import copy
import pickle
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

import pytest
import tomllib
from qmf.core import (
    Account,
    AccountRole,
    Fingerprint,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    SecretRef,
    SecretValue,
    SinkAck,
    SinkResult,
    TypedRefusal,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.venue import (
    AccountBinding,
    BlockCause,
    CommandPipeStatus,
    ConnectionManager,
    HealthReport,
    PipeState,
    venue_command_stream,
    venue_writer_id,
)

T = TypeVar("T")

_MACHINE = "vps-fra-01"
_ADAPTER_ROLE = "ctrader-adapter"
_BOOT_EPOCH = "boot-epoch-A"
_BOOT = _BOOT_EPOCH
_CRED_REF_ID = "sref-71a4c9e2d8b305"
# A deliberately non-empty fake plaintext, used only as a test fixture (S106 waived for
# tests): it must never render through any manager surface.
_PLAINTEXT = "plaintext-refresh-token-value-xyz"
_PLAINTEXT_2 = "rotated-refresh-token-value-abc"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]) -> TypedRefusal:
    assert is_refusal(result), result
    return result


def _venue() -> VenueId:
    return _ok(VenueId.try_create("venue-ctrader-demo"))


def _account(venue: VenueId | None = None, *, account_id: str = "acct-001") -> Account:
    anchor = venue if venue is not None else _venue()
    return _ok(Account.try_create(account_id, anchor, AccountRole.DEMO))


def _secret_ref(value: str = _CRED_REF_ID) -> SecretRef:
    return _ok(SecretRef.try_create(value))


def _secret_value(ref: SecretRef | None = None, plaintext: str = _PLAINTEXT) -> SecretValue:
    return _ok(SecretValue.try_create(ref if ref is not None else _secret_ref(), plaintext))


def _instant(value_ns: int) -> Instant:
    return _ok(Instant.try_create(value_ns))


def _binding(
    *, venue: VenueId | None = None, world: World = World.LIVE, ref: SecretRef | None = None
) -> AccountBinding:
    anchor = venue if venue is not None else _venue()
    return _ok(
        AccountBinding.try_create(
            anchor, _account(anchor), world, ref if ref is not None else _secret_ref()
        )
    )


def _writer(*, venue: VenueId | None = None) -> WriterId:
    anchor = venue if venue is not None else _venue()
    return _ok(venue_writer_id(_MACHINE, _ADAPTER_ROLE, anchor, _account(anchor), _BOOT_EPOCH))


# --- canned injected seams --------------------------------------------------


class FakeSecretStore:
    """An in-memory ``SecretStore``: read + atomic replace, no host, no disk."""

    def __init__(self) -> None:
        self._values: dict[SecretRef, SecretValue] = {}
        self.reject_read: bool = False
        self.fail_replace: bool = False
        self.replaced: list[SecretRef] = []
        # A probe invoked at the start of atomic_replace so a test can inspect the
        # connection manager's held state at store time (store-before-discard).
        self.replace_probe: Callable[[], None] | None = None

    def preload(self, value: SecretValue) -> None:
        self._values[value.ref] = value

    def preload_under(self, key: SecretRef, value: SecretValue) -> None:
        # Store a value under a key that does not match the value's own reference, so a
        # read can return a mismatched value — a store contract violation to test against.
        self._values[key] = value

    def read(self, ref: SecretRef, /) -> Result[SecretValue]:
        if self.reject_read or ref not in self._values:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.NO,
                context={"field": "credential", "secret_ref": ref.value},
            )
        return Ok(self._values[ref])

    def atomic_replace(self, ref: SecretRef, new_value: SecretValue, /) -> Result[SecretRef]:
        if self.replace_probe is not None:
            self.replace_probe()
        if self.fail_replace:
            return unpersistable(
                "the protected store rejected the rotated credential",
                context={"secret_ref": ref.value},
            )
        self._values[ref] = new_value
        self.replaced.append(ref)
        return Ok(ref)


class FakeObservationSink:
    def __init__(self) -> None:
        self.emitted: list[object] = []
        self.fail: bool = False
        # When set, return a NON-storage-failure refusal (an invalid-input) instead — it is
        # surfaced but must not trigger the block-on-unpersistable command block.
        self.fail_nonstorage: bool = False

    def emit(self, observation: object, /) -> SinkResult:
        if self.fail_nonstorage:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={"field": "observation"},
            )
        if self.fail:
            return unpersistable("observation store unavailable")
        self.emitted.append(observation)
        return Ok(SinkAck())


class FakeJournalSink:
    def __init__(self) -> None:
        self.appended: list[object] = []
        self.fail: bool = False

    def append(self, event: object, /) -> SinkResult:
        if self.fail:
            return unpersistable("journal store unavailable")
        self.appended.append(event)
        return Ok(SinkAck())


class FakeRecordSink:
    def __init__(self) -> None:
        self.written: list[object] = []
        self.fail: bool = False

    def write(self, record: object, /) -> SinkResult:
        if self.fail:
            return unpersistable("registry store unavailable")
        self.written.append(record)
        return Ok(SinkAck())


class _Sinks:
    def __init__(self) -> None:
        self.store = FakeSecretStore()
        self.obs = FakeObservationSink()
        self.journal = FakeJournalSink()
        self.record = FakeRecordSink()


def _manager(sinks: _Sinks | None = None, *, venue: VenueId | None = None) -> ConnectionManager:
    kit = sinks if sinks is not None else _Sinks()
    return _ok(
        ConnectionManager.try_create(
            _writer(venue=venue), kit.store, kit.obs, kit.journal, kit.record
        )
    )


# --- AC1: SecretValue never renders; the secret-scan gate rides poe check ----


def test_secret_value_repr_str_format_yield_reference_never_value() -> None:
    value = _secret_value()
    assert _PLAINTEXT not in repr(value)
    assert _PLAINTEXT not in str(value)
    assert _PLAINTEXT not in format(value)
    assert _PLAINTEXT not in f"{value}"
    assert _PLAINTEXT not in f"{value!r}"
    # Every rendering surfaces the opaque reference id, the safe handle.
    assert _CRED_REF_ID in repr(value)
    assert _CRED_REF_ID in str(value)


def test_secret_value_is_never_serialized() -> None:
    value = _secret_value()
    try:
        pickle.dumps(value)
    except TypeError:
        pass
    else:  # pragma: no cover - a SecretValue must refuse pickling
        raise AssertionError("a SecretValue must never pickle")
    try:
        copy.deepcopy(value)
    except TypeError:
        pass
    else:  # pragma: no cover - copy routes through __reduce_ex__ and must refuse
        raise AssertionError("a SecretValue must never copy")


def test_tier1_secret_scan_gate_rides_poe_check() -> None:
    # The gate is wired at the workspace root: poe's `check` sequence includes secret-scan.
    root = Path(__file__).resolve().parents[3] / "pyproject.toml"
    config = tomllib.loads(root.read_text(encoding="utf-8"))
    tasks = config["tool"]["poe"]["tasks"]
    assert "secret-scan" in tasks
    assert "secret-scan" in tasks["check"]["sequence"]


# --- AC2: writer id, injected store, single holder, no secret crosses out ----


def test_writer_id_is_at_venue_granularity() -> None:
    writer = _writer()
    assert writer.machine == _MACHINE
    assert writer.role == _ADAPTER_ROLE
    assert writer.stream == venue_command_stream(_venue(), _account())
    assert writer.boot_epoch_id == _BOOT_EPOCH
    manager = _manager()
    assert manager.writer_id == writer


def test_venue_writer_id_refuses_malformed_wiring() -> None:
    good_venue = _venue()
    assert is_refusal(venue_writer_id(_MACHINE, _ADAPTER_ROLE, "not-a-venue", _account(), _BOOT))
    assert is_refusal(venue_writer_id(_MACHINE, _ADAPTER_ROLE, good_venue, "not-an-account", _BOOT))
    # An account belonging to another venue cannot key this command stream.
    other = _ok(VenueId.try_create("venue-other"))
    foreign = _account(other)
    assert is_refusal(venue_writer_id(_MACHINE, _ADAPTER_ROLE, good_venue, foreign, _BOOT))
    # A blank boot epoch is refused by the core WriterId factory.
    assert is_refusal(
        venue_writer_id(_MACHINE, _ADAPTER_ROLE, good_venue, _account(good_venue), "")
    )


def test_try_create_refuses_every_missing_seam() -> None:
    kit = _Sinks()
    writer = _writer()
    assert is_refusal(
        ConnectionManager.try_create("nope", kit.store, kit.obs, kit.journal, kit.record)
    )
    assert is_refusal(
        ConnectionManager.try_create(writer, object(), kit.obs, kit.journal, kit.record)
    )
    assert is_refusal(
        ConnectionManager.try_create(writer, kit.store, object(), kit.journal, kit.record)
    )
    assert is_refusal(
        ConnectionManager.try_create(writer, kit.store, kit.obs, object(), kit.record)
    )
    assert is_refusal(
        ConnectionManager.try_create(writer, kit.store, kit.obs, kit.journal, object())
    )


def test_manager_is_single_holder_and_exposes_no_value_getter() -> None:
    kit = _Sinks()
    kit.store.preload(_secret_value())
    manager = _manager(kit)
    binding = _binding()
    assert is_ok(manager.open_session(binding))
    # The session-open return is the reference, never the value.
    opened = _ok(manager.open_session(binding))
    assert isinstance(opened, SecretRef)
    assert opened == binding.secret_ref
    # Presence is queryable; the value is not — no public attribute returns plaintext.
    assert manager.holds_secret(binding.secret_ref)
    assert not manager.holds_secret(_secret_ref("sref-e2d3c4b5a60718"))
    assert not manager.holds_secret("not-a-ref")
    for name in dir(manager):
        if name.startswith("__"):
            continue
        attr = getattr(manager, name)
        if callable(attr):
            continue
        assert not isinstance(attr, SecretValue)


def test_no_secret_crosses_out_through_health_repr_or_refusal() -> None:
    kit = _Sinks()
    kit.store.preload(_secret_value())
    manager = _manager(kit)
    binding = _binding()
    assert is_ok(manager.open_session(binding))
    report = manager.health()
    # Health carries the reference id only — never the plaintext.
    assert _CRED_REF_ID in report.held_secret_ref_ids
    assert _PLAINTEXT not in str(report)
    assert _PLAINTEXT not in repr(manager)
    # A read failure refusal carries the reference id, never the value.
    kit.store.reject_read = True
    refusal = _refusal(manager.open_session(_binding(ref=_secret_ref("sref-09d8c7b6a5e403"))))
    assert refusal.context["secret_ref"] == "sref-09d8c7b6a5e403"
    assert _PLAINTEXT not in str(refusal.context)


def test_open_session_rejects_foreign_stream_and_non_binding() -> None:
    manager = _manager()
    assert is_refusal(manager.open_session("not-a-binding"))
    other = _ok(VenueId.try_create("venue-elsewhere"))
    foreign_binding = _binding(venue=other)
    stream_refusal = _refusal(manager.open_session(foreign_binding))
    assert stream_refusal.category is RefusalCategory.INVALID_INPUT


def test_open_session_refuses_value_for_wrong_reference() -> None:
    kit = _Sinks()
    binding = _binding()
    # The store returns, for the requested reference, a value carrying a DIFFERENT ref — a
    # store contract violation, refused rather than trusted (and never held).
    kit.store.preload_under(binding.secret_ref, _secret_value(ref=_secret_ref("sref-a7d2e9c4")))
    manager = _manager(kit)
    refusal = _refusal(manager.open_session(binding))
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refusal.context["secret_ref"] == _CRED_REF_ID
    assert not manager.holds_secret(binding.secret_ref)


def test_close_session_discards_the_held_value() -> None:
    kit = _Sinks()
    kit.store.preload(_secret_value())
    manager = _manager(kit)
    binding = _binding()
    assert is_ok(manager.open_session(binding))
    assert manager.holds_secret(binding.secret_ref)
    assert is_ok(manager.close_session(binding.secret_ref))
    assert not manager.holds_secret(binding.secret_ref)
    # Closing again, or an unheld / non-ref, is an invalid-input refusal.
    assert is_refusal(manager.close_session(binding.secret_ref))
    assert is_refusal(manager.close_session("not-a-ref"))


def test_next_command_key_stamps_writer_and_strictly_increasing_sequence() -> None:
    manager = _manager()
    key0 = _ok(manager.next_command_key(_instant(1_000)))
    key1 = _ok(manager.next_command_key(_instant(2_000)))
    assert key0.writer == manager.writer_id
    assert key0.sequence == 0
    assert key1.sequence == 1
    assert is_refusal(manager.next_command_key("not-an-instant"))


# --- AC3: rotation is store-before-discard; failed store blocks the command pipe


def test_rotation_stores_before_discarding_old_material() -> None:
    kit = _Sinks()
    old = _secret_value()
    kit.store.preload(old)
    manager = _manager(kit)
    binding = _binding()
    assert is_ok(manager.open_session(binding))

    # At the moment the store is asked to persist the new secret, the OLD one is still
    # held — the discard happens only after a durable store (store-before-discard).
    seen_at_store_time: list[bool] = []

    def probe() -> None:
        seen_at_store_time.append(manager.holds_secret(binding.secret_ref))

    kit.store.replace_probe = probe
    new = _secret_value(plaintext=_PLAINTEXT_2)
    assert is_ok(manager.rotate_secret(binding, new))
    assert seen_at_store_time == [True]
    assert kit.store.replaced == [binding.secret_ref]
    # The new value is now the held one; the manager still holds exactly one session.
    assert manager.holds_secret(binding.secret_ref)
    assert manager.health().open_session_count == 1
    assert manager.command_pipe_open


def test_failed_store_after_rotation_alarms_and_blocks_command_pipe() -> None:
    kit = _Sinks()
    kit.store.preload(_secret_value())
    manager = _manager(kit)
    binding = _binding()
    assert is_ok(manager.open_session(binding))

    kit.store.fail_replace = True
    new = _secret_value(plaintext=_PLAINTEXT_2)
    refusal = _refusal(manager.rotate_secret(binding, new))
    # Unavailable-dependency alarm with the after-condition retry gate; ref id, no value.
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refusal.retryability is Retryability.AFTER_CONDITION
    assert refusal.after_condition_descriptor == "successful store or operator re-provision"
    assert refusal.context["alarm"] is True
    assert refusal.context["secret_ref"] == _CRED_REF_ID
    assert _PLAINTEXT_2 not in str(refusal.context)
    # The command pipe is blocked by the rotation-store failure; sensing is unaffected.
    assert not manager.command_pipe_open
    assert manager.sensing_pipe_open
    block = manager.command_block
    assert isinstance(block, PipeState)
    assert block.cause is BlockCause.ROTATION_STORE_FAILURE
    # The old material is kept undiscarded (store-before-discard: the store failed).
    assert manager.holds_secret(binding.secret_ref)


def test_successful_reprovision_clears_the_rotation_block() -> None:
    kit = _Sinks()
    kit.store.preload(_secret_value())
    manager = _manager(kit)
    binding = _binding()
    assert is_ok(manager.open_session(binding))
    kit.store.fail_replace = True
    assert is_refusal(manager.rotate_secret(binding, _secret_value(plaintext=_PLAINTEXT_2)))
    assert not manager.command_pipe_open
    # A successful store (operator re-provision) satisfies the after-condition and clears it.
    kit.store.fail_replace = False
    assert is_ok(manager.rotate_secret(binding, _secret_value(plaintext=_PLAINTEXT_2)))
    assert manager.command_pipe_open


def test_rotation_refuses_malformed_new_secret() -> None:
    kit = _Sinks()
    kit.store.preload(_secret_value())
    manager = _manager(kit)
    binding = _binding()
    assert is_refusal(manager.rotate_secret("not-a-binding", _secret_value()))
    assert is_refusal(manager.rotate_secret(binding, "not-a-secret-value"))
    # A SecretValue for a different reference is refused.
    mismatched = _secret_value(ref=_secret_ref("sref-d8f1a4c7"))
    refusal = _refusal(manager.rotate_secret(binding, mismatched))
    assert refusal.category is RefusalCategory.INVALID_INPUT
    # A command-pipe-block was never set by these caller mistakes.
    assert manager.command_pipe_open


# --- AC4: missing credential refusal; binding ref excluded from fp1 ----------


def test_missing_credential_is_unavailable_dependency_with_reference_only() -> None:
    kit = _Sinks()  # store is empty: the credential is missing.
    manager = _manager(kit)
    binding = _binding()
    refusal = _refusal(manager.open_session(binding))
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refusal.context["secret_ref"] == _CRED_REF_ID
    assert not manager.holds_secret(binding.secret_ref)


def test_binding_secret_reference_is_excluded_from_fp1() -> None:
    venue = _venue()
    account = _account(venue)
    base = _ok(AccountBinding.try_create(venue, account, World.LIVE, _secret_ref("ref-A")))
    rotated = _ok(AccountBinding.try_create(venue, account, World.LIVE, _secret_ref("ref-B")))
    # Two bindings differing ONLY by credential reference fingerprint identically: the
    # secret reference is occurrence/display-only and never enters identity.
    fp_base = _ok(base.fingerprint())
    fp_rotated = _ok(rotated.fingerprint())
    assert isinstance(fp_base, Fingerprint)
    assert fp_base == fp_rotated
    identity = base.fp1_identity()
    assert "secret_ref" not in identity
    assert set(identity) == {"class", "venue_id", "account_id", "role", "world"}
    # A different world DOES change identity — world is part of the binding identity tuple.
    other_world = _ok(AccountBinding.try_create(venue, account, World.REPLAY, _secret_ref("ref-A")))
    assert _ok(other_world.fingerprint()) != fp_base


def test_binding_construction_refusals() -> None:
    venue = _venue()
    account = _account(venue)
    ref = _secret_ref()
    assert is_refusal(AccountBinding.try_create("nope", account, World.LIVE, ref))
    assert is_refusal(AccountBinding.try_create(venue, "nope", World.LIVE, ref))
    assert is_refusal(AccountBinding.try_create(venue, account, "not-a-world", ref))
    # A non-string, non-World value is likewise refused (world coercion returns None).
    assert is_refusal(AccountBinding.try_create(venue, account, 123, ref))
    # An account belonging to another venue cannot form a binding under this venue.
    other = _ok(VenueId.try_create("venue-other"))
    assert is_refusal(AccountBinding.try_create(venue, _account(other), World.LIVE, ref))
    # A non-SecretRef (or empty) credential handle is an invalid-input refusal.
    assert is_refusal(AccountBinding.try_create(venue, account, World.LIVE, "raw-string-ref"))
    assert is_refusal(AccountBinding.try_create(venue, account, World.LIVE, SecretRef("")))


def test_non_opaque_reference_construction_is_invalid_input() -> None:
    # A non-opaque (blank) reference is refused at construction with an invalid-input refusal.
    refusal = _refusal(SecretRef.try_create("   "))
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert is_refusal(SecretRef.try_create(""))
    assert is_refusal(SecretRef.try_create(None))
    # A valid opaque token constructs cleanly.
    assert is_ok(SecretRef.try_create("opaque-token-0001"))


@pytest.mark.parametrize(
    "bad",
    [
        "venue=cTrader;broker=Pepperstone;account=1234567;env=live;key=material",
        "live/ctrader/acct-9988/refresh-token-material",
        "APIKEY-1a2b3c4d5e6f-account-1234567",
        "sref-venue-0001",
        "sref-broker-0001",
        "sref-account-0001",
        "sref-environment-0001",
        "sref-key-0001",
        "not-a-minted-id",
    ],
)
def test_non_opaque_reference_semantics_are_refused_before_binding(bad: str) -> None:
    """CT-21: the qmf-core construction gate protects the venue consumer."""
    refusal = _refusal(SecretRef.try_create(bad))
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "value"
    assert bad not in repr(refusal.context)


def test_binding_revalidates_an_unchecked_secret_ref() -> None:
    """The public venue factory cannot trust qmf-core's unchecked constructor path."""
    venue = _venue()
    account = _account(venue)
    unchecked = SecretRef("sref-account-0001")

    refusal = _refusal(AccountBinding.try_create(venue, account, World.LIVE, unchecked))
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "secret_ref"
    assert unchecked.value not in repr(refusal.context)


def test_binding_command_stream_matches_writer_stream() -> None:
    binding = _binding()
    assert binding.command_stream == venue_command_stream(_venue(), _account())


# --- AC5: command-path storage failure blocks; sensing pipe unaffected -------


def test_command_path_storage_failure_blocks_command_stream() -> None:
    kit = _Sinks()
    manager = _manager(kit)
    assert manager.command_pipe_open
    assert is_ok(manager.require_command_pipe_open())

    kit.obs.fail = True
    result = manager.emit_command_observation({"kind": "command-outcome"})
    # The storage failure is surfaced, never swallowed, and blocks the command stream.
    assert is_refusal(result)
    assert not manager.command_pipe_open
    block = manager.command_block
    assert isinstance(block, PipeState)
    assert block.cause is BlockCause.STORAGE_FAILURE
    # The gate a dispatcher reads now returns the block's refusal.
    assert is_refusal(manager.require_command_pipe_open())


def test_each_command_sink_blocks_on_storage_failure() -> None:
    for setter in ("obs", "journal", "record"):
        kit = _Sinks()
        manager = _manager(kit)
        getattr(kit, setter).fail = True
        if setter == "obs":
            out = manager.emit_command_observation({"x": 1})
        elif setter == "journal":
            out = manager.append_command_journal({"x": 1})
        else:
            out = manager.write_command_record({"x": 1})
        assert is_refusal(out)
        assert not manager.command_pipe_open


def test_command_pipe_block_clears_when_store_recovers() -> None:
    kit = _Sinks()
    manager = _manager(kit)
    kit.journal.fail = True
    assert is_refusal(manager.append_command_journal({"x": 1}))
    assert not manager.command_pipe_open
    # The store recovers; a subsequent successful command-path write clears the block.
    kit.journal.fail = False
    assert is_ok(manager.append_command_journal({"x": 2}))
    assert manager.command_pipe_open
    assert kit.journal.appended == [{"x": 2}]


def test_successful_sink_write_does_not_clear_a_rotation_block() -> None:
    kit = _Sinks()
    kit.store.preload(_secret_value())
    manager = _manager(kit)
    binding = _binding()
    assert is_ok(manager.open_session(binding))
    kit.store.fail_replace = True
    assert is_refusal(manager.rotate_secret(binding, _secret_value(plaintext=_PLAINTEXT_2)))
    assert manager.command_block is not None
    assert manager.command_block.cause is BlockCause.ROTATION_STORE_FAILURE
    # A successful sink write recovers the SINK store, not the SECRET store: the
    # rotation-store block, scoped to its own after-condition, stays.
    assert is_ok(manager.emit_command_observation({"x": 1}))
    assert not manager.command_pipe_open
    assert manager.command_block is not None
    assert manager.command_block.cause is BlockCause.ROTATION_STORE_FAILURE


def test_sensing_pipe_unaffected_by_command_block() -> None:
    kit = _Sinks()
    manager = _manager(kit)
    kit.record.fail = True
    assert is_refusal(manager.write_command_record({"x": 1}))
    assert not manager.command_pipe_open
    # The sensing pipe stays open and keeps recording despite the command block.
    assert manager.sensing_pipe_open
    ack = manager.emit_sensing_observation({"tick": 1})
    assert is_ok(ack)
    assert kit.obs.emitted == [{"tick": 1}]


def test_non_storage_failure_from_command_sink_is_surfaced_without_blocking() -> None:
    kit = _Sinks()
    manager = _manager(kit)
    # A non-storage-failure refusal (invalid input) is surfaced but is NOT block-on-
    # unpersistable: the command pipe stays open and no block is set.
    kit.obs.fail_nonstorage = True
    result = manager.emit_command_observation({"x": 1})
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert manager.command_pipe_open
    assert manager.command_block is None


def test_sensing_storage_failure_does_not_block_the_command_pipe() -> None:
    kit = _Sinks()
    manager = _manager(kit)
    kit.obs.fail = True
    result = manager.emit_sensing_observation({"tick": 1})
    # A sensing-path storage failure is surfaced but never blocks the command stream.
    assert is_refusal(result)
    assert manager.command_pipe_open


def test_persistence_only_ever_crosses_the_injected_sinks() -> None:
    kit = _Sinks()
    manager = _manager(kit)
    assert is_ok(manager.emit_command_observation({"a": 1}))
    assert is_ok(manager.append_command_journal({"b": 2}))
    assert is_ok(manager.write_command_record({"c": 3}))
    assert is_ok(manager.emit_sensing_observation({"d": 4}))
    # Every write landed in an injected sink — the manager never wrote a store directly.
    assert kit.obs.emitted == [{"a": 1}, {"d": 4}]
    assert kit.journal.appended == [{"b": 2}]
    assert kit.record.written == [{"c": 3}]


# --- health report shape ----------------------------------------------------


def test_health_report_shape_open_and_blocked() -> None:
    kit = _Sinks()
    kit.store.preload(_secret_value())
    manager = _manager(kit)
    open_report = manager.health()
    assert isinstance(open_report, HealthReport)
    assert open_report.machine == _MACHINE
    assert open_report.adapter_role == _ADAPTER_ROLE
    assert open_report.command_stream == venue_command_stream(_venue(), _account())
    assert open_report.boot_epoch_id == _BOOT_EPOCH
    assert open_report.command_pipe is CommandPipeStatus.OPEN
    assert open_report.command_block_cause is None
    assert open_report.sensing_pipe is CommandPipeStatus.OPEN
    assert open_report.open_session_count == 0
    assert open_report.held_secret_ref_ids == ()

    kit.obs.fail = True
    assert is_refusal(manager.emit_command_observation({"x": 1}))
    blocked = manager.health()
    assert blocked.command_pipe is CommandPipeStatus.BLOCKED
    assert blocked.command_block_cause is BlockCause.STORAGE_FAILURE
