"""Candidate retain / filter / rank as a read-time query (Story 34.3).

A candidate set is a read-time view over (1) QMB ledger lines, (2) registry
as-of sets including ``dev``-zone candidates of Library kinds, and (3)
coordinated Experiment Ledger refs. It does not read QMA staging and does
not persist copied rows (FR-W20, DEC-0282).

``sweep.rank`` (Story 33.2 / 20.4) is this same view when used as the
candidate-set rank; it still publishes no copied-row artifact.

A saved view's home follows FR-W24: ungoverned is a return value;
governed-without-QMA is JSON in the source run-dir; coordinated persistence
is Epic 36. The body is required — a citation without a body is not a saved
view. Writing candidates into ``qmf-registry`` as a new kind or into a new
sqlite table is refused; DEC-0084 stays dead.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Final, cast

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal
from qmf.registry import RegistrationRecord

from qmb._refuse import clean_token, invalid, policy
from qmb.registryread.library import (
    KIND_OWNER,
    LIBRARY_KIND_NAMES,
    register_library_kind,
)
from qmb.registryread.port import RegistryReadPort
from qmb.registryread.search import QUERY_SURFACES, LibraryHit, search_library

if TYPE_CHECKING:
    from qmb.sweep.rank import SweepRanking

__all__ = [
    "CANDIDATE_SET_CLASS",
    "CANDIDATE_SET_HOLDS_CACHE",
    "CANDIDATE_SET_MINTS_CT32",
    "CANDIDATE_SET_MINTS_EXPERIMENT_SPEC",
    "CANDIDATE_SET_MINTS_REGISTRY_KIND",
    "CANDIDATE_SET_OCCUPANCY",
    "CANDIDATE_SET_OPENS_SQLITE",
    "CANDIDATE_SET_PERSISTS_COPIED_ROWS",
    "CANDIDATE_SET_READS_STAGING",
    "DEC_0084_DEAD",
    "HOME_COORDINATED",
    "HOME_GOVERNED",
    "HOME_UNGOVERNED",
    "SAVED_VIEW_CLASS",
    "SAVED_VIEW_FILENAME",
    "SAVED_VIEW_HOMES",
    "SAVED_VIEW_METHOD",
    "ZONES",
    "ZONE_DEV",
    "ZONE_LIVE",
    "Candidate",
    "CandidateSet",
    "SavedCandidateView",
    "candidate_set_identity",
    "query_candidates",
    "save_candidate_view",
]

CANDIDATE_SET_CLASS: Final[str] = "qmb-candidate-set"
CANDIDATE_SET_OCCUPANCY: Final[str] = "query"
CANDIDATE_SET_MINTS_CT32: Final[bool] = False
CANDIDATE_SET_MINTS_EXPERIMENT_SPEC: Final[bool] = False
CANDIDATE_SET_MINTS_REGISTRY_KIND: Final[bool] = False
CANDIDATE_SET_OPENS_SQLITE: Final[bool] = False
CANDIDATE_SET_READS_STAGING: Final[bool] = False
CANDIDATE_SET_PERSISTS_COPIED_ROWS: Final[bool] = False
CANDIDATE_SET_HOLDS_CACHE: Final[bool] = False
DEC_0084_DEAD: Final[bool] = True

ZONE_DEV: Final[str] = "dev"
ZONE_LIVE: Final[str] = "live"
ZONES: Final[tuple[str, ...]] = (ZONE_DEV, ZONE_LIVE)

HOME_UNGOVERNED: Final[str] = "ungoverned"
HOME_GOVERNED: Final[str] = "governed"
HOME_COORDINATED: Final[str] = "coordinated"
SAVED_VIEW_HOMES: Final[tuple[str, ...]] = (
    HOME_UNGOVERNED,
    HOME_GOVERNED,
    HOME_COORDINATED,
)
SAVED_VIEW_CLASS: Final[str] = "qmb-candidate-set-view"
SAVED_VIEW_METHOD: Final[str] = "candidate-set"
SAVED_VIEW_FILENAME: Final[str] = "candidate-set-view.json"

_CANDIDATE_CLASS: Final[str] = "qmb-candidate"
_LANE_GOVERNED: Final[str] = "governed"
_LANE_UNGOVERNED: Final[str] = "ungoverned"
_EXPERIMENT_SPEC: Final[str] = "experiment-spec"
_RANK_ENTRY: Final[str] = "sweep.rank"

_STAGING_FIELDS: Final[tuple[str, ...]] = (
    "staging",
    "qma_staging",
    "refinement_proposals",
)
_COPIED_ROW_FIELDS: Final[tuple[str, ...]] = (
    "persist",
    "persist_candidates",
    "copied_rows",
    "persist_copied_rows",
    "candidate_database",
    "database",
    "store",
    "sqlite",
    "databank",
)
_REGISTRY_KIND_FIELDS: Final[tuple[str, ...]] = (
    "mint_registry_kind",
    "registry_kind",
)

_HOME_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "ungoverned": HOME_UNGOVERNED,
        "return-value": HOME_UNGOVERNED,
        "return_value": HOME_UNGOVERNED,
        "governed": HOME_GOVERNED,
        "governed-without-qma": HOME_GOVERNED,
        "governed_without_qma": HOME_GOVERNED,
        "coordinated": HOME_COORDINATED,
        "epic-36": HOME_COORDINATED,
        "epic_36": HOME_COORDINATED,
    }
)


def candidate_set_identity() -> dict[str, object]:
    """Identity-bearing candidate-set fields. Package SemVer is omitted."""
    return {
        "class": CANDIDATE_SET_CLASS,
        "command": "library.candidates",
        "dec_0084_dead": DEC_0084_DEAD,
        "holds_cache": CANDIDATE_SET_HOLDS_CACHE,
        "homes": list(SAVED_VIEW_HOMES),
        "mints_ct32": CANDIDATE_SET_MINTS_CT32,
        "mints_experiment_spec": CANDIDATE_SET_MINTS_EXPERIMENT_SPEC,
        "mints_registry_kind": CANDIDATE_SET_MINTS_REGISTRY_KIND,
        "occupancy": CANDIDATE_SET_OCCUPANCY,
        "opens_sqlite": CANDIDATE_SET_OPENS_SQLITE,
        "owner": KIND_OWNER,
        "persists_copied_rows": CANDIDATE_SET_PERSISTS_COPIED_ROWS,
        "rank": _RANK_ENTRY,
        "reads_staging": CANDIDATE_SET_READS_STAGING,
        "surfaces": list(QUERY_SURFACES),
        "zones": list(ZONES),
    }


@dataclass(frozen=True, slots=True)
class Candidate:
    """One candidate in the read-time view. Identity cite is ``fp1``."""

    kind: str
    fingerprint: Fingerprint
    surface: str
    zone: str | None = None
    is_registry_kind: bool = True
    source_fp1: Fingerprint | None = None
    contract: str | None = None
    ledger_ref: str | None = None
    origin: str | None = None

    def cite(self) -> str:
        """The only legal identity cite: ``fp1`` of the source kind."""
        return self.fingerprint.value

    def fp1_identity(self) -> dict[str, object]:
        """Identity-bearing candidate fields. Package SemVer is omitted."""
        content: dict[str, object] = {
            "class": _CANDIDATE_CLASS,
            "fp1": self.fingerprint.value,
            "is_registry_kind": self.is_registry_kind,
            "kind": self.kind,
            "surface": self.surface,
        }
        if self.zone is not None:
            content["zone"] = self.zone
        if self.source_fp1 is not None:
            content["source_fp1"] = self.source_fp1.value
        if self.contract is not None:
            content["contract"] = self.contract
        if self.ledger_ref is not None:
            content["ledger_ref"] = self.ledger_ref
        if self.origin is not None:
            content["origin"] = self.origin
        return content


@dataclass(frozen=True, slots=True)
class CandidateSet:
    """Read-time retain / filter / rank view. Occupancy is a query."""

    candidates: tuple[Candidate, ...]
    predicate: Mapping[str, object]
    ranking: SweepRanking | None = None
    occupancy: str = CANDIDATE_SET_OCCUPANCY
    surfaces: tuple[str, ...] = QUERY_SURFACES
    mints_ct32: bool = False
    mints_experiment_spec: bool = False
    mints_registry_kind: bool = False
    opens_sqlite: bool = False
    reads_staging: bool = False
    persists_copied_rows: bool = False
    holds_cache: bool = False
    rank_is_sweep_rank: bool = True
    dec_0084_dead: bool = True

    def view_body(self) -> dict[str, object]:
        """Saved-view JSON body: fingerprints and predicates, never copied rows."""
        content: dict[str, object] = {
            "cites": [item.cite() for item in self.candidates],
            "class": SAVED_VIEW_CLASS,
            "method": SAVED_VIEW_METHOD,
            "occupancy": CANDIDATE_SET_OCCUPANCY,
            "predicate": dict(self.predicate),
            "surfaces": list(QUERY_SURFACES),
        }
        if self.ranking is not None:
            content["rank"] = _RANK_ENTRY
        return content

    def fp1_identity(self) -> dict[str, object]:
        """Identity-bearing candidate-set fields. Package SemVer is omitted."""
        content: dict[str, object] = {
            "candidates": [item.fp1_identity() for item in self.candidates],
            "class": CANDIDATE_SET_CLASS,
            "command": "library.candidates",
            "dec_0084_dead": True,
            "holds_cache": False,
            "mints_ct32": False,
            "mints_experiment_spec": False,
            "mints_registry_kind": False,
            "occupancy": CANDIDATE_SET_OCCUPANCY,
            "opens_sqlite": False,
            "owner": KIND_OWNER,
            "persists_copied_rows": False,
            "predicate": dict(self.predicate),
            "rank_is_sweep_rank": self.rank_is_sweep_rank,
            "reads_staging": False,
            "surfaces": list(QUERY_SURFACES),
        }
        if self.ranking is not None:
            content["ranking"] = self.ranking.fp1_identity()
        return content


@dataclass(frozen=True, slots=True)
class SavedCandidateView:
    """A candidate-set saved view. The JSON body is the durable identity."""

    home: str
    body: Mapping[str, object]
    fingerprint: Fingerprint
    path: str | None = None
    durable: bool = False
    is_library_object: bool = False

    def fp1_identity(self) -> dict[str, object]:
        """Identity-bearing saved-view fields. Package SemVer is omitted."""
        content: dict[str, object] = {
            "body": dict(self.body),
            "class": SAVED_VIEW_CLASS,
            "durable": self.durable,
            "fp1": self.fingerprint.value,
            "home": self.home,
            "is_library_object": False,
            "method": SAVED_VIEW_METHOD,
        }
        if self.path is not None:
            content["path"] = self.path
        return content


def query_candidates(
    *,
    kind: object = None,
    fp1: object = None,
    zone: object = None,
    port: object = None,
    ledger_lines: object = None,
    world: object = None,
    role: object = None,
    experiment_refs: object = None,
    lane: object = None,
    sweep_id: object = None,
    objective: object = None,
    constraints: object = None,
    direction: object = None,
    staging: object = None,
    qma_staging: object = None,
    refinement_proposals: object = None,
    persist: object = None,
    persist_candidates: object = None,
    copied_rows: object = None,
    persist_copied_rows: object = None,
    candidate_database: object = None,
    database: object = None,
    store: object = None,
    sqlite: object = None,
    databank: object = None,
    mint_registry_kind: object = None,
    registry_kind: object = None,
) -> Result[CandidateSet]:
    """Retain / filter / rank candidates as a read-time view (Story 34.3).

    Ranking, when requested, is :func:`qmb.sweep.rank.rank_sweep` — the same
    view, publishing no copied-row artifact.
    """
    copied = _requested_field(
        {
            "persist": persist,
            "persist_candidates": persist_candidates,
            "copied_rows": copied_rows,
            "persist_copied_rows": persist_copied_rows,
            "candidate_database": candidate_database,
            "database": database,
            "store": store,
            "sqlite": sqlite,
            "databank": databank,
        },
        _COPIED_ROW_FIELDS,
    )
    if copied is not None:
        return _refuse_copied_row_store(copied)
    minted = _requested_field(
        {
            "mint_registry_kind": mint_registry_kind,
            "registry_kind": registry_kind,
        },
        _REGISTRY_KIND_FIELDS,
    )
    if minted is not None:
        return _refuse_registry_kind(minted)
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
            "a candidate-set query does not read QMA staging (FR-W20, DEC-0282)",
            occupancy=CANDIDATE_SET_OCCUPANCY,
            reads_staging=False,
            persists_copied_rows=False,
            surfaces=list(QUERY_SURFACES),
            owner=KIND_OWNER,
        )
    if port is not None and not isinstance(port, RegistryReadPort):
        return invalid(
            "port",
            "the candidate-set query reads as-of through the one B-15 RegistryReadPort",
            given=repr(type(port).__name__),
        )
    zone_token = _as_zone(zone)
    if isinstance(zone_token, TypedRefusal):
        return zone_token
    kinds = _query_kinds(kind, lane=lane)
    if isinstance(kinds, TypedRefusal):
        return kinds
    hits: list[LibraryHit] = []
    for member in kinds:
        found = search_library(
            member,
            fp1=fp1,
            port=port,
            ledger_lines=ledger_lines,
            world=world,
            role=role,
            experiment_refs=experiment_refs,
            lane=lane,
        )
        if is_refusal(found):
            return found
        hits.extend(found.value.hits)
    bound = port.bound if isinstance(port, RegistryReadPort) else None
    candidates = _candidates_from_hits(tuple(hits), bound=bound, zone=zone_token)
    ranking = _rank_if_requested(
        ledger_lines,
        sweep_id=sweep_id,
        objective=objective,
        world=world,
        role=role,
        constraints=constraints,
        direction=direction,
    )
    if isinstance(ranking, TypedRefusal):
        return ranking
    predicate: dict[str, object] = {}
    if kinds != LIBRARY_KIND_NAMES and len(kinds) == 1:
        predicate["kind"] = kinds[0]
    if zone_token is not None:
        predicate["zone"] = zone_token
    wanted = _coerce_fingerprint(fp1)
    if wanted is not None:
        predicate["fp1"] = wanted.value
    elif clean_token(fp1) is not None:
        predicate["fp1"] = clean_token(fp1)
    if sweep_id is not None:
        sweep_fp = _coerce_fingerprint(sweep_id)
        sweep_token = sweep_fp.value if sweep_fp is not None else clean_token(sweep_id)
        if sweep_token is not None:
            predicate["sweep_id"] = sweep_token
    if objective is not None:
        objective_token = clean_token(objective)
        if objective_token is not None:
            predicate["objective"] = objective_token
    return Ok(
        CandidateSet(
            candidates=candidates,
            predicate=MappingProxyType(predicate),
            ranking=ranking,
        )
    )


def save_candidate_view(
    view: object = None,
    *,
    home: object,
    body: object = None,
    run_dir: object = None,
    cite: object = None,
    citation: object = None,
) -> Result[SavedCandidateView]:
    """Persist a candidate-set saved view at the FR-W24 home, or refuse.

    Ungoverned is a return value (not durable, not a Library object).
    Governed-without-QMA writes JSON in the source run-dir. Coordinated
    persistence is Epic 36. A citation without a body is not a saved view.
    """
    resolved_home = _as_home(home)
    if isinstance(resolved_home, TypedRefusal):
        return resolved_home
    if body is None and (_truthy(cite) or _truthy(citation)):
        return _refuse_citation_without_body(cite if cite is not None else citation)
    resolved_body = _as_view_body(body, view)
    if isinstance(resolved_body, TypedRefusal):
        return resolved_body
    stamped = fingerprint(resolved_body)
    if is_refusal(stamped):
        return invalid(
            "body",
            "a saved-view body must be fp1-clean JSON; a citation without a body "
            "is not a saved view (FR-W20, FR-W24)",
            cause=dict(stamped.context),
        )
    if resolved_home == HOME_COORDINATED:
        return policy(
            "home",
            "coordinated candidate-set persistence is Epic 36; this query does "
            "not open daemon sqlite and does not write analysis.published "
            "(FR-W24, DEC-0273)",
            home=HOME_COORDINATED,
            occupancy=CANDIDATE_SET_OCCUPANCY,
            opens_sqlite=False,
            persists_copied_rows=False,
            epic="36",
            dec_0084_dead=True,
        )
    if resolved_home == HOME_UNGOVERNED:
        return Ok(
            SavedCandidateView(
                home=HOME_UNGOVERNED,
                body=resolved_body,
                fingerprint=stamped.value,
                durable=False,
                is_library_object=False,
            )
        )
    return _write_governed_sidecar(resolved_body, stamped.value, run_dir)


def _query_kinds(kind: object, *, lane: object) -> tuple[str, ...] | TypedRefusal:
    if kind is None:
        kinds = LIBRARY_KIND_NAMES
        folded_lane = _fold(clean_token(lane) or "")
        if folded_lane in {_LANE_GOVERNED, _LANE_UNGOVERNED}:
            return tuple(name for name in kinds if name != _EXPERIMENT_SPEC)
        return kinds
    admitted = register_library_kind(kind, lane=lane)
    if is_refusal(admitted):
        return admitted
    return (admitted.value.kind,)


def _candidates_from_hits(
    hits: tuple[LibraryHit, ...],
    *,
    bound: object,
    zone: str | None,
) -> tuple[Candidate, ...]:
    out: list[Candidate] = []
    seen: set[tuple[str, str, str]] = set()
    ordered = sorted(hits, key=lambda hit: (hit.surface, hit.kind, hit.fingerprint.value))
    for hit in ordered:
        key = (hit.surface, hit.kind, hit.fingerprint.value)
        if key in seen:
            continue
        seen.add(key)
        record_zone, origin = _zone_and_origin(bound, hit.fingerprint)
        if zone is not None and record_zone != zone:
            continue
        out.append(
            Candidate(
                kind=hit.kind,
                fingerprint=hit.fingerprint,
                surface=hit.surface,
                zone=record_zone,
                is_registry_kind=hit.is_registry_kind,
                source_fp1=hit.source_fp1,
                contract=hit.contract,
                ledger_ref=hit.ledger_ref,
                origin=origin,
            )
        )
    return tuple(out)


def _zone_and_origin(
    bound: object,
    ref: Fingerprint,
) -> tuple[str | None, str | None]:
    getter = getattr(bound, "get", None)
    if not callable(getter):
        return None, None
    member = getter(ref)
    if not isinstance(member, RegistrationRecord):
        return None, None
    body = member.body
    origin = clean_token(body.get("origin"))
    token = clean_token(body.get("zone"))
    if token is not None:
        folded = _fold(token)
        if folded in ZONES:
            return folded, origin
    if origin is not None:
        return ZONE_DEV, origin
    return ZONE_LIVE, origin


def _rank_if_requested(
    ledger_lines: object,
    *,
    sweep_id: object,
    objective: object,
    world: object,
    role: object,
    constraints: object,
    direction: object,
) -> SweepRanking | TypedRefusal | None:
    ranking_requested = any(
        item is not None for item in (sweep_id, objective, constraints, direction)
    )
    if not ranking_requested:
        return None
    if sweep_id is None or objective is None or world is None:
        return invalid(
            "objective",
            "candidate-set rank is sweep.rank and needs sweep_id, objective, and world; "
            "it publishes no copied-row artifact (FR-W20, Story 33.2)",
            rank=_RANK_ENTRY,
            persists_copied_rows=False,
        )
    # Late import: qmb.sweep.rank → ledger.line → config.compiler → registryread.
    from qmb.ledger.line import ROLE_CONFIRMATION  # noqa: PLC0415
    from qmb.sweep.rank import RANK_DESCENDING, rank_sweep  # noqa: PLC0415

    ranked = rank_sweep(
        () if ledger_lines is None else ledger_lines,
        sweep_id=sweep_id,
        objective=objective,
        world=world,
        role=ROLE_CONFIRMATION if role is None else role,
        constraints=() if constraints is None else constraints,
        direction=RANK_DESCENDING if direction is None else direction,
    )
    if is_refusal(ranked):
        return ranked
    return ranked.value


def _as_view_body(
    body: object,
    view: object,
) -> dict[str, object] | TypedRefusal:
    if body is None:
        if isinstance(view, CandidateSet):
            return view.view_body()
        if isinstance(view, SavedCandidateView):
            return dict(view.body)
        return _refuse_citation_without_body(view)
    if isinstance(body, SavedCandidateView):
        return dict(body.body)
    if isinstance(body, CandidateSet):
        return body.view_body()
    if not isinstance(body, Mapping):
        return _refuse_citation_without_body(body)
    mapping = cast("Mapping[str, object]", body)
    if not mapping:
        return _refuse_citation_without_body("empty-body")
    method = clean_token(mapping.get("method"))
    if method is None:
        return invalid(
            "body",
            "a saved-view body is required JSON and must name method; a citation "
            "without a body is not a saved view (FR-W20, FR-W24)",
            given=repr(sorted(mapping)),
        )
    return dict(mapping)


def _write_governed_sidecar(
    body: Mapping[str, object],
    stamp: Fingerprint,
    run_dir: object,
) -> Result[SavedCandidateView]:
    token = clean_token(run_dir)
    if token is None and not isinstance(run_dir, Path):
        return invalid(
            "run_dir",
            "governed-without-QMA writes the saved-view JSON sidecar in the source "
            "run-dir (FR-W24, DEC-0273)",
            given=repr(run_dir),
            home=HOME_GOVERNED,
        )
    root = run_dir if isinstance(run_dir, Path) else Path(token or "")
    if not root.is_dir():
        return invalid(
            "run_dir",
            "governed-without-QMA writes the saved-view JSON sidecar in the source "
            "run-dir; the directory must already exist",
            given=str(root),
            home=HOME_GOVERNED,
        )
    import json  # noqa: PLC0415

    from qmb.orchestrator.paths import write_bytes_exclusive_no_follow  # noqa: PLC0415

    target = root / SAVED_VIEW_FILENAME
    payload = json.dumps(dict(body), ensure_ascii=False, sort_keys=True).encode("utf-8")
    written = write_bytes_exclusive_no_follow(
        target,
        payload,
        contain_within=root,
        field="run_dir",
    )
    if is_refusal(written):
        return written
    return Ok(
        SavedCandidateView(
            home=HOME_GOVERNED,
            body=dict(body),
            fingerprint=stamp,
            path=str(target),
            durable=True,
            is_library_object=False,
        )
    )


def _refuse_copied_row_store(field: str) -> TypedRefusal:
    return policy(
        field,
        "a candidate set is a read-time view: it does not persist copied rows, "
        "does not open a sqlite table, and does not revive DEC-0084 "
        "(FR-W20, DEC-0269, DEC-0282)",
        occupancy=CANDIDATE_SET_OCCUPANCY,
        persists_copied_rows=False,
        opens_sqlite=False,
        mints_registry_kind=False,
        reads_staging=False,
        dec_0084_dead=True,
        surfaces=list(QUERY_SURFACES),
        owner=KIND_OWNER,
        rank=_RANK_ENTRY,
    )


def _refuse_registry_kind(field: str) -> TypedRefusal:
    return policy(
        field,
        "candidates are not written into qmf-registry as a new kind; DEC-0084 "
        "stays dead (FR-W20, DEC-0269)",
        occupancy=CANDIDATE_SET_OCCUPANCY,
        mints_registry_kind=False,
        persists_copied_rows=False,
        opens_sqlite=False,
        dec_0084_dead=True,
        owner=KIND_OWNER,
        legal=list(LIBRARY_KIND_NAMES),
    )


def _refuse_citation_without_body(given: object) -> TypedRefusal:
    return policy(
        "body",
        "a citation without a body is not a saved view; the durable body is "
        "required JSON (FR-W20, FR-W24)",
        given=repr(given),
        occupancy=CANDIDATE_SET_OCCUPANCY,
        is_library_object=False,
    )


def _as_zone(value: object) -> str | TypedRefusal | None:
    if value is None:
        return None
    token = clean_token(value)
    if token is None:
        return invalid(
            "zone",
            "a candidate-set zone filter is dev or live when supplied",
            given=repr(value),
            legal=list(ZONES),
        )
    folded = _fold(token)
    if folded not in ZONES:
        return invalid(
            "zone",
            "a candidate-set zone filter is dev or live when supplied",
            given=token,
            legal=list(ZONES),
        )
    return folded


def _as_home(value: object) -> str | TypedRefusal:
    token = clean_token(value)
    if token is None:
        return invalid(
            "home",
            "a saved-view home is ungoverned, governed-without-QMA, or coordinated",
            given=repr(value),
            legal=list(SAVED_VIEW_HOMES),
        )
    folded = _fold(token)
    aliased = _HOME_ALIASES.get(folded)
    if aliased is None:
        return invalid(
            "home",
            "a saved-view home is ungoverned, governed-without-QMA, or coordinated",
            given=token,
            legal=list(SAVED_VIEW_HOMES),
        )
    return aliased


def _requested_field(fields: Mapping[str, object], names: Sequence[str]) -> str | None:
    for name in names:
        value = fields.get(name)
        if value is None or value is False:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return name
    return None


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


def _fold(token: str) -> str:
    return token.casefold().replace("_", "-").replace(" ", "-")


def _truthy(value: object) -> bool:
    if value is None or value is False:
        return False
    return not (isinstance(value, str) and value.strip() == "")
