"""Template-governed Agent-authored Mission hooks (FR-Q35; CT-41; AD-11).

An Agent may author a hook only from an approved, schema-validated template,
only under Mission source, and only as observe-or-deny. Registration passes
``before_hook_register``, journals a ``correlation_id``, folds under the Mission
into definition-store ``hook_registrations``, and pushes the disposer onto the
Mission exit stack. No durable hook except through AD-22; no privilege
escalation.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, cast
from uuid import uuid4

from qma.core.plugins.context import Disposer, HookHandler
from qma.core.plugins.hooks import (
    HookEvent,
    HookImplementationKind,
    HookResult,
    HookSource,
    assert_hook_result_phase_law,
    build_hook_result,
    parse_hook_implementation_kind,
)
from qma.core.vocabulary.enums import HookResultDecision, HookVerb
from qma.core.vocabulary.hooks import HOOK_RESULT_FIELDS, parse_hook_event_name
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qma.daemon.hooks.registry import HookRegistry, PrimitiveInvocation
from qma.daemon.hooks.source_bounds import HookSourceBinding, assert_matcher_within_source
from qma.daemon.staging.proposal import (
    AGENT_DIRECT_DEFINITION_EXCEPTION,
    register_mission_scoped_hook_exception,
)
from qma.wire.vocabulary import WireQuery
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "AGENT_AUTHORED_ALLOWED_DECISIONS",
    "AGENT_AUTHORED_FORBIDDEN_RESULT_FIELDS",
    "AGENT_AUTHORED_WIRE_QUERY",
    "HOOK_DISPOSED_JOURNAL_EVENT",
    "HOOK_REGISTERED_JOURNAL_EVENT",
    "HOOK_REGISTRATIONS_FOLD",
    "AgentAuthoredHookRegistrar",
    "ApprovedHookTemplate",
    "MissionExitStack",
    "MissionHookRegistration",
    "assert_agent_authored_hook_result",
    "intersect_permissions_exact",
    "validate_agent_authored_template",
]


# Closed reject list — the five non-decision/reason HookResult fields (DEC-0310).
AGENT_AUTHORED_FORBIDDEN_RESULT_FIELDS: Final[frozenset[str]] = HOOK_RESULT_FIELDS

AGENT_AUTHORED_ALLOWED_DECISIONS: Final[frozenset[HookResultDecision]] = frozenset(
    {
        HookResultDecision.OBSERVE,
        HookResultDecision.DENY,
    }
)

AGENT_AUTHORED_WIRE_QUERY: Final[str] = WireQuery.LIST_MISSION_HOOKS.value
HOOK_REGISTERED_JOURNAL_EVENT: Final[str] = "hook.registered"
HOOK_DISPOSED_JOURNAL_EVENT: Final[str] = "hook.disposed"
HOOK_REGISTRATIONS_FOLD: Final[str] = "hook_registrations"

_ESCALATION_PERMISSIONS: Final[frozenset[str]] = frozenset(
    {
        "register_hook",
        "register_hooks",
        "register_tool",
        "register_tools",
        "register_plugin",
        "register_plugins",
        "register_contribution",
        "register_contributions",
        "escalate_privilege",
    }
)


@dataclass(frozen=True, slots=True)
class ApprovedHookTemplate:
    """Operator/daemon-approved template an Agent may instantiate (FR-Q35; AD-11)."""

    template_id: str
    event: str
    decisions: frozenset[HookResultDecision]
    permissions: frozenset[str] = frozenset()
    matcher: str | None = None
    implementation: HookImplementationKind = HookImplementationKind.CALLABLE
    schema_version: str = "1"

    def __post_init__(self) -> None:
        if self.template_id.strip() == "":
            msg = "approved hook template_id must be non-empty (FR-Q35; AD-11)"
            raise VocabularyError(msg)
        name = parse_hook_event_name(self.event)
        object.__setattr__(self, "event", name)
        if not self.decisions:
            msg = "approved hook template must declare at least one decision (FR-Q35)"
            raise VocabularyError(msg)
        illegal = self.decisions - AGENT_AUTHORED_ALLOWED_DECISIONS
        if illegal:
            msg = (
                "approved hook template decisions must be observe-or-deny only; "
                f"refused {sorted(d.value for d in illegal)!r} (FR-Q35; AD-11)"
            )
            raise VocabularyError(msg)
        if self.implementation not in (
            HookImplementationKind.CALLABLE,
            HookImplementationKind.SUBPROCESS,
        ):
            msg = "approved hook template implementation must be deterministic (FR-Q35)"
            raise VocabularyError(msg)

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "template_id": self.template_id,
                "event": self.event,
                "decisions": tuple(sorted(d.value for d in self.decisions)),
                "permissions": tuple(sorted(self.permissions)),
                "matcher": self.matcher,
                "implementation": self.implementation.value,
                "schema_version": self.schema_version,
            }
        )


@dataclass(frozen=True, slots=True)
class MissionHookRegistration:
    """Folded definition-store hook registration under a Mission (FR-Q35; AD-11)."""

    registration_id: str
    mission_id: str
    template_id: str
    event: str
    permissions: frozenset[str]
    correlation_id: str
    source: HookSource = HookSource.MISSION
    matcher: str | None = None
    durable: bool = False
    fold: str = HOOK_REGISTRATIONS_FOLD
    journal_event: str = HOOK_REGISTERED_JOURNAL_EVENT

    def __post_init__(self) -> None:
        object.__setattr__(self, "permissions", frozenset(self.permissions))
        if self.source is not HookSource.MISSION:
            msg = "agent-authored hook source must be mission (FR-Q35; AD-11)"
            raise VocabularyError(msg)
        if self.durable:
            msg = (
                "mission-scoped agent-authored hooks are not durable except "
                "through AD-22 (FR-Q35; AD-11)"
            )
            raise VocabularyError(msg)

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "registration_id": self.registration_id,
                "mission_id": self.mission_id,
                "template_id": self.template_id,
                "event": self.event,
                "permissions": tuple(sorted(self.permissions)),
                "correlation_id": self.correlation_id,
                "source": self.source.value,
                "matcher": self.matcher,
                "durable": self.durable,
                "fold": self.fold,
                "journal_event": self.journal_event,
                "observe_or_deny_only": True,
                "wire_query": AGENT_AUTHORED_WIRE_QUERY,
            }
        )


@dataclass
class MissionExitStack:
    """LIFO disposer stack for Mission-scoped resources (FR-Q35; AD-11)."""

    mission_id: str
    _disposers: list[Disposer] = field(default_factory=list[Disposer], init=False)
    closed: bool = field(default=False, init=False)

    def push(self, disposer: Disposer) -> None:
        if self.closed:
            msg = f"Mission exit stack for {self.mission_id!r} is already closed"
            raise RuntimeError(msg)
        self._disposers.append(disposer)

    def unwind(self) -> int:
        """Invoke disposers LIFO; returns how many ran."""
        if self.closed:
            return 0
        self.closed = True
        count = 0
        while self._disposers:
            dispose = self._disposers.pop()
            dispose()
            count += 1
        return count

    @property
    def depth(self) -> int:
        return len(self._disposers)


def validate_agent_authored_template(raw: Mapping[str, object]) -> Result[ApprovedHookTemplate]:
    """Schema-validate an approved template mapping at registration (FR-Q35)."""
    template_id = raw.get("template_id")
    if not isinstance(template_id, str) or template_id.strip() == "":
        return invalid_input(
            "template_id",
            "approved hook template requires non-empty template_id (FR-Q35; AD-11)",
            given=repr(template_id),
        )
    event = raw.get("event")
    if not isinstance(event, str):
        return invalid_input(
            "event",
            "approved hook template requires a HookEvent name (FR-Q35; AD-11)",
            given=repr(event),
        )
    try:
        parse_hook_event_name(event)
    except VocabularyError as exc:
        return invalid_input("event", str(exc), given=event)

    decisions_raw = raw.get("decisions")
    if not isinstance(decisions_raw, Sequence) or isinstance(decisions_raw, (str, bytes)):
        return invalid_input(
            "decisions",
            "approved hook template decisions must be a sequence of observe|deny",
            given=repr(decisions_raw),
        )
    decisions: set[HookResultDecision] = set()
    for item in cast("Sequence[object]", decisions_raw):
        try:
            resolved = parse_closed(HookResultDecision, item)
        except VocabularyError as exc:
            return invalid_input("decisions", str(exc), given=repr(item))
        if resolved not in AGENT_AUTHORED_ALLOWED_DECISIONS:
            return policy_rejection(
                "decisions",
                "agent-authored hook template is observe-or-deny only (FR-Q35; AD-11)",
                given=resolved.value,
            )
        decisions.add(resolved)
    if not decisions:
        return invalid_input(
            "decisions",
            "approved hook template must declare at least one decision (FR-Q35)",
        )

    permissions_raw = raw.get("permissions", ())
    if not isinstance(permissions_raw, Sequence) or isinstance(permissions_raw, (str, bytes)):
        return invalid_input(
            "permissions",
            "template permissions must be a sequence of strings (FR-Q35; AD-11)",
            given=repr(permissions_raw),
        )
    permissions: set[str] = set()
    for item in cast("Sequence[object]", permissions_raw):
        if not isinstance(item, str) or item.strip() == "":
            return invalid_input(
                "permissions",
                "template permission entries must be non-empty strings (FR-Q35)",
                given=repr(item),
            )
        permissions.add(item)

    matcher = raw.get("matcher")
    if matcher is not None and not isinstance(matcher, str):
        return invalid_input(
            "matcher",
            "template matcher must be a string or omitted (FR-Q35)",
            given=repr(matcher),
        )

    implementation_raw = raw.get("implementation", HookImplementationKind.CALLABLE.value)
    try:
        implementation = parse_hook_implementation_kind(implementation_raw)
    except VocabularyError as exc:
        return policy_rejection("implementation", str(exc), given=repr(implementation_raw))

    schema_version = raw.get("schema_version", "1")
    if not isinstance(schema_version, str) or schema_version.strip() == "":
        return invalid_input(
            "schema_version",
            "template schema_version must be a non-empty string (FR-Q35)",
            given=repr(schema_version),
        )

    fields_raw = raw.get("fields", ())
    if fields_raw not in (None, (), []):
        if not isinstance(fields_raw, Sequence) or isinstance(fields_raw, (str, bytes)):
            return invalid_input(
                "fields",
                "template fields must be an empty sequence when present (FR-Q35; AD-11)",
                given=repr(fields_raw),
            )
        declared = {str(item) for item in cast("Sequence[object]", fields_raw)}
        forbidden = declared & AGENT_AUTHORED_FORBIDDEN_RESULT_FIELDS
        if forbidden:
            return policy_rejection(
                "fields",
                "agent-authored HookResult may carry only decision and reason; "
                f"refused fields {sorted(forbidden)!r} (FR-Q35; AD-11)",
                given=sorted(forbidden),
            )
        if declared:
            return policy_rejection(
                "fields",
                "agent-authored HookResult may carry only decision and reason (FR-Q35; AD-11)",
                given=sorted(declared),
            )

    try:
        template = ApprovedHookTemplate(
            template_id=template_id.strip(),
            event=event,
            decisions=frozenset(decisions),
            permissions=frozenset(permissions),
            matcher=matcher,
            implementation=implementation,
            schema_version=schema_version.strip(),
        )
    except VocabularyError as exc:
        return policy_rejection("template", str(exc), given=template_id)
    return Ok(template)


def intersect_permissions_exact(
    requested: Iterable[str],
    mission_permissions: Iterable[str],
) -> Result[frozenset[str]]:
    """Accept exact intersection; refuse any permission the Mission lacks.

    Silent narrowing is forbidden: if the hook names a permission outside the
    Mission set, registration is refused rather than clipped (FR-Q35; AD-11).
    """
    requested_set = frozenset(requested)
    mission_set = frozenset(mission_permissions)
    missing = requested_set - mission_set
    if missing:
        return policy_rejection(
            "permissions",
            "agent-authored hook permissions must be an exact intersection with "
            "the Mission; permissions the Mission lacks are refused, never "
            f"silently narrowed: {sorted(missing)!r} (FR-Q35; AD-11)",
            given=sorted(missing),
        )
    return Ok(requested_set)


def assert_agent_authored_hook_result(result: HookResult) -> Result[HookResult]:
    """Refuse a HookResult that carries any non-decision/reason field (FR-Q35)."""
    present: list[str] = []
    if result.updated_input is not None:
        present.append("updated_input")
    if result.updated_output is not None:
        present.append("updated_output")
    if result.injected_context is not None:
        present.append("injected_context")
    if result.ledger_entry is not None:
        present.append("ledger_entry")
    if result.verifier_ref is not None:
        present.append("verifier_ref")
    if present:
        return policy_rejection(
            "hook_result",
            "agent-authored HookResult may carry only decision and reason; "
            f"refused fields {present!r} (FR-Q35; AD-11)",
            given=present,
        )
    if result.decision not in AGENT_AUTHORED_ALLOWED_DECISIONS:
        return policy_rejection(
            "decision",
            "agent-authored hook is observe-or-deny only (FR-Q35; AD-11)",
            given=result.decision.value,
        )
    return Ok(result)


@dataclass
class AgentAuthoredHookRegistrar:
    """AD-11 registration validator and Mission-scoped hook lifecycle (FR-Q35)."""

    registry: HookRegistry
    _templates: dict[str, ApprovedHookTemplate] = field(
        default_factory=dict[str, ApprovedHookTemplate]
    )
    _missions: dict[str, frozenset[str]] = field(default_factory=dict[str, frozenset[str]])
    _exit_stacks: dict[str, MissionExitStack] = field(
        default_factory=dict[str, MissionExitStack]
    )
    _registrations: dict[str, MissionHookRegistration] = field(
        default_factory=dict[str, MissionHookRegistration]
    )
    _by_mission: dict[str, list[str]] = field(default_factory=dict[str, list[str]])
    _journal: list[Mapping[str, object]] = field(default_factory=list[Mapping[str, object]])
    _fold: dict[str, MissionHookRegistration] = field(
        default_factory=dict[str, MissionHookRegistration]
    )
    _handler_disposers: dict[str, Disposer] = field(default_factory=dict[str, Disposer])

    @property
    def wire_query(self) -> str:
        return AGENT_AUTHORED_WIRE_QUERY

    @property
    def journal_events(self) -> tuple[Mapping[str, object], ...]:
        return tuple(self._journal)

    def approve_template(
        self,
        raw: Mapping[str, object] | ApprovedHookTemplate,
    ) -> Result[ApprovedHookTemplate]:
        """Admit an approved template into the catalog after schema validation."""
        if isinstance(raw, ApprovedHookTemplate):
            template = raw
        else:
            validated = validate_agent_authored_template(raw)
            if is_refusal(validated):
                return validated
            template = validated.value
        self._templates[template.template_id] = template
        return Ok(template)

    def open_mission(
        self,
        mission_id: object,
        *,
        permissions: Iterable[str],
    ) -> Result[MissionExitStack]:
        """Open a Mission scope that may receive agent-authored hooks."""
        if not isinstance(mission_id, str) or mission_id.strip() == "":
            return invalid_input(
                "mission_id",
                "agent-authored hooks register only under an open Mission (FR-Q35; AD-11)",
                given=repr(mission_id),
            )
        mid = mission_id.strip()
        perms: set[str] = set()
        for item in permissions:
            if item.strip() == "":
                return invalid_input(
                    "permissions",
                    "Mission permissions must be non-empty strings (FR-Q35; AD-11)",
                    given=repr(item),
                )
            perms.add(item)
        stack = MissionExitStack(mission_id=mid)
        self._missions[mid] = frozenset(perms)
        self._exit_stacks[mid] = stack
        self._by_mission.setdefault(mid, [])
        return Ok(stack)

    def register(
        self,
        *,
        mission_id: object,
        template_id: object,
        handler: HookHandler,
        permissions: Iterable[str] | None = None,
        source: HookSource | str = HookSource.MISSION,
        correlation_id: object | None = None,
        durable: bool = False,
        registration_id: str | None = None,
        matcher: str | None = None,
        escalate: bool = False,
    ) -> Result[MissionHookRegistration]:
        """Validate and register an Agent-authored Mission hook (FR-Q35; AD-11)."""
        if not isinstance(mission_id, str) or mission_id.strip() == "":
            return invalid_input(
                "mission_id",
                "agent-authored hooks require a Mission id (FR-Q35; AD-11)",
                given=repr(mission_id),
            )
        mid = mission_id.strip()
        if mid not in self._missions or mid not in self._exit_stacks:
            return policy_rejection(
                "mission_id",
                "registration outside an open Mission is refused (FR-Q35; AD-11)",
                given=mid,
            )
        stack = self._exit_stacks[mid]
        if stack.closed:
            return policy_rejection(
                "mission_id",
                "Mission has ended; agent-authored hook registration refused (FR-Q35; AD-11)",
                given=mid,
            )

        if template_id is None or (isinstance(template_id, str) and template_id.strip() == ""):
            return policy_rejection(
                "template_id",
                "untemplated agent-authored hooks are refused (FR-Q35; AD-11)",
                given=repr(template_id),
            )
        if not isinstance(template_id, str):
            return invalid_input(
                "template_id",
                "agent-authored hooks require an approved template id (FR-Q35; AD-11)",
                given=repr(template_id),
            )
        template = self._templates.get(template_id.strip())
        if template is None:
            return policy_rejection(
                "template_id",
                "hook template is not in the approved catalog (FR-Q35; AD-11)",
                given=template_id,
            )

        try:
            src = source if isinstance(source, HookSource) else parse_closed(HookSource, source)
        except VocabularyError as exc:
            return invalid_input("source", str(exc), given=repr(source))
        if src is not HookSource.MISSION:
            return policy_rejection(
                "source",
                "agent-authored hook source above mission is refused "
                f"(got {src.value!r}) (FR-Q35; AD-11)",
                given=src.value,
            )

        if durable:
            return policy_rejection(
                "durable",
                "a mission-scoped hook never becomes durable except through "
                "AD-22 admission (FR-Q35; AD-11)",
            )

        if escalate:
            return policy_rejection(
                "privilege",
                "agent-authored hooks cannot escalate privilege — may not register "
                "hooks, tools, plugins or contributions (FR-Q35; AD-11)",
            )

        exception_gate = register_mission_scoped_hook_exception(
            mission_id=mid,
            template_id=template.template_id,
            observe_or_deny_only=True,
            via_hook=AGENT_DIRECT_DEFINITION_EXCEPTION,
        )
        if is_refusal(exception_gate):
            return exception_gate

        requested = (
            frozenset(permissions)
            if permissions is not None
            else frozenset(template.permissions)
        )
        for perm in requested:
            if perm.strip() == "":
                return invalid_input(
                    "permissions",
                    "hook permissions must be non-empty strings (FR-Q35; AD-11)",
                    given=repr(perm),
                )
            if perm in _ESCALATION_PERMISSIONS:
                return policy_rejection(
                    "privilege",
                    "agent-authored hooks cannot escalate privilege via "
                    f"permission {perm!r} (FR-Q35; AD-11)",
                    given=perm,
                )
        intersection = intersect_permissions_exact(requested, self._missions[mid])
        if is_refusal(intersection):
            return intersection
        accepted_permissions = intersection.value

        effective_matcher = matcher if matcher is not None else template.matcher
        binding = HookSourceBinding(
            source=HookSource.MISSION,
            source_ref=mid,
            matcher=effective_matcher,
        )
        matcher_ok = assert_matcher_within_source(binding, effective_matcher)
        if is_refusal(matcher_ok):
            return matcher_ok

        if correlation_id is None:
            cid = str(uuid4())
        elif isinstance(correlation_id, str) and correlation_id.strip() != "":
            cid = correlation_id.strip()
        else:
            return invalid_input(
                "correlation_id",
                "registration journal entry requires a non-empty correlation_id "
                "(FR-Q35; AD-11)",
                given=repr(correlation_id),
            )

        rid = registration_id or str(uuid4())
        attach_refusal: list[Result[object]] = []

        def _guarded(event: HookEvent) -> HookResult:
            raw_result = handler(event)
            checked = assert_agent_authored_hook_result(raw_result)
            if is_refusal(checked):
                return build_hook_result(
                    HookResultDecision.DENY,
                    reason="agent_authored_illegal_result_fields",
                )
            try:
                return assert_hook_result_phase_law(template.event, checked.value)
            except VocabularyError:
                return build_hook_result(
                    HookResultDecision.DENY,
                    reason="agent_authored_phase_law_violation",
                )

        def _attach() -> MissionHookRegistration | None:
            attached = self.registry.register_handler(
                template.event,
                _guarded,
                source=HookSource.MISSION,
                source_ref=mid,
                matcher=matcher_ok.value,
                implementation=template.implementation,
                decisions=tuple(template.decisions),
                fields=(),
            )
            if is_refusal(attached):
                attach_refusal.append(attached)
                return None
            handler_dispose = attached.value

            registration = MissionHookRegistration(
                registration_id=rid,
                mission_id=mid,
                template_id=template.template_id,
                event=template.event,
                permissions=accepted_permissions,
                correlation_id=cid,
                source=HookSource.MISSION,
                matcher=matcher_ok.value,
                durable=False,
            )

            def dispose() -> None:
                handler_dispose()
                self._registrations.pop(rid, None)
                self._fold.pop(rid, None)
                self._handler_disposers.pop(rid, None)
                mission_list = self._by_mission.get(mid)
                if mission_list is not None and rid in mission_list:
                    mission_list.remove(rid)
                self._journal.append(
                    MappingProxyType(
                        {
                            "event": HOOK_DISPOSED_JOURNAL_EVENT,
                            "correlation_id": cid,
                            "mission_id": mid,
                            "registration_id": rid,
                            "fold": HOOK_REGISTRATIONS_FOLD,
                        }
                    )
                )

            self._handler_disposers[rid] = dispose
            self._registrations[rid] = registration
            self._fold[rid] = registration
            self._by_mission.setdefault(mid, []).append(rid)
            stack.push(dispose)
            self._journal.append(
                MappingProxyType(
                    {
                        "event": HOOK_REGISTERED_JOURNAL_EVENT,
                        "correlation_id": cid,
                        "mission_id": mid,
                        "registration_id": rid,
                        "template_id": template.template_id,
                        "hook_event": template.event,
                        "permissions": tuple(sorted(accepted_permissions)),
                        "fold": HOOK_REGISTRATIONS_FOLD,
                        "via": AGENT_DIRECT_DEFINITION_EXCEPTION,
                    }
                )
            )
            return registration

        gated = self.registry.agent_reachable_write(
            HookVerb.HOOK_REGISTER,
            act=_attach,
            payload={
                "mission_id": mid,
                "template_id": template.template_id,
                "correlation_id": cid,
                "registration_id": rid,
            },
            source=HookSource.MISSION,
        )
        if is_refusal(gated):
            return gated
        if attach_refusal:
            return attach_refusal[0]  # type: ignore[return-value]
        invocation: PrimitiveInvocation = gated.value
        value = invocation.value
        if isinstance(value, MissionHookRegistration):
            return Ok(value)
        return policy_rejection(
            "hook_register",
            "before_hook_register act did not produce a MissionHookRegistration",
            given=repr(type(value)),
        )

    def list_mission_hooks(self, mission_id: object) -> Result[Mapping[str, object]]:
        """Named ``qma-wire`` query ``list_mission_hooks`` (FR-Q35; AD-11)."""
        if not isinstance(mission_id, str) or mission_id.strip() == "":
            return invalid_input(
                "mission_id",
                f"{AGENT_AUTHORED_WIRE_QUERY} requires a Mission id",
                given=repr(mission_id),
            )
        mid = mission_id.strip()
        records = [
            dict(self._registrations[rid].to_payload())
            for rid in self._by_mission.get(mid, ())
            if rid in self._registrations
        ]
        return Ok(
            MappingProxyType(
                {
                    "query": AGENT_AUTHORED_WIRE_QUERY,
                    "mission_id": mid,
                    "fold": HOOK_REGISTRATIONS_FOLD,
                    "hooks": records,
                    "count": len(records),
                }
            )
        )

    def answer_wire_query(
        self,
        query: object,
        *,
        args: Mapping[str, object] | None = None,
    ) -> Result[Mapping[str, object]]:
        """Dispatch the named wire query exposing Mission hook registrations."""
        if query not in {AGENT_AUTHORED_WIRE_QUERY, WireQuery.LIST_MISSION_HOOKS}:
            return policy_rejection(
                "query",
                f"agent-authored hook surface exposes only {AGENT_AUTHORED_WIRE_QUERY!r}",
                given=repr(query),
            )
        payload = dict(args or {})
        return self.list_mission_hooks(payload.get("mission_id"))

    def end_mission(self, mission_id: object) -> Result[Mapping[str, object]]:
        """Unwind the Mission exit stack and remove all agent-authored hooks."""
        if not isinstance(mission_id, str) or mission_id.strip() == "":
            return invalid_input(
                "mission_id",
                "Mission end requires a Mission id (FR-Q35; AD-11)",
                given=repr(mission_id),
            )
        mid = mission_id.strip()
        stack = self._exit_stacks.get(mid)
        if stack is None:
            return policy_rejection(
                "mission_id",
                "no open Mission exit stack to unwind (FR-Q35; AD-11)",
                given=mid,
            )
        removed_ids = list(self._by_mission.get(mid, ()))
        unwound = stack.unwind()
        self._missions.pop(mid, None)
        self._exit_stacks.pop(mid, None)
        self._by_mission.pop(mid, None)
        remaining = self.list_mission_hooks(mid)
        remaining_count = remaining.value["count"] if is_ok(remaining) else 0
        return Ok(
            MappingProxyType(
                {
                    "mission_id": mid,
                    "removed_registration_ids": tuple(removed_ids),
                    "disposers_run": unwound,
                    "hooks_remaining": remaining_count,
                }
            )
        )

    def folded_under_mission(self, mission_id: str) -> tuple[MissionHookRegistration, ...]:
        """Inspect definition-store fold rows for one Mission."""
        return tuple(
            self._fold[rid]
            for rid in self._by_mission.get(mission_id, ())
            if rid in self._fold
        )
