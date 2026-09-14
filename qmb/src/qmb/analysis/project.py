"""Projection saved views over one cited CT-32 and its CT-29 stream.

``analysis.project`` is a COMP-QMB library function. It filters one cited CT-32
and its paired CT-29 stream with a permitted predicate and returns a saved view
whose durable body is the canonical JSON ``{method: projection, source_ct32,
source_ct29, predicate, as_of}``. Identity ``fp1`` is of that JSON. ``as_of`` is
the source CT-32's ``registry_as_of`` / occurrence Instant, never query time.

The view is not a CT-32: it mints no artifact, appends no QMB ledger line, mints
no ExperimentSpec successor, and consumes no ExecutionEnvironment occupancy.
Claim-class is always ``projection`` — never admission evidence, never B-4
``role=confirmation``. A citation without that JSON body is refused. A copied
trade list is not a saved view (DEC-0273, FR-W21, FR-W22, SCN-0016).

Story 35.2: a predicate or extra field that would change size, R, Book/BMS
fragments, execution ports, or ``starting_capital`` is a typed refusal naming
that axis as path-dependent (a new run, a new CT-32). This story does not
implement ``analysis.rerun``. Homes: ungoverned is a return value only (not
durable, not a Library object); governed-without-QMA writes the canonical JSON
sidecar in the source run-dir (no orchestrator spawn, no QMB ledger line, no
CT-32); coordinated ``analysis.published`` persistence is Epic 36.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import Instant
from qmf.core.fingerprint import (
    Fingerprint,
    OccurrenceRecord,
    ResultLabel,
    fingerprint,
)
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal
from qmf.risk.exit_record import ExitRecord, ExitRecordStream
from qmf.risk.performance import PerformanceResult

from qmb._refuse import clean_token, invalid, policy
from qmb.config.compiler import ResolvedRunConfig

__all__ = [
    "ANALYSIS_PROJECT_CLASS",
    "ANALYSIS_PROJECT_IS_LIBRARY_OBJECT",
    "ANALYSIS_PROJECT_MINTS_CT32",
    "ANALYSIS_PROJECT_MINTS_EXPERIMENT_SPEC",
    "ANALYSIS_PROJECT_OCCUPANCY",
    "ANALYSIS_PROJECT_OPENS_SQLITE",
    "CLAIM_CLASS_PROJECTION",
    "FORBIDDEN_PROJECTION_AXES",
    "METHOD_PROJECTION",
    "PERMITTED_PREDICATE_KEYS",
    "PROJECTION_HOMES",
    "PROJECTION_SIDECAR_FILENAME",
    "ProjectionView",
    "analysis_project_identity",
    "apply_projection_predicate",
    "cite_projection",
    "project",
]

ANALYSIS_PROJECT_CLASS: Final[str] = "qmb-projection-view"
ANALYSIS_PROJECT_OCCUPANCY: Final[str] = "query"
ANALYSIS_PROJECT_MINTS_CT32: Final[bool] = False
ANALYSIS_PROJECT_MINTS_EXPERIMENT_SPEC: Final[bool] = False
ANALYSIS_PROJECT_IS_LIBRARY_OBJECT: Final[bool] = False
ANALYSIS_PROJECT_OPENS_SQLITE: Final[bool] = False
CLAIM_CLASS_PROJECTION: Final[str] = "projection"
METHOD_PROJECTION: Final[str] = "projection"
PERMITTED_PREDICATE_KEYS: Final[tuple[str, ...]] = (
    "days",
    "exclude",
    "hours",
    "include",
    "max_trades",
    "session",
)
_AXIS_SIZE: Final[str] = "size"
_AXIS_R: Final[str] = "R"
_AXIS_BOOK: Final[str] = "Book/BMS fragments"
_AXIS_PORTS: Final[str] = "execution ports"
_AXIS_CAPITAL: Final[str] = "starting_capital"
FORBIDDEN_PROJECTION_AXES: Final[tuple[str, ...]] = (
    _AXIS_SIZE,
    _AXIS_R,
    _AXIS_BOOK,
    _AXIS_PORTS,
    _AXIS_CAPITAL,
)
_HOME_UNGOVERNED: Final[str] = "ungoverned"
_HOME_GOVERNED: Final[str] = "governed"
_HOME_COORDINATED: Final[str] = "coordinated"
PROJECTION_HOMES: Final[tuple[str, ...]] = (
    _HOME_UNGOVERNED,
    _HOME_GOVERNED,
    _HOME_COORDINATED,
)
PROJECTION_SIDECAR_FILENAME: Final[str] = "projection-view.json"

_ROLE_CONFIRMATION: Final[str] = "confirmation"
_REGISTRY_AS_OF_KEY: Final[str] = "registry_as_of"
_QMB_EXTENSIONS_KEY: Final[str] = "qmb_extensions"
_BODY_FIELDS: Final[tuple[str, ...]] = (
    "as_of",
    "method",
    "predicate",
    "source_ct29",
    "source_ct32",
)
_WEEKDAYS: Final[tuple[str, ...]] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
_REGISTRY_AS_OF_CLASS: Final[str] = "registry-as-of"
_STREAM_CLASS: Final[str] = "ct-29-stream"
_TRADE_CITE_CLASS: Final[str] = "closed-trade"

_PERMITTED_SET: Final[frozenset[str]] = frozenset(PERMITTED_PREDICATE_KEYS)
_KIND_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "day": "days",
        "days": "days",
        "exclude": "exclude",
        "hour": "hours",
        "hours": "hours",
        "hours-of-day": "hours",
        "include": "include",
        "max-trades": "max_trades",
        "max_trades": "max_trades",
        "session": "session",
        "session-window": "session",
        "session_window": "session",
    }
)
_FORBIDDEN_AXES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "binding_seed": _AXIS_CAPITAL,
        "bms": _AXIS_BOOK,
        "bms_fragment": _AXIS_BOOK,
        "bms_fragments": _AXIS_BOOK,
        "bms_fp1": _AXIS_BOOK,
        "book": _AXIS_BOOK,
        "book_bms": _AXIS_BOOK,
        "book_fragment": _AXIS_BOOK,
        "book_fragments": _AXIS_BOOK,
        "book_fp1": _AXIS_BOOK,
        "cost_port": _AXIS_PORTS,
        "cost_ports": _AXIS_PORTS,
        "execution_port": _AXIS_PORTS,
        "execution_ports": _AXIS_PORTS,
        "fill_port": _AXIS_PORTS,
        "fill_ports": _AXIS_PORTS,
        "financing_port": _AXIS_PORTS,
        "financing_ports": _AXIS_PORTS,
        "lot": _AXIS_SIZE,
        "lot_size": _AXIS_SIZE,
        "lots": _AXIS_SIZE,
        "port": _AXIS_PORTS,
        "ports": _AXIS_PORTS,
        "position_size": _AXIS_SIZE,
        "r": _AXIS_R,
        "r_multiple": _AXIS_R,
        "rescale": _AXIS_SIZE,
        "risk_r": _AXIS_R,
        "seed_capital": _AXIS_CAPITAL,
        "size": _AXIS_SIZE,
        "size_rescale": _AXIS_SIZE,
        "starting_capital": _AXIS_CAPITAL,
        "starting_equity": _AXIS_CAPITAL,
    }
)
_HOME_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "analysis_published": _HOME_COORDINATED,
        "coordinated": _HOME_COORDINATED,
        "epic_36": _HOME_COORDINATED,
        "governed": _HOME_GOVERNED,
        "governed_without_qma": _HOME_GOVERNED,
        "in_process": _HOME_UNGOVERNED,
        "library": _HOME_UNGOVERNED,
        "return_value": _HOME_UNGOVERNED,
        "sidecar": _HOME_GOVERNED,
        "ungoverned": _HOME_UNGOVERNED,
    }
)
_SPAWN_FIELDS: Final[tuple[str, ...]] = (
    "orchestrator",
    "spawn",
    "spawn_orchestrator",
    "spawn_run",
)
_TRADE_LIST_KEYS: Final[tuple[str, ...]] = (
    "copied_trade_list",
    "copied_trades",
    "trade_list",
    "trades",
)
_LEDGER_FIELDS: Final[tuple[str, ...]] = ("append_ledger", "ledger", "ledger_line")
_CT32_FIELDS: Final[tuple[str, ...]] = ("mint_ct32", "new_ct32")
_SPEC_FIELDS: Final[tuple[str, ...]] = (
    "experiment_spec",
    "mint_experiment_spec",
    "successor",
)
_SQLITE_FIELDS: Final[tuple[str, ...]] = ("daemon_sqlite", "database", "sqlite")
_TRADE_LIST_FIELDS: Final[tuple[str, ...]] = _TRADE_LIST_KEYS
_OCCUPANCY_RUN_TOKENS: Final[frozenset[str]] = frozenset({"job", "run"})


@dataclass(frozen=True, slots=True)
class ProjectionView:
    """A projection saved view. Identity ``fp1`` is of the canonical JSON body."""

    source_ct32: str
    source_ct29: str
    predicate: Mapping[str, object]
    as_of: Mapping[str, object]
    fingerprint: Fingerprint
    matched_count: int = 0
    claim_class: str = CLAIM_CLASS_PROJECTION
    occupancy: str = ANALYSIS_PROJECT_OCCUPANCY
    mints_ct32: bool = False
    mints_experiment_spec: bool = False
    is_admission_evidence: bool = False
    b4_role: str | None = None
    home: str = _HOME_UNGOVERNED
    durable: bool = False
    is_library_object: bool = False
    path: str | None = None
    opens_sqlite: bool = False
    spawns_orchestrator: bool = False
    appends_ledger: bool = False

    @property
    def method(self) -> str:
        """Always ``projection`` — this is not a CT-32 and not a rerun."""
        return METHOD_PROJECTION

    def body(self) -> dict[str, object]:
        """Canonical saved-view JSON. Never a copied trade list."""
        return {
            "as_of": dict(self.as_of),
            "method": METHOD_PROJECTION,
            "predicate": dict(self.predicate),
            "source_ct29": self.source_ct29,
            "source_ct32": self.source_ct32,
        }

    def fp1_identity(self) -> dict[str, object]:
        """Identity content IS the canonical JSON (DEC-0273)."""
        return self.body()


def analysis_project_identity() -> dict[str, object]:
    """Identity-bearing analysis.project fields. Package SemVer is omitted."""
    return {
        "claim_class": CLAIM_CLASS_PROJECTION,
        "class": ANALYSIS_PROJECT_CLASS,
        "command": "analysis.project",
        "forbidden_axes": list(FORBIDDEN_PROJECTION_AXES),
        "homes": list(PROJECTION_HOMES),
        "is_admission_evidence": False,
        "is_library_object": ANALYSIS_PROJECT_IS_LIBRARY_OBJECT,
        "method": METHOD_PROJECTION,
        "mints_ct32": ANALYSIS_PROJECT_MINTS_CT32,
        "mints_experiment_spec": ANALYSIS_PROJECT_MINTS_EXPERIMENT_SPEC,
        "occupancy": ANALYSIS_PROJECT_OCCUPANCY,
        "opens_sqlite": ANALYSIS_PROJECT_OPENS_SQLITE,
        "permitted_predicates": list(PERMITTED_PREDICATE_KEYS),
        "sidecar_filename": PROJECTION_SIDECAR_FILENAME,
        "spawns_orchestrator": False,
        "ungoverned_durable": False,
    }


def project(
    *,
    source_ct32: object = None,
    source_ct29: object = None,
    predicate: object = None,
    as_of: object = None,
    config: object = None,
    body: object = None,
    cite: object = None,
    trades: object = None,
    trade_list: object = None,
    copied_trades: object = None,
    copied_trade_list: object = None,
    occupancy: object = None,
    ledger: object = None,
    append_ledger: object = None,
    ledger_line: object = None,
    mint_ct32: object = None,
    new_ct32: object = None,
    experiment_spec: object = None,
    successor: object = None,
    mint_experiment_spec: object = None,
    sqlite: object = None,
    database: object = None,
    daemon_sqlite: object = None,
    role: object = None,
    b4_role: object = None,
    admission: object = None,
    admission_evidence: object = None,
    claim_class: object = None,
    hours: object = None,
    days: object = None,
    session: object = None,
    max_trades: object = None,
    include: object = None,
    exclude: object = None,
    home: object = None,
    run_dir: object = None,
    spawn: object = None,
    orchestrator: object = None,
    spawn_run: object = None,
    spawn_orchestrator: object = None,
    **extra: object,
) -> Result[ProjectionView]:
    """Filter one cited CT-32 and its CT-29 stream into a projection saved view.

    Occupancy is a query. The durable body is the canonical JSON; ``fp1`` is of
    that JSON. QMA must call this function (or the thin door) and must not
    reimplement the filter. Forbidden axes are path-dependent (Story 35.2).
    """
    extra_blocked = _refuse_forbidden_fields(extra)
    if extra_blocked is not None:
        return extra_blocked
    spawn_blocked = _refuse_spawn(
        spawn=spawn,
        orchestrator=orchestrator,
        spawn_run=spawn_run,
        spawn_orchestrator=spawn_orchestrator,
    )
    if spawn_blocked is not None:
        return spawn_blocked
    if body is not None or cite is not None:
        cited = cite_projection(
            body=body,
            cite=cite,
            trades=trades,
            trade_list=trade_list,
            copied_trades=copied_trades,
            copied_trade_list=copied_trade_list,
        )
        if is_refusal(cited):
            return cited
        return _place_view(
            cited.value,
            home=home,
            run_dir=run_dir,
            source_ct32=source_ct32,
        )
    blocked = _refuse_side_effects(
        occupancy=occupancy,
        ledger=ledger,
        append_ledger=append_ledger,
        ledger_line=ledger_line,
        mint_ct32=mint_ct32,
        new_ct32=new_ct32,
        experiment_spec=experiment_spec,
        successor=successor,
        mint_experiment_spec=mint_experiment_spec,
        sqlite=sqlite,
        database=database,
        daemon_sqlite=daemon_sqlite,
        role=role,
        b4_role=b4_role,
        admission=admission,
        admission_evidence=admission_evidence,
        claim_class=claim_class,
        trades=trades,
        trade_list=trade_list,
        copied_trades=copied_trades,
        copied_trade_list=copied_trade_list,
    )
    if blocked is not None:
        return blocked
    resolved_predicate = _predicate_from_parts(
        predicate,
        hours=hours,
        days=days,
        session=session,
        max_trades=max_trades,
        include=include,
        exclude=exclude,
    )
    if is_refusal(resolved_predicate):
        return resolved_predicate
    source = _resolve_source_ct32(source_ct32)
    if is_refusal(source):
        return source
    ct32_fp, identity, trade_refs, input_fps = source.value
    as_of_identity = _resolve_as_of(
        as_of,
        config=config,
        source_ct32=source_ct32,
        input_fps=input_fps,
        identity=identity,
    )
    if is_refusal(as_of_identity):
        return as_of_identity
    ct29 = _resolve_source_ct29(source_ct29, trade_refs=trade_refs)
    if is_refusal(ct29):
        return ct29
    cite_token, records = ct29.value
    matched = apply_projection_predicate(records, resolved_predicate.value)
    if is_refusal(matched):
        return matched
    body_json = {
        "as_of": dict(as_of_identity.value),
        "method": METHOD_PROJECTION,
        "predicate": dict(resolved_predicate.value),
        "source_ct29": cite_token,
        "source_ct32": ct32_fp.value,
    }
    stamped = fingerprint(body_json)
    if is_refusal(stamped):
        return stamped
    view = ProjectionView(
        source_ct32=ct32_fp.value,
        source_ct29=cite_token,
        predicate=resolved_predicate.value,
        as_of=as_of_identity.value,
        fingerprint=stamped.value,
        matched_count=len(matched.value),
    )
    return _place_view(
        view,
        home=home,
        run_dir=run_dir,
        source_ct32=source_ct32,
    )


def cite_projection(
    *,
    body: object = None,
    cite: object = None,
    trades: object = None,
    trade_list: object = None,
    copied_trades: object = None,
    copied_trade_list: object = None,
) -> Result[ProjectionView]:
    """Treat a citation as a saved view only when the canonical JSON body is present.

    A citation without that body is refused. A copied trade list is not a saved
    view (FR-W22).
    """
    listed = _requested_field(
        {
            "copied_trade_list": copied_trade_list,
            "copied_trades": copied_trades,
            "trade_list": trade_list,
            "trades": trades,
        },
        _TRADE_LIST_FIELDS,
    )
    if listed is not None:
        return _refuse_copied_trade_list(listed)
    if body is None and cite is None:
        return invalid(
            "body",
            "a projection saved view is the canonical JSON "
            "{method: projection, source_ct32, source_ct29, predicate, as_of}",
        )
    if body is None:
        return policy(
            "body",
            "a citation of a projection without that JSON body is not a saved view; "
            "the durable body is the canonical JSON "
            "{method: projection, source_ct32, source_ct29, predicate, as_of} "
            "(FR-W22, DEC-0273)",
            given=repr(cite),
            occupancy=ANALYSIS_PROJECT_OCCUPANCY,
            mints_ct32=False,
            mints_experiment_spec=False,
            claim_class=CLAIM_CLASS_PROJECTION,
        )
    if isinstance(body, ProjectionView):
        return Ok(body)
    if not isinstance(body, Mapping) or isinstance(body, (str, bytes)):
        if isinstance(body, Sequence):
            return _refuse_copied_trade_list("body")
        return policy(
            "body",
            "a citation of a projection without that JSON body is not a saved view; "
            "the durable body is the canonical JSON "
            "{method: projection, source_ct32, source_ct29, predicate, as_of} "
            "(FR-W22, DEC-0273)",
            given=repr(type(body).__name__),
            occupancy=ANALYSIS_PROJECT_OCCUPANCY,
            mints_ct32=False,
        )
    mapping = cast("Mapping[str, object]", body)
    if not mapping:
        return policy(
            "body",
            "a citation of a projection without that JSON body is not a saved view; "
            "the durable body is the canonical JSON "
            "{method: projection, source_ct32, source_ct29, predicate, as_of} "
            "(FR-W22, DEC-0273)",
            given="empty-body",
            occupancy=ANALYSIS_PROJECT_OCCUPANCY,
            mints_ct32=False,
        )
    copied = [key for key in _TRADE_LIST_KEYS if key in mapping]
    if copied:
        return _refuse_copied_trade_list(copied[0])
    extra = [key for key in mapping if key not in _BODY_FIELDS]
    if extra:
        return invalid(
            "body",
            "a projection saved-view body is exactly "
            "{method: projection, source_ct32, source_ct29, predicate, as_of}; "
            "a copied trade list is not a saved view (FR-W22, DEC-0273)",
            extra=sorted(extra),
        )
    missing = [field for field in _BODY_FIELDS if field not in mapping]
    if missing:
        return policy(
            "body",
            "a citation of a projection without that JSON body is not a saved view; "
            "the durable body is the canonical JSON "
            "{method: projection, source_ct32, source_ct29, predicate, as_of} "
            "(FR-W22, DEC-0273)",
            missing=missing,
            occupancy=ANALYSIS_PROJECT_OCCUPANCY,
            mints_ct32=False,
        )
    method = clean_token(mapping.get("method"))
    if method != METHOD_PROJECTION:
        return invalid(
            "method",
            "a projection saved view carries method: projection",
            given=repr(mapping.get("method")),
            expected=METHOD_PROJECTION,
        )
    source_ct32 = clean_token(mapping.get("source_ct32"))
    source_ct29 = clean_token(mapping.get("source_ct29"))
    if source_ct32 is None or source_ct29 is None:
        return invalid(
            "body",
            "source_ct32 and source_ct29 are non-blank cites of the source stream",
        )
    as_of_raw = mapping.get("as_of")
    if not isinstance(as_of_raw, Mapping):
        return invalid(
            "as_of",
            "as_of is the source CT-32's registry_as_of Instant identity, never query time",
            given=repr(type(as_of_raw).__name__),
        )
    predicate_raw = mapping.get("predicate")
    canonical = _canonicalize_predicate(predicate_raw)
    if is_refusal(canonical):
        return canonical
    body_json = {
        "as_of": dict(cast("Mapping[str, object]", as_of_raw)),
        "method": METHOD_PROJECTION,
        "predicate": dict(canonical.value),
        "source_ct29": source_ct29,
        "source_ct32": source_ct32,
    }
    stamped = fingerprint(body_json)
    if is_refusal(stamped):
        return stamped
    return Ok(
        ProjectionView(
            source_ct32=source_ct32,
            source_ct29=source_ct29,
            predicate=canonical.value,
            as_of=dict(cast("Mapping[str, object]", as_of_raw)),
            fingerprint=stamped.value,
        )
    )


def apply_projection_predicate(
    stream: object,
    predicate: object,
) -> Result[tuple[object, ...]]:
    """Apply one permitted predicate to a CT-29 / ClosedTrade stream.

    The filter lives once here. Doors wrap it; QMA must not reimplement it.
    """
    canonical = _canonicalize_predicate(predicate)
    if is_refusal(canonical):
        return canonical
    rows = _coerce_stream_rows(stream)
    if is_refusal(rows):
        return rows
    pred = canonical.value
    hours = pred.get("hours")
    days = pred.get("days")
    session = pred.get("session")
    include = pred.get("include")
    exclude = pred.get("exclude")
    cap = pred.get("max_trades")
    include_set = set(cast("list[str]", include)) if isinstance(include, list) else None
    exclude_set = set(cast("list[str]", exclude)) if isinstance(exclude, list) else None
    day_set = set(cast("list[str]", days)) if isinstance(days, list) else None
    matched: list[object] = []
    for row in rows.value:
        hour, weekday = _utc_hour_and_weekday(row.recorded_at)
        if hours is not None and not _hour_in_window(hour, hours):
            continue
        if session is not None and not _hour_in_window(hour, session):
            continue
        if day_set is not None and _WEEKDAYS[weekday] not in day_set:
            continue
        if include_set is not None and row.cite not in include_set:
            continue
        if exclude_set is not None and row.cite in exclude_set:
            continue
        matched.append(row.record)
        if isinstance(cap, int) and len(matched) >= cap:
            break
    return Ok(tuple(matched))


@dataclass(frozen=True, slots=True)
class _StreamRow:
    cite: str
    recorded_at: Instant
    record: object


def _predicate_from_parts(
    predicate: object,
    *,
    hours: object,
    days: object,
    session: object,
    max_trades: object,
    include: object,
    exclude: object,
) -> Result[dict[str, object]]:
    if predicate is not None:
        return _canonicalize_predicate(predicate)
    parts: dict[str, object] = {}
    if hours is not None:
        parts["hours"] = hours
    if days is not None:
        parts["days"] = days
    if session is not None:
        parts["session"] = session
    if max_trades is not None:
        parts["max_trades"] = max_trades
    if include is not None:
        parts["include"] = include
    if exclude is not None:
        parts["exclude"] = exclude
    return _canonicalize_predicate(parts)


def _canonicalize_predicate(raw: object) -> Result[dict[str, object]]:
    if raw is None:
        return invalid(
            "predicate",
            "analysis.project requires a permitted predicate "
            "(hours/days/session window, max-trades cap, include/exclude filter)",
            legal=list(PERMITTED_PREDICATE_KEYS),
        )
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError as exc:
                return invalid(
                    "predicate",
                    "a predicate JSON string is canonical JSON of a permitted predicate",
                    given=type(exc).__name__,
                )
            return _canonicalize_predicate(parsed)
        return invalid(
            "predicate",
            "a predicate is a mapping of permitted keys, not a bare string",
            given=repr(raw),
            legal=list(PERMITTED_PREDICATE_KEYS),
        )
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        merged: dict[str, object] = {}
        for index, item in enumerate(cast("Sequence[object]", raw)):
            part = _canonicalize_predicate(item)
            if is_refusal(part):
                return part
            overlap = [key for key in part.value if key in merged]
            if overlap:
                return invalid(
                    "predicate",
                    "a sequence of predicates is AND-combined; duplicate keys are refused",
                    index=index,
                    overlap=overlap,
                )
            merged.update(part.value)
        if not merged:
            return invalid(
                "predicate",
                "analysis.project requires a permitted predicate "
                "(hours/days/session window, max-trades cap, include/exclude filter)",
                legal=list(PERMITTED_PREDICATE_KEYS),
            )
        return Ok(merged)
    if not isinstance(raw, Mapping):
        return invalid(
            "predicate",
            "a predicate is a mapping of permitted keys "
            "(hours/days/session window, max-trades cap, include/exclude)",
            given=repr(type(raw).__name__),
            legal=list(PERMITTED_PREDICATE_KEYS),
        )
    mapping = {str(key): value for key, value in cast("Mapping[object, object]", raw).items()}
    kind_token = clean_token(mapping.pop("kind", None))
    if kind_token is not None:
        folded = _KIND_ALIASES.get(_fold(kind_token))
        if folded is None:
            forbidden = _forbidden_axis(kind_token)
            if forbidden is not None:
                return _refuse_forbidden_axis(forbidden, field=kind_token)
            return invalid(
                "predicate",
                "a permitted predicate kind is hours, days, session, max_trades, "
                "include, or exclude",
                given=kind_token,
                legal=list(PERMITTED_PREDICATE_KEYS),
            )
        if folded not in mapping:
            if folded in {"hours", "session"}:
                mapping[folded] = {
                    key: mapping.pop(key) for key in ("start", "end", "name") if key in mapping
                }
            elif folded == "days" and "days" not in mapping:
                mapping["days"] = mapping.pop("value", mapping.pop("day", ()))
            elif folded == "max_trades" and "max_trades" not in mapping:
                mapping["max_trades"] = mapping.pop("value", mapping.pop("max-trades", None))
            elif folded in {"include", "exclude"} and folded not in mapping:
                mapping[folded] = mapping.pop("value", mapping.pop("ids", ()))
    copied = [key for key in _TRADE_LIST_KEYS if key in mapping]
    if copied:
        return _refuse_copied_trade_list(copied[0])
    for key in mapping:
        forbidden = _forbidden_axis(key)
        if forbidden is not None:
            return _refuse_forbidden_axis(forbidden, field=str(key))
    folded_keys = {_fold(key): key for key in mapping}
    unknown = [folded_keys[key] for key in folded_keys if key not in _PERMITTED_SET]
    if unknown:
        return invalid(
            "predicate",
            "permitted predicates are hours/days/session windows, max-trades caps, "
            "and include/exclude filters (DEC-0273)",
            given=sorted(unknown),
            legal=list(PERMITTED_PREDICATE_KEYS),
        )
    canonical: dict[str, object] = {}
    if "hours" in folded_keys:
        window = _coerce_hour_window(mapping[folded_keys["hours"]], field="hours")
        if is_refusal(window):
            return window
        canonical["hours"] = window.value
    if "session" in folded_keys:
        window = _coerce_hour_window(mapping[folded_keys["session"]], field="session")
        if is_refusal(window):
            return window
        canonical["session"] = window.value
    if "days" in folded_keys:
        days = _coerce_days(mapping[folded_keys["days"]])
        if is_refusal(days):
            return days
        canonical["days"] = days.value
    if "max_trades" in folded_keys:
        cap = _coerce_max_trades(mapping[folded_keys["max_trades"]])
        if is_refusal(cap):
            return cap
        canonical["max_trades"] = cap.value
    if "include" in folded_keys:
        ids = _coerce_id_list(mapping[folded_keys["include"]], field="include")
        if is_refusal(ids):
            return ids
        canonical["include"] = ids.value
    if "exclude" in folded_keys:
        ids = _coerce_id_list(mapping[folded_keys["exclude"]], field="exclude")
        if is_refusal(ids):
            return ids
        canonical["exclude"] = ids.value
    if not canonical:
        return invalid(
            "predicate",
            "analysis.project requires a permitted predicate "
            "(hours/days/session window, max-trades cap, include/exclude filter)",
            legal=list(PERMITTED_PREDICATE_KEYS),
        )
    return Ok(canonical)


def _resolve_source_ct32(
    source: object,
) -> Result[tuple[Fingerprint, dict[str, object] | None, tuple[str, ...], tuple[Fingerprint, ...]]]:
    if source is None:
        return invalid(
            "source_ct32",
            "analysis.project cites one completed CT-32 performance-result",
        )
    if isinstance(source, Fingerprint):
        return Ok((source, None, (), ()))
    token = clean_token(source)
    if token is not None and token.startswith("fp1:"):
        parsed = Fingerprint.try_create(token)
        if is_ok(parsed):
            return Ok((parsed.value, None, (), ()))
        return parsed
    if isinstance(source, PerformanceResult):
        stamped = source.fingerprint()
        if is_refusal(stamped):
            return stamped
        return Ok(
            (
                stamped.value,
                dict(source.fp1_identity()),
                tuple(source.trade_event_references),
                tuple(source.result_label.input_fingerprints),
            )
        )
    from qmb.results.ct32 import as_ct32_artifact  # noqa: PLC0415 — avoid qmb package cycle

    artifact = as_ct32_artifact(source)
    if is_refusal(artifact):
        if token is not None:
            return invalid(
                "source_ct32",
                "analysis.project cites one completed CT-32 performance-result "
                "(artifact, stored JSON, run directory, or fp1)",
                given=token,
            )
        return artifact
    body = artifact.value
    identity = {key: value for key, value in body.items() if key != _QMB_EXTENSIONS_KEY}
    stamped = fingerprint(identity)
    if is_refusal(stamped):
        return stamped
    refs = _trade_refs_from_body(body)
    inputs = _input_fingerprints_from_body(body)
    if is_refusal(inputs):
        return inputs
    return Ok((stamped.value, identity, refs, inputs.value))


def _resolve_source_ct29(
    source: object,
    *,
    trade_refs: tuple[str, ...],
) -> Result[tuple[str, tuple[object, ...]]]:
    if source is None:
        if trade_refs:
            return Ok((trade_refs[0], ()))
        return invalid(
            "source_ct29",
            "analysis.project cites the paired CT-29 stream of the source CT-32",
        )
    if isinstance(source, Fingerprint):
        return Ok((source.value, ()))
    token = clean_token(source)
    if token is not None and not token.startswith("{") and not token.startswith("["):
        return Ok((token, ()))
    if isinstance(source, ExitRecordStream):
        records = source.records()
        cite = _stream_cite(records, trade_refs=trade_refs)
        if is_refusal(cite):
            return cite
        return Ok((cite.value, records))
    if isinstance(source, Mapping) and not isinstance(source, (str, bytes)):
        mapping = cast("Mapping[str, object]", source)
        if "trades" in mapping and mapping.get("method") is None:
            return _refuse_copied_trade_list("trades")
        cite_token = clean_token(
            mapping.get("source_ct29", mapping.get("cite", mapping.get("fp1")))
        )
        records_raw = mapping.get("records", mapping.get("stream"))
        if records_raw is None:
            if cite_token is None:
                return invalid(
                    "source_ct29",
                    "a CT-29 cite is an fp1, a ct-13:ct-29: reference, or a record stream",
                )
            return Ok((cite_token, ()))
        rows = _records_only(records_raw)
        if is_refusal(rows):
            return rows
        if cite_token is None:
            cited = _stream_cite(rows.value, trade_refs=trade_refs)
            if is_refusal(cited):
                return cited
            cite_token = cited.value
        elif trade_refs and cite_token not in trade_refs:
            return invalid(
                "source_ct29",
                "the CT-29 cite must pair with the source CT-32 trade-event reference",
                given=cite_token,
                paired=list(trade_refs),
            )
        return Ok((cite_token, rows.value))
    if isinstance(source, Sequence) and not isinstance(source, (str, bytes)):
        rows = _records_only(cast("Sequence[object]", source))
        if is_refusal(rows):
            return rows
        cited = _stream_cite(rows.value, trade_refs=trade_refs)
        if is_refusal(cited):
            return cited
        return Ok((cited.value, rows.value))
    return invalid(
        "source_ct29",
        "analysis.project cites the paired CT-29 stream (records, ExitRecordStream, "
        "or a ct-13:ct-29: / fp1 cite)",
        given=repr(type(source).__name__),
    )


def _resolve_as_of(
    as_of: object,
    *,
    config: object,
    source_ct32: object,
    input_fps: tuple[Fingerprint, ...],
    identity: dict[str, object] | None,
) -> Result[dict[str, object]]:
    instant = _coerce_as_of_instant(as_of)
    if isinstance(instant, TypedRefusal):
        return instant
    if instant is None:
        instant = _as_of_from_config(config)
    if instant is None:
        instant = _as_of_from_config(source_ct32)
    if instant is None:
        instant = _as_of_from_identity(identity)
    if instant is None:
        return invalid(
            "as_of",
            "as_of is the source CT-32's registry_as_of / occurrence Instant, "
            "never query time (DEC-0273)",
        )
    recipe = fingerprint(
        {
            "class": _REGISTRY_AS_OF_CLASS,
            "registry_as_of": instant.fp1_identity(),
        }
    )
    if is_refusal(recipe):
        return recipe
    if input_fps and recipe.value not in input_fps:
        return policy(
            "as_of",
            "as_of is the source CT-32's registry_as_of / occurrence, never query time (DEC-0273)",
            occupancy=ANALYSIS_PROJECT_OCCUPANCY,
            mints_ct32=False,
        )
    return Ok(dict(instant.fp1_identity()))


def _coerce_as_of_instant(value: object) -> Instant | TypedRefusal | None:
    if value is None:
        return None
    if isinstance(value, OccurrenceRecord):
        return value.ran_at
    if isinstance(value, Instant):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        created = Instant.try_create(value)
        if is_refusal(created):
            return created
        return created.value
    if isinstance(value, Mapping):
        body = cast("Mapping[str, object]", value)
        raw = body.get("value_ns", body.get("registry_as_of", body.get("ran_at")))
        if isinstance(raw, Instant):
            return raw
        if isinstance(raw, Mapping):
            nested = cast("Mapping[str, object]", raw)
            return _coerce_as_of_instant(nested.get("value_ns"))
        if raw is not None:
            return _coerce_as_of_instant(raw)
        return invalid(
            "as_of",
            "as_of is the source CT-32's registry_as_of Instant identity, never query time",
            given=repr(sorted(body)),
        )
    attribute = getattr(value, "registry_as_of", None)
    if attribute is not None:
        return _coerce_as_of_instant(attribute)
    ran_at = getattr(value, "ran_at", None)
    if isinstance(ran_at, Instant):
        return ran_at
    return invalid(
        "as_of",
        "as_of is the source CT-32's registry_as_of / occurrence Instant, never query time",
        given=repr(type(value).__name__),
    )


def _as_of_from_config(config: object) -> Instant | None:
    if isinstance(config, ResolvedRunConfig):
        return _instant_from_raw(config.keys.get(_REGISTRY_AS_OF_KEY))
    keys = getattr(config, "keys", None)
    if isinstance(keys, Mapping):
        return _instant_from_raw(cast("Mapping[str, object]", keys).get(_REGISTRY_AS_OF_KEY))
    if isinstance(config, Mapping):
        mapping = cast("Mapping[str, object]", config)
        nested = mapping.get("keys")
        if isinstance(nested, Mapping):
            found = _instant_from_raw(cast("Mapping[str, object]", nested).get(_REGISTRY_AS_OF_KEY))
            if found is not None:
                return found
        return _instant_from_raw(mapping.get(_REGISTRY_AS_OF_KEY))
    attribute = getattr(config, "registry_as_of", None)
    return _instant_from_raw(attribute)


def _as_of_from_identity(identity: dict[str, object] | None) -> Instant | None:
    if identity is None:
        return None
    return _instant_from_raw(identity.get(_REGISTRY_AS_OF_KEY))


def _instant_from_raw(raw: object) -> Instant | None:
    if raw is None:
        return None
    coerced = _coerce_as_of_instant(raw)
    if isinstance(coerced, Instant):
        return coerced
    return None


def _input_fingerprints_from_body(body: Mapping[str, object]) -> Result[tuple[Fingerprint, ...]]:
    label = body.get("result_label")
    if isinstance(label, ResultLabel):
        return Ok(tuple(label.input_fingerprints))
    if not isinstance(label, Mapping):
        return Ok(())
    raw = cast("Mapping[str, object]", label).get("input_fingerprints")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return Ok(())
    out: list[Fingerprint] = []
    for item in cast("Sequence[object]", raw):
        if isinstance(item, Fingerprint):
            out.append(item)
            continue
        token = clean_token(item)
        if token is None:
            continue
        parsed = Fingerprint.try_create(token)
        if is_ok(parsed):
            out.append(parsed.value)
    return Ok(tuple(out))


def _trade_refs_from_body(body: Mapping[str, object]) -> tuple[str, ...]:
    extensions = body.get(_QMB_EXTENSIONS_KEY)
    if isinstance(extensions, Mapping):
        raw = cast("Mapping[str, object]", extensions).get("trade_event_references")
        return _as_tokens(raw)
    return _as_tokens(body.get("trade_event_references"))


def _as_tokens(value: object) -> tuple[str, ...]:
    if isinstance(value, str) and value.strip() != "":
        return (value,)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    out: list[str] = []
    for item in cast("Sequence[object]", value):
        token = clean_token(item)
        if token is not None:
            out.append(token)
    return tuple(out)


def _stream_cite(
    records: tuple[object, ...],
    *,
    trade_refs: tuple[str, ...],
) -> Result[str]:
    if trade_refs:
        return Ok(trade_refs[0])
    cites: list[str] = []
    for record in records:
        row = _as_stream_row(record)
        if is_refusal(row):
            return row
        cites.append(row.value.cite)
    stamped = fingerprint({"class": _STREAM_CLASS, "records": cites})
    if is_refusal(stamped):
        return stamped
    return Ok(stamped.value.value)


def _records_only(value: object) -> Result[tuple[object, ...]]:
    from qmb.results.measures import ClosedTrade  # noqa: PLC0415 — avoid qmb package cycle

    if isinstance(value, ExitRecordStream):
        return Ok(value.records())
    if isinstance(value, (ExitRecord, ClosedTrade)):
        return Ok((value,))
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            "source_ct29",
            "a CT-29 stream is a sequence of ExitRecord or ClosedTrade values",
            given=repr(type(value).__name__),
        )
    return Ok(tuple(cast("Sequence[object]", value)))


def _coerce_stream_rows(stream: object) -> Result[tuple[_StreamRow, ...]]:
    records = _records_only(stream)
    if is_refusal(records):
        return records
    rows: list[_StreamRow] = []
    for index, item in enumerate(records.value):
        row = _as_stream_row(item)
        if is_refusal(row):
            return invalid(
                "source_ct29",
                "each CT-29 row is an ExitRecord or ClosedTrade with a recorded Instant",
                index=index,
                given=repr(type(item).__name__),
            )
        rows.append(row.value)
    return Ok(tuple(rows))


def _as_stream_row(record: object) -> Result[_StreamRow]:
    from qmb.results.measures import ClosedTrade  # noqa: PLC0415 — avoid qmb package cycle

    if isinstance(record, ExitRecord):
        stamped = record.fingerprint()
        if is_refusal(stamped):
            return stamped
        return Ok(_StreamRow(stamped.value.value, record.recorded_at, record))
    if isinstance(record, ClosedTrade):
        stamped = fingerprint(
            {
                "class": _TRADE_CITE_CLASS,
                "closed_at": record.closed_at.fp1_identity(),
                "fees": record.fees.fp1_identity(),
                "realized_pnl": record.realized_pnl.fp1_identity(),
                "side": record.side.value,
            }
        )
        if is_refusal(stamped):
            return stamped
        return Ok(_StreamRow(stamped.value.value, record.closed_at, record))
    if isinstance(record, Mapping):
        mapping = cast("Mapping[str, object]", record)
        instant = _instant_from_raw(
            mapping.get("recorded_at", mapping.get("closed_at", mapping.get("at")))
        )
        if instant is None:
            return invalid(
                "recorded_at",
                "a CT-29 mapping row carries recorded_at / closed_at as an Instant",
            )
        cite = clean_token(mapping.get("cite", mapping.get("fp1", mapping.get("id"))))
        if cite is None:
            stamped = fingerprint(
                {
                    "class": _TRADE_CITE_CLASS,
                    "recorded_at": instant.fp1_identity(),
                }
            )
            if is_refusal(stamped):
                return stamped
            cite = stamped.value.value
        return Ok(_StreamRow(cite, instant, mapping))
    return invalid(
        "source_ct29",
        "each CT-29 row is an ExitRecord or ClosedTrade",
        given=repr(type(record).__name__),
    )


def _coerce_hour_window(value: object, *, field: str) -> Result[dict[str, object]]:
    if isinstance(value, str):
        token = value.strip()
        if "-" in token:
            left, right = token.split("-", 1)
            return _coerce_hour_window({"start": left.strip(), "end": right.strip()}, field=field)
        return invalid(
            field,
            "a hours/session window is {start, end} UTC hours or a 'start-end' token; "
            "QMB does not invent a market-hours calendar (DEC-0106)",
            given=token,
        )
    if isinstance(value, int) and not isinstance(value, bool):
        return _coerce_hour_window({"start": value, "end": value + 1}, field=field)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        sequence = cast("Sequence[object]", value)
        if len(sequence) == 2:
            return _coerce_hour_window({"start": sequence[0], "end": sequence[1]}, field=field)
    if not isinstance(value, Mapping):
        return invalid(
            field,
            "a hours/session window is a caller-declared UTC {start, end} range; "
            "QMB does not invent a market-hours calendar (DEC-0106)",
            given=repr(type(cast("object", value)).__name__),
        )
    mapping = cast("Mapping[str, object]", value)
    start = _as_hour(mapping.get("start"), field=field)
    if is_refusal(start):
        return start
    end = _as_hour(mapping.get("end"), field=field)
    if is_refusal(end):
        return end
    window: dict[str, object] = {"end": end.value, "start": start.value}
    name = clean_token(mapping.get("name"))
    if name is not None:
        window["name"] = name
    return Ok(window)


def _as_hour(value: object, *, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        token = clean_token(value)
        if token is None or not token.isdigit():
            return invalid(
                field,
                "a window bound is a UTC hour in 0..24",
                given=repr(value),
            )
        value = int(token)
    if value < 0 or value > 24:
        return invalid(field, "a window bound is a UTC hour in 0..24", given=repr(value))
    return Ok(value)


def _coerce_days(value: object) -> Result[list[str]]:
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        value = (value,)
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return invalid(
            "days",
            "days is a sequence of weekday names (monday..sunday) or 0..6",
            given=repr(type(value).__name__),
        )
    out: list[str] = []
    seen: set[str] = set()
    for item in cast("Sequence[object]", value):
        name = _as_weekday(item)
        if is_refusal(name):
            return name
        if name.value not in seen:
            seen.add(name.value)
            out.append(name.value)
    out.sort()
    if not out:
        return invalid("days", "days names at least one weekday", legal=list(_WEEKDAYS))
    return Ok(out)


def _as_weekday(value: object) -> Result[str]:
    if isinstance(value, int) and not isinstance(value, bool):
        if 0 <= value <= 6:
            return Ok(_WEEKDAYS[value])
        return invalid("days", "a weekday index is 0..6 (monday..sunday)", given=repr(value))
    token = clean_token(value)
    if token is None:
        return invalid("days", "a weekday is a name (monday..sunday) or 0..6", given=repr(value))
    folded = _fold(token)
    if folded in _WEEKDAYS:
        return Ok(folded)
    return invalid(
        "days",
        "a weekday is a name (monday..sunday) or 0..6",
        given=token,
        legal=list(_WEEKDAYS),
    )


def _coerce_max_trades(value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return invalid(
            "max_trades",
            "a max-trades cap is a positive integer",
            given=repr(value),
        )
    return Ok(value)


def _coerce_id_list(value: object, *, field: str) -> Result[list[str]]:
    if isinstance(value, (str, Fingerprint)):
        value = (value,)
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return invalid(
            field,
            "include/exclude is a sequence of trade cites (fp1)",
            given=repr(type(value).__name__),
        )
    out: list[str] = []
    seen: set[str] = set()
    for item in cast("Sequence[object]", value):
        token = item.value if isinstance(item, Fingerprint) else clean_token(item)
        if token is None:
            return invalid(
                field,
                "each include/exclude cite is a non-blank fp1 token",
                given=repr(item),
            )
        if token not in seen:
            seen.add(token)
            out.append(token)
    out.sort()
    return Ok(out)


def _hour_in_window(hour: int, window: object) -> bool:
    if not isinstance(window, Mapping):
        return False
    body = cast("Mapping[str, object]", window)
    start = body.get("start")
    end = body.get("end")
    if not isinstance(start, int) or not isinstance(end, int):
        return False
    if start == end:
        return hour == start % 24
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def _utc_hour_and_weekday(instant: Instant) -> tuple[int, int]:
    seconds = instant.value_ns // 1_000_000_000
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return dt.hour, dt.weekday()


def _refuse_side_effects(
    **fields: object,
) -> TypedRefusal | None:
    occupancy = fields.get("occupancy")
    if occupancy is not None:
        token = _fold(clean_token(occupancy) or "")
        if token in _OCCUPANCY_RUN_TOKENS:
            return policy(
                "occupancy",
                "analysis.project is a query: it consumes no ExecutionEnvironment occupancy, "
                "mints no CT-32, and mints no ExperimentSpec successor (FR-W11, DEC-0276)",
                occupancy=ANALYSIS_PROJECT_OCCUPANCY,
                mints_ct32=False,
                mints_experiment_spec=False,
                claim_class=CLAIM_CLASS_PROJECTION,
            )
    listed = _requested_field(
        {name: fields.get(name) for name in _TRADE_LIST_FIELDS},
        _TRADE_LIST_FIELDS,
    )
    if listed is not None:
        return _refuse_copied_trade_list(listed)
    ledger = _requested_field({name: fields.get(name) for name in _LEDGER_FIELDS}, _LEDGER_FIELDS)
    if ledger is not None:
        return policy(
            ledger,
            "analysis.project appends no QMB ledger line; it is a saved view, not a run "
            "(FR-W21, DEC-0273)",
            occupancy=ANALYSIS_PROJECT_OCCUPANCY,
            mints_ct32=False,
            mints_experiment_spec=False,
            claim_class=CLAIM_CLASS_PROJECTION,
        )
    minted = _requested_field({name: fields.get(name) for name in _CT32_FIELDS}, _CT32_FIELDS)
    if minted is not None:
        return policy(
            minted,
            "analysis.project mints no CT-32; the durable body is saved-view JSON "
            "(FR-W21, DEC-0273)",
            occupancy=ANALYSIS_PROJECT_OCCUPANCY,
            mints_ct32=False,
            mints_experiment_spec=False,
            claim_class=CLAIM_CLASS_PROJECTION,
        )
    spec = _requested_field({name: fields.get(name) for name in _SPEC_FIELDS}, _SPEC_FIELDS)
    if spec is not None:
        return policy(
            spec,
            "analysis.project mints no ExperimentSpec successor; it is a query (FR-W11, DEC-0276)",
            occupancy=ANALYSIS_PROJECT_OCCUPANCY,
            mints_ct32=False,
            mints_experiment_spec=False,
        )
    sqlite = _requested_field({name: fields.get(name) for name in _SQLITE_FIELDS}, _SQLITE_FIELDS)
    if sqlite is not None:
        return policy(
            sqlite,
            "analysis.project does not open daemon sqlite; coordinated persistence is Epic 36 "
            "(FR-W24, DEC-0273)",
            occupancy=ANALYSIS_PROJECT_OCCUPANCY,
            opens_sqlite=False,
            mints_ct32=False,
        )
    role = fields.get("role", fields.get("b4_role"))
    role_token = _fold(clean_token(role) or "") if role is not None else ""
    if role_token == _ROLE_CONFIRMATION:
        return policy(
            "role",
            "claim-class is projection — never admission evidence, never B-4 "
            "role=confirmation (FR-W21, FR-W28, SCN-0016)",
            claim_class=CLAIM_CLASS_PROJECTION,
            is_admission_evidence=False,
            b4_role=None,
            occupancy=ANALYSIS_PROJECT_OCCUPANCY,
        )
    if fields.get("admission") is not None or fields.get("admission_evidence") is not None:
        return policy(
            "admission",
            "claim-class is projection — never admission evidence, never B-4 "
            "role=confirmation (FR-W21, FR-W28, SCN-0016)",
            claim_class=CLAIM_CLASS_PROJECTION,
            is_admission_evidence=False,
            b4_role=None,
        )
    claim = clean_token(fields.get("claim_class"))
    if claim is not None and _fold(claim) != CLAIM_CLASS_PROJECTION:
        return policy(
            "claim_class",
            "analysis.project claim-class is always projection (FR-W21, DEC-0273)",
            given=claim,
            claim_class=CLAIM_CLASS_PROJECTION,
            is_admission_evidence=False,
        )
    return None


def _refuse_copied_trade_list(field: str) -> TypedRefusal:
    return policy(
        field,
        "a copied trade list is not a saved view; the durable body is the canonical JSON "
        "{method: projection, source_ct32, source_ct29, predicate, as_of} (FR-W22, DEC-0273)",
        occupancy=ANALYSIS_PROJECT_OCCUPANCY,
        mints_ct32=False,
        claim_class=CLAIM_CLASS_PROJECTION,
    )


def _refuse_forbidden_axis(axis: str, *, field: str = "predicate") -> TypedRefusal:
    return policy(
        field,
        f"{axis} is forbidden as projection: that change is path-dependent "
        "(a new run, a new CT-32 via analysis.rerun) (FR-W23, SCN-0016 Branch A, DEC-0273)",
        axis=axis,
        path_dependent=True,
        occupancy=ANALYSIS_PROJECT_OCCUPANCY,
        mints_ct32=False,
        implements_rerun=False,
        spawns_orchestrator=False,
        legal=list(PERMITTED_PREDICATE_KEYS),
    )


def _forbidden_axis(key: object) -> str | None:
    token = _fold(clean_token(key) or "")
    return _FORBIDDEN_AXES.get(token)


def _refuse_forbidden_fields(fields: Mapping[str, object]) -> TypedRefusal | None:
    unknown: list[str] = []
    for name, value in fields.items():
        if value is None:
            continue
        axis = _forbidden_axis(name)
        if axis is not None:
            return _refuse_forbidden_axis(axis, field=name)
        unknown.append(name)
    if unknown:
        return invalid(
            unknown[0],
            "analysis.project extra fields that would change size, R, Book/BMS "
            "fragments, execution ports, or starting_capital are path-dependent; "
            "other extra fields are not a permitted predicate "
            "(FR-W23, SCN-0016 Branch A, DEC-0273)",
            given=unknown[0],
            extra=unknown,
            legal=list(PERMITTED_PREDICATE_KEYS),
            forbidden_axes=list(FORBIDDEN_PROJECTION_AXES),
        )
    return None


def _refuse_spawn(**fields: object) -> TypedRefusal | None:
    listed = _requested_field(fields, _SPAWN_FIELDS)
    if listed is None:
        return None
    return policy(
        listed,
        "analysis.project does not spawn an orchestrator and does not implement "
        "analysis.rerun; a path-dependent change is a new run, a new CT-32 "
        "(FR-W23, FR-W24, Story 35.3)",
        occupancy=ANALYSIS_PROJECT_OCCUPANCY,
        mints_ct32=False,
        spawns_orchestrator=False,
        implements_rerun=False,
        appends_ledger=False,
    )


def _place_view(
    view: ProjectionView,
    *,
    home: object,
    run_dir: object,
    source_ct32: object,
) -> Result[ProjectionView]:
    resolved = _as_home(home)
    if isinstance(resolved, TypedRefusal):
        return resolved
    if resolved == _HOME_COORDINATED:
        return policy(
            "home",
            "coordinated analysis.published persistence is Epic 36; "
            "analysis.project does not open daemon sqlite (FR-W24, DEC-0273)",
            home=_HOME_COORDINATED,
            occupancy=ANALYSIS_PROJECT_OCCUPANCY,
            opens_sqlite=False,
            mints_ct32=False,
            spawns_orchestrator=False,
            appends_ledger=False,
            epic="36",
        )
    if resolved == _HOME_UNGOVERNED:
        return Ok(
            replace(
                view,
                home=_HOME_UNGOVERNED,
                durable=False,
                is_library_object=False,
                path=None,
                opens_sqlite=False,
                spawns_orchestrator=False,
                appends_ledger=False,
            )
        )
    return _write_governed_sidecar(view, run_dir=run_dir, source_ct32=source_ct32)


def _as_home(value: object) -> str | TypedRefusal:
    if value is None:
        return _HOME_UNGOVERNED
    token = clean_token(value)
    if token is None:
        return invalid(
            "home",
            "a projection saved-view home is ungoverned, governed-without-QMA, or coordinated",
            given=repr(value),
            legal=list(PROJECTION_HOMES),
        )
    aliased = _HOME_ALIASES.get(_fold(token))
    if aliased is None:
        return invalid(
            "home",
            "a projection saved-view home is ungoverned, governed-without-QMA, or coordinated",
            given=token,
            legal=list(PROJECTION_HOMES),
        )
    return aliased


def _write_governed_sidecar(
    view: ProjectionView,
    *,
    run_dir: object,
    source_ct32: object,
) -> Result[ProjectionView]:
    root = _resolve_governed_run_dir(run_dir, source_ct32)
    if is_refusal(root):
        return root
    from qmb.orchestrator.paths import write_bytes_exclusive_no_follow  # noqa: PLC0415

    target = root.value / PROJECTION_SIDECAR_FILENAME
    payload = json.dumps(view.body(), ensure_ascii=False, sort_keys=True).encode("utf-8")
    written = write_bytes_exclusive_no_follow(
        target,
        payload,
        contain_within=root.value,
        field="run_dir",
    )
    if is_refusal(written):
        return written
    return Ok(
        replace(
            view,
            home=_HOME_GOVERNED,
            durable=True,
            is_library_object=False,
            path=str(target),
            opens_sqlite=False,
            spawns_orchestrator=False,
            appends_ledger=False,
        )
    )


def _resolve_governed_run_dir(run_dir: object, source_ct32: object) -> Result[Path]:
    if run_dir is not None:
        return _as_existing_run_dir(run_dir)
    inferred = _infer_run_dir(source_ct32)
    if inferred is not None:
        return Ok(inferred)
    return invalid(
        "run_dir",
        "governed-without-QMA writes the saved-view JSON sidecar in the source "
        "run-dir (FR-W24, DEC-0273)",
        home=_HOME_GOVERNED,
        mints_ct32=False,
        spawns_orchestrator=False,
        appends_ledger=False,
    )


def _as_existing_run_dir(run_dir: object) -> Result[Path]:
    if isinstance(run_dir, Path):
        root = run_dir
    else:
        token = clean_token(run_dir)
        if token is None:
            return invalid(
                "run_dir",
                "governed-without-QMA writes the saved-view JSON sidecar in the source "
                "run-dir (FR-W24, DEC-0273)",
                given=repr(run_dir),
                home=_HOME_GOVERNED,
            )
        root = Path(token)
    if not root.is_dir():
        return invalid(
            "run_dir",
            "governed-without-QMA writes the saved-view JSON sidecar in the source "
            "run-dir; the directory must already exist (no new orchestrator spawn)",
            given=str(root),
            home=_HOME_GOVERNED,
            spawns_orchestrator=False,
            mints_ct32=False,
        )
    return Ok(root)


def _infer_run_dir(source: object) -> Path | None:
    output = getattr(source, "output_dir", None)
    if output is not None:
        token = output if isinstance(output, Path) else clean_token(output)
        if isinstance(token, Path) and token.is_dir():
            return token
        if isinstance(token, str):
            path = Path(token)
            if path.is_dir():
                return path
    if isinstance(source, Path):
        return _run_dir_from_path(source)
    token = clean_token(source)
    if token is not None:
        return _run_dir_from_path(Path(token))
    return None


def _run_dir_from_path(path: Path) -> Path | None:
    if path.is_dir():
        return path
    if not path.is_file():
        return None
    from qmb.results.ct32 import CT32_ARTIFACT_NAME, RESULTS_DIR_NAME  # noqa: PLC0415

    if path.name == CT32_ARTIFACT_NAME and path.parent.name == RESULTS_DIR_NAME:
        root = path.parent.parent
        return root if root.is_dir() else None
    parent = path.parent
    return parent if parent.is_dir() else None


def _requested_field(values: Mapping[str, object], names: Sequence[str]) -> str | None:
    for name in names:
        item = values.get(name)
        if item is None or item is False:
            continue
        if item in ("", ()):
            continue
        return name
    return None


def _fold(token: str) -> str:
    return token.strip().replace("-", "_").replace(" ", "_").casefold()
