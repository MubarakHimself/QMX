"""Unified Tool Registry (AD-16; FR-Q41, FR-Q42; AR-Q18).

Native, CLI, plugin, MCP-adapter, browser, computer-use and backtest tools
enter one registry. Availability ``check_fn`` excludes an unrunnable tool
before its schema reaches a model. MCP desk-and-role bindings are operator-only.
Lowest capable capability-ladder rung wins. Trading desk stays read-and-calculate:
the code-declared act-level money-path deny-list refuses matching tools at
registration, before ``check_fn``, including paper-only tools. An MCP adapter
that advertises one denied tool is refused whole. Role, Mission, hook, toolset,
tool_adapter, and check_fn cannot lift the denial.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any, cast

from qma.core.barriers.capability import (
    CAPABILITY_LADDER,
    assert_ladder_is_code_declared,
    parse_capability_rung,
)
from qma.core.barriers.money_path import (
    QMA_MINTED_PROMOTION_COMMAND,
    is_money_path_act_denied,
    match_money_path_act,
    refuse_money_path_permission,
    refuse_money_path_registration,
)
from qma.core.barriers.parent_surfaces import (
    ProhibitedMutation,
    ProhibitedRecordFamily,
)
from qma.core.control.primitives import Skill
from qma.core.ports.tools import (
    TOOL_ADAPTER_WRITE_COMMAND,
    TOOL_KINDS,
    AvailabilityCheck,
    ToolAdapterBinding,
    ToolAdapterRecord,
    ToolKind,
    ToolRecord,
    ToolsetRecord,
    default_rung_for_kind,
    narrow_toolset_ids,
    parse_tool_kind,
    select_lowest_capable,
    skill_grants_tool_or_capability,
    subagent_inherited_tool_ids,
    write_tool_adapter_binding,
)
from qma.core.refusals.variants import ProhibitedMoneyPathTool
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, PrincipalClass
from qma.core.vocabulary.registry import VocabularyError
from qma.daemon.envs.registry import ExecutionEnvironmentRegistry
from qma.daemon.tools.parent_writes import DEV_ZONE, DevZoneCandidate, ParentSurfaceGate
from qmf.core import Ok, Result, is_ok
from qmf.data.store.refusals import invalid_input

__all__ = [
    "GAP_0070_DESKTOP_EXCLUSION",
    "ToolRegistry",
]

# Deferred GAP-0070: no Windows VPS / desktop environment is provisioned here.
GAP_0070_DESKTOP_EXCLUSION: Mapping[str, str] = MappingProxyType(
    {
        "gap": "GAP-0070",
        "status": "deferred",
        "effect": (
            "computer-use tools fail check_fn until a desktop ExecutionEnvironment "
            "is registered; this story does not provision one"
        ),
    }
)


def _always_available() -> bool:
    return True


def _declared_acts(record: ToolRecord) -> tuple[str, ...]:
    """Acts the deny-list inspects: ``money_path_act`` plus declared ``acts``."""
    acts: list[str] = []
    if record.money_path_act is not None:
        acts.append(record.money_path_act)
    acts.extend(record.acts)
    return tuple(acts)


def _metadata_advertised_rows(
    record: ToolAdapterRecord,
) -> tuple[tuple[str, str], ...]:
    """``(tool_id, act)`` pairs declared on adapter metadata / advertised_acts."""
    rows: list[tuple[str, str]] = []
    for act in record.advertised_acts:
        rows.append((record.adapter_id, act))
    raw = record.metadata.get("advertised_tools")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return tuple(rows)
    for item in cast(Sequence[object], raw):
        if not isinstance(item, Mapping):
            continue
        mapping = cast(Mapping[str, object], item)
        tool_raw = mapping.get("tool_id", mapping.get("id", record.adapter_id))
        tool_id = str(tool_raw)
        money = mapping.get("money_path_act")
        if isinstance(money, str) and money:
            rows.append((tool_id, money))
        acts_raw = mapping.get("acts", ())
        if isinstance(acts_raw, str):
            rows.append((tool_id, acts_raw))
            continue
        if isinstance(acts_raw, Sequence) and not isinstance(acts_raw, (str, bytes)):
            for act_item in cast(Sequence[object], acts_raw):
                rows.append((tool_id, str(act_item)))
    return tuple(rows)


class ToolRegistry:
    """One governed Tool Registry for every tool kind (AD-16; FR-Q41)."""

    def __init__(
        self,
        *,
        environments: ExecutionEnvironmentRegistry | None = None,
    ) -> None:
        assert_ladder_is_code_declared()
        self._tools: dict[str, ToolRecord] = {}
        self._adapters: dict[str, ToolAdapterRecord] = {}
        self._bindings: dict[str, ToolAdapterBinding] = {}
        self._toolsets: dict[str, ToolsetRecord] = {}
        self._environments = (
            environments if environments is not None else ExecutionEnvironmentRegistry()
        )
        self._parent_writes = ParentSurfaceGate()

    @property
    def environments(self) -> ExecutionEnvironmentRegistry:
        return self._environments

    @property
    def supported_kinds(self) -> tuple[ToolKind, ...]:
        return TOOL_KINDS

    @property
    def capability_ladder(self) -> tuple[str, ...]:
        return tuple(rung.value for rung in CAPABILITY_LADDER)

    def bind_environments(self, environments: ExecutionEnvironmentRegistry) -> None:
        """Attach the daemon's ExecutionEnvironment registry (desktop preflight)."""
        self._environments = environments

    def _desktop_registered(self) -> bool:
        return ExecutionEnvironmentKind.DESKTOP.value in self._environments.kinds()

    def _computer_use_check_fn(
        self,
        user_check: AvailabilityCheck | None,
    ) -> AvailabilityCheck:
        """Computer-use fails until a desktop environment is registered (GAP-0070)."""

        def check() -> bool:
            if not self._desktop_registered():
                return False
            if user_check is None:
                return True
            return bool(user_check())

        return check

    def _money_path_refusal_for(self, record: ToolRecord) -> ProhibitedMoneyPathTool | None:
        """Evaluate the deny-list before ``check_fn`` (FR-Q42; AD-16).

        Paper-only tags and account-role prefixes cannot lift a match.
        """
        for act in _declared_acts(record):
            if is_money_path_act_denied(act):
                return refuse_money_path_registration(
                    tool_id=record.tool_id,
                    act=act,
                    plugin_id=record.plugin_id,
                )
        return None

    def _adapter_money_path_refusal(
        self,
        record: ToolAdapterRecord,
        *,
        extra_tools: Sequence[ToolRecord] = (),
    ) -> ProhibitedMoneyPathTool | None:
        """Refuse the whole MCP server when any advertised tool matches."""
        extras = {tool.tool_id: tool for tool in extra_tools}
        for tool_id, act in _metadata_advertised_rows(record):
            if is_money_path_act_denied(act):
                return refuse_money_path_registration(
                    tool_id=tool_id,
                    act=act,
                    plugin_id=record.plugin_id,
                )
        for tool_id in record.advertised_tool_ids:
            tool = extras.get(tool_id, self._tools.get(tool_id))
            if tool is None:
                continue
            refused = self._money_path_refusal_for(tool)
            if refused is not None:
                return refused
        for tool in extra_tools:
            refused = self._money_path_refusal_for(tool)
            if refused is not None:
                return refused
        return None

    def register_tool(
        self,
        record: ToolRecord,
        *,
        check_fn: AvailabilityCheck | None = None,
    ) -> Result[str]:
        """Register any tool kind into the one registry (no kind-specific bypass)."""
        try:
            kind = parse_tool_kind(record.kind)
        except VocabularyError as exc:
            return invalid_input("kind", str(exc), given=repr(record.kind))

        if record.tool_id in self._tools:
            return invalid_input(
                "tool_id",
                "tool id already registered (AD-16; FR-Q41)",
                given=record.tool_id,
            )

        # FR-Q42 / AD-16: act-level deny-list before check_fn, every kind, paper included.
        denied = self._money_path_refusal_for(record)
        if denied is not None:
            return denied

        resolved_check = check_fn if check_fn is not None else record.check_fn
        if kind is ToolKind.COMPUTER_USE:
            resolved_check = self._computer_use_check_fn(resolved_check)
        elif resolved_check is None:
            resolved_check = _always_available

        stored = ToolRecord(
            tool_id=record.tool_id,
            kind=kind,
            capability_rung=record.capability_rung,
            schema=dict(record.schema),
            check_fn=resolved_check,
            acts=record.acts,
            tags=record.tags,
            plugin_id=record.plugin_id,
            requires_environment_kind=record.requires_environment_kind,
            money_path_act=record.money_path_act,
        )
        self._tools[stored.tool_id] = stored
        return Ok(stored.tool_id)

    def register(
        self,
        *,
        tool_id: str,
        kind: ToolKind | str,
        schema: Mapping[str, object] | None = None,
        capability_rung: str | None = None,
        acts: Sequence[str] = (),
        tags: Sequence[str] = (),
        check_fn: AvailabilityCheck | None = None,
        money_path_act: str | None = None,
        plugin_id: str | None = None,
    ) -> Result[str]:
        """Convenience registration for any of the seven closed kinds."""
        try:
            resolved_kind = parse_tool_kind(kind)
        except VocabularyError as exc:
            return invalid_input("kind", str(exc), given=repr(kind))
        rung = (
            parse_capability_rung(capability_rung)
            if capability_rung is not None
            else default_rung_for_kind(resolved_kind)
        )
        record = ToolRecord(
            tool_id=tool_id,
            kind=resolved_kind,
            capability_rung=rung,
            schema=dict(schema or {}),
            acts=frozenset(acts),
            tags=frozenset(tags),
            check_fn=None,
            money_path_act=money_path_act,
            plugin_id=plugin_id,
        )
        return self.register_tool(record, check_fn=check_fn)

    def get(self, tool_id: str) -> ToolRecord | None:
        return self._tools.get(tool_id)

    def catalog(self) -> tuple[ToolRecord, ...]:
        return tuple(self._tools.values())

    def is_available(self, tool_id: str) -> bool:
        tool = self._tools.get(tool_id)
        if tool is None:
            return False
        return tool.is_available()

    def model_visible_schemas(
        self,
        allowed_tool_ids: Sequence[str] | frozenset[str] | set[str] | None = None,
    ) -> tuple[Mapping[str, object], ...]:
        """Schemas that pass ``check_fn`` — unrunnable tools never reach the model."""
        allowed = None if allowed_tool_ids is None else frozenset(allowed_tool_ids)
        visible: list[Mapping[str, object]] = []
        for tool in self._tools.values():
            if allowed is not None and tool.tool_id not in allowed:
                continue
            if not tool.is_available():
                continue
            payload = MappingProxyType(
                {
                    "tool_id": tool.tool_id,
                    "kind": tool.kind.value,
                    "capability_rung": tool.capability_rung.value,
                    "schema": dict(tool.schema),
                    "acts": sorted(tool.acts),
                }
            )
            visible.append(payload)
        return tuple(visible)

    def register_adapter(self, record: ToolAdapterRecord) -> Result[str]:
        """Register an MCP/adapter contribution without desk-and-role binding.

        One advertised money-path tool refuses the whole server (FR-Q42; AD-16).
        """
        if record.adapter_id in self._adapters:
            return invalid_input(
                "adapter_id",
                "tool_adapter already registered (AD-16; FR-Q41)",
                given=record.adapter_id,
            )
        for forbidden in ("desk", "role", "desk_and_role", "binding"):
            if forbidden in record.metadata:
                return invalid_input(
                    forbidden,
                    (
                        "plugin tool_adapter may not declare desk-and-role binding; "
                        f"only {TOOL_ADAPTER_WRITE_COMMAND} may write it (AD-16)"
                    ),
                    given=repr(record.metadata.get(forbidden)),
                )
        denied = self._adapter_money_path_refusal(record)
        if denied is not None:
            return denied
        self._adapters[record.adapter_id] = record
        return Ok(record.adapter_id)

    def register_mcp_server(
        self,
        adapter: ToolAdapterRecord,
        tools: Sequence[ToolRecord],
        *,
        check_fns: Mapping[str, AvailabilityCheck] | None = None,
    ) -> Result[str]:
        """Register an MCP server as one adapter plus its advertised tools.

        Any matching advertised tool refuses the whole server — nothing binds.
        """
        denied = self._adapter_money_path_refusal(adapter, extra_tools=tools)
        if denied is not None:
            return denied
        previous_tools = set(self._tools)
        previous_adapters = set(self._adapters)
        adapter_out = self.register_adapter(adapter)
        if not is_ok(adapter_out):
            return adapter_out
        for tool in tools:
            check = None if check_fns is None else check_fns.get(tool.tool_id)
            registered = self.register_tool(tool, check_fn=check)
            if not is_ok(registered):
                for tool_id in tuple(self._tools):
                    if tool_id not in previous_tools:
                        del self._tools[tool_id]
                for adapter_id in tuple(self._adapters):
                    if adapter_id not in previous_adapters:
                        del self._adapters[adapter_id]
                return registered
        return Ok(adapter.adapter_id)

    def write_adapter_binding(
        self,
        adapter_id: str,
        *,
        desk: str,
        role: str,
        principal: PrincipalClass | str,
    ) -> Result[ToolAdapterBinding]:
        """Operator-principal desk-and-role binding for a registered adapter."""
        adapter = self._adapters.get(adapter_id)
        if adapter is None:
            return invalid_input(
                "adapter_id",
                "unknown tool_adapter for tool_adapter.write",
                given=adapter_id,
                command=TOOL_ADAPTER_WRITE_COMMAND,
            )
        outcome = write_tool_adapter_binding(
            adapter,
            desk=desk,
            role=role,
            principal=principal,
        )
        if not isinstance(outcome, Ok):
            return outcome
        binding = outcome.value
        self._bindings[binding.binding_key] = binding
        return Ok(binding)

    def get_adapter(self, adapter_id: str) -> ToolAdapterRecord | None:
        return self._adapters.get(adapter_id)

    def get_binding(self, adapter_id: str, desk: str, role: str) -> ToolAdapterBinding | None:
        key = f"{adapter_id}@{desk}/{role}"
        return self._bindings.get(key)

    def register_toolset(self, record: ToolsetRecord) -> Result[str]:
        """Register a versioned definition-store toolset of FQ tool ids."""
        if record.toolset_id in self._toolsets:
            return invalid_input(
                "toolset_id",
                "toolset already registered (AD-16; FR-Q41)",
                given=record.toolset_id,
            )
        self._toolsets[record.toolset_id] = record
        return Ok(record.toolset_id)

    def get_toolset(self, toolset_id: str) -> ToolsetRecord | None:
        return self._toolsets.get(toolset_id)

    def resolve_effective_tool_ids(
        self,
        *,
        role_toolset_id: str,
        mission_tool_ids: Sequence[str] | frozenset[str] | set[str] | None = None,
        parent_tool_ids: Sequence[str] | frozenset[str] | set[str] | None = None,
        is_subagent: bool = False,
        appended_skills: Sequence[Skill] = (),
    ) -> Result[frozenset[str]]:
        """Role grants a toolset; Mission narrows; Subagent inherits ≤ parent.

        Appended Skills supply knowledge only and never grant a tool.
        """
        toolset = self._toolsets.get(role_toolset_id)
        if toolset is None:
            return invalid_input(
                "role_toolset_id",
                "Role toolset must be a registered definition-store record",
                given=role_toolset_id,
            )
        if appended_skills and skill_grants_tool_or_capability():
            return invalid_input(
                "skill",
                "Skill must not grant a tool or capability (AD-16; FR-Q41)",
            )
        for skill in appended_skills:
            if skill.to_payload().get("grants_capability"):
                return invalid_input(
                    "skill",
                    "appended Skill supplies knowledge only (AD-16; FR-Q41)",
                    given=skill.qualified_id,
                )

        narrowed = narrow_toolset_ids(toolset.tool_ids, mission_tool_ids)
        if not isinstance(narrowed, Ok):
            return narrowed
        effective = narrowed.value

        if parent_tool_ids is not None:
            parent = frozenset(parent_tool_ids)
            extras = effective - parent
            if extras:
                return invalid_input(
                    "parent_tool_ids",
                    "child may not hold tools outside its parent grant (AD-16)",
                    extras=sorted(extras),
                )
            effective = effective & parent

        if is_subagent:
            tags_by_id = {
                tool_id: tuple(self._tools[tool_id].tags)
                for tool_id in effective
                if tool_id in self._tools
            }
            effective = subagent_inherited_tool_ids(effective, tool_tags=tags_by_id)

        return Ok(effective)

    def resolve_permission(
        self,
        act: str,
        *,
        tool_id: str = "registry:permission",
        plugin_id: str | None = None,
        via: str | None = None,
        check_fn: AvailabilityCheck | None = None,
    ) -> Result[bool]:
        """Resolve availability/permission; a deny-list match cannot be lifted.

        Role, Mission, hook, toolset, tool_adapter, and ``check_fn`` are ignored
        when the act is denied — the refusal is raised here, never deferred to a
        runtime hook (FR-Q42; AD-16).
        """
        if is_money_path_act_denied(act):
            return refuse_money_path_permission(
                tool_id=tool_id,
                act=act,
                plugin_id=plugin_id,
                via=via,
            )
        if check_fn is not None:
            return Ok(bool(check_fn()))
        return Ok(True)

    def attempt_money_path_write(
        self,
        family: ProhibitedRecordFamily | str,
        mutation: ProhibitedMutation | str = ProhibitedMutation.WRITE,
    ) -> Result[DevZoneCandidate]:
        """Refuse a money-path write through the permitted dependency surface."""
        return self._parent_writes.attempt_write(family=family, mutation=mutation)

    def attempt_zone_transition(self) -> Result[DevZoneCandidate]:
        """Refuse every zone-transition surface."""
        return self._parent_writes.attempt_zone_transition()

    def write_dev_zone_candidate(
        self,
        payload: Mapping[str, object],
        *,
        origin: str = "qma",
        summary: str | None = None,
        lineage_predecessor: str | None = None,
        zone: str = DEV_ZONE,
    ) -> Result[DevZoneCandidate]:
        """Sole permitted write: a content-addressed candidate in the ``dev`` zone."""
        return self._parent_writes.write_dev_zone_candidate(
            payload,
            origin=origin,
            summary=summary,
            lineage_predecessor=lineage_predecessor,
            zone=zone,
        )

    @property
    def minted_promotion_command(self) -> None:
        """This registry mints no promotion command (FR-Q42)."""
        return QMA_MINTED_PROMOTION_COMMAND

    def select_for_act(
        self,
        act: str,
        *,
        allowed_tool_ids: Sequence[str] | frozenset[str] | set[str] | None = None,
    ) -> Result[ToolRecord]:
        """Pick the lowest capable available tool that declares ``act``."""
        if is_money_path_act_denied(act):
            matched = match_money_path_act(act)
            return refuse_money_path_registration(
                tool_id="registry:select_for_act",
                act=matched if matched is not None else act,
            )
        allowed = None if allowed_tool_ids is None else frozenset(allowed_tool_ids)
        candidates: list[ToolRecord] = []
        for tool in self._tools.values():
            if allowed is not None and tool.tool_id not in allowed:
                continue
            if act not in tool.acts:
                continue
            if not tool.is_available():
                continue
            candidates.append(tool)
        selected = select_lowest_capable(candidates)
        if selected is None:
            return invalid_input(
                "act",
                "no available tool satisfies the allowed act under the capability ladder",
                given=act,
            )
        return Ok(selected)

    def snapshot(self) -> Mapping[str, Any]:
        return MappingProxyType(
            {
                "tool_count": len(self._tools),
                "adapter_count": len(self._adapters),
                "binding_count": len(self._bindings),
                "toolset_count": len(self._toolsets),
                "kinds": sorted({tool.kind.value for tool in self._tools.values()}),
                "ladder": list(self.capability_ladder),
                "gap_0070": dict(GAP_0070_DESKTOP_EXCLUSION),
                "desktop_registered": self._desktop_registered(),
                "minted_promotion_command": self.minted_promotion_command,
                "permitted_parent_write": list(self._parent_writes.permitted_write),
            }
        )
