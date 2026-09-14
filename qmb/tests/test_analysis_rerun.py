"""Story 35.3 — analysis.rerun is a new QMB run and a new CT-32."""

from __future__ import annotations

import ast
import inspect
import json
import textwrap
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar

import pytest
from click.testing import CliRunner
from qmb.analysis import rerun
from qmb.config import (
    CLOCK_REPLAY,
    FOLD_RATED,
    FOLD_UNRATED,
    PROVENANCE_RECORDED,
    STARTING_CAPITAL_KEY,
    ConfigFragment,
    ResolvedRunConfig,
    compile_run_config,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.doors import api, flatten_capabilities, required_library_names
from qmb.doors.cli import (
    ANALYSIS_RERUN_OCCUPANCY,
    analysis_command_occupancy,
    command_tree,
    invoke_analysis_rerun,
    main,
)
from qmb.doors.cli import tree as cli_tree
from qmb.execution import FILL_ADAPTER_DECLARED_PATH, FILL_ADAPTER_KEY
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmb.results import mint_run_performance_result
from qmb.results.ct32 import load_stored_ct32
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import Money, UnitKind
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord
from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability
from qmf.risk.performance import PerformanceResult
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BmsDefinition,
    BookDefinition,
)

import qmb

T = TypeVar("T")

_SRC = Path(__file__).resolve().parents[1] / "src" / "qmb"
_NS = 1_700_000_000_000_000_000
_BOOT = "boot-1"
_MACHINE = "test-machine"
_SEED = Money(value=1_000_000, currency="USD", scale=2)
_SEED_ALT = Money(value=2_000_000, currency="USD", scale=2)
_SEVERITY = "workspace-declared"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _obs(stream_id: str = "eurusd", ns: int = _NS) -> SliceObservation:
    return _ok(SliceObservation.try_create(stream_id, _instant(ns), True))


def _slices() -> tuple[tuple[SliceObservation, ...], ...]:
    return ((_obs(),), (_obs(ns=_NS + 1),))


def _config(*, tag: str) -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "analysis-rerun-cfg", "tag": tag}))
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",)},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def _source_ct32(*, tag: str = "source") -> PerformanceResult:
    config = _config(tag=tag)
    outcome = _ok(
        run(
            slices=_slices(),
            config=config,
            handler=SilentSliceHandler(),
        )
    )
    return _ok(
        mint_run_performance_result(
            config,
            evidence_range=outcome.evidence_range,
            stream_order=outcome.stream_order,
            slice_count=2,
            filled_count=0,
            resting_count=0,
            data_points_processed=2,
            outcome_identity=outcome.fp1_identity(),
        )
    )


def _sink(tmp_path: Path, *, slot: object = 0) -> qmb.LedgerSink:
    return _ok(
        qmb.LedgerSink.try_create(
            tmp_path / "ledger",
            machine=_MACHINE,
            worker_slot=slot,
            boot_epoch_id=_BOOT,
        )
    )


def _writer(stream: str = "config-fragment") -> WriterId:
    return _ok(WriterId.try_create("node-a", "authoring", stream, "boot-1"))


def _money_variable(name: str, minor: int) -> TemplateVariable:
    return _ok(
        TemplateVariable.try_create(
            name,
            UnitKind.MONEY,
            Money(value=minor, currency="USD", scale=2),
            UiEditability.UI_EDITABLE,
            AdmissionImpact.RESIGN,
        )
    )


def _section(name: str, variable: TemplateVariable) -> TemplateSection:
    return _ok(TemplateSection.try_create(name, {variable.name: variable}))


def _book() -> BookDefinition:
    return _ok(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _money_variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _money_variable("loss_floor", 800_000)),
                "exit_policy": _section("exit_policy", _money_variable("q", 100)),
            },
        )
    )


def _bms() -> BmsDefinition:
    return _ok(
        BmsDefinition.try_create(
            BMS_CONTRACT_FORMAT_VERSION,
            {
                "accounting_rules": _section(
                    "accounting_rules", _money_variable("numeraire_unit", 1)
                ),
                "constraints": _section("constraints", _money_variable("exposure_ceiling", 50_000)),
                "ksa_policy": _section("ksa_policy", _money_variable("posture", 1)),
                "reporting": _section("reporting", _money_variable("cadence", 1)),
            },
        )
    )


def _record(
    kind: str, body: Mapping[str, object] | BookDefinition | BmsDefinition
) -> RegistrationRecord:
    if isinstance(body, (BookDefinition, BmsDefinition)):
        parents: tuple[object, ...] = (_ok(body.fingerprint()),)
        payload: Mapping[str, object] = body.fp1_identity()
        version = body.contract_format_version
    else:
        parents = ()
        payload = dict(body)
        version = 1
    return _ok(
        RegistrationRecord.try_create(
            kind,
            version,
            parents,
            payload,
            _writer(kind),
            0,
            _instant(),
        )
    )


def _compile_layers() -> tuple[
    RegistryReadPort,
    ConfigFragment,
    ConfigFragment,
    dict[str, object],
    dict[str, object],
]:
    book = _book()
    bms = _bms()
    book_record = _record("book-definition", book)
    bms_record = _record("bms-definition", bms)
    bot = _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion"})
    pointer = _ok(DatedPointer.try_create("mean-reversion", bot.stable_id, _instant()))
    as_of = _ok(
        AsOfSet.try_create(
            _instant(),
            records=(book_record, bms_record, bot),
            pointers=(pointer,),
        )
    )
    hub = _ok(PassiveHub.try_create((as_of,)))
    port = _ok(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY))
    book_fragment = _ok(materialize_book_fragment(port, book_record.stable_id, _writer()))
    bms_fragment = _ok(materialize_bms_fragment(port, bms_record.stable_id, _writer()))
    run_spec: dict[str, object] = {"bot": bot.stable_id, STARTING_CAPITAL_KEY: _SEED}
    defaults: dict[str, object] = {
        "account_id": "acct-replay",
        "clock": CLOCK_REPLAY,
        "data_provenance": PROVENANCE_RECORDED,
        "venue_id": "venue-replay",
        STREAM_SET_KEY: ("eurusd",),
    }
    return port, book_fragment, bms_fragment, run_spec, defaults


def test_rerun_identity_is_a_run_that_mints_ct32() -> None:
    identity = qmb.analysis_rerun_identity()
    assert identity["occupancy"] == ANALYSIS_RERUN_OCCUPANCY == "run"
    assert identity["mints_ct32"] is qmb.ANALYSIS_RERUN_MINTS_CT32 is True
    assert identity["mints_experiment_spec"] is qmb.ANALYSIS_RERUN_MINTS_EXPERIMENT_SPEC is False
    assert identity["method"] == qmb.METHOD_RERUN == "rerun"
    assert identity["workbench_lane"] == qmb.WORKBENCH_LANE_GOVERNED == "governed"
    assert identity["spawns_orchestrator"] is True
    assert qmb.__version__ not in identity.values()
    assert _ok(analysis_command_occupancy("rerun")) == "run"
    assert _ok(analysis_command_occupancy("analysis.rerun")) == "run"
    assert _ok(analysis_command_occupancy("project")) == "query"


def test_rerun_spawns_governed_run_and_new_ct32(tmp_path: Path) -> None:
    source = _source_ct32()
    source_fp = _ok(source.fingerprint())
    config = _config(tag="rerun-new")
    outcome = _ok(
        rerun(
            source_ct32=source,
            config=config,
            slices=_slices(),
            output_root=tmp_path / "runs",
            ledger=_sink(tmp_path),
        )
    )
    assert outcome.occupancy == "run"
    assert outcome.mints_ct32 is True
    assert outcome.mints_experiment_spec is False
    assert outcome.workbench_lane == qmb.WORKBENCH_LANE_GOVERNED
    assert outcome.ct32_fingerprint != source_fp
    assert outcome.isolated.ct32_fingerprint == outcome.ct32_fingerprint
    assert outcome.config.fingerprint != source_fp
    stored = _ok(load_stored_ct32(outcome.isolated.output_dir))
    assert "analysis_method" not in stored
    assert "lane" not in stored
    assert "workbench_lane" not in stored
    line = outcome.ledger_line
    identity = line.fp1_identity()
    assert "analysis_method" not in identity
    assert "lane" not in identity
    assert identity["role"] == qmb.ROLE_CONFIRMATION
    assert identity["workbench_lane"] == "governed"
    assert identity["ct32"] == {"_ref": outcome.ct32_fingerprint.value}
    assert line.ct32_fingerprint == outcome.ct32_fingerprint
    merged = _ok(
        qmb.read_merge_view(
            tmp_path / "ledger",
            world=World.REPLAY,
            role=qmb.ROLE_CONFIRMATION,
        )
    )
    assert len(merged) == 1
    assert merged[0].fp1_identity() == identity


def test_starting_capital_override_stamps_seed_overridden_and_unrated(tmp_path: Path) -> None:
    port, book, bms, spec, defaults = _compile_layers()
    rated = _ok(
        compile_run_config(
            port,
            book_fragment=book,
            bms_fragment=bms,
            run_spec=spec,
            workspace_defaults=defaults,
        )
    )
    assert rated.seed_overridden is False
    assert rated.fold_rating == FOLD_RATED
    outcome = _ok(
        rerun(
            source_ct32=_source_ct32(),
            port=port,
            book_fragment=book,
            bms_fragment=bms,
            run_spec=spec,
            workspace_defaults=defaults,
            starting_capital=_SEED_ALT,
            fill_port=FILL_ADAPTER_DECLARED_PATH,
            slices=_slices(),
            output_root=tmp_path / "runs",
            ledger=_sink(tmp_path),
        )
    )
    assert outcome.config.seed_overridden is True
    assert outcome.config.fold_rating == FOLD_UNRATED
    assert outcome.config.replay_binding is not None
    assert outcome.config.replay_binding.seed_overridden is True
    assert outcome.config.replay_binding.starting_capital == _SEED_ALT
    assert outcome.config.keys[FILL_ADAPTER_KEY] == FILL_ADAPTER_DECLARED_PATH
    assert outcome.config.fingerprint != rated.fingerprint
    assert outcome.ct32_fingerprint is not None


def test_occupancy_query_and_payload_labels_are_refused() -> None:
    query = rerun(occupancy="query")
    assert is_refusal(query)
    assert query.category is RefusalCategory.POLICY_REJECTION
    assert query.context["occupancy"] == "run"
    method = rerun(analysis_method="rerun")
    assert is_refusal(method)
    assert method.context["field"] == "analysis_method"
    lane = rerun(lane="governed")
    assert is_refusal(lane)
    workbench = rerun(workbench_lane="governed")
    assert is_refusal(workbench)
    spec = rerun(experiment_spec=True)
    assert is_refusal(spec)
    assert spec.context["epic"] == "36"
    sqlite = rerun(sqlite=True)
    assert is_refusal(sqlite)


def test_ledger_line_refuses_analysis_method_and_lane_fields() -> None:
    config = _config(tag="label-ban")
    outcome = _ok(run(slices=_slices(), config=config, handler=SilentSliceHandler()))
    artifact = _ok(
        mint_run_performance_result(
            config,
            evidence_range=outcome.evidence_range,
            stream_order=outcome.stream_order,
            slice_count=2,
            filled_count=0,
            resting_count=0,
            data_points_processed=2,
            outcome_identity=outcome.fp1_identity(),
        )
    )
    minted = _ok(
        qmb.mint_completed_line(
            config,
            outcome_identity=outcome.fp1_identity(),
            ct32_fingerprint=_ok(artifact.fingerprint()),
            workbench_lane="governed",
        )
    )
    body = dict(minted.fp1_identity())
    body["analysis_method"] = "rerun"
    refused = qmb.LedgerLine.from_mapping(body)
    assert is_refusal(refused)
    assert refused.context["field"] == "analysis_method"
    lane_body = dict(minted.fp1_identity())
    lane_body["lane"] = "governed"
    refused_lane = qmb.LedgerLine.from_mapping(lane_body)
    assert is_refusal(refused_lane)


def test_python_api_and_cli_are_thin_doors(tmp_path: Path) -> None:
    source = _source_ct32()
    config = _config(tag="door")
    sink = _sink(tmp_path)
    library = rerun(
        source_ct32=source,
        config=config,
        slices=_slices(),
        output_root=tmp_path / "lib",
        ledger=sink,
    )
    door = invoke_analysis_rerun(
        source_ct32=source,
        config=_config(tag="door-cli"),
        slices=_slices(),
        output_root=tmp_path / "door",
        ledger=_sink(tmp_path, slot=1),
    )
    assert is_ok(library) and is_ok(door)
    assert library.value.ct32_fingerprint != door.value.ct32_fingerprint
    assert api.rerun is qmb.rerun
    assert "rerun" in required_library_names()
    assert "analysis.rerun" in flatten_capabilities()
    assert command_tree()["analysis"] == ("project", "rerun")
    tree = ast.parse(textwrap.dedent(inspect.getsource(invoke_analysis_rerun)))
    names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "rerun" in names
    runner = CliRunner()
    helped = runner.invoke(main, ["analysis", "--help"])
    assert helped.exit_code == 0, helped.output
    assert "rerun" in helped.output
    rerun_help = runner.invoke(main, ["analysis", "rerun", "--help"])
    assert rerun_help.exit_code == 0, rerun_help.output
    assert "run" in rerun_help.output.lower()
    clicked = runner.invoke(
        main,
        ["analysis", "rerun"],
        obj={
            "source_ct32": source,
            "config": _config(tag="click"),
            "slices": _slices(),
            "output_root": tmp_path / "click",
            "ledger": _sink(tmp_path, slot=2),
        },
    )
    assert clicked.exit_code == 0, clicked.output
    payload = json.loads(clicked.stdout)
    assert payload["occupancy"] == "run"
    assert payload["mints_ct32"] is True
    assert payload["workbench_lane"] == "governed"
    assert payload["ct32"]["_ref"].startswith("fp1:")
    query = runner.invoke(
        main,
        ["analysis", "rerun", "--occupancy", "query"],
        obj={
            "source_ct32": source,
            "config": _config(tag="query"),
            "slices": _slices(),
            "output_root": tmp_path / "query",
            "ledger": _sink(tmp_path, slot=3),
        },
    )
    assert query.exit_code != 0


def test_door_calls_the_library_not_a_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    calls: list[str] = []

    def _record(*args: object, **kwargs: object) -> object:
        _ = (args, kwargs)
        calls.append("rerun")
        from qmf.core.refusal import Ok

        return Ok(sentinel)

    monkeypatch.setattr(cli_tree, "rerun", _record)
    result = invoke_analysis_rerun(
        source_ct32=1,
        config=1,
        slices=1,
        output_root=1,
        ledger=1,
    )
    assert is_ok(result)
    assert result.value is sentinel
    assert calls == ["rerun"]


def test_module_does_not_open_sqlite_or_import_qma() -> None:
    source = (_SRC / "analysis" / "rerun.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module.split(".", 1)[0])
    assert "qma" not in imported
    assert "sqlite3" not in imported
    assert "qmx-agents" not in source
