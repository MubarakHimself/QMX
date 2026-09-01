"""Default ContextCompiler — handle references only (AD-14; FR-Q53)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType

from qma.core.ports.handles import EvidenceHandle, context_entries_for_handles

__all__ = ["DefaultContextCompiler"]


class DefaultContextCompiler:
    """Daemon default ContextCompiler. Handle contents never enter the window."""

    def compile_context(self, handles: Sequence[EvidenceHandle]) -> Mapping[str, object]:
        entries = [dict(entry) for entry in context_entries_for_handles(handles)]
        return MappingProxyType(
            {
                "handles": entries,
                "contents_in_context": False,
            }
        )
