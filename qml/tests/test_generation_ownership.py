"""Story 38.1 — search stays QMB; generation write-ownership is QML/host."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from qmf.core.chrono import CalendarIdentity, Instant, WriterId
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import KindRegistry, Registrar, RegistrationRecord
from qml.conformance import evaluate_ticket
from qml.declaration import KIND_BOT_DEFINITION
from qml.footprint import ProducerBinding, mint_footprint
from qml.generation import (
    ACT_GENERATION,
    ACT_SEARCH,
    FORBIDDEN_QMB_GENERATOR_NAMES,
    GENERATOR_ALGORITHM_UNRULED,
    QMB_AUTHORS_CANDIDATES,
    QMB_RUNS_CANDIDATES,
    RANDOM_CONDITION_DONOR_SHAPE,
    ActKind,
    AuthoredStructure,
    author_new_structure,
    classify_parameter_search,
    forbidden_generator_module_hits,
    refuse_gap_0085_nouns,
    refuse_generator_algorithm,
    refuse_no_code_authoring,
    refuse_qml_dsl,
    refuse_random_condition_schema,
)
from qml.host import (
    HOST_MINTS_CT06_ENVELOPE,
    install_bot_domain_kinds,
    mint_ct06_envelope,
    mint_generation_envelope,
    register_bot_definition,
)

import qml
from qml import host

T = TypeVar("T")

_REPO = Path(__file__).resolve().parents[2]
_QMB_SRC = _REPO / "qmb" / "src" / "qmb"
_CREATED_NS = 1_700_000_000_000_000_000
_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, instant):\n    return ()\n",
}


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _writer(kind: str, machine: str = "node-a") -> WriterId:
    return _ok(WriterId.try_create(machine, "authoring", kind, "boot-1"))


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "test-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _calendar() -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))


def _footprint(tag: str = "sma") -> object:
    return _ok(
        mint_footprint(
            [
                {
                    "instrument_role": "primary",
                    "bar_specs": [{"kind": "time-interval", "seconds": 60}],
                    "stream_role": "trading",
                }
            ],
            [_calendar()],
            [_pinned(tag)],
        )
    )


def _int_param(default: int = 20) -> dict[str, object]:
    return {
        "name": "lookback",
        "type": "exact integer",
        "bounds": {"min": 1, "max": 200},
        "step": 1,
        "default": default,
        "unit_kind": UnitKind.COUNT,
        "ui": "ui-editable",
    }


def _legs(tag: str = "zone") -> list[dict[str, object]]:
    return [{"role": "level", "producer_binding": _pinned(tag)}]


def _ticket() -> object:
    return _ok(evaluate_ticket(layer1_passed=True, layer2_passed=True))


def _host() -> Registrar:
    registry = KindRegistry()
    _ok(install_bot_domain_kinds(registry))
    return Registrar(registry)


def _author(*, lookback: int = 20, tag: str = "zone") -> AuthoredStructure:
    authored = _ok(
        author_new_structure(
            strategy_family_id="trend-follow",
            confluence_legs=_legs(tag),
            parameter_space=[_int_param(lookback)],
            footprint=_footprint(tag),
            permitted_exit_intents=(),
            logic_source=_SOURCE,
        )
    )
    assert authored.bot is not None
    assert authored.confluence is not None
    assert authored.logic is not None
    return authored


def test_search_and_generation_are_different_acts() -> None:
    assert ACT_SEARCH == "search"
    assert ACT_GENERATION == "generation"
    assert ActKind.SEARCH is not ActKind.GENERATION
    assert QMB_AUTHORS_CANDIDATES is False
    assert QMB_RUNS_CANDIDATES is True
    assert HOST_MINTS_CT06_ENVELOPE is True
    assert GENERATOR_ALGORITHM_UNRULED is True
    assert RANDOM_CONDITION_DONOR_SHAPE == "donor-shape-not-schema"


def test_parameter_search_cites_the_same_bot_fp1() -> None:
    bot_fp = _ok(fingerprint({"class": "bot", "id": "one"}))
    classified = classify_parameter_search(
        bot_fp1=bot_fp,
        trial_bot_fp1s=(bot_fp, bot_fp.value, bot_fp),
    )
    assert _ok(classified) is ActKind.SEARCH


def test_parameter_search_refuses_a_new_bot_fp1() -> None:
    first = _ok(fingerprint({"class": "bot", "id": "one"}))
    second = _ok(fingerprint({"class": "bot", "id": "two"}))
    refused = classify_parameter_search(bot_fp1=first, trial_bot_fp1s=(first, second))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["act"] == ACT_SEARCH


def test_qml_authors_new_ct33_ct34_and_logic_bytes() -> None:
    authored = _author(lookback=20, tag="zone")
    assert authored.act is ActKind.GENERATION
    assert authored.confluence is not None
    assert authored.logic is not None
    assert authored.bot is not None
    bot = authored.bot
    logic = authored.logic
    bot_fp = _ok(bot.fingerprint_content())
    other = _author(lookback=21, tag="zone")
    assert other.bot is not None
    other_fp = _ok(other.bot.fingerprint_content())
    assert bot_fp != other_fp
    logic_fp = logic.source_manifest
    changed_logic = _ok(
        author_new_structure(
            strategy_family_id="trend-follow",
            confluence_legs=_legs("zone"),
            parameter_space=[_int_param(20)],
            footprint=_footprint("zone"),
            logic_source={
                "research_bot/__init__.py": "",
                "research_bot/bot.py": "def on_instant(self, instant):\n    return (1,)\n",
            },
        )
    )
    assert changed_logic.logic is not None
    assert changed_logic.logic.source_manifest != logic_fp


def test_host_mints_ct06_envelope_and_qmb_does_not_author() -> None:
    authored = _author()
    assert authored.bot is not None
    registrar = _host()
    minted = _ok(
        mint_generation_envelope(
            authored,
            registrar=registrar,
            created_at=_instant(),
            ticket=_ticket(),
            bot_writer=_writer("bot-definition"),
            confluence_writer=_writer("confluence"),
        )
    )
    assert minted.qmb_authors is False
    assert minted.host_mints_envelope is True
    assert minted.confluence is not None
    assert minted.bot is not None
    assert minted.bot.record.kind == KIND_BOT_DEFINITION
    assert minted.bot_fp1() == minted.bot.record.stable_id
    assert "writer" not in authored.bot.identity_payload()
    assert minted.bot.record.writer.role == "authoring"
    envelope = _ok(
        mint_ct06_envelope(
            kind=KIND_BOT_DEFINITION,
            body=authored.bot,
            registrar=registrar,
            writer=_writer("bot-definition", "node-b"),
            sequence=1,
            created_at=_instant(_CREATED_NS + 1),
            ticket=_ticket(),
        )
    )
    assert envelope.record.stable_id == minted.bot.record.stable_id


def test_bot_kind_envelope_without_ticket_is_policy_rejection() -> None:
    authored = _author()
    assert authored.bot is not None
    registrar = _host()
    refused = register_bot_definition(
        authored.bot,
        registrar=registrar,
        writer=_writer("bot-definition"),
        sequence=0,
        created_at=_instant(),
        ticket=None,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "ticket"


def test_declaration_surface_still_has_no_bot_kind_install_register() -> None:
    import qml.declaration
    import qml.declaration.bot

    for module in (qml.declaration, qml.declaration.bot):
        assert not hasattr(module, "install_bot_definition_kind")
        assert not hasattr(module, "register_bot_definition")
    assert hasattr(host, "register_bot_definition")
    assert hasattr(host, "install_bot_definition_kind")


def test_identical_content_is_not_generation() -> None:
    first = _author()
    assert first.bot is not None
    parent = _ok(first.bot.fingerprint_content())
    refused = author_new_structure(
        strategy_family_id="trend-follow",
        confluence_legs=_legs("zone"),
        parameter_space=[_int_param(20)],
        footprint=_footprint("zone"),
        logic_source=_SOURCE,
        parent_bot_fp1=parent,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "parent_bot_fp1"


def test_qml_dsl_revival_is_refused() -> None:
    refused = refuse_qml_dsl(".qml")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    authored = author_new_structure(dsl="qml")
    assert is_refusal(authored)
    source = author_new_structure(
        logic_source={"bot.qml": "entry when close > open"},
    )
    assert is_refusal(source)
    assert source.context["field"] == "dsl"


def test_random_condition_schema_is_refused_as_donor_shape() -> None:
    refused = refuse_random_condition_schema({"slots": []})
    assert is_refusal(refused)
    assert refused.context["donor_shape"] == RANDOM_CONDITION_DONOR_SHAPE
    authored = author_new_structure(
        confluence_legs=[
            {
                "role": "level",
                "producer_binding": _pinned("zone"),
                "RandomCondition": {"min": 1, "max": 5},
            }
        ]
    )
    assert is_refusal(authored)
    assert authored.context["field"] == "random_condition"


def test_gap_0085_nouns_and_gap_0063_algorithm_stay_unfilled() -> None:
    nouns = refuse_gap_0085_nouns({"EntryMechanism": {"kind": "breakout"}})
    assert is_refusal(nouns)
    assert nouns.context["field"] == "mechanisms"
    authored = author_new_structure(
        confluence_legs=_legs(),
        mechanisms={"ExitMechanism": {}},
    )
    assert is_refusal(authored)
    algorithm = refuse_generator_algorithm("placeholder-fill")
    assert is_refusal(algorithm)
    assert algorithm.context["unruled"] is True
    choice = author_new_structure(
        confluence_legs=_legs(),
        algorithm="python-logic-synthesis",
    )
    assert is_refusal(choice)
    assert choice.context["field"] == "algorithm"
    no_code = refuse_no_code_authoring(True)
    assert is_refusal(no_code)
    refused_no_code = author_new_structure(no_code=True)
    assert is_refusal(refused_no_code)
    assert refused_no_code.context["field"] == "no_code"


def test_qmb_has_no_generator_module() -> None:
    assert "generate" not in FORBIDDEN_QMB_GENERATOR_NAMES
    names: list[str] = []
    for path in _QMB_SRC.rglob("*"):
        if any(part in {".git", "__pycache__", ".venv"} for part in path.parts):
            continue
        names.append(path.stem if path.is_file() else path.name)
    hits = _ok(forbidden_generator_module_hits(names))
    assert hits == ()
    assert _ok(forbidden_generator_module_hits(("optimize", "sweep", "generate"))) == ()
    assert _ok(forbidden_generator_module_hits(("generator", "random_condition"))) == (
        "generator",
        "random_condition",
    )


def test_qma_does_not_assemble_ct33() -> None:
    qma_src = _REPO / "qmx-agents" / "packages" / "qma-core" / "src"
    forbidden = (
        "mint_bot_definition",
        "mint_confluence",
        "register_bot_definition",
        "author_new_structure",
    )
    hits: list[str] = []
    for path in qma_src.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                hits.append(f"{path}: {token}")
    assert hits == []


def test_host_stamped_generation_records_are_not_stamped_by_qml_content() -> None:
    authored = _author()
    assert authored.bot is not None
    payload = authored.bot.identity_payload()
    assert "writer" not in payload
    assert "sequence" not in payload
    assert "created_at" not in payload
    assert not isinstance(authored.bot, RegistrationRecord)
    assert qml.__version__ not in str(payload)
