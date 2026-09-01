"""AD-8 state ownership across the eight store classes (FR-Q26; DEC-0307).

Each persistence class has exactly one named writer, one crossing rule, and one
retention rule. Context is invocation-only; journal evidence, ledgers, artifacts,
staging, and the ledger quarantine stream keep their durable posture.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Literal

from qmf.core import Ok, Result
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "DURABLE_POSTURE_CLASSES",
    "EIGHT_STORE_CLASSES",
    "INVOCATION_ONLY_CLASSES",
    "OwnershipRule",
    "PersistenceClass",
    "StoreOwnershipRegistry",
    "default_ownership_table",
]


class PersistenceClass(StrEnum):
    """The eight AD-8 store classes named by FR-Q26."""

    JOURNAL = "journal"
    LEDGER = "ledger"
    MEMORY = "memory"
    KNOWLEDGE = "knowledge"
    ARTIFACTS = "artifacts"
    CONTEXT = "context"
    TELEMETRY = "telemetry"
    STAGING = "staging"


DurablePosture = Literal["durable", "invocation_only", "provider_owned", "external_readonly"]

EIGHT_STORE_CLASSES: Final[frozenset[str]] = frozenset(member.value for member in PersistenceClass)

# Context is never durable state (FR-Q26; AD-8).
INVOCATION_ONLY_CLASSES: Final[frozenset[str]] = frozenset({PersistenceClass.CONTEXT.value})

# Journal evidence, ledgers, artifacts, staging, and ledger quarantine retain
# durable posture. Quarantine is named separately as a durable companion of ledger.
DURABLE_POSTURE_CLASSES: Final[frozenset[str]] = frozenset(
    {
        PersistenceClass.JOURNAL.value,
        PersistenceClass.LEDGER.value,
        PersistenceClass.ARTIFACTS.value,
        PersistenceClass.STAGING.value,
        "ledger_quarantine",
    }
)


@dataclass(frozen=True, slots=True)
class OwnershipRule:
    """One named writer, crossing rule, and retention rule for a store class."""

    store_class: PersistenceClass
    writer: str
    crossing_rule: str
    retention_rule: str
    posture: DurablePosture

    @property
    def is_invocation_only(self) -> bool:
        """True when the class is discarded with the invocation (context)."""
        return self.posture == "invocation_only"

    @property
    def is_durable(self) -> bool:
        """True when the class retains required durable posture."""
        return self.posture == "durable"


def default_ownership_table() -> Mapping[str, OwnershipRule]:
    """The closed AD-8 ownership table for the eight FR-Q26 classes."""
    rows: tuple[OwnershipRule, ...] = (
        OwnershipRule(
            store_class=PersistenceClass.JOURNAL,
            writer="daemon",
            crossing_rule="own announcement journal_seq stamp",
            retention_rule="forever, backed up, exempt from trim",
            posture="durable",
        ),
        OwnershipRule(
            store_class=PersistenceClass.LEDGER,
            writer="daemon_store_via_before_ledger_append",
            crossing_rule="_ref",
            retention_rule="forever",
            posture="durable",
        ),
        OwnershipRule(
            store_class=PersistenceClass.MEMORY,
            writer="memory_provider",
            crossing_rule="recalled into Context only",
            retention_rule=(
                "until admitted, superseded, invalidated, expired or contradicted"
            ),
            posture="provider_owned",
        ),
        OwnershipRule(
            store_class=PersistenceClass.KNOWLEDGE,
            writer="nobody",
            crossing_rule="Citation with source_ref, locator, snapshot_ref",
            retention_rule="cited copies kept forever in the artifact store",
            posture="external_readonly",
        ),
        OwnershipRule(
            store_class=PersistenceClass.ARTIFACTS,
            writer="daemon_via_before_artifact_register",
            crossing_rule="_ref",
            retention_rule="forever, with lineage",
            posture="durable",
        ),
        OwnershipRule(
            store_class=PersistenceClass.CONTEXT,
            writer="nobody",
            crossing_rule="never persisted",
            retention_rule="discarded with the invocation",
            posture="invocation_only",
        ),
        OwnershipRule(
            store_class=PersistenceClass.TELEMETRY,
            writer="daemon_harness",
            crossing_rule="shares correlation_id; ledger may carry trace_ref, never reverse",
            retention_rule="bounded; trajectories and session replay exempt",
            posture="durable",
        ),
        OwnershipRule(
            store_class=PersistenceClass.STAGING,
            writer="daemon",
            crossing_rule="staged content never read by a runtime path",
            retention_rule="approval decisions and lineage kept forever",
            posture="durable",
        ),
    )
    return MappingProxyType({rule.store_class.value: rule for rule in rows})


@dataclass
class StoreOwnershipRegistry:
    """Registers the eight persistence classes with fixed ownership rules."""

    _rules: dict[str, OwnershipRule]

    def __init__(self, rules: Mapping[str, OwnershipRule] | None = None) -> None:
        source = default_ownership_table() if rules is None else rules
        self._rules = dict(source)

    def registered(self) -> Mapping[str, OwnershipRule]:
        """Snapshot of registered ownership rules."""
        return MappingProxyType(dict(self._rules))

    def get(self, store_class: object) -> Result[OwnershipRule]:
        """Return the ownership rule for a named FR-Q26 class."""
        if not isinstance(store_class, str) or store_class.strip() == "":
            return invalid_input(
                "store_class",
                "ownership lookup names one of the eight AD-8 store classes "
                "(FR-Q26; AD-8)",
                given=repr(store_class),
            )
        rule = self._rules.get(store_class)
        if rule is None:
            return policy_rejection(
                "store_ownership",
                "a store class outside the eight AD-8 classes has no ownership "
                "row (FR-Q26; AD-8)",
                store_class=store_class,
                closed=sorted(EIGHT_STORE_CLASSES),
            )
        return Ok(rule)

    def register_defaults(self) -> Mapping[str, OwnershipRule]:
        """Ensure all eight classes are registered; return the table."""
        for name, rule in default_ownership_table().items():
            self._rules.setdefault(name, rule)
        return self.registered()

    def assert_complete(self) -> Result[Mapping[str, OwnershipRule]]:
        """Refuse when any of the eight classes is missing a rule."""
        missing = sorted(EIGHT_STORE_CLASSES - self._rules.keys())
        if missing:
            return policy_rejection(
                "store_ownership",
                "every FR-Q26 persistence class must declare writer, crossing, "
                "and retention (FR-Q26; AD-8)",
                missing=missing,
            )
        for name, rule in self._rules.items():
            if not rule.writer or not rule.crossing_rule or not rule.retention_rule:
                return policy_rejection(
                    "store_ownership",
                    "each ownership row requires one named writer, one crossing "
                    "rule, and one retention rule (FR-Q26; AD-8)",
                    store_class=name,
                )
        context = self._rules[PersistenceClass.CONTEXT.value]
        if not context.is_invocation_only:
            return policy_rejection(
                "store_ownership",
                "context remains invocation-only rather than durable state "
                "(FR-Q26; AD-8)",
                store_class=PersistenceClass.CONTEXT.value,
                posture=context.posture,
            )
        for name in DURABLE_POSTURE_CLASSES:
            if name == "ledger_quarantine":
                continue
            rule = self._rules[name]
            if not rule.is_durable:
                return policy_rejection(
                    "store_ownership",
                    "journal evidence, ledgers, artifacts, and staging retain "
                    "required durable posture (FR-Q26; AD-8)",
                    store_class=name,
                    posture=rule.posture,
                )
        return Ok(self.registered())

    @property
    def ledger_quarantine_durable(self) -> bool:
        """Ledger quarantine is durable evidence, exempt from trim (AD-8)."""
        return "ledger_quarantine" in DURABLE_POSTURE_CLASSES
