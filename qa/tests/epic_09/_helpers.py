"""Shared builders and fakes for the Epic 9 (qmf-structure) independent QA suite.

These helpers ONLY construct public objects and drive the public API. They encode
NO assertions about behaviour — every assertion lives in a test module and is drawn
from an oracle (epics.md Epic 9, docs/contracts/ct-17-causal-structure.yaml,
docs/constitution.md, docs/registry/variables.yaml), never from the implementation.

Objects flow through the public ``qmf.structure`` surface only; primitive value
types (Instant, Price, ExactRational, ...) come from ``qmf.core``. No private
``_helper`` of the implementation is ever touched.
"""

from __future__ import annotations

from typing import TypeVar

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
    is_ok,
)
from qmf.structure import (
    AnchorSpan,
    CompositeChild,
    ConfirmationRule,
    DeclaredFamily,
    FamilyIdentity,
    HighLowObservation,
    StructureObject,
    SwingPointFamily,
)

T = TypeVar("T")

# Fixed instruments and a fixed epoch, so identical builds fingerprint identically.
EURUSD = Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")
GBPUSD = Instrument(venue=VenueId(value="ctrader"), symbol="GBPUSD")

T0 = 1_700_000_000_000_000_000
MINUTE = 60_000_000_000


def ok(result: Result[T]) -> T:
    """Unwrap an Ok, or fail loudly (used only in builders — never as an assertion)."""
    assert is_ok(result), f"expected Ok in a test builder, got {result}"
    assert isinstance(result, Ok)
    return result.value


def is_refused(result: object) -> bool:
    return isinstance(result, TypedRefusal)


def inst(offset_minutes: int) -> Instant:
    return Instant(value_ns=T0 + offset_minutes * MINUTE)


def price(value: int, instrument: Instrument = EURUSD, scale: int = 5) -> Price:
    return ok(Price.try_create(value, instrument, scale))


def rational(num: int, den: int = 1) -> ExactRational:
    return ok(ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO))


def family(
    family_id: str = "swing-point",
    version: int = 1,
    geometry: str = "point",
    *,
    descriptor: str = "confirmed the moment a later bar closes beyond the pivot",
    clock_confirmed: bool = False,
    bound: int | None = 3,
) -> DeclaredFamily:
    identity = ok(FamilyIdentity.try_create(family_id, version, geometry))
    rule = ok(
        ConfirmationRule.try_create(
            descriptor, clock_confirmed=clock_confirmed, confirmation_delay_bound=bound
        )
    )
    return ok(DeclaredFamily.try_create(identity, rule))


def anchor(
    start_min: int = 0,
    end_min: int = 1,
    low: int = 108_000,
    high: int = 108_500,
    instrument: Instrument = EURUSD,
) -> AnchorSpan:
    return ok(
        AnchorSpan.try_create(
            inst(start_min), inst(end_min), price(low, instrument), price(high, instrument)
        )
    )


def mint(
    *,
    fam: DeclaredFamily | None = None,
    parameters: object | None = None,
    anc: AnchorSpan | None = None,
    observed_min: int = 2,
    evidence_class: object = EvidenceClass.UNCONFIRMED,
    consumed: object = (),
) -> Result[StructureObject]:
    """Return the RAW Result of a mint (tests decide Ok vs refusal)."""
    return StructureObject.try_create(
        family() if fam is None else fam,
        {"pivot_tolerance": rational(1, 4)} if parameters is None else parameters,
        anchor() if anc is None else anc,
        inst(observed_min),
        evidence_class,
        consumed_input_times=consumed,
    )


def minted(**kwargs: object) -> StructureObject:
    """A successfully-minted object (builder convenience)."""
    return ok(mint(**kwargs))  # type: ignore[arg-type]


def fp(obj: StructureObject) -> Fingerprint:
    return ok(obj.content_fingerprint())


def observation(
    minute: int, high: int, low: int, close: int, instrument: Instrument = EURUSD
) -> HighLowObservation:
    return ok(
        HighLowObservation.try_create(
            inst(minute),
            price(high, instrument),
            price(low, instrument),
            price(close, instrument),
        )
    )


def swing_family(*, left: int = 1, right: int = 1, bound: int | None = 5) -> SwingPointFamily:
    return ok(SwingPointFamily.create(left=left, right=right, confirmation_delay_bound=bound))


def child(
    ref: Fingerprint,
    *,
    observed_min: int,
    confirmed_min: int | None = None,
    bound: int | None = 0,
) -> CompositeChild:
    return ok(
        CompositeChild.try_create(
            ref,
            inst(observed_min),
            confirmed_at=None if confirmed_min is None else inst(confirmed_min),
            confirmation_delay_bound=bound,
        )
    )
