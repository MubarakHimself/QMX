"""Shared helpers for Stage 0 → Stage 1 collapse tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, is_ok
from qml.conformance import lint_declaration, run_layer2_suite
from qml.declaration import BotDefinition, Confluence, mint_bot_definition, mint_confluence
from qml.families import StrategyFamilyRecord, mint_strategy_family
from qml.footprint import Footprint, ProducerBinding, mint_footprint
from qml.logic import LogicIdentity, mint_logic_identity
from qml.protocol import PROTOCOL_FORMAT_VERSION, FunctionFactory, mint_state_scope
from qml.research import (
    F_SLOTS,
    DictionaryCite,
    Hypothesis,
    RoleBinding,
    mint_hypothesis,
)

T = TypeVar("T")

SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}


def ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def pinned(tag: str) -> ProducerBinding:
    return ok(ProducerBinding.try_create(ok(fingerprint({"class": "test-producer", "tag": tag}))))


def open_role_hypothesis() -> Hypothesis:
    cite = DictionaryCite("dictionary/a.md", "swing-high")
    return ok(
        mint_hypothesis(
            hypothesis_class="entry_hypothesis",
            origin="seed_package",
            role_bindings=[
                RoleBinding(cite=cite, role="location"),
                RoleBinding(cite=cite, role="trigger"),
                RoleBinding(cite=cite, role="invalidation"),
                RoleBinding(cite=cite, role="confirmation"),
                RoleBinding(cite=cite, role="filter"),
            ],
            graph={"operators": ("ALL", "sequence", "within"), "meaning": ("boolean", "temporal")},
        )
    )


def unresolved_f_hypothesis() -> Hypothesis:
    return ok(
        mint_hypothesis(
            hypothesis_class="entry_hypothesis",
            origin="idea",
            f_labels=dict.fromkeys(F_SLOTS, "unresolved"),
        )
    )


@dataclass(frozen=True, slots=True)
class ResearchBotWorld:
    zone: ProducerBinding
    family: StrategyFamilyRecord
    confluence: Confluence
    footprint: Footprint
    logic: LogicIdentity
    source: dict[str, str]


def research_bot_world() -> ResearchBotWorld:
    zone = pinned("zone")
    family = ok(mint_strategy_family("trend-follow"))
    confluence = ok(mint_confluence([{"role": "level", "producer_binding": zone}]))
    footprint = ok(
        mint_footprint(
            [
                {
                    "instrument_role": "primary",
                    "bar_specs": [{"kind": "time-interval", "seconds": 60}],
                    "stream_role": "trading",
                }
            ],
            [ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))],
            [zone],
        )
    )
    logic = ok(mint_logic_identity("research-bot", "1.0.0", SOURCE))
    return ResearchBotWorld(
        zone=zone,
        family=family,
        confluence=confluence,
        footprint=footprint,
        logic=logic,
        source=SOURCE,
    )


def bot_definition_body(
    world: ResearchBotWorld,
    *,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    body: dict[str, object] = {
        "strategy_family_id": world.family.family_id.value,
        "confluence_set": [world.confluence],
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
        "footprint": world.footprint,
        "permitted_exit_intents": (),
        "logic_reference": world.logic,
    }
    if extra:
        body.update(extra)
    return body


def mint_research_bot(
    world: ResearchBotWorld,
    *,
    extra: dict[str, object] | None = None,
) -> Result[BotDefinition]:
    return mint_bot_definition(bot_definition_body(world, extra=extra))


def layer_verdicts(
    world: ResearchBotWorld,
    declaration: BotDefinition,
) -> tuple[object, object]:
    layer1 = lint_declaration(
        declaration=declaration,
        family_catalog=[world.family],
        confluence_catalog=[world.confluence],
        producer_catalog=[world.zone],
        logic_catalog=[world.logic],
    )
    layer2 = run_layer2_suite(
        declaration=declaration,
        factory=FunctionFactory(logic=lambda evidence: ()),
        source_tree=world.source,
        state_scope=ok(
            mint_state_scope(
                os="windows-11",
                logic_identity=declaration.logic_reference,
                protocol_format_version=PROTOCOL_FORMAT_VERSION,
                arithmetic_reference_build="none",
            )
        ),
        state_bound=256,
    )
    return layer1, layer2
