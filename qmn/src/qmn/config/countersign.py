"""Value-status countersign: one provisional row → ratified (DEC-0254).

A powers-channel act under the operator principal. Exactly one variable per
call; refused without the row's evidence_fp1 citation. Mints a new config
version branched from the prior artifact.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qmn.config._refuse import clean_token, invalid, policy
from qmn.config.compiler import (
    VALUE_STATUS_PROVISIONAL,
    VALUE_STATUS_RATIFIED,
    ResolvedNodeConfig,
    ResolvedValueRow,
    compile_node_config,
)
from qmn.journal_dispatch import (
    CallableDispatcher,
    WriteBoundary,
    enact_settings,
    passthrough_dispatch,
)

__all__ = ["apply_settings_edit", "countersign_value_status"]


def apply_settings_edit(
    *,
    journal: object,
    dispatcher: object,
    variable: object,
    operator_signature: object,
    config_version: object = None,
    boundary: object = WriteBoundary.ATOMIC,
) -> Result[object]:
    """Journal a settings edit before the resolved config is applied."""
    name = clean_token(variable)
    if name is None:
        return invalid(
            "variable",
            "settings_edit names exactly one variable",
            given=repr(variable),
        )
    signature = clean_token(operator_signature)
    if signature is None:
        return invalid(
            "operator_signature",
            "a settings edit requires an operator signature",
            given=repr(operator_signature),
        )
    payload = MappingProxyType(
        {
            "kind": "settings",
            "variable": name,
            "operator_signature": signature,
            "config_version": config_version,
        }
    )
    apply = dispatcher if dispatcher is not None else CallableDispatcher(passthrough_dispatch)
    return enact_settings(
        payload,
        journal=journal,
        dispatcher=apply,
        boundary=boundary,
    )


def countersign_value_status(
    config: object,
    *,
    variable: object,
    evidence_fp1: object,
    extra_variables: object = None,
) -> Result[ResolvedNodeConfig]:
    """Flip exactly one provisional-evidence row to ratified.

    ``extra_variables`` exists so a multi-row call is an explicit typed refusal
    rather than silent truncation. Missing or mismatched evidence refuses.
    """
    if not isinstance(config, ResolvedNodeConfig):
        return invalid(
            "config",
            "countersign requires a ResolvedNodeConfig",
            given=repr(type(config).__name__),
        )
    if extra_variables is not None:
        return policy(
            "variable",
            "value-status countersign is one variable per call",
            given=repr(extra_variables),
        )
    if not isinstance(variable, str) or variable.strip() == "":
        return invalid(
            "variable",
            "countersign names exactly one variable",
            given=repr(variable),
        )
    if variable not in config.rows:
        return invalid(
            "variable",
            "countersign names a value_status_required row on the artifact",
            given=variable,
        )

    cited = _as_fingerprint(evidence_fp1)
    if is_refusal(cited):
        return cited

    row = config.rows[variable]
    if row.value_status != VALUE_STATUS_PROVISIONAL:
        return policy(
            "variable",
            "countersign applies only to provisional-evidence rows",
            given=row.value_status,
            variable=variable,
        )
    if row.evidence_fp1 is None:
        return invalid(
            "evidence_fp1",
            "provisional-evidence rows carry an evidence_fp1 citation",
            variable=variable,
        )
    if row.evidence_fp1.value != cited.value.value:
        return policy(
            "evidence_fp1",
            "countersign evidence_fp1 must match the row citation",
            variable=variable,
            expected=row.evidence_fp1.value,
            given=cited.value.value,
        )

    layers = _rows_as_layer_maps(config.rows, flip={variable: cited.value})
    return compile_node_config(
        roster=layers["roster"],
        bms=layers["bms"],
        book=layers["book"],
        node_defaults=layers["node_defaults"],
        roster_identity=dict(config.roster_identity),
        config_version=config.config_version + 1,
        branches_from=config.config_version,
    )


def _rows_as_layer_maps(
    rows: Mapping[str, ResolvedValueRow],
    *,
    flip: Mapping[str, Fingerprint],
) -> dict[str, dict[str, object]]:
    """Rebuild layer maps from resolved rows so compile stamps the new version."""
    layers: dict[str, dict[str, object]] = {
        "roster": {},
        "bms": {},
        "book": {},
        "node_defaults": {},
    }
    for name, row in rows.items():
        if row.value_status == "blank" or row.source_layer is None:
            continue
        entry: dict[str, object] = {
            "value_status": (
                VALUE_STATUS_RATIFIED if name in flip else row.value_status
            ),
        }
        if row.value is not None:
            entry["value"] = row.value
        evidence = flip.get(name, row.evidence_fp1)
        if evidence is not None:
            entry["evidence_fp1"] = evidence.value
        layers[row.source_layer][name] = entry
    return layers


def _as_fingerprint(raw: object) -> Result[Fingerprint]:
    if isinstance(raw, Fingerprint):
        return Ok(raw)
    return Fingerprint.try_create(raw)
