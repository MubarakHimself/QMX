"""Reference usage — gate registration on both conformance layers (Story 12.7).

Executable::

    python qml/examples/registration_usage.py

Shows the things QL-8 / Story 12.7 pin down:

1. The Bot kind mints only if both Layer 1 and Layer 2 pass. A declaration
   failing either layer is ``policy rejection`` — there is no partial or
   probationary registration.
2. A registered Bot definition may be cited by governed evidence (CT-32) and
   seats (CT-28) by ``fp1``. Conformance gates citation and seats, never
   tunnel entry.
3. Ungoverned plain-Python bots keep full tunnel access (B-4 ledger lines,
   the research door) and cannot be cited by governed evidence.
4. Graduation mints the two artifacts (declaration + logic) with a
   ``promoted-from`` lineage edge back to the originating research artifact.
5. ``max_acceptable_complexity_score`` is a stated drop — never a registration
   gate. qml returns fingerprintable content plus the pass/fail verdict; the
   host composition root holds the ``WriterId`` and stamps the record.
"""

from __future__ import annotations

from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity, Instant, WriterId
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, TypedRefusal, is_ok
from qmf.registry import KindRegistry, Registrar
from qml.conformance import (
    DROPPED_REGISTRATION_GATES,
    Layer1Verdict,
    Layer2Verdict,
    RegistrationCandidate,
    admit_ungoverned_tunnel,
    cite_registered_bot,
    cite_ungoverned_bot,
    evaluate_layer2,
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
from qml.logic import mint_logic_identity
from qml.protocol import PROTOCOL_FORMAT_VERSION, FunctionFactory, mint_state_scope

T = TypeVar("T")

_SOURCE = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _pinned(tag: str) -> ProducerBinding:
    fp = _unwrap(fingerprint({"class": "example-producer", "tag": tag}), "producer fp")
    return _unwrap(ProducerBinding.try_create(fp), "binding")


def _calendar() -> CalendarIdentity:
    return _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"), "calendar")


def _world() -> dict[str, object]:
    zone = _pinned("zone")
    sma = _pinned("sma")
    family = _unwrap(mint_strategy_family("trend-follow"), "family")
    confluence = _unwrap(
        mint_confluence([{"role": "level", "producer_binding": zone}]),
        "confluence",
    )
    footprint = _unwrap(
        mint_footprint(
            [
                {
                    "instrument_role": "primary",
                    "bar_specs": [{"kind": "time-interval", "seconds": 60}],
                    "stream_role": "trading",
                }
            ],
            [_calendar()],
            [zone, sma],
        ),
        "footprint",
    )
    logic = _unwrap(mint_logic_identity("research-bot", "1.0.0", _SOURCE), "logic")
    declaration = _unwrap(
        mint_bot_definition(
            {
                "strategy_family_id": family.family_id.value,
                "confluence_set": [confluence],
                "parameter_space": [
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
                "footprint": footprint,
                "permitted_exit_intents": (),
                "logic_reference": logic,
            }
        ),
        "declaration",
    )
    return {
        "declaration": declaration,
        "family": family,
        "confluence": confluence,
        "logic": logic,
        "producers": [zone, sma],
    }


def _lint(world: dict[str, object], **overrides: object) -> Result[Layer1Verdict]:
    kwargs: dict[str, object] = {
        "declaration": world["declaration"],
        "family_catalog": [world["family"]],
        "confluence_catalog": [world["confluence"]],
        "producer_catalog": world["producers"],
        "logic_catalog": [world["logic"]],
    }
    kwargs.update(overrides)
    return lint_declaration(**kwargs)


def _suite(world: dict[str, object]) -> Result[Layer2Verdict]:
    declaration = cast(BotDefinition, world["declaration"])
    scope = _unwrap(
        mint_state_scope(
            os="windows-11",
            logic_identity=declaration.logic_reference,
            protocol_format_version=PROTOCOL_FORMAT_VERSION,
            arithmetic_reference_build="none",
        ),
        "scope",
    )
    return run_layer2_suite(
        declaration=declaration,
        factory=FunctionFactory(logic=lambda evidence: ()),
        source_tree=_SOURCE,
        state_scope=scope,
        state_bound=256,
    )


def both_layers_pass() -> bool:
    world = _world()
    candidate = _unwrap(
        gate_registration(layer1=_lint(world), layer2=_suite(world)),
        "gate",
    )
    assert isinstance(candidate, RegistrationCandidate)
    payload = candidate.identity_payload()
    assert "writer" not in payload
    assert "sequence" not in payload
    assert "created_at" not in payload
    return candidate.ticket.layer1_passed and candidate.ticket.layer2_passed


def qml_returns_fingerprintable_content() -> bool:
    world = _world()
    candidate = _unwrap(
        gate_registration(layer1=_lint(world), layer2=_suite(world)),
        "gate",
    )
    registry = KindRegistry()
    _unwrap(install_bot_definition_kind(registry), "install")
    registrar = Registrar(registry)
    writer = _unwrap(
        WriterId.try_create("node-a", "authoring", KIND_BOT_DEFINITION, "boot-1"),
        "writer",
    )
    created = _unwrap(Instant.try_create(1_700_000_000_000_000_000), "created-at")
    receipt = _unwrap(
        register_bot_definition(
            candidate.declaration,
            registrar=registrar,
            writer=writer,
            sequence=0,
            created_at=created,
        ),
        "host stamp",
    )
    assert receipt.record.kind == KIND_BOT_DEFINITION
    assert "writer" not in candidate.identity_payload()
    return True


def layer1_fail_is_policy() -> str:
    world = _world()
    refused = gate_registration(layer1=_lint(world, family_catalog=()), layer2=_suite(world))
    assert isinstance(refused, TypedRefusal)
    return refused.category.value


def layer2_fail_is_policy() -> str:
    world = _world()
    declaration = cast(BotDefinition, world["declaration"])
    slice_ = _unwrap(generate_golden_slice(declaration.footprint), "slice")
    observations = evaluate_layer2(
        {
            "loaded_in_isolation": True,
            "book_present": True,
            "scan_findings": (),
            "golden_slice_fingerprint": _unwrap(slice_.fingerprint_content(), "slice fp"),
            "declaration_fingerprint": _unwrap(declaration.fingerprint_content(), "decl fp"),
            "first_run": ((), (), ()),
            "second_run": ((), (), ()),
            "state_bound_holds": True,
            "restore_equivalent": True,
        }
    )
    refused = gate_registration(layer1=_lint(world), layer2=observations)
    assert isinstance(refused, TypedRefusal)
    return refused.category.value


def no_probation() -> bool:
    world = _world()
    refused = gate_registration(
        layer1=_lint(world),
        layer2=_suite(world),
        probation=True,
    )
    assert isinstance(refused, TypedRefusal)
    return refused.category.value == "policy rejection"


def citations() -> tuple[bool, bool]:
    world = _world()
    candidate = _unwrap(
        gate_registration(layer1=_lint(world), layer2=_suite(world)),
        "gate",
    )
    evidence = _unwrap(
        cite_registered_bot(
            candidate=candidate,
            cited_fp1=candidate.fingerprint,
            kind="governed-evidence",
        ),
        "ct-32 cite",
    )
    seat = _unwrap(
        cite_registered_bot(
            candidate=candidate,
            cited_fp1=candidate.fingerprint,
            kind="seat",
        ),
        "seat cite",
    )
    return evidence.kind.value == "governed-evidence", seat.kind.value == "seat"


def ungoverned_tunnel() -> tuple[bool, str]:
    access = _unwrap(admit_ungoverned_tunnel(), "tunnel")
    cited = cite_ungoverned_bot()
    assert isinstance(cited, TypedRefusal)
    return access.fp1_identity()["tunnel_open"] is True, cited.category.value


def graduation_lineage() -> str:
    world = _world()
    research = _unwrap(fingerprint({"class": "research-experiment", "id": "exp-42"}), "research")
    graduated = _unwrap(
        graduate_to_governed(
            layer1=_lint(world),
            layer2=_suite(world),
            originating_research_ref=research,
        ),
        "graduation",
    )
    assert graduated.declaration.logic_reference is graduated.logic
    assert graduated.promoted_from_edge.to_ref == research
    return graduated.promoted_from_edge.edge_type


def complexity_is_not_a_gate() -> bool:
    world = _world()
    candidate = _unwrap(
        gate_registration(
            layer1=_lint(world),
            layer2=_suite(world),
            max_acceptable_complexity_score=10_000,
        ),
        "gate",
    )
    return (
        "max_acceptable_complexity_score" in DROPPED_REGISTRATION_GATES
        and candidate.ticket.layer1_passed
        and candidate.ticket.layer2_passed
    )


def main() -> None:
    print(f"layer 1 and layer 2 pass: {both_layers_pass()}")
    print(f"qml returns fingerprintable content: {qml_returns_fingerprintable_content()}")
    print("host stamps WriterId: True")
    print(f"layer 1 fail is policy rejection: {layer1_fail_is_policy()}")
    print(f"layer 2 fail is policy rejection: {layer2_fail_is_policy()}")
    print(f"no probation: {no_probation()}")
    evidence, seat = citations()
    print(f"governed evidence cite: {evidence}")
    print(f"seat cite: {seat}")
    tunnel, ungoverned_cite = ungoverned_tunnel()
    print(f"ungoverned tunnel open: {tunnel}")
    print(f"ungoverned cannot be cited: {ungoverned_cite}")
    print(f"graduation lineage: {graduation_lineage()}")
    print(f"complexity is not a gate: {complexity_is_not_a_gate()}")
    print("registration gate ok")


if __name__ == "__main__":
    main()
