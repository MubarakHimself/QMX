"""Minimal ``qml.research`` helpers (Stories 49.5–49.6).

Parse/validate/lookup and a read-only Stage 0 LAYOUT-DEMO projection over
**cited bytes the host passed in**. No filesystem I/O, no threads, no process.
Collision resolution is ``(file_path, id)``. Eligible roles including
invalidation stay on Stage 0; GAP-0085 stays unfilled.

This module does **not** export ``Confluence`` / ``confluence`` (CT-34 remains
the registry kind). Stage 0 composition, if named, is ``graph``. It does
**not** mint ``research_ref`` (Epic 50), a registry row, a CT-16 producer, or
CT-33/CT-34 from DNA. Viewing cited seed is not a save.
"""

from __future__ import annotations

from qml.research.projection import (
    F_LABELS,
    F_SLOTS,
    GRAPH_COMPILE_TARGETS,
    GRAPH_PLANE,
    HYPOTHESIS_CLASSES,
    LAYOUT_DEMO_PACKAGE_ID,
    POPULATION_INGEST_SOURCES,
    POPULATION_INGEST_STARTED,
    PRODUCT_NOUNS,
    LayoutDemoProjection,
    compile_graph,
    complete_unresolved_f,
    mint_bot_from_projection,
    project_layout_demo,
    save_hypothesis,
    start_population_ingest,
)
from qml.research.vocab import (
    DICTIONARY_FIELDS,
    DictionaryEntry,
    resolve_dictionary_entry,
)

__all__ = [
    "DICTIONARY_FIELDS",
    "F_LABELS",
    "F_SLOTS",
    "GRAPH_COMPILE_TARGETS",
    "GRAPH_PLANE",
    "HYPOTHESIS_CLASSES",
    "LAYOUT_DEMO_PACKAGE_ID",
    "POPULATION_INGEST_SOURCES",
    "POPULATION_INGEST_STARTED",
    "PRODUCT_NOUNS",
    "DictionaryEntry",
    "LayoutDemoProjection",
    "compile_graph",
    "complete_unresolved_f",
    "mint_bot_from_projection",
    "project_layout_demo",
    "resolve_dictionary_entry",
    "save_hypothesis",
    "start_population_ingest",
]
