"""Reference usage — ship-no-corpus licensing gate (Story 18.2, B-11).

Executable::

    python qmb/examples/data_licensing_usage.py

Shows the things the licensing gate pins down:

1. Licence-tag taxonomy is an explicit interface (redistribution-ok /
   internal-only / denied / unknown); blank is unknown.
2. Tags that grant use pass only with a venue policy / operator ruling
   granting authority — never inferred by a provider adapter.
3. denied / unknown / absent refuse with (venue, symbol, window) + tag state.
4. A Dukascopy window with no recorded usage right stays catalogable;
   non-evidence use (infra-stress / strategy-logic smoke) is allowed;
   governed-evidence citation is refused.
5. Passing admissions carry licence tag + granting authority into CT-07
   lineage; the gate itself writes nothing.
6. Distribution / wheel check asserts zero corpus bytes.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

from qmb.data import (
    DUKASCOPY_PERSONAL_USE_POLICY,
    SourceWindowRef,
    admit_governed_evidence,
    allow_non_evidence_use,
    assert_distribution_has_no_corpus,
    entitlement_lineage_edge,
    licensing_gate_identity,
)
from qmf.core import RefusalCategory, Result, WriterId, fingerprint, is_ok, is_refusal
from qmf.data.dukascopy import PERSONAL_USE_LICENSE
from qmf.registry import EdgeType

T = TypeVar("T")

_START = 1_705_316_400_000_000_000
_END = _START + 3_600_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def _require(condition: object, what: str) -> None:
    if not condition:
        raise AssertionError(f"expected {what}")


def main() -> None:
    identity = licensing_gate_identity()
    _require(identity["writes"] is False, "gate writes nothing")
    _require(identity["ship_no_corpus"] is True, "ship-no-corpus posture")
    print(
        f"licensing gate: states={identity['license_tag_states']} "
        f"writes={identity['writes']} ship_no_corpus={identity['ship_no_corpus']}"
    )

    policies = {DUKASCOPY_PERSONAL_USE_POLICY.venue: DUKASCOPY_PERSONAL_USE_POLICY}
    licensed = SourceWindowRef(
        venue="dukascopy-fx",
        symbol="EURUSD",
        window_start_ns=_START,
        window_end_ns=_END,
        license_tag=PERSONAL_USE_LICENSE,
        source="dukascopy",
    )
    admitted = _unwrap(admit_governed_evidence(licensed, policies=policies), "admit")
    print(
        f"governed-evidence admitted: tag={admitted.license_tag.value} "
        f"authority={admitted.granting_authority}"
    )

    citing = _unwrap(fingerprint({"class": "citing-artifact", "id": "demo"}), "citing fp")
    writer = _unwrap(WriterId.try_create("node-a", "qmb", "license", "boot-1"), "writer")
    edge = _unwrap(
        entitlement_lineage_edge(admitted, citing_ref=citing, writer=writer),
        "CT-07 edge",
    )
    _require(edge.edge_type is EdgeType.OCCURRENCE_OF, "occurrence-of entitlement edge")
    print(
        f"CT-07 lineage: edge={edge.edge_type.value} "
        f"entitlement={admitted.lineage_payload()['granting_authority']}"
    )

    blank = SourceWindowRef(
        venue="dukascopy-fx",
        symbol="EURUSD",
        window_start_ns=_START,
        window_end_ns=_END,
        license_tag=None,
    )
    refused = admit_governed_evidence(blank, policies=policies)
    assert is_refusal(refused)
    _require(refused.category is RefusalCategory.POLICY_REJECTION, "policy rejection")
    _require(refused.context["license_tag"] == "unknown", "blank is unknown")
    _require(refused.context["venue"] == "dukascopy-fx", "venue in context")
    print(
        "unlicensed governed-evidence refused: "
        f"venue={refused.context['venue']} symbol={refused.context['symbol']} "
        f"tag={refused.context['license_tag']}"
    )

    _unwrap(allow_non_evidence_use(blank, use="infra-stress"), "infra-stress")
    _unwrap(allow_non_evidence_use(blank, use="strategy-logic-smoke"), "logic-smoke")
    print("non-evidence use allowed for blank Dukascopy window (catalogable)")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "pkg"
        root.mkdir()
        (root / "qmb").mkdir()
        (root / "qmb" / "__init__.py").write_text("# no corpus\n", encoding="utf-8")
        _unwrap(assert_distribution_has_no_corpus(root), "zero corpus")
    print("wheel/release check: distribution bundles zero corpus bytes")
    print("qmb data licensing gate ok")


if __name__ == "__main__":
    main()
