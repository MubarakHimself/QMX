"""Reference usage — one resolved run-config from fixed-precedence layers (Story 13.4).

Executable::

    python qmb/examples/run_config_usage.py

Shows the things B-3 / Story 13.4 pin down:

1. Layers compile with fixed precedence: invocation flags > run spec (bot) >
   BMS fragment > Book fragment > workspace defaults. Same inputs yield a
   byte-identical artifact.
2. A Book/BMS key collision is a compile-time typed refusal; in any sanctioned
   overlap BMS outranks Book.
3. The resolved artifact cites Book, BMS, bot, and any binding by fp1, never
   name@version, even when the invocation used a human alias.
4. The artifact stamps an AD-5 format version and declares AD-10 identity-vs-
   display classification. Every door computes the same fingerprint; that
   fingerprint is the run-id root and the ledger key. The artifact path is
   named by the run id.
5. A replay clock bound to synthetic-tainted data is invalid input — world is
   provenance-derived and B-7 wins.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.config import (
    CLOCK_REPLAY,
    PROVENANCE_RECORDED,
    PROVENANCE_SYNTHETIC_TAINTED,
    SANCTIONED_OVERLAP_KEYS,
    compile_run_config,
    ledger_key,
    materialize_bms_fragment,
    materialize_book_fragment,
    merge_book_bms_keys,
    run_id_root,
)
from qmb.doors import api
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import Money, UnitKind
from qmf.core.fingerprint import World, canonical_bytes
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord
from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BmsDefinition,
    BookDefinition,
)

import qmb

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"
_SEED = Money(value=1_000_000, currency="USD", scale=2)
_DEFAULTS = {
    "account_id": "acct-replay",
    "clock": CLOCK_REPLAY,
    "data_provenance": PROVENANCE_RECORDED,
    "fill": "default-fill",
    "venue_id": "venue-replay",
}


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _writer(stream: str) -> WriterId:
    return _unwrap(
        WriterId.try_create("node-a", "authoring", stream, "boot-1"),
        "writer",
    )


def _money_variable(name: str, minor: int) -> TemplateVariable:
    return _unwrap(
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
    return _unwrap(TemplateSection.try_create(name, {variable.name: variable}), f"section {name}")


def _book() -> BookDefinition:
    return _unwrap(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _money_variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _money_variable("loss_floor", 800_000)),
                "exit_policy": _section("exit_policy", _money_variable("q", 100)),
            },
        ),
        "book definition",
    )


def _bms() -> BmsDefinition:
    return _unwrap(
        BmsDefinition.try_create(
            BMS_CONTRACT_FORMAT_VERSION,
            {
                "accounting_rules": _section(
                    "accounting_rules", _money_variable("numeraire_unit", 1)
                ),
                "constraints": _section("constraints", _money_variable("exposure_ceiling", 50_000)),
                "ksa_policy": _section("ksa_policy", _money_variable("posture", 1)),
                "reporting": _section("reporting", _money_variable("cadence", 1)),
            },
        ),
        "bms definition",
    )


def _definition_record(kind: str, definition: BookDefinition | BmsDefinition) -> RegistrationRecord:
    stamped = _unwrap(definition.fingerprint(), f"{kind} fp1")
    return _unwrap(
        RegistrationRecord.try_create(
            kind,
            definition.contract_format_version,
            (stamped,),
            definition.fp1_identity(),
            _writer(kind),
            0,
            _instant(),
        ),
        f"{kind} record",
    )


def _bot_record() -> RegistrationRecord:
    return _unwrap(
        RegistrationRecord.try_create(
            "bot-definition",
            1,
            [],
            {"class": "bot-definition", "alias": "mean-reversion"},
            _writer("bot-definition"),
            0,
            _instant(),
        ),
        "bot record",
    )


def main() -> None:
    book = _book()
    bms = _bms()
    book_record = _definition_record("book-definition", book)
    bms_record = _definition_record("bms-definition", bms)
    bot = _bot_record()
    as_of = _unwrap(
        AsOfSet.try_create(
            _instant(),
            records=(book_record, bms_record, bot),
            pointers=(
                _unwrap(
                    DatedPointer.try_create("scalping", book_record.stable_id, _instant()),
                    "book pointer",
                ),
                _unwrap(
                    DatedPointer.try_create("mean-reversion", bot.stable_id, _instant()),
                    "bot pointer",
                ),
            ),
        ),
        "as-of set",
    )
    port = _unwrap(
        RegistryReadPort.try_create(
            _unwrap(PassiveHub.try_create((as_of,)), "hub"),
            stale_evidence_severity=_SEVERITY,
        ),
        "port",
    )
    book_fragment = _unwrap(
        materialize_book_fragment(port, "scalping", _writer("config-fragment")),
        "book fragment",
    )
    bms_fragment = _unwrap(
        materialize_bms_fragment(port, bms_record.stable_id, _writer("config-fragment")),
        "bms fragment",
    )

    compiled = _unwrap(
        compile_run_config(
            port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec={"bot": "mean-reversion", "horizon": 5, "starting_capital": _SEED},
            invocation_flags={"fill": "flag-fill"},
            workspace_defaults=_DEFAULTS,
        ),
        "resolved run-config",
    )
    again = _unwrap(
        compile_run_config(
            port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec={"bot": "mean-reversion", "horizon": 5, "starting_capital": _SEED},
            invocation_flags={"fill": "flag-fill"},
            workspace_defaults=_DEFAULTS,
        ),
        "second compile",
    )
    assert compiled.fingerprint == again.fingerprint
    assert _unwrap(compiled.artifact_bytes(), "bytes") == _unwrap(again.artifact_bytes(), "bytes")
    assert compiled.keys["fill"] == "flag-fill"
    assert compiled.keys["horizon"] == 5
    assert compiled.world is World.REPLAY
    print("same inputs yield a byte-identical resolved artifact")

    assert compiled.bot_fp1 == bot.stable_id
    assert compiled.book_fp1 == book_fragment.source_fp1
    assert compiled.bms_fp1.value.startswith("fp1:sha256:")
    assert "@" not in compiled.book_fp1.value
    named = compile_run_config(
        port,
        book_fragment=book_fragment,
        bms_fragment=bms_fragment,
        run_spec={"bot": "mean-reversion@1"},
        workspace_defaults=_DEFAULTS,
    )
    assert is_refusal(named)
    assert named.category is RefusalCategory.INVALID_INPUT
    print(f"cites by fp1, never name@version; bot {compiled.bot_fp1.value}")

    collision = merge_book_bms_keys(
        {"admission": {"x": 1}, "accounting": {"stolen": 1}},
        {"accounting": {"y": 1}},
    )
    assert is_refusal(collision)
    assert frozenset() == SANCTIONED_OVERLAP_KEYS
    ranked = _unwrap(
        merge_book_bms_keys(
            {"admission": {"x": 1}, "reporting": {"from": "book"}},
            {"reporting": {"from": "bms"}},
            sanctioned_overlap={"reporting"},
        ),
        "sanctioned overlap",
    )
    assert ranked["reporting"] == {"from": "bms"}
    print("Book/BMS collision is a compile-time refusal; sanctioned overlap BMS outranks Book")

    assert run_id_root(compiled) == compiled.fingerprint == ledger_key(compiled)
    door = _unwrap(
        api.compile_run_config(
            port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec={"bot": "mean-reversion", "horizon": 5, "starting_capital": _SEED},
            invocation_flags={"fill": "flag-fill"},
            workspace_defaults=_DEFAULTS,
        ),
        "api door compile",
    )
    assert door.fingerprint == compiled.fingerprint
    path = compiled.artifact_relative_path()
    assert path.endswith("/run-config.json")
    assert ":" not in path.split("/")[0]
    identity = compiled.fp1_identity()
    assert "package_version" not in identity
    assert qmb.__version__ not in str(identity)
    assert _unwrap(canonical_bytes(identity), "canonical") == _unwrap(
        compiled.artifact_bytes(), "artifact"
    )
    print(f"run-id root / ledger key {compiled.fingerprint.value}")
    print(f"artifact path {path}")

    tainted = compile_run_config(
        port,
        book_fragment=book_fragment,
        bms_fragment=bms_fragment,
        run_spec={"bot": "mean-reversion"},
        workspace_defaults={
            "clock": CLOCK_REPLAY,
            "data_provenance": PROVENANCE_SYNTHETIC_TAINTED,
        },
    )
    assert is_refusal(tainted)
    assert tainted.category is RefusalCategory.INVALID_INPUT
    print("replay clock + synthetic-tainted data: invalid input")

    print(f"qmb {qmb.__version__}")
    print("resolved run-config ok")


if __name__ == "__main__":
    main()
