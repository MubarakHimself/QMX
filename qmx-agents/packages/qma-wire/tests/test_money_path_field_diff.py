"""Story 45.6 — named qma-wire money_path_field_diff schema (FR-Q53)."""

from __future__ import annotations

from qma.core.ports.handles import MONEY_PATH_FIELD_DIFF_SCHEMA
from qma.wire import (
    MONEY_PATH_FIELD_DIFF_SCHEMA_FILE,
    MONEY_PATH_FIELD_DIFF_SCHEMA_NAME,
    SCHEMA_DIR,
    SCHEMA_FILES,
    validate_money_path_field_diff,
)
from qmf.core import is_ok, is_refusal


def test_named_schema_is_shipped() -> None:
    assert MONEY_PATH_FIELD_DIFF_SCHEMA == "qma.wire.money_path_field_diff.v1"
    assert SCHEMA_FILES[MONEY_PATH_FIELD_DIFF_SCHEMA_NAME] == MONEY_PATH_FIELD_DIFF_SCHEMA_FILE
    assert (SCHEMA_DIR / MONEY_PATH_FIELD_DIFF_SCHEMA_FILE).is_file()


def test_valid_diff_round_trips() -> None:
    payload = {
        "schema": MONEY_PATH_FIELD_DIFF_SCHEMA,
        "candidate_ref": "fp1:sha256:bbb",
        "predecessor_ref": "fp1:sha256:aaa",
        "fields": [{"path": "sizing", "ancestor": "1R", "proposed": "2R"}],
    }
    checked = validate_money_path_field_diff(payload)
    assert is_ok(checked)
    assert checked.value.schema == MONEY_PATH_FIELD_DIFF_SCHEMA
    assert checked.value.paths == frozenset({"sizing"})


def test_invented_schema_or_path_is_refused() -> None:
    invented = validate_money_path_field_diff(
        {
            "schema": "local.invented",
            "candidate_ref": "fp1:sha256:bbb",
            "predecessor_ref": "fp1:sha256:aaa",
            "fields": [{"path": "sizing", "ancestor": "1R", "proposed": "2R"}],
        }
    )
    assert is_refusal(invented)
    unknown_path = validate_money_path_field_diff(
        {
            "schema": MONEY_PATH_FIELD_DIFF_SCHEMA,
            "candidate_ref": "fp1:sha256:bbb",
            "predecessor_ref": "fp1:sha256:aaa",
            "fields": [{"path": "kill_switch", "ancestor": "off", "proposed": "on"}],
        }
    )
    assert is_refusal(unknown_path)
    extra = validate_money_path_field_diff(
        {
            "schema": MONEY_PATH_FIELD_DIFF_SCHEMA,
            "candidate_ref": "fp1:sha256:bbb",
            "predecessor_ref": "fp1:sha256:aaa",
            "fields": [{"path": "sizing", "ancestor": "1R", "proposed": "2R"}],
            "promotion": True,
        }
    )
    assert is_refusal(extra)
