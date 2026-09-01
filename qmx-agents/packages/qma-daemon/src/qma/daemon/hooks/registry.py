"""Mandatory daemon hook registry (AD-10; FR-Q30/FR-Q31; CT-41; DEC-0309, DEC-0339).

Hooks are the single enforcement and control surface — never optional. Every
daemon-owned primitive ships ``before_<verb>`` and ``after_<verb>``; the only
phase-less blocking controls are ``agent_stop`` and ``review_required``. An
agent-reachable write into a daemon-owned store passes that primitive's
``before_*`` gate with no bypass path. Registration validates the phase law
so an illegal decision or field never reaches runtime resolution.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, TypeVar, cast

from qma.core.plugins.context import Disposer, HookHandler
from qma.core.plugins.hooks import (
    HookPhase,
    HookResult,
    HookSource,
    assert_hook_result_phase_law,
    build_hook_event,
    build_hook_result,
)
from qma.core.vocabulary.enums import HookControl, HookResultDecision, HookVerb
from qma.core.vocabulary.hooks import (
    HOOK_CONTROLS,
    HOOK_VERBS,
    empty_result_decision_for_event,
    legal_decisions_for_event,
    legal_fields_for_event,
    most_restrictive_hook_result,
    parse_hook_event_name,
    validate_registration_phase_law,
)
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result, is_ok
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "AGENT_REACHABLE_WRITE_VERBS",
    "BYPASS_WRITE_PATHS",
    "DAEMON_OWNED_HOOK_VERBS",
    "PHASE_LESS_CONTROLS",
    "HookRegistry",
    "HookRegistryEntry",
    "PrimitiveInvocation",
    "assert_no_bypass_write_path",
    "default_empty_hook_result",
    "event_names_for_verb",
    "resolve_parallel_hook_results",
]


T = TypeVar("T")

DAEMON_OWNED_HOOK_VERBS: Final[tuple[HookVerb, ...]] = HOOK_VERBS
PHASE_LESS_CONTROLS: Final[tuple[HookControl, ...]] = HOOK_CONTROLS

# Agent-reachable writes into daemon-owned stores (FR-Q30; AD-10). Each must
# pass its ``before_*`` gate; there is no secondary enforcement surface.
AGENT_REACHABLE_WRITE_VERBS: Final[frozenset[HookVerb]] = frozenset(
    {
        HookVerb.LEDGER_APPEND,
        HookVerb.MEMORY_WRITE,
        HookVerb.SKILL_WRITE,
        HookVerb.ARTIFACT_REGISTER,
        HookVerb.EXPERIMENT_REGISTER,
        HookVerb.HOOK_REGISTER,
        HookVerb.PROPOSAL_STAGE,
        HookVerb.PROPOSAL_APPLY,
    }
)

# Explicit empty set: no optional mode, secondary surface, or ungated write.
BYPASS_WRITE_PATHS: Final[frozenset[str]] = frozenset()

_BLOCKING_BEFORE_DECISIONS: Final[frozenset[HookResultDecision]] = frozenset(
    {
        HookResultDecision.DENY,
        HookResultDecision.DEFER,
        HookResultDecision.ASK,
        HookResultDecision.BLOCK_STOP,
    }
)


@dataclass(frozen=True, slots=True)
class HookRegistryEntry:
    """One closed registry slot: a before_/after_ verb event or a control."""

    event: str
    phase: HookPhase
    verb: HookVerb | None = None
    control: HookControl | None = None

    @property
    def legal_decisions(self) -> frozenset[HookResultDecision]:
        return legal_decisions_for_event(self.event)

    @property
    def legal_fields(self) -> frozenset[str]:
        return legal_fields_for_event(self.event)

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "event": self.event,
            "phase": self.phase.value,
            "legal_decisions": tuple(sorted(d.value for d in self.legal_decisions)),
            "legal_fields": tuple(sorted(self.legal_fields)),
        }
        if self.verb is not None:
            payload["verb"] = self.verb.value
        if self.control is not None:
            payload["control"] = self.control.value
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class PrimitiveInvocation:
    """Outcome of evaluating one daemon-owned primitive through before_/after_."""

    verb: HookVerb
    before_event: str
    after_event: str
    before_result: HookResult
    after_result: HookResult
    value: object = None
    agent_write: bool = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "verb": self.verb.value,
                "before_event": self.before_event,
                "after_event": self.after_event,
                "before_decision": self.before_result.decision.value,
                "after_decision": self.after_result.decision.value,
                "agent_write": self.agent_write,
                "value": self.value,
            }
        )


def event_names_for_verb(verb: HookVerb | str) -> tuple[str, str]:
    """Return ``(before_<verb>, after_<verb>)`` for a daemon-owned verb."""
    resolved = parse_closed(HookVerb, verb) if not isinstance(verb, HookVerb) else verb
    before = f"before_{resolved.value}"
    after = f"after_{resolved.value}"
    return before, after


def default_empty_hook_result(event: str) -> HookResult:
    """Resolution when no handler returns a result (FR-Q31 empty-result law).

    ``before_*`` and ``after_tool`` resolve to ``allow``; phase-less controls
    and every other ``after_*`` resolve to ``observe``. Never a null decision.
    """
    name = parse_hook_event_name(event)
    decision = empty_result_decision_for_event(name)
    return build_hook_result(decision, reason="empty_handler")


def resolve_parallel_hook_results(results: Sequence[HookResult]) -> HookResult:
    """Most-restrictive-wins under total precedence; observe does not participate."""
    if not results:
        raise VocabularyError(
            "parallel resolution requires at least one HookResult; "
            "use default_empty_hook_result for missing handlers (FR-Q31)"
        )
    winner = most_restrictive_hook_result(tuple(item.decision for item in results))
    for item in results:
        if item.decision is winner:
            return item
    return build_hook_result(winner)


def assert_no_bypass_write_path() -> None:
    """Hard invariant: no ungated agent-write surface exists (FR-Q30)."""
    if BYPASS_WRITE_PATHS:
        msg = (
            "bypass write paths are forbidden; hooks are the sole enforcement "
            f"surface, found={sorted(BYPASS_WRITE_PATHS)!r} (FR-Q30; AD-10)"
        )
        raise RuntimeError(msg)


def _build_v1_entries() -> tuple[HookRegistryEntry, ...]:
    entries: list[HookRegistryEntry] = []
    for verb in DAEMON_OWNED_HOOK_VERBS:
        before, after = event_names_for_verb(verb)
        entries.append(HookRegistryEntry(event=before, phase=HookPhase.BEFORE, verb=verb))
        entries.append(HookRegistryEntry(event=after, phase=HookPhase.AFTER, verb=verb))
    for control in PHASE_LESS_CONTROLS:
        entries.append(
            HookRegistryEntry(
                event=control.value,
                phase=HookPhase.PHASE_LESS,
                control=control,
            )
        )
    return tuple(entries)


_V1_ENTRIES: Final[tuple[HookRegistryEntry, ...]] = _build_v1_entries()


@dataclass(frozen=True, slots=True)
class _HandlerRecord:
    source: HookSource
    handler: HookHandler
    decisions: frozenset[HookResultDecision]
    fields: frozenset[str]


@dataclass
class HookRegistry:
    """Closed-and-addable v1 hook registry owned by the daemon (FR-Q30/FR-Q31).

    Initialized with the full twenty-three before_/after_ pairs plus the two
    phase-less controls. Unknown verbs and incomplete pairs are refused.
    Registration validates the phase law for declared decisions and fields.
    """

    _handlers: dict[str, list[_HandlerRecord]] = field(
        default_factory=dict[str, list[_HandlerRecord]]
    )
    _entries: tuple[HookRegistryEntry, ...] = field(default=_V1_ENTRIES, init=False)
    _by_event: Mapping[str, HookRegistryEntry] = field(init=False)

    def __post_init__(self) -> None:
        by_event = {entry.event: entry for entry in self._entries}
        object.__setattr__(self, "_by_event", MappingProxyType(by_event))
        # Construction-time completeness: every verb has both phases.
        for verb in DAEMON_OWNED_HOOK_VERBS:
            before, after = event_names_for_verb(verb)
            if before not in by_event or after not in by_event:
                msg = (
                    f"daemon primitive {verb.value!r} missing before_/after_ pair; "
                    "omission requires a spine amendment (FR-Q30; AD-10)"
                )
                raise RuntimeError(msg)
        controls = {entry.event for entry in self._entries if entry.phase is HookPhase.PHASE_LESS}
        if controls != {c.value for c in PHASE_LESS_CONTROLS}:
            msg = (
                "phase-less controls must be exactly agent_stop and "
                f"review_required, found={sorted(controls)!r} (FR-Q30; AD-10)"
            )
            raise RuntimeError(msg)
        assert_no_bypass_write_path()

    @property
    def event_names(self) -> frozenset[str]:
        return frozenset(self._by_event)

    @property
    def verbs(self) -> tuple[HookVerb, ...]:
        return DAEMON_OWNED_HOOK_VERBS

    @property
    def controls(self) -> tuple[HookControl, ...]:
        return PHASE_LESS_CONTROLS

    def entries(self) -> Sequence[HookRegistryEntry]:
        """Inspect the closed v1 registry slots."""
        return self._entries

    def entry(self, event: str) -> HookRegistryEntry | None:
        return self._by_event.get(event)

    def has_complete_pair(self, verb: HookVerb | str) -> bool:
        try:
            before, after = event_names_for_verb(verb)
        except VocabularyError:
            return False
        return before in self._by_event and after in self._by_event

    def resolve_verb(self, verb: object) -> Result[HookVerb]:
        """Accept only a registered daemon-owned hook verb."""
        if not isinstance(verb, (str, HookVerb)):
            return invalid_input(
                "verb",
                "hook verb must be a registered daemon-owned primitive (FR-Q30; AD-10)",
                given=repr(verb),
            )
        try:
            resolved = verb if isinstance(verb, HookVerb) else parse_closed(HookVerb, verb)
        except VocabularyError:
            return policy_rejection(
                "verb",
                "unknown hook verb refused until an owning architecture decision "
                "adds it (FR-Q30; AD-10)",
                given=repr(verb),
            )
        if not self.has_complete_pair(resolved):
            return policy_rejection(
                "verb",
                "daemon primitive lacks a complete before_/after_ pair; "
                "omission requires a spine amendment (FR-Q30; AD-10)",
                given=resolved.value,
            )
        return Ok(resolved)

    def resolve_event(self, event: object) -> Result[str]:
        """Accept only a registered before_/after_ or phase-less control event."""
        if not isinstance(event, str):
            return invalid_input(
                "event",
                "hook event must be a registered HookEvent name (FR-Q30; CT-41)",
                given=repr(event),
            )
        try:
            name = parse_hook_event_name(event)
        except VocabularyError:
            return policy_rejection(
                "event",
                "unknown hook event refused until an owning architecture decision "
                "adds it (FR-Q30; AD-10)",
                given=event,
            )
        if name not in self._by_event:
            return policy_rejection(
                "event",
                "hook event is not in the daemon registry (FR-Q30; AD-10)",
                given=name,
            )
        return Ok(name)

    def resolve_control(self, control: object) -> Result[HookControl]:
        """Accept only ``agent_stop`` or ``review_required``."""
        if not isinstance(control, (str, HookControl)):
            return invalid_input(
                "control",
                "phase-less control must be agent_stop or review_required (FR-Q30)",
                given=repr(control),
            )
        try:
            resolved = (
                control if isinstance(control, HookControl) else parse_closed(HookControl, control)
            )
        except VocabularyError:
            return policy_rejection(
                "control",
                "unknown phase-less control refused; only agent_stop and "
                "review_required are owned (FR-Q30; AD-10)",
                given=repr(control),
            )
        return Ok(resolved)

    def permitted_decisions(self, event: str) -> Result[frozenset[HookResultDecision]]:
        """Inspect the phase-law decision set for a registered event."""
        resolved = self.resolve_event(event)
        if not is_ok(resolved):
            return cast(Result[frozenset[HookResultDecision]], resolved)
        return Ok(legal_decisions_for_event(resolved.value))

    def permitted_fields(self, event: str) -> Result[frozenset[str]]:
        """Inspect the phase-gated fields legal for a registered event."""
        resolved = self.resolve_event(event)
        if not is_ok(resolved):
            return cast(Result[frozenset[str]], resolved)
        return Ok(legal_fields_for_event(resolved.value))

    def register_handler(
        self,
        event: str,
        handler: HookHandler,
        *,
        source: HookSource | str = HookSource.PLUGIN,
        decisions: Iterable[HookResultDecision | str] | None = None,
        fields: Iterable[str] | None = None,
    ) -> Result[Disposer]:
        """Attach a handler; illegal decisions/fields are refused at registration."""
        resolved = self.resolve_event(event)
        if not is_ok(resolved):
            return cast(Result[Disposer], resolved)
        name = resolved.value
        try:
            src = source if isinstance(source, HookSource) else parse_closed(HookSource, source)
        except VocabularyError as exc:
            return invalid_input("source", str(exc), given=repr(source))
        try:
            declared_decisions, declared_fields = validate_registration_phase_law(
                name,
                decisions=decisions,
                fields=fields,
            )
        except VocabularyError as exc:
            return policy_rejection(
                "phase_law",
                str(exc),
                given=name,
            )
        bucket = self._handlers.setdefault(name, [])
        record = _HandlerRecord(
            source=src,
            handler=handler,
            decisions=declared_decisions,
            fields=declared_fields,
        )
        bucket.append(record)

        def dispose() -> None:
            current = self._handlers.get(name)
            if current is None:
                return
            try:
                current.remove(record)
            except ValueError:
                return
            if not current:
                self._handlers.pop(name, None)

        return Ok(dispose)

    def dispatch(
        self,
        event: str,
        *,
        payload: Mapping[str, object] | None = None,
        source: HookSource | str = HookSource.PLUGIN,
        matcher: str | None = None,
    ) -> Result[HookResult]:
        """Fire handlers for one registered event and resolve most-restrictive."""
        resolved = self.resolve_event(event)
        if not is_ok(resolved):
            return cast(Result[HookResult], resolved)
        name = resolved.value
        try:
            hook_event = build_hook_event(
                name,
                source=source,
                payload=payload,
                matcher=matcher,
            )
        except VocabularyError as exc:
            return invalid_input("event", str(exc), given=name)
        handlers = self._handlers.get(name, ())
        if not handlers:
            return Ok(default_empty_hook_result(name))
        collected: list[HookResult] = []
        for record in handlers:
            raw = record.handler(hook_event)
            try:
                validated = assert_hook_result_phase_law(name, raw)
            except VocabularyError as exc:
                return policy_rejection(
                    "phase_law",
                    str(exc),
                    given=name,
                )
            if validated.decision not in record.decisions:
                return policy_rejection(
                    "phase_law",
                    f"handler returned {validated.decision.value!r} outside its "
                    f"registered decision set for {name!r} (FR-Q31; AD-10)",
                    given=validated.decision.value,
                )
            collected.append(validated)
        return Ok(resolve_parallel_hook_results(collected))

    def evaluate_primitive(
        self,
        verb: HookVerb | str,
        *,
        act: Callable[[], T],
        payload: Mapping[str, object] | None = None,
        source: HookSource | str = HookSource.PLUGIN,
        agent_write: bool = False,
    ) -> Result[PrimitiveInvocation]:
        """Evaluate ``before_<verb>``, run ``act``, then emit ``after_<verb>``.

        Unknown verbs and incomplete pairs are refused. A blocking ``before_*``
        decision refuses the act without running it.
        """
        resolved = self.resolve_verb(verb)
        if not is_ok(resolved):
            return cast(Result[PrimitiveInvocation], resolved)
        owned = resolved.value
        before, after = event_names_for_verb(owned)
        if agent_write and owned not in AGENT_REACHABLE_WRITE_VERBS:
            return policy_rejection(
                "verb",
                "verb is not an agent-reachable write primitive (FR-Q30; AD-10)",
                given=owned.value,
            )
        before_result = self.dispatch(before, payload=payload, source=source)
        if not is_ok(before_result):
            return cast(Result[PrimitiveInvocation], before_result)
        gate = before_result.value
        if gate.decision in _BLOCKING_BEFORE_DECISIONS:
            return policy_rejection(
                before,
                f"before_{owned.value} resolved to {gate.decision.value}; "
                "act not executed (FR-Q30; AD-10)",
                given=gate.reason or gate.decision.value,
            )
        value = act()
        after_payload: dict[str, object] = dict(payload or {})
        after_payload["effect"] = value
        after_result = self.dispatch(after, payload=after_payload, source=source)
        if not is_ok(after_result):
            return cast(Result[PrimitiveInvocation], after_result)
        return Ok(
            PrimitiveInvocation(
                verb=owned,
                before_event=before,
                after_event=after,
                before_result=gate,
                after_result=after_result.value,
                value=value,
                agent_write=agent_write,
            )
        )

    def agent_reachable_write(
        self,
        verb: HookVerb | str,
        *,
        act: Callable[[], T],
        payload: Mapping[str, object] | None = None,
        source: HookSource | str = HookSource.MISSION,
    ) -> Result[PrimitiveInvocation]:
        """Sole path for an agent-reachable daemon-store write (FR-Q30).

        Always evaluates ``before_*`` then ``after_*``. No bypass, optional
        enforcement mode, or secondary control surface exists.
        """
        assert_no_bypass_write_path()
        return self.evaluate_primitive(
            verb,
            act=act,
            payload=payload,
            source=source,
            agent_write=True,
        )

    def evaluate_control(
        self,
        control: HookControl | str,
        *,
        payload: Mapping[str, object] | None = None,
        source: HookSource | str = HookSource.PLUGIN,
    ) -> Result[HookResult]:
        """Fire a phase-less blocking control before the act it gates."""
        resolved = self.resolve_control(control)
        if not is_ok(resolved):
            return cast(Result[HookResult], resolved)
        return self.dispatch(resolved.value.value, payload=payload, source=source)

    def require_pair_or_refuse(self, verb: object) -> Result[tuple[str, str]]:
        """Refuse a proposed primitive that omits before_ or after_ (FR-Q30)."""
        resolved = self.resolve_verb(verb)
        if not is_ok(resolved):
            return cast(Result[tuple[str, str]], resolved)
        return Ok(event_names_for_verb(resolved.value))
