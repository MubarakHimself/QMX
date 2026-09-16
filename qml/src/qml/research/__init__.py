"""Minimal ``qml.research`` vocabulary helpers (Story 49.5).

Parse/validate/lookup over **cited bytes the host passed in**. No filesystem
I/O, no threads, no process. Collision resolution is ``(file_path, id)``.
Eligible roles including invalidation stay on Stage 0; GAP-0085 stays unfilled.

This module does **not** export ``Confluence`` / ``confluence`` (CT-34 remains
the registry kind). It does **not** mint ``research_ref`` (Epic 50), a registry
row, or a CT-16 producer.
"""

from __future__ import annotations

from qml.research.vocab import (
    DICTIONARY_FIELDS,
    DictionaryEntry,
    resolve_dictionary_entry,
)

__all__ = [
    "DICTIONARY_FIELDS",
    "DictionaryEntry",
    "resolve_dictionary_entry",
]
