"""Epic 1 — Story 1.9 core seams: secrets & injected sinks (secret.py, sinks.py). L1.

Independent, requirements-derived assertions (E1-U57..U62). Authored from FM-9,
AR-37/38, AD-15, CT-04/CT-21, epics.md Story 1.9. Source code is read-only evidence.
"""

from __future__ import annotations

import pickle

from qmf.core.fingerprint import canonical_bytes, fingerprint
from qmf.core.refusal import RefusalCategory, Result, Retryability, TypedRefusal, is_ok, is_refusal
from qmf.core.secret import SecretRef, SecretStore, SecretValue
from qmf.core.sinks import (
    JournalSink,
    ObservationSink,
    RecordSink,
    is_unpersistable,
    unpersistable,
)

# Assembled from fragments so the tier-1 secret-scan gate never sees a quoted
# credential assignment in tracked source (QMX-F064 / Story 25.13).
SECRET = "super" + "-secret-token-" + "value-9f3a"
REF_ID = "cred-ref-001"


def _ok(result: Result[object]) -> object:
    assert is_ok(result), f"expected Ok, got {result!r}"
    return result.value


def _refusal(result: Result[object]) -> TypedRefusal:
    assert is_refusal(result), f"expected a TypedRefusal, got {result!r}"
    return result


def _secret_value() -> SecretValue:
    ref = _ok(SecretRef.try_create(REF_ID))
    return _ok(SecretValue.try_create(ref, SECRET))


# E1-U57 -----------------------------------------------------------------------
def test_e1_u57_secret_value_never_renders_only_reference_id() -> None:
    """FM-9 / AR-37 / DEC-0136: SecretValue never renders its secret in repr, str,
    format, or serialization — each yields only the reference id."""
    sv = _secret_value()
    for rendered in (repr(sv), str(sv), format(sv), f"{sv}", f"{sv:>40}"):
        assert SECRET not in rendered
        assert REF_ID in rendered
    # Serialization refuses (never emits secret bytes).
    assert is_refusal(canonical_bytes(sv))
    try:
        pickle.dumps(sv)
        raise AssertionError("a SecretValue must never be serializable")
    except (TypeError, pickle.PicklingError):
        pass
    # The one controlled path returns the plaintext.
    assert sv.reveal() == SECRET


# E1-U58 -----------------------------------------------------------------------
def test_e1_u58_secret_ref_from_non_opaque_reference_refuses() -> None:
    """DEC-0136 / DEC-0109: SecretRef from a non-opaque (empty/blank/non-string)
    reference -> invalid input refusal."""
    for bad in ("", "   ", None, 123):
        r = _refusal(SecretRef.try_create(bad))
        assert r.category is RefusalCategory.INVALID_INPUT
    # A SecretValue built from a non-SecretRef is refused, secret never echoed.
    bad_sv = _refusal(SecretValue.try_create("not-a-ref", SECRET))
    assert SECRET not in str(bad_sv.context)


# E1-U59 -----------------------------------------------------------------------
def test_e1_u59_sink_and_store_protocols_are_typing_protocol_seams() -> None:
    """AD-15 / DEC-0138: the four sink protocols are typing.Protocol seams;
    qmf-core performs no I/O itself (the ports are definitions-only)."""
    for proto in (ObservationSink, JournalSink, RecordSink, SecretStore):
        assert getattr(proto, "_is_protocol", False) is True

    class _StubObs:
        def emit(self, observation: object, /) -> object:
            return None

    assert isinstance(_StubObs(), ObservationSink)  # runtime-checkable seam


# E1-U60 -----------------------------------------------------------------------
def test_e1_u60_sink_refusal_is_ct04_typed_refusal_branchable() -> None:
    """CT-04 / AR-47: a sink's refusal for an unpersistable write is a CT-04 typed
    refusal (category, context, retryability) the caller can branch on."""
    refusal = unpersistable("disk full")
    assert isinstance(refusal, TypedRefusal)
    assert refusal.category is RefusalCategory.STORAGE_FAILURE
    assert refusal.context["reason"] == "disk full"
    assert isinstance(refusal.retryability, Retryability)
    assert is_unpersistable(refusal) is True
    # A non-storage-failure refusal is NOT unpersistable (branch is precise).
    other = TypedRefusal(category=RefusalCategory.INVALID_INPUT, retryability=Retryability.NO)
    assert is_unpersistable(other) is False


# E1-U61 -----------------------------------------------------------------------
def test_e1_u61_secret_store_read_plus_atomic_replace_only_no_plaintext_getter() -> None:
    """AR-37/38: SecretStore exposes read + atomic replace only; no getter path
    returns plaintext outside SecretValue's controlled access."""
    public_callables = {
        name
        for name, member in vars(SecretStore).items()
        if callable(member) and not name.startswith("_")
    }
    assert public_callables == {"read", "atomic_replace"}
    # SecretValue exposes no public attribute holding the plaintext.
    sv = _secret_value()
    public_attrs = {a for a in dir(sv) if not a.startswith("_")}
    for attr in public_attrs:
        value = getattr(sv, attr)
        if not callable(value):
            assert value != SECRET, f"public attribute {attr!r} leaks the plaintext"
    assert "reveal" in public_attrs  # the single controlled access path


# E1-U62 -----------------------------------------------------------------------
def test_e1_u62_secret_ref_and_value_excluded_from_fp1_identity() -> None:
    """DEC-0136 / DEC-0108: a SecretRef/SecretValue is excluded from fp1 identity (a
    credential is a deployment fact, never a market fact)."""
    ref = _ok(SecretRef.try_create(REF_ID))
    assert is_refusal(fingerprint(ref))
    assert is_refusal(fingerprint(_secret_value()))
    assert not hasattr(SecretRef, "fp1_identity")
    assert not hasattr(SecretValue, "fp1_identity")
