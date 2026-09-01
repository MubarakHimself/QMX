"""Story 26.13 / QMX-F069 — FAILURES.md completeness CI gate."""

from __future__ import annotations

from typing import TypeVar

from qmf.core.refusal import Result, is_ok, is_refusal
from qmn.doors.catalog import CLOSED_POWERS
from qmn.doors.library import EVIDENCE_CAPABILITIES, POWERS_CAPABILITIES
from qmn.observability import (
    NFR11_REQUIRED_FIELDS,
    PUSH_ALERT_CLASSES,
    default_failures_path,
    generate_alert_allow_list,
    load_alert_allow_list,
    parse_failures_register,
    push_classes_for_tier,
)
from qmn.observability.failures_gate import (
    DESIGNED_TYPED_FAILURE_IDS,
    collect_emitted_failure_ids,
    operations_toolkit_recipes,
    resolve_operator_affordance,
    validate_failures_completeness,
)
from qmn.time import CLOCK_BAND_FAILURE_IDS

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def test_failures_completeness_gate_passes_on_the_register() -> None:
    report = _ok(validate_failures_completeness())
    assert report.entries
    assert NFR11_REQUIRED_FIELDS == (
        "Failure class",
        "Detection",
        "Auto-recovery / retry",
        "Visible degraded state",
        "Notification tier",
        "Product-user affordance",
    )
    emitted = collect_emitted_failure_ids()
    assert emitted
    assert report.emitted_ids == emitted
    for failure_id in CLOCK_BAND_FAILURE_IDS.values():
        assert failure_id in report.registered_ids
        assert failure_id in DESIGNED_TYPED_FAILURE_IDS
    for failure_id in emitted:
        assert failure_id in report.registered_ids or any(
            failure_id.startswith(f"{parent}.")
            for parent in report.registered_ids
            if "." in parent
        )
    for failure_id in DESIGNED_TYPED_FAILURE_IDS:
        assert failure_id in report.registered_ids or any(
            failure_id.startswith(f"{parent}.")
            for parent in report.registered_ids
            if "." in parent
        )
    for fr_id, resolved in report.affordances.items():
        assert resolved, fr_id
        named = (
            CLOSED_POWERS
            | frozenset(EVIDENCE_CAPABILITIES)
            | frozenset(POWERS_CAPABILITIES)
            | operations_toolkit_recipes()
        )
        assert resolved <= named | {
            "enact_power",
            "node-config-validate",
        }


def test_allow_list_matches_notification_column_exactly() -> None:
    entries = _ok(parse_failures_register(default_failures_path()))
    generated = _ok(generate_alert_allow_list(entries))
    loaded = _ok(load_alert_allow_list())
    assert tuple(generated.by_class.keys()) == PUSH_ALERT_CLASSES
    for class_name in PUSH_ALERT_CLASSES:
        assert generated.by_class[class_name] == loaded.by_class[class_name]
    rebuilt: dict[str, set[str]] = {name: set() for name in PUSH_ALERT_CLASSES}
    for entry in entries:
        for class_name in push_classes_for_tier(entry.notification_tier):
            rebuilt[class_name].add(entry.fr_id)
            rebuilt[class_name].update(entry.detection_failure_ids)
    for class_name in PUSH_ALERT_CLASSES:
        assert set(generated.by_class[class_name]) == rebuilt[class_name]


def test_missing_duplicate_and_orphan_rows_fail() -> None:
    empty = generate_alert_allow_list(())
    assert is_refusal(empty)

    duplicate_text = """
### FR-1: Dup one

- **Failure class:** policy rejection
- **Detection:** `clock.band.warn`
- **Auto-recovery / retry:** none
- **Visible degraded state:** blocked
- **Notification tier:** silent-degradation
- **Product-user affordance:** Retry from the desktop UI over the powers channel.

### FR-1: Dup two

- **Failure class:** policy rejection
- **Detection:** `clock.band.warn`
- **Auto-recovery / retry:** none
- **Visible degraded state:** blocked
- **Notification tier:** silent-degradation
- **Product-user affordance:** Retry from the desktop UI over the powers channel.
"""
    duplicated = generate_alert_allow_list(_ok(parse_failures_register(duplicate_text)))
    assert is_refusal(duplicated)
    assert duplicated.context["fr_id"] == "FR-1"

    import tempfile
    from pathlib import Path

    missing_text = """
### FR-1: Incomplete coverage

- **Failure class:** policy rejection
- **Detection:** `clock.band.warn`
- **Auto-recovery / retry:** none
- **Visible degraded state:** blocked
- **Notification tier:** silent-degradation
- **Product-user affordance:** Retry from the desktop UI over the powers channel.
"""
    orphan_text = """
### FR-1: Orphan detection

- **Failure class:** policy rejection
- **Detection:** `not.a.designed.failure`
- **Auto-recovery / retry:** none
- **Visible degraded state:** blocked
- **Notification tier:** operator-visible (journaled)
- **Product-user affordance:** Inspect `read_failure_detail` on the evidence channel.
"""
    with tempfile.TemporaryDirectory() as tmp:
        missing_path = Path(tmp) / "missing.md"
        missing_path.write_text(missing_text, encoding="utf-8")
        missing = validate_failures_completeness(
            missing_path,
            emitted_ids=frozenset({"clock.band.warn", "storage.partial_write"}),
            designed_ids=frozenset({"clock.band.warn", "storage.partial_write"}),
        )
        assert is_refusal(missing)
        assert "storage.partial_write" in missing.context.get("missing_emitted", ()) or (
            "storage.partial_write" in missing.context.get("missing_designed", ())
        )

        orphan_path = Path(tmp) / "orphan.md"
        orphan_path.write_text(orphan_text, encoding="utf-8")
        orphan = validate_failures_completeness(
            orphan_path,
            emitted_ids=frozenset(),
            designed_ids=frozenset(),
        )
        assert is_refusal(orphan)
        assert "not.a.designed.failure" in orphan.context.get("orphan", ())


def test_blank_nfr11_field_fails_completeness() -> None:
    import tempfile
    from pathlib import Path

    blank = """
### FR-1: Blank detection

- **Failure class:** policy rejection
- **Detection:**
- **Auto-recovery / retry:** none
- **Visible degraded state:** blocked
- **Notification tier:** operator-visible (journaled)
- **Product-user affordance:** Inspect `read_failure_detail` on the evidence channel.
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "FAILURES.md"
        path.write_text(blank, encoding="utf-8")
        refused = validate_failures_completeness(path)
        assert is_refusal(refused)


def test_affordance_resolves_to_existing_door_or_recipe() -> None:
    recipes = operations_toolkit_recipes()
    assert "node-config-validate" in recipes
    assert "node-notify-test" in recipes
    resolved = resolve_operator_affordance(
        "Retry from the desktop UI over the powers channel; resurrect via the "
        "operations toolkit.",
        recipes=recipes,
    )
    assert "enact_power" in resolved
    assert "resurrect" in resolved
    assert "node-config-validate" in resolved
    empty = resolve_operator_affordance("something broke")
    assert empty == frozenset()


def test_emitted_scan_is_independent_of_the_catalog_module() -> None:
    from qmn.observability.failures_gate import qmn_src_root

    emitted = collect_emitted_failure_ids()
    assert "storage.journal_before_dispatch" in emitted
    assert "storage.partial_write" in emitted
    assert "storage.log_only_path" in emitted
    assert "storage.best_effort_path" in emitted
    assert "preflight.config.boot_blocking" in emitted
    assert "compose.light_heavy.no_baseline" in emitted
    scanned = collect_emitted_failure_ids(qmn_src_root())
    # failures_gate.py is excluded; catalog membership is not emission.
    assert scanned == emitted
