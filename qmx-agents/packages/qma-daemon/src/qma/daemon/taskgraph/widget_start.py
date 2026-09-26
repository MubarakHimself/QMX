"""Widget binds ``start`` of template T; it does not own invoke.

Story 63.3 / FR-PG-28 / SCN-0025 Then 1. A user or agent press is an
enveloped ``start`` with ``caller_kind=user|agent`` and required
``instance_id``. Widgets are not a fifth parent-AD-10 composition mode.
Disposing the widget does not cancel the Mission. A widget contribution
point that executes without an envelope is refused (SCN-0025 Branch B).
GAP-0081 chrome is not filled; widgets never own invoke (DEC-0455).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal

from qma.core.ontology import Quant
from qma.core.plugins.pack_sdk import WIDGETS_OWN_INVOKE
from qma.core.ports.copilot import GAP_0081_CHROME_FILLED
from qma.core.ports.jobs import JobHandle
from qma.core.vocabulary.enums import CallerKind, LifecycleVerb
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qma.daemon.taskgraph.records import MissionRecord, TaskGraph
from qma.wire.invocation_envelope import InvocationEnvelope
from qmf.core import Ok, Result
from qmf.core.refusal import TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "FIFTH_COMPOSITION_MODE_MINTED",
    "GAP_0081_CHROME_FILLED",
    "PARENT_AD10_COMPOSITION_MODES",
    "WIDGETS_OWN_INVOKE",
    "WIDGET_DISPOSE_CANCELS_MISSION",
    "WIDGET_START_CALLER_KINDS",
    "WIDGET_START_IMPLEMENTED",
    "WIDGET_START_VERB",
    "WidgetStartBinding",
    "WidgetStartedMission",
    "parse_widget_start_binding",
    "refuse_fifth_composition_mode",
    "refuse_gap_0081_widget_chrome",
    "refuse_widget_contribution_without_envelope",
    "refuse_widget_owned_invoke",
]


FIFTH_COMPOSITION_MODE_MINTED: Final[bool] = False
WIDGET_START_IMPLEMENTED: Final[bool] = True
WIDGET_DISPOSE_CANCELS_MISSION: Final[bool] = False
WIDGET_START_VERB: Final[str] = LifecycleVerb.START.value
PARENT_AD10_COMPOSITION_MODES: Final[tuple[str, ...]] = (
    "consume_artifact",
    "invoke_op",
    "graph_template_coordinate",
    "composite_instance_graph",
)
WIDGET_START_CALLER_KINDS: Final[frozenset[CallerKind]] = frozenset(
    {CallerKind.USER, CallerKind.AGENT}
)
_WIDGET_CONTRIBUTION_POINTS: Final[frozenset[str]] = frozenset(
    {"widget", "ui_widget", "ui_view", "widgets"}
)


@dataclass(frozen=True, slots=True)
class WidgetStartBinding:
    """Host bind of a widget to ``start`` of Graph Template T.

    Not a contribution point, not GAP-0081 chrome, and not an invoke owner.
    Composition stays one of the parent AD-10 four modes.
    """

    widget_id: str
    template_qualified_id: str
    template_version: str
    bound_verb: str = WIDGET_START_VERB
    composition_mode: str = "invoke_op"
    owns_invoke: Literal[False] = False
    is_contribution_point: Literal[False] = False
    gap_0081_chrome: Literal[False] = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "bound_verb": self.bound_verb,
                "composition_mode": self.composition_mode,
                "fifth_composition_mode_minted": FIFTH_COMPOSITION_MODE_MINTED,
                "gap_0081_chrome": self.gap_0081_chrome,
                "is_contribution_point": self.is_contribution_point,
                "owns_invoke": self.owns_invoke,
                "template": {
                    "qualified_id": self.template_qualified_id,
                    "version": self.template_version,
                },
                "widget_id": self.widget_id,
            }
        )


@dataclass(frozen=True, slots=True)
class WidgetStartedMission:
    """Top-level Mission started by a widget-bound enveloped ``start``."""

    binding: WidgetStartBinding
    envelope: InvocationEnvelope
    owner: Quant
    mission: MissionRecord
    task_graph: TaskGraph
    handle: JobHandle

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "bound_verb": self.binding.bound_verb,
                "caller_kind": self.envelope.caller_kind.value,
                "cancelled_on_dispose": WIDGET_DISPOSE_CANCELS_MISSION,
                "composition_mode": self.binding.composition_mode,
                "fifth_composition_mode_minted": FIFTH_COMPOSITION_MODE_MINTED,
                "gap_0081_chrome_filled": GAP_0081_CHROME_FILLED,
                "graph_id": self.task_graph.id,
                "instance_id": self.envelope.instance_id,
                "job_id": self.handle.job_id,
                "mission_id": self.mission.id,
                "owns_invoke": WIDGETS_OWN_INVOKE,
                "template": {
                    "qualified_id": self.binding.template_qualified_id,
                    "version": self.binding.template_version,
                },
                "widget_id": self.binding.widget_id,
            }
        )


def refuse_widget_owned_invoke(
    *,
    given: object | None = None,
    **extra: object,
) -> TypedRefusal:
    """Widgets bind or display ops; they never own invoke (FR-PG-28)."""
    context: dict[str, object] = {
        "owns_invoke": WIDGETS_OWN_INVOKE,
        "bound_verb": WIDGET_START_VERB,
        "fifth_composition_mode_minted": FIFTH_COMPOSITION_MODE_MINTED,
    }
    if given is not None:
        context["given"] = given
    context.update(extra)
    return policy_rejection(
        "widget",
        "widgets bind or display ops; they do not own invoke (DEC-0455; FR-PG-28)",
        **context,
    )


def refuse_widget_contribution_without_envelope(
    *,
    point: object | None = None,
    **extra: object,
) -> TypedRefusal:
    """SCN-0025 Branch B — widget contribution must not execute without envelope."""
    context: dict[str, object] = {
        "envelope_present": False,
        "owns_invoke": WIDGETS_OWN_INVOKE,
        "branch": "B",
    }
    if point is not None:
        context["point"] = point
    context.update(extra)
    return invalid_input(
        "invocation_envelope",
        "a widget contribution point that executes without an envelope is refused "
        "(SCN-0025 Branch B; FR-PG-28; UX-DR-PG-02)",
        **context,
    )


def refuse_fifth_composition_mode(
    given: object,
    **extra: object,
) -> TypedRefusal:
    """Parent AD-10 four modes remain; widget is not a fifth."""
    return invalid_input(
        "composition_mode",
        "parent AD-10 four modes remain; widgets do not introduce a fifth "
        "composition mode (FR-PG-28; SCN-0025 Then 1)",
        given=given if isinstance(given, (str, int, type(None))) else repr(given),
        allowed=list(PARENT_AD10_COMPOSITION_MODES),
        fifth_composition_mode_minted=FIFTH_COMPOSITION_MODE_MINTED,
        **extra,
    )


def refuse_gap_0081_widget_chrome(**extra: object) -> TypedRefusal:
    """Widget start bind is not UI contribution SDK chrome."""
    return policy_rejection(
        "ui_view",
        "widget start bind is not GAP-0081 chrome; ui_view stays deferred (DEC-0280; FR-PG-28)",
        gap_0081_chrome_filled=GAP_0081_CHROME_FILLED,
        owns_invoke=WIDGETS_OWN_INVOKE,
        **extra,
    )


def parse_widget_start_binding(
    widget_id: object,
    *,
    qualified_id: str,
    version: str,
    verb: object = WIDGET_START_VERB,
    composition_mode: object | None = None,
    owns_invoke: object = False,
    is_contribution_point: object = False,
    gap_0081_chrome: object = False,
) -> Result[WidgetStartBinding]:
    """Accept a bind of ``start`` on template T. Refuse invoke ownership."""
    if owns_invoke is True or owns_invoke == "true":
        return refuse_widget_owned_invoke(given=owns_invoke)
    if is_contribution_point is True or is_contribution_point == "true":
        return refuse_widget_owned_invoke(
            given=is_contribution_point,
            is_contribution_point=False,
        )
    if gap_0081_chrome is True or gap_0081_chrome == "true":
        return refuse_gap_0081_widget_chrome(given=gap_0081_chrome)
    if not isinstance(widget_id, str) or widget_id.strip() == "":
        return invalid_input(
            "widget_id",
            "widget id is a non-empty string",
            given=repr(widget_id),
        )
    parsed_verb = _parse_start_verb(verb)
    if isinstance(parsed_verb, TypedRefusal):
        return parsed_verb
    mode = "invoke_op" if composition_mode is None else composition_mode
    if not isinstance(mode, str) or mode not in PARENT_AD10_COMPOSITION_MODES:
        return refuse_fifth_composition_mode(mode)
    return Ok(
        WidgetStartBinding(
            widget_id=widget_id.strip(),
            template_qualified_id=qualified_id,
            template_version=version,
            bound_verb=parsed_verb,
            composition_mode=mode,
        )
    )


def widget_contribution_point_name(point: object) -> str | None:
    """Return a widget-like contribution token, else None."""
    if not isinstance(point, str) or point.strip() == "":
        return None
    token = point.strip()
    if token in _WIDGET_CONTRIBUTION_POINTS:
        return token
    return None


def _parse_start_verb(verb: object) -> str | TypedRefusal:
    try:
        parsed = parse_closed(LifecycleVerb, verb)
    except VocabularyError:
        return refuse_widget_owned_invoke(
            given=repr(verb),
            bound_verb=WIDGET_START_VERB,
        )
    if parsed is not LifecycleVerb.START:
        return invalid_input(
            "verb",
            "a widget binds start; it does not own invoke (FR-PG-28)",
            given=parsed.value,
            bound_verb=WIDGET_START_VERB,
            owns_invoke=WIDGETS_OWN_INVOKE,
        )
    return parsed.value
