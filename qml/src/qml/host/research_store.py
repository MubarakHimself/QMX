"""QML authoring composition-root blob store under ``research_root`` (Story 50.3).

Persists only canonical Stage 0 bytes keyed by ``research_ref``. Distinct from
seed ``root_path``. Not daemon sqlite, not QMA staging, not a new COMP store,
not Stats, and not a second AD-4 include/exclude. COMP-QMA-DAEMON must not write
this root and must not bind a second CT-44 ``source_id`` in v1.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

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
            "research_root",
            "COMP-QMA-DAEMON must not write the research root in v1",
        )
    root = _admit_root(research_root)
    if is_refusal(root):
        return root
    ref = _admit_ref(research_ref)
    if is_refusal(ref):
        return ref
    if not isinstance(canonical_bytes, (bytes, bytearray)):
        return invalid(
            "canonical_bytes",
            "the host persists only canonical Stage 0 bytes",
            given=type(canonical_bytes).__name__,
        )
    payload = bytes(canonical_bytes)
    path = research_blob_path(root.value, ref.value)
    if is_refusal(path):
        return path
    try:
        root.value.mkdir(parents=True, exist_ok=True)
        path.value.write_bytes(payload)
    except OSError as exc:
        return invalid(
            "research_root",
            "the host could not persist canonical research bytes",
            given=type(exc).__name__,
            path=str(path.value),
        )
    return Ok(
        PersistedHypothesis(
            research_root=root.value,
            path=path.value,
            canonical_bytes=payload,
            research_ref=ref.value,
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
    try:
        if not path.value.is_file():
            return invalid(
                "research_ref",
                "no canonical research blob is stored under research_root for that ref",
                research_ref=str(getattr(research_ref, "value", research_ref)),
            )
        return Ok(path.value.read_bytes())
    except OSError as exc:
        return invalid(
            "research_root",
            "the host could not read canonical research bytes",
            given=type(exc).__name__,
        )


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


def _admit_root(research_root: object) -> Result[Path]:
    if isinstance(research_root, Path):
        root = research_root
    elif isinstance(research_root, str) and research_root.strip() != "":
        root = Path(research_root)
    else:
        return invalid(
            "research_root",
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
