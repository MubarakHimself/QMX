"""Story 27.2 — node-data-bootstrap recipe (check-mode / fixtures, no live download)."""

from __future__ import annotations

import ast
import importlib.util
import json
import lzma
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import TypeVar

from qmf.core import (
    Instrument,
    Ok,
    RefusalCategory,
    Result,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.data.dukascopy import DUKASCOPY_SOURCE, PERSONAL_USE_LICENSE, DukascopyAdapter
from qmf.data.ingest import ExternalSourceIngest
from qmn.data import (
    BOOTSTRAP_CONTEXT,
    VENUE_SPAN_CAP_NS,
    HistoryBootstrap,
    RefusingLiveTransport,
    VenueContinuityBridge,
    refuse_ad_hoc_fetch,
    refuse_live_network,
)

T = TypeVar("T")

_QMN_ROOT = Path(__file__).resolve().parents[1]
_DEPLOY = _QMN_ROOT / "deploy"
_WORKSPACE = _QMN_ROOT.parent
_HOUR = datetime(2024, 1, 15, 10, tzinfo=timezone.utc)
_HOUR_NS = int(_HOUR.timestamp() * 1_000_000_000)
_END_NS = _HOUR_NS + 3_600 * 1_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _instrument() -> Instrument:
    venue = _ok(VenueId.try_create("dukascopy-fx"))
    return _ok(Instrument.try_create(venue, "EURUSD"))


def _writer() -> WriterId:
    return _ok(WriterId.try_create("vps-fra-01", "data-bootstrap", "dukascopy", "boot-27-2"))


def _bi5(*ticks: tuple[int, int, int]) -> bytes:
    raw = b"".join(struct.pack("!IIIff", ms, ask, bid, 1.0, 1.0) for ms, ask, bid in ticks)
    return lzma.compress(raw)


class _FixtureTransport:
    def __init__(self, hours: dict[str, bytes] | None = None) -> None:
        self.hours = hours or {}
        self.calls: list[object] = []

    def fetch_hour(self, key: object, /) -> Result[bytes]:
        self.calls.append(key)
        path = getattr(key, "path_reference", "")
        return Ok(self.hours.get(str(path), b""))


def test_bootstrap_modules_never_import_qmn_host_or_urllib() -> None:
    banned = ("qmn.host", "qmn.doors", "urllib", "httpx", "requests")
    path = _DEPLOY / "data_bootstrap.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imported.add(node.module)
    for name in imported:
        assert not name.startswith("qmn."), path
        assert name not in banned
        assert "urllib" not in name
    text = path.read_text(encoding="utf-8")
    assert "datafeed.dukascopy.com" not in text


def test_check_mode_plan_is_licensed_checkpointed_and_offline() -> None:
    wizard = _load("qmn_deploy_data_bootstrap", _DEPLOY / "data_bootstrap.py")
    plan = wizard.build_bootstrap_plan(mode="check")
    assert plan.ok, plan.findings
    assert plan.recipe == "node-data-bootstrap"
    assert plan.principal == "ops"
    assert plan.source == "dukascopy"
    assert plan.license_tag == "internal-only"
    assert plan.live_network is False
    assert plan.ad_hoc is False
    kinds = {step.kind for step in plan.steps}
    assert "dukascopy_hours" in kinds
    assert "checkpoint" in kinds
    assert "refuse_live_network" in kinds
    assert "refuse_ad_hoc" in kinds
    payload = json.dumps(plan.to_jsonable())
    assert "https://" not in payload
    assert "datafeed.dukascopy.com" not in payload


def test_plan_refuses_venue_gap_above_one_week() -> None:
    wizard = _load("qmn_deploy_data_bootstrap_span", _DEPLOY / "data_bootstrap.py")
    plan = wizard.build_bootstrap_plan(venue_gap_ns=VENUE_SPAN_CAP_NS + 1)
    assert plan.ok is False
    assert any("span cap" in item for item in plan.findings)
    kinds = {step.kind for step in plan.steps}
    assert "refuse_span_cap" in kinds


def test_cli_refuses_apply_without_fixture_root() -> None:
    wizard = _load("qmn_deploy_data_bootstrap_cli", _DEPLOY / "data_bootstrap.py")
    assert wizard.main(["--apply"]) == 2


def test_cli_check_mode_writes_plan(tmp_path: Path) -> None:
    wizard = _load("qmn_deploy_data_bootstrap_out", _DEPLOY / "data_bootstrap.py")
    out = tmp_path / "plan.json"
    code = wizard.main(["--check-mode", "--out", str(out)])
    assert code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["recipe"] == "node-data-bootstrap"
    assert payload["live_network"] is False


def test_fixture_apply_writes_archive_with_provenance(tmp_path: Path) -> None:
    wizard = _load("qmn_deploy_data_bootstrap_fix", _DEPLOY / "data_bootstrap.py")
    plan = wizard.build_bootstrap_plan(mode="apply")
    hours = {"EURUSD/2024/00/15/10h_ticks.bi5": _bi5((0, 110260, 110250))}
    result = wizard.apply_plan_to_fixture(plan, fixture_root=tmp_path, hours=hours)
    assert result["ok"] is True
    assert result["live_network"] is False
    archive = tmp_path / "archive"
    assert (archive / wizard.CHECKPOINT_NAME).is_file()
    checkpoint = json.loads((archive / wizard.CHECKPOINT_NAME).read_text(encoding="utf-8"))
    assert checkpoint["source"] == "dukascopy"
    assert checkpoint["license_tag"] == "internal-only"
    assert checkpoint["idempotent"] is True
    assert checkpoint["resumable"] is True
    provenances = list((archive / "raw" / "dukascopy").glob("*.provenance.json"))
    assert provenances
    body = json.loads(provenances[0].read_text(encoding="utf-8"))
    assert body["licence"] == "internal-only"
    assert body["live_network"] is False


def test_root_justfile_recipe_points_at_bootstrap() -> None:
    node_just = (_DEPLOY / "justfile-recipes" / "node.just").read_text(encoding="utf-8")
    assert "data_bootstrap.py" in node_just
    assert "node-data-bootstrap" in node_just
    root = (_WORKSPACE / "justfile").read_text(encoding="utf-8")
    assert 'import "./qmn/deploy/justfile-recipes/node.just"' in root


def test_refusing_live_transport_never_downloads() -> None:
    refused = refuse_live_network(target="datafeed.dukascopy.com")
    assert is_refusal(refused)
    assert refused.context["failure_id"] == "data.bootstrap.live_network"
    transport = RefusingLiveTransport()
    hour = transport.fetch_hour("EURUSD/2024/00/15/10h_ticks.bi5")
    assert is_refusal(hour)
    assert hour.context["failure_id"] == "data.bootstrap.live_network"


def test_ad_hoc_fetch_from_the_loop_is_refused() -> None:
    refused = refuse_ad_hoc_fetch(context="run_slice")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["failure_id"] == "data.bootstrap.ad_hoc"


def test_history_bootstrap_is_idempotent_over_injected_hours(tmp_path: Path) -> None:
    path = "EURUSD/2024/00/15/10h_ticks.bi5"
    transport = _FixtureTransport({path: _bi5((0, 110260, 110250), (1_000, 110265, 110255))})
    adapter = DukascopyAdapter(transport, instruments={"EURUSD": _instrument()})
    ingest = ExternalSourceIngest(adapter)
    bootstrap = HistoryBootstrap(
        adapter=adapter,
        ingest=ingest,
        writer=_writer(),
        archive_root=tmp_path,
        world=World.LIVE,
        context=BOOTSTRAP_CONTEXT,
    )
    first = _ok(
        bootstrap.run(
            symbol="EURUSD",
            start_ns=_HOUR_NS,
            end_ns=_END_NS,
            receive_wall_ns=_END_NS + 1_000_000,
            license_tag=PERSONAL_USE_LICENSE,
        )
    )
    assert first.source == DUKASCOPY_SOURCE
    assert first.license_tag == PERSONAL_USE_LICENSE
    assert first.produced == 2
    assert first.provenance["live_network"] is False
    assert first.provenance["licence"] == PERSONAL_USE_LICENSE
    assert (tmp_path / "bootstrap-checkpoint.json").is_file()
    second = _ok(
        bootstrap.run(
            symbol="EURUSD",
            start_ns=_HOUR_NS,
            end_ns=_END_NS,
            receive_wall_ns=_END_NS + 2_000_000,
            license_tag=PERSONAL_USE_LICENSE,
        )
    )
    assert second.produced == 0
    assert second.checkpoint.last_end_ns == _END_NS


def test_ad_hoc_context_refuses_bootstrap_run(tmp_path: Path) -> None:
    adapter = DukascopyAdapter(_FixtureTransport(), instruments={"EURUSD": _instrument()})
    bootstrap = HistoryBootstrap(
        adapter=adapter,
        ingest=ExternalSourceIngest(adapter),
        writer=_writer(),
        archive_root=tmp_path,
        context="run_slice",
    )
    refused = bootstrap.run(
        symbol="EURUSD",
        start_ns=_HOUR_NS,
        end_ns=_END_NS,
        receive_wall_ns=_END_NS,
    )
    assert is_refusal(refused)
    assert refused.context["failure_id"] == "data.bootstrap.ad_hoc"


def test_venue_bridge_pages_recent_gap_and_refuses_over_span() -> None:
    bridge = VenueContinuityBridge()
    gap_end = _HOUR_NS + 2 * 3_600 * 1_000_000_000
    pages = _ok(bridge.plan(archive_end_ns=_HOUR_NS, go_live_ns=gap_end))
    assert len(pages) == 2
    assert pages[0].has_more is True
    assert pages[-1].has_more is False
    assert pages[0].as_mapping()["source"] == "ctrader"
    over = bridge.plan(archive_end_ns=_HOUR_NS, go_live_ns=_HOUR_NS + VENUE_SPAN_CAP_NS + 1)
    assert is_refusal(over)
    assert over.context["failure_id"] == "data.bootstrap.span_cap"
