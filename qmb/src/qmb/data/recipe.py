"""RecipeDefinition identity is not the output release fp1 (Story 58.3).

DEC-0425 / DEC-0444 / AD-31: authored identity is
``(recipe_def_id, recipe_def_version, recipe_def_hash)`` and is reviewable
before a run. A run produces a new output **release fp1** with CT-07 lineage.
Two runs of one definition are two releases, not two recipes. Display
``recipe_id`` is not identity. Provider ≠ venue. Preview ≠ export ≠ stream.
Non-trading outputs need no CT-33 / Book / QMN wrap. CT-06 recipe kind stays
deferred. Not a Library kind. COMP-QMB wraps COMP-QMF-DATA.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import WriterId
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal
from qmf.registry import EdgeType, LineageEdge

from qmb._refuse import clean_token, invalid, policy, unsupported

__all__ = [
    "INPUT_REQUIRED_FIELDS",
    "RECIPE_CT06_KIND_DEFERRED",
    "RECIPE_DEFINITION_CLASS",
    "RECIPE_DEF_HASH_FIELDS",
    "RECIPE_DEF_IDENTITY_FIELDS",
    "RECIPE_DELIVERY_MODES",
    "RECIPE_IS_LIBRARY_KIND",
    "RECIPE_LINEAGE_BINDS",
    "RECIPE_LINEAGE_EDGE_TYPE",
    "RECIPE_OUTPUT_COMPLETENESS",
    "RECIPE_RELEASE_CLASS",
    "RECIPE_ROOM_MACHINERY",
    "RECIPE_WRAP_OWNER",
    "TRANSFORM_REQUIRED_FIELDS",
    "RecipeDefinition",
    "RecipeRelease",
    "hash_recipe_definition",
    "recipe_identity",
    "review_recipe_definition",
    "run_recipe_definition",
]

RECIPE_DEFINITION_CLASS: Final[str] = "qmb-recipe-definition"
RECIPE_RELEASE_CLASS: Final[str] = "qmb-recipe-release"
RECIPE_IS_LIBRARY_KIND: Final[bool] = False
RECIPE_CT06_KIND_DEFERRED: Final[bool] = True
RECIPE_WRAP_OWNER: Final[str] = "COMP-QMB"
RECIPE_ROOM_MACHINERY: Final[str] = "qmf-data"
RECIPE_LINEAGE_EDGE_TYPE: Final[EdgeType] = EdgeType.OCCURRENCE_OF
RECIPE_OUTPUT_COMPLETENESS: Final[tuple[str, ...]] = (
    "complete",
    "partial",
    "missing",
    "expired",
)
RECIPE_DELIVERY_MODES: Final[tuple[str, ...]] = ("preview", "export", "stream")
RECIPE_DEF_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "recipe_def_id",
    "recipe_def_version",
    "recipe_def_hash",
)
RECIPE_DEF_HASH_FIELDS: Final[tuple[str, ...]] = (
    "recipe_def_id",
    "recipe_def_version",
    "inputs",
    "transforms",
    "split_policy",
    "environment_pin",
    "output_schema",
    "completeness_required",
)
RECIPE_LINEAGE_BINDS: Final[tuple[str, ...]] = (
    "recipe_def_id",
    "recipe_def_version",
    "recipe_def_hash",
    "input_revisions",
    "transform_pins",
    "environment_pin",
    "run_id",
    "completeness",
)
INPUT_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "kind",
    "provider",
    "coverage",
    "schema_roles",
    "units",
    "timezone",
    "calendar",
    "freshness",
    "provenance",
    "entitlement_ref",
    "licensing",
    "revision",
)
TRANSFORM_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "name",
    "alignment",
    "known_at_policy",
    "missing_policy",
    "late_policy",
    "adjustment",
)
_COVERAGE_FIELDS: Final[tuple[str, ...]] = ("start", "end", "resolution")
_FRESHNESS_FIELDS: Final[tuple[str, ...]] = ("max_lag", "as_of_policy")
_PROVENANCE_FIELDS: Final[tuple[str, ...]] = ("source_class", "lineage_kind")
_ENVIRONMENT_FIELDS: Final[tuple[str, ...]] = ("python", "code_fp1")
_SPLIT_REQUIRED: Final[tuple[str, ...]] = ("kind",)
_INPUT_OPTIONAL: Final[frozenset[str]] = frozenset({"venue", "instrument", "adjustment"})
_DISPLAY_FIELDS: Final[frozenset[str]] = frozenset(
    {"display_name", "display_recipe_id", "recipe_id"}
)
_SECRET_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "api_key",
        "credential",
        "credential_value",
        "password",
        "secret",
        "secret_value",
        "token_value",
    }
)
_WRAP_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "bms",
        "bms_fp1",
        "book",
        "book_fp1",
        "bot",
        "bot_fp1",
        "ct-33",
        "ct33",
        "qmn",
        "qmn_seat",
        "seat",
    }
)
_LIBRARY_FIELDS: Final[frozenset[str]] = frozenset({"library_kind", "register_library"})
_CT06_FIELDS: Final[frozenset[str]] = frozenset(
    {"ct-06", "ct06", "ct06_kind", "recipe_kind", "register_ct06"}
)
_PROVIDER_VENUE_FIELDS: Final[frozenset[str]] = frozenset(
    {"provider_as_venue", "provider_venue", "venue_as_provider"}
)

_CATALOGUE_REASON: Final[str] = (
    "RecipeDefinition carries the AD-31 catalogue (CONTRACTS §5): inputs with "
    "coverage/schema/roles/units/timezone/calendar/freshness/provenance/"
    "entitlement_ref/licensing/revision; transforms with alignment, "
    "known_at_policy, missing/late policy, adjustment; split_policy; "
    "environment_pin; output_schema; output_completeness_enumeration; "
    "completeness_required (DEC-0444)"
)
_HASH_REASON: Final[str] = (
    "recipe_def_hash is fp1 over (recipe_def_id, recipe_def_version, inputs[], "
    "transforms[], split_policy, environment_pin, output_schema, "
    "completeness_required) after canonical JSON; display rename and runtime "
    "credential values are excluded (DEC-0444)"
)
_WRAP_REASON: Final[str] = (
    "non-trading recipe outputs need no CT-33 / Book / QMN wrap (AD-11 class 3, DEC-0444)"
)
_CT06_REASON: Final[str] = (
    "CT-06 recipe kind remains deferred; RecipeDefinition is not a Library kind "
    "(DEC-0425, DEC-0444)"
)
_PROVIDER_VENUE_REASON: Final[str] = (
    "provider ≠ venue ≠ account ≠ instrument; they are never the same field (DEC-0425)"
)
_DELIVERY_REASON: Final[str] = (
    "preview ≠ export ≠ stream; a run names exactly one delivery mode (DEC-0444)"
)
_TWO_RECIPES_REASON: Final[str] = (
    "two runs of one definition are two releases, not two recipes; "
    "output release fp1 is not RecipeDefinition identity (DEC-0444)"
)


def recipe_identity() -> dict[str, object]:
    """Identity-bearing recipe schema. Package SemVer is omitted."""
    return {
        "recipe_ct06_kind_deferred": RECIPE_CT06_KIND_DEFERRED,
        "recipe_definition_class": RECIPE_DEFINITION_CLASS,
        "recipe_delivery_modes": RECIPE_DELIVERY_MODES,
        "recipe_hash_fields": RECIPE_DEF_HASH_FIELDS,
        "recipe_identity_fields": RECIPE_DEF_IDENTITY_FIELDS,
        "recipe_is_library_kind": RECIPE_IS_LIBRARY_KIND,
        "recipe_lineage_binds": RECIPE_LINEAGE_BINDS,
        "recipe_lineage_edge_type": RECIPE_LINEAGE_EDGE_TYPE.value,
        "recipe_output_completeness_enumeration": RECIPE_OUTPUT_COMPLETENESS,
        "recipe_release_class": RECIPE_RELEASE_CLASS,
        "recipe_room_machinery": RECIPE_ROOM_MACHINERY,
        "recipe_wrap_owner": RECIPE_WRAP_OWNER,
    }


@dataclass(frozen=True, slots=True)
class RecipeDefinition:
    """Authored recipe identity, reviewable before a run. Not a release fp1."""

    recipe_def_id: str
    recipe_def_version: int
    recipe_def_hash: Fingerprint
    inputs: tuple[Mapping[str, object], ...]
    transforms: tuple[Mapping[str, object], ...]
    split_policy: Mapping[str, object]
    environment_pin: Mapping[str, object]
    output_schema: str
    output_completeness_enumeration: tuple[str, ...]
    completeness_required: str
    display_recipe_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "inputs",
            tuple(_freeze_mapping(item) for item in self.inputs),
        )
        object.__setattr__(
            self,
            "transforms",
            tuple(_freeze_mapping(item) for item in self.transforms),
        )
        object.__setattr__(self, "split_policy", _freeze_mapping(self.split_policy))
        object.__setattr__(self, "environment_pin", _freeze_mapping(self.environment_pin))

    def identity(self) -> dict[str, object]:
        """``(recipe_def_id, recipe_def_version, recipe_def_hash)`` — not display."""
        return {
            "recipe_def_hash": self.recipe_def_hash.value,
            "recipe_def_id": self.recipe_def_id,
            "recipe_def_version": self.recipe_def_version,
        }

    def catalogue(self) -> dict[str, object]:
        """Full AD-31 definition body. Display rename is omitted from hash."""
        body: dict[str, object] = {
            "completeness_required": self.completeness_required,
            "environment_pin": _plain_mapping(self.environment_pin),
            "inputs": [_plain_mapping(item) for item in self.inputs],
            "output_completeness_enumeration": list(self.output_completeness_enumeration),
            "output_schema": self.output_schema,
            "recipe_def_hash": self.recipe_def_hash.value,
            "recipe_def_id": self.recipe_def_id,
            "recipe_def_version": self.recipe_def_version,
            "split_policy": _plain_mapping(self.split_policy),
            "transforms": [_plain_mapping(item) for item in self.transforms],
        }
        if self.display_recipe_id is not None:
            body["recipe_id"] = self.display_recipe_id
        return body

    def hash_preimage(self) -> dict[str, object]:
        """Canonical hash inputs. Display rename and credential values excluded."""
        return {
            "completeness_required": self.completeness_required,
            "environment_pin": _plain_mapping(self.environment_pin),
            "inputs": [_plain_mapping(item) for item in self.inputs],
            "output_schema": self.output_schema,
            "recipe_def_id": self.recipe_def_id,
            "recipe_def_version": self.recipe_def_version,
            "split_policy": _plain_mapping(self.split_policy),
            "transforms": [_plain_mapping(item) for item in self.transforms],
        }


@dataclass(frozen=True, slots=True)
class RecipeRelease:
    """Run result: a new output release fp1, never a second recipe identity."""

    output_release: Fingerprint
    recipe_def_id: str
    recipe_def_version: int
    recipe_def_hash: Fingerprint
    run_id: str
    input_revisions: tuple[Mapping[str, object], ...]
    transform_pins: tuple[Mapping[str, object], ...]
    environment_pin: Mapping[str, object]
    completeness: str
    delivery: str
    lineage: LineageEdge
    is_library_kind: bool = False
    wraps_ct33: bool = False
    wraps_book: bool = False
    wraps_qmn: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "input_revisions",
            tuple(_freeze_mapping(item) for item in self.input_revisions),
        )
        object.__setattr__(
            self,
            "transform_pins",
            tuple(_freeze_mapping(item) for item in self.transform_pins),
        )
        object.__setattr__(self, "environment_pin", _freeze_mapping(self.environment_pin))

    def fp1_identity(self) -> dict[str, object]:
        """Release identity. Distinct from RecipeDefinition identity."""
        return {
            "class": RECIPE_RELEASE_CLASS,
            "completeness": self.completeness,
            "delivery": self.delivery,
            "environment_pin": _plain_mapping(self.environment_pin),
            "input_revisions": [_plain_mapping(item) for item in self.input_revisions],
            "is_library_kind": False,
            "lineage_binds": list(RECIPE_LINEAGE_BINDS),
            "lineage_edge_type": self.lineage.edge_type.value,
            "output_release": self.output_release.value,
            "recipe_def_hash": self.recipe_def_hash.value,
            "recipe_def_id": self.recipe_def_id,
            "recipe_def_version": self.recipe_def_version,
            "run_id": self.run_id,
            "transform_pins": [_plain_mapping(item) for item in self.transform_pins],
            "wraps_book": False,
            "wraps_ct33": False,
            "wraps_qmn": False,
        }


def hash_recipe_definition(payload: object) -> Result[Fingerprint]:
    """fp1 over the AD-31 hash preimage after canonical JSON normalization."""
    reviewed = review_recipe_definition(payload)
    if is_refusal(reviewed):
        return reviewed
    return fingerprint(reviewed.value.hash_preimage())


def review_recipe_definition(payload: object) -> Result[RecipeDefinition]:
    """Review and pin a RecipeDefinition before a run."""
    if isinstance(payload, RecipeDefinition):
        return Ok(payload)
    if not isinstance(payload, Mapping):
        return invalid(
            "payload",
            "a RecipeDefinition is a key->value mapping",
            given=repr(type(payload).__name__),
        )
    body = cast("Mapping[str, object]", payload)
    blocked = _refuse_forbidden_payload(body)
    if blocked is not None:
        return blocked
    def_id = clean_token(body.get("recipe_def_id"))
    if def_id is None:
        return invalid("recipe_def_id", "RecipeDefinition identity includes recipe_def_id")
    version = _positive_int(body.get("recipe_def_version"), "recipe_def_version")
    if is_refusal(version):
        return version
    inputs = _parse_inputs(body.get("inputs"))
    if is_refusal(inputs):
        return inputs
    transforms = _parse_transforms(body.get("transforms"))
    if is_refusal(transforms):
        return transforms
    split = _parse_object_section(
        body.get("split_policy"),
        "split_policy",
        _SPLIT_REQUIRED,
        optional=frozenset({"split_ref"}),
    )
    if is_refusal(split):
        return split
    env = _parse_object_section(
        body.get("environment_pin"),
        "environment_pin",
        _ENVIRONMENT_FIELDS,
    )
    if is_refusal(env):
        return env
    schema = clean_token(body.get("output_schema"))
    if schema is None:
        return invalid("output_schema", _CATALOGUE_REASON)
    enumeration = _parse_completeness_enumeration(body.get("output_completeness_enumeration"))
    if is_refusal(enumeration):
        return enumeration
    required = clean_token(body.get("completeness_required"))
    if required is None or required not in RECIPE_OUTPUT_COMPLETENESS:
        return invalid(
            "completeness_required",
            "completeness_required is one of complete | partial | missing | expired",
            given=repr(body.get("completeness_required")),
        )
    display = _optional_display(body)
    if is_refusal(display):
        return display
    preimage = {
        "completeness_required": required,
        "environment_pin": env.value,
        "inputs": inputs.value,
        "output_schema": schema,
        "recipe_def_id": def_id,
        "recipe_def_version": version.value,
        "split_policy": split.value,
        "transforms": transforms.value,
    }
    hashed = fingerprint(preimage)
    if is_refusal(hashed):
        return hashed
    supplied = body.get("recipe_def_hash")
    if supplied is not None:
        parsed = _coerce_fingerprint(supplied)
        if parsed is None or parsed.value != hashed.value.value:
            return invalid("recipe_def_hash", _HASH_REASON, given=repr(supplied))
    return Ok(
        RecipeDefinition(
            recipe_def_id=def_id,
            recipe_def_version=version.value,
            recipe_def_hash=hashed.value,
            inputs=tuple(inputs.value),
            transforms=tuple(transforms.value),
            split_policy=split.value,
            environment_pin=env.value,
            output_schema=schema,
            output_completeness_enumeration=enumeration.value,
            completeness_required=required,
            display_recipe_id=display.value,
        )
    )


def run_recipe_definition(
    payload: object,
    *,
    run_id: object,
    writer: object,
    delivery: object = "export",
    wrap: object = None,
    register_ct06: object = False,
    library_kind: object = False,
) -> Result[RecipeRelease]:
    """Complete a run: new output release fp1 bound by CT-07 to the definition."""
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "a recipe release mints CT-07 lineage under a WriterId",
            given=repr(type(writer).__name__),
        )
    token = clean_token(run_id)
    if token is None:
        return invalid("run_id", "a recipe run records a non-empty run_id")
    mode = clean_token(delivery)
    if mode is None or mode not in RECIPE_DELIVERY_MODES:
        return invalid("delivery", _DELIVERY_REASON, given=repr(delivery))
    if register_ct06 is True or library_kind is True:
        return _refuse_ct06_or_library("register_ct06" if register_ct06 is True else "library_kind")
    wrap_hit = _refuse_wrap(wrap)
    if wrap_hit is not None:
        return wrap_hit
    reviewed = review_recipe_definition(payload)
    if is_refusal(reviewed):
        return reviewed
    definition = reviewed.value
    if isinstance(payload, Mapping):
        pretends = _refuse_release_as_recipe(cast("Mapping[str, object]", payload))
        if pretends is not None:
            return pretends
    revisions = tuple(_input_revision(item) for item in definition.inputs)
    pins = tuple(_transform_pin(item) for item in definition.transforms)
    release_identity = {
        "class": RECIPE_RELEASE_CLASS,
        "completeness": definition.completeness_required,
        "delivery": mode,
        "environment_pin": _plain_mapping(definition.environment_pin),
        "input_revisions": [_plain_mapping(item) for item in revisions],
        "recipe_def_hash": definition.recipe_def_hash.value,
        "recipe_def_id": definition.recipe_def_id,
        "recipe_def_version": definition.recipe_def_version,
        "run_id": token,
        "transform_pins": [_plain_mapping(item) for item in pins],
    }
    stamped = fingerprint(release_identity)
    if is_refusal(stamped):
        return stamped
    if stamped.value.value == definition.recipe_def_hash.value:
        return invalid("output_release", _TWO_RECIPES_REASON)
    lineage = LineageEdge.try_create(
        RECIPE_LINEAGE_EDGE_TYPE,
        stamped.value,
        definition.recipe_def_hash,
        writer,
    )
    if is_refusal(lineage):
        return lineage
    return Ok(
        RecipeRelease(
            output_release=stamped.value,
            recipe_def_id=definition.recipe_def_id,
            recipe_def_version=definition.recipe_def_version,
            recipe_def_hash=definition.recipe_def_hash,
            run_id=token,
            input_revisions=revisions,
            transform_pins=pins,
            environment_pin=definition.environment_pin,
            completeness=definition.completeness_required,
            delivery=mode,
            lineage=lineage.value,
        )
    )


def _refuse_forbidden_payload(body: Mapping[str, object]) -> TypedRefusal | None:
    secret = _first_secret_field(body)
    if secret is not None:
        return invalid(
            secret,
            "credentials appear only as typed refs (entitlement_ref); runtime "
            "credential values are excluded from recipe_def_hash (DEC-0444)",
        )
    for key in _WRAP_FIELDS:
        if key in body:
            return policy(key, _WRAP_REASON)
    for key in _LIBRARY_FIELDS | _CT06_FIELDS:
        if key in body and body.get(key) not in (None, False):
            return _refuse_ct06_or_library(key)
    for key in _PROVIDER_VENUE_FIELDS:
        if key in body:
            return invalid(key, _PROVIDER_VENUE_REASON)
    delivery_flags = [name for name in RECIPE_DELIVERY_MODES if name in body]
    if len(delivery_flags) > 1:
        return invalid(delivery_flags[0], _DELIVERY_REASON, extra=delivery_flags)
    if "delivery" in body:
        return invalid("delivery", "delivery is a run mode, not RecipeDefinition identity")
    return _refuse_release_as_recipe(body)


def _refuse_release_as_recipe(body: Mapping[str, object]) -> TypedRefusal | None:
    if "output_release" in body and "recipe_def_id" not in body:
        return invalid("output_release", _TWO_RECIPES_REASON)
    return None


def _refuse_wrap(wrap: object) -> TypedRefusal | None:
    if wrap is None or wrap is False:
        return None
    if wrap is True:
        return policy("wrap", _WRAP_REASON)
    if not isinstance(wrap, Mapping):
        return invalid(
            "wrap",
            "a wrap claim is omitted or a mapping of refused Book/CT-33/QMN keys",
            given=repr(type(wrap).__name__),
        )
    mapping = cast("Mapping[str, object]", wrap)
    for key in _WRAP_FIELDS | _LIBRARY_FIELDS | _CT06_FIELDS:
        if key in mapping and mapping.get(key) not in (None, False):
            if key in _CT06_FIELDS or key in _LIBRARY_FIELDS:
                return _refuse_ct06_or_library(key)
            return policy(key, _WRAP_REASON)
    return None


def _refuse_ct06_or_library(field: str) -> TypedRefusal:
    if field in _LIBRARY_FIELDS:
        return policy(field, _CT06_REASON, is_library_kind=False, ct06_kind_deferred=True)
    return unsupported(field, _CT06_REASON, ct06_kind_deferred=True, is_library_kind=False)


def _parse_inputs(value: object) -> Result[list[dict[str, object]]]:
    if not isinstance(value, (list, tuple)):
        return invalid(
            "inputs",
            "RecipeDefinition inputs are a sequence of CT-10 (or sibling) descriptors",
            given=repr(type(value).__name__),
        )
    sequence = cast("Sequence[object]", value)
    if len(sequence) < 1:
        return invalid("inputs", _CATALOGUE_REASON)
    out: list[dict[str, object]] = []
    for index, item in enumerate(sequence):
        parsed = _parse_input(item, index)
        if is_refusal(parsed):
            return parsed
        out.append(parsed.value)
    return Ok(out)


def _parse_input(value: object, index: int) -> Result[dict[str, object]]:
    if not isinstance(value, Mapping):
        return invalid(
            "inputs",
            "each input is a mapping of AD-31 catalogue fields",
            index=index,
        )
    body = cast("Mapping[str, object]", value)
    secret = _first_secret_field(body)
    if secret is not None:
        return invalid(secret, "credentials appear only as typed entitlement_ref")
    for key in _PROVIDER_VENUE_FIELDS:
        if key in body:
            return invalid(key, _PROVIDER_VENUE_REASON)
    parsed = _require_keys(body, INPUT_REQUIRED_FIELDS, optional=_INPUT_OPTIONAL)
    if is_refusal(parsed):
        return parsed
    row = parsed.value
    coverage = _parse_object_section(row.get("coverage"), "coverage", _COVERAGE_FIELDS)
    if is_refusal(coverage):
        return coverage
    freshness = _parse_object_section(row.get("freshness"), "freshness", _FRESHNESS_FIELDS)
    if is_refusal(freshness):
        return freshness
    provenance = _parse_object_section(row.get("provenance"), "provenance", _PROVENANCE_FIELDS)
    if is_refusal(provenance):
        return provenance
    roles = row.get("schema_roles")
    if not isinstance(roles, (list, tuple)) or not roles:
        return invalid("schema_roles", "schema_roles is a non-empty sequence of role tokens")
    role_tokens: list[str] = []
    for role in cast("Sequence[object]", roles):
        token = clean_token(role)
        if token is None:
            return invalid("schema_roles", "each schema role is a non-empty token")
        role_tokens.append(token)
    entitlement = clean_token(row.get("entitlement_ref"))
    if entitlement is None or not entitlement.startswith("cred:"):
        return invalid(
            "entitlement_ref",
            "credentials appear only as typed refs (cred:…), never secret bytes",
            given=repr(row.get("entitlement_ref")),
        )
    provider = cast("str", row["provider"])
    venue = row.get("venue")
    if isinstance(venue, str) and venue == provider:
        return invalid("venue", _PROVIDER_VENUE_REASON, provider=provider)
    out: dict[str, object] = {
        "calendar": row["calendar"],
        "coverage": coverage.value,
        "entitlement_ref": entitlement,
        "freshness": freshness.value,
        "kind": row["kind"],
        "licensing": row["licensing"],
        "provider": provider,
        "provenance": provenance.value,
        "revision": row["revision"],
        "schema_roles": role_tokens,
        "timezone": row["timezone"],
        "units": row["units"],
    }
    instrument = row.get("instrument")
    if isinstance(instrument, str) and instrument.strip() != "":
        out["instrument"] = instrument
    if isinstance(venue, str) and venue.strip() != "":
        out["venue"] = venue
    adjustment = row.get("adjustment")
    if isinstance(adjustment, str) and adjustment.strip() != "":
        out["adjustment"] = adjustment
    return Ok(out)


def _parse_transforms(value: object) -> Result[list[dict[str, object]]]:
    if not isinstance(value, (list, tuple)):
        return invalid(
            "transforms",
            "RecipeDefinition transforms are a sequence of named transform maps",
            given=repr(type(value).__name__),
        )
    sequence = cast("Sequence[object]", value)
    if len(sequence) < 1:
        return invalid("transforms", _CATALOGUE_REASON)
    out: list[dict[str, object]] = []
    for index, item in enumerate(sequence):
        if not isinstance(item, Mapping):
            return invalid("transforms", "each transform is a mapping", index=index)
        parsed = _require_keys(cast("Mapping[str, object]", item), TRANSFORM_REQUIRED_FIELDS)
        if is_refusal(parsed):
            return parsed
        out.append(parsed.value)
    return Ok(out)


def _parse_object_section(
    value: object,
    field: str,
    required: tuple[str, ...],
    *,
    optional: frozenset[str] = frozenset(),
) -> Result[dict[str, object]]:
    if not isinstance(value, Mapping):
        return invalid(field, _CATALOGUE_REASON, given=repr(type(value).__name__))
    return _require_keys(cast("Mapping[str, object]", value), required, optional=optional)


def _require_keys(
    body: Mapping[str, object],
    required: tuple[str, ...],
    *,
    optional: frozenset[str] = frozenset(),
) -> Result[dict[str, object]]:
    secret = _first_secret_field(body)
    if secret is not None:
        return invalid(secret, "runtime credential values are excluded from identity")
    allowed = set(required) | optional
    out: dict[str, object] = {}
    for raw_key, item in body.items():
        if raw_key.strip() == "":
            return invalid("key", "catalogue field names are non-empty strings")
        if raw_key in _DISPLAY_FIELDS:
            continue
        if item is None:
            continue
        if raw_key not in allowed:
            return invalid(raw_key, _CATALOGUE_REASON, extra=raw_key)
        if isinstance(item, Mapping):
            nested = _omit_nulls(cast("Mapping[str, object]", item))
            if is_refusal(nested):
                return nested
            out[raw_key] = nested.value
        elif isinstance(item, (list, tuple)):
            out[raw_key] = list(cast("Sequence[object]", item))
        elif isinstance(item, bool):
            return invalid(raw_key, "catalogue field values are not booleans")
        elif isinstance(item, int):
            out[raw_key] = item
        else:
            token = clean_token(item)
            if token is None:
                return invalid(raw_key, "catalogue field values are tokens or nested maps")
            out[raw_key] = token
    missing = [name for name in required if name not in out]
    if missing:
        return invalid(missing[0], _CATALOGUE_REASON, missing=missing)
    return Ok(out)


def _omit_nulls(body: Mapping[str, object]) -> Result[dict[str, object]]:
    out: dict[str, object] = {}
    for key, item in body.items():
        if key.strip() == "" or item is None:
            continue
        if key in _SECRET_FIELDS:
            return invalid(key, "runtime credential values are excluded from identity")
        if isinstance(item, Mapping):
            nested = _omit_nulls(cast("Mapping[str, object]", item))
            if is_refusal(nested):
                return nested
            out[key] = nested.value
        elif isinstance(item, (list, tuple)):
            out[key] = list(cast("Sequence[object]", item))
        elif isinstance(item, bool):
            return invalid(key, "catalogue field values are not booleans")
        elif isinstance(item, int):
            out[key] = item
        else:
            token = clean_token(item)
            if token is None:
                return invalid(key, "catalogue field values are tokens or nested maps")
            out[key] = token
    return Ok(out)


def _parse_completeness_enumeration(value: object) -> Result[tuple[str, ...]]:
    if not isinstance(value, (list, tuple)):
        return invalid(
            "output_completeness_enumeration",
            "output completeness is the closed set complete | partial | missing | expired",
            given=repr(type(value).__name__),
        )
    tokens: list[str] = []
    for item in cast("Sequence[object]", value):
        token = clean_token(item)
        if token is None:
            return invalid(
                "output_completeness_enumeration",
                "each completeness token is a non-empty string",
            )
        tokens.append(token)
    if tuple(tokens) != RECIPE_OUTPUT_COMPLETENESS:
        return invalid(
            "output_completeness_enumeration",
            "output completeness is the closed set complete | partial | missing | expired",
            given=tokens,
        )
    return Ok(tuple(tokens))


def _optional_display(body: Mapping[str, object]) -> Result[str | None]:
    present = [name for name in ("recipe_id", "display_recipe_id", "display_name") if name in body]
    if not present:
        return Ok(None)
    token = clean_token(body.get(present[0]))
    if token is None:
        return Ok(None)
    return Ok(token)


def _input_revision(item: Mapping[str, object]) -> dict[str, object]:
    return {
        "provider": item["provider"],
        "revision": item["revision"],
    }


def _transform_pin(item: Mapping[str, object]) -> dict[str, object]:
    return {
        "known_at_policy": item["known_at_policy"],
        "name": item["name"],
    }


def _first_secret_field(value: object) -> str | None:
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        for key, item in mapping.items():
            if isinstance(key, str) and key in _SECRET_FIELDS:
                return key
            nested = _first_secret_field(item)
            if nested is not None:
                return nested
    elif isinstance(value, (list, tuple)):
        for item in cast("Sequence[object]", value):
            nested = _first_secret_field(item)
            if nested is not None:
                return nested
    return None


def _positive_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return invalid(field, "this field is a positive integer", given=repr(value))
    return Ok(value)


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


def _plain_mapping(value: Mapping[str, object]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, item in value.items():
        if isinstance(item, Mapping):
            out[key] = _plain_mapping(cast("Mapping[str, object]", item))
        elif isinstance(item, tuple):
            sequence = cast("Sequence[object]", item)
            out[key] = [
                _plain_mapping(cast("Mapping[str, object]", entry))
                if isinstance(entry, Mapping)
                else entry
                for entry in sequence
            ]
        elif isinstance(item, Fingerprint):
            out[key] = item.value
        else:
            out[key] = item
    return out


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    frozen: dict[str, object] = {}
    for key, item in value.items():
        if isinstance(item, Mapping):
            frozen[key] = _freeze_mapping(cast("Mapping[str, object]", item))
        elif isinstance(item, (list, tuple)):
            sequence = cast("Sequence[object]", item)
            frozen[key] = tuple(
                _freeze_mapping(cast("Mapping[str, object]", entry))
                if isinstance(entry, Mapping)
                else entry
                for entry in sequence
            )
        else:
            frozen[key] = item
    return MappingProxyType(frozen)
