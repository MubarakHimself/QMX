"""Versioned door wire vocabulary shared by evidence and powers (TN-17).

Integer-versioned like every other node artifact. Shapes for versioning,
refusal rendering, and provenance carriage align with QMA wire conventions
as an obligation — never an import (DEC-0202).
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from qmf.core.refusal import TypedRefusal

__all__ = [
    "AUTHORITY_LIVE",
    "AUTHORITY_REPLICATED",
    "AUTHORITY_SOURCES",
    "WIRE_FORMAT_VERSION",
    "refusal_wire_shape",
    "wire_identity",
]

WIRE_FORMAT_VERSION: Final[int] = 1

AUTHORITY_LIVE: Final[str] = "live-authoritative"
AUTHORITY_REPLICATED: Final[str] = "replicated-evidence"
AUTHORITY_SOURCES: Final[frozenset[str]] = frozenset({AUTHORITY_LIVE, AUTHORITY_REPLICATED})


def refusal_wire_shape(refusal: object) -> Mapping[str, object]:
    """Machine-readable refusal payload identical across doors (CT-04)."""
    if not isinstance(refusal, TypedRefusal):
        return MappingProxyType(
            {
                "wire_format_version": WIRE_FORMAT_VERSION,
                "ok": False,
                "category": "invalid input",
                "retryability": "no",
                "context": {"field": "refusal", "reason": "not a TypedRefusal"},
            }
        )
    body: dict[str, object] = {
        "wire_format_version": WIRE_FORMAT_VERSION,
        "ok": False,
        "category": refusal.category.value,
        "retryability": refusal.retryability.value,
        "context": dict(refusal.context),
    }
    if refusal.after_condition_descriptor is not None:
        body["after_condition_descriptor"] = refusal.after_condition_descriptor
    return MappingProxyType(body)


def wire_identity() -> Mapping[str, object]:
    """Identity-bearing wire constants (no SemVer)."""
    return MappingProxyType(
        {
            "wire_format_version": WIRE_FORMAT_VERSION,
            "authority_sources": tuple(sorted(AUTHORITY_SOURCES)),
            "refusal_fields": ("category", "retryability", "context"),
            "provenance_fields": (
                "authority_source",
                "source_time_ns",
                "receive_time_ns",
                "watermark_ns",
            ),
            "epoch_fields": ("boot_epoch", "composition_fp", "knowledge_time_ns"),
        }
    )
