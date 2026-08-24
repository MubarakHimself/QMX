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

from qmb.config.fragments import (
    BMS_NAMESPACES,
    BMS_RECORD_KIND,
    BOOK_NAMESPACES,
    BOOK_RECORD_KIND,
    CONFIG_FRAGMENT_CLASS,
    FRAGMENT_FORMAT_VERSION,
    FRAGMENT_FORMAT_VERSION_1,
    FRAGMENT_KNOWN_FORMAT_VERSIONS,
    FRAGMENT_LINEAGE_EDGE_TYPE,
    SOURCE_BMS,
    SOURCE_BOOK,
    SOURCE_PRESET,
    ConfigFragment,
    fragment_identity,
    materialize_bms_fragment,
    materialize_book_fragment,
    materialize_condition_preset,
)

__all__ = [
    "BMS_NAMESPACES",
    "BMS_RECORD_KIND",
    "BOOK_NAMESPACES",
    "BOOK_RECORD_KIND",
    "CONFIG_FRAGMENT_CLASS",
    "FRAGMENT_FORMAT_VERSION",
    "FRAGMENT_FORMAT_VERSION_1",
    "FRAGMENT_KNOWN_FORMAT_VERSIONS",
    "FRAGMENT_LINEAGE_EDGE_TYPE",
    "LAYER_PRECEDENCE",
    "SOURCE_BMS",
    "SOURCE_BOOK",
    "SOURCE_PRESET",
    "ConfigFragment",
    "fingerprint_layers",
    "fragment_identity",
    "layers_identity",
    "materialize_bms_fragment",
    "materialize_book_fragment",
    "materialize_condition_preset",
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
