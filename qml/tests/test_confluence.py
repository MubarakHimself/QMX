"""Story 11.5 — CT-34 confluence kind (QL-5)."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from qmf.core.chrono import CalendarIdentity, Instant, WriterId
from qmf.core.exact import ExactRational, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import FieldSetKind, KindRegistry, Registrar, RegistrationRecord
from qml.declaration import (
    CONFLUENCE_KIND_FORMAT_VERSION,
    FORBIDDEN_CONDITION_FIELDS,
    KIND_CONFLUENCE,
    LEG_ROLES,
    AuthoredArtifact,
    AuthoredKind,
    ConfluenceOrdering,
    LegRole,
    confluence_kind_contract,
    install_confluence_kind,
    mint_confluence,
    parse_leg_role,
    register_confluence,
    resolve_confluence_at_layer1,
)
from qml.footprint import (
    ProducerBinding,
    mint_footprint,
    mint_producer_template,
    report_completeness,
)

import qml

_REPO = Path(__file__).resolve().parents[2]
_CREATED_NS = 1_700_000_000_000_000_000

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _writer(machine: str = "node-a") -> WriterId:
    return _ok(WriterId.try_create(machine, "authoring", KIND_CONFLUENCE, "boot-1"))


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _registrar() -> Registrar:
    registry = KindRegistry()
    assert is_ok(install_confluence_kind(registry))
    return Registrar(registry)


def _period(n: int = 20) -> ExactRational:
    return _ok(ExactRational.try_create(n, 1, UnitKind.COUNT))


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "test-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _leg(
    role: str = "level",
    *,
    tag: str = "sma",
    binding: ProducerBinding | None = None,
    confluence_ref: object = None,
    declared_parameters: object = None,
    display_ordinal: object = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"role": role}
    if binding is not None:
        payload["producer_binding"] = binding
    elif confluence_ref is None:
        payload["producer_binding"] = _pinned(tag)
    if confluence_ref is not None:
        payload["confluence_ref"] = confluence_ref
    if declared_parameters is not None:
        payload["declared_parameters"] = declared_parameters
    if display_ordinal is not None:
        payload["display_ordinal"] = display_ordinal
    return payload


def _template_fields(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "formula_id": "sma",
        "contract_format_version": 1,
        "inputs": [
            {
                "name": "close",
                "source": {"kind": "instrument", "venue": "venue-ic", "symbol": "EURUSD"},
                "bar_spec": {"kind": "time-interval", "seconds": 60},
                "channel_kind": "exact-price",
                "quote_side": "mid",
            }
        ],
        "calendar_requirements": [_ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))],
        "alignment_policy": "as-of",
        "missing_value_policy": "mark-gap",
        "warm_up": 20,
        "output_schema": [
            {
                "name": "sma",
                "channel_kind": "float-analytic",
                "arity": "scalar-per-sample",
                "index_offset": 0,
            }
        ],
        "supported_modes": ["batch", "streaming"],
        "arithmetic_reference_configuration": {
            "c_library": "ta-lib-c@sha256:aaaa",
            "python_wrapper": "ta-lib-py@sha256:bbbb",
            "reference_configuration": {"compatibility_mode": "classic"},
        },
        "space_bound": {"period": "sma_period"},
    }
    fields.update(overrides)
    return fields


# --- AC: roles, one-or-more legs, unbounded counts ---------------------------


def test_kind_is_ct06_confluence_not_a_new_envelope() -> None:
    assert KIND_CONFLUENCE == "confluence"
    assert CONFLUENCE_KIND_FORMAT_VERSION == 1
    contract = _ok(confluence_kind_contract())
    assert isinstance(contract, FieldSetKind)
    assert contract.name == KIND_CONFLUENCE
    assert contract.contract_format_version == 1
    assert contract.required_fields == frozenset({"legs"})
    assert contract.optional_fields == frozenset({"order_significance"})
    ct06 = (_REPO / "docs" / "contracts" / "ct-06-registration.yaml").read_text(encoding="utf-8")
    assert "bot_domain_kinds: [bot-definition, confluence, strategy-family]" in ct06
    ct34 = (_REPO / "docs" / "contracts" / "ct-34-confluence.yaml").read_text(encoding="utf-8")
    assert "level | trigger | confirmation | filter" in ct34


def test_closed_role_vocabulary_is_level_trigger_confirmation_filter() -> None:
    assert frozenset({"level", "trigger", "confirmation", "filter"}) == LEG_ROLES
    for role in LEG_ROLES:
        parsed = parse_leg_role(role)
        assert is_ok(parsed)
        assert parsed.value.value == role
    assert _ok(parse_leg_role(LegRole.FILTER)) is LegRole.FILTER
    bad = parse_leg_role("feature")
    assert is_refusal(bad)
    assert bad.category is RefusalCategory.INVALID_INPUT
    assert is_refusal(parse_leg_role("exit"))
    assert is_refusal(parse_leg_role(None))


def test_one_or_more_legs_of_any_role_mix_and_zero_leg_is_invalid() -> None:
    trigger_only = _ok(mint_confluence([_leg("trigger", tag="break")]))
    assert trigger_only.legs[0].role is LegRole.TRIGGER
    filter_only = _ok(mint_confluence([_leg("filter", tag="news")]))
    assert filter_only.legs[0].role is LegRole.FILTER
    mixed = _ok(
        mint_confluence(
            [
                _leg("level", tag="zone"),
                _leg("trigger", tag="break"),
                _leg("confirmation", tag="close"),
                _leg("filter", tag="session"),
            ]
        )
    )
    assert [leg.role for leg in mixed.legs] == [
        LegRole.LEVEL,
        LegRole.TRIGGER,
        LegRole.CONFIRMATION,
        LegRole.FILTER,
    ]
    zero = mint_confluence([])
    assert is_refusal(zero)
    assert zero.category is RefusalCategory.INVALID_INPUT
    assert zero.context["field"] == "legs"


def test_leg_and_component_counts_are_never_bounded() -> None:
    twenty_levels = [_leg("level", tag=f"zone-{i}", display_ordinal=i) for i in range(20)]
    twenty_levels.append(_leg("trigger", tag="break", display_ordinal=20))
    minted = _ok(mint_confluence(twenty_levels))
    assert len(minted.legs) == 21
    assert sum(1 for leg in minted.legs if leg.role is LegRole.LEVEL) == 20


def test_missing_role_is_invalid_input() -> None:
    refused = mint_confluence([{"producer_binding": _pinned("sma")}])
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "role"


# --- AC: producer binding and/or child cite ----------------------------------


def test_leg_accepts_pinned_binding_template_child_cite_or_both() -> None:
    pinned = _ok(mint_confluence([_leg("level", binding=_pinned("sma"))]))
    assert pinned.legs[0].producer_binding is not None
    assert pinned.legs[0].confluence_ref is None

    template = _ok(mint_producer_template(_template_fields()))
    templated = _ok(mint_confluence([{"role": "trigger", "producer_binding": template}]))
    assert templated.legs[0].producer_binding is not None
    assert templated.legs[0].producer_binding.template is template

    child = _ok(mint_confluence([_leg("level", tag="child-zone")]))
    child_fp = _ok(child.fingerprint_content())
    cite_only = _ok(mint_confluence([{"role": "confirmation", "confluence_ref": child_fp}]))
    assert cite_only.legs[0].producer_binding is None
    assert cite_only.legs[0].confluence_ref == child_fp

    both = _ok(
        mint_confluence(
            [
                {
                    "role": "filter",
                    "producer_binding": _pinned("session"),
                    "confluence_ref": child_fp,
                }
            ]
        )
    )
    assert both.legs[0].producer_binding is not None
    assert both.legs[0].confluence_ref == child_fp


def test_neither_binding_nor_child_cite_is_invalid_input() -> None:
    refused = mint_confluence([{"role": "level"}])
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert "at least one" in str(refused.context["reason"])


def test_template_missing_identity_field_is_invalid_input() -> None:
    payload = _template_fields()
    del payload["warm_up"]
    refused = mint_confluence([{"role": "level", "producer_binding": payload}])
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "producer_binding"


def test_declared_parameters_are_exact_and_optional() -> None:
    with_params = _ok(
        mint_confluence(
            [
                _leg(
                    "level",
                    tag="zone",
                    declared_parameters={"lookback": _period(14)},
                )
            ]
        )
    )
    assert "lookback" in with_params.legs[0].declared_parameters
    without = _ok(mint_confluence([_leg("level", tag="zone")]))
    assert dict(without.legs[0].declared_parameters) == {}
    identity_legs = without.identity_legs()
    assert "declared_parameters" not in identity_legs[0]
    floated = mint_confluence([_leg("level", tag="zone", declared_parameters={"lookback": 1.5})])
    assert is_refusal(floated)
    assert floated.category is RefusalCategory.INVALID_INPUT


# --- AC: fingerprint-ascending default; order-significance opt-in ------------


def test_default_order_is_fingerprint_ascending_and_ordinals_stay_out() -> None:
    a = _pinned("aaa")
    z = _pinned("zzz")
    authored = _ok(
        mint_confluence(
            [
                _leg("trigger", binding=z, display_ordinal=0),
                _leg("level", binding=a, display_ordinal=1),
            ]
        )
    )
    assert authored.ordering is ConfluenceOrdering.FINGERPRINT_ASCENDING
    assert authored.order_significant is False
    body = authored.body()
    assert "order_significance" not in body
    canonical = authored.identity_legs()
    assert "display_ordinal" not in canonical[0]
    assert "display_ordinal" not in canonical[1]
    fp_first = _ok(fingerprint(canonical[0]))
    fp_second = _ok(fingerprint(canonical[1]))
    assert fp_first.value < fp_second.value
    assert authored.legs[0].display_ordinal == 0
    assert authored.legs[1].display_ordinal == 1
    reversed_input = _ok(
        mint_confluence(
            [
                _leg("level", binding=a, display_ordinal=5),
                _leg("trigger", binding=z, display_ordinal=9),
            ]
        )
    )
    assert _ok(authored.fingerprint_content()) == _ok(reversed_input.fingerprint_content())


def test_declared_order_significance_enters_the_fingerprint() -> None:
    a = _pinned("aaa")
    z = _pinned("zzz")
    legs = [
        _leg("trigger", binding=z, display_ordinal=0),
        _leg("level", binding=a, display_ordinal=1),
    ]
    default = _ok(mint_confluence(legs))
    significant = _ok(mint_confluence(legs, order_significance=True))
    assert significant.order_significant is True
    assert significant.body()["order_significance"] == "declared-order-significant"
    assert "display_ordinal" in significant.identity_legs()[0]
    assert _ok(default.fingerprint_content()) != _ok(significant.fingerprint_content())
    swapped = _ok(
        mint_confluence(
            [
                _leg("level", binding=a, display_ordinal=0),
                _leg("trigger", binding=z, display_ordinal=1),
            ],
            order_significance="declared-order-significant",
        )
    )
    assert _ok(significant.fingerprint_content()) != _ok(swapped.fingerprint_content())
    same_ordinals = _ok(
        mint_confluence(
            [
                _leg("level", binding=a, display_ordinal=1),
                _leg("trigger", binding=z, display_ordinal=0),
            ],
            order_significance=True,
        )
    )
    assert _ok(same_ordinals.fingerprint_content()) == _ok(significant.fingerprint_content())


def test_unknown_contract_format_version_is_unsupported_capability() -> None:
    refused = mint_confluence([_leg()], format_version=2)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    zero = mint_confluence([_leg()], format_version=0)
    assert is_refusal(zero)
    assert zero.category is RefusalCategory.INVALID_INPUT
    flag = mint_confluence([_leg()], format_version=True)
    assert is_refusal(flag)
    assert flag.category is RefusalCategory.INVALID_INPUT


# --- AC: reuse mints no new confluence; content changes do -------------------


def test_same_content_reused_across_bots_mints_no_new_confluence() -> None:
    content = _ok(mint_confluence([_leg("level", tag="zone"), _leg("trigger", tag="break")]))
    again = _ok(mint_confluence([_leg("trigger", tag="break"), _leg("level", tag="zone")]))
    fp = _ok(content.fingerprint_content())
    assert fp == _ok(again.fingerprint_content())
    via_core = _ok(fingerprint(content.identity_payload()))
    assert fp == via_core
    assert fp.value.startswith("fp1:sha256:")
    payload = content.identity_payload()
    assert payload["kind"] == KIND_CONFLUENCE
    assert "writer" not in payload
    assert "sequence" not in payload
    assert "created_at" not in payload
    assert qml.__version__ not in payload.values()
    bot_a = _ok(
        AuthoredArtifact.try_create(
            AuthoredKind.BOT_DEFINITION, 1, {"confluence_set": [fp.value], "family": "a"}
        )
    )
    bot_b = _ok(
        AuthoredArtifact.try_create(
            AuthoredKind.BOT_DEFINITION, 1, {"confluence_set": [fp.value], "family": "b"}
        )
    )
    assert _ok(fingerprint(bot_a.identity_payload())) != _ok(fingerprint(bot_b.identity_payload()))
    reused = _ok(mint_confluence(content.completeness_legs()))
    assert _ok(reused.fingerprint_content()) == fp


def test_changed_leg_role_binding_parameter_cite_or_order_mints_new_fp() -> None:
    base = _ok(mint_confluence([_leg("level", tag="zone")]))
    base_fp = _ok(base.fingerprint_content())
    role = _ok(mint_confluence([_leg("trigger", tag="zone")]))
    assert _ok(role.fingerprint_content()) != base_fp
    binding = _ok(mint_confluence([_leg("level", tag="other")]))
    assert _ok(binding.fingerprint_content()) != base_fp
    params = _ok(
        mint_confluence([_leg("level", tag="zone", declared_parameters={"n": _period(3)})])
    )
    assert _ok(params.fingerprint_content()) != base_fp
    child = _ok(mint_confluence([_leg("filter", tag="child")]))
    child_fp = _ok(child.fingerprint_content())
    cited = _ok(
        mint_confluence(
            [
                {
                    "role": "level",
                    "producer_binding": _pinned("zone"),
                    "confluence_ref": child_fp,
                }
            ]
        )
    )
    assert _ok(cited.fingerprint_content()) != base_fp
    ordered = _ok(mint_confluence([_leg("level", tag="zone")], order_significance=True))
    assert _ok(ordered.fingerprint_content()) != base_fp


def test_host_stamped_records_deduplicate_across_sandboxes() -> None:
    legs = [_leg("level", tag="zone")]
    registrar = _registrar()
    a = _ok(
        register_confluence(
            legs,
            registrar=registrar,
            writer=_writer("node-a"),
            sequence=0,
            created_at=_instant(_CREATED_NS),
        )
    )
    b = _ok(
        register_confluence(
            legs,
            registrar=registrar,
            writer=_writer("node-b"),
            sequence=0,
            created_at=_instant(_CREATED_NS + 1_000),
        )
    )
    assert a.record.kind == KIND_CONFLUENCE
    assert a.record.stable_id == b.record.stable_id
    assert a.outcome.value == "stored"
    assert b.outcome.value == "idempotent"
    sandbox_a = _ok(
        RegistrationRecord.try_create(
            KIND_CONFLUENCE,
            1,
            [],
            _ok(mint_confluence(legs)).body(),
            _writer("node-a"),
            0,
            _instant(_CREATED_NS),
        )
    )
    sandbox_b = _ok(
        RegistrationRecord.try_create(
            KIND_CONFLUENCE,
            1,
            [],
            _ok(mint_confluence(legs)).body(),
            _writer("node-b"),
            99,
            _instant(_CREATED_NS + 500),
        )
    )
    assert sandbox_a.writer != sandbox_b.writer
    assert sandbox_a.created_at != sandbox_b.created_at
    assert sandbox_a.stable_id == sandbox_b.stable_id
    assert not isinstance(_ok(mint_confluence(legs)), RegistrationRecord)


# --- AC: invalid role / missing cite; unresolvable is unavailable ------------


def test_role_outside_vocabulary_is_invalid_input() -> None:
    refused = mint_confluence([_leg("feature", tag="sma")])
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "role"


def test_condition_semantics_are_not_declaration_surface() -> None:
    stuffed = mint_confluence(
        [{"role": "filter", "producer_binding": _pinned("sma"), "when": "close > sma"}]
    )
    assert is_refusal(stuffed)
    assert stuffed.category is RefusalCategory.INVALID_INPUT
    assert stuffed.context["forbidden"] == ("when",)
    assert "when" in FORBIDDEN_CONDITION_FIELDS
    top = mint_confluence({"legs": [_leg()], "predicate": "always"})
    assert is_refusal(top)
    assert top.category is RefusalCategory.INVALID_INPUT


def test_unresolvable_producer_fingerprint_is_unavailable_dependency() -> None:
    binding = _pinned("sma")
    confluence = _ok(mint_confluence([_leg("level", binding=binding)]))
    found = resolve_confluence_at_layer1(confluence, (), producer_catalog=[binding])
    assert is_ok(found)
    missing = resolve_confluence_at_layer1(confluence, (), producer_catalog=())
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert missing.context["journal"] is True
    assert missing.context["field"] == "producer_binding"


def test_unresolvable_child_confluence_is_unavailable_dependency() -> None:
    child = _ok(mint_confluence([_leg("level", tag="child")]))
    child_fp = _ok(child.fingerprint_content())
    child_binding = child.legs[0].producer_binding
    assert child_binding is not None
    parent = _ok(
        mint_confluence(
            [
                {
                    "role": "trigger",
                    "producer_binding": _pinned("parent"),
                    "confluence_ref": child_fp,
                }
            ]
        )
    )
    parent_binding = parent.legs[0].producer_binding
    assert parent_binding is not None
    resolved = resolve_confluence_at_layer1(
        parent,
        [child],
        producer_catalog=[parent_binding, child_binding],
    )
    assert is_ok(resolved)
    missing = resolve_confluence_at_layer1(parent, (), producer_catalog=[parent_binding])
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert missing.context["field"] == "confluence_ref"
    assert missing.context["journal"] is True
    by_fp = resolve_confluence_at_layer1(child_fp, [child], producer_catalog=[child_binding])
    assert is_ok(by_fp)
    unknown_fp = _ok(fingerprint({"class": "missing-confluence"}))
    miss_fp = resolve_confluence_at_layer1(unknown_fp, [child], producer_catalog=[child_binding])
    assert is_refusal(miss_fp)
    assert miss_fp.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_cyclic_composition_is_invalid_input() -> None:
    alias_a = _ok(fingerprint({"class": "cycle-alias", "id": "a"}))
    alias_b = _ok(fingerprint({"class": "cycle-alias", "id": "b"}))
    conf_a = _ok(mint_confluence([{"role": "level", "confluence_ref": alias_b}]))
    conf_b = _ok(mint_confluence([{"role": "trigger", "confluence_ref": alias_a}]))
    catalog = {alias_a.value: conf_a, alias_b.value: conf_b}
    cycled = resolve_confluence_at_layer1(conf_a, catalog, producer_catalog=())
    assert is_refusal(cycled)
    assert cycled.category is RefusalCategory.INVALID_INPUT


def test_malformed_child_ref_is_invalid_input() -> None:
    refused = mint_confluence([{"role": "level", "confluence_ref": "child-conf"}])
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "confluence_ref"


def test_completeness_walker_accepts_typed_confluence_legs() -> None:
    calendar = _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))
    confluence = _ok(mint_confluence([_leg("level", tag="zone")]))
    binding = confluence.legs[0].producer_binding
    assert binding is not None
    footprint = _ok(
        mint_footprint(
            [
                {
                    "instrument_role": "primary",
                    "bar_specs": [{"kind": "time-interval", "seconds": 60}],
                    "stream_role": "trading",
                }
            ],
            [calendar],
            [binding],
        )
    )
    report = _ok(report_completeness(footprint, confluence.completeness_legs()))
    assert report.complete is True


def test_install_kind_refuses_a_non_registry_and_a_redefinition() -> None:
    assert is_refusal(install_confluence_kind("nope"))
    registry = KindRegistry()
    assert is_ok(install_confluence_kind(registry))
    again = install_confluence_kind(registry)
    assert is_refusal(again)


def test_duplicate_display_ordinals_are_invalid() -> None:
    refused = mint_confluence(
        [
            _leg("level", tag="a", display_ordinal=0),
            _leg("trigger", tag="b", display_ordinal=0),
        ]
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_qml_adds_no_registry_configurable_row() -> None:
    text = (_REPO / "docs" / "registry" / "variables.yaml").read_text(encoding="utf-8")
    assert "name: qml_" not in text
    assert "component: COMP-QML" not in text
