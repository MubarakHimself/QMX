"""Reference usage — the single registry-read port over as-of sets (Story 13.2).

Executable::

    python qmb/examples/registryread_usage.py

Shows the things B-15 / Story 13.2 pin down:

1. Registry state is an immutable fingerprinted as-of set
   (``registry_as_of`` instant + set fingerprint), never a live query.
2. ONE library-owned registry-read port serves every consumer. Doors do not
   hold a second cache. Resolve by ``fp1``; a human alias is UX only.
3. ``name@version`` is not a legal identity cite.
4. A ref a fresher as-of shows superseded returns AD-11 stale evidence at
   ``registry:qmb_stale_evidence_severity`` — returned, not raised.
5. A sweep freezes one as-of at batch admission; thereafter fragments
   resolve by explicit fingerprint, never ``name@latest``.
6. The hub is dumb passive storage — never the dead DEC-0084 central service.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.registryread import (
    HUB_KIND,
    STALE_EVIDENCE_SEVERITY_KEY,
    AsOfSet,
    DatedPointer,
    PassiveHub,
    RegistryReadPort,
    SupersedesRef,
)
from qmf.core.chrono import Instant, WriterId
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord

import qmb

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _writer(machine: str) -> WriterId:
    return _unwrap(
        WriterId.try_create(machine, "authoring", "book-definition", "boot-1"),
        "writer",
    )


def _record(note: str, machine: str) -> RegistrationRecord:
    return _unwrap(
        RegistrationRecord.try_create(
            "book-definition",
            1,
            [],
            {"alias": "scalping", "note": note},
            _writer(machine),
            0,
            _instant(),
        ),
        "record",
    )


def main() -> None:
    first = _record("v1", "node-a")
    older = _unwrap(
        AsOfSet.try_create(
            _instant(_CREATED_NS),
            records=(first,),
            pointers=(
                _unwrap(
                    DatedPointer.try_create("scalping", first.stable_id, _instant(_CREATED_NS)),
                    "pointer",
                ),
            ),
        ),
        "older as-of set",
    )
    hub = _unwrap(PassiveHub.try_create((older,)), "hub")
    assert hub.kind == HUB_KIND == "passive-storage"
    port = _unwrap(
        RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY),
        "registry-read port",
    )
    resolved = _unwrap(port.resolve("scalping"), "alias resolve")
    assert resolved.cite() == first.stable_id.value
    print(f"alias scalping cites {resolved.cite()}")

    banned = port.resolve("scalping@1")
    assert is_refusal(banned) and banned.category is RefusalCategory.INVALID_INPUT
    print("name@version refused: invalid input")

    second = _record("v2", "node-b")
    fresher = _unwrap(
        AsOfSet.try_create(
            _instant(_CREATED_NS + 1),
            records=(first, second),
            pointers=(
                _unwrap(
                    DatedPointer.try_create(
                        "scalping", second.stable_id, _instant(_CREATED_NS + 1)
                    ),
                    "fresher pointer",
                ),
            ),
            supersedes=(
                _unwrap(
                    SupersedesRef.try_create(second.stable_id, first.stable_id),
                    "supersedes",
                ),
            ),
        ),
        "fresher as-of set",
    )
    grown = _unwrap(hub.with_set(fresher), "hub with fresher as-of")
    current = _unwrap(
        RegistryReadPort.try_create(grown, stale_evidence_severity=_SEVERITY),
        "port over fresher hub",
    )
    stale_ref = current.resolve(first.stable_id)
    assert is_refusal(stale_ref) and stale_ref.category is RefusalCategory.STALE_EVIDENCE
    assert stale_ref.context["severity_key"] == STALE_EVIDENCE_SEVERITY_KEY
    assert stale_ref.context["severity"] == _SEVERITY
    print(f"superseded ref: stale evidence (severity_key={stale_ref.context['severity_key']})")

    frozen = _unwrap(
        RegistryReadPort.try_create(
            grown,
            stale_evidence_severity=_SEVERITY,
            bound=older,
            frozen=True,
        ),
        "frozen sweep port",
    )
    trial = _unwrap(frozen.resolve(first.stable_id), "frozen fp1 resolve")
    assert trial.cite() == first.stable_id.value
    late = frozen.resolve("scalping@latest")
    assert is_refusal(late) and late.category is RefusalCategory.INVALID_INPUT
    print("sweep freeze: fp1 resolved; name@latest refused")
    print(f"qmb {qmb.__version__}")
    print("registry-read port ok")


if __name__ == "__main__":
    main()
