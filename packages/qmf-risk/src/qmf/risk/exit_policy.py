"""Story 11.7 — CT-22 format-2 ``exit_policy`` catch-all default entry.

Format 1's ``exit_policy`` already declared ``ExitLogicRef = {module_id, config}``
per strategy family (DEC-0147). Format 2 adds **exactly one** explicit optional
catch-all default entry, applied when a bot's family resolves no explicit entry
(DEC-0176, DEC-0181). The CT-29 exit record keys the **resolved** entry
(explicit family or this catch-all) so loss-predicate attribution stays
unambiguous; a family that resolves neither fails later at the prediction linter
(QL-8) — this module exposes the resolution.

A format-1 ``exit_policy`` cannot carry the catch-all (the field does not exist
yet). qmf-risk imports only ``qmf-core`` and sibling modules (L30/DEC-0120).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    Ok as _Ok,
)
from qmf.core import (
    Result as _Result,
)
from qmf.core import (
    TypedRefusal as _TypedRefusal,
)
from qmf.risk._common import clean_str, coerce_enum, invalid, type_name, unsupported
from qmf.risk.door import ExitKind, ExitLogicRef

__all__ = [
    "EXIT_POLICY_CATCH_ALL_FORMAT_VERSION",
    "ExitPolicy",
    "ExitPolicyResolution",
    "ProtectiveStopAttachment",
    "ResolvedExitPolicyEntry",
    "resolve_exit_policy_entry",
]

EXIT_POLICY_CATCH_ALL_FORMAT_VERSION: Final[int] = 2


class ProtectiveStopAttachment(StrEnum):
    """Whether the Book requires a protective stop at entry (CT-22; DEC-0147)."""

    REQUIRED = "required"
    OPTIONAL = "optional"


class ExitPolicyResolution(StrEnum):
    """How an ``exit_policy`` entry was selected for a strategy family (DEC-0176)."""

    EXPLICIT_FAMILY = "explicit-family"
    CATCH_ALL_DEFAULT = "catch-all-default"


@dataclass(frozen=True, slots=True)
class ResolvedExitPolicyEntry:
    """The CT-29-keyed resolved exit_policy entry — explicit family or catch-all."""

    family_id: str
    entry: ExitLogicRef
    resolution: ExitPolicyResolution

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the resolved entry."""
        return {
            "class": "resolved-exit-policy-entry",
            "family_id": self.family_id,
            "entry": self.entry.fp1_identity(),
            "resolution": self.resolution.value,
            "format_version": EXIT_POLICY_CATCH_ALL_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ExitPolicy:
    """A Book's ``exit_policy`` — per-family ExitLogicRef plus optional format-2 catch-all.

    ``family_entries`` keys by strategy-family id. ``catch_all_default_entry`` exists
    only at contract format version 2 and is optional (a single default). Permitted
    exit-intent kinds are a subset of the V1 CT-23 exit vocabulary and may be empty
    (a static-protective-stop-only Book is the honest V1 default). ``entry`` is never
    gated here.
    """

    family_entries: Mapping[str, ExitLogicRef]
    permitted_exit_intent_kinds: frozenset[ExitKind]
    protective_stop_attachment: ProtectiveStopAttachment
    catch_all_default_entry: ExitLogicRef | None = None
    contract_format_version: int = EXIT_POLICY_CATCH_ALL_FORMAT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "family_entries", MappingProxyType(dict(self.family_entries)))
        object.__setattr__(
            self, "permitted_exit_intent_kinds", frozenset(self.permitted_exit_intent_kinds)
        )

    @classmethod
    def try_create(
        cls,
        family_entries: object,
        permitted_exit_intent_kinds: object = (),
        protective_stop_attachment: object = ProtectiveStopAttachment.REQUIRED,
        *,
        catch_all_default_entry: object = None,
        contract_format_version: object = EXIT_POLICY_CATCH_ALL_FORMAT_VERSION,
    ) -> _Result[ExitPolicy]:
        """Validate and build an :class:`ExitPolicy`, value-or-refusal.

        Format 1 cannot carry ``catch_all_default_entry`` (the field is format-2
        surface). An unknown ``contract_format_version`` is ``unsupported capability``.
        """
        if isinstance(contract_format_version, bool) or not isinstance(
            contract_format_version, int
        ):
            return unsupported(
                "contract_format_version",
                "an exit_policy contract format version is an integer this build understands",
                given=repr(contract_format_version),
            )
        if contract_format_version not in {1, EXIT_POLICY_CATCH_ALL_FORMAT_VERSION}:
            return unsupported(
                "contract_format_version",
                "an exit_policy contract format version this build does not understand; "
                "an unknown version is never best-effort read",
                given=repr(contract_format_version),
                understood=[1, EXIT_POLICY_CATCH_ALL_FORMAT_VERSION],
            )
        resolved_entries = _coerce_family_entries(family_entries)
        if isinstance(resolved_entries, _TypedRefusal):
            return resolved_entries
        resolved_kinds = _coerce_exit_kinds(permitted_exit_intent_kinds)
        if isinstance(resolved_kinds, _TypedRefusal):
            return resolved_kinds
        resolved_attachment = coerce_enum(ProtectiveStopAttachment, protective_stop_attachment)
        if resolved_attachment is None:
            return invalid(
                "protective_stop_attachment",
                "protective-stop attachment is required | optional",
                given=repr(protective_stop_attachment),
                allowed=[member.value for member in ProtectiveStopAttachment],
            )
        resolved_catch_all: ExitLogicRef | None = None
        if catch_all_default_entry is not None:
            if contract_format_version < EXIT_POLICY_CATCH_ALL_FORMAT_VERSION:
                return invalid(
                    "catch_all_default_entry",
                    "the exit_policy catch-all default entry lands only through the CT-22 "
                    "format-2 mint; a format-1 exit_policy cannot carry it",
                    given=repr(catch_all_default_entry),
                )
            if not isinstance(catch_all_default_entry, ExitLogicRef):
                return invalid(
                    "catch_all_default_entry",
                    "the catch-all default entry is an ExitLogicRef when present",
                    given=repr(catch_all_default_entry),
                )
            resolved_catch_all = catch_all_default_entry
        return _Ok(
            cls(
                family_entries=resolved_entries,
                permitted_exit_intent_kinds=resolved_kinds,
                protective_stop_attachment=resolved_attachment,
                catch_all_default_entry=resolved_catch_all,
                contract_format_version=contract_format_version,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity — catch-all omitted when absent."""
        content: dict[str, object] = {
            "class": "exit-policy",
            "contract_format_version": self.contract_format_version,
            "family_entries": {
                family: entry.fp1_identity() for family, entry in self.family_entries.items()
            },
            "permitted_exit_intent_kinds": sorted(
                kind.value for kind in self.permitted_exit_intent_kinds
            ),
            "protective_stop_attachment": self.protective_stop_attachment.value,
        }
        if (
            self.contract_format_version >= EXIT_POLICY_CATCH_ALL_FORMAT_VERSION
            and self.catch_all_default_entry is not None
        ):
            content["catch_all_default_entry"] = self.catch_all_default_entry.fp1_identity()
        return content


def _coerce_family_entries(
    value: object,
) -> Mapping[str, ExitLogicRef] | _TypedRefusal:
    """Resolve a family-id -> ExitLogicRef mapping."""
    if not isinstance(value, Mapping):
        return invalid(
            "family_entries",
            "exit_policy family entries are a strategy-family-id -> ExitLogicRef mapping",
            given=type_name(value),
        )
    mapping = cast("Mapping[object, object]", value)
    resolved: dict[str, ExitLogicRef] = {}
    for key, entry in mapping.items():
        token = clean_str(key)
        if token is None:
            return invalid(
                "family_entries",
                "an exit_policy family key is a non-empty strategy-family id",
                given=repr(key),
            )
        if not isinstance(entry, ExitLogicRef):
            return invalid(
                "family_entries",
                "each exit_policy family entry is an ExitLogicRef",
                family_id=token,
                given=repr(entry),
            )
        resolved[token] = entry
    return MappingProxyType(resolved)


def _coerce_exit_kinds(value: object) -> frozenset[ExitKind] | _TypedRefusal:
    """Resolve a (possibly empty) subset of the V1 CT-23 exit vocabulary."""
    given = type_name(value)
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return invalid(
            "permitted_exit_intent_kinds",
            "permitted exit-intent kinds are a collection of V1 ExitKind values (may be empty)",
            given=given,
        )
    kinds: set[ExitKind] = set()
    for item in cast("Iterable[object]", value):
        if isinstance(item, str) and item == "close_partial":
            return unsupported(
                "permitted_exit_intent_kinds",
                "close_partial is not a V1 exit kind; a partial exit is an "
                "unsupported-capability refusal",
            )
        resolved = coerce_enum(ExitKind, item)
        if resolved is None:
            return invalid(
                "permitted_exit_intent_kinds",
                "each permitted exit-intent kind is close_full | tighten_protective_stop",
                given=repr(item),
                allowed=[member.value for member in ExitKind],
            )
        kinds.add(resolved)
    return frozenset(kinds)


def resolve_exit_policy_entry(
    policy: object, family_id: object
) -> _Result[ResolvedExitPolicyEntry]:
    """Resolve a bot's strategy family to an ``exit_policy`` entry (DEC-0176).

    Prefers the explicit family entry; otherwise the format-2 catch-all default.
    A family that matches neither is ``invalid input`` — the prediction linter
    (QL-8) fails the seat; this function is the resolution the linter and CT-29
    keying share.
    """
    if not isinstance(policy, ExitPolicy):
        return invalid("policy", "resolution reads an ExitPolicy", given=repr(policy))
    token = clean_str(family_id)
    if token is None:
        return invalid(
            "family_id",
            "exit_policy resolution keys by a non-empty strategy-family id",
            given=repr(family_id),
        )
    explicit = policy.family_entries.get(token)
    if explicit is not None:
        return _Ok(
            ResolvedExitPolicyEntry(
                family_id=token, entry=explicit, resolution=ExitPolicyResolution.EXPLICIT_FAMILY
            )
        )
    if policy.catch_all_default_entry is not None:
        return _Ok(
            ResolvedExitPolicyEntry(
                family_id=token,
                entry=policy.catch_all_default_entry,
                resolution=ExitPolicyResolution.CATCH_ALL_DEFAULT,
            )
        )
    return invalid(
        "exit_policy",
        "the bot's strategy family resolves no exit_policy entry — neither an explicit "
        "family entry nor the declared catch-all default",
        family_id=token,
    )
