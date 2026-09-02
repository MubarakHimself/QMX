"""CI gate: FAILURES.md completeness against emitted typed failure IDs (QMX-F069).

Three independently collected sets:

* **emitted** — AST scan of ``qmn/src`` ``failure_id`` string literals (this
  module is excluded so the catalog cannot satisfy the scan by existing).
* **designed** — :data:`DESIGNED_TYPED_FAILURE_IDS`, the closed inventory of
  dotted typed-failure ids the node may emit, including dormant rows.
* **register** — ``qmn/FAILURES.md`` FR rows plus dotted detection ids.

Missing (emitted or designed not covered by the register), duplicate FR ids,
orphan detection ids, blank NFR-11 fields, and affordances that resolve to no
named door capability or operations-toolkit recipe all fail. The generated
alert allow-list is required to match the notification-tier column exactly.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final

from qmf.core import Ok, Result, is_refusal

from qmn.observability._refuse import invalid, policy
from qmn.observability.alerts import (
    NFR11_REQUIRED_FIELDS,
    PUSH_ALERT_CLASSES,
    AlertAllowList,
    FailureRegisterEntry,
    default_failures_path,
    generate_alert_allow_list,
    parse_failures_register,
    push_classes_for_tier,
)
from qmn.time import CLOCK_BAND_FAILURE_IDS

__all__ = [
    "DESIGNED_TYPED_FAILURE_IDS",
    "FAILURES_GATE_SURFACE",
    "FailuresCompletenessReport",
    "collect_emitted_failure_ids",
    "operations_toolkit_recipes",
    "qmn_src_root",
    "resolve_operator_affordance",
    "validate_failures_completeness",
]

FAILURES_GATE_SURFACE: Final[str] = "qmn.observability.failures_gate"

# Closed designed inventory — independent of FAILURES.md (QMX-F069).
# Dotted typed-failure ids the node may emit, including dormant/invariant rows.
DESIGNED_TYPED_FAILURE_IDS: Final[frozenset[str]] = frozenset(
    {
        "boot.attempt.amend",
        "boot.attempt.write",
        "clock.band.halt",
        "clock.band.no_new_entry",
        "clock.band.warn",
        "clock.divergence.suspect_window",
        "clock.sync.unsynchronized",
        "compose.light_heavy",
        "compose.light_heavy.heavy_dependency",
        "compose.light_heavy.missing_dependency",
        "compose.light_heavy.no_baseline",
        "compose.light_heavy.unmet_bounds",
        "compose.risk_population",
        "compose.risk_population.cardinalities",
        "compose.risk_population.declared_scopes",
        "compose.risk_population.netting_partitions",
        "compose.risk_population.one_active_paper_target",
        "compose.risk_population.one_bms_per_account",
        "compose.risk_population.one_book_per_bot",
        "compose.risk_population.referential_integrity",
        "compose.risk_population.total_unique_rank",
        "compose.writer_ids",
        "compose.shadow_isolation",
        "data.backup.backblaze_tonight",
        "data.backup.blank_row",
        "data.backup.ceremony_tonight",
        "data.backup.custody",
        "data.backup.destructive_fallback",
        "data.backup.journal",
        "data.backup.missing_bucket_account",
        "data.backup.missing_key",
        "data.backup.mutate_existing",
        "data.backup.processed_excluded",
        "data.backup.provider_default_retention",
        "data.backup.rclone_transfer",
        "data.backup.rpo_not_derived",
        "data.backup.rto_conflated",
        "data.backup.rto_not_from_drill",
        "data.backup.secret_in_evidence",
        "data.backup.trading_power",
        "data.backup.two_copy",
        "data.backup.uncommitted",
        "data.backup.unverified_purge",
        "data.backup.venue_shared_custody",
        "data.backup.vps_minted_key",
        "data.backup.world",
        "data.backup.wrong_key",
        "data.backup.retention_window",
        "data.bootstrap.ad_hoc",
        "data.bootstrap.live_network",
        "data.bootstrap.span_cap",
        "data.intake.ftr01_mapping",
        "data.intake.observation_journal_type",
        "data.intake.sibling_failover",
        "data.news_calendar.budget_breach",
        "data.news_calendar.failed_refresh",
        "data.news_calendar.live_skip",
        "data.news_calendar.paid_provider",
        "data.news_calendar.second_source",
        "data.news_calendar.stale",
        "data.purge.journal",
        "data.purge.missing_off_host",
        "data.purge.missing_sealed",
        "data.purge.monitoring_is_not_restore",
        "data.purge.retained_forever",
        "data.purge.retention_window",
        "data.restore.clean_host_tonight",
        "data.restore.cutover",
        "data.restore.journal",
        "data.restore.kind",
        "data.restore.missing_copy",
        "data.restore.pull",
        "data.restore.sample_rto",
        "data.restore.silent_retry",
        "data.restore.verify_mismatch",
        "data.restore.wrong_writer",
        "data.sealed.loop_blocking",
        "data.sealed.off_host_infra",
        "data.sealed.second_writer",
        "data.sealed.uncommitted",
        "data.sealed.verify_mismatch",
        "data.sealed.world",
        "hub.inbound_crossing",
        "hub.inbox.read",
        "hub.published.write",
        "hub.sync_into_inbox",
        "hub.writer_scope",
        "fingerprint.composition_fp",
        "first_deployment.book_routing",
        "first_deployment.continuous_supervision",
        "first_deployment.demo_roster",
        "first_deployment.late_approval_blocks_demo",
        "first_deployment.live_binding",
        "first_deployment.live_command_stream",
        "first_deployment.live_execution_target",
        "first_deployment.live_sequencer",
        "first_deployment.open_live_credentials",
        "first_deployment.pre_unattended",
        "first_deployment.procure_vps",
        "lifecycle.stand_down",
        "money.boundary.re_seed",
        "money.boundary.refund",
        "money.boundary.sweep",
        "preflight.clock.chrony",
        "preflight.config.boot_blocking",
        "preflight.detected",
        "protection.kill_switch",
        "protection.ksa.escalation",
        "readiness.commit_lineage",
        "readiness.demo_roster",
        "readiness.failure_register",
        "readiness.invented_ksa_or_latency",
        "readiness.machine_gate",
        "readiness.procure_vps",
        "readiness.ratified_vps_minimum",
        "readiness.settings_status",
        "readiness.unrelated_epic_blocker",
        "replay.admission_gate",
        "replay.clock_exhaustion",
        "replay.command_submit",
        "replay.credential_bind",
        "replay.cross_world_write",
        "replay.disjoint_writer",
        "replay.fill_simulation",
        "replay.import_port_required",
        "replay.in_node_process",
        "replay.ledger.collision",
        "replay.ledger.rewrite",
        "replay.ledger.storage",
        "replay.live_sink",
        "replay.live_venue_client",
        "replay.missing_sealed_interval",
        "replay.network",
        "replay.restore_into_live",
        "replay.secret_resolved",
        "replay.sqs_recompute",
        "replay.wrong_world",
        "risk_gate.manual_observation",
        "risk_gate.paper_profit",
        "risk_gate.unwired_contract",
        "secrets.drill.not_demo",
        "secrets.holder.fifth",
        "secrets.holder.scope",
        "secrets.holder.unknown",
        "secrets.rotation.in_flight",
        "secrets.rotation.store_failed",
        "secrets.store.missing",
        "secrets.store.off_host",
        "secrets.surface.value_leak",
        "storage.best_effort_path",
        "storage.journal_before_dispatch",
        "storage.log_only_path",
        "storage.partial_write",
        "supervision.fail_closed",
    }
)

_TYPED_ID = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")
_FR_ID = re.compile(r"^FR-\d+$")
_RECIPE_HEADER = re.compile(r"^([a-z][a-z0-9-]*)\s")
_SKIP_SCAN_NAMES: Final[frozenset[str]] = frozenset({"failures_gate.py"})

# Phrases in product-user affordance text that resolve to a named capability.
_AFFORDANCE_PHRASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "activation": "activation",
        "operator identity": "enact_power",
        "published area": "hub_publish",
        "de-escalate": "de_escalate",
        "de_escalate": "de_escalate",
        "desktop ui": "enact_power",
        "evidence channel": "read_status",
        "flatten": "flatten",
        "operations toolkit": "node-config-validate",
        "ops-toolkit": "node-config-validate",
        "ops toolkit": "node-config-validate",
        "operator principal": "enact_power",
        "powers channel": "enact_power",
        "promotion click": "promotion_sign",
        "promotion": "promotion_sign",
        "read_failure_detail": "read_failure_detail",
        "read_health": "read_health",
        "read_status": "read_status",
        "reinstate": "seat_reinstate",
        "resurrect": "resurrect",
        "seat_reinstate": "seat_reinstate",
        "settings": "settings_edit",
        "status/health": "read_status",
    }
)


@dataclass(frozen=True, slots=True)
class FailuresCompletenessReport:
    """Result of the NFR-11 / TN-23 completeness gate."""

    entries: tuple[FailureRegisterEntry, ...]
    emitted_ids: frozenset[str]
    designed_ids: frozenset[str]
    registered_ids: frozenset[str]
    allow_list: AlertAllowList
    affordances: Mapping[str, frozenset[str]]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "entry_count": len(self.entries),
                "emitted_ids": tuple(sorted(self.emitted_ids)),
                "designed_ids": tuple(sorted(self.designed_ids)),
                "registered_ids": tuple(sorted(self.registered_ids)),
                "allow_list_members": tuple(sorted(self.allow_list.member_ids)),
            }
        )


def qmn_src_root() -> Path:
    """``qmn/src/qmn`` — production sources for the emitted-id scan."""
    return Path(__file__).resolve().parents[1]


def operations_toolkit_recipes(justfile: Path | None = None) -> frozenset[str]:
    """Recipe names from ``qmn/deploy/justfile-recipes/node.just``."""
    path = justfile if justfile is not None else _default_node_just()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return frozenset()
    found: set[str] = set()
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _RECIPE_HEADER.match(stripped)
        if match is None:
            continue
        name = match.group(1)
        if name.startswith("node-"):
            found.add(name)
    return frozenset(found)


def collect_emitted_failure_ids(src_root: Path | None = None) -> frozenset[str]:
    """AST-scan production sources for ``failure_id`` string literals."""
    root = src_root if src_root is not None else qmn_src_root()
    found: set[str] = set()
    for path in sorted(root.rglob("*.py")):
        if path.name in _SKIP_SCAN_NAMES:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg != "failure_id":
                        continue
                    token = _const_str(keyword.value)
                    if token is not None:
                        found.add(token)
                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "get"
                    and len(node.args) >= 2
                ):
                    key = _const_str(node.args[0])
                    default = _const_str(node.args[1])
                    if key == "failure_id" and default is not None:
                        found.add(default)
            elif isinstance(node, ast.Dict):
                for key_node, value_node in zip(node.keys, node.values, strict=False):
                    if _const_str(key_node) != "failure_id":
                        continue
                    token = _const_str(value_node)
                    if token is not None:
                        found.add(token)
    found.update(CLOCK_BAND_FAILURE_IDS.values())
    return frozenset(token for token in found if token)


def resolve_operator_affordance(
    text: object,
    *,
    recipes: frozenset[str] | None = None,
) -> frozenset[str]:
    """Map an affordance cell onto named door capabilities or ``just node-…`` recipes."""
    if not isinstance(text, str) or text.strip() == "":
        return frozenset()
    lowered = text.lower()
    named = recipes if recipes is not None else operations_toolkit_recipes()
    found: set[str] = set()
    powers, evidence, power_caps = _door_names()
    for phrase, target in _AFFORDANCE_PHRASES.items():
        if phrase in lowered:
            found.add(target)
    for power in powers:
        needle = power.replace("_", " ")
        if power in lowered or needle in lowered or power.replace("_", "-") in lowered:
            found.add(power)
    for capability in (*evidence, *power_caps):
        if capability in lowered:
            found.add(capability)
    for recipe in named:
        if recipe in lowered:
            found.add(recipe)
    return frozenset(found)


def validate_failures_completeness(
    path: str | Path | None = None,
    *,
    src_root: Path | None = None,
    emitted_ids: frozenset[str] | None = None,
    designed_ids: frozenset[str] | None = None,
) -> Result[FailuresCompletenessReport]:
    """Gate FAILURES.md against emitted ids, designed ids, and the allow-list.

    ``path`` may be a Path (contained O_NOFOLLOW read of FAILURES.md) or the
    markdown text itself for fixture coverage without leaving the qmn root.
    """
    target: str | Path = path if path is not None else default_failures_path()
    parsed = parse_failures_register(target)
    if is_refusal(parsed):
        return parsed
    entries = parsed.value

    seen_fr: set[str] = set()
    registered: set[str] = set()
    blank_fields: list[str] = []
    duplicate: list[str] = []
    affordances: dict[str, frozenset[str]] = {}
    recipes = operations_toolkit_recipes()
    unresolved: list[str] = []

    for entry in entries:
        if entry.fr_id in seen_fr:
            duplicate.append(entry.fr_id)
        seen_fr.add(entry.fr_id)
        registered.add(entry.fr_id)
        mapping = {
            "Failure class": entry.failure_class,
            "Detection": entry.detection,
            "Auto-recovery / retry": entry.auto_recovery,
            "Visible degraded state": entry.visible_degraded_state,
            "Notification tier": entry.notification_tier,
            "Product-user affordance": entry.product_user_affordance,
        }
        missing = [name for name in NFR11_REQUIRED_FIELDS if not mapping[name].strip()]
        if missing:
            blank_fields.append(f"{entry.fr_id}:{','.join(missing)}")
        for detection_id in entry.detection_failure_ids:
            if _is_typed_failure_id(detection_id):
                registered.add(detection_id)
        resolved = resolve_operator_affordance(
            entry.product_user_affordance,
            recipes=recipes,
        )
        affordances[entry.fr_id] = resolved
        if not resolved:
            unresolved.append(entry.fr_id)

    if duplicate:
        return invalid(
            "fr_id",
            "duplicate FAILURES.md entry id",
            fr_id=duplicate[0],
            duplicates=tuple(duplicate),
        )
    if blank_fields:
        return invalid(
            "failures_register",
            "every FAILURES.md entry needs all six NFR-11 fields populated",
            blank=tuple(blank_fields),
        )

    emitted = emitted_ids if emitted_ids is not None else collect_emitted_failure_ids(src_root)
    designed = (
        designed_ids
        if designed_ids is not None
        else DESIGNED_TYPED_FAILURE_IDS | frozenset(CLOCK_BAND_FAILURE_IDS.values())
    )
    covered = frozenset(registered)

    missing_emitted = tuple(
        sorted(token for token in emitted if not _covered_by_register(token, covered))
    )
    missing_designed = tuple(
        sorted(token for token in designed if not _covered_by_register(token, covered))
    )
    if missing_emitted or missing_designed:
        return policy(
            "failures_register",
            "typed failure ids missing from FAILURES.md",
            missing_emitted=missing_emitted,
            missing_designed=missing_designed,
        )

    orphans = tuple(
        sorted(
            token
            for token in covered
            if _is_typed_failure_id(token) and token not in designed and token not in emitted
        )
    )
    if orphans:
        return policy(
            "failures_register",
            "orphan FAILURES.md detection ids are not designed or emitted",
            orphan=orphans,
        )

    if unresolved:
        return policy(
            "product_user_affordance",
            "every operator affordance must resolve to a named door capability "
            "or operations-toolkit recipe that exists",
            unresolved=unresolved,
        )

    generated = generate_alert_allow_list(entries)
    if is_refusal(generated):
        return generated
    allow_list = generated.value
    expected_by_class = _allow_list_from_notification_column(entries)
    observed = {name: set(allow_list.by_class[name]) for name in PUSH_ALERT_CLASSES}
    if observed != expected_by_class:
        return policy(
            "allow_list",
            "generated alert allow-list must match the notification-tier column exactly",
            expected={name: tuple(sorted(expected_by_class[name])) for name in PUSH_ALERT_CLASSES},
            observed={name: tuple(sorted(observed[name])) for name in PUSH_ALERT_CLASSES},
        )

    return Ok(
        FailuresCompletenessReport(
            entries=entries,
            emitted_ids=emitted,
            designed_ids=designed,
            registered_ids=frozenset(registered),
            allow_list=allow_list,
            affordances=MappingProxyType(affordances),
        )
    )


def _allow_list_from_notification_column(
    entries: tuple[FailureRegisterEntry, ...],
) -> dict[str, set[str]]:
    """Rebuild the closed allow-list solely from notification-tier cells."""
    by_class: dict[str, set[str]] = {name: set() for name in PUSH_ALERT_CLASSES}
    for entry in entries:
        classes = push_classes_for_tier(entry.notification_tier)
        for class_name in classes:
            by_class[class_name].add(entry.fr_id)
            for detection_id in entry.detection_failure_ids:
                by_class[class_name].add(detection_id)
    return by_class


def _covered_by_register(token: str, registered: frozenset[str]) -> bool:
    if token in registered:
        return True
    # Prefix match: compose.light_heavy.no_baseline is covered by compose.light_heavy
    # only when the parent itself is a registered detection id.
    parts = token.split(".")
    for index in range(len(parts) - 1, 1, -1):
        parent = ".".join(parts[:index])
        if parent in registered:
            return True
    return False


def _is_typed_failure_id(token: str) -> bool:
    if _FR_ID.match(token) is not None:
        return False
    if token.startswith("qmn."):
        return False
    if ":" in token:
        return False
    return _TYPED_ID.match(token) is not None


def _const_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.strip():
        return node.value.strip()
    return None


def _default_node_just() -> Path:
    return Path(__file__).resolve().parents[3] / "deploy" / "justfile-recipes" / "node.just"


def _door_names() -> tuple[frozenset[str], tuple[str, ...], tuple[str, ...]]:
    """Late-import door catalogs so this module cannot cycle package init."""
    from qmn.doors.catalog import CLOSED_POWERS  # noqa: PLC0415
    from qmn.doors.library import EVIDENCE_CAPABILITIES, POWERS_CAPABILITIES  # noqa: PLC0415

    return CLOSED_POWERS, EVIDENCE_CAPABILITIES, POWERS_CAPABILITIES
