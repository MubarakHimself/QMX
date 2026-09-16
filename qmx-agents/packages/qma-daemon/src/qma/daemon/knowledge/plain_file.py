"""Read-only plain-file KnowledgeSource adapter (CT-44; AD-19; FR-Q65).

Imposes no schema, folder or field convention on the corpus. QMX adapts to the
library; the library is never built around QMX. Write-back is refused.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from types import MappingProxyType

from qma.core.ports.knowledge import (
    KNOWLEDGE_SOURCE_KINDS,
    CorpusSnapshot,
    build_corpus_snapshot,
    literal_search,
    parse_confidence_dimensions,
    refuse_knowledge_write_back,
)
from qmf.core import Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "DEFAULT_PLAIN_FILE_CONFIDENCE_DIMENSIONS",
    "PlainFileLibrarySource",
]


# Default six-dimension keys when a source does not declare its own (STRATS
# ground-state §4.6). Keys remain source-declared for the life of source_id —
# this tuple is only a constructor convenience for the plain-file adapter.
DEFAULT_PLAIN_FILE_CONFIDENCE_DIMENSIONS: tuple[str, ...] = (
    "extraction_confidence",
    "rule_explicitness",
    "source_quality_completeness",
    "ambiguity_unresolved_status",
    "empirical_status",
    "portability_market_transfer_status",
)


def _normalize_patterns(patterns: Sequence[str] | None) -> tuple[str, ...]:
    if not patterns:
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for item in patterns:
        text = item.replace("\\", "/").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return tuple(out)


def _is_hidden_rel(rel: str) -> bool:
    return any(part.startswith(".") for part in PurePosixPath(rel).parts)


def _pattern_matches(rel: str, pattern: str) -> bool:
    """Match a posix relative path against an include/exclude pattern.

    Trailing-slash patterns are directories (a single segment matches any
    path component; multi-segment matches a contiguous component run).
    Globs use :meth:`PurePosixPath.full_match`. Other patterns are exact.
    """
    path = PurePosixPath(rel)
    if pattern.endswith("/"):
        dirname = pattern.rstrip("/")
        if dirname == "":
            return False
        pat_parts = PurePosixPath(dirname).parts
        rel_parts = path.parts
        n = len(pat_parts)
        if n == 0 or n > len(rel_parts):
            return False
        if n == 1:
            return pat_parts[0] in rel_parts
        last = len(rel_parts) - n + 1
        return any(rel_parts[index : index + n] == pat_parts for index in range(last))
    if any(token in pattern for token in "*?["):
        return path.full_match(pattern)
    return rel == pattern


def _path_participates(rel: str, *, include: Sequence[str], exclude: Sequence[str]) -> bool:
    # Built-in rule is hidden path parts only — no corpus schema.
    if _is_hidden_rel(rel):
        return False
    if include and not any(_pattern_matches(rel, pattern) for pattern in include):
        return False
    return not any(_pattern_matches(rel, pattern) for pattern in exclude)


@dataclass
class PlainFileLibrarySource:
    """Read-only adapter over an external plain-file library root.

    Satisfies :class:`~qma.core.ports.knowledge.KnowledgeSource`. Does not
    invent layout: every regular non-hidden file under ``root_path``
    participates unless the caller supplies include/exclude patterns.
    Those patterns are plugin config, never a hardcoded corpus schema.
    """

    root_path: Path
    source_id: str
    confidence_dimensions: tuple[str, ...] = DEFAULT_PLAIN_FILE_CONFIDENCE_DIMENSIONS
    kind: str = "plain_file_library"
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    _last_files: dict[str, bytes] = field(default_factory=dict[str, bytes], repr=False)

    def __post_init__(self) -> None:
        self.root_path = Path(self.root_path)
        if self.source_id.strip() == "":
            msg = "source_id is a non-empty string (CT-44; AD-1)"
            raise ValueError(msg)
        self.source_id = self.source_id.strip()
        dims = parse_confidence_dimensions(self.confidence_dimensions)
        if is_refusal(dims):
            raise ValueError(str(dims.context.get("reason", "invalid confidence_dimensions")))
        self.confidence_dimensions = dims.value
        if self.kind not in KNOWLEDGE_SOURCE_KINDS:
            msg = f"kind {self.kind!r} is not a known KnowledgeSource kind (CT-44; DEC-0318)"
            raise ValueError(msg)
        self.include = _normalize_patterns(self.include)
        self.exclude = _normalize_patterns(self.exclude)

    def declaration(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "source_id": self.source_id,
                "kind": self.kind,
                "adapter": "plain_file_library",
                "read_only": True,
                "impose_schema": False,
                "confidence_dimensions": list(self.confidence_dimensions),
                "hardcoded_layout": False,
                "include": list(self.include),
                "exclude": list(self.exclude),
            }
        )

    def write(self, *_args: object, **_kwargs: object) -> Result[None]:
        """Explicit write-back refusal — library is never mutated by QMX."""
        return refuse_knowledge_write_back(source_id=self.source_id)

    def snapshot(self) -> Result[CorpusSnapshot]:
        files = self._read_tree()
        if is_refusal(files):
            return files
        self._last_files = dict(files.value)
        return build_corpus_snapshot(source_id=self.source_id, file_bytes=files.value)

    def search(self, snapshot: CorpusSnapshot, query: str) -> Result[tuple[str, ...]]:
        scoped = self._bytes_for_snapshot(snapshot)
        if is_refusal(scoped):
            return scoped
        return literal_search(scoped.value, query)

    def invalidate_cache(self) -> None:
        """Drop the tree captured at the last successful ``snapshot()``."""
        self._last_files.clear()

    def retrieve(self, snapshot: CorpusSnapshot, locator: object) -> Result[bytes]:
        if not isinstance(locator, str) or locator.strip() == "":
            return invalid_input(
                "locator",
                "locator is a non-empty in-snapshot path (CT-44; FR-Q65)",
                given=repr(locator),
            )
        path = locator.strip().replace("\\", "/").split("#", 1)[0]
        scoped = self._bytes_for_snapshot(snapshot)
        if is_refusal(scoped):
            return scoped
        if path not in scoped.value:
            return invalid_input(
                "locator",
                "locator is not present in the pinned CorpusSnapshot (CT-44)",
                locator=path,
                snapshot_ref=snapshot.id,
            )
        return Ok(scoped.value[path])

    def _read_tree(self) -> Result[dict[str, bytes]]:
        root = self.root_path
        if not root.exists() or not root.is_dir():
            return invalid_input(
                "root_path",
                "plain-file KnowledgeSource root_path must be an existing directory "
                "(CT-44; FR-Q65)",
                given=str(root),
            )
        files: dict[str, bytes] = {}
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if not _path_participates(rel, include=self.include, exclude=self.exclude):
                continue
            try:
                files[rel] = path.read_bytes()
            except OSError as exc:
                return policy_rejection(
                    "root_path",
                    f"failed to read corpus file {rel!r}: {exc}",
                    source_id=self.source_id,
                )
        return Ok(files)

    def _bytes_for_snapshot(self, snapshot: CorpusSnapshot) -> Result[dict[str, bytes]]:
        if snapshot.source_id != self.source_id:
            return invalid_input(
                "snapshot",
                "CorpusSnapshot source_id must match the adapter source_id (CT-44)",
                snapshot_source_id=snapshot.source_id,
                source_id=self.source_id,
            )
        # Prefer the tree captured at snapshot() so search/retrieve stay
        # consistent with the pinned digests even if the live tree moved.
        if self._last_files:
            live = build_corpus_snapshot(
                source_id=self.source_id,
                file_bytes=self._last_files,
            )
            if not is_refusal(live) and live.value.id == snapshot.id:
                return Ok(dict(self._last_files))
        refreshed = self._read_tree()
        if is_refusal(refreshed):
            return refreshed
        current = build_corpus_snapshot(
            source_id=self.source_id,
            file_bytes=refreshed.value,
        )
        if is_refusal(current):
            return current
        if current.value.id != snapshot.id:
            return policy_rejection(
                "snapshot",
                "live corpus bytes no longer match the pinned CorpusSnapshot; "
                "cite retained copies or re-pin (CT-44; FR-Q65)",
                snapshot_ref=snapshot.id,
                live_snapshot_ref=current.value.id,
            )
        self._last_files = dict(refreshed.value)
        return Ok(dict(refreshed.value))
