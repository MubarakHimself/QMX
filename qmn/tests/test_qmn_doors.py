"""Story 25.8 — three parity-tested, UI-ready doors (FR-069 / TN-17)."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, cast

from qmf.core.refusal import Result, is_ok, is_refusal
from qmn.config import config_init
from qmn.doors import api, library, parity
from qmn.doors.http import evidence
from qmn.doors.http.dispatch import handle_powers_call, render_powers_response
from qmn.doors.http.evidence import handle_evidence_request, render_evidence_http
from qmn.doors.http.powers import (
    CLOSED_POWERS,
    DeclaredPrincipals,
    PeerCredential,
    RecordingPowersJournal,
    declare_principals,
)
from qmn.doors.library import DoorRuntime, PowersEnactment, enact_power, read_status
from qmn.doors.wire import WIRE_FORMAT_VERSION, refusal_wire_shape

from qmn import doors

T = TypeVar("T")

_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn"
_OPERATOR_UID = 1000
_OPS_UID = 1001
_SERVICE_UID = 1002


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _runtime(
    *,
    evidence_channel_budget: int = 100,
    knowledge_time_ns: int = 1_000,
) -> DoorRuntime:
    return DoorRuntime(
        boot_epoch="boot-1",
        composition_fp="fp1:composition",
        knowledge_time_ns=knowledge_time_ns,
        watermark_ns=900,
        source_time_ns=950,
        receive_time_ns=980,
        evidence_channel_budget=evidence_channel_budget,
        config=_ok(config_init()),
        failures={
            "FR-1": {"category": "policy rejection", "summary": "unknown peer"},
        },
        projections={"veto_ledger": [{"role": "live", "row": 1}]},
        metrics={"qmn_evidence_reads": 0},
    )


def _principals() -> DeclaredPrincipals:
    return _ok(
        declare_principals(
            operator_uid=_OPERATOR_UID,
            ops_uid=_OPS_UID,
            service_account_uid=_SERVICE_UID,
        )
    )


def test_shipped_doors_are_exactly_three_without_cli_or_mcp() -> None:
    assert doors.shipped_doors() == ("python_api", "evidence_http", "powers_unix")
    assert doors.HAS_OPERATOR_CLI_DOOR is False
    assert doors.CLI_IN_DOOR_SET is False
    assert doors.AGENT_MCP_IN_DOOR_SET is False
    assert not (_SRC / "doors" / "cli").exists()
    assert not (_SRC / "doors" / "mcp").exists()
    identity = doors.door_parity_identity()
    assert identity["cli_in_door_set"] is False
    assert identity["agent_mcp_in_door_set"] is False
    assert identity["derived_reconciliation"] is True


def test_derived_door_parity_holds_across_unequal_doors() -> None:
    gaps = doors.capability_gaps()
    assert gaps["missing_evidence_from_api"] == ()
    assert gaps["missing_powers_from_api"] == ()
    assert set(cast("tuple[str, ...]", gaps["evidence_http"])).issubset(
        set(cast("tuple[str, ...]", gaps["api"]))
    )
    assert set(cast("tuple[str, ...]", gaps["powers_unix"])).issubset(
        set(cast("tuple[str, ...]", gaps["api"]))
    )
    # Injected counter-case proves the reconciler is live, not a tautology.
    broken = doors.capability_gaps(api_names=frozenset())
    assert broken["missing_evidence_from_api"] != ()
    assert broken["missing_powers_from_api"] != ()


def test_api_reexports_are_identity_equal_to_library() -> None:
    for name in library.library_capability_names():
        assert getattr(api, name) is getattr(library, name)
    assert api.read_status is read_status
    assert api.enact_power is enact_power
    assert parity.api_capability_surface() == library.library_capability_names()


def test_evidence_and_api_return_equivalent_status_payload() -> None:
    runtime = _runtime()
    via_api = _ok(api.read_status(runtime))
    runtime_http = _runtime()
    via_http = _ok(handle_evidence_request(runtime_http, method="GET", path="/status"))
    for key in (
        "boot_epoch",
        "composition_fp",
        "knowledge_time_ns",
        "authority_source",
        "source_time_ns",
        "receive_time_ns",
        "watermark_ns",
        "capability",
        "acts",
        "publishes",
        "wire_format_version",
    ):
        assert via_api[key] == via_http[key]
    assert via_api["acts"] is False
    assert via_api["publishes"] is True
    assert via_api["wire_format_version"] == WIRE_FORMAT_VERSION


def test_evidence_channel_publishes_never_acts_and_carries_provenance() -> None:
    runtime = _runtime()
    for path in ("/status", "/health", "/projections", "/config/explain", "/metrics"):
        payload = _ok(handle_evidence_request(runtime, method="GET", path=path))
        assert payload["acts"] is False
        assert payload["publishes"] is True
        assert payload["boot_epoch"] == "boot-1"
        assert payload["composition_fp"] == "fp1:composition"
        assert payload["knowledge_time_ns"] == 1_000
        assert payload["authority_source"] == "live-authoritative"
        assert "watermark_ns" in payload

    refused = handle_evidence_request(runtime, method="POST", path="/status")
    assert is_refusal(refused)
    assert refused.context["acts"] is False
    rendered = render_evidence_http(refused)
    assert rendered["as_evidence"] is True
    assert rendered["category"] == "policy rejection"


def test_evidence_budget_and_failure_detail() -> None:
    runtime = _runtime(evidence_channel_budget=1)
    _ok(handle_evidence_request(runtime, method="GET", path="/status"))
    exhausted = handle_evidence_request(runtime, method="GET", path="/health")
    assert is_refusal(exhausted)
    assert exhausted.context["field"] == "evidence_channel_budget"
    assert doors.EVIDENCE_CHANNEL_BUDGET_UNIT == "request-count-per-boot-epoch"

    runtime2 = _runtime()
    detail = _ok(handle_evidence_request(runtime2, method="GET", path="/failures/FR-1"))
    assert detail["failure_id"] == "FR-1"
    missing = handle_evidence_request(runtime2, method="GET", path="/failures/missing")
    assert is_refusal(missing)
    assert missing.category.value == "stale evidence"


def test_health_states_are_independent_not_one_colour() -> None:
    payload = _ok(api.read_health(_runtime()))
    assert payload["collapsed_global_colour"] is False
    states = cast("Mapping[str, Mapping[str, object]]", payload["states"])
    assert "safety" in states and "lifecycle" in states
    assert states["safety"]["authority_source"] == "live-authoritative"


def test_powers_and_api_share_enact_function_and_refusal_shape() -> None:
    runtime = _runtime()
    principals = _principals()
    peer = PeerCredential(pid=1, uid=_OPS_UID, gid=10)
    journal = RecordingPowersJournal()

    via_dispatch = _ok(
        handle_powers_call(
            runtime,
            peer=peer,
            principals=principals,
            power="notify_test",
            artifact_key="notify-1",
            evidence_knowledge_time_ns=1_000,
            requested={"channel": "ops"},
            claimed_signer="ops-human",
            journal=journal,
        )
    )
    runtime2 = _runtime()
    via_api = _ok(
        api.enact_power(
            runtime2,
            power="notify_test",
            principal="ops",
            artifact_key="notify-1",
            evidence_knowledge_time_ns=1_000,
            requested={"channel": "ops"},
        )
    )
    assert via_dispatch.power == via_api.power == "notify_test"
    assert via_dispatch.enforced["status"] == via_api.enforced["status"] == "notified"
    assert doors.handle_powers_call is handle_powers_call

    # Same refusal shape across doors for an unknown power.
    api_refusal = api.enact_power(
        _runtime(),
        power="not-a-power",
        principal="operator",
        artifact_key="x",
        evidence_knowledge_time_ns=1_000,
        requested={},
    )
    http_refusal = handle_powers_call(
        _runtime(),
        peer=PeerCredential(pid=1, uid=_OPERATOR_UID, gid=10),
        principals=principals,
        power="not-a-power",
        artifact_key="x",
        evidence_knowledge_time_ns=1_000,
        requested={},
        claimed_signer="operator",
        journal=RecordingPowersJournal(),
    )
    assert is_refusal(api_refusal) and is_refusal(http_refusal)
    assert (
        refusal_wire_shape(api_refusal)["category"] == refusal_wire_shape(http_refusal)["category"]
    )
    api_context = cast("Mapping[str, object]", refusal_wire_shape(api_refusal)["context"])
    assert api_context["field"] == "power"


def test_stale_evidence_cannot_authorize_powers_call() -> None:
    runtime = _runtime(knowledge_time_ns=5_000)
    refused = api.enact_power(
        runtime,
        power="notify_test",
        principal="ops",
        artifact_key="stale-1",
        evidence_knowledge_time_ns=4_999,
        requested={},
    )
    assert is_refusal(refused)
    assert refused.category.value == "stale evidence"
    assert "stale evidence cannot authorize" in str(refused.context["reason"])


def test_powers_enactment_type_roundtrip() -> None:
    enactment = _ok(
        api.enact_power(
            _runtime(),
            power="notify_test",
            principal="ops",
            artifact_key="typed-1",
            evidence_knowledge_time_ns=1_000,
            requested={},
        )
    )
    assert isinstance(enactment, PowersEnactment)


def test_powers_idempotent_by_artifact_key_and_journals_requested_vs_enforced() -> None:
    runtime = _runtime()
    first = _ok(
        api.enact_power(
            runtime,
            power="hub_publish",
            principal="ops",
            artifact_key="frag-1",
            evidence_knowledge_time_ns=1_000,
            requested={"fragment_fp1": "fp1:frag", "provenance": "live"},
        )
    )
    assert first.was_idempotent is False
    assert runtime.hub_published == ["fp1:frag"]

    second = _ok(
        api.enact_power(
            runtime,
            power="hub_publish",
            principal="ops",
            artifact_key="frag-1",
            evidence_knowledge_time_ns=1_000,
            requested={"fragment_fp1": "fp1:frag", "provenance": "live"},
        )
    )
    assert second.was_idempotent is True
    assert runtime.hub_published == ["fp1:frag"]  # no duplicate act

    phases = [row["phase"] for row in runtime.journals if row.get("kind") == "powers-enactment"]
    assert "requested" in phases
    assert "enforced" in phases
    assert "idempotent-replay" in phases
    # Requested and enforced are separate journal records on the first act.
    requested_rows = [r for r in runtime.journals if r.get("phase") == "requested"]
    enforced_rows = [r for r in runtime.journals if r.get("phase") == "enforced"]
    assert len(requested_rows) == 1
    assert len(enforced_rows) == 1
    assert "enforced" not in requested_rows[0]
    assert "requested" in enforced_rows[0] and "enforced" in enforced_rows[0]


def test_sandbox_hub_publish_refused_and_config_validate_works() -> None:
    runtime = _runtime()
    sandbox = api.enact_power(
        runtime,
        power="hub_publish",
        principal="ops",
        artifact_key="sandbox-1",
        evidence_knowledge_time_ns=1_000,
        requested={"fragment_fp1": "fp1:x", "provenance": "sandbox"},
    )
    assert is_refusal(sandbox)
    assert sandbox.context["field"] == "provenance"

    validated = _ok(
        api.enact_power(
            runtime,
            power="config_validate",
            principal="ops",
            artifact_key="cfg-1",
            evidence_knowledge_time_ns=1_000,
            requested={},
        )
    )
    assert validated.enforced["status"] == "validated"


def test_wire_vocabulary_and_render_helpers() -> None:
    assert doors.WIRE_FORMAT_VERSION == 1
    wire = doors.wire_identity()
    assert "provenance_fields" in wire
    assert evidence.EVIDENCE_BIND_HOST == "127.0.0.1"
    rendered = render_powers_response(
        api.enact_power(
            _runtime(),
            power="restore_drill_run",
            principal="ops",
            artifact_key="drill-1",
            evidence_knowledge_time_ns=1_000,
            requested={},
        )
    )
    assert rendered["ok"] is True
    assert rendered["door"] == "powers_unix"


def test_closed_powers_list_unchanged_and_ops_subset() -> None:
    assert "notify_test" in CLOSED_POWERS
    assert "resurrect" in CLOSED_POWERS
    assert doors.OPS_ALLOWED_POWERS <= CLOSED_POWERS


def test_doors_modules_stay_free_of_venue_and_cli() -> None:
    banned = {"qmf.venue", "click", "typer", "argparse"}
    for path in sorted((_SRC / "doors").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".", 1)[0] not in banned
                    assert not alias.name.startswith("qmf.venue")
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("qmf.venue")
                assert node.module.split(".", 1)[0] not in banned
