"""In-house interpretation skills that read CT-32, never a rendering (Story 19.5).

Explain a run, compare two runs, and flag a refusal-bearing period from the
stored artifact only. Agents never parse HTML. No skill sizes, promotes,
benches, binds, or changes a mode (R-RPT-9, R-RPT-22, B-10).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.performance import PublishAct

from qmb._refuse import clean_token, invalid, policy
from qmb.results.ct32 import as_ct32_artifact, looks_like_rendering
from qmb.results.render import AGENTS_PARSE_HTML, DOWNSTREAM_PUBLISH_ONLY

__all__ = [
    "DOWNSTREAM_FORBIDDEN_ACTS",
    "INTERPRETATION_SOURCE",
    "FieldDiff",
    "RefusalHeavyFlag",
    "RunComparison",
    "RunExplanation",
    "compare_runs",
    "explain_run",
    "flag_refusal_heavy",
    "refuse_downstream_act",
]

INTERPRETATION_SOURCE: Final[str] = "ct-32"
DOWNSTREAM_FORBIDDEN_ACTS: Final[tuple[str, ...]] = (
    "allocate",
    "bench",
    "bind",
    "change_mode",
    "demote",
    "promote",
    "size",
)
_RENDERING_REFUSAL: Final[str] = (
    "interpretation skills read the CT-32 artifact and never a rendering — "
    "agents never parse HTML (R-RPT-22, B-10)"
)


@dataclass(frozen=True, slots=True)
class RunExplanation:
    """Plain stored-field readout of one CT-32 artifact. No derived metric."""

    world: str
    account_binding_role: str
    evidence_class: str
    measure_set: tuple[object, ...]
    suppression_accounting: tuple[object, ...]
    veto_accounting: tuple[object, ...]
    source: str = INTERPRETATION_SOURCE
    parsed_html: bool = False
    publish_only: bool = True


@dataclass(frozen=True, slots=True)
class FieldDiff:
    """Two stored values at the same path that are not equal. Not a delta."""

    path: str
    left: object
    right: object


@dataclass(frozen=True, slots=True)
class RunComparison:
    """Field-wise comparison of two stored CT-32 artifacts. No new number."""

    same_world: bool
    same_account_binding_role: bool
    matching_paths: tuple[str, ...]
    differing: tuple[FieldDiff, ...]
    source: str = INTERPRETATION_SOURCE
    parsed_html: bool = False
    publish_only: bool = True


@dataclass(frozen=True, slots=True)
class RefusalHeavyFlag:
    """Stored suppression/veto rows whose count is not the explicit zero."""

    refusal_bearing: bool
    suppression_rows: tuple[object, ...]
    veto_rows: tuple[object, ...]
    source: str = INTERPRETATION_SOURCE
    parsed_html: bool = False
    publish_only: bool = True


def explain_run(source: object) -> Result[RunExplanation]:
    """Explain a run from the stored CT-32 artifact. HTML is a typed refusal."""
    body = _read_artifact(source)
    if is_refusal(body):
        return body
    payload = body.value
    label = _label(payload)
    if is_refusal(label):
        return label
    world = _token(label.value.get("world"), "world")
    if is_refusal(world):
        return world
    role = _token(payload.get("account_binding_role"), "account_binding_role")
    if is_refusal(role):
        return role
    evidence = _token(label.value.get("evidence_class"), "evidence_class")
    if is_refusal(evidence):
        return evidence
    measures = _rows(payload.get("measure_set"), "measure_set")
    if is_refusal(measures):
        return measures
    suppressions = _rows(payload.get("suppression_accounting"), "suppression_accounting")
    if is_refusal(suppressions):
        return suppressions
    vetoes = _rows(payload.get("veto_accounting"), "veto_accounting")
    if is_refusal(vetoes):
        return vetoes
    return Ok(
        RunExplanation(
            world=world.value,
            account_binding_role=role.value,
            evidence_class=evidence.value,
            measure_set=measures.value,
            suppression_accounting=suppressions.value,
            veto_accounting=vetoes.value,
            parsed_html=AGENTS_PARSE_HTML,
            publish_only=DOWNSTREAM_PUBLISH_ONLY,
        )
    )


def compare_runs(left: object, right: object) -> Result[RunComparison]:
    """Compare two stored CT-32 artifacts field-for-field. No computed delta."""
    first = _read_artifact(left)
    if is_refusal(first):
        return first
    second = _read_artifact(right)
    if is_refusal(second):
        return second
    left_paths = _flatten(first.value)
    right_paths = _flatten(second.value)
    keys = sorted(set(left_paths) | set(right_paths))
    matching: list[str] = []
    differing: list[FieldDiff] = []
    for path in keys:
        if path not in left_paths or path not in right_paths:
            differing.append(
                FieldDiff(
                    path=path,
                    left=left_paths.get(path, "<absent>"),
                    right=right_paths.get(path, "<absent>"),
                )
            )
            continue
        if left_paths[path] == right_paths[path]:
            matching.append(path)
        else:
            differing.append(FieldDiff(path=path, left=left_paths[path], right=right_paths[path]))
    left_world = left_paths.get("result_label.world")
    right_world = right_paths.get("result_label.world")
    left_role = left_paths.get("account_binding_role")
    right_role = right_paths.get("account_binding_role")
    return Ok(
        RunComparison(
            same_world=left_world == right_world and left_world is not None,
            same_account_binding_role=left_role == right_role and left_role is not None,
            matching_paths=tuple(matching),
            differing=tuple(differing),
            parsed_html=AGENTS_PARSE_HTML,
            publish_only=DOWNSTREAM_PUBLISH_ONLY,
        )
    )


def flag_refusal_heavy(source: object) -> Result[RefusalHeavyFlag]:
    """Flag a period whose stored suppression or veto count is not zero.

    Comparison is against the artifact's explicit zero default (R-RPT-8), never
    an invented threshold. Non-zero stored counts are copied, not recomputed.
    """
    body = _read_artifact(source)
    if is_refusal(body):
        return body
    payload = body.value
    suppressions = _nonzero_counts(payload.get("suppression_accounting"), "suppression_accounting")
    if is_refusal(suppressions):
        return suppressions
    vetoes = _nonzero_counts(payload.get("veto_accounting"), "veto_accounting")
    if is_refusal(vetoes):
        return vetoes
    return Ok(
        RefusalHeavyFlag(
            refusal_bearing=bool(suppressions.value or vetoes.value),
            suppression_rows=suppressions.value,
            veto_rows=vetoes.value,
            parsed_html=AGENTS_PARSE_HTML,
            publish_only=DOWNSTREAM_PUBLISH_ONLY,
        )
    )


def refuse_downstream_act(act: object) -> Result[None]:
    """Refuse size / promote / bench / bind / mode-change on a downstream read."""
    if isinstance(act, PublishAct):
        return _publish_only(act.value)
    token = act if isinstance(act, str) else clean_token(act)
    if not isinstance(token, str) or token.strip() == "":
        return invalid(
            "act",
            "publish-only downstream reads refuse a named act; the name is required",
            given=repr(act),
            forbidden=list(DOWNSTREAM_FORBIDDEN_ACTS),
        )
    normalized = token.casefold().replace("-", "_").replace(" ", "_")
    if normalized in DOWNSTREAM_FORBIDDEN_ACTS:
        return _publish_only(normalized)
    for member in PublishAct:
        if member.value.replace("-", "_") == normalized or member.name.casefold() == normalized:
            return _publish_only(member.value)
    return invalid(
        "act",
        "rendering, interpretation, and reproduction are publish-only and "
        "do not size, promote, bench, bind, or change a mode (R-RPT-9, B-10)",
        given=token,
        forbidden=list(DOWNSTREAM_FORBIDDEN_ACTS),
    )


def _publish_only(act: object) -> Result[None]:
    return policy(
        "act",
        "rendering, interpretation, and reproduction are publish-only: none may "
        "size, promote, bench, bind, or change a mode (R-RPT-9, B-10)",
        act=act,
        forbidden=list(DOWNSTREAM_FORBIDDEN_ACTS),
    )


def _read_artifact(source: object) -> Result[dict[str, object]]:
    if looks_like_rendering(source):
        return policy("artifact", _RENDERING_REFUSAL)
    return as_ct32_artifact(source)


def _label(payload: Mapping[str, object]) -> Result[Mapping[str, object]]:
    raw = payload.get("result_label")
    if not isinstance(raw, Mapping):
        return invalid(
            "result_label",
            "interpretation reads the stored AD-12 result_label mapping",
            given=repr(type(raw).__name__),
        )
    return Ok(cast("Mapping[str, object]", raw))


def _token(value: object, field: str) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return invalid(
            field,
            "interpretation copies the stored world and account-binding role verbatim",
            given=repr(value),
        )
    return Ok(value)


def _rows(value: object, field: str) -> Result[tuple[object, ...]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            field,
            "interpretation copies the stored CT-32 sequence; it does not re-derive it",
            given=repr(type(value).__name__),
        )
    return Ok(tuple(cast("Sequence[object]", value)))


def _nonzero_counts(value: object, field: str) -> Result[tuple[object, ...]]:
    rows = _rows(value, field)
    if is_refusal(rows):
        return rows
    flagged: list[object] = []
    for index, row in enumerate(rows.value):
        if not isinstance(row, Mapping):
            return invalid(
                field,
                "each stored accounting row is a mapping with a count the skill copies",
                index=index,
                given=repr(type(row).__name__),
            )
        body = cast("Mapping[str, object]", row)
        count = body.get("count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            return invalid(
                field,
                "each stored accounting count is a non-negative int already on the artifact",
                index=index,
                given=repr(count),
            )
        if count != 0:
            flagged.append(dict(body))
    return Ok(tuple(flagged))


def _flatten(value: object, path: str = "") -> dict[str, object]:
    """Path -> stored scalar. Sequences and mappings are walked, never reduced."""
    out: dict[str, object] = {}
    if isinstance(value, Mapping) and not isinstance(value, (str, bytes)):
        body = cast("Mapping[str, object]", value)
        for key, item in body.items():
            child = f"{path}.{key}" if path else str(key)
            out.update(_flatten(item, child))
        return out
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        sequence = cast("Sequence[object]", value)
        for index, item in enumerate(sequence):
            out.update(_flatten(item, f"{path}[{index}]"))
        return out
    out[path] = value
    return out
