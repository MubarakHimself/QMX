"""Composition-root CT-06 mint: once per fingerprint (E12-F01 / Story 25.3).

Compose constructs Books, BMS instances, bindings, seats, calendar identities,
capability profiles, and producer definitions by minting fingerprintable content
through the existing qmf-registry :class:`~qmf.registry.Registrar` seam. Stable
ids derive from ``fp1`` exactly once per fingerprint; child modules never
restamp. Each occurrence cites the canonical definition record and
``composition_fp`` as permitted occurrence evidence outside identity, so
duplicate content across processes or timers returns the existing record (QMB
B-15; AD-16; CT-06/09). Doors hold no registry cache and no alternate identity
function — ``qmf.core.fingerprint`` is the sole identity path.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.registry import (
    FieldSetKind,
    KindRegistry,
    Registrar,
    RegistrationRecord,
    WriteOutcome,
)

from qmn.host._refuse import clean_token, invalid, policy

__all__ = [
    "COMPOSE_KIND_FORMAT_VERSION",
    "COMPOSE_RECORD_KINDS",
    "DOOR_LOCAL_REGISTRY_CACHE",
    "HAS_ALTERNATE_IDENTITY_FUNCTION",
    "IDENTITY_FORBIDDEN_OCCURRENCE_KEYS",
    "REGISTRY_MINT_SURFACE",
    "ComposeOccurrenceEvidence",
    "CompositionRootRegistry",
    "compose_kind_contract",
    "install_compose_kinds",
    "mint_compose_record",
]

REGISTRY_MINT_SURFACE: Final[str] = "qmn.host"
COMPOSE_KIND_FORMAT_VERSION: Final[int] = 1

# Closed Compose mint roster (Story 25.3 AC1). CT-06 risk names where they exist;
# seat / calendar-identity / capability-profile / producer-definition are
# composition-root addable kinds under the same FieldSetKind machinery.
COMPOSE_RECORD_KINDS: Final[tuple[str, ...]] = (
    "book-definition",
    "bms-definition",
    "book-binding",
    "seat",
    "calendar-identity",
    "capability-profile",
    "producer-definition",
)

# Occurrence cites never enter fp1 identity (DEC-0110, DEC-0187).
IDENTITY_FORBIDDEN_OCCURRENCE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "composition_fp",
        "composition-fp",
        "created_at",
        "writer",
        "sequence",
        "occurrence",
    }
)

# Doors never own a registry cache or a second fingerprint path (B-15; AD-16).
DOOR_LOCAL_REGISTRY_CACHE: Final[bool] = False
HAS_ALTERNATE_IDENTITY_FUNCTION: Final[bool] = False

_BODY_FIELD: Final[str] = "content"


@dataclass(frozen=True, slots=True)
class ComposeOccurrenceEvidence:
    """Permitted occurrence evidence for one composition-root mint.

    Cites the canonical definition record and ``composition_fp``. Both cites sit
    outside the CT-06 record's ``fp1`` identity so identical content across
    processes or timers still deduplicates on the Registrar seam.
    """

    kind: str
    outcome: WriteOutcome
    record: RegistrationRecord
    definition_fp: Fingerprint
    composition_fp: Fingerprint

    @property
    def stable_id(self) -> Fingerprint:
        return self.record.stable_id

    @property
    def was_stored(self) -> bool:
        return self.outcome is WriteOutcome.STORED

    @property
    def was_idempotent(self) -> bool:
        return self.outcome is WriteOutcome.IDEMPOTENT


def compose_kind_contract(kind: object) -> Result[FieldSetKind]:
    """Build the CT-06 FieldSetKind contract for one Compose mint kind."""
    token = clean_token(kind)
    if token is None or token not in COMPOSE_RECORD_KINDS:
        return invalid(
            "kind",
            "Compose mints only the closed composition-root kind roster",
            given=repr(kind),
            allowed=list(COMPOSE_RECORD_KINDS),
        )
    return FieldSetKind.try_create(
        token,
        COMPOSE_KIND_FORMAT_VERSION,
        required_fields=(_BODY_FIELD,),
        optional_fields=(),
    )


def install_compose_kinds(registry: object) -> Result[tuple[FieldSetKind, ...]]:
    """Install every Compose mint kind on a host :class:`KindRegistry`."""
    if not isinstance(registry, KindRegistry):
        return invalid(
            "registry",
            "Compose kinds install on a CT-06 KindRegistry at the composition root",
            given=type(registry).__name__,
        )
    installed: list[FieldSetKind] = []
    for kind in COMPOSE_RECORD_KINDS:
        contract = compose_kind_contract(kind)
        if is_refusal(contract):
            return contract
        admitted = registry.register(contract.value)
        if is_refusal(admitted):
            return admitted
        installed.append(contract.value)
    return Ok(tuple(installed))


def _coerce_fingerprint(value: object, field: str) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    parsed = Fingerprint.try_create(value)
    if is_refusal(parsed):
        return invalid(
            field,
            f"{field} is an fp1 fingerprint (Fingerprint or fp1:sha256:<hex>)",
            given=repr(value),
        )
    return Ok(parsed.value)


def _refuse_occurrence_leak(body: Mapping[str, object]) -> Result[Mapping[str, object]]:
    """Refuse bodies that fold occurrence cites into identity content."""
    leaked = sorted(key for key in body if key in IDENTITY_FORBIDDEN_OCCURRENCE_KEYS)
    if leaked:
        return policy(
            "body",
            "composition_fp and other occurrence facts are excluded from fp1 identity; "
            "they cite on the occurrence evidence, never inside the record body",
            leaked=leaked,
        )
    content = body.get(_BODY_FIELD)
    if isinstance(content, Mapping):
        nested = cast("Mapping[str, object]", content)
        nested_leak = sorted(key for key in nested if key in IDENTITY_FORBIDDEN_OCCURRENCE_KEYS)
        if nested_leak:
            return policy(
                "content",
                "composition_fp and other occurrence facts are excluded from fp1 identity; "
                "they cite on the occurrence evidence, never inside fingerprintable content",
                leaked=nested_leak,
            )
    return Ok(body)


def _normalize_body(content: object) -> Result[Mapping[str, object]]:
    """Wrap fingerprintable content as the kind body ``{content: ...}``."""
    if isinstance(content, Mapping):
        mapping = cast("Mapping[str, object]", content)
        if set(mapping.keys()) == {_BODY_FIELD}:
            inner = mapping[_BODY_FIELD]
            if not isinstance(inner, Mapping):
                return invalid(
                    "content",
                    "fingerprintable Compose content is a key->value mapping",
                    given=type(inner).__name__,
                )
            body: dict[str, object] = {_BODY_FIELD: dict(cast("Mapping[str, object]", inner))}
        else:
            body = {_BODY_FIELD: dict(mapping)}
        return _refuse_occurrence_leak(body)
    return invalid(
        "content",
        "fingerprintable Compose content is a key->value mapping",
        given=type(content).__name__,
    )


def mint_compose_record(
    *,
    kind: object,
    content: object,
    registrar: object,
    writer: object,
    sequence: object,
    created_at: object,
    definition_fp: object,
    composition_fp: object,
    at_birth_parent_refs: object = (),
) -> Result[ComposeOccurrenceEvidence]:
    """Mint one Compose record through the CT-06 Registrar exactly once per fp.

    ``definition_fp`` and ``composition_fp`` are occurrence cites only. The
    definition fingerprint is also attached as an at-birth parent ref so the
    record header cites the canonical definition without folding
    ``composition_fp`` into identity.
    """
    if not isinstance(registrar, Registrar):
        return invalid(
            "registrar",
            "the composition root stamps CT-06 records through a Registrar; "
            "child modules and doors never restamp",
            given=type(registrar).__name__,
        )
    token = clean_token(kind)
    if token is None or token not in COMPOSE_RECORD_KINDS:
        return invalid(
            "kind",
            "Compose mints only the closed composition-root kind roster",
            given=repr(kind),
            allowed=list(COMPOSE_RECORD_KINDS),
        )
    definition = _coerce_fingerprint(definition_fp, "definition_fp")
    if is_refusal(definition):
        return definition
    composition = _coerce_fingerprint(composition_fp, "composition_fp")
    if is_refusal(composition):
        return composition
    body = _normalize_body(content)
    if is_refusal(body):
        return body

    parents = _merge_parent_refs(at_birth_parent_refs, definition.value)
    if is_refusal(parents):
        return parents

    receipt = registrar.register(
        kind=token,
        body=body.value,
        writer=writer,
        sequence=sequence,
        created_at=created_at,
        at_birth_parent_refs=parents.value,
    )
    if is_refusal(receipt):
        return receipt
    return Ok(
        ComposeOccurrenceEvidence(
            kind=token,
            outcome=receipt.value.outcome,
            record=receipt.value.record,
            definition_fp=definition.value,
            composition_fp=composition.value,
        )
    )


def _merge_parent_refs(
    at_birth_parent_refs: object,
    definition_fp: Fingerprint,
) -> Result[tuple[Fingerprint, ...]]:
    """Canonical definition cite plus any extra at-birth parents."""
    refs: list[Fingerprint] = [definition_fp]
    if at_birth_parent_refs is None:
        return Ok((definition_fp,))
    if isinstance(at_birth_parent_refs, (str, bytes)) or not isinstance(
        at_birth_parent_refs, Sequence
    ):
        return invalid(
            "at_birth_parent_refs",
            "at-birth parent refs are a sequence of fp1 fingerprints",
            given=type(at_birth_parent_refs).__name__,
        )
    for index, item in enumerate(cast("Sequence[object]", at_birth_parent_refs)):
        parsed = _coerce_fingerprint(item, "at_birth_parent_refs")
        if is_refusal(parsed):
            return invalid(
                "at_birth_parent_refs",
                "each at-birth parent ref is an fp1 fingerprint",
                index=index,
                given=repr(item),
            )
        refs.append(parsed.value)
    # Dedup by digest; Registrar also canonical-sorts.
    seen: set[str] = set()
    unique: list[Fingerprint] = []
    for ref in refs:
        if ref.digest in seen:
            continue
        seen.add(ref.digest)
        unique.append(ref)
    return Ok(tuple(unique))


@dataclass(frozen=True, slots=True)
class CompositionRootRegistry:
    """Single composition-root mint seam over one shared Registrar.

    Timers and sibling processes that present identical content receive the
    existing record (``idempotent``) plus fresh occurrence evidence citing this
    boot's ``composition_fp``. There is no door-local cache.
    """

    registrar: Registrar
    composition_fp: Fingerprint
    kinds: Mapping[str, FieldSetKind]

    @classmethod
    def try_create(
        cls,
        *,
        composition_fp: object,
        registrar: object | None = None,
        kinds: object | None = None,
    ) -> Result[CompositionRootRegistry]:
        """Build the root mint seam; installs Compose kinds when none supplied."""
        composition = _coerce_fingerprint(composition_fp, "composition_fp")
        if is_refusal(composition):
            return composition

        if registrar is None:
            registry = KindRegistry()
            installed = install_compose_kinds(registry)
            if is_refusal(installed):
                return installed
            built_registrar = Registrar(registry)
            kind_map = {contract.name: contract for contract in installed.value}
        else:
            if not isinstance(registrar, Registrar):
                return invalid(
                    "registrar",
                    "CompositionRootRegistry wraps a CT-06 Registrar",
                    given=type(registrar).__name__,
                )
            built_registrar = registrar
            if kinds is None:
                # Re-read contracts from the registrar's kind registry when possible.
                kind_map = {}
            elif isinstance(kinds, Mapping):
                kind_map = {
                    str(name): cast("FieldSetKind", contract)
                    for name, contract in cast("Mapping[object, object]", kinds).items()
                }
            else:
                return invalid(
                    "kinds",
                    "kinds is a name->FieldSetKind mapping when supplied",
                    given=type(kinds).__name__,
                )

        return Ok(
            cls(
                registrar=built_registrar,
                composition_fp=composition.value,
                kinds=MappingProxyType(kind_map),
            )
        )

    def mint(
        self,
        *,
        kind: object,
        content: object,
        writer: object,
        sequence: object,
        created_at: object,
        definition_fp: object,
        at_birth_parent_refs: object = (),
    ) -> Result[ComposeOccurrenceEvidence]:
        """Mint through this root's Registrar; occurrence cites this composition_fp."""
        return mint_compose_record(
            kind=kind,
            content=content,
            registrar=self.registrar,
            writer=writer,
            sequence=sequence,
            created_at=created_at,
            definition_fp=definition_fp,
            composition_fp=self.composition_fp,
            at_birth_parent_refs=at_birth_parent_refs,
        )

    def record_for(self, stable_id: object) -> RegistrationRecord | None:
        """Look up an admitted record by stable id — no door-local cache."""
        return self.registrar.record_for(stable_id)
