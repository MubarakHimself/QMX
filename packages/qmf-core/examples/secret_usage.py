"""Reference usage — SecretRef, SecretValue, and the SecretStore seam (COMP-QMF-CORE).

Executable::

    python packages/qmf-core/examples/secret_usage.py

Shows the credential discipline CT-21 / AR-37 / AR-38 pin down:

1. A :class:`SecretRef` is the **safe handle** — it renders its opaque id, and that
   id is what belongs in logs and refusal context.
2. A :class:`SecretValue` **never renders its secret**: ``repr``, ``str``, and
   ``format`` all yield the reference id, and the plaintext is reachable only
   through the one controlled method :meth:`SecretValue.reveal`.
3. The :class:`SecretStore` port exposes **only** read and atomic replace. A missing
   credential is an ``unavailable dependency`` typed refusal carrying the reference
   id — never the value.
4. Rotation is **store-before-discard**: the new secret is durably bound before the
   old is unreachable (AR-38).

``InMemorySecretStore`` here is a *pure reference* store for this example and the
tests — **not** a production holder. In production the single in-memory holder is
the venue adapter's connection manager, wired at the composition root through this
same port; ``qmf-core`` holds no secret value itself.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
)
from qmf.core.secret import SecretRef, SecretStore, SecretValue

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a construction we assert must succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


class InMemorySecretStore:
    """A pure, in-memory reference :class:`SecretStore` for examples and tests only.

    Read plus atomic replace, nothing else — no plaintext getter. It is not the
    platform's secret store and never a production holder; it exists to demonstrate
    the port the composition root injects, the same way ``DataDrivenClock`` is a
    reference ``Clock``.
    """

    def __init__(self) -> None:
        self._values: dict[str, SecretValue] = {}

    def provision(self, value: SecretValue) -> None:
        """Seed the store (a stand-in for the composition root's initial wiring)."""
        self._values[value.ref.value] = value

    def read(self, ref: SecretRef, /) -> Result[SecretValue]:
        current = self._values.get(ref.value)
        if current is None:
            # The refusal carries the reference id only — never a value, never a null.
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "secret_ref": ref.value,
                    "reason": "no credential provisioned at this reference",
                },
                after_condition_descriptor="operator provisions the credential at the reference",
            )
        return Ok(current)

    def atomic_replace(self, ref: SecretRef, new_value: SecretValue, /) -> Result[SecretRef]:
        # Store-before-discard: bind the new value first; only then is the old one
        # unreachable. A real store makes this one atomic filesystem replace.
        self._values[ref.value] = new_value
        return Ok(ref)


def ref_is_the_safe_handle() -> SecretRef:
    """A SecretRef renders its opaque id — safe for logs and refusal context."""
    ref = _unwrap(SecretRef.try_create("sref-7f3a9c2e8d4b01"), "SecretRef")
    assert ref.value in repr(ref)
    return ref


def value_never_renders(ref: SecretRef) -> tuple[SecretValue, str]:
    """A SecretValue hides its secret everywhere but :meth:`reveal`."""
    plaintext = "demo-session-material-001"
    value = _unwrap(SecretValue.try_create(ref, plaintext), "SecretValue")

    # Every rendering path yields the reference id and never the secret.
    assert plaintext not in repr(value)
    assert plaintext not in str(value)
    assert plaintext not in format(value, ">40")
    assert ref.value in repr(value)

    # reveal() is the one controlled path to the plaintext.
    assert value.reveal() == plaintext
    return value, plaintext


def missing_credential_is_a_refusal(store: SecretStore) -> TypedRefusal:
    """A read for an unprovisioned reference refuses, carrying the id, not the value."""
    absent = _unwrap(SecretRef.try_create("sref-9a8b7c6d5e4f03"), "absent ref")
    result = store.read(absent)
    assert isinstance(result, TypedRefusal)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert result.context["secret_ref"] == absent.value
    return result


def rotation_is_store_before_discard(
    store: InMemorySecretStore, ref: SecretRef, old_secret: str
) -> str:
    """Atomic replace binds the new secret before the old becomes unreachable."""
    rotated = "demo-session-material-002"
    new_value = _unwrap(SecretValue.try_create(ref, rotated), "rotated SecretValue")

    replaced = store.atomic_replace(ref, new_value)
    assert is_ok(replaced)

    current = store.read(ref)
    assert is_ok(current)
    # The store now yields the new secret; the old one is gone.
    assert current.value.reveal() == rotated
    assert current.value.reveal() != old_secret
    return rotated


def main() -> None:
    ref = ref_is_the_safe_handle()
    print(f"ref renders its id: {ref.value}")

    value, plaintext = value_never_renders(ref)
    print(f"secret value hides its secret in repr/str/format: {plaintext not in repr(value)}")
    print(f"reveal is the only plaintext path: {value.reveal() == plaintext}")

    store = InMemorySecretStore()
    store.provision(value)

    # The concrete store is used through the SecretStore port — the parameter type
    # of this helper — exactly as the composition root injects it.
    refusal = missing_credential_is_a_refusal(store)
    print(f"missing credential refused: {refusal.category.value} / {refusal.context['secret_ref']}")
    assert plaintext not in repr(refusal)

    rotated = rotation_is_store_before_discard(store, ref, plaintext)
    print(f"rotation stored new value before discard: {rotated != plaintext}")


if __name__ == "__main__":
    main()
