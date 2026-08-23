"""CT-34 confluence kind — reusable Bot-domain registry artifact (QL-5).

A confluence is its own registry artifact (AD-17): one-or-more legs of any role
mix from the closed-and-addable vocabulary ``level | trigger | confirmation |
filter``. Each leg carries a producer binding (pinned CT-16/CT-17 fingerprint or
QL-4 template) and/or a child-confluence cite; at least one of the two is
required and the role is always mandatory. Condition semantics live in Python
logic in V1 — the declaration names what is consumed and which role each plays
(DEC-0175, DEC-0185).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core.exact import ExactRational
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_ok, is_refusal
from qmf.registry import (
    FieldSetKind,
    KindRegistry,
    Registrar,
    RegistrationReceipt,
    RegistrationRecord,
)

from qml._refuse import invalid, unavailable, unsupported
from qml.footprint import ProducerBinding, ProducerBindingForm
from qml.footprint._coerce import coerce_fingerprint, coerce_parameters

__all__ = [
    "CONFLUENCE_KIND_FORMAT_VERSION",
    "FORBIDDEN_CONDITION_FIELDS",
    "KIND_CONFLUENCE",
    "LEG_ROLES",
    "Confluence",
    "ConfluenceLeg",
    "ConfluenceOrdering",
    "LegRole",
    "confluence_kind_contract",
    "install_confluence_kind",
    "mint_confluence",
    "parse_leg_role",
    "parse_ordering",
    "register_confluence",
    "resolve_confluence_at_layer1",
]

KIND_CONFLUENCE: Final[str] = "confluence"
CONFLUENCE_KIND_FORMAT_VERSION: Final[int] = 1
_LEGS_FIELD: Final[str] = "legs"
_ORDER_FIELD: Final[str] = "order_significance"

# Condition / predicate keys are not declaration surface in V1 (DEC-0175).
FORBIDDEN_CONDITION_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "condition",
        "conditions",
        "when",
        "predicate",
        "satisfied_when",
        "grammar",
        "expression",
        "filter_expr",
    }
)

_EMPTY_PARAMS: Final[Mapping[str, ExactRational]] = MappingProxyType({})

_LEG_KNOWN_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "role",
        "producer_binding",
        "confluence_ref",
        "declared_parameters",
        "display_ordinal",
        "producer",
        "binding",
        "confluence_id",
        "parameters",
        "ordinal",
    }
)


class LegRole(StrEnum):
    """CT-34 closed-and-addable leg-role vocabulary (DEC-0175). ``filter`` is first-addition."""

    LEVEL = "level"
    TRIGGER = "trigger"
    CONFIRMATION = "confirmation"
    FILTER = "filter"


LEG_ROLES: Final[frozenset[str]] = frozenset(member.value for member in LegRole)


class ConfluenceOrdering(StrEnum):
    """CT-34 ordering: fingerprint-ascending default, order-significance opt-in (DEC-0175)."""

    FINGERPRINT_ASCENDING = "fingerprint-ascending"
    DECLARED_ORDER_SIGNIFICANT = "declared-order-significant"


def parse_leg_role(value: object) -> Result[LegRole]:
    """Resolve a leg role, value-or-refusal."""
    if isinstance(value, LegRole):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(LegRole(value))
        except ValueError:
            pass
    return invalid(
        "role",
        "a confluence leg role is level | trigger | confirmation | filter "
        "(closed-and-addable; a further role is a contract-format-version mint)",
        given=repr(value),
        allowed=sorted(LEG_ROLES),
    )


def parse_ordering(value: object) -> Result[ConfluenceOrdering]:
    """Resolve confluence ordering; omitted/false is the fingerprint-ascending default."""
    if value is None:
        return Ok(ConfluenceOrdering.FINGERPRINT_ASCENDING)
    if isinstance(value, ConfluenceOrdering):
        return Ok(value)
    if value is False:
        return Ok(ConfluenceOrdering.FINGERPRINT_ASCENDING)
    if value is True:
        return Ok(ConfluenceOrdering.DECLARED_ORDER_SIGNIFICANT)
    if isinstance(value, str):
        try:
            return Ok(ConfluenceOrdering(value))
        except ValueError:
            pass
        if value in {"order-significant", "order_significant", "declared"}:
            return Ok(ConfluenceOrdering.DECLARED_ORDER_SIGNIFICANT)
        if value in {"order-insignificant", "order_insignificant", "default"}:
            return Ok(ConfluenceOrdering.FINGERPRINT_ASCENDING)
    return invalid(
        _ORDER_FIELD,
        "ordering is fingerprint-ascending (default) or declared-order-significant (opt-in)",
        given=repr(value),
    )


def _as_sequence(value: object, field: str) -> Result[tuple[object, ...]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(field, "expected a sequence", given=type(value).__name__)
    return Ok(tuple(cast("Sequence[object]", value)))


def _nonneg_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _condition_refusal(field: str, keys: Sequence[str]) -> Result[None]:
    forbidden = sorted(FORBIDDEN_CONDITION_FIELDS.intersection(keys))
    if not forbidden:
        return Ok(None)
    return invalid(
        field,
        "condition semantics live in the Python logic in V1; the declaration carries "
        "what is consumed and which role each plays, never when a leg is satisfied",
        forbidden=tuple(forbidden),
    )


@dataclass(frozen=True, slots=True)
class ConfluenceLeg:
    """One CT-34 leg: mandatory role plus producer binding and/or child cite."""

    role: LegRole
    display_ordinal: int
    producer_binding: ProducerBinding | None = None
    confluence_ref: Fingerprint | None = None
    declared_parameters: Mapping[str, ExactRational] = _EMPTY_PARAMS

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "declared_parameters", MappingProxyType(dict(self.declared_parameters))
        )

    def content_identity(self) -> dict[str, object]:
        """Leg identity excluding display ordinal (the fingerprint-ascending key)."""
        content: dict[str, object] = {"role": self.role.value}
        if self.producer_binding is not None:
            content["producer_binding"] = self.producer_binding.fp1_identity()
        if self.confluence_ref is not None:
            content["confluence_ref"] = self.confluence_ref.value
        if self.declared_parameters:
            content["declared_parameters"] = {
                name: param.fp1_identity()
                for name, param in sorted(self.declared_parameters.items())
            }
        return content

    def fp1_identity(self) -> dict[str, object]:
        """Default leg identity omits the display ordinal (order-insignificant)."""
        return self.content_identity()

    def identity_for(self, ordering: ConfluenceOrdering) -> dict[str, object]:
        content = self.content_identity()
        if ordering is ConfluenceOrdering.DECLARED_ORDER_SIGNIFICANT:
            content["display_ordinal"] = self.display_ordinal
        return content

    def content_fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.content_identity())

    def as_completeness_leg(self) -> dict[str, object]:
        """Mapping form the QL-4 transitive-union walker already understands."""
        payload: dict[str, object] = {"role": self.role.value}
        if self.producer_binding is not None:
            payload["producer_binding"] = self.producer_binding
        if self.confluence_ref is not None:
            payload["confluence_ref"] = self.confluence_ref.value
        return payload

    @classmethod
    def try_create(
        cls,
        payload: object = None,
        *,
        role: object = None,
        producer_binding: object = None,
        confluence_ref: object = None,
        declared_parameters: object = None,
        display_ordinal: object = None,
        index: int = 0,
    ) -> Result[ConfluenceLeg]:
        """Validate one leg; role is mandatory and at least one cite-or-binding is required."""
        if isinstance(payload, cls):
            return Ok(payload)
        mapping: dict[str, object] = {}
        if payload is not None:
            if not isinstance(payload, Mapping):
                return invalid(
                    "legs",
                    "each leg is a mapping of role plus a producer binding and/or a "
                    "child-confluence cite",
                    given=type(payload).__name__,
                    index=index,
                )
            mapping.update(cast("Mapping[str, object]", payload))
        if role is not None:
            mapping["role"] = role
        if producer_binding is not None:
            mapping["producer_binding"] = producer_binding
        if confluence_ref is not None:
            mapping["confluence_ref"] = confluence_ref
        if declared_parameters is not None:
            mapping["declared_parameters"] = declared_parameters
        if display_ordinal is not None:
            mapping["display_ordinal"] = display_ordinal
        blocked = _condition_refusal("legs", tuple(mapping))
        if is_refusal(blocked):
            return blocked
        unknown = sorted(set(mapping) - _LEG_KNOWN_FIELDS)
        if unknown:
            return invalid(
                "legs",
                "a confluence leg carries role, producer_binding, confluence_ref, "
                "declared_parameters, and display_ordinal only; unknown fields are "
                "refused (addable never redefined)",
                unknown=unknown,
                index=index,
            )
        if "role" not in mapping:
            return invalid(
                "role",
                "a confluence leg role is mandatory (level | trigger | confirmation | filter)",
                index=index,
            )
        parsed_role = parse_leg_role(mapping["role"])
        if is_refusal(parsed_role):
            return parsed_role
        raw_binding = mapping.get(
            "producer_binding", mapping.get("producer", mapping.get("binding"))
        )
        binding: ProducerBinding | None = None
        if raw_binding is not None:
            made = ProducerBinding.try_create(raw_binding)
            if is_refusal(made):
                return invalid(
                    "producer_binding",
                    "a leg producer binding is a pinned CT-16/CT-17 fingerprint or a "
                    "QL-4 template (a complete configuration minus only space-bound values)",
                    index=index,
                    cause=dict(made.context),
                )
            binding = made.value
        raw_ref = mapping.get("confluence_ref", mapping.get("confluence_id"))
        child: Fingerprint | None = None
        if raw_ref is not None:
            parsed_ref = _coerce_child_ref(raw_ref)
            if is_refusal(parsed_ref):
                return parsed_ref
            child = parsed_ref.value
        if binding is None and child is None:
            return invalid(
                "legs",
                "a leg carries a producer binding, a child-confluence cite, or both; "
                "at least one of the two is required, the role always mandatory",
                index=index,
                role=parsed_role.value.value,
            )
        raw_params = mapping.get("declared_parameters", mapping.get("parameters"))
        params = coerce_parameters(raw_params)
        if is_refusal(params):
            return invalid(
                "declared_parameters",
                "leg declared parameters are exact rationals or scaled integers "
                "(AD-7 — no binary float); an omitted key, never null",
                index=index,
                cause=dict(params.context),
            )
        raw_ordinal = mapping.get("display_ordinal", mapping.get("ordinal", index))
        ordinal = _nonneg_int(raw_ordinal)
        if ordinal is None:
            return invalid(
                "display_ordinal",
                "a display ordinal is a non-negative integer; it is always present "
                "and enters identity only when order-significance is declared",
                given=repr(raw_ordinal),
                index=index,
            )
        return Ok(
            cls(
                role=parsed_role.value,
                display_ordinal=ordinal,
                producer_binding=binding,
                confluence_ref=child,
                declared_parameters=params.value,
            )
        )


def _coerce_child_ref(value: object) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    if isinstance(value, Confluence):
        return value.fingerprint_content()
    pinned = coerce_fingerprint(value)
    if is_ok(pinned):
        return pinned
    return invalid(
        "confluence_ref",
        "a cited child confluence is an fp1:sha256:<hex> fingerprint of another "
        "CT-34 confluence (composition; the child is its own artifact)",
        given=repr(value),
    )


@dataclass(frozen=True, slots=True)
class Confluence:
    """Fingerprintable CT-34 confluence content (DEC-0175).

    Identity is ``kind`` + per-kind format version + the canonical leg set, plus
    the order-significance declaration only when present. Display ordinals and
    occurrence facts never enter ``fp1`` under the fingerprint-ascending default.
    Package SemVer never enters identity (DEC-0180).
    """

    legs: tuple[ConfluenceLeg, ...]
    ordering: ConfluenceOrdering = ConfluenceOrdering.FINGERPRINT_ASCENDING
    kind_format_version: int = CONFLUENCE_KIND_FORMAT_VERSION

    @property
    def order_significant(self) -> bool:
        return self.ordering is ConfluenceOrdering.DECLARED_ORDER_SIGNIFICANT

    def canonical_legs(self) -> tuple[ConfluenceLeg, ...]:
        """Legs in identity order: fingerprint-ascending, or display-ordinal when opted in."""
        if self.order_significant:
            return tuple(sorted(self.legs, key=lambda leg: leg.display_ordinal))
        keyed: list[tuple[str, int, ConfluenceLeg]] = []
        for leg in self.legs:
            fp = leg.content_fingerprint()
            if is_refusal(fp):
                return self.legs
            keyed.append((fp.value.value, leg.display_ordinal, leg))
        keyed.sort(key=lambda item: (item[0], item[1]))
        return tuple(item[2] for item in keyed)

    def identity_legs(self) -> tuple[dict[str, object], ...]:
        """Canonical identity-bearing leg mappings (ordinals only when order-significant)."""
        return tuple(leg.identity_for(self.ordering) for leg in self.canonical_legs())

    def body(self) -> dict[str, object]:
        """Kind-specific CT-06 payload — identity-bearing; ordinals omitted by default."""
        payload: dict[str, object] = {_LEGS_FIELD: list(self.identity_legs())}
        if self.order_significant:
            payload[_ORDER_FIELD] = self.ordering.value
        return payload

    def identity_payload(self) -> dict[str, object]:
        """Canonical semantic content for ``fp1``. SemVer and occurrence facts omitted."""
        return {
            "kind": KIND_CONFLUENCE,
            "contract_format_version": self.kind_format_version,
            "body": self.body(),
        }

    def fp1_identity(self) -> dict[str, object]:
        return self.identity_payload()

    def fingerprint_content(self) -> Result[Fingerprint]:
        """``fp1`` over the canonical leg set (+ order-significance when declared)."""
        return fingerprint(self.identity_payload())

    def producer_bindings(self) -> tuple[ProducerBinding, ...]:
        return tuple(leg.producer_binding for leg in self.legs if leg.producer_binding is not None)

    def child_refs(self) -> tuple[Fingerprint, ...]:
        return tuple(leg.confluence_ref for leg in self.legs if leg.confluence_ref is not None)

    def completeness_legs(self) -> tuple[dict[str, object], ...]:
        return tuple(leg.as_completeness_leg() for leg in self.legs)

    @classmethod
    def try_create(
        cls,
        legs: object,
        *,
        order_significance: object = None,
        format_version: object = CONFLUENCE_KIND_FORMAT_VERSION,
    ) -> Result[Confluence]:
        """Validate and build fingerprintable confluence content, value-or-refusal."""
        if isinstance(legs, cls):
            return Ok(legs)
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
        if version != CONFLUENCE_KIND_FORMAT_VERSION:
            return unsupported(
                "contract_format_version",
                "an uninterpretable confluence contract format version is an "
                "unsupported capability refusal, never a best-effort read",
                given=version,
                supported=CONFLUENCE_KIND_FORMAT_VERSION,
            )
        ordering = parse_ordering(order_significance)
        if is_refusal(ordering):
            return ordering
        resolved = _coerce_legs(legs)
        if is_refusal(resolved):
            return resolved
        return Ok(
            cls(
                legs=resolved.value,
                ordering=ordering.value,
                kind_format_version=version,
            )
        )

    @classmethod
    def try_from_mapping(cls, payload: object) -> Result[Confluence]:
        """Admit a CT-34 mapping (kind envelope, body, or a bare legs sequence)."""
        if isinstance(payload, cls):
            return Ok(payload)
        if isinstance(payload, (list, tuple)):
            return cls.try_create(cast("object", payload))
        if not isinstance(payload, Mapping):
            return invalid(
                "confluence",
                "a confluence is a mapping of legs plus optional order-significance",
                given=type(payload).__name__,
            )
        mapping = cast("Mapping[str, object]", payload)
        nested = mapping.get("body")
        if isinstance(nested, Mapping) and _LEGS_FIELD not in mapping:
            mapping = cast("Mapping[str, object]", nested)
        blocked = _condition_refusal("confluence", tuple(mapping))
        if is_refusal(blocked):
            return blocked
        version = mapping.get("contract_format_version", mapping.get("format_version"))
        if version is None:
            version = CONFLUENCE_KIND_FORMAT_VERSION
        if _LEGS_FIELD not in mapping:
            return invalid(
                _LEGS_FIELD,
                "a confluence carries one-or-more legs; a zero-leg confluence is invalid input",
            )
        return cls.try_create(
            mapping.get(_LEGS_FIELD),
            order_significance=mapping.get(_ORDER_FIELD, mapping.get("ordering")),
            format_version=version,
        )

    @classmethod
    def try_from_body(cls, body: object) -> Result[Confluence]:
        """Admit a CT-06 confluence body."""
        return cls.try_from_mapping(body)


def _coerce_legs(value: object) -> Result[tuple[ConfluenceLeg, ...]]:
    items = _as_sequence(value, _LEGS_FIELD)
    if is_refusal(items):
        return invalid(
            _LEGS_FIELD,
            "a confluence carries a sequence of one-or-more legs of any role mix; "
            "leg and component counts are never bounded",
            given=type(value).__name__,
        )
    resolved: list[ConfluenceLeg] = []
    seen_ordinals: set[int] = set()
    for index, item in enumerate(items.value):
        leg = ConfluenceLeg.try_create(item, index=index)
        if is_refusal(leg):
            return leg
        ordinal = leg.value.display_ordinal
        if ordinal in seen_ordinals:
            return invalid(
                "display_ordinal",
                "display ordinals are unique within a confluence",
                display_ordinal=ordinal,
                index=index,
            )
        seen_ordinals.add(ordinal)
        resolved.append(leg.value)
    if not resolved:
        return invalid(
            _LEGS_FIELD,
            "a confluence carries one-or-more legs of any role mix; a zero-leg "
            "confluence is invalid input",
        )
    return Ok(tuple(resolved))


def mint_confluence(
    legs: object,
    *,
    order_significance: object = None,
    format_version: object = CONFLUENCE_KIND_FORMAT_VERSION,
) -> Result[Confluence]:
    """Mint fingerprintable CT-34 confluence content (DEC-0175).

    The dated CT-06 envelope is stamped by a host composition root via
    :func:`register_confluence`. This helper never invents a WriterId, sequence,
    or created-at. Reuse of the same content never mints a new fingerprint.
    """
    if isinstance(legs, Mapping) and _LEGS_FIELD in cast("Mapping[str, object]", legs):
        mapping = cast("Mapping[str, object]", legs)
        return Confluence.try_from_mapping(
            {
                **dict(mapping),
                **({_ORDER_FIELD: order_significance} if order_significance is not None else {}),
                "contract_format_version": format_version,
            }
        )
    return Confluence.try_create(
        cast("object", legs),
        order_significance=order_significance,
        format_version=format_version,
    )


def confluence_kind_contract() -> Result[FieldSetKind]:
    """The CT-06 ``confluence`` kind contract — body field names only (DEC-0175)."""
    return FieldSetKind.try_create(
        KIND_CONFLUENCE,
        CONFLUENCE_KIND_FORMAT_VERSION,
        required_fields=(_LEGS_FIELD,),
        optional_fields=(_ORDER_FIELD,),
    )


def install_confluence_kind(registry: object) -> Result[FieldSetKind]:
    """Register the confluence kind on a host :class:`KindRegistry`."""
    if not isinstance(registry, KindRegistry):
        return invalid(
            "registry",
            "the confluence kind installs on a CT-06 KindRegistry",
            given=type(registry).__name__,
        )
    contract = confluence_kind_contract()
    if is_refusal(contract):
        return contract
    installed = registry.register(contract.value)
    if is_refusal(installed):
        return installed
    return Ok(contract.value)


def register_confluence(
    legs: object,
    *,
    registrar: object,
    writer: object,
    sequence: object,
    created_at: object,
    order_significance: object = None,
    at_birth_parent_refs: object = (),
) -> Result[RegistrationReceipt]:
    """Stamp fingerprintable confluence content onto a host CT-06 :class:`Registrar`.

    The host supplies writer, sequence, and created-at (AD-25 root-mints). The
    kind must already be installed on the registrar's :class:`KindRegistry`.
    """
    if not isinstance(registrar, Registrar):
        return invalid(
            "registrar",
            "a host composition root stamps the dated CT-06 record through a Registrar",
            given=type(registrar).__name__,
        )
    content = mint_confluence(legs, order_significance=order_significance)
    if is_refusal(content):
        return content
    return registrar.register(
        kind=KIND_CONFLUENCE,
        body=content.value.body(),
        writer=writer,
        sequence=sequence,
        created_at=created_at,
        at_birth_parent_refs=at_birth_parent_refs,
    )


def resolve_confluence_at_layer1(
    reference: object,
    catalog: object,
    *,
    producer_catalog: object = (),
) -> Result[Confluence]:
    """Resolve a cited confluence and its producer / child cites (QL-8 / DEC-0175).

    An unresolvable producer fingerprint or cited child confluence is
    ``unavailable dependency``, never a silent pass. Malformed structure stays
    ``invalid input``. The catalogs are host-supplied in-memory evidence.
    """
    wanted = _coerce_reference(reference)
    if is_refusal(wanted):
        return wanted
    checked = _require_catalog(catalog, "catalog")
    if is_refusal(checked):
        return checked
    producers = _producer_keys(producer_catalog)
    if is_refusal(producers):
        return producers
    resolved = wanted.value
    if isinstance(resolved, Fingerprint):
        found = _lookup_confluence(resolved, catalog)
        if is_refusal(found):
            return found
        target = found.value
    else:
        target = resolved
    walked = _walk_dependencies(target, catalog, producers.value, visiting=set())
    if is_refusal(walked):
        return walked
    return Ok(target)


def _coerce_reference(reference: object) -> Result[Confluence | Fingerprint]:
    if isinstance(reference, Confluence):
        found: Confluence | Fingerprint = reference
        return Ok(found)
    if isinstance(reference, Fingerprint):
        found = reference
        return Ok(found)
    parsed = Fingerprint.try_create(reference)
    if is_ok(parsed):
        found = parsed.value
        return Ok(found)
    if isinstance(reference, (Mapping, list, tuple)):
        built = Confluence.try_from_mapping(cast("object", reference))
        if is_ok(built):
            found = built.value
            return Ok(found)
        return built
    return invalid(
        "confluence_ref",
        "a confluence cite is a CT-34 fingerprint (fp1:sha256:<hex>) or confluence content",
        given=repr(type(reference).__name__),
    )


def _require_catalog(catalog: object, field: str) -> Result[None]:
    if isinstance(catalog, Mapping):
        return Ok(None)
    if isinstance(catalog, Sequence) and not isinstance(catalog, (str, bytes)):
        return Ok(None)
    return invalid(
        field,
        "Layer 1 resolves against an as-of catalog of confluence records or producer fingerprints",
        given=type(catalog).__name__,
    )


def _iter_catalog(catalog: object, field: str) -> Result[tuple[object, ...]]:
    required = _require_catalog(catalog, field)
    if is_refusal(required):
        return required
    if isinstance(catalog, Mapping):
        mapping = cast("Mapping[object, object]", catalog)
        return Ok(tuple(mapping.values()))
    return Ok(tuple(cast("Sequence[object]", catalog)))


def _extract_confluence(item: object) -> Result[Confluence] | None:
    if isinstance(item, Confluence):
        return Ok(item)
    if isinstance(item, RegistrationRecord):
        if item.kind != KIND_CONFLUENCE:
            return None
        return Confluence.try_from_body(item.body)
    if isinstance(item, Mapping):
        mapping = cast("Mapping[str, object]", item)
        kind = mapping.get("kind")
        if kind is not None and kind != KIND_CONFLUENCE:
            return None
        body = mapping.get("body")
        if isinstance(body, Mapping) and (
            _LEGS_FIELD in body or _LEGS_FIELD in mapping or kind == KIND_CONFLUENCE
        ):
            source: Mapping[str, object] = (
                mapping if _LEGS_FIELD in mapping else cast("Mapping[str, object]", body)
            )
            return Confluence.try_from_mapping(source)
        if _LEGS_FIELD in mapping:
            return Confluence.try_from_mapping(mapping)
        return None
    return None


def _lookup_confluence(wanted: Fingerprint, catalog: object) -> Result[Confluence]:
    token = wanted.value
    if isinstance(catalog, Mapping):
        mapping = cast("Mapping[object, object]", catalog)
        if token in mapping:
            extracted = _extract_confluence(mapping[token])
            if extracted is None:
                return unavailable(
                    "confluence_ref",
                    "an unresolvable cited child confluence is an unavailable dependency",
                    confluence_id=token,
                    journal=True,
                )
            return extracted
        items: Sequence[object] = tuple(mapping.values())
    elif isinstance(catalog, Sequence) and not isinstance(catalog, (str, bytes)):
        items = cast("Sequence[object]", catalog)
    else:
        items = ()
    for item in items:
        extracted = _extract_confluence(item)
        if extracted is None:
            continue
        if is_refusal(extracted):
            return extracted
        fp = extracted.value.fingerprint_content()
        if is_refusal(fp):
            return fp
        if fp.value.value == token:
            return extracted
    return unavailable(
        "confluence_ref",
        "an unresolvable cited child confluence is an unavailable dependency",
        confluence_id=token,
        journal=True,
    )


def _producer_keys(catalog: object) -> Result[frozenset[str]]:
    if catalog is None:
        return Ok(frozenset())
    if isinstance(catalog, Mapping):
        mapping = cast("Mapping[object, object]", catalog)
        keys: list[object] = []
        for key, value in mapping.items():
            keys.append(key)
            keys.append(value)
        return _collect_producer_keys(keys)
    items = _iter_catalog(catalog, "producer_catalog")
    if is_refusal(items):
        return items
    return _collect_producer_keys(items.value)


def _collect_producer_keys(items: Sequence[object]) -> Result[frozenset[str]]:
    found: set[str] = set()
    for item in items:
        if isinstance(item, Fingerprint):
            found.add(item.value)
            continue
        if isinstance(item, str):
            parsed = Fingerprint.try_create(item)
            if is_ok(parsed):
                found.add(parsed.value.value)
            continue
        if isinstance(item, ProducerBinding):
            if item.form is ProducerBindingForm.PINNED_FINGERPRINT and item.pinned is not None:
                found.add(item.pinned.value)
            else:
                fp = item.fingerprint_content()
                if is_refusal(fp):
                    return fp
                found.add(fp.value.value)
            continue
        if isinstance(item, Mapping):
            mapping = cast("Mapping[str, object]", item)
            raw = mapping.get("fingerprint", mapping.get("fp1"))
            if raw is not None:
                parsed = coerce_fingerprint(raw)
                if is_ok(parsed):
                    found.add(parsed.value.value)
    return Ok(frozenset(found))


def _walk_dependencies(
    confluence: Confluence,
    catalog: object,
    producer_keys: frozenset[str],
    visiting: set[str],
) -> Result[None]:
    for index, leg in enumerate(confluence.legs):
        if leg.producer_binding is not None:
            binding = leg.producer_binding
            if binding.form is ProducerBindingForm.PINNED_FINGERPRINT:
                pinned = binding.pinned
                if pinned is None or pinned.value not in producer_keys:
                    return unavailable(
                        "producer_binding",
                        "an unresolvable producer fingerprint is an unavailable dependency",
                        fingerprint=None if pinned is None else pinned.value,
                        index=index,
                        journal=True,
                    )
        if leg.confluence_ref is None:
            continue
        token = leg.confluence_ref.value
        if token in visiting:
            return invalid(
                "confluence_ref",
                "confluence composition must be acyclic",
                confluence_id=token,
            )
        visiting.add(token)
        child = _lookup_confluence(leg.confluence_ref, catalog)
        if is_refusal(child):
            visiting.discard(token)
            return child
        walked = _walk_dependencies(child.value, catalog, producer_keys, visiting)
        visiting.discard(token)
        if is_refusal(walked):
            return walked
    return Ok(None)
