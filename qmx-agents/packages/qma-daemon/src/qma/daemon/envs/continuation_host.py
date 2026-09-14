"""Laptop-off continuation host gate (DEC-0278; FR-W35).

Evaluates the daemon-property configuration: ``qma-daemon`` plus a reachable
remote ExecutionEnvironment plus the Story 41.4 durable outbox. Does not
rewrite Task Graph continuation budgets (Story 46.7), QMB process-per-run,
or the outbox spool. GAP-0062's always-on host stays operator config.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from qma.core.ontology.continuation import CONTINUATION_BOUND_KEYS
from qma.core.ports.continuation_host import (
    CONTINUATION_LAPTOP_OFF_PROMISED_KEY,
    GAP_0062_ALWAYS_ON_HOST,
    GAP_0062_HOST_MACHINE,
    LAPTOP_OFF_OWNERS,
    ContinuationDoor,
    DurableOutboxPosture,
    JobLifetime,
    LaptopOffAdmission,
    classify_job_lifetime,
    evaluate_laptop_off_configuration,
    parse_laptop_off_promised,
)
from qma.daemon.envs.registry import ExecutionEnvironmentRegistry
from qma.daemon.journal.authoritative import AuthoritativeJournal
from qma.daemon.journal.variables import GovernedVariableRegistry, VariableSetReceipt
from qma.wire.outbox import RemoteOutbox
from qmf.core import Ok, Result, is_refusal

__all__ = [
    "CONTINUATION_BOUND_KEYS",
    "CONTINUATION_LAPTOP_OFF_PROMISED_KEY",
    "GAP_0062_ALWAYS_ON_HOST",
    "GAP_0062_HOST_MACHINE",
    "LAPTOP_OFF_OWNERS",
    "LaptopOffContinuationGate",
    "durable_outbox_posture",
]


def durable_outbox_posture(outbox: RemoteOutbox | None) -> DurableOutboxPosture:
    """Story 41.4 ``RemoteOutbox`` is ordered and fsynced by construction."""
    if outbox is None:
        return DurableOutboxPosture(present=False, ordered=False, fsynced=False)
    return DurableOutboxPosture(present=True, ordered=True, fsynced=True)


class LaptopOffContinuationGate:
    """Daemon-owned laptop-off configuration. Does not mint a host machine."""

    def __init__(
        self,
        *,
        environments: ExecutionEnvironmentRegistry | None = None,
        variables: GovernedVariableRegistry | None = None,
        outbox: RemoteOutbox | None = None,
    ) -> None:
        self._environments = (
            environments if environments is not None else ExecutionEnvironmentRegistry()
        )
        self._variables = (
            variables if variables is not None else GovernedVariableRegistry.with_builtins()
        )
        self._outbox = outbox

    @property
    def environments(self) -> ExecutionEnvironmentRegistry:
        return self._environments

    @property
    def variables(self) -> GovernedVariableRegistry:
        return self._variables

    @property
    def outbox(self) -> RemoteOutbox | None:
        return self._outbox

    @property
    def bound_keys(self) -> tuple[str, str, str]:
        """Story 46.7 continuation budgets — unchanged by this gate."""
        return CONTINUATION_BOUND_KEYS

    def bind_outbox(self, outbox: RemoteOutbox | None) -> None:
        self._outbox = outbox

    def promise(
        self,
        promised: bool,
        *,
        journal: AuthoritativeJournal,
        principal_class: object = "operator",
    ) -> Result[VariableSetReceipt]:
        """Record the laptop-off promise via operator ``variable.set``."""
        parsed = parse_laptop_off_promised(promised)
        if is_refusal(parsed):
            return parsed
        return self._variables.variable_set(
            CONTINUATION_LAPTOP_OFF_PROMISED_KEY,
            parsed.value,
            principal_class=principal_class,
            journal=journal,
        )

    def promised(self) -> Result[bool]:
        got = self._variables.get_value(CONTINUATION_LAPTOP_OFF_PROMISED_KEY)
        if is_refusal(got):
            return got
        return parse_laptop_off_promised(got.value)

    def evaluate(
        self,
        *,
        door: ContinuationDoor | str | None = None,
        promised: bool | None = None,
    ) -> Result[LaptopOffAdmission]:
        """Admit laptop-off only for daemon continuation with a reachable remote env."""
        lifetime = JobLifetime.DAEMON_CONTINUATION
        if door is not None:
            classified = classify_job_lifetime(door)
            if is_refusal(classified):
                return classified
            lifetime = classified.value
        if promised is None:
            flag = self.promised()
            if is_refusal(flag):
                return flag
            promised_flag = flag.value
        else:
            parsed = parse_laptop_off_promised(promised)
            if is_refusal(parsed):
                return parsed
            promised_flag = parsed.value
        return evaluate_laptop_off_configuration(
            promised=promised_flag,
            daemon_present=True,
            daemon_on_workstation=True,
            envs=self._environments.continuation_env_views(),
            outbox=durable_outbox_posture(self._outbox),
            lifetime=lifetime,
        )

    def snapshot(self) -> Mapping[str, object]:
        promised = self.promised()
        return MappingProxyType(
            {
                "promised": promised.value if isinstance(promised, Ok) else False,
                "host_machine": GAP_0062_HOST_MACHINE,
                "gap": dict(GAP_0062_ALWAYS_ON_HOST),
                "owners": list(LAPTOP_OFF_OWNERS),
                "bound_keys": list(self.bound_keys),
                "outbox": dict(durable_outbox_posture(self._outbox).to_payload()),
                "envs": [
                    dict(view.to_payload()) for view in self._environments.continuation_env_views()
                ],
            }
        )
