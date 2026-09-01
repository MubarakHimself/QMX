"""Story 26.11 / QMX-F067 — runtime risk population, windows, shakedown, cardinality."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    Account,
    AccountRole,
    Duration,
    Instant,
    Instrument,
    Money,
    RefusalCategory,
    VenueId,
    World,
    fingerprint,
)
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.risk.control_rank import ControlActionKind, ControlRankRow, ControlRankTable
from qmf.risk.control_window import AnchorSide, WindowKind
from qmn.host import (
    LAYER1_CHECKS,
    MISMATCH_REFUSES_BEFORE_SEAL,
    RISK_POPULATION_SURFACE,
    SHAKEDOWN_EXERCISES,
    SHAKEDOWN_FOR_HUMAN_SIGNATURE,
    SHAKEDOWN_IS_PERFORMANCE_PROOF,
    SHAKEDOWN_SURFACE,
    CapabilityRecord,
    CompositionFingerprintInputs,
    InMemoryBootAttemptSink,
    PairedTargetRecord,
    PopulationBindingRecord,
    PopulationBmsRecord,
    PopulationBookRecord,
    PreflightFacts,
    PriorityRecord,
    RuntimeRiskGraph,
    ScopeRecord,
    SeatRecord,
    ShakedownPlan,
    WindowRecord,
    admit_runtime_risk_population,
    assemble_shakedown_signature_page,
    refuse_invented_soak_or_ksa_number,
    refuse_shakedown_as_performance_proof,
    run_boot_ceremony,
    run_demo_shakedown,
)
from qmn.protection.windows import require_resolved_window_settings
from qmn.venue import Command

T = TypeVar("T")

_QMN_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn"
_HOST_SRC = _QMN_SRC / "host"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _fp(label: str):
    return _ok(fingerprint({"class": "cite", "label": label}))


def _venue() -> VenueId:
    return _ok(VenueId.try_create("venue-a"))


def _instant(ns: int = 1_700_000_000_000_000_000) -> Instant:
    return _ok(Instant.try_create(ns))


def _duration(ns: int = 60_000_000_000) -> Duration:
    return _ok(Duration.try_create(ns))


def _money(value: int = 100_000) -> Money:
    return _ok(Money.try_create(value, "USD", 2))


def _rank_table() -> ControlRankTable:
    rows = [
        _ok(ControlRankRow.try_create(ControlActionKind.SUSPEND_NEW, 0)),
        _ok(ControlRankRow.try_create(ControlActionKind.FLATTEN, 1)),
        _ok(ControlRankRow.try_create(ControlActionKind.DRAIN, 2)),
        _ok(ControlRankRow.try_create(ControlActionKind.RESUME, 3)),
    ]
    return _ok(ControlRankTable.try_create(rows))


def _partial_rank_table() -> ControlRankTable:
    rows = [
        _ok(ControlRankRow.try_create(ControlActionKind.SUSPEND_NEW, 0)),
        _ok(ControlRankRow.try_create(ControlActionKind.FLATTEN, 1)),
        _ok(ControlRankRow.try_create(ControlActionKind.DRAIN, 2)),
    ]
    return _ok(ControlRankTable.try_create(rows))


def _binding(
    *,
    binding_id: str,
    book_id: str,
    instruments: frozenset[str],
    bms_id: str = "bms-1",
    account_id: str = "acct-1",
    role: AccountRole = AccountRole.LIVE,
) -> PopulationBindingRecord:
    return _ok(
        PopulationBindingRecord.try_create(
            binding_id=binding_id,
            book_instance_id=book_id,
            bms_instance_id=bms_id,
            venue_id="venue-a",
            account_id=account_id,
            role=role,
            world=World.LIVE,
            environment="live",
            position_model="netting",
            instruments=instruments,
            attribution_instruments=instruments,
        )
    )


def _windows_for(binding_id: str) -> tuple[WindowRecord, ...]:
    return tuple(
        _ok(
            WindowRecord.try_create(
                window_id=f"{binding_id}-{kind.value}",
                kind=kind.value,
                binding_id=binding_id,
            )
        )
        for kind in WindowKind
    )


def _valid_graph() -> RuntimeRiskGraph:
    return _ok(
        RuntimeRiskGraph.try_create(
            bms=(
                _ok(
                    PopulationBmsRecord.try_create(
                        bms_instance_id="bms-1",
                        venue_id="venue-a",
                        account_id="acct-1",
                        definition_fp1="bms-def-1",
                    )
                ),
            ),
            books=(
                _ok(
                    PopulationBookRecord.try_create(
                        book_instance_id="book-1",
                        bms_instance_id="bms-1",
                        definition_fp1="book-def-1",
                    )
                ),
                _ok(
                    PopulationBookRecord.try_create(
                        book_instance_id="book-2",
                        bms_instance_id="bms-1",
                        definition_fp1="book-def-2",
                    )
                ),
            ),
            bindings=(
                _binding(
                    binding_id="bind-1",
                    book_id="book-1",
                    instruments=frozenset({"EURUSD"}),
                ),
                _binding(
                    binding_id="bind-2",
                    book_id="book-2",
                    instruments=frozenset({"GBPUSD"}),
                ),
            ),
            seats=(
                _ok(
                    SeatRecord.try_create(
                        seat_id="seat-1",
                        bot_id="bot-1",
                        book_instance_id="book-1",
                        binding_id="bind-1",
                    )
                ),
                _ok(
                    SeatRecord.try_create(
                        seat_id="seat-2",
                        bot_id="bot-2",
                        book_instance_id="book-2",
                        binding_id="bind-2",
                    )
                ),
            ),
            paired_targets=(
                _ok(
                    PairedTargetRecord.try_create(
                        live_binding_id="bind-1",
                        paper_account_id="acct-demo",
                        paper_role=AccountRole.DEMO,
                        paper_bms_instance_id="bms-paper-1",
                    )
                ),
            ),
            windows=_windows_for("bind-1") + _windows_for("bind-2"),
            priorities=(
                _ok(
                    PriorityRecord.try_create(
                        venue_id="venue-a",
                        account_id="acct-1",
                        rank_table=_rank_table(),
                    )
                ),
            ),
            capabilities=(
                _ok(
                    CapabilityRecord.try_create(
                        binding_id="bind-1",
                        required=frozenset({"protective_stop"}),
                        declared=frozenset({"protective_stop", "netting"}),
                    )
                ),
                _ok(
                    CapabilityRecord.try_create(
                        binding_id="bind-2",
                        required=frozenset({"protective_stop"}),
                        declared=frozenset({"protective_stop", "netting"}),
                    )
                ),
            ),
            scopes=(_ok(ScopeRecord.try_create(kind="global")),),
        )
    )


def _inputs() -> CompositionFingerprintInputs:
    return CompositionFingerprintInputs(
        config_fp=_fp("config-risk"),
        distribution_identities={
            "qmf": "lockstep",
            "qmb": "0.1.0",
            "qml": "0.1.0",
            "qmn": "0.1.0",
        },
        extension_identities={"qmf-calendar-forex": "1.0.0"},
        proto_release_tag="proto-1",
        tzdata_version="2026a",
        adapter_capability_fps=(_fp("cap-ctrader"),),
        registry_as_of_fp=_fp("as-of-1"),
        calendar_code_identities={
            "market_hours_calendar": "mh-code-1",
            "day_boundary_calendar": "db-code-1",
            "news_calendar": "news-code-1",
        },
        os_cpu_class="linux-x86_64",
    )


def _window_settings():
    return _ok(
        require_resolved_window_settings(
            news_blackout_before=_duration(),
            news_blackout_after=_duration(),
            daily_dead_zone_width=_duration(),
            session_handover_buffer_width=_duration(),
            session_handover_buffer_anchor=AnchorSide.PRE_CLOSE,
            news_calendar_max_staleness=_duration(),
        )
    )


def _demo_account() -> Account:
    return _ok(Account.try_create("acct-demo", _venue(), AccountRole.DEMO))


def _live_account() -> Account:
    return _ok(Account.try_create("acct-live", _venue(), AccountRole.LIVE))


def _cancel(account: Account) -> Command:
    return _ok(
        Command.cancel_order(_venue(), account, "session-shakedown", 1, "ord-1")
    )


def _shakedown_plan(**overrides: object) -> ShakedownPlan:
    kwargs: dict[str, object] = {
        "binding_identity": "bind-demo-1",
        "shakedown_role": AccountRole.DEMO,
        "live_path_rung_baseline_present": True,
        "sensor_baselines_present": True,
        "window_settings": _window_settings(),
        "ledger_binding_epoch": _fp("ledger-demo"),
        "ledger_seed": _money(50_000),
        "ledger_recorded_at": _instant(),
        "kill_line_capital_floor": _money(10_000),
        "kill_line_equity": _money(40_000),
        "kill_line_evaluated_at": _instant(),
        "sqs_venue": _venue(),
        "sqs_environment": "demo",
        "sqs_instrument": _ok(Instrument.try_create(_venue(), "EURUSD")),
        "callback_deadline": _duration(5_000_000),
        "memory_ceiling_bytes": 8_388_608,
        "dry_run_command": _cancel(_demo_account()),
        "protective_stop_forms": {"market": "entry-relative"},
    }
    kwargs.update(overrides)
    return _ok(ShakedownPlan.try_create(**kwargs))


# --- Layer-1 population -----------------------------------------------------


def test_surface_markers_and_closed_check_list() -> None:
    assert RISK_POPULATION_SURFACE == "qmn.host.risk_population"
    assert SHAKEDOWN_SURFACE == "qmn.host.shakedown"
    assert MISMATCH_REFUSES_BEFORE_SEAL is True
    assert SHAKEDOWN_FOR_HUMAN_SIGNATURE is True
    assert SHAKEDOWN_IS_PERFORMANCE_PROOF is False
    assert LAYER1_CHECKS == (
        "cardinalities",
        "referential_integrity",
        "total_unique_rank",
        "declared_scopes",
        "netting_partitions",
        "one_bms_per_account_many_books",
        "one_book_per_bot",
        "one_active_paper_target",
    )
    assert "required_windows" in SHAKEDOWN_EXERCISES
    assert "command_path_dry_run" in SHAKEDOWN_EXERCISES


def test_assembled_valid_graph_passes_every_check_together() -> None:
    proof = _ok(admit_runtime_risk_population(_valid_graph()))
    assert proof.checks_run == LAYER1_CHECKS
    assert proof.binding_ids == ("bind-1", "bind-2")
    assert set(proof.book_ids) == {"book-1", "book-2"}
    assert proof.bms_ids == ("bms-1",)
    assert set(proof.bot_ids) == {"bot-1", "bot-2"}
    assert proof.stream_keys == ("venue-a::acct-1",)


def test_dangling_seat_is_referential_integrity_refusal() -> None:
    base = _valid_graph()
    graph = replace(
        base,
        seats=(
            *base.seats,
            _ok(
                SeatRecord.try_create(
                    seat_id="seat-x",
                    bot_id="bot-x",
                    book_instance_id="book-1",
                    binding_id="missing-bind",
                )
            ),
        ),
    )
    refused = _refusal(admit_runtime_risk_population(graph))
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refused.context["failure_id"] == (
        "compose.risk_population.referential_integrity"
    )


def test_incomplete_rank_table_refuses_total_unique_rank() -> None:
    graph = replace(
        _valid_graph(),
        priorities=(
            PriorityRecord(
                venue_id="venue-a",
                account_id="acct-1",
                rank_table=_partial_rank_table(),
            ),
        ),
    )
    refused = _refusal(admit_runtime_risk_population(graph))
    assert refused.context["failure_id"] == "compose.risk_population.total_unique_rank"
    assert "missing" in refused.context or "rank" in str(refused.context["reason"])


def test_undeclared_stream_scope_refuses() -> None:
    graph = replace(
        _valid_graph(),
        scopes=(
            _ok(
                ScopeRecord.try_create(
                    kind="stream",
                    venue_id="venue-a",
                    account_id="unknown-acct",
                )
            ),
        ),
    )
    refused = _refusal(admit_runtime_risk_population(graph))
    assert refused.context["failure_id"] == "compose.risk_population.declared_scopes"


def test_overlapping_netting_without_shared_flatten_refuses() -> None:
    graph = replace(
        _valid_graph(),
        bindings=(
            _binding(
                binding_id="bind-1",
                book_id="book-1",
                instruments=frozenset({"EURUSD"}),
            ),
            _binding(
                binding_id="bind-2",
                book_id="book-2",
                instruments=frozenset({"EURUSD", "GBPUSD"}),
            ),
        ),
    )
    refused = _refusal(admit_runtime_risk_population(graph))
    assert refused.context["failure_id"] == "compose.risk_population.netting_partitions"


def test_second_bms_on_same_account_refuses() -> None:
    base = _valid_graph()
    graph = replace(
        base,
        bms=(
            *base.bms,
            _ok(
                PopulationBmsRecord.try_create(
                    bms_instance_id="bms-2",
                    venue_id="venue-a",
                    account_id="acct-1",
                    definition_fp1="bms-def-2",
                )
            ),
        ),
    )
    refused = _refusal(admit_runtime_risk_population(graph))
    assert refused.context["failure_id"] == "compose.risk_population.one_bms_per_account"


def test_one_bot_on_two_books_refuses_assembled_population() -> None:
    base = _valid_graph()
    graph = replace(
        base,
        seats=(
            *base.seats,
            _ok(
                SeatRecord.try_create(
                    seat_id="seat-3",
                    bot_id="bot-1",
                    book_instance_id="book-2",
                    binding_id="bind-2",
                )
            ),
        ),
    )
    refused = _refusal(admit_runtime_risk_population(graph))
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["failure_id"] == "compose.risk_population.one_book_per_bot"
    assert refused.context["bot_id"] == "bot-1"


def test_two_paper_targets_for_one_binding_refuse() -> None:
    base = _valid_graph()
    graph = replace(
        base,
        paired_targets=(
            *base.paired_targets,
            _ok(
                PairedTargetRecord.try_create(
                    live_binding_id="bind-1",
                    paper_account_id="acct-demo-2",
                    paper_role=AccountRole.DEMO,
                    paper_bms_instance_id="bms-paper-2",
                )
            ),
        ),
    )
    refused = _refusal(admit_runtime_risk_population(graph))
    assert refused.context["failure_id"] == (
        "compose.risk_population.one_active_paper_target"
    )


def test_compose_refuses_population_mismatch_before_seal() -> None:
    sink = InMemoryBootAttemptSink()
    base = _valid_graph()
    bad = replace(
        base,
        seats=(
            *base.seats,
            _ok(
                SeatRecord.try_create(
                    seat_id="seat-3",
                    bot_id="bot-1",
                    book_instance_id="book-2",
                    binding_id="bind-2",
                )
            ),
        ),
    )
    outcome = _ok(
        run_boot_ceremony(
            boot_epoch_id="boot-risk-1",
            machine="vps-a",
            composition_inputs=_inputs(),
            writer_streams=(
                ("command", "venue-a::acct-1"),
                ("adapter", "venue-a::acct-1"),
                ("risk", "risk:venue-a::acct-1"),
            ),
            risk_population=bad,
            boot_attempt_sink=sink,
            preflight=PreflightFacts(
                required_credential_refs=("venue-token",),
                credential_is_set={"venue-token": True},
            ),
        )
    )
    assert outcome.stand_down_alive is True
    assert outcome.sealed is False
    assert outcome.ready is False
    assert outcome.failure_id == "compose.risk_population.one_book_per_bot"
    assert sink.records[0].stage == "compose"


def test_compose_seals_when_assembled_graph_passes() -> None:
    sink = InMemoryBootAttemptSink()
    outcome = _ok(
        run_boot_ceremony(
            boot_epoch_id="boot-risk-ok",
            machine="vps-a",
            composition_inputs=_inputs(),
            writer_streams=(
                ("command", "venue-a::acct-1"),
                ("adapter", "venue-a::acct-1"),
                ("risk", "risk:venue-a::acct-1"),
            ),
            risk_population=_valid_graph(),
            boot_attempt_sink=sink,
            preflight=PreflightFacts(
                required_credential_refs=("venue-token",),
                credential_is_set={"venue-token": True},
            ),
        )
    )
    assert outcome.sealed is True
    assert outcome.ready is True
    assert outcome.failure_id is None
    assert sink.records[0].stage == "seal"


# --- Layer-2 shakedown ------------------------------------------------------


def test_demo_shakedown_exercises_required_machinery_without_live_binding() -> None:
    evidence = _ok(run_demo_shakedown(_shakedown_plan()))
    assert evidence.exercises_run == SHAKEDOWN_EXERCISES
    assert evidence.shakedown_role is AccountRole.DEMO
    assert evidence.for_human_signature is True
    assert evidence.is_performance_proof is False
    assert evidence.live_binding_used is False
    assert evidence.command_path_submitted_live is False
    assert evidence.invented_ksa_or_soak_numbers is False
    assert evidence.sqs_live_conditioned is False
    assert evidence.venue_client_kind == "conformance"
    assert evidence.layer2.shakedown_role is AccountRole.DEMO
    assert evidence.layer2.binding_identity == "bind-demo-1"


def test_live_binding_shakedown_is_policy_rejection() -> None:
    refused = _refusal(
        run_demo_shakedown(_shakedown_plan(shakedown_role=AccountRole.LIVE))
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "shakedown_role"


def test_shakedown_evidence_is_not_performance_proof() -> None:
    refused = _refusal(
        run_demo_shakedown(_shakedown_plan(treat_as_performance_proof=True))
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION
    evidence = _ok(run_demo_shakedown(_shakedown_plan()))
    page = _ok(
        assemble_shakedown_signature_page(
            layer1_checks_run=LAYER1_CHECKS,
            shakedown=evidence,
        )
    )
    assert page.for_human_signature is True
    assert page.is_performance_proof is False
    assert refuse_shakedown_as_performance_proof().context["for_human_signature"] is True


def test_shakedown_refuses_invented_soak_or_ksa_numbers() -> None:
    soak = _refusal(run_demo_shakedown(_shakedown_plan(soak_duration=604_800)))
    assert soak.context["field"] == "invented-value"
    ksa = _refusal(run_demo_shakedown(_shakedown_plan(ksa_numeric_value=50)))
    assert ksa.context["field"] == "invented-value"
    minutes = _refusal(
        run_demo_shakedown(_shakedown_plan(invented_window_minutes=15))
    )
    assert minutes.context["field"] == "window_bounds"
    assert is_refusal(refuse_invented_soak_or_ksa_number())


def test_demo_sqs_baseline_cannot_claim_live_conditioning() -> None:
    refused = _refusal(
        run_demo_shakedown(_shakedown_plan(claim_sqs_live_conditioned=True))
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION
    live_env = _refusal(run_demo_shakedown(_shakedown_plan(sqs_environment="live")))
    assert live_env.category is RefusalCategory.POLICY_REJECTION


def test_command_path_dry_run_refuses_live_account() -> None:
    refused = _refusal(
        run_demo_shakedown(
            _shakedown_plan(dry_run_command=_cancel(_live_account()))
        )
    )
    assert refused.context["field"] == "dry_run_command"


def test_no_invented_soak_or_ksa_literals_in_admission_modules() -> None:
    banned_names = {
        "SOAK_DAYS",
        "SOAK_DURATION",
        "KSA_DEFAULT",
        "KSA_MATRIX_DEFAULT",
        "LATENCY_BUDGET",
        "WATCHED_LATENCY_MS",
        "FIFTY_MS",
        "SOAK_WEEK_SECONDS",
    }
    found: list[str] = []
    for path in (_HOST_SRC / "risk_population.py", _HOST_SRC / "shakedown.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in banned_names:
                        found.append(f"{path.name}:{target.id}")
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id in banned_names
            ):
                found.append(f"{path.name}:{node.target.id}")
    assert found == []
    assert SHAKEDOWN_IS_PERFORMANCE_PROOF is False
