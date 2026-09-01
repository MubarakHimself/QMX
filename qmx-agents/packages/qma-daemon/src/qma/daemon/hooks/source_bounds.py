"""Source-bound hook selection and matcher registration (FR-Q34; CT-41; AD-10).

The daemon applies the source bound before the matcher. A registration whose
matcher could resolve outside its bound is refused at registration.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

from qma.core.plugins.hooks import HookSource
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "HookSourceBinding",
    "ScopeSegmentView",
    "assert_matcher_within_source",
    "event_within_source_bound",
    "matcher_matches",
    "parse_scope_segments",
    "resolve_source",
    "select_handlers_for_event",
]


_SCOPE_KIND_ORDER: Final[tuple[str, ...]] = (
    "desk",
    "quant",
    "mission",
    "task",
    "session",
    "agent",
    "subagent",
)
_SCOPE_CLAIM_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:^|[|,])\s*(desk|role|mission|plugin)\s*[:=]\s*([^\s|,]+)"
)
_SAFE_MATCHER_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9_\- ,|]*$")


@dataclass(frozen=True, slots=True)
class ScopeSegmentView:
    """Minimal ``{kind, id}`` view — no wire import at the bound check."""

    kind: str
    id: str


@dataclass(frozen=True, slots=True)
class HookSourceBinding:
    """Registered source identity that bounds events a handler may receive."""

    source: HookSource
    source_ref: str
    # Plugin-only: declared scope prefixes (desk→…); empty means no scopes.
    allowed_scopes: tuple[tuple[ScopeSegmentView, ...], ...] = ()
    matcher: str | None = None

    def __post_init__(self) -> None:
        if self.source_ref.strip() == "":
            msg = "source_ref must be a non-empty string (FR-Q34; AD-10)"
            raise VocabularyError(msg)


def parse_scope_segments(value: object) -> tuple[ScopeSegmentView, ...]:
    """Parse a scope_path-like sequence into segment views."""
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise VocabularyError("scope_path must be a sequence of {kind, id} segments")
    segments: list[ScopeSegmentView] = []
    expected = 0
    for raw_obj in cast("Sequence[object]", value):
        if isinstance(raw_obj, ScopeSegmentView):
            kind, seg_id = raw_obj.kind, raw_obj.id
        elif isinstance(raw_obj, Mapping):
            raw_map = cast("Mapping[object, object]", raw_obj)
            kind_obj, id_obj = raw_map.get("kind"), raw_map.get("id")
            if not isinstance(kind_obj, str) or not isinstance(id_obj, str):
                raise VocabularyError("scope_path segment must be {kind, id}")
            kind, seg_id = kind_obj, id_obj
        else:
            raise VocabularyError(
                f"scope_path segment must be {{kind, id}}; got {type(raw_obj).__name__}"
            )
        if kind not in _SCOPE_KIND_ORDER:
            raise VocabularyError(f"unknown scope_path kind {kind!r}")
        index = _SCOPE_KIND_ORDER.index(kind)
        if index != expected:
            raise VocabularyError(
                "scope_path ancestors must be contiguous from desk "
                f"(expected {_SCOPE_KIND_ORDER[expected]!r}, got {kind!r})"
            )
        if seg_id.strip() == "":
            raise VocabularyError("scope_path id must be non-empty")
        segments.append(ScopeSegmentView(kind=kind, id=seg_id))
        expected = index + 1
    return tuple(segments)


def _segment_id(segments: Sequence[ScopeSegmentView], kind: str) -> str | None:
    for segment in segments:
        if segment.kind == kind:
            return segment.id
    return None


def _is_prefix(
    prefix: Sequence[ScopeSegmentView],
    full: Sequence[ScopeSegmentView],
) -> bool:
    if len(prefix) > len(full):
        return False
    return tuple(prefix) == tuple(full[: len(prefix)])


def event_within_source_bound(
    binding: HookSourceBinding,
    *,
    scope_path: Sequence[ScopeSegmentView | Mapping[str, str]] | None = None,
    role_id: str | None = None,
    plugin_id: str | None = None,
) -> bool:
    """True when the event lies inside the handler's source bound (FR-Q34)."""
    segments = parse_scope_segments(scope_path) if scope_path is not None else ()
    source = binding.source
    ref = binding.source_ref
    if source is HookSource.DESK:
        return _segment_id(segments, "desk") == ref
    if source is HookSource.MISSION:
        return _segment_id(segments, "mission") == ref
    if source is HookSource.ROLE:
        return role_id is not None and role_id == ref
    if source is HookSource.PLUGIN:
        if plugin_id is not None and plugin_id != ref:
            return False
        if not binding.allowed_scopes:
            return False
        if not segments:
            return False
        return any(_is_prefix(allowed, segments) for allowed in binding.allowed_scopes)
    return False


def assert_matcher_within_source(
    binding: HookSourceBinding,
    matcher: str | None,
) -> Result[str | None]:
    """Refuse a matcher that could resolve outside the registered source.

    Safe tool-name matchers (``[A-Za-z0-9_\\- ,|]`` / ``*`` / empty) stay inside
    the source bound because the bound is applied before the matcher. Explicit
    ``desk|role|mission|plugin`` claims must equal ``source_ref`` for the same
    source class and may not name a wider or foreign scope.
    """
    if matcher is None or matcher.strip() == "" or matcher.strip() == "*":
        return Ok(None if matcher is None or matcher.strip() == "" else "*")
    text = matcher.strip()
    claims = list(_SCOPE_CLAIM_RE.finditer(text))
    if claims:
        for match in claims:
            kind, claimed_id = match.group(1), match.group(2)
            if kind != binding.source.value:
                return policy_rejection(
                    "matcher",
                    "matcher claims source class "
                    f"{kind!r} outside registered source "
                    f"{binding.source.value!r} (FR-Q34; AD-10)",
                    given=text,
                )
            if claimed_id != binding.source_ref:
                return policy_rejection(
                    "matcher",
                    "matcher could resolve outside registered source_ref "
                    f"{binding.source_ref!r} (FR-Q34; AD-10)",
                    given=text,
                )
        return Ok(text)
    return Ok(text)


def matcher_matches(matcher: str | None, match_value: str | None) -> bool:
    """Apply the matcher after the source bound (exact list or unanchored regex)."""
    if matcher is None or matcher in {"", "*"}:
        return True
    if match_value is None:
        return False
    if _SAFE_MATCHER_RE.fullmatch(matcher):
        options = {part.strip() for part in matcher.replace(",", "|").split("|") if part.strip()}
        return match_value in options
    try:
        return re.compile(matcher).search(match_value) is not None
    except re.error:
        return False


def select_handlers_for_event[H](
    handlers: Sequence[H],
    *,
    scope_path: Sequence[ScopeSegmentView] | None,
    role_id: str | None,
    plugin_id: str | None,
    match_value: str | None,
    get_binding: Callable[[H], HookSourceBinding],
) -> list[H]:
    """Filter handlers: source bound first, then matcher (FR-Q34)."""
    selected: list[H] = []
    for handler in handlers:
        binding = get_binding(handler)
        if not event_within_source_bound(
            binding,
            scope_path=scope_path,
            role_id=role_id,
            plugin_id=plugin_id,
        ):
            continue
        if not matcher_matches(binding.matcher, match_value):
            continue
        selected.append(handler)
    return selected


def resolve_source(source: HookSource | str) -> Result[HookSource]:
    """Parse a closed HookSource."""
    try:
        resolved = source if isinstance(source, HookSource) else parse_closed(HookSource, source)
    except VocabularyError as exc:
        return invalid_input("source", str(exc), given=repr(source))
    return Ok(resolved)
