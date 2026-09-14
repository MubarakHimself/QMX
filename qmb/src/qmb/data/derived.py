"""Derived datasets, frozen data_ref, and quality read models (Story 33.3).

Data commands stay thin fronts over qmf-data rooms (B-11). A derived dataset is
a new fingerprinted artifact with a CT-07 lineage edge — never a Library kind
and never a vendor-style timezone clone that auto-updates the source under a
running experiment. Quality surfaces are read models over CT-13 ``data quality``
events and ``gap_check`` reports, not ``analysis.project`` and not a new COMP.
CSV/file import, if requested as a store, is refused: it is a CT-15 adapter
extend. ExperimentSpec ``data_ref`` (coordinated) and governed run-config cite
frozen CT-12 split fingerprints (FR-W30, FR-W31, DEC-0281).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import WriterId
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal
from qmf.data.journal import JournalEvent, JournalEventType
from qmf.data.splits import SplitManifest
from qmf.registry import EdgeType, LineageEdge

from qmb._refuse import invalid, policy

__all__ = [
    "CSV_IMPORT_CONTRACT",
    "DERIVED_DATASET_CLASS",
    "DERIVED_IS_LIBRARY_KIND",
    "DERIVED_LINEAGE_EDGE_TYPE",
    "QUALITY_SURFACE_CLASS",
    "QUALITY_SURFACE_OCCUPANCY",
    "DerivedDataset",
    "QualitySurface",
    "cite_frozen_data_ref",
    "derived_identity",
    "guard_data_door",
    "materialize_derived_dataset",
    "quality_surface",
]

DERIVED_DATASET_CLASS: Final[str] = "qmb-derived-dataset"
DERIVED_IS_LIBRARY_KIND: Final[bool] = False
DERIVED_LINEAGE_EDGE_TYPE: Final[EdgeType] = EdgeType.OCCURRENCE_OF
QUALITY_SURFACE_CLASS: Final[str] = "qmb-data-quality-surface"
QUALITY_SURFACE_OCCUPANCY: Final[str] = "query"
CSV_IMPORT_CONTRACT: Final[str] = "CT-15"
_ROOM_MACHINERY: Final[str] = "qmf-data"
_DATA_QUALITY: Final[str] = JournalEventType.DATA_QUALITY.value
_CLONE_FIELDS: Final[tuple[str, ...]] = (
    "timezone_clone",
    "auto_update",
    "auto_update_source",
    "clone_timezone",
    "vendor_clone",
    "sync_clone",
)
_STORE_FIELDS: Final[tuple[str, ...]] = (
    "clone_store",
    "cdn",
    "cdn_product",
    "second_catalog",
    "new_store",
)
_CSV_IMPORT_FIELDS: Final[tuple[str, ...]] = (
    "csv_store",
    "file_store",
    "csv",
    "csv_path",
    "file_path",
    "import_csv",
    "file_import",
)
_LIBRARY_FIELDS: Final[tuple[str, ...]] = ("library_kind", "register_library")
_LIVE_TOKENS: Final[frozenset[str]] = frozenset({"latest", "live", "head", "auto"})


@dataclass(frozen=True, slots=True)
class DerivedDataset:
    """Fingerprinted derived-room artifact with a CT-07 edge to its source."""

    fingerprint: Fingerprint
    source_room_fp1: Fingerprint
    lineage: LineageEdge
    transform: Mapping[str, object]
    is_library_kind: bool = False
    auto_updates_source: bool = False
    room_machinery: str = _ROOM_MACHINERY

    def fp1_identity(self) -> dict[str, object]:
        """Identity-bearing derived-dataset fields. Package SemVer is omitted."""
        return {
            "auto_updates_source": False,
            "class": DERIVED_DATASET_CLASS,
            "fingerprint": self.fingerprint.value,
            "is_library_kind": False,
            "lineage_edge_type": self.lineage.edge_type.value,
            "room_machinery": self.room_machinery,
            "source_room_fp1": self.source_room_fp1.value,
            "transform": dict(self.transform),
        }


@dataclass(frozen=True, slots=True)
class QualitySurface:
    """Read model over CT-13 data-quality events and a gap_check report."""

    events: tuple[Mapping[str, object], ...]
    gap_check: Mapping[str, object] | None
    occupancy: str = QUALITY_SURFACE_OCCUPANCY
    mints_ct32: bool = False
    mints_experiment_spec: bool = False
    is_analysis_project: bool = False

    def fp1_identity(self) -> dict[str, object]:
        """Identity-bearing quality-surface fields. Package SemVer is omitted."""
        return {
            "class": QUALITY_SURFACE_CLASS,
            "event_count": len(self.events),
            "gap_check": dict(self.gap_check) if self.gap_check is not None else None,
            "is_analysis_project": False,
            "mints_ct32": False,
            "mints_experiment_spec": False,
            "occupancy": QUALITY_SURFACE_OCCUPANCY,
        }


def derived_identity() -> dict[str, object]:
    """Identity-bearing derived-dataset / quality-surface fields."""
    return {
        "csv_import_contract": CSV_IMPORT_CONTRACT,
        "csv_import_is_new_store": False,
        "data_ref_cites": "CT-12",
        "derived_auto_updates_source": False,
        "derived_dataset_class": DERIVED_DATASET_CLASS,
        "derived_is_library_kind": DERIVED_IS_LIBRARY_KIND,
        "derived_lineage_edge_type": DERIVED_LINEAGE_EDGE_TYPE.value,
        "derived_room_machinery": _ROOM_MACHINERY,
        "quality_is_analysis_project": False,
        "quality_occupancy": QUALITY_SURFACE_OCCUPANCY,
        "quality_surface_class": QUALITY_SURFACE_CLASS,
        "timezone_clone_auto_update": False,
    }


def guard_data_door(command: object, provided: object = None) -> Result[None]:
    """Refuse clone stores, auto-updating timezone clones, and Library mints."""
    _ = command
    resources: Mapping[str, object]
    if provided is None:
        resources = {}
    elif isinstance(provided, Mapping):
        resources = cast("Mapping[str, object]", provided)
    else:
        return invalid(
            "provided",
            "data-door policy resources are a key->value mapping",
            given=repr(type(provided).__name__),
        )
    clone_field = _requested_field(resources, _CLONE_FIELDS)
    if clone_field is not None:
        return _refuse_timezone_clone(clone_field)
    store_field = _requested_field(resources, _STORE_FIELDS)
    if store_field is not None:
        return _refuse_clone_store(store_field)
    csv_field = _requested_field(resources, _CSV_IMPORT_FIELDS)
    if csv_field is not None and resources.get("adapter") is None:
        return _refuse_csv_store(csv_field)
    library_field = _requested_field(resources, _LIBRARY_FIELDS)
    if library_field is not None:
        return policy(
            library_field,
            "a derived dataset is a fingerprinted qmf-data artifact with a CT-07 "
            "lineage edge; it is not a Library kind (FR-W31, FR-W18, DEC-0271)",
            is_library_kind=False,
            mints_ct32=False,
            mints_experiment_spec=False,
        )
    if _truthy(resources.get("analysis_project")) or resources.get("analysis_method") == (
        "analysis.project"
    ):
        return policy(
            "analysis_project",
            "quality surfaces are read models over CT-13 data quality events and "
            "gap_check reports — not analysis.project views and not a new COMP "
            "(FR-W30, DEC-0281); analysis.project is Epic 35",
            occupancy=QUALITY_SURFACE_OCCUPANCY,
            is_analysis_project=False,
            mints_ct32=False,
            mints_experiment_spec=False,
        )
    return Ok(None)


def materialize_derived_dataset(
    *,
    source_room_fp1: object = None,
    writer: object = None,
    transform: object = None,
    library_kind: object = False,
    auto_update: object = False,
    timezone_clone: object = False,
) -> Result[DerivedDataset]:
    """Mint a fingerprinted derived artifact with a CT-07 lineage edge.

    Existing qmf-data room machinery; new as-of. Not a Library kind, not a
    CT-10, not a CT-32, not a QMB sidecar, and never an auto-updating clone.
    """
    guarded = guard_data_door(
        "derive",
        {
            "library_kind": library_kind,
            "auto_update": auto_update,
            "timezone_clone": timezone_clone,
        },
    )
    if is_refusal(guarded):
        return guarded
    source = _as_fingerprint(source_room_fp1, field="source_room_fp1")
    if is_refusal(source):
        return source
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "a derived dataset lineage edge carries a WriterId",
            given=repr(type(writer).__name__),
        )
    body: Mapping[str, object]
    if transform is None:
        body = MappingProxyType({})
    elif isinstance(transform, Mapping):
        body = MappingProxyType(dict(cast("Mapping[str, object]", transform)))
    else:
        return invalid(
            "transform",
            "a derived-dataset transform is a key->value mapping",
            given=repr(type(transform).__name__),
        )
    stamped = fingerprint(
        {
            "class": DERIVED_DATASET_CLASS,
            "is_library_kind": False,
            "room_machinery": _ROOM_MACHINERY,
            "source_room_fp1": source.value.value,
            "transform": dict(body),
        }
    )
    if is_refusal(stamped):
        return stamped
    edge = LineageEdge.try_create(
        DERIVED_LINEAGE_EDGE_TYPE,
        stamped.value,
        source.value,
        writer,
    )
    if is_refusal(edge):
        return edge
    return Ok(
        DerivedDataset(
            fingerprint=stamped.value,
            source_room_fp1=source.value,
            lineage=edge.value,
            transform=body,
        )
    )


def quality_surface(
    *,
    events: object = (),
    gap_check: object = None,
    analysis_project: object = False,
    analysis_method: object = None,
) -> Result[QualitySurface]:
    """Fold CT-13 data-quality events and a gap_check report as a query."""
    guarded = guard_data_door(
        "quality",
        {"analysis_project": analysis_project, "analysis_method": analysis_method},
    )
    if is_refusal(guarded):
        return guarded
    rows = _quality_events(events)
    if is_refusal(rows):
        return rows
    report = _gap_check_mapping(gap_check)
    if is_refusal(report):
        return report
    return Ok(QualitySurface(events=rows.value, gap_check=report.value))


def cite_frozen_data_ref(
    data_ref: object,
    *,
    auto_update: object = False,
    timezone_clone: object = False,
    clone: object = False,
) -> Result[Fingerprint]:
    """Cite a frozen CT-12 split fingerprint; refuse auto-updating clones."""
    guarded = guard_data_door(
        "data_ref",
        {
            "auto_update": auto_update,
            "timezone_clone": timezone_clone,
            "vendor_clone": clone,
        },
    )
    if is_refusal(guarded):
        return guarded
    if isinstance(data_ref, str) and data_ref.strip().lower() in _LIVE_TOKENS:
        return _refuse_timezone_clone("data_ref")
    if isinstance(data_ref, SplitManifest):
        return Ok(data_ref.fingerprint)
    return _as_fingerprint(data_ref, field="data_ref")


def _refuse_timezone_clone(field: str) -> TypedRefusal:
    return policy(
        field,
        "vendor-style timezone clones that auto-update the source under a running "
        "experiment are refused; ExperimentSpec data_ref (coordinated) and governed "
        "run-config cite frozen CT-12 split fingerprints (FR-W31, DEC-0281)",
        auto_updates_source=False,
        data_ref_cites="CT-12",
        mints_ct32=False,
        mints_experiment_spec=False,
    )


def _refuse_clone_store(field: str) -> TypedRefusal:
    return policy(
        field,
        "qmb data commands wrap qmf-data rooms; no clone store, CDN product, or "
        "second catalog is minted (FR-W30, DEC-0281)",
        csv_import_contract=CSV_IMPORT_CONTRACT,
        mints_ct32=False,
        mints_experiment_spec=False,
    )


def _refuse_csv_store(field: str) -> TypedRefusal:
    return policy(
        field,
        "CSV/file import is a CT-15 adapter extend, not a new store (FR-W30)",
        csv_import_contract=CSV_IMPORT_CONTRACT,
        csv_import_is_new_store=False,
        mints_ct32=False,
        mints_experiment_spec=False,
    )


def _requested_field(resources: Mapping[str, object], fields: Sequence[str]) -> str | None:
    for name in fields:
        if _truthy(resources.get(name)):
            return name
    return None


def _truthy(value: object) -> bool:
    if value is None or value is False:
        return False
    return not (isinstance(value, str) and value.strip() == "")


def _as_fingerprint(value: object, *, field: str) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return Ok(parsed.value)
    return invalid(
        field,
        "ExperimentSpec data_ref (coordinated) and governed run-config cite frozen "
        "CT-12 split fingerprints — never a live or auto-updating clone (FR-W31)",
        given=repr(value),
        data_ref_cites="CT-12",
    )


def _quality_events(events: object) -> Result[tuple[Mapping[str, object], ...]]:
    if events is None:
        return Ok(())
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        return invalid(
            "events",
            "quality events are a sequence of CT-13 data-quality records",
            given=repr(type(events).__name__),
        )
    rows: list[Mapping[str, object]] = []
    for item in cast("Sequence[object]", events):
        extracted = _as_quality_event(item)
        if extracted is None:
            continue
        rows.append(extracted)
    return Ok(tuple(rows))


def _as_quality_event(item: object) -> Mapping[str, object] | None:
    if isinstance(item, JournalEvent):
        if item.event_type is not JournalEventType.DATA_QUALITY:
            return None
        return item.fp1_identity()
    if not isinstance(item, Mapping):
        return None
    body = cast("Mapping[str, object]", item)
    token = body.get("event_type")
    label = token.value if isinstance(token, JournalEventType) else token
    if label != _DATA_QUALITY:
        return None
    return dict(body)


def _gap_check_mapping(report: object) -> Result[Mapping[str, object] | None]:
    if report is None:
        empty: Mapping[str, object] | None = None
        return Ok(empty)
    as_mapping = getattr(report, "as_mapping", None)
    if callable(as_mapping):
        mapped = as_mapping()
        if isinstance(mapped, Mapping):
            return Ok(dict(cast("Mapping[str, object]", mapped)))
        return invalid(
            "gap_check",
            "a gap_check report mapping is a key->value mapping",
            given=repr(type(mapped).__name__),
        )
    if isinstance(report, Mapping):
        return Ok(dict(cast("Mapping[str, object]", report)))
    return invalid(
        "gap_check",
        "quality surfaces fold a gap_check report or its mapping",
        given=repr(type(report).__name__),
    )
