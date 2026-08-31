"""QMA content addressing — one construction only (AD-3; DEC-0302; FR-Q04).

A content-addressed id is ``fp1`` over the value's canonical JSON. A tree digest
is ``fp1`` over a canonical manifest of per-file ``fp1`` values. Both call the
single imported ``qmf-core`` implementation; no second hash or Merkle scheme.
"""

from __future__ import annotations

from collections.abc import Mapping

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import RefusalCategory, Result, Retryability, TypedRefusal, is_refusal

__all__ = [
    "content_address",
    "tree_digest",
]


def content_address(value: object) -> Result[Fingerprint]:
    """Content-addressed id: imported ``fp1`` over the value's canonical JSON."""
    return fingerprint(value)


def tree_digest(file_fingerprints: Mapping[str, str | Fingerprint]) -> Result[Fingerprint]:
    """Tree digest: ``fp1`` over a canonical manifest of per-file ``fp1`` values.

    ``file_fingerprints`` maps relative path → ``fp1:sha256:<hex>`` (string or
    :class:`~qmf.core.fingerprint.Fingerprint`). Paths must be non-empty strings.
    The manifest is the object itself; ``fp1`` sorts keys lexicographically, so
    callers need not pre-sort.
    """
    manifest: dict[str, str] = {}
    for path, fp in file_fingerprints.items():
        if path.strip() == "":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "path",
                    "reason": "tree digest paths are non-empty strings",
                    "given": repr(path),
                },
            )
        if isinstance(fp, Fingerprint):
            token = fp.value
        else:
            parsed = Fingerprint.try_create(fp)
            if is_refusal(parsed):
                return parsed
            token = parsed.value.value
        if path in manifest:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "path",
                    "reason": "duplicate path in tree digest manifest",
                    "path": path,
                },
            )
        manifest[path] = token
    return fingerprint(manifest)
