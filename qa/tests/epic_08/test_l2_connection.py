"""L2 contract tests — CT-21 venue secret & session boundary (Story 8.3).

Oracle: docs/contracts/ct-21-venue-secret-session.yaml (verbatim invariants),
constitution L34, and the Story 8.3 acceptance criteria.

Covers QA-E08-L2-019..022.
"""

from __future__ import annotations

from qmf.core import RefusalCategory, Retryability, World, is_ok, is_refusal
from qmf.venue import AccountBinding

import _helpers as H

SECRET_PLAINTEXT = "plaintext-crown-jewel-XYZZY"


# --- QA-E08-L2-019 — binding identity excludes the secret ref (P1) ----------


def test_l2_019_binding_fp1_excludes_secret_reference():
    """CT-21: an account-binding's identity is (VenueId, AccountId, role, world) and its
    secret reference is occurrence/display-only, excluded from fp1."""
    v = H.mk_venue()
    a = H.mk_account(v)
    binding = H.make_account_binding(v, a, H.mk_secret_ref("sref-A"))
    content = dict(binding.fp1_identity())
    assert "secret_ref" not in content
    assert content["venue_id"] == v.value
    assert content["account_id"] == a.account_id
    assert content["role"] == a.role.value
    assert content["world"] == World.LIVE.value


def test_l2_019_bindings_differing_only_by_credential_fingerprint_identically():
    """CT-21: two bindings that differ only by credential reference fingerprint
    identically — a credential is a deployment fact, never a market fact."""
    v = H.mk_venue()
    a = H.mk_account(v)
    b1 = H.make_account_binding(v, a, H.mk_secret_ref("sref-A"))
    b2 = H.make_account_binding(v, a, H.mk_secret_ref("sref-B"))
    assert H.ok(b1.fingerprint()) == H.ok(b2.fingerprint())


def test_l2_019_non_opaque_secret_ref_is_refused_at_binding_construction():
    """CT-21: a binding names its credential by a bare opaque SecretRef; a non-SecretRef
    is an invalid-input refusal."""
    v = H.mk_venue()
    a = H.mk_account(v)
    res = AccountBinding.try_create(v, a, World.LIVE, "raw-string-not-a-ref")
    assert is_refusal(res)
    assert res.category is RefusalCategory.INVALID_INPUT


# --- QA-E08-L2-020 — single value-holder / no leak (P0) ---------------------


def test_l2_020_secret_value_never_crosses_out_of_the_connection_manager():
    """CT-21/AR-37: the connection manager is the single value-holder — no secret value
    crosses out through a getter, log line (repr), health field, or metric label."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ref = H.mk_secret_ref("sref-hold")
    value = H.mk_secret_value(ref, SECRET_PLAINTEXT)
    store = H.FakeSecretStore(values={ref: value})
    cm = H.build_connection_manager(v, a, secret_store=store)
    binding = H.make_account_binding(v, a, ref)

    opened = cm.open_session(binding)
    assert is_ok(opened)
    # open_session returns ONLY the reference, never the value.
    assert opened.value == ref
    assert cm.holds_secret(ref) is True

    # No getter/attribute exposes the plaintext or the SecretValue.
    for forbidden in ("reveal", "secret_value", "get_secret", "secrets", "secret_for"):
        attr = getattr(cm, forbidden, None)
        assert not callable(attr), f"connection manager exposes a secret getter: {forbidden}"

    # The plaintext never appears in repr (a log line) or the health report.
    assert SECRET_PLAINTEXT not in repr(cm)
    health = cm.health()
    assert SECRET_PLAINTEXT not in str(health)
    assert health.held_secret_ref_ids == (ref.value,)  # reference ids only


def test_l2_020_missing_credential_is_unavailable_dependency_carrying_ref_not_value():
    """CT-21: a missing/expired/rejected credential is an unavailable-dependency refusal
    carrying the reference id, never the value."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ref = H.mk_secret_ref("sref-missing")
    store = H.FakeSecretStore(read_fails=True)  # store cannot supply the credential
    cm = H.build_connection_manager(v, a, secret_store=store)
    binding = H.make_account_binding(v, a, ref)
    res = cm.open_session(binding)
    assert is_refusal(res)
    assert res.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    # The refusal context carries the reference id, never a plaintext value.
    assert res.context.get("secret_ref") == ref.value
    assert SECRET_PLAINTEXT not in str(res.context)


# --- QA-E08-L2-021 — rotation store-before-discard (P0) ---------------------


def test_l2_021_failed_store_after_rotation_alarms_blocks_command_keeps_old():
    """CT-21/AR-38: rotation is store-before-discard — a failed store after rotation is
    an unavailable-dependency alarm plus a command-pipe block (after-condition), the old
    value is kept undiscarded, and the sensing pipe is unaffected."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ref = H.mk_secret_ref("sref-rot")
    old_value = H.mk_secret_value(ref, "old-secret")
    store = H.FakeSecretStore(values={ref: old_value}, replace_fails=True)
    cm = H.build_connection_manager(v, a, secret_store=store)
    binding = H.make_account_binding(v, a, ref)
    assert is_ok(cm.open_session(binding))

    new_value = H.mk_secret_value(ref, "new-secret")
    res = cm.rotate_secret(binding, new_value)
    assert is_refusal(res)
    assert res.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert res.retryability is Retryability.AFTER_CONDITION
    assert res.context.get("alarm") is True
    # The command pipe is blocked; the old material is kept (store-before-discard); the
    # sensing pipe is unaffected.
    assert cm.command_pipe_open is False
    assert cm.holds_secret(ref) is True
    assert cm.sensing_pipe_open is True


def test_l2_021_successful_rotation_stores_then_swaps():
    """CT-21/AR-38: a successful store durably persists the new secret and swaps the
    held value; the command pipe stays open."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ref = H.mk_secret_ref("sref-rot2")
    old_value = H.mk_secret_value(ref, "old-secret")
    store = H.FakeSecretStore(values={ref: old_value})
    cm = H.build_connection_manager(v, a, secret_store=store)
    binding = H.make_account_binding(v, a, ref)
    assert is_ok(cm.open_session(binding))
    res = cm.rotate_secret(binding, H.mk_secret_value(ref, "new-secret"))
    assert is_ok(res)
    assert cm.command_pipe_open is True
    assert cm.holds_secret(ref) is True


# --- QA-E08-L2-022 — one writer / session-epoch (P2) ------------------------


def test_l2_022_per_writer_sequence_is_strictly_increasing():
    """CT-19/CT-21: the per-writer command sequence is gapless and strictly increasing
    within one boot epoch."""
    v = H.mk_venue()
    a = H.mk_account(v)
    cm = H.build_connection_manager(v, a)
    k1 = H.ok(cm.next_command_key(H.mk_instant(1000)))
    k2 = H.ok(cm.next_command_key(H.mk_instant(1001)))
    k3 = H.ok(cm.next_command_key(H.mk_instant(1002)))
    assert k1.sequence < k2.sequence < k3.sequence


def test_l2_022_one_held_value_per_credential_and_boot_epoch_distinct():
    """CT-21: exactly one held value per credential (one refresher per credential), and
    the boot epoch on the WriterId is a distinct field from the session epoch that rides
    observations."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ref = H.mk_secret_ref("sref-one")
    value = H.mk_secret_value(ref, "s")
    store = H.FakeSecretStore(values={ref: value})
    cm = H.build_connection_manager(v, a, secret_store=store)
    binding = H.make_account_binding(v, a, ref)
    assert is_ok(cm.open_session(binding))
    assert is_ok(cm.open_session(binding))  # re-open is idempotent for the same ref
    assert cm.health().open_session_count == 1  # one held value per credential

    # The boot epoch is a distinct WriterId field (not the session epoch token).
    assert cm.writer_id.boot_epoch_id == H.BOOT_EPOCH
