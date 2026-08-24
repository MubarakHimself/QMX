"""Layer 1 declaration linter — machine checks at registration (QL-8).

Pure: catalogs are host-supplied in-memory evidence. The linter performs no I/O,
spawns no process, and never swallows a failure. Refusals are AD-11 typed values
(`invalid input | unsupported capability | unavailable dependency`) carrying
``layer=1`` and ``journal=True`` so a host can journal them (DEC-0178).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal
from qmf.registry import RegistrationRecord

from qml._refuse import clean_token, invalid, unavailable, unsupported
from qml.conformance.contract import CONFORMANCE_FORMAT_VERSION
from qml.declaration import (
    BOT_DEFINITION_KIND_FORMAT_VERSION,
    KIND_CONFLUENCE,
    PERMITTED_EXIT_INTENT_VOCABULARY,
    BotDefinition,
    Confluence,
    mint_bot_definition,
    resolve_confluence_at_layer1,
)
from qml.families import resolve_family_at_layer1
from qml.footprint import (
    AD22_IDENTITY_FIELDS,
    ProducerBinding,
    ProducerBindingForm,
    ProducerTemplate,
    compute_transitive_union,
    report_completeness,
)
from qml.logic import resolve_logic_at_layer1
from qml.protocol.factory import resolve_assignment

__all__ = [
    "LAYER1_CHECKS",
    "Layer1Verdict",
    "lint_declaration",
]

LAYER1_CHECKS: Final[tuple[str, ...]] = (
    "schema_completeness",
    "unit_kinded_canonical_assignment",
    "resolvable_references",
    "footprint_transitive_union",
    "producer_template_completeness",
    "permitted_exit_intents",
)

_LAYER: Final[int] = 1


def _journal(refusal: TypedRefusal) -> TypedRefusal:
    """Stamp Layer-1 journal markers; never drop the original category or field."""
    extra: dict[str, object] = dict(refusal.context)
    extra["journal"] = True
    extra.setdefault("layer", _LAYER)
    return TypedRefusal(
        category=refusal.category,
        retryability=refusal.retryability,
        context=extra,
        after_condition_descriptor=refusal.after_condition_descriptor,
    )


@dataclass(frozen=True, slots=True)
class Layer1Verdict:
    """Proof that the declaration passed every Layer-1 check (DEC-0178).

    Carries the linted Bot definition's ``fp1`` so a later ticket or seat can
    bind to the exact content linted, never a superseded one.
    """

    declaration: BotDefinition
    fingerprint: Fingerprint
    checks: tuple[str, ...] = LAYER1_CHECKS

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity of the Layer-1 proof. Package SemVer never enters."""
        return {
            "class": "qml-layer1-verdict",
            "contract_format_version": CONFORMANCE_FORMAT_VERSION,
            "declaration_fingerprint": self.fingerprint.value,
            "checks": list(self.checks),
        }


def lint_declaration(
    declaration: object,
    *,
    family_catalog: object = (),
    confluence_catalog: object = (),
    producer_catalog: object = (),
    formula_catalog: object = (),
    logic_catalog: object = (),
) -> Result[Layer1Verdict]:
    """Run the Layer-1 declaration linter at registration (QL-8, DEC-0178).

    Checks, in order: schema completeness against the declared format version;
    every parameter unit-kinded with a valid canonical assignment; every
    reference resolvable (family record, confluence fingerprints, producer
    formulas at their declared format versions, logic distribution); footprint
    transitive-union completeness (Epic 11 ``footprint/`` machinery); producer
    template completeness; permitted EXIT-intent kinds within
    ``close_full | tighten_protective_stop``. An unknown contract format
    version is ``unsupported capability``, never a best-effort read.
    """
    version = _peek_format_version(declaration)
    if is_refusal(version):
        return _journal(version)
    bot = _admit_declaration(declaration)
    if is_refusal(bot):
        return _journal(bot)
    content = bot.value
    intents = _check_exit_intents(content)
    if is_refusal(intents):
        return intents
    assignment = _check_canonical_assignment(content)
    if is_refusal(assignment):
        return assignment
    family = resolve_family_at_layer1(content.strategy_family_id.value, family_catalog)
    if is_refusal(family):
        return _journal(family)
    cited = _resolve_cited_confluences(content, confluence_catalog, producer_catalog)
    if is_refusal(cited):
        return cited
    formulas = _formula_index(formula_catalog)
    if is_refusal(formulas):
        return _journal(formulas)
    pinned = _pinned_keys(producer_catalog)
    if is_refusal(pinned):
        return _journal(pinned)
    templates = _check_producer_references(
        content,
        cited.value,
        confluence_catalog,
        pinned.value,
        formulas.value,
    )
    if is_refusal(templates):
        return templates
    logic = resolve_logic_at_layer1(content.logic_reference, logic_catalog)
    if is_refusal(logic):
        return _journal(logic)
    complete = _check_footprint_completeness(content, cited.value, confluence_catalog)
    if is_refusal(complete):
        return complete
    fingerprint = content.fingerprint_content()
    if is_refusal(fingerprint):
        return _journal(fingerprint)
    return Ok(
        Layer1Verdict(
            declaration=content,
            fingerprint=fingerprint.value,
            checks=LAYER1_CHECKS,
        )
    )


def _admit_declaration(declaration: object) -> Result[BotDefinition]:
    if isinstance(declaration, BotDefinition):
        return Ok(declaration)
    minted = mint_bot_definition(declaration)
    if is_refusal(minted):
        promoted = _promote_template_identity_refusal(minted)
        if promoted is not minted:
            return promoted
        return minted
    return minted


def _promote_template_identity_refusal(refusal: TypedRefusal) -> TypedRefusal:
    """Surface an omitted AD-22 identity field even when wrapped by a parent mapping."""
    field = _nested_template_field(refusal.context)
    if field is None:
        return refusal
    return invalid(
        field,
        "a producer template is a complete CT-16/CT-17 configuration minus only the "
        "space-bound parameter values; an omitted AD-22 identity field is a Layer-1 "
        "registration refusal (a missing element is a contract defect)",
        layer=_LAYER,
        journal=True,
    )


def _nested_template_field(context: Mapping[str, object]) -> str | None:
    field = context.get("field")
    if isinstance(field, str) and field in AD22_IDENTITY_FIELDS:
        return field
    cause = context.get("cause")
    if isinstance(cause, Mapping):
        return _nested_template_field(cast("Mapping[str, object]", cause))
    return None


def _peek_format_version(declaration: object) -> Result[int]:
    """Admit the declared format version before any best-effort field read."""
    if isinstance(declaration, BotDefinition):
        return _admit_format_version(declaration.kind_format_version)
    if not isinstance(declaration, Mapping):
        return Ok(BOT_DEFINITION_KIND_FORMAT_VERSION)
    mapping = cast("Mapping[str, object]", declaration)
    version = mapping.get("contract_format_version", mapping.get("format_version"))
    nested = mapping.get("body")
    if version is None and isinstance(nested, Mapping):
        body = cast("Mapping[str, object]", nested)
        version = body.get("contract_format_version", body.get("format_version"))
    if version is None:
        return Ok(BOT_DEFINITION_KIND_FORMAT_VERSION)
    return _admit_format_version(version)


def _admit_format_version(value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(
            "format_version",
            "a kind format version is a positive integer; package SemVer never enters",
            given=repr(value),
            layer=_LAYER,
            journal=True,
        )
    if value < 1:
        return invalid(
            "format_version",
            "a kind format version is a positive integer ordinal",
            given=repr(value),
            layer=_LAYER,
            journal=True,
        )
    if value != BOT_DEFINITION_KIND_FORMAT_VERSION:
        return unsupported(
            "contract_format_version",
            "an uninterpretable Bot definition contract format version is an "
            "unsupported capability refusal, never a best-effort read",
            given=value,
            supported=BOT_DEFINITION_KIND_FORMAT_VERSION,
            layer=_LAYER,
            journal=True,
        )
    return Ok(value)


def _check_exit_intents(bot: BotDefinition) -> Result[None]:
    """Permitted EXIT kinds are a (possibly empty) subset of the CT-23 vocabulary."""
    for kind in bot.permitted_exit_intents:
        if kind == "entry":
            return _journal(
                invalid(
                    "permitted_exit_intents",
                    "entry is always permitted and is never declared here; the "
                    "declaration names only permitted EXIT-intent kinds",
                    given=kind,
                    layer=_LAYER,
                    journal=True,
                )
            )
        if kind not in PERMITTED_EXIT_INTENT_VOCABULARY:
            return _journal(
                invalid(
                    "permitted_exit_intents",
                    "permitted EXIT-intent kinds must lie within the ratified CT-23 "
                    "vocabulary (close_full | tighten_protective_stop)",
                    given=kind,
                    allowed=sorted(PERMITTED_EXIT_INTENT_VOCABULARY),
                    layer=_LAYER,
                    journal=True,
                )
            )
    return Ok(None)


def _check_canonical_assignment(bot: BotDefinition) -> Result[None]:
    """Every parameter is unit-kinded; defaults together are a valid assignment."""
    for spec in bot.parameter_space:
        if spec.default is None:
            return _journal(
                invalid(
                    "default",
                    "every declared parameter carries a mandatory default; defaults "
                    "together are the canonical assignment",
                    name=spec.name,
                    layer=_LAYER,
                    journal=True,
                )
            )
    checked = resolve_assignment(bot, bot.canonical_assignment())
    if is_refusal(checked):
        return _journal(checked)
    return Ok(None)


def _resolve_cited_confluences(
    bot: BotDefinition,
    confluence_catalog: object,
    producer_catalog: object,
) -> Result[tuple[Confluence, ...]]:
    resolved: list[Confluence] = []
    for cite in bot.confluence_set:
        found = resolve_confluence_at_layer1(
            cite.fingerprint,
            confluence_catalog,
            producer_catalog=producer_catalog,
        )
        if is_refusal(found):
            return _journal(found)
        resolved.append(found.value)
    return Ok(tuple(resolved))


def _check_producer_references(
    bot: BotDefinition,
    cited: Sequence[Confluence],
    confluence_catalog: object,
    pinned_keys: frozenset[str],
    formulas: Mapping[str, frozenset[int]],
) -> Result[None]:
    """Pinned fingerprints and template formulas must resolve; templates complete."""
    catalog = _leg_catalog(confluence_catalog)
    if is_refusal(catalog):
        return catalog
    legs: list[object] = []
    for confluence in cited:
        legs.extend(confluence.completeness_legs())
    union = compute_transitive_union(legs, bot_direct=(), catalog=catalog.value)
    if is_refusal(union):
        return _journal(union)
    seen: set[str] = set()
    bindings: list[ProducerBinding] = []
    for binding in (*bot.footprint.producer_bindings, *union.value):
        key = _binding_key(binding)
        if is_refusal(key):
            return _journal(key)
        if key.value in seen:
            continue
        seen.add(key.value)
        bindings.append(binding)
    for binding in bindings:
        checked = _check_one_binding(binding, pinned_keys, formulas)
        if is_refusal(checked):
            return checked
    return Ok(None)


def _check_one_binding(
    binding: ProducerBinding,
    pinned_keys: frozenset[str],
    formulas: Mapping[str, frozenset[int]],
) -> Result[None]:
    if binding.form is ProducerBindingForm.PINNED_FINGERPRINT:
        pinned = binding.pinned
        if pinned is None or pinned.value not in pinned_keys:
            return _journal(
                unavailable(
                    "producer_binding",
                    "an unresolvable producer fingerprint is an unavailable dependency",
                    fingerprint=None if pinned is None else pinned.value,
                    journal=True,
                    layer=_LAYER,
                )
            )
        return Ok(None)
    template = binding.template
    if template is None:
        return _journal(
            invalid(
                "producer_binding",
                "a template binding must carry a complete producer template",
                layer=_LAYER,
                journal=True,
            )
        )
    complete = _template_identity_complete(template)
    if is_refusal(complete):
        return complete
    return _resolve_formula(template.formula_id, template.contract_format_version, formulas)


def _template_identity_complete(template: ProducerTemplate) -> Result[None]:
    identity = template.fp1_identity()
    missing = [name for name in AD22_IDENTITY_FIELDS if name not in identity]
    if missing:
        return _journal(
            invalid(
                missing[0],
                "a producer template is a complete CT-16/CT-17 configuration minus "
                "only the space-bound parameter values; an omitted AD-22 identity "
                "field is a Layer-1 registration refusal (a missing element is a "
                "contract defect)",
                layer=_LAYER,
                journal=True,
            )
        )
    return Ok(None)


def _resolve_formula(
    formula_id: str,
    format_version: int,
    formulas: Mapping[str, frozenset[int]],
) -> Result[None]:
    versions = formulas.get(formula_id)
    if versions is None:
        return _journal(
            unavailable(
                "formula_id",
                "the cited producer formula does not resolve at its declared format "
                "version; an unresolvable producer formula is an unavailable "
                "dependency, never a silent pass",
                formula_id=formula_id,
                contract_format_version=format_version,
                journal=True,
                layer=_LAYER,
            )
        )
    if format_version not in versions:
        return _journal(
            unavailable(
                "formula_id",
                "the cited producer formula does not resolve at its declared format "
                "version; an unresolvable producer formula is an unavailable "
                "dependency, never a silent pass",
                formula_id=formula_id,
                contract_format_version=format_version,
                available_format_versions=tuple(sorted(versions)),
                journal=True,
                layer=_LAYER,
            )
        )
    return Ok(None)


def _check_footprint_completeness(
    bot: BotDefinition,
    cited: Sequence[Confluence],
    confluence_catalog: object,
) -> Result[None]:
    """Footprint producer set equals confluence-leg union plus bot-direct producers."""
    catalog = _leg_catalog(confluence_catalog)
    if is_refusal(catalog):
        return catalog
    legs: list[object] = []
    for confluence in cited:
        legs.extend(confluence.completeness_legs())
    union = compute_transitive_union(legs, bot_direct=(), catalog=catalog.value)
    if is_refusal(union):
        return _journal(union)
    union_keys: set[str] = set()
    for binding in union.value:
        key = _binding_key(binding)
        if is_refusal(key):
            return _journal(key)
        union_keys.add(key.value)
    bot_direct: list[ProducerBinding] = []
    for binding in bot.footprint.producer_bindings:
        key = _binding_key(binding)
        if is_refusal(key):
            return _journal(key)
        if key.value not in union_keys:
            bot_direct.append(binding)
    report = report_completeness(
        bot.footprint,
        legs,
        bot_direct=bot_direct,
        catalog=catalog.value,
    )
    if is_refusal(report):
        return _journal(report)
    if report.value.complete:
        return Ok(None)
    return _journal(
        invalid(
            "footprint",
            "the footprint's producer-binding set must equal the transitive union of "
            "every cited confluence's leg producers plus bot-direct producers; a "
            "confluence-leg producer absent from the footprint is a Layer-1 "
            "registration refusal",
            missing=report.value.missing,
            extra=report.value.extra,
            layer=_LAYER,
            journal=True,
        )
    )


def _binding_key(binding: ProducerBinding) -> Result[str]:
    fp = binding.fingerprint_content()
    if is_refusal(fp):
        return fp
    return Ok(fp.value.value)


def _iter_catalog(catalog: object, field: str) -> Result[tuple[object, ...]]:
    if isinstance(catalog, Mapping):
        return Ok(tuple(cast("Mapping[object, object]", catalog).values()))
    if isinstance(catalog, Sequence) and not isinstance(catalog, (str, bytes)):
        return Ok(tuple(cast("Sequence[object]", catalog)))
    return invalid(
        field,
        "Layer 1 resolves against an as-of catalog of in-memory records",
        given=type(catalog).__name__,
        layer=_LAYER,
        journal=True,
    )


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
        if isinstance(body, Mapping) and "legs" in body:
            source: Mapping[str, object] = (
                mapping if "legs" in mapping else cast("Mapping[str, object]", body)
            )
            return Confluence.try_from_mapping(source)
        if "legs" in mapping:
            return Confluence.try_from_mapping(mapping)
        return None
    return None


def _leg_catalog(catalog: object) -> Result[dict[str, tuple[object, ...]]]:
    items = _iter_catalog(catalog, "confluence_catalog")
    if is_refusal(items):
        return items
    found: dict[str, tuple[object, ...]] = {}
    if isinstance(catalog, Mapping):
        mapping = cast("Mapping[object, object]", catalog)
        for key, value in mapping.items():
            extracted = _extract_confluence(value)
            if extracted is None or is_refusal(extracted):
                continue
            legs = extracted.value.completeness_legs()
            if isinstance(key, str):
                found[key] = legs
            fp = extracted.value.fingerprint_content()
            if is_ok(fp):
                found[fp.value.value] = legs
    for item in items.value:
        extracted = _extract_confluence(item)
        if extracted is None or is_refusal(extracted):
            continue
        fp = extracted.value.fingerprint_content()
        if is_refusal(fp):
            return _journal(fp)
        found[fp.value.value] = extracted.value.completeness_legs()
    return Ok(found)


def _pinned_keys(catalog: object) -> Result[frozenset[str]]:
    if catalog is None:
        return Ok(frozenset())
    if isinstance(catalog, Mapping):
        mapping = cast("Mapping[object, object]", catalog)
        scanned: list[object] = []
        for key, value in mapping.items():
            scanned.append(key)
            scanned.append(value)
        return _collect_pinned(scanned)
    items = _iter_catalog(catalog, "producer_catalog")
    if is_refusal(items):
        return items
    return _collect_pinned(items.value)


def _collect_pinned(items: Sequence[object]) -> Result[frozenset[str]]:
    found: set[str] = set()
    for item in items:
        if isinstance(item, Fingerprint):
            found.add(item.value)
            continue
        if isinstance(item, ProducerBinding):
            if item.form is ProducerBindingForm.PINNED_FINGERPRINT and item.pinned is not None:
                found.add(item.pinned.value)
            continue
        if isinstance(item, str):
            parsed = Fingerprint.try_create(item)
            if is_ok(parsed):
                found.add(parsed.value.value)
            continue
        if isinstance(item, Mapping):
            mapping = cast("Mapping[str, object]", item)
            raw = mapping.get("fingerprint", mapping.get("fp1"))
            if raw is None:
                continue
            parsed = Fingerprint.try_create(raw) if not isinstance(raw, Fingerprint) else Ok(raw)
            if is_ok(parsed):
                found.add(parsed.value.value)
    return Ok(frozenset(found))


def _formula_index(catalog: object) -> Result[dict[str, frozenset[int]]]:
    collected: dict[str, set[int]] = {}
    if catalog is None:
        return Ok({})
    if isinstance(catalog, Mapping):
        mapping = cast("Mapping[object, object]", catalog)
        if "formula_id" in mapping:
            added = _add_formula_record(collected, mapping)
            if is_refusal(added):
                return added
            return Ok({name: frozenset(versions) for name, versions in collected.items()})
        for key, value in mapping.items():
            added = _add_formula_entry(collected, key, value)
            if is_refusal(added):
                return added
        return Ok({name: frozenset(versions) for name, versions in collected.items()})
    items = _iter_catalog(catalog, "formula_catalog")
    if is_refusal(items):
        return items
    for item in items.value:
        added = _add_formula_record(collected, item)
        if is_refusal(added):
            return added
    return Ok({name: frozenset(versions) for name, versions in collected.items()})


def _add_formula_entry(
    collected: dict[str, set[int]],
    key: object,
    value: object,
) -> Result[None]:
    name = clean_token(key)
    if name is None:
        return invalid(
            "formula_catalog",
            "a formula catalog maps a non-empty formula id onto a declared format version",
            key=repr(key),
            layer=_LAYER,
            journal=True,
        )
    versions = _coerce_versions(value)
    if is_refusal(versions):
        return versions
    collected.setdefault(name, set()).update(versions.value)
    return Ok(None)


def _add_formula_record(collected: dict[str, set[int]], item: object) -> Result[None]:
    if isinstance(item, ProducerTemplate):
        collected.setdefault(item.formula_id, set()).add(item.contract_format_version)
        return Ok(None)
    if isinstance(item, ProducerBinding) and item.template is not None:
        template = item.template
        collected.setdefault(template.formula_id, set()).add(template.contract_format_version)
        return Ok(None)
    if isinstance(item, Mapping):
        mapping = cast("Mapping[str, object]", item)
        name = clean_token(mapping.get("formula_id"))
        if name is None:
            return invalid(
                "formula_catalog",
                "a formula catalog record names a non-empty formula_id",
                given=repr(mapping.get("formula_id")),
                layer=_LAYER,
                journal=True,
            )
        raw_version = mapping.get(
            "contract_format_version", mapping.get("format_version", mapping.get("version"))
        )
        version = _positive_int(raw_version)
        if version is None:
            return invalid(
                "formula_catalog",
                "a producer formula declares a positive integer contract format version",
                formula_id=name,
                given=repr(raw_version),
                layer=_LAYER,
                journal=True,
            )
        collected.setdefault(name, set()).add(version)
        return Ok(None)
    if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
        pair = tuple(cast("Sequence[object]", item))
        if len(pair) == 2:
            return _add_formula_entry(collected, pair[0], pair[1])
    return invalid(
        "formula_catalog",
        "each formula catalog entry is a formula_id plus a declared format version",
        given=type(cast("object", item)).__name__,
        layer=_LAYER,
        journal=True,
    )


def _coerce_versions(value: object) -> Result[frozenset[int]]:
    if isinstance(value, ProducerTemplate):
        return Ok(frozenset({value.contract_format_version}))
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        raw = mapping.get("contract_format_version", mapping.get("format_version"))
        version = _positive_int(raw)
        if version is None:
            return invalid(
                "formula_catalog",
                "a producer formula declares a positive integer contract format version",
                given=repr(raw),
                layer=_LAYER,
                journal=True,
            )
        return Ok(frozenset({version}))
    if isinstance(value, bool) or not isinstance(value, int):
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            found: set[int] = set()
            for item in cast("Sequence[object]", value):
                version = _positive_int(item)
                if version is None:
                    return invalid(
                        "formula_catalog",
                        "formula format versions are positive integer ordinals",
                        given=repr(item),
                        layer=_LAYER,
                        journal=True,
                    )
                found.add(version)
            if not found:
                return invalid(
                    "formula_catalog",
                    "a formula catalog entry declares one or more format versions",
                    layer=_LAYER,
                    journal=True,
                )
            return Ok(frozenset(found))
        return invalid(
            "formula_catalog",
            "a producer formula declares a positive integer contract format version",
            given=repr(value),
            layer=_LAYER,
            journal=True,
        )
    if value < 1:
        return invalid(
            "formula_catalog",
            "a producer formula declares a positive integer contract format version",
            given=repr(value),
            layer=_LAYER,
            journal=True,
        )
    return Ok(frozenset({value}))


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value
