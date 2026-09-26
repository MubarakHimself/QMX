"""Reference usage — Book/BMS variants are complete dev-zone candidates (Story 35.4).

Executable::

    python qmb/examples/analysis_book_bms_variants_usage.py

Shows the things Story 35.4 / FR-W27 / SCN-0016 pin down:

1. A proposed Book or BMS is a complete new fingerprinted CT-22/CT-27 in dev.
2. A patch record or partial overlay is refused as a definition.
3. Evaluation is analysis.rerun citing that fingerprint.
4. Trade-list rescaling is not Book/BMS truth.
5. QMA-emitted candidates remain money_path_relevant with a field-level diff.
6. QMA never fills an unset money-path field.
7. COMP-QMF-RISK remains the shape owner; composition root remains the mint.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypeVar

from qmb.analysis import evaluate_book_bms_variant, register_book_bms_variant
from qmb.config import (
    CLOCK_REPLAY,
    PROVENANCE_RECORDED,
    STARTING_CAPITAL_KEY,
    ResolvedRunConfig,
    compile_run_config,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmb.results import mint_run_performance_result
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import Money, UnitKind
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import Result, is_ok, is_refusal
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
_NS = 1_700_000_000_000_000_000
_SEED = Money(value=1_000_000, currency="USD", scale=2)


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _obs(ns: int = _NS) -> SliceObservation:
    return _unwrap(SliceObservation.try_create("eurusd", _instant(ns), True), "obs")


def _slices() -> tuple[tuple[SliceObservation, ...], ...]:
    return ((_obs(),), (_obs(_NS + 1),))


def _writer() -> WriterId:
    return _unwrap(
        WriterId.try_create("node-a", "authoring", "book-definition", "boot-1"),
        "writer",
    )


def _money_variable(name: str, minor: int) -> TemplateVariable:
    return _unwrap(
        TemplateVariable.try_create(
            name,
            UnitKind.MONEY,
            Money(value=minor, currency="USD", scale=2),
            UiEditability.UI_EDITABLE,
            AdmissionImpact.RESIGN,
        ),
        "variable",
    )


def _section(name: str, variable: TemplateVariable) -> TemplateSection:
    return _unwrap(TemplateSection.try_create(name, {variable.name: variable}), "section")


def _source() -> PerformanceResult:
    stamp = _unwrap(fingerprint({"n": "analysis-variant-example"}), "fp")
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
    outcome = _unwrap(run(slices=_slices(), config=config, handler=SilentSliceHandler()), "run")
    return _unwrap(
        mint_run_performance_result(
            config,
            evidence_range=outcome.evidence_range,
            stream_order=outcome.stream_order,
            slice_count=2,
            filled_count=0,
            resting_count=0,
            data_points_processed=2,
            outcome_identity=outcome.fp1_identity(),
        ),
        "ct32",
    )


def main() -> None:
    identity = qmb.book_bms_variant_identity()
    assert identity["shape_owner"] == "COMP-QMF-RISK"
    assert identity["mint"] == "composition-root"
    assert identity["evaluation"] == "analysis.rerun"
    print("COMP-QMF-RISK remains the shape owner")
    print("composition root remains the mint")

    book = _unwrap(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _money_variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _money_variable("loss_floor", 800_000)),
                "exit_policy": _section("exit_policy", _money_variable("q", 100)),
            },
        ),
        "book",
    )
    variant = _unwrap(
        register_book_bms_variant(definition=book, writer=_writer(), created_at=_instant()),
        "variant",
    )
    assert variant.zone == "dev"
    assert variant.contract == "CT-22"
    assert variant.cite() == _unwrap(book.fingerprint(), "book-fp").value
    print("dev-zone candidate is a complete CT-22")

    patched = register_book_bms_variant(
        definition=book,
        writer=_writer(),
        created_at=_instant(),
        patch={"loss_floor": 1},
    )
    assert is_refusal(patched)
    print("patch record refused as a definition")

    rescale = register_book_bms_variant(
        definition=book,
        writer=_writer(),
        created_at=_instant(),
        rescale=True,
    )
    assert is_refusal(rescale)
    print("trade-list rescale is not Book/BMS truth")

    stolen = register_book_bms_variant(
        definition=book,
        writer=_writer(),
        created_at=_instant(),
        mint_into="qmb",
    )
    assert is_refusal(stolen)
    print("mint does not move into QMB or QMA")

    qma = register_book_bms_variant(
        definition=book,
        writer=_writer(),
        created_at=_instant(),
        origin="qma",
    )
    assert is_refusal(qma)
    print("QMA candidate without field-level diff refused")

    definition_fp = _unwrap(book.fingerprint(), "book-fp")
    qma_ok = _unwrap(
        register_book_bms_variant(
            definition=book,
            writer=_writer(),
            created_at=_instant(),
            sequence=1,
            origin="qma",
            approval_request={
                "schema": qmb.MONEY_PATH_FIELD_DIFF_SCHEMA,
                "candidate_ref": definition_fp.value,
                "predecessor_ref": "fp1:sha256:" + "ab" * 32,
                "fields": [{"path": "sizing", "ancestor": "1R", "proposed": "2R"}],
            },
            ancestor={"sizing": "1R"},
        ),
        "qma-variant",
    )
    assert qma_ok.money_path_relevant is True
    print("QMA-emitted candidate remains money_path_relevant")

    unset = register_book_bms_variant(
        definition=book,
        writer=_writer(),
        created_at=_instant(),
        origin="qma",
        approval_request={
            "schema": qmb.MONEY_PATH_FIELD_DIFF_SCHEMA,
            "candidate_ref": definition_fp.value,
            "predecessor_ref": "fp1:sha256:" + "cd" * 32,
            "fields": [{"path": "risk", "ancestor": None, "proposed": "new"}],
        },
    )
    assert is_refusal(unset)
    print("QMA never fills an unset money-path field")

    bms = _unwrap(
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
        ),
        "bms",
    )
    bms_variant = _unwrap(
        register_book_bms_variant(
            bms=bms,
            writer=_unwrap(
                WriterId.try_create("node-a", "authoring", "bms-definition", "boot-1"),
                "bms-writer",
            ),
            created_at=_instant(),
            sequence=2,
        ),
        "bms-variant",
    )
    bot = _unwrap(
        RegistrationRecord.try_create(
            "bot-definition",
            1,
            (),
            {"class": "bot-definition", "alias": "mean-reversion"},
            _writer(),
            0,
            _instant(),
        ),
        "bot",
    )
    pointer = _unwrap(DatedPointer.try_create("mean-reversion", bot.stable_id, _instant()), "ptr")
    as_of = _unwrap(
        AsOfSet.try_create(
            _instant(),
            records=(variant.record, bms_variant.record, bot),
            pointers=(pointer,),
        ),
        "as-of",
    )
    hub = _unwrap(PassiveHub.try_create((as_of,)), "hub")
    port = _unwrap(
        RegistryReadPort.try_create(hub, stale_evidence_severity="workspace-declared"),
        "port",
    )
    book_fragment = _unwrap(
        materialize_book_fragment(port, variant.record.stable_id, _writer()),
        "book-fragment",
    )
    bms_fragment = _unwrap(
        materialize_bms_fragment(
            port,
            bms_variant.record.stable_id,
            _unwrap(WriterId.try_create("node-a", "authoring", "bms-definition", "boot-1"), "w"),
        ),
        "bms-fragment",
    )
    compiled = _unwrap(
        compile_run_config(
            port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec={"bot": bot.stable_id, STARTING_CAPITAL_KEY: _SEED},
            workspace_defaults={
                "account_id": "acct-replay",
                "clock": CLOCK_REPLAY,
                "data_provenance": PROVENANCE_RECORDED,
                "venue_id": "venue-replay",
                STREAM_SET_KEY: ("eurusd",),
            },
        ),
        "config",
    )
    assert compiled.book_fp1 == variant.definition_fp1
    with TemporaryDirectory() as raw:
        root = Path(raw)
        sink = _unwrap(
            qmb.LedgerSink.try_create(
                root / "ledger",
                machine="example-machine",
                worker_slot=0,
                boot_epoch_id="boot-1",
            ),
            "ledger",
        )
        outcome = _unwrap(
            evaluate_book_bms_variant(
                candidate=variant,
                source_ct32=_source(),
                config=compiled,
                slices=_slices(),
                output_root=root / "runs",
                ledger=sink,
            ),
            "evaluate",
        )
        assert outcome.config.book_fp1 == variant.definition_fp1
        assert outcome.mints_ct32 is True
        print("evaluation is analysis.rerun citing that fingerprint")
    print("book/bms variants ok")


if __name__ == "__main__":
    main()
