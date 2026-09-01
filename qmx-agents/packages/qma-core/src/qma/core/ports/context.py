"""ContextCompiler port — per-daemon replaceable default (AD-1, AD-14)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from qma.core.ports.handles import EvidenceHandle

__all__ = ["ContextCompiler"]


@runtime_checkable
class ContextCompiler(Protocol):
    """Definitions-only ContextCompiler seam.

    The daemon's implementation occupies the per-daemon key only while no plugin
    binds it; exactly one plugin may replace that default at load time.

    Cardinality: singleton, scope key ``daemon``, replaceable default
    (see ``PORT_CONTRACTS``). Handle contents never enter a compiled window.
    """

    def compile_context(self, handles: Sequence[EvidenceHandle]) -> Mapping[str, object]:
        """Compile handle *references* only. Contents stay out of the window."""
        ...
