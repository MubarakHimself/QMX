"""Reference usage — CT-21 account bindings with opaque credentials (L27, AR-21).

Executable::

    python packages/qmf-venue/examples/account_binding_usage.py

Shows the things CT-21 / DEC-0136 / DEC-0140 pin down:

1. A credential is named by an OPAQUE minted :class:`~qmf.core.SecretRef`; a
   reference encoding account data (a venue, account, or environment token) is
   an ``invalid input`` refusal at construction — never stored, never echoed.
2. Binding identity is ``(VenueId, AccountId, role, world)``; the secret
   reference is occurrence/display-only and excluded from ``fp1``, so two
   bindings that differ only by credential fingerprint identically (a rotation
   never forks identity).
3. A cross-venue account, and a non-constructed secret handle, are each an
   ``invalid input`` refusal — value-or-refusal, never a raise (CT-04).
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Account,
    AccountRole,
    Result,
    SecretRef,
    TypedRefusal,
    VenueId,
    World,
    is_ok,
)
from qmf.venue import AccountBinding

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def opaque_reference_mints_and_encoding_refuses() -> str:
    """CT-21: opacity is validated AT CONSTRUCTION as an invalid-input refusal."""
    minted = _unwrap(SecretRef.try_create("sref-71a4c9e2d8b305"), "opaque secret reference")
    encoded = SecretRef.try_create("live:acct-123:password")
    if not isinstance(encoded, TypedRefusal):
        raise AssertionError("an encoding reference must refuse")
    _require(
        encoded.category.value == "invalid input",
        "a non-opaque reference is an invalid-input refusal",
    )
    _require(
        "acct-123" not in str(encoded.context),
        "rejected material is never echoed back in the refusal",
    )
    _ = minted
    return encoded.category.value


def rotation_never_forks_identity() -> bool:
    """Identity is (venue, account, role, world); the secret ref is excluded from fp1."""
    venue = _unwrap(VenueId.try_create("venue-ctrader-demo"), "venue")
    account = _unwrap(Account.try_create("acct-001", venue, AccountRole.DEMO), "account")
    before = _unwrap(
        AccountBinding.try_create(
            venue,
            account,
            World.LIVE,
            _unwrap(SecretRef.try_create("sref-71a4c9e2d8b305"), "ref-A"),
        ),
        "binding before rotation",
    )
    after = _unwrap(
        AccountBinding.try_create(
            venue,
            account,
            World.LIVE,
            _unwrap(SecretRef.try_create("sref-e2d3c4b5a60718"), "ref-B"),
        ),
        "binding after rotation",
    )
    _require(before.fp1_identity() == after.fp1_identity(), "rotation must not fork identity")
    _require(
        _unwrap(before.fingerprint(), "fp before") == _unwrap(after.fingerprint(), "fp after"),
        "the two bindings fingerprint identically",
    )
    _require("secret" not in str(before.fp1_identity()).casefold(), "no secret field in fp1")
    return True


def cross_venue_account_refuses() -> str:
    """An account that does not belong to the binding's venue is invalid input."""
    venue = _unwrap(VenueId.try_create("venue-ctrader-demo"), "venue")
    other = _unwrap(VenueId.try_create("venue-other-live"), "other venue")
    foreign = _unwrap(Account.try_create("acct-001", other, AccountRole.DEMO), "foreign account")
    refused = AccountBinding.try_create(
        venue, foreign, World.LIVE, _unwrap(SecretRef.try_create("sref-71a4c9e2d8b305"), "ref")
    )
    if not isinstance(refused, TypedRefusal):
        raise AssertionError("a cross-venue account must refuse")
    return refused.category.value


def main() -> None:
    print(f"encoding secret reference refused: {opaque_reference_mints_and_encoding_refuses()}")
    print(f"rotation never forks identity: {rotation_never_forks_identity()}")
    print(f"cross-venue account refused: {cross_venue_account_refuses()}")
    print("account binding usage ok")


if __name__ == "__main__":
    main()
