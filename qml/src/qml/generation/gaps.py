"""GAP-0085 nouns and GAP-0063 algorithm stay unfilled (Story 38.3).

Typed Entry/Exit/Filter/Session vocabulary is not minted. Write-ownership
remains QML/host for a later increment. A first algorithm requested as a
decided default is refused as unruled. No-code authoring is not a V1
generation surface; rung 2 ordinary Python (Story 32.3) remains the logic
path. This epic trails connect-wave (Epics 32-37) and does not block
Library, What-if, or the door.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from types import MappingProxyType
from typing import Final, cast

from qmf.core.refusal import Ok, Result

from qml._refuse import invalid, policy, unsupported

__all__ = [
    "CHEAP_VETO_A1",
    "CONNECT_WAVE_EPICS",
    "DEFAULT_GENERATOR_ALGORITHM",
    "DOES_NOT_BLOCK_EPICS",
    "DOES_NOT_BLOCK_SURFACES",
    "DOOR_EPIC",
    "GAP_0063_ALGORITHM_CHOICES",
    "GAP_0063_ID",
    "GAP_0063_RECORD",
    "GAP_0063_STATUS",
    "GAP_0085_ID",
    "GAP_0085_MECHANISM_FIELDS",
    "GAP_0085_NOUNS",
    "GAP_0085_RECORD",
    "GAP_0085_STATUS",
    "GAP_0085_WRITE_INCREMENT",
    "GAP_0085_WRITE_OWNER",
    "GENERATION_EPIC",
    "GENERATOR_ALGORITHM_UNRULED",
    "HOST_MINTS_MECHANISM_VOCABULARY",
    "LIBRARY_EPIC",
    "LOGIC_PATH",
    "LOGIC_PATH_RUNG",
    "LOGIC_PATH_STORY",
    "MECHANISM_VOCABULARY_MINTED",
    "TRAILS_CONNECT_WAVE",
    "WHATIF_EPIC",
    "admit_decided_generator_algorithm",
    "blocks_library_whatif_or_door",
    "mint_mechanism_vocabulary",
    "minted_mechanism_type_hits",
    "prose_fills_gap_0063",
    "refuse_gap_0085_nouns",
    "refuse_generator_algorithm",
    "refuse_no_code_authoring",
    "trails_connect_wave",
    "write_ownership_is_qml_host",
]


GAP_0085_ID: Final[str] = "GAP-0085"
GAP_0063_ID: Final[str] = "GAP-0063"
GAP_0085_STATUS: Final[str] = "deferred"
GAP_0063_STATUS: Final[str] = "unruled"
GAP_0085_WRITE_OWNER: Final[str] = "qml-host"
GAP_0085_WRITE_INCREMENT: Final[str] = "later"
MECHANISM_VOCABULARY_MINTED: Final[bool] = False
HOST_MINTS_MECHANISM_VOCABULARY: Final[bool] = False
GENERATOR_ALGORITHM_UNRULED: Final[bool] = True
DEFAULT_GENERATOR_ALGORITHM: Final[None] = None
LOGIC_PATH: Final[str] = "ordinary_python"
LOGIC_PATH_RUNG: Final[int] = 2
LOGIC_PATH_STORY: Final[str] = "32.3"

# NFR-W06 A1 / DEC-0287 A1: connect-wave first; generation trails.
CHEAP_VETO_A1: Final[str] = "NFR-W06 A1"
CONNECT_WAVE_EPICS: Final[tuple[int, ...]] = (32, 33, 34, 35, 36, 37)
GENERATION_EPIC: Final[int] = 38
LIBRARY_EPIC: Final[int] = 34
WHATIF_EPIC: Final[int] = 35
DOOR_EPIC: Final[int] = 36
DOES_NOT_BLOCK_EPICS: Final[tuple[int, ...]] = (LIBRARY_EPIC, WHATIF_EPIC, DOOR_EPIC)
DOES_NOT_BLOCK_SURFACES: Final[tuple[str, ...]] = ("library", "what-if", "door")
TRAILS_CONNECT_WAVE: Final[bool] = True

# PascalCase strategy-mechanism types. CT-34 ``filter`` is a leg role, not this set.
GAP_0085_NOUNS: Final[frozenset[str]] = frozenset(
    {
        "EntryMechanism",
        "ExitMechanism",
        "Filter",
        "InvalidationRule",
        "PositionRule",
        "SessionRule",
    }
)

# Extra-key refuse set. ``filter`` as a CT-34 leg *role value* is not this set.
GAP_0085_MECHANISM_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "entry_mechanism",
        "entrymechanism",
        "exit_mechanism",
        "exitmechanism",
        "filter",
        "invalidation_rule",
        "invalidationrule",
        "position_rule",
        "positionrule",
        "session_rule",
        "sessionrule",
    }
)

GAP_0063_ALGORITHM_CHOICES: Final[frozenset[str]] = frozenset(
    {
        "ct34-placeholder",
        "ct34_placeholder",
        "logic-synthesis",
        "logic_synthesis",
        "placeholder-fill",
        "placeholder_fill",
        "python-logic-synthesis",
        "python_logic_synthesis",
    }
)
_GAP_0063_NORMALIZED: Final[frozenset[str]] = frozenset(
    item.replace("-", "_") for item in GAP_0063_ALGORITHM_CHOICES
)

GAP_0085_RECORD: Final[Mapping[str, object]] = MappingProxyType(
    {
        "gap": GAP_0085_ID,
        "status": GAP_0085_STATUS,
        "minted": MECHANISM_VOCABULARY_MINTED,
        "write_owner": GAP_0085_WRITE_OWNER,
        "write_increment": GAP_0085_WRITE_INCREMENT,
        "nouns": tuple(sorted(GAP_0085_NOUNS)),
    }
)
GAP_0063_RECORD: Final[Mapping[str, object]] = MappingProxyType(
    {
        "gap": GAP_0063_ID,
        "status": GAP_0063_STATUS,
        "unruled": GENERATOR_ALGORITHM_UNRULED,
        "default": DEFAULT_GENERATOR_ALGORITHM,
        "choices": tuple(sorted(GAP_0063_ALGORITHM_CHOICES)),
    }
)

_MECHANISMS_FIELD: Final[str] = "mechanisms"
_DECIDED_ALGORITHM_RE: Final[re.Pattern[str]] = re.compile(
    r"algorithm\s+is\s+(placeholder(?:[-\s_]fill)?|python[-\s_]logic[-\s_]synthesis)"
    r"|DEFAULT_GENERATOR_ALGORITHM\s*[:=]\s*['\"]",
    re.IGNORECASE,
)
_UNRULED_WINDOW_RE: Final[re.Pattern[str]] = re.compile(
    r"unruled|not filled|stay(?:s)? unfilled|must not be filled|does not choose|"
    r"refused as unruled",
    re.IGNORECASE,
)


def _normalize_token(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().casefold().replace("-", "_")
    return token if token else None


def refuse_gap_0085_nouns(value: object = None) -> Result[None]:
    """Refuse typed Entry/Exit/Filter/Session mechanism nouns (GAP-0085)."""
    if value is None or value is False:
        return Ok(None)
    hits: list[str] = []
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        for key in mapping:
            token = _normalize_token(key)
            if token is not None and token in GAP_0085_MECHANISM_FIELDS:
                hits.append(str(key))
            elif isinstance(key, str) and key in GAP_0085_NOUNS:
                hits.append(key)
    elif isinstance(value, str):
        token = _normalize_token(value)
        if (token is not None and token in GAP_0085_MECHANISM_FIELDS) or value in GAP_0085_NOUNS:
            hits.append(value)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in cast("Sequence[object]", value):
            token = _normalize_token(item)
            if token is not None and token in GAP_0085_MECHANISM_FIELDS:
                hits.append(str(item))
            elif isinstance(item, str) and item in GAP_0085_NOUNS:
                hits.append(item)
    extra: dict[str, object] = {
        "gap": GAP_0085_ID,
        "gap_status": GAP_0085_STATUS,
        "minted": MECHANISM_VOCABULARY_MINTED,
        "write_owner": GAP_0085_WRITE_OWNER,
        "later_increment": True,
    }
    if hits:
        extra["fields"] = sorted(hits)
    else:
        extra["given"] = "mechanism-payload"
    return policy(
        "mechanisms",
        "typed Entry/Exit/Filter/Session vocabulary is Deferred GAP-0085; "
        "write-ownership remains QML/host for a later increment",
        **extra,
    )


def refuse_generator_algorithm(
    value: object = None,
    *,
    as_default: bool = False,
) -> Result[None]:
    """Refuse choosing GAP-0063's first generator algorithm."""
    if value is None or value is False:
        if not as_default:
            return Ok(None)
        token = None
    else:
        token = _normalize_token(value) if isinstance(value, str) else None
    return unsupported(
        "algorithm",
        "the first generator algorithm (placeholder-fill of CT-34 legs vs "
        "Python-logic synthesis) is unruled GAP-0063 and is not filled here",
        given=repr(value) if value is not None and value is not False else "decided-default",
        gap=GAP_0063_ID,
        gap_status=GAP_0063_STATUS,
        unruled=GENERATOR_ALGORITHM_UNRULED,
        as_default=as_default,
        chosen=DEFAULT_GENERATOR_ALGORITHM,
        named_choice=token in _GAP_0063_NORMALIZED if token is not None else False,
    )


def refuse_no_code_authoring(value: object = None) -> Result[None]:
    """Refuse no-code authoring as a V1 generation surface (FR-W40)."""
    if value is None or value is False:
        return Ok(None)
    return unsupported(
        "no_code",
        "no-code authoring is not a V1 generation surface; rung 2 ordinary "
        "Python remains the logic path",
        given=repr(value),
        logic_path=LOGIC_PATH,
        logic_rung=LOGIC_PATH_RUNG,
        logic_path_story=LOGIC_PATH_STORY,
    )


def mint_mechanism_vocabulary(nouns: object = None) -> Result[None]:
    """Always refuse. GAP-0085 nouns are not minted in this increment."""
    if nouns is None or nouns is False:
        return policy(
            "mechanisms",
            "typed Entry/Exit/Filter/Session vocabulary is Deferred GAP-0085; "
            "write-ownership remains QML/host for a later increment",
            gap=GAP_0085_ID,
            gap_status=GAP_0085_STATUS,
            minted=MECHANISM_VOCABULARY_MINTED,
            write_owner=GAP_0085_WRITE_OWNER,
            later_increment=True,
            given="mint-vocabulary",
        )
    return refuse_gap_0085_nouns(nouns)


def admit_decided_generator_algorithm(choice: object = None) -> Result[None]:
    """Refuse a first algorithm requested as a decided default (GAP-0063)."""
    return refuse_generator_algorithm(choice, as_default=True)


def minted_mechanism_type_hits(names: object) -> Result[tuple[str, ...]]:
    """Return PascalCase GAP-0085 type names present in a host-supplied name list.

    Pure: the caller walks AST/class tables. CT-34 ``filter`` is a role value.
    """
    if isinstance(names, (str, bytes)) or not isinstance(names, Iterable):
        return invalid(
            "names",
            "mechanism-type hits are computed over an iterable of identifiers",
            given=type(names).__name__,
        )
    hits: list[str] = []
    for item in cast("Iterable[object]", names):
        if not isinstance(item, str):
            return invalid(
                "names",
                "each scanned name is a string identifier",
                given=repr(item),
            )
        if item in GAP_0085_NOUNS:
            hits.append(item)
    return Ok(tuple(dict.fromkeys(hits)))


def prose_fills_gap_0063(text: object) -> Result[bool]:
    """True when prose treats one GAP-0063 choice as the decided default."""
    if not isinstance(text, str):
        return invalid(
            "text",
            "GAP-0063 prose fill is classified over a string",
            given=type(text).__name__,
        )
    for match in _DECIDED_ALGORITHM_RE.finditer(text):
        window = text[max(0, match.start() - 96) : match.end() + 96]
        if _UNRULED_WINDOW_RE.search(window) is not None:
            continue
        if "DEFAULT_GENERATOR_ALGORITHM" in match.group(0).upper() and "None" in window:
            continue
        return Ok(True)
    return Ok(False)


def write_ownership_is_qml_host() -> bool:
    """GAP-0085 write path stays QML/host for a later increment (DEC-0272)."""
    return GAP_0085_WRITE_OWNER == "qml-host" and GAP_0085_WRITE_INCREMENT == "later"


def trails_connect_wave() -> bool:
    """True when generation is sequenced after Epics 32-37 (DEC-0287 A1)."""
    return TRAILS_CONNECT_WAVE and max(CONNECT_WAVE_EPICS) < GENERATION_EPIC


def blocks_library_whatif_or_door() -> bool:
    """Generation must not block Library, What-if, or the door (NFR-W06 A1)."""
    return False
