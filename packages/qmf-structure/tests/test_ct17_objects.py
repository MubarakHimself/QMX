"""Tier-1 tests for CT-17 Story 9.1: the structure object mint and the emission invariant.

Covers the acceptance criteria:

* the package versions in roster SemVer lockstep and its public value types are frozen
  dataclasses with a ``typing.Protocol`` seam, importing only qmf-core;
* an object is minted once at observation carrying family identity + version,
  exact-rational parameters, its confirmation rule, its anchor span (frozen, permitted
  to precede observed-at, excluded from the causal test), observed-at (known-at), and
  evidence class — every field identity-bearing, the object never mutated and never
  stamped;
* the in-component emission invariant requires
  ``anchor.start <= anchor.end <= observed_at <= confirmed_at <= invalidated_at`` and
  ``observed_at >= max consumed-input evidence time``, refusing a violation as
  ``invalid input`` (FM-1); and
* the library returns fingerprintable content (a derived ``fp1``), never a stamped
  record.
"""

from __future__ import annotations

from typing import TypeVar

import pytest
import qmf.structure
from qmf.core import (
    EvidenceClass,
    ExactRational,
    Fingerprint,
    Instant,
    Instrument,
    Ok,
    Price,
    Result,
    TypedRefusal,
    UnitKind,
    VenueId,
    fingerprint,
    is_ok,
)
from qmf.structure import (
    CONTRACT_FORMAT_VERSION,
    KNOWN_GEOMETRIES,
    AnchorSpan,
    ConfirmationRule,
    DeclaredFamily,
    EmissionWitness,
    FamilyIdentity,
    StructureFamily,
    StructureObject,
    check_emission_invariant,
)

T = TypeVar("T")

_EURUSD = Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")
_GBPUSD = Instrument(venue=VenueId(value="ctrader"), symbol="GBPUSD")

_T0 = 1_700_000_000_000_000_000
_MINUTE = 60_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), f"expected Ok, got {result}"
    assert isinstance(result, Ok)
    return result.value


def _price(value: int, instrument: Instrument = _EURUSD, scale: int = 5) -> Price:
    return _ok(Price.try_create(value, instrument, scale))


def _rational(num: int, den: int) -> ExactRational:
    return _ok(ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO))


def _family(
    family_id: str = "swing-point",
    version: int = 1,
    geometry: str = "point",
    *,
    descriptor: str = "confirmed the moment a later bar closes beyond the pivot",
    bound: int | None = 3,
) -> DeclaredFamily:
    identity = _ok(FamilyIdentity.try_create(family_id, version, geometry))
    rule = _ok(ConfirmationRule.try_create(descriptor, confirmation_delay_bound=bound))
    return _ok(DeclaredFamily.try_create(identity, rule))


def _anchor(
    start: int = _T0,
    end: int = _T0 + _MINUTE,
    low: int = 108_000,
    high: int = 108_500,
) -> AnchorSpan:
    return _ok(
        AnchorSpan.try_create(
            Instant(value_ns=start), Instant(value_ns=end), _price(low), _price(high)
        )
    )


# --- package scaffold / conventions -----------------------------------------


def test_version_is_semver_0x() -> None:
    assert qmf.structure.__version__ == "0.1.0"


def test_contract_format_version_is_one() -> None:
    assert CONTRACT_FORMAT_VERSION == 1


def test_known_geometries_are_the_seed_set() -> None:
    assert set(KNOWN_GEOMETRIES) == {"point", "level", "zone", "span", "distribution", "graph"}


def test_declared_family_satisfies_the_protocol_seam() -> None:
    assert isinstance(_family(), StructureFamily)


# --- FamilyIdentity ---------------------------------------------------------


def test_family_identity_carries_id_version_geometry() -> None:
    identity = _ok(FamilyIdentity.try_create("swing-point", 2, "point"))
    assert identity.family_id == "swing-point"
    assert identity.version == 2
    assert identity.geometry == "point"
    assert identity.fp1_identity()["format_version"] == CONTRACT_FORMAT_VERSION


def test_family_geometry_is_open_not_a_closed_enum() -> None:
    # A family may declare a geometry outside the seed set — geometry is open.
    identity = _ok(FamilyIdentity.try_create("fractal-channel", 1, "channel"))
    assert identity.geometry == "channel"


@pytest.mark.parametrize(
    ("family_id", "version", "geometry", "field"),
    [
        ("", 1, "point", "family_id"),
        ("  ", 1, "point", "family_id"),
        ("swing", 0, "point", "version"),
        ("swing", -1, "point", "version"),
        ("swing", True, "point", "version"),
        ("swing", "1", "point", "version"),
        ("swing", 1, "", "geometry"),
        ("swing", 1, "   ", "geometry"),
    ],
)
def test_family_identity_refuses_bad_parts(
    family_id: object, version: object, geometry: object, field: str
) -> None:
    result = FamilyIdentity.try_create(family_id, version, geometry)
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "invalid input"
    assert result.context["field"] == field


# --- ConfirmationRule -------------------------------------------------------


def test_confirmation_rule_bounded() -> None:
    rule = _ok(ConfirmationRule.try_create("confirmed at bar close", confirmation_delay_bound=5))
    assert rule.descriptor == "confirmed at bar close"
    assert rule.clock_confirmed is False
    assert rule.confirmation_delay_bound == 5
    assert rule.fp1_identity()["confirmation_delay_bound"] == 5


def test_confirmation_rule_unbounded_is_explicit_token_not_null() -> None:
    rule = _ok(ConfirmationRule.try_create("confirmed on manual review"))
    assert rule.confirmation_delay_bound is None
    content = rule.fp1_identity()
    assert content["confirmation_delay"] == "unbounded"
    assert "confirmation_delay_bound" not in content


def test_confirmation_rule_clock_confirmed_is_legal() -> None:
    rule = _ok(
        ConfirmationRule.try_create("confirmed the instant it is derived", clock_confirmed=True)
    )
    assert rule.clock_confirmed is True


def test_bounded_and_unbounded_rules_fingerprint_differently() -> None:
    bounded = _ok(ConfirmationRule.try_create("r", confirmation_delay_bound=0))
    unbounded = _ok(ConfirmationRule.try_create("r"))
    assert fingerprint(bounded.fp1_identity()) != fingerprint(unbounded.fp1_identity())


def test_confirmation_rule_refuses_blank_descriptor_fm2() -> None:
    # An imprecise (blank) rule is not admitted to the governed library (FM-2).
    result = ConfirmationRule.try_create("   ")
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "descriptor"


@pytest.mark.parametrize("bound", [-1, 1.5, "3"])
def test_confirmation_rule_refuses_bad_bound(bound: object) -> None:
    result = ConfirmationRule.try_create("rule", confirmation_delay_bound=bound)
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "confirmation_delay_bound"


def test_confirmation_rule_refuses_non_bool_clock_confirmed() -> None:
    result = ConfirmationRule.try_create("rule", clock_confirmed=1)  # type: ignore[arg-type]
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "clock_confirmed"


# --- DeclaredFamily ---------------------------------------------------------


def test_declared_family_refuses_bad_identity_or_rule() -> None:
    rule = _ok(ConfirmationRule.try_create("rule"))
    identity = _ok(FamilyIdentity.try_create("f", 1, "point"))
    bad_identity = DeclaredFamily.try_create("not-a-family", rule)
    assert isinstance(bad_identity, TypedRefusal)
    assert bad_identity.context["field"] == "identity"
    bad_rule = DeclaredFamily.try_create(identity, "not-a-rule")
    assert isinstance(bad_rule, TypedRefusal)
    assert bad_rule.context["field"] == "confirmation_rule"


def test_declared_family_fingerprints() -> None:
    family = _family()
    assert _ok(fingerprint(family.fp1_identity())).value.startswith("fp1:sha256:")


# --- AnchorSpan -------------------------------------------------------------


def test_anchor_span_happy_and_fingerprint() -> None:
    anchor = _anchor()
    content = anchor.fp1_identity()
    assert content["start_ns"] == _T0
    assert content["end_ns"] == _T0 + _MINUTE
    assert content["format_version"] == CONTRACT_FORMAT_VERSION


def test_anchor_span_point_allows_equal_bounds() -> None:
    anchor = _ok(
        AnchorSpan.try_create(
            Instant(value_ns=_T0), Instant(value_ns=_T0), _price(108_000), _price(108_000)
        )
    )
    assert anchor.start == anchor.end
    assert anchor.low.as_fraction() == anchor.high.as_fraction()


def test_anchor_span_refuses_start_after_end() -> None:
    result = AnchorSpan.try_create(
        Instant(value_ns=_T0 + _MINUTE), Instant(value_ns=_T0), _price(1), _price(2)
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "start"


def test_anchor_span_refuses_low_above_high() -> None:
    result = AnchorSpan.try_create(
        Instant(value_ns=_T0), Instant(value_ns=_T0), _price(108_500), _price(108_000)
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "low"


def test_anchor_span_refuses_cross_instrument_bounds() -> None:
    result = AnchorSpan.try_create(
        Instant(value_ns=_T0),
        Instant(value_ns=_T0),
        _price(108_000, _EURUSD),
        _price(108_500, _GBPUSD),
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "high"


@pytest.mark.parametrize(
    ("start", "end", "low", "high", "field"),
    [
        (object(), Instant(value_ns=_T0), _price(1), _price(2), "start"),
        (Instant(value_ns=_T0), object(), _price(1), _price(2), "end"),
        (Instant(value_ns=_T0), Instant(value_ns=_T0), object(), _price(2), "low"),
        (Instant(value_ns=_T0), Instant(value_ns=_T0), _price(1), object(), "high"),
    ],
)
def test_anchor_span_refuses_wrong_types(
    start: object, end: object, low: object, high: object, field: str
) -> None:
    result = AnchorSpan.try_create(start, end, low, high)
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == field


# --- emission invariant -----------------------------------------------------


def test_emission_invariant_happy_mint_chain() -> None:
    witness = _ok(
        check_emission_invariant(
            anchor=_anchor(),
            observed_at=Instant(value_ns=_T0 + 2 * _MINUTE),
            consumed_input_times=[Instant(value_ns=_T0 + _MINUTE)],
        )
    )
    assert isinstance(witness, EmissionWitness)
    assert witness.max_input_ns == _T0 + _MINUTE
    assert witness.chain[0] == ("anchor.start", _T0)
    assert witness.chain[-1] == ("observed_at", _T0 + 2 * _MINUTE)


def test_emission_invariant_full_chain_with_lifecycle_instants() -> None:
    witness = _ok(
        check_emission_invariant(
            anchor=_anchor(),
            observed_at=Instant(value_ns=_T0 + 2 * _MINUTE),
            confirmed_at=Instant(value_ns=_T0 + 3 * _MINUTE),
            invalidated_at=Instant(value_ns=_T0 + 4 * _MINUTE),
        )
    )
    labels = [label for label, _ in witness.chain]
    assert labels == ["anchor.start", "anchor.end", "observed_at", "confirmed_at", "invalidated_at"]
    assert witness.max_input_ns is None


def test_emission_invariant_allows_equal_instants_consumption_not_lookahead() -> None:
    # Equality is consumption, not look-ahead: observed_at == max input evidence time and
    # observed_at == confirmed_at are both legal.
    at = Instant(value_ns=_T0 + 2 * _MINUTE)
    witness = _ok(
        check_emission_invariant(
            anchor=_anchor(),
            observed_at=at,
            confirmed_at=at,
            consumed_input_times=[at],
        )
    )
    assert witness.max_input_ns == at.value_ns


def test_emission_invariant_refuses_anchor_end_after_observed_at() -> None:
    result = check_emission_invariant(
        anchor=_anchor(end=_T0 + 5 * _MINUTE),
        observed_at=Instant(value_ns=_T0 + 2 * _MINUTE),
    )
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "invalid input"
    assert result.context["field"] == "observed_at"


def test_emission_invariant_refuses_confirmed_before_observed() -> None:
    result = check_emission_invariant(
        anchor=_anchor(),
        observed_at=Instant(value_ns=_T0 + 3 * _MINUTE),
        confirmed_at=Instant(value_ns=_T0 + 2 * _MINUTE),
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "confirmed_at"


def test_emission_invariant_refuses_invalidated_before_confirmed() -> None:
    result = check_emission_invariant(
        anchor=_anchor(),
        observed_at=Instant(value_ns=_T0 + 2 * _MINUTE),
        confirmed_at=Instant(value_ns=_T0 + 3 * _MINUTE),
        invalidated_at=Instant(value_ns=_T0 + 2 * _MINUTE),
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "invalidated_at"


def test_emission_invariant_invalidated_without_confirmed() -> None:
    # An unconfirmed object may be invalidated: the chain skips confirmed_at, and
    # observed_at <= invalidated_at is still enforced.
    result = check_emission_invariant(
        anchor=_anchor(),
        observed_at=Instant(value_ns=_T0 + 3 * _MINUTE),
        invalidated_at=Instant(value_ns=_T0 + 2 * _MINUTE),
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "invalidated_at"


def test_emission_invariant_refuses_observed_at_behind_consumed_input() -> None:
    result = check_emission_invariant(
        anchor=_anchor(),
        observed_at=Instant(value_ns=_T0 + 2 * _MINUTE),
        consumed_input_times=[Instant(value_ns=_T0 + 5 * _MINUTE)],
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "observed_at"
    assert result.context["max_input_evidence_time"] == _T0 + 5 * _MINUTE


def test_emission_invariant_anchor_excluded_from_causal_test() -> None:
    # The anchor may precede everything, including a consumed input's evidence time —
    # the anchor is excluded from the causal-availability test.
    witness = _ok(
        check_emission_invariant(
            anchor=_anchor(start=_T0, end=_T0 + _MINUTE),
            observed_at=Instant(value_ns=_T0 + 10 * _MINUTE),
            consumed_input_times=[Instant(value_ns=_T0 + 9 * _MINUTE)],
        )
    )
    assert witness.max_input_ns == _T0 + 9 * _MINUTE


@pytest.mark.parametrize(
    ("kwargs", "field"),
    [
        ({"anchor": object(), "observed_at": Instant(value_ns=_T0)}, "anchor"),
        ({"anchor": _anchor(), "observed_at": object()}, "observed_at"),
    ],
)
def test_emission_invariant_refuses_wrong_core_types(kwargs: dict[str, object], field: str) -> None:
    result = check_emission_invariant(**kwargs)  # type: ignore[arg-type]
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == field


def test_emission_invariant_refuses_wrong_confirmed_or_invalidated_type() -> None:
    bad_confirmed = check_emission_invariant(
        anchor=_anchor(), observed_at=Instant(value_ns=_T0 + _MINUTE), confirmed_at=object()
    )
    assert isinstance(bad_confirmed, TypedRefusal)
    assert bad_confirmed.context["field"] == "confirmed_at"
    bad_invalidated = check_emission_invariant(
        anchor=_anchor(), observed_at=Instant(value_ns=_T0 + _MINUTE), invalidated_at=object()
    )
    assert isinstance(bad_invalidated, TypedRefusal)
    assert bad_invalidated.context["field"] == "invalidated_at"


@pytest.mark.parametrize("consumed", [123, "not-a-sequence", [Instant(value_ns=_T0), 456]])
def test_emission_invariant_refuses_bad_consumed_input_times(consumed: object) -> None:
    result = check_emission_invariant(
        anchor=_anchor(),
        observed_at=Instant(value_ns=_T0 + 5 * _MINUTE),
        consumed_input_times=consumed,
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "consumed_input_times"


# --- StructureObject mint ---------------------------------------------------


def _mint(
    *,
    evidence_class: object = EvidenceClass.UNCONFIRMED,
    parameters: object | None = None,
    consumed: object = (),
) -> Result[StructureObject]:
    return StructureObject.try_create(
        _family(),
        {"pivot_tolerance": _rational(1, 4)} if parameters is None else parameters,
        _anchor(),
        Instant(value_ns=_T0 + 2 * _MINUTE),
        evidence_class,
        consumed_input_times=consumed,
    )


def test_mint_carries_every_identity_field() -> None:
    obj = _ok(_mint())
    assert obj.family.family_id == "swing-point"
    assert obj.family.version == 1
    assert obj.confirmation_rule.descriptor.startswith("confirmed the moment")
    assert obj.parameters["pivot_tolerance"] == _rational(1, 4)
    assert obj.anchor.start.value_ns == _T0
    assert obj.observed_at.value_ns == _T0 + 2 * _MINUTE
    assert obj.evidence_class is EvidenceClass.UNCONFIRMED


def test_mint_returns_fingerprintable_content_not_a_stamped_record() -> None:
    obj = _ok(_mint())
    derived = _ok(obj.content_fingerprint())
    assert isinstance(derived, Fingerprint)
    assert derived.value.startswith("fp1:sha256:")
    # The fingerprint is DERIVED from the identity content, never minted.
    assert derived == _ok(fingerprint(obj.fp1_identity()))
    # No writer, sequence, or created-at is carried — the composition root stamps those.
    assert not hasattr(obj, "writer")
    assert not hasattr(obj, "sequence")
    assert not hasattr(obj, "created_at")


def test_mint_fp1_identity_stamps_format_version_and_class() -> None:
    content = _ok(_mint()).fp1_identity()
    assert content["class"] == "structure-object"
    assert content["format_version"] == CONTRACT_FORMAT_VERSION
    assert content["observed_at"] == _T0 + 2 * _MINUTE


def test_identical_mints_deduplicate_by_fingerprint() -> None:
    a = _ok(obj) if is_ok(obj := _mint()) else None
    b = _ok(obj2) if is_ok(obj2 := _mint()) else None
    assert a is not None and b is not None
    assert _ok(a.content_fingerprint()) == _ok(b.content_fingerprint())


def test_evidence_class_is_identity_bearing() -> None:
    unconfirmed = _ok(_mint(evidence_class=EvidenceClass.UNCONFIRMED))
    confirmed = _ok(_mint(evidence_class="confirmed"))  # string coerces to the member
    assert confirmed.evidence_class is EvidenceClass.CONFIRMED
    # A different evidence class is a different fact — a different fingerprint.
    assert _ok(unconfirmed.content_fingerprint()) != _ok(confirmed.content_fingerprint())


def test_different_parameters_change_the_fingerprint() -> None:
    a = _ok(_mint(parameters={"pivot_tolerance": _rational(1, 4)}))
    b = _ok(_mint(parameters={"pivot_tolerance": _rational(1, 3)}))
    assert _ok(a.content_fingerprint()) != _ok(b.content_fingerprint())


def test_mint_allows_empty_parameter_set() -> None:
    obj = _ok(_mint(parameters={}))
    assert dict(obj.parameters) == {}


def test_mint_parameters_are_snapshot_against_later_mutation() -> None:
    mutable = {"pivot_tolerance": _rational(1, 4)}
    obj = _ok(_mint(parameters=mutable))
    mutable["pivot_tolerance"] = _rational(9, 10)
    assert obj.parameters["pivot_tolerance"] == _rational(1, 4)


def test_mint_runs_the_emission_invariant() -> None:
    # observed-at behind a consumed input's evidence time is refused at mint (FM-1).
    result = _mint(consumed=[Instant(value_ns=_T0 + 9 * _MINUTE)])
    assert isinstance(result, TypedRefusal)
    assert result.category.value == "invalid input"
    assert result.context["field"] == "observed_at"


def test_mint_refuses_non_family() -> None:
    result = StructureObject.try_create(
        123,
        {},
        _anchor(),
        Instant(value_ns=_T0 + _MINUTE),
        EvidenceClass.UNCONFIRMED,
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "family"


class _FakeFamily:
    """A structural StructureFamily whose members return the wrong types."""

    def __init__(self, identity: object, confirmation_rule: object) -> None:
        self.identity = identity
        self.confirmation_rule = confirmation_rule


def test_mint_refuses_family_with_wrong_identity_type() -> None:
    fake = _FakeFamily("not-a-family-identity", _ok(ConfirmationRule.try_create("r")))
    assert isinstance(fake, StructureFamily)  # structurally a family, semantically not
    result = StructureObject.try_create(
        fake, {}, _anchor(), Instant(value_ns=_T0 + _MINUTE), EvidenceClass.UNCONFIRMED
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "family"


def test_mint_refuses_family_with_wrong_rule_type() -> None:
    fake = _FakeFamily(_ok(FamilyIdentity.try_create("f", 1, "point")), "not-a-rule")
    result = StructureObject.try_create(
        fake, {}, _anchor(), Instant(value_ns=_T0 + _MINUTE), EvidenceClass.UNCONFIRMED
    )
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "family"


@pytest.mark.parametrize(
    "parameters",
    [
        "not-a-mapping",
        {"": _rational(1, 2)},
        {"tolerance": "not-an-exact-rational"},
        {"tolerance": 0.5},
    ],
)
def test_mint_refuses_bad_parameters(parameters: object) -> None:
    result = _mint(parameters=parameters)
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "parameters"


def test_mint_refuses_bad_anchor_observed_and_evidence_class() -> None:
    bad_anchor = StructureObject.try_create(
        _family(), {}, object(), Instant(value_ns=_T0 + _MINUTE), EvidenceClass.UNCONFIRMED
    )
    assert isinstance(bad_anchor, TypedRefusal)
    assert bad_anchor.context["field"] == "anchor"

    bad_observed = StructureObject.try_create(
        _family(), {}, _anchor(), object(), EvidenceClass.UNCONFIRMED
    )
    assert isinstance(bad_observed, TypedRefusal)
    assert bad_observed.context["field"] == "observed_at"

    bad_class = StructureObject.try_create(
        _family(), {}, _anchor(), Instant(value_ns=_T0 + _MINUTE), "not-a-class"
    )
    assert isinstance(bad_class, TypedRefusal)
    assert bad_class.context["field"] == "evidence_class"
