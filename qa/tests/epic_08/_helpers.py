"""Shared builders and fakes for the Epic 8 (qmf-venue) independent QA suite.

These helpers ONLY construct public objects and drive the public API. They encode
no assertions about behaviour — every assertion lives in a test module and is drawn
from a contract/scenario/AC oracle, never from the implementation. All fakes are
injected seams (sinks, secret store, probe transport, clock) so no live venue is
ever contacted (test-design-qa.md "Not in Scope"; DEC-0135).
"""

from __future__ import annotations

from qmf.core import (
    Account,
    AccountRole,
    Duration,
    Instant,
    Instrument,
    Money,
    MonotonicReading,
    Ok,
    Price,
    PriceDelta,
    Quantity,
    RefusalCategory,
    Result,
    Retryability,
    SecretRef,
    SecretValue,
    TypedRefusal,
    VenueId,
    World,
    is_ok,
    unpersistable,
)
from qmf.venue import (
    AccountBinding,
    CapabilityDeclaration,
    CapabilityField,
    CapabilityFieldName,
    Command,
    CommandOutcomeResolver,
    ConnectionManager,
    ErrorMap,
    ErrorMapRow,
    FieldMarking,
    OrderParameters,
    OrderType,
    ProtectionAmendment,
    ProtectionSide,
    ProtoArtifact,
    SubmissionOutcomeClass,
    TimeInForce,
    venue_writer_id,
)

# --- unwrap ----------------------------------------------------------------


def ok(result: Result[object]) -> object:
    """Assert the Result is the success arm and return its value (fixture-side only)."""
    assert is_ok(result), f"expected Ok, got refusal: {result!r}"
    return result.value


# --- nouns -----------------------------------------------------------------

MACHINE = "vps-1"
ADAPTER_ROLE = "ctrader-adapter"
BOOT_EPOCH = "boot-epoch-1"
SESSION_EPOCH = "session-epoch-1"
DIGEST = "sha256:" + "a" * 64
PINNED_TAG = 91


def mk_venue(value: str = "VEN-CTRADER-DEMO") -> VenueId:
    return ok(VenueId.try_create(value))


def mk_account(venue: VenueId, account_id: str = "ACC-1", role: object = AccountRole.DEMO) -> Account:
    return ok(Account.try_create(account_id, venue, role))


def mk_instrument(venue: VenueId, symbol: str = "EURUSD") -> Instrument:
    return ok(Instrument.try_create(venue, symbol))


def mk_secret_ref(value: str = "sref-000000000001") -> SecretRef:
    return ok(SecretRef.try_create(value))


def mk_secret_value(ref: SecretRef, secret: str = "plaintext-crown-jewel") -> SecretValue:
    return ok(SecretValue.try_create(ref, secret))


def mk_price(value: int, instrument: Instrument, scale: int = 5) -> Price:
    return ok(Price.try_create(value, instrument, scale))


def mk_delta(value: int, instrument: Instrument, scale: int = 5) -> PriceDelta:
    return ok(PriceDelta.try_create(value, instrument, scale))


def mk_qty(value: int, unit: str = "lot", scale: int = 2) -> Quantity:
    return ok(Quantity.try_create(value, unit, scale))


def mk_money(value: int, currency: str = "USD", scale: int = 2) -> Money:
    return ok(Money.try_create(value, currency, scale))


def mk_instant(value_ns: int) -> Instant:
    return ok(Instant.try_create(value_ns))


def mk_duration(value_ns: int) -> Duration:
    return ok(Duration.try_create(value_ns))


def mk_mono(value_ns: int, boot: str = BOOT_EPOCH) -> MonotonicReading:
    return ok(MonotonicReading.try_create(value_ns, boot))


# --- injected sinks --------------------------------------------------------


class RecordingSink:
    """A single object implementing emit/append/write (satisfies all three sink
    protocols). Records every payload in call order; a per-instance ``fail`` flag
    makes every command-path call return a CT-04 ``storage failure`` refusal."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, object]] = []

    def _settle(self, kind: str, payload: object) -> Result[object]:
        self.calls.append((kind, payload))
        if self.fail:
            return unpersistable(f"fake {kind} sink is down")
        return Ok(_ACK())

    def emit(self, observation: object) -> Result[object]:
        return self._settle("emit", observation)

    def append(self, event: object) -> Result[object]:
        return self._settle("append", event)

    def write(self, record: object) -> Result[object]:
        return self._settle("write", record)


class _ACK:
    """A stand-in SinkAck payload (the sinks return Ok(SinkAck) in production; the
    connection manager only branches on is_refusal, so any Ok payload is fine)."""


class FakeSecretStore:
    """A fake SecretStore (read + atomic_replace). Configurable to fail either op."""

    def __init__(
        self,
        *,
        values: dict[SecretRef, SecretValue] | None = None,
        read_fails: bool = False,
        replace_fails: bool = False,
    ) -> None:
        self._values: dict[SecretRef, SecretValue] = dict(values or {})
        self.read_fails = read_fails
        self.replace_fails = replace_fails

    def read(self, ref: SecretRef) -> Result[SecretValue]:
        if self.read_fails or ref not in self._values:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.NO,
                context={"field": "credential", "secret_ref": ref.value},
            )
        return Ok(self._values[ref])

    def atomic_replace(self, ref: SecretRef, new_value: SecretValue) -> Result[SecretRef]:
        if self.replace_fails:
            return unpersistable("fake store cannot durably replace the secret")
        self._values[ref] = new_value
        return Ok(ref)


def build_connection_manager(
    venue: VenueId,
    account: Account,
    *,
    secret_store: FakeSecretStore | None = None,
    observation_sink: RecordingSink | None = None,
    journal_sink: RecordingSink | None = None,
    record_sink: RecordingSink | None = None,
) -> ConnectionManager:
    writer = ok(venue_writer_id(MACHINE, ADAPTER_ROLE, venue, account, BOOT_EPOCH))
    cm = ConnectionManager.try_create(
        writer,
        secret_store if secret_store is not None else FakeSecretStore(),
        observation_sink if observation_sink is not None else RecordingSink(),
        journal_sink if journal_sink is not None else RecordingSink(),
        record_sink if record_sink is not None else RecordingSink(),
    )
    return ok(cm)


# --- capability declaration ------------------------------------------------

# The CT-18 measured-at-connection roster fields (CT-18 invariants: settlement
# currency, margin surface, value factor, reconciliation lookback, protection
# capabilities, plus instrument-metadata and equity nativeness that ride the
# profile). Everything else is a static declaration value.
DEFAULT_MEASURED: frozenset[CapabilityFieldName] = frozenset(
    {
        CapabilityFieldName.SETTLEMENT_CURRENCY,
        CapabilityFieldName.MARGIN_SURFACE,
        CapabilityFieldName.VALUE_FACTOR_METADATA,
        CapabilityFieldName.RECONCILIATION_LOOKBACK,
        CapabilityFieldName.PROTECTION_CAPABILITIES,
        CapabilityFieldName.INSTRUMENT_METADATA_SURFACE,
        CapabilityFieldName.EQUITY_NATIVENESS,
    }
)

_STATIC_VALUES: dict[CapabilityFieldName, object] = {
    CapabilityFieldName.MARKET_DATA_KINDS: ["tick", "bar"],
    CapabilityFieldName.ORDER_PARAMETER_SUBSET: {
        "order_types": ["market", "limit", "stop", "stop-limit"],
        "time_in_force": ["good-till-cancel"],
    },
    CapabilityFieldName.COMMAND_SCOPES: [
        "account",
        "account-binding",
        "instrument-within-binding",
    ],
    CapabilityFieldName.ACKNOWLEDGEMENT_MODES: {"place_order": "explicit-event"},
    CapabilityFieldName.POSITION_MODEL: "hedging",
    CapabilityFieldName.SESSION_TOPOLOGY: {"connections": 2},
    CapabilityFieldName.THROTTLE_SCOPE: "connection",
    CapabilityFieldName.RATE_LIMITS: {
        "non_historical_per_second": 50,
        "historical_per_second": 5,
        "scope": "connection",
    },
    CapabilityFieldName.SPAN_CAPS_AND_PAGING: {
        "historical_tick_span_cap_ms": 604800000,
        "paging": "hasMore",
    },
    CapabilityFieldName.TOKEN_LIFECYCLE_CLASS: {
        "access_token": "approximately-30-day",
        "refresh_token": "never-expiring",
    },
    CapabilityFieldName.SERVER_CLOCK_AVAILABILITY: False,
    CapabilityFieldName.ATTRIBUTION_LABEL_SUPPORT: False,
    CapabilityFieldName.PROTECTION_PRIMITIVES: ["suspend-new", "drain", "close_all"],
    CapabilityFieldName.COMMAND_ID_MAPPING: {"injective_total": False},
    CapabilityFieldName.FLOAT_TARGET_SCALES: {
        "execution_price": "declared-digits",
        "money": "account-money-exponent",
        "market_data": 5,
    },
    CapabilityFieldName.VERIFICATION_SUITE: [
        "spot-timestamp-unit",
        "daily-boundary",
        "bar-basis",
        "pip-formula",
        "money-exponent",
    ],
}


def build_proto_artifact(tag: int = PINNED_TAG, digest: str = DIGEST) -> ProtoArtifact:
    return ok(ProtoArtifact.try_create("openapi-proto-messages", tag, digest))


def build_error_map(
    *,
    version: int = 1,
    reject_code: str = "ORDER-REJECTED",
    reject_context: str = "place_order",
    unknown_code: str = "TEMP-GLITCH",
    unknown_context: str = "place_order",
) -> ErrorMap:
    reject_row = ok(
        ErrorMapRow.try_create(
            reject_code,
            reject_context,
            RefusalCategory.POLICY_REJECTION,
            Retryability.NO,
            SubmissionOutcomeClass.REJECTED_BY_VENUE,
        )
    )
    unknown_row = ok(
        ErrorMapRow.try_create(
            unknown_code,
            unknown_context,
            RefusalCategory.TRANSIENT_VENUE_FAILURE,
            Retryability.AFTER_CONDITION,
            SubmissionOutcomeClass.UNKNOWN,
            "the venue recovers",
        )
    )
    return ok(ErrorMap.try_create(version, [reject_row, unknown_row]))


def build_declaration(
    *,
    measured: frozenset[CapabilityFieldName] | None = None,
    error_map: ErrorMap | None = None,
    proto: ProtoArtifact | None = None,
    adapter_version: str = "1.0.0",
    injective_total: bool = False,
    command_scopes: list[str] | None = None,
) -> CapabilityDeclaration:
    measured_set = DEFAULT_MEASURED if measured is None else measured
    fields: list[CapabilityField] = []
    for name in CapabilityFieldName:
        if name in measured_set:
            fields.append(ok(CapabilityField.measured(name)))
        else:
            value = _STATIC_VALUES[name]
            if name is CapabilityFieldName.COMMAND_ID_MAPPING:
                value = {"injective_total": injective_total}
            if name is CapabilityFieldName.COMMAND_SCOPES and command_scopes is not None:
                value = command_scopes
            fields.append(ok(CapabilityField.static(name, value)))
    decl = CapabilityDeclaration.try_create(
        adapter_version,
        proto if proto is not None else build_proto_artifact(),
        error_map if error_map is not None else build_error_map(),
        fields,
    )
    return ok(decl)


def build_resolver(declaration: CapabilityDeclaration | None = None) -> CommandOutcomeResolver:
    return ok(
        CommandOutcomeResolver.try_create(
            declaration if declaration is not None else build_declaration()
        )
    )


# --- commands --------------------------------------------------------------


def build_place_order(
    venue: VenueId,
    account: Account,
    instrument: Instrument,
    *,
    ordinal: int = 0,
    session_epoch: str = SESSION_EPOCH,
    order_type: object = OrderType.MARKET,
    quantity: Quantity | None = None,
) -> Command:
    params = ok(
        OrderParameters.try_create(
            order_type,
            TimeInForce.GOOD_TILL_CANCEL,
            quantity if quantity is not None else mk_qty(100),
        )
    )
    return ok(Command.place_order(venue, account, session_epoch, ordinal, params))


def build_cancel_order(
    venue: VenueId,
    account: Account,
    *,
    ordinal: int = 1,
    subject: str = "order-abc",
    session_epoch: str = SESSION_EPOCH,
) -> Command:
    return ok(Command.cancel_order(venue, account, session_epoch, ordinal, subject))


def build_close_position(
    venue: VenueId,
    account: Account,
    *,
    ordinal: int = 2,
    scope: object = "account-binding",
    subject: str = "position-xyz",
    session_epoch: str = SESSION_EPOCH,
) -> Command:
    return ok(
        Command.close_position(venue, account, session_epoch, ordinal, scope, subject)
    )


def build_amend_protection(
    venue: VenueId,
    account: Account,
    instrument: Instrument,
    *,
    ordinal: int = 3,
    subject: str = "position-xyz",
    session_epoch: str = SESSION_EPOCH,
    new_distance_value: int = 40,
    original_distance_value: int = 50,
    side: object = ProtectionSide.STOP,
) -> Command:
    kwargs = {}
    if side is ProtectionSide.STOP or side == "stop":
        kwargs["original_risk_distance"] = mk_delta(original_distance_value, instrument)
    amendment = ok(
        ProtectionAmendment.try_create(
            side,
            mk_delta(new_distance_value, instrument),
            mk_price(110000, instrument),
            **kwargs,
        )
    )
    return ok(
        Command.amend_protection(venue, account, session_epoch, ordinal, amendment, subject)
    )


def make_account_binding(
    venue: VenueId, account: Account, secret_ref: SecretRef, world: object = World.LIVE
) -> AccountBinding:
    return ok(AccountBinding.try_create(venue, account, world, secret_ref))
