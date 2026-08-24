"""Story 12.6 — prediction linter (QL-8)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity, Duration
from qmf.core.exact import ExactRational, UnitKind
from qmf.core.fingerprint import World, fingerprint
from qmf.core.identity import AccountRole
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.admission_bar import (
    AdmissionBar,
    AdmissionRequirement,
    Comparison,
    EvidenceRequirements,
    RuledThreshold,
)
from qmf.risk.binding import BindingState, PositionModel, VenueBindingProfile
from qmf.risk.door import ExitKind, ExitLogicRef
from qmf.risk.exit_policy import ExitPolicy, ExitPolicyResolution
from qmf.risk.footprint_requirements import (
    FORMAT_1_FOOTPRINT_REQUIREMENTS_PENDING,
    FootprintFieldKind,
    FootprintRequirement,
    FootprintRequirements,
)
from qmf.risk.grammar import NotYetRuled
from qmf.risk.migrations import THRESHOLD_GAPS_BEHIND_NEW_ADMISSION_BAR_FIELDS
from qml.conformance import (
    CONFORMANCE_FORMAT_VERSION,
    PREDICTION_CHECKS,
    PredictionBindingContext,
    PredictionVerdict,
    conformance_contract_identity,
    lint_prediction,
    stream_set_required_capabilities,
)
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.families import mint_strategy_family
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity

import qml

T = TypeVar("T")

_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}
_PREDICTION = Path(__file__).resolve().parents[1] / "src" / "qml" / "conformance" / "prediction.py"
_VENUE_CAPS: frozenset[str] = frozenset({"trading", "time-interval"})


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "test-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _calendar() -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))


def _logic():
    return _ok(mint_logic_identity("research-bot", "1.0.0", _SOURCE))


def _family():
    return _ok(mint_strategy_family("trend-follow"))


def _int_param() -> dict[str, object]:
    return {
        "name": "lookback",
        "type": "exact integer",
        "bounds": {"min": 1, "max": 200},
        "step": 1,
        "default": 20,
        "unit_kind": UnitKind.COUNT,
        "ui": "ui-editable",
    }


def _stream() -> dict[str, object]:
    return {
        "instrument_role": "primary",
        "bar_specs": [{"kind": "time-interval", "seconds": 60}],
        "stream_role": "trading",
    }


def _ref(module_id: str = "book.default.evidence_stop") -> ExitLogicRef:
    return _ok(ExitLogicRef.try_create(module_id, {"style": "structure"}))


def _er(num: int, den: int = 1, kind: UnitKind = UnitKind.COUNT) -> ExactRational:
    return _ok(ExactRational.try_create(num, den, kind))


def _blank(gap: str = "GAP-0048") -> NotYetRuled:
    return _ok(NotYetRuled.try_create(gap))


def _req(
    field_identity: str = "stream_set",
    *,
    field_kind: FootprintFieldKind = FootprintFieldKind.STREAM_SET,
    comparison: Comparison = Comparison.AT_LEAST,
    threshold: object | None = None,
    unit: UnitKind = UnitKind.COUNT,
    display_ordinal: int = 0,
) -> FootprintRequirement:
    if threshold is None:
        threshold = _blank()
    return _ok(
        FootprintRequirement.try_create(
            field_kind, field_identity, unit, comparison, threshold, display_ordinal
        )
    )


def _requirements(*items: FootprintRequirement) -> FootprintRequirements:
    return _ok(FootprintRequirements.try_create(items))


def _policy(
    *,
    family_id: str = "trend-follow",
    kinds: object = (),
    catch_all: ExitLogicRef | None = None,
) -> ExitPolicy:
    entries = {} if family_id == "" else {family_id: _ref()}
    return _ok(
        ExitPolicy.try_create(
            entries,
            permitted_exit_intent_kinds=kinds,
            catch_all_default_entry=catch_all,
        )
    )


def _declaration(*, exits: object = ()) -> BotDefinition:
    zone = _pinned("zone")
    confluence = _ok(mint_confluence([{"role": "level", "producer_binding": zone}]))
    footprint = _ok(mint_footprint([_stream()], [_calendar()], [zone]))
    family = _family()
    return _ok(
        mint_bot_definition(
            {
                "strategy_family_id": family.family_id.value,
                "confluence_set": [confluence],
                "parameter_space": [_int_param()],
                "footprint": footprint,
                "permitted_exit_intents": exits,
                "logic_reference": _logic(),
            }
        )
    )


def _lint(
    declaration: object | None = None,
    *,
    exit_policy: object | None = None,
    footprint_requirements: object = (),
    venue_capabilities: object = _VENUE_CAPS,
    account_role: object = AccountRole.DEMO,
    admission_bar: object = None,
    exits: object = (),
) -> Result[PredictionVerdict]:
    bot = _declaration(exits=exits) if declaration is None else declaration
    policy = _policy() if exit_policy is None else exit_policy
    return lint_prediction(
        bot,
        exit_policy=policy,
        footprint_requirements=footprint_requirements,
        venue_capabilities=venue_capabilities,
        account_role=account_role,
        admission_bar=admission_bar,
    )


# --- AC: pinned four-check list ----------------------------------------------


def test_pinned_checks_are_addable_never_redefined() -> None:
    assert PREDICTION_CHECKS == (
        "footprint_satisfies_requirements",
        "exit_intent_subset",
        "family_resolves_exit_policy",
        "stream_set_within_venue_capabilities",
    )
    identity = conformance_contract_identity()
    assert identity["prediction_checks"] == list(PREDICTION_CHECKS)
    assert identity["ladder"] == "qml-ad5"
    assert "ct" not in identity
    assert qml.__version__ not in identity.values()


def test_clean_binding_passes_every_prediction_check() -> None:
    verdict = _ok(_lint())
    assert isinstance(verdict, PredictionVerdict)
    assert verdict.checks == PREDICTION_CHECKS
    assert verdict.live_binding_blocked is False
    assert verdict.account_role is AccountRole.DEMO
    assert verdict.resolved_exit_entry.resolution is ExitPolicyResolution.EXPLICIT_FAMILY
    identity = verdict.fp1_identity()
    assert identity["class"] == "qml-prediction-verdict"
    assert identity["contract_format_version"] == CONFORMANCE_FORMAT_VERSION
    assert identity["declaration_fingerprint"] == verdict.fingerprint.value
    assert identity["threshold_gaps"] == list(THRESHOLD_GAPS_BEHIND_NEW_ADMISSION_BAR_FIELDS)
    assert qml.__version__ not in identity.values()


def test_on_demand_and_seat_time_share_one_pure_function() -> None:
    on_demand = _ok(_lint(account_role=AccountRole.DEMO))
    seat = _ok(_lint(account_role=BindingState.PAPER))
    assert on_demand.fingerprint == seat.fingerprint
    assert on_demand.checks == seat.checks


# --- AC: (b) entry-only vs zero-exit Book ------------------------------------


def test_entry_only_bot_passes_zero_exit_kind_book() -> None:
    policy = _policy(kinds=())
    verdict = _ok(_lint(exit_policy=policy, exits=()))
    assert verdict.declaration.permitted_exit_intents == ()
    assert policy.permitted_exit_intent_kinds == frozenset()


def test_exit_kinds_must_be_a_subset() -> None:
    policy = _policy(kinds=())
    refused = _lint(exit_policy=policy, exits=("close_full",))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "permitted_exit_intents"
    assert refused.context["linter"] == "prediction"
    assert refused.context["journal"] is True
    allowed = _ok(_lint(exit_policy=_policy(kinds=(ExitKind.CLOSE_FULL,)), exits=("close_full",)))
    assert "close_full" in allowed.declaration.permitted_exit_intents


# --- AC: (c) unresolved family -----------------------------------------------


def test_unresolved_family_is_prediction_linter_failure() -> None:
    policy = _ok(ExitPolicy.try_create({}, permitted_exit_intent_kinds=()))
    refused = _lint(exit_policy=policy)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "exit_policy"
    assert refused.context["family_id"] == "trend-follow"
    assert refused.context["journal"] is True


def test_catch_all_resolves_unknown_family() -> None:
    policy = _ok(
        ExitPolicy.try_create(
            {},
            permitted_exit_intent_kinds=(),
            catch_all_default_entry=_ref("book.catch-all"),
        )
    )
    verdict = _ok(_lint(exit_policy=policy))
    assert verdict.resolved_exit_entry.resolution is ExitPolicyResolution.CATCH_ALL_DEFAULT


# --- AC: (d) stream set within CT-18 venue capabilities ----------------------


def test_stream_set_within_declared_venue_capabilities() -> None:
    bot = _declaration()
    required = _ok(stream_set_required_capabilities(bot.footprint))
    assert required == frozenset({"trading", "time-interval"})
    profile = _ok(
        VenueBindingProfile.try_create(
            frozenset({"trading", "time-interval", "bar"}),
            PositionModel.HEDGING,
            "USD",
        )
    )
    verdict = _ok(_lint(declaration=bot, venue_capabilities=profile))
    assert verdict.live_binding_blocked is False


def test_stream_set_exceeding_venue_caps_is_bind_time_failure() -> None:
    refused = _lint(venue_capabilities=frozenset({"tick"}))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refused.context["field"] == "venue_capabilities"
    assert refused.context["bind_time"] is True
    extra = cast("tuple[str, ...]", refused.context["extra"])
    assert "trading" in extra or "time-interval" in extra


# --- AC: (a) footprint satisfies requirements --------------------------------


def test_ruled_footprint_requirement_must_hold() -> None:
    ruled = _ok(RuledThreshold.try_create(_er(1)))
    reqs = _requirements(_req("stream_set", threshold=ruled))
    verdict = _ok(_lint(footprint_requirements=reqs))
    assert verdict.live_binding_blocked is False
    too_high = _requirements(
        _req(
            "stream_set",
            comparison=Comparison.AT_LEAST,
            threshold=_ok(RuledThreshold.try_create(_er(2))),
        )
    )
    refused = _lint(footprint_requirements=too_high)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "footprint_requirements"
    missing = _requirements(
        _req(
            "missing-role",
            field_kind=FootprintFieldKind.STREAM_SET,
            threshold=_ok(RuledThreshold.try_create(_er(1))),
        )
    )
    absent = _lint(footprint_requirements=missing)
    assert is_refusal(absent)


def test_member_identity_presence_and_locus_count() -> None:
    present = _requirements(
        _req(
            "primary",
            field_kind=FootprintFieldKind.STREAM_SET,
            threshold=_ok(RuledThreshold.try_create(_er(1))),
        ),
        _req(
            "calendars.forex-17NY",
            field_kind=FootprintFieldKind.CALENDARS,
            threshold=_ok(RuledThreshold.try_create(_er(1))),
        ),
    )
    assert is_ok(_lint(footprint_requirements=present))


# --- AC: blank GAP-0048/0049 passes registration, blocks live ----------------


def test_blank_footprint_requirement_passes_non_live_and_blocks_live() -> None:
    reqs = _requirements(_req(threshold=_blank("GAP-0048")))
    demo = _ok(_lint(footprint_requirements=reqs, account_role=AccountRole.DEMO))
    assert demo.live_binding_blocked is True
    gaps = demo.fp1_identity()["threshold_gaps"]
    assert isinstance(gaps, list)
    assert "GAP-0048" in gaps
    paper = _ok(_lint(footprint_requirements=reqs, account_role=BindingState.PAPER))
    assert paper.live_binding_blocked is True
    live = _lint(footprint_requirements=reqs, account_role=AccountRole.LIVE)
    assert is_refusal(live)
    assert live.category is RefusalCategory.POLICY_REJECTION
    reason = str(live.context["reason"])
    assert THRESHOLD_GAPS_BEHIND_NEW_ADMISSION_BAR_FIELDS[0] in reason
    assert live.context["journal"] is True


def test_format_1_pending_slot_blocks_live_only() -> None:
    demo = _ok(
        _lint(
            footprint_requirements=FORMAT_1_FOOTPRINT_REQUIREMENTS_PENDING,
            account_role=AccountRole.DEMO,
        )
    )
    assert demo.live_binding_blocked is True
    live = _lint(
        footprint_requirements=FORMAT_1_FOOTPRINT_REQUIREMENTS_PENDING,
        account_role=AccountRole.LIVE,
    )
    assert is_refusal(live)
    assert live.category is RefusalCategory.POLICY_REJECTION


def test_blank_admission_bar_threshold_blocks_live() -> None:
    evidence = _ok(
        EvidenceRequirements.try_create(
            World.LIVE, AccountRole.LIVE, Duration(value_ns=86_400_000_000_000), {}
        )
    )
    requirement = _ok(
        AdmissionRequirement.try_create(
            "sharpe",
            UnitKind.DIMENSIONLESS_RATIO,
            Comparison.AT_LEAST,
            _blank("GAP-0049"),
            evidence,
            0,
        )
    )
    bar = _ok(AdmissionBar.try_create([requirement]))
    demo = _ok(_lint(admission_bar=bar, account_role=AccountRole.DEMO))
    assert demo.live_binding_blocked is True
    live = _lint(admission_bar=bar, account_role=AccountRole.LIVE)
    assert is_refusal(live)
    assert live.category is RefusalCategory.POLICY_REJECTION


# --- refusals, purity, public surface ----------------------------------------


def test_malformed_binding_inputs_are_invalid() -> None:
    assert is_refusal(_lint(exit_policy="nope"))
    assert is_refusal(_lint(footprint_requirements="nope"))
    assert is_refusal(_lint(venue_capabilities="trading"))
    assert is_refusal(_lint(account_role="not-a-role"))
    assert is_refusal(_lint(admission_bar="nope"))
    assert is_refusal(stream_set_required_capabilities("nope"))


def test_prediction_module_is_pure_and_venue_free() -> None:
    tree = ast.parse(_PREDICTION.read_text(encoding="utf-8"), filename=str(_PREDICTION))
    banned = {"subprocess", "threading", "multiprocessing", "socket", "asyncio", "pathlib"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned
                assert not alias.name.startswith("qmf.venue")
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned
            assert not node.module.startswith("qmf.venue")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "open"


def test_public_export_surface() -> None:
    bot = _declaration()
    policy = _policy()
    reqs = _ok(FootprintRequirements.try_create(()))
    context = PredictionBindingContext(
        declaration=bot,
        exit_policy=policy,
        footprint_requirements=reqs,
        venue_capabilities=_VENUE_CAPS,
        account_role=AccountRole.DEMO,
    )
    identity = context.fp1_identity()
    assert identity["class"] == "qml-prediction-binding-context"
    assert identity["account_role"] == AccountRole.DEMO.value
    assert qml.lint_prediction is lint_prediction
    assert qml.PREDICTION_CHECKS == PREDICTION_CHECKS
    assert qml.PredictionVerdict is PredictionVerdict
    assert qml.PredictionBindingContext is PredictionBindingContext
    assert qml.stream_set_required_capabilities is stream_set_required_capabilities
