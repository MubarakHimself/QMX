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
    text = _decode_cited_bytes(cited_bytes)
    if is_refusal(text):
        return text
    matches = [item for item in _parse_entries(text.value) if item["id"] == slug]
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
    raw = matches[0]
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
    token: str
    if entry_id is None:
        token = fragment
    elif not isinstance(entry_id, str):
        return invalid(
            "id",
            "a dictionary entry id is the seed kebab slug",
            given=repr(entry_id),
        )
    else:
        token = entry_id.strip()
        if fragment and token and fragment != token:
            return invalid(
                "id",
                "locator fragment must match entry id",
                id=token,
                fragment=fragment,
            )
        if token == "":
            token = fragment
    if token == "" or _ENTRY_ID_RE.fullmatch(token) is None:
        return invalid(
            "id",
            "colliding slugs require (file_path, id) (FR-RES-05; DEC-0385)",
            given=repr(entry_id),
        )
    return Ok(token)


def _decode_cited_bytes(cited_bytes: object) -> Result[str]:
    if isinstance(cited_bytes, str):
        return Ok(cited_bytes)
    if not isinstance(cited_bytes, bytes):
        return invalid(
            "cited_bytes",
            "the vocabulary helper resolves host-passed cited bytes; it does not "
            "read a filesystem path",
            given=type(cited_bytes).__name__,
        )
    try:
        return Ok(cited_bytes.decode("utf-8"))
    except UnicodeDecodeError:
        return invalid(
            "cited_bytes",
            "cited dictionary bytes are UTF-8 markdown",
            given="bytes",
        )


def _parse_entries(text: str) -> tuple[dict[str, object], ...]:
    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    current_field: tuple[str, list[str]] | None = None

    def flush_field() -> None:
        nonlocal current_field
        if current is not None and current_field is not None:
            key, chunks = current_field
            fields = cast("dict[str, str]", current["fields"])
            fields[key] = " ".join(chunks).strip()
            current_field = None

    def flush_entry() -> None:
        flush_field()
        if current is not None:
            entries.append(current)

    for raw in text.splitlines():
        line = raw.rstrip()
        heading = _HEADING_RE.match(line)
        if heading is not None:
            flush_entry()
            current = {
                "id": heading.group(1),
                "title": (heading.group(2) or "").strip(),
                "fields": {},
            }
            current_field = None
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.startswith("|") or stripped.startswith("---"):
            continue
        field = _FIELD_RE.match(line)
        if field is not None:
            flush_field()
            mapped = _MARKDOWN_TO_FIELD.get(field.group(1).strip().casefold())
            if mapped is None:
                current_field = None
                continue
            value = field.group(2).strip()
            current_field = (mapped, [value] if value else [])
            continue
        if current_field is not None and stripped and not stripped.startswith("#"):
            current_field[1].append(stripped)

    flush_entry()
    return tuple(entries)


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
