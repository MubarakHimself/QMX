"""Reference usage — analysis.rerun is a new QMB run and a new CT-32 (Story 35.3).

Executable::

    python qmb/examples/analysis_rerun_usage.py

Shows the things Story 35.3 / FR-W25 / FR-W11 / SCN-0016 pin down:

1. analysis.rerun is a new governed QMB run through the tunnel.
2. Canonical artifact is a new CT-32, not a rewrite of the source.
3. Occupancy is one qmb run invocation — not a query.
4. starting_capital override stamps seed_overridden and forces fold unrated.
5. analysis_method and lane are not CT-32 or B-4 fields.
6. Metadata lives on the QMB ledger line (workbench_lane=governed) citing CT-32 by _ref.
7. Coordinated Experiment Ledger stamp is Epic 36.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypeVar

from qmb.analysis import rerun
from qmb.config import (
    CLOCK_REPLAY,
    FOLD_UNRATED,
    PROVENANCE_RECORDED,
    STARTING_CAPITAL_KEY,
    ResolvedRunConfig,
    compile_run_config,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmb.results import mint_run_performance_result
from qmb.results.ct32 import load_stored_ct32
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
_SEED_ALT = Money(value=2_000_000, currency="USD", scale=2)


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


def _config(*, tag: str) -> ResolvedRunConfig:
    stamp = _unwrap(fingerprint({"n": "analysis-rerun-example", "tag": tag}), "fp")
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


def _source() -> PerformanceResult:
    config = _config(tag="source")
    outcome = _unwrap(
        run(slices=_slices(), config=config, handler=SilentSliceHandler()),
        "run",
    )
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


def _writer() -> WriterId:
    return _unwrap(WriterId.try_create("node-a", "authoring", "fragment", "boot-1"), "writer")


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


def main() -> None:
    source = _source()
    source_fp = _unwrap(source.fingerprint(), "source-fp")
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
            rerun(
                source_ct32=source,
                config=_config(tag="rerun"),
                slices=_slices(),
                output_root=root / "runs",
                ledger=sink,
            ),
            "rerun",
        )
        assert outcome.occupancy == "run"
        assert outcome.mints_ct32 is True
        assert outcome.ct32_fingerprint != source_fp
        stored = _unwrap(load_stored_ct32(outcome.isolated.output_dir), "stored")
        assert "analysis_method" not in stored
        assert "lane" not in stored
        line = outcome.ledger_line.fp1_identity()
        assert line["workbench_lane"] == "governed"
        assert line["ct32"] == {"_ref": outcome.ct32_fingerprint.value}
        assert "analysis_method" not in line
        print("analysis.rerun is a new QMB run")
        print("canonical artifact is a new CT-32")
        print("occupancy is run, not a query")
        print("workbench_lane=governed cites CT-32 by _ref")
        print("analysis_method and lane are not CT-32 or B-4 fields")

        query = rerun(occupancy="query")
        assert is_refusal(query)
        print("query occupancy refused")

        book = _unwrap(
            BookDefinition.try_create(
                BOOK_CONTRACT_FORMAT_VERSION,
                "USD",
                {
                    "admission_bar": _section(
                        "admission_bar", _money_variable("bar_floor", 1)
                    ),
                    "money_rules": _section(
                        "money_rules", _money_variable("loss_floor", 800_000)
                    ),
                    "exit_policy": _section("exit_policy", _money_variable("q", 100)),
                },
            ),
            "book",
        )
        bms = _unwrap(
            BmsDefinition.try_create(
                BMS_CONTRACT_FORMAT_VERSION,
                {
                    "accounting_rules": _section(
                        "accounting_rules", _money_variable("numeraire_unit", 1)
                    ),
                    "constraints": _section(
                        "constraints", _money_variable("exposure_ceiling", 50_000)
                    ),
                    "ksa_policy": _section("ksa_policy", _money_variable("posture", 1)),
                    "reporting": _section("reporting", _money_variable("cadence", 1)),
                },
            ),
            "bms",
        )
        book_record = _unwrap(
            RegistrationRecord.try_create(
                "book-definition",
                book.contract_format_version,
                (_unwrap(book.fingerprint(), "book-fp"),),
                book.fp1_identity(),
                _writer(),
                0,
                _instant(),
            ),
            "book-record",
        )
        bms_record = _unwrap(
            RegistrationRecord.try_create(
                "bms-definition",
                bms.contract_format_version,
                (_unwrap(bms.fingerprint(), "bms-fp"),),
                bms.fp1_identity(),
                _writer(),
                0,
                _instant(),
            ),
            "bms-record",
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
        pointer = _unwrap(
            DatedPointer.try_create("mean-reversion", bot.stable_id, _instant()),
            "pointer",
        )
        as_of = _unwrap(
            AsOfSet.try_create(
                _instant(),
                records=(book_record, bms_record, bot),
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
            materialize_book_fragment(port, book_record.stable_id, _writer()),
            "book-fragment",
        )
        bms_fragment = _unwrap(
            materialize_bms_fragment(port, bms_record.stable_id, _writer()),
            "bms-fragment",
        )
        spec = {"bot": bot.stable_id, STARTING_CAPITAL_KEY: _SEED}
        defaults = {
            "account_id": "acct-replay",
            "clock": CLOCK_REPLAY,
            "data_provenance": PROVENANCE_RECORDED,
            "venue_id": "venue-replay",
            STREAM_SET_KEY: ("eurusd",),
        }
        rated = _unwrap(
            compile_run_config(
                port,
                book_fragment=book_fragment,
                bms_fragment=bms_fragment,
                run_spec=spec,
                workspace_defaults=defaults,
            ),
            "rated",
        )
        assert rated.seed_overridden is False
        seed = _unwrap(
            rerun(
                source_ct32=source,
                port=port,
                book_fragment=book_fragment,
                bms_fragment=bms_fragment,
                run_spec=spec,
                workspace_defaults=defaults,
                starting_capital=_SEED_ALT,
                slices=_slices(),
                output_root=root / "seed",
                ledger=_unwrap(
                    qmb.LedgerSink.try_create(
                        root / "ledger-seed",
                        machine="example-machine",
                        worker_slot=1,
                        boot_epoch_id="boot-1",
                    ),
                    "seed-ledger",
                ),
            ),
            "seed-rerun",
        )
        assert seed.config.seed_overridden is True
        assert seed.config.fold_rating == FOLD_UNRATED
        print("starting_capital override stamps seed_overridden and fold unrated")
        epic = rerun(experiment_spec=True)
        assert is_refusal(epic)
        print("coordinated Experiment Ledger is Epic 36")
    print("analysis.rerun ok")


if __name__ == "__main__":
    main()
