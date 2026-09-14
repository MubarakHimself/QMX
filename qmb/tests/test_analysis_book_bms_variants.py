"""Story 35.4 — Book and BMS variants are complete dev-zone candidates plus replay."""

from __future__ import annotations

import ast
import inspect
import textwrap
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar

from qmb.analysis import evaluate_book_bms_variant, register_book_bms_variant
from qmb.analysis import variants as variants_mod
from qmb.config import (
    CLOCK_REPLAY,
    PROVENANCE_RECORDED,
    STARTING_CAPITAL_KEY,
    ResolvedRunConfig,
    compile_run_config,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.doors import api
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort, query_candidates
from qmb.results import mint_run_performance_result
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


def _source_ct32(*, tag: str = "source") -> PerformanceResult:
    stamp = _ok(fingerprint({"n": "analysis-variant-src", "tag": tag}))
    config = ResolvedRunConfig(
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
    outcome = _ok(run(slices=_slices(), config=config, handler=SilentSliceHandler()))
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


def _writer(stream: str = "book-definition") -> WriterId:
    return _ok(WriterId.try_create("node-a", "authoring", stream, _BOOT))


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


def _book(*, loss_floor: int = 800_000) -> BookDefinition:
    return _ok(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _money_variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _money_variable("loss_floor", loss_floor)),
                "exit_policy": _section("exit_policy", _money_variable("q", 100)),
            },
        )
    )


def _bms(*, cadence: int = 1) -> BmsDefinition:
    return _ok(
        BmsDefinition.try_create(
            BMS_CONTRACT_FORMAT_VERSION,
            {
                "accounting_rules": _section(
                    "accounting_rules", _money_variable("numeraire_unit", 1)
                ),
                "constraints": _section("constraints", _money_variable("exposure_ceiling", 50_000)),
                "ksa_policy": _section("ksa_policy", _money_variable("posture", 1)),
                "reporting": _section("reporting", _money_variable("cadence", cadence)),
            },
        )
    )


def _qma_request(
    *,
    candidate: str,
    predecessor: str = "fp1:sha256:" + "aa" * 32,
) -> dict[str, object]:
    return {
        "schema": qmb.MONEY_PATH_FIELD_DIFF_SCHEMA,
        "candidate_ref": candidate,
        "predecessor_ref": predecessor,
        "fields": [{"path": "sizing", "ancestor": "1R", "proposed": "2R"}],
    }


def _port_for(
    records: tuple[object, ...],
    *,
    pointers: tuple[DatedPointer, ...] = (),
) -> RegistryReadPort:
    as_of = _ok(AsOfSet.try_create(_instant(), records=records, pointers=pointers))
    hub = _ok(PassiveHub.try_create((as_of,)))
    return _ok(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY))


def test_identity_names_risk_shape_and_composition_root_mint() -> None:
    identity = qmb.book_bms_variant_identity()
    assert identity["shape_owner"] == qmb.BOOK_BMS_SHAPE_OWNER == "COMP-QMF-RISK"
    assert identity["mint"] == qmb.BOOK_BMS_MINT_SURFACE == "composition-root"
    assert identity["zone"] == qmb.VARIANT_ZONE == "dev"
    assert identity["evaluation"] == "analysis.rerun"
    assert identity["trade_list_rescale_is_book_truth"] is False
    assert identity["qma_fills_unset_money_path_fields"] is False
    assert identity["money_path_field_diff_schema"] == qmb.MONEY_PATH_FIELD_DIFF_SCHEMA
    assert qmb.__version__ not in identity.values()
    assert qmb.QMA_CANDIDATE_ORIGIN == "qma"


def test_complete_book_registers_as_dev_zone_ct22(tmp_path: Path) -> None:
    _ = tmp_path
    book = _book()
    definition_fp = _ok(book.fingerprint())
    variant = _ok(
        register_book_bms_variant(
            definition=book,
            writer=_writer(),
            created_at=_instant(),
        )
    )
    assert variant.kind == "book-definition"
    assert variant.contract == "CT-22"
    assert variant.zone == "dev"
    assert variant.shape_owner == "COMP-QMF-RISK"
    assert variant.mint == "composition-root"
    assert variant.definition_fp1 == definition_fp
    assert variant.cite() == definition_fp.value
    assert variant.record.body["class"] == "book-definition"
    assert variant.record.body["zone"] == "dev"
    assert variant.record.body["sections"] == book.fp1_identity()["sections"]
    assert variant.record.at_birth_parent_refs == (definition_fp,)
    port = _port_for((variant.record,))
    found = _ok(query_candidates(port=port, kind="book-definition", zone="dev"))
    assert any(item.fingerprint == variant.record.stable_id for item in found.candidates)
    fragment = _ok(materialize_book_fragment(port, variant.record.stable_id, _writer()))
    assert fragment.source_fp1 == definition_fp


def test_complete_bms_registers_as_dev_zone_ct27() -> None:
    bms = _bms()
    definition_fp = _ok(bms.fingerprint())
    variant = _ok(
        register_book_bms_variant(
            bms=bms,
            writer=_writer("bms-definition"),
            created_at=_instant(),
        )
    )
    assert variant.kind == "bms-definition"
    assert variant.contract == "CT-27"
    assert variant.zone == "dev"
    assert variant.definition_fp1 == definition_fp
    port = _port_for((variant.record,))
    fragment = _ok(
        materialize_bms_fragment(port, variant.record.stable_id, _writer("bms-definition"))
    )
    assert fragment.source_fp1 == definition_fp


def test_patch_and_partial_overlay_are_refused_as_definitions() -> None:
    book = _book()
    patched = register_book_bms_variant(
        definition=book,
        writer=_writer(),
        created_at=_instant(),
        patch={"money_rules.loss_floor": 1},
    )
    assert is_refusal(patched)
    assert patched.category is RefusalCategory.POLICY_REJECTION
    assert patched.context["field"] == "patch"
    overlay = register_book_bms_variant(
        definition={"overlay": {"loss_floor": 1}},
        writer=_writer(),
        created_at=_instant(),
    )
    assert is_refusal(overlay)
    partial = register_book_bms_variant(
        definition={"class": "book-definition", "sections": {}},
        writer=_writer(),
        created_at=_instant(),
    )
    assert is_refusal(partial)
    fragment = register_book_bms_variant(
        definition=book,
        writer=_writer(),
        created_at=_instant(),
        fragment=True,
    )
    assert is_refusal(fragment)


def test_mint_does_not_move_into_qmb_or_qma() -> None:
    book = _book()
    into_qmb = register_book_bms_variant(
        definition=book,
        writer=_writer(),
        created_at=_instant(),
        mint_into="qmb",
    )
    assert is_refusal(into_qmb)
    assert into_qmb.context["field"] == "mint"
    assert into_qmb.context["mint"] == "composition-root"
    into_qma = register_book_bms_variant(
        definition=book,
        writer=_writer(),
        created_at=_instant(),
        mint="qma",
    )
    assert is_refusal(into_qma)
    stolen = register_book_bms_variant(
        definition=book,
        writer=_writer(),
        created_at=_instant(),
        shape_owner="COMP-QMB",
    )
    assert is_refusal(stolen)
    live = register_book_bms_variant(
        definition=book,
        writer=_writer(),
        created_at=_instant(),
        zone="live",
    )
    assert is_refusal(live)


def test_qma_candidate_stays_money_path_relevant_with_field_level_diff() -> None:
    book = _book()
    definition_fp = _ok(book.fingerprint())
    variant = _ok(
        register_book_bms_variant(
            definition=book,
            writer=_writer(),
            created_at=_instant(),
            origin="qma",
            approval_request=_qma_request(candidate=definition_fp.value),
            ancestor={"sizing": "1R"},
        )
    )
    assert variant.origin == "qma"
    assert variant.money_path_relevant is True
    assert variant.record.body["origin"] == "qma"
    assert variant.record.body["money_path_relevant"] is True
    request = variant.record.body["approval_request"]
    assert isinstance(request, Mapping)
    assert request["schema"] == qmb.MONEY_PATH_FIELD_DIFF_SCHEMA
    missing = register_book_bms_variant(
        definition=book,
        writer=_writer(),
        created_at=_instant(),
        origin="qma",
    )
    assert is_refusal(missing)
    assert missing.context["field"] == "approval_request"
    unset = register_book_bms_variant(
        definition=book,
        writer=_writer(),
        created_at=_instant(),
        origin="qma",
        approval_request={
            "schema": qmb.MONEY_PATH_FIELD_DIFF_SCHEMA,
            "candidate_ref": definition_fp.value,
            "predecessor_ref": "fp1:sha256:" + "bb" * 32,
            "fields": [{"path": "risk", "ancestor": None, "proposed": "new"}],
        },
    )
    assert is_refusal(unset)
    assert unset.context["field"] == "ancestor"
    filled = register_book_bms_variant(
        definition=book,
        writer=_writer(),
        created_at=_instant(),
        origin="qma",
        approval_request={
            "schema": qmb.MONEY_PATH_FIELD_DIFF_SCHEMA,
            "candidate_ref": definition_fp.value,
            "predecessor_ref": "fp1:sha256:" + "cc" * 32,
            "fields": [{"path": "risk", "ancestor": "kept", "proposed": "new"}],
        },
        ancestor={"sizing": "1R"},
    )
    assert is_refusal(filled)
    assert filled.context["field"] == "ancestor"


def test_evaluation_is_analysis_rerun_citing_the_fingerprint(tmp_path: Path) -> None:
    book = _book(loss_floor=900_000)
    bms = _bms()
    variant = _ok(
        register_book_bms_variant(definition=book, writer=_writer(), created_at=_instant())
    )
    bms_variant = _ok(
        register_book_bms_variant(
            bms=bms,
            writer=_writer("bms-definition"),
            created_at=_instant(),
            sequence=1,
        )
    )
    bot_writer = _ok(WriterId.try_create("node-a", "authoring", "bot-definition", _BOOT))
    bot = _ok(
        RegistrationRecord.try_create(
            "bot-definition",
            1,
            (),
            {"class": "bot-definition", "alias": "mean-reversion"},
            bot_writer,
            0,
            _instant(),
        )
    )
    pointer = _ok(DatedPointer.try_create("mean-reversion", bot.stable_id, _instant()))
    port = _port_for((variant.record, bms_variant.record, bot), pointers=(pointer,))
    book_fragment = _ok(materialize_book_fragment(port, variant.record.stable_id, _writer()))
    bms_fragment = _ok(
        materialize_bms_fragment(port, bms_variant.record.stable_id, _writer("bms-definition"))
    )
    assert book_fragment.source_fp1 == variant.definition_fp1
    run_spec: dict[str, object] = {"bot": bot.stable_id, STARTING_CAPITAL_KEY: _SEED}
    defaults: dict[str, object] = {
        "account_id": "acct-replay",
        "clock": CLOCK_REPLAY,
        "data_provenance": PROVENANCE_RECORDED,
        "venue_id": "venue-replay",
        STREAM_SET_KEY: ("eurusd",),
    }
    compiled = _ok(
        compile_run_config(
            port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec=run_spec,
            workspace_defaults=defaults,
        )
    )
    assert compiled.book_fp1 == variant.definition_fp1
    outcome = _ok(
        evaluate_book_bms_variant(
            candidate=variant,
            source_ct32=_source_ct32(),
            config=compiled,
            slices=_slices(),
            output_root=tmp_path / "runs",
            ledger=_sink(tmp_path),
        )
    )
    assert outcome.occupancy == "run"
    assert outcome.mints_ct32 is True
    assert outcome.config.book_fp1 == variant.definition_fp1
    tree = ast.parse(textwrap.dedent(inspect.getsource(evaluate_book_bms_variant)))
    names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "rerun" in names


def test_evaluation_refuses_a_config_that_does_not_cite_the_candidate() -> None:
    book = _book()
    variant = _ok(
        register_book_bms_variant(definition=book, writer=_writer(), created_at=_instant())
    )
    stamp = _ok(fingerprint({"n": "other-book"}))
    config = ResolvedRunConfig(
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
    refused = evaluate_book_bms_variant(candidate=variant, config=config)
    assert is_refusal(refused)
    assert refused.context["field"] == "candidate"
    assert refused.context["expected"] == variant.definition_fp1.value


def test_trade_list_rescale_is_not_book_truth() -> None:
    book = _book()
    refused = register_book_bms_variant(
        definition=book,
        writer=_writer(),
        created_at=_instant(),
        rescale=True,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "rescale"
    assert refused.context["trade_list_rescale_is_book_truth"] is False
    variant = _ok(
        register_book_bms_variant(definition=book, writer=_writer(), created_at=_instant())
    )
    evaluated = evaluate_book_bms_variant(candidate=variant, trades=True)
    assert is_refusal(evaluated)
    assert evaluated.context["evaluation"] == "analysis.rerun"


def test_python_api_reexports_variant_surface() -> None:
    assert api.register_book_bms_variant is qmb.register_book_bms_variant
    assert api.evaluate_book_bms_variant is qmb.evaluate_book_bms_variant
    assert api.BookBmsVariant is qmb.BookBmsVariant
    assert api.book_bms_variant_identity is qmb.book_bms_variant_identity


def test_module_does_not_open_sqlite_or_import_qma() -> None:
    source = (_SRC / "analysis" / "variants.py").read_text(encoding="utf-8")
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
    assert inspect.getsource(variants_mod.register_book_bms_variant)
    assert "COMP-QMF-RISK" in source
    assert "composition-root" in source
