"""Public extension ladder — rungs 1–3 bind; rung 4 stays GAP-0081 (DEC-0280).

The public surface is exactly three rungs: ui-editable config variables on
templates, ordinary Python plus QMB ports/adapters, and QMA plugins / skills /
graph templates / desk packs. Rung 4 (UI contribution SDK / qma-ui-contract)
is refused as GAP-0081 deferred. No ``ui_view`` contribution point is minted.
No-code authoring is not an extension rung; ordinary Python remains the logic
path. QMA ``plugin`` vocabulary stays QMA-scoped (DEC-0346). The
work-environment roster is a later UI alias over fingerprints — this module
does not mint a roster kind (NFR-W06 A2; FR-W16).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qma.core.plugins.packs import DESK_PLUGIN_PACK_IDS
from qma.core.ports.cardinality import (
    MULTI_CONTRIBUTION_POINTS,
    RETIRED_CONTRIBUTION_POINTS,
)
from qma.core.refusals.variants import (
    ExtensionSurfaceRefused,
    NoCodeAuthoringRefused,
    UiContributionDeferred,
)
from qma.core.vocabulary.enums import VariableEditability
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "DEFERRED_EXTENSION_RUNG",
    "GAP_0081_STATUS",
    "GAP_0081_UI_CONTRIBUTION",
    "LOGIC_PATH_RUNG",
    "NO_CODE_AUTHORING_REQUESTS",
    "PLUGIN_VOCABULARY_SCOPE",
    "PUBLIC_EXTENSION_RUNGS",
    "QMA_UI_CONTRACT_PACKAGE",
    "QMA_UI_CONTRACT_STATUS",
    "QMB_MODULE_IS_PLUGIN",
    "RUNG_1_CONFIGURABLE_FLAG",
    "RUNG_1_LAW",
    "RUNG_3_CONTRIBUTIONS",
    "UI_CONTRIBUTION_POINTS",
    "UI_VIEW_CONTRIBUTION_POINT",
    "WORK_ENVIRONMENT_ROSTER",
    "WORK_ENVIRONMENT_ROSTER_KIND",
    "ExtensionRung",
    "ExtensionRungSpec",
    "admit_extension_rung",
    "enumerate_public_extension_rungs",
    "is_no_code_authoring_request",
    "is_public_extension_rung",
    "is_ui_contribution_point",
    "logic_path_is_ordinary_python",
    "mint_work_environment_roster_kind",
    "parse_extension_rung",
    "plugin_vocabulary_is_qma_scoped",
    "refuse_no_code_authoring",
    "refuse_qmb_plugin_label",
    "refuse_ui_contribution",
    "register_ui_widget_contribution",
    "ui_view_contribution_point_minted",
]


class ExtensionRung(StrEnum):
    """Four-rung ladder. Only the first three bind (DEC-0280; FR-W37)."""

    CONFIG_VARIABLES = "config_variables"
    ORDINARY_PYTHON = "ordinary_python"
    QMA_PACKS = "qma_packs"
    UI_CONTRIBUTION_SDK = "ui_contribution_sdk"


PUBLIC_EXTENSION_RUNGS: Final[tuple[int, int, int]] = (1, 2, 3)
DEFERRED_EXTENSION_RUNG: Final[int] = 4
LOGIC_PATH_RUNG: Final[int] = 2
RUNG_1_CONFIGURABLE_FLAG: Final[str] = "configurable: true"
RUNG_1_LAW: Final[str] = "L38"
RUNG_3_CONTRIBUTIONS: Final[tuple[str, str, str, str]] = (
    "plugin",
    "skill",
    "graph_template",
    "desk_pack",
)
PLUGIN_VOCABULARY_SCOPE: Final[str] = "qma"
QMB_MODULE_IS_PLUGIN: Final[bool] = False
QMA_UI_CONTRACT_PACKAGE: Final[str] = "qma-ui-contract"
QMA_UI_CONTRACT_STATUS: Final[str] = "stub"
GAP_0081_STATUS: Final[str] = "deferred"
UI_VIEW_CONTRIBUTION_POINT: Final[str] = "ui_view"
UI_CONTRIBUTION_POINTS: Final[frozenset[str]] = frozenset(
    {
        "ui_view",
        "ui_package",
        "ui_extension",
        "ui_widget",
        "ui_contribution_sdk",
    }
)
NO_CODE_AUTHORING_REQUESTS: Final[frozenset[str]] = frozenset(
    {
        "sq_building_block_dsl",
        "sq_style_dsl",
        "building_block_dsl",
        "random_condition_editor",
        "qml_revival",
        ".qml",
        "qml",
    }
)
WORK_ENVIRONMENT_ROSTER_KIND: Final[None] = None
WORK_ENVIRONMENT_ROSTER: Final[Mapping[str, object]] = MappingProxyType(
    {
        "kind": WORK_ENVIRONMENT_ROSTER_KIND,
        "status": "later_ui_alias",
        "over": "fingerprints",
        "nfr": "NFR-W06 A2",
        "fr": "FR-W16",
        "minted": False,
    }
)
GAP_0081_UI_CONTRIBUTION: Final[Mapping[str, str]] = MappingProxyType(
    {
        "gap": "GAP-0081",
        "status": GAP_0081_STATUS,
        "package": QMA_UI_CONTRACT_PACKAGE,
        "package_status": QMA_UI_CONTRACT_STATUS,
        "effect": (
            "rung 4 is the UI contribution SDK / qma-ui-contract; it stays "
            "deferred and no ui_view contribution point is minted"
        ),
    }
)

_RUNG_BY_NUMBER: Final[Mapping[int, ExtensionRung]] = MappingProxyType(
    {
        1: ExtensionRung.CONFIG_VARIABLES,
        2: ExtensionRung.ORDINARY_PYTHON,
        3: ExtensionRung.QMA_PACKS,
        4: ExtensionRung.UI_CONTRIBUTION_SDK,
    }
)
_NO_CODE_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "sq_building_block_dsl": "sq_building_block_dsl",
        "sq-style": "sq_building_block_dsl",
        "sq_style": "sq_building_block_dsl",
        "sq_style_dsl": "sq_building_block_dsl",
        "building_block_dsl": "sq_building_block_dsl",
        "building-block-dsl": "sq_building_block_dsl",
        "random_condition_editor": "random_condition_editor",
        "randomcondition": "random_condition_editor",
        "random_condition": "random_condition_editor",
        "qml_revival": "qml_revival",
        ".qml": "qml_revival",
        "qml": "qml_revival",
    }
)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


@dataclass(frozen=True, slots=True)
class ExtensionRungSpec:
    """One ladder rung. ``binds`` is true only for the public three."""

    number: int
    name: ExtensionRung
    binds: bool
    surface: str
    gap: str | None = None
    status: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "number": self.number,
            "name": self.name.value,
            "binds": self.binds,
            "surface": self.surface,
        }
        if self.number == 1:
            payload["configurable"] = True
            payload["flag"] = RUNG_1_CONFIGURABLE_FLAG
            payload["law"] = RUNG_1_LAW
            payload["editability"] = VariableEditability.UI_EDITABLE.value
        elif self.number == 2:
            payload["logic"] = "ordinary_python"
            payload["host"] = ("qmb_ports", "qmb_adapters")
            payload["no_code"] = False
        elif self.number == 3:
            payload["contributions"] = list(RUNG_3_CONTRIBUTIONS)
            payload["plugin_scope"] = PLUGIN_VOCABULARY_SCOPE
            payload["desk_packs"] = list(DESK_PLUGIN_PACK_IDS)
            payload["qmb_module_is_plugin"] = QMB_MODULE_IS_PLUGIN
        elif self.number == 4:
            payload["package"] = QMA_UI_CONTRACT_PACKAGE
            payload["package_status"] = QMA_UI_CONTRACT_STATUS
            payload["ui_view_minted"] = False
        if self.gap is not None:
            payload["gap"] = self.gap
        if self.status is not None:
            payload["status"] = self.status
        return MappingProxyType(payload)


_RUNG_SPECS: Final[Mapping[int, ExtensionRungSpec]] = MappingProxyType(
    {
        1: ExtensionRungSpec(
            number=1,
            name=ExtensionRung.CONFIG_VARIABLES,
            binds=True,
            surface="ui-editable config variables on templates",
        ),
        2: ExtensionRungSpec(
            number=2,
            name=ExtensionRung.ORDINARY_PYTHON,
            binds=True,
            surface="ordinary Python logic plus QMB ports/adapters",
        ),
        3: ExtensionRungSpec(
            number=3,
            name=ExtensionRung.QMA_PACKS,
            binds=True,
            surface="QMA plugins, skills, graph templates, and desk packs",
        ),
        4: ExtensionRungSpec(
            number=4,
            name=ExtensionRung.UI_CONTRIBUTION_SDK,
            binds=False,
            surface="UI contribution SDK / qma-ui-contract",
            gap="GAP-0081",
            status=GAP_0081_STATUS,
        ),
    }
)


def enumerate_public_extension_rungs() -> tuple[ExtensionRungSpec, ...]:
    """Return the three binding rungs, in order. Rung 4 is not public."""
    return tuple(_RUNG_SPECS[number] for number in PUBLIC_EXTENSION_RUNGS)


def is_public_extension_rung(number: object) -> bool:
    return number in PUBLIC_EXTENSION_RUNGS


def ui_view_contribution_point_minted() -> bool:
    """``ui_view`` stays retired. It is not one of the eight multi points."""
    return (
        UI_VIEW_CONTRIBUTION_POINT in MULTI_CONTRIBUTION_POINTS
        or UI_VIEW_CONTRIBUTION_POINT not in RETIRED_CONTRIBUTION_POINTS
    )


def is_ui_contribution_point(point: object) -> bool:
    return isinstance(point, str) and point in UI_CONTRIBUTION_POINTS


def logic_path_is_ordinary_python() -> bool:
    """Rung 2 remains the logic path. No-code is not a rung."""
    return LOGIC_PATH_RUNG == 2 and _RUNG_SPECS[2].name is ExtensionRung.ORDINARY_PYTHON


def plugin_vocabulary_is_qma_scoped() -> bool:
    """``plugin`` names a QMA desk pack. No QMB module is a plugin (DEC-0346)."""
    return PLUGIN_VOCABULARY_SCOPE == "qma" and QMB_MODULE_IS_PLUGIN is False


def parse_extension_rung(value: ExtensionRung | int | str) -> Result[ExtensionRungSpec]:
    """Parse a rung number, name, or ``rung_N`` token."""
    if isinstance(value, ExtensionRung):
        return Ok(_RUNG_SPECS[_number_for(value)])
    if isinstance(value, int):
        spec = _RUNG_SPECS.get(value)
        if spec is None:
            return ExtensionSurfaceRefused.of(
                reason="undeclared_rung",
                surface="extension_rung",
                given=value,
            )
        return Ok(spec)
    token = value.strip().casefold().replace("-", "_")
    if token.startswith("rung_"):
        token = token.removeprefix("rung_")
    if token.isdigit():
        return parse_extension_rung(int(token))
    try:
        parsed = parse_closed(ExtensionRung, token)
    except VocabularyError as exc:
        return _invalid("rung", str(exc), given=repr(value))
    return Ok(_RUNG_SPECS[_number_for(parsed)])


def _number_for(rung: ExtensionRung) -> int:
    for number, member in _RUNG_BY_NUMBER.items():
        if member is rung:
            return number
    raise AssertionError(f"unnumbered extension rung {rung!r}")


def admit_extension_rung(value: ExtensionRung | int | str) -> Result[ExtensionRungSpec]:
    """Admit rungs 1–3. Rung 4 is GAP-0081; no-code is not a rung."""
    if isinstance(value, str) and is_no_code_authoring_request(value):
        return refuse_no_code_authoring(value)
    parsed = parse_extension_rung(value)
    if not isinstance(parsed, Ok):
        return parsed
    spec = parsed.value
    if spec.number == DEFERRED_EXTENSION_RUNG:
        return refuse_ui_contribution(UI_VIEW_CONTRIBUTION_POINT)
    if not spec.binds:
        return ExtensionSurfaceRefused.of(
            reason="undeclared_rung",
            surface="extension_rung",
            given=spec.name.value,
        )
    return Ok(spec)


def refuse_ui_contribution(point: str = UI_VIEW_CONTRIBUTION_POINT) -> UiContributionDeferred:
    """Refuse a UI widget / SDK contribution as GAP-0081 deferred."""
    return UiContributionDeferred.of(contribution_point=point)


def register_ui_widget_contribution(
    *,
    plugin_id: str,
    local_id: str,
    point: str = UI_VIEW_CONTRIBUTION_POINT,
) -> UiContributionDeferred:
    """Registration path for a UI widget. Always GAP-0081; never mints ``ui_view``."""
    return UiContributionDeferred.of(
        contribution_point=point,
        plugin_id=plugin_id,
        local_id=local_id,
    )


def refuse_no_code_authoring(request: object) -> NoCodeAuthoringRefused:
    """Refuse SQ-style DSL, RandomCondition editor, or ``.qml`` revival as a rung."""
    token = _normalize_no_code(request)
    return NoCodeAuthoringRefused.of(
        request=token,
        logic_path="ordinary_python",
        logic_rung=LOGIC_PATH_RUNG,
    )


def _normalize_no_code(request: object) -> str:
    if not isinstance(request, str) or not request.strip():
        return repr(request)
    token = request.strip().casefold().replace("-", "_")
    return _NO_CODE_ALIASES.get(token, token)


def is_no_code_authoring_request(request: object) -> bool:
    if not isinstance(request, str):
        return False
    token = _normalize_no_code(request)
    return (
        token
        in {
            "sq_building_block_dsl",
            "random_condition_editor",
            "qml_revival",
        }
        or request.strip().casefold() in NO_CODE_AUTHORING_REQUESTS
    )


def refuse_qmb_plugin_label(module: object) -> Result[str]:
    """Refuse calling a QMB module a plugin. QMA plugin vocabulary stays QMA-scoped."""
    if not isinstance(module, str) or not module:
        return _invalid("module", "QMB module path must be a non-empty string", given=repr(module))
    if module == "qmb" or module.startswith("qmb."):
        return ExtensionSurfaceRefused.of(
            reason="qmb_plugin_vocabulary",
            surface="qmb_module",
            module=module,
            plugin_scope=PLUGIN_VOCABULARY_SCOPE,
        )
    return Ok(module)


def mint_work_environment_roster_kind() -> ExtensionSurfaceRefused:
    """Work-environment roster stays a later UI alias. No kind is minted."""
    return ExtensionSurfaceRefused.of(
        reason="work_environment_roster_kind",
        surface="work_environment_roster",
        kind=WORK_ENVIRONMENT_ROSTER_KIND,
        status=str(WORK_ENVIRONMENT_ROSTER["status"]),
        over=str(WORK_ENVIRONMENT_ROSTER["over"]),
        nfr=str(WORK_ENVIRONMENT_ROSTER["nfr"]),
        fr=str(WORK_ENVIRONMENT_ROSTER["fr"]),
    )
