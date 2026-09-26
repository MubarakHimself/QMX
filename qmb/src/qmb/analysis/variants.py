"""Book/BMS variants are complete dev-zone candidates plus replay (Story 35.4).

A proposed Book or BMS is a complete new fingerprinted CT-22 / CT-27 document
registered in the registry ``dev`` zone — never a patch record or partial
overlay posing as a definition (FR-W27, DEC-0274, SCN-0016). Shape owner
stays ``COMP-QMF-RISK``; the CT-06 envelope is minted at the composition root
through ``qmf.registry.RegistrationRecord`` — this module does not move mint
into QMB or QMA (AR-W04).

Evaluation of that candidate ``fp1`` is ``analysis.rerun`` citing the
definition fingerprint. Trade-list rescaling is not Book/BMS truth.

QMA-emitted candidates remain ``money_path_relevant`` with a field-level diff
in ``approval_request`` (Story 45.6 / FR-Q53). QMA never fills an unset
money-path field. This library validates that contract without importing
``qma`` (QMA must call the door; it must not reimplement the filter).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import Instant, WriterId
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal
from qmf.registry import RegistrationRecord
from qmf.risk.templates import BmsDefinition, BookDefinition

from qmb._refuse import clean_token, invalid, policy, unavailable
from qmb.analysis.rerun import RerunOutcome, rerun
from qmb.config.compiler import ResolvedRunConfig
from qmb.config.dummy import refuse_dummy_definition
from qmb.config.fragments import (
    BMS_RECORD_KIND,
    BOOK_RECORD_KIND,
    ConfigFragment,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.registryread.candidates import ZONE_DEV, ZONE_LIVE
from qmb.registryread.port import RegistryReadPort

__all__ = [
    "ANALYSIS_VARIANT_CLASS",
    "BOOK_BMS_MINT_SURFACE",
    "BOOK_BMS_SHAPE_OWNER",
    "MONEY_PATH_FIELD_DIFF_SCHEMA",
    "MONEY_PATH_RELEVANT_FIELDS",
    "QMA_CANDIDATE_ORIGIN",
    "VARIANT_ZONE",
    "BookBmsVariant",
    "book_bms_variant_identity",
    "evaluate_book_bms_variant",
    "register_book_bms_variant",
]

ANALYSIS_VARIANT_CLASS: Final[str] = "qmb-book-bms-variant"
BOOK_BMS_SHAPE_OWNER: Final[str] = "COMP-QMF-RISK"
BOOK_BMS_MINT_SURFACE: Final[str] = "composition-root"
VARIANT_ZONE: Final[str] = ZONE_DEV
QMA_CANDIDATE_ORIGIN: Final[str] = "qma"
# Named qma-wire schema (Story 45.6). Cited, never reimplemented as a second schema.
MONEY_PATH_FIELD_DIFF_SCHEMA: Final[str] = "qma.wire.money_path_field_diff.v1"
MONEY_PATH_RELEVANT_FIELDS: Final[frozenset[str]] = frozenset(
    {"binding", "exit", "priority", "protection", "risk", "sizing"}
)

_BOOK_CLASS: Final[str] = "book-definition"
_BMS_CLASS: Final[str] = "bms-definition"
_CONTRACT_BY_KIND: Final[Mapping[str, str]] = MappingProxyType(
    {BOOK_RECORD_KIND: "CT-22", BMS_RECORD_KIND: "CT-27"}
)
_DEFINITION_IDENTITY_KEYS: Final[tuple[str, ...]] = (
    "accounting_currency",
    "class",
    "contract_format_version",
    "sections",
)
_PATCH_FIELDS: Final[tuple[str, ...]] = (
    "delta",
    "field_patch",
    "overlay",
    "partial",
    "partial_overlay",
    "patch",
)
_RESCALE_FIELDS: Final[tuple[str, ...]] = (
    "copied_trades",
    "mm_simulator",
    "rescale",
    "size_rescale",
    "trade_list",
    "trade_list_rescale",
    "trades",
)
_MINT_OWNERS: Final[frozenset[str]] = frozenset(
    {
        "comp-qma",
        "comp-qmb",
        "qma",
        "qmb",
    }
)
_QMA_ORIGINS: Final[frozenset[str]] = frozenset({"qma", "qma-daemon", "qma-core"})
_OCCURRENCE_BODY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "approval_request",
        "money_path_relevant",
        "origin",
        "predecessor_fp1",
        "zone",
    }
)


@dataclass(frozen=True, slots=True)
class BookBmsVariant:
    """A complete CT-22/CT-27 document registered in the registry ``dev`` zone."""

    kind: str
    contract: str
    definition_fp1: Fingerprint
    record: RegistrationRecord
    zone: str = VARIANT_ZONE
    shape_owner: str = BOOK_BMS_SHAPE_OWNER
    mint: str = BOOK_BMS_MINT_SURFACE
    origin: str | None = None
    money_path_relevant: bool = False
    approval_request: Mapping[str, object] | None = None

    def cite(self) -> str:
        """The candidate identity cite: the complete CT-22/CT-27 ``fp1``."""
        return self.definition_fp1.value

    def fp1_identity(self) -> dict[str, object]:
        """Identity-bearing variant fields. Package SemVer is omitted."""
        content: dict[str, object] = {
            "class": ANALYSIS_VARIANT_CLASS,
            "contract": self.contract,
            "fp1": self.definition_fp1.value,
            "kind": self.kind,
            "mint": BOOK_BMS_MINT_SURFACE,
            "money_path_relevant": self.money_path_relevant,
            "record_fp1": self.record.stable_id.value,
            "shape_owner": BOOK_BMS_SHAPE_OWNER,
            "zone": VARIANT_ZONE,
        }
        if self.origin is not None:
            content["origin"] = self.origin
        return content


def book_bms_variant_identity() -> dict[str, object]:
    """Identity-bearing Book/BMS-variant fields. Package SemVer is omitted."""
    return {
        "class": ANALYSIS_VARIANT_CLASS,
        "evaluation": "analysis.rerun",
        "mint": BOOK_BMS_MINT_SURFACE,
        "money_path_field_diff_schema": MONEY_PATH_FIELD_DIFF_SCHEMA,
        "qma_fills_unset_money_path_fields": False,
        "shape_owner": BOOK_BMS_SHAPE_OWNER,
        "trade_list_rescale_is_book_truth": False,
        "zone": VARIANT_ZONE,
    }


def register_book_bms_variant(
    *,
    definition: object = None,
    book: object = None,
    bms: object = None,
    writer: object = None,
    created_at: object = None,
    sequence: object = 0,
    origin: object = None,
    money_path_relevant: object = None,
    approval_request: object = None,
    predecessor: object = None,
    ancestor: object = None,
    shape_owner: object = None,
    mint: object = None,
    mint_into: object = None,
    zone: object = None,
    patch: object = None,
    overlay: object = None,
    partial: object = None,
    delta: object = None,
    field_patch: object = None,
    partial_overlay: object = None,
    fragment: object = None,
    trades: object = None,
    trade_list: object = None,
    copied_trades: object = None,
    rescale: object = None,
    size_rescale: object = None,
    mm_simulator: object = None,
    trade_list_rescale: object = None,
    **extra: object,
) -> Result[BookBmsVariant]:
    """Register a complete CT-22/CT-27 document in the registry ``dev`` zone.

    The shape is a ``qmf.risk`` Book/BMS definition. The CT-06 envelope is
    minted through ``qmf.registry.RegistrationRecord`` at the composition root.
    """
    blocked = _refuse_definition_abuses(
        extra=extra,
        patch=patch,
        overlay=overlay,
        partial=partial,
        delta=delta,
        field_patch=field_patch,
        partial_overlay=partial_overlay,
        fragment=fragment,
        trades=trades,
        trade_list=trade_list,
        copied_trades=copied_trades,
        rescale=rescale,
        size_rescale=size_rescale,
        mm_simulator=mm_simulator,
        trade_list_rescale=trade_list_rescale,
        mint=mint,
        mint_into=mint_into,
        shape_owner=shape_owner,
        zone=zone,
    )
    if blocked is not None:
        return blocked
    chosen = _one_definition(definition=definition, book=book, bms=bms, fragment=fragment)
    if is_refusal(chosen):
        return chosen
    dummy = refuse_dummy_definition(chosen.value)
    if dummy is not None:
        return dummy
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "the composition root stamps a WriterId on the CT-06 envelope; QMB "
            "does not own the mint (AR-W04, DEC-0120)",
            given=repr(type(writer).__name__),
            mint=BOOK_BMS_MINT_SURFACE,
            shape_owner=BOOK_BMS_SHAPE_OWNER,
        )
    if not isinstance(created_at, Instant):
        return invalid(
            "created_at",
            "the composition root stamps an Instant occurrence fact on the CT-06 envelope",
            given=repr(type(created_at).__name__),
        )
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        return invalid(
            "sequence",
            "the per-writer sequence is a non-negative int64 ordering key",
            given=repr(sequence),
        )
    definition_fp = chosen.value.fingerprint()
    if is_refusal(definition_fp):
        return definition_fp
    origin_token = _as_origin(origin)
    if isinstance(origin_token, TypedRefusal):
        return origin_token
    qma_emitted = origin_token is not None and _fold(origin_token) in _QMA_ORIGINS
    relevant = _as_money_path_relevant(money_path_relevant, qma_emitted=qma_emitted)
    if isinstance(relevant, TypedRefusal):
        return relevant
    request = _as_approval_request(approval_request)
    if isinstance(request, TypedRefusal):
        return request
    gated = _require_qma_money_path(
        qma_emitted=qma_emitted,
        money_path_relevant=relevant,
        approval_request=request,
        candidate_ref=definition_fp.value,
        predecessor=predecessor,
        ancestor=ancestor,
    )
    if gated is not None:
        return gated
    kind = BOOK_RECORD_KIND if isinstance(chosen.value, BookDefinition) else BMS_RECORD_KIND
    body = _record_body(
        chosen.value,
        origin=origin_token,
        money_path_relevant=relevant,
        approval_request=request,
        predecessor=predecessor,
    )
    if isinstance(body, TypedRefusal):
        return body
    minted = RegistrationRecord.try_create(
        kind,
        chosen.value.contract_format_version,
        (definition_fp.value,),
        body,
        writer,
        sequence,
        created_at,
    )
    if is_refusal(minted):
        return minted
    return Ok(
        BookBmsVariant(
            kind=kind,
            contract=_CONTRACT_BY_KIND[kind],
            definition_fp1=definition_fp.value,
            record=minted.value,
            origin=origin_token,
            money_path_relevant=relevant,
            approval_request=None if request is None else MappingProxyType(request),
        )
    )


def evaluate_book_bms_variant(
    *,
    candidate: object = None,
    fp1: object = None,
    source_ct32: object = None,
    config: object = None,
    port: object = None,
    book_fragment: object = None,
    bms_fragment: object = None,
    run_spec: object = None,
    invocation_flags: object = None,
    workspace_defaults: object = None,
    condition_presets: object = (),
    starting_capital: object = None,
    fill_port: object = None,
    cost_port: object = None,
    financing_port: object = None,
    slices: object = None,
    output_root: object = None,
    ledger: object = None,
    occupancy: object = None,
    cpu_budget: object = None,
    memory_budget: object = None,
    projected_peak_memory: object = None,
    analysis_method: object = None,
    lane: object = None,
    workbench_lane: object = None,
    experiment_spec: object = None,
    successor: object = None,
    mint_experiment_spec: object = None,
    sqlite: object = None,
    database: object = None,
    daemon_sqlite: object = None,
    trades: object = None,
    trade_list: object = None,
    copied_trades: object = None,
    rescale: object = None,
    size_rescale: object = None,
    mm_simulator: object = None,
    trade_list_rescale: object = None,
    patch: object = None,
    overlay: object = None,
    partial: object = None,
    **extra: object,
) -> Result[RerunOutcome]:
    """Evaluate a Book/BMS candidate by ``analysis.rerun`` citing that fingerprint.

    Trade-list rescaling is refused as not Book/BMS truth (FR-W27, FR-W23).
    """
    rescale_field = _requested_field(
        {
            "copied_trades": copied_trades,
            "mm_simulator": mm_simulator,
            "rescale": rescale,
            "size_rescale": size_rescale,
            "trade_list": trade_list,
            "trade_list_rescale": trade_list_rescale,
            "trades": trades,
        },
        _RESCALE_FIELDS,
    )
    if rescale_field is None:
        rescale_field = next((key for key in extra if key in _RESCALE_FIELDS), None)
    if rescale_field is not None:
        return _refuse_rescale(rescale_field)
    patch_field = _requested_field(
        {"overlay": overlay, "partial": partial, "patch": patch},
        ("overlay", "partial", "patch"),
    )
    if patch_field is not None:
        return _refuse_patch(patch_field)
    variant = _resolve_candidate(candidate=candidate, fp1=fp1, port=port)
    if is_refusal(variant):
        return variant
    cited = _cite_in_config_or_layers(
        variant.value,
        config=config,
        port=port,
        book_fragment=book_fragment,
        bms_fragment=bms_fragment,
    )
    if is_refusal(cited):
        return cited
    compiled = cited.value.get("config")
    if compiled is not None:
        return rerun(
            source_ct32=source_ct32,
            config=compiled,
            slices=slices,
            output_root=output_root,
            ledger=ledger,
            occupancy=occupancy,
            cpu_budget=cpu_budget,
            memory_budget=memory_budget,
            projected_peak_memory=projected_peak_memory,
            analysis_method=analysis_method,
            lane=lane,
            workbench_lane=workbench_lane,
            experiment_spec=experiment_spec,
            successor=successor,
            mint_experiment_spec=mint_experiment_spec,
            sqlite=sqlite,
            database=database,
            daemon_sqlite=daemon_sqlite,
        )
    return rerun(
        source_ct32=source_ct32,
        port=port,
        book_fragment=cited.value.get("book_fragment", book_fragment),
        bms_fragment=cited.value.get("bms_fragment", bms_fragment),
        run_spec=run_spec,
        invocation_flags=invocation_flags,
        workspace_defaults=workspace_defaults,
        condition_presets=condition_presets,
        starting_capital=starting_capital,
        fill_port=fill_port,
        cost_port=cost_port,
        financing_port=financing_port,
        slices=slices,
        output_root=output_root,
        ledger=ledger,
        occupancy=occupancy,
        cpu_budget=cpu_budget,
        memory_budget=memory_budget,
        projected_peak_memory=projected_peak_memory,
        analysis_method=analysis_method,
        lane=lane,
        workbench_lane=workbench_lane,
        experiment_spec=experiment_spec,
        successor=successor,
        mint_experiment_spec=mint_experiment_spec,
        sqlite=sqlite,
        database=database,
        daemon_sqlite=daemon_sqlite,
    )


def _one_definition(
    *,
    definition: object,
    book: object,
    bms: object,
    fragment: object,
) -> Result[BookDefinition | BmsDefinition]:
    supplied = [item for item in (definition, book, bms) if item is not None]
    if fragment is not None and not _is_false(fragment):
        return _refuse_patch("fragment")
    if len(supplied) > 1:
        return invalid(
            "definition",
            "a proposed Book or BMS variant is one complete CT-22 or CT-27 document, "
            "never a pair of overlays (FR-W27, DEC-0274)",
        )
    if not supplied:
        return invalid(
            "definition",
            "a proposed Book or BMS variant is a complete qmf-risk CT-22/CT-27 "
            "document (COMP-QMF-RISK remains the shape owner)",
            shape_owner=BOOK_BMS_SHAPE_OWNER,
        )
    return _as_definition(supplied[0])


def _as_definition(value: object) -> Result[BookDefinition | BmsDefinition]:
    if isinstance(value, (BookDefinition, BmsDefinition)):
        return Ok(value)
    if isinstance(value, ConfigFragment):
        return _refuse_patch("fragment")
    if isinstance(value, RegistrationRecord):
        return invalid(
            "definition",
            "a proposed variant is a complete CT-22/CT-27 document; the CT-06 "
            "envelope is minted at the composition root from that document, not "
            "from a patch of an existing record (FR-W27, DEC-0274)",
            given=value.kind,
        )
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        if any(key in mapping for key in _PATCH_FIELDS):
            hit = next(key for key in _PATCH_FIELDS if key in mapping)
            return _refuse_patch(hit)
        class_token = clean_token(mapping.get("class"))
        if class_token == _BOOK_CLASS:
            built = BookDefinition.try_create(
                mapping.get("contract_format_version"),
                mapping.get("accounting_currency"),
                mapping.get("sections"),
            )
            if is_ok(built):
                return Ok(built.value)
            return _refuse_patch("partial")
        if class_token == _BMS_CLASS:
            built_bms = BmsDefinition.try_create(
                mapping.get("contract_format_version"),
                mapping.get("sections"),
            )
            if is_ok(built_bms):
                return Ok(built_bms.value)
            return _refuse_patch("partial")
        return _refuse_patch("overlay")
    return invalid(
        "definition",
        "a proposed Book or BMS variant is a complete qmf-risk BookDefinition "
        "or BmsDefinition (COMP-QMF-RISK remains the shape owner)",
        given=repr(type(value).__name__),
        shape_owner=BOOK_BMS_SHAPE_OWNER,
    )


def _record_body(
    definition: BookDefinition | BmsDefinition,
    *,
    origin: str | None,
    money_path_relevant: bool,
    approval_request: Mapping[str, object] | None,
    predecessor: object,
) -> dict[str, object] | TypedRefusal:
    body = dict(definition.fp1_identity())
    body["zone"] = VARIANT_ZONE
    if origin is not None:
        body["origin"] = origin
    if money_path_relevant:
        body["money_path_relevant"] = True
    if approval_request is not None:
        body["approval_request"] = {
            key: item for key, item in approval_request.items() if item is not None
        }
    predecessor_fp = _coerce_fingerprint(predecessor)
    if (
        predecessor is not None
        and predecessor_fp is None
        and not isinstance(predecessor, (BookDefinition, BmsDefinition, Mapping))
    ):
        return invalid(
            "predecessor",
            "a QMA Book/BMS predecessor is a complete CT-22/CT-27 fp1 or definition",
            given=repr(type(predecessor).__name__),
        )
    if predecessor_fp is not None:
        body["predecessor_fp1"] = predecessor_fp.value
    elif isinstance(predecessor, (BookDefinition, BmsDefinition)):
        stamped = predecessor.fingerprint()
        if is_refusal(stamped):
            return stamped
        body["predecessor_fp1"] = stamped.value.value
    return body


def _as_origin(value: object) -> str | TypedRefusal | None:
    if value is None:
        return None
    token = clean_token(value)
    if token is None:
        return invalid(
            "origin",
            "origin is a non-empty token; QMA-emitted candidates carry origin=qma "
            "(Story 45.6, FR-Q53)",
            given=repr(value),
        )
    return token


def _as_money_path_relevant(value: object, *, qma_emitted: bool) -> bool | TypedRefusal:
    if value is None:
        return qma_emitted
    if isinstance(value, bool):
        if qma_emitted and value is False:
            return policy(
                "money_path_relevant",
                "QMA-emitted Book/BMS candidates remain money_path_relevant "
                "(FR-W27, Story 45.6 / FR-Q53)",
                origin=QMA_CANDIDATE_ORIGIN,
            )
        return value
    return invalid(
        "money_path_relevant",
        "money_path_relevant is a boolean flag",
        given=repr(value),
    )


def _as_approval_request(
    value: object,
) -> Mapping[str, object] | TypedRefusal | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        return invalid(
            "approval_request",
            "QMA Book/BMS candidates carry a field-level diff in approval_request "
            "(Story 45.6 / FR-Q53)",
            given=repr(type(value).__name__),
        )
    return dict(cast("Mapping[str, object]", value))


def _require_qma_money_path(
    *,
    qma_emitted: bool,
    money_path_relevant: bool,
    approval_request: Mapping[str, object] | None,
    candidate_ref: Fingerprint,
    predecessor: object,
    ancestor: object,
) -> TypedRefusal | None:
    if not qma_emitted:
        return None
    if not money_path_relevant:
        return policy(
            "money_path_relevant",
            "QMA-emitted Book/BMS candidates remain money_path_relevant "
            "(FR-W27, Story 45.6 / FR-Q53)",
            origin=QMA_CANDIDATE_ORIGIN,
        )
    if approval_request is None:
        return policy(
            "approval_request",
            "a money_path_relevant Book/BMS candidate requires a field-level diff "
            "in approval_request (Story 45.6 / FR-Q53, DEC-0274)",
            schema=MONEY_PATH_FIELD_DIFF_SCHEMA,
            origin=QMA_CANDIDATE_ORIGIN,
        )
    diff = _field_level_diff(approval_request, candidate_ref=candidate_ref)
    if isinstance(diff, TypedRefusal):
        return diff
    filled = _unset_fills(ancestor=ancestor, predecessor=predecessor, approval_request=diff)
    if filled:
        return policy(
            "ancestor",
            "QMA never fills an unset money-path field; unset stays unset "
            "(FR-W27, DEC-0274, Story 45.6 / FR-Q53)",
            filled=list(filled),
            origin=QMA_CANDIDATE_ORIGIN,
        )
    return None


def _field_level_diff(
    request: Mapping[str, object],
    *,
    candidate_ref: Fingerprint,
) -> dict[str, object] | TypedRefusal:
    payload = request
    nested = request.get("payload")
    if isinstance(nested, Mapping) and "fields" in nested:
        payload = cast("Mapping[str, object]", nested)
    diff = request.get("diff")
    if isinstance(diff, Mapping) and "fields" in diff:
        payload = cast("Mapping[str, object]", diff)
    schema = clean_token(payload.get("schema"))
    if schema != MONEY_PATH_FIELD_DIFF_SCHEMA:
        return policy(
            "schema",
            "a money_path_relevant field-level diff must use the named "
            f"{MONEY_PATH_FIELD_DIFF_SCHEMA} qma-wire schema (Story 45.6 / FR-Q53)",
            given=repr(payload.get("schema")),
            schema=MONEY_PATH_FIELD_DIFF_SCHEMA,
        )
    fields = payload.get("fields")
    if not isinstance(fields, Sequence) or isinstance(fields, (str, bytes)):
        return invalid(
            "fields",
            "approval_request field-level diff fields are an array of "
            "{path, ancestor, proposed} (Story 45.6 / FR-Q53)",
        )
    parsed: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in cast("Sequence[object]", fields):
        if not isinstance(item, Mapping):
            return invalid("fields", "each field-level diff entry is an object")
        body = cast("Mapping[str, object]", item)
        path = clean_token(body.get("path"))
        if path is None or path not in MONEY_PATH_RELEVANT_FIELDS:
            return invalid(
                "path",
                "field-level diff paths are exactly the money_path_relevant fields "
                "risk, sizing, exit, protection, binding, priority",
                given=repr(body.get("path")),
            )
        if path in seen:
            return invalid("path", "field-level diff paths must be unique", path=path)
        if "ancestor" not in body or body["ancestor"] is None:
            return policy(
                "ancestor",
                "QMA never fills an unset money-path field; unset stays unset "
                "(FR-W27, DEC-0274, Story 45.6 / FR-Q53)",
                path=path,
            )
        seen.add(path)
        parsed.append(
            {
                "path": path,
                "ancestor": body["ancestor"],
                "proposed": body.get("proposed"),
            }
        )
    if not parsed:
        return invalid(
            "fields",
            "a money_path_relevant field-level diff names at least one field",
        )
    return {
        "schema": MONEY_PATH_FIELD_DIFF_SCHEMA,
        "candidate_ref": clean_token(payload.get("candidate_ref")) or candidate_ref.value,
        "predecessor_ref": payload.get("predecessor_ref"),
        "fields": parsed,
    }


def _unset_fills(
    *,
    ancestor: object,
    predecessor: object,
    approval_request: Mapping[str, object],
) -> tuple[str, ...]:
    prior = _money_path_map(ancestor)
    if not prior:
        prior = _money_path_map(predecessor)
    if not prior:
        return ()
    filled: list[str] = []
    fields = approval_request.get("fields")
    if not isinstance(fields, Sequence):
        return ()
    for item in cast("Sequence[object]", fields):
        if not isinstance(item, Mapping):
            continue
        body = cast("Mapping[str, object]", item)
        path = clean_token(body.get("path"))
        if path is None:
            continue
        proposed = body.get("proposed")
        if proposed is None:
            continue
        if path not in prior or prior[path] is None:
            filled.append(path)
    return tuple(filled)


def _money_path_map(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return {
            str(key): item
            for key, item in mapping.items()
            if str(key) in MONEY_PATH_RELEVANT_FIELDS
        }
    return {}


def _resolve_candidate(
    *,
    candidate: object,
    fp1: object,
    port: object,
) -> Result[BookBmsVariant]:
    if isinstance(candidate, BookBmsVariant):
        if candidate.zone != VARIANT_ZONE:
            return policy(
                "zone",
                "a proposed Book or BMS variant is registered in the registry dev zone "
                "(FR-W27, DEC-0274)",
                given=candidate.zone,
                zone=VARIANT_ZONE,
            )
        return Ok(candidate)
    if isinstance(candidate, RegistrationRecord):
        rebuilt = _variant_from_record(candidate)
        if rebuilt is not None:
            return Ok(rebuilt)
        return invalid(
            "candidate",
            "evaluation cites a complete CT-22/CT-27 dev-zone candidate",
            given=candidate.kind,
        )
    cited = candidate if candidate is not None else fp1
    wanted = _coerce_fingerprint(cited)
    if wanted is None:
        return invalid(
            "candidate",
            "evaluation is analysis.rerun citing the complete CT-22/CT-27 fingerprint "
            "(FR-W27, Story 35.3)",
            given=repr(type(cited).__name__ if cited is not None else None),
        )
    if isinstance(port, RegistryReadPort):
        record = _find_candidate_record(port, wanted)
        if record is not None:
            rebuilt = _variant_from_record(record)
            if rebuilt is not None:
                return Ok(rebuilt)
        return unavailable(
            "candidate",
            "evaluation cites a complete CT-22/CT-27 fingerprint present in the "
            "registry as-of set as a dev-zone candidate (FR-W27)",
            fp1=wanted.value,
        )
    return invalid(
        "candidate",
        "evaluation is analysis.rerun citing a registered Book/BMS variant or its fp1",
        fp1=wanted.value,
    )


def _variant_from_record(record: RegistrationRecord) -> BookBmsVariant | None:
    if record.kind not in {BOOK_RECORD_KIND, BMS_RECORD_KIND}:
        return None
    class_token = clean_token(record.body.get("class"))
    expected = _BOOK_CLASS if record.kind == BOOK_RECORD_KIND else _BMS_CLASS
    if class_token != expected:
        return None
    zone = _fold(clean_token(record.body.get("zone")) or "")
    origin = clean_token(record.body.get("origin"))
    if zone == _fold(ZONE_LIVE):
        return None
    if zone != VARIANT_ZONE and origin is None:
        return None
    identity = {key: record.body[key] for key in _DEFINITION_IDENTITY_KEYS if key in record.body}
    stamped = fingerprint(identity)
    if is_refusal(stamped):
        return None
    request = record.body.get("approval_request")
    approval: Mapping[str, object] | None
    if isinstance(request, Mapping):
        approval = MappingProxyType(dict(cast("Mapping[str, object]", request)))
    else:
        approval = None
    relevant = record.body.get("money_path_relevant") is True
    definition_fp = stamped.value
    if record.at_birth_parent_refs:
        definition_fp = record.at_birth_parent_refs[0]
    return BookBmsVariant(
        kind=record.kind,
        contract=_CONTRACT_BY_KIND[record.kind],
        definition_fp1=definition_fp,
        record=record,
        origin=origin,
        money_path_relevant=relevant,
        approval_request=approval,
    )


def _find_candidate_record(
    port: RegistryReadPort,
    cited: Fingerprint,
) -> RegistrationRecord | None:
    direct = port.bound.get(cited)
    if isinstance(direct, RegistrationRecord) and direct.kind in {
        BOOK_RECORD_KIND,
        BMS_RECORD_KIND,
    }:
        return direct
    for record in port.bound.records:
        if record.kind not in {BOOK_RECORD_KIND, BMS_RECORD_KIND}:
            continue
        if cited in record.at_birth_parent_refs:
            return record
        identity = {
            key: record.body[key] for key in _DEFINITION_IDENTITY_KEYS if key in record.body
        }
        stamped = fingerprint(identity)
        if is_ok(stamped) and stamped.value == cited:
            return record
    return None


def _cite_in_config_or_layers(
    variant: BookBmsVariant,
    *,
    config: object,
    port: object,
    book_fragment: object,
    bms_fragment: object,
) -> Result[dict[str, object]]:
    if isinstance(config, ResolvedRunConfig):
        cited = config.book_fp1 if variant.kind == BOOK_RECORD_KIND else config.bms_fp1
        if cited != variant.definition_fp1:
            return policy(
                "candidate",
                "evaluation is analysis.rerun citing that Book/BMS fingerprint; "
                "a resolved run-config that does not cite the candidate is not "
                "Book/BMS truth (FR-W27, DEC-0274)",
                given=cited.value,
                expected=variant.definition_fp1.value,
            )
        cited_config: dict[str, object] = {"config": config}
        return Ok(cited_config)
    if config is not None:
        return invalid(
            "config",
            "analysis.rerun takes a resolved run-config or compiles one from "
            "Book/BMS fragments citing the candidate fingerprint",
            given=repr(type(config).__name__),
        )
    layers: dict[str, object] = {}
    if variant.kind == BOOK_RECORD_KIND:
        resolved_book = _fragment_citing(
            variant,
            port=port,
            provided=book_fragment,
            materialize=materialize_book_fragment,
        )
        if is_refusal(resolved_book):
            return resolved_book
        layers["book_fragment"] = resolved_book.value
        if bms_fragment is not None:
            layers["bms_fragment"] = bms_fragment
    else:
        resolved_bms = _fragment_citing(
            variant,
            port=port,
            provided=bms_fragment,
            materialize=materialize_bms_fragment,
        )
        if is_refusal(resolved_bms):
            return resolved_bms
        layers["bms_fragment"] = resolved_bms.value
        if book_fragment is not None:
            layers["book_fragment"] = book_fragment
    return Ok(layers)


def _fragment_citing(
    variant: BookBmsVariant,
    *,
    port: object,
    provided: object,
    materialize: Callable[[object, object, object], Result[ConfigFragment]],
) -> Result[ConfigFragment]:
    if isinstance(provided, ConfigFragment):
        if provided.source_fp1 != variant.definition_fp1:
            return policy(
                "candidate",
                "evaluation is analysis.rerun citing that Book/BMS fingerprint; "
                "a fragment that does not cite the candidate is not Book/BMS truth "
                "(FR-W27, DEC-0274)",
                given=provided.source_fp1.value,
                expected=variant.definition_fp1.value,
            )
        return Ok(provided)
    if not isinstance(port, RegistryReadPort):
        return invalid(
            "port",
            "evaluation materializes the candidate Book/BMS fragment through the "
            "one registry-read port, citing that fingerprint (FR-W27)",
            given=repr(type(port).__name__),
        )
    minted = materialize(port, variant.record.stable_id, variant.record.writer)
    if is_refusal(minted):
        minted = materialize(port, variant.definition_fp1, variant.record.writer)
    if is_refusal(minted):
        return minted
    fragment = minted.value
    if fragment.source_fp1 != variant.definition_fp1:
        return policy(
            "candidate",
            "evaluation is analysis.rerun citing that Book/BMS fingerprint (FR-W27, DEC-0274)",
            given=fragment.source_fp1.value,
            expected=variant.definition_fp1.value,
        )
    return Ok(fragment)


def _refuse_definition_abuses(
    *,
    extra: Mapping[str, object],
    patch: object,
    overlay: object,
    partial: object,
    delta: object,
    field_patch: object,
    partial_overlay: object,
    fragment: object,
    trades: object,
    trade_list: object,
    copied_trades: object,
    rescale: object,
    size_rescale: object,
    mm_simulator: object,
    trade_list_rescale: object,
    mint: object,
    mint_into: object,
    shape_owner: object,
    zone: object,
) -> TypedRefusal | None:
    patch_field = _requested_field(
        {
            "delta": delta,
            "field_patch": field_patch,
            "overlay": overlay,
            "partial": partial,
            "partial_overlay": partial_overlay,
            "patch": patch,
        },
        _PATCH_FIELDS,
    )
    if patch_field is None:
        patch_field = next((key for key in extra if key in _PATCH_FIELDS), None)
    if patch_field is not None:
        return _refuse_patch(patch_field)
    if fragment is not None and not _is_false(fragment):
        return _refuse_patch("fragment")
    rescale_field = _requested_field(
        {
            "copied_trades": copied_trades,
            "mm_simulator": mm_simulator,
            "rescale": rescale,
            "size_rescale": size_rescale,
            "trade_list": trade_list,
            "trade_list_rescale": trade_list_rescale,
            "trades": trades,
        },
        _RESCALE_FIELDS,
    )
    if rescale_field is None:
        rescale_field = next((key for key in extra if key in _RESCALE_FIELDS), None)
    if rescale_field is not None:
        return _refuse_rescale(rescale_field)
    owner = clean_token(shape_owner)
    if owner is not None and owner != BOOK_BMS_SHAPE_OWNER:
        return policy(
            "shape_owner",
            "COMP-QMF-RISK remains the Book/BMS shape owner; this story does not "
            "move the shape into QMB or QMA (FR-W27, AR-W04)",
            given=owner,
            shape_owner=BOOK_BMS_SHAPE_OWNER,
        )
    mint_token = _fold(clean_token(mint_into) or clean_token(mint) or "")
    if mint_token in _MINT_OWNERS:
        return policy(
            "mint",
            "the composition root remains the mint; this story does not move mint "
            "into QMB or QMA (FR-W27, AR-W04, DEC-0120)",
            given=mint_token,
            mint=BOOK_BMS_MINT_SURFACE,
            shape_owner=BOOK_BMS_SHAPE_OWNER,
        )
    zone_token = _fold(clean_token(zone) or "")
    if zone_token and zone_token != VARIANT_ZONE:
        return policy(
            "zone",
            "a proposed Book or BMS variant is a complete fingerprinted CT-22/CT-27 "
            "in the registry dev zone (FR-W27, DEC-0274)",
            given=zone,
            zone=VARIANT_ZONE,
        )
    leaked = [key for key in extra if key in _OCCURRENCE_BODY_KEYS]
    if leaked:
        return invalid(
            leaked[0],
            "zone, origin, money_path_relevant, and approval_request are named "
            "parameters, never extra payload keys",
        )
    return None


def _refuse_patch(field: str) -> TypedRefusal:
    return policy(
        field,
        "a proposed Book or BMS variant is a complete new fingerprinted CT-22/CT-27 "
        "document in the registry dev zone; a patch record or partial overlay is "
        "refused as a definition (FR-W27, DEC-0274)",
        zone=VARIANT_ZONE,
        shape_owner=BOOK_BMS_SHAPE_OWNER,
        mint=BOOK_BMS_MINT_SURFACE,
    )


def _refuse_rescale(field: str) -> TypedRefusal:
    return policy(
        field,
        "trade-list rescaling is not Book/BMS truth; evaluation of a Book/BMS "
        "candidate is analysis.rerun citing that fingerprint (FR-W27, FR-W23, "
        "DEC-0274)",
        evaluation="analysis.rerun",
        trade_list_rescale_is_book_truth=False,
    )


def _requested_field(fields: Mapping[str, object], names: tuple[str, ...]) -> str | None:
    for name in names:
        if fields.get(name) not in (None, False):
            return name
    return None


def _is_false(value: object) -> bool:
    return value is False


def _fold(token: str) -> str:
    return token.casefold().replace("_", "-")


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None
