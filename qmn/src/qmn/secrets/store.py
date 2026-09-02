"""Two-layer VPS SecretStore (TN-12 / DEC-0197).

Bootstrap material arrives from systemd ``CREDENTIALS_DIRECTORY`` (host-key
sealed ``LoadCredentialEncrypted``). Rotated material is AEAD ciphertext under
the KEK at ``/var/lib/qmx/state``. The store implements qmf-core's SecretStore
port (read + atomic replace) and refuses to construct a venue-session holder
off the roster VPS machine tuple.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Final, Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from qmf.core.refusal import Ok, Result, Retryability, is_ok, is_refusal
from qmf.core.secret import SecretRef, SecretValue

from qmn.secrets._refuse import ROTATION_AFTER_CONDITION, invalid, policy, unavailable
from qmn.secrets.holders import (
    KEK_SLOT,
    extra_holders,
    refuse_holder_scope,
    refuse_unknown_holder,
    slot_in_holder,
)
from qmn.secrets.rotation import RotationGate

__all__ = [
    "AEAD_NONCE_SIZE",
    "BLOB_MAGIC",
    "KEK_SIZE",
    "ROTATED_STATE_DIRNAME",
    "BlobStore",
    "FilesystemBlobStore",
    "NodeSecretStore",
    "NonceSource",
    "os_aead_nonce",
    "try_create_secret_store",
]

KEK_SIZE: Final[int] = 32
AEAD_NONCE_SIZE: Final[int] = 12
BLOB_MAGIC: Final[bytes] = b"QMN1"
ROTATED_STATE_DIRNAME: Final[str] = "rotated"
_MAX_BLOB_BYTES: Final[int] = 1 << 20


class NonceSource(Protocol):
    """Injected AEAD nonce factory (entropy is not read at import)."""

    def __call__(self, size: int) -> bytes: ...


class BlobStore(Protocol):
    """Durable rotated-ciphertext backend (no plaintext)."""

    def write_atomic(self, name: str, blob: bytes) -> Result[None]: ...

    def read(self, name: str) -> Result[bytes]: ...

    def exists(self, name: str) -> bool: ...


def os_aead_nonce(size: int = AEAD_NONCE_SIZE) -> bytes:
    """Production nonce source, injected at the composition root."""
    return os.urandom(size)  # ambient-scan: allow — AEAD nonce for rotated material (TN-12)


class FilesystemBlobStore:
    """Atomic ciphertext files under ``/var/lib/qmx/state/rotated``."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def write_atomic(self, name: str, blob: bytes) -> Result[None]:
        if ".." in name or "/" in name or "\\" in name:
            return invalid("rotated", "rotated blob name is a single path segment")
        self._directory.mkdir(parents=True, exist_ok=True)
        dest = self._directory / name
        if dest.is_symlink():
            return policy("rotated", "refusing to follow a symlink at the rotated path")
        tmp = self._directory / f".{name}.tmp-{os.getpid()}"
        if tmp.is_symlink():
            return policy("rotated", "refusing to follow a symlink at the rotated temp")
        try:
            fd = os.open(  # skylos: ignore[SKY-D215] contained rotated ciphertext
                tmp,
                os.O_CREAT
                | os.O_EXCL
                | os.O_WRONLY
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_BINARY", 0),
                0o600,
            )
        except OSError:
            return unavailable(
                "rotated",
                "the rotated store rejected the new ciphertext",
                failure_id="secrets.rotation.store_failed",
                retryability=Retryability.AFTER_CONDITION,
                after_condition_descriptor=ROTATION_AFTER_CONDITION,
                secret_ref=name,
            )
        try:
            view = memoryview(blob)
            offset = 0
            while offset < len(view):
                offset += os.write(fd, view[offset:])
        except OSError:
            os.close(fd)
            tmp.unlink(missing_ok=True)
            return unavailable(
                "rotated",
                "the rotated store rejected the new ciphertext",
                failure_id="secrets.rotation.store_failed",
                retryability=Retryability.AFTER_CONDITION,
                after_condition_descriptor=ROTATION_AFTER_CONDITION,
                secret_ref=name,
            )
        os.close(fd)
        try:
            os.replace(tmp, dest)
        except OSError:
            tmp.unlink(missing_ok=True)
            return unavailable(
                "rotated",
                "the rotated store rejected the new ciphertext",
                failure_id="secrets.rotation.store_failed",
                retryability=Retryability.AFTER_CONDITION,
                after_condition_descriptor=ROTATION_AFTER_CONDITION,
                secret_ref=name,
            )
        return Ok(None)

    def read(self, name: str) -> Result[bytes]:
        dest = self._directory / name
        if dest.is_symlink() or not dest.is_file():
            return unavailable(
                "rotated",
                "rotated ciphertext is missing",
                failure_id="secrets.store.missing",
                secret_ref=name,
            )
        data = dest.read_bytes()
        if len(data) > _MAX_BLOB_BYTES:
            return policy("rotated", "rotated ciphertext exceeds the size cap")
        return Ok(data)

    def exists(self, name: str) -> bool:
        dest = self._directory / name
        return dest.is_file() and not dest.is_symlink()


class NodeSecretStore:
    """Holder-scoped SecretStore: read + atomic replace, references never values."""

    def __init__(
        self,
        *,
        holder: str,
        kek: bytes,
        catalog: Mapping[SecretRef, str],
        nonce_source: NonceSource,
        rotated: BlobStore,
        bootstrap: Mapping[str, bytes],
        gate: RotationGate,
    ) -> None:
        self._holder = holder
        self._aead = ChaCha20Poly1305(kek)
        self._catalog = dict(catalog)
        self._nonce_source = nonce_source
        self._rotated = rotated
        self._bootstrap = dict(bootstrap)
        self._gate = gate

    @property
    def holder(self) -> str:
        """The one named holder this instance may resolve."""
        return self._holder

    def is_set(self, ref: SecretRef) -> bool:
        """Presence metadata only — never the value."""
        slot = self._catalog.get(ref)
        if slot is None:
            return False
        return self._rotated.exists(_blob_name(ref)) or slot in self._bootstrap

    def presence(self) -> Mapping[str, bool]:
        """``is_set`` for every catalogued reference (reference ids as keys)."""
        return MappingProxyType({ref.value: self.is_set(ref) for ref in self._catalog})

    def read(self, ref: SecretRef, /) -> Result[SecretValue]:
        scoped = self._scope(ref)
        if is_refusal(scoped):
            return scoped
        blob_name = _blob_name(ref)
        if self._rotated.exists(blob_name):
            loaded = self._rotated.read(blob_name)
            if is_refusal(loaded):
                return unavailable(
                    "credential",
                    "the credential is missing, expired, or rejected at the secret store",
                    failure_id="secrets.store.missing",
                    secret_ref=ref.value,
                )
            opened = self._decrypt(ref, loaded.value)
            if is_refusal(opened):
                return opened
            return _secret_value(ref, opened.value)
        slot = self._catalog[ref]
        raw = self._bootstrap.get(slot)
        if raw is None:
            return unavailable(
                "credential",
                "the credential is missing, expired, or rejected at the secret store",
                failure_id="secrets.store.missing",
                secret_ref=ref.value,
            )
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return unavailable(
                "credential",
                "the credential is missing, expired, or rejected at the secret store",
                failure_id="secrets.store.missing",
                secret_ref=ref.value,
            )
        return _secret_value(ref, text)

    def atomic_replace(self, ref: SecretRef, new_value: SecretValue, /) -> Result[SecretRef]:
        scoped = self._scope(ref)
        if is_refusal(scoped):
            return scoped
        if new_value.ref != ref:
            return invalid(
                "new_value",
                "the new secret's reference does not match the credential reference",
                secret_ref=ref.value,
            )
        acquired = self._gate.acquire(ref)
        if is_refusal(acquired):
            return acquired
        try:
            sealed = self._encrypt(ref, new_value.reveal())
            stored = self._rotated.write_atomic(_blob_name(ref), sealed)
            if is_refusal(stored):
                return unavailable(
                    "rotation_store",
                    "the new secret failed to store after rotation; the old "
                    "material is kept undiscarded",
                    failure_id="secrets.rotation.store_failed",
                    retryability=Retryability.AFTER_CONDITION,
                    after_condition_descriptor=ROTATION_AFTER_CONDITION,
                    secret_ref=ref.value,
                    alarm=True,
                )
            return Ok(ref)
        finally:
            self._gate.release(ref)

    def __repr__(self) -> str:
        return (
            f"NodeSecretStore(holder={self._holder!r}, "
            f"refs={sorted(ref.value for ref in self._catalog)!r})"
        )

    def _scope(self, ref: SecretRef) -> Result[None]:
        slot = self._catalog.get(ref)
        if slot is None:
            return unavailable(
                "credential",
                "the credential is missing, expired, or rejected at the secret store",
                failure_id="secrets.store.missing",
                secret_ref=ref.value,
            )
        if slot == KEK_SLOT:
            return refuse_holder_scope(holder=self._holder, slot=slot, secret_ref=ref.value)
        if not slot_in_holder(self._holder, slot):
            return refuse_holder_scope(holder=self._holder, slot=slot, secret_ref=ref.value)
        return Ok(None)

    def _encrypt(self, ref: SecretRef, plaintext: str) -> bytes:
        nonce = self._nonce_source(AEAD_NONCE_SIZE)
        ciphertext = self._aead.encrypt(nonce, plaintext.encode("utf-8"), ref.value.encode("utf-8"))
        return BLOB_MAGIC + nonce + ciphertext

    def _decrypt(self, ref: SecretRef, blob: bytes) -> Result[str]:
        if not blob.startswith(BLOB_MAGIC) or len(blob) < 4 + AEAD_NONCE_SIZE:
            return unavailable(
                "credential",
                "the credential is missing, expired, or rejected at the secret store",
                failure_id="secrets.store.missing",
                secret_ref=ref.value,
            )
        nonce = blob[4 : 4 + AEAD_NONCE_SIZE]
        ciphertext = blob[4 + AEAD_NONCE_SIZE :]
        try:
            plaintext = self._aead.decrypt(nonce, ciphertext, ref.value.encode("utf-8"))
        except (InvalidTag, ValueError):
            return unavailable(
                "credential",
                "the credential is missing, expired, or rejected at the secret store",
                failure_id="secrets.store.missing",
                secret_ref=ref.value,
            )
        try:
            return Ok(plaintext.decode("utf-8"))
        except UnicodeDecodeError:
            return unavailable(
                "credential",
                "the credential is missing, expired, or rejected at the secret store",
                failure_id="secrets.store.missing",
                secret_ref=ref.value,
            )


def try_create_secret_store(
    *,
    machine: str,
    roster_vps_machine: str,
    holder: str,
    kek: object,
    catalog: Mapping[object, object],
    nonce_source: NonceSource,
    rotated: BlobStore,
    bootstrap: Mapping[str, bytes] | None = None,
    gate: RotationGate | None = None,
) -> Result[NodeSecretStore]:
    """Bind one named holder onto the two-layer VPS store."""
    extra = extra_holders((holder,))
    if extra:
        return refuse_unknown_holder(holder)
    if machine != roster_vps_machine:
        return policy(
            "host",
            "SecretStore refuses to construct a secret holder off the roster VPS machine tuple",
            failure_id="secrets.store.off_host",
            holder=holder,
        )
    if not isinstance(kek, bytes) or len(kek) != KEK_SIZE:
        return invalid("kek", "the key-encryption key is 32 bytes")
    bound: dict[SecretRef, str] = {}
    for ref, slot in catalog.items():
        if not isinstance(ref, SecretRef):
            return invalid("catalog", "catalog keys are SecretRef values")
        if not isinstance(slot, str) or slot.strip() == "":
            return invalid("catalog", "catalog values are systemd-creds slot names")
        bound[ref] = slot
        if slot != KEK_SLOT and not slot_in_holder(holder, slot):
            return refuse_holder_scope(holder=holder, slot=slot, secret_ref=ref.value)
    return Ok(
        NodeSecretStore(
            holder=holder,
            kek=kek,
            catalog=bound,
            nonce_source=nonce_source,
            rotated=rotated,
            bootstrap=dict(bootstrap or {}),
            gate=gate if gate is not None else RotationGate(),
        )
    )


def _blob_name(ref: SecretRef) -> str:
    digest = hashlib.sha256(ref.value.encode("utf-8")).hexdigest()
    return f"{digest}.bin"


def _secret_value(ref: SecretRef, plaintext: str) -> Result[SecretValue]:
    built = SecretValue.try_create(ref, plaintext)
    if is_ok(built):
        return built
    return unavailable(
        "credential",
        "the credential is missing, expired, or rejected at the secret store",
        failure_id="secrets.store.missing",
        secret_ref=ref.value,
    )
