"""Agent-run continuation bounds (CT-49; AD-29; DEC-0328, DEC-0325; FR-Q63).

Definitions only. Continuation is a property of the Agent run, not of a Routine
record. Cap, budget, and escalation target are the three AD-26 registry-homed
keys and nothing else — no spine default, no model-authored completion, and no
invented Task to fill remaining budget.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qma.core.vocabulary.enums import VariableEditability, VariableScope
from qmf.core import Ok, Result, is_ok
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "CONTINUATION_BOUND_KEYS",
    "CONTINUATION_BUDGET_KEY",
    "CONTINUATION_EDITABILITY",
    "CONTINUATION_ESCALATION_TARGET_KEY",
    "CONTINUATION_HOME",
    "CONTINUATION_MAX_CONSECUTIVE_KEY",
    "CONTINUATION_SCOPE",
    "CONTINUATION_UNDECLARED_VALUE",
    "ContinuationBounds",
    "is_continuation_bound_key",
    "parse_continuation_bounds",
    "refuse_invented_continuation_task",
    "refuse_model_authored_completion",
]


CONTINUATION_MAX_CONSECUTIVE_KEY: Final[str] = "registry:continuation.max_consecutive"
CONTINUATION_BUDGET_KEY: Final[str] = "registry:continuation.budget"
CONTINUATION_ESCALATION_TARGET_KEY: Final[str] = "registry:continuation.escalation_target"
CONTINUATION_BOUND_KEYS: Final[tuple[str, str, str]] = (
    CONTINUATION_MAX_CONSECUTIVE_KEY,
    CONTINUATION_BUDGET_KEY,
    CONTINUATION_ESCALATION_TARGET_KEY,
)
CONTINUATION_HOME: Final[str] = "registry"
CONTINUATION_SCOPE: Final[VariableScope] = VariableScope.GLOBAL
CONTINUATION_EDITABILITY: Final[VariableEditability] = VariableEditability.UI_EDITABLE
# Builtin registry default token — not a bound. Operator ``variable.set`` replaces it.
CONTINUATION_UNDECLARED_VALUE: Final[str] = "declared-per-installation"

_BARE_BOUND_NAMES: Final[frozenset[str]] = frozenset(
    {
        "continuation.max_consecutive",
        "continuation.budget",
        "continuation.escalation_target",
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


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def is_continuation_bound_key(name: object) -> bool:
    """True when ``name`` is one of the three registry continuation bound keys."""
    if not isinstance(name, str) or name.strip() == "":
        return False
    key = name if name.startswith("registry:") else f"registry:{name}"
    return key in CONTINUATION_BOUND_KEYS


def refuse_model_authored_completion(
    *,
    source: object = "model",
    **extra: object,
) -> TypedRefusal:
    """Refuse a model-authored completion standing in for the verifier."""
    return _policy(
        "completion",
        "a Task is not complete until the deterministic verifier passes; no "
        "model-authored outcome substitutes for the verifier's result "
        "(CT-49; AD-29; FR-Q63)",
        source=repr(source),
        model_substituted=True,
        complete=False,
        **extra,
    )


def refuse_invented_continuation_task(
    *,
    source: object = "continuation",
    **extra: object,
) -> TypedRefusal:
    """Refuse minting a Task to fill remaining continuation budget."""
    return _policy(
        "continuation",
        "an Agent that exhausts its continuation budget escalates to its Quant "
        "Mailbox and stops; it neither invents a Task nor continues merely to "
        "fill the remaining time (CT-49; AD-29; FR-Q63)",
        source=repr(source),
        invented_task=False,
        **extra,
    )


def _canonical_bound_key(name: object) -> str | None:
    if not isinstance(name, str) or name.strip() == "":
        return None
    stripped = name.strip()
    if stripped in _BARE_BOUND_NAMES:
        return f"registry:{stripped}"
    if stripped in CONTINUATION_BOUND_KEYS:
        return stripped
    return None


def _parse_count(value: object, field: str) -> Result[int]:
    if value == CONTINUATION_UNDECLARED_VALUE:
        return _invalid(
            field,
            "continuation bounds have no spine default; an operator-principal "
            "variable.set must declare the registry-homed value (CT-49; AD-26; "
            "FR-Q63)",
            given=repr(value),
            registry_key=field,
        )
    if isinstance(value, bool) or not isinstance(value, int):
        return _invalid(
            field,
            "continuation cap and budget are counts declared on the registry "
            "row, never a model-authored number (CT-49; FR-Q63)",
            given=repr(value),
            registry_key=field,
        )
    if value < 0:
        return _invalid(
            field,
            "continuation cap and budget must be >= 0 (CT-49; FR-Q63)",
            given=value,
            registry_key=field,
        )
    return Ok(value)


def _parse_target(value: object) -> Result[str]:
    if value == CONTINUATION_UNDECLARED_VALUE:
        return _invalid(
            CONTINUATION_ESCALATION_TARGET_KEY,
            "continuation.escalation_target has no spine default; an "
            "operator-principal variable.set must declare it (CT-49; AD-26; "
            "FR-Q63)",
            given=repr(value),
        )
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(
            CONTINUATION_ESCALATION_TARGET_KEY,
            "escalation_target is a non-empty registry-homed string (CT-49; FR-Q63)",
            given=repr(value),
        )
    return Ok(value.strip())


@dataclass(frozen=True, slots=True)
class ContinuationBounds:
    """Resolved Agent-run continuation ceilings from the three registry keys."""

    max_consecutive: int
    budget: int
    escalation_target: str

    @property
    def source_keys(self) -> tuple[str, str, str]:
        return CONTINUATION_BOUND_KEYS

    @property
    def max_consecutive_key(self) -> str:
        return CONTINUATION_MAX_CONSECUTIVE_KEY

    @property
    def budget_key(self) -> str:
        return CONTINUATION_BUDGET_KEY

    @property
    def escalation_target_key(self) -> str:
        return CONTINUATION_ESCALATION_TARGET_KEY

    @property
    def home(self) -> str:
        return CONTINUATION_HOME

    @property
    def scope(self) -> VariableScope:
        return CONTINUATION_SCOPE

    def exhausted(self, *, consecutive: int, budget_used: int) -> bool:
        """True when either registered ceiling has been reached."""
        return consecutive >= self.max_consecutive or budget_used >= self.budget

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "max_consecutive": self.max_consecutive,
                "budget": self.budget,
                "escalation_target": self.escalation_target,
                "max_consecutive_key": self.max_consecutive_key,
                "budget_key": self.budget_key,
                "escalation_target_key": self.escalation_target_key,
                "source_keys": list(self.source_keys),
                "home": self.home,
                "scope": self.scope.value,
            }
        )


def parse_continuation_bounds(values: Mapping[str, object]) -> Result[ContinuationBounds]:
    """Accept only the three registry continuation keys as the bound source."""
    canonical: dict[str, object] = {}
    extras: list[str] = []
    for raw_name, raw_value in values.items():
        key = _canonical_bound_key(raw_name)
        if key is None:
            extras.append(str(raw_name))
            continue
        canonical[key] = raw_value
    if extras:
        return _policy(
            "continuation",
            "continuation bounds use only registry:continuation.max_consecutive, "
            "registry:continuation.budget, and registry:continuation.escalation_target "
            "(CT-49; AD-26; FR-Q63)",
            extra_keys=extras,
            allowed=list(CONTINUATION_BOUND_KEYS),
        )
    missing = [key for key in CONTINUATION_BOUND_KEYS if key not in canonical]
    if missing:
        return _invalid(
            "continuation",
            "all three registry continuation bounds are required (CT-49; FR-Q63)",
            missing=missing,
            allowed=list(CONTINUATION_BOUND_KEYS),
        )
    max_consecutive = _parse_count(
        canonical[CONTINUATION_MAX_CONSECUTIVE_KEY],
        CONTINUATION_MAX_CONSECUTIVE_KEY,
    )
    if not is_ok(max_consecutive):
        return max_consecutive
    budget = _parse_count(canonical[CONTINUATION_BUDGET_KEY], CONTINUATION_BUDGET_KEY)
    if not is_ok(budget):
        return budget
    target = _parse_target(canonical[CONTINUATION_ESCALATION_TARGET_KEY])
    if not is_ok(target):
        return target
    return Ok(
        ContinuationBounds(
            max_consecutive=max_consecutive.value,
            budget=budget.value,
            escalation_target=target.value,
        )
    )
