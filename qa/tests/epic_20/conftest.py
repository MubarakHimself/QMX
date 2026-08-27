"""Independent fixture builders for the Epic 20 (qmb-sweeps) audit.

Every builder here is owned by the TEST, not by the code under test. Fixtures are
built from the ratified qmf-core / qmf-registry / qmf-risk value types directly
(Money, ExactRational, Instant, WriterId, RegistrationRecord, AsOfSet,
BookDefinition, ...) so they are shape-faithful to the contracts by construction.
The sweep package (``qmb.sweep``) is imported only to EXERCISE it — never to build
an input that would then be asserted against itself.

Discipline (HARDENED AUTHOR CONTRACT):
  * effects are observed through returned artifacts, the on-disk ledger lines, and
    RETURNED CT-04 refusals — never a module's self-declared flag as proof;
  * ``ok()`` unwraps a value-or-refusal and fails loudly on a refusal;
  * refusals are RETURNED TypedRefusal values, asserted by category + context.

The batch execution fixtures (`happy_batch`, `victim_batch`, `concurrent_pair`)
run the REAL never-forked run loop under the REAL orchestrator/governor/ledger —
each combination is one isolated OS process writing one ledger line. They are
module-scoped so the (slow) process fan-out runs once and many assertions read it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar, cast

import pytest

from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import ExactRational, Money, UnitKind
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import Result, is_ok
from qmf.registry import RegistrationRecord
from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BmsDefinition,
    BookDefinition,
)

import qmb
from qmb.config import CLOCK_REPLAY, PROVENANCE_RECORDED, STARTING_CAPITAL_KEY
from qmb.ledger import LedgerLine
from qmb.registryread import (
    AsOfSet,
    DatedPointer,
    PassiveHub,
    RegistryReadPort,
    SupersedesRef,
)
from qmb.results import emit_measure
from qmb.runloop import SliceObservation
from qmb.sweep import AdmittedSweep, SweepDeclaration, SweepRunSpec, admit_sweep, run_sweep_batch

T = TypeVar("T")

NS: int = 1_700_000_000_000_000_000
SEVERITY: str = "workspace-declared"
SEED: Money = Money(value=1_000_000, currency="USD", scale=2)
TF_1M: dict[str, object] = {"kind": "time-interval", "seconds": 60}
TF_5M: dict[str, object] = {"kind": "time-interval", "seconds": 300}
GIB: int = 1024 * 1024 * 1024
PEAK: int = 64 * 1024 * 1024


def ok(result: Result[T]) -> T:
    """Unwrap an ``Ok`` or fail the test with the refusal's context."""
    assert is_ok(result), result
    return result.value


def instant(ns: int = NS) -> Instant:
    return ok(Instant.try_create(ns))


def writer(stream: str = "config-fragment") -> WriterId:
    return ok(WriterId.try_create("node-a", "authoring", stream, "boot-1"))


def fp(*parts: object) -> Fingerprint:
    """A test-owned fp1 over arbitrary parts (for building ledger-line ids)."""
    return ok(fingerprint({"parts": list(parts)}))


# --- ratified Book / BMS / bot registration records --------------------------


def _variable(name: str, minor: int) -> TemplateVariable:
    return ok(
        TemplateVariable.try_create(
            name,
            UnitKind.MONEY,
            Money(value=minor, currency="USD", scale=2),
            UiEditability.UI_EDITABLE,
            AdmissionImpact.RESIGN,
        )
    )


def _section(name: str, variable: TemplateVariable) -> TemplateSection:
    return ok(TemplateSection.try_create(name, {variable.name: variable}))


def book_definition(q: int = 100) -> BookDefinition:
    return ok(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _variable("loss_floor", 800_000)),
                "exit_policy": _section("exit_policy", _variable("q", q)),
            },
        )
    )


def bms_definition(cadence: int = 1) -> BmsDefinition:
    return ok(
        BmsDefinition.try_create(
            BMS_CONTRACT_FORMAT_VERSION,
            {
                "accounting_rules": _section("accounting_rules", _variable("numeraire_unit", 1)),
                "constraints": _section("constraints", _variable("exposure_ceiling", 50_000)),
                "ksa_policy": _section("ksa_policy", _variable("posture", 1)),
                "reporting": _section("reporting", _variable("cadence", cadence)),
            },
        )
    )


def record(kind: str, body: object) -> RegistrationRecord:
    if isinstance(body, (BookDefinition, BmsDefinition)):
        parents: tuple[object, ...] = (ok(body.fingerprint()),)
        payload: Mapping[str, object] = body.fp1_identity()
        version = body.contract_format_version
    else:
        parents = ()
        payload = cast("Mapping[str, object]", body)
        version = 1
    return ok(
        RegistrationRecord.try_create(kind, version, parents, payload, writer(kind), 0, instant())
    )


def bot_record(alias: str = "mean-reversion") -> RegistrationRecord:
    return record("bot-definition", {"class": "bot-definition", "alias": alias})


def make_port(*records: RegistrationRecord, **as_of_kwargs: object) -> RegistryReadPort:
    as_of = ok(AsOfSet.try_create(instant(), records=records, **as_of_kwargs))
    hub = ok(PassiveHub.try_create((as_of,)))
    return ok(RegistryReadPort.try_create(hub, stale_evidence_severity=SEVERITY))


def fixture_port() -> tuple[
    RegistryReadPort, RegistrationRecord, RegistrationRecord, RegistrationRecord
]:
    """A live port over one as-of holding a Book/BMS/bot the sweep can admit."""
    book = record("book-definition", book_definition())
    bms = record("bms-definition", bms_definition())
    bot = bot_record()
    pointers = (
        ok(DatedPointer.try_create("mean-reversion", bot.stable_id, instant())),
        ok(DatedPointer.try_create("scalping", book.stable_id, instant())),
    )
    port = make_port(book, bms, bot, pointers=pointers)
    return port, book, bms, bot


def declaration(
    *,
    bot: object,
    book: object,
    bms: object,
    instruments: object = ("EURUSD", "GBPUSD"),
    timeframes: object = (TF_1M,),
    parameters: object = None,
) -> SweepDeclaration:
    return ok(
        SweepDeclaration.try_create(
            bot=bot,
            book=book,
            bms=bms,
            instruments=instruments,
            timeframes=timeframes,
            parameters=parameters if parameters is not None else {"lookback": [10, 20]},
        )
    )


def admit(
    *,
    instruments: object = ("EURUSD", "GBPUSD"),
    timeframes: object = (TF_1M,),
    parameters: object = None,
) -> AdmittedSweep:
    port, book, bms, bot = fixture_port()
    decl = declaration(
        bot=bot.stable_id,
        book=book.stable_id,
        bms=bms.stable_id,
        instruments=instruments,
        timeframes=timeframes,
        parameters=parameters,
    )
    return ok(admit_sweep(decl, port, writer()))


def run_settings() -> dict[str, object]:
    return {
        "invocation_flags": {STARTING_CAPITAL_KEY: SEED},
        "workspace_defaults": {
            "account_id": "acct-replay",
            "clock": CLOCK_REPLAY,
            "data_provenance": PROVENANCE_RECORDED,
            "venue_id": "venue-replay",
        },
    }


def good_slices(combo: SweepRunSpec) -> tuple[tuple[SliceObservation, ...], ...]:
    return (
        (ok(SliceObservation.try_create(combo.instrument, instant(NS), True)),),
        (ok(SliceObservation.try_create(combo.instrument, instant(NS + 1), True)),),
    )


def make_ledger(root: Path, sub: str = "ledger") -> "qmb.LedgerSink":
    return ok(
        qmb.LedgerSink.try_create(root / sub, machine="node-a", worker_slot=0, boot_epoch_id="boot-1")
    )


def runs_dir(root: Path, sub: str = "runs") -> Path:
    directory = root / sub
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def run_batch(
    admitted: AdmittedSweep,
    root: Path,
    *,
    combo_slices: object = good_slices,
    cpu_budget: int = 2,
    memory_budget: int = GIB,
    projected_peak_memory: int = PEAK,
    runs_sub: str = "runs",
    ledger_sub: str = "ledger",
    role: object = None,
) -> "qmb.SweepBatchReport":
    kwargs: dict[str, object] = dict(
        output_root=runs_dir(root, runs_sub),
        ledger=make_ledger(root, ledger_sub),
        combo_slices=combo_slices,
        projected_peak_memory=projected_peak_memory,
        cpu_budget=cpu_budget,
        memory_budget=memory_budget,
        **run_settings(),
    )
    if role is not None:
        kwargs["role"] = role
    return ok(run_sweep_batch(admitted, **kwargs))


# --- shape-faithful ledger lines for the ranking fold (Story 20.4) -----------

_BAR = fingerprint({"class": "book-bar", "id": "bar-1"})
_BAR_SPEC: dict[str, object] = {"kind": "time-interval", "seconds": 60}


def sweep_id_a() -> Fingerprint:
    return ok(fingerprint({"class": "sweep", "id": "sweep-a"}))


def sweep_id_b() -> Fingerprint:
    return ok(fingerprint({"class": "sweep", "id": "sweep-b"}))


def coordinates(sweep_id: Fingerprint, instrument: str, param: str) -> dict[str, object]:
    return {
        "bar_spec": _BAR_SPEC,
        "class": "qmb-sweep-coordinates",
        "format_version": 1,
        "instrument": instrument,
        "param_hash": fp("param", param).value,
        "sweep_id": sweep_id.value,
    }


def net_profit(minor: int) -> dict[str, object]:
    return ok(emit_measure("net_profit", Money(value=minor, currency="USD", scale=2))).fp1_identity()


def max_drawdown(num: int, den: int) -> dict[str, object]:
    quantity = ok(ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO))
    return ok(emit_measure("max_drawdown", quantity)).fp1_identity()


def completed_line(
    run: str,
    *,
    sweep_id: Fingerprint,
    measures: tuple[dict[str, object], ...],
    instrument: str = "EURUSD",
    world: World = World.REPLAY,
    role: str = "confirmation",
) -> LedgerLine:
    return LedgerLine(
        run_id=fp("run", run),
        role=role,
        world=world,
        result_label={"class": "result-label", "world": world.value, "run": run},
        book_bar_fp1=ok(_BAR),
        measures=measures,
        ct32_fingerprint=fp("ct32", run),
        sweep_coordinates=coordinates(sweep_id, instrument, run),
    )


def aborted_line(run: str, *, sweep_id: Fingerprint, instrument: str = "EURUSD") -> LedgerLine:
    return LedgerLine(
        run_id=fp("run", run),
        role="aborted",
        world=World.REPLAY,
        result_label={"class": "result-label", "world": World.REPLAY.value, "run": run},
        book_bar_fp1=ok(_BAR),
        measures=(),
        ct32_fingerprint=None,
        refusal={"category": "invalid input", "field": "terminal", "reason": "combo refused"},
        sweep_coordinates=coordinates(sweep_id, instrument, run),
    )


# --- module-scoped batch executions (the slow, real, process-per-run fan-out) -


@dataclass(frozen=True)
class BatchRun:
    admitted: AdmittedSweep
    report: "qmb.SweepBatchReport"
    ledger_root: Path


@pytest.fixture(scope="module")
def happy_batch(tmp_path_factory: pytest.TempPathFactory) -> BatchRun:
    """One admitted 2x1x2 = 4-combo sweep, every combination completing."""
    root = tmp_path_factory.mktemp("happy")
    admitted = admit(instruments=("EURUSD", "GBPUSD"), parameters={"lookback": [10, 20]})
    report = run_batch(admitted, root)
    return BatchRun(admitted=admitted, report=report, ledger_root=make_ledger(root).root)


@pytest.fixture(scope="module")
def victim_batch(tmp_path_factory: pytest.TempPathFactory) -> BatchRun:
    """A 4-combo sweep where one combination's stream is invalid: it aborts, the
    batch continues, and the survivors complete."""
    root = tmp_path_factory.mktemp("victim")
    admitted = admit(instruments=("EURUSD", "GBPUSD"), parameters={"lookback": [10, 20]})
    victim = admitted.combos[1]

    def _slices(combo: SweepRunSpec) -> tuple[tuple[SliceObservation, ...], ...]:
        if combo.fp1_identity() == victim.fp1_identity():
            return ((ok(SliceObservation.try_create("NOT-A-STREAM", instant(), True)),),)
        return good_slices(combo)

    report = run_batch(admitted, root, combo_slices=_slices)
    return BatchRun(admitted=admitted, report=report, ledger_root=make_ledger(root).root)
