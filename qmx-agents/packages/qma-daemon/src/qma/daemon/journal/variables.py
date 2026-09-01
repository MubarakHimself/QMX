"""AD-26 governed configurable-variable registry (FR-Q36; DEC-0325).

Every number any QMA subsystem mints is a registry row declaring name, owning
subsystem, scope, type, units, default, editability, and home. Registry-homed
values change only via an ``operator``-principal ``variable.set`` that records a
``variable.set`` journal event. Uneditable and record-homed values are refused.
There is no ``variable`` edit kind — agents, hooks, Roles and Missions never set
one. Store-lifecycle cadences are cited by ``registry:`` key and never copied.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

from qma.core.refusals import OperatorPrincipalRequired
from qma.core.vocabulary import (
    PrincipalClass,
    RefinementEditKind,
    VariableEditability,
    VariableScope,
    VocabularyError,
    parse_closed,
)
from qma.daemon.journal.authoritative import AuthoritativeJournal, JournalAppendReceipt
from qma.wire.principals import authorize_wire_command
from qmf.core import Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "REGISTRY_HOME",
    "STORE_BACKUP_CADENCE_KEY",
    "STORE_FULL_RESTORE_REHEARSAL_CADENCE_KEY",
    "STORE_LIFECYCLE_KEYS",
    "STORE_SAMPLE_RESTORE_TEST_CADENCE_KEY",
    "VARIABLE_SET_COMMAND",
    "VARIABLE_SET_EVENT",
    "GovernedVariableRegistry",
    "VariableRow",
    "VariableSetReceipt",
    "builtin_qma_variable_rows",
    "cite_store_lifecycle_key",
    "has_variable_edit_kind",
    "registry_key",
]


VARIABLE_SET_COMMAND: Final[str] = "variable.set"
VARIABLE_SET_EVENT: Final[str] = "variable.set"
REGISTRY_HOME: Final[str] = "registry"

# Cite by key — never copy a registry value into code (FR-Q36; AD-26).
STORE_BACKUP_CADENCE_KEY: Final[str] = "registry:store.backup_cadence"
STORE_SAMPLE_RESTORE_TEST_CADENCE_KEY: Final[str] = "registry:store.sample_restore_test_cadence"
STORE_FULL_RESTORE_REHEARSAL_CADENCE_KEY: Final[str] = (
    "registry:store.full_restore_rehearsal_cadence"
)
STORE_LIFECYCLE_KEYS: Final[frozenset[str]] = frozenset(
    {
        STORE_BACKUP_CADENCE_KEY,
        STORE_SAMPLE_RESTORE_TEST_CADENCE_KEY,
        STORE_FULL_RESTORE_REHEARSAL_CADENCE_KEY,
    }
)


def registry_key(name: str) -> str:
    """Return the ``registry:<name>`` citation form."""
    if name.startswith("registry:"):
        return name
    return f"registry:{name}"


def cite_store_lifecycle_key(name: object) -> Result[str]:
    """Resolve a store-lifecycle citation to its ``registry:`` key.

    Refuses unknown names and never returns a copied cadence value.
    """
    if not isinstance(name, str) or name.strip() == "":
        return invalid_input(
            "store_lifecycle_key",
            "cite registry:store.backup_cadence, "
            "registry:store.sample_restore_test_cadence, or "
            "registry:store.full_restore_rehearsal_cadence by key (FR-Q36; AD-26)",
            given=repr(name),
        )
    key = registry_key(name.removeprefix("registry:"))
    if key not in STORE_LIFECYCLE_KEYS:
        return policy_rejection(
            "store_lifecycle_key",
            "store-lifecycle citations name one of the three AD-26 cadence keys "
            "and never copy a registry value (FR-Q36; AD-26)",
            given=name,
            allowed=sorted(STORE_LIFECYCLE_KEYS),
        )
    return Ok(key)


def has_variable_edit_kind() -> bool:
    """False — AD-22 mints no ``variable`` edit kind (FR-Q36; AD-26)."""
    return any(kind.value == "variable" for kind in RefinementEditKind)


@dataclass(frozen=True, slots=True)
class VariableRow:
    """One machine-readable AD-26 registry row."""

    name: str
    owning_subsystem: str
    scope: VariableScope
    value_type: str
    units: str | None
    default: object
    editability: VariableEditability
    home: str

    @property
    def registry_key(self) -> str:
        """``registry:<name>`` citation form."""
        return registry_key(self.name)

    @property
    def is_registry_homed(self) -> bool:
        """True when ``home`` is the registry itself."""
        return self.home == REGISTRY_HOME

    @property
    def is_record_homed(self) -> bool:
        """True when ``home`` is a named owning record type."""
        return not self.is_registry_homed

    def to_dict(self) -> Mapping[str, object]:
        """JSON-native row shape."""
        return MappingProxyType(
            {
                "name": self.name,
                "owning_subsystem": self.owning_subsystem,
                "scope": self.scope.value,
                "type": self.value_type,
                "units": self.units,
                "default": self.default,
                "editability": self.editability.value,
                "home": self.home,
                "registry_key": self.registry_key,
            }
        )


def _row(
    name: str,
    *,
    owning_subsystem: str,
    scope: VariableScope,
    value_type: str,
    units: str | None,
    default: object,
    editability: VariableEditability = VariableEditability.UI_EDITABLE,
    home: str = REGISTRY_HOME,
) -> VariableRow:
    return VariableRow(
        name=name,
        owning_subsystem=owning_subsystem,
        scope=scope,
        value_type=value_type,
        units=units,
        default=default,
        editability=editability,
        home=home,
    )


def builtin_qma_variable_rows() -> tuple[VariableRow, ...]:
    """QMA AD-26 rows shipped in v1 (DEC-0325).

    Defaults cite declarations, not copies of unresolved values where the spine
    left none.
    """
    daemon = "COMP-QMA-DAEMON"
    wire = "COMP-QMA-WIRE"
    g = VariableScope.GLOBAL
    return (
        _row(
            "quant.quiet_hours",
            owning_subsystem=daemon,
            scope=VariableScope.QUANT,
            value_type="declaration",
            units="schedule",
            default="declared-per-quant",
            home="quant_record.WakePolicy",
        ),
        _row(
            "quant.max_wakes_per_window",
            owning_subsystem=daemon,
            scope=VariableScope.QUANT,
            value_type="count",
            units="count",
            default="declared-per-quant",
            home="quant_record.WakePolicy",
        ),
        _row(
            "hook.timeout_before",
            owning_subsystem=daemon,
            scope=g,
            value_type="duration",
            units="duration",
            default="declared-per-installation",
        ),
        _row(
            "hook.timeout_after",
            owning_subsystem=daemon,
            scope=g,
            value_type="duration",
            units="duration",
            default="declared-per-installation",
        ),
        _row(
            "hook.timeout_control",
            owning_subsystem=daemon,
            scope=g,
            value_type="duration",
            units="duration",
            default="declared-per-installation",
        ),
        _row(
            "mission.ask_timeout",
            owning_subsystem=daemon,
            scope=VariableScope.MISSION,
            value_type="duration",
            units="duration",
            default="declared-per-mission",
            home="mission.approval_route",
        ),
        _row(
            "mission.on_timeout",
            owning_subsystem=daemon,
            scope=VariableScope.MISSION,
            value_type="enum",
            units="enum",
            default="declared-per-mission",
            home="mission.approval_route",
        ),
        _row(
            "wire.deprecation_minors",
            owning_subsystem=wire,
            scope=g,
            value_type="count",
            units="count",
            default=2,
        ),
        _row(
            "wire.dedup_window",
            owning_subsystem=daemon,
            scope=g,
            value_type="duration",
            units="duration",
            default="declared-per-installation",
        ),
        _row(
            "rlm.depth_cap",
            owning_subsystem=daemon,
            scope=g,
            value_type="count",
            units="count",
            default=2,
        ),
        _row(
            "rlm.fanout_cost_ceiling_usd",
            owning_subsystem=daemon,
            scope=VariableScope.DESK,
            value_type="money",
            units="money(numeraire)",
            default="declared-per-installation",
        ),
        _row(
            "telemetry.retention_window",
            owning_subsystem=daemon,
            scope=g,
            value_type="duration",
            units="duration",
            default="declared-per-installation",
        ),
        _row(
            "telemetry.trim_event_count",
            owning_subsystem=daemon,
            scope=g,
            value_type="count",
            units="count",
            default="declared-per-installation",
        ),
        _row(
            "telemetry.trim_disk_bytes",
            owning_subsystem=daemon,
            scope=g,
            value_type="quantity",
            units="bytes",
            default="declared-per-installation",
        ),
        _row(
            "mailbox.delivery_trim_event_count",
            owning_subsystem=daemon,
            scope=g,
            value_type="count",
            units="count",
            default="declared-per-installation",
        ),
        _row(
            "mailbox.delivery_trim_disk_bytes",
            owning_subsystem=daemon,
            scope=g,
            value_type="quantity",
            units="bytes",
            default="declared-per-installation",
        ),
        _row(
            "mailbox.delivery_retention_window",
            owning_subsystem=daemon,
            scope=g,
            value_type="duration",
            units="duration",
            default="declared-per-installation",
        ),
        _row(
            "environment.max_in_flight",
            owning_subsystem=daemon,
            scope=VariableScope.EXECUTION_ENVIRONMENT,
            value_type="count",
            units="count",
            default=1,
            home="execution_environment_declaration",
        ),
        _row(
            "routine.max_concurrent",
            owning_subsystem=daemon,
            scope=VariableScope.ROUTINE,
            value_type="count",
            units="count",
            default="declared-per-routine",
            home="routine_record",
        ),
        _row(
            "continuation.max_consecutive",
            owning_subsystem=daemon,
            scope=g,
            value_type="count",
            units="count",
            default="declared-per-installation",
        ),
        _row(
            "continuation.budget",
            owning_subsystem=daemon,
            scope=g,
            value_type="count",
            units="count",
            default="declared-per-installation",
        ),
        _row(
            "continuation.escalation_target",
            owning_subsystem=daemon,
            scope=g,
            value_type="string",
            units="string",
            default="declared-per-installation",
        ),
        _row(
            "store.backup_cadence",
            owning_subsystem=daemon,
            scope=g,
            value_type="enum",
            units="schedule",
            # Value lives in docs/registry/variables.yaml — code cites the key only.
            default=None,
        ),
        _row(
            "store.sample_restore_test_cadence",
            owning_subsystem=daemon,
            scope=g,
            value_type="enum",
            units="schedule",
            default=None,
        ),
        _row(
            "store.full_restore_rehearsal_cadence",
            owning_subsystem=daemon,
            scope=g,
            value_type="enum",
            units="schedule",
            default=None,
        ),
        _row(
            "proxy.allow_unauthenticated_loopback",
            owning_subsystem=daemon,
            scope=g,
            value_type="enum",
            units=None,
            default=True,
        ),
        _row(
            "deployment.model_family",
            owning_subsystem=daemon,
            scope=g,
            value_type="enum",
            units="enum",
            default="declared-per-installation",
        ),
        _row(
            "review_policy.families",
            owning_subsystem=daemon,
            scope=g,
            value_type="enum",
            units="enum",
            default="declared-per-installation",
        ),
        _row(
            "wire.remote_outbox_depth",
            owning_subsystem=daemon,
            scope=g,
            value_type="count",
            units="count",
            default="declared-per-installation",
        ),
        _row(
            "wire.remote_spool_bytes",
            owning_subsystem=daemon,
            scope=g,
            value_type="quantity",
            units="bytes",
            default="declared-per-installation",
        ),
        _row(
            "deferred.finished_mission_trajectory_count",
            owning_subsystem=daemon,
            scope=g,
            value_type="count",
            units="count",
            default=50,
        ),
        _row(
            "deferred.sandbox_refusal_count",
            owning_subsystem=daemon,
            scope=g,
            value_type="count",
            units="count",
            default=3,
        ),
    )


@dataclass(frozen=True, slots=True)
class VariableSetReceipt:
    """Outcome of an accepted ``variable.set``."""

    name: str
    value: object
    previous: object
    journal: JournalAppendReceipt


@dataclass
class GovernedVariableRegistry:
    """In-memory AD-26 registry with operator-only ``variable.set`` write path."""

    _rows: dict[str, VariableRow] = field(default_factory=dict)
    _values: dict[str, object] = field(default_factory=dict)

    @classmethod
    def with_builtins(cls) -> GovernedVariableRegistry:
        """Load the shipped QMA AD-26 rows."""
        registry = cls()
        for row in builtin_qma_variable_rows():
            registered = registry.register(row)
            if is_refusal(registered):
                msg = f"builtin variable row refused: {row.name}"
                raise RuntimeError(msg)
        return registry

    def rows(self) -> Mapping[str, VariableRow]:
        """Snapshot of registered rows (metadata only for record-homed)."""
        return MappingProxyType(dict(self._rows))

    def values(self) -> Mapping[str, object]:
        """Snapshot of registry-homed runtime values."""
        return MappingProxyType(dict(self._values))

    def register(self, row: VariableRow | Mapping[str, object]) -> Result[VariableRow]:
        """Register one machine-readable variable row (FR-Q36)."""
        parsed = self._coerce_row(row) if not isinstance(row, VariableRow) else Ok(row)
        if is_refusal(parsed):
            return parsed
        item = parsed.value
        if item.name in self._rows:
            return policy_rejection(
                "variable_registry",
                "a variable name may be registered once (FR-Q36; AD-26)",
                name=item.name,
            )
        self._rows[item.name] = item
        if item.is_registry_homed:
            self._values[item.name] = item.default
        return Ok(item)

    def get(self, name: object) -> Result[VariableRow]:
        """Look up a registered row by bare name or ``registry:`` key."""
        resolved = self._resolve_name(name)
        if is_refusal(resolved):
            return resolved
        row = self._rows.get(resolved.value)
        if row is None:
            return policy_rejection(
                "variable_registry",
                "unknown registered variable (FR-Q36; AD-26)",
                name=resolved.value,
            )
        return Ok(row)

    def get_value(self, name: object) -> Result[object]:
        """Return the current registry-homed value; refuse record-homed reads here."""
        row_result = self.get(name)
        if is_refusal(row_result):
            return row_result
        row = row_result.value
        if row.is_record_homed:
            return policy_rejection(
                "variable_value",
                "a record-homed variable's value lives on its owning record, not "
                "in the registry (FR-Q36; AD-26)",
                name=row.name,
                home=row.home,
            )
        return Ok(self._values[row.name])

    def variable_set(
        self,
        name: object,
        value: object,
        *,
        principal_class: object,
        journal: AuthoritativeJournal,
        scope_path: object = (),
        source: object = "operator",
    ) -> Result[VariableSetReceipt]:
        """Set a registry-homed value via operator-principal ``variable.set``.

        Records a ``variable.set`` journal event. Refuses uneditable rows,
        record-homed rows, non-operator principals, and any Agent/hook/Role/
        Mission route (no ``variable`` edit kind).
        """
        if source not in {None, "operator", VARIABLE_SET_COMMAND}:
            return policy_rejection(
                "variable_set",
                "no Agent, hook, Role or Mission may alter a registered value; "
                "there is no variable edit kind and no non-operator configuration "
                "write path (FR-Q36; AD-26)",
                source=repr(source),
            )

        authorized = authorize_wire_command(VARIABLE_SET_COMMAND, principal_class)
        if is_refusal(authorized):
            return authorized
        if authorized.value.principal_class is not PrincipalClass.OPERATOR:
            return OperatorPrincipalRequired.of(
                command=VARIABLE_SET_COMMAND,
                principal_class=str(principal_class),
            )

        row_result = self.get(name)
        if is_refusal(row_result):
            return row_result
        row = row_result.value

        if row.editability is VariableEditability.UNEDITABLE:
            return policy_rejection(
                "variable_set",
                "a variable.set naming an uneditable variable is refused (FR-Q36; AD-26)",
                name=row.name,
                editability=row.editability.value,
            )
        if row.is_record_homed:
            return policy_rejection(
                "variable_set",
                "a variable.set naming a record-homed variable is refused; "
                "change it only through that record's operator-principal write "
                "command (FR-Q36; AD-24, AD-26)",
                name=row.name,
                home=row.home,
            )

        previous = self._values.get(row.name, row.default)
        append = journal.append_event(
            VARIABLE_SET_EVENT,
            scope_path=scope_path,
            payload={
                "name": row.name,
                "registry_key": row.registry_key,
                "value": value,
                "previous": previous,
                "home": row.home,
                "scope": row.scope.value,
            },
        )
        if is_refusal(append):
            return append
        self._values[row.name] = value
        return Ok(
            VariableSetReceipt(
                name=row.name,
                value=value,
                previous=previous,
                journal=append.value,
            )
        )

    def refuse_non_operator_route(
        self,
        name: object,
        value: object,
        *,
        principal_class: object = "machine",
        via: object = "agent",
    ) -> Result[None]:
        """Refuse Agent / hook / Role / Mission configuration-write attempts."""
        _ = (name, value)
        return policy_rejection(
            "variable_set",
            "no Agent, hook, Role or Mission may alter a registered value; "
            "there is no variable edit kind and no non-operator configuration "
            "write path (FR-Q36; AD-26)",
            via=repr(via),
            principal_class=repr(principal_class),
        )

    def _resolve_name(self, name: object) -> Result[str]:
        if not isinstance(name, str) or name.strip() == "":
            return invalid_input(
                "name",
                "a variable name is a non-empty string (FR-Q36; AD-26)",
                given=repr(name),
            )
        return Ok(name.removeprefix("registry:"))

    def _coerce_row(self, raw: Mapping[str, object]) -> Result[VariableRow]:
        name = raw.get("name")
        if not isinstance(name, str) or name.strip() == "":
            return invalid_input("name", "variable row requires a non-empty name")
        owning = raw.get("owning_subsystem")
        if not isinstance(owning, str) or owning.strip() == "":
            return invalid_input(
                "owning_subsystem",
                "variable row declares its owning subsystem (FR-Q36; AD-26)",
            )
        try:
            scope = parse_closed(VariableScope, raw.get("scope"))
        except VocabularyError as exc:
            return policy_rejection(
                "variable_scope",
                "scope is one of the eight closed AD-26 values (FR-Q36; AD-26)",
                detail=str(exc),
                given=repr(raw.get("scope")),
            )
        value_type = raw.get("type")
        if not isinstance(value_type, str) or value_type.strip() == "":
            return invalid_input("type", "variable row declares its type")
        units = raw.get("units")
        if units is not None and not isinstance(units, str):
            return invalid_input("units", "units is a string or null")
        try:
            editability = parse_closed(VariableEditability, raw.get("editability"))
        except VocabularyError as exc:
            return policy_rejection(
                "variable_editability",
                "editability is ui-editable or uneditable (FR-Q36; AD-26)",
                detail=str(exc),
                given=repr(raw.get("editability")),
            )
        home = raw.get("home", REGISTRY_HOME)
        if not isinstance(home, str) or home.strip() == "":
            return invalid_input(
                "home",
                "home is registry or a named owning record type (FR-Q36; AD-26)",
            )
        if "default" not in raw:
            return invalid_input("default", "variable row declares its default")
        return Ok(
            VariableRow(
                name=name,
                owning_subsystem=owning,
                scope=scope,
                value_type=value_type,
                units=units,
                default=raw.get("default"),
                editability=editability,
                home=home,
            )
        )
