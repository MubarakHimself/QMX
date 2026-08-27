"""Fixture builders for the Epic 13 (qmb-substrate) independent audit.

These builders are TEST SCAFFOLDING only — they construct the registry/as-of/
fragment universe QMB consumes, using the same public construction API the
shipped usage examples use. They assert nothing about behaviour; the assertions
live in the ``test_l*`` modules and state what the REQUIREMENT demands, never
what the source happens to do. Source is read-only evidence.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TypeVar

from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import Money, UnitKind
from qmf.core.refusal import Result, is_ok
from qmf.registry import RegistrationRecord
from qmf.risk.grammar import (
    AdmissionImpact,
    TemplateSection,
    TemplateVariable,
    UiEditability,
)
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BmsDefinition,
    BookDefinition,
)

from qmb.config import (
    CLOCK_REPLAY,
    PROVENANCE_RECORDED,
    STARTING_CAPITAL_KEY,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.registryread import (
    AsOfSet,
    DatedPointer,
    PassiveHub,
    RegistryReadPort,
)

T = TypeVar("T")

CREATED_NS = 1_700_000_000_000_000_000
SEVERITY = "workspace-declared"
SEED = Money(value=1_000_000, currency="USD", scale=2)

DEFAULTS = {
    "account_id": "acct-replay",
    "clock": CLOCK_REPLAY,
    "data_provenance": PROVENANCE_RECORDED,
    "venue_id": "venue-replay",
}


def unwrap(result: Result[T], what: str = "value") -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"FIXTURE could not construct {what}: {result!r}")


def instant(ns: int = CREATED_NS) -> Instant:
    return unwrap(Instant.try_create(ns), "instant")


def writer(stream: str) -> WriterId:
    return unwrap(WriterId.try_create("node-a", "authoring", stream, "boot-1"), "writer")


def _money_variable(name: str, minor: int) -> TemplateVariable:
    return unwrap(
        TemplateVariable.try_create(
            name,
            UnitKind.MONEY,
            Money(value=minor, currency="USD", scale=2),
            UiEditability.UI_EDITABLE,
            AdmissionImpact.RESIGN,
        ),
        f"variable {name}",
    )


def _section(name: str, variable: TemplateVariable) -> TemplateSection:
    return unwrap(TemplateSection.try_create(name, {variable.name: variable}), f"section {name}")


def book_definition(*, loss_floor: int = 800_000) -> BookDefinition:
    return unwrap(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _money_variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _money_variable("loss_floor", loss_floor)),
                "exit_policy": _section("exit_policy", _money_variable("q", 100)),
            },
        ),
        "book definition",
    )


def bms_definition(*, exposure_ceiling: int = 50_000) -> BmsDefinition:
    return unwrap(
        BmsDefinition.try_create(
            BMS_CONTRACT_FORMAT_VERSION,
            {
                "accounting_rules": _section(
                    "accounting_rules", _money_variable("numeraire_unit", 1)
                ),
                "constraints": _section(
                    "constraints", _money_variable("exposure_ceiling", exposure_ceiling)
                ),
                "ksa_policy": _section("ksa_policy", _money_variable("posture", 1)),
                "reporting": _section("reporting", _money_variable("cadence", 1)),
            },
        ),
        "bms definition",
    )


def definition_record(kind: str, definition: BookDefinition | BmsDefinition) -> RegistrationRecord:
    stamped = unwrap(definition.fingerprint(), f"{kind} fp1")
    return unwrap(
        RegistrationRecord.try_create(
            kind,
            definition.contract_format_version,
            (stamped,),
            definition.fp1_identity(),
            writer(kind),
            0,
            instant(),
        ),
        f"{kind} record",
    )


def bot_record(alias: str = "mean-reversion") -> RegistrationRecord:
    return unwrap(
        RegistrationRecord.try_create(
            "bot-definition",
            1,
            [],
            {"class": "bot-definition", "alias": alias},
            writer("bot-definition"),
            0,
            instant(),
        ),
        "bot record",
    )


def build_universe(
    *,
    loss_floor: int = 800_000,
    exposure_ceiling: int = 50_000,
    bot_alias: str = "mean-reversion",
) -> SimpleNamespace:
    """The full registry universe QMB Epic-13 consumes: records, as-of set, port, fragments."""
    book = book_definition(loss_floor=loss_floor)
    bms = bms_definition(exposure_ceiling=exposure_ceiling)
    book_record = definition_record("book-definition", book)
    bms_record = definition_record("bms-definition", bms)
    bot = bot_record(bot_alias)
    as_of = unwrap(
        AsOfSet.try_create(
            instant(),
            records=(book_record, bms_record, bot),
            pointers=(
                unwrap(
                    DatedPointer.try_create("scalping", book_record.stable_id, instant()),
                    "book pointer",
                ),
                unwrap(
                    DatedPointer.try_create("account-bms", bms_record.stable_id, instant()),
                    "bms pointer",
                ),
                unwrap(
                    DatedPointer.try_create(bot_alias, bot.stable_id, instant()),
                    "bot pointer",
                ),
            ),
        ),
        "as-of set",
    )
    hub = unwrap(PassiveHub.try_create((as_of,)), "hub")
    port = unwrap(
        RegistryReadPort.try_create(hub, stale_evidence_severity=SEVERITY),
        "registry-read port",
    )
    book_fragment = unwrap(
        materialize_book_fragment(port, "scalping", writer("config-fragment")),
        "book fragment",
    )
    bms_fragment = unwrap(
        materialize_bms_fragment(port, "account-bms", writer("config-fragment")),
        "bms fragment",
    )
    return SimpleNamespace(
        book=book,
        bms=bms,
        book_record=book_record,
        bms_record=bms_record,
        bot=bot,
        bot_alias=bot_alias,
        as_of=as_of,
        hub=hub,
        port=port,
        book_fragment=book_fragment,
        bms_fragment=bms_fragment,
    )


def base_run_spec(*, bot_ref: object = "mean-reversion", seed: object = SEED) -> dict[str, object]:
    return {"bot": bot_ref, "horizon": 5, STARTING_CAPITAL_KEY: seed}
