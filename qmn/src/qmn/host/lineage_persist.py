"""Composition lineage and occurrence evidence persistence (E12-F04 / Story 25.4).

After Compose → Fingerprint → Seal, the boot epoch becomes eligible to run only when
the composition occurrence and its append-only CT-07 lineage land through the
ratified registry→data edge (:class:`~qmf.registry.RegistryPersistence`, CT-09/11).
A sink refusal blocks readiness rather than dropping an edge. A later boot with
changed config or definitions mints new content and occurrence identities without
rewriting the prior epoch. ``continues-performance`` and ``carries-ledger`` stay two
explicit, human-signed edges that never imply each other (TN-18/25; DEC-0158).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

from qmf.core.chrono import Instant, WriterId
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.registry import (
    EdgeType,
    FieldSetKind,
    KindRegistry,
    LineageEdge,
    Registrar,
    RegistrationRecord,
    RegistryPersistence,
    StoreReceipt,
    WriteOutcome,
)

from qmn.host._refuse import clean_token, invalid, policy

__all__ = [
    "COMPOSITION_LINEAGE_STREAM",
    "COMPOSITION_OCCURRENCE_FORMAT_VERSION",
    "COMPOSITION_OCCURRENCE_KIND",
    "LINEAGE_PERSIST_SURFACE",
    "OCCURRENCE_LINEAGE_EDGE_TYPE",
    "CarriesLedgerEdgeRequest",
    "CompositionCiteSet",
    "CompositionLineageReceipt",
    "carries_ledger_edge",
    "composition_cite_set",
    "continues_performance_edge",
    "install_composition_occurrence_kind",
    "persist_composition_lineage",
    "persist_explicit_lineage_edge",
]

LINEAGE_PERSIST_SURFACE: Final[str] = "qmn.host"
COMPOSITION_OCCURRENCE_KIND: Final[str] = "composition-occurrence"
COMPOSITION_OCCURRENCE_FORMAT_VERSION: Final[int] = 1
COMPOSITION_LINEAGE_STREAM: Final[str] = "composition-lineage"
OCCURRENCE_LINEAGE_EDGE_TYPE: Final[EdgeType] = EdgeType.OCCURRENCE_OF

_BODY_FIELD: Final[str] = "content"


@dataclass(frozen=True, slots=True)
class CompositionCiteSet:
    """Identity-bearing cites sealed into one composition occurrence.

    ``composition_fp`` is occurrence provenance for the boot epoch — it cites the
    sealed composition but is excluded from the occurrence record's ``fp1`` identity
    so identical cite content still deduplicates across writers (DEC-0110, DEC-0187).
    """

    composition_fp: Fingerprint
    config_version_fp: Fingerprint
    definition_refs: tuple[Fingerprint, ...]
    capability_profile_refs: tuple[Fingerprint, ...]
    deployment_tuple_fp: Fingerprint
    code_commit_fp: Fingerprint
    calendar_identity_refs: tuple[Fingerprint, ...]

    def identity_content(self) -> dict[str, object]:
        """Fingerprintable occurrence body — composition_fp stays off identity."""
        return {
            "class": COMPOSITION_OCCURRENCE_KIND,
            "config_version_fp": self.config_version_fp.value,
            "definition_refs": tuple(sorted(ref.value for ref in self.definition_refs)),
            "capability_profile_refs": tuple(
                sorted(ref.value for ref in self.capability_profile_refs)
            ),
            "deployment_tuple_fp": self.deployment_tuple_fp.value,
            "code_commit_fp": self.code_commit_fp.value,
            "calendar_identity_refs": tuple(
                sorted(ref.value for ref in self.calendar_identity_refs)
            ),
        }

    def lineage_targets(self) -> tuple[Fingerprint, ...]:
        """Endpoints that receive append-only ``occurrence-of`` edges from the occurrence."""
        seen: set[str] = set()
        targets: list[Fingerprint] = []
        for ref in (
            self.composition_fp,
            self.config_version_fp,
            *self.definition_refs,
            *self.capability_profile_refs,
            self.deployment_tuple_fp,
            self.code_commit_fp,
            *self.calendar_identity_refs,
        ):
            if ref.digest in seen:
                continue
            seen.add(ref.digest)
            targets.append(ref)
        return tuple(targets)


@dataclass(frozen=True, slots=True)
class CompositionLineageReceipt:
    """Durable composition occurrence plus CT-07 edges after a successful sink write.

    ``ready`` is True only when the occurrence record and every required lineage edge
    persisted. A sink refusal never sets ``ready`` — readiness stays blocked so an edge
    is not silently lost (E12-F04; CT-09/11).
    """

    occurrence: RegistrationRecord
    occurrence_outcome: WriteOutcome
    edges: tuple[LineageEdge, ...]
    edge_receipts: tuple[StoreReceipt, ...]
    composition_fp: Fingerprint
    ready: bool

    @property
    def occurrence_fp(self) -> Fingerprint:
        return self.occurrence.stable_id


@dataclass(frozen=True, slots=True)
class CarriesLedgerEdgeRequest:
    """Explicit ``carries-ledger`` intent — never inferred from continues-performance."""

    from_ref: Fingerprint
    to_ref: Fingerprint
    writer: WriterId
    human_signed: bool


def install_composition_occurrence_kind(registry: object) -> Result[FieldSetKind]:
    """Install the composition-occurrence CT-06 kind on a host KindRegistry."""
    if not isinstance(registry, KindRegistry):
        return invalid(
            "registry",
            "composition-occurrence installs on a CT-06 KindRegistry at the composition root",
            given=type(registry).__name__,
        )
    contract = FieldSetKind.try_create(
        COMPOSITION_OCCURRENCE_KIND,
        COMPOSITION_OCCURRENCE_FORMAT_VERSION,
        required_fields=(_BODY_FIELD,),
        optional_fields=(),
    )
    if is_refusal(contract):
        return contract
    admitted = registry.register(contract.value)
    if is_refusal(admitted):
        return admitted
    return Ok(contract.value)


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


def _coerce_fp_sequence(value: object, field: str) -> Result[tuple[Fingerprint, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            field,
            f"{field} is a sequence of fp1 fingerprints",
            given=type(value).__name__,
        )
    refs: list[Fingerprint] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        parsed = _coerce_fingerprint(item, field)
        if is_refusal(parsed):
            return invalid(
                field,
                f"each entry of {field} is an fp1 fingerprint",
                index=index,
                given=repr(item),
            )
        refs.append(parsed.value)
    return Ok(tuple(refs))


def composition_cite_set(
    *,
    composition_fp: object,
    config_version_fp: object,
    definition_refs: object,
    capability_profile_refs: object,
    deployment_tuple_fp: object,
    code_commit_fp: object,
    calendar_identity_refs: object,
) -> Result[CompositionCiteSet]:
    """Validate and freeze the sealed cite set for one composition occurrence."""
    composition = _coerce_fingerprint(composition_fp, "composition_fp")
    if is_refusal(composition):
        return composition
    config_version = _coerce_fingerprint(config_version_fp, "config_version_fp")
    if is_refusal(config_version):
        return config_version
    definitions = _coerce_fp_sequence(definition_refs, "definition_refs")
    if is_refusal(definitions):
        return definitions
    capabilities = _coerce_fp_sequence(capability_profile_refs, "capability_profile_refs")
    if is_refusal(capabilities):
        return capabilities
    deployment = _coerce_fingerprint(deployment_tuple_fp, "deployment_tuple_fp")
    if is_refusal(deployment):
        return deployment
    code_commit = _coerce_fingerprint(code_commit_fp, "code_commit_fp")
    if is_refusal(code_commit):
        return code_commit
    calendars = _coerce_fp_sequence(calendar_identity_refs, "calendar_identity_refs")
    if is_refusal(calendars):
        return calendars
    return Ok(
        CompositionCiteSet(
            composition_fp=composition.value,
            config_version_fp=config_version.value,
            definition_refs=definitions.value,
            capability_profile_refs=capabilities.value,
            deployment_tuple_fp=deployment.value,
            code_commit_fp=code_commit.value,
            calendar_identity_refs=calendars.value,
        )
    )


def _mint_occurrence_record(
    *,
    cites: CompositionCiteSet,
    registrar: Registrar,
    writer: WriterId,
    sequence: int,
    created_at: Instant,
) -> Result[tuple[RegistrationRecord, WriteOutcome]]:
    """Mint the composition-occurrence CT-06 record through the Registrar seam."""
    body: Mapping[str, object] = {_BODY_FIELD: cites.identity_content()}
    # composition_fp cites via occurrence-of edges only — never at-birth parents
    # or body fields, so it stays outside fp1 identity (DEC-0110, DEC-0187).
    receipt = registrar.register(
        kind=COMPOSITION_OCCURRENCE_KIND,
        body=body,
        writer=writer,
        sequence=sequence,
        created_at=created_at,
        at_birth_parent_refs=(),
    )
    if is_refusal(receipt):
        return receipt
    return Ok((receipt.value.record, receipt.value.outcome))


def persist_composition_lineage(
    *,
    composition_fp: object,
    config_version_fp: object,
    definition_refs: object,
    capability_profile_refs: object,
    deployment_tuple_fp: object,
    code_commit_fp: object,
    calendar_identity_refs: object,
    persistence: object,
    writer: object,
    sequence: object,
    created_at: object,
    registrar: object | None = None,
) -> Result[CompositionLineageReceipt]:
    """Persist the composition occurrence and append-only occurrence-of edges.

    Every cite lands as a CT-07 ``occurrence-of`` edge (from_ref = occurrence,
    to_ref = cite). Persistence is append-only through CT-09: a later boot with
    different cites mints a new occurrence and new edges without rewriting the prior
    epoch. If the record sink or any edge sink refuses, the Result is that refusal —
    readiness is never granted and the edge is not silently dropped.
    """
    if not isinstance(persistence, RegistryPersistence):
        return invalid(
            "persistence",
            "composition lineage persists through the CT-09 RegistryPersistence "
            "registry→data edge",
            given=type(persistence).__name__,
        )
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "composition lineage stamps a host WriterId",
            given=type(writer).__name__,
        )
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        return invalid(
            "sequence",
            "sequence is a non-negative int per (writer, boot-epoch)",
            given=repr(sequence),
        )
    if not isinstance(created_at, Instant):
        return invalid(
            "created_at",
            "created_at is a CT-02 Instant",
            given=type(created_at).__name__,
        )

    cites = composition_cite_set(
        composition_fp=composition_fp,
        config_version_fp=config_version_fp,
        definition_refs=definition_refs,
        capability_profile_refs=capability_profile_refs,
        deployment_tuple_fp=deployment_tuple_fp,
        code_commit_fp=code_commit_fp,
        calendar_identity_refs=calendar_identity_refs,
    )
    if is_refusal(cites):
        return cites

    if registrar is None:
        registry = KindRegistry()
        installed = install_composition_occurrence_kind(registry)
        if is_refusal(installed):
            return installed
        built_registrar = Registrar(registry)
    else:
        if not isinstance(registrar, Registrar):
            return invalid(
                "registrar",
                "composition occurrence mints through a CT-06 Registrar",
                given=type(registrar).__name__,
            )
        built_registrar = registrar

    minted = _mint_occurrence_record(
        cites=cites.value,
        registrar=built_registrar,
        writer=writer,
        sequence=sequence,
        created_at=created_at,
    )
    if is_refusal(minted):
        return minted
    record, outcome = minted.value

    # Sink the occurrence first — a storage failure here blocks readiness entirely.
    stored = persistence.persist_record(record)
    if is_refusal(stored):
        return stored

    edges: list[LineageEdge] = []
    edge_receipts: list[StoreReceipt] = []
    for target in cites.value.lineage_targets():
        edge = LineageEdge.try_create(
            OCCURRENCE_LINEAGE_EDGE_TYPE,
            record.stable_id,
            target,
            writer,
        )
        if is_refusal(edge):
            return edge
        receipt = persistence.persist_edge(
            edge.value,
            edge_stream=COMPOSITION_LINEAGE_STREAM,
        )
        if is_refusal(receipt):
            # Sink refusal prevents readiness rather than losing the edge silently.
            return receipt
        edges.append(edge.value)
        edge_receipts.append(receipt.value)

    return Ok(
        CompositionLineageReceipt(
            occurrence=record,
            occurrence_outcome=outcome,
            edges=tuple(edges),
            edge_receipts=tuple(edge_receipts),
            composition_fp=cites.value.composition_fp,
            ready=True,
        )
    )


def continues_performance_edge(
    *,
    from_ref: object,
    to_ref: object,
    writer: object,
    human_signed: object,
) -> Result[LineageEdge]:
    """Author an explicit CT-07 ``continues-performance`` edge (track record only).

    Never inferred from a ``carries-ledger`` edge. Unsigned attempts are policy
    rejection (DEC-0158; TN-18/25).
    """
    if human_signed is not True:
        return policy(
            "continues_performance",
            "continues-performance asserts a track record across bindings only when "
            "human-signed; it is never inferred from carries-ledger",
            human_signed=repr(human_signed),
        )
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "a continues-performance edge stamps a host WriterId",
            given=type(writer).__name__,
        )
    return LineageEdge.try_create(
        EdgeType.CONTINUES_PERFORMANCE,
        from_ref,
        to_ref,
        writer,
    )


def carries_ledger_edge(
    *,
    from_ref: object,
    to_ref: object,
    writer: object,
    human_signed: object,
) -> Result[LineageEdge]:
    """Author an explicit CT-07 ``carries-ledger`` edge (money-state only).

    Never inferred from a ``continues-performance`` edge. Unsigned attempts are policy
    rejection (DEC-0158; TN-18/25).
    """
    if human_signed is not True:
        return policy(
            "carries_ledger",
            "carries-ledger moves per-binding money-state only when human-signed; "
            "it is never inferred from continues-performance",
            human_signed=repr(human_signed),
        )
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "a carries-ledger edge stamps a host WriterId",
            given=type(writer).__name__,
        )
    return LineageEdge.try_create(
        EdgeType.CARRIES_LEDGER,
        from_ref,
        to_ref,
        writer,
    )


def persist_explicit_lineage_edge(
    *,
    edge: object,
    persistence: object,
    edge_stream: object = COMPOSITION_LINEAGE_STREAM,
) -> Result[StoreReceipt]:
    """Append one already-authored CT-07 edge; sink refusal is returned, never dropped."""
    if not isinstance(edge, LineageEdge):
        return invalid(
            "edge",
            "persistence appends a CT-07 LineageEdge",
            given=type(edge).__name__,
        )
    if not isinstance(persistence, RegistryPersistence):
        return invalid(
            "persistence",
            "lineage edges persist through CT-09 RegistryPersistence",
            given=type(persistence).__name__,
        )
    stream = clean_token(edge_stream)
    if stream is None:
        return invalid(
            "edge_stream",
            "edge_stream is a non-blank stream name",
            given=repr(edge_stream),
        )
    return persistence.persist_edge(edge, edge_stream=stream)
