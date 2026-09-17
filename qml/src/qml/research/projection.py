"""Read-only Stage 0 projection of LAYOUT-DEMO (Story 49.6, SCN-0017).

Parse cited bytes the host passed in. No filesystem I/O, no threads, no
process. The projection preserves class ``entry_hypothesis`` and unresolved F;
it does not invent stops, take-profits, a short side, or a CT-29 close-reason.
Viewing cited seed is not a save: no ``research_ref``. Boolean/temporal
operators stay on the hypothesis plane as a ``graph`` (never Confluence).
Compiling that graph to ``run_slice`` is refused. Auto-mint of CT-33/CT-34
from DNA is refused. Population ingest is not started.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.refusal import Ok, Result, is_refusal

from qml._refuse import invalid, policy
from qml.research._cited import FIELD_CITED_BYTES, decode_cited_buffer
from qml.research.stage0 import (
    F_LABELS,
    F_SLOTS,
    GRAPH_PLANE,
    HYPOTHESIS_CLASSES,
    Hypothesis,
    SavedHypothesis,
    save_authored_hypothesis,
)

__all__ = [
    "F_LABELS",
    "F_SLOTS",
    "GRAPH_COMPILE_TARGETS",
    "GRAPH_PLANE",
    "HYPOTHESIS_CLASSES",
    "LAYOUT_DEMO_PACKAGE_ID",
    "POPULATION_INGEST_SOURCES",
    "POPULATION_INGEST_STARTED",
    "PRODUCT_NOUNS",
    "LayoutDemoProjection",
    "compile_graph",
    "complete_unresolved_f",
    "mint_bot_from_projection",
    "project_layout_demo",
    "save_hypothesis",
    "start_population_ingest",
]

LAYOUT_DEMO_PACKAGE_ID: Final[str] = "STRAT-000001"
POPULATION_INGEST_STARTED: Final[bool] = False
PRODUCT_NOUNS: Final[tuple[str, ...]] = (
    "research",
    "hypothesis",
    "dictionary entry",
    "seed corpus",
)
GRAPH_COMPILE_TARGETS: Final[frozenset[str]] = frozenset(
    {
        "run_slice",
        "graph-template",
        "graph_template",
        "order-adapter",
        "order_adapter",
        "executor",
        "backtest",
    }
)
POPULATION_INGEST_SOURCES: Final[tuple[str, ...]] = (
    "yt-dlp",
    "n8n",
    "YouTube",
    "Hermes",
    "vision",
)

_FIELD_F_LABELS: Final[str] = "f_labels"
_MAPPING_REASON: Final[str] = "cited LAYOUT-DEMO bytes are a mapping of locator to buffer"

_CLASS_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:^class:\s*|^\|\s*class\s*\|\s*`?)"
    r"(entry_hypothesis|fragment|descriptive_pattern|composite|complete)",
    re.IGNORECASE | re.MULTILINE,
)
_PACKAGE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:strategy_id:\s*|^\|\s*id\s*\|\s*`?)(STRAT-\d+)",
    re.IGNORECASE | re.MULTILINE,
)
_DIRECTION_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:[ \t]*direction:\s*|\|\s*direction\s*\|\s*)(long|short)\b",
    re.IGNORECASE | re.MULTILINE,
)
_MARKET_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:^market:\s*|^\|\s*market\s*\|\s*`?)(forex|crypto-spot)",
    re.IGNORECASE | re.MULTILINE,
)
_TABLE_F_RE: Final[re.Pattern[str]] = re.compile(
    r"^\|\s*(invalidation|stop|targets|exit|management)\s*\|\s*`?"
    r"(source_defined|external_policy|deliberately_open|unresolved)`?",
    re.IGNORECASE | re.MULTILINE,
)
_YAML_F_RE: Final[re.Pattern[str]] = re.compile(
    r"^[ \t]+(invalidation|stop|targets|exit|management):\s*"
    r"(source_defined|external_policy|deliberately_open|unresolved)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_F_UNRESOLVED_RE: Final[re.Pattern[str]] = re.compile(
    r"\bF\b.{0,160}\bunresolved\b",
    re.IGNORECASE | re.DOTALL,
)
_OPERATOR_RE: Final[re.Pattern[str]] = re.compile(
    r"^[ \t]+operator:\s*(ALL|ANY|NOT|K_OF_N|sequence|within|arming|"
    r"reset|cooldown|re-entry)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_REL_THEN_RE: Final[re.Pattern[str]] = re.compile(
    r"^[ \t]+rel:\s*then\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_ALL_THEN_PROSE_RE: Final[re.Pattern[str]] = re.compile(
    r"\bALL\b.{0,400}\bTHEN\b",
    re.IGNORECASE | re.DOTALL,
)
_EMPTY_F: Final[Mapping[str, str]] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class LayoutDemoProjection:
    """Read-only Stage 0 view of cited LAYOUT-DEMO seed.

    Identity is the seed package id. This is not a save, not a ``research_ref``,
    not a CT-33/CT-34 mint, and not an executor.
    """

    package_id: str
    hypothesis_class: str
    f_labels: Mapping[str, str] = _EMPTY_F
    graph_operators: tuple[str, ...] = ()
    direction: str | None = None
    market: str | None = None
    read_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, _FIELD_F_LABELS, MappingProxyType(dict(self.f_labels)))
        object.__setattr__(self, "graph_operators", tuple(self.graph_operators))

    def to_payload(self) -> Mapping[str, object]:
        """Honesty-envelope payload. No ``research_ref``, no invented exits."""
        body: dict[str, object] = {
            "package_id": self.package_id,
            "class": self.hypothesis_class,
            _FIELD_F_LABELS: dict(self.f_labels),
            "graph": {
                "operators": list(self.graph_operators),
                "plane": GRAPH_PLANE,
            },
            "read_only": True,
        }
        if self.direction is not None:
            body["direction"] = self.direction
        if self.market is not None:
            body["market"] = self.market
        return MappingProxyType(body)


def project_layout_demo(cited_bytes: object) -> Result[LayoutDemoProjection]:
    """Project LAYOUT-DEMO meaning from host-passed cited bytes.

    ``cited_bytes`` is a mapping of posix locator → UTF-8 buffer, or one buffer.
    Lookup never opens a path.
    """
    files = _decode_cited(cited_bytes)
    if is_refusal(files):
        return files
    text = "\n".join(files.value.values())
    if "STRAT-000001" not in text and "LAYOUT-DEMO" not in text:
        return invalid(
            FIELD_CITED_BYTES,
            "the Stage 0 projection opens cited LAYOUT-DEMO seed; it does not "
            "read a filesystem path",
            given="cited buffers without STRAT-000001",
        )
    parts = _layout_parts(text)
    if is_refusal(parts):
        return parts
    package_id, hypothesis_class, f_labels = parts.value
    return Ok(
        LayoutDemoProjection(
            package_id=package_id,
            hypothesis_class=hypothesis_class,
            f_labels=f_labels,
            graph_operators=_graph_operators(text),
            direction=_direction(text),
            market=_market(text),
            read_only=True,
        )
    )


def compile_graph(
    projection: object,
    *,
    into: object = "run_slice",
) -> Result[None]:
    """Refuse compiling a Stage 0 graph off the hypothesis plane (DEC-0411)."""
    checked = _require_projection(projection)
    if is_refusal(checked):
        return checked
    target = into if isinstance(into, str) and into.strip() != "" else "run_slice"
    return policy(
        "graph",
        "Boolean/temporal operators stay on the hypothesis plane as meaning; "
        "compiling a Stage 0 graph to run_slice, a Graph Template, or an order "
        "adapter is refused (DEC-0411)",
        into=target,
        plane=GRAPH_PLANE,
        operators=list(checked.value.graph_operators),
        compile_targets=tuple(sorted(GRAPH_COMPILE_TARGETS)),
    )


def complete_unresolved_f(projection: object) -> Result[None]:
    """Refuse invented stops, take-profits, a short side, or CT-29 (DEC-0400)."""
    checked = _require_projection(projection)
    if is_refusal(checked):
        return checked
    return policy(
        _FIELD_F_LABELS,
        "unresolved F is not completed by invented stops, take-profits, a short "
        "side, or a CT-29 close-reason (DEC-0386, DEC-0400)",
        hypothesis_class=checked.value.hypothesis_class,
        f_labels=dict(checked.value.f_labels),
        invented_exits=False,
        short_side=False,
        close_reason=None,
    )


def mint_bot_from_projection(projection: object) -> Result[None]:
    """Refuse auto-mint of CT-33/CT-34 from DNA (DEC-0409)."""
    checked = _require_projection(projection)
    if is_refusal(checked):
        return checked
    return policy(
        "declaration",
        "auto-mint of CT-33 / CT-34 from DNA is dead; LAYOUT-DEMO is not "
        "extracted research to complete (DEC-0409)",
        package_id=checked.value.package_id,
        mints_ct33=False,
        mints_ct34=False,
        source="dna",
    )


def save_hypothesis(candidate: object) -> Result[SavedHypothesis]:
    """Explicit save returns canonical bytes + ``research_ref``; views refuse.

    A read-only LAYOUT-DEMO projection is not a save (DEC-0394, DEC-0401). An
    authored Stage 0 :class:`~qml.research.stage0.Hypothesis` returns pure
    :class:`~qml.research.stage0.SavedHypothesis` bytes — hosts persist.
    """
    if isinstance(candidate, LayoutDemoProjection):
        return policy(
            "research_ref",
            "viewing cited seed is not a save; identity waits on an explicit later "
            "save (DEC-0394, DEC-0401)",
            package_id=candidate.package_id,
            research_ref=None,
            read_only=True,
        )
    if isinstance(candidate, Hypothesis):
        return save_authored_hypothesis(candidate)
    return invalid(
        "hypothesis",
        "explicit save takes a Stage 0 Hypothesis; a seed view does not mint research_ref",
        given=type(candidate).__name__,
    )


def start_population_ingest(source: object = None) -> Result[None]:
    """Refuse population ingest; the mill stays source-agnostic (DEC-0380)."""
    given = source if isinstance(source, str) else None
    return policy(
        "ingest",
        "population ingest is not started; the mill remains source-agnostic "
        "without ingest (DEC-0380)",
        started=POPULATION_INGEST_STARTED,
        source=given,
        sources=POPULATION_INGEST_SOURCES,
    )


def _require_projection(projection: object) -> Result[LayoutDemoProjection]:
    if isinstance(projection, LayoutDemoProjection):
        return Ok(projection)
    return invalid(
        "projection",
        "compile/mint/save doors take a read-only LAYOUT-DEMO projection",
        given=type(projection).__name__,
    )


def _layout_parts(text: str) -> Result[tuple[str, str, Mapping[str, str]]]:
    package = _package_id(text)
    if is_refusal(package):
        return package
    hypothesis_class = _hypothesis_class(text)
    if is_refusal(hypothesis_class):
        return hypothesis_class
    f_labels = _read_f_labels(text)
    if is_refusal(f_labels):
        return f_labels
    return Ok((package.value, hypothesis_class.value, f_labels.value))


def _decode_cited(cited_bytes: object) -> Result[Mapping[str, str]]:
    if isinstance(cited_bytes, Mapping):
        return _decode_cited_mapping(cast("Mapping[object, object]", cited_bytes))
    text = decode_cited_buffer(cited_bytes)
    if is_refusal(text):
        return text
    return Ok(MappingProxyType({"": text.value}))


def _decode_cited_mapping(
    cited_map: Mapping[object, object],
) -> Result[Mapping[str, str]]:
    decoded: dict[str, str] = {}
    for raw_key, raw_value in cited_map.items():
        if not isinstance(raw_key, str) or raw_key.strip() == "":
            return invalid(
                FIELD_CITED_BYTES,
                _MAPPING_REASON,
                given=repr(raw_key),
            )
        text = decode_cited_buffer(raw_value)
        if is_refusal(text):
            return text
        decoded[raw_key.replace("\\", "/").strip()] = text.value
    if not decoded:
        return invalid(
            FIELD_CITED_BYTES,
            _MAPPING_REASON,
            given="empty mapping",
        )
    return Ok(MappingProxyType(decoded))


def _package_id(text: str) -> Result[str]:
    match = _PACKAGE_RE.search(text)
    if match is None:
        return invalid(
            "package_id",
            "cited LAYOUT-DEMO bytes name seed package STRAT-000001",
        )
    _prefix, _sep, digits = match.group(1).partition("-")
    return Ok(f"STRAT-{digits}")


def _hypothesis_class(text: str) -> Result[str]:
    match = _CLASS_RE.search(text)
    if match is None:
        return invalid(
            "class",
            "cited LAYOUT-DEMO bytes name a Stage 0 class",
        )
    token = match.group(1).casefold()
    if token not in HYPOTHESIS_CLASSES:
        return invalid("class", "class is Stage 0 taxonomy", given=token)
    return Ok(token)


def _read_f_labels(text: str) -> Result[Mapping[str, str]]:
    found: dict[str, str] = {}
    for match in (*_TABLE_F_RE.finditer(text), *_YAML_F_RE.finditer(text)):
        slot = match.group(1).casefold()
        label = match.group(2).casefold()
        if slot in F_SLOTS and label in F_LABELS:
            found.setdefault(slot, label)
    if _F_UNRESOLVED_RE.search(text) is not None:
        for slot in F_SLOTS:
            found.setdefault(slot, "unresolved")
    missing = [slot for slot in F_SLOTS if slot not in found]
    if missing:
        return invalid(
            _FIELD_F_LABELS,
            "Stage 0 preserves F labels; unresolved slots are not invented",
            missing=tuple(missing),
        )
    return Ok(MappingProxyType({slot: found[slot] for slot in F_SLOTS}))


def _graph_operators(text: str) -> tuple[str, ...]:
    found: list[str] = []
    seen: set[str] = set()

    def add(token: str) -> None:
        if token not in seen:
            seen.add(token)
            found.append(token)

    for match in _OPERATOR_RE.finditer(text):
        raw = match.group(1)
        add(raw.upper() if raw.casefold() in {"all", "any", "not"} else raw)
    if _ALL_THEN_PROSE_RE.search(text) is not None:
        add("ALL")
        add("THEN")
    if _REL_THEN_RE.search(text) is not None:
        add("THEN")
    return tuple(found)


def _direction(text: str) -> str | None:
    match = _DIRECTION_RE.search(text)
    if match is None:
        return None
    return match.group(1).casefold()


def _market(text: str) -> str | None:
    match = _MARKET_RE.search(text)
    if match is None:
        return None
    return match.group(1).casefold()
