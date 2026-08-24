"""Book and BMS config fragments as schema-validated derived fp1 artifacts (B-3).

A Book (CT-22) or BMS (CT-27) definition resolved through the one registry-read
port materializes a fingerprinted DERIVED fragment — never a newly minted
registry kind, never free-hand-edited. The fragment stamps its own AD-5 integer
format version so old fragments stay readable forever. Lineage back to the
source is a CT-07 ``occurrence-of`` edge (from_ref = fragment fp1, to_ref =
definition fp1). Named condition presets are config fragments like any other
(DEC-0160).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import WriterId
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal
from qmf.registry import EdgeType, LineageEdge, RegistrationRecord

from qmb._refuse import clean_token, invalid, unsupported
from qmb.registryread import RegistryFragment, RegistryReadPort

__all__ = [
    "BMS_NAMESPACES",
    "BMS_RECORD_KIND",
    "BOOK_NAMESPACES",
    "BOOK_RECORD_KIND",
    "CONFIG_FRAGMENT_CLASS",
    "FRAGMENT_FORMAT_VERSION",
    "FRAGMENT_FORMAT_VERSION_1",
    "FRAGMENT_KNOWN_FORMAT_VERSIONS",
    "FRAGMENT_LINEAGE_EDGE_TYPE",
    "SOURCE_BMS",
    "SOURCE_BOOK",
    "SOURCE_PRESET",
    "ConfigFragment",
    "fragment_identity",
    "materialize_bms_fragment",
    "materialize_book_fragment",
    "materialize_condition_preset",
]

# The fragment envelope format version (AD-5). Incompatible meaning mints the
# next integer; history stays readable. Not package SemVer.
FRAGMENT_FORMAT_VERSION_1: Final[int] = 1
FRAGMENT_FORMAT_VERSION: Final[int] = FRAGMENT_FORMAT_VERSION_1
FRAGMENT_KNOWN_FORMAT_VERSIONS: Final[frozenset[int]] = frozenset({FRAGMENT_FORMAT_VERSION_1})

CONFIG_FRAGMENT_CLASS: Final[str] = "config-fragment"
SOURCE_BOOK: Final[str] = "book"
SOURCE_BMS: Final[str] = "bms"
SOURCE_PRESET: Final[str] = "named-condition-preset"
BOOK_RECORD_KIND: Final[str] = "book-definition"
BMS_RECORD_KIND: Final[str] = "bms-definition"
FRAGMENT_LINEAGE_EDGE_TYPE: Final[EdgeType] = EdgeType.OCCURRENCE_OF

# Compiler key namespaces — DISJOINT by construction (B-3, DEC-0143, DEC-0160).
BOOK_NAMESPACES: Final[frozenset[str]] = frozenset({"admission", "sizing", "exit-door"})
BMS_NAMESPACES: Final[frozenset[str]] = frozenset(
    {"accounting", "constraints", "kill-line", "reporting"}
)

# CT-22 sections projected into Book-owned fragment namespaces. Unmapped
# sections (charter, control_policy, protection_windows) stay on the source
# definition — cited by source fp1 — and never become fragment keys.
BOOK_SECTION_NAMESPACE: Final[Mapping[str, str]] = MappingProxyType(
    {
        "admission_bar": "admission",
        "footprint_requirements": "admission",
        "leash_grammar": "admission",
        "capacity_and_sweep": "admission",
        "money_rules": "sizing",
        "paper": "sizing",
        "exit_policy": "exit-door",
    }
)

# CT-27 sections projected into BMS-owned fragment namespaces. kill-line is a
# fragment key namespace, not a CT-27 section name; ksa_policy occupies it as
# the BMS-owned protection posture. BMS admission_bar is not mapped — admission
# is Book-owned.
BMS_SECTION_NAMESPACE: Final[Mapping[str, str]] = MappingProxyType(
    {
        "accounting_rules": "accounting",
        "constraints": "constraints",
        "control_rank_table": "constraints",
        "ksa_policy": "kill-line",
        "reporting": "reporting",
    }
)


def fragment_identity() -> dict[str, object]:
    """Identity-bearing fragment-schema fields. Package SemVer is omitted."""
    return {
        "book_namespaces": tuple(sorted(BOOK_NAMESPACES)),
        "bms_namespaces": tuple(sorted(BMS_NAMESPACES)),
        "class": CONFIG_FRAGMENT_CLASS,
        "format_version": FRAGMENT_FORMAT_VERSION,
        "lineage_edge_type": FRAGMENT_LINEAGE_EDGE_TYPE.value,
    }


@dataclass(frozen=True, slots=True)
class ConfigFragment:
    """A schema-validated, fingerprinted DERIVED config fragment (B-3).

    Not a registry kind. Identity is qmf-core ``fp1`` over source kind, source
    definition fingerprint, keys, and the fragment's own AD-5 format version.
    The CT-07 lineage edge is an occurrence fact attached at materialization
    and excluded from identity.
    """

    format_version: int
    source_kind: str
    source_fp1: Fingerprint
    keys: Mapping[str, object]
    fingerprint: Fingerprint
    lineage: LineageEdge | None = None
    preset_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "keys", _freeze_mapping(self.keys))

    def fp1_identity(self) -> dict[str, object]:
        """The parts that ARE this fragment's identity. Lineage is omitted."""
        content: dict[str, object] = {
            "class": CONFIG_FRAGMENT_CLASS,
            "format_version": self.format_version,
            "keys": _plain(self.keys),
            "source_fp1": self.source_fp1.value,
            "source_kind": self.source_kind,
        }
        if self.preset_name is not None:
            content["preset_name"] = self.preset_name
        return content

    def as_registry_fragment(self) -> Result[RegistryFragment]:
        """Delivery envelope for an as-of set — still not a registry kind."""
        return RegistryFragment.try_create(self.source_fp1, self.fp1_identity())

    @classmethod
    def try_read(
        cls,
        identity: object,
        *,
        reader_format_version: object = FRAGMENT_FORMAT_VERSION,
        lineage: LineageEdge | None = None,
    ) -> Result[ConfigFragment]:
        """Re-read a fragment identity. Old format versions stay readable forever.

        A format-1 reader confronting a newer artifact refuses ``unsupported
        capability``. An unknown format version is likewise unsupported — never
        a best-effort read (AD-5).
        """
        if not isinstance(identity, Mapping):
            return invalid(
                "identity",
                "a config fragment identity is a key->value mapping",
                given=repr(type(identity).__name__),
            )
        body = cast("Mapping[str, object]", identity)
        class_token = clean_token(body.get("class"))
        if class_token != CONFIG_FRAGMENT_CLASS:
            return invalid(
                "class",
                "a config fragment identity names class config-fragment",
                given=repr(body.get("class")),
            )
        reader = _coerce_format_version(reader_format_version)
        if reader is None:
            return unsupported(
                "reader_format_version",
                "a fragment reader format version is a positive integer ordinal",
                given=repr(reader_format_version),
            )
        version = _coerce_format_version(body.get("format_version"))
        if version is None or version not in FRAGMENT_KNOWN_FORMAT_VERSIONS:
            return unsupported(
                "format_version",
                "this config fragment format version is not one this build "
                "understands; an unknown version is never best-effort read",
                given=repr(body.get("format_version")),
                understood=sorted(FRAGMENT_KNOWN_FORMAT_VERSIONS),
            )
        if version > reader:
            return unsupported(
                "format_version",
                "a format-1 reader confronting a newer fragment refuses "
                "unsupported capability; old fragments stay readable forever",
                given=version,
                reader_format_version=reader,
            )
        source_kind = clean_token(body.get("source_kind"))
        if source_kind not in {SOURCE_BOOK, SOURCE_BMS, SOURCE_PRESET}:
            return invalid(
                "source_kind",
                "a config fragment source kind is book, bms, or named-condition-preset",
                given=repr(body.get("source_kind")),
            )
        source = _coerce_fingerprint(body.get("source_fp1"))
        if source is None:
            return invalid(
                "source_fp1",
                "a config fragment cites its source definition by fp1",
                given=repr(body.get("source_fp1")),
            )
        keys = body.get("keys")
        if not isinstance(keys, Mapping):
            return invalid(
                "keys",
                "a config fragment body is a key->value mapping",
                given=repr(type(keys).__name__),
            )
        keys_map = cast("Mapping[str, object]", keys)
        owned = _owned_namespaces(source_kind)
        if owned is not None:
            extra = [key for key in keys_map if key not in owned]
            if extra:
                return invalid(
                    "keys",
                    "a Book or BMS fragment emits only its owned key namespaces",
                    extra=sorted(extra),
                    owned=sorted(owned),
                )
        mixed = _mixed_namespace_keys(keys_map)
        if mixed is not None:
            return mixed
        preset_name: str | None = None
        if source_kind == SOURCE_PRESET:
            preset_name = clean_token(body.get("preset_name"))
            if preset_name is None:
                return invalid(
                    "preset_name",
                    "a named condition preset carries a non-empty name",
                    given=repr(body.get("preset_name")),
                )
        elif "preset_name" in body:
            return invalid(
                "preset_name",
                "Book and BMS fragments are not named condition presets",
                given=repr(body.get("preset_name")),
            )
        return _finish(
            format_version=version,
            source_kind=source_kind,
            source_fp1=source,
            keys=keys_map,
            writer=None,
            lineage=lineage,
            preset_name=preset_name,
        )


def materialize_book_fragment(
    port: object,
    ref: object,
    writer: object,
) -> Result[ConfigFragment]:
    """Materialize a Book config fragment from a CT-22 definition the port resolves."""
    return _materialize_definition(
        port,
        ref,
        writer,
        expected_kind=BOOK_RECORD_KIND,
        source_kind=SOURCE_BOOK,
        projection=BOOK_SECTION_NAMESPACE,
    )


def materialize_bms_fragment(
    port: object,
    ref: object,
    writer: object,
) -> Result[ConfigFragment]:
    """Materialize a BMS config fragment from a CT-27 definition the port resolves."""
    return _materialize_definition(
        port,
        ref,
        writer,
        expected_kind=BMS_RECORD_KIND,
        source_kind=SOURCE_BMS,
        projection=BMS_SECTION_NAMESPACE,
    )


def materialize_condition_preset(
    port: object,
    source_ref: object,
    writer: object,
    *,
    name: object,
    keys: object,
) -> Result[ConfigFragment]:
    """Author a named condition preset as a config fragment like any other (B-3).

    ``source_ref`` resolves through the registry-read port — the preset is
    derived, never a free-hand file. Keys are schema-validated (fp1-clean) and
    may not mix Book-owned and BMS-owned namespaces.
    """
    resolved_port = _require_port(port)
    if is_refusal(resolved_port):
        return resolved_port
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "materialization stamps a WriterId on the CT-07 occurrence-of edge",
            given=repr(type(writer).__name__),
        )
    preset_name = clean_token(name)
    if preset_name is None:
        return invalid(
            "name",
            "a named condition preset carries a non-empty name",
            given=repr(name),
        )
    if not isinstance(keys, Mapping):
        return invalid(
            "keys",
            "a named condition preset body is a key->value mapping",
            given=repr(type(keys).__name__),
        )
    keys_map = cast("Mapping[str, object]", keys)
    mixed = _mixed_namespace_keys(keys_map)
    if mixed is not None:
        return mixed
    looked_up = resolved_port.value.resolve(source_ref)
    if is_refusal(looked_up):
        return looked_up
    source = _source_fp1(looked_up.value.record, looked_up.value.fingerprint)
    if is_refusal(source):
        return source
    return _finish(
        format_version=FRAGMENT_FORMAT_VERSION,
        source_kind=SOURCE_PRESET,
        source_fp1=source.value,
        keys=keys_map,
        writer=writer,
        lineage=None,
        preset_name=preset_name,
    )


def _materialize_definition(
    port: object,
    ref: object,
    writer: object,
    *,
    expected_kind: str,
    source_kind: str,
    projection: Mapping[str, str],
) -> Result[ConfigFragment]:
    """Resolve a definition record and project it into a disjoint-namespace fragment."""
    resolved_port = _require_port(port)
    if is_refusal(resolved_port):
        return resolved_port
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "materialization stamps a WriterId on the CT-07 occurrence-of edge",
            given=repr(type(writer).__name__),
        )
    looked_up = resolved_port.value.resolve(ref)
    if is_refusal(looked_up):
        return looked_up
    record = looked_up.value.record
    if record is None:
        return invalid(
            "ref",
            "config fragments materialize from a Book or BMS definition record, "
            "never from a free-hand fragment",
            fingerprint=looked_up.value.cite(),
        )
    if record.kind != expected_kind:
        return invalid(
            "kind",
            "this materializer reads a "
            f"{expected_kind} record and projects it into a derived fragment",
            given=record.kind,
            expected=expected_kind,
        )
    class_token = clean_token(record.body.get("class"))
    expected_class = "book-definition" if source_kind == SOURCE_BOOK else "bms-definition"
    if class_token != expected_class:
        return invalid(
            "body",
            "the record body is a CT-22/CT-27 definition identity, never a free-hand mapping",
            given=repr(record.body.get("class")),
            expected=expected_class,
        )
    extracted = _extract_keys(record.body, projection, source_kind=source_kind)
    if is_refusal(extracted):
        return extracted
    source = fingerprint(_plain(record.body))
    if is_refusal(source):
        return invalid(
            "body",
            "the definition body is not fp1-clean identity content",
            cause=dict(source.context),
        )
    return _finish(
        format_version=FRAGMENT_FORMAT_VERSION,
        source_kind=source_kind,
        source_fp1=source.value,
        keys=extracted.value,
        writer=writer,
        lineage=None,
        preset_name=None,
    )


def _finish(
    *,
    format_version: int,
    source_kind: str,
    source_fp1: Fingerprint,
    keys: Mapping[str, object],
    writer: WriterId | None,
    lineage: LineageEdge | None,
    preset_name: str | None,
) -> Result[ConfigFragment]:
    """Fingerprint the fragment and attach the occurrence-of edge when a writer is given."""
    identity: dict[str, object] = {
        "class": CONFIG_FRAGMENT_CLASS,
        "format_version": format_version,
        "keys": _plain(keys),
        "source_fp1": source_fp1.value,
        "source_kind": source_kind,
    }
    if preset_name is not None:
        identity["preset_name"] = preset_name
    derived = fingerprint(identity)
    if is_refusal(derived):
        return invalid(
            "keys",
            "the fragment keys are not fp1-clean identity content",
            cause=dict(derived.context),
        )
    edge = lineage
    if writer is not None:
        minted = LineageEdge.try_create(
            FRAGMENT_LINEAGE_EDGE_TYPE,
            derived.value,
            source_fp1,
            writer,
        )
        if is_refusal(minted):
            return minted
        edge = minted.value
    return Ok(
        ConfigFragment(
            format_version=format_version,
            source_kind=source_kind,
            source_fp1=source_fp1,
            keys=keys,
            fingerprint=derived.value,
            lineage=edge,
            preset_name=preset_name,
        )
    )


def _extract_keys(
    body: Mapping[str, object],
    projection: Mapping[str, str],
    *,
    source_kind: str,
) -> Result[dict[str, object]]:
    """Project mapped template sections into disjoint fragment namespaces."""
    sections = body.get("sections")
    if not isinstance(sections, Mapping):
        return invalid(
            "sections",
            "a Book/BMS definition body carries a sections mapping",
            given=repr(type(sections).__name__),
        )
    section_map = cast("Mapping[object, object]", sections)
    buckets: dict[str, dict[str, object]] = {}
    for raw_name, section in section_map.items():
        if not isinstance(raw_name, str):
            return invalid(
                "sections",
                "a section key is a string",
                given=repr(raw_name),
            )
        namespace = projection.get(raw_name)
        if namespace is None:
            continue
        if not isinstance(section, Mapping):
            return invalid(
                "sections",
                "each mapped section is a key->value mapping",
                section=raw_name,
                given=repr(type(section).__name__),
            )
        section_body = cast("Mapping[str, object]", section)
        buckets.setdefault(namespace, {})[raw_name] = _plain(section_body)
    if source_kind == SOURCE_BOOK:
        currency = clean_token(body.get("accounting_currency"))
        if currency is None:
            return invalid(
                "accounting_currency",
                "a Book definition declares accounting_currency (USD in V1)",
                given=repr(body.get("accounting_currency")),
            )
        buckets.setdefault("sizing", {})["accounting_currency"] = currency
    owned = _owned_namespaces(source_kind)
    if owned is not None:
        extra = [key for key in buckets if key not in owned]
        if extra:
            return invalid(
                "keys",
                "projected fragment keys left the owned namespace",
                extra=sorted(extra),
                owned=sorted(owned),
            )
    return Ok(cast("dict[str, object]", buckets))


def _source_fp1(record: RegistrationRecord | None, fallback: Fingerprint) -> Result[Fingerprint]:
    """Prefer the CT-22/CT-27 definition fp1 when the source is a definition record."""
    if record is None:
        return Ok(fallback)
    if record.kind not in {BOOK_RECORD_KIND, BMS_RECORD_KIND}:
        return Ok(record.stable_id)
    class_token = clean_token(record.body.get("class"))
    expected = "book-definition" if record.kind == BOOK_RECORD_KIND else "bms-definition"
    if class_token != expected:
        return Ok(record.stable_id)
    derived = fingerprint(_plain(record.body))
    if is_refusal(derived):
        return invalid(
            "body",
            "the definition body is not fp1-clean identity content",
            cause=dict(derived.context),
        )
    return Ok(derived.value)


def _require_port(port: object) -> Result[RegistryReadPort]:
    """The one library-owned registry-read port, or invalid input."""
    if not isinstance(port, RegistryReadPort):
        return invalid(
            "port",
            "Book/BMS fragments materialize through the one registry-read port",
            given=repr(type(port).__name__),
        )
    return Ok(port)


def _owned_namespaces(source_kind: str) -> frozenset[str] | None:
    """The key namespaces a Book or BMS fragment may emit. Presets are unchecked here."""
    if source_kind == SOURCE_BOOK:
        return BOOK_NAMESPACES
    if source_kind == SOURCE_BMS:
        return BMS_NAMESPACES
    return None


def _mixed_namespace_keys(keys: Mapping[str, object]) -> TypedRefusal | None:
    """Refuse a fragment that mixes Book-owned and BMS-owned top-level keys."""
    book_hit = any(key in BOOK_NAMESPACES for key in keys)
    bms_hit = any(key in BMS_NAMESPACES for key in keys)
    if book_hit and bms_hit:
        return invalid(
            "keys",
            "Book and BMS key namespaces are DISJOINT; a fragment may not mix them (B-3, DEC-0143)",
            book_keys=sorted(key for key in keys if key in BOOK_NAMESPACES),
            bms_keys=sorted(key for key in keys if key in BMS_NAMESPACES),
        )
    return None


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


def _coerce_format_version(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _plain(value: object) -> object:
    """JSON-native copy of frozen mappings/tuples for fp1 identity content."""
    if isinstance(value, Mapping):
        nested = cast("Mapping[str, object]", value)
        out: dict[str, object] = {}
        for key in nested:
            item: object = nested[key]
            out[key] = _plain(item)
        return out
    if isinstance(value, tuple):
        sequence = cast("Sequence[object]", value)
        return [_plain(item) for item in sequence]
    return value


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    """Deep-freeze a mapping so a later caller mutation cannot reach the fragment."""
    frozen: dict[str, object] = {}
    for key, item in value.items():
        if isinstance(item, Mapping):
            nested = cast("Mapping[str, object]", item)
            frozen[key] = _freeze_mapping(nested)
        elif isinstance(item, (list, tuple)):
            sequence = cast("Sequence[object]", item)
            frozen[key] = tuple(sequence)
        else:
            frozen[key] = item
    return MappingProxyType(frozen)
