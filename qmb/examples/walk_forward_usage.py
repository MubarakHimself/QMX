"""Reference usage — walk-forward as a sequence of split-manifest runs (Story 22.5).

Executable::

    python qmb/examples/walk_forward_usage.py

Shows what the fourth B-14 ladder rung pins down:

1. A walk-forward is an ordered sequence of split manifests: each window pairs one
   in-sample and one out-of-sample CT-12 split manifest and materializes as two
   first-class runs under B-3/B-4, each with its own resolved run-config and its own
   ledger line. ``train``/``test`` are display aliases for the two manifests, never a
   substitute for their fingerprints.
2. An in-sample (train) run ledgers role=trial with its objective measure and never a
   bar verdict; an out-of-sample window's bar outcome is a read-time fold that returns
   not-yet-ruled until GAP-0048/0049 close (no verdict-bearing backtest ships).
3. Admission resolves exactly ONE registry as-of through the single B-15 registry-read
   port, freezes it for every window, and stamps it into the batch and window labels;
   after admission fragments resolve by explicit fingerprint, never name@latest.
4. The window count, in-sample and out-of-sample spans, and step are UI-editable
   configurables with no ratified value; the module ships no default and no WF/OOS battery.
5. The walk-forward view is a read-time aggregation over the ledger's window runs — never
   a merged run — whose in-sample / out-of-sample distributions are the declared feeders
   for the deferred PBO / CSCV governance battery, and it ships no threshold.
6. Recompiling a window run under its resolved config reproduces the run-config
   fingerprint; each window's label carries its split fingerprints, registry_as_of,
   world, and evidence class.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

from qmb.config import CLOCK_REPLAY, PROVENANCE_RECORDED, STARTING_CAPITAL_KEY
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmf.core.chrono import CalendarIdentity, Instant, WriterId
from qmf.core.exact import ExactRational, Money, UnitKind
from qmf.core.fingerprint import World
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.data.splits import SplitBoundary, SplitManifest
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


def _ratio(numerator: int, denominator: int = 10) -> ExactRational:
    return _unwrap(
        ExactRational.try_create(numerator, denominator, UnitKind.DIMENSIONLESS_RATIO), "ratio"
    )


def _manifest(offset: int) -> SplitManifest:
    """One CT-12 split manifest — a knowledge-time / embargo-purge / calendar-in-band unit."""
    calendar = _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025b"), "calendar")
    segments = _unwrap(
        SplitManifest.default_split_segments([1000 + offset, 2000 + offset, 3000 + offset]),
        "segments",
    )
    seal_boundary = _unwrap(SplitBoundary.try_create(3000 + offset), "seal boundary")
    return _unwrap(
        SplitManifest.try_create(
            calendar_identity=calendar,
            segments=segments,
            seal_boundary=seal_boundary,
            purge_width=0,
            embargo_width=0,
            world=World.REPLAY,
        ),
        "split manifest",
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


def _book() -> BookDefinition:
    return _unwrap(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _variable("loss_floor", 800_000)),
                "exit_policy": _section("exit_policy", _variable("q", 100)),
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
    # 1. A walk-forward is a sequence of split manifests. Two rolling windows, each a
    # distinct in-sample / out-of-sample split-manifest pair; each window is two runs.
    windows = [
        _unwrap(
            qmb.WalkForwardWindow.try_create(
                index, _manifest(index * 100), _manifest(index * 100 + 50)
            ),
            "window",
        )
        for index in range(2)
    ]
    first = windows[0]
    assert first.in_sample_run.role == qmb.IN_SAMPLE_RUN_ROLE == "trial"
    assert first.in_sample_run.contributes_to_objective is True
    assert first.out_of_sample_run.contributes_to_objective is False
    assert first.runs == (first.in_sample_run, first.out_of_sample_run)
    # train/test are display aliases for the two manifest fingerprints, never a substitute.
    assert first.display_aliases() == {
        "train": first.in_sample_split.value,
        "test": first.out_of_sample_split.value,
    }
    assert "train" not in first.fp1_identity()
    print(
        "a walk-forward is a sequence of split manifests; each window is two first-class runs; "
        "train/test are display aliases:",
        list(first.display_aliases()),
    )

    # A plan sequences the windows and pins the deferred configurables.
    plan = _unwrap(
        qmb.plan_walk_forward(
            windows,
            config={
                qmb.WINDOW_COUNT_KEY: 2,
                qmb.IN_SAMPLE_SPAN_KEY: 500,
                qmb.OUT_OF_SAMPLE_SPAN_KEY: 100,
                qmb.STEP_KEY: 100,
            },
        ),
        "plan",
    )
    assert plan.window_count == 2
    assert len(plan.runs) == 4  # two runs per window
    print("the ordered window sequence has", len(plan.runs), "first-class runs")

    # 2. In-sample run ledgers role=trial, never a bar verdict; OOS bar outcome is a
    # read-time fold that returns not-yet-ruled while GAP-0048/0049 stay open.
    assert qmb.fold_oos_bar_outcome(first) == qmb.OOS_BAR_OUTCOME_NOT_YET_RULED == "not-yet-ruled"
    assert qmb.VERDICT_BEARING_BACKTEST_SHIPS is False
    assert is_refusal(qmb.refuse_window_bar_verdict("bar-pass"))
    print(
        "in-sample run is role=trial, never a bar verdict; OOS bar outcome is a read-time fold:",
        qmb.fold_oos_bar_outcome(first),
        "gated behind",
        qmb.OOS_VERDICT_GATED_BEHIND,
    )

    # 3. Admission resolves exactly ONE registry as-of, frozen for every window.
    book_record = _record("book-definition", _book())
    bms_record = _record("bms-definition", _bms())
    bot_record = _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion"})
    pointers = (
        _unwrap(
            DatedPointer.try_create("mean-reversion", bot_record.stable_id, _instant()), "pointer"
        ),
    )
    as_of = _unwrap(
        AsOfSet.try_create(
            _instant(), records=(book_record, bms_record, bot_record), pointers=pointers
        ),
        "as-of set",
    )
    hub = _unwrap(PassiveHub.try_create((as_of,)), "hub")
    port = _unwrap(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY), "port")

    definition = _unwrap(
        qmb.WalkForwardDefinition.try_create(
            bot=bot_record.stable_id,
            book=book_record.stable_id,
            bms=bms_record.stable_id,
            plan=plan,
        ),
        "definition",
    )
    admitted = _unwrap(qmb.admit_walk_forward(definition, port, _writer()), "admission")
    assert admitted.port.frozen is True
    assert admitted.registry_as_of == as_of.registry_as_of
    assert admitted.window_count == 2
    assert admitted.run_count == 4
    stamp = admitted.registry_as_of_stamp()
    print(
        "one registry as-of resolved at admission, frozen for every window:",
        f"{admitted.window_count} windows share as-of {admitted.set_fingerprint.value[:19]}...",
    )

    # After admission fragments resolve by explicit fp1, never name@latest.
    assert is_refusal(admitted.port.resolve("mean-reversion"))
    assert is_refusal(admitted.port.resolve("scalping@latest"))
    print("after admission fragments resolve by explicit fp1, never name@latest")

    # 6. Every window's label carries both split fingerprints, the frozen as-of, world,
    # and evidence class; recompiling a run reproduces its run-config fingerprint.
    settings = _run_settings()
    for window in admitted.windows:
        label = _unwrap(admitted.window_label(window), "window label")
        assert label["registry_as_of"] == stamp
        assert label["in_sample_split_fp1"] == window.in_sample_split.value
        assert label["out_of_sample_split_fp1"] == window.out_of_sample_split.value
        assert label["world"] == "replay"
        assert label["evidence_class"] == "provisional"
        for run in window.runs:
            first_cfg = _unwrap(admitted.compile_run(run, **settings), "compile run")
            again_cfg = _unwrap(admitted.compile_run(run, **settings), "recompile run")
            assert first_cfg.fingerprint == again_cfg.fingerprint
            assert first_cfg.keys["registry_as_of"] == stamp
            assert first_cfg.keys["split_fingerprint"] == run.split_fp1.value
    print(
        "each window label carries both split fingerprints, registry_as_of, world, and evidence "
        "class; recompiling a run reproduces its run-config fingerprint"
    )

    # 4. The window count, spans, and step are UI-editable configurables with no ratified
    # value; the module ships no default. Omit one and the plan refuses.
    assert qmb.WALK_FORWARD_SHIPS_INVENTED_DEFAULT is False
    assert qmb.WALK_FORWARD_SHIPS_OOS_BATTERY is False
    unset = qmb.plan_walk_forward(
        windows, window_count=2, in_sample_span=500, out_of_sample_span=100
    )
    assert is_refusal(unset)  # step unset -> typed refusal, no baked default
    print(
        "window count / spans / step are UI-editable configurables with no ratified value:",
        list(qmb.WALK_FORWARD_CONFIGURABLE_KEYS),
    )

    # 5. The read-time aggregation view over the window runs — never a merged run.
    window_results = [
        _unwrap(
            qmb.WalkForwardWindowResult.try_create(
                index,
                {"sharpe_ratio": _ratio(15 + index)},
                {"sharpe_ratio": _ratio(8 + index)},
            ),
            "window result",
        )
        for index in range(2)
    ]
    aggregation = _unwrap(
        qmb.aggregate_walk_forward(window_results, ["sharpe_ratio"]), "aggregation"
    )
    assert aggregation.is_merged_run is False
    assert aggregation.emits_verdict is False
    payload = aggregation.ct32_data_payload()
    assert payload["is_merged_run"] is False
    assert payload["governance_battery_candidates"] == ["pbo", "cscv"]
    assert payload["governance_battery_has_ratified_thresholds"] is False
    fold = aggregation.metric_named("sharpe_ratio")
    assert fold is not None
    assert fold.window_count == 2
    # A merged run is refused; the view is read-time only.
    assert is_refusal(qmb.refuse_merged_walk_forward_run())
    assert is_refusal(qmb.refuse_walk_forward_battery_threshold("pbo"))
    print(
        "read-time aggregation over the window runs, never a merged run; in-sample / "
        "out-of-sample distributions feed the deferred PBO / CSCV battery (no thresholds):",
        payload["governance_battery_candidates"],
    )

    # Reproducibility: identical window results reproduce the aggregation fingerprint.
    again = _unwrap(
        qmb.aggregate_walk_forward(window_results, ["sharpe_ratio"]), "second aggregation"
    )
    first_fp = _unwrap(aggregation.fingerprint(), "fp1").value
    second_fp = _unwrap(again.fingerprint(), "fp1").value
    assert first_fp == second_fp
    print("re-aggregating the same window results reproduces the view fingerprint bit-for-bit")

    print("walk forward ok")


if __name__ == "__main__":
    main()
