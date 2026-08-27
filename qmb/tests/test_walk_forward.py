"""Story 22.5 — walk-forward as an ordered sequence of split-manifest runs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

from qmb.config import CLOCK_REPLAY, PROVENANCE_RECORDED, STARTING_CAPITAL_KEY
from qmb.doors import api
from qmb.registryread import (
    STALE_EVIDENCE_SEVERITY_KEY,
    AsOfSet,
    DatedPointer,
    PassiveHub,
    RegistryReadPort,
    SupersedesRef,
)
from qmb.results import REGISTRY_AS_OF_KEY, SPLIT_FINGERPRINT_KEY, mint_run_performance_result
from qmb.robustness import (
    AGGREGATION_IS_MERGED_RUN,
    GOVERNANCE_BATTERY_CANDIDATES,
    IN_SAMPLE_ALIAS,
    IN_SAMPLE_RUN_ROLE,
    OOS_BAR_OUTCOME_NOT_YET_RULED,
    OUT_OF_SAMPLE_ALIAS,
    VERDICT_BEARING_BACKTEST_SHIPS,
    WALK_FORWARD_CONFIGURABLE_KEYS,
    WALK_FORWARD_MODE,
    WALK_FORWARD_PROCEDURE,
    WALK_FORWARD_SHIPS_INVENTED_DEFAULT,
    WALK_FORWARD_SHIPS_OOS_BATTERY,
    WINDOW_COUNT_KEY,
    AdmittedWalkForward,
    MetricFoldDistribution,
    WalkForwardAggregation,
    WalkForwardDefinition,
    WalkForwardLabel,
    WalkForwardPlan,
    WalkForwardRun,
    WalkForwardWindow,
    WalkForwardWindowResult,
    admit_walk_forward,
    aggregate_walk_forward,
    fold_oos_bar_outcome,
    plan_walk_forward,
    refuse_merged_walk_forward_run,
    refuse_walk_forward_battery_threshold,
    refuse_window_bar_verdict,
    walk_forward_admission_identity,
    walk_forward_identity,
)
from qmf.core.chrono import CalendarIdentity, Instant, Interval, WriterId
from qmf.core.exact import ExactRational, Money, UnitKind
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
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
_REGISTRY_AS_OF_CLASS = "registry-as-of"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer() -> WriterId:
    return _ok(WriterId.try_create("node-a", "authoring", "config-fragment", "boot-1"))


def _manifest(offset: int, *, world: World = World.REPLAY) -> SplitManifest:
    calendar = _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025b"))
    segments = _ok(
        SplitManifest.default_split_segments([1000 + offset, 2000 + offset, 3000 + offset])
    )
    seal_boundary = _ok(SplitBoundary.try_create(3000 + offset))
    return _ok(
        SplitManifest.try_create(
            calendar_identity=calendar,
            segments=segments,
            seal_boundary=seal_boundary,
            purge_width=0,
            embargo_width=0,
            world=world,
        )
    )


def _window(index: int) -> WalkForwardWindow:
    return _ok(
        WalkForwardWindow.try_create(index, _manifest(index * 100), _manifest(index * 100 + 50))
    )


def _windows(count: int = 2) -> list[WalkForwardWindow]:
    return [_window(index) for index in range(count)]


def _plan(count: int = 2) -> WalkForwardPlan:
    return _ok(
        plan_walk_forward(
            _windows(count),
            config={
                WINDOW_COUNT_KEY: count,
                "qmb_walk_forward_in_sample_span": 500,
                "qmb_walk_forward_out_of_sample_span": 100,
                "qmb_walk_forward_step": 100,
            },
        )
    )


def _ratio(numerator: int, denominator: int = 10) -> ExactRational:
    return _ok(ExactRational.try_create(numerator, denominator, UnitKind.DIMENSIONLESS_RATIO))


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


def _book(q: int = 100) -> BookDefinition:
    return _ok(
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
        RegistrationRecord.try_create(kind, version, parents, payload, _writer(), 0, _instant())
    )


def _port(*records: RegistrationRecord, **as_of_kwargs: object) -> RegistryReadPort:
    as_of = _ok(AsOfSet.try_create(_instant(), records=records, **as_of_kwargs))
    hub = _ok(PassiveHub.try_create((as_of,)))
    return _ok(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY))


def _fixture_port() -> tuple[
    RegistryReadPort, RegistrationRecord, RegistrationRecord, RegistrationRecord
]:
    book_record = _record("book-definition", _book())
    bms_record = _record("bms-definition", _bms())
    bot_record = _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion"})
    pointers = (_ok(DatedPointer.try_create("mean-reversion", bot_record.stable_id, _instant())),)
    port = _port(book_record, bms_record, bot_record, pointers=pointers)
    return port, book_record, bms_record, bot_record


def _admit(count: int = 2) -> AdmittedWalkForward:
    port, book_record, bms_record, bot_record = _fixture_port()
    definition = _ok(
        WalkForwardDefinition.try_create(
            bot=bot_record.stable_id,
            book=book_record.stable_id,
            bms=bms_record.stable_id,
            plan=_plan(count),
        )
    )
    return _ok(admit_walk_forward(definition, port, _writer()))


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


# --- AC1: a sequence of split manifests; each window two first-class runs -----


def test_a_walk_forward_is_a_sequence_of_split_manifest_pairs() -> None:
    window = _window(0)
    in_manifest = _manifest(0)
    out_manifest = _manifest(50)
    assert window.in_sample_split == in_manifest.fingerprint
    assert window.out_of_sample_split == out_manifest.fingerprint
    assert window.world is World.REPLAY
    # train/test are display aliases for the two manifests, never in identity.
    assert window.display_aliases() == {
        IN_SAMPLE_ALIAS: in_manifest.fingerprint.value,
        OUT_OF_SAMPLE_ALIAS: out_manifest.fingerprint.value,
    }
    assert _ok(window.split_for("train")) == window.in_sample_split
    assert _ok(window.split_for("test")) == window.out_of_sample_split
    identity = window.fp1_identity()
    assert IN_SAMPLE_ALIAS not in identity and "aliases" not in identity
    assert identity["in_sample_split_fp1"] == window.in_sample_split.value
    assert identity["out_of_sample_split_fp1"] == window.out_of_sample_split.value


def test_each_window_materializes_two_first_class_runs() -> None:
    window = _window(0)
    assert isinstance(window.in_sample_run, WalkForwardRun)
    assert window.in_sample_run.contributes_to_objective is True
    assert window.out_of_sample_run.contributes_to_objective is False
    assert window.in_sample_run.split_fp1 == window.in_sample_split
    assert window.out_of_sample_run.split_fp1 == window.out_of_sample_split
    assert window.runs == (window.in_sample_run, window.out_of_sample_run)
    # The two runs have distinct identities (different split + objective role).
    assert window.in_sample_run.fp1_identity() != window.out_of_sample_run.fp1_identity()
    # The display alias never enters run identity.
    assert "train" not in window.in_sample_run.fp1_identity()


def test_a_window_with_one_manifest_for_both_splits_is_refused() -> None:
    same = _manifest(0)
    refused = WalkForwardWindow.try_create(0, same, same)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "out_of_sample_split"


def test_a_simulated_split_manifest_window_is_a_policy_rejection() -> None:
    refused = WalkForwardWindow.try_create(0, _manifest(0, world=World.SIMULATED), _manifest(50))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_the_plan_is_an_ordered_contiguous_window_sequence() -> None:
    plan = _plan(2)
    assert isinstance(plan, WalkForwardPlan)
    assert plan.window_count == 2
    assert len(plan.windows) == 2
    assert len(plan.runs) == 4
    # A gap or out-of-order index in the sequence is refused.
    scrambled = plan_walk_forward(
        [_window(0), _window(2)], window_count=2, in_sample_span=1, out_of_sample_span=1, step=1
    )
    assert is_refusal(scrambled)
    assert scrambled.context["field"] == "windows"


# --- AC2: B-4 ledger roles + the OOS read-time fold --------------------------


def test_the_in_sample_run_is_role_trial_and_never_a_bar_verdict() -> None:
    window = _window(0)
    assert window.in_sample_run.role == IN_SAMPLE_RUN_ROLE == "trial"
    assert window.in_sample_run.is_in_sample is True
    assert qmb.WINDOW_WRITES_BAR_VERDICT is False
    refused = refuse_window_bar_verdict("bar-pass")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["oos_bar_outcome"] == OOS_BAR_OUTCOME_NOT_YET_RULED


def test_the_oos_bar_outcome_is_a_read_time_fold_returning_not_yet_ruled() -> None:
    # No verdict-bearing backtest ships while GAP-0048 is open (SC-06), so the OOS bar
    # outcome is a read-time fold that returns not-yet-ruled until GAP-0048/0049 close.
    assert VERDICT_BEARING_BACKTEST_SHIPS is False
    assert fold_oos_bar_outcome() == OOS_BAR_OUTCOME_NOT_YET_RULED == "not-yet-ruled"
    assert fold_oos_bar_outcome(_window(0)) == OOS_BAR_OUTCOME_NOT_YET_RULED
    # The token matches the B-4 ledger canonical-assignment fold vocabulary.
    assert OOS_BAR_OUTCOME_NOT_YET_RULED == qmb.CANONICAL_ASSIGNMENT_NOT_YET_RULED


# --- AC3: SC-11 batch admission over one frozen registry as-of ----------------


def test_admission_resolves_one_as_of_and_freezes_it_for_every_window() -> None:
    port, book_record, bms_record, bot_record = _fixture_port()
    as_of = port.bound
    definition = _ok(
        WalkForwardDefinition.try_create(
            bot=bot_record.stable_id,
            book=book_record.stable_id,
            bms=bms_record.stable_id,
            plan=_plan(2),
        )
    )
    admitted = _ok(admit_walk_forward(definition, port, _writer()))
    assert isinstance(admitted, AdmittedWalkForward)
    assert admitted.port.frozen is True
    assert admitted.registry_as_of == as_of.registry_as_of
    assert admitted.set_fingerprint == as_of.fingerprint
    assert admitted.window_count == 2
    assert admitted.run_count == 4


def test_the_one_as_of_is_stamped_into_the_batch_and_every_window_label() -> None:
    admitted = _admit(2)
    label = admitted.label
    assert isinstance(label, WalkForwardLabel)
    assert is_ok(label.fingerprint())
    stamp = admitted.registry_as_of_stamp()
    assert stamp == {
        "value_ns": admitted.registry_as_of.value_ns,
        "fingerprint": admitted.set_fingerprint.value,
    }
    for window in admitted.windows:
        window_label = _ok(admitted.window_label(window))
        assert window_label["registry_as_of"] == stamp
        assert window_label["walk_forward_id"] == label.walk_forward_id.value
        assert window_label["in_sample_split_fp1"] == window.in_sample_split.value
        assert window_label["out_of_sample_split_fp1"] == window.out_of_sample_split.value


def test_after_admission_fragments_resolve_by_fp1_never_name_at_latest() -> None:
    admitted = _admit(2)
    assert is_refusal(admitted.port.resolve("mean-reversion"))
    at_latest = admitted.port.resolve("scalping@latest")
    assert is_refusal(at_latest)
    assert at_latest.category is RefusalCategory.INVALID_INPUT
    # Every window run resolves the identical frozen bot/Book/BMS fp1.
    settings = _run_settings()
    configs = [
        _ok(admitted.compile_run(run, **settings))
        for window in admitted.windows
        for run in window.runs
    ]
    assert {config.book_fp1 for config in configs} == {admitted.label.book_fp1}
    assert {config.bms_fp1 for config in configs} == {admitted.label.bms_fp1}
    assert {config.bot_fp1 for config in configs} == {admitted.label.bot_fp1}


def test_a_stale_context_reference_at_admission_is_an_ad11_refusal() -> None:
    book_v1 = _record("book-definition", _book(q=100))
    book_v2 = _record("book-definition", _book(q=200))
    bms_record = _record("bms-definition", _bms())
    bot_record = _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion"})
    supersedes = (_ok(SupersedesRef.try_create(book_v2.stable_id, book_v1.stable_id)),)
    port = _port(book_v1, book_v2, bms_record, bot_record, supersedes=supersedes)
    definition = _ok(
        WalkForwardDefinition.try_create(
            bot=bot_record.stable_id,
            book=book_v1.stable_id,
            bms=bms_record.stable_id,
            plan=_plan(1),
        )
    )
    refused = admit_walk_forward(definition, port, _writer())
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STALE_EVIDENCE
    assert refused.context["severity"] == _SEVERITY
    assert refused.context["severity_key"] == STALE_EVIDENCE_SEVERITY_KEY


def test_a_fresher_as_of_mid_batch_never_changes_an_in_flight_window() -> None:
    admitted = _admit(2)
    settings = _run_settings()
    run = admitted.windows[0].in_sample_run
    first = _ok(admitted.compile_run(run, **settings))
    again = _ok(admitted.compile_run(run, **settings))
    # A frozen port yields the byte-identical run id on recompilation (SC-11, B-15).
    assert first.fingerprint == again.fingerprint


# --- AC4: window count / spans / step are deferred configurables --------------


def test_the_configurables_carry_no_ratified_value_and_ship_no_default() -> None:
    assert WALK_FORWARD_SHIPS_INVENTED_DEFAULT is False
    assert WALK_FORWARD_SHIPS_OOS_BATTERY is False
    assert WALK_FORWARD_CONFIGURABLE_KEYS == (
        "qmb_walk_forward_window_count",
        "qmb_walk_forward_in_sample_span",
        "qmb_walk_forward_out_of_sample_span",
        "qmb_walk_forward_step",
    )
    # Any unset configurable is a typed refusal — no silently-applied default.
    unset = plan_walk_forward(
        _windows(2), window_count=2, in_sample_span=500, out_of_sample_span=100
    )
    assert is_refusal(unset)
    assert unset.category is RefusalCategory.INVALID_INPUT
    assert unset.context["field"] == "qmb_walk_forward_step"


def test_a_window_count_that_disagrees_with_the_sequence_is_refused() -> None:
    refused = plan_walk_forward(
        _windows(2), window_count=3, in_sample_span=1, out_of_sample_span=1, step=1
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "window_count"


def test_the_configurables_resolve_from_a_run_config_mapping() -> None:
    plan = _plan(2)
    assert plan.in_sample_span == 500
    assert plan.out_of_sample_span == 100
    assert plan.step == 100
    assert plan.window_count == 2


# --- AC5: read-time aggregation over the window runs, never a merged run -------


def _window_results() -> list[WalkForwardWindowResult]:
    return [
        _ok(
            WalkForwardWindowResult.try_create(
                index,
                {"sharpe_ratio": _ratio(15 + index)},
                {"sharpe_ratio": _ratio(8 + index)},
            )
        )
        for index in range(2)
    ]


def test_the_aggregation_is_a_read_time_view_never_a_merged_run() -> None:
    aggregation = _ok(aggregate_walk_forward(_window_results(), ["sharpe_ratio"]))
    assert isinstance(aggregation, WalkForwardAggregation)
    assert aggregation.is_merged_run is AGGREGATION_IS_MERGED_RUN is False
    assert aggregation.emits_verdict is False
    assert aggregation.window_count == 2
    fold = aggregation.metric_named("sharpe_ratio")
    assert isinstance(fold, MetricFoldDistribution)
    assert fold.window_count == 2
    # Per-window in-sample and out-of-sample values are collected in window order.
    assert len(fold.in_sample_distribution.values) == 2
    assert len(fold.out_of_sample_distribution.values) == 2
    assert "values" in fold.in_sample_distribution.as_data()
    # Minting a merged walk-forward run is refused.
    merged = refuse_merged_walk_forward_run()
    assert is_refusal(merged)
    assert merged.category is RefusalCategory.POLICY_REJECTION


def test_the_aggregation_feeds_the_deferred_governance_battery_with_no_thresholds() -> None:
    aggregation = _ok(aggregate_walk_forward(_window_results(), ["sharpe_ratio"]))
    payload = aggregation.ct32_data_payload()
    assert payload["is_merged_run"] is False
    assert payload["emits_verdict"] is False
    assert payload["governance_battery_candidates"] == list(GOVERNANCE_BATTERY_CANDIDATES)
    assert GOVERNANCE_BATTERY_CANDIDATES == ("pbo", "cscv")
    assert payload["governance_battery_has_ratified_thresholds"] is False
    # Applying a ratified WF/OOS/PBO/CSCV threshold is refused (deferred, SC-07).
    refused = refuse_walk_forward_battery_threshold("pbo")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_the_aggregation_reproduces_its_fingerprint_bit_for_bit() -> None:
    results = _window_results()
    first = _ok(aggregate_walk_forward(results, ["sharpe_ratio"]))
    again = _ok(aggregate_walk_forward(results, ["sharpe_ratio"]))
    assert _ok(first.fingerprint()).value == _ok(again.fingerprint()).value


def test_a_metric_missing_from_a_window_fold_is_refused_not_dropped() -> None:
    results = [
        _ok(
            WalkForwardWindowResult.try_create(
                0, {"sharpe_ratio": _ratio(15)}, {"sharpe_ratio": _ratio(8)}
            )
        ),
        _ok(WalkForwardWindowResult.try_create(1, {"sharpe_ratio": _ratio(16)}, {})),
    ]
    refused = aggregate_walk_forward(results, ["sharpe_ratio"])
    assert is_refusal(refused)
    assert refused.context["field"] == "metric"


def test_a_raw_binary_float_metric_value_is_refused() -> None:
    refused = WalkForwardWindowResult.try_create(0, {"sharpe_ratio": 1.5}, {"sharpe_ratio": 0.8})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


# --- AC6: reproducibility + the window label's split fingerprints -------------


def test_recompiling_a_window_run_reproduces_its_run_config_fingerprint() -> None:
    admitted = _admit(2)
    settings = _run_settings()
    for window in admitted.windows:
        for run in window.runs:
            first = _ok(admitted.compile_run(run, **settings))
            again = _ok(admitted.compile_run(run, **settings))
            assert first.fingerprint == again.fingerprint
            assert first.keys[REGISTRY_AS_OF_KEY] == admitted.registry_as_of_stamp()
            assert first.keys[SPLIT_FINGERPRINT_KEY] == run.split_fp1.value


def test_the_window_label_carries_split_fingerprints_registry_as_of_world_and_class() -> None:
    admitted = _admit(2)
    for window in admitted.windows:
        label = _ok(admitted.window_label(window))
        assert label["in_sample_split_fp1"] == window.in_sample_split.value
        assert label["out_of_sample_split_fp1"] == window.out_of_sample_split.value
        assert label["registry_as_of"] == admitted.registry_as_of_stamp()
        assert label["world"] == "replay"
        assert label["evidence_class"] == "provisional"


def test_the_frozen_as_of_and_split_are_verbatim_in_the_window_ct32_label() -> None:
    admitted = _admit(1)
    settings = _run_settings()
    run = admitted.windows[0].in_sample_run
    config = _ok(admitted.compile_run(run, **settings))
    registry_input = _ok(
        fingerprint(
            {
                "class": _REGISTRY_AS_OF_CLASS,
                "registry_as_of": admitted.registry_as_of.fp1_identity(),
                "fingerprint": admitted.set_fingerprint.value,
            }
        )
    )
    result = _ok(
        mint_run_performance_result(
            config,
            evidence_range=_ok(Interval.try_create(_instant(_NS), _instant(_NS + 1_000))),
            stream_order=("EURUSD",),
            slice_count=1,
            filled_count=0,
            resting_count=0,
            data_points_processed=1,
            outcome_identity={"done": True},
        )
    )
    assert registry_input in result.result_label.input_fingerprints
    # The window's split-manifest fingerprint rides in the CT-32 input fingerprints too.
    assert run.split_fp1 in result.result_label.input_fingerprints


def test_a_caller_may_not_declare_registry_as_of_or_split_fingerprint() -> None:
    admitted = _admit(1)
    run = admitted.windows[0].in_sample_run
    settings = _run_settings()
    refused_registry = admitted.compile_run(
        run,
        invocation_flags={STARTING_CAPITAL_KEY: _SEED, REGISTRY_AS_OF_KEY: {"value_ns": 1}},
        workspace_defaults=settings["workspace_defaults"],
    )
    assert is_refusal(refused_registry)
    assert refused_registry.context["field"] == "invocation_flags"
    refused_split = admitted.compile_run(
        run,
        invocation_flags={STARTING_CAPITAL_KEY: _SEED},
        workspace_defaults={
            **cast("dict[str, object]", settings["workspace_defaults"]),
            SPLIT_FINGERPRINT_KEY: "x",
        },
    )
    assert is_refusal(refused_split)
    assert refused_split.context["field"] == "workspace_defaults"


# --- guards, foreign members, and the pure-function discipline ---------------


def test_compile_and_label_refuse_a_foreign_window_or_run() -> None:
    admitted = _admit(2)
    stranger = _window(9)
    assert is_refusal(admitted.window_label(stranger))
    assert is_refusal(admitted.compile_run(stranger.in_sample_run, **_run_settings()))
    assert is_refusal(admitted.window_label(object()))
    assert is_refusal(admitted.compile_run(object(), **_run_settings()))


def test_admission_refuses_a_non_port_a_non_writer_and_a_malformed_definition() -> None:
    port, book_record, bms_record, bot_record = _fixture_port()
    definition = _ok(
        WalkForwardDefinition.try_create(
            bot=bot_record.stable_id,
            book=book_record.stable_id,
            bms=bms_record.stable_id,
            plan=_plan(1),
        )
    )
    bad_port = admit_walk_forward(definition, object(), _writer())
    assert is_refusal(bad_port)
    assert bad_port.context["field"] == "port"
    bad_writer = admit_walk_forward(definition, port, "node-a")
    assert is_refusal(bad_writer)
    assert bad_writer.context["field"] == "writer"
    bad = admit_walk_forward(["not", "a", "definition"], port, _writer())
    assert is_refusal(bad)
    assert bad.context["field"] == "definition"


# --- surface: identity excludes SemVer; both doors are identity-equal ---------


def test_walk_forward_identity_excludes_package_semver() -> None:
    identity = walk_forward_identity()
    assert identity["procedure"] == WALK_FORWARD_PROCEDURE == "walk-forward"
    assert identity["mode"] == WALK_FORWARD_MODE
    assert identity["aggregation_is_merged_run"] is False
    assert qmb.__version__ not in identity.values()
    assert is_ok(fingerprint(identity))
    admission = walk_forward_admission_identity()
    assert admission["admission_single_as_of"] is True
    assert admission["admission_has_second_cache"] is False
    assert qmb.__version__ not in admission.values()


def test_walk_forward_surface_is_on_both_doors_identity_equal() -> None:
    assert api.admit_walk_forward is qmb.admit_walk_forward
    assert api.WalkForwardWindow is qmb.WalkForwardWindow
    assert api.aggregate_walk_forward is qmb.aggregate_walk_forward
    assert api.fold_oos_bar_outcome is qmb.fold_oos_bar_outcome
    assert api.WALK_FORWARD_PROCEDURE == qmb.WALK_FORWARD_PROCEDURE
    for name in (
        "admit_walk_forward",
        "plan_walk_forward",
        "aggregate_walk_forward",
        "fold_oos_bar_outcome",
        "WalkForwardWindow",
        "WalkForwardWindowResult",
        "AdmittedWalkForward",
        "WALK_FORWARD_PROCEDURE",
        "OOS_BAR_OUTCOME_NOT_YET_RULED",
    ):
        assert name in api.__all__
        assert name in qmb.__all__


def test_walk_forward_is_the_fourth_ratified_ladder_procedure() -> None:
    assert WALK_FORWARD_PROCEDURE in qmb.ROBUSTNESS_PROCEDURES
    assert WALK_FORWARD_PROCEDURE in qmb.PROCEDURES
    # The rung is a pure library function that gates no live money and claims no edge.
    assert is_refusal(qmb.refuse_edge_claim(WALK_FORWARD_PROCEDURE))
    assert is_refusal(qmb.refuse_live_money_gate(WALK_FORWARD_PROCEDURE))
    assert is_ok(qmb.procedure_contract(WALK_FORWARD_PROCEDURE))
