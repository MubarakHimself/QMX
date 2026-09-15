"""Story 38.1 — QMB optimize/sweep is search: same bot fp1, not generation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, cast

from qmb.config import (
    ASSIGNMENT_KEY,
    CLOCK_REPLAY,
    PROVENANCE_RECORDED,
    STARTING_CAPITAL_KEY,
    ConfigFragment,
    ResolvedRunConfig,
    compile_run_config,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.ledger.line import ROLE_TRIAL, LedgerLine, mint_completed_line
from qmb.optimize import admit_study, coerce_study_space
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmb.results import mint_run_performance_result
from qmb.sweep import admit_sweep
from qmf.core.chrono import CalendarIdentity, Instant, Interval, WriterId
from qmf.core.exact import Money, UnitKind
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Result, is_ok
from qmf.registry import RegistrationRecord
from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability
from qmf.risk.performance import PerformanceResult
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BmsDefinition,
    BookDefinition,
)
from qml.declaration import mint_bot_definition, mint_confluence
from qml.footprint import ProducerBinding, mint_footprint
from qml.generation import ACT_SEARCH, QMB_AUTHORS_CANDIDATES, classify_parameter_search
from qml.logic import mint_logic_identity

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"
_SEED = Money(value=1_000_000, currency="USD", scale=2)
_TF_1M = {"kind": "time-interval", "seconds": 60}
_TF_5M = {"kind": "time-interval", "seconds": 300}
_QMB_SRC = Path(__file__).resolve().parents[1] / "src" / "qmb"
_SOURCE = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, instant):\n    return ()\n",
}


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer(stream: str = "config-fragment") -> WriterId:
    return _ok(WriterId.try_create("node-a", "authoring", stream, "boot-1"))


def _variable(name: str, minor: int) -> TemplateVariable:
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
                "admission_bar": _section("admission_bar", _variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _variable("loss_floor", 800_000)),
                "exit_policy": _section("exit_policy", _variable("q", 100)),
            },
        )
    )


def _bms() -> BmsDefinition:
    return _ok(
        BmsDefinition.try_create(
            BMS_CONTRACT_FORMAT_VERSION,
            {
                "accounting_rules": _section("accounting_rules", _variable("numeraire_unit", 1)),
                "constraints": _section("constraints", _variable("exposure_ceiling", 50_000)),
                "ksa_policy": _section("ksa_policy", _variable("posture", 1)),
                "reporting": _section("reporting", _variable("cadence", 1)),
            },
        )
    )


def _record(kind: str, body: object) -> RegistrationRecord:
    if isinstance(body, (BookDefinition, BmsDefinition)):
        parents: tuple[object, ...] = (_ok(body.fingerprint()),)
        payload: Mapping[str, object] = body.fp1_identity()
        version = body.contract_format_version
    else:
        parents = ()
        payload = cast("Mapping[str, object]", body)
        version = 1
    return _ok(
        RegistrationRecord.try_create(kind, version, parents, payload, _writer(kind), 0, _instant())
    )


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "search-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _definition_body() -> Mapping[str, object]:
    calendar = _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))
    confluence = _ok(mint_confluence([{"role": "level", "producer_binding": _pinned("zone")}]))
    footprint = _ok(
        mint_footprint(
            [
                {
                    "instrument_role": "primary",
                    "bar_specs": [{"kind": "time-interval", "seconds": 60}],
                    "stream_role": "trading",
                }
            ],
            [calendar],
            [_pinned("sma")],
        )
    )
    logic = _ok(mint_logic_identity("research-bot", "1.0.0", _SOURCE))
    bot = _ok(
        mint_bot_definition(
            strategy_family_id="trend-follow",
            confluence_set=[confluence],
            parameter_space=[
                {
                    "name": "lookback",
                    "type": "exact integer",
                    "bounds": {"min": 1, "max": 200},
                    "step": 1,
                    "default": 20,
                    "unit_kind": UnitKind.COUNT,
                    "ui": "ui-editable",
                }
            ],
            footprint=footprint,
            permitted_exit_intents=(),
            logic_reference=logic,
        )
    )
    return bot.body()


def _port_with_bot(
    bot: RegistrationRecord,
) -> tuple[RegistryReadPort, ConfigFragment, ConfigFragment, RegistrationRecord]:
    book_record = _record("book-definition", _book())
    bms_record = _record("bms-definition", _bms())
    pointers = (
        _ok(DatedPointer.try_create("mean-reversion", bot.stable_id, _instant())),
        _ok(DatedPointer.try_create("scalping", book_record.stable_id, _instant())),
    )
    as_of = _ok(
        AsOfSet.try_create(
            _instant(),
            records=(book_record, bms_record, bot),
            pointers=pointers,
        )
    )
    port = _ok(
        RegistryReadPort.try_create(
            _ok(PassiveHub.try_create((as_of,))),
            stale_evidence_severity=_SEVERITY,
        )
    )
    book_fragment = _ok(materialize_book_fragment(port, book_record.stable_id, _writer()))
    bms_fragment = _ok(materialize_bms_fragment(port, bms_record.stable_id, _writer()))
    return port, book_fragment, bms_fragment, bot


def _defaults() -> dict[str, object]:
    return {
        "account_id": "acct-replay",
        "clock": CLOCK_REPLAY,
        "data_provenance": PROVENANCE_RECORDED,
        "fill": "default-fill",
        "venue_id": "venue-replay",
    }


def _span() -> Interval:
    return _ok(Interval.try_create(_instant(_NS), _instant(_NS + 1_000)))


def _trial_line(
    config: ResolvedRunConfig, *, lookback: int
) -> tuple[LedgerLine, PerformanceResult]:
    span = _span()
    outcome: dict[str, object] = {
        "data_points_processed": 1,
        "evidence_range": span,
        "filled": (),
        "lookback": lookback,
        "resting": (),
        "slice_count": 1,
        "stream_order": ("EURUSD",),
    }
    artifact = _ok(
        mint_run_performance_result(
            config,
            evidence_range=span,
            stream_order=("EURUSD",),
            slice_count=1,
            filled_count=0,
            resting_count=0,
            data_points_processed=1,
            outcome_identity=outcome,
        )
    )
    line = _ok(
        mint_completed_line(
            config,
            outcome_identity=outcome,
            ct32_fingerprint=_ok(artifact.fingerprint()),
            role=ROLE_TRIAL,
        )
    )
    return line, artifact


def test_qmb_does_not_author_candidates() -> None:
    assert QMB_AUTHORS_CANDIDATES is False
    assert not (_QMB_SRC / "generation").exists()
    assert not (_QMB_SRC / "generator.py").exists()
    assert not (_QMB_SRC / "random_condition.py").exists()


def test_optimize_and_sweep_trial_lines_cite_the_same_bot_fp1() -> None:
    bot = _record("bot-definition", _definition_body())
    port, book_fragment, bms_fragment, bot_record = _port_with_bot(bot)
    space = _ok(
        coerce_study_space(
            [
                {
                    "name": "lookback",
                    "type": "exact integer",
                    "unit_kind": UnitKind.COUNT,
                    "bounds": {"min": 1, "max": 200},
                    "step": 1,
                    "default": 20,
                    "ui": "ui-editable",
                }
            ]
        )
    )
    study = _ok(admit_study(space, seed=7, port=port, bot=bot_record.stable_id))
    configs: list[ResolvedRunConfig] = []
    artifacts: list[PerformanceResult] = []
    lines: list[LedgerLine] = []
    for lookback in (10, 20, 40):
        compiled = _ok(
            compile_run_config(
                study.port,
                book_fragment=book_fragment,
                bms_fragment=bms_fragment,
                run_spec={
                    "bot": study.label.bot_fp1,
                    STARTING_CAPITAL_KEY: _SEED,
                    ASSIGNMENT_KEY: {"lookback": lookback},
                },
                workspace_defaults=_defaults(),
            )
        )
        line, artifact = _trial_line(compiled, lookback=lookback)
        configs.append(compiled)
        artifacts.append(artifact)
        lines.append(line)
    bot_fps = {config.bot_fp1 for config in configs}
    assert bot_fps == {study.label.bot_fp1}
    assert {config.bot_fp1 for config in configs} == {bot_record.stable_id}
    assignments = [
        cast("Mapping[str, object]", config.keys[ASSIGNMENT_KEY])["lookback"] for config in configs
    ]
    assert assignments == [10, 20, 40]
    cited = [artifact.population.bot_identity for artifact in artifacts]
    assert set(cited) == {study.label.bot_fp1}
    assert {line.role for line in lines} == {ROLE_TRIAL}
    classified = classify_parameter_search(
        bot_fp1=study.label.bot_fp1,
        trial_bot_fp1s=tuple(config.bot_fp1 for config in configs),
    )
    assert _ok(classified).value == ACT_SEARCH


def test_sweep_trial_labels_cite_the_same_bot_fp1() -> None:
    bot = _record("bot-definition", _definition_body())
    port, _book_fragment, _bms_fragment, bot_record = _port_with_bot(bot)
    book_id: Fingerprint | None = None
    bms_id: Fingerprint | None = None
    for record in port.bound.records:
        if record.kind == "book-definition":
            book_id = record.stable_id
        elif record.kind == "bms-definition":
            bms_id = record.stable_id
    assert book_id is not None
    assert bms_id is not None
    admitted = _ok(
        admit_sweep(
            {
                "bot": bot_record.stable_id,
                "book": book_id,
                "bms": bms_id,
                "instruments": ["EURUSD", "GBPUSD"],
                "timeframes": [_TF_1M, _TF_5M],
                "parameters": {"lookback": [10, 20]},
            },
            port,
            _writer(),
        )
    )
    run_bots = {_ok(admitted.run_label(combo))["bot_fp1"] for combo in admitted.combos}
    assert run_bots == {admitted.label.bot_fp1.value}
    compiled_combos = _ok(
        admitted.compile_all(
            invocation_flags={STARTING_CAPITAL_KEY: _SEED},
            workspace_defaults=_defaults(),
        )
    )
    assert {config.bot_fp1 for config in compiled_combos} == {admitted.label.bot_fp1}
    sweep_search = classify_parameter_search(
        bot_fp1=admitted.label.bot_fp1,
        trial_bot_fp1s=tuple(config.bot_fp1 for config in compiled_combos),
    )
    assert _ok(sweep_search).value == ACT_SEARCH
