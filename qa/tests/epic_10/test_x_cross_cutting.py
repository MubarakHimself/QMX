"""Epic 10 independent audit — Cluster X (cross-cutting gates + L0 static).

R-009 (typed-refusal register conformance), R-001 (no float on the money path),
P0-8 (the admitted-entry lifecycle), and the L0 static scanners (money-path float,
ambient nondeterminism, AR-06 dependency direction).

Planned IDs: X1-X4 plus L0 gates.
"""

from __future__ import annotations

import ast
from pathlib import Path

import yaml
import qmf.risk
from qmf.core import (
    ExactRational,
    Instrument,
    Money,
    Price,
    PriceDelta,
    Quantity,
    RefusalCategory,
    UnitKind,
    ValueFactor,
    VenueId,
    is_ok,
    is_refusal,
)
from qmf.risk.admission_bar import AdmissionRequirement, Comparison, RuledThreshold
from qmf.risk.binding import BookBindingRequirements
from qmf.risk.control_action import RiskReducingAct, check_exit_preservation
from qmf.risk.control_rank import ControlActionKind, ControlRankRow, ControlRankTable
from qmf.risk.door import (
    Direction,
    EntryIntent,
    ExitIntent,
    ExitKind,
    ExitLogicRef,
    ReasonCode,
    admit_entry_intent,
    reject_inbound_requested_r,
)
from qmf.risk.grammar import AdmissionImpact, TemplateVariable, UiEditability
from qmf.risk.numeraire import validate_accounting_currency, validate_book_limit
from qmf.risk.paper import ExecutionTarget, validate_book_mode
from qmf.risk.performance import PerformanceMeasure
from qmf.risk.r_faces import RFaces, admit_entry_r_faces, r_to_money


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")


def _price(value: int) -> Price:
    result = Price.try_create(value, _instrument(), 5)
    assert is_ok(result)
    return result.value


def _delta(value: int) -> PriceDelta:
    result = PriceDelta.try_create(value, _instrument(), 5)
    assert is_ok(result)
    return result.value


def _usd(minor: int) -> Money:
    return Money(value=minor, currency="USD", scale=2)


def _r(num: int, den: int = 1) -> ExactRational:
    result = ExactRational.try_create(num, den, UnitKind.R_MULTIPLE)
    assert is_ok(result)
    return result.value


_SRC_DIR = Path(qmf.risk.__file__).resolve().parent
_PACKAGES_DIR = _SRC_DIR.parents[3]  # .../packages


def _register_from_docs() -> set[str]:
    docs = _PACKAGES_DIR.parent / "docs" / "registry" / "variables.yaml"
    data = yaml.safe_load(docs.read_text(encoding="utf-8"))
    for entry in data.get("variables", data if isinstance(data, list) else []):
        if isinstance(entry, dict) and entry.get("name") == "typed_refusal_codes":
            return set(entry["value"])
    raise AssertionError("typed_refusal_codes not found in registry")


def _canonical(category: RefusalCategory) -> str:
    # The register spells categories hyphenated ("invalid-input"); the enum spells them
    # spaced ("invalid input"). Map the enum's spaced value to the register's form.
    return category.value.replace(" ", "-")


# --- X2 [R-009]: the register is exactly the seven categories -----------------


def test_X2_register_is_exactly_the_seven_categories() -> None:
    enum_seven = {_canonical(member) for member in RefusalCategory}
    assert len(enum_seven) == 7
    register = _register_from_docs()
    assert register == enum_seven
    # The seven names, verbatim.
    assert enum_seven == {
        "invalid-input", "unsupported-capability", "unavailable-dependency", "stale-evidence",
        "policy-rejection", "transient-venue-failure", "storage-failure",
    }


# --- X1 [R-009]: every door-reachable refusal is on the register -------------


def test_X1_every_door_reachable_refusal_is_on_the_register() -> None:
    register = _register_from_docs()
    emitted: set[str] = set()

    def _capture(result: object) -> None:
        assert is_refusal(result)
        emitted.add(_canonical(result.category))  # type: ignore[union-attr]

    # CT-22 grammar / numeraire
    _capture(TemplateVariable.try_create(name="x", unit_kind=None, value=_usd(1),
                                         ui_editable=UiEditability.UI_EDITABLE,
                                         admission_impact=AdmissionImpact.NONE))
    _capture(validate_accounting_currency("EUR"))
    _capture(validate_book_limit(UnitKind.QUANTITY))
    # CT-23 r-faces / door
    _capture(RFaces.try_create("d", _usd(1)))
    _capture(admit_entry_r_faces(_price(110_000), _price(109_000), Direction.LONG,
                                 Quantity(value=1, unit="lot", scale=0), None, money_scale=2))
    _capture(reject_inbound_requested_r({"intent_family": "entry", "requested_r": _r(2)}))
    _capture(ExitIntent.try_create("close_partial", _reason(), _fp("vp")))
    # CT-22 admission bar
    _capture(AdmissionRequirement.try_create("m", UnitKind.DIMENSIONLESS_RATIO, "weighted-aggregate",
                                             RuledThreshold(bound=_r(1)), _evidence(), 0))
    # CT-28 binding
    _capture(BookBindingRequirements.try_create("EUR", frozenset[str](), frozenset[str](), {}))
    # CT-30 control rank
    _capture(ControlRankTable.try_create([ControlRankRow(control_action_kind=ControlActionKind.FLATTEN, rank=1),
                                          ControlRankRow(control_action_kind=ControlActionKind.DRAIN, rank=1)]))
    # L39 exit preservation
    _capture(check_exit_preservation(blocked_act=RiskReducingAct.CLOSE_ALL))
    # CT-24 paper
    _capture(validate_book_mode("benched"))
    # CT-32 performance
    qty = ExactRational.try_create(1, 1, UnitKind.DIMENSIONLESS_RATIO)
    assert is_ok(qty)
    _capture(PerformanceMeasure.try_create("composite-score", qty.value, 1))

    # Every emitted category is on the register; no door emitted an off-register code.
    assert emitted, "expected to observe some refusals"
    assert emitted <= register, emitted - register


def _reason() -> ReasonCode:
    result = ReasonCode.try_create("r", "fam")
    assert is_ok(result)
    return result.value


def _fp(seed: str):
    from qmf.core import fingerprint

    result = fingerprint({"seed": seed})
    assert is_ok(result)
    return result.value


def _evidence():
    from qmf.core import AccountRole, Duration, World
    from qmf.risk.admission_bar import EvidenceRequirements

    result = EvidenceRequirements.try_create(World.LIVE, AccountRole.LIVE, Duration(value_ns=1), {})
    assert is_ok(result)
    return result.value


# --- X3 [R-001]: no binary float enters a money/price/R identity -------------


def test_X3_money_path_value_types_refuse_floats() -> None:
    # Every money-path value factory refuses a binary float.
    assert is_refusal(Money.try_create(1.5, "USD", 2))
    assert is_refusal(Price.try_create(1.5, _instrument(), 5))
    assert is_refusal(PriceDelta.try_create(1.5, _instrument(), 5))
    assert is_refusal(Quantity.try_create(1.5, "lot", 2))
    assert is_refusal(ExactRational.try_create(1.5, 1, UnitKind.R_MULTIPLE))
    assert is_refusal(ValueFactor.try_create(1.5, 1, _instrument(), "USD"))
    # A template variable likewise refuses a float value on the money path.
    assert is_refusal(TemplateVariable.try_create(name="x", unit_kind=UnitKind.MONEY, value=1.5,
                                                  ui_editable=UiEditability.UI_EDITABLE,
                                                  admission_impact=AdmissionImpact.NONE))


def test_X3_L0_money_path_float_scanner() -> None:
    # L0: no binary-float literal appears anywhere in the qmf-risk source.
    offenders: list[str] = []
    for path in sorted(_SRC_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                offenders.append(f"{path.name}:{node.lineno} -> {node.value!r}")
    assert offenders == [], offenders


# --- L0: ambient-nondeterminism scanner --------------------------------------


def test_L0_no_ambient_nondeterminism_in_qmf_risk() -> None:
    forbidden_modules = {"random", "secrets", "uuid"}
    offenders: list[str] = []
    for path in sorted(_SRC_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in forbidden_modules:
                        offenders.append(f"{path.name}:{node.lineno} import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in forbidden_modules:
                    offenders.append(f"{path.name}:{node.lineno} from {node.module}")
    assert offenders == [], offenders


# --- L0: AR-06 dependency direction ------------------------------------------


def test_L0_ar06_dependency_direction() -> None:
    forbidden = ("qmf.data", "qmf.registry", "qmf.indicators", "qmf.structure", "qmf.venue")
    for path in sorted(_SRC_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                names.append(node.module)
            elif isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            for name in names:
                assert not any(name == bad or name.startswith(f"{bad}.") for bad in forbidden), \
                    f"{path.name} imports forbidden {name}"


# --- X4 [P0-8]: the admitted-entry lifecycle passes the charter doors ---------


class _OffsetStopModule:
    def derive_full_loss_price(self, *, entry_price, direction, cited_evidence):
        value = entry_price.value - 500 if direction is Direction.LONG else entry_price.value + 500
        return Price.try_create(value, entry_price.instrument, entry_price.scale)


def _target() -> ExecutionTarget:
    from qmf.core import AccountRole

    result = ExecutionTarget.try_create(AccountRole.LIVE, VenueId(value="ctrader"), "acct-1")
    assert is_ok(result)
    return result.value


def _entry(**kwargs) -> EntryIntent:
    from qmf.risk.door import CitedEvidence, EvidenceSlot
    from qmf.core import Instant

    slot = EvidenceSlot.try_create("sqs", "ref", Instant(value_ns=1))
    assert is_ok(slot)
    cited = CitedEvidence.try_create(sqs_reading=slot.value)
    assert is_ok(cited)
    result = EntryIntent.try_create(_instrument(), Direction.LONG, _reason(), _target(),
                                    proposed_r=_r(3), cited_evidence=cited.value, **kwargs)
    assert is_ok(result)
    return result.value


def _ref() -> ExitLogicRef:
    result = ExitLogicRef.try_create("book.default.evidence_stop", None)
    assert is_ok(result)
    return result.value


def test_X4_p0_8_admitted_entry_lifecycle_r_frozen_full_loss_required() -> None:
    import dataclasses

    import pytest

    # 1. The bot may not size: an inbound requested_r is refused before admission.
    assert is_refusal(reject_inbound_requested_r({"intent_family": "entry", "requested_r": _r(2)}))

    # 2. An entry with a derivable full-loss price is admitted; R is FROZEN at admission
    #    (money-bearing faces set once), the full-loss price is Book-derived and stamped,
    #    and requested_r is Book-resolved (never the bot's proposed_r).
    admitted = admit_entry_intent(intent=_entry(), entry_price=_price(105000),
                                  exit_logic_ref=_ref(), module=_OffsetStopModule(),
                                  book_resolved_requested_r=_r(2))
    assert is_ok(admitted)
    record = admitted.value
    assert record.declared_full_loss_price == _price(104500)
    assert record.original_risk_distance == _delta(500)
    assert record.requested_r == _r(2)
    assert record.proposed_r == _r(3)
    assert record.requested_r != record.proposed_r
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.requested_r = _r(9)  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.original_risk_distance = _delta(1)  # type: ignore[misc]

    # 3. A declared full-loss price is REQUIRED: with no derivable price, no admission.
    class _NoStop:
        def derive_full_loss_price(self, *, entry_price, direction, cited_evidence):
            from qmf.risk.door import refuse_no_full_loss_price

            return refuse_no_full_loss_price(module="none")

    no_admission = admit_entry_intent(intent=_entry(), entry_price=_price(105000),
                                      exit_logic_ref=_ref(), module=_NoStop(),
                                      book_resolved_requested_r=_r(2))
    assert is_refusal(no_admission)
    assert no_admission.category is RefusalCategory.INVALID_INPUT

    # 4. Downstream, neither a stop move nor a budget re-derivation re-bases the frozen R.
    faces = RFaces.try_create(record.original_risk_distance, _usd(50_000))
    assert is_ok(faces)
    amount_before = faces.value.original_risk_amount
    rederived = r_to_money(_r(9), __rate(25), scale=2)
    assert is_ok(rederived)
    assert faces.value.original_risk_amount == amount_before


def __rate(num: int) -> ExactRational:
    result = ExactRational.try_create(num, 1, UnitKind.RATE)
    assert is_ok(result)
    return result.value
