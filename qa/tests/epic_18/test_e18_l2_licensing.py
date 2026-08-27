"""Epic 18 · L2 — the ship-no-corpus licensing gate (Story 18.2).

T18-2a  value-or-refusal: grant passes; denied/unknown/absent refuse   (RQ13)
T18-2c  an unlicensed window still ingests + non-evidence use allowed;  (RQ15)
        governed-evidence citation is refused until a right is recorded
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from qmf.core.refusal import is_ok, is_refusal
from qmf.data.dukascopy import LicenseTag

from _e18 import (
    NS,
    FakeAdapter,
    download_resources,
    provider_record,
    store_at,
)

from qmb.data.catalog import PRESENT, list_data
from qmb.data.download import download
from qmb.data.licensing import (
    AuthorityKind,
    SourceWindowRef,
    VenueLicensePolicy,
    admit_governed_evidence,
    allow_non_evidence_use,
)

_POLICY = {
    "dukascopy-fx": VenueLicensePolicy(
        "dukascopy-fx", LicenseTag.INTERNAL_ONLY, "DEC-0170", AuthorityKind.OPERATOR_RULING
    )
}


def _window(tag):
    return SourceWindowRef("dukascopy-fx", "EURUSD", NS, NS + 10, license_tag=tag)


# --- T18-2a  value-or-typed-refusal (RQ13) ------------------------------------
def test_t18_2a_granting_tag_passes_with_authority() -> None:
    admission = admit_governed_evidence(_window("internal-only"), policies=_POLICY)
    assert is_ok(admission), admission
    adm = admission.value
    assert adm.venue == "dukascopy-fx" and adm.symbol == "EURUSD"
    assert adm.license_tag.value == "internal-only"
    assert adm.granting_authority == "DEC-0170"


def test_t18_2a_denied_unknown_absent_refuse_with_context() -> None:
    for tag in ("denied", "unknown", None):
        result = admit_governed_evidence(_window(tag), policies=_POLICY)
        assert is_refusal(result), f"tag {tag!r} must refuse governed-evidence use"
        assert result.category.value == "policy rejection"
        ctx = result.context
        # (venue, symbol, window) + tag state carried as machine-readable context.
        assert ctx.get("venue") == "dukascopy-fx"
        assert ctx.get("symbol") == "EURUSD"
        assert ctx.get("window_start_ns") == NS and ctx.get("window_end_ns") == NS + 10
        assert "license_tag" in ctx


def test_t18_2a_granting_tag_without_authority_refuses() -> None:
    # A grant tag with no per-venue policy / operator ruling cannot be inferred.
    result = admit_governed_evidence(_window("internal-only"), policies=None)
    assert is_refusal(result)
    assert result.category.value == "policy rejection"


# --- T18-2c  unlicensed window still ingests + catalogable; citation refused ---
def test_t18_2c_unlicensed_window_ingests_and_is_catalogable() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        # A window recorded with an unknown/blank usage right.
        res = download(
            download_resources(dest, license_tag="unknown"),
            adapter=FakeAdapter((provider_record("EURUSD#1", NS),)),
            store=store_at(dest),
        )
        assert is_ok(res), res
        listed = list_data({"destination": str(dest), "world": "replay"})
        assert is_ok(listed), listed
        assert listed.value.entries, "unlicensed window was not catalogable"
        for entry in listed.value.entries:
            assert entry.status == PRESENT


def test_t18_2c_non_evidence_use_allowed_but_citation_refused() -> None:
    window = _window("unknown")
    # infra-stress / strategy smoke: allowed without a usage right.
    assert is_ok(allow_non_evidence_use(window, use="infra-stress"))
    assert is_ok(allow_non_evidence_use(window, use="strategy-logic-smoke"))
    # governed-evidence citation: refused until a right is recorded.
    assert is_refusal(admit_governed_evidence(window, policies=_POLICY))
