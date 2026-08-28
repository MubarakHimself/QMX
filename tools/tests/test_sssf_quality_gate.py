"""Regression guard: the SSSF merge gate must invoke ``uv run poe check`` (OR-10c).

Findings QMX-F036 / QMX-F100 (card FC-33): the factory's merge gate re-runs the
roster's ``quality:`` commands against the rebased tree before anything lands on
``integration`` (``adws/engine.py::quality_commands`` /
``adws/adw_modules/data_types.QualityConfig``). Left at the factory defaults, that
gate re-ran the factory's OWN ``adws`` scaffolding suite and never the QMF tier-1
scanners, so a money-path float, an ambient clock read, mock data, or a committed
secret could reach ``integration`` without the gate ever running the scanner that
exists to catch it.

These tests read ``adws/adw_sssf_config/sssf.config.yaml`` (reading is allowed; the
one-line write lives in that file) and pin the fix in place so the gate cannot
silently regress: ``uv run poe check`` — the full Tier-1 sequence (fmt-check, lint,
strict types, tests + coverage, the workspace-tool suite, and the money-path /
ambient / mock-data / secret scanners) — must sit in one of the three command slots
the merge gate actually executes.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import yaml

# tools/tests/<this file> -> repo root is two parents up from the tests dir.
REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "adws" / "adw_sssf_config" / "sssf.config.yaml"

# The command the factory merge gate must run in full (OR-10c).
POE_CHECK = "uv run poe check"

# The `quality:` slots `engine.quality_commands` actually re-runs at the merge gate:
# it builds argv from (config.lint, config.typecheck, config.test) only. `scan`
# (the diff-scoped AI-defect pass) is deliberately NOT part of the merge gate, so a
# command parked there would never run — the guard checks the executed slots.
MERGE_GATE_SLOTS = ("lint", "typecheck", "test")


def _load_quality_block() -> dict[str, object]:
    """Parse the roster and return its ``quality:`` mapping.

    Fail-closed: an unreadable roster, an unparseable file, a missing ``quality:``
    block, or a non-mapping block is a hard failure here, never a silent pass — the
    same posture ``engine.quality_commands`` takes when it cannot read the roster.
    """
    assert CONFIG_PATH.is_file(), f"roster not found at {CONFIG_PATH}"
    data = cast("object", yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")))
    assert isinstance(data, dict), "sssf.config.yaml did not parse to a mapping"
    quality = cast("dict[str, object]", data).get("quality")
    assert isinstance(quality, dict), "sssf.config.yaml has no `quality:` mapping"
    return {str(key): value for key, value in cast("dict[str, object]", quality).items()}


def test_roster_quality_block_is_readable() -> None:
    # The block exists, parses, and is a non-empty mapping of named commands.
    quality = _load_quality_block()
    assert quality, "the `quality:` block is empty"


def test_merge_gate_invokes_poe_check() -> None:
    # OR-10c: `uv run poe check` must sit in a slot the merge gate actually runs
    # (lint / typecheck / test), not merely somewhere in the block. A command parked
    # in an unread key would be dead config and the gate would silently regress.
    quality = _load_quality_block()
    gate_commands = [str(quality[slot]) for slot in MERGE_GATE_SLOTS if slot in quality]
    assert POE_CHECK in gate_commands, (
        f"the merge gate must run `{POE_CHECK}` in one of {MERGE_GATE_SLOTS}; "
        f"it currently runs {gate_commands}"
    )


def test_quality_commands_list_includes_poe_check() -> None:
    # The literal command the factory gate must invoke, asserted across every value
    # in the block so the pin holds regardless of which slot carries it.
    quality = _load_quality_block()
    commands = [str(value) for value in quality.values()]
    assert POE_CHECK in commands, f"`{POE_CHECK}` is missing from the quality commands: {commands}"


@pytest.mark.parametrize("slot", MERGE_GATE_SLOTS)
def test_merge_gate_slots_are_non_empty(slot: str) -> None:
    # A merge-gate slot emptied to "" is recorded NOT VERIFIED, never a pass
    # (data_types.QualityConfig); keep all three carrying a real command.
    quality = _load_quality_block()
    assert slot in quality, f"the `{slot}` merge-gate slot is missing from the roster"
    assert str(quality[slot]).strip(), f"the `{slot}` merge-gate slot is empty"
