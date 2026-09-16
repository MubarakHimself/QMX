"""Public ``qml.research`` Stage 0 mill (Stories 49.5–50.x).

Parse/validate/lookup and a read-only Stage 0 LAYOUT-DEMO projection over
**cited bytes the host passed in**, plus Stage 0 hypothesis types on QML's own
``RESEARCH_FORMAT_VERSION`` ladder. No filesystem I/O, no threads, no process.
Collision resolution is ``(file_path, id)``. Eligible roles including
invalidation stay on Stage 0; GAP-0085 stays unfilled.

This module does **not** export ``Confluence`` / ``confluence`` (CT-34 remains
the registry kind). Stage 0 composition is ``graph``. Viewing cited seed is not
a save. Hosts persist; QMA does not write research identity.
"""

from __future__ import annotations

from qml.research.projection import (
    GRAPH_COMPILE_TARGETS,
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
from qml.research.stage0 import (
    F_LABELS,
    F_SLOTS,
    GRAPH_MEANING_KINDS,
    GRAPH_PLANE,
    HYPOTHESIS_CLASSES,
    HYPOTHESIS_ORIGINS,
    RESEARCH_CONTRACT_CLASS,
    RESEARCH_FORMAT_VERSION,
    RESEARCH_KNOWN_FORMAT_VERSIONS,
    RESEARCH_LADDER,
    STAGE0_CITED_BY_GOVERNED_EVIDENCE,
    STAGE0_EMITS_CT23,
    STAGE0_IS_BOOK_SEAT,
    STAGE0_NEVER_SIZES,
    STAGE0_SURFACES,
    DictionaryCite,
    EvidenceClaim,
    Graph,
    Hypothesis,
    RoleBinding,
    admit_research_format_version,
    mint_hypothesis,
    refuse_stage0_governed_citation,
    refuse_stage0_intent_emit,
    refuse_stage0_seat,
    refuse_stage0_sizing,
    research_contract_identity,
    restore_hypothesis,
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
    "GRAPH_MEANING_KINDS",
    "GRAPH_PLANE",
    "HYPOTHESIS_CLASSES",
    "HYPOTHESIS_ORIGINS",
    "LAYOUT_DEMO_PACKAGE_ID",
    "POPULATION_INGEST_SOURCES",
    "POPULATION_INGEST_STARTED",
    "PRODUCT_NOUNS",
    "RESEARCH_CONTRACT_CLASS",
    "RESEARCH_FORMAT_VERSION",
    "RESEARCH_KNOWN_FORMAT_VERSIONS",
    "RESEARCH_LADDER",
    "STAGE0_CITED_BY_GOVERNED_EVIDENCE",
    "STAGE0_EMITS_CT23",
    "STAGE0_IS_BOOK_SEAT",
    "STAGE0_NEVER_SIZES",
    "STAGE0_SURFACES",
    "DictionaryCite",
    "DictionaryEntry",
    "EvidenceClaim",
    "Graph",
    "Hypothesis",
    "LayoutDemoProjection",
    "RoleBinding",
    "admit_research_format_version",
    "compile_graph",
    "complete_unresolved_f",
    "mint_bot_from_projection",
    "mint_hypothesis",
    "project_layout_demo",
    "refuse_stage0_governed_citation",
    "refuse_stage0_intent_emit",
    "refuse_stage0_seat",
    "refuse_stage0_sizing",
    "research_contract_identity",
    "resolve_dictionary_entry",
    "restore_hypothesis",
    "save_hypothesis",
    "start_population_ingest",
]
