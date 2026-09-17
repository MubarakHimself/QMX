"""QML authoring composition-root blob store under ``research_root`` (Story 50.3).

Persists only canonical Stage 0 bytes keyed by ``research_ref``. Distinct from
seed ``root_path``. Not daemon sqlite, not QMA staging, not a new COMP store,
not Stats, and not a second AD-4 include/exclude. COMP-QMA-DAEMON must not write
this root and must not bind a second CT-44 ``source_id`` in v1.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qml._refuse import invalid, policy
from qml.research.stage0 import Hypothesis, SavedHypothesis, save_authored_hypothesis

__all__ = [
    "QMA_BINDS_SECOND_CT44_OVER_RESEARCH_ROOT_V1",
    "QMA_WRITES_RESEARCH_ROOT",
    "RESEARCH_ROOT_IS_QMA_SETTING",
    "RESEARCH_ROOT_IS_SEED_ROOT",
    "PersistedHypothesis",
    "persist_research_blob",
    "read_research_blob",
    "research_blob_path",
    "save_research_hypothesis",
]

# AD-8 / AD-21 ownership law — QMA does not write or re-bind this store in v1.
QMA_WRITES_RESEARCH_ROOT: Final[bool] = False
RESEARCH_ROOT_IS_QMA_SETTING: Final[bool] = False
RESEARCH_ROOT_IS_SEED_ROOT: Final[bool] = False
QMA_BINDS_SECOND_CT44_OVER_RESEARCH_ROOT_V1: Final[bool] = False

_FIELD_RESEARCH_ROOT: Final[str] = "research_root"
_SYMLINK_ROOT_REASON: Final[str] = "refusing to follow a symlink at research_root"
_SYMLINK_WRITE_REASON: Final[str] = "refusing to follow a symlink or write outside research_root"
_PERSIST_FAIL_REASON: Final[str] = "the host could not persist canonical research bytes"


@dataclass(frozen=True, slots=True)
class PersistedHypothesis:
    """Host-persisted Stage 0 blob: canonical bytes under ``research_root``."""

    research_root: Path
    path: Path
    canonical_bytes: bytes
    research_ref: Fingerprint


def research_blob_path(research_root: object, research_ref: object) -> Result[Path]:
    """Resolve the blob path for a ``research_ref`` under ``research_root``."""
    root = _admit_root(research_root)
    if is_refusal(root):
        return root
    ref = _admit_ref(research_ref)
    if is_refusal(ref):
        return ref
    # Filesystem-safe key derived from the fp1 string (colons are not path-safe).
    name = ref.value.value.replace(":", "-")
    return Ok(root.value / name)


def persist_research_blob(
    *,
    research_root: object,
    research_ref: object,
    canonical_bytes: object,
) -> Result[PersistedHypothesis]:
    """Persist only the canonical Stage 0 bytes keyed by ``research_ref``."""
    if QMA_WRITES_RESEARCH_ROOT:
        return policy(
            _FIELD_RESEARCH_ROOT,
            "COMP-QMA-DAEMON must not write the research root in v1",
        )
    prepared = _prepare_persist(research_root, research_ref, canonical_bytes)
    if is_refusal(prepared):
        return prepared
    root, ref, payload, path = prepared.value
    written = _write_research_blob(root=root, path=path, payload=payload)
    if is_refusal(written):
        return written
    return Ok(
        PersistedHypothesis(
            research_root=root,
            path=path,
            canonical_bytes=payload,
            research_ref=ref,
        )
    )


def read_research_blob(
    *,
    research_root: object,
    research_ref: object,
) -> Result[bytes]:
    """Read previously persisted canonical bytes. Host I/O only."""
    path = research_blob_path(research_root, research_ref)
    if is_refusal(path):
        return path
    return _read_blob_file(path.value, research_ref)


def save_research_hypothesis(
    hypothesis: object,
    *,
    research_root: object,
) -> Result[PersistedHypothesis]:
    """Explicit QML authoring save: mint bytes + ref, then persist under research_root."""
    if not isinstance(hypothesis, Hypothesis):
        return invalid(
            "hypothesis",
            "the host saves an authored Stage 0 Hypothesis; viewing cited seed "
            "mints no research_ref",
            given=type(hypothesis).__name__,
        )
    saved = save_authored_hypothesis(hypothesis)
    if is_refusal(saved):
        return saved
    blob: SavedHypothesis = saved.value
    return persist_research_blob(
        research_root=research_root,
        research_ref=blob.research_ref,
        canonical_bytes=blob.canonical_bytes,
    )


def _read_blob_file(path: Path, research_ref: object) -> Result[bytes]:
    try:
        if not path.is_file():
            return invalid(
                "research_ref",
                "no canonical research blob is stored under research_root for that ref",
                research_ref=str(getattr(research_ref, "value", research_ref)),
            )
        return Ok(path.read_bytes())
    except OSError as exc:
        return invalid(
            _FIELD_RESEARCH_ROOT,
            "the host could not read canonical research bytes",
            given=type(exc).__name__,
        )


def _prepare_persist(
    research_root: object,
    research_ref: object,
    canonical_bytes: object,
) -> Result[tuple[Path, Fingerprint, bytes, Path]]:
    admitted = _admit_persist_inputs(research_root, research_ref, canonical_bytes)
    if is_refusal(admitted):
        return admitted
    root, ref, payload = admitted.value
    path = research_blob_path(root, ref)
    if is_refusal(path):
        return path
    return Ok((root, ref, payload, path.value))


def _admit_persist_inputs(
    research_root: object,
    research_ref: object,
    canonical_bytes: object,
) -> Result[tuple[Path, Fingerprint, bytes]]:
    root = _admit_root(research_root)
    if is_refusal(root):
        return root
    ref = _admit_ref(research_ref)
    if is_refusal(ref):
        return ref
    payload = _admit_canonical_bytes(canonical_bytes)
    if is_refusal(payload):
        return payload
    return Ok((root.value, ref.value, payload.value))


def _admit_canonical_bytes(canonical_bytes: object) -> Result[bytes]:
    if isinstance(canonical_bytes, (bytes, bytearray)):
        return Ok(bytes(canonical_bytes))
    return invalid(
        "canonical_bytes",
        "the host persists only canonical Stage 0 bytes",
        given=type(canonical_bytes).__name__,
    )


def _persist_os_error(path: Path, exc: OSError) -> TypedRefusal:
    return invalid(
        _FIELD_RESEARCH_ROOT,
        _PERSIST_FAIL_REASON,
        given=type(exc).__name__,
        path=str(path),
    )


def _ensure_research_root(root: Path) -> Result[Path]:
    """Create ``research_root`` without following a symlink leaf."""
    if root.is_symlink():
        return policy(_FIELD_RESEARCH_ROOT, _SYMLINK_ROOT_REASON)
    created = _mkdir_research_root(root)
    if is_refusal(created):
        return created
    if root.is_symlink() or not root.is_dir():
        return policy(_FIELD_RESEARCH_ROOT, _SYMLINK_ROOT_REASON)
    return Ok(root)


def _mkdir_research_root(root: Path) -> Result[None]:
    try:
        if root.exists() and not root.is_dir():
            return invalid(
                _FIELD_RESEARCH_ROOT,
                "research_root must be a directory",
                given=str(root),
            )
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _persist_os_error(root, exc)
    return Ok(None)


def _contain_under_root(path: Path, root: Path) -> Result[Path]:
    try:
        resolved = Path(os.path.realpath(path))
        root_real = Path(os.path.realpath(root))
    except OSError as exc:
        return _persist_os_error(path, exc)
    if path.is_symlink() or not resolved.is_relative_to(root_real):
        return policy(_FIELD_RESEARCH_ROOT, _SYMLINK_WRITE_REASON)
    return Ok(root_real)


def _prepare_write_tmp(path: Path, root_real: Path) -> Result[Path]:
    tmp = path.parent / f".{path.name}.write-{os.getpid()}"
    try:
        tmp_resolved = Path(os.path.realpath(tmp))
    except OSError as exc:
        return _persist_os_error(tmp, exc)
    if tmp.is_symlink() or not tmp_resolved.is_relative_to(root_real):
        return policy(_FIELD_RESEARCH_ROOT, _SYMLINK_WRITE_REASON)
    if tmp.exists() or tmp.is_symlink():
        if tmp.is_dir() and not tmp.is_symlink():
            return policy(_FIELD_RESEARCH_ROOT, _SYMLINK_WRITE_REASON)
        tmp.unlink()
    return Ok(tmp)


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    offset = 0
    while offset < len(view):
        offset += os.write(fd, view[offset:])


def _exclusive_replace(tmp: Path, path: Path, payload: bytes) -> Result[None]:
    try:
        # getattr keeps the "O_NOFOLLOW" token on this open so SKY-D324 sees
        # the no-follow flag; Windows has no O_NOFOLLOW (value 0).
        fd = os.open(  # skylos: ignore[SKY-D215] contained, no-follow, exclusive create
            tmp,
            os.O_CREAT
            | os.O_EXCL
            | os.O_WRONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_BINARY", 0),
            0o600,
        )
    except OSError as exc:
        return _persist_os_error(path, exc)
    try:
        try:
            _write_all(fd, payload)
        finally:
            os.close(fd)
        if path.is_symlink():
            tmp.unlink(missing_ok=True)
            return policy(_FIELD_RESEARCH_ROOT, _SYMLINK_WRITE_REASON)
        os.replace(tmp, path)
    except OSError as exc:
        if tmp.exists() or tmp.is_symlink():
            tmp.unlink(missing_ok=True)
        return _persist_os_error(path, exc)
    return Ok(None)


def _write_research_blob(*, root: Path, path: Path, payload: bytes) -> Result[None]:
    """Exclusive no-follow create via sibling temp, then replace (SKY-D324)."""
    ensured = _ensure_research_root(root)
    if is_refusal(ensured):
        return ensured
    root_real = _contain_write_target(path, root)
    if is_refusal(root_real):
        return root_real
    tmp = _prepare_write_tmp(path, root_real.value)
    if is_refusal(tmp):
        return tmp
    return _exclusive_replace(tmp.value, path, payload)


def _contain_write_target(path: Path, root: Path) -> Result[Path]:
    root_real = _contain_under_root(path, root)
    if is_refusal(root_real):
        return root_real
    if path.exists() and (path.is_symlink() or not path.is_file()):
        return policy(_FIELD_RESEARCH_ROOT, _SYMLINK_WRITE_REASON)
    return Ok(root_real.value)


def _admit_root(research_root: object) -> Result[Path]:
    if isinstance(research_root, Path):
        root = research_root
    elif isinstance(research_root, str) and research_root.strip() != "":
        root = Path(research_root)
    else:
        return invalid(
            _FIELD_RESEARCH_ROOT,
            "research_root is a filesystem path distinct from seed root_path; "
            "it is not a QMA daemon / research-corpus setting",
            given=repr(research_root),
            is_qma_setting=RESEARCH_ROOT_IS_QMA_SETTING,
            is_seed_root=RESEARCH_ROOT_IS_SEED_ROOT,
        )
    return Ok(root)


def _admit_ref(research_ref: object) -> Result[Fingerprint]:
    if isinstance(research_ref, Fingerprint):
        return Ok(research_ref)
    parsed = Fingerprint.try_create(research_ref)
    if is_refusal(parsed):
        return invalid(
            "research_ref",
            "research_ref is an fp1-shaped fingerprint string",
            given=repr(research_ref),
        )
    return Ok(parsed.value)
