"""Story 11.6 — CT-33 Bot definition with identity carve-out and versioning."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from qmf.core.chrono import CalendarIdentity, Instant, WriterId
from qmf.core.exact import ExactRational, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import FieldSetKind, KindRegistry, Registrar, RegistrationRecord
from qmf.risk.door import ExitKind
from qml.declaration import (
    BOT_DEFINITION_KIND_FORMAT_VERSION,
    FORBIDDEN_BOT_FIELDS,
    KIND_BOT_DEFINITION,
    PARAMETER_TYPES,
    PERMITTED_EXIT_INTENT_VOCABULARY,
    BotDefinition,
    BotVersionGraph,
    Confluence,
    ParameterType,
    bot_definition_kind_contract,
    branches_from_edge,
    continues_performance_edge,
    install_bot_definition_kind,
    mint_bot_definition,
    mint_confluence,
    parse_parameter_type,
    promote_tuned_assignment,
    register_bot_definition,
)
from qml.footprint import Footprint, ProducerBinding, mint_footprint
from qml.logic import LogicIdentity, mint_logic_identity

import qml

_REPO = Path(__file__).resolve().parents[2]
_CREATED_NS = 1_700_000_000_000_000_000
_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, instant):\n    return ()\n",
}

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _writer(machine: str = "node-a") -> WriterId:
    return _ok(WriterId.try_create(machine, "authoring", KIND_BOT_DEFINITION, "boot-1"))


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _registrar() -> Registrar:
    registry = KindRegistry()
    assert is_ok(install_bot_definition_kind(registry))
    return Registrar(registry)


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "test-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _calendar() -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))


def _footprint(tag: str = "sma") -> Footprint:
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


def _logic(source: dict[str, str] | None = None, *, version: str = "1.0.0") -> LogicIdentity:
    return _ok(
        mint_logic_identity("research-bot", version, source if source is not None else _SOURCE)
    )


def _confluence(tag: str = "zone") -> Confluence:
    return _ok(mint_confluence([{"role": "level", "producer_binding": _pinned(tag)}]))


def _int_param(
    name: str = "lookback",
    *,
    default: int = 20,
    minimum: int = 1,
    maximum: int = 200,
    step: int = 1,
) -> dict[str, object]:
    return {
        "name": name,
        "type": "exact integer",
        "bounds": {"min": minimum, "max": maximum},
        "step": step,
        "default": default,
        "unit_kind": UnitKind.COUNT,
        "ui": "ui-editable",
    }


def _bot_kwargs(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "strategy_family_id": "trend-follow",
        "confluence_set": [_confluence()],
        "parameter_space": [_int_param()],
        "footprint": _footprint(),
        "permitted_exit_intents": (),
        "logic_reference": _logic(),
    }
    fields.update(overrides)
    return fields


def _mint(**overrides: object) -> Result[BotDefinition]:
    return mint_bot_definition(**_bot_kwargs(**overrides))


# --- AC: fp1 identity carve-out ---------------------------------------------


def test_kind_is_ct06_bot_definition_filling_reserved_bot_kind() -> None:
    assert KIND_BOT_DEFINITION == "bot-definition"
    assert BOT_DEFINITION_KIND_FORMAT_VERSION == 1
    contract = _ok(bot_definition_kind_contract())
    assert isinstance(contract, FieldSetKind)
    assert contract.name == KIND_BOT_DEFINITION
    assert contract.required_fields == frozenset(
        {
            "strategy_family_id",
            "confluence_set",
            "parameter_space",
            "footprint",
            "permitted_exit_intents",
            "logic_reference",
        }
    )
    ct06 = (_REPO / "docs" / "contracts" / "ct-06-registration.yaml").read_text(encoding="utf-8")
    assert "bot_domain_kinds: [bot-definition, confluence, strategy-family]" in ct06
    ct33 = (_REPO / "docs" / "contracts" / "ct-33-bot-definition.yaml").read_text(encoding="utf-8")
    assert "EXCLUDED from `fp1`" in ct33


def test_fp1_excludes_ad16_header_and_is_six_groups_plus_refs() -> None:
    parent = _ok(fingerprint({"class": "at-birth"}))
    authored = _ok(_mint(at_birth_parent_refs=[parent]))
    payload = authored.identity_payload()
    assert payload["kind"] == KIND_BOT_DEFINITION
    assert payload["contract_format_version"] == 1
    assert payload["at_birth_parent_refs"] == [parent.value]
    body = authored.body()
    assert set(body) == {
        "strategy_family_id",
        "confluence_set",
        "parameter_space",
        "footprint",
        "permitted_exit_intents",
        "logic_reference",
    }
    assert "writer" not in payload
    assert "sequence" not in payload
    assert "stable_id" not in payload
    assert "created_at" not in payload
    assert "canonical_assignment" not in body
    assert "exit_logic" not in body
    assert qml.__version__ not in payload.values()
    fp = _ok(authored.fingerprint_content())
    via_core = _ok(fingerprint(payload))
    assert fp == via_core
    assert fp.value.startswith("fp1:sha256:")
    without_refs = _ok(_mint())
    assert "at_birth_parent_refs" not in without_refs.identity_payload()
    assert _ok(without_refs.fingerprint_content()) != fp


def test_header_fields_on_the_mapping_are_invalid_input() -> None:
    refused = mint_bot_definition({**_bot_kwargs(), "writer": "node-a", "sequence": 0})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    forbidden = refused.context["forbidden"]
    assert isinstance(forbidden, tuple)
    assert "writer" in forbidden
    stamped = mint_bot_definition({**_bot_kwargs(), "created_at": _CREATED_NS, "stable_id": "x"})
    assert is_refusal(stamped)
    assert stamped.category is RefusalCategory.INVALID_INPUT


# --- AC: parameter space + canonical assignment -----------------------------


def test_parameter_types_are_the_closed_b8_set() -> None:
    assert frozenset({"exact integer", "exact rational", "categorical", "boolean"}) == (
        PARAMETER_TYPES
    )
    for token in PARAMETER_TYPES:
        parsed = parse_parameter_type(token)
        assert is_ok(parsed)
        assert parsed.value.value == token
    assert _ok(parse_parameter_type(ParameterType.BOOLEAN)) is ParameterType.BOOLEAN
    bad = parse_parameter_type("float")
    assert is_refusal(bad)
    assert bad.category is RefusalCategory.INVALID_INPUT


def test_each_parameter_carries_type_bounds_step_default_filter_and_unit_kind() -> None:
    lookback = _ok(ExactRational.try_create(1, 2, UnitKind.DIMENSIONLESS_RATIO))
    ceiling = _ok(ExactRational.try_create(2, 1, UnitKind.DIMENSIONLESS_RATIO))
    step = _ok(ExactRational.try_create(1, 2, UnitKind.DIMENSIONLESS_RATIO))
    authored = _ok(
        _mint(
            parameter_space=[
                _int_param(),
                {
                    "name": "threshold",
                    "type": "exact rational",
                    "bounds": {"min": lookback, "max": ceiling},
                    "step": step,
                    "default": lookback,
                    "unit_kind": UnitKind.DIMENSIONLESS_RATIO,
                    "ui": "ui-editable",
                    "hard_constraint": {
                        "measure_identity": "drawdown",
                        "op": "<=",
                        "value": 3,
                    },
                },
                {
                    "name": "session",
                    "type": "categorical",
                    "bounds": ["london", "ny"],
                    "default": "london",
                    "unit_kind": UnitKind.DIMENSIONLESS_RATIO,
                    "ui": "uneditable",
                },
                {
                    "name": "use_filter",
                    "type": "boolean",
                    "default": True,
                    "unit_kind": UnitKind.DIMENSIONLESS_RATIO,
                    "ui": "ui-editable",
                },
            ]
        )
    )
    names = [spec.name for spec in authored.parameter_space]
    assert names == ["lookback", "session", "threshold", "use_filter"]
    assignment = dict(authored.canonical_assignment())
    assert assignment["lookback"] == 20
    assert assignment["session"] == "london"
    assert assignment["use_filter"] is True
    assert "canonical_assignment" not in authored.body()
    assert authored.parameter_space[2].hard_constraint is not None


def test_missing_unit_kind_or_default_is_invalid_input() -> None:
    missing_kind = _mint(
        parameter_space=[
            {
                "name": "lookback",
                "type": "exact integer",
                "bounds": {"min": 1, "max": 10},
                "step": 1,
                "default": 2,
                "ui": "ui-editable",
            }
        ]
    )
    assert is_refusal(missing_kind)
    assert missing_kind.category is RefusalCategory.INVALID_INPUT
    assert missing_kind.context["field"] == "unit_kind"
    missing_default = _mint(
        parameter_space=[
            {
                "name": "lookback",
                "type": "exact integer",
                "bounds": {"min": 1, "max": 10},
                "step": 1,
                "unit_kind": "count",
                "ui": "ui-editable",
            }
        ]
    )
    assert is_refusal(missing_default)
    assert missing_default.context["field"] == "default"
    floated = _mint(
        parameter_space=[
            {
                "name": "lookback",
                "type": "exact integer",
                "bounds": {"min": 1, "max": 10},
                "step": 1,
                "default": 1.5,
                "unit_kind": "count",
                "ui": "ui-editable",
            }
        ]
    )
    assert is_refusal(floated)
    assert floated.category is RefusalCategory.INVALID_INPUT


def test_canonical_assignment_is_derived_not_declared() -> None:
    declared = mint_bot_definition({**_bot_kwargs(), "canonical_assignment": {"lookback": 20}})
    assert is_refusal(declared)
    assert declared.category is RefusalCategory.INVALID_INPUT
    assert declared.context["field"] == "canonical_assignment"
    authored = _ok(_mint())
    assert dict(authored.canonical_assignment()) == {"lookback": 20}


# --- AC: family cardinality and confluence set ------------------------------


def test_zero_or_more_than_one_family_id_is_invalid_input() -> None:
    zero = _mint(strategy_family_id=None)
    assert is_refusal(zero)
    assert zero.category is RefusalCategory.INVALID_INPUT
    assert zero.context["field"] == "strategy_family_id"
    empty = _mint(strategy_family_id=[])
    assert is_refusal(empty)
    assert empty.context["field"] == "strategy_family_id"
    two = _mint(strategy_family_id=["trend-follow", "mean-revert"])
    assert is_refusal(two)
    assert two.context["field"] == "strategy_family_id"
    one = _ok(_mint(strategy_family_id="trend-follow"))
    assert one.strategy_family_id.value == "trend-follow"


def test_confluence_set_is_one_or_more_ordered_by_fingerprint_ascending() -> None:
    a = _confluence("aaa")
    z = _confluence("zzz")
    authored = _ok(
        _mint(
            confluence_set=[
                {"fingerprint": z, "display_ordinal": 0},
                {"fingerprint": a, "display_ordinal": 1},
            ]
        )
    )
    ordered = [cite.fingerprint.value for cite in authored.canonical_confluence_set()]
    assert ordered == sorted(ordered)
    assert authored.confluence_set[0].display_ordinal == 0
    assert "display_ordinal" not in str(authored.body())
    reversed_input = _ok(
        _mint(
            confluence_set=[
                {"fingerprint": a, "display_ordinal": 9},
                {"fingerprint": z, "display_ordinal": 3},
            ]
        )
    )
    assert _ok(authored.fingerprint_content()) == _ok(reversed_input.fingerprint_content())
    zero = _mint(confluence_set=[])
    assert is_refusal(zero)
    assert zero.category is RefusalCategory.INVALID_INPUT
    assert zero.context["field"] == "confluence_set"


# --- AC: permitted exit intents; no sizing / venue / exit-logic -------------


def test_permitted_exit_intents_are_a_possibly_empty_ct23_subset() -> None:
    assert frozenset({"close_full", "tighten_protective_stop"}) == PERMITTED_EXIT_INTENT_VOCABULARY
    empty = _ok(_mint(permitted_exit_intents=()))
    assert empty.permitted_exit_intents == ()
    both = _ok(
        _mint(
            permitted_exit_intents=(
                ExitKind.TIGHTEN_PROTECTIVE_STOP,
                "close_full",
            )
        )
    )
    assert both.permitted_exit_intents == ("close_full", "tighten_protective_stop")
    entry = _mint(permitted_exit_intents=("entry",))
    assert is_refusal(entry)
    assert entry.category is RefusalCategory.INVALID_INPUT
    partial = _mint(permitted_exit_intents=("close_partial",))
    assert is_refusal(partial)
    assert partial.category is RefusalCategory.INVALID_INPUT


def test_sizing_venue_and_exit_logic_fields_are_invalid_input() -> None:
    for field in ("exit_logic", "requested_r", "sizing", "venue_command"):
        refused = mint_bot_definition({**_bot_kwargs(), field: "nope"})
        assert is_refusal(refused), field
        assert refused.category is RefusalCategory.INVALID_INPUT
        assert field in FORBIDDEN_BOT_FIELDS
    assert "exit_logic" not in _ok(_mint()).body()


# --- AC: AD-30 versioning ---------------------------------------------------


def test_branches_from_graph_allows_multiple_heads_and_dated_current() -> None:
    root = _ok(_mint())
    tuned = _ok(promote_tuned_assignment(root, {"lookback": 14}))
    other = _ok(_mint(parameter_space=[_int_param(default=30)]))
    root_fp = _ok(root.fingerprint_content())
    tuned_fp = _ok(tuned.fingerprint_content())
    other_fp = _ok(other.fingerprint_content())
    assert tuned_fp != root_fp
    graph = BotVersionGraph()
    assert is_ok(graph.append_version(root_fp))
    assert is_ok(graph.append_version(tuned_fp, branches_from=root_fp))
    assert is_ok(graph.append_version(other_fp, branches_from=root_fp))
    assert set(graph.heads()) == {tuned_fp, other_fp}
    assert graph.parent_of(tuned_fp) == root_fp
    assert graph.current() is None
    assert is_ok(graph.set_current(root_fp, _instant()))
    assert graph.current() == root_fp
    assert is_ok(graph.set_current(tuned_fp, _instant(_CREATED_NS + 1)))
    assert graph.current() == tuned_fp
    assert len(graph.pointer_history()) == 2
    assert graph.is_readable(root_fp) is True
    edge = _ok(branches_from_edge(child=tuned_fp, parent=root_fp, writer=_writer()))
    assert edge.edge_type.value == "branches-from"


def test_changed_default_confluence_footprint_or_logic_mints_new_bot() -> None:
    base = _ok(_mint())
    base_fp = _ok(base.fingerprint_content())
    defaulted = _ok(_mint(parameter_space=[_int_param(default=14)]))
    assert _ok(defaulted.fingerprint_content()) != base_fp
    other_conf = _ok(_mint(confluence_set=[_confluence("other")]))
    assert _ok(other_conf.fingerprint_content()) != base_fp
    other_foot = _ok(_mint(footprint=_footprint("other")))
    assert _ok(other_foot.fingerprint_content()) != base_fp
    other_logic = _ok(
        _mint(
            logic_reference=_logic(
                {**_SOURCE, "research_bot/bot.py": "def on_instant(self, instant):\n    return 1\n"}
            )
        )
    )
    assert _ok(other_logic.fingerprint_content()) != base_fp


def test_rebinding_seats_and_paper_never_mint_a_new_bot() -> None:
    authored = _ok(_mint())
    fp = _ok(authored.fingerprint_content())
    again = _ok(_mint())
    assert _ok(again.fingerprint_content()) == fp
    for field in ("seat", "binding", "paper_mode", "rebinding"):
        refused = mint_bot_definition({**_bot_kwargs(), field: "epoch-1"})
        assert is_refusal(refused), field
        assert refused.category is RefusalCategory.INVALID_INPUT
    unsigned = continues_performance_edge(
        child=fp,
        parent=fp,
        writer=_writer(),
        human_signed=False,
    )
    assert is_refusal(unsigned)
    assert unsigned.category is RefusalCategory.POLICY_REJECTION
    parent = _ok(_mint(parameter_space=[_int_param(default=14)]))
    signed = _ok(
        continues_performance_edge(
            child=_ok(authored.fingerprint_content()),
            parent=_ok(parent.fingerprint_content()),
            writer=_writer(),
            human_signed=True,
        )
    )
    assert signed.edge_type.value == "continues-performance"


# --- AC: qml returns fingerprintable content, host stamps -------------------


def test_mint_returns_fingerprintable_content_never_a_stamped_record() -> None:
    made = _ok(_mint())
    assert not isinstance(made, RegistrationRecord)
    payload = made.identity_payload()
    assert "writer" not in payload
    assert "sequence" not in payload
    assert "created_at" not in payload


def test_host_stamped_records_deduplicate_across_sandboxes() -> None:
    registrar = _registrar()
    payload = _bot_kwargs()
    a = _ok(
        register_bot_definition(
            payload,
            registrar=registrar,
            writer=_writer("node-a"),
            sequence=0,
            created_at=_instant(_CREATED_NS),
        )
    )
    b = _ok(
        register_bot_definition(
            payload,
            registrar=registrar,
            writer=_writer("node-b"),
            sequence=0,
            created_at=_instant(_CREATED_NS + 1_000),
        )
    )
    assert a.record.kind == KIND_BOT_DEFINITION
    assert a.record.stable_id == b.record.stable_id
    assert a.outcome.value == "stored"
    assert b.outcome.value == "idempotent"
    sandbox_a = _ok(
        RegistrationRecord.try_create(
            KIND_BOT_DEFINITION,
            1,
            [],
            _ok(_mint()).body(),
            _writer("node-a"),
            0,
            _instant(_CREATED_NS),
        )
    )
    sandbox_b = _ok(
        RegistrationRecord.try_create(
            KIND_BOT_DEFINITION,
            1,
            [],
            _ok(_mint()).body(),
            _writer("node-b"),
            99,
            _instant(_CREATED_NS + 500),
        )
    )
    assert sandbox_a.writer != sandbox_b.writer
    assert sandbox_a.created_at != sandbox_b.created_at
    assert sandbox_a.stable_id == sandbox_b.stable_id
    assert "writer" not in sandbox_a.fp1_identity()
    assert _writer().role == "authoring"
    assert _writer().stream == KIND_BOT_DEFINITION


def test_unknown_contract_format_version_is_unsupported_capability() -> None:
    refused = mint_bot_definition(_bot_kwargs(), format_version=2)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    zero = mint_bot_definition(_bot_kwargs(), format_version=0)
    assert is_refusal(zero)
    assert zero.category is RefusalCategory.INVALID_INPUT


def test_install_kind_refuses_a_non_registry_and_a_redefinition() -> None:
    assert is_refusal(install_bot_definition_kind("nope"))
    registry = KindRegistry()
    assert is_ok(install_bot_definition_kind(registry))
    again = install_bot_definition_kind(registry)
    assert is_refusal(again)


def test_qml_adds_no_registry_configurable_row() -> None:
    text = (_REPO / "docs" / "registry" / "variables.yaml").read_text(encoding="utf-8")
    assert "name: qml_" not in text
    assert "component: COMP-QML" not in text
