"""Stage 0 → Stage 1 collapse helpers (Story 51.2).

Open Stage 0 roles collapse into the closed CT-34 enum or Python WHEN.
Unresolved F becomes empty ``permitted_exit_intents`` / Book family policy —
graduation never invents exits, producers, or CT-29 close-reasons.
``entry_hypothesis`` stays Stage 0 taxonomy, never a CT-33 field.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qml._refuse import invalid, policy
from qml.research.stage0 import (
    F_LABELS,
    F_SLOTS,
    HYPOTHESIS_CLASSES,
    Hypothesis,
    RoleBinding,
)

__all__ = [
    "CT34_LEG_ROLES",
    "INFORMAL_ROLE_TO_CT34",
    "PYTHON_WHEN_REMAINDERS",
    "STAGE0_CLASS_IS_CT33_FIELD",
    "CollapsedRoles",
    "UnresolvedFCollapse",
    "collapse_stage0_roles",
    "collapse_unresolved_f",
    "refuse_entry_hypothesis_as_ct33_field",
    "refuse_invented_ct34_role",
    "refuse_invented_exits",
]

# Closed CT-34 enum mirrored here so qml.research stays free of declaration imports.
CT34_LEG_ROLES: Final[frozenset[str]] = frozenset({"level", "trigger", "confirmation", "filter"})
STAGE0_CLASS_IS_CT33_FIELD: Final[bool] = False

# Informal handoff aid (AD-7) — not a contract mint.
INFORMAL_ROLE_TO_CT34: Final[Mapping[str, str]] = MappingProxyType(
    {
        "level": "level",
        "location": "level",
        "trigger": "trigger",
        "confirmation": "confirmation",
        "filter": "filter",
    }
)

# Remainder lands in Python WHEN — never a new CT-34 role / GAP-0085 noun.
PYTHON_WHEN_REMAINDERS: Final[frozenset[str]] = frozenset(
    {
        "all",
        "sequence",
        "within",
        "invalidation",
        "target",
        "targets",
        "context",
        "arming",
        "then",
        "management",
        "stop",
        "exit",
    }
)


@dataclass(frozen=True, slots=True)
class CollapsedRoles:
    """CT-34 legs plus Python WHEN remainder from open Stage 0 roles."""

    ct34_roles: tuple[str, ...]
    python_when: tuple[str, ...]

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "ct34_roles": list(self.ct34_roles),
                "python_when": list(self.python_when),
                "allowed_ct34": sorted(CT34_LEG_ROLES),
            }
        )


@dataclass(frozen=True, slots=True)
class UnresolvedFCollapse:
    """Unresolved F → empty exit intents; Book family policy may still apply."""

    permitted_exit_intents: tuple[str, ...]
    book_family_policy: bool
    invented_exits: bool = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "permitted_exit_intents": list(self.permitted_exit_intents),
                "book_family_policy": self.book_family_policy,
                "invented_exits": self.invented_exits,
            }
        )


def collapse_stage0_roles(bindings: object) -> Result[CollapsedRoles]:
    """Collapse open Stage 0 roles into CT-34 enum + Python WHEN remainder."""
    roles = _admit_role_tokens(bindings)
    if is_refusal(roles):
        return roles
    return _partition_roles(roles.value)


def collapse_unresolved_f(
    f_labels: object = None,
    *,
    invent_exits: object = False,
    invent_producers: object = False,
    invent_close_reasons: object = False,
) -> Result[UnresolvedFCollapse]:
    """Unresolved F → empty ``permitted_exit_intents`` and/or Book family policy."""
    if invent_exits is True or invent_producers is True or invent_close_reasons is True:
        return refuse_invented_exits(
            invent_exits=invent_exits,
            invent_producers=invent_producers,
            invent_close_reasons=invent_close_reasons,
        )
    labels = _admit_f_labels(f_labels)
    if is_refusal(labels):
        return labels
    return Ok(
        UnresolvedFCollapse(
            permitted_exit_intents=(),
            book_family_policy=True,
            invented_exits=False,
        )
    )


def refuse_invented_exits(
    *,
    invent_exits: object = True,
    invent_producers: object = False,
    invent_close_reasons: object = False,
) -> TypedRefusal:
    """Graduation refuses invented exits / producers / CT-29 close-reasons."""
    return policy(
        "permitted_exit_intents",
        "graduation refuses to invent exits, producers, or CT-29 close-reasons "
        "to complete a hypothesis (DEC-0400)",
        invented_exits=bool(invent_exits),
        invented_producers=bool(invent_producers),
        invented_close_reasons=bool(invent_close_reasons),
        permitted_exit_intents=(),
        book_family_policy=True,
    )


def refuse_invented_ct34_role(role: object) -> TypedRefusal:
    """Refuse a CT-34 role outside level|trigger|confirmation|filter."""
    return policy(
        "role",
        "CT-34 legs use only level | trigger | confirmation | filter; remainder "
        "lands in Python WHEN, not a new CT-34 role and not GAP-0085 nouns",
        given=repr(role),
        allowed=sorted(CT34_LEG_ROLES),
        gap_0085=False,
    )


def refuse_entry_hypothesis_as_ct33_field(value: object = "entry_hypothesis") -> Result[None]:
    """``entry_hypothesis`` is Stage 0 taxonomy, not a CT-33 field."""
    token = value if isinstance(value, str) else type(value).__name__
    return policy(
        "class",
        "entry_hypothesis is Stage 0 taxonomy, not a CT-33 field (AD-20; DEC-0400)",
        given=token,
        stage0_classes=tuple(sorted(HYPOTHESIS_CLASSES)),
        is_ct33_field=STAGE0_CLASS_IS_CT33_FIELD,
    )


def _partition_roles(roles: tuple[str, ...]) -> Result[CollapsedRoles]:
    ct34: list[str] = []
    python_when: list[str] = []
    for role in roles:
        mapped = INFORMAL_ROLE_TO_CT34.get(role)
        if mapped is not None:
            ct34.append(mapped)
            continue
        if role in CT34_LEG_ROLES:
            ct34.append(role)
            continue
        # ALL/sequence/within, invalidation, and other open roles → Python WHEN.
        python_when.append(role)
    for token in ct34:
        if token not in CT34_LEG_ROLES:
            return refuse_invented_ct34_role(token)
    return Ok(CollapsedRoles(ct34_roles=tuple(ct34), python_when=tuple(python_when)))


def _admit_role_tokens(bindings: object) -> Result[tuple[str, ...]]:
    if bindings is None:
        return Ok(())
    if isinstance(bindings, Hypothesis):
        return Ok(tuple(item.role for item in bindings.role_bindings))
    if isinstance(bindings, RoleBinding):
        return Ok((bindings.role,))
    if isinstance(bindings, str):
        return _admit_role_string(bindings)
    if isinstance(bindings, Sequence) and not isinstance(bindings, (str, bytes)):
        return _admit_role_sequence(cast("Sequence[object]", bindings))
    return invalid(
        "role_bindings",
        "collapse consumes Stage 0 role bindings or role tokens",
        given=type(bindings).__name__,
    )


def _admit_role_string(bindings: str) -> Result[tuple[str, ...]]:
    token = bindings.casefold().strip()
    if token == "":
        return invalid("role", "Stage 0 role is a non-empty string", given=repr(bindings))
    return Ok((token,))


def _admit_role_sequence(bindings: Sequence[object]) -> Result[tuple[str, ...]]:
    out: list[str] = []
    for item in bindings:
        token = _one_role_token(item)
        if is_refusal(token):
            return token
        out.append(token.value)
    return Ok(tuple(out))


def _one_role_token(item: object) -> Result[str]:
    if isinstance(item, RoleBinding):
        return Ok(item.role)
    if isinstance(item, str) and item.strip() != "":
        return Ok(item.casefold().strip())
    if isinstance(item, Mapping):
        role = cast("Mapping[str, object]", item).get("role")
        if isinstance(role, str) and role.strip() != "":
            return Ok(role.casefold().strip())
    return invalid(
        "role_bindings",
        "collapse consumes Stage 0 role bindings or role tokens",
        given=type(cast("object", item)).__name__,
    )


def _admit_f_labels(value: object) -> Result[Mapping[str, str]]:
    if value is None:
        return Ok(MappingProxyType(dict.fromkeys(F_SLOTS, "unresolved")))
    if isinstance(value, Hypothesis):
        return Ok(value.f_labels)
    if not isinstance(value, Mapping):
        return invalid(
            "f_labels",
            "F labels are a mapping of Stage 0 F slots",
            given=type(value).__name__,
        )
    return _admit_f_label_map(cast("Mapping[str, object]", value))


def _admit_f_label_map(mapping: Mapping[str, object]) -> Result[Mapping[str, str]]:
    out: dict[str, str] = {}
    for key, raw in mapping.items():
        if key not in F_SLOTS:
            return invalid("f_labels", "F label keys are Stage 0 F slots", given=repr(key))
        if not isinstance(raw, str) or raw not in F_LABELS:
            return invalid(
                "f_labels",
                "F label values are the closed Stage 0 F label set",
                given=repr(raw),
                allowed=tuple(sorted(F_LABELS)),
            )
        out[key] = raw
    return Ok(MappingProxyType(out))
