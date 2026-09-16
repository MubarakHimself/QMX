"""Parse seed 12-field dictionary records from host-passed cited bytes (Story 49.5).

QML computes meaning. The host already cited the buffer — this helper performs
no filesystem I/O, spawns no thread, and spawns no process. Identity is the
seed pair ``(file_path, id)``; QML does not mint a parallel primitive id.
Eligible roles including invalidation stay on Stage 0 (GAP-0085 unfilled).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.refusal import Ok, Result, is_refusal

from qml._refuse import invalid
from qml.research._cited import decode_cited_buffer

__all__ = [
    "DICTIONARY_FIELDS",
    "DictionaryEntry",
    "resolve_dictionary_entry",
]

# Seed 12-field markdown record (dictionary/README.md), as QML identifiers.
DICTIONARY_FIELDS: Final[tuple[str, ...]] = (
    "family",
    "aliases",
    "definition",
    "boundaries",
    "observable_inputs",
    "recognition_semantics",
    "parameters_profiles",
    "eligible_roles",
    "market_data_constraints",
    "transfer_notes",
    "evidence_status",
    "uncertainty_variants",
)

_MARKDOWN_TO_FIELD: Final[Mapping[str, str]] = MappingProxyType(
    {
        "family": "family",
        "aliases": "aliases",
        "definition": "definition",
        "boundaries": "boundaries",
        "observable inputs": "observable_inputs",
        "recognition semantics": "recognition_semantics",
        "parameters/profiles": "parameters_profiles",
        "eligible roles": "eligible_roles",
        "market/data constraints": "market_data_constraints",
        "transfer notes": "transfer_notes",
        "evidence/status": "evidence_status",
        "uncertainty/variants": "uncertainty_variants",
    }
)

_HEADING_RE: Final[re.Pattern[str]] = re.compile(
    r"^##\s+([a-z0-9][a-z0-9-]*)(?:\s+[\u2014\u2013-]\s+(.+))?\s*$"
)
_FIELD_RE: Final[re.Pattern[str]] = re.compile(r"^- \*\*([^:*]+):\*\*\s*(.*)$")
_ENTRY_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ROLE_PAREN_RE: Final[re.Pattern[str]] = re.compile(r"\([^)]*\)")
_EMPTY_FIELDS: Final[Mapping[str, str]] = MappingProxyType({})
_COLLISION_REASON: Final[str] = "colliding slugs require (file_path, id) (FR-RES-05; DEC-0385)"


@dataclass(frozen=True, slots=True)
class DictionaryEntry:
    """Role-neutral dictionary record resolved from cited bytes.

    Identity is ``(file_path, id)``. This is not a registry row, not a CT-16
    producer, and not a hypothesis ``research_ref``.
    """

    file_path: str
    id: str
    title: str
    fields: Mapping[str, str] = _EMPTY_FIELDS
    eligible_roles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))
        object.__setattr__(self, "eligible_roles", tuple(self.eligible_roles))

    def identity(self) -> tuple[str, str]:
        """Seed collision key. QML does not mint a parallel primitive id."""
        return (self.file_path, self.id)

    def to_payload(self) -> Mapping[str, object]:
        """Meaning payload. No class labels, F maps, DNA, or research_ref."""
        return MappingProxyType(
            {
                "file_path": self.file_path,
                "id": self.id,
                "title": self.title,
                "fields": dict(self.fields),
                "eligible_roles": list(self.eligible_roles),
            }
        )


def resolve_dictionary_entry(
    cited_bytes: object,
    *,
    file_path: object,
    entry_id: object = None,
) -> Result[DictionaryEntry]:
    """Resolve one 12-field record from a host-passed buffer.

    ``file_path`` may be a posix path or a ``path#id`` locator. Lookup never
    opens a path. Missing ``file_path`` is a collision-key refusal.
    """
    path_and_id = _identity_pair(file_path, entry_id)
    if is_refusal(path_and_id):
        return path_and_id
    posix_path, slug = path_and_id.value
    text = decode_cited_buffer(cited_bytes)
    if is_refusal(text):
        return text
    return _entry_from_text(text.value, posix_path=posix_path, slug=slug)


def _entry_from_text(
    text: str,
    *,
    posix_path: str,
    slug: str,
) -> Result[DictionaryEntry]:
    matches = [item for item in _parse_entries(text) if item["id"] == slug]
    selected = _select_match(matches, posix_path=posix_path, slug=slug)
    if is_refusal(selected):
        return selected
    return _dictionary_entry_from_raw(selected.value, posix_path=posix_path, slug=slug)


def _select_match(
    matches: list[dict[str, object]],
    *,
    posix_path: str,
    slug: str,
) -> Result[dict[str, object]]:
    if len(matches) > 1:
        return invalid(
            "id",
            _COLLISION_REASON,
            slug=slug,
            id=slug,
            file_path=posix_path,
            occurrences=len(matches),
        )
    if not matches:
        return invalid(
            "id",
            "cited bytes do not contain that dictionary entry id",
            id=slug,
            file_path=posix_path,
        )
    return Ok(matches[0])


def _dictionary_entry_from_raw(
    raw: dict[str, object],
    *,
    posix_path: str,
    slug: str,
) -> Result[DictionaryEntry]:
    fields = _required_fields(cast("Mapping[str, str]", raw["fields"]))
    if is_refusal(fields):
        return fields
    record = fields.value
    return Ok(
        DictionaryEntry(
            file_path=posix_path,
            id=slug,
            title=cast("str", raw["title"]),
            fields=record,
            eligible_roles=_parse_eligible_roles(record["eligible_roles"]),
        )
    )


def _identity_pair(file_path: object, entry_id: object) -> Result[tuple[str, str]]:
    if not isinstance(file_path, str) or file_path.strip() == "":
        return invalid(
            "file_path",
            _COLLISION_REASON,
            given=repr(file_path),
            id=entry_id if isinstance(entry_id, str) else None,
        )
    locator = file_path.replace("\\", "/").strip()
    path, sep, fragment = locator.partition("#")
    if path.strip() == "":
        return invalid(
            "file_path",
            _COLLISION_REASON,
            given=repr(file_path),
        )
    slug = _entry_id(entry_id, fragment if sep else "")
    if is_refusal(slug):
        return slug
    return Ok((path, slug.value))


def _entry_id(entry_id: object, fragment: str) -> Result[str]:
    token_result = _token_from_id_and_fragment(entry_id, fragment)
    if is_refusal(token_result):
        return token_result
    token = token_result.value
    if token == "" or _ENTRY_ID_RE.fullmatch(token) is None:
        return invalid(
            "id",
            _COLLISION_REASON,
            given=repr(entry_id),
        )
    return Ok(token)


def _token_from_id_and_fragment(entry_id: object, fragment: str) -> Result[str]:
    if entry_id is None:
        return Ok(fragment)
    if not isinstance(entry_id, str):
        return invalid(
            "id",
            "a dictionary entry id is the seed kebab slug",
            given=repr(entry_id),
        )
    token = entry_id.strip()
    if fragment and token and fragment != token:
        return invalid(
            "id",
            "locator fragment must match entry id",
            id=token,
            fragment=fragment,
        )
    return Ok(token if token else fragment)


def _parse_entries(text: str) -> tuple[dict[str, object], ...]:
    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    current_field: tuple[str, list[str]] | None = None

    for raw in text.splitlines():
        line = raw.rstrip()
        heading = _HEADING_RE.match(line)
        if heading is not None:
            _flush_entry(entries, current, current_field)
            current = _new_entry(heading)
            current_field = None
            continue
        if current is None:
            continue
        current_field = _consume_entry_line(current, current_field, line)

    _flush_entry(entries, current, current_field)
    return tuple(entries)


def _new_entry(heading: re.Match[str]) -> dict[str, object]:
    return {
        "id": heading.group(1),
        "title": (heading.group(2) or "").strip(),
        "fields": {},
    }


def _flush_field(
    current: dict[str, object] | None,
    current_field: tuple[str, list[str]] | None,
) -> None:
    if current is None or current_field is None:
        return
    key, chunks = current_field
    fields = cast("dict[str, str]", current["fields"])
    fields[key] = " ".join(chunks).strip()


def _flush_entry(
    entries: list[dict[str, object]],
    current: dict[str, object] | None,
    current_field: tuple[str, list[str]] | None,
) -> None:
    _flush_field(current, current_field)
    if current is not None:
        entries.append(current)


def _consume_entry_line(
    current: dict[str, object],
    current_field: tuple[str, list[str]] | None,
    line: str,
) -> tuple[str, list[str]] | None:
    stripped = line.strip()
    if stripped.startswith("|") or stripped.startswith("---"):
        return current_field
    field = _FIELD_RE.match(line)
    if field is not None:
        _flush_field(current, current_field)
        mapped = _MARKDOWN_TO_FIELD.get(field.group(1).strip().casefold())
        if mapped is None:
            return None
        value = field.group(2).strip()
        return (mapped, [value] if value else [])
    if current_field is not None and stripped and not stripped.startswith("#"):
        current_field[1].append(stripped)
    return current_field


def _required_fields(raw: Mapping[str, str]) -> Result[Mapping[str, str]]:
    missing = [name for name in DICTIONARY_FIELDS if name not in raw]
    if missing:
        return invalid(
            "fields",
            "a dictionary entry is the seed 12-field markdown record",
            missing=tuple(missing),
        )
    return Ok(MappingProxyType({name: raw[name] for name in DICTIONARY_FIELDS}))


def _parse_eligible_roles(text: str) -> tuple[str, ...]:
    cleaned = _ROLE_PAREN_RE.sub(" ", text)
    roles: list[str] = []
    seen: set[str] = set()
    for part in cleaned.split(","):
        token = " ".join(part.strip().strip(".;").split())
        if token == "":
            continue
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        roles.append(key)
    return tuple(roles)
