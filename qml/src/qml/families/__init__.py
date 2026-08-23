"""Strategy-family keying token (QL-6).

A family is an opaque operator-minted id plus a dated CT-06 metadata record —
the same machinery as ``instrument_class``, under the addable-kinds law, with no
new CT number. QML returns fingerprintable content; a host composition root
stamps writer / sequence / created-at onto the registry record (DEC-0171,
DEC-0176). Constraining stays the Book's job.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.registry import (
    FieldSetKind,
    KindRegistry,
    Registrar,
    RegistrationReceipt,
    RegistrationRecord,
)

from qml._refuse import clean_token, invalid, policy, unavailable

__all__ = [
    "FAMILY_ID_FIELD",
    "FAMILY_KEYED_SURFACES",
    "FORBIDDEN_AUTHORITY_FIELDS",
    "KIND_STRATEGY_FAMILY",
    "STRATEGY_FAMILY_KIND_FORMAT_VERSION",
    "FamilyKeyedSurface",
    "StrategyFamilyId",
    "StrategyFamilyRecord",
    "install_strategy_family_kind",
    "mint_strategy_family",
    "register_strategy_family",
    "resolve_family_at_layer1",
    "strategy_family_kind_contract",
    "validate_family_body",
]

# CT-06 addable kind name (docs/contracts/ct-06-registration.yaml bot_domain_kinds).
KIND_STRATEGY_FAMILY: Final[str] = "strategy-family"
# Per-kind contract format version — not a qml package pin and not a new CT number.
STRATEGY_FAMILY_KIND_FORMAT_VERSION: Final[int] = 1
FAMILY_ID_FIELD: Final[str] = "family_id"

# Retired ArchetypeSpec constraint powers — a family must never carry these.
FORBIDDEN_AUTHORITY_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "permitted_timeframes",
        "permitted_feature_families",
        "mutation_allowances",
    }
)


class FamilyKeyedSurface(StrEnum):
    """Ratified law already keyed by family id; the family itself decides nothing."""

    EXIT_POLICY_EXIT_LOGIC_REF = "exit_policy.ExitLogicRef"
    PAPER_STARTING_BALANCE = "paper_starting_balance"
    BENCH_CONSECUTIVE_LOSS_THRESHOLD = "bench_consecutive_loss_threshold"


FAMILY_KEYED_SURFACES: Final[frozenset[str]] = frozenset(
    member.value for member in FamilyKeyedSurface
)

_EMPTY_POWERS: Final[Mapping[str, object]] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class StrategyFamilyId:
    """Opaque family key. One per Bot definition; the token itself decides nothing."""

    value: str

    @classmethod
    def try_create(cls, value: object) -> Result[StrategyFamilyId]:
        """Validate and build a family id, value-or-refusal.

        The token is stored verbatim and never parsed. A blank or non-string is
        ``invalid input``.
        """
        token = clean_token(value)
        if token is None:
            return invalid(
                "value",
                "a strategy family is a non-empty opaque operator-minted token; it is a "
                "key never an authority",
                given=repr(value),
            )
        return Ok(cls(token))


@dataclass(frozen=True, slots=True)
class StrategyFamilyRecord:
    """Fingerprintable strategy-family metadata content (CT-06 kind body).

    Identity is ``kind`` + per-kind format version + ``family_id``. Occurrence
    facts (writer, sequence, created-at) are host-stamped on the CT-06 envelope
    and never live here — so identical content from two sandboxes deduplicates
    (DEC-0114, DEC-0171). Package SemVer never enters identity (DEC-0180).
    """

    family_id: StrategyFamilyId
    kind_format_version: int = STRATEGY_FAMILY_KIND_FORMAT_VERSION

    def body(self) -> dict[str, object]:
        """Kind-specific CT-06 payload — the family id only, no authority fields."""
        return {FAMILY_ID_FIELD: self.family_id.value}

    def identity_payload(self) -> dict[str, object]:
        """Canonical semantic content for ``fp1``. SemVer and occurrence facts omitted."""
        return {
            "kind": KIND_STRATEGY_FAMILY,
            "contract_format_version": self.kind_format_version,
            "body": self.body(),
        }

    def constraint_powers(self) -> Mapping[str, object]:
        """Always empty — a family is a keying token with no authority (DEC-0176)."""
        return _EMPTY_POWERS

    def keyed_surfaces(self) -> dict[str, str]:
        """Map each ratified keyed surface onto this family id.

        The family decides none of these: Book ``exit_policy`` ``ExitLogicRef``,
        family-scoped paper starting balance, and per-family bench threshold.
        """
        return dict.fromkeys(sorted(FAMILY_KEYED_SURFACES), self.family_id.value)

    def fingerprint_content(self) -> Result[Fingerprint]:
        """``fp1`` over the fingerprintable content, computed only by qmf-core."""
        return fingerprint(self.identity_payload())

    @classmethod
    def try_create(cls, family_id: object) -> Result[StrategyFamilyRecord]:
        """Validate and build fingerprintable family content, value-or-refusal."""
        token = StrategyFamilyId.try_create(family_id)
        if is_refusal(token):
            return token
        return Ok(cls(family_id=token.value))

    @classmethod
    def try_from_body(cls, body: object) -> Result[StrategyFamilyRecord]:
        """Admit a CT-06 strategy-family body, refusing constraint-power fields."""
        admitted = validate_family_body(body)
        if is_refusal(admitted):
            return admitted
        return cls.try_create(admitted.value[FAMILY_ID_FIELD])


def mint_strategy_family(family_id: object) -> Result[StrategyFamilyRecord]:
    """Mint fingerprintable strategy-family metadata content (DEC-0176).

    The dated CT-06 envelope is stamped by a host composition root via
    :func:`register_strategy_family`. This helper never invents a WriterId,
    sequence, or created-at.
    """
    return StrategyFamilyRecord.try_create(family_id)


def strategy_family_kind_contract() -> Result[FieldSetKind]:
    """The CT-06 ``strategy-family`` kind contract — same machinery as instrument-class.

    Required body field is ``family_id`` only. Constraint-power field names are
    not in the field set, so a body carrying them is refused (addable never
    redefined).
    """
    return FieldSetKind.try_create(
        KIND_STRATEGY_FAMILY,
        STRATEGY_FAMILY_KIND_FORMAT_VERSION,
        required_fields=(FAMILY_ID_FIELD,),
        optional_fields=(),
    )


def install_strategy_family_kind(registry: object) -> Result[FieldSetKind]:
    """Register the strategy-family kind on a host :class:`KindRegistry`."""
    if not isinstance(registry, KindRegistry):
        return invalid(
            "registry",
            "the strategy-family kind installs on a CT-06 KindRegistry",
            given=type(registry).__name__,
        )
    contract = strategy_family_kind_contract()
    if is_refusal(contract):
        return contract
    installed = registry.register(contract.value)
    if is_refusal(installed):
        return installed
    return Ok(contract.value)


def validate_family_body(body: object) -> Result[Mapping[str, object]]:
    """Admit a strategy-family body; constraint-power fields are a policy rejection."""
    if not isinstance(body, Mapping):
        return invalid(
            "body",
            "a strategy-family record body is a key->value mapping",
            given=type(body).__name__,
        )
    body_map = cast("Mapping[str, object]", body)
    forbidden = sorted(FORBIDDEN_AUTHORITY_FIELDS.intersection(body_map))
    if forbidden:
        return policy(
            "body",
            "a strategy family is a keying token with no authority; permitted "
            "timeframes, feature families, and mutation allowances are the Book's "
            "job (admission bar, footprint_requirements, prediction linter)",
            forbidden=forbidden,
        )
    contract = strategy_family_kind_contract()
    if is_refusal(contract):
        return contract
    admitted = contract.value.validate_body(body_map)
    if is_refusal(admitted):
        return admitted
    token = StrategyFamilyId.try_create(admitted.value.get(FAMILY_ID_FIELD))
    if is_refusal(token):
        return token
    return Ok(admitted.value)


def register_strategy_family(
    family_id: object,
    *,
    registrar: object,
    writer: object,
    sequence: object,
    created_at: object,
) -> Result[RegistrationReceipt]:
    """Stamp fingerprintable family content onto a host CT-06 :class:`Registrar`.

    The host supplies writer, sequence, and created-at (AD-25 root-mints). The
    kind must already be installed on the registrar's :class:`KindRegistry`.
    """
    if not isinstance(registrar, Registrar):
        return invalid(
            "registrar",
            "a host composition root stamps the dated CT-06 record through a Registrar",
            given=type(registrar).__name__,
        )
    content = mint_strategy_family(family_id)
    if is_refusal(content):
        return content
    return registrar.register(
        kind=KIND_STRATEGY_FAMILY,
        body=content.value.body(),
        writer=writer,
        sequence=sequence,
        created_at=created_at,
    )


def resolve_family_at_layer1(
    family_id: object,
    catalog: object,
) -> Result[StrategyFamilyRecord]:
    """Resolve a cited family id against an as-of catalog of family records (QL-8).

    A miss is ``unavailable dependency``, never a silent pass — Layer 1 journals
    the typed refusal (DEC-0176, DEC-0178). The catalog is host-supplied in-memory
    evidence (RegistrationRecord, fingerprintable content, or a body mapping).
    """
    wanted = StrategyFamilyId.try_create(family_id)
    if is_refusal(wanted):
        return wanted
    items = _iter_catalog(catalog)
    if is_refusal(items):
        return items
    token = wanted.value.value
    for item in items.value:
        peeked = _peek_family_id(item)
        if peeked is None or peeked != token:
            continue
        extracted = _extract_family_record(item)
        if extracted is None:
            continue
        if is_refusal(extracted):
            return extracted
        return extracted
    return unavailable(
        "strategy_family_id",
        "the cited strategy family does not resolve to a dated CT-06 metadata "
        "record; an unresolvable family is an unavailable dependency, never a "
        "silent pass",
        family_id=token,
        kind=KIND_STRATEGY_FAMILY,
        journal=True,
    )


def _iter_catalog(catalog: object) -> Result[tuple[object, ...]]:
    """Snapshot a host as-of catalog to a tuple of items, or refuse."""
    if isinstance(catalog, Mapping):
        mapping = cast("Mapping[object, object]", catalog)
        return Ok(tuple(mapping.values()))
    if isinstance(catalog, Sequence) and not isinstance(catalog, (str, bytes)):
        return Ok(tuple(cast("Sequence[object]", catalog)))
    return invalid(
        "catalog",
        "Layer 1 resolves a family against an as-of catalog of strategy-family records",
        given=type(catalog).__name__,
    )


def _peek_family_id(item: object) -> str | None:
    """The family id an item would resolve, or ``None`` if it is not a family record."""
    if isinstance(item, StrategyFamilyRecord):
        return item.family_id.value
    if isinstance(item, RegistrationRecord):
        if item.kind != KIND_STRATEGY_FAMILY:
            return None
        value = item.body.get(FAMILY_ID_FIELD)
        return value if isinstance(value, str) else None
    if isinstance(item, Mapping):
        mapping = cast("Mapping[str, object]", item)
        kind = mapping.get("kind")
        body = mapping.get("body")
        if kind is not None and kind != KIND_STRATEGY_FAMILY:
            return None
        if isinstance(body, Mapping):
            nested = cast("Mapping[str, object]", body)
            value = nested.get(FAMILY_ID_FIELD)
            if isinstance(value, str):
                return value
        value = mapping.get(FAMILY_ID_FIELD)
        return value if isinstance(value, str) else None
    return None


def _extract_family_record(item: object) -> Result[StrategyFamilyRecord] | None:
    """Build fingerprintable content from a catalog item, or ``None`` if not a family."""
    if isinstance(item, StrategyFamilyRecord):
        return Ok(item)
    if isinstance(item, RegistrationRecord):
        if item.kind != KIND_STRATEGY_FAMILY:
            return None
        return StrategyFamilyRecord.try_from_body(item.body)
    if isinstance(item, Mapping):
        mapping = cast("Mapping[str, object]", item)
        kind = mapping.get("kind")
        if kind is not None and kind != KIND_STRATEGY_FAMILY:
            return None
        body = mapping.get("body")
        if isinstance(body, Mapping):
            nested = cast("Mapping[str, object]", body)
            return StrategyFamilyRecord.try_from_body(nested)
        if FAMILY_ID_FIELD in mapping:
            return StrategyFamilyRecord.try_from_body(mapping)
        return None
    return None
