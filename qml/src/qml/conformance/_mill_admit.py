"""Mill-graduation admit helpers (split from ``registration`` for Skylos quality).

``originating_research_ref`` is hypothesis ``research_ref`` only
(class ``qml-research-hypothesis``). Knowledge Citation shapes are refused.
Public names are re-exported from ``registration``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qml._refuse import invalid, policy
from qml.conformance.registration import Graduation, graduate_to_governed
from qml.research.collapse import refuse_invented_exits
from qml.research.stage0 import (
    RESEARCH_CONTRACT_CLASS as MILL_RESEARCH_CLASS_TOKEN,
)
from qml.research.stage0 import (
    Hypothesis,
    SavedHypothesis,
    fingerprint_hypothesis,
    hypothesis_identity_payload,
)

__all__ = [
    "MILL_ORIGINATING_BANNED_KEYS",
    "MILL_RESEARCH_CLASS",
    "admit_mill_originating_research_ref",
    "graduate_mill_to_governed",
    "refuse_spawn_as_graduation",
]

MILL_RESEARCH_CLASS: Final[str] = MILL_RESEARCH_CLASS_TOKEN
MILL_ORIGINATING_BANNED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "artifact_ref",
        "seed_cite",
        "source_ref",
    }
)

_CITATION_SHAPE_ATTRS: Final[frozenset[str]] = frozenset(
    {"artifact_ref", "source_ref", "seed_cite"}
)


def admit_mill_originating_research_ref(
    value: object,
    *,
    hypothesis: object,
) -> Result[Fingerprint]:
    """Admit mill ``originating_research_ref`` = hypothesis ``research_ref`` only.

    Knowledge Citation digest / ``artifact_ref`` / ``source_ref`` / ``seed_cite``
    are refused; seed cites travel on ``seed_cite`` only (Story 51.3).
    """
    shaped = _refuse_citation_shaped_origin(value)
    if is_refusal(shaped):
        return shaped
    expected = _research_ref_from_hypothesis(hypothesis)
    if is_refusal(expected):
        return expected
    if value is None:
        return Ok(expected.value)
    given = _coerce_fingerprint(value, "originating_research_ref")
    if is_refusal(given):
        return given
    if given.value.value != expected.value.value:
        return invalid(
            "originating_research_ref",
            "mill originating_research_ref must equal the hypothesis research_ref "
            f"(class {MILL_RESEARCH_CLASS})",
            given=given.value.value,
            research_ref=expected.value.value,
            research_class=MILL_RESEARCH_CLASS,
        )
    return Ok(given.value)


def graduate_mill_to_governed(
    *,
    layer1: object,
    layer2: object,
    hypothesis: object,
    originating_research_ref: object = None,
    **extra: object,
) -> Result[Graduation]:
    """Mill graduation: call :func:`graduate_to_governed` with ``research_ref`` only.

    Does not call the structure-package research graduate helper. ``spawn_governed``
    is not graduation (use :func:`refuse_spawn_as_graduation`).
    """
    if "spawn_governed" in extra:
        return refuse_spawn_as_graduation(extra.pop("spawn_governed"))
    invented = _refuse_invent_flags(extra)
    if is_refusal(invented):
        return invented
    research = admit_mill_originating_research_ref(
        originating_research_ref,
        hypothesis=hypothesis,
    )
    if is_refusal(research):
        return research
    return graduate_to_governed(
        layer1=layer1,
        layer2=layer2,
        originating_research_ref=research.value,
        **extra,
    )


def refuse_spawn_as_graduation(label: object = "spawn_governed") -> TypedRefusal:
    """``spawn_governed`` is not graduation; L33 stays two-artifact registration."""
    return policy(
        "graduation",
        "spawn_governed is not graduation; L33 remains two-artifact registration, "
        "not an orchestrator spawn (DEC-0270)",
        given=repr(label),
        spawn_governed=False,
        mill_calls="qml.conformance.registration.graduate_to_governed",
    )


def _refuse_invent_flags(extra: dict[str, object]) -> Result[None]:
    # Story 51.2 — refuse invented exits/producers/CT-29 during mill collapse.
    invent_flags = (
        extra.pop("invent_exits", False),
        extra.pop("invent_producers", False),
        extra.pop("invent_close_reasons", False),
    )
    if not any(flag is True for flag in invent_flags):
        return Ok(None)
    return refuse_invented_exits(
        invent_exits=invent_flags[0],
        invent_producers=invent_flags[1],
        invent_close_reasons=invent_flags[2],
    )


def _refuse_citation_shaped_origin(value: object) -> Result[None]:
    """Refuse Knowledge Citation / seed_cite shapes as mill originating refs."""
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        hit = sorted(key for key in MILL_ORIGINATING_BANNED_KEYS if key in mapping)
        if hit:
            return policy(
                "originating_research_ref",
                "Knowledge Citation digest / artifact_ref / source_ref / seed_cite "
                "is not a legal mill originating_research_ref; seed cites travel on "
                "seed_cite only",
                banned=hit,
                research_class=MILL_RESEARCH_CLASS,
            )
        return Ok(None)
    for attr in sorted(_CITATION_SHAPE_ATTRS):
        if hasattr(value, attr) and not isinstance(value, (Fingerprint, str, bytes)):
            return policy(
                "originating_research_ref",
                "Knowledge Citation digest / artifact_ref / source_ref / seed_cite "
                "is not a legal mill originating_research_ref; seed cites travel on "
                "seed_cite only",
                banned=attr,
                given=type(value).__name__,
                research_class=MILL_RESEARCH_CLASS,
            )
    return Ok(None)


def _research_ref_from_hypothesis(hypothesis: object) -> Result[Fingerprint]:
    """Resolve hypothesis research_ref (class qml-research-hypothesis)."""
    if isinstance(hypothesis, SavedHypothesis):
        return Ok(hypothesis.research_ref)
    if isinstance(hypothesis, Hypothesis):
        return fingerprint_hypothesis(hypothesis)
    if isinstance(hypothesis, Mapping):
        return _research_ref_from_mapping(cast("Mapping[str, object]", hypothesis))
    return invalid(
        "hypothesis",
        "mill graduation requires a Stage 0 Hypothesis or SavedHypothesis so "
        f"originating_research_ref is proven as class {MILL_RESEARCH_CLASS}",
        given=type(hypothesis).__name__,
        research_class=MILL_RESEARCH_CLASS,
        identity_helper=hypothesis_identity_payload.__name__,
    )


def _research_ref_from_mapping(mapping: Mapping[str, object]) -> Result[Fingerprint]:
    if mapping.get("class") != MILL_RESEARCH_CLASS:
        return invalid(
            "hypothesis",
            "mill graduation proves originating_research_ref against a "
            f"{MILL_RESEARCH_CLASS} hypothesis (or its saved envelope)",
            given=repr(mapping.get("class")),
            research_class=MILL_RESEARCH_CLASS,
        )
    return fingerprint(dict(mapping))


def _coerce_fingerprint(value: object, field: str) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    parsed = Fingerprint.try_create(value)
    if is_refusal(parsed):
        return invalid(
            field,
            "a Bot citation or research artifact is referenced by fp1:sha256:<hex>",
            given=repr(value),
        )
    return parsed
