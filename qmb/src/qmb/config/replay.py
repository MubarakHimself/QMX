"""World=replay binding mint and virtual-ledger seed (B-3, DEC-0160).

Every QMB run mints exactly one AD-29/CT-28 binding with ``world = replay`` — a
different identity from any live binding of the same Book instance, and
incomparable to it. ``starting_capital`` is the binding's virtual-ledger seed:
a mandatory run-spec field the Book fragment may default. An invocation-flag
override stamps ``seed_overridden`` on the binding and forces the run's fold
to ``unrated`` (FM-12). QMB consumes CT-28; it does not redefine it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

from qmf.core.exact import MONEY_STORAGE_SCALE, Money
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.identity import VenueId
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.binding import (
    STATE_CARRY_COUNTERS,
    BmsInstanceId,
    BookBindingRecord,
    BookInstance,
    BookInstanceId,
    CapabilityCheckResult,
    PositionModel,
    StateCarry,
    StateCarryChoice,
)
from qmf.risk.numeraire import V1_NUMERAIRE

from qmb._refuse import clean_token, invalid, policy

__all__ = [
    "FOLD_RATED",
    "FOLD_UNRATED",
    "REPLAY_BINDING_CLASS",
    "STARTING_CAPITAL_KEY",
    "VIRTUAL_LEDGER_CLASS",
    "ReplayBinding",
    "VirtualLedger",
    "check_incomparable_to_live",
    "coerce_starting_capital",
    "mint_replay_binding",
    "replay_capability_result",
    "replay_state_carry",
    "resolve_starting_capital",
]

FOLD_RATED: Final[str] = "rated"
FOLD_UNRATED: Final[str] = "unrated"
REPLAY_BINDING_CLASS: Final[str] = "qmb-replay-binding"
VIRTUAL_LEDGER_CLASS: Final[str] = "virtual-ledger"
STARTING_CAPITAL_KEY: Final[str] = "starting_capital"
_BOOK_INSTANCE_CLASS: Final[str] = "qmb-replay-book-instance"
_MINT_OCCURRENCE: Final[str] = "qmb-replay"


@dataclass(frozen=True, slots=True)
class VirtualLedger:
    """The binding-scoped virtual ledger, seeded from ``starting_capital``.

    Equity starts equal to the seed. The value is frozen — later cash events
    mint a new ledger state rather than mutating this one (DEC-0160).
    """

    binding_epoch: Fingerprint
    seed: Money
    equity: Money

    @classmethod
    def try_create(cls, binding_epoch: object, seed: object) -> Result[VirtualLedger]:
        """Seed a virtual ledger. Equity opens at the seed."""
        if not isinstance(binding_epoch, Fingerprint):
            return invalid(
                "binding_epoch",
                "the virtual ledger is scoped to the CT-28 binding epoch",
                given=repr(binding_epoch),
            )
        capital = coerce_starting_capital(seed)
        if is_refusal(capital):
            return capital
        return Ok(
            cls(
                binding_epoch=binding_epoch,
                seed=capital.value,
                equity=capital.value,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """Identity content. Package SemVer is omitted."""
        return {
            "binding_epoch": self.binding_epoch.value,
            "class": VIRTUAL_LEDGER_CLASS,
            "equity": self.equity.fp1_identity(),
            "seed": self.seed.fp1_identity(),
        }


@dataclass(frozen=True, slots=True)
class ReplayBinding:
    """One minted ``world = replay`` CT-28 binding plus its virtual-ledger seed.

    ``seed_overridden`` is stamped here, never caller-declared. The fold reads
    it: overridden seeds force ``unrated`` (FM-12).
    """

    record: BookBindingRecord
    book_instance: BookInstance
    virtual_ledger: VirtualLedger
    seed_overridden: bool
    fingerprint: Fingerprint

    @property
    def world(self) -> World:
        """Always ``replay`` — QMB never mints a live binding."""
        return World.REPLAY

    @property
    def starting_capital(self) -> Money:
        """The virtual-ledger seed."""
        return self.virtual_ledger.seed

    @property
    def fold_rating(self) -> str:
        """``unrated`` when the seed was flag-overridden, else ``rated``."""
        return FOLD_UNRATED if self.seed_overridden else FOLD_RATED

    def fp1_identity(self) -> dict[str, object]:
        """Identity content. The CT-28 record fingerprint is the epoch."""
        return {
            "book_instance_id": self.book_instance.instance_id.value,
            "class": REPLAY_BINDING_CLASS,
            "fingerprint": self.fingerprint.value,
            "fold_rating": self.fold_rating,
            "record": self.record.fp1_identity(),
            "seed_overridden": self.seed_overridden,
            "starting_capital": self.starting_capital.fp1_identity(),
            "virtual_ledger": self.virtual_ledger.fp1_identity(),
            "world": World.REPLAY.value,
        }


def replay_state_carry() -> Result[StateCarry]:
    """A new replay epoch resets every counter. Carry would need a signed edge."""
    per_counter = dict.fromkeys(STATE_CARRY_COUNTERS, StateCarryChoice.RESET)
    return StateCarry.try_create(per_counter)


def replay_capability_result(*, settlement_currency: str = V1_NUMERAIRE) -> CapabilityCheckResult:
    """Bind-time result for a replay mint.

    Replay is not a live binding: no live-path rung and no SQS live baseline.
    Virtual positions are Book-scoped (hedging). Settlement stays the V1
    numeraire. Constructed at the composition root, not via the live-path
    :func:`~qmf.risk.binding.bind_time_capability_check`.
    """
    return CapabilityCheckResult(
        position_model=PositionModel.HEDGING,
        settlement_currency=settlement_currency,
        satisfied_capabilities=frozenset(),
        shared_flatten_signature=None,
        satisfied_sensor_baselines=frozenset(),
        live_path_rung_baseline_present=False,
        rank_table_non_contradicted=True,
    )


def resolve_starting_capital(
    *,
    invocation_flags: Mapping[str, object],
    run_spec: Mapping[str, object],
    book_fragment_keys: Mapping[str, object],
) -> Result[tuple[Money, bool]]:
    """Resolve the virtual-ledger seed.

    Precedence for this field only: invocation flags (stamps ``seed_overridden``)
    > run spec > Book fragment ``sizing.starting_capital``. Workspace defaults
    and BMS keys cannot silently seed it (B-3, FM-12).
    """
    if STARTING_CAPITAL_KEY in invocation_flags:
        capital = coerce_starting_capital(invocation_flags[STARTING_CAPITAL_KEY])
        if is_refusal(capital):
            return capital
        return Ok((capital.value, True))
    if STARTING_CAPITAL_KEY in run_spec:
        capital = coerce_starting_capital(run_spec[STARTING_CAPITAL_KEY])
        if is_refusal(capital):
            return capital
        return Ok((capital.value, False))
    sizing = book_fragment_keys.get("sizing")
    if isinstance(sizing, Mapping):
        sizing_map = cast("Mapping[str, object]", sizing)
        if STARTING_CAPITAL_KEY in sizing_map:
            capital = coerce_starting_capital(sizing_map[STARTING_CAPITAL_KEY])
            if is_refusal(capital):
                return capital
            return Ok((capital.value, False))
    return invalid(
        STARTING_CAPITAL_KEY,
        "starting_capital is a mandatory run-spec field seeding the binding's "
        "virtual ledger; the Book fragment may default it (B-3, DEC-0160)",
    )


def coerce_starting_capital(value: object) -> Result[Money]:
    """``starting_capital`` is exact Money in the V1 numeraire, never a float."""
    if isinstance(value, float):
        return invalid(
            STARTING_CAPITAL_KEY,
            "starting_capital is exact Money; a binary float on the money path is refused",
            given=repr(value),
        )
    if isinstance(value, Money):
        return _validate_seed_money(value)
    if isinstance(value, Mapping):
        body = cast("Mapping[str, object]", value)
        if "value" in body and "currency" in body and "scale" in body:
            minted = Money.try_create(body["value"], body["currency"], body["scale"])
            if is_refusal(minted):
                return minted
            return _validate_seed_money(minted.value)
        if clean_token(body.get("class")) == "money":
            reconstructed = _money_from_fp1(body)
            if is_refusal(reconstructed):
                return reconstructed
            return _validate_seed_money(reconstructed.value)
        return invalid(
            STARTING_CAPITAL_KEY,
            "starting_capital is exact Money in the V1 numeraire (USD)",
            given="mapping",
        )
    return invalid(
        STARTING_CAPITAL_KEY,
        "starting_capital is exact Money in the V1 numeraire (USD)",
        given=type(value).__name__,
    )


def mint_replay_binding(
    *,
    book_fp1: object,
    bms_fp1: object,
    bot_fp1: object,
    starting_capital: object,
    seed_overridden: object,
    venue_id: object,
    account_id: object,
    clock: object,
    data_provenance: object,
    keys: Mapping[str, object],
) -> Result[ReplayBinding]:
    """Mint exactly one CT-28 binding with ``world = replay``.

    Identity is deterministic: same inputs yield the same BookInstanceId and the
    same binding epoch. ``world`` is ``replay`` so a live binding of the same
    Book version on the same account fingerprints apart (DEC-0160).
    """
    if not isinstance(book_fp1, Fingerprint):
        return invalid(
            "book_fp1",
            "the replay binding cites the CT-22 Book VERSION by fp1",
            given=repr(book_fp1),
        )
    if not isinstance(bms_fp1, Fingerprint):
        return invalid(
            "bms_fp1",
            "the replay binding cites the CT-27 BMS VERSION by fp1",
            given=repr(bms_fp1),
        )
    if not isinstance(bot_fp1, Fingerprint):
        return invalid(
            "bot_fp1",
            "the replay Book instance cites the bot by fp1",
            given=repr(bot_fp1),
        )
    capital = coerce_starting_capital(starting_capital)
    if is_refusal(capital):
        return capital
    if not isinstance(seed_overridden, bool):
        return invalid(
            "seed_overridden",
            "seed_overridden is a bool stamped when an invocation flag overrides the seed",
            given=repr(seed_overridden),
        )
    venue = _coerce_venue(venue_id)
    if is_refusal(venue):
        return venue
    account = clean_token(account_id)
    if account is None:
        return invalid(
            "account_id",
            "the replay binding tuple names an account id",
            given=repr(account_id),
        )
    clock_token = clean_token(clock)
    provenance_token = clean_token(data_provenance)
    if clock_token is None or provenance_token is None:
        return invalid(
            "clock",
            "the replay Book-instance mint cites the bound clock and data provenance",
            clock=repr(clock),
            data_provenance=repr(data_provenance),
        )
    instance_id = _replay_book_instance_id(
        book_fp1=book_fp1,
        bms_fp1=bms_fp1,
        bot_fp1=bot_fp1,
        starting_capital=capital.value,
        seed_overridden=seed_overridden,
        venue_id=venue.value,
        account_id=account,
        clock=clock_token,
        data_provenance=provenance_token,
        keys=keys,
    )
    if is_refusal(instance_id):
        return instance_id
    book_instance = BookInstance.try_create(
        instance_id.value,
        book_fp1,
        account,
        venue.value,
        World.REPLAY,
        _MINT_OCCURRENCE,
        0,
    )
    if is_refusal(book_instance):
        return book_instance
    bms_instance = BmsInstanceId.derive(bms_fp1, account, venue.value, World.REPLAY)
    if is_refusal(bms_instance):
        return bms_instance
    carry = replay_state_carry()
    if is_refusal(carry):
        return carry
    record = BookBindingRecord.try_create(
        book_instance.value.instance_id,
        bms_instance.value,
        venue.value,
        account,
        World.REPLAY,
        book_fp1,
        bms_fp1,
        carry.value,
        replay_capability_result(),
    )
    if is_refusal(record):
        return record
    epoch = record.value.fingerprint()
    if is_refusal(epoch):
        return epoch
    ledger = VirtualLedger.try_create(epoch.value, capital.value)
    if is_refusal(ledger):
        return ledger
    return Ok(
        ReplayBinding(
            record=record.value,
            book_instance=book_instance.value,
            virtual_ledger=ledger.value,
            seed_overridden=seed_overridden,
            fingerprint=epoch.value,
        )
    )


def check_incomparable_to_live(replay: object, live: object) -> Result[None]:
    """Refuse a cross-world read of a replay binding against a live binding.

    A replay binding is a different identity, deliberately incomparable
    (AD-29, AD-19, DEC-0160). Returned as a policy rejection, never merged.
    """
    if not isinstance(replay, ReplayBinding):
        return invalid(
            "replay",
            "incomparability reads the minted world=replay binding",
            given=repr(type(replay).__name__),
        )
    if not isinstance(live, BookBindingRecord):
        return invalid(
            "live",
            "incomparability compares against a CT-28 live BookBindingRecord",
            given=repr(type(live).__name__),
        )
    if replay.record.world is not World.REPLAY:
        return invalid(
            "replay",
            "the minted binding's world must be replay",
            given=replay.record.world.value,
        )
    if live.world is not World.LIVE:
        return invalid(
            "live",
            "the compared binding must be world=live",
            given=live.world.value,
        )
    live_epoch = live.fingerprint()
    if is_refusal(live_epoch):
        return live_epoch
    if replay.fingerprint == live_epoch.value:
        return invalid(
            "binding",
            "a replay binding must fingerprint apart from any live binding of the "
            "same Book instance; equal fingerprints would collapse two pots of money",
            fingerprint=replay.fingerprint.value,
        )
    return policy(
        "world",
        "a world=replay binding is a different identity from any live binding of "
        "the same Book instance, and incomparable to it (AD-29, DEC-0160)",
        live_fp=live_epoch.value.value,
        live_world=World.LIVE.value,
        replay_fp=replay.fingerprint.value,
        replay_world=World.REPLAY.value,
    )


def _replay_book_instance_id(
    *,
    book_fp1: Fingerprint,
    bms_fp1: Fingerprint,
    bot_fp1: Fingerprint,
    starting_capital: Money,
    seed_overridden: bool,
    venue_id: VenueId,
    account_id: str,
    clock: str,
    data_provenance: str,
    keys: Mapping[str, object],
) -> Result[BookInstanceId]:
    """Opaque BookInstanceId derived from the run's identity, never a clock."""
    derived = fingerprint(
        {
            "account_id": account_id,
            "bms_definition_fingerprint": bms_fp1.value,
            "book_definition_fingerprint": book_fp1.value,
            "bot_fp1": bot_fp1.value,
            "class": _BOOK_INSTANCE_CLASS,
            "clock": clock,
            "data_provenance": data_provenance,
            "keys": {key: keys[key] for key in keys},
            "seed_overridden": seed_overridden,
            "starting_capital": starting_capital.fp1_identity(),
            "venue_id": venue_id.value,
            "world": World.REPLAY.value,
        }
    )
    if is_refusal(derived):
        return invalid(
            "keys",
            "the replay Book-instance mint is not fp1-clean identity content",
            cause={str(item): derived.context[item] for item in derived.context},
        )
    return BookInstanceId.try_create(derived.value.value)


def _coerce_venue(value: object) -> Result[VenueId]:
    if isinstance(value, VenueId):
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid(
            "venue_id",
            "the replay binding tuple names a VenueId",
            given=repr(value),
        )
    return VenueId.try_create(token)


def _validate_seed_money(value: Money) -> Result[Money]:
    if value.currency != V1_NUMERAIRE:
        return policy(
            STARTING_CAPITAL_KEY,
            "starting_capital is Money in the V1 numeraire (USD); a non-USD seed is refused",
            given=value.currency,
            numeraire=V1_NUMERAIRE,
        )
    if value.value <= 0:
        return invalid(
            STARTING_CAPITAL_KEY,
            "starting_capital is a positive amount seeding the virtual ledger",
            given=value.value,
        )
    return Ok(value)


def _money_from_fp1(body: Mapping[str, object]) -> Result[Money]:
    """Rebuild Money from CT-01 fp1 identity content (num/den + storage scale)."""
    currency = clean_token(body.get("currency"))
    num = body.get("num")
    den = body.get("den")
    scale = body.get("storage_scale", MONEY_STORAGE_SCALE)
    if currency is None:
        return invalid(
            STARTING_CAPITAL_KEY,
            "a money identity names a currency",
            given=repr(body.get("currency")),
        )
    if isinstance(num, bool) or not isinstance(num, int):
        return invalid(
            STARTING_CAPITAL_KEY,
            "a money identity numerator is an integer",
            given=repr(num),
        )
    if isinstance(den, bool) or not isinstance(den, int) or den <= 0:
        return invalid(
            STARTING_CAPITAL_KEY,
            "a money identity denominator is a positive integer",
            given=repr(den),
        )
    if isinstance(scale, bool) or not isinstance(scale, int) or scale < 0:
        return invalid(
            STARTING_CAPITAL_KEY,
            "a money identity storage scale is a non-negative integer",
            given=repr(scale),
        )
    scaled = num * (10**scale)
    if scaled % den != 0:
        return invalid(
            STARTING_CAPITAL_KEY,
            "starting_capital must be representable at the money storage scale",
            num=num,
            den=den,
            scale=scale,
        )
    return Money.try_create(scaled // den, currency, scale)
