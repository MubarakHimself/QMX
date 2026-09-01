"""Example: principal classes and human-gate authorization (FR-Q20)."""

from __future__ import annotations

from qma.wire import (
    HUMAN_GATE_COMMANDS,
    WireConnection,
    authorize_wire_command,
    journal_entry_principal_shape,
    ledger_entry_principal_shape,
)
from qmf.core.refusal import Ok, is_refusal


def main() -> None:
    print(f"human-gate commands: {len(HUMAN_GATE_COMMANDS)}")

    operator = WireConnection()
    operator.authenticate("cred://operator/desk", principal_class="operator")
    allowed = operator.authorize_command("desk.create", args={"slug": "research"})
    assert isinstance(allowed, Ok)
    print("operator desk.create:", allowed.value.to_dict())

    machine = authorize_wire_command("desk.create", "machine")
    assert is_refusal(machine)
    print("machine desk.create refused:", machine.context.get("variant"))

    journal = journal_entry_principal_shape(
        event="desk.created",
        principal_class="operator",
        correlation_id="corr-example",
        payload={"slug": "research"},
    )
    assert isinstance(journal, Ok)
    ledger = ledger_entry_principal_shape(
        kind="task.dispatched",
        principal_class="machine",
        correlation_id="corr-example",
        body={"task_id": "t-1"},
    )
    assert isinstance(ledger, Ok)
    print("journal principal:", journal.value.to_dict()["principal_class"])
    print("ledger principal:", ledger.value.to_dict()["principal_class"])


if __name__ == "__main__":
    main()
