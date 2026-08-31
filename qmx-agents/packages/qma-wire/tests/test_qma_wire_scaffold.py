"""Structural-seed smoke for qma-wire (Story 40.1)."""

from __future__ import annotations

from pathlib import Path

import qma.wire

SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"


def test_version_display_only() -> None:
    assert qma.wire.__version__ == "0.1.0"


def test_message_family_schemas_present() -> None:
    expected = {
        "envelope.v1.schema.json",
        "command.v1.schema.json",
        "query.v1.schema.json",
        "event.v1.schema.json",
        "initialize.v1.schema.json",
        "host_request.v1.schema.json",
    }
    found = {p.name for p in SCHEMAS.glob("*.schema.json")}
    assert expected <= found
