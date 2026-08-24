"""Run-config schema, layering, and compiler home (B-3).

Every run consumes exactly one fully-resolved, read-only, schema-validated
run-config. Layering is deterministic and pure: same inputs yield a
byte-identical resolved artifact. The artifact's fingerprint is the run-id
root and the ledger key, computed only by qmf-core ``fp1`` (DEC-0160).
"""

from __future__ import annotations

from typing import Final

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Result

__all__ = [
    "LAYER_PRECEDENCE",
    "fingerprint_layers",
    "layers_identity",
]

LAYER_PRECEDENCE: Final[tuple[str, ...]] = (
    "invocation-flags",
    "run-spec",
    "bms-fragment",
    "book-fragment",
    "workspace-defaults",
)


def layers_identity() -> dict[str, object]:
    """Identity-bearing compiler fields. Package SemVer is omitted."""
    return {"layer_precedence": LAYER_PRECEDENCE}


def fingerprint_layers() -> Result[Fingerprint]:
    """``fp1`` over the layering identity, computed only by qmf-core."""
    return fingerprint(layers_identity())
