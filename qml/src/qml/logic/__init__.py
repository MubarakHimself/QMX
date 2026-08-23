"""Logic-artifact identity: distribution + version + source-manifest fp1 (QL-2).

A governed bot is two artifacts. The logic half is a versioned plain-Python
distribution whose identity is distribution identity + version + a normalized,
reproducible source-manifest fingerprint. That fingerprint is computed only by
calling qmf-core's canonical ``fp1`` function — qml never hashes (DEC-0172,
DEC-0108). Wheel timestamps and build metadata are stripped from the tree and
are not identity fields, so identical source in two sandboxes yields one Bot
``fp1``. The library is pure: the host supplies the source tree in memory.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qml._refuse import clean_token, invalid, unavailable

__all__ = [
    "LOGIC_REFERENCE_CLASS",
    "LogicIdentity",
    "fingerprint_source_manifest",
    "mint_logic_identity",
    "normalize_source_manifest",
    "resolve_logic_at_layer1",
]

LOGIC_REFERENCE_CLASS: Final[str] = "logic-reference"
_DISTRIBUTION_FIELD: Final[str] = "distribution"
_VERSION_FIELD: Final[str] = "distribution_version"
_MANIFEST_FIELD: Final[str] = "source_manifest"

_BUILD_SUFFIXES: Final[tuple[str, ...]] = (".pyc", ".pyo", ".whl", ".egg", ".pyd", ".so")


def normalize_source_manifest(source_tree: object) -> Result[Mapping[str, str]]:
    """Normalize a source tree to POSIX-relative path -> text, dropping build artifacts.

    Paths use ``/``, NFC, no ``..`` or absolute forms. ``__pycache__``, wheel
    files, ``*.dist-info`` / ``*.egg-info``, and compiled artifacts are omitted
    so wheel timestamps and build metadata never enter identity (DEC-0172).
    """
    if not isinstance(source_tree, Mapping):
        return invalid(
            "source_tree",
            "a logic source tree is a mapping of relative path -> file content",
            given=type(source_tree).__name__,
        )
    files: dict[str, str] = {}
    mapping = cast("Mapping[object, object]", source_tree)
    for raw_path, raw_content in mapping.items():
        if not isinstance(raw_path, str):
            return invalid(
                "path",
                "source-manifest paths are strings",
                given=repr(raw_path),
            )
        posix = _posix_path(raw_path)
        if is_refusal(posix):
            return posix
        path = posix.value
        if _is_build_artifact(path):
            continue
        content = _normalize_content(raw_content)
        if is_refusal(content):
            return content
        if path in files:
            return invalid(
                "path",
                "duplicate source path after normalization; a fingerprint must not "
                "fork or collapse on path form",
                path=path,
            )
        files[path] = content.value
    if not files:
        return invalid(
            "source_tree",
            "a logic source-manifest requires at least one source file after "
            "dropping wheel and build artifacts",
        )
    return Ok(MappingProxyType(files))


def fingerprint_source_manifest(source_tree: object) -> Result[Fingerprint]:
    """``fp1:sha256:<hex>`` over the normalized source tree, via qmf-core only."""
    normalized = normalize_source_manifest(source_tree)
    if is_refusal(normalized):
        return normalized
    return fingerprint(dict(normalized.value))


@dataclass(frozen=True, slots=True)
class LogicIdentity:
    """Identity of the logic half of a governed bot (DEC-0172).

    ``distribution`` + ``version`` + ``source_manifest`` (an ``fp1`` over the
    source tree). Package SemVer of qml, wheel timestamps, and build metadata
    are not fields and never enter ``fp1``.
    """

    distribution: str
    version: str
    source_manifest: Fingerprint

    def fp1_identity(self) -> dict[str, object]:
        """Canonical semantic content for ``fp1``. SemVer and occurrence facts omitted."""
        return {
            "class": LOGIC_REFERENCE_CLASS,
            _DISTRIBUTION_FIELD: self.distribution,
            _VERSION_FIELD: self.version,
            _MANIFEST_FIELD: self.source_manifest.value,
        }

    def fingerprint_content(self) -> Result[Fingerprint]:
        """``fp1`` over the logic identity, computed only by qmf-core."""
        return fingerprint(self)

    def as_logic_reference(self) -> dict[str, object]:
        """The CT-33 ``logic_reference`` field — identity-bearing on the Bot definition."""
        return self.fp1_identity()

    @classmethod
    def try_create(
        cls,
        distribution: object,
        version: object,
        source_tree: object = None,
        *,
        source_manifest: object = None,
    ) -> Result[LogicIdentity]:
        """Validate and build a logic identity from a source tree or an existing fp1."""
        dist = clean_token(distribution)
        if dist is None:
            return invalid(
                _DISTRIBUTION_FIELD,
                "a logic distribution identity is a non-empty opaque token",
                given=repr(distribution),
            )
        ver = clean_token(version)
        if ver is None:
            return invalid(
                _VERSION_FIELD,
                "a logic distribution version is a non-empty identity string",
                given=repr(version),
            )
        manifest = _resolve_manifest(source_tree, source_manifest)
        if is_refusal(manifest):
            return manifest
        return Ok(cls(distribution=dist, version=ver, source_manifest=manifest.value))

    @classmethod
    def try_from_payload(cls, payload: object) -> Result[LogicIdentity]:
        """Admit a logic-reference mapping (identity payload or a declaration body)."""
        if isinstance(payload, cls):
            return Ok(payload)
        if not isinstance(payload, Mapping):
            return invalid(
                "logic_reference",
                "a logic reference is a mapping of distribution, version, and "
                "source-manifest fingerprint",
                given=type(payload).__name__,
            )
        mapping = cast("Mapping[str, object]", payload)
        nested = mapping.get("logic_reference")
        if nested is not None:
            if isinstance(nested, cls):
                return Ok(nested)
            if isinstance(nested, Mapping):
                return cls.try_from_payload(cast("Mapping[str, object]", nested))
            return invalid(
                "logic_reference",
                "a logic reference is a mapping of distribution, version, and "
                "source-manifest fingerprint",
                given=type(nested).__name__,
            )
        body = mapping.get("body")
        if isinstance(body, Mapping) and "logic_reference" in body:
            return cls.try_from_payload(cast("Mapping[str, object]", body))
        if _DISTRIBUTION_FIELD not in mapping and _MANIFEST_FIELD not in mapping:
            return invalid(
                "logic_reference",
                "the logic reference is mandatory, because a governed bot is exactly two artifacts",
            )
        return cls.try_create(
            mapping.get(_DISTRIBUTION_FIELD),
            mapping.get(_VERSION_FIELD),
            source_manifest=mapping.get(_MANIFEST_FIELD),
        )


def mint_logic_identity(
    distribution: object,
    version: object,
    source_tree: object,
) -> Result[LogicIdentity]:
    """Mint logic identity from a host-supplied in-memory source tree (DEC-0172)."""
    return LogicIdentity.try_create(distribution, version, source_tree)


def resolve_logic_at_layer1(reference: object, catalog: object) -> Result[LogicIdentity]:
    """Resolve a cited logic distribution against a host as-of catalog (QL-8).

    A miss is ``unavailable dependency``, never a silent pass — the logic
    reference is mandatory because a governed bot is exactly two artifacts
    (DEC-0172, DEC-0178).
    """
    wanted = LogicIdentity.try_from_payload(reference)
    if is_refusal(wanted):
        return wanted
    items = _iter_catalog(catalog)
    if is_refusal(items):
        return items
    key = _identity_key(wanted.value)
    for item in items.value:
        extracted = _extract_logic(item)
        if extracted is None or is_refusal(extracted):
            continue
        if _identity_key(extracted.value) == key:
            return extracted
    return unavailable(
        "logic_reference",
        "the cited logic distribution does not resolve; an unresolvable logic "
        "distribution is an unavailable dependency, never a silent pass",
        distribution=wanted.value.distribution,
        distribution_version=wanted.value.version,
        source_manifest=wanted.value.source_manifest.value,
        journal=True,
    )


def _resolve_manifest(source_tree: object, source_manifest: object) -> Result[Fingerprint]:
    """Exactly one of a source tree or an existing source-manifest fp1."""
    tree_given = source_tree is not None
    manifest_given = source_manifest is not None
    if tree_given and manifest_given:
        computed = fingerprint_source_manifest(source_tree)
        if is_refusal(computed):
            return computed
        parsed = _coerce_fingerprint(source_manifest)
        if is_refusal(parsed):
            return parsed
        if computed.value.value != parsed.value.value:
            return invalid(
                _MANIFEST_FIELD,
                "the cited source-manifest fingerprint does not match the source tree",
                given=parsed.value.value,
                computed=computed.value.value,
            )
        return computed
    if tree_given:
        return fingerprint_source_manifest(source_tree)
    if manifest_given:
        return _coerce_fingerprint(source_manifest)
    return invalid(
        "source_tree",
        "logic identity needs a source tree or a source-manifest fp1",
    )


def _coerce_fingerprint(value: object) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    parsed = Fingerprint.try_create(value)
    if is_refusal(parsed):
        return invalid(
            _MANIFEST_FIELD,
            "the source-manifest fingerprint is fp1:sha256:<hex>, computed by qmf-core",
            given=repr(value),
        )
    return parsed


def _posix_path(path: str) -> Result[str]:
    """Normalize a relative source path; refuse absolute forms and ``..``."""
    raw = path.replace("\\", "/")
    if "\x00" in raw:
        return invalid("path", "a source path must not contain NUL", given=repr(path))
    if raw.startswith("/") or raw.startswith("//") or (len(raw) >= 2 and raw[1] == ":"):
        return invalid(
            "path",
            "a source-manifest path is a relative POSIX path, never absolute",
            given=path,
        )
    parts: list[str] = []
    for part in raw.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            return invalid(
                "path",
                "a source-manifest path must not contain parent-directory components",
                given=path,
            )
        parts.append(part)
    if not parts:
        return invalid(
            "path", "a source-manifest path is a non-empty relative file path", given=path
        )
    return Ok(unicodedata.normalize("NFC", "/".join(parts)))


def _is_build_artifact(path: str) -> bool:
    """True for wheel/build outputs that must never enter identity."""
    for part in path.split("/"):
        if part == "__pycache__":
            return True
        lowered = part.lower()
        if lowered.endswith(".dist-info") or lowered.endswith(".egg-info"):
            return True
    name = path.rsplit("/", 1)[-1].lower()
    return any(name.endswith(suffix) for suffix in _BUILD_SUFFIXES)


def _normalize_content(value: object) -> Result[str]:
    """Admit file bytes as UTF-8 text, or lowercase hex when the bytes are not UTF-8."""
    if isinstance(value, str):
        return Ok(value)
    if isinstance(value, bytes):
        try:
            return Ok(value.decode("utf-8"))
        except UnicodeDecodeError:
            return Ok(value.hex())
    return invalid(
        "content",
        "source-manifest file content is a string or bytes",
        given=type(value).__name__,
    )


def _iter_catalog(catalog: object) -> Result[tuple[object, ...]]:
    if isinstance(catalog, Mapping):
        mapping = cast("Mapping[object, object]", catalog)
        return Ok(tuple(mapping.values()))
    if isinstance(catalog, Sequence) and not isinstance(catalog, (str, bytes)):
        return Ok(tuple(cast("Sequence[object]", catalog)))
    return invalid(
        "catalog",
        "Layer 1 resolves a logic distribution against an as-of catalog of logic identities",
        given=type(catalog).__name__,
    )


def _identity_key(item: LogicIdentity) -> tuple[str, str, str]:
    return (item.distribution, item.version, item.source_manifest.value)


def _extract_logic(item: object) -> Result[LogicIdentity] | None:
    if isinstance(item, LogicIdentity):
        return Ok(item)
    if isinstance(item, Mapping):
        mapping = cast("Mapping[str, object]", item)
        body = mapping.get("body")
        nested_ref = isinstance(body, Mapping) and "logic_reference" in body
        if (
            _DISTRIBUTION_FIELD not in mapping
            and _MANIFEST_FIELD not in mapping
            and "logic_reference" not in mapping
            and not nested_ref
        ):
            return None
        return LogicIdentity.try_from_payload(mapping)
    return None
