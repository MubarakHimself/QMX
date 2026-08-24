"""Story 12.7 — gate registration on both conformance layers (QL-8)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity, Instant, WriterId
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import KindRegistry, Registrar, RegistrationRecord
from qml.conformance import (
    CITATION_KINDS,
    DROPPED_REGISTRATION_GATES,
    PROMOTED_FROM_EDGE_TYPE,
    BotCitation,
    CitationKind,
    Graduation,
    Layer1Verdict,
    Layer2Verdict,
    RegistrationCandidate,
    UngovernedTunnelAccess,
    admit_ungoverned_tunnel,
    cite_registered_bot,
    cite_ungoverned_bot,
    evaluate_layer2,
    evaluate_ticket,
    gate_registration,
    generate_golden_slice,
    graduate_to_governed,
    lint_declaration,
    run_layer2_suite,
)
from qml.declaration import (
    KIND_BOT_DEFINITION,
    BotDefinition,
    install_bot_definition_kind,
    mint_bot_definition,
    mint_confluence,
    register_bot_definition,
)
from qml.families import mint_strategy_family
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import LogicIdentity, mint_logic_identity
from qml.protocol import PROTOCOL_FORMAT_VERSION, FunctionFactory, mint_state_scope

import qml

T = TypeVar("T")

_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}
_CLOCK_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "import time\n\ndef on_instant(self, evidence):\n    return ()\n",
}
_REGISTRATION = (
    Path(__file__).resolve().parents[1] / "src" / "qml" / "conformance" / "registration.py"
)
_CREATED_NS = 1_700_000_000_000_000_000
_OS = "windows-11"
_AR = "none"
_BOUND = 256


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "test-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _calendar() -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))


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


def _world(*, source: dict[str, str] | None = None) -> dict[str, object]:
    zone = _pinned("zone")
    sma = _pinned("sma")
    family = _ok(mint_strategy_family("trend-follow"))
    confluence = _ok(mint_confluence([{"role": "level", "producer_binding": zone}]))
    footprint = _ok(mint_footprint([_stream()], [_calendar()], [zone, sma]))
    logic = _ok(mint_logic_identity("research-bot", "1.0.0", source or _SOURCE))
    declaration = _ok(
        mint_bot_definition(
            {
                "strategy_family_id": family.family_id.value,
                "confluence_set": [confluence],
                "parameter_space": [_int_param()],
                "footprint": footprint,
                "permitted_exit_intents": (),
                "logic_reference": logic,
            }
        )
    )
    return {
        "declaration": declaration,
        "family": family,
        "confluence": confluence,
        "logic": logic,
        "producers": [zone, sma],
        "source": source or _SOURCE,
    }


def _layer1(world: dict[str, object], **overrides: object) -> Result[Layer1Verdict]:
    kwargs: dict[str, object] = {
        "declaration": world["declaration"],
        "family_catalog": [world["family"]],
        "confluence_catalog": [world["confluence"]],
        "producer_catalog": world["producers"],
        "logic_catalog": [world["logic"]],
    }
    kwargs.update(overrides)
    return lint_declaration(**kwargs)


def _scope(declaration: BotDefinition):
    return _ok(
        mint_state_scope(
            os=_OS,
            logic_identity=declaration.logic_reference,
            protocol_format_version=PROTOCOL_FORMAT_VERSION,
            arithmetic_reference_build=_AR,
        )
    )


def _layer2(
    world: dict[str, object], *, source: dict[str, str] | None = None
) -> Result[Layer2Verdict]:
    declaration = cast(BotDefinition, world["declaration"])
    tree = source if source is not None else cast(dict[str, str], world["source"])
    return run_layer2_suite(
        declaration=declaration,
        factory=FunctionFactory(logic=lambda evidence: ()),
        source_tree=tree,
        state_scope=_scope(declaration),
        state_bound=_BOUND,
    )


def _gate(world: dict[str, object], **extra: object) -> Result[RegistrationCandidate]:
    return gate_registration(layer1=_layer1(world), layer2=_layer2(world), **extra)


def _writer(machine: str = "node-a") -> WriterId:
    return _ok(WriterId.try_create(machine, "authoring", KIND_BOT_DEFINITION, "boot-1"))


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


# --- AC: both layers pass → Bot kind may mint; either fail is policy --------


def test_both_layers_pass_returns_fingerprintable_candidate() -> None:
    world = _world()
    candidate = _ok(_gate(world))
    assert isinstance(candidate, RegistrationCandidate)
    assert candidate.ticket.layer1_passed is True
    assert candidate.ticket.layer2_passed is True
    assert candidate.logic is candidate.declaration.logic_reference
    payload = candidate.identity_payload()
    assert "writer" not in payload
    assert "sequence" not in payload
    assert "created_at" not in payload
    assert "stable_id" not in payload
    assert qml.__version__ not in payload.values()
    assert not isinstance(candidate, RegistrationRecord)
    identity = candidate.fp1_identity()
    assert identity["class"] == "qml-registration-candidate"
    assert identity["declaration_fingerprint"] == candidate.fingerprint.value
    assert qml.__version__ not in identity.values()


def test_gate_accepts_unwrapped_verdicts() -> None:
    world = _world()
    first = _ok(_layer1(world))
    second = _ok(_layer2(world))
    candidate = _ok(gate_registration(layer1=first, layer2=second))
    assert candidate.fingerprint == first.fingerprint


def test_layer1_failure_is_policy_rejection_with_no_mint() -> None:
    world = _world()
    refused = gate_registration(
        layer1=_layer1(world, family_catalog=()),
        layer2=_layer2(world),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["failed_layer"] == 1
    assert refused.context["failed_category"] == "unavailable dependency"
    assert refused.context["journal"] is True


def test_layer2_failure_is_policy_rejection_with_no_mint() -> None:
    world = _world(source=_CLOCK_SOURCE)
    refused = gate_registration(layer1=_layer1(world), layer2=_layer2(world))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["failed_layer"] == 2


def test_mismatched_layer_fingerprints_are_invalid_input() -> None:
    world_a = _world()
    world_b = _world()
    # Distinct producer tags mint distinct Bot fps.
    world_b["declaration"] = _ok(
        mint_bot_definition(
            {
                "strategy_family_id": cast(
                    BotDefinition, world_a["declaration"]
                ).strategy_family_id,
                "confluence_set": list(cast(BotDefinition, world_a["declaration"]).confluence_set),
                "parameter_space": [_int_param() | {"default": 14}],
                "footprint": cast(BotDefinition, world_a["declaration"]).footprint,
                "logic_reference": world_a["logic"],
            }
        )
    )
    refused = gate_registration(layer1=_layer1(world_a), layer2=_layer2(world_b))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "layers"


def test_no_probationary_registration() -> None:
    world = _world()
    refused = _gate(world, probation=True)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "probation"
    still = _ok(_gate(world, probation=False))
    assert still.ticket.layer1_passed is True


def test_non_verdict_inputs_are_invalid_input() -> None:
    world = _world()
    refused = gate_registration(layer1="pass", layer2=_layer2(world))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    refused2 = gate_registration(layer1=_layer1(world), layer2=object())
    assert is_refusal(refused2)
    assert refused2.category is RefusalCategory.INVALID_INPUT


# --- AC: registered Bot may be cited by governed evidence and seats ---------


def test_registered_bot_may_be_cited_by_governed_evidence_and_seats() -> None:
    candidate = _ok(_gate(_world()))
    evidence = _ok(
        cite_registered_bot(
            candidate=candidate,
            cited_fp1=candidate.fingerprint,
            kind=CitationKind.GOVERNED_EVIDENCE,
        )
    )
    assert isinstance(evidence, BotCitation)
    assert evidence.kind is CitationKind.GOVERNED_EVIDENCE
    seat = _ok(
        cite_registered_bot(
            candidate=candidate,
            cited_fp1=candidate.fingerprint.value,
            kind="seat",
        )
    )
    assert seat.kind is CitationKind.SEAT
    assert seat.fingerprint == candidate.fingerprint
    assert CITATION_KINDS == ("governed-evidence", "seat")


def test_citation_of_a_different_fp1_is_policy_rejection() -> None:
    candidate = _ok(_gate(_world()))
    other = _ok(fingerprint({"class": "other-bot"}))
    refused = cite_registered_bot(
        candidate=candidate,
        cited_fp1=other,
        kind="governed-evidence",
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "cited_fp1"


def test_citation_without_a_ticket_is_policy_rejection() -> None:
    refused = cite_registered_bot(
        candidate=None,
        cited_fp1=_ok(fingerprint({"class": "research"})),
        kind="seat",
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert cite_ungoverned_bot().category is RefusalCategory.POLICY_REJECTION


def test_unknown_citation_kind_is_invalid_input() -> None:
    candidate = _ok(_gate(_world()))
    refused = cite_registered_bot(
        candidate=candidate,
        cited_fp1=candidate.fingerprint,
        kind="exam",
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


# --- AC: ungoverned plain-Python bots keep full tunnel access ---------------


def test_ungoverned_bots_keep_full_tunnel_access() -> None:
    access = _ok(admit_ungoverned_tunnel())
    assert isinstance(access, UngovernedTunnelAccess)
    identity = access.fp1_identity()
    assert identity["ticket_required"] is False
    assert identity["citation_allowed"] is False
    assert identity["tunnel_open"] is True
    cited = cite_ungoverned_bot()
    assert cited.context["tunnel_open"] is True
    assert cited.context["citation_allowed"] is False


# --- AC: graduation mints two artifacts with lineage to originating research


def test_graduation_mints_two_artifacts_with_promoted_from_edge() -> None:
    world = _world()
    research = _ok(fingerprint({"class": "research-experiment", "id": "exp-42"}))
    graduated = _ok(
        graduate_to_governed(
            layer1=_layer1(world),
            layer2=_layer2(world),
            originating_research_ref=research,
        )
    )
    assert isinstance(graduated, Graduation)
    assert isinstance(graduated.declaration, BotDefinition)
    assert isinstance(graduated.logic, LogicIdentity)
    assert graduated.logic == graduated.declaration.logic_reference
    assert graduated.promoted_from_edge.edge_type == PROMOTED_FROM_EDGE_TYPE
    assert graduated.promoted_from_edge.edge_type == "promoted-from"
    assert graduated.promoted_from_edge.from_ref == graduated.candidate.fingerprint
    assert graduated.promoted_from_edge.to_ref == research
    assert "writer" not in graduated.promoted_from_edge.fp1_identity()
    edge_fp = _ok(graduated.promoted_from_edge.fingerprint_content())
    assert edge_fp.value.startswith("fp1:sha256:")


def test_graduation_refuses_a_failed_layer_and_a_self_edge() -> None:
    world = _world()
    failed = graduate_to_governed(
        layer1=_layer1(world, family_catalog=()),
        layer2=_layer2(world),
        originating_research_ref=_ok(fingerprint({"class": "research"})),
    )
    assert is_refusal(failed)
    assert failed.category is RefusalCategory.POLICY_REJECTION
    candidate = _ok(_gate(world))
    looped = graduate_to_governed(
        layer1=_layer1(world),
        layer2=_layer2(world),
        originating_research_ref=candidate.fingerprint,
    )
    assert is_refusal(looped)
    assert looped.category is RefusalCategory.INVALID_INPUT


def test_graduation_research_ref_must_be_fp1() -> None:
    world = _world()
    refused = graduate_to_governed(
        layer1=_layer1(world),
        layer2=_layer2(world),
        originating_research_ref="research://exp-42",
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


# --- AC: max_acceptable_complexity_score is not revived ---------------------


def test_complexity_score_is_not_a_registration_gate() -> None:
    world = _world()
    huge = _ok(
        _gate(
            world,
            max_acceptable_complexity_score=10**9,
            complexity_score=0,
        )
    )
    tiny = _ok(_gate(world))
    assert huge.fingerprint == tiny.fingerprint
    assert (
        frozenset({"max_acceptable_complexity_score", "complexity_score"})
        == DROPPED_REGISTRATION_GATES
    )


def test_dropped_complexity_gate_is_never_consulted() -> None:
    source = _REGISTRATION.read_text(encoding="utf-8")
    assert "max_acceptable_complexity_score" in source
    tree = ast.parse(source, filename=str(_REGISTRATION))
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            dumped = ast.dump(node)
            assert "complexity" not in dumped.lower()
        if isinstance(node, ast.If):
            dumped = ast.dump(node.test)
            assert "complexity" not in dumped.lower()


# --- AC: host stamps; qml returns content + verdict never a stamped record --


def test_host_stamps_after_a_pass_qml_never_returns_the_record() -> None:
    world = _world()
    candidate = _ok(_gate(world))
    registry = KindRegistry()
    assert is_ok(install_bot_definition_kind(registry))
    registrar = Registrar(registry)
    receipt = _ok(
        register_bot_definition(
            candidate.declaration,
            registrar=registrar,
            writer=_writer(),
            sequence=0,
            created_at=_instant(),
        )
    )
    assert receipt.record.kind == KIND_BOT_DEFINITION
    assert receipt.record.writer == _writer()
    assert "writer" not in candidate.identity_payload()
    assert type(candidate).__name__ == "RegistrationCandidate"


def test_evaluate_ticket_still_requires_both_bools() -> None:
    assert is_ok(evaluate_ticket(layer1_passed=True, layer2_passed=True))
    refused = evaluate_ticket(layer1_passed=True, layer2_passed=False)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_book_present_layer2_failure_is_policy_at_the_gate() -> None:
    world = _world()
    declaration = cast(BotDefinition, world["declaration"])
    slice_ = _ok(generate_golden_slice(declaration.footprint))
    observations = evaluate_layer2(
        {
            "loaded_in_isolation": True,
            "book_present": True,
            "scan_findings": (),
            "golden_slice_fingerprint": _ok(slice_.fingerprint_content()),
            "declaration_fingerprint": _ok(declaration.fingerprint_content()),
            "first_run": ((), (), ()),
            "second_run": ((), (), ()),
            "state_bound_holds": True,
            "restore_equivalent": True,
        }
    )
    refused = gate_registration(layer1=_layer1(world), layer2=observations)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["failed_layer"] == 2


def test_unknown_extra_field_is_invalid_input() -> None:
    world = _world()
    refused = _gate(world, archetype="trend")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_registration_module_is_pure() -> None:
    banned = frozenset(
        {
            "subprocess",
            "threading",
            "multiprocessing",
            "socket",
            "asyncio",
            "qmf.venue",
        }
    )
    tree = ast.parse(_REGISTRATION.read_text(encoding="utf-8"), filename=str(_REGISTRATION))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in banned
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module not in banned
            assert not node.module.startswith("qmf.venue")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "open"


def test_public_export_surface() -> None:
    assert qml.gate_registration is gate_registration
    assert qml.graduate_to_governed is graduate_to_governed
    assert qml.cite_registered_bot is cite_registered_bot
    assert qml.admit_ungoverned_tunnel is admit_ungoverned_tunnel
    assert qml.RegistrationCandidate is RegistrationCandidate
    assert qml.DROPPED_REGISTRATION_GATES is DROPPED_REGISTRATION_GATES
    assert qml.PROMOTED_FROM_EDGE_TYPE == "promoted-from"
