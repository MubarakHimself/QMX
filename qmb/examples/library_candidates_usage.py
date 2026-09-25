"""Reference usage — candidate retain / filter / rank is a query (Story 34.3).

Executable::

    python qmb/examples/library_candidates_usage.py

Shows the things Story 34.3 / FR-W20 / FR-W24 pin down:

1. Candidate-set query is a read-time view over ledger lines, as-of sets
   including dev-zone Library kinds, and coordinated Experiment Ledger refs.
2. QMA staging is not read and copied rows are not persisted.
3. sweep.rank is this same view and publishes no copied-row artifact.
4. Ungoverned save is a return value; governed-without-QMA is JSON in the
   source run-dir; coordinated persistence is Epic 36.
5. A citation without a body is not a saved view.
6. Writing candidates into qmf-registry or a sqlite table is refused
   (DEC-0084 stays dead).
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import TypeVar

from qmb.ledger.line import LedgerLine
from qmb.registryread import (
    QUERY_SURFACES,
    SAVED_VIEW_FILENAME,
    AsOfSet,
    DatedPointer,
    ExperimentLedgerRef,
    PassiveHub,
    RegistryReadPort,
    candidate_set_identity,
    query_candidates,
    save_candidate_view,
)
from qmb.results import emit_measure
from qmb.sweep import rank_sweep
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import Money
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord

import qmb

T = TypeVar("T")
_NS = 1_700_000_000_000_000_000
_SWEEP = fingerprint({"class": "sweep", "id": "example-sweep"})
_BAR = fingerprint({"class": "book-bar", "id": "example-bar"})


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant() -> Instant:
    return _unwrap(Instant.try_create(_NS), "instant")


def _record(
    kind: str,
    note: str,
    machine: str,
    *,
    zone: str | None = None,
    origin: str | None = None,
) -> RegistrationRecord:
    writer = _unwrap(WriterId.try_create(machine, "authoring", kind, "boot-1"), "writer")
    body: dict[str, object] = {"alias": note, "note": note}
    if zone is not None:
        body["zone"] = zone
    if origin is not None:
        body["origin"] = origin
    return _unwrap(
        RegistrationRecord.try_create(kind, 1, [], body, writer, 0, _instant()),
        "record",
    )


def main() -> None:
    identity = candidate_set_identity()
    assert identity["surfaces"] == list(QUERY_SURFACES)
    assert identity["reads_staging"] is False
    assert identity["persists_copied_rows"] is False
    assert identity["opens_sqlite"] is False
    assert identity["mints_registry_kind"] is False
    assert identity["dec_0084_dead"] is True
    assert identity["rank"] == "sweep.rank"
    assert qmb.__version__ not in identity.values()
    sys.stdout.write(str("surfaces: " + ", ".join(QUERY_SURFACES)) + "\n")

    live = _record("bot-definition", "live-bot", "node-a", zone="live")
    dev = _record(
        "bot-definition",
        "dev-bot",
        "node-b",
        zone="dev",
        origin="qma-strategy-handle",
    )
    result = _record("performance-result", "run-a", "node-c")
    spec = _record("experiment-spec", "exp-a", "node-d")
    as_of = _unwrap(
        AsOfSet.try_create(
            _instant(),
            records=(live, dev, result, spec),
            pointers=(
                _unwrap(DatedPointer.try_create("live-bot", live.stable_id, _instant()), "ptr"),
                _unwrap(DatedPointer.try_create("dev-bot", dev.stable_id, _instant()), "ptr"),
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
    sweep_id = _unwrap(_SWEEP, "sweep")
    measure = _unwrap(emit_measure("net_profit", Money(value=3000, currency="USD", scale=2)), "m")
    line = LedgerLine(
        run_id=_unwrap(fingerprint({"run": "c1"}), "run"),
        role="confirmation",
        world=World.REPLAY,
        result_label={"class": "result-label", "world": World.REPLAY.value},
        book_bar_fp1=_unwrap(_BAR, "bar"),
        measures=(measure.fp1_identity(),),
        ct32_fingerprint=result.stable_id,
        sweep_coordinates={
            "bar_spec": {"kind": "time-interval", "seconds": 60},
            "class": "qmb-sweep-coordinates",
            "format_version": 1,
            "instrument": "EURUSD",
            "param_hash": "p1",
            "sweep_id": sweep_id.value,
        },
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
        query_candidates(
            port=port,
            ledger_lines=(line,),
            world=World.REPLAY,
            experiment_refs=(exp,),
            lane="coordinated",
        ),
        "query",
    )
    cites = {item.cite() for item in found.candidates}
    assert dev.stable_id.value in cites
    sys.stdout.write("dev-zone candidate included\n")

    ranked = _unwrap(
        query_candidates(
            ledger_lines=(line,),
            world=World.REPLAY,
            sweep_id=sweep_id,
            objective="net_profit",
        ),
        "rank query",
    )
    library = _unwrap(
        rank_sweep((line,), sweep_id=sweep_id, objective="net_profit", world=World.REPLAY),
        "rank_sweep",
    )
    assert ranked.ranking is not None
    assert ranked.ranking.fp1_identity() == library.fp1_identity()
    assert ranked.ranking.publishes_never_acts is True
    assert qmb.sweep_rank_identity()["candidate_set_view"] is True
    sys.stdout.write("sweep.rank is the candidate-set rank\n")

    ungoverned = _unwrap(save_candidate_view(found, home="ungoverned"), "ungoverned")
    assert ungoverned.durable is False
    assert ungoverned.is_library_object is False
    sys.stdout.write("ungoverned is a return value\n")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        governed = _unwrap(
            save_candidate_view(found, home="governed", run_dir=root),
            "governed",
        )
        sidecar = root / SAVED_VIEW_FILENAME
        assert sidecar.is_file()
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        assert payload["method"] == "candidate-set"
        assert governed.durable is True
        sys.stdout.write("governed sidecar written\n")

    cited = save_candidate_view(home="ungoverned", cite=dev.stable_id)
    assert is_refusal(cited) and cited.category is RefusalCategory.POLICY_REJECTION
    sys.stdout.write("citation without a body refused\n")

    sqlite = query_candidates(sqlite=True)
    minted = query_candidates(mint_registry_kind=True)
    assert is_refusal(sqlite) and sqlite.context["dec_0084_dead"] is True
    assert is_refusal(minted) and minted.context["mints_registry_kind"] is False
    sys.stdout.write("sqlite and registry-kind refused\n")

    staging = query_candidates(port=port, staging=({"proposal": 1},))
    assert is_refusal(staging) and staging.context["reads_staging"] is False
    sys.stdout.write("staging is not read\n")
    sys.stdout.write(f"qmb {qmb.__version__}\n")
    sys.stdout.write("library candidates ok\n")


if __name__ == "__main__":
    main()
