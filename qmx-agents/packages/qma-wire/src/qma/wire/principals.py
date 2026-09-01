"""Principal classes and the closed human-gate command list (AD-24; DEC-0323; FR-Q20).

Every authenticated wire connection carries exactly one principal class,
``operator`` or ``machine``, recorded verbatim on every command and in the
contract shapes for journal and ledger records. The closed human-gate list is
the sole authority on which commands require an ``operator`` principal; a
``machine`` principal on any listed command returns ``OperatorPrincipalRequired``.
A machine principal may not acquire, delegate, borrow, cache, or impersonate
``operator`` through this wire.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qma.core.refusals import OperatorPrincipalRequired
from qma.core.vocabulary import (
    PrincipalClass,
    assert_no_principal_conversion,
    may_convert_principal,
    parse_closed,
)
from qma.core.vocabulary.registry import VocabularyError
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "DAEMON_JOB_TRIM_STREAMS",
    "HUMAN_GATE_COMMANDS",
    "HUMAN_GATE_OWNING_AD",
    "HUMAN_GATE_VOCABULARY_OWNER",
    "AuthorizedWireCommand",
    "JournalPrincipalShape",
    "LedgerPrincipalShape",
    "PrincipalBearingCommand",
    "authorize_wire_command",
    "command_carries_principal",
    "is_daemon_job_trim",
    "is_human_gate_command",
    "journal_entry_principal_shape",
    "ledger_entry_principal_shape",
    "parse_principal_class",
    "refuse_principal_impersonation",
]


HUMAN_GATE_VOCABULARY_OWNER: Final[str] = "qma-wire"
HUMAN_GATE_OWNING_AD: Final[str] = "AD-24"

# Closed-and-addable human-gate command list (DEC-0323). Extended only by a
# spine amendment — never silently by a client, worker, plugin, or daemon module.
HUMAN_GATE_COMMANDS: Final[frozenset[str]] = frozenset(
    {
        "admission.approve",
        "migration.confirm_forward_only",
        "unknown.resolve",
        "retention.trim",
        "plugin.install",
        "plugin.enable",
        "plugin.reload",
        "desk.create",
        "quant.create",
        "role.set_base",
        "model_family.assign",
        "tool_adapter.write",
        "store.restore_live",
        "routine.catch_up",
        "approval_request.read",
        "approval_request.answer",
        "desk.moved",
        "quant.write",
        "routine.write",
        "execution_environment.write",
        "mission.set_approval_route",
        "variable.set",
        "human_gate.answer",
        # Seed packet aliases that fall under the AD-24 list (DEC-0304 nouns).
        "install_enable_plugin",
        "approve_hook_action",
    }
)

# The two AD-23 daemon-job trims exempt from the human-gate retention.trim rule
# when performed inside their registered retention windows (DEC-0322, DEC-0323).
DAEMON_JOB_TRIM_STREAMS: Final[frozenset[str]] = frozenset(
    {
        "mailbox.delivery",
        "telemetry",
    }
)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def parse_principal_class(value: object) -> Result[PrincipalClass]:
    """Accept only ``operator`` or ``machine`` (exactly one class per connection)."""
    try:
        return Ok(parse_closed(PrincipalClass, value))
    except VocabularyError as exc:
        return _invalid("principal_class", str(exc), given=repr(value))


def is_human_gate_command(command: object) -> bool:
    """True when ``command`` is on the closed AD-24 human-gate list."""
    return isinstance(command, str) and command in HUMAN_GATE_COMMANDS


def is_daemon_job_trim(
    command: object,
    *,
    stream: object = None,
    inside_retention_window: bool = False,
) -> bool:
    """True for the two AD-23 daemon-job trims inside their registered windows."""
    if command != "retention.trim":
        return False
    if not inside_retention_window:
        return False
    return isinstance(stream, str) and stream in DAEMON_JOB_TRIM_STREAMS


def refuse_principal_impersonation(
    source: object,
    target: object,
) -> Result[PrincipalClass]:
    """Refuse any attempt to acquire, borrow, or impersonate another class."""
    parsed_source = parse_principal_class(source)
    if not isinstance(parsed_source, Ok):
        return parsed_source
    parsed_target = parse_principal_class(target)
    if not isinstance(parsed_target, Ok):
        return parsed_target
    src = parsed_source.value
    dst = parsed_target.value
    if may_convert_principal(src, dst):
        return Ok(src)
    try:
        assert_no_principal_conversion(src, dst)
    except VocabularyError:
        pass
    return OperatorPrincipalRequired.of(
        command="principal.impersonate",
        principal_class=src.value,
    )


@dataclass(frozen=True, slots=True)
class PrincipalBearingCommand:
    """Command contract shape carrying the connection principal verbatim."""

    command: str
    principal_class: PrincipalClass
    args: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "command": self.command,
            "principal_class": self.principal_class.value,
            "args": dict(self.args),
        }


@dataclass(frozen=True, slots=True)
class AuthorizedWireCommand:
    """Authorization outcome: principal preserved; primitive still validates separately."""

    command: str
    principal_class: PrincipalClass
    human_gate: bool
    args: Mapping[str, object]

    def to_command_shape(self) -> PrincipalBearingCommand:
        return PrincipalBearingCommand(
            command=self.command,
            principal_class=self.principal_class,
            args=self.args,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "command": self.command,
            "principal_class": self.principal_class.value,
            "human_gate": self.human_gate,
            "args": dict(self.args),
            # Authorization grants no blanket authority — daemon primitive validates.
            "blanket_authority": False,
        }


@dataclass(frozen=True, slots=True)
class JournalPrincipalShape:
    """Journal entry contract shape: principal class recorded verbatim (DEC-0323)."""

    event: str
    principal_class: PrincipalClass
    correlation_id: str
    payload: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "event": self.event,
            "principal_class": self.principal_class.value,
            "correlation_id": self.correlation_id,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class LedgerPrincipalShape:
    """Ledger entry contract shape: principal class recorded verbatim (DEC-0323)."""

    kind: str
    principal_class: PrincipalClass
    correlation_id: str
    body: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "principal_class": self.principal_class.value,
            "correlation_id": self.correlation_id,
            "body": dict(self.body),
        }


def command_carries_principal(
    command: object,
    principal_class: object,
    *,
    args: Mapping[str, object] | None = None,
) -> Result[PrincipalBearingCommand]:
    """Build the command contract shape with ``principal_class`` stamped verbatim."""
    if not isinstance(command, str) or command.strip() == "":
        return _invalid("command", "command must be a non-empty string", given=repr(command))
    parsed = parse_principal_class(principal_class)
    if not isinstance(parsed, Ok):
        return parsed
    frozen_args: Mapping[str, object] = MappingProxyType(dict(args or {}))
    return Ok(
        PrincipalBearingCommand(
            command=command,
            principal_class=parsed.value,
            args=frozen_args,
        )
    )


def journal_entry_principal_shape(
    *,
    event: object,
    principal_class: object,
    correlation_id: object,
    payload: Mapping[str, object] | None = None,
) -> Result[JournalPrincipalShape]:
    """Journal contract shape carrying the connection principal verbatim."""
    if not isinstance(event, str) or event.strip() == "":
        return _invalid("event", "journal event must be a non-empty string")
    if not isinstance(correlation_id, str) or correlation_id.strip() == "":
        return _invalid("correlation_id", "correlation_id must be a non-empty string")
    parsed = parse_principal_class(principal_class)
    if not isinstance(parsed, Ok):
        return parsed
    return Ok(
        JournalPrincipalShape(
            event=event,
            principal_class=parsed.value,
            correlation_id=correlation_id,
            payload=MappingProxyType(dict(payload or {})),
        )
    )


def ledger_entry_principal_shape(
    *,
    kind: object,
    principal_class: object,
    correlation_id: object,
    body: Mapping[str, object] | None = None,
) -> Result[LedgerPrincipalShape]:
    """Ledger contract shape carrying the connection principal verbatim."""
    if not isinstance(kind, str) or kind.strip() == "":
        return _invalid("kind", "ledger kind must be a non-empty string")
    if not isinstance(correlation_id, str) or correlation_id.strip() == "":
        return _invalid("correlation_id", "correlation_id must be a non-empty string")
    parsed = parse_principal_class(principal_class)
    if not isinstance(parsed, Ok):
        return parsed
    return Ok(
        LedgerPrincipalShape(
            kind=kind,
            principal_class=parsed.value,
            correlation_id=correlation_id,
            body=MappingProxyType(dict(body or {})),
        )
    )


def authorize_wire_command(
    command: object,
    principal_class: object,
    *,
    args: Mapping[str, object] | None = None,
    trim_stream: object = None,
    inside_retention_window: bool = False,
) -> Result[AuthorizedWireCommand]:
    """Authorize a wire command under the connection's principal class.

    Human-gate commands require ``operator`` and refuse ``machine`` with
    ``OperatorPrincipalRequired``. The two AD-23 daemon-job retention trims
    (mailbox delivery / telemetry, inside their windows) are exempt. Success
    preserves the principal verbatim and grants no blanket authority — the
    daemon-owned primitive still validates separately.
    """
    if not isinstance(command, str) or command.strip() == "":
        return _invalid("command", "command must be a non-empty string", given=repr(command))
    parsed = parse_principal_class(principal_class)
    if not isinstance(parsed, Ok):
        return parsed
    principal = parsed.value

    human_gate = is_human_gate_command(command)
    if human_gate and is_daemon_job_trim(
        command,
        stream=trim_stream,
        inside_retention_window=inside_retention_window,
    ):
        human_gate = False

    if human_gate and principal is not PrincipalClass.OPERATOR:
        return OperatorPrincipalRequired.of(
            command=command,
            principal_class=principal.value,
        )

    frozen_args: Mapping[str, object]
    if args is None:
        frozen_args = MappingProxyType({})
    else:
        frozen_args = MappingProxyType(dict(args))

    return Ok(
        AuthorizedWireCommand(
            command=command,
            principal_class=principal,
            human_gate=human_gate,
            args=frozen_args,
        )
    )
