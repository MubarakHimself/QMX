"""Library search over the three existing query surfaces (Story 34.2).

Search by kind + ``fp1`` is a read-time fold over (1) the B-15 registry-read
as-of port (Story 13.2), (2) the QMB ledger merge view (Story 15.4), and
(3) coordinated Experiment Ledger refs (Story 46.3). It opens no fourth
store, holds no door-side registry cache, and does not read QMA staging
(FR-W19, FR-W20, UX-DR4, DEC-0271, DEC-0282).

Saved views and analysis publications are query hits citing the source
kind's ``fp1`` (the CT-32, or a saved-view JSON ``fp1`` when one already
exists). They are not a new registry kind (FR-W19, FR-W18).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Protocol, cast, runtime_checkable

from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    TypedRefusal,
    is_ok,
    is_refusal,
)
from qmf.registry import RegistrationRecord

from qmb._refuse import clean_token, invalid, policy
from qmb.registryread.library import KIND_OWNER, register_library_kind
from qmb.registryread.port import RegistryReadPort, ResolvedRef

if TYPE_CHECKING:
    from qmb.ledger.line import LedgerLine

__all__ = [
    "CITATION_KINDS",
    "CITATION_KIND_PUBLICATION",
    "CITATION_KIND_SAVED_VIEW",
    "LIBRARY_SEARCH_CLASS",
    "LIBRARY_SEARCH_HOLDS_CACHE",
    "LIBRARY_SEARCH_MINTS_CT32",
    "LIBRARY_SEARCH_MINTS_EXPERIMENT_SPEC",
    "LIBRARY_SEARCH_OCCUPANCY",
    "LIBRARY_SEARCH_OPENS_FOURTH_STORE",
    "LIBRARY_SEARCH_READS_STAGING",
    "QUERY_SURFACES",
    "SURFACE_EXPERIMENT_LEDGER",
    "SURFACE_LEDGER_MERGE",
    "SURFACE_REGISTRY_AS_OF",
    "ExperimentLedgerRef",
    "LibraryHit",
    "LibrarySearch",
    "SavedViewCite",
    "library_search_identity",
    "search_library",
]

LIBRARY_SEARCH_CLASS: Final[str] = "qmb-library-search"
LIBRARY_SEARCH_OCCUPANCY: Final[str] = "query"
LIBRARY_SEARCH_MINTS_CT32: Final[bool] = False
LIBRARY_SEARCH_MINTS_EXPERIMENT_SPEC: Final[bool] = False
LIBRARY_SEARCH_OPENS_FOURTH_STORE: Final[bool] = False
LIBRARY_SEARCH_READS_STAGING: Final[bool] = False
LIBRARY_SEARCH_HOLDS_CACHE: Final[bool] = False

SURFACE_REGISTRY_AS_OF: Final[str] = "registry-as-of"
SURFACE_LEDGER_MERGE: Final[str] = "ledger-merge"
SURFACE_EXPERIMENT_LEDGER: Final[str] = "experiment-ledger"
QUERY_SURFACES: Final[tuple[str, ...]] = (
    SURFACE_REGISTRY_AS_OF,
    SURFACE_LEDGER_MERGE,
    SURFACE_EXPERIMENT_LEDGER,
)

CITATION_KIND_SAVED_VIEW: Final[str] = "saved-view"
CITATION_KIND_PUBLICATION: Final[str] = "analysis-publication"
CITATION_KINDS: Final[tuple[str, ...]] = (
    CITATION_KIND_SAVED_VIEW,
    CITATION_KIND_PUBLICATION,
)

_HIT_CLASS: Final[str] = "qmb-library-hit"
_SAVED_VIEW_CITE_CLASS: Final[str] = "qmb-saved-view-cite"
_EXPERIMENT_REF_CLASS: Final[str] = "qmb-experiment-ledger-ref"
_LANE_COORDINATED: Final[str] = "coordinated"
_PERFORMANCE_RESULT: Final[str] = "performance-result"
_EXPERIMENT_SPEC: Final[str] = "experiment-spec"
_SOURCE_KIND_CT32: Final[str] = _PERFORMANCE_RESULT

_CITATION_ALIASES: Final[Mapping[str, str]] = {
    "saved-view": CITATION_KIND_SAVED_VIEW,
    "savedview": CITATION_KIND_SAVED_VIEW,
    "saved-views": CITATION_KIND_SAVED_VIEW,
    "analysis-publication": CITATION_KIND_PUBLICATION,
    "analysis.published": CITATION_KIND_PUBLICATION,
    "analysis-published": CITATION_KIND_PUBLICATION,
    "analysispublication": CITATION_KIND_PUBLICATION,
}

_FOURTH_STORE_FIELDS: Final[tuple[str, ...]] = (
    "store",
    "sqlite",
    "database",
    "fourth_store",
    "new_store",
    "identity_store",
)

_STAGING_FIELDS: Final[tuple[str, ...]] = (
    "staging",
    "qma_staging",
    "refinement_proposals",
)


def library_search_identity() -> dict[str, object]:
    """Identity-bearing Library-search fields. Package SemVer is omitted."""
    return {
        "class": LIBRARY_SEARCH_CLASS,
        "command": "library.search",
        "holds_cache": LIBRARY_SEARCH_HOLDS_CACHE,
        "mints_ct32": LIBRARY_SEARCH_MINTS_CT32,
        "mints_experiment_spec": LIBRARY_SEARCH_MINTS_EXPERIMENT_SPEC,
        "occupancy": LIBRARY_SEARCH_OCCUPANCY,
        "opens_fourth_store": LIBRARY_SEARCH_OPENS_FOURTH_STORE,
        "owner": KIND_OWNER,
        "reads_staging": LIBRARY_SEARCH_READS_STAGING,
        "surfaces": list(QUERY_SURFACES),
    }


@dataclass(frozen=True, slots=True)
class LibraryHit:
    """One Library search hit. Identity cite is ``fp1``, never a new kind."""

    kind: str
    fingerprint: Fingerprint
    surface: str
    is_registry_kind: bool
    source_fp1: Fingerprint | None = None
    contract: str | None = None
    ledger_ref: str | None = None

    def cite(self) -> str:
        """The only legal identity cite: ``fp1`` of the source kind (or JSON)."""
        return self.fingerprint.value

    def fp1_identity(self) -> dict[str, object]:
        """Identity-bearing hit fields. Package SemVer is omitted."""
        content: dict[str, object] = {
            "class": _HIT_CLASS,
            "fp1": self.fingerprint.value,
            "is_registry_kind": self.is_registry_kind,
            "kind": self.kind,
            "surface": self.surface,
        }
        if self.source_fp1 is not None:
            content["source_fp1"] = self.source_fp1.value
        if self.contract is not None:
            content["contract"] = self.contract
        if self.ledger_ref is not None:
            content["ledger_ref"] = self.ledger_ref
        return content


@dataclass(frozen=True, slots=True)
class LibrarySearch:
    """Read-time fold over the three query surfaces. Occupancy is a query."""

    kind: str
    hits: tuple[LibraryHit, ...]
    fingerprint: Fingerprint | None = None
    occupancy: str = LIBRARY_SEARCH_OCCUPANCY
    surfaces: tuple[str, ...] = QUERY_SURFACES
    mints_ct32: bool = False
    mints_experiment_spec: bool = False
    opens_fourth_store: bool = False
    reads_staging: bool = False
    holds_cache: bool = False
    is_registry_kind: bool = True

    def fp1_identity(self) -> dict[str, object]:
        """Identity-bearing search fields. Package SemVer is omitted."""
        content: dict[str, object] = {
            "class": LIBRARY_SEARCH_CLASS,
            "command": "library.search",
            "holds_cache": False,
            "hits": [hit.fp1_identity() for hit in self.hits],
            "is_registry_kind": self.is_registry_kind,
            "kind": self.kind,
            "mints_ct32": False,
            "mints_experiment_spec": False,
            "occupancy": LIBRARY_SEARCH_OCCUPANCY,
            "opens_fourth_store": False,
            "owner": KIND_OWNER,
            "reads_staging": False,
            "surfaces": list(QUERY_SURFACES),
        }
        if self.fingerprint is not None:
            content["fp1"] = self.fingerprint.value
        return content


@dataclass(frozen=True, slots=True)
class ExperimentLedgerRef:
    """One coordinated Experiment Ledger citation (Story 46.3).

    QMB never opens the Experiment Ledger store. The caller (daemon or test)
    supplies refs already read from that store.
    """

    ledger_ref: str
    spec_fp1: Fingerprint
    cited_fp1: Fingerprint
    kind: str = _EXPERIMENT_SPEC
    workbench_lane: str = _LANE_COORDINATED

    @classmethod
    def try_create(
        cls,
        ledger_ref: object,
        spec_fp1: object,
        *,
        cited_fp1: object = None,
        kind: object = None,
        workbench_lane: object = _LANE_COORDINATED,
    ) -> Result[ExperimentLedgerRef]:
        """Validate one Experiment Ledger citation, returning value-or-refusal."""
        token = clean_token(ledger_ref)
        if token is None:
            return invalid(
                "ledger_ref",
                "an Experiment Ledger ref names a non-blank ledger_ref",
                given=repr(ledger_ref),
            )
        spec = _coerce_fingerprint(spec_fp1)
        if spec is None:
            return invalid(
                "spec_fp1",
                "an Experiment Ledger ref cites the ExperimentSpec by fp1",
                given=repr(spec_fp1),
            )
        cited = spec if cited_fp1 is None else _coerce_fingerprint(cited_fp1)
        if cited is None:
            return invalid(
                "cited_fp1",
                "an Experiment Ledger _ref cites a source kind by fp1",
                given=repr(cited_fp1),
            )
        lane = clean_token(workbench_lane)
        if lane is None:
            return invalid(
                "workbench_lane",
                "Experiment Ledger refs are coordinated-lane only (Story 46.3)",
                given=repr(workbench_lane),
            )
        folded_lane = _fold(lane)
        if folded_lane != _LANE_COORDINATED:
            return policy(
                "workbench_lane",
                "Experiment Ledger refs are coordinated-lane only (Story 46.3, DEC-0270)",
                given=folded_lane,
                required=_LANE_COORDINATED,
            )
        if kind is None:
            kind_token = _EXPERIMENT_SPEC
        else:
            admitted = register_library_kind(kind, lane=_LANE_COORDINATED)
            if is_refusal(admitted):
                return admitted
            kind_token = admitted.value.kind
        return Ok(
            cls(
                ledger_ref=token,
                spec_fp1=spec,
                cited_fp1=cited,
                kind=kind_token,
                workbench_lane=_LANE_COORDINATED,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """Identity-bearing Experiment Ledger citation. Package SemVer is omitted."""
        return {
            "cited_fp1": self.cited_fp1.value,
            "class": _EXPERIMENT_REF_CLASS,
            "kind": self.kind,
            "ledger_ref": self.ledger_ref,
            "spec_fp1": self.spec_fp1.value,
            "workbench_lane": self.workbench_lane,
        }


@dataclass(frozen=True, slots=True)
class SavedViewCite:
    """A saved-view or analysis-publication citation of a source kind's fp1.

    Not a registry kind. ``view_fp1`` is the saved-view JSON fingerprint when
    one already exists; otherwise the hit cites the source CT-32.
    """

    source_fp1: Fingerprint
    kind: str = CITATION_KIND_SAVED_VIEW
    view_fp1: Fingerprint | None = None

    @classmethod
    def try_create(
        cls,
        source_fp1: object,
        *,
        kind: object = CITATION_KIND_SAVED_VIEW,
        view_fp1: object = None,
    ) -> Result[SavedViewCite]:
        """Validate a citation hit. Refuses minting a registry kind."""
        source = _coerce_fingerprint(source_fp1)
        if source is None:
            return invalid(
                "source_fp1",
                "a saved-view hit cites the source kind's fp1 (the CT-32)",
                given=repr(source_fp1),
            )
        citation = _canonical_citation(kind)
        if citation is None:
            return invalid(
                "kind",
                "a citation hit is a saved-view or analysis-publication, never a "
                "new registry kind (FR-W19, FR-W18)",
                given=repr(kind),
                legal=list(CITATION_KINDS),
            )
        view: Fingerprint | None = None
        if view_fp1 is not None:
            parsed_view = _coerce_fingerprint(view_fp1)
            if parsed_view is None:
                return invalid(
                    "view_fp1",
                    "a saved-view JSON fp1 is an fp1 fingerprint when present",
                    given=repr(view_fp1),
                )
            view = parsed_view
        return Ok(cls(source_fp1=source, kind=citation, view_fp1=view))

    def cite(self) -> Fingerprint:
        """JSON fp1 when one exists; otherwise the source CT-32."""
        return self.view_fp1 if self.view_fp1 is not None else self.source_fp1

    def fp1_identity(self) -> dict[str, object]:
        """Identity-bearing citation. Package SemVer is omitted."""
        content: dict[str, object] = {
            "class": _SAVED_VIEW_CITE_CLASS,
            "is_registry_kind": False,
            "kind": self.kind,
            "source_fp1": self.source_fp1.value,
            "source_kind": _SOURCE_KIND_CT32,
        }
        if self.view_fp1 is not None:
            content["view_fp1"] = self.view_fp1.value
        return content


@runtime_checkable
class _ExperimentLedgerRefSource(Protocol):
    """Injected Story 46.3 reader. QMB never opens the store."""

    def refs(self) -> object: ...


def search_library(
    kind: object,
    *,
    fp1: object = None,
    port: object = None,
    ledger_lines: object = None,
    world: object = None,
    role: object = None,
    experiment_refs: object = None,
    saved_views: object = None,
    lane: object = None,
    staging: object = None,
    qma_staging: object = None,
    refinement_proposals: object = None,
    store: object = None,
    sqlite: object = None,
    database: object = None,
    fourth_store: object = None,
    new_store: object = None,
    identity_store: object = None,
) -> Result[LibrarySearch]:
    """Search Library kinds by kind + fp1 over the three existing surfaces.

    Story 13.2 frozen as-of / fingerprint resolution is delegated to
    :class:`RegistryReadPort.resolve` — this fold never adds a door-side
    cache and never opens a fourth store.
    """
    store_field = _requested_field(
        {
            "store": store,
            "sqlite": sqlite,
            "database": database,
            "fourth_store": fourth_store,
            "new_store": new_store,
            "identity_store": identity_store,
        },
        _FOURTH_STORE_FIELDS,
    )
    if store_field is not None:
        return policy(
            store_field,
            "Library search reads the three existing surfaces and does not open "
            "a fourth store (FR-W19, DEC-0271, UX-DR4)",
            occupancy=LIBRARY_SEARCH_OCCUPANCY,
            opens_fourth_store=False,
            reads_staging=False,
            surfaces=list(QUERY_SURFACES),
            owner=KIND_OWNER,
        )
    staging_field = _requested_field(
        {
            "staging": staging,
            "qma_staging": qma_staging,
            "refinement_proposals": refinement_proposals,
        },
        _STAGING_FIELDS,
    )
    if staging_field is not None:
        return policy(
            staging_field,
            "Library search does not read QMA staging; a fold of staging into "
            "Library is refused (FR-W20, DEC-0282)",
            occupancy=LIBRARY_SEARCH_OCCUPANCY,
            reads_staging=False,
            opens_fourth_store=False,
            surfaces=list(QUERY_SURFACES),
            owner=KIND_OWNER,
        )
    if port is not None and not isinstance(port, RegistryReadPort):
        return invalid(
            "port",
            "Library search reads as-of through the one B-15 RegistryReadPort; "
            "it does not add a door-side registry cache (AR-W04, Story 13.2)",
            given=repr(type(port).__name__),
        )
    wanted = _coerce_fingerprint(fp1) if fp1 is not None else None
    if fp1 is not None and wanted is None:
        token = clean_token(fp1)
        if token is None:
            return invalid(
                "fp1",
                "search by fp1 takes an fp1 fingerprint or, before sweep admission, "
                "a human alias resolved through the B-15 port",
                given=repr(fp1),
            )
        if "@" in token:
            return invalid(
                "fp1",
                "name@version is not a legal identity cite; after admission, "
                "fragments resolve by explicit fingerprint, never name@latest "
                "(B-13, B-15, Story 13.2)",
                given=token,
            )
        if isinstance(port, RegistryReadPort):
            resolved_alias = port.resolve(token)
            if is_refusal(resolved_alias):
                return resolved_alias
            wanted = resolved_alias.value.fingerprint
        else:
            return invalid(
                "fp1",
                "a non-fingerprint search token resolves through the B-15 as-of "
                "port; name@version is never a cite (Story 13.2)",
                given=token,
            )
    citation = _canonical_citation(kind)
    if citation is not None:
        return _search_citations(
            citation,
            wanted=wanted,
            port=port if isinstance(port, RegistryReadPort) else None,
            ledger_lines=ledger_lines,
            world=world,
            role=role,
            experiment_refs=experiment_refs,
            saved_views=saved_views,
        )
    admitted = register_library_kind(kind, lane=lane)
    if is_refusal(admitted):
        return admitted
    member = admitted.value
    as_of_hits = _hits_from_as_of(
        port if isinstance(port, RegistryReadPort) else None,
        kind=member.kind,
        wanted=wanted,
        fp1=fp1,
    )
    if isinstance(as_of_hits, TypedRefusal):
        return as_of_hits
    merged = _merged_lines(ledger_lines, world=world, role=role)
    if isinstance(merged, TypedRefusal):
        return merged
    ledger_hits = _hits_from_ledger(merged, kind=member.kind, wanted=wanted)
    refs = _as_experiment_refs(experiment_refs)
    if isinstance(refs, TypedRefusal):
        return refs
    experiment_hits = _hits_from_experiment(refs, kind=member.kind, wanted=wanted)
    hits = _dedupe((*as_of_hits, *ledger_hits, *experiment_hits))
    return Ok(
        LibrarySearch(
            kind=member.kind,
            fingerprint=wanted,
            hits=hits,
            is_registry_kind=True,
        )
    )


def _search_citations(
    citation: str,
    *,
    wanted: Fingerprint | None,
    port: RegistryReadPort | None,
    ledger_lines: object,
    world: object,
    role: object,
    experiment_refs: object,
    saved_views: object,
) -> Result[LibrarySearch]:
    """Return saved-view / publication hits citing the source kind's fp1."""
    cites = _as_saved_views(saved_views)
    if isinstance(cites, TypedRefusal):
        return cites
    merged = _merged_lines(ledger_lines, world=world, role=role)
    if isinstance(merged, TypedRefusal):
        return merged
    refs = _as_experiment_refs(experiment_refs)
    if isinstance(refs, TypedRefusal):
        return refs
    hits: list[LibraryHit] = []
    for cite in cites:
        if cite.kind != citation:
            continue
        cited = cite.cite()
        if wanted is not None and wanted.value not in {cited.value, cite.source_fp1.value}:
            continue
        surface = _citation_surface(
            cite.source_fp1,
            port=port,
            lines=merged,
            refs=refs,
        )
        hits.append(
            LibraryHit(
                kind=citation,
                fingerprint=cited,
                surface=surface,
                is_registry_kind=False,
                source_fp1=cite.source_fp1,
                contract="CT-32",
            )
        )
    return Ok(
        LibrarySearch(
            kind=citation,
            fingerprint=wanted,
            hits=_dedupe(tuple(hits)),
            is_registry_kind=False,
        )
    )


def _citation_surface(
    source: Fingerprint,
    *,
    port: RegistryReadPort | None,
    lines: tuple[LedgerLine, ...],
    refs: tuple[ExperimentLedgerRef, ...],
) -> str:
    """Bind a citation hit to one of the three existing surfaces."""
    for line in lines:
        if line.ct32_fingerprint is not None and line.ct32_fingerprint.value == source.value:
            return SURFACE_LEDGER_MERGE
    for ref in refs:
        if source.value in {ref.cited_fp1.value, ref.spec_fp1.value}:
            return SURFACE_EXPERIMENT_LEDGER
    if port is not None:
        member = port.bound.get(source)
        if member is not None:
            return SURFACE_REGISTRY_AS_OF
        resolved = port.resolve(source)
        if is_ok(resolved):
            return SURFACE_REGISTRY_AS_OF
    return SURFACE_LEDGER_MERGE


def _hits_from_as_of(
    port: RegistryReadPort | None,
    *,
    kind: str,
    wanted: Fingerprint | None,
    fp1: object,
) -> tuple[LibraryHit, ...] | TypedRefusal:
    """Story 13.2: resolve through the one registry-read port."""
    if port is None:
        return ()
    if wanted is not None or fp1 is not None:
        ref = wanted if wanted is not None else fp1
        resolved = port.resolve(ref)
        if is_refusal(resolved):
            if resolved.category is RefusalCategory.UNAVAILABLE_DEPENDENCY:
                return ()
            return resolved
        return _hit_from_resolved(port, resolved.value, kind=kind)
    hits: list[LibraryHit] = []
    for candidate in port.complete("", kind=kind):
        resolved = port.resolve(candidate.fingerprint)
        if is_refusal(resolved):
            continue
        hits.extend(_hit_from_resolved(port, resolved.value, kind=kind))
    if not hits:
        for record in port.bound.records:
            if record.kind != kind:
                continue
            resolved = port.resolve(record.stable_id)
            if is_refusal(resolved):
                continue
            hits.extend(_hit_from_resolved(port, resolved.value, kind=kind))
    return tuple(hits)


def _hit_from_resolved(
    port: RegistryReadPort,
    resolved: ResolvedRef,
    *,
    kind: str,
) -> tuple[LibraryHit, ...]:
    """Admit a B-15 resolution as a Library hit when the kind matches."""
    record_kind = _resolved_kind(port, resolved)
    if record_kind != kind:
        return ()
    return (
        LibraryHit(
            kind=kind,
            fingerprint=resolved.fingerprint,
            surface=SURFACE_REGISTRY_AS_OF,
            is_registry_kind=True,
            contract=_contract_for(kind),
        ),
    )


def _resolved_kind(port: RegistryReadPort, resolved: ResolvedRef) -> str | None:
    """Record kind for a resolved ref, walking a fragment to its source."""
    if resolved.record is not None:
        return resolved.record.kind
    if resolved.fragment is None:
        return None
    source = port.bound.get(resolved.fragment.source_fp1)
    if isinstance(source, RegistrationRecord):
        return source.kind
    return None


def _hits_from_ledger(
    lines: tuple[LedgerLine, ...],
    *,
    kind: str,
    wanted: Fingerprint | None,
) -> tuple[LibraryHit, ...]:
    """Story 15.4: fold the world-and-role-scoped merge view."""
    if kind != _PERFORMANCE_RESULT:
        return ()
    hits: list[LibraryHit] = []
    for line in lines:
        if line.ct32_fingerprint is None:
            continue
        if wanted is not None and line.ct32_fingerprint.value != wanted.value:
            continue
        hits.append(
            LibraryHit(
                kind=kind,
                fingerprint=line.ct32_fingerprint,
                surface=SURFACE_LEDGER_MERGE,
                is_registry_kind=True,
                contract="CT-32",
            )
        )
    return tuple(hits)


def _hits_from_experiment(
    refs: tuple[ExperimentLedgerRef, ...],
    *,
    kind: str,
    wanted: Fingerprint | None,
) -> tuple[LibraryHit, ...]:
    """Story 46.3: fold coordinated Experiment Ledger refs, never the store."""
    hits: list[LibraryHit] = []
    for ref in refs:
        if ref.kind != kind:
            continue
        if wanted is not None and wanted.value not in {
            ref.cited_fp1.value,
            ref.spec_fp1.value,
        }:
            continue
        hits.append(
            LibraryHit(
                kind=kind,
                fingerprint=ref.cited_fp1,
                surface=SURFACE_EXPERIMENT_LEDGER,
                is_registry_kind=True,
                source_fp1=ref.spec_fp1,
                contract=_contract_for(kind),
                ledger_ref=ref.ledger_ref,
            )
        )
    return tuple(hits)


def _merged_lines(
    ledger_lines: object,
    *,
    world: object,
    role: object,
) -> tuple[LedgerLine, ...] | TypedRefusal:
    """Read the Story 15.4 merge view, or admit an already-merged sequence."""
    # Late import: qmb.ledger → config.compiler → fragments → registryread.
    from qmb.ledger.line import (  # noqa: PLC0415
        ROLE_CONFIRMATION,
        LedgerLine,
        merge_ledger_lines,
    )

    if ledger_lines is None:
        return ()
    if world is not None:
        merged = merge_ledger_lines(
            ledger_lines,
            world=world,
            role=ROLE_CONFIRMATION if role is None else role,
        )
        if is_refusal(merged):
            return merged
        return merged.value
    if isinstance(ledger_lines, (str, bytes)) or not isinstance(ledger_lines, Sequence):
        return invalid(
            "ledger_lines",
            "Library search reads the QMB ledger merge view as a sequence of lines",
            given=repr(type(ledger_lines).__name__),
        )
    admitted: list[LedgerLine] = []
    for index, raw in enumerate(cast("Sequence[object]", ledger_lines)):
        if isinstance(raw, LedgerLine):
            admitted.append(raw)
            continue
        parsed = LedgerLine.from_mapping(raw)
        if is_refusal(parsed):
            extra = dict(parsed.context)
            extra["index"] = index
            return TypedRefusal(
                category=parsed.category,
                retryability=parsed.retryability,
                context=extra,
            )
        admitted.append(parsed.value)
    return tuple(admitted)


def _as_experiment_refs(value: object) -> tuple[ExperimentLedgerRef, ...] | TypedRefusal:
    """Admit injected Story 46.3 refs. Never opens the Experiment Ledger store."""
    if value is None:
        return ()
    if isinstance(value, _ExperimentLedgerRefSource):
        value = value.refs()
    if isinstance(value, ExperimentLedgerRef):
        return (value,)
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "experiment_refs",
            "coordinated Experiment Ledger refs are a sequence already read from "
            "Story 46.3; Library search does not open that store",
            given=repr(type(value).__name__),
        )
    admitted: list[ExperimentLedgerRef] = []
    for index, raw in enumerate(cast("Sequence[object]", value)):
        parsed = _one_experiment_ref(raw)
        if is_refusal(parsed):
            extra = dict(parsed.context)
            extra["index"] = index
            return TypedRefusal(
                category=parsed.category,
                retryability=parsed.retryability,
                context=extra,
            )
        admitted.append(parsed.value)
    return tuple(admitted)


def _one_experiment_ref(raw: object) -> Result[ExperimentLedgerRef]:
    if isinstance(raw, ExperimentLedgerRef):
        return Ok(raw)
    if not isinstance(raw, Mapping):
        return invalid(
            "experiment_refs",
            "an Experiment Ledger ref is an ExperimentLedgerRef or mapping",
            given=repr(type(raw).__name__),
        )
    body = cast("Mapping[str, object]", raw)
    return ExperimentLedgerRef.try_create(
        body.get("ledger_ref"),
        body.get("spec_fp1"),
        cited_fp1=body.get("cited_fp1"),
        kind=body.get("kind"),
        workbench_lane=body.get("workbench_lane", _LANE_COORDINATED),
    )


def _as_saved_views(value: object) -> tuple[SavedViewCite, ...] | TypedRefusal:
    """Admit citation hits. Not a store and not a registry kind."""
    if value is None:
        return ()
    if isinstance(value, SavedViewCite):
        return (value,)
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "saved_views",
            "saved-view citations are a sequence of source-kind fp1 cites, not a "
            "registry kind and not a fourth store (FR-W19)",
            given=repr(type(value).__name__),
        )
    admitted: list[SavedViewCite] = []
    for index, raw in enumerate(cast("Sequence[object]", value)):
        parsed = _one_saved_view(raw)
        if is_refusal(parsed):
            extra = dict(parsed.context)
            extra["index"] = index
            return TypedRefusal(
                category=parsed.category,
                retryability=parsed.retryability,
                context=extra,
            )
        admitted.append(parsed.value)
    return tuple(admitted)


def _one_saved_view(raw: object) -> Result[SavedViewCite]:
    if isinstance(raw, SavedViewCite):
        return Ok(raw)
    if not isinstance(raw, Mapping):
        return invalid(
            "saved_views",
            "a saved-view citation is a SavedViewCite or mapping",
            given=repr(type(raw).__name__),
        )
    body = cast("Mapping[str, object]", raw)
    return SavedViewCite.try_create(
        body.get("source_fp1"),
        kind=body.get("kind", CITATION_KIND_SAVED_VIEW),
        view_fp1=body.get("view_fp1"),
    )


def _dedupe(hits: tuple[LibraryHit, ...]) -> tuple[LibraryHit, ...]:
    """Stable unique hits by surface + kind + fp1."""
    seen: set[tuple[str, str, str]] = set()
    out: list[LibraryHit] = []
    ordered = sorted(hits, key=lambda hit: (hit.surface, hit.kind, hit.fingerprint.value))
    for hit in ordered:
        key = (hit.surface, hit.kind, hit.fingerprint.value)
        if key in seen:
            continue
        seen.add(key)
        out.append(hit)
    return tuple(out)


def _requested_field(fields: Mapping[str, object], names: Sequence[str]) -> str | None:
    """Return the first requested store/staging field, else None."""
    for name in names:
        value = fields.get(name)
        if value is None or value is False:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return name
    return None


def _canonical_citation(kind: object) -> str | None:
    token = clean_token(kind)
    if token is None:
        return None
    return _CITATION_ALIASES.get(_fold(token))


def _contract_for(kind: str) -> str | None:
    contracts = {
        "bot-definition": "CT-33",
        "confluence": "CT-34",
        "strategy-family": "CT-06",
        "book-definition": "CT-22",
        "bms-definition": "CT-27",
        "book-binding": "CT-28",
        "split-manifest": "CT-12",
        "source-observation": "CT-10",
        "performance-result": "CT-32",
        "experiment-spec": "CT-47",
    }
    return contracts.get(kind)


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


def _fold(token: str) -> str:
    return token.casefold().replace("_", "-").replace(" ", "-")
