"""Reference usage — one registry as-of frozen for every combination (Story 20.2).

Executable::

    python qmb/examples/sweep_admit_usage.py

Shows the things B-15 / SC-11 / Story 20.2 pin down:

1. A sweep is admitted as a batch: admission resolves exactly ONE registry as-of
   — a (registry_as_of instant + set fingerprint) — through the single
   library-owned registry-read port, then freezes it for every combination and
   stamps it into the sweep label and every combo's run label.
2. After admission, every Book/BMS/bot fragment resolves by explicit fingerprint
   against the frozen as-of set, never by name@latest; two combos citing the same
   Book resolve the identical Book fp1, and a fresher registry state arriving
   mid-batch never reaches an in-flight combination.
3. A context reference that a fresher as-of shows superseded at admission time is
   an AD-11 stale-evidence refusal at the configured severity — no invented
   default — never a silent bind of either version.
4. The frozen registry_as_of appears verbatim as the registry_as_of field in
   every combination's CT-32 label set.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

from qmb.config import CLOCK_REPLAY, PROVENANCE_RECORDED, STARTING_CAPITAL_KEY
from qmb.registryread import (
    AsOfSet,
    DatedPointer,
    PassiveHub,
    RegistryReadPort,
    SupersedesRef,
)
from qmb.results import mint_run_performance_result
from qmf.core.chrono import Instant, Interval, WriterId
from qmf.core.exact import Money, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord
from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BmsDefinition,
    BookDefinition,
)

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"
_SEED = Money(value=1_000_000, currency="USD", scale=2)
_TF_1M = {"kind": "time-interval", "seconds": 60}
_TF_5M = {"kind": "time-interval", "seconds": 300}


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _writer() -> WriterId:
    return _unwrap(
        WriterId.try_create("node-a", "authoring", "config-fragment", "boot-1"), "writer"
    )


def _variable(name: str, minor: int) -> TemplateVariable:
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


def _book(q: int = 100) -> BookDefinition:
    return _unwrap(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _variable("loss_floor", 800_000)),
                "exit_policy": _section("exit_policy", _variable("q", q)),
            },
        ),
        "book",
    )


def _bms() -> BmsDefinition:
    return _unwrap(
        BmsDefinition.try_create(
            BMS_CONTRACT_FORMAT_VERSION,
            {
                "accounting_rules": _section("accounting_rules", _variable("numeraire_unit", 1)),
                "constraints": _section("constraints", _variable("exposure_ceiling", 50_000)),
                "ksa_policy": _section("ksa_policy", _variable("posture", 1)),
                "reporting": _section("reporting", _variable("cadence", 1)),
            },
        ),
        "bms",
    )


def _record(kind: str, body: object) -> RegistrationRecord:
    if isinstance(body, (BookDefinition, BmsDefinition)):
        parents: tuple[object, ...] = (_unwrap(body.fingerprint(), "definition fp1"),)
        payload: Mapping[str, object] = body.fp1_identity()
        version = body.contract_format_version
    else:
        parents = ()
        payload = cast("Mapping[str, object]", body)
        version = 1
    return _unwrap(
        RegistrationRecord.try_create(kind, version, parents, payload, _writer(), 0, _instant()),
        "record",
    )


def _run_settings() -> dict[str, object]:
    return {
        "invocation_flags": {STARTING_CAPITAL_KEY: _SEED},
        "workspace_defaults": {
            "account_id": "acct-replay",
            "clock": CLOCK_REPLAY,
            "data_provenance": PROVENANCE_RECORDED,
            "venue_id": "venue-replay",
        },
    }


def main() -> None:
    book_record = _record("book-definition", _book())
    bms_record = _record("bms-definition", _bms())
    bot_record = _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion"})
    pointers = (
        _unwrap(
            DatedPointer.try_create("mean-reversion", bot_record.stable_id, _instant()), "pointer"
        ),
        _unwrap(DatedPointer.try_create("scalping", book_record.stable_id, _instant()), "pointer"),
    )
    as_of = _unwrap(
        AsOfSet.try_create(
            _instant(), records=(book_record, bms_record, bot_record), pointers=pointers
        ),
        "as-of set",
    )
    hub = _unwrap(PassiveHub.try_create((as_of,)), "hub")
    port = _unwrap(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY), "port")

    declaration = _unwrap(
        qmb.SweepDeclaration.try_create(
            bot=bot_record.stable_id,
            book=book_record.stable_id,
            bms=bms_record.stable_id,
            instruments=["EURUSD", "GBPUSD"],
            timeframes=[_TF_1M, _TF_5M],
            parameters={"lookback": [10, 20, 30]},
        ),
        "declaration",
    )

    admitted = _unwrap(qmb.admit_sweep(declaration, port, _writer()), "admission")
    assert admitted.port.frozen is True
    assert admitted.registry_as_of == as_of.registry_as_of
    assert admitted.set_fingerprint == as_of.fingerprint
    assert admitted.run_count == 12
    print(
        "one registry as-of resolved at admission, frozen for every combination: "
        f"{admitted.run_count} combos share as-of {admitted.set_fingerprint.value[:19]}..."
    )

    stamp = admitted.registry_as_of_stamp()
    for combo in admitted.combos:
        run_label = _unwrap(admitted.run_label(combo), "run label")
        assert run_label["registry_as_of"] == stamp
    print("sweep label and every combo run label carry the identical frozen as-of")

    settings = _run_settings()
    configs = _unwrap(admitted.compile_all(**settings), "compile all")
    book_fps = {config.book_fp1 for config in configs}
    bms_fps = {config.bms_fp1 for config in configs}
    bot_fps = {config.bot_fp1 for config in configs}
    assert book_fps == {admitted.label.book_fp1}
    assert bms_fps == {admitted.label.bms_fp1}
    assert bot_fps == {admitted.label.bot_fp1}
    print("two combos citing the same Book resolve the identical Book fp1")

    assert is_refusal(admitted.port.resolve("mean-reversion"))
    assert is_refusal(admitted.port.resolve("scalping@latest"))
    print("after admission fragments resolve by explicit fp1, never name@latest")

    stale = _stale_admission()
    assert is_refusal(stale)
    assert stale.category is RefusalCategory.STALE_EVIDENCE
    assert stale.context["severity"] == _SEVERITY
    print("a superseded reference at admission is an AD-11 stale-evidence refusal; no default")

    registry_input = _unwrap(
        fingerprint(
            {
                "class": "registry-as-of",
                "registry_as_of": admitted.registry_as_of.fp1_identity(),
                "fingerprint": admitted.set_fingerprint.value,
            }
        ),
        "registry input",
    )
    for combo, config in zip(admitted.combos, configs, strict=True):
        assert config.keys["registry_as_of"] == stamp
        result = _unwrap(
            mint_run_performance_result(
                config,
                evidence_range=_unwrap(
                    Interval.try_create(_instant(_NS), _instant(_NS + 1_000)), "interval"
                ),
                stream_order=(combo.instrument,),
                slice_count=1,
                filled_count=0,
                resting_count=0,
                data_points_processed=1,
                outcome_identity={"done": True},
            ),
            "ct-32",
        )
        assert registry_input in result.result_label.input_fingerprints
    print("registry_as_of appears verbatim in every combo's CT-32 label set")

    print("sweep admission ok")


def _stale_admission() -> Result[qmb.AdmittedSweep]:
    """Admit a sweep whose Book reference a fresher as-of shows superseded."""
    book_v1 = _record("book-definition", _book(q=100))
    book_v2 = _record("book-definition", _book(q=200))
    bms_record = _record("bms-definition", _bms())
    bot_record = _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion"})
    supersedes = (
        _unwrap(SupersedesRef.try_create(book_v2.stable_id, book_v1.stable_id), "supersedes"),
    )
    as_of = _unwrap(
        AsOfSet.try_create(
            _instant(),
            records=(book_v1, book_v2, bms_record, bot_record),
            supersedes=supersedes,
        ),
        "as-of set",
    )
    hub = _unwrap(PassiveHub.try_create((as_of,)), "hub")
    port = _unwrap(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY), "port")
    declaration = _unwrap(
        qmb.SweepDeclaration.try_create(
            bot=bot_record.stable_id,
            book=book_v1.stable_id,
            bms=bms_record.stable_id,
            instruments=["EURUSD"],
            timeframes=[_TF_1M],
        ),
        "declaration",
    )
    return qmb.admit_sweep(declaration, port, _writer())


if __name__ == "__main__":
    main()
