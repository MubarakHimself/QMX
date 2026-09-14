"""Reference usage — Library search reads three existing surfaces (Story 34.2).

Executable::

    python qmb/examples/library_search_usage.py

Shows the things Story 34.2 / FR-W19 / FR-W20 pin down:

1. Search by kind + fp1 reads the B-15 as-of port, the ledger merge view,
   and coordinated Experiment Ledger refs — never a fourth store.
2. Saved-view hits cite the source CT-32 fp1 (or a saved-view JSON fp1).
3. QMA staging is not read.
4. Frozen as-of / fingerprint resolution from Story 13.2 still holds.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.ledger.line import LedgerLine
from qmb.registryread import (
    QUERY_SURFACES,
    SURFACE_EXPERIMENT_LEDGER,
    SURFACE_LEDGER_MERGE,
    SURFACE_REGISTRY_AS_OF,
    AsOfSet,
    DatedPointer,
    ExperimentLedgerRef,
    PassiveHub,
    RegistryReadPort,
    SavedViewCite,
    library_search_identity,
    search_library,
)
from qmf.core.chrono import Instant, WriterId
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord

import qmb

T = TypeVar("T")
_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant() -> Instant:
    return _unwrap(Instant.try_create(_NS), "instant")


def _record(kind: str, note: str, machine: str) -> RegistrationRecord:
    writer = _unwrap(WriterId.try_create(machine, "authoring", kind, "boot-1"), "writer")
    return _unwrap(
        RegistrationRecord.try_create(
            kind, 1, [], {"alias": note, "note": note}, writer, 0, _instant()
        ),
        "record",
    )


def main() -> None:
    identity = library_search_identity()
    assert identity["surfaces"] == list(QUERY_SURFACES)
    assert identity["opens_fourth_store"] is False
    assert identity["reads_staging"] is False
    assert identity["holds_cache"] is False
    assert qmb.__version__ not in identity.values()
    print("surfaces: " + ", ".join(QUERY_SURFACES))

    bot = _record("bot-definition", "scalping", "node-a")
    result = _record("performance-result", "run-a", "node-b")
    spec = _record("experiment-spec", "exp-a", "node-c")
    as_of = _unwrap(
        AsOfSet.try_create(
            _instant(),
            records=(bot, result, spec),
            pointers=(
                _unwrap(DatedPointer.try_create("scalping", bot.stable_id, _instant()), "ptr"),
                _unwrap(DatedPointer.try_create("run-a", result.stable_id, _instant()), "ptr"),
            ),
        ),
        "as-of",
    )
    port = _unwrap(
        RegistryReadPort.try_create(
            _unwrap(PassiveHub.try_create((as_of,)), "hub"),
            stale_evidence_severity="workspace-declared",
        ),
        "port",
    )
    line = LedgerLine(
        run_id=_unwrap(fingerprint({"run": "run-a"}), "run"),
        role="confirmation",
        world=World.REPLAY,
        result_label={"class": "result-label", "world": World.REPLAY.value},
        book_bar_fp1=_unwrap(fingerprint({"bar": "run-a"}), "bar"),
        measures=(),
        ct32_fingerprint=result.stable_id,
    )
    exp = _unwrap(
        ExperimentLedgerRef.try_create(
            "experiment-ledger:" + spec.stable_id.value,
            spec.stable_id,
            cited_fp1=result.stable_id,
            kind="performance-result",
        ),
        "experiment ref",
    )
    found = _unwrap(
        search_library(
            "performance-result",
            fp1=result.stable_id,
            port=port,
            ledger_lines=(line,),
            world=World.REPLAY,
            experiment_refs=(exp,),
        ),
        "search",
    )
    surfaces = {hit.surface for hit in found.hits}
    assert surfaces == {SURFACE_REGISTRY_AS_OF, SURFACE_LEDGER_MERGE, SURFACE_EXPERIMENT_LEDGER}
    print("three-surface search hit count: " + str(len(found.hits)))

    alias = _unwrap(search_library("bot-definition", fp1="scalping", port=port), "alias")
    assert alias.hits[0].cite() == bot.stable_id.value
    print("as-of alias resolved by fp1")

    frozen = port.admit_batch()
    banned = search_library("bot-definition", fp1="scalping@latest", port=frozen)
    assert is_refusal(banned) and banned.category is RefusalCategory.INVALID_INPUT
    print("name@version refused; frozen as-of still holds")

    view = _unwrap(SavedViewCite.try_create(result.stable_id), "saved-view")
    cited = _unwrap(
        search_library("saved-view", saved_views=(view,), ledger_lines=(line,), world=World.REPLAY),
        "saved-view search",
    )
    assert cited.hits[0].cite() == result.stable_id.value
    assert cited.hits[0].is_registry_kind is False
    print("saved-view cites source CT-32 fp1; not a registry kind")

    staging = search_library("bot-definition", port=port, staging=({"proposal": 1},))
    assert is_refusal(staging) and staging.context["reads_staging"] is False
    print("staging is not read")

    store = search_library("bot-definition", store="library.sqlite")
    assert is_refusal(store) and store.context["opens_fourth_store"] is False
    print("fourth store refused")
    print(f"qmb {qmb.__version__}")
    print("library search ok")


if __name__ == "__main__":
    main()
