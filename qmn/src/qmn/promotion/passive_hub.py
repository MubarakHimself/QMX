"""Passive hub filesystem: write-only inbox and read-only published area.

The hub is a separate tree from the evidence-tier rooms (TN-3, DEC-0188).
Sandbox fragments land WriterId-scoped in ``hub-inbox``. The operator
``hub_publish`` act moves verified fragments into ``hub-published``. Promotion
pull reads only the published area. ``provenance = sandbox`` is refused at
publish and at pull. The only inbound crossings are the confined sandbox push
and the click-gated promotion pull. Evidence sync never writes the inbox.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Fingerprint, Ok, Result, WriterId, fingerprint_bytes, is_refusal

from qmn.promotion._refuse import clean_token, invalid, policy, unavailable
from qmn.promotion.hub import (
    HubArtifact,
    PublishedHub,
    publish_hub_fragment,
    pull_published_as_of,
)

__all__ = [
    "HUB_INBOX_NAME",
    "HUB_PUBLISHED_NAME",
    "INBOUND_CROSSINGS",
    "HubFragment",
    "InboxReceipt",
    "PassiveHubTree",
    "PublishReceipt",
    "accept_inbox_fragment",
    "publish_inbox_fragment",
    "pull_from_published",
    "refuse_evidence_sync_into_inbox",
    "refuse_inbound_crossing",
    "refuse_inbox_promotion_read",
    "refuse_published_direct_write",
]


HUB_INBOX_NAME: Final[str] = "hub-inbox"
HUB_PUBLISHED_NAME: Final[str] = "hub-published"
INBOUND_CROSSINGS: Final[frozenset[str]] = frozenset({"sandbox-push", "promotion-pull"})

_INBOX_READ_ID: Final[str] = "hub.inbox.read"
_PUBLISHED_WRITE_ID: Final[str] = "hub.published.write"
_CROSSING_ID: Final[str] = "hub.inbound_crossing"
_SYNC_INBOX_ID: Final[str] = "hub.sync_into_inbox"
_WRITER_SCOPE_ID: Final[str] = "hub.writer_scope"
_MAX_FRAGMENT_BYTES: Final[int] = 1 << 20


def refuse_inbound_crossing(*, crossing: object) -> Result[None]:
    """Refuse any inbound path other than sandbox push and promotion pull."""
    token = clean_token(crossing)
    if token is not None and token in INBOUND_CROSSINGS:
        return Ok(None)
    return policy(
        "crossing",
        "the only inbound crossings are confined sandbox push and click-gated "
        "promotion pull (TN-3, DEC-0188)",
        failure_id=_CROSSING_ID,
        given=repr(crossing),
        allowed=sorted(INBOUND_CROSSINGS),
    )


def refuse_inbox_promotion_read(*, source: object = None) -> Result[None]:
    """Promotion pull cannot read the write-only inbox."""
    return policy(
        "inbox",
        "the hub inbox is write-only; a promotion pull reads only the published "
        "area (DEC-0188, DEC-0205)",
        failure_id=_INBOX_READ_ID,
        given=repr(source),
    )


def refuse_published_direct_write(*, target: object = None) -> Result[None]:
    """The published area is read-only except via operator hub_publish."""
    return policy(
        "published",
        "the hub published area is read-only; fragments enter only through "
        "operator hub_publish (DEC-0188)",
        failure_id=_PUBLISHED_WRITE_ID,
        given=repr(target),
    )


def refuse_evidence_sync_into_inbox(*, target: object = None) -> Result[None]:
    """One-way evidence sync never writes the hub inbox; the inbox is not a room."""
    return policy(
        "inbox",
        "the one-way evidence sync never writes into the inbox, and the inbox is "
        "never a room (DEC-0188)",
        failure_id=_SYNC_INBOX_ID,
        given=repr(target),
    )


@dataclass(frozen=True, slots=True)
class HubFragment:
    """One WriterId-scoped inbox fragment awaiting operator publish."""

    artifact: HubArtifact
    writer: WriterId
    payload: bytes

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "artifact_key": self.artifact.artifact_key,
                "fp1": self.artifact.fp1.value,
                "provenance": self.artifact.provenance,
                "writer": list(self.writer.order_tuple()),
                "payload_bytes": len(self.payload),
            }
        )

    @classmethod
    def try_create(
        cls,
        *,
        artifact_key: object,
        fp1: object,
        provenance: object,
        writer: object,
        payload: object,
    ) -> Result[HubFragment]:
        artifact = HubArtifact.try_create(artifact_key=artifact_key, fp1=fp1, provenance=provenance)
        if is_refusal(artifact):
            return artifact
        if not isinstance(writer, WriterId):
            return invalid(
                "writer",
                "each hub fragment is WriterId-scoped",
                given=repr(type(writer).__name__),
                failure_id=_WRITER_SCOPE_ID,
            )
        if not isinstance(payload, (bytes, bytearray)):
            return invalid(
                "payload",
                "a hub fragment carries payload bytes",
                given=repr(type(payload).__name__),
            )
        body = bytes(payload)
        if len(body) > _MAX_FRAGMENT_BYTES:
            return policy(
                "payload",
                "a hub fragment exceeds the size cap",
                size=len(body),
                cap=_MAX_FRAGMENT_BYTES,
            )
        digest = fingerprint_bytes(body)
        if digest.value != artifact.value.fp1.value:
            return policy(
                "fp1",
                "hub publish verifies each fragment's fp1 against its payload (DEC-0188)",
                artifact_fp1=artifact.value.fp1.value,
                payload_fp1=digest.value,
            )
        key = _segment(artifact.value.artifact_key, field="artifact_key")
        if is_refusal(key):
            return key
        return Ok(cls(artifact=artifact.value, writer=writer, payload=body))


@dataclass(frozen=True, slots=True)
class InboxReceipt:
    """Write-only inbox accept — never a promotion-pull source."""

    artifact_key: str
    writer_scope: str
    provenance: str
    write_only: bool = True

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "artifact_key": self.artifact_key,
                "writer_scope": self.writer_scope,
                "provenance": self.provenance,
                "write_only": self.write_only,
            }
        )


@dataclass(frozen=True, slots=True)
class PublishReceipt:
    """Operator hub_publish moved a verified fragment into the published area."""

    artifact: HubArtifact
    writer_scope: str

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "artifact_key": self.artifact.artifact_key,
                "fp1": self.artifact.fp1.value,
                "provenance": self.artifact.provenance,
                "writer_scope": self.writer_scope,
            }
        )


class PassiveHubTree:
    """Filesystem hub under ``/var/lib/qmx/{hub-inbox,hub-published}``."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def inbox_root(self) -> Path:
        return self._root / HUB_INBOX_NAME

    @property
    def published_root(self) -> Path:
        return self._root / HUB_PUBLISHED_NAME

    def accept(self, fragment: HubFragment) -> Result[InboxReceipt]:
        """Sandbox push into the write-only WriterId-scoped inbox."""
        gated = refuse_inbound_crossing(crossing="sandbox-push")
        if is_refusal(gated):
            return gated
        path = self._inbox_path(fragment.writer, fragment.artifact.artifact_key)
        if is_refusal(path):
            return path
        payload = _fragment_bytes(fragment)
        written = _atomic_write(path.value, payload)
        if is_refusal(written):
            return written
        return Ok(
            InboxReceipt(
                artifact_key=fragment.artifact.artifact_key,
                writer_scope=_writer_dirname(fragment.writer),
                provenance=fragment.artifact.provenance,
            )
        )

    def publish(self, *, writer: WriterId, artifact_key: str) -> Result[PublishReceipt]:
        """Operator hub_publish: inbox → published, sandbox refused."""
        inbox = self._inbox_path(writer, artifact_key)
        if is_refusal(inbox):
            return inbox
        loaded = _load_fragment(inbox.value)
        if is_refusal(loaded):
            return loaded
        fragment = loaded.value
        published = publish_hub_fragment(fragment.artifact)
        if is_refusal(published):
            return published
        dest = self._published_path(fragment.artifact.artifact_key)
        if is_refusal(dest):
            return dest
        written = _atomic_write(dest.value, _fragment_bytes(fragment))
        if is_refusal(written):
            return written
        _unlink_contained(inbox.value)
        return Ok(
            PublishReceipt(
                artifact=published.value,
                writer_scope=_writer_dirname(writer),
            )
        )

    def published_hub(self) -> Result[PublishedHub]:
        """Read-only published area as the in-memory hub the pull already uses."""
        root = self.published_root
        if not root.exists():
            return Ok(PublishedHub(artifacts=()))
        if root.is_symlink():
            return policy("published", "refusing to follow a symlink at hub-published")
        artifacts: list[HubArtifact] = []
        for child in sorted(root.iterdir()):
            if child.is_symlink() or not child.is_file() or child.suffix != ".json":
                continue
            loaded = _load_fragment(child)
            if is_refusal(loaded):
                return loaded
            artifacts.append(loaded.value.artifact)
        return Ok(PublishedHub(artifacts=tuple(artifacts)))

    def write_published(self, fragment: object) -> Result[None]:
        """Closed: published is read-only from this door."""
        del fragment
        return refuse_published_direct_write(target=HUB_PUBLISHED_NAME)

    def read_inbox_for_promotion(self, *, writer: object, artifact_key: object) -> Result[None]:
        """Closed: promotion pull cannot source the inbox."""
        del writer, artifact_key
        return refuse_inbox_promotion_read(source=HUB_INBOX_NAME)

    def sync_into_inbox(self, payload: object) -> Result[None]:
        """Closed: evidence sync is not an inbound hub crossing."""
        del payload
        refused = refuse_inbound_crossing(crossing="evidence-sync")
        if is_refusal(refused):
            return refused
        return refuse_evidence_sync_into_inbox(target=HUB_INBOX_NAME)

    def _inbox_path(self, writer: WriterId, artifact_key: str) -> Result[Path]:
        scope = _writer_dirname(writer)
        key = _segment(artifact_key, field="artifact_key")
        if is_refusal(key):
            return key
        path = self.inbox_root / scope / f"{key.value}.json"
        return _contained_file(self._root, path)

    def _published_path(self, artifact_key: str) -> Result[Path]:
        key = _segment(artifact_key, field="artifact_key")
        if is_refusal(key):
            return key
        path = self.published_root / f"{key.value}.json"
        return _contained_file(self._root, path)


def accept_inbox_fragment(tree: object, fragment: object) -> Result[InboxReceipt]:
    """Sandbox push into a PassiveHubTree inbox."""
    hub = _as_tree(tree)
    if is_refusal(hub):
        return hub
    if not isinstance(fragment, HubFragment):
        return invalid(
            "fragment",
            "inbox accept takes a HubFragment",
            given=repr(type(fragment).__name__),
        )
    return hub.value.accept(fragment)


def publish_inbox_fragment(
    tree: object, *, writer: object, artifact_key: object
) -> Result[PublishReceipt]:
    """Operator hub_publish over the filesystem tree."""
    hub = _as_tree(tree)
    if is_refusal(hub):
        return hub
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "hub_publish names the WriterId-scoped inbox fragment",
            given=repr(type(writer).__name__),
            failure_id=_WRITER_SCOPE_ID,
        )
    key = _segment(artifact_key, field="artifact_key")
    if is_refusal(key):
        return key
    return hub.value.publish(writer=writer, artifact_key=key.value)


def pull_from_published(
    tree: object,
    *,
    artifact_keys: object,
    attested_fp1: object,
    template_fp1: object,
) -> Result[tuple[HubArtifact, ...]]:
    """Click-gated promotion pull — published area only, sandbox refused."""
    gated = refuse_inbound_crossing(crossing="promotion-pull")
    if is_refusal(gated):
        return gated
    hub = _as_tree(tree)
    if is_refusal(hub):
        return hub
    published = hub.value.published_hub()
    if is_refusal(published):
        return published
    return pull_published_as_of(
        published.value,
        artifact_keys=artifact_keys,
        attested_fp1=attested_fp1,
        template_fp1=template_fp1,
    )


def _as_tree(value: object) -> Result[PassiveHubTree]:
    if not isinstance(value, PassiveHubTree):
        return invalid(
            "tree",
            "passive hub operations require a PassiveHubTree",
            given=repr(type(value).__name__),
        )
    return Ok(value)


def _writer_dirname(writer: WriterId) -> str:
    joined = "\0".join(writer.order_tuple())
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _fragment_bytes(fragment: HubFragment) -> bytes:
    body = {
        "artifact_key": fragment.artifact.artifact_key,
        "fp1": fragment.artifact.fp1.value,
        "provenance": fragment.artifact.provenance,
        "writer": list(fragment.writer.order_tuple()),
        "payload_hex": fragment.payload.hex(),
    }
    return (json.dumps(body, sort_keys=True) + "\n").encode("utf-8")


def _load_fragment(path: Path) -> Result[HubFragment]:
    loaded = _read_capped(path)
    if is_refusal(loaded):
        return loaded
    try:
        body = json.loads(loaded.value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return unavailable("fragment", "hub fragment is not readable JSON")
    if not isinstance(body, dict):
        return unavailable("fragment", "hub fragment is an object")
    mapping = cast("Mapping[str, object]", body)
    writer_raw = mapping.get("writer")
    if not isinstance(writer_raw, list):
        return invalid(
            "writer",
            "hub fragment writer is a four-tuple",
            failure_id=_WRITER_SCOPE_ID,
        )
    items = cast("list[object]", writer_raw)
    if len(items) != 4:
        return invalid(
            "writer",
            "hub fragment writer is a four-tuple",
            failure_id=_WRITER_SCOPE_ID,
        )
    tokens: list[str] = []
    for item in items:
        if not isinstance(item, str):
            return invalid(
                "writer",
                "hub fragment writer tokens are strings",
                failure_id=_WRITER_SCOPE_ID,
            )
        tokens.append(item)
    writer = WriterId.try_create(tokens[0], tokens[1], tokens[2], tokens[3])
    if is_refusal(writer):
        return writer
    hex_payload = mapping.get("payload_hex")
    if not isinstance(hex_payload, str):
        return invalid("payload", "hub fragment payload_hex is a hex string")
    try:
        payload = bytes.fromhex(hex_payload)
    except ValueError:
        return invalid("payload", "hub fragment payload_hex is not valid hex")
    fp_raw = mapping.get("fp1")
    if not isinstance(fp_raw, str):
        return invalid("fp1", "hub fragment carries an fp1 fingerprint")
    parsed = Fingerprint.try_create(fp_raw)
    if is_refusal(parsed):
        return parsed
    return HubFragment.try_create(
        artifact_key=mapping.get("artifact_key"),
        fp1=parsed.value,
        provenance=mapping.get("provenance"),
        writer=writer.value,
        payload=payload,
    )


def _segment(value: object, *, field: str) -> Result[str]:
    token = clean_token(value)
    if token is None:
        return invalid(field, f"{field} is a non-empty path segment", given=repr(value))
    if token in {".", ".."} or "/" in token or "\\" in token or ":" in token:
        return policy(field, f"{field} is a single confined path segment", given=token)
    return Ok(token)


def _contained_dir(root: Path, path: Path) -> Result[Path]:
    try:
        resolved_root = root.resolve()
        resolved = path.resolve()
    except OSError:
        return unavailable("path", "hub path could not be resolved")
    if path.is_symlink() or resolved.is_symlink():
        return policy("path", "refusing to follow a symlink in the passive hub")
    if not resolved.is_relative_to(resolved_root):
        return policy("path", "hub path escaped the hub root")
    return Ok(path)


def _contained_file(root: Path, path: Path) -> Result[Path]:
    contained = _contained_dir(root, path.parent)
    if is_refusal(contained):
        return contained
    if path.is_symlink():
        return policy("path", "refusing to follow a symlink in the passive hub")
    try:
        resolved_root = root.resolve()
        resolved = path.resolve()
    except OSError:
        return unavailable("path", "hub path could not be resolved")
    if not resolved.is_relative_to(resolved_root):
        return policy("path", "hub path escaped the hub root")
    return Ok(path)


def _read_capped(path: Path) -> Result[bytes]:
    if path.is_symlink() or not path.is_file():
        return unavailable("path", "hub fragment is missing")
    data = path.read_bytes()
    if len(data) > _MAX_FRAGMENT_BYTES:
        return policy("payload", "hub fragment exceeds the size cap")
    return Ok(data)


def _atomic_write(path: Path, payload: bytes) -> Result[None]:
    if path.is_symlink():
        return policy("path", "refusing to follow a symlink at the hub dest")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return unavailable("path", "hub directory could not be created")
    tmp = path.parent / f".{path.name}.tmp-{os.getpid()}"
    if tmp.is_symlink():
        return policy("path", "refusing to follow a symlink at the hub temp")
    flags = (
        os.O_CREAT
        | os.O_EXCL
        | os.O_WRONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        fd = os.open(tmp, flags, 0o600)  # skylos: ignore[SKY-D215] contained hub fragment
    except OSError:
        return unavailable("path", "hub rejected the fragment write")
    try:
        view = memoryview(payload)
        offset = 0
        while offset < len(view):
            offset += os.write(fd, view[offset:])
    except OSError:
        os.close(fd)
        tmp.unlink(missing_ok=True)
        return unavailable("path", "hub rejected the fragment write")
    os.close(fd)
    try:
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        return unavailable("path", "hub rejected the fragment write")
    return Ok(None)


def _unlink_contained(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        return
    path.unlink(missing_ok=True)
