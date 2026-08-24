"""CT-33 Bot definition kind — declaration half of a governed bot (QL-3).

Identity is the six semantic-content groups plus the contract format version
and at-birth refs. The AD-16 header's writer, sequence, stable id, and
created-at are occurrence facts excluded from ``fp1``; the stable id is derived
FROM the fingerprint, never hashed into it (DEC-0173, DEC-0114). QML returns
fingerprintable content; a host composition root stamps the dated CT-06 envelope
(DEC-0171).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.registry import (
    FieldSetKind,
    KindRegistry,
    Registrar,
    RegistrationReceipt,
)

from qml._refuse import invalid, unsupported
from qml.declaration.confluence import Confluence
from qml.declaration.parameters import (
    ParameterSpec,
    canonical_assignment_of,
    coerce_parameter_space,
)
from qml.families import StrategyFamilyId
from qml.footprint import Footprint
from qml.footprint._coerce import coerce_fingerprint
from qml.logic import LogicIdentity
from qml.protocol import permitted_exit_kinds

__all__ = [
    "BOT_DEFINITION_KIND_FORMAT_VERSION",
    "FORBIDDEN_BOT_FIELDS",
    "KIND_BOT_DEFINITION",
    "PERMITTED_EXIT_INTENT_VOCABULARY",
    "BotDefinition",
    "ConfluenceCite",
    "bot_definition_kind_contract",
    "install_bot_definition_kind",
    "mint_bot_definition",
    "promote_tuned_assignment",
    "register_bot_definition",
]

KIND_BOT_DEFINITION: Final[str] = "bot-definition"
BOT_DEFINITION_KIND_FORMAT_VERSION: Final[int] = 1

PERMITTED_EXIT_INTENT_VOCABULARY: Final[frozenset[str]] = frozenset(
    {"close_full", "tighten_protective_stop"}
)

_BODY_FIELDS: Final[tuple[str, ...]] = (
    "strategy_family_id",
    "confluence_set",
    "parameter_space",
    "footprint",
    "permitted_exit_intents",
    "logic_reference",
)

# Occurrence, sizing, venue, and derived fields never enter identity (DEC-0173).
FORBIDDEN_BOT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "writer",
        "sequence",
        "stable_id",
        "stable id",
        "created_at",
        "created-at",
        "exit_logic",
        "requested_r",
        "sizing",
        "venue_command",
        "venue",
        "full_loss_price",
        "declared_full_loss_price",
        "canonical_assignment",
        "seat",
        "seat_binding",
        "binding",
        "paper",
        "paper_mode",
        "rebinding",
        "entry",
        "package_version",
        "version_graph",
        "current",
    }
)

_EMPTY_ASSIGNMENT: Final[Mapping[str, object]] = MappingProxyType({})


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _nonneg_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _as_sequence(value: object, field: str) -> Result[tuple[object, ...]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(field, "expected a sequence", given=type(value).__name__)
    return Ok(tuple(cast("Sequence[object]", value)))


@dataclass(frozen=True, slots=True)
class ConfluenceCite:
    """One cited CT-34 fingerprint plus a display-only ordinal (DEC-0173)."""

    fingerprint: Fingerprint
    display_ordinal: int

    def content_identity(self) -> str:
        return self.fingerprint.value


@dataclass(frozen=True, slots=True)
class BotDefinition:
    """Fingerprintable CT-33 Bot definition content (DEC-0173).

    Six semantic groups: exactly one strategy-family id; one-or-more confluence
    fingerprints; the declared parameter space; the footprint; permitted EXIT
    intents; the logic reference. Canonical assignment is the defaults projection.
    """

    strategy_family_id: StrategyFamilyId
    confluence_set: tuple[ConfluenceCite, ...]
    parameter_space: tuple[ParameterSpec, ...]
    footprint: Footprint
    permitted_exit_intents: tuple[str, ...]
    logic_reference: LogicIdentity
    at_birth_parent_refs: tuple[Fingerprint, ...] = ()
    kind_format_version: int = BOT_DEFINITION_KIND_FORMAT_VERSION

    def canonical_assignment(self) -> Mapping[str, object]:
        """Mandatory defaults taken together — not a separate declared field."""
        if not self.parameter_space:
            return _EMPTY_ASSIGNMENT
        return canonical_assignment_of(self.parameter_space)

    def canonical_confluence_set(self) -> tuple[ConfluenceCite, ...]:
        """Fingerprint-ascending; display ordinals stay out of identity."""
        return tuple(sorted(self.confluence_set, key=lambda cite: cite.fingerprint.value))

    def body(self) -> dict[str, object]:
        """Kind-specific CT-06 payload — identity-bearing six groups, nothing more."""
        return {
            "strategy_family_id": self.strategy_family_id.value,
            "confluence_set": [cite.fingerprint.value for cite in self.canonical_confluence_set()],
            "parameter_space": [spec.fp1_identity() for spec in self.parameter_space],
            "footprint": self.footprint.fp1_identity(),
            "permitted_exit_intents": list(self.permitted_exit_intents),
            "logic_reference": self.logic_reference.as_logic_reference(),
        }

    def identity_payload(self) -> dict[str, object]:
        """Canonical semantic content for ``fp1``.

        Six groups + contract format version + at-birth refs. Writer, sequence,
        stable id, created-at, package SemVer, and occurrence facts are omitted.
        """
        payload: dict[str, object] = {
            "kind": KIND_BOT_DEFINITION,
            "contract_format_version": self.kind_format_version,
            "body": self.body(),
        }
        if self.at_birth_parent_refs:
            payload["at_birth_parent_refs"] = [ref.value for ref in self.at_birth_parent_refs]
        return payload

    def fp1_identity(self) -> dict[str, object]:
        return self.identity_payload()

    def fingerprint_content(self) -> Result[Fingerprint]:
        """``fp1`` over the canonical semantic content (DEC-0173)."""
        return fingerprint(self.identity_payload())

    @classmethod
    def try_create(
        cls,
        *,
        strategy_family_id: object,
        confluence_set: object,
        parameter_space: object,
        footprint: object,
        logic_reference: object,
        permitted_exit_intents: object = (),
        at_birth_parent_refs: object = (),
        format_version: object = BOT_DEFINITION_KIND_FORMAT_VERSION,
    ) -> Result[BotDefinition]:
        """Validate and build fingerprintable Bot definition content."""
        version = _positive_int(format_version)
        if version is None:
            if isinstance(format_version, bool) or not isinstance(format_version, int):
                return invalid(
                    "format_version",
                    "a kind format version is a positive integer; package SemVer never enters",
                    given=repr(format_version),
                )
            return invalid(
                "format_version",
                "a kind format version is a positive integer ordinal",
                given=repr(format_version),
            )
        if version != BOT_DEFINITION_KIND_FORMAT_VERSION:
            return unsupported(
                "contract_format_version",
                "an uninterpretable Bot definition contract format version is an "
                "unsupported capability refusal, never a best-effort read",
                given=version,
                supported=BOT_DEFINITION_KIND_FORMAT_VERSION,
            )
        family = _coerce_family(strategy_family_id)
        if is_refusal(family):
            return family
        cites = _coerce_confluence_set(confluence_set)
        if is_refusal(cites):
            return cites
        space = coerce_parameter_space(parameter_space)
        if is_refusal(space):
            return space
        resolved_footprint = _coerce_footprint(footprint)
        if is_refusal(resolved_footprint):
            return resolved_footprint
        intents = _coerce_exit_intents(permitted_exit_intents)
        if is_refusal(intents):
            return intents
        logic = LogicIdentity.try_from_payload(logic_reference)
        if is_refusal(logic):
            return logic
        parents = _coerce_parent_refs(at_birth_parent_refs)
        if is_refusal(parents):
            return parents
        return Ok(
            cls(
                strategy_family_id=family.value,
                confluence_set=cites.value,
                parameter_space=space.value,
                footprint=resolved_footprint.value,
                permitted_exit_intents=intents.value,
                logic_reference=logic.value,
                at_birth_parent_refs=parents.value,
                kind_format_version=version,
            )
        )

    @classmethod
    def try_from_mapping(cls, payload: object) -> Result[BotDefinition]:
        """Admit a CT-33 mapping (kind envelope, body, or the six groups)."""
        if isinstance(payload, cls):
            return Ok(payload)
        if not isinstance(payload, Mapping):
            return invalid(
                "bot_definition",
                "a Bot definition is a mapping of the six semantic-content groups",
                given=type(payload).__name__,
            )
        mapping = cast("Mapping[str, object]", payload)
        nested = mapping.get("body")
        if isinstance(nested, Mapping) and "strategy_family_id" not in mapping:
            header_refs = mapping.get("at_birth_parent_refs")
            mapping = dict(cast("Mapping[str, object]", nested))
            if header_refs is not None and "at_birth_parent_refs" not in mapping:
                mapping["at_birth_parent_refs"] = header_refs
        blocked = _refuse_forbidden(mapping)
        if is_refusal(blocked):
            return blocked
        version = mapping.get("contract_format_version", mapping.get("format_version"))
        if version is None:
            version = BOT_DEFINITION_KIND_FORMAT_VERSION
        return cls.try_create(
            strategy_family_id=mapping.get("strategy_family_id", mapping.get("family_id")),
            confluence_set=mapping.get("confluence_set"),
            parameter_space=mapping.get("parameter_space", ()),
            footprint=mapping.get("footprint"),
            permitted_exit_intents=mapping.get("permitted_exit_intents", ()),
            logic_reference=mapping.get("logic_reference"),
            at_birth_parent_refs=mapping.get("at_birth_parent_refs", ()),
            format_version=version,
        )


def _refuse_forbidden(mapping: Mapping[str, object]) -> Result[None]:
    forbidden = FORBIDDEN_BOT_FIELDS.intersection(mapping)
    if not forbidden:
        return Ok(None)
    listed = tuple(sorted(forbidden))
    if "canonical_assignment" in forbidden:
        return invalid(
            "canonical_assignment",
            "the canonical assignment is the mandatory-default projection of "
            "parameter_space — one identity locus, not a separate declared field",
            forbidden=listed,
        )
    if forbidden & {
        "exit_logic",
        "requested_r",
        "sizing",
        "venue_command",
        "venue",
        "full_loss_price",
        "declared_full_loss_price",
    }:
        return invalid(
            "bot_definition",
            "the declaration carries no sizing, no venue command, and no exit-logic "
            "field — exit behaviour is the Book's, keyed by the bot's one family",
            forbidden=listed,
        )
    if forbidden & {
        "writer",
        "sequence",
        "stable_id",
        "stable id",
        "created_at",
        "created-at",
    }:
        return invalid(
            "bot_definition",
            "the AD-16 header's writer, sequence, stable id, and created-at are "
            "occurrence fields excluded from fp1 (the stable id is derived from the "
            "fingerprint, never hashed into it)",
            forbidden=listed,
        )
    return invalid(
        "bot_definition",
        "re-binding, seat assignment, and paper flips never mint a new Bot; those "
        "occurrence facts are not identity fields",
        forbidden=listed,
    )


def _coerce_family(value: object) -> Result[StrategyFamilyId]:
    if isinstance(value, StrategyFamilyId):
        return Ok(value)
    if value is None:
        return invalid(
            "strategy_family_id",
            "a Bot definition declares exactly one strategy-family id; a cardinality "
            "of zero is invalid input",
            given=repr(value),
        )
    if isinstance(value, (list, tuple, set, frozenset)):
        items = tuple(cast("Sequence[object]", value))
        if len(items) != 1:
            return invalid(
                "strategy_family_id",
                "a Bot definition declares exactly one strategy-family id; a "
                "cardinality of zero or more-than-one is invalid input "
                "(AD-17 cardinality-one)",
                given=len(items),
            )
        return invalid(
            "strategy_family_id",
            "a Bot definition declares exactly one strategy-family id as an opaque "
            "token, never a sequence",
            given=len(items),
        )
    return StrategyFamilyId.try_create(value)


def _coerce_confluence_cite(value: object, index: int) -> Result[ConfluenceCite]:
    if isinstance(value, ConfluenceCite):
        return Ok(value)
    ordinal = index
    raw: object = value
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        raw = mapping.get(
            "fingerprint",
            mapping.get("fp1", mapping.get("confluence_ref", mapping.get("confluence"))),
        )
        if "display_ordinal" in mapping or "ordinal" in mapping:
            parsed_ordinal = _nonneg_int(mapping.get("display_ordinal", mapping.get("ordinal")))
            if parsed_ordinal is None:
                return invalid(
                    "display_ordinal",
                    "a display ordinal is a non-negative integer; it is always present "
                    "and never enters identity",
                    given=repr(mapping.get("display_ordinal", mapping.get("ordinal"))),
                    index=index,
                )
            ordinal = parsed_ordinal
    if isinstance(raw, Confluence):
        fp = raw.fingerprint_content()
        if is_refusal(fp):
            return fp
        return Ok(ConfluenceCite(fingerprint=fp.value, display_ordinal=ordinal))
    parsed = coerce_fingerprint(raw)
    if is_refusal(parsed):
        return invalid(
            "confluence_set",
            "each confluence cite is a CT-34 fp1:sha256:<hex> fingerprint",
            given=repr(raw),
            index=index,
        )
    return Ok(ConfluenceCite(fingerprint=parsed.value, display_ordinal=ordinal))


def _coerce_confluence_set(value: object) -> Result[tuple[ConfluenceCite, ...]]:
    items = _as_sequence(value, "confluence_set")
    if is_refusal(items):
        if value is None:
            return invalid(
                "confluence_set",
                "the confluence set is one-or-more CT-34 fingerprints; a zero-member "
                "set is invalid input",
            )
        return invalid(
            "confluence_set",
            "the confluence set is a sequence of one-or-more CT-34 fingerprints, "
            "canonically ordered by child fingerprint ascending",
            given=type(value).__name__,
        )
    resolved: list[ConfluenceCite] = []
    seen_fps: set[str] = set()
    seen_ordinals: set[int] = set()
    for index, item in enumerate(items.value):
        cite = _coerce_confluence_cite(item, index)
        if is_refusal(cite):
            return cite
        token = cite.value.fingerprint.value
        if token in seen_fps:
            return invalid(
                "confluence_set",
                "confluence fingerprints are a set; a duplicate cite is invalid input",
                fingerprint=token,
                index=index,
            )
        if cite.value.display_ordinal in seen_ordinals:
            return invalid(
                "display_ordinal",
                "display ordinals are unique within the confluence set",
                display_ordinal=cite.value.display_ordinal,
                index=index,
            )
        seen_fps.add(token)
        seen_ordinals.add(cite.value.display_ordinal)
        resolved.append(cite.value)
    if not resolved:
        return invalid(
            "confluence_set",
            "the confluence set is one-or-more CT-34 fingerprints; a zero-member "
            "set is invalid input",
        )
    return Ok(tuple(resolved))


def _coerce_footprint(value: object) -> Result[Footprint]:
    if isinstance(value, Footprint):
        return Ok(value)
    if value is None:
        return invalid(
            "footprint",
            "the footprint is the single canonical consumption manifest and is mandatory",
        )
    return Footprint.try_from_mapping(value)


def _coerce_exit_intents(value: object) -> Result[tuple[str, ...]]:
    if value is None:
        return Ok(())
    items = _as_sequence(value, "permitted_exit_intents")
    if is_refusal(items):
        return invalid(
            "permitted_exit_intents",
            "permitted EXIT-intent kinds are a sequence (possibly empty); an absent "
            "key is an empty set, never null",
            given=type(value).__name__,
        )
    for item in items.value:
        kind_name: object = item if isinstance(item, str) else getattr(item, "value", item)
        if isinstance(kind_name, str) and kind_name == "entry":
            return invalid(
                "permitted_exit_intents",
                "entry is always permitted and is never declared here; the declaration "
                "names only permitted EXIT-intent kinds",
                given=kind_name,
            )
    parsed = permitted_exit_kinds(items.value)
    if is_refusal(parsed):
        return parsed
    seen: set[str] = set()
    ordered: list[str] = []
    for kind in parsed.value:
        token = kind.value
        if token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    ordered.sort()
    return Ok(tuple(ordered))


def _coerce_parent_refs(value: object) -> Result[tuple[Fingerprint, ...]]:
    if value is None or value == ():
        return Ok(())
    items = _as_sequence(value, "at_birth_parent_refs")
    if is_refusal(items):
        return invalid(
            "at_birth_parent_refs",
            "at-birth parent refs are a sequence of fingerprints (identity-bearing); "
            "an empty set is an omitted key, never null",
            given=type(value).__name__,
        )
    resolved: list[Fingerprint] = []
    seen: set[str] = set()
    for index, item in enumerate(items.value):
        parsed = coerce_fingerprint(item)
        if is_refusal(parsed):
            return invalid(
                "at_birth_parent_refs",
                "each at-birth parent ref is an fp1:sha256:<hex> fingerprint",
                index=index,
                given=repr(item),
            )
        if parsed.value.value in seen:
            continue
        seen.add(parsed.value.value)
        resolved.append(parsed.value)
    resolved.sort(key=lambda ref: ref.value)
    return Ok(tuple(resolved))


def mint_bot_definition(
    payload: object = None,
    *,
    strategy_family_id: object = None,
    confluence_set: object = None,
    parameter_space: object = None,
    footprint: object = None,
    permitted_exit_intents: object = None,
    logic_reference: object = None,
    at_birth_parent_refs: object = None,
    format_version: object = BOT_DEFINITION_KIND_FORMAT_VERSION,
) -> Result[BotDefinition]:
    """Mint fingerprintable CT-33 Bot definition content (DEC-0173).

    The dated CT-06 envelope is stamped by a host composition root via
    :func:`register_bot_definition`. This helper never invents a WriterId,
    sequence, or created-at.
    """
    if isinstance(payload, BotDefinition):
        return Ok(payload)
    mapping: dict[str, object] = {}
    if isinstance(payload, Mapping):
        mapping.update(cast("Mapping[str, object]", payload))
    elif payload is not None:
        return invalid(
            "bot_definition",
            "a Bot definition is a mapping of the six semantic-content groups",
            given=type(payload).__name__,
        )
    if strategy_family_id is not None:
        mapping["strategy_family_id"] = strategy_family_id
    if confluence_set is not None:
        mapping["confluence_set"] = confluence_set
    if parameter_space is not None:
        mapping["parameter_space"] = parameter_space
    if footprint is not None:
        mapping["footprint"] = footprint
    if permitted_exit_intents is not None:
        mapping["permitted_exit_intents"] = permitted_exit_intents
    if logic_reference is not None:
        mapping["logic_reference"] = logic_reference
    if at_birth_parent_refs is not None:
        mapping["at_birth_parent_refs"] = at_birth_parent_refs
    mapping["contract_format_version"] = format_version
    return BotDefinition.try_from_mapping(mapping)


def promote_tuned_assignment(
    parent: object,
    assignment: object,
) -> Result[BotDefinition]:
    """Mint a new Bot version whose defaults are the tuned assignment (DEC-0173).

    Governed live/paper seats execute the canonical assignment only; promoting a
    tuned assignment mints a NEW Bot (``branches-from``) so it cannot silently
    wear the original's track record. The caller appends the new fingerprint to
    a :class:`~qml.declaration.versioning.BotVersionGraph`.
    """
    content = mint_bot_definition(parent)
    if is_refusal(content):
        return content
    if not isinstance(assignment, Mapping):
        return invalid(
            "assignment",
            "a tuned assignment is a name-keyed mapping of parameter values",
            given=type(assignment).__name__,
        )
    values = cast("Mapping[object, object]", assignment)
    expected = {spec.name for spec in content.value.parameter_space}
    names = {key for key in values if isinstance(key, str)}
    if names != expected or len(values) != len(expected):
        return invalid(
            "assignment",
            "a promoted assignment names every declared parameter exactly once",
            expected=sorted(expected),
            given=sorted(str(key) for key in values),
        )
    updated: list[ParameterSpec] = []
    for spec in content.value.parameter_space:
        rebuilt = spec.with_default(values[spec.name])
        if is_refusal(rebuilt):
            return rebuilt
        updated.append(rebuilt.value)
    return BotDefinition.try_create(
        strategy_family_id=content.value.strategy_family_id,
        confluence_set=content.value.confluence_set,
        parameter_space=updated,
        footprint=content.value.footprint,
        permitted_exit_intents=content.value.permitted_exit_intents,
        logic_reference=content.value.logic_reference,
        at_birth_parent_refs=content.value.at_birth_parent_refs,
        format_version=content.value.kind_format_version,
    )


def bot_definition_kind_contract() -> Result[FieldSetKind]:
    """The CT-06 ``bot-definition`` kind contract — body field names only."""
    return FieldSetKind.try_create(
        KIND_BOT_DEFINITION,
        BOT_DEFINITION_KIND_FORMAT_VERSION,
        required_fields=_BODY_FIELDS,
        optional_fields=(),
    )


def install_bot_definition_kind(registry: object) -> Result[FieldSetKind]:
    """Register the Bot definition kind on a host :class:`KindRegistry`."""
    if not isinstance(registry, KindRegistry):
        return invalid(
            "registry",
            "the Bot definition kind installs on a CT-06 KindRegistry",
            given=type(registry).__name__,
        )
    contract = bot_definition_kind_contract()
    if is_refusal(contract):
        return contract
    installed = registry.register(contract.value)
    if is_refusal(installed):
        return installed
    return Ok(contract.value)


def register_bot_definition(
    payload: object,
    *,
    registrar: object,
    writer: object,
    sequence: object,
    created_at: object,
    at_birth_parent_refs: object = None,
) -> Result[RegistrationReceipt]:
    """Stamp fingerprintable Bot definition content onto a host CT-06 Registrar.

    The host supplies writer, sequence, and created-at (AD-25 root-mints). The
    writer unit is ``(machine, authoring role, kind)``. qml never returns this
    stamped record from :func:`mint_bot_definition`.
    """
    if not isinstance(registrar, Registrar):
        return invalid(
            "registrar",
            "a host composition root stamps the dated CT-06 record through a Registrar",
            given=type(registrar).__name__,
        )
    content = mint_bot_definition(payload, at_birth_parent_refs=at_birth_parent_refs)
    if is_refusal(content):
        return content
    return registrar.register(
        kind=KIND_BOT_DEFINITION,
        body=content.value.body(),
        writer=writer,
        sequence=sequence,
        created_at=created_at,
        at_birth_parent_refs=content.value.at_birth_parent_refs,
    )
