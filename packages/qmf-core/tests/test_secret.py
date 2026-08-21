"""Tier-1 tests for the secret seam: SecretRef, SecretValue, SecretStore.

These pin the AR-37 / AR-38 render guard and the read-plus-atomic-replace port: a
SecretValue never renders its plaintext (repr, str, format, serialization, or
logging), the plaintext is reachable only through the one controlled ``reveal``,
and the store exposes no plaintext getter (CT-21; DEC-0136, DEC-0138).
"""

from __future__ import annotations

import io
import logging
import pickle

import pytest
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, Retryability, TypedRefusal, is_ok, is_refusal
from qmf.core.secret import SecretRef, SecretStore, SecretValue

_PLAINTEXT = "correct-horse-staple-42"


def _make_ref(token: str = "secret-ref-ctrader-refresh-01") -> SecretRef:
    result = SecretRef.try_create(token)
    assert is_ok(result)
    return result.value


def _make_value(secret: str = _PLAINTEXT) -> SecretValue:
    result = SecretValue.try_create(_make_ref(), secret)
    assert is_ok(result)
    return result.value


# --- SecretRef --------------------------------------------------------------


def test_secret_ref_try_create_accepts_opaque_token() -> None:
    ref = _make_ref()
    assert ref.value == "secret-ref-ctrader-refresh-01"
    # The reference id is the safe handle — it renders.
    assert ref.value in repr(ref)


@pytest.mark.parametrize("bad", ["", "   ", None, 123, b"bytes"])
def test_secret_ref_try_create_refuses_non_opaque_token(bad: object) -> None:
    result = SecretRef.try_create(bad)
    assert isinstance(result, TypedRefusal)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "value"


def test_secret_ref_is_excluded_from_fp1_identity() -> None:
    # A SecretRef exposes no fp1_identity, so fingerprinting one is refused — a
    # credential reference never folds into a market fact.
    result = fingerprint(_make_ref())
    assert is_refusal(result)


# --- SecretValue: construction ----------------------------------------------


def test_secret_value_try_create_ok() -> None:
    value = _make_value()
    assert value.reveal() == _PLAINTEXT
    assert value.ref.value == "secret-ref-ctrader-refresh-01"


def test_secret_value_try_create_refuses_bad_ref() -> None:
    result = SecretValue.try_create("not-a-ref", _PLAINTEXT)
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "ref"


@pytest.mark.parametrize("bad", ["", 123, None])
def test_secret_value_try_create_refuses_bad_secret(bad: object) -> None:
    result = SecretValue.try_create(_make_ref(), bad)
    assert isinstance(result, TypedRefusal)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "secret"
    # The refusal never echoes the (missing/invalid) secret value itself.
    assert "given" in result.context


# --- SecretValue: the render guard (AR-37) ----------------------------------


def test_secret_value_never_renders_in_repr_or_str() -> None:
    value = _make_value()
    assert _PLAINTEXT not in repr(value)
    assert _PLAINTEXT not in str(value)
    # Both yield the reference id.
    assert value.ref.value in repr(value)
    assert value.ref.value in str(value)


def test_secret_value_never_renders_through_format() -> None:
    value = _make_value()
    # No format spec may coax out the secret.
    assert _PLAINTEXT not in format(value, "")
    assert _PLAINTEXT not in format(value, ">50")
    assert _PLAINTEXT not in f"{value}"
    assert _PLAINTEXT not in f"{value:^30}"


def test_secret_value_never_renders_through_logging() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("qmf.core.tests.secret")
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        value = _make_value()
        logger.info("credential in use: %s and %r", value, value)
    finally:
        logger.removeHandler(handler)
    logged = stream.getvalue()
    assert _PLAINTEXT not in logged
    assert value.ref.value in logged


def test_secret_value_is_never_serialized() -> None:
    value = _make_value()
    # Pickling (and copy, which routes through __reduce_ex__) is blocked so the
    # secret can never reach a byte stream.
    with pytest.raises(TypeError):
        pickle.dumps(value)


def test_secret_value_is_refused_by_canonical_serializer() -> None:
    value = _make_value()
    result = fingerprint(value)
    assert is_refusal(result)
    # The refusal itself never carries the secret.
    assert _PLAINTEXT not in repr(result)


# --- SecretValue: reveal is the only plaintext path -------------------------


def test_reveal_is_the_controlled_plaintext_path() -> None:
    value = _make_value()
    assert value.reveal() == _PLAINTEXT
    # The public surface exposes no other plaintext getter: `ref` returns the
    # reference, never the value.
    assert isinstance(value.ref, SecretRef)


# --- SecretValue: equality, hashing, immutability ---------------------------


def test_secret_value_equality_and_hash() -> None:
    a = _make_value()
    b = _make_value()
    assert a == b
    assert hash(a) == hash(b)
    # A rotated secret under the same reference is a different value.
    other = SecretValue.try_create(_make_ref(), "correct-horse-staple-99")
    assert is_ok(other)
    assert a != other.value


def test_secret_value_equality_with_foreign_type_is_false() -> None:
    value = _make_value()
    # Exercises the NotImplemented arm: comparison to a non-SecretValue is False.
    assert value != "not a secret value"
    assert value != 7
    assert (value == 7) is False


def test_secret_value_is_immutable() -> None:
    value = _make_value()
    with pytest.raises(AttributeError):
        value._secret = "tampered-material"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        del value._secret  # type: ignore[attr-defined]


# --- SecretStore protocol conformance ---------------------------------------


class _ConformingStore:
    def read(self, ref: SecretRef, /) -> Result[SecretValue]:
        return SecretValue.try_create(ref, _PLAINTEXT)

    def atomic_replace(self, ref: SecretRef, new_value: SecretValue, /) -> Result[SecretRef]:
        assert isinstance(new_value, SecretValue)
        return SecretRef.try_create(ref.value)


class _MissingReplace:
    def read(self, ref: SecretRef, /) -> Result[SecretValue]:
        return SecretValue.try_create(ref, _PLAINTEXT)


def test_secret_store_runtime_conformance() -> None:
    assert isinstance(_ConformingStore(), SecretStore)
    # A class missing atomic_replace does not satisfy the port.
    assert not isinstance(_MissingReplace(), SecretStore)


def test_secret_store_read_returns_value_or_refusal() -> None:
    store: SecretStore = _ConformingStore()
    ref = _make_ref()
    result = store.read(ref)
    assert is_ok(result)
    assert result.value.reveal() == _PLAINTEXT
    replaced = store.atomic_replace(ref, result.value)
    assert is_ok(replaced)
    assert isinstance(replaced.value, SecretRef)


def test_missing_credential_refusal_carries_reference_not_value() -> None:
    # The canonical shape a store returns for an absent credential (CT-21): an
    # unavailable-dependency refusal carrying the reference id, never the value.
    ref = _make_ref("secret-ref-absent")
    refusal = TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.AFTER_CONDITION,
        context={"secret_ref": ref.value},
        after_condition_descriptor="operator provisions the credential",
    )
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refusal.context["secret_ref"] == ref.value
    assert _PLAINTEXT not in repr(refusal)
